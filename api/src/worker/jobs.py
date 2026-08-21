"""
arq job: process_document

Pipeline
--------
Phase 1  Mark the Document as 'processing' and commit immediately so
         the status is visible while the heavy work runs.

Phase 2  Run the pure-Python pipeline (parse → structure → chunk),
         generate embeddings in a thread pool (encode is synchronous
         and CPU-bound — we must not block the event loop), then
         persist everything atomically.

Idempotency
-----------
arq retries jobs that raise an exception.  If the job ran partially in
a previous attempt it may have left orphan chunks.  Before inserting,
we delete any existing chunks for this document_id so a retry always
produces a clean result.

Transaction pattern (matches the convention established in 3B)
--------------------------------------------------------------
Phase 1 uses its own session → its own autobegin → explicit commit.
Phase 2 opens a fresh session.  On success: bulk DELETE old chunks +
bulk INSERT new chunks + UPDATE Document, all in one autobegin, then
explicit commit.  On failure: explicit rollback (clears dirty state),
then write Document(status=failed) in a new autobegin, then commit.
No session.begin() calls — we rely on SQLAlchemy 2.0 autobegin.
"""

import asyncio
import uuid
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import Chunk as DbChunk
from src.db.models import Document, DocumentStatus
from src.embeddings.encoder import encode_passages
from src.ingest.service import run_pipeline

_UPLOADS_DIR = Path("uploads")


async def process_document(ctx: dict, document_id: str) -> None:
    """
    Ingest a document: chunk it, embed it, persist it.

    Called by arq.  `ctx` is populated by WorkerSettings.on_startup and
    contains `session_factory` (an async_sessionmaker bound to the worker's
    own engine).
    """
    doc_uuid = uuid.UUID(document_id)
    factory: async_sessionmaker[AsyncSession] = ctx["session_factory"]

    # ── Phase 1: mark as processing ────────────────────────────────────────
    async with factory() as session:
        doc = await session.get(Document, doc_uuid)
        if doc is None:
            raise ValueError(f"Document {document_id} not found in database")

        content_hash = doc.content_hash  # capture before session closes
        doc.status = DocumentStatus.processing
        session.add(doc)
        await session.commit()

    pdf_path = _UPLOADS_DIR / f"{content_hash}.pdf"

    # ── Phase 2: pipeline → embed → persist ────────────────────────────────
    async with factory() as session:
        doc = await session.get(Document, doc_uuid)
        try:
            pages, chunks = run_pipeline(pdf_path)

            # encode_passages is synchronous and CPU-bound — run in a thread
            # so the event loop stays free for other jobs
            texts = [c.content for c in chunks]
            embeddings: list[list[float]] = await asyncio.to_thread(encode_passages, texts)

            # Idempotency: remove chunks left by any previous partial run
            await session.execute(
                delete(DbChunk).where(DbChunk.document_id == doc_uuid)
            )

            db_chunks = [
                DbChunk(
                    document_id=doc_uuid,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    structure_path=c.structure_path,
                    page_number=c.page_number,
                    embedding=emb,
                )
                for c, emb in zip(chunks, embeddings)
            ]
            session.add_all(db_chunks)

            doc.status = DocumentStatus.completed
            doc.page_count = len(pages)
            session.add(doc)
            await session.commit()

        except Exception as exc:
            # Rollback the failed transaction (undoes the DELETE + any INSERTs)
            # before writing the failure status in a clean autobegin.
            await session.rollback()
            doc.status = DocumentStatus.failed
            doc.error_message = str(exc)[:500]
            session.add(doc)
            await session.commit()
            raise
