from __future__ import annotations

import argparse

import anyio
import structlog

from mcp_sentinel import __version__
from mcp_sentinel.config import Settings
from mcp_sentinel.logging import configure_logging
from mcp_sentinel.proxy.sentinel_server import run_stdio_proxy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-sentinel",
        description="ToolchainGate MCP passthrough proxy entrypoint.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--print-settings", action="store_true", help="Print resolved settings and exit"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

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
