"""
Integration tests for POST /documents and GET /documents/{id}.

With the async pipeline the endpoint now returns 202 Accepted immediately
after registering the document.  The worker processes chunks and embeddings
asynchronously — in these tests the worker never runs, so documents stay in
'pending' status and have zero chunks.  Worker behaviour is covered
separately in test_worker_job.py.

PDF fixture
-----------
Uses reportlab to generate a minimal but real PDF with a recognizable
heading ("ARTICULO 1") so the fixture is realistic.  The pipeline itself
is NOT invoked in these tests — we only exercise the HTTP layer.
reportlab is a dev dependency — it's the standard library for programmatic
PDF generation in Python.
"""

import io
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Document


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



async def test_upload_pdf_returns_202_with_pending_status(
    client: AsyncClient, sample_pdf: Path
) -> None:
    with open(sample_pdf, "rb") as f:
        response = await client.post(
            "/documents",
            files={"file": ("reglamento_test.pdf", f, "application/pdf")},
        )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert data["chunk_count"] == 0
    assert data["page_count"] is None
    assert data["already_existed"] is False
    assert data["filename"] == "reglamento_test.pdf"


async def test_upload_enqueues_job(client: AsyncClient, sample_pdf: Path) -> None:
    """The endpoint must call enqueue_job exactly once for a new document."""
    with open(sample_pdf, "rb") as f:
        response = await client.post(
            "/documents",
            files={"file": ("reglamento_test.pdf", f, "application/pdf")},
        )

    assert response.status_code == 202
    from src.main import app

    app.state.arq_redis.enqueue_job.assert_called_once()
    call_args = app.state.arq_redis.enqueue_job.call_args
    assert call_args.args[0] == "process_document"


async def test_upload_same_pdf_returns_existing_without_duplicating(
    client: AsyncClient, sample_pdf: Path
) -> None:
    pdf_bytes = sample_pdf.read_bytes()

    first = await client.post(
        "/documents",
        files={"file": ("reglamento_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert first.status_code == 202
    assert first.json()["already_existed"] is False

    second = await client.post(
        "/documents",
        files={"file": ("reglamento_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert second.status_code == 200
    data = second.json()
    assert data["already_existed"] is True
    assert data["id"] == first.json()["id"]


async def test_upload_non_pdf_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/documents",
        files={"file": ("report.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400


async def test_get_document_returns_status(
    client: AsyncClient, sample_pdf: Path
) -> None:
    with open(sample_pdf, "rb") as f:
        upload = await client.post(
            "/documents",
            files={"file": ("reglamento_test.pdf", f, "application/pdf")},
        )
    assert upload.status_code == 202
    doc_id = upload.json()["id"]

    get_response = await client.get(f"/documents/{doc_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == doc_id
    assert data["status"] == "pending"


async def test_get_document_returns_404_for_unknown_id(client: AsyncClient) -> None:
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/documents/{fake_id}")
    assert response.status_code == 404
