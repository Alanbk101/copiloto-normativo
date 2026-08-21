"""
Ingest service: pure-Python pipeline and document registration.

Responsibilities
----------------
run_pipeline     — parse → structure → chunk.  Pure Python, no DB, no async.
                   Used by the arq worker (src.worker.jobs) to do the heavy
                   lifting outside the HTTP request cycle.

register_document — inserts Document(status=pending) and commits so the
                    record is immediately visible in the DB before the worker
                    picks up the job.

count_chunks     — read-only helper for the GET endpoint.
"""

import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chunk as DbChunk
from src.db.models import Document, DocumentStatus
from src.ingest.chunker import chunk_document
from src.ingest.models import Chunk, PageText
from src.ingest.parser import extract_pages
from src.ingest.structure import detect_structure


def run_pipeline(pdf_path: Path) -> tuple[list[PageText], list[Chunk]]:
    """
    Run the pure-Python ingest pipeline.

    Returns the extracted pages and the final list of indexable chunks.
    No database access, no async — safe to call from a thread pool.
    """
    pages = extract_pages(pdf_path)
    blocks = detect_structure(pages)
    chunks = chunk_document(blocks)
    return pages, chunks


async def register_document(
    session: AsyncSession,
    filename: str,
    content_hash: str,
) -> Document:
    """
    Insert a Document with status=pending and commit immediately.

    The record is visible in the DB as soon as this returns, so the
    worker can find it even if the caller crashes right after enqueueing.
    """
    doc = Document(
        filename=filename,
        content_hash=content_hash,
        status=DocumentStatus.pending,
    )
    session.add(doc)
    await session.commit()
    return doc


async def count_chunks(session: AsyncSession, document_id: uuid.UUID) -> int:
    """Return the number of chunks persisted for a given document."""
    result = await session.scalar(
        select(func.count()).select_from(DbChunk).where(DbChunk.document_id == document_id)
    )
    return result or 0
