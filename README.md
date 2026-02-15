# Bansho

Bansho is an MCP security gateway that sits between MCP clients and upstream MCP servers.
It adds API-key authentication, role-based tool authorization, rate limiting, and audit logging without requiring upstream code changes.

Demo video: https://example.com/bansho-demo-video

## Why It Matters

Many MCP servers expose powerful tools over stdio/HTTP with little protection.
Bansho enforces a deny-first security posture while preserving normal MCP protocol behavior.

## Features

- MCP passthrough proxy for stdio and HTTP upstream transports
- API key lifecycle CLI (`bansho keys create|list|revoke`)
- YAML policies for role-to-tool allow lists
- Redis fixed-window rate limiting (per API key and per tool)
- PostgreSQL audit event storage with a lightweight dashboard API

## Quickstart

1. Copy local environment defaults:

```bash
cp .env.example .env
```

2. Start local dependencies:

```bash
docker compose -f docker-compose.yml up -d redis postgres
```

3. Create an admin API key:

```bash
uv run bansho keys create --role admin
```

4. Point Bansho at an upstream MCP server and run the proxy:

```bash
export UPSTREAM_TRANSPORT=stdio
export UPSTREAM_CMD="uv run python demo/vulnerable_server.py"
uv run bansho serve
```

5. Optional: run the audit dashboard:

```bash
uv run bansho dashboard
```

## Demo (Before vs After)

Run the deterministic recording flow:

```bash
bash demo/run_before_after.sh
```

The script demonstrates:

- **Before:** unauthorized sensitive tool call succeeds.
- **After:** Bansho enforces `401`, `403`, `429`, and successful authorized `200`.
- **Evidence:** audit row count increases and dashboard API returns events.

## Policy Configuration

- Default policy path: `config/policies.yaml`
- Override policy path at runtime with `BANSHO_POLICY_PATH=/path/to/policy.yaml`
- Demo runner uses `BANSHO_POLICY_PATH=demo/policies_demo.yaml`

See `docs/policies.md` for schema and examples.

## Architecture

See `docs/architecture.md` for component roles, request flow, and data stores.

## Testing

```bash
uv run pytest
```
