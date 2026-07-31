# PROJECT_PLAN.md — FEM Electromagnetics Solver for MRI Coil Simulation

**Single source of truth for scope, status, and sequencing.** Resolved defects and
the reasoning behind past decisions live in [`docs/project-history.md`](docs/project-history.md);
nothing there is a task.

---

## 1. Mission

A FEniCSX/DolfinX finite element solver for electromagnetic simulation of MRI coils
loaded with gelled saline phantoms. Target capability:

1. Generate realistic birdcage coil + phantom geometry
2. Solve magnetostatic and **time-harmonic** Maxwell problems with complex,
   frequency-dependent materials
3. Produce credible field diagnostics and ParaView-friendly outputs
4. Produce lumped-port S-parameters usable for downstream tuning workflows

Commercial solvers (HFSS, CST) are expensive and black-box; open-source
alternatives (Elmer, OpenEMS) lack MRI-specific features. This is the gap.

---

## 2. Current state — read before planning work

A **validated magnetostatics core**, and a large body of scaffolding whose green
tests do not mean what they appear to mean.

### 2.1 The time-harmonic solver — proxy replaced 2026-07-31, closed form matched

**Was:** `core/time_harmonic.py` ran the *magnetostatic* solver for `A`, then set
`E_real ≡ 0`, `E_imag = −ω·A`. No `ω²εE` term, no `jωσ` term, no complex system;
the material response `σ + jωε₀εᵣ` was computed and discarded, so phantom
conductivity and permittivity had zero effect on any computed field.

**Now:** `TH-1` steps 1–3 landed — a complex N1curl curl-curl solve of
`∇×(μᵣ⁻¹∇×E) − k₀²ε_c E = −jωμ₀J` with MUMPS, gated by a manufactured solution
that converges at the discretisation rate (`0.9929` measured in `h`, N1curl
degree 1) and by the complex-symmetric-but-not-Hermitian structure of the
assembled operator. `ε_c` now enters the matrix, and the run requires the
complex DolfinX build (real mode raises rather than silently dropping the loss
term).

**Step 4 landed 2026-07-31** (`tests/validation/test_lossy_plane_wave.py`): the
solve now reproduces a *physical* closed form. Driving a box with the analytic
lossy plane wave `E = ẑe^{−jkx}`, `k = k₀√(ε_c)`, on its boundary and measuring
the **interior** decay and phase gives `α = 13.0695` vs `13.0670 Np/m` (**0.019%**)
and `β = 27.0312` vs `27.0152 rad/m` (**0.059%**), with the field itself at
**3.61%** relative L2 and a measured `O(h)` rate of `0.9998`. `MAT-2` rides on
the same gate: σ = 0.1 → 1.4 S/m moves the decay constant by **10.32×**, against
a closed-form **10.3116×** (0.113%), each α matching its own closed form to
< 0.24%. Conductivity now demonstrably drives the solved field.

**Step 5 landed the same day:** `core/resonance.py` flags near-resonant sweep
points from stored-energy continuity (`S = |dlnW/dlnf| ≈ 2f/|f−f₀|`, threshold
50 ⇒ 4% detuning), verified firing at 1.5% from the `TH-9` fundamental with the
energy rise matching the `|f−f₀|⁻²` pole law to 3.16%. **`TH-1` is closed.**

**What this does and does not license.** The frequency-domain *formulation* is
now validated against a physical closed form in a homogeneous medium. It is not
yet validated against a *loaded coil*: `MAT-6` (Dodd–Deeds) is the gate that
would license SAR and coil-loading figures, and §2.2's heuristic S-parameters
are untouched by any of this — `PORT-1` still owns that.

### 2.2 The S-parameters are heuristic, not computed

`ports/excitation.py` discards the solved field and derives port voltages from
invented constants (`1e-3 * support` is dimensionally meaningless; a `0.20`
coupling factor is arbitrary). The orientation-flip test passes because a helper
returns `−1.0` when two orientation *strings* differ. `PORT-1` is the fix.

### 2.3 Test assertions cannot detect either problem

Finiteness checks (`np.isfinite`, `> 0`) dominate the solver, port, material, and
post-processing suites. A solver returning `E = −ωA` passed every time-harmonic,
port, and workflow test in the repo — every one of those tests still passes
against the real complex solve, which is the measure of how little they assert.
The quantitative gates are `tests/validation/test_time_harmonic_mms.py` and
`tests/validation/test_lossy_plane_wave.py` (`TH-6` + `MAT-2`).

### 2.3b Phase-1 analytic validation was also broken (repaired 2026-07-27/30)

Nearly every Phase-1 test evaluated fields with `B.eval(points, np.arange(n))`,
which evaluates each point in an arbitrary cell. Those tests are now repaired
(`MAG-7`…`MAG-9`, `MAG-13`, `MAG-14`) and the claim "validated against analytic
solutions" is now supported for magnetostatics — but only there. See
`docs/project-history.md` for the audit that found it.

### 2.4 What is genuinely trustworthy

- **The magnetostatic formulation in `core/solvers.py`.** N1curl weak form
  `∫μ⁻¹(∇×A)·(∇×v) dx` with gauge penalty, matching closed-form Helmholtz to
  **0.04% at centre / 0.83% mean**, monotone convergence in domain size and `h`.
- The repaired validation suite: `test_helmholtz_magnitude.py` (1.731% vs closed
  form), `test_circular_loop.py` (7.07%), `test_convergence.py` (fitted rate 1.10),
  `test_cavity_resonances.py` (0.0436%), `test_gauge_lagrange.py`.
- `post/evaluation.py` — correct bounding-box/collision point location. All point
  evaluation must go through it.
- Gmsh geometry generation, mesh-tag QA, and `scripts/testing/run_and_log.sh`.

### 2.5 Before you debug a failing test

**Check [`docs/testing/known-issues.md`](docs/testing/known-issues.md) first.** It
lists every currently-failing test with symptom, the commit it was verified failing
at, and the diagnosed cause. Several tests fail on `main` for reasons unrelated to
any change you are making.

---

## 3. Status legend

| Symbol | Meaning |
|---|---|
| ✅ VERIFIED | Test executed, assertion is quantitative, passing |
| 🟡 IN PROGRESS | Actively being implemented |
| 🧪 UNVERIFIED | Code landed; test has never actually executed anywhere |
| ⚠️ PLACEHOLDER-BACKED | Implemented and "green", but rests on §2.1/§2.2 proxies |
| ⬜ NOT STARTED | |
| 🚫 BLOCKED | Cannot proceed; blocker named in the chunk |

`⚠️` is not a bug report against the chunk's own code — it means the chunk cannot
be trusted until `TH-1` lands. Do not "fix" a `⚠️` chunk by loosening its test.

---

## 4. Definition of done

A chunk is `✅ VERIFIED` when **all** of the following hold:

1. **Code and docs are committed.**
2. **The agent executed the verification command itself** and recorded the result
   via `scripts/testing/run_and_log.sh`. A chunk does not park on a human.
