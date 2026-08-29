# `mesh:9` — the 16-leg ring-gapped birdcage: 32 ring ports, the production high-pass layout

Script: `examples/meshing/09_birdcage_sixteen_ring_gaps.py` (`EX-35`)
Gate: `tests/mesh/test_birdcage_ring_gaps_scaleup.py` (`GEO-20` step 2, ✅ 2026-08-29)

## 1. What this demonstrates

Three birdcage-port examples exist and none of them shows the topology the §10
32-port directive actually asks for:

| example | cut | legs | ports |
|---|---|---|---|
| `mesh:6` (`EX-28`) | legs | 4 | 4 leg |
| `mesh:7` (`EX-31`) | end rings (and, on rung 2, both families) | 4 | 8 ring / 12 dual |
| `mesh:8` (`EX-33`) | legs | 16 | 16 leg |
| **`mesh:9` (this one)** | **end rings** | **16** | **32 ring** |

This is the missing corner: the high-pass cut (**both end rings**) at the
production leg count (**sixteen**), so `2 × 16 = 32` ring ports on one mesh —
the layout `GEO-20` step 2 gated and that until now lived only inside the gate
module.

### Why sixteen ring gaps is a different measurement, not a bigger one

The ring gap centres sit at `phi = 2·pi·j/N + pi/N`, i.e. **11.25 + 22.5·j deg**
at sixteen legs. So:

- **not one of the 32 sheets stands in a coordinate plane**, and none is
  diagonal-aligned either — unlike the 4-leg ring build, whose gap centres at
  45/135/225/315° all fold to a single "aligned" class;
- a ring sheet is **radial**: its normal is azimuthal, so *no global coordinate
  is constant on it* at any leg count. Every planarity and extent reading has to
  be taken in each port's own ring frame (`_ring_gap_frame`), which is why the
  bounding-box planarity check `GEO-18` uses for leg sheets cannot be reused
  here;
- the terminal *equality* half is read **per azimuth class** (the 2026-08-25
  ruling), and the fold predicts **four** classes here where four legs give
  **one**. That structural count — asserted on both rungs by the gate module,
  and read as a pair by this example — is the centrepiece table.

### The legs are UNCUT on this rung: 32 sheets, not 48

The high-pass layout drives the **ring** gaps. The sixteen leg boxes are
floating air blocks with no terminal and nothing to split, so a leg carries cell
tag `100+i` alone while a ring port carries both `100+i` and `200+i`. That
asymmetry *is* the high-pass fixture and the gate asserts the exact expected tag
set rather than assuming it.

The **48-sheet dual-family build** — both gap families switched on at once, as
`mesh:7` rung 2 does at four legs — **has never been meshed at sixteen legs** in
this repo. It is not built here and nothing below says anything about it.

### It asserts, it does not merely render

The identity family is asserted by the gate module's own
`_assert_ring_identity_family` on *this run's own mesh* (the `ANS-1` rule), so
this example cannot drift from the gate it demonstrates: the `GEO-9`
tagged-volume partition and the analytic air box, every port solid at its
analytic wedge volume and every sheet at `w²` to `EXACT` (`1e-9`), the C32
spread and the top/bottom ring mirror under `SYMMETRY` (`1e-12`), the terminals
inside the inscribed band and equal per azimuth class (intra `1e-6`, inter
ceiling `5e-3`), the ring arcs against Pappus, and the graded conductor against
its own CAD mass.

### The negative control: the same code path at four legs returns ONE class

`GEO-20` step 1's fixture, rebuilt in the same process: its cell count and its
eight terminal ratios are asserted against the imported step-1 records, and it
must collapse to a single azimuth class. If the class partition were reading
measured *areas* rather than the mesh's own symmetry, the four-leg build would
not collapse — which is what makes the four-class reading at sixteen a
refinement rather than a different test.

### Scope

**Mesh only.** No solve, no port model, no drive, no impedance, no resonance and
no F-human claim at any leg count. A gapped birdcage without lumped elements
cannot resonate; a high-pass *layout* is not a high-pass *circuit*. Nothing in
this repo solves at sixteen legs, and `PORT-9` is 🟡 (PROJECT_PLAN.md §2). This
is F-small — a 0.07 m ring.

## 2. How to run it

```
./run_examples.sh -e mesh:9 -n 2 -t 400
```

Real DolfinX build (no complex mode needed); the runner selects it. Tier:
**standard**.

On record at `-n 2`, log `20260829T200308Z_EX-35-run1.log`, **104 s** wall clock
(101.1 s in-script): 16-leg rung **265 621 cells, 66.95 s mesh, 74.35 s build
rung**; 4-leg control **110 786 cells, 22.29 s mesh, 24.11 s rung**. Those
digits move with the mesh generator and with gmsh; they are prints, and the only
*asserted* count here is the control's against its imported record.

