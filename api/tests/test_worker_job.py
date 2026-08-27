"""
Integration tests for the process_document arq job.

The real embedding model is never loaded.  encode_passages is patched to
return deterministic 1024-dim vectors so we can assert that:
  - After a successful run the Document status is 'completed'.
  - All chunks have a non-NULL embedding of the correct dimension.

Idempotency is also verified: running the job twice does not duplicate chunks.

Persistence regression test
---------------------------
test_chunks_are_persisted_independently verifies that chunks really land in the
database by querying via a *separate engine* — not the shared db_session or the
worker's session_factory.  This rules out any SQLAlchemy identity-map caching
masking a missing commit.  It also simulates encoding latency (via a small
sleep inside the fake encoder) so the session is idle long enough to expose
connection-timeout bugs that the instant fake_encode_passages would miss.

The `worker_ctx` fixture (from conftest) wires the job to the same test
engine as the rest of the test suite.
"""

import asyncio
import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import settings
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


# ---------------------------------------------------------------------------
# Persistence regression test
# ---------------------------------------------------------------------------
# This test exists specifically to catch the production bug where the worker
# reports "completed" but the chunks table is empty.
#
# Two things make it different from the tests above:
#
# 1. Verification via an INDEPENDENT engine — not the worker's session factory
#    and not db_session.  This rules out SQLAlchemy identity-map caching where
#    the session "knows" about objects it added but that were never actually
#    committed to PostgreSQL.
#
# 2. Encoding latency — the fake encoder sleeps briefly so the transaction
#    opened by session.get() is idle for a moment before the DB writes happen.
#    This exercises the same timing window that the production bug hits (the
#    real encoder holds the connection idle for minutes).
# ---------------------------------------------------------------------------

def _slow_fake_encode_passages(texts: list[str]) -> list[list[float]]:
    """
    Fake encoder that sleeps 50 ms to simulate CPU-bound work.

    50 ms is enough to expose in-process session/connection state bugs without
    making the test suite noticeably slower.
    """
    import time
    time.sleep(0.05)
    return [[float(i % 10) / 10] * _EMBEDDING_DIM for i, _ in enumerate(texts)]


async def test_chunks_are_persisted_independently(
    worker_ctx: dict,
    db_session: AsyncSession,
    sample_pdf_path: tuple[Path, str],
) -> None:
    """
    Regression: chunks must be present in the DB after a successful job run,
    verified via a completely separate database connection.

    If this test fails while test_process_document_marks_completed_with_embeddings
    passes, the bug is in the commit/flush of chunks (not in status update) and
    SQLAlchemy's session cache was hiding it from the shared db_session.
    """
    uploads_dir, content_hash = sample_pdf_path

    doc = Document(
        filename="regression.pdf",
        content_hash=content_hash,
        status=DocumentStatus.pending,
    )
    db_session.add(doc)
    await db_session.commit()
    doc_id = str(doc.id)

    with (
        patch("src.worker.jobs._UPLOADS_DIR", uploads_dir),
        patch("src.worker.jobs.encode_passages", _slow_fake_encode_passages),
    ):
        await process_document(worker_ctx, doc_id)

    # ── Verify via a completely independent engine ──────────────────────────
    # This bypasses db_session's identity map and the worker's session factory.
    # If chunks are in the DB they will show up here regardless of any
    # in-process SQLAlchemy state.
    probe_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        probe_factory = async_sessionmaker(probe_engine, expire_on_commit=False)
        async with probe_factory() as probe:
            chunk_count = await probe.scalar(
                select(func.count())
                .select_from(Chunk)
                .where(Chunk.document_id == doc.id)
            )
            doc_status_value = await probe.scalar(
                select(Document.status).where(Document.id == doc.id)
            )
    finally:
        await probe_engine.dispose()

    assert doc_status_value == DocumentStatus.completed, (
        f"Document status is '{doc_status_value}', expected 'completed'"
    )
    assert chunk_count is not None and chunk_count > 0, (
        f"Document is completed but chunks table has {chunk_count} rows — "
        "the commit of add_all(db_chunks) did not reach the database"
    )
