---
phase: 03-authz-rate-limit
plan: 02
subsystem: authz
tags: [authorization, mcp, policy, role-based-access, deny-by-default]

requires:
  - phase: 03-01
    provides: Validated policy schema and loader with deny-first defaults
provides:
  - Tool authorization middleware with structured allow/deny decisions
  - Role-based enforcement for tools/call with 403 on authorization failures
  - Role-filtered tools/list output to limit sensitive tool discovery
affects: [03-authz-rate-limit-03, 03-authz-rate-limit-04, auth-tests]

tech-stack:
  added: []
  patterns:
    - Startup policy loading via SENTINEL_POLICY_PATH with fail-closed behavior
    - Tool-level authorization checks driven by AuthContext.role
    - Authorization-aware tool listing to reduce sensitive surface disclosure

key-files:
  created:
    - src/mcp_sentinel/middleware/authz.py
    - tests/test_authz_enforcement.py
  modified:
    - src/mcp_sentinel/proxy/sentinel_server.py
    - tests/test_auth_enforcement.py
    - tests/test_passthrough.py

key-decisions:
  - "Represent authorization outcomes as structured decisions (allowed, reason, matched_rule) for future audit/log integration."
  - "Load policy once during Sentinel startup and fail closed if the configured policy file is missing or invalid."
  - "Filter tools/list by role policy in addition to enforcing tools/call to reduce discovery of sensitive tools."

patterns-established:
  - "MCP tool calls return 403 Forbidden on authorization denials"
  - "Role matrix tests validate readonly/user/admin behavior for sensitive operations"

duration: 6 min
completed: 2026-02-13
---

# Phase 3 Plan 02: Authorization Enforcement Summary

**Sentinel now enforces policy-driven tool authorization per role, denies unauthorized tool calls with 403, and hides sensitive tools from non-admin listings.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-13T05:51:46Z
- **Completed:** 2026-02-13T05:57:59Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added `authorize_tool` middleware with deny-by-default behavior and structured decision metadata.
- Wired policy loading and authorization checks into Sentinel tool handlers with fail-closed startup semantics.
- Added role matrix tests proving readonly/user/admin behavior for sensitive tools and filtered tool lists.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement authz middleware** - `ec4983f` (feat)
2. **Task 2: Wire authz into tool calls** - `c09fcc4` (feat)
3. **Task 3: Add authz tests (role matrix)** - `ac10b3f` (test)

**Plan metadata:** Pending final docs commit for summary/state/roadmap updates.

## Files Created/Modified

- `src/mcp_sentinel/middleware/authz.py` - Authorization decision logic for role/tool evaluation.
- `src/mcp_sentinel/proxy/sentinel_server.py` - Startup policy loading, tools/list filtering, and tools/call 403 enforcement.
- `tests/test_authz_enforcement.py` - Role matrix regression coverage for sensitive tool access.
- `tests/test_auth_enforcement.py` - Authentication tests updated to inject explicit policy under authz-enabled server construction.
- `tests/test_passthrough.py` - Integration passthrough fixture updated to use admin role with default deny policy.

## Decisions Made

- Enforced a single authorization primitive (`authorize_tool`) for both discovery (`tools/list`) and invocation (`tools/call`) to keep behavior consistent.
- Preserved admin wildcard semantics from 03-01 while keeping non-admin roles deny-by-default for unknown/sensitive tools.
- Chose MCP `Forbidden` (403) errors for authorization denials while retaining existing 401 behavior for authentication failures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated auth enforcement tests for policy-aware server construction**
- **Found during:** Task 3 (full-suite verification)
- **Issue:** Existing auth tests called `create_sentinel_server(connector)` without the new required `policy` argument, causing `TypeError` failures.
- **Fix:** Added a test policy fixture and passed policy explicitly to each auth test setup call.
- **Files modified:** `tests/test_auth_enforcement.py`
- **Verification:** `uv run pytest -q`
- **Committed in:** `ac10b3f` (part of Task 3 commit)

**2. [Rule 3 - Blocking] Adjusted passthrough integration role for default-deny policy**
- **Found during:** Task 3 (full-suite verification)
- **Issue:** Passthrough test authenticated as `readonly`, which now receives filtered empty tool lists under default policy.
- **Fix:** Updated passthrough fixture to authenticate as `admin` so passthrough assertions remain focused on forwarding behavior.
- **Files modified:** `tests/test_passthrough.py`
- **Verification:** `uv run pytest -q`
- **Committed in:** `ac10b3f` (part of Task 3 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were required to keep existing regression suites compatible with enforced authorization behavior; no feature scope expansion.

## Issues Encountered

- Existing tests assumed pre-authz server constructor and readonly passthrough visibility; resolved by updating test fixtures to align with enforced policy checks.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for `03-03-PLAN.md` to implement Redis-backed rate limiting using the same policy source.
- No unresolved blockers carried forward.

## Self-Check: PASSED

- Verified all key files listed in this summary exist on disk.
- Verified task commit hashes `ec4983f`, `c09fcc4`, and `ac10b3f` exist in git history.

---

*Phase: 03-authz-rate-limit*
*Completed: 2026-02-13*
