"""
arq WorkerSettings.

Run with:
    python -m arq src.worker.main.WorkerSettings

on_startup opens a dedicated SQLAlchemy engine for the worker process
(separate from the API's engine) and stores a session factory in ctx
so every job function can create its own sessions.

on_shutdown disposes the engine to close all pooled connections cleanly.
"""

from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import settings
from src.worker.jobs import process_document


async def on_startup(ctx: dict) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    ctx["engine"] = engine
    ctx["session_factory"] = async_sessionmaker(engine, expire_on_commit=False)


async def on_shutdown(ctx: dict) -> None:
    await ctx["engine"].dispose()


class WorkerSettings:
    functions = [process_document]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = on_startup
    on_shutdown = on_shutdown
    job_timeout = 1800  # 30 min — CPU inference on large docs can be slow
