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
| `OPS-11` | Put `tests/mesh` in CI — the directory no job runs | ✅ | smoke |

**`OPS-11` — `tests/mesh` is in no CI job** ✅ *(created 2026-08-02, 18:00
review; closed 2026-08-03, 12:00 implementer run)*
> `GEO-8` added one file from `tests/mesh` to both jobs; the rest of the
> directory has never run in CI, which is why known-issues 7 (three mesh
> generators failing outright) sat undiscovered until a regression sweep
> tripped over it. Excluding `test_birdcage_port_tags.py` — ~10 min on its own,
> known-issues "Non-test issues" — the directory is 9.7 s, i.e. nearly free.
> Done when: the `validation` job runs `tests/mesh` with `--ignore` on birdcage
> and on exactly the known-issues files that actually fail (no broader
> exclusion), the excluded set is justified by a re-run at the same commit
> showing those and only those failing, and the exclusions are removed by the
> commit that fixes them. This is a wiring chunk: its §4.3 assertion comes from
> the tests it wires in, so it cannot be `✅` before at least the `GEO-9` step-1
> gate exists to carry one.
>
> **Rescoped 2026-08-03, 03:00 review — the exclusion set is now measured, and it
> is smaller than this entry assumed.** `20260803T034252Z_GEO-9-step1-cohabit.log`
> ran all of `tests/mesh` less the birdcage in one process at `-n 2`:
> **16 passed, 1 failed, 1 skipped in 22.95 s.** So:
> * The **known-issues-7 coil+phantom tests pass** once the birdcage file is out
>   of the process — all three `test_coil_phantom_mesh.py` tests are `PASSED` in
>   that log. They need **no** exclusion. This entry's "exactly the
>   known-issues-7 files" is therefore wrong: `GEO-9` step 1 showed the
>   coil+phantom generator is innocent and the birdcage is the whole cause.
> * The one real failure is `test_domain_sizing_heuristics.py::test_coil_phantom_domain_sizing_accounts_for_off_center_phantom_extent`
>   (`assert 0.09 > 0.09`) — **known-issues entry 5**, pure geometry arithmetic
>   with no solve. *(Correction: commit `3ac025c` and `attempts.md:1903,1907`
>   both call this "known-issues 6". Entry 6 is the rank-dependent single-port
>   excitation test in `tests/solver`, unrelated. `attempts.md` is append-only,
>   so the correction lives here: the exclusion set is **5 and birdcage**, not
>   "6 and 7".)*
> * **The birdcage must be `--ignore`d for a second reason this entry did not
>   know: it hangs.** A gmsh-poisoned MPI process does not exit after pytest
>   reports — both `GEO-9` order probes exited **124 at the 180 s ceiling** after
>   pytest had finished in ~3.4 s (`test-results.md:136,139`). In CI that is not
>   a red job, it is a job that burns its whole `timeout-minutes`. Ignoring the
>   file on budget grounds happens to fix it; `GEO-9` step 2a fixes it properly,
>   and this chunk does **not** wait on that.
>
> So the concrete wiring is `pytest tests/mesh
> --ignore=tests/mesh/test_birdcage_port_tags.py --deselect
> tests/mesh/test_domain_sizing_heuristics.py::test_coil_phantom_domain_sizing_accounts_for_off_center_phantom_extent`,
> ~23 s at `-n 2`, carrying the `GEO-9` step-1 volume-partition identities
> (`1e-9`) as its §4.3 assertion. Re-run at the working commit to confirm
> "those and only those", per the done-when above — do not quote the cohabit log.
>
> **✅ Closed 2026-08-03 (12:00 implementer run), at `fa82c2d`.** The
> `validation` job gained a `Mesh generation suite` step running the whole
> directory with the two measured exclusions and nothing else; the single
> `tests/mesh/test_two_torus_conforming.py` line `GEO-8` had added to that job's
> analytic step was dropped, since the directory step now covers it (its
> `@complex_only` half still runs by name in `validation-complex`).
>
> **The "those and only those" control was executed, not quoted**
> (`20260803T170132Z_OPS-11-fullsweep.log`, `-n 2`, real mode, at this commit):
> the *unexcluded* directory is **2 failed, 18 passed, 1 skipped in 31.85 s**,
> harness exit 1 in 33 s — and the two failures are exactly
> `test_birdcage_port_tags.py` (known-issues 7) and the off-centre sizing test
> (known-issues **5**). Nothing else fails, so neither exclusion is wider than
> the defect it names. With them applied: **17 passed, 1 skipped, 1 deselected
> in 27.61 s**, exit 0 (`20260803T170047Z_OPS-11-negctl.log`), and the same
> figures **28.27 s, exit 0** under the CI-fidelity invocation with no
> `PYTHONPATH` override and the package from `pip install -e`
> (`20260803T170248Z_OPS-11-cifidelity.log`) — the `OPS-10` precedent for
> checking that a job does not depend on the container's path override.
>
> **§4.3 assertion (a wiring chunk's comes from what it wires in):** the
> volume-partition identities `V_mesh/V_box = 1` and `Σ(tagged)/V_mesh = 1`,
> each `< 1e-9`, now execute in CI for the first time — three files' worth
> (`test_coil_phantom_conforming.py:129,136,187,188`,
> `test_two_torus_conforming.py:97,104`, and post-poisoning in
> `test_birdcage_finalize_isolation.py:116,121`).
>
> **One trap from the item's own text confirmed:** the birdcage `--ignore`
> reason has changed and the CI comment states the current one. `GEO-9` step 2a
> fixed the hang, so the file now fails **promptly** — the full-sweep run above
> exited 1 in 33 s where the pre-2a order probes burned the whole 180 s ceiling
> to exit 124. The exclusion therefore rests on "deliberately red until `GEO-9`
> step 2b, and a red test hides regressions behind an expected failure", not on
> the budget/hang argument this entry was written with. Corollary worth
> recording: post-2a the coil+phantom tests pass *even with the birdcage in the
> same process* (18 passed in the unexcluded sweep), which is the poisoning fix
> holding under the one condition that used to break it.
>
> **Does not close:** known-issues 5 or 7. Both exclusions are annotated at
> their entries and must be removed by the commits that fix them.


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
| `GEO-9` | **`coil_phantom_domain` / birdcage meshes do not generate** | 🟡 step 1 ✅ (coil+phantom gated), step 2a ✅ 2026-08-03 (finalize + `bcast` the failure: 180 s hang → 13 s, gate exit 0), step 2b (geometry rewrite) planned 2026-08-03 10:30 review and queued | standard |

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
> `20260801T003108Z_GEO-8-before-numbers.log` (before, real mode),
> `20260801T003415Z_GEO-8-gate.log` (volume half, real mode, 2 passed
> 1 skipped in 11.1 s at `-n 2`),
> `20260801T003600Z_GEO-8-field-gate-numbers.log` (field-leakage half,
> **complex**, 2 passed in 31.8 s at `-n 2`),
> `20260801T003528Z_GEO-8-after.log` (gate + three users, 4 passed
> 1 skipped in 19.7 s at `-n 2`). Standard tier. Unblocks `PORT-1` steps 1–2.
> *(18:00 review audit correction: the earlier draft of this line grouped the
> real-mode gate log under a "31.8 s complex" label — only the field-gate log
> is complex. And the two "before (non-conforming)" numbers in the table above,
> `1.002633` and the exactly-zero `∫|E|²`, are not in any `GEO-8`-prefixed log:
> they come from the parked `PORT-1` probe,
> `20260731T213423Z_PORT-1-step1-meshconformity.log`, which the gate's own
> docstring cites correctly. Everything else in the table was re-verified
> against the cited logs and matches to the printed digit.)*
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

**`GEO-9` — `coil_phantom_domain` and the birdcage do not generate a mesh** 🟡
*(created 2026-08-02, 18:00 review, from known-issues entry 7 and a §10 gap;
step 1 ✅ 2026-08-03, step 2 open)*
> **Step-1 result (2026-08-03, 22:30 implementer run) — the hypothesis below is
> wrong, and the real cause is one defect, not two.** The negative control was
> run first, as instructed, and **did not reproduce**: in a fresh process all
> three `test_coil_phantom_mesh.py` tests **pass** in 4.80 s
> (`20260803T033050Z_GEO-9-before.log`). They fail only when
> `test_birdcage_port_tags.py` runs earlier **in the same process**
> (`20260803T033119Z_GEO-9-order-probe.log`, 3 failed 2 passed in 3.47 s,
> reproducing the known-issues symptom exactly). The birdcage generator raises
> inside its `comm.rank == rank` block and so never reaches `gmsh.finalize()`;
> gmsh is left initialised and mid-command (`Gmsh has aleady been initialized`,
> `I'm busy! Ask me that later...`), every later `occ` call is refused, and
> `model_to_mesh` reads the stale birdcage model — which is what `gmshio.py:118`
> asserts on. **Fragment and the group re-derivation are innocent:** the
> generator's own print reports `fragment volumes=4`, masses
> `1.579137e-04, 1.579137e-04` (both exactly `2π²Rr²`), `5.026548e-04`
> (exactly `πr²h`), `1.134952e-02` air.
>
> Landed anyway, because it is the assertion whose absence hid this:
> `tests/mesh/test_coil_phantom_conforming.py` (the `GEO-8` volume-partition
> identity on four regions) plus two guards in `coil_phantom_domain` that raise
> with the volume count and per-volume masses if fragment returns other than
> four volumes or leaves any 3-D entity ungrouped. Gate
> `20260803T033659Z_GEO-9-step1-gate.log`, standard tier, `-n 2`, **8 passed
> 1 skipped in 22.25 s**: `V_mesh/V_box = 1.000000000000` and
> `Σ(tagged)/V_mesh = 1.000000000000` (both bounds `1e-9`), phantom
> `4.943768e-04` = **0.9835** of `πr²h`, coils 0.7547 / 0.7526 of `2π²Rr²`
> (the global `resolution=0.015` exceeds the 0.01 minor radius — a statement
> about resolution, and the band is set from this measurement, not guessed).
> Both presets partition identically and the off-centre phantom keeps the same
> volume to all printed digits.
>
> **What step 1 does *not* fix:** known-issues 7 still fails as a suite. The new
> guards do not fire under contamination — gmsh is already busy, so they never
> execute (`20260803T033733Z_GEO-9-order-probe-after.log`, still
> `gmshio.py:118`). **Step 2's first action is therefore the cheap half:** wrap
> the birdcage rank-0 block in `try/finally: gmsh.finalize()`, so one broken
> generator stops poisoning every later mesh in the process. That is separable
> from, and should land before, the `occ.fragment` geometry rewrite.
> **Why this is a chunk and not a nuisance.** Three `tests/mesh` tests have been
> failing since before 2026-08-01 (known-issues 7, found by the `GEO-8`
> regression sweep, invisible because **`tests/mesh` is in no CI job**): the
> birdcage raises gmsh `Invalid boundary mesh (overlapping facets) on surface 3
> surface 49`, and coil+phantom raises `dolfinx/io/gmshio.py:118:
> AssertionError` on both presets. Neither mesh reaches dolfinx at all. Two of
> the four §10 *Target* criteria — "loaded birdcage + phantom simulation runs
> end to end" and "B1+ field matches literature" — route through exactly these
> two generators, and no chunk owned them. That is the gap this closes.
>
> **Correction to the known-issues entry-7 note, from code reading this review
> (unverified by execution).** The note guesses "likely the same
> overlapping-geometry family `GEO-8` just fixed … audit for missing
> `occ.fragment`". That is **wrong for coil+phantom and right for the
> birdcage**, and the difference is the whole scoping of this chunk:
> * `coil_phantom_domain` **already fragments** (`io/mesh.py:1616`,
>   `occ.fragment([(3, air)], [(3, coil_1), (3, coil_2), (3, phantom)])`) and
>   re-derives its groups by mass and z-centroid. So the cause is downstream of
>   fragment. The visible fragility is the group re-derivation at
>   `io/mesh.py:1622-1634`: it assumes fragment returns **exactly four**
>   volumes — `air_tag` is the largest mass, the two coils are the z-extremes,
>   and `phantom_tag = [tag for tag in remaining if tag not in (coil_1_tag,
>   coil_2_tag)][0]`. If the phantom cylinder intersects a coil torus, fragment
>   splits the overlap into extra pieces: `remaining` then holds more than three
>   tags, some volume is left with **no physical group**, and dolfinx's gmshio
>   asserts when it meets cells carrying no marker. If instead a merge drops the
>   count below four, the same line raises `IndexError`. Both are consistent
>   with the observed `gmshio.py:118` and with a *preset-dependent* failure
>   (both presets fail, and the off-centre preset moves the phantom in x).
>   **Hypothesis, not a diagnosis — the run's first job is to print the volume
>   count and the per-volume masses and settle it.**
> * `birdcage_port_domain` does **not** fragment: it uses
>   `occ.cut(..., removeObject=True, removeTool=False)` (`io/mesh.py:1970`),
>   which carves the conductors, phantom and port boxes out of the air but
>   keeps the tools as independent volumes that were never booleaned against
>   *each other*. The port boxes overlap the legs and the rings by
>   construction, and overlapping tool volumes meshed independently is exactly
>   the "overlapping facets" gmsh reports. Secondary defect in the same block:
>   the port boxes are cut out of the air but receive **no 3-D physical group**
>   (`io/mesh.py:1985-1988` groups only `conductor` and `air`).
>
> **Step 1 — coil+phantom only (one run).** Anchor: the `GEO-8` volume-partition
> identity, which is the same closed form and the same test shape —
> `V_mesh / V_box = 1` to `1e-9` where `V_box` is the analytic
> `8·(radial_extent+pad)²·(z_extent+pad)`, and `Σ(tagged volumes) / V_mesh = 1`
> to `1e-9`, plus the meshed phantom against the analytic `πr²h` in an inscribed
> band (`GEO-8` measured 0.9801 of the analytic torus at
> `wire_resolution ≲ 0.4·minor_radius`; a cylinder discretises better, so
> `(0.90, 1.00)` is the band to try and to widen only with a measurement). Add
> an explicit assertion that fragment returned exactly four volumes and that
> every 3-D entity carries a physical group — that is the assertion whose
> absence let this fail silently. Negative control: today the generator **raises
> before dolfinx sees a mesh**, so the before-state is unambiguous and must be
> recorded from a re-run of the three failing tests, not quoted from
> known-issues. Tier: standard, `-n 2`, mesh-only, no solve — `tests/mesh`
> excluding birdcage is 9.7 s in total (known-issues, "Non-test issues"), so
> budget ~60 s and cost-probe the mesh first. Traps already paid for:
> `cell_tags.values` is rank-local (use `tests/mesh/helpers.py::global_cell_tag_set`);
> `assemble_scalar` needs an allreduce before any volume is asserted on;
> `gmsh.model.occ.getMass` must be read **before** `synchronize` invalidates
> entity ids, and fragment renumbers, so never trust its returned tag order
> (the `GEO-8`/`loop_over_half_space_domain` discipline). Scope boundary: this
> does **not** close known-issues 4 (coil+phantom B-field symmetry 0.557 vs
> 0.350) and does **not** generalise the air box — `coil_phantom_domain` still
> uses a single global `setSize`, which is `GEO-4`'s open half and is what
> known-issues 4 most likely needs. If the measurement says the cause is not
> the group re-derivation, **report the volume count and the masses and stop**:
> the artifact is an annotation on this entry plus an updated known-issues 7,
> not an improvised fix.
>
> **Audit finding (2026-08-03, 03:00 review) — the two order probes did not
> merely fail, they *hung*, and step 1's prose does not say so.** Both
> `20260803T033119Z_GEO-9-order-probe.log` and
> `…033733Z_GEO-9-order-probe-after.log` record pytest finishing in 3.47 s and
> 3.29 s, but the **harness** exit status is `124` at 181 s and 180 s — the run
> was killed at the `timeout` ceiling, with `Loguru caught a signal: SIGTERM`.
> `docs/testing/test-results.md:136,139` record the 124s honestly; the §7 and
> attempts.md prose quotes only the pytest wall time. So a gmsh-poisoned MPI
> process does not exit after pytest reports — **it hangs**. That is not a
> footnote: it is why `tests/mesh` cannot go into CI with the birdcage in it
> (the job would burn its whole timeout rather than fail fast, see `OPS-11`),
> and it gives step 2a a second, sharper anchor than "the tests pass".
> Two lesser attribution nits, recorded so a later reader is not misled: the
> printed volume figures quoted above against
> `20260803T033659Z_GEO-9-step1-gate.log` actually appear in
> `…033625Z_GEO-9-step1-probe.log` (the gate ran without `-s`, so it contains
> the passing assertions that bound those numbers but not the numbers), and the
> `(0.70, 1.00)` coil band survives audit as a genuine resolution statement —
> an inscribed-polygon estimate at `resolution = 0.015` gives
> `(5/2π)sin(2π/5) × (34/2π)sin(2π/34) ≈ 0.7525–0.7568`, bracketing the measured
> 0.7547 / 0.7526 — though its lower edge is empirical headroom, not the
> first-principles ≈ 0.74.
>
> **Step 2a — stop the birdcage poisoning the process (one run; cheap, and it
> lands before any geometry work).** *(Split out 2026-08-03, 03:00 review.)*
> Wrap the `birdcage_port_domain` rank-0 block in `try/finally:
> gmsh.finalize()`, so a generator that raises leaves gmsh clean instead of
> initialised and mid-command. **Anchors, two, both already measured as the
> before-state:** (i) re-run the exact order probe — birdcage file, then
> `test_coil_phantom_mesh.py`, one process — and require the harness to exit
> **0 in seconds** where it now exits **124 at 180 s**; (ii) require
> `tests/mesh/test_coil_phantom_conforming.py`'s step-1 identities to *execute
> and hold* in that contaminated process — `V_mesh/V_box = 1.000000000000` and
> `Σ(tagged)/V_mesh = 1.000000000000` to `1e-9`. Today they cannot even run
> there (`…033733Z_GEO-9-order-probe-after.log`: the new guards never fire
> because gmsh is busy before they execute), so (ii) is a real conservation
> identity newly holding under a condition that previously destroyed it, not a
> re-assertion of step 1.
> **Negative control:** the before-state is unambiguous and needs no invention —
> 3 failed 1 passed, `gmshio.py:118`, harness exit 124. Re-run it at the working
> commit rather than quoting it, as step 1 was told to and did.
> **Cost:** smoke-to-standard, `-n 2`, **~30 s**. The birdcage file is cheap
> *when it raises* (3.3 s to the exception); the ~10-minute figure in
> known-issues is what it costs when it meshes, which after this change it still
> will not.
> **Traps already paid for:** `gmsh.finalize()` must be guarded by
> `gmsh.isInitialized()` or the `finally` raises over the original exception and
> hides it; the fix is rank-0-scoped, so check the other ranks are not left
> waiting on a collective the raising rank will never reach — that is the most
> likely reason a naive `try/finally` still hangs; do not silently swallow the
> gmsh exception, the birdcage must still fail loudly.
> **Does not close:** `GEO-9` (step 2b is the geometry), known-issues 7 in full
> (`test_birdcage_port_tags.py` itself stays red — the overlapping facets are
> untouched), known-issues 4, or the air-box generalisation. It *does* close the
> coil+phantom two-thirds of known-issues 7, which is the part `OPS-11` needs.
> **Negative result:** if the process still hangs after the `finally`, that
> locates the hang in MPI collective mismatch rather than in gmsh state —
> **report which, annotate this entry and known-issues 7, and stop.** Do not
> start the geometry rewrite with the remaining time.
>
> **Step-2a result (2026-08-03, 07:30 implementer run) — ✅ done, and the
> review's trap was the load-bearing half.** `try/finally: gmsh.finalize()`
> alone would **not** have fixed the hang: there were two independent defects.
> (1) gmsh contamination, as diagnosed. (2) **An MPI collective mismatch** —
> rank 0 raised inside its rank-0 block and skipped the collective
> `gmshio.model_to_mesh`, so rank 1 blocked in it forever. That is the exit 124,
> and it is why pytest could report in 3 s while the harness burned 180 s.
> The fix does both: the rank-0 body moved to `_build_birdcage_port_model`,
> the caller catches, finalizes under `gmsh.isInitialized()`, and
> `comm.bcast`es the failure so **every** rank raises before any enters
> `model_to_mesh`. The birdcage still fails loudly with its own message
> (`Invalid boundary mesh (overlapping facets) on surface 3 surface 49`) — the
> geometry is untouched, as 2a requires.
> **Before-state, re-run at the working commit as instructed rather than
> quoted** (`20260803T123116Z_GEO-9-step2a-before.log`): birdcage +
> `test_coil_phantom_mesh.py` + `test_coil_phantom_conforming.py`, one process,
> `-n 2` — 5 failed 2 passed in 3.16 s of pytest, **harness exit 124 at the
> 180 s ceiling**. **After** (`…123549Z_GEO-9-step2a-after.log`, byte-identical
> command): **1 failed 6 passed in 12.10 s, harness exit 1 at 13 s** — the one
> failure is `test_birdcage_port_tags.py` itself, which 2a explicitly does not
> fix. Anchor (i) is therefore met as *180 s hang → 13 s*; the probe cannot
> exit 0 while the birdcage file is in it, so anchor (i)'s exit-0 form lives in
> the gate below instead.
> **Gate:** `tests/mesh/test_birdcage_finalize_isolation.py`,
> `20260803T123657Z_GEO-9-step2a-gate.log`, smoke tier, `-n 2`, **1 passed in
> 5.30 s, exit 0 in 6 s**. One test, the poisoning order in one process: the
> birdcage must raise with a non-empty message; `gmsh.isInitialized()` must be
> `False` on rank 0 afterwards; an `allreduce` must complete (i.e. no rank is
> still stuck in `model_to_mesh` — reaching that line at `-n 2` *is* the
> no-hang assertion); and then anchor (ii), the coil+phantom volume-partition
> identity evaluated in that contaminated process —
> `V_mesh/V_box = 1.000000000000` and `Σ(tagged)/V_mesh = 1.000000000000`,
> both at `1e-9`, phantom `4.943768e-04` = 0.9835 of `πr²h`. Those match step 1's
> fresh-process figures to all printed digits, which is the point: the condition
> that previously destroyed the identity now leaves it exact.
> **Regression sweep:** `tests/mesh` less the birdcage file is 17 passed
> 1 skipped 1 failed in 28.46 s (`…123714Z_GEO-9-step2a-sweep.log`); the single
> failure is known-issues **5**, unrelated and pre-existing. This closes the
> coil+phantom two-thirds of known-issues 7 and unblocks `OPS-11`'s measured
> exclusion set.
>
> **Audit (2026-08-03, 10:30 review) — ✅ stands on every §4 criterion.** All
> four logs registered with exit codes, every claimed number reproduces
> verbatim, the volume identities are asserted (not printed) from
> allreduce-reduced quantities on every rank, the test diff is purely additive
> (`122 0`), and a mechanical dedent-diff of the moved rank-0 body shows exactly
> one changed line (the `port_radius` parameter read) — the geometry is
> byte-identical. The anchor substitution (exit 124→1 in place of the
> unobtainable exit 0, with the exit-0 statement in the gate) is disclosed in
> three places and strictly stronger than what it replaced. Three carry-forwards:
> (a) the gate's no-hang `allreduce` assertion degenerates to `1 == 1` at
> `-n 1` — the test proves nothing below two ranks, so never move it to a
> single-rank job; (b) the gate command wraps `timeout 180` while declaring
> smoke — harmless at 6 s measured, but the wrapper should match the declared
> tier; (c) once step 2b makes the birdcage *generate*, this gate's
> `pytest.raises` fixture needs a deliberately-failing parameter set or it goes
> red for the right reason — 2b's plan carries that instruction.
>
> **Step 2b — the birdcage geometry (one run).** *(Scoped from the directional
> note 2026-08-03, 10:30 review, which also made the fixture decision the 03:00
> review deferred — see the cost paragraph.)* Replace the
> `occ.cut(..., removeTool=False)` at the end of `_build_birdcage_port_model`
> (`io/mesh.py:2070-2075`) with a single `occ.fragment` of the air box against
> **all** tools — rings, legs, phantom, port boxes — so every pair of
> overlapping solids (legs pierce both rings by construction; port boxes may
> graze either) is booleaned into conforming pieces instead of being meshed
> twice. Re-derive every physical group from the **fragment out-map** (input
> solid → output pieces; never absolute tags — fragment renumbers): all pieces
> descended from any ring or leg → tag 1 `conductor` (a leg∩ring piece is
> conductor either way, so no policy question arises there); a piece descended
> from both a port box and a conductor → conductor (metal wins; the port region
> is an air-like integration volume); pieces descended only from a port box →
> that port's `100+i` group — **the port boxes currently receive no 3-D group
> at all** (`io/mesh.py:2085-2095`), which is the secondary defect and would
> `gmshio.py:118`-assert the moment the mesh otherwise succeeded. Air = the
> remaining pieces. Keep the outer-boundary surface block; its bounding-box
> arithmetic does not depend on volume tags. Add the `GEO-9` step-1 guard: raise
> with the volume count and per-volume masses if any 3-D piece ends up
> ungrouped.
> **Anchor:** the same volume-partition identity that gated steps 1 and 2a —
> `V_mesh/V_box = 1` to `1e-9`, `V_box` analytic
> `8·radial_extent²·z_extent` from the generator's own arithmetic
> (`io/mesh.py:2058-2059`), and `Σ(tagged)/V_mesh = 1` to `1e-9`, which is
> precisely the "no piece left ungrouped" statement. Per-region masses (rings vs
> `2π²Rr²`, legs vs `πr²ℓ`, phantom vs `πr²h`, port boxes vs `dx·dy·dz`) are
> **printed in the probe and banded only from that measurement** — the
> conductor total must come in *below* the analytic sum by the leg∩ring
> junction volumes, so a `= 1` assertion there would be wrong physics; the
> step-1 `(0.70, 1.00)` precedent applies. Also flip
> `test_birdcage_port_tags.py::test_birdcage_like_mesh_has_core_and_port_tags`
> green, **switching it to `tests/mesh/helpers.py::global_cell_tag_set()`** in
> the same commit — its `set(np.unique(cell_tags.values))` is the known
> rank-local latent bug, and known-issues ("Non-test issues") records that fix
> as written-and-reverted *pending exactly this rework*, so now is its
> sanctioned moment. That is a fixture-correctness change, not a loosening: the
> assertion content (core + per-port tags all present) is unchanged.
> **Negative control:** the before-state, re-run at the working commit as 2a
> did, not quoted — the generator raises `Invalid boundary mesh (overlapping
> facets) on surface 3 surface 49` and (post-2a) every rank raises promptly,
> exit 1 in seconds. Mesh-exists vs raises is total separation; say so.
> **Cost, and the fixture decision.** Mesh-only, no solve, `-n 2` (mandatory —
> the `bcast` failure path and the rank-safe tag read are exactly what `-n 1`
> cannot exercise). **The ~10-minute figure in known-issues is unmeasured
> post-2a and is probably the hang, not meshing cost**: pytest reported in ~3 s
> while the harness burned its whole ceiling (exit 124), and that entry predates
> the discovery that a poisoned process hangs. `coil_phantom_domain` meshes a
> comparable box at the same `resolution=0.015` in ~5 s. So: **cost-probe
> mesh generation at the default parameters first, `timeout 180`**; expect
> seconds-to-tens-of-seconds, and only if the probe exceeds the standard tier
> coarsen `resolution` 0.015 → 0.02/0.025 and record the measured pair — that
> is the reduced rung, chosen by measurement rather than in advance. Budget
> ~60 s for the gate on the probe's evidence; declare standard.
> **Traps already paid for:** fragment renumbers and reorders — trust only the
> out-map, and read `occ.getMass` before `synchronize` invalidates entity ids
> (the `GEO-8`/step-1 discipline); `cell_tags.values` is rank-local
> (`global_cell_tag_set()`); `assemble_scalar` needs an allreduce before any
> volume assertion; the step-2a isolation gate
> (`test_birdcage_finalize_isolation.py`) asserts the birdcage *raises* — once
> 2b makes it generate, that test's fixture must be given a deliberately
> invalid parameter set (e.g. `port_clearance` large enough to fail validation,
> or a forced-overlap geometry) so the isolation property stays tested; do not
> delete it. pytest captures prints without `-s` — the numbers log needs it.
> **Does not close:** `PORT-1` step 3b (gap excitation is its own work),
> known-issues 4, the air-box generalisation (`GEO-4`), or the ~10-min
> known-issues entry unless the cost probe measures otherwise — update that
> entry with whatever the probe finds. **Closes `GEO-9`** (steps 1 + 2a + 2b
> are the whole chunk) only if both `1e-9` identities gate green *and* the
> port-tags test passes rank-safely at `-n 2`; anything less holds the chunk
> at 🟡. Known-issues 7 retires with this commit if and only if all three of
> its tests are green.
> **Negative result:** if the fragmented geometry still fails to mesh, report
> the failing surface pair and the fragment volume count/masses, annotate this
> entry and known-issues 7, park the diff on `attempt/*`, and stop — do not
> iterate blind on gmsh tolerances inside the slot.

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
| `MAT-4` | SAR computation `σ|E|²/(2ρ)` | 🟡 | standard |
| `MAT-5` | Temperature-dependent conductivity | ⬜ | smoke |
| `MAT-6` | **Dodd–Deeds coil-over-lossy-half-space impedance** | ✅ | heavy |

> `MAT-1` is `⚠️` not because the preset table is wrong but because nothing
> consumes it.

**`MAT-4` — SAR computation** 🟡 *(step 1 ✅ 2026-08-03; step 2 ⬜.
Implementation plan 2026-07-31, 18:00 review)*
> **Step 1 ✅ done 2026-08-03, 21:00 implementer run** —
> `tests/validation/test_lossy_sphere_sar.py::test_lossy_sphere_mean_sar_matches_closed_form`
> plus `src/fem_em_solver/post/sar.py`; log
> `20260803T020448Z_MAT-4-step1-gate.log`, **5 passed in 39.4 s** at `-n 2`,
> standard tier, complex build (a first run without `-s`,
> `20260803T020355Z_MAT-4-step1-probe.log`, 43 s, passed identically — the
> gate's numbers are only in the `-s` log).
> Operating point exactly as the control-ceiling paragraph below prescribes:
> f = 64 MHz, R = 0.01 m, εᵣ = 78, σ = 0.05 / 0.57 S/m, ρ = 1000 kg/m³, two
> meshes at h = R/6 (17785 cells) and R/10 (74019 cells). Measured:
> * **Mean SAR against `σ|3E₀/(ε_c+2)|²/(2ρ)`, each σ against its own closed
>   form:** σ = 0.05 → 3.5273e-8 vs 3.4105e-8 W/kg (**3.42%**), converging
>   from 8.45% at the coarse mesh; σ = 0.57 → 8.2917e-8 vs 8.0084e-8 W/kg
>   (**3.54%**), from 8.75%. Both under the 10% bound, which is the closed
>   form's own O((k_in R)²) ≈ 6%-in-SAR model error plus P1 discretisation,
>   not a fitted tolerance. Quasi-statics holds and is printed:
>   `|k_in|R = 0.119 / 0.179`, `t = σ/(ωε₀) = 14.04 / 160.09`.
> * **The imaginary axis, directly:** interior `Im E_z/Re E_z` = 0.1752 vs the
>   closed-form 0.1755 (0.17%) and 1.9900 vs 2.0011 (0.55%). `TH-8` measures
>   this same quantity as exactly 0 by construction, so this is the first
>   quantitative assertion anywhere on `Im ε_c`.
> * **Two-σ negative control:** FEM `SAR₂/SAR₁ = 2.3507` against the closed
>   form 2.3481 (0.11%); a σ-blind solver returns 11.4000 exactly. Separation
>   **4.850 against the predicted ceiling 4.855** — the ceiling paragraph's
>   arithmetic reproduced by the solver to 0.1%. Gated at > 3.
> * Interior uniformity 0.07% / 0.11% spread inside 0.55 R; meshed sphere
>   volume 0.9964 of `4πR³/3` at the fine mesh (0.9900 coarse), reported
>   because it is the denominator of the mean as well as a field error.
>
> `post/sar.py` computes SAR in UFL from `e_complex` (`mean_sar`, subdomain-
> restricted, allreduced) and never touches `post/phantom_fields.py`, whose
> `float64` cast would discard `Im E` — on the σ = 0.57 sphere `Im E_z` is
> **twice** `Re E_z`, so that route would have been wrong by ~5×. The ½
> peak-phasor convention matches `poynting_power_balance`: `mean_sar`'s
> `dissipated_power_w` is that identity's volume leg restricted to the sphere.
>
> **Step 1 — the lossy-sphere gate (one run).** *(original plan, executed as
> written)* Extend the `TH-8` fixture
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
>
> **Control ceiling, computed 2026-08-02 (18:00 review) — do not gate a factor
> before reading this.** `POST-3` step 2 cost a run by naming a separation the
> fixture could not reach, and step 3 cost another by gating a control that
> turned out to be 1.07×. Both controls above have closed-form ceilings; here
> they are, with `t ≡ σ/(ωε₀)` the loss tangent numerator and
> `SAR ∝ σ|E_in|² = 9σE₀²/|ε_c+2|²`, `|ε_c+2|² = (εᵣ+2)² + t²`:
> * **The σ-blind control is weak — about 2.5×, not 10×.** Blind means the
>   solve runs at σ = 0 (so `E_in = 3E₀/(εᵣ+2)`) and is *scored* with the honest
>   σ. The ratio is then `((εᵣ+2)² + t²)/(εᵣ+2)²`. At the saline-ish point
>   εᵣ = 78, t ≈ 98 (σ = 0.7 S/m at 127.74 MHz) that is
>   `(6400+9604)/6400 = 2.50`. Useful as a direction check, unusable as a
>   factor-of-10 gate.
> * **The two-σ ratio control is the strong one — its ceiling is
>   `((εᵣ+2)² + t₂²)/((εᵣ+2)² + t₁²)`.** A σ-blind solver returns the trivial
>   ratio `SAR₂/SAR₁ = σ₂/σ₁` exactly, because E never moves; the honest solver
>   returns `(σ₂/σ₁)·|ε_c1+2|²/|ε_c2+2|²`. The separation between those two is
>   the expression above and is what the test should assert.
> * **It fights the quasi-static constraint, which is the trap.** Separation
>   wants `t₂ ≫ εᵣ+2`, but `|k_in|R = k₀√|ε_c|·R` grows as `√t₂`, and the
>   closed form needs `|k_in|R ≪ 1`. One point that satisfies both, worked here
>   so the run does not have to search: **f = 64 MHz, R = 0.01 m, εᵣ = 78,
>   σ = 0.05 / 0.57 S/m** → `t₁ = 14.0`, `t₂ = 160`, separation
>   `(6400+25600)/(6400+197) = 4.85`, `|k_in|R = 0.179`. Note `TH-8` today is
>   `SPHERE_RADIUS = 0.05`, `K0_R` fixed, `EPSILON_R_SPHERE = 78.0`
>   (`tests/validation/test_dielectric_sphere.py:61-73`), so **f and R both
>   move** for this step — recompute both numbers at whatever the fixture ends
>   up using and put them in the test's docstring. Gate the separation at a
>   bound *below* the computed ceiling (≈ 4 ⇒ assert > 3), never at a round
>   number chosen first.
> * If a negative result comes back — the interior SAR misses its closed form,
>   or the separation lands under 2 — **report the measurement and stop**. The
>   artifact is an annotation on this entry and a known-issues entry if a test
>   is left red; do not widen the tolerance to swallow it, and do not fall back
>   to the σ-blind control's 2.5×.
> **Step 1 audit (2026-08-03, 03:00 review) — ✅ stands, §4-compliant on every
> criterion.** All nine executed checks re-verified against
> `20260803T020448Z_MAT-4-step1-gate.log:494-500`; every figure reproduces
> exactly and none is rounded in the commit's favour.
> `git show --name-status c0d1d73` touches **zero** existing test files. One
> characterisation worth keeping straight: the σ-blind control is **analytic**
> (`test_lossy_sphere_sar.py:252`, `ratio_blind = σ₂/σ₁`), not a second executed
> σ-blind solve — which is correct, since a σ-blind solver returns that ratio
> exactly by construction and no run could tell you otherwise, but it is a
> reasoned control rather than a measured one and should be described that way.
>
> **Step 2 — mass-averaged SAR (one run; independent of everything else in the
> queue).** *(Scoped 2026-08-03, 03:00 review; previously one line reading
> "needs ρ as a field and an averaging-volume decision".)*
> **Read the sizing trap first — it is the whole design constraint.** At
> ρ = 1000 kg/m³ the step-1 sphere (R = 0.01 m) has a total mass of
> **4.19 g**, and a 1 g averaging volume is `1e-6 m³` ⇒ an equivalent sphere of
> radius **6.20 mm = 0.62 R**, i.e. larger than the 0.55 R core where step 1
> measured the field uniform to 0.07%/0.11%. **10 g exceeds the whole phantom.**
> So this fixture cannot carry a physical 1 g/10 g claim, and a run that assumes
> it can will spend the hour discovering that. Growing R is not the escape:
> `|k_in|R = 0.179` already, and it scales linearly, so R = 0.03 m puts the
> closed form out of its quasi-static regime.
> **Anchor — gate the averaging *operator*, on a mass that fits.** Take
> `m_avg = 0.05 g` ⇒ `V = 5e-8 m³` ⇒ radius **2.29 mm = 0.23 R**, comfortably
> inside the uniform core. Two quantitative assertions: (i) **the uniform-field
> identity** — where the field is uniform, averaging is the identity operator, so
> `SAR_avg(x)/SAR_point(x) = 1` for `x` in the deep interior, to a tolerance
> taken from step 1's *measured* 0.07%/0.11% interior spread plus the
> averaging-volume discretisation (state the budget in the docstring; do not pick
> a round number); (ii) **mass conservation of the kernel** — the averaging
> volume's mass `∫ρ dV` over the meshed averaging region equals `m_avg` to the
> same relative accuracy as step 1's meshed sphere volume (0.9964 of analytic at
> the fine mesh), which is what catches an averaging region that silently
> truncates at the mesh boundary.
> **Negative control, ceiling computed:** average at the sphere's **surface**
> instead of its centre. There roughly half the averaging volume lies in the
> lossless exterior (σ = 0), so `SAR_avg/SAR_point ≈ 0.5` against 1.0 at the
> centre — a **~2× separation, and that is the ceiling**, not a factor to be
> improved on. Assert > 1.5, and say in the docstring why 2 is the arithmetic
> maximum. Do not reach for a bigger factor by shrinking the phantom.
> **Cost:** standard tier, `-n 2`, **~45 s** — reuse the step-1 fixture and its
> solves unchanged (39.4 s measured); the averaging is post-processing on an
> already-solved field.
> **Traps already paid for:** ρ becomes a DG0 field, so it must be built through
> `build_material_fields`, not a python float multiplied in afterwards;
> `assemble_scalar` is rank-local and an averaging volume straddles rank
> boundaries — allreduce numerator *and* denominator separately before dividing,
> as `post/sar.py:123` already does; do not route through
> `post/phantom_fields.py` (the `POST-1` `float64` cast discards `Im E`, ~5×
> wrong here); keep the ½ peak-phasor convention consistent with `mean_sar` and
> `poynting_power_balance`.
> **Does not close:** `MAT-4` as an IEEE C95.3-conformant 1 g/10 g SAR — that
> needs a phantom large enough to contain the averaging volume with margin, and
> the honest place for it is the coil+phantom fixture once `GEO-9` step 2 lands.
> Say so, and hold `MAT-4` at 🟡 rather than claiming the standard.
> **Negative result:** if the uniform-field identity misses, that is information
> about the averaging kernel, not a licence to widen it — report the ratio,
> annotate this entry, and stop.

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

**`MAT-6` step 2a — fixture + cost/air-box probe** 🧪 *(demoted from ✅
2026-08-02, 18:00 review: its deliverable is `scripts/probes/mat6_step2a_probe.py`,
a script that prints and asserts nothing, so §4.3 is not met — see the §3
"measurement-only step" note. The measurements below stand and are fully
log-backed; only the symbol was wrong. `MAT-6` the **chunk** remains ✅ on
step 2b's ΔR-vs-Dodd–Deeds gate at 1.58%, which is unaffected.)* *(2026-07-31, 04:30
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
> attempt 1 measured at 1.07× and disproved.
>
> **Audit corrections, 18:00 review (§4-compliant, kept ✅).** Three things the
> entry got wrong or left out, none of them affecting the verdict:
> 1. "The gate prints every measured number to the log" is **false as written**.
>    The four residuals are printed (log lines 62–67); the *rate* and the
>    *separation* are computed inside the assert bodies
>    (`test_current_divergence.py:165, 201`) and appear only on failure —
>    `grep rate` and `grep separation` over the log of record return nothing.
>    Both are exactly recoverable from the printed values, so nothing is
>    unverifiable, but a later drift in the rate is **not** separable from a
>    regression without opening the file. Printing them is a one-line fix for
>    whoever next touches this test; it is not worth a run of its own.
> 2. **Which bounds can actually fail.** `rate > 0.7` against a measured 0.9422
>    is the load-bearing gate — it trips on a ~10% degradation of the 12³
>    residual. `coarse < 0.15` is self-fitted (the test comment says "~1.6× the
>    measured 9.3e-2") but still excludes 85% of the metric's attainable range,
>    which is Cauchy–Schwarz-bounded by 1. `cg1 < 1e-10` (measured 6.1e-15) and
>    `separation > 1e6` (measured 1.5e13) are **structural tripwires, not
>    regression gates**: they cannot fail gradually. Two consequences worth
>    knowing before anyone tightens this file — `separation > 1e6` is the only
>    floor anywhere under the CG2 residual and it sits ~6e-9, so CG2 could
>    collapse seven decades into round-off and only the two-point rate would
>    notice; and the CG1 residual at 12³ is **1.768e-14**, 3× the 8³ value the
>    entry quotes, so `1e-10` carries less margin than "4 decades" suggests if
>    the mesh ever moves. Neither is a reason to loosen anything.
> 3. The log of record was produced at commit `6c10e96`, which contains neither
>    the module nor the test — the gated code was still working tree at run
>    time. The post-commit cohabitation log
>    `20260802T213440Z_POST-3-step3-cohabit.log` (12 passed in 68.33 s at
>    `-n 2`, commit `e6de89d`) is what closes that gap, and it is the log to
>    cite when this gate's provenance is questioned.
>
> **What step 3 does *not* close.** The residual is scored on a boundary-driven
> fixture with no volume source; on a coil drive the identity holds only outside
> the source support (trap (ii)), and nothing here exercises that case yet. The
> `POST-3` chunk itself stays 🟡 for the reasons listed above — piecewise μᵣ and
> reciprocity are still open, and the `POST-1` cast defect still means the
> *phantom-field* metrics are taken on `Re(E)`.
>
> **Reciprocity is discharged by `PORT-1` step 2, not by a fourth `POST-3` step**
> *(decision, 18:00 review 2026-08-02)*. The note above says reciprocity "waits
> for `GEO-8` + `PORT-1` step 1, which produce a two-source fixture for free".
> Both have now landed, and the free fixture turns out to carry the identity
> directly: `‖Z − Zᵀ‖/‖Z‖` on the two-torus reaction Z-matrix **is** the
> field-level reciprocity `∫E₁·J₂ = ∫E₂·J₁`, measured at 7.9e-14 by step 1 and
> gated by step 2. Writing a second `POST-3` metric over the same integral would
> duplicate it. `POST-3` therefore has exactly one open leg of its own —
> piecewise μᵣ, which still waits on a magnetic phantom — and the chunk stays 🟡
> until that and the `POST-1` cast defect are settled.
>
> **Step 4 — phasor-magnitude semantics for the phantom-field extraction (one
> run; the `POST-1` cast defect, owned here per the 2026-07-31 note above).**
> *(Scoped 2026-08-03, 10:30 review.)* `post/phantom_fields.py::_evaluate_on_cells`
> casts every sampled value to `float64` at **two** sites — the batch path
> (`phantom_fields.py:88`) and the point-by-point fallback
> (`phantom_fields.py:102`) — so under the complex build every downstream
> phantom-field statistic is `Re(E)` at phase 0, silently (a `ComplexWarning`
> is the only trace, and warnings don't fail CI). The fix is the semantics, not
> the dtype: carry the complex phasor through extraction and report statistics
> on the **phasor magnitude** (the §11 peak-phasor convention, same as
> `SAR = σ|E|²/2ρ`), documented in the module docstring.
> **Anchors, two identities (§4.3 symmetry class), both on the piecewise-σ
> fixture from `test_poynting_balance.py` (tagged cells + complex solve,
> already costed — the step-2 suite is 64.5 s, one solve is a fraction of it):**
> (i) *code-path equivalence* — the per-point magnitudes `phantom_fields`
> reports must match `|·|` of the complex samples from
> `post.evaluation.evaluate_vector_field_parallel` at the same points to
> `1e-12`; (ii) *phase-rotation invariance* — multiply the solved `Function` by
> `e^{jπ/2}` and by one non-trivial angle (`e^{jπ/5}`), and every reported
> statistic must be invariant to `1e-12`. Both are exact identities; neither
> can be satisfied by the current cast.
> **Negative control — measure the ceiling first, do not name a factor in
> advance.** Reproduce the old behaviour beside the fix (`Re`-cast of the same
> samples) and *print* its deficit against the honest magnitude plus its
> movement under the two rotations. Expectation to check against, not assert:
> for phase ≈ uniformly distributed over the sample (print the measured phase
> span — the fixture's field carries `βz` through the slab), `mean|Re(E)|`
> sits near `2/π ≈ 0.64` of `mean|E|` **at every rotation angle**, so the
> rotation-*variance* of the broken path may be small even though its *value*
> is ~36% wrong — the deficit, not the variance, is the load-bearing control.
> On an in-phase field both go to zero, which is exactly how this bug survived
> `TH-8`. Set the control assertion from the measured deficit with the reason
> in the docstring (the `GEO-9` step-1 band precedent).
> **Cost:** standard tier, `-n 2`, ~60–90 s — one piecewise-σ solve plus
> sampling; no new mesh. Complex build + `FEM_EM_REQUIRE_COMPLEX=1`.
> **Traps already paid for:** the fallback path has the same cast — fix both
> sites or the guardrail branch silently reverts the semantics; any global
> statistic must allreduce numerator and denominator — `POST-1` is `⚠️`, so
> treat the existing aggregation as unverified rather than correct; keep the ½
> peak-phasor convention; pytest captures prints without `-s`.
> **Does not close:** `POST-3` (piecewise μᵣ still waits on a magnetic
> phantom) or `POST-1` (`⚠️` — the interface-guardrail machinery is still
> unrevalidated; this step only makes its sampled values complex-correct).
> `MAT-4` step 2's "do not route through `post/phantom_fields.py`" warning
> stays until this lands, then re-points at whatever this step measures.
> **Negative result:** if the two paths disagree beyond `1e-12` at the same
> points, that is a finding about one of them — report both sets of samples,
> annotate this entry and the `POST-1` row, and stop; do not adjust either
> until it is understood.

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

**`PORT-1` — Real port excitation from the solved field** 🟡 *(status corrected
from ⬜ 2026-08-02, 18:00 review: a landed probe, five harness logs and a
completed measurement step is not "not started")*
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
> **Step 2 — the gate (one run).** *Rewritten 2026-08-02, 18:00 review, with
> every bound now stated from a step-1 measurement rather than left to the
> implementer. The original wording (10:30 review, 2026-07-31) is preserved in
> git at `ed5b95a`, the commit before this review.*
> `tests/validation/test_port_reaction_impedance.py`, one mesh, two solves, at
> **padding 0.08 / h_far 0.03** — 119738 cells, mesh 21 s + solves 21 s and
> 31 s, so ~75–90 s for the gate: **standard tier, `-n 2`**. Do not take
> padding 0.12 at h_far 0.02 (237926 cells); step 1 had it killed at 180 s
> inside the MUMPS factorisation.
>
> | # | assertion | bound | step-1 measurement | why this bound |
> |---|---|---|---|---|
> | i | `‖Z − Zᵀ‖/‖Z‖` | `< 1e-9` | 7.86e-14 / 3.06e-13 / 4.31e-13 | four orders of slack over the worst measured value, and still catches any real symmetry break — reciprocity is at machine precision, so this bound is free |
> | ii | `Im Z₁₂` vs `ωM₁₂ = 1.241755 Ω` | within **10%** | −9.35% at this exact configuration | the gap is the PEC box, not the mesh: h_far 0.02→0.03 moves it 0.09%, padding 0.08→0.12 moves it 5.20% and monotonically toward the closed form. **Do not tighten** — the filamentary reference itself spans 66.5% of nominal over ρ, z within ± r_wire, so the closed form cannot support better |
> | iii | `Re Z₁₂` | `== 0.0` exactly, or `< 1e-30` | exactly `0.0` | structural, not a convergence result: the lossless operator is real-symmetric, so the real part is absent rather than cancelled. Assert it as structure and say so in the docstring |
> | iv | diagonal | **not gated** | `Im Z₁₁ ≈ −40.9 Ω` vs an expected `+ωL ≈ 6.8 Ω` | the diagonal is wrong in sign and undiagnosed (step 2b). Gating "sign and order" would gate a known-bad number; leave it out, print it, and let step 2b own it |
> | v | `M(2d)/M(d)` doubling | **✅ step 2c, 2026-08-03** | 0.270089 vs closed form 0.287120, −5.93% (bound 10%) | needed its own two meshes *and* a larger box (padding 0.12): the PEC wall costs the wider separation more, so its error does not cancel out of the ratio |
>
> Then convert through the existing `S = (Z − Z₀I)(Z + Z₀I)⁻¹` path with
> `Z₀ = 50 Ω` and assert S symmetric and passive (`‖S‖₂ ≤ 1`) — this is the
> first S-matrix in the repo derived from a solved field, and it is what makes
> the step §4.3-compliant on its own. Wire the file into `validation-complex`.
> **Negative control**: the pre-`GEO-8` fixture returned `Z₁₂` **identically
> zero** against `ωM₁₂ = 1.2418 Ω`, so the honest-vs-broken separation on
> assertion (ii) is total, not a factor — say so in the docstring rather than
> inventing a ratio. Traps: `ufl.max_value` does not compile in the complex
> build (use the regularised-sqrt current pattern from
> `test_dodd_deeds_impedance.py`); every `I` is the **meshed** loop current
> `∫J dV/(2πa)`, never the nominal one (a 17% error that looked like physics in
> `MAT-6` step 2a); a killed run leaves a stale FFCx lock — `rm -rf
> ~/.cache/fenics` before the next; `-k a or b` splits into stray argv inside
> an already-quoted container command. Scope boundary: this closes reciprocity
> and mutual coupling on a **two-loop air fixture**, and closes `PORT-1` step 1
> retroactively (§3: the probe's numbers finally carry an assertion). It does
> **not** close `PORT-1` — gap-voltage ports on a real coil are step 3 — and it
> does **not** resolve the two red port tests (known-issues 3). If a bound
> comes back missed, **report the measurement and stop**; annotate this entry
> and open a known-issues entry rather than widening (ii) past 10%.
>
> **Step 2 executed 2026-08-02 (19:30 run) — ✅ §4-done, and it retroactively
> closes step 1 (🧪 → ✅: the step-1 numbers now carry assertions).**
> `tests/validation/test_port_reaction_impedance.py`, four tests, **4 passed in
> 56.1 s** at `-n 2`, standard tier, complex build
> (`20260803T003217Z_PORT-1-step2-gate.log`). One mesh at padding 0.08 /
> h_far 0.03 — **119738 cells, mesh 20.9 s, solves 19.2 s and 15.2 s**, i.e.
> the step-1 cost model held (predicted 75–90 s, measured 56 s; the second
> solve is faster than step 1's 31 s because the file solves only this one
> box). The file is wired into the `validation-complex` CI job.
>
> Every gated number reproduced the step-1 measurement it was sized from:
>
> | # | assertion | bound | measured 2026-08-02 | step-1 value |
> |---|---|---|---|---|
> | i | `‖Z − Zᵀ‖/‖Z‖` | `< 1e-9` | **2.6497e-13** | 3.06e-13 at this configuration |
> | ii | `Im Z₁₂` vs `ωM₁₂ = +1.241755 Ω` | within 10% | **+1.125614 Ω, −9.35%** | +1.125614 Ω, −9.35% — bit-for-bit |
> | iii | `Re Z₁₂` | `< 1e-30` | **exactly +0.000000e+00** | exactly 0.0 |
> | iv | S symmetric + passive at `Z₀ = 50 Ω` | `‖S−Sᵀ‖/‖S‖ < 1e-9`, `‖S‖₂ ≤ 1` | **2.5993e-13** and **‖S‖₂ = 1.000000000000** | new here |
>
> `M₁₂ = 1.976314e-08 H`; `S₁₁ = −1.941026e-01 − 9.806119e-01j`,
> `S₂₁ = −2.639550e-02 + 5.277699e-03j`; meshed currents 0.969009 A on both
> tori, identical to all printed digits; `k₀·diag = 0.08618`. **This is the
> first S-matrix in the repository derived from a solved field.** Because the
> domain is lossless and reciprocal, S is unitary, so the file asserts
> `|‖S‖₂ − 1| < 1e-9` as well as passivity — the sharper statement of the same
> physics, and the one a real part leaking into Z would break. No bound was
> loosened and no assertion was weakened from the step-2 table above; item (v)
> stayed split out as step 2c.
>
> **Left ungated on purpose:** the diagonal. The gate prints
> `Im Z₁₁, Im Z₂₂ = −4.108550e+01, −4.092413e+01 Ω` and asserts nothing about
> them — still negative where a lossless loop must be inductive, still `PORT-1`
> step 2b's to diagnose. Step 2c (the `M(2d)/M(d)` doubling control) did land in
> this file, ✅ 2026-08-03. Also still open: step 3 (gap-voltage
> ports) and the two deliberately-red port tests (known-issues 3). `PORT-1`
> therefore stays 🟡.
>
> **Audit (2026-08-03, 03:00 review) — ✅ stands, §4-compliant on every criterion;
> two notes that change how the coverage should be counted, not the status.**
> Every headline number was re-verified against
> `20260803T003217Z_PORT-1-step2-gate.log` (lines 430–442, 458) and reproduces
> exactly; `git show --diff-filter=M --name-only c299ab1` touches no test file,
> so "nothing was loosened" is verifiable and true; the reciprocity check is
> genuinely non-trivial, since `Z[0,1]` and `Z[1,0]` come from two different
> solves (`test_port_reaction_impedance.py:204,222-226`).
> * **The unitarity assertion is not a fourth independent physics check.** Once
>   `Re Z ≡ 0` (assertion iii) and `Z` is symmetric (assertion i), `‖S‖₂ = 1`
>   follows algebraically for *any* purely imaginary symmetric `Z`. The file says
>   as much in its own docstring, and it is a legitimate identity — but it should
>   not be tallied as independent coverage, and it constrains nothing about the
>   diagonal's sign or magnitude. That is *why* step 2's S-matrix could pass with
>   a diagonal step 2b then showed to be physically meaningless.
> * **The reciprocity residual is normalised by `‖Z‖ ≈ 58 Ω`, which the diagonal
>   dominates, not by `|Z₁₂| ≈ 1.13 Ω`.** The `1e-9` bound is therefore ~50×
>   looser in `Z₁₂`-relative terms than it reads. It costs nothing at 2.6e-13,
>   but if a later step changes the diagonal's magnitude — which is exactly what
>   a step-2e fix would do — the normalisation should move to `|Z₁₂|` in the same
>   commit, or the bound silently tightens by 50× and the drift gets blamed on
>   the fix.
>
> **Step 2b — the self-impedance diagnosis (one run; independent of step 2).**
> *(New 2026-08-02, 18:00 review.)* Step 1's diagonal is not merely imprecise,
> it is the wrong sign: `Im Z₁₁ ≈ −40.9 Ω` where a lossless loop must be
> inductive. Nothing in the plan can currently say whether the reaction
> integral's self-term is wrong or the fixture is genuinely
> capacitance-dominated, and until that is settled no Z-matrix diagonal — and
> therefore no input impedance and no S₁₁ — means anything. **Anchor: the
> complex-power identity, an independent derivation from the same solved
> field.** In a lossless PEC box with an impressed current source,
> `Z_in = 2P_in/|I|²` with `P_in = −½∫E·J* dV`, and Poynting's theorem reduces
> it to `Im Z₁₁ = 4ω(W_m − W_e)/|I₁|²`, where `W_e = (ε₀/4)∫εᵣ|E|² dV` is
> already computed by `core/resonance.py::stored_electric_energy` (peak-phasor,
> matching §11) and `W_m = (1/(4μ₀ω²))∫|∇×E|² dV` is three lines of UFL
> alongside it. The run computes both and compares against the reaction-integral
> diagonal. **Two outcomes, both informative** — which is why this item is worth
> a slot: if the energy route reproduces −40.9 Ω, the reaction integral is right
> and the *fixture* is electric-energy-dominated at 10 MHz, which is a finding
> about the two-torus box (and about every `Z_in` anyone would later read off
> it); if it returns `+ωL` instead, the reaction integral's self-term is the
> bug, localised to the source-region integral, and the third anchor —
> Grover's `L ≈ μ₀a(ln(8a/r_wire) − 2)`, `ωL ≈ 6.8 Ω`, **compute it in code, it
> is prose-only today** — says which is right. Cost is known and is step 2's:
> one mesh at padding 0.08 / h_far 0.03, one solve, ~50 s, standard tier,
> `-n 2`; `W_e` is already in the probe's `--energy-sweep` path. Traps:
> `assemble_scalar` is rank-local — allreduce `W_m` as `stored_electric_energy`
> already does for `W_e`; `ufl.inner` conjugates its second argument, so
> `inner(curl E, curl E)` is `|∇×E|²` and is real up to round-off. Scope
> boundary: this is a **diagnosis**, and it closes nothing on its own — if it
> localises the bug, the fix is a separate step. If both routes agree on a
> negative number, **report it and stop**: the artifact is an annotation here
> plus a known-issues entry, not a sign flip applied to make the number look
> right.
>
> **Step 2b executed 2026-08-03 (00:00 run) — ✅ §4-done as a diagnosis, and it
> answers the question with the outcome the step called "informative but
> negative": the reaction integral is right, the fixture is the problem.**
> New file `tests/validation/test_port_self_impedance_energy.py`, three tests,
> **3 passed in 43.5 s** at `-n 2`, standard tier, complex build
> (`20260803T050252Z_PORT-1-step2b-gate.log`). One mesh at padding 0.08 /
> h_far 0.03 — 119738 cells, mesh 22.9 s — and **one** solve, 19.5 s; the file
> imports the step-2 file's constants and helpers so the two cannot drift, and
> it is wired into `validation-complex`. Meshed current 0.969009 A, identical to
> step 2's.
>
> | quantity | measured | reference |
> |---|---|---|
> | `Im Z₁₁`, reaction integral | `−4.108550e+01 Ω` | step 2's ungated print, bit-for-bit |
> | `Im Z₁₁`, complex power `4ω(W_m−W_e)/I²` | `−4.108550e+01 Ω` | — |
> | relative disagreement | **1.8128e-10** | **gated `< 1e-9`** |
> | `Re Z₁₁` | exactly `−0.000000e+00` | gated `< 1e-30`, structural |
> | `4ωW_m/I²` | `+7.437 Ω` | Grover `ωL = 6.818 Ω`, **ratio 1.0908** — printed, not gated |
> | `4ωW_e/I²` | `+48.52 Ω` | — |
> | `W_e/W_m` | 6.524 | — |
>
> The step named two outcomes; this is the first one, sharpened. The two routes
> agree to 1.8e-10, so **the self-term of the reaction integral is not the bug**
> — the guess recorded in known-issues was wrong and is corrected there. Grover
> then localises the anomaly to one half of the identity: `4ωW_m/I² = 7.437 Ω`
> is the physical loop inductance to 9.1%, within what the PEC box at this
> padding can account for, so the whole of `−40.9 = 7.44 − 48.52` is an
> **electric-energy excess**. The two-torus box at 10 MHz is electric-energy
> dominated by 6.5×, which invalidates any `Z_in` or `S₁₁` read off this
> fixture's diagonal — exactly as the step warned, and now measured rather than
> suspected. Grover's `ωL` is no longer prose-only: `grover_loop_inductance()`
> computes it and the log prints 6.818343e+00 Ω.
>
> The identity's bound deserves one caveat for whoever touches it next: 1.81e-10
> against 1e-9 is **5.5× of margin, not the four orders the other `PORT-1`
> bounds carry**, because the residual is limited by the MUMPS solve and the
> quadrature agreement of the two form pairs rather than by physics. If a rank
> count, solver or mesh change moves it, re-measure and record — a drift there
> is information about the solve, and widening the bound would discard it.
>
> **Leading hypothesis for the fix step (not measured, do not treat as
> established):** low-frequency breakdown of the curl-curl formulation. At
> ω → 0 the operator acts on the gradient subspace as `−k₀²ε_c`, so any residual
> non-solenoidal component of the *discretised* impressed current — the analytic
> azimuthal `J` is exactly divergence-free and tangent to the torus surface, but
> the faceted meshed boundary is only approximately so — is amplified into a
> spurious electrostatic field that lands in `W_e` and nowhere else.
>
> **Correction (2026-08-03, 03:00 review): the ω-sweep this entry named as "the
> discriminating measurement" does not discriminate, and queueing it as written
> would have bought a run that could not answer the question.** Restrict the
> solved equation to the gradient subspace: `E = ∇φ` gives `∇×E = 0`, so
> `−k₀²ε_c∇φ = −jωμ₀J_g` and, in air,
> `E_g = jωμ₀J_g/k₀² = jJ_g/(ωε₀) ∝ 1/ω`. Hence `W_e ∝ ω⁻²` and
> `4ωW_e/I² ∝ ω⁻¹` — **exactly the `1/(ωC)` a physical capacitance gives.**
> Gradient-space contamination *is* a spurious electrostatic response, so of
> course it scales like one. The sweep separates only the capacitive family
> (`ω⁻¹`) from an induction-driven `E = −jωA` (`E ∝ ω`, `W_e ∝ ω²`,
> `4ωW_e/I² ∝ ω³`) — a cheap sanity check, not the discriminator, and not worth
> a slot on its own.
>
> **What does discriminate, and why this fixture makes it decisive.** The
> two-torus fixture has **no conductors**: the tori are tagged *air* subdomains
> carrying an impressed `J`, and the only metal is the outer PEC wall. With
> `∇·J = 0` analytically there is no charge and therefore **no physical
> capacitance available to find** — so a `ω⁻¹`-family `W_e` of this size is
> already evidence of discrete current divergence, and the open question is
> quantitative rather than categorical: does the gradient content of the load
> account for all 48.52 Ω, or only part of it?
>
> **Step 2d — charge the electric-energy excess to the load vector (one run;
> independent of 2c and 3).** *(New 2026-08-03, 03:00 review.)*
> **Anchor — an exact discrete identity, in the step-2b two-route mould.** For
> the N1curl/CG1 pair the discrete sequence is exact, so `∇q` is in the trial
> space for every `q ∈ CG1 ∩ H¹₀` and the curl term annihilates it *identically*.
> Testing the assembled system with `v = ∇q` therefore gives, with no
> approximation and no extra solve,
> **`∫E_h·∇q dV = (j/(ωε₀))·∫J·∇q dV` for every such `q`** — two assemblies of
> the solved field and the impressed current, compared in a vector norm. This is
> the low-frequency analysis above, asserted against the actual solve rather than
> argued. Expect solver precision; step 2b's comparable residual was 1.8e-10, so
> take `1e-9` as the house bound, **cost-probe it and record what it actually is**
> — and if it comes back at 1e-3, that is the more interesting result, because it
> says the gradient subspace is *not* behaving as the analysis claims.
> **Then the physics number, reported not gated:** solve
> `∫∇ψ·∇q dV = ∫J·∇q dV`, `ψ ∈ CG1 ∩ H¹₀` (one cheap scalar Poisson solve), so
> that `∇ψ = P_G J` and `‖P_G J‖² = ∫J·∇ψ dV`; the spurious reactance is then
> `4ωW_e^spur/I² = ‖P_G J‖²/(ωε₀I²)`. Print it beside the measured
> `4ωW_e/I² = 4.852271e+01 Ω`
> (`20260803T050252Z_PORT-1-step2b-gate.log:436`). **That ratio is the answer the
> step exists for.**
> **Negative control, with its ceiling read first:** a discretely solenoidal
> current gives `P_G J = 0` *exactly*, so the honest-vs-blind separation is
> total, like step 2's pre-`GEO-8` `Z₁₂ ≡ 0` — state it as such rather than
> inventing a factor. The informative outcome is **partial** agreement: a
> prediction of ~5 Ω against a measured 48.5 Ω means the gradient content
> explains a tenth and something else owns the rest.
> **Cost:** standard tier, `-n 2`, budget **~60 s** — one mesh at padding 0.08 /
> h_far 0.03 (119738 cells, **22.9 s**) and one curl-curl solve (**19.5 s**),
> both measured by step 2b, plus a CG1 Poisson solve far cheaper than the N1curl
> one. Step 2b's whole file was 43.5 s.
> **Traps already paid for:** `ψ` and `q` must carry the Dirichlet condition that
> matches the PEC wall (`n×E = 0` ⇒ `φ` constant on the boundary ⇒
> `ψ, q ∈ H¹₀`), or the identity is testing a different operator and will miss
> for a reason that is not physics; `assemble_scalar` is rank-local — allreduce
> before asserting; `ufl.inner` conjugates its second argument; every `I` is the
> **meshed** loop current 0.969009 A, never the nominal; `ufl.max_value` does not
> compile in the complex build, so import `_azimuthal_current_density` from
> `test_port_self_impedance_energy.py` rather than re-deriving the current
> pattern; a killed run leaves a stale FFCx lock (`rm -rf ~/.cache/fenics`).
> **Does not close:** `PORT-1`, and not even the diagonal — a confirmed cause
> licenses a fix step, it is not the fix. The diagonal stays ungated and the
> known-issues entry stays open either way. A current representation that is
> discretely divergence-free would be step 2e, and is deliberately not written
> until 2d reports.
> **Negative result:** report the ratio, annotate this entry and the known-issues
> entry, and stop. Do not tune `ψ`'s boundary condition until the two numbers
> meet.
>
> **Scope: step 2b closes nothing.** The diagonal stays ungated in
> `test_port_reaction_impedance.py`, known-issues' negative-diagonal entry stays
> open with its diagnosis appended, and `PORT-1` stays 🟡.
>
> **Audit note (2026-08-03, 03:00 review), for whoever moves this code:**
> `stored_magnetic_energy()` landed in
> `tests/validation/test_port_self_impedance_energy.py:117`, **not** in
> `core/resonance.py` — commit `26a4e7b` touches no file under `src/`. The step-2b
> text above ("three lines of UFL alongside it") reads as an invitation to put it
> next to `stored_electric_energy`, and it was not taken; for a diagnosis that
> changes no production code that is the right call, but any later step that
> wants `W_m` in the solver must move it first. Also: "bit-for-bit" against
> step 2's diagonal is really "identical to all printed digits" — seven
> significant figures, which is what two prints can establish.
>
> **Step 2c — the `M(2d)/M(d)` doubling control (one run; independent).**
> Step 1's item (v), split out because a second separation needs a second mesh.
> Anchor: `M(2d)/M(d) = 0.287120` from
> `utils/analytical.py::circular_loop_vector_potential` (Jackson 5.37),
> measured by step 1 on the same geometry. Assert the FEM `|Z₁₂|` ratio between
> `d = 0.04` and `d = 0.08` against it at the same 10% the box sensitivity
> justifies for (ii) — and note the two boxes differ, so some box error
> cancels in the ratio and some does not; measure before tightening.
> **Negative control**: a solver blind to separation returns ratio 1.000 where
> the closed form says 0.287 — a 3.5× separation, which is the ceiling here and
> is ample. Cost: two meshes + two solves at padding 0.08 / h_far 0.03,
> ~150–180 s — **at the edge of the standard tier, so cost-probe the second
> mesh first and take heavy if it does not fit**. If step 2 has landed, add the
> test to `test_port_reaction_impedance.py`; if it has not, this is a standalone
> file and does not wait. Negative result: report and stop.
>
> **Step 2c ✅ 2026-08-03 (06:00 run), at padding 0.12 — option (b) below, and
> the sweep's predicted landing point held.** Gate:
> `20260803T110902Z_PORT-1-step2c-gate12-numbers.log:1256`, 5 passed in 167.7 s,
> `-n 2`, heavy tier declared for an unmeasured solve but 168 s elapsed.
> * **`|Z₁₂(2d)|/|Z₁₂(d)| = 0.270089` against the closed-form `0.287120`,
>   −5.93%** inside the 10% bound — **1.69× of margin**, against the 1.1× that
>   padding 0.10 would have bought. The bound was *not* touched.
> * The per-separation box errors that caused the failure both shrank as
>   predicted: **−4.64% at `d`, −10.30% at `2d`** (from −9.36% / −21.4% at
>   padding 0.08). The gap between them, which is what the ratio actually sees,
>   narrowed from 12.0 to 5.7 points.
> * **Cost-probed first, and the 2.3×-cells fear was wrong**: 154493 cells at
>   `d` and 169502 at `2d`, **1.29× and 1.42×** step 2's box, meshes 27 s and
>   30 s (`20260803T110058Z_PORT-1-step2c-costprobe12.log:417,823`) — well clear
>   of the 237926-cell case MUMPS was killed on. The ratio solve then measured
>   122 s for the pair (`20260803T110209Z_PORT-1-step2c-ratio12.log:825`).
> * **The probe and the test agree bit-for-bit** — `|Z₁₂(d)| = 1.184134e+00`,
>   `|Z₁₂(2d)| = 3.198216e-01 Ω` in both — so the gate is not a second
>   implementation of the physics that happened to land nearby.
> * **Step 2's four assertions are untouched and still pass**, because step 2c
>   pays for its own two meshes rather than re-siting the shared fixture: the
>   ratio is only meaningful with both separations in one box, and step 2's box
>   is the padding-0.08 one its own bounds were justified against. File cost is
>   now ~168 s, which is the standard-tier ceiling — the next thing added here
>   needs its own file.
>
> **Step 2c's first attempt, 2026-08-03 (04:30 run) — NEGATIVE at the step-2
> configuration, kept because it is the measurement that sized the box above.**
> The control was built as specified and executed; what fails is the *bound* at
> padding 0.08, not the method. Numbers, all reproducible:
> * **Anchor confirmed independently.** `M(2d)/M(d) = 0.287120` re-evaluated
>   from `circular_loop_vector_potential`, matching the queued value to all six
>   figures (`20260803T093119Z_PORT-1-step2c-costprobe.log:34`).
> * **The second mesh is cheap** — the cost probe the plan demanded was worth
>   running, but not for the reason feared: `d = 0.08` at padding 0.08 / h_far
>   0.03 is **127763 cells, 1.067× step 2's**, mesh 22.4 s, solve 14.5 s. The
>   taller box is nowhere near the 237926-cell case MUMPS was killed on, so
>   step 2c is a **standard-tier** item, not heavy.
> * **The gate fails: ratio 0.248854 vs 0.287120, −13.33%** against the 10%
>   bound (`20260803T093329Z_PORT-1-step2c-gate.log:843`). The other four
>   assertions in the file passed unchanged, so this is not a step-2 regression.
> * **It fails because the PEC box hurts the wider pair more**, which the queued
>   item anticipated in words ("some box error cancels in the ratio and some
>   does not") but not in size. Per-separation: **−9.36% at `d`** (step 1's
>   −9.35%, reproduced) but **−21.4% at `2d`**. The ratio error is the
>   difference of two unequal box errors, not a fall-off error.
> * **Confirmed by a padding sweep, and the direction is right.** At padding
>   0.10 (`20260803T093617Z_PORT-1-step2c-boxsens.log:417-818`): −6.38% at `d`,
>   −14.60% at `2d`, **ratio 0.261901, −8.78%** — monotone toward the closed
>   form and *inside* 10%. Both errors shrink and their gap narrows.
>
> **What that attempt deliberately left to this one.** The
> padding-0.10 result would pass the gate as written, and re-siting the fixture
> there was left untaken: 8.78% against a 10% bound is 1.1× of margin, chosen
> **after** seeing it pass — the "was this fitted?" pattern the review audits
> for. The honest options are (a) re-site at padding 0.10 **and** state the thin
> margin in the test; (b) go to padding 0.12 — unmeasured, ~2.3× the cells at
> `d = 0.08`, so cost-probe it first — where the trend says the ratio should
> clear 10% with real margin; or (c) keep padding 0.08 and set the bound to the
> *measured* box error with the sweep quoted in the code comment, which is the
> `MAG-10`/`MAG-15` precedent. **(b) is the recommendation**: it is the only one
> that buys margin rather than redistributing it, and the sweep gives it a
> predicted landing point. What is *not* available is asserting 10% at padding
> 0.08.
> **(b) is what the 06:00 run executed, with the result above.** The parked gate
> code came off `attempt/PORT-1-step2c-20260803T094412Z` essentially unchanged —
> only the padding was parameterised — so the negative run's real product was
> the sweep, not the code.
>
> **Audit (2026-08-03, 10:30 review) — ✅ stands, decisively.** The 10% bound is
> provably older than both measurements (`git log -S`: written into §7 at
> `fb77d01`, 2026-08-02 18:15, ~10 h before the −13.33% and ~12 h before the
> −5.93%), the assert line is textually identical between the parked attempt
> `655ea26` and landed `5550f89`, step 2's four assertions are byte-unchanged,
> and the closed-form ratio is *recomputed* from `circular_loop_vector_potential`
> each run rather than hardcoded. Two records for later readers: the gate log's
> header names the parent commit `daadd31` (the run preceded the commit — the
> `POST-3` step-3 provenance pattern; the log body pins the code by content),
> and the printed "separation-blind control would give 1.000000" is an analytic
> statement in the f-string, not an executed control run — correct per the
> plan's own instruction, but it should be counted as stated, not measured.
>
> **Step 3a — move the Z→S conversion into `src/`, and point `PORT-5`'s metrics
> at a real matrix for the first time (one run; independent of 2c and 2d).**
> *(New 2026-08-03, 03:00 review — split out of step 3 because it does not need
> the birdcage, and step 3 was the only route to §10 Target criteria 2 and 3.)*
> Step 2 produced the repo's first S-matrix from a solved field, but as three
> numpy lines inside a test (`test_port_reaction_impedance.py:166-169`); the
> **package** still has only the placeholder path, so §10's "S-parameters derived
> from the solved field, not a coupling heuristic" is currently gated behind a
> birdcage mesh that does not generate. This step decouples them.
> **Anchor — a code-path-equivalence identity against a number already in a
> log.** Add `sparameters_from_impedance(z_matrix, *, z0_ohm)` to
> `ports/sparameters.py` — pure numpy, `S = (Z − Z₀I)(Z + Z₀I)⁻¹`, no import of
> `excitation.py` — then feed it the reaction Z from the two-torus solve and
> assert the result reproduces the step-2 gate's S **to `1e-12`**, entry by
> entry: `S₁₁ = −1.941026e-01 − 9.806119e-01j`,
> `S₂₁ = −2.639550e-02 + 5.277699e-03j`
> (`20260803T003217Z_PORT-1-step2-gate.log`). Second anchor, and the one that
> earns the step: run the **existing** `summarize_sparameter_sanity()` on that
> matrix and assert its reported metrics match the test's own —
> `reciprocity_max_abs_delta` at the 2.5993e-13 scale and
> `passivity_max_sigma = 1.000000000000` to `1e-9`. Those metrics have never
> been evaluated on anything but placeholder arithmetic, which is exactly why
> `PORT-5` is `⚠️`.
> **Negative control:** the placeholder path on the same two ports returns a
> matrix with an identically-zero diagonal (known-issues 3 — the fakes set
> `current = voltage/z0`, so `b = 0` exactly), against `|S₁₁| = 0.9996` here.
> Total separation on the diagonal, as with step 2's pre-`GEO-8` `Z₁₂ ≡ 0`;
> state it as such rather than inventing a ratio.
> **Cost:** standard tier, `-n 2`, **~60 s** — reuse the step-2 mesh and its two
> solves (56.1 s measured); the conversion and the metrics are microseconds.
> **Scope boundary, and it is the point of the split:** this is a *replacement*
> path, not an extension of the `⚠️` subsystem — do **not** touch
> `_power_waves`, `_assemble_sparameter_matrix`, `run_n_port_sparameter_sweep`,
> or `excitation.py`, and do **not** try to fix the two red port tests
> (known-issues 3), which stay red for `PORT-1` step 3b. Threading
> `is_placeholder=False` through `SParameterSweepResult` and `export_touchstone`
> is 3b's, because it needs the sweep path this step deliberately avoids.
> **Does not close:** `PORT-1`, `PORT-5` (its sweep-level metrics still run on
> the placeholder), or §10 criterion 2 in full — a two-loop air fixture is not a
> coil. It *does* mean the conversion and the sanity metrics live in `src/` and
> are gated against a solved field, so 3b inherits them rather than inventing
> them on a mesh that does not exist yet.
> **Negative result:** if the packaged conversion disagrees with the test's three
> lines, that is a finding about one of the two — report both matrices, annotate
> this entry, and stop; do not adjust either until it is understood.
>
> **Step 3a done 2026-08-03 (09:00 run)**, gate
> `20260803T140251Z_PORT-1-step3a-gate.log`, **9 passed 1 deselected in 58.0 s**,
> standard tier, `-n 2`, exit 0. `sparameters_from_impedance(z, *, z0_ohm)` is in
> `ports/sparameters.py` and exported from `ports/__init__.py`; it is pure numpy
> and touches nothing in the `⚠️` path (`_power_waves`,
> `_assemble_sparameter_matrix`, `run_n_port_sparameter_sweep` and
> `excitation.py` are all unmodified — the diff adds one function and one test,
> deleting nothing).
> * **Code-path equivalence exceeded its bound: `max|S_pkg − S_test| = 0.0000e+00`
>   against 1e-12** — bit-identical, not merely within tolerance, which is the
>   available outcome when both paths do the same operations in the same order.
> * **Cross-run agreement with the step-2 log:** `|ΔS₁₁| = 4.75e-08`,
>   `|ΔS₂₁| = 4.51e-09` against the logged `−1.941026e-01 − 9.806119e-01j` and
>   `−2.639550e-02 + 5.277699e-03j`. Held at 1e-6, not 1e-12, and the constant's
>   comment says why: the log prints seven figures, so 5e-8 is the rounding of
>   the printed value itself. Both residuals sit at that floor.
> * **The sanity metrics ran on a real matrix for the first time:**
>   `passivity_max_sigma = 1.000000000000` and `max column power sum =
>   1.000000000000`, both asserted to 1e-9 as *identities* (a lossless reciprocal
>   2-port is unitary, so unit column norms are exact, not fitted);
>   `reciprocity_max_abs_delta = 3.4981e-13`, `max rel = 1.2995e-11`, `warnings =
>   ()`. The run also confirms the arithmetic the test's comment claims: this
>   run's `‖S−Sᵀ‖/‖S‖` printed `3.4981e-13`, **equal to `max|Sᵢⱼ−Sⱼᵢ|`**, because
>   `‖S‖_F = √2` for a unitary 2×2. (The step-2 log's 2.5993e-13 is the same
>   quantity at that run's partition; both are machine precision.)
> * **Negative control, stated not measured, as the plan directed:** the
>   placeholder path returns an identically-zero diagonal on two ports
>   (known-issues 3 — the fakes set `current = voltage/z0`, so `b = 0` exactly)
>   against the measured `|S₁₁| = 0.999638`. Total separation.
> * Step 2c's doubling test was `--deselect`ed from this gate: it carries its own
>   two meshes and two solves (122 s measured) and was gated in the 06:00 run;
>   including it would have pushed a 58 s command past the standard tier for no
>   new information. The other nine tests in the file, including all of step 2's,
>   ran and passed.
> * **Still open, and 3a does not touch any of it:** `PORT-5` stays `⚠️` — its
>   *sweep-level* metrics still run on the placeholder — the two red port tests
>   (known-issues 3) stay red for 3b, and §10 criterion 2 stays open because a
>   two-loop air fixture is not a coil.
>
> **Audit (2026-08-03, 10:30 review) — ✅ stands; the 1e-6 substitution is an
> honest correction, not a loosening.** The plan's 1e-12 against the *logged*
> `S₁₁`/`S₂₁` literals was arithmetically unachievable — `%.6e` prints seven
> significant figures, a ~5e-8 half-ulp per component, so the target number
> does not carry the digits, and the measured residuals (4.75e-08, 4.51e-09)
> sit at that floor, the signature of a correct fixture rather than a bought
> pass. Nothing failed at 1e-12 and was then widened; the claim was split, the
> substitute bound named in a constant with its reason, and the deviation
> declared in plan, code, and attempts.md. The 1e-12 survives on the code-path
> comparison, where it was met at exactly 0.0. Two corrections for whoever
> touches the file: the `STEP2_LOGGED_S_TOLERANCE` comment's "at a different
> rank count" rationale is **false** — both gates ran at `-n 2`; the slack it
> justifies is real run-to-run drift (2.60e-13 → 3.50e-13 on the reciprocity
> residual), so fix the comment, not the constant. And the entry's "other nine
> tests in the file" is a miscount — nine is the whole run (five in this file
> plus four environment tests); step 2 has four tests here, not five.
>
> **Step 3b — gap-voltage ports on the tagged birdcage (directional; a later
> review firms this up, and it needs `GEO-9` step 2).** The MRI-relevant form:
> excite across the tagged gaps of `birdcage_port_domain`, recover `V = −∫E·dl`
> as a volumetric average over the gap (not point sampling), cross-check
> gap-voltage Z against reaction Z on a fixture where both apply, resolve the two
> deliberately-red port tests (below), and thread `is_placeholder=False`
> through to `export_touchstone`. Known trap: the birdcage suite is over the
> compute budget (known-issues) — the gate must run on a reduced-rung fixture,
> not the full birdcage mesh. **Blocked** until `GEO-9` step 2 makes that mesh
> generate at all.
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

> **Step 1 re-run 2026-08-02 (13:30 run) after `GEO-8` — ✅ *(restored by the
> 19:30 run: step 2's gate asserts these numbers, so the §4.3 defect the 18:00
> audit found is discharged)*; the numbers below sized step 2.**
> *(Demoted from ✅ by the 18:00 review audit. The step
> executed cleanly, all five logs are registered, and every headline number
> below was re-verified against them this review — but the committed
> deliverable is `scripts/probes/port1_step1_probe.py`, which contains no
> `assert` at all and says so in its own output, and no test file was added by
> `f72ef3a`. §4.3 requires an executed quantitative assertion and has no
> carve-out for probes; see the §3 "measurement-only step" note. Nothing here
> is retracted — step 2 writes the gate and this becomes ✅ with it.)*
> The probe landed unchanged at
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
>   diagonal assertion entirely.** Not diagnosed here. *(18:00 review: the
>   `Im Z₁₁` values are in the logs and were re-verified — `-4.069329e+01j`
>   at `20260802T183226Z_…-solve008.log:442,449`, `-4.108550e+01j` and
>   `-4.096890e+01j` in the boxsens log. The **Grover comparison `ωL ≈ 6.8 Ω`
>   is prose only**: it appears in no log, `grep Grover` over
>   `docs/testing/logs/` is empty, so it is a hand-evaluated closed form, not a
>   measurement. Step 2b below computes it in code rather than inheriting it.)*
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
   What remains is piecewise μᵣ and reciprocity.
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
   both fixed — 180 s hang → 13 s prompt failure, isolation gate exit 0. Step
   2b (the `occ.fragment` geometry rewrite) got its full plan at the 10:30
   review and is queued. Two of the four §10 Target criteria route
   through these fixtures, so this is on the critical path, not housekeeping.
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

Last reviewed 2026-08-03, 10:30 daily review. Tree clean; no `attempt/*` and no
`recovered/*` branches at review time. **One disposition note:** the 06:00 run
left `attempt/PORT-1-step2c-20260803T094412Z` in place "for the daily review to
dispose of", but the branch was already gone by 10:30 — deleted without a
journal entry saying so (the record does not say by whom; the tree also carries
a manual `chore(automation)` commit from 10:56, so a human was active). Verified
harmless before closing it out: the parked wip `655ea26` differs from the landed
`5550f89` only by the padding parameterisation and the sweep comment, so its
content is fully captured on main and nothing was lost. Recorded here because
an unjournaled branch deletion is the kind of silent tree change the disposition
step exists to catch, even when it turns out benign.

**4/4 slots again — the second consecutive clean interval.** 04:30 `PORT-1`
step 2c (negative at padding 0.08, journaled, code parked); 06:00 step 2c ✅ at
padding 0.12; 07:30 `GEO-9` step 2a ✅; 09:00 `PORT-1` step 3a ✅. Twelve harness
logs, all registered in `docs/testing/test-results.md`. The 04:30→06:00 pair is
the queue working as designed: a negative result that *answered the question*
(the box, not the physics), then a bound/fixture decision executed in the next
slot — one item costing two runs for the right reason. Nothing in this interval
needs a cron diagnosis.

**Audit of the three statuses that flipped ✅ — all three stand, no demotions.**
One auditor per step, each re-verifying the headline numbers against the cited
logs and checking `git show`/`git diff` for a loosened bound; full findings are
recorded as audit notes in the §7 entries.
* `PORT-1` step 2c — ✅ stands, decisively. The 10% bound provably predates both
  measurements (`git log -S`: written at `fb77d01`, ~10–12 h before either); the
  assert line is textually identical between the parked attempt and the landed
  commit; the negative attempt reported-and-stopped, and the fix bought margin
  with mesh (padding 0.12), not tolerance. Cosmetic: the gate log's header names
  the parent commit, and the "separation-blind control gives 1.000000" is an
  analytic statement, not an executed run.
* `GEO-9` step 2a — ✅ stands on every criterion. Purely additive test diff, the
  moved rank-0 geometry body is byte-identical (one-line dedent diff), the
  exception still raises loudly on every rank, and the volume identities are
  asserted from allreduce-reduced quantities. The anchor substitution
  (exit 124→1 in place of an exit 0 the item's own scope made unobtainable) is
  disclosed in three places and strictly stronger. Carry-forward: the no-hang
  `allreduce` assertion is vacuous at `-n 1` — the gate must stay at `-n 2`.
* `PORT-1` step 3a — ✅ stands; the 1e-6 substitution against the logged S
  literals is an honest correction of an arithmetically impossible plan bound
  (seven printed figures ⇒ ~5e-8 floor; the residuals landed *at* the floor),
  with 1e-12 retained and met at exactly 0.0 on the code-path comparison where
  it is meaningful. One falsehood to fix in passing: the
  `STEP2_LOGGED_S_TOLERANCE` comment blames "a different rank count" — both
  gates ran at `-n 2`; the real slack consumer is run-to-run drift.

**Plan work this review.** No invented chunks; two entries scoped from
directional notes into full §7 plans:
* **`GEO-9` step 2b written**, including the fixture decision the 03:00 review
  deferred — and the decision is *no pre-chosen reduced rung*. The known-issues
  "~10 minutes" birdcage figure is unmeasured post-2a and is most plausibly the
  hang burning the harness ceiling, not meshing cost (pytest reported in ~3 s
  while the harness exited 124 at 180 s; `coil_phantom_domain` meshes a
  comparable box at the same resolution in ~5 s). The item therefore cost-probes
  the **default** parameters first and coarsens only on measurement. The plan
  also carries the secondary defect the rewrite would otherwise trip over: the
  port boxes currently receive **no 3-D physical group** (`io/mesh.py:2085-2095`),
  which would `gmshio.py:118`-assert the moment the overlap error was fixed.
* **`POST-3` step 4 written** (the `POST-1` `float64`-cast defect, recorded
  2026-07-31 and owned by `POST-3`): phasor-magnitude semantics gated by two
  exact identities — code-path equivalence with
  `evaluate_vector_field_parallel` at `1e-12`, and phase-rotation invariance
  under `e^{jφ}`. The control ceiling is computed in the plan rather than left
  to the run: for phase-uniform samples the broken path's rotation-*variance*
  can be small at every angle (`mean|Re| ≈ (2/π)·mean|E|` regardless of φ), so
  the load-bearing control is its ~36% *deficit*, not its variance — naming the
  wrong one would have bought a run that could not fail.

Pre-computing control ceilings in the review is now 4-for-4 at saving a run
(`POST-3` step 2, `MAT-4` step 1's 4.855, the 03:00 ω-scaling derivation, and
this review's `2/π` rotation-variance ceiling).

**Assessment against §10 (step 5).** The backlog still reaches the mission and
no new chunk is needed. Criteria 2 and 3 now have their solved-field halves
discharged (`PORT-1` steps 2 + 3a); everything still open routes through one
serial pair — **`GEO-9` step 2b** (the last fixture that does not generate a
mesh) then **`PORT-1` step 3b** (gap-voltage ports on it; criterion 1, and the
fixture criterion 4's B1+ comparison needs). 2b is queued below with a full
plan; 3b stays deliberately directional until 2b lands and a later review firms
it up against the measured mesh. Criterion 4 additionally needs a B1+
computation chunk once the fixtures exist — that gap is real but not actionable
until 2b, and is noted here rather than invented as a premature entry.

**All five items below are independent of each other; none waits on another
landing.**

1. **`OPS-11` — put `tests/mesh` in CI.** ✅ **done 2026-08-03, 12:00 run** —
   `validation` job gained a `Mesh generation suite` step; the unexcluded
   control at the working commit gave 2 failed / 18 passed / 1 skipped with the
   two failures being exactly known-issues 5 and 7, and the wired step is
   17 passed 1 skipped 1 deselected in 27.6 s (28.3 s CI-fidelity), exit 0.
   The birdcage `--ignore` reason was confirmed changed and is now cited as
   "deliberately red until step 2b", not the hang. See the §7 entry.
   Independent.
   Execute the §7 `OPS-11` entry **as rescoped at the 03:00 review** — its
   original exclusion set was wrong. **Anchor:** the `GEO-9` step-1
   volume-partition identities (`V_mesh/V_box` and `Σ(tagged)/V_mesh`, both
   `1e-9`) become CI-executed for the first time; a wiring chunk's §4.3 assertion
   comes from the tests it wires in. **Measured exclusion set:**
   `--ignore=tests/mesh/test_birdcage_port_tags.py` plus `--deselect` of
   `test_domain_sizing_heuristics.py::test_coil_phantom_domain_sizing_accounts_for_off_center_phantom_extent`
   — and **nothing else**. The known-issues-7 coil+phantom tests *pass* once the
   birdcage leaves the process (`20260803T034252Z_GEO-9-step1-cohabit.log`,
   16 passed 1 failed 1 skipped in **22.95 s**), so they need no exclusion; the
   one real failure is **known-issues 5**, which `3ac025c` and
   `attempts.md:1903,1907` miscite as 6. **Negative control:** the done-when
   requires a re-run at the working commit showing *those and only those*
   failing — **execute it, do not quote the cohabit log** (the 07:30 run's
   sweep, `20260803T123714Z_GEO-9-step2a-sweep.log`, re-verified the set
   post-2a: 17 passed 1 skipped 1 failed in 28.46 s). **Cost:** smoke,
   `-n 2`, ~25 s plus the CI edit. **Traps:** the birdcage `--ignore` reason
   has *changed* since this item was written — `GEO-9` step 2a fixed the
   exit-124 hang (it now fails promptly, exit 1 in ~13 s) and the ~10-min
   budget figure is reinterpreted as that hang (known-issues, "Non-test
   issues") — the current reason is simply that the test is deliberately red
   until `GEO-9` step 2b, and a red test in CI hides regressions behind an
   expected failure; cite that, not the hang. `--deselect` needs
   the full node id and splits on whitespace inside an already-quoted container
   command. **Does not close:** known-issues 5 or 7, and the exclusions must be
   removed by the commits that fix them, not carried. **Negative result:** if
   anything outside that set fails, **it is a new finding** — record it in
   known-issues and stop rather than widening the exclusion to make the job
   green.

2. **`PORT-1` step 2d — charge the electric-energy excess to the load vector.**
   Independent. Execute the §7 step-2d plan, **which the 03:00 review rewrote: the
   ω-sweep step 2b named as "the discriminating measurement" does not
   discriminate** (both candidates give `4ωW_e/I² ∝ ω⁻¹`; the derivation is in
   the §7 entry). **Anchor:** the N1curl/CG1 discrete sequence is exact, so
   `∇q` is in the trial space and the curl term annihilates it identically —
   giving **`∫E_h·∇q dV = (j/(ωε₀))·∫J·∇q dV` for every `q ∈ CG1 ∩ H¹₀`**, two
   assemblies of an already-solved field, no extra solve. House bound `1e-9`
   (step 2b's comparable residual was 1.8e-10), **but cost-probe it and record
   what it actually is** — if it returns 1e-3 that is the more interesting
   result. Then, reported not gated: one CG1 Poisson solve gives `P_G J` and
   hence `4ωW_e^spur/I² = ‖P_G J‖²/(ωε₀I²)`, printed beside the measured
   **4.852271e+01 Ω**. That ratio is the answer the step exists for.
   **Negative control:** a discretely solenoidal current gives `P_G J = 0`
   exactly — total separation, so state it as such. The informative outcome is
   *partial* agreement. **Cost:** standard tier, `-n 2`, **~60 s** — mesh 22.9 s
   + curl-curl solve 19.5 s (both measured by step 2b) + a much cheaper scalar
   solve. **Traps:** `ψ` and `q` must carry the Dirichlet condition matching the
   PEC wall (`ψ, q ∈ H¹₀`) or the identity tests a different operator;
   `assemble_scalar` is rank-local — allreduce before asserting; `ufl.inner`
   conjugates its second argument; import `_azimuthal_current_density` from
   `test_port_self_impedance_energy.py` rather than re-deriving the current
   (`ufl.max_value` does not compile in the complex build). **Does not close:**
   `PORT-1`, and not even the diagonal — a confirmed cause licenses a fix step,
   it is not the fix. **Negative result:** report the ratio, annotate §7 and
   known-issues, stop; do not tune `ψ`'s boundary condition until the numbers
   meet.

3. **`GEO-9` step 2b — fragment the birdcage geometry.** Independent of items
   1 and 2. Execute the §7 step-2b plan, written this review. **Anchor:** the
   volume-partition identity of steps 1/2a — `V_mesh/V_box = 1` and
   `Σ(tagged)/V_mesh = 1`, both to `1e-9`, `V_box` analytic from the
   generator's own extents (`io/mesh.py:2058-2059`) — plus
   `test_birdcage_port_tags.py` green, switched to `global_cell_tag_set()` in
   the same commit (the rank-safe form known-issues records as
   written-and-reverted *pending exactly this rework*; the assertion content is
   unchanged). Per-region masses are printed in the probe and banded only from
   measurement — the conductor total sits *below* the analytic sum by the
   leg∩ring junction volumes, so `= 1` there would be wrong physics.
   **Negative control:** the before-state, re-run at the working commit —
   post-2a the generator raises `Invalid boundary mesh (overlapping facets)`
   promptly on every rank, exit 1 in seconds. Mesh-exists vs raises is total
   separation; state it as such. **Cost:** mesh-only, no solve, `-n 2`
   (mandatory — the `bcast` failure path and rank-safe tag reads are invisible
   at `-n 1`), standard tier; **cost-probe the default parameters first,
   `timeout 180`** — the known-issues "~10 min" figure is probably the pre-2a
   hang burning the harness ceiling, not meshing cost (pytest reported in ~3 s;
   `coil_phantom_domain` meshes a comparable box at the same resolution in
   ~5 s). Coarsen `resolution` 0.015 → 0.02/0.025 only if the probe says so,
   and record the measured pair. **Traps:** re-derive every physical group from
   the fragment **out-map** — fragment renumbers, never trust absolute tags;
   the port boxes currently receive **no 3-D physical group**
   (`io/mesh.py:2085-2095`) and must, or the fixed geometry trips
   `gmshio.py:118` anyway; `occ.getMass` before `synchronize`;
   `cell_tags.values` is rank-local (`global_cell_tag_set()`); the piece policy
   is in §7 (conductor∩anything → conductor, port-only pieces → `100+i`); the
   step-2a isolation gate asserts the birdcage *raises* — give it a
   deliberately-invalid parameter set in the same commit, do not delete it;
   pytest captures prints without `-s`. **Closes:** `GEO-9` (and retires
   known-issues 7) only if both `1e-9` identities gate green *and* the
   port-tags test passes rank-safely at `-n 2`; anything less holds 🟡.
   **Negative result:** report the failing surface pair and the fragment volume
   count/masses, annotate §7 and known-issues 7, park on `attempt/*`, stop —
   no blind iteration on gmsh tolerances inside the slot.

4. **`MAT-4` step 2 — mass-averaged SAR.** Independent. Execute the §7
   `MAT-4` step-2 plan, **scoped at the 03:00 review from one line, including the sizing
   trap that decides the design**: at ρ = 1000 the step-1 sphere holds 4.19 g, so
   a 1 g averaging volume is 0.62 R — larger than the uniform core — and 10 g
   exceeds the phantom entirely. Growing R is not the escape (`|k_in|R = 0.179`
   already). **Anchor:** gate the averaging *operator* at `m_avg = 0.05 g`
   (radius 2.29 mm = 0.23 R, inside the uniform core): (i) the uniform-field
   identity `SAR_avg/SAR_point = 1` in the deep interior, to a tolerance built
   from step 1's **measured** 0.07%/0.11% interior spread plus the
   averaging-volume discretisation — state the budget, do not pick a round
   number; (ii) kernel mass conservation, `∫ρ dV` over the meshed averaging
   region equal to `m_avg` to step 1's meshed-volume accuracy (0.9964 of
   analytic). **Negative control, ceiling computed:** average at the sphere's
   *surface*, where roughly half the volume is lossless exterior, giving
   `≈ 0.5` against 1.0 — a **~2× separation, which is the arithmetic maximum**.
   Assert > 1.5 and say why 2 is the ceiling. **Cost:** standard tier, `-n 2`,
   **~45 s** — reuse the step-1 fixture and solves unchanged (39.4 s measured);
   the averaging is post-processing. **Traps:** ρ becomes a DG0 field through
   `build_material_fields`, not a float multiplied in afterwards; an averaging
   volume straddles rank boundaries, so allreduce numerator *and* denominator
   separately before dividing (`post/sar.py:123` is the pattern); do not route
   through `post/phantom_fields.py` (the `POST-1` `float64` cast discards
   `Im E`, ~5× wrong here); keep the ½ peak-phasor convention. **Does not
   close:** `MAT-4` as an IEEE C95.3-conformant 1 g/10 g claim — that needs a
   phantom large enough to hold the averaging volume with margin, which is the
   coil+phantom fixture after `GEO-9` step 2. Hold `MAT-4` at 🟡. **Negative
   result:** report the ratio, annotate the §7 entry, stop.

5. **`POST-3` step 4 — phasor-magnitude semantics for the phantom-field
   extraction** (spare). Independent. Execute the §7 step-4 plan, written this
   review. **Anchor:** two exact identities on the piecewise-σ fixture from
   `test_poynting_balance.py` — (i) per-point magnitudes equal to `|·|` of
   `evaluate_vector_field_parallel`'s complex samples at the same points to
   `1e-12`; (ii) phase-rotation invariance of every reported statistic under
   `× e^{jπ/2}` and `× e^{jπ/5}`, to `1e-12`. The current `float64` casts
   (`phantom_fields.py:88` **and** the fallback at `:102`) can satisfy
   neither. **Negative control, ceiling computed in the §7 plan:** the
   `Re`-cast path's *deficit* against the honest magnitude — expected near
   `1 − 2/π ≈ 36%` for phase-uniform samples; print the measured phase span —
   not its rotation-variance, which stays small at every angle for exactly the
   fields this fixture produces. Band the control assertion from the
   measurement (`GEO-9` step-1 precedent). **Cost:** standard tier, `-n 2`,
   ~60–90 s — one piecewise-σ solve, no new mesh; complex build +
   `FEM_EM_REQUIRE_COMPLEX=1`. **Traps:** fix both cast sites or the guardrail
   fallback silently reverts the semantics; allreduce any global statistic —
   `POST-1` is `⚠️`, treat its existing aggregation as unverified; keep the ½
   peak-phasor convention (§11); `-s` for the numbers log. **Does not close:**
   `POST-3` (piecewise μᵣ still waits on a magnetic phantom) or `POST-1` (`⚠️`
   — the interface-guardrail machinery stays unrevalidated). **Negative
   result:** if the two paths disagree beyond `1e-12` at the same points,
   report both sample sets, annotate §7 and the `POST-1` row, stop — do not
   adjust either until it is understood.

If the queue drains: **stop and journal.** Do **not** improvise `PORT-1` step 3b
(gap-voltage birdcage ports) — its §7 plan is deliberately directional and it
stays blocked until `GEO-9` step 2b (queue item 3) lands and a later review
firms it up against the measured mesh.

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
- [ ] Loaded birdcage + phantom simulation runs end to end *(blocked: the
  birdcage mesh does not generate — `GEO-9` step 2, then `PORT-1` step 3b. The
  coil+phantom half is gated as of 2026-08-03, `GEO-9` step 1.)*
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
