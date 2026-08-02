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
now validated against a physical closed form in a homogeneous medium, **and, as
of 2026-07-31, against a loaded coil**: `MAT-6` closed with the FEM coil
resistance change over a conductive half-space matching Dodd–Deeds to **1.58%**
(§7). The loading claim is real but bounded — it is established in the *eddy-
current* regime (10 MHz, σ = 100 S/m, loss tangent 1.8e5), and the reactive part
ΔX is gated only on sign and magnitude, so "the phantom loads the coil at
127.74 MHz" (loss tangent ≈ 1.26, displacement current not negligible) is an
extrapolation, not a validated result: it needs the full-wave kernel named in
the `MAT-6` step-2 entry. §2.2's heuristic S-parameters are untouched by any of
this — `PORT-1` still owns that.

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
- The repaired validation suite: `test_helmholtz_magnitude.py` (0.728% vs closed
  form since the `GEO-8` fragment fix, 2026-08-01; 1.731% before),
  `test_circular_loop.py` (7.07%), `test_convergence.py` (fitted rate 1.10),
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
| 2 | Time-harmonic Maxwell, complex materials, ABC/PML | `TH-1`…`TH-9` | In progress — every analytic gate closed (`TH-1`/`TH-6`/`TH-7`/`TH-8`/`TH-9` ✅); `TH-2`/`TH-3` API hardening ⚠️ |
| 3 | Material models, phantoms, SAR | `MAT-1`…`MAT-6` | `MAT-2` ✅; `MAT-6` ✅ (ΔR to 1.58%, eddy-current regime); SAR still ungated |
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
| `MAG-14` | Helmholtz magnitude comparison in the test suite | ✅ | smoke | 0.728% vs closed form (1.731% before `GEO-8`); 11 s, in CI |
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
| `GEO-8` | **Make `two_torus_domain` a conforming mesh** | ✅ | standard |

> `GEO-4`'s substance is discharged for the two-torus fixture (`air_padding` +
> graded sizing), but it stays 🧪 until its own test executes. **Every other
> fixture in `io/mesh.py` still uses a single global `setSize` and tight padding,
> including coil+phantom** — expect the same boundary-mirror error that cost 20%
> on Helmholtz, and expect graded sizing to be equally necessary.

**`GEO-8` — make `two_torus_domain` a conforming mesh** ✅ *(created
2026-07-31, 18:00 review, from the `PORT-1` step-1 block; done 2026-08-01,
19:30 implementer run)*
> **Done.** `occ.fragment([(3, box)], [(3, torus_1), (3, torus_2)])` plus
> centroid/mass re-derivation of the physical groups (fragment renumbers, so
> its tag order is not trusted — same discipline as
> `loop_over_half_space_domain`). The outer-boundary facet test tightened from
> "within one `resolution` of a wall" to "flat against the wall" (both
> bounding-box extremes, tol 1e-9): fragment creates interior faces the loose
> test could have swept into the BC. Graded sizing now references the
> fragmented wire volumes. Gate:
> `tests/mesh/test_two_torus_conforming.py` (volume half real-mode,
> field-leakage half `@complex_only`), added to both CI jobs.
>
> | quantity | before (non-conforming) | after (fragmented) |
> |---|---|---|
> | mesh volume / analytic box | 1.002633 | 1.000000000 |
> | meshed torus / analytic `2π²Rr²` | n/a (box meshed through the tori) | 0.9801, 0.9801 |
> | `∫\|E\|²` air / driven torus | 0 exactly | 1.4118 |
> | `∫\|E\|²` undriven / driven torus | 0 exactly | 5.2088e-08 |
> | Helmholtz centre-field error | 1.731% | **0.728%** |
> | Helmholtz mean error, \|z\| ≤ 0.005 m | 1.730% | **0.644%** |
> | Helmholtz central CV | 0.0216% | 0.1602% (bound 1%) |
> | cells (magnitude fixture) | 53941 | 53365 |
>
> The Helmholtz improvement is the predicted effect: the geometric `in_wire` J
> now integrates over cells aligned to the torus surface instead of
> stair-stepping through box cells. No bound was loosened; the 5% and 1% CV
> tolerances are unchanged. One measurement is worth keeping for future
> fixtures: at the uniform `resolution=0.01` the meshed torus retains only
> 0.598 of its analytic volume (5.905213e-06 vs 9.869604e-06 m³) — the wire
> needs `wire_resolution ≲ 0.4·minor_radius` before any volume-based
> conformity statement means anything, which is why the gate grades.
>
> Logs: `20260801T003039Z_GEO-8-before.log`,
> `20260801T003108Z_GEO-8-before-numbers.log` (before),
> `20260801T003415Z_GEO-8-gate.log`,
> `20260801T003600Z_GEO-8-field-gate-numbers.log` (gates, 31.8 s at `-n 2`
> complex), `20260801T003528Z_GEO-8-after.log` (gate + three users, 4 passed
> 1 skipped in 19.7 s at `-n 2`). Standard tier. Unblocks `PORT-1` steps 1–2.
>
> *Original plan, for the record:*
> The fixture adds two tori and a box and never fragments — the docstring even
> advertises "non-fragmenting geometry construction" — so gmsh meshes three
> disconnected components. Measurements are in known-issues
> ("`two_torus_domain` is not a conforming mesh"): the box is meshed solid
> through the torus regions, a driven torus's field is confined to its island
> (`∫|E|²` over the air tag exactly 0), and the `PORT-1` reaction Z-matrix has
> `Z₁₂ ≡ 0` against a closed-form `ωM₁₂ = 1.2418 Ω`.
>
> **Why the fixture's validation users pass anyway — code reading, 18:00
> review, numerically unverified.** `test_helmholtz_v2.py` and
> `test_helmholtz_magnitude.py` define J as a *geometric UFL expression*
> (`in_wire` from coordinates) assembled over the whole mesh, so the solid
> box's own cells inside the torus regions carry a full copy of the current:
> the centre field is sourced through a connected path and the 0.04% §10 claim
> is genuine. The torus islands carry a second copy of the source and solve a
> private problem nobody samples — they are inert duplicates, not part of the
> measurement. The parked `PORT-1` probe instead passed
> `subdomain_ids=[torus tag]`, which puts the source *only* on the islands —
> hence zero coupling. `test_two_torus.py` asserts tag presence only (no
> solve); `two_cylinder_domain` shares the deliberate non-fragmenting pattern
> (`io/mesh.py`) but its one user is qualitative — out of scope here.
>
> **Plan (one run).**
> 1. Re-run the three users through the harness *first* and record what they
>    measure today (centre-field and mean/cv errors, global tag sets) — the
>    "before" side this fix must publish.
> 2. `occ.fragment` the box against both tori; re-derive physical groups 1/2/3
>    from the fragment map by centroid/measure as `loop_over_half_space_domain`
>    does — do **not** trust gmsh's returned tag order. Keep tag numbering and
>    the `air_padding`/`wire_resolution`/`far_resolution` semantics; the graded
>    sizing references torus surfaces whose entity ids change under fragment,
>    so re-derive those too. Fix the now-false docstring.
> 3. Conformity gate (new smoke test): global mesh volume within the linear-tet
>    curvature deficit of the analytic box (today it *exceeds* the box by
>    1.002633×, the overlap signature); air-tag volume < box minus the meshed
>    tori; and the field check from the parked diagnostic — drive torus 1 with
>    tag-restricted J and assert `∫|E|² dV` over tag 3 > 0 where today it is
>    exactly 0.
> 4. Re-run the three users and record the after-numbers next to the
>    before-numbers. Expect the Helmholtz numbers to *move* — the geometric J
>    now integrates over cells aligned to the torus surface instead of
>    stair-stepping through box cells. Bounds move only if the fix improves
>    them; never loosened.
>
> Done when: conformity assertions pass through the harness, the three users
> are green with both sides recorded, and the known-issues entry is retired in
> the same commit. Unblocks `PORT-1` steps 1–2 (§9 items 2 and 5).

