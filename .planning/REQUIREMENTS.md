# Requirements

## v1 Requirements

### Foundation (FOUND)

- [ ] **FOUND-01**: Python project with MCP protocol implementation
- [ ] **FOUND-02**: MCP passthrough proxy (fully spec-compliant)
- [ ] **FOUND-03**: Redis for rate limiting state
- [ ] **FOUND-04**: PostgreSQL for audit logging

### Authentication (AUTH)

- [ ] **AUTH-01**: API key validation middleware
- [ ] **AUTH-02**: API key storage and management
- [ ] **AUTH-03**: Reject unauthenticated requests
- [ ] **AUTH-04**: API key in header or query param

### Authorization (AUTHZ)

- [ ] **AUTHZ-01**: YAML-based policy configuration
- [ ] **AUTHZ-02**: Tool-level access control
- [ ] **AUTHZ-03**: Role-based permissions (admin, user, readonly)
- [ ] **AUTHZ-04**: Policy evaluation on each request

### Rate Limiting (RATE)

- [ ] **RATE-01**: Rate limiting per API key
- [ ] **RATE-02**: Rate limiting per tool
- [ ] **RATE-03**: Configurable limits in policy file
- [ ] **RATE-04**: 429 response on limit exceeded

### Audit (AUDIT)

- [ ] **AUDIT-01**: Log all requests with timestamp
- [ ] **AUDIT-02**: Log client identity (API key)
- [ ] **AUDIT-03**: Log tool name and parameters
- [ ] **AUDIT-04**: Simple dashboard to view logs

### Demo (DEMO)

- [ ] **DEMO-01**: Sample MCP server (vulnerable, no auth)
- [ ] **DEMO-02**: Before/after demo showing security improvement
- [ ] **DEMO-03**: 2-minute video showing security in action
- [ ] **DEMO-04**: README with setup and policy examples

---

## v2 Requirements

### Enhancements

- [ ] OAuth/OIDC integration
- [ ] mTLS support
- [ ] OPA policy engine integration
- [ ] Anomaly detection
- [ ] Multi-server aggregation

---

## Out of Scope

- **OAuth/OIDC** — API keys only for MVP
- **mTLS** — TLS termination only
- **OPA** — simple YAML policies only
- **Multi-server** — single server proxy
- **Anomaly detection** — basic logging only

---

## Traceability

| REQ-ID | Phase | Status | Success Criteria |
|--------|-------|--------|------------------|
| FOUND-01 | Phase 1: Foundation | Pending | Project initialized |
| FOUND-02 | Phase 1: Foundation | Pending | MCP passthrough works |
| FOUND-03 | Phase 1: Foundation | Pending | Redis connected |
| FOUND-04 | Phase 1: Foundation | Pending | PostgreSQL connected |
| AUTH-01 | Phase 2: Authentication | Pending | API key validated |
| AUTH-02 | Phase 2: Authentication | Pending | Keys stored securely |
| AUTH-03 | Phase 2: Authentication | Pending | Unauth rejected with 401 |
| AUTH-04 | Phase 2: Authentication | Pending | Header and query work |
| AUTHZ-01 | Phase 3: Authorization | Pending | YAML policies loaded |
| AUTHZ-02 | Phase 3: Authorization | Pending | Tool access enforced |
| AUTHZ-03 | Phase 3: Authorization | Pending | Roles work correctly |
| AUTHZ-04 | Phase 3: Authorization | Pending | Every request checked |
| RATE-01 | Phase 3: Authorization | Pending | Per-key limits work |
| RATE-02 | Phase 3: Authorization | Pending | Per-tool limits work |
| RATE-03 | Phase 3: Authorization | Pending | Limits configurable |
| RATE-04 | Phase 3: Authorization | Pending | 429 returned correctly |
| AUDIT-01 | Phase 4: Audit | Pending | Requests logged |
| AUDIT-02 | Phase 4: Audit | Pending | Client ID logged |
| AUDIT-03 | Phase 4: Audit | Pending | Tool/params logged |
| AUDIT-04 | Phase 4: Audit | Pending | Dashboard works |
| DEMO-01 | Phase 5: Demo | Pending | Vulnerable server ready |
| DEMO-02 | Phase 5: Demo | Pending | Before/after works |
| DEMO-03 | Phase 5: Demo | Pending | Video recorded |
| DEMO-04 | Phase 5: Demo | Pending | README complete |

**Coverage:** 24/24 requirements mapped (100%)
