# Architecture Overview

Bansho operates as a protocol-preserving gateway:

1. **MCP server** toward downstream clients
2. **MCP client** toward an upstream MCP server

It evaluates every tool call against auth, authz, and rate-limit controls before forwarding.

## High-Level Flow

```text
MCP Client
   |
   | JSON-RPC over stdio/HTTP
   v
Bansho (Gateway)
   |- Auth middleware (API key lookup in Postgres)
   |- AuthZ middleware (role + tool policy)
   |- Rate limiter (Redis fixed windows)
   |- Audit logger (Postgres audit_events)
   |
   | MCP passthrough (allowed requests only)
   v
Upstream MCP Server
```

## Components

- `src/bansho/proxy/bansho_server.py`
  - MCP request handlers
  - Security pipeline order: `auth -> authz -> rate-limit -> forward`
  - Audit event emission for allow/deny/failure outcomes

- `src/bansho/middleware/auth.py`
  - Extracts API key from MCP request metadata headers/query
  - Resolves key identity + role from Postgres-backed key store

- `src/bansho/middleware/authz.py`
  - Loads role-to-tool allow rules from YAML policy
  - Filters `tools/list` visibility and gates `tools/call`

- `src/bansho/middleware/rate_limit.py`
  - Enforces per-key and per-tool quotas using Redis counters
  - Returns `429` when a window limit is exceeded

- `src/bansho/audit/logger.py` and `src/bansho/ui/dashboard.py`
  - Persist audit events to Postgres (`audit_events`)
  - Expose dashboard API and HTML viewer for operator review

## Data Stores

- **PostgreSQL**
  - `api_keys` table for hashed key records and role assignment
  - `audit_events` table for request/decision evidence

- **Redis**
  - Fixed-window counters for rate-limit enforcement
  - Per-key and per-tool bucket keys with TTL

## Demo Mode

The before/after demo uses:

- Vulnerable upstream server: `demo/vulnerable_server.py`
- Bansho policy override: `BANSHO_POLICY_PATH=demo/policies_demo.yaml`
- End-to-end runner: `bash demo/run_before_after.sh`
