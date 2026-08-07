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

### 1. ✅ RETIRED 2026-07-31 — stale test double, `DummyMagnetostaticSolver`

The two phantom tests
(`tests/materials/test_phantom_material_model.py::test_phantom_material_assignment_and_time_harmonic_pipeline_wiring`,
`tests/post/test_phantom_field_metrics.py::test_phantom_field_metrics_and_exports_are_finite`)
failed with `AttributeError: 'DummyMagnetostaticSolver' object has no attribute
'last_solve_diagnostics'`. No fix ever landed: `TH-1` steps 1–3 deleted the
`last_solve_diagnostics` read from the time-harmonic path, so the failing code
path went away under the entry.

Re-verified through the harness at `424faed`:
`20260731T170152Z_KI-1-retire-gate.log` — complex build, `FEM_EM_REQUIRE_COMPLEX=1`,
`-n 2`, **10 passed in 4.6 s**; and `20260731T170140Z_KI-1-real-mode-iomatpost.log`
— real build, the CI `validation` job's exact command with the `--deselect`s
removed, **15 passed, 2 skipped in 0.5 s**. Both `--deselect`s are gone from the
`validation` job and both files are now listed in `validation-complex`, which is
where the two `@complex_only` tests actually execute. The test-side
`ComplexWarning` casts were fixed in the same commit; the remaining one at
`post/phantom_fields.py:88` was recorded under `POST-1` in `PROJECT_PLAN.md` §7
and is **fixed as of 2026-08-04** (`POST-3` step 4 — both cast sites removed,
statistics taken on the phasor magnitude, gated by
`tests/post/test_phantom_phasor_semantics.py`). `POST-1` stays ⚠️ for the
interface-guardrail machinery, which is unrelated to the cast.

The heading is kept (rather than deleted with the entries renumbered) so the
numbering of entries 2–6 stays stable — several commits and CI comments refer to
them by number.

### 2. Residual-trend classifier disagrees with its test

| | |
|---|---|
| **Tests** | `tests/solver/test_convergence_diagnostics.py::test_classify_residual_trend_summaries_are_deterministic`<br>`tests/solver/test_convergence_diagnostics.py::test_time_harmonic_solver_emits_optional_solve_health_diagnostics` |
| **Symptom** | `assert 'mixed' == 'mostly-decreasing'` (line 22); `assert False` (line 63) |
| **Cause** | Not diagnosed. `classify_residual_trend()` in `core/solvers.py` returns `mixed` for a sequence the test expects to be classified `mostly-decreasing`. Either the classifier's thresholds or the test's expectation is wrong — **do not assume it is the test**: the analytic expectation in `test_analytical_circular_loop` turned out to be the wrong side of exactly this kind of disagreement (it wanted `μ₀I/(2√2a)` where the correct value is `μ₀I/(4√2a)`). |
| **Verified pre-existing at** | `ce92e8c` and earlier |
| **Status** | Whole file left out of the `validation-complex` CI job (`OPS-10`): one of the two failures is `@complex_only` and the other is not, so there is nothing to select. Add the file when this entry is fixed. |

### 3. Port tests assert a non-zero S-matrix diagonal on a matched port

