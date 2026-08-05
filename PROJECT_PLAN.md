# PROJECT_PLAN.md — FEM Electromagnetics Solver for MRI Coil Simulation

**Single source of truth for scope, status, and sequencing.** Resolved defects and
the reasoning behind past decisions live in [`docs/project-history.md`](docs/project-history.md);
nothing there is a task.

---

## 1. Mission *(rescoped 2026-08-04)*

A FEniCSX/DolfinX finite element toolkit that reproduces, for the slice of
electromagnetics relevant to **MRI RF safety**, the workflow an engineer runs
in Ansys Electronics Desktop — HFSS plus the circuit solver first, with the
Pennes bioheat equation for thermal simulation as the long-term extension.
The canonical workflow the tool must support end to end:

1. **Construct** a birdcage coil + gelled saline phantom simulation from
   parametric geometry — often with an implant inside the phantom.
2. **Tune** the birdcage at 64 MHz (1.5 T) and 128 MHz (3 T): EM solve plus
   circuit co-simulation to pick capacitor values, verify the mode spectrum,
   and match the ports.
3. **Drive** the tuned coil and extract the safety quantities: B1+ maps,
   SAR (whole-phantom and local, including near-implant hot spots), and port
   S-parameters.
4. Long term: **couple to thermal** via the Pennes bioheat equation.

Commercial solvers are expensive and black-box; open-source alternatives lack
the MRI-specific workflow. The scope is deliberately **the MRI-safety slice of
HFSS, not HFSS**: general-purpose 3-D full-wave parity is out of reach for
this project and is not the goal. Parity claims are made per-workflow ("tunes
a shielded 8-rung birdcage at 128 MHz to within X of AED"), never
per-product.

**Cross-validation against Ansys is part of the method.** `examples/` carries
runnable examples with XDMF outputs for visual review in ParaView, and
periodically a benchmark case specified precisely enough for the human
operator to replicate in Ansys Electronics Desktop; the returned numbers
become gates (§5.4).

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

*(2026-08-02, `PORT-1` step 2: there is now **one** S-matrix in the repo that is
not heuristic — `tests/validation/test_port_reaction_impedance.py` converts a
reaction Z-matrix from a solved two-loop field through
`S = (Z − Z₀I)(Z + Z₀I)⁻¹` and gates it symmetric, passive and unitary. It is a
two-loop air fixture, not a coil, and `ports/excitation.py` is untouched: every
S-parameter the **package** produces is still heuristic.)*

*(2026-08-03, `PORT-1` step 3a: the **conversion** now lives in `src/` —
`ports.sparameters_from_impedance()`, pure numpy, gated bit-identical to the test
path on that solved field, with `PORT-5`'s sanity metrics reporting
`passivity_max_sigma = 1.000000000000` on a real matrix for the first time. This
does not move the sentence above: `run_n_port_sparameter_sweep` still gets its
port voltages from `excitation.py`, so **every S-parameter the package produces
end to end is still heuristic**. What changed is that a caller holding an honest
Z now has an honest conversion to call.)*

*(2026-08-04, `PORT-1` step 2f: the **port diagonal** of that Z is now gated
too, and honest — `TimeHarmonicSolver.solve()` drives with the
CG1-weakly-solenoidal part of the prescribed current by default
(`project_source=True`), which moves `Im Z₁₁` from `−41.09 Ω` on a lossless
loop to `+7.437243 Ω`, 1.0908× Grover's `ωL`. So the two-loop fixture's Z is
now gated in every entry rather than three of four. This still does not move
the sentence above — `excitation.py` is untouched and every S-parameter the
**package** produces end to end is still heuristic — and it is still a
two-loop air fixture, not a coil.)*

*(2026-08-04, `MAT-6` step 3 — **the coil-loading number now holds on the
production default path.** The caveat that stood here since 2f, that `MAT-6`'s
ΔR-to-1.58% was an unprojected-drive measurement, is retired by measurement,
not by argument: the same W = 0.15 fixture solved with `project_source` at its
default gives **ΔR = +3.2770406e-01 Ω, 1.5834% off Dodd–Deeds**, against the
pinned path's +3.276882e-01 Ω / 1.58% — the two drives agree on the gated
number to 5e-5 relative, because the projection barely moves a closed loop
current (`I′/I = 0.999974`). The original test keeps its `project_source=False`
pins as the landed number's provenance; the default path is gated separately in
`tests/validation/test_dodd_deeds_projected_drive.py`
(`20260804T213600Z_MAT-6-step3-gate-final.log`, 8 passed, 65 s). **Still
unchanged:** the licence is the eddy-current regime only — 10 MHz, σ = 100 S/m —
and saline at the Larmor frequency remains an extrapolation, not a result.
`ΔX` moved from ratio 0.8123 to 0.9200 under the projection, reported and not
gated: this fixture is not converged in `ΔX` and cannot say whether that is an
improvement.)*

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

**A measurement-only step is `🧪`, never `✅`** *(clarified 2026-08-02, 18:00
review, after an audit found two probe steps carrying `✅`)*. Several chunks are
split into a probe step whose stated product is "measurements, assert nothing"
and a gate step that turns those measurements into bounds. The probe step lands
real code and real logs, but §4.3 asks for an executed quantitative *assertion*,
and a script that only prints has none — so the probe step is `🧪` until its
gate lands, however good its numbers are. This is a clarification of §4, not an
exception to it: the fix is to write the gate, never to widen §4. Demoted on
this ground 2026-08-02: `PORT-1` step 1, `MAT-6` step 2a. (`PORT-1` step 1 was
restored to ✅ the same day when its gate, step 2, landed — which is exactly
the intended route back.)

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
- **Do not append duplicate status blocks.** Status lives in §7 tables. (The
  legacy human-gated queue `docs/testing/pending-tests.md` and its
  `AWAITING-HUMAN-TEST` status were removed 2026-08-04 — verification is
  agent-executed per §4; the old queue survives in git history.)

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

### 5.4 Examples and Ansys cross-validation

- **`examples/` is a maintained product surface, not a scratch area.** Each
  phase keeps at least one clean, runnable example demonstrating its current
  capability, executed via `./run_examples.sh` and producing combined-XDMF
  output that opens in ParaView — this is how the human operator reviews
  progress independently of the test suite. When a chunk changes what an
  example demonstrates, the same commit updates the example. A broken example
  is a defect (known-issues discipline applies).
- **Ansys benchmark cases** live in `examples/ansys_benchmarks/<case>/`, each
  containing: `SPEC.md`, precise enough to replicate in Ansys Electronics
  Desktop with no judgement calls (geometry with dimensions, materials,
  boundary conditions, port definitions, frequencies, mesh guidance, and
  exactly which quantities to export); the runnable script; our results
  (metrics JSON + XDMF); and `COMPARISON.md` with our numbers filled in and
  blank columns for the AED numbers.
- **Cadence is the weekly planning review's call**
  (docs/automation/weekly-review.md) — roughly one case per phase milestone,
  and only on gated capability. A benchmark on ungated physics wastes a
  licence-hour measuring noise.
- **Returned AED numbers are adjudicated by the next weekly review**: recorded
  in the case's `COMPARISON.md`, promoted into §7 gates where they agree, and
  opened as known-issues/chunks where they disagree — a disagreement with the
  commercial solver is a finding to diagnose, never to explain away.

---

## 6. Phase map

| Phase | Goal | Gating chunks | State |
|---|---|---|---|
| 0 | Infrastructure, packaging, CI, meshing | `OPS-1`, `OPS-2` | Done |
| 1 | Magnetostatics + analytic validation | `MAG-1`…`MAG-6` | **Complete and trustworthy** |
| 2 | Time-harmonic Maxwell, complex materials, ABC/PML | `TH-1`…`TH-9` | In progress — every analytic gate closed (`TH-1`/`TH-6`/`TH-7`/`TH-8`/`TH-9` ✅); `TH-2`/`TH-3` API hardening ⚠️ |
| 3 | Material models, phantoms, SAR | `MAT-1`…`MAT-6` | `MAT-2` ✅; `MAT-6` ✅ (ΔR to 1.58% pinned / 1.5834% on the production projected drive, step 3; eddy-current regime); SAR still ungated |
| 4 | Coil modeling, lumped elements, ports, S-params | `PORT-1`…`PORT-8` | Placeholder-backed |
| 5 | Full MRI system: loaded birdcage, B1+, SAR maps | `WF-5`…`WF-8` | Blocked on Phases 2–4 |
| 6 | Birdcage tuning at 64/128 MHz: mode spectrum, lumped capacitors, circuit co-simulation (the HFSS + Circuit split) | subgoals owned by the weekly review (§10) | Not started |
| 7 | Implants: parametric implant geometry in the phantom, local SAR / near-implant hot spots | subgoals owned by the weekly review (§10) | Not started |
| 8 | Thermal: Pennes bioheat driven by SAR | subgoals owned by the weekly review (§10) | Not started |
| 9 | Advanced: MPI scaling, AMR, sweeps, optimization | — | Deferred |

Phases 6–8 are the 2026-08-04 scope adjustment (§1). Their phase goals and
subgoals live in §10's long-horizon roadmap and are **owned by the weekly
planning review**; the daily review breaks current-phase subgoals into
implementer-sized items and does not restructure phases.

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
`A1`/`B2`/`C3` IDs in commit messages and old logs map here via §8.
These tables are the authoritative *status*. Closed chunks and steps keep
compressed result blocks here (gated numbers, dates, log IDs, live
carry-forwards); their full plans, execution journals and audit narratives are
archived verbatim in `docs/planning/plan-archive.md` — grep there before
re-deriving a closed step's diagnosis. (The older per-chunk log,
`docs/testing/pending-tests.md`, was removed 2026-08-04; see git history.)

### OPS — Infrastructure & testing operations

| ID | Title | Status | Tier |
|---|---|---|---|
| `OPS-1` | Executable verification environment (Docker) | ✅ | smoke |
| `OPS-2` | CI runs the real test suite, not just `tests/unit` | ✅ | standard |
| `OPS-3` | Deterministic test tolerance policy | ✅ | smoke |
| `OPS-4` | Lightweight smoke matrix | ✅ | smoke |
| `OPS-5` | Testing status dashboard | ✅ | smoke |
| `OPS-6` | Expanded run-and-log metadata | ✅ | smoke |
| `OPS-7` | Guided pending-test queue helper *(retired 2026-08-04 — queue tooling removed; verification is agent-executed per §4)* | 🧪 | smoke |
| `OPS-8` | v1 milestone acceptance checklist | 🧪 | smoke |
| `OPS-9` | Prune duplicate/stale entries from `pending-tests.md` | ✅ | smoke |
| `OPS-10` | Complex-mode CI job for the frequency-domain gates | ✅ | smoke |
| `OPS-11` | Put `tests/mesh` in CI — the directory no job runs | ✅ | smoke |

**`OPS-11` — `tests/mesh` in CI** ✅ *(created 2026-08-02, closed 2026-08-03,
12:00 run; full narrative archived in `docs/planning/plan-archive.md`)*
> The directory no job ran — which is why known-issues 7 (mesh generators
> failing outright) sat undiscovered. The `validation` job's
> `Mesh generation suite` step now runs the **whole directory** with exactly
> one exclusion left: the known-issues-5 `--deselect` (off-centre sizing
> arithmetic). **20 passed 1 skipped 1 deselected in 42.15 s, exit 0**
> (`20260803T200504Z_GEO-9-step2b-gate.log`; the birdcage `--ignore` was
> removed by `GEO-9` step 2b as required). The "those and only those" control
> was executed, not quoted (`20260803T170132Z_OPS-11-fullsweep.log`); the
> §4.3 assertion is the volume-partition identities (`1e-9`) executing in CI
> across three files. The remaining exclusion is annotated at its
> known-issues entry and must be removed by the commit that fixes it.

**`OPS-10` — complex-mode CI job** ✅ *(2026-07-31; full narrative archived)*
> Before this, CI executed **no** time-harmonic solve at all (`@complex_only`
> skips). The `validation-complex` job sources
> `/usr/local/bin/dolfinx-complex-mode` and runs `tests/environment` first
> (so an environment regression is not blamed on the formulation), then the
> frequency-domain gates, under `FEM_EM_REQUIRE_COMPLEX=1` — which converts
> skips into failures so the job cannot pass by skipping. Verified with the
> CI-fidelity invocation (no `PYTHONPATH` override, `pip install -e`) plus a
> real-mode negative control that fails rather than skips.
>
> **This job has never executed on a GitHub runner.** Local `main` is well
> ahead of `origin/main` — nothing pushed since 2026-07-27 — so every "in CI"
> claim in this file is verified by local reproduction of the CI invocation
> only. The runner-environment caveat settles on the first push, which is a
> human action, not a scheduled-session one.
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
| `MAG-16` | Complex-build-safe magnetostatic energy | 🧪 | smoke | owns known-issues 8 |

**`MAG-16` — complex-build-safe magnetostatic energy** 🧪 *(chunk written
2026-08-05, 10:30 review; owns known-issues 8)*
> `MagnetostaticSolver.compute_magnetic_energy` (`core/solvers.py:661`) casts
> the assembled energy with an unconditional `float(...)`, which raises
> `TypeError` in the complex build — 2 of the 4 standing regression failures
> in every complex-mode sweep since `POST-3` step 5's regression first ran
> `tests/solver/test_energy_and_point_evaluation.py` under
> `dolfinx-complex-mode` (reproduced pre-existing at `aabb0a7`,
> `20260805T003945Z_POST-3-step5-preexisting.log`). The energy is real by
> construction; the presumed fix is a real-part reduction with a guard, but
> the value has never been compared across builds, so the fix must pin it.
> Done when: both energy tests pass at `-n 2` under `dolfinx-complex-mode`
> with their identity assertions unchanged (the discrete work-energy identity
> is the quantitative anchor — already a conservation identity); the
> complex-build energy matches a real-build value captured in the same slot
> *before* the fix commit, at a stated rtol; the discarded imaginary part is
> asserted small relative to the real part at a probe-measured band; and
> known-issues 8 is retired in the fixing commit. Negative control on record:
> the `TypeError` itself, plus the imag/real ratio a wrong reduction (e.g.
> `abs()` swallowing a genuinely large imaginary part) would move. Cost:
> smoke-tier compute in a standard slot — the 4-test file measured 4.46 s at
> `-n 2`; roughly one real-build run, one complex-build run, one
> `tests/solver` regression, `timeout 180` each. Traps: grep every `float(`
> cast on the energy path in `core/solvers.py`, not just line 661;
> `tests/environment` first in the complex command; do not touch the
> time-harmonic power paths (`POST-3` owns those). Does not close:
> known-issues 2; no field-accuracy claim. Negative result: a genuinely
> non-small imaginary part is a formulation finding — report the number,
> leave the cast unpatched, annotate known-issues 8, stop.

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
| `GEO-9` | **`coil_phantom_domain` / birdcage meshes do not generate** | ✅ 2026-08-03 — step 1 (coil+phantom gated), step 2a (finalize + `bcast`: 180 s hang → 13 s), step 2b (`occ.fragment` rewrite; both identities 1.000000000000, whole `tests/mesh` green in CI). Retires known-issues 7 | standard |

