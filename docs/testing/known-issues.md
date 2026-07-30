# Known Issues — failing tests and open defects

**Purpose: tell you whether a failure is yours.**

Every entry below was verified failing *before* the work recorded against it, by
checking out the stated commit and re-running. If you hit one of these, you did not
break it. If you hit something not listed here, you probably did.

That distinction is the whole point of this file. Establishing it after the fact
costs a `git stash` / re-run cycle per failure; it was done five times over on
2026-07-27 and is not worth repeating.

Last audited: 2026-07-27 against `ce92e8c`.

## How to check a failure against this baseline

```bash
# Is this failure mine, or was it already there?
git stash                              # or: git checkout <base> -- <paths>
mpiexec -n 8 python3 -m pytest <the failing test> -q
git stash pop
```

If it fails at the base commit too, add it here rather than fixing it in passing —
unless fixing it is the task.

---

## Failing tests

### 1. Stale test double — `DummyMagnetostaticSolver`

| | |
|---|---|
| **Tests** | `tests/materials/test_phantom_material_model.py::test_phantom_material_assignment_and_time_harmonic_pipeline_wiring`<br>`tests/post/test_phantom_field_metrics.py::test_phantom_field_metrics_and_exports_are_finite` |
| **Symptom** | `AttributeError: 'DummyMagnetostaticSolver' object has no attribute 'last_solve_diagnostics'` at `core/time_harmonic.py:309` |
| **Cause** | `TimeHarmonicSolver.solve()` reads `mag_solver.last_solve_diagnostics` when building `TimeHarmonicFields`. The chunk that added solver health diagnostics (`TH-4`, legacy C6) did not update the test doubles that stand in for `MagnetostaticSolver`. |
| **Fix** | Add a `last_solve_diagnostics = None` attribute to both doubles. Small and self-contained — this is *not* blocked on `TH-1`. |
| **Status** | `--deselect`ed in the CI `validation` job, visibly, so the debt is not silently skipped |
| **Verified pre-existing at** | `b2715ab` and earlier |

### 2. Residual-trend classifier disagrees with its test

| | |
|---|---|
| **Tests** | `tests/solver/test_convergence_diagnostics.py::test_classify_residual_trend_summaries_are_deterministic`<br>`tests/solver/test_convergence_diagnostics.py::test_time_harmonic_solver_emits_optional_solve_health_diagnostics` |
| **Symptom** | `assert 'mixed' == 'mostly-decreasing'` (line 22); `assert False` (line 63) |
| **Cause** | Not diagnosed. `classify_residual_trend()` in `core/solvers.py` returns `mixed` for a sequence the test expects to be classified `mostly-decreasing`. Either the classifier's thresholds or the test's expectation is wrong — **do not assume it is the test**: the analytic expectation in `test_analytical_circular_loop` turned out to be the wrong side of exactly this kind of disagreement (it wanted `μ₀I/(2√2a)` where the correct value is `μ₀I/(4√2a)`). |
| **Verified pre-existing at** | `ce92e8c` and earlier |

### 3. Port tests assert a non-zero S-matrix diagonal on a matched port

| | |
|---|---|
| **Tests** | `tests/ports/test_sparameter_assembly.py::test_n_port_sweep_assembles_finite_matrix_with_expected_shape`<br>`tests/ports/test_port_orientation_sensitivity.py::test_port_orientation_flip_changes_off_diagonal_sparameter_sign` |
| **Symptom** | `assert np.all(np.abs(diagonal) > 0.0)` fails on `array([0.+0.j, 0.+0.j, 0.+0.j])` |
| **Cause** | Both fakes set `current = voltage / port.z0_ohm` at the driven port, i.e. a perfectly matched port. The reflected power wave is then `b = (V − Z₀I)/(2√Z₀) = 0` exactly, so the diagonal is *legitimately* zero and the assertion cannot hold. |
| **Fix** | **Deliberately not fixed.** These exercise the placeholder coupling model's arithmetic (see `PORT-0`). Repairing them means tuning assertions to match a heuristic that `PORT-1` deletes. Resolve them there. |
| **Verified pre-existing at** | `53f6428` and earlier |

### 4. Coil+phantom B-field symmetry exceeds tolerance

| | |
|---|---|
| **Test** | `tests/validation/test_coil_phantom_bfield_metrics.py::test_coil_phantom_bfield_metrics_are_finite_smooth_and_symmetric` |
| **Symptom** | `max_rel_diff=0.557` against a `0.350` tolerance; `max_abs_diff=7.090e-07` against `6.523e-08` |
| **Cause** | Not diagnosed. Tracked as `MAG-6` (legacy A1). Its predecessor failed at `0.322` against `0.30`; interface-aware sampling was added in response and the revised test has still never passed. |
| **Note** | The coil+phantom fixture uses a single global `setSize` and tight air padding — the same pattern that cost **20% error** on Helmholtz until `air_padding` was decoupled (see `docs/validation/helmholtz.md`). A boundary-mirror artifact is a plausible contributor and should be ruled out before the tolerance is touched. |
| **Verified pre-existing at** | `ce92e8c` and earlier (0.559 at `HEAD`, 0.557 after the gauge change — the gauge default is not the cause) |

### 5. Domain sizing heuristic, off-centre phantom

