<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/brand/logo-horizontal-dark.svg">
  <img alt="Bansho" src="docs/brand/logo-horizontal.svg" width="640">
</picture>

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**An MCP security gateway — adds auth, rate limits, and audit logging between your AI client and any MCP server.**

Bansho sits in front of any MCP server and adds API-key authentication, role-based tool authorization, Redis rate limiting, and PostgreSQL audit logging — all without touching a line of upstream code.

---

## How It Works

```
MCP Client (Claude Desktop, Cursor, etc.)
        │  JSON-RPC over stdio  (bansho serve)
        │  API key in metadata headers / X-API-Key
        ▼
┌──────────────────────────────────────────────────────────────┐
│                       Bansho Gateway                         │
│                                                              │
│  1. Auth      — resolve API key → role (Postgres api_keys)   │
│  2. AuthZ     — check role against YAML tool allow-list       │
│  3. Rate limit — fixed-window counter (Redis)                │
│  4. Audit     — persist event to Postgres audit_events       │
│  5. Forward   — pass allowed request to upstream             │
└──────────────────────────────────────────────────────────────┘
        │  stdio or HTTP/SSE upstream
        ▼
Upstream MCP Server (any MCP server, unchanged)
```

**What each store does:**

| Store | Purpose |
|-------|---------|
| **PostgreSQL** | `api_keys` table (hashed key + role), `audit_events` table |
| **Redis** | Fixed-window rate-limit counters (per key + per tool, with TTL) |

---

## Features

- **MCP passthrough proxy** — stdio and HTTP upstream transports; protocol-transparent
- **API key authentication** — PBKDF2-hashed keys stored in Postgres; extracted from `Authorization: Bearer`, `X-API-Key`, or `?api_key=`
- **Role-based tool authorization** — YAML policy maps roles to allowed tools; `tools/list` visibility is filtered per-caller
- **Redis fixed-window rate limiting** — separate per-key and per-tool quotas; per-tool overrides supported
- **PostgreSQL audit log** — every tool call persisted with timestamp, key ID, role, method, status, latency, and full decision payload
- **Audit dashboard** — lightweight HTML UI + JSON API (`GET /api/events`) for operator review
- **Fail-closed** — policy load failure, missing key, unknown role, and exceeded limits all deny by default
- **Zero upstream changes** — wrap any existing MCP server without modifying it

---

## Quickstart

**Prerequisites:** Go 1.21+, Docker

```bash
# 1. Clone and configure
git clone https://github.com/Microck/bansho.git
cd bansho
cp .env.example .env

# 2. Start Redis and Postgres
docker compose up -d redis postgres

# 3. Build
mkdir -p bin
go build -o ./bin/bansho ./cmd/bansho
go build -o ./bin/vulnerable-server ./cmd/vulnerable-server

# 4. Create an API key
./bin/bansho keys create --role admin
# → api_key_id: <uuid>
# → api_key: bsk_...

# 5. Start the gateway (stdio mode, upstream is the demo server)
export UPSTREAM_TRANSPORT=stdio
export UPSTREAM_CMD="./bin/vulnerable-server"
./bin/bansho serve
```

Bansho logs startup metadata to stderr:

```
bansho_proxy_start listen_addr=127.0.0.1:9000 upstream_transport=stdio upstream_target=./bin/vulnerable-server policy_path=config/policies.yaml
```

---

## Installation

### From source

```bash
git clone https://github.com/Microck/bansho.git
cd bansho
go build -o ./bin/bansho ./cmd/bansho
```

### Binaries

No pre-built binaries are published yet. Build from source with Go 1.21+.

### Docker

```bash
docker compose up -d redis postgres
```

The `docker-compose.yml` starts:
- `redis:7-alpine` on `127.0.0.1:6379`
- `postgres:16-alpine` on `127.0.0.1:5433` (user/pass/db: `bansho`)

---

## Usage

### stdio upstream (spawn a local server)

Set `UPSTREAM_TRANSPORT=stdio` and `UPSTREAM_CMD` to the command that launches your upstream MCP server:

```bash
export UPSTREAM_TRANSPORT=stdio
export UPSTREAM_CMD="python -m my_mcp_server --some-flag"
./bin/bansho serve
```

