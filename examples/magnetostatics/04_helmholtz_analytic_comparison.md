# `-e 4` — Helmholtz coil, on-axis `B_z` vs the analytic field

Guide for `examples/magnetostatics/04_helmholtz_analytic_comparison.py`.
Written to be followed without the source open.

## 1. What this demonstrates

Two coaxial tori (major radius `R = 0.02 m`, minor radius `a = 0.005 m`,
separated by `R` — the Helmholtz condition) carrying azimuthal current density,
with the on-axis `B_z` compared against the filamentary closed form

```
B_z(z) = Σ_loops  μ₀ I R² / (2 (R² + (z − z_i)²)^{3/2}),   I = |J| · π a²
```

and — unlike the other magnetostatics examples — swept over **three mesh
resolutions in one run**, so the reader sees whether the error is
discretisation or a systematic floor.

It is also the **corrected counterpart** of the deleted example 03 (the file is
gone, and is deliberately not named here — the reference checker would flag the
name, which is how the dead reference in `PARAVIEW_VALIDATION_GUIDE.md` was
caught), which evaluated with `B.eval(points, np.arange(n))` — asking dolfinx to
evaluate each point in an *arbitrary* cell rather than the one containing it,
which produces meaningless numbers. This example uses
`post.evaluation.evaluate_vector_field_parallel` (bounding-box tree + collision
search). That is the single most important thing it demonstrates about how to
sample a field in this codebase.

**Two accuracy floors that do not shrink with refinement**, both stated in the
source:

1. **Finite wire thickness** — the closed form is a filament; the model is a
   torus at `a/R = 0.25`, biasing the centre field by `O((a/R)²)`, order a few
   percent. `--minor-radius` trades thinness against cost.
2. **Domain truncation** — the outer box carries `n × (μ⁻¹ curl A) = 0`, a
   perfect magnetic conductor that mirrors flux back in. At the legacy
   `2·minor_radius` padding this alone cost ~20% at the centre
   (`docs/validation/helmholtz.md`); the default is now `4·major_radius` with
   graded far-field refinement, which pushes it below 0.1%. `--air-padding`
   overrides it.

On record at `-n 2`, all three rungs from one run
(`20260810T093203Z_EX-15-step1-refresh-allmag.log`, 2026-08-10; analytic centre
field `3.531057e-09 T` throughout):

| `h` [m] | `h/a` | cells | mesh / solve | centre `B_z` FEM | centre rel err | on-axis mean / max | central CV |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.005 | 1.00 | 70 054 | 8.6 s / 4.0 s | 3.562433e-09 T | **0.89%** | 2.11% / 7.98% | 0.111% |
| 0.0035 | 0.70 | 103 984 | 13.6 s / 6.9 s | 3.522577e-09 T | **0.24%** | 0.88% / 6.07% | 0.013% |
| 0.0025 | 0.50 | 160 478 | 22.3 s / 16.5 s | 3.485828e-09 T | **1.28%** | 1.47% / 4.05% | 0.051% |

**The centre error is not monotone in `h`, and that is the result, not a
defect** — it is what hitting the systematic floor looks like: refinement moves
the answer around inside the few-percent band set by `a/R` and the truncation,
instead of walking it toward zero. The *max* on-axis error does fall
monotonically (7.98 → 6.07 → 4.05%), because that number is dominated by the
far points where discretisation still rules.

The gated Helmholtz number is a different fixture: `MAG-14` (✅, smoke), the
magnitude comparison in the test suite, **0.728%** vs closed form (1.731%
before `GEO-8`; PROJECT_PLAN.md §7, re-verified in
`…050656Z_GEO-10-helmholtz-regression.log`). Do not conflate the two.

## 2. How to run it

```
./run_examples.sh -e 4 -n 2 -t 180
```

Real DolfinX build; the runner selects it. Tier: **standard**. On record the
three-rung sweep is the expensive part of the magnetostatics group: the
2026-08-10 run of all three magnetostatics examples took **204 s** harness-wall
at `-n 2`, of which this example is roughly 75 s of mesh + 27 s of solve.

