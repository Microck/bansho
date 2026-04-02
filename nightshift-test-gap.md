# Nightshift: Test Gap Analysis — bansho

**Task:** test-gap (Test Gap Finder)
**Category:** analysis
**Date:** 2026-04-02
**Agent:** Nightshift v3 (GLM 5.1)

## Executive Summary

Bansho is a Go MCP security gateway with **22 source files** across 8 packages and only **3 test files**. The test coverage is estimated at **~15%** of total functions/methods. Critical gaps exist in the proxy, rate limiter, audit, and storage packages which form the core security enforcement pipeline.

| Severity | Count | Area |
|----------|-------|------|
| P0 (Critical) | 3 | Rate limiter logic, API key resolution, audit event validation |
| P1 (High) | 5 | Proxy gateway flow, upstream connection, policy enforcement |
| P2 (Medium) | 6 | Config loading, storage pooling, dashboard handlers |
| P3 (Low) | 3 | CLI argument handling, demo runner, helpers |

## Current Test Coverage

| Package | Source Files | Test Files | Coverage |
|---------|-------------|------------|----------|
| `internal/auth` | 2 | 1 (`hash_test.go`) | ~40% — only hash/verify, missing api_keys.go |
| `internal/policy` | 2 | 1 (`loader_test.go`) | ~30% — only file loading, missing models.go unit tests |
| `internal/proxy` | 2 | 0 | **0%** — no tests at all |
| `internal/ratelimit` | 1 | 0 | **0%** — critical untested logic |
| `internal/audit` | 2 | 0 | **0%** — no tests |
| `internal/storage` | 3 | 0 | **0%** — no tests |
| `internal/ui` | 1 | 0 | **0%** — no tests |
| `cmd/bansho` | 1 | 0 | **0%** — no tests |
| `integration` | — | 1 (`demo_runner_test.go`) | Requires Docker |

## Detailed Findings

### P0-1: Rate limiter fixed-window logic untested
- **File:** `internal/ratelimit/limiter.go`
- **Functions:** `CheckAPIKeyLimit`, `CheckToolLimit`, `checkFixedWindowLimit`, `windowBucket`, `secondsUntilReset`
- **Gap:** The core rate limiting algorithm has zero unit tests. The fixed-window bucket calculation (`windowBucket`) and reset timing (`secondsUntilReset`) are critical for correctness. A bug here means rate limits either don't work or are too aggressive.
- **Suggested tests:**
  - `TestCheckFixedWindowLimit_AllowsWithinLimit` — verify requests within limit pass
  - `TestCheckFixedWindowLimit_BlocksOverLimit` — verify requests exceeding limit are blocked
  - `TestWindowBucket_Calculation` — verify bucket math with known timestamps
  - `TestSecondsUntilReset_EdgeCases` — verify reset time at window boundaries
  - `TestRateLimitKey_Normalization` — verify empty segments get fallback values

### P0-2: API key resolution scans all keys without tests
- **File:** `internal/auth/api_keys.go`
- **Function:** `ResolveAPIKey` (line 42-70)
- **Gap:** This function loads ALL non-revoked API keys from the database and iterates through them checking hashes. It has no pagination, no query optimization, and is completely untested. The `CreateAPIKey`, `ListAPIKeys`, and `RevokeAPIKey` functions are also untested.
- **Suggested tests:**
  - `TestResolveAPIKey_ValidKey` — mock pool, verify correct key resolved
  - `TestResolveAPIKey_EmptyKey` — verify nil return for empty input
  - `TestResolveAPIKey_RevokedKey` — verify revoked keys are skipped
  - `TestCreateAPIKey_NormalizesRole` — verify role normalization
  - `TestRevokeAPIKey_Idempotent` — verify double-revoke doesn't error

