# `mesh:7` — the high-pass birdcage: ring-gap ports and the 12-port dual family

Guide for `examples/meshing/07_birdcage_ring_gap_ports.py` (`EX-31`), the example
angle `GEO-20` step 1 owes.

## 1. What this demonstrates

`EX-28` (`mesh:6`) cuts the **legs** — the low-pass drive element — and its
terminals are the axis-aligned stub faces of a cylinder. This example is the
other coil topology: the **end rings** cut instead, at the mid-azimuth between
each adjacent leg pair, on both rings. A 4-leg fixture therefore carries
`2·4 = 8` ring ports (32 at the 16-leg production count — item (b) of the §10
32-port directive), and switching both families on at once gives the repo's
first **12-port dual-family mesh**.

### Why the cut is radial, and why that is the whole point

The leg-gap module named the end-ring alternative and rejected it: an
*axis-aligned* box cutting a torus gives oblique sections at 45° and no closed
form at all. That is not the construction here. The gap is cut by the two
**radial half-planes** `phi = phi_c ± alpha`, `alpha = g/(2·R)` — the planes
every partial-torus arc already ends on — so each cut face is an exact planar
disk of area `pi·r_ring²`. The closed form exists *because* the cut is radial.

The port solid spanning the gap is then the `GEO-18` box **rotated into the
gap's own frame**: the wedge `|phi − phi_c| <= alpha` intersected with
`|z − z_ring| <= w/2` and `|u − R| <= w/2`, where `u = rho·cos(phi − phi_c)`.
All six of its faces are planar, so

- volume `2·R·w²·tan(alpha)`,
- surface `2·w²/cos(alpha) + 8·R·w·tan(alpha)`,
- mid-plane section `w²` (the sheet),

are **exact** under a linear mesh. A constant-`rho` face would have turned all
three into faceting bands instead of identities.

### The quantities, and which one is banded

Gated at `1e-9` as identities: port volume / analytic wedge, sheet area / `w²`,
the boundary closure (conductor + air + phantom facing areas over the analytic
wedge surface — what says the terminal reading is the whole terminal and not a
fragment), and the `GEO-9` box partition. Gated at `1e-12`: the C4 spread and
the top/bottom ring mirror on those exact forms, and the sheet's out-of-plane
spread.

The **terminal** is the one banded quantity, and deliberately so: the meshed
disk is an *inscribed* triangulation of the ring's circular cut face, so its
ratio to `2·pi·r_ring²` must land at or below 1. It is asserted inside the
imported `[0.95, 1.0]` inscribed band, against step 1's record **0.974455** to
`1e-5`, and equal across the 8 ports to `1e-5` — the circulant premise any
future port assembly would need.

### The planarity check that could not be reused

A ring sheet's plane is *radial*, so its normal is azimuthal and **no global
coordinate is constant on it**. The `GEO-18` / two-torus planarity check —
smallest bounding-box extent is zero — reads a diagonal rectangle's projected
extents instead and would fail a perfectly flat sheet: P5's extents are
`(7.071068e-03, 7.071068e-03, 1.000000e-02)`, exactly the `w = 1e-2` rectangle
seen edge-on at 45°. The script therefore measures `max |(p − p_c)·n̂_phi|` along
the sheet's own azimuthal normal, taking `n̂_phi` and the gap centre from the
port ordinal alone.

### The negative control is inverted, and measured rather than implied

`ring_gap_length=None` must reproduce the uncut birdcage's cell-count record and
`EX-21`'s meshed/CAD ratio, and must **lack** everything above: no ring port
cell tag at all, and — measured, not implied — `_global_facet_count` **= 0** on
every ring sheet group after running the *same* `_interface_facet_tags` rebuild
on that mesh. That is `EX-28`'s clause, applied to the ring family.

Every constant is **imported** from `tests/mesh/test_birdcage_ring_gaps.py` and
the modules it imports in turn (the `ANS-1` rule); nothing is restated, so this
example cannot drift from the gate it demonstrates.

**Mesh only — no port model, no drive, no solve, no impedance or resonance
claim.** A gapped birdcage without lumped elements cannot resonate; a high-pass
*layout* is not a high-pass *circuit*. `PORT-9` is 🟡 (PROJECT_PLAN.md §2) and
nothing here is a port claim.

## 2. How to run it

```
./run_examples.sh -e mesh:7 -n 2 -t 400
```

Real DolfinX build (no complex mode needed); the runner selects it. Tier:
**standard**. On record at `-n 2`: ring-gapped rung **110 786 cells, ~20.9 s
mesh**, leg+ring rung **128 402 cells, ~24.9 s**, uncut control **98 666 cells**
— see `docs/testing/attempts.md` for this example's own measured wall clock and
log name.

Exit status 0 means every identity *and* the inverted control held. A non-zero
exit is an assertion failure, not a rendering problem.

## 3. How to analyze it, step by step

**Step 1 — read the tag inventory before opening ParaView.** Expected:

- ring-gapped rung cell groups `1, 2, 3, 101-104, 105-112, 205-212`. The four
  `101-104` are the *uncut* leg boxes — floating air blocks, because there is no
  leg gap on this rung, so they have no terminal and nothing to split. That
  asymmetry is the high-pass fixture and the script asserts it rather than
  assuming it. `105-112` / `205-212` are the lower/upper halves of the eight ring
  gap boxes; a set with `105-112` but no `205-212` means the mid-plane fragment
  did not happen and there is no interface to rebuild a sheet from — the script
  stops on the non-emptiness guard rather than passing vacuously at `0 == 0`.
- leg+ring rung: all 12 ports as split pairs.
- control rung: `1, 2, 3, 101-104` and nothing else. Printed explicitly, because
  the opt-in must be opt-in.

