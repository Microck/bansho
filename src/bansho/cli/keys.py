from __future__ import annotations

import argparse
import sys

import anyio

from bansho.auth.api_keys import (
    DEFAULT_API_KEY_ROLE,
    create_api_key,
    revoke_api_key,
)
from bansho.storage.postgres import (
    close_postgres_pool,
    ensure_schema,
    get_postgres_pool,
)

_ROLE_CHOICES = ("admin", "user", "readonly")


def register_keys_subcommand(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    keys_parser = subparsers.add_parser("keys", help="Manage API keys")
    _configure_keys_parser(keys_parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bansho keys",
        description="Create, list, and revoke API keys.",
    )
    _configure_keys_parser(parser)
    return parser


def run_keys_command(args: argparse.Namespace) -> int:
    return anyio.run(_run_keys_command, args)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_keys_command(args)


def _configure_keys_parser(parser: argparse.ArgumentParser) -> None:
    keys_subparsers = parser.add_subparsers(dest="keys_action", metavar="command")
    keys_subparsers.required = True

    create_parser = keys_subparsers.add_parser("create", help="Create an API key")
    create_parser.add_argument(
        "--role",
        choices=_ROLE_CHOICES,
        default=DEFAULT_API_KEY_ROLE,
        help="Role for the new API key (default: readonly)",
    )

    keys_subparsers.add_parser("list", help="List API keys")

    revoke_parser = keys_subparsers.add_parser("revoke", help="Revoke an API key")
    revoke_parser.add_argument("api_key_id", help="API key ID to revoke")


async def _run_keys_command(args: argparse.Namespace) -> int:
    await ensure_schema()
    try:
        action = _extract_keys_action(args)
        if action == "create":
            role = _extract_role(args)
            return await _handle_create(role)
        if action == "list":
            return await _handle_list()
        if action == "revoke":
            api_key_id = _extract_api_key_id(args)
            return await _handle_revoke(api_key_id)
        raise ValueError(f"Unsupported keys command: {action}")
    finally:
        await close_postgres_pool()


def _extract_keys_action(args: argparse.Namespace) -> str:
    action = getattr(args, "keys_action", None)
    if isinstance(action, str):
        return action
    return ""


def _extract_role(args: argparse.Namespace) -> str:
    role = getattr(args, "role", DEFAULT_API_KEY_ROLE)
    if isinstance(role, str) and role.strip():
        return role
    return DEFAULT_API_KEY_ROLE


def _extract_api_key_id(args: argparse.Namespace) -> str:
    api_key_id = getattr(args, "api_key_id", "")
    if isinstance(api_key_id, str):
        return api_key_id
    return ""


async def _handle_create(role: str) -> int:
    created = await create_api_key(role=role)
    api_key_id = created.get("api_key_id")
    api_key = created.get("api_key")

    if not isinstance(api_key_id, str) or not isinstance(api_key, str):
        print("Failed to create API key.", file=sys.stderr)
        return 1

    print(f"api_key_id: {api_key_id}")
    print(f"api_key: {api_key}")
    return 0


async def _handle_list() -> int:
    api_keys = await _list_api_keys()
    if not api_keys:
        print("No API keys found.")
        return 0

    print("api_key_id\trole\trevoked")
    for api_key in api_keys:
        revoked_text = "yes" if api_key["revoked"] else "no"
        print(f"{api_key['api_key_id']}\t{api_key['role']}\t{revoked_text}")

    return 0


async def _list_api_keys() -> list[dict[str, str | bool]]:
    pool = await get_postgres_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id, role, (revoked_at IS NOT NULL) AS revoked
            FROM api_keys
            ORDER BY created_at DESC;
            """
        )

    return [
        {
            "api_key_id": str(row["id"]),
            "role": str(row["role"]),
            "revoked": bool(row["revoked"]),
        }
        for row in rows
    ]


async def _handle_revoke(api_key_id: str) -> int:
    revoked = await revoke_api_key(api_key_id)
    if revoked:
        print(f"Revoked API key: {api_key_id}")
        return 0

    print(f"API key not found or already revoked: {api_key_id}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
