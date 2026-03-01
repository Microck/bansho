# Bansho - Test & Smoke Checklist

Goal: run the exact checks needed before recording the submission video and submitting.

## 0) Repo sanity

```bash
cd projects/bansho
git status --porcelain
```

Expected: no output.

## 1) Tooling sanity

```bash
go version
docker --version
curl --version
```

## 2) Automated tests (Go)

```bash
cd projects/bansho
go test ./...
```

## 3) Full E2E smoke (before/after demo)

This spins up Redis/Postgres via docker-compose, builds binaries, runs the vulnerable
before-state, then runs the secured after-state and verifies audit evidence.

```bash
cd projects/bansho
bash demo/run_before_after.sh
```

Expected:
- before-state prints `UNAUTHORIZED CALL SUCCEEDED`
- after-state asserts `401`, `403`, `429`, and authorized `200`
- script prints an `Audit delta: +... events`
- script prints dashboard JSON evidence

## 4) Submission artifacts

- README: `README.md`
- Architecture diagram: `docs/architecture.svg` (source: `docs/architecture.mmd`)
- Policy docs: `docs/policies.md`
- Recording checklist: `demo/recording_checklist.md`
- Optional local video artifact: `demo/video.mp4`