### TH — Time-harmonic Maxwell (Phase 2)

| ID | Title | Status | Tier |
|---|---|---|---|
| `TH-1` | **Real complex time-harmonic formulation** | ✅ | standard |
| `TH-2` | Time-harmonic API hardening | ⚠️ | standard |
| `TH-3` | Boundary-condition option set | ⚠️ | standard |
| `TH-4` | Convergence/conditioning diagnostics | 🧪 | standard |
| `TH-5` | Absorbing boundary condition (ABC) | ⬜ | standard |
| `TH-6` | **Validation: plane wave in lossy half-space** | ✅ | standard |
| `TH-7` | **Validation: waveguide cutoff / coaxial line** | ✅ | standard |
| `TH-8` | **Validation: sphere in uniform field (quasi-static)** | ✅ | standard |
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

**`TH-7` — Validation: waveguide cutoff** ✅ *(2026-07-31)*
> Evanescent TE₁₀ below cutoff in a PEC a×b×L box, `tests/validation/
> test_waveguide_cutoff.py`. `E = ŷ sin(πx/a) e^{−γz}` with `γ = √(k_c² − k₀²)`
> is an exact source-free solution at `εᵣ = μᵣ = 1, σ = 0` (`∇·E = 0` ⇒
> `∇×∇×E = −∇²E = k₀²E`) and satisfies PEC on the four side walls identically.
> Imposed on the whole boundary via `dirichlet_e_field`; the *interior*
> log-amplitude slope along z is fitted, and the boundary data pins only the two
> end faces.
>
> **Why it is not a repeat of `TH-6`.** `TH-6` measures decay driven by
> `Im ε_c` — the mass term's imaginary part. Here the medium is **lossless** and
> the decay comes from the transverse geometry against the operator's *real*
> part. A solver that dropped `k₀²ε` entirely still decays, at `γ = k_c` exactly;
> at `f = 2.4 GHz` that is 66% high, which is why `γ < k_c` is asserted
> separately from the 5% closed-form bound.
>
> **Measured** (a = 0.05 m, b = 0.025 m, L = 0.05 m, f_c = 2.998 GHz;
> `20260731T123411Z_TH-7-gate-final.log`, 6 tests / **9.8 s** at `-n 2`,
> standard tier): at f = 2.4 GHz, `γ = 37.650399` vs the closed form
> `37.652670 Np/m` (**0.006%**); relative L2 `8.821e-2 → 4.407e-2` from 5184 to
> 41472 cells, **rate 1.0013** in `h`. Frequency sweep at 1.0 / 2.4 / 2.8 GHz:
> each γ within 0.066% of its own closed form, end-to-end ratio 2.6373 vs 2.6383
> (**0.038%**) — the negative control a k₀-blind solver fails with a ratio of 1.
> Residual `|Im E_y|/|Re E_y|` is **exactly 0.0** (real operator, real data), the
> cheapest available check on the `e^{+jωt}` convention.
>
> The `TH-1` step-5 energy guard is asserted **quiet** rather than worked around:
> below cutoff γ is real, so the operator has no pole in the band, and the guard
> reports `max |dlnW/dlnf| = 2.769` against its threshold of 50. The above-cutoff
> β case was deliberately dropped — it buys nothing the phase fits in `TH-6` and
> `TH-9` do not already cover, and would have to be placed away from the box's
> discrete modes.

