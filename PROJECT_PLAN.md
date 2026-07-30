# PROJECT_PLAN.md — FEM Electromagnetics Solver for MRI Coil Simulation

**This is the single source of truth for project scope, status, and sequencing.**
It supersedes the former `ROADMAP.md` (strategy/chunks are merged here) and
`docs/status.md` (which is now a generated snapshot, not a plan).

Last full review: 2026-07-27.

---

## 1. Mission

A finite element solver built on FEniCSX/DolfinX for electromagnetic simulation of
MRI coils loaded with gelled saline phantoms. Target capability:

1. Generate realistic birdcage coil + phantom geometry
2. Solve magnetostatic and **time-harmonic** Maxwell problems with complex,
   frequency-dependent materials
3. Produce credible field diagnostics and ParaView-friendly outputs
4. Produce lumped-port S-parameters usable for downstream tuning workflows

### Why this exists
- Commercial EM solvers (HFSS, CST) are expensive and black-box
- Open-source alternatives (Elmer, OpenEMS) lack MRI-specific features
- Academic codes often use legacy frameworks
- Need a modern, Python-based, inspectable solver for research and teaching

---

## 2. Honest current state (read this before planning work)

The project has a **validated magnetostatics core** and a **large body of
scaffolding whose green tests do not mean what they appear to mean.** Three facts
govern all sequencing decisions below.

### 2.1 The time-harmonic solver does not solve Maxwell's equations

`src/fem_em_solver/core/time_harmonic.py` runs the *magnetostatic* solver for `A`,
then sets:

```
E_real ≡ 0
E_imag  = -ω·A
```

There is no `ω²εE` term, no `jωσ` term, and no complex linear system. The material
response `σ + jωε₀εᵣ` is computed and then **discarded** (assigned to `_`).

**Consequence:** phantom conductivity and permittivity have zero effect on any
computed field. Coil loading by the phantom — the central purpose of this project —
is not modeled. Every downstream "phantom metric", SAR figure, and consistency
diagnostic is therefore physically meaningless, however well-formed its output.

### 2.2 The S-parameters are heuristic, not computed

`src/fem_em_solver/ports/excitation.py` discards the solved field and derives port
voltages from invented constants:

```python
admittance = material_response * (1e-3 * support)   # `support` = a count of mesh cells
coupling   = orientation_sign * (0.20 / (1.0 + wrapped_distance))
```

`1e-3 * support` is dimensionally meaningless; `0.20` is arbitrary. Every port
track deliverable (reciprocity metrics, Touchstone export, orientation sensitivity)
exercises this placeholder's arithmetic rather than electromagnetics. The
orientation-flip test passes because a helper returns `-1.0` when two orientation
*strings* differ.

### 2.3 Test assertions cannot detect either problem

Finiteness checks (`np.isfinite`, `> 0`) dominate the solver, port, material, and
post-processing suites. Only the Phase-1 magnetostatics tests compare against
analytic solutions with quantitative tolerances. A solver returning `E = -ωA`
passes every time-harmonic, port, and workflow test currently in the repo.

### 2.3b The Phase-1 analytic validation is also broken

Established by execution on 2026-07-27, and it revises what §2.4 can claim.

Nearly every Phase-1 validation test evaluates fields with
`B.eval(points, np.arange(n))`, which asks dolfinx to evaluate each point inside an
arbitrary cell rather than the cell containing it. The resulting numbers are
meaningless. `test_straight_wire.py` additionally applies the wire current over the
whole domain. See `MAG-7`/`MAG-8`/`MAG-9` in §7 for the measured evidence.

Consequence: the claim "validated against analytic solutions" — in the old
`docs/status.md`, in the README, and in earlier reviews of this repo — is **not
supported**. Exactly one Phase-1 test is methodologically sound
(`test_helmholtz_v2.py`), and it checks field *uniformity*, not agreement with a
closed-form magnitude.

### 2.4 What is genuinely trustworthy

- **The magnetostatic formulation in `core/solvers.py` is verified.** N1curl weak
  form `∫μ⁻¹(∇×A)·(∇×v) dx = ∫J·v dx` with gauge penalty, matching the closed-form
  on-axis Helmholtz field to **0.04% at centre / 0.83% mean**, with monotone
  convergence in both domain size and mesh resolution. See `MAG-1`/`MAG-4` in §7.
  This is the project's one solid foundation — and note it took fixing the *tests*
  and the *air box*, not the solver, to demonstrate it.
- `examples/magnetostatics/04_helmholtz_analytic_comparison.py` — the working
  analytic comparison, and the reference pattern for repairing the other tests
- `tests/validation/test_helmholtz_v2.py` — correct point location, real tolerance
- `src/fem_em_solver/post/evaluation.py` — correct bounding-box/collision machinery,
  which the broken tests simply don't use
- Gmsh geometry generation and mesh-tag QA infrastructure
- `scripts/testing/run_and_log.sh` traceability design — now producing real elapsed
  times for the first time in project history

---

### 2.5 Before you debug a failing test

**Check [`docs/testing/known-issues.md`](docs/testing/known-issues.md) first.** It
lists every currently-failing test with its symptom, the commit it was verified
failing at, and the diagnosed cause where one exists.

Nine tests fail on `main` for reasons unrelated to any change you are likely to be
making. Establishing that after the fact costs a `git stash` and re-run per failure.
That file exists so you do not pay it again.

---

## 3. Status legend

| Symbol | Meaning |
|---|---|
| ✅ VERIFIED | Test executed, assertion is quantitative, passing |
| 🟡 IN PROGRESS | Actively being implemented |
| 🧪 UNVERIFIED | Code landed; test has never actually executed anywhere |
| ⚠️ PLACEHOLDER-BACKED | Implemented and "green", but rests on §2.1/§2.2 proxies — green means nothing physically |
| ⬜ NOT STARTED | |
| 🚫 BLOCKED | Cannot proceed; blocker named in the chunk |

`⚠️` is not a bug report against the chunk's own code — it is a statement that the
chunk cannot be trusted until `TH-1` lands. Do not "fix" a `⚠️` chunk by loosening
its test.

---

## 4. Definition of done (revised)

A chunk is done — `✅ VERIFIED` — when **all** of the following hold:

1. **Code and docs are committed.**
2. **The agent executed the verification command itself** and recorded the result
   via `scripts/testing/run_and_log.sh`. A chunk does not park on a human.
3. **The assertion is quantitative.** At least one check must compare against one of:
   - a closed-form analytic solution, with a stated tolerance
   - a measured convergence rate under h- or p-refinement
   - a conservation, reciprocity, or symmetry identity
   - a documented reference value from literature or a prior validated run

   > **Finiteness-only gate:** a chunk may **not** be marked `✅` if every assertion
   > it adds is of the form "is finite", "is non-zero", "has shape N", or "did not
   > raise". Those are smoke checks. They are welcome as *additional* assertions and
   > insufficient as the *only* ones.
4. **Its runtime budget tier is declared and its measured elapsed time recorded.**
5. **Any dependency on a `⚠️` chunk is stated explicitly** in the chunk entry.

### When human verification *is* required

Reserve it for judgments a test genuinely cannot make, and name the judgment:

- "Does this B1+ field map look physically plausible in ParaView?"
- "Is this mesh refinement acceptable near the port faces?"
- "Does this S11 curve resemble published birdcage behavior?"

Never for routine pass/fail. If a human is asked to run something, the chunk entry
must state *what judgment* is being requested, not just "run this and check it passes".

---

## 5. Execution policy

### 5.1 Compute budget — shared machine

The development server is a **shared** resource. Every verification command must
declare a tier, and must not exceed it:

| Tier | Wall-clock ceiling | Use for |
|---|---|---|
| `smoke` | 30 s | Imports, pure-Python logic, config validation, doc presence |
| `standard` | 3 min | Coarse meshes, single small solves — the default for chunk verification |
| `heavy` | 10 min | Convergence studies, multi-frequency sweeps — must be labeled `heavy` in the chunk entry |

Rules:
- Wrap commands in `timeout` at the tier ceiling. **If a run overruns, kill it and
  redesign the case smaller** rather than letting it complete. Do not re-run with a
  longer timeout — that is the failure mode this rule exists to prevent.
- Prefer `mpiexec -n 2`. Wide-rank runs require explicit human approval.
- Record real elapsed time in `docs/testing/test-results.md`.
- **A tier is a measurement, not an intention.** A chunk whose runtime has never been
  measured is `unmeasured`, not `standard`. Before the first full run of an
  `unmeasured` chunk, cost-probe it: build the mesh, print the cell count, and solve
  a deliberately tiny case. Extrapolate, then size the real case to fit the tier.

#### Measured runtimes (2026-07-27, `mpiexec -n 2` unless noted)

| Command | Cells | Elapsed | Tier |
|---|---|---|---|
| `pytest tests/unit` | — | 2 s | smoke |
| `./run_tests.sh --smoke` (13 tests) | — | 1 s | smoke |
| straight-wire probe, solve+eval | 8,210 | 3.4 s | smoke |
| `test_straight_wire.py::test_straight_wire_b_field` | ~4×10⁵ | **>400 s, killed** | infeasible |

The last row is why `MAG-9` exists. Cost is dominated by mesh size: ~8×10³ cells
solve in seconds, ~4×10⁵ cells do not finish inside the budget.

### 5.2 Agent autonomy and loop hygiene

- Agents implement **and verify**. The previous "cron-safe mode forbids solves"
  policy, combined with human-gated completion, produced ~35 consecutive commits of
  the form *"record audit note: no new human test logs found"*. That failure mode is
  now explicitly prohibited.
- **No-op guard:** if a work cycle produces only documentation edits and executes no
  verification command, the agent must stop and escalate rather than commit an audit
  note.
- **Do not append duplicate status blocks.** `docs/testing/pending-tests.md`
  accumulated 19 byte-identical A5 entries. Status lives in the tables in §7 of this
  file; `pending-tests.md` is an append-only *log*, not a status store.

### 5.3 Verification environment — Docker (working as of 2026-07-27)

Verification runs inside the `fem-em-solver` container. **This is the supported and
verified method.** Every command in §7 is written as:

```bash
docker compose exec fem-em-solver bash -lc '...'
```

#### One-time setup

```bash
cd docker
docker compose build     # ~4 min: pulls dolfinx/dolfinx:v0.7.2, compiles h5py from source
docker compose up -d     # start the long-lived service
docker compose ps        # confirm STATUS is "Up"
```

The container mounts the repo at `/workspace`, so **source edits are picked up
without rebuilding.** Rebuild only when `docker/Dockerfile` or dependencies change.

`docker compose exec` fails with `service "fem-em-solver" is not running` if the
service is down — this is what killed three of the seven historical manual runs, and
it is a *setup* error, not a test failure. Always confirm `docker compose ps` first.

#### Environment facts (verified)

| Property | Value |
|---|---|
| Image | `fem-em-solver:latest`, 6.26 GB on disk |
| Base | `dolfinx/dolfinx:v0.7.2`, Python 3.10.12 |
| dolfinx | 0.7.2 |
| Default PETSc scalar | `numpy.float64` — **real mode** |
| Complex build | present at `/usr/local/dolfinx-complex` |
| Memory cap | 16 GB (compose `deploy.resources.limits`) |

**Switching to complex scalars** — required by `TH-1`, since a frequency-domain
Maxwell solve cannot be assembled in real mode:

```bash
source /usr/local/bin/dolfinx-complex-mode   # petsc4py ScalarType -> numpy.complex128
```

`dolfinx-real-mode` switches back. Confirmed working in this image.

> **Why the chunk commands set `PYTHONPATH=/workspace/src`:** that override drops the
> container's dolfinx path. `src/sitecustomize.py` re-appends
> `/usr/local/dolfinx-real/lib/python3.10/dist-packages` so imports still resolve.
> `TH-1` will need to extend that shim, or set PYTHONPATH explicitly, to work under
> complex mode.

#### If `docker` gives "permission denied ... /var/run/docker.sock"

The user must be in the `docker` group. If `getent group docker` already lists the
user but `id` does not show it, the shell's process credentials predate the group
edit. Either start a fresh login shell, or pick up the group in-place:

```bash
sg docker -c '<command>'          # works without logging out; composes with run_and_log.sh
```

#### Running a verification command

Always go through the logging harness so results land in
`docs/testing/test-results.md` and `docs/testing/logs/`:

```bash
scripts/testing/run_and_log.sh <CHUNK-ID> "docker compose exec -T fem-em-solver bash -lc '...'"
```

Use `exec -T` for non-interactive/automated runs; without it, `exec` allocates a TTY
and can hang when driven by an agent. The harness exports `COMPOSE_FILE` itself, so
it can be invoked from any directory — but a bare `docker compose` command outside
`docker/` needs `COMPOSE_FILE=docker/docker-compose.yml` set explicitly.

---

## 6. Phase map

Chunks in §7 are grouped by subsystem; this is how they ladder into capability.

| Phase | Goal | Gating chunks | State |
|---|---|---|---|
| 0 | Infrastructure, packaging, CI, meshing | `OPS-1`, `OPS-2` | Partially done; CI validates almost nothing |
| 1 | Magnetostatics + analytic validation | `MAG-1`…`MAG-6` | **Substantially complete and trustworthy** |
| 2 | Time-harmonic Maxwell, complex materials, ABC/PML | `TH-1`…`TH-9` | **Barely started** — `TH-9` (cavity gate) ✅ 2026-07-30; the driven solver is still §2.1-blocked |
| 3 | Material models, phantoms, SAR | `MAT-1`…`MAT-5` | Presets exist but are inert |
| 4 | Coil modeling, lumped elements, ports, S-params | `PORT-1`…`PORT-8` | Placeholder-backed |
| 5 | Full MRI system: loaded birdcage, B1+, SAR maps | `WF-5`…`WF-8` | Blocked on Phases 2–4 |
| 6 | Advanced: MPI scaling, AMR, sweeps, optimization | — | Deferred |

### Critical path

```
OPS-1 (executable env) ✅        MAG-7/8/9 (repair validation) ✅
   └─> MAG re-run: core/solvers.py matches closed-form to 0.04% ✅
                 └─> TH-1 (real complex time-harmonic formulation)
                        ├─> TH-9/6/7/8 (analytic validation gates; TH-9 first)
                        ├─> MAT-2 (materials actually affect fields)
                        └─> PORT-1 (real port excitation) ──> PORT-2…8
                                                                └─> WF-5…8 (MRI deliverables)
```

Two hard rules follow from the shape of this graph:

- Nothing downstream of `TH-1` should be extended until `TH-1` lands. Adding features
  to a proxy solver is what produced the current `⚠️` backlog.
- **`TH-1` should not start until the MAG re-run passes.** The time-harmonic solver
  is built on `MagnetostaticSolver`; if the magnetostatic formulation has a defect,
  `TH-1` would inherit it and the analytic gates would fail for reasons that have
  nothing to do with the new code.

---

## 7. Chunk backlog

IDs are prefixed by subsystem and are **globally unique and stable**. The legacy
`A1`/`B2`/`C3`-style IDs used in commit messages and `docs/testing/pending-tests.md`
map here via §8.

Per-chunk historical detail (files changed, full pass signals, commit hashes) remains
in `docs/testing/pending-tests.md`. This table is the authoritative *status*.

### OPS — Infrastructure & testing operations

| ID | Title | Status | Tier | Legacy |
|---|---|---|---|---|
| `OPS-1` | Executable verification environment (Docker) | ✅ | smoke | *new* |
| `OPS-2` | CI runs the real test suite, not just `tests/unit` | ⬜ | standard | *new* |
| `OPS-3` | Deterministic test tolerance policy | ✅ | smoke | A2 |
| `OPS-4` | Lightweight smoke matrix | ✅ | smoke | A3 |
| `OPS-5` | Testing status dashboard | ✅ | smoke | A5 |
| `OPS-6` | Expanded run-and-log metadata | ✅ | smoke | F1 |
| `OPS-7` | Guided pending-test queue helper | 🧪 | smoke | F2 |
| `OPS-8` | v1 milestone acceptance checklist | 🧪 | smoke | F3 |
| `OPS-9` | Prune duplicate/stale entries from `pending-tests.md` | ✅ | smoke | *new* |

**`OPS-1` — Executable verification environment** ✅ *(2026-07-27)*
> Docker toolchain verified end to end: image built, service up, dolfinx 0.7.2
> importing, `tests/unit` 3 passed in 2 s through `run_and_log.sh`. Setup and usage
> are documented in §5.3. This unblocked every other chunk.

**`OPS-3`/`OPS-4` — were silently broken; fixed 2026-07-27** ✅
> Both chunks had sat at `AWAITING-HUMAN-TEST` for months while being **unrunnable**.
> `tests/solver/test_tolerance_policy.py` and `tests/validation/test_tolerance_policy.py`
> share a basename, and with no `__init__.py` in the test tree pytest's default
> `prepend` import mode derives module names from basename alone — the second file
> failed to collect with `import file mismatch`, and `./run_tests.sh --smoke` exited
> 2 every time.
>
> Fixed with `--import-mode=importlib` in `pyproject.toml` (a config one-liner,
> preferred over renaming so existing doc references to both paths stay valid).
> Smoke matrix went from exit 2 → **13 passed in 0.38 s**.
>
> This is the canonical example of why §4's execute-it-yourself rule exists: a chunk
> can look complete in a dashboard indefinitely while being incapable of running.

**`OPS-2` — CI runs the real suite** ✅ *(2026-07-27)*
> Added a `validation` job to `.github/workflows/ci.yml` running the smoke matrix,
> the full magnetostatics validation suite at `mpiexec -n 2`, and the IO/materials/
> post suites. 25-minute job timeout; measured 150 s at 8 ranks locally, so expect
> 5–10 min on a 2-core runner.
>
> This closes the gap that produced essentially every defect found on 2026-07-27:
> ~3,400 lines of test code ran nowhere, so breakage accumulated silently for
> months behind chunks that *looked* complete in a dashboard.
>
> Two tests are `--deselect`ed explicitly (visible in the workflow, not silently
> skipped): `test_phantom_material_assignment_and_time_harmonic_pipeline_wiring`
> and `test_phantom_field_metrics_and_exports_are_finite`. Both pre-existing, both
> downstream of the time-harmonic proxy, both to be revisited with `TH-1`.
>
> Note MPI here is **MPICH/Hydra**, not OpenMPI — `--allow-run-as-root` is not a
> valid flag and will break the job.
> CI cannot host the `heavy` tier; keep those local.

### MAG — Magnetostatics (Phase 1)

| ID | Title | Status | Tier | Legacy |
|---|---|---|---|---|
| `MAG-1` | Vector-potential formulation, N1curl, gauge penalty | ✅ | standard | ch. 1–5 |
| `MAG-2` | Straight-wire analytic validation | ✅ | standard | — |
| `MAG-3` | Circular-loop analytic validation | ✅ | standard | — |
| `MAG-4` | Helmholtz analytic validation (**0.04% centre**) | ✅ | standard | ch. 9 |
| `MAG-5` | h-refinement convergence study (rate **+0.81**) | ✅ | standard | — |
| `MAG-6` | Coil+phantom B-field symmetry metric strategy | 🧪 | unmeasured | A1 |
| `MAG-7` | Fix point evaluation in validation tests | ✅ | standard | *new* |
| `MAG-8` | Restrict straight-wire current density to the wire | ✅ | standard | *new* |
| `MAG-9` | Re-size validation meshes to fit the tier budget | ✅ | standard | *new* |
| `MAG-10` | Gauge penalty was below the safe window | ✅ | standard | *new* |
| `MAG-11` | Parallel energy was rank-local (missing allreduce) | ✅ | smoke | *new* |
| `MAG-12` | `evaluate_at_points` still used the MAG-7 broken pattern | ✅ | smoke | *new* |
| `MAG-13` | Analytic-Dirichlet outer boundary for wire/loop fixtures | ✅ | heavy | wire 12.75%, loop 7.07%, 3-point rate 1.10; 167 s + 196 s `-n 2` |
| `MAG-14` | Promote the Helmholtz analytic comparison into the test suite | ✅ | smoke | 11 s, `-n 2` |
| `MAG-15` | Lagrange-multiplier Coulomb gauge (parameter-free cross-check) | ✅ | smoke | *new* |

