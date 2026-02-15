# Recording Checklist

Use this checklist before recording the hackathon demo.

## Pre-Flight

- [ ] Docker Desktop / Docker Engine is running.
- [ ] Ports `5433`, `6379`, and `9100` are free on localhost.
- [ ] Go toolchain is installed (`go version`).
- [ ] Repository root is the current working directory.
- [ ] Demo runner exists: `demo/run_before_after.sh`.

## Recording Command Sequence

Run exactly:

```bash
bash demo/run_before_after.sh
```

## Must-Show Moments

- [ ] **Before state:** unauthorized sensitive action succeeds (`UNAUTHORIZED CALL SUCCEEDED`).
- [ ] **After state:** explicit `401`, `403`, `429`, and successful authorized `200` outputs appear.
- [ ] **Audit proof:** script prints `Audit delta: +... events`.
- [ ] **Dashboard proof:** script prints `Dashboard API returned ... events` with JSON payload snippet.
- [ ] **Final success line:** `Success: before/after demo ran with deterministic 401/403/429/200 + audit evidence.`

## Export Requirements

- [ ] Export as MP4.
- [ ] Target duration: about 2:00.
- [ ] Save local artifact to `demo/video.mp4`.
- [ ] Upload hosted copy and replace README `Demo video:` placeholder URL.
