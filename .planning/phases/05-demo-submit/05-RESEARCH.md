# Phase 5: Demo & Submit - Research

**Researched:** 2026-02-14
**Domain:** demo packaging for MCP Bansho (vulnerable server, before/after runner, docs, recording)
**Confidence:** HIGH

<user_constraints>
## User Constraints

No phase CONTEXT.md found for Phase 5.

### Locked Decisions
(none)

### Claude's Discretion
(none)

### Deferred Ideas (OUT OF SCOPE)
(none)
</user_constraints>

## Summary

Phase 5 is about making the already-implemented security proxy easy to judge in minutes: a deliberately vulnerable MCP server (no auth), a deterministic before/after runner that exercises the security controls (401/403/429 + audit evidence), and documentation that lets a stranger reproduce the demo without reading code.

The project already uses the official `mcp` Python SDK on both sides: `mcp.server.stdio.stdio_server` to serve over stdio and `mcp.client.stdio.stdio_client` + `mcp.ClientSession` to drive tool calls. The demo should reuse these exact primitives so the recording is reliable and consistent with the production proxy implementation.

**Primary recommendation:** implement the vulnerable upstream as a tiny stdio MCP server, then drive both "before" and "after" via a single script that spawns processes and calls `ClientSession.call_tool(..., meta={"headers": {"x-api-key": ...}})` and `ClientSession.list_tools(params=PaginatedRequestParams(meta=...))` to deterministically show 401/403/429 and confirm audit rows exist.

## Standard Stack

### Core
| Library/Tool | Version | Purpose | Why Standard |
|---|---:|---|---|
| Python | >=3.11 | runtime | repo baseline (`pyproject.toml`) |
| `mcp` | >=1.26.0 | MCP server/client SDK | already used by Bansho proxy and tests |
| Docker Compose | (local) | Redis + Postgres for demo | matches project infra (`docker-compose.yml`) |
| Postgres | 16 (docker) | audit log + api keys | matches repo (`docker-compose.yml`) |
| Redis | 7 (docker) | rate limiting counters | matches repo (`docker-compose.yml`) |

### Supporting
| Library/Tool | Version | Purpose | When to Use |
|---|---:|---|---|
| `asyncpg` | >=0.31.0 | query audit/events or keys | verifying audit evidence from scripts |
| `pyyaml` | >=6.0.0 | load demo policy YAML | demo policy file validation |
| `uv` | (repo uses `uv.lock`) | deterministic local runs | consistent quickstart commands |
| `bash` | (system) | orchestrate the demo | one-command runner, process control |
| `curl` | (system) | hit dashboard JSON endpoint | optional: show audit evidence via HTTP |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|---|---|---|
| stdio upstream server | streamable HTTP upstream | HTTP adds moving parts; stdio matches existing proxy scaffolding (UpstreamConnector supports both) |

**Installation:**
```bash
uv sync
docker compose up -d
```

## Architecture Patterns

### Recommended Project Structure
```text
demo/
  vulnerable_server.py        # intentionally insecure MCP server (upstream)
  client_attack.py            # BEFORE: talks to vulnerable_server.py directly
  client_after.py             # AFTER: talks to Bansho, demonstrates 401/403/429/200
  policies_demo.yaml          # policy tuned for recording (small limits + clear roles)
  run_before_after.sh         # one command that runs the full story
  recording_checklist.md      # exact steps + narration beats for ~2 min mp4
docs/
  policies.md                 # policy schema + examples
  architecture.md             # system diagram-level explanation
README.md                     # judge-facing quickstart
```

