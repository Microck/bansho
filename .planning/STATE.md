# ToolchainGate - Project State

## Current Position

Phase: 4 of 5 (Audit)
Plan: 2 of 3
Status: In progress
Last activity: 2026-02-14 - Completed 04-02-PLAN.md
Progress: ████████████░░░░ 12/16 plans (75%)

---

## Phase Status

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 1 | Foundation | Complete | 3/3 plans |
| 2 | Authentication | Complete | 3/3 plans |
| 3 | Authorization & Rate Limiting | Complete | 4/4 plans |
| 4 | Audit | In Progress | 2/3 plans |
| 5 | Demo & Submit | Not Started | 0/3 plans |

---

## Decisions Accumulated

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 01-01 | Keep startup entrypoint as settings/logging stub only | Avoid constraining upcoming proxy and security architecture |
| 01-01 | Use typed BaseSettings with explicit env aliases | Make runtime config contract explicit and safer |
| 01-01 | Bind local Postgres host port to 5433 | Avoid host conflicts on 5432 while keeping localhost-only exposure |
| 01-02 | Use lazy async Redis/Postgres client factories | Reuse long-lived connections across future middleware paths |
| 01-02 | Bootstrap schema with idempotent CREATE TABLE IF NOT EXISTS | Allow repeatable setup without migration tooling this early |
| 01-02 | Return storage smoke check as boolean map contract | Keep health-check integration trivial for later CLI/API endpoints |
| 01-03 | Use low-level MCP request handlers for passthrough | Return upstream result payloads without reshaping |
| 01-03 | Mirror upstream initialize capabilities in Sentinel | Ensure client-facing capabilities match the proxied upstream |
| 01-03 | Emit startup diagnostics to stderr for stdio mode | Protect MCP JSON-RPC framing from non-protocol log output |
| 02-01 | Use PBKDF2-SHA256 (stdlib) with per-key salt for API key storage | Keep hashes non-reversible without introducing new crypto dependencies |
| 02-01 | Encode stored hashes as `scheme$iterations$salt$digest` | Preserve algorithm metadata for deterministic future verification and migrations |
| 02-01 | Default blank API key role values to `readonly` | Maintain deny-by-default posture for newly issued keys |
| 02-02 | Enforce auth only on `tools/list` and `tools/call` in this plan | Satisfy AUTH-03/04 while preserving existing non-tool passthrough behavior |
| 02-02 | Read credentials from request context metadata and HTTP request objects | Keep auth extraction compatible across stdio and HTTP transports |
| 02-02 | Return generic `Unauthorized` MCP errors without key details | Prevent sensitive credential leakage in error responses |
| 02-03 | Build key lifecycle commands with stdlib `argparse` (`create`, `list`, `revoke`) | Keep operator workflow dependency-light and easy for demo environments |
| 02-03 | Limit CLI key visibility to one-time creation output plus non-secret listing metadata | Prevent accidental key/hash disclosure while preserving operational usability |
| 02-03 | Bootstrap schema and close Postgres pool within each keys command invocation | Keep local/demo CLI execution reliable without manual database prep/cleanup |
| 03-01 | Model policies with explicit `admin`, `user`, and `readonly` role keys | Keep authorization behavior predictable and avoid drifting dynamic role maps |
| 03-01 | Support wildcard tool access via `*` for admin policies only | Preserve explicit allow-list semantics while keeping non-admin roles deny-by-default |
| 03-01 | Fail closed on missing/invalid policy files via `PolicyLoadError` | Prevent Sentinel from starting without a trusted policy source |
| 03-02 | Return structured authorization decisions (`allowed`, `reason`, `matched_rule`) from middleware | Prepare policy evaluations for future audit and observability without re-parsing handler state |
| 03-02 | Enforce authz for both `tools/call` and `tools/list` filtering | Reduce sensitive tool discovery while keeping invocation checks non-bypassable |
| 03-02 | Resolve startup policy path via `SENTINEL_POLICY_PATH` with `config/policies.yaml` fallback | Keep runtime policy selection configurable while preserving fail-closed startup behavior |
| 03-03 | Use fixed-window Redis keys bucketed by epoch window for per-key and per-tool counters | Keep limiter deterministic while avoiding additional TTL lookups |
| 03-03 | Enforce both per-api-key and per-tool quotas, denying on first exceeded dimension | Preserve strict abuse controls while minimizing unnecessary limiter operations |
| 03-03 | Apply conservative fallback limits when policy rate-limit config is missing | Avoid accidental rate-limit disablement in partial/misconfigured policy scenarios |
| 03-04 | Execute `tools/call` security gates inline as `auth -> authz -> rate_limit -> forward` | Make pipeline ordering explicit and non-bypassable in one auditable code path |
| 03-04 | Assert upstream call count in security E2E regression scenarios | Ensure denied/limited flows prove side-effect safety, not just status-code correctness |
| 03-04 | Stub limiter Redis eval in authz test module | Keep authorization tests deterministic after pipeline integration without external Redis loop coupling |
| 04-01 | Sanitize and bound audit JSON payloads at model construction time | Prevent oversized rows and secret leakage regardless of logger call site |
| 04-01 | Store audit `role` and `decision` as dedicated columns with JSONB decision payload | Keep later audit queries/filtering straightforward for integration and dashboard plans |
| 04-01 | Treat invalid `api_key_id` values as NULL during persistence | Preserve non-blocking audit writes when identity metadata is malformed |
| 04-02 | Emit audit events from a finally block in `tools/call` handling | Guarantee one audit attempt per tool-call request regardless of allow/deny/failure outcome |
| 04-02 | Restrict denied `response_json` to safe `{code,message}` metadata while storing gate details in `decision` | Preserve forensic detail without leaking sensitive failure internals in response payload storage |

