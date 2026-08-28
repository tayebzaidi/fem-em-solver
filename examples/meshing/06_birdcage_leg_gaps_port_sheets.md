# `mesh:6` — the gapped birdcage: leg terminals and port sheets

Guide for `examples/meshing/06_birdcage_leg_gaps_port_sheets.py` (`EX-28`), the
example angle `GEO-18` owes.

## 1. What this demonstrates

The first example in this repo showing a **discontinuous conductor**: a coil
whose legs are cut, with planar disk terminals on the stub faces and an interior
sheet spanning metal to metal across the cut. `EX-21` (`mesh:3`) is the *uncut*
graded birdcage; `EX-23` (`mesh:4`) is an interior port sheet, but on the
two-torus fixture. Neither shows the geometry `GEO-18` gated, which is both at
once and on a coil.

### Why the cut exists

`PORT-9` step 3 could not run at all before it. Leg (a) measured that the
birdcage carries no port-sheet facet; leg (b) measured *why that is not fixable
by splitting a box* — on the uncut coil every port box's conductor-facing area
is **exactly `0.000000e+00 m²`**, under a closure identity at
`1.000000000000`. The boxes are isolated air blocks sitting at the midpoint
azimuth between adjacent legs, outside the metal. A port sheet spanning such a
box drives nothing.

`leg_gap_length` removes the segment `|z| <= g/2` from every leg (here
`g = 8 mm` on a 140 mm leg) and re-places each port box **centred on its own leg
axis, spanning exactly the gap**, so the two stub cut faces *are* the box's
z-faces. Legs are axis-aligned cylinders, so those faces are planar disks with
the closed form `pi*r_leg**2` each — which is what makes this the cheap cut; the
end-ring alternative gives oblique torus sections at 45° and no closed form at
all. Two of leg (a)'s open questions dissolve by construction: the drive
direction is `ẑ` for every port, and a square transverse section makes the
four-port layout exactly C4-invariant.

`emit_port_sheets` then fragments that box with its own mid-plane, so each port
becomes **two** cell groups (`10x` + `11x`) and the sheet is rebuilt
dolfinx-side from the interface between them — never as a gmsh dim-2 physical
group, which hangs `model_to_mesh` at `-n 2` inside `distribute_entity_data`
(known-issues 9).

### The quantities, and why they are identities rather than bands

The sheet plane contains the leg axis and the radial direction, so it spans the
gap along the current direction `ẑ` (`h = g`) and the box transversely
(`w = dx`): a full rectangle of closed-form area `dx·g`. A planar rectangle
meshed by a conforming fragment has **no discretisation error to spend**, so
these are exact to roundoff and gated at `1e-9`, not banded:

- sheet area / `dx·g` = 1 on all four ports;
- effective width `A/h` = the bounding-box transverse extent (the `PORT-9`
  step 2b width convention `w = A/h`). These are equal exactly when the
  reconstructed facet set is the *whole* rectangle, so this is the assertion
  that the sheet is not ragged or partial;
- the two halves of each box are `0.5` of the analytic gap box;
- the boundary closure — conductor + air + phantom facing areas over the
  analytic box surface — is 1, which is what says the terminal reading below is
  the whole terminal and not a fragment of one;
- the four sheets agree to `1e-12` relative (C4 by construction, checked).

The **terminal** is the one banded quantity, and deliberately so: the meshed
disk is an *inscribed* triangulation of the stub's circular face, so its ratio
to `2·pi·r_leg²` must land at or below 1. It is asserted inside `GEO-18`'s
pre-stated `[0.95, 1.0]` and against step 1's record `0.988616` to `1e-5`.

The `GEO-9` box-partition identities are re-asserted on **both** rungs. Cutting
a leg and splitting a box move cell groups, not geometry; an identity that moves
is a defect in the fragment, not a resolution effect.

### The negative control is inverted, and now measured rather than implied

