"""
Text encoder backed by intfloat/multilingual-e5-large (1024 dimensions).

e5 prefixing contract
---------------------
The model was trained with explicit prefixes that must be respected at
inference time — omitting them degrades retrieval quality significantly:

  - Passages to be indexed  →  "passage: <text>"
  - User queries at search time  →  "query: <text>"

Model loading
-------------
SentenceTransformer initialisation downloads ~2 GB and takes several
seconds.  The module-level singleton `_model` is initialised on the first
call to `_get_model()` and reused for every subsequent call.  In the
Docker worker the model directory is mounted from a named volume
(`HF_HOME=/model_cache`) so it is only downloaded once across rebuilds.

Thread safety
-------------
`encode()` is synchronous and CPU/GPU-bound.  The worker calls these
functions via `asyncio.to_thread` so the event loop is never blocked.
These functions themselves are intentionally plain (non-async) so they
can also be called directly from synchronous test code.
"""

from sentence_transformers import SentenceTransformer

_MODEL_NAME = "intfloat/multilingual-e5-large"
_EMBEDDING_DIM = 1024

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def encode_passages(texts: list[str]) -> list[list[float]]:
    """
    Encode a batch of document passages for indexing.

    Applies the required "passage: " prefix before encoding so that
    cosine similarity with query embeddings (encoded with "query: ") is
    meaningful.  Always processes the full batch in one call — never
    loops one text at a time.
    """
    prefixed = [f"passage: {t}" for t in texts]
    model = _get_model()
    embeddings = model.encode(prefixed, convert_to_numpy=True)
    return [vec.tolist() for vec in embeddings]


def encode_query(text: str) -> list[float]:
    """
    Encode a single user query for retrieval.

    Uses the "query: " prefix required by the e5 training objective.
    """
    model = _get_model()
    embedding = model.encode(f"query: {text}", convert_to_numpy=True)
    return embedding.tolist()