3. **The assertion is quantitative** — at least one check compares against:
   - a closed-form analytic solution, with a stated tolerance
   - a measured convergence rate under h- or p-refinement
   - a conservation, reciprocity, or symmetry identity
   - a documented reference value from literature or a prior validated run

   > **Finiteness-only gate:** a chunk may **not** be `✅` if every assertion it
   > adds is "is finite", "is non-zero", "has shape N", or "did not raise". Those
   > are welcome as *additional* assertions and insufficient as the *only* ones.
4. **Its runtime tier is declared and its measured elapsed time recorded.**
5. **Any dependency on a `⚠️` chunk is stated explicitly** in the chunk entry.

Never loosen a failing assertion to make a test pass. A failing analytic
comparison is evidence about the test as much as about the code.

### When human verification *is* required

Reserve it for judgments a test cannot make, and name the judgment: "does this B1+
map look physically plausible in ParaView?", "is this refinement acceptable near
the port faces?", "does this S11 curve resemble published birdcage behavior?"
Never for routine pass/fail.

---

## 5. Execution policy

### 5.1 Compute budget — shared machine

The development server is a **shared 36-core box; this project may use at most 12
cores.** Every verification command declares a tier and must not exceed it:

| Tier | Ceiling | Use for |
|---|---|---|
| `smoke` | 30 s | Imports, pure-Python logic, config validation |
| `standard` | 3 min | Coarse meshes, single small solves — the default |
| `heavy` | 20 min | Convergence studies, sweeps — must be labeled `heavy` |

- Wrap commands in `timeout` at the tier ceiling. **If a run overruns, kill it and
  redesign the case smaller.** Never re-run with a longer timeout. 20 minutes is a
  hard ceiling for any single compute command regardless of tier.
- **`mpiexec -n 12` is the hard rank ceiling.** Use the smallest count that fits
  the tier — more ranks on a fixed mesh stop paying quickly, and a bigger mesh is
  usually a better use of the budget than more ranks on a small one. Keep `-n 2`
  for anything a rank-local bug could hide in (`MAG-11` was a missing allreduce
  visible only under MPI), and note that CI runs at `-n 2`, so a test that only
  passes at wider ranks is not CI-portable.
- Record real elapsed time in `docs/testing/test-results.md`.
- **A tier is a measurement, not an intention.** A chunk whose runtime has never
  been measured is `unmeasured`. Cost-probe first: build the mesh, print the cell
  count, solve a tiny case, extrapolate, then size the real case to fit.

Cost is dominated by mesh size: ~8×10³ cells solve in seconds, ~4×10⁵ cells take
minutes, and CI cannot host the `heavy` tier.

### 5.2 Agent autonomy and loop hygiene

- Agents implement **and verify**. Human-gated completion is prohibited (§4.2).
- **No-op guard:** if a work cycle produces only documentation edits and executes
  no verification command, stop and escalate rather than commit an audit note.
- **Do not append duplicate status blocks.** Status lives in §7 tables;
  `docs/testing/pending-tests.md` is an append-only *log*, not a status store.

### 5.3 Verification environment — Docker

All verification runs inside the `fem-em-solver` container. Preflight
`docker compose -f docker/docker-compose.yml ps` — STATUS must be "Up"; `exec`
fails with `service ... is not running` otherwise, and that is a *setup* error,
not a test failure. Do **not** use the `cd docker && ...` form: a `cd` inside a
compound command prompts for permission regardless of the allowlist, which fails
in scheduled sessions.

One-time setup: `docker compose -f docker/docker-compose.yml build` (~4 min), then
`... up -d`. The repo mounts at `/workspace`, so source edits need no rebuild.

| Property | Value |
|---|---|
| Image / base | `fem-em-solver:latest` (6.26 GB) on `dolfinx/dolfinx:v0.7.2` |
| dolfinx / Python | 0.7.2 / 3.10.12 |
| Default PETSc scalar | `numpy.float64` — **real mode** |
| Complex build | `/usr/local/dolfinx-complex` |
| Memory cap | 16 GB |

**Complex scalars**, required by `TH-1`:
`source /usr/local/bin/dolfinx-complex-mode` (→ `numpy.complex128`);
`dolfinx-real-mode` switches back. The chunk commands set
`PYTHONPATH=/workspace/src`, which drops the container's dolfinx path;
`src/sitecustomize.py` re-appends the dist-packages directory matching the active
`PETSC_ARCH`, so imports resolve in **either** mode. Set
`FEM_EM_REQUIRE_COMPLEX=1` on any run that is supposed to be complex, so the
real-mode skips in `tests/environment/test_complex_mode.py` become failures, and
put `tests/environment` first in the pytest path list.

Run everything through the harness so results land in
`docs/testing/test-results.md` and `docs/testing/logs/`:

```bash
scripts/testing/run_and_log.sh <CHUNK-ID> "docker compose exec -T fem-em-solver bash -lc '...'"
```

Use `exec -T` — without it `exec` allocates a TTY and can hang under an agent. The
harness exports `COMPOSE_FILE` itself; a bare `docker compose` outside `docker/`
needs `-f docker/docker-compose.yml`.

---

## 6. Phase map

| Phase | Goal | Gating chunks | State |
|---|---|---|---|
| 0 | Infrastructure, packaging, CI, meshing | `OPS-1`, `OPS-2` | Done |
| 1 | Magnetostatics + analytic validation | `MAG-1`…`MAG-6` | **Complete and trustworthy** |
| 2 | Time-harmonic Maxwell, complex materials, ABC/PML | `TH-1`…`TH-9` | In progress — `TH-1`/`TH-6`/`TH-9` ✅; `TH-7`/`TH-8` open |
| 3 | Material models, phantoms, SAR | `MAT-1`…`MAT-6` | `MAT-2` ✅; `MAT-6` step 1 done, step 2 is the loading gate |
| 4 | Coil modeling, lumped elements, ports, S-params | `PORT-1`…`PORT-8` | Placeholder-backed |
| 5 | Full MRI system: loaded birdcage, B1+, SAR maps | `WF-5`…`WF-8` | Blocked on Phases 2–4 |
| 6 | Advanced: MPI scaling, AMR, sweeps, optimization | — | Deferred |

### Critical path

```
TH-1 (real complex time-harmonic formulation)
   ├─> TH-6/7/8 (analytic validation gates)
   ├─> MAT-2 ──> MAT-6 (materials actually affect fields; Dodd–Deeds)
   └─> PORT-1 (real port excitation) ──> PORT-2…8 ──> WF-5…8
```

**`TH-1` landed 2026-07-31; the constraint moves one link down the chain.** The
`⚠️` backlog still may not be extended until revalidated against the real solve,
and nothing S-parameter-shaped should grow until `PORT-1` replaces the heuristic.
Adding features to a proxy is what produced the `⚠️` backlog in the first place.

---

## 7. Chunk backlog

IDs are prefixed by subsystem and **globally unique and stable**. Legacy
`A1`/`B2`/`C3` IDs in commit messages and `pending-tests.md` map here via §8.
These tables are the authoritative *status*; per-chunk historical detail is in
`docs/testing/pending-tests.md`.

### OPS — Infrastructure & testing operations

