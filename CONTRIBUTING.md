# Contributing

This is research software: a change is complete only when its numerical claim
is stated precisely and the corresponding check has actually run. Start with
the short status dashboard in `docs/status/dashboard.md`; consult
`PROJECT_PLAN.md` for the authoritative backlog and
`docs/testing/known-issues.md` before investigating a failure.

## Development environment

The supported environment is the repository Docker image, currently based on
DolfinX 0.11. Host Python environments are not used as validation evidence.

```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml ps
```

Frequency-domain tests require the complex DolfinX mode. The test commands in
CI and `PROJECT_PLAN.md` show where it must be enabled.

## Before changing code

1. Check `git status` and preserve unrelated work.
2. Read the relevant package module and its quantitative validation test.
3. Check `docs/testing/known-issues.md` for deliberate or previously diagnosed
   failures.
4. State the physical or software invariant that the change must preserve.

Do not weaken a tolerance merely to make a test pass. A failed analytic,
convergence, conservation, reciprocity, or symmetry check is a result to
diagnose.

## Verification

Use the lightweight matrix for a quick feedback pass:

```bash
./run_tests.sh --smoke
```

Repository verification is performed inside Docker through the logging
harness. A typical standard-tier command is:

```bash
scripts/testing/run_and_log.sh <CHUNK-ID> \
  "docker compose exec -T fem-em-solver bash -lc \
  'cd /workspace && PYTHONPATH=/workspace/src timeout -k 30 180 \
  mpiexec -n 2 python3 -m pytest <test-paths> -v --tb=short'"
```

Never use more than 12 MPI ranks or run one compute command for more than 20
minutes. See `CLAUDE.md` and `PROJECT_PLAN.md` section 5 for the full runtime,
logging, rank-safety, and evidence rules.

Before submitting a change, also run the formatting and static checks used by
CI:

```bash
black --check --diff src tests
isort --check-only --diff src tests
flake8 src tests --max-line-length=100 --extend-ignore=E203,W503
mypy src
```

## Change scope

Keep solver physics, tests, and the claim they license together. Keep generated
simulation output out of Git unless it is an intentional, indexed verification
record. Ansys result numbers are private and must follow the policy in
`CLAUDE.md`; never put them in tracked files, commit messages, or public logs.

Prefer small modules and reusable fixtures. If a change adds substantial
experiment setup to an already large test file, extract the fixture or analysis
helper instead of extending the monolith.