**`TH-8` — Validation: dielectric sphere in a uniform quasi-static field** ✅
*(2026-07-31, 15:00 implementer run)*
> A sphere of radius `R` and permittivity `ε` in a uniform `E₀ẑ` polarises
> uniformly: `E_in = 3/(ε+2)·E₀ ẑ` inside, uniform + point dipole outside with
> `β = (ε−1)/(ε+2)`. Both branches are curl-free, so the pair solves
> `∇×∇×E − k²E = 0` exactly up to the `O((kR)²)` the quasi-static limit drops.
> The exterior branch is imposed as Dirichlet data on the wall of a cubic air
> box (exact there — the exterior solution holds on any surface outside the
> sphere) and the **interior** field is measured. Nothing in the boundary data
> states the interior value: `3/(ε+2)` comes out of `ε` acting through the mass
> term `−k₀²ε_c E` plus the normal-`D` jump at the sphere surface.
>
> **Measured** (`R = 0.05 m`, box half-width `0.10 m`, `εᵣ = 78`, `σ = 0`,
> `k₀R = 5e-3` ⇒ `f = 4.7713 MHz`, so `k_in R = 4.4e-2` and the dropped
> retardation is ~0.2%, an order of magnitude under the discretisation error;
> `20260731T200457Z_TH-8-gate-final.log`, 6 tests / **16.2 s** at `-n 2`,
> standard tier): closed form `E_in/E₀ = 0.037500`; measured
> **9.546% → 4.270% → 2.443%** at `h_sphere = 0.0125 / 0.00833 / 0.00625`
> (5866 / 17670 / 39693 cells), **fitted rate 1.9675** in `h` over the three
> resolutions. Interior spread across probe points inside `0.55 R` falls
> `0.877% → 0.342% → 0.080%` and the transverse component `2.038% → 0.085%`,
> both against the closed form's *uniform, purely z-directed* interior.
> `|Im E_z|/|Re E_z|` is **exactly 0.0** (lossless material, real boundary
> data) — the same cheap `e^{+jωt}` convention check `TH-7` uses.
>
> The negative control is the discriminator that matters here: drop the sphere
> from the `material_map` (vacuum everywhere, **same** Dirichlet data) and the
> interior field goes to **0.918 V/m**, i.e. 2348% off the closed form and
> within 8% of `E₀`. The asserted interior value is 26.7× smaller than `E₀`
> while the dipole term contributes at most `2βR³/W³ ≈ 24%` of `E₀` at the
> wall, so the gate cannot be passing by reading back its own boundary data.
>
> The rate is ~2 rather than the O(h) of `TH-6`/`TH-7` because the asserted
> quantity is a probe-averaged interior functional of a field that is
> *piecewise constant* in the sphere, not a global L2 norm of an oscillating
> one — superconvergence in the functional, not a better element. The bound
> asserted is the 5% MVP criterion at the finest mesh (2.443% measured), with
> uniformity and transverse bounds at 1% (0.080% / 0.085% measured).
>
> New fixture: `MeshGenerator.sphere_in_box_domain` (cell tags `1` sphere,
> `2` air; facet tag `1` outer wall). Sizing is a gmsh `Ball` field, not a
> `Distance` field from the sphere surface — the latter is unsigned and would
> coarsen towards the centre, which is precisely where the gate measures.
>
> Not covered: a *lossy* sphere (`σ > 0`, complex `ε_c`) would exercise the
> same closed form with a complex depolarisation factor and is the obvious
> cheap extension; and the low-frequency limit is not stressed — at
> `k₀R = 5e-3` the mass term is ~1e-4 of the curl block, and pushing `k₀R`
> further down is where a low-frequency-breakdown failure would first appear.

> `TH-8` is a cheap closed-form gate in the same mould; it, `TH-7`, or `TH-6`
> would have caught the `E = −ωA` defect immediately.

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
| `MAT-6` | **Dodd–Deeds coil-over-lossy-half-space impedance** | ✅ | heavy |

> `MAT-1` is `⚠️` not because the preset table is wrong but because nothing
> consumes it.

**`MAT-4` — SAR computation** ⬜ *(implementation plan 2026-07-31, 18:00
review)*
> **Step 1 — the lossy-sphere gate (one run).** Extend the `TH-8` fixture
> (`sphere_in_box_domain` + the `test_dielectric_sphere.py` machinery) to
> σ > 0: the same closed form holds with complex permittivity,
> `E_in = 3E₀/(ε_c + 2)`, `ε_c = εᵣ − j·σ/(ωε₀)`, entering both the exterior
> Dirichlet data (the dipole coefficient) and the reference. Implement
> pointwise `SAR = σ|E|²/(2ρ)` (in `post/`, peak-phasor convention per §11)
> and gate the interior mean SAR against the closed-form
> `σ·|3E₀/(ε_c+2)|²/(2ρ)` at two resolutions. This is the first quantitative
> assertion anywhere on the **imaginary axis of ε_c** — `TH-8` measured
> `|Im E_z|/|Re E_z|` exactly 0 by construction, so the lossy path of the
> material model is currently ungated.
> Traps: (i) do **not** route the field through `post/phantom_fields.py` —
> its `dtype=np.float64` cast discards `Im(E)` (the `POST-1` defect recorded
> below); compute SAR in UFL from the solution directly. (ii) Check
> quasi-static validity *numerically in the test*: `|k_in|·R ≪ 1` with
> `k_in = k₀√ε_c` — loss inflates `|ε_c|`, so a σ that looks physically mild
> can leave the closed form's regime silently; print `σ/(ωε₀)` and `|k_in|R`.
> (iii) State the ½ (peak-phasor) convention in the docstring and keep it
> consistent with `poynting_power_balance`. Controls: a σ-blind control in the
> `TH-8` ε-blind mould, and two σ values each gated against its own closed
> form (the `MAT-2` two-decay pattern). Complex build, standard tier — the
> `TH-8` suite runs in 16 s; expect similar.
> **Step 2 (later, do not improvise in step 1):** mass-averaged SAR
> (1 g / 10 g) on the phantom mesh — needs ρ as a field and an averaging-volume
> decision.

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

**`MAT-6` step 2 — the FEM gate** ✅ *(closed 2026-07-31 by step 2b, below)*
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

**`MAT-6` step 2b — the gate** ✅ *(2026-07-31, 06:00 implementer run,
`tests/validation/test_dodd_deeds_impedance.py` FEM half, log
`20260731T110515Z_MAT-6-step2b-gate-numbers.log`, 10 tests, **85 s** at `-n 2`,
heavy tier, complex build)*
> **`MAT-6` is closed. The coil-loading claim is now quantitative.** One mesh
> (`loop_over_half_space_domain` at W = 0.15, **138 619 cells**) and three
> solves at 25.6 / 23.8 / 23.9 s, in a module-scoped fixture:
>
> | quantity | FEM | closed form | gate |
> |---|---|---|---|
> | ΔR | **+0.3276882 Ω** | +0.3225961 Ω | **1.58%**, asserted < 5% |
> | ΔX | −0.5002739 Ω | −0.6158675 Ω | ratio **0.8123**, sign + O(1) only |
> | null control | +0 + j7.82e−09 Ω | 0 | 1.31e−08 of \|ΔZ\|, asserted < 1e−3 |
>
> ΔR reproduces the step-2a W = 0.15 probe number to every printed digit, which
> is the check that the test measures what the probe measured. The **5% bound is
> sized from measurement, not chosen**: 1.58% at W = 0.15, 1.85% at W = 0.20,
> 0.268% of box motion between them. A σ-blind solver returns ΔZ = 0 and fails
> by 100%; the null control (same mesh solved with the slab tagged σ = 0 versus
> no material map at all — physically identical media) shows the tagging and the
> reaction extraction manufacture nothing on their own, so the ΔR the gate
> compares is field physics.
>
> **ΔX is deliberately not gated tightly, and the test says so in code.** It is
> not converged (−35.3% → −18.8% → −14.3% across W = 0.10/0.15/0.20, 5.57% still
> moving) and step 2a could not split the residual between PEC-wall imaging and
> the finite wire section (the filamentary reference spreads ΔX by 30% over
> h ± r_wire). Tightening it would need h/r_wire ≥ 16 or W ≥ 0.25 — a follow-up
> chunk, not a widened tolerance (MAG defect-5 note).
>
> **What stays open, deliberately.** This gates the *eddy-current* regime
> (10 MHz, σ = 100 S/m). Gelled saline at 127.74 MHz has loss tangent ≈ 1.26 and
> is **outside** it; the full-wave kernel (`α₀ = √(α²−k₀²)`, `α/α₀` weight) named
> in the step-2 entry is what would extend the claim there, and `SAR`/`MAT-4`
> figures at Larmor frequency are still unlicensed. See §2.1.

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
| `POST-3` | Replace vacuous consistency metrics | 🟡 | standard |

