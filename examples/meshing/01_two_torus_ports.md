# `mesh:1` — the gapped two-torus port fixture

Guide for `examples/meshing/01_two_torus_ports.py` (`EX-1`). Written to be
followed without the source open.

## 1. What this demonstrates

The **geometry and tag structure** of the two-torus port fixture — two coaxial
wire tori inside an air box, each torus interrupted by a rectangular *gap box*
where a port would be driven. Every other example in this repo shows a solved
field; this one shows the mesh you have to look at in ParaView when a `PORT-1`
number comes out wrong.

There is **no solve** here. Port voltages and S-parameters are ungated
(`PORT-1` is 🟡, PROJECT_PLAN.md §2) and deliberately absent; the script needs
only the real DolfinX build.

What anchors it — three closed-form identities, all MPI-allreduced, each one a
landed gate re-executed on the example's own mesh:

| Identity | Gate | Closed form | Band |
| --- | --- | --- | --- |
| Summed `outer_boundary` (facet tag `1`) area / box surface | `GEO-10` | `2(LW + LH + WH)` | ratio = 1 to `1e-9` |
| Total mesh volume / box volume, and the five tagged volumes summed to the total | `GEO-8` | `L·W·H` | ratio = 1 to `1e-9` |
| Each gap-box volume | `PORT-1` step 3b-i | `dx·dy·dz` | ratio = 1 to `1e-9` |

These are identities, not tolerance bands with slack in them: the box walls and
the gap boxes are planar, so a linear-tet mesh partitions them **exactly**. A
deviation in the tenth digit is a real defect, not discretisation.

**Negative controls, on record, not re-run by the script.** Before `GEO-8`
(2026-08-01) the fixture never fragmented — gmsh meshed the box solid through
the torus regions and the tori as two disconnected islands, so the volume ratio
read `1.002633` (tori counted twice) and a source restricted to torus 1 gave
`Z12 == 0` *exactly*, because the field could not leave its island (`PORT-1`
step-1 logs `20260731T213222Z_…`, `…213423Z_…meshconformity.log`). Before
`GEO-10` (2026-08-06) the `outer_boundary` physical group never reached the
dolfinx facet tags: the ungapped global facet-tag set was `[]` and the gapped
one `[201, 202]` (known-issues 10). **Both defects render perfectly.** Only the
identities above catch them — which is the reason this example asserts rather
than merely exports.

## 2. How to run it

```
./run_examples.sh -e mesh:1
```

Real DolfinX build (no complex mode needed); the runner selects it. Tier:
**standard**. On record at `-n 2` on the **0.11 image** (dolfinx 0.11 /
gmsh 4.15.2): **79 070 cells, mesh built in 14.1 s, 14.2 s total** (measured
2026-08-26, log `20260826T033431Z_GEO-16-rerecord-mesh1.log`; the 0.7.2 image
meshed 79 534 cells in 12.9 s,
13.1 s total, measured 2026-08-06; the −0.58% move is the documented image
change, ruled re-recordable 2026-08-25). Add `-n <k>`
to change rank count and `-t <s>` to lower the per-example timeout.

Exit status 0 means every identity above passed. A non-zero exit is an
assertion failure, not a rendering problem.

## 3. How to analyze it, step by step

**Step 1 — read the printed report before opening ParaView.** The three
identities print as ratios. Check, in order:

1. `outer_boundary` area ratio — on record `1.000000000000`. Anything that
   differs before the ninth decimal means the facet tags no longer cover the
   box walls: suspect the physical-group → dolfinx facet-tag path first
   (that is exactly what known-issues 10 was).
2. Total volume ratio = 1 and the five tagged volumes summing to the total,
   both to `1e-9`. A ratio near `1.0026` is the pre-`GEO-8` non-fragmentation
   signature — the tori are being counted twice, i.e. the box was meshed solid
   through them and the tags no longer partition the domain.
3. Each gap-box volume against `dx·dy·dz`. A miss here means the gap box did
   not survive the boolean fragmentation, so there is no port cut to drive.

**Step 2 — open the cell tags.** In ParaView:
`File → Open → examples/meshing/paraview_output/two_torus_ports_combined.xdmf`.
Apply a **Threshold** on the `CellTags` cell array:

- `1` = wire torus 1, `2` = wire torus 2, `3` = air,
- `101` / `102` = the two gap boxes.

What to look at: each torus must be a **single closed ring interrupted only by
its gap box**, and the gap boxes must sit *in* the ring, sharing faces with it
— not floating in air and not overlapping the wire. Threshold to `101` alone
and it should be a rectangular solid spanning the wire cross-section.

**Step 3 — open the facet tags.** Open
`examples/meshing/paraview_output/two_torus_ports_facets.xdmf` alongside it and
colour by the `mesh_tags` array: `1` = outer boundary, `201` / `202` = the port
cuts. What to look at: tag `1` must cover **all six box walls** with no holes
(a hole is the visual form of a wall-area ratio below 1), and `201`/`202` must
be flat disks cutting the wire, one per gap, coincident with a gap-box face.

**Step 4 — what a deviation means.** An identity that fails while the render
looks fine is the normal failure mode of this fixture, and it is a *geometry*
defect (fragmentation, physical groups, tag propagation) — not a solver
defect, because nothing is solved here. Read known-issues.md entry 10 and the
`GEO-8` / `GEO-10` entries in PROJECT_PLAN.md §7 before debugging: both classes
of failure have occurred and are documented with their signatures.

## Related

- Group-level ParaView workflow: `examples/magnetostatics/PARAVIEW_GUIDE.md`.
- Mesh diagnostics: `examples/magnetostatics/MESH_DIAGNOSTIC_GUIDE.md`.
- The cylindrical counterpart: `examples/meshing/02_cylindrical_phantom.md`.
