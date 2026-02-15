# ToolchainGate

## What This Is

A security gateway for the Model Context Protocol (MCP) that adds authentication, authorization, rate limiting, and audit logging to MCP servers. Sits between MCP clients and servers, providing drop-in security without code changes. Built for the Microsoft AI Dev Days Hackathon 2026.

## Core Value

**25% of MCP servers have NO authentication. ToolchainGate is a drop-in gateway that secures any MCP server with auth, rate limiting, and audit logging — zero code changes required.**

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] MCP protocol passthrough (fully spec-compliant)
- [ ] API key authentication layer
- [ ] Rate limiting per client/tool
- [ ] Request/response audit logging
- [ ] YAML-based policy configuration
- [ ] Tool-level access control
- [ ] Simple dashboard for viewing audit logs
- [ ] 2-minute demo video showing before/after security

### Out of Scope

- OAuth/OIDC integration — API keys only for MVP
- mTLS support — TLS termination only
- OPA policy engine — simple YAML policies only
- Multi-server aggregation — single server proxy
- Anomaly detection — basic logging only

## Context

**Hackathon:** Microsoft AI Dev Days 2026 (Feb 10 - Mar 15, 2026)

**Target Prizes:**
- Primary: Enterprise ($10,000)
- Secondary: AI Apps & Agents ($20,000)

**Why This Wins:**
- VERIFIED pain point: 50% cite security as top MCP challenge
- 25% of MCP servers have NO authentication (Zuplo Report)
- Perfect timing: MCP donated to Linux Foundation (Dec 2025)
- 72% expect increased MCP usage

**Source:** Zuplo State of MCP Report (Jan 13, 2026)

**Key Stats:**
- 25% of MCP servers have NO authentication
- 50% cite security/access control as TOP challenge
- 38% say security concerns block MCP adoption
- 58% are just wrapping APIs without security

## Constraints

- **Timeline**: 5 weeks (Feb 10 - Mar 15, 2026)
- **Perfect Tech Stack**:
  - **Language**: Go (single static binary, great for gateways)
  - **MCP**: official MCP Go SDK (`github.com/modelcontextprotocol/go-sdk`) for spec-compliant server/client + stdio/command transports
  - **Core**: MCP reverse proxy + security middleware pipeline (auth -> authz -> rate limit -> forward)
  - **Storage**: PostgreSQL (audit logs), Redis (rate limiting)
  - **Config**: YAML policies + env-driven runtime settings
  - **Testing**: Go test + table-driven tests; integration tests using docker compose
- **Demo**: 2-minute video required

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Sidecar pattern | Drop-in, no server code changes | — Pending |
| API keys first | Simplest auth, most impactful | — Pending |
| YAML policies | Easy to configure, demo-friendly | — Pending |
| Tool-level auth | MCP-native granularity | — Pending |

---
*Last updated: 2026-02-08 after project initialization*
