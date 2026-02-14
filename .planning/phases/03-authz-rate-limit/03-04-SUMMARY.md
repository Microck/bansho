---
phase: 03-authz-rate-limit
plan: 04
subsystem: security-pipeline
tags: [auth, authorization, rate-limiting, mcp, testing]

requires:
  - phase: 03-03
    provides: Policy-driven Redis-backed rate limiting middleware for tool handlers
provides:
  - Explicit non-bypassable `authenticate -> authorize -> rate_limit -> forward` pipeline for tool calls
  - End-to-end regression that proves denied and limited requests never invoke upstream tools
  - Security pipeline status contract coverage for 401, 403, 429, and successful call flow
affects: [04-audit, proxy-runtime, security-enforcement]

tech-stack:
  added: []
  patterns:
    - Tool-call handlers execute security gates inline and in fixed order before forwarding
    - Security regressions assert both response status and upstream side effects

key-files:
  created:
    - tests/test_security_pipeline.py
  modified:
    - src/mcp_sentinel/proxy/sentinel_server.py
    - tests/test_authz_enforcement.py

key-decisions:
  - "Make `tools/call` security sequencing explicit in one handler path so bypasses are auditable and harder to introduce accidentally."
  - "Use upstream call-count assertions in E2E coverage so failures verify side effects, not only error codes."
  - "Stub Redis eval in authz-focused tests to keep authorization assertions deterministic after rate-limit pipeline wiring."

patterns-established:
  - "Security gate failures (401/403/429) short-circuit before upstream forwarding"
  - "Authz tests isolate policy behavior from rate-limit storage mechanics"

duration: 5 min
completed: 2026-02-13
---

# Phase 3 Plan 04: Security Pipeline Summary

**Sentinel now enforces a strict tool-call security chain (`auth -> authz -> rate limit -> forward`) with regression coverage that proves denied or limited calls never reach upstream.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-13T06:13:36Z
- **Completed:** 2026-02-13T06:18:55Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Refactored proxy tool-call handling to run authentication, authorization, and rate limiting in explicit order before forwarding.
- Added end-to-end security pipeline regression coverage for missing key (401), disallowed tool (403), limited tool (429), and allowed success (200).
- Added upstream invocation assertions to guarantee failed security checks do not call the proxied upstream tool.

## Task Commits

Each task was committed atomically:

1. **Task 1: Ensure strict pipeline ordering in proxy** - `42c0cd6` (feat)
2. **Task 2: Add E2E regression test for bypass prevention** - `45eaeac` (test)

**Plan metadata:** Pending final docs commit for summary/state/roadmap updates.

## Files Created/Modified

- `src/mcp_sentinel/proxy/sentinel_server.py` - Inlines `authenticate -> authorize -> rate_limit -> upstream` for `tools/call` and keeps 401/403/429 short-circuit behavior.
- `tests/test_security_pipeline.py` - Adds fake-upstream E2E regression with explicit status expectations and upstream call-count assertions.
- `tests/test_authz_enforcement.py` - Stubs limiter Redis eval for authz tests so full-suite verification remains deterministic after pipeline wiring.

## Decisions Made

- Enforced the full security chain directly in the tool-call handler instead of relying on implicit middleware composition, making execution order explicit and reviewable.
- Captured bypass prevention as a side-effect contract (`upstream call_count`) so regressions cannot pass by only returning the right error code.
- Isolated authz tests from Redis-backed limiter internals by monkeypatching `redis_eval` in-module, keeping authorization expectations focused.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Full-suite authz tests failed after rate-limit pipeline integration**
- **Found during:** Task 2 verification (`uv run pytest -q`)
- **Issue:** `tests/test_authz_enforcement.py` started invoking Redis-backed rate limiting on `tools/call`, which caused async event-loop reuse failures in the full suite.
- **Fix:** Added an autouse fixture to monkeypatch `limiter_module.redis_eval` in authz tests.
- **Files modified:** `tests/test_authz_enforcement.py`
- **Verification:** `uv run pytest -q`
- **Committed in:** `45eaeac` (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix was required to complete full verification after introducing strict pipeline enforcement; no scope creep beyond test isolation.

## Issues Encountered

- Initial full-suite verification failed because authz tests implicitly depended on non-mocked Redis calls once rate limiting became part of the tool-call path; resolved by test-level Redis eval stubbing.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 security controls are now complete for the planned pipeline ordering and bypass-prevention coverage.
- Ready to begin Phase 4 audit logging work with no unresolved blockers.

## Self-Check: PASSED

- Verified key files listed in this summary exist on disk.
- Verified task commit hashes `42c0cd6` and `45eaeac` exist in git history.

---

*Phase: 03-authz-rate-limit*
*Completed: 2026-02-13*
