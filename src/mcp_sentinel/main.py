from __future__ import annotations

import argparse

import structlog

from mcp_sentinel.config import Settings
from mcp_sentinel.logging import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcp-sentinel", add_help=True)
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
        print(settings.model_dump())
        return 0

    log.info(
        "sentinel_startup_stub",
        listen_host=settings.sentinel_listen_host,
        listen_port=settings.sentinel_listen_port,
        upstream_transport=settings.upstream_transport,
    )
    print("mcp-sentinel-lite: scaffold complete (proxy logic not implemented yet)")
    return 0
