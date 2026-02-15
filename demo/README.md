# Vulnerable Before-State Demo

This folder contains an intentionally insecure MCP setup used for the "before" segment of the hackathon demo.

## What It Shows

- A vulnerable MCP server exposes sensitive tools with no authentication.
- An attack client can list tools and call a sensitive operation without any API key.

## Quickstart

From the repository root:

```bash
uv run python demo/vulnerable_server.py --self-test
```

Expected output includes:

- `registered_tools: list_customers, wipe_cache, delete_customer`
- `sensitive_tool_output: WARNING: Deleted customer ...`
- `self-test passed`

Run the attack demonstration (spawns the vulnerable server automatically):

```bash
uv run python demo/client_attack.py
```

Expected output includes:

- `Exposed tools: list_customers, wipe_cache, delete_customer`
- `UNAUTHORIZED CALL SUCCEEDED`
- `Before-state demo complete: no auth controls blocked the action.`

Optional smoke check (list tools only):

```bash
uv run python demo/client_attack.py --list-tools-only
```

Expected output includes:

- `List-tools smoke mode passed.`
- `Server subprocess terminated cleanly.`

## Full Before/After Runner

Run the end-to-end hackathon demo flow with one command:

```bash
bash demo/run_before_after.sh
```

The runner:

- Starts Redis and Postgres with Docker Compose and waits for readiness.
- Executes the before-state unauthorized attack.
- Creates deterministic `readonly` and `admin` API keys.
- Starts Sentinel against the vulnerable server with `BANSHO_POLICY_PATH=demo/policies_demo.yaml`.
- Asserts after-state outcomes: `401`, `403`, `429`, and `200`.
- Confirms audit rows increase and fetches non-empty dashboard API events.

Expected output includes:

- `After-state checks complete: 401 / 403 / 429 / 200`
- `Audit delta: +... events`
- `Dashboard API returned ... events`
