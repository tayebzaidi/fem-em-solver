# `mesh:3` — graded conductor sizing on the birdcage fixture

Guide for `examples/meshing/03_birdcage_graded_conductors.py` (`EX-21`).
Written to be followed without the source open.

## 1. What this demonstrates

The **first birdcage example of any kind** in this repo, and the angle
`GEO-15` owes. That chunk gated *graded conductor sizing* — a gmsh
Distance→Threshold background field that refines only on and near the
conductor surfaces, leaving the air box at the global size — and until now
nothing you could open in ParaView showed it.

The script builds the same fixture twice and asserts the difference:

| Rung | Sizing | What it is |
| --- | --- | --- |
| control | `conductor_resolution = BASELINE_CONTROL_RESOLUTION` = 4.8 mm | the negative control, printed first |
| graded | `conductor_resolution = 0.4 × ring_minor_radius` = 1.6 mm | the gated capability |

### ⚠️ The claim was demoted on 2026-08-26 — read this before citing the example

The control was one global `setSize = 0.015` with **no conductor grading at
all**, and the comparison was therefore *graded vs ungraded*: the form in which
`GEO-15` answered the `PORT-9`-prerequisite question. On the 0.11 image
(dolfinx 0.11 / gmsh 4.15.2) the ungraded build stopped meshing — gmsh aborts
with `Invalid boundary mesh (overlapping facets)` before the graded rung ever
runs — so this example and the gate it imports were red and **non-executing on
`main` from the 0.11 merge until `GEO-21` disposed of it** (2026-08-26).

Every meshable replacement control is itself graded. What this example
demonstrates is now **fine vs coarse conductor grading** — still quantitative,
still monotone, still a real separation, but **no longer evidence that grading
is *required***. That stronger claim closed on the 0.7.2 image (`GEO-15`,
2026-08-16: 0.740335 ungraded vs 0.967019 graded) and stays closed there; do
not restate it from this example's present numbers. The generator limitation
behind the demotion — coarse conductor sizings, `None` included, cannot mesh on
0.11 — is open in `docs/testing/known-issues.md` and deliberately not
commissioned for a fix while no production path uses it.

There is **no solve**. The birdcage has no port model yet (`PORT-9`,
PROJECT_PLAN.md §2), so nothing here is a port or S-parameter claim; the
script needs only the real DolfinX build.

### The quantity, and why it is that one

Not "does it look finer". The measured number is the fraction of the
conductor's **CAD (occ) mass** that survives into the mesh.

The obvious denominator — the analytic ring + leg sum — is wrong for this
question: it double-counts the eight leg∩ring junctions, so it never reaches
1 no matter how fine the mesh, and the deficit it reports is *two* effects
tangled together. The CAD mass of the conductor physical group counts every
fragment piece exactly once, so it tends to 1 under refinement and the deficit
against it is **resolution alone**. That is what makes grading measurable.

| Assertion | Gate | On record (0.11 image, 2026-08-26) | Superseded (0.7.2, 2026-08-16) |
| --- | --- | --- | --- |
| graded meshed/CAD ≥ `CAD_MASS_GATE` (0.95) | `GEO-15` | **0.966977** | 0.967019 |
| control meshed/CAD **fails** 0.95, by ≥ 0.05 | inverted control | **0.846150** | 0.740335 (ungraded) |
| `GEO-9` box partition, both rungs | `GEO-9` | ratios = 1 to `1e-9` | same |
| conductor CAD mass identical across rungs | premise | to `1e-12` | same |

The separation between the two rungs (**0.120826** on record, was 0.226685 with
the ungraded control) is the point of the control: a gate a coarse mesh already
clears measures nothing. The script asserts the control *fails*, in the
`EX-18` / `EX-20` inverted-assertion pattern, so a regression that silently
disabled grading would turn this example red rather than leaving it green on
the fallback.

`BASELINE_CONTROL_RESOLUTION` = 4.8 mm was chosen **measure-first** by `GEO-21`
step 1 and ruled by the 2026-08-26 03:00 review; the gate module's comment on
that constant carries the full six-rung probe table (9.6 mm still FAILs, 6.4 mm
was rejected for cliff adjacency, 3.2 mm reads 0.916742 and would itself fail
the 0.05 separation guard). `CAD_MASS_GATE`, the 0.05 guard and the rung ladder
are unmoved — the control moved, the gate did not.

The `GEO-9` identities are re-asserted on **both** rungs because grading
changes element sizes, not geometry: a partition identity that moves is a
defect in the size field (a piece lost its physical group, or a region got
meshed twice), not a resolution effect. Same reason the CAD mass itself is
checked identical across rungs — if the denominator moved, neither ratio
means anything.

Every constant — fixture parameters, the rung ladder, the gate, the `GEO-9`
identity checks — is **imported** from
`tests/mesh/test_birdcage_conductor_sizing.py`, the module that gated them
(the `ANS-1` rule). The example cannot drift from the gate it demonstrates.

## 2. How to run it

```
./run_examples.sh -e mesh:3
```