### P0-3: Audit event validation and JSON bounding untested
- **File:** `internal/audit/models.go`
- **Function:** `NormalizeAndBound` (line 64+)
- **Gap:** The JSON bounding logic (`boundJSONPayload`) truncates and redacts sensitive fields. This is a security-critical function — if it fails, sensitive data (API keys, tokens) could leak into audit logs. Completely untested.
- **Suggested tests:**
  - `TestNormalizeAndBound_ValidEvent` — verify happy path
  - `TestNormalizeAndBound_EmptyMethod` — verify error for empty method
  - `TestNormalizeAndBound_InvalidStatusCode` — verify rejection of out-of-range codes
  - `TestBoundJSONPayload_SensitiveKeyRedaction` — verify `api_key`, `authorization`, `token` are replaced with `[REDACTED]`
  - `TestBoundJSONPayload_DeepNestingTruncation` — verify `MaxJSONDepth` enforcement
  - `TestBoundJSONPayload_LargeArrayTruncation` — verify `MaxJSONItems` enforcement

### P1-1: Proxy gateway handler untested
- **File:** `internal/proxy/server.go`
- **Function:** `RunStdioGateway`, `handleToolCall`, `handleToolList`
- **Gap:** The entire MCP gateway flow — policy evaluation, rate limiting, audit logging, upstream proxying — has no tests. This is the main entry point of the application.
- **Suggested tests:** Integration test with mock upstream MCP server, verifying:
  - Authorized requests are proxied
  - Unauthorized requests are rejected
  - Rate-limited requests get 429
  - Audit events are logged for each request

### P1-2: Upstream transport selection untested
- **File:** `internal/proxy/upstream.go`
- **Function:** `buildTransport` (line 63-84)
- **Gap:** The transport builder chooses between stdio and HTTP based on config, with command parsing via shlex. Error paths (empty cmd, invalid transport type) are untested.
- **Suggested tests:**
  - `TestBuildTransport_HTTP` — verify HTTP transport creation
  - `TestBuildTransport_Stdio` — verify stdio transport with valid command
  - `TestBuildTransport_EmptyStdioCmd` — verify error for empty UPSTREAM_CMD
  - `TestBuildTransport_EmptyHTTPURL` — verify error for empty UPSTREAM_URL

### P1-3: Policy tool access control untested
- **File:** `internal/policy/models.go`
- **Functions:** `Allows`, `Normalize`, `IsToolAllowed`
- **Gap:** `RoleToolPolicy.Allows()` and `Policy.IsToolAllowed()` have no direct unit tests (only indirect coverage via `loader_test.go`). Edge cases like wildcard matching, unknown roles, and empty tool names are untested.
- **Suggested tests:**
  - `TestAllows_Wildcard` — verify `*` matches any tool
  - `TestAllows_ExactMatch` — verify specific tool names
  - `TestAllows_EmptyToolName` — verify rejection
  - `TestNormalize_DeduplicatesAndTrims` — verify normalization
  - `TestNormalize_WildcardShortCircuit` — verify wildcard replaces entire allow list

### P1-4: Rate limit key format untested
- **File:** `internal/ratelimit/limiter.go`
- **Functions:** `apiKeyRateLimitKey`, `toolRateLimitKey`, `normalizeSegment`
- **Gap:** The Redis key format affects correctness of rate limiting. If the format changes, existing counters become orphaned.
- **Suggested tests:**
  - `TestAPIKeyRateLimitKey_Format` — verify `rl:<key>:<bucket>` format
  - `TestToolRateLimitKey_Format` — verify `rl:<key>:<tool>:<bucket>` format
  - `TestNormalizeSegment_EmptyFallback` — verify fallback to `__unknown_*__`

### P1-5: Audit logger nil-receiver handling untested
- **File:** `internal/audit/logger.go`
- **Functions:** `LogEvent`, `FetchRecentEvents`
- **Gap:** Both methods have nil-receiver checks but these paths are untested. The SQL query builder in `FetchRecentEvents` also has potential SQL injection concerns if the dynamic conditions aren't properly parameterized (they appear to be, but tests would confirm).
- **Suggested tests:**
  - `TestLogEvent_NilLogger` — verify error return
  - `TestLogEvent_NilPool` — verify error return
  - `TestFetchRecentEvents_LimitClamping` — verify limit bounds (1-200)

