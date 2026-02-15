---
phase: 05-demo-submit
plan: 02
subsystem: demo
tags: [mcp, automation, policies, docker, audit]
requires:
  - phase: 05-01
    provides: vulnerable before-state server and attack client baseline
provides:
  - One-command before/after demo runner for hackathon recording
  - Demo policy file with deterministic allow/deny and rate-limit behavior
  - Automated proof of auth/authz/rate-limit outcomes plus audit evidence
affects: [05-03, submission, demo-recording]
tech-stack:
  added: []
  patterns:
    - Bash orchestration with explicit dependency readiness gates
    - Embedded MCP stdio assertions for deterministic 401/403/429/200 checks
key-files:
  created:
    - demo/policies_demo.yaml
    - demo/run_before_after.sh
  modified:
    - demo/README.md
key-decisions:
  - Kept demo policy isolated in `demo/policies_demo.yaml` to avoid mutating production-default policy behavior.
  - Embedded Sentinel stdio checks in the runner to enforce deterministic error-code assertions during recording.
patterns-established:
  - "Before/after demos must prove security outcomes with both application-level assertions and DB/dashboard evidence."
duration: 4 min
completed: 2026-02-15
---

# Phase 5 Plan 2: Deterministic Before/After Runner Summary

**Shipped a single-command demo runner that reproduces before-state compromise and after-state 401/403/429/200 enforcement with auditable evidence.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-15T04:44:49Z
- **Completed:** 2026-02-15T04:49:40Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `demo/policies_demo.yaml` with readonly-only harmless access and a low per-tool threshold to trigger 429 predictably.
- Implemented `demo/run_before_after.sh` to automate Docker readiness, before-state attack, key provisioning, Sentinel stdio checks, and dashboard evidence retrieval.
- Extended `demo/README.md` with one-command before/after runner usage and expected outcome markers.

## Task Commits

1. **Task 1: Add demo policy file tuned for the recording** - `49b9096` (feat)
2. **Task 2: Create a before/after runner script** - `bb2281f` (feat)

## Files Created/Modified

- `demo/policies_demo.yaml` - Demo policy mapping readonly/admin permissions and deterministic rate limits.
- `demo/run_before_after.sh` - End-to-end automation for before/after flows, assertions, and audit/dashboard checks.
- `demo/README.md` - Updated with full runner command and expected output checkpoints.

## Decisions Made

- Isolated demo-specific authorization/rate-limit behavior in `demo/policies_demo.yaml` instead of changing `config/policies.yaml` defaults.
- Used MCP stdio sessions inside the runner to assert exact security outcomes (`401`, `403`, `429`, `200`) in one deterministic flow.

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for `05-03-PLAN.md` documentation and recording checklist finalization.

No blockers identified.

---

*Phase: 05-demo-submit*
*Completed: 2026-02-15*

## Self-Check: PASSED

- Verified required artifacts exist: `demo/policies_demo.yaml`, `demo/run_before_after.sh`, `demo/README.md`.
- Verified task commits exist in git history: `49b9096`, `bb2281f`.