> **`POST-1` defect recorded 2026-07-31 (12:00 implementer run), not fixed.**
> `post/phantom_fields.py:88` does `np.asarray(field.eval(...), dtype=np.float64)`,
> which under the complex build silently discards the imaginary part of every
> sampled E/B value — `ComplexWarning` at that line in
> `20260731T170152Z_KI-1-retire-gate.log`. Every phantom field metric downstream
> is therefore taken on `Re(E)` at phase 0, not on the phasor magnitude, so it
> is phase-dependent and wrong by up to 100% for a field in quadrature. Fixing it
> is choosing the metric semantics (|phasor| vs. a time average), which is this
> chunk's job, not a cast change.

> The current flagship metric `e_to_b_mean_ratio` is by construction
> `≈ ω·|A|/|∇×A|` — it measures a mesh length scale, not physics, and cannot
> detect that the solver is wrong. After `TH-1`, replace it with checks that can
> fail for real reasons: Poynting flux balance, `∇·(σE)` residual, or reciprocity.

> **`POST-3` step 1 — done 2026-07-31, 09:00 implementer run.**
> `post/power_balance.py::poynting_power_balance` computes the complex-Poynting
> real-power identity `−∮½Re(E×H̄)·n̂dS = ½∫σ|E|²dV` with `H = ∇×E/(−jωμ₀μᵣ)`,
> and `tests/validation/test_poynting_balance.py` gates it on the `TH-6` lossy
> plane wave. Measured on that fixture (log
> `20260731T140404Z_POST-3-step1-gate.log`, 8 tests, 39 s at `-n 2`, standard
> tier): imbalance **8.19% at 12³ → 4.13% at 24³**, rate **0.987 in h** — O(h),
> as expected for the N1curl-degree-1 curl trace on the boundary, which is the
> weakest link (the volume side converges faster). Asserted: imbalance falls
> under refinement, fine-mesh imbalance < 5% (§10's MVP bar, the same one `TH-6`
> uses on this fixture — not fitted), and net real power flows *inward*
> (`+1.190e−04 W`; an outward sign would mean the `e^{+jωt}` convention is
> conjugated between Faraday's law and the flux integral). Negative control: the
> identical solve with the solver's σ zeroed but scored against σ = 0.7 S/m
> gives **95.2%** imbalance against the honest solve's 8.19% — the metric moves
> by 11.6× where `e_to_b_mean_ratio` does not move at all. The reactive part of
> the flux is reported (`6.40e−05 var`) and deliberately not asserted on: it
> carries `2ω(W_m − W_e)`, which no closed form here pins down.
> `e_to_b_mean_ratio` is now documented as deprecated-as-a-gate in
> `post/consistency.py` and relabelled "shape ratios, non-physical" in the
> quick-look report; its keys stay so `POST-2`'s consumers keep working.
> **`POST-3` step 2 — done 2026-07-31, 13:30 implementer run.** `sigma` now
> accepts either a scalar or a `fem.Function`, so the volume leg is
> `½∫σ(x)|E|²dV` over the DG0 `sigma_field` the solver already returns; the
> boundary flux leg is untouched. Gated on a *piecewise* solve —
> `test_poynting_balance.py::test_poynting_balance_holds_for_piecewise_sigma`
> puts σ = 0.1 S/m for x < L/2 and 1.4 S/m beyond it (the `MAT-2` pair, but as
> one two-material solve rather than two homogeneous ones; the interface lands
> on a mesh plane, so the DG0 σ is exactly the geometry) and drives the box with
> the σ_low plane wave, which is *not* the exact solution of the two-material
> problem and does not need to be: the identity has no free parameters.
> Measured (log `20260731T183707Z_POST-3-step2-gate-final.log`, 9 tests, 64.5 s at
> `-n 2`, standard tier): imbalance **8.93% at 16³ → 4.49% at 32³**, rate
> **0.9915 in h** — the same O(h) boundary-curl-trace leg as step 1, unchanged
> by the interface. The mesh moved, not the bound: at 12³→24³ this fixture gives
> 11.85% → 5.98% (rate 0.987, log
> `20260731T183338Z_POST-3-step2-refine-probe.log`), 5.98% being just over
> step 1's 5% MVP bar, and since the leg is O(h) the fine level went to 32³
> (predicted 4.5%, measured 4.49%) rather than the bar going up.
> Negative control on the field path: both slabs zeroed in the solver, scored
> against the honest σ(x), gives **99.19% against the honest 11.85%** at 12³ —
> 8.4×. That test asserts 5×, not step 1's 10×, because the blind imbalance
> saturates just under 100% (the two legs differ by at most the scale), so
> 1/0.1185 = 8.4× is the largest ratio this fixture can produce; the reason is
> recorded in the test's docstring. A no-solve regression test
> (`test_uniform_sigma_field_reproduces_the_scalar_path`) pins the scalar path:
> a uniform DG0 σ reproduces the float σ numbers to `rtol = 1e-12`.
>
> **Still open for `POST-3`:** μᵣ is still scalar — a piecewise μᵣ also enters
> `H` inside the boundary integral, so it waits for a magnetic phantom.
> Reciprocity waits for `GEO-8` + `PORT-1` step 1, which produce a two-source
> fixture for free. And the `POST-1` cast defect recorded above still means
> the *phantom-field* metrics are taken on `Re(E)`.
>
> **Step 3 plan — total-current divergence residual (2026-07-31, 18:00
> review).** The identity is on the **total** current:
> `∇·(ε_c E) = 0`, i.e. `∇·((σ + jωε₀εᵣ)E) = 0` — *not* `∇·(σE)` as the note
> above loosely named it, which is legitimately nonzero at a σ interface
> (surface charge accumulates), so the piecewise fixture would fail it for
> physics reasons. Two traps are the whole design:
> (i) **Vacuity.** For `v ∈ CG1` vanishing on the wall, `∇v` lies inside the
> degree-1 N1curl test space, so `∫ε_c E·∇v̄ dV` matches the source term
> *identically by Galerkin orthogonality* — a CG1-weak residual is enforced,
> not emergent, and can never fail: exactly the vacuous-metric class `POST-3`
> exists to remove. Test against `∇(CG2)` instead (not a subspace of the
> test space), normalised by a `‖ε_c E‖·‖∇v‖`-type scale.
> (ii) **Source divergence.** Taking div of Ampère gives
> `∇·(ε_c E) ∝ −∇·J_imp`, nonzero inside a volumetric source. The existing
> piecewise-σ fixture (`test_poynting_balance.py`) is boundary-driven — no
> volume source — so it is clean; on a coil drive the identity holds only
> outside the source support.
> Gate on the piecewise-σ fixture: residual falls under refinement with a
> recorded rate, and a negative control — score the residual with σ dropped
> from ε_c on the honest solve; the interface jump in `jωε₀εᵣE_n` alone must
> then surface. Complex build, standard tier (the step-2 suite is 64 s).
>
> **Step 3 attempt 1 — 🟡 incomplete, 2026-08-02 15:00 implementer run.** Metric
> written and measured; gate test not written, so nothing flips. Parked on
> `attempt/POST-3-step3-20260802T205600Z`
> (`post/current_divergence.py::current_divergence_residual` + probe), journalled
> in attempts.md 2026-08-02T20:00Z, log
> `20260802T201000Z_POST-3-step3-probe2.log`. The residual is measured as a
> **dual norm** — `sup |∫J_tot·∇v̄dV| / ‖∇v‖` over degree-p Lagrange vanishing on
> the wall, computed exactly via the Riesz representer (a Poisson solve, 0.5–1 s,
> `gamg`), normalised by `‖J_tot‖_{L²}` so it is dimensionless and ≤ 1.
> Measured on the piecewise-σ fixture: CG2 relative residual 9.316e-2 (8³) →
> 6.358e-2 (12³), **rate 0.942 in h**. Trap (i) confirmed hard: the CG1 residual
> is **6e-15**, 1.5e13× smaller — Galerkin orthogonality, exactly as predicted.
> **The negative control proposed above does not work and must be replaced:**
> dropping σ from `J_tot` moves the relative residual by 1.07% — 9.32e-2 →
> 9.96e-2 — and the absolute dual norm *falls*, because `‖J_tot‖` falls with it;
> at 64 MHz the two currents are comparable and the O(h) N1curl interpolation
> error dominates the interface jump. Use the CG1-vs-CG2 contrast as the control
> instead (same solve, 1e13× separation, mechanistic). Environment: `pc_type
> hypre` aborts this image (SIGABRT in `hypre_ParCSRCommHandleDestroy`, log
> `20260802T200303Z_POST-3-step3-probe.log`); use `gamg`.
>
> **Step 3 — ✅ done 2026-08-02, 16:30 implementer run.** Attempt 1's parked
> module landed unchanged and the gate is written:
> `tests/validation/test_current_divergence.py`, wired into `validation-complex`.
> Log of record `20260802T213238Z_POST-3-step3-gate-final.log` — 7 passed in
> 2.73 s at `-n 2` (standard tier, 4 s elapsed; the probe's 65 s was a cold JIT
> cache, the solves themselves are 0.27 s at 8³ and 0.89 s at 12³). Three
> assertions, all quantitative and all reproducing the probe to the printed
> digit: the CG2 relative residual falls 9.316430e-2 (8³) → 6.358255e-2 (12³),
> **rate 0.942 in h**, gated at `rate > 0.7` and `coarse < 0.15`; and the vacuity
> control gates the CG1 residual at `< 1e-10` (measured 6.136073e-15) with a
> CG2/CG1 separation gated at `> 1e6` (measured **1.5e13**). That contrast is the
> negative control — same solve, same field, same integral, only the test space
> changes — and it replaces the σ-dropped control the step-3 plan proposed, which
> attempt 1 measured at 1.07× and disproved. The gate prints every measured
> number to the log, so a later drift is separable from a regression.
>
> **What step 3 does *not* close.** The residual is scored on a boundary-driven
> fixture with no volume source; on a coil drive the identity holds only outside
> the source support (trap (ii)), and nothing here exercises that case yet. The
> `POST-3` chunk itself stays 🟡 for the reasons listed above — piecewise μᵣ and
> reciprocity are still open, and the `POST-1` cast defect still means the
> *phantom-field* metrics are taken on `Re(E)`.

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

> **Implementation plan (2026-07-31, 10:30 review).** Route the first real
> Z-matrix through the reaction integral `MAT-6` step 2b just validated to 1.58%
> against Dodd–Deeds, on a fixture and a closed form the repo already has;
> gap-voltage extraction becomes step 3 once the identity machinery is proven.
>
> **Step 1 — two-loop reaction Z-matrix probe (one run; product is
> measurements, nothing asserted — the `MAT-6` step-2a pattern).**
> Fixture: `MeshGenerator.two_torus_domain` — two coaxial tagged tori, graded
> sizing already supported (`wire_resolution`/`far_resolution`; the docstring's
> PMC-boundary warning says use `air_padding ≥ 2·major_radius`). Air everywhere
> (σ = 0, εᵣ = 1). Starting geometry a = 0.04 m, r_wire = 0.005 m, d = 0.04 m,
> f = 10 MHz — check k₀·(box diagonal) ≪ 1 numerically before trusting the
> quasistatic reference, and run `check_energy_continuity` even though box
> resonances sit far above. Drive torus 1 only: azimuthal impressed J with the
> regularised-sqrt pattern from `tests/validation/test_dodd_deeds_impedance.py`
> (**not** `ufl.max_value` — it does not compile in the complex build), passing
> `subdomain_ids=[torus-1 tag]`. Extract the column
> `Z_i1 = −(1/(I₁·Iᵢ))·∫E₁·Jᵢ dV` where `Jᵢ` is torus i's *shape* current and
> every `I` is the **meshed** loop current `∫J dV / (2πa)` — the nominal-current
> shortfall was a 17% error that looked like physics in `MAT-6` step 2a. Swap
> driven torus for the second column. Record in this entry: the 2×2 Z; the
> reciprocity residual `‖Z − Zᵀ‖/‖Z‖`; `Im Z₁₂` vs the closed form
> `ωM₁₂`, `M₁₂ = 2πa·A_φ(a, d)/I` from
> `utils/analytical.py::circular_loop_vector_potential` (Jackson 5.37) — also
> its filament sensitivity re-evaluated at a ± r_wire; box sensitivity at two
> paddings; wall-clock per solve at `-n 2`.
>
> **Step 2 — the gate (one run; tier from the step-1 cost numbers).**
> `tests/validation/test_port_reaction_impedance.py`: assert (i) reciprocity
> residual below a bound **stated from the step-1 measurement**, (ii) `Im Z₁₂`
> against `ωM₁₂` at a tolerance the measured box/filament sensitivity justifies,
> (iii) `|Re Z₁₂|/|Im Z₁₂|` small — the domain is lossless, so a real part is
> numerical, (iv) diagonal entries on sign and order only (the finite wire
> section spread 30% on `MAT-6`'s ΔX; do not gate self-reactance tightly and do
> not widen a bound to swallow it), and (v) if the budget allows a third solve,
> a physics control: doubling d must scale `|Z₁₂|` by the closed-form
> `M(2d)/M(d)`. Then convert through the existing
> `S = (Z − Z₀I)(Z + Z₀I)⁻¹` path with `Z₀ = 50 Ω` and assert S symmetric and
> passive (`‖S‖₂ ≤ 1`) — this is the first S-matrix in the repo derived from a
> solved field. Wire the file into the `validation-complex` CI job.
>
> **Step 3 — gap-voltage ports on the tagged birdcage (directional; a later
> review firms this up after steps 1–2 report).** The MRI-relevant form: excite
> across the tagged gaps of `birdcage_port_domain`, recover `V = −∫E·dl` as a
> volumetric average over the gap (not point sampling), cross-check gap-voltage
> Z against reaction Z on a fixture where both apply, resolve the two
> deliberately-red port tests (below), and thread `is_placeholder=False`
> through to `export_touchstone`. Known trap: the birdcage suite is over the
> compute budget (known-issues) — the gate must run on a reduced-rung fixture,
> not the full birdcage mesh.
>
> **Step 1 attempted 2026-07-31 (16:30 run) — 🚫 blocked on the fixture, not on
> the method.** The probe (parked on `attempt/PORT-1-step1-20260731T213516Z`,
> logs `20260731T213222Z_PORT-1-step1-costprobe.log`,
> `…213312Z_…-diagnostic.log`, `…213423Z_…-meshconformity.log`) runs end to end
> and returns a 2×2 Z whose **off-diagonals are exactly zero**:
> `Z₁₁ = +6.724232e-01j`, `Z₂₂ = +6.730717e-01j`, `Z₁₂ = Z₂₁ = 0` against a
> closed-form `ωM₁₂ = +1.241755e+00 Ω`. Two independent measurements say the
> cause is `MeshGenerator.two_torus_domain`, which **never fragments** the box
> against the tori (`io/mesh.py` — `occ.addBox` then `occ.synchronize()`, no
> `fragment`/`cut`):
>
> * volume arithmetic at padding 0.08, 31953 cells — total mesh volume
>   `1.315956e-02 m³`, tag-3 ("domain") volume `1.312500e-02 m³` = the **whole**
>   analytic box, ratio total/box = `1.002633`, and the excess `3.456e-05 m³` is
>   exactly the two meshed torus volumes. The box is meshed as a solid box and
>   the tori are meshed a *second* time as separate islands;
> * the solved field itself — driving torus 1, `∫|E|² dV` over tags (1, 2, 3) is
>   `2.0537e-04, 0, 0`. The field is confined to the driven island because there
>   is no shared node between the components, so no coupling path exists.
>
> Consequence for step 1: the reaction Z-matrix is correct arithmetic on a
> geometry that is not the intended one, and no reciprocity or `ωM₁₂` number
> from this fixture means anything. **Unblocking is a fixture change**, not a
> probe change: fragment the box against the two tori in `two_torus_domain`
> (`occ.fragment`, re-derive the physical groups from the fragment map, keep the
> `air_padding`/graded-sizing knobs) and re-run the parked probe unchanged. The
> meshed-current bookkeeping already works — meshed/exact torus volume is
> −12.5% at `h_wire = 0.005`, giving meshed currents 0.875149 / 0.875583 A, so
> the two tori discretise to within 0.05% of each other. Cost is not the
> problem: 31953 cells, 6.0 s to mesh, 2.8–3.0 s per solve at `-n 2`.
>
> The same non-conformity affects **every** existing user of this fixture
> (`test_helmholtz_v2.py`, `test_helmholtz_magnitude.py`, `test_two_torus.py`) —
> recorded in `docs/testing/known-issues.md`, not diagnosed here, and it needs a
> decision before the fix lands.
>
> Session traps that cost runs this week, all applicable here: stale FFCx lock
> after a killed run (`rm -rf ~/.cache/fenics` in the container); `-k`
> expressions splitting inside the single-quoted container command; numbers
> logs need `pytest -s` or the prints are captured.

> **Step 1 re-run 2026-08-02 (13:30 run) after `GEO-8` — ✅ done; the numbers
> below size step 2.** The probe landed unchanged at
> `scripts/probes/port1_step1_probe.py`; the attempt branch is deleted, its
> content fully captured here. The fixture is conforming: total mesh volume /
> analytic box = `1.000000` at both paddings, gmsh reports "3 volumes with 1
> connected component", and the meshed/exact torus volume deficit improved
> −12.5% → **−3.10%** (meshed current 0.969009 A, the two tori identical to
> all printed digits). Off-diagonals are no longer zero.
>
> Measurements (all at `-n 2`, f = 10 MHz, a = 0.04, r_wire = 0.005, d = 0.04):
>
> | padding | h_far | cells | `Im Z₁₂` (Ω) | vs `ωM₁₂` | recip. `‖Z−Zᵀ‖/‖Z‖` | `Im Z₁₁`, `Im Z₂₂` (Ω) |
> |---|---|---|---|---|---|---|
> | 0.08 | 0.02 | 167906 | +1.126596 | −9.27% | 7.86e-14 | −40.693, −40.422 |
> | 0.08 | 0.03 | 119738 | +1.125614 | −9.35% | 3.06e-13 | −41.086, −40.924 |
> | 0.12 | 0.03 | 154493 | +1.184134 | −4.64% | 4.31e-13 | −40.969, −40.776 |
>
> Closed form `ωM₁₂ = +1.241755e+00 Ω` (`M₁₂ = 1.976314e-08 H`);
> `M(2d)/M(d) = 0.287120` for the step-2 physics control.
>
> Reading of those columns, which is what step 2 needs:
> * **Reciprocity is at machine precision** — 1e-13, not 1e-3. The step-2 bound
>   is not sensitivity-limited; a bound of `1e-9` is still four orders of slack
>   and would catch any real symmetry break.
> * **`Re Z₁₂` is exactly `0.0`**, not small — in the lossless case the operator
>   is real-symmetric, so the real part is structurally absent rather than
>   numerically cancelled. Step 2 item (iii) should assert this as an equality-ish
>   bound and note it is structural, not a convergence result.
> * **The `ωM₁₂` gap is the box, not the mesh.** Coarsening h_far 0.02 → 0.03 at
>   fixed padding moves `Im Z₁₂` by 0.09% (−9.27% → −9.35%); enlarging the box
>   0.08 → 0.12 moves it **5.20%** and monotonically *toward* the closed form.
>   The PEC wall images the loops back into the domain, exactly as the fixture
>   docstring's `air_padding ≥ 2·major_radius` warning predicts (0.08 = 2a is the
>   minimum, and is still 9% off). A step-2 tolerance on `ωM₁₂` of **10% at
>   padding 0.08** is justified by measurement; tightening it means paying for a
>   bigger box, not a finer mesh.
> * **The filamentary reference is itself soft at this geometry**: re-evaluating
>   `M₁₂` over ρ, z within ± r_wire spans `[1.3768e-08, 2.6917e-08] H` —
>   **66.5% of nominal**. At d = a the loops are close enough that the finite wire
>   section matters more than the solve error does. Do not tighten past 10% on the
>   strength of the closed form; it does not support it.
> * **The diagonal is wrong and step 2 must not gate it.** `Im Z₁₁ ≈ −40.9 Ω`:
>   negative where a lossless loop must be inductive (`+ωL`), and ~6× too large
>   against a Grover estimate `ωL ≈ ω·μ₀a(ln(8a/r_wire) − 2) ≈ 6.8 Ω`. The
>   off-diagonal is right in sign and within 5–9% of its closed form while the
>   diagonal is wrong in sign — so this is the self-term (the source's own
>   singular field inside the driven wire entering `∫E·J` over the source
>   region), not a global convention error. **Open question for step 2's author,
>   and a reason to keep item (iv) to order-of-magnitude only or drop the
>   diagonal assertion entirely.** Not diagnosed here.
> * Energy continuity is quiet, as intended: over f ∈ [7, 14] MHz,
>   `|d ln W/d ln f|max = 2.0000` against threshold 50, `triggered = False` —
>   W ∝ f⁻² exactly, i.e. cleanly quasistatic, no box resonance anywhere near.
>   `k₀·diag = 0.086` (0.08) and `0.115` (0.12).
>
> **Cost, and the step-2 tier — the one hard constraint this run found.**
> Conforming meshing is 5.25× the old cell count at the same knobs (31953 →
> 167906 at padding 0.08 / h_far 0.02), and solve cost went 2.8–3.0 s → 21–37 s
> per solve. **Padding 0.12 at h_far 0.02 (237926 cells) does not fit the
> standard tier**: it was killed at 180 s inside the MUMPS factorisation
> (`20260802T183423Z_PORT-1-step1-solve012.log`, status 124) and the sweep was
> re-run coarser per §5.1 rather than given more time. Step 2 should gate at
> **padding 0.08 / h_far 0.03, standard tier** — 119738 cells, mesh 21 s + two
> solves 21 s and 31 s = 152 s for the full two-padding sweep, so a single-box
> two-solve gate lands near 75 s. A third solve for the `M(2d)/M(d)` control
> needs its own mesh (different d ⇒ different box) and will not fit alongside;
> either take the heavy tier or split it into its own test.
>
> Logs: `20260802T183045Z_PORT-1-step1-costprobe.log` (mesh-only, conformity),
> `…183226Z_…-solve008.log`, `…183423Z_…-solve012.log` (the 180 s kill),
> `…183747Z_…-boxsens.log` (the sensitivity pair), `…184031Z_…-energy.log`.

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

