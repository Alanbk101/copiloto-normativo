import hashlib
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.engine import get_db_session
from src.db.models import Document
from src.ingest.service import count_chunks, register_document

router = APIRouter(prefix="/documents", tags=["documents"])

_UPLOADS_DIR = Path("uploads")


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    page_count: int | None
    chunk_count: int
    created_at: datetime


class DocumentUploadResponse(DocumentResponse):
    already_existed: bool


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    """
    Upload a PDF document for ingestion.

    Returns 202 Accepted for new uploads — the document is registered
    immediately but chunking and embedding happen asynchronously in the
    worker.  Poll GET /documents/{id} to track progress.

    Returns 200 OK for duplicate uploads (same content hash) — no new
    job is enqueued.
    """
    _validate_pdf(file)

    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    # Dedup: return the existing record without re-processing.
    existing = await session.scalar(
        select(Document).where(Document.content_hash == content_hash)
    )
    if existing is not None:
        chunk_count = await count_chunks(session, existing.id)
        return DocumentUploadResponse(
            id=existing.id,
            filename=existing.filename,
            status=existing.status.value,
            page_count=existing.page_count,
            chunk_count=chunk_count,
            created_at=existing.created_at,
            already_existed=True,
        )

    pdf_path = _UPLOADS_DIR / f"{content_hash}.pdf"
    pdf_path.write_bytes(content)

    doc = await register_document(
        session=session,
        filename=file.filename or "document.pdf",
        content_hash=content_hash,
    )

    await request.app.state.arq_redis.enqueue_job("process_document", str(doc.id))

    response.status_code = 202
    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status.value,
        page_count=doc.page_count,
        chunk_count=0,
        created_at=doc.created_at,
        already_existed=False,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_count = await count_chunks(session, doc.id)

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status.value,
        page_count=doc.page_count,
        chunk_count=chunk_count,
        created_at=doc.created_at,
    )


def _validate_pdf(file: UploadFile) -> None:
    """Reject non-PDF uploads at the boundary, before touching the filesystem."""
    filename = file.filename or ""
    content_type = file.content_type or ""

    if not filename.lower().endswith(".pdf") or content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted (check extension and Content-Type).",
        )
