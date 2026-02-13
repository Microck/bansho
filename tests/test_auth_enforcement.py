from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import mcp.types as types
import pytest
from mcp.server.lowlevel.server import request_ctx
from mcp.shared.context import RequestContext
from mcp.shared.exceptions import McpError

from mcp_sentinel.middleware import auth as auth_middleware
from mcp_sentinel.proxy.sentinel_server import create_sentinel_server


class FakeUpstreamConnector:
    async def list_tools(
        self,
        _params: types.PaginatedRequestParams | None = None,
    ) -> types.ListToolsResult:
        return types.ListToolsResult(
            tools=[
                types.Tool(
                    name="echo",
                    description="Echo tool",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                        },
                        "required": ["text"],
                        "additionalProperties": False,
                    },
                )
            ]
        )

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> types.CallToolResult:
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
def patch_api_key_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_resolve_api_key(presented_key: str) -> dict[str, str] | None:
        if presented_key in {
            "valid-header-key",
            "valid-query-key",
            "valid-bearer-key",
        }:
            return {
                "api_key_id": "key-123",
                "role": "readonly",
            }
        return None

    monkeypatch.setattr(auth_middleware, "resolve_api_key", fake_resolve_api_key)


def _build_request_context(
    *,
    headers: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
) -> RequestContext[Any, Any, Any]:
    meta_payload: dict[str, object] = {}
    if headers is not None:
        meta_payload["headers"] = headers
    if query is not None:
        meta_payload["query"] = query

    meta = types.RequestParams.Meta.model_validate(meta_payload)
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
async def test_tools_list_and_call_reject_requests_without_api_key(
    connector: FakeUpstreamConnector,
    patch_api_key_resolution: None,
) -> None:
    server = create_sentinel_server(connector)

    list_handler = server.request_handlers[types.ListToolsRequest]
    call_handler = server.request_handlers[types.CallToolRequest]

    with pytest.raises(McpError) as list_error:
        await _call_with_context(
            context=_build_request_context(),
            handler=list_handler,
            request=types.ListToolsRequest(),
        )

    assert list_error.value.error.code == 401
    assert list_error.value.error.message == "Unauthorized"

    with pytest.raises(McpError) as call_error:
        await _call_with_context(
            context=_build_request_context(),
            handler=call_handler,
            request=types.CallToolRequest(
                params=types.CallToolRequestParams(name="echo", arguments={"text": "hi"})
            ),
        )

    assert call_error.value.error.code == 401
    assert call_error.value.error.message == "Unauthorized"


@pytest.mark.anyio
async def test_tools_list_and_call_succeed_with_valid_header_key(
    connector: FakeUpstreamConnector,
    patch_api_key_resolution: None,
) -> None:
    server = create_sentinel_server(connector)

    list_handler = server.request_handlers[types.ListToolsRequest]
    call_handler = server.request_handlers[types.CallToolRequest]

    context = _build_request_context(headers={"X-API-Key": "valid-header-key"})

    list_result = await _call_with_context(
        context=context,
        handler=list_handler,
        request=types.ListToolsRequest(),
    )
    assert isinstance(list_result.root, types.ListToolsResult)
    assert {tool.name for tool in list_result.root.tools} == {"echo"}

    call_result = await _call_with_context(
        context=context,
        handler=call_handler,
        request=types.CallToolRequest(
            params=types.CallToolRequestParams(name="echo", arguments={"text": "hello"})
        ),
    )
    assert isinstance(call_result.root, types.CallToolResult)
    assert call_result.root.isError is False
    assert len(call_result.root.content) == 1
    assert isinstance(call_result.root.content[0], types.TextContent)
    assert call_result.root.content[0].text == "echo:hello"


@pytest.mark.anyio
async def test_tools_list_succeeds_with_bearer_authorization_header(
    connector: FakeUpstreamConnector,
    patch_api_key_resolution: None,
) -> None:
    server = create_sentinel_server(connector)
    list_handler = server.request_handlers[types.ListToolsRequest]

    list_result = await _call_with_context(
        context=_build_request_context(headers={"Authorization": "Bearer valid-bearer-key"}),
        handler=list_handler,
        request=types.ListToolsRequest(),
    )

    assert isinstance(list_result.root, types.ListToolsResult)
    assert {tool.name for tool in list_result.root.tools} == {"echo"}


@pytest.mark.anyio
async def test_tools_list_succeeds_with_query_param_api_key(
    connector: FakeUpstreamConnector,
    patch_api_key_resolution: None,
) -> None:
    server = create_sentinel_server(connector)
    list_handler = server.request_handlers[types.ListToolsRequest]

    list_result = await _call_with_context(
        context=_build_request_context(query={"api_key": "valid-query-key"}),
        handler=list_handler,
        request=types.ListToolsRequest(),
    )

    assert isinstance(list_result.root, types.ListToolsResult)
    assert {tool.name for tool in list_result.root.tools} == {"echo"}


@pytest.mark.anyio
async def test_tools_list_rejects_invalid_api_key(
    connector: FakeUpstreamConnector,
    patch_api_key_resolution: None,
) -> None:
    server = create_sentinel_server(connector)
    list_handler = server.request_handlers[types.ListToolsRequest]

    with pytest.raises(McpError) as error:
        await _call_with_context(
            context=_build_request_context(headers={"X-API-Key": "invalid-key"}),
            handler=list_handler,
            request=types.ListToolsRequest(),
        )

    assert error.value.error.code == 401
    assert error.value.error.message == "Unauthorized"


RequestType = TypeVar("RequestType")