1. ~~**`MAT-6` step 2**~~ — **done 2026-07-31** (steps 2a + 2b): ΔR matches
   Dodd–Deeds to 1.58%, so coil loading is licensed *in the eddy-current
   regime*. The saline/Larmor case needs the full-wave kernel; SAR (`MAT-4`)
   is still ungated.
2. ~~**`TH-7`**~~ — **done 2026-07-31** (γ to 0.006%). **`TH-8`** is the last of
   the cheap closed-form gates on the frequency-domain solver; one run in the
   `TH-6` mould.
3. **`POST-3`** — 🟡: steps 1–2 landed 2026-07-31 (Poynting real-power balance,
   4.13% on the `TH-6` fixture with a σ-blind control at 95.2%; then σ(x) as a
   DG0 field, 4.49% on a two-slab σ = 0.1 | 1.4 S/m solve, control at 99.2%);
   step 3 landed 2026-08-02 (total-current divergence residual, 9.32e-2 → 6.36e-2
   at rate 0.942 in h, with a CG1-vs-CG2 vacuity control separating by 1.5e13).
   What remains is piecewise μᵣ and reciprocity.
4. **`PORT-1`** — real port excitation from the solved field. Resolves the two
   deliberately-red port tests as a side effect. §7-grade implementation plan
   written 2026-07-31 (10:30 review): reaction Z-matrix on the two-torus
   fixture first (steps 1–2), gap-voltage birdcage ports as step 3 after those
   report. **Step 1 attempted at the 16:30 run and blocked on the fixture:**
   `two_torus_domain` is three disconnected meshes (known-issues), so `GEO-8`
   (new, 18:00 review) must land first — the critical path is now
   `GEO-8` → step 1 → step 2, On-deck items 1, 2 and 5.
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

