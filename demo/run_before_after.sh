#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"

DASHBOARD_PID=""

cleanup() {
  local exit_code=$?
  trap - EXIT
  set +e

  if [[ -n "${DASHBOARD_PID}" ]] && kill -0 "${DASHBOARD_PID}" 2>/dev/null; then
    kill "${DASHBOARD_PID}" 2>/dev/null || true
    sleep 1
    if kill -0 "${DASHBOARD_PID}" 2>/dev/null; then
      kill -9 "${DASHBOARD_PID}" 2>/dev/null || true
    fi
  fi

  exit "${exit_code}"
}
trap cleanup EXIT

cd "${REPO_ROOT}"

log_step() {
  printf "\n==> %s\n" "$1"
}

compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

fail() {
  printf "ERROR: %s\n" "$1" >&2
  exit 1
}

wait_for_dependencies() {
  local timeout_seconds=60
  local deadline=$((SECONDS + timeout_seconds))

  while ((SECONDS < deadline)); do
    local redis_status=""
    redis_status="$(compose exec -T redis redis-cli --raw ping 2>/dev/null || true)"

    if [[ "${redis_status}" == "PONG" ]] \
      && compose exec -T postgres pg_isready -h 127.0.0.1 -U bansho -d bansho >/dev/null 2>&1; then
      return 0
    fi

    sleep 2
  done

  compose ps
  fail "Redis/Postgres readiness checks timed out after ${timeout_seconds}s"
}

query_audit_count() {
  local count
  count="$(compose exec -T postgres env PGPASSWORD=bansho psql -U bansho -d bansho -tAc "SELECT count(*) FROM audit_events;" | tr -d '[:space:]')"

  if [[ ! "${count}" =~ ^[0-9]+$ ]]; then
    fail "Unexpected audit count value: ${count}"
  fi

  printf "%s\n" "${count}"
}

log_step "Starting docker dependencies (redis + postgres)"
compose up -d redis postgres
wait_for_dependencies

log_step "Before state: vulnerable server allows unauthorized sensitive calls"
uv run python demo/client_attack.py

log_step "Provisioning deterministic demo API keys"
readonly_create_output="$(uv run bansho keys create --role readonly)"
printf "%s\n" "${readonly_create_output}"
DEMO_READONLY_API_KEY="$(printf '%s\n' "${readonly_create_output}" | awk -F': ' '/^api_key: /{print $2}')"

admin_create_output="$(uv run bansho keys create --role admin)"
printf "%s\n" "${admin_create_output}"
DEMO_ADMIN_API_KEY="$(printf '%s\n' "${admin_create_output}" | awk -F': ' '/^api_key: /{print $2}')"

if [[ -z "${DEMO_READONLY_API_KEY}" || -z "${DEMO_ADMIN_API_KEY}" ]]; then
  fail "Missing demo API key value after creation"
fi

export DEMO_READONLY_API_KEY
export DEMO_ADMIN_API_KEY
export UPSTREAM_TRANSPORT="stdio"
export UPSTREAM_CMD="uv run python demo/vulnerable_server.py"
export BANSHO_POLICY_PATH="demo/policies_demo.yaml"

printf "Sentinel env: UPSTREAM_TRANSPORT=%s UPSTREAM_CMD=%s BANSHO_POLICY_PATH=%s\n" \
  "${UPSTREAM_TRANSPORT}" \
  "${UPSTREAM_CMD}" \
  "${BANSHO_POLICY_PATH}"

AUDIT_COUNT_BEFORE="$(query_audit_count)"
printf "Audit count before after-state checks: %s\n" "${AUDIT_COUNT_BEFORE}"

log_step "After state: assert 401, 403, 429, 200 through Sentinel"
uv run python - <<'PY'
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import anyio
import mcp.types as types
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.exceptions import McpError

READONLY_KEY = os.environ["DEMO_READONLY_API_KEY"]
ADMIN_KEY = os.environ["DEMO_ADMIN_API_KEY"]

SENSITIVE_TOOL = "delete_customer"
RATE_LIMITED_TOOL = "list_customers"


def auth_meta(api_key: str | None) -> types.RequestParams.Meta | None:
    if api_key is None:
        return None
    return types.RequestParams.Meta.model_validate({"headers": {"X-API-Key": api_key}})


async def call_tool(
    session: ClientSession,
    name: str,
    arguments: dict[str, Any],
    api_key: str | None,
) -> types.CallToolResult:
    params_data: dict[str, Any] = {
        "name": name,
        "arguments": arguments,
    }
    meta = auth_meta(api_key)
    if meta is not None:
        params_data["_meta"] = meta

    result = await session.send_request(
        types.ClientRequest(types.CallToolRequest(params=types.CallToolRequestParams(**params_data))),
        types.CallToolResult,
    )
    return result


