# `-e 2` — magnetic field of a circular current loop

Guide for `examples/magnetostatics/02_circular_loop.py`. Written to be followed
without the source open.

## 1. What this demonstrates

The magnetostatic solver on a circular loop coil — 1.0 A in a torus of major
radius 2 cm and wire radius 3 mm, inside a 6 cm air sphere — with the on-axis
`B_z` compared against the closed form for a filamentary loop,
`B_z(0) = μ₀I/2a`. This is the first example where the geometry is a **coil**
rather than a wire, so it is the closest magnetostatic analogue of the birdcage
target.

Two design choices carry the accuracy, and both are visible in the source
comments: the domain radius is **3× the loop radius**, because the natural
`n × H = 0` wall acts as a magnetic mirror and inflates the field when it is
close; and the outer boundary uses the **analytic Dirichlet** condition
(`exterior_dirichlet_bc`) — the `MAG-13` treatment — rather than the natural
wall that `-e 1` leaves in place. That is why this example lands an order of
magnitude closer to its closed form than the straight wire does.

On record at `-n 2` (`20260810T093203Z_EX-15-step1-refresh-allmag.log`,
2026-08-10):

| Quantity | Value |
| --- | --- |
| Mesh | **411 393 cells** (resolution 0.002 m) |
| `B_z` at centre, numerical | **2.974560e-05 T** |
| `B_z` at centre, analytic `μ₀I/2a` | **3.141593e-05 T** |
| Relative L2 error on the axis | **6.3046%** |
| Max relative error | **13.5037%** (at z = +0.0240 m) |
| Magnetic energy | **2.466288e-08 J** |

The gate for this physics is `MAG-13` (✅, heavy tier): the loop fixture in
`tests/validation/test_circular_loop.py` lands at **7.07%** with measured
convergence rate **1.10** (PROJECT_PLAN.md §7). This example is the
demonstration at its own resolution and sits in the same band — quote the
example's numbers as the example's, and `MAG-13`'s as the gate's.

## 2. How to run it

```
./run_examples.sh -e 2 -n 2 -t 180
```

Real DolfinX build; the runner selects it. Tier: **standard**. Cost is
dominated by meshing, not solving: 411 k cells at resolution 0.002 m means
~48 s in the gmsh optimiser alone on the 2026-08-10 record. The source notes
that relaxing the resolution to 0.0025 costs about 2% extra error — the trade
is documented in the parameter comments.

The VTX/`.bp` export was repaired 2026-08-10 (`EX-17`, the port of `EX-14`'s
straight-wire fix). A healthy run prints, on rank 0,

```
  VTX round-trip check (EX-17 anchor):
    in-memory  max|B| = 7.756122914931e-05 T
    read-back  max|B| = 7.756122914931e-05 T
    relative difference = 0.000e+00  (tol 1e-10)
```

— the written `circular_loop_B.bp` read back through ADIOS2 and compared with
the field still in memory (`20260810T200154Z_EX-17-gate-mag2.log`, exit 0,
124 s at `-n 2`). A mismatch raises rather than printing a warning. Before the
fix the run printed `⚠ VTX output failed (ADIOS2 may not be available)` on
every rank and left `circular_loop_A.bp` with zero ADIOS2 variables; if you see
that line, the tree predates the fix. Exit status 0 either way — the XDMF files
were always written.

## 3. How to analyze it, step by step

**Step 1 — check the centre field first.** `B_z(0)` numerical **2.974560e-05 T**
against analytic **3.141593e-05 T** is a **5.32%** deficit, and it is a
*deficit* for a physical reason: the loop is a torus of finite cross-section,
not a filament, so the current is spread over `a/R = 0.15` and the centre field
is biased low by `O((a/R)²)`. A centre field *above* the closed form is the
diagnostic to worry about — that is the mirrored-wall signature, and it means
the domain radius or the boundary condition changed.

**Step 2 — read the on-axis table.** The run prints five sample points and
writes the full sweep to `circular_loop_results.txt` in the working directory.
On record:

| z [m] | `B_z` num [T] | `B_z` ana [T] | error |
| --- | --- | --- | --- |
| −0.0240 | 7.990011e-06 | 8.242617e-06 | 3.06% |
| −0.0120 | 1.932907e-05 | 1.980804e-05 | 2.42% |
| 0.0000 | 2.974560e-05 | 3.141593e-05 | 5.32% |
| +0.0120 | 2.008817e-05 | 1.980804e-05 | 1.41% |
| +0.0240 | 7.129556e-06 | 8.242617e-06 | 13.50% |

What to look at: **the asymmetry between ±z.** The closed form is exactly
symmetric, so the difference between the −0.0240 error (3.06%) and the +0.0240
error (13.50%) is entirely numerical — mesh asymmetry plus the outer boundary,
worst at the largest |z| where the axis comes nearest the wall. A run whose
±z errors are equal would mean the mesh got symmetric (fine, and worth
recording); a run where the *inner* points (±0.0120) degrade instead is a
solver or gauge problem, since those are far from every boundary.

**Step 3 — check the energy.** **2.466288e-08 J** is the global scalar that
does not depend on where you sampled. It is the fastest check that a change was
harmless: pointwise on-axis values can stay put while the off-axis field moves.

**Step 4 — open the fields in ParaView.**
`File → Open → paraview_output/circular_loop_combined.xdmf` — one grid carrying
`CellTags`, `A`, `B` and `B_analytical`.

1. **Threshold** on `CellTags` to hide the conductor cells (the analytic
   comparison is only meaningful outside the torus).
2. **Stream Tracer** or **Glyph** on `B`, seeded on the axis. What to look at:
   closed field loops threading the torus, symmetric about the loop plane, with
   no flux appearing to originate at the outer wall.
3. **Plot Over Line** along the z axis with `B` — this reproduces the table in
   step 2 visually. (If you export it, ParaView names the CSV whatever you
   choose; the guides call that file `lineplot.csv` illustratively.)
4. **Calculator** `mag(B - B_analytical)`. What to look at: the error must peak
   at the conductor surface and at the outer wall, and be smooth in between.
   `B_analytical` here is the filamentary field, so large error *inside* the
   torus is expected and is not a defect.

**Step 5 — what a deviation means.** Centre field high → boundary/mirror;
centre field low beyond ~6% → wire cross-section or current density; on-axis
errors symmetric but all larger → resolution; errors erratic point to point →
the point-evaluation path (must be
`post.evaluation.evaluate_vector_field_parallel`, never `B.eval(points,
np.arange(n))`, and never a rank-local reduction).

## Related

- ParaView workflow for this group: `examples/magnetostatics/PARAVIEW_GUIDE.md`.
- Combined-file layout: `examples/magnetostatics/COMBINED_XDMF_README.md`.
- Two-coil version with a graded far field:
  `examples/magnetostatics/04_helmholtz_analytic_comparison.md`.