Exit status 0 means the whole identity family held across all 32 ring ports
**and** the control collapsed to one class. A non-zero exit is an assertion
failure, not a rendering problem.

## 3. How to analyze it, step by step

**Step 1 — read the tag inventory before opening ParaView.** The 16-leg rung
carries cell groups `1, 2, 3, 101-116, 117-148, 217-248`: conductor, air,
phantom, then the sixteen **uncut** leg boxes (single tags, no `2xx` partner),
then the lower and upper halves of the 32 ring gap boxes. A `2xx` tag appearing
on a leg ordinal would mean the legs got cut too — a 48-sheet build, not this
one. A ring ordinal missing its `2xx` partner means the mid-plane fragment did
not happen and there is no interface to rebuild a sheet from. The gate asserts
the exact expected set, so either stops the run before any ratio is taken.

**Step 2 — read the 16-leg numbers in this order.**

1. **Partition and air box.** `1.000000000000` on both. The cut and the split
   move cell groups, not geometry, so these may not move at all. Read them
   first: everything below is a ratio against an analytic form that assumes
   them.
2. **Ring arcs against Pappus.** `3.134786420778e-05 / 3.134786420778e-05 =
   1.000000000000` — the swept angle really is `2·pi/N − g/R` on all 32 arcs.
   This is the pre-boolean primitive mass; the union form (gapped = uncut −
   removed) is printed by the gate module but deliberately **not** gated, since
   it carries OCC quadrature error over more curved pieces at sixteen legs, not
   fewer.
3. **Closure, per port.** `1.000000000000` on all 32. A closure below 1 means
   boundary leaked into a group the partition does not name, which invalidates
   the terminal reading rather than merely perturbing it.
4. **Port volume / analytic wedge.** `1.000000000000` on all 32 against
   `8.008718871e-07 m³ = 2·R·w²·tan(alpha)`. Off 1 means the rotated box does
   not span the gap exactly, so its radial faces are not the ring's cut faces.
5. **Sheet meshed/analytic.** `1.000000000000` on all 32 against `w² =
   1.000000000e-04 m²`, with out-of-plane spread at `~2e-18 m` measured along
   each sheet's **own** azimuthal normal. A planar rectangle meshed by a
   conforming fragment has no discretisation error to spend here; anything off 1
   by more than `1e-9` is a **regression against the `GEO-20` gate** — record it
   in the `EX-35` / `GEO-20` entries, never widen the band (PROJECT_PLAN §7, MAG
   table, defect 5).
6. **C32 sheet spread.** `4.985e-16` against `SYMMETRY` `1e-12` — summation
   order, nothing more. Growth here means the 32 ports are not the same port and
   any future circulant premise fails.
7. **The azimuth-class table.** Four classes, on record:

   | class | ports | azimuths (deg) | meshed/analytic | intra-class spread |
   |---|---|---|---|---|
   | `11.250 deg` | 8 | 11.25, 168.75, 191.25, 348.75 (× both rings) | 0.974454812 | 4.198e-08 |
   | `33.750 deg` | 8 | 33.75, 146.25, 213.75, 326.25 | 0.974454921 | 4.498e-07 |
   | `56.250 deg` | 8 | 56.25, 123.75, 236.25, 303.75 | 0.974454916 | 4.681e-07 |
   | `78.750 deg` | 8 | 78.75, 101.25, 258.75, 281.25 | 0.974455135 | 8.997e-07 |

   Inter-class spread **3.315e-07** against the `5e-3` ceiling. Read the two
   columns differently: the intra-class spreads are the **construction's C32
   covariance** and sit inside their `1e-6` band (the `78.750 deg` class at
   `9.0e-07` is the tightest margin in the family — the number to watch on any
   future mesh change); the inter-class term is the inscribed triangulation's
   azimuthal variation, and here it is **four orders of magnitude inside its
   ceiling**, unlike the leg family's `8.4e-04` at the same leg count. That
   contrast is the ring construction's advantage: a ring gap's cut faces are
   exact planar disks whose triangulation barely notices azimuth, where a leg
   gap's terminal is a disk read against a box the air mesh does not rotate
   with.
8. **Terminal meshed/analytic.** `0.974454791`–`0.974455668` across all 32,
   against the closed-form two disks `1.005309649e-04 m² = 2·pi·r_ring²`. The
   ~2.55% under-read is the inscribed triangulation of a disk, not an error: the
   gate bands it inside `TERMINAL_AREA_BAND` and this example reproduces
   `GEO-20` step 1's `0.974455` record to the digit at four legs.
9. **Conductor meshed/CAD.** `0.976465` at 16 legs against the imported
   `CAD_MASS_GATE` `0.95`; the 4-leg control reads `0.969275` on the same `h_c`.
   The 16-leg figure is the *higher* one — more legs at the same graded sizing
   means a larger fraction of the conductor volume is well-resolved leg rather
   than ring.
