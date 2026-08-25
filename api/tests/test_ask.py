"""
Tests for POST /ask endpoint.

Strategy
--------
- The LLM is mocked via app.state.llm — the same attribute the lifespan sets
  in production.  No Ollama instance is needed.
- hybrid_search is patched so the encoder (2 GB model) is never loaded.
- DB state comes from the standard conftest fixtures.

The conftest client fixture mocks app.state.redis and app.state.arq_redis but
does NOT set app.state.llm — we set it here so tests are explicit about what
the LLM returns.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chunk, Document, DocumentStatus
from src.generation.llm import OllamaUnavailable
from src.main import app


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_embedding() -> list[float]:
    vec = [0.0] * 1024
    vec[0] = 1.0
    return vec


async def _insert_doc_and_chunk(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    doc = Document(
        filename="reglamento.pdf",
        content_hash=uuid.uuid4().hex,
        status=DocumentStatus.completed,
    )
    session.add(doc)
    await session.flush()

    chunk = Chunk(
        document_id=doc.id,
        chunk_index=0,
        content="El plazo para presentar la declaración es de 30 días.",
        structure_path="Título I/Artículo 5",
        page_number=3,
        embedding=_make_embedding(),
    )
    session.add(chunk)
    await session.flush()
    return doc.id, chunk.id


# ── endpoint tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ask_returns_correct_structure_on_success(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /ask with a matching chunk returns found=True and well-formed sources."""
    doc_id, chunk_id = await _insert_doc_and_chunk(db_session)
    await db_session.commit()

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = (
        "El plazo es 30 días [Fuente: Título I/Artículo 5, página 3]"
    )
    app.state.llm = mock_llm

    with patch("src.retrieval.search.encode_query", return_value=_make_embedding()):
        response = await client.post("/ask", json={"question": "plazo declaración"})

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert "30 días" in body["answer"]
    assert len(body["sources"]) >= 1

    source = body["sources"][0]
    assert set(source.keys()) == {"chunk_id", "document_id", "structure_path", "page_number"}
    assert source["structure_path"] == "Título I/Artículo 5"
    assert source["page_number"] == 3


@pytest.mark.asyncio
async def test_ask_empty_db_returns_not_found(client: AsyncClient) -> None:
    """With no chunks in DB, the endpoint returns found=False, empty sources, no LLM call."""
    mock_llm = AsyncMock()
    app.state.llm = mock_llm

    with patch("src.retrieval.search.encode_query", return_value=_make_embedding()):
        response = await client.post("/ask", json={"question": "¿algo?"})

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is False
    assert body["sources"] == []
    mock_llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_ask_llm_unavailable_returns_found_false_with_sources(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    When Ollama is down, the endpoint returns found=False but still includes
    the retrieved sources so the client can display relevant fragments.
    """
    await _insert_doc_and_chunk(db_session)
    await db_session.commit()

    mock_llm = AsyncMock()
    mock_llm.generate.side_effect = OllamaUnavailable("timeout")
    app.state.llm = mock_llm

    with patch("src.retrieval.search.encode_query", return_value=_make_embedding()):
        response = await client.post("/ask", json={"question": "plazo"})

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is False
    assert len(body["sources"]) >= 1   # retrieval succeeded despite LLM failure
    assert body["answer"] != ""        # human-readable error message is present


@pytest.mark.asyncio
async def test_ask_missing_question_field_returns_422(client: AsyncClient) -> None:
    """FastAPI must reject a body without 'question' with 422 Unprocessable Entity."""
    response = await client.post("/ask", json={})
    assert response.status_code == 422