| | |
|---|---|
| **Tests** | `tests/ports/test_sparameter_assembly.py::test_n_port_sweep_assembles_finite_matrix_with_expected_shape`<br>`tests/ports/test_port_orientation_sensitivity.py::test_port_orientation_flip_changes_off_diagonal_sparameter_sign` |
| **Symptom** | `assert np.all(np.abs(diagonal) > 0.0)` fails on `array([0.+0.j, 0.+0.j, 0.+0.j])` |
| **Cause** | Both fakes set `current = voltage / port.z0_ohm` at the driven port, i.e. a perfectly matched port. The reflected power wave is then `b = (V − Z₀I)/(2√Z₀) = 0` exactly, so the diagonal is *legitimately* zero and the assertion cannot hold. |
| **Fix** | **Deliberately not fixed.** These exercise the placeholder coupling model's arithmetic (see `PORT-0`). Repairing them means tuning assertions to match a heuristic that `PORT-1` deletes. Resolve them there. |
| **Verified pre-existing at** | `53f6428` and earlier |
| **Progress 2026-08-04** | `PORT-1` step 3b-ii, the step that would replace these fakes with a driven gap port, was **attempted and parked** (`attempt/PORT-1-step3bii-20260804T141200Z`). The drive works — reciprocity `2.2840e-04`, undriven port open at `2.32e-03` — but `Im Z₁₂` is +72.12% off `ωM₁₂`, traced to the gap box's 1.83×-oversized cross-section rather than to the solve. These two tests stay red and unchanged; see PROJECT_PLAN §7 `PORT-1` step 3b-ii for the measurement and the ranked successor. |
| **Progress 2026-08-04 (2)** | Step 3b-iii tested that diagnosis and **refuted it** (parked on `attempt/PORT-1-step3biii-20260804T173000Z`; logs `20260804T170301Z_PORT-1-step3biii-costprobe.log`, `20260804T170439Z_PORT-1-step3biii-sweep-o5e4.log`). Shrinking only the transverse overhang gives `Im Z₁₂/ωM₁₂` = `+1.7210` (fringe 0.4546), `−0.2391` (0.3509), `+0.3317` (0.2739) — non-monotone and **sign-changing**, so a box-volume average is not a port voltage at any overhang. The shadow-restricted average is stable at `0.687–0.814 ×` across the same three geometries. The replacement route is now the facet-integral voltage (§7 step 3b-v on 3b-iv's tags); these two tests stay red and unchanged. |
| **Progress 2026-08-06** | Step 3b-v ran that facet-integral route and it is **also excluded** (parked on `attempt/PORT-1-step3bv-20260806T004500Z`; log `20260806T003559Z_PORT-1-step3bv-gate.log`, 3 failed / 7 passed, 67.6 s at `-n 2` — no hang, 3b-iv's hoisted `create_entity_permutations()` held). `V = −⟨E·ŷ⟩_{terminal discs, gap side}·L` gives `\|Im Z₁₂\|/ωM₁₂` = **4.845** (+384.54%) against the full-box `0.332` and tube-shadow `0.763 / 0.814` **on the same solve**, with reciprocity degrading `1.15e-4 → 1.79e-2`. Cause: `E·ŷ` on a terminal is the surface-charge-dominated *normal* component (measured gap/wire jump ratio 2.9e-5–4.6e-5), so a two-endpoint trapezoid samples exactly where the integrand peaks. Both the box family and the terminal-facet route are now excluded by measurement; a successor must integrate the *tangential* component along the whole gap path. `MUTUAL_TOLERANCE` unmoved. These two tests stay red and unchanged. |
| **Progress 2026-08-06 (2)** | Step 3b-vi ran the tangential path integral — `V = −∫E·t̂ dl` along the torus centreline arc through the gap, Gauss–Legendre nodes strictly interior to the arc, sampled via `post.evaluation.evaluate_vector_field_parallel` — and it is **unresolved, not refuted** (parked on `attempt/PORT-1-step3bvi-20260806T094500Z`, `ee5f0cb`; logs `20260806T093603Z_PORT-1-step3bvi-gate-n2.log` and `20260806T093808Z_PORT-1-step3bvi-quadrature-sweep-n2.log`, 4 failed / 4 passed, 136.13 s at `-n 2`). Value, off one solve: path **0.468933 / 0.499728** × ωM₁₂ against facet `4.802 / 4.889`, full-box `0.332`, tube-shadow `0.763 / 0.814` — a *third* distinct answer, below the shadow family, at −51.6% with reciprocity `6.3e-2`. But the plan's own quadrature precondition fails first: the proposed `(33, 65)` node pair disagrees by `1.07e-1`, and the sequence extended to 4097 nodes converges only at `O(1/n)` to a `~1e-3` plateau — because N1curl makes only the *facet*-tangential component continuous, the arc's tangent is not facet-tangential, and with `h_wire = 2.5e-3` against arc length `a·g = 1.2e-2` only ~5 cells span the path. Four estimator families now give four answers spanning a factor 15 on one solved field. The successor is **arc refinement, not more quadrature nodes**; if `~0.48` survives it, the family question is closed negatively and the suspects become finite-σ terminal penetration or the `ωM₁₂` reference. `MUTUAL_TOLERANCE` unmoved. These two tests stay red and unchanged. |
| **Progress 2026-08-06 (3)** | Step 3b-vii ran that arc refinement and **the family question closes negatively** (parked on `attempt/PORT-1-step3bvii-20260806T170000Z`, `bc8c04e`; probe `20260806T170559Z_PORT-1-step3bvii-probe.log`, gate `20260806T170835Z_PORT-1-step3bvii-gate-n2.log`, 2 failed / 10 passed, 165 s at `-n 2`). A coordinate-defined `MathEval`+`Threshold` size field on the fragmented model put `h_gap = 3e-4` — 40 cells across `a·g` — in a tube around each gap arc: 124 753 → 178 055 cells (1.427×), gap-tagged cells 1569 → 24 430 per port. It fixed the discretization and not the answer. Reciprocity **6.3e-2 → 3.8823e-3** (inside the 1e-2 band for the first time) and the fixed-order quadrature residual improved ~3×, but (129, 257) still disagree by `1.1444e-2` and the converged path value is **0.493653 / 0.491744** × ωM₁₂ (0.4808 at 4097 nodes) against 3b-vi's 0.468933 / 0.499728 — a discretization-level shift, `Im Z₁₂` at −50.73%. The built-in control holds: facet `5.165/5.169`, box `0.3496/0.3492`, shadow `0.8566/0.8386` all moved only a few % off the refined solve, so the solve did not change underneath the estimator. Four sampling geometries, four answers, and the ~0.48 survives refinement: **the deficit is not the sampling geometry**. Remaining suspects are finite-σ terminal penetration at `δ = 1.125 r_wire` and the filamentary `ωM₁₂` reference itself — a review's adjudication. `MUTUAL_TOLERANCE` unmoved. These two tests stay red and unchanged. |
| **Progress 2026-08-07** | Step 3b-viii audited the **`ωM₁₂` reference** — the first of the two remaining suspects — in closed form, no solve and no mesh (`tests/validation/test_mutual_inductance_reference.py`, on `main` and green; log `20260807T020314Z_PORT-1-step3bviii-gate.log`, 7 passed in 0.43 s at `-n 1`, smoke). **The suspect is retired.** (i) The vector-potential route the gates use and an independent elliptic-integral reimplementation (`M = μ₀√(ab)[(2/k − k)K − (2/k)E]`, `m = k²`) agree to **1.5e-15** at the fixture's `d`, and to ≤ 7.5e-14 across `d/4 … 4d`; `ω·M` reproduces the logged `1.241755 Ω` to 3.1e-7. A vacuity control confirms the identity has teeth — feeding SciPy the modulus where the parameter belongs moves `M` by **140%**, eleven orders above the 1e-9 gate. (ii) The finite-cross-section correction at `r/a = 0.125`, the filament kernel averaged over both minor discs at uniform current density (Gauss–Legendre × periodic trapezoid, converged to 6.7e-16 between orders), is **`M_tube/M_fil = 1.004809992`, i.e. +0.481%** — and it has the *wrong sign* to help, since a larger reference makes the deficit slightly worse (0.4937 → 0.4914 × ωM). A 0.5% correction cannot produce a factor 2, consistent with step 2's field-level agreement at −9.35%. **The reference is exonerated; finite-σ terminal penetration (step 3b-ix) is now the only named suspect.** `MUTUAL_TOLERANCE` unmoved. These two tests stay red and unchanged. |
| **Progress 2026-08-07 (2)** | Step 3b-ix closed the loop and **found the cause of the factor 2 — it is not physics, it is the estimator's integration limits.** Parked on `attempt/PORT-1-step3bix-20260807T050000Z` (`6caec85`); log `20260807T050654Z_PORT-1-step3bix-gate-n2.log` on that branch, 178 055 cells, `-n 2`, 227 s. Faraday on the closed centreline circle, tiled into four segments each verified against the DG0 material indicator before any solve (0 misassigned of 5392 nodes), gives on the undriven port: `V_gap = 0.493653 / 0.491744`, **`V_buried = 0.399972 / 0.402239`**, `V_wire = 0.002394 / 0.002316`, **sum = 0.896019 / 0.896299 × ωM₁₂** — inside the pre-set `1 ± 0.15` band and matching step 2's independent reaction route (−9.35%, of which −9.36% is the PEC box at padding 0.08). **Finite-σ terminal penetration is retired**: at `σ × {1, 2, 4}` (δ/r_wire 1.125 → 0.796 → 0.563) `V_wire/ωM` = 0.002394 → 0.001856 → 0.000727 — the signature is real and 200× too small to matter — while `V_gap/ωM` = 0.493653 → 0.490837 → 0.485059, i.e. it *falls*. The missing half is the **buried** dielectric: `GAP_BURIAL` puts the gap region out to `±arcsin(half_y/a) = ±0.175335` rad while `_gap_arc_quadrature` integrates only the nominal `±GAP_ANGLE/2 = ±0.15`, so 1.013 mm of arc per side — 0.8% of the loop's length, and exactly where the terminal fields live — carries 45% of its EMF. **Terminal to terminal the gap-port voltage is 0.8936 × ωM₁₂, not 0.4937.** Both suspects the 2026-08-06 review named are now dead. Successor **step 3b-x** (correct the limits off the port facet tags, then a box-padding sweep — the residual −10.6% is the PEC box's, and a `MUTUAL_TOLERANCE` edit is *not* the remedy) is written into PROJECT_PLAN §7 for a review to scope. `MUTUAL_TOLERANCE` unmoved at 0.10; nothing under `src/` changed. These two tests stay red and unchanged. |
| **Scoped 2026-08-07 (03:00 review)** | Both successors are now full §7 plans and queued (§9 items 1–2). **3b-x**: correct `_gap_arc_quadrature` to terminal-to-terminal limits read off the port facet tags, gate the corrected estimator against the *same-fixture* reaction-route `Im Z₁₂` (≤ 3%; the ωM₁₂ comparison stays printed and tracked here, expected ~−10.6%), delete the σ-monotonicity test whose premise 3b-ix refuted, and land the branch. **3b-xi**: padding sweep {0.08, 0.10, 0.12} on the ungapped fixture — if the deficit does not shrink monotonically with padding, the PEC-box attribution dies and this entry escalates to the weekly review. `MUTUAL_TOLERANCE` untouched by either. |

### 4. Coil+phantom B-field symmetry exceeds tolerance

| | |
|---|---|
| **Test** | `tests/validation/test_coil_phantom_bfield_metrics.py::test_coil_phantom_bfield_metrics_are_finite_smooth_and_symmetric` |
| **Symptom** | `max_rel_diff=0.557` against a `0.350` tolerance; `max_abs_diff=7.090e-07` against `6.523e-08` |
| **Cause** | Not diagnosed. Tracked as `MAG-6` (legacy A1). Its predecessor failed at `0.322` against `0.30`; interface-aware sampling was added in response and the revised test has still never passed. |
| **Note** | The coil+phantom fixture uses a single global `setSize` and tight air padding — the same pattern that cost **20% error** on Helmholtz until `air_padding` was decoupled (see `docs/validation/helmholtz.md`). A boundary-mirror artifact is a plausible contributor and should be ruled out before the tolerance is touched. |
| **Verified pre-existing at** | `ce92e8c` and earlier (0.559 at `HEAD`, 0.557 after the gauge change — the gauge default is not the cause) |

### 5. ✅ RETIRED 2026-08-06 — domain sizing heuristic, off-centre phantom

| | |
|---|---|
| **Test** | `tests/mesh/test_domain_sizing_heuristics.py::test_coil_phantom_domain_sizing_accounts_for_off_center_phantom_extent` |
| **Symptom** | `assert 0.09 > 0.09` |
| **Was pre-existing at** | `794d2f1` (pre-session); reproduced one last time 2026-08-06 at `d4e278d` (`20260806T033155Z_GEO-4-step1-precontrol.log`, 1 failed 3 passed in 1.31 s) |
| **Diagnosis** (`GEO-4` step 1) | **The test's assertion, not the arithmetic.** The air box is centred on the origin, so its half-width is `max(coil_major + coil_minor, |offset| + phantom_radius) + padding` — the off-centre phantom enters through the second term of the max. `coil_phantom_domain` rejects any placement with `|offset| + phantom_radius >= coil_major - coil_minor` (the `radial_clearance <= 0` guard), so the phantom's outer radius is **always** strictly below the coil's outer radius and the max is always won by the coil. The property "an offset phantom grows the box" is therefore unattainable for every meshable configuration, not merely unexercised by the chosen 0.03 m offset (phantom reaches 0.07 m vs the coil's 0.09 m). Test and code landed together in `2c52f05`; the test never passed. |
| **Resolution** | The strict `>` was **not** relaxed. The test now gates the containment identity with the clearance term explicit — `half_width == max(coil_outer, |offset| + r_phantom) + padding` for both presets, and `clearance(centered) - clearance(shifted) == 0.03` exactly (the whole offset is spent out of the phantom's wall clearance). Two tests added: the phantom-governed branch of the max keeps a strict `>` alive where it exists (arithmetic only, outside the meshable envelope), and a zero-padding negative control still detects an undersized domain. `coil_phantom_domain_sizing_diagnostics` gained `phantom_outer_radial_extent_m`, `phantom_boundary_clearance_m`, `phantom_offset_radius_m`, `phantom_governs_radial_extent`; **no sizing number changed**, so no meshed fixture moved. |
| **Verified at** | `20260806T033316Z_GEO-4-step1-gate.log` (6 passed, 1.36 s, `-n 2`) and `20260806T033327Z_GEO-4-step1-mesh-regression.log` (whole `tests/mesh`, no `--deselect`, **27 passed 1 skipped in 85.3 s**) |
| **Back in CI** | The `OPS-11` `--deselect` was removed in the same commit; the `Mesh generation suite` step now excludes nothing. |
| **Cited wrongly as "known-issues 6"** | Commit `3ac025c` and `docs/testing/attempts.md:1903,1907` call this entry 6. **It was entry 5.** Entry 6 is the rank-dependent single-port excitation test in `tests/solver`, unrelated to `tests/mesh`. |

**Open follow-up for a review (not a failing test):** because the overlap guard
is z-blind, a *short* phantom that would clear the torus tubes in z is rejected
just the same. If off-centre placements that radially govern the box are ever
wanted, that guard — not the sizing heuristic — is what must change.

### 6. Rank-dependent: single-port excitation

| | |
|---|---|
| **Test** | `tests/solver/test_single_port_excitation.py::test_single_port_excitation_returns_finite_estimates` |
| **Symptom** | Passes at 1 rank, fails at `mpiexec -n 8` |
| **Cause** | Not diagnosed. Two rank-local bugs of this family were already fixed on 2026-07-27 (`tests/solver/test_two_torus.py` asserted on rank-local `cell_tags.values`; `test_helmholtz_v2.py` did a per-rank collision search). Suspect the same pattern — a quantity that is rank-local being treated as global. |
| **Tool** | `tests/mesh/helpers.py::global_cell_tag_set()` exists for the tag case. `post.evaluation.evaluate_vector_field_parallel()` for the point-location case. |
| **Verified pre-existing at** | `ce92e8c` and earlier |

### 8. ✅ RETIRED 2026-08-05 — magnetostatic energy raised `TypeError` in the complex build

**Fixed 2026-08-05 (16:30 run) by `MAG-16`.** Both tests pass at `-n 2` under
`dolfinx-complex-mode` with their identity assertions untouched
(`20260805T213601Z_MAG-16-gate-complex-final.log`, 10 passed in 4.9 s with
`tests/environment` first), and the complex-mode `tests/solver` sweep went from
4 standing failures to 2 — the remaining two are **entry 2**, unrelated
(`20260805T213408Z_MAG-16-regress-complex.log`, 2 failed 34 passed in 28.3 s).

`compute_magnetic_energy` now takes `np.real` of the reduced scalar and raises
if `abs(Im W)/abs(Re W)` exceeds `ENERGY_IMAG_RTOL = 1e-8`; `abs()` was
rejected on purpose, since it would swallow a genuine imaginary part *and* a
negative real one. The suspicion recorded below — that the imaginary part is
round-off — was **too pessimistic**: it is **exactly 0.0** in both gauges,
because the magnetostatic load is real and `ufl.inner` conjugates its second
argument, so the assembled integrand is `μ⁻¹|curl A|²/2` and the complex build
merely stores a real number in a complex slot.

The value had indeed never been compared across builds, so it was pinned before
being trusted: the real-build energies were captured *pre-fix*
(`20260805T213144Z_MAG-16-probe-real.log` — `1.121469318858e-08 J` penalty,
`1.121466766900e-08 J` Lagrange) and the complex build reproduces them to
`2.9e-07` and `1.3e-13` respectively. The penalty gauge's run-to-run wander
(`1.9e-08…2.9e-07`) is its κ ~ 1e10 operator, not the reduction.

The file is now listed in the `validation-complex` CI job, which is what stops
this from recurring — nothing had ever run it under the complex build until a
`POST-3` step-5 regression sweep did by hand. Original entry follows.

| | |
|---|---|
| **Tests** | `tests/solver/test_energy_and_point_evaluation.py::test_energy_matches_explicitly_reduced_assembly`<br>`tests/solver/test_energy_and_point_evaluation.py::test_energy_satisfies_discrete_work_energy_identity` |
| **Symptom** | `TypeError: float() argument must be a string or a real number, not 'complex'` at `src/fem_em_solver/core/solvers.py:661` (`MagnetostaticSolver.compute_magnetic_energy`) |
| **Cause** | Not diagnosed beyond the mechanism: in the complex build every `fem.Function` is complex, so the assembled energy scalar is complex-typed (with a round-off imaginary part) and the unconditional `float(...)` refuses it. The magnetostatic energy is real by construction, so the fix is presumably `np.real(...)` before the cast — but that is `MAG` work and the value has never been checked against the real-build number, so it is recorded rather than patched in passing. Both tests pass in the real build. |
| **Verified pre-existing at** | `aabb0a7` — reproduced with the `POST-3` step-5 diff stashed: `2 failed, 2 passed in 4.46 s` (`20260805T003945Z_POST-3-step5-preexisting.log`, `-n 2`, complex build). Found by that step's regression sweep, which is the first time this file was run under `dolfinx-complex-mode`. |

Owned by chunk `MAG-16` (§7, written by the 2026-08-05 10:30 review); this
entry leaves with `MAG-16`'s fixing commit — which is the commit carrying the
retirement header above.

### 9. ✅ RETIRED 2026-08-05 — `-n 2` hang on `two_torus_domain`'s port facets

**Diagnosed and fixed 2026-08-05 (12:00 run); `tests/mesh/test_two_torus_port_facets.py`
is on `main` and green at `-n 2` in 20 s
(`20260805T171107Z_PORT-1-step3biv-parallel-gate-fixed.log`, 2 passed).**

**Cause: a lazy collective, reached on only one rank.** An interior-facet
(`dS`) assembly requires `Topology::create_entity_permutations()`, and the
dolfinx assembler calls it *lazily* — only once a rank finds integration
entities for the form's subdomain id. Under this fixture's partition each rank
owns the facets of exactly one port (rank 0 → tag 201, rank 1 → tag 202), so
assembling tag 201 put rank 0 inside that collective while rank 1, with no
201 facets, sailed past it into the next one. Hence the two ranks' *different*
SIGTERM stacks (`create_entity_permutations` vs mpi4py `MPI_Comm_dup`) — a
mismatched collective, not a slow one. The fix is one hoisted line in
`_facet_group_area`: call `create_entity_permutations()` unconditionally on
every rank before building the form.

**What the discriminating run was.** The same computation, marker-instrumented,
ran to completion as a *script* at `-n 2` (exit 0, 12 s,
`20260805T170545Z_PORT-1-step3biv-dS-localise.log`) while the pytest gate hung
— and the script's only extra call was the explicit
`create_entity_permutations()`. Markers inside the gate then pinned the hang to
`_facet_group_area` at tag 201
(`20260805T170743Z_PORT-1-step3biv-pytest-localise.log`, exit 124).

**The ghost-mode hypothesis was necessary but not sufficient.** The
`shared_facet` partitioner now plumbed into `two_torus_domain` does what the
entry below predicted — `cells_ghost` 0 → 239/231 per rank
(`20260805T170109Z_PORT-1-step3biv-ghostprobe.log`, 14 s) — but the gate still
hung with it alone (`20260805T170140Z_…-parallel-gate.log`, exit 124, 181 s).
Both changes are kept: an interior-facet integral does need both cells of every
facet, and the fixture's docstring records the requirement.

**Generalisation, untested elsewhere:** any `dS` integral over a subdomain that
some rank does not touch is exposed to this. Only this fixture is fixed.

#### Superseded diagnosis, 2026-08-05 (22:30 run)

**Retitled and half-refuted 2026-08-05 (22:30 run).** The mesh is innocent: with
the gmsh dim-2 physical groups removed entirely and the identical facet set
rebuilt on the dolfinx side from the distributed cell tags, `model_to_mesh`,
`create_entities(fdim)` and `create_connectivity(fdim, tdim)` all return at
`-n 2` on the gate's own mesh in **14 s** (marker probe
`20260805T034007Z_PORT-1-step3biv-hang-localise-fine.log`, exit 0; 39578/39956
cells per rank, 116 interface facets found per port). The `-n 2` gate still
times out, so *something* on this path hangs — but it is downstream of the tags,
in the `dS` facet-area assembly, and the paragraph below misattributes it.

