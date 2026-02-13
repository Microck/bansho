from __future__ import annotations

from uuid import UUID, uuid4

from mcp_sentinel.auth.hash import generate_api_key, hash_api_key, verify_api_key
from mcp_sentinel.storage.postgres import get_postgres_pool

DEFAULT_API_KEY_ROLE = "readonly"


async def create_api_key(role: str = DEFAULT_API_KEY_ROLE) -> dict[str, str]:
    normalized_role = _normalize_role(role)
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    api_key_id = uuid4()

    pool = await get_postgres_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            "INSERT INTO api_keys (id, key_hash, role) VALUES ($1, $2, $3);",
            api_key_id,
            api_key_hash,
            normalized_role,
        )

    return {
        "api_key": api_key,
        "api_key_id": str(api_key_id),
    }


async def resolve_api_key(presented_key: str) -> dict[str, str] | None:
    if not presented_key:
        return None

    pool = await get_postgres_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            "SELECT id, key_hash, role FROM api_keys WHERE revoked_at IS NULL;"
        )

    resolved: dict[str, str] | None = None
    for row in rows:
        if verify_api_key(presented_key, row["key_hash"]):
            resolved = {
                "api_key_id": str(row["id"]),
                "role": str(row["role"]),
            }

    return resolved


async def revoke_api_key(api_key_id: str | UUID) -> bool:
    normalized_key_id = _normalize_api_key_id(api_key_id)
    if normalized_key_id is None:
        return False

    pool = await get_postgres_pool()
    async with pool.acquire() as connection:
        status = await connection.execute(
            """
            UPDATE api_keys
            SET revoked_at = NOW()
            WHERE id = $1 AND revoked_at IS NULL;
            """,
            normalized_key_id,
        )

    return _extract_updated_count(status) > 0


def _normalize_role(role: str) -> str:
    normalized = role.strip()
    if normalized:
        return normalized
    return DEFAULT_API_KEY_ROLE


def _normalize_api_key_id(api_key_id: str | UUID) -> UUID | None:
    if isinstance(api_key_id, UUID):
        return api_key_id

    try:
        return UUID(api_key_id)
    except (TypeError, ValueError, AttributeError):
        return None


def _extract_updated_count(status: str) -> int:
    try:
        return int(status.rsplit(" ", maxsplit=1)[-1])
    except (TypeError, ValueError):
        return 0
