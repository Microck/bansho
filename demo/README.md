# Vulnerable Before-State Demo

This folder contains an intentionally insecure MCP setup used for the "before" segment of the hackathon demo.

## What It Shows

- A vulnerable MCP server exposes sensitive tools with no authentication.
- An attack client can list tools and call a sensitive operation without any API key.

## Quickstart

From the repository root:

```bash
mkdir -p bin
go build -o ./bin/vulnerable-server ./cmd/vulnerable-server
go build -o ./bin/demo-attack ./cmd/demo-attack
./bin/demo-attack --server ./bin/vulnerable-server --list-tools-only
```

Expected output includes:

- `Exposed tools: list_customers, wipe_cache, delete_customer`
- `List-tools smoke mode passed.`

Run the attack demonstration (spawns the vulnerable server automatically):

```bash
./bin/demo-attack --server ./bin/vulnerable-server
```

Expected output includes:

- `Exposed tools: list_customers, wipe_cache, delete_customer`
- `UNAUTHORIZED CALL SUCCEEDED`
- `Before-state demo complete: no auth controls blocked the action.`

## Full Before/After Runner

Run the end-to-end hackathon demo flow with one command:

```bash
bash demo/run_before_after.sh
```

The runner:

- Starts Redis and Postgres with Docker Compose and waits for readiness.
- Executes the before-state unauthorized attack.
- Creates deterministic `readonly` and `admin` API keys.
- Starts Bansho against the vulnerable server with `BANSHO_POLICY_PATH=demo/policies_demo.yaml`.
- Asserts after-state outcomes: `401`, `403`, `429`, and `200`.
- Confirms audit rows increase and fetches non-empty dashboard API events.

Expected output includes:

- `After-state checks complete: 401 / 403 / 429 / 200`
- `Audit delta: +... events`
- `Dashboard API returned ... events`