---

## Blockers/Concerns Carried Forward

- None. Ready to continue Phase 4 audit pipeline instrumentation.

---

## Recent Activity

| Date | Activity |
|------|----------|
| 2026-02-14 | Completed 04-02 audit pipeline instrumentation: wired call-path audit events (401/403/200/failure) with integration regression coverage |
| 2026-02-14 | Completed 04-01 audit primitives: bounded/redacted AuditEvent model and Postgres AuditLogger with regression tests |
| 2026-02-13 | Completed 02-03 operator API key CLI (`keys create/list/revoke`) and entrypoint command routing |
| 2026-02-13 | Completed 03-04 explicit auth->authz->rate-limit proxy pipeline wiring with bypass-prevention E2E coverage |
| 2026-02-13 | Completed 03-03 Redis-backed fixed-window limiter, policy middleware, and 429/reset regression coverage |
| 2026-02-13 | Completed 03-02 tool-level authorization middleware/wiring with role matrix regression coverage |
| 2026-02-13 | Completed 03-01 policy schema/loader foundation with default deny-first YAML configuration |
| 2026-02-13 | Completed 02-02 auth middleware + sentinel tool auth enforcement with header/query credential tests |
| 2026-02-13 | Completed 02-01 API key hashing + Postgres key CRUD primitives with lifecycle verification |
| 2026-02-13 | Completed 01-03 MCP passthrough proxy and end-to-end forwarding regression test |
| 2026-02-13 | Completed 01-02 storage layer (Redis wrapper, Postgres schema bootstrap, smoke check) |
| 2026-02-13 | Completed 01-01 foundation scaffold; summary and user setup docs generated |
| 2026-02-08 | Project initialized, requirements defined, roadmap created |

---

## Next Steps

1. Execute `.planning/phases/04-audit/04-03-PLAN.md`.
2. Build the audit dashboard view over persisted `audit_events` data.
3. Continue progressing Phase 5 demo/submission deliverables after Phase 4 completion.

---

## Session Continuity

- Last session: 2026-02-14T01:17:59Z
- Stopped at: Completed 04-02-PLAN.md
- Resume file: `.planning/phases/04-audit/04-03-PLAN.md`

---

*Last updated: 2026-02-14*
