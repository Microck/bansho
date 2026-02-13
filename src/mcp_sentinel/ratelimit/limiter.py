from __future__ import annotations

import time
from dataclasses import dataclass

from mcp_sentinel.storage.redis import redis_eval

FIXED_WINDOW_INCR_SCRIPT = """
local current = redis.call("INCR", KEYS[1])
if current == 1 then
  redis.call("EXPIRE", KEYS[1], ARGV[1])
end
return current
""".strip()

_UNKNOWN_API_KEY_SEGMENT = "__unknown_key__"
_UNKNOWN_TOOL_SEGMENT = "__unknown_tool__"


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_s: int


async def check_api_key_limit(
    *,
    api_key_id: str,
    requests: int,
    window_seconds: int,
    now_s: int | None = None,
) -> RateLimitResult:
    current_epoch = _current_epoch(now_s)
    window_bucket = _window_bucket(current_epoch, window_seconds)
    key = api_key_rate_limit_key(api_key_id, window_bucket)
    return await _check_fixed_window_limit(
        key=key,
        requests=requests,
        window_seconds=window_seconds,
        current_epoch=current_epoch,
    )


async def check_tool_limit(
    *,
    api_key_id: str,
    tool_name: str,
    requests: int,
    window_seconds: int,
    now_s: int | None = None,
) -> RateLimitResult:
    current_epoch = _current_epoch(now_s)
    window_bucket = _window_bucket(current_epoch, window_seconds)
    key = tool_rate_limit_key(api_key_id, tool_name, window_bucket)
    return await _check_fixed_window_limit(
        key=key,
        requests=requests,
        window_seconds=window_seconds,
        current_epoch=current_epoch,
    )


def api_key_rate_limit_key(api_key_id: str, window_bucket: int) -> str:
    normalized_api_key = _normalize_segment(api_key_id, fallback=_UNKNOWN_API_KEY_SEGMENT)
    return f"rl:{normalized_api_key}:{window_bucket}"


def tool_rate_limit_key(api_key_id: str, tool_name: str, window_bucket: int) -> str:
    normalized_api_key = _normalize_segment(api_key_id, fallback=_UNKNOWN_API_KEY_SEGMENT)
    normalized_tool_name = _normalize_segment(tool_name, fallback=_UNKNOWN_TOOL_SEGMENT)
    return f"rl:{normalized_api_key}:{normalized_tool_name}:{window_bucket}"


async def _check_fixed_window_limit(
    *,
    key: str,
    requests: int,
    window_seconds: int,
    current_epoch: int,
) -> RateLimitResult:
    if requests <= 0:
        msg = "requests must be greater than 0"
        raise ValueError(msg)
    if window_seconds <= 0:
        msg = "window_seconds must be greater than 0"
        raise ValueError(msg)

    reset_s = _seconds_until_reset(current_epoch, window_seconds)
    raw_count = await redis_eval(FIXED_WINDOW_INCR_SCRIPT, keys=[key], args=[reset_s])
    current_count = int(raw_count)

    return RateLimitResult(
        allowed=current_count <= requests,
        remaining=max(requests - current_count, 0),
        reset_s=reset_s,
    )


def _window_bucket(current_epoch: int, window_seconds: int) -> int:
    if window_seconds <= 0:
        msg = "window_seconds must be greater than 0"
        raise ValueError(msg)
    return current_epoch // window_seconds


def _seconds_until_reset(current_epoch: int, window_seconds: int) -> int:
    remainder = current_epoch % window_seconds
    if remainder == 0:
        return window_seconds
    return window_seconds - remainder


def _current_epoch(now_s: int | None) -> int:
    if now_s is None:
        return int(time.time())
    return int(now_s)


def _normalize_segment(value: str, *, fallback: str) -> str:
    normalized = value.strip()
    if not normalized:
        return fallback
    return normalized


__all__ = [
    "FIXED_WINDOW_INCR_SCRIPT",
    "RateLimitResult",
    "api_key_rate_limit_key",
    "check_api_key_limit",
    "check_tool_limit",
    "tool_rate_limit_key",
]
