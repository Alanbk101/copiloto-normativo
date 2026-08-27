"""
Tests for src/generation/llm.py and src/generation/answer.py.

Strategy
--------
- OllamaClient tests mock httpx.AsyncClient to avoid any real network call.
  The mock is patched at "src.generation.llm.httpx.AsyncClient" — the name
  as used inside the module under test.
- answer_question tests mock both hybrid_search and the LLMClient so neither
  the database nor Ollama is required.
- The real SentenceTransformer model is never loaded (hybrid_search is mocked).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.generation.answer import (
    AnswerResult,
    _NOT_FOUND_MSG,
    _LLM_ERROR_MSG,
    answer_question,
)
from src.generation.llm import OllamaClient, OllamaUnavailable


# ── OllamaClient ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ollama_client_sends_correct_request() -> None:
    """generate() must POST to /api/generate with the right model and prompt."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "respuesta del modelo"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.generation.llm.httpx.AsyncClient", return_value=mock_client):
        client = OllamaClient(base_url="http://ollama:11434", model="qwen2.5:1.5b")
        result = await client.generate("¿Cuál es el plazo?")

    mock_client.post.assert_called_once_with(
        "http://ollama:11434/api/generate",
        json={
            "model": "qwen2.5:1.5b",
            "prompt": "¿Cuál es el plazo?",
            "stream": False,
        },
    )
    assert result == "respuesta del modelo"


@pytest.mark.asyncio
async def test_ollama_client_raises_on_timeout() -> None:
    """A ReadTimeout from httpx must be wrapped in OllamaUnavailable."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ReadTimeout("timed out", request=MagicMock())
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.generation.llm.httpx.AsyncClient", return_value=mock_client):
        client = OllamaClient(base_url="http://ollama:11434", model="qwen2.5:1.5b")
        with pytest.raises(OllamaUnavailable, match="timeout"):
            await client.generate("pregunta")


@pytest.mark.asyncio
async def test_ollama_client_raises_on_http_error() -> None:
    """A 503 response from Ollama must be wrapped in OllamaUnavailable."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "503", request=MagicMock(), response=mock_response
    )

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.generation.llm.httpx.AsyncClient", return_value=mock_client):
        client = OllamaClient(base_url="http://ollama:11434", model="qwen2.5:1.5b")
        with pytest.raises(OllamaUnavailable, match="503"):
            await client.generate("pregunta")


@pytest.mark.asyncio
async def test_ollama_client_raises_on_connection_error() -> None:
    """A ConnectError (Ollama not running) must be wrapped in OllamaUnavailable."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.generation.llm.httpx.AsyncClient", return_value=mock_client):
        client = OllamaClient(base_url="http://ollama:11434", model="qwen2.5:1.5b")
        with pytest.raises(OllamaUnavailable):
            await client.generate("pregunta")


# ── answer_question ───────────────────────────────────────────────────────────

def _make_chunk_result(
    content: str = "contenido de prueba",
    structure_path: str = "Capítulo 1/Artículo 3",
    page_number: int = 5,
) -> object:
    """Return a minimal ChunkResult-like object for patching hybrid_search."""
    from src.retrieval.search import ChunkResult
    return ChunkResult(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content=content,
        structure_path=structure_path,
        page_number=page_number,
        score=0.5,
    )


@pytest.mark.asyncio
async def test_answer_question_empty_retrieval_returns_not_found_without_llm_call() -> None:
    """
    When hybrid_search returns no chunks, answer_question must:
    - return found=False with the "not found" message
    - NOT call llm.generate under any circumstances
    """
    mock_llm = AsyncMock()
    mock_session = AsyncMock()

    with patch(
        "src.generation.answer.hybrid_search", new=AsyncMock(return_value=[])
    ):
        result: AnswerResult = await answer_question("pregunta sin respuesta", mock_session, mock_llm)

    mock_llm.generate.assert_not_called()
    assert result.found is False
    assert result.sources == []
    assert _NOT_FOUND_MSG in result.answer


@pytest.mark.asyncio
async def test_answer_question_with_chunks_calls_llm_and_returns_found() -> None:
    """
    When chunks are found, answer_question must call llm.generate and return
    found=True with the model's answer and all retrieved chunks as sources.
    """
    chunk = _make_chunk_result()
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = "El plazo es de 30 días [Fuente: Capítulo 1/Artículo 3, página 5]"
    mock_session = AsyncMock()

    with patch(
        "src.generation.answer.hybrid_search", new=AsyncMock(return_value=[chunk])
    ):
        result: AnswerResult = await answer_question("¿cuál es el plazo?", mock_session, mock_llm)

    mock_llm.generate.assert_called_once()
    assert result.found is True
    assert len(result.sources) == 1
    assert result.sources[0].structure_path == chunk.structure_path
    assert result.sources[0].page_number == chunk.page_number
    assert "30 días" in result.answer


@pytest.mark.asyncio
async def test_answer_question_context_includes_structure_path_and_page() -> None:
    """The prompt passed to llm.generate must contain the chunk's metadata."""
    chunk = _make_chunk_result(
        content="El contribuyente debe presentar declaración.",
        structure_path="Título II/Artículo 7",
        page_number=12,
    )
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = "respuesta"
    mock_session = AsyncMock()

    with patch(
        "src.generation.answer.hybrid_search", new=AsyncMock(return_value=[chunk])
    ):
        await answer_question("pregunta", mock_session, mock_llm)

    prompt_sent: str = mock_llm.generate.call_args[0][0]
    assert "Título II/Artículo 7" in prompt_sent
    assert "12" in prompt_sent
    assert "El contribuyente debe presentar declaración." in prompt_sent


@pytest.mark.asyncio
async def test_answer_question_llm_failure_returns_sources_with_found_false() -> None:
    """
    When OllamaUnavailable is raised, answer_question must:
    - return found=False (generation failed)
    - still return the retrieved sources (retrieval succeeded)
    - include a human-readable error message
    """
    from src.generation.llm import OllamaUnavailable

    chunk = _make_chunk_result()
    mock_llm = AsyncMock()
    mock_llm.generate.side_effect = OllamaUnavailable("Ollama no responde")
    mock_session = AsyncMock()

    with patch(
        "src.generation.answer.hybrid_search", new=AsyncMock(return_value=[chunk])
    ):
        result: AnswerResult = await answer_question("pregunta", mock_session, mock_llm)

    assert result.found is False
    # Sources are preserved even though generation failed
    assert len(result.sources) == 1
    assert _LLM_ERROR_MSG in result.answer
