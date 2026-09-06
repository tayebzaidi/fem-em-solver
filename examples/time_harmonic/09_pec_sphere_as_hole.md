# `-e th:9` — the conductor as a hole: PEC sphere cut from the mesh

Guide for `examples/time_harmonic/09_pec_sphere_as_hole.py`. Written to be
followed without the source open.

## 1. What this demonstrates

**A boundary condition standing in for a conductor, rather than a material
setting a field.** `th:3` (`EX-6`) shows a sphere **solved inside** the mesh,
where `ε` sets the interior field the assembly produces. This example takes
the opposite geometry/boundary-condition angle: the sphere's cells are cut
from the mesh entirely (`MeshGenerator.sphere_in_box_domain(as_hole=True)`),
its surface arrives as its own facet tag, and the homogeneous tangential
condition `n × E = 0` on that facet tag is what stands in for a perfectly
conducting sphere — no material, no interior mesh, no interior field at all.

Outside the (absent) sphere the exact solution is `th:3`'s own uniform-plus-
dipole pair, at the perfect-conductor limit of the dipole coefficient:

```
E_out = E0 zhat + beta E0 R^3 (3 (zhat.rhat) rhat - zhat) / r^3,  beta = 1
```

(the dielectric's `beta = (eps-1)/(eps+2)` as `eps -> inf`; that limit is
never reached by passing `eps = inf` into `th:3`'s callable, where the
expression is `nan` — this is a distinct closed form, PEC from the start).
On the sphere surface the tangential field vanishes, which is exactly what
makes `n × E = 0` on the cavity wall the *same* closed form and not an extra
piece of data.

The fixture — geometry, resolution, bands, and every callable — is *imported*
from the module that gates this capability
(`tests/validation/test_pec_sphere_hole.py`, `TH-15` step 1), so the example
and the landed gate cannot drift apart.

On record at `-n 2` (`20260906T020307Z_EX-50.log`, 4 s harness-wall / 1.9 s
in-example):

| Quantity | Closed form | Measured | Bound |
| --- | --- | --- | --- |
| Dipole coefficient `beta` | 1.0 | **1.019746** | `\|beta-1\|` = **1.9746%** vs `BAND` 4.8860% |
| Cavity dofs (tag 2, reduced) | > 0 | **1702** | > 0 |
| Max `\|E\|` on cavity dofs | 0 | **0.000e+00** | < 1e-12 |
| `\|Im E\|/\|Re E\|` | 0 | **0.000e+00** | < 1e-6 |
| Control `beta` (cavity natural) | −0.5 (void) | **−0.419038** | `\|beta-1\|` = 141.9038% = **29.0×** the band, floor 5× |
| Mesh | — | 13 239 cells | the gate's own rung |

The measured `beta` and its `1.9746%` miss reproduce the gate module's own
reading on this identical mesh to 1e-3 relative. The gate is `TH-15` step 1
(opened 2026-09-05); this example closes nothing on its own and moves no
band.

## 2. How to run it

```
./run_examples.sh -e th:9 -n 2 -t 300
```

**Complex build required** — the `th:` group sources it automatically, and a
real build raises. Tier: **standard**; 4 s harness-wall on record, three
solves (anchor, control, and the mesh's own build) inside it.

## 3. How to analyze it, step by step

**Step 1 — the anchor: the dipole coefficient against `beta = 1`.**

```
  fitted beta = 1.019746   |beta - 1| = 1.9746%   BAND = 4.8860%
```

`BAND` is twice `th:3`'s own interior-miss record (`TH8_RECORD_INTERIOR_MISS`
= 2.4430%), imported rather than restated, so it can never silently drift.
1.9746% here reproduces the gate module's own reading on this exact mesh
(13 239 cells, `h_sphere = 0.00833`, `h_far = 0.0167` — the gate's own middle
rung, called directly rather than through the gate's process-local mesh
cache).

**Step 2 — the two structural anchors on the same solve.** A dipole fit can
land inside its band while the mechanism producing it is wrong, so two direct
checks on the cavity wall itself:

```
  cavity dofs (tag 2, reduced) = 1702, max |E| on them = 0.000e+00
  |Im E| / |Re E| = 0.000e+00
```

