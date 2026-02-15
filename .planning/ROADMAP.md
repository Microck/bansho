# ToolchainGate Roadmap

## Overview

Security gateway for the Model Context Protocol (MCP) that adds authentication, authorization, rate limiting, and audit logging. Built for Microsoft AI Dev Days Hackathon 2026.

**Timeline:** 5 weeks (Feb 10 - Mar 15, 2026)
**Target Prizes:** Enterprise ($10k), AI Apps & Agents ($20k)

---

## Phase 1: Foundation

**Goal:** MCP passthrough proxy infrastructure

**Duration:** ~1 week

**Status:** Complete (2026-02-13)

**Requirements Covered:**
- FOUND-01: Python project with MCP protocol implementation
- FOUND-02: MCP passthrough proxy (fully spec-compliant)
- FOUND-03: Redis for rate limiting state
- FOUND-04: PostgreSQL for audit logging

**Success Criteria:**
1. Python project initialized with dependencies
2. MCP passthrough works (requests forwarded correctly)
3. Redis connected for state
4. PostgreSQL connected for logs

**Deliverables:**
- `src/proxy/mcp_proxy.py`
- `src/storage/redis.py`
- `src/storage/postgres.py`

---

## Phase 2: Authentication

**Goal:** API key validation layer

**Duration:** ~1 week

**Status:** Complete (Plans 02-01 through 02-03 completed on 2026-02-13)

**Requirements Covered:**
- AUTH-01: API key validation middleware
- AUTH-02: API key storage and management
- AUTH-03: Reject unauthenticated requests
- AUTH-04: API key in header or query param

**Success Criteria:**
1. API key validated on each request
2. Keys stored securely (hashed)
3. Unauthenticated requests rejected with 401
4. Header and query param both work

**Deliverables:**
- `src/mcp_sentinel/auth/hash.py` (completed in 02-01)
- `src/mcp_sentinel/auth/api_keys.py` (completed in 02-01)
- `src/mcp_sentinel/middleware/auth.py` (completed in 02-02)
- `src/mcp_sentinel/proxy/sentinel_server.py` (auth enforcement added in 02-02)
- `tests/test_auth_enforcement.py` (completed in 02-02)
- `src/mcp_sentinel/cli/keys.py` (completed in 02-03)
- `src/mcp_sentinel/main.py` (serve/keys command routing added in 02-03)

---

## Phase 3: Authorization & Rate Limiting

**Goal:** Policy-based access control + rate limits

**Duration:** ~1 week

**Status:** Complete (Plans 03-01 through 03-04 completed on 2026-02-13)

**Requirements Covered:**
- AUTHZ-01: YAML-based policy configuration
- AUTHZ-02: Tool-level access control
- AUTHZ-03: Role-based permissions (admin, user, readonly)
- AUTHZ-04: Policy evaluation on each request
- RATE-01: Rate limiting per API key
- RATE-02: Rate limiting per tool
- RATE-03: Configurable limits in policy file
- RATE-04: 429 response on limit exceeded

**Success Criteria:**
1. YAML policies loaded and parsed
2. Tool access enforced per policy
3. Roles work (admin can delete, user cannot)
4. Every request evaluated against policy
5. Rate limits enforced per key
6. Rate limits enforced per tool
7. Limits configurable in YAML
8. 429 returned when exceeded

**Deliverables:**
- `src/policy/engine.py`
- `src/middleware/authz.py`
- `src/middleware/rate_limit.py`
- `config/policies.yaml`
- `src/mcp_sentinel/proxy/sentinel_server.py` (strict `auth -> authz -> rate_limit -> forward` ordering finalized in 03-04)
- `tests/test_security_pipeline.py` (bypass-prevention E2E regression added in 03-04)

---

## Phase 4: Audit Logging

**Goal:** Request logging + simple dashboard

**Duration:** ~1 week

**Status:** Complete (Plans 04-01 through 04-03 completed on 2026-02-14)

**Requirements Covered:**
- AUDIT-01: Log all requests with timestamp
- AUDIT-02: Log client identity (API key)
- AUDIT-03: Log tool name and parameters
- AUDIT-04: Simple dashboard to view logs

**Success Criteria:**
1. All requests logged with timestamp
2. Client identity (key ID) logged
3. Tool and parameters logged
4. Dashboard shows recent logs

**Deliverables:**
- `src/mcp_sentinel/audit/models.py` (completed in 04-01)
- `src/mcp_sentinel/audit/logger.py` (completed in 04-01)
- `src/mcp_sentinel/ui/dashboard.py` (completed in 04-03)

---

## Phase 5: Demo & Submit

**Goal:** Before/after demo + documentation

**Duration:** ~1 week

**Status:** Complete (Plans 05-01 through 05-03 completed on 2026-02-15)

**Requirements Covered:**
- DEMO-01: Sample MCP server (vulnerable, no auth)
- DEMO-02: Before/after demo showing security improvement
- DEMO-03: 2-minute video showing security in action
- DEMO-04: README with setup and policy examples

**Success Criteria:**
1. Vulnerable MCP server ready for demo
2. Before/after clearly shows security improvement
3. Video demonstrates auth, rate limit, audit
4. README includes setup and policy examples

**Deliverables:**
- `demo/vulnerable_server.py`
- `demo/video.mp4`
- `README.md`
- `docs/policies.md`

---

## Coverage Validation

All 24 v1 requirements are mapped:
- Phase 1: FOUND-01 to FOUND-04 (4 requirements)
- Phase 2: AUTH-01 to AUTH-04 (4 requirements)
- Phase 3: AUTHZ-01 to AUTHZ-04, RATE-01 to RATE-04 (8 requirements)
- Phase 4: AUDIT-01 to AUDIT-04 (4 requirements)
- Phase 5: DEMO-01 to DEMO-04 (4 requirements)

**Total: 24/24 requirements covered (100%)**

---

*Last updated: 2026-02-15*
