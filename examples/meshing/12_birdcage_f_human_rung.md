# `mesh:12` — the F-human birdcage: 16 legs, 32 ring ports, at 0.15 m, in ParaView

Script: `examples/meshing/12_birdcage_f_human_rung.py` (`EX-51`)
Gate: `tests/validation/test_birdcage_f_human_rung.py` (`GEO-25` step 2)

## 1. What this demonstrates

`GEO-25` step 1 (2026-09-04) *measured* the `ring_radius` 0.07 -> 0.15 m
ladder on `birdcage_port_domain` and asserted nothing, so the chunk was
demoted ✅ -> 🧪. `GEO-25` step 2 turned the ladder's top rung — a 30 cm-coil,
16-leg, high-pass (both-end-ring) layout, the operator's 2026-08-25
directive — into an executed gate. This example is that rung in ParaView.

Two branches come from the gate module's own `_params(F_HUMAN_RING_RADIUS,
scale_sizing=...)`, the single source of the parameter set:

* **branch B** (`scale_sizing=False`): the global `resolution` is held at
  `mesh:9`'s 0.015 m — fixed absolute element sizing — while only the
  geometry grows. This is the **fixture**.
* **branch A** (`scale_sizing=True`): `resolution` scales with the radius
  too, so every rung in the ladder is a geometrically *similar* mesh. This
  is the **negative control**.

### It asserts, it does not merely render

Every anchor is imported from the gate module and read off *this run's own
mesh* (the `ANS-1` rule) — nothing here is restated:

- branch-B cell count against `F_HUMAN_BRANCH_B_CELL_RECORD` (504 642) at
  `CELL_COUNT_BAND`;
- the `GEO-18` volume-partition identity (tagged volumes sum to the air box)
  at `EXACT`;
- the `GEO-19` closed-form terminal-area ratio, on all 32 ring ports, inside
  `TERMINAL_RATIO_BAND`;
- the meshed/CAD conductor-mass recovery, at least `CAD_MASS_GATE` (record
  0.965414);
- the negative control below.

### Why branch A fails and branch B doesn't

At 0.15 m the conductor's 1.6 mm graded region is pinned by
`conductor_resolution` regardless of branch, but the *global* element size
around it is not: branch A's `resolution` grew 2.14x with the radius, and
that coarser surrounding mesh swamps the graded region until the meshed
conductor loses mass and its CAD-mass ratio (0.893028, `GEO-25` step 1)
drops under `CAD_MASS_GATE`. Branch B holds `resolution` at `mesh:9`'s value,
so the graded region keeps the same relative resolution as at the base rung,
and its ratio (0.965414) clears the gate. The finding this example makes
durable: **fixed absolute sizing, not similar-mesh scaling, is the right
choice for this generator at human scale.**

### Scope

**Mesh only.** No field, no port model, no drive, no solve, no resonance
claim, and no Phase 6 cost claim at any leg count or radius — `GEO-25` step
2's own bands are unmoved by this example.

## 2. How to run it

```
./run_examples.sh -e mesh:12 -n 2 -t 600
```

Real DolfinX build (no complex mode needed); the runner selects it. Tier:
**standard by the host-runner window** (<=600 s ceiling; the gate module's
own two builds measured 109 + 63 s at `-n 2`
(`20260905T183654Z_GEO-25.log:9728,20019`), so ~200 s plus a ~15 s write is
expected).

## 3. How to analyze it, step by step

**Step 1 — read the branch-B cell count.** The fixture reads its cells
against `F_HUMAN_BRANCH_B_CELL_RECORD` (504 642) at `CELL_COUNT_BAND` — a
version-tagged record on the 0.11 image (dolfinx 0.11 / gmsh 4.15.2).

**Step 2 — read the `GEO-18` volume partition.** The tagged volumes
(conductor, air, phantom, every port solid) sum to the mesh's total volume
to `EXACT` — a deficit would mean a fragment carries no physical group, an
excess that a region is meshed twice.

**Step 3 — read the `GEO-19` terminal ratios.** All 32 ring-port terminal
areas, meshed over analytic, land inside `TERMINAL_RATIO_BAND` (`[0.95,
1.0]`) — a meshed terminal disk is inscribed in the analytic one, so the
ratio never exceeds 1.

**Step 4 — read the meshed/CAD conductor-mass recovery.** Branch B reads
0.965414 (`GEO-25` step 1's own printed value), clearing `CAD_MASS_GATE`
(0.95).

**Step 5 — read the negative control.** Branch A reads 0.893028, *below*
the same gate — `CAD_MASS_GATE - control["cad_ratio"] = 0.056972` under it,
while branch B sits `fixture["cad_ratio"] - CAD_MASS_GATE = 0.015414` over
it. The example asserts the two-sided separation
`control["cad_ratio"] < CAD_MASS_GATE <= fixture["cad_ratio"]`, backed by
the gate module's own measurement of the same comparison on the same rungs
(`20260905T183654Z_GEO-25.log:20024-20027`). The printed separation between
the two branches is `fixture["cad_ratio"] - control["cad_ratio"] =
0.072387`.

**Step 6 — open the mesh in ParaView.** `File -> Open ->`
`examples/meshing/paraview_output/meshing_12_birdcage_f_human_rung_combined.xdmf`
— one file, branch B (the fixture) only; the branch-A control mesh is not
written to disk, only its numbers (this guide and the run's own log output).

- Threshold `CellTags`: `1` conductor, `2` air, `3` phantom, `101-116` the
  sixteen uncut leg boxes, `117-148` / `217-248` the lower/upper halves of
  the 32 ring gap boxes.
- Or threshold / color by the DG0 `cell_diameter` field (written on the same
  grid, a distinct array from `CellTags`) for a per-cell mesh-size picture —
  it is largest in the air far-field and smallest across the graded
  conductor region.
- In the same file's facet block, threshold `mesh_tags` to `227-258` for the
  32 reconstructed ring sheets.

**Step 7 — what a deviation means.** Nothing is solved here, so every
failure mode is a geometry, tagging, or scaling-mechanism defect:

- **A branch-B cell-count miss** while the gate module (re-run) still holds
  the record — an example/test divergence, not a new mesh: journal in the
  `EX-51` §7 row and stop, do not re-record from this side.
- **The `GEO-18` or `GEO-19` identity failing** — a regression in the
  generator's tagging, not a band to move (PROJECT_PLAN §7, MAG table,
  defect 5).
- **The negative control's separation collapsing** (branch A clearing the
  gate, or branch B falling below it) — either the argument for fixed
  absolute sizing at human scale is gone, or the fixture itself has
  regressed; either is a finding, not a band to move.

## Related

- The gate itself: `tests/validation/test_birdcage_f_human_rung.py`
  (`GEO-25` step 2).
- `GEO-25` step 1's own unadjudicated ladder measurement (demoted ✅ -> 🧪 on
  the §3 rule): PROJECT_PLAN.md §7, `GEO-25` row.
- The 16-leg, base-radius (0.07 m), 32-ring-port layout this rung scales
  from: `examples/meshing/09_birdcage_sixteen_ring_gaps.md` (`EX-35`,
  `GEO-20` step 2).
- The conductor-mass gate this rung's branch-B fixture clears and branch-A
  control fails: `tests/mesh/test_birdcage_conductor_sizing.py`
  (`GEO-15`/`GEO-21`).