The first says the hole's surface group actually reached the assembled
degrees of freedom (a wiring failure here would silently constrain nothing,
and the "control" experiment below is exactly what that failure looks like).
The second says the problem stayed real: it is lossless and its data real, so
any imaginary leakage means a complex quantity entered where it should not
have.

**Step 3 — printed, not asserted: the pointwise miss.**

```
  max pointwise |E - E_closed|/E0 = 46.0725%, rms 18.6437%
```

These numbers look alarming next to a 2% anchor, and that is the point of
printing them rather than hiding them: at lowest-order Nédélec elements, one
cell away from a Dirichlet-pinned *curved* wall, the pointwise interpolation
error has a discretisation floor that does not shrink with the dipole fit's
averaging. `TH-15` step 1 gates the exterior field's **convergence rate**
(`+1.19` over three mesh rungs, against a `0.8` floor) rather than this
absolute number — the rate says the field is converging to the right closed
form, even though any single mesh's pointwise miss stays large. Do not read a
regression into these two numbers moving; read one into the rate falling
below `0.8` in the gate module, which this example does not re-measure.

**Step 4 — the negative control, asserted per rule (e).** Drop the cavity
tag from the Dirichlet set and the cavity wall becomes *natural* instead of
perfectly conducting — a different physical statement (a void), not a
relabelling of the same one:

```
  control beta = -0.419038 (void closed form -0.5000)
  |beta - 1| = 141.9038% = 29.0x the band   (floor 5x, ceiling factor 30x)
```

The control is backed by the gate module's own measurement of this identical
comparison on this identical mesh (`20260905T170225Z_TH-15.log:303`: 29.0×
against a 30× ceiling) — this run reproduces that separation to the digit.
The example asserts `≥ 5×` and prints the measured factor; nothing larger is
claimed here even though the gate module's own ceiling is 30×.

**Step 5 — open it in ParaView.**
`File → Open → examples/time_harmonic/paraview_output/time_harmonic_09_pec_sphere_hole_combined.xdmf`,
then colour by `E_magnitude`.

1. **What to look at first:** a box with a spherical **void**, not a solid
   ball — nothing is meshed inside the cavity wall, unlike `th:3`'s picture
   of the same geometry with a solved sphere occupying that space.
2. **Clip** through `y = 0` and **Glyph** on `E_real`: arrows converge over
   the poles and reverse at the equator, the dipole lobe of step 1, and drop
   to (numerically) zero tangential to the cavity surface — step 2's
   assertion, made visible.
3. **Threshold** on `CellTags` shows only tag 2 (air) exists in this mesh —
   there is no tag 1 to threshold to, which is itself the geometry/material
   distinction this example draws against `th:3`.

**Step 6 — what a deviation means.** `beta` far from 1 with cavity dofs still
reported nonzero and pinned → the dipole fit or probe cloud has drifted, not
the boundary condition. Cavity dof count zero or `max |E|` on them nonzero →
the facet tag never reached the assembled system — check
`pec_facet_tags=(OUTER_BOUNDARY_TAG, CAVITY_TAG)` is actually being passed.
Nonzero `|Im E|/|Re E|` → a complex quantity in a lossless problem, look at
the material map before the solver. Control factor collapsing toward 5× or
below → the natural-cavity route and the PEC route are no longer producing
distinguishable physics, which would mean `pec_facet_tags` is not doing what
it claims. Any of these against an imported, unmoved band is an example/test
divergence: report and stop, do not touch `BAND` or `CONTROL_CEILING`.

## Related

- The gate this example runs: `tests/validation/test_pec_sphere_hole.py`
  (`TH-15` step 1), and PROJECT_PLAN.md §7 for its record.
- The same geometry solved as a *material*, rather than cut as a *hole* — the
  contrast this example exists to draw:
  `examples/time_harmonic/03_dielectric_sphere_in_uniform_field.py` (`th:3`,
  `EX-6`).
- The closed form this one specialises: `tests/validation/test_dielectric_sphere.py`
  (`TH-8`), whose finest-rung interior-miss record sets `BAND` here.