10. **Leg-arc clearance.** `3.744468e-03 m` at 16 legs against `4.497787e-02 m`
    at 4. This is the term that closes as the leg count rises: the ring gap has
    to fit in the arc between two adjacent legs, and at sixteen it has ~3.7 mm of
    room left. It is the reason the directive's counts are studied on this ring
    rather than assumed.

**Step 3 — read the control, which must collapse.** One azimuth class,
`aligned`, 8 ports, `meshed/analytic = 0.974454812`, intra-class spread
`4.198e-08`, inter-class spread `0.000e+00` — the flat equality gate, recovered
exactly. Its cell count reads `110786` against `GEO-20` step 1's record at
relative `0.000e+00`, and every one of its eight terminal ratios is asserted
against `RING_TERMINAL_RATIO`.

**Step 4 — read the cost rung.** On record: cells `110786 → 265621`
(**2.3976×**), ring ports `8 → 32` (**4×**), mesh `22.29 → 66.95 s`
(**3.0042×**), build rung `24.11 → 74.35 s`. The leg count went up 4×; cells
went up 2.40× and mesh seconds 3.00×. So cells grow **sublinearly** in leg count
— the added ring arcs and gap boxes are small features inside an air box whose
size never changed — while mesh time grows **faster than cells** (3.00× on 2.40×
the cells), the same shape `EX-33` measured on the leg family (3.18× on 2.65×).
Two independent cut families now agree that meshing time, not cell count, is the
term that bites first on the way to a production count. Printed rather than
asserted: a machine-to-machine comparison of these seconds means nothing.

**Step 5 — open the mesh in ParaView.** `File → Open →`
`examples/meshing/paraview_output/meshing_09_birdcage_sixteen_ring_gaps_combined.xdmf`,
and `meshing_09_birdcage_sixteen_ring_gaps_facets.xdmf` alongside it.

- Threshold the `CellTags` cell array in the `_combined` file: `1` conductor,
  `2` air, `3` phantom, `101-116` the sixteen uncut leg boxes, `117-148` /
  `217-248` the lower and upper halves of the 32 ring gap boxes. Both end rings
  are broken by an 8 mm arc at each mid-azimuth while the legs run through
  unbroken — put it beside `meshing_08_birdcage_sixteen_legs_combined.xdmf`
  (`mesh:8`), the same leg count with the *other* family cut, and the difference
  between a high-pass and a low-pass layout is the whole picture.
- Threshold `117` and `217` separately: the flat radial interface between them
  *is* ring port P17's sheet.
- In the `_facets` file, threshold `mesh_tags` to `227`-`258`. Those are the 32
  sheets, radial rectangles seen edge-on at a 22.5° pitch offset 11.25° off
  every axis — the picture the ring-frame flatness check exists for.

**Step 6 — what a deviation means.** Nothing is solved here, so every failure
mode is a geometry or tagging defect. The five to know:

- **An intra-class terminal red** — the construction lost C_N covariance. A
  generator finding; do not widen the band and do not re-partition the classes
  to fit the measurement. The `78.750 deg` class is the one with the least
  margin.
- **The control reporting more than one class** — `_azimuth_class` is reading
  areas rather than azimuths, which would make the whole per-class gate
  circular.
- **A sheet off `w²` at the `1e-9` level** — with ring gaps there is no
  axis-aligned subset to hide behind, since every sheet is off-axis; a red here
  is the frame construction, not a special case.
- **A leg ordinal carrying a `2xx` tag** — the leg family got switched on too.
  That would be the 48-sheet dual-family build, which has never been meshed at
  this leg count and whose identities are therefore unknown.
- **Hang at `-n 2`, no output** — a collective reached inside a rank-0 print.
  Every count, area, extent and azimuth here is computed by `_measure_ring`
  before anything is printed, and the report runs under the gate module's
  `_report_safely` broadcast guard, which turned a 561 s Status 124 into a
  failed assertion once already (`GEO-19` step C, 2026-08-25).

## Related

- The gate itself: `tests/mesh/test_birdcage_ring_gaps_scaleup.py` (`GEO-20`
  step 2).
- The four-leg version of this exact cut: `examples/meshing/07_birdcage_ring_gap_ports.md`
  (`EX-31`, `GEO-20` step 1) — and rung 2 there is the 12-port dual family, the
  build that has *not* been done at sixteen.
- The same leg count with the other family cut:
  `examples/meshing/08_birdcage_sixteen_legs.md` (`EX-33`, `GEO-19`).
- The uncut graded coil: `examples/meshing/03_birdcage_graded_conductors.md`
  (`EX-21`, `GEO-15`).
- What the ports are eventually for: `PORT-9` and `PORT-11` in PROJECT_PLAN.md
  §7 — both at four legs, and no port claim is made here at any count.
