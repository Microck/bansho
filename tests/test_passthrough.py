from __future__ import annotations

import textwrap
from pathlib import Path

import mcp.types as types
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

FAKE_UPSTREAM_SERVER = """
from __future__ import annotations

import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

server = Server("fake-upstream", version="1.0.0")


async def handle_list_tools(_req: types.ListToolsRequest) -> types.ServerResult:
    return types.ServerResult(
        types.ListToolsResult(
            tools=[
                types.Tool(
                    name="echo",
                    description="Echoes text back",
                    inputSchema={
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                        "additionalProperties": False,
                    },
                )
            ]
        )
    )


async def handle_call_tool(req: types.CallToolRequest) -> types.ServerResult:
    text = str((req.params.arguments or {}).get("text", ""))
    return types.ServerResult(
        types.CallToolResult(
            content=[types.TextContent(type="text", text=f"ECHO::{text}")],
            isError=False,
        )
    )


async def handle_list_resources(_req: types.ListResourcesRequest) -> types.ServerResult:
    return types.ServerResult(
        types.ListResourcesResult(
            resources=[
                types.Resource(
                    name="hello-resource",
                    uri="resource://hello.txt",
                    mimeType="text/plain",
                    description="Passthrough test resource",
                )
            ]
        )
    )


async def handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
    return types.ServerResult(
        types.ReadResourceResult(
            contents=[
                types.TextResourceContents(
                    uri=req.params.uri,
                    mimeType="text/plain",
                    text="resource body",
                )
            ]
        )
    )


async def handle_list_prompts(_req: types.ListPromptsRequest) -> types.ServerResult:
    return types.ServerResult(
        types.ListPromptsResult(
            prompts=[types.Prompt(name="summarize", description="Passthrough test prompt")]
        )
    )


async def handle_get_prompt(req: types.GetPromptRequest) -> types.ServerResult:
    topic = (req.params.arguments or {}).get("topic", "unknown")
    return types.ServerResult(
        types.GetPromptResult(
            description="Prompt payload",
            messages=[
                types.PromptMessage(
                    role="assistant",
                    content=types.TextContent(type="text", text=f"SUMMARIZE::{topic}"),
                )
            ],
        )
    )


server.request_handlers[types.ListToolsRequest] = handle_list_tools
server.request_handlers[types.CallToolRequest] = handle_call_tool
server.request_handlers[types.ListResourcesRequest] = handle_list_resources
server.request_handlers[types.ReadResourceRequest] = handle_read_resource
server.request_handlers[types.ListPromptsRequest] = handle_list_prompts
server.request_handlers[types.GetPromptRequest] = handle_get_prompt


async def run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(run)
"""


@pytest.mark.anyio
async def test_passthrough_tools_resources_and_prompts(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    upstream_script = tmp_path / "fake_upstream.py"
    upstream_script.write_text(textwrap.dedent(FAKE_UPSTREAM_SERVER), encoding="utf-8")

    sentinel_process = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "mcp_sentinel"],
        cwd=project_root,
        env={
            "UPSTREAM_TRANSPORT": "stdio",
            "UPSTREAM_CMD": f"uv run python {upstream_script}",
            "SENTINEL_LISTEN_HOST": "127.0.0.1",
            "SENTINEL_LISTEN_PORT": "9000",
        },
    )

    async with stdio_client(sentinel_process) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialize_result = await session.initialize()
            assert initialize_result.capabilities.tools is not None
            assert initialize_result.capabilities.resources is not None
            assert initialize_result.capabilities.prompts is not None

            tools_result = await session.list_tools()
            assert {tool.name for tool in tools_result.tools} == {"echo"}

            tool_result = await session.call_tool("echo", {"text": "hello"})
            assert tool_result.isError is False
            assert len(tool_result.content) == 1
            assert isinstance(tool_result.content[0], types.TextContent)
            assert tool_result.content[0].text == "ECHO::hello"

            resources_result = await session.list_resources()
            assert {str(resource.uri) for resource in resources_result.resources} == {
                "resource://hello.txt"
            }

            read_result = await session.read_resource("resource://hello.txt")
            assert len(read_result.contents) == 1
            assert isinstance(read_result.contents[0], types.TextResourceContents)
            assert read_result.contents[0].text == "resource body"
            assert str(read_result.contents[0].uri) == "resource://hello.txt"
            assert read_result.contents[0].mimeType == "text/plain"

            prompts_result = await session.list_prompts()
            assert {prompt.name for prompt in prompts_result.prompts} == {"summarize"}

            prompt_result = await session.get_prompt("summarize", {"topic": "alpha"})
            assert prompt_result.description == "Prompt payload"
            assert len(prompt_result.messages) == 1
            assert isinstance(prompt_result.messages[0].content, types.TextContent)
            assert prompt_result.messages[0].content.text == "SUMMARIZE::alpha"
