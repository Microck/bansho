# ToolchainGate - Project State

## Current Position

Phase: 3 of 5 (Authorization & Rate Limiting)
Plan: 2 of 4
Status: In progress
Last activity: 2026-02-13 - Completed 03-02-PLAN.md
Progress: ███████░░░░░░░░░ 7/16 plans (44%)

---

## Phase Status

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 1 | Foundation | Complete | 3/3 plans |
| 2 | Authentication | In Progress | 2/3 plans |
| 3 | Authorization & Rate Limiting | In Progress | 2/4 plans |
| 4 | Audit | Not Started | 0/3 plans |
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
| 03-01 | Model policies with explicit `admin`, `user`, and `readonly` role keys | Keep authorization behavior predictable and avoid drifting dynamic role maps |
| 03-01 | Support wildcard tool access via `*` for admin policies only | Preserve explicit allow-list semantics while keeping non-admin roles deny-by-default |
| 03-01 | Fail closed on missing/invalid policy files via `PolicyLoadError` | Prevent Sentinel from starting without a trusted policy source |
| 03-02 | Return structured authorization decisions (`allowed`, `reason`, `matched_rule`) from middleware | Prepare policy evaluations for future audit and observability without re-parsing handler state |
| 03-02 | Enforce authz for both `tools/call` and `tools/list` filtering | Reduce sensitive tool discovery while keeping invocation checks non-bypassable |
| 03-02 | Resolve startup policy path via `SENTINEL_POLICY_PATH` with `config/policies.yaml` fallback | Keep runtime policy selection configurable while preserving fail-closed startup behavior |

---

## Blockers/Concerns Carried Forward

- None. Ready for 03-03 policy-driven rate limiting work.

---

## Recent Activity

| Date | Activity |
|------|----------|
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

1. Execute `.planning/phases/03-authz-rate-limit/03-03-PLAN.md`.
2. Implement Redis-backed per-key and per-tool rate limiting middleware.
3. Add end-to-end pipeline ordering coverage in 03-04 (`auth -> authz -> rate limit`).

---

## Session Continuity

- Last session: 2026-02-13T05:57:59Z
- Stopped at: Completed 03-02-PLAN.md
- Resume file: `.planning/phases/03-authz-rate-limit/03-03-PLAN.md`

---

*Last updated: 2026-02-13*
