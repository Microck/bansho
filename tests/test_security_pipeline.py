from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypeVar

import mcp.types as types
import pytest
from mcp.server.lowlevel.server import request_ctx
from mcp.shared.context import RequestContext
from mcp.shared.exceptions import McpError

from bansho.middleware import auth as auth_middleware
from bansho.policy.models import Policy
from bansho.proxy.bansho_server import create_bansho_server
from bansho.ratelimit import limiter as limiter_module

RequestType = TypeVar("RequestType")


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
        return types.ReadResourceResult(
            contents=[types.TextResourceContents(uri=uri, mimeType="text/plain", text="")]
        )

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
def security_policy() -> Policy:
    return Policy.model_validate(
        {
            "roles": {
                "admin": {"allow": ["public.echo", "admin.delete"]},
                "user": {"allow": ["public.echo"]},
                "readonly": {"allow": []},
            },
            "rate_limits": {
                "per_api_key": {"requests": 10, "window_seconds": 60},
                "per_tool": {
                    "default": {"requests": 10, "window_seconds": 60},
                    "overrides": {
                        "public.echo": {"requests": 1, "window_seconds": 60},
                    },
                },
            },
        }
    )


@pytest.fixture
def patch_api_key_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_resolve_api_key(presented_key: str) -> dict[str, str] | None:
        if presented_key == "disallowed-key":
            return {"api_key_id": "key-disallowed", "role": "user"}
        if presented_key == "limited-key":
            return {"api_key_id": "key-limited", "role": "user"}
        if presented_key == "allowed-key":
            return {"api_key_id": "key-allowed", "role": "user"}
        return None

    monkeypatch.setattr(auth_middleware, "resolve_api_key", fake_resolve_api_key)


@pytest.fixture
def fake_redis_eval(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    counters: dict[str, int] = {}

    async def fake_eval(
        _script: str,
        keys: Sequence[str] | None = None,
        args: Sequence[str | bytes | int | float] | None = None,
    ) -> int:
        key_list = list(keys or [])
        _ = args
        assert len(key_list) == 1

        key = key_list[0]
        counters[key] = counters.get(key, 0) + 1
        return counters[key]

    monkeypatch.setattr(limiter_module, "redis_eval", fake_eval)
    monkeypatch.setattr(limiter_module.time, "time", lambda: 120.0)
    return counters


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


@pytest.mark.anyio
async def test_security_pipeline_prevents_bypass_and_only_forwards_allowed_requests(
    connector: FakeUpstreamConnector,
    security_policy: Policy,
    patch_api_key_resolution: None,
    fake_redis_eval: dict[str, int],
) -> None:
    _ = patch_api_key_resolution
    server = create_bansho_server(connector, policy=security_policy)
    call_handler = server.request_handlers[types.CallToolRequest]

    disallowed_request = types.CallToolRequest(
        params=types.CallToolRequestParams(name="admin.delete", arguments={"text": "x"})
    )
    allowed_request = types.CallToolRequest(
        params=types.CallToolRequestParams(name="public.echo", arguments={"text": "ok"})
    )

    status_code, result = await _invoke_with_status(
        context=_build_request_context(None),
        handler=call_handler,
        request=allowed_request,
    )
    assert status_code == 401
    assert result is None
    assert connector.call_count == 0

    status_code, result = await _invoke_with_status(
        context=_build_request_context("disallowed-key"),
        handler=call_handler,
        request=disallowed_request,
    )
    assert status_code == 403
    assert result is None
    assert connector.call_count == 0

    window_seconds = security_policy.rate_limits.per_tool.for_tool("public.echo").window_seconds
    window_bucket = int(limiter_module.time.time()) // window_seconds
    limited_tool_key = limiter_module.tool_rate_limit_key(
        api_key_id="key-limited",
        tool_name="public.echo",
        window_bucket=window_bucket,
    )
    fake_redis_eval[limited_tool_key] = security_policy.rate_limits.per_tool.for_tool(
        "public.echo"
    ).requests

    status_code, result = await _invoke_with_status(
        context=_build_request_context("limited-key"),
        handler=call_handler,
        request=allowed_request,
    )
    assert status_code == 429
    assert result is None
    assert connector.call_count == 0

    status_code, result = await _invoke_with_status(
        context=_build_request_context("allowed-key"),
        handler=call_handler,
        request=allowed_request,
    )
    assert status_code == 200
    assert result is not None
    assert isinstance(result.root, types.CallToolResult)
    assert result.root.isError is False
    assert connector.call_count == 1
