# `mesh:8` — the 16-leg gapped + sheeted birdcage: the first coil above four legs

Guide for `examples/meshing/08_birdcage_sixteen_legs.py` (`EX-33`), the example
angle `GEO-19` ✅ (2026-08-25) owes under the §5.4 ramp.

## 1. What this demonstrates

Every other birdcage example in this repo is **four legs**:
`03_birdcage_graded_conductors.md` (`EX-21`, `mesh:3`) grades the conductors on
the uncut coil, `06_birdcage_leg_gaps_port_sheets.md` (`EX-28`, `mesh:6`) cuts
the legs and rebuilds the port sheets, `07_birdcage_ring_gap_ports.md` (`EX-31`,
`mesh:7`) cuts the end rings. Until `GEO-19` nothing in this repo had ever been
meshed above four legs at all — the half-tag encoding `110+i` collided at
`i >= 11` and the box/sheet construction raised `NotImplementedError` for any
leg off a coordinate axis. Both are fixed; this example is what that bought.

### Why sixteen is a different measurement, not a bigger one

At four legs every port sits on a coordinate axis. The sheets are x- or
y-normal, the four terminal disks are the same disk under a coordinate mirror,
and every identity the gate asserts is equally consistent with the construction
being an accident of C4. At sixteen the azimuthal pitch is 22.5°, **twelve of
the sixteen ports are off-axis**, and a sheet is neither x- nor y-normal — so
its extents have to be read as projections onto that port's own
(radial, azimuthal, axial) frame, taken from the mesh rather than assumed. The
identities either survive that or they were never properties of the
construction.

They survive. Asserted here, all imported from
`tests/mesh/test_birdcage_port_scaleup.py` and executed by the gate module's own
`_assert_identity_family` rather than re-implemented:

- the `GEO-9` tagged-volume partition and the analytic air box, to `1e-9`;
- all **32** half-boxes at `0.5` of the analytic gap box, to `1e-9`;
- all **16** sheets at the closed-form mid-section `dx·g`, planar, spanning the
  gap, `A/h` equal to the transverse extent, C16 spread under
  `SHEET_SPREAD_BAND`;
- all 16 terminal disks inside the imported `TERMINAL_AREA_BAND` `[0.95, 1.0]`,
  under a boundary closure at `1.000000000000` that is what makes them readable
  as terminals rather than as fragments;
- the graded conductor at its own CAD mass against `CAD_MASS_GATE`;
- the layout's port-centre clearance floor at the new pitch.

### The one gate that reads differently, and the table this example prints

The terminal **equality** half is read per azimuth class (the 2026-08-25 review
ruling, `GEO-19` §7). The mesh's own mirror symmetries — `x → −x` and `y → −y` —
fold sixteen azimuths into three classes, and the gate is intra-class
`TERMINAL_INTRA_CLASS_BAND` = `1e-6` with an inter-class ceiling
`TERMINAL_INTER_CLASS_CEILING` = `5e-3` placed at half the inscribed
triangulation's own `~1.1e-2` azimuthal under-read of the disk. The partition
comes off the *azimuths*, never off the measured areas — that is what keeps it
from being circular.

That three-value table is the centrepiece print here, and it is the reading a
C4 fixture structurally cannot show you.

### The negative control: the same code path at four legs reports ONE class

`GEO-19`'s back-compat identity, asserted here rather than assumed. At four legs
every port is aligned, so the per-class reading collapses to exactly the old
flat equality gate. A four-leg build reporting more than one class would mean
`_azimuth_class` had started reading areas instead of azimuths. The control's
cell count and its four terminal ratios are checked against the imported step-B
records in the same rung, so the example's mesh is provably the gate's mesh.

### Phase 6's first cost rung — printed, never asserted

Cells and mesh wall time for 4 → 16 legs come out of the **same run on the same
box**, so the ratio is a measurement rather than a comparison across machines.
Counts and timings are prints; nothing here bands them.

**Mesh only — no solve, no port model, no drive, no impedance, no resonance and
no F-human claim, at any leg count.** Nothing in this repo solves at sixteen
legs. The 32-port ring layout is `GEO-20` step 2 and is not built here. And 32
legs do not fit this ring at all: the clearance floor
`1.25·box_width = 1.750000e-02 m` against a pitch `2·R·sin(π/N)` admits
`N ≤ 25` (`SEPARATION_LEG_COUNT_CEILING`, measured 2026-08-23), which is why the
production rung this example prices is 16 and not the directive's 32.

