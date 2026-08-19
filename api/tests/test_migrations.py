import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import settings


def test_upgrade_head_runs_clean() -> None:
    """alembic upgrade head completes without error from a clean state."""
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.mark.asyncio
async def test_three_tables_exist() -> None:
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            table_names: list[str] = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
    finally:
        await engine.dispose()

    assert "documents" in table_names
    assert "chunks" in table_names
    assert "queries" in table_names


@pytest.mark.asyncio
async def test_chunks_has_vector_and_tsv_columns() -> None:
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            column_names: set[str] = await conn.run_sync(
                lambda sync_conn: {
                    col["name"]
                    for col in inspect(sync_conn).get_columns("chunks")
                }
            )
    finally:
        await engine.dispose()

    assert "embedding" in column_names
    assert "tsv" in column_names
