import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

logger = logging.getLogger(__name__)

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.ask import router as ask_router
from src.api.routes.documents import router as documents_router
from src.api.routes.health import router as health_router
from src.api.routes.search import router as search_router
from src.config import settings
from src.db.engine import async_session_factory, create_redis_client, engine
from src.embeddings.encoder import encode_query
from src.generation.llm import GroqClient, OllamaClient

_UPLOADS_DIR = Path("uploads")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _UPLOADS_DIR.mkdir(exist_ok=True)
    app.state.db_session_factory = async_session_factory
    app.state.redis = create_redis_client()
    # arq connection pool for enqueueing jobs — separate from the plain Redis
    # client used for other purposes (pub/sub, caching, etc.)
    app.state.arq_redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))

    # For the local provider, load the ~2 GB model weights into the process
    # singleton before the first request arrives so that /ask and /search do
    # not pay the cold-load cost (~10–30 s) on the first real call.
    # With the Jina provider there is nothing to warm up — the API is stateless.
    if settings.embedding_provider == "local":
        await encode_query("warmup")

    logger.info("Embedding provider: %s  model: %s",
                settings.embedding_provider,
                settings.jina_model if settings.embedding_provider == "jina"
                else "intfloat/multilingual-e5-large")

    # LLM client — selected at startup by LLM_PROVIDER; shared across requests.
    if settings.llm_provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
                "Add it to .env or set LLM_PROVIDER=ollama to use the local model."
            )
        if not settings.groq_model:
            raise RuntimeError(
                "LLM_PROVIDER=groq but GROQ_MODEL is not set. "
                "Add GROQ_MODEL=<model-name> to .env."
            )
        llm = GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)
        logger.info("LLM provider: Groq  model: %s", settings.groq_model)
    else:
        llm = OllamaClient(base_url=settings.ollama_url, model=settings.ollama_model)
        logger.info("LLM provider: Ollama  model: %s  url: %s",
                    settings.ollama_model, settings.ollama_url)
        # Warm up Ollama so the first /ask does not pay the model-load cost.
        asyncio.create_task(llm.warmup())
    app.state.llm = llm

    yield
    await app.state.arq_redis.aclose()
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title="Copiloto Normativo", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(ask_router)