### Pattern 1: Vulnerable MCP server over stdio
**What:** a tiny MCP server exposing a few tools, including one obviously sensitive tool, with *no* auth/authz/rate/audit.
**When to use:** "before" demo; upstream target for Bansho.
**Example:**
```python
# Source: src/bansho/proxy/bansho_server.py (stdio_server + Server request_handlers)
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server


def create_vulnerable_server() -> Server[object, object]:
    server = Server("vulnerable-demo")

    async def list_tools(_req: types.ListToolsRequest) -> types.ServerResult:
        return types.ServerResult(
            types.ListToolsResult(
                tools=[
                    types.Tool(
                        name="public.echo",
                        description="Echo input back",
                        inputSchema={
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                            "additionalProperties": False,
                        },
                    ),
                    types.Tool(
                        name="admin.wipe_all_customers",
                        description="DANGEROUS: wipes all customers (demo-only)",
                        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
                    ),
                ]
            )
        )

    async def call_tool(req: types.CallToolRequest) -> types.ServerResult:
        name = req.params.name
        if name == "admin.wipe_all_customers":
            return types.ServerResult(
                types.CallToolResult(
                    content=[types.TextContent(type="text", text="WIPED ALL CUSTOMERS (unauthenticated!)")],
                    isError=False,
                )
            )
        text = str((req.params.arguments or {}).get("text", ""))
        return types.ServerResult(
            types.CallToolResult(
                content=[types.TextContent(type="text", text=text)],
                isError=False,
            )
        )

    server.request_handlers[types.ListToolsRequest] = list_tools
    server.request_handlers[types.CallToolRequest] = call_tool
    return server


async def run() -> None:
    server = create_vulnerable_server()
    initialization_options = InitializationOptions(
        server_name="vulnerable-demo",
        server_version="0.0.0",
        capabilities={},
        instructions="Intentionally insecure demo server.",
    )
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, initialization_options)
```

### Pattern 2: Demo clients using stdio_client + ClientSession
**What:** client scripts that spawn an MCP server process and call tools via `ClientSession`.
**When to use:** both BEFORE (talk to vulnerable server directly) and AFTER (talk to Bansho proxy).
**Example:**
```python
# Source: src/bansho/proxy/upstream.py (stdio_client + ClientSession)
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def call_sensitive_tool() -> None:
    server = StdioServerParameters(command=".venv/bin/python", args=["demo/vulnerable_server.py"])
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            # BEFORE: no meta at all
            result = await session.call_tool("admin.wipe_all_customers")
            print(result.model_dump(mode="json", exclude_none=True))
```

### Pattern 3: Passing API keys via MCP request meta
**What:** Bansho auth reads API key from request meta headers/query (bearer or x-api-key).
**When to use:** AFTER demo to show 401/403/429/200.
**Example:**
```python
# Source: src/bansho/middleware/auth.py (extract_api_key + meta['headers']/meta['query'])
import mcp.types as types


meta_headers = {"headers": {"x-api-key": "<api_key_value>"}}
await session.call_tool("public.echo", arguments={"text": "ok"}, meta=meta_headers)

params = types.PaginatedRequestParams(meta=meta_headers)
await session.list_tools(params=params)
```

### Anti-Patterns to Avoid
- **Mixing transports in the demo:** Bansho's current entrypoint is stdio (`run_stdio_proxy`); avoid adding an HTTP-facing Bansho mode in Phase 5 just for the demo.
- **Editing `config/policies.yaml` for recording:** keep demo policy separate and select it via `BANSHO_POLICY_PATH=demo/policies_demo.yaml`.
- **Relying on wall-clock rate limits in narration:** make rate-limit triggers deterministic by using very small limits for a specific tool and a tight loop.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| MCP protocol framing | custom JSON-RPC framing | `mcp.server.stdio.stdio_server`, `mcp.client.stdio.stdio_client` | easy to get subtly wrong; repo already uses these |
| Tool request metadata | ad-hoc out-of-band env vars | `meta={"headers": {...}}` / `PaginatedRequestParams(meta=...)` | Bansho auth reads from meta (tests enforce behavior) |
| Policy parsing/validation | custom YAML parsing | `bansho.policy.loader.load_policy()` | schema validation via Pydantic; consistent errors |
| Audit proof | parsing stdout logs | Postgres `audit_events` table or dashboard `/api/events` | deterministic and judge-friendly |
| Process orchestration | complicated orchestration framework | bash + `trap` + `timeout` | fewer dependencies; easy to rerun |

**Key insight:** the demo should reuse the same integration points the tests already exercise (meta-based auth, YAML policy loader, Redis/Postgres backends) so "works on my machine" risk is minimized.

## Common Pitfalls

### Pitfall 1: "Why am I always getting 401?"
**What goes wrong:** the AFTER demo client calls Bansho without meta headers/query, so auth never sees an API key.
**Why it happens:** `ClientSession.call_tool` requires `meta=...` explicitly; and `list_tools` requires meta passed via `PaginatedRequestParams(meta=...)`.
**How to avoid:** always pass API key in `meta["headers"]["x-api-key"]` (or Authorization: Bearer) for all requests you want authenticated.
**Warning signs:** Bansho rejects *every* request including harmless tools; audit rows show `decision.auth.allowed=false`.

