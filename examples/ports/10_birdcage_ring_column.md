# `ports:10` — the first field on the 32-ring-port birdcage

Script: `examples/ports/10_birdcage_ring_column.py` (`EX-46`)
Gate: `tests/validation/test_port_birdcage_ring_column.py` (`PORT-13` step 1)

## 1. What this demonstrates

`PORT-13` step 1 (2026-09-04) put the first solve on the 16-leg /
32-ring-port high-pass birdcage: the `GEO-26` step 2 rung with
**longitudinal** ring sheets — the sheet orientation the lumped-sheet port
model can actually drive, spanning the gap's chord along its own drive
direction. Every example before this one that solves a coil (`ports:4`
through `ports:9`) is the 4-leg *leg*-gap fixture at 116 085 cells; no
example has solved a 16-leg coil or driven a ring-gap port. This example
re-implements the gate module's own module-scoped fixture body (a pytest
fixture is not callable outside pytest) up to and including the one drive
step 1 gates — port `P17` at 1 V, the other 31 ring ports terminated at
`Z_p = z0 = 50 Ohm` — then writes `|E|` (DG0) over the whole domain, with the
cell tags and the 32 sheet facet tags, into one combined XDMF.

### It asserts, it does not merely render

Every record, band and helper used here is imported from
`tests/validation/test_port_birdcage_ring_column.py` as it stands at
`052bd61` — nothing is restated (the `ANS-1` rule):

- cells = `RING_LONGITUDINAL_SCALED_CELL_RECORD` (270 728) at
  `CELL_COUNT_BAND`;
- the three-way power-accounting residual `|supplied − total|/supplied` <=
  `POWER_BALANCE_BAND` (1e-2, imported from `WF-6` step 1);
- the two ring ports diametrically opposite `P17` (found from the *measured*
  sheet azimuths via `_driven_and_opposite`, never assumed from the
  ordinal) agree to `OPPOSITE_SPREAD_BAND` (5%);
- the supplied power `1/2 Re(V_src I*)` reproduces step 1's own printed
  record, **5.078728668e-03 W**, at rtol 1e-3
  (`20260904T050538Z_PORT-13.log:10751` — not an importable module constant,
  so it is carried here as a literal recomputed from the *same* accounting
  function at the *same* fixture, the `EX-42` precedent for a printed, not
  named, record; the rank count here differs from the gate's `-n 8`, so
  1e-6 is not claimed).

`sheet_terminal_current` and `mean_sar(...)["dissipated_power_w"]` are used
exactly as the gate module uses them — this script re-derives no accounting
term, and the four-drive `S`-matrix construction (`PORT-13` step 2) is not
touched.

### Negative control (free, step 1's own)

Dropping the conductor's `1/2 int sigma|E|^2` term from the power accounting
must push the residual **outside** `POWER_BALANCE_BAND` — step 1 measured
4.14x the band at `-n 8`; that is the printed ceiling, and this run does not
claim to exceed it.

### Scope

One solve, one column, one price — `PORT-13` step 1's own scope, unchanged.
No 32×32, no C16 gate, no tuning, no resonance and no absolute-accuracy
claim.

## 2. How to run it

```
./run_examples.sh -e ports:10 -n 4 -t 600
```

Needs the complex DolfinX build (`source /usr/local/bin/dolfinx-complex-mode`
— the runner sources it automatically for the `ports:` group). Tier:
**heavy by ceiling** (~250 s: ~118 s serial gmsh rung + one solve, scaled
from `PORT-11` step 1's per-cell rate to ≲60 s at `-n 4`, plus the write).

## 3. How to analyze it, step by step

**Step 1 — read the cell count.** `270728` cells against
`RING_LONGITUDINAL_SCALED_CELL_RECORD` (ratio `1.000000`) — the same rung
`mesh:11`/`EX-45` shows without a solve.

**Step 2 — read the 32-vector.** `V = V_src − I·Z_p` (generator convention)
for all 32 ring ports, printed in mesh order, `P17` marked `<-- DRIVEN` and
the two measured-opposite ports marked `<-- OPPOSITE`.

**Step 3 — read gate (i), the power accounting.** Supplied, phantom,
conductor and the 32-sheet total, the residual against `POWER_BALANCE_BAND`,
and the free negative control (conductor term dropped) printed alongside it.

**Step 4 — read the supplied-power reproduction.** The supplied power
against step 1's own printed record at rtol 1e-3 — same fixture, same
accounting, so a miss here is a wiring defect in this example, not physics.

**Step 5 — read gate (ii), the opposite pair.** The two ring ports 180°
from the drive (one per ring), the complex and magnitude-only spreads, and
the `OPPOSITE_SPREAD_BAND` verdict.

**Step 6 — open the mesh in ParaView.** `File → Open →`
`examples/ports/paraview_output/ports_10_birdcage_ring_column_combined.xdmf`.

- Threshold `CellTags`: `1` conductor, `2` air, `3` phantom, `101-116` the
  sixteen uncut leg boxes, `117-148`/`217-248` the inner/outer halves of the
  32 ring-port boxes (split by the longitudinal sheet at `u = R`).
- Or threshold the `mesh_tags` facet array, `227-258`, for the 32
  reconstructed longitudinal sheets themselves (the driven `P17` sheet and
  its z-mirror `P33` are called out in the run's printed output).
- Colour by `E_magnitude` (DG0, V/m) — the honest cell-wise resolution of a
  degree-1 curl element, never interpolated onto a smoother space than the
  discretisation supports (`EX-26`'s convention).

**Step 7 — what a deviation means.** Every anchor is imported from the gate
module, so a miss through this script's path is an example/test
**divergence**, not a new physics finding:

- **A cell-count miss** — a wiring defect in this example's call into
  `_measure_ring`; journal and stop, do not re-record from this side.
- **The power residual outside `POWER_BALANCE_BAND`, or the free control
  landing inside it** — an example/test divergence: known-issues entry,
  stop, never widen the band.
- **The supplied power missing step 1's record at rtol 1e-3** — a wiring
  defect (this example re-implements the fixture body; step 1's own gate
  module is unchanged), not a re-recordable reading.
- **The opposite pair outside `OPPOSITE_SPREAD_BAND`** — an example/test
  divergence: known-issues entry with both voltages printed, stop.

## Related

- The same rung, mesh only, with the two-state terminal triangulation as a
  diagnostic field: `examples/meshing/11_birdcage_sixteen_ring_sheet_longitudinal.md`
  (`EX-45`, `GEO-26` step 3).
- The 4-leg longitudinal sheet, the mechanism's first reading:
  `examples/meshing/10_birdcage_ring_sheet_longitudinal.md` (`EX-44`,
  `GEO-26` step 1).
- The 4-leg leg-gap birdcage's own driven-port SAR/`|B₁⁺|` examples:
  `examples/ports/06_birdcage_b1_plus_map.md` (`EX-38`),
  `examples/ports/09_birdcage_sar_quadrant_powers.md` (`EX-43`).
- The gate itself, and step 2's 4×4 sub-block built on this same fixture:
  `tests/validation/test_port_birdcage_ring_column.py` (`PORT-13` steps 1-2).
- What this column is not yet: `PORT-13` in PROJECT_PLAN.md §7 — no 32×32,
  no C16 class gate, no tuning or resonance claim at any leg count.
