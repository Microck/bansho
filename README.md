# Bansho

Bansho is a security gateway for the Model Context Protocol (MCP).
It sits between MCP clients and upstream MCP servers to enforce:

- API key authentication
- Role-based tool authorization
- Per-key and per-tool rate limiting
- Audit logging with a simple dashboard

## Why Bansho

Many MCP servers expose tools with little or no security controls.
Bansho provides a drop-in guard layer without requiring upstream server code changes.

## Features

- MCP protocol passthrough over stdio and HTTP upstream modes
- API key management CLI (`create`, `list`, `revoke`)
- YAML policy configuration for tool-level access
- Redis-backed fixed-window rate limiting
- PostgreSQL-backed audit event storage
- Dashboard and JSON API for recent audit activity

## Requirements

- Python 3.11+
- Redis
- PostgreSQL
- `uv` (recommended) or another Python environment manager

## Quick Start

1) Copy environment settings:

```bash
cp .env.example .env
```

2) Start local dependencies:

```bash
docker compose up -d
```

3) Create an API key:

```bash
uv run bansho keys create --role admin
```

4) Run the proxy:

```bash
uv run bansho serve
```

5) Run the dashboard:

```bash
uv run bansho dashboard
```

## Configuration

Primary settings are in `.env`:

- `BANSHO_LISTEN_HOST`, `BANSHO_LISTEN_PORT`
- `UPSTREAM_TRANSPORT`, `UPSTREAM_CMD`, `UPSTREAM_URL`
- `POSTGRES_DSN`, `REDIS_URL`
- `DASHBOARD_HOST`, `DASHBOARD_PORT`

Policy configuration is loaded from `config/policies.yaml`.

## Testing

```bash
uv run pytest
```