**Leading hypothesis for the next attempt, measured not guessed:**
`gmshio.model_to_mesh` passes no partitioner, so the mesh is built with the
default ghost mode and the probe measures `cells_ghost=0` on **both** ranks. An
interior-facet (`dS`) integral needs both cells behind every facet, which a mesh
with no ghost cells cannot supply on a partition-boundary facet. First move:
hand `model_to_mesh` a `shared_facet` partitioner and re-measure. Second
observation from the same probe, relevant either way: with the current
partition each rank sees exactly **one** port (rank 0 tag 201, rank 1 tag 202),
so any per-port assertion is rank-local until it is reduced.

The original entry follows, kept because its serial measurements stand.

#### Original entry, 2026-08-05 (21:00 run) — the `model_to_mesh` attribution is superseded above

| | |
|---|---|
| **Tests** | `tests/mesh/test_two_torus_port_facets.py` (both tests) — **not on `main`**; the file and the mesh change were parked *because* of this, so nothing on `main` is red. *(The branch this row named, `…021000Z`, was deleted by the 2026-08-05 10:30 review; the current code is on `attempt/PORT-1-step3biv-20260805T034500Z`.)* |
| **Symptom** | With `PORT-1` step 3b-iv's dim-2 physical groups `201`/`202` (the gap↔conductor shared surfaces, which are **interior** facets) added to the gapped fixture, `mpiexec -n 2` hangs inside `gmshio.model_to_mesh` and is killed by `timeout` at the 180 s ceiling. Both ranks' loguru stacks are identical and spinning in `MPI_Testall` ← `MPI::compute_graph_edges_nbx` ← `IndexMap::index_to_dest_ranks` ← `Topology::create_entity_permutations` ← `create_entities`. gmsh finishes (`Done optimizing mesh (Wall 7.14s)`) ~10 s in; the remaining ~168 s is the hang. No test code runs — the hang is before `model_to_mesh` returns. Log: `20260805T020301Z_PORT-1-step3biv-costprobe.log`, exit 124. |
| **Cause** | Not diagnosed. Bounded from two sides by measurement: `-n 1` completes the identical case in 22.5 s with correct areas (`20260805T020843Z_PORT-1-step3biv-serial-gate.log`, 2 passed), and `-n 2` on the same fixture **without** the new facet groups is green today (`tests/mesh/test_two_torus_gapped.py`). So it is neither cost nor the gapped geometry: it is the distribution of facet tags whose facets are interior to the partitioned mesh. The `2xx` groups are the fixture's first interior dim-2 groups — the only pre-existing one is the outer boundary. |
| **Verified pre-existing at** | Not pre-existing — introduced by the parked branch, which is why it is parked. Recorded here so the next attempt starts from the stack trace instead of re-deriving it. |