| ID | Title | Status | Tier |
|---|---|---|---|
| `OPS-1` | Executable verification environment (Docker) | ✅ | smoke |
| `OPS-2` | CI runs the real test suite, not just `tests/unit` | ✅ | standard |
| `OPS-3` | Deterministic test tolerance policy | ✅ | smoke |
| `OPS-4` | Lightweight smoke matrix | ✅ | smoke |
| `OPS-5` | Testing status dashboard | ✅ | smoke |
| `OPS-6` | Expanded run-and-log metadata | ✅ | smoke |
| `OPS-7` | Guided pending-test queue helper | 🧪 | smoke |
| `OPS-8` | v1 milestone acceptance checklist | 🧪 | smoke |
| `OPS-9` | Prune duplicate/stale entries from `pending-tests.md` | ✅ | smoke |
| `OPS-10` | Complex-mode CI job for the frequency-domain gates | ✅ | smoke |

**`OPS-10` — complex-mode CI job.** `TH-1` steps 1–5 put every frequency-domain
test behind `@complex_only`, and the `validation` job runs real mode, so between
steps 1–3 and this chunk CI executed **no** time-harmonic solve at all — the MMS
convergence gate, the lossy plane-wave closed form (`TH-6`), the conductivity
gate (`MAT-2`) and the resonance guard all skipped silently. The
`validation-complex` job sources `/usr/local/bin/dolfinx-complex-mode` and runs
`tests/environment` (first, so an environment regression is not blamed on the
formulation) plus `test_time_harmonic_mms.py`, `test_lossy_plane_wave.py`,
`test_resonance_guard.py`, `test_time_harmonic_smoke.py` and
`test_boundary_condition_selection.py` under `FEM_EM_REQUIRE_COMPLEX=1`, which
converts the skips into failures so the job cannot pass by skipping. Verified
2026-07-31: 18 passed in 32 s at `-n 2` with the CI-fidelity invocation (no
`PYTHONPATH` override, package from `pip install -e`), and the real-mode
negative control fails 3 of 4 environment tests with "the complex build was not
picked up" rather than skipping. Three `@complex_only` tests are still outside
any job; the CI file names them at the point they should be added. *(2026-07-31
review: the claim that all three are blocked on known-issues entries 1 and 2 is
half stale — entry 1's two tests actually **passed** under the complex build in
`20260731T003802Z_TH-1-steps123-complexsuite.log`, because `TH-1` deleted the
code path they were failing in. Retiring entry 1 and adding those files to the
job is a §9 On-deck item. Entry 2 remains genuinely open.)*
>
> **This job has never executed on a GitHub runner.** Local `main` is 47 commits
> ahead of `origin/main` — nothing has been pushed since 2026-07-27 — so every
> "in CI" claim in this file is verified by local reproduction of the CI
> invocation only. The runner-environment caveat in the 2026-07-31T03:35Z
> attempts entry (image paths, `source` in the runner shell) settles on the
> first push, which is a human action, not a scheduled-session one.

> CI notes for anyone editing `.github/workflows/ci.yml`: MPI here is
> **MPICH/Hydra**, so `--allow-run-as-root` is not a valid flag and will break the
> job. The `validation` job timeout is 45 min (`MAG-13` is heavy tier). Two tests
> are explicitly `--deselect`ed, both downstream of the time-harmonic proxy and to
> be revisited with `TH-1`: `test_phantom_material_assignment_and_time_harmonic_pipeline_wiring`
> and `test_phantom_field_metrics_and_exports_are_finite`.

### MAG — Magnetostatics (Phase 1)

| ID | Title | Status | Tier | Result |
|---|---|---|---|---|
| `MAG-1` | Vector-potential formulation, N1curl, gauge penalty | ✅ | standard | 0.04% centre vs closed form |
| `MAG-2` | Straight-wire analytic validation | ✅ | standard | |
| `MAG-3` | Circular-loop analytic validation | ✅ | standard | |
| `MAG-4` | Helmholtz analytic validation | ✅ | standard | 0.04% centre / 0.83% mean |
| `MAG-5` | h-refinement convergence study | ✅ | standard | |
| `MAG-6` | Coil+phantom B-field symmetry metric strategy | 🧪 | unmeasured | never executed |
| `MAG-7` | Fix point evaluation in validation tests | ✅ | standard | |
| `MAG-8` | Restrict straight-wire current density to the wire | ✅ | standard | |
| `MAG-9` | Re-size validation meshes to fit the tier budget | ✅ | standard | |
| `MAG-10` | Gauge penalty was below the safe window | ✅ | standard | default now 1.0 |
| `MAG-11` | Parallel energy was rank-local (missing allreduce) | ✅ | smoke | |
| `MAG-12` | `evaluate_at_points` used the MAG-7 broken pattern | ✅ | smoke | |
| `MAG-13` | Analytic-Dirichlet outer boundary for wire/loop | ✅ | heavy | wire 12.75%, loop 7.07%, rate 1.10; 167 s + 196 s |
| `MAG-14` | Helmholtz magnitude comparison in the test suite | ✅ | smoke | 1.731% vs closed form; 11 s, in CI |
| `MAG-15` | Lagrange-multiplier Coulomb gauge (cross-check) | ✅ | smoke | 7 passed, 13 s |

**Open follow-ups in MAG** (none currently on deck):

- `MAG-6`'s revised test has never been executed. Its predecessor failed at
  `max relative |B| mismatch = 0.322` against a `< 0.30` limit — treat that figure
  as unreliable, it came from the `MAG-7` broken evaluation path.
- `MAG-13` did not reach the < 5% target on the wire. Extrapolating the measured
  rate puts it at h ≈ 0.00125, ~1.1M cells, > 5 min at `-n 2` — which was outside
  the budget when `heavy` was 10 min at 2 ranks, and **is now plausibly inside it**
  at 20 min and up to 12 ranks. Cost-probe before assuming so. The residual is
  uniform-mesh discretization of a 1/r field next to a thin conductor, so graded
  refinement is still the cheaper route than more uniform h.
  `J·n ≠ 0` at the end caps also still stands; capping the wire short of the end
  faces was never needed and is unmeasured.
- `MAG-15` is a working option, not a finished subsystem: Dirichlet conditions on
  `A` are rejected (`bc_functions` raises — so `TimeHarmonicBoundaryCondition.PEC`
  would not work); the point-pin on `p` is not `H¹`-stable in 3D, so use
  `gauge_multiplier_spread()` rather than `max|p|`; it is not wired through
  `TimeHarmonicSolver` or the port entry points; and the degree-2 cost (~7.5×
  the penalty) is unprofiled against MUMPS.

### GEO — Geometry & meshing

Independent of the §2.1 physics defect; meshes are meshes.

| ID | Title | Status | Tier |
|---|---|---|---|
| `GEO-1` | Parametric birdcage geometry generator | 🧪 | standard |
| `GEO-2` | Port-face geometry robustness checks | 🧪 | standard |
| `GEO-3` | Phantom placement presets (centered/off-center) | 🧪 | standard |
| `GEO-4` | Air-box and boundary sizing heuristics | 🧪 | smoke |
| `GEO-5` | Region-specific mesh resolution policy | 🧪 | standard |
| `GEO-6` | Geometry sanity report utility | 🧪 | smoke |
| `GEO-7` | Mesh-tag QA diagnostic hardening | 🧪 | standard |

