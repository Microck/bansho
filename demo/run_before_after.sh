#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"
BIN_DIR="${REPO_ROOT}/bin"

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

build_binaries() {
  mkdir -p "${BIN_DIR}"

  go build -o "${BIN_DIR}/bansho" ./cmd/bansho
  go build -o "${BIN_DIR}/vulnerable-server" ./cmd/vulnerable-server
  go build -o "${BIN_DIR}/demo-attack" ./cmd/demo-attack
  go build -o "${BIN_DIR}/demo-after" ./cmd/demo-after
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

log_step "Building Go binaries"
build_binaries

log_step "Before state: vulnerable server allows unauthorized sensitive calls"
"${BIN_DIR}/demo-attack" --server "${BIN_DIR}/vulnerable-server"

log_step "Provisioning deterministic demo API keys"
readonly_create_output="$("${BIN_DIR}/bansho" keys create --role readonly)"
printf "%s\n" "${readonly_create_output}"
DEMO_READONLY_API_KEY="$(printf '%s\n' "${readonly_create_output}" | awk -F': ' '/^api_key: /{print $2}')"

admin_create_output="$("${BIN_DIR}/bansho" keys create --role admin)"
printf "%s\n" "${admin_create_output}"
DEMO_ADMIN_API_KEY="$(printf '%s\n' "${admin_create_output}" | awk -F': ' '/^api_key: /{print $2}')"

if [[ -z "${DEMO_READONLY_API_KEY}" || -z "${DEMO_ADMIN_API_KEY}" ]]; then
  fail "Missing demo API key value after creation"
fi

export DEMO_READONLY_API_KEY
export DEMO_ADMIN_API_KEY
export UPSTREAM_TRANSPORT="stdio"
export UPSTREAM_CMD="${BIN_DIR}/vulnerable-server"
export BANSHO_POLICY_PATH="demo/policies_demo.yaml"

printf "Sentinel env: UPSTREAM_TRANSPORT=%s UPSTREAM_CMD=%s BANSHO_POLICY_PATH=%s\n" \
  "${UPSTREAM_TRANSPORT}" \
  "${UPSTREAM_CMD}" \
  "${BANSHO_POLICY_PATH}"

AUDIT_COUNT_BEFORE="$(query_audit_count)"
printf "Audit count before after-state checks: %s\n" "${AUDIT_COUNT_BEFORE}"

log_step "After state: assert 401, 403, 429, 200 through Sentinel"
"${BIN_DIR}/demo-after" --bansho "${BIN_DIR}/bansho"

AUDIT_COUNT_AFTER="$(query_audit_count)"
printf "Audit count after after-state checks: %s\n" "${AUDIT_COUNT_AFTER}"

AUDIT_DELTA=$((AUDIT_COUNT_AFTER - AUDIT_COUNT_BEFORE))
if ((AUDIT_DELTA < 1)); then
  fail "Audit evidence check failed: expected count delta >= 1, got ${AUDIT_DELTA}"
fi
printf "Audit delta: +%s events\n" "${AUDIT_DELTA}"

log_step "Starting dashboard and fetching judge-friendly audit evidence"
"${BIN_DIR}/bansho" dashboard >/tmp/bansho-dashboard.log 2>&1 &
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

if ! [[ "${DASHBOARD_JSON}" =~ \"events\":\[[^\]]*\{ ]]; then
  fail "Dashboard evidence check failed: expected at least one event"
fi

printf "Dashboard API returned events (limit=5).\n"
printf "Dashboard JSON snippet:\n%s\n" "${DASHBOARD_JSON}"

log_step "Demo complete"
printf "Success: before/after demo ran with deterministic 401/403/429/200 + audit evidence.\n"
