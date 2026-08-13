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
and **coil loading** at the Larmor frequency remains an extrapolation, not a
result. *(Narrowed 2026-08-13, 10:30 review: the **imposed-field** Larmor case
is no longer extrapolation — `TH-10` gates the interior field at 64/128 MHz to
3.643%/1.826% and the ½∫σ|E|² integral to 3.629% against the Mie series. What
remains extrapolated is this fixture's ΔR/ΔX trend across the
eddy→displacement transition — `TH-11`.)*
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

- Wrap commands in `timeout -k 30 <s>` at the tier ceiling — the `-k` is
  mandatory: a plain TERM does not reliably stop an `mpiexec` job, and an
  overrun can wedge the container (MAT-6 step 10, 2026-08-12; known-issues has
  the recovery recipe). **If a run overruns, kill it and
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
  phase keeps **at least five** clean, runnable examples demonstrating its
  capability from distinct angles (different geometries, materials, drives, or
  output quantities — five trivial variations of one case do not count),
  executed via `./run_examples.sh` and producing combined-XDMF output that
  opens in ParaView — this is how the human operator reviews progress
  independently of the test suite. When a chunk changes what an example
  demonstrates, the same commit updates the example. A broken example is a
  defect (known-issues discipline applies). **Examples accrue with gate
  closures, not at phase end**: each time a chunk closes a quantitative gate
  (§4 ✅), the next daily review enqueues a standalone example chunk
  demonstrating that newly gated capability (daily-review.md step 5). The
  audited bar for an in-progress phase is therefore a ramp —
  `examples ≥ min(5, gating chunks closed ✅)` — checked by the weekly review
  (weekly-review.md step 4); the flat five binds once the phase completes.
  *(Clarified 2026-08-09, weekly review: the ramp binds the physics phases
  1+. Phase 0's infrastructure capability — Docker, CI, the harness, the
  runner — is exercised by every example run and does not owe a separate
  example set; its meshing slice is covered by the `mesh:` group.)*
  Example chunks are their own §7 entries sized for one implementer run,
  never riders on physics chunks, and never target ungated capability.
  *(Operator directive 2026-08-10:)* **every runnable example also ships
  with a same-stem step-by-step guide page** — what it demonstrates, how
  to run it, and how to analyze the output step by step so the operator
  can understand what is going on without reading the source (required
  sections and the mechanical gate: §7 `EX-15`). A missing or stale guide
  is a defect like a broken example; the doc-reference checker enforces
  presence and structure, and the weekly review audits guides with the
  ramp. Example chunks scoped after 2026-08-10 include the guide page in
  their done-when; the pre-existing examples are backfilled by `EX-15`.
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
| 3 | Material models, phantoms, SAR | `MAT-1`…`MAT-6` | `MAT-2` ✅; `MAT-6` ✅ (ΔR to 1.58% pinned / 1.5834% on the production projected drive, step 3; eddy-current regime); SAR gated on an **imposed** uniform field only (`MAT-4` steps 1+3: lossy-sphere closed form 3.5%, mass-averaging exact at 1 g/10 g) — coil-driven SAR and the C95.3 claim still open |
| 4 | Coil modeling, lumped elements, ports, S-params | `PORT-1`…`PORT-8` | Package path still heuristic (`PORT-1` 🟡); honest Z→S conversion packaged (step 3a) and the two-loop fixture's Z gated in every entry; the 3b diagnostic lineage is at its last suspect (gap geometry/estimator — weekly-review licence 2026-08-09, see the `PORT-1` entry) |
| 5 | Full MRI system: loaded birdcage, B1+, SAR maps | `WF-5`…`WF-8` | Blocked on Phases 2–4 for excitation; both meshes (coil+phantom, birdcage) generate and are identity-gated in CI (`GEO-9`, 2026-08-03) |
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
| `OPS-12` | Adjudicate the residual-trend classifier (known-issues 2) and return `test_convergence_diagnostics.py` to CI | ✅ 2026-08-08 | standard |
| `OPS-13` | Land the rank-safe `_validate_material_map_tags` fix on `main` with its own gate | ✅ 2026-08-08 | standard |
| `OPS-14` | Diagnose the rank-dependence of `test_single_port_excitation` (known-issues 6) | ✅ | standard |
| `OPS-15` | Retire the checker's standing freshness tax: default `--max-age-s` 1 h → 48 h | ✅ 2026-08-10 | smoke |
| `OPS-16` | Retry-on-529 in the three automation launchers (two review slots lost 2026-08-13; rubric in the §9 item) | ⬜ | smoke |

**`OPS-13` — land the rank-safe material-map validation on `main`** ✅
*(scoped 2026-08-08, 03:00 review; closed 2026-08-08, 06:00 run.)*
> **Landed, gated, and the gate was proved red before the fix.** The hunk is
> byte-identical to `82bfb40`'s (verified by diffing the two patches'
> added/removed lines, not by eye alone) — signature gains `mesh`, the tag set
> is reduced with `mesh.comm.allgather` before it is tested, both call sites
> updated, and the docstring records the 3b-xiii measurement. `OPS-12`'s
> `setConvergenceHistory()` edit at ~line 438 does not overlap; nothing else
> from the branch rode along.
>
> **New gate** `tests/materials/test_material_map_rank_safety.py`, three tests.
> The fixture is the worst case on purpose: **exactly one cell** of a 162-cell
> unit cube is tagged, so at any rank count > 1 at least one rank's local tag
> array is empty. The cell is chosen partition-independently (owned midpoint
> nearest a fixed point, ties to the lowest rank), and the fixture asserts the
> global tagged count is 1 by `allreduce`.
> **Anchors, both asserted on every rank.** (1) Exact set identity — the
> allgathered tag set `== {7}`, the enumerated global set, plus
> `total_cells == 162`. (2) The volume identity, with σ_default = 0 so the
> integral is a bare product: `∫σ dx = 1.23456790123456805e+00` against
> `σ × V_tagged = 1.23456790123456828e+00` and against the closed form
> `200/162 = 1.23456790123456805e+00` (rel 1e-12; the only slack is
> floating-point summation order). `V_tagged = 6.17283950617284090e-03`
> against the Kuhn-subdivision closed form `1/162 = 6.17283950617283916e-03`
> — 2.8e-16 relative. μᵣ and εᵣ integrals are checked against the same
> one-cell partition independently (2.0/1.0 and 4.0/1.0 weightings).
> **Every printed digit string is identical at `-n 2` and `-n 4`** — the
> partition-independence claim, measured rather than argued.
> **Negative control:** a map naming absent tag 4242 raises `ValueError` on
> **every** rank from both `build_material_fields` and `build_mu_r_field`, and
> the message must name both 4242 *and* the surviving global tag 7 — under the
> old code a rank owning no tagged cell reported `Known tags: []`. The
> `cell_tags=None` guard is separately re-asserted, unchanged by the reduction.
> **Red baseline (the gate has teeth):** with the one hunk stashed, the same
> command at `-n 2` reproduces the 3b-xiii failure mode exactly — the accept
> test `FAILED` on one rank while the other hung in a collective, session
> killed at the ceiling, **exit 124 / 120 s**
> (`20260808T110411Z_OPS-13-baseline-red-n2.log`).
> **Gates:** 3 passed at `-n 2` in 2.45 s
> (`20260808T110323Z_OPS-13-gate-n2.log`); 3 passed at `-n 4` in 0.49 s
> (`20260808T110339Z_OPS-13-gate-n4.log`); 7 passed under the complex build
> with `FEM_EM_REQUIRE_COMPLEX=1` and `tests/environment` first, 1.18 s
> (`20260808T110348Z_OPS-13-gate-complex.log`); post-restore re-confirmation
> 3 passed, 0.43 s (`20260808T110636Z_OPS-13-gate-final-n2.log`).
> **Regression on every caller of the two builders** (complex,
> `tests/environment` + `tests/materials` +
> `test_current_divergence.py` + `test_poynting_balance.py`): **22 passed in
> 120.46 s**, exit 0 (`20260808T110648Z_OPS-13-regress-complex.log`).
> Standard tier throughout; no assertion anywhere was loosened and no
> tolerance moved. **Closes nothing else:** known-issues 6 is a different code
> path (`OPS-14`), and no `PORT-1` question is touched.
>
> **CI.** `tests/materials` runs in the `validation` job **serially**, where a
> rank-local read cannot fail — so the file is added twice: to
> `validation-complex`'s explicit list (it runs at `-n 2` there), and as a new
> `validation` step running it at `-n 2` **and** `-n 4`, because one width
> cannot distinguish a fix from an even-partition artifact. Verified with the
> CI-fidelity invocation — no `PYTHONPATH` override, both widths — 3 passed
> each, 0.43 s, exit 0 (`20260808T111107Z_OPS-13-ci-fidelity.log`).
>
> **Observed and deliberately left alone:** `build_material_fields`'s
> `phantom_cells.size == 0` check (same file, phantom branch) reads the same
> rank-local array and would raise on a rank owning no phantom cells. It is
> out of `OPS-13`'s scope — one hunk was what this chunk authorized — and no
> current fixture puts a phantom entirely on one rank, so it is unmeasured
> rather than known-broken. Worth a review's scoping as its own chunk.
>
> *(Original scoping text below, for the record.)*
*(scoped 2026-08-08, 03:00 review, from the `PORT-1` step 3b-xiii park. The
fix exists, measured and documented, on
`attempt/PORT-1-step3bxiii-20260808T005500Z` (`82bfb40`) — it is parked only
because the protocol parks all code on an incomplete run, and any material
map over a subdomain small enough to live on one rank hits the same trap at
any rank count.)*
> **What lands:** exactly one hunk from `82bfb40` —
> `src/fem_em_solver/core/time_harmonic.py`,
> `_validate_material_map_tags(mesh, cell_tags, material_map)` with the tag
> set reduced via `mesh.comm.allgather` before it is tested, plus the two
> call-site updates and the docstring that records the measurement. **Nothing
> else from the branch rides along** — not the ladder test additions, not the
> logs; take the hunk by hand (`git diff 82bfb40~1 82bfb40 --
> src/.../time_harmonic.py`), do not cherry-pick the commit. `main`'s
> `time_harmonic.py` has moved since the branch diverged (`OPS-12` armed
> `setConvergenceHistory()` at ~line 438); the hunks do not overlap, but
> verify by eye. **New gate** (new file, e.g.
> `tests/materials/test_material_map_rank_safety.py`): on a small built-in
> mesh at `-n 2`, tag exactly **one global cell** (pick deterministically:
> the cell containing a fixed corner point, located via ownership query, tag
> communicated to all ranks) and build a material map naming that tag —
> `build_material_fields` / `build_mu_r_field` must succeed **on every
> rank**. **Anchor:** the exact set identity — the allgathered tag set equals
> the analytically known global tag set (constructed, so known by
> enumeration), asserted with `==` on all ranks; and the DG0 σ field built
> from the map integrates to the tagged cell's volume × σ exactly
> (`assemble_scalar` + allreduce vs the cell volume computed the same way —
> an identity, not a band). **Negative control:** a map naming a genuinely
> absent tag must raise `ValueError` on **every** rank (collective agreement
> — the failure mode being fixed is ranks *disagreeing*); assert with
> `pytest.raises` on all ranks and require the error message to name the
> missing tag. **Cost:** standard, `-n 2` then `-n 4` (asymmetric ownership),
> `timeout 180`; no solve — build-only, seconds (the branch's failing session
> was 246 s only because half the ranks hung to the ceiling). **Traps:** the
> trap being fixed is the trap — do not assert on rank-local
> `cell_tags.values` in the new test either; complex build not required
> (build-only path) but run once under it since `time_harmonic.py` imports
> there; a killed run leaves a stale FFCx lock. **Does not close:**
> known-issues 6 (different code path — the placeholder port model; `OPS-14`
> owns that question) or anything `PORT-1`; the parked branch keeps its own
> copy of the fix — whichever lands second reconciles a near-identical hunk,
> which is a trivial conflict and should be noted in the landing commit.
> **Negative result:** if single-rank ownership cannot be forced
> deterministically at `-n 2`, that is a fixture finding — report the
> partition observed, fall back to a tag whose cells are verified (by
> allgather) to be absent from ≥ 1 rank, and record the construction; never
> skip the negative control.

**`OPS-14` — diagnose the rank-dependence of `test_single_port_excitation`
(known-issues 6)** ✅ *(scoped 2026-08-08, 03:00 review; closed as a diagnosis
2026-08-08, 09:00 run.)*
> **Done — and the entry's one-line symptom was right about the outcome and
> wrong about the mechanism, which is now two defects, not one.** The failure
> is not a test assertion at all: it is `ValueError: missing required port
> tags: [21, 22]` (and `[12, 21, 22]`) raised from
> `ports/definitions.py:99`, on 8/8 ranks. It is also red at **`-n 4`**
> (`[22]`, 4/4 ranks) — `-n 8` is the count someone tried, not the threshold.
> `-n 1` and `-n 2` are green, 4 passed each
> (`20260808T140044Z_OPS-14-repro-n1.log`, `…140055Z…-n2.log`,
> `…140056Z…-n8.log`; smoke, 3 s / 1 s / 1 s).
>
> **Defect 1 — the fixture (test-side).** `tags[cell_indices % 4]` runs over
> **rank-local** indices, so the *global* tag set is itself rank-count
> dependent. Measured global per-tag cell counts: `-n 1` `{11:3, 12:3, 21:3,
> 22:3}`; `-n 2` `{4, 4, 2, 2}`; `-n 4` `{4, 4, 4, 0}`; `-n 8` `{8, 4, 0,
> 0}`. At `-n 4` and `-n 8` the required tags are on **no** rank, so the
> raise is *correct behaviour* — the mesh genuinely lacks them. The same
> defect makes the placeholder's numbers rank-dependent while the test is
> green: `P1.I` = `3.000000e-03+4.263898e-04j` at `-n 1` against
> `4.000000e-03+5.685197e-04j` at `-n 2`, **+33.3%**, because `support` is a
> tagged-cell count. Only the finiteness/inequality shape of the assertions
> hides it.
>
> **Defect 2 — `excitation.py:249` (production-side).** It hands rank-local
> `problem.cell_tags.values` to `validate_required_port_tags_exist`, so the
> check is not collective: a rank owning no cell of a terminal region raises
> while other ranks return. This is the family that cost `PORT-1` step
> 3b-xiii a 601 s hang (one rank raising, the other entering a collective).
>
> **The two are separated by counterfactuals, each run in the probe on the
> same solve** (`scripts/probes/ops14_rank_probe.py`; logs
> `20260808T140412Z`/`140424Z`/`140426Z`/`140427Z_OPS-14-table-n{1,2,4,8}.log`,
> smoke, ≤ 3 s each). **A** = collective validator argument, fixture
> untouched ⇒ still raises at `-n 4/8` (`[22]` / `[21, 22]`), so defect 1
> alone is fatal. **B** = fixture tags taken over *global* cell numbering,
> production code untouched ⇒ global per-tag counts become exactly
> `{3, 3, 3, 3}` at **every** rank count, and it *still* raises on 4/4 ranks
> at `-n 4` and 8/8 at `-n 8`, so defect 2 alone is fatal. Neither fix works
> without the other.
>
> **§4 anchor — the cross-rank identity.** Under counterfactual B the
> quantities the test reads are **byte-identical** at `-n 1` and `-n 2`:
> `P1.V = 1.000000000000e+00+0.000000000000e+00j`,
> `P1.I = 3.000000000000e-03+4.263897544510e-04j`,
> `P2.V = 5.000000000000e-02+0.000000000000e+00j`,
> `P2.I = 1.000000000000e-03+0.000000000000e+00j`,
> `coupling = 1.000000000000e-01`, `wrapped_ring_distance = 1` — against
> production's 33.3% divergence across those same two rank counts. The
> negative control (the reproduction itself: same command red at `-n 8`,
> green at `-n 1`, before any change, both logs kept) executed as specified.
>
> **Disposition: the pre-registered not-to-fix branch, taken as written.**
> Both defects are wholly inside the `PORT-0` placeholder `PORT-1` deletes —
> defect 2 is a line of `run_placeholder_port_coupling_case`, defect 1 a
> fixture that exists only to drive it. known-issues 6 is **re-pointed at
> `PORT-1`**, not retired, exactly like entry 3. Shared-machinery survey (the
> condition that would have forced a fix): no other non-collective tag read
> remains in `src/` — `core/time_harmonic.py:162` was fixed by `OPS-13`,
> `post/sar.py:184` already reduces with `allreduce(..., op=MPI.MAX)`,
> `io/mesh.py:1711` with `SUM`. **Only change landed under `src/`:** a hazard
> warning in `validate_required_port_tags_exist`'s docstring — behaviour
> unchanged — so `PORT-1`'s real caller does not repeat defect 2. Regression
> `20260808T140513Z_OPS-14-regress.log` (`tests/ports` + the entry's test,
> `-n 2`, 4 s): **2 failed, 19 passed**, and both failures are known-issues 3
> verbatim (matched-port zero diagonal), unrelated. Nothing re-pointed, no
> assertion touched, `PORT-0` quarantine intact.
>
> *(Original plan below.)*
> *(scoped 2026-08-08, 03:00 review. The last
never-diagnosed baseline entry after `OPS-12` retired entry 2 and `MAG-6`
step 1 re-characterised entry 4 — and both of those found the recorded
symptom wrong or the green signal non-physical, so entry 6's description is
to be re-derived, not trusted.)*
> **Diagnosis, not necessarily a fix.** (1) Reproduce first: the recorded
> symptom is "passes at 1 rank, fails at `mpiexec -n 8`" — run the test at
> `-n 1`, `-n 2`, `-n 8` and capture the **actual** failing assertion and
> values (known-issues 2's recorded symptom was wrong; treat entry 6's the
> same way). (2) Locate the rank-local read. Named suspects, in order: the
> fixture builds `cell_tags` as `tags[cell_indices % 4]` over **rank-local**
> indices on a 12-cell unit cube, so at `-n 8` some ranks own ≤ 1 cell and
> see a strict subset of `{11, 12, 21, 22}` — any code (or test assertion)
> that treats the local tag set or a per-tag cell selection as global then
> diverges across ranks; the consumer is
> `run_placeholder_port_coupling_case` (`ports/excitation.py`), the
> `PORT-0`-quarantined placeholder. (3) **Pre-registered disposition,
> decided before running:** if the defect is wholly inside the placeholder
> model that `PORT-1` deletes ⇒ do **not** fix it — annotate known-issues 6
> with the located line and the known-issues-3 "resolve in `PORT-1`"
> disposition, and the chunk closes as a diagnosis (the `PORT-1` step 2b
> precedent); if it is in shared machinery (tag handling, result reduction,
> anything `PORT-1` keeps) ⇒ fix it, gated. **Anchor (either branch):** the
> cross-rank identity — the quantities the test reads must be equal across
> `-n 1/2/8` (exact for tag sets and counts, and to round-off for reduced
> scalars); on the fix branch, assert it; on the diagnosis branch, print the
> per-rank-count table into the log as the §4 measurement. **Negative
> control:** the reproduction itself — the same command red at `-n 8` and
> green at `-n 1` *before* any change, both logs kept. **Cost:** standard,
> `timeout 180` per command; the test is a 12-cell placeholder evaluation,
> seconds per run — `-n 8` is authorized here because the defect *is* the
> rank count (smallest-width rule satisfied: the failure needs ≥ 8).
> **Traps:** `DeprecationWarning` from the alias is expected, not the
> defect; pytest swallows prints without `-s`; do not "fix" by weakening the
> finiteness assertions; nothing here may start gating the placeholder's
> numbers as physics (`PORT-0` quarantine stands). **Does not close:**
> `PORT-1`, `PORT-3`, or any physics claim; known-issues 6 leaves only with
> a fixing commit, or is re-pointed at `PORT-1` if the disposition is
> not-to-fix. **Negative result:** irreproducibility at `-n 8` is itself the
> finding (the entry predates the current fixtures) — record the three-way
> rank table in known-issues 6 and stop.

**`OPS-11` — `tests/mesh` in CI** ✅ *(created 2026-08-02, closed 2026-08-03,
12:00 run; full narrative archived in `docs/planning/plan-archive.md`)*
> The directory no job ran — which is why known-issues 7 (mesh generators
> failing outright) sat undiscovered. The `validation` job's
> `Mesh generation suite` step now runs the **whole directory** with exactly
> one exclusion left: the known-issues-5 `--deselect` (off-centre sizing
> arithmetic) — **removed 2026-08-06 by `GEO-4` step 1; the step now excludes
> nothing and runs 27 passed 1 skipped in 85.3 s**. **20 passed 1 skipped
> 1 deselected in 42.15 s, exit 0**
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

**`OPS-12` — adjudicate the residual-trend classifier** ✅ *(created 2026-08-07,
18:00 review; closed 2026-08-08, 00:00 run. Retires known-issues 2.)*
> **Done, and the classifier moved, not the test.** The chunk asked which side
> of the disagreement was wrong; the answer is the code, on all three counts —
> the file held **three** defects, not the one it was written for.
>
> **1. The threshold (the chunk's actual question).** The classifier carried
> `f >= 0.75` ⇒ `mostly-decreasing`, `f >= 0.5` ⇒ `mixed`, with `f` the
> fraction of non-increasing steps. Nothing documented those numbers — the
> docstring named no thresholds at all, so the only specification of the
> labels is the label names, and under their plain reading ("mostly X" = a
> strict majority of X steps) all six of the test's expectations follow
> exactly, including the disputed `[1.0, 0.4, 0.45, 0.1]` at `f = 2/3`. The
> old bands were also asymmetric with no stated justification — width 0.5 for
> increases against 0.25 for decreases — and made `mostly-decreasing`
> **unreachable** for any non-monotone history of four or fewer samples. The
> three non-monotone labels now partition by the sign of `f - 0.5` and the
> docstring states the table.
> **2. The recorded symptom of the second failure was wrong.** known-issues 2
> said `assert diagnostics is not None` (line 63). It was
> `assert diagnostics.converged`, `converged_reason = -3`
> (`KSP_DIVERGED_ITS`), 300 iterations, residual `1.4999e-06`: the fixture
> requested gmres+jacobi at `ksp_rtol = 1e-8` with `ksp_max_it = 300`, and
> that solve needs **1409** iterations on the 1405-cell fixture (probe log
> `20260808T050338Z_OPS-12-probe.log`: reason 2 / 1409 its / `4.26e-12` at a
> 5000 cap; bjacobi/ilu 338 its; lu/mumps 1). The cap was under-resourced, so
> the cap moved and the assertion did not. jacobi was kept deliberately — it
> is the weak preconditioner that makes the history long enough to classify.
> **3. The classifier was unreachable in production.** The time-harmonic path
> never called `ksp.setConvergenceHistory()` (the magnetostatic path always
> has), so `residual_history` came back **empty** on every solve and
> `residual_trend` was permanently `unavailable` — which means the test's
> membership assertion had been passing vacuously the whole time. Armed; the
> test now gates `len(history) == iterations + 1` and
> `trend == classify_residual_trend(history)`, so the unit identity and the
> production path are tied together.
>
> **Gate:** 18 passed at `-n 2` under the complex build with
> `FEM_EM_REQUIRE_COMPLEX=1` and `tests/environment` first, 0.93 s
> (`20260808T050622Z_OPS-12-gate-final.log`; first green run
> `20260808T050500Z_OPS-12-gate.log` at 2.38 s, baseline
> `20260808T050156Z_OPS-12-baseline.log` 2 failed / 4 passed). The quantitative
> assertion is an exact discrete identity — the label as a function of `f`,
> asserted with `==` on an 11-row parameterized family whose sequences have
> analytically known decrease fractions spanning both sides of the specified
> `f = 0.5` **and** both sides of the retired `f = 0.75`, so the four rows in
> `0.5 < f < 0.75` are exactly the ones the old thresholds got wrong.
> **Negative controls:** an alternating history (`f = 0.5`) classifies
> `mixed`; a strictly increasing one classifies `mostly-increasing` and is
> asserted *not* to be either decreasing label; non-finite and negative
> histories classify `invalid`. Real-build regression on the two solver files
> CI runs: 9 passed, 1 skipped
> (`20260808T050535Z_OPS-12-regress-real.log`). CI: the file is now in
> `validation-complex`, which was known-issues 2's own stated exit condition.
> Nothing physics-side closes — no tolerance elsewhere moved and no
> inner-region quantity is gated.

*(Original entry text, for the record.)*
> `classify_residual_trend()` (`core/solvers.py`) returns `mixed` where its
> test expects `mostly-decreasing`; known-issues 2's own warning applies —
> **do not assume it is the test** (the `MAG` closed-form precedent cut the
> other way). Step: hand-derive, from the classifier's documented
> definition/thresholds, the classification of the test's exact sequence;
> whichever side the derivation contradicts is the wrong one; fix that side
> only. Then re-run the whole file under the complex build and remove the
> `OPS-10` exclusion so `validation-complex` runs it (known-issues 2's
> status note says exactly this is the exit condition). **Anchor:** the
> hand-derived classification is an exact discrete identity — assert the
> classifier reproduces it on a parameterized family of synthesized residual
> sequences with known decrease fractions spanning both sides of each
> documented threshold (exact equality, no tolerance). **Negative control:**
> a genuinely alternating sequence must classify `mixed` and a strictly
> increasing one must not classify `mostly-decreasing` — the identity has
> teeth only if a wrong label is reachable. **Cost:** standard, `-n 2`,
> `timeout 180`; the file's second failing test solves a small
> `cylindrical_domain` case (seconds on record for its siblings); run under
> complex + `FEM_EM_REQUIRE_COMPLEX=1` so the `@complex_only` half cannot
> pass by skipping. **Traps:** the file mixes `@complex_only` and plain
> tests — one selected build must execute both, which is why complex;
> `tests/environment` first; the heptagonal inner cylinder is latent on
> these fixtures (EX-2 caller audit) — nothing here gates an inner-region
> quantity, keep it that way. **Does not close:** anything physics-side;
> known-issues 2 leaves only with the commit that lands this. **Negative
> result:** if the documented definition is too ambiguous to derive either
> label, that is the finding — the classifier is unspecified, not broken;
> report the derivation gap, annotate known-issues 2, propose the spec for
> a review, stop.

**Open follow-up in OPS — the `lint` CI job is red on `main`, and that is
adjudicated as expected-red for now** *(surfaced by `OPS-12`'s regression
log, decided 2026-08-08, 03:00 review)*. `flake8`/`black --check`/`isort
--check-only` fail on `src` and `tests` from **pre-existing** debt (W293
throughout `solvers.py`, E501 in `time_harmonic.py`, etc.) — no recent chunk
introduced any of it (verified for `OPS-12`: zero findings on its added
lines). A repo-wide reformat is deliberately **deferred until the `PORT-1`
lineage lands**: `attempt/PORT-1-step3bxiii-…` carries a 2000+-line test
file plus `src/` edits, and reformatting `main` underneath it would turn the
eventual landing into a conflict festival for zero behavioral gain. Whoever
lands that branch should scope the reformat as the next OPS chunk, in its
own commit, immediately after. Until then: red `lint` is known and expected;
do not "fix in passing", and do not read it as a chunk failure.

**`OPS-15` — retire the checker's standing freshness tax: default
`--max-age-s` 3600 s → 172800 s (48 h)** ✅ *(2026-08-10, 13:30 run; smoke,
three legs at 1 s each, no solves run)*
> **Done, first attempt, nothing rescoped.** `default=3600.0` →
> `default=172800.0` in `scripts/testing/check_example_doc_references.py`,
> the module docstring's example invocation follows it, and a short paragraph
> in the docstring records *why* 48 h (so the next reader does not re-tighten
> it). `artifact_mtime()` untouched; `PENDING_GUIDES`, the reference pass and
> the guide pass untouched; the scratch directory was **not** cleaned — the
> green leg runs against the same day-old artifacts the tax was firing on.
>
> | leg | invocation | exit | flagged |
> |---|---|---|---|
> | baseline, same slot (`20260810T183126Z_OPS-15-oldwindow.log`) | `--max-age-s 3600` | **1** | 14, "4.4 h old, limit 1.0 h" |
> | **anchor (a)** (`20260810T183139Z_OPS-15-default.log`) | default | **0** | 0 — *zero refresh solves* |
> | **anchor (b)** (`20260810T183202Z_OPS-15-tight-negctl.log`) | `--max-age-s 1` | **1** | 14, "limit 0.0 h" |
> | arithmetic (`20260810T183247Z_OPS-15-limit-arith.log`) | default, synthetic fixture | **1** | 1, "72.0 h old, **limit 48.0 h**" |
>
> The baseline leg was re-measured in-slot rather than cited: it reproduces the
> on-record tax (`20260810T124544Z_EX-9-refcheck.log` and siblings) on
> *today's* artifacts, so the before/after pair differs by the default alone
> and by nothing about the scratch directory's state. The `limit 48.0 h`
> arithmetic could not be shown on real artifacts — no referenced artifact is
> older than 48 h, which is exactly what anchor (a) asserts — so it was fired
> against a backdated `.csv` and a one-line guide in a throwaway
> `--docs-root` under scratch, removed after the run. Net: the branch is
> **retuned, not disabled** (it still flags at 72 h, and 3.3× tighter than
> the 158-h `EX-14` catch it must keep catching), and the ~80–200 s
> per-slot refresh tax is gone. Original scope follows.

*(scoped 2026-08-10, 10:30 review —
the decision three consecutive run journals asked for, taken; one run, smoke
tier, doc-tooling only, no solves licensed).* The doc-reference checker's
freshness pass at its default 1.0 h window has fired in every example-touching
slot since 2026-08-09 (`EX-6`, `EX-10`, `EX-9`, `EX-14` journals) — the window
is shorter than the 90-min slot grid, so any slot that runs the checker after
examples aged half an hour pays an 80–200 s refresh solve. That is a
structural tax, not a freshness finding. The review's decision: the standing
default becomes **48 h** — wide enough that committed guides referencing
same-day artifacts stay green across a review interval, and narrow enough
that the one genuinely dead reference this pass ever caught (the 158.0-h-old
`straight_wire_A.bp`, `EX-14`) is still 3.3× over the new limit. The tight
window stays available explicitly: in-slot freshness-branch controls keep
passing `--max-age-s 1`, exactly as `EX-14`'s negative control did. The
alternative (refreshing artifacts from inside the runner) was rejected — it
spends solves on every runner invocation to keep a scratch directory warm.
Change `default=3600.0` → `default=172800.0` in
`scripts/testing/check_example_doc_references.py` (argparse and the module
docstring's example, which currently shows `--max-age-s 3600`); the violation
message already prints the limit in hours. **Anchor:** two-sided checker
behavior in one slot — (a) default invocation exits 0 on the existing
scratch artifacts with **zero** refresh solves run (the tax retired, vs the
on-record exit-1-then-refresh in `20260810T124544Z_EX-9-refcheck.log` and
three sibling logs); (b) `--max-age-s 1` still exits 1 flagging every scratch
artifact (14 flagged on record, `20260810T140434Z_EX-14-refcheck-negctl.log`)
— the branch is retuned, not disabled. **Negative control:** (b) is it; also
assert the stale-message arithmetic prints `limit 48.0 h`. **Tier/cost:**
smoke — checker runs are ~1 s; the only compute risk is scratch artifacts
older than 48 h at run time, in which case one refresh is licensed and the
run notes it. **Traps:** `artifact_mtime()` (directory-tree mtime, `EX-14`)
must stay the mtime source; `PENDING_GUIDES` and the reference/guide passes
untouched; do not "clean up" the scratch directory to make (a) pass — the
point is that day-old artifacts are acceptable evidence. **Does not close:**
nothing physics-side; the checker stays advisory (not a CI gate). **Negative
result:** if the default invocation still exits 1 on same-day artifacts after
the raise, the mtime source is wrong somewhere new — report with the flagged
list, leave the default as landed only if (b) still holds, known-issues
entry.

### MAG — Magnetostatics (Phase 1)

| ID | Title | Status | Tier | Result |
|---|---|---|---|---|
| `MAG-1` | Vector-potential formulation, N1curl, gauge penalty | ✅ | standard | 0.04% centre vs closed form |
| `MAG-2` | Straight-wire analytic validation | ✅ | standard | |
| `MAG-3` | Circular-loop analytic validation | ✅ | standard | |
| `MAG-4` | Helmholtz analytic validation | ✅ | standard | 0.04% centre / 0.83% mean |
| `MAG-5` | h-refinement convergence study | ✅ | standard | |
| `MAG-6` | Coil+phantom B-field symmetry metric strategy | ✅ | landed on DG0 at h = 0.010: mirror-symmetry `max_rel_diff` **0.323844 / 0.302661 / 0.308407** at `-n 1/2/4` vs the untouched 0.350, three-way rank spread **7.00%** (gate ≤ 10%); `-n 1` byte-reproduces the on-record 0.323844 | steps 1–3 ✅ 2026-08-08 — CG1 interpolation owned it (rank-dependent 3.03×, non-convergent under `h`); boundary and gauge exonerated; ~0.53 was discretisation (p ≈ 1.07); step 3 re-pointed **both** sampled metrics at DG0 and refined one rung, no tolerance touched; known-issues 4 retired. Gates discretisation symmetry, **not** phantom physics (uniform μ) |
| `MAG-7` | Fix point evaluation in validation tests | ✅ | standard | |
| `MAG-8` | Restrict straight-wire current density to the wire | ✅ | standard | |
| `MAG-9` | Re-size validation meshes to fit the tier budget | ✅ | standard | |
| `MAG-10` | Gauge penalty was below the safe window | ✅ | standard | default now 1.0 |
| `MAG-11` | Parallel energy was rank-local (missing allreduce) | ✅ | smoke | |
| `MAG-12` | `evaluate_at_points` used the MAG-7 broken pattern | ✅ | smoke | |
| `MAG-13` | Analytic-Dirichlet outer boundary for wire/loop | ✅ | heavy | wire 12.75%, loop 7.07%, rate 1.10; 167 s + 196 s |
| `MAG-14` | Helmholtz magnitude comparison in the test suite | ✅ | smoke | 0.728% vs closed form (1.731% before `GEO-8`); 11 s, in CI |
| `MAG-15` | Lagrange-multiplier Coulomb gauge (cross-check) | ✅ | smoke | 7 passed, 13 s |
| `MAG-16` | Complex-build-safe magnetostatic energy | ✅ 2026-08-05 | smoke | 10 passed complex `-n 2` in 4.9 s; cross-build pin 2.9e-07, `Im W` exactly 0; retires known-issues 8 |

**`MAG-16` — complex-build-safe magnetostatic energy** ✅ *(2026-08-05,
16:30 run; retires known-issues 8)*
> **Done.** `compute_magnetic_energy()` now reduces the assembled scalar with
> `np.real` and **raises** if `|Im W|/|Re W|` exceeds `ENERGY_IMAG_RTOL = 1e-8`
> — `abs()` was rejected deliberately: it would absorb both a spurious
> imaginary part and a negative real one. Measurements, all `-n 2` on the
> coarse straight-wire fixture (`tests/solver/test_energy_and_point_evaluation.py`):
>
> | quantity | penalty gauge | Lagrange gauge |
> |---|---|---|
> | real-build `W` (captured **before** the fix commit) | `1.121469318858e-08 J` | `1.121466766900e-08 J` |
> | complex-build `W` after the fix | `1.121469648297e-08 J` | `1.121466766900e-08 J` |
> | deviation from the real-build pin | `2.938e-07` (`1.9e-08…2.9e-07` over four runs) | `1.278e-13` |
> | ratio `abs(Im W) / abs(Re W)` | **0.0 exactly** | **0.0 exactly** |
>
> The imaginary part is exactly zero because the magnetostatic load is real and
> `ufl.inner` conjugates its second argument, so the integrand is
> `μ⁻¹|curl A|²/2` — the reduction discards nothing, which is what the second
> new test asserts (band `1e-12`, inside the solver's own `1e-8` refusal
> threshold). The penalty gauge is not bit-reproducible run to run (its
> operator carries the gauge null space at κ ~ 1e10), hence `PIN_RTOL = 1e-5`,
> two decades above the observed wander and five below the O(1) defects the pin
> exists to catch. The two pre-existing identity assertions are **unchanged**
> and now pass in the complex build. Logs: pre-fix negative control
> `20260805T213201Z_MAG-16-probe-complex-prefix.log` (2 failed 7 passed, the
> `TypeError` at `solvers.py:661`) and `20260805T213144Z_MAG-16-probe-real.log`
> (the pin capture, 5 passed 6.5 s); gates
> `20260805T213601Z_MAG-16-gate-complex-final.log` (10 passed 4.9 s) and
> `20260805T213357Z_MAG-16-gate-real.log` (6 passed 3.0 s); regressions
> `20260805T213408Z_MAG-16-regress-complex.log` (`tests/solver` 2 failed 34
> passed 28.3 s — the standing complex-mode failures went 4 → 2 and the
> remaining two are known-issues 2) and `20260805T213514Z_MAG-16-regress-real.log`
> (1 failed 28 passed 3 skipped 18.4 s, same entry). The file joins the
> `validation-complex` CI job in this commit, which is what stops the cast from
> coming back. Not closed here: known-issues 2, and no field-accuracy claim —
> the `MAG` closed-form gates are untouched.
>
> Original entry follows *(chunk written 2026-08-05, 10:30 review)*:
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

**`MAG-6` step 1 — execute the never-run symmetry metric, and make the
boundary-mirror hypothesis pay or die** *(scoped 2026-08-07, 18:00 review.
The chunk is 🧪 with a revised test that has literally never executed; its
known-issues 4 note says a boundary-mirror artifact "should be ruled out
before the tolerance is touched" — this step is that ruling-out, and it is
in-phase: Phase 5's B1+ target routes through this same coil+phantom
fixture.)*
> Measurement, not a fix. A probe script (`scripts/probes/mag6_step1_probe.py`)
> computes the symmetry metric (`max_rel_diff` of |B| across the fixture's
> mirror plane, sampled via `post.evaluation.evaluate_vector_field_parallel`
> — never the `MAG-7`-era path that produced the unreliable 0.322) at **two
> paddings**: the fixture default and 1.5× it, same solve settings otherwise.
> **Anchor:** the mirror-symmetry identity — the geometry is symmetric by
> construction, the exact metric is 0, so everything measured is error; the
> quantitative assertion is the *response*: pre-decided readings are
> **(mirror confirmed)** metric drops ≥ 2× under the padding growth ⇒ the
> boundary owns it; successor = decouple `air_padding` (the Helmholtz-fix
> pattern, `docs/validation/helmholtz.md`, which bought 20% there); **(mirror
> exonerated)** metric moves < 20% ⇒ the suspect becomes the metric/sampling
> path itself; **(mixed)** between ⇒ report both values, stop. Known-issues 4's
> on-record 0.557 at default padding is the comparison point — reproduce it
> first (±10%) or the fixture has drifted and that is the finding instead.
> **Negative control:** a deliberately offset phantom (asymmetric by
> construction) must *increase* the metric — directional only, no factor
> asserted in-slot; print it so the next review can size a band from
> measurement. **Cost:** unmeasured — mesh-only probe first, then one solve
> at `-n 2`, `timeout 600`; one solve > 300 s ⇒ report cost and stop
> (standard tier target; the fixture meshes in seconds per `GEO-9` step 1).
> **Traps:** rank-local point evaluation (the exact bug family that broke
> `MAG-7`); reductions before asserting; real build suffices (magnetostatic);
> do **not** touch the 0.35 tolerance or the test file's assertions — the
> test stays red and unchanged, this step only buys the diagnosis.
> **Does not close:** `MAG-6` (the metric *strategy* decision is a review's,
> with these numbers) or known-issues 4 — annotate both. **Negative result:**
> every band is informative — this is a discriminator; report and annotate
> known-issues 4, stop.

**`MAG-6` step 1 — ✅ executed 2026-08-08 (22:30 run). The boundary is
exonerated; the estimator is the finding.** Probe:
`scripts/probes/mag6_step1_probe.py`. Full write-up in
`docs/testing/attempts.md` (2026-08-08T03:45Z); known-issues 4 rewritten.
> **The reproduction failed, so §7's fallback applied:** the record 0.557 does
> not reproduce — the test prints **0.238291** and **passes** its own 0.350
> tolerance (`20260808T033316Z_MAG-6-step1-testmetrics.log`). The drift is not
> a fix. **The metric is rank-dependent by 3.03×** on one unchanged
> 19 792-cell mesh: `max_rel_diff` = **0.727907 (`-n 1`, fails)** / 0.240541
> (`-n 2`) / 0.321468 (`-n 4`), so the green CI signal is a property of the
> partition. **Located to the CG1 interpolation, not the solve:** `curl A` is
> cell-wise constant at N1curl degree 1, and sampling the same field at the
> same points through DG0 is rank-stable — 0.513648 / 0.534746 / 0.538472
> (4.8% spread) with assembled `‖B‖_L2` stable to **0.09%**, against 1.84%
> through CG1. **Both bands' hypotheses die on the rank-stable path:** growing
> the padding 1.5× moves the DG0 metric **0.005%** (0.534746 → 0.534772), far
> from the "≥ 2× drop" that would have confirmed the boundary; and the gauge
> penalty — 1e-3, 1000× below the validated floor and the source of the run's
> `GaugeContaminationWarning`s — is exonerated too, moving the metric 0.240541
> → 0.241846 and `‖B‖_L2` by 0.016% at gauge 1.0. **The negative control is not
> directional** on the rank-stable path (offset phantom 0.476684 vs centred
> 0.534746, *down*), and the fixture says why: `mu = MU_0` is uniform, so the
> phantom is physically invisible and the control moves only the mesh.
> **Nothing was touched:** the 0.350 tolerance, `tests/tolerances.py`, and every
> assertion in the test file are unchanged. **Cost:** 8 standard-tier commands,
> longest 92 s.
> **Open for a review — the estimator, not the tolerance.** Candidates, ranked
> by what the measurements support: (i) make the metric cell-native (DG0, or
> evaluate `curl A` directly) so the verdict is a property of the mesh rather
> than of `-n`; (ii) give the fixture the material contrast its control
> assumes (`mu_phantom ≠ mu_air`), which would make the control directional and
> the symmetry claim physical; (iii) refine `h` — 0.015 m gives only ~2.7 cells
> across the 0.04 m phantom radius — and read the DG0 metric's convergence, the
> one route that decides whether ~0.53 is discretisation or a defect. **0.350
> may not be raised before (iii) is measured.**

**`MAG-6` step 2 — measure the DG0 metric's `h`-convergence: is ~0.53
discretisation or a defect?** ✅ *(executed 2026-08-08, 07:30 run — see the
readings block below. Original plan text follows.)* *(scoped 2026-08-08, 03:00 review — step 1's
candidate (iii), taken first deliberately: (i) re-pointing the test at DG0
today would flip it hard-red (0.53 > 0.35) with no licensed number to gate
against, and (ii) adding material contrast changes the physics under the
metric; (iii) is the measurement both of those decisions need.)*
> Measurement, not a fix — extend `scripts/probes/mag6_step1_probe.py`; the
> test file and the 0.350 tolerance stay untouched. Solve the same
> coil+phantom fixture at three resolutions — the default `h` (19 792 cells
> on record) and two uniform refinements (target `h/1.5` and `h/2`; the
> default meshes in 2–3 s per the step-1 meshprobe, so ~8× cells at `h/2` is
> ~160 k, well inside standard) — and read the **DG0-sampled** `max_rel_diff`
> and mean at each rung, `-n 2`. **Anchor:** the convergence claim itself —
> if ~0.53 is discretisation, the DG0 metric must fall monotonically with
> `h`; compute the observed rate from the three rungs (the metric is built
> from a field that is O(h) at best for N1curl degree 1, so a rate ≫ 0 with
> a monotone ladder is the signal, not a specific constant). Pre-decided
> readings: **(discretisation)** monotone decrease, total drop ≥ 1.5× over
> the 2× refinement ⇒ ~0.53 is coarse-mesh error; successor = extrapolate
> the `h` where the DG0 metric meets 0.35, cost it, and only then decide
> estimator vs tolerance; **(defect)** total move < 20%, or non-monotone ⇒
> the asymmetry is mesh-independent — suspect the sampling-point set or the
> fixture, and the tolerance question is moot until it is found; **(mixed)**
> between ⇒ report all three rungs, stop. **Negative control:** rank
> stability at every rung — the DG0 metric at `-n 1` vs `-n 2` must stay
> within the step-1 spread (≤ 10%; 4.8% on record at the default `h`), or
> the rung is measuring the partition again and the ladder is void; also
> print the assembled DG0 `‖B‖_L2` per rung (0.09% rank-spread on record),
> which must itself converge. **Cost:** standard, `-n 2`, `timeout 600` per
> command; step-1 measured 0.5 s per solve at `-n 2` default-`h` and 12.9 s
> at `-n 1` (sequential LU — the expensive way; keep `-n 1` runs to the
> rank-stability checks). Mesh-probe the two refined rungs first; a rung
> > 300 s ⇒ drop it and report two rungs plus the cost. **Traps:** step-1
> list unchanged (rank-local point evaluation, reduce before asserting,
> real build); refinement via the fixture's resolution knob, not a manual
> re-mesh — the mesh must stay the fixture's own; do not touch
> `tests/tolerances.py` or the test file; the CG1 numbers may be printed
> beside DG0 for continuity but nothing may be asserted on them. **Does not
> close:** `MAG-6` (the estimator strategy stays a review's, now with the
> convergence measured) or known-issues 4 — annotate both. **Negative
> result:** every band is informative — (defect) is arguably the more
> valuable outcome; report, annotate known-issues 4, stop.

**`MAG-6` step 2 — ✅ executed 2026-08-08 (07:30 run). (discretisation): the
DG0 metric converges at ~O(h), and it already meets 0.350 at `h/1.5`.** Probe:
`scripts/probes/mag6_step1_probe.py --stage hconv`. Full write-up in
`docs/testing/attempts.md` (2026-08-08T12:55Z); known-issues 4 annotated.
> **The ladder reads (discretisation) at both rank counts that completed it.**
> DG0 `max_rel_diff` on the **fixed** probe grid, `-n 2`
> (`20260808T123245Z_MAG-6-step2-hconv-n2.log`): **0.534746** (h = 0.015,
> 19 792 cells) → **0.312197** (h = 0.010, 55 784) → **0.255165**
> (h = 0.0075, 124 179) — monotone, total ratio **2.0957** over the 2×
> refinement (band needs ≥ 1.5), observed rate **p = 1.067** against the O(h)
> ceiling N1curl degree 1 allows. At `-n 4`
> (`20260808T124355Z_MAG-6-step2-hconv-n4.log`): 0.537750 → 0.304356 →
> 0.292706, ratio **1.8372**, p = 0.878 — same band, independently.
> **Rung 1 byte-reproduces step 1**: 0.534746 at `-n 2` and 0.513648 at
> `-n 1`, digit for digit on an unchanged fixture.
> **The negative control voids the finest rung, and the band survives it.**
> Three-way rank spread `(max−min)/min` of the DG0 metric: rung `h`
> **4.69%**, rung `h/1.5` **6.40%** — both inside the ≤ 10% control — but
> rung `h/2` moves **14.71%** between `-n 2` and `-n 4` and is therefore
> **void by its own control**, reported and not used. §7's two-rung fallback
> carries the reading anyway: 0.534746 → 0.312197 is a **1.713×** monotone
> drop across a **1.5×** refinement, already ≥ 1.5 on controlled rungs alone
> (1.767× at `-n 4`). The `-n 1` control for rung `h/2` was **dropped on
> cost**, per §7's > 300 s rule: sequential LU goes 13.0 s → 132.4 s over the
> first two rungs and the third exceeded the 600 s ceiling
> (`20260808T123335Z_MAG-6-step2-hconv-n1.log`, **exit 124**) — the rung was
> not retried at a longer timeout.
> **The solve is not what moved at rung 3.** Assembled `‖B_dg0‖_L2` converges
> — 3.699608960472e-07 → 4.093187042167e-07 → 4.282577123172e-07, successive
> moves 10.64% then **4.63%** — and its rank spread at rung `h/2` is
> **0.0079%** (`-n 2` vs `-n 4`) against the metric's 14.71%. So the finest
> rung's instability is in the **point sampling**, not the field: as cells
> shrink under a fixed probe grid, which cell owns a point becomes a
> partition question again. That is the ceiling on refining this estimator.
> **Bonus, print-only (nothing asserted): CG1 does not converge on the same
> ladder.** The test's own path reads 0.240541 → 0.760519 → 0.723637 at
> `-n 2` (0.324167 → 0.555144 → 0.258471 at `-n 4`) — non-monotone and
> mostly *rising* under refinement, on the identical solves where DG0 falls
> monotonically. Step 1 localised the rank-dependence to CG1; this adds that
> CG1 is not fixable by refinement either.
> **Successor number, costed (§7's (discretisation) successor).** The
> extrapolation is unnecessary — the ladder already contains the answer:
> the DG0 metric meets the **existing untouched 0.350** at `h = 0.010`
> (0.312197 at `-n 2`, 0.304356 at `-n 4`), i.e. at rung `h/1.5`, for
> **55 784 cells, 6.4 s mesh + 2.0 s solve at `-n 2`** — comfortably
> standard tier. Fitting p = 1.327 over the two controlled rungs puts the
> 0.350 crossing at h ≈ 0.0109 m, consistent. **This licenses the number
> candidate (i) lacked:** re-pointing the estimator at DG0 *and* refining the
> fixture to h = 0.010 would gate green against 0.350 without touching the
> tolerance. **The decision remains a review's** — nothing was re-pointed
> here. **Nothing was touched:** the 0.350 tolerance, `tests/tolerances.py`,
> and the test file are unchanged; the ladder refines through the fixture's
> own `resolution` knob, and the probe grid is **frozen at the default-`h`
> clearance** on every rung so refinement cannot move the points (the
> rung-native grid is printed beside it: 0.534746 / 0.269491 / 0.274266).
> **Does not close:** `MAG-6` (estimator strategy stays a review's) or
> known-issues 4 — both annotated. **Cost:** 4 standard-tier commands, 27 s
> / 35 s / 601 s (the exit-124 control) / 32 s.

**`MAG-6` step 3 — land the adjudicated estimator: DG0 sampling at
h = 0.010 m, gated against the untouched 0.350** *(adjudicated and scoped
2026-08-08, 10:30 review; queued §9 item 1)*.
> **The adjudication this chunk was holding for.** Step 1 localised the
> rank-dependence to the CG1 interpolation; step 2 measured that CG1 does not
> converge under `h` while DG0 falls at p ≈ 1.067 and meets the unmodified
> 0.350 at h = 0.010 on both rank counts that completed the ladder. Candidate
> (i) is therefore taken: re-point the test's sampling at DG0 and refine the
> fixture one rung. Candidate (ii) — real phantom material contrast — is
> rejected *for this chunk*: it changes the physics under the metric, and the
> fixture's uniform-μ caveat (known-issues 4) means today's metric is a
> discretisation-symmetry identity; that caveat transfers into the test's
> docstring rather than being fixed here. The 0.350 tolerance moves in
> neither direction.
> **Plan.** Modify `tests/validation/test_coil_phantom_bfield_metrics.py`
> only: sample `curl A` through the DG0 path the probe validated
> (interpolate into DG0, evaluate via
> `post.evaluation.evaluate_vector_field_parallel` —
> `scripts/probes/mag6_step1_probe.py` is the working reference), set the
> fixture's `resolution` to 0.010 m, keep the mirror-symmetry metric and the
> 0.350 bound unchanged. **Anchor:** the mirror-symmetry identity gated
> `max_rel_diff < 0.350` at h = 0.010 — the on-record values are 0.312197
> (`-n 2`), 0.304356 (`-n 4`), 0.323844 (`-n 1`); print the measured value
> beside the record. **Rank-stability gate (the property CG1 lacked):**
> three-way spread `(max−min)/min` across `-n 1/2/4` asserted ≤ 10% —
> 6.40% on record at this rung. **Negative control:** cite, do not
> recompute — the CG1 record: 3.03× rank swing at h = 0.015 and
> non-monotone under refinement (0.240541 → 0.760519 → 0.723637); the
> retired path may keep a pinned print, never a gate. **Cost:** standard
> tier — mesh 6.4 s + solve 2.0 s at `-n 2`, the `-n 1` rung 132.4 s on
> record; three commands, `timeout 180` each. **Traps:** the step-1/-2
> list — reduce before asserting, DG0 not CG1, stale FFCx lock after any
> kill; do not touch `tests/tolerances.py`; the off-centre asymmetry
> control keeps its recorded direction (it *decreases* the metric on this
> uniform-μ fixture). **Closes:** `MAG-6` ✅, and known-issues 4 retires
> with the landing commit — stating in both places that this gates
> discretisation symmetry, not phantom physics. **Negative result:** the
> on-record numbers failing to reproduce (metric > 0.350 or spread > 10%)
> is a reproduction failure — park on `attempt/*`, annotate known-issues 4,
> touch nothing; the record is the evidence either way.

**`MAG-6` step 3 — ✅ executed 2026-08-08 (12:00 run). The estimator landed;
a *second* CG1-owned metric surfaced on the way and was fixed with it.**
Test: `tests/validation/test_coil_phantom_bfield_metrics.py`. Full write-up in
`docs/testing/attempts.md` (2026-08-08T17:10Z); known-issues 4 retired.
> **Red first.** The test at `-n 1` on the pre-change fixture fails exactly as
> known-issues 4 records: `max_rel_diff=0.728 (tol 0.350)`, `max_abs_diff`
> also over its scale so the `or` branch did not rescue it
> (`20260808T170126Z_MAG-6-step3-redbaseline-n1.log`, 20 s).
> **The gate, green at three rank counts.** DG0 sampling, `resolution = 0.010`
> m, probe grid pinned to the 0.015 m clearance (the ladder's fixed grid),
> `PHANTOM_SYMMETRY_REL_TOL = 0.35` **untouched**: `max_rel_diff` =
> **0.323844** (`-n 1`, 144 s), **0.302661** (`-n 2`, 10 s), **0.308407**
> (`-n 4`, 10 s). Three-way spread `(max−min)/min` = **7.00%**, inside the
> pre-registered ≤ 10% (6.40% on record). The `-n 1` reading **byte-reproduces
> the step-2 record 0.323844**. Spread computed by this session across the
> three harness logs — a single pytest process cannot span rank counts.
> **The scoped change was not sufficient, and that is the finding.** Refining
> to h = 0.010 with only the symmetry metric re-pointed left the test **red at
> `-n 4`**: the *centerline smoothness* check — a separate assertion, sampling
> the same CG1 interpolation — failed at jump ratio **0.705** against its 0.60
> bound (`20260808T170334Z_MAG-6-step3-gate-n4.log`), where `-n 2` read
> 0.318029. A second `-n 4` run of identical code read **0.732**: the CG1
> centerline is not rank-stable *and* not run-to-run reproducible. Measured
> on the same solve, DG0 read **0.227869**
> (`20260808T170423Z_MAG-6-step3-centerline-diag-n4.log`), so the centerline
> was re-pointed at DG0 too — same defect, same fix, tolerance untouched.
> **Honest limit on the centerline metric.** DG0 shrinks its rank scatter but
> does not remove it: 0.473300 / 0.268765 / 0.251746 at `-n 1/2/4` is an
> **88%** three-way spread (CG1's is ~200%). All three pass the 0.60 bound,
> but **no rank-stability claim is made for the centerline gate** — the ≤ 10%
> gate is the symmetry metric's, and only it. Sizing that second estimator is
> unscoped work, left for a review.
> **Second-order caveat, measured:** the DG0 symmetry metric moved 0.323290 →
> 0.302661 (6.8%) between two identical `-n 2` runs, with CG1 moving only 0.8%
> — the meshing is not bit-reproducible run to run, and DG0 point sampling is
> sensitive to which cell owns a point. Both readings sit inside the recorded
> band and under 0.350; the ≤ 10% spread gate absorbs it, but a tighter future
> band would have to account for it.
> **Closes:** `MAG-6` ✅ and known-issues 4, both stating the metric gates
> **discretisation symmetry, not phantom physics** (uniform μ — the phantom is
> invisible to this solve); the caveat now lives in the test's module
> docstring. **Cost:** standard tier, 5 commands, 20 / 12 / 9 / 10 / 10 / 144 s.

**`MAG-6` step 5 — re-point the gate fixture at the validated gauge floor**
✅ *(completed 2026-08-09, 12:00 run. **The gate now solves at the validated
floor and both metrics landed on their step-4 predictions to better than
0.01%, with the bounds untouched.** Three harness logs, standard tier:
`20260809T170054Z` (`-n 2`, 15 s), `20260809T170117Z` (`-n 4`, 9 s),
`20260809T170214Z` (`-n 2` confirming run after the docstring edits, 12 s),
all `_MAG-6.log`.)*
> **Readings, against step 4's on-record expectations.** Centerline jump ratio
> (gated, ≤ 0.60): **0.250414** at `-n 2` and **0.250474** at `-n 4`, versus
> the predicted 0.250416 / 0.250453 — deviations **0.0008%** and **0.008%**,
> two to three orders inside the ~2% finding threshold. Mirror symmetry
> (gated, ≤ 0.350): **0.311170 / 0.311166**, versus 0.311166 / 0.311157 —
> **0.001%** and **0.003%**. Two-rank spread at the floor: **0.024%**
> centerline, **0.001%** mirror. A third run of the same `-n 2` case read
> 0.250404 / 0.311167, so run-to-run noise is ~0.03% — the 6.8% mesh noise on
> record belongs to the old sub-floor fixture, as the step-5 scope predicted.
> **The change is the one argument licensed** (`gauge_penalty=1e-3 → 1.0`),
> plus in-file comment/print updates so the fixture's "on record" strings
> quote the penalty-1.0 numbers rather than the retired sub-floor ones.
> `tests/tolerances.py` is untouched; both bounds are untouched; no `src/`
> change.
> **In-fixture continuity observation.** The retired CG1 print-only path still
> rank-swings at the validated floor — 0.323398 at `-n 2` against 0.714122 at
> `-n 4`, **2.21×** — so the floor fixes the *gauge* contamination, not the
> nodal-averaging defect that sent the sampling to DG0 in the first place.
> The two mechanisms are independent and both remain correctly attributed.
> **Finding for a review, not swept in-slot** (per the scope boundary): eight
> other `gauge_penalty=1e-3` call sites remain —
> `tests/solver/test_coil_phantom_magnetostatics.py:52`,
> `test_convergence_diagnostics.py:148`, `test_boundary_condition_selection.py:75`,
> `test_time_harmonic_smoke.py:52`, `tests/materials/test_phantom_material_model.py:165`,
> `tests/post/test_phantom_field_metrics.py:79`,
> `examples/mri/01_coil_phantom_fields.py:302` and `:334`, plus
> `scripts/probes/ops12_probe.py:95`. Inspected, none is a quantitative
> physics gate: the `tests/` ones assert finiteness, structure, or
> material-field values (not solved-field magnitudes against a bound), so
> the sub-floor solve cannot corrupt a gated number there. The one worth a
> decision is **`examples/mri/01`**, which solves both legs sub-floor and
> *does* carry on-record numbers — and `EX-12` was already queued to touch
> that file, so the review may wish to fold it in. **`EX-12` closed
> 2026-08-09 without folding it in**: that chunk is doc-only, and changing
> `gauge_penalty` there changes the on-record numbers, which is a decision
> for the review rather than a hygiene run. **Decision taken, 18:00 review
> 2026-08-09: `EX-13` created and queued** — move both legs of
> `examples/mri/01` to the floor, measure the rank spread there against the
> sub-floor spread in the same slot, and refresh the on-record numbers.
> **`MAG-6` stays ✅** and the ≤ 10% rank-stability claim stays the symmetry
> metric's alone; the centerline's 0.024% at the floor is evidence toward
> extending it, and remains a separate future decision.
>
> *Original scope, retained:*
> *(scoped 2026-08-09, 03:00 review — this is the review decision step 4
escalated, taken: the gate fixture
(`tests/validation/test_coil_phantom_bfield_metrics.py`) solves at
`gauge_penalty=1e-3`, below the validated floor of 1.0, and step 4 measured
that the sub-floor solve is what makes its centerline metric rank-scatter 88%.
A gate should exercise the solver in its validated regime; the change is one
argument, gate-touching, and now licensed to a slot.)*
> Change `gauge_penalty=1e-3 → 1.0` in the `MAG-6` gate fixture **only** —
> the other `1e-3` call sites in the suite (smoke/diagnostic tests, other
> gates) are out of scope; if any of them is also a quantitative gate that
> deserves the same treatment, report it as a finding for a review, do not
> sweep it in-slot. Re-run the gate at `-n 2` and `-n 4`. **Anchor:** the
> gate's own bounds, **unchanged** — mirror-symmetry ≤ 0.35, centerline
> ≤ 0.60 — with step 4's on-record readings at penalty 1.0 as the expected
> values: centerline 0.251272 / 0.250416 / 0.250453 (`-n 1/2/4`, spread
> 0.341%), mirror 0.311226 / 0.311166 / 0.311157 (0.022%). A gate value more
> than ~2% from those (solver noise ceiling: 6.8% run-to-run mesh noise is
> the *old* fixture's number; the step-4 solves repeated to well under 1%)
> is a real finding — report, do not tune. **Negative control:** on record,
> cite not recompute — the sub-floor fixture's 88% centerline rank scatter
> (step 4) and CG1's ~200% (step 1). **Cost:** standard, two commands
> `timeout 180`; gate solves are 10 s at `-n 2/4` on record. **Traps:** do
> not touch `tests/tolerances.py`; DG0 not CG1;
> `evaluate_vector_field_parallel` for points; the `1e-3` grep hits many
> files — edit exactly one. **Does not close / reopen:** `MAG-6` stays ✅;
> the ≤ 10% rank-stability claim stays the symmetry metric's alone (though
> step 4's 0.341% suggests the centerline could earn it later — that is a
> separate, future decision). **Negative result:** a gate that fails at the
> validated floor with bounds untouched is evidence about the fixture or
> the solver, not a reason to revert to 1e-3 silently — report the
> readings, annotate here, known-issues entry if red persists.

**`MAG-6` step 4 — diagnose the centerline metric's 88% rank scatter
(diagnosis only; `MAG-6` stays ✅)** ✅ *(completed 2026-08-09, 00:00 run —
second pass. **The attribution is gauge contamination, and the "rank-safety
defect" the first pass reported is refuted with its own signature measured.**
Five harness logs, standard tier: `20260809T050202Z` (`-n 4`, 12 s),
`20260809T050259Z` (`-n 1`, **152 s** — the missing rung), `20260809T050621Z`
(`-n 2`, 10 s), `20260809T050706Z` (claim-set comparison, 10 s),
`20260809T050838Z` (write-time check, 10 s), `20260809T050930Z` (confirming
run after the probe fix, 9 s), all `_MAG-6.log`. Instrument:
`scripts/probes/mag6_step4_probe.py`, standalone; **no `src/` change, no
tolerance touched, no gate moved.**)*
> **The rank-invariance identity holds — this is the quantitative result.** On
> the gate's own evaluation path, at the validated `gauge_penalty=1.0`, the
> centerline jump ratio reads **0.251272 / 0.250416 / 0.250453** at
> `-n 1 / -n 2 / -n 4`: a three-way spread of **0.341%** against the ≤ 10%
> band. In-fixture control on the same solves, the mirror-symmetry metric:
> 0.311226 / 0.311166 / 0.311157, spread **0.022%**. Mesh fingerprint
> `cells=55784 m1=-4.9768680987…e+00 m2=7.977798997317e+02` identical to 12
> digits at all three rank counts, `-n 1` included.
> **The first pass's defect was the probe's own bug, and it is a √3.**
> `instrumented_eval` inflated `|B|` at any point whose claiming rank held
> *only that one point*: `Function.eval` squeezes to shape `(3,)` for a single
> point, so `rank_vals[k]` was the scalar x-component and
> `values[i] = rank_vals[k]` broadcast it into all three components. The
> write-time check dates the divergence to inside the write loop and gives the
> ratio at both affected points: `4.852607687905e-07 / 2.801654354883e-07` and
> `2.853753669222e-07 / 1.647615449126e-07`, both **1.7320508 = √3 to 8
> digits**. `post/evaluation.py::evaluate_vector_field_parallel` is immune by
> construction — it assigns `values[rank_indices] = rank_values`, and numpy
> broadcasts a `(3,)` row into a `(1, 3)` slice correctly. The claim-set
> comparison rules out non-determinism first: two instrumented calls in one
> process produce **bitwise identical** claim sets (`SAME` at all 9 points,
> `INSTRUMENTED_REPEAT_AGREES = True`), so the divergence is between the two
> code paths, not between two runs.
> **The "second signal" is the same bug, quantified at 42.02%.**
> `EVAL_REPEAT_MAXREL call1_vs_call2 = 4.202249e-01`, `call2_vs_call3 = 0`. It
> fires at `-n 4` and not at `-n 1` or `-n 2` for the obvious reason: only at 4
> ranks does a rank end up holding exactly one centerline point.
> **Therefore step 3's 88% scatter is gauge contamination** — the mechanism the
> first pass believed it had refuted. That refutation compared 0.250406 at
> `-n 2` against 0.328496 at `-n 4`, but the `-n 4` number was a call-1 value
> carrying the √3; the same run's library-path value is 0.250417. At the
> fixture's sub-floor `gauge_penalty=1e-3` the scatter is real; at the
> validated 1.0 it is 0.341%.
> **Probe fixed and confirmed** (`.reshape(-1, 3)`, one line, with the √3
> measurement in the comment): `20260809T050930Z_MAG-6.log` — all four
> evaluations in one process bitwise identical, zero `WRITECHECK` DIFF, metric
> 0.250457 at `-n 4`.
> **For the review — one thing to decide, and one not to.** *Not* to scope: a
> fix chunk on the DG0 evaluation path; there is no defect there. *To* decide:
> the gate fixture solves at `gauge_penalty=1e-3`, below the validated floor of
> 1, which is what makes its centerline metric rank-scatter 88% — whether to
> re-point the fixture at the validated floor is a gate-touching change and so
> a review's, not a slot's. `MAG-6` stays ✅ either way: the 0.60 bound is
> untouched and passes at every rank count measured, and the ≤ 10%
> rank-stability claim remains the symmetry metric's alone.
> **known-issues:** the first pass's "Rank-dependent DG0 centerline sample"
> entry is **retired** in this commit, refutation recorded in place.
>
> *First-pass annotation, retained for the record:*
> *(attempted 2026-08-09, 22:30 run —
**the attribution is delivered and both proposed mechanisms are refuted, but
the `-n 1` rung was not run and the mechanism that remains is a defect, not an
explanation.** Six harness logs, 9–12 s each, standard tier:
`20260809T033322Z` / `…033350Z` / `…033403Z` / `…033514Z` / `…033555Z` /
`…033608Z`, all `_MAG-6.log`. Instrument:
`scripts/probes/mag6_step4_probe.py`, standalone, touches no `src/` and no
tolerance.*
> **Not mesh noise.** The mesh fingerprint — global cell count plus reduced
> midpoint moments — is `cells=55784, m1=-4.9768680987…e+00,
> m2=7.977798997317e+02` in every run at `-n 2`, `-n 4`, and a fixed-rank
> repeat: identical to **12 significant digits**. Step 3's 6.8% "run-to-run
> mesh drift" attribution does not survive; the mesh is reproducible.
> **Not partition-owned sampling.** `CENTERLINE_MULTICLAIM = 0/9` and
> `CENTERLINE_MULTICELL = 0/9` at both rank counts — each point is claimed by
> exactly one rank and collides with exactly one cell, so the `links[0]` and
> rank-order-overwrite ambiguities in `evaluate_vector_field_parallel` never
> fire. The **chosen owning-cell midpoints are identical across `-n 2` and
> `-n 4` for all nine points**, to 9 decimals.
> **Not gauge contamination** (a mechanism neither step 3 nor this plan named,
> surfaced by the fixture's own `GaugeContaminationWarning`: it solves at
> `gauge_penalty=1e-3`, below the validated floor of 1). Re-run at 1.0 the
> scatter persists — jump ratio **0.250406** at `-n 2` vs **0.328496** at
> `-n 4`, 31%.
> **What is left is a rank-safety defect.** At `gauge_penalty=1.0` eight of
> nine centerline points are rank-invariant to ~5 significant digits; the whole
> metric spread is set by **one point, i=1 at z = -0.0225 m**, reading
> `2.813455e-07` at `-n 2` and `4.852531e-07` at `-n 4` — **72% apart in the
> same cell, on the same mesh**. The rank-invariance identity this step was
> anchored on is therefore *violated*, and violated locally.
> **In-fixture control, same solves:** the mirror-symmetry metric reads
> 0.306591 / 0.309126 / 0.310501 / 0.311161 / 0.311162 across all five runs — a
> **0.15% spread** against the centerline metric's 31%. The defect is localised
> to the centerline sample, not global to the solve.
> **Second signal, undiagnosed:** the probe evaluates the same unchanged
> `b_dg0` at the same points twice in one process and compares exactly; the two
> agree at `-n 2` and **disagree at `-n 4`**. Two identical evaluations in one
> run should be bitwise equal. The probe prints only the boolean, not the
> magnitude — measuring that is the cheapest next step.
> **Not done, and why:** the `-n 1` rung (144 s on record) was not run — the
> slot ended first; the attribution above rests on `-n 2` vs `-n 4` plus one
> fixed-rank repeat, which is sufficient to refute the two proposed mechanisms
> but not to characterise the defect's rank dependence. **No gate moved and no
> fix was attempted** — `MAG-6` stays ✅, the 0.60 bound is untouched and passed
> at every rank count measured, and per this step's own terms a real reduction
> defect "gets a known-issues entry and a fix is scoped by a review, not
> improvised in-slot". The known-issues entry is written. **For the review:**
> the follow-up is a fix chunk on the DG0 evaluation/interpolation path, not
> another diagnosis of the metric.*
>
> *Original plan, retained verbatim:*
> Step 3 landed the DG0 centerline jump-ratio metric passing its 0.60 bound at
> all three rank counts but rank-scattered **88%** (0.473300 / 0.268765 /
> 0.251746 at `-n 1/2/4`) where the mirror-symmetry metric on the *same
> solves* spreads 7.00%. Step 3 also measured two candidate mechanisms without
> separating them: DG0 point sampling is sensitive to which cell owns a point
> (rank-partition dependent), and the meshing is not bit-reproducible run to
> run (6.8% metric drift between identical `-n 2` runs). **The job: separate
> those two, on the recorded fixture, without touching the gate.** Print the
> centerline sample points' owning-cell ids (or a rank-ownership fingerprint)
> and the per-point sampled values at `-n 1/2/4` plus one repeat at a fixed
> rank count; attribute the scatter — partition-owned (values differ only
> where ownership differs), mesh-noise-owned (repeat at fixed ranks moves as
> much as ranks do), or a genuine rank-safety defect in the metric's reduction
> path (the `PORT-1` step 3b-viii family — values that should be identical
> after reduction are not). **Anchor:** a rank-invariance identity — after a
> correct global reduction, a scalar metric on identical input must reproduce
> across rank counts; quantify the residual scatter attributable to each
> mechanism, with the mirror metric's 7.00% spread on the same runs as the
> in-fixture control (same solves, same build — isolates the metric code
> path). **Negative control:** on record, cite not recompute — CG1's ~200%
> scatter and the 0.705/0.732 `-n 4` failures
> (`20260808T170334Z_MAG-6-step3-gate-n4.log`). **Cost:** standard tier —
> the gate solves are 10 s at `-n 2/4` and 144 s at `-n 1` on record; four
> commands, `timeout 180` each. **Traps:** DG0 not CG1; point evaluation
> through `evaluate_vector_field_parallel`, never rank-local eval; reduce
> before asserting; stale FFCx lock after a kill; do not touch
> `tests/tolerances.py`. **Does not close / reopen:** `MAG-6` stays ✅ — the
> ≤ 10% rank-stability claim is the symmetry metric's alone and this step
> does not extend it; no bound moves in-slot. **Negative result:** an
> inconclusive attribution is still a finding — report the per-mechanism
> numbers, annotate here; if a real reduction defect surfaces, it gets a
> known-issues entry and a fix is scoped by a review, not improvised in-slot.

**`MAG-13` step 2 profile — EXECUTED 2026-08-11 (21:00 slot): the map is
measured — the error goes as 1/r *and* as a per-cell staircase; the near-wire
hint survives, but the mechanism is the cell-wise-constant B, not a
near-wire solve defect.** ✅
*(**Restored 🧪 → ✅ 2026-08-12, 07:30 slot** by the re-gate step below: the
probe's verdicts now drive its exit code, the smoke rung exits 1 on 0/4 gates,
and the real rung re-solves to 4/4 with every number below reproduced
digit-identically — `20260812T123255Z_MAG-13-step2-regate-n8.log`, exit 0,
263 s. The demotion text is retained verbatim for the audit trail.)*
*(Demoted ✅ → 🧪 by the 2026-08-12 03:00 review audit, §4(c): every
PASS/FAIL in `mag13_step2_profile.py` is print-only — `main()` returns 0
unconditionally, and the smoke log demonstrates it: its identity and control
checks FAIL by construction and it still exits 0, so the exit code carries no
information in either log. The numbers below were audited digit-faithful to
`20260812T020247Z_MAG-13-step2-profile-n8.log` and stand as *measurements*;
the route reasoning survives. Restoration path is §9 item 2: add enforced
gates to the probe and re-run once. Two audit corrections folded into the
text below: the staircase groups are identical to all printed digits (5
significant figures — "bit-identical" overstated the evidence), and the
mechanism wording — `A` is lowest-order N1curl, not Lagrange P1; its curl is
cell-wise constant either way, so the finding stands.)*
> **Measured** (`20260812T020247Z_MAG-13-step2-profile-n8.log`, exit 0,
> **269 s** harness-wall, `-n 8`, real build, container `timeout 590`,
> foreground; instrument `scripts/probes/mag13_step2_profile.py`, standalone,
> touches no `src/`, no `tests/`, no tolerance).
> **Fixture identity first, both PASS:** **1 097 873 cells** digit-identical
> to record, ten-point relative L2 **5.6494% vs 5.6494%** reproducing every
> printed digit; azimuthality `B_z` 1.853e-07 / 3.333e-05 = 5.6e-03 against
> the 0.10 bound, also digit-identical. Mesh + solve **267.0 s** (275.3 s on
> record), 4 391 492 global dofs.
> **Negative control PASS on all four recorded radii** — dense vs the
> ten-point table: 9.46/9.46 (−0.003 pp), 6.33/6.33 (−0.000 pp), 0.33/0.33
> (−0.004 pp), 1.40/1.40 (−0.003 pp). The dense profile does not contradict
> its own coarse sample.
> **The profile** (45 radii, 0.006 → 0.028 m, 0.5 mm steps, all 45 inside the
> mesh, `evaluate_vector_field_parallel`), by band — relL2 / mean|rel| /
> max|rel|: near-wire 2.0a–3.3a **5.4939% / 5.0527% / 9.4574%**; mid 3.3a–5.3a
> 4.1411% / 3.3406% / 6.5574%; outer 5.3a–8.0a 2.8345% / 2.2152% / 5.9029%;
> wall band 0.8R–0.93R 2.3341% / 2.0972% / 3.8259%. Worst radius r = 0.0080 m
> (2.67a) at 9.4574%. **The near-wire hypothesis is confirmed and quantified:**
> the log-log slope of |rel| vs r over [0.006, 0.024] is **−1.069**, i.e.
> relative error ∝ 1/r to within 7% of an exact inverse law, and the wall band
> is the *quietest* of the four — the error is not boundary-dominated.
> **The second, unasked-for finding — and the one that should shape the mesh
> decision: the profile is a staircase, not a curve.** Adjacent radii return
> `|B|_num` identical to all printed digits in eight groups (0.0070/0.0075 =
> 2.7490e-05; 0.0080/0.0085 = 2.2636e-05; 0.0105/0.0110/0.0115 = 1.7862e-05;
> 0.0120/0.0125 = 1.6148e-05; 0.0145/0.0150; 0.0160/0.0165; 0.0175/0.0180/
> 0.0185; 0.0190/0.0195/0.0200), while the closed form varies across
> each group. That is exactly the fixture's own construction: `A` is
> lowest-order N1curl, so `B = ∇ × A` is **cell-wise constant** —
> `compute_b_field` interpolates it
> into DG1 (`solvers.py:637`), but a constant is a constant, and the DG1
> container carries no gradient. Consequently the signed error **alternates
> sign within every group** (e.g. −9.46% at 0.0080 then −3.80% at 0.0085;
> −3.11% then +0.93%): each sample's error is dominated by *where inside its
> cell it sits*, not by a smooth solution defect. Sampling-position noise of
> this kind is the reason the ten-point table looked jagged (9.46% at 0.0080
> next to 0.33% at 0.0200).
> **Both facts compose, and they say the same thing about the mesh.** A
> cell-wise-constant B on a mesh of size h samples an exact field with
> |dB/dr| = B/r, so the local relative error is O(h/r) — which *is* the
> measured −1.069 slope, and is also why the global rate came out ~1.1–1.17
> (first order in h) rather than 2. Halving h halves the error everywhere;
> halving it only near the wire buys the same reduction where the error is 5–9%
> and nothing where it is already 0.3–2%. **Graded refinement is therefore the
> right route on this evidence** — the review's provisional call survives the
> map. Indicative arithmetic, *not* a measurement: taking the 4.7235% dense
> relL2 over the recorded span and the measured O(h/r), refining only
> r < 0.010 m (9 of 45 radii, band relL2 5.4939%) by 2× removes ~half of the
> dominant band's contribution — enough to cross 5% only if the mid band is
> also touched. The cheaper, *better-targeted* alternative the staircase
> surfaces and this step does **not** cost out: recover B at higher order (P2
> `A`, or a projection of `curl A` into a continuous space) so B is no longer
> cell-constant. The §7 note above records that degree 2 was measured to
> *diverge* at res = 0.003 on this fixture and is not a free swap.
> **Does not close / does not reopen:** `MAG-13` stays ✅ at its recorded
> numbers; no mesh changed, no graded mesh built, no bound moved, no `src/`
> or `tests/` file touched. §9 item 5 (the uniform 1.50 M-cell rung) is *not*
> retired by this — it remains a real measurement of the brute-force route,
> and its predicted cost is unchanged.
> **For the review, one thing to decide:** whether the next `MAG-13` step is
> a graded mesh at fixed B-recovery (the route this map endorses) or a
> higher-order B recovery at fixed mesh (the route the staircase suggests and
> nobody has priced). Both are mesh/gate-touching and so a review's call, not
> a slot's.
>
> *Original plan, retained verbatim:*
*(scoped 2026-08-11, 18:00 review — the route decision the step-2 run asked
for. Graded refinement stays the named cheaper route, but the run's
near-wire hint rests on ten sample points; this step buys the map before
any mesh is committed to grading. Queued as §9 item 2; the uniform rung 3
below is the declared spare, §9 item 5.)*
> Re-run the h ≈ 0.00125 rung exactly as measured (mesh + solve **275.3 s
> on record** at `-n 8`, `20260811T200040Z_MAG-13-step2-solve-n8.log`) and
> sample the error-vs-radius profile densely: **≥ 40 radii spanning
> r ∈ [0.006, 0.028]** through `evaluate_vector_field_parallel`, replacing
> the ten points on record. Real build, **no complex mode**; foreground,
> tool `timeout` 660000 ms, container `timeout 590`. **Anchor:** the
> straight-wire closed form
> `utils/analytical.py::straight_wire_magnetic_field` (B_θ = μ₀I/2πr) per
> radius; fixture identity first — cell count digit-identical to
> **1 097 873** and global relative L2 reproducing **5.6494%** to its
> printed digits before any profile claim. **Negative control:** the
> ten-point table on record (9.46% at r = 0.0080, 6.33% at 0.0100, 0.33%
> at 0.0200, 1.40% at 0.0240) — the dense profile must reproduce those
> radii; a profile that contradicts its own coarse sample is a bug, not a
> finding. **Cost:** heavy; 275.3 s mesh + solve on record, sampling
> seconds. **Traps:** never background; stale FFCx lock; point evaluation
> through `evaluate_vector_field_parallel`, never rank-local eval;
> `J·n ≠ 0` at the end caps stands unmeasured. **Does not close / does not
> reopen:** `MAG-13` stays ✅; no mesh change, no graded mesh in-slot —
> this buys the map, a review scopes the mesh against it. **Negative
> result:** a flat or wall-dominated profile refutes the near-wire
> hypothesis and the uniform rung (below) becomes the honest route; report
> the profile table, annotate here, stop.

**`MAG-13` step 2 profile re-gate — make the map's checks bite, restore the
✅** ✅
**EXECUTED 2026-08-12 (07:30 slot) — the gates bite and the fixture holds; the
profile step above is restored 🧪 → ✅.**
> **Negative control first, and it fired**
> (`20260812T123217Z_MAG-13-step2-regate-smoke.log`, **exit 1**, 27 s
> harness-wall, `-n 8`, `MAG13_STEP2_RES=0.0025`): **0/4 gates pass** —
> cells 145 884 vs 1 097 873, ten-point relL2 12.7485% vs 5.6494%, negative
> control FAIL, shape FAIL (slope **−0.244**, outside [−1.3, −0.9]; the
> near-wire > wall half PASSed, 12.2034% vs 7.5104%). This is the same rung
> whose 2026-08-12 log FAILed print-only and exited 0 — the defect the audit
> named is demonstrably fixed, and the coarse rung's −0.244 slope also shows
> the shape pin is not vacuous.
> **Real rung** (`20260812T123255Z_MAG-13-step2-regate-n8.log`, **exit 0**,
> **263 s** harness-wall, mesh+solve 261.5 s, `-n 8`, real build, container
> `timeout -k 30 590`, foreground): **4/4 gates pass**, and every measurement
> reproduces the record digit-for-digit — 1 097 873 cells / 4 391 492 global
> dofs, ten-point relL2 **5.6494%**, azimuthality 5.6e-03 vs the 0.10 bound,
> all four control radii inside ±0.05 pp, bands 5.4939% / 4.1411% / 2.8345% /
> 2.3341%, dense span 4.6500%, worst radius 0.0080 m at 9.4574%, log-log
> slope **−1.069**. Nothing drifted since 2026-08-12, so the negative-result
> branch (known-issues entry) did not apply.
> **What changed:** `scripts/probes/mag13_step2_profile.py` only — four
> named gates, the ±0.05 pp control band lifted to a constant, and the
> verdict broadcast from rank 0 so every rank exits with the same code
> (non-rank-0 ranks now wait on a matching `bcast` instead of returning 0
> early). No new physics, no new sampling, no `src/`, no `tests/`, no
> tolerance.
*(scoped 2026-08-12, 03:00 review — the restoration path for the audit
demotion above. Queued as §9 item 2.)*
> Edit `scripts/probes/mag13_step2_profile.py` so its already-computed
> verdicts gate the exit code — no new physics, no new sampling: `main()`
> returns nonzero unless (1) cell count == **1 097 873** exactly, (2) the
> ten-point relative L2 reproduces **5.6494%** to its printed digits,
> (3) all four negative-control radii agree with the recorded table within
> the probe's existing ±0.05 pp print band, and (4) a profile pin authored
> from the on-record map: log-log slope of |rel| vs r over [0.006, 0.024]
> in **[−1.3, −0.9]** and near-wire band relL2 > wall band relL2 (measured
> −1.069 and 5.4939% vs 2.3341%; the pin asserts the *shape*, generously,
> not the digits). Then one re-run at `-n 8`. **Anchor:** the closed form
> per radius plus the fixture-identity reproduction, now enforced.
> **Negative control — free, and mandatory:** the smoke rung
> (`MAG13_STEP2_RES=0.0025`, 26 s on record) must now **exit nonzero**,
> demonstrating the gates bite where they FAILed print-only on
> 2026-08-12; run it first, expect exit ≠ 0, record it. **Cost:** heavy;
> 269 s harness-wall on record for the real rung + ~30 s smoke; `-n 8`,
> foreground, container `timeout -k 30 590`. **Traps:** the profile step's
> list verbatim, plus the new `-k 30`. **Closes:** flips the profile step
> above 🧪 → ✅ citing both logs (the failing smoke IS the §4 negative
> control). **Does not reopen:** `MAG-13` chunk untouched. **Negative
> result:** the real rung failing its own reproduction says the fixture
> drifted since 2026-08-12 — that is a known-issues entry, not a band
> adjustment; report, keep 🧪, stop.

**`MAG-13` step 2c — the third rung, and the CG1 rate is second order** ✅
**EXECUTED 2026-08-13 (22:30 slot): the intermediate rung lands on the
p = 2 line. CG1 relL2 reads 3.6530% at h = 0.0017678 where the two-point
observation predicted 3.9207%, and the three-point least-squares rate is
p = 2.003 against the observation's 2.00; the DG1 path reads 7.5952%
(predicted 7.1946%) at p = 1.217 against 1.22. Step 2b's rate was not
an artefact of two points.**
*(`MAG-13` stays ✅ at its recorded numbers — nothing in `src/` or `tests/`
changed, no mesh in any test changed, no bound moved. Gate adoption —
moving `compute_b_field` to CG1 recovery — remains the **weekly review's**
call, now with the third point in hand; this step buys the point, it does
not spend it.)*
> **Identity first, and it reproduced exactly**
> (`20260813T033235Z_MAG-13-step2c-smoke.log`, **exit 0**, 26 s
> harness-wall, `-n 8`, `MAG13_STEP2C_RES=0.0025`): **3/3 gates** —
> 145 884 cells, DG1 span **10.9806%**, CG1 span **7.8411%**, each
> digit-identical to the step-2b smoke log. The imported machinery is the
> step-2b machinery: `scripts/probes/mag13_step2c_third_rung.py` restates
> nothing, importing `_solve_straight_wire_keep_solver`,
> `_project_curl_to_cg1`, `_sample`, `_bands` and the 45-radius grid
> constants from `mag13_step2b_recovery`, so a drift between the steps
> cannot pass silently. *(Deviation from the §9 recipe, declared: the item
> said "extend `mag13_step2b_recovery.py`". A sibling module that imports
> it was preferred so the recorded step-2b gates — which are pinned to the
> 1.1 M-cell rung — could not be perturbed by a rung-selection edit. The
> GATE-4 nit fix the item required does ride in the step-2b file, as
> instructed.)*
> **The new rung** (`20260813T033311Z_MAG-13-step2c-rung3.log`, **exit 0**,
> **78 s** harness-wall, mesh+solve 75.5 s, `-n 8`, real build, container
> `timeout -k 30 590`, foreground): **408 079 cells** / 1 632 316 global
> DG1 dofs — **1.051×** the ~388 k the declared cube-scaling assumption
> predicted, so that assumption held to 5%. All 45 dense radii inside the
> mesh for both recoveries. The CG1 projection again costs nothing: 11 CG
> iterations, **0.82 s**, **1.1%** of the solve (step 2b: 2.71 s, 1.0%).
> **The three-point table** (relL2 over the recorded metric span; the outer
> two rows are **cited from the step-2b logs, not re-solved** — the 1.1 M
> rung's 271 s is a solve this step did not need to buy):
>
> | h [m] | cells | DG1 relL2 | CG1 relL2 |
> |---|---|---|---|
> | 0.0025 | 145 884 | 10.9806% | 7.8411% | *(record)* |
> | 0.0017678 | 408 079 | **7.5952%** | **3.6530%** | *(this run)* |
> | 0.00125 | 1 097 873 | 4.7235% | 1.9557% | *(record)* |
>
> **The reading:** least-squares over three points gives CG1 **p = 2.003**
> and DG1 **p = 1.217** — both within 0.005 of the two-point observations
> they were fitted to test. The two-point p = 2.00 was **not**
> pre-asymptotic in the sense that would have voided it.
> **The honest caveat, and it is the one the review should weigh:** the
> *pairwise* rates are not flat. CG1 reads **2.204** coarse→new and
> **1.803** new→fine; DG1 reads 1.064 then 1.370. A ±0.20 spread about the
> fitted 2.003 means three points constrain the CG1 rate to roughly
> "second order, ±10%", not to 2.00 as a converged constant — and the
> spread's *sign* (steeper first, shallower second) is what a solution
> approaching a floor looks like, not what a clean asymptotic rate looks
> like. The measured level supports the same caution: CG1 came in
> **0.2677 pp below** the p = 2.00 extrapolation (3.6530% vs 3.9207%),
> i.e. 6.8% low.
> **The band-flat floor survives the rung.** Per band (DG1 → CG1 relL2):
> near-wire 8.4299% → **3.0688%** (−5.3610 pp); mid 7.3593% → 4.5303%;
> outer 4.5173% → 4.1168%; wall 4.2106% → **4.2842%** (+0.0736 pp — the
> only band where CG1 does not help, as at the fine rung). CG1 is again
> **band-flat**, here at ≈ 3–4.5% against the fine rung's ≈ 2.0%: the
> O(h/r) radial structure is removed at this rung too, and the residual
> scales with h rather than sitting at a fixed floor. That is the
> substantive addition to step 2b — a *fixed* ≈ 2% bias would not have
> halved.
> **Negative control, executed not cited:** the DG1 path on this same
> rung, same solve, same sampler, same 45 points. The CG1/DG1 gap
> persists (3.6530% < 7.5952%, −3.94 pp) and CG1 improves on the smoke
> rung — both asserted, and the gate reads them as its exit code. Step
> 2b's finding is not rung-specific.
> **The §7 nit is fixed** (18:00 review, advisory): the step-2b probe's
> GATE-4 failure-path detail string is now conditional — it prints
> "VARIES … inside at least one of the eight recorded groups" when the
> gate fails, instead of the static passing claim. Boolean and exit code
> were always correct; only the text misled, and only on the failure path.
> **Does not close / does not reopen:** `MAG-13` stays ✅;
> `compute_b_field` untouched; §9 item 5 (the 1.50 M-cell uniform rung)
> is not retired. **For the weekly review:** the third point is in, and
> it says second order — but read it with the pairwise spread beside it.
> If the graded route is re-derived (step 2b's hand-off), it is now being
> re-derived against a *second-order, radially flat* error map, not the
> first-order near-wire-concentrated one it was originally scoped
> against.

**`MAG-13` step 2b — price higher-order B recovery on the solved rung** ✅
**EXECUTED 2026-08-12 (13:30 slot): the recovery route is bought and it is
cheap — CG1-projected `curl A` reads 1.9557% where the DG1 interpolation
reads 4.7235%, for 2.71 s on top of a 271.1 s solve. The < 5% wire is
reached at the *existing* mesh, and the staircase breaks in all eight
groups.**
*(`MAG-13` stays ✅ at its recorded numbers — nothing in `src/` or `tests/`
changed, no mesh changed, no bound moved. This prices a route; it does not
adopt one. The graded route is **not** retired: it remains the only lever on
the ~2% floor this step exposes.)*
> **Negative control first, and it fired**
> (`20260812T183247Z_MAG-13-step2b-smoke.log`, **exit 1**, 30 s harness-wall,
> `-n 8`, `MAG13_STEP2_RES=0.0025`): **0/4 gates pass** — 145 884 cells vs
> 1 097 873, ten-point relL2 12.7485% vs 5.6494%, dense bands FAIL, and the
> DG1 staircase is **not** flat at the coarse rung, so GATE 4 is not vacuous.
> The probe's verdicts drive its exit code from the outset (the step-2
> re-gate's lesson, applied at authorship rather than after an audit).
> **Real rung** (`20260812T183329Z_MAG-13-step2b-n8.log`, **exit 0**,
> **276 s** harness-wall, mesh+solve 271.1 s, `-n 8`, real build, container
> `timeout -k 30 590`, foreground; instrument
> `scripts/probes/mag13_step2b_recovery.py`, standalone, touches no `src/`,
> no `tests/`, no tolerance): **4/4 gates pass** and the DG1 path reproduces
> the record digit-for-digit — 1 097 873 cells / 4 391 492 global DG1 dofs,
> ten-point relL2 **5.6494%**, dense span **4.7235%**, near-wire **5.4939%**,
> wall **2.3341%**. That reproduction *is* the declared negative control: the
> two recoveries are scored on one solve, one sampler, one point set.
> **The CG1 projection costs nothing**: L2-project `curl A` into vector CG1
> (602 052 global dofs, `cg` + `gamg`, rtol 1e-12) converges in **11 CG
> iterations, 2.71 s** — **1.0%** of the solve it post-processes, versus the
> 1.37× cell count (~380–450 s predicted) that §9 item 5's brute-force rung
> would spend to reach the same target.
> **The reading, pre-registered and met** — CG1 relL2 **1.9557%** over the
> recorded metric span against the **< 5.00%** mark (full dense span
> 1.9590% vs DG1 4.6500%). Recovery alone reaches the target at the existing
> mesh, with **2.77 pp** to spare.
> **Per band (DG1 → CG1 relL2), and this is the shape of the finding:**
> near-wire 5.4939% → **1.9099%** (−3.5840 pp); mid 4.1411% → 2.0511%
> (−2.0900 pp); outer 2.8345% → 2.0646% (−0.7699 pp); wall 2.3341% →
> 2.0441% (−0.2900 pp). The gain is monotone in how much error the band
> held, and the CG1 residual is **band-flat at ≈ 2.0%** — the measured
> O(h/r) structure the profile step mapped (slope −1.069) is **removed**,
> exactly as the cell-wise-constant-B mechanism predicts, and what is left
> is a nearly uniform ≈ −2% bias, same sign at every radius. Finite wire
> length does not own it: L/√(L²+4r²) is −3.9% at r = 0.028 m but < 0.02%
> at the near-wire radii, where the bias is already 1.8%.
> **The floor is h-convergent, and at rate ≈ 2** — a two-point reading the
> slot's own two logs supply for free: the smoke rung (h = 0.0025, same
> probe, same 45 radii, identity gates deliberately failing because it is a
> different mesh) reads CG1 **7.8411%** against this rung's **1.9557%**, a
> ratio of **4.01** over one halving, i.e. **p = 2.00**, where the DG1 path
> over the same two rungs reads 10.9806% → 4.7235% (ratio 2.32, p = 1.22).
> Continuous recovery does not merely shift the error down, it restores the
> **second-order** rate the DG1 container was throwing away. Two points is
> a rate with no redundancy — it is an observation, not a fitted rate, and
> a third rung would settle it.
> **The staircase breaks, 8/8.** Inside every one of the eight recorded
> groups the DG1 values are flat to five significant figures (control,
> reproduced) while the CG1 values are **distinct** — e.g. 0.0105/0.0110/
> 0.0115 reads DG1 1.7862e-05 three times, CG1 1.8717e-05 / 1.7887e-05 /
> 1.7058e-05. The continuous container carries the gradient the DG1 one
> could not; sampling-position noise is gone.
> **Does not close / does not reopen:** `MAG-13` stays ✅ at its recorded
> numbers; `compute_b_field` is untouched — adopting CG1 recovery in `src/`
> is a gate-touching change and a review's call, not a slot's. §9 item 5
> (the 1.50 M-cell uniform rung) is not retired: it measures the *solve*
> route and remains a real measurement, though this step makes it the
> expensive way to the same number.
> **For the review, two things to decide:** (1) whether
> `compute_b_field`/`MAG-13`'s gate move to a continuous recovery — the
> 2.71 s price and the 8/8 staircase break argue yes, but every
> B-consuming test's recorded number would shift and that is a
> re-gating exercise, not an edit; (2) whether the ≈ 2% band-flat floor
> gets a third rung to confirm the p = 2.00 two-point reading — if it
> holds, the *cheap* route to any future accuracy target on this fixture
> is continuous recovery plus uniform refinement at second order, and the
> graded-mesh route (scoped against a first-order, near-wire-concentrated
> error map that this step just dismantled) should be re-derived before it
> is built.
>
> **Review decision, 2026-08-12 (18:00 daily review):** (1) gate adoption
> is **deferred to the weekly review pending a third rung** — the p = 2.00
> reading is a two-point observation, and re-gating every B-consuming
> test's recorded numbers on an observation is backwards; step 2c buys the
> third point first. (2) **Step 2c commissioned** (§9 item 3): one
> intermediate rung at h = 0.0017678 (√2 between the recorded rungs),
> both recoveries on the recorded 45-radius grid, smoke-rung identity
> gates enforced; full recipe in the §9 item. Audit note (18:00 review,
> this step COMPLIANT on all §4 criteria): one advisory nit — the probe's
> GATE-4 failure-path detail string is static, printing "flat to 5 sig
> figs inside all eight recorded groups" even when the gate fails
> precisely because it is *not* flat
> (`scripts/probes/mag13_step2b_recovery.py`, ~line 419); the boolean and
> exit code are correct, only the failure-path text misleads. Fix rides
> with step 2c's probe edit, never its own commit.
>
> *Original plan, retained verbatim:*
*(scoped 2026-08-12, 03:00 review — the route the staircase surfaced and
nobody has priced; decision deferred by the profile entry's "for the
review" note, resolved as: measure (b) before committing any mesh to
grading, because it attacks the measured O(h/r) mechanism directly and
costs one slot. Queued as §9 item 4; independent of the re-gate item — it
carries its own identity checks.)*
> On the h = 0.00125 rung (mesh + solve 267.0 s on record at `-n 8`),
> compute a **continuous-recovery B**: L2-project `curl A` into CG1
> (one mass solve, `cg` + `gamg` per `post/current_divergence.py`'s
> pattern) beside the existing DG1 interpolation, and evaluate **both**
> recoveries on the recorded 45-radius grid through
> `evaluate_vector_field_parallel`. **Anchor:**
> `utils/analytical.py::straight_wire_magnetic_field` per radius; fixture
> identity enforced first (cell count 1 097 873, DG1 ten-point relL2
> reproducing 5.6494% to printed digits — exit nonzero on miss). The
> reading: dense relL2 and per-band table for CG1-recovered B beside the
> DG1 record (4.7235% dense; 5.4939% near-wire / 2.3341% wall), and
> whether the staircase groups break (adjacent radii in the eight recorded
> groups must return *distinct* CG1 values). **Pre-registered read:**
> CG1 relL2 < **5.00%** on the dense grid says recovery alone reaches the
> target without any new mesh — report beside the graded-route arithmetic;
> ≥ 5.00% still prices the route. **Negative control:** the DG1 path's own
> numbers, reproduced in the same run (that is the identity check).
> **Cost:** heavy; 267 s solve + one CG1 mass solve (seconds at 4.4 M
> dofs with `gamg` — if it exceeds 60 s, print the KSP time and continue);
> `-n 8`, foreground, container `timeout -k 30 590`. **Traps:** the
> profile step's list; do **not** confuse this with the recorded
> degree-2 *solve* divergence (`test_straight_wire.py:96` — that was P2
> `A`, a different route; this projects the existing solution and touches
> no solve space); projection is a fresh FFCx form — clear a stale lock
> after any kill. **Does not close / does not reopen:** `MAG-13` stays ✅
> at its recorded numbers; no mesh change, no export change, no bound
> moved; the graded route is not retired by any outcome. **Negative
> result:** CG1 recovery that does not beat DG1 (Gibbs-like overshoot at
> the wire is the plausible mode) makes graded refinement the sole live
> route — report both tables, annotate here, stop.

**`MAG-13` step 2 rung 3 — EXECUTED 2026-08-13 (09:00 slot): the < 5% wire
lands by brute force at 3.7372%, and it beat its own prediction.** ✅ *(the
rung was priced at exactly 5.00%; it measured 3.74%. `MAG-13` stays ✅ at its
recorded numbers, exactly as the entry pre-committed — this annotates, it does
not reopen, and it does not retire the graded route.)*
> **Measured** (`20260813T140146Z_MAG-13-step2-rung3-n8.log`, **exit 0**,
> **423 s** harness-wall, `-n 8`, real build, container `timeout -k 30 590`,
> foreground): mesh + solve **420.3 s**, **1 520 152 cells / 6 080 608 global
> dofs**, relative L2 error **3.7372%** against
> `straight_wire_magnetic_field` — **gate green at the unmoved < 5.00%**,
> exit code carried by the gate. Azimuthality control **3.057e-02** vs the
> unmoved 0.10 bound (`B_z` max 1.019e-06 vs `|B|_ref` 3.333e-05). Cost
> landed inside the declared 380–450 s estimate at its top end, with 167 s of
> margin on the window.
> **The prediction was conservative and that is the finding.** The rung was
> chosen so that the measured two-rung rate 1.174 prices it at exactly 5.00%;
> it came in **1.26 pp better**. Rates: two-rung vs the 0.0025 record
> **1.540**, three-rung log-log fit over 0.0025 / 0.00125 / 0.001127
> **1.407**, both above the 1.174 that sized the rung and the 1.10 landed
> with `MAG-13`. The pairwise 0.00125 → 0.001127 rate prints as **3.989** —
> read it as noise, not superconvergence: the h ratio is 1.109, so
> log(ratio) = 0.104 and a 0.1 pp wobble in either error moves the exponent
> by ~0.2; the three-rung fit is the defensible number. **The observed rate
> is not a converged constant** (1.10 → 1.174 → 1.407 as h falls), the same
> caveat step 2c recorded for its p = 2.003.
> **Weakens the rung-2 "residual concentrated near the wire" hypothesis.**
> Per-radius errors are again non-monotone in r (6.03% at r = 0.0080, 4.27%
> at 0.0160, 3.47% at 0.0200, 0.38% at 0.0220), but the far radii got
> *worse* than rung 2's (0.33% at 0.0200, 1.40% at 0.0240) while the total
> fell — pointwise per-radius error at fixed r is not monotone in h, so the
> ten-point pattern is mesh-realization noise rather than a spatial error
> map. Rung 2's hypothesis was flagged as "a hypothesis from ten sample
> points, not a measurement"; this rung is the evidence that the ten points
> do not support it. Graded refinement remains the cheaper route, still a
> review's to scope; nothing about its motivation is settled here.
> **Probe change, landed with the run:** `scripts/probes/mag13_step2_probe.py`
> gains the two recorded rung-2 constants (cited, never recomputed), the
> pairwise + three-rung rate prints, and an explicit exit-code gate on the
> pre-registered < 5.00% / ≤ 0.10 pair. Neither bound moved. At the default
> h = 0.00125 the probe now exits 1 — correct: that rung is a measured miss
> on the record.
>
> *Original plan, retained verbatim:*
> *(scoped 2026-08-11, 18:00 review — the spare, §9 item 5; the other route
to the same question as the profile step above. A slot reaching it runs it
as written even if the profile already landed — a completed rung is a real
measurement either way.)*
> Mesh + one solve of **h ≈ 0.001127** (~1.50 M cells at 1.37× the
> 1 097 873 on record — the rung the measured rate 1.174 prices at exactly
> 5.00%), `-n 8`, real build, foreground, tool `timeout` 660000 ms,
> container `timeout 590`. **Anchor:**
> `utils/analytical.py::straight_wire_magnetic_field` (B_θ = μ₀I/2πr),
> target **< 5.00%** relative L2 at the rung; print the three-rung observed
> rate beside 1.174 and the landed 1.10; azimuthality control ≤ 0.10 as on
> record. **Negative control:** `MAG-13`'s analytic-Dirichlet-vs-plain-box
> separation and the rate fit, on record, cited never recomputed. **Cost:**
> heavy; **estimate 380–450 s if cost scales with cell count — an
> assumption, declared**: the 590 s window holds it only with thin margin,
> and **exit 124 is the measurement** ("~1.5 M cells does not fit the
> window at `-n 8`"), not a failure. **Traps:** the profile step's list
> verbatim. **Does not close / does not reopen:** `MAG-13` stays ✅ at its
> recorded numbers either way; a green < 5% annotates this entry and the
> MAG follow-up bullet; it does not retire the graded route, which stays
> the cheaper path for any further rung. **Negative result:** still > 5%
> on-rate, or exit 124, says the uniform route is exhausted inside the
> window — graded refinement becomes the only route; report the measured
> error and cost beside the prediction, annotate here, stop.

**`MAG-13` step 2 — EXECUTED 2026-08-11 (15:00 slot): the rung is measured
and the target is missed on-rate — 5.6494% vs < 5%, in 278 s.** *(`MAG-13`
stays ✅ at its recorded numbers, exactly as the entry pre-committed; the
< 5% target moves from "unmeasured" to **measured and missed at
h = 0.00125**. Nothing closes, nothing reopens.)*
> **Measured** (`20260811T200040Z_MAG-13-step2-solve-n8.log`, exit 0,
> **278 s** harness-wall, `-n 8`, real build, container `timeout 590`,
> foreground): mesh + solve **275.3 s**, **1 097 873 cells / 4 391 492
> global dofs**, relative L2 error **5.6494%** against
> `straight_wire_magnetic_field` (target < 5.00%; record 12.75% at
> h = 0.0025), two-rung observed rate **1.174** over 0.0025 → 0.00125
> (record 1.10 over 0.004 → 0.0018). Azimuthality control passes with room:
> `B_z` max 1.853e-07 vs `|B|_ref` 3.333e-05 = **5.6e-03**, bound 0.10. The
> cell count is **digit-identical** to the 2026-08-08 mesh record and the
> 08-09 diag, so this is the same rung all three runs meshed.
> **The rung is on-rate; the prediction that put < 5% here was optimistic on
> its own arithmetic.** The extrapolation was 12.75% × (1/2)^1.10 =
> **5.95%** at h = 0.00125 — already above 5% before this run. Measured
> 5.6494% *beats* that (the local rate 1.174 exceeds the 1.10 on record):
> the convergence behaviour is as good as advertised or better, and the
> target still misses by 0.65 pp. Nothing here is evidence against the
> fixture or the analytic Dirichlet wall.
> **The foreground recipe is also confirmed at the exact profile that
> "died" twice**: the same probe, same script, same rung that produced the
> two 2026-08-08 footerless logs ran to an `## Exit` block in 278 s — a
> fourth independent confirmation of the 10:30 review's
> background-and-end-turn root cause (the retired known-issues entry needs
> no reopening).
> **Next-rung arithmetic, recorded for the review, not executed here:** at
> the measured rate 1.174, 5.00% wants h = 0.00125 × (5.00/5.6494)^(1/1.174)
> = **h ≈ 0.001127**, i.e. ~1.37× the cells (**~1.50 M**) — mesh + solve
> plausibly ~380–450 s at `-n 8` if cost scales with cell count, inside the
> 590 s window but with thin margin and no measurement behind the scaling.
> **Cheaper route, still the named one:** graded refinement. This run adds a
> hint for it — the per-radius errors are **not monotone in r** (9.46% at
> r = 0.0080 and 6.33% at r = 0.0100, against 0.33% at r = 0.0200 and 1.40%
> at r = 0.0240), so the residual looks concentrated near the wire rather
> than at the truncation wall. That is a hypothesis from ten sample points,
> not a measurement, and per the entry's own scope boundary graded
> refinement is a review's to scope, not to be improvised in-slot.

**`MAG-13` step 2 diag — EXECUTED 2026-08-09 (07:30 slot): the mesh rung
reproduces exactly; no stage owns the kill.** *(`MAG-13` stays ✅; the < 5%
target stays unmeasured-not-missed; stage 2 stays blocked pending a review.)*
> **Measured** (`20260809T123053Z_MAG-13-step2-meshonly-diag.log`, exit 0,
> **188 s** harness-wall vs the 196 s record, heavy envelope, `-n 4`,
> `timeout 1200`, real build, FFCx cache cleared first): the anchor is met —
> **1 097 873 cells**, equal to the 2026-08-08 record digit for digit, mesh
> 185.7 s (record 192.7 s, −3.6%), `## Exit` block present, `test-results.md`
> row written, 668 lines. The log is structurally identical to the record's,
> both `Done optimizing mesh` lines at line 486 / 663 (fine volume
> optimisation 142.4 s vs 147.8 s). Container before *and* after:
> `StartedAt = 2026-08-08T20:00:21Z`, `RestartCount = 0`, Up 17 h — unchanged
> across this run and both deaths.
> **Branch (a) fired literally, its inference did not.** MESH_ONLY completes,
> but "the kill is specific to the longer/heavier solve stage" is refuted by
> the second death's own position: `20260809T003125Z…-cap16G.log` stops
> mid-Netgen **volume optimisation of the fine mesh** (`Total badness =
> 1.36536e+06`, before any `Done optimizing mesh (Wall 14x s)`, before any
> solve) — inside the phase MESH_ONLY has now completed twice at the same rank
> count and resolution. One death in the mesh phase, one past it in the solve,
> and the mesh phase runs clean on demand ⇒ **no stage owns the kill**. With
> the 6.7× time-to-death spread and the never-restarted container, what
> survives is a non-deterministic host-side kill of the process tree,
> uncorrelated with the computation. **The physics is fully exonerated**, so
> branch (b)'s *consequence* is the one taken: the known-issues entry is
> updated and the host-side question (dmesg/journalctl at 20:15Z / 00:33Z,
> WSL2 reclaim, session supervisor) is on the dashboard for the human —
> unobservable from inside the container. Stage 2 was **not** run under any
> outcome, per the plan. Nothing closes and nothing reopens.
>
> *Original plan, retained verbatim:* *(scoped 2026-08-09, 03:00 review, from the
known-issues non-test entry's own next-step: two unexplained mid-command
harness deaths on this probe's stage-2 solve (15:00 and 19:30 slots,
2026-08-08) fired the pre-registered escalation — the solve is **not**
retryable, and this step spends one slot finding out whether the harness or
the solve is the failing thing.)*
> Run the landed probe with `MAG13_STEP2_MESH_ONLY=1` at `-n 4`,
> `timeout 1200`, through the harness as usual — a stage that has completed
> once (1 097 873 cells, 192.7 s, exit 0,
> `20260808T200126Z_MAG-13-step2-meshprobe.log`), so a death here is
> diagnostic rather than ambiguous. Immediately after (whatever the
> outcome), record `docker compose ps` uptime and
> `docker inspect` `StartedAt`/`RestartCount` in the log or the journal.
> **Anchor:** reproduction of the on-record mesh rung — cell count equal to
> **1 097 873**, exit 0, an `## Exit` block present, elapsed beside the
> 196 s record. **Negative control:** the two truncated logs
> (`20260808T200451Z…` at ~660 s, `20260809T003125Z…` at ~99 s), no Exit
> block, no OOM signature — cite, never re-run stage 2. **Reading,
> pre-decided:** (a) MESH_ONLY completes ⇒ the kill is specific to the
> longer/heavier solve stage — memory pressure short of a cgroup kill or
> duration-correlated host kill are the live hypotheses; report, and any
> further stage-2 attempt stays blocked pending a review. (b) MESH_ONLY
> also dies truncated ⇒ the harness/session path itself is the failing
> thing at this rank/duration profile independent of the solve — a third
> data point with the physics fully exonerated; update the known-issues
> entry and put the host-side question (dmesg/journalctl, WSL2 memory
> reclaim, session supervisor) on the dashboard for the human — it is not
> observable from inside the container. **Cost:** heavy tier envelope, one
> command, expected ~200 s on record. **Traps:** stale FFCx lock after the
> prior kills — clear `~/.cache/fenics` first; do **not** run stage 2 under
> any outcome; real build (no complex-mode source needed). **Does not
> close / reopen:** nothing — `MAG-13` stays ✅; the < 5% target stays
> unmeasured-not-missed. **Negative result:** both branches are findings by
> construction; report which fired, annotate the known-issues entry, stop.

**`MAG-13` step 2 — attempted 2026-08-08 (15:00 run): the mesh rung is priced;
the solve is unobserved.** *(Annotated by the 18:00 review from the 16:30
slot's anomaly journal (attempts.md, 20260808T21:52Z entry); the slot died
mid-command and its artifacts were landed by the review in `8b8a706`.
`MAG-13` stays ✅; the < 5% question stays open and this step stays queued.)*
> **Stage 1 (mesh-only) is a real measurement:** h = 0.00125 m at `-n 4`
> meshes to **1 097 873 cells in 192.7 s**, exit 0, 196 s elapsed
> (`20260808T200126Z_MAG-13-step2-meshprobe.log`) — the §7 "~1.1 M cells"
> extrapolation confirmed to 0.2%. **Stage 2 (the one solve) has no result:**
> its log (`20260808T200451Z_MAG-13-step2-solve-n4.log`) ends mid-Netgen with
> no `## Exit` block — the harness itself was terminated ~660 s in, well
> inside its own `timeout 1200` and the slot's 65-minute kill. **No
> relative-L2 number exists; the < 5% target is unmeasured, not missed** — do
> not read the truncated log as a physics failure; see the known-issues
> non-test entry on the unexplained termination. The probe
> (`scripts/probes/mag13_step2_probe.py`) is a complete standalone instrument:
> env-driven (`MAG13_STEP2_MESH_ONLY`, `MAG13_STEP2_RES`), imports the fixture
> from `tests/validation/test_straight_wire.py`, touches no `src/`.
> **Rescope (18:00 review): re-run stage 2 only** — the mesh rung is paid for;
> skip the mesh-only probe. One solve at `-n 4` via the landed script,
> `timeout 1200`. Watch for the **cgroup kill signature** (signal 9 /
> exit 137): `MAT-6` step 6 established the container's 16 G total-footprint
> cap, and 1.1 M real-build cells inside it is a hope, not a measurement — if
> `MAT-6` step 7 (the 64 G cap raise) has landed first, note which cap was in
> force in the log. OOM at 16 G ⇒ that *is* the measured cost; report it
> beside the cap and stop — do not retry at more ranks (step 6 showed more
> ranks cannot lower a total-footprint ceiling). A second unexplained harness
> death ⇒ stop and escalate to the known-issues entry rather than burn a third
> slot. All other terms of the original plan below stand unchanged.

**`MAG-13` step 2 — the < 5% wire at the budget the follow-up predicted:
cost-probe, then the gate** *(scoped 2026-08-08, 10:30 review; queued §9
item 3; `MAG-13` stays ✅ — this extends a measurement, it does not reopen
the chunk)*.

*Un-blocked, 2026-08-11 10:30 review — **the two 2026-08-08 harness deaths
are the background-and-end-turn trap, and the block is lifted.** The wrapper
logs are dispositive: `logs/automation/20260808T200001Z_implementer.log`
ends "Stage 2 is running … I'll report when the monitor fires" then
`exit=0` at 20:16:37Z (harness died ~20:15Z), and
`…20260809T003001Z_implementer.log` ends "Waiting on the background solve …
I'll report when it lands" then `exit=0` at 00:33:04Z — the exact minute of
the log's last flushed write. Both sessions backgrounded the harness run and
ended their turn; in headless `-p` mode that exits the CLI and SIGKILLs the
process tree — the same mechanism, with the same evidence shape, as the
three `MAT-6` step 7 deaths root-caused 2026-08-11 03:00. The "host-side
mystery kill" hypothesis and the operator's host-observables ask are
withdrawn; the known-issues entry is retired this commit. **Rescope for the
re-queue (§9 item 3):** foreground harness call, Bash-tool `timeout`
660000 ms, container-side `timeout 590`, **`-n 8`** (real build — lighter
than the complex solves measured at this scale; the 08-08 attempt showed
mesh 149.8 s in-solve + > 510 s of `-n 4` solve without finishing, so `-n 4`
cannot fit the window). Exit 124 is a result: "mesh + solve > 590 s at
`-n 8`, real build" — record it, annotate here, stop; the fallback is then a
split mesh-cache/solve recipe or a review-priced wider slot, never a raised
timeout. All anchors, controls, and traps below unchanged.*
> `MAG-13` closed at wire 12.75% / loop 7.07% with measured rate 1.10 when
> heavy was 10 min at 2 ranks; extrapolating that rate puts the < 5% wire
> crossing at h ≈ 0.00125, ~1.1 M cells, which the current budget (20 min,
> ≤ 12 ranks) plausibly affords. **Probe first and treat it as the point of
> no return** (`MAT-6` step 6's discipline): mesh-count probe, then one
> solve at `-n 4`; OOM ⇒ one retry at `-n 8`; still OOM or > 600 s ⇒ report
> the measured cost and stop — `MAT-6`'s 1 458 561-cell rung is on record
> OOM-killed at `-n 4` (complex build; this real-build solve is lighter,
> but that is a hope, not a measurement). **Anchor:** the straight-wire
> closed form `utils/analytical.py::straight_wire_magnetic_field`
> (B_θ = μ₀I/2πr — `MAG-13`'s own gate reference), target < 5% at the
> extrapolated rung; print the new two-rung observed rate beside the 1.10
> on record. **Negative control:** on record, cite not recompute —
> `MAG-13`'s analytic-Dirichlet-vs-plain-box separation and the rate fit;
> a rung that lands on-rate but off-target is a real reading, not a rerun
> candidate. **Cost:** heavy tier, one solve command at `timeout 1200`,
> smallest rank count the probe shows fits. **Traps:** `MAG-13`'s list —
> `J·n ≠ 0` at the end caps stands unmeasured; point evaluation through
> `evaluate_vector_field_parallel`, never rank-local eval; stale FFCx lock
> after a kill. **Does not close / reopen:** nothing — `MAG-13` stays ✅ at
> its recorded numbers; a green < 5% annotates the entry and the MAG
> follow-up bullet, and graded refinement stays the named cheaper route
> either way (not to be improvised in-slot). **Negative result:** still
> > 5% at the extrapolated `h`, or unaffordable at the ceiling — both are
> findings; report the measured error and cost beside the prediction,
> annotate here, stop.

**Open follow-ups in MAG:**

- `MAG-6`'s revised test has never been executed. Its predecessor failed at
  `max relative |B| mismatch = 0.322` against a `< 0.30` limit — treat that figure
  as unreliable, it came from the `MAG-7` broken evaluation path. *(Step 1
  above, scoped 2026-08-07, executes it as a measurement.)*
- `MAG-13` did not reach the < 5% target on the wire. Extrapolating the measured
  rate puts it at h ≈ 0.00125, ~1.1M cells, > 5 min at `-n 2` — which was outside
  the budget when `heavy` was 10 min at 2 ranks, and **is now plausibly inside it**
  at 20 min and up to 12 ranks. Cost-probe before assuming so. *(Step 2 above,
  scoped 2026-08-08, executes exactly this.)* **Executed 2026-08-11
  (15:00 slot): the rung is measured and the target missed on-rate —
  5.6494% at h = 0.00125, observed rate 1.174, 275.3 s at `-n 8`
  (`20260811T200040Z_MAG-13-step2-solve-n8.log`). The 1.10-rate
  extrapolation had itself predicted 5.95% here, so this was never a < 5%
  rung; the crossing sits at h ≈ 0.001127 (~1.50 M cells).** The residual is
  uniform-mesh discretization of a 1/r field next to a thin conductor, so graded
  refinement is still the cheaper route than more uniform h — ~~and the
  measured per-radius errors, largest at the two smallest sampled radii, are
  consistent with that~~ *(struck 2026-08-13, 10:30 review: rung 3 refuted the
  per-radius pattern — see three sentences down — and the grading case rests
  on cost alone)* (§7 entry). **Rung 3 executed 2026-08-13 (09:00 slot):
  the target is reached by brute force — 3.7372% at h = 0.001127, 1 520 152
  cells, 420.3 s at `-n 8`, exit 0
  (`20260813T140146Z_MAG-13-step2-rung3-n8.log`), beating the 5.00% the rate
  1.174 priced the rung at; three-rung fitted rate 1.407.** The per-radius
  argument for grading does **not** survive that rung — the far radii got
  worse while the total fell, so the ten-point pattern is mesh-realization
  noise, not a spatial error map (§7 entry). Grading stays the cheaper route
  on cost alone; `MAG-13` stays ✅ at its recorded numbers either way.
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
| `GEO-10` | **`two_torus_domain` never emits its `outer_boundary` facet tag** (known-issues 10) | ✅ *(2026-08-06, 00:00 run; known-issues 10 retired)* | standard |
| `GEO-11` | **Boundary-classification margins under OCC bounding-box padding (CAD-only probe sweep)** | ✅ | smoke |
| `GEO-12` | **Widen the two `1e-9` wall tolerances and gate the `outer_boundary` group** (known-issues 12) | ✅ | standard |
| `GEO-13` | **Decouple `cylindrical_domain`'s wall tolerance from `resolution`** (known-issues 13) | ✅ | standard |
| `GEO-14` | **The shared ~3% geometry floor: faceting vs resolution** (entry lives after `TH-11`, beside the fixtures it measures) | ⬜ | standard |

> `GEO-4`'s substance is discharged for the two-torus fixture (`air_padding` +
> graded sizing), but it stays 🧪 until its own test executes. **Every other
> fixture in `io/mesh.py` still uses a single global `setSize` and tight padding,
> including coil+phantom** — expect the same boundary-mirror error that cost 20%
> on Helmholtz, and expect graded sizing to be equally necessary.

**`GEO-4` step 1 — off-centre domain sizing: diagnose and fix known-issues 5**
✅ *(plan written 2026-08-05, 18:00 review; executed 2026-08-06, 22:30 run)*.
> **Result: the test's assertion was wrong, and unattainable — the arithmetic
> is right.** The air box is origin-centred, so `half_width =
> max(coil_major + coil_minor, |offset| + r_phantom) + padding`; the
> off-centre phantom enters through the max's second term. But
> `coil_phantom_domain` rejects any placement with
> `|offset| + r_phantom >= coil_major - coil_minor` (the `radial_clearance
> <= 0` guard), so the phantom's outer radius is **always** strictly below
> the coil's and the coil **always** wins the max. "An offset phantom grows
> the box" is therefore false for every meshable configuration — not merely
> unexercised by the 0.03 m offset (phantom 0.07 m vs coil 0.09 m). Test and
> code landed together in `2c52f05`; the test never passed. The strict `>`
> was **not** relaxed: the test now gates the containment identity with the
> clearance term explicit (`half_width == max(coil_outer, |offset| +
> r_phantom) + 0.35·reference` for both presets) plus the exact clearance
> identity `clearance(centered) − clearance(shifted) = 0.03 m` — the whole
> offset is spent out of the phantom's wall clearance — and two new tests
> keep a strict `>` alive on the phantom-governed branch (arithmetic only,
> outside the meshable envelope) and re-gate zero-padding detection.
> `coil_phantom_domain_sizing_diagnostics` gained four reporting keys
> (`phantom_offset_radius_m`, `phantom_outer_radial_extent_m`,
> `phantom_boundary_clearance_m`, `phantom_governs_radial_extent`); **no
> sizing number changed**, so no meshed fixture moved. Negative control
> executed first, not quoted: `20260806T033155Z_GEO-4-step1-precontrol.log`
> (1 failed 3 passed, `assert 0.09 > 0.09`, 1.31 s). Gates
> `20260806T033316Z_GEO-4-step1-gate.log` (6 passed, 1.36 s) and
> `20260806T033327Z_GEO-4-step1-mesh-regression.log` (whole `tests/mesh`,
> `--deselect` removed, **27 passed 1 skipped in 85.3 s**), both `-n 2`,
> smoke tier. Known-issues 5 retired; the `OPS-11` exclusion is gone and
> `tests/mesh` now runs unexcluded in CI. **Handed to the review:** the
> overlap guard is z-blind, so a short phantom that would clear the torus
> tubes in z is rejected too — if radially governing off-centre placements
> are ever wanted, that guard is what must change, not the heuristic.
> `GEO-4` itself stays 🧪 (graded-sizing generalization is separate).
> The oldest standing failure on `main`:
> `tests/mesh/test_domain_sizing_heuristics.py::test_coil_phantom_domain_sizing_accounts_for_off_center_phantom_extent`
> fails `assert 0.09 > 0.09` — pure geometry arithmetic in
> `MeshGenerator.coil_phantom_domain_sizing_diagnostics`, no solve involved,
> pre-existing since before this session's history (`794d2f1`). It has been
> `--deselect`ed from CI since `OPS-11` and pollutes every `tests/mesh`
> regression sweep as a standing "1 failed". The exact-equality symptom says
> the heuristic sizes the domain to *exactly* the off-centre phantom extent
> with zero margin — diagnose which side is wrong: either the heuristic omits
> the clearance/padding term for the off-centre preset (fix the arithmetic),
> or the test's strict `>` encodes an intent the heuristic never had (then
> the *intent* must be established from the sizing docstring/call sites
> before any code moves — per the never-loosen rule, the assertion is
> evidence, and relaxing `>` to `>=` without that provenance is forbidden).
> **Anchor:** the geometric identity the fix must gate — domain half-extent
> `≥ |offset| + phantom half-extent + stated clearance`, asserted
> quantitatively with the clearance term explicit, plus the centered preset's
> current passing numbers reproduced unchanged (print both presets' extents).
> **Negative control:** on record — the failing `assert 0.09 > 0.09` at
> `794d2f1`..today (`20260803T034252Z_GEO-9-step1-cohabit.log`); after the
> fix, a zero-clearance call must still be *detected* (the diagnostics
> function exists to catch exactly that). **Cost:** smoke — the sizing
> diagnostics run without meshing; the full `tests/mesh` regression at `-n 2`
> is 72 s on record; `timeout 180`. **Traps:** known-issues 5 has been
> miscited as "6" (commit `3ac025c`, attempts.md) — it is 5; **remove the
> `OPS-11` `--deselect` in the fixing commit** — it is the only thing keeping
> the test out of CI, and the entry leaves only with that commit; do not
> touch birdcage exclusions, which are separate; `tests/mesh` at `-n 2`
> should then be 25 passed 1 skipped — any other failure is new information,
> not this chunk's. **Does not close:** `GEO-4` — the graded-sizing
> generalization to other fixtures (§9 air-box item) is separate work; this
> step retires known-issues 5 only. **Negative result:** if the intent
> genuinely cannot be established from the code and history, journal the
> archaeology in the known-issues entry and stop — the test stays deselected,
> and adjudicating intent becomes an operator question on the dashboard.

**`GEO-10` — `two_torus_domain` never emits its `outer_boundary` facet tag
(known-issues 10)** ✅ *(2026-08-06, 00:00 run)*.
> **What it was — not the prime suspect.** The group was never *declared*, so
> no renumbering could lose it. gmsh inflates an OCC entity's bounding box by
> its geometric tolerance, measured at exactly **`1.000e-07`** on all six walls
> (`20260806T050143Z_GEO-10-probe.log`), and the fixture's flat-against-wall
> test used `tol = 1e-9`: every wall failed, `boundary_surfaces` came out
> empty, and the `if boundary_surfaces:` guard skipped `addPhysicalGroup`
> silently. Fragment renumbering is refuted — the group is re-derived from
> bounding boxes *after* `fragment` + `synchronize`. Fix: that one tolerance,
> `1e-9` → `1e-6`, 10× above the measured padding and four orders below the
> nearest interior face's `2.000e-02` residual, so the interior-face
> protection the tight test existed for is intact. Fixture-local: every other
> `outer_boundary` derivation in `io/mesh.py` uses a `< resolution` test.
> **Gate** `tests/mesh/test_two_torus_outer_boundary.py` — tag sets exactly
> `{1}` / `{1, 201, 202}`, and tagged `ds` area = analytic box surface
> `3.220000000000e-02 m²` at ratio **`1.000000000000000`** (`-n 2`, 25 s,
> `20260806T050313Z_GEO-10-gate-n2.log`) and `1.000000000000001` (`-n 1`,
> 24 s). An identity at `1e-9`, not a band: the walls are planar.
> **Nothing moved.** The open question is answered — *neither* Helmholtz
> consumer depends on tag `1`: both are digit-identical with the group present,
> `MAG-14`'s centre-field error still `0.728%`
> (`…050656Z_GEO-10-helmholtz-regression.log`). Port facets reproduce
> `1.563786482e-04 m²` at `0.974490841` (`…050620Z_…-portfacet-digits.log`);
> full `tests/mesh` **29 passed, 1 skipped, 107.64 s**
> (`…050421Z_GEO-10-mesh-regression.log`). Known-issues 10 retired.
> *(Original chunk text below, written 2026-08-05, 18:00 review.)*
> Measured 2026-08-05: the fixture's third return value carries **no** tag
> `1` — the ungapped global facet-tag set is `[]`, the gapped set is
> `[201, 202]`, while `mesh.py:1038` adds an `outer_boundary` physical group
> that never survives to the dolfinx tags
> (`20260805T020843Z_PORT-1-step3biv-serial-gate.log`). Diagnose where the
> group is lost — prime suspect is the `GEO-8` fragment renumbering the box
> boundary surfaces after the dim-2 group is declared (the "fragment
> renumbers — never trust its returned tag order" lesson, applied to
> surfaces), in which case the fix is re-deriving the outer-surface group
> from the fragment out-map exactly as `GEO-9` step 2b did for volumes.
> **Anchor:** the tagged outer-boundary facet area must equal the analytic
> box surface area `2(LW + LH + WH)` — planar facets partition the boundary
> exactly, so this is an identity gated at `1e-9` like `GEO-9`'s volume
> identities, allreduced, at `-n 1` and `-n 2`; plus tag-set assertions
> `{1}` ungapped and `{1, 201, 202}` gapped. **Negative control:** on
> record, cite — today's empty tag set is the broken-state measurement; the
> port-facet gate's areas (`1.563786482e-04 m²`, band `(0.970, 0.980)`) must
> reproduce digit for digit, since adding a boundary group must not move
> interface tags. **Cost:** standard, `-n 2`; the port-facet gate is 20 s
> and `tests/mesh` 72 s on record; `timeout 180`. **Traps:** dim-2 physical
> groups must be declared after `synchronize` and re-derived after fragment;
> the two Helmholtz consumers (`test_helmholtz_v2.py`,
> `test_helmholtz_magnitude.py`) pass `facet_tags=` into a solver — run both
> as regression and **their gated numbers must not move** (`MAG-14`'s 0.728%
> is in CI); whether either actually depends on tag `1` is unchecked — check
> and record it in the known-issues retirement; `create_entity_permutations`
> before any per-tag facet assembly (the 3b-iv lazy-collective lesson);
> pytest `-s`. **Does not close:** nothing downstream — this is fixture
> hygiene that unblocks any future ABC/radiation boundary work on this
> fixture; `PORT-1` does not depend on tag `1`. **Negative result:** if the
> group is lost somewhere other than fragment renumbering and the diagnosis
> exceeds the slot, journal the named loss point in known-issues 10 and stop
> — do not restructure `two_torus_domain` in-slot; it feeds five validated
> gates.

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

**`GEO-11` — boundary-classification margins under OCC bounding-box padding**
✅ *(2026-08-06, 09:00 run — gate landed and the sweep found two fixtures with
`GEO-10`'s exact defect; known-issues 12 and 13 opened, no tolerance moved)*
> **The sweep found the defect live in two more fixtures.**
> `tests/mesh/test_boundary_classification_margins.py` replicates the CAD stage
> only (build, fragment, synchronize — never mesh) of four fixtures, applies
> each one's *own* classification predicate to every dim-2 entity, and asserts
> the two-sided separation `max(accepted residual)/tol ≤ 0.1` and
> `min(rejected residual)/tol ≥ 10`. Smoke, `-n 1`, **0.19 s**, 2 passed /
> 3 skipped (`20260806T140517Z_GEO-11-gate.log`; the measuring probe run is
> `…140325Z_GEO-11-probe.log`).
> * `two_torus_domain` **meets both sides**: 6 of 8 accepted, wall ratio
>   `1.000000e-01` (exactly the 10× `GEO-10` designed), interior `2.000010e+04`.
>   The `GEO-10` known case is re-derived as its own test — the OCC padding is
>   `1.000000e-07`, bracketed strictly inside `(1e-9, 1e-6)`, against the
>   nearest interior face at `2.000010e-02`.
> * `loop_over_half_space_domain` (`MAT-6`) accepts **0 of 12** and
>   `sphere_in_box_domain` (`TH-8`/`MAT-4`) accepts **0 of 7** — both use
>   `tol = 1e-9`, i.e. **100× below** the same `1.000e-07` padding, so their
>   `outer_boundary` group is never declared. Retired known-issues 10's closing
>   "no other fixture is affected" is **refuted by measurement** and annotated
>   in place. **Latent, not a wrong result:** all six callers of the two
>   generators discard `facet_tags` and impose the wall geometrically, verified
>   by grep — no landed `MAT-6`/`TH-8`/`MAT-4` number reads the missing group.
>   known-issues 12.
> * `cylindrical_domain`'s interior margin is **`4.499995 ×` tol** (inner
>   cylinder at `r = 0.01` vs outer wall `r = 0.1`, `tol = resolution = 0.02`),
>   below the 10× floor. Correct today, under-separated. known-issues 13.
>
> **No tolerance was moved** — the plan reserves that for a review with the
> numbers in hand, and it now has them. The two failing fixtures are instead
> **pinned** at their measured ratios (surface counts, accepted counts,
> wall/interior ratios at `rel=1e-6`) and the margin assertion is skipped with
> the known-issues reference in the skip message, so the defect cannot drift
> silently while the review holds it. Bound note: `two_torus_domain`'s wall
> ratio lands on `0.1` to within double-precision noise
> (`1.0000000000287557e-01`, 2.9e-11 relative, because `GEO-10` sized `tol` at
> exactly 10× the padding), so the ceiling carries a `1e-6` relative slack —
> that is the float representation, not a loosened bound. *(Digit string
> corrected from the gate log by the 10:30 review's audit; the in-slot
> transcription read `…029e-01`.)*
> **Not covered, deliberately:** `coil_phantom_domain` and
> `birdcage_port_domain`. Their CAD stages are ~190 lines each and a copy would
> drift from the original silently, which is worse than no gate; covering them
> needs the CAD stage factored out of the generator, which is a review's call.
> **Does not close:** `GEO-4`, or anything downstream — hygiene measurement.

*(Original plan, 03:00 review, retained for the audit trail.)*
> `GEO-10` found that gmsh inflates an
OCC entity's bounding box by its geometric tolerance (measured `1.000e-07`) and
that a wall-classification test tighter than that padding silently empties a
boundary group — no error, just a missing physical group. The other
`outer_boundary` derivations in `io/mesh.py` (the `< resolution` wall tests at
~lines 676, 2025, 2515) are believed safe by ~4 orders, but that margin is
asserted from one fixture's measurement, not measured per fixture. This chunk
converts the hazard into numbers. Extend `scripts/probes/geo10_probe.py` into a
smoke-tier gate that, for each CAD-only buildable fixture with a wall test,
prints and asserts the two-sided margin: every true wall's residual against its
classification tolerance, and every interior face's residual against the same
tolerance. **CAD-only — build the OCC model, never mesh.** **Anchor:** per
fixture, `max(wall residual)/tol ≤ 0.1` and `min(interior-face residual)/tol
≥ 10` — a measured two-sided separation, numbers printed per surface; the
`GEO-10` fixture re-probed as the known case (`1.000e-07` vs `1e-6` vs
`2.000e-02` on record). **Negative control:** on record, cite —
`20260806T050143Z_GEO-10-probe.log`, where `tol = 1e-9` classified zero of six
walls. **Cost:** smoke, `-n 1` (the probe is serial CAD arithmetic; the
`GEO-10` probe ran 2 s); `timeout 180`. **Traps:** gmsh state poisoning across
fixtures in one process — finalize between builds (`GEO-9` step 2a lesson);
`birdcage_port_domain` raises by design pre-`GEO-9` geometry only — use the
current fixed generators and still wrap in `try/finally`; do not mesh anything;
pytest `-s`. **Does not close:** `GEO-4` (sizing is a different property) or
anything downstream — this is hygiene measurement. **Negative result:** any
fixture with margin < 10× gets a known-issues entry naming the fixture and the
measured ratio — report and stop; widening a fixture's tolerance is a per-
fixture decision for a review with the numbers in hand.

**`GEO-12` — widen the two `1e-9` wall tolerances and gate the
`outer_boundary` group (plan written 2026-08-06, 10:30 review; fixes
known-issues 12).** The review now has the numbers `GEO-11`'s plan reserved
the decision for, and takes it: `loop_over_half_space_domain` and
`sphere_in_box_domain` widen their wall-classification `tol` from `1e-9` to
`1e-6` (`io/mesh.py` ~lines 1384 and 1532) — exactly `GEO-10`'s fix, and for
the same measured reason: the OCC bounding-box padding is `1.000e-07`, 100×
*above* the current tolerance, and the nearest true interior faces sit at
`9.000e-02` and `1.500e-01`, so `1e-6` clears the padding by 10× while
keeping ~5 orders of interior-face protection. The tolerance change must land
**with** the gates, because the defect survived precisely because nothing
gated the group: (i) un-pin the two fixtures in
`tests/mesh/test_boundary_classification_margins.py` — remove their
`pytest.skip` and pinned-failure assertions so the two-sided margin gate
executes (expected wall ratio `1e-7/1e-6 = 0.1`, on the ceiling exactly as
`two_torus_domain` is — reuse the existing `×(1+1e-6)` float slack, do not
invent a new one); (ii) add a meshed facet-tag gate per fixture asserting
tag `1` exists with an **allreduced** facet count > 0 and the summed wall
area equal to the analytic outer-surface area of the box (flat facets are
represented exactly — assert at `1e-9` relative after `MPI.SUM`). **Anchor:**
the margin identity per fixture (`≤ 0.1×(1+1e-6)` / `≥ 10`) plus the
wall-area identity vs the closed-form box area. **Negative control:** on
record, cite — the pre-fix pinned state, 0-of-12 and 0-of-7 accepted
(`20260806T140325Z_GEO-11-probe.log`), and retired entry 10's identical
defect on `two_torus_domain`. **Cost:** the CAD margin gate is smoke
(0.19 s on record); the facet-tag gate meshes both fixtures — both mesh
routinely inside `MAT-6`/`TH-8` suites, standard tier, `-n 2`,
`timeout 180`; then whole `tests/mesh` (108 s on record) plus the six
downstream callers' suites as regression (`tests/materials` +
`tests/validation/test_lossy_sphere_sar.py`, 157 s on record at
`timeout 600`). **Traps:** gmsh init/finalize per fixture in `try/finally`
(`GEO-9` step 2a); all six downstream callers discard `facet_tags`
(3-tuple unpack) so no landed number should move — but measured, not
assumed: re-run their suites; `cell_tags.values` and facet counts are
rank-local — allreduce before asserting; the two fixtures' `tol` literals
also appear in the `GEO-11` test's pinned constants — update both sides in
the same commit or the pin contradicts the fix; pytest `-s`. **Does not
close:** known-issues 13 (`cylindrical_domain`'s 4.50× interior margin is a
different mechanism — tolerance coupled to `resolution` — and stays open);
`GEO-4`. **Negative result:** if the accepted-wall count after widening is
not exactly the fixture's wall count, or the area identity misses, the
classification predicate is wrong in a way `tol` cannot fix — report the
measured counts and residuals, leave known-issues 12 open with the new
numbers, revert nothing silently, stop.

> **✅ 2026-08-06 (13:30 implementer slot).** Both tolerances widened to `1e-6`;
> the negative result did not occur — the accepted count is exactly each
> fixture's wall count and the area identity holds to the last digit.
>
> **CAD margin** (`20260806T183203Z_GEO-12-probe.log`): `loop_over_half_space`
> accepts **10 of 12** dim-2 entities — the cube's four `z = 0`-split sides plus
> top and bottom, which *is* its wall count, the two rejected being the torus
> surface (`9.000010e-02`) and the air/slab interface (`1.000001e-01`) — and
> `sphere_in_box` **6 of 7** (sphere surface rejected at `1.500001e-01`). Both
> sit at wall ratio `1.0000000000287557e-01`, the same `1e-7/1e-6 = 0.1`
> `GEO-10` designed, and interior ratios `9.000010e+04` / `1.500001e+05` —
> five orders of interior-face protection, as predicted. The two
> `pytest.skip`s in `tests/mesh/test_boundary_classification_margins.py` are
> gone; that file now *asserts* the two-sided margin for these fixtures.
>
> **Meshed gate** (new `tests/mesh/test_wall_boundary_tag_areas.py`, `-n 2`,
> `20260806T183328Z_GEO-12-gate.log`, 3.2 s): facet tag `1` present on both,
> allreduced facet counts **1958** and **988**, and the assembled `ds` area
> equals the analytic cube surface `6(2W)² = 2.400000000000e-01 m²` at ratio
> **1.000000000000000** (loop) and **0.999999999999999** (sphere) — planar
> walls, so an identity at `1e-9`, not a band.
>
> **Regression — the latency claim measured, not assumed.** All six discarding
> callers plus `tests/post/test_drop_set_semantics_sphere.py` re-run: **no
> landed number moved a digit.** `MAT-6` step 3 `dR` 1.5834% / `dX` 0.9200;
> step 4 projected 1.5763% / 0.9849 and pinned 1.5713% / 0.8740, identical to
> `20260805T200455Z` / `20260805T200938Z`; mass-averaged SAR ratio 0.999846;
> `POST-1` sphere table 4.2530%. Logs
> `20260806T183745Z_GEO-12-callers-A.log` (24 passed, 210 s) and
> `20260806T184151Z_GEO-12-callers-B.log` (8 passed, 574 s, heavy). Whole
> `tests/mesh` at `-n 2`: **35 passed, 2 skipped, 118.29 s**
> (`20260806T183404Z_GEO-12-mesh-regression.log`). known-issues 12 retires with
> this commit; **known-issues 13 stays open** as scoped.

**`GEO-13` — decouple `cylindrical_domain`'s wall tolerance from `resolution`**
✅ *(2026-08-07, 22:30 implementer slot; known-issues 13 retired)*
> The tolerance is now `0.01 × (outer_radius − inner_radius)`, a fraction of the
> radial gap, replacing `resolution` in **both** the outer- and inner-surface
> predicates. The fraction was chosen from a sweep, not from the plan's
> illustrative 0.05: `20260807T033127Z_GEO-13-probe.log` measured every
> fraction in `{0.5 … 1e-5}` against all four argument sets the repo calls this
> generator with (gaps `0.09` and `0.07`), and the window where **both** sides
> of the `GEO-11` identity hold is `[1e-4, 0.05]` on all four — `0.01` is its
> middle. **Anchor met, live:** at defaults the nearest rejected surface is
> `9.999989e+01 × tol` (floor `10×`, was `4.499995×`) and the worst accepted is
> `1.111111e-04 × tol` (ceiling `0.1×`); the r_out = 0.08 geometry lands on
> `9.999986e+01` / `1.428571e-04`. The classification is **unchanged** — 3 of 6
> surfaces on every geometry — so no landed number can move, and none did.
> **Negative control reproduced in the same probe:** the old predicate at
> `resolution = 0.09` accepts **6 of 6** surfaces, i.e. the inner cylinder swept
> whole into `outer_boundary`, which is the failure known-issues 13 predicted
> and nothing had ever executed.
>
> `tests/mesh/test_boundary_classification_margins.py`: the `cylindrical_domain`
> pin and its `pytest.skip` are **gone**, replaced by the live two-sided
> assertion — all four fixtures in that file now assert rather than pin, which
> closes the `GEO-11` sweep. The test reads `_WALL_TOL_FRACTION` from
> `io/mesh.py` so the gate and the generator cannot drift apart. **5 passed in
> 1.05 s** (`20260807T033236Z_GEO-13-margins.log`, `-n 1`, smoke); whole
> `tests/mesh` **36 passed, 1 skipped in 110.34 s**
> (`20260807T033250Z_GEO-13-mesh-regression.log`, `-n 2`) — one skip fewer than
> `GEO-12`'s 35/2, which is exactly this fixture going live; callers
> `tests/solver/test_cylinder.py` + `test_boundary_condition_selection.py`
> **4 passed, 1 skipped in 0.97 s** (`20260807T033454Z_GEO-13-callers.log`,
> `-n 2`; the skip is the complex-mode PEC test). No meshed wall-area gate was
> added, per the plan — the cylinder wall is curved and `GEO-12`'s exact planar
> identity does not transfer.
>
> **New precondition, recorded at the use site:** the tolerance now scales with
> the gap, so a gap below ~`1e-4` m stops clearing the `1.000e-07` OCC padding
> by 10×. The smallest gap in the repo is `0.07` m.

<details>
<summary>Original plan (2026-08-06, 18:00 review)</summary>

> **`GEO-13` — decouple `cylindrical_domain`'s wall tolerance from
> `resolution` (plan written 2026-08-06, 18:00 review; fixes known-issues
> 13).** The last open classification-margin defect, and the mechanism the
> `GEO-12` slot's closing note already named: the fixture's wall test is
> `abs(r_max − outer_radius) < resolution`, so the margin is geometry over
> *mesh size* — 4.50× at defaults (inner cylinder at residual `8.999990e-02`
> vs `tol = 0.02`), and at `resolution ≥ 0.09` the inner cylinder would be
> swept into `outer_boundary`. Replace `resolution` in the predicate with a
> geometric fraction of `outer_radius − inner_radius`, chosen so both
> two-sided bounds hold at defaults with the probe's measured numbers: the
> fraction must clear the `1.000e-07` OCC padding by ≥ 10× on the accept
> side and sit ≥ 10× below the interior residual on the reject side (e.g.
> 0.05 × 0.09 = 4.5e-3 → interior ratio 20, wall ratio ~2e-5 — but set the
> final value from the probe, not from this sentence). Then un-skip
> `cylindrical_domain` in `tests/mesh/test_boundary_classification_margins.py`
> — the fixture is already parameterized there — replacing the pin with live
> two-sided assertions, exactly the `GEO-12` pattern. **Anchor:** the
> two-sided margin identity (wall ratio ≤ 0.1×(1+1e-6), interior ratio
> ≥ 10), asserted for the fourth and last box/cylinder fixture. **Negative
> control:** on record — the pinned `4.499995×` ratio
> (`20260806T140325Z_GEO-11-probe.log`) and the accept-side `5.000e-06×`.
> **Cost:** CAD margin smoke (0.19 s on record for the sweep); regression =
> whole `tests/mesh` at `-n 2` (118 s on record), `timeout 180`. Do **not**
> add a meshed wall-area gate here: the cylinder wall is curved, a
> linear-tet surface converges only O(h²), so `GEO-12`'s exact planar
> identity does not transfer — a banded area check is optional and its band
> must be set from a probe, never asserted at 1e-9. **Traps:** gmsh
> init/finalize in `try/finally`; the margins test's pinned constants
> encode the *old* predicate — update both sides in one commit; check
> `cylindrical_domain`'s callers for anything that passes a coarse
> `resolution` and relied on the old coupling; pytest `-s`. **Does not
> close:** anything outside known-issues 13; the loop/sphere/two-torus
> tolerances do not move. **Negative result:** if no single fraction clears
> both bounds at defaults, the radii are too close for a static fraction —
> report the measured ratios, leave known-issues 13 open with them, stop.

</details>

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
| `TH-10` | **Validation: lossy dielectric sphere in a full-wave field at 64/128 MHz (the first Larmor-regime gate)** | ✅ | standard |
| `TH-11` | **Coil-loading trend across the eddy→displacement transition (`MAT-6`'s ΔR machinery at rising f)** | ⬜ | standard |

**`TH-10` — lossy dielectric sphere, full-wave, 64/128 MHz (Larmor gate)** ✅
*(steps 1–4 ✅ 2026-08-13; **chunk closed by the 2026-08-13 10:30 review**
(run interactively after the scheduled slot's 529) — the interior field is
gated against the series at **both** Larmor frequencies — 3.643% at 64 MHz,
1.826% at 128 MHz — and the SAR-relevant volume integral ½∫σ|E|² to 3.629%
at 64 MHz, with the quasi-static power route missing by 58.1%. All four
scoped steps audited §4-compliant (assertions enforced in code, negative
controls executed, no bound moved). Disposition of the one unscoped item:
the coil-loading trend is **not** this chunk's — it validates a different
machinery (`MAT-6`'s ΔR route) on a different fixture — and is commissioned
as `TH-11`. Audit caveats on record: step 4 gates the fine-rung level but
not monotonicity (add the assert on the next edit of that file); step 4's
negative-control margin is 1.16× vs the field gates' 1.9–5.7× — floor was
pre-stated, not moved. No SAR *wording* follows: this gates the volume
integral, not mass averaging or C95.3, and §2.1's sentence moves only the
imposed-field clause.)*
*(opened 2026-08-12, 18:00 daily review, per §10 subgoal 3's standing
instruction — "the daily review should start breaking this down as the port
lineage clears, and a §7 chunk ID should exist by the next weekly review".
The port lineage cleared its diagnosis phase this interval — 3b-xvi closed
and the pair gate is queued — which is the condition §10 named.)*
> The §2.1 honesty gap this chunk exists to close: every coil-loading/SAR
> gate today is eddy-current (10 MHz, `MAT-6`) or imposed-field (`MAT-4`);
> gelled saline at 64/128 MHz is an **extrapolation**, not a result. The
> named target (§10 subgoal 3): the lossy dielectric sphere in a full-wave
> time-harmonic field against its analytic series solution — the `TH-8`
> machinery carried into the displacement-current regime, where σ/(ωε₀)
> is order-one (saline εᵣ ≈ 78, σ ≈ 0.5–0.7 S/m at 64/128 MHz) and the
> quasi-static approximation `TH-8` gated is no longer valid.
>
> * **Step 1 — author the anchor (zero-solve, smoke).** ✅ **2026-08-13
>   (00:00 run)**. `LossySphereSeries` + `complex_permittivity` are in
>   `utils/analytical.py`: the Mie series (Bohren & Huffman ch. 4,
>   eqs. 4.37/4.40/4.45/4.50/4.53) imported into the `e^{+jωt}` convention
>   **by conjugating both `ε_c` and the field**, with special functions per
>   Jin App. E.2 (eqs. E.24–E.31) — `scipy.special.jv(n+½, ·)` for the complex
>   interior argument, since `spherical_jn` rejects complex. Interior,
>   incident, scattered and piecewise-total fields are all exposed; the total
>   field is the callable a later step drives the box wall with, as `TH-8`
>   does. **6/6 gates, exit 0, 1 s, `-n 1`**
>   (`20260813T050847Z_TH-10.log`): empty limit **1.998e-15** (and `c_n = d_n
>   = 1` to **0.000e+00** — the Wronskian collapse, exact); quasi-static tie to
>   `TH-8` **0.0151%**; the same on the imaginary axis of `ε_c` **0.0083%**;
>   tangential-`E` continuity at `r = a` **2.4e-14** at 64/128 MHz (the only
>   gate that touches `a_n`/`b_n`, and a *full-wave* identity — it needs no
>   quasi-static limit); conjugated-convention control **173.8%**, i.e.
>   **2.1e+04×** the spec error; truncation drift at `N+6` **9.7e-17**.
>   **The quasi-static gate is aimed at the mean, and both retardation orders
>   are gated, because the first attempt measured why:** pointwise the series
>   misses `3E₀/(εᵣ+2)` by **3.52e-02** at the `TH-8` fixture — a linear
>   interior phase ramp `e^{−j k_in z}` that the closed form has no term for —
>   falling at **rate 1.0002** in `|m|k₀a` over three radius halvings, while
>   the mean (`TH-8`'s own gated `ez_mean`) falls at **rate 1.9684** from
>   1.5e-04. `TH-8`'s fixture comment ("the retardation correction the closed
>   form drops is O((k_in R)²) ≈ 0.2%") is thereby **confirmed for its mean and
>   shown to be wrong pointwise** — a note for whoever next reads that fixture,
>   not a defect in it, since `TH-8` asserts on the mean. The lossy sweep
>   reproduces both rates (1.9003 / 1.0001) on the imaginary axis.
>   **The reading `TH-10` exists for** (printed, ungated): the saline sphere's
>   full-wave interior field departs from the quasi-static value by **102.3%**
>   at 64 MHz and **154.6%** at 128 MHz (a = 0.05 m, εᵣ = 78, σ = 0.5 S/m,
>   `|m|k₀a` = 0.85 / 1.37). That is the size of the extrapolation §2.1 flags —
>   at the Larmor frequencies the quasi-static answer is not a correction away
>   from the truth, it is the wrong answer. **For the review:** the anchor is
>   self-consistent and limit-correct, but nothing has yet compared it to an
>   *independent* implementation or to a solve; step 2 is where it earns
>   trust as a gate. Probe: `scripts/probes/th10_step1_sphere_series.py`.
>   *Original step text follows.* Queued as §9
>   item 4, 2026-08-12 18:00: implement the series solution in
>   `utils/analytical.py` (complex `ε_c = εᵣ − j·σ/(ωε₀)`, the `TH-1`
>   `e^{+jωt}` convention) with a self-check probe through the harness.
>   Quantitative identities: the quasi-static limit reproduces `TH-8`'s
>   validated closed form to < 0.5% at ka ≪ 1; the empty limit
>   (εᵣ → 1, σ → 0) returns the incident field to machine precision; a
>   conjugated-convention negative control must break the limit check by
>   orders. Full recipe in the §9 item. Consult
>   `docs/references/jin-fem-3e/` before re-deriving; cite chapter/eq.
>   numbers in the annotation.
> * **Step 2 — the first full-wave solve gate, 64 MHz** ✅ **2026-08-13
>   (04:30 run)**. `tests/validation/test_lossy_sphere_fullwave.py`: the
>   `sphere_in_box_domain` wall is driven with `LossySphereSeries.total_field`
>   through `TimeHarmonicProblem.dirichlet_e_field` (the `TH-8` pattern, the
>   piecewise-total callable step 1 exposed for exactly this), a = 0.05 m,
>   εᵣ = 78, σ = 0.5 S/m, 64 MHz — `ε_c = 78 − j140.43`, m = 10.9233 +
>   6.428j, k₀a = 0.067067, **|m|k₀a = 0.850029**, N = 7, last-term bound
>   8.075e-16. **Both gates green first run, exit 0, 10 s, `-n 2`, standard
>   tier** (`20260813T093212Z_TH-10-step2-64mhz.log`):
>   **interior relL2(E_FEM vs series) 8.154% (5 866 cells) → 3.643%
>   (17 670 cells)** on `TH-8`'s own two coarser rungs — under the 5% band
>   and decreasing, and within 0.9% of `TH-1`'s plane-wave precedent
>   (3.61% L2) on a completely different fixture. Negative control: the
>   solve sits **18.68×** closer to the series than to the quasi-static
>   closed form (bound 10×; relL2(FEM vs quasi-static) 68.034%), so the
>   solver is resolving physics `TH-8`'s closed form does not contain.
>   **Number worth carrying:** the reference's *own* series-vs-quasi-static
>   separation on this probe set is **55.113% in relL2** — the same fact
>   step 1 recorded as 102.3% in max-norm. The two are not interchangeable;
>   quote the norm with the number. **Where the claim now stands:** this is
>   the repo's first solve gated in the Larmor regime, and the first
>   external check on step 1's anchor — the series and a fully independent
>   FEM discretisation agree to 3.6%, which retires the "six gates are all
>   internal identities of one implementation" caveat for 64 MHz. It does
>   **not** license SAR (that is step 4's ∫σ|E|²) or any coil-loading claim.
>   `TH-10` stays 🟡 pending steps 3–4.
> * **Step 3 — 128 MHz** ✅ **2026-08-13 (07:30 run)**. Step 2's fixture
>   made frequency-parametric (`_run_gate`) and re-run at 128 MHz with the
>   **bounds unchanged** — ε_c = 78 − j70.215, m = 9.5642 + 3.6707j,
>   k₀a = 0.134134, **|m|k₀a = 1.37413**, N = 8, last-term bound 7.207e-16.
>   Rungs are step 2's fine rung plus one 1.5× refinement. **Both gates
>   green first run, exit 0, 26 s for the whole file, `-n 2`, standard
>   tier** (`20260813T123211Z_TH-10-step3-128mhz.log`):
>   **interior relL2(E_FEM vs series) 3.299% (17 670 cells) → 1.826%
>   (55 251 cells)** — under the 5% band and decreasing, at *half* `TH-1`'s
>   plane-wave 3.61%. Negative control: **57.31×** separation from the
>   quasi-static closed form (bound 10×; relL2(FEM vs quasi-static)
>   104.658%, and the reference's own series-vs-quasi-static separation is
>   **68.703% in relL2** = step 1's 154.6% in max-norm — quote the norm with
>   the number). The same command re-ran 64 MHz through the refactored
>   helper and reproduced step 2's record digit-for-digit (8.154% → 3.643%,
>   18.68×), so the parametrisation moved nothing.
>   **The frequency-scaling read, which contradicts the item's
>   prediction:** §9 item 3 priced the resolution demand as "roughly
>   doubling", and it did not. At the **same** rung (17 670 cells) the error
>   is *lower* at 128 MHz (3.299%) than at 64 MHz (3.643%), even though the
>   interior wavenumber |m|k₀ rises 1.71× (16.06 → 27.48 rad/m). So at these
>   rungs the ~3% error is **not** interior-wavelength-limited — something
>   else (most plausibly sphere faceting / exterior discretisation, both
>   frequency-independent) sets it, which also means 64 MHz's 3.643% may be
>   a geometry floor rather than a resolution level. The observed pairwise
>   rates are consistent with that: **1.985 at 64 MHz vs 1.463 at 128 MHz**,
>   printed as reads, not gated. Isolating that floor is not `TH-10`'s
>   scope — flagged for the weekly review beside `MAG-13`'s own CG1 floor.
>   **Where the claim now stands:** the solver is gated against an
>   independent full-wave anchor at **both** Larmor frequencies, the
>   condition §10 subgoal 3 names. It still licenses no SAR number (step 4's
>   ∫σ|E|²) and no coil-loading claim; `TH-10` stays 🟡 pending step 4.
> * **Step 4 — the SAR-relevant integral** ✅ **2026-08-13 (12:00 run)**.
>   Both gates green first run at the bounds §9 item 5 stated before the
>   run, exit 0, **30 s** for the whole file, `-n 2`, standard tier
>   (`20260813T170337Z_TH-10-step4-power-n2.log`). ½∫σ|E|² over the sphere
>   at 64 MHz, on step 2's two rungs and its σ field:
>   **P_FEM vs the series integral 8.387% (5 866 cells) → 3.629%
>   (17 670 cells)** — under the 5% band and decreasing. Negative control:
>   the quasi-static uniform-field power route misses the series integral by
>   **58.14%** against the > 50% floor (P_qs = 4.464e-08 W vs
>   P_series = 1.066e-07 W; quasi-statics under-predicts the absorbed power
>   by a factor 2.4 at the 1.5 T Larmor frequency — the §2.1 extrapolation
>   priced in watts rather than volts).
>   **What the reference is, precisely.** The gated comparison integrates the
>   series interior field over the *same meshed* sphere cells with the *same*
>   DG0 σ field and the same measure, so the only thing differing between the
>   two integrals is `E`. That matters: the meshed sphere holds
>   **V_mesh/V_exact = 0.9898** at the fine rung and carries
>   **98.59%** of the exact-ball power, so scoring the FEM against an
>   exact-ball reference would have folded a 1.4% geometry defect into a 5%
>   field band. The exact-ball value is computed independently anyway (numpy
>   Gauss-Legendre product quadrature, r × cosθ × φ) and printed as a read:
>   **1.081637779e-07 W**, drift **2.45e-16** between 24 and 32 radial nodes,
>   i.e. converged. Quadrature degree is **12** (`MAT-4` step 2's measured
>   degree, stated in the log per the latent-degree lesson); recomputing the
>   reference at degree 16 moves it **6.11e-14** relative, so the degree is
>   not load-bearing here.
>   **The number worth carrying:** the power error (3.629%) lands essentially
>   *on* the field relL2 (3.643%), not at twice it. Squaring a field error
>   need not double the functional error — here the interior error is
>   dominantly a phase/sign-varying component that |E|² is insensitive to, and
>   the residual level is the same ~3% floor step 3 traced to geometry rather
>   than wavelength. Read, not gated.
>   **Where the claim now stands:** the volume integral every SAR number
>   routes through is gated against an independent full-wave anchor in the
>   Larmor regime. It gates the *integral only* — no mass averaging, no
>   C95.3 wording, no coil. `MAT-4` stays 🟡 and `TH-10` stays 🟡 pending a
>   review's read on whether its remaining unscoped item (the coil-loading
>   trend across the eddy→displacement transition) belongs to this chunk or
>   to a successor; all four scoped steps are now ✅.
> * **Still unscoped:** the coil-loading trend across the
>   eddy→displacement transition (`MAT-6`'s ΔR machinery) — after the
>   sphere gates, not before.

**`TH-11` — coil-loading trend across the eddy→displacement transition** ⬜
*(commissioned 2026-08-13, 10:30 review, executing the `TH-10` disposition:
the trend validates `MAT-6`'s ΔR machinery — a different route on a different
fixture — so it is its own chunk, per §10 subgoal 3's second named target.
Owns the remaining half of §2.1's extrapolation sentence.)* **Step 1 —
feasibility/cost probe at 64 MHz (measurement only, nothing gated on
physics).** Re-run the `MAT-6` W = 0.25 / `resolution_near` 0.0025 fixture
(ΔR 0.8835% on record at 10 MHz) with f = 64 MHz, complex build, projected
drive. **Anchor (internal identities only):** the complex-power identity
residual < 1e-9 (the step-2f family gate) and reciprocity on the ΔZ read;
the physics read is **printed, never gated** — ΔR/ΔX at 64 MHz beside the
Dodd–Deeds quasi-static prediction, their deviation being the measurement
this chunk exists for (expected to *grow* with f; a large deviation is the
finding, not a failure). **Negative control:** the σ = 0 solve's exact-zero
dissipation (== 0.0, the `EX-11` control) still holds at 64 MHz.
**Tier/cost:** standard, `-n 2` first at the 10 MHz price (70–75 s on
record); stop rule 300 s/solve — 64 MHz may condition differently (`MAT-6`
step 10's ≥ 5.1× lesson), and skin depth shrinks ~2.5× so the mesh may be
under-resolved: if the identity residual blows past 1e-6, that *is* the
step-1 finding (report, stop, do not refine in-slot). **Traps:** standard
list; `timeout -k 30`; the Dodd–Deeds kernel itself is quasi-static — at
64 MHz it is the *comparison*, not the *reference*; never call its deviation
an error. **Scope boundary:** measurement only; §2.1 stays as written until
a gated trend exists; no SAR wording. **Negative result:** any outcome is a
finding — report in §7, park nothing (no src changes licensed).

**`GEO-14` — the shared ~3% geometry floor: discriminate faceting from
resolution** ⬜ *(commissioned 2026-08-13, 10:30 review; entry placed here
beside the fixtures it measures. Three residuals now sit at ~3% on curved
fixtures — `TH-10` 64 MHz field 3.643%, power 3.629%, `MAG-13` CG1 floor —
and the 12:00 slot's hypothesis is one shared sphere/wire-faceting floor.)*
**Step 1 — the one-command discriminator (from the `TH-10` step-3
annotation):** run the 64 MHz gate at the already-priced 55 251-cell mesh
(128 MHz's fine rung, 26 s on record). **Pre-registered bands:** relL2
stays > 3.0% ⇒ the 3.643% is a floor, not resolution — faceting confirmed
as the owner at 64 MHz; falls < 2.0% ⇒ it was resolution and the step-3
inference is wrong; between ⇒ mixed, report both. **Negative control:** the
same run reproduces the 128 MHz record digits at that mesh (1.826%, 57.31×)
— a run that moves the recorded frequency is a bug, not a finding.
**Tier/cost:** standard, `-n 2`, ~30–40 s (26 s on record + one extra
gate). **Traps:** standard; the series r = 0 evaluation offset (1 nm, on
record). **Scope boundary:** measurement only; step 2 (surface-graded
sizing moving all three numbers together) is scoped only after this reads;
`TH-10`'s ✅ does not reopen under any band — its gates are levels, not
floor attributions. **Negative result:** report and annotate `TH-10`/
`MAG-13` §7 entries; nothing parked.

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

**`MAT-4` — SAR computation** 🟡 *(step 1 ✅ 2026-08-03; step 2 ✅ 2026-08-04;
step 3 ✅ 2026-08-07.
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
> * **Step 3 — the averaging operator at the standard masses** ✅
>   *(2026-08-07, 13:30 run; `tests/validation/test_mass_averaged_sar_standard_masses.py`,
>   gate `20260807T183506Z_MAT-4-step3-gate2.log`, 7 passed 17.4 s at `-n 2`,
>   standard tier, complex build)*. The sizing gap is closed: on R = 0.03 m
>   with a uniform complex phasor **imposed** (no solve — degree-1 N1curl
>   contains the constants exactly, so every residual below belongs to the
>   kernel), the uniform-field identity is **exact at both standard masses**
>   — `SAR_avg/SAR_point = 1.00000000` at 1 g (0.207 R) and 10 g (0.446 R),
>   against a 0.5% budget, with the pointwise path agreeing with the closed
>   form `σ|E|²/(2ρ)` to 5e-16. Kernel mass conservation **0.0120% / 0.0044%**
>   against 0.1%. Negative control, the 1 g ball re-centred on `(0,0,R)`:
>   separation **2.1894** against the lens ceiling `1/f` **recomputed for this
>   geometry** — 2.1681 at a/R = 0.2068, *not* step 2's 2.1875 — agreeing to
>   **0.98%** (band 5%, floor > 1.5). **Measured in-run, and it is a fact
>   about the kernel, not the operator:** the first gate run
>   (`…183256Z_MAT-4-step3-gate.log`) failed the 1 g mass gate at **0.3008%**
>   at step 2's quadrature degree 12. The probe sweep
>   (`…183401Z_MAT-4-step3-probe.log`) shows why — the averaging ball is a UFL
>   `conditional`, so the degree resolves the ball's *surface*, and at 2.07
>   cells per ball radius degree 12 is under-resolved: 1 g reads
>   0.7637/0.3008/0.0120/0.0145/0.0039/0.0036% at degrees 8/12/16/20/24/30,
>   non-monotone, i.e. sampling noise rather than a truncation order. Degree
>   **16** was selected as the smallest at which all three placements (1 g,
>   10 g, 1 g-at-surface) sit an order of magnitude inside the 0.1% budget;
>   **no budget was moved**, only the resolution of the region. Consequence
>   for step 2, latent and not a wrong number: its 0.040% at degree 12 was
>   within its own 0.36% budget but is a lucky draw from the same noise, not
>   a floor — a future kernel change should not read it as one. **`MAT-4`
>   stays 🟡**: this closes the operator's sizing gap, not a C95.3 claim,
>   which needs a solved coil+phantom field (§2.1). *(Original plan below.)*
>
>   Step 2 gated the
>   operator at m = 0.05 g because the step-1 sphere cannot contain a 1 g
>   ball — the sizing, not the operator, was the limit. Close that gap on a
>   sphere sized for the standard: R = 0.03 m, ρ = 1000 kg/m³, so the 1 g
>   ball (r = 6.20e-3 m, 0.207 R — the same relative size step 2 gated) and
>   the 10 g ball (r = 1.337e-2 m, 0.446 R, surface clearance 1.24 ball
>   radii) both sit inside with margin. **No solve:** impose the uniform
>   field analytically on the new mesh, exactly as step 2's uniform-field
>   identity does — the subject is the operator, and a solved field would
>   only add the closed form's O((k_inR)²) model error, ~9× step 1's at
>   this R. **Anchor:** `SAR_avg/SAR_point = 1` at **both** masses
>   (0.999846 on record at 0.05 g; gate |ratio − 1| < 0.5%, sized as 2× the
>   step-2 measured-parts budget of 0.26% for the coarser ball-to-mesh
>   ratio), and kernel mass conservation < 0.1% (0.040% on record).
>   **Negative control:** the surface ball — centre the 1 g ball at
>   R − r_ball and assert the ratio drop against the convex-lens ceiling,
>   recomputing `1/f` for this R/r before asserting anything (step 2's was
>   2.1875 at its own geometry; floor > 1.5 and 5% agreement with the
>   recomputed `1/f`, as step 2 gated). **Cost:** standard, `-n 2`,
>   `timeout 180`; no solve — step 2's three gates ran 54.8 s *including*
>   solves; mesh at h = R/10 is the step-1 density. **Traps:**
>   `ComplexComparisonError` — a UFL comparison with a non-zero centre
>   needs `ufl.real`, and the surface ball is exactly the non-origin case
>   (step 2 paid for this); complex build sourced +
>   `FEM_EM_REQUIRE_COMPLEX=1` since `post/sar.py` takes `e_complex`;
>   density via `build_density_field`, never a literal; averaging-ball
>   integrals allreduced. **Does not close:** `MAT-4` — a C95.3 1 g/10 g
>   *claim* needs a solved coil+phantom field, which stays unlicensed
>   (§2.1); this closes the operator's sizing gap only, so the chunk stays
>   🟡. **Negative result:** a ratio off 1 beyond the budget at either
>   mass is an operator defect at scale — report both ratios and the
>   kernel mass error, annotate here, stop.
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
> with `PORT-1` step 2e's spurious-gradient (`W_e^spur`) mechanism.
> *(**Superseded 2026-08-07 by step 5**: the gap does not shrink with the box,
> but it collapses 0.1077 → 0.0005 under wire refinement at fixed W. The
> offset is finite-wire discretisation error; the `W_e^spur` attribution in
> this paragraph is withdrawn. The four ΔX numbers and the box reading below
> stand.)* Note what is
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

**`MAT-6` step 5 — separate the last ~1.5% of ΔX: wire resolution at fixed
box** ✅ *(2026-08-07, 15:00 run;
`tests/validation/test_dodd_deeds_reactance_wire_resolution.py`,
`20260807T201036Z_MAT-6-step5-projected.log` (8 passed, 492 s) and
`20260807T201914Z_MAT-6-step5-pinned.log` (6 passed, 238 s), heavy, `-n 2`,
W = 0.15 fixed, 366 207 cells / 426 722 dofs, four solves at 101–111 s; cost
probes `20260807T200206Z_MAT-6-step5-probe.log` (ladder) and
`20260807T200830Z_MAT-6-step5-probe-solve.log` (one solve, 80.1 s at `-n 4`))*
> **Step 4's finding does not survive this knob: the two drives *converge* in
> ΔX under wire refinement, so the drive-dependent offset was finite-wire
> discretisation error, not the `W_e^spur` mechanism.** The ΔX ratios
> `ΔX_FEM/ΔX_exact` (exact `−6.1586749e-01 Ω`) at fixed W = 0.15:
>
> | drive | `resolution_wire` 0.002 | 0.001 (**here**) |
> |---|---|---|
> | pinned (`project_source=False`) | 0.8123 | **0.9189** (`−5.6589001e-01 Ω`) |
> | projected (production default) | 0.9200 | **0.9194** (`−5.6623884e-01 Ω`) |
>
> The projected drive does not move (−0.0006); the pinned drive moves +0.1066
> and lands on it. The projected-minus-pinned gap collapses **0.1077 → 0.0005,
> a factor of 215**, where step 4 measured that same gap *not* shrinking with
> box size (0.1077 at W = 0.15, 0.1109 at W = 0.25). Read together: the
> solenoidal projection was already delivering, on a coarse wire, the answer
> the refined wire gives both drives — a real and useful property of the
> projection, but the coarse-wire *difference* between the drives is a
> discretisation artefact and step 4's attribution of it to `PORT-1` step 2e's
> spurious-gradient mechanism is withdrawn. Note step 4's box result stands
> unchanged; what is revised is only what the drive gap meant.
>
> **The refinement is real and second-order, measured independently of ΔZ.**
> The faceted torus's volume deficit against `π r² · 2π a` goes
> **8.0310% → 2.0114%, a 3.99× shrink against the O(h²) prediction of 4.00×**
> (`I` = 0.919690 → 0.979886 A). That control is what makes the null projected
> ΔX reading interpretable rather than vacuous: the mesh demonstrably changed
> where it was supposed to, quadratically, and ΔX still did not follow.
>
> **ΔR moves, and the wire — not the box — owns its residual.** ΔR goes
> 1.5834% (projected) / 1.58% (pinned) → **1.0562% / 1.0558%**: 0.53
> percentage-points, i.e. **53× step 4's < 0.01 pp box wobble** across a 2.17×
> cell change. So of the landed 1.58%, roughly a third was wire
> discretisation. The landed number does not move — 1.58% is what the landed
> fixture measures and stays §2.1's claim — but its error budget is now
> attributed. Gates are step 2b's, inherited unchanged: ΔR under the 5% hard
> ceiling, ΔX on sign and order of magnitude only. No ΔX band was tightened.
>
> **Step 2b's literal `h/r_wire ≥ 16` target is not reachable on this
> machine**, and that is a measured statement, not an estimate. Read as cells
> across the wire radius (`r_wire = 0.0025` m fixed), the ladder at W = 0.15
> is 0.002 → 138 619 cells (r_wire/h = 1.25, byte-reproducing step 2b's
> count), 0.001 → 366 207 (2.50), 0.0005 → 1 458 561 (5.00) — and that last
> mesh **OOM-killed at `-n 4`** (signal 9, probe log). The target needs
> `h ≤ 1.5625e-4`, two further doublings past a rung that already will not fit
> in memory. §5.1 forbids buying it with a longer timeout, so 2.50 is the
> refinement this step could execute: it *bounds* the wire-discretisation term
> rather than exhausting it.
>
> **Does not close / does not reopen:** `MAT-6` stays ✅ — this adjudicates a
> finding, not the chunk. No claim in §2.1 moves: the landed 1.58% ΔR is
> untouched, saline/Larmor stays unlicensed (eddy-current kernel), and **ΔX is
> still not gateable anywhere** — neither knob is saturated (the box was still
> moving at W = 0.25; the wire knob is bounded by memory, not by convergence),
> and the filamentary reference's 30% spread over `h ± r_wire` remains
> untouched by either. Arithmetic worth recording but *not* tested: at
> W = 0.25 the box was worth ~+0.065 and here the wire is worth ~0.000 on the
> projected drive, so if the two knobs were additive a converged fixture would
> land near 0.985 — which is step 4's W = 0.25 projected number. That is a
> hypothesis for a later step, not a result; additivity was not measured.
>
> *Original plan, for the record:*
> Step 4 left the projected-drive ΔX ratio at 0.9849 with two unseparated
> residual terms: box truncation (still moving ~+0.06 per 0.10 m of W, so
> not exhausted at W = 0.25) and the filamentary reference's own ~30% spread
> over `h ± r_wire`, which no box can remove. The other knob step 2b named —
> `h/r_wire ≥ 16` local refinement **at fixed W = 0.15** — moves only the
> wire-discretisation term, so the two become separable: a ΔX ratio that
> moves under wire refinement at fixed box is finite-wire error; what
> remains after both knobs saturate is the filamentary-reference ambiguity,
> and only then would a quantitative ΔX gate be defensible. **Anchor:**
> Dodd–Deeds `ΔX = −6.1586749e-01 Ω` / `ΔR = +3.2259615e-01 Ω`, step 2b's
> gates unchanged (ΔR < 5% ceiling; ΔX sign + order of magnitude; **never**
> a ΔX band tightened in-slot — convergence of ΔX is the thing under test).
> The reported result is the projected + pinned ΔX ratios at the refined
> wire beside the four on record from step 4. **Negative control:** on
> record, cite — σ-blind `ΔZ = 0`, null tagging `1.31e-08`; and step 4's
> own W-series is the comparison baseline (any refinement effect must
> exceed the < 0.01 pp ΔR wobble measured there before it is called real).
> **Cost — probe before committing, the step-4 discipline:** current
> `h/r_wire` and the refined cell count are unmeasured; run the mesh + one-
> solve cost probe first (extend `scripts/probes/mat6_step4_probe.py`; heavy
> `timeout 1200`, `-n 4` allowed for the probe only). If one solve exceeds
> ~300 s at `-n 4`, report the measured cost and stop — the rescope is a
> smaller `h/r_wire` target, never a raised timeout (§5.1). Gates at `-n 2`
> (allreduced current + reaction integral), split by `-k` into per-drive
> commands if four solves exceed one command's ceiling, exactly as step 4
> did. **Traps:** `project_source=False` pins stay; separate module
> importing the step-2b/3/4 fixtures (nothing restated); local refinement
> means `resolution_far` stays put — refine the wire region only, or the
> far-field cell count explodes; stale FFCx lock; `ufl.max_value`; complex
> build + `FEM_EM_REQUIRE_COMPLEX=1`. **Does not close / reopen:** `MAT-6`
> stays ✅ regardless; ΔX becomes gateable only in a *later* step once both
> knobs are saturated, never in this one; saline/Larmor stays unlicensed.
> **Negative result:** a ratio that does not move under refinement says the
> residual is reference ambiguity + box tail — that is the finding; report
> all ratios, annotate this entry, stop.

**`MAT-6` step 6 — the additivity hypothesis: both knobs at once** 🚫
*(attempted 2026-08-08, 13:30 run — **stopped on the entry's own pre-registered
cost rule; the additivity ratio was not measured.** Probe logs
`20260808T183121Z_MAT-6-step6-probe.log` (`-n 4`, 314 s, signal 9) and
`20260808T183648Z_MAT-6-step6-probe-n8.log` (`-n 8`, 184 s, exit 137);
`scripts/probes/mat6_step6_probe.py`. Scoped 2026-08-07, 18:00 review — the
step-5 entry's own "hypothesis for a later step", promoted now that both
single-knob moves are measured. Heavy spare; memory, not time, is the binding
constraint.)*
> **Result: the combined fixture meshes but does not solve inside the
> container's memory, at either rank count the entry authorised — so the point
> of no return closed and the step stopped, exactly as pre-registered.**
> Measured:
>
> | run | ranks | cells | mesh | killed after | signal |
> |---|---|---|---|---|---|
> | probe | 4 | 697 401 | 51.9 s | ~262 s of solve | 9 |
> | probe retry | 8 | 697 401 | 46.5 s | ~138 s of solve | 137 (128+9) |
>
> No ΔZ, no ΔX ratio, nothing to compare against the 0.9843 additive
> prediction. The prediction stands unmeasured and the hypothesis is neither
> confirmed nor killed.
>
> **The entry's retry rule rests on a false premise, and that is the reusable
> finding.** "OOM ⇒ retry at `-n 8` (memory per rank halves)" only helps when
> the limit is *per rank*. It is not: the container is capped at **16 G**
> (`docker/docker-compose.yml`, `deploy.resources.limits.memory`) while the
> host had **747 G of 754 G free** at probe time — so the binding constraint is
> a cgroup ceiling on the job's **total** footprint, which more ranks cannot
> lower and (through per-rank duplication) tends to raise. The `-n 8` retry
> died sooner than `-n 4`, consistent with that reading. **This also re-reads
> step 5's record:** its 1 458 561-cell rung "OOM-killed at `-n 4`" was the same
> 16 G container ceiling, not a machine limit, and step 5's conclusion that
> `h/r_wire ≥ 16` is "not reachable on this machine" is therefore an overstated
> attribution — it is not reachable *in this container as configured*. Nothing
> measured in step 5 changes; only the cause named for the ceiling does.
>
> **Mesh-count composition, measured in passing and worth keeping.** Against
> the W = 0.15 coarse-wire baseline of 138 619 cells, the box knob alone gives
> 300 591 (2.1685×) and the wire knob alone 366 207 (2.6418×), so a
> multiplicative composition predicts 794 166 cells; the combined mesh is
> **697 401, i.e. 87.8% of that — 12.2% sub-multiplicative**. Expected in sign
> (the volume the larger box adds is all far-field at `resolution_far = 0.025`,
> untouched by the wire knob) and it is why the entry's ~790 k estimate came in
> high. The count reproduced **byte-identically at `-n 4` and `-n 8`**, so the
> mesh is rank-independent as the fixtures assume. Note this says nothing about
> ΔX additivity — cell counts are not the quantity under test.
>
> **Rescope for a review, not for a slot.** §5.1 forbids buying the run with a
> longer timeout and this entry forbids improvising a different case in-slot,
> so the run stopped. Three candidate routes, none of them taken here: (i)
> raise the 16 G container limit — the machine plainly has the headroom, but
> the compose file is shared infrastructure and the §5 budget never priced
> memory, so it is a human/review decision; (ii) a smaller combined case
> (W = 0.20 at `resolution_wire = 0.001`, or W = 0.25 at 0.0015) — cheaper but
> it measures the composition of two knobs at settings neither single-knob run
> used, which weakens the comparison against 0.9843; (iii) drop the step —
> additivity is a convenience for extrapolating ΔX, and ΔX is ungateable either
> way. The first is the only route that answers the question as posed.
>
> **Does not close / reopen:** `MAT-6` stays ✅; §2.1's 1.58% untouched; ΔX
> stays ungateable, now for the additional reason that its extrapolation
> shortcut is still unvalidated.

*Original plan, for the record:*
> Step 4 measured the box knob at coarse wire (projected ΔX ratio
> 0.9200 → 0.9849 for W 0.15 → 0.25); step 5 measured the wire knob at fixed
> box (0.9200 → 0.9194 at W = 0.15). If the knobs are additive, the combined
> fixture — **W = 0.25 `resolution_wire = 0.001`, projected drive only** —
> lands at `0.9194 + 0.9849 − 0.9200 = 0.9843`. Measuring it says whether the
> two residual terms can be extrapolated independently, which is the
> precondition for ever writing a defensible ΔX gate. **Probe first, and the
> probe is the point of no return:** mesh count at the combined parameters
> (~790 k cells predicted from the two measured growth factors — 366 207 ×
> the step-4 W-growth; the 1 458 561-cell rung OOM-killed at `-n 4`, signal
> 9, on record), then **one** solve at `-n 4`; OOM ⇒ retry that single probe
> solve once at `-n 8` (memory per rank halves, cap 12 respected); still OOM
> or > 300 s ⇒ **report the measured cost and stop** — the rescope is a
> smaller case, never a raised timeout (§5.1). **Anchor:** Dodd–Deeds
> `ΔX = −6.1586749e-01 Ω` / `ΔR = +3.2259615e-01 Ω`, step 2b's gates
> inherited unchanged (ΔR < 5%, ΔX sign + order; never a ΔX band tightened
> in-slot). The *reading* is the additivity defect
> `ratio(0.25, fine) − 0.9843`, pre-decided: |defect| ≤ 0.5 pp ⇒ consistent
> with additive; > 1.5 pp ⇒ a real cross-term (single-knob extrapolation
> invalid); between ⇒ ambiguous, report-and-stop. **Negative control:** the
> volume-deficit control re-asserted on the new mesh (step 5's O(h²)
> mechanism, floor > 1.5× shrink vs the W = 0.25 coarse-wire deficit); the
> < 0.01 pp ΔR box wobble stays the reality floor. **Cost:** heavy; gate
> `-n 2` preferred, one command `timeout 1200`, projected drive only
> (step 5's projected gate was 492 s at 366 k cells — ~790 k may not fit one
> ceiling; if the probe solve says it will not, or `-n 2` cannot fit memory,
> `-n 4` for the gate is pre-authorized with a note — the fixture's
> reductions were exercised at `-n 2` in steps 2b–5). **Traps:** step 5's
> list unchanged (`project_source=False` pins, separate module importing the
> fixtures, `resolution_far` stays put, FFCx lock, `ufl.max_value`, complex
> build + `FEM_EM_REQUIRE_COMPLEX=1`); do not re-run the pinned drive — its
> convergence to the projected answer is step 5's result, not this step's
> question. **Does not close / reopen:** `MAT-6` stays ✅; ΔX stays
> ungateable regardless of outcome (neither knob is saturated — this
> measures their *composition*, not their limit); §2.1's 1.58% untouched.
> **Negative result:** a cross-term is the more informative outcome — it
> kills the extrapolation shortcut before anything downstream trusts it;
> report the measured ratio beside the 0.9843 prediction, annotate here,
> stop.

**`MAT-6` step 7 — raise the container memory cap to 64 G, verify it took,
and measure the additivity ratio step 6 could not** ✅ *(closed 2026-08-11,
16:30 run, by Part 2c — the additivity reading is **0.9835 vs the 0.9843
prediction, defect −0.080 pp, consistent with ADDITIVE**; see the Part 2c
paragraph below. Part 1 ✅
2026-08-10, interactive session — **the operator approved the cap raise and
the edit went through with the human answering the `ask` prompt**, resolving
the blocker below by route (a)/the compose edit: `docker/docker-compose.yml`
`limits.memory: 16G → 64G` (reservation stays 4G), service recreated
(`up -d`, Up), and the cap verified at the kernel before anything else:
`/sys/fs/cgroup/memory.max` = **68719476736** — the exact value Part 1's
plan names. Part 2 — the additivity measurement against 0.9843 — remains
unrun and is now executable in a scheduled slot per the original scoping
below; the new headroom also un-sticks step 5's 1 458 561-cell rung and
loosens step 8's cost gate. The 12-core and 20-minute ceilings are
untouched: this bought memory, not compute.)*

*Part 2 rescoped, 2026-08-11 03:00 review — **three consecutive slots
(19:30, 22:30, 00:00) attempted Part 2 as scoped above and all three died
the same way, none of it physics.** Root cause, established from
`logs/automation/*_implementer.log` (each session exited **0** after 2–5
minutes) and the three footerless probe logs: each session launched the
harness run as a background Bash task, wrote "waiting on the solve", and
ended its turn — which in headless `claude -p` mode exits the CLI and
SIGKILLs the harness. Not OOM (dmesg's only memcg kills are step 6's, Aug 8,
at 16 G), not the 65-min wrapper, not a late start (the 21:00 anomaly
entry's hypothesis — 19:30's probe started one minute into its slot). What
the night did establish, three times over: the 64 G cap is in effect at the
kernel (`memory.max` = 68719476736) and the combined mesh reproduces
byte-identically at 697 401 cells (51.9/51.5/56.1 s). The solve never ran
more than ~2.5 min before its session died; **its cost at 64 G is still
unmeasured**. The orphaned artifacts — the drafted, never-executed gate
module `tests/validation/test_dodd_deeds_reactance_combined_knobs.py` and
the three probe logs — are landed on main (chore(recover), 2026-08-11); the
module is input, not evidence. **Rescoped run recipe (supersedes the
`timeout 1200` instruction below, which is unrunnable in a scheduled slot):**
run the probe **foreground**, Bash-tool `timeout` parameter at 660000 ms,
container-side `timeout 590` (mesh ~56 s + solve window ~530 s). Exit 124 is
a *result*: "solve > 530 s at `-n 4` under 64 G" is the cost measurement —
record it, annotate here, stop; do not retry at more ranks in the same slot
and do not background anything. Any other exit gives the first real
additivity reading or a real OOM record. The 0.9843 bands, anchors,
negative controls, and no-retry rationale below are unchanged.*

*Part 2 executed under the rescoped recipe, 2026-08-11 04:30 run — **the
recipe works and the solve cost is measured at last, but the additivity
reading is not.** Foreground harness call, Bash-tool `timeout` 660000 ms,
container-side `timeout 590`: exit **0**, elapsed 427 s
(`20260811T093111Z_MAT-6-step7-part2-probe.log`). Cap re-read first,
`memory.max` = 68719476736. Mesh **697 401 cells in 51.7 s** — the same
count a sixth time. **One projected loaded solve: 372.9 s at `-n 4`,
813 287 global dofs, no OOM** — the fixture that step 6 saw killed twice at
16 G (`-n 4` signal 9 at ~262 s, `-n 8` exit 137 at ~138 s; cited, not
recomputed) now runs to completion at 64 G. 372.9 s > the 300 s threshold,
so the pre-decided stop rule fired: reported, stopped, no retry at more
ranks in-slot, gate module left unrun and still unverified. **New measured
constraint:** the gate's loaded+free pair prices at ~746 s solve + 52 s mesh
= **~797 s**, which is inside the heavy 1200 s tier but **outside the 660 s
hard maximum of the Bash tool's foreground `timeout`** — so the gate cannot
be run in one foreground call in a scheduled slot at `-n 4`, and
backgrounding is what killed three slots. Options for the review, in cost
order: (1) `-n 8` — the 16 G no-retry rule addressed a rank-blind *memory*
ceiling, and memory is no longer the binding constraint; one ~4-min probe
answers it; (2) split the pair across two harness calls and combine the
impedances (needs the module restructured); (3) shrink the fixture (loses
step 6's case). The O(h²) volume-deficit control is still not re-asserted —
outside the probe. Step 7 stays 🟡; `MAT-6` stays ✅; the 0.9843 reading
remains the open deliverable.*

*Route decision, 2026-08-11 10:30 review — **option (1), the `-n 8` cost
probe, is taken** (§9 item 1; the conditional gate run is §9 item 4). The
16 G no-retry rule was about a rank-blind memory ceiling and memory is no
longer binding at 64 G; ~4 minutes of probe answers whether the loaded+free
pair fits one foreground call at `-n 8`. Option (2) (split the pair across
two harness calls) is the named fallback if `-n 8` prices the pair above the
~530 s solve window; option (3) (shrink the fixture) stays last. The gate,
when it runs, must also re-assert the O(h²) volume-deficit control the probe
skips. Rank-width caveat, stated now so the gate slot does not have to argue
it: the additivity **reading** is a measurement at `-n 8`; the Dodd–Deeds
anchors it inherits were gated at `-n 2` in step 2b and are not re-gated
wider.*

*Part 2b executed, 2026-08-11 12:00 run — **option (1) is confirmed
green: 179.3 s at `-n 8`, and the gate fits one foreground call.**
Foreground harness call, container `timeout 590`, Bash-tool `timeout`
660000 ms: exit **0**, elapsed 229 s
(`20260811T170103Z_MAT-6-step7-part2b-probe-n8.log`). Cap re-read first,
`memory.max` = 68719476736. Mesh **697 401 cells in 46.6 s** — the same
count a seventh time, and the cheapest mesh on record. **One projected
loaded solve: 179.3 s at `-n 8`, 813 287 global dofs, no OOM** — the same
dof count as the `-n 4` record, so this is one problem priced at two
widths: **2.08× speedup for 2× the ranks, superlinear**, consistent with
the smaller per-rank working set at 64 G. Negative control, cited not
recomputed: step 6's `-n 8` kill at 16 G (exit 137, ~138 s) on this exact
fixture — the same rank width that died then completes now, so the cap
raise is what changed, not the rank count. **Decision rule (§9 item 1,
pre-committed as solve ≤ ~240 s) fires green with 60.7 s of margin:** the
loaded/free pair prices at **~359 s solve + 47 s mesh = ~405 s**, ~125 s
inside the 530 s solve window and far inside the Bash tool's 660 s
foreground maximum. Consequences: option (2) (split the pair across two
harness calls, module restructure) is **not needed**; §9 item 4's skip
clause does **not** fire; the gate runs at `-n 8` with container `timeout`
~470 s (mesh + 2× solve + 60 s margin). Untouched, still owed by the gate:
the gate module has never executed, the O(h²) volume-deficit control is
not re-asserted, and **0.9843 remains unmeasured**. Step 7 stays 🟡;
`MAT-6` stays ✅.*

*Part 2c executed, 2026-08-11 16:30 run — **step 7 closes: the two mesh
knobs are additive, and the gate module's first execution is green on all
four tests.** Foreground harness call, `-n 8`, container `timeout 470`
(sized from Part 2b's measurement: mesh + 2× solve + 60 s margin),
Bash-tool `timeout` 660000 ms: exit **0**, elapsed 423 s, 4 passed in
421.9 s (`20260811T213057Z_MAT-6-step7-part2c-gate-n8.log`); a 3 s
collect-only smoke ran first to catch import bugs before the spend
(`20260811T213045Z_MAT-6-step7-part2c-collect.log`, 4 tests collected).
Cap re-read first, `memory.max` = 68719476736. **The reading:
ΔX ratio 0.9835 against the additive prediction 0.9194 + 0.9849 − 0.9200 =
0.9843 → defect −0.080 pp**, well inside the pre-decided ≤ 0.5 pp band, so
the verdict is **consistent with ADDITIVE** — no cross-term, and
single-knob extrapolation on this fixture is a defensible shortcut rather
than an assumption. The band was pre-decided in step 6 and the ratio is
reported, never asserted, exactly as drafted. **Inherited gates, both
green:** ΔR **0.8835%** of Dodd–Deeds (FEM `+3.2544615e-01 Ω` vs exact
`+3.2259615e-01 Ω`) under step 2b's unwidened 5% ceiling — and note that
the combined fixture is *sub-1% on ΔR* without step 8's slab knob, against
1.5834% at W = 0.15 coarse wire and 1.0562% fine; ΔX sign negative (flux
expelled) and ratio inside the order-of-magnitude gate. **The O(h²)
volume-deficit control the probe skips is now re-asserted on this mesh:**
meshed torus `I = 0.979886 A`, deficit **2.0114%** against the coarse
wire's 8.0310% → **3.99× shrink** vs the ~4× O(h²) prediction, reproducing
step 5's 3.99× at W = 0.15 — the box knob did not disturb the wire
discretisation. Mesh **697 401 cells** an eighth time, 46.1 s, 5.03× the
138 619 baseline; solves **196.2 s + 178.2 s** at `-n 8`, i.e. 374.4 s
against Part 2b's ~359 s projection (4.3% over, and the whole pair landed
420.5 s against the ~405 s estimate — Part 2b's pricing was accurate).
Negative control cited, never recomputed: step 6's two 16 G kills on this
exact fixture. **Rank-width caveat, as stated by the route note:** the
additivity reading is a measurement at `-n 8`; the Dodd–Deeds anchors it
inherits stay gated at `-n 2` from step 2b and were not re-gated wider.
`MAT-6` stays ✅ (this never reopened it); ΔX remains reported, not gated.*

*Blocked-attempt record, 2026-08-08, retained:* *(attempted 2026-08-08,
19:30 run — **blocked before any compute: a scheduled session cannot edit
`docker/`.** `.claude/settings.json` lists `Edit(docker/**)` under
`permissions.ask`, and an `ask` rule in a headless run is a denial — there is
no human to answer it. The `Edit` call on
`docker/docker-compose.yml` (`limits.memory: 16G → 64G`) was denied outright,
so Part 1 could not start and Part 2 has no cap to measure under. Nothing was
run, nothing measured; the 0.9843 additivity prediction stands unmeasured
exactly as step 6 left it. **The container's cgroup limit was read and is on
record: `/sys/fs/cgroup/memory.max` = 17179869184 (16 G)** — the cap step 6
inferred from the compose file is confirmed at the kernel, so the diagnosis
does not depend on a file read. **Unblocking is a one-line human decision, not
a physics question:** either move `Edit(docker/**)` from `ask` to `allow` in
`.claude/settings.json` (widest, and it hands scheduled runs the shared
infrastructure), or narrow it to the single file, or have the human make the
16G → 64G edit once by hand and let a later slot run Part 2 against it. The
third is the smallest change and keeps the guard intact — this step's Part 2
needs the cap raised, not the ability to raise it. Escalated to the daily
review, which owns allowlist proposals (implementer-run.md, "Working inside
the permission allowlist").*

*Original scoping, retained verbatim for the record (18:00 review — this is
the review decision step 6 escalated: route (i) taken.*
*Rationale: the host had 747 G of 754 G free at probe time, §5.1 prices cores
and wall clock and has never priced memory, and 64 G is 8.5% of the box and
transient — 4× the current cap covers both the 697 401-cell combined case and
step 5's 1 458 561-cell rung with headroom. The 12-core and 20-minute
ceilings are untouched; this buys memory, not compute.)*
> **Part 1, infrastructure:** edit `docker/docker-compose.yml`
> `deploy.resources.limits.memory: 16G → 64G` (reservation stays 4G), recreate
> the service (`docker compose -f docker/docker-compose.yml up -d`), and
> verify the cap took *before* any solve: read the container's cgroup limit
> (`docker compose exec -T fem-em-solver bash -lc 'cat
> /sys/fs/cgroup/memory.max'` — expect 68719476736; fall back to `docker
> stats --no-stream` if the cgroup path differs) and record the number in the
> log. A recreate mid-grid is acceptable: each slot recreates nothing and the
> harness preflight checks the service is Up. **Part 2, the measurement:**
> re-run step 6's probe (`scripts/probes/mat6_step6_probe.py`) exactly as its
> entry authorised — mesh count (697 401 on record, byte-identical at two
> rank counts), then one solve at `-n 4`, `timeout 1200`; still OOM at 64 G
> or > 600 s of solve ⇒ report the measured cost and stop (no retry at more
> ranks — step 6 showed a total-footprint ceiling is rank-blind). **Anchor:**
> step 6's, inherited verbatim — Dodd–Deeds refs with step 2b's gates
> unchanged; the reading is the additivity defect vs **0.9843** with the
> pre-decided bands (≤ 0.5 pp additive / > 1.5 pp cross-term / between
> ambiguous). **Negative control:** step 6's two kill records on the same
> fixture at 16 G (`-n 4` signal 9 at ~262 s, `-n 8` exit 137 at ~138 s) —
> cite, never recompute; the O(h²) volume-deficit control re-asserted on the
> new mesh per the step-6 plan. **Cost:** heavy tier, one solve command
> `timeout 1200`; the mesh is 51.9 s on record; solve cost beyond ~262 s is
> unmeasured — that is the point of the step. **Traps:** step 6's list
> (complex build + `FEM_EM_REQUIRE_COMPLEX=1`, `project_source=False` pins,
> FFCx lock after a kill, `ufl.max_value`); the compose edit must be
> committed with the run, not left dirty; if the recreate fails, restore
> 16 G and stop — a down service costs every later slot. **Does not close /
> reopen:** `MAT-6` stays ✅; ΔX stays ungateable either way; §2.1
> untouched; step 6 stays 🚫 as its own record. **Negative result:** OOM at
> 64 G is a real per-cell memory measurement — report it beside the cap and
> the cell count, annotate here, stop; a cross-term reading is the more
> informative physics outcome, per step 6.

**`MAT-6` step 8 — ΔR error budget: the slab-resolution knob** ✅
*(2026-08-11, 07:30 run; `20260811T125226Z_MAT-6-step8-gate-final.log`,
9 passed, 384 s, heavy, `-n 2`, complex build; probes
`20260811T123143Z_MAT-6-step8-probe-mesh.log` (ladder, 44 s) and
`20260811T123242Z_MAT-6-step8-probe-solve.log` (one solve, 138 s))*
> **The residual is skin-depth resolution, not the coil model — and the
> fixture is now sub-1% on ΔR.** Moving only `resolution_near` 0.005 → 0.0025
> (3.18 → 6.37 cells per δ = 15.9 mm) at fixed `resolution_wire = 0.002`,
> W = 0.15 and fixed near-region extents takes the projected-drive ΔR from
> **1.5834% to 0.2829%** of the Dodd–Deeds `ΔR = +3.2259615e-01 Ω`
> (FEM `+3.2168355e-01 Ω`) — a **−1.3005 pp** move at the *same* wire rung,
> 130× step 4's < 0.01 pp box-wobble reality floor. Step 5's wire knob alone
> reached 1.0562%, so the slab knob is the larger of the two terms and the
> ~1.06% step 5 left unattributed is now attributed: it is the ohmic boundary
> layer under-resolved at ~3 cells per skin depth, and a sub-1% fixture needs
> **more slab mesh, not a thinner wire**. The filamentary-reference mismatch
> (h/r_wire = 8) is correspondingly bounded *below* 0.2829% at this rung —
> it cannot be the dominant term it was a candidate for. §7's naive ~8×
> cell-growth bound was pessimistic: the measured ladder is 138 619 → 209 964
> (0.0035) → **417 914** (0.0025), i.e. 3.01×, so the 0.0035 rescope rung was
> never needed. **Cost, all inside the gates:** one projected loaded solve
> 108.8 s at `-n 4` / 486 694 global dofs, against the > 300 s stop rule;
> the gate's loaded/free pair at `-n 2` cost 176.8 s + 170.0 s + 35.6 s of
> mesh. **Controls, all green:** the σ-blind control re-asserted on the new
> mesh — ohmic `R = ½∫σ|E|²·2/I²` is `+3.2168355e-01 Ω` loaded and **exactly
> `+0.0`** free (no tolerance, infinite separation by construction), and it
> agrees with the reaction-integral ΔR to all printed digits, a second route
> to the same number; the knob is proven slab-local by the meshed wire current
> reproducing the on-record 0.919690 A to **0.0000%** (8.0310% volume deficit
> unmoved), so no part of the ΔR move is the 1/I² prefactor; the cell count is
> asserted at the probe's exact 417 914. ΔX reported, never gated: ratio
> **0.9160** (step 3's landed 0.9200 on the same drive), sign and order of
> magnitude only. Two independent gate runs produced bit-identical ΔZ.
> **Does not close / does not reopen:** `MAT-6` stays ✅ and §2.1's landed
> 1.58% is unmoved — that number is the *landed fixture's* and this is a
> refinement study on a separate module; the `ANS-1` comparison numbers stay
> the landed fixture's; the 5% ceiling is inherited unchanged and was not
> tightened in-slot; saline/Larmor stays unlicensed (eddy-current kernel).
> **For the review:** promoting 0.0025 to the production fixture is a real
> option now (3.01× cells, ~6 min at `-n 2`) but is a scoping decision this
> slot did not take — it would move §2.1's headline number and every downstream
> citation of it.
>
> *Review decision, 2026-08-11 10:30 — **promotion deferred, deliberately.**
> `ANS-1`'s SPEC/COMPARISON numbers are the landed fixture's, and the human
> operator has not yet run the Ansys replication (Waiting-on-you since
> 2026-08-05); changing the production fixture mid-replication would move the
> numbers the operator is replicating against. The 0.2829% record stands as a
> refinement-study result; promotion is re-decidable the review after `ANS-1`'s
> comparison is adjudicated, and must move §2.1, the `ANS-1` docs, and every
> downstream citation in one commit.*

*(Original scoping, retained: scoped 2026-08-10, interactive session at
operator direction.)*
> Step 5 attributed roughly a third of the landed 1.58% ΔR error to wire
> discretisation (1.5834% → 1.0562% under `resolution_wire` 0.002 → 0.001 at
> fixed box), and step 4 bounded the box term at < 0.01 pp of wobble past
> W = 0.15. The remaining ~1.06% is unattributed between two candidates this
> step separates: **skin-depth resolution in the slab** (`resolution_near`
> = 0.005 gives ~3.2 cells per δ = 15.9 mm, degree-1 Nédélec, and the ohmic
> boundary layer decays as e^(−z/δ)) versus the **filamentary-reference
> mismatch** (the closed form is evaluated for an ideal loop at (a, h); the
> meshed coil is a 2.5 mm wire, h/r_wire = 8 against step 2b's ≥ 16 target,
> which step 5 measured as unreachable in the container as configured). Move
> only the slab knob: `resolution_near` 0.005 → 0.0025 (~6.4 cells/δ) at
> fixed `resolution_wire = 0.002`, W = 0.15, **projected drive only** (two
> solves, loaded + free). A ΔR that moves ~1 pp toward the closed form
> attributes the residual to skin-depth resolution and names the knob a
> sub-1% fixture would need; a ΔR that barely moves says the residual is the
> coil-model mismatch, which no slab mesh can remove — either reading closes
> the budget. **Anchor:** Dodd–Deeds `ΔR = +3.2259615e-01 Ω`; step 2b's 5%
> ceiling inherited unchanged and never tightened in-slot; the reported
> result is the refined-slab ΔR relative error beside the measured ladder
> (1.5834% at wire 0.002 / 1.0562% at wire 0.001). ΔX reported, never gated,
> exactly as everywhere else in `MAT-6`. **Negative controls:** on record,
> cite — σ-blind `ΔZ = 0` (100% separation) and null tagging `1.31e-08`
> (`20260731T110515Z_MAT-6-step2b-gate-numbers.log`); the σ = 0 solve's
> `R = +0.0` exactly (no tolerance) re-asserted on the new mesh; the reality
> floor is step 4's < 0.01 pp box wobble — a slab-refinement effect below it
> is not called real. **Cost — probe first, point of no return (steps 4–6
> discipline):** the refined-slab cell count is unmeasured (naive bound: the
> near region's cells grow ~8×; baseline 138 619 total). Extend the
> `scripts/probes/mat6_step*_probe.py` pattern: mesh count, then **one**
> solve at `-n 4`, heavy `timeout 1200`; OOM or > 300 s ⇒ report the
> measured cost and stop — the 16 G cap is total-footprint and rank-blind
> (step 6's finding; no retry at more ranks), and the rescope is a smaller
> refinement ratio (0.005 → 0.0035), never a raised timeout (§5.1). Gate at
> `-n 2`. **Traps:** step 5's list unchanged — `project_source=False` pins
> untouched, separate module importing the step-2b fixtures (nothing
> restated), `resolution_far` and `resolution_wire` stay put, stale FFCx
> lock after a kill, `ufl.max_value` complex trap, complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first. The near-box
> extents (`near_depth = 0.05` etc.) also stay put — this refines cell size
> inside the region, not the region. **Does not close / does not reopen:**
> `MAT-6` stays ✅; §2.1's landed 1.58% and the `ANS-1` comparison numbers
> are the landed fixture's and do not move; saline/Larmor stays unlicensed
> (eddy-current kernel). **Negative result:** a ΔR pinned near 1.06% under
> slab refinement is the finding — the residual is reference ambiguity, and
> any future sub-1% claim needs a finite-cross-section closed form or a
> thinner wire, not more mesh; report both numbers, annotate here, stop.

**`MAT-6` step 9 — ΔX box-truncation attribution: the third W rung** ✅
*(2026-08-12, 22:30 run; `20260812T034631Z_MAT-6-step9-gate-final.log`,
9 passed, 427 s, heavy, `-n 8`, complex build; probe
`20260812T033054Z_MAT-6-step9-probe.log` (595 391 cells, one solve 271.3 s at
`-n 4`, inside the 300 s stop rule); superseded first gate run
`20260812T033830Z_MAT-6-step9-gate-n8.log` (1 failed / 8 passed — the refuted
control below), whose ΔZ is bit-identical to the final run's.)*
> **Truncation owns the ΔX residual.** The third rung lands the projected
> coarse-wire trend at **0.9200 (W = 0.15) → 0.9849 (0.25) → 0.9960 (0.35)**,
> and the free-exponent power-law fit `ratio(W) = r∞ − C·W^(−p)` through the
> three points extrapolates to **r∞ = 1.0023 at p = 3.045**, i.e. **+0.226 pp**
> from unity against the pre-decided ≤ 1 pp band. The measured exponent is the
> physics: a current loop's truncated far field is dipolar, and p ≈ 3 is what a
> 1/W³ tail predicts — the fit was not given that exponent, it recovered it.
> Step 7 Part 2c's unattributed last ~1.6% of ΔX is therefore box truncation,
> and the finite-cross-section reference is **not** needed to explain it.
> **Cost:** 595 391 cells (4.30× the W = 0.15 baseline, 1.98× W = 0.25 — the
> growth is far-field-dominated at `resolution_far = 0.025`), mesh 37.7 s,
> solves 190.1 s + 197.2 s at `-n 8`. Run at `-n 8`, not `-n 2`: the probe
> priced one solve at 271.3 s at `-n 4`, so a `-n 2` pair is ~18 min and does
> not fit one foreground command; every reduction in the reaction integral and
> the current is imported verbatim from the step-2b/step-3 modules that CI
> exercises at `-n 2`, and step 7 Part 2 established `-n 8` on this fixture
> family. Two independent gate runs produced bit-identical ΔZ.
>
> **A negative control was refuted by its own first run, and the refutation is
> the step's second finding.** The module asserted ΔR *box-invariance* — on
> record ΔR moves 1.5834% → 1.5763% across W = 0.15 → 0.25, 0.0071 pp — inside
> a 0.10 pp band set at ~14× that wobble. W = 0.35 moved it **0.3797 pp, to
> 1.1966%**: 53× the wobble, 3.8× the band. **The band was not widened** (§7's
> standing rule); the premise is what the measurement disproved. The hypothesis
> that control existed to exclude — "the mesh changed under the fixture, so the
> ΔX trend is meaningless" — is separately excluded by two sharper checks that
> both passed inside bands fixed *before* the run: the cell count is the
> probe's exact 595 391, and the drive current I' is invariant to **5.92e-08 A**
> against a 2e-4 A band. So the fixture is intact and **ΔR is simply not
> box-converged at W = 0.25**: it carries a truncation term of its own, worth
> ~0.38 pp, which step 8's error budget could not see because it held W = 0.15
> fixed. The test is retained as a measurement, asserting only the direction
> the truncation hypothesis predicts (a bigger box truncates less, so the ΔR
> error shrinks) — recorded in-module as a consistency check written after the
> sign was seen, **not** one of the assertions carrying §4. Those are the 5% ΔR
> ceiling, the exact cell count, and the pre-run I' band.
> **For the review:** the ΔR reading is new information for the step-8 budget —
> box truncation and skin-depth resolution are now both live ΔR terms, measured
> on disjoint fixtures (W = 0.35/slab 0.005 here; W = 0.15/slab 0.0025 there),
> and whether they compose is the same question step 10 asks of the other pair.
> *(Review note, 2026-08-12 03:00: taken up. Any future composed-ΔR rung
> reads composition on the **signed FEM ΔZ values**, never on the relative-
> percent errors — the naive percent arithmetic here (1.1966% − 1.3005% < 0)
> already shows the percent terms cannot be additive offsets. Step 10 itself
> is gated behind step 10a's cost attribution.)*
> **Does not close / does not reopen:** `MAT-6` stays ✅; **no ΔX band was
> written or tightened** — the extrapolated endpoint is the input to a future
> gate-authoring step, which stays deferred per the 18:00 review decision;
> §2.1's landed 1.58% and the `ANS-1` numbers are the landed fixture's and do
> not move; saline/Larmor stays unlicensed.

*(Original scoping, retained: scoped 2026-08-11, 18:00 review — decision (2);
this is the first of the two follow-ons the step-7 Part 2c entry flagged for a
review. Queued as §9 item 3.)*
> Step 7 Part 2c left ΔX converging to ~0.98, not 1.00, with the last
> ~1.6% unattributed; box truncation at W = 0.25 is the named suspect, and
> step 4's own sweep — projected ratio **0.9200 at W = 0.15 → 0.9849 at
> W = 0.25** — is two points of the trend a third rung would pin. Solve
> **W = 0.35 at coarse wire** (`resolution_wire = 0.002`; additivity is
> green, so the coarse-wire trend transfers), projected drive only, one
> loaded + free pair; report the three-point ratio trend and its W → ∞
> extrapolation. **Probe first, point of no return (step-4 discipline):**
> mesh count, then one solve at `-n 4`, stop at > 300 s or OOM — W = 0.35's
> cell count is unmeasured (W = 0.25 was 300 591 cells, 2.17× the baseline,
> 18–22 s mesh, 81 s solve at `-n 4`; the growth is far-field-dominated at
> `resolution_far = 0.025`, so ~2–2.5× again is an estimate, not a
> measurement). **Anchor:** Dodd–Deeds `ΔX = −6.1586749e-01 Ω`,
> `ΔR = +3.2259615e-01 Ω`, step 2b's gates inherited unchanged (ΔR < 5%
> hard ceiling; ΔX sign and order of magnitude only); the reading —
> the trend and extrapolated endpoint — is **reported, never gated**, for
> exactly step 4's stated reason: the box convergence of ΔX is the thing
> under test. **Negative control:** ΔR box-invariance on record (< 0.01 pp
> across W = 0.15 → 0.25, drives identical to 5e-5) — a ΔR that moves with
> W says the fixture changed, not the truncation. **Cost:** heavy; complex
> build + `FEM_EM_REQUIRE_COMPLEX=1`; gate at `-n 2` (allreduced current
> and reaction integral, step 4's note), split by `-k` into two commands if
> the pair exceeds one ceiling. **Traps:** step 4's list — import geometry,
> tags, and both solve routines from the step-2b/step-3 modules, restate
> nothing; `project_source=False` pins untouched; stale FFCx lock;
> `ufl.max_value`. **Does not close / does not reopen:** `MAT-6` stays ✅;
> no ΔX band is written or tightened in-slot — the extrapolated endpoint is
> the *input* to a future gate-authoring step, which stays deferred until
> this attribution lands (18:00 review decision). **Negative result:** an
> extrapolation that plateaus visibly below 1.00 says the residual is not
> truncation — the finite-cross-section reference becomes the next suspect,
> and a ΔX gate needs a better reference before it needs a bigger box; that
> is the more informative reading. Report all three ratios and the fit,
> annotate here, stop.

**`MAT-6` step 10 — do the two sub-1% routes compose? Slab knob on the
combined fixture** 🟡
*(attempted 2026-08-12, 00:00 run — **the probe's stop rule fired and the
step is blocked on solve cost, not on memory**;
`20260812T050133Z_MAT-6-step10-probe.log`, footerless because the run was
killed.)*
> **The composed fixture meshes cheaply and then does not solve.** The mesh
> is **895 974 cells** (1.28× the box+wire fixture's 697 401, 6.46× the
> step-2b baseline), meshed in 66.3 s at `-n 8` — §7's "~1 M is an estimate"
> was close and is now measured. But **one projected loaded solve did not
> finish in ~1 700 s at `-n 8`**: ≥ 5.7× the 300 s stop rule, and ~9× step
> 9's 190.1 s solve on 595 391 cells at the same rank count. Nine times the
> time for 1.5× the cells means the cost is **not** scaling with size, so
> this entry's own estimate ("178–196 s each at `-n 8` on record for the
> un-composed fixture") is refuted for the composed one. **It is not the
> 64 G cap:** the cap was re-read (68719476736) before the run, host memory
> peaked at 74 G of 754 G with no swap growth, and load sat at 11–12 with 8
> ranks — compute-bound, not reclaim-bound. No ΔR reading exists; the
> composition question is untouched.
> **Two harness findings came with it, both for the review:** (1) the
> container-side `timeout 590` **did not terminate the job** (it should have
> fired at 05:11:23Z; ranks were still running at 05:31Z) — every heavy
> recipe on record inherits this, and `timeout -k 30 <s>` is the suggested
> repair; (2) the overrun **wedged the container** — `exec` hung, `restart`
> and `kill` both returned "did not receive an exit event", a later exec
> failed with "error executing setns process" — and
> `docker compose up -d --force-recreate` is what recovered it (verified
> afterwards: exec responds, cap unchanged, zero stray `python3`, load back
> to baseline).
> **Next attempt (as journaled by the run):** the suspect is
> **conditioning**, not size — the composed mesh carries the widest
> cell-size ratio in the `MAT-6` family (0.001 wire / 0.0025 near / 0.025
> far inside W = 0.25); the run proposed re-running with KSP iteration
> counts printed. **Review correction, 2026-08-12 03:00: there are no KSP
> iterations to count.** The time-harmonic solve is `ksp_type: preonly` +
> `pc_type: lu` (`core/time_harmonic.py:445` — direct MUMPS, one "iteration"
> by construction), so on this solver the conditioning hypothesis cashes
> out as **factorization fill-in**, not iteration growth, and the right
> instrument is MUMPS's own analysis-phase statistics (estimated factor
> flops/NNZ), which print **before** numeric factorization starts and so
> survive a kill. Formal rescope in **step 10a** below; the probe script is
> landed on `main` (`scripts/probes/mat6_step10_probe.py`, commit
> `cc2e8da`; the attempt branch is deleted).
> **Attribution landed 2026-08-12 (09:00 run, step 10a below): the
> conditioning/fill-in hypothesis is refuted.** Estimated factor flops grow
> only **1.693×** for the 1.28× cell ratio, so the composed matrix is
> ordinary for its size and ≥ 5.1× of the 9× is unexplained by arithmetic.
> The two surviving suspects are cgroup memory pressure (MUMPS estimates
> 69 894 MB of in-core factorization space against a 65 536 MiB cap) and
> MUMPS parallel load balancing (the kill landed in its message receive).
> This step is now the weekly review's to commission.
> **Does not close / does not reopen:** `MAT-6` stays ✅; nothing in §2.1 or
> the `ANS-1` numbers moves.

**`MAT-6` step 10a — attribute the 9× composed-fixture solve cost before
any bigger box or rank count is spent on it** ✅
*(scoped 2026-08-12, 03:00 review — the step-10 rescope after its stop
rule fired. **Executed 2026-08-12, 09:00 run — the attribution landed and
it is negative: fill-in is exonerated.** Logs
`20260812T140222Z_MAT-6-step10a-baseline.log` (exit 0, 230 s),
`20260812T140637Z_MAT-6-step10a-intermediate.log` (exit 0, 246 s),
`20260812T141058Z_MAT-6-step10a-composed.log` (exit 124, 302 s — the
intended reading). Heavy, `-n 8`, three foreground commands.)*
> **Result.** Estimated factor flops `RINFOG(1)`: baseline (0.005, 697 401
> cells, 813 287 dofs) **9.059690e+12**; intermediate (0.0035, 738 953
> cells) 1.051031e+13; composed (0.0025, 895 974 cells) **1.534e+13**. The
> anchor ratio is **1.693×** against the **1.28×** cell ratio — **1.32× the
> cell ratio**, where the pre-registered fill-in verdict demanded ≥ 4×
> (5.12×). Estimated factor entries move less still (2 230 926 270 /
> 1 621 116 647 = 1.376×; digits corrected to the logs by the 10:30
> review audit — the run's plan text had transcribed both slightly off,
> ratio unaffected). The composed matrix is ordinary for its size.
> **Negative control PASS and enforced:** the baseline solve read **179.8 s**
> inside the 178–196 s record at ±25%, and the probe now exits 1 when that
> band is missed (`MAT6_STEP10_ROLE=baseline`), so the exit code carries the
> verdict.
> **Where the 9× is not.** Baseline `-log_view` puts `MatLUFactorNum` at
> 157.85 s of 227.7 s (69%; MUMPS "Elapsed time for factorization" 152.06 s),
> so the healthy rung *is* numeric-factorization-dominated and the flop ratio
> is the right predictor — it predicts a ~257 s composed numeric phase and a
> ~330 s solve against the ≥ 1 700 s measured at 00:00. **≥ 5.1× is
> unexplained by arithmetic and lives in the numeric phase.**
> **Two leads, both first readings of their kind.** (1) MUMPS `INFOG(17)`
> total in-core factorization space is **69 894 MB** composed vs 48 950 MB
> baseline, against a container cap of 68 719 476 736 B = **65 536 MiB** —
> the estimate *exceeds the cap by 6.7%*; effective use runs ~75% of estimate
> (baseline `INFOG(22)` 36 960 MB), so composed projects to ~52 GB, ~20%
> headroom vs 44%. The 00:00 run ruled the cap out from *host* memory, which
> cannot see cgroup reclaim. (2) The SIGTERM landed in
> `zmumps_fac_par → zmumps_fac2_lu → zmumps_send_factored_blk →
> zmumps_load_recv_msgs → PMPI_Iprobe` — blocked in MUMPS's parallel
> load-balancing receive, not in local BLAS.
> **Harness:** `timeout -k 30 300` stopped the job cleanly at 299.654 s,
> footer written, container Up, zero stray `python3`, `memory.max`
> unchanged — the direct counter-case to the 00:00 plain-`timeout` failure.
> **Instrumentation landed:** `time_harmonic.py` keeps the `LinearProblem`
> as `self._linear_problem` (diagnostic access only, nothing in the solve
> path reads it) so `getFactorMatrix()` survives the solve; the probe gained
> `MAT6_STEP10_ROLE` / `MAT6_STEP10_MUMPS_VERBOSE` and a stats reader.
> **Does not close / does not reopen:** `MAT-6` stays ✅; **step 10 stays 🟡
> and goes to the weekly review** per this entry's negative-result clause.
> The commissionable discriminator is a memory-headroom run (same fixture at
> `-n 12`, or MUMPS out-of-core / raised `ICNTL(14)`) timed against the 257 s
> prediction: near it ⇒ memory pressure owns the gap and step 10 is
> schedulable; still ~5× long ⇒ parallel load balancing owns it and step 10
> needs ordering or grading, not a bigger machine. *(10:30 review audit
> note for that commission: the factor-retention change this step landed
> means the factor now stays resident from `solve()` return until the
> solver leaves scope, so any post-solve processing on MAT-6-class
> fixtures runs with ~37–52 GB held against the 64 GiB cap — a headroom
> run that post-processes in the same scope should account for it, or
> extract INFOG/RINFOG at solve time and drop the handle per the code
> comment at `time_harmonic.py:453`.)*
> Three runs, all with MUMPS verbosity through the existing
> `solver_petsc_options` passthrough (`core/time_harmonic.py:449` —
> `mat_mumps_icntl_4: 2` and `-log_view`, so the analysis phase prints
> estimated factor flops and NNZ before numeric factorization):
> (1) **baseline** — the un-composed box+wire fixture (W = 0.25, wire
> 0.001, slab 0.005; solve 178–196 s on record at `-n 8`), one loaded
> solve, capturing its analysis stats; (2) **intermediate rung** — the
> combined fixture at `resolution_near` = **0.0035**, one solve under
> container `timeout -k 30 590`; (3) **the composed 0.0025 fixture
> itself** — launch one solve under `timeout -k 30 300`: the analysis
> stats print in the first minutes, and **exit 124 with the stats in the
> log is the measurement** — numeric factorization is not expected to
> finish and does not need to. Extend `mat6_step10_probe.py` (landed,
> `MAT6_STEP10_MESH_ONLY` knob already present) rather than writing a new
> script. **Anchor:** the ratio of MUMPS estimated factor flops,
> composed-0.0025 / baseline, read against the cell ratio **1.28×**
> (895 974 / 697 401, both on record). Pre-registered read: flop ratio
> ≥ **4×** the cell ratio says fill-in owns the 9× and step 10 rescopes
> onto mesh grading/ordering, not onto ranks; flop ratio ≈ cell ratio
> says the cost is *not* the factorization and the `-log_view` phase
> timings name the owner (assembly, projection, or MUMPS numeric-phase
> pathology) — either reading is decisive. **Negative control:** the
> baseline's own wall clock must land on its 178–196 s record (band
> ±25%); a baseline that moved says the environment changed and the
> ratios are void. **Cost:** heavy; ~190 s + ≤ 590 s + ≤ 300 s solves plus
> two ~66 s meshes at `-n 8` — three separate harness commands, each
> foreground inside one 660000 ms tool window. **Traps:** complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`; `timeout -k 30` mandatory (this step exists
> because plain `timeout` failed); a killed run leaves a stale FFCx lock —
> clear `~/.cache/fenics` after run (3); if the container wedges anyway,
> `docker compose up -d --force-recreate` and journal it;
> `project_source=False` pins untouched. **Does not close / does not
> reopen:** `MAT-6` stays ✅; step 10 stays 🟡 — this buys the attribution
> that decides whether step 10 is rescopable or out of scheduled reach;
> no ΔR is read. **Negative result:** analysis stats that are ordinary
> everywhere put the pathology in the numeric phase or the environment —
> journal beside the step-10 annotation and hand step 10 to the weekly
> review; do not spend `-n 12` on a 5.7× gap (~1.5× at best).

*(Original scoping, retained: scoped 2026-08-11, 18:00 review — decision (2);
the second Part 2c follow-on. Queued as §9 item 4; independent of step 9.)*
> Two separate routes now reach sub-1% ΔR: box+wire (step 7 Part 2c,
> **0.8835%** at W = 0.25 / wire 0.001 / slab 0.005) and the slab knob alone
> (step 8, **0.2829%** at W = 0.15 / wire 0.002 / slab 0.0025). Step 7's
> additivity verdict makes their composition a one-pair question: solve the
> combined fixture **plus** `resolution_near = 0.0025`, projected drive,
> loaded + free, `-n 8` under the 64 G cap, and read ΔR beside the two
> records. **Probe first:** mesh count, then one solve; stop at > 300 s or
> OOM — the composed cell count is unmeasured (combined 697 401 on record;
> step 8's knob added ~208 k near-region cells to a 210 k fixture, so ~1 M
> is an estimate), and an OOM at 64 G is itself a per-cell memory reading.
> **Anchor:** Dodd–Deeds `ΔR = +3.2259615e-01 Ω` under step 2b's unwidened
> 5% ceiling; the reading — whether ΔR improves from 0.8835% toward the
> sub-0.5% an additive error budget predicts — is **reported beside the
> prediction, never gated to it**. **Negative control:** step 6's two 16 G
> kill records on the un-composed fixture and the σ-blind `ΔZ = 0`, cited
> never recomputed. **Cost:** heavy; solves 178–196 s each at `-n 8` on
> record for the un-composed fixture; container `timeout` sized after the
> probe, ≤ 590; cap re-read (`memory.max` = 68719476736) before the solve.
> **Traps:** complex build + `FEM_EM_REQUIRE_COMPLEX=1`;
> `project_source=False` pins; stale FFCx lock after any kill; never
> background — foreground harness call, tool `timeout` 660000 ms. **Does
> not close / does not reopen:** measurement only — the production fixture,
> §2.1's landed 1.58%, and the `ANS-1` SPEC/COMPARISON numbers stay frozen
> pending the operator's adjudication (step-8 review decision, unchanged);
> `MAT-6` stays ✅. **Negative result:** a ΔR that does not improve — or
> worsens — under the composed knobs says mesh-knob additivity (measured on
> ΔX) does not imply error-term additivity (assumed for ΔR): that is the
> finding this step exists to catch, and it would bound how far single-knob
> extrapolation can be trusted. Report both numbers, annotate here, stop.

### POST — Post-processing & field extraction

| ID | Title | Status | Tier |
|---|---|---|---|
| `POST-1` | Interface-aware field extraction reliability | 🟡 *(adjudicated 2026-08-05, 18:00 review — mean semantics decided, extremum semantics is step 4)* | standard |
| `POST-2` | Energy/consistency diagnostics | ⚠️ | standard |
| `POST-3` | Replace vacuous consistency metrics | 🟡 | standard |
| `POST-4` | Centerline point evaluation is rank-count-dependent: attribute and fix the ownership tie-break in `evaluate_vector_field_parallel` | ✅ *(chunk closed 2026-08-12 — every step closed or dispositioned; note the title's premise was itself refuted, the tie-break was never the defect. Step 1 ✅ 2026-08-11 — ownership **refuted**, 0/120 multi-claims; locus is the Lagrange-P1 interpolation, 1.163e+04× separation. Step 2 🚫 skipped. Step 3 ✅ 2026-08-11 — the centerline samples the source fields: **23.5539% → 0.008613%**, a 2735× collapse; known-issues entry **retired**. Step 4 ✅ 2026-08-12 — the export-path P1 artifact is **bounded and attributed**: midpoint relative medians **51.17% / 52.47% / 20.18%** (`A`/`B`/`E`), vertex/midpoint separation **0.42–0.68×** so the step's vertex-localization hypothesis is **REFUTED**, and a DG1 target reproduces all three sources to round-off — 100% of it is the P1 continuity constraint. All four steps now closed or dispositioned)* | standard |

> *(Closed-step plans, execution journals and audits below are archived
> verbatim in `docs/planning/plan-archive.md`.)*
>
> **`POST-1` — what the symbol stands for** *(⚠️ → 🟡, adjudicated 2026-08-05,
> 18:00 review)*. Three defects found and closed: the complex→float64 cast
> that scored every phantom metric on `Re(E)` at phase 0 (fixed by `POST-3`
> step 4); the ghost-cell double-count in the tagged-cell aggregation
> (step 1); and the guardrail's rank-local fallback (step 2). Step 3 then
> measured the drop-set semantics on a solved field, and this review reads
> the numbers as follows. **For means, the guardrail is adjudicated
> harmless and stays:** (a) vs (b) is 4.253% vs 4.263% — 0.01 pp on an
> error that is 4.25% of bulk discretisation — so no landed mean-statistic
> claim (including `MAT-4`'s 3.5% mean SAR) is disturbed by either keeping
> or bypassing it, and no production change is warranted on the mean's
> account. **For extrema, the rule is adjudicated *unsafe pending step 4*:**
> both tag extrema live in the drop layer (full range 1.334× surviving),
> and SAR peaks are extrema — so no peak/extremum statistic may be reported
> through `prefer_interior=True` until step 4 separates interface smearing
> from the sphere's chordal geometry error on a planar fixture. Nothing
> currently gates a peak through this path, which is why this is a scoping
> decision, not a defect entry. **Step 4 settled it 2026-08-05 (21:00 run) and
> the "pending" is discharged: on a chordal-error-free planar interface the
> drop layer is 22% *more* accurate than the interior ((c)/(a) = 0.7822), and
> dropping it costs 2.157× in peak error (1.6537% vs 0.7666% against the
> closed-form entry-face value). The rule protects nothing measurable and
> demonstrably harms peaks.** **Both handed items adjudicated 2026-08-06,
> 03:00 review:** (i) the production default flips — `prefer_interior=False`
> becomes the default via step 5 below **(executed 2026-08-06, 07:30 run — the
> flip is landed and gated on both fixtures)**, parameter retained and the
> `True` path
> pinned, on the evidence that the mean is insensitive (0.01 pp on both
> fixtures) and the peak is measurably harmed (2.157×, with no geometry
> confound left to blame); (ii) step 3's sphere gates stay ✅ — their
> assertions are internally consistent and were executed — but the quantity
> they scored is `Re E`, and step 4b re-scores the same fixture on `|E|` so
> the step-3 conclusions rest on the anchored quantity rather than on
> "probably undisturbed". **Step 4b executed 2026-08-06 (06:00 run) and (ii)
> is discharged: the sphere phasor is exactly real (`max|Im E| = 0`), the two
> tables agree to 2.054e-16, and step 3's conclusions transfer *identically*.**
> The chunk is 🟡, not ✅: the coil+phantom
> application is where the chunk ultimately earns its ✅.
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
> * **`POST-1` step 4 — drop-set semantics on a planar interface: the
>   guardrail is refuted for means *and* unsafe for extrema** ✅ *(2026-08-05,
>   21:00 run; `tests/post/test_drop_set_semantics_planar.py`, probe
>   `scripts/probes/post1_step4_probe.py`)*. Gates
>   `20260806T020812Z_POST-1-step4-gate-n2.log` (6 passed, 96.43 s) and
>   `…021009Z_POST-1-step4-gate-n4.log` (6 passed, 60.14 s) — **every printed
>   digit identical across rank counts**, so both readings below are properties
>   of the field, not the partition.
>
>   **The plan's fixture premise was wrong and is corrected here.** `POST-3`
>   step 2 has **no closed form**: it imposes the σ_low plane wave on all six
>   faces, which its own comment says is not the two-material solution, and
>   which on `y = 0`/`y = L` pins `E_z = e^{-j k_low x}` right through slab 2
>   where no piecewise solution can match it. A Poynting *identity* has no free
>   parameters and does not care (step 2 stands); a *pointwise* comparison does.
>   So this step keeps the mesh, tags and material map and replaces only the
>   Dirichlet trace with the self-consistent normal-incidence transmission
>   solution `f₁ = e^{-jk₁x} + R e^{-jk₁(2xᵢ-x)}`, `f₂ = T e^{-jk₁xᵢ}
>   e^{-jk₂(x-xᵢ)}`, `R = (k₁-k₂)/(k₁+k₂)`, `T = 2k₁/(k₁+k₂)`. That pair is an
>   exact curl-curl solution for `E = (0,0,f(x))`, and the module **proves it
>   rather than assuming it**: rel L2 `4.3147% → 2.1568%` at rate **1.0004**
>   in h (16³ → 32³), gated at rate > 0.9 and fine error < 5%.
>
>   **The sampled object had to change too, and this is the transferable
>   lesson.** The anchor is `|E|`, so the sampled function is `e_complex`.
>   Step 3 sampled `fields.e_real` — `np.real` of the phasor, a phase-0
>   snapshot. On the sphere's nearly in-phase interior the two nearly agree; on
>   this propagating decaying field `Re E` crosses zero and the identical
>   measurement returns **61.8232%** error against a solve whose global L2 error
>   is 2.1568% (`20260806T020312Z_POST-1-step4-probe.log`, before the switch;
>   `…020449Z…probe2.log` after). **`POST-1` step 3's sphere numbers are
>   therefore scored on `Re E`, not `|E|`** — for the review to adjudicate; the
>   sphere's own conclusion is probably undisturbed but nothing here establishes
>   that, and this step did not reopen a closed gate to find out.
>
>   Per-centroid `|E|` against the closed form at the *same* centroids, slab-2
>   tag, 32³ = 196 608 cells:
>
>   | set | n | mean rel error | `|E|` range |
>   |---|---|---|---|
>   | (a) `prefer_interior=True` (production) | 96256 | 1.1472% | [0.237386, 0.692107] |
>   | (b) full owned tagged set | 98304 | 1.1420% | [0.237386, 0.698349] |
>   | (c) drop set alone | 2048 | **0.8974%** | [0.697742, 0.698349] |
>
>   **Interface smearing is refuted with a sign.** (c)/(a) = **0.7822** — with
>   chordal error identically zero, the dropped layer is 22% **more** accurate
>   than the interior the guardrail keeps. The sphere's 1.009 was consistent
>   with "harmless"; this points the other way. The layer sits at the entry
>   face, pinned by continuity to the well-resolved σ_low side, while the
>   surviving set carries the accumulated phase-and-decay error of the whole
>   slab. Gated at ratio < 0.95; partition identity 96256 + 2048 = 98304 exact.
>
>   **The extremum claim is now closed-form priced, and it is the adjudication
>   the review was waiting on.** `|f₂|` decays monotonically, so the slab's true
>   maximum sits *at the interface*: `|E| = 0.703744`. Measured: full set (b)
>   max **0.7666%** below it, surviving set (a) max **1.6537%** below it —
>   **2.157× worse**. Dropping the interface layer discards the peak by
>   construction and doubles the peak error. `prefer_interior=True` is unsafe
>   for any peak statistic, on a fixture with no geometry confound to blame.
>   Gates: (b) peak error < 1.2%, (a) max strictly below (b) max, ratio > 1.5.
>
>   **What this does not do.** It does not change the production default —
>   `prefer_interior=True` still ships — because that is the next review's call,
>   and it does not close `POST-1`: the coil+phantom application is still where
>   the chunk earns ✅. Two items for the review: the default's fate (the drop
>   rule now protects nothing measurable and demonstrably harms peaks), and
>   step 3's `e_real` sampling.
>
> * **`POST-1` step 4b — the sphere re-scored on `|E|`: step 3's conclusions
>   survive *identically*, and the reason is now gated** ✅ *(2026-08-06,
>   06:00 run; `tests/post/test_drop_set_semantics_sphere.py`, probe
>   `scripts/probes/post1_step4b_probe.py`)*. Gates
>   `20260806T110400Z_POST-1-step4b-gate-n2.log` (6 passed, 7.38 s) and
>   `…110428Z…-gate-n4.log` (6 passed, 4.42 s); probes `…110135Z…probe.log`
>   and `…110235Z…probe2.log`; regression `…110445Z…-regression.log`,
>   `tests/post` 31 passed, 109.91 s.
>
>   Scored on `fields.e_complex`, off one solve, beside the `Re E` table:
>
>   | set | n | mean | error on `Re E` | error on `|E|` |
>   |---|---|---|---|---|
>   | (a) `prefer_interior=True` | 3327 | 0.039095 | 4.2530% | **4.2530%** |
>   | (b) full owned tagged set | 4431 | 0.039099 | 4.2630% | **4.2630%** |
>   | (c) drop set alone | 1104 | 0.039110 | 4.2931% | **4.2931%** |
>
>   **The two tables are the same table.** `max|Im E| = 0` over the tag —
>   *exactly* zero, not small — and all twelve statistics agree to
>   **2.054e-16** at `-n 2` / 3.114e-16 at `-n 4`, i.e. to reduction-order
>   roundoff. (c)/(a) is 1.0094× and the spread ratio 1.3337× on **both**
>   quantities. So step 3's two readings — the mean is unmoved by the
>   guardrail, both extrema live in the drop layer — are properties of the
>   anchored quantity, and the 03:00 review's "probably undisturbed" is
>   discharged as an equality rather than an estimate.
>
>   **What makes it an equality is a property of the fixture, and that is what
>   the new gate asserts.** The sphere is lossless (`σ = 0` everywhere) and its
>   exact-exterior Dirichlet data is real, so neither the operator nor the data
>   carries a phase and the solved phasor is real to the last bit. The test
>   gates `max|Im E|/max|E| < 1e-12` and the worst `|E|`-vs-`Re E` disagreement
>   `< 1e-12` — both many orders under the measurement, and both fail the moment
>   the fixture acquires a phase (a nonzero σ, a complex trace, a PML), which is
>   precisely when `Re E` would stop being the magnitude. The step-3 gates are
>   left untouched and their sampled function is now explicit in a comment.
>   Negative control on record, not re-run: step 4's planar pair — the identical
>   substitution scoring **61.8232%** where `|E|` scores 1.1472%
>   (`20260806T020312Z…probe.log`) — is what makes the sphere's zero a
>   measurement worth having rather than a foregone conclusion.
>
>   **Does not close `POST-1`**: the coil+phantom application still does.
>
> * **`POST-1` step 4b — the plan as written (2026-08-06, 03:00 review;
>   superseded by the result above, kept for the audit trail).** Step 3's gates
>   scored
>   `fields.e_real` — a phase-0 snapshot — where the anchor `3/(εᵣ+2)E₀ =
>   0.037500` is a magnitude. On the sphere's nearly in-phase interior the two
>   nearly agree, which is why the numbers looked sane; on the planar fixture
>   the same substitution produced a 61.8232% phantom error. This step adds the
>   `|E|`-scored table to `tests/post/test_drop_set_semantics_sphere.py`
>   without touching the existing `e_real` gates (pin them by making the
>   sampled function explicit, the `project_source=False` pattern). Probe
>   first; band the new (a) error from the probe. **Anchor:** the same closed
>   form `0.037500` at `h_sphere = 0.00833`, per-set mean/range of `|E|` from
>   `e_complex`; partition identity `3327 + 1104 = 4431` unchanged and exact
>   (the sets are classification, not sampling). **Negative control:** on
>   record, cite — the step-3 `Re E` table (4.253/4.263/4.293%, range ratio
>   1.334) and the planar 61.8232%-vs-1.1472% pair that motivates this step.
>   The deliverable is the `|E|` table beside the `Re E` table and whether
>   step 3's two conclusions (mean-harmless; both extrema in the drop layer)
>   survive the change of quantity. **Cost:** standard, `-n 2`, `timeout 180`;
>   the step-3 gate ran 4.42 s, probe ~30 s. **Traps:** complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first; `e_complex`, never
>   `np.real`/`np.abs` of `e_real`; allreduce counts and extrema; pytest `-s`;
>   do not widen the existing 1.2 range-ratio ceiling — if `|E|` moves the
>   ratio outside it, that is a new measurement, band it separately.
>   **Does not close:** `POST-1`. **Negative result:** if `|E|` scoring
>   overturns a step-3 conclusion (e.g. the extrema leave the drop layer),
>   report both tables and annotate step 3's entry — step 4's planar
>   adjudication stands on its own evidence either way; nothing is re-gated
>   in-slot.
>
> * **`POST-1` step 5 — retire `prefer_interior=True` as the production
>   default** ✅ *(2026-08-06, 07:30 run)*. All four defaults in
>   `post/phantom_fields.py` are now `False`
>   (`_sampling_cells_with_interface_guardrails`,
>   `compute_tagged_vector_magnitude_stats`,
>   `export_tagged_field_samples_csv`,
>   `compute_phantom_eb_metrics_and_export`); the parameter is retained and the
>   `True` path pinned, not deleted. **Anchor met on both fixtures.** Step 1's
>   12³ piecewise-σ fixture, production called with *no* sampling kwarg vs the
>   full-owned-set reference through step 1's own reduction: `count` 5184 =
>   5184 for both tags, min/max/mean equal at `1e-12`, digit-identical at
>   `-n 2` and `-n 4` (`20260806T123424Z_POST-1-step5-partition.log:116`,
>   `…123943Z…-n4.log:168`). Step 4's 32³ planar fixture, production vs row
>   (b): n = 98304, `|E| ∈ [0.237386, 0.698349]`, peak deficit **0.7666%** —
>   the landed row (b) numbers digit-for-digit through the production entry
>   point (`…123445Z_POST-1-step5-planar-n2.log:79`). **Negative control held:**
>   `prefer_interior_samples=True` reproduces row (a) exactly — n = 96256, max
>   0.692107, peak deficit 1.6537%, i.e. the landed **2.157×** penalty, now
>   measured *through production* rather than through the test module's helper;
>   on the step-1 fixture the guarded set is short by exactly the 288
>   boundary-adjacent cells the guardrail drops (integer identity), and on tag 2
>   the default's `max` 0.885040 exceeds the guarded 0.879575 — the extremum
>   really does live in the dropped layer. **No landed gate moved:** 39 passed
>   across `tests/environment tests/post tests/materials
>   tests/validation/test_lossy_sphere_sar.py` in 157 s
>   (`…123648Z_POST-1-step5-regression-n2.log`), `MAT-4`'s mean-SAR gate
>   included — `post/sar.py` integrates over the tagged volume and never calls
>   this sampler, so the insensitivity is structural, not just measured.
>   Implicit-default call sites swept: `test_phantom_phasor_semantics.py` (3
>   sites) now passes `True` explicitly so its 45.4% `Re`-cast deficit band is
>   scored on the set it was measured on; `test_phantom_field_metrics.py`'s
>   summary assertion flipped to `is False` — the one place the default is
>   observable from outside the module. Tier standard, `-n 2`/`-n 4`, 8.8 s +
>   103 s + 157 s + 3 s. **Does not close `POST-1`** — the coil+phantom
>   application remains.
>
> * **`POST-1` step 5 — the plan as written (2026-08-06, 03:00 review;
>   superseded by the result above, kept for the audit trail).** Flip the
>   defaults in
>   `post/phantom_fields.py` (`prefer_interior` at ~line 201,
>   `prefer_interior_samples` at its three pass-through sites) to `False`,
>   parameter retained, docstrings updated to cite the step-3/step-4
>   measurements. **Anchor:** the production path (defaults, no kwargs) equals
>   the full-owned-set reference exactly in count and to 1e-12 in
>   min/max/mean — step 1's comparison machinery on step 1's fixture — and the
>   step-4 planar fixture's row (b) numbers (1.1420% mean, 0.7666% peak
>   deficit) reproduce digit-for-digit through the production path.
>   **Negative control:** `prefer_interior=True` passed explicitly reproduces
>   row (a) unchanged (4.253% sphere mean, 1.6537% planar peak deficit) — the
>   old behaviour is pinned, not deleted. **Cost:** standard, `-n 2`,
>   `timeout 180`; step-4 gate 96 s + `tests/post` regression on record at
>   ~30 s. **Traps:** sweep `tests/post` and `tests/materials` for call sites
>   that rely on the old default implicitly — pass `True` explicitly there
>   rather than re-deriving their numbers; `MAT-4`'s 3.5% mean SAR is
>   mean-based and measured insensitive (0.01 pp) but re-run it as regression,
>   not assumed; complex build; pytest `-s`. **Does not close:** `POST-1` —
>   the coil+phantom application remains. **Negative result:** any landed gate
>   that moves by more than the measured 0.01-pp mean effect is information —
>   report the delta, annotate here, stop; never widen the moved gate
>   in-slot.
>
> * **`POST-1` step 6 — CSV-export/stats sampling parity** ✅ *(2026-08-06,
>   15:00 run)*. `tests/post/test_csv_export_stats_parity.py` gates
>   `export_tagged_field_samples_csv` against
>   `compute_tagged_vector_magnitude_stats` off one solve of step 1's 12³
>   piecewise-σ fixture. **Anchor met in both sampling modes and at two rank
>   counts.** Default (`prefer_interior_samples=False`): CSV data rows
>   **5184 = 5184** stats samples on each tag, and the parsed `mag` column's
>   min/max/mean equal the allreduced statistics **bit-for-bit** — tag 1
>   `0.5708276489752246 / 0.9980976155749424 / 0.8205203318606578`, tag 2
>   `0.577614544558443 / 0.8850402333786891 / 0.7651432632537083`, relative
>   disagreement **0.000e+00** on all six numbers, not merely inside the
>   `1e-12` gate (`20260806T200216Z_POST-1-step6-probe.log:82`). The
>   round-trip is exact because `csv.writer` formats a float with `str`,
>   which is the shortest round-tripping repr of a float64 — the probe
>   measured that before anything was gated, per the plan. Guarded mode
>   (`True` through *both* paths): **4896 = 4896** on each tag, so the
>   agreement in the default mode is shared sampling and not a coincidence of
>   two equal defaults. **Negative control held as an integer identity:**
>   default rows − guarded rows = **5184 − 4896 = 288** = the
>   boundary-adjacent cells `_interior_tagged_cells` drops, per tag — step 5's
>   number, now measured through the *export*. **Rank-invariant:** every count
>   above is digit-identical at `-n 4`
>   (`…200248Z_POST-1-step6-gate-n4.log:109`), which is the check that matters
>   for a path that gathers to rank 0. One identity beyond the plan: the CSV's
>   `mag` column is recomputed from its own `fx_re/fx_im/…` columns and agrees
>   to **4.120e-16** worst case — the export writes the phasor magnitude, not
>   `Re` of anything (`POST-3` step 4's defect, now gated on the artefact the
>   operator reads). **No divergence found, so nothing was patched.** No
>   production code changed: this step is gate-only. Tier smoke-to-standard,
>   `-n 2`/`-n 4`, 5 s + 5 s + 5 s; regression `tests/environment tests/post`
>   41 passed in 124 s (`…200300Z_POST-1-step6-regression.log:145`), the 30
>   pre-existing gates unmoved. **Does not close `POST-1`** — the coil+phantom
>   application remains.
>
> * **`POST-1` step 6 — the plan as written (2026-08-06, 10:30 review;
>   superseded by the result above, kept for the audit trail).** Step 5 flipped
>   `export_tagged_field_samples_csv`'s default along with the stats path,
>   but nothing gates the two sampling calls against each other — a future
>   divergence (one path regaining a guardrail, a filter, an off-by-one in
>   ownership) would be silent, and the CSV is what the human operator reads.
>   On step 1's 12³ piecewise-σ fixture (cheap, on record at ~9 s for the
>   whole partition gate), call the production stats path and the CSV export
>   off the same field and tag, parse the CSV with numpy, and gate:
>   **Anchor:** row count equals the stats count *exactly* (integer identity,
>   5184 per tag on this fixture, gathered/allreduced — never rank-local) and
>   per-column min/max/mean of the parsed CSV agree with
>   `compute_tagged_vector_magnitude_stats` to 1e-12 relative — the same
>   identity standard step 1 set. **Negative control:**
>   `prefer_interior_samples=True` passed to both reproduces the guarded
>   count (4896 = 5184 − 288, the integer identity step 5 measured) — the
>   two paths must agree in *both* modes, or agreement in the default mode is
>   coincidence. **Cost:** smoke-to-standard, `-n 2`, `timeout 180`; one
>   12³ solve plus file I/O, well under a minute on record. **Traps:** CSV
>   writing under MPI — establish whether the export gathers to rank 0 or
>   writes per rank *before* asserting the count, and read the file on rank 0
>   only, after a barrier; float round-trip through CSV text may cap
>   agreement near 1e-15–1e-12 — probe the printed precision first and set
>   the assert at what the format carries, never loosen after the fact;
>   complex build + `FEM_EM_REQUIRE_COMPLEX=1`; pytest `-s`. **Does not
>   close:** `POST-1` — the coil+phantom application remains the ✅. 
>   **Negative result:** any count or statistic divergence between the two
>   paths is the finding — report both sides, open a known-issues entry
>   naming the divergent path, stop; do not patch the export in the same
>   slot the divergence is discovered.
>
> **`POST-1` step 4 — the plan as written (2026-08-05, 18:00 review; superseded
> by the result above, kept for the audit trail).** Fixture: the `POST-3`
> step-2 **two-slab** solve (σ = 0.1 | 1.4 S/m, planar interface;
> `20260731T183453Z_POST-3-step2-gate.log`) — the one solved interface field
> where the boundary layer carries **zero** chordal geometry error, because
> planar facets are represented exactly. Import that fixture and its
> piecewise closed form; do not restate either. Solve once; score `|E|`
> sampled at cell centroids against the closed form **evaluated at those same
> centroids** (the field decays, so a single interior value is not the
> anchor — the pointwise closed form is), for the three sets of the slab-2
> tag: (a) `prefer_interior=True` survivors, (b) full owned tagged set,
> (c) drop set alone. **Anchor:** the per-centroid closed-form error of (a),
> gated at a probe-set band inside the fixture's existing tolerance (4.49%
> landed), plus the exact partition identity n(a) + n(c) = n(b) globally.
> The reported result is the (c)/(a) mean-error ratio — on this geometry it
> is the interface-smearing term *alone*, which the sphere could not give.
> **The extremum claim, now closed-form-predictable:** the decaying field's
> true maximum over the slab sits at the interface itself, so the closed
> form *predicts* the surviving-set max deficit — approximately the decay
> across the dropped layer's thickness, computable from the probe's printed
> layer geometry before any factor is asserted. Probe first, print the
> per-set extrema and the predicted deficit, then gate full-set max against
> the closed-form entry-face value at a probe-set band; the surviving-vs-full
> max comparison is printed beside its prediction, gated only if the probe
> shows clean separation (`POST-3` step 2's ceiling rule). **Negative
> control:** step 3's sphere numbers, on record — mean ratio 1.009 with
> curvature confounded; if the planar (c)/(a) ratio lands at ~1.0 too, the
> interface-smearing hypothesis is refuted outright. **Cost:** standard,
> `-n 2`, `timeout 180`; the two-slab gate ran 66 s harness-total on record,
> so probe + gate fit in two commands. **Traps:** complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first; ghosts classify but
> never contribute samples; allreduce counts and extrema; pytest `-s`; thin
> tagged layers and tet decomposition (step 2's hexahedra lesson) — the drop
> layer here is whatever the classifier emits, print its cell count per
> class; import, don't restate. **Does not close:** `POST-1` — the coil+
> phantom application is still where the chunk earns ✅; this step decides
> only the extremum-semantics rule. **Negative result:** no separation on
> the planar fixture ⇒ the drop rule protects nothing measurable anywhere —
> report all ratios, annotate this entry, and the next review decides
> whether `prefer_interior` remains the default; report-and-stop either way.
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

**`POST-4` — centerline point evaluation is rank-count-dependent: attribute
and fix the ownership tie-break in `evaluate_vector_field_parallel`** ✅
*(closed 2026-08-12 — steps 1, 3 and 4 ✅, step 2 🚫 skipped under its own
clause. The chunk title's premise did not survive its own step 1: the
ownership tie-break was refuted at 0/120 multi-claims and never was the
defect. What the chunk actually bought: the locus attributed to the
Lagrange-P1 interpolation (step 1), the mri centerline printout made
rank-invariant and faithful by sampling the source fields (step 3, 2735×
collapse), and the export-path artifact that remains bounded and attributed
to the P1 continuity constraint (step 4). `evaluate_vector_field_parallel`
was never changed.)*
*(scoped 2026-08-10, 18:00 review — this is the chunk the `EX-16` negative
result demanded: converging the mri demo's solve moved the centerline rank
spread 23.5545% → 23.5539% (1.0000×), while the 493-point phantom-region
sampler on the *same two solves and the same fields* agrees across rank
counts to 0.007326% — 3215× tighter. Same solve, two samplers: the defect
is in the point-evaluation path. Owns the open known-issues entry
"`examples/mri/01` centerline samples are rank-dependent at ~23%".)*
> **The suspect mechanism, stated so the probe can refute it.**
> `post/evaluation.py::evaluate_vector_field_parallel` has each rank claim
> `links[0]` — the first locally-colliding cell — and rank 0 resolve
> multi-rank claims by last-writer-wins in rank order (`values[rank_indices]
> = rank_values` in the gather loop). For a point on a shared facet/edge —
> and the demo's centerline sits at x = y = 0, plausibly on shared entities
> of the axis — the evaluating *cell* is therefore partition-dependent, and
> a Nédélec interpolant is only tangentially continuous across faces, so
> cell choice changes the value. `MAG-6` step 4 measured **0/9 multi-claims
> on its fixture** (and refuted its own probe's √3 artifact), so this
> mechanism is *plausible but unmeasured* on the mri fixture — hence
> diagnosis before fix. A second candidate the probe must also cover:
> silent zero-fill — a point no rank's bbox collision claims returns 0 with
> `valid_mask=False`, and a sampler ignoring the mask would swallow the
> zero into a spread statistic.
>
> **Step-1 outcome (2026-08-11, 09:00 implementer run) — the suspect above is
> REFUTED, and the locus is measured.** On a byte-identical mesh across
> `-n 1/2/4` (9261 cells; coordinate moments equal to 12 digits) the census is
> empty: `MULTI_RANK_CLAIMS = 0/120`, `MULTI_CELL_CLAIMS = 0/120`,
> `MASK_INVALID = 0/120`, `CROSS_CELL_DISAGREE = 0/120` — every centerline point
> is claimed by exactly one cell on exactly one rank, so `links[0]` has nothing
> to choose between and last-writer-wins nothing to overwrite; silent zero-fill
> is dead too. The ε-nudge does not collapse the spread (97.9755% → 97.9754%,
> **1.00×** against the ≥ 235× the anchor demanded), the third independent
> refutation. **What does carry it:** the probe sampled the Lagrange-P1
> interpolants the example prints (`E_lag`, `B_lag`) *and* the source fields
> they were interpolated from (`E_src`, `B_src`), at the same points on the same
> solves — interpolant path **97.9755%**, source path **0.008426%** (and `E_src`
> bit-identical across all three rank counts *(corrected 2026-08-11, 10:30
> review audit: last-ulp, not literally bit-identical — n1 vs n2 print
> `…7731` vs `…7732` at z = −0.0225 m, ~4e-13 relative; the 0.008426% and the
> separation stand)*), a **1.163e+04×** separation. The
> solve is rank-invariant; the 23% enters at `fem.Function.interpolate` into
> `("Lagrange", 1, (3,))`, where a vertex dof of a field not continuous there is
> written by whichever adjacent cell writes last locally. The `-n 2` vs `-n 4`
> table reproduces `EX-16`'s 23.5539% `B_lag` at z = +0.0225 m exactly, so this
> is the same fixture; the previously unmeasured `-n 1` leg is the worst, with
> `E_lag` = 7.670127e+03 at z = −0.045 m against a source value of 1.368268e+02
> — a 56× interpolation artifact present at every rank count. Probes
> `scripts/probes/post4_step1_probe.py` (3 runs, 4/4/8 s at `-n 2/4/1`) and
> `scripts/probes/post4_step1_spread.py`; logs `20260811T140345Z` /
> `…140402Z` / `…140414Z_POST-4-step1-n{2,4,1}.log` and
> `…140549Z_POST-4-step1-attribution.log` (anchor PASS, 1 s). No `src/` change,
> no gate, no tolerance; the known-issues entry stays open and is re-pointed at
> the interpolation. **Step 2 is skipped under its own conditional clause** — a
> min-global-cell tie-break cannot move a spread that has no multi-claims — and
> the real owner (P1 interpolation of a non-conforming field, or the example
> sampling the interpolant rather than the source field) needs review scoping
> before any code is written.
>
> * **Step 1 — diagnosis on the `EX-16` fixture (measurement only, no
>   `src/` change)** ✅ *(executed 2026-08-11; the suspect mechanism refuted,
>   the locus attributed — see the step-1 outcome above)*. New probe `scripts/probes/post4_step1_probe.py`
>   in the `mag6_step4_probe.py` mold, on `examples/mri/01`'s debug preset
>   exactly as `EX-16` left it (`preonly`/LU, `gauge_penalty=1.0`). Solve
>   at `-n 1`, `-n 2`, `-n 4`; per centerline point and per rank count
>   record: (a) claim multiplicity — how many ranks' `colliding_cells`
>   found it; (b) the set of *global* cell indices claiming it
>   (`local_to_global` on the links, all of them, not just `links[0]`);
>   (c) the per-claiming-cell evaluated value and the max cross-cell
>   relative disagreement; (d) `valid_mask` — any point invalid at any
>   rank count; (e) the ε-nudge discriminator: the same points offset to
>   x = y = 1e-6 m (off the axis, geometry otherwise identical),
>   spread re-measured. **Anchor (attribution identity):** the points
>   carrying the 23.5539% spread coincide with the points whose claiming
>   cell set is partition-varying (or mask-invalid), and their measured
>   cross-cell disagreement accounts for the spread's magnitude; the
>   nudged points collapse to the phantom path's scale — assert nudged
>   spread ≤ 0.1% against the on-axis 23.5539%, a ≥ 235× separation
>   (ceiling measured: 3215×, `20260810T170457Z_EX-16-spread-v2.log`).
>   **Negative control:** the phantom-region 0.007326% on the same solves,
>   cited not recomputed (same log); `MAG-6` step 4's 0/9 multi-claim
>   fixture is the on-record contrast. **Cost:** standard tier; the demo
>   solves in 6 s / 4 s at `-n 2` / `-n 4` on record
>   (`20260810T170234Z` / `…170309Z_EX-16-direct-n2/n4.log`); `-n 1` is
>   unmeasured — wrap it alone in `timeout 600`, the rest 180.
>   **Traps:** the √3 probe bug is pre-paid — `Function.eval` squeezes a
>   single point to shape `(3,)`, so `.reshape(-1, 3)` before indexing
>   (`MAG-6` step 4's one-line fix); complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first; stale FFCx
>   lock after any kill; claim counts are rank-local — reduce before
>   printing; pytest swallows prints without `-s`. **Scope boundary:**
>   diagnosis only — no `src/` edit, no tolerance, no gate; `MAG-6` and
>   `EX-13`/`EX-16` records untouched; the known-issues entry stays open
>   regardless of outcome. **Negative result:** zero multi-claims, stable
>   claim sets, full masks *and* no collapse under the nudge refutes the
>   ownership mechanism — then the per-point rank-difference table itself
>   localizes where the 23% lives (which points, which leg); re-point the
>   known-issues entry at the measured locus, annotate here, stop.
> * **Step 2 — deterministic tie-break in
>   `evaluate_vector_field_parallel`, gated by the collapse** 🚫 *(skipped
>   2026-08-11 under its own conditional clause: step 1 measured 0/120
>   multi-claims, so there is no tie to break and this edit would change no
>   sampled value. Do not execute as written. The measured owner is the P1
>   interpolation step; re-scoping it — fix the interpolation, or have the
>   example sample the source fields — is the next review's call. Original
>   text retained below for the audit trail.)*
>   *(execute only if step 1 confirmed partition-varying cell choice; a
>   refuted step 1 makes this step's edit aimless — skip and leave for
>   the next review).* The fix shape: choose the evaluating cell by
>   **minimum global cell index** — each rank evaluates at its
>   locally-min global claimed cell and reports that index; rank 0 keeps,
>   per point, the value from the globally minimal cell instead of
>   last-writer-wins. The claimed-cell set of a point is geometric, so
>   the selection is partition-independent by construction. **Anchor:**
>   on the step-1 fixture, the on-axis centerline spread across
>   `-n 1/2/4` collapses 23.5539% → ≤ 0.1% (≥ 235× — ceiling 3215×,
>   the solve-noise floor is the phantom path's 0.007326%); plus
>   non-regression, the phantom-region stats and `tests/post` reproduce
>   their on-record digits. **Negative control:** the pre-fix 23.5539%
>   on record (`…EX-16-spread-v2.log`), cited. **Cost:** standard,
>   `-n 1/2/4` re-runs of the step-1 measurement, same budgets.
>   **Traps:** ghost cells appear in `colliding_cells` links —
>   `local_to_global` handles them, but evaluate only at cells the rank
>   can (owned or ghost, after `scatter_forward`); keep the complex
>   scalar dtype path exactly as is; do not touch the function's
>   signature — `MAG-8`-era callers exist. **Scope boundary:** the
>   *value* at a shared-facet point remains convention (the min-cell
>   trace) — this chunk buys rank-invariance, not a claim that the trace
>   equals the physical field at a discontinuity; no SAR/B1 gate cites
>   centerline numbers, and none may cite this as new physics validation.
>   Closing the known-issues entry requires this step's anchor to land —
>   the entry leaves with this commit or stays. **Negative result:** a
>   deterministic tie-break that does not collapse the spread means the
>   disagreement is between *runs*, not cells — report the per-point
>   table, keep the entry open, annotate here, stop.
> * **Step 3 — the centerline samples the source fields, not the P1
>   interpolants (standard; re-scoped 2026-08-11, 10:30 review, onto the
>   locus step 1 measured).** ✅ *(executed 2026-08-11, 13:30 implementer run —
>   the chunk-anchor leg passed on the script's first execution; the anchor
>   script as a whole first exited 1 on two secondary tolerances, corrected
>   in-slot with the FAIL log committed — see below. Wording corrected
>   2026-08-11, 18:00 review audit.* `examples/mri/01_coil_phantom_fields.py`'s
>   centerline table now evaluates `e_field`/`b_field` **as solved** through
>   `evaluate_vector_field_parallel`; the P1 interpolants stay on the XDMF
>   export path, untouched, and **no `src/` change** was made. Measured on the
>   post-fix example at `-n 1/2/4` (logs `20260811T183229Z` / `…183211Z` /
>   `…183222Z_POST-4-step3-n{1,2,4}.log`, exit 0, 9/6/4 s): centerline spread
>   **0.008613%** against the 23.5539% record — a **2735×** collapse, where the
>   anchor demanded ≥ 235× and ≤ 0.1%. The `|E|` leg reproduces **every printed
>   digit** at all three rank counts (0.000000%); the 0.008613% residue is the
>   magnetostatic `|B|` leg's own solve noise, at the phantom control's
>   0.007326% scale. Faithfulness: the printed values equal step 1's measured
>   source values (`|E|` to 3.090e-07, `|B|` to 7.615e-05), and `|E|` at
>   z = −0.045 m now reads **1.368268e+02** where the interpolant printed
>   **7.670127e+03** — the 56× artifact, gone from the printout.
>   Non-regression: phantom-region aggregates reproduce their `EX-16` record to
>   **0.005745%** (`-n 2`) and **0.002218%** (`-n 4`), inside that path's own
>   floor. Anchor script `scripts/probes/post4_step3_spread.py`, log
>   `20260811T183503Z_POST-4-step3-anchor.log` (PASS, 1 s). **Two anchor-script
>   tolerances were corrected between its first and second execution, with the
>   measurements recorded in code comments** (neither is the chunk's anchor,
>   which passed unchanged): faithfulness 5e-6 → 1e-4, because the comparison is
>   against a *different process's* solves and step 1 had already measured that
>   floor at 0.008426% (the 5e-6 assumed print precision was achievable
>   cross-run; it is not); and non-regression restricted to the rank counts
>   `EX-16` actually recorded (`-n 2`, `-n 4`) — `EX-16` never ran `-n 1`, so
>   the 0.025917% first reading was an n1 leg's 493-point `|B|` **min** compared
>   against an n2 reference, and it is now printed as an unasserted reading
>   rather than silently dropped. The `mri:1` guide's caveat block is rewritten
>   as closed history (with the export-path residue called out), the
>   known-issues entry is **retired** in the same commit, and
>   `check_example_doc_references.py` re-run. Step 4 (the export-path bound) is
>   unaffected and stays open.)* Original text: change `examples/mri/01`'s centerline
>   table to evaluate the **source fields** (`E`, `B` as solved) through
>   `post.evaluation.evaluate_vector_field_parallel`, instead of the
>   `("Lagrange", 1, (3,))` interpolants it prints today; the P1
>   interpolation stays where it is load-bearing (the XDMF/VTX export
>   path), untouched. Refresh the `mri:1` guide's caveat block in the
>   same commit (it currently cites the 23.5539% spread as open). **No
>   `src/` change** — this is an example-level sampling fix; `interpolate`
>   itself is DolfinX behaviour and vertex dofs of a non-conforming field
>   are convention there, not a bug this chunk owns. **Anchor:** centerline
>   spread across `-n 1/2/4` collapses 23.5539% → ≤ 0.1% (measured floor on
>   the source path: 0.008426%, `20260811T140549Z_POST-4-step1-attribution.
>   log`; separation demanded ≥ 235×, ceiling on record 1.163e+04×); plus
>   non-regression — the phantom-region stats reproduce their on-record
>   digits and the printed values now match `E_src`/`B_src` (e.g.
>   1.368268e+02 at z = −0.045 m where the interpolant printed 7.670127e+03).
>   **Negative control:** the pre-fix interpolant spread 97.9755% and the
>   56× `-n 1` artifact, cited from step 1's logs, never recomputed.
>   **Cost:** standard, `-n 1/2/4` re-runs of the step-1 measurement —
>   solves 8/4/4 s on record; the spread script is 1 s. **Traps:** step 1's
>   list — `.reshape(-1, 3)` on single-point eval, complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, rank-local claim counts, `-s` for prints;
>   plus: the guide checker's 48 h freshness window (`OPS-15`) — cite the
>   new logs, and re-run `check_example_doc_references.py` since the guide
>   changes. **Scope boundary:** buys a rank-invariant *and* faithful
>   centerline printout; it does not validate the physics of those values,
>   and the export-path interpolants remain vertex-convention-dependent —
>   that residue is step 4's. The known-issues centerline entry leaves with
>   this commit iff the anchor lands. **Negative result:** a source-path
>   spread that does not collapse contradicts step 1's own measurement —
>   report both tables, keep the entry open, annotate here, stop.
> * **Step 4 — bound the P1-interpolant artifact on the export paths
>   (standard; measurement only; spare — scoped 2026-08-11, 10:30
>   review).** ✅ *(executed 2026-08-11, 19:30 slot (logs 2026-08-12 UTC;
>   date corrected by the 03:00 review audit) — the bound is
>   measured and the step's own **localization hypothesis is REFUTED**, which
>   is the more informative reading. The sweep found **11** P1 interpolation
>   sites in `examples/`, **10** fed by a non-conforming source (N1curl `A`/`E`
>   or DG `B`); `magnetostatics/06_h_convergence_rate.py:164` is the safe
>   exception — it exports the CG1 function it also asserts on. On
>   `examples/mri/01`'s debug preset (9261 cells, `-n 2`, 400 cell midpoints +
>   400 vertices, `20260812T003454Z_POST-4-step4-anchor-n2.log`, exit 0, 4 s)
>   the pointwise relative **median** of |P1 − source| / |source| is
>   **51.17% / 52.47% / 20.18%** at midpoints for `A` / `B` / `E`, against
>   **27.33% / 38.39% / 15.79%** at vertices. The entry demanded midpoint
>   ≤ 1% where vertices show the on-record O(50×); measured, the midpoints are
>   ~50× the expected bound and the vertex/midpoint separations are
>   **0.4185× / 0.4818× / 0.6835×** — the interiors are the *noisier* side, the
>   opposite of the prediction. Mechanism, measured not argued: interpolating
>   the same three sources onto a **DG1** target (same degree, no dofs shared
>   between cells) reproduces them to round-off — scaled median
>   **3.25e-17 / 0.0 / 0.0** against a 1e-14 bound — because all three are
>   degree-1 discontinuous polynomials and are represented exactly there. So
>   degree-1 interpolation error is zero and **100% of the disagreement is the
>   P1 continuity constraint**: the shared vertex dof is one adjacent cell's
>   trace, and it then defines the interpolant across the whole cell, which is
>   why the interior inherits the error rather than escaping it. A vertex
>   *sample* can by chance draw the same cell trace on both paths, which is why
>   the vertex column reads quieter. **Negative control:** a conforming P1
>   source round-tripped through the same machinery agrees to **0.000e+00**
>   against 1e-10. The anchor script's exit code enforces the control, the DG1
>   discriminator, and a **refutation pin** (midpoint relative median ≥ 10%,
>   vertex ≤ midpoint) so a later export change cannot silently invalidate this
>   reading; the hypothesis itself is printed as `verdict=REFUTED` and no
>   longer sets the exit code, per this entry's own negative-result clause.
>   **The first execution FAILed** (exit 1, `20260812T003243Z_POST-4-step4-n2.log`)
>   with the hypothesis asserted as written — that log is committed, not hidden;
>   no tolerance was loosened to make it pass, the refuted claim was
>   demoted to a reported verdict and the measured facts took over the exit
>   code. Probe `scripts/probes/post4_step4_probe.py`; known-issues entry
>   added naming all ten affected exports, including the one case that is not
>   merely visual — `magnetostatics/01_straight_wire.py:185` **evaluates** its
>   radial profile from the P1 interpolant. No `src/` change, no export change,
>   no ParaView claim withdrawn. **Open for the review:** whether to export DG1
>   (faithful, discontinuous rendering, larger files) or keep P1 under the
>   caveat. *(Taken up 2026-08-12, 03:00 review: step 5 below buys the
>   decision table before the call is made.)*)* Original text: Step 1 showed the P1 interpolant of a non-conforming
>   field can sit 56× off its source at a point even at `-n 1`; every
>   example's XDMF/VTX export ships exactly such interpolants. Sweep
>   `examples/` for `interpolate` targets of `("Lagrange", 1, …)` fed by
>   Nédélec/DG sources (grep, then confirm by reading), and on **one**
>   representative fixture (`examples/mri/01`'s debug preset — the probe
>   machinery exists) measure interpolant-vs-source disagreement at cell
>   midpoints and at vertices, reusing `scripts/probes/post4_step1_spread.py`
>   patterns. **Anchor:** the measured disagreement is reported as a
>   max/median table, and the *midpoint* disagreement must sit far below
>   the vertex disagreement (the discontinuity lives at shared vertices/
>   facets) — assert midpoint ≤ 1% where vertex shows the on-record
>   O(50×); a violation is a finding about the export, not a tolerance to
>   tune. **Negative control:** a conforming source (the magnetostatic P1
>   path) interpolated the same way must agree to solver tolerance.
>   **Cost:** standard, `-n 2`, solves seconds on record; the sweep is
>   read-only. **Traps:** step 1's list. **Scope boundary:** measurement +
>   a known-issues caveat naming the affected exports; no export code
>   changes, no ParaView claims withdrawn in-slot. **Negative result:**
>   a small artifact everywhere says the centerline points were
>   pathological (on-axis) — that is itself the caveat text; report,
>   annotate, stop.
> * **Step 5 — price the faithful-export route before the P1-vs-DG1
>   decision is made (standard; measurement only; scoped 2026-08-12,
>   03:00 review — the decision input for step 4's open call; does not
>   reopen the chunk).** ✅ *(executed 2026-08-12, 15:00 slot — **the DG1/VTX
>   route is faithful and the price is 10.5× on disk, nothing on wall clock**.
>   Probe `scripts/probes/post4_step5_probe.py`, `-n 2`, complex build, 5 s
>   (`20260812T200532Z_POST-4-step5-n2.log`, exit 0), fixture identity enforced
>   (9261 cells, step-4's record). **Anchor (1) — round-trip:** the read-back
>   `.bp` agrees with the in-memory DG1 function at **exactly 0.000000e+00**,
>   scaled median *and* max, at both step-4 point sets and independently at dof
>   level (max |Δ| 0.0 against field maxima 1.35e+03 / 1.65e-05 / 1.59e+04) for
>   all three fields — against the ≤ 1e-14 bound. ADIOS2 does not degrade the
>   field; the write path is bit-exact. **Anchor (2) — fidelity to the source:**
>   the read-back DG1 fields read **3.246992e-17 / 0.0 / 0.0** (midpoint scaled
>   median, `A`/`B`/`E`; 3.808588e-17 / 0.0 / 0.0 at vertices) where the P1 path
>   measured in the *same run* reads **51.17084% / 52.47222% / 20.18185%**
>   relative median. **Negative control:** step 4's refutation pin fires on that
>   same run — midpoint relative medians reproduce the step-4 record to
>   **8.19e-9 / 3.65e-7 / 1.24e-7** relative drift and the vertex/midpoint
>   separations come back **0.4185× / 0.4818× / 0.6835×**, digit-identical to
>   step 4, so the fixture did not drift and the comparison stands. **Cost, the
>   number the decision actually turns on:** `.bp` (DG1, 3 fields, BP4) is
>   **6 936 408 B in 4 files** by tree walk against **661 260 B** for the P1
>   `.xdmf` + `.h5` — **10.49×** — while the writer is *faster*, 0.0143 s vs
>   0.0193 s (**0.74×**). So the trade is disk, not time. **Two mechanism facts
>   measured on the way, neither previously on record and both load-bearing for
>   any implementation:** (a) in the **complex** build `VTXWriter` has no
>   complex point-data type and emits **two real arrays per function**,
>   `<name>_real` and `<name>_imag` — any reader (ParaView included) sees two
>   real fields, not one complex one
>   (`20260812T200439Z_POST-4-step5-n2.log`); (b) VTX point data on a
>   discontinuous space is one point per **dof coordinate**, i.e.
>   `size_local + num_ghosts` rows per writer rank in dofmap order — the smoke
>   arm on a unit cube measured 2884 rows against size_local 2596 + 288 ghosts
>   (`20260812T200352Z_POST-4-step5-smoke.log`), where the real fixture's DG1
>   space happens to carry no ghosts (18 516 = size_local). A read-back that
>   assumes owned-only rows silently mis-reconstructs; this probe checks the
>   extent rather than assuming it. **The smoke arm's first execution FAILed**
>   (`20260812T200316Z_POST-4-step5-smoke.log`) on exactly that assumption —
>   committed, not hidden; nothing was loosened, the reconstruction was
>   corrected. No `src/` change, no example switched its export, `POST-4` stays
>   ✅. **Open for the review — the call is now priced, not argued:** DG1/VTX
>   buys exact fidelity for 10.5× disk and no time, and costs a
>   two-real-arrays-per-field representation of every complex field; "P1 +
>   caveat" costs O(20–52%) disagreement in every rendered picture. ParaView-side
>   rendering of DG1 `.bp` is **not** asserted here and cannot be headless — it
>   remains a dashboard Waiting-on-you one-click operator check.)*
>   **Review call, 2026-08-12 (18:00 daily review), on the measured
>   table: DG1/VTX is the faithful-export direction.** Exact fidelity for
>   10.5× disk and *no* wall-clock cost is the right trade for any export
>   consumed as data; O(20–52%) in every rendered picture is not a
>   caveat, it is a defect with a caveat attached. But **adoption is
>   blocked on the operator's one-click ParaView check** of a DG1 `.bp`
>   (now on the dashboard's Waiting-on-you, with the complex-build
>   two-real-arrays-per-field caveat stated so the operator knows what
>   they should see) — "P1 + caveat" remains the standing answer and no
>   example switches its export until that check returns. No implementer
>   item queued: the switch is one mechanical commit once the check
>   clears, and queueing it ahead of the check inverts the dependency.
>   Audit (18:00 review): COMPLIANT on all §4 criteria — the round-trip
>   identity is asserted at ≤ 1e-14 and measured exactly 0.0, and all
>   four failed runs are committed, not hidden. Original text:
>   On `examples/mri/01`'s debug preset (9261
>   cells, `-n 2`, seconds on record), write the three fields through the
>   **DG1/VTX route** — `B` (already DG1) directly, `A`/`E` interpolated
>   N1curl → DG1 (exact per step 4: 3.25e-17 scaled median) — via
>   `VTXWriter` to `.bp`, read them back, and measure. **Anchor:** (1)
>   round-trip read-back agrees with the in-memory DG1 function to
>   ≤ **1e-14** scaled median at the step-4 point sets (the `EX-14`/
>   `EX-17` `.bp` round-trip machinery is on record bit-identical — reuse
>   it, restate nothing); (2) the step-4 probe pointed at the read-back
>   DG1 fields reads round-off where the P1 path reads **51.17% /
>   52.47% / 20.18%** — run both paths in one command and print the
>   table. **Negative control:** the P1 path's refutation pin (midpoint
>   median ≥ 10%, vertex ≤ midpoint) must still fire on the same run —
>   if the P1 numbers moved, the fixture drifted and the comparison is
>   void. Report beside the numbers: file size `.bp`-DG1 vs `.xdmf`-P1,
>   and wall-clock of each writer. **Cost:** standard, `-n 2`,
>   `timeout -k 30 180`; solve seconds, writes seconds. **Traps:** step
>   1's list (reshape, complex build, rank-local counts, `-s`); ADIOS2
>   engine files are *directories* — size them with a tree walk, not
>   `stat`; ParaView-side rendering of DG1 `.bp` **cannot be asserted
>   headless** — it goes to the dashboard's Waiting-on-you as a
>   one-click operator check, not into any gate. **Scope boundary:** no
>   example switches its export in-slot; `POST-4` stays ✅; this buys the
>   decision table, a review makes the call. **Negative result:** a DG1
>   round-trip that is *not* faithful (ADIOS2 write path degrades it) is
>   the finding that kills the DG1 route and makes "P1 + caveat" the
>   standing answer — report, annotate here, stop.

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
> **Weekly-review adjudication, 2026-08-09 (the 3b-xiii/3b-xiv escalation —
> this is the licence those steps asked for).** The lineage's own record makes
> the call almost mechanical: four owners of the ~3.02 pp estimator-vs-control
> deviation are excluded by measurement (wedge limits 3b-x, ωM₁₂ reference
> 3b-viii, PEC box 3b-xii, loss 3b-xiv's 4×-in-σ ⇒ +0.19 pp sensitivity), and
> both corners of the intended 2×2 are degenerate (closed+lossy is a shorted
> turn, gapped+lossless is an open circuit). Four decisions:
> **(1) Licence granted** for the fixture-topology change 3b-xiv proposed:
> *gapped vs closed at fixed σ = 800*, the one variable the two routes still
> differ in, at the σ where both are well-posed. Measurement only, on the
> `attempt/PORT-1-step3bxiv-20260808T095500Z` lineage; the daily review scopes
> it as step 3b-xv with its usual anchors/bands.
> **(2) Diagnostic budget: two more slots**, the discriminator plus at most
> one follow-up. This lineage has spent six steps on a 3 pp deviation; that
> was correct discipline (the estimator is the foundation every later port
> number stands on) and it is now one suspect from done — but it does not get
> an open-ended seventh-and-beyond. If the discriminator lands (mixed) or
> contradicts 3b-xiv, the question comes back to the next weekly review
> rather than burning further slots.
> **(3) Pre-registered disposition** so the outcome is not adjudicated by the
> slot that measures it: if the gap owns the deviation — the expected reading,
> since everything else is excluded — then the ~3 pp is a *physical property
> of the gapped fixture* (the gap's fringing/capacitive termination genuinely
> changes the terminal-to-terminal reading), not an estimator defect. The
> consistency gate is then re-pointed to compare at matched topology, the
> −3.0224e-02 record is kept as the measured gapped-vs-closed offset with its
> owner named, and the lineage proceeds to the deferred 3b-i/3b-ii port-pair
> gate on the two-torus fixture carrying the stated systematic.
> `REACTION_CONSISTENCY_TOLERANCE` (0.03) and `MUTUAL_TOLERANCE` (0.10) stay
> untouched until that re-pointing commit, which must cite the discriminator's
> log — never loosened to make the current red green.
> **(4) Branch disposition:** `attempt/PORT-1-step3bxiv-20260808T095500Z`
> stays the working lineage and **lands on `main` together with the first ✅
> gate this lineage produces** — nothing lands from a 🟡 park without a gate.
> The `_validate_material_map_tags` hunk it carries is already on `main` via
> `OPS-13`; whoever lands the branch resolves that already-applied conflict
> trivially, as the 3b-xiii note records. *(Executed: the lineage landed
> by path with 3b-xvii, `a755afb`, 2026-08-13. The 2026-08-13 03:00 review
> verified capture — xiv/xvi logs and rows on `main` via the landing, the
> xv logs and rows copied by the review itself, the xv probe-test variant
> deliberately not landed (measurement scaffolding, superseded by the
> matched-topology gate) — and deleted all three `attempt/PORT-1-*`
> branches.)*
>
> * **Step 3b-xv — the licensed discriminator: gapped vs closed at fixed
>   σ = 800** 🟡 *(executed 2026-08-09, 04:30 run; parked on
>   `attempt/PORT-1-step3bxv-20260809T093000Z` (`a158c91`), measurement only,
>   nothing landed. **Band (mixed), by 43×**: closed(σ = 800 on `WIRE_TAGS`,
>   gap boxes air) reads **1.223696 × ωM₁₂** — 30.13 pp from closed(σ = 0)
>   0.922423 and 32.92 pp from gapped(σ = 800) 0.894543, against the 0.7 pp
>   quarter-spread. Fixture identity byte-reproduced first (0.894543 /
>   0.894022 / 0.922423 / −3.0224e-02); `|I_cond/I′| = 0.005792`, neither
>   3b-xiii's 0.865 short nor the gapped 0.971942 series continuity; I′
>   identical to the control's to < 1e-9 (gated), so the rung did not move its
>   own normalisation. **Why (mixed):** at fixed *closed* topology, moving only
>   where σ sits takes the estimator 0.107556 (wire ∪ gap box, 3b-xiii) →
>   1.223696 (wire alone) either side of the control's 0.922423, so the closed
>   route has no σ-independent estimator to be the fixed endpoint — step 3b-x's
>   already-measured mechanism (−∫E·J₂ over a **lossy test region** returns the
>   ohmic term, factor 244 there, +32.7% here; `WIRE_TAGS` made the *undriven*
>   loop lossy too). All four corners of the 2×2 are now measured and none is
>   clean. Per decision (2) this returns to the **weekly review**, which holds
>   the second licensed slot; the successor the run proposes is σ on the
>   **driven** wire tag alone, keeping the test region lossless. Tolerances
>   untouched (0.03 / 0.10). `-n 2`, 475 s inside `timeout 600`, 22 passed +
>   the known consistency gate red;
>   `20260809T093317Z_PORT-1-step3bxv-disc-n2.log`,
>   `20260809T093302Z_PORT-1-step3bxv-collect.log` — copied to `main` with
>   their test-results rows by the 2026-08-13 03:00 review (they lived only
>   on the xv branch; the 3b-xvii landing took the xvi lineage, which had
>   forked before them).
>   Full journal: `docs/testing/attempts.md`, 2026-08-09T09:30Z.)*
>   *(scoped 2026-08-09, 03:00 review, under the weekly-review
>   licence above — decision (1). Measurement only, on the
>   `attempt/PORT-1-step3bxiv-20260808T095500Z` lineage (`5f34f88`); every
>   disposition parks and reports, nothing lands in-slot, per decisions (2)
>   and (3). This is the first of the two licensed slots.)* Hold σ = 800 on
>   `WIRE_TAGS` (3b-xiv's σ placement — never the gap box, which closes the
>   loop into 3b-xiii's degeneracy) and move only the topology: solve the
>   **closed** loop at σ = 800 and read the terminal-to-terminal estimator
>   beside the two on-record endpoints — gapped(σ = 800) **0.894543** and
>   closed(σ = 0) **0.922423**, 2.788 pp apart. **Anchor:** (1) fixture
>   identity first — byte-reproduce the padding-0.08 record (estimator
>   0.894543 / 0.894022, control 0.922423, deviation −3.0224e-02) before any
>   new solve; (2) the discriminator, pre-decided bands at quarter-spread
>   (0.7 pp): **(gap owns it)** `|est_closed(σ=800) − 0.922423| ≤ 0.7 pp` ⇒
>   closing the loop restores the control reading at matched σ; the ~3 pp is
>   a physical property of the gapped fixture and the weekly review's
>   pre-registered disposition (3) applies — report, park; the re-pointing
>   commit is separate and must cite this log. **(topology does not move
>   it)** `|est_closed(σ=800) − 0.894543| ≤ 0.7 pp` ⇒ the deviation survives
>   matched topology, contradicting 3b-xiv's loss exoneration — back to the
>   weekly review per decision (2), report all numbers. **(mixed)** between
>   ⇒ report both distances, back to the weekly review. **Negative
>   controls:** print `|I_cond/I′|` for the closed σ = 800 solve and label
>   it — 3b-xiii's shorted-turn record (up to 0.865) is the expected
>   signature and is *why* this rung reads as a diagnostic, not a
>   consistency control; the gapped 0.971942 series-continuity value is on
>   record, cite not recompute. **Cost:** standard, `-n 2`, one command
>   `timeout 600` — 3b-xiii's measured envelope (344.6 s) covers mesh
>   byte-reproduction plus ~25 s solves. **Traps:** the 3b-xiii list
>   unchanged (FFCx lock, pytest `-s`, complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first, σ via the DG0
>   field never a global); every pinned digit-string on the branch is
>   gapped-σ800-specific — print, pin nothing in-slot;
>   `REACTION_CONSISTENCY_TOLERANCE` stays 0.03 and `MUTUAL_TOLERANCE`
>   stays 0.10 under every band; the branch's `_validate_material_map_tags`
>   hunk is already on `main` (resolve trivially only if landing, which no
>   band does in-slot). **Does not close:** `PORT-1`, known-issues 3, the
>   branch disposition, or the gate re-pointing — the last two stay the
>   weekly review's per its decisions (3)/(4); this step only delivers the
>   measurement they are conditioned on. **Negative result:** every band is
>   a finding; a degenerate or unforeseen reading (e.g. the closed lossy
>   solve refusing the impressed-drive normalisation) is itself the
>   measurement — report and stop, never substitute a different σ or
>   topology silently.
>
> **Operator-session adjudication, 2026-08-12 (interactive session, at the
> human operator's direction — this spends the *decision* of the second
> licensed slot granted 2026-08-09; the slot itself runs from §9 as step
> 3b-xvi. The 2026-08-16 weekly review audits this rather than re-opening
> it, unless 3b-xvi's reading itself demands otherwise).** Grounding: the
> in-repo reference library (`docs/references/jin-fem-3e/`, added
> 2026-08-12). Two findings from the text change the plan:
> **(a)** the lineage's estimator families map exactly onto Jin's feed-model
> taxonomy (§10.4.2.1: current filament/probe, magnetic frill, and the gap
> generator — "specifying the field across a gap a priori" — with the
> caveat that "more accurate modeling … is possible with the use of a
> waveguide port boundary condition", ch. 11). The ~3 pp deviation is a
> **documented artifact class** of gap-generator feeds — known least
> accurate for impedance and gap-geometry dependent — not an unexplained
> defect. **(b)** Jin's feed-modeling practice refines the feed region
> locally as routine hygiene (ch. 12, coax-fed cone: 3 mm elements at the
> feed vs 10 mm elsewhere), and this fixture has never been tested for
> that: `h_wire = 2.5e-3` spans the 1.2e-2 gap arc in ~5 cells (3b-vi's
> count), and 3b-ix located **45% of the loop EMF in the 2e-4 overhang
> region — one order below local mesh size, sub-cell**. A reading whose
> feed-region mesh convergence is unestablished must not be diagnosed for
> physics ownership; the discretisation question precedes the σ question.
> Decisions:
> **(1)** The second licensed slot is **re-pointed** from 3b-xv's proposed
> σ-on-driven-wire successor to **step 3b-xvi below — gap-region
> h-refinement of the estimator**.
> **(2)** Further σ-placement variants are **barred**: the 2×2 is complete
> and every corner measured (3b-xv). Daily reviews do not scope new ones.
> **(3)** **All-outcomes-proceed, pre-registered:** after 3b-xvi the
> lineage proceeds to the deferred 3b-i/3b-ii port-pair gate carrying the
> offset as a **stated systematic** labeled by whichever band fired
> (feed-model physics per Jin §10.4.2.1 / feed under-resolution, measured /
> unowned). No outcome loops back into diagnosis. The re-pointing commit
> re-aims the consistency gate at matched topology, keeps the −3.0224e-02
> record with its label, and remains the only place
> `REACTION_CONSISTENCY_TOLERANCE` (0.03) / `MUTUAL_TOLERANCE` (0.10) may
> move — citing 3b-xvi's log. The port-pair gate's reciprocity identity is
> the standing tripwire if the label is wrong.
> **(4)** Zero-solve annotation commissioned: apply `MAT-6` step 9's
> free-exponent fit (`ratio = r∞ − C·W^(−p)`) to 3b-xi's three padding
> rungs (deficits −8.0324 / −5.0256 / −3.2733 pp at W = 0.08/0.10/0.12) so
> the port-pair gate states the box term as an extrapolated number rather
> than "the suspect". Arithmetic on recorded digits; may ride with 3b-xvi
> or any later slot.
> **(5)** Long-horizon (§10 note): **no further `∫E·dl` estimator variants
> after this lineage** — voltage on an inductive fixture is a stated-path
> convention (the estimator families measured three different numbers
> because they are three different path conventions, not three attempts at
> one truth). Port-definition investment for the birdcage moves toward a
> lumped/circuit-element port boundary condition per Jin's own hierarchy
> (ch. 11); consult the reference library before scoping.
> **(6)** 2026-08-09 decision (4) stands unchanged: the attempt branch
> lands on `main` only with the lineage's first ✅ gate.
>
> * **Step 3b-xvi — gap-region h-refinement of the terminal-to-terminal
>   estimator** *(scoped 2026-08-12 by the operator-session adjudication
>   above; one run, standard tier, measurement only, on the
>   `attempt/PORT-1-step3bxiv-20260808T095500Z` lineage like 3b-xv).*
>   Rebuild the gapped padding-0.08 fixture with a **local** gmsh size
>   field halving the element size in the gap boxes and overhang region
>   only (target h_gap ≈ 1.25e-3; **never** refine globally — the PEC-box
>   deficit must stay common-mode with the on-record control), one solve,
>   read the terminal-to-terminal estimator. **Anchor:** (1) fixture
>   identity first — byte-reproduce the unrefined record (estimator
>   0.894543, control 0.922423, deviation −3.0224e-02) before building the
>   refined mesh; (2) a mesh-only probe prints cells-across-arc and
>   cells-across-overhang for both meshes — turns the "~5 cells /
>   sub-cell" inference into record; (3) the refined estimator beside
>   0.894543, pre-registered bands at 0.5 pp: **(converged at the feed)**
>   |Δ| < 0.5 pp ⇒ feed discretisation exonerated, the offset is gap
>   physics — adjudication decision (3) fires with the physics label
>   (Jin §10.4.2.1 cited as the mechanism class). **(under-resolved)**
>   |Δ| ≥ 0.5 pp ⇒ feed discretisation owns part of the offset; the stated
>   systematic becomes the refined reading with the trend direction noted —
>   decision (3) fires with the discretisation label. Either band
>   proceeds; neither loops back. **Negative control:** the closed-loop
>   control is *not* re-solved (a gap-local size field cannot touch its
>   mesh); instead assert the refined gapped mesh's cell count *outside*
>   the gap region moves < 5%, so the common-mode claim about the box
>   deficit holds. **Cost:** standard, `-n 2`, one `timeout 600` command —
>   3b-xiii's envelope (344.6 s) covered mesh + two solves; one mesh + one
>   solve fits with margin. If the mesh-only probe prices the refined
>   solve out of the envelope, halve the refinement factor, not the
>   region, and report both cell counts. **Traps:** the 3b-xiii list
>   (FFCx lock, pytest `-s`, complex build + `FEM_EM_REQUIRE_COMPLEX=1`,
>   `tests/environment` first, σ via the DG0 field never a global); gmsh
>   size fields interact with the wall-tolerance classification (`GEO-13`)
>   — assert the gap-box facet-tag identity 1.000000000000 before trusting
>   the estimator; print, pin nothing in-slot; tolerances untouched under
>   every band (0.03 / 0.10). **Does not close:** `PORT-1`, known-issues 3,
>   or the re-pointing — that is a separate commit citing this log, per
>   decision (3). **Negative result:** every band is a finding; a mesh
>   that refuses the size field or breaks the tag identity is reported and
>   stopped, never worked around silently.
>
>   🟡 **Mesh arm executed 2026-08-12 (04:30 slot), no solve bought — the
>   step's *refinement factor* is refuted, the step itself stands.** Parked
>   on `attempt/PORT-1-step3bxvi-20260812T093000Z` (`0d128ca`);
>   `20260812T093819Z_PORT-1-step3bxvi-mesh.log`,
>   `…094005Z_…-mesh6e4.log`; attempts.md 2026-08-12T09:30Z. Fixture
>   identity held (178 055 cells, the number on record; gap-box
>   meshed/analytic volume **1.000000000000** on both meshes; facet tags
>   `[1, 201, 202]`). Measured, where the adjudication had inferred:
>   **cells_across_overhang = 0.1405** (sub-cell, premise confirmed) but
>   **cells_across_arc = 24.70**, not the "~5" quoted from 3b-vi — that
>   count predates step 3b-vii's `gap_arc_resolution = 3e-4`. The
>   consequence is arithmetic: the wall band is sized by the arc field's
>   slope-0.3 ramp at `3e-4 + 0.3·(5e-3 − 1.2e-3) = 1.44e-3` (measured
>   1.4230e-3), **not** at `h_wire = 2.5e-3`, so the scoped
>   `h_gap ≈ 1.25e-3` moves the wall band 4.2% and the cell count 1.0430×
>   — a solve arm there would compare a mesh against itself. At
>   `h_box = 6.0e-4` (wall band 9.05e-4, cells_across_overhang 0.2209,
>   1.5223×) the pre-registered locality control **fires**: cells outside
>   the gap boxes move +35.4560% against < 5%, because the `Box` field's
>   `Thickness` inherits the slope-0.3 value (0.098 m) and leaks a 10 cm
>   shell into the air. **Next attempt (one slot):** bound that
>   `Thickness` to ~3–5 mm, re-confirm the < 5% band at `h_box = 6.0e-4`
>   on the mesh arm, then buy the solve arm — `port1_step3bxvi_probe.py
>   solve 6.0e-4`, one mesh + one σ = 800 rung per arm, ~2×(55 + 30) s
>   inside `timeout -k 30 590`. Bands, tolerances and decision (3)
>   unchanged; only the refinement factor moves, and it moves *because*
>   the mesh was measured.
>
>   🟡 **Mesh arm re-run 2026-08-12 (06:00 slot) with the `Thickness`
>   bound — the refinement is now local and the refinement factor is
>   viable, but the *pre-registered locality control cannot see it*; still
>   no solve bought.** Same branch
>   `attempt/PORT-1-step3bxvi-20260812T093000Z` (`bc6d69c`);
>   `20260812T110229Z_PORT-1-step3bxvi-mesh6e4-capped.log`,
>   `20260812T110511Z_PORT-1-step3bxvi-mesh6e4-collar.log`; attempts.md
>   2026-08-12T11:00Z. Capping the `Box` field's `Thickness` at 5 mm
>   (`GAP_BOX_THICKNESS_CAP_M`, `mesh.py`) against the slope-0.3 rule's
>   0.098 m cut the control from **+35.4560% → +16.3159%** at
>   `h_box = 6.0e-4` — still over the < 5% band, so the recipe's
>   "re-confirm, then buy the solve" clause did **not** fire and the slot
>   stopped there. The added diagnostic says why, and it is decisive:
>   count the same cells outside a *dilated* box and the move is
>   **−0.1658% at a 5 mm collar, −0.3098% at 10 mm, −0.2937% at 20 mm** —
>   every one of the 21 087 added cells sits within 5 mm of the gap box,
>   and beyond that the mesh is unchanged to within gmsh's run-to-run
>   noise. That collar is not a leak: a size field stepping
>   6.0e-4 → `h_wire` = 2.5e-3 cannot do it in zero cells, so gmsh lays a
>   gradation shell just outside the box whatever `Thickness` says, and the
>   control counts it as "outside". The claim the control protects — the
>   PEC-box deficit stays common-mode with the unrefined record — is about
>   a wall **0.08 m** away, and is measured *satisfied* at every collar
>   width. Mesh otherwise healthy: 178 055 → 246 364 cells (1.3836×, under
>   the 350 000 ceiling), `cells_across_overhang` 0.1405 → 0.2209,
>   `cells_across_arc` 24.70 → 24.63 (arc field untouched, as designed),
>   gap-box volume identity 1.000000000000 and facet tags `[1, 201, 202]`
>   on both meshes. For contrast the earlier `h_box = 1.25e-3` arm
>   *passes* the control (+3.8262%) precisely because it barely refines
>   (1.0430×) — so as written the control admits only refinements too weak
>   to answer the question. **Decision needed from a review, not from a
>   slot:** re-point the locality control to the 5 mm-dilated box at the
>   same < 5% band (the measurements above are its calibration), after
>   which the solve arm — `port1_step3bxvi_probe.py solve 6.0e-4`, bands
>   0.5 pp and tolerances 0.03 / 0.10 unchanged — is one command. Not
>   re-pointed in-slot: it is a pre-registered control and this slot had a
>   live incentive to move it. Cost to price into that arm: the refined
>   mesh is 246 364 cells and step 1 killed a 237 926-cell solve at 180 s
>   inside MUMPS, so it wants its own `timeout -k 30 590` and exit 124 is
>   a possible outcome.
>
>   **Review decision, 2026-08-12 (10:30 daily review) — the locality
>   control is re-pointed to the 5 mm-dilated gap boxes, same < 5% band.**
>   Grounds, from the 06:00 slot's calibration measurements: (a) the claim
>   the control protects — the PEC-box deficit stays common-mode because
>   the mesh at the wall 0.08 m away is untouched — is measured satisfied
>   at every collar width (−0.1658% / −0.3098% / −0.2937% at 5/10/20 mm);
>   (b) the raw +16.3159% is gmsh's mandatory gradation collar (a size
>   field stepping 6.0e-4 → 2.5e-3 cannot do it in zero cells), not a leak;
>   (c) as written the control admits only refinements too weak to answer
>   the question (the 1.0430× arm passes, the 1.5223× arm fails). The
>   band itself (< 5%), the estimator bands (0.5 pp), and the tolerances
>   (0.03 / 0.10) do not move — this re-points the instrument at the claim
>   it was always meant to test; it does not widen anything. The dilation
>   width is 5 mm because it is the smallest measured collar that already
>   contains every added cell. Made by a review, not the incentivized
>   slot, per the 06:00 entry's own hand-off. **Third attempt (one slot,
>   re-queued as §9 item 1):** on the parked branch, re-run the mesh arm
>   at `h_box = 6.0e-4` asserting the re-pointed control (< 5% outside the
>   5 mm-dilated boxes) plus the standing identities (gap-box volume
>   1.000000000000, facet tags `[1, 201, 202]`), then buy the solve arm —
>   `port1_step3bxvi_probe.py solve 6.0e-4`, refined estimator vs 0.894543
>   at the pre-registered 0.5 pp bands, either band proceeds per
>   adjudication decision (3). 246 364 cells wants its own
>   `timeout -k 30 590`; exit 124 is itself a finding ("the refined
>   fixture does not fit the window at `-n 2`") — report it, park, stop.
>
>   ✅ **Third attempt executed 2026-08-12 (12:00 slot) — the re-pointed
>   control passes, the solve was bought, and the reading is
>   *converged at the feed*: feed discretisation is exonerated and the
>   offset is gap physics.** Parked on the same lineage branch
>   `attempt/PORT-1-step3bxvi-20260812T093000Z` (`d459af9`);
>   `20260812T170128Z_PORT-1-step3bxvi-mesh6e4-repointed.log` (mesh arm,
>   95 s, exit 0), `20260812T170317Z_PORT-1-step3bxvi-solve6e4.log`
>   (solve arm, 174 s, exit 0); attempts.md 2026-08-12T17:00Z. Both arms
>   `-n 2`, complex build, standard tier.
>   **Control (enforced first, in its own command, before the solve was
>   bought):** cells outside the 5 mm-dilated gap boxes 115 220 → 115 029,
>   **−0.1658%** against the < 5% band — digit-identical to the 06:00
>   calibration, so the re-pointing reproduces rather than re-measures.
>   The undilated count is printed beside it and gated on nothing
>   (129 242 → 150 329, +16.3159%: gmsh's mandatory gradation collar).
>   Standing identities held on both meshes — gap-box meshed/analytic
>   volume **1.000000000000**, facet tags `[1, 201, 202]`; mesh
>   178 055 → 246 364 cells (1.3836×, under the 350 000 ceiling),
>   `cells_across_overhang` 0.1405 → 0.2209, `cells_across_arc`
>   24.70 → 24.63.
>   **Anchor:** the unrefined arm's estimator is **0.894543**, the record
>   to six digits, **+0.0000 pp** — the fixture reproduces itself before
>   the refined arm is read.
>   **Reading:** refined estimator **0.895051**, **Δ = +0.0508 pp**
>   against the pre-registered 0.5 pp band ⇒ band **(converged at the
>   feed)**. A 1.38× mesh carrying 1.57× the resolution across the
>   overhang moves the estimator by **one tenth of the band**, so the
>   −3.02e-02 deviation from the 0.922423 closed-loop control is **not**
>   owned by the feed's discretisation. Against that cited control the
>   refined deviation is −2.9674e-02 (record −3.0224e-02). Adjudication
>   decision (3) therefore fires with the **physics** label (Jin
>   §10.4.2.1 as the mechanism class), as pre-registered. Bands,
>   tolerances (0.03 / 0.10) and decision (3) untouched; the solve arms
>   cost 25.5 s and 29.8 s, so the `timeout -k 30 590` window was never
>   near — exit 124 did not fire.
>   **Does not close** `PORT-1` (stays 🟡), known-issues 3, or the
>   re-pointing of the σ-on-driven-wire successor — decision (3)'s commit
>   is separate and cites these two logs. **Hand-off:** the code is
>   parked, not landed, per this item's scope boundary; a review that
>   wants the re-pointed control in the tree lands `d459af9` from the
>   branch. The physics label is now *earned by measurement* rather than
>   assumed, which is the input decision (3) was waiting on.
>   **Review actions, 2026-08-12 (18:00 daily review):** audit COMPLIANT
>   on all §4 criteria — the control was gated in its own command before
>   the solve was bought, both footers carry exit 0 and elapsed times,
>   and every band was pre-registered. The two logs lived only on the
>   parked branch; **copied to `main` with this review's commit** so the
>   ✅ evidence is main-resident regardless of branch fate (the branch
>   itself still lands only per decision (6)). Decision (3)'s re-pointing
>   commit is queued as §9 item 1 — it lands the lineage branch
>   (`d459af9`), the lineage's first ✅ gate — and the deferred
>   3b-i/3b-ii port-pair gate as §9 item 2, serial on item 1.
>
> * **Step 3b-xvii — decision (3)'s re-pointing commit** ✅ *(2026-08-12,
>   19:30 run; the lineage's first ✅ gate, and the commit that lands the
>   branch)*. `attempt/PORT-1-step3bxvi-20260812T093000Z` (`d459af9`) is on
>   `main`: applied by path rather than merged, because the branch forked at
>   `dc4eb66` (2026-08-07 10:30) and a wholesale merge would have reverted
>   100+ commits of main-side work. `io/mesh.py` was untouched on `main`
>   since the fork and taken verbatim (carrying `GAP_BOX_THICKNESS_CAP_M`);
>   the `core/time_harmonic.py` `_validate_material_map_tags` hunk was
>   skipped, already on `main` via `OPS-13` (verified: `mesh.comm.allgather`
>   present at line 163); 19 branch-only logs, three probes
>   (`port1_step3bvii/xii/xvi_probe.py`) and both gap-voltage test modules
>   landed, with the 19 harness rows interleaved chronologically into
>   `test-results.md`.
>   **The re-point.** `test_gap_voltage_mutual_matches_the_same_fixture_reaction_control`
>   no longer compares gapped-against-closed. It gates **Faraday closure on
>   the gapped loop at matched topology**: `Im Z_terminal` against
>   `Im Z_loop` from `V_terminal + V_wire`, both read off the same gapped
>   σ = 800 S/m solve. Measured **−2.6687e-03 (gap 101) / −2.5842e-03
>   (gap 102)** against `REACTION_CONSISTENCY_TOLERANCE` = 0.03 **unmoved** —
>   11× margin, so the re-point did not need a loosened bound, which decision
>   (3) named as the tripwire. Negative control: the wedge-only estimator
>   0.4937 × ωM₁₂ gives ratio 0.5504, missing the closure by 45% (15× the
>   bound). Fixture identity reproduced digit-for-digit: estimator 0.894543 /
>   0.894022, wire term 0.002394 / 0.002316 × ωM₁₂, reciprocity 5.8343e-04
>   against `RECIPROCITY_TOLERANCE` 1e-2 (the 1e-9 figure belongs to the
>   step-1/2 lossless fixture, not this one). The −3.0224e-02 / −3.0789e-02
>   gapped-vs-closed deviation is **printed ungated** with its earned label —
>   gap physics, Jin §10.4.2.1's gap-generator feed model — citing
>   `20260812T170128Z_...-mesh6e4-repointed.log` and
>   `20260812T170317Z_...-solve6e4.log`. `MUTUAL_TOLERANCE` unmoved at 0.10.
>   `-n 2`, **22 passed, exit 0, 474 s**, standard tier;
>   `20260813T003532Z_PORT-1-step3bxvii-repoint-n2.log`.
>   **Judgement this slot had to make, flagged for the weekly review.**
>   Decision (3) said "matched topology" and item 1 said "a gapped-fixture
>   reference" without naming one, and the fixture offers no *independent
>   route* at matched topology: 3b-x measured that a reaction integral over a
>   gapped, conducting arc returns the wire term (factor 244), and the σ = 0
>   impressed-current control is closed by construction. The closure identity
>   gated here is real and was previously ungated — the retiling gate (1e-3)
>   tiles the *gap* arc and is blind to the wire, and reciprocity (1e-2)
>   compares the two drives with each other — but it is a self-consistency
>   identity, not an independent route. Independence returns with the
>   port-pair gate (§9 item 2). If the weekly review wants a different
>   matched-topology reference, this test is the single place to change.
>   **Does not close** `PORT-1` (stays 🟡) or known-issues 3.
>
> * **Step 3b-xviii — the deferred 3b-i/3b-ii port-pair gate** ✅ *(2026-08-12,
>   21:00 run; the lineage's second ✅ gate, and the first time this fixture's
>   `Im Z₁₂` is asserted against an **independent** reference)*.
>   `test_gap_voltage_port_pair_mutual_carries_its_systematics` replaces the
>   printed-only `..._is_reported` and gates the gap-voltage `Im Z₁₂` against
>   the filamentary closed form `ωM₁₂ = +1.241755 Ω` at `MUTUAL_TOLERANCE`
>   = 0.10, **unmoved**, carrying decision (3)'s two pre-registered systematics
>   **by name in the assertion message**. The measured ladder, printed raw
>   first: **raw 0.894283 (−10.57%) → +PEC box `D∞ = +0.0169` at
>   `p = 1.657` (effective-range, §7 3b-xi — never quoted without its exponent)
>   → 0.911183 (−8.88%) → ÷(1 − 0.030224) gap physics (Jin 3e §10.4.2.1) →
>   0.939581, deviation −6.04%** against the 10% band, a 1.66× margin.
>   The raw number is on the record *because it does not clear the band*: the
>   0.57 pp miss is what the two systematics are there to account for, and the
>   band was not widened by a point. **Negative control, executed rather than
>   cited:** the gate is a pure function of one number
>   (`_mutual_systematics_ladder`), so it is run in the same test on step 1's
>   unfragmented-mesh record `Im Z₁₂ ≡ 0` — corrected ratio 0.017427, −98.26%,
>   `passes = False`, asserted. **Network tripwires:** reciprocity unmoved and
>   reproduced (5.8343e-04 vs 1e-2 — the 1e-9 identity belongs to the reaction
>   route, where the same bilinear form appears in both off-diagonals); and the
>   step-2 `scattering_from_impedance` machinery on this `Z` for the first time
>   — **‖S−Sᵀ‖/‖S‖ = 2.5494e-05** (band 1e-2) and **‖S‖₂ = 0.861449** ≤ 1,
>   passive with a 0.1386 loss margin. Step 2's *unitarity* assertion is
>   deliberately absent: that fixture was lossless air, this one dissipates
>   (`Re Z₁₁ = +3.82 Ω`), so `‖S‖₂ = 1` would be the wrong claim. `-n 2`,
>   **23 passed, exit 0, 457 s**, standard tier;
>   `20260813T020352Z_PORT-1-step3bxviii-pairgate-n2.log` (collect-only
>   preflight `20260813T020340Z_PORT-1-step3bxviii-collect.log`, 3 s).
>   **What this licenses and what it does not.** The two-torus `∫E·dl`
>   machinery is now gated against a reference that is not derived from this
>   fixture — the independence 3b-xvii's self-consistency identity could not
>   supply. It does **not** claim path-independence (the estimator is a
>   stated-path convention, decision (5)), and the −6.04% residual is
>   unattributed: finite cross-section (3b-viii measured +0.481% on the
>   reference side), the remaining truncation beyond the extrapolation, and
>   discretisation. **For the weekly review:** the corrections are additive in
>   the units each was measured in (box: pp of ratio; gap: relative vs the
>   closed control), which assumes they compose independently — untested, and
>   the 3.1 pp exponent-model spread on the box term is the larger of the two
>   uncertainties either way. **Does not close** `PORT-1` (stays 🟡) or
>   known-issues 3; birdcage ports and B1+ stay held.
>
> * **Step 4 — the package path: `run_n_port_sparameter_sweep` reads the
>   solved field** ⬜ *(scoped 2026-08-13, 10:30 review — the §10 subgoal-2
>   critical-path step the 3b lineage cleared the way for. §2's standing
>   sentence — "every S-parameter the package produces is a heuristic" —
>   falls only when this lands.)* Replace the port-voltage source inside
>   `run_n_port_sparameter_sweep` (`ports/excitation.py`'s coupling
>   heuristic) with the gap-voltage route the pair gate validated: one
>   impressed-gap solve per port on the two-torus fixture, `V = −∫E·dl` via
>   the gate module's estimator, Z column-by-column, S via the step-3a
>   converter, systematics via `ports/systematics.py` (single source, the
>   `EX-18` lift). **Anchor:** the package entry point reproduces the gated
>   record — raw ratio within `RAW_REPRODUCTION_BAND = 2e-3` of 0.894283,
>   corrected inside the unmoved `MUTUAL_TOLERANCE = 0.10`,
>   `‖S−Sᵀ‖/‖S‖ < 1e-3`, `‖S‖₂ ≤ 1` — asserted through the *package* call,
>   not the test path. **Negative control, executed:** the retiring
>   heuristic on the same fixture — print its S beside the solved-field S
>   and assert they *differ* beyond the reproduction band (if the heuristic
>   accidentally agrees, that is a finding about the heuristic, report it).
>   Blind-ladder control cited (−98.26%, `EX-18`). **Tier/cost:** standard,
>   `-n 2`, one command; 3b-xviii's 457 s envelope covers two solves + the
>   gate set — `timeout -k 30 600`. **Traps:** standard list; do **not**
>   delete the heuristic path in-slot — deprecate behind a kwarg with the
>   old path reachable (the `prefer_interior` precedent) so the diff is
>   reviewable; `excitation.py`'s placeholder case is load-bearing for
>   other tests (grep before touching shared helpers). **Scope boundary:**
>   two-torus fixture only; no birdcage tags, no B1+; hold `PORT-1` at 🟡 —
>   if every gate is green through the package entry point the chunk's
>   done-when is plausibly met, but that flip is the reviewing session's
>   call, not the slot's. **Negative result:** report and park on
>   `attempt/*`; the heuristic stays the default until the gate is green.
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
>   closed form; h_far 0.02→0.03 moves it 0.09%) — *the two-point attribution
>   became a three-point trend in step 3b-xi, 2026-08-07: 4.7591% on the
>   projected drive, strictly monotone, 52.9× the h_far knob*. **The 10% mutual
>   tolerance is measurement-justified — do not tighten**: the filamentary reference itself
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
> build + `FEM_EM_REQUIRE_COMPLEX=1`; **and the 3b-iv lazy collective
> (added 2026-08-05, 18:00 review):** any facet integral over a subdomain
> some rank does not touch reaches `create_entity_permutations()` on only
> the ranks that own entities — this partition gives each rank exactly one
> port, so call `msh.topology.create_entity_permutations()` unconditionally
> on every rank before assembling any per-port form, exactly as
> `_facet_group_area` now does; if a `-n 2` command hangs, suspect this
> first, not the physics. **Does not close:** `PORT-1` —
> known-issues 3 and the touchstone threading come after; `Z₁₁` stays
> printed, never gated, on this fixture. **Negative result:** report
> `V/ωM` for both ports beside the shadow numbers at the same geometry,
> annotate this entry and known-issues 3, stop — the tolerance does not
> move, and a third estimator is a review's call, not a fourth box.
>
> **Step 3b-v attempted 2026-08-06 (19:30 run) — 🟡 negative result, taken as
> the plan's negative branch instructs.** The estimator is mechanically sound
> and physically wrong. Code parked on
> `attempt/PORT-1-step3bv-20260806T004500Z` (`49fa50e`); log on main,
> `20260806T003559Z_PORT-1-step3bv-gate.log` — **3 failed, 7 passed, 67.6 s**
> at `-n 2`, standard tier, 124 753 cells (mesh 24.8 s, solves 16.3 / 16.4 s).
>
> *The parallel half is fine.* No hang: `create_entity_permutations()` is
> hoisted unconditionally onto every rank before any per-port `dS` form,
> exactly as 3b-iv's fix prescribed, and the run completed first time. That
> hazard is now discharged twice on this fixture.
>
> *The measurement.* `V_i = −⟨E·ŷ⟩_{disc pair i, gap side} · L_gap`, with the
> restriction picked by a DG0 indicator of the gap tag (not `avg`, not an
> uncontrolled `('+')`), gives
>
> | estimator | `\|Im Z₁₂\|/ωM₁₂` | reciprocity |
> |---|---|---|
> | facet (this step), ports 1 / 2 | **4.845** (4.802 / 4.889) | 1.79e-2 |
> | full-box volume (3b-iii) | 0.332 | 1.15e-4 |
> | tube-shadow volume (3b-iii) | 0.763 / 0.814 | — |
>
> all three off **one** solve at one geometry, so the comparison is no longer
> across logs. The facet route does not land in the shadow's 0.687–0.814 band:
> it neither closes the ~0.78 deficit nor inherits it — it is a third and worse
> number, at +384.54% with `MUTUAL_TOLERANCE` unmoved. The open-port
> precondition (1.4162e-03) and the exact gap-box identity (1.000000000000)
> both still hold, so the fixture is not what moved.
>
> *Why, and this is the durable part.* `E·ŷ` on a conductor terminal is the
> facet-**normal** component — surface-charge-dominated and discontinuous by
> construction; the measured wire/gap jump ratio is 2.9e-5 to 4.6e-5, five
> orders. A two-endpoint trapezoid over a quantity that is *peaked at exactly
> those two endpoints* must overestimate, and 4.8× is the size of the peak. The
> volumetric shadow average, whatever its 22% deficit, at least integrates
> along the whole path. **Route 2 is therefore excluded on the same footing as
> the box family**: not a tuning failure, a category error about which
> component of `E` a terminal facet carries. A successor should integrate along
> the path (a line/tube integral inside the shadow with the *tangential*
> component), not sample its ends.
>
> *Second, independent finding — the fixture at small overhang.* At
> `gap_overhang = 2e-4` the tube protrudes **0.2018 mm** through the gap box's
> `−x` face over `2.821 mm < |y| < 3.989 mm` (arithmetic: box `min x` =
> 1.480000e-02, tube `min x` at `y = half_y` = 1.459821e-02), so facet tag
> `201`/`202` is the arc-end disc pair **plus two lateral strips**. Measured
> `1.643447371e-04 m²` per port, `1.0241 ×` 3b-iv's exact oblique cut
> `1.604721580e-04` — *above* it, where an inscribed linear-tet section must
> sit below. 3b-iv's anchor was measured at overhang 1e-3, where the tube
> clears the face by 0.598 mm; it does not transfer, and the band assertion
> this attempt inherited from it is wrong for this geometry rather than the
> mesh being wrong. Whoever revisits the fixture at small overhang owes it a
> geometry note: the "gap box contains the arc ends" invariant fails below
> overhang ≈ 6e-4. *(Recorded as known-issues 11 by the 2026-08-06, 03:00
> review.)*
>
> **Step 3b-vi — the tangential path-integral port voltage (plan written
> 2026-08-06, 03:00 review).** Two estimator families are now excluded by
> measurement on one solve: region averages (box: sign-unstable; tube shadow:
> stable 0.763–0.814 × ωM₁₂) and terminal-facet sampling (4.845 × — the facet
> carries the surface-charge-dominated *normal* component). What `−∫E·dl`
> literally is, and what neither route computed, is the integral of the
> **tangential** component along the gap path. Compute
> `V_i = −∫ E·t̂ dl` along the torus centerline arc through port i's gap,
> terminal to terminal: sample `E` at Gauss/trapezoid points on the arc of
> major radius `R` between the two disc planes via
> `post.evaluation.evaluate_vector_field_parallel` (never `f.eval`), dot with
> the analytic unit tangent, integrate. Two quadrature resolutions (e.g. 33
> and 65 points) off the same solve must agree to < 0.1% before the number is
> compared to anything — quadrature convergence is free, solve time is not.
> Reuse `test_port_gap_voltage_impedance.py` from
> `attempt/PORT-1-step3bv-20260806T004500Z` (the newest copy; it carries the
> `gap_burial`/`gap_overhang` split and the hoisted
> `create_entity_permutations()`) — do not rewrite it. Geometry: overhang
> 2e-4, so all four estimators sit on directly comparable solves; the path
> integral uses no facet tags, so known-issues 11's lateral strips do not
> enter the estimator — but do not gate anything on the 2xx facet areas at
> this overhang (that is known-issues 11). **Anchor:** `Im Z₁₂ = V₂/I₁`
> against `ωM₁₂ = 1.241755e+00 Ω` at the unmoved 10% `MUTUAL_TOLERANCE`;
> reciprocity and open-port preconditions at the measured scales (3b-v:
> open-port 1.4162e-03, gap-box identity 1.000000000000). **Negative
> controls:** on record, cite — box family +1.7210/−0.2391/+0.3317
> (sign-changing), facet 4.845/reciprocity 1.79e-2, shadow 0.763/0.814,
> unfragmented-mesh exact zero. The shadow's ~0.78 deficit is the number to
> close: landing inside 0.69–0.81 again means the deficit is not the sampling
> geometry at all — the next suspects are the field's own scale in the gap
> (finite-σ penetration at skin depth 1.125 r_wire; the PEC box already
> bounded at −9.35% by step 1's reaction route) or the `ωM₁₂` reference
> itself, and that adjudication is a review's, not this slot's. **Cost:**
> standard, `-n 2`, `timeout 180`; the 3b-v gate measured 67.6 s for mesh +
> two solves at 124 753 cells; point evaluation is seconds. One geometry.
> **Traps:** point evaluation near the gap/conductor interface can land in a
> cell on either side — keep interior quadrature points strictly inside the
> gap and handle the terminal endpoints explicitly (half-interval or offset);
> tangent-sign convention — fix the path orientation from the terminal
> ordering and print per-port `V` with its sign before asserting anything (a
> sign error here reproduces 3b-ii's symptom); complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`; hoisted `create_entity_permutations()` before
> any per-port `dS` form the reused file still assembles; stale FFCx lock;
> gap-wins piece policy; `gap_burial` strictly positive; pytest `-s`.
> **Does not close:** `PORT-1` — known-issues 3 and touchstone threading come
> after; `Z₁₁` stays printed, never gated, on this fixture. **Negative
> result:** report `V/ωM` for both ports beside the three prior numbers off
> the same solve, annotate this entry and known-issues 3, stop —
> `MUTUAL_TOLERANCE` does not move, and a fourth estimator family is a
> review's call.
>
> **Step 3b-vi attempted 2026-08-06 (04:30 implementer slot) — 🟡 negative
> result, parked on `attempt/PORT-1-step3bvi-20260806T094500Z` (`ee5f0cb`).**
> The path integral was built exactly as planned (Gauss–Legendre on the
> centreline arc, `evaluate_vector_field_parallel`, four estimators on one
> solve at `gap_overhang = 2e-4`, 124 753 cells, mesh 25.5 s + solves
> 16.4/16.0 s, 136 s at `-n 2`;
> `20260806T093808Z_PORT-1-step3bvi-quadrature-sweep-n2.log`). Two independent
> findings.
>
> *First — the value.* Mutual, off one solve, the four estimators now read:
>
>     path    0.468933 / 0.499728  x omega*M12   (3b-vi)
>     facet   4.801707 / 4.889116                (3b-v, excluded)
>     box     0.331729 / 0.331767                (3b-ii/iii, excluded)
>     shadow  0.763430 / 0.814325                (3b-iii)
>
> The path route does **not** close the ~0.78 deficit; it lands *below* the
> shadow family at ~0.48, a **third** distinct value, at −51.6% against the
> unmoved 10% `MUTUAL_TOLERANCE`, with reciprocity `|Z₁₂−Z₂₁|/|Z₁₂| = 6.3e-2`
> against the 1e-2 band. Four estimator families, four answers spanning a
> factor 15 on one solved field: the spread is now itself the evidence, and it
> says the disagreement is not in any one sampling geometry.
>
> *Second, and the reason this is parked rather than reported as a clean
> negative — the plan's own precondition fails.* The proposed `(33, 65)`
> quadrature pair disagrees by **1.07e-1**, two orders above the 1e-3 gate.
> Extending the sequence to 4097 nodes off the same solve measures the rate:
> 1.07e-1 (65), 1.07e-1 (129), 3.82e-2 (257), 5.23e-3 (513), 7.43e-3 (1025),
> 2.58e-3 (2049), 8.12e-4 (4097) — non-monotone, roughly `O(1/n)`, plateauing
> at ~1e-3…2e-3 and never reaching the precondition. This is structural, not a
> node count to raise: N1curl guarantees continuity of the **facet**-tangential
> component only, the arc's own tangent is not facet-tangential, so `E·t̂` jumps
> at every cell crossing, and with `h_wire = 2.5e-3` against arc length
> `a·g = 1.2e-2` only ~5 cells span the whole path. A line integral cannot be
> resolved to 0.1% through 5 elements of a discontinuous integrand at any node
> count. **The successor is mesh refinement along the arc, not more quadrature
> nodes** — and if the ~0.48 survives refinement, the estimator-family question
> is settled negatively and the next suspects are the ones the 3b-vi plan
> already named (finite-σ terminal penetration; the `ωM₁₂` reference itself).
>
> Preconditions that *do* hold, measured: all 4097 arc nodes located and every
> one in a **gap**-tagged cell at both ports (through the same
> `evaluate_vector_field_parallel` locate path the field sampling uses, on a
> DG0 `(gap, wire, air)` indicator); gap-box identity 1.000000000000;
> open-port 1.4162e-03 / 1.4129e-03. Carried forward onto the branch and
> re-applied to current `main`: the `gap_burial`/`gap_overhang` split of
> `two_torus_domain()`'s single `gap_clearance`. Incidental, for the review:
> `test_port_discs_are_the_arc_end_cut`'s per-disc `y`-split identity fails at
> 1.1e-8 against its 1e-9 tolerance — a facet-area sum over ~1e5 cells is not
> reproducible to 1e-9 between the two halves.
>
> **Step 3b-vii — the path integral on an arc-refined mesh (plan written
> 2026-08-06, 10:30 review; rescope of 3b-vi, which is parked *unresolved*,
> not refuted).** 3b-vi's quadrature plateau is a mesh property, not an
> estimator property: only ~5 cells of `h_wire = 2.5e-3` span the
> `a·g = 1.2e-2` gap arc, and `E·t̂` is discontinuous at every cell crossing
> (N1curl is facet-tangentially continuous only). Resolve the integrand, not
> the quadrature. Continue on `attempt/PORT-1-step3bvi-20260806T094500Z`
> (`ee5f0cb`) — the test file and the `gap_burial`/`gap_overhang` split live
> there, **not on `main`** — rebase or cherry-pick onto current `main` first
> (the branch base is `dcbd322`; `main` has moved by docs + `tests/post`/
> `tests/mesh` work only, so no conflict with `io/mesh.py` is expected).
> Add a gmsh `Distance` + `Threshold` size field per gap arc confining
> `h_gap ≈ 3e-4` (≥ 40 cells across the arc) to a tube of radius ~2 `h_wire`
> around the arc; `h_wire` elsewhere and `resolution_far` stay put. Re-run the
> same four-estimator sweep off one solve per drive. **Precondition (3b-vi's
> gate, now attainable):** successive quadrature orders (129, 257) agree
> < 1e-3 before any comparison — with ~40 cells the observed `O(1/n)` plateau
> scales to ~2e-4, so the gate is reachable, and a plateau that does *not*
> fall with refinement is itself a finding (the integrand is rougher than the
> element-crossing model says). **Anchor:** unchanged — `Im Z₁₂ = V₂/I₁` vs
> `ωM₁₂ = 1.241755e+00 Ω` at the unmoved 10% `MUTUAL_TOLERANCE`; reciprocity
> 1e-2; open-port and gap-box preconditions at their measured scales.
> **Negative controls:** on record — the four-family table off the unrefined
> solve (path 0.4689/0.4997, facet 4.80/4.89, box 0.3317, shadow
> 0.763/0.814 × ωM₁₂); the unfragmented-mesh exact zero. The shadow and box
> numbers re-read off the *refined* solve are a built-in control: they do not
> sample the arc, so they should move only at discretization level (a few %) —
> a large shift there means the solve changed, not the estimator. **Cost:**
> probe first. 3b-vi measured mesh 25.5 s + 16 s/solve at 124 753 cells,
> 136 s total at `-n 2`; the refinement tube is ~π(1.25 h_wire)²·(arc) per
> port, estimated ≤ 1.5–2× the cell count. Probe mesh + one solve at `-n 2`,
> `timeout 600` (standard work, declared above tier for the probe only); if
> mesh + two solves projects > 300 s, drop to `h_gap = 6e-4` (~20 cells) —
> never raise the timeout further. Gates `-n 2`. **Traps:** all of 3b-vi's
> (Legendre interior nodes so terminals are never sampled; tangent sign
> printed per port before asserting; complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`; hoisted `create_entity_permutations()` before
> any per-port `dS` form; stale FFCx lock after a killed run; pytest `-s`;
> known-issues 11 — never gate on the 2xx facet areas at overhang 2e-4) plus
> two of its own: the size field must act on the **fragmented** model —
> define it by coordinates (arc centreline distance), not by pre-fragment
> entity tags, and set it after `occ.fragment`/`synchronize`; and the
> branch's `test_port_discs_are_the_arc_end_cut` per-disc `y`-split identity
> is measured at 1.1e-8 vs its 1e-9 tolerance — if that file lands on `main`,
> set that tolerance from the measurement (facet-area sums over ~1e5 cells),
> never assume 1e-9. **Does not close:** `PORT-1`; `Z₁₁` stays printed, never
> gated, on this fixture. **Negative result:** if the *converged* path V
> still reads ~0.48 × ωM₁₂, the estimator-family question is settled
> negatively — four sampling geometries, four answers off one field — and the
> remaining suspects (finite-σ terminal penetration at `δ = 1.125 r_wire`;
> the filamentary `ωM₁₂` reference itself) are the next review's
> adjudication, not this slot's: report all four numbers off the refined
> solve, annotate this entry and known-issues 3, park the branch, stop —
> `MUTUAL_TOLERANCE` does not move.
>
> **Step 3b-vii attempted 2026-08-06 (12:00 implementer slot) — 🟡 the
> plan's negative result, parked on
> `attempt/PORT-1-step3bvii-20260806T170000Z` (`bc8c04e`).** The refinement
> was built as planned and *worked as a mesh change*; the value did not move.
>
> `two_torus_domain` gained `gap_arc_resolution` / `gap_arc_tube_radius`: a
> `MathEval` distance-to-the-gap-arc field (distance to the centreline circle
> plus `max(0,|y|−a sin(g/2))` and `max(0,−x)` penalties, both spelled with
> `sqrt` so the expression needs no `fabs`/`max` from gmsh's parser),
> `Threshold`-ramped at slope 0.3 and `Min`-composed with the existing wire
> grading — coordinate-defined on the *fragmented* model, per the trap.
> Measured cost before the gate
> (`20260806T170559Z_PORT-1-step3bvii-probe.log`): 124 753 → 178 055 cells
> (1.427×), mesh 29.2 → 41.4 s, gap-tagged cells 1569 → 24 430 per port, i.e.
> the arc is genuinely resolved at 40 cells across `a·g`. The gate
> (`20260806T170835Z_PORT-1-step3bvii-gate-n2.log`, 165 s at `-n 2`, 10 passed
> 2 failed; mesh 37.4 s, solves 22.9/22.1 s) then split cleanly in two.
>
> *What refinement fixed.* Reciprocity `|Z₁₂−Z₂₁|/|Z₁₂|` went **6.3e-2 →
> 3.8823e-3**, inside the 1e-2 band for the first time on this estimator. The
> quadrature residual at fixed order improved ~3× (129→257 now 1.14e-2 against
> 3b-vi's 3.82e-2). Both are what a resolved integrand should do.
>
> *What it did not fix — and this is the finding.* The precondition still
> fails: (129, 257) disagree by **1.1444e-2**, an order above the 1e-3 gate,
> and the high-order plateau is essentially where 3b-vi left it (5.96e-4 at
> 2049, 8.76e-4 at 4097 vs 2.58e-4/8.12e-4). More importantly the **converged
> value is unchanged**: path `V` reads **0.493653 / 0.491744 × ωM₁₂** at order
> 257 (and 0.4808 at 4097) against 3b-vi's 0.468933 / 0.499728 — a shift of a
> few percent, i.e. discretization level. `Im Z₁₂` is −50.73% against the
> unmoved 10% `MUTUAL_TOLERANCE`.
>
> *The built-in control passed, which is what makes the negative clean.* All
> four families re-read off the refined solve moved only at discretization
> level, so the solve did not change underneath the estimator:
>
>     family   refined (3b-vii)      unrefined (3b-vi)
>     path     0.493653 / 0.491744   0.468933 / 0.499728
>     facet    5.164602 / 5.168622   4.801707 / 4.889116
>     box      0.349567 / 0.349227   0.331729 / 0.331767
>     shadow   0.856617 / 0.838592   0.763430 / 0.814325
>
> Preconditions that hold: gap boxes meshed/analytic 1.000000000000, every arc
> node located in a gap-tagged cell, open-port 1.4062e-03.
>
> **So the estimator-family question is settled negatively, exactly as this
> plan defined it**: four sampling geometries, four answers off one field,
> and the ~0.48 survives a 1.43× refinement that fixed reciprocity. The
> deficit is not the sampling geometry. The remaining suspects are the two
> 3b-vi already named — finite-σ terminal penetration at `δ = 1.125 r_wire`,
> and the filamentary `ωM₁₂` reference itself — and adjudicating between them
> is a review's call, not an implementer slot's. Incidental, for the review:
> the per-disc `y`-split tolerance was set from 3b-vi's 1.1e-8 measurement to
> 1e-7 on the branch (two independent ~1e5-cell facet-area sums have a float
> floor there; a misassigned split is O(1)).
>
> **Adjudication (2026-08-06, 18:00 review) — the two suspects are not
> equals, and the review ranks them opposite to their cost.** The
> filamentary-reference suspect is already *bounded*: step 2's reaction
> route measured `Im Z₁₂` at **−9.35%** of the same filamentary `ωM₁₂` on
> the ungapped pair, and step 2c's box-sensitivity sweep attributes
> **−9.36%** to the PEC wall at padding 0.08 — an independent field-level
> estimator agrees with the filamentary closed form to within the box
> effect. A finite-cross-section correction at `r/a = 0.125` is
> percent-scale; it cannot produce 0.49. It is still queued **first**
> (step 3b-viii) because it is free — no solve — and retires the suspect
> cleanly. The stronger suspect is finite-σ terminal penetration, and it
> has a mechanism with a measurable signature: `−∮E·dl` around the closed
> centreline loop equals the EMF `−iωΦ ≈ ωM₁₂I₁`, so the gap voltage
> differs from the EMF by exactly the tangential-`E` integral through the
> **wire interior** — and at `δ = 1.125 r_wire` the centreline runs deep
> inside a conductor whose eddy response makes that interior term O(1),
> not a correction. Both the decomposition (off one solve) and the σ
> scaling (V_gap → EMF as σ → PEC) are measurable in one slot — step
> 3b-ix. If *both* suspects fall, the question escalates from "which
> estimator" to "what quantity a gap port should report", and that is a
> weekly-review-grade rescope of known-issues 3, not another slot.
>
> **Step 3b-viii — audit the `ωM₁₂` reference in closed form (plan written
> 2026-08-06, 18:00 review; no solve, no mesh).** Pure-Python/scipy, smoke
> tier. (1) Reimplement the coaxial-filament mutual inductance
> independently via the elliptic-integral form `M = μ₀√(ab)·[(2/k −
> k)K(k) − (2/k)E(k)]`, `k² = 4ab/((a+b)² + d²)`, and assert it matches
> the existing `mutual_inductance(a, a, d)` in
> `tests/validation/test_port_reaction_impedance.py` (vector-potential
> route) to **< 1e-9 relative** — two independent derivations of one
> closed form. (2) Compute the finite-cross-section correction: average
> the filament kernel over both minor discs at `r/a = 0.125` (2-D Gauss
> quadrature per disc, uniform current density — the δ ≈ r near-uniform
> limit; state the assumption), converged **< 1e-6** between successive
> quadrature orders, and report `M_tube/M_fil`. **Anchor:** the two-route
> filament identity plus the converged tube/filament ratio. **Negative
> control / ceiling:** the reaction route's −9.35% (≈ −9.36% box effect)
> bounds any legitimate correction at ~10% — a computed "correction"
> approaching 0.49's factor 2 means the *calculation* is wrong, not the
> reference; the expected result is percent-scale, which retires the
> suspect. **Cost:** smoke, `-n 1`, seconds; real build is fine (no FEM).
> **Traps:** `scipy.special.ellipk/ellipe` take the parameter `m = k²`,
> not the modulus `k`; the internal-inductance `μ₀/8π` term belongs to
> *self*-inductance, never mutual — do not add it; take `(a, r_wire, d)`
> from the fixture constants on the branch, not from memory; the gapped
> fixture's wedge is `2π − g`, not `2π` — decide and state whether the
> reference should be the full-loop `M` (as the landed tests use) before
> comparing. **Does not close:** `PORT-1`, known-issues 3; this
> adjudicates one suspect. **Negative result:** a percent-scale ratio is
> the *expected* outcome and is still the deliverable — record it in this
> entry and known-issues 3's progress table; a large ratio means stop and
> report (it would contradict the reaction-route agreement, and that
> contradiction is the finding).
>
> **Step 3b-viii is ✅ 2026-08-07 (21:00 slot) — the reference is exonerated,
> and the expected negative is the deliverable.**
> `tests/validation/test_mutual_inductance_reference.py`, on `main`, green:
> 7 passed in **0.43 s** at `-n 1`, smoke tier, real build, no solve and no
> mesh (log `20260807T020314Z_PORT-1-step3bviii-gate.log`; the identical
> pre-control run is `20260807T020243Z_PORT-1-step3bviii-probe.log`, 6 passed
> in 1.56 s before the vacuity control was added).
>
> 1. **Two routes, one closed form.** The vector-potential route every
>    `PORT-1` gate uses (`mutual_inductance` → `circular_loop_vector_potential`)
>    and an independent elliptic-integral reimplementation of Maxwell's
>    formula agree to **1.507e-15** relative at the fixture's `(a, d) =
>    (0.04, 0.04)`, and to 1.02e-15 / 1.75e-16 / 7.46e-14 at `2d`, `d/4`, `4d`
>    — round-off in two different transcendental evaluations, against a 1e-9
>    gate. `ω·M_elliptic = 1.241755 Ω` reproduces the value printed by the
>    step-1 box-sensitivity log to 3.1e-7.
> 2. **The 1e-9 identity is not vacuous.** The plan named SciPy's `m = k²`
>    convention as the likeliest way to get a silently-wrong reference, so
>    that mistake is now a *control*: passing the modulus where the parameter
>    belongs gives `4.746063e-08 H` against the correct `1.976314e-08 H`, a
>    **140%** error — eleven orders above the gate that would have to catch it.
> 3. **The finite-cross-section correction is 0.481%, and it has the wrong
>    sign.** Averaging the filament kernel over both minor discs at uniform
>    current density (Gauss–Legendre in the minor radius × periodic trapezoid
>    in the minor angle; the discs are `d = 8·r_wire` apart, so the integrand
>    is smooth) gives `M_tube = 1.985819906053e-08 H` against
>    `M_fil = 1.976313852319e-08 H`, i.e. **`M_tube/M_fil = 1.004809992`**,
>    converged to **6.7e-16** between the last two quadrature orders (deltas
>    7.61e-09 → 8.90e-13 → 6.67e-16 over (4,8) … (10,20)). `ωM_tube =
>    1.247727 Ω`. Uniform current density is the stated assumption (the
>    `δ ≳ r` limit; the fixture sits at `δ = 1.125 r_wire`, its edge), and a
>    skin-concentrated distribution would spread the current *further* out,
>    not less, so 0.481% is not an accidental floor.
>
> **What this settles.** The correction is percent-scale exactly as the
> ceiling predicted, and it is *positive*: a corrected reference makes the
> gap-voltage deficit marginally **worse**, 0.4937/0.4917 → 0.4914/0.4894 ×
> ωM. Two independent facts now agree that the filamentary reference is
> sound — this calculation, and step 2's field-level `Im Z₁₂` at −9.35% with
> −9.36% attributable to the PEC box. **The reference suspect is retired**,
> and finite-σ terminal penetration (step 3b-ix) is the only named suspect
> left for the factor 2. Recorded in known-issues 3's progress table.
> `MUTUAL_TOLERANCE` unmoved; nothing under `src/` changed.
>
> **Step 3b-ix — the missing half is in the wire: loop-closure
> decomposition + σ scaling (plan written 2026-08-06, 18:00 review).**
> Continue on `attempt/PORT-1-step3bvii-20260806T170000Z` (`bc8c04e`) —
> the refined mesh and the four-estimator harness live there;
> cherry-pick onto current `main` first (only docs moved since; no code
> conflict expected). Two measurements, one geometry. (1) **Decomposition,
> off one solve** (the σ×1 solve, on record at 165 s for the full gate):
> extend the path integral around the *wire interior* centreline arc
> (the `2π − g` complement; ~100 cells of `h_wire` across `2πa ≈ 0.25 m`)
> and report `V_wire = −∫_wire E·t̂ dl` beside the recorded
> `V_gap = 0.4937/0.4917 × ωM₁₂`. Quadrature precondition: successive
> orders (513, 1025) on the wire arc agree **< 1e-2** before any
> comparison — the integrand crosses ~100 cells, not 3b-vi's 5, but it is
> still discontinuous; a plateau above 1e-2 is reportable, not padding to
> raise. The loop-closure sum `(V_gap + V_wire)/ωM₁₂` should land within
> ~10–15% of 1 (the reference's own bound plus discretization) **if**
> penetration is the mechanism — print all three numbers per port before
> asserting anything. (2) **σ scaling, two more solves on the same mesh:**
> `σ_wire × {2, 4}` (δ/r_wire: 1.125 → 0.795 → 0.563), report
> `V_gap/ωM₁₂` at each — monotone rise toward 1 is the mechanism's
> signature; the recorded 0.49 at σ×1 is the negative control. **Do not
> exceed σ×4:** at σ×16, δ = 1.4e-3 < h_wire = 2.5e-3 and the skin layer
> is unresolved — the point would be noise, and that ceiling is stated
> here so the slot does not buy it. **Anchor:** the loop-closure identity
> and the monotone σ trend, both quantitative, both off the existing
> harness. **Cost:** standard, `-n 2`, `timeout 600`; mesh 37 s + ~23 s
> per solve on record at 178 055 cells → three solves ≈ 110 s plus
> evaluation. **Traps:** all of 3b-vii's (complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`; hoisted `create_entity_permutations()`;
> FFCx lock; pytest `-s`; Legendre interior nodes); the wire-arc nodes
> must verify against the DG0 indicator as *wire*-tagged (3b-vi's gap
> check, inverted); find where `σ_wire` is actually set before sweeping
> it (fixture constant vs material table); `E = J/σ` inside the conductor
> is small per-cell but the arc is long — do not assume it negligible,
> that assumption is the thing under test; `MUTUAL_TOLERANCE` does not
> move. **Does not close:** `PORT-1`; `Z₁₁` stays printed, never gated.
> **Independent of 3b-viii landing** — and 3b-viii has now landed
> (2026-08-07): the reference is exonerated at +0.481%, so no rescaling of
> the `× ωM₁₂` ratios below is warranted and none should be applied; this
> step now carries the *only* surviving named suspect.
> **Negative result:** if `V_wire` is small *and* `V_gap` is σ-flat, both
> named suspects are dead — report all numbers, annotate this entry and
> known-issues 3, park on the branch, stop; the follow-up (what quantity
> a gap port should report) is the next weekly review's, per the
> adjudication above.
>
> **Step 3b-ix is 🟡 2026-08-07 (00:00 slot) — the loop closes, both named
> suspects are dead, and the factor 2 turns out to be the estimator's
> integration limits.** Parked on
> `attempt/PORT-1-step3bix-20260807T050000Z` (`6caec85`; 3b-vi/3b-vii
> cherry-picked forward onto `38d189d`). One mesh, 178 055 cells, `-n 2`,
> `timeout 600`, **227 s** — `20260807T050654Z_PORT-1-step3bix-gate-n2.log`
> on the branch (collection probe `20260807T050637Z_...-collect.log`, 4 s).
>
> 1. **The plan's two-piece tiling is a three-piece tiling.** `GAP_BURIAL`
>    makes the dielectric wider than the nominal wedge: the box spans
>    `|y| ≤ half_y` and the centreline has `y = a sin φ`, so the gap region
>    reaches `±arcsin(half_y/a) = ±0.175335` rad against the wedge's `±0.15`.
>    The two **buried** segments — 1.013 mm of arc each — are gap-tagged, and
>    omitting them would have left a hole in the "closed" loop. All four
>    segments' nodes verified wire-/gap-tagged against the DG0 indicator
>    before any solve: 0 misassigned of 5392.
> 2. **The closure identity holds.** Undriven port, gap 101 / gap 102 driven:
>    `V_gap = 0.493653 / 0.491744` (3b-vii's estimator, reproduced),
>    **`V_buried = 0.399972 / 0.402239`**, `V_wire = 0.002394 / 0.002316`,
>    **sum = 0.896019 / 0.896299 × ωM₁₂** — inside the pre-set `1 ± 0.15`
>    band, and at −10.40%/−10.37% against step 2's independent reaction-route
>    `Im Z₁₂` at −9.35% with −9.36% attributed to the PEC box at padding 0.08.
> 3. **σ scaling is the plan's declared negative.** At `σ × {1, 2, 4}`
>    (δ/r_wire 1.125 → 0.796 → 0.563; σ moved in both the material map and
>    the `I = σ⟨E·φ̂⟩A` reconstruction), `V_gap/ωM` = 0.493653 → 0.490837 →
>    0.485059 — it **falls**. `V_wire/ωM` = 0.002394 → 0.001856 → 0.000727:
>    the penetration signature is real and is 200× too small to matter.
>    Undriven port open at every scale (2.1e-3, 3.2e-3 < 1e-2, gated).
>
> **What this settles.** The factor 2 is not physics. `_gap_arc_quadrature`
> integrates the *nominal* wedge while the terminals — the
> conductor/dielectric cut that tags 201/202 already mark — sit at
> `±arcsin(half_y/a)`. That 0.8% of the loop's length carries 45% of its
> EMF, because it is exactly where the terminal fields are. **Terminal to
> terminal the gap-port voltage is 0.8936 × ωM₁₂, not 0.4937.** With
> 3b-viii's +0.481% the reference suspect was already retired; penetration is
> retired here; the estimator's limits are the cause, measured.
>
> **Two gates fail and are deliberately left failing.**
> `test_gap_voltage_rises_monotonically_toward_the_emf_with_sigma` asserts the
> penetration signature the plan predicted — it fails because the prediction
> is wrong, and that failure is the deliverable.
> `test_wire_arc_quadrature_is_converged` reaches 2.01e-2 against the plan's
> 1e-2 on the *undriven* port only (driven port 5.7e-4 / 1.7e-4): a relative
> tolerance on a term worth 0.24% of the loop, absolute stake 5e-5 × ωM.
> Neither bound was moved, and `MUTUAL_TOLERANCE` is unmoved at 0.10; nothing
> under `src/` changed.
>
> **Step 3b-x — terminal-to-terminal limits for `_gap_arc_quadrature`; land
> the branch** *(scoped 2026-08-07, 03:00 review; §9 item 1; works on
> `attempt/PORT-1-step3bix-20260807T050000Z`, `6caec85`)*. One change of
> substance: the gap-voltage estimator integrates terminal to terminal — the
> meshed dielectric extent — not the nominal wedge. Derive the limits from
> the geometry the mesh actually carries: read the terminal angles off the
> port facet tags (201/202) and assert they match `±arcsin(half_y/a) =
> ±0.175335` rad to 1e-6 *before* any solve, so the limits cannot drift from
> the geometry (`GAP_BURIAL` is the on-record cause, 3b-ix). Then one σ×1
> solve per drive on the same 178 055-cell mesh. **Anchor, both halves
> pre-sized:** (1) the retiling identity — the corrected `V_gap` must equal
> 3b-ix's wedge + buried segment sum off the same field (0.893625 /
> 0.893983 × ωM₁₂ on record) to < 1e-3 relative: same integrand, same
> field, different tiling; (2) estimator-vs-reaction consistency — compute
> the reaction-route `Im Z₁₂` on *this gapped fixture* with the landed
> step-1/2 machinery and gate the corrected gap-voltage mutual against it
> at ≤ 3% (the closure sum sits −10.4% vs the ungapped reaction route's
> −9.35%, ~1.2 pp apart; 3% leaves room for the gapped/ungapped
> difference). **Negative control:** on record — the wedge-only estimator
> at 0.4937 × ωM₁₂ is ~45% off the reaction route, 15× the bound.
> **Gate dispositions, decided by this review so the slot does not
> improvise:** (i) the ωM₁₂ closed-form comparison stays *printed* in the
> log and tracked by known-issues 3, expected at ~−10.6% — outside
> `MUTUAL_TOLERANCE = 0.10` by 0.6 pp; the *assertion* moves to the
> same-fixture reaction route per anchor (2). That is a re-anchoring
> recorded here, not an in-slot loosening: no tolerance moves, and whether
> the −10.6% is the PEC box is 3b-xi's question. (ii)
> `test_gap_voltage_rises_monotonically_toward_the_emf_with_sigma` asserts
> a prediction 3b-ix measured to be false (`V_gap` *falls*, 0.493653 →
> 0.485059) — delete it; the σ-sweep record lives in the 3b-ix log and
> attempts entry. A hypothesis test that returned its negative is
> finished, not red. (iii) `test_wire_arc_quadrature_is_converged`: keep
> the 1e-2 bound, gate the driven port (5.7e-4 / 1.7e-4 on record), print
> the undriven (2.01e-2 — a relative bound on a term worth 0.24% of the
> loop; absolute stake 5e-5 × ωM), and record the split in the docstring.
> **Landing:** all gates green at `-n 2` ⇒ land the branch lineage
> (3b-vi → 3b-x: test file, probe, logs) onto `main` in one commit and
> delete the branch; anything red beyond the expectations above ⇒ park and
> report. **Cost:** standard, `-n 2`, `timeout 600` — mesh 37 s +
> ~23 s/solve × 2 drives (~150 s; 3b-ix's full run was 227 s with three σ
> solves). **Traps:** all of 3b-vii/3b-ix's (FFCx lock after a kill,
> pytest `-s`, DG0 node verification before any solve, complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first); the buried
> segments are **gap-tagged, not wire-tagged**; if step-2 reaction
> machinery is reused, mind the `‖Z‖` normalisation note (step 2's audit).
> **Does not close:** `PORT-1` or known-issues 3 — the ωM residual
> adjudication is 3b-xi's. **Negative result:** a failed retiling identity
> means the new limits read the wrong tags — report the measured terminal
> angles against ±0.175335 and stop; a reaction-route disagreement > 3% on
> the same solve is a genuine estimator defect that 3b-ix's closure could
> not see — park, report, do not tune.
>
> **Step 3b-x is 🟡 2026-08-07 (04:30 slot) — the correction works and is
> gated; the plan's second anchor turns out not to exist on this fixture.**
> Parked on `attempt/PORT-1-step3bx-20260807T095500Z` (`5a5980b`; 3b-vi →
> 3b-ix rebased onto `e814fa2`, then this step on top). One mesh, 178 055
> cells, `-n 2`, `timeout 600`, **271.8 s, all 19 gates green** —
> `20260807T094728Z_PORT-1-step3bx-gate2-n2.log`.
>
> 1. **Terminal to terminal, gated to the mesh.** The estimator integrates
>    `(−φ_term, +φ_term)`, `φ_term = arcsin(half_y/a)`, and the fixture reads
>    the terminals off the 201/202 facet tags and raises before any solve on a
>    ≥ 1e-6 mismatch: measured **5.6e-17 / 2.8e-16 rad** on all four. The
>    gate's first form used the area-weighted `⟨y⟩` and measured 1.48e-3
>    short — that is **known-issues 11** (lateral strips in the tag at
>    `gap_overhang = 2e-4`), so the gated quantity is the interface's extreme
>    reach and the contaminated mean is printed beside it.
> 2. **The corrected port voltage is 0.894543 / 0.894022 × ωM₁₂**, against
>    0.4937 wedge-limited. The retiling identity (anchor 1) holds at
>    **2.67e-4 / 2.29e-4** against 1e-3, and 3b-ix's decomposition reproduces
>    bit for bit — only the limits moved. Against the closed form the mutual
>    is **−10.57%**, printed and known-issues-3-tracked as this entry
>    pre-decided.
> 3. **Quadrature resolved, not relaxed.** `PATH_QUADRATURE_GATE_ORDERS`
>    129/257 → 2049/4097 (the wider span adds the buried end zones; the sweep
>    runs 2.99e-3 → 3.91e-4 across 129 → 4097). `PATH_QUADRATURE_TOLERANCE`
>    and `MUTUAL_TOLERANCE` are unmoved; the closure segments keep 3b-ix's
>    orders. Newly print-only, on the standing "`Z₁₁` stays printed" rule:
>    the **driven** diagonal's path integral does not converge at all under
>    the new limits (2.3e-2 at 4097) — its path crosses the impressed
>    source's own terminals. The mutual is the undriven port throughout.
> 4. **Why it is parked.** Anchor (2) executed literally reads
>    `4.5376e-3 Ω` against the estimator's `1.1108 Ω`, a factor 244, and the
>    cause is that the landed reaction route drives an impressed current in a
>    **non-conducting closed** torus while this fixture's test region is a
>    **σ = 800 S/m arc of an open loop** — so `−∫E·J₂` returns the ohmic
>    `V_wire` term (0.003654 vs 3b-ix's 0.002394 × ωM₁₂), not the mutual.
>    Not an estimator defect and not tunable: the anchor needs a control solve
>    the slot did not buy (σ = 0 on the wire tags, impressed azimuthal drive
>    in wire 1, `project_source` per step 2f), ≈ 25 s on the same mesh. Step
>    **3b-x-b** is that solve plus the ≤ 3% gate, and it lands the branch.
>    `REACTION_CONSISTENCY_TOLERANCE = 0.03` is unmoved and ungated;
>    nothing under `src/` changed.
>
> **Step 3b-x-b is 🟡 2026-08-07 (06:00 slot) — the control exists and the
> anchor is now computable; the estimator misses the bound by 0.02 pp.**
> Parked on `attempt/PORT-1-step3bxb-20260807T111036Z` (on top of the 3b-x
> branch). `-n 2`, `timeout 600`, standard tier, **298.6 s, 19 passed +
> the new gate red** — `20260807T110513Z_PORT-1-step3bxb-gate-n2.log`.
> Nothing under `src/` changed; no tolerance moved.
>
> 1. **The control.** Same 178 055-cell gapped mesh, `material_map=None`
>    (σ = 0 everywhere), impressed azimuthal current over loop 1's **wire +
>    gap footprint** — the union, so the source is a closed loop rather than
>    the open arc 3b-x's hypothesis worried about — and `project_source` at
>    step 2f's default. One extra solve, **25.4 s**. `I'/I_prescribed =
>    0.998295`, projection `imag_ratio = 0`. Both currents use the landed
>    route's own normalisation `I = ∫J·φ̂ dV/(2πa)`.
> 2. **The reference: `Im Z₂₁ = +1.145422659 Ω = 0.922423 × ωM₁₂`**
>    (−7.76% vs the closed form; the *ungapped* reaction route sits at
>    −9.35%, so the box residual is not identical between the two meshes).
>    `Re Z₂₁ = 0` exactly, as an impressed-current mutual in a lossless
>    domain must be. The normalisation's one assumption — that `E·φ̂` is
>    azimuthally uniform, so an arc mean times `2πa` is the loop EMF — is
>    **measured, not assumed**: the same integral over the wire tag alone
>    (94.4% of the loop) reads 0.918372, **0.44% apart**.
> 3. **The gate, red at 3.0224%.** Corrected estimator 0.894543 vs control
>    0.922423 ⇒ ratio **0.969776**, deviation **−3.0224e-02** against
>    `REACTION_CONSISTENCY_TOLERANCE = 0.03`. Same number on both driven
>    columns. The negative control is in the same log and works as sized:
>    the wedge-only estimator would give ratio 0.5352, 46% off, 15× the
>    bound. So the two independent routes — a volume reaction integral over
>    conductor 2 and a terminal-to-terminal line integral of `E·φ̂` —
>    **agree to 3.0%**, and the pre-decided bound is 3.0%.
> 4. **Not tuned, and the adjudication is the review's.** The bound was
>    sized at 3% for a ~1.2 pp gapped/ungapped spread (−10.4% vs −9.35%);
>    the control measures that spread at **2.8 pp** (−10.57% vs −7.76%)
>    instead, so the premise the bound was sized from is what the
>    measurement contradicts, not the estimator. Moving it in-slot is
>    exactly the loosening the rules forbid. Two dispositions are open and
>    both are one review decision: (a) re-size the bound *with* the measured
>    gapped/ungapped spread recorded, per the MAG-10/MAG-15 precedent; or
>    (b) treat the 2.8 pp as physics to be explained first — the control's
>    closed non-conducting loop and the production gapped σ = 800 S/m loop
>    are different problems in the same box, and 3b-xi's padding sweep bears
>    directly on it. *(Adjudicated 2026-08-07, 10:30 review: neither picked
>    blind — step 3b-xii below buys the discriminating measurement and
>    pre-decides both outcomes; (a)'s re-size to 5% is authorized there iff
>    the routes converge under box enlargement.)*
>
> * **Step 3b-xi — the PEC-box padding sweep** ✅ *(scoped 2026-08-07 03:00
>   review, executed 2026-08-07 07:30 run; `§9 item 2`;
>   `tests/validation/test_port_box_padding_sweep.py`, 7 passed 153.7 s
>   heavy-declared/standard-actual, `20260807T124038Z_PORT-1-step3bxi-gate.log`;
>   mesh probe `20260807T123435Z_PORT-1-step3bxi-probe.log`, 57 s)*.
>   **The box attribution is now a trend, not a point, and it holds.** Every
>   `PORT-1` step since step 1 has charged the residual `Im Z₁₂` deficit to the
>   PEC truncation box on the strength of two measurements (padding 0.08 → 0.12
>   moving it 5.20%; h_far 0.02 → 0.03 moving it 0.09%). The ungapped pair at
>   `d = 0.04`, h_far 0.03, **projected drive**, one solve per padding
>   (`Z₂₁` only — reciprocity is 3.06e-13 here, step 2c's trade):
>
>   | air padding | `Im Z₂₁` | `Im Z₁₂/ωM₁₂` | deficit |
>   |---|---|---|---|
>   | 0.08 m | +1.142011 Ω | 0.919676 | **−8.0324%** |
>   | 0.10 m | +1.179349 Ω | 0.949744 | **−5.0256%** |
>   | 0.12 m | +1.201108 Ω | 0.967267 | **−3.2733%** |
>
>   All three gates green, none tuned: (i) padding 0.08 reproduces step 2f's
>   landed **−8.03%** to `2.44e-05` — the sweep is on the fixture the
>   attribution was made on, and the other two boxes differ only in the wall;
>   (ii) `|deficit|` is **strictly decreasing**, 8.0324% > 5.0256% > 3.2733%,
>   and every deficit is negative, which is the sign a PEC wall must produce
>   (it shorts out the field it truncates, so it can only remove flux from the
>   pickup loop); (iii) the 0.08 → 0.12 move is **4.7591%**, inside the
>   pre-decided 3–7% band around step 1's 5.20% — measured on the projected
>   drive where step 1's was unprojected — and **52.9×** the h_far control's
>   0.09% on the same fixture, so mesh and box are cleanly separated knobs.
>   Cost was probed mesh-only first as the plan required: 119 738 / 135 542 /
>   154 493 cells (both end points byte-reproducing their logged counts;
>   padding 0.10 had never been meshed at this h_far), all well under the
>   250 000-cell line where padding 0.12 / h_far 0.02 once died in MUMPS.
>   **What this licenses:** 3b-x's corrected terminal-to-terminal port voltage
>   at ~−10.6% now has a *named, measured* owner rather than an asserted one,
>   and 3b-x-b's open adjudication gains a datum — the box is worth ~4.8 pp of
>   deficit over this padding range, comfortably more than the 2.8 pp
>   gapped/ungapped spread that the 3% bound's premise stumbled on, so
>   disposition (b) ("explain the 2.8 pp first") is not blocked on an unknown
>   mechanism. **What it does not do:** no extrapolation to a converged answer
>   (three paddings inside a factor 1.5 cannot support a Richardson fit, and
>   none was attempted — the claim is directional); `MUTUAL_TOLERANCE`
>   untouched at 10%, as the plan required regardless of outcome; known-issues
>   3 unchanged; no symbol flips.
>
>   **Decision-(4) padding fit — the box term as a number, and why it must be
>   quoted with its exponent** ✅ *(2026-08-12, 16:30 run;
>   `scripts/probes/port1_padding_fit.py`,
>   `20260812T213337Z_PORT-1-dec4-fit.log`, exit 0, 1 s, smoke, `-n 1`,
>   zero-solve — no mesh, no solve, no complex mode, nothing under `src/`)*.
>   The operator adjudication's decision (4) commissioned `MAT-6` step 9's
>   free-exponent form on the three rungs above so the port-pair gate could
>   state the box term as a number. It now can, and **both pre-registered
>   gates pass** — but the number's honest error bar is set by the model, not
>   the data, and that is this step's real content.
>
>   | quantity | value |
>   |---|---|
>   | `D∞` (free exponent) | **+1.6934 pp** |
>   | `C` | −1.478719e-01 pp·mᵖ |
>   | `p` (recovered, not given) | **1.6574** |
>   | `D∞` conditioning, half-ulp on all three rungs | [+1.6915, +1.6953] pp (span **0.0037 pp**) |
>   | `D∞` with `p` pinned at the dipolar 3.0 | **−1.4291 pp** (max residual 0.1864 pp) |
>
>   **Three findings.** (i) **The extrapolation crosses zero.** All three
>   measured rungs are negative deficits and `C < 0` — the sign 3b-xi argued a
>   PEC wall must produce — but the endpoint is *positive*: box-free, the fit
>   says +1.69 pp of **excess**, not zero. Read literally, the box owns 9.73 pp
>   at `W = 0.08`, more than the whole −8.03 pp measured there, and something
>   of the opposite sign owns the remainder. (ii) **The exponent is not
>   dipolar.** `p = 1.657` against `MAT-6` step 9's blind **3.045** and the
>   dipolar **3** — step 9's fixture recovered the physics it was never given;
>   this one does not. (iii) **Model uncertainty dominates data uncertainty by
>   ~840×.** The recorded digits move `D∞` by 0.0037 pp; the *choice of
>   exponent* moves it by **3.1225 pp, across zero** (+1.6934 → −1.4291). The
>   pinned-`p = 3` fit's 0.1864 pp max residual is 3 700× the rungs' recording
>   precision, so the rungs genuinely are not a 1/W³ tail — but three points
>   inside a factor 1.5 in `W` cannot distinguish exponents either. `p = 1.657`
>   is an **effective exponent over [0.08, 0.12] m, not an asymptotic tail
>   exponent**, and `D∞` inherits that status.
>
>   **What the port-pair gate should state**, therefore: the box term as
>   **`D∞ = +1.69 pp` at the recovered `p = 1.657`, labeled an effective-range
>   extrapolation from three rungs spanning a factor 1.5** — never as a
>   converged box-free value, and never without the exponent, since assuming
>   the physically-expected `p = 3` instead gives −1.43 pp. This is strictly
>   better than "the suspect", which was the standing alternative, and it is
>   the whole of what decision (4) asked for. **Controls, both green:** a
>   synthetic triple planted from a known `(D∞, C, p)` is recovered to 4.4e-16
>   / 6.7e-15 (the vacuity guard — an exactly-determined solve has a
>   zero-by-construction residual and *no* goodness-of-fit claim exists, which
>   this step states up front and does not manufacture), and a non-monotone
>   triple is refused rather than fitted. **Method note:** decision (4) asked
>   for the solve seeded at `p = 3`; step 9's method needs no seed and was used
>   unchanged — it eliminates `C` and `p` analytically and bisects on the one
>   remaining unknown, so the complex/negative-`p` root the seed guarded
>   against is structurally absent rather than assumed away. **Scope held:**
>   annotation only; `PORT-1` stays 🟡; `MUTUAL_TOLERANCE` and
>   `REACTION_CONSISTENCY_TOLERANCE` untouched; no symbol flips; 3b-xi's own
>   "no extrapolation was attempted" sentence above stands as the record of
>   what *that* step did. **For a review:** if a converged box-free number is
>   ever wanted rather than an effective-range one, the blocker is named — a
>   fourth padding rung well outside [0.08, 0.12] (a factor ≥ 2 in `W`) is what
>   separates the exponents; nothing cheaper will.
>   **Review decision, 2026-08-12 (18:00): the fourth rung is not
>   commissioned.** The port-pair gate consumes the box term as a stated,
>   labeled systematic under the 10% `MUTUAL_TOLERANCE` bound; the full
>   exponent-model spread (+1.69 → −1.43 pp) is 3.1 pp — absorbable as a
>   labeled systematic and nowhere near the bound. A converged box-free
>   value would cost a ~250 000-cell rung at the recorded MUMPS kill line
>   (padding 0.12 / h_far 0.02 died at 237 926 cells) and buy no decision
>   the gate can see. Revisit only if the pair gate (§9 item 2,
>   2026-08-12 18:00) misses with the box term as the live suspect.
>
> * **Step 3b-xii — the box discriminator at padding 0.10** 🟡 *(executed
>   2026-08-07 12:00 run; **disposition (ii)** — parked on
>   `attempt/PORT-1-step3bxii-20260807T170000Z` (`87bf35d`), which carries the
>   full 3b-ix → 3b-x-b lineage plus this step)*. **The box is not the
>   residual.** Probe first, as the plan required: the gapped fixture meshes at
>   **194 985 cells** at `air_padding = 0.10` (1.0951× the 178 055 at 0.08,
>   under the 230 000 stop rule), and padding 0.08 re-meshed at **exactly**
>   178 055 — mesh-level fixture identity
>   (`20260807T170143Z_PORT-1-step3bxii-probe.log`, 59 s). The discriminator
>   then ran both routes on the enlarged box through the *same*
>   `_solve_gap_ports` the 0.08 gates use (`-n 2`, standard, **353 s**, 5
>   passed + the discriminator red,
>   `20260807T170430Z_PORT-1-step3bxii-disc-n2.log`):
>
>   | padding | estimator (× ωM₁₂) | σ = 0 control | deviation |
>   |---|---|---|---|
>   | 0.08 m | 0.894543 / 0.894022 | 0.922423 | **−3.0224e-02** |
>   | 0.10 m | 0.924103 / 0.923075 | 0.952868 | **−3.0188e-02 / −3.1267e-02** |
>
>   Enlarging the box moved the estimator **+2.956 pp** and the control
>   **+3.045 pp** — *both routes together* — so their difference stayed at
>   3.02–3.13% against the pre-decided 2.5% threshold: a move of **−0.104 pp**,
>   the wrong direction and 5× smaller than the 0.5 pp (i) demanded. The box
>   itself behaved exactly as 3b-xi measured, which is what makes this a
>   discriminator rather than a null result: the σ = 0 control reads 0.952868
>   at padding 0.10 against 3b-xi's *ungapped* reaction route at 0.949744, and
>   0.922423 against 0.919676 at 0.08 — a stable +0.27/+0.31 pp gapped/ungapped
>   offset under enlargement. Negative control, recomputed against this box's
>   own reference rather than quoted: the uncorrected wedge-only estimator
>   gives ratio 0.5181, deviation −0.4819, **15×** the threshold.
>   **Not tuned:** `REACTION_CONSISTENCY_TOLERANCE` stays at **0.03**. The
>   review authorized the re-size to 0.05 *iff* the routes converged; they did
>   not, so it is not taken. `MUTUAL_TOLERANCE` unmoved; nothing under `src/`
>   changed; known-issues 3 annotated. **What it leaves for a review:** the two
>   routes differ by ~3% for a reason that is neither truncation (this step)
>   nor the wedge limits (3b-x). The one remaining structural difference
>   between them is that the production loop is **gapped and σ = 800 S/m**
>   while the control's is **closed and lossless** — 3b-x-b's disposition (b)
>   ("explain the 2.8 pp first"), now the only surviving reading and no longer
>   competing with a box hypothesis. The successor a review must scope is a σ
>   sweep *on the control* (drive the closed footprint at the production σ, or
>   the production loop at σ → 0) to isolate which of gap-vs-closed and
>   lossy-vs-lossless carries the 3%; the branch does **not** land until that
>   is answered, and the estimator is not ported to the birdcage before it
>   lands. *(Original plan, 10:30 review, retained below for the record.)*
>
> * **Step 3b-xii — plan as scoped** *(scoped 2026-08-07 10:30 review — the rescope
>   of the twice-parked 3b-x/3b-x-b; works on
>   `attempt/PORT-1-step3bxb-20260807T111036Z` (`b86861e`), which carries the
>   full 3b-vi → 3b-x-b lineage)*. The 3% consistency gate is red by 0.02 pp
>   and the premise it was sized from is measured wrong (gapped/ungapped
>   spread 2.8 pp, not the assumed 1.2 pp); 3b-xi makes the box worth
>   ~4.8 pp over padding 0.08 → 0.12 on the ungapped pair. One measurement
>   chooses between 3b-x-b's two open dispositions: rebuild the **gapped**
>   fixture at `air_padding = 0.10` (nothing else moves) and compute both
>   routes on it — the corrected terminal-to-terminal estimator and the
>   σ = 0 closed-footprint control.
>   **Probe first, mesh-only:** gapped mesh at padding 0.10; > ~230 000 cells
>   ⇒ report the count and stop (0.08 gives 178 055; the ungapped sweep grew
>   1.132× at 0.10, so expect ~201k; 237 926 cells once died in MUMPS).
>   **Anchor:** (1) fixture identity before anything new runs — the branch's
>   padding-0.08 record byte-reproduces (estimator 0.894543 / 0.894022,
>   control 0.922423, deviation −3.0224e-02); (2) the discriminator — the
>   estimator/control deviation at padding 0.10 against the 0.08 record,
>   adjudicated by thresholds this review pre-decides: **(i) converging**,
>   deviation(0.10) ≤ 2.5% (a ≥ 0.5 pp move, 5× the 0.09% h_far mesh floor)
>   ⇒ the box owns the spread; execute disposition (a) as authorized here:
>   `REACTION_CONSISTENCY_TOLERANCE` 0.03 → **0.05**, the code comment
>   carrying the measured 2.8 pp spread, the 46% wedge-only negative
>   control, and both deviations; re-run the full padding-0.08 gate; all
>   green ⇒ land the whole branch lineage onto `main` in one commit and
>   delete the branch. **(ii) not converging**, deviation(0.10) > 2.5%
>   (including the ambiguous band up to 3.02%) ⇒ a real estimator bias
>   3b-x's correction did not remove, or an unresolved mix — park, report
>   both deviations and all four route values, annotate this entry and
>   known-issues 3; the escalation is the review's. Never tune to reach (i).
>   **Negative control:** on record — the wedge-only estimator's ratio
>   0.5352, 46% off, 9× even the re-sized bound. **Cost:** standard, `-n 2`;
>   two commands, each `timeout 600` — the discriminator (mesh ~60 s + two
>   drives ~2×30 s + control ~30 s at ~201k cells; 3b-x-b's full 0.08 run
>   was 298.6 s at 178k) and, under (i) only, the 0.08 gate re-run (~300 s).
>   **Traps:** all of 3b-vii/3b-ix/3b-x's (FFCx lock after a kill, pytest
>   `-s`, complex build + `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment`
>   first); buried segments are gap-tagged; the control drives the closed
>   **wire ∪ gap-footprint** union, never the open arc; `‖Z‖` normalisation
>   if reaction machinery is reused; known-issues 11 — the terminal gate
>   reads the tags' extreme reach, not the strip-contaminated ⟨y⟩; every
>   digit-string pinned in the branch's gates is padding-0.08-specific —
>   print the 0.10 numbers, pin nothing new in-slot. **Does not close:**
>   `PORT-1` or known-issues 3; `MUTUAL_TOLERANCE` never moves; the ωM₁₂
>   residual (−10.57% gapped) stays printed and tracked; no porting to the
>   birdcage. **Negative result:** disposition (ii) *is* the negative
>   result's disposition, and it is still a finding — the wedge correction
>   was not the last defect.
>
> * **Step 3b-xiii — executed 2026-08-08 (19:30 run), disposition (mixed):
>   the closed+lossy corner is physically degenerate** 🟡 *(parked on
>   `attempt/PORT-1-step3bxiii-20260808T005500Z` (`82bfb40`), which carries
>   the full 3b-ix → 3b-xii lineage plus this step)*. Fixture identity first
>   and it byte-reproduces the branch's record **exactly** — estimator
>   0.894543 / 0.894022 × ωM₁₂, control(σ = 0) 0.922423, deviation
>   **−3.0224e-02** — so nothing geometric moved. The ladder, σ applied to the
>   wire ∪ gap-box footprints of both loops through the same DG0 material map
>   the production solves use (`-n 2`, standard, **344.6 s**, 20 passed + the
>   known consistency gate red,
>   `20260808T004346Z_PORT-1-step3bxiii-ladder-b-n2.log`):
>
>   | control σ (S/m) | Im Z₂₁ (× ωM₁₂) | \|I_cond/I′\| |
>   |---|---|---|
>   | 0 | 0.922423 | — |
>   | 200 | 0.496614 | 0.412 |
>   | 800 | 0.107556 | 0.865 |
>
>   The ladder is **monotone decreasing** — the new ordering gate (the
>   intermediate rung must lie between the endpoints, or the ladder measures
>   noise rather than σ) passes — but it lands nowhere near either
>   pre-decided band: control(σ = 800) sits **78.7 pp** from the estimator and
>   **81.5 pp** from control(σ = 0), against 0.7 pp bands on a 2.81 pp
>   endpoint spread. **Not tuned:** `REACTION_CONSISTENCY_TOLERANCE` stays
>   **0.03**, nothing re-pointed, `MUTUAL_TOLERANCE` unmoved.
>   **What it actually measured, which is a finding about the plan and not
>   about the estimator:** the step's premise — that σ is a small perturbation
>   filling the (closed, lossy) corner of a 2×2 — is **disproved**. A *closed*
>   lossy loop is a shorted turn; the induced circulating current reaches 41%
>   of the impressed current at σ = 200 and 87% at σ = 800, and its back-field
>   cancels most of the mutual EMF the reaction integral reads. σ and
>   closed-vs-gapped are therefore **not separable on this control** — the
>   knob the review believed was independent is confounded with the very
>   difference it was meant to isolate. The ~3% deviation is untouched by this
>   step: three owners remain excluded (wedge limits 3b-x, the ωM₁₂ reference
>   3b-viii, the PEC box 3b-xii) and the loss-vs-gap question is **still
>   open**, but it now needs a *gapped* control (drive the production loop at
>   σ → 0 — the other half of the sweep the 3b-xii note offered) rather than a
>   lossy closed one. That is the escalation, and it is the weekly review's.
>   **Also fixed here, and independent of `PORT-1`:**
>   `_validate_material_map_tags` tested rank-local `cell_tags.values`, so a
>   material map over the two 1 mm gap boxes — valid globally — raised on one
>   rank of two while the other entered the solve and hung in the first
>   collective until the ceiling: a 246 s test session cost 601 s and 16
>   errors (`20260808T003238Z_PORT-1-step3bxiii-ladder-n2.log`). The tag set
>   is now reduced with `mesh.comm.allgather` before it is tested. It is
>   parked with the rest of the branch, but it is a standalone rank-safety
>   defect fix and a review should consider landing it on its own.
>   *(**Landed on `main` 2026-08-08 by `OPS-13`** (06:00 run) with its own
>   gate; the branch keeps its own copy of the identical hunk, so whoever
>   lands the branch resolves a trivial already-applied conflict.)*
>   *(Original plan retained below for the record.)*
>
> * **Step 3b-xiv — executed 2026-08-08 (04:30 run): the gapped σ = 0 corner
>   is an open circuit, and loss is exonerated by sensitivity** 🟡 *(parked on
>   `attempt/PORT-1-step3bxiv-20260808T095500Z` (`5f34f88`), which carries the
>   full 3b-ix → 3b-xiii lineage plus this step. Measurement only; every
>   disposition parks by plan.)* Fixture identity byte-reproduces the
>   padding-0.08 record exactly (estimator 0.894543 / 0.894022, control(σ = 0)
>   0.922423, deviation −3.0224e-02). σ went on `WIRE_TAGS` only — §9's
>   "wire ∪ gap-box" phrasing is the *control*'s region, and giving the gap box
>   σ closes the loop into 3b-xiii's degeneracy. New gate, the **bridge**: the
>   ladder's σ = 800 rung on the record's own `I_cond` normalisation returns
>   **0.894543** against the fixture's own production estimator, relative
>   difference **3.442e-13** — the ladder is the production route, solved
>   twice. Ladder (`-n 2`, standard, **448 s**, 17 passed + the known
>   consistency gate red,
>   `20260808T093445Z_PORT-1-step3bxiv-ladder-n2.log`):
>
>   | σ (S/m) | est on I′ | est on I_cond | \|I_cond/I′\| |
>   |---|---|---|---|
>   | 800 | 0.869401 | 0.894543 | 0.971942 |
>   | 200 | 0.872123 | 0.896408 | 0.972936 |
>   | 0 | 315.134574 | undefined | 0.000000 |
>
>   **(1) The σ = 0 corner is degenerate** — the pre-registered negative
>   result. With the gap open and the wire lossless the impressed 1 A across
>   the 1 mm gap box has no return path; it terminates as charge on the arc end
>   faces, `V_undriven` = −3.913198e+02 V (purely imaginary), and the estimator
>   reads 315.13 × ωM₁₂, **350×** the 2.788 pp band it was to be read inside.
>   That is a capacitive potential, not a mutual EMF. The 2×2 therefore cannot
>   be closed from **either** corner: closed+lossy is a short (3b-xiii),
>   gapped+lossless is an open (here). **(2) The non-degenerate rungs answer
>   the discriminator anyway, and they exonerate loss:** a 4× reduction in σ
>   moves the gapped estimator **+0.19 pp** (0.894543 → 0.896408), so closing
>   the 2.788 pp to control(σ = 0) needs ~4¹⁵ in σ. In the plan's bands this is
>   the **(gap owns it)** reading, reached by sensitivity rather than by the
>   degenerate σ = 0 point. With the wedge limits (3b-x), the ωM₁₂ reference
>   (3b-viii), the PEC box (3b-xii) and now loss all excluded, the gapped
>   estimator/geometry is the last suspect and 3b-xiii's escalation is
>   confirmed real. **(3) §9's negative control is inverted on this route:**
>   `|I_cond/I′|` here is a *series-continuity* number (0.97 = the impressed
>   current returning through the wire as it must), not a shorted-turn number;
>   only its exact collapse to 0 at σ = 0 transfers, and that is why the
>   record's normalisation dies at the bottom rung. **Not tuned:**
>   `REACTION_CONSISTENCY_TOLERANCE` 0.03, `MUTUAL_TOLERANCE` 0.10, nothing
>   re-pinned or re-pointed, nothing landed. The successor the attempts.md
>   entry proposes — *gapped-vs-closed at fixed σ = 800*, the one variable the
>   two routes still differ in, at the σ where both are well-posed — changes
>   the fixture's topology and needs the weekly review's licence.
>   *(Original plan retained below for the record.)*
>
> * **Step 3b-xiv — plan as scoped** *(scoped 2026-08-08, 03:00 review, from 3b-xiii's own
>   next-attempt hypothesis. Scope note: 3b-xiii's (mixed) disposition hands
>   the strategic adjudication — branch landing, gate re-pointing, fixture
>   redesign — to the weekly review, and this step does **not** take any of
>   that back. It is measurement only: the same sweep 3b-xiii attempted, run
>   from the half that is not degenerate, so the Sunday weekly review
>   adjudicates with the ladder in hand instead of commissioning it. Works on
>   `attempt/PORT-1-step3bxiii-20260808T005500Z` (`82bfb40`), the one live
>   lineage.)* 3b-xiii proved σ and closed-vs-gapped are confounded on the
>   *closed* control — a closed lossy loop is a shorted turn (`|I_cond/I′|`
>   up to 0.865). The reciprocal experiment has no such degeneracy: hold the
>   **production gapped** fixture fixed and move only σ on the wire ∪
>   gap-box footprints, σ ∈ {800 (the record), 200, 0}, through the same DG0
>   material field — a lossless *gapped* loop carries no circulating current
>   to confound the reading, and at σ = 0 the gap is the only structural
>   difference left against the closed lossless control. **Anchor:** (1)
>   fixture identity first — the branch's padding-0.08 record byte-reproduces
>   (estimator 0.894543 / 0.894022, control(σ = 0) 0.922423, deviation
>   −3.0224e-02) before any new solve; (2) the discriminator — where the
>   terminal-to-terminal estimator on the gapped loop at **σ = 0** lands
>   between the two on-record endpoints (2.81 pp apart), pre-decided bands at
>   quarter-spread: **(loss owns it)** `|est(σ=0) − 0.9224| ≤ 0.7 pp` ⇒ the
>   ~3% deviation was the loss, and the estimator-vs-control comparison was
>   across a σ mismatch — report; the re-pointing and the branch landing are
>   the weekly review's calls, now licensed by measurement; **(gap owns it)**
>   `|est(σ=0) − 0.8945| ≤ 0.7 pp` ⇒ the deviation survives with loss
>   removed — the gap geometry / estimator is the last suspect and the
>   escalation is confirmed real; **(mixed)** between ⇒ report all three
>   rungs and both distances. All three dispositions **park and report** —
>   nothing is re-pointed, no branch lands in-slot. **Negative controls:**
>   `|I_cond/I′|` must collapse toward 0 as σ → 0 on the gapped loop (print
>   the column — it is the anti-shorted-turn check that separates this
>   experiment from 3b-xiii's), and the σ = 200 rung must sit between its
>   neighbours or the ladder measures noise; the wedge-only estimator
>   (0.5181/0.5352, 15× the threshold) is on record, cite not recompute.
>   **Cost:** standard, `-n 2`, one command `timeout 600` — the identical
>   envelope 3b-xiii measured (344.6 s: mesh byte-reproduction + solves at
>   ~25 s + estimator drives). **Traps:** the 3b-xiii list unchanged (FFCx
>   lock, pytest `-s`, complex build + `FEM_EM_REQUIRE_COMPLEX=1`,
>   `tests/environment` first, σ via the DG0 field never a global,
>   known-issues 11); every pinned digit-string on the branch is
>   σ = 800-specific — print the ladder, pin nothing in-slot;
>   `REACTION_CONSISTENCY_TOLERANCE` stays 0.03 and `MUTUAL_TOLERANCE` stays
>   0.10 under every band. **Does not close:** `PORT-1`, known-issues 3, or
>   the branch's disposition — all weekly-review calls; this step only
>   converts the idle slots before Sunday into the measurement that review
>   needs. **Negative result:** every band is a finding; if σ = 0 makes the
>   solve or the normalisation degenerate in some unforeseen way (the
>   impressed-drive normalisation should be σ-independent, but that is an
>   expectation, not a record), *that* is the measurement — report it and
>   stop; never substitute a small σ > 0 silently.
>
> * **Step 3b-xiii — plan as scoped** *(scoped
>   2026-08-07, 18:00 review — the successor 3b-xii's disposition (ii) handed
>   to a review. Works on `attempt/PORT-1-step3bxii-20260807T170000Z`
>   (`87bf35d`), the one live lineage — 3b-x-b's branch was verified strictly
>   superseded and deleted this review.)* Three owners of the ~3%
>   estimator-vs-control deviation are measured and excluded — wedge limits
>   (3b-x), the `ωM₁₂` reference (3b-viii), the PEC box (3b-xii). The two
>   routes now differ in exactly two ways at once: the production loop is
>   **gapped** and **σ = 800 S/m**, the control's is **closed** and
>   **lossless**. One knob separates them: re-run the *existing* σ = 0
>   reaction control (closed wire ∪ gap-footprint union, same
>   `_solve_gap_ports` machinery, padding 0.08 — nothing geometric moves)
>   with the union's conductivity set to **σ ∈ {200, 800} S/m** via the same
>   DG0 material field the control already builds. That fills the missing
>   corner of the 2×2 (closed + lossy) and makes σ the only moved variable.
>   **Anchor:** (1) fixture identity first — the branch's padding-0.08 record
>   byte-reproduces (estimator 0.894543 / 0.894022, control 0.922423,
>   deviation −3.0224e-02) before any new solve; (2) the discriminator —
>   where `control(σ=800)` lands between the two on-record endpoints, 2.80 pp
>   apart, adjudicated by pre-decided bands: **(loss owns it)**
>   `|control(800) − 0.8945| ≤ 0.7 pp` (quarter-spread) **and** the ladder
>   monotone decreasing in σ ⇒ the consistency gate was comparing across a σ
>   mismatch, not measuring an estimator bias; re-point
>   `REACTION_CONSISTENCY_TOLERANCE`'s comparison at the σ-matched control
>   (bound **stays 0.03**), re-run the full 0.08 gate; all green ⇒ **land the
>   branch lineage onto `main` and delete the branch** (authorized by this
>   review under exactly this disposition). **(gap owns it)**
>   `|control(800) − 0.9224| ≤ 0.7 pp` ⇒ loss is exonerated; the gap
>   geometry / estimator bias is the last suspect — park, annotate here +
>   known-issues 3; escalation (weekly review) is explicitly next.
>   **(mixed)** anything between ⇒ report the full ladder and both distances,
>   park, no re-pointing. **Negative control:** on record, cite — the
>   wedge-only estimator at 0.5181/0.5352, 15× the threshold; and the σ = 200
>   rung must sit between the σ = 0 and σ = 800 values or the ladder itself
>   is suspect. **Cost:** standard, `-n 2`, one command `timeout 600` —
>   mesh ~60 s (must byte-reproduce 178 055 cells) + two control solves
>   (25.4 s each on record at σ = 0) + the two estimator drives for the
>   identity check (~2 × 30 s); 3b-x-b's full 0.08 run was 298.6 s.
>   **Traps:** the 3b-xii list unchanged (FFCx lock, pytest `-s`, complex
>   build + `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first, buried
>   segments gap-tagged, control drives the closed **wire ∪ gap-footprint**
>   union, known-issues 11); σ enters through the control's DG0 field, never
>   a global constant; every pinned digit-string on the branch is
>   σ = 0-specific — print the ladder, pin nothing in-slot. **Does not
>   close:** `PORT-1` or known-issues 3 (even landing the branch leaves the
>   birdcage port step unscoped); `MUTUAL_TOLERANCE` never moves; the ωM₁₂
>   residual stays printed and tracked. **Negative result:** every band is a
>   finding — (gap) and (mixed) park with the ladder recorded here and in
>   known-issues 3; never tune σ, the bands, or the bound to force (loss).

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

### EX — Examples (§5.4 ramp)

Standalone example chunks enqueued by the daily review when a chunk closes a
quantitative gate (§5.4). Each is sized for one implementer run, executes via
`./run_examples.sh`, produces combined-XDMF that opens in ParaView, and
demonstrates a **gated** capability from an angle no existing example covers.

**Ramp accounting (2026-08-09 weekly review, first full audit).** Seven
registered examples. Per-phase against §5.4's
`min(5, gating chunks closed ✅)`: **Phase 1** (complete, owes 5) has 3 —
straight wire, circular loop, Helmholtz — shortfall 2 → `EX-9`, `EX-10`.
*(Backfill complete 2026-08-10: `EX-10` closed at the 06:00 run and `EX-9` at
the 07:30 run, so Phase 1 now carries 5 of 5 and this shortfall is discharged
too — the figures in this paragraph are the 2026-08-09 weekly-review snapshot,
kept for the audit trail.)*
**Phase 2** (5 of `TH-1`…`TH-9` ✅, owes 5) has **0** — no example runs a
time-harmonic solve at all; shortfall 5 → `EX-4`…`EX-8`. *(Backfill complete
2026-08-09, 22:30 run: `EX-8` closed the last of the five, so Phase 2 now
carries 5 of 5 and this shortfall is discharged — the figures above are the
2026-08-09 weekly-review snapshot, kept for the audit trail.)* The miss predates
the accrual mechanism (adopted 2026-08-06, after Phase 2's gates closed
2026-07-31), so it is a backfill, not a mechanism failure this week.
**Phase 3** (`MAT-2` + `MAT-6` ✅, owes 2) has 1 (`mri:2`) — shortfall 1 →
`EX-11`. **Phases 4/5** owe 0 (no gating chunk ✅ yet); `mesh:1`/`mesh:2`
are bonus meshing coverage. `mri:1` is the one **ungated** example (WF-1
🧪 end-to-end demo); its stale docstring was fixed by `EX-12` ✅ 2026-08-09,
which also labels it in the file as the one example that asserts nothing.
New chunks are ordered most-mission-relevant first (`EX-11` feeds `ANS-1`);
the daily review queues them at its own pace — they are backlog, not a
mandate to displace the critical path.

| ID | Title | Status | Tier |
|---|---|---|---|
| `EX-1` | Two-torus port fixture: conforming mesh, cell and facet tags in ParaView | ✅ | standard |
| `EX-2` | Cylindrical phantom domain: wall classification and tags in ParaView | ✅ | standard |
| `EX-3` | Mass-averaged SAR on the standard-masses sphere: point and 1 g/10 g fields in ParaView | ✅ | standard |
| `EX-4` | Lossy plane wave: decay and phase vs closed form (first time-harmonic example) | ✅ | standard |
| `EX-5` | PEC cavity resonances: eigenfrequencies vs closed form, mode field in ParaView | ✅ | standard |
| `EX-6` | Sphere in a uniform field: solved quasi-static response vs closed form | ✅ | standard |
| `EX-7` | Waveguide/coax: the `TH-7` gated quantity as a runnable example | ✅ | standard |
| `EX-8` | Resonance guard on a frequency sweep: the `TH-1` step-5 detector firing | ✅ | standard |
| `EX-9` | Measured h-convergence rate as an example output (Phase 1) | ✅ 2026-08-10 | heavy (reclassified from standard: 130 s of solve, §5.1 names convergence studies) |
| `EX-10` | Gauge cross-check: penalty vs Lagrange-multiplier Coulomb gauge (Phase 1) | ✅ | standard |
| `EX-11` | Dodd–Deeds coil loading: ΔR vs closed form, eddy currents in ParaView | ✅ | standard |
| `EX-12` | Examples hygiene: stale claims, dead references, the 2026-02 PNG | ✅ | smoke |
| `EX-13` | `examples/mri/01` at the validated gauge floor: rank-spread measured, on-record numbers refreshed | 🚫 | standard |
| `EX-14` | Straight-wire VTX export repair + the refcheck freshness branch exercised | ✅ (2026-08-10: round-trip max\|B\| identical to 12 digits, rel diff 0.000e+00 vs 1e-10; freshness branch fired, then green) | standard |
| `EX-15` | Every runnable example gets a step-by-step analysis guide (3 steps, operator directive) | ✅ (2026-08-11: all three steps landed; **16 of 16** runnable examples checked against 3 required headings, `PENDING_GUIDES` empty, negative controls fired in all three steps) | standard |
| `EX-16` | `examples/mri/01`: converge the frequency-domain solve, then re-measure the rank spread | 🚫 (2026-08-10: solve converges — `preonly`/LU, `reason=4` — and the spread does **not** move, 23.5539% vs the 23.5545% unconverged record; anchor FAIL, negative-result clause taken. Fix landed; the 23% is the centerline sampling path, 3215× the phantom path on the same fields) | standard |
| `EX-17` | Circular-loop VTX export repair: port the `EX-14` diff, same round-trip anchor | ✅ (2026-08-10: round-trip max\|B\| 7.756122914931e-05 T both ways, rel diff 0.000e+00 vs 1e-10; loop's analytic numbers unmoved, checker green) | standard |
| `EX-18` | Gap-voltage port pair → Z → S on the two-torus fixture (the 3b-xvii/xviii gated capability; first ports example) | ✅ (2026-08-13: raw 0.894543 × ωM₁₂ printed as the miss it is, corrected 0.939849 (−6.02%) inside the unmoved 10%; ‖S−Sᵀ‖/‖S‖ = 2.5494e-05, ‖S‖₂ = 0.861449 ≤ 1; blind-ladder negative control −98.26% asserted to fail; 134 s at `-n 2`) | standard |
| `EX-19` | Larmor lossy-sphere example (`TH-10`'s newly gated capability: first example solving at 64/128 MHz; rubric in the §9 item) | ⬜ | standard |

**`EX-4`…`EX-11` — backfill plans (scoped 2026-08-09, weekly review; one
run each).** Common rules: gated capability only; the example *asserts* its
anchor (allreduced), never just renders; tolerances cite the gate log they
come from and may be looser, never tighter, than the gated bound; complex
build sourced + `FEM_EM_REQUIRE_COMPLEX=1` for `EX-4`…`EX-8`; runner
registration (`./run_examples.sh --list` + `-e <id>` logs) is part of the
chunk, per the `EX-1` demotion lesson. Done-when for each: runner-dispatched
harness log with the anchor asserted, combined-XDMF written, elapsed
recorded.
> * **`EX-4`** — the `TH-6` box driven by the analytic lossy plane wave
>   (`tests/validation/test_lossy_plane_wave.py` fixture, σ = 0.6 S/m
>   — *the fixture's `SIGMA` is in fact **0.7**; corrected 2026-08-09 at
>   execution, the example imports the constant rather than restating it*,
>   εᵣ = 78 at 127.74 MHz): export Re/Im E and |E|; assert interior decay
>   and phase constants within 1% of their closed forms (0.019% / 0.059% on
>   record). Angle: the first example anywhere to show a solved
>   time-harmonic field, and loss visibly attenuating it.
> * **`EX-5`** — ✅ **closed 2026-08-09 (15:00 run).**
>   `examples/time_harmonic/02_pec_cavity_resonances.py`, dispatched as `th:2`,
>   reproduces the `TH-9` record digit for digit through the example path: all
>   four modes asserted against the (l,m,n) closed form at the plan's 0.5%
>   ceiling — 239.9805 / 291.3904 / 312.3465 / 346.5469 MHz, errors 0.0123% /
>   0.0153% / 0.0201% / 0.0436% — with `null_mode_count == 0` and 720 cells /
>   5330 dofs, 0.6 s of solve. Two further gates the plan did not ask for but
>   the export needed: the **Rayleigh quotient** ∫|∇×E|²/∫|E|² of the exact
>   function written to XDMF re-measures 239.9805 MHz, **3.48e-15** relative to
>   the reported eigenvalue (so ParaView colours the asserted mode, not a
>   look-alike), and the exported magnitude spans 2.31e-17 … 1.0 after peak
>   normalisation, i.e. the PEC wall condition is visible in the array itself.
>   Negative control cited not re-run per the plan (8/8 gradient modes at
>   3.2e-15 relative, `20260730T154846Z_TH-9.log`), with an in-run assertion
>   that the cited cluster and the measured 4.36e-04 physical error still
>   straddle the gate's 1e-8 cutoff. `core/cavity.py` gained an additive
>   `return_modes=False` kwarg (eigenvectors, sorted with their eigenvalues,
>   `CavitySpectrum.mode_functions`/`.mesh`); no gate assertion depends on it
>   and `TH-9` was re-run to prove it (3 passed, `-n 2`). Logs
>   `20260809T200348Z_EX-5-runner-list.log`,
>   `20260809T200354Z_EX-5-gate.log` (2 s),
>   `20260809T200401Z_EX-5-TH-9-regress.log` (4 s). *(Original plan text
>   follows.)* `TH-9` machinery on the rectangular PEC cavity: assert the
>   fundamental within 0.5% of the (l,m,n) closed form (0.0436% on record);
>   export one mode field. Angle: eigen-analysis, the Phase-6 tuning
>   primitive.
> * **`EX-6`** — ✅ **closed 2026-08-09 (19:30 run).**
>   `examples/time_harmonic/03_dielectric_sphere_in_uniform_field.py`, dispatched
>   as `th:3`, reproduces the `TH-8` finest-mesh record **digit for digit**
>   through the example path: interior `E_z` = 0.038416 V/m vs the closed-form
>   3/(ε+2)·E₀ = 0.037500, **2.443%** against the gate's own 5% MVP ceiling —
>   identical to `20260731T200457Z_TH-8-gate-final.log` — with spread **0.080%**,
>   transverse/E_z **0.085%** and |Im|/|Re| **0.0e+00**, also identical, at 39 693
>   cells and 7.3 s of solve. The fixture is imported (geometry, frequency, probe
>   cloud, and the exterior Dirichlet callable), never restated.
>   Two gates beyond the plan's ask, both for the export: the interior average is
>   re-measured by a **volume integral** ∫_sphere E_z dx / ∫_sphere dx over the
>   tagged cells — 0.038411 V/m, **0.014%** from the probe average, i.e. assembly
>   over the whole ball agrees with point location on two shells, so what
>   ParaView colours is the field the anchor was read from; and the tagged region
>   is confirmed to *be* the sphere (assembled volume 5.206270e-04 m³ vs
>   4/3πR³ = 5.235988e-04, **0.568%** — a faceted tetrahedral ball under-fills,
>   which is what that reads). The **interface jump** is a number, not just a
>   picture: E_out/E_in = **59.20×** over the pole (closed form 56.27×) and
>   **11.46×** at the equator (11.83×), the sign reversal of the dipole lobe in
>   one pair. Negative control cited not re-run per the plan (ε-blind solve, same
>   Dirichlet data, E_z = 0.918143 V/m, **2348%** off — a factor 23.9 above this
>   run), with an in-run assertion that the cited control and the measured error
>   still straddle 100%.
>   **One bound was set from measurement, not inherited:** the two *exterior*
>   probes at r = 1.2 R sit in the far mesh (h_far = 0.0125 m = 0.25 R, twice the
>   sphere's h, unrefined by the fixture) where the dipole falls as 1/r³, and
>   they read 7.782% (pole) / 0.756% (equator) against their closed form. `TH-8`
>   gates the interior only, so no gated bound existed to inherit; `EXTERIOR_RTOL`
>   is 10% with both numbers and the reason recorded in the constant's comment.
>   The interior anchor was **not** touched — it stands at the gate's own 5%.
>   The pre-measurement 5% guess failing on the polar probe is why the first run
>   is on record too. Logs `20260810T003330Z_EX-6-runner-list.log` (`th:3`
>   registered), `20260810T003418Z_EX-6-run1.log` (exit 1, the exterior-bound
>   finding, 13 s), `20260810T003510Z_EX-6-gate.log` (exit 0, 9 s harness-wall,
>   7.8 s in-example), `20260810T003546Z_EX-6-refcheck.log` +
>   `20260810T003557Z_EX-6-refcheck-refresh.log` +
>   `20260810T003610Z_EX-6-refcheck2.log` (the `EX-12` doc-reference checker: it
>   fired the **freshness** branch on the straight-wire artifacts, 3.0 h old
>   against a 1.0 h window — the branch `EX-14` was created to exercise, hit here
>   for real; re-running `-e 1` refreshed them and the checker is PASS at 16
>   references). README example list extended with `th:3`.
>   *(Original plan text follows.)* the `TH-8` sphere in an imposed uniform
>   field: assert the interior/exterior field ratio against the quasi-static
>   closed form at the gated tolerance; export the field showing the interface
>   jump. Angle: material contrast in a solved field (`EX-3` *imposes* its field;
>   this one solves it — state that distinction in the report text).
> * **`EX-7`** — ✅ **closed 2026-08-09 (21:00 run).**
>   `examples/time_harmonic/04_evanescent_waveguide_decay.py`, dispatched as
>   `th:4`, reproduces the `TH-7` finer-mesh record **digit for digit** through
>   the example path: fitted decay constant **γ = 37.650399 Np/m** against the
>   closed form √(k_c²−k₀²) = 37.652670 Np/m, **0.006%** at the gate's own 5%
>   MVP ceiling — identical to `20260731T123411Z_TH-7-gate-final.log` — with
>   whole-domain relative L2 **4.406648e-02** and residual |Im E_y|/|Re E_y|
>   **0.000e+00**, also identical, at 41 472 cells and 5.1 s in-example. The
>   fixture is imported (geometry, frequency, the exact-field factory, the probe
>   line and its fit window), never restated. The §9 item's wording correction
>   holds: the `TH-7` gate is the **evanescent TE₁₀ decay below cutoff**, and no
>   line-impedance or S-parameter claim is made or implied (`PORT-1` owns that).
>   Two gates beyond the plan's ask, both for the export: γ is **refitted from
>   the CG1 array actually written to XDMF** — 37.606274 Np/m, **0.117%** from
>   the N1curl fit, so ParaView colours the field the anchor was measured on —
>   and the **mode profile is a number**: 25 points across the guide at mid-length
>   read **0.200%** RMS from sin(πx/a) after peak normalisation, i.e. the TE₁₀
>   half-arch is in the exported array. The exported |E| spans
>   5.147567e-17 … 1.000725e+00 V/m, so the PEC side-wall zero is visible in the
>   array itself. Negative control cited not re-run per the plan (the gate's
>   three-frequency sweep: measured γ ratio 2.6373 vs closed-form 2.6383, 0.038%,
>   asserted > 2.0, against exactly 1 for a k₀-blind solver), with an in-run
>   assertion that this run's own γ sits strictly below k_c (1.67× below), which
>   a k₀-blind operator cannot do at any mesh.
>   **Two bounds were set from measurement, not inherited** — both on the
>   *exported* CG1 field, which `TH-7` does not gate: `CG1_VS_NEDELEC_MAX` = 0.5%
>   (measured 0.117%) and `PROFILE_RMS_MAX` = 2% (measured 0.200%), each with its
>   measurement and the reason for the margin in the constant's comment. The
>   anchor was **not** touched — it stands at the gate's own 5%. No `src/` change
>   was needed, so no gate re-run was owed. Logs
>   `20260810T020317Z_EX-7-runner-list.log` (`th:4` registered by the runner's
>   filename glob), `20260810T020325Z_EX-7-run1.log` (exit 0, 11 s — first run
>   passed; its numbers are what the two export bounds were then set from),
>   `20260810T020355Z_EX-7-gate.log` (exit 0, 7 s harness-wall, 5.1 s in-example,
>   the tightened bounds re-verified), `20260810T020419Z_EX-7-refcheck.log` +
>   `20260810T020433Z_EX-7-refcheck-refresh.log` +
>   `20260810T020439Z_EX-7-refcheck2.log` (the `EX-12` doc-reference checker
>   fired the **freshness** branch on the straight-wire artifacts again — 1.5 h
>   against the 1.0 h window, the second consecutive run to hit it, unrelated to
>   this chunk; `-e 1` refreshed them, checker PASS at 16 references, and `-e 1`
>   reproduced 65.8739% / 85.2498% on the way). README example list extended
>   with `th:4`. *(Original plan text follows.)* the `TH-7` waveguide/coax case:
>   reproduce the gated cutoff or line-impedance quantity within its gate
>   tolerance; export the mode profile. Angle: guided-wave/port-adjacent
>   geometry.
> * **`EX-8`** — ✅ **closed 2026-08-09 (22:30 run).**
>   `examples/time_harmonic/05_resonance_guard_sweep.py`, dispatched as `th:5`,
>   reproduces the `TH-1` step-5 record **digit for digit** through the example
>   path — every printed quantity, not merely the anchor: approach max
>   |dlnW/dlnf| **137.554** (threshold 50) and implied detuning **1.454%**;
>   quiet-band max slope **21.951**, untriggered; separation **6.267×**; energy
>   amplification **16.505×** against the |f−f₀|⁻² pole law's 16.0×, **3.156%**
>   against the gate's own 10% ceiling; all six sweep energies identical to
>   `20260731T021521Z_TH-1-step5b.log` (5.8742e-07 / 2.3992e-06 / 9.6953e-06 and
>   1.4700e-07 / 9.4344e-08 / 6.6048e-08). Six solves in 21.4 s, 23.3 s total.
>   The fixture is imported — sweep windows, mesh, material, drive — never
>   restated, which the plan required precisely because that gate had to place
>   its quiet window twice. **The negative control is in-fixture and solved
>   here, not cited:** the quiet arm is the third and fourth solves of the run
>   and must stay silent, so a guard that always fires fails this example.
>   Two gates beyond the plan's ask, both for the export: the two `.xdmf`
>   arrays are the phasors of the nearest-approach and quiet-midpoint solves,
>   and the stored energy **re-assembled from the Functions handed to the
>   writer** reproduces their sweep-table entries to **0.00e+00** relative
>   (bitwise — same Function objects, so an off-by-one in the sweep index or a
>   stale field is what this would catch); and the pole is visible in the
>   exported field itself, |E| peaking at **6.0531e+03 V/m** near-resonant vs
>   **6.1951e+02 V/m** quiet, a factor **9.77** on the same mesh, same drive,
>   same colour scale. No tolerance was loosened and none was invented: every
>   bound is the `TH-1` step-5 gate's own.
>   `tests/validation/test_resonance_guard.py` gained one **additive** refactor
>   — `_solve_at(msh, f)` returning the fields, with `_energy_at` now a
>   one-liner over it — so the example exports the solve the guard scored rather
>   than an equivalent re-solve; no gate assertion depends on it and `TH-1`
>   step 5 was re-run to prove it (6 passed, `-n 2`, 21.29 s). Logs
>   `20260810T033306Z_EX-8-runner-list.log`,
>   `20260810T033313Z_EX-8-gate.log` (26 s),
>   `20260810T033348Z_EX-8-TH-1-step5-regress.log` (23 s),
>   `20260810T033443Z_EX-8-refcheck-final.log` (PASS, 16 references).
>   *(Original plan text follows.)* sweep across the `TH-9` fundamental with
>   `core/resonance.py`: assert the guard fires at the on-record detuning
>   (1.5%) and the energy rise follows the |f−f₀|⁻² pole law within 10%
>   (3.16% on record); output the S-metric table. Angle: diagnostics — the
>   ill-conditioning trap Phase 6 will operate inside, made visible.
> * **`EX-9`** — ✅ **closed 2026-08-10 (07:30 run).**
>   `examples/magnetostatics/06_h_convergence_rate.py`, dispatched as `-e 6`
>   (real build), runs the `MAG-13` h-refinement sequence as an example and
>   outputs the quantity no other example does: a **rate**. **Anchor:** the
>   fitted slope of `log(error)` against `log(h)` over the gate's own triple is
>   **1.1009**, inside the gate's `0.7 < p < 1.5` band and reproducing the
>   **1.10** on record in `20260730T125522Z_MAG-13.log`; the three errors
>   reproduce that record to every digit it carries — **22.1925% / 12.7485% /
>   9.2568%** at h = 0.004 / 0.0025 / 0.0018 (38 750 / 145 884 / 383 248 cells)
>   against 22.19 / 12.75 / 9.26. **The negative control is solved here, not
>   cited:** monotone decrease across the three resolutions is asserted, which
>   is what a slope fitted through h-blind noise fails — the same property that
>   forced `MAG-13` to exclude h = 0.0035 (11.77%, below the h = 0.0025 value).
>   The fixture is **imported**, not restated: an additive refactor lifted the
>   parameters, the per-resolution solve (`solve_h_refinement`), the sample line
>   and the rate fit (`fit_convergence_rate`) to module scope in
>   `tests/validation/test_convergence.py`, so the example and the gate run one
>   measurement rather than two copies; the gate was re-run to prove the
>   refactor changed nothing (`20260810T124051Z_EX-9-MAG-13-regress.log`,
>   1 passed / 2 skipped, 129 s, `-n 2`).
>   **One gate beyond the plan's ask, and it returned a finding.** The error was
>   re-measured on the *exported* CG1 function at the same ten points:
>   **17.1451%**, against **9.2568%** for the solved N1curl field — a **7.89
>   percentage-point** loss. `curl(A)` is cell-wise constant at N1curl degree 1,
>   so writing `B` to a continuous space averages neighbouring cells at each
>   vertex, and on a 1/r field near a conductor that averaging costs most of
>   what the whole refinement sequence bought. The first run
>   (`20260810T123503Z_EX-9-run1.log`, exit 1) asserted a ±5% agreement between
>   the two, which measurement refuted; the bound was **not** widened to fit —
>   the check was re-pointed at the run's own coarsest solved resolution
>   (exported error must stay under 22.1925%, i.e. smoothing may not cost more
>   than the refinement gained), with the measured 7.89 points recorded in the
>   constant's comment, the docstring and the guide. Nothing was inherited:
>   `MAG-13` gates no export. The closed form is deliberately **not** exported
>   beside the numeric field — it is the exterior solution, valid only for
>   r > a, so a whole-domain difference would be dominated by an invalid
>   interior comparison and a 1/r axis singularity.
>   No `src/` change. Guide `06_h_convergence_rate.md` written to the `EX-15`
>   step-1 bar (guide pass now checks 7 examples, up from 6). Logs
>   `20260810T123456Z_EX-9-runner-list.log` (`-e 6` registered),
>   `20260810T123503Z_EX-9-run1.log` (exit 1, the export finding above),
>   `20260810T123824Z_EX-9-run2.log` (exit 0, 129 s),
>   `20260810T124317Z_EX-9-run-final.log` (exit 0, 131 s harness-wall, 130.1 s
>   in-example — the committed record),
>   `20260810T124051Z_EX-9-MAG-13-regress.log` (gate green after the refactor),
>   `20260810T124544Z_EX-9-refcheck.log` (exit 1: the **freshness** branch yet
>   again, the same 11 straight-wire/Helmholtz/gauge artifacts 1.7 h against the
>   1.0 h window — third consecutive run, `EX-14`'s branch, unrelated to this
>   chunk; the guide pass PASSed here),
>   `20260810T124556Z_EX-9-refcheck-refresh.log` (`-e 1,4,5`, 84 s, reproducing
>   65.8739% and 0.0004% / 0.0033% on the way),
>   `20260810T124730Z_EX-9-refcheck2.log` (both passes PASS, 37 references).
>   **Tier reclassified standard → heavy**: 130 s of solve at `-n 2` on the
>   example path plus meshing exceeds what a 180 s ceiling can hold with any
>   margin, and §5.1 names convergence studies as the heavy tier's own example
>   (`MAG-13` is labeled heavy for the same measurement). **Phase-1 §5.4
>   example backfill is complete** — `EX-9` was the last of it. *(Original plan
>   text follows.)*
>   *(corrected 2026-08-09, 18:00 review: the original text
>   said "three-resolution Helmholtz (the `MAG-14` fixture, cheap)" — no
>   such fixture exists. The 1.10 rate on record belongs to the
>   straight-wire h-refinement,
>   `tests/validation/test_convergence.py::TestConvergence::test_h_refinement_straight_wire`,
>   measured in `20260730T125522Z_MAG-13.log` at ~167 s — standard tier at
>   its ceiling, not cheap. Corrected plan:)* three-resolution straight
>   wire via the `test_convergence.py` fixture: fit the convergence rate,
>   assert `0.7 < rate < 1.5` (the gate's own band; 1.10 on record);
>   print the (h, error) table. Angle: the output quantity is the *rate* —
>   no example shows convergence behaviour. Budget the full 180 s.
> * **`EX-10`** — ✅ **closed 2026-08-10 (06:00 run).**
>   `examples/magnetostatics/05_gauge_cross_check.py`, dispatched as `-e 5`
>   (real build), solves the imported `MAG-15` wire fixture
>   (`tests/solver/test_gauge_lagrange.py` — geometry, `RESOLUTION`, and the
>   same eight probe points, imported not restated) **twice on one mesh**, once
>   per `GaugeMethod`. **Anchor:** probe-point
>   `ErrorMetrics.l2_relative_error(b_lag, b_pen)` = **0.0004%** against the
>   gate's 5% ceiling — the scalar `20260728T193524Z_MAG-15.log` never printed,
>   so this run is now its record. **The negative control is measured, not just
>   cited, and it is the reason the anchor means anything:** max|A| = 5.073e+01
>   (penalty) vs **1.407e-09** (Lagrange), ratio **2.774e-11** against the
>   gate's 1e-6 — matching the on-record 5.2e+01 / 1.6e-09 at the finer h, so
>   the two solves demonstrably differ by eleven orders in `A` while agreeing to
>   four decimals in `B`. The multiplier diagnostic is asserted to discriminate
>   (`nan` for penalty, finite 2.083e+02 for Lagrange) and never pinned — the
>   fixture's source is incompatible by construction (`J·n ≠ 0` on the end
>   caps).
>   **One gate beyond the plan's ask, for the export:** eight probes on one line
>   say nothing about what ParaView colours, so agreement is re-measured as a
>   volume integral `sqrt(∫|B_lag−B_pen|²dx / ∫|B_pen|²dx)` over the *exact CG1
>   functions written to the XDMF* — **0.0033%**, both integrals allreduced
>   before the division. 8× the probe figure and four orders inside the ceiling,
>   which is the expected ordering (the volume norm includes the conductor
>   interior and the wall region the probes never see). Its 5% bound is not
>   inherited — no `MAG-15` assertion covers a volume norm — and is set equal to
>   the probe anchor it corroborates, with the reason in the constant's comment.
>   No `src/` change, so no regression re-run was owed. 14 055 cells, 0.5 s
>   penalty / 2.3 s Lagrange, 5.1 s in-example. Guide
>   `05_gauge_cross_check.md` written to the `EX-15` step-1 bar (the guide pass
>   checks 6 examples now, up from 5). Logs
>   `20260810T110301Z_EX-10-runner-list.log` (`-e 5` registered),
>   `20260810T110311Z_EX-10-run1.log` (exit 0, 8 s harness-wall — passed first
>   attempt, no bound was moved), `20260810T110431Z_EX-10-refcheck.log` (exit 1:
>   the **freshness** branch again, 10 straight-wire/Helmholtz artifacts 1.5 h
>   old against the 1.0 h window — same `EX-14` branch `EX-6` hit; the guide
>   pass already PASSed here),
>   `20260810T110453Z_EX-10-refcheck-refresh.log` (`-e 1,4`, 78 s — `-e 2`
>   deliberately excluded, its 411 k-cell mesh is the expensive one and no
>   `.xdmf` reference points at it), `20260810T110622Z_EX-10-refcheck2.log`
>   (both passes PASS, 34 references). Phase-1 §5.4 shortfall is now **1**
>   (`EX-9` outstanding). *(Original plan text follows.)* same magnetostatic
>   fixture solved with the gauge penalty
>   and the `MAG-15` Lagrange-multiplier gauge: assert the two B fields
>   agree within the `MAG-15` gated tolerance; export both. Angle:
>   formulation cross-validation.
> * **`EX-11`** — the `MAT-6` W = 0.15 fixture, two solves (σ = 100, σ = 0
>   at 10 MHz): assert ΔR within 2% of the Dodd–Deeds closed form (1.5834%
>   on record, projected drive); export |J| in the slab so the eddy-current
>   pattern is visible. ~27 s/solve at 138 619 cells on record — standard
>   tier holds. Angle: the headline loaded-coil physics; doubles as the
>   compute core of `ANS-1`. **Does not close:** any Larmor-frequency
>   claim — 10 MHz, eddy-current regime, per §2.1.
> * **`EX-12`** — ✅ **closed 2026-08-09 (16:30 run).** All four named defects
>   fixed, plus two the gate itself found. The gate is a new script,
>   `scripts/testing/check_example_doc_references.py`: it scans every `*.md`
>   under `examples/`, requires each referenced `*.py` to exist in the repo,
>   and requires each referenced artifact either to be committed in-tree (the
>   `ans:` cases keep theirs beside `SPEC.md`) or to sit in `paraview_output/`
>   **newer than `--max-age-s`** — existence alone would let a months-old
>   leftover in that gitignored scratch dir vouch for a dead reference.
>   16 distinct references checked across 7 guides, 1 allowlisted
>   (`lineplot.csv`, user-created by a ParaView filter, reason recorded in the
>   script). PASS at exit 0 (`20260809T213823Z_EX-12-refcheck.log`, 1 s);
>   **negative control** `--max-age-s 1 --output-dir /tmp/empty-outdir` flags
>   5 of them and exits 1 (`20260809T213828Z_EX-12-refcheck-negctl.log`), so
>   the check discriminates rather than always passing. Re-run gate
>   `./run_examples.sh -e 1,mri:1 -n 2 -t 180`
>   (`20260809T213840Z_EX-12-gate.log`, exit 0, 11 s harness-wall, smoke tier)
>   reproduces every on-record number after the edits: `-e 1` relative L2
>   error **65.8739%** and max relative error **85.2499%** (2026-08-04 record
>   `20260804T174037Z_MAG-EX.log`, identical), `mri:1` `residual_norm`
>   **1.684628e+00** and all five centerline (|E|, |B|) pairs digit for digit
>   against `20260804T174011Z_WF-1.log`. **Two findings the plan did not
>   anticipate.** (i) The VTX/`.bp` export in `01_straight_wire.py` has never
>   worked — `VTXWriter` is handed the N1curl `A` and the one `try` covers
>   both writers, so `B` is never attempted either; three `.bp` references in
>   `PARAVIEW_GUIDE.md` and one printed by the example were therefore dead.
>   Diagnosed, **not fixed** (code, outside a doc chunk): known-issues entry
>   filed, guide now states the format is unavailable, the false print
>   removed. (ii) `mri:1`'s phantom aggregates have legitimately moved since
>   the 2026-08-04 record (|E| max 2.884886e+02 → 3.200140e+02) because
>   sampling coverage went 239/493 → 493/493; the solve itself is unchanged,
>   which is why the centerline and residual match exactly. The `.msh` claim
>   could not be made true — no code path writes one, `MeshGenerator` hands
>   the gmsh model straight to `gmshio` — so that step now points at the
>   combined XDMF, which a run does produce. The 2026-02-18 PNG was
>   **regenerated** rather than deleted (from the same run that produced the
>   gate numbers) and its provenance is now stated where it is referenced.
>   *(Original plan text follows.)* fix `mri:1`'s docstring
>   ("`TH-6` has not landed" — it closed 2026-07-31) and label it honestly
>   as the ungated end-to-end demo; delete or regenerate the 2026-02-18
>   `straight_wire_validation.png` (predates the example's 2026-08-03
>   rewrite); fix `PARAVIEW_VALIDATION_GUIDE.md`'s reference to the removed
>   `03_helmholtz_coil.py` and `MESH_DIAGNOSTIC_GUIDE.md:84`'s false
>   "saves `straight_wire.msh`" claim. Gate: a grep-style check that guides
>   reference only files a run actually produces, plus re-run of `-e 1` and
>   `-e mri:1` via the runner with their on-record numbers re-asserted.
>   *(Audit note, 18:00 review 2026-08-09: compliant, no demotion — but the
>   negative control mutates two knobs at once (`--max-age-s 1` **and** an
>   empty `--output-dir`), so the not-exists branch fires first and the
>   freshness branch — the script's stated raison d'être — is written but
>   never exercised; no log contains "stale". Folded into `EX-14`.)*
>
> **`EX-11` ✅ 2026-08-09 (06:00 slot, §9 item 2).**
> `examples/materials/01_dodd_deeds_coil_loading.py` lands and reproduces the
> `MAT-6` step-3 record through the example path at every printed digit. Gate
> `./run_examples.sh -e mat:1 -n 2 -t 180`
> (`20260809T110326Z_EX-11-gate.log`, exit 0, 74 s harness-wall / 70.8 s
> example-internal, standard tier, complex build sourced by the runner — the
> log line reads `(complex build)`), preceded by `./run_examples.sh --list`
> (`20260809T110317Z_EX-11-runner-list.log`, exit 0, 1 s), which enumerates
> `mat:1 -> examples/materials/01_dodd_deeds_coil_loading.py` under
> "materials (complex build, sourced automatically)" — the `EX-1` runner gap is
> not repeated. **A new runner group.** The example needs the complex build but
> is not an MRI case, so `scripts/run_examples.sh` gains a fourth group,
> `mat:` → `examples/materials/`, sourced complex exactly like `mri:` and
> included in `-e all`; `mesh:`/`mri:`/magnetostatics dispatch is untouched.
> Measured, against the step-3 record: **138 619 cells** (the record's count),
> mesh 10.8 s, solves 29.4 s / 26.9 s, `I' = 0.919666` A,
> ΔZ = **+3.2770406e-01 + j(−5.6657895e-01) Ω** against exact
> +3.2259615e-01 + j(−6.1586749e-01) Ω → ΔR **1.5834%** and ΔX ratio
> **0.9200** — every figure byte-matching `MAT-6` step 3, so the example path
> and the gate path are the same computation. Gated here at 2% on ΔR (the §7
> `EX-11` plan's ceiling; the gate's own is 5%), plus the two signs (ΔR > 0,
> ΔX < 0). ΔX is printed and explicitly *not* gated — unconverged in box size
> at W = 0.15 per step 3. Two things the gate does not have: (i) the ohmic
> power in the slab from the *solved field*, `∫_slab (σ/2)|E|² dV` =
> **1.385836e-01 W**, against `½ ΔR I'²` = 1.385836e-01 W from the reaction
> integral — ratio **1.0000**, a Poynting-side reading of the same physics
> (analytically equivalent, so it is reported, not gated); (ii) the |J| array
> ParaView colours by is checked, not merely written — **max |J| = 6.8396e+02
> A/m²** loaded. Negative control, in-fixture and free: the σ = 0 half of the
> same solve pair dissipates **exactly 0.0 W** and carries **exactly 0.0 A/m²**
> of eddy current (asserted `== 0.0`, no tolerance — with σ zero cell by cell
> the integrand is identically zero), against the loaded solve's finite values:
> total separation. Every constant, the mesh, the azimuthal drive and the solve
> itself are **imported** from `test_dodd_deeds_impedance.py` /
> `test_dodd_deeds_projected_drive.py` rather than restated. **Closes nothing
> physics-side:** 10 MHz, eddy-current regime; no Larmor/saline claim (§2.1),
> and the example's report text says so on screen. Feeds `ANS-1`, which now has
> its compute path on record, but does not start it.

**`EX-15` — every runnable example gets a step-by-step analysis guide**
*(operator directive 2026-08-10, interactive session; three runs, one per
step, standard tier, doc-only apart from the checker extension; the daily
review queues step 1 at its next §9 refresh and the later steps as slots
free).* Policy now stated in §5.4: every script `./run_examples.sh --list`
enumerates ships with a **same-stem guide page** next to it
(`01_lossy_plane_wave.py` → `01_lossy_plane_wave.md`) that a reader can
follow without the source open, with three required sections: **(1) What
this demonstrates** — the physics, and which §7 gate / closed form anchors
it; **(2) How to run it** — exact runner command, tier, expected wall time
on record; **(3) How to analyze it, step by step** — which artifacts to
open in ParaView and what to look at, which printed numbers to check,
their on-record values with log provenance, and what a deviation in each
would mean. Group-level guides (`PARAVIEW_GUIDE.md` and friends) stay but
do not satisfy the per-example requirement. Fourteen runnable scripts at
scoping time; the split below is by runner group. *(Count correction,
2026-08-10, 18:00 review: the step-2 run measured **16** runnable scripts —
examples landed after scoping (`EX-9`'s `-e 6` among them) were picked up by
the `--list` glob automatically. The guide requirement follows `--list`, not
this paragraph's snapshot; step 3's four `PENDING_GUIDES` entries still
empty the dict, and the two post-scoping scripts already carry guides —
that is how the step-2 gate reads 12 checked + 4 pending at 16 total.)*
- **Step 1 — checker + template + `mesh:`/magnetostatics (5 scripts).**
  Extend `scripts/testing/check_example_doc_references.py` with a guide
  pass: every `--list` entry must have its same-stem `.md` containing the
  three required headings (existing reference/freshness passes untouched).
  **Anchor:** checker exit 0 with the pass on and all five guides present;
  **negative control, two-sided:** one guide temporarily absent → exit 1
  naming the orphaned script, and one guide missing a required heading →
  exit 1 naming the heading; both restored before commit.
- **Step 2 — `th:` group (5 scripts).** Every stated number is the gate
  record already in §7 (`EX-4`–`EX-7`, `th:5`), cited by log name, digit
  for digit. Same checker gate.
- **Step 3 — `mat:`, `mri:`, `ans:` (4 scripts).** The `ans:1` guide
  points at the case's `SPEC.md`/`COMPARISON.md` rather than duplicating
  them; the `mri:1` guide keeps `EX-12`'s "ungated end-to-end demo"
  labelling.

> **`EX-15` step 1 ✅ 2026-08-10 (04:30 slot, §9 item 1) — guide pass live,
> five guides landed, both negative controls fired.** The pass asks
> `scripts/run_examples.sh --list` for the example set (no second list to keep
> in sync) and requires the three headings.
> **Anchor:** `20260810T093807Z_EX-15-step1-refcheck-final.log`, exit 0, 1 s —
> 14 examples enumerated, **5 checked against 3 required headings**, 9 pending,
> `EX-12` reference pass green alongside (12 guides, 31 references).
> **Negative controls:** guide absent → exit 1 naming
> `examples/meshing/02_cylindrical_phantom.py`
> (`…093747Z_EX-15-step1-negctl-missing-guide.log`); heading absent → exit 1
> naming `How to run it` (`…093757Z_…-negctl-missing-heading.log`). Both
> mutations reverted inside the same container invocation and verified
> restored.
> **Decision the step-1 bullet did not resolve:** exit 0 is unreachable while
> steps 2–3 owe nine guides (first run flagged all nine,
> `…093635Z_EX-15-step1-refcheck.log`, exit 1), so those nine sit in a
> `PENDING_GUIDES` dict, each naming its owing step; an entry whose guide
> *exists* is itself a violation, so steps 2–3 must delete their entries in the
> commit that adds the guides. Steps 2–3 unchanged otherwise.
> **Numbers:** `mesh:` guides copy the docstring records; the three
> magnetostatics guides cite the one licensed refresh
> `20260810T093203Z_EX-15-step1-refresh-allmag.log` (exit 0, 204 s, `-n 2`) —
> `-e 1` 65.8739% / 85.2498% (identical to `20260804T174037Z_MAG-EX.log`),
> `-e 2` 6.3046% / 13.5037% at 411 393 cells, `-e 4` centre rel err
> 0.89% → 0.24% → 1.28% over h/a = 1.00 / 0.70 / 0.50. Each guide names the
> gate its example is **not** (`MAG-13` 12.75% / 7.07%, `MAG-14` 0.728%).
> **Finding, recorded not acted on:** `-e 4`'s centre error is non-monotone in
> `h` — the systematic-floor signature its own docstring predicts, stated as
> the result in the guide; `MAG-14` is a different fixture and is unaffected.

> **`EX-15` step 2 ✅ 2026-08-10 (16:30 slot, §9 item 4) — the five `th:` guides
> land, and the group is the first to cost nothing to gate.** Guides for
> `th:1`…`th:5` written to the step-1 bar (three required sections, on-record
> numbers copied from the `EX-4`…`EX-8` §7 records and cited by log name), and
> the five step-2 `PENDING_GUIDES` entries deleted in the same commit.
> **Anchor:** `20260810T213556Z_EX-15-step2-refcheck-final.log`, exit 0, 0 s —
> **12** of 16 runnable examples now checked against 3 required headings (was
> 5), 4 pending, reference pass green alongside at 19 guides / 60 distinct
> references / 1 allowlisted. The pre-mutation run
> (`…213519Z_EX-15-step2-refcheck.log`, exit 0, 1 s) is identical.
> **Negative control:** the heading side re-fired on a step-2 guide —
> `## 2. How to run it` renamed in `01_lossy_plane_wave.md` → exit 1,
> `missing required heading 'How to run it'`
> (`…213543Z_EX-15-step2-negctl-heading.log`), mutation reverted inside the same
> container invocation and verified byte-identical on the host afterwards (clean
> `git status` for that path, heading restored at line 50).
> **`OPS-15` paid off exactly as scoped:** all three checker runs took **zero**
> refresh solves — the oldest `th:` artifact (`lossy_plane_wave_combined.xdmf`,
> 2026-08-09 09:05 local) is ~36.7 h old, under the new 48 h default and well
> over the retired 1 h one, which would have forced five `-e th:*` refreshes.
> Doc-only apart from the five-line `PENDING_GUIDES` deletion; no `src/` change,
> no solve, no gate re-run owed.
> **Two notes for the next reader.** The `th:4` guide restates the §9 scope
> correction explicitly — `TH-7` gates the evanescent TE₁₀ decay, and no line
> impedance or S-parameter claim is made or implied (`PORT-1` owns that, §2). And
> the runnable-example count is **16**, not the 14 this chunk's scoping text
> records — examples landed after scoping (`EX-9`'s `-e 6` among them) and the
> `--list` glob picked them up automatically; which two is not diagnosed here,
> and it does not change step 3, whose four entries still empty the dict.
> **Finding, none:** every one of the five guides was writable to the section-3
> bar from the existing records without re-running its example, so the
> journal-don't-thin clause did not fire.

> **`EX-15` step 3 ✅ 2026-08-11 (06:00 slot, §9 item 2) — the last four guides
> land, `PENDING_GUIDES` is empty, and the chunk closes.** Guides for `mat:1`,
> `mri:1`, `mri:2` and `ans:1` written to the step-1 bar (three required
> sections, on-record numbers copied from the `EX-11` / `EX-16` / `EX-3` /
> `ANS-1` §7 records and cited by log name), and the four step-3
> `PENDING_GUIDES` entries deleted in the same commit — the dict is now `{}`,
> with a comment recording that a new example must ship its guide with it.
> **Anchor:** `20260811T110627Z_EX-15-step3-refcheck-final.log`, exit 0, 1 s —
> **16 of 16** runnable examples checked against 3 required headings (was 12),
> **0 pending**, reference pass green alongside at 23 guides / 74 distinct
> references / 1 allowlisted.
> **Negative control:** the heading side fired on a step-3 guide —
> `## 2. How to run it` renamed in `01_dodd_deeds_coil_loading.md` → the checker
> reports `missing required heading 'How to run it'` and the sentinel prints
> `NEGCTL RESULT: exit 1 — expected`
> (`20260811T110641Z_EX-15-step3-negctl-heading.log`); mutation reverted inside
> the same container invocation and the heading verified present on the host
> afterwards.
> **The reference pass caught a real defect in the new prose**, which is worth
> recording because it is the pass doing its job on first use against fresh
> text: the first run
> (`20260811T110554Z_EX-15-step3-refcheck.log`, exit 1, 1 s) flagged two dead
> references, `_B.xdmf` and `_E.xdmf`, from an ellipsis shorthand
> (`` `…_B.xdmf` ``) in the `mri:1` guide. Fixed by naming
> `mri_coil_phantom_fields_B.xdmf` / `…_E.xdmf` in full — a guide "a reader can
> follow without the source open" cannot abbreviate a filename anyway. Guide
> pass was already 16/16 green on that same run, so the two passes are
> independent as designed.
> **Zero solves, zero refresh tax:** all three checker runs ran at
> `--max-age-s 172800`; `OPS-15`'s 48 h default covers every artifact the four
> guides cite, so no example was re-run. Doc-only apart from the six-line
> `PENDING_GUIDES` edit; no `src/` change, no gate re-run owed.
> **Two notes for the next reader.** The `mri:1` guide is the awkward one and
> was written to be honest rather than tidy: it keeps `EX-12`'s **ungated
> end-to-end demo** labelling in the title and section 1, states in section 1
> that no printed number is evidence, cites the **converged** `EX-16` record
> (`preonly`/LU `reason=4` at `gauge_penalty=1.0`, 9261 cells, the tag counts
> and the phantom aggregates), and carries the still-open centerline caveat as
> its own subsection — 23.5539% centerline spread across `-n 2`/`-n 4` against
> **0.007326%** on the phantom-region sampler over the same fields, known-issues
> entry open, assigned `POST-4`. Its per-quantity table marks each row
> rank-stable or not, and step 5 tells the reader to read the centerline block
> last. And the `ans:1` guide deliberately **does not** duplicate `SPEC.md` or
> `COMPARISON.md`: it opens by naming them as authority-for-the-problem and
> regenerated-result respectively, and covers only how to run the script and
> read its output — including that `COMPARISON.md` is rewritten by every run and
> must not be hand-edited except to fill the AED columns.
> **Finding, none:** all four guides were writable to the section-3 bar from the
> existing records without re-running their examples, so the journal-don't-thin
> clause did not fire in any step of this chunk.

**Traps:** on-record numbers are *copied* from §7/gate records, never
re-measured — no solves are licensed here (checker runs are ~1 s; at most
one `-e` refresh if the freshness branch fires, as it did twice on
2026-08-09/10); `mri:1`'s numbers move if `EX-16` lands first (`EX-13`
closed negative 2026-08-10; `EX-16` owns the record refresh) — write that
guide after `EX-16`, or state the unconverged-solve caveat explicitly; the sibling
`.md` files land next to scripts, so make sure the checker does not
mistake them for referenced-artifact entries. **Does not close:** nothing
physics-side; documentation surface only. **Negative result:** a guide
that cannot be written to the section-3 bar without re-running its example
means that example's record is under-documented — journal it as a finding
against the example, not a reason to thin the guide.

**`EX-13` — `examples/mri/01` at the validated gauge floor** *(scoped
2026-08-09, 18:00 review — this is the review decision the `MAG-6` step-5
finding asked for, taken; one run, standard tier).* The one example that
still solves below the validated `gauge_penalty=1.0` floor is the
operator-facing end-to-end demo, and it carries on-record numbers
(`examples/mri/01_coil_phantom_fields.py:302` and `:334`). Change both
call sites `1e-3 → 1.0`; run `./run_examples.sh -e mri:1` at `-n 2` and
`-n 4` at the floor, and the same pair sub-floor (four runner invocations,
~10 s each on record from the `EX-12` baselines), then refresh every
on-record string in the file and any guide the change staled, and finish
with `scripts/testing/check_example_doc_references.py` (1 s) green.
**Anchor:** the `-n 2` vs `-n 4` maximum relative spread across the five
centerline (|E|, |B|) pairs at the floor, asserted **< 5%** — the `MAG-6`
gate fixture measured 0.024% (centerline) / 0.001% (mirror) there, so 5%
is two orders above the expected reading and well under the sub-floor
scatter scale (88% on the gate fixture). **Negative control:** the same
spread measured sub-floor in the same slot; report both. If the sub-floor
spread is not clearly larger (≥ 2× the floor spread), do **not** claim
discrimination — that outcome means the example's DG0 sampling already
suppresses gauge scatter, which is itself the finding: report it and stop.
**Tier/cost:** standard, `-n 2`/`-n 4`, ≈ 1 min of compute total plus
edits. **Traps:** the `mri:` group sources the complex build itself;
`residual_norm` and the phantom aggregates *will* move at the floor —
that is the point, not a regression, and the new numbers become the
record; `EX-12` just relabelled this file, so keep its "ungated
end-to-end demo" labelling intact. **Does not close:** `WF-1` stays 🧪 —
this example still asserts no physics against a closed form; the spread
assertion gates only rank stability of the sampling. **Negative result:**
a floor solve that fails to converge or a spread ≥ 5% is a finding
against the floor-on-this-fixture assumption — report in a §7 annotation,
leave the example sub-floor, known-issues entry.

> **`EX-13` 🟡 2026-08-10 (00:00 slot, §9 item 4) — executed, both legs
> negative; the example stays sub-floor and the chunk needs a review
> decision.** The four runner invocations ran as planned
> (`20260810T050120Z_EX-13-subfloor-n2.log`, `…050133Z_EX-13-subfloor-n4`,
> `…050150Z_EX-13-floor-n2`, `…050157Z_EX-13-floor-n4`; all exit 0, 6/4/4/4 s,
> standard tier), and the spread computation over the four logs is
> `20260810T050319Z_EX-13-spread.log` (exit 0).
>
> 1. **The anchor fails, by a factor of five.** Max `-n 2` vs `-n 4` relative
>    spread across the five centerline (|E|, |B|) pairs **at the floor is
>    23.5545%** (|B| at z = +0.0225 m: 4.055231e-07 vs 5.304733e-07), against
>    the asserted **< 5%**. The largest |E| spread is 15.6832% (z = +0.0450 m).
>    So the `MAG-6` gate-fixture reading of 0.024% does **not** transfer to this
>    example: the gate samples a converged wire fixture, this example samples a
>    coarse unconverged coil+phantom solve.
> 2. **No discrimination, and the reason is structural.** Sub-floor max spread
>    is **23.3010%** — ratio sub-floor/floor **0.9892×**, where the plan
>    required ≥ 2× to claim discrimination. The five |E| spreads are
>    *bit-identical* between floor and sub-floor because
>    `TimeHarmonicSolver.solve` accepts `gauge_penalty` for call-site
>    compatibility and **ignores it** (`core/time_harmonic.py:351`) — so the
>    plan's "both call sites" premise is half-inert: only the magnetostatic
>    site can move a number, and it moves |B| by < 0.6% at the centerline.
>
> Per the entry's negative-result clause the gauge edits were reverted and the
> example is left sub-floor at `1e-3`; known-issues entry filed. **What the
> review must decide:** (a) whether the floor change lands anyway on its merits
> — it is nearly free here (E unaffected by construction, |B| ≤ 0.6%) but
> cannot be justified by *this* anchor; and (b) whether a rank-stability anchor
> on this fixture is salvageable at all, or whether the finding is simply that
> an unconverged GMRES (`converged=False (reason=-3)`, `ksp_max_it=180`,
> identical `residual_norm=1.684628e+00` at every rank count) produces a
> partition-dependent iterate that no gauge setting can quiet. The 23% is a
> property of the demo, not of the gauge.
>
> Not touched: `WF-1` stays 🧪 as scoped; the doc-reference checker was run
> (`20260810T050349Z_EX-13-refcheck.log`) and exits 1 on
> **artifact-freshness** for five `straight_wire*` files, unrelated to this
> chunk — see the `EX-14` note below.

> **`EX-13` 🚫 2026-08-10 (03:00 review) — both owed decisions taken; the
> chunk closes negative and `EX-16` inherits the salvage.** (a) The
> gauge-floor change does **not** land on this chunk's evidence: it is inert
> on the E leg by construction (the solver ignores `gauge_penalty`) and
> < 0.6% on |B| — a change justified only by "harmless" is churn against
> on-record numbers that would have to be refreshed inside 23% rank noise.
> It rides `EX-16` instead, so the record strings refresh once, on a
> converged solve. (b) The rank-stability anchor is **not salvageable on
> this fixture as-is**: an iterate returned at `ksp_max_it` with
> `converged=False (reason=-3)` is partition-dependent no matter the gauge —
> the 23% measures the unconverged GMRES, not the sampling. The salvage is
> to make the solve converge and re-measure, scoped as `EX-16` below; the
> known-issues entry is reassigned there. Do not re-run `EX-13` as written.

**`EX-16` — `examples/mri/01`: converge the frequency-domain solve, then
re-measure the rank spread** *(scoped 2026-08-10, 03:00 review — the two
decisions the `EX-13` negative result asked for, taken; one run, standard
tier).* The demo's time-harmonic leg overrides the solver's default direct
path (`ksp_type=preonly` + MUMPS, `core/time_harmonic.py:445` — the path
every `TH-6`/`TH-7`/`TH-8` gate solves through) with GMRES+Jacobi at
`ksp_max_it` 180–450 (`examples/mri/01_coil_phantom_fields.py:340`), and
that iteration stops at `reason=-3`, `residual_norm=1.684628e+00` on the
debug preset — the returned iterate is what `EX-13` measured as 23%
partition-dependent. Fix: drop the override (or pass the direct options
explicitly) so the debug/coarse presets solve direct — 9261 cells of
degree-1 N1curl is trivially within MUMPS range; keep
`collect_solver_diagnostics=True` and require `converged=True` before any
spread claim. In the same motion, flip the **magnetostatic** call site
(`:317`) `1e-3 → 1.0` — the `EX-13` decision (a) rider — then re-run the
`EX-13` measurement verbatim (`mri:1` at `-n 2`/`-n 4`), refresh every
on-record string in the file and any guide that staled, and finish with
`check_example_doc_references.py` green. **Anchor:** the `-n 2` vs `-n 4`
max relative spread across the five centerline (|E|, |B|) pairs on a
**converged** solve, asserted **< 5%** (KSP `converged=True` is the
precondition, not the anchor — a convergence flag alone closes nothing
under §4). **Negative control, cite not recompute:** the unconverged
record — 23.5545% floor / 23.3010% sub-floor
(`20260810T050319Z_EX-13-spread.log`); the arithmetic ceiling on
separation is 23.55/5 ≈ 4.7×, so assert < 5% and report the measured
ratio; do not erect a 10× bar the fixture cannot show. **Tier/cost:**
standard, two runner invocations ≈ 10 s each on the `EX-13` record; the
direct solve may cost more than the truncated GMRES but nothing near the
180 s ceiling at 9261 cells. **Traps:** the `mri:` runner sources the
complex build itself; `gauge_penalty` is ignored by
`TimeHarmonicSolver.solve` (`EX-13` finding) — make no gauge claim on the
E leg; the on-record strings *will* move, that is the point and the new
numbers become the record; keep `EX-12`'s "ungated end-to-end demo"
labelling intact; the `mri:1` guide (`EX-15` step 3) should be written
after this lands or carry the caveat. **Does not close:** `WF-1` stays
🧪 — the demo still asserts no physics against a closed form; the spread
anchor gates sampling stability only. **Negative result:** a converged
solve that still spreads ≥ 5% is a real finding against the centerline
sampling path — report both numbers, keep the known-issues entry open,
stop; a debug-preset solve that cannot converge direct is a finding
against the demo fixture itself — known-issues update, stop.

> **`EX-16` 🚫 2026-08-10 (12:00 run) — the fix works, the anchor fails, and
> the convergence hypothesis is refuted.** Both edits landed: the
> GMRES+Jacobi override is gone (the demo now reports
> `ksp=preonly, pc=lu, converged=True (reason=4)` at both rank counts, from
> `converged=False (reason=-3)`, `residual_norm=1.684628e+00`), and the
> magnetostatic gauge penalty is `1.0`. The `-n 2` vs `-n 4` centerline
> spread is **23.5539%** against the < 5% anchor — **1.0000×** the 23.5545%
> unconverged record it was supposed to beat
> (`20260810T170457Z_EX-16-spread-v2.log`; runs
> `…170234Z_EX-16-direct-n2.log` / `…170309Z_EX-16-direct-n4.log`, 6 s and
> 4 s, standard tier). Converging the KSP moved only the |E| leg, 15.6832%
> → 13.4499%; the anchor's max is carried by the **magnetostatic |B|** leg,
> which no frequency-domain change can touch. **The decisive measurement is
> the added positive control:** on the same two runs and the same fields,
> the 493-point phantom-region sampling path agrees across rank counts to
> **0.007326%** — **3215×** tighter than the centerline path. Same solve,
> same field, two samplers, so the defect is the **centerline
> point-evaluation path**, not the solve, the KSP or the gauge; the likely
> mechanism is on-axis points (x = y = 0) sitting on shared mesh edges,
> exactly what `MAG-6` step 4 characterised. Per the entry's
> negative-result clause: reported, known-issues entry stays **open** and
> is re-pointed at `evaluate_vector_field_parallel` (currently
> unassigned — a review must scope it; it is solver-side work, not an
> example edit). The code change lands anyway on its own merits (a
> converged solve and the validated gauge floor are strictly better than a
> truncated iterate at a sub-floor penalty) and the example's on-record
> strings are refreshed to the converged numbers. `WF-1` stays 🧪 as
> scoped. Doc-reference checker: **green at exit 0** with
> `--max-age-s 172800` (`…170630Z_EX-16-refcheck-maxage.log`); the default
> 1.0 h window still fails 14 references on the standing freshness tax
> (`…170614Z_EX-16-refcheck.log`) — all magnetostatics artifacts 3.0 h old,
> nothing dead, nothing this chunk touched. That is exactly what `OPS-15`
> (§9 item 2) retires.

**`EX-17` — circular-loop VTX export repair: port the `EX-14` diff, same
round-trip anchor** *(scoped 2026-08-10, 10:30 review, from the finding
`EX-14` filed and correctly did not fix; one run, standard tier; fixes the
2026-08-10 known-issues entry).* `examples/magnetostatics/02_circular_loop.py:214`
carries the identical defect `EX-14` repaired in the straight-wire example:
the first `io.VTXWriter` is handed the N1curl `A`, one `try` wraps both
writers so `B` is never attempted, and the on-disk
`paraview_output/circular_loop_A.bp` probes to **zero ADIOS2 variables**
(probed in-container 2026-08-10). Fix is a one-file port of the `EX-14`
diff (`f626171`, `01_straight_wire.py` hunks): hand the writers the
Lagrange interpolants the example already builds, split the `try`, add the
same `_check_vtx_roundtrip()` (allreduced in-memory max |B| vs the rank-0
ADIOS2 read-back, verdict broadcast), then re-run `-e 2` and finish with
the doc-reference checker green. **Anchor:** the round-trip identity —
read-back max |B| equals the in-memory value, relative difference
asserted < 1e-10 (`EX-14` record on the straight wire: 0.000e+00,
bit-identical, `20260810T140337Z_EX-14-gate-mag1-v2.log`). **Negative
control, cite not recompute:** the pre-fix state is on record — the
zero-variable `.bp` in the known-issues entry, and the `⚠ VTX output
failed … Only (discontinuous) Lagrange functions are supported` print
class every unfixed `-e` log carries. **Tier/cost:** standard declared,
`-n 2`, but budget `-t 600`: `-e 2` builds the 411 393-cell mesh — the
expensive magnetostatics example, ~100–130 s inside the 204 s all-mag
refresh on record (`20260810T093203Z_EX-15-step1-refresh-allmag.log`);
expect one run, no slack for a second at standard's 180 s. **Traps
already paid for:** VTX point data is an ADIOS2 *local* array with empty
`Shape` — walk `BlocksInfo`, not `Shape` (`EX-14`'s first attempt died on
this, then segfaulted at teardown, exit 139); `.bp` is a directory —
`artifact_mtime()` already handles its mtime, do not re-fix; the
freshness branch may fire on other artifacts at the current 1.0 h default
if `OPS-15` has not landed — one refresh licensed (~80–200 s, exclude
`-e 2` from it since this run just produced those artifacts); real build,
no complex sourcing. **Does not close:** nothing physics-side — the
loop's analytic numbers (6.3046% / 13.5037% on record) are `MAG-EX`'s and
must not move; guide `02_circular_loop.md` gains the working `.bp`
references only. **Negative result:** a round-trip mismatch on the loop
where the wire was bit-identical is a finding about the loop's export
path specifically — report both numbers, keep the known-issues entry
open, stop.

> **`EX-17` ✅ 2026-08-10 (15:00 slot, §9 item 3) — the port carries, and the
> loop's round trip is bit-identical too.**
> The diff is the `EX-14` one, line for line: `02_circular_loop.py` hands both
> `VTXWriter`s the `A_lag`/`B_lag` interpolants it already builds, each writer
> gets its own `try`, and `_check_vtx_roundtrip()` reads `circular_loop_B.bp`
> back through ADIOS2 on rank 0 with the verdict broadcast. The `BlocksInfo`
> trap the entry pre-paid for was real and pre-solved — the ported read-back
> worked first attempt, no `AxisError`, no exit 139.
> **Anchor:** in-memory **7.756122914931e-05 T**, read-back
> **7.756122914931e-05 T**, relative difference **0.000e+00** against 1e-10 —
> bit-identical, matching the straight wire's result on a mesh 30× larger
> (`20260810T200154Z_EX-17-gate-mag2.log`, exit 0, **124 s**, `-n 2`, standard
> declared with the `-t 600` budget the entry allowed; one run, no second solve).
> **Negative control, cited not recomputed:** the zero-variable
> `circular_loop_A.bp` and the `⚠ VTX output failed … Only (discontinuous)
> Lagrange functions are supported` print class, both on record in the
> known-issues entry this commit retires; the run now prints `✓ Vector
> potential A saved` / `✓ Magnetic field B saved`.
> **Nothing physics-side moved,** as required: relative L2 error **6.3046%**,
> max relative error **13.5037%** at z = +0.0240 m — `MAG-EX`'s numbers, digit
> for digit.
> **Checker green** at the `OPS-15` default, exit 0, both passes PASS
> (`20260810T200519Z_EX-17-refcheck.log`) — and the freshness branch did not
> fire at all, the first `-e` slot since the 48 h default landed that paid no
> refresh tax.

**`EX-18` — gap-voltage port pair → Z → S on the two-torus fixture** ⬜
*(scoped 2026-08-13, 03:00 review, per the §5.4 ramp: `PORT-1` steps
3b-xvii/xviii closed the matched-topology closure gate and the port-pair
mutual gate this interval, and no example demonstrates ports or
S-parameters from a solved field — the `EX-*` set covers magnetostatics,
plane wave, cavity, quasi-static sphere, waveguide, coil-phantom fields,
SAR and Dodd–Deeds, nothing port-side. Queued as §9 item 2; full
rubric-complete recipe there.)* One example under `examples/ports/`
(new family), runner-registered, `./run_examples.sh` dispatched: build
the gapped two-torus fixture (padding 0.08, 178 055-cell class), solve
both drives at σ = 800 S/m, read `Im Z₁₂` by the gap-voltage route,
apply the two named systematics (PEC box `D∞ = +0.0169` at p = 1.657,
effective-range; gap physics ÷(1 − 0.030224), Jin §10.4.2.1), convert
through `sparameters_from_impedance()` at Z₀ = 50 Ω, and write
combined-XDMF that opens in ParaView. **Done-when (per the `EX-*`
common rules):** runner-dispatched harness log asserting the allreduced
reproduction of the 3b-xviii gated digits — raw 0.894283 × ωM₁₂,
corrected 0.939581 (−6.04% inside the unmoved 10%), ‖S−Sᵀ‖/‖S‖ ≈
2.5494e-05, ‖S‖₂ = 0.861449 ≤ 1 — with tolerances citing
`20260813T020352Z_PORT-1-step3bxviii-pairgate-n2.log` (looser allowed,
never tighter); combined-XDMF written; elapsed recorded. Demonstrates
gated capability only; `PORT-1` stays 🟡 and the correction-ladder
composition question stays the weekly review's.
>
> **`EX-18` ✅ 2026-08-13 (06:00 slot, §9 item 2) — the port lineage is
> demonstrable, and the example prints the miss first.**
> `examples/ports/01_two_torus_port_pair.py` + guide, a new `ports:` runner
> group (`./run_examples.sh -e ports:1`, complex build sourced automatically
> like `mri:`/`th:`/`mat:`/`ans:`), runner-dispatched through the harness:
> `20260813T110940Z_EX-18-example-n2-v3.log`, **exit 0, 135 s**, `-n 2`,
> standard tier — mesh 36.1 s / 178 055 cells, solves 22.0 + 22.5 s.
> **Reproduced on `main`, allreduced:** raw **0.894543** × ωM₁₂ (−10.55%,
> printed first and labelled a miss — the unmoved 10% band would reject it),
> + PEC box 0.911443, + gap physics **0.939849 (−6.02%)**; reciprocity
> |Z₁₂−Z₂₁|/|Z₁₂| = 5.8343e-04 printed; **‖S−Sᵀ‖/‖S‖ = 2.5494e-05** and
> **‖S‖₂ = 0.861449** — both the 3b-xviii digits to every printed figure.
> The raw ratio lands on the 3b-xi padding-sweep digit 0.894543 rather than
> 3b-xviii's 0.894283 (2.6e-4 apart, inside the declared 2e-3 reproduction
> band); same fixture, same padding — the spread is partition/lineage, not
> drift.
> **Negative control, cited not recomputed:** step 1's unfragmented fixture's
> `Im Z₁₂ ≡ 0` run through the same ladder reads **−98.26%** and is asserted
> *to fail* the band.
> **The lift:** `PEC_BOX_SYSTEMATIC` / `PEC_BOX_SYSTEMATIC_EXPONENT` /
> `GAP_PHYSICS_SYSTEMATIC` and the ladder moved out of
> `tests/validation/test_port_gap_voltage_impedance.py` into
> **`src/fem_em_solver/ports/systematics.py`**, so the example and the gate
> share one definition instead of two copies of three constants. The test
> keeps the module-level names (every sibling module's reference reads as it
> did when the numbers were measured) and keeps `passes` alone, since
> `MUTUAL_TOLERANCE` is that module's band, not a property of the
> systematics. `test_lifted_systematics_ladder_is_bit_identical` asserts the
> lift with `==` — not a tolerance — against the literals and the expression
> as they stood, at four inputs including the blind fixture's zero
> (`20260813T110626Z_EX-18-ladderlift.log`, exit 0, 3 s).
> **Two misses on the way, both the example's and both real:** (1) the
> pre-solve terminal-angle check first used the *area-weighted* ⟨y⟩ and read
> 0.173852 against 0.175335 — that is known-issues 11 (lateral strips the tag
> picks up at `gap_overhang = 2e-4`), not a geometry drift, and the gate
> module's *extreme*-y form was ported instead; (2) the quadrature
> precondition was applied to both ports and the **driven** one failed at
> 2.26e-02 — step 3b-x's standing disposition gates the undriven port and
> prints the driven diagonal, because the driven path runs through the
> impressed source's own terminals. Neither tolerance was moved.
> **Does not close** `PORT-1` (stays 🟡): no `S₁₁` claim (step 2b's
> electric-energy excess), no birdcage ports, and the correction-ladder
> composition question stays the weekly review's.

**`EX-14` — straight-wire VTX export repair and the refcheck freshness
branch exercised** *(scoped 2026-08-09, 18:00 review; one run, standard
tier; fixes the `EX-12` known-issues entry and the audit gap in the same
motion).* The `.bp` export in `examples/magnetostatics/01_straight_wire.py`
has never worked: `VTXWriter` is handed the N1curl `A`, and one `try`
wraps both writers, so the writable `B` is never attempted (known-issues,
2026-08-09). Fix: hand the writers the `A_lag`/`B_lag` Lagrange
interpolants the example already builds, split the `try` so each writer
fails independently, restore the three `.bp` references
`PARAVIEW_GUIDE.md` lost, and re-run `-e 1`. **Anchor:** read the written
`.bp` back through the ADIOS2 Python bindings in-container and assert the
allreduced max |B| of the round-trip equals the in-memory value to 1e-10
— a closed-loop identity on the artifact itself, not a finiteness check.
**Negative control, two-sided:** (i) the pre-fix state is on record — the
`⚠ VTX output failed` print in every `-e 1` log since 2026-08-04; (ii)
run the checker against the **real** `paraview_output/` with
`--max-age-s 1` some seconds after the run: the files exist but are
stale, so this exercises the freshness branch the `EX-12` negctl skipped
(empty dir fired the not-exists branch first) — assert it flags the
artifacts and exits 1, and that the normal invocation passes at exit 0.
**Tier/cost:** standard; `-e 1` is 8 s on record, checker 1 s. **Traps:**
`VTXWriter` accepts only (discontinuous) Lagrange — that is the original
defect, do not hand it `A`/`B`; if the ADIOS2 Python read-back API is
absent from the container, that halves the anchor — report, keep the
known-issues entry open for the read-back half, and gate on the
writer-succeeds + freshness pair alone, holding the chunk 🟡. **Does not
close:** nothing physics-side; doc/example hygiene plus one artifact
identity. **Negative result:** a round-trip mismatch is a real I/O
finding — report the two numbers, stop, known-issues entry.
>
> *(2026-08-10, 00:00 slot: the freshness branch was observed firing
> unprompted, at the **default** `--max-age-s`, in
> `20260810T050349Z_EX-13-refcheck.log` — five `straight_wire*` references
> flagged "stale in paraview_output/ (1.5 h old, limit 1.0 h)", exit 1, with
> no `--max-age-s` override. Two consequences for this chunk: the negative
> control is easier than scoped — no `--max-age-s 1` gymnastics needed, just
> let the artifacts age — and the checker is **not** a standing tree gate,
> since it goes red on any tree whose examples were last run over an hour
> ago. Whether `EX-12`'s "finish with the checker green" step is even
> achievable outside the slot that ran the examples is a question this chunk
> should settle.)*

> **`EX-14` ✅ 2026-08-10 (09:00 slot, §9 item 4) — the export works, the
> artifact is verified against itself, and the freshness pass had a second
> defect the restored `.bp` references exposed.**
> **The fix** is the one the known-issues entry predicted:
> `examples/magnetostatics/01_straight_wire.py` hands `VTXWriter` the
> `A_lag`/`B_lag` Lagrange interpolants it already builds instead of the
> N1curl `A`/DG `B`, and each writer gets its own `try` (the single block was
> why `B` — always writable — was never attempted). Both `.bp` directories now
> write on every run: `✓ Vector potential A saved` / `✓ Magnetic field B
> saved`, where every log since 2026-08-04 printed `⚠ VTX output failed
> (ADIOS2 may not be available): Only (discontinuous) Lagrange functions are
> supported` — negative control (i), on record and now absent.
> **Anchor, and it is exact.** `_check_vtx_roundtrip` reads
> `straight_wire_B.bp` back through the ADIOS2 Python bindings (2.9.1, present
> in-container) and compares its max |B| with the allreduced in-memory value
> over owned dofs: **4.463805898300e-05 T** both ways, **relative difference
> 0.000e+00** against the 1e-10 tolerance — bit-identical, which is the right
> answer for a lossless round trip, and a closed-loop identity on the artifact
> rather than a finiteness check. A mismatch raises; a missing read-back API
> degrades to a printed warning and `return False`, the 🟡 branch the entry
> licensed, unused. One API note for successors: VTX writes point data as an
> ADIOS2 **local** array (one block per writer rank, `Shape` empty), so the
> read-back walks `BlocksInfo` — asking for a global shape returns nothing and
> was the first attempt's failure (`…140244Z_EX-14-gate-mag1.log`).
> **Negative control (ii) fired, and caught a real defect.**
> `--max-age-s 1` against the *real* `paraview_output/` flagged 14 references
> stale and exited 1 (`20260810T140434Z_EX-14-refcheck-negctl.log`) — the
> freshness branch `EX-12`'s negctl skipped, now exercised. But it also read
> `straight_wire_A.bp` as **158.0 h old** minutes after the run rewrote every
> file inside it: a `.bp` is a *directory*, and overwriting the same entries
> (`data.0`, `md.0`, …) never touches the directory's own mtime, so
> `stat().st_mtime` reports the creation date forever. Restoring the `.bp`
> references would have made the checker permanently red on an artifact no
> rerun could refresh. Fixed in `check_example_doc_references.py` with
> `artifact_mtime()` — newest mtime in the tree for a directory artifact — and
> the same run that had flagged `straight_wire_A.bp` stops flagging it.
> **Green afterwards:** `20260810T140845Z_EX-14-refcheck-green.log`, exit 0,
> both passes PASS (39 references, 7 guides checked / 9 pending), after an
> `-e 4,5,6` freshness refresh (`…140521Z_EX-14-freshness-refresh.log`, exit 0,
> 200 s) cleared seven artifacts left 1.3 h old by earlier slots.
> **The question the entry asked, answered:** `EX-12`'s "finish with the
> checker green" is achievable outside the slot that ran the examples only by
> re-running them — the 1.0 h window is shorter than the 90-minute slot grid,
> so any run that touches example docs must budget a refresh. The checker is
> therefore still not a standing tree gate.
> **Docs:** `PARAVIEW_GUIDE.md` regains its three `.bp` sections (Output Files,
> Method 2, Troubleshooting) with the round-trip numbers and the
> ADIOS2VTXReader instruction; the `EX-15` guide `01_straight_wire.md` swaps
> its "expected failure" block for the round-trip record. Known-issues: the
> straight-wire entry retires. **New entry filed, not fixed:**
> `02_circular_loop.py` carries the identical defect
> (`02_circular_loop.py:214`) — `paraview_output/circular_loop_A.bp` probes to
> **zero ADIOS2 variables**, an empty directory from a failed write — and is
> out of this chunk's scope.
> **Tier/cost:** standard for the example (`20260810T140337Z_EX-14-gate-mag1-v2.log`,
> exit 0, **5 s** at `-n 2`) and 1 s for each checker run; the freshness
> refresh alone was heavy-tier (200 s), declared as such. **Does not close:**
> nothing physics-side, as scoped.

> **`EX-4` ✅ 2026-08-09 (09:00 slot, §9 item 4).**
> `examples/time_harmonic/01_lossy_plane_wave.py` lands — **the first example in
> the repository that runs a time-harmonic solve at all** — and reproduces the
> `TH-6` gate record through the example path at every printed digit. Gate
> `./run_examples.sh -e th:1 -n 2 -t 180`
> (`20260809T140510Z_EX-4-gate.log`, exit 0, 16 s harness-wall / 14.8 s
> example-internal, standard tier, complex build sourced by the runner — the log
> line reads `(complex build)`), preceded by `./run_examples.sh --list`
> (`20260809T140421Z_EX-4-runner-list.log`, exit 0, 1 s), which enumerates
> `th:1 -> examples/time_harmonic/01_lossy_plane_wave.py` under "time-harmonic
> (complex build, sourced automatically)" — the `EX-1` runner gap is not
> repeated. **A new runner group.** `EX-4`…`EX-8` are frequency-domain but
> neither MRI nor materials, so `scripts/run_examples.sh` gains a fifth group,
> `th:` → `examples/time_harmonic/`, sourced complex exactly like `mri:`/`mat:`
> and included in `-e all`; the other four groups' dispatch is untouched. The
> README's runner section gains `th:` **and** the `mat:` line `EX-11` never
> added. Measured, against `20260731T020427Z_TH-6-gate3.log`: closed form
> α = **13.067043** Np/m, β = **27.015150** rad/m (δ = 76.53 mm, αL = 1.307,
> βL = 2.702); coarse 12³ (10 368 cells) rel L2 **7.217852e-02**, fine 24³
> (82 944 cells) rel L2 **3.609441e-02**, measured L2 rate in h **0.9998**, fitted
> α = **13.069460** (**0.0185%**) and β = **27.031165** (**0.0593%**) — every
> figure byte-matching the gate log, so the example path and the gate path are
> the same computation. Gated here at **1%** on both constants (the §7 `EX-4`
> plan's ceiling; the gate's own is the 5% §10 MVP criterion), plus α > 0 (the
> conjugated-convention trap), plus the refinement and O(h) rate so a
> coincidental match at one mesh size cannot pass. **The exported field is the
> gated solve**, not a look-alike: `_solve_plane_wave` gained an additive
> `return_fields=False` kwarg — no assertion in the gate depends on it, and the
> gate was re-run to prove it (`20260809T140531Z_EX-4-TH-6-regress.log`, 6
> passed, exit 0, 25 s, `tests/environment` first). One thing the gate does not
> have: the `|E|` array ParaView colours by is **checked, not merely written** —
> it spans 2.707108e-01 … 1.001903e+00 V/m, a **3.701×** drop against the
> closed-form `e^{αL}` = **3.694×**. Negative control, per the plan structural
> and *cited rather than recomputed*: the same closed form at σ = 0 gives
> α ≡ **0.0** Np/m exactly (asserted `== 0.0`, no tolerance — a zero loss
> tangent makes the radical identically zero) against 13.069460 measured; the
> solved-field version stays on record as `MAT-2` in the same gate log (α ratio
> 10.3232 vs 10.3116, 0.113%) and is not re-run. **Closes nothing physics-side:**
> `TH-6`/`MAT-2` were already ✅ 2026-07-31; this is the Phase-2 §5.4 backfill
> making a gated capability runnable, and it retires 1 of that phase's shortfall
> of 5.

> **✅ Restored 2026-08-07 (19:30 slot, §9 item 1).** The runner path is now
> on record. `./run_examples.sh --list`
> (`20260807T003037Z_EX-1-runner-list.log`, 0 s) enumerates
> `mesh:1 -> examples/meshing/01_two_torus_ports.py` under
> "meshing (default real build, no solve)", so the `mesh:` group dispatches
> from the listing the operator reads. `./run_examples.sh -e mesh:1`
> (`20260807T003044Z_EX-1-runner-mesh1.log`, exit 0, 16 s harness-wall / 13.1 s
> example-internal, `mpiexec -n 2`, smoke-to-standard) reproduces every gated
> identity at every printed digit through the runner: `GEO-10` area ratio
> **1.000000000000000**, `GEO-8` volume ratio **1.000000000000** with
> `sum(tagged)/V_mesh` **1.000000000000**, both gap boxes
> **1.000000000000**, and the wire ratios **0.963633** / **0.963756** — all
> byte-matching the direct-invocation gate log. Tag inventory unchanged
> (`{1, 2, 3, 101, 102}` / `{1, 201, 202}`). The predicted `-T` trap did
> **not** fire: `run_examples.sh:199` omits `-T`, but `docker compose exec`
> under the harness (`bash -lc`, no TTY) still ran to completion, so the
> runner was left unmodified per the item's "fix only the dispatch" rule —
> the missing `-T` remains a latent headless hazard, not a live defect, and
> is not tracked as an issue because nothing has ever failed on it. No
> source, test, or example file changed for this closure; the log is the
> whole deliverable. The demotion note follows, for the record.

> **🟡 Demoted from ✅ 2026-08-06, 18:00 review (audit finding).** The §4
> substance is fully earned — both harness logs exist, every identity below
> was re-verified in the gate log to the printed digit, elapsed recorded —
> but the §5.4 delivery mechanism was never exercised on record: both logs
> run `mpiexec -n 2 python3 examples/meshing/01_two_torus_ports.py` directly,
> byte-equivalent to the runner's inner command, yet no log shows
> `./run_examples.sh --list` or `-e mesh:1` actually dispatching the new
> `mesh:` group. §5.4 says examples execute *via the runner*, and the runner
> wiring is the one part of this chunk verified only by code inspection.
> Remedy is one logged `--list` + `-e mesh:1` run (queued, §9 item 1); the ✅
> returns with that log. Two corrections to the record while here: the
> original plan text below says "examples run serial via `./run_examples.sh`"
> — wrong, the runner's default is `-n 2` (`NPROC=2`, `run_examples.sh:41`);
> and attempts.md calls the two logs "identical runs" — they differ (the
> ParaView hint text was edited between them; the *gate* log is the one
> matching committed source).

**`EX-1` landed 2026-08-06, closed 2026-08-07 by the runner log** (16:30 slot, `20260806T213439Z_EX-1-gate.log`,
14 s at `-n 2`; probe run `20260806T213341Z_EX-1-example.log`, 15 s).
`examples/meshing/01_two_torus_ports.py` builds the *gapped* fixture at the
`GEO-8`/`GEO-10`/3b-i parameter set (79 534 cells, 12.4 s) and asserts three
closed-form identities, all allreduced, all holding to every printed digit:
`GEO-10` outer-boundary area `3.220000000000e-02 m²` / analytic box surface =
**1.000000000000000**; `GEO-8` `V_mesh` `3.920000000e-04 m³` / analytic box =
**1.000000000000** with `sum(tagged)/V_mesh` = **1.000000000000** over all
five tags; and each gap box `1.148763643e-06 m³` / `dx·dy·dz` =
**1.000000000000**. The wire ratios reproduce the landed
`test_two_torus_gapped.py` record digit-for-digit (**0.963633** /
**0.963756** of the analytic partial torus), and the tag inventory is exactly
`{1, 2, 3, 101, 102}` / `{1, 201, 202}` — the pre-`GEO-10` facet set was `[]`
(known-issues 10). New runner group: `./run_examples.sh -e mesh:1` (real
build, no complex source, no solve); `examples/meshing/` is enumerated by
`scripts/run_examples.sh` alongside `mag`/`mri` and is picked up by `-e all`.
Two XDMF files, since facet tags live on `tdim-1` and cannot share the cell
grid: `_combined` (mesh + DG0 `CellTags`) and `_facets` (mesh + `mesh_tags`),
both verified to bind their arrays. No solve, no port voltage — `PORT-1`
stays 🟡. Original plan follows.
**`EX-1` — the two-torus port fixture, meshed and tagged, in ParaView (plan
written 2026-08-06, 10:30 review; the §5.4 ramp entry for `GEO-11`'s
closure, demonstrating the `GEO-8`/`GEO-10`/`GEO-11`-gated meshing
capability).** New `examples/meshing/01_two_torus_ports.py`, wired into
`./run_examples.sh`: build `two_torus_domain()` at its validated defaults,
write combined-XDMF carrying the mesh, the cell tags (wire/gap/air), and the
facet tags (`outer_boundary` from `GEO-10`, the port groups from 3b-iv), plus
a short printed report. Angle no existing example covers: every current
example shows solved fields; none shows a validation fixture's geometry or
any tag structure, which is exactly what the operator needs to eyeball in
ParaView when a `PORT-1` number looks wrong. **Gated capability only:** the
conforming fragment (`GEO-8`), the outer-boundary group (`GEO-10`), and the
classification margins (`GEO-11`) are all ✅; the example must not solve
anything or show port voltages (ungated, `PORT-1` 🟡). **Anchor (the example
asserts, not just renders):** the `GEO-10` box-surface identity — summed
`outer_boundary` facet area / analytic box area — printed and asserted at
`1e-9` (1.000000000000 on record), and the `GEO-8`/`GEO-9`-style volume
identity per cell tag vs the closed-form solid volumes, allreduced.
**Negative control:** on record, cite in the report text — the pre-`GEO-10`
state (facet tag absent entirely) and the unfragmented mesh's exactly-zero
mutual coupling that `PORT-1` step 1 caught. **Cost:** standard, `-n 2` is
unnecessary — examples run serial via `./run_examples.sh`; the default-mesh
build is ~25 s on record at the *gapped* geometry, less at defaults;
`timeout 180`. **Traps:** gmsh init/finalize in `try/finally`; XDMF needs
the mesh written before the meshtags and matching names for ParaView to bind
them; `run_examples.sh` discovers examples by directory — a new
`examples/meshing/` dir must actually be picked up (check the script, add
the dir if it enumerates explicitly); no solve, so the real build is fine —
do not source the complex mode for a meshing-only script unless the imports
require it. **Does not close:** nothing physics-side; §5.4 inventory only.
**Negative result:** if either identity misses at `1e-9`, that contradicts
`GEO-8`/`GEO-10`'s landed gates — do not ship the example; report the
measured ratio against the landed log and stop (that is a regression
finding, not an example-authoring problem).

**`EX-2` — the cylindrical phantom domain, meshed, classified and tagged, in
ParaView (plan written 2026-08-07, 03:00 review; the §5.4 ramp entry for
`GEO-13`'s closure).**

> **✅ Done 2026-08-07 (09:00 slot, §9 item 3).**
> `examples/meshing/02_cylindrical_phantom.py` ships and dispatches through
> the runner: `--list` names
> `mesh:2 -> examples/meshing/02_cylindrical_phantom.py`
> (`20260807T140515Z_EX-2-list.log`) and `./run_examples.sh -e mesh:2 -n 2 -t 180`
> runs it (`20260807T140554Z_EX-2.log`, exit 0, 5 717 cells, 0.7 s
> example-internal — the `EX-1` runner gap is not repeated).
>
> **Anchor (1) reproduces the `GEO-13` record exactly**, live through the
> example path on its own CAD model with `_WALL_TOL_FRACTION` imported from
> the generator: `tol = 9.000000e-04`, **3 of 6** surfaces accepted, worst
> accepted **1.111111e-04 × tol** (ceiling 0.1), nearest rejected
> **9.999989e+01 × tol** (floor 10) — every digit matching
> `20260807T033127Z_GEO-13-probe.log`. No regression; the example asserts the
> record to 1e-6 relative rather than re-deriving it.
>
> **Anchor (2), volumes, with one correction to the plan's premise.** The
> exact partition identity holds — `(V_inner + V_outer)/V_mesh =
> 1.000000000000000` — and the plan's `(0.98, 1)` inscription band holds
> wherever the *outer* wall is what is being measured: `V_mesh/cylinder =
> 0.995260198`, `V_outer/annulus = 0.998059093`, and (added here)
> `A_outer_boundary/(lateral + 2 caps) = 0.994172277`, all strictly below 1.
> **The plan's assumption that the band applies per tag is contradicted by
> measurement**: at the defaults `resolution = 0.02` is *twice*
> `inner_radius = 0.01`, so the inner cylinder is not resolved at all —
> `V_inner/cylinder = 0.718169560`, a 28.2% deficit, nowhere near 0.98. That
> is not a defect and not a tuning question; it is what these defaults mesh.
> Rather than pin it, the example gates it in **closed form**: gmsh falls back
> to its 7-node minimum circle discretisation, so the phantom is a heptagonal
> prism, and the meshed inner end-cap area equals the inscribed regular
> heptagon `(7/2π)·sin(2π/7) = 0.8710264` to **1.11e-16 relative** — an
> identity at machine precision, asserted at 1e-12. The inner *volume* falls
> further as the lateral triangulation cuts inside that prism, and is bracketed
> two-sidedly between the degenerate-square floor `2/π = 0.636620` and that
> heptagonal ceiling (measured 0.718170). Nothing was loosened: the cap bound
> was *tightened* from the 1e-3 first written to 1e-12 once the first run
> showed the agreement was exact (`20260807T140522Z_EX-2.log`).
>
> Measurement probe: `scripts/probes/ex2_probe.py`
> (`20260807T140150Z_…`, `20260807T140258Z_EX-2-probe.log`). Closes nothing
> physics-side; §5.4 inventory only.
>
> *Caller audit (2026-08-07, 10:30 review — the follow-up the attempts entry
> flagged):* every repo caller of `cylindrical_domain` passes
> `resolution ≥ 2 × inner_radius` (`tests/mesh/test_cylindrical_domain.py`
> 0.02, `tests/solver/test_cylinder.py` 0.03,
> `test_boundary_condition_selection.py` 0.04, `test_time_harmonic_smoke.py`
> ×4 0.03, `test_convergence_diagnostics.py` 0.03 — all at
> `inner_radius = 0.01`), so **every one of them gets the heptagonal-or-
> coarser inner cylinder**. None asserts a closed form or a volume-dependent
> quantity on the inner subdomain — they are smoke/finiteness and operator
> fixtures — so the 28% inner-volume deficit is latent, not an active
> defect, and no chunk is opened for it. The hazard arms the day a test
> gates an inner-region quantity on one of these fixtures against an
> analytic value; whoever writes that test must pass
> `resolution ≪ inner_radius` or inherit the heptagon.

New `examples/meshing/02_cylindrical_phantom.py` in
the existing `mesh:` group: build `cylindrical_domain()` at the defaults
`GEO-13` swept, write combined-XDMF (mesh + cell tags, plus the facet file
carrying the wall/interior classification), print a short report. Angle no
existing example covers: `mesh:1` shows a box-bounded two-conductor
fixture; nothing shows the *cylindrical* geometry — curved outer wall,
phantom-in-domain — or the boundary classification the margins gate
protects, which is exactly what the operator eyeballs when a coil+phantom
mesh looks wrong (the birdcage path runs through cylinders). **Gated
capability only:** generation and classification margins are ✅ (`GEO-13`,
2026-08-07); no solve, no fields, no port quantities. **Anchor (the example
asserts, not just renders):** (1) the live two-sided classification
identity reproduced through the example at the meshed defaults — accepted
surfaces 3 of 6, wall ratio ≤ 0.1, interior ratio ≥ 10, importing
`_WALL_TOL_FRACTION` from the generator exactly as the margins test does
(on record: wall `1.111111e-04`, interior `9.999989e+01`,
`20260807T033127Z_GEO-13-probe.log`); (2) the per-tag closed-form volume
check with the curvature stated honestly — linear tets inscribe a curved
wall, so assert `V_mesh/V_analytic < 1` **and** inside (0.98, 1) at the
default resolution, printing the deficit beside the analytic cylinder
volumes so the record shows the O(h²) chordal loss rather than hiding it
(no exact identity exists here; `GEO-12`'s planar 1e-15 does not transfer —
that is the `GEO-13` plan's own boundary, restated). **Negative control:**
on record, cite in the report text — the old `tol = resolution` predicate
accepting **6 of 6** surfaces at `resolution = 0.09`, the inner cylinder
swept whole into `outer_boundary` (same probe log). **Cost:** standard;
the CAD sweep is 0.19 s and the caller meshes are seconds on record;
`timeout 180`, runner default `-n 2` — volume sums and counts allreduced,
rank-local values never asserted. **Traps:** gmsh init/finalize in
`try/finally`; XDMF mesh written before meshtags with matching names;
`run_examples.sh` already enumerates `examples/meshing/` (`EX-1`) — the
new file must appear as `mesh:2` in `--list`, and the closure logs must
show *the runner* dispatching it (`--list` + `-e mesh:2`), the exact gap
that cost `EX-1` its first ✅; real build, no complex source for a
meshing-only script. **Does not close:** anything physics-side; §5.4
inventory only. **Negative result:** classification counts or margins that
differ from the `GEO-13` record through the example path are a regression
finding against a chunk closed hours earlier — do not ship; report
measured vs logged and stop.

> **✅ 2026-08-08 (21:00 slot, §9 item 2).** `examples/mri/02_mass_averaged_sar.py`
> lands and reproduces the `MAT-4` step-3 record through the example path at
> every printed digit. Gate `./run_examples.sh -e mri:2 -n 2 -t 180`
> (`20260808T020414Z_EX-3-gate.log`, exit 0, 14 s harness-wall / 13.4 s
> example-internal, standard tier, complex build sourced by the runner —
> the log line reads `(complex build)`), preceded by a probe at the same
> settings (`20260808T020339Z_EX-3-probe.log`, exit 0, 17 s) and by
> `./run_examples.sh --list` (`20260808T020407Z_EX-3-runner-list.log`, 0 s),
> which enumerates `mri:2 -> examples/mri/02_mass_averaged_sar.py` under
> "mri (complex build, sourced automatically)" — the `EX-1` runner gap is not
> repeated. Measured, against the step-3 record: 74 216 cells, mesh 7.1 s,
> imposed `E_z = 7.493197e-03 + 1.499490e-02j` V/m, closed form
> **8.00835406e-08 W/kg**; `SAR_avg/SAR_point` = **1.00000000** at both 1 g and
> 10 g (budget 0.5%); kernel mass **0.0120%** / **0.0044%** (budget 0.1%) —
> both byte-matching the step-3 log; pointwise vs closed form **4.96e-16**,
> also byte-matching. One identity the gate does not have: the DG0 `SAR` array
> ParaView actually colours by is checked, not merely written — its
> sphere-averaged value hits the same closed form to **1.32e-15**, so a
> rendering that disagrees with the integrated quantity cannot ship silently.
> Negative control reproduced: the 1 g ball re-centred on `(0, 0, R)` separates
> by **2.1894** against the recomputed lens ceiling `1/f = 2.1681`
> (`f = 0.4612`), **0.98%**, floor 1.5 — a `sigma`-blind kernel returns 1.0.
> Every constant that could drift (`QUADRATURE_DEGREE = 16`, both budgets, the
> geometry, the masses, `SIGMA_HIGH`, `RHO_KG_M3`, the interior closed form) is
> **imported** from the step-3 test rather than restated; the runner puts only
> `src` on `PYTHONPATH`, so the example puts the repo root on `sys.path`
> explicitly — the one structural cost of the import-don't-restate rule, and
> cheaper than a second copy of the numbers. **Closes nothing physics-side:**
> `MAT-4` stays 🟡, the field is imposed, and the example's report text says so
> in two places; §5.4 inventory only.

**`EX-3` — mass-averaged SAR, point vs 1 g/10 g, in ParaView (plan written
2026-08-07, 18:00 review; the §5.4 ramp entry for `MAT-4` step 3's closure,
demonstrating the averaging operator at the standard masses).** New
`examples/mri/02_mass_averaged_sar.py` in the existing `mri:` group (which
sources the complex build automatically — no runner change): rebuild `MAT-4`
step 3's fixture (R = 0.03 m sphere, uniform complex phasor **imposed** on
N1curl, no solve), compute the pointwise SAR field and the 1 g / 10 g
mass-averaged values at centre and at the 1 g surface placement, write
combined-XDMF carrying the mesh, cell tags, and the pointwise SAR (DG0) so
ParaView shows the first SAR quantity any example has produced, plus a short
printed report. Angle no existing example covers: nothing under `examples/`
shows SAR, mass averaging, or any complex-build post quantity — and this is
exactly what the operator eyeballs when a future coil+phantom SAR number
looks wrong. **Gated capability only:** the operator identity at 1 g/10 g
closed 2026-08-07 (`MAT-4` step 3) on an imposed field; the example must not
solve, not claim C95.3, and the report text must state the imposed-field
caveat (§2.1: SAR-on-a-coil is unlicensed). **Anchor (the example asserts,
not just renders):** reproduce the step-3 record through the example path —
`SAR_avg/SAR_point` at both masses with |ratio − 1| < 0.5% (1.00000000 on
record), kernel mass error < 0.1% (0.0120% / 0.0044% on record), pointwise
vs the closed form `σ|E|²/(2ρ)` < 1e-12 (4.96e-16 on record), quadrature
degree 16 imported from the test's constant, not restated. **Negative
control:** the 1 g surface ball — separation vs the recomputed lens ceiling
`1/f = 2.1681` (2.1894 on record, floor > 1.5), printed in the report.
**Cost:** standard; the step-3 gate ran 7 tests in 17.4 s *with* the mesh —
`timeout 180`, runner default `-n 2`, all ball integrals allreduced.
**Traps:** `ufl.real` on the non-origin ball comparison
(`ComplexComparisonError`, paid twice); density via `build_density_field`,
never a literal; XDMF mesh written before meshtags with matching names; the
closure logs must show *the runner* dispatching (`--list` naming `mri:2` +
`-e mri:2`), the exact gap that cost `EX-1` its first ✅; quadrature degree
12 is measured insufficient at this ball-to-mesh ratio — 16, from the
step-3 sweep. **Does not close:** `MAT-4` (stays 🟡) or anything
physics-side; §5.4 inventory only. **Negative result:** numbers that differ
from the step-3 record through the example path are a regression finding
against a chunk closed the same day — do not ship; report measured vs
logged and stop.

### ANS — Ansys benchmark cases (§5.4)

Commissioned by the weekly planning review only, on gated physics only; the
human operator replicates each case in Ansys Electronics Desktop and the
next weekly review adjudicates the returned numbers.

| ID | Title | Status | Tier |
|---|---|---|---|
| `ANS-1` | Loop over a lossy slab at 10 MHz: runnable half of the first AED benchmark | ✅ | standard |

**`ANS-1` — runnable half of the first commissioned benchmark** *(scoped
2026-08-09, weekly review — the case is
`examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/`; `SPEC.md` is
committed and is the authority for geometry/materials/BCs; the physics is
`MAT-6`'s, gated at 1.58%/1.5834% vs Dodd–Deeds)*. Build a runnable script
in the case directory reusing the `MAT-6` W = 0.15 fixture exactly
(`tests/validation/test_dodd_deeds_impedance.py` constants; production
projected drive): two solves (σ_slab = 100 and 0 S/m at 10 MHz), then write
(1) `metrics.json` — R, X, ΔR, ΔX for both solves plus cell count and
elapsed; (2) combined-XDMF of |J| in the slab; (3) `COMPARISON.md` with the
closed-form column regenerated from `utils/dodd_deeds.py` (never
transcribed), our columns filled, and the AED columns blank per the SPEC
table. **Anchor:** ΔR within 2% of the closed form (1.5834% on record) and
within 1e-3 relative of the pinned `+3.2770406e-01 Ω` — a drift from the
pin at matched fixture is a regression finding, stop and report. The script
registers in `./run_examples.sh` (its own group or `mesh:`-style prefix —
implementer's call) and the closure log dispatches through the runner, per
the case README and the `EX-1` lesson. **Cost:**
standard, `-n 2`, ~27 s/solve at 138 619 cells on record, `timeout 180`.
**Traps:** complex build + `FEM_EM_REQUIRE_COMPLEX=1`; the ΔX row is
reported, never gated (unconverged in box size, §7 `MAT-6` step 4); if
`EX-11` has landed first, share its compute path rather than duplicating
it. **On closure:** the next daily review puts the case at the top of the
dashboard's Waiting-on-you list (§5.4) — that is how the operator learns it
is ready to replicate. **Does not close:** nothing Larmor-frequency; the
comparison is commissioned in the eddy-current regime on purpose, where our
number is gated.

**✅ 2026-08-09 (13:30 run).** `examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/01_loop_over_lossy_slab_10MHz.py`,
dispatched through the runner's **new `ans:` group** (one case directory per
benchmark, complex build sourced automatically):
`./run_examples.sh -e ans:1 -n 2 -t 180`, log
`20260809T183731Z_ANS-1.log`, exit 0 in **70 s** harness-wall (68.4 s in-script;
138 619 cells meshed in 11.0 s, solves 28.4 s loaded + 26.8 s free) — inside
the standard tier, and matching `EX-11`'s 74 s price for the same path.
**Both legs of the anchor hold**: ΔR = **+3.2770406e-01 Ω** is **1.5834%** from
the Dodd–Deeds closed form (+3.2259615e-01 Ω, regenerated at run time from
`utils/dodd_deeds.py`) against the 2% ceiling — the step-3 record digit for
digit — and **1.387e-08** relative from the pinned `+3.2770406e-01 Ω` against
the 1e-3 ceiling, so the benchmark demonstrably solves the *same* problem the
gate solved, not merely one with the same closed-form answer. The
**negative control is in-fixture and exact**: the σ = 0 solve dissipates
`0.0` W in the slab and carries `0.0` A/m² of eddy current, both asserted
`== 0.0` with no tolerance. An independent energy identity ½ΔR|I′|² vs
∫(σ/2)|E|² dV agrees to **ratio 1.0000** (reported, not gated). ΔX is
reported only, ratio 0.9200 — unconverged in box size per step 4, which is
the point of commissioning it.
Deliverables per §5.4 all landed in the case directory: `metrics.json`
(R/X for both solves + ΔR/ΔX + closed form + cell count + elapsed),
`COMPARISON.md` (our column and the closed-form column both generated by the
run, AED columns blank), and the combined-XDMF of |J| under
`paraview_output/` (untracked, like every other `paraview_output/` in the
repo — regenerated by each run; max |J| = 6.84e+02 A/m² loaded vs exactly 0
in the control). No physics or `src/` change: every constant, the mesh, the
drive and `_solve_projected` are **imported** from the `MAT-6` test modules
and the `EX-11` example, so the benchmark cannot drift from the gate.
*Two incidental fixes made while writing the operator-facing artifact:* the
max-|J| reduction took `np.real` explicitly (it was raising a `ComplexWarning`
into the published log), and the solve-metadata row now names the element
family correctly — `N1curl` degree 1, lowest-order Nédélec edge elements.
**The AED half is now the operator's**: `SPEC.md` box 1 is checked, and the
next daily review promotes the case to the top of the dashboard's
Waiting-on-you list.

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
   real matrix. *(Updated 2026-08-05, 18:00 review: the `W_e` spur is fully
   discharged — step 2d explained it to ratio 0.999998, step 2e removed it by
   solenoidal projection, step 2f made the projection the production drive.)*
   What remains is **3b** gap-voltage ports on the two-torus validation pair,
   and as of 2026-08-07 the factor-2 question that dominated it is
   **answered**: 3b-i/3b-iv landed the gapped fixture and its port tags;
   3b-v excluded the facet-integral estimator (4.845 × ωM₁₂ — normal,
   surface-charge-dominated); 3b-vi/3b-vii measured the tangential path
   voltage at 0.4937/0.4917 × ωM₁₂ and settled the estimator-family
   question negatively; 3b-viii exonerated the `ωM₁₂` reference in closed
   form (+0.481%, wrong sign to help); and 3b-ix closed the Faraday loop at
   **0.896 × ωM₁₂** — the missing half is the **buried** gap arc that
   `GAP_BURIAL` places outside the nominal wedge and
   `_gap_arc_quadrature` never integrates: 0.8% of the loop's length
   carrying 45% of its EMF. Terminal to terminal the port voltage is
   **0.8936 × ωM₁₂**, not 0.4937. As of 2026-08-07 (10:30): **3b-x's
   correction works** (0.8945 × ωM₁₂, all 19 gates green, parked —
   its consistency gate vs the new σ = 0 control reads 3.0224% against a
   3% bound whose premise the control disproved); **3b-xi is ✅** — the
   box attribution holds as a three-point monotone trend (deficits
   −8.03% / −5.03% / −3.27% at padding 0.08 / 0.10 / 0.12, 52.9× the
   mesh control); **3b-xii is executed (2026-08-07, 12:00 run) and lands on
   disposition (ii)** — the box moves both routes together (+2.956 pp /
   +3.045 pp), so the ~3% estimator-vs-control residual is real and the box
   is exonerated as its owner. **3b-xiii is executed (2026-08-08, 19:30 run)
   and lands on disposition (mixed) with the experiment's premise disproved**
   — a closed lossy loop is a shorted turn (`|I_cond/I′|` up to 0.865), so σ
   and closed-vs-gapped are confounded on the closed control and that route
   cannot separate them at any σ; the ~3% deviation is untouched and the
   strategic adjudication (branch landing, gate re-pointing) escalates to
   the weekly review. **3b-xiv is executed (2026-08-08,
   04:30 run) and completes the sweep**: the σ = 0 corner is degenerate
   (open circuit — neither corner of the 2×2 is well-posed), but the
   non-degenerate rungs exonerate loss by sensitivity (4× in σ moves the
   gapped estimator +0.19 pp, vs the 2.788 pp to be explained), so the
   **gap geometry/estimator owns the ~3% deviation** — the last suspect
   standing. Sunday's weekly review adjudicates the branch landing and the
   topology-changing successor (gapped-vs-closed at fixed σ = 800) with
   the full ladder in hand.
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
may reappear. If every item is done or blocked, the drain instruction at the
end of this section applies: **stop and journal**.

Last reviewed 2026-08-13, **10:30 review, run interactively** — the
scheduled 10:30 slot died on an API 529 before doing any work (empty log,
exit 1); the human operator directed an interactive session to run the
protocol in its place, ~6.5 h late but before any implementer slot hit the
drained queue, so no slot was lost to the outage. **The interval (03:00 →
now): five slots, five landings — `TH-10` went from anchor-only to closed.**
04:30: step 2 ✅ — the repo's first Larmor-frequency solve gate: 64 MHz
interior relL2 **8.154% → 3.643%** vs `LossySphereSeries` (< 5%,
decreasing), quasi-static separation 18.68× (> 10×), 10 s. 06:00: `EX-18` ✅
— first ports example, `ports:` runner group, systematics ladder lifted to
`ports/systematics.py` and asserted bit-identical; raw −10.55% printed as
the miss it is. 07:30: step 3 ✅ — 128 MHz at **1.826%**, 57.31×, same
bounds shared by both frequencies; *refuted its own scoping* (error is
lower at 128 MHz at the same mesh ⇒ the ~3% is not wavelength-limited —
now `GEO-14`'s question). 09:00: `MAG-13` rung 3 ✅ — **3.7372%** at 1.52 M
cells: the < 5% wire target reached by brute force; rung 2's near-wire
error-map pattern refuted (mesh-realization noise; §2 bullet struck).
12:00: step 4 ✅ — ½∫σ|E|² to **3.629%**, quasi-static power route missing
by 58.1%; queue correctly drained-and-stopped. **Step-3 audit (one
subagent auditor per landing): EX-18, TH-10 steps 2–4, MAG-13 rung 3 all
COMPLIANT — no demotions.** Caveats recorded, none §4-blocking: TH-10
step 4 gates the level but not monotonicity (add the assert on that
file's next edit); its negative-control margin is 1.16× vs the field
gates' 1.9–5.7× (floor pre-stated, not moved); MAG-13's new exit gate is
code-verified but was never bitten in-slot (a 26 s `RES=0.0025` smoke
closes that — ride it on the next probe edit); EX-18's negative control
is cited-not-solved (disclosed) and one code comment overstates its
reproduction-band margin ~50× (comment fix rides with the next edit of
that file). Step 2: tree clean, no `attempt/*`/`recovered/*`.
**Review decisions:** (1) **`TH-10` closed ✅** — all scoped steps green
and audited; the coil-loading trend is a different machinery on a
different fixture and becomes **`TH-11`** (§2.1's extrapolation sentence
narrowed accordingly: imposed-field Larmor is now gated; coil-at-Larmor
remains the extrapolation). (2) **`PORT-1` step 4 scoped** — the package
path (`run_n_port_sparameter_sweep` off the solved field, retiring the
`excitation.py` heuristic on the two-torus fixture); this is the §10
subgoal-2 critical-path step and queue item 1. It is *not* birdcage
ports and does not touch the weekly hold. (3) **`GEO-14` commissioned**
— the shared ~3% floor discriminator (TH-10's three residuals +
`MAG-13`'s CG1 floor), step 1 is the one-command 64 MHz run at the
priced 55 251-cell mesh. (4) §5.4 ramp: **`EX-19` commissioned** —
`TH-10` closed new quantitative gates and no example solves at a Larmor
frequency. (5) **`OPS-16` commissioned (spare)** — retry-on-529 in the
three automation launchers; two review slots died on 529 today (15:30Z
and the 10:30 slot), and a single guarded retry converts that class of
loss into a delay. Standing weekly-review items unchanged (composition
question, `MAG-13` gate adoption, `MAT-6` step 10, `POST-4`/ParaView,
birdcage-ports/B1+ hold). Waiting-on-you delta: nothing new; ParaView
`.bp` check, `ANS-1`, and the push stand (origin at `b6e994f`,
2026-08-10 — ~45 ahead once this lands).

Previous interval's digest (2026-08-13 03:00), retained for the audit
trail: **four slots, four landings — the port lineage landed on `main`
(3b-xvii, 11× margin at matched topology; 3b-xviii pair gate green at
the unmoved 10% via the two named systematics, raw −10.57% on record as
a miss) and the Larmor anchor appeared (`LossySphereSeries`, 6/6, the
102.3%/154.6% quasi-static departure sized). All four flips audited
COMPLIANT; the three `attempt/PORT-1-*` branches deleted after capture
verification.** *(Full text in `docs/planning/plan-archive.md`, archived
2026-08-13, 10:30 review.)*

**Five ready items, mutually independent.** Item 5 is the declared spare.
Items 1, 3 and 4 execute their §7 entries verbatim; items 2 and 5 are
self-contained below.

1. **`PORT-1` step 4 — the package path reads the solved field
   (standard).** Execute the §7 `PORT-1` step-4 entry verbatim:
   `run_n_port_sparameter_sweep` gets its port voltages from the
   gap-voltage route (systematics via `ports/systematics.py`) instead of
   `ports/excitation.py`'s heuristic, on the two-torus fixture.
   **Anchor:** the gated record reproduced through the *package* entry
   point — raw within 2e-3 of 0.894283, corrected inside the unmoved
   0.10, `‖S−Sᵀ‖/‖S‖ < 1e-3`, `‖S‖₂ ≤ 1`. **Negative control:** the
   retiring heuristic's S on the same fixture, asserted to *differ*
   beyond the reproduction band. **Cost:** `-n 2`, one command,
   `timeout -k 30 600` (3b-xviii's 457 s envelope). Deprecate the
   heuristic behind a kwarg, do not delete. Hold `PORT-1` 🟡 — the ✅
   flip is the reviewing session's call.
2. **`EX-19` — Larmor lossy-sphere example (standard).** The first
   example solving at 64/128 MHz: `examples/time_harmonic/06_…` under
   the `th:` group, importing the `TH-10` fixture (never restating it),
   both frequencies in one run, combined XDMF of |E| in and around the
   sphere, guide to the `EX-15` bar. **Anchor:** the gate record
   reproduced digit-for-digit through the example path — 3.643% /
   1.826% interior relL2, separations 18.68× / 57.31×, power 3.629%
   (logs `20260813T093212Z…`, `…123211Z…`, `…170337Z…`). **Negative
   control, executed in-run:** the quasi-static separation assertions
   are part of the imported fixture. **Cost:** standard, `-n 2`; the
   three gate runs price it at ~70 s total + export. **Traps:** complex
   build via the runner; the series raises at r = 0 (the 1 nm offset is
   on record); the doc-reference checker's guide pass will fail the
   commit without the guide. **Scope:** no SAR wording, no mass
   averaging. **Negative result:** report, annotate §7, stop.
3. **`GEO-14` step 1 — the ~3% floor discriminator (standard).**
   Execute the §7 `GEO-14` entry verbatim: the 64 MHz gate at the
   priced 55 251-cell mesh; bands pre-registered (> 3.0% floor /
   < 2.0% resolution / between mixed); the 128 MHz record digits at the
   same mesh are the negative control. ~30–40 s.
4. **`TH-11` step 1 — coil loading at 64 MHz, cost/feasibility probe
   (standard, measurement only).** Execute the §7 `TH-11` step-1 entry
   verbatim: the `MAT-6` combined fixture at 64 MHz, identities gated
   (complex-power residual, exact-zero σ = 0 control), physics printed
   never gated, stop rule 300 s/solve. Any outcome is a finding.
5. *(spare)* **`OPS-16` — retry-on-529 in the automation launchers
   (smoke, no compute).** Add to `daily-review.sh`, `weekly-review.sh`,
   `implementer-run.sh`: if the claude CLI exits nonzero **and** the
   log tail matches `API Error` / `5[0-9][0-9]`, sleep 300 s and retry
   **once**, appending an `attempt 2` marker line; lock semantics
   unchanged (retry happens inside the held lock); total runtime stays
   inside each script's existing `timeout` budget — shrink the CLI
   timeout accordingly rather than extending the slot. **Anchor:** a
   rehearsal with a stub `CLAUDE_BIN` (add an env override for
   testability): stub fails with an `API Error` line → exactly one
   retry, then success → log carries both attempts and exit 0.
   **Negative control:** stub succeeds first try → no retry marker;
   stub fails with a non-API error → **no** retry (a protocol failure
   must not run twice). **Traps:** `scripts/automation/hooks/` is
   write-protected — this touches only the three launchers; keep the
   one-session lock held across the retry or two sessions can
   interleave. **Scope:** no protocol-document changes. **Negative
   result:** report; the scripts stay as they are.

*(The per-review journal — slot recap, completion audits, plan-work notes,
§10 assessment — lives in the review commits and
`docs/planning/plan-archive.md`, not here.)*

If the queue drains: **stop and journal.** Do **not** improvise gap-voltage
ports on the birdcage itself or a B1+ chunk — both are deliberately held for
a review to scope once the corrected estimator has *landed*, and the landing
decision belongs to the weekly review (its 2026-08-09 adjudication, decisions
(3)/(4)), conditioned on the 3b-xv discriminator — executed 2026-08-09,
band (mixed): the closed route has no σ-independent estimator. *(Updated
2026-08-13, 03:00: both conditions are now met — the lineage landed on
`main` with 3b-xvii and the port-pair gate is green with 3b-xviii
(corrected 0.939581, −6.04% inside the unmoved 10%). The hold on birdcage
ports and B1+ **still stands**: scoping them is the weekly review's call,
and it has an open question first — the two systematics' independent
composition is untested (§7 3b-xviii). Also still open: whether `GEO-4`'s
graded sizing is a birdcage prerequisite, per the 0.7091 measurement.)*

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

First weekly review 2026-08-09: re-derived from measured pace per the
seeding note; owned here thereafter. "Phase 5 (current)" is the organizing
goal, not a claim that §6's phases 2–4 are closed — their open gates
(`PORT-1`, the Larmor-regime validation, coil-driven SAR) *are* the content
of the loaded-birdcage goal, and §6 stays authoritative for gate status.

**Pace ledger — week of 2026-08-02 01:30 → 2026-08-09 01:30 (the first
measured week; every date below cites it).**
- **47 items reached §4-✅** (14 chunks: `GEO-9`…`GEO-13`, `OPS-11`…`OPS-14`,
  `MAG-6`, `MAG-16`, `EX-1`…`EX-3`; plus ~33 steps inside open chunks), from
  72 journaled implementer slots (49 complete, 16 parked, 2 blocked,
  5 anomalies; ~8 further slots lost to host downtime against the 84-slot
  nominal grid). 115 commits, 260 harness rows, 13 known-issues retired vs
  2 net-new still open.
- Phase attribution of the 47: ports (Phase 4) **12** ✅ steps plus 11
  parked diagnostic probes; post-processing **10**; meshing on the Phase-5
  lineage (`GEO-9`…`GEO-13`) **7**; materials/SAR (Phase 3) **6**; Phase-1
  hardening **6**; OPS **4**; examples **3**. Phase 2 added nothing (its
  five analytic gates closed the previous week) — the measured TH-campaign
  rate, **5 analytic gates in ~1 week** of focus (2026-07-27…31), is the
  precedent used below for gate-type work.
- **The measured risk to pace is reliability, not physics**: two unexplained
  mid-command harness kills (open known-issues entry, fired twice on
  `MAG-13` step 2 — its own rule now says escalate, not retry a third
  slot), ~8 slots of host downtime, two dirty-tree incidents from live
  human edits, and two items waiting on one-line human decisions (`MAT-6`
  step 7's `Edit(docker/**)` allowlist move; origin push remains manual and
  stale). At the measured 65% slot-completion rate, one lost day ≈ 7 gated
  items.

**Phase 5 — loaded birdcage RF (current).** Subgoals, each with its
validation target:

1. *Port-estimator adjudication* — the licensed gapped-vs-closed
   discriminator at σ = 800 (weekly-review licence 2026-08-09 in the
   `PORT-1` entry: two-slot budget, pre-registered disposition, branch
   lands with the lineage's first ✅ gate). Target: matched-topology
   consistency identity on the two-torus fixture. **Update 2026-08-12
   (operator session, textbook-grounded — §7 `PORT-1` adjudication):** the
   second slot is re-pointed to gap-region h-refinement (step 3b-xvi;
   Jin's feed-modeling practice, and 45% of the loop EMF sits sub-cell),
   all outcomes proceed to the 3b-i/ii port-pair gate with a stated,
   labeled systematic, and further σ-placement or `∫E·dl`-variant
   diagnosis is barred. The 08-09 assessment's step count stands.
2. *Honest S-parameters from the package* — gap-voltage `V = −∫E·dl` ports,
   `excitation.py` replaced, N-port Z from single-port solves, then the
   same machinery on the birdcage mesh. Targets: cross-route identity
   (gap-voltage Z vs reaction Z on the same solved field), reciprocity
   below stated tolerance, and the `PORT-5` metrics on a package-produced
   S-matrix. **Assessment 2026-08-09:** remaining work ≈ 20 ± 5 steps at
   the landed grain (discriminator + re-point + the deferred 3b-i/ii pair
   gate + V/I estimator + single-port Z + `excitation.py` + birdcage tags +
   N-port assembly); measured port throughput 12 ✅ steps/week ⇒ 20/12 ≈
   **1.7 weeks — ports on the birdcage ≈ 2026-08-19…26**. *(Note
   2026-08-12, operator session: for the birdcage itself, the port
   definition should move toward a lumped/circuit-element port boundary
   condition rather than further gap-voltage estimator variants — Jin
   ch. 11's hierarchy; theory now in-repo at `docs/references/jin-fem-3e/`.
   The two-torus `∫E·dl` machinery stays what the 3b-i/ii gate validates,
   with its systematic stated.)*
3. *Larmor-regime validation gate — this phase's real content.* Every
   loading/SAR gate today is eddy-current (10 MHz) or imposed-field; saline
   at 64/128 MHz is an extrapolation (§2.1). Named targets: the lossy
   dielectric sphere in a full-wave field at 64/128 MHz against its
   analytic series solution (the `TH-8` machinery carried into the
   displacement-current regime), and the coil-loading trend vs frequency
   crossing out of the eddy-current regime. **Assessment:** ≈ 8–12
   gate-grain items; at the TH-campaign precedent (5 gates/week focused) ⇒
   **≈ 1.5–2 weeks once queued**; not yet queued — the daily review should
   start breaking this down as the port lineage clears, and a §7 chunk ID
   should exist by the next weekly review.
4. *B1+ and SAR maps on the coil+phantom fixture at 64/128 MHz.* Targets:
   SAR through the `MAT-4`-gated averaging operator (its C95.3 claim closes
   here); B1+ gated qualitatively against published birdcage homogeneity
   behaviour and, once computed, an AED benchmark case (`ANS-2`, to be
   commissioned when subgoals 2–3 close). Blocked on 2 + 3 by §6's
   scaffolding rule.

**Phase-5 exit assessment, 2026-08-09 (the arithmetic on record):** ports
≈ 1.7 wk (subgoal 2) + Larmor gates ≈ 1.5–2 wk (subgoal 3, partly
parallel) + maps ≈ 1 wk (subgoal 4) ⇒ **exit ≈ 2026-09-06…13 at measured
pace, reliability permitting**. That is well inside a quarter, so no rescope
is forced. The number honest people watch: if the port lineage's
discriminator round does not convert to the 3b-i/ii pair gate within its
two-slot budget, subgoal 2's 20-step estimate is wrong and the next weekly
review re-plans rather than extends.

**Phase 6 — tuning.** Mode spectrum of the birdcage (the `TH-9` eigensolver
machinery on the birdcage mesh), lumped capacitors at the gap/port level,
and a circuit co-simulation loop: S-parameters from the EM solve, tuning
and matching in a circuit layer — the HFSS + Circuit split. Validation
targets, named now: birdcage mode frequencies against the lumped-element
ladder-network closed form; tuned S11/capacitor values against an AED
HFSS + Circuit benchmark case. Hard parts unchanged: near-resonance solves
are §2.1's ill-conditioning trap *by construction*, and the phase is
`PORT-1`-blocked until gap-voltage ports gate. **Assessment 2026-08-09:**
earliest meaningful start ≈ end of August (when subgoal-2 ports land); no
completion date — no circuit co-simulation work of any kind exists in the
repo, so there is no measured pace to extrapolate from, and inventing one
is what this section exists to prevent. First date next review after its
first steps land.

**Phase 7 — implants.** Parametric implant geometry first (wires, rods,
plates in the phantom; CAD import later), mesh grading around thin
conductors (the `MAG-13` 1/r lesson, made worse by skin depth), local SAR
and near-implant hot spots. Validation targets: published measured implant-
heating data, and AED comparisons — this is where they matter most. No
dated estimate: no measured pace for this work type exists.

**Phase 8 — thermal.** Pennes bioheat with SAR as the source term;
phantom-regime validation first (gel: no perfusion, so the equation reduces
to heat conduction + source, which analytic solutions cover). Mathematically
the easiest phase; the risk is validation data and the EM–thermal
interface, not the solver. No dated estimate, same rule.

**Epitaphs.** None this cycle: every subgoal above either moved this week
(the port lineage logged 23 slot-outcomes) or is five days old — nothing
qualifies as stalled. The rule stands: a subgoal unmoved for a month is
rescoped or killed here, with a dated one-line epitaph.

**Examples and benchmarks (2026-08-09).** The §5.4 ramp audit found an
8-example shortfall (Phase 1: 2, Phase 2: 5, Phase 3: 1) — backfill chunks
`EX-4`…`EX-12` opened in §7 with the accounting stated there. First Ansys
benchmark commissioned: `ANS-1`
(`examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/SPEC.md`, on `MAT-6`'s
gated physics; runnable half chunked, dashboard hand-off on closure). No
`COMPARISON.md` has AED numbers yet, so there was nothing to adjudicate
this cycle.

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
