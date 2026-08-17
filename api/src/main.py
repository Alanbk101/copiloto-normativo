from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from src.api.routes.health import router as health_router
from src.db.engine import async_session_factory, create_redis_client, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.db_session_factory = async_session_factory
    app.state.redis = create_redis_client()
    yield
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title="Copiloto Normativo", lifespan=lifespan)
app.include_router(health_router)
