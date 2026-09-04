# `mesh:10` — the longitudinal ring-gap port sheet, in ParaView

Script: `examples/meshing/10_birdcage_ring_sheet_longitudinal.py` (`EX-44`)
Gate: `tests/mesh/test_birdcage_ring_sheet_orientation.py` (`GEO-26` step 1, ✅ 2026-09-03)

## 1. What this demonstrates

`GEO-26` step 1 gated a new keyword on `MeshGenerator.birdcage_port_domain`:
`ring_sheet_orientation="longitudinal"`. Every ring-gap example that existed
before it — `mesh:7` (`EX-31`) and `mesh:9` (`EX-35`) — shows only the
*default* **transverse** section of a ring gap: the `w × w` rectangle at
`phi = phi_c`, normal `phi_hat`, whose extent along its own drive direction is
**zero** to machine precision. `PORT-13` step 1 measured that directly
(`≤ 1.43e-17` m on all eight sheets) and found it un-terminable: the
lumped-sheet port model divides by that extent (`R_s = Z_p·w/h`), so `h = 0`
is a well-posedness gap, not a solver bug. No example showed the sheet the
port model can actually drive. This one does.

The **longitudinal** sheet is a different planar rectangle: it lies in the
plane `u = ring_radius` (normal `û(phi_c)`), spans the gap's **chord**
`2R·tan(alpha)` along `phi_hat` and `w = ring_port_box_width_m` along `ẑ`. Its
four edges lie on the port box's two radial caps and its two `z` faces, so it
spans the box and splits it into an inner (`u < R`, cell tag `100+i`) and
outer (`u > R`, `200+i`) half with closed-form volumes
`w·tan(alpha)·(R·w ∓ w²/4)`.

### Chord, not arc

The box's radial caps are planar, so what they actually deliver is the
**chord**, not the arc `ring_gap_length` a gap is specified by. At this
fixture's `g = 0.008 m` / `R = 0.07 m` the two differ by **+0.10%**
(`8.008718871e-03` m chord vs `8.000000000e-03` m arc) — both diagnostics are
emitted by the generator and both are printed here.

### One measured difference, not absorbed

The longitudinal sheet's two `phi` edges are **diameters** of the two
terminal disks (the transverse sheet sits mid-gap and touches neither), so
the inscribed triangulation of a terminal is constrained differently. Every
terminal still lands inside the `[0.95, 1.0]` closed-form band and every
*exact* (polyhedral) identity — sheet area, port volume, both halves, the C4
spread — is untouched, but the terminal C4 covariance moves from `4.198e-08`
(transverse) to `1.605e-05` (longitudinal). `TERMINAL_INTRA_CLASS_BAND`
(`1e-6`) is not widened for this; `_assert_ring_identity_family` takes a
`terminal_intra_band` keyword and only this call site passes the measured
`LONGITUDINAL_TERMINAL_INTRA_BAND = 2.0e-5`.

### It asserts, it does not merely render

Every anchor here is imported from the gate module and read off *this run's
own mesh* (the `ANS-1` rule):

- both meshes' cell counts against their own record (`RING_LONGITUDINAL_CELL_RECORD`
  111 898, `RING_GAP_CELL_RECORD` 110 786, both at `CELL_COUNT_BAND`);
- `_assert_ring_identity_family` — the whole `GEO-20` step 1 family (partition,
  air-box closure, Pappus arcs, terminal ratio band, C4 sheet spread and
  top/bottom mirror) plus the chord/`w`/half-volume identities the
  longitudinal mode adds — green on the subject at its own measured band and
  on the control at the function's default band;
- the negative control below.

### Scope

**Mesh only.** No port model, no drive, no solve, no `GEO-20` record moves, no
§2 change. **Only the 4-leg rung is shown** — the 16-leg longitudinal rung
(`GEO-26` step 2) hit a pre-registered stop (two of its four azimuth classes'
terminal covariance exceeds the unmoved `2.0e-5` band) and is a deliberate red
on `main` with its own known-issues entry; nothing about it is claimed or
built here.

## 2. How to run it

```
./run_examples.sh -e mesh:10 -n 2 -t 300
```

Real DolfinX build (no complex mode needed); the runner selects it. Tier:
**standard**.

## 3. How to analyze it, step by step

**Step 1 — read the two cell counts.** The longitudinal mesh reads
`111898` cells against `RING_LONGITUDINAL_CELL_RECORD` (ratio `1.000000`);
the transverse control reads `110786` against `RING_GAP_CELL_RECORD` (ratio
`1.000000`). Different sheets are a different `dim-2` fragment tool for
gmsh, so the counts genuinely differ — this is not the same mesh printed
twice.

