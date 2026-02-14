from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any, cast

from redis.asyncio import Redis

from bansho.config import Settings

RedisValue = str | bytes | int | float

_redis_client: Redis | None = None
_redis_lock = asyncio.Lock()


async def get_redis() -> Redis:
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    async with _redis_lock:
        if _redis_client is None:
            settings = Settings()
            _redis_client = Redis.from_url(str(settings.redis_url))

    return _redis_client


async def close_redis() -> None:
    global _redis_client

    if _redis_client is None:
        return

    await _redis_client.aclose()
    _redis_client = None


async def ping_redis() -> bool:
    redis = await get_redis()
    return bool(await redis.ping())


async def redis_get(key: str) -> bytes | None:
    redis = await get_redis()
    value = await redis.get(key)
    return cast(bytes | None, value)


async def redis_set(key: str, value: RedisValue, ex: int | None = None) -> bool:
    redis = await get_redis()
    return bool(await redis.set(key, value, ex=ex))


async def redis_incr(key: str, amount: int = 1) -> int:
    redis = await get_redis()
    return int(await redis.incr(key, amount))


async def redis_expire(key: str, seconds: int) -> bool:
    redis = await get_redis()
    return bool(await redis.expire(key, seconds))


async def redis_eval(
    script: str,
    keys: Sequence[str] | None = None,
    args: Sequence[RedisValue] | None = None,
) -> Any:
    redis = await get_redis()
    key_list = list(keys or [])
    arg_list = list(args or [])
    return await redis.eval(script, len(key_list), *key_list, *arg_list)
