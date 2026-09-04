# `mesh:11` — the 16-leg longitudinal ring-gap rung, in ParaView

Script: `examples/meshing/11_birdcage_sixteen_ring_sheet_longitudinal.py` (`EX-45`)
Gate: `tests/mesh/test_birdcage_ring_sheet_orientation.py` (`GEO-26` steps 2-3, ✅ 2026-09-04)

## 1. What this demonstrates

`GEO-26` step 1 (`mesh:10` / `EX-44`) gated `ring_sheet_orientation="longitudinal"`
on `MeshGenerator.birdcage_port_domain`, at four legs only: the ring-gap sheet
the lumped-sheet port model can actually drive, spanning the gap's chord along
its own drive direction, where the default (transverse) sheet spans zero.
Step 2 re-read the same construction at the production leg count — sixteen
legs, thirty-two ring ports — and hit a pre-registered stop: two of the four
azimuth classes' intra-class terminal-area covariance read 9.990e-05, five
times the 4-leg rung's 2.0e-5. Step 3 (2026-09-04) diagnosed the mechanism
rather than absorbing it: the longitudinal sheet's two `phi` edges are
diameters of the two terminal disks it bounds, and the inscribed
triangulation of a disk whose boundary must contain a diameter is
**bistable** — gmsh settles on one of exactly two discrete areas depending on
how that diameter falls against the surrounding air mesh. Across the 32
terminals, 10 sit on the low area and 22 on the high one. The 2026-09-03
18:00 review ruled the mechanism acceptable for the port model and gave the
16-leg rung its own record band (`LONGITUDINAL_TERMINAL_BAND[16]`, 2.0e-4);
the 4-leg band is unmoved.

No existing example shows the 32 drivable sheets at once, or makes that
two-state census visible. This one does — as a mesh and a diagnostic on the
mesh, not a solve: `mesh:9` (`EX-35`) is the 32-port *transverse* layout, and
`mesh:10` (`EX-44`) is the longitudinal sheet at 4 legs only.

### One mesh, no transverse control

This example calls `_measure_ring(SCALED_LEG_COUNT,
orientation="longitudinal")` exactly once. `mesh:9` already is the transverse
control at 16 legs; building it again here would be a second copy of that
example, not a control for this one. The negative control this example does
carry is free (see below): it needs no second mesh.

### It asserts, it does not merely render

Every anchor here is imported from the gate module(s) and read off *this
run's own mesh* (the `ANS-1` rule):

- the cell count against `RING_LONGITUDINAL_SCALED_CELL_RECORD` (270 728) at
  `CELL_COUNT_BAND`;
- `_assert_ring_identity_family(m, ..., terminal_intra_band=
  LONGITUDINAL_TERMINAL_BAND[16])` — the whole `GEO-20` step-1 family
  (partition, air-box closure, Pappus arcs, terminal ratio band, C32 sheet
  spread and top/bottom mirror) plus the chord/`w`/half-volume identities the
  longitudinal mode adds, green at this rung's own measured band;
- the terminal-area state census: exactly two states, the low one taken by
  10 of the 32 terminals — `GEO-26` step 3's own record;
- the negative control below.

### Scope

**Mesh only.** No port model, no drive, no solve, no `GEO-20` / `GEO-26`
record moves, no §2 change. A cell-count miss, a failed identity-family
assertion, a low-state count off 10, or a third terminal state is a wiring
defect or a fresh generator finding respectively — journaled in the `EX-45`
§7 row, nothing widened.

## 2. How to run it

```
./run_examples.sh -e mesh:11 -n 2 -t 400
```

Real DolfinX build (no complex mode needed); the runner selects it. Tier:
**standard** (~150 s including the 106 s serial gmsh build).

## 3. How to analyze it, step by step

**Step 1 — read the cell count.** The rung reads `270728` cells against
`RING_LONGITUDINAL_SCALED_CELL_RECORD` (ratio `1.000000`) — `GEO-26` step 2's
own record, reproduced identically at `-n 2` and `-n 12`.

**Step 2 — read the four azimuth-class spreads.** Four classes (11.25 /
33.75 / 56.25 / 78.75 deg), eight ports each. Two classes (11.25, 78.75 deg)
read an intra-class terminal-area spread near `9.99e-05`; the other two
(33.75, 56.25 deg) read near `3.8e-11` — the classes whose ports are not
split by the bistable triangulation at all. This asymmetry between classes
is the fingerprint of a two-*state* effect, not a smooth azimuth dependence.