The uncut rung (`leg_gap_length=None`) must reproduce `EX-21`'s record — 98 474
cells, meshed/CAD `0.967019` — and must **lack** everything above: conductor
-facing port area exactly `0.0` on all four ports, no `11x` cell tag, and
`_global_facet_count` **= 0** on every `210+i` after running the *same*
`_interface_facet_tags` rebuild on that mesh. `GEO-18` step 2's audit found that
last clause asserted on the *cell* tags and only implied for the facet groups;
this example closes it directly, which is the one thing here that is not simply
a re-execution of the gate.

Every constant is **imported** from `tests/mesh/test_birdcage_leg_gaps.py`,
`tests/mesh/test_birdcage_port_sheets.py` and the modules they import in turn
(the `ANS-1` rule); nothing is restated, so this example cannot drift from the
gates it demonstrates.

**Mesh only — no port model, no solve, no impedance or resonance claim.** A
gapped birdcage without lumped elements cannot resonate. This is the mesh
`PORT-9` step 3 solves on, and nothing downstream of it. `PORT-9` is 🟡
(PROJECT_PLAN.md §2).

## 2. How to run it

```
./run_examples.sh -e mesh:6 -n 2 -t 400
```

Real DolfinX build (no complex mode needed); the runner selects it. Tier:
**standard**. On record at `-n 2`: sheeted rung **116 416 cells, 21.46 s mesh /
23.41 s rung**, uncut control **98 474 cells / 19.02 s**, **43.1 s** in-script
total including all three ParaView exports — 46 s of harness wall clock,
measured 2026-08-23, log `20260823T020338Z_EX-28-example-n2.log`. Add `-n <k>`
to change rank count and `-t <s>` to lower the per-example timeout.

Exit status 0 means every identity *and* the inverted control held. A non-zero
exit is an assertion failure, not a rendering problem.

## 3. How to analyze it, step by step

**Step 1 — read the tag inventory before opening ParaView.** Expected:

- sheeted rung cell groups `1, 2, 3, 101-104, 111-114`. A set with `101-104` but
  no `111-114` means the fragment did not happen and the sheet is not a mesh
  entity at all — the identities below would then have nothing to reconstruct
  from, and the script stops on the non-emptiness guard rather than passing
  vacuously at `0 == 0`.
- uncut rung cell groups `1, 2, 3, 101-104` and nothing else. This is printed
  explicitly because the opt-in must be opt-in.

**Step 2 — read the sheeted rung's numbers in this order.**

1. **Facet counts.** 54 per sheet on record, 204-212 per terminal. Zero is the
   vacuous-pass failure mode; a wildly different count at the same resolution
   means the mesh moved.
2. **meshed/analytic on the sheet.** `1.000000000000` and area
   `1.120000000e-04 m²` on all four. Anything off 1 by more than `1e-9` is a
   **regression against the `GEO-18` step 2 gate** — record it in the `EX-28` /
   `GEO-18` entries; never widen the band (PROJECT_PLAN §7, MAG table,
   defect 5).
3. **`w_eff/w_bbox`.** `1.000000000000`. Below 1 means the reconstruction found
   only part of the mid-section, and the area identity above would then be
   failing for the same reason — read them together.
4. **Out-of-plane spread.** `2.512e-16` m (P1/P3) and `9.714e-17` m (P2/P4) on
   record — roundoff, so the facet set really is a plane. The two values differ
   because the plane is `y`-normal for a leg on the `x`-axis and `x`-normal for
   one on the `y`-axis; the script reads the pinned axis off the measurement
   rather than assuming it. A spread of order the cell size means the rebuild
   picked up facets off the mid-plane.
5. **Halves.** `0.500000000000/0.500000000000` of the analytic gap box. A split
   at anything but `0.5` means the plane does not pass through the box centre,
   i.e. not through the leg axis, so the sheet is not the mid-section.
