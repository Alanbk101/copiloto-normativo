"""
Ingest service: orchestrates the full pipeline for a new document.

Transaction strategy
--------------------
Phase 1 — INSERT Document(status=processing) and commit immediately.
          The document is visible in the DB before the pipeline runs,
          so a crash mid-pipeline leaves a traceable record rather than
          leaving the caller wondering if the upload happened.

Phase 2 — Run the pure-Python pipeline (no DB I/O).
          On success: bulk-INSERT all chunks + UPDATE Document in one
          transaction.  On failure: UPDATE Document(status=failed) in
          its own transaction, then re-raise so the endpoint can return
          an appropriate HTTP error.

Invariant: a Document never stays in 'processing' after this function
           returns, regardless of outcome.
"""

import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chunk as DbChunk
from src.db.models import Document, DocumentStatus
from src.ingest.chunker import chunk_document
from src.ingest.parser import extract_pages
from src.ingest.structure import detect_structure


async def ingest_document(
    session: AsyncSession,
    pdf_path: Path,
    filename: str,
    content_hash: str,
) -> tuple[Document, int]:
    """
    Run the ingest pipeline and persist results.

    Returns the completed Document and the number of chunks created.
    Raises on pipeline failure after marking the Document as 'failed'.
    """
    # Phase 1: register the document so a failure is always traceable.
    # We rely on autobegin (SQLAlchemy 2.0 default) rather than calling
    # session.begin() explicitly — the session may already have an active
    # transaction started by a prior SELECT in the calling endpoint.
    doc = Document(
        filename=filename,
        content_hash=content_hash,
        status=DocumentStatus.processing,
    )
    session.add(doc)
    await session.commit()  # doc.id is populated; expire_on_commit=False keeps it accessible

    try:
        pages = extract_pages(pdf_path)
        blocks = detect_structure(pages)
        chunks = chunk_document(blocks)

        db_chunks = [
            DbChunk(
                document_id=doc.id,
                chunk_index=c.chunk_index,
                content=c.content,
                structure_path=c.structure_path,
                page_number=c.page_number,
                # embedding stays NULL until the embedding worker runs (part C)
            )
            for c in chunks
        ]

        # Phase 2: bulk-insert chunks and mark the document completed.
        session.add_all(db_chunks)
        doc.status = DocumentStatus.completed
        doc.page_count = len(pages)
        session.add(doc)
        await session.commit()

        return doc, len(chunks)

    except Exception as exc:
        # Rollback any pending adds before writing the failure status.
        # If the pipeline raised before any DB work, this is a no-op.
        # If session.commit() above raised, this clears the dirty state.
        await session.rollback()
        doc.status = DocumentStatus.failed
        doc.error_message = str(exc)[:500]
        session.add(doc)
        await session.commit()
        raise


async def count_chunks(session: AsyncSession, document_id: uuid.UUID) -> int:
    """Return the number of chunks persisted for a given document."""
    result = await session.scalar(
        select(func.count()).select_from(DbChunk).where(DbChunk.document_id == document_id)
    )
    return result or 0