> `GEO-4`'s substance is discharged for the two-torus fixture (`air_padding` +
> graded sizing), but it stays 🧪 until its own test executes. **Every other
> fixture in `io/mesh.py` still uses a single global `setSize` and tight padding,
> including coil+phantom** — expect the same boundary-mirror error that cost 20%
> on Helmholtz, and expect graded sizing to be equally necessary.

**`GEO-8` — make `two_torus_domain` a conforming mesh** ✅ *(2026-08-01,
19:30 run; full narrative archived in `docs/planning/plan-archive.md`)*
> The fixture never fragmented, so gmsh meshed three disconnected components —
> the box solid through the tori, a driven torus's field confined to its
> island, `PORT-1`'s `Z₁₂ ≡ 0`. Fixed with
> `occ.fragment([(3, box)], [(3, torus_1), (3, torus_2)])` plus
> centroid/mass re-derivation of the physical groups (**fragment renumbers —
> never trust its returned tag order**; the `loop_over_half_space_domain`
> discipline every later fixture inherits). Gate
> `tests/mesh/test_two_torus_conforming.py`, both CI jobs; logs
> `20260801T003039Z…003600Z_GEO-8-*.log`. Mesh volume / analytic box:
> 1.002633 → **1.000000000**; Helmholtz centre-field error 1.731% → **0.728%**
> with no bound touched. Measurement worth keeping: at uniform
> `resolution=0.01` a meshed torus retains only 0.598 of its analytic volume —
> **the wire needs `wire_resolution ≲ 0.4·minor_radius`** before any
> volume-based conformity statement means anything. Unblocked `PORT-1`
> steps 1–2.

**`GEO-9` — `coil_phantom_domain` and the birdcage do not generate a mesh** ✅
*(created 2026-08-02, 18:00 review, from known-issues 7; steps 1, 2a, 2b all ✅
2026-08-03 — chunk closed, known-issues 7 retired; full diagnosis narrative
archived in `docs/planning/plan-archive.md`)*
> **What it turned out to be — two independent defects, neither the one the
> known-issues note guessed.** `coil_phantom_domain` was innocent: it generates
> fine in a fresh process (step 1 gated its volume-partition identities at
> `1.000000000000`/`1e-9`, phantom 0.9835 of `πr²h`). The whole of
> known-issues 7 was the **birdcage** raising without reaching
> `gmsh.finalize()` and poisoning every later mesh in the process — which also
> *hung* it: rank 0 raised inside its rank-0 block and skipped the collective
> `model_to_mesh`, so rank 1 blocked forever (harness exit 124 at the ceiling
> while pytest reported in 3 s).
> * **Step 2a** ✅ *(07:30 run)*: rank-0 body moved to
>   `_build_birdcage_port_model`, caller finalizes under
>   `gmsh.isInitialized()` and `comm.bcast`s the failure so every rank raises
>   before `model_to_mesh`. 180 s hang → **13 s prompt failure**; isolation
>   gate `tests/mesh/test_birdcage_finalize_isolation.py` exit 0
>   (`20260803T123657Z_GEO-9-step2a-gate.log`). Carry-forward: the gate's
>   no-hang `allreduce` assertion degenerates at `-n 1` — **never move it to a
>   single-rank job**.
> * **Step 2b** ✅ *(15:00 run)*: one `occ.fragment` of the air box against
>   all tools (rings, legs, phantom, 4 port boxes) replacing the
>   `occ.cut(..., removeTool=False)`, every group re-derived from the fragment
>   out-map (26 volumes; leg∩ring pieces → conductor; port-box-only pieces →
>   `100+i` — they previously carried **no** 3-D group). Meshed first try at
>   default parameters. `V_mesh/V_box = 1.000000000000`,
>   `Σ(tagged)/V_mesh = 1.000000000000` (1e-9), all four port boxes **exact**,
>   conductor 0.7091 banded (junction double-count in the analytic sum + the
>   global `setSize` — the latter is exactly what `GEO-4`'s open half
>   measures), phantom 0.9734. The rank-local
>   `set(np.unique(cell_tags.values))` bug **fired** with the geometry fixed
>   (opposite missing tags on the two ranks) and was switched to
>   `global_cell_tag_set()`, assertion content unchanged. The known-issues
>   "~10 minutes" figure is retired by measurement: the mesh is **8.95 s** —
>   the old figure was the pre-2a hang. Whole `tests/mesh` green in CI at
>   42.15 s (`20260803T200504Z_GEO-9-step2b-gate.log`); the `--ignore` came
>   out of `ci.yml` in the same commit. The 2a isolation gate was kept with a
>   deliberately self-intersecting fixture so the isolation property stays
>   tested.
>
> **Does not close:** `PORT-1` step 3b (gap excitation), known-issues 4, or
> `GEO-4` (air-box generalisation — the birdcage still uses one global
> `setSize`, which is exactly what the 0.7091 measures).

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
2026-07-30/31; full step journal archived in `docs/planning/plan-archive.md`)*
> Replaced the `E = −ωA` proxy with an actual frequency-domain solve:
>
> ```
> ∇×(μᵣ⁻¹∇×E) − k₀²ε_c E = −jωμ₀J,    ε_c = εᵣ − j·σ/(ωε₀)
> ```
>
> **Formulation notes (live constraints, not history):**
> - **The sign convention is part of the spec.** The equation assumes `e^{+jωt}`,
>   matching `ε_c = εᵣ − j·σ/(ωε₀)`. Every analytic gate must be derived in the
>   same convention or validation fails spuriously with conjugated fields.
>   `ufl.inner` conjugates its second argument in complex mode — `ufl.dot` for
>   the load silently flips the convention.
> - **Do not port the gauge penalty.** At ω > 0 the operator acts as `−k₀²ε_c`
>   on the gradient subspace — nonzero everywhere, dissipative wherever σ > 0.
>   The `MAG-10` disease is statics-only; a penalty here would *add* error.
> - **The silent-failure mode is near-resonance ill-conditioning.** With PEC
>   boundaries and lossless air the matrix is exactly singular at cavity
>   eigenfrequencies — and an MRI coil is deliberately operated near resonance.
>   MUMPS returns clean exit codes on near-singular systems. The `core/resonance.py`
>   energy-continuity guard (step 5) is the calibrated detector: threshold 50
>   fires at ~4% fractional detuning, verified against the `TH-9` fixture
>   (pole-law 16.505× vs 16.0×, 3.16%).
> - `build_material_fields` returns σ and εᵣ only — per-tag `μᵣ` needs that
>   function extended (`POST-3` step 5's first code touch).
>
> Results: MMS gate `E_ex = (sin ky, sin kz, sin kx)` at relative L2
> 11.26% → 5.66% over a 2× refinement, **rate 0.9929** vs the O(h) expectation;
> assembled operator complex symmetric to 1e-10 and **not** Hermitian — the
> structural signature that the loss term survived assembly. `solve()` raises
> in real mode (`require_complex_mode`); `TimeHarmonicProblem.dirichlet_e_field`
> imposes an analytic total field on the exterior N1curl dofs, which is how
> every closed-form gate below drives its box. Logs
> `20260731T003553Z_TH-1-steps123-mms.log`, `20260731T021415Z_TH-1-step5.log`.

**`TH-9` — PEC cavity resonance gate** ✅ *(2026-07-30, `core/cavity.py` +
`tests/validation/test_cavity_resonances.py`, `20260730T154846Z_TH-9.log`)*
> First four modes of a 1.0 × 0.8 × 0.6 m cavity match the closed form to
> **0.0436%** (720 cells) / 0.0102% (2268); rate 3.85; the 8 gradient modes
> return as a machine-zero cluster (3.2e-15). **Traps that stand:** a
> 1.0 × 0.7 × 0.5 box is degenerate (two modes coincide); PEC rows need a large
> diagonal in `A` and **unit** diagonal in `B` or the GHEP orthogonalisation is
> invalid. This is the known-frequency fixture the `TH-1` resonance guard is
> verified against.

**`TH-6` — lossy plane wave vs closed form** ✅ *(2026-07-31,
`tests/validation/test_lossy_plane_wave.py`, `20260731T020427Z_TH-6-gate3.log`)*
> The exact source-free `E = ẑe^{−jkx}`, `k = k₀√ε_c` (`Im k < 0` branch),
> imposed as Dirichlet data (εᵣ = 78, σ = 0.7 S/m, 127.74 MHz); *interior*
> slopes measured: `α` to **0.019%**, `β` to **0.059%**, L2 rate 0.9998. Clears
> §10's < 5% MVP bar (the bar is on the field norm — 16³ landed at 5.41% and
> the fix was mesh, not tolerance). Fixed in passing: `post/evaluation.py`
> gathered into a `float64` buffer and had never been called under the complex
> build; it now follows the function's dtype.

**`TH-7` — Validation: waveguide cutoff** ✅ *(2026-07-31,
`tests/validation/test_waveguide_cutoff.py`, `20260731T123411Z_TH-7-gate-final.log`)*
> Evanescent TE₁₀ below cutoff — decay from the transverse geometry against the
> operator's *real* part, complementing `TH-6`'s `Im ε_c` decay. `γ` to
> **0.006%** at 2.4 GHz; L2 rate 1.0013; three-frequency sweep each within
> 0.066% with end-to-end ratio to 0.038% (a k₀-blind solver returns ratio 1);
> `|Im E_y|/|Re E_y|` exactly 0.0 (convention check); the `TH-1` energy guard
> asserted quiet in-band.

**`TH-8` — Validation: dielectric sphere in a uniform quasi-static field** ✅
*(2026-07-31, 15:00 run; `20260731T200457Z_TH-8-gate-final.log`)*
> `E_in = 3/(ε+2)·E₀` measured at **2.443%** at the finest of three meshes,
> fitted rate 1.9675 (superconvergence of the probe-averaged functional, not a
> better element); interior uniformity 0.080%. The load-bearing negative
> control: dropping the sphere from the `material_map` under the *same*
> Dirichlet data moves the interior to 2348% off — the gate cannot be passing
> by reading back its boundary data. New fixture
> `MeshGenerator.sphere_in_box_domain`; its sizing is a gmsh `Ball` field, not
> a `Distance` field (unsigned — would coarsen toward the centre, where the
> gate measures). The lossy-sphere extension it named became `MAT-4` step 1;
> the `k₀R → 0` low-frequency-breakdown regime is still unstressed.
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
| `MAT-4` | SAR computation `σ|E|²/(2ρ)` | 🟡 | standard |
| `MAT-5` | Temperature-dependent conductivity | ⬜ | smoke |
| `MAT-6` | **Dodd–Deeds coil-over-lossy-half-space impedance** | ✅ | heavy |

> `MAT-1` is `⚠️` not because the preset table is wrong but because nothing
> consumes it.

**`MAT-4` — SAR computation** 🟡 *(step 1 ✅ 2026-08-03; step 2 ✅ 2026-08-04.
The chunk stays 🟡: neither step is an IEEE C95.3 1 g/10 g claim — see "does
not close" below. Full plans, control-ceiling arithmetic and audits archived
in `docs/planning/plan-archive.md`.)*
> * **Step 1 — the lossy-sphere gate** ✅ *(2026-08-03, 21:00 run;
>   `src/fem_em_solver/post/sar.py` + `test_lossy_sphere_sar.py`, gate
>   `20260803T020448Z_MAT-4-step1-gate.log`, 5 passed 39.4 s)*. Operating
>   point from the review's computed control ceiling: f = 64 MHz, R = 0.01 m,
>   εᵣ = 78, σ = 0.05 / 0.57 S/m. Mean SAR vs the closed form
>   `σ|3E₀/(ε_c+2)|²/(2ρ)`: **3.42% / 3.54%** at h = R/10, converging from
>   ~8.5% coarse, under a 10% bound that is the closed form's own
>   O((k_inR)²) model error plus P1 discretisation. Interior
>   `Im E_z/Re E_z` matches to 0.17% / 0.55% — **the first quantitative gate
>   anywhere on the imaginary axis of ε_c**. Two-σ ratio control: separation
>   4.850 vs the predicted ceiling 4.855 (gated > 3; the σ-blind side is
>   analytic — `σ₂/σ₁` exactly — a reasoned control, not a measured one).
>   `post/sar.py` computes SAR in UFL from `e_complex` (½ peak-phasor, same
>   convention as `poynting_power_balance`) and does not route through
>   `phantom_fields.py` — centroid samples are not the volume integral SAR is
>   defined by.
> * **Step 2 — mass-averaged SAR** ✅ *(2026-08-04, 21:00 run;
>   `build_density_field` / `averaging_ball_radius` / `mass_averaged_sar` /
>   `point_sar` in `post/sar.py` + `test_mass_averaged_sar.py`, gate
>   `20260804T020933Z_MAT-4-step2-gate2.log`, 3 passed 54.8 s)*. The sizing
>   trap is the design constraint: at ρ = 1000 kg/m³ a 1 g ball is 0.62 R of
>   the step-1 sphere and 10 g exceeds the whole phantom — so the step gates
>   the averaging *operator* at m = 0.05 g (0.23 R, inside the uniform core).
>   Uniform-field identity `SAR_avg/SAR_point = 0.999846` (0.0154% vs a 0.26%
>   measured-parts budget); kernel mass conservation 0.040%; surface control
>   separation 2.2094 vs the convex-lens ceiling `1/f = 2.1875` (the plan's
>   flat-interface 2 was corrected from geometry; both the > 1.5 floor and
>   agreement with `1/f` to 5% are gated). **Defect found and fixed in-run:**
>   a UFL comparison with a non-zero centre raises `ComplexComparisonError`
>   in the complex build (the origin case simplifies away and passes) —
>   `ufl.real` around the comparison argument; **a UFL comparison that works
>   at the origin is not evidence it works anywhere else.**
>
> **Does not close:** `MAT-4` as an IEEE C95.3-conformant 1 g/10 g SAR — that
> needs a phantom large enough to contain the averaging volume with margin;
> the honest place is the coil+phantom fixture (now that `GEO-9` is closed).
> Hold 🟡 rather than claiming the standard; SAR at Larmor stays unlicensed
> (§2.1).

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