Last reviewed 2026-07-31, 18:00 daily review. Tree clean; no `recovered/*`
branches. One `attempt/*` branch, `attempt/PORT-1-step1-20260731T213516Z` —
**kept deliberately**: the probe script on it re-runs unchanged once `GEO-8`
lands, so its content is not yet captured by the plan; item 2 deletes it when
it lands the probe. All four runs since 10:30 resolved cleanly: known-issues
entry 1 retired, `POST-3` step 2 and `TH-8` done, `PORT-1` step 1 blocked and
parked per protocol. Audit: the one status that flipped ✅ since the last
review (`TH-8`) is §4-compliant — log of record
`20260731T200457Z_TH-8-gate-final.log`, 6 passed in 16.24 s at `-n 2`,
closed-form interior field to 2.443% with fitted rate 1.9675 and an ε-blind
negative control; the entry-1 retirement is likewise log-backed
(`20260731T170152Z`, `20260731T170140Z`); nothing demoted. Queue rebuilt:
items 1–3 of the previous queue are done (struck text preserved in git at
`424faed`), item 4 is blocked on the fixture defect `GEO-8` now owns, and the
open question it raised about the Helmholtz users is answered by code reading
in the `GEO-8` entry (numerically unverified; `GEO-8` step 1 records the
numbers). New plans written this review: `GEO-8`, `POST-3` step 3, `MAT-4`
step 1 — items 3 and 4 are deliberately independent of the `PORT-1` chain.