> `GEO-4`'s substance is discharged for the two-torus fixture (`air_padding` +
> graded sizing), but it stays 🧪 until its own test executes. **Every other
> fixture in `io/mesh.py` still uses a single global `setSize` and tight padding,
> including coil+phantom** — expect the same boundary-mirror error that cost 20%
> on Helmholtz, and expect graded sizing to be equally necessary.

### TH — Time-harmonic Maxwell (Phase 2)

| ID | Title | Status | Tier |
|---|---|---|---|
| `TH-1` | **Real complex time-harmonic formulation** | ✅ | standard |
| `TH-2` | Time-harmonic API hardening | ⚠️ | standard |
| `TH-3` | Boundary-condition option set | ⚠️ | standard |
| `TH-4` | Convergence/conditioning diagnostics | 🧪 | standard |
| `TH-5` | Absorbing boundary condition (ABC) | ⬜ | standard |
| `TH-6` | **Validation: plane wave in lossy half-space** | ✅ | standard |
| `TH-7` | **Validation: waveguide cutoff / coaxial line** | ⬜ | standard |
| `TH-8` | **Validation: sphere in uniform field (quasi-static)** | ⬜ | standard |
| `TH-9` | **Validation: PEC rectangular-cavity resonances** | ✅ | standard |

**`TH-1` — Real complex time-harmonic formulation** ✅ *(all five steps,
2026-07-30/31)* **← was the critical chunk**
> Replace the `E = −ωA` proxy with an actual frequency-domain solve:
>
> ```
> ∇×(μᵣ⁻¹∇×E) − k₀²ε_c E = −jωμ₀J,    ε_c = εᵣ − j·σ/(ωε₀)
> ```
>
> Done when: `TH-6` passes against the analytic lossy plane-wave solution, and
> changing phantom σ **measurably changes the field**.
> Blocks: `MAT-2`, `PORT-1`, all of Phase 5.
>
> **Formulation notes:**
> - **The sign convention is part of the spec.** The equation assumes `e^{+jωt}`,
>   matching `ε_c = εᵣ − j·σ/(ωε₀)`. Every analytic gate (`TH-6`…`TH-9`) must be
>   derived in the same convention or validation fails spuriously with conjugated
>   fields.
> - **Do not port the gauge penalty.** At ω > 0 the operator acts as `−k₀²ε_c` on
>   the gradient subspace — nonzero everywhere, dissipative wherever σ > 0. The
>   `MAG-10` disease is statics-only; a penalty here would *add* error.
> - **Phase 2's silent-failure mode is near-resonance ill-conditioning.** With PEC
>   boundaries and lossless air the matrix is exactly singular at cavity
>   eigenfrequencies — and an MRI coil is deliberately operated near resonance.
>   MUMPS returns clean exit codes on near-singular systems, the same shape as
>   `MAG-10`'s "converged, residual 0.0, 920% error".
>
> **Steps 1–3 done 2026-07-31** (`core/time_harmonic.py` rewritten,
> `tests/validation/test_time_harmonic_mms.py`, logs
> `20260731T003553Z_TH-1-steps123-mms.log` 6 s and
> `20260731T003535Z_TH-1-steps123-probe.log` 3 s, both `-n 2`). Manufactured
> field `E_ex = (sin ky, sin kz, sin kx)`, `k = π/L`, satisfies
> `∇×∇×E_ex = k²E_ex` exactly, so the source `−jωμ₀J = (k²/μᵣ − k₀²ε_c)E_ex` is
> analytic: relative L2 error **11.26% → 5.66%** from 3072 to 24576 cells,
> **measured rate 0.9929** against the O(h) expectation for N1curl degree 1;
> `max|Im E|/max|Re E| = 3.0e-3` where the exact phasor is real (the retired
> proxy had `e_real ≡ 0` identically). The assembled operator is complex
> symmetric to `‖A−Aᵀ‖_F/‖A‖_F < 1e-10` and **not** Hermitian — the structural
> signature that the `−jσ/(ωε₀)` term survived assembly.
>
> Two things the next attempt needs to know. `solve()` now raises in real mode
> (`require_complex_mode`), after argument validation so bad-unit/bad-tag errors
> still report in both builds; the five legacy tests that solve carry
> `@complex_only` from `tests/complex_mode.py` and therefore **no longer run in
> CI**, which is a real coverage loss until CI gains a complex job. And
> `build_material_fields` still returns σ and εᵣ only, so `μᵣ` is taken from the
> scalar `problem.material` — a per-tag `μᵣ` needs that function extended.
> The hook `TH-6` needs already exists: `TimeHarmonicProblem.dirichlet_e_field`
> is interpolated onto the exterior N1curl dofs under the PEC mode, which is how
> an analytic total field is imposed on a truncation box.
>
> **Implementation plan.** Step 0 (complex-mode environment gate) is **done**
> 2026-07-30: `tests/environment/test_complex_mode.py`, 4 tests, which pins the
> step-1 conjugation trap numerically (`∫ inner(f,g) dx = 11+2j` vs
> `∫ dot(f,g) dx = −5+10j`) and the ε_c-weighted N1curl mass matrix to 4e-16
> relative. The `TH-9` cavity gate re-run under the complex build returns
> identical physics, so a failure in steps 1–5 is formulation, not environment.
>
> 1. ✅ Assemble the sesquilinear form
>    `∫μᵣ⁻¹(∇×E)·(∇×v̄) − k₀²ε_c E·v̄ dx` with `ε_c = εᵣ − jσ/(ωε₀)` built from
>    the existing DG0 `build_material_fields` (carries over unchanged); load
>    `−jωμ₀∫J·v̄ dx`. **`ufl.inner` conjugates its second argument in complex
>    mode — using `ufl.dot` for the load silently flips the sign convention.**
> 2. ✅ Direct solve, MUMPS. PEC = zero-tangential-E on exterior/tagged facets
>    (pattern exists in `build_boundary_conditions`); natural = PMC, as today.
> 3. ✅ Replace the `E = −jωA` body of `TimeHarmonicSolver.solve`; keep the
>    `TimeHarmonicFields` container (e_real/e_imag split from the complex vector)
>    so downstream `⚠️` chunks recompile without edits. `B = ∇×E/(−jω)` is the
>    post-processing route to B1+ later.
> 4. ✅ Gates in the same chunk: `TH-6` (interior decay/phase vs `k = k₀√(ε_c)`)
>    plus the `MAT-2` sensitivity assertion. Both landed 2026-07-31 in
>    `tests/validation/test_lossy_plane_wave.py`; numbers in the `TH-6` entry
>    below. The convention risk flagged here was real but benign: the wave
>    decays, `Im k < 0`, and the measured α is positive, which the test asserts
>    explicitly as the conjugation control.
> 5. ✅ The resonance guard, 2026-07-31: `core/resonance.py` takes the
>    energy-continuity option. Stored energy `W = (ε₀/4)∫εᵣ|E|²dx` behaves as
>    `W ∼ |f−f₀|⁻²` near a mode, so `S = |dlnW/dlnf| ≈ 2f/|f−f₀|` is a
>    *calibrated* detector — the default threshold 50 fires at exactly 4%
>    fractional detuning — and it costs nothing beyond the solves a sweep is
>    already doing. Verified in `tests/validation/test_resonance_guard.py`
>    against the `TH-9` fixture, driven at its **discrete** fundamental (taken
>    from the `TH-9` eigen-solver on the same mesh, not from the closed form):
>    sweeping 4% → 2% → 1% below `f₁ = 2.399584e8 Hz` raises the stored energy
>    **16.505×** against the pole law's **16.0×** (3.16%), `S = 137.554`
>    (implied detuning 1.454%, against the ~1.5% the sweep was placed at), while
>    the midband control at `(f₁+f₂)/2` stays clear at `S = 21.951`. Both
>    verdicts hold with a factor of two of margin on the threshold.
>
> The two risks flagged during planning both materialised and both were benign.
> The convention risk resolved as a positive measured α (asserted). The
> "near-mode ill-conditioning read as a formulation bug" risk showed up in the
> guard's own control sweep: the first mid-band placement at `f₁ + 0.35(f₂−f₁)`
> measured `S = 48.9` and looked like a false positive, but it is 6% above `f₁`
> and the guard's implied detuning read 4.1% — the *guard was right and the
> control was misplaced* (`20260731T021415Z_TH-1-step5.log`).

