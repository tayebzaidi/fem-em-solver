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
| **Symptom** | `assert 0.09 > 0.09` |
| **Cause** | Not diagnosed. Pure geometry arithmetic in `MeshGenerator.coil_phantom_domain_sizing_diagnostics` — no solve involved, so no solver change can affect it. |
| **Verified pre-existing at** | `794d2f1` (pre-session); still failing 2026-08-03 at `de6d40a` (`20260803T034252Z_GEO-9-step1-cohabit.log`, 1 failed 16 passed 1 skipped in 22.95 s) |
| **Excluded from CI** | Since `OPS-11` (2026-08-03) the `validation` job's `Mesh generation suite` step `--deselect`s this node id by name. **Remove that `--deselect` in the commit that fixes this entry** — it is the only thing keeping the test out of CI, and the rest of the file runs there. |
| **Cited wrongly as "known-issues 6"** | Commit `3ac025c` and `docs/testing/attempts.md:1903,1907` both call this entry 6. **It is entry 5.** Entry 6 is the rank-dependent single-port excitation test in `tests/solver`, unrelated to `tests/mesh`. `attempts.md` is append-only so the correction lives here and in the `OPS-11` §7 entry; it matters because `OPS-11`'s exclusion set is **5 and birdcage**, not "6 and 7". |

### 6. Rank-dependent: single-port excitation

| | |
|---|---|
| **Test** | `tests/solver/test_single_port_excitation.py::test_single_port_excitation_returns_finite_estimates` |
| **Symptom** | Passes at 1 rank, fails at `mpiexec -n 8` |
| **Cause** | Not diagnosed. Two rank-local bugs of this family were already fixed on 2026-07-27 (`tests/solver/test_two_torus.py` asserted on rank-local `cell_tags.values`; `test_helmholtz_v2.py` did a per-rank collision search). Suspect the same pattern — a quantity that is rank-local being treated as global. |
| **Tool** | `tests/mesh/helpers.py::global_cell_tag_set()` exists for the tag case. `post.evaluation.evaluate_vector_field_parallel()` for the point-location case. |
| **Verified pre-existing at** | `ce92e8c` and earlier |

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

### 2026-08-03: the 16:30 implementer cron slot never fired — no log at all

Observed by the 18:00 daily review. The 21:30Z slot (fourth after the 10:30
review) produced **no file in `logs/automation/`** — not even the one-line
lock-skip entry `scripts/automation/implementer-run.sh` writes when another
run holds the lock, which is the first thing the script does after cron
invokes it. So cron never invoked it: the entry is missing/edited, or the
host skipped the minute. Every earlier slot that day logged (skip or run).
Consequence: `MAT-4` step 2 sat open and unattempted for the interval. The
review sandbox cannot read the crontab, so this needs a human check of
`crontab -l` against the 90-minute grid. Not a tree outage — preflight was
never involved. Entry leaves when the cause is identified (with a note in the
fixing commit) or when a full day of slots logs cleanly and it is downgraded
to a one-off.

**Update 2026-08-04 (03:00 review):** no recurrence — every slot since has a
session log (00:30Z preflight stop, 02:00Z, 03:30Z, 05:10Z runs; the 23:00Z
review). One more clean review interval completes the "full day of slots" and
downgrades this to a one-off; the crontab check by a human is still the faster
route to closing it.

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
