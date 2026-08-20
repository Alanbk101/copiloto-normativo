from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI

from src.api.routes.documents import router as documents_router
from src.api.routes.health import router as health_router
from src.db.engine import async_session_factory, create_redis_client, engine

_UPLOADS_DIR = Path("uploads")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _UPLOADS_DIR.mkdir(exist_ok=True)
    app.state.db_session_factory = async_session_factory
    app.state.redis = create_redis_client()
    yield
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title="Copiloto Normativo", lifespan=lifespan)
app.include_router(health_router)
app.include_router(documents_router)
