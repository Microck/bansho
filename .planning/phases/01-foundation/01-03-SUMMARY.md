---
phase: 01-foundation
plan: 03
subsystem: api
tags: [mcp, proxy, stdio, streamable-http, passthrough, testing]

# Dependency graph
requires:
  - phase: 01-02
    provides: Redis/Postgres connectivity baseline and runnable sentinel scaffold
provides:
  - Upstream MCP connector supporting stdio and HTTP transports
  - Sentinel MCP server forwarding tools/resources/prompts request families
  - End-to-end passthrough regression test with deterministic upstream fixture
affects: [02-authentication, 03-authorization-rate-limiting, 04-audit]

# Tech tracking
tech-stack:
  added: []
  patterns: [upstream session lifecycle wrapper, low-level MCP request forwarding, stderr-only control-plane diagnostics]

key-files:
  created:
    - src/mcp_sentinel/proxy/upstream.py
    - src/mcp_sentinel/proxy/sentinel_server.py
    - src/mcp_sentinel/proxy/__init__.py
    - tests/test_passthrough.py
  modified:
    - src/mcp_sentinel/main.py

key-decisions:
  - "Use mcp.server.lowlevel.Server request handlers so passthrough responses are returned verbatim without reshaping"
  - "Initialize upstream once at startup and mirror upstream capabilities in Sentinel initialization options"
  - "Emit startup diagnostics to stderr to avoid corrupting stdio JSON-RPC framing"

patterns-established:
  - "Proxy Pattern: UpstreamConnector owns transport/session lifecycle and exposes a narrow forwarding API"
  - "Protocol Safety Pattern: Never write non-JSON logs to stdout when running MCP stdio transport"

# Metrics
duration: 9 min
completed: 2026-02-13
---

# Phase 1 Plan 3: MCP Passthrough Proxy Summary

**Spec-aligned MCP passthrough proxy forwarding tools/resources/prompts to upstream servers with end-to-end regression coverage.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-13T03:13:08Z
- **Completed:** 2026-02-13T03:22:37Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Implemented `UpstreamConnector` with stdio and streamable HTTP transport support plus async lifecycle management.
- Added Sentinel MCP server forwarding handlers for `tools/list`, `tools/call`, `resources/list`, `resources/read`, `prompts/list`, and `prompts/get`.
- Added deterministic passthrough regression coverage proving end-to-end forwarding behavior through Sentinel.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement upstream connection abstraction** - `c4801b8` (feat)
2. **Task 2: Sentinel MCP server that forwards tool methods** - `0de7647` (feat)
3. **Task 3: Passthrough test with a fake upstream server** - `2f54c56` (test)

Additional auto-fix commit:

- `66a78d6` (fix): moved startup diagnostics off stdout to preserve stdio protocol framing

## Files Created/Modified
- `src/mcp_sentinel/proxy/upstream.py` - transport-aware upstream connector and forwarded MCP method wrappers.
- `src/mcp_sentinel/proxy/sentinel_server.py` - low-level Sentinel MCP server that forwards request families to upstream.
- `src/mcp_sentinel/proxy/__init__.py` - proxy package export surface.
- `src/mcp_sentinel/main.py` - runtime entrypoint now launches stdio passthrough proxy.
- `tests/test_passthrough.py` - end-to-end regression using SDK-based fake upstream server.

## Decisions Made
- Chose low-level MCP server handlers over higher-level decorators to preserve upstream payload shapes exactly.
- Bound Sentinel initialization capabilities to upstream `initialize()` output so clients see real upstream capability flags.
- Routed startup diagnostics to stderr after discovering stdout logs can break stdio JSON-RPC parsing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed non-JSON startup logs from stdio data channel**
- **Found during:** Plan-level manual sanity verification
- **Issue:** Startup `structlog` output was written to stdout, causing MCP stdio client parse errors before JSON-RPC responses.
- **Fix:** Replaced startup event logging with stderr output in proxy startup routine.
- **Files modified:** `src/mcp_sentinel/proxy/sentinel_server.py`
- **Verification:** Re-ran manual client connect/list-tools flow with no JSON parse failures.
- **Committed in:** `66a78d6`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix was required for protocol correctness; no scope creep beyond passthrough requirements.

## Issues Encountered

None.

## Authentication Gates

None.

## User Setup Required

None - no new external setup required for this plan.

## Next Phase Readiness

- Foundation phase is complete; the proxy now exposes the request surface needed for auth/authz middleware in Phase 2+.
- No blockers carried forward.

## Self-Check: PASSED

- Verified key files exist on disk: `src/mcp_sentinel/proxy/upstream.py`, `src/mcp_sentinel/proxy/sentinel_server.py`, `src/mcp_sentinel/proxy/__init__.py`, `tests/test_passthrough.py`.
- Verified commit hashes exist in git history: `c4801b8`, `0de7647`, `2f54c56`, `66a78d6`.

---
*Phase: 01-foundation*
*Completed: 2026-02-13*
