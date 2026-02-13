from __future__ import annotations

from asyncpg import Pool

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
        method text NOT NULL,
        tool_name text NOT NULL,
        request_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        response_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        status_code integer NOT NULL,
        latency_ms integer NOT NULL CHECK (latency_ms >= 0)
    );
    """,
)


async def bootstrap_schema(pool: Pool) -> None:
    async with pool.acquire() as connection:
        for statement in SCHEMA_STATEMENTS:
            await connection.execute(statement)
