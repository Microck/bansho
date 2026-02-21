# README Outline (Bansho / mcp-sentinel-lite)

This file captures the current README structure, a recommended top-starred-repo-style outline tailored to this project, and a ready-to-copy skeleton you can apply manually.

Apply mode for this run: ON (updated README.md in-place using a safe marker block).

## 1) Current Headings (verbatim)

From `README.md`:

- # Bansho
- ## Usage
- ## CLI Reference
- ## Dashboard / Audit API
- ## Development
- ## Troubleshooting
- ## Support / Community
- ## Changelog / Releases
- ## Roadmap
- ## Features
- ## Installation
- ## Quick Start
- ## Demo
- ## Configuration
- ## Architecture
- ## Testing
- ## Security
- ## Contributing
- ## License

Related (not in the root README) from `demo/README.md`:

- # Vulnerable Before-State Demo
- ## What It Shows
- ## Quickstart
- ## Full Before/After Runner

## 2) Recommended Outline (project-specific)

1. Title + one-line value proposition
2. Quickstart (local, minimal steps)
3. What It Does (gateway model + threat model in 2-4 bullets)
4. Features
5. Installation (prereqs + build)
6. Usage
    - Run gateway (stdio upstream)
    - Run gateway (http upstream)
7. CLI Reference
    - `bansho serve`
    - `bansho keys create|list|revoke`
8. Configuration
    - Environment variables (`.env.example`)
    - Policy file (`config/policies.yaml` / `docs/policies.md`)
    - Data stores (Redis/Postgres via docker-compose)
9. Demo (before/after runner + expected outcomes)
9. Dashboard / Audit API (what it exposes + how to query)
10. Architecture (link to `docs/architecture.md`)
11. Development (local dev setup)
12. Testing
13. Troubleshooting (common misconfig + ports)
14. Contributing
15. Support / Community
16. Security
17. License
18. Changelog / Releases
19. Roadmap

## 3) Mapping (current -> recommended)

| Current heading | Recommended section |
| --- | --- |
| `# Bansho` | Title + one-line value proposition |
| `## Usage` | Usage |
| `## CLI Reference` | CLI Reference |
| `## Dashboard / Audit API` | Dashboard / Audit API |
| `## Development` | Development |
| `## Troubleshooting` | Troubleshooting |
| `## Support / Community` | Support / Community |
| `## Changelog / Releases` | Changelog / Releases |
| `## Roadmap` | Roadmap |
| `## Features` | Features |
| `## Installation` | Installation |
| `## Quick Start` | Quickstart |
| `## Demo` | Demo |
| `## Configuration` | Configuration |
| `## Architecture` | Architecture |
| `## Testing` | Testing |
| `## Security` | Security |
| `## Contributing` | Contributing |
| `## License` | License |

## 4) Missing Sections Checklist

- [x] All recommended sections now exist as headings in `README.md` (inside the `top-readme` marker block).
- [ ] Fill in `Usage` (stdio vs HTTP upstream examples)
- [ ] Fill in `CLI Reference` (document `bansho serve` + `bansho keys create|list|revoke` flags)
- [ ] Fill in `Dashboard / Audit API` (endpoints + examples)
- [ ] Fill in `Development` (local dev loop)
- [ ] Fill in `Troubleshooting` (ports, DSNs, Compose, policy parse failures)
- [ ] Add support channel details under `Support / Community`
- [ ] Decide whether to keep `Changelog / Releases` and `Roadmap` (or link to issues/releases)

## 5) Ready-to-copy README Skeleton (apply-safe marker block)

This is the exact block inserted into `README.md` (after the intro paragraph, before `## Features`).

```md
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
```
