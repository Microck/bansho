---
phase: 01-foundation
plan: 02
subsystem: database
tags: [redis, postgres, asyncpg, schema-bootstrap, health-check]

# Dependency graph
requires:
  - phase: 01-01
    provides: Base configuration, dependency toolchain, and local Docker services
provides:
  - Async Redis client wrapper with reusable primitive helpers
  - Async Postgres pool wrapper with schema bootstrap entrypoint
  - Idempotent schema bootstrap for api_keys and audit_events tables
  - Reusable storage smoke check for Redis/Postgres readiness
affects: [authentication, authorization, rate-limiting, audit]

# Tech tracking
tech-stack:
  added: []
  patterns: [lazy async client factories, idempotent DDL bootstrap, non-throwing health probes]

key-files:
  created:
    - src/bansho/storage/__init__.py
    - src/bansho/storage/redis.py
    - src/bansho/storage/postgres.py
    - src/bansho/storage/schema.py
  modified:
    - .planning/phases/01-foundation/01-02-SUMMARY.md
    - .planning/STATE.md

key-decisions:
  - "Use lazy singleton async clients for Redis and Postgres to avoid reconnecting on each operation"
  - "Keep schema bootstrap idempotent with CREATE TABLE IF NOT EXISTS and safe postgres types"
  - "Expose storage_smoke_check() as a boolean map so later health checks can reuse it directly"

patterns-established:
  - "Storage modules expose get_* and close_* lifecycle helpers"
  - "Postgres schema creation lives in schema.py and is invoked via postgres.ensure_schema()"

# Metrics
duration: 3 min
completed: 2026-02-13
---

# Phase 1 Plan 2: Storage Connectivity Summary

**Async Redis and Postgres storage primitives with idempotent schema bootstrap for API key and audit event persistence.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-13T03:04:36Z
- **Completed:** 2026-02-13T03:08:28Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Added Redis async wrapper with get/set/incr/expire and Lua eval helpers.
- Added asyncpg pool wrapper and `ensure_schema()` entrypoint for storage bootstrap.
- Added idempotent schema SQL for `api_keys` and `audit_events` plus reusable `storage_smoke_check()`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Redis client wrapper** - `5c1e12e` (feat)
2. **Task 2: Postgres pool wrapper + schema bootstrap** - `439d3b3` (feat)
3. **Task 3: Storage smoke test** - `09851cc` (feat)

_Plan metadata commit is created after summary/state updates._

## Files Created/Modified
- `src/bansho/storage/__init__.py` - storage package exports for Redis helpers.
- `src/bansho/storage/redis.py` - Redis lifecycle and primitive helper operations.
- `src/bansho/storage/postgres.py` - asyncpg pool lifecycle and schema bootstrap entrypoint.
- `src/bansho/storage/schema.py` - idempotent schema DDL and storage smoke-check helper.

## Decisions Made
- Used lazy process-level async clients/pools for Redis and Postgres to keep upcoming middleware integrations simple.
- Included both `api_keys` and `audit_events` schema now, even before all consumers exist, to reduce migration churn in later phases.
- Returned smoke-check results as a simple `{redis: bool, postgres: bool}` contract for future CLI health endpoints.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Authentication Gates

None.

## User Setup Required

None - no additional external service setup beyond existing local Docker services.

## Next Phase Readiness

- Storage primitives are in place and verified; Phase 01-03 can build MCP proxy wiring on top.
- No blockers carried forward.

## Self-Check: PASSED

- Verified all referenced storage files exist on disk.
- Verified all task commit hashes exist in git history.

---
*Phase: 01-foundation*
*Completed: 2026-02-13*
