import hashlib
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.engine import get_db_session
from src.db.models import Document
from src.ingest.service import count_chunks, ingest_document

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


@router.post("", response_model=DocumentUploadResponse, status_code=200)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    _validate_pdf(file)

    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    # Dedup check: return the existing document without re-processing.
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

    try:
        doc, chunk_count = await ingest_document(
            session=session,
            pdf_path=pdf_path,
            filename=file.filename or "document.pdf",
            content_hash=content_hash,
        )
    except Exception as exc:
        # The service already marked the document as 'failed' in the DB.
        # Surface a clear error instead of a raw 500.
        raise HTTPException(
            status_code=422,
            detail=f"PDF processing failed: {exc}",
        ) from exc

    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status.value,
        page_count=doc.page_count,
        chunk_count=chunk_count,
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