### 10. ✅ RETIRED 2026-08-06 — `two_torus_domain`'s outer-boundary facet group never reached the dolfinx facet tags (`GEO-10`)

The group was never *declared*, so nothing downstream could lose it. gmsh
inflates an OCC entity's bounding box by its geometric tolerance — measured at
exactly **`1.000e-07`** on all six walls of this box
(`20260806T050143Z_GEO-10-probe.log`) — and the fixture's flat-against-wall
test used `tol = 1e-9`. All six walls failed it, `boundary_surfaces` came out
empty, and the `if boundary_surfaces:` guard silently skipped
`addPhysicalGroup`. The chunk's prime suspect, fragment renumbering, is
**refuted**: the group is re-derived from bounding boxes after `fragment` +
`synchronize`, so renumbering never reaches it.

Fixed by widening that one tolerance to `1e-6` — 10× above the measured
padding and four orders below the nearest interior face's `2.000e-02`
residual, so the interior-face protection the tight test existed for is
intact. ~~No other fixture is affected: the rest of `io/mesh.py` uses a
`< resolution` wall test (loose by ~4 orders), and only `two_torus_domain` had
tightened it.~~ **Corrected 2026-08-06 by `GEO-11` measurement:** two other
fixtures had also tightened it to `1e-9` and have the identical defect —
`loop_over_half_space_domain` and `sphere_in_box_domain`, see entry 12. This
retirement stands (its own gate is unaffected); only the generality claim was
wrong.

Gated by `tests/mesh/test_two_torus_outer_boundary.py`: tag sets exactly `{1}`
ungapped and `{1, 201, 202}` gapped, and the assembled `ds` area over tag `1`
equals the analytic box surface `2(LW+LH+WH) = 3.220000000000e-02 m²` at
ratio **`1.000000000000000`** (`-n 2`,
`20260806T050313Z_GEO-10-gate-n2.log`, 25 s) and `1.000000000000001` (`-n 1`,
`…050350Z_…-n1.log`, 24 s) — planar walls, so this is an identity at `1e-9`,
not a band.

The open question the entry recorded is now answered: **neither Helmholtz
consumer depends on tag `1`.** Both were re-run with the group present and
their gated numbers are digit-identical — `MAG-14`'s centre-field error is
still `0.728%` (`…050656Z_GEO-10-helmholtz-regression.log`, 2 passed, 11 s).
The port-facet gate likewise reproduces `A_201 = A_202 = 1.563786482e-04 m²`
at `0.974490841` of analytic (`…050620Z_GEO-10-portfacet-digits.log`), so
adding a boundary group moved no interface tag. Full `tests/mesh` at `-n 2`:
**29 passed, 1 skipped, 107.64 s** (`…050421Z_GEO-10-mesh-regression.log`).

### 11. `two_torus_domain` gap-box terminal facet tags include lateral strips below `gap_overhang ≈ 6e-4`

| | |
|---|---|
| **Test** | `tests/validation/test_port_gap_voltage_impedance.py` disc-area band (on `attempt/PORT-1-step3bv-20260806T004500Z`, not on `main`) — and any future test that gates on the `201`/`202` facet areas at small overhang |
| **Symptom** | Measured facet-group area `1.643447371e-04 m²` per port at `gap_overhang = 2e-4` — `1.0241 ×` the exact oblique cut `1.604721580e-04 m²`, i.e. **above** a value an inscribed linear-tet section must sit below |
| **Cause** | Measured, not guessed (`PORT-1` step 3b-v, `20260806T003559Z_PORT-1-step3bv-gate.log`): at overhang 2e-4 the tube protrudes 0.2018 mm through the gap box's `−x` face over `2.821 mm < \|y\| < 3.989 mm` (box `min x` = 1.480000e-02, tube `min x` at `y = half_y` = 1.459821e-02), so the fragment-boundary intersection that defines tags `201`/`202` picks up the arc-end disc pair **plus two lateral strips**. The "gap box contains the arc ends" invariant fails below overhang ≈ 6e-4. 3b-iv's disc-area band was measured at overhang 1e-3, where the tube clears the face by 0.598 mm — it does not transfer to small overhang, and the mesh is not what is wrong. |
| **Verified at** | `main` fixture geometry as of `7747999`; the failing band assertion lives only on the parked branch |
| **Fix options, neither taken in-slot** | Raise `GAP_OVERHANG` back above ~6e-4 (changes the comparison geometry all 3b measurements share), or make the band overhang-aware (the strip area is computable from the same arithmetic above). A per-geometry decision for whoever next gates on these tags. |
| **Owned by** | `PORT-1` steps 3b-vi/3b-vii note it as a trap (do not gate on the 2xx areas at overhang 2e-4); entry leaves with the commit that restores an exact terminal-area anchor at the geometry it is asserted on |

### 12. ✅ RETIRED 2026-08-06 — `loop_over_half_space_domain` and `sphere_in_box_domain` never declared their `outer_boundary` group (`GEO-12`)

