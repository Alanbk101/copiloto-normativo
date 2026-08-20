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
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import settings
from src.db.engine import get_db_session
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
async def client(db_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
