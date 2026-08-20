"""
Integration tests for POST /documents and GET /documents/{id}.

PDF fixture
-----------
Uses reportlab to generate a minimal but real PDF with a recognizable
heading ("ARTICULO 1") so detect_structure() produces at least one chunk.
reportlab is a dev dependency — it's the standard library for programmatic
PDF generation in Python.
"""

import io
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chunk, Document


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Generate a minimal valid PDF with extractable text."""
    from reportlab.pdfgen import canvas

    path = tmp_path / "reglamento_test.pdf"
    c = canvas.Canvas(str(path))
    c.drawString(72, 750, "ARTICULO 1")
    c.drawString(72, 730, "El presente reglamento establece las bases generales.")
    c.drawString(72, 710, "Las disposiciones aplican a todas las entidades reguladas.")
    c.save()
    return path


@pytest.fixture(autouse=True)
async def cleanup_documents(db_session: AsyncSession) -> None:
    """Delete all documents (and cascaded chunks) created during each test."""
    yield
    await db_session.execute(delete(Document))
    await db_session.commit()


async def test_upload_pdf_creates_document_and_chunks(
    client: AsyncClient, sample_pdf: Path
) -> None:
    with open(sample_pdf, "rb") as f:
        response = await client.post(
            "/documents",
            files={"file": ("reglamento_test.pdf", f, "application/pdf")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["chunk_count"] >= 1
    assert data["page_count"] == 1
    assert data["already_existed"] is False
    assert data["filename"] == "reglamento_test.pdf"


async def test_upload_same_pdf_returns_existing_without_duplicating(
    client: AsyncClient, sample_pdf: Path
) -> None:
    pdf_bytes = sample_pdf.read_bytes()

    first = await client.post(
        "/documents",
        files={"file": ("reglamento_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert first.status_code == 200
    assert first.json()["already_existed"] is False

    second = await client.post(
        "/documents",
        files={"file": ("reglamento_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert second.status_code == 200
    data = second.json()
    assert data["already_existed"] is True
    # Same document id returned — no duplicate created.
    assert data["id"] == first.json()["id"]
    assert data["chunk_count"] == first.json()["chunk_count"]


async def test_upload_non_pdf_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/documents",
        files={"file": ("report.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400


async def test_get_document_returns_status_and_chunk_count(
    client: AsyncClient, sample_pdf: Path
) -> None:
    with open(sample_pdf, "rb") as f:
        upload = await client.post(
            "/documents",
            files={"file": ("reglamento_test.pdf", f, "application/pdf")},
        )
    assert upload.status_code == 200
    doc_id = upload.json()["id"]
    expected_chunks = upload.json()["chunk_count"]

    get_response = await client.get(f"/documents/{doc_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == doc_id
    assert data["status"] == "completed"
    assert data["chunk_count"] == expected_chunks


async def test_get_document_returns_404_for_unknown_id(client: AsyncClient) -> None:
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/documents/{fake_id}")
    assert response.status_code == 404