### P2-1: Config loading edge cases untested
- **File:** `internal/config/config.go`
- **Function:** `Load`
- **Gap:** No tests for invalid port numbers, missing DSN, or unknown transport types.
- **Suggested tests:**
  - `TestLoad_Defaults` — verify defaults without env vars
  - `TestLoad_InvalidPort` — verify error for non-numeric port
  - `TestLoad_InvalidTransport` — verify error for unknown transport

### P2-2: Storage pool singleton behavior untested
- **File:** `internal/storage/postgres.go`, `internal/storage/redis.go`
- **Functions:** `GetPostgresPool`, `GetRedisClient`, `ClosePostgresPool`, `CloseRedisClient`
- **Gap:** The singleton pool pattern with mutex locking is completely untested. Race conditions or leaks would be hard to detect without tests.
- **Suggested tests:**
  - `TestGetPostgresPool_SameDSN` — verify pool reuse
  - `TestGetPostgresPool_DifferentDSN` — verify pool recreation
  - `TestClosePostgresPool_Idempotent` — verify safe double-close

### P2-3: Schema migration idempotency untested
- **File:** `internal/storage/schema.go`
- **Function:** `EnsureSchema`
- **Gap:** Uses `CREATE TABLE IF NOT EXISTS` and `ADD COLUMN IF NOT EXISTS` — idempotent by design, but ALTER statements could fail if column already exists with different type.
- **Suggested tests:** Test with real Postgres instance (integration).

### P2-4: Dashboard HTTP handlers untested
- **File:** `internal/ui/dashboard.go`
- **Functions:** `handleDashboard`, `handleEventsAPI`, `handleKeysAPI`
- **Gap:** HTTP handlers have no tests. Template rendering, query parameter parsing, and auth middleware are all untested.
- **Suggested tests:** Use `httptest.NewRecorder` to test handler responses.

### P2-5: Audit JSON sanitization edge cases
- **File:** `internal/audit/models.go`
- **Function:** `boundJSONPayload`, `redactSensitiveKeys`
- **Gap:** The sensitive key list (`api_key`, `authorization`, etc.) is hardcoded. Missing keys or new patterns won't be caught.
- **Suggested tests:** Exhaustive test of all known sensitive keys, verify nested objects are sanitized.

### P2-6: API key role normalization
- **File:** `internal/auth/api_keys.go`
- **Function:** `normalizeRole` (referenced but not visible in excerpt)
- **Gap:** Role normalization affects authorization decisions. Unknown roles should default to `readonly` (per `DefaultAPIKeyRole`).

### P3-1: CLI argument handling
- **File:** `cmd/bansho/main.go`
- **Function:** `run`, `runServe`, `runDashboard`, `runKeys`
- **Gap:** No tests for CLI subcommand routing, flag parsing, or error output.
- **Suggested tests:** Verify exit codes for valid/invalid commands.

### P3-2: Demo runner requires Docker
- **File:** `integration/demo_runner_test.go`
- **Gap:** Only integration test, skipped without Docker. No fast unit test coverage exists.

### P3-3: Helper functions in ratelimit
- **File:** `internal/ratelimit/limiter.go`
- **Functions:** `coerceInt`, `currentEpoch`
- **Gap:** Small utility functions but affect correctness of rate limiting math.

## Recommendations

1. **Immediate (P0):** Add unit tests for `ratelimit/limiter.go`, `audit/models.go`, and `auth/api_keys.go`. These form the security enforcement pipeline and any bug here is a security vulnerability.

2. **Short-term (P1):** Add proxy handler tests with mock upstream. This validates the end-to-end flow.

3. **Medium-term (P2):** Add config and storage tests. These prevent regression in infrastructure setup.

4. **Test infrastructure:** Consider adding a `testutil` package with mock implementations for `pgxpool.Pool` and `redis.Client` to enable unit testing without external dependencies.

## Estimated Coverage After Fixes

If all P0-P1 gaps are addressed, estimated coverage would increase from ~15% to ~60%.
