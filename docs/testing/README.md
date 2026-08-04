# Testing

Verification is executed by agents through the logging harness — there is no
human-gated test queue. (The old `pending-tests.md` queue and its
`bootstrap_pending_tests.sh` / `run_pending_tests.sh` tooling were removed
2026-08-04; see git history.)

## Running verification

Start the Docker service once per session:

```bash
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml ps   # STATUS must be "Up"
```

Run any verification command through the harness so it is logged in-repo:

```bash
scripts/testing/run_and_log.sh <CHUNK-ID> "docker compose exec -T fem-em-solver \
  bash -lc 'cd /workspace && PYTHONPATH=/workspace/src timeout 180 \
  mpiexec -n 2 python3 -m pytest <paths> -v --tb=short'"
```

See `PROJECT_PLAN.md` §4 (definition of done) and §5 (compute budget, tiers,
Docker) for the rules that govern these runs.

## Lightweight smoke matrix

```bash
./run_tests.sh --smoke
```

This is the fast, solver-free matrix CI runs; it is not sufficient to close a
chunk.

## Output locations

- Full logs: `docs/testing/logs/*.log`
- Summary index: `docs/testing/test-results.md`
- Known pre-existing failures on main: `docs/testing/known-issues.md` — check
  this before debugging any failing test.