Fixed by widening both `tol` from `1e-9` to `1e-6` (`io/mesh.py`, the two sites
below) — exactly `GEO-10`'s fix, for the identical measured cause. Post-fix
(`20260806T183203Z_GEO-12-probe.log`): the loop fixture accepts **10 of 12**
dim-2 entities (the cube's four `z = 0`-split sides plus top and bottom; the
two rejected are the torus surface at `9.000010e-02` and the air/slab interface
at `1.000001e-01`) and the sphere fixture **6 of 7** (the sphere surface is
rejected at `1.500001e-01`). Both land on wall ratio
`1.0000000000287557e-01` — the same `1e-7/1e-6 = 0.1` `GEO-10` designed — so
`tests/mesh/test_boundary_classification_margins.py` now *asserts* the
two-sided margin for them instead of pinning a defect; the two `pytest.skip`s
are gone.

The group was invisible because nothing gated it, so the tolerance landed with
a meshed gate: `tests/mesh/test_wall_boundary_tag_areas.py` asserts per fixture
that facet tag `1` exists, carries an allreduced facet count > 0, and that its
assembled `ds` area equals the analytic cube surface `6(2W)² = 2.4e-01 m²` —
an identity on planar walls, gated at `1e-9` relative. Measured at `-n 2`
(`20260806T183328Z_GEO-12-gate.log`, 3.2 s): loop **1958 facets, ratio
1.000000000000000**; sphere **988 facets, ratio 0.999999999999999**.

The latency claim is now measured, not assumed. All six downstream callers plus
`tests/post/test_drop_set_semantics_sphere.py` were re-run and **no landed
number moved a digit**: `MAT-6` step 3 `dR` rel. error `1.5834%` / `dX` ratio
`0.9200`; step 4 `1.5763%` / `0.9849` (projected) and `1.5713%` / `0.8740`
(pinned), identical to `20260805T200455Z`/`20260805T200938Z`; `TH-8`/`MAT-4`
mass-averaged SAR ratio `0.999846` and the `POST-1` sphere table `4.2530%`
(`20260806T183745Z_GEO-12-callers-A.log`, 24 passed 210 s;
`20260806T184151Z_GEO-12-callers-B.log`, 8 passed 574 s). Whole `tests/mesh` at
`-n 2`: **35 passed, 2 skipped, 118.29 s**
(`20260806T183404Z_GEO-12-mesh-regression.log`).

Entry 13 is **not** covered by this fix and stays open — `cylindrical_domain`'s
margin is a different mechanism (tolerance coupled to `resolution`).

| | |
|---|---|
| **Test** | None fails. Measured and pinned by `tests/mesh/test_boundary_classification_margins.py` (`GEO-11`), which **skipped** the margin assertion for these two after pinning their numbers |
| **Symptom** | Both fixtures' wall test classifies **zero** surfaces — 0 of 12 and 0 of 7 dim-2 entities — so `boundary_surfaces` is empty and the `if boundary_surfaces:` guard silently skips `addPhysicalGroup`. Facet tag `1` does not exist in the returned `facet_tags` |
| **Cause** | Measured, not guessed (`20260806T140325Z_GEO-11-probe.log`): identical to retired entry 10. Both use `tol = 1e-9` (`io/mesh.py` ~lines 1384 and 1532) against gmsh's OCC bounding-box padding, which is the same **`1.000e-07`** `GEO-10` measured on `two_torus_domain` — the tolerance sits **100× below** the padding it must clear. Retired entry 10's closing claim that "no other fixture is affected" was wrong: it checked the `< resolution` fixtures and missed these two, which had also tightened the test |
| **Live impact** | **None — latent.** Every caller of both generators discards the facet tags (`msh, cell_tags, _ = MeshGenerator...`) in `test_dodd_deeds_impedance.py`, `test_dodd_deeds_projected_drive.py`, `test_dodd_deeds_reactance_box_size.py`, `test_dielectric_sphere.py`, `test_lossy_sphere_sar.py`, `test_mass_averaged_sar.py`, and imposes its wall condition geometrically instead. No landed `MAT-6`, `TH-8` or `MAT-4` number reads the missing group, so none of them is wrong |
| **Verified at** | `main` as of `2cad984` |
| **Fix, not taken in-slot** | Widen both to `1e-6`, exactly as `GEO-10` did — the nearest interior faces sit at `9.000e-02` and `1.500e-01`, so `1e-6` keeps 5 orders of interior-face protection. `GEO-11`'s plan reserves any tolerance change for a review with the numbers in hand, which these are. Whoever takes it must add a facet-tag assertion at the same time: the defect was invisible precisely because nothing gates the group |
| **Owned by** | `GEO-12` (commissioned by the 2026-08-06, 10:30 review — §9 item 2, with the tolerance decision taken); **discharged 2026-08-06, 13:30 implementer slot** — see the retirement note above |

### 13. ✅ RETIRED 2026-08-07 — `cylindrical_domain`'s classification margin was 4.50× its tolerance (`GEO-13`)

The tolerance was the *mesh size*: `abs(r_max - outer_radius) < resolution`. It
is now `0.01 × (outer_radius - inner_radius)` — a fraction of the radial gap,
so the margin is a ratio of geometry to geometry and no longer moves when a
caller coarsens the mesh. Measured across all four argument sets the repo calls
the generator with (`20260807T033127Z_GEO-13-probe.log`): the fraction window
where **both** sides of the `GEO-11` identity hold is `[1e-4, 0.05]`, and `0.01`
sits in the middle of it. At defaults the interior margin goes
**`4.499995×` → `99.99989×`** (floor `10×`) with the accepted side at
`1.111111e-04×` (ceiling `0.1×`), and the classification itself is **unchanged**
— still 3 of 6 surfaces, on every one of the four geometries.

The failure mode the entry named is reproduced in the probe before the fix: at
`resolution = 0.09` (the gap) the old predicate accepts **6 of 6** surfaces, the
inner cylinder swept whole into `outer_boundary`.

`tests/mesh/test_boundary_classification_margins.py` now **asserts** the
two-sided margin for this fixture instead of pinning it — the pin and its skip
are gone, and the file reads the fraction from the generator so the two cannot
drift apart. All four fixtures in that file are now live: **5 passed in 1.05 s**
(`20260807T033236Z_GEO-13-margins.log`, `-n 1`). Regression: whole `tests/mesh`
**36 passed, 1 skipped in 110.34 s** (`20260807T033250Z_GEO-13-mesh-regression.log`,
`-n 2`) — one skip fewer than the 35/2 on record, which is this fixture. Callers
green at `-n 2`: `4 passed, 1 skipped in 0.97 s`
(`20260807T033454Z_GEO-13-callers.log`; the skip is the complex-mode PEC test).

**Live precondition, new:** the tolerance scales with the gap, so a gap below
~`1e-4` m stops clearing the `1.000e-07` gmsh OCC bounding-box padding by 10×.
Recorded at the use site in `io/mesh.py`; no caller is near it (smallest gap in
the repo is `0.07` m).

<details>
<summary>Original entry</summary>

| | |
|---|---|
| **Test** | None fails. Measured and pinned by `tests/mesh/test_boundary_classification_margins.py` (`GEO-11`), which skips the margin assertion after pinning the ratio |
| **Symptom** | The nearest surface the wall test *rejects* sits at residual `8.999990e-02` = **`4.499995 ×`** `tol`, below the `10×` floor `GEO-11` asserts. The accepted side is fine (`5.000e-06 × tol`) |
| **Cause** | Measured (`20260806T140325Z_GEO-11-probe.log`): the test is `abs(r_max - outer_radius) < resolution` with `tol = resolution = 0.02` at defaults. The inner cylinder's surface and end caps sit at `r_max = inner_radius = 0.01`, a residual of `0.09`. The margin is a ratio of geometry to *mesh size*, so it shrinks as either radius gap narrows or `resolution` coarsens — at `resolution ≥ 0.09` the inner cylinder would be swept into `outer_boundary` |
| **Live impact** | **None at defaults.** `tests/mesh/test_cylindrical_domain.py` passes; the classification is correct today, only under-separated |
| **Verified at** | `main` as of `2cad984` |
| **Fix, not taken in-slot** | Either decouple the tolerance from `resolution` (a geometric fraction of `outer_radius - inner_radius` is the natural choice) or document the sizing precondition. A per-fixture decision for a review, per the `GEO-11` plan |
| **Owned by** | `GEO-13` (filed 2026-08-06, 18:00 review, with the geometric-fraction fix and the un-skip of the margin assertion; was `GEO-11`, whose sweep found it); **discharged 2026-08-07, 22:30 implementer slot** — see the retirement note above |

</details>

### 7. ✅ RETIRED 2026-08-03 — birdcage mesh fails to generate (`GEO-9`, steps 1 + 2a + 2b)