Real DolfinX build (no complex mode needed); the runner selects it. Tier:
**standard**. On record at `-n 2` on the 0.11 image: control **33 185 cells /
6.43 s mesh**, graded **98 666 cells / 18.32 s mesh**, **27.7 s total**
including both ParaView exports (measured 2026-08-26,
`20260826T093403Z_GEO-21-step2-mesh3.log`, Status 0). Superseded record on
0.7.2 with the ungraded control: baseline 48 245 cells / 6.1–6.3 s mesh, graded
98 474 cells / 16.7 s mesh, 26 s total (`20260816T200348Z_EX-21-example-n2.log`,
`20260816T200516Z_EX-21-example-n2-final.log`). Add `-n <k>` to change rank
count and `-t <s>` to lower the per-example timeout.

Exit status 0 means the gate *and* the inverted control both held. A non-zero
exit is an assertion failure, not a rendering problem.

## 3. How to analyze it, step by step

**Step 1 — read the two-row table before opening ParaView.** The script
prints the CAD-mass denominator, then one line per rung with `h_c`, cell
count, `meshed/CAD`, and mesh wall time. Check, in order:

1. **The denominator.** Both rungs must report the same conductor CAD mass
   (asserted to `1e-12`). If they differ, the size field changed the
   geometry — a gmsh bug or a mis-set `Mesh.MeshSizeFrom*` switch — and
   everything below is meaningless.
2. **The control.** The coarse-graded control's `meshed/CAD` on record is
   `0.846150`. A control that has crept up toward 0.95 means the sizing moved
   underneath the example; the gate stops discriminating and the script says
   so in the failure message rather than passing quietly.
3. **The gate.** Graded `meshed/CAD` on record is `0.966977`. Below 0.95 is a
   finding to record in the `EX-21` / `GEO-15` entries — **never** a reason to
   move the gate (PROJECT_PLAN §7, MAG table, defect 5).
4. **The cell counts.** Refining the conductor grading 4.8 mm → 1.6 mm costs
   **2.97×** the cells here (33 185 → 98 666) and **2.85×** the mesh time
   (6.43 s → 18.32 s). That 98 k is exactly the figure the `PORT-9` entry
   budgets its birdcage solves from (PROJECT_PLAN §7, `PORT-9`): a graded
   birdcage is not free, and every solve on it pays this cell count.

**Step 2 — open the two meshes side by side.** In ParaView:
`File → Open → examples/meshing/paraview_output/birdcage_graded_conductors_baseline_combined.xdmf`,
then the same for
`examples/meshing/paraview_output/birdcage_graded_conductors_graded_combined.xdmf`.
Apply a **Threshold** on the
`CellTags` cell array in each:

- `1` = conductor (the two rings and the four legs),
- `2` = air, `3` = phantom,
- `101`–`104` = the four leg port boxes.

Threshold both to `1` alone and put the two views next to each other. What to
look at: at the control's 4.8 mm conductor size the ring's circular
cross-section (minor radius 4 mm) is barely resolved — roughly one cell across
the radius — so the ring renders as a coarsely **faceted** tube that visibly
under-fills its own volume, and that is the 0.846150 made visible. The graded
rung resolves the same cross-section with 1.6 mm cells and the tube is round.
The leg∩ring junctions are the worst region in the control and the most
improved in the graded rung. (Both files are graded meshes now; the *air* looks
the same in each, and only the conductor shell differs.)

**Step 3 — check that grading stayed local.** Threshold to `2` (air) in the
graded file. The fine cells must sit in a thin skin around the conductor and
the far air must look like the control's air: the background field's
`SizeMax` *is* the global `resolution`, so a graded mesh whose air box is also
refined means the threshold distance (default `3 × ring_minor_radius`) or the
`SizeMax` is wrong, and the cell count will have exploded well past the
98 666 on record.

**Step 4 — what a deviation means.** Every failure mode here is a *geometry*
defect, because nothing is solved. The three gmsh switches
`Mesh.MeshSizeFromPoints`, `Mesh.MeshSizeFromCurvature` and
`Mesh.MeshSizeExtendFromBoundary` must all be off or gmsh silently re-imposes
the coarse size on top of the background field — that is the trap `GEO-15`
named, and its signature is a graded rung whose `meshed/CAD` barely moves off
the control. Read the `GEO-15`, `GEO-21` and `GEO-9` entries in
PROJECT_PLAN.md §7 before debugging; a mesh that does not build at all is the
coarse-sizing generator limitation in `docs/testing/known-issues.md`, not a
switch.

## Related

- The gate itself: `tests/mesh/test_birdcage_conductor_sizing.py` (`GEO-15`).
- The partition identities: `tests/mesh/test_birdcage_port_tags.py` (`GEO-9`).
- The other mesh-only examples:
  `examples/meshing/01_two_torus_ports.md`,
  `examples/meshing/02_cylindrical_phantom.md`.
- Group-level ParaView workflow: `examples/magnetostatics/PARAVIEW_GUIDE.md`.