**Step 2 — read the ring-gapped rung's numbers in this order.**

1. **Pappus on the ring primitives.** `1.000000000000` — the swept angle really
   is `2·pi/N − g/R`, i.e. the removed arc really is `g` long. This is asserted
   *pre-boolean*; the union form (gapped conductor = uncut conductor − removed
   arcs) is printed by the gate module but never gated, because it is a
   difference of two `O(1e-4)` OCC unions and carries their quadrature error.
2. **Closure and volume/analytic.** `1.000000000000` on all eight. Volume off 1
   means the wedge does not span the gap exactly, so its radial faces are not the
   ring's cut faces — read it before the terminal, which it invalidates.
3. **Sheet meshed/analytic.** `1.000000000000` on 14 facets per port. Anything
   off 1 by more than `1e-9` is a **regression against the `GEO-20` step 1
   gate** — record it in the `EX-31` / `GEO-20` entries; never widen the band
   (PROJECT_PLAN §7, MAG table, defect 5).
4. **Out-of-plane spread.** `~5e-18` m on record — roundoff, so the facet set
   really is the radial mid-section. A spread of order the cell size means the
   rebuild picked up facets off the plane. Do not read the `extents` triple as a
   planarity check; see §1 above.
5. **Terminal.** `9.796288e-05 m²`, `0.974455` of the closed-form
   `1.005309649e-04 m²`. The deficit is the inscribed triangulation of a circle
   and nothing else. Gated in `[0.95, 1.0]`, recorded at `0.974455 ± 1e-5`, and
   equal across the 8 to `1e-5` (the eight readings take two values a few `1e-12`
   apart).
6. **C4 and mirror spreads.** Below `1e-12` on volume and sheet. If they grow,
   the eight ring ports are not the same port and a circulant premise fails.

**Step 3 — read the 12-port rung.** Both identity families must be exact on the
*same* mesh: closure and volume/analytic `1.000000000000` on all 12, leg
terminals reproducing `GEO-18` step 1's **0.988616** and ring terminals
**0.974455**, each to `1e-5`. The two opt-ins are independent by construction —
the leg gap is a `z`-cut on the leg axis, the ring gap an azimuthal cut at the
mid-azimuth — and this is the measurement that they do not interact.

**Step 4 — read the control, which must fail everything.** Cell tags with no
ring port, cell count against the uncut record, meshed/CAD against `EX-21`'s,
and `ring sheet facets found by the same rebuild: P5=0 … P12=0`. That last line
is a measurement of absence.

**Step 5 — open the meshes in ParaView.** `File → Open →`
`examples/meshing/paraview_output/meshing_07_birdcage_ring_gap_ports_ring_combined.xdmf`,
then `meshing_07_birdcage_ring_gap_ports_legring_combined.xdmf`,
`meshing_07_birdcage_ring_gap_ports_uncut_combined.xdmf` and
`meshing_07_birdcage_ring_gap_ports_ring_facets.xdmf` alongside it.

- Threshold the `CellTags` cell array in any `_combined` file: `1` is the
  conductor, `2` the air, `3` the phantom, `101-104` the leg boxes, and
  `105-112` / `205-212` the lower and upper halves of the eight ring gap boxes.
  Put the ring rung beside the control — the end rings are continuous there and
  broken by an 8 mm arc at each mid-azimuth here.
- Threshold `105` and `205` separately: the flat interface between them *is* the
  ring port sheet.
- In the `_facets` file, threshold `mesh_tags` to `215`-`222`. Those are the
  sheets themselves — 10 mm × 10 mm rectangles standing in the radial planes, so
  they appear edge-on at 45° from the global axes. That view is the reason the
  planarity check had to change.
- The `legring` file is the one to open when you want to see both gap families
  at once: breaks in the legs *and* in the rings, 12 port boxes.

**Step 6 — what a deviation means.** Nothing is solved here, so every failure
mode is a geometry or tagging defect. The four to know:

- **Sheet or volume off 1 at the `1e-9` level** — the wedge is not the gap
  solid, or the rebuild matched the wrong interface. The closure localises it:
  a closure below 1 means boundary leaked into a group the partition does not
  name.
- **Terminal ratio outside `[0.95, 1.0]`** — above 1 is impossible for an
  inscribed triangulation and means the partition is picking up facets that are
  not the ring's cut disk; below 0.95 means the conductor sizing regressed.
- **Control cell count off the uncut record** — the opt-in changed the *default*
  geometry, which invalidates `EX-21`'s and `PORT-9` step 3a's numbers rather
  than just this example.
- **Hang at `-n 2`, no output** — the interior-facet (`dS`) assembly needs
  `create_entity_permutations` on *every* rank, not only ranks owning tagged
  facets (known-issues 9). The imported helpers hoist it; the same class of bug
  bit `GEO-18` step 2 attempt 1 as a collective reached inside a rank-0 print,
  which is why every count, area, extent and flatness reading here is computed
  before anything is printed.

## Related

- The gate itself: `tests/mesh/test_birdcage_ring_gaps.py` (`GEO-20` step 1).
- The other cut family: `examples/meshing/06_birdcage_leg_gaps_port_sheets.md`
  (`EX-28`, `GEO-18`) — leg gaps, planar disk terminals on cylinder stubs.
- The uncut coil: `examples/meshing/03_birdcage_graded_conductors.md`
  (`EX-21`, `GEO-15`).
- The other interior sheet: `examples/meshing/04_two_torus_port_sheet.md`
  (`EX-23`, `GEO-16`).
- What the ports are eventually for: `PORT-9` step 3 in PROJECT_PLAN.md §7 —
  still 🟡, and no port claim is made here.