All three tests are green and the whole of `tests/mesh` less known-issues 5 is
`20 passed, 1 skipped, 1 deselected in 42.15 s`, exit 0
(`20260803T200504Z_GEO-9-step2b-gate.log`, `-n 2`) — the CI command verbatim,
with the birdcage `--ignore` removed in the same commit. **Step 2b** replaced the
`occ.cut(..., removeTool=False)` with a single `occ.fragment` of the air box
against every tool, so the legs and rings that pierce each other by construction
are booleaned into conforming pieces instead of being meshed twice; the physical
groups are re-derived from the fragment out-map (26 volumes, 20 of them
conductor) and the port boxes get the 3-D groups they never had. Measured:
`V_mesh/V_box = 1.000000000000` and `Σ(tagged)/V_mesh = 1.000000000000`, both
gated to `1e-9`, and every port box exact to `1e-9` of `dx·dy·dz`. The
rank-local `set(np.unique(cell_tags.values))` was fixed to `global_cell_tag_set()`
in the same commit — it was real and it fired: at `-n 2` rank 0 reported P2/P3
missing and rank 1 reported P1/P4 missing on an otherwise correct mesh
(`20260803T200151Z_GEO-9-step2b-probe.log`).

The history below is kept because several commits and the `GEO-9` §7 entry refer
to it, and because the diagnosis — one poisoned generator hanging every later
mesh in the process — is the reusable part.

<details>
<summary>Original entry (steps 1 and 2a)</summary>

#### Birdcage mesh fails to generate *(coil+phantom half resolved 2026-08-03, `GEO-9` step 2a)*

| | |
|---|---|
| **Tests** | `tests/mesh/test_birdcage_port_tags.py::test_birdcage_like_mesh_has_core_and_port_tags` — **still red**, the overlapping-facets geometry is `GEO-9` step 2b<br>~~`tests/mesh/test_coil_phantom_mesh.py::test_coil_phantom_mesh_generates_required_tags_centered_preset`~~ **passes since 2026-08-03**<br>~~`tests/mesh/test_coil_phantom_mesh.py::test_coil_phantom_mesh_off_center_preset_moves_phantom_without_overlap`~~ **passes since 2026-08-03** |
| **Symptom** | `gmsh.py:2006: Exception: Invalid boundary mesh (overlapping facets) on surface 3 surface 49` (birdcage) and `dolfinx/io/gmshio.py:118: AssertionError` ×2 (coil+phantom) — the meshes never reach dolfinx |
| **Cause** | **Diagnosed 2026-08-03 by `GEO-9` step 1, and it is a single cause, not two.** `birdcage_port_domain` raises inside its `comm.rank == rank` block (the overlapping-facets error) and therefore never reaches its `gmsh.finalize()`. The process is left with gmsh initialised and mid-command, so the *next* generator in the same pytest process gets `Warning : Gmsh has aleady been initialized` and `Info : I'm busy! Ask me that later...`, every subsequent `occ` call is silently refused, and `model_to_mesh` reads the stale birdcage model — whose mixed element types are what `gmshio.py:118` asserts on. **The coil+phantom generator is innocent:** in a fresh process all three of its tests pass in 4.8 s (`20260803T033050Z_GEO-9-before.log`), and they fail again the moment the birdcage file runs first (`20260803T033119Z_GEO-9-order-probe.log`, 3 failed 2 passed in 3.47 s — the same two failures). Found 2026-08-01 by the `GEO-8` run, which ran `tests/mesh` as a regression sweep; the whole directory is in no CI job, which is why these were invisible. Both fixtures are untouched by `GEO-8` (it changed `two_torus_domain` only). |
| **Verified pre-existing at** | `63c94f2` — the `GEO-8` diff touches neither generator; log `20260801T004839Z_GEO-8-unrelated-failures.log`, 3 failed 2 passed in 3.5 s at `-n 2` |
| **Note** | ~~Likely the same overlapping-geometry family `GEO-8` just fixed for `two_torus_domain`: `coil_phantom_domain` and the birdcage fixture should be audited for missing `occ.fragment`.~~ **Half wrong — corrected 2026-08-02, 18:00 review, by code reading (not by execution).** `coil_phantom_domain` **already fragments** (`io/mesh.py:1616`), so its cause is downstream of fragment; the visible fragility is the group re-derivation at `io/mesh.py:1622-1634`, which assumes fragment returns exactly four volumes and leaves any extra piece with no physical group — which is what `gmshio.py:118` asserts on. The **birdcage** does match the family, differently: it uses `occ.cut(..., removeTool=False)` (`io/mesh.py:1970`), so the conductors, phantom and port boxes are never booleaned against *each other* and the port boxes overlap the legs by construction — hence "overlapping facets". The birdcage's port boxes also receive no 3-D physical group (`io/mesh.py:1985-1988`). |
| **Owned by** | `GEO-9` (created 2026-08-02): step 1 coil+phantom, step 2 birdcage. Two of the four §10 Target criteria route through these two fixtures. **Step 1 landed 2026-08-03** — the coil+phantom half is now gated by `tests/mesh/test_coil_phantom_conforming.py` (volume-partition identity, `20260803T033659Z_GEO-9-step1-gate.log`, 8 passed 1 skipped in 22.25 s) and the generator raises with the volume count and per-volume masses if fragment ever does return other than four grouped volumes. **All three tests above still fail in a shared process** and will until step 2 fixes the birdcage: `20260803T033733Z_GEO-9-order-probe-after.log` shows the new guards do *not* fire (gmsh is already busy, so they never execute), still `gmshio.py:118`. **Step 2's first action is the cheap half of this — wrap the birdcage's rank-0 block in `try/finally: gmsh.finalize()`**, which stops one broken generator from poisoning every later mesh in the process, independently of fixing the geometry. Split out as **`GEO-9` step 2a** at the 2026-08-03 03:00 review, with step 2b holding the `occ.fragment` geometry rewrite. |
| **A poisoned process hangs — added 2026-08-03, 03:00 review** | Both `GEO-9` order probes report pytest finishing (3.47 s and 3.29 s) but the **harness** exits **124 at the 180 s ceiling**, with `Loguru caught a signal: SIGTERM` (`docs/testing/test-results.md:136,139`; logs `20260803T033119Z_GEO-9-order-probe.log`, `…033733Z_GEO-9-order-probe-after.log`). The step-1 prose quotes only the pytest wall time and does not say this. Two consequences: `tests/mesh` cannot enter CI with the birdcage in it (`OPS-11`) because the job would burn its whole `timeout-minutes` rather than fail fast; and `GEO-9` step 2a gets a sharper anchor than "the tests pass" — harness exit **124 at 180 s → 0 in seconds**. If a `try/finally` does not fix it, suspect an MPI collective the raising rank never reaches, not gmsh state. |
| **Excluded from CI, and the reason has changed — `OPS-11`, 2026-08-03** | The `validation` job's `Mesh generation suite` step `--ignore`s `test_birdcage_port_tags.py`. The exclusion no longer rests on the hang or the budget: post-2a the file fails **promptly** (the unexcluded-directory control `20260803T170132Z_OPS-11-fullsweep.log` is 2 failed 18 passed 1 skipped in 31.85 s, harness exit 1 in 33 s, where the pre-2a probes exited 124 at the 180 s ceiling). It is ignored because it is deliberately red until `GEO-9` step 2b, and a permanently-red test in CI hides regressions behind an expected failure. **Remove the `--ignore` in the commit that fixes the geometry.** The same control also shows the coil+phantom tests now passing *with the birdcage in the same process* — the step-2a poisoning fix holding under the condition that used to break it. |
| **✅ Two-thirds resolved 2026-08-03 by `GEO-9` step 2a — and the hang was *both* causes, not one** |<!-- retired: see the summary above --> The review's warning was right: `try/finally` alone would not have fixed the hang. Rank 0 raised and skipped the collective `gmshio.model_to_mesh`, so rank 1 blocked in it forever — that is the exit 124, and gmsh contamination is a second, independent defect. `birdcage_port_domain` now builds its model in `_build_birdcage_port_model`, calls `gmsh.finalize()` (guarded by `gmsh.isInitialized()`) when that raises, and `comm.bcast`es the failure so **every** rank raises before any enters `model_to_mesh`. The birdcage still fails loudly with the original message. **Before** (`20260803T123116Z_GEO-9-step2a-before.log`, re-run at the working commit, not quoted): 5 failed 2 passed in 3.16 s of pytest, harness **exit 124 at 180 s**. **After** (`20260803T123549Z_GEO-9-step2a-after.log`, same command): **1 failed 6 passed in 12.10 s, harness exit 1 at 13 s** — only the birdcage test itself. Gated by `tests/mesh/test_birdcage_finalize_isolation.py` (`20260803T123657Z_GEO-9-step2a-gate.log`, 1 passed in 5.30 s, **exit 0**), which runs the two generators in the poisoning order in one process and asserts `V_mesh/V_box = 1.000000000000` and `Σ(tagged)/V_mesh = 1.000000000000` to `1e-9` afterwards. `tests/mesh` less the birdcage file is now 17 passed 1 skipped, 1 failed in 28.46 s (`20260803T123714Z_GEO-9-step2a-sweep.log`) — the single failure is **entry 5**, unrelated. |