## 2. How to run it

```
./run_examples.sh -e mesh:8 -n 2 -t 400
```

Real DolfinX build (no complex mode needed); the runner selects it. Tier:
**standard**.

On record at `-n 2`, commit `478e8f1` + this example, log
`20260826T183240Z_EX-33-run1.log`, **131 s** wall clock (127.7 s in-script):
16-leg rung **307 296 cells, 84.25 s mesh, 96.38 s build rung**; 4-leg control
**116 085 cells, 26.51 s mesh, 29.52 s rung**. Those digits move with the mesh
generator and with gmsh; they are prints, and the only *asserted* count here is
the control's against its imported record.

Exit status 0 means the whole identity family held at sixteen **and** the
control collapsed to one class. A non-zero exit is an assertion failure, not a
rendering problem.

## 3. How to analyze it, step by step

**Step 1 — read the tag inventory before opening ParaView.** The 16-leg rung
carries cell groups `1, 2, 3, 101-116, 201-216`: conductor, air, phantom, then
the lower and upper halves of the sixteen gap boxes. The upper base is `200+i`,
not the `110+i` that collided above nine legs — a set carrying `101-116` but no
`201-216` means the mid-plane fragment did not happen and there is no interface
to rebuild a sheet from. The gate asserts the exact expected set, so a stray or
missing tag stops the run before any ratio is taken.

**Step 2 — read the 16-leg numbers in this order.**

1. **Partition and air box.** `1.000000000000` on both. The cut and the split
   move cell groups, not geometry, so these may not move at all. Read them
   first: everything below is a ratio against an analytic form that assumes
   them.
2. **Closure, per port.** `1.000000000000` on all sixteen. A closure below 1
   means boundary leaked into a group the partition does not name, which
   invalidates the terminal reading rather than merely perturbing it.
3. **Halves.** `0.500000000000 / 0.500000000000` on all sixteen. Off 0.5 means
   the mid-plane does not pass through the box centre, i.e. not through the leg
   axis.
4. **Sheet meshed/analytic.** `1.000000000000` on all sixteen, with
   out-of-plane spread at `~1e-18` m and `w_eff/w_bbox` at
   `1.000000000000`. A planar rectangle meshed by a conforming fragment has no
   discretisation error to spend here; anything off 1 by more than `1e-9` is a
   **regression against the `GEO-19` gate** — record it in the `EX-33` / `GEO-19`
   entries, never widen the band (PROJECT_PLAN §7, MAG table, defect 5). Note
   that only four of the sixteen sheets are axis-normal, so this line is also
   the statement that the frame-aware extents are correct off-axis.
5. **C16 sheet spread.** `1.331e-15` on record against `SHEET_SPREAD_BAND`
   `1e-12` — summation order, nothing more. Growth here means the sixteen ports
   are not the same port and any future circulant premise fails.
6. **The azimuth-class table.** Three classes, on record:

   | class | ports | azimuths (deg) | meshed/analytic | intra-class spread |
   |---|---|---|---|---|
   | `aligned` | 8 | 0, 45, 90, 135, 180, 225, 270, 315 | 0.988615772 | 1.923e-07 |
   | `22.500 deg` | 4 | 22.5, 157.5, 202.5, 337.5 | 0.989367514 | 5.849e-08 |
   | `67.500 deg` | 4 | 67.5, 112.5, 247.5, 292.5 | 0.989449735 | 6.144e-08 |

   Inter-class spread **8.431e-04** against the `5e-3` ceiling. Read the two
   columns differently: the intra-class spreads are the **construction's C16
   covariance** and sit 5–17× inside their `1e-6` band; the inter-class term is
   the inscribed triangulation's azimuthal variation and sits ~6× inside its
   ceiling and ~13× below the triangulation's own `~1.1e-2` under-read of the
   disk. An intra-class red is a generator finding — the ports in one class are
   the same disk under a symmetry of the mesh, so there is nothing there to
   widen.