**Step 2 — read the chord vs. the arc.** `chord/arc = 1.001089871`: the
longitudinal sheet's radial caps are planar, so the sheet is 0.10% wider than
the nominal gap length. This is the mechanism, not a discretisation error —
both numbers are closed forms.

**Step 3 — read the per-port table.** Eight rows, one per ring port (both end
rings, four gaps each):

- `longitudinal phi_hat/chord` — should read `1.000000000000` on all four:
  the sheet spans the full chord along the drive direction, to `1e-9`.
- `z/w` — should also read `1.000000000000`: the sheet spans its box in `ẑ`.
- `V_in/analytic` and `V_out/analytic` — both `1.000000000000`: the sheet
  really does cut the box into the two closed-form halves that sum to
  `ring_port_volume_m3`.
- `transverse phi_hat extent` — the same port's *default* sheet, printed
  beside it: `~1e-17` m, fourteen decades below the longitudinal chord.

**Step 4 — the identity family.** `_assert_ring_identity_family` re-reads,
on both meshes, the `GEO-9` tagged-volume partition, the analytic air box,
the Pappus arcs on the ring primitives, the graded-conductor CAD-mass gate,
the per-port boundary closure and wedge volume, the terminal ratio band, and
the C4 sheet spread / top-bottom mirror. On the longitudinal mesh the
terminal covariance is read against `LONGITUDINAL_TERMINAL_INTRA_BAND`
(`2.0e-5`, the measured constrained-triangulation effect); on the transverse
control it is read against the function's own default (`1e-6`).

**Step 5 — the negative control.** Every transverse sheet's `phi_hat`
extent must sit below `DEGENERATE_EXTENT_M` (`1e-12` m) while every
longitudinal sheet's ratio to the closed-form chord is `1.000000000` and the
longitudinal/transverse extent ratio exceeds `1e13`. If this ever failed, the
opt-in would have leaked into the default emission, or the longitudinal sheet
would not actually span the drive direction.

**Step 6 — open the mesh in ParaView.** `File → Open →`
`examples/meshing/paraview_output/meshing_10_birdcage_ring_sheet_longitudinal_combined.xdmf`,
and `meshing_10_birdcage_ring_sheet_longitudinal_facets.xdmf` alongside it.

- Threshold `CellTags` in the `_combined` file: `1` conductor, `2` air, `3`
  phantom, `101-104` the four uncut leg boxes, `105-112` / `205-212` the
  inner/outer halves of the eight ring gap boxes (both end rings, four gaps
  each).
- Threshold `105` and `205` separately (one ring port): the flat radial
  interface between them, at `u = ring_radius`, *is* that port's longitudinal
  sheet.
- In the `_facets` file, threshold `mesh_tags` to `215-222`. Those are the
  eight sheets themselves — planar rectangles lying in the `u = R` plane, each
  running the gap's full chord along `phi_hat` and through both terminal
  disks' centres along `ẑ`, unlike the mid-gap transverse sheets `mesh:7` /
  `mesh:9` show.

**Step 7 — what a deviation means.** Nothing is solved here, so every failure
mode is a geometry or tagging defect:

- **A cell-count miss** — a wiring defect in this example, not the mesh
  (`GEO-26` step 1 already gates the generator); journal in the `EX-44` §7 row
  and stop, do not re-record from this side.
- **A `phi_hat`/chord ratio off `1e-9`** — the longitudinal sheet does not
  span the gap, so the `h` it would offer a port model is not the chord.
- **A transverse `phi_hat` extent above `1e-12` m** — the opt-in leaked into
  the default emission.
- **A terminal-band miss above `2.0e-5`** on the 4-leg rung — a genuine
  regression in the constrained-diameter triangulation; do not widen the band
  (PROJECT_PLAN §7, MAG table, defect 5).

## Related

- The gate itself: `tests/mesh/test_birdcage_ring_sheet_orientation.py`
  (`GEO-26` steps 1–2).
- The default (transverse) sheet at four legs:
  `examples/meshing/07_birdcage_ring_gap_ports.md` (`EX-31`, `GEO-20` step 1).
- The default sheet at sixteen legs, 32 ring ports:
  `examples/meshing/09_birdcage_sixteen_ring_gaps.md` (`EX-35`, `GEO-20`
  step 2) — the longitudinal analogue at that leg count is `GEO-26` step 2's
  own unresolved red and is not shown anywhere yet.
- What the sheet is eventually for: `PORT-13` in PROJECT_PLAN.md §7 — blocked
  until a review adjudicates the 16-leg terminal-triangulation finding; no
  port or solve claim is made here at any leg count.
