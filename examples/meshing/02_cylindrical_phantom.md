# `mesh:2` — the cylindrical phantom domain, classified and tagged

Guide for `examples/meshing/02_cylindrical_phantom.py` (`EX-2`). Written to be
followed without the source open.

## 1. What this demonstrates

The **cylindrical** geometry the birdcage path runs through: a curved outer
wall with a phantom cylinder inside it, and the **boundary classification**
that decides which surfaces become `outer_boundary`. `mesh:1` shows a
box-bounded fixture where every wall is planar; this one shows what changes
when the wall is curved, and it is honest about the fact that a linear-tet mesh
*inscribes* a curved surface rather than matching it.

There is **no solve**: fields, ports and SAR are out of scope here. Real
DolfinX build only.

What anchors it:

- **`GEO-13` — the live two-sided classification margin**, recomputed on the
  example's own CAD model with `_WALL_TOL_FRACTION` imported from the
  generator, exactly as `tests/mesh/test_boundary_classification_margins.py`
  does. On record: **3 of 6 surfaces accepted**, worst accepted at
  `1.111111e-04 × tol` (ceiling `0.1`), nearest rejected at `9.999989e+01 × tol`
  (floor `10`).
- **An exact partition identity** — the two tagged volumes sum to the mesh
  total to `1e-9`. Linear tets partition exactly whether or not the boundary is
  curved.
- **Closed-form volumes and areas with the curvature stated honestly.** Every
  meshed/analytic ratio on the curved wall is strictly below 1; `GEO-12`'s
  planar `1e-15` does **not** transfer here. Where the outer wall is resolved
  the deficit is the O(h²) chordal loss and the ratio sits in `(0.98, 1)`.
- **The inner cylinder is under-resolved by construction, and the example says
  so in closed form.** At the defaults the cell size `0.02` is *twice* the
  inner radius `0.01`, so gmsh falls back to its minimum circle discretisation
  (7 nodes) and the inner cylinder meshes as a **heptagonal prism**. The
  end-cap area ratio is therefore the inscribed-heptagon value
  `(7/2π)·sin(2π/7) = 0.8710264`, hit to **1.11e-16 relative** — the cap is not
  approximately that polygon, it *is* that polygon. The inner *volume* ratio
  falls further, to `0.718170`, as the lateral triangulation cuts inside the
  prism; it is bracketed between the degenerate-square floor `2/π` and the
  heptagonal-prism ceiling.

**Negative control, on record, not re-run by the script.** Before `GEO-13`
(2026-08-07) the predicate used `tol = resolution`, keying a *geometric*
classification to *mesh size*. At `resolution = 0.09` it accepted **6 of 6**
surfaces — sweeping the inner cylinder whole into `outer_boundary` — and even
at the defaults the interior margin was only `4.50×` the tolerance, under the
`10×` floor (`20260807T033127Z_GEO-13-probe.log`, known-issues 13, now
retired). A rendering shows none of that; the margins do.

## 2. How to run it

```
./run_examples.sh -e mesh:2
```

Real DolfinX build; the runner selects it. Tier: **standard**, but this is a
mesh-only case. On record at `-n 2`: **5 717 cells, mesh built in 0.7 s**
(measured 2026-08-07, recorded in the script docstring).

Exit status 0 means the margin, the partition identity and every closed-form
ratio above held.

## 3. How to analyze it, step by step

**Step 1 — read the classification margins first.** They are the reason this
example exists. Two numbers matter, both dimensionless multiples of the
tolerance:

- **worst accepted** — on record `1.111111e-04 × tol`, and the gate ceiling is
  `0.1`. A value creeping toward 0.1 means a surface that *should* be on the
  outer wall is barely making it; at 1.0 it stops being classified at all.
- **nearest rejected** — on record `9.999989e+01 × tol`, floor `10`. A value
  dropping toward 10 means an *interior* surface is approaching acceptance;
  below 10 you are back in the pre-`GEO-13` regime where the inner cylinder
  gets swallowed into `outer_boundary`.

Also check the accepted count: **3 of 6**. A `6 of 6` reading is the exact
pre-`GEO-13` signature.

**Step 2 — check the ratios in the printed report.** Expected, at the
defaults:

| Quantity | On record | Why not 1 |
| --- | --- | --- |
| Tagged volumes summed / mesh total | 1 to `1e-9` | exact — linear tets partition |
| Outer wall (resolved) meshed/analytic | in `(0.98, 1)` | O(h²) chordal inscription |
| Inner cap area / πr² | `0.8710264` (to `1.11e-16`) | 7-node circle → inscribed heptagon |
| Inner volume / πr²h | `0.718170` | lateral triangulation cuts inside the prism |

A ratio **above 1** anywhere is a defect, not noise: an inscribed mesh cannot
exceed the smooth object.

**Step 3 — open the cell tags.** `File → Open →
examples/meshing/paraview_output/cylindrical_phantom_combined.xdmf`, then
**Threshold** on `CellTags`: `1` = inner phantom cylinder, `2` = surrounding
domain. What to look at: threshold to `1` alone and you should clearly see a
**heptagonal prism**, not a cylinder — that is the point of the `0.8710264`
number above, made visible. Seeing a smooth cylinder at these defaults would
mean the mesh size or the generator defaults changed.

**Step 4 — open the facet tags.** Open
`examples/meshing/paraview_output/cylindrical_phantom_facets.xdmf` and colour
by `mesh_tags`: `1` = `outer_boundary`, `2` = `inner_boundary`. What to look
at: tag `1` must be the outer curved wall **plus its two end caps and nothing
else**; if any part of the inner prism carries tag `1`, the classification has
regressed to the pre-`GEO-13` behaviour and the margins in step 1 will already
have said so.

**Step 5 — what a deviation means.** A margin failure is a *predicate* defect
(the classification rule), a ratio failure on the outer wall is a *resolution*
defect (mesh size vs curvature), and a failure of the partition identity is a
*tagging* defect (cells claimed twice or not at all). They are three different
bugs and the report tells you which one you have before you open ParaView.

## Related

- The box-bounded counterpart: `examples/meshing/01_two_torus_ports.md`.
- Mesh diagnostics: `examples/magnetostatics/MESH_DIAGNOSTIC_GUIDE.md`.
