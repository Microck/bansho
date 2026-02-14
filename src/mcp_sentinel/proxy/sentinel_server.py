from __future__ import annotations

import os
import sys
from typing import Any

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError

from mcp_sentinel.config import Settings
from mcp_sentinel.middleware import AuthContext, authenticate_request
from mcp_sentinel.middleware.authz import authorize_tool
from mcp_sentinel.middleware.rate_limit import enforce_rate_limit
from mcp_sentinel.policy.loader import DEFAULT_POLICY_PATH, load_policy
from mcp_sentinel.policy.models import Policy
from mcp_sentinel.proxy.upstream import UpstreamConnector

_FORBIDDEN_ERROR = types.ErrorData(code=403, message="Forbidden")


def create_sentinel_server(connector: UpstreamConnector, *, policy: Policy) -> Server[Any, Any]:
    server = Server("mcp-sentinel-lite")

    async def handle_list_tools(req: types.ListToolsRequest) -> types.ServerResult:
        auth_context = await _authenticate(server)
        listed_tools = await connector.list_tools(req.params)
        filtered_tools = [
            tool
            for tool in listed_tools.tools
            if authorize_tool(policy, auth_context, tool.name).allowed
        ]
        return types.ServerResult(listed_tools.model_copy(update={"tools": filtered_tools}))

    async def handle_call_tool(req: types.CallToolRequest) -> types.ServerResult:
        auth_context = await _authenticate(server)
        tool_name = req.params.name

        _authorize_or_raise(policy, auth_context, tool_name)
        await enforce_rate_limit(policy, auth_context, tool_name)

        return types.ServerResult(
            await connector.call_tool(name=tool_name, arguments=req.params.arguments)
        )

    async def handle_list_resources(req: types.ListResourcesRequest) -> types.ServerResult:
        return types.ServerResult(await connector.list_resources(req.params))

    async def handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
        return types.ServerResult(await connector.read_resource(req.params.uri))

    async def handle_list_prompts(req: types.ListPromptsRequest) -> types.ServerResult:
        return types.ServerResult(await connector.list_prompts(req.params))

    async def handle_get_prompt(req: types.GetPromptRequest) -> types.ServerResult:
        return types.ServerResult(
            await connector.get_prompt(name=req.params.name, arguments=req.params.arguments)
        )

    server.request_handlers[types.ListToolsRequest] = handle_list_tools
    server.request_handlers[types.CallToolRequest] = handle_call_tool
    server.request_handlers[types.ListResourcesRequest] = handle_list_resources
    server.request_handlers[types.ReadResourceRequest] = handle_read_resource
    server.request_handlers[types.ListPromptsRequest] = handle_list_prompts
    server.request_handlers[types.GetPromptRequest] = handle_get_prompt

    return server


async def _authenticate(server: Server[Any, Any]) -> AuthContext:
    return await authenticate_request(_request_context(server))


def _request_context(server: Server[Any, Any]) -> Any | None:
    try:
        return server.request_context
    except LookupError:
        return None


def _authorize_or_raise(policy: Policy, auth_context: AuthContext, tool_name: str) -> None:
    decision = authorize_tool(policy, auth_context, tool_name)
    if not decision.allowed:
        raise McpError(_FORBIDDEN_ERROR)


def _upstream_target(settings: Settings) -> str:
    if settings.upstream_transport == "stdio":
        return settings.upstream_cmd
    return settings.upstream_url


async def run_stdio_proxy(settings: Settings | None = None) -> None:
    resolved_settings = settings or Settings()
    connector = UpstreamConnector(resolved_settings)
    policy_path = os.environ.get("SENTINEL_POLICY_PATH", str(DEFAULT_POLICY_PATH))
    policy = load_policy(policy_path)

    try:
        upstream_init = await connector.initialize()
        server = create_sentinel_server(connector, policy=policy)

        initialization_options = InitializationOptions(
            server_name=upstream_init.serverInfo.name,
            server_version=upstream_init.serverInfo.version,
            capabilities=upstream_init.capabilities,
            instructions=upstream_init.instructions,
        )

        print(
            "sentinel_proxy_start"
            f" listen_addr={resolved_settings.sentinel_listen_host}"
            f":{resolved_settings.sentinel_listen_port}"
            f" upstream_transport={resolved_settings.upstream_transport}"
            f" upstream_target={_upstream_target(resolved_settings)}",
            f" policy_path={policy_path}",
            file=sys.stderr,
            flush=True,
        )

        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, initialization_options)
    finally:
        await connector.aclose()
