---
phase: 04-audit
plan: 01
subsystem: audit-logging
tags: [audit, postgres, jsonb, security, mcp]

requires:
  - phase: 03-04
    provides: Explicit auth/authz/rate pipeline outcomes available for audit capture
provides:
  - Bounded and redacted `AuditEvent` model for request, response, and decision metadata
  - Postgres `AuditLogger` that inserts identity, timing, and outcome data into `audit_events`
  - Unit test coverage for logger insertion, payload redaction, and pool resolution
affects: [04-02, 04-03, proxy-runtime, dashboard]

tech-stack:
  added: []
  patterns:
    - Bound and sanitize audit payloads before persistence to avoid secret leakage and oversized rows
    - Keep logger pool-injectable for deterministic tests while defaulting to shared Postgres pool

key-files:
  created:
    - src/mcp_sentinel/audit/models.py
    - src/mcp_sentinel/audit/logger.py
    - src/mcp_sentinel/audit/__init__.py
    - tests/test_audit_logger.py
  modified:
    - src/mcp_sentinel/storage/schema.py

key-decisions:
  - "Normalize audit payloads through model validators with key-based redaction and byte bounding before DB writes."
  - "Store `role` and `decision` as first-class `audit_events` columns so later plans can query/filter audit outcomes directly."
  - "Allow invalid `api_key_id` strings to degrade to NULL at write time so logging never crashes request handling."

patterns-established:
  - "Audit payload sanitation happens in model construction, not ad-hoc in logger call sites"
  - "Schema evolution for existing environments uses additive `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`"

duration: 4 min
completed: 2026-02-14
---

# Phase 4 Plan 01: Audit Primitives Summary

**Sentinel now has an auditable event model plus a Postgres logger that persists timestamped tool-request outcomes with bounded, redacted JSON metadata.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-14T00:29:42Z
- **Completed:** 2026-02-14T00:34:14Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `AuditEvent` with required audit fields (`ts`, identity, method/tool, request/response payloads, status, latency, decision) and safe JSON bounding.
- Implemented `AuditLogger.log_event(event)` to write audit rows to Postgres via `INSERT INTO audit_events` without storing plaintext API keys.
- Added focused tests that validate DB insert behavior, payload redaction, and fallback pool resolution.

## Task Commits

Each task was committed atomically:

1. **Task 1: Define audit event model** - `d023d07` (feat)
2. **Task 2: Implement Postgres audit logger** - `e5426d7` (feat)

**Plan metadata:** Pending final docs commit for summary/state/roadmap updates.

## Files Created/Modified

- `src/mcp_sentinel/audit/models.py` - Defines `AuditEvent`, JSON sanitization/redaction, and bounded serialization helpers.
- `src/mcp_sentinel/audit/logger.py` - Implements `AuditLogger` with Postgres insert and safe API key UUID parsing.
- `src/mcp_sentinel/audit/__init__.py` - Exposes audit model imports.
- `tests/test_audit_logger.py` - Covers audit insertion, redaction behavior, and default pool fallback.
- `src/mcp_sentinel/storage/schema.py` - Adds `role` and `decision` fields to `audit_events` creation/migration paths.

## Decisions Made

- Centralized payload sanitation in `AuditEvent` validators so every caller gets consistent truncation and secret redaction by default.
- Added dedicated `role` and `decision` columns to `audit_events` instead of burying them in generic JSON blobs to support upcoming audit integration/dashboard queries.
- Parsed `api_key_id` defensively (UUID when valid, NULL otherwise) so audit logging remains non-blocking for malformed identity metadata.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extended `audit_events` schema for new logger fields**
- **Found during:** Task 2 (Implement Postgres audit logger)
- **Issue:** Existing schema lacked `role` and `decision` columns required by the new audit model/logger contract.
- **Fix:** Added `role` and `decision` to table creation SQL plus additive `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` migration statements.
- **Files modified:** `src/mcp_sentinel/storage/schema.py`
- **Verification:** `uv run pytest -q`
- **Committed in:** `e5426d7` (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Schema extension was required for correctness and future queryability; no scope creep beyond audit contract support.

## Issues Encountered

None.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Audit primitives are complete and verified with full test-suite pass.
- Ready for `.planning/phases/04-audit/04-02-PLAN.md` (pipeline instrumentation and integration coverage).

## Self-Check: PASSED

- Verified key files listed in this summary exist on disk.
- Verified task commit hashes `d023d07` and `e5426d7` exist in git history.

---

*Phase: 04-audit*
*Completed: 2026-02-14*
