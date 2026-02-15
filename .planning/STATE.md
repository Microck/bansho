# ToolchainGate - Project State

## Current Position

Phase: 6 of 6 (Go Migration)
Plan: 1 of 1
Status: Phase complete
Last activity: 2026-02-15 - Completed 06-01-PLAN.md
Progress: █████████████████ 17/17 plans (100%)

---

## Phase Status

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 1 | Foundation | Complete | 3/3 plans |
| 2 | Authentication | Complete | 3/3 plans |
| 3 | Authorization & Rate Limiting | Complete | 4/4 plans |
| 4 | Audit | Complete | 3/3 plans |
| 5 | Demo & Submit | Complete | 3/3 plans |
| 6 | Go Migration | Complete | 1/1 plans |

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
| 04-03 | Implement dashboard with stdlib HTTPServer bridged to async Postgres queries via anyio portal | Deliver audit visibility without introducing new web framework dependencies |
| 04-03 | Require admin-role API keys for dashboard access | Keep audit event visibility restricted to operator-level credentials |
| 05-01 | Add `--self-test` mode to vulnerable demo server | Keep before-state verification deterministic without transport coupling |
| 05-01 | Spawn and teardown vulnerable server within attack client script | Make unauthorized demo execution reproducible in one command |
| 05-02 | Keep recording-specific policies in `demo/policies_demo.yaml` | Protect default production-safe policy behavior while enabling deterministic demo outcomes |
| 05-02 | Assert 401/403/429/200 via Sentinel stdio flow inside one runner script | Ensure fast, repeatable, judge-friendly evidence in a single command |
| 05-03 | Add hosted demo video URL placeholder in README | Support out-of-band final video delivery without forcing binary storage in repository |
| 05-03 | Tie docs and recording checklist to `bash demo/run_before_after.sh` | Keep judge verification path deterministic and command-driven |
| 06-01 | Keep existing Postgres schema (`api_keys`, `audit_events`) during migration | Preserve docker-compose/local workflows and avoid migration tooling scope |
| 06-01 | Use MCP Go SDK middleware + low-level tool handlers for proxying | Preserve upstream payloads and enable per-method passthrough without reshaping |
| 06-01 | Run demo checks via Go MCP clients (CommandTransport) | Remove Python tooling dependency from the demo runner |

---

## Blockers/Concerns Carried Forward

- None. Go migration complete; ready for final submission.

---

## Recent Activity

| Date | Activity |
|------|----------|
| 2026-02-15 | Completed 06-01 Go migration: Go MCP gateway, key CLI, YAML policy, Redis limiter, Postgres audit, dashboard API, and Go-only demo runner + integration test |
| 2026-02-15 | Completed 05-03 submission docs and recording checklist: README overhaul, policies reference, architecture overview, and video handoff checklist |
| 2026-02-15 | Completed 05-02 deterministic before/after runner: docker readiness, key provisioning, 401/403/429/200 assertions, and dashboard audit evidence |
| 2026-02-15 | Completed 05-01 vulnerable demo baseline: unauthenticated MCP server, attack client, and before-state quickstart docs |
| 2026-02-14 | Completed 04-03 audit dashboard delivery: admin-protected HTTP/JSON audit event viewer with api_key_id/tool_name filters and CLI wiring |
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

1. Record final 2-minute demo and upload to hosted URL.
2. Replace README `Demo video:` placeholder with the real link.
3. Submit final hackathon package.
4. Optional: archive/remove the legacy Python implementation once the Go surface is accepted.

---

## Session Continuity

- Last session: 2026-02-15T06:38:31Z
- Stopped at: Completed 06-01-PLAN.md
- Resume file: `None (phase complete)`

---

*Last updated: 2026-02-15*
