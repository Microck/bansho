# Bansho

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Bansho is an MCP security gateway that sits between MCP clients and upstream MCP servers.

It adds API-key authentication, role-based tool authorization, rate limiting, and audit logging without requiring upstream code changes.

<!-- top-readme: begin -->
## Usage

## CLI Reference

## Dashboard / Audit API

## Development

## Troubleshooting

## Support / Community
- [Issues](https://github.com/microck/bansho/issues)

## Changelog / Releases
- [Releases](https://github.com/microck/bansho/releases)

## Roadmap
<!-- top-readme: end -->

## Features

- MCP passthrough proxy (stdio and HTTP upstream transports)
- API key lifecycle CLI (`bansho keys create|list|revoke`)
- YAML policies for role-to-tool allow lists
- Redis fixed-window rate limiting (per API key and per tool)
- PostgreSQL audit event storage + lightweight dashboard API

## Installation

Prereqs:
- Go
- Docker

## Quick Start

1. Copy local defaults:

```bash
cp .env.example .env
```

2. Start dependencies:

```bash
docker compose up -d redis postgres
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

5. Run the proxy:

```bash
export UPSTREAM_TRANSPORT=stdio
export UPSTREAM_CMD="./bin/vulnerable-server"
./bin/bansho serve
```

## Demo

This repo includes an intentionally insecure before-state to demonstrate the value of the gateway.

- Video: TBD
- Deterministic runner:

```bash
bash demo/run_before_after.sh
```

## Configuration

Policy configuration:

- Default policy path: `config/policies.yaml`
- Override at runtime: `BANSHO_POLICY_PATH=/path/to/policy.yaml`
- Demo runner uses: `BANSHO_POLICY_PATH=demo/policies_demo.yaml`

See `docs/policies.md` for schema and examples.

## Architecture

See `docs/architecture.md` for component roles, request flow, and data stores.

## Testing

```bash
go test ./...
```

## Security

The demo includes a deliberately vulnerable server under `demo/`.
Only run the vulnerable server locally in a controlled environment.

## Contributing

Issues and pull requests are welcome.

## License

Apache-2.0 (see `LICENSE`).
