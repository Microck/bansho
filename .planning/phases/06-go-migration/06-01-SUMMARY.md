---
phase: 06-go-migration
plan: 01
subsystem: api
tags: [go, mcp, redis, postgres, pgx, go-redis, yaml]

requires:
  - phase: 05-demo-submit
    provides: before/after demo requirements and artifacts
provides:
  - Go `bansho` binary with MCP gateway (auth->authz->rate limit->audit->forward)
  - API key lifecycle CLI (create/list/revoke)
  - YAML policy loader + Redis fixed-window rate limiting
  - Postgres audit log + admin-only dashboard HTTP API
  - Go-based demo server + deterministic before/after runner
affects: [demo, docs, testing]

tech-stack:
  added: [github.com/modelcontextprotocol/go-sdk, github.com/jackc/pgx/v5, github.com/redis/go-redis/v9, gopkg.in/yaml.v3]
  patterns: [package-internal layering, stdio gateway, per-request MCP meta auth, fixed-window limiter]

key-files:
  created:
    - cmd/bansho/main.go
    - internal/proxy/server.go
    - internal/auth/hash.go
    - internal/ratelimit/limiter.go
    - internal/audit/logger.go
    - integration/demo_runner_test.go
  modified:
    - demo/run_before_after.sh
    - README.md
    - .gitignore

key-decisions:
  - "Keep the existing Postgres schema (api_keys, audit_events) for drop-in compatibility with docker-compose"
  - "Use MCP Go SDK receiving middleware for non-tool passthrough and tool-list filtering; enforce gates inside per-tool handlers"
  - "Run demo checks via Go MCP clients (CommandTransport) to remove Python tooling from the demo runner"

patterns-established:
  - "Gateway pipeline: authenticate -> authorize -> rate limit -> forward, with audit in defer"
  - "Auth extraction supports MCP _meta headers and HTTP transport headers"

duration: 32m
completed: 2026-02-15
---

# Phase 6 Plan 1: Go Migration Summary

**Go `bansho` gateway using the official MCP Go SDK, preserving the auth/authz/rate-limit/audit proxy surface with a Go-only deterministic demo runner.**

## Performance

- **Duration:** 32m
- **Started:** 2026-02-15T06:06:17Z
- **Completed:** 2026-02-15T06:38:31Z
- **Tasks:** 9

## Accomplishments
- Shipped a Go-based MCP gateway that enforces `401/403/429/200` on `tools/call` and writes audit evidence to Postgres.
- Preserved YAML policy configuration and Redis fixed-window rate limiting semantics.
- Replaced the demo runner flow with Go binaries (no Python toolchain required) and added a docker-aware integration test.

## Task Commits

Each task was committed atomically:

1. **Task 1: Go module scaffold + bansho CLI skeleton** - `a8f3d86` (feat)
2. **Task 2: Storage layer (Postgres + Redis) and schema bootstrap** - `362e424` (feat)
3. **Task 3: API key hashing + key lifecycle CLI parity** - `4eb0abc` (feat)
4. **Task 4: YAML policy models + loader parity** - `0a9f90f` (feat)
5. **Task 5: Redis fixed-window rate limiting parity** - `fc29230` (feat)
6. **Task 6: Audit logging + dashboard HTTP API parity** - `54d4645` (feat)
7. **Task 7: MCP gateway proxy (auth -> authz -> rate limit -> audit -> forward)** - `9778a77` (feat)
8. **Task 8: Go demo server + updated before/after runner** - `b7ebe08` (feat)
9. **Task 9: Go tests + at least one integration test path for demo runner** - `43e58d1` (test)

## Files Created/Modified
- `go.mod` - Go module definition for the Go migration
- `cmd/bansho/main.go` - CLI entrypoint (`serve`, `dashboard`, `keys`)
- `internal/proxy/server.go` - Gateway wiring + MCP method middleware passthrough
- `internal/proxy/upstream.go` - Upstream connector (stdio command or streamable HTTP)
- `internal/auth/hash.go` - PBKDF2-SHA256 API key hashing compatible with stored format
- `internal/auth/api_keys.go` - Postgres-backed key lifecycle and key resolution
- `internal/ratelimit/limiter.go` - Redis fixed-window limiter (INCR+EXPIRE)
- `internal/audit/logger.go` - Audit persistence + recent event query
- `internal/ui/dashboard.go` - Admin-only dashboard API (`/api/events`) + HTML view
- `demo/run_before_after.sh` - Go-based deterministic runner (401/403/429/200 + audit evidence)
- `integration/demo_runner_test.go` - Integration path that runs the demo runner when docker is available
- `README.md` - Updated to Go build/test workflow

## Decisions Made
- Kept the Python-era Postgres schema and docker-compose defaults to avoid breaking the local dev story.
- Used the MCP Go SDK's low-level `Server.AddTool` + receiving middleware to implement a proxy without reshaping upstream payloads.
- Left the existing Python code in-place as reference/legacy; the Go binaries are the primary surface.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Go demo programs initially collided as multiple `package main` files under `demo/`; resolved by moving them to dedicated `cmd/*` directories.
- Policy loader unit test pathing was brittle; resolved by walking up directories to find `demo/policies_demo.yaml`.

## User Setup Required

None - local dev uses docker compose for Postgres/Redis and env vars from `.env.example`.

## Next Phase Readiness
- Ready to record the final demo video using `bash demo/run_before_after.sh`.
- Optional follow-up: remove or archive the legacy Python implementation once the Go surface is accepted.

---
*Phase: 06-go-migration*
*Completed: 2026-02-15*

## Self-Check: PASSED

- FOUND: `.planning/phases/06-go-migration/06-01-PLAN.md`
- FOUND: `.planning/phases/06-go-migration/06-01-SUMMARY.md`
- FOUND: `.planning/STATE.md`
- FOUND commits: `a8f3d86`, `362e424`, `4eb0abc`, `0a9f90f`, `fc29230`, `54d4645`, `9778a77`, `b7ebe08`, `43e58d1`