**`TH-9` — PEC cavity resonance gate** ✅ *(2026-07-30, `core/cavity.py` +
`tests/validation/test_cavity_resonances.py`, log `20260730T154846Z_TH-9.log`,
3 s at `-n 2`)*
> Cavity 1.0 × 0.8 × 0.6 m, N1curl degree 2: first four modes match the closed
> form `f = (c/2)·√((m/a)² + (n/b)² + (p/d)²)` to **0.0436%** at 720 cells and
> 0.0102% at 2268; fitted refinement rate **3.85** in h; the 8 gradient modes
> return as a machine-zero cluster (max |λ|/k₁² = 3.2e-15), none leaking into the
> physical band.
>
> **Two traps worth keeping:** the plan's suggested 1.0 × 0.7 × 0.5 m box is
> degenerate (`d = a/2` puts two modes at exactly 368.5 MHz). And PEC rows must be
> assembled with a large diagonal in `A` and **unit** diagonal in `B` — a zero
> diagonal in `B` makes it singular and invalidates the GHEP orthogonalisation.
>
> This is the known-frequency fixture the `TH-1` resonance guard is verified
> against.

**`TH-6` — lossy plane wave vs closed form** ✅ *(2026-07-31,
`tests/validation/test_lossy_plane_wave.py`, log `20260731T020427Z_TH-6-gate3.log`,
21 s at `-n 2`, complex build)*
> `E = ẑ e^{−jkx}` with `k = k₀√(ε_c)` on the `Im k < 0` branch is an exact
> **source-free** solution of the solved PDE, so the gate imposes it as Dirichlet
> data on all six faces of a 0.1 m box (εᵣ = 78, σ = 0.7 S/m, 127.74 MHz) and
> measures the *interior* slopes — nothing in the boundary data says how fast the
> field must decay, that is `ε_c` acting through the mass term. Measured:
> `α = 13.0695` vs `13.0670 Np/m` (**0.019%**, δ = 76.53 mm), `β = 27.0312` vs
> `27.0152 rad/m` (**0.059%**), relative L2 `7.218e-2 → 3.609e-2` from 10368 to
> 82944 cells, **rate 0.9998** in `h`. Clears §10's "< 5% vs the analytic lossy
> plane wave" MVP criterion.
>
> **Three things worth keeping.** The 5% bar is on the *field norm*, and N1curl
> degree 1 at 16³ lands at 5.41% — just over (`20260731T020308Z_TH-6-gate.log`);
> the fix was mesh, not tolerance, and α/β were already at 0.2% there, so the
> log-slope fit is far more forgiving than the L2 norm. The probe line sits at
> `0.5137·L` in y and z so it never lands on a facet plane of the structured
> mesh. And `post/evaluation.py` gathered into a `float64` buffer, which throws a
> casting error the moment it is handed a complex-mode Function — fixed here to
> follow the function's own dtype; it had simply never been called under the
> complex build before.

> `TH-7`/`TH-8` are cheap closed-form gates in the same mould; any one of them,
> or `TH-6`, would have caught the `E = −ωA` defect immediately.

> `TH-4` is 🧪 rather than ⚠️ because PETSc residual/conditioning diagnostics are
> meaningful regardless of which weak form is assembled.

> `TH-5` demoted off the MVP path: a birdcage operates inside an RF shield, so a
> **PEC outer boundary is physically correct** for the Phase-5 deliverables.
> ABC/PML is needed only for unshielded free-space validation geometries.

### MAT — Materials & phantoms (Phase 3)

| ID | Title | Status | Tier |
|---|---|---|---|
| `MAT-1` | Gelled saline presets (low/mid/high σ) | ⚠️ | smoke |
| `MAT-2` | Materials demonstrably affect solved fields | ✅ | standard |
| `MAT-3` | Debye/Cole-Cole dispersion models | ⬜ | smoke |
| `MAT-4` | SAR computation `σ|E|²/(2ρ)` | ⬜ | standard |
| `MAT-5` | Temperature-dependent conductivity | ⬜ | smoke |
| `MAT-6` | **Dodd–Deeds coil-over-lossy-half-space impedance** | 🟡 | standard |

> `MAT-1` is `⚠️` not because the preset table is wrong but because nothing
> consumes it.

**`MAT-2` — conductivity demonstrably drives the solved field** ✅ *(2026-07-31,
`tests/validation/test_lossy_plane_wave.py::test_conductivity_measurably_changes_the_field`,
log `20260731T020427Z_TH-6-gate3.log`, 21 s at `-n 2`, complex build)*
> Stronger than the "differ by a stated threshold" originally planned: σ = 0.1
> and σ = 1.4 S/m are solved on the same 24³ box at 127.74 MHz and each interior
> decay constant is compared with *its own* closed form — 2.1193 vs 2.1243 Np/m
> (0.233%) and 21.8781 vs 21.9045 Np/m (0.121%) — and the **ratio** 10.3232 is
> compared with the closed-form 10.3116 (0.113%). A σ-independent solver (the
> retired proxy) returns ratio 1. `MAT-6` still owns the coil-loading claim.

> `MAT-6` is the quantitative teeth for `MAT-2`. Dodd & Deeds (1968) gives the
> closed-form impedance change of a circular coil above a layered conductive
> half-space — the project's headline physics, *"the phantom loads the coil"*, in
> closed form. Upgrades `MAT-2` from "fields differ by a threshold" to "the coil
> impedance change matches a published solution", and bridges `TH-1` to `PORT-1`.