1. ~~**`GEO-8` — make `two_torus_domain` conforming**~~ ✅ **done** 2026-08-01
   (19:30 run) — mesh-volume ratio 1.000000000, air/driven `∫|E|²` 1.4118
   where it was exactly 0, Helmholtz centre error 1.731% → 0.728%. Item 2 is
   unblocked. Original text: **make `two_torus_domain` conforming**, independent; unblocks
   the `PORT-1` chain. Execute the §7 `GEO-8` plan: record what the three
   existing users measure today, fragment the box against both tori
   re-deriving the physical groups from the fragment map, land the conformity
   gate (mesh-volume arithmetic + the driven-torus field-leakage check), then
   re-run the users and record before/after. Standard tier; the mesh is 32k
   cells / 6 s, the magnetostatic users are the only meaningful cost.
2. ~~**`PORT-1` step 1 — two-loop reaction Z-matrix probe**~~ ✅ **done**
   2026-08-02 (13:30 run) — reciprocity residual 7.9e-14, `Im Z₁₂` +1.1266 Ω
   vs closed-form `ωM₁₂` +1.2418 Ω (−9.27%), box sensitivity 5.20% and
   monotone toward the closed form; probe landed, attempt branch deleted. Two
   findings step 2 must absorb, both in the §7 entry: the diagonal is wrong in
   sign (`Im Z₁₁ ≈ −40.9 Ω` where `+ωL ≈ 6.8 Ω` is expected — do not gate it),
   and conforming meshing made solves 10× dearer, so the gate must sit at
   padding 0.08 / h_far 0.03 (padding 0.12 at h_far 0.02 blew the standard
   tier). Original text: **two-loop reaction Z-matrix probe.** **Depends on
   item 1 having landed; if it did not, skip to item 3 and journal.** Re-apply
   the parked probe from `attempt/PORT-1-step1-20260731T213516Z`
   (`scripts/probes/port1_step1_probe.py`) and run it unchanged per the §7
   `PORT-1` step-1 plan; product is measurements, assert nothing. Cost is
   known: 2.8–3.0 s per solve at `-n 2`, the whole sweep ~2 min. Delete the
   attempt branch in the same commit — its content is then fully landed.
