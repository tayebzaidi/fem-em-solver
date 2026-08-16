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
| baseline | one global `setSize = 0.015` | the negative control, printed first |
| graded | `conductor_resolution = 0.4 × ring_minor_radius` = 1.6 mm | the gated capability |

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

| Assertion | Gate | On record (`GEO-15`) |
| --- | --- | --- |
| graded meshed/CAD ≥ `CAD_MASS_GATE` (0.95) | `GEO-15` | **0.967019** |
| baseline meshed/CAD **fails** 0.95, by ≥ 0.05 | inverted control | **0.740335** |
| `GEO-9` box partition, both rungs | `GEO-9` | ratios = 1 to `1e-9` |
| conductor CAD mass identical across rungs | premise | to `1e-12` |

The separation between the two rungs (**0.2267** on record) is the point of
the control: a gate a coarse mesh already clears measures nothing. The script
asserts the baseline *fails*, in the `EX-18` / `EX-20` inverted-assertion
pattern, so a regression that silently disabled grading would turn this
example red rather than leaving it green on the fallback.

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
**standard**. On record at `-n 2`: baseline **48 245 cells / 6.1–6.3 s mesh**,
graded **98 474 cells / 16.7 s mesh**, **26 s total** including both ParaView
exports (measured 2026-08-16, logs
`20260816T200348Z_EX-21-example-n2.log` and
`20260816T200516Z_EX-21-example-n2-final.log` — cell counts and ratios
identical across both, only wall times move). Add `-n <k>` to change rank
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
2. **The control.** Baseline `meshed/CAD` on record is `0.740335`. A baseline
   that has crept up toward 0.95 means the global resolution changed
   underneath the example; the gate stops discriminating and the script says
   so in the failure message rather than passing quietly.
3. **The gate.** Graded `meshed/CAD` on record is `0.967019`. Below 0.95 is a
   finding to record in the `EX-21` / `GEO-15` entries — **never** a reason to
   move the gate (PROJECT_PLAN §7, MAG table, defect 5).
4. **The cell counts.** Grading costs **2.04×** the cells here
   (48 245 → 98 474) and **~2.7×** the mesh time (6.1–6.3 s → 16.7 s). That 98 k
   is exactly the figure the `PORT-9` entry budgets its birdcage solves from
   (PROJECT_PLAN §7, `PORT-9`): a graded birdcage is not free, and every
   solve on it pays this cell count.

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
look at: at the global size the ring's circular cross-section (minor radius
4 mm) is resolved by cells ~15 mm across, so the ring renders as a coarsely
**faceted** tube that visibly under-fills its own volume — that is the
0.740335, made visible. The graded rung resolves the same cross-section with
1.6 mm cells and the tube is round. The leg∩ring junctions are the worst
region in the baseline and the most improved in the graded rung.

**Step 3 — check that grading stayed local.** Threshold to `2` (air) in the
graded file. The fine cells must sit in a thin skin around the conductor and
the far air must look like the baseline's air: the background field's
`SizeMax` *is* the global `resolution`, so a graded mesh whose air box is also
refined means the threshold distance (default `3 × ring_minor_radius`) or the
`SizeMax` is wrong, and the cell count will have exploded well past the
98 474 on record.

**Step 4 — what a deviation means.** Every failure mode here is a *geometry*
defect, because nothing is solved. The three gmsh switches
`Mesh.MeshSizeFromPoints`, `Mesh.MeshSizeFromCurvature` and
`Mesh.MeshSizeExtendFromBoundary` must all be off or gmsh silently re-imposes
the coarse size on top of the background field — that is the trap `GEO-15`
named, and its signature is a graded rung whose `meshed/CAD` barely moves off
the baseline. Read the `GEO-15` and `GEO-9` entries in PROJECT_PLAN.md §7
before debugging.

## Related

- The gate itself: `tests/mesh/test_birdcage_conductor_sizing.py` (`GEO-15`).
- The partition identities: `tests/mesh/test_birdcage_port_tags.py` (`GEO-9`).
- The other mesh-only examples:
  `examples/meshing/01_two_torus_ports.md`,
  `examples/meshing/02_cylindrical_phantom.md`.
- Group-level ParaView workflow: `examples/magnetostatics/PARAVIEW_GUIDE.md`.
