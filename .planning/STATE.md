# ToolchainGate - Project State

## Current Position

Phase: 2 of 5 (Authentication)
Plan: 1 of 3
Status: In progress
Last activity: 2026-02-13 - Completed 02-01-PLAN.md
Progress: ████░░░░░░░░░░░░ 4/16 plans (25%)

---

## Phase Status

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 1 | Foundation | Complete | 3/3 plans |
| 2 | Authentication | In Progress | 1/3 plans |
| 3 | Authorization & Rate Limiting | Not Started | 0/4 plans |
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

---

## Blockers/Concerns Carried Forward

- None. Ready to continue Phase 02 authentication work.

---

## Recent Activity

| Date | Activity |
|------|----------|
| 2026-02-13 | Completed 02-01 API key hashing + Postgres key CRUD primitives with lifecycle verification |
| 2026-02-13 | Completed 01-03 MCP passthrough proxy and end-to-end forwarding regression test |
| 2026-02-13 | Completed 01-02 storage layer (Redis wrapper, Postgres schema bootstrap, smoke check) |
| 2026-02-13 | Completed 01-01 foundation scaffold; summary and user setup docs generated |
| 2026-02-08 | Project initialized, requirements defined, roadmap created |

---

## Next Steps

1. Execute `.planning/phases/02-authentication/02-02-PLAN.md`.
2. Layer API key authentication checks into Sentinel proxy request handling.
3. Add API key extraction from headers/query params and return 401 on missing/invalid keys.

---

## Session Continuity

- Last session: 2026-02-13T04:13:26Z
- Stopped at: Completed 02-01-PLAN.md
- Resume file: `.planning/phases/02-authentication/02-02-PLAN.md`

---

*Last updated: 2026-02-13*