#### The whole magnetostatics suite now runs and passes

`10 passed, 2 skipped` in 150 s on 8 ranks — log
`docs/testing/logs/20260727T190008Z_MAG-7.log`. It had never completed before.
Repairing it surfaced **six independent defects, none of them in the solver**:

| # | Defect | Evidence |
|---|---|---|
| 1 | `B.eval(points, np.arange(n))` — evaluates in arbitrary cells | 7 sites; output oscillated where analytic was smooth |
| 2 | Axial current density in an xy-plane torus (**both** loop tests) | on-axis `B_z` ~1000× too small, 100.3% error |
| 3 | Current applied over whole domain, not the wire | ~2500 A enclosed instead of 1 A |
| 4 | Convergence-rate sign inverted | reported −0.79 for genuinely convergent data |
| 5 | Analytic expectation 2× wrong | test wanted `μ₀I/(2√2a)`; correct is `μ₀I/(4√2a)` |
| 6 | Meshes mis-sized | OOM at 16 GB / >400 s |

Defect 5 is worth dwelling on: the *test* was wrong and the *implementation* was
right. Treat a failing analytic comparison as evidence about the test as much as
about the code.

#### `MAG-10` — the degree-2 divergence was a silently-corrupting default ✅

Diagnosed 2026-07-27. The blow-up at N1curl degree 2 was **not** an element-order
problem. The default `gauge_penalty = 1e-3` sat *below* the numerically safe
window, and the resulting corruption was invisible to every existing diagnostic.

**Mechanism.** The weak form is
`∫μ⁻¹(∇×A)·(∇×v) dx + gauge·∫A·v dx`. The penalty removes the curl-curl
operator's gradient null space, and it fixes the magnitude of the null-space
component of `A` as `|A_gradient| ∝ 1/gauge`. With `gauge = 1e-3` against
`μ⁻¹ ≈ 8×10⁵`, that component ran ~9 orders larger than the physical field.
`B = ∇×A` annihilates a gradient exactly in *exact* arithmetic; in floating
point the physical signal is destroyed by cancellation. Degree 2 has a larger
gradient null space, so it crosses the precision limit first — degree 1 merely
*hid* the problem.

**Measured** (straight-wire fixture, `h = 0.003`, 88k cells, 8 ranks):

| degree | gauge | L2 error | `max\|A\|` | KSP reason | residual |
|---|---|---|---|---|---|
| 1 | 1e-3 | 24.84% | 4.39e+04 | 4 (converged) | 0.0 |
| 1 | ≥1e0 | 24.67% | 5.23e+01 | 4 | 0.0 |
| 2 | **1e-3** | **919.85%** | **3.46e+07** | **4 (converged)** | **0.0** |
| 2 | ≥1e0 | **19.59%** | 4.26e+01 | 4 | 0.0 |

Raising the penalty fixes degree 2 outright, and it then beats degree 1 as
theory predicts (19.59% vs 24.67%). `max|A| ∝ 1/gauge` exactly, confirming the
mechanism. `B` is insensitive to the value across **1e0…1e6**, verified on two
independent geometries (straight wire and Helmholtz two-torus, the latter
unchanged at 1.55% → 1.54%). There is no accuracy reason to go below 1.

**The failure was silent.** The default solver is a direct LU
(`ksp_type: preonly, pc_type: lu`), so PETSc reported *converged, residual 0.0*
for the 919% answer. `LinearSolveDiagnostics` could not have caught it. Anyone
raising the element degree would have received quietly wrong results.

**Fix.** `DEFAULT_GAUGE_PENALTY = 1.0` in `core/solvers.py`, shared by the
magnetostatic solver, the time-harmonic solver, and both port entry points so
the value cannot drift between them. `GaugeContaminationWarning` fires whenever
a caller passes something below the validated floor.

> **A solution-based guard was tried and rejected.** The natural metric —
> `||A|| / (L·||curl A||)`, since a physical potential satisfies `|A| ~ |B|·L` —
> does not discriminate. It reads ~5e8 for a *known-good* solve on this fixture,
> and degree 1 at `gauge = 1e-3` carries a similarly large ratio while staying
> accurate to within 0.2% of the well-conditioned answer. The catastrophe needs
> a large null-space component *and* degree-2 conditioning, so no threshold on
> the ratio alone separates good from bad without false alarms — and a warning
> that cries wolf on good solves is worse than none. The ratio is still computed
> and returned for diagnostics; it is simply not a trigger. Recalibrating it
> properly would need a study across degrees and mesh sizes.

**Resolved by decision (2026-07-28).** `MAG-15` landed the saddle-point Lagrange
gauge as a parameter-free cross-check; the penalty at 1.0 stays the production
default on cost grounds. Tree-cotree gauging is rejected outright: `TH-1`'s
E-field formulation has no static null space at ω > 0 (the operator acts as
−k₀²ε_c on the gradient subspace), so further magnetostatic gauge machinery has
no Phase-2 payoff. The Phase-2 analog to guard against instead is near-resonance
ill-conditioning — see the `TH-1` formulation notes.

#### `MAG-15` — Lagrange-multiplier Coulomb gauge ✅ *(2026-07-28)*

Solves (A, p) in N1curl × H1, enforcing div(A) = 0 weakly. The null space is
*removed* rather than priced: no parameter to choose, A comes out physically
scaled (max|A| ~ 1.6e-9 vs ~5e1 for the penalty on the straight-wire fixture),
and B needs no floating-point cancellation. Costs ~2× the penalty at degree 1,
~7.5× at degree 2 — hence cross-check, not default. Full measurements live in
the `GaugeMethod` docstring in `core/solvers.py`.

