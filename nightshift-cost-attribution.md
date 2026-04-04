# Nightshift: Cost Attribution Analysis — Bansho

**Repo:** Microck/bansho  
**Date:** 2026-04-04  
**Task:** cost-attribution  
**Category:** analysis

---

## Summary

Bansho is an MCP security gateway that sits in front of MCP servers, adding auth, authorization, rate limiting, and audit logging. It uses PostgreSQL for persistent storage (API keys, audit events) and Redis for rate-limit counters. This report analyzes cost drivers, per-request costs, scaling factors, and proposes a cost attribution model.

---

## 1. Infrastructure Cost Drivers

| Component | Source | Cost Type | Severity |
|-----------|--------|-----------|----------|
| **PostgreSQL** | `internal/storage/postgres.go`, `internal/audit/logger.go` | Fixed + variable | P1 |
| **Redis** | `internal/ratelimit/limiter.go` | Fixed + variable | P2 |
| **Compute** | `cmd/bansho/main.go` (single binary) | Fixed | P2 |
| **Network egress** | Upstream forwarding (`internal/proxy/upstream.go`) | Variable | P3 |
| **Storage growth** | `audit_events` table (JSONB columns) | Variable | P1 |

### P1: Audit storage growth is the dominant long-term cost

Every request writes a full audit event (`internal/audit/logger.go:34-47`) with 3 JSONB columns: `request_json`, `response_json`, and `decision`. Each event contains the full MCP request payload and response. The `NormalizeAndBound()` function caps JSON payloads at 4KB (`MaxJSONBytes = 4096` in `internal/audit/models.go:12`), so worst case is ~12KB JSONB per event plus metadata (~13-14KB per row).

At 1000 req/min, that's ~1.4 GB/day or ~42 GB/month of audit data. No TTL or partitioning exists in the schema (`internal/storage/schema.go`).

### P2: Redis memory is proportional to active rate-limit windows

The rate limiter uses fixed-window counters (`internal/ratelimit/limiter.go:14`). Keys are formatted as `rl:{apiKeyID}:{windowBucket}` and `rl:{apiKeyID}:{toolName}:{windowBucket}`. Each key is a single INCR counter with TTL. Memory per key is negligible (<100 bytes), but at high cardinality (many API keys × many tools), the total is O(keys × tools). The Lua script (`FixedWindowIncrScript`) ensures auto-expiry.

---

## 2. Per-Request Cost Breakdown

Each `tools/call` request passes through 5 stages in `internal/proxy/server.go`:

| Stage | Operations | I/O Cost | Estimated Latency |
|-------|-----------|----------|-------------------|
| **Auth** | PBKDF2 verify + Postgres query | 1 DB read | ~2-5ms |
| **AuthZ** | In-memory YAML policy check | 0 I/O | <0.1ms |
| **Rate limit** | 2× Redis INCR (per-key + per-tool) | 2 Redis writes | ~0.5-1ms |
| **Forward** | Upstream MCP call | 1 upstream call | Variable |
| **Audit** | Postgres INSERT with 3 JSONB columns | 1 DB write | ~1-3ms |

**Per-request infrastructure cost** (at typical cloud pricing):
- Postgres reads: ~$0.0001 (auth lookup scans all non-revoked keys — see `api_keys.go:46`)
- Redis writes: ~$0.00005
- Postgres writes (audit): ~$0.0001
- **Total overhead per request: ~$0.00025** (excluding upstream call)

### P1: Auth query scans all active keys

`ResolveAPIKey()` in `internal/auth/api_keys.go:42-70` queries ALL non-revoked keys and iterates them in Go, performing PBKDF2 verification on each. This is O(n) in number of API keys. At 10,000 keys, that's 10,000 PBKDF2 verifications per request. Should use constant-time lookup (hash-based index or prepared statement).

---

## 3. Cost Scaling Factors

| Factor | Scaling | Threshold |
|--------|---------|-----------|
| Request volume | Linear (audit + rate-limit writes) | Storage dominates after ~1M events |
| Number of API keys | Linear for auth (scan-based) | Auth latency degrades >1000 keys |
| Number of tools | Linear (per-tool rate-limit keys) | Redis memory grows O(keys × tools) |
| Audit retention | Linear storage growth | No auto-cleanup exists |

The system scales linearly in most dimensions. The audit_events table is the primary bottleneck — without partitioning or TTL, query performance degrades as the table grows.

---

## 4. Cost Optimization Opportunities

### P0: Add audit_events retention/TTL

No retention policy exists. Add partitioning by `ts` and a scheduled job to drop old partitions. For most use cases, 30-90 days of audit data is sufficient.

**File:** `internal/storage/schema.go` — add `PARTITION BY RANGE (ts)` or a cron to `DELETE FROM audit_events WHERE ts < NOW() - INTERVAL '90 days'`.

### P1: Index auth lookups instead of full scan

`ResolveAPIKey()` does a full table scan of non-revoked keys. Add a partial index on `key_hash WHERE revoked_at IS NULL` and query by hash prefix, or cache resolved keys in Redis.

**File:** `internal/auth/api_keys.go:46`

### P2: Batch audit writes

Each request does a synchronous INSERT. Consider batching audit events (write to a channel, flush every N events or M milliseconds) to reduce Postgres write amplification.

**File:** `internal/audit/logger.go:34`

### P3: Compress audit JSONB

The `request_json`, `response_json`, and `decision_json` columns are stored as plain JSONB. For large payloads (up to 4KB each after bounding), consider TOAST compression or pre-compressing with gzip before storage.

---

## 5. Cost Attribution Model

### Recommended model: Per-API-key attribution

Since every request is authenticated and audit-logged with `api_key_id`, costs can be directly attributed:

| Cost Category | Attribution Method | Granularity |
|---------------|-------------------|-------------|
| **Compute** | Divide by request count per key | Per-key |
| **Postgres storage** | Sum JSONB size per key's audit events | Per-key |
| **Postgres I/O** | Count reads (auth) + writes (audit) per key | Per-key |
| **Redis memory** | Count unique rate-limit keys per API key | Per-key × per-tool |
| **Network** | Sum request/response payload sizes per key | Per-key |

### Suggested implementation

1. **Materialized view** for cost attribution:
```sql
CREATE MATERIALIZED VIEW cost_attribution AS
SELECT
  api_key_id,
  role,
  COUNT(*) AS total_requests,
  SUM(pg_column_size(request_json) + pg_column_size(response_json) + pg_column_size(decision)) AS audit_bytes,
  SUM(CASE WHEN status_code = 200 THEN 1 ELSE 0 END) AS successful_requests,
  SUM(CASE WHEN status_code != 200 THEN 1 ELSE 0 END) AS rejected_requests,
  AVG(latency_ms) AS avg_latency_ms,
  date_trunc('day', ts) AS day
FROM audit_events
GROUP BY api_key_id, role, date_trunc('day', ts);
```

2. **Redis-based per-key counters** — already available via rate-limit keys; aggregate for attribution.

3. **Cost formula** per key per month:
```
Cost = (requests × $0.00025) + (audit_GB × $0.10) + (compute_hours × $0.05)
```

---

## Recommendations Summary

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| P0 | Add audit_events retention policy | Prevents unbounded storage growth | Low |
| P1 | Index auth lookups | Fixes O(n) auth scan | Low |
| P1 | Add cost attribution materialized view | Enables chargeback | Medium |
| P2 | Batch audit writes | Reduces Postgres write load | Medium |
| P3 | Compress large JSONB payloads | Reduces storage 30-50% | Low |
