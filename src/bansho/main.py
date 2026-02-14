from __future__ import annotations

import argparse

import anyio
import structlog

from bansho import __version__
from bansho.cli import register_keys_subcommand, run_keys_command
from bansho.config import Settings
from bansho.logging import configure_logging
from bansho.proxy.bansho_server import run_stdio_proxy
from bansho.ui import run_dashboard_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bansho",
        description="Bansho MCP passthrough proxy entrypoint.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    serve_parser = subparsers.add_parser("serve", help="Start the MCP bansho proxy")
    serve_parser.add_argument(
        "--print-settings",
        action="store_true",
        help="Print resolved settings and exit",
    )

    dashboard_parser = subparsers.add_parser("dashboard", help="Start the audit dashboard")
    dashboard_parser.add_argument(
        "--print-settings",
        action="store_true",
        help="Print resolved dashboard settings and exit",
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

    if command == "dashboard":
        return _run_dashboard(args)

    if command != "serve":
        parser.error(f"Unknown command: {command}")
        return 2

    return _run_serve(args)


def _run_serve(args: argparse.Namespace) -> int:
    settings = Settings()
    configure_logging()
    log = structlog.get_logger("bansho")

    if args.print_settings:
        print(settings.model_dump_json(indent=2))
        return 0

    try:
        anyio.run(run_stdio_proxy, settings)
    except KeyboardInterrupt:
        log.info("bansho_shutdown")
    except Exception:
        log.exception("bansho_runtime_error")
        return 1

    return 0


def _run_dashboard(args: argparse.Namespace) -> int:
    settings = Settings()
    configure_logging()
    log = structlog.get_logger("bansho")

    if args.print_settings:
        print(
            {
                "dashboard_host": settings.dashboard_host,
                "dashboard_port": settings.dashboard_port,
                "postgres_dsn": str(settings.postgres_dsn),
            }
        )
        return 0

    try:
        run_dashboard_server(settings)
    except KeyboardInterrupt:
        log.info("dashboard_shutdown")
    except Exception:
        log.exception("dashboard_runtime_error")
        return 1

    return 0
