# `mesh:5` — the region-resolution policy on the coil+phantom mesh

Script: [`05_region_resolution_policy.py`](05_region_resolution_policy.py) ·
gate: `tests/mesh/test_mesh_tag_integrity.py` (`GEO-17`) · chunk: `EX-27`

## 1. What this demonstrates

The first example in this repo whose subject is a **mesh sizing policy** rather
than a field, a geometry or an output quantity. `mesh:3` (`EX-21`) grades one
conductor by an explicit `h_c`; this one asks `coil_phantom_domain` for a
*different characteristic length per tagged region* — coil 0.012 m, phantom
0.010 m, air 0.020 m — instead of one global 0.015 m, and measures what the
mesh does about it.

### Why the example exists

`OPS-17` step 2 (2026-08-17) measured the policy **losing** 21.68% / 22.62% of
the two coil volumes while asking for a *finer* coil size — a sign an inscribing
linear-tet mesh cannot produce by refinement. `GEO-17` step 1 (2026-08-20)
diagnosed it: the per-region point walk went through `gmsh.model.getBoundary`
with the default `combined=True`, whose result for a volume's closed shell is
empty, so **all four regions collected zero points and `mesh.setSize` was never
called once**. The only surviving sizing authority was the global
`CharacteristicLengthMin/Max` clamps, which under the policy are
`[0.010, 0.020]` — so the "refined" coil was meshed at the *air's* 0.020
ceiling. The fix is a `Min` over four per-volume `Constant` size fields
(`VolumesList` + `IncludeBoundary=1`, `VOut = 1e22`) installed as the background
mesh, so a region's request bounds the size on its own boundary and a shared
curved interface takes the finer of its two neighbours.

That fix is gated by a test. This script is the thing you can open.

### The quantity, and why the sign of the move is an identity

Not "does it look finer": the fraction of each curved region's **analytic CAD
volume** that survives into the mesh — two tori `2 π² R r²` and a cylinder
`π r² h`. A linear-tet mesh *inscribes* a curved surface, so the ratio is
bounded above by 1 and rises monotonically with refinement. Refinement moving a
curved region's volume **up** is therefore an identity, not a band.

This matters because `GEO-17` step 1 **replaced a band with its measurement**
(the `MAG-10`/`MAG-15` precedent). The old gate asserted the two sizings agreed
to 5%, on the premise that region sizing "must not move the geometry". That
premise is false for a curved region: a real 0.015 → 0.012 refinement of a torus
of minor radius 0.01 *must* move the volume, and by more than 5% (+10.72%
measured). The old band would now reject a correct mesh.

### What is gated here

| | on record | where it comes from |
|---|---|---|
| policy coil meshed/CAD ≥ `POLICY_MIN_CAD_RECOVERY` = 0.755 | **0.835563 / 0.833730** | imported from the `GEO-17` module |
| clamps-only coil meshed/CAD **< 0.755** (inverted control) | **0.754685 / 0.752565** | derived from imported `UNIFORM_VOLUMES_RECORD` ÷ `CAD_VOLUMES` |
| separation between the two sizings ≥ `SIZING_SEPARATION` = 0.05 | **+0.080879 / +0.081165** | measured here |
| policy volume > clamps-only volume on every refined tag (1, 2, 3) | +10.7169% / +10.7851% / +0.9374% | the sign identity |
| air (the one coarsened region) *loses* volume | −0.2643% | the volume has to come from somewhere |
| meshed/CAD ≤ 1 on both meshes, all three curved tags | max 0.992751 | the inscription bound |
| tagged-volume partition = 1 to `VOLUME_PARTITION_BAND` (1e-9) on **both** meshes | `1.000000000000` | imported helper |
| clamps-only table unmoved from the `OPS-17` record to 1e-9 | 4/4 tags | imported `UNIFORM_VOLUMES_RECORD` |

The inverted control is thin **by construction** and the script says so: the
0.755 floor was pre-registered as "the uniform mesh's own recovery, which a
finer request must beat", so it sits ~3.2e-4 above the control it inverts. On
its own that assertion would pass even if the policy did almost nothing, which
is why `SIZING_SEPARATION` is gated separately — that margin is the one that
discriminates.

Every gate above is **imported** from `tests/mesh/test_mesh_tag_integrity.py`
(the `ANS-1` rule), including the policy sizes themselves. The two policy
*recovery* records (0.835563 / 0.833730) are restated in the script with their
log provenance and reproduced inside a pre-stated 1% band, because the gate
holds them as printed output rather than as named constants — the `EX-26`
precedent.

**Mesh only — no solve, no SAR claim.** This is the mesh capability `MAT-4`'s
SAR-on-a-coil route runs through, and nothing downstream of it.

## 2. How to run it

```
./run_examples.sh -e mesh:5
```

