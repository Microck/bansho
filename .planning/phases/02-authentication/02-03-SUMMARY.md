---
phase: 02-authentication
plan: 03
subsystem: auth-cli
tags: [auth, api-keys, argparse, postgres, cli]

requires:
  - phase: 02-02
    provides: Auth middleware and repository-backed API key validation at Bansho boundaries
provides:
  - Operator-facing `keys create/list/revoke` CLI workflow with no direct SQL requirement
  - Safe key output behavior where plaintext API keys are shown only on creation
  - Entrypoint command split between `serve` runtime mode and `keys` management mode
affects: [03-authz-rate-limit, 04-audit, demo-operations]

tech-stack:
  added: []
  patterns:
    - Argparse subcommand trees for operational workflows
    - Async CLI command handlers with schema bootstrap and pool teardown per invocation

key-files:
  created:
    - src/bansho/cli/__init__.py
    - src/bansho/cli/keys.py
  modified:
    - src/bansho/main.py

key-decisions:
  - "Use a dedicated `keys` argparse tree with explicit `create`, `list`, and `revoke` actions plus readonly default role."
  - "Keep key listing output restricted to key id/role/revoked metadata and never display stored hashes or plaintext secrets."
  - "Run Postgres schema bootstrap and pool teardown within each CLI invocation so local/demo workflows are resilient."

patterns-established:
  - "Operational CLIs should call repository functions for state-changing auth operations rather than embedding SQL mutations in command handlers."
  - "Entrypoint defaults to explicit subcommands (`serve`, `keys`) and prints help when no mode is selected."

duration: 5 min
completed: 2026-02-13
---

# Phase 2 Plan 03: API Key CLI Summary

**Shipped an operator-safe API key management CLI that creates, lists, and revokes keys from `bansho` while exposing plaintext secrets only at creation time.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-13T20:45:13Z
- **Completed:** 2026-02-13T20:50:57Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `src/bansho/cli/keys.py` with argparse-based `create`, `list`, and `revoke` subcommands for API key lifecycle operations.
- Added `src/bansho/cli/__init__.py` exports so the main entrypoint can register and execute key-management commands cleanly.
- Updated `src/bansho/main.py` to support explicit `serve` and `keys` modes and default to help output when no command is provided.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement keys CLI (create/list/revoke)** - `e4d4a86` (feat)
2. **Task 2: Wire CLI into main entrypoint** - `982deee` (feat)

**Plan metadata:** Pending final docs commit for summary/state/roadmap updates.

## Files Created/Modified

- `src/bansho/cli/__init__.py` - Exposes key CLI registration/execution hooks for entrypoint integration.
- `src/bansho/cli/keys.py` - Implements async key lifecycle commands with safe output semantics.
- `src/bansho/main.py` - Adds `serve`/`keys` subcommands and routes key operations to CLI handlers.

## Decisions Made

- Chose stdlib `argparse` for key management to keep the CLI lightweight and avoid introducing new dependencies.
- Kept `keys create` role default as `readonly` and explicit role choices to preserve deny-by-default operator behavior.
- Ensured command startup always bootstraps schema and command shutdown always closes the Postgres pool for predictable local runs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 2 authentication work is now complete, including practical API key lifecycle management for demos/operators.
- Repository state remains ready for Phase 4 audit logging plans.

## Self-Check: PASSED

- Verified key files listed in this summary exist on disk.
- Verified task commit hashes `e4d4a86` and `982deee` exist in git history.

---

*Phase: 02-authentication*
*Completed: 2026-02-13*
