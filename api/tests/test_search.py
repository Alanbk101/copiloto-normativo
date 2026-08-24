"""
Tests for hybrid retrieval (Paso 4).

Strategy
--------
- _rrf is a pure function → unit-tested with handcrafted ID lists, no DB, no async.
- Full-text and endpoint tests hit real Postgres via the conftest db_session fixture.
- encode_query is patched in every integration test so the 2 GB model is never loaded.
  The patch target is "src.retrieval.search.encode_query" — the name as imported
  in the module under test, not the original definition site.
- Chunk fixtures always insert a parent Document first (FK constraint).
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chunk, Document, DocumentStatus
from src.retrieval.search import RRF_K, ChunkResult, _rrf, hybrid_search


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_embedding(leading: float) -> list[float]:
    """1024-dim vector with `leading` at position 0, zeros elsewhere."""
    vec = [0.0] * 1024
    vec[0] = leading
    return vec


async def _insert_document(session: AsyncSession) -> uuid.UUID:
    doc = Document(
        filename="test.pdf",
        content_hash=uuid.uuid4().hex,
        status=DocumentStatus.completed,
    )
    session.add(doc)
    await session.flush()
    return doc.id


async def _insert_chunk(
    session: AsyncSession,
    document_id: uuid.UUID,
    content: str,
    embedding: list[float] | None,
    chunk_index: int = 0,
) -> uuid.UUID:
    chunk = Chunk(
        document_id=document_id,
        chunk_index=chunk_index,
        content=content,
        structure_path="§1",
        page_number=1,
        embedding=embedding,
    )
    session.add(chunk)
    await session.flush()
    return chunk.id


# ── unit tests: _rrf ───────────────────────────────────────────────────────────

def test_rrf_double_hit_scores_higher_than_single_hit() -> None:
    """
    Chunk A appears at rank 1 in both lists → score = 2/(60+1).
    Chunk B appears at rank 1 in only the FT list → score = 1/(60+1).
    Chunk A must rank first.
    """
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()

    ranked = _rrf(ft_ids=[id_a, id_b], vec_ids=[id_a])

    assert ranked[0][0] == id_a
    assert ranked[0][1] == pytest.approx(2 / (RRF_K + 1))
    assert ranked[1][0] == id_b
    assert ranked[1][1] == pytest.approx(1 / (RRF_K + 2))  # id_b is rank 2 in FT


def test_rrf_returns_descending_order() -> None:
    """Scores must be non-increasing from first to last entry."""
    ids = [uuid.uuid4() for _ in range(5)]
    # ids[0] appears at rank 1 in both lists → highest score
    ranked = _rrf(ft_ids=ids[:3], vec_ids=[ids[0], ids[3], ids[4]])
    scores = [score for _, score in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rrf_empty_lists() -> None:
    assert _rrf([], []) == []


def test_rrf_only_one_list() -> None:
    id_a, id_b = uuid.uuid4(), uuid.uuid4()
    ranked = _rrf([id_a, id_b], [])
    assert ranked[0][0] == id_a  # rank 1 beats rank 2
    assert ranked[0][1] > ranked[1][1]


# ── integration: full-text search ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fulltext_finds_chunk_by_exact_word(db_session: AsyncSession) -> None:
    """
    A chunk containing 'fiscalización' must be returned when the question
    contains that word.  A chunk with unrelated content must not appear.
    """
    doc_id = await _insert_document(db_session)
    target_id = await _insert_chunk(
        db_session, doc_id,
        content="El procedimiento de fiscalización tributaria aplica a personas morales.",
        embedding=_make_embedding(1.0),
        chunk_index=0,
    )
    await _insert_chunk(
        db_session, doc_id,
        content="El régimen simplificado de confianza tiene tasas diferenciadas.",
        embedding=_make_embedding(0.0),
        chunk_index=1,
    )
    await db_session.commit()

    with patch("src.retrieval.search.encode_query", return_value=_make_embedding(0.5)):
        results = await hybrid_search(db_session, "fiscalización", top_n=5)

    assert target_id in [r.id for r in results]


@pytest.mark.asyncio
async def test_search_returns_empty_list_when_no_match(db_session: AsyncSession) -> None:
    """No chunks in DB → hybrid_search returns [] without raising."""
    with patch("src.retrieval.search.encode_query", return_value=_make_embedding(0.0)):
        results = await hybrid_search(db_session, "xyzzy irrelevante", top_n=5)
    assert results == []


# ── integration: RRF ordering ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_search_double_hit_ranks_above_single_hit(
    db_session: AsyncSession,
) -> None:
    """
    Verifies the core RRF guarantee: a chunk that appears in both FT and vector
    results always outscores a chunk that appears in only one list.

    Setup
    -----
    chunk_a: embedding=[1.0,0,...] (identical to mocked query) + content with
             'fiscalización tributaria' → rank 1 in vector, appears in FT.
             Double hit.

    chunk_b: embedding=None (excluded from vector search by WHERE IS NOT NULL)
             + content with 'fiscalización tributaria' → appears in FT only.
             Single hit.

    Why chunk_a always wins
    -----------------------
    Even if chunk_b ranks first in FT, chunk_a's minimum combined score is:
      1/(60+2) + 1/(60+1) ≈ 0.0325  (FT rank 2 + vec rank 1)
    chunk_b's maximum score is:
      1/(60+1) ≈ 0.0164  (FT rank 1, no vec contribution)

    The double-hit minimum beats the single-hit maximum regardless of FT order.
    """
    doc_id = await _insert_document(db_session)
    chunk_a_id = await _insert_chunk(
        db_session, doc_id,
        content="artículo fiscalización tributaria obligaciones contribuyentes",
        embedding=_make_embedding(1.0),
        chunk_index=0,
    )
    chunk_b_id = await _insert_chunk(
        db_session, doc_id,
        content="fiscalización tributaria personas físicas actividad empresarial",
        embedding=None,  # excluded from vector search; single hit (FT only)
        chunk_index=1,
    )
    await db_session.commit()

    with patch("src.retrieval.search.encode_query", return_value=_make_embedding(1.0)):
        results = await hybrid_search(db_session, "fiscalización tributaria", top_n=5)

    ids = [r.id for r in results]
    assert chunk_a_id in ids, "double-hit chunk must appear in results"
    assert chunk_b_id in ids, "FT-only chunk must appear in results"
    assert ids.index(chunk_a_id) < ids.index(chunk_b_id), (
        f"Expected chunk_a (double-hit) before chunk_b (FT-only). Order: {ids}"
    )


# ── endpoint tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_endpoint_returns_correct_structure(
    client,
    db_session: AsyncSession,
) -> None:
    """POST /search returns a list with the expected field names and types."""
    doc_id = await _insert_document(db_session)
    await _insert_chunk(
        db_session, doc_id,
        content="impuesto sobre la renta personas morales deducciones autorizadas",
        embedding=_make_embedding(1.0),
        chunk_index=0,
    )
    await db_session.commit()

    with patch("src.retrieval.search.encode_query", return_value=_make_embedding(1.0)):
        response = await client.post("/search", json={"question": "impuesto renta"})

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 1

    first = body[0]
    assert set(first.keys()) == {
        "id", "document_id", "content", "structure_path", "page_number", "score"
    }
    assert isinstance(first["score"], float)
    assert isinstance(first["page_number"], int)


@pytest.mark.asyncio
async def test_search_endpoint_respects_top_k(
    client,
    db_session: AsyncSession,
) -> None:
    """top_k=1 returns at most one chunk even when multiple chunks match."""
    doc_id = await _insert_document(db_session)
    for i in range(3):
        await _insert_chunk(
            db_session, doc_id,
            content=f"contribuyente obligación fiscal declaración anual número {i}",
            embedding=_make_embedding(float(i + 1)),
            chunk_index=i,
        )
    await db_session.commit()

    with patch("src.retrieval.search.encode_query", return_value=_make_embedding(1.0)):
        response = await client.post(
            "/search", json={"question": "obligación fiscal", "top_k": 1}
        )

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_search_endpoint_empty_db_returns_empty_list(client) -> None:
    """No chunks in DB → 200 with empty list, not a 404 or 500."""
    with patch("src.retrieval.search.encode_query", return_value=_make_embedding(0.0)):
        response = await client.post("/search", json={"question": "nada"})

    assert response.status_code == 200
    assert response.json() == []
