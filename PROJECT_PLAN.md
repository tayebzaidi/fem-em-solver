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
| 2 | Time-harmonic Maxwell, complex materials, ABC/PML | `TH-1`…`TH-8` | **Not started** — §2.1 blocks everything |
| 3 | Material models, phantoms, SAR | `MAT-1`…`MAT-5` | Presets exist but are inert |
| 4 | Coil modeling, lumped elements, ports, S-params | `PORT-1`…`PORT-8` | Placeholder-backed |
| 5 | Full MRI system: loaded birdcage, B1+, SAR maps | `WF-5`…`WF-8` | Blocked on Phases 2–4 |
| 6 | Advanced: MPI scaling, AMR, sweeps, optimization | — | Deferred |

### Critical path

```
OPS-1 (executable env) ✅        MAG-7/8/9 (repair validation) ✅
   └─> MAG re-run: core/solvers.py matches closed-form to 0.04% ✅
                 └─> TH-1 (real complex time-harmonic formulation)
                        ├─> TH-6/7/8 (analytic validation gates)
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

**Open.** The penalty is a workaround, not a gauge. A proper treatment
(tree-cotree gauging, or an A-V saddle-point formulation with a Lagrange
multiplier) would remove the null space instead of pricing it. Worth considering
before `TH-1` hardens, since the time-harmonic solver inherits this formulation
— and inherits it in complex arithmetic, where cancellation behaviour is not
obviously the same.

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

> `TH-4` is marked 🧪 rather than ⚠️ because PETSc residual/conditioning diagnostics
> are meaningful regardless of which weak form is assembled.

`TH-6`/`TH-7`/`TH-8` are cheap closed-form gates. Any one of them would have caught
the `E = -ωA` defect immediately. **Land them alongside `TH-1`, not after.**

### MAT — Materials & phantoms (Phase 3)

| ID | Title | Status | Tier | Legacy |
|---|---|---|---|---|
| `MAT-1` | Gelled saline presets (low/mid/high σ) | ⚠️ | smoke | C2 |
| `MAT-2` | Materials demonstrably affect solved fields | ⬜ | standard | *new* |
| `MAT-3` | Debye/Cole-Cole dispersion models | ⬜ | smoke | *new* |
| `MAT-4` | SAR computation `σ|E|²/(2ρ)` | ⬜ | standard | *new* |
| `MAT-5` | Temperature-dependent conductivity | ⬜ | smoke | *new* |

> `MAT-1` is `⚠️` not because the preset table is wrong, but because nothing
> consumes it. `MAT-2` is the chunk that makes `MAT-1` mean something: assert that
> a low-σ and a high-σ phantom produce fields differing by more than a stated
> threshold. It is currently guaranteed to fail — which is precisely why it is worth
> writing.

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

1. **`TH-1` + `TH-6`** together — the real complex time-harmonic formulation landed
   against an analytic gate in the same chunk, so the gate cannot be deferred.
   Requires `dolfinx-complex-mode` (§5.3), and note `sitecustomize.py` currently
   patches only the *real* dolfinx path.
2. **`MAT-2`** — prove materials measurably affect solved fields. Currently
   guaranteed to fail, which is the point.
3. **`PORT-1`** — real port excitation from the solved field. Resolves the two
   deliberately-red port tests as a side effect.
4. **`MAG-10`** — investigate why N1curl degree 2 diverges. Worth doing before
   `TH-1` hardens, since both share the gauge-penalty formulation.
5. **`J` / air-box generalization** — every other `io/mesh.py` fixture still uses a
   single global `setSize` and tight padding, including coil+phantom. Expect the
   same boundary-mirror error that cost 20% on Helmholtz.
6. Then `PORT-4`…`PORT-8`, then Phase 5 (`WF-5`…`WF-8`).

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