</details>

---

## Non-test issues

### ✅ RETIRED 2026-08-04 — reaction Z-matrix diagonal is negative where it must be inductive

**Fixed by `PORT-1` step 2f**: `TimeHarmonicSolver.solve()` now drives with the
CG1-weakly-solenoidal part of the prescribed current by default
(`project_source=True`, helper
`src/fem_em_solver/core/source_projection.py`), and the diagonal of
`test_port_reaction_impedance.py` is **gated**, not printed. Gate
`20260804T111102Z_PORT-1-step2f-gate.log`, 12 passed 1 deselected in 58.9 s at
`-n 2`, on the same fixture every measurement below was taken on:

| quantity | production path, projected | this entry's unprojected number |
|---|---|---|
| `Im Z₁₁`, reaction / energy routes | **`+7.437243e+00 Ω`** (both) | `−4.108550e+01 Ω` |
| `Im Z₂₂`, reaction / energy routes | **`+7.436633e+00 Ω`** (both) | `−4.092413e+01 Ω` |
| ratio to Grover `ωL = 6.818343 Ω` | **1.090770 / 1.090680** | −6.03 |
| complex-power identity residual | `4.0412e-11` / `9.1813e-11` (gated `< 1e-9`) | `1.8128e-10` |
| driven current | `I′ = 0.969001 A` | `I = 0.969009 A` |

The three gates are `test_projected_port_diagonal_is_inductive` (sign, a
priori, both ports, both routes), `..._satisfies_the_complex_power_identity`
(bookkeeping, `< 1e-9`) and `..._matches_grover` (the independent physics
anchor, band `(1.042, 1.140)` carried over from step 2e's measurement, which
the production path reproduced to 2e-5). The number reproduced step 2e's
hand-rolled `+7.437243e+00 Ω` to all seven printed figures — same physics,
now on the path callers actually use.

Nothing was widened to retire this: the diagonal moved from *ungated* to
gated, and the three files that pin the unprojected numbers (steps 2b, 2d, 2e)
now pass `project_source=False` explicitly and reproduce them unchanged
(`20260804T111221Z_PORT-1-step2f-regress-diagnosis.log`,
`20260804T111607Z_PORT-1-step2f-regress-remainder.log`). The original entry
follows, unedited, because the diagnosis chain in it is the reason the fix is
believable.

---

Found 2026-08-02 by `PORT-1` step 1; **diagnosed 2026-08-03 by step 2b to the
electric energy — see the update at the end of this entry — and still not
fixed.** The diagonal remains ungated. Recorded here because the number is wrong
in a way a later run would otherwise re-discover from scratch.

On the two-torus air fixture (a = 0.04 m, r_wire = 0.005 m, d = 0.04 m,
f = 10 MHz), the reaction integral `Z_i1 = −(1/(I₁Iᵢ))∫E₁·Jᵢ dV` returns
`Im Z₁₁ ≈ −40.9 Ω` (`-4.069329e+01j` at
`20260802T183226Z_PORT-1-step1-solve008.log:442`, and −41.09 / −40.97 at the two
boxsens configurations). A lossless loop must be inductive, `+ωL`; a Grover
estimate `ωL ≈ μ₀ωa(ln(8a/r_wire) − 2) ≈ 6.8 Ω` — **hand-evaluated, in no log**.
So the diagonal is wrong in sign and ~6× in magnitude, while the *off*-diagonal
on the same solve is right in sign and within 5–9% of its closed form. That
contrast points at the self-term (the source's own singular field inside the
driven wire entering `∫E·J` over the source region) rather than at a global
convention error, but nothing has been measured to confirm it.

**Consequence:** no input impedance and no `S₁₁` derived from this path means
anything yet. `PORT-1` step 2 therefore leaves the diagonal **ungated** —
deliberately, and *not* by widening a bound. `PORT-1` step 2b (§7) owns the
diagnosis, and its anchor is the complex-power identity
`Im Z₁₁ = 4ω(W_m − W_e)/|I₁|²` as an independent second derivation.

**Update 2026-08-03 — step 2b executed; the reaction integral is exonerated and
the anomaly is localised to the electric energy.**
`tests/validation/test_port_self_impedance_energy.py`, 3 passed in 43.5 s at
`-n 2` (log `20260803T050252Z_PORT-1-step2b-gate.log`), one mesh at padding
0.08 / h_far 0.03 and one solve:

| quantity | value |
|---|---|
| `Im Z₁₁`, reaction integral | `−4.108550e+01 Ω` |
| `Im Z₁₁`, complex-power route `4ω(W_m−W_e)/I²` | `−4.108550e+01 Ω` |
| relative disagreement | **1.8128e-10** (gated `< 1e-9`) |
| `4ωW_m/I²` (inductive part) | `+7.437 Ω` vs Grover `ωL = 6.818 Ω`, **ratio 1.0908** |
| `4ωW_e/I²` (capacitive part) | `+48.52 Ω` |
| `W_e/W_m` | 6.524 |

So the guess above — that the self-term of `∫E·J` is the bug — is **wrong**. The
two derivations agree to 1.8e-10, and the magnetic half is the physical loop
inductance to 9.1% of Grover, which is within what the PEC box at this padding
can plausibly account for. The whole of `−40.9 = 7.44 − 48.52` is an *electric*
energy excess in the solved field.

**Leading hypothesis, not yet measured:** low-frequency breakdown of the
curl-curl formulation. At ω → 0 the operator acts on the gradient subspace as
`−k₀²ε_c`, so any residual non-solenoidal component of the discretised impressed
current — the analytic azimuthal `J` is exactly divergence-free and tangent to
the torus surface, but the *faceted* meshed boundary is only approximately so —
is amplified into a spurious electrostatic field that contributes to `W_e` and to
nothing else.

**Correction 2026-08-03 (03:00 review): the ω-sweep named here as "the
discriminating measurement" does not discriminate.** Restricting the solved
equation to the gradient subspace gives `E_g = jωμ₀J_g/k₀² = jJ_g/(ωε₀) ∝ 1/ω`,
hence `W_e ∝ ω⁻²` and `4ωW_e/I² ∝ ω⁻¹` — **the same `1/(ωC)` a physical
capacitance gives.** Gradient-space contamination *is* a spurious electrostatic
response, so it necessarily scales like one, and the sweep separates only the
capacitive family (`ω⁻¹`) from an induction-driven `E = −jωA` (`4ωW_e/I² ∝ ω³`).
It is a cheap sanity check, not the discriminator; do not spend a run on it
expecting an answer.

What does settle it, and why this fixture makes it decisive: the two-torus
fixture has **no conductors** — the tori are tagged *air* subdomains carrying an
impressed `J`, the only metal is the outer PEC wall, and `∇·J = 0` analytically
means no charge. There is therefore **no physical capacitance available to
find**, so the open question is quantitative: does the gradient content of the
load account for all 48.52 Ω? Because the N1curl/CG1 discrete sequence is exact,
that is answerable by two assemblies and no extra solve —
`∫E_h·∇q dV = (j/(ωε₀))∫J·∇q dV` must hold for every `q ∈ CG1 ∩ H¹₀` — with the
energy share following from one cheap scalar Poisson solve. `PORT-1` step 2d in
`PROJECT_PLAN.md` §7 carries the plan; `tests/validation/test_current_divergence.py`
(`POST-3` step 3) is the second, structural route to the same question.

**Update 2026-08-03 — step 2d executed; the answer is "all of it", and the cause
is now measured rather than hypothesised.**
`tests/validation/test_port_gradient_load.py`, 7 passed in 41.5 s at `-n 2` (log
`20260803T183556Z_PORT-1-step2d-gate.log`), same mesh, one curl-curl solve and
one CG1 Poisson solve:

| quantity | value |
|---|---|
| identity `∫E_h·∇q = (j/ωε₀)∫J·∇q`, relative residual | **4.4916e-09** (gated `< 1e-7`) |
| blind control, `j` dropped | 1.4142e+00 = `√2`, as the identity implies |
| `‖P_G J‖²` | `2.534713e-02` (two routes agree to 7.9e-15) |
| `4ωW_e^spur/I² = ‖P_G J‖²/(ωε₀I²)` | **`4.852262e+01 Ω`** |
| measured `4ωW_e/I²` | `4.852271e+01 Ω` |
| **ratio** | **0.999998** |

So the "leading hypothesis" above is confirmed *quantitatively*: the gradient
content of the **discretised** impressed current, amplified by `1/(ωε₀)` on the
subspace where the operator acts as `−k₀²ε_c`, is two-parts-in-a-million the
entire electric-energy excess. Nothing is left for a second mechanism. The
negative diagonal is an artifact of the current representation — not the
reaction integral (step 2b), not physical capacitance (none exists here).

The identity's bound was raised 1e-9 → 1e-7 after a first run measured
4.4916e-09 and failed the plan's house guess; the gate reproduced 4.4916e-09
bit-for-bit. It is a solve-accuracy number, not a physics one — a rank-count,
mesh or solver change that moves it is information, so re-measure rather than
widening again. PROJECT_PLAN §7 `PORT-1` step 2d carries the full reasoning.

**Step 2e executed 2026-08-04 — the fix works, and this entry still stays
open.** `tests/validation/test_port_solenoidal_drive.py` drives the same mesh
with `J′ = J − P_G J` and gets the prediction to three figures
(`20260804T050616Z_PORT-1-step2e-gate.log`, 9 passed in 41.8 s at `-n 2`):

| quantity | projected drive | unprojected (this entry) |
|---|---|---|
| `Im Z₁₁`, both routes | **`+7.437243e+00 Ω`** | `−4.108550e+01 Ω` |
| ratio to Grover's `ωL = 6.818343 Ω` | **1.090770** | −6.03 |
| `4ωW_e/I′²` | `8.761041e-05 Ω` | `4.852271e+01 Ω` |
| `‖P_G J′‖²/‖J′‖²` | `4.5758e-33` | `8.175e-06` |
| complex-power identity residual | `1.6242e-14` | `1.8128e-10` |
| meshed current | `I′ = 0.969001 A` | `I = 0.969009 A` |

`4ωW_m/I′² = 7.4373 Ω` is step 2b's number unchanged, as it must be — the
projection moves `W_e`, not `W_m` — so the fixture's inductance was physical
throughout and the sign is now explained *and* demonstrated, not just
diagnosed.

The entry stays open because **the production driver still builds the
unprojected load**: `TimeHarmonicSolver.solve()` assembles
`−jωμ₀∫J·v̄` from the caller's `current_density` with no projection, so the
diagonal in `test_port_reaction_impedance.py` is still negative and still
ungated. Making the projection the port-excitation default is its own step.

**Consequence, unchanged:** no input impedance and no `S₁₁` off this path means
anything. The off-diagonal is unaffected — `PORT-1` step 2 gates `Im Z₁₂` to
9.35% of `ωM₁₂` and that number does not go through `W_e`.

Remove this entry with the commit that explains the sign.

*(That step is 2f and it landed 2026-08-04 — see the retirement header at the
top of this entry. The off-diagonal did move slightly, as the projection
changes the field and not only its gradient part: `Im Z₁₂` went from
`+1.125614e+00 Ω` (−9.35% of `ωM₁₂`) to `+1.142011e+00 Ω` (**−8.03%**), toward
the closed form, under the unchanged 10% gate.)*

### ✅ RESOLVED 2026-08-03 — "birdcage suite is over the compute budget" was the hang, not meshing cost

The 10:30 review's reinterpretation was right and `GEO-9` step 2b's cost probe
settles the figure. The claim was that
`tests/mesh/test_birdcage_port_tags.py` takes **~10 minutes** on its own and
that a full `tests/mesh` run exceeded a 700 s bound. **Measured at the fixed
geometry, default parameters, no coarsening:** the file is **8.95 s** of pytest,
harness 10 s (`20260803T200151Z_GEO-9-step2b-probe.log`), and the whole
directory at `-n 2` is **42.15 s**, exit 0
(`20260803T200504Z_GEO-9-step2b-gate.log`). The old number was a poisoned
process burning the harness `timeout` — pytest reported in ~3 s while the run
exited 124 at 180 s — so `resolution` never had to be coarsened from 0.015 and
the file needs no exclusion from routine runs. It is in CI as of this commit.

The **latent rank-local tag bug** recorded here is also fixed, and it was not
latent: `set(np.unique(cell_tags.values))` is per-rank, and at `-n 2` on the
newly-working mesh rank 0 reported P2/P3 missing while rank 1 reported P1/P4
missing. `GEO-9` step 2b switched the test to
`tests/mesh/helpers.py::global_cell_tag_set()` — the fix that was written and
reverted on request pending exactly this rework. The assertion content (core +
per-port tags all present) is unchanged.

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

### ✅ RESOLVED 2026-07-30 — truncation-wall modeling floor on the wire/loop fixtures (MAG-13)

The natural BC `n×H = 0` on a truncation wall contradicts Ampère's law for any net
enclosed current (`∮H·dl = I` vs `H_φ(R) = 0` forced at the wall), so it puts a
floor under these fixtures that no refinement removes.

**Straight wire: fixed 2026-07-30** (`MAG-13` steps 1–3). `test_straight_wire.py`
now imposes the analytic `A_z` on the exterior via
`core.solvers.exterior_dirichlet_bc`; measured 35.13% → 22.19% at h=0.004 on the
same mesh, and 22.19% → 12.75% → 9.26% across h = 0.004/0.0025/0.0018, i.e. still
converging at ~O(h^1.2) with no plateau. `J·n ≠ 0` at the end caps remains (the
`MAG-15` multiplier spread measures it) but is not what was dominating.

**Loop: fixed 2026-07-30** (`MAG-13` steps 4–5). `test_circular_loop.py` now
imposes the Jackson 5.37 off-axis `A_φ` on the outer sphere through the same
helper, and `test_convergence.py::test_h_refinement_straight_wire` fits the rate
over three resolutions (**1.10**, bound `[0.7, 1.5]`) instead of two.

One measurement worth keeping: on the *loop*, the analytic wall is ~20% **worse**
at fixed h than the natural one (16.23% vs 14.98% at h=0.0035; 10.37% vs 8.86% at
h=0.0025, on-axis `B_z` over `|z| ≤ 0.4 R`). Unlike the wire's Ampère-law
contradiction, the loop's natural-BC bias is a PMC image term of order
`(a/R)³ ≈ 3.7%`, which is *smaller* than the O(h) error that degree-1
interpolation of `A_φ` injects through the boundary data. What the Dirichlet wall
buys is the limit: 16.23% → 10.37% → 7.07% at h = 0.0035/0.0025/0.002 converges
monotonically to the analytic field (fitted ~1.4), where the natural wall
converges to a different field. The loop tolerance is therefore tightened
10% → 8% *at h = 0.002* (411k cells) rather than at the old h = 0.0025 — no
assertion was loosened to accommodate the better boundary condition.

Remaining, not blocking: `J·n ≠ 0` at the wire end caps, and the < 5% wire target
needs h ≈ 0.00125 (~1.1M cells, > 5 min at `-n 2`) — graded refinement (`MAG-9`),
not more uniform h.

### ✅ RESOLVED 2026-08-01 — `two_torus_domain` was not a conforming mesh (`GEO-8`)

The fixture added two tori and `occ.addBox` over them and never fragmented, so
gmsh meshed a solid box plus two torus islands: total mesh volume exceeded the
analytic box by exactly the two torus volumes (ratio `1.002633`), and driving
torus 1 with a tag-restricted source gave `∫|E|² dV` over tags (1, 2, 3) =
`2.0537e-04, 0, 0` — the field could not leave the driven island, which is why
`PORT-1` measured `Z₁₂ ≡ 0`.

Fixed by `occ.fragment` plus centroid/mass re-derivation of the physical
groups. Both signatures are now gated by
`tests/mesh/test_two_torus_conforming.py`: volume ratio `1.000000000`
(log `20260801T003528Z_GEO-8-after.log`) and air/driven `∫|E|²` ratio
`1.4118`, undriven/driven `5.2088e-08` (log
`20260801T003600Z_GEO-8-field-gate-numbers.log`). The Helmholtz users improved
rather than regressed: centre-field error `1.731% → 0.728%`.

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
