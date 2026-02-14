---
phase: 02-authentication
verified: 2026-02-13T21:45:00Z
status: passed
score: 5/5 must-haves verified
automated_verification:
  - test: "stdio transport E2E auth (missing key 401; header+query succeed; revoked key 401)"
    expected: "Bansho enforces 401 on missing/revoked keys; header and query meta authenticate; tools/list and tools/call succeed under valid admin key"
    evidence: "Executed locally via mcp stdio client against a real Postgres-backed key record; upstream was a fake stdio MCP server exposing an echo tool"
human_verification: []
---

# Phase 2: Authentication Verification Report

**Phase Goal:** API key validation layer
**Verified:** 2026-02-13T21:45:00Z
**Status:** passed
**Re-verification:** Yes - automated transport verification added

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | API keys are stored as non-reversible hashes | ✓ VERIFIED | PBKDF2 hashing is implemented and `create_api_key` inserts `key_hash` (not plaintext key) into Postgres: `src/bansho/auth/hash.py:21`, `src/bansho/auth/api_keys.py:20` |
| 2 | A presented API key can be validated against storage | ✓ VERIFIED | Resolver fetches active key hashes and verifies presented key via constant-time compare path: `src/bansho/auth/api_keys.py:39`, `src/bansho/auth/api_keys.py:44`, `src/bansho/auth/hash.py:45` |
| 3 | Requests without an API key are rejected with 401 | ✓ VERIFIED | Middleware raises 401 Unauthorized, server authenticates before tools/list and tools/call, tests assert 401: `src/bansho/middleware/auth.py:42`, `src/bansho/proxy/bansho_server.py:29`, `tests/test_auth_enforcement.py:173` |
| 4 | API key can be provided via header or query param | ✓ VERIFIED | Auth extraction supports `Authorization: Bearer`, `X-API-Key`, and `api_key` query; tests cover bearer/header/query: `src/bansho/middleware/auth.py:59`, `src/bansho/middleware/auth.py:63`, `src/bansho/middleware/auth.py:68`, `tests/test_auth_enforcement.py:234`, `tests/test_auth_enforcement.py:253` |
| 5 | An operator can create and revoke API keys without writing SQL | ✓ VERIFIED | CLI exposes create/list/revoke and calls repository functions; command wired into main entrypoint: `src/bansho/cli/keys.py:52`, `src/bansho/cli/keys.py:105`, `src/bansho/cli/keys.py:154`, `src/bansho/main.py:45` |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/bansho/auth/api_keys.py` | Create/revoke/lookup API keys | ✓ VERIFIED | Exists (94 lines), substantive async CRUD/resolution logic, wired from middleware and CLI: `src/bansho/middleware/auth.py:12`, `src/bansho/cli/keys.py:8` |
| `src/bansho/auth/hash.py` | Constant-time verification + secure hashing | ✓ VERIFIED | Exists (54 lines), substantive PBKDF2 + `hmac.compare_digest`, wired via repository import: `src/bansho/auth/api_keys.py:5` |
| `src/bansho/middleware/auth.py` | Auth middleware producing authenticated context | ✓ VERIFIED | Exists (158 lines), substantive extraction+authentication+401 behavior, wired into server auth path: `src/bansho/proxy/bansho_server.py:14`, `src/bansho/proxy/bansho_server.py:74` |
| `tests/test_auth_enforcement.py` | Auth enforcement regression coverage | ✓ VERIFIED | Exists (283 lines), substantive coverage for missing/invalid/header/bearer/query paths, wired via pytest discovery (`testpaths = ["tests"]`): `pyproject.toml:39` |
| `src/bansho/cli/keys.py` | CLI for create/revoke/list API keys | ✓ VERIFIED | Exists (165 lines), substantive command handlers + DB interactions, wired into package and entrypoint: `src/bansho/cli/__init__.py:1`, `src/bansho/main.py:31` |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `src/bansho/auth/api_keys.py` | `src/bansho/storage/postgres.py` | `api_keys` SQL operations through pool | WIRED | Imports pool provider and executes `INSERT/SELECT/UPDATE` against `api_keys`: `src/bansho/auth/api_keys.py:6`, `src/bansho/auth/api_keys.py:20`, `src/bansho/auth/api_keys.py:39`, `src/bansho/auth/api_keys.py:62` |
| `src/bansho/proxy/bansho_server.py` | `src/bansho/middleware/auth.py` | Server auth gate before tool handlers | WIRED | Uses `authenticate_request` directly (rather than `require_api_key` wrapper) and applies it to both tool list/call paths: `src/bansho/proxy/bansho_server.py:14`, `src/bansho/proxy/bansho_server.py:29`, `src/bansho/proxy/bansho_server.py:39`, `src/bansho/proxy/bansho_server.py:74` |
| `src/bansho/cli/keys.py` | `src/bansho/auth/api_keys.py` | Repository function imports and calls | WIRED | CLI imports and calls create/revoke repository functions: `src/bansho/cli/keys.py:8`, `src/bansho/cli/keys.py:105`, `src/bansho/cli/keys.py:154` |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| --- | --- | --- |
| AUTH-01: API key validation middleware | ✓ SATISFIED | None |
| AUTH-02: API key storage and management | ✓ SATISFIED | None |
| AUTH-03: Reject unauthenticated requests | ✓ SATISFIED | None |
| AUTH-04: API key in header or query param | ✓ SATISFIED | None |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | No TODO/FIXME/placeholder/empty implementation patterns detected in phase-modified auth files | - | None |

### Automated Transport Verification

These runtime checks were executed using the official `mcp` stdio client against the real `bansho` stdio server process, with local Postgres and Redis running.

- Missing key rejects with 401
- Header key authenticates for `tools/list` and `tools/call`
- Query key authenticates for `tools/list`
- Revoked key rejects with 401

### Gaps Summary

No must-have gaps found.

---

_Verified: 2026-02-13T20:57:15Z_
_Verifier: Claude (gsd-verifier)_
