# `ports:11` — the ring rung's mirror pair in ParaView

Script: `examples/ports/11_birdcage_ring_mirror_pair.py` (`EX-47`)
Gate: `tests/validation/test_port_birdcage_ring_column.py` (`PORT-13` step 2)

## 1. What this demonstrates

`PORT-13` step 2 (2026-09-04) put a second, independently solved drive on
the 16-leg / 32-ring-port longitudinal rung `EX-46` first solved: the
z-mirror port `P33` alongside `P17`. Two independently solved columns of one
network buy an identity that a single drive cannot: the top/bottom mirror
table, a 2×2 `S` sub-block among `{P17, P33}` and its reciprocity, and
per-column passivity read on both drives at once. `ports:10` (`EX-46`)
drives one ring port and writes one field; no example before this one
drives two ports of one coil and puts their fields side by side in one
file, and none prints an `S` sub-block on the ring rung.

This example calls `_build_ring_context` (`PORT-13` step 3, additive,
landed 2026-09-04) — the fixture body `ports:10` reimplemented inline before
that function existed — then drives `_solve_one_drive` twice: `P17` and its
measured z-mirror `P33` (`_ring_mirror_map`), each at 1 V with the other 31
ports terminated at `Z_p = z0 = 50 Ohm`.

### It asserts, it does not merely render

Every record, band and helper used here is imported from
`tests/validation/test_port_birdcage_ring_column.py` — nothing is restated
(the `ANS-1` rule):

- cells = `RING_LONGITUDINAL_SCALED_CELL_RECORD` (270 728) at
  `CELL_COUNT_BAND`;
- the 2×2 sub-block `{P17, P33}`'s `_reciprocity_ratio` (imported) <=
  `RECIPROCITY_BAND` (1e-3);
- the worst of the 32 measured top/bottom mirror pairs <=
  `OPPOSITE_SPREAD_BAND` (5%);
- each column's `Σ_i|S_ij|²` <= `COLUMN_PASSIVITY_CEILING` (1) and its
  power-accounting residual <= `POWER_BALANCE_BAND` (1e-2);
- the `P17` column's `Σ|S_ij|²` reproduces step 2's own printed record,
  **0.915817419** (`20260904T093638Z_PORT-13.log:10797`), at rtol 1e-3 —
  this run is at `-n 4` against the gate's `-n 8` (the `EX-46` precedent
  for a cross-rank-count reproduction, not exact).

### Negative control

The `P17` column of the 2×2 sub-block scaled by the imported
`CONTROL_COLUMN_SCALE` (1.01, the `PORT-9` leg (d2) per-column-normalisation
defect class) must move the reciprocity ratio to at least
`CONTROL_MARGIN_FACTOR` (5×) times `RECIPROCITY_BAND` — the gate module's
own in-run control on this exact identity, reused verbatim.

### Scope

Two columns, one file, one identity table — no band, no gate change, no
32×32 and no `src/` change. `PORT-13` step 3's full 32×32 (reciprocity /
passivity / C16-symmetry across all 32 drives) lives in
`tests/validation/test_port_birdcage_ring_matrix.py` and is not touched
here.

## 2. How to run it

```
./run_examples.sh -e ports:11 -n 4 -t 600
```

Needs the complex DolfinX build (`source /usr/local/bin/dolfinx-complex-mode`
— the runner sources it automatically for the `ports:` group). Tier:
**standard by ceiling** (host-runner window <= 600 s; sized off `EX-46`'s
mesh 68.96 s + rung 75.62 s + one solve 13.12 s at `-n 4`
(`20260904T140525Z_EX-46.log:10561`) — two solves and a two-field write,
estimated ≈ 200 s, budgeted to ≈ 300 s).

## 3. How to analyze it, step by step

**Step 1 — read the cell count.** `270728` cells against
`RING_LONGITUDINAL_SCALED_CELL_RECORD` (ratio `1.000000`) — the same rung
`ports:10`/`EX-46` reports.

