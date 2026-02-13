from __future__ import annotations

from dataclasses import dataclass

import mcp.types as types
from mcp.shared.exceptions import McpError

from mcp_sentinel.middleware.auth import AuthContext
from mcp_sentinel.policy.models import Policy, RateLimitWindow, ToolRateLimitPolicy
from mcp_sentinel.ratelimit import RateLimitResult, check_api_key_limit, check_tool_limit

_TOO_MANY_REQUESTS_ERROR = types.ErrorData(code=429, message="Too Many Requests")
_DEFAULT_PER_API_KEY_LIMIT = RateLimitWindow(requests=60, window_seconds=60)
_DEFAULT_PER_TOOL_LIMIT = RateLimitWindow(requests=20, window_seconds=60)
_UNKNOWN_TOOL_NAME = "__unknown_tool__"


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    per_api_key: RateLimitResult
    per_tool: RateLimitResult
    tool_name: str


async def enforce_rate_limit(
    policy: Policy | None,
    auth_ctx: AuthContext,
    tool_name: str,
    *,
    now_s: int | None = None,
) -> RateLimitDecision:
    normalized_tool_name = _normalize_tool_name(tool_name)
    per_api_key_window = _resolve_per_api_key_limit(policy)
    per_tool_window = _resolve_per_tool_limit(policy, normalized_tool_name)

    per_api_key_result = await check_api_key_limit(
        api_key_id=auth_ctx.api_key_id,
        requests=per_api_key_window.requests,
        window_seconds=per_api_key_window.window_seconds,
        now_s=now_s,
    )
    if not per_api_key_result.allowed:
        raise McpError(_TOO_MANY_REQUESTS_ERROR)

    per_tool_result = await check_tool_limit(
        api_key_id=auth_ctx.api_key_id,
        tool_name=normalized_tool_name,
        requests=per_tool_window.requests,
        window_seconds=per_tool_window.window_seconds,
        now_s=now_s,
    )
    if not per_tool_result.allowed:
        raise McpError(_TOO_MANY_REQUESTS_ERROR)

    return RateLimitDecision(
        per_api_key=per_api_key_result,
        per_tool=per_tool_result,
        tool_name=normalized_tool_name,
    )


def _resolve_per_api_key_limit(policy: Policy | None) -> RateLimitWindow:
    rate_limits = getattr(policy, "rate_limits", None)
    per_api_key = getattr(rate_limits, "per_api_key", None)
    if isinstance(per_api_key, RateLimitWindow):
        return per_api_key
    return _DEFAULT_PER_API_KEY_LIMIT


def _resolve_per_tool_limit(policy: Policy | None, tool_name: str) -> RateLimitWindow:
    rate_limits = getattr(policy, "rate_limits", None)
    per_tool = getattr(rate_limits, "per_tool", None)
    if isinstance(per_tool, ToolRateLimitPolicy):
        return per_tool.for_tool(tool_name)
    return _DEFAULT_PER_TOOL_LIMIT


def _normalize_tool_name(tool_name: str) -> str:
    normalized = tool_name.strip()
    if normalized:
        return normalized
    return _UNKNOWN_TOOL_NAME


__all__ = ["RateLimitDecision", "enforce_rate_limit"]