7. **Conductor meshed/CAD.** `0.981503` at 16 legs against the imported
   `CAD_MASS_GATE`; the 4-leg control reads `0.970069` on the same `h_c`. The
   16-leg figure is the *higher* one — more legs at the same graded sizing means
   a larger fraction of the conductor volume is well-resolved leg rather than
   ring.
8. **Port-centre separation margin.** `1.560723x` at 16 legs against
   `5.656854x` at 4. This is the term that closes: it is the reason 32 legs are
   below the floor on this ring, and the gate asserts the margin rather than
   shrinking the boxes to make it pass.

**Step 3 — read the control, which must collapse.** One azimuth class,
`aligned`, 4 ports, `meshed/analytic = 0.988615842`, intra-class spread
`3.184e-08`, inter-class spread `0.000e+00` — the flat equality gate, recovered
exactly. Its cell count reads `116085` against the imported step-B record at
relative `0.000e+00`.

**Step 4 — read the cost rung.** On record: cells `116085 → 307296`
(**2.6472×**), mesh `26.51 → 84.25 s` (**3.1777×**), build rung
`29.52 → 96.38 s`. The leg count went up 4×; cells went up 2.65× and mesh
seconds 3.18×. So cells grow **sublinearly** in leg count — the added legs are
thin graded conductors inside an air box whose size never changed — while mesh
time grows **faster than cells** (3.18× on 2.65× the cells), which is the term
that will bite first on the way to a production count. That is the rung Phase 6
needs, and it is printed rather than asserted: a machine-to-machine comparison
of these seconds means nothing.

**Step 5 — open the mesh in ParaView.** `File → Open →`
`examples/meshing/paraview_output/birdcage_sixteen_legs_combined.xdmf`, and
`birdcage_sixteen_legs_facets.xdmf` alongside it.

- Threshold the `CellTags` cell array in the `_combined` file: `1` conductor,
  `2` air, `3` phantom, `101-116` / `201-216` the lower and upper halves of the
  sixteen gap boxes. Put it beside `birdcage_leg_gaps_port_sheets_sheeted_combined.xdmf`
  (`mesh:6`) — same construction, four legs, 90° pitch.
- Threshold `101` and `201` separately: the flat interface between them *is*
  port 1's sheet.
- In the `_facets` file, threshold `mesh_tags` to `211`-`226`. Those are the
  sixteen sheets. Only four stand in a coordinate plane; the other twelve are
  seen edge-on at 22.5° multiples, which is the picture the frame-aware extents
  exist for.

**Step 6 — what a deviation means.** Nothing is solved here, so every failure
mode is a geometry or tagging defect. The four to know:

- **An intra-class terminal red** — the construction lost C_N covariance. A
  generator finding; do not widen the band and do not re-partition the classes
  to fit the measurement.
- **The control reporting more than one class** — `_azimuth_class` is reading
  areas rather than azimuths, which would make the whole per-class gate
  circular.
- **A sheet or half off its identity at the `1e-9` level, off-axis only** — the
  local-frame construction (`GEO-19` step B) has regressed to something
  axis-aligned; the four aligned ports would still read clean, which is why the
  off-axis twelve are the ones to look at.
- **Hang at `-n 2`, no output** — a collective reached inside a rank-0 print.
  Every count, area, extent and azimuth here is computed by `_measure` before
  anything is printed, and the report itself runs under the gate module's
  `_report_safely` broadcast guard, which turned a 561 s Status 124 into a
  failed assertion once already (`GEO-19` step C, 2026-08-25).

## Related

- The gate itself: `tests/mesh/test_birdcage_port_scaleup.py` (`GEO-19`).
- The four-leg version of this exact construction:
  `examples/meshing/06_birdcage_leg_gaps_port_sheets.md` (`EX-28`, `GEO-18`).
- The other cut family: `examples/meshing/07_birdcage_ring_gap_ports.md`
  (`EX-31`, `GEO-20` step 1) — ring gaps, and where the 32-port layout goes
  next.
- The uncut graded coil: `examples/meshing/03_birdcage_graded_conductors.md`
  (`EX-21`, `GEO-15`).
- What the ports are eventually for: `PORT-9` and `PORT-11` in
  PROJECT_PLAN.md §7 — both at four legs, and no port claim is made here at any
  count.
