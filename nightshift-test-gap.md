# Nightshift: Test Gap Analysis

**Repo:** Microck/bansho
**Date:** 2026-04-04
**Agent:** Nightshift v3 (GLM 5.1)

## Summary

Bansho has **18 Go source files** in `internal/` but only **2 test files** (`hash_test.go`, `loader_test.go`) plus 1 integration test. Estimated test coverage is **under 15%**. The core security gateway logic (proxy, rate limiting, policy evaluation, audit logging) has zero unit tests.

## Test Coverage Map

| Package | Source Lines | Test Files | Status |
|---------|-------------|------------|--------|
| `internal/proxy` | 672 | 0 | **P0 — No tests** |
| `internal/ui` | 415 | 0 | **P1 — No tests** |
| `internal/audit` | 424 | 0 | **P0 — No tests** |
| `internal/policy` | 282 | 1 (loader_test.go) | P2 — Partial |
| `internal/ratelimit` | 135 | 0 | **P0 — No tests** |
| `internal/auth` | 200 | 1 (hash_test.go) | P2 — Partial |
| `internal/config` | 101 | 0 | P2 — No tests |
| `internal/storage` | 151 | 0 | **P1 — No tests** |
| `cmd/` | ~80 | 0 | P3 — Entry points |
| `integration/` | — | 1 | Existing |

## Priority Gaps (P0)

### 1. `internal/proxy/server.go` (588 lines)
**Risk:** Critical — this is the security gateway's request path. Handles auth, authorization, rate limiting, and upstream proxying.

**Untested functions:**
- `RunStdioGateway()` — full gateway startup
- `handleToolCall()` — tool authorization + rate limit enforcement
- `evaluateAccess()` — combines auth + authz + rate limit decisions
- `defaultDecisionPayload()` — default deny payload
- `safeErrorPayload()` / `safeExceptionPayload()` — error response construction
- `rawArgs()` — argument extraction from MCP requests

**Recommended tests:**
- Auth context resolution (valid key, revoked key, missing key)
- Policy enforcement (admin allowed, readonly denied for restricted tool)
- Rate limiting (within limit, over limit, per-tool override)
- Decision payload structure verification
- Error sanitization (no internal details leaked)

### 2. `internal/audit/models.go` (260 lines)
**Risk:** High — handles sensitive data sanitization and JSON bounding.

**Untested functions:**
- `NormalizeAndBound()` — field normalization and validation
- `sanitizeJSONValue()` — recursive sanitization with depth/item/string limits
- `sanitizeMap()` — sensitive key redaction
- `sanitizeList()` — list truncation
- `boundJSONPayload()` — payload size bounding
- `serializeJSON()` — fallback serialization

**Recommended tests:**
- Sensitive key redaction (`api_key`, `authorization`, `password` etc.)
- Depth limiting (nested objects beyond `MaxJSONDepth=6`)
- Item count limiting (maps/arrays beyond `MaxJSONItems=40`)
- String truncation (values beyond `MaxJSONStringChars=512`)
- Payload bounding (JSON beyond `MaxJSONBytes=4096`)
- Edge cases: nil values, empty strings, NaN/Inf floats

### 3. `internal/ratelimit/limiter.go` (135 lines)
**Risk:** High — rate limiting is a security control.

**Untested functions:**
- `CheckAPIKeyLimit()` — per-key rate limiting
- `CheckToolLimit()` — per-tool rate limiting
- `checkFixedWindowLimit()` — core algorithm
- `windowBucket()` — time bucketing
- `secondsUntilReset()` — reset time calculation
- `coerceInt()` — type coercion from Redis responses

**Recommended tests:**
- Window bucketing math (various `windowSeconds` values)
- Reset time calculation (start/middle/end of window)
- `coerceInt()` for int/int64/float64/string types
- Boundary: requests exactly at limit, one over limit
- Edge cases: zero/negative requests, zero/negative window

## Priority Gaps (P1)

### 4. `internal/ui/dashboard.go` (415 lines)
**Risk:** Medium — HTTP dashboard with auth and query handling.

**Untested functions:**
- `handleDashboard()` / `handleEventsAPI()` — HTTP handlers
- `parseDashboardFilters()` — query parameter parsing
- `renderDashboardHTML()` — template rendering with XSS protection
- `displayRole()` — role name formatting
- `deref()` — nil-safe string dereferencing

**Recommended tests:**
- Filter parsing (valid/invalid limits, empty parameters)
- Role display formatting
- XSS prevention in rendered HTML (user-controlled data in templates)

### 5. `internal/storage/` (151 lines across 3 files)
**Risk:** Medium — database interactions.

**Untested functions:**
- `GetPostgresPool()` — connection pool creation
- `EnsureSchema()` — schema migration
- `GetRedisClient()` — Redis client creation
- `PingRedis()` — connectivity check
- `RedisEval()` — Lua script execution wrapper

## Existing Tests (Good Coverage)

- `internal/auth/hash_test.go` — Tests key generation, hashing, and verification. Good.
- `internal/policy/loader_test.go` — Tests policy loading from demo YAML file. Good.
- `integration/demo_runner_test.go` — End-to-end demo scenario.

## Recommendations

1. **Start with `audit/models.go` tests** — pure functions, no external dependencies, high security impact
2. **Then `ratelimit/limiter.go`** — mock Redis with interface, test algorithm logic
3. **Then `proxy/server.go`** — needs significant mocking (Postgres, Redis, MCP upstream) but is the highest value
4. **Add table-driven tests** — Go idiom, works well for policy/rate-limit/audit boundary conditions
5. **Target: 60% coverage** for the `internal/` packages in the next iteration
