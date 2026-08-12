# FEM-EM Solver — agent onboarding

FEniCSX/DolfinX FEM toolkit targeting the MRI-RF-safety slice of Ansys
Electronics Desktop (HFSS + circuit solver first; Pennes bioheat long-term):
construct birdcage coil + gelled saline phantom (± implant) simulations, tune
the coil at 64/128 MHz, extract B1+/SAR/S-parameters. Scope rescoped
2026-08-04 — see PROJECT_PLAN.md §1; parity claims are per-workflow, never
"HFSS parity".
Magnetostatics is validated against closed forms. The time-harmonic path is a
real complex curl-curl solve validated against the analytic lossy plane wave
(`TH-1` closed 2026-07-31; decay/phase constants to < 0.06%, `TH-6`). Coil
loading **is** now gated, but only in the eddy-current regime — `MAT-6` closed
2026-07-31 with ΔR matching Dodd–Deeds to 1.58% at 10 MHz, σ = 100 S/m; the
saline/Larmor case is an extrapolation, not a result. SAR is gated against the
lossy-sphere closed form to 3.5% (`MAT-4` step 1, 2026-08-03) on an **imposed
uniform field**, never on a coil. The package's S-parameters are still a
heuristic (`PORT-1`; one real S-matrix exists, in a test, on a two-loop air
fixture) — read PROJECT_PLAN.md §2 before trusting any S-parameter or
coil-loading/SAR figure. Anything
that solves in the frequency domain needs the complex DolfinX build
(`source /usr/local/bin/dolfinx-complex-mode`); real mode raises.

## Read these before working

- **PROJECT_PLAN.md** — the single source of truth. §2 honest current state,
  §4 definition of done, §5 compute budget + Docker + logging harness,
  §7 chunk backlog (stable IDs; several entries carry ready-to-execute
  implementation plans).
- **docs/testing/known-issues.md** — check BEFORE debugging any failing test.
  A set of failures on main predates you; that file says which.
- **docs/references/** — Jin, *The FEM in Electromagnetics* 3rd ed. is
  available as searchable per-chapter markdown under
  `docs/references/jin-fem-3e/` (gitignored, operator-provided; start at
  `INDEX.md`). Consult it before re-deriving formulation, feed/port-model,
  boundary-condition, or solver theory; cite chapter/section/equation
  numbers in plan annotations. Absent on a fresh clone — see
  `docs/references/README.md`.

## Hard rules

- **Shared 36-core box, 12 cores max for this project.** Declare a tier
  (smoke 30 s / standard 180 s / heavy 1200 s), wrap runs in `timeout` at the
  ceiling, never exceed 20 minutes for a single compute command.
  Overrun ⇒ kill and shrink the case; never just raise the timeout.
- **All verification runs in Docker through the logging harness** (service must
  be Up — `docker compose -f docker/docker-compose.yml ps`):

  ```
  scripts/testing/run_and_log.sh <CHUNK-ID> "docker compose exec -T fem-em-solver \
    bash -lc 'cd /workspace && PYTHONPATH=/workspace/src timeout -k 30 180 \
    mpiexec -n 2 python3 -m pytest <paths> -v --tb=short'"
  ```

  The `-k 30` is mandatory: a plain `timeout` TERM does not reliably stop an
  `mpiexec` job (MAT-6 step 10, 2026-08-12 — a `timeout 590` run burned cores
  for ~1 700 s and wedged the container; recovery is
  `docker compose -f docker/docker-compose.yml up -d --force-recreate`, see
  known-issues).

- `mpiexec -n 12` is the hard ceiling; use the smallest rank count that fits the
  tier, and keep `-n 2` for anything a rank-local bug could hide in (that is the
  only width where a missing reduction is visible in CI).
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

System cron runs headless sessions via `scripts/automation/` on a 90-minute
grid — 3 reviews and 12 implementer runs a day, four runs after each review,
plus one weekly planning review:

- **Plan review** (Fable 5, medium effort, 03:00 / 10:30 / 18:00 local) — audits results
  against §4, rescopes failed attempts, disposes of `recovered/*` branches,
  tops the §9 "On deck" queue up to 5 items. Protocol:
  docs/automation/daily-review.md.
- **Weekly planning review** (Fable 5, high effort, Sunday 01:30 local) —
  owns the long horizon with brutal realism: §6 phase map and §10 roadmap
  (phases → subgoals, dated pace-based assessments), examples/ health, and
  commissioning/adjudicating `examples/ansys_benchmarks/` cases the human
  operator replicates in Ansys Electronics Desktop (PROJECT_PLAN §5.4).
  Never edits §9. Protocol: docs/automation/weekly-review.md.
- **Implementer runs** (Opus, 04:30 / 06:00 / 07:30 / 09:00 and the same
  offsets after each later review) — each attempts the top On-deck item
  inside a 1-hour timebox; incomplete work is parked on `attempt/*` branches
  and journaled in docs/testing/attempts.md, never left on main. A dirty tree
  stops the first run that meets it and is parked on `recovered/*` by the
  second, so an outage costs two slots rather than the rest of the day.
  Protocol: docs/automation/implementer-run.md.

The daily review also maintains a status dashboard for the human operator
(`docs/status/dashboard.md`, republished as a Claude artifact — URL in
daily-review.md step 7); its Waiting-on-you section is the only alerting
channel — scheduled sessions never send push notifications. A PreToolUse
hook (`scripts/automation/hooks/bash_guard.py`, wired in
.claude/settings.json) mechanically denies `mpiexec` rank counts above 12
and pytest runs that bypass the logging harness.

If you are one of these scheduled sessions, your protocol document is
authoritative; read it before acting. If you are an interactive session,
expect these runs to exist: check `git log` and attempts.md before assuming
the tree is as you left it.