**`MAT-6` steps 1–2b** ✅ *(full narratives archived in
`docs/planning/plan-archive.md`)*
> * **Step 1 — the closed form** ✅ *(2026-07-31, 00:00 run;
>   `utils/dodd_deeds.py` + the analytic half of
>   `test_dodd_deeds_impedance.py`, `20260731T050449Z_MAT-6-step1b.log`)*.
>   Anchored on the perfect-conductor limit: the Hankel integral vs the
>   image-mutual `−2πa·A_φ(a,2h)` agree to **0.0002%** — two derivations
>   sharing no algebra beyond μ₀. Also gated: σ = 0 exactly invisible;
>   ΔR > 0, ΔX < 0; thin-skin identity → 0.99973; `ΔR ∝ ω^0.5009`.
>   **Deliberate limitation: this is the 1968 eddy-current kernel** —
>   displacement current neglected; gelled saline at 127.74 MHz (loss tangent
>   ≈ 1.26) is outside its regime.
> * **Step 2a — fixture + air-box probe** 🧪 *(measurement-only, so 🧪 per §3;
>   its numbers stand log-backed, `20260731T094211Z…094411Z`)*. Operating
>   point f = 10 MHz, σ = 100 S/m (loss tangent 1.8e5, δ = 15.9 mm at 3.18
>   cells/δ). Found: ΔR converges in box size by W = 0.15 (0.27% residual
>   motion) but ΔX is still drifting (−35% → −19% → −14%), and the
>   filamentary reference spreads ΔX by 30% over h ± r_wire — so ΔR is
>   gateable and ΔX is sign-and-order only.
> * **Step 2b — the gate; `MAT-6` closed** ✅ *(2026-07-31, 06:00 run;
>   `20260731T110515Z_MAT-6-step2b-gate-numbers.log`, 10 tests, 85 s, heavy,
>   W = 0.15, 138 619 cells, three solves)*.
>   **ΔR = +0.3276882 Ω vs Dodd–Deeds +0.3225961 Ω — 1.58%**, asserted < 5%
>   (bound sized from the step-2a box sweep, not chosen); ΔX ratio 0.8123,
>   gated sign + O(1) only (not converged in box size; tightening needs
>   h/r_wire ≥ 16 or W ≥ 0.25 — a follow-up chunk, never a widened
>   tolerance); null tagging control 1.31e-08 of |ΔZ|; σ-blind control fails
>   by 100%. **What stays open, deliberately:** this licenses the
>   *eddy-current* regime only — saline/Larmor needs the full-wave kernel and
>   stays unlicensed (§2.1), and since `PORT-1` step 2f the 1.58% is
>   explicitly an **unprojected-drive** result (step 3 below re-gates it).
> **Trap found, costs a run if rediscovered.** `ufl.max_value` does not compile
> in the complex build — UFL refuses conditionals on complex-valued operands —
> so the magnetostatic loop fixture's `azimuthal_current_density`
> (`tests/validation/test_circular_loop.py`) cannot be reused verbatim in any
> frequency-domain solve. The probe regularises inside the square root instead
> (`sqrt(x²+y²+1e-24)`). A killed run also leaves a stale FFCx lock that makes
> the *next* run fail with "JIT compilation timed out, probably due to a failed
> previous compile"; clear it with `rm -rf ~/.cache/fenics` in the container.

**`MAT-6` step 3 — re-gate ΔR under the solenoidal projection** ✅
*(2026-08-04, 16:30 run; `tests/validation/test_dodd_deeds_projected_drive.py`,
`20260804T213600Z_MAT-6-step3-gate-final.log`, 8 passed, 65 s, standard, `-n 2`,
138 619 cells, two solves at 27.9 / 25.7 s)*
> **The projection is a no-op on this fixture, to 5e-5 in the gated number.**
> Default-path `ΔR = +3.2770406e-01 Ω` vs Dodd–Deeds `+3.2259615e-01 Ω` —
> **1.5834%**, against the pinned path's `+3.276882e-01 Ω` / 1.58%; asserted
> under step 2b's 5% ceiling, inherited unchanged and not widened. `I′ = 0.919666 A`
> against the meshed `I = 0.919690 A` (ratio 0.999974, 26 ppm) — a closed loop
> drive is already solenoidal, so `P_G J` here is purely a discrete artefact,
> as step 2f predicted. Both solves are driven by the *identical* `J′`
> (`||J′_loaded − J′_free||²/||J′||² = 0.0` on the gate, 8.774e-39 on the probe):
> `remove_gradient_content` never sees the material, so the reaction difference
> measures the half-space and not the drive — measured, not assumed, and the
> assertion that would catch a material-dependent drive is in the file.
> All three runs (probe + two gates) reproduce every printed digit of `ΔZ`.
>
> **The one thing that moved: `ΔX` ratio 0.8123 → 0.9200** (`−5.6657895e-01 Ω`
> vs exact `−6.1586749e-01 Ω`) while `ΔR` moved 5e-5. Reported, gated only on
> sign and order of magnitude exactly as step 2b gates it, and *not* claimed as
> an improvement: this fixture has 5.57% of box motion left in `ΔX` and a 30%
> filamentary spread over `h ± r_wire`, which is more than the 13% shift. The
> converged fixture step 2b named (`h/r_wire ≥ 16` or `W ≥ 0.25`) is what could
> adjudicate it; that is a follow-up chunk for a review to scope, never a
> tightened tolerance here.
>
> **Adjudicated 2026-08-05 by step 4 below: the shift is real.** At W = 0.25 the
> ratios are 0.8740 (pinned) / 0.9849 (projected) — both drives gain ~+0.06 from
> the larger box, but the 0.11 gap between them does not shrink, so the 13% here
> was not reshuffled box error.
>
> **Method note for reuse.** The step-3 tests live in their own module and
> *import* the geometry, current density and tags from
> `test_dodd_deeds_impedance.py` rather than restating them: one definition of
> the fixture, the `project_source=False` pins untouched, and two pytest
> commands of ~70 s instead of one ~155 s command against a 180 s ceiling.
> **Does not close / does not reopen:** `MAT-6` stays ✅; what changed is that
> the claim now covers the production default drive. Saline/Larmor stays
> unlicensed (eddy-current kernel, §2.1).
>
> *Original plan, for the record:*
> Since 2f, `TimeHarmonicSolver.solve()` projects the drive by default, but
> `test_dodd_deeds_impedance.py` pins `project_source=False` to preserve the
> landed 1.58% — so the package's headline coil-loading number is now a
> **non-default-path** result (§2.1 annotation). This step measures the
> projected-drive ΔR on the same W = 0.15 fixture. Both solves (loaded and
> free) must project identically, or the reaction difference picks up the
> drive difference instead of the half-space.
>
> **Anchor:** the Dodd–Deeds closed form `ΔR = +0.3225961 Ω`; expectation
> scale is the unprojected 1.58%. Gate band set from the probe (step-2d
> precedent), and it must land **inside the existing 5%** — a projected ΔR
> needing more than 5% is a finding about the projection in lossy media, not
> a tolerance to widen. Print `I′` vs `I`: the loop drive is closed and
> near-solenoidal already, so the projection should be nearly a no-op there
> (the two-torus fixture measured `I′ = 0.969` of `I`); a large shift is
> itself the result. **Negative controls:** on record, cite — the σ-blind
> `ΔZ = 0` (100% separation) and the null tagging control at `1.31e-08`
> (`20260731T110515Z_MAT-6-step2b-gate-numbers.log`). **Cost:** the step-2b
> gate ran **85 s** at `-n 2` (three solves at 24–26 s on 138 619 cells); a
> projected pair adds two solves plus ~2 s of CG1 Poisson each ⇒ ~140 s if
> cohabited, so probe first and split the commands rather than raising any
> timeout; standard `timeout 180` per command, `-n 2`. Mind the
> module-scoped fixture — adding solves to it re-runs them for every test in
> the module. **Traps:** the existing tests keep their
> `project_source=False` pins (the landed number's provenance — never flip
> them); `ufl.max_value` complex trap (fixture already regularises);
> stale FFCx lock; complex build + `FEM_EM_REQUIRE_COMPLEX=1`,
> `tests/environment` first. **Does not close / does not reopen:** `MAT-6`
> stays ✅ — the unprojected result stands log-backed either way; this
> extends the claim to the production default. Saline/Larmor stays
> unlicensed (eddy-current kernel, §2.1). **Negative result:** report
> projected ΔR, ΔX and `I′`, keep the pins, annotate this entry and §2.1
> (the coil-loading claim then explicitly excludes the production drive),
> add a known-issues entry, stop.

