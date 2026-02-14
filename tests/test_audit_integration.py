from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypeVar, cast
from uuid import UUID

import mcp.types as types
import pytest
from asyncpg import Pool
from mcp.server.lowlevel.server import request_ctx
from mcp.shared.context import RequestContext
from mcp.shared.exceptions import McpError

from mcp_sentinel.middleware import auth as auth_middleware
from mcp_sentinel.policy.models import Policy
from mcp_sentinel.proxy.sentinel_server import create_sentinel_server
from mcp_sentinel.ratelimit import limiter as limiter_module
from mcp_sentinel.storage.postgres import get_postgres_pool
from mcp_sentinel.storage.schema import bootstrap_schema

RequestType = TypeVar("RequestType")

_DENIED_KEY_ID = UUID("00000000-0000-0000-0000-000000000101")
_ALLOWED_KEY_ID = UUID("00000000-0000-0000-0000-000000000202")


class FakeUpstreamConnector:
    def __init__(self) -> None:
        self.call_count = 0

    async def list_tools(
        self,
        _params: types.PaginatedRequestParams | None = None,
    ) -> types.ListToolsResult:
        return types.ListToolsResult(tools=[])

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> types.CallToolResult:
        self.call_count += 1
        text = str((arguments or {}).get("text", ""))
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"{name}:{text}")],
            isError=False,
        )

    async def list_resources(
        self,
        _params: types.PaginatedRequestParams | None = None,
    ) -> types.ListResourcesResult:
        return types.ListResourcesResult(resources=[])

    async def read_resource(self, uri: str) -> types.ReadResourceResult:
        contents: list[types.TextResourceContents | types.BlobResourceContents] = [
            types.TextResourceContents(
                uri=cast(Any, uri),
                mimeType="text/plain",
                text="",
            )
        ]
        return types.ReadResourceResult(contents=contents)

    async def list_prompts(
        self,
        _params: types.PaginatedRequestParams | None = None,
    ) -> types.ListPromptsResult:
        return types.ListPromptsResult(prompts=[])

    async def get_prompt(
        self,
        name: str,
        arguments: dict[str, str] | None = None,
    ) -> types.GetPromptResult:
        _ = (name, arguments)
        return types.GetPromptResult(description="", messages=[])


@pytest.fixture
def connector() -> FakeUpstreamConnector:
    return FakeUpstreamConnector()


@pytest.fixture
def audit_policy() -> Policy:
    return Policy.model_validate(
        {
            "roles": {
                "admin": {"allow": ["public.echo", "admin.delete"]},
                "user": {"allow": ["public.echo"]},
                "readonly": {"allow": []},
            },
            "rate_limits": {
                "per_api_key": {"requests": 60, "window_seconds": 60},
                "per_tool": {
                    "default": {"requests": 30, "window_seconds": 60},
                    "overrides": {},
                },
            },
        }
    )


@pytest.fixture
def patch_api_key_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_resolve_api_key(presented_key: str) -> dict[str, str] | None:
        if presented_key == "denied-key":
            return {"api_key_id": str(_DENIED_KEY_ID), "role": "user"}
        if presented_key == "allowed-key":
            return {"api_key_id": str(_ALLOWED_KEY_ID), "role": "user"}
        return None

    monkeypatch.setattr(auth_middleware, "resolve_api_key", fake_resolve_api_key)


