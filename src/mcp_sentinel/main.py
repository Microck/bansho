from __future__ import annotations

import argparse

import anyio
import structlog

from mcp_sentinel import __version__
from mcp_sentinel.cli import register_keys_subcommand, run_keys_command
from mcp_sentinel.config import Settings
from mcp_sentinel.logging import configure_logging
from mcp_sentinel.proxy.sentinel_server import run_stdio_proxy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-sentinel",
        description="ToolchainGate MCP passthrough proxy entrypoint.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    serve_parser = subparsers.add_parser("serve", help="Start the MCP sentinel proxy")
    serve_parser.add_argument(
        "--print-settings",
        action="store_true",
        help="Print resolved settings and exit",
    )

    register_keys_subcommand(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if command is None:
        parser.print_help()
        return 0

    if command == "keys":
        return run_keys_command(args)

    if command != "serve":
        parser.error(f"Unknown command: {command}")
        return 2

    return _run_serve(args)


def _run_serve(args: argparse.Namespace) -> int:
    settings = Settings()
    configure_logging()
    log = structlog.get_logger("mcp-sentinel")

    if args.print_settings:
        print(settings.model_dump_json(indent=2))
        return 0

    try:
        anyio.run(run_stdio_proxy, settings)
    except KeyboardInterrupt:
        log.info("sentinel_shutdown")
    except Exception:
        log.exception("sentinel_runtime_error")
        return 1

    return 0
