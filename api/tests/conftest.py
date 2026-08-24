"""
Test configuration.

Event loop / engine isolation
------------------------------
pytest-asyncio >= 0.24 creates a new event loop per test function by default.
SQLAlchemy's default QueuePool creates asyncio primitives (Lock, Future, …) the
first time a connection is requested, binding them to the running loop.  If the
engine is module-level (as in production src/db/engine.py), those primitives
survive across tests and explode in the next test's loop with "got Future
attached to a different loop".

Fix: each test gets a fresh AsyncEngine configured with NullPool.  NullPool
discards every connection on release so no asyncio primitives survive between
tests.  The engine is created inside the fixture, i.e. inside the test's own
event loop, so SQLAlchemy and asyncio always agree on which loop owns what.

The `client` fixture also overrides `get_db_session` so the app's routes use
the same test engine — cleanup and endpoint operations see the same database
state without any cross-loop surprises.

app.state mocks
---------------
ASGITransport does not run the app lifespan, so any attribute set in
`lifespan()` via `app.state.*` is absent during tests.  The `client` fixture
mirrors what the lifespan provides for everything that route handlers access:

  - db_session_factory  → real async_sessionmaker bound to the test engine
                          (so /health can open a session and run SELECT 1)
  - redis               → AsyncMock whose ping() returns True
                          (so /health sees redis as reachable)
  - arq_redis           → AsyncMock
                          (so POST /documents can call enqueue_job)
"""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import settings
from src.db.engine import get_db_session
from src.db.models import Document
from src.main import app


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def worker_ctx(db_engine: AsyncEngine) -> dict:
    """
    Minimal arq context dict for calling job functions directly in tests.
    Provides a session_factory bound to the test engine so jobs use the same
    database state as the rest of the test.
    """
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    return {"session_factory": factory}


@pytest.fixture
async def client(db_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override
    # Mirror the three app.state attributes set by the lifespan so that both
    # /health and POST /documents work without a running Redis or arq pool.
    app.state.db_session_factory = factory
    app.state.redis = AsyncMock()
    app.state.redis.ping.return_value = True
    app.state.arq_redis = AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    del app.state.db_session_factory
    del app.state.redis
    del app.state.arq_redis


@pytest.fixture(autouse=True)
async def cleanup_documents(db_session: AsyncSession) -> AsyncIterator[None]:
    """Delete all documents (and cascaded chunks) after every test that uses the DB."""
    yield
    await db_session.execute(delete(Document))
    await db_session.commit()
