# `mesh:4` — the port-sheet mid-plane on the two-torus fixture

Guide for `examples/meshing/04_two_torus_port_sheet.py` (`EX-23`).
Written to be followed without the source open.

## 1. What this demonstrates

The first example in this repo showing an **interior sheet surface**. `mesh:1`
shows the gapped two-torus and `mesh:3` the graded birdcage; neither shows the
geometry `GEO-16` gated — a tagged surface *inside* the volume, whose facet
tags are not a dim-2 gmsh physical group at all. They are rebuilt on the
dolfinx side from the cell tags either side of the surface (the known-issues-9
pattern), which is why they need the fragment: the tet mesh must **conform** to
the plane before anything can integrate over it.

### Why the surface exists

A lumped-element port sheet spans terminal to terminal with the port current
flowing *in* its plane, so `R = Z_p · w / h` is written for a surface that
contains the current direction. The fixture's existing port facets `201` /
`202` are the gap↔conductor cross-sections — *normal* to that current, and
therefore the wrong constitutive law. `emit_port_sheet=True` fragments each gap
box with its own mid-plane `z = ±separation/2`, which contains both the gap's
centreline arc and the current direction `ŷ`.

One visible consequence: each gap volume becomes **two** cell groups,
`101`+`111` and `102`+`112`. A caller selecting gap 1 must select both.

### The quantity, and why it is an identity rather than a band

The mid-plane is planar and the mesh conforms to it, so a linear-tet
triangulation of it is *exact*. There is no curvature to inscribe — unlike the
2.55% chordal deficit the arc-end port cuts carry (`PORT-1` 3b-iv). The
MPI-reduced `dS` area of the reconstructed facet set must therefore **equal**
the CAD mid-plane area `(2·gap_half_xz)·(2·gap_half_y)`, not merely approach
it.

| Assertion | Gate | Measured 2026-08-17 |
| --- | --- | --- |
| sheet 211 meshed/CAD = 1 to `AREA_IDENTITY_BAND` (1e-9) | `GEO-16` | **1.000000000000** |
| sheet 212 meshed/CAD, same band | `GEO-16` | **1.000000000000** |
| 211/212 area symmetry < `1e-12` | mirror premise | areas bit-identical |
| kwarg-off control: 79 534 cells, **no** `21x` tags | inverted control | 79 534, `[]` |

Each facet group is asserted **non-empty first** (84 facets each). That order
matters: a reconstruction matching zero facets would give `0 == 0` and pass the
area identity vacuously.

The kwarg-off run is the `EX-18` / `EX-21` inverted-assertion pattern. Every
gated `PORT-1` / `PORT-10` number was measured on the sheet-less mesh, so the
opt-in sheet may not perturb it: the control asserts the recorded 79 534 cells,
cell tags `{1, 2, 3, 101, 102}`, facet tags `{1, 201, 202}`, and that the
sheet tags are *absent*.

**Printed, never gated:** the measured sheet extents — `w = 1.200000000e-02` m
transverse, `h = 7.977525299e-03` m along the current direction, and
`w/h = 1.504225878`, the "number of squares" a port impedance converts
through. The gap box crosses a round arc, so these are measured rather than
nominal. The `PORT-9` solve fixture is parameterised differently
(`w/h = 0.745249896`) and belongs to that chunk, not here.

Every constant is **imported** from `tests/mesh/test_two_torus_port_sheet.py`
and the `GEO-16` module it imports in turn (the `ANS-1` rule); nothing is
restated, so this example cannot drift from the gate it demonstrates.

**Mesh only — no port, no solve, no `Z` claim.** `PORT-9` is 🟡
(PROJECT_PLAN.md §2).

## 2. How to run it

```
./run_examples.sh -e mesh:4
```

Real DolfinX build (no complex mode needed); the runner selects it. Tier:
**standard**. On record at `-n 2`: sheet mesh **79 888 cells in 13.7 s**,
kwarg-off control **79 534 cells in 12.2 s**, **26.0 s** in-script total
including both ParaView exports — 30 s of harness wall clock, measured
2026-08-17, log `20260817T140242Z_EX-23-example-n2.log`. Add `-n <k>` to change
rank count and `-t <s>` to lower the per-example timeout.

Exit status 0 means both area identities *and* the inverted control held. A
non-zero exit is an assertion failure, not a rendering problem.

