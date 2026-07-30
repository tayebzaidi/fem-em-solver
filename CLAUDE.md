# FEM-EM Solver — agent onboarding

FEniCSX/DolfinX FEM solver for MRI coils loaded with gelled saline phantoms.
Magnetostatics is validated against closed forms; the time-harmonic path is a
**proxy, not a Maxwell solve** — read PROJECT_PLAN.md §2 before trusting any
frequency-domain output, S-parameter, or green test downstream of it.

## Read these before working

- **PROJECT_PLAN.md** — the single source of truth. §2 honest current state,
  §4 definition of done, §5 compute budget + Docker + logging harness,
  §7 chunk backlog (stable IDs; several entries carry ready-to-execute
  implementation plans).
- **docs/testing/known-issues.md** — check BEFORE debugging any failing test.
  A set of failures on main predates you; that file says which.

## Hard rules

- **Shared 36-core box.** Declare a tier (smoke 30 s / standard 180 s /
  heavy 600 s), wrap runs in `timeout` at the ceiling, never exceed 10 minutes.
  Overrun ⇒ kill and shrink the case; never just raise the timeout.
- **All verification runs in Docker through the logging harness** (service must
  be Up — `docker compose -f docker/docker-compose.yml ps`):

  ```
  scripts/testing/run_and_log.sh <CHUNK-ID> "docker compose exec -T fem-em-solver \
    bash -lc 'cd /workspace && PYTHONPATH=/workspace/src timeout 180 \
    mpiexec -n 2 python3 -m pytest <paths> -v --tb=short'"
  ```

- Prefer `mpiexec -n 2`; wider runs need explicit human approval.
- A chunk is ✅ only per §4: verification executed by the agent itself, at
  least one quantitative assertion (closed form, convergence rate, or a
  conservation/reciprocity identity), elapsed time recorded. Finiteness-only
  checks close nothing.
- Never loosen a failing assertion to make a test pass; a failing analytic
  comparison is evidence about the test as much as the code (PROJECT_PLAN §7,
  MAG table, defect 5).
- Rank-safety: `cell_tags.values`, `assemble_scalar`, local max/min are
  rank-local — reduce before asserting. Point evaluation goes through
  `post.evaluation.evaluate_vector_field_parallel`, never
  `f.eval(points, np.arange(n))`.
- Commit code, tests, harness logs, and PROJECT_PLAN/known-issues updates
  together.
- The project permission allowlist (.claude/settings.json) funnels all compute
  through `run_and_log.sh` / `docker compose` and blocks host package managers,
  network commands, and reads of files outside this repo. Prefer Read/Grep/Glob
  tools over shell readers. For multi-line commit messages use
  `git commit -F <file>` — `$(...)` substitution in commands is denied.

## Chunk execution

Implementation work is delegated per chunk to the `implementer` agent
(.claude/agents/implementer.md, pinned to Opus) — one chunk ID per invocation:
"Use the implementer agent to execute MAG-13." Planning, chunk design, and
review of returned diffs stay in the main (Fable) session.

## Scheduled automation

System cron runs headless sessions via `scripts/automation/`:

- **Daily review** (Fable, 06:12 local) — audits results against §4,
  rescopes failed attempts, maintains the §9 "On deck" queue. Protocol:
  docs/automation/daily-review.md.
- **Implementer runs** (Opus, six daily: every 3 h at :42, 07:42–22:42
  local) — each attempts the
  top On-deck item inside a 1-hour timebox; incomplete work is parked on
  `attempt/*` branches and journaled in docs/testing/attempts.md, never left
  on main. Protocol: docs/automation/implementer-run.md.

If you are one of these scheduled sessions, your protocol document is
authoritative; read it before acting. If you are an interactive session,
expect these runs to exist: check `git log` and attempts.md before assuming
the tree is as you left it.
