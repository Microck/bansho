from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.shared.context import RequestContext
from mcp.shared.exceptions import McpError

from mcp_sentinel.auth.api_keys import resolve_api_key

_UNAUTHORIZED_ERROR = types.ErrorData(code=401, message="Unauthorized")

RequestT = TypeVar("RequestT")


@dataclass(frozen=True, slots=True)
class AuthContext:
    api_key_id: str
    role: str


def require_api_key(
    server: Server[Any, Any],
    handler: Callable[[RequestT, AuthContext], Awaitable[types.ServerResult]],
) -> Callable[[RequestT], Awaitable[types.ServerResult]]:
    async def wrapped(request: RequestT) -> types.ServerResult:
        request_context = _get_request_context(server)
        auth_context = await authenticate_request(request_context)
        return await handler(request, auth_context)

    return wrapped


async def authenticate_request(
    request_context: RequestContext[Any, Any, Any] | None,
) -> AuthContext:
    presented_api_key = extract_api_key(request_context)
    if presented_api_key is None:
        raise McpError(_UNAUTHORIZED_ERROR)

    resolved = await resolve_api_key(presented_api_key)
    if resolved is None:
        raise McpError(_UNAUTHORIZED_ERROR)

    api_key_id = _normalize_string(resolved.get("api_key_id"))
    role = _normalize_string(resolved.get("role"))
    if api_key_id is None or role is None:
        raise McpError(_UNAUTHORIZED_ERROR)

    return AuthContext(api_key_id=api_key_id, role=role)


def extract_api_key(request_context: RequestContext[Any, Any, Any] | None) -> str | None:
    headers = _extract_headers(request_context)

    bearer_token = _extract_bearer_token(headers.get("authorization"))
    if bearer_token is not None:
        return bearer_token

    header_api_key = _normalize_string(headers.get("x-api-key"))
    if header_api_key is not None:
        return header_api_key

    query_params = _extract_query_params(request_context)
    return _normalize_string(query_params.get("api_key"))


def _get_request_context(server: Server[Any, Any]) -> RequestContext[Any, Any, Any] | None:
    try:
        return server.request_context
    except LookupError:
        return None


def _extract_headers(request_context: RequestContext[Any, Any, Any] | None) -> dict[str, str]:
    headers: dict[str, str] = {}

    if request_context is None:
        return headers

    if request_context.meta is not None:
        _merge_string_mapping(headers, _meta_entry(request_context.meta.model_extra, "headers"))

    request_headers = getattr(request_context.request, "headers", None)
    _merge_string_mapping(headers, request_headers)

    return headers


def _extract_query_params(request_context: RequestContext[Any, Any, Any] | None) -> dict[str, str]:
    query_params: dict[str, str] = {}

    if request_context is None:
        return query_params

    if request_context.meta is not None:
        _merge_string_mapping(query_params, _meta_entry(request_context.meta.model_extra, "query"))
        _merge_string_mapping(
            query_params,
            _meta_entry(request_context.meta.model_extra, "query_params"),
        )

    request_query_params = getattr(request_context.request, "query_params", None)
    _merge_string_mapping(query_params, request_query_params)

    return query_params


def _extract_bearer_token(authorization_header: str | None) -> str | None:
    normalized = _normalize_string(authorization_header)
    if normalized is None:
        return None

    parts = normalized.split(maxsplit=1)
    if len(parts) != 2:
        return None

    scheme, token = parts
    if scheme.lower() != "bearer":
        return None

    return _normalize_string(token)


def _merge_string_mapping(target: dict[str, str], source: object) -> None:
    if not isinstance(source, Mapping):
        return

    for key, value in source.items():
        normalized_key = _normalize_string(key)
        normalized_value = _normalize_string(value)

        if normalized_key is None or normalized_value is None:
            continue

        target[normalized_key.lower()] = normalized_value


def _meta_entry(meta: object, key: str) -> object:
    if not isinstance(meta, Mapping):
        return None

    return meta.get(key)


def _normalize_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    if not normalized:
        return None

    return normalized
