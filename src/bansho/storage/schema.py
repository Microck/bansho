from __future__ import annotations

from asyncpg import Pool

from bansho.storage.postgres import get_postgres_pool
from bansho.storage.redis import ping_redis

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS api_keys (
        id uuid PRIMARY KEY,
        key_hash text NOT NULL UNIQUE,
        role text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT NOW(),
        revoked_at timestamptz
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_events (
        id uuid PRIMARY KEY,
        ts timestamptz NOT NULL DEFAULT NOW(),
        api_key_id uuid REFERENCES api_keys(id) ON DELETE SET NULL,
        role text NOT NULL DEFAULT 'unknown',
        method text NOT NULL,
        tool_name text NOT NULL,
        request_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        response_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        decision jsonb NOT NULL DEFAULT '{}'::jsonb,
        status_code integer NOT NULL,
        latency_ms integer NOT NULL CHECK (latency_ms >= 0)
    );
    """,
    """
    ALTER TABLE audit_events
    ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'unknown';
    """,
    """
    ALTER TABLE audit_events
    ADD COLUMN IF NOT EXISTS decision jsonb NOT NULL DEFAULT '{}'::jsonb;
    """,
)


async def bootstrap_schema(pool: Pool) -> None:
    async with pool.acquire() as connection:
        for statement in SCHEMA_STATEMENTS:
            await connection.execute(statement)


async def storage_smoke_check() -> dict[str, bool]:
    redis_ok = False
    postgres_ok = False

    try:
        redis_ok = await ping_redis()
    except Exception:
        redis_ok = False

    try:
        pool = await get_postgres_pool()
        async with pool.acquire() as connection:
            postgres_ok = await connection.fetchval("SELECT 1;") == 1
    except Exception:
        postgres_ok = False

    return {
        "redis": redis_ok,
        "postgres": postgres_ok,
    }
