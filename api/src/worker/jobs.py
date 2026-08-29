"""
arq job: process_document

Pipeline
--------
Phase 1  Mark the Document as 'processing' and commit immediately so
         the status is visible while the heavy work runs.

Phase 2a Run the pure-Python pipeline (parse → structure → chunk) and
         generate embeddings in a thread pool.  No session is open here —
         the previous bug held a transaction idle for the entire duration
         of the CPU-bound embedding call (minutes on CPU), which caused
         the connection to be killed by PostgreSQL or the network layer,
         losing the pending chunk INSERTs on reconnect.

Phase 2b Open a fresh session only for the DB writes (DELETE orphans +
         INSERT chunks + UPDATE Document).  The session is alive for
         milliseconds, not minutes.  All three operations are in one
         autobegin transaction, committed with a single session.commit().

Capture-before-commit (option 1)
---------------------------------
Values needed after the commit (chunk_count, page_count) are captured
in plain local variables before session.commit() is called.  This avoids
touching expired ORM attributes after commit, regardless of the
expire_on_commit setting of the factory.

Idempotency
-----------
arq retries jobs that raise an exception.  If the job ran partially in
a previous attempt it may have left orphan chunks.  Before inserting,
we delete any existing chunks for this document_id so a retry always
produces a clean result.

Transaction pattern (matches the convention established in 3B)
--------------------------------------------------------------
Phase 1 uses its own session → its own autobegin → explicit commit.
Phase 2b opens a fresh session.  On success: bulk DELETE old chunks +
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

    # ── Phase 2a: pipeline + embeddings (no session, no idle transaction) ──
    # The session must NOT be open here.  encode_passages is CPU-bound and
    # can run for minutes; holding a transaction open that long risks a
    # connection timeout from PostgreSQL (idle_in_transaction_session_timeout)
    # or from a network proxy.  A dead connection on reconnect loses the
    # pending add_all(db_chunks) from the session's identity map.
    pages, chunks = run_pipeline(pdf_path)
    texts = [c.content for c in chunks]
    embeddings: list[list[float]] = await encode_passages(texts)

    # Capture values we need after the commit in plain local variables so we
    # never have to read attributes off an expired ORM object (option 1).
    page_count = len(pages)
    chunk_count = len(chunks)

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

    # ── Phase 2b: persist (session open only during fast DB ops) ───────────
    async with factory() as session:
        doc = await session.get(Document, doc_uuid)
        try:
            # Idempotency: remove chunks left by any previous partial run.
            await session.execute(
                delete(DbChunk).where(DbChunk.document_id == doc_uuid)
            )

            session.add_all(db_chunks)

            doc.status = DocumentStatus.completed
            doc.page_count = page_count
            session.add(doc)

            # Single commit: DELETE orphans + INSERT chunks + UPDATE Document
            # are all in one autobegin transaction.  No second commit that
            # could roll back what the first one did.
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

        except BaseException as exc:
            # CancelledError (arq job timeout) lands here — it is a BaseException,
            # not an Exception, so the block above is skipped entirely.
            #
            # The current session may be in a broken state: any await inside it
            # could itself raise CancelledError again.  Open a fresh session and
            # shield the write so the cleanup task survives the cancellation of
            # this job coroutine.
            error_msg = (str(exc) or type(exc).__name__)[:500]

            async def _mark_failed_after_cancel() -> None:
                try:
                    async with factory() as fail_session:
                        fail_doc = await fail_session.get(Document, doc_uuid)
                        if fail_doc is not None:
                            fail_doc.status = DocumentStatus.failed
                            fail_doc.error_message = error_msg
                            fail_session.add(fail_doc)
                            await fail_session.commit()
                except Exception:
                    pass  # best-effort: don't let cleanup errors shadow the original

            try:
                # shield keeps the inner task alive even though *this* task is
                # being cancelled; the await here will raise CancelledError (the
                # outer task is still cancelled), but the inner task continues.
                await asyncio.shield(_mark_failed_after_cancel())
            except asyncio.CancelledError:
                pass  # inner task is still running — that's the intended behaviour
            raise