**Step 2 — read the two solve prices.** `P17` and `P33`'s individual wall
times and their total, at `-n 4`, against `SOLVE_PRICE_STOP_RULE_S`.

**Step 3 — read gate (i), power accounting on both columns.** Supplied,
phantom, conductor and the 32-sheet total per column, each residual against
`POWER_BALANCE_BAND`.

**Step 4 — read gate (iv), column passivity.** `Σ_i|S_ij|²` for `P17` and
`P33`, each against the `COLUMN_PASSIVITY_CEILING` of 1.

**Step 5 — read the `P17` passivity-sum reproduction.** Against step 2's own
printed record at rtol 1e-3 — same fixture, same accounting, so a miss here
is a wiring defect in this example, not physics.

**Step 6 — read gate (iii), the 2×2 sub-block and its reciprocity.** The
printed 2×2 matrix, the reciprocity ratio against `RECIPROCITY_BAND`, and
the free negative control (the `P17` column scaled by 1%) alongside it.

**Step 7 — read gate (v), the top/bottom mirror identity.** The worst of
the 32 measured mirror pairs `|S_Pi,P17|` vs `|S_P(sigma(i)),P33|`, against
`OPPOSITE_SPREAD_BAND`.

**Step 8 — open the mesh in ParaView.** `File → Open →`
`examples/ports/paraview_output/ports_11_birdcage_ring_mirror_pair_combined.xdmf`.

- Threshold `CellTags`: `1` conductor, `2` air, `3` phantom, `101-116` the
  sixteen uncut leg boxes, `117-148`/`217-248` the inner/outer halves of the
  32 ring-port boxes.
- Or threshold the `mesh_tags` facet array for the 32 reconstructed
  longitudinal sheets themselves.
- Colour by `E_magnitude_P17` and, separately, `E_magnitude_P33` (both
  DG0, V/m, distinct `name`s — a shared name would leave ParaView showing
  only one of the two, `EX-46`'s trap). Apply the *Reflect* filter on `z` to
  one of the two arrays and it overlays the driven port's field onto its
  z-mirror's.

**Step 9 — what a deviation means.** Every anchor is imported from the gate
module, so a miss through this script's path is an example/test
**divergence**, not a new physics finding:

- **A cell-count miss** — a wiring defect in this example's call into
  `_build_ring_context`; journal and stop, do not re-record from this side.
- **A power residual outside `POWER_BALANCE_BAND` on either column** — an
  example/test divergence: known-issues entry, stop, never widen the band.
- **A column passivity sum above 1, or the `P17` sum missing step 2's
  record at rtol 1e-3** — a port-normalisation or wiring defect: known-issues
  entry with both readings printed, stop.
- **The 2×2 sub-block not reciprocal at `RECIPROCITY_BAND`, or the
  negative control landing under `CONTROL_MARGIN_FACTOR`× the band** — an
  example/test divergence: known-issues entry, stop, never widen the band.
- **The worst mirror pair outside `OPPOSITE_SPREAD_BAND`** — an
  example/test divergence: known-issues entry with the pair table printed,
  stop.

## Related

- The first field on this rung, one drive: `examples/ports/10_birdcage_ring_column.md`
  (`EX-46`, `PORT-13` step 1).
- The gate itself, the four-column 4×4 sub-block built on the same fixture,
  and the additive `_build_ring_context`:
  `tests/validation/test_port_birdcage_ring_column.py` (`PORT-13` steps 1-3).
- The full 32×32 on this rung: `tests/validation/test_port_birdcage_ring_matrix.py`
  (`PORT-13` step 3).
- The 4-leg leg-gap birdcage's own driven-port SAR/`|B₁⁺|` examples:
  `examples/ports/06_birdcage_b1_plus_map.md` (`EX-38`),
  `examples/ports/09_birdcage_sar_quadrant_powers.md` (`EX-43`).
- What this rung is not yet: `PORT-13` in PROJECT_PLAN.md §7 — no tuning or
  resonance claim at any leg count, no absolute-accuracy claim.