**`MAT-6` step 1 — the closed form itself** ✅ *(2026-07-31, 00:00 implementer
run, `src/fem_em_solver/utils/dodd_deeds.py` +
`tests/validation/test_dodd_deeds_impedance.py`, log
`20260731T050449Z_MAT-6-step1b.log`, 6 tests, 2 s at `-n 2`, real build)*
> `ΔZ = jωπμ₀a² ∫₀^∞ Γ(α) J₁(αa)² e^{−2αh} dα`, `Γ = (μᵣα−α₁)/(μᵣα+α₁)`,
> `α₁ = √(α²+jωμ₀μᵣσ)`, integrated piecewise between the zeros of `J₁(αa)`.
> The anchor is the **perfect-conductor limit**: at σ = 10¹² S/m the Hankel
> integral gives `ΔL = −6.753682e−08 H` against `−6.753694e−08 H` from minus the
> image mutual inductance `−2πa·A_φ(a,2h)` computed with the elliptic-integral
> `A_φ` in `AnalyticalSolutions` — **0.0002%**, two derivations sharing no
> algebra beyond μ₀, which is what pins the `jωπμ₀a²` prefactor and the sign of
> Γ. Also gated: σ = 0 is *exactly* invisible; ΔR > 0 and ΔX < 0 for a real
> conductor; the thin-skin identity `ΔR = ΔX − ΔX_pec` converging monotonically
> to 0.99973 by σ = 10⁸ S/m; and `ΔR ∝ ω^0.5009` over a decade (expect 0.5).
>
> **Known limitation, deliberate.** This is the 1968 *eddy-current* kernel:
> displacement current is neglected on both sides, which is exactly what makes
> a σ = 0 half-space vanish identically (a first draft mixed a full-wave
> half-space with a magnetoquasistatic free-space kernel and reflected Γ = −1
> off vacuum — log `20260731T050326Z_MAT-6-step1.log`). Gelled saline at
> 127.74 MHz has loss tangent ≈ 1.26, i.e. **outside** this kernel's regime.

**`MAT-6` step 2 — the FEM gate** ⬜ *(the part that actually closes the chunk)*
> Solve a filamentary loop over a lossy half-space with `TimeHarmonicSolver`
> and extract ΔZ by the reaction integral `ΔZ = −(1/I²)∫(E_loaded − E_free)·J dV`
> over the source region, i.e. two solves differing only in the half-space σ, so
> the coil self-impedance and the PEC-truncation error cancel in the difference.
> Two decisions step 2 must make before meshing: (a) gate against a **high-σ**
> half-space where the step-1 kernel is valid, or first upgrade step 1 to the
> full-wave kernel (`α₀ = √(α²−k₀²)` above, `α₁ = √(α²−ω²μ₀ε₀ε_c)` below, with an
> `α/α₀` weight) so saline is in range; (b) size the air box so the PEC outer
> boundary does not contaminate ΔZ — cost-probe this, it is the likely time sink.
>
> **Decision (a) taken by the 2026-07-31 review: gate inside the eddy-current
> kernel's regime; defer the full-wave upgrade.** A σ that is both eddy-valid
> and meshable exists — the constraint set is loss tangent σ/(ωε₀) ≳ 10² *and*
> δ = √(2/(ωμ₀σ)) resolvable (≥ 3–4 cells, slab ≥ 3δ) *and* k₀·box ≪ 1, and at
> a few tens of MHz with σ of a few S/m all three hold with δ at centimetres.
> Frequency is a free knob here: nothing ties this gate to 127.74 MHz, and the
> saline-regime (full-wave) version can become a follow-up chunk if it is ever
> needed. Decision (b) is the §9 item-1 probe. Split as On-deck items 1–2.

**`MAT-6` step 2a — fixture + cost/air-box probe** ✅ *(2026-07-31, 04:30
implementer run, `MeshGenerator.loop_over_half_space_domain` +
`scripts/probes/mat6_step2a_probe.py`, logs
`20260731T094211Z_MAT-6-step2a-boxprobe.log` (96 s) and
`20260731T094411Z_MAT-6-step2a-boxprobe-w20.log` (196 s), `-n 2`, heavy tier,
complex build)*
> **Configuration chosen** (all three eddy-current constraints checked, not
> assumed): f = 10 MHz, σ = 100 S/m, εᵣ = 1, a = 0.04 m, h = 0.02 m,
> r_wire = 0.0025 m. Loss tangent σ/(ωε₀) = **1.80e5**; δ = **15.915 mm** at
> **3.18** near-cells per δ with the slab **6.28 δ** deep (it fills the whole
> lower half-box, so the PEC floor sits where the field is already dead);
> k₀·(box diagonal) = **0.073 / 0.109 / 0.145** at W = 0.10 / 0.15 / 0.20 m.
> Low f with high σ is what satisfies δ-resolvable and k₀·box ≪ 1 at once —
> δ ∝ 1/√(fσ) but k₀ ∝ f.
>
> **Both probe numbers, at three box half-widths** (graded mesh: 2 mm on the
> wire, 5 mm in the near box, 25 mm far; ΔZ by the reaction integral
> `−(1/I²)∫(E_loaded−E_free)·J dV` over the wire):
>
> | W [m] | cells | ΔR [Ω] | ΔX [Ω] | vs closed form | solve [s] |
> |---|---|---|---|---|---|
> | 0.10 | 96 726 | +0.30952 | −0.39841 | ΔR −4.05%, ΔX −35.3% | 14.4 |
> | 0.15 | 138 619 | +0.32769 | −0.50027 | ΔR +1.58%, ΔX −18.8% | 26.5 |
> | 0.20 | 205 327 | +0.32857 | −0.52812 | ΔR +1.85%, ΔX −14.3% | 69.0 |
>
> Closed form (filamentary, step 1): ΔZ = +0.322596 − j0.615868 Ω.
> **(i) Box sensitivity**: 0.10→0.15 moves ΔR by 5.87% and ΔX by 25.6%;
> 0.15→0.20 moves ΔR by **0.268%** and ΔX by **5.57%**. **(ii) Wall clock per
> solve** at `-n 2`: 14.4 / 26.5 / 69.0 s, plus 6.5 / 9.9 / 14.5 s of meshing;
> a full four-solve two-box sweep is 196 s — heavy tier, not standard.
>
> **The two parts of ΔZ are not equally gateable, and that is the step-2b
> finding.** ΔR is converged in box size by W = 0.15 (0.27% left) and sits
> **1.6–1.9%** off the closed form. ΔX is still drifting monotonically toward
> the reference (−35% → −19% → −14%) and has 5.6% of box motion left at
> W = 0.20. Two contributions are not separated yet: PEC-wall imaging of the
> induced currents, and the **finite wire section** — the reference is
> filamentary, and re-evaluating it at h ± r_wire spreads ΔR by 38% and ΔX by
> 30%, so a fat torus is a first-order modelling error, not a rounding one.
>
> **Recommendation for step 2b** (rescope, not a free pass): assert ΔR against
> the closed form at a tolerance sized from the measurement — 5% covers the
> 1.9% offset plus the 0.27% box motion — plus the σ = 0 control, and gate ΔX
> only on **sign and order of magnitude** until the wire is thinned (h/r_wire
> ≥ 16, i.e. r_wire ≤ 1.25 mm) or the box reaches W ≥ 0.25. Do not close
> `MAT-6` on a tolerance widened to swallow 14%.