Useful flags when run directly (`python3 examples/magnetostatics/04_helmholtz_analytic_comparison.py …`):
`--minor-radius` (attacks floor 1), `--air-padding` (floor 2, use ≥ 2R),
`--far-resolution` (default `R/2`, sets the far-field cell size so the large
air box stays affordable), `--output-dir ""` to skip the export.

**Keep `h ≤ a/2` or the wire is not resolved at all** — the `h/a = 1.00` rung
is deliberately at the edge to show what that costs.

## 3. How to analyze it, step by step

**Step 1 — read the sweep as a sweep, not as three runs.** For each rung the
script prints `cells`, `mesh`/`solve` times, the centre field with its relative
error, and the on-axis mean/max error plus the *central CV* (the coefficient of
variation of `B_z` over the central region — how flat the field is, which is
the whole point of a Helmholtz pair). Compare against the table above. What to
look at:

- **Centre rel err staying in the ~0.2–1.3% band and not improving
  monotonically** = the systematic floor, as recorded. Errors an order of
  magnitude larger at every rung = something structural (current density, wire
  cross-section, or the boundary), not the mesh.
- **Max on-axis error falling with `h`** (7.98 → 6.07 → 4.05%) = the
  discretisation part is still converging. If this stops falling too, you have
  hit the truncation floor and only `--air-padding` will move it.
- **Central CV ≤ ~0.1%** = the pair really is in the Helmholtz condition. A CV
  of several percent means the separation is no longer `R`.

**Step 2 — check the analytic reference is fixed.** `analytic=3.531057e-09 T`
must be identical across all three rungs — it depends only on `R`, `a` and the
current, never on the mesh. If it moves between rungs, the geometry is being
rebuilt differently per rung and the comparison is meaningless.

**Step 3 — read the on-axis table at the finest rung.** The run prints
`z`, FEM `B_z`, analytic `B_z`, and the pointwise error over the sampled axis,
and writes the full sweep to `paraview_output/helmholtz_on_axis.csv`. On
record at `h = 0.0025 m` the error runs ~1–2% over the central span, with local
excursions to 4.05% near `z = 0.0084 m`. What to look at: **repeated identical
FEM values at consecutive z** (e.g. `3.481650e-09` at both 0.00120 and 0.00240)
— that is two sample points landing in the same cell, i.e. the axis sampling is
finer than the mesh there. It is expected at these resolutions and it caps how
much of the error is really "pointwise".

**Step 4 — open the fields in ParaView.** `File → Open →
paraview_output/helmholtz_combined.xdmf` (mesh + `CellTags` + `A`, `B`,
`B_analytical` on one grid; `CellTags` 1/2 = the two wire tori, 3 = air).

1. **Threshold** on `CellTags` to 3 to keep only air.
2. **Plot Over Line** along the z axis with `B` — the visual form of step 3;
   the FEM and analytic curves should overlap through the flat central region
   and separate near the coils.
3. **Calculator** `mag(B - B_analytical)`. What to look at: error concentrated
   **at the wire surfaces** (finite-thickness floor) and **at the outer box**
   (truncation floor), with the mid-air region clean. Error filling the central
   volume instead means the solve, not the floors.

Individual files `helmholtz_A.xdmf`, `helmholtz_B.xdmf` and
`helmholtz_B_analytical.xdmf` carry the same mesh if you prefer one field per
reader.

**Step 5 — what a deviation means.** Centre error high at *every* rung and
falling when you raise `--air-padding` → truncation. Falling when you lower
`--minor-radius` → wire thickness. Falling when you lower `h` → ordinary
discretisation, and the sweep above says you are not there any more. Erratic
values that change with rank count → the evaluation path, which is exactly the
defect that killed the deleted example 03.

## Related

- Floor analysis and the 20% truncation history: `docs/validation/helmholtz.md`.
- ParaView workflow: `examples/magnetostatics/PARAVIEW_GUIDE.md`.
- Single-coil version: `examples/magnetostatics/02_circular_loop.md`.
