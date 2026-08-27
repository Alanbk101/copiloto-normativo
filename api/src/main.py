import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI

from src.api.routes.ask import router as ask_router
from src.api.routes.documents import router as documents_router
from src.api.routes.health import router as health_router
from src.api.routes.search import router as search_router
from src.config import settings
from src.db.engine import async_session_factory, create_redis_client, engine
from src.embeddings.encoder import encode_query
from src.generation.llm import OllamaClient

_UPLOADS_DIR = Path("uploads")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _UPLOADS_DIR.mkdir(exist_ok=True)
    app.state.db_session_factory = async_session_factory
    app.state.redis = create_redis_client()
    # arq connection pool for enqueueing jobs — separate from the plain Redis
    # client used for other purposes (pub/sub, caching, etc.)
    app.state.arq_redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))

    # Warm up the sentence-transformer encoder.  encode_query is synchronous
    # and CPU-bound; running it here (in a thread, so the event loop stays
    # free) loads the ~2 GB model weights into the process singleton before
    # the first request arrives.  Without this, the first /ask or /search call
    # would pay the full load cost (~10–30 s) while holding a live request.
    # We await it — a few extra seconds at startup beats a frozen first request.
    await asyncio.to_thread(encode_query, "warmup")

    # LLM client — shared across requests; stateless (no connection pool to close)
    llm = OllamaClient(
        base_url=settings.ollama_url,
        model=settings.ollama_model,
    )
    app.state.llm = llm
    # Warm up Ollama in the background so the first /ask request does not pay
    # the model-load cost (~60–120 s on CPU).  Fire-and-forget: if Ollama is
    # not ready yet, warmup() swallows the error and the real call will work.
    asyncio.create_task(llm.warmup())

    yield
    await app.state.arq_redis.aclose()
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title="Copiloto Normativo", lifespan=lifespan)
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(ask_router)
