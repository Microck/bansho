from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError

SENSITIVE_TOOL_NAME = "delete_customer"


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], str]

    def as_mcp_tool(self) -> types.Tool:
        return types.Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema,
        )


def _list_customers(_arguments: dict[str, Any]) -> str:
    return "Visible customers: cust_1001, cust_1002, cust_1003"


def _wipe_cache(arguments: dict[str, Any]) -> str:
    tenant = str(arguments.get("tenant", "global"))
    return f"Cache wipe completed for tenant '{tenant}'."


def _delete_customer(arguments: dict[str, Any]) -> str:
    customer_id = str(arguments.get("customer_id", "unknown"))
    return (
        f"WARNING: Deleted customer {customer_id} and permanently removed invoices, "
        "billing history, and support tickets."
    )


TOOL_DEFINITIONS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="list_customers",
        description="Lists customer IDs available in the CRM.",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        handler=_list_customers,
    ),
    ToolDefinition(
        name="wipe_cache",
        description="Wipes application cache for a tenant.",
        input_schema={
            "type": "object",
            "properties": {
                "tenant": {"type": "string"},
            },
            "required": ["tenant"],
            "additionalProperties": False,
        },
        handler=_wipe_cache,
    ),
    ToolDefinition(
        name=SENSITIVE_TOOL_NAME,
        description="Deletes a customer account and related records.",
        input_schema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
            },
            "required": ["customer_id"],
            "additionalProperties": False,
        },
        handler=_delete_customer,
    ),
)

TOOL_REGISTRY: dict[str, ToolDefinition] = {tool.name: tool for tool in TOOL_DEFINITIONS}


def build_server() -> Server[Any, Any]:
    server = Server("vulnerable-demo", version="0.1.0")

    async def handle_list_tools(_req: types.ListToolsRequest) -> types.ServerResult:
        return types.ServerResult(
            types.ListToolsResult(tools=[tool.as_mcp_tool() for tool in TOOL_DEFINITIONS])
        )

    async def handle_call_tool(req: types.CallToolRequest) -> types.ServerResult:
        tool = TOOL_REGISTRY.get(req.params.name)
        if tool is None:
            raise McpError(types.ErrorData(code=-32601, message=f"Unknown tool: {req.params.name}"))

        arguments = req.params.arguments or {}
        output = tool.handler(arguments)
        return types.ServerResult(
            types.CallToolResult(
                content=[types.TextContent(type="text", text=output)],
                isError=False,
            )
        )

    server.request_handlers[types.ListToolsRequest] = handle_list_tools
    server.request_handlers[types.CallToolRequest] = handle_call_tool
    return server


async def run_stdio_server() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run_self_test() -> int:
    tool_names = [tool.name for tool in TOOL_DEFINITIONS]
    print(f"registered_tools: {', '.join(tool_names)}")

    if len(tool_names) < 2:
        print("self-test error: expected at least 2 registered tools", file=sys.stderr)
        return 1

    if SENSITIVE_TOOL_NAME not in TOOL_REGISTRY:
        print(
            f"self-test error: missing sensitive tool '{SENSITIVE_TOOL_NAME}'",
            file=sys.stderr,
        )
        return 1

    scary_output = (
        TOOL_REGISTRY[SENSITIVE_TOOL_NAME].handler({"customer_id": "cust_demo_007"}).strip()
    )
    print(f"sensitive_tool_output: {scary_output}")

    if not scary_output:
        print("self-test error: sensitive tool output must be non-empty", file=sys.stderr)
        return 1

    lowered = scary_output.lower()
    if "warning" not in lowered and "deleted" not in lowered:
        print(
            "self-test error: sensitive tool output must look clearly dangerous",
            file=sys.stderr,
        )
        return 1

    print("self-test passed")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Intentionally vulnerable MCP demo server.")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Validate local tool registration and sensitive-tool output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.self_test:
        return run_self_test()

    anyio.run(run_stdio_server)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
