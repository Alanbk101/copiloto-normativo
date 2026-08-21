"""
Integration tests for the process_document arq job.

The real embedding model is never loaded.  encode_passages is patched to
return deterministic 1024-dim vectors so we can assert that:
  - After a successful run the Document status is 'completed'.
  - All chunks have a non-NULL embedding of the correct dimension.

Idempotency is also verified: running the job twice does not duplicate chunks.

The `worker_ctx` fixture (from conftest) wires the job to the same test
engine as the rest of the test suite.
"""

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chunk, Document, DocumentStatus
from src.embeddings.encoder import _EMBEDDING_DIM
from src.worker.jobs import process_document


@pytest.fixture
def sample_pdf_path(tmp_path: Path) -> tuple[Path, str]:
    """
    Create a minimal real PDF and return (pdf_path, content_hash).

    We write the file under tmp_path using its own hash as the filename
    so process_document can locate it via _UPLOADS_DIR / {content_hash}.pdf.
    """
    raw = tmp_path / "_raw.pdf"
    c = canvas.Canvas(str(raw))
    c.drawString(72, 750, "ARTICULO 1")
    c.drawString(72, 730, "El presente reglamento regula la materia normativa.")
    c.save()

    content = raw.read_bytes()
    content_hash = hashlib.sha256(content).hexdigest()

    final = tmp_path / f"{content_hash}.pdf"
    final.write_bytes(content)
    return tmp_path, content_hash


@pytest.fixture(autouse=True)
async def cleanup_documents(db_session: AsyncSession) -> None:
    yield
    await db_session.execute(delete(Document))
    await db_session.commit()


def _fake_encode_passages(texts: list[str]) -> list[list[float]]:
    """Return deterministic 1024-dim vectors without loading the real model."""
    return [[0.0] * _EMBEDDING_DIM for _ in texts]


async def test_process_document_marks_completed_with_embeddings(
    worker_ctx: dict,
    db_session: AsyncSession,
    sample_pdf_path: tuple[Path, str],
) -> None:
    uploads_dir, content_hash = sample_pdf_path

    # Register document as the endpoint would.
    doc = Document(
        filename="test.pdf",
        content_hash=content_hash,
        status=DocumentStatus.pending,
    )
    db_session.add(doc)
    await db_session.commit()
    doc_id = str(doc.id)

    with (
        patch("src.worker.jobs._UPLOADS_DIR", uploads_dir),
        patch("src.worker.jobs.encode_passages", _fake_encode_passages),
    ):
        await process_document(worker_ctx, doc_id)

    # Reload from DB (db_session may have cached the old state).
    await db_session.refresh(doc)
    assert doc.status == DocumentStatus.completed
    assert doc.page_count == 1

    chunks = (
        await db_session.scalars(select(Chunk).where(Chunk.document_id == doc.id))
    ).all()
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.embedding is not None
        assert len(chunk.embedding) == _EMBEDDING_DIM


async def test_process_document_is_idempotent(
    worker_ctx: dict,
    db_session: AsyncSession,
    sample_pdf_path: tuple[Path, str],
) -> None:
    """Running the job twice must not duplicate chunks."""
    uploads_dir, content_hash = sample_pdf_path

    doc = Document(
        filename="test.pdf",
        content_hash=content_hash,
        status=DocumentStatus.pending,
    )
    db_session.add(doc)
    await db_session.commit()
    doc_id = str(doc.id)

    with (
        patch("src.worker.jobs._UPLOADS_DIR", uploads_dir),
        patch("src.worker.jobs.encode_passages", _fake_encode_passages),
    ):
        await process_document(worker_ctx, doc_id)

        # Simulate a retry by resetting status to pending.
        await db_session.refresh(doc)
        doc.status = DocumentStatus.pending
        db_session.add(doc)
        await db_session.commit()

        await process_document(worker_ctx, doc_id)

    chunks_after_two_runs = (
        await db_session.scalars(select(Chunk).where(Chunk.document_id == doc.id))
    ).all()
    first_run_count = len(chunks_after_two_runs)

    # Run a third time to confirm count is stable.
    with (
        patch("src.worker.jobs._UPLOADS_DIR", uploads_dir),
        patch("src.worker.jobs.encode_passages", _fake_encode_passages),
    ):
        await db_session.refresh(doc)
        doc.status = DocumentStatus.pending
        db_session.add(doc)
        await db_session.commit()
        await process_document(worker_ctx, doc_id)

    chunks_after_three_runs = (
        await db_session.scalars(select(Chunk).where(Chunk.document_id == doc.id))
    ).all()
    assert len(chunks_after_three_runs) == first_run_count