3. ~~**`POST-3` step 3 — total-current divergence residual**~~ ✅ **done**
   2026-08-02 (16:30 run) — attempt 1's parked module landed unchanged and the
   gate is written: `tests/validation/test_current_divergence.py`, in
   `validation-complex`, log `20260802T213238Z_POST-3-step3-gate-final.log`,
   7 passed in 2.73 s at `-n 2`. Gated on rate 0.942 in h (bound 0.7),
   magnitude 9.32e-2 (bound 0.15), and the CG1-vs-CG2 vacuity control at 1.5e13
   separation (bound 1e6). Attempt branch deleted — content fully landed.
   `POST-3` stays 🟡: piecewise μᵣ and reciprocity remain. Original text:
   **total-current divergence residual**, independent.
   🟡 **attempt 1 incomplete** (2026-08-02, 15:00 run) — metric written and
   measured (CG2 relative residual 9.32e-2 → 6.36e-2, rate 0.942 in h; CG1
   residual 6e-15, confirming trap (i)), gate test not written, parked on
   `attempt/POST-3-step3-20260802T205600Z`. The next attempt lands that branch
   and writes the gate; **the σ-dropped negative control in the plan below is
   dead** (1.07× separation, measured) — use the CG1-vs-CG2 contrast instead.
   See the §7 entry and attempts.md 2026-08-02T20:00Z.
   Execute the §7 `POST-3` step-3 plan on the existing piecewise-σ fixture.
   The two traps (CG1 vacuity by Galerkin orthogonality — test against
   `∇(CG2)`; and the identity is on total current, not `σE` alone) are the
   whole design and are written in the entry. Complex build, standard tier.
4. **`MAT-4` step 1 — the lossy-sphere SAR gate**, independent. Execute the
   §7 `MAT-4` plan: extend the `TH-8` sphere fixture to σ > 0, gate interior
   SAR against `σ|3E₀/(ε_c+2)|²/(2ρ)` with complex ε_c — the first assertion
   on the imaginary axis of ε_c (`TH-8` measured `|Im E_z|` exactly 0 by
   construction). Do not route fields through `post/phantom_fields.py` (the
   `POST-1` cast defect). Complex build, standard tier.
5. **`PORT-1` step 2 — the reciprocity gate** (spare). **Depends on item 2
   having produced its numbers; if it did not, stop and journal — do not
   improvise the probe and the gate in one run.** Turn the step-1 numbers into
   `tests/validation/test_port_reaction_impedance.py` per the §7 plan:
   reciprocity residual and `ωM₁₂` bounds stated from the step-1 measurement,
   lossless `Re/Im` check, diagonals on sign and order only, S-conversion
   symmetry + passivity, wired into `validation-complex`.

If the queue drains: stop and journal — `PORT-1` step 3 (gap-voltage birdcage
ports) is next on the critical path but its §7 plan is deliberately directional
until steps 1–2 report their numbers, and an implementer run should not
improvise it.

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
  2.68, `TH-6`. The loaded-**coil** claim landed 2026-07-31: the FEM ΔR of a
  loop over a conductive half-space matches Dodd–Deeds to 1.58%, `MAT-6` step
  2b — in the eddy-current regime, not yet at saline/Larmor.)*

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
