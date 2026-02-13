# Phase 1: User Setup Required

**Generated:** 2026-02-13
**Phase:** 01-foundation
**Status:** Incomplete

Complete these items for local infrastructure setup. Claude automated project scaffolding and Docker configuration; these checks confirm your local machine is ready.

## Environment Variables

| Status | Variable | Source | Add to |
|--------|----------|--------|--------|
| [ ] | `POSTGRES_DSN` | `.env (local)` | `.env` |
| [ ] | `REDIS_URL` | `.env (local)` | `.env` |

## Account Setup

None - no third-party account setup is required for this phase.

## Dashboard Configuration

None - no external dashboard configuration is required for this phase.

## Local Development

- [ ] Start local data services with Docker Compose:
  - `docker compose up -d redis postgres`

## Verification

After completing setup, verify with:

```bash
docker compose up -d redis postgres
docker compose ps
uv run python -m mcp_sentinel --print-settings
```

Expected results:
- Redis and Postgres are running with healthy status.
- `postgres_dsn` resolves to `postgresql://sentinel:sentinel@127.0.0.1:5433/mcp_sentinel`.
- `redis_url` resolves to `redis://127.0.0.1:6379/0`.

---

**Once all items complete:** Mark status as "Complete" at top of file.