| | |
|---|---|
| **Test** | `tests/mesh/test_domain_sizing_heuristics.py::test_coil_phantom_domain_sizing_accounts_for_off_center_phantom_extent` |
| **Cause** | Not diagnosed. Pure geometry arithmetic in `MeshGenerator.coil_phantom_domain_sizing_diagnostics` — no solve involved, so no solver change can affect it. |
| **Verified pre-existing at** | `794d2f1` (pre-session) |

### 6. Rank-dependent: single-port excitation

| | |
|---|---|
| **Test** | `tests/solver/test_single_port_excitation.py::test_single_port_excitation_returns_finite_estimates` |
| **Symptom** | Passes at 1 rank, fails at `mpiexec -n 8` |
| **Cause** | Not diagnosed. Two rank-local bugs of this family were already fixed on 2026-07-27 (`tests/solver/test_two_torus.py` asserted on rank-local `cell_tags.values`; `test_helmholtz_v2.py` did a per-rank collision search). Suspect the same pattern — a quantity that is rank-local being treated as global. |
| **Tool** | `tests/mesh/helpers.py::global_cell_tag_set()` exists for the tag case. `post.evaluation.evaluate_vector_field_parallel()` for the point-location case. |
| **Verified pre-existing at** | `ce92e8c` and earlier |

---

## Non-test issues

### Birdcage suite is over the compute budget

`tests/mesh/test_birdcage_port_tags.py` takes **~10 minutes** on its own — the rest of
`tests/mesh` runs in 9.7 s. A full `tests/mesh` run exceeded a 700 s bound; excluding
birdcage it is trivial. Exclude it from routine runs:

```bash
pytest tests/mesh --ignore=tests/mesh/test_birdcage_port_tags.py
```

It also carries a **latent rank-local tag bug**: it asserts on
`set(np.unique(cell_tags.values))`, which is per-rank, so a rank owning no port or leg
cells will trip it at higher rank counts — the same defect already fixed in
`test_two_torus.py`. A fix using `global_cell_tag_set()` was written and then reverted
on request, as the birdcage geometry is slated for rework alongside a proper analytic
reference. Left untouched intentionally.

### The gauge penalty is a workaround, not a gauge — closed by decision (2026-07-28)

`DEFAULT_GAUGE_PENALTY = 1.0` prices the curl-curl operator's gradient null space
rather than removing it (`PROJECT_PLAN.md` §7 `MAG-10`). This was previously the
highest-risk open item; the decision is recorded here so it is not reopened:

- `MAG-15` landed `GaugeMethod.LAGRANGE` — an (A, p) saddle point that removes the
  null space with no parameter — as a cross-check and diagnostic
  (`tests/solver/test_gauge_lagrange.py`). The penalty at 1.0 stays the production
  default on cost grounds (~2× at degree 1, ~7.5× at degree 2).
- Tree-cotree gauging is rejected: `TH-1`'s E-field formulation has no static null
  space at ω > 0 (the operator acts as −k₀²ε_c on the gradient subspace), so deeper
  magnetostatic gauge machinery has no Phase-2 payoff.
- The risk does **not** transfer to `TH-1` as gauge cancellation. The Phase-2
  silent-failure analog is *near-resonance ill-conditioning*, tracked in the
  `TH-1` formulation notes in `PROJECT_PLAN.md` §7.

### Loop fixture still has a modeling floor (MAG-13, wire half fixed)

The natural BC `n×H = 0` on a truncation wall contradicts Ampère's law for any net
enclosed current (`∮H·dl = I` vs `H_φ(R) = 0` forced at the wall), so it puts a
floor under these fixtures that no refinement removes.

**Straight wire: fixed 2026-07-30** (`MAG-13` steps 1–3). `test_straight_wire.py`
now imposes the analytic `A_z` on the exterior via
`core.solvers.exterior_dirichlet_bc`; measured 35.13% → 22.19% at h=0.004 on the
same mesh, and 22.19% → 12.75% → 9.26% across h = 0.004/0.0025/0.0018, i.e. still
converging at ~O(h^1.2) with no plateau. `J·n ≠ 0` at the end caps remains (the
`MAG-15` multiplier spread measures it) but is not what was dominating.

**`test_circular_loop.py` is untreated** and hides the same class of bias — a
~(a/R)³ PMC-image term — inside its 10% tolerance. **Symptom to expect:** a
convergence assertion on the loop fails at some future, finer resolution pair
*while the solver is correct* — the error plateaus at the floor and the fitted rate
collapses. **Do not loosen the assertion; fix the boundary** — `MAG-13` steps 4–5,
for which the off-axis `AnalyticalSolutions.circular_loop_vector_potential` and the
BC helper are already in place.

### Air-box sizing is not generalised

Only `two_torus_domain` has `air_padding` and graded sizing. Every other fixture in
`io/mesh.py` — including the coil+phantom geometry all MRI work depends on — still
uses a single global `setSize` with padding tied to feature size. On Helmholtz that
pattern produced a **20.4% error that did not improve across a 7× refinement**, and it
was invisible until an analytic comparison existed. Coil+phantom has no analytic
reference yet. See `PROJECT_PLAN.md` §9.

---

## Recording a new entry

Add an entry when you find a failure you are **not** fixing. Include: the test id, the
literal symptom, the commit you verified it against, the cause (or an explicit "not
diagnosed" — an honest gap is more useful than a guess), and which chunk resolves it.

Remove the entry in the same commit that fixes the test.
