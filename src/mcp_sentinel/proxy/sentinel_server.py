from __future__ import annotations

import sys
from typing import Any

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from mcp_sentinel.config import Settings
from mcp_sentinel.proxy.upstream import UpstreamConnector


def create_sentinel_server(connector: UpstreamConnector) -> Server[Any, Any]:
    server = Server("mcp-sentinel-lite")

    async def handle_list_tools(req: types.ListToolsRequest) -> types.ServerResult:
        return types.ServerResult(await connector.list_tools(req.params))

    async def handle_call_tool(req: types.CallToolRequest) -> types.ServerResult:
        return types.ServerResult(
            await connector.call_tool(name=req.params.name, arguments=req.params.arguments)
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


def _upstream_target(settings: Settings) -> str:
    if settings.upstream_transport == "stdio":
        return settings.upstream_cmd
    return settings.upstream_url


async def run_stdio_proxy(settings: Settings | None = None) -> None:
    resolved_settings = settings or Settings()
    connector = UpstreamConnector(resolved_settings)

    try:
        upstream_init = await connector.initialize()
        server = create_sentinel_server(connector)

        initialization_options = InitializationOptions(
            server_name=upstream_init.serverInfo.name,
            server_version=upstream_init.serverInfo.version,
            capabilities=upstream_init.capabilities,
            instructions=upstream_init.instructions,
        )

        print(
            "sentinel_proxy_start"
            f" listen_addr={resolved_settings.sentinel_listen_host}:{resolved_settings.sentinel_listen_port}"
            f" upstream_transport={resolved_settings.upstream_transport}"
            f" upstream_target={_upstream_target(resolved_settings)}",
            file=sys.stderr,
            flush=True,
        )

        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, initialization_options)
    finally:
        await connector.aclose()
