# Bansho

Bansho is an MCP security gateway that sits between MCP clients and upstream MCP servers.
It adds API-key authentication, role-based tool authorization, rate limiting, and audit logging without requiring upstream code changes.

Built for: Microsoft AI Dev Days Hackathon 2026
Categories: Best Enterprise Solution, AI Apps and Agents
Demo video: <paste hosted link>

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

Prereqs:
- Go
- Docker

1. Copy local environment defaults:

```bash
cp .env.example .env
```

2. Start local dependencies:

```bash
docker compose -f docker-compose.yml up -d redis postgres
```

3. Build binaries:

```bash
mkdir -p bin
go build -o ./bin/bansho ./cmd/bansho
go build -o ./bin/vulnerable-server ./cmd/vulnerable-server
```

4. Create an admin API key:

```bash
./bin/bansho keys create --role admin
```

5. Run Bansho against an upstream MCP server:

```bash
export UPSTREAM_TRANSPORT=stdio
export UPSTREAM_CMD="./bin/vulnerable-server"
./bin/bansho serve
```

## Demo (Before vs After)

Run the deterministic end-to-end demo flow:

```bash
bash demo/run_before_after.sh
```

This script demonstrates:
- Before: unauthorized sensitive tool call succeeds.
- After: Bansho enforces `401`, `403`, `429`, and a successful authorized `200`.
- Evidence: audit row count increases and dashboard API returns events.

## Policy Configuration

- Default policy path: `config/policies.yaml`
- Override at runtime: `BANSHO_POLICY_PATH=/path/to/policy.yaml`
- Demo runner uses: `BANSHO_POLICY_PATH=demo/policies_demo.yaml`

Schema and examples: `docs/policies.md`

## Architecture

Component roles, request flow, and data stores: `docs/architecture.md`

## Verification

```bash
go test ./...
```

## Safety

The demo includes an intentionally insecure before-state MCP server under `demo/`.
Only run the vulnerable server locally in a controlled environment.

## License

Apache-2.0 (see `LICENSE`).
