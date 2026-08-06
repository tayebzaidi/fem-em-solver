"""`GEO-10` probe: where does `two_torus_domain`'s `outer_boundary` group go?

Replicates the fixture's CAD stage only (box + two tori, fragment, synchronize)
and prints, for every dim-2 entity, its bounding box against the six walls with
the fixture's `tol = 1e-9` wall test. No meshing, so this is smoke-cheap.

Run: `python3 scripts/probes/geo10_probe.py` inside the container (serial).
"""

import numpy as np
import gmsh

separation = 0.05
major_radius = 0.02
minor_radius = 0.005

gmsh.initialize()
gmsh.model.add("geo10_probe")

z_offset = separation / 2
wire_1 = gmsh.model.occ.addTorus(0, 0, -z_offset, major_radius, minor_radius)
wire_2 = gmsh.model.occ.addTorus(0, 0, z_offset, major_radius, minor_radius)

padding = 2.0 * minor_radius
radial_extent = major_radius + minor_radius
box_half_x = radial_extent + padding
box_half_y = radial_extent + padding
box_half_z = z_offset + minor_radius + padding

domain = gmsh.model.occ.addBox(
    -box_half_x, -box_half_y, -box_half_z,
    2.0 * box_half_x, 2.0 * box_half_y, 2.0 * box_half_z,
)
gmsh.model.occ.fragment([(3, domain)], [(3, wire_1), (3, wire_2)])
gmsh.model.occ.synchronize()

halves = (box_half_x, box_half_y, box_half_z)
print(f"[geo10] box halves = {halves}")
print(f"[geo10] dim-2 entities: {len(gmsh.model.getEntities(dim=2))}")

tol = 1e-9
hits = []
for dim, surf in gmsh.model.getEntities(dim=2):
    bb = gmsh.model.getBoundingBox(dim, surf)
    x_min, y_min, z_min, x_max, y_max, z_max = bb
    # Per-wall residual: how far each extreme is from its wall.
    residuals = {
        "x-": (abs(x_min + box_half_x), abs(x_max + box_half_x)),
        "x+": (abs(x_min - box_half_x), abs(x_max - box_half_x)),
        "y-": (abs(y_min + box_half_y), abs(y_max + box_half_y)),
        "y+": (abs(y_min - box_half_y), abs(y_max - box_half_y)),
        "z-": (abs(z_min + box_half_z), abs(z_max + box_half_z)),
        "z+": (abs(z_min - box_half_z), abs(z_max - box_half_z)),
    }
    best = min(residuals.items(), key=lambda kv: max(kv[1]))
    on_wall = max(best[1]) < tol
    area = gmsh.model.occ.getMass(2, surf)
    print(
        f"[geo10] surf {surf:3d} area={area:.9e} nearest_wall={best[0]} "
        f"residual_max={max(best[1]):.3e} on_wall={on_wall}"
    )
    if on_wall:
        hits.append(surf)

print(f"[geo10] boundary_surfaces (tol=1e-9) = {hits}")
analytic = 2.0 * (
    (2 * box_half_x) * (2 * box_half_y)
    + (2 * box_half_x) * (2 * box_half_z)
    + (2 * box_half_y) * (2 * box_half_z)
)
print(f"[geo10] analytic box surface area = {analytic:.12e}")
if hits:
    cad = sum(gmsh.model.occ.getMass(2, s) for s in hits)
    print(f"[geo10] CAD area of hits = {cad:.12e} ratio={cad / analytic:.12f}")

# Does the group survive to elements at all? Declare it and mesh coarsely.
if hits:
    gmsh.model.addPhysicalGroup(2, hits, tag=1)
    gmsh.model.setPhysicalName(2, 1, "outer_boundary")
print(f"[geo10] dim-2 physical groups = {gmsh.model.getPhysicalGroups(dim=2)}")

gmsh.finalize()