Two properties earn it trust as a cross-check, both pinned in
`tests/solver/test_gauge_lagrange.py`: agreement with the penalty B field
(< 5% bound; measured identical analytic error to 4 significant figures), and
null-space removal (Lagrange max|A| < 1e-6 × penalty's; measured ~1e-11).
A non-zero multiplier spread additionally diagnoses an incompatible source
(div J ≠ 0, or J·n ≠ 0 on the boundary) — the straight-wire fixture trips it
by construction, which is `MAG-13`'s subject. 7 passed in 13 s at `-n 2`;
log `20260728T193524Z_MAG-15.log`.

Bonus discovered under `MAG-11`: the Lagrange solution satisfies the clean
work-energy identity `W = ½∫J·A` (the constraint row with q = p zeroes the
gauge term exactly), which the penalty solution provably cannot provide — its
identity buries the ~1e-8 signal under O(1) terms carrying the operator's full
null-space conditioning (measured 1.4e-3 identity error, sign flipped; log
`20260728T194622Z_MAG-11.log`).

**Two implementation traps**, both of which cost real time and neither of which a
single-rank test will catch:

- `p` must live in the **full `H¹`**, not `H¹₀`. Restricting the multiplier to
  `H¹₀` leaves gradients of boundary-nonzero functions unconstrained, so the
  system stays singular — and it returns `NaN`/`inf` rather than failing loudly.
  With `q` free in `H¹` the constraint annihilates constants, hence the pinned dof.
- `fem.locate_dofs_geometrical` is **collective**. Calling it under
  `if comm.rank == owner` deadlocks, and the deadlock is *rank-count dependent*:
  it completes at 2 ranks and hangs at 4. Broadcast the target, then let every
  rank make the call. `MPI.MINLOC` over a pickled Python tuple is likewise not
  reliably consistent across ranks; owner election uses scalar reductions only.

**Not done — `MAG-15` is a working option, not a finished subsystem:**

- **Dirichlet conditions on `A` are rejected** (`bc_functions` raises). The
  multiplier space would need matching constraints. Only the natural-BC path works,
  which is the path all current fixtures use — but `TimeHarmonicBoundaryCondition.PEC`
  would not.
- The point-pin on `p` is **not `H¹`-stable in 3D**, so the multiplier carries an
  arbitrary offset. Its *spread* is the meaningful quantity — use
  `gauge_multiplier_spread()`, not `max|p|` (which read 8e13 in one probe and is
  nearly all constant offset). A mean-zero constraint would be cleaner.
- **Not wired through** `TimeHarmonicSolver` or the port entry points; those still
  take `gauge_penalty` only.
- The degree-2 cost (~7.5×) is **unprofiled**. The mixed system is indefinite and
  goes to MUMPS direct with no preconditioner strategy; whether that is the right
  approach at scale is untested.
- **Tree-cotree was not attempted.** It is exact for lowest-order Nédélec (a
  spanning tree has exactly `#vertices−1` edges, matching the null-space
  dimension), but a global spanning tree across MPI ranks is research-grade work,
  and the saddle point already removes the null space without it. See the rejection
  rationale above.

#### `MAG-11`/`MAG-12` — two API defects survived the 2026-07-27 audit ✅ *(2026-07-28)*

Nothing in-tree called either method, which is exactly why they survived the
audit that fixed the same defects everywhere else:

- `compute_magnetic_energy()` returned the rank-local `assemble_scalar`
  contribution — under `mpiexec -n N` every caller saw ~1/N of the true
  energy, including both flagship magnetostatics examples. Fixed with an
  allreduce. Guards: exact agreement with an explicitly reduced assembly
  (catches a missing reduction at factor ~N under the CI `-n 2` job), plus
  the `W = ½∫J·A` identity on a Lagrange solve.
- `evaluate_at_points()` still did `f.eval(points, np.arange(n))` — the
  arbitrary-cells pattern `MAG-7` eradicated from the tests, surviving in the
  public API itself. Now routed through `post.evaluation`; out-of-mesh points
  raise `ValueError` instead of returning extrapolated garbage.

Logs `20260728T195016Z_MAG-11.log`, `20260728T195031Z_MAG-12.log`. The guard
file joined the CI validation job's `mpiexec -n 2` step — the only environment
where a missing reduction is visible at all.

#### `MAG-13` — analytic-Dirichlet boundaries for the wire/loop fixtures ✅

**Done 2026-07-30.** Wire half (steps 1–3, 6) landed in `a30682c`; the loop
fixture and convergence rework (steps 4–5) in the 07:42 run, both scheduled
implementer runs.

**Steps 4–5 (loop + convergence rate).** `test_circular_loop.py` now solves
through a shared `solve_loop(..., analytic_bc=True)` helper that imposes the
Jackson 5.37 off-axis `A_φ` on the outer sphere via `exterior_dirichlet_bc`;
`test_convergence.py::test_h_refinement_straight_wire` uses the analytic BC and
fits the rate over **three** resolutions instead of two.

Measured, `mpiexec -n 2`, on-axis `B_z` L2 error over `|z| ≤ 0.4 R_domain`:

| h | cells | natural `n×H = 0` | analytic Dirichlet |
|---|---|---|---|
| 0.0035 | 82.8k | 14.98% | 16.23% |
| 0.0025 | 208.0k | 8.86% | 10.37% |
| 0.002 | 411.4k | — | **7.07%** |

**The plan's premise was wrong for the loop, and the measurement is the
deliverable.** The analytic wall is ~20% *worse* at fixed h, the opposite of the
wire (35.13% → 22.19%). Reason: the wire's natural BC contradicts Ampère's law
for net axial current — an error no refinement removes — whereas the loop's is a
PMC image term of order `(a/R)³ ≈ 3.7%`, *smaller* than the O(h) error that
degree-1 interpolation of `A_φ` injects through the boundary data itself. What
the Dirichlet wall buys is the limit: 16.23% → 10.37% → 7.07% converges
monotonically (fitted ≈ 1.4) to the analytic field, while the natural wall
converges to a field that differs from it. So the tolerance tightens
**10% → 8% at h = 0.002**, not at the old h = 0.0025 where the analytic BC would
have needed 12%; nothing was loosened to accommodate the better BC. The
sampling window stays at `0.4 R` deliberately — widening to `0.8 R` reports
6.28% instead of 7.07% by adding far-field points where `B` is small.

Convergence rate, wire, analytic BC, three resolutions:
22.19% → 12.75% → 9.26% at h = 0.004/0.0025/0.0018, fitted **1.10**, bound
`[0.7, 1.5]` (two-sided: an inflated rate means an anomalous resolution, not
better convergence). Two candidate sequences were rejected on measurement:
h = 0.005 gives 30.34% at 23.2k cells (5 mm cells cannot resolve the 3 mm wire —
a geometry artifact that inflates the fit), and h = 0.0035 gives 11.77%, *below*
the h = 0.0025 value, so any triple containing it is non-monotone — cell-wise
constant `curl A` gives each resolution O(h) pointwise sampling noise.

Verification: `20260730T125223Z_MAG-13.log` (loop, 3 passed, **167 s**) and
`20260730T125522Z_MAG-13.log` (convergence + wire, 5 passed 2 skipped,
**196 s**), both `mpiexec -n 2`, **heavy** tier — the loop's analytic test alone
is 124 s at 411k cells, so this fixture is no longer `standard`. Probes:
`20260730T124356Z`, `20260730T124523Z`, `20260730T124829Z_MAG-13-loop-probe*`,
`20260730T124930Z_MAG-13-conv2`.

Landed in the wire half (`a30682c`):

- `AnalyticalSolutions.straight_wire_vector_potential(..., wire_radius=a)` —
  finite-conductor branch, gauged to `A_z(a) = 0`, so the potential is finite
  on the axis. Required: the `straight_wire_domain` end caps cross `r = 0`,
  where the filament `ln r` diverges and interpolation would poison the BC.
- `AnalyticalSolutions.circular_loop_vector_potential` — off-axis `A_φ` via
  `scipy.special.ellipk/ellipe` (scipy 1.11.3 present in the container), with
  the `ρ → 0` branch. Unit-tested by curling it back to the on-axis closed form
  at three `z` (rtol 1e-6), which is what catches the `m = k²` convention trap.
- `core.solvers.exterior_dirichlet_bc(V, field)` — interpolate a callable into
  an N1curl space, constrain all topologically-located exterior dofs. Generic;
  the loop fixture reuses it unchanged.

**Measured** (`mpiexec -n 2`, |B| L2 error over `2a → 0.8 R_domain`):

| h | cells | natural `n×H = 0` | analytic Dirichlet |
|---|---|---|---|
| 0.004 | 38.8k | 35.13% | 22.19% |
| 0.0025 | 145.9k | — | 12.75% |
| 0.0018 | 383.2k | — | 9.26% |

Fitted rate ≈ **O(h^1.2)** across the three, with no plateau — the modeling
floor this chunk was written against is gone. The test bound tightens
**25% → 15%** at h = 0.0025 (measured 12.75%) and the sampling window widens
from `0.4 R` back to `0.8 R`; a new test
`test_analytic_bc_improves_on_natural_bc` asserts the BC beats the natural wall
on the *same* mesh (measured factor 0.63, bound 0.85), which is the chunk's
physical claim rather than a tolerance.

Not reached: the < 5% target. Extrapolating the measured rate puts it at
h ≈ 0.00125, ~1.1M cells and > 5 min at `-n 2` — outside the standard tier.
The residual is uniform-mesh discretization of a 1/r field next to a thin
conductor, so graded refinement (`MAG-9` machinery) is the cheap route, not
more uniform h. `J·n ≠ 0` at the end caps also still stands; step 3's
"cap the wire short of the end faces" option was not needed to clear the floor
and was left unmeasured.

Logs: `20260730T034941Z_MAG-13.log` (9 passed, 72 s, standard tier);
probes `20260730T034541Z_MAG-13-probe.log` (BC vs natural at h=0.004),
`20260730T034614Z_MAG-13-probe2.log` (h-refinement).

**Original analysis and plan, retained for the record (all steps now executed;
step 3's "cap the wire short of the end faces" option was never needed and is
left unmeasured):**

The straight-wire fixture cannot converge to `μ₀I/(2πr)` at any resolution:
the natural BC `n×H = 0` on the side wall contradicts Ampère's law for any net
axial current (`∮H·dl = I` vs `H_φ(R) = 0` forced at the wall), and the wire
terminates on the end caps so `J·n ≠ 0` — an incompatible source the gauge
term absorbs (the `MAG-15` multiplier spread measures it directly). The
observed 18–25% error is therefore substantially a **modeling floor**, not
discretization error, and `test_h_refinement_straight_wire`'s `rate > 0.5`
assertion will eventually fail on a *correct* solver as h approaches the
floor. Do not loosen that assertion when it happens — fix the boundary.

Fix: impose the analytic solution as Dirichlet data through the existing
`bc_functions` path (wire: `A_z = −μ₀I/(2π)·ln r` on the outer boundary; loop:
closed-form off-axis form). The continuum limit then *is* the analytic
field, tolerances tighten from 25%/10% toward single digits, and rates get fit
over ≥ 3 resolutions instead of 2. The same treatment removes the ~(a/R)³
PMC-image bias the loop test currently hides inside its 10% tolerance.

**Implementation plan (Batch 2 — documented 2026-07-28, not yet executed):**

1. `utils/analytical.py`: add the off-axis loop vector potential (Jackson
   eq. 5.37): `A_φ(ρ,z) = (μ₀I/π)·√(a/ρ)·[(1 − k²/2)K(k) − E(k)]/k` with
   `k² = 4aρ/((a+ρ)² + z²)`, via `scipy.special.ellipk/ellipe`.
   **Two traps:** scipy's elliptic functions take the *parameter* `m = k²`,
   not the modulus `k` — passing `k` is a silent factor error; and the ρ → 0
   limit needs the explicit `A_φ = 0` branch. Verify scipy imports in the
   container at chunk start — it is the long pole if absent. The wire
   potential (`straight_wire_vector_potential`) already exists.
2. New small helper (`core/solvers.py` or `utils/`): build a Dirichlet BC on
   the exterior boundary of an N1curl space from a callable `A(x)` —
   interpolate into V, locate exterior dofs topologically (the pattern
   already exists in `TimeHarmonicSolver.build_boundary_conditions`), return
   `fem.dirichletbc`. Constraining all exterior dofs of the interpolant
   imposes its tangential trace, which is what the formulation needs.
3. `test_straight_wire.py`: pass the BC via `bc_functions`; the sampling
   window may widen back toward the boundary; tighten the 0.25 bound to a
   *measured* single-digit value. Note `J·n ≠ 0` at the end caps remains
   after the BC fix; if a floor persists, cap the wire short of the end
   faces in `straight_wire_domain` so `J·n = 0` — decide on measurement,
   not speculation (the `MAG-15` multiplier spread is the instrument).
4. `test_circular_loop.py`: same treatment with the elliptic-integral A;
   tolerance from 0.10 to a measured single-digit value.
5. `test_convergence.py`: ≥ 3 resolutions; assert the fitted rate in
   [0.7, 1.5] rather than `> 0.5` (N1curl degree 1 predicts ~1.0, and an
   upper bound catches a superconvergent-looking artifact as well).
6. Tier: `standard` per test, but cost-probe first per §5.1 — Dirichlet rows
   change the matrix, not the mesh, so existing measured sizes should hold.

Done when: wire and loop L2 errors < 5% (or the measured
discretization-limited value, recorded with the log), h-rate ≈ 1 over ≥ 3
resolutions, all recorded via `run_and_log.sh`.

#### `MAG-14` — promote the Helmholtz analytic comparison into the test suite ✅

**Done 2026-07-29** (scheduled implementer run). `tests/validation/test_helmholtz_magnitude.py`
executed at `mpiexec -n 2`: **53941 cells, centre `B_z` error 1.731%** against the
closed form `(4/5)^{3/2}·μ₀I/R` (FEM 3.592162e-09 T vs 3.531057e-09 T), mean
on-axis error 1.730% over `|z| ≤ 0.25R`, central `CV = 0.0216%`; the analytic
helper agrees with the closed form to `< 1e-12`. **11 s wall clock — `smoke`
tier**, not `standard` as planned, so the test is now in the CI `mpiexec -n 2`
magnetostatics step (`.github/workflows/ci.yml`). Log:
`docs/testing/logs/20260729T144331Z_MAG-14.log` (cost probe:
`20260729T144309Z_MAG-14-probe.log`).

The measured 1.731% matches the padding study's predicted 1.73% at 2R exactly,
which is the useful part: the air-box error model in the `MAG-1`/`MAG-4` table
predicts this fixture. Cell count is 53.9k rather than the table's 76k because
the graded wire/far sizing differs from the study mesh; the error is unchanged.
The suite now has one test that is simultaneously correctly-evaluated,
quantitative, and scale-sensitive — a missing `μ₀` or a mis-normalized current
fails it, where `test_helmholtz_v2.py`'s `CV` check passes untouched.

Original plan, retained for the record:

`test_helmholtz_v2.py` asserts only `CV < 1%`, which is **scale-invariant**: a
solver wrong by any constant factor (μ₀, current normalization) passes it
untouched. The magnitude check — the 0.04% result that justifies `MAG-1`/
`MAG-4` — lives only in `examples/magnetostatics/04_helmholtz_analytic_comparison.py`,
which CI never executes. Land it as a test at budget size with a ≤ 5%
centre-field tolerance, giving the suite one test that is simultaneously
correctly-evaluated, quantitative, and scale-sensitive.

**Implementation plan (Batch 2 — documented 2026-07-28, not yet executed):**

- New `tests/validation/test_helmholtz_magnitude.py`, adapted from example 04
  (same mesh helper, same point evaluation, same current normalization — the
  normalization is the entire point, since CV cannot see it).
- Air box: start from `air_padding = 2R` with graded `wire_resolution` /
  `far_resolution` (76k cells, 1.73% centre error measured). The 4R study
  (163k cells, 0.01%) ran 26 s at 8 ranks; cost-probe before assuming it fits
  `standard` at `-n 2`, and fall back to 2R if not — 5% tolerance has margin
  either way.
- Assert: centre `B_z` within 5% of the closed form `(4/5)^{3/2}·μ₀I/R`;
  mean on-axis error < 5% over the central window; keep a CV assertion as a
  secondary check so this test supersedes rather than duplicates `_v2`.
- Add to the CI `mpiexec -n 2` step only if the measured runtime permits;
  otherwise it stays in the local validation set with its log recorded.

**Parked work (noted by the 2026-07-29 review; branch deleted by the
2026-07-30 review — commit `b81b958` was cherry-picked to main and verified):**
the 2026-07-28 scheduled
run wrote `tests/validation/test_helmholtz_magnitude.py` on branch
`attempt/MAG-14-20260728T224647Z` (commit `b81b958`) before the
since-resolved Docker blocker stopped it. The file implements this plan —
2R padding, 0.003/0.010 graded resolution, centre/on-axis/CV assertions,
analytic helper self-checked against the closed form to 1e-12 — but **has
never executed**; only `ast.parse` passed. Next attempt: cherry-pick
`b81b958`, cost-probe at `mpiexec -n 2` (~76k cells), then run under
`standard`. Expect ~1.7% centre error; if it exceeds 5%, raise `AIR_PADDING`
to `4 * MAJOR_RADIUS`, never the tolerance.

Done when: the magnitude assertions pass at a measured runtime inside
`standard`, recorded via `run_and_log.sh`, and the chunk entry states whether
CI carries it.

#### `MAG-1`/`MAG-4` — the solver is correct. Verified 2026-07-27.

`examples/magnetostatics/04_helmholtz_analytic_comparison.py` compares on-axis `B_z`
against the closed-form Helmholtz solution using proper collision-based point
location. Log: `docs/testing/logs/20260727T171928Z_MAG-4.log`, 26 s on 8 ranks.

**Result: 0.04% centre-field error, 0.83% mean along the axis, central `CV = 0.003%`.**
This clears the plan's `<5%` MVP criterion by two orders of magnitude and is the
first quantitative analytic validation the project has ever had.

Reaching it required fixing the air box (below). Two independent convergence studies
confirm the result is real rather than error cancellation:

| air padding | cells | centre err | | wire `h` @ 4R pad | cells | centre err | mean err |
|---|---|---|---|---|---|---|---|
| 0.5 R | 40k | 20.42% | | 0.004 | 89k | 0.11% | 1.07% |
| 1 R | 51k | 7.43% | | 0.003 | 127k | 0.04% | 0.84% |
| 2 R | 76k | 1.73% | | 0.002 | 228k | 0.05% | 0.51% |
| 4 R | 163k | **0.01%** | | | | | |

Boundary error falls monotonically with domain size; discretization error falls
monotonically with `h`. `MAG-1` is therefore `✅` — `core/solvers.py` reproduces
closed-form magnetostatics.

#### The air box was the dominant error, not mesh resolution

`two_torus_domain` hardcoded `box_half = R + 3a`, coupling the air gap to the *wire
radius*. The outer boundary carries the natural condition
`n×(μ⁻¹∇×A) = 0` ⟹ `n×H = 0`, which acts as a **perfect magnetic conductor** and
mirrors flux back into the domain, inflating the on-axis field. Because of the
coupling, making the wire *thinner* shrank the air box and made agreement *worse*
(43.7% at `a = 0.003` vs 20.5% at `a = 0.005`) — the opposite of the expected trend,
which is what identified the boundary as the culprit.

Fixed by adding to `MeshGenerator.two_torus_domain`:
- `air_padding` — decouples the box from `minor_radius`. Use `>= 2*major_radius` for
  free-space comparisons. Defaults to the legacy `2*minor_radius`, so existing
  callers are unaffected.
- `wire_resolution` / `far_resolution` — graded sizing via a gmsh Distance+Threshold
  field, fine at the tori and coarse at the boundary. **This is what makes a large
  box affordable**: 76k cells instead of ~626k for equivalent wire fidelity, an ~8×
  saving. Without grading the 4R-padding study would not fit the compute budget.

This discharges the substance of `GEO-4` ("air-box and boundary sizing heuristics")
for the two-torus fixture. `GEO-4` itself stays 🧪 until its own test is executed.

> **Generalize this.** Every other fixture in `io/mesh.py` uses a single global
> `setSize` and similarly tight padding, including the coil+phantom geometry that all
> MRI work depends on. Expect the same boundary-mirror error there, and expect graded
> sizing to be equally necessary once air boxes grow.

#### Phase 1 is not as validated as previously documented

Executed 2026-07-27. `docs/status.md` claimed "Phase 1 — COMPLETE" and the README
claimed validation against analytic wire/loop/Helmholtz solutions. Running the tests
does not support that.

**`MAG-7` — broken point evaluation (affects nearly every Phase-1 test).**
The tests evaluate fields with:

```python
B_num = B.eval(points, np.arange(n_points))       # WRONG
```

`Function.eval(points, cells)` requires `cells[i]` to be *the cell containing*
`points[i]`. Passing `np.arange(n)` evaluates each point inside arbitrary cells
`0..n-1`, extrapolating basis functions far outside their support. Measured output
on a clean 8,210-cell mesh oscillates — `8.0e-6, 1.6e-5, 3.2e-6, 1.4e-5, 6.6e-6` —
where the analytic curve falls smoothly from `2.0e-5` to `1.25e-5`. These are not
discretization errors; the numbers are meaningless.

Affected: `tests/validation/test_straight_wire.py` (×2),
`test_circular_loop.py` (×2), `test_helmholtz.py` (×3), `test_convergence.py`,
`tests/solver/test_two_cylinder.py`, plus `examples/magnetostatics/02_*.py` and
`03_*.py`.

**The correct machinery already exists** in `src/fem_em_solver/post/evaluation.py`
(bounding-box tree + collision search), and `tests/validation/test_helmholtz_v2.py`
uses it properly. `_v2` was evidently written as a correction of `test_helmholtz.py`
— but the broken original was left in place and kept being counted as validation.
`MAG-7` is to route every test through `post/evaluation.py` and delete the
superseded originals.

**`MAG-8` — the straight-wire test doesn't model a straight wire.** Its current
density is applied over the *entire domain*, not the wire, and the test says so:

```python
# For simplicity, apply uniform J in whole domain
# (proper subdomain restriction would use cell_tags)
return ufl.as_vector([0.0, 0.0, J_magnitude])
```

With `J = I/(π·0.001²)` over a 5 cm domain the enclosed current is ~2500 A, not 1 A.
Worse, inside a uniform current distribution `|B|` grows *linearly* with r while the
analytic reference `μ₀I/(2πr)` *falls* as 1/r — opposite slopes. This test could
never have passed. It needs `subdomain_ids` restriction to the wire tag.

**`MAG-9` — the validation meshes are mis-sized.** `test_straight_wire` meshes a
5 cm × 1 m cylinder at h = 5 mm ≈ 4×10⁵ tetrahedra. Measured: **>400 s single-rank,
killed before completion** — over the `heavy` ceiling, for something labeled a unit
test. For scale, an 8,210-cell case runs in 3.4 s total (0.9 s mesh + 2.5 s solve),
so cost here is almost entirely mesh-size driven. Re-parameterize to land inside
`standard`.

> **This was a defect in the *tests*, not in `core/solvers.py`.** Confirmed: once
> field evaluation and the air box were fixed, the solver matched the closed-form
> Helmholtz solution to 0.04% (see `MAG-1`/`MAG-4` above). The remaining broken tests
> are still broken and still need `MAG-7`/`MAG-8`, but the formulation is sound.

> `MAG-6` note: the predecessor test failed with `max relative |B| mismatch = 0.322`
> against a `< 0.30` limit. The fix added interface-aware sampling offsets. **The
> revised test has never been executed.** Given `MAG-7`, treat the original 0.322
> figure as unreliable — it was produced by the same broken evaluation path.

### GEO — Geometry & meshing

Independent of the §2.1 physics defect; meshes are meshes.

| ID | Title | Status | Tier | Legacy |
|---|---|---|---|---|
| `GEO-1` | Parametric birdcage geometry generator | 🧪 | standard | B1 |
| `GEO-2` | Port-face geometry robustness checks | 🧪 | standard | B2 |
| `GEO-3` | Phantom placement presets (centered/off-center) | 🧪 | standard | B3 |
| `GEO-4` | Air-box and boundary sizing heuristics | 🧪 | smoke | B4 |
| `GEO-5` | Region-specific mesh resolution policy | 🧪 | standard | B5 |
| `GEO-6` | Geometry sanity report utility | 🧪 | smoke | B6 |
| `GEO-7` | Mesh-tag QA diagnostic hardening | 🧪 | standard | A4 |

### TH — Time-harmonic Maxwell (Phase 2)

| ID | Title | Status | Tier | Legacy |
|---|---|---|---|---|
| `TH-1` | **Real complex time-harmonic formulation** | ⬜ | standard | *new* |
| `TH-2` | Time-harmonic API hardening | ⚠️ | standard | C1 |
| `TH-3` | Boundary-condition option set | ⚠️ | standard | C3 |
| `TH-4` | Convergence/conditioning diagnostics | 🧪 | standard | C6 |
| `TH-5` | Absorbing boundary condition (ABC) | ⬜ | standard | *new* |
| `TH-6` | **Validation: plane wave in lossy half-space** | ⬜ | standard | *new* |
| `TH-7` | **Validation: waveguide cutoff / coaxial line** | ⬜ | standard | *new* |
| `TH-8` | **Validation: sphere in uniform field (quasi-static)** | ⬜ | standard | *new* |
| `TH-9` | **Validation: PEC rectangular-cavity resonances** | ✅ | standard | *new* |

**`TH-1` — Real complex time-harmonic formulation** ⬜ **← the critical chunk**
> Replace the `E = -ωA` proxy with an actual frequency-domain solve:
>
> ```
> ∇×(μᵣ⁻¹∇×E) - k₀²ε_c E = -jωμ₀J,    ε_c = εᵣ - j·σ/(ωε₀)
> ```
>
> Requires a complex-scalar PETSc build, complex-valued N1curl assembly, and a
> direct solve (MUMPS) at MVP mesh sizes.
> Done when: `TH-6` passes against the analytic lossy plane-wave solution, and
> changing phantom σ **measurably changes the field** — the property the current
> code provably lacks.
> Blocks: `MAT-2`, `PORT-1`, and all of Phase 5.
>
> **Formulation notes (2026-07-28 theory review):**
> - **The sign convention is part of the spec.** The equation above assumes
>   `e^{+jωt}`, matching `ε_c = εᵣ − j·σ/(ωε₀)`. Every analytic gate
>   (`TH-6`…`TH-9`) must be derived in the same convention, or validation will
>   fail spuriously with conjugated fields.
> - **Do not port the gauge penalty.** At ω > 0 the operator acts as `−k₀²ε_c`
>   on the gradient subspace — nonzero everywhere, dissipative wherever σ > 0.
>   The `MAG-10` disease is statics-only; a penalty term here would *add* error
>   rather than remove a null space.
> - **Phase 2's silent-failure mode is near-resonance ill-conditioning.** With
>   PEC boundaries and lossless air, the matrix is exactly singular at cavity
>   eigenfrequencies — and an MRI coil is deliberately operated near resonance.
>   MUMPS returns clean exit codes on near-singular systems: the same shape as
>   `MAG-10`'s "converged, residual 0.0, 920% error". Done-when therefore also
>   includes a **resonance guard** (condition estimate, a small loss floor for
>   empty-coil sweeps, or an energy-continuity check across sweep points),
>   verified by stepping deliberately close to a `TH-9` cavity mode and
>   observing the guard fire.
>
> **Implementation plan (Batch 3, after `TH-9` — documented 2026-07-28, not
> yet executed):**
> 0. **Environment first, as its own logged smoke chunk.** Extend
>    `src/sitecustomize.py` (or set `PYTHONPATH` explicitly in the chunk
>    commands) for `/usr/local/dolfinx-complex`, then verify
>    `PETSc.ScalarType == complex128` inside the container. Environment
>    failures must not masquerade as formulation failures (§5.3).
> 1. Assemble the sesquilinear form
>    `∫μᵣ⁻¹(∇×E)·(∇×v̄) − k₀²ε_c E·v̄ dx` with `ε_c = εᵣ − jσ/(ωε₀)` built
>    from the existing DG0 machinery (`build_material_fields` carries over
>    unchanged); load `−jωμ₀∫J·v̄ dx`. **`ufl.inner` conjugates its second
>    argument in complex mode — using `ufl.dot` for the load silently flips
>    the sign convention.**
> 2. Direct solve, MUMPS. PEC = zero-tangential-E on exterior/tagged facets
>    (pattern exists in `build_boundary_conditions`); natural = PMC, as today.
> 3. Replace the `E = −jωA` body of `TimeHarmonicSolver.solve`; keep the
>    `TimeHarmonicFields` container (e_real/e_imag split from the complex
>    vector) so downstream `⚠️` chunks recompile without edits.
>    `B = ∇×E/(−jω)` is the post-processing route to B1+ later.
> 4. Gates in the same chunk: `TH-6` — impose the analytic lossy-half-space
>    total field as Dirichlet data on a box and compare interior decay
>    constant and phase against the closed-form skin depth — plus the `MAT-2`
>    sensitivity assertion (low-σ vs high-σ phantom fields differ beyond a
>    stated threshold).
> 5. The resonance guard from the notes above, verified against a `TH-9`
>    mode.
>
> Risks, in likelihood order: complex-path plumbing in `sitecustomize`;
> sign-convention mismatch between solver and gates; near-mode
> ill-conditioning read as a formulation bug.

> `TH-4` is marked 🧪 rather than ⚠️ because PETSc residual/conditioning diagnostics
> are meaningful regardless of which weak form is assembled.

`TH-6`…`TH-9` are cheap closed-form gates. Any one of them would have caught
the `E = -ωA` defect immediately. **Land them alongside `TH-1`, not after** —
and `TH-9` first: closed-form eigenfrequencies
`f = (c/2)·√((m/a)² + (n/b)² + (p/d)²)` make it the purest check of the
curl-curl + mass assembly, with no material or source modeling in the way. It
also supplies the known-frequency fixture the `TH-1` resonance guard is
verified against.

> `TH-5` demoted off the MVP path (2026-07-28): a birdcage operates inside an
> RF shield, so a **PEC outer boundary is physically correct** for the Phase-5
> deliverables. ABC/PML is needed only for unshielded free-space validation
> geometries; do not let it block Phase 5.

**`TH-9` — PEC rectangular-cavity resonance gate** ✅ *(Batch 3 step 1 —
executed 2026-07-30, `src/fem_em_solver/core/cavity.py` +
`tests/validation/test_cavity_resonances.py`, harness log
`20260730T154846Z_TH-9.log`, 3 s at `mpiexec -n 2`)*
> **Result.** Cavity 1.0 × 0.8 × 0.6 m (edges non-commensurate so the first
> four modes are non-degenerate: 239.95 / 291.35 / 312.28 / 346.40 MHz, closest
> pair 7% apart; the fifth at 353.53 MHz is only 2% above the fourth, which is
> why the gate stops at four). N1curl degree 2, `mpiexec -n 2`:
>
> | divisions | cells | dofs | per-mode error (%) | max |
> |---|---|---|---|---|
> | (6, 5, 4) | 720 | 5330 | 0.0123 / 0.0153 / 0.0201 / 0.0436 | 0.0436% |
> | (9, 7, 6) | 2268 | 15998 | 0.0030 / 0.0025 / 0.0049 / 0.0102 | 0.0102% |
>
> Every mode improves under the refinement; the fitted max-error rate is
> **3.85** in h, consistent with the O(h^{2k}) eigenvalue convergence of
> degree-2 edge elements (assertion floor 2.0). Null space: the 8 eigenvalues
> nearest zero are all below 1e-8·k₁² — measured max |λ|/k₁² = 3.2e-15 — i.e.
> the gradient modes come back as a clean machine-zero cluster, counted rather
> than skipped. Zero null modes leaked into the physical band.
>
> **Constrained-dof handling** (the trap): the PEC rows are assembled with a
> large diagonal in `A` (1e4·k₄²) and unit diagonal in `B`, which keeps `B`
> SPD — so SLEPc sees a genuine GHEP — and parks the spurious eigenvalues far
> above the band, where a cutoff drops them. Assembling `B` with a zero
> diagonal instead makes it singular and invalidates the GHEP orthogonalisation.
> The shift-and-invert target is the midpoint of the analytic k₁²…k₄² band;
> that is preconditioning only, and the returned eigenvalues are compared with
> the closed form independently.
>
> This chunk needed only the real-scalar build, as planned — it is the
> known-frequency fixture the `TH-1` resonance guard will be verified against.
>
> Original plan, retained:
> The first executable deliverable of Phase 2, landing *before* the driven
> solver — and it needs **only the real-scalar build**: a lossless source-free
> cavity eigenproblem is real symmetric, so this chunk is deliberately
> decoupled from the complex-mode environment work in the `TH-1` plan.
>
> Design: assemble stiffness `∫(∇×E)·(∇×v) dx` and mass `∫E·v dx` on N1curl
> over a PEC box (zero tangential E on all exterior facets), solve the
> generalized eigenproblem with SLEPc (shift-and-invert near the first
> physical mode; verify `slepc4py` imports in the image at chunk start), and
> compare against `f_mnp = (c/2)·√((m/a)² + (n/b)² + (p/d)²)`. Use unequal
> edges — e.g. 1.0 × 0.7 × 0.5 m, fundamental ≈ 335 MHz, MRI-adjacent — so
> modes are non-degenerate and ordering is unambiguous.
>
> This pins two things nothing else can:
> - the curl-curl **and** mass assembly (any sign/scaling error moves every
>   eigenvalue);
> - correct N1curl null-space behavior: the solver must return the gradient
>   modes as a zero cluster cleanly separated from the physical spectrum.
>   **Count and discard** the near-zero eigenvalues against a stated cutoff —
>   their number is itself a diagnostic — rather than silently skipping them.
>
> Done when: the first 3–5 non-zero eigenfrequencies match the closed form to
> < 1% at a budgeted mesh, improving monotonically under one refinement step,
> recorded via `run_and_log.sh`. Tier: `standard` (cost-probe per §5.1; edge
> counts at λ/20 in a half-metre box are modest).

### MAT — Materials & phantoms (Phase 3)

| ID | Title | Status | Tier | Legacy |
|---|---|---|---|---|
| `MAT-1` | Gelled saline presets (low/mid/high σ) | ⚠️ | smoke | C2 |
| `MAT-2` | Materials demonstrably affect solved fields | ⬜ | standard | *new* |
| `MAT-3` | Debye/Cole-Cole dispersion models | ⬜ | smoke | *new* |
| `MAT-4` | SAR computation `σ|E|²/(2ρ)` | ⬜ | standard | *new* |
| `MAT-5` | Temperature-dependent conductivity | ⬜ | smoke | *new* |
| `MAT-6` | **Dodd–Deeds coil-over-lossy-half-space impedance benchmark** | ⬜ | standard | *new* |

> `MAT-1` is `⚠️` not because the preset table is wrong, but because nothing
> consumes it. `MAT-2` is the chunk that makes `MAT-1` mean something: assert that
> a low-σ and a high-σ phantom produce fields differing by more than a stated
> threshold. It is currently guaranteed to fail — which is precisely why it is worth
> writing.

> `MAT-6` (2026-07-28) is the quantitative teeth for `MAT-2`. Dodd & Deeds
> (1968) gives the closed-form impedance change of a circular coil above a
> layered conductive half-space — the project's headline physics, *"the phantom
> loads the coil"*, in closed form. It upgrades `MAT-2` from "fields differ by
> more than a threshold" to "the coil impedance change matches a published
> solution", and it is the natural bridge between `TH-1` and `PORT-1`.

### POST — Post-processing & field extraction

| ID | Title | Status | Tier | Legacy |
|---|---|---|---|---|
| `POST-1` | Interface-aware field extraction reliability | ⚠️ | standard | C4 |
| `POST-2` | Energy/consistency diagnostics | ⚠️ | standard | C5 |
| `POST-3` | Replace vacuous consistency metrics | ⬜ | standard | *new* |

> `POST-2`/`POST-3`: the current flagship metric `e_to_b_mean_ratio` is by
> construction `≈ ω·|A|/|∇×A|` — it measures a mesh length scale, not physics, and
> cannot detect that the solver is wrong. After `TH-1`, replace it with checks that
> can fail for real reasons: Poynting flux balance, `∇·(σE)` residual, or reciprocity.

### PORT — Ports & S-parameters (Phase 4)

**All `⚠️` chunks below sit on the §2.2 placeholder.**

| ID | Title | Status | Tier | Legacy |
|---|---|---|---|---|
| `PORT-0` | Quarantine the placeholder coupling model | ✅ | smoke | *new* |
| `PORT-1` | **Real port excitation from the solved field** | ⬜ | standard | *new* |
| `PORT-2` | Port data model and tagging contract | 🧪 | smoke | D1 (partial) |
| `PORT-3` | Calibration checklist → executable checks | 🚫 | standard | D1 |
| `PORT-4` | Multi-port drive/termination consistency | ⚠️ | standard | D2 |
| `PORT-5` | S-matrix reciprocity/passivity metrics | ⚠️ | smoke | D3 |
| `PORT-6` | Frequency sweep orchestration | 🧪 | smoke | D4 |
| `PORT-7` | Touchstone metadata + parser cross-check | 🧪 | smoke | D5 |
| `PORT-8` | Port-orientation sensitivity | ⚠️ | standard | D6 |

**`PORT-0` — Quarantine the placeholder** ✅ *(2026-07-27)*
> `run_single_port_excitation_case` → `run_placeholder_port_coupling_case` (alias
> kept, warns); `PlaceholderPortModelWarning` on every call; `is_placeholder`
> threaded through `SinglePortExcitationResult` and `SParameterSweepResult`;
> `export_touchstone()` refuses flagged data unless `allow_placeholder=True` and
> stamps `PLACEHOLDER DATA — NOT A SIMULATION RESULT` into any file exported that
> way. Two tests cover the gate in both directions.
>
> Fabricated `.s2p` files can no longer leave the project looking authoritative.
> The numbers are unchanged and still meaningless — `PORT-1` is what fixes that.

**`PORT-1` — Real port excitation from the solved field** ⬜ *(design sketched 2026-07-28)*
> Gap-voltage lumped ports, the standard approach for MRI coils at 64–300 MHz:
> excite one port per solve with an impressed gap source; recover
> `V_i = −∫E·dl` across each port gap and terminal currents from the solved
> field; assemble the Z-matrix column-by-column from N single-port solves;
> convert `S = (Z − Z₀I)(Z + Z₀I)⁻¹`.
> Done when: `‖Z − Zᵀ‖/‖Z‖` (reciprocity) sits below a stated tolerance — a
> real, failable identity that replaces the placeholder-arithmetic assertions,
> and resolves known-issues entry 3 exactly the way that file prescribes
> ("resolve them there"). Depends on `TH-1`; wave ports are out of scope at
> these frequencies.

> **Two port tests are red and are deliberately left red.** Both fakes set
> `current = voltage/z0` at the driven port, making it perfectly matched, so
> `b = (V − Z₀I)/2√Z₀ = 0` and the S-matrix diagonal is legitimately zero against
> an assertion demanding it be non-zero. Verified pre-existing. Fixing them means
> tuning assertions to match a heuristic that `PORT-1` deletes; resolve them there.

> `PORT-3` blocker: the recorded failure was a docker preflight error, not a code
> failure. Its real status is unknown and is resolved by `OPS-1`, not by code changes.
> `PORT-6`/`PORT-7` are 🧪 rather than ⚠️ — sweep-grid generation and Touchstone
> *formatting* are correct independent of what fills the matrix.

### WF — End-to-end workflow & MRI outputs (Phase 5)

| ID | Title | Status | Tier | Legacy |
|---|---|---|---|---|
| `WF-1` | MRI example CLI/config | 🧪 | smoke | E1 |
| `WF-2` | Reproducible output bundle manifest | ⚠️ | standard | E2 |
| `WF-3` | Quick-look phantom metrics report | ⚠️ | standard | E3 |
| `WF-4` | Scenario presets (debug/dev/benchmark-lite) | 🧪 | standard | E4 |
| `WF-5` | Loaded birdcage: frequency shift & Q degradation | ⬜ | heavy | *new* |
| `WF-6` | B1+ field mapping and homogeneity (CV) | ⬜ | heavy | *new* |
| `WF-7` | SAR10g hotspot identification | ⬜ | heavy | *new* |
| `WF-8` | Publication-quality visualization pipeline | ⬜ | standard | *new* |

> `WF-2`/`WF-3` produce structurally valid manifests and reports containing
> physically meaningless numbers. The chunks are `⚠️`, not broken — the plumbing is
> fine and will become useful the moment `TH-1` lands.

---

## 8. Legacy ID mapping

Commit messages, `docs/testing/pending-tests.md`, and `docs/testing/logs/*.log` use
older IDs. Two generations of IDs collided — `E1`–`E4` refer to *different chunks*
in the ROADMAP than in `pending-tests.md`. Resolve via this table.

| Legacy (ROADMAP gen-2) | New ID | | Legacy (gen-1, in `pending-tests.md`) | New ID |
|---|---|---|---|---|
| A1 | `MAG-6` | | C1 (coil+phantom B-solve) | `MAG-1` |
| A2 | `OPS-3` | | C2 (sanity validation metrics) | `MAG-6` |
| A3 | `OPS-4` | | D1 (freq-domain scaffold) | `TH-2` |
| A4 | `GEO-7` | | D2 (phantom material MVP) | `MAT-1` |
| A5 | `OPS-5` | | D3 (E/B extraction) | `POST-1` |
| B1–B6 | `GEO-1`…`GEO-6` | | E1 (port data model) | `PORT-2` |
| C1 | `TH-2` | | E2 (birdcage port tags) | `GEO-1` |
| C2 | `MAT-1` | | E3 (port excitation hook) | `PORT-4` |
| C3 | `TH-3` | | E4 (N-port S-assembly) | `PORT-5` |
| C4 | `POST-1` | | E5 (Touchstone export) | `PORT-7` |
| C5 | `POST-2` | | E6 (calibration checklist) | `PORT-3` |
| C6 | `TH-4` | | F1 (run-and-log metadata) | `OPS-6` |
| D1–D6 | `PORT-3`…`PORT-8` | | F2 (manual checklist doc) | `OPS-7` |
| E1–E4 | `WF-1`…`WF-4` | | | |
| F1–F3 | `OPS-6`…`OPS-8` | | | |

---

## 9. Immediate sequencing

**Phase 1 is now genuinely validated** and the foundation is sound: the solver
matches the closed-form Helmholtz field to 0.04%, the full magnetostatics suite
runs green, CI guards it, and the fabricated S-parameter path is quarantined.
Attention moves to the actual physics gap.

Done 2026-07-27: `OPS-1`, `OPS-2`, `OPS-3`, `OPS-4`, `OPS-6`, `OPS-9`,
`MAG-1`…`MAG-5`, `MAG-7`, `MAG-8`, `MAG-9`, `PORT-0`.

Done 2026-07-28: `MAG-11`, `MAG-12`, `MAG-15` (and the `MAG-10` "open" item is
closed by decision — see its entry).

Done 2026-07-29: `MAG-14` (scheduled run, 1.731% vs closed form, in CI).
Done 2026-07-30: `MAG-13` in full — wire half (steps 1–3, 6) in the 22:42 run of
2026-07-29, loop fixture + convergence rework (steps 4–5) in the 07:42 run.
Also done 2026-07-30 (10:42 run): `TH-9`, the PEC cavity resonance gate —
Batch 3 step 1, real-scalar build only.
**Batch 2 is complete**; Batch 3 is under way — `TH-9` ✅, next `TH-1`
(starting with its environment step 0) + `TH-6`.

Steps 1 and 2 below carry **per-chunk implementation plans in their §7
entries** (added 2026-07-28): concrete file lists, formulas with their known
traps, acceptance criteria, and tier guidance. An implementing agent should
start from those entries, not from this summary.

1. ~~**Batch 2 — `MAG-13` + `MAG-14`**~~ — done 2026-07-29/30. The wire and loop
   cases are now true convergence gates (three-resolution fitted rate, analytic
   Dirichlet walls) and example 04 is a scale-sensitive test in CI.
2. **Batch 3 — ~~`TH-9`~~ → `TH-1` + `TH-6`** — the cavity gate landed
   2026-07-30 (purest assembly check, the resonance-guard fixture, and
   **real-mode only**, so it was not blocked on environment work); next the
   complex formulation landed against the lossy plane-wave gate in the same
   chunk. `TH-1` requires
   `dolfinx-complex-mode` (§5.3); its plan makes the environment work a
   separate logged smoke chunk because `sitecustomize.py` currently patches
   only the *real* dolfinx path.
3. **`MAT-2` + `MAT-6`** — prove materials measurably affect solved fields
   (currently guaranteed to fail, which is the point), then pin the loading
   physics against the Dodd–Deeds closed form.
4. **`PORT-1`** — real port excitation from the solved field, per the design
   sketch in §7. Resolves the two deliberately-red port tests as a side effect.
5. **Air-box generalization** — every other `io/mesh.py` fixture still uses a
   single global `setSize` and tight padding, including coil+phantom. Expect the
   same boundary-mirror error that cost 20% on Helmholtz.
6. Then `PORT-4`…`PORT-8`, then Phase 5 (`WF-5`…`WF-8`).

### ✅ RESOLVED 2026-07-28 — scheduled sessions cannot reach the Docker daemon

**Resolution (2026-07-28 21:20 CDT, interactive session):** root cause was the
Bash sandbox, not group membership — the sandbox's user namespace strips the
`docker` supplementary group, so nothing running inside it can open
`/var/run/docker.sock`. Per the Claude Code sandboxing docs, `docker` is
incompatible with the sandbox and belongs in `sandbox.excludedCommands`.
`.claude/settings.json` now excludes `docker *` and
`scripts/testing/run_and_log.sh *`; both run outside the sandbox and are still
gated by the existing permission allowlist (`Bash(docker compose *)`,
`Bash(scripts/testing/run_and_log.sh *)`), so headless runs stay auto-approved
and `docker compose down/build/rm` remain ask-gated. Verified: the exact
failing preflight re-run through the harness passes —
`docs/testing/logs/20260729T022156Z_PREFLIGHT.log` (exit 0, 1 s). Same fix
also moves automation session logs from `~/fem-em-automation/logs` to
`logs/automation/` in-repo (gitignored). The parked MAG-14 test on
`attempt/MAG-14-20260728T224647Z` is now runnable. Original report kept below
for the record.

### 🚫 Automation blocker (original report) — scheduled sessions cannot reach the Docker daemon

Found by the 2026-07-28 17:42 CDT implementer run (the first scheduled run
after `25d99d3` replaced `--dangerously-skip-permissions` with the sandboxed
allowlist). **This blocks every chunk, not just the one on deck** — no
verification can execute, so nothing can reach §4-done.

```
$ docker compose exec -T fem-em-solver bash -lc 'echo container-alive'
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

Log: `docs/testing/logs/20260728T224240Z_PREFLIGHT.log` (exit 1, 1 s). Client-only
commands still work (`docker compose version`, `docker compose config --services`
both succeed); only calls that reach the daemon fail. Inside the session `id`
reports `uid=1000(taz5297) gid=1000(taz5297) groups=1000(taz5297),65534(nogroup)`
and the socket appears as `srw-rw---- 65534 65534`, while `/etc/group` on the host
has `docker:x:989:taz5297` — i.e. the session's view of ids is namespace-remapped
and the `docker` group membership the human relies on interactively is not usable
here. No rootless daemon exists (`/run/user/1000/docker.sock` absent).

**Needs a human decision** — the agent cannot fix this from inside the sandbox
(`sudo`, host package managers and `scripts/automation/**` edits are all denied):

1. Permit the Docker socket for these sessions — sandbox write access to
   `/var/run/docker.sock`, or run the cron sessions unsandboxed. Note the
   current policy reports `dangerouslyDisableSandbox` as disabled, so this is a
   settings/managed-policy change, not a flag the wrapper can pass.
2. Or decouple verification from the agent: a host-side runner (cron/systemd)
   consumes a queue file the agent writes and drops the `run_and_log.sh` output
   back into `docs/testing/logs/`. Slower loop, immune to sandbox policy.

Until one of these lands, scheduled runs can only produce parked branches and
attempts.md entries. See `docs/testing/attempts.md` 2026-07-28T22:46Z.

### On deck — maintained by the scheduled daily review

The next scheduled implementer run takes the **first** item below that is not
marked done or blocked (see `docs/automation/implementer-run.md`). Exactly
three items, ordered, each sized for one run: ≤ 1 h wall clock, ≤ 10 min per
compute command. Items that fail twice get rescoped by the daily review
before they may reappear.

Last reviewed 2026-07-30 (daily review). Since the previous review: `MAG-14`
✅ (09:42 run; §4 audit passed — agent-executed harness log
`20260729T144331Z_MAG-14.log`, quantitative 1.731% vs closed form, 11 s
recorded) and the `MAG-13` wire half done (22:42 run; entry stays 🟡 for
steps 4–5). Three runs (13:42/16:42/19:42) were lost to the uncommitted
schedule-doc edits journaled in attempts.md; the human cleared the tree
interactively at 22:17–22:20 (`e9e49cb`, `c8d5201`) before the 22:42 slot, and
both journal requests landed with it (`crontab -l` allowlisted; protocols now
self-heal journaled doc-only drift). Tree was clean at review time — nothing
to clear. Parked branch `attempt/MAG-14-20260728T224647Z` deleted: its single
commit `b81b958` was cherry-picked to main and verified on 2026-07-29.

1. ~~`MAG-13` **steps 4–5** — loop fixture + convergence rework.~~ **Done
   2026-07-30** (07:42 run): loop on the analytic wall at h = 0.002, 7.07% vs
   the Jackson closed form, tolerance 10% → 8%; wire rate fitted over three
   resolutions, 1.10 in [0.7, 1.5]. The expected "more modest gain" was in fact
   *negative* at fixed h — the loop's PMC-image bias is smaller than the O(h)
   interpolation error of the BC data — so the gain is monotone convergence to
   the analytic field, not a lower number on the same mesh. Both fixtures are
   now **heavy** tier. See the §7 entry.
2. ~~`TH-9` — PEC cavity resonance gate.~~ **Done 2026-07-30** (10:42 run):
   `slepc4py` 3.20.0 is present in the image, so the feared long pole was a
   non-issue. First four modes of a 1.0 × 0.8 × 0.6 m box match the closed form
   to 0.0436% at the budgeted mesh (tolerance 1%), every mode improves under one
   refinement at a fitted rate of 3.85 in h, and the N1curl gradient modes come
   back as a machine-zero cluster (8/8 below 1e-8·k₁²). 3 s at `mpiexec -n 2`;
   log `20260730T154846Z_TH-9.log`. See the §7 entry.
3. `TH-1` **step 0 only** — complex-mode environment smoke (§7 `TH-1` plan
   step 0): extend `src/sitecustomize.py` (or set `PYTHONPATH` explicitly) for
   `/usr/local/dolfinx-complex`, then assert `PETSc.ScalarType == complex128`
   inside the container, logged via the harness. Smoke tier. Environment
   failures must not masquerade as formulation failures (§5.3); landing this
   before `TH-1` proper is the point.

**Do not add new features to `⚠️` subsystems.** Extending a proxy is what produced
the current backlog: roughly 20 chunks of scaffolding that will need revalidation
regardless of how carefully they were written.

**Do not trust a chunk's status without a log.** Two independent classes of defect
(`OPS-3`/`OPS-4` uncollectable; `MAG-2`/`MAG-3`/`MAG-5` evaluating in arbitrary
cells) survived months of dashboard maintenance because nothing ever executed. Every
status in §7 that is not `✅` should be read as "unknown", not "probably fine".

---

## 10. Success criteria

### MVP (end of Phase 2)
- [ ] Time-harmonic solver reproduces the analytic lossy plane-wave solution to < 5%
- [ ] Helmholtz coil magnetostatic result matches analytic to < 5% *(achieved)*
- [ ] Phantom σ and εᵣ measurably change the solved field

### Target (end of Phase 4)
- [ ] Loaded birdcage + phantom simulation runs end to end
- [ ] S-parameters derived from the solved field, not a coupling heuristic
- [ ] S-matrix satisfies reciprocity and passivity within stated tolerance
- [ ] B1+ field matches literature/measured data qualitatively

### Stretch (Phase 6)
- [ ] Multi-channel coil optimization
- [ ] Validation results published
- [ ] Community adoption

---

## 11. Key technical reference

**Function spaces** — H(curl)/Nédélec for `E` and `A`; H(div) for `B`; L2 for scalar
potential in A-V formulations.

**Boundary conditions** — PEC `n×E = 0`; PMC `n·B = 0`; ABC for radiation; PML via
complex coordinate stretching; waveguide ports for S-parameter extraction.

**Materials** — `ε = ε₀(ε' - jε'')`, `μ = μ₀(μ' - jμ'')`; anisotropic tensors;
frequency-dependent dispersion. Gelled saline at 128 MHz (3T): `σ ≈ 0.6–0.9 S/m`,
`εᵣ ≈ 78–80`; phantom diameter 16–20 cm (head), 30–40 cm (body); ~1% agarose.

**Linear solvers** — MUMPS direct for small/medium; GMRES + ILU iterative; complex
systems required for time-harmonic (`TH-1`).

**Post-processing** — `SAR = σ|E|²/(2ρ)` [W/kg]; `J = σE`; Poynting `S = ½Re(E×H*)`.

### Resources
- [FEniCSX Tutorial](https://jorgensd.github.io/dolfinx-tutorial/) ·
  [API docs](https://docs.fenicsproject.org/dolfinx/v0.7.0/)
- Similar work: [Elmer FEM](https://www.elmerfem.org/) (EM module),
  [OpenEMS](https://openems.de/) (FDTD), [scikit-rf](https://scikit-rf.readthedocs.io/)
