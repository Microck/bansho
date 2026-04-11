# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Azure deployment support with Azure Cache for Redis and Azure Database for PostgreSQL (`e01a962`)
- GitHub Actions CI workflow (`c28ed41`)
- Cockpit-style audit dashboard with sorting, expansion, export, and keyboard shortcuts (`05db02f`)
- Go demo server and before/after runner (`b7ebe08`)
- MCP gateway proxy with security pipeline (`9778a77`)
- Audit logging and dashboard API (`54d4645`)
- Redis fixed-window rate limiter (`fc29230`)
- YAML policy models and loader (`0a9f90f`)
- API key hashing and keys CLI (`4eb0abc`)
- Postgres/Redis storage primitives (`362e424`)
- Go module scaffold and bansho CLI (`a8f3d86`)
- Vulnerable unauthenticated MCP server for demos (`4f61f80`)
- Unauthorized attack client demo (`5e3d568`)
- Deterministic before-after demo runner (`bb2281f`)
- Demo policy for after-state scenarios (`49b9096`)

### Fixed
- Dashboard column visibility now reliably hides table columns (`e528f83`)

### Changed
- Revise description for clarity and accuracy (`b0180e2`)
- Revise README for clarity and detail (`b4d3eb9`)
- Swap main and accent colors for dark logo variants (`720b7b5`)
- Make README judge-first and add Apache-2.0 license (`1303d66`)

### Removed
- Legacy Python implementation (`5c08d1a`)
- `.planning` scaffolding and draft files (`c96aa11`)
- Demo recording checklists (`303784f`)
- Stale Python demo references (`75e2a65`)