@pytest.fixture
def patch_rate_limit_eval(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_eval(
        _script: str,
        keys: Sequence[str] | None = None,
        args: Sequence[str | bytes | int | float] | None = None,
    ) -> int:
        _ = (keys, args)
        return 1

    monkeypatch.setattr(limiter_module, "redis_eval", fake_eval)


@pytest.fixture
async def postgres_pool() -> Pool:
    pool = await get_postgres_pool()
    await bootstrap_schema(pool)

    async with pool.acquire() as connection:
        await connection.execute("TRUNCATE TABLE audit_events, api_keys CASCADE;")
        await connection.execute(
            """
            INSERT INTO api_keys (id, key_hash, role)
            VALUES ($1, $2, $3), ($4, $5, $6);
            """,
            _DENIED_KEY_ID,
            "hash-denied",
            "user",
            _ALLOWED_KEY_ID,
            "hash-allowed",
            "user",
        )

    return pool


def _build_request_context(api_key: str | None) -> RequestContext[Any, Any, Any]:
    meta_payload: dict[str, object] = {}
    if api_key is not None:
        meta_payload["headers"] = {"x-api-key": api_key}

    return RequestContext(
        request_id=1,
        meta=types.RequestParams.Meta.model_validate(meta_payload),
        session=object(),
        lifespan_context=object(),
        experimental=object(),
        request=None,
        close_sse_stream=None,
        close_standalone_sse_stream=None,
    )


async def _call_with_context(
    *,
    context: RequestContext[Any, Any, Any],
    handler: Callable[[RequestType], Awaitable[types.ServerResult]],
    request: RequestType,
) -> types.ServerResult:
    token = request_ctx.set(context)
    try:
        return await handler(request)
    finally:
        request_ctx.reset(token)


async def _invoke_with_status(
    *,
    context: RequestContext[Any, Any, Any],
    handler: Callable[[types.CallToolRequest], Awaitable[types.ServerResult]],
    request: types.CallToolRequest,
) -> tuple[int, types.ServerResult | None]:
    try:
        result = await _call_with_context(context=context, handler=handler, request=request)
    except McpError as exc:
        return exc.error.code, None

    return 200, result


def _parse_json_column(value: object) -> dict[str, Any]:
    if isinstance(value, str):
        loaded = json.loads(value)
        assert isinstance(loaded, dict)
        return loaded

    assert isinstance(value, dict)
    return value


@pytest.mark.anyio
async def test_audit_rows_written_for_401_403_and_200_call_paths(
    connector: FakeUpstreamConnector,
    audit_policy: Policy,
    patch_api_key_resolution: None,
    patch_rate_limit_eval: None,
    postgres_pool: Pool,
) -> None:
    _ = (patch_api_key_resolution, patch_rate_limit_eval)

    server = create_sentinel_server(cast(Any, connector), policy=audit_policy)
    call_handler = server.request_handlers[types.CallToolRequest]

    status_code, _ = await _invoke_with_status(
        context=_build_request_context(None),
        handler=call_handler,
        request=types.CallToolRequest(
            params=types.CallToolRequestParams(name="public.echo", arguments={"text": "no-auth"})
        ),
    )
    assert status_code == 401

    status_code, _ = await _invoke_with_status(
        context=_build_request_context("denied-key"),
        handler=call_handler,
        request=types.CallToolRequest(
            params=types.CallToolRequestParams(name="admin.delete", arguments={"text": "x"})
        ),
    )
    assert status_code == 403

    status_code, result = await _invoke_with_status(
        context=_build_request_context("allowed-key"),
        handler=call_handler,
        request=types.CallToolRequest(
            params=types.CallToolRequestParams(name="public.echo", arguments={"text": "ok"})
        ),
    )
    assert status_code == 200
    assert result is not None
    assert connector.call_count == 1

    async with postgres_pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT status_code, method, tool_name, response_json, decision, latency_ms
            FROM audit_events
            ORDER BY ts ASC;
            """
        )

    assert len(rows) == 3
    rows_by_status = {int(row["status_code"]): row for row in rows}
    assert set(rows_by_status) == {200, 401, 403}

    unauthorized = rows_by_status[401]
    unauthorized_response = _parse_json_column(unauthorized["response_json"])
    unauthorized_decision = _parse_json_column(unauthorized["decision"])
    assert unauthorized["method"] == "TOOLS/CALL"
    assert unauthorized["tool_name"] == "public.echo"
    assert unauthorized["latency_ms"] >= 0
    assert set(unauthorized_response) == {"error"}
    assert set(unauthorized_response["error"]) == {"code", "message"}
    assert unauthorized_response["error"] == {
        "code": 401,
        "message": "Unauthorized",
    }
    assert unauthorized_decision["auth"]["allowed"] is False
    assert unauthorized_decision["auth"]["reason"] == "unauthorized"
    assert unauthorized_decision["authz"]["reason"] == "not_evaluated"
    assert unauthorized_decision["rate"]["reason"] == "not_evaluated"

    forbidden = rows_by_status[403]
    forbidden_response = _parse_json_column(forbidden["response_json"])
    forbidden_decision = _parse_json_column(forbidden["decision"])
    assert forbidden["method"] == "TOOLS/CALL"
    assert forbidden["tool_name"] == "admin.delete"
    assert forbidden["latency_ms"] >= 0
    assert set(forbidden_response) == {"error"}
    assert set(forbidden_response["error"]) == {"code", "message"}
    assert forbidden_response["error"] == {
        "code": 403,
        "message": "Forbidden",
    }
    assert forbidden_decision["auth"]["allowed"] is True
    assert forbidden_decision["authz"]["allowed"] is False
    assert forbidden_decision["authz"]["reason"] == "tool_not_allowed_for_role"
    assert forbidden_decision["rate"]["reason"] == "not_evaluated"

    allowed = rows_by_status[200]
    allowed_response = _parse_json_column(allowed["response_json"])
    allowed_decision = _parse_json_column(allowed["decision"])
    assert allowed["method"] == "TOOLS/CALL"
    assert allowed["tool_name"] == "public.echo"
    assert allowed["latency_ms"] >= 0
    assert allowed_response["isError"] is False
    assert allowed_decision["auth"]["allowed"] is True
    assert allowed_decision["authz"]["allowed"] is True
    assert allowed_decision["rate"]["allowed"] is True
    assert allowed_decision["rate"]["per_api_key"]["allowed"] is True
    assert allowed_decision["rate"]["per_tool"]["allowed"] is True
