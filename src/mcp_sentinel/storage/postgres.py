from __future__ import annotations

import asyncio

import asyncpg
from asyncpg import Pool

from mcp_sentinel.config import Settings

_postgres_pool: Pool | None = None
_postgres_lock = asyncio.Lock()


async def get_postgres_pool() -> Pool:
    global _postgres_pool

    if _postgres_pool is not None:
        return _postgres_pool

    async with _postgres_lock:
        if _postgres_pool is None:
            settings = Settings()
            _postgres_pool = await asyncpg.create_pool(
                dsn=str(settings.postgres_dsn),
                min_size=1,
                max_size=10,
                timeout=10.0,
                command_timeout=30.0,
                max_inactive_connection_lifetime=300.0,
            )

    return _postgres_pool


async def close_postgres_pool() -> None:
    global _postgres_pool

    if _postgres_pool is None:
        return

    await _postgres_pool.close()
    _postgres_pool = None


async def ping_postgres() -> bool:
    pool = await get_postgres_pool()
    async with pool.acquire() as connection:
        value = await connection.fetchval("SELECT 1;")
    return value == 1


async def ensure_schema() -> None:
    from mcp_sentinel.storage.schema import bootstrap_schema

    pool = await get_postgres_pool()
    await bootstrap_schema(pool)