Real DolfinX build (no complex mode needed); the runner selects it. Commissioned
**standard**, measured **smoke**: on record at `-n 2`, clamps-only **19 792
cells in 2.89 s**, policy **20 843 cells in 2.38 s**, **5.4 s** in-script total
including both ParaView exports — 8 s of harness wall clock, measured
2026-08-22, log `20260822T033345Z_EX-27-example-n2.log`. Add `-n <k>` to change
rank count and `-t <s>` to lower the per-example timeout.

Exit status 0 means the gate, the inverted control, the sign identity and both
partition identities all held. A non-zero exit is an assertion failure, not a
rendering problem.

## 3. How to analyze it, step by step

**Step 1 — read the two partition blocks before anything else.** The script
prints `[EX-27 clamps_only]` and `[EX-27 policy]` tagged-volume partitions, each
ending in `ratio 1.000000000000`. If either misses 1e-9, stop: a region lost its
physical group or got meshed twice, and every ratio below is then being computed
on a mesh that does not partition its own volume. That is a defect in the size
field, not a resolution effect — sizing changes element sizes, not geometry.

**Step 2 — check the clamps-only column against the `OPS-17` record.** The four
tagged volumes must reproduce `UNIFORM_VOLUMES_RECORD` to 1e-9. This is the
negative control on the fix itself: the `Min`-field change must not touch a mesh
that asks for one size everywhere. A move here means the fix leaked into the
uniform path, and the comparison in step 3 no longer has a fixed baseline.

**Step 3 — read the volume table, watching the signs.** Expected:

```
  tag 1 (coil_1  ) 1.191750413e-04 -> 1.319468693e-04 m^3  (+10.7169%)
  tag 2 (coil_2  ) 1.188402981e-04 -> 1.316573175e-04 m^3  (+10.7851%)
  tag 3 (phantom ) 4.943767949e-04 -> 4.990112950e-04 m^3  ( +0.9374%)
  tag 4 (air     ) 1.143560787e-02 -> 1.140538452e-02 m^3  ( -0.2643%)
```

Three plus signs and one minus, and the minus is on the one region the policy
**coarsens**. That pattern is the whole claim: the refined regions grow toward
their CAD, and the volume they gain comes out of their coarsened neighbour. A
plus on the air, or a minus on a coil, is the `OPS-17` defect returning.

The phantom moves only +0.94% because it is a cylinder whose flat faces and
straight generators are already resolved exactly — it starts at 0.9835
recovery, so there is little left to recover. The tori, curved in both
directions, are where the policy earns its cost.

**Step 4 — read the recovery block, and check the separation, not just the
floor.**

```
  tag 1 (coil_1  ) CAD 1.579136704e-04 m^3  clamps 0.754685 -> policy 0.835563  (separation +0.080879)
  tag 2 (coil_2  ) CAD 1.579136704e-04 m^3  clamps 0.752565 -> policy 0.833730  (separation +0.081165)
```

Read the separation column first. The floor (0.755) is cleared by the policy by
0.08 and missed by the control by 0.0003, so "policy ≥ floor > control" is true
but nearly vacuous on the control side; the 0.08 separation is what says the
policy did something. Both readings share a denominator that is analytic, so
neither can drift from a mesh artifact in the other.

Recovery `> 1` on any tag is a hard failure the script asserts on: a linear-tet
mesh cannot contain more volume than the curved CAD it inscribes, so a ratio
above 1 means the CAD volume in `CAD_VOLUMES` no longer describes the geometry
being meshed.

**Step 5 — open both meshes in ParaView.** In
`examples/meshing/paraview_output/`:

```
region_resolution_policy_clamps_only_combined.xdmf
region_resolution_policy_policy_combined.xdmf
```

Threshold on `CellTags` (1 = coil_1, 2 = coil_2, 3 = phantom, 4 = air) and open
the two side by side. Threshold to `1 ≤ CellTags ≤ 2` in both: the tori are
visibly faceted under the clamps and round under the policy — that difference is
the 8 points of CAD recovery, made visual. Then threshold to `CellTags = 4` and
look at the air: it is coarser in the policy mesh, and the cell counts (19 792 →
20 843) show the trade is nearly free — the policy buys torus fidelity by
spending the air, for ~5% more cells.

**Step 6 — if a number moved.** A drift outside the pre-stated bands is an
example-path regression against a gated capability. Record the measured value in
the `EX-27` / `GEO-17` entries and open a `docs/testing/known-issues.md` entry;
never widen a band to make the example green (PROJECT_PLAN §7, MAG table,
defect 5).

## Related

- `mesh:3` (`EX-21`) — graded conductor sizing on the birdcage fixture: one
  conductor, an explicit `h_c`, a Distance→Threshold field. The neighbouring
  angle, on a different fixture and a different mechanism.
- `mesh:2` (`EX-2`) — the cylindrical phantom fixture.
- PROJECT_PLAN.md §7 `GEO-17` — the diagnosis, the fix, and the band that was
  replaced with its measurement.
- `docs/testing/known-issues.md`, "Four defects…" §1 — where the uniform-sizing
  volume table this example re-asserts was first recorded.
