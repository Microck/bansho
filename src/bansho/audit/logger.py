from __future__ import annotations

from uuid import UUID, uuid4

from asyncpg import Pool

from bansho.audit.models import AuditEvent
from bansho.storage.postgres import get_postgres_pool

_INSERT_AUDIT_EVENT_SQL = """
INSERT INTO audit_events (
    id,
    ts,
    api_key_id,
    role,
    method,
    tool_name,
    request_json,
    response_json,
    status_code,
    latency_ms,
    decision
) VALUES (
    $1,
    $2,
    $3,
    $4,
    $5,
    $6,
    $7::jsonb,
    $8::jsonb,
    $9,
    $10,
    $11::jsonb
);
"""


class AuditLogger:
    def __init__(self, pool: Pool | None = None) -> None:
        self._pool = pool

    async def log_event(self, event: AuditEvent) -> None:
        pool = self._pool or await get_postgres_pool()
        (
            ts,
            api_key_id,
            role,
            method,
            tool_name,
            request_json,
            response_json,
            status_code,
            latency_ms,
            decision,
        ) = event.as_insert_values()

        async with pool.acquire() as connection:
            await connection.execute(
                _INSERT_AUDIT_EVENT_SQL,
                uuid4(),
                ts,
                _parse_api_key_id(api_key_id),
                role,
                method,
                tool_name,
                request_json,
                response_json,
                status_code,
                latency_ms,
                decision,
            )


def _parse_api_key_id(api_key_id: str | None) -> UUID | None:
    if api_key_id is None:
        return None

    try:
        return UUID(api_key_id)
    except (TypeError, ValueError, AttributeError):
        return None


__all__ = ["AuditLogger"]
