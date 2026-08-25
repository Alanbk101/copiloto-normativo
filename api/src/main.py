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
    # LLM client — shared across requests; stateless (no connection pool to close)
    app.state.llm = OllamaClient(
        base_url=settings.ollama_url,
        model=settings.ollama_model,
    )
    yield
    await app.state.arq_redis.aclose()
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title="Copiloto Normativo", lifespan=lifespan)
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(ask_router)