> **Trap found, costs a run if rediscovered.** `ufl.max_value` does not compile
> in the complex build — UFL refuses conditionals on complex-valued operands —
> so the magnetostatic loop fixture's `azimuthal_current_density`
> (`tests/validation/test_circular_loop.py`) cannot be reused verbatim in any
> frequency-domain solve. The probe regularises inside the square root instead
> (`sqrt(x²+y²+1e-24)`). A killed run also leaves a stale FFCx lock that makes
> the *next* run fail with "JIT compilation timed out, probably due to a failed
> previous compile"; clear it with `rm -rf ~/.cache/fenics` in the container.

### POST — Post-processing & field extraction

| ID | Title | Status | Tier |
|---|---|---|---|
| `POST-1` | Interface-aware field extraction reliability | ⚠️ | standard |
| `POST-2` | Energy/consistency diagnostics | ⚠️ | standard |
| `POST-3` | Replace vacuous consistency metrics | ⬜ | standard |

> The current flagship metric `e_to_b_mean_ratio` is by construction
> `≈ ω·|A|/|∇×A|` — it measures a mesh length scale, not physics, and cannot
> detect that the solver is wrong. After `TH-1`, replace it with checks that can
> fail for real reasons: Poynting flux balance, `∇·(σE)` residual, or reciprocity.

### PORT — Ports & S-parameters (Phase 4)

**All `⚠️` chunks below sit on the §2.2 placeholder.**

| ID | Title | Status | Tier |
|---|---|---|---|
| `PORT-0` | Quarantine the placeholder coupling model | ✅ | smoke |
| `PORT-1` | **Real port excitation from the solved field** | ⬜ | standard |
| `PORT-2` | Port data model and tagging contract | 🧪 | smoke |
| `PORT-3` | Calibration checklist → executable checks | 🧪 | standard |
| `PORT-4` | Multi-port drive/termination consistency | ⚠️ | standard |
| `PORT-5` | S-matrix reciprocity/passivity metrics | ⚠️ | smoke |
| `PORT-6` | Frequency sweep orchestration | 🧪 | smoke |
| `PORT-7` | Touchstone metadata + parser cross-check | 🧪 | smoke |
| `PORT-8` | Port-orientation sensitivity | ⚠️ | standard |

**`PORT-1` — Real port excitation from the solved field** ⬜
> Gap-voltage lumped ports, the standard approach for MRI coils at 64–300 MHz:
> excite one port per solve with an impressed gap source; recover `V_i = −∫E·dl`
> across each port gap and terminal currents from the solved field; assemble the
> Z-matrix column-by-column from N single-port solves; convert
> `S = (Z − Z₀I)(Z + Z₀I)⁻¹`.
> Done when: `‖Z − Zᵀ‖/‖Z‖` (reciprocity) sits below a stated tolerance — a real,
> failable identity replacing the placeholder-arithmetic assertions. Depends on
> `TH-1`; wave ports are out of scope at these frequencies.

> **Two port tests are red and deliberately left red.** Both fakes set
> `current = voltage/z0` at the driven port, making it perfectly matched, so
> `b = (V − Z₀I)/2√Z₀ = 0` and the S-matrix diagonal is legitimately zero against
> an assertion demanding non-zero. Fixing them means tuning assertions to match a
> heuristic that `PORT-1` deletes; resolve them there.

> `PORT-3` was 🚫; its recorded failure was a docker preflight error, not a code
> failure, and `OPS-1` resolved that. Real status is unknown — hence 🧪, not ✅.

> `PORT-0` quarantine: `PlaceholderPortModelWarning` on every call, `is_placeholder`
> threaded through the result types, and `export_touchstone()` refuses flagged data
> unless `allow_placeholder=True`. Fabricated `.s2p` files can no longer leave the
> project looking authoritative. `PORT-6`/`PORT-7` are 🧪 rather than ⚠️ — sweep-grid
> generation and Touchstone *formatting* are correct independent of what fills the
> matrix.

### WF — End-to-end workflow & MRI outputs (Phase 5)

| ID | Title | Status | Tier |
|---|---|---|---|
| `WF-1` | MRI example CLI/config | 🧪 | smoke |
| `WF-2` | Reproducible output bundle manifest | ⚠️ | standard |
| `WF-3` | Quick-look phantom metrics report | ⚠️ | standard |
| `WF-4` | Scenario presets (debug/dev/benchmark-lite) | 🧪 | standard |
| `WF-5` | Loaded birdcage: frequency shift & Q degradation | ⬜ | heavy |
| `WF-6` | B1+ field mapping and homogeneity (CV) | ⬜ | heavy |
| `WF-7` | SAR10g hotspot identification | ⬜ | heavy |
| `WF-8` | Publication-quality visualization pipeline | ⬜ | standard |

> `WF-2`/`WF-3` produce structurally valid manifests and reports containing
> physically meaningless numbers. The plumbing is fine and becomes useful the
> moment `TH-1` lands.

---

## 8. Legacy ID mapping

Commit messages, `docs/testing/pending-tests.md`, and `docs/testing/logs/*.log`
use older IDs. Two generations collided — `E1`–`E4` refer to *different chunks* in
the ROADMAP than in `pending-tests.md`. Resolve via this table.

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

Phase 1 is complete and CI guards it. `TH-1` closed 2026-07-31 against the lossy
plane-wave closed form; attention moves to the loaded-coil gate and ports.

1. **`MAT-6` step 2** — the Dodd–Deeds FEM loading gate, split into probe + gate
   in On deck below. This is what licenses coil-loading and SAR claims.
2. **`TH-7`/`TH-8`** — the remaining cheap closed-form gates on the
   frequency-domain solver; each is one run in the `TH-6` mould.
3. **`POST-3`** — replace the vacuous consistency metrics with identities that
   can fail (Poynting balance), now unblocked by `TH-1`.
4. **`PORT-1`** — real port excitation from the solved field. Resolves the two
   deliberately-red port tests as a side effect. **Needs a §7-grade
   implementation plan before it can be queued — writing that plan is the next
   review's first job.**
5. **Air-box generalization** — every other `io/mesh.py` fixture still uses a
   single global `setSize` and tight padding, including coil+phantom.
6. Then `PORT-4`…`PORT-8`, then Phase 5 (`WF-5`…`WF-8`).

**Do not add new features to `⚠️` subsystems.** Extending a proxy is what produced
the current backlog: roughly 20 chunks of scaffolding needing revalidation.

**Do not trust a chunk's status without a log.** Two independent classes of defect
survived months of dashboard maintenance because nothing ever executed. Every
status in §7 that is not `✅` should be read as "unknown", not "probably fine".

### On deck — maintained by the scheduled daily review

The next scheduled implementer run takes the **first** item below that is not
marked done or blocked (see `docs/automation/implementer-run.md`). At least five
open items — the four runs before the next review, plus a spare — ordered, each
sized for one run: ≤ 1 h wall clock, ≤ 20 min per compute command. Prefer items
that do not depend on each other; where the critical path is genuinely serial,
say so in the item. Items that fail twice get rescoped by the review before they
may reappear. If every item is done, the implementer falls back to the "obvious
next entry" named below.

Last reviewed 2026-07-31, 03:00 daily review. Tree clean, no `attempt/*` or
`recovered/*` branches. Audit: every status that flipped ✅ since the last review
(`MAG-13`, `TH-9`, `TH-1`, `TH-6`, `MAT-2`, `OPS-10`) is §4-compliant — harness
logs, quantitative assertions, and elapsed times all present; nothing demoted.
The four struck-through items from the previous queue are recorded in
attempts.md and the §7 entries; this is a fresh queue.

