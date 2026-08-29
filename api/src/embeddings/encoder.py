"""
Text encoder — local (multilingual-e5-large) or Jina AI API.

Public interface
----------------
Both functions are async.  Callers await them directly; the implementation
handles whether the work belongs in a thread (local, CPU-bound) or in an
async HTTP call (Jina, I/O-bound).

  encode_passages(texts)  →  list[list[float]]   (batch, for indexing)
  encode_query(text)      →  list[float]          (single, for retrieval)

Provider selection
------------------
Controlled by settings.embedding_provider:

  "jina"  — calls the Jina AI Embeddings API (requires JINA_API_KEY).
             Uses task-specific LoRA adapters:
               retrieval.passage  for encode_passages
               retrieval.query    for encode_query
             Requests dimensions=1024 explicitly so the column contract is
             documented in code and immune to future API default changes.

  "local" — loads intfloat/multilingual-e5-large via sentence-transformers.
             CPU-bound; runs in asyncio.to_thread so the event loop is free.
             Applies "passage: " / "query: " prefixes required by e5 training.

Jina error handling
-------------------
JinaUnavailable is raised on 401 (bad key), 429 (rate limit), timeouts, and
network failures.  The caller surfaces a structured error to the user instead
of an unhandled exception.
"""

import asyncio
import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Jina
# ---------------------------------------------------------------------------

_JINA_ENDPOINT = "https://api.jina.ai/v1/embeddings"
_JINA_DIM = 1024  # matches vector(1024) in the DB schema

_JINA_TIMEOUT = httpx.Timeout(connect=10.0, write=10.0, read=60.0, pool=10.0)


class JinaUnavailable(Exception):
    """Raised when the Jina Embeddings API cannot be reached or returns an error."""


async def _jina_embed(texts: list[str], task: str) -> list[list[float]]:
    """
    Call the Jina Embeddings API for *texts* with the given *task* adapter.

    task values:
      "retrieval.passage" — for document chunks being indexed
      "retrieval.query"   — for user queries at search time
    """
    headers = {
        "Authorization": f"Bearer {settings.jina_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.jina_model,
        "input": texts,
        "task": task,
        "dimensions": _JINA_DIM,
    }
    logger.debug("Jina embed  task=%s  texts=%d  model=%s", task, len(texts), settings.jina_model)
    try:
        async with httpx.AsyncClient(timeout=_JINA_TIMEOUT) as client:
            response = await client.post(_JINA_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # OpenAI-compatible response: data[].embedding, ordered by index
            items = sorted(data["data"], key=lambda x: x["index"])
            embeddings = [item["embedding"] for item in items]
            logger.debug("Jina embed ← %d vectors of dim %d", len(embeddings), len(embeddings[0]))
            return embeddings
    except httpx.TimeoutException as exc:
        logger.error("Jina timeout: %s", exc)
        raise JinaUnavailable(f"Jina did not respond within {_JINA_TIMEOUT.read}s") from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 401:
            logger.error("Jina 401 — check JINA_API_KEY")
            raise JinaUnavailable("Jina rejected the API key (401)") from exc
        if status == 429:
            logger.error("Jina 429 — rate limit exceeded")
            raise JinaUnavailable("Jina rate limit exceeded (429)") from exc
        logger.error("Jina HTTP %s — body: %s", status, exc.response.text[:500])
        raise JinaUnavailable(f"Jina returned HTTP {status}") from exc
    except httpx.RequestError as exc:
        logger.error("Jina request error: %s", exc)
        raise JinaUnavailable(f"Could not reach Jina: {exc}") from exc


# ---------------------------------------------------------------------------
# Local (sentence-transformers, kept for EMBEDDING_PROVIDER=local)
# ---------------------------------------------------------------------------

_MODEL_NAME = "intfloat/multilingual-e5-large"

# Loaded on first use; None until then.  Only instantiated when provider=local.
_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        _local_model = SentenceTransformer(_MODEL_NAME)
    return _local_model


def _local_encode_passages(texts: list[str]) -> list[list[float]]:
    prefixed = [f"passage: {t}" for t in texts]
    model = _get_local_model()
    embeddings = model.encode(prefixed, convert_to_numpy=True)
    return [vec.tolist() for vec in embeddings]


def _local_encode_query(text: str) -> list[float]:
    model = _get_local_model()
    embedding = model.encode(f"query: {text}", convert_to_numpy=True)
    return embedding.tolist()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def encode_passages(texts: list[str]) -> list[list[float]]:
    """
    Encode a batch of document passages for indexing.

    With provider=jina: single batched HTTP call to the Jina API.
    With provider=local: runs sentence-transformers in a thread pool.
    """
    if settings.embedding_provider == "jina":
        return await _jina_embed(texts, task="retrieval.passage")
    return await asyncio.to_thread(_local_encode_passages, texts)


async def encode_query(text: str) -> list[float]:
    """
    Encode a single user query for retrieval.

    With provider=jina: HTTP call to the Jina API.
    With provider=local: runs sentence-transformers in a thread pool.
    """
    if settings.embedding_provider == "jina":
        results = await _jina_embed([text], task="retrieval.query")
        return results[0]
    return await asyncio.to_thread(_local_encode_query, text)