Bansho spawns the command as a subprocess and communicates over stdin/stdout.

### HTTP upstream (forward to a running server)

Set `UPSTREAM_TRANSPORT=http` and `UPSTREAM_URL` to the upstream MCP endpoint:

```bash
export UPSTREAM_TRANSPORT=http
export UPSTREAM_URL=http://127.0.0.1:8080/mcp
./bin/bansho serve
```

### Passing the API key from a client

MCP clients send the key via request metadata. Bansho looks for it in three locations (in priority order):

| Location | Example |
|----------|---------|
| `Authorization` header | `Authorization: Bearer bsk_abc123` |
| `X-API-Key` header | `X-API-Key: bsk_abc123` |
| Query string | `?api_key=bsk_abc123` |

---

## CLI Reference

### `bansho serve`

Starts the MCP gateway. All configuration is via environment variables (see [Configuration](#configuration)).

```
bansho serve
```

### `bansho dashboard`

Starts the audit dashboard HTTP server on `DASHBOARD_HOST:DASHBOARD_PORT` (default `127.0.0.1:9100`).

```
bansho dashboard
```

Requires an `admin` API key to access (`X-API-Key` or `Authorization: Bearer`).

### `bansho keys create`

Creates a new API key and prints the plaintext value (only shown once).

```
bansho keys create [--role <role>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--role` | `readonly` | Role to assign (`admin`, `user`, `readonly`, or any role in your policy) |

**Example:**

```bash
./bin/bansho keys create --role admin
# api_key_id: 3f2b1c0a-...
# api_key: bsk_a1b2c3d4...
```

### `bansho keys list`

Lists all API keys (ID, role, revoked status). The plaintext key is never shown again after creation.

```
bansho keys list
```

Output:

```
api_key_id                            role      revoked
3f2b1c0a-...                          admin     no
7a9e4d1f-...                          readonly  no
```

### `bansho keys revoke`

Revokes an API key by ID. Revoked keys are immediately rejected on all subsequent requests.

```
bansho keys revoke <api_key_id>
```

**Example:**

```bash
./bin/bansho keys revoke 3f2b1c0a-0000-0000-0000-000000000000
# Revoked API key: 3f2b1c0a-0000-0000-0000-000000000000
```

---

## Configuration

All settings are read from environment variables. Copy `.env.example` to `.env` for local development:

```bash
cp .env.example .env
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BANSHO_LISTEN_HOST` | `127.0.0.1` | Bind host for the MCP gateway |
| `BANSHO_LISTEN_PORT` | `9000` | Bind port for the MCP gateway |
| `DASHBOARD_HOST` | `127.0.0.1` | Bind host for the dashboard server |
| `DASHBOARD_PORT` | `9100` | Bind port for the dashboard server |
| `UPSTREAM_TRANSPORT` | `stdio` | Upstream transport: `stdio` or `http` |
| `UPSTREAM_CMD` | _(empty)_ | Command to spawn (required when `UPSTREAM_TRANSPORT=stdio`) |
| `UPSTREAM_URL` | _(empty)_ | Upstream HTTP endpoint (required when `UPSTREAM_TRANSPORT=http`) |
| `POSTGRES_DSN` | `postgresql://bansho:bansho@127.0.0.1:5433/bansho` | PostgreSQL connection string |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis connection URL |
| `BANSHO_POLICY_PATH` | `config/policies.yaml` | Path to the YAML policy file |

### Policy YAML schema

`config/policies.yaml` controls which tools each role may call and the rate-limit quotas:

```yaml
roles:
  admin:
    allow:
      - "*"            # wildcard: all tools allowed
  user:
    allow:
      - public.echo    # only this tool
  readonly:
    allow:
      - public.echo

rate_limits:
  per_api_key:
    requests: 120      # max 120 requests per key per window
    window_seconds: 60
  per_tool:
    default:
      requests: 30     # default per-tool quota
      window_seconds: 60
    overrides:
      public.echo:     # tighter quota for this specific tool
        requests: 10
        window_seconds: 60
```

**Behavior:**

- Unknown or missing roles are **denied by default**.
- `allow: ["*"]` grants wildcard access to all tools for that role.
- `tools/list` responses are filtered — callers only see tools their role allows.
- Per-tool overrides in `rate_limits.per_tool.overrides` take precedence over `default`.
- If the policy file fails to load, Bansho **fails closed** at startup.
- Override the policy path at runtime: `BANSHO_POLICY_PATH=/path/to/custom.yaml`

---

## Demo — Before / After

The repo includes an intentionally vulnerable MCP server to demonstrate the value of the gateway.

**Before state:** the vulnerable server (`cmd/vulnerable-server`) exposes `list_customers` and `delete_customer` with zero authentication. Any client can call any tool.

**After state:** Bansho intercepts every call. Clients without a valid API key receive `401`. Clients calling a tool outside their role receive `403`. Clients exceeding the rate limit receive `429`. Valid callers get `200`.

### Run the end-to-end demo

```bash
bash demo/run_before_after.sh
```

The script:
1. Starts Redis + Postgres via Docker Compose and waits for health checks
2. Builds all Go binaries (`bansho`, `vulnerable-server`, `demo-attack`, `demo-after`)
3. Runs the **before-state** attack — confirms the vulnerable server allows unauthorized calls
4. Creates `readonly` and `admin` API keys
5. Runs the **after-state** checks through Bansho — asserts `401`, `403`, `429`, and `200` outcomes
6. Verifies audit rows increased in Postgres
7. Starts the dashboard and confirms the events API returns audit evidence

Expected final lines:

```
==> Demo complete
Success: before/after demo ran with deterministic 401/403/429/200 + audit evidence.
```

---

## Dashboard / Audit API

Start the audit dashboard:

```bash
./bin/bansho dashboard
# Listening on http://127.0.0.1:9100
```

All endpoints require an `admin` API key (via `X-API-Key`, `Authorization: Bearer`, or `?api_key=`).

### `GET /dashboard`

HTML audit table with filter controls (API key ID, tool name, limit).

### `GET /api/events`

JSON audit feed.

**Query parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `limit` | `50` | Number of events to return (max `200`) |
| `api_key_id` | _(all)_ | Filter by key UUID |
| `tool_name` | _(all)_ | Filter by tool name |

**Example:**

```bash
curl -H "X-API-Key: bsk_yourAdminKey" \
  "http://127.0.0.1:9100/api/events?limit=5"
```

**Response:**

```json
{
  "count": 2,
  "filters": { "api_key_id": null, "tool_name": null, "limit": 5 },
  "events": [
    {
      "ts": "2026-07-15T10:23:44Z",
      "api_key_id": "3f2b1c0a-...",
      "role": "readonly",
      "method": "tools/call",
      "tool_name": "delete_customer",
      "status": 403,
      "latency_ms": 2,
      "decision": {
        "auth":  { "allowed": true,  "api_key_id": "3f2b1c0a-...", "role": "readonly" },
        "authz": { "allowed": false, "role": "readonly", "reason": "tool_not_allowed_for_role" },
        "rate":  { "allowed": false, "reason": "not_evaluated" }
      }
    }
  ]
}
```

Each event's `decision` object records the outcome of every pipeline stage (`auth`, `authz`, `rate`).

---

## Architecture

```mermaid
graph TD
    Client["MCP Client\n(Claude Desktop / Cursor / custom)"]
    Gateway["Bansho Gateway\n(bansho serve)"]
    Auth["Auth middleware\napi_keys table lookup\nPBKDF2 verify"]
    AuthZ["AuthZ middleware\nYAML role policy\ntools/list filter"]
    RL["Rate limiter\nRedis fixed-window\nper-key + per-tool"]
    Audit["Audit logger\naudit_events table\nstatus + decision JSON"]
    Upstream["Upstream MCP Server\n(stdio or HTTP)"]
    PG[("PostgreSQL\napi_keys\naudit_events")]
    Redis[("Redis\nrate-limit counters")]

    Client -->|"JSON-RPC + API key"| Gateway
    Gateway --> Auth
    Auth -->|"resolved role"| AuthZ
    AuthZ -->|"tool allowed"| RL
    RL -->|"within quota"| Audit
    Audit -->|"forwarded request"| Upstream
    Auth --- PG
    Audit --- PG
    RL --- Redis
```

### Pipeline order

Every `tools/call` request passes through four stages in sequence:

1. **Auth** — extract API key from request metadata; verify against Postgres `api_keys`; reject with `401` on failure
2. **AuthZ** — check the resolved role against the YAML policy allow-list for the requested tool; reject with `403` on mismatch
3. **Rate limit** — increment per-key and per-tool Redis counters; reject with `429` when a window is exceeded
4. **Forward** — pass the request to the upstream MCP server and return its response

An audit event is emitted for every call regardless of outcome, capturing the full decision payload for each stage.

### Source layout

```
bansho/
├── cmd/
│   ├── bansho/            # Main binary (serve, dashboard, keys)
│   ├── vulnerable-server/ # Demo insecure MCP server (no auth)
│   ├── demo-attack/       # Simulates unauthorized access against vulnerable server
│   └── demo-after/        # Asserts 401/403/429/200 outcomes through Bansho
├── internal/
│   ├── auth/              # API key creation, resolution, hashing (PBKDF2), revocation
│   ├── proxy/             # MCP gateway: security pipeline + upstream client
│   ├── policy/            # YAML policy loader and role/tool allow-list evaluator
│   ├── ratelimit/         # Redis fixed-window rate limiter
│   ├── storage/           # Postgres pool, Redis client, schema migrations
│   ├── audit/             # Audit event model, logger, query
│   ├── ui/                # Dashboard HTTP server and JSON API
│   └── config/            # Environment-variable based settings loader
├── config/
│   └── policies.yaml      # Default policy (admin: *, others: empty)
├── demo/
│   ├── policies_demo.yaml # Demo policy (readonly: list_customers, tight rate limits)
│   ├── run_before_after.sh
│   └── README.md
├── docs/
│   ├── architecture.md
│   ├── policies.md
│   └── brand/             # Logo SVGs
├── docker-compose.yml     # Redis + Postgres for local dev
└── .env.example           # Environment variable template
```

---

## Development

### Local dev loop

```bash
# Start dependencies
docker compose up -d redis postgres

# Build and run the gateway (reload by re-running after code changes)
go build -o ./bin/bansho ./cmd/bansho && \
  UPSTREAM_TRANSPORT=stdio \
  UPSTREAM_CMD="./bin/vulnerable-server" \
  ./bin/bansho serve
```

### Rebuilding after changes

Fast rebuild:

```bash
go build -o ./bin/bansho ./cmd/bansho
```

### Policy iteration

Edit `config/policies.yaml` and restart `bansho serve`. Policy is loaded once at startup; changes require a restart.

To test a different policy without touching the default:

```bash
BANSHO_POLICY_PATH=demo/policies_demo.yaml ./bin/bansho serve
```

### Schema migrations

`storage.EnsureSchema` is idempotent. Re-running `bansho serve` or `bansho keys create` against a fresh Postgres instance creates the `api_keys` and `audit_events` tables automatically.

---

## Testing

```bash
go test ./...
```

Integration tests require Redis and Postgres to be running:

```bash
docker compose up -d redis postgres
go test ./...
```

The end-to-end demo also serves as a functional smoke test:

```bash
bash demo/run_before_after.sh
```

---

## Contributing

Issues and pull requests are welcome.

1. Fork the repository
2. Create a feature branch (`git switch -c feat/my-change`)
3. Make your changes and add tests
4. Open a pull request against `main`

Please keep pull requests focused. Security-sensitive changes (auth, key hashing, policy evaluation) require extra care — include a clear description of the threat model impact.

---

## Security

- API keys are hashed with PBKDF2-SHA256 before storage. The plaintext is shown once at creation and never stored.
- Bansho fails closed: missing policy file, unreachable Postgres/Redis, or unknown role all result in denial.
- The `cmd/vulnerable-server` and `cmd/demo-attack` binaries are intentionally insecure demos. **Do not expose the vulnerable server outside a local, controlled environment.**
- To report a security issue, open a GitHub issue with the `security` label or email the maintainer directly.

---

## License

Apache-2.0 — see [LICENSE](LICENSE).

---

## Origin

Built at the **Microsoft AI Dev Days Hackathon 2026**.
