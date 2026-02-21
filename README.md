# Bansho

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Bansho is an MCP security gateway that sits between MCP clients and upstream MCP servers.

It adds API-key authentication, role-based tool authorization, rate limiting, and audit logging without requiring upstream code changes.

## Quickstart

Prereqs:
- Go
- Docker

```bash
cp .env.example .env

docker compose up -d redis postgres

mkdir -p bin
go build -o ./bin/bansho ./cmd/bansho
go build -o ./bin/vulnerable-server ./cmd/vulnerable-server

./bin/bansho keys create --role admin

export UPSTREAM_TRANSPORT=stdio
export UPSTREAM_CMD="./bin/vulnerable-server"
./bin/bansho serve
```

## Features

- MCP passthrough proxy (stdio and HTTP upstream transports)
- API key lifecycle CLI (`bansho keys create|list|revoke`)
- YAML policies for role-to-tool allow lists
- Redis fixed-window rate limiting (per API key and per tool)
- PostgreSQL audit event storage + lightweight dashboard API

## Installation

TODO: document exact Go version and any platform notes.

## Usage

TODO: add examples for stdio vs HTTP upstream, and how clients provide the API key.

## CLI Reference

TODO: document flags and examples:
- `bansho serve`
- `bansho keys create|list|revoke`

## Configuration

Policy configuration:
- Default policy path: `config/policies.yaml`
- Override at runtime: `BANSHO_POLICY_PATH=/path/to/policy.yaml`
- Demo runner uses: `BANSHO_POLICY_PATH=demo/policies_demo.yaml`

See `docs/policies.md` for schema and examples.

## Dashboard / Audit API

TODO: list endpoints + example curl commands.

## Demo

This repo includes an intentionally insecure before-state to demonstrate the value of the gateway.

```bash
bash demo/run_before_after.sh
```

## Development

TODO: document local dev loop (run, reload, policy iteration).

## Testing

```bash
go test ./...
```

## Troubleshooting

TODO: common issues (ports, DSNs, compose not up, policy parse errors).

## Contributing

Issues and pull requests are welcome.

## Support / Community

TODO: add Issues/Discussions links.

## Security

The demo includes a deliberately vulnerable server under `demo/`.
Only run the vulnerable server locally in a controlled environment.

## License

Apache-2.0 (see `LICENSE`).

## Changelog / Releases

TODO: link to GitHub Releases or add `CHANGELOG.md`.

## Roadmap

TODO: add 3-5 near-term improvements (or link to issues/milestones).