## 3. How to analyze it, step by step

**Step 1 — read the tag inventory before opening ParaView.** The script prints
the cell and facet groups it found. Expected:

- cell groups `1, 2, 3, 101, 111, 102, 112` — the gap boxes split in two.
  A set with `101`/`102` but no `111`/`112` means the fragment did not happen
  and the sheet is not a mesh entity at all.
- facet groups `1, 201, 202, 211, 212`. Missing `211`/`212` is the
  reconstruction failing; missing `201`/`202` means the sheet path *dropped*
  the pre-existing port groups, which would silently break `PORT-1`.

**Step 2 — check the identity, then the extents.** Read in this order:

1. **Facet counts.** 84 facets per sheet on record. Zero is the vacuous-pass
   failure mode the script guards against explicitly; a wildly different count
   at the same resolution means the mesh moved.
2. **meshed/CAD.** `1.000000000000` for both sheets. Anything off 1 by more
   than `1e-9` is a **regression against the `GEO-16` gate** — record it in the
   `EX-23` / `GEO-16` entries; never widen the band (PROJECT_PLAN §7, MAG
   table, defect 5).
3. **Out-of-plane spread.** `3.469e-18` m on record — the facet set really is
   a plane. A spread of order the cell size means the tag reconstruction
   picked up facets off the mid-plane, and the area identity would then be
   passing for the wrong reason.
4. **`w/h`.** `1.504225878` here. This is the geometric factor a port
   impedance converts through, so it is worth reading even though nothing
   gates it; the generator prints its own CAD-side value
   (`squares_w_over_h=1.504206917`) a few lines earlier, and the two agree to
   the arc-chord difference between the CAD surface and its triangulation.
5. **Port areas.** `1.563786482e-04` m² on both `201` and `202`, unchanged by
   the sheet — printed as a cross-check that the shared code path did not move.

**Step 3 — open the mesh in ParaView.** `File → Open →`
`examples/meshing/paraview_output/two_torus_port_sheet_combined.xdmf`, then
`two_torus_port_sheet_facets.xdmf` alongside it.

- In the `_combined` file, threshold the `CellTags` cell array: `1`/`2` are the
  two wires, `3` the air, and `101`/`111`, `102`/`112` are the lower and upper
  halves of each gap box. Threshold to `101` and `111` separately and put them
  side by side — the flat interface between them *is* the port sheet.
- In the `_facets` file, threshold the `mesh_tags` array to `211` or `212`.
  That is the surface itself: a flat rectangle sitting at `z = ±0.025` m
  inside the gap box, with the wire arc's cut ends (`201`/`202`) normal to it.

**Step 4 — what a deviation means.** Nothing is solved here, so every failure
mode is a geometry or tagging defect. The three to know:

- **Area off by ~2.5%** — the facet set is picking up the arc-end cuts rather
  than the mid-plane; that is the chordal deficit of the curved tube surface,
  and it means the tag reconstruction matched the wrong interface.
- **Control cell count off 79 534** — the opt-in sheet perturbed the default
  mesh. Every gated `PORT-1` / `PORT-10` number was measured on that mesh, so
  this invalidates them rather than just this example.
- **Hang at `-n 2`, no output** — the interior-facet assembly needs
  `create_entity_permutations` called on *every* rank, not only ranks owning
  tagged facets (known-issues 9: 180 s hang at `-n 2` against 22.5 s at
  `-n 1`). The helper this example imports already hoists that call.

## Related

- The gate itself: `tests/mesh/test_two_torus_port_sheet.py` (`GEO-16`).
- The port facets `201`/`202` and the helpers this example reuses:
  `tests/mesh/test_two_torus_port_facets.py` (`PORT-1` 3b-iv).
- What the sheet is *for*: `PORT-9` in PROJECT_PLAN.md §7 (lumped port), and
  the ports examples `examples/ports/01_two_torus_port_pair.md`,
  `examples/ports/02_package_sparameter_sweep.md`.
- The other mesh-only examples: `examples/meshing/01_two_torus_ports.md`,
  `examples/meshing/02_cylindrical_phantom.md`,
  `examples/meshing/03_birdcage_graded_conductors.md`.
- Group-level ParaView workflow: `examples/magnetostatics/PARAVIEW_GUIDE.md`.
