# `ports:12` — the ring rung's quarter turn in ParaView

Script: `examples/ports/12_birdcage_ring_quarter_turn.py` (`EX-48`)
Gate: `tests/validation/test_port_birdcage_ring_column.py`,
`tests/validation/test_port_birdcage_ring_matrix.py` (`PORT-13` step 3)

## 1. What this demonstrates

`PORT-13` step 3 (2026-09-04) gated the full 32×32 on the 16-leg /
32-ring-port longitudinal rung: an 18-class `C16 × mirror` identity built
from every pair of the 32 measured azimuths. That gate needs all 32
columns; `ports:11` (`EX-47`) already shows the cheap two-column slice for
the *mirror* (z-flip) symmetry. No example before this one shows a
**rotation** pair — two independently solved columns 4 steps (90°) apart on
the same ring — or the C16 class identity that a rotation, rather than a
mirror, tests.

This example calls `_build_ring_context` (`PORT-13` step 3, additive) then
drives `_solve_one_drive` twice: `P17` and the ring port whose *measured*
azimuth sits 4 × 22.5° from it, found by azimuth search and never assumed
from the ordinal (this fixture's numbering happens to land it on `P21`, but
the script never reads the number 21).

### It asserts, it does not merely render

Every record, band and helper used here is imported from
`tests/validation/test_port_birdcage_ring_column.py` (the context, the two
solves) and `tests/validation/test_port_birdcage_ring_matrix.py`
(`AZIMUTH_STEP_DEG`) — nothing is restated (the `ANS-1` rule):

- cells = `RING_LONGITUDINAL_SCALED_CELL_RECORD` (270 728) at
  `CELL_COUNT_BAND`;
- both columns' power-accounting residual <= `POWER_BALANCE_BAND` (1e-2);
- both columns' `Σ_i|S_ij|²` <= `COLUMN_PASSIVITY_CEILING` (1);
- the `P17` column's `Σ|S_ij|²` reproduces step 2's own printed record,
  **0.915817419** (`20260904T093638Z_PORT-13.log:10797`), at rtol 1e-3
  (this run is at `-n 4` against the gate's `-n 8`, the `EX-46`/`EX-47`
  precedent for a cross-rank-count reproduction, not exact);
- **the C16 column identity** — for every ring port `i`, `|S_{i,P21}|` vs
  `|S_{ρ⁻⁴(i),P17}|`, with `ρ` the 4-step (90°) rotation on measured
  azimuths **within each ring** (top rotates onto top, bottom onto bottom —
  the physical rotation of the whole coil about `z`), worst relative
  mismatch <= `OPPOSITE_SPREAD_BAND` (5%; step 3 measured every 18-class
  mean <= 0.4426%, `20260904T171419Z_PORT-13.log:93-111`).

`ρ⁻⁴(i)` for every port is found the same way `_driven_and_opposite`/
`_ring_mirror_map` find their partners in the gate module — by measured
azimuth, to `AZIMUTH_MATCH_DEG` — never ordinal arithmetic; a port with no
partner at that separation is an assertion failure, never a silent drop.

### Negative control, ceiling first

The same per-port comparison with a **3-step** (67.5°) rotation instead of
4 pairs each port against a partner one class off from the true separation.
Step 3's class means put a same-ring pair at 4.307e-2 vs 7.418e-2 (a 72%
mismatch) and an other-ring pair at 0.8948 vs 4.995e-2 (94%)
(`20260904T171419Z_PORT-13.log:93-111`) — the wrong rotation is expected to
miss by roughly 14× the band. Asserted only to `CONTROL_MARGIN_FACTOR` (5×)
the band; the measured factor is printed, none larger claimed than what
this run computes.

### One ungated reading, printed only

`|E|` sampled through `post.evaluation.evaluate_vector_field_parallel` on a
64-point ring (r = 0.02 m, z = 0) inside the phantom, for both drives; the
`P21` samples compared against the `P17` samples rotated by 90° (a
16-sample index shift on the 64-point ring). No band exists for this: at
CG1 on this mesh a rotated discrete field is not exactly the discrete
rotated field (`WF-6` step 1's C4 field identities read ~2% on the 4-leg
mesh for the same reason) — printed for inspection only, never asserted.

### Scope

Two columns, one field-level reading, one file — no band, no gate change,
no 32×32 and no `src/` change. `PORT-13` step 3's full 32×32 (reciprocity /
passivity / C16-symmetry across all 32 drives) lives in
`tests/validation/test_port_birdcage_ring_matrix.py` and is not touched
here.

## 2. How to run it

```
./run_examples.sh -e ports:12 -n 4 -t 600
```

