---
phase: 05-demo-submit
plan: 01
subsystem: demo
tags: [mcp, stdio, demo, security]
requires:
  - phase: 04-audit
    provides: MCP gateway with auth/authz/rate-limit/audit controls for after-state comparison
provides:
  - Intentionally vulnerable MCP server with sensitive tool exposed without authentication
  - Attack client that demonstrates unauthorized tool execution over stdio
  - Demo quickstart guide for deterministic before-state walkthrough
affects: [05-02, 05-03, demo-recording]
tech-stack:
  added: []
  patterns:
    - Lightweight MCP low-level server fixtures for demo storytelling
    - Self-test and smoke-mode CLIs for deterministic verification
key-files:
  created:
    - demo/vulnerable_server.py
    - demo/client_attack.py
    - demo/README.md
  modified: []
key-decisions:
  - Added `--self-test` to the vulnerable server so verification does not depend on external transport state.
  - Used stdio subprocess orchestration in attack client to keep demo startup deterministic and self-contained.
patterns-established:
  - "Demo scripts must include explicit success/failure output suitable for live recording narration."
duration: 4 min
completed: 2026-02-15
---

# Phase 5 Plan 1: Vulnerable Demo Baseline Summary

**Delivered an intentionally insecure MCP server and attack client that reliably demonstrates unauthorized sensitive-tool execution in the before-state demo.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-15T04:38:55Z
- **Completed:** 2026-02-15T04:43:27Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Implemented `demo/vulnerable_server.py` with multiple tools, including a clearly sensitive `delete_customer` operation, without any auth controls.
- Added `demo/client_attack.py` that spawns the vulnerable server over stdio, lists tools, and successfully calls the sensitive tool without credentials.
- Documented exact local execution commands and expected output snippets in `demo/README.md`.

## Task Commits

1. **Task 1: Implement vulnerable MCP server (no auth)** - `4f61f80` (feat)
2. **Task 2: Implement attack client demonstrating unauthorized tool call** - `5e3d568` (feat)
3. **Task 3: Add demo README quickstart** - `1caa7f9` (docs)

## Files Created/Modified

- `demo/vulnerable_server.py` - Unauthenticated MCP server plus deterministic `--self-test` mode.
- `demo/client_attack.py` - Attack walkthrough client with `--list-tools-only` smoke mode.
- `demo/README.md` - Before-state quickstart and expected output snippets.

## Decisions Made

- Added server-local self-test logic that validates tool registration and sensitive output quality before transport-level demos.
- Kept the attack client self-contained by spawning and tearing down the vulnerable server process per run.

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for `05-02-PLAN.md` to build the deterministic before/after runner and after-state policy enforcement demo.

No blockers identified.

---

*Phase: 05-demo-submit*
*Completed: 2026-02-15*

## Self-Check: PASSED

- Verified created files exist on disk: `demo/vulnerable_server.py`, `demo/client_attack.py`, `demo/README.md`.
- Verified task commits exist in git history: `4f61f80`, `5e3d568`, `1caa7f9`.