async def expect_error(
    session: ClientSession,
    *,
    label: str,
    tool_name: str,
    arguments: dict[str, Any],
    api_key: str | None,
    expected_code: int,
) -> None:
    try:
        await call_tool(session, tool_name, arguments, api_key)
    except McpError as exc:
        if exc.error.code != expected_code:
            raise AssertionError(
                f"{label}: expected {expected_code}, got {exc.error.code}"
            ) from exc
        print(f"[after] {label}: got expected {expected_code}")
        return

    raise AssertionError(f"{label}: expected McpError code {expected_code}")


def first_text(result: types.CallToolResult) -> str:
    if result.content and isinstance(result.content[0], types.TextContent):
        return result.content[0].text
    return ""


async def main() -> None:
    sentinel_env = {
        "UPSTREAM_TRANSPORT": os.environ["UPSTREAM_TRANSPORT"],
        "UPSTREAM_CMD": os.environ["UPSTREAM_CMD"],
        "BANSHO_POLICY_PATH": os.environ["BANSHO_POLICY_PATH"],
    }

    for optional_var in ("POSTGRES_DSN", "REDIS_URL"):
        value = os.environ.get(optional_var)
        if value:
            sentinel_env[optional_var] = value

    sentinel = StdioServerParameters(
        command="uv",
        args=["run", "bansho", "serve"],
        cwd=str(Path.cwd()),
        env=sentinel_env,
    )

    async with stdio_client(sentinel) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            await expect_error(
                session,
                label="401 check (missing API key)",
                tool_name=RATE_LIMITED_TOOL,
                arguments={},
                api_key=None,
                expected_code=401,
            )

            await expect_error(
                session,
                label="403 check (readonly on sensitive tool)",
                tool_name=SENSITIVE_TOOL,
                arguments={"customer_id": "cust_blocked_01"},
                api_key=READONLY_KEY,
                expected_code=403,
            )

            first_rate_call = await call_tool(session, RATE_LIMITED_TOOL, {}, READONLY_KEY)
            if first_rate_call.isError:
                raise AssertionError("429 check: first rate-limited call should succeed")
            print("[after] 429 check: first readonly call succeeded")

            await expect_error(
                session,
                label="429 check (second readonly call)",
                tool_name=RATE_LIMITED_TOOL,
                arguments={},
                api_key=READONLY_KEY,
                expected_code=429,
            )

            admin_result = await call_tool(
                session,
                SENSITIVE_TOOL,
                {"customer_id": "cust_allowed_01"},
                ADMIN_KEY,
            )
            if admin_result.isError:
                raise AssertionError("200 check: admin sensitive call returned error")

            admin_text = first_text(admin_result)
            if not admin_text.strip():
                raise AssertionError("200 check: admin sensitive call returned empty payload")

            print("[after] 200 check (admin sensitive call) succeeded")
            print(f"[after] admin response: {admin_text}")
            print("After-state checks complete: 401 / 403 / 429 / 200")


anyio.run(main)
PY

AUDIT_COUNT_AFTER="$(query_audit_count)"
printf "Audit count after after-state checks: %s\n" "${AUDIT_COUNT_AFTER}"

AUDIT_DELTA=$((AUDIT_COUNT_AFTER - AUDIT_COUNT_BEFORE))
if ((AUDIT_DELTA < 1)); then
  fail "Audit evidence check failed: expected count delta >= 1, got ${AUDIT_DELTA}"
fi
printf "Audit delta: +%s events\n" "${AUDIT_DELTA}"

log_step "Starting dashboard and fetching judge-friendly audit evidence"
uv run bansho dashboard >/tmp/bansho-dashboard.log 2>&1 &
DASHBOARD_PID=$!

DASHBOARD_JSON=""
for _attempt in $(seq 1 30); do
  if DASHBOARD_JSON="$(curl -s -f -H "X-API-Key: ${DEMO_ADMIN_API_KEY}" "http://127.0.0.1:9100/api/events?limit=5" 2>/dev/null)"; then
    break
  fi
  sleep 1
done

if [[ -z "${DASHBOARD_JSON}" ]]; then
  fail "Dashboard API did not become ready on http://127.0.0.1:9100/api/events"
fi

EVENT_COUNT="$(printf '%s' "${DASHBOARD_JSON}" | uv run python -c "import json, sys; print(len(json.load(sys.stdin).get('events', [])))")"
if [[ ! "${EVENT_COUNT}" =~ ^[0-9]+$ ]]; then
  fail "Dashboard response did not return a numeric event count"
fi

if ((EVENT_COUNT < 1)); then
  fail "Dashboard evidence check failed: expected non-empty events list"
fi

printf "Dashboard API returned %s events (limit=5).\n" "${EVENT_COUNT}"
printf "Dashboard JSON snippet:\n%s\n" "${DASHBOARD_JSON}"

log_step "Demo complete"
printf "Success: before/after demo ran with deterministic 401/403/429/200 + audit evidence.\n"