Needs the complex DolfinX build (`source /usr/local/bin/dolfinx-complex-mode`
— the runner sources it automatically for the `ports:` group). Tier:
**standard by ceiling** (host-runner window <= 600 s; sized off `EX-47`'s
mesh 69.26 s + rung 75.89 s + two solves 13.20 + 12.98 s at `-n 4`
(`20260904T183520Z_EX-47.log:10561-10563`) — two solves, one 64-point
evaluation and a two-array write, estimated ≈ 200 s).

## 3. How to analyze it, step by step

**Step 1 — read the cell count.** `270728` cells against
`RING_LONGITUDINAL_SCALED_CELL_RECORD` (ratio `1.000000`) — the same rung
`ports:10`/`ports:11` report.

**Step 2 — read which port was located as `P17`'s quarter-turn partner.**
The `[located]` line names the port found by measured-azimuth search — on
this fixture, `P21`.

**Step 3 — read the two solve prices.** `P17` and the located port's
individual wall times and their total, at `-n 4`, against
`SOLVE_PRICE_STOP_RULE_S`.

**Step 4 — read gate (i), power accounting on both columns.** Supplied,
phantom, conductor and the 32-sheet total per column, each residual against
`POWER_BALANCE_BAND`.

**Step 5 — read gate (iv), column passivity.** `Σ_i|S_ij|²` for both
columns, each against the `COLUMN_PASSIVITY_CEILING` of 1.

**Step 6 — read the `P17` passivity-sum reproduction.** Against step 2's own
printed record at rtol 1e-3 — same fixture, same accounting, so a miss here
is a wiring defect in this example, not physics.

**Step 7 — read the C16 column identity gate.** The worst of the 32 ring
ports' `|S_i,P21|` vs `|S_ρ⁻⁴(i),P17|` mismatch, against
`OPPOSITE_SPREAD_BAND`.

**Step 8 — read the 3-step wrong-rotation control.** The worst mismatch
under the wrong rotation and its multiple of the band, against
`CONTROL_MARGIN_FACTOR`.

**Step 9 — read the ungated field-level reading.** The 64-point ring's RMS
and worst relative difference between `P21`'s samples and `P17`'s samples
rotated 90° — no band, printed only.

**Step 10 — open the mesh in ParaView.** `File → Open →`
`examples/ports/paraview_output/ports_12_birdcage_ring_quarter_turn_combined.xdmf`.

- Threshold `CellTags`: `1` conductor, `2` air, `3` phantom, `101-116` the
  sixteen uncut leg boxes, `117-148`/`217-248` the inner/outer halves of the
  32 ring-port boxes.
- Or threshold the `mesh_tags` facet array for the 32 reconstructed
  longitudinal sheets themselves.
- Colour by `E_magnitude_P17` and, separately, `E_magnitude_P21` (both DG0,
  V/m, distinct `name`s — a shared name would leave ParaView showing only
  one of the two, `EX-46`'s trap). Apply ParaView's *Transform* filter,
  rotate 90° about `z`, to one of the two arrays and it overlays onto the
  other.

**Step 11 — what a deviation means.** Every anchor is imported from the
gate modules, so a miss through this script's path is an example/test
**divergence**, not a new physics finding:

- **A cell-count miss** — a wiring defect in this example's call into
  `_build_ring_context`; journal and stop, do not re-record from this side.
- **A power residual outside `POWER_BALANCE_BAND` on either column** — an
  example/test divergence: known-issues entry, stop, never widen the band.
- **A column passivity sum above 1, or the `P17` sum missing step 2's
  record at rtol 1e-3** — a port-normalisation or wiring defect: known-issues
  entry with both readings printed, stop.
- **The C16 column identity outside `OPPOSITE_SPREAD_BAND`, or the
  negative control landing under `CONTROL_MARGIN_FACTOR`× the band** — an
  example/test divergence: known-issues entry, stop, never widen the band.

## Related

- The mirror (z-flip) pair on this rung: `examples/ports/11_birdcage_ring_mirror_pair.md`
  (`EX-47`, `PORT-13` step 2).
- The first field on this rung, one drive: `examples/ports/10_birdcage_ring_column.md`
  (`EX-46`, `PORT-13` step 1).
- The gate itself and the additive `_build_ring_context`:
  `tests/validation/test_port_birdcage_ring_column.py` (`PORT-13` steps 1-3).
- The full 32×32 and the 18-class `C16 × mirror` identity on this rung:
  `tests/validation/test_port_birdcage_ring_matrix.py` (`PORT-13` step 3).
- The 4-leg leg-gap birdcage's own driven-port SAR/`|B₁⁺|` examples:
  `examples/ports/06_birdcage_b1_plus_map.md` (`EX-38`),
  `examples/ports/09_birdcage_sar_quadrant_powers.md` (`EX-43`).
- What this rung is not yet: `PORT-13` in PROJECT_PLAN.md §7 — no tuning or
  resonance claim at any leg count, no absolute-accuracy claim.
