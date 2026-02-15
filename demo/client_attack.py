from __future__ import annotations

import argparse
import sys
from pathlib import Path

import anyio
import mcp.types as types
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_TOOL_NAME = "delete_customer"
SERVER_COMMAND = ["run", "python", "demo/vulnerable_server.py"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demonstrate unauthorized MCP tool access.")
    parser.add_argument(
        "--list-tools-only",
        action="store_true",
        help="Only list available tools from the vulnerable server.",
    )
    return parser.parse_args(argv)


async def run_attack_demo(list_tools_only: bool) -> None:
    params = StdioServerParameters(
        command="uv",
        args=SERVER_COMMAND,
        cwd=str(PROJECT_ROOT),
    )

    print("[1/4] Spawning vulnerable MCP server over stdio...")
    shutdown_clean = False
    try:
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                print("[2/4] Connected. Initializing MCP session...")
                await session.initialize()

                print("[3/4] Listing exposed tools (no API key provided)...")
                tools_result = await session.list_tools()
                tool_names = [tool.name for tool in tools_result.tools]
                print(f"Exposed tools: {', '.join(tool_names)}")

                if not tool_names:
                    raise RuntimeError("No tools returned by vulnerable server.")

                if list_tools_only:
                    print("List-tools smoke mode passed.")
                else:
                    if SENSITIVE_TOOL_NAME not in tool_names:
                        raise RuntimeError(
                            f"Sensitive tool '{SENSITIVE_TOOL_NAME}' was not exposed."
                        )

                    print(
                        f"[4/4] Calling sensitive tool '{SENSITIVE_TOOL_NAME}' without credentials..."
                    )
                    response = await session.send_request(
                        types.ClientRequest(
                            types.CallToolRequest(
                                params=types.CallToolRequestParams(
                                    name=SENSITIVE_TOOL_NAME,
                                    arguments={"customer_id": "cust_victim_42"},
                                )
                            )
                        ),
                        types.CallToolResult,
                    )

                    if response.isError:
                        raise RuntimeError("Sensitive tool returned an error unexpectedly.")

                    text_output = ""
                    if response.content and isinstance(response.content[0], types.TextContent):
                        text_output = response.content[0].text

                    if not text_output.strip():
                        raise RuntimeError("Sensitive tool response was empty.")

                    print("UNAUTHORIZED CALL SUCCEEDED")
                    print(f"Tool response: {text_output}")
                    print("Before-state demo complete: no auth controls blocked the action.")

        shutdown_clean = True
    finally:
        if shutdown_clean:
            print("Server subprocess terminated cleanly.")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        anyio.run(run_attack_demo, args.list_tools_only)
    except Exception as exc:
        print(f"Attack demo failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