**`MAT-6` step 4 — adjudicate the ΔX shift on the converged box** ✅
*(2026-08-05, 15:00 run; `tests/validation/test_dodd_deeds_reactance_box_size.py`,
`20260805T200455Z_MAT-6-step4-projected-w25.log` (6 passed, 271 s) and
`20260805T200938Z_MAT-6-step4-pinned-w25.log` (6 passed, 260 s), heavy, `-n 2`,
300 591 cells / 353 201 dofs, four solves at 116–127 s; cost probe
`20260805T200132Z_MAT-6-step4-probe.log`)*
> **The step-3 finding survives: the projected drive is closer to Dodd–Deeds in
> ΔX at *both* box sizes, and the two paths do not converge.** The four ΔX
> ratios `ΔX_FEM/ΔX_exact` (exact `−6.1586749e-01 Ω`):
>
> | drive | W = 0.15 | W = 0.25 |
> |---|---|---|
> | pinned (`project_source=False`) | 0.8123 | **0.8740** (`−5.3826816e-01 Ω`) |
> | projected (production default) | 0.9200 | **0.9849** (`−6.0655648e-01 Ω`) |
>
> Both drives improve by ~+0.06 as the box grows — that is the box-truncation
> term, common to both — while the projected-minus-pinned gap is **0.1077 at
> W = 0.15 and 0.1109 at W = 0.25**, i.e. it does not shrink with box size. That
> is the discriminator this step was written for: had the 0.9200 been reshuffled
> truncation error, the two paths would have closed on each other as W grew.
> They did not, so the reactive part carries a drive-dependent offset consistent
> with `PORT-1` step 2e's spurious-gradient (`W_e^spur`) mechanism. Note what is
> *not* claimed: this shows the projection moves ΔX toward the closed form
> systematically, not that ΔX is converged — at W = 0.25 the projected ratio is
> still 1.5% short and still moving with W, and the filamentary reference's 30%
> spread over `h ± r_wire` is untouched by any of this.
>
> **The ΔR control holds, which is what makes the ΔX reading legible.** At
> W = 0.25, projected `ΔR = +3.2768109e-01 Ω` (1.5763%) and pinned
> `+3.2766511e-01 Ω` (1.5713%), against 1.5834% / 1.58% at W = 0.15 — ΔR moves
> < 0.01 percentage-point across a 2.17× change in cell count and is identical
> between drives to 5e-5 relative, so the box change did not move the resistive
> physics and the drives differ *only* in the reactive part. `I` = 0.919690 A
> (meshed) vs `I′` = 0.919666 A (projected), the same 26 ppm as step 3.
> Gates are step 2b's, inherited unchanged: ΔR under the 5% hard ceiling, ΔX on
> sign and order of magnitude only. No ΔX band was tightened to the measured
> ratios — the box convergence of ΔX is the thing under test, so a band sized to
> this run would assert its own conclusion.
>
> **Cost, measured before the tier was chosen** (the §7 stop rule was one solve
> > 300 s at `-n 4`): W = 0.25 is 300 591 cells — 2.17×, not the ~4.6× the box
> volume grew, because the added volume is all far-field at
> `resolution_far = 0.025` — meshing in 18–22 s, one projected solve 81.0 s at
> `-n 4` and 116–127 s at `-n 2`. Four solves do not fit one standard command,
> so the drives are split by `-k` into two ~4.5 min commands, each meshing once
> and solving its own loaded/free pair; `-n 2` (not the permitted `-n 4`) because
> the current and the reaction integral are allreduced. The module restates
> nothing: geometry, current density, tags, both solve routines and the pinned
> reaction integral are imported from the step-2b and step-3 modules, so the box
> is provably the only difference from the recorded W = 0.15 numbers.
> **Does not close / does not reopen:** `MAT-6` stays ✅ — this adjudicates a
> finding, not the chunk. No claim moves in §2.1: the landed 1.58% ΔR is
> untouched, saline/Larmor stays unlicensed (eddy-current kernel), and ΔX is
> still not a gated quantity anywhere.
>
> *Original plan, for the record:*
> Step 3 measured the ΔX ratio move 0.8123 → 0.9200 under projection while
> ΔR moved 5e-5, and this fixture cannot attribute it (5.57% box motion
> left in ΔX at W = 0.20, 30% filamentary spread). Hypothesis, from the
> step-3 entry: the projection removes spurious discrete gradient content
> from the reactive part — `PORT-1` step 2e's `W_e^spur` mechanism.
> Discriminator: on a larger box, projected ΔX sits closer to Dodd–Deeds
> than the pinned drive at *every* size if the mechanism is real; if the
> two paths converge to the same ΔX, the 0.9200 was reshuffled box error
> and the finding dies. **Anchor:** Dodd–Deeds `ΔX = −6.1586749e-01 Ω` and
> `ΔR = +3.2259615e-01 Ω`, with step 2b's gates applied unchanged on the
> W = 0.25 fixture (ΔR < 5% hard ceiling; ΔX sign and order of magnitude —
> never a tightened ΔX band in-slot). The *reported result* is the four ΔX
> numbers: projected/pinned × W = 0.15 (on record) / W = 0.25 (new).
> **Negative control:** on record, cite — the σ-blind `ΔZ = 0` and the
> `1.31e-08` null tagging control
> (`20260731T110515Z_MAT-6-step2b-gate-numbers.log`). **Cost — probe
> before committing to a tier:** W = 0.15 is 138 619 cells at 24–28 s per
> solve at `-n 2`; W = 0.25 scales the box volume ~4.6×, so expect
> ~600 k cells and minutes per MUMPS solve. Run a mesh + single-solve cost
> probe first (`-n 4` allowed, heavy `timeout 1200` for the probe only);
> if one solve exceeds ~300 s at `-n 4`, report the measured cost and stop
> — the rescope is `h/r_wire ≥ 16` local refinement, not a raised timeout
> (§5.1). **Traps:** the `project_source=False` pins stay (the landed
> number's provenance); a module-scoped fixture re-runs its solves for
> every test — separate module importing the fixture, step 3's method;
> stale FFCx lock; `ufl.max_value` complex trap; complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`. **Does not close / does not reopen:**
> `MAT-6` stays ✅ regardless — this adjudicates a finding, not the chunk;
> saline/Larmor stays unlicensed. **Negative result:** report the four ΔX
> and both ΔR numbers, annotate the step-3 entry, stop — an ambiguous
> split (closer at one size, not the other) is also report-and-stop.

### POST — Post-processing & field extraction

| ID | Title | Status | Tier |
|---|---|---|---|
| `POST-1` | Interface-aware field extraction reliability | ⚠️ | standard |
| `POST-2` | Energy/consistency diagnostics | ⚠️ | standard |
| `POST-3` | Replace vacuous consistency metrics | 🟡 | standard |

> *(Closed-step plans, execution journals and audits below are archived
> verbatim in `docs/planning/plan-archive.md`.)*
>
> **`POST-1` — what the ⚠️ now stands for.** Three defects found and closed:
> the complex→float64 cast that scored every phantom metric on `Re(E)` at
> phase 0 (fixed by `POST-3` step 4); the ghost-cell double-count in the
> tagged-cell aggregation (step 1); and the guardrail's rank-local fallback
> (step 2). **What remains — and the next step to scope:** whether the
> boundary-adjacent **drop set** is the right semantics for a *solved* field —
> the guardrail discards 234 of 5073 tag-1 cells but **234 of 385** tag-2
> cells on the minority-tag rank, and no analytic interface field has ever
> been compared against what survives. The review adjudicates the symbol.
>
> * **`POST-1` step 1 — ghost-cell partition invariance** ✅ *(2026-08-04,
>   07:30 run)*. The defect was real: 578 tagged ghost cells at `-n 2`,
>   production overcounting by 2–6% of samples, and on tag 2 the reported
>   `max` itself was wrong (0.884971 vs the invariant 0.879575) — an extremum
>   from a cell another rank owns. Fixed in `_tagged_cells` by restricting to
>   `cells < index_map.size_local` (ghosts still inform boundary-adjacency
>   classification). Gates `20260804T123257Z_POST-1-step1-gate-n2.log` /
>   `…-gate-n4.log`: production equals the owned-cells-only reference exactly
>   in count and to 1e-12 in min/max/mean, counts identical across rank
>   counts; negative control separates by exactly the tagged ghost count.
>   `RE_CAST_DEFICIT_BAND` survived unwidened (45.40% → 44.39% inside
>   (43.40%, 47.40%)).
> * **`POST-1` step 2 — guardrail fallback rank-safety** ✅ *(2026-08-04,
>   13:30 run)*. The per-rank fallback was real, reproduced by an integer
>   identity on a constructed mixed-regime fixture (production sampled 32 vs
>   the interior-only 28 — excess 4, exactly the sliver rank's tagged count;
>   sentinel `max` 200.0 vs 2.0 — identically at `-n 2/4/8`), and fixed by
>   taking the fallback decision on the **allreduced** interior count. Two
>   collateral rank-safety defects fixed with it (rank-local early return
>   that would hang the new allreduce; connectivity now built
>   unconditionally). Gates `20260804T183654Z_POST-1-step2-gate-n2.log` /
>   `…-gate-n4.log`, 12 passed each; regression 27 passed. The
>   `_owned_cell_count` AttributeError escape hatch is **pinned, not fixed**
>   (`test_owned_cell_count_escape_hatch_is_characterised`). **Fixture
>   lesson:** a one-layer **tet** slab is not interior-free (the six-tet hex
>   decomposition leaves interior tets) — thin tagged regions for guardrail
>   tests must be hexahedra.
>
> * **`POST-1` step 3 — drop-set semantics on a solved field: measured** ✅
>   *(2026-08-05, 13:30 run;
>   `tests/post/test_drop_set_semantics_sphere.py`)*. The three statistics of
>   `|E|` over the `TH-8` sphere tag, against the closed form
>   `3/(ε+2)E₀ = 0.037500` at `h_sphere = 0.00833`
>   (`20260805T183328Z_POST-1-step3-gate-n2.log`, 5 passed 4.42 s; identical to
>   the last printed digit at `-n 4`, `…183344Z…gate-n4.log`, 2.21 s):
>
>   | set | n | mean | error |
>   |---|---|---|---|
>   | (a) `prefer_interior=True` (production) | 3327 | 0.039095 | **4.253%** |
>   | (b) full owned tagged set | 4431 | 0.039099 | **4.263%** |
>   | (c) drop set alone | 1104 | 0.039110 | **4.293%** |
>
>   **The answer to the semantics question is that on this field it does not
>   matter — for the mean.** The drop layer is 24.92% of the tag and its error
>   is 1.009× the surviving set's, so discarding it moves the reported mean by
>   0.01 percentage points, 1/400th of the 4.25% error itself. That 4.25% is
>   bulk discretisation, which no sampling rule can touch; the plan's
>   expectation that (c) would sample the smeared `ε = 78` discontinuity and
>   separate is **refuted for the mean** — the interface layer is not biased
>   against the interior closed form.
>
>   Where it separates is the **spread**: surviving `[0.035692, 0.043769]` vs
>   full `[0.033788, 0.044560]` — both extrema of the tag come from the drop
>   layer, and the full range is 1.334× the surviving range. That is the gated
>   separation (ceiling 1.2, probe-measured), together with the exact partition
>   identity `3327 + 1104 = 4431` and (a) inside a probe band
>   `(3.75%, 4.75%)` that sits inside `TH-8`'s own 5%. The (a)-vs-(b)
>   comparison is printed, never gated. Probe
>   `20260805T183210Z_POST-1-step3-probe.log`; regressions 12 passed /
>   12 skipped real, 28 passed complex (`…183359Z…`, `…183409Z…`).
>
>   **For the review to adjudicate.** The guardrail is defensible but is
>   protecting a mean that does not need protecting, at a 24.92% cost in
>   sample count; the quantity it *does* move is the extremum, and SAR peaks
>   are extrema — a rule that discards the interface layer discards the peak.
>   Two confounds are unseparated and neither is this step's to resolve: the
>   sphere's curved boundary puts chordal geometry error in the same layer, and
>   a smooth-interface fixture would tell them apart.
>
> **`POST-1` step 3 — drop-set semantics on a solved field (plan written
> 2026-08-04, 18:00 review; the adjudication the ⚠️ waits on).** Steps 1–2
> made the guardrail rank-safe; nothing has ever asked whether dropping the
> interface-adjacent layer *improves* a statistic on a real field. Fixture:
> the `TH-8` dielectric sphere (`tests/validation/test_dielectric_sphere.py`,
> `sphere_in_box_domain` cell tags) — the one solved field with a
> closed-form interior value, `|E_in| = 3/(εᵣ+2)·E₀`, uniform, gated to
> 2.44% on 2026-07-31. Import the fixture, do not restate it (`MAT-6`
> step 3's method note); solve once, then score three statistics of `|E|`
> over the sphere tag against the closed form: (a) `prefer_interior=True`
> (the guardrail's surviving set), (b) the full tagged set, (c) the drop set
> alone (interface-adjacent cells). **Anchor:** the closed form itself —
> probe first, then gate (a) at a probe-set band that must sit inside
> `TH-8`'s existing tolerance; the (a)-vs-(b) comparison is *printed and
> reported*, never gated — the review adjudicates the semantics from the
> numbers. **Negative control:** (c) samples exactly the smeared
> discontinuity, so its error against the interior closed form is the
> separation scale; compute its ceiling from the probe before asserting any
> factor (`POST-3` step 2's rule). **Cost:** standard, `-n 2`; the `TH-8`
> gate-final ran 6 tests including the solve in 16.2 s
> (`20260731T200457Z_TH-8-gate-final.log`), so probe + gate fit in two
> ~30 s commands, `timeout 180`. **Traps:** complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first; ghosts inform
> classification but never contribute samples (steps 1–2); counts and
> extrema allreduce before asserting; pytest `-s`; the sphere's curved
> boundary puts chordal geometry error in the same interface layer the
> semantics question is about — print per-class cell counts so the two
> effects can be told apart later. **Does not close:** `POST-1` — this step
> puts real numbers under the symbol; the review reads (a) vs (b) and
> decides it. **Negative result:** if (a) scores *worse* than (b), that is
> the answer, not a defect — report all three errors, annotate this entry,
> stop; never pick the statistic that flatters the gate.

> The old flagship metric `e_to_b_mean_ratio` is by construction
> `≈ ω·|A|/|∇×A|` — a mesh length scale, not physics; deprecated-as-a-gate in
> `post/consistency.py` and relabelled in the quick-look report. `POST-3`
> replaced it with identities that can fail for real reasons:
>
> * **`POST-3` step 1 — Poynting real-power balance** ✅ *(2026-07-31, 09:00
>   run; `post/power_balance.py::poynting_power_balance`, gated on the `TH-6`
>   lossy plane wave, `20260731T140404Z_POST-3-step1-gate.log`)*. Imbalance
>   8.19% (12³) → **4.13%** (24³), rate 0.987 in h (the O(h) boundary curl
>   trace); < 5% fine-mesh bar (§10 MVP); inward power sign asserted.
>   σ-blind control: **95.2%** vs 8.19% — 11.6× separation.
> * **`POST-3` step 2 — σ(x) as a DG0 field** ✅ *(2026-07-31, 13:30 run;
>   `20260731T183707Z_POST-3-step2-gate-final.log`)*. Piecewise two-slab
>   σ = 0.1 | 1.4 S/m: imbalance 8.93% (16³) → **4.49%** (32³), rate 0.9915;
>   blind control 99.19% vs 11.85% (asserted 5× — the blind side saturates
>   near 100%, so 8.4× is this fixture's ceiling); uniform-DG0-reproduces-
>   scalar pin at 1e-12.
> * **`POST-3` step 3 — total-current divergence residual** ✅ *(2026-08-02,
>   16:30 run; `post/current_divergence.py::current_divergence_residual`,
>   dual-norm via Riesz representer; gate
>   `tests/validation/test_current_divergence.py`; log of record
>   `20260802T213238Z_POST-3-step3-gate-final.log`, provenance closed by the
>   cohabitation log `20260802T213440Z_POST-3-step3-cohabit.log` — cite that
>   one if questioned)*. CG2 relative residual 9.316e-2 (8³) → 6.358e-2
>   (12³), **rate 0.942 in h** gated at > 0.7; vacuity control: the CG1
>   residual is Galerkin-enforced at 6.1e-15, CG2/CG1 separation **1.5e13**
>   gated > 1e6 (this contrast replaced the σ-dropped control, which attempt
>   1 measured at 1.07× and disproved). Audit caveats that stand: the rate
>   and separation are computed inside assert bodies, not printed to the log
>   (one-line fix for whoever next touches the test); `separation > 1e6` is a
>   structural tripwire, not a regression gate. **Environment note:**
>   `pc_type hypre` SIGABRTs this image — use `gamg`.
> * **`POST-3` step 4 — phasor-magnitude semantics** ✅ *(2026-08-04, 22:30
>   run; both cast sites in `post/phantom_fields.py::_evaluate_on_cells`
>   removed; gate `20260804T033506Z_POST-3-step4-gate.log`, 9 passed 8.1 s;
>   cohabit 17 passed 68.0 s)*. Both identities exact: code-path equivalence
>   vs `evaluate_vector_field_parallel` bit-identical over 5030 samples;
>   phase-rotation invariance to all 9 printed digits. The `Re`-cast deficit
>   is banded from measurement (45.40% ± 2 pp at θ = 0, rotation spread
>   > 0.30 asserted as a floor — the plan's uniform-phase prediction did not
>   apply, phase span 1.2667 rad; failing plan-value probe log committed).
>   CSV schema for real fields byte-unchanged. `MAT-4` step 2's "do not route
>   through `phantom_fields.py`" warning: the cast reason is gone, the
>   samples-vs-volume-integral reason stands.
>
> **Reciprocity is discharged by `PORT-1` step 2, not by a fourth `POST-3`
> step** *(decision, 18:00 review 2026-08-02)*: `‖Z − Zᵀ‖/‖Z‖` on the
> two-torus reaction Z-matrix **is** the field-level reciprocity
> `∫E₁·J₂ = ∫E₂·J₁`, measured at machine precision and gated there. `POST-3`
> had exactly one open leg of its own — piecewise μᵣ, step 5 — and that landed
> 2026-08-04. It stays 🟡 pending the review's call: every `POST-3` step of its
> own is now ✅, and what remains is the borrowed reciprocity leg at `PORT-1`
> step 3b-v. **The 19:30 run did not flip the symbol** — its §9 item said "does
> not close `POST-3`", and closing on someone else's open chunk is the review's
> adjudication, not an implementer's.
>
> * **`POST-3` step 5 — piecewise μᵣ through the Poynting balance** ✅
>   *(2026-08-04, 19:30 run; gate `20260805T003551Z_POST-3-step5-gate.log`,
>   12 passed 114 s, `-n 2`, complex build)*. μᵣ is now a DG0 field on **both**
>   legs — `build_mu_r_field` feeds `bilinear_form`'s curl-curl term and the
>   same field is passed to `poynting_power_balance`'s
>   `H = ∇×E/(−jωμ₀μᵣ)`. Two-slab μᵣ = 2 | 1 across x = L/2 at σ = 0.7 S/m:
>   imbalance 8.6101% (16³) → **4.3284%** (32³), **rate 0.9922 in h**, under
>   the unmoved 5% MVP bar. Scalar-path pin exact (uniform DG0 μᵣ = 1
>   reproduces the float path to `rtol = 1e-12` on all three reported powers).
>   **Both vacuity controls fire**, which is the point of the step: μᵣ-blind
>   *flux leg* 42.2557% (3.693×) and μᵣ-blind *operator* 58.3013% (5.096×)
>   against the honest 11.4409% at 12³, ceiling 1/0.1144 = 8.741×; asserted at
>   3× / 4×. **Orientation was measured, not assumed** (probe
>   `20260805T003302Z`): with the magnetic slab on the *far* side the wave has
>   decayed where μᵣ ≠ 1 and the flux-leg control separated by only **1.141×**
>   — a fixture whose control cannot fire. The entry-side orientation
>   (`20260805T003431Z`) is what the gate uses. `HomogeneousMaterial.validate`
>   was **not** relaxed: μᵣ stays one scalar per material and the piecewise
>   field is assembled from the `material_map`'s scalars. Regression
>   `20260805T003806Z_POST-3-step5-regression.log`: 36 passed / 4 failed, all
>   four pre-existing (known-issues 2, and new known-issues 8 — the
>   magnetostatic-energy `float(complex)` this sweep surfaced, verified at
>   `aabb0a7` with the diff stashed).
>
> **Step 5 plan as written (2026-08-04, 03:00 review; §9 item 1 as of the 18:00
> review).** The "magnetic phantom"
> this step has been waiting on is a fixture, and the two-slab pattern from
> step 2 is it: μᵣ = 1 for x < L/2 and μᵣ = 2 beyond, σ uniform, interface on
> a mesh plane so the DG0 field is exactly the geometry. Two code touches,
> both mirroring the σ pattern from step 2: `time_harmonic.py:400` uses a
> scalar `float(mu_r)` in the curl-curl term — make it a DG0 field through
> `build_material_fields`; and `power_balance.py:111` builds
> `H = ∇×E/(−jωμ₀μᵣ)` with a scalar — the same field must enter there. **The
> vacuity trap is the whole design: μᵣ enters both the bilinear form and the
> boundary-flux leg; fixing only one produces a metric that cannot fail for
> the right reason.** (DG0 is single-valued on exterior facets, so the
> boundary trace is well-defined.) **Anchor:** the parameter-free real-power
> identity `−∮½Re(E×H̄)·n̂ dS = ½∫σ|E|² dV` on the two-μᵣ solve: imbalance
> falls under refinement at ~O(h) (steps 1–2 measured 0.987/0.9915) and the
> fine-mesh imbalance < 5% (§10's MVP bar, same as steps 1–2 — pick the fine
> level from a refinement probe as step 2 did, do not move the bar); plus a
> no-solve regression: uniform DG0 μᵣ = 1 reproduces the scalar-path numbers
> to `rtol = 1e-12` (step 2's scalar-path pin, exactly). **Negative control,
> ceiling measured first:** score the honest solve with μᵣ-blind H (μᵣ = 1
> everywhere in the flux leg only); band the separation from the probe
> measurement — steps 1–2's controls saturated near 1/imbalance, so compute
> the ceiling before asserting a factor. **Cost:** standard tier, `-n 2`;
> step 2's two-level piecewise gate ran 64.5 s — budget ~90 s, probe first.
> **Traps:** `MaterialProperties.mu_r` validation currently rejects
> non-scalars (`time_harmonic.py:85`) — extend the validation with the field,
> not around it; keep the ½ peak-phasor convention; complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first; pytest `-s`.
> **Does not close:** `POST-3` — the reciprocity leg still waits on the
> two-source port fixture (`PORT-1` step 3b-ii). **Negative result:** report
> imbalance and rate at both levels, annotate this entry, stop — an identity
> that fails on piecewise μᵣ after passing on piecewise σ is information about
> the μᵣ discretisation, not a tolerance problem.

### PORT — Ports & S-parameters (Phase 4)

**All `⚠️` chunks below sit on the §2.2 placeholder.**

| ID | Title | Status | Tier |
|---|---|---|---|
| `PORT-0` | Quarantine the placeholder coupling model | ✅ | smoke |
| `PORT-1` | **Real port excitation from the solved field** | 🟡 | standard |
| `PORT-2` | Port data model and tagging contract | 🧪 | smoke |
| `PORT-3` | Calibration checklist → executable checks | 🧪 | standard |
| `PORT-4` | Multi-port drive/termination consistency | ⚠️ | standard |
| `PORT-5` | S-matrix reciprocity/passivity metrics | ⚠️ | smoke |
| `PORT-6` | Frequency sweep orchestration | 🧪 | smoke |
| `PORT-7` | Touchstone metadata + parser cross-check | 🧪 | smoke |
| `PORT-8` | Port-orientation sensitivity | ⚠️ | standard |

**`PORT-1` — Real port excitation from the solved field** 🟡
> Gap-voltage lumped ports, the standard approach for MRI coils at 64–300 MHz:
> excite one port per solve with an impressed gap source; recover `V_i = −∫E·dl`
> across each port gap and terminal currents from the solved field; assemble the
> Z-matrix column-by-column from N single-port solves; convert
> `S = (Z − Z₀I)(Z + Z₀I)⁻¹`.
> Done when: `‖Z − Zᵀ‖/‖Z‖` (reciprocity) sits below a stated tolerance — a real,
> failable identity replacing the placeholder-arithmetic assertions. Depends on
> `TH-1`; wave ports are out of scope at these frequencies.
>
> *(The closed steps below are result blocks. Their full plans, traps, execution
> journals and audit notes are archived verbatim in
> `docs/planning/plan-archive.md` — grep there before re-deriving anything.)*
>
> **Closed steps** *(two-loop air fixture `two_torus_domain`, f = 10 MHz,
> a = 0.04 m, r_wire = 0.005 m, d = 0.04 m; padding 0.08 / h_far 0.03,
> 119738 cells, unless stated; all gates `-n 2`, complex build, in
> `validation-complex` CI)*:
>
> * **Step 1 — reaction Z-matrix probe** ✅ *(first attempt 2026-07-31 blocked on
>   the then-non-conforming fixture — `Z₁₂ ≡ 0` exactly,
>   `20260731T213222Z_PORT-1-step1-costprobe.log`, the total-separation negative
>   control every later step cites; re-run 2026-08-02 after `GEO-8`; closed
>   retroactively when step 2's gate asserted its numbers)*. The measurements
>   that sized every later bound: reciprocity at machine precision (3.06e-13);
>   `Re Z₁₂` exactly 0.0 (structural — lossless operator is real-symmetric);
>   `Im Z₁₂ = +1.125614 Ω` vs `ωM₁₂ = +1.241755e+00 Ω` (−9.35%), the gap owned
>   by the PEC box, not the mesh (padding 0.08→0.12 moves it 5.20% toward the
>   closed form; h_far 0.02→0.03 moves it 0.09%). **The 10% mutual tolerance is
>   measurement-justified — do not tighten**: the filamentary reference itself
>   spans 66.5% of nominal over ρ, z within ±r_wire. Diagonal wrong in sign
>   (`−40.9 Ω` vs Grover `+6.8 Ω`) — became step 2b. Cost ceiling: padding 0.12
>   / h_far 0.02 (237926 cells) was killed at 180 s inside MUMPS; the gate
>   config meshes ~21 s + ~20 s/solve. Logs
>   `20260802T183045Z…184031Z_PORT-1-step1-*.log`.
> * **Step 2 — reciprocity/mutual gate** ✅ *(2026-08-02, 19:30 run;
>   `tests/validation/test_port_reaction_impedance.py`, 4 passed 56.1 s,
>   `20260803T003217Z_PORT-1-step2-gate.log`)*. Gated: `‖Z−Zᵀ‖/‖Z‖ = 2.65e-13
>   < 1e-9`; `Im Z₁₂` within 10% of `ωM₁₂` (−9.35%); `Re Z₁₂ < 1e-30` (exactly
>   0.0); S symmetric, passive and unitary at `Z₀ = 50 Ω`
>   (`‖S‖₂ = 1.000000000000`) — **the repo's first S-matrix derived from a
>   solved field**. Diagonal printed, not gated. Two audit notes that stand:
>   the unitarity assertion follows algebraically from (`Re Z ≡ 0` + symmetry),
>   so it is not independent coverage; and the reciprocity residual is
>   normalised by `‖Z‖ ≈ 58 Ω`, which the diagonal dominates — if a step
>   changes the diagonal's magnitude, move the normalisation to `|Z₁₂|` in the
>   same commit or the bound silently tightens ~50×.
> * **Step 2b — self-impedance diagnosis** ✅ *(2026-08-03, 00:00 run;
>   `tests/validation/test_port_self_impedance_energy.py`, 3 passed 43.5 s,
>   `20260803T050252Z_PORT-1-step2b-gate.log`)*. The reaction integral is
>   **exonerated**: reaction and complex-power routes agree to 1.8128e-10
>   (gated < 1e-9 — only 5.5× margin, solve-limited; a drift is information,
>   re-measure rather than widen). The whole `−40.9 Ω` is an
>   **electric-energy excess**: `4ωW_m/I² = +7.437 Ω` (Grover ratio 1.0908;
>   `grover_loop_inductance()` is in code), `4ωW_e/I² = +48.52 Ω`,
>   `W_e/W_m = 6.524` — no `Z_in` or `S₁₁` may be read off this fixture's
>   unprojected diagonal. Note: `stored_magnetic_energy()` lives in the test
>   file, not `src/` — any step wanting `W_m` in the solver moves it first.
> * **Step 2c — `M(2d)/M(d)` doubling control** ✅ *(2026-08-03, 06:00 run, at
>   padding 0.12; 5 passed 167.7 s,
>   `20260803T110902Z_PORT-1-step2c-gate12-numbers.log`. The first attempt at
>   padding 0.08 failed honestly at −13.33% — the PEC box hurts the wider pair
>   more — and its padding sweep sized the box; the 10% bound predates both
>   measurements and was not touched)*. `|Z₁₂(2d)|/|Z₁₂(d)| = 0.270089` vs
>   closed form 0.287120, **−5.93%**. The test file now sits at the
>   standard-tier ceiling (~168 s) — the next test added there needs its own
>   file.
> * **Step 2d — gradient content of the load** ✅ *(2026-08-03, 13:30 run;
>   `tests/validation/test_port_gradient_load.py`, 7 passed 41.5 s,
>   `20260803T183556Z_PORT-1-step2d-gate.log`)*. The discretised load's gradient
>   content explains the **entire** excess: predicted spur
>   `4ωW_e^spur/I² = 4.852262e+01 Ω` vs measured `4.852271e+01 Ω`, **ratio
>   0.999998**. The identity-residual bound was widened 1e-9 → 1e-7 after a
>   failing probe and adjudicated by the 18:00 review as an honest correction
>   (a two-vector residual reports LU accuracy, a different quantity; the
>   failing probe log is committed; the headline ratio is gated by the
>   untouched 1e-9 two-route check at 7.9e-15). Measured 4.4916e-09 — on any
>   solver/mesh/rank change, re-measure and record; do not widen again.
> * **Step 2e — solenoidal-projection drive** ✅ *(2026-08-04, 00:00 run;
>   `tests/validation/test_port_solenoidal_drive.py`, 9 passed 41.8 s,
>   `20260804T050616Z_PORT-1-step2e-gate.log`)*. Driving `J′ = J − P_G J`:
>   `Im Z₁₁ = +7.437243e+00 Ω` against the step-2d prediction `+7.44 Ω`;
>   Grover ratio 1.090770 gated in the probe-banded `(1.042, 1.140)`; `W_e`
>   collapses 48.52 Ω → 8.76e-5 Ω (factor 5.5e5); `‖P_G J′‖²/‖J′‖² = 4.6e-33`
>   (structural — assembly-level cancellation — gated < 1e-24; a lift to
>   ~1e-18 is information about the assembly); `I′ = 0.969001 A`, 8 ppm from
>   `I = 0.969009 A`, still re-measured and used in every denominator.
> * **Step 2f — the projection is the production drive** ✅ *(2026-08-04, 06:00
>   run; `project_source: bool = True` on `TimeHarmonicSolver.solve()`, backed
>   by `src/fem_em_solver/core/source_projection.py::remove_gradient_content`;
>   gate `20260804T111102Z_PORT-1-step2f-gate.log`, 12 passed 58.9 s; four
>   green regression logs; **known-issues 8 retired**)*. The production path
>   reproduces step 2e's `+7.437243e+00 Ω` to all seven printed figures; the
>   diagonal of `test_port_reaction_impedance.py` is gated (both ports, Grover
>   band, complex-power identity < 1e-9); `Im Z₁₂` moved −9.35% → **−8.03%**
>   of `ωM₁₂`, toward the closed form, inside the unchanged 10%. Callers
>   pinned `project_source=False`, each with a stated reason: the 2b/2d/2e
>   diagnosis files (their subject *is* the unprojected load),
>   `test_time_harmonic_mms.py` (the manufactured source is the exact RHS),
>   and `test_dodd_deeds_impedance.py` — **`MAT-6`'s landed 1.58% is
>   explicitly an unprojected-drive result** *(re-gated 2026-08-04 by `MAT-6`
>   step 3: the pin stays, and the default path measures 1.5834% on the same
>   fixture — the projection moves the gated number by 5e-5 relative)*.
>   Bookkeeping gap (10:30 audit): the live fixture's
>   S-matrix has no cross-run numeric pin — capture a projected-drive S
>   baseline whenever the S conversion is next touched; fold into the
>   touchstone-threading step, not a slot of its own.
> * **Step 3a — Z→S conversion in `src/`** ✅ *(2026-08-03, 09:00 run;
>   `sparameters_from_impedance(z_matrix, *, z0_ohm)` in
>   `ports/sparameters.py`, pure numpy, `⚠️` path untouched;
>   `20260803T140251Z_PORT-1-step3a-gate.log`, 9 passed 58.0 s)*. Code-path
>   equivalence exact (`max|S_pkg − S_test| = 0.0` vs 1e-12); cross-run
>   agreement with the step-2 log held at 1e-6 — the log prints seven figures,
>   so ~5e-8 residuals are the printed value's own floor, adjudicated as an
>   honest split, not a loosening. `summarize_sparameter_sanity()` scored a
>   real matrix for the first time (`passivity_max_sigma = 1.000000000000`,
>   reciprocity delta 3.5e-13, no warnings). `PORT-5` stays ⚠️ — its
>   *sweep-level* metrics still run on the placeholder.
> * **Step 3b-i — gapped two-torus fixture, mesh only** ✅ *(2026-08-04, 04:30
>   run; `two_torus_domain(port_gap=True, gap_angle=0.30, gap_clearance=1e-3)`,
>   default off so the seven existing callers are byte-unaffected; gate
>   `20260804T093552Z_PORT-1-step3bi-gate.log`, 27 passed 1 failed — the one
>   failure is the pre-existing domain-sizing known issue — 101.5 s)*. Volume
>   identities `1.000000000000` at 1e-9; both gap boxes meshed exactly;
>   conductor at 0.9636 of the analytic partial torus inside the
>   probe-measured band `(0.955, 0.975)` (the chordal deficit 0.98030 equals
>   the ungapped fixture's 0.980079 — the evidence the arc is intact); vacuity
>   control `< 0.9790` would catch a non-bridging box. **Piece-policy
>   deviation that later steps depend on: the gap wins over the conductor** —
>   the gap *is* the box exactly, the conductor is the arc minus the box (a
>   dielectric gap with metal in it is not a gap). `tests/mesh` is now 101.5 s
>   with these tests.
>
> **Step 3b — gap-voltage ports** *(firmed 2026-08-03, 18:00 review, once
> `GEO-9` closed)*. End state: excite across tagged gaps, recover
> `V = −∫E·dl` over the gap, cross-check gap-voltage Z against reaction Z,
> then (later steps) resolve the two deliberately-red port tests and thread
> `is_placeholder=False` through `export_touchstone`. The validation fixture
> is the gapped two-torus pair — the only geometry with a closed-form anchor
> (`ωM₁₂ = 1.241755e+00 Ω`).
>
> **Step 3b-ii — gap-voltage `Z₁₂` against the closed form — attempted
> 2026-08-04 (09:00 run), 🟡 parked on
> `attempt/PORT-1-step3bii-20260804T141200Z`; superseded by 3b-iii.** The
> gap-driven machinery runs end to end and two of three claims are green —
> reciprocity `2.2840e-04` (a network identity from two solves, not the
> reaction route's algebraic symmetry) and the open-port precondition
> (`|I_undriven/I_driven| = 2.32e-03`) — but the anchor fails at **+72.12%**
> (`|Im Z₁₂| = 2.137292e+00 Ω` vs `ωM₁₂ = 1.241755e+00 Ω`), with
> σ = 8.0e2 S/m asserted inside the skin-depth ceiling `σ ≤ 2/(ωμ₀r²)`.
> Diagnosed in-slot: `gap_clearance` also sets the box's transverse half-size,
> making its cross-section 1.83× the tube's — 45% of the averaged lines never
> cross conductor, and restricting to the tube's shadow flips the sign of
> `Im V`. Nothing landed; `MUTUAL_TOLERANCE` untouched. *(Branch
> `attempt/PORT-1-step3bii-…` deleted at the 18:00 review 2026-08-04: the
> test file lives on, superseded, on the 3b-iii attempt branch, and the
> measured numbers are in this entry and attempts.md — full plan text in
> the archive.)*
>
> **Step 3b-iii attempted 2026-08-04 (12:00 run) — 🟡 negative, and it is the
> discriminating negative the step was written to buy.** Code parked on
> `attempt/PORT-1-step3biii-20260804T173000Z`; logs on main,
> `20260804T170301Z_PORT-1-step3biii-costprobe.log` (1 failed, 8 passed, 60.0 s)
> and `20260804T170439Z_PORT-1-step3biii-sweep-o5e4.log` (1 failed, 4 passed,
> 63.0 s); ~124 800 cells, mesh ~24 s + two solves ~16–20 s, standard tier at
> `-n 2`.
>
> *Mesh half — done and clean.* `gap_clearance` is split into `gap_burial`
> (ŷ half-length margin, must stay strictly positive) and `gap_overhang`
> (transverse `xz` margin), both defaulting to `gap_clearance`, so the default
> gapped call is byte-identical and 3b-i's gate is untouched. The new
> slab-shaped box meshes **exactly**: meshed/analytic `= 1.000000000000` at
> overhang 2e-4, both ports, asserted at `1e-9` in the file — 3b-i's exact-box
> identity holds at aspect ratio ~1:10 as predicted.
>
> *Measurement half — the fringe hypothesis is refuted.* Varying only the
> overhang:
>
> | `gap_overhang` | fringe | `Im Z₁₂` [Ω] | `Im Z₁₂/ωM₁₂` | `I′` [A] | shadow `V` [× ωM] |
> |---|---|---|---|---|---|
> | 1.0e-3 (3b-ii) | 0.4546 | +2.137292 | **+1.7210** | 0.9151 | 0.750 / 0.687 |
> | 5.0e-4 | 0.3509 | −0.296954 | **−0.2391** | 0.9506 | 0.783 / 0.754 |
> | 2.0e-4 | 0.2739 | +0.411950 | **+0.3317** | 0.9731 | 0.763 / 0.814 |
>
> The full-box mutual is **non-monotone in the fringe fraction and changes
> sign** between 2e-4 and 5e-4. The 3b-ii hypothesis — a 45% annulus of
> opposite-sign field inflating the average, which would march smoothly toward
> 1 as the annulus shrank — predicted ≈ +30% at this fringe and is dead. The
> right reading is that a volumetric average over a *rectangular* region is not
> a port voltage at any overhang: the corners sample fringe field whose sign
> depends on where the box face cuts the fringe pattern, not on how much of it
> there is, and the `1 − π/4` corner floor guarantees the box never stops
> sampling them. `MUTUAL_TOLERANCE` was **not moved**; the gate fails at
> −66.83% and that failure is the result.
>
> *What did improve, and it corroborates the reading.* Every quantity that
> does not depend on the box-average got better as the overhang shrank:
> reciprocity `2.2840e-04 → 1.1509e-04`, undriven-port ratio
> `2.32e-03 → 1.4162e-03`, and the driven current `0.9151 → 0.9731 A`, i.e.
> the 8.5% impressed-current shortfall closed to 2.7% — so the fringe annulus
> *was* eating impressed `J` (3b-ii's third clue was right), it just was not
> what set `V`. And the tube-shadow-restricted average is stable and
> sign-consistent across all three geometries at **0.687–0.814 × ωM₁₂**, a
> spread that no longer shows the 9% inter-port asymmetry as a fixture defect
> so much as a ~20–25% common deficit — consistent with an average over a
> region that still includes non-conductor path length.
>
> **Successor: 3b-v, the facet-integral voltage, on 3b-iv's tags** — as the
> 3b-iii plan's own negative branch said, and now with the box route excluded
> by measurement rather than by argument. **Do not attempt a fourth box
> geometry**; the sign change rules the family out, not one member of it.
> Open question for whoever scopes 3b-v: the shadow average's ~0.78 common
> deficit is the *next* number to explain, and it is not obviously the PEC box
> (step 1's reaction route measured −9.35% there). `Z₁₁` stayed ungated
> throughout, as instructed.
>
> **Step 3b-iv — facet tags on the arc-end discs (mesh only; written at the
> 2026-08-04 10:30 review).** The prerequisite 3b-ii's ranked route 2 named:
> the textbook lumped-port voltage is a facet integral over the
> gap–conductor interface, and the fixture emits no facet tags. Emit one
> facet physical group per port (tags `201`/`202`), each containing the two
> planar discs where the gap box's ŷ-faces cut the conductor arc, found from
> the fragment's shared 2-D boundaries (`gmsh.model.getBoundary` on the gap
> and conductor fragments, intersect), never absolute tags. **Anchor:** each
> port's facet-group area against the analytic `2·πr² = 1.570796e-04 m²`
> (the tube passes fully through the box face whenever `gap_overhang ≥ 0`,
> so each disc is a planar circle of radius `r_wire = 0.005`), banded from
> the probe — planar-disc meshing has only boundary chordal deficit, so
> expect a band far tighter than the volume's 0.980; the two ports equal to
> `1e-9` (same construction). **Negative control:** the ungapped fixture
> emits no `2xx` groups (exact); and a group mistakenly placed on the full
> box face would measure `4(r+o)² ≈ 1.83×` the disc pair per face — total
> separation, assert the measured area is below it. **Cost:** standard,
> `-n 2`, mesh-only, ~25 s per mesh measured; `timeout 180`. **Traps:**
> physical groups of dim 2 added after `synchronize`;
> `model_to_mesh` must be asked for facet tags; on the dolfinx side
> `create_connectivity(fdim, tdim)` before touching facet→cell maps; facet
> areas assemble rank-locally — allreduce before asserting. Shares
> `two_torus_domain` with 3b-iii but does not depend on its *outcome* —
> runs are serial, take main as found. **Does not close:** anything — no
> field is solved; the facet-voltage measurement itself is 3b-v, scoped by
> a review once 3b-iii has reported. **Negative result:** report the
> shared-surface pairs found and their areas, annotate here, stop — no
> blind surface hunting.
>
> **Step 3b-iv attempted 2026-08-05 (21:00 run) — 🟡 incomplete: the mesh
> half is measured and right, the parallel half hangs.** Code parked on
> `attempt/PORT-1-step3biv-20260805T021000Z`; logs on main,
> `20260805T020301Z_PORT-1-step3biv-costprobe.log` (exit 124, 181 s),
> `20260805T020659Z_…-serial-isolation.log` (2 failed, 24 s — the probe that
> set the band) and `20260805T020843Z_…-serial-gate.log` (**2 passed, 22.5 s**
> at `-n 1`).
>
> *What the tags are.* Intersecting the fragment's gap-piece and
> conductor-piece boundaries yields **exactly 2 surfaces per port** — no blind
> hunting, no absolute tags — emitted as physical groups `201`/`202`.
>
> *The analytic anchor in the plan was wrong, and the measurement says by how
> much.* The gap box overhangs the tube in `x` and `z`, so the arc leaves it
> only through the two `y`-faces, and those planes are **not** normal to the
> tube axis (the arc crosses at `φ = arcsin(gap_half_y/R) ≈ 0.2` rad). Each
> cut is an oblique section of the solid torus, not a circle. Its exact area,
> `A(y₀) = ∫_{R−r}^{R+r} 2√(r²−(s−R)²)·s/√(s²−y₀²) ds` (which reduces to `πr²`
> at `y₀ = 0`), gives **1.604721580e-04 m²** for the pair — `1.0216 ×` the
> plan's `2πr² = 1.570796e-04`. Two independent routes agree: OCC's own
> `getMass(2, ·)` on the CAD surfaces returns **1.604721e-04 m²**, every
> printed digit.
>
> | quantity | measured |
> |---|---|
> | facet-group area, ports 201 / 202 | 1.563786482e-04 m² (identical to < 1e-12) |
> | meshed / analytic oblique cut | **0.974490841**, both ports |
> | exact cut / naive `2πr²` | 1.021597 |
> | gap-box `y`-face pair (vacuity ceiling) | 2.88e-04 m², `1.7947 ×` — total separation |
>
> The plan predicted "far tighter than the volume's 0.980"; **refuted** —
> 0.9745 is the *same* chordal deficit the volume shows (0.980079 ungapped,
> 0.98030 on the arc). A planar section of an inscribed linear-tet solid
> inherits the solid's deficit rather than improving on it. The band was set
> from the probe at `(0.970, 0.980)` and the measurement recorded in a code
> comment; nothing was loosened.
>
> *The blocker.* At `-n 2` the run hangs inside `gmshio.model_to_mesh` — before
> any test code — and is killed at the 180 s ceiling; both ranks spin in
> `MPI_Testall ← compute_graph_edges_nbx ← create_entity_permutations`. `-n 1`
> completes the identical case in 22.5 s, and `-n 2` on this fixture *without*
> the new groups is green, so it is neither cost nor geometry: it is the
> distribution of tags on facets that are **interior** to the partition, which
> `201`/`202` are the fixture's first instance of. Filed as **known-issues 9**
> with the stack. CI is `-n 2`, so the diff stays parked. **Successor:** find
> where `distribute_entity_data` diverges for interior facets (compare against
> a fixture that already tags an interior surface, if one exists); a serial-only
> gate is *not* an acceptable fallback here — 3b-v solves on this mesh at `-n 2`.
> A second finding, unrelated and pre-existing: the fixture's `outer_boundary`
> group reaches the dolfinx facet tags from **neither** path (gapped set is
> `[201, 202]`, ungapped is `[]`) — **known-issues 10**, not fixed in passing.
>
> **Step 3b-iv attempted a second time 2026-08-05 (22:30 run) — 🟡 still
> incomplete, and the blocker moved: known-issues 9 was misdiagnosed.** Code
> parked on `attempt/PORT-1-step3biv-20260805T034500Z` (`e3fd31f`), which
> supersedes the 02:10 branch. The gmsh dim-2 physical groups on interior
> facets are **removed**; the fragment-boundary intersection stays only as a
> CAD cross-check print (`201: 2 surface(s) area=1.604721e-04` per port,
> matching the first attempt's OCC number), and the identical facet set is
> rebuilt on the dolfinx side from the distributed *cell* tags —
> `_interface_facet_tags` in `io/mesh.py`, gap piece `101`/`102` against
> conductor `1`/`2`, with the ghost-cell tag pushed through a DG0
> `scatter_forward` because `cell_tags` does not carry ghosts.
>
> *The mesh is not what hangs.* A per-rank marker probe
> (`tests/mesh/probe_two_torus_facets.py`, on the branch) runs the gate's own
> mesh at `-n 2` to completion, **exit 0 in 14 s**
> (`20260805T034007Z_PORT-1-step3biv-hang-localise-fine.log`): 39578/39956
> cells per rank, `create_entities(fdim)` and `create_connectivity(fdim, tdim)`
> both return, **116 interface facets found per port**. The coarse variant is
> 6 s. So `model_to_mesh` and facet creation are cleared by measurement, and
> known-issues 9 is retitled and half-refuted in place.
>
> *What still hangs.* The gate itself times out at `-n 2` after the generator's
> prints and before any assertion — the `dS` facet-area assembly. The two
> ranks' SIGTERM stacks now **differ** (one in `create_entity_permutations`,
> one in mpi4py `MPI_Comm_dup`), so it is a mismatched collective, not a slow
> one. **Ranked hypothesis, in the next attempt's order:** (1) ghost mode —
> `model_to_mesh` takes no partitioner and the probe measures `cells_ghost=0`
> on both ranks, while an interior-facet integral needs both cells of every
> facet; hand it a `shared_facet` partitioner and re-measure. (2) Each rank
> sees exactly one port under the current partition (rank 0 → 201, rank 1 →
> 202), so per-port quantities are rank-local until reduced. (3) Failing (1),
> instrument `_facet_group_area` with the same marker pattern — `fem.form`
> (JIT), `assemble_scalar` and the allreduce are three separable suspects.
> **Second failure**, so §9's own rule applies: the review rescopes this item
> before a third attempt.
>
> **Step 3b-iv, third attempt — rescoped 2026-08-05, 10:30 review. One
> discriminating experiment: ghost cells.** Start from
> `attempt/PORT-1-step3biv-20260805T034500Z` (`e3fd31f`); the tags, the gate
> file, and the marker probe are done — write no new derivation. (1) Hand the
> fixture's `model_to_mesh` call a `shared_facet` cell partitioner
> (`dolfinx.mesh.create_cell_partitioner(GhostMode.shared_facet)`), plumbed
> through `two_torus_domain` only — not every fixture — and re-run the marker
> probe: it already prints `cells_ghost`, which must go nonzero on both
> ranks, and the per-port facet counts, which may change now that both ranks
> can see both ports' facets. (2) Only then run the gate at `-n 2`; green ⇒
> land the branch on main and retire known-issues 9 in the same commit,
> noting the ghost-mode requirement in the fixture docstring. (3) If the
> gate still hangs, do not iterate blind: move the marker pattern into
> `_facet_group_area` — `fem.form` (JIT), `assemble_scalar`, and the
> allreduce are three separable suspects and one probe run names the hanging
> one; that name is the slot's deliverable in the failure case. **Anchor**
> (unchanged, all numbers on record from attempt 1): per-port meshed facet
> area in the probe-set band `(0.970, 0.980)` of the exact oblique cut
> `1.604721580e-04 m²`; ports equal to `< 1e-12`; the `-n 2` gate reproduces
> the `-n 1` numbers (`20260805T020843Z…serial-gate.log`, 2 passed, 22.5 s)
> — a rank-count-dependent area is a missing reduction, not a tolerance
> problem. **Negative control** (on record, cite): the ungapped fixture
> yields no interface tags (exact); the gap-box `y`-face pair ceiling
> `2.88e-04 m² = 1.7947×`, total separation. **Cost:** standard, `-n 2`;
> marker probe 14 s and serial gate 22.5 s measured; `timeout 180` per
> command; a second exit-124 on the gate is the stop signal for route (3),
> not a retry. **Traps, all bought this week:** `cells_ghost=0` under the
> default partitioner — measure it changed before re-running the gate;
> per-port quantities are rank-local (today each rank holds exactly one
> port) — allreduce before asserting, and never divide on a rank whose
> local count is zero; the two ranks died in *different* collectives, so
> any code between mesh build and assembly must be collective-symmetric
> (no rank-conditional early returns); a killed run leaves a stale FFCx
> lock; pytest `-s`. **Does not close:** anything — mesh-only, no field
> solved; the voltage is 3b-v; `PORT-1` stays 🟡. **Negative result:**
> ghosting measured on but the `dS` assembly still hangs ⇒ record the named
> hanging call in known-issues 9 with the probe log, keep the branch
> parked, annotate here, stop — the workaround (an exterior-facet
> reformulation on a submesh, or a dolfinx-version pin) is a review's call,
> not this slot's.
>
> **Step 3b-iv ✅ 2026-08-05 (12:00 run), third attempt — the tags are on
> `main` and the gate is green at `-n 2`.** `20260805T171107Z_PORT-1-step3biv-parallel-gate-fixed.log`,
> **2 passed, 20 s**, `-n 2`, standard tier. The parallel numbers reproduce
> the `-n 1` gate to every printed digit: `A_201 = A_202 = 1.563786482e-04 m²`,
> **0.974490841** of the exact oblique cut `1.604721580e-04 m²` (inside the
> probe-set band `(0.970, 0.980)`), port-to-port ratio **1.000000000000**, and
> the gap-box `y`-face vacuity ceiling `2.880000000e-04 m²` stays `1.794704×`
> away. The ungapped negative control emits facet tags `[]` — exact
> separation. `attempt/PORT-1-step3biv-20260805T034500Z` is landed and may be
> deleted by the review. `tests/mesh` otherwise unchanged: 24 passed, 1
> skipped, 1 failed at `-n 2` in 72 s
> (`20260805T171139Z_PORT-1-step3biv-mesh-regression.log`) — the failure is
> known-issues 5, the off-centre sizing heuristic, untouched here.
>
> *The blocker was a lazy collective, and the review's ghost hypothesis was
> half of it.* `shared_facet` partitioning is now plumbed into
> `two_torus_domain` and does exactly what the rescope predicted —
> `cells_ghost` 0 → **239 / 231** per rank
> (`20260805T170109Z_PORT-1-step3biv-ghostprobe.log`, 14 s) — but the gate
> **still hung** with it alone (`20260805T170140Z_…-parallel-gate.log`, exit
> 124 at 181 s). Route (3) then named the call. The instrumented `dS`
> assembly ran to completion at `-n 2` as a *script* (exit 0, 12 s,
> `20260805T170545Z_…-dS-localise.log`) while markers inside the gate pinned
> its hang to `_facet_group_area` at tag 201
> (`20260805T170743Z_…-pytest-localise.log`, exit 124) — and the script's one
> extra call was an explicit `create_entity_permutations()`. That is the bug:
> the assembler reaches that collective lazily, only on a rank that owns
> integration entities for the subdomain id, and this partition gives each
> rank exactly one port. Rank 0 entered it for tag 201; rank 1 did not. Hence
> the two ranks dying in *different* collectives. The fix is one hoisted line
> in `_facet_group_area`, with the measurement in a code comment. Known-issues
> 9 retires in the same commit. **Standing hazard, not swept up here:** any
> `dS` integral over a subdomain some rank does not touch has this shape; only
> this fixture is fixed. Known-issues 10 (the missing `outer_boundary` tag) is
> untouched and still open.
>
> **Step 3b-v — the facet-integral port voltage on 3b-iv's tags (plan
> written 2026-08-04, 18:00 review; depends on 3b-iv landing).** The
> estimator 3b-ii ranked as route 2, now the only route left: the
> box-average family is excluded by 3b-iii's sign change, and the
> volumetric tube-shadow average sits at a stable 0.687–0.814 × ωM₁₂.
> Recover each port's `V` from the tagged arc-end discs (`201`/`202`): the
> disc-averaged axial `E` times the gap's arc length — the path integral
> restricted to exactly the conductor cross-section, no corner cells, no
> non-conductor path width. Probe first and print each port's two disc
> integrals *separately* with their assembled normals: the two discs face
> opposite directions, so a consistent orientation convention is half this
> step, and a sign error here reproduces 3b-ii's symptom. Reuse
> `test_port_gap_voltage_impedance.py` from
> `attempt/PORT-1-step3biii-20260804T173000Z` (the newest copy; the branch
> also carries the `gap_burial`/`gap_overhang` split) — do not rewrite it.
> **Anchor:** `Im Z₁₂ = V₂/I₁` against `ωM₁₂ = 1.241755e+00 Ω` at the
> unmoved 10% `MUTUAL_TOLERANCE`; reciprocity and the open-port
> precondition at 3b-iii's measured scales at overhang 2e-4 (1.1509e-04,
> 1.42e-03). **Negative controls:** on record, cite — the box family's
> sign flip (+1.7210 / −0.2391 / +0.3317) and the unfragmented mesh's
> exact-zero `Z₁₂`. The shadow average's ~0.78 common deficit is the
> number this estimator must either close or inherit: landing in the same
> 0.69–0.81 band means the deficit is not the averaging region — report
> that as the finding (next suspects: arc-length vs chord definition of
> the gap path, finite-σ penetration into the conductor ends; the PEC box
> is already bounded at −9.35% by step 1's reaction route). **Cost:**
> standard, `-n 2`, `timeout 180`; 3b-iii measured ~60 s per configuration
> (mesh ~24 s + two solves 16–20 s, ~124 800 cells); one geometry
> (overhang 2e-4) suffices. **Traps:** gap-wins piece policy; dim-2
> groups after `synchronize`; `create_connectivity(fdim, tdim)` before any
> facet→cell map; facet integrals assemble rank-locally — allreduce;
> `gap_burial` strictly positive; stale FFCx lock; pytest `-s`; complex
> build + `FEM_EM_REQUIRE_COMPLEX=1`. **Does not close:** `PORT-1` —
> known-issues 3 and the touchstone threading come after; `Z₁₁` stays
> printed, never gated, on this fixture. **Negative result:** report
> `V/ωM` for both ports beside the shadow numbers at the same geometry,
> annotate this entry and known-issues 3, stop — the tolerance does not
> move, and a third estimator is a review's call, not a fourth box.

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

Commit messages, `docs/testing/logs/*.log`, and the retired
`docs/testing/pending-tests.md` (removed 2026-08-04; in git history) use older
IDs. Two generations collided — `E1`–`E4` refer to *different chunks* in
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
2. ~~**`TH-7`**~~ — **done 2026-07-31** (γ to 0.006%); ~~**`TH-8`**~~ —
   **done 2026-07-31** (interior `E` matches `3/(εᵣ+2)E₀` to 2.44%). The cheap
   closed-form gates on the frequency-domain solver are exhausted; `MAT-4`
   step 1 continued that sphere fixture onto the *imaginary* axis of `ε_c`
   on 2026-08-03 (mean SAR within 3.5%).
3. **`POST-3`** — 🟡: steps 1–2 landed 2026-07-31 (Poynting real-power balance,
   4.13% on the `TH-6` fixture with a σ-blind control at 95.2%; then σ(x) as a
   DG0 field, 4.49% on a two-slab σ = 0.1 | 1.4 S/m solve, control at 99.2%);
   step 3 landed 2026-08-02 (total-current divergence residual, 9.32e-2 → 6.36e-2
   at rate 0.942 in h, with a CG1-vs-CG2 vacuity control separating by 1.5e13).
   Step 5 landed 2026-08-04 (piecewise μᵣ = 2 | 1 through **both** legs,
   4.33% at 32³ at rate 0.9922, flux-blind and operator-blind controls at
   3.69× / 5.10×). What remains is only the reciprocity leg, which `PORT-1`
   discharges — the symbol is the review's to flip.
4. **`PORT-1`** — 🟡, and the most active chunk in the plan. `GEO-8` unblocked
   the fixture 2026-08-01; **steps 1 and 2 are ✅** (2026-08-02: reciprocity
   2.65e-13, `Im Z₁₂` within 9.35% of the closed-form `ωM₁₂`, `Re Z₁₂`
   structurally zero, and the repo's **first S-matrix derived from a solved
   field** — symmetric to 2.6e-13 and unitary to 1.000000000000). **Step 2b is
   ✅ as a diagnosis** (2026-08-03): the reaction integral is exonerated — two
   independent routes to `Im Z₁₁` agree to 1.8e-10 — and the negative diagonal
   is localised to an **electric-energy excess**, `W_e/W_m = 6.524`, so no
   `Z_in` and no `S₁₁` may be read off this fixture's diagonal. **Step 2c is ✅
   2026-08-03** — the coupling falls off like `M(2d)/M(d)` to −5.93% against a
   10% bound, so `Z₁₂` is now gated as a *geometric* quantity, not one
   magnitude. **Step 3a is ✅ 2026-08-03** — `sparameters_from_impedance()` is
   in `ports/sparameters.py` and `PORT-5`'s sanity metrics have now scored a
   real matrix. Two spurs remain, independent: **2d** charging that `W_e`
   excess to the load vector, and **3b** gap-voltage birdcage ports — 3b alone
   needs `GEO-9` step 2b.
5. **`GEO-9`** — 🟡: created 2026-08-02 from known-issues 7, **step 1 ✅
   2026-08-03**, and step 1 refuted the hypothesis it was written on.
   `coil_phantom_domain` generates fine in a fresh process; the whole of
   known-issues 7 is the **birdcage** raising without reaching
   `gmsh.finalize()` and poisoning every later mesh in the process — which also
   *hangs* it (harness exit 124 at the ceiling). **Step 2a ✅ 2026-08-03**: the
   hang was two defects, gmsh contamination *and* an MPI collective mismatch,
   both fixed — 180 s hang → 13 s prompt failure, isolation gate exit 0.
   **Step 2b ✅ 2026-08-03, and the chunk is closed**: one `occ.fragment`
   against all tools with the groups re-derived from the out-map; both volume
   identities 1.000000000000 at `1e-9`, all four port boxes exact, whole
   `tests/mesh` green in CI at 42.15 s. Known-issues 7 retires with it. Two of
   the four §10 Target criteria route through these fixtures — **both birdcage
   fixtures now generate**, so `PORT-1` step 3b (gap-voltage ports) is
   unblocked and needs a review to firm up its plan against the measured mesh.
6. **Air-box generalization** — every other `io/mesh.py` fixture still uses a
   single global `setSize` and tight padding, including coil+phantom. Distinct
   from `GEO-9`, which is about whether the mesh exists at all.
7. Then `PORT-4`…`PORT-8`, then Phase 5 (`WF-5`…`WF-8`).

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

Last reviewed 2026-08-05, 10:30 daily review. Tree clean at review start and
end; no `recovered/*` branches. Branch disposition this review:
`attempt/PORT-1-step3biv-20260805T021000Z` **deleted** — superseded by the
22:30 attempt, whose whole point was removing that branch's gmsh-side
interior physical groups; its measurements (areas, bands, the OCC
cross-check) are journaled in attempts.md and the §7 3b-iv entry.
`attempt/PORT-1-step3biv-20260805T034500Z` **kept**: item 1 starts from it.
`attempt/PORT-1-step3biii-20260804T173000Z` **kept** (unchanged reason:
item 5 reuses its `test_port_gap_voltage_impedance.py`; delete only when
3b-v lands that file on main). The 19:30–04:30 slot outcomes (POST-3 step 5
complete — audited §4-compliant this review against the 114 s gate log —
and two 3b-iv incompletes, the second refuting known-issues 9's diagnosis)
are journaled in attempts.md and the §7 entries. New chunk `MAG-16` written
this review to own known-issues 8.

*(The per-review journal — slot recap, completion audits, plan-work notes,
§10 assessment — lives in the review commits and
`docs/planning/plan-archive.md`, not here.)*

**Items 1–4 are mutually independent; item 5 depends on item 1 landing** and
says so in its own text.

1. ~~**`PORT-1` step 3b-iv, third attempt — ghost cells into the port-facet
   mesh.**~~ — **done 2026-08-05 (12:00 run)**: tags on `main`, gate green at
   `-n 2` in 20 s, `A = 1.563786482e-04 m²` per port at 0.974490841 of the
   analytic cut, ports equal to 1.000000000000. Ghosting was necessary but not
   sufficient; the hang was a lazily-reached `create_entity_permutations()`
   entered on one rank only. Known-issues 9 retired. **Item 5's dependency is
   satisfied.** Original text follows.
   *On the critical path — item 5 consumes
   its tags. Failed twice; this rescope replaces the original plan per
   §9's rule, and the job has narrowed to one discriminating experiment.
   Start from `attempt/PORT-1-step3biv-20260805T034500Z` (`e3fd31f`) —
   tags, gate, and marker probe are done; write no new derivation. Execute
   the §7 third-attempt plan: (1) pass a `shared_facet` cell partitioner
   into the fixture's `model_to_mesh` call and re-run the marker probe —
   `cells_ghost` must go nonzero on both ranks before anything else runs;
   (2) only then the `-n 2` gate; green ⇒ land on main and retire
   known-issues 9 in the same commit; (3) still hanging ⇒ move the marker
   pattern into `_facet_group_area` and name which of `fem.form` /
   `assemble_scalar` / the allreduce hangs — that name is the slot's
   deliverable in the failure case. **Anchor** (on record from attempt 1):
   per-port facet area in the probe-set band `(0.970, 0.980)` of the exact
   oblique cut `1.604721580e-04 m²`, ports equal to `< 1e-12`; the `-n 2`
   gate must reproduce the `-n 1` numbers
   (`20260805T020843Z…serial-gate.log`, 2 passed, 22.5 s) — a
   rank-count-dependent area is a missing reduction. **Negative control**
   (on record, cite): ungapped fixture yields no interface tags (exact);
   gap-box `y`-face pair ceiling `2.88e-04 m² = 1.7947×`, total
   separation. **Cost:** standard, `-n 2`; probe 14 s and serial gate
   22.5 s measured; `timeout 180` per command, and a second exit-124 on
   the gate is the stop signal for route (3), not a retry. **Traps, all
   bought this week:** `cells_ghost=0` under the default partitioner —
   measure it changed before re-running the gate; each rank currently
   holds exactly one port, so per-port counts/areas are rank-local until
   allreduced and no assertion may divide by an empty rank's zero; the two
   ranks died in *different* collectives (`create_entity_permutations` vs
   `MPI_Comm_dup`), so code between mesh build and assembly must be
   collective-symmetric; a killed run leaves a stale FFCx lock; pytest
   `-s`. **Does not close:** anything — mesh-only, no field solved; the
   voltage is item 5; `PORT-1` stays 🟡. **Negative result:** ghosting
   measured on but the `dS` leg still hangs ⇒ the named hanging call goes
   into known-issues 9 with the probe log, the branch stays parked,
   annotate §7, stop — the workaround (submesh reformulation or a
   dolfinx-version pin) is a review's call, not this slot's.*

2. ~~**`POST-1` step 3 — drop-set semantics on the solved `TH-8` sphere.**~~
   — **done 2026-08-05 (13:30 run)**: gated green at `-n 2` (4.42 s) and
   bit-identical at `-n 4`. (a) 4.253%, (b) 4.263%, (c) 4.293% against
   `3/(ε+2)E₀`; the drop layer is 24.92% of the tag and separates in spread
   (1.334×) but **not** in mean (1.009×) — the plan's expected separation is
   refuted for the mean, which is the reported result. `POST-1` stays ⚠️: the
   review reads (a) vs (b) and decides the symbol. Original text follows.
   *Independent; the adjudication `POST-1`'s ⚠️ waits on. Execute the §7
   step-3 plan, written this review. **Anchor:** the `TH-8` closed form
   `|E_in| = 3/(εᵣ+2)·E₀` (gated to 2.44%, 2026-07-31) — probe, then gate
   the guardrail-surviving mean at a probe-set band inside `TH-8`'s
   existing tolerance; the surviving-vs-full-set comparison is printed and
   reported, never gated. **Negative control:** the drop set alone samples
   the smeared discontinuity — ceiling from the probe before asserting a
   factor. **Cost:** standard, `-n 2`; the `TH-8` gate-final ran 16.2 s
   including the solve — two ~30 s commands, `timeout 180`. **Traps:**
   complex build; ghosts classify but never contribute samples; allreduce
   counts and extrema; pytest `-s`; import the fixture, don't restate it.
   **Does not close:** `POST-1` — the review reads the comparison and
   decides the symbol. **Negative result:** surviving-set scoring *worse*
   than full-set is the answer, not a defect — report all three errors,
   annotate §7, stop.*

3. ~~**`MAT-6` step 4 — adjudicate the ΔX shift on the converged box.**~~ —
   **done 2026-08-05 (15:00 run)**: on `main`, both gates green at `-n 2`
   (271 s / 260 s, 300 591 cells). The four ΔX ratios are 0.8123 / 0.8740
   (pinned, W = 0.15 / 0.25) and 0.9200 / 0.9849 (projected) — the projected
   drive is closer at both sizes and the 0.11 gap does not shrink with the box,
   so the step-3 finding **survives**; ΔR held at 1.5713% / 1.5763%, i.e. the
   box change moved nothing resistive. Cost probe measured first, as §7
   required: 81.0 s per solve at `-n 4`, inside the 300 s stop rule. Original
   text follows.
   *Independent. Execute the §7 step-4 plan, written this review.
   **Anchor:** Dodd–Deeds `ΔX = −6.1586749e-01 Ω` /
   `ΔR = +3.2259615e-01 Ω` with step 2b's gates unchanged on a W = 0.25
   fixture (ΔR < 5% ceiling; ΔX sign + order of magnitude; never a
   tightened ΔX band in-slot); the reported result is the four ΔX numbers,
   projected/pinned × two box sizes. **Negative control:** on record, cite
   — σ-blind `ΔZ = 0`, null tagging `1.31e-08`. **Cost:** probe the
   W = 0.25 mesh + one solve first (heavy `timeout 1200` for the probe
   only, `-n 4` allowed); if one solve exceeds ~300 s, report the cost and
   stop — rescope is `h/r_wire ≥ 16` refinement, never a raised timeout.
   **Traps:** `project_source=False` pins stay; separate module importing
   the fixture; stale FFCx lock; `ufl.max_value`; complex build. **Does
   not close / reopen:** `MAT-6` stays ✅ regardless. **Negative result:**
   report all six numbers, annotate the step-3 entry, stop — ambiguous is
   also report-and-stop.*

4. **`MAG-16` — complex-build-safe magnetostatic energy (known-issues 8).**
   Independent; new chunk, written this review. Execute the §7 `MAG-16`
   plan. **Anchor:** the existing discrete work-energy identity test — a
   conservation identity, already quantitative and unchanged — passing at
   `-n 2` under `dolfinx-complex-mode`, plus a cross-build pin: the
   complex-build energy matches the real-build value captured in the same
   slot (capture it *before* the fix commit, or it pins nothing) at a
   stated rtol, and the discarded imaginary part is asserted small against
   a probe-measured band, not a guessed one. **Negative control:** on
   record, cite — the `TypeError` reproduced at `aabb0a7`
   (`20260805T003945Z_POST-3-step5-preexisting.log`, 2 failed 4.46 s); the
   imag/real ratio is what a wrong reduction would move. **Cost:** smoke
   tier in a standard slot, `-n 2`: the 4-test file measured 4.46 s; one
   real-build run + one complex-build run + a `tests/solver` regression,
   `timeout 180` each. **Traps:** grep every `float(` cast on the energy
   path in `core/solvers.py`, not just line 661; `tests/environment` first
   in the complex command; do not touch the time-harmonic power paths
   (`POST-3` owns those); known-issues 8 retires only in the fixing
   commit. **Does not close:** known-issues 2 (the other two standing
   regression failures); no field-accuracy claim — the closed-form `MAG`
   gates are untouched. **Negative result:** if the imaginary part is
   genuinely non-small, that is a formulation finding — report the number,
   leave the `TypeError` unpatched, annotate known-issues 8, stop.

5. **`PORT-1` step 3b-v — the facet-integral port voltage (spare).**
   **Depends on item 1 landing; if 3b-iv's tags are not on main when this
   item comes up, stop and journal — do not improvise the tags in-slot.**
   Execute the §7 step-3b-v plan, written this review. **Anchor:**
   `Im Z₁₂ = V₂/I₁` against `ωM₁₂ = 1.241755e+00 Ω` at the unmoved 10%
   `MUTUAL_TOLERANCE`; reciprocity and open-port precondition at 3b-iii's
   overhang-2e-4 scales (1.1509e-04, 1.42e-03). Probe first: print each
   port's two disc integrals separately — normal orientation is half the
   step. **Negative controls:** on record, cite — the box family's sign
   flip and the unfragmented mesh's exact-zero `Z₁₂`; the shadow average's
   ~0.78 deficit is the number to close or inherit, and inheriting it is a
   finding. **Cost:** standard, `-n 2`, ~60 s per configuration measured;
   one geometry (overhang 2e-4). **Traps:** gap-wins policy;
   `create_connectivity` before facet→cell; facet integrals allreduce;
   `gap_burial` strictly positive; FFCx lock; pytest `-s`; complex build.
   **Does not close:** `PORT-1` — known-issues 3 and touchstone threading
   come after; `Z₁₁` printed, never gated. **Negative result:** report
   `V/ωM` beside the shadow numbers, annotate §7 and known-issues 3, stop
   — the tolerance does not move; a third estimator is a review's call.

If the queue drains: **stop and journal.** Do **not** improvise gap-voltage
ports on the birdcage itself or a B1+ chunk — both are deliberately held for
a review to scope once 3b-v reports (including whether `GEO-4`'s graded
sizing is a birdcage prerequisite, per the 15:00 run's 0.7091 measurement).

Every frequency-domain command needs `source /usr/local/bin/dolfinx-complex-mode`
**and** `FEM_EM_REQUIRE_COMPLEX=1`, with `tests/environment` first in the pytest
path list, so an environment regression fails before the formulation tests get
blamed.

---

## 10. Success criteria and long-horizon roadmap

### MVP (end of Phase 2)
- [x] Time-harmonic solver reproduces the analytic lossy plane-wave solution to < 5% *(3.61% in L2; decay constant 0.019%, `TH-6`)*
- [x] Helmholtz coil magnetostatic result matches analytic to < 5% *(0.04%)*
- [x] Phantom σ and εᵣ measurably change the solved field *(σ: interior decay
  constants each match their own closed form and their ratio is 10.3232 vs the
  closed-form 10.3116, `MAT-2`; εᵣ: at εᵣ = 78 the measured β = 27.03 rad/m
  matches the εᵣ-dependent closed form 27.02 to 0.059% where vacuum would give
  2.68, `TH-6`. The loaded-**coil** claim landed 2026-07-31: the FEM ΔR of a
  loop over a conductive half-space matches Dodd–Deeds to 1.58%, `MAT-6` step
  2b — in the eddy-current regime, not yet at saline/Larmor; step 3 extended it
  to the production projected drive at 1.5834%, 2026-08-04.)*

### Target (end of Phase 4)
- [ ] Loaded birdcage + phantom simulation runs end to end *(the mesh half is
  done: both fixtures generate and are identity-gated in CI as of 2026-08-03,
  `GEO-9` steps 1 + 2b. What remains is excitation — `PORT-1` step 3b-i/3b-ii
  on the two-torus validation pair, then ports on the birdcage itself.)*
- [ ] S-parameters derived from the solved field, not a coupling heuristic
  *(partial: the **conversion** is now packaged — `PORT-1` step 3a, 2026-08-03,
  `sparameters_from_impedance()` in `ports/sparameters.py`, gated bit-identical
  to the test path on a solved field — but the only impedance matrix feeding it
  is the two-loop air fixture's, and `run_n_port_sparameter_sweep` still calls
  the heuristic. `PORT-1` step 3b puts it on a coil.)*
- [ ] S-matrix satisfies reciprocity and passivity within stated tolerance
  *(demonstrated on that same fixture, and as of `PORT-1` step 3a, 2026-08-03,
  through **`PORT-5`'s own metrics** rather than the test's arithmetic:
  `passivity_max_sigma = 1.000000000000` and unit column power sums to `1e-9`,
  `reciprocity_max_abs_delta = 3.4981e-13`. Left open because the matrix is
  still a two-loop air fixture's and `PORT-5`'s sweep-level path is untouched;
  what step 3a removed was the "placeholder matrices only" objection.)*
- [ ] B1+ field matches literature/measured data qualitatively *(routes through
  the coil+phantom fixture, which `GEO-9` step 1 gated on 2026-08-03; nothing
  has yet computed B1+ on it.)*

### Long-horizon roadmap — owned by the weekly planning review

The weekly review (docs/automation/weekly-review.md) maintains this section
with brutal realism: phase goals, subgoals within phases, and dated
assessments extrapolated from **measured pace**, never from hope. Rules of
engagement: a subgoal that has not moved in a month is rescoped or killed, not
carried; parity claims are per-workflow, never per-product (§1); a phase goal
without a named validation target (closed form, literature value, or AED
comparison) is not a goal; every phase milestone lands an `examples/` case
and, where gated physics supports it, an Ansys benchmark case (§5.4).

Seeded 2026-08-04 with the scope adjustment; the first weekly review
re-derives all of this from measured pace and owns it thereafter:

- **Phase 5 — loaded birdcage RF (current).** Ports on the birdcage
  (`PORT-1` step 3b lineage), then B1+ maps and SAR on the coil+phantom
  fixture at 64/128 MHz. The honest blocker stated plainly: saline at Larmor
  frequency is outside every current gate's regime (§2.1) — full-wave
  validation there is this phase's real content, not an afterthought, and no
  Phase-6 tuning number means anything before it exists.
- **Phase 6 — tuning.** Mode spectrum of the birdcage (the `TH-9` eigensolver
  machinery on the birdcage mesh), lumped capacitors at the gap/port level,
  and a circuit co-simulation loop: S-parameters from the EM solve, tuning
  and matching in a circuit layer — the HFSS + Circuit split. Hard parts
  named now: near-resonance solves are §2.1's ill-conditioning trap *by
  construction* (tuning means operating at the singularity the resonance
  guard exists to detect), and the whole phase is `PORT-1`-blocked until
  gap-voltage ports gate.
- **Phase 7 — implants.** Parametric implant geometry first (wires, rods,
  plates in the phantom; CAD import later), mesh grading around thin
  conductors (the `MAG-13` 1/r lesson, made worse by skin depth), local SAR
  and near-implant hot spots. This is where AED comparisons matter most and
  where published measured data exists to gate against.
- **Phase 8 — thermal.** Pennes bioheat with SAR as the source term;
  phantom-regime validation first (gel: no perfusion, so the equation reduces
  to heat conduction + source, which analytic solutions cover).
  Mathematically the easiest phase; the risk is validation data and the
  EM–thermal interface, not the solver.

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