1. ~~**`MAT-6` step 2a — loop-over-half-space FEM fixture + cost/box probe.**~~
   **Done 2026-07-31, 04:30 implementer run** — see the `MAT-6` step-2a entry in
   §7 for the chosen configuration, both probe numbers, and the ΔR/ΔX split that
   rescopes item 2 below. Original text kept for the record:
   Complex build, standard tier. Pick the gate parameters *first*, inside the
   step-1 kernel's regime rather than upgrading the kernel (decision (a) in the
   §7 entry): εᵣ = 1 half-space, and (f, σ) chosen so that loss tangent
   σ/(ωε₀) ≳ 10², skin depth δ = √(2/(ωμ₀σ)) spans ≥ 3–4 cells with the slab
   ≥ 3δ deep, and k₀·(box diagonal) ≪ 1 (the kernel neglects air-side
   retardation). Tens of MHz with σ of a few S/m lands δ at a few cm — compute
   these, don't trust this sentence. Reuse the volumetric loop-current source
   pattern from the magnetostatic loop fixture for J. Then the probe: solve
   loaded and free at **two air-box sizes**, extract
   `ΔZ = −(1/I²)∫(E_loaded − E_free)·J dV` over the source region both times,
   and record (i) the box-size sensitivity of ΔZ and (ii) wall-clock per solve.
   Product: the chosen configuration plus both numbers in the §7 entry, and a
   first *unasserted* ΔZ against `utils/dodd_deeds.py`. Graded mesh — the
   known-issues air-box note applies to exactly this kind of fixture.
2. **`MAT-6` step 2b — the gate.** Item 1 landed, so the configuration and the
   tolerance budget are fixed by the §7 step-2a table: run
   `MeshGenerator.loop_over_half_space_domain` at **W = 0.15** (138 619 cells,
   ~27 s per solve at `-n 2`; two solves + mesh ≈ 75 s, **standard tier fits,
   heavy tier if the σ = 0 control is a third solve**) and turn the probe's ΔZ
   extraction into a `tests/validation/test_dodd_deeds_impedance.py` FEM test.
   **Assert ΔR against the closed form at 5%** (measured offset 1.6–1.9%, box
   motion 0.27% — this is a measurement, not a fitted bound) plus the σ = 0
   control (the reaction-integral difference ≈ 0, the negative control a
   σ-blind solver fails). **ΔX gets sign + order of magnitude only** and an
   explicit code comment saying why: 14.3% residual at W = 0.20 that the probe
   could not split between PEC-wall imaging (5.6% still moving) and the finite
   wire section (the filamentary reference spreads 30% over h ± r_wire).
   Closing `MAT-6` on a tolerance widened to swallow that 14% is exactly the
   move §7's MAG defect-5 note forbids. Complex build.
3. **`TH-7` — waveguide-cutoff gate**, independent; the `TH-6` pattern on a new
   closed form. PEC a×b×L box, complex build, standard tier: impose the analytic
   evanescent TE₁₀ field `E_y = sin(πx/a)·e^{−γz}`, `γ = √(k_c² − k₀²)`, on all
   faces via `dirichlet_e_field` at f **below cutoff** and fit the interior
   decay against γ exactly as `test_lossy_plane_wave.py` fits α. Below cutoff
   there is no resonance risk; if an above-cutoff β case is added, place f away
   from the box's discrete modes and show the resonance guard stays quiet, or
   drop that half. Same `e^{+jωt}` convention discipline as every TH gate.
4. **`POST-3` step 1 — power-balance identity on the `TH-6` fixture**,
   independent. Complex build, standard tier. On the lossy plane-wave solve:
   absorbed power `½∫σ|E|²dV` vs net inward Poynting flux `−∮½Re(E×H̄)·n̂ dS`
   with `H = ∇×E/(−jωμ₀)`; assert the relative imbalance below a stated
   tolerance at two resolutions and that it shrinks with h. Traps: facet-normal
   sign, and `assemble_scalar` is rank-local — reduce both integrals before
   comparing. Deprecate `e_to_b_mean_ratio` as the flagship metric in the same
   commit (§7 POST note).
5. **Retire known-issues entry 1**, independent, smoke tier. Both
   `DummyMagnetostaticSolver` tests **passed** under the complex build in
   `20260731T003802Z_TH-1-steps123-complexsuite.log` — `TH-1` deleted the
   attribute read they were failing in. Re-verify through the harness, remove
   the two `--deselect`s from the `validation` job, add both files to
   `validation-complex`, and delete the known-issues entry in the same commit.
   While there: the run emits `ComplexWarning` (complex→real casts) at
   `tests/materials/test_phantom_material_model.py:33-34` and
   `src/fem_em_solver/post/phantom_fields.py:88` — fix the test-side casts; the
   `phantom_fields.py` one is `POST-1` territory, record it there if not fixed.
6. **`TH-8` — sphere in a uniform quasi-static field** (spare), independent.
   Dielectric sphere, closed-form interior field `E_in = 3/(ε_c + 2)·E₀`:
   impose the full exterior solution (uniform + dipole) on the box boundary,
   assert the interior field's magnitude and uniformity. Needs a tagged
   sphere-in-box gmsh fixture (pattern exists in `io/mesh.py`); choose f so
   k₀R ≪ 1, and cost-probe before sizing. Complex build, standard tier.

If the queue drains: take `TH-8` if still open; otherwise stop and journal —
`PORT-1` is next on the critical path but needs the review to write its §7-grade
plan first, and an implementer run should not improvise it.

Every frequency-domain command needs `source /usr/local/bin/dolfinx-complex-mode`
**and** `FEM_EM_REQUIRE_COMPLEX=1`, with `tests/environment` first in the pytest
path list, so an environment regression fails before the formulation tests get
blamed.

---

## 10. Success criteria

### MVP (end of Phase 2)
- [x] Time-harmonic solver reproduces the analytic lossy plane-wave solution to < 5% *(3.61% in L2; decay constant 0.019%, `TH-6`)*
- [x] Helmholtz coil magnetostatic result matches analytic to < 5% *(0.04%)*
- [x] Phantom σ and εᵣ measurably change the solved field *(σ: interior decay
  constants each match their own closed form and their ratio is 10.3232 vs the
  closed-form 10.3116, `MAT-2`; εᵣ: at εᵣ = 78 the measured β = 27.03 rad/m
  matches the εᵣ-dependent closed form 27.02 to 0.059% where vacuum would give
  2.68, `TH-6`. The loaded-**coil** claim stays open until `MAT-6` step 2.)*

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

**Function spaces** — H(curl)/Nédélec for `E` and `A`; H(div) for `B`; L2 for
scalar potential in A-V formulations.

**Boundary conditions** — PEC `n×E = 0`; PMC `n·B = 0`; ABC for radiation; PML via
complex coordinate stretching; waveguide ports for S-parameter extraction.

**Materials** — `ε = ε₀(ε' − jε'')`, `μ = μ₀(μ' − jμ'')`; anisotropic tensors;
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
