# Policy Reference

Bansho reads a YAML policy document with two top-level sections:

- `roles`: tool allow-lists by role (`admin`, `user`, `readonly`)
- `rate_limits`: per-key and per-tool fixed-window quotas

By default Bansho loads `config/policies.yaml`.
Override at runtime with `BANSHO_POLICY_PATH`.

## Schema

```yaml
roles:
  admin:
    allow:
      - "*"
  user:
    allow:
      - public.echo
  readonly:
    allow:
      - public.echo

rate_limits:
  per_api_key:
    requests: 120
    window_seconds: 60
  per_tool:
    default:
      requests: 30
      window_seconds: 60
    overrides:
      public.echo:
        requests: 10
        window_seconds: 60
```

## Behavior Notes

- Missing or unknown roles are denied by default.
- `allow: ["*"]` grants wildcard access for that role.
- Tool override limits in `rate_limits.per_tool.overrides` take precedence over `default`.
- If policy loading fails, Bansho fails closed at startup.

## Demo Policy

The recording flow uses `demo/policies_demo.yaml` with:

- `readonly` allowed only `list_customers`
- `admin` allowed wildcard access
- low per-tool quota on `list_customers` to trigger `429`

Run with:

```bash
BANSHO_POLICY_PATH=demo/policies_demo.yaml ./bin/bansho serve
```