**Step 3 — read the terminal-area state census.** Across all 32 terminals,
exactly two discrete areas appear (clustered at `1.0e-8` relative — four
decades under the states' own `9.99e-05` separation, three above the
`3.8e-11` scatter inside one state). The low state is taken by **10 of the
32** terminals, both rings — the `GEO-26` step 3 record.

**Step 4 — read the C32 sheet spread and mirror.** Both at the unmoved
`SYMMETRY` band: the sheet geometry itself (a polyhedron, exact under a
linear mesh) is untouched by the triangulation effect, which lives entirely
in the *terminal* disk's inscribed mesh.

**Step 5 — read the 32-sheet identity table.** One row per ring port:
`phi_hat/chord` and `z/w` should both read `1.000000000000` (the sheet spans
its box's drive direction and `z`-extent exactly), `V_in/analytic` and
`V_out/analytic` likewise (the sheet cuts the box into the two closed-form
halves), and the terminal area column shows which of the two states that
port's terminal landed on.

**Step 6 — the negative control.** The largest of the four classes'
intra-class terminal spreads is asserted strictly above
`LONGITUDINAL_TERMINAL_INTRA_BAND` (`2.0e-5`, the 4-leg rung's monostable
reading) and strictly below `LONGITUDINAL_TERMINAL_BAND[16]` (`2.0e-4`) — a
5.0x separation, the ceiling `GEO-26` step 3's own measurement allows; no
larger factor is claimed. If this rung's construction were monostable like
the 4-leg one, the spread would fall inside `2.0e-5` and this control would
fail by construction.

**Step 7 — open the mesh in ParaView.** `File → Open →`
`examples/meshing/paraview_output/meshing_11_birdcage_sixteen_ring_sheet_longitudinal_combined.xdmf`,
and
`examples/meshing/paraview_output/meshing_11_birdcage_sixteen_ring_sheet_longitudinal_facets.xdmf`
alongside it.

- Threshold `CellTags` in the `_combined` file: `1` conductor, `2` air, `3`
  phantom, `101-116` the sixteen uncut leg boxes, `117-148` / `217-248` the
  inner/outer halves of the 32 ring gap boxes.
- Or threshold the DG0 field `RingPortTerminalArea` (written on the same
  grid): `> 0` isolates the 32 ring-port boxes directly, and its own value
  is each port's measured terminal area — the two clustered values *are* the
  two triangulation states, visible without cross-referencing the cell tags.
- In the `_facets` file, threshold `mesh_tags` to `227-258` for the 32
  reconstructed longitudinal sheets — radial rectangles in each gap's own
  `u = R` plane, each spanning its gap's full chord through both terminal
  disks' centres.

**Step 8 — what a deviation means.** Nothing is solved here, so every
failure mode is a geometry, tagging, or triangulation-mechanism defect:

- **A cell-count miss** — a wiring defect in this example or its generator
  call, not a new mesh; journal in the `EX-45` §7 row and stop, do not
  re-record from this side.
- **The identity-family assertion failing** at `LONGITUDINAL_TERMINAL_BAND[16]`
  — a regression in the bistable mechanism itself; do not widen the band
  (PROJECT_PLAN §7, MAG table, defect 5).
- **A low-state count off 10, or more than two states in the census** — a
  fresh generator finding (the triangulation resolved a third way), not
  absorbed here; journal and stop.
- **The negative control's spread landing outside (2.0e-5, 2.0e-4)** — either
  the rung has quietly become monostable (falls below) or the separation has
  grown past the measured ceiling (falls above); either is a finding, not a
  band to move.

## Related

- The 4-leg longitudinal rung (the mechanism's first, monostable, reading):
  `examples/meshing/10_birdcage_ring_sheet_longitudinal.md` (`EX-44`,
  `GEO-26` step 1).
- The 16-leg *transverse* layout, 32 ports, four azimuth classes:
  `examples/meshing/09_birdcage_sixteen_ring_gaps.md` (`EX-35`, `GEO-20`
  step 2).
- The gate itself, and the bistable-triangulation ruling in full:
  `tests/mesh/test_birdcage_ring_sheet_orientation.py` (`GEO-26` steps 2-3).
- What the sheet is eventually for: `PORT-13` in PROJECT_PLAN.md §7 — the
  port model has not yet been driven on this rung; no port or solve claim is
  made here at any leg count.
