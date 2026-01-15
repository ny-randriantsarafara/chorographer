"""Async PostgreSQL connection pool management."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from psycopg_pool import AsyncConnectionPool

from infrastructure.config import Settings


@asynccontextmanager
async def create_pool(settings: Settings) -> AsyncIterator[AsyncConnectionPool]:
    """Create and manage an async connection pool.

    Usage:
        async with create_pool(settings) as pool:
            async with pool.connection() as conn:
                await conn.execute(...)

    Args:
        settings: Application settings with PostgreSQL config

    Yields:
        Configured async connection pool
    """
    pool = AsyncConnectionPool(
        conninfo=settings.postgres_dsn,
        min_size=2,
        max_size=10,
        open=False,
    )

    try:
        await pool.open()
        yield pool
    finally:
        await pool.close()


async def get_pool(settings: Settings) -> AsyncConnectionPool:
    """Create a standalone connection pool (caller manages lifecycle).

    For long-running applications, prefer managing the pool lifecycle manually:

        pool = await get_pool(settings)
        try:
            # use pool...
        finally:
            await pool.close()

    Args:
        settings: Application settings with PostgreSQL config

    Returns:
        Opened async connection pool
    """
    pool = AsyncConnectionPool(
        conninfo=settings.postgres_dsn,
        min_size=2,
        max_size=10,
        open=False,
    )
    await pool.open()
    return pool