### Pitfall 2: Non-deterministic 429 behavior
**What goes wrong:** demo sometimes triggers 429, sometimes doesn't.
**Why it happens:** rate limits are windowed; if the demo straddles a window boundary, counters reset.
**How to avoid:** set a tiny tool limit (e.g., 1 request / 60s) and do 2 sequential calls immediately.
**Warning signs:** repeated runs give different status codes.

### Pitfall 3: Demo script hangs (stdio subprocesses)
**What goes wrong:** background processes remain alive or the script blocks waiting on pipes.
**Why it happens:** stdio MCP servers are long-lived and need explicit termination.
**How to avoid:** in `run_before_after.sh`, use `trap` to kill background PIDs and use `timeout` for each step.
**Warning signs:** `bash demo/run_before_after.sh` never exits.

### Pitfall 4: Dashboard returns 401/403 unexpectedly
**What goes wrong:** dashboard requires an admin key; using a non-admin key returns 403.
**Why it happens:** dashboard auth is separate and checks role == admin.
**How to avoid:** ensure the demo creates an admin key for dashboard access.
**Warning signs:** `/api/events` shows `{"error":{"code":403,...}}`.

## Code Examples

Verified patterns from this repo:

### Start Bansho with a demo policy and a stdio upstream
```bash
# Source: src/bansho/config.py + src/bansho/proxy/upstream.py + src/bansho/proxy/bansho_server.py
export UPSTREAM_TRANSPORT=stdio
export UPSTREAM_CMD="uv run python demo/vulnerable_server.py"
export BANSHO_POLICY_PATH="demo/policies_demo.yaml"

uv run bansho serve
```

### Create API keys for demo roles
```bash
# Source: src/bansho/cli/keys.py
uv run bansho keys create --role admin
uv run bansho keys create --role readonly
```

### Query audit events via dashboard JSON API
```bash
# Source: src/bansho/ui/dashboard.py (/api/events, X-API-Key/Bearer/query api_key)
uv run bansho dashboard &
curl -s -H "X-API-Key: <admin_api_key_value>" "http://127.0.0.1:9100/api/events?limit=5" | head
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| ad-hoc demo steps | one-command runner + recorded checklist | Phase 5 plan | reduces judge friction and makes recording repeatable |
| only show "happy path" | show 401/403/429 + audit proof | Phase 5 requirements | communicates security value clearly |

**Deprecated/outdated:**
- "Demo by describing features" -> the demo should prove enforcement with actual failing/succeeding calls.

## Open Questions

1. **Should the Phase 5 deliverable include an actual `demo/video.mp4` committed to git?**
   - What we know: ROADMAP lists `demo/video.mp4` as a deliverable; plan 05-03 treats recording as manual later.
   - What's unclear: repo policy on committing large binaries.
   - Recommendation: treat `demo/video.mp4` as an external submission artifact unless the hackathon explicitly requires it in-repo.

2. **How should the demo prove audit logging: DB query vs dashboard HTTP call?**
   - What we know: audit rows are written to Postgres; dashboard exposes `/api/events` with admin auth.
   - What's unclear: which is more robust on judge machines.
   - Recommendation: prefer a Postgres count query in the runner (no HTTP dependency) and optionally also `curl` `/api/events` for human-friendly output.

## Sources

### Primary (HIGH confidence)
- `pyproject.toml` (dependencies + versions)
- `docker-compose.yml` (Redis/Postgres versions and ports)
- `src/bansho/proxy/bansho_server.py` (stdio server + enforcement + audit)
- `src/bansho/proxy/upstream.py` (stdio_client + ClientSession patterns)
- `src/bansho/middleware/auth.py` (meta-based API key extraction)
- `src/bansho/policy/models.py` + `src/bansho/policy/loader.py` (policy schema + loading)
- `src/bansho/ui/dashboard.py` (admin-protected audit dashboard + `/api/events`)
- `.planning/ROADMAP.md` (Phase 5 requirements and deliverables)

### Secondary (MEDIUM confidence)
(none)

### Tertiary (LOW confidence)
(none)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - directly from `pyproject.toml` and repo usage
- Architecture: HIGH - existing proxy + tests show the integration points
- Pitfalls: HIGH - derived from tests and actual auth/rate/dashboard behavior

**Research date:** 2026-02-14
**Valid until:** 2026-03-15