6. **Terminal.** `2.236196e-04 m²`, `0.988616` of the closed-form
   `2.261946711e-04 m²`, closure `1.000000000000`. The deficit is the inscribed
   triangulation of a circle and nothing else; it is *gated* in `[0.95, 1.0]`
   and *recorded* at `0.988616 ± 1e-5`.
7. **C4 sheet spread.** `8.470e-16`. The four ports are the same port; if this
   grows, gate (iii)'s circulant premise for `PORT-9` step 3 fails.

**Step 3 — read the control, which must fail everything.** On record:
`cells=98474 (ratio 1.000000)`, `meshed/CAD 0.967019`, conductor-facing areas
`P1=0.000000e+00 … P4=0.000000e+00`, and `21x sheet facets found by the same
rebuild: P1=0 P2=0 P3=0 P4=0`. That last line is a measurement of absence, and
it is the clause this example exists to close.

**Step 4 — open the meshes in ParaView.** `File → Open →`
`examples/meshing/paraview_output/meshing_06_birdcage_leg_gaps_port_sheets_sheeted_combined.xdmf`,
then `meshing_06_birdcage_leg_gaps_port_sheets_uncut_combined.xdmf` and
`meshing_06_birdcage_leg_gaps_port_sheets_sheeted_facets.xdmf` alongside it.

- Threshold the `CellTags` cell array in either `_combined` file: `1` is the
  conductor, `2` the air, `3` the phantom, and `101-104` / `111-114` the lower
  and upper halves of the four gap boxes. Put the two rungs side by side — the
  legs are continuous in the uncut coil and broken by an 8 mm gap in the
  sheeted one. That break is the whole geometric content of `GEO-18` step 1.
- Threshold `101` and `111` separately: the flat interface between them *is* the
  port sheet.
- In the `_facets` file, threshold the `mesh_tags` array to `211`-`214`. Those
  are the surfaces themselves — flat 14 mm × 8 mm rectangles sitting inside each
  gap box, with the leg's two circular cut faces normal to them.

**Step 5 — what a deviation means.** Nothing is solved here, so every failure
mode is a geometry or tagging defect. The four to know:

- **Sheet area off 1 at the `1e-9` level** — the rebuild matched the wrong
  interface, or the mid-plane no longer cuts the box in half. Check the halves
  and `w_eff/w_bbox` first; they localise it.
- **Terminal ratio outside `[0.95, 1.0]`** — above 1 is impossible for an
  inscribed triangulation and means the partition is picking up facets that are
  not the stub face; below 0.95 means the conductor sizing regressed.
- **Control cell count off 98 474** — the opt-in changed the *default*
  geometry. `EX-21`'s and `PORT-9` step 3a's numbers were measured on that
  mesh, so this invalidates them rather than just this example.
- **Hang at `-n 2`, no output** — the interior-facet (`dS`) assembly needs
  `create_entity_permutations` called on *every* rank, not only ranks owning
  tagged facets (known-issues 9). The helpers this example imports already
  hoist it; the same class of bug bit `GEO-18` step 2 attempt 1 as a collective
  reached inside a rank-0 print, which is why the counts, areas and extents
  here are all computed before anything is printed.

## Related

- The gates themselves: `tests/mesh/test_birdcage_leg_gaps.py` (`GEO-18`
  step 1) and `tests/mesh/test_birdcage_port_sheets.py` (`GEO-18` step 2).
- What the cut was for: `PORT-9` step 3 in PROJECT_PLAN.md §7 — legs (a)/(b)
  are the 🚫 this geometry lifts, and leg (c) is the first solve on this mesh.
- The uncut coil: `examples/meshing/03_birdcage_graded_conductors.md`
  (`EX-21`, `GEO-15`).
- The other interior sheet: `examples/meshing/04_two_torus_port_sheet.md`
  (`EX-23`, `GEO-16`).
- The other mesh-only examples: `examples/meshing/01_two_torus_ports.md`,
  `examples/meshing/02_cylindrical_phantom.md`,
  `examples/meshing/05_region_resolution_policy.md`.
