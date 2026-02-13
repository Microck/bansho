from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import mcp.types as types
import pytest
from mcp.server.lowlevel.server import request_ctx
from mcp.shared.context import RequestContext
from mcp.shared.exceptions import McpError

from mcp_sentinel.middleware import auth as auth_middleware
from mcp_sentinel.policy.models import Policy
from mcp_sentinel.proxy.sentinel_server import create_sentinel_server
from mcp_sentinel.ratelimit import limiter as limiter_module

RequestType = TypeVar("RequestType")


class FakeUpstreamConnector:
    def __init__(self) -> None:
        self.call_count = 0

    async def list_tools(
        self,
        _params: types.PaginatedRequestParams | None = None,
    ) -> types.ListToolsResult:
        return types.ListToolsResult(
            tools=[
                types.Tool(
                    name="public.echo",
                    description="Echo text",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                        },
                        "required": ["text"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="sensitive.delete",
                    description="Sensitive delete operation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "resource": {"type": "string"},
                        },
                        "required": ["resource"],
                        "additionalProperties": False,
                    },
                ),
            ]
        )

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> types.CallToolResult:
        self.call_count += 1
        payload = arguments or {}
        value = payload.get("resource") or payload.get("text") or ""
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"{name}:{value}")],
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


@pytest.fixture(autouse=True)
def patch_rate_limit_eval(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_eval(
        _script: str,
        keys: list[str] | None = None,
        args: list[str | bytes | int | float] | None = None,
    ) -> int:
        _ = (keys, args)
        return 1

    monkeypatch.setattr(limiter_module, "redis_eval", fake_eval)


@pytest.fixture
def authz_policy() -> Policy:
    return Policy.model_validate(
        {
            "roles": {
                "admin": {"allow": ["public.echo", "sensitive.delete"]},
                "user": {"allow": ["public.echo"]},
                "readonly": {"allow": ["public.echo"]},
            },
            "rate_limits": {
                "per_api_key": {"requests": 120, "window_seconds": 60},
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
        if presented_key == "readonly-key":
            return {"api_key_id": "key-readonly", "role": "readonly"}
        if presented_key == "user-key":
            return {"api_key_id": "key-user", "role": "user"}
        if presented_key == "admin-key":
            return {"api_key_id": "key-admin", "role": "admin"}
        return None

    monkeypatch.setattr(auth_middleware, "resolve_api_key", fake_resolve_api_key)


def _build_request_context(api_key: str) -> RequestContext[Any, Any, Any]:
    meta = types.RequestParams.Meta.model_validate(
        {
            "headers": {
                "x-api-key": api_key,
            }
        }
    )
    return RequestContext(
        request_id=1,
        meta=meta,
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


@pytest.mark.anyio
async def test_sensitive_tool_denied_for_readonly_and_user_allowed_for_admin(
    connector: FakeUpstreamConnector,
    authz_policy: Policy,
    patch_api_key_resolution: None,
) -> None:
    server = create_sentinel_server(connector, policy=authz_policy)
    call_handler = server.request_handlers[types.CallToolRequest]
    sensitive_call = types.CallToolRequest(
        params=types.CallToolRequestParams(name="sensitive.delete", arguments={"resource": "doc-1"})
    )

    with pytest.raises(McpError) as readonly_error:
        await _call_with_context(
            context=_build_request_context("readonly-key"),
            handler=call_handler,
            request=sensitive_call,
        )
    assert readonly_error.value.error.code == 403
    assert readonly_error.value.error.message == "Forbidden"

    with pytest.raises(McpError) as user_error:
        await _call_with_context(
            context=_build_request_context("user-key"),
            handler=call_handler,
            request=sensitive_call,
        )
    assert user_error.value.error.code == 403
    assert user_error.value.error.message == "Forbidden"

    admin_result = await _call_with_context(
        context=_build_request_context("admin-key"),
        handler=call_handler,
        request=sensitive_call,
    )
    assert isinstance(admin_result.root, types.CallToolResult)
    assert admin_result.root.isError is False
    assert connector.call_count == 1


@pytest.mark.anyio
async def test_tools_list_hides_sensitive_tool_for_readonly_and_user(
    connector: FakeUpstreamConnector,
    authz_policy: Policy,
    patch_api_key_resolution: None,
) -> None:
    server = create_sentinel_server(connector, policy=authz_policy)
    list_handler = server.request_handlers[types.ListToolsRequest]

    readonly_result = await _call_with_context(
        context=_build_request_context("readonly-key"),
        handler=list_handler,
        request=types.ListToolsRequest(),
    )
    assert isinstance(readonly_result.root, types.ListToolsResult)
    assert {tool.name for tool in readonly_result.root.tools} == {"public.echo"}

    user_result = await _call_with_context(
        context=_build_request_context("user-key"),
        handler=list_handler,
        request=types.ListToolsRequest(),
    )
    assert isinstance(user_result.root, types.ListToolsResult)
    assert {tool.name for tool in user_result.root.tools} == {"public.echo"}

    admin_result = await _call_with_context(
        context=_build_request_context("admin-key"),
        handler=list_handler,
        request=types.ListToolsRequest(),
    )
    assert isinstance(admin_result.root, types.ListToolsResult)
    assert {tool.name for tool in admin_result.root.tools} == {"public.echo", "sensitive.delete"}
