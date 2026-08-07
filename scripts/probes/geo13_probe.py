"""`GEO-13` probe: pick `cylindrical_domain`'s wall tolerance from geometry.

known-issues 13: the wall test is ``abs(r_max - outer_radius) < resolution``,
so the classification margin is geometry over *mesh size* — 4.50x at defaults,
and at ``resolution >= 0.09`` the inner cylinder would be swept into
``outer_boundary``.  The fix is a tolerance built from the radial gap,
``tol = fraction * (outer_radius - inner_radius)``.  This probe measures which
fraction clears both bounds of the `GEO-11` two-sided identity
(accepted <= 0.1*tol, rejected >= 10*tol) on **both** geometries the repo's
callers actually use, and prints the old-predicate ratios beside them.

CAD stage only (two cylinders, fragment, synchronize) — never meshes, so this
is smoke-cheap.

Run: `python3 scripts/probes/geo13_probe.py` inside the container (serial).
"""

import gmsh
import numpy as np

WALL_MARGIN = 0.1
INTERIOR_MARGIN = 10.0

# (label, inner_radius, outer_radius, length, resolution) — every distinct
# argument set `MeshGenerator.cylindrical_domain` is called with in the repo.
GEOMETRIES = (
    ("defaults / tests/mesh", 0.01, 0.1, 0.2, 0.02),
    ("tests/solver/test_cylinder", 0.01, 0.1, 0.2, 0.03),
    ("tests/solver time-harmonic", 0.01, 0.08, 0.12, 0.03),
    ("tests/solver bc-selection", 0.01, 0.08, 0.12, 0.04),
)

FRACTIONS = (0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 1e-3, 1e-4, 1e-5)


def residuals(inner_radius, outer_radius, length):
    """Every dim-2 entity's ``abs(r_max - outer_radius)``, as the generator sees it."""
    gmsh.initialize()
    try:
        gmsh.model.add("geo13_probe")
        inner = gmsh.model.occ.addCylinder(
            0, 0, -length / 2, 0, 0, length, inner_radius
        )
        outer = gmsh.model.occ.addCylinder(
            0, 0, -length / 2, 0, 0, length, outer_radius
        )
        gmsh.model.occ.fragment([(3, outer)], [(3, inner)])
        gmsh.model.occ.synchronize()

        out = []
        for dim, surf in gmsh.model.getEntities(dim=2):
            _, _, _, x_max, y_max, _ = gmsh.model.getBoundingBox(dim, surf)
            r_max = float(np.sqrt(max(x_max**2, y_max**2)))
            out.append((surf, abs(r_max - outer_radius), abs(r_max - inner_radius)))
    finally:
        gmsh.finalize()
    return out


def ratios(rows, tol, index=1):
    """(n_accepted, worst accepted / tol, nearest rejected / tol) at this tol."""
    accepted = [r[index] for r in rows if r[index] < tol]
    rejected = [r[index] for r in rows if not r[index] < tol]
    return (
        len(accepted),
        max(accepted) / tol if accepted else None,
        min(rejected) / tol if rejected else None,
    )


def show(n_acc, wall, interior):
    w = "none" if wall is None else f"{wall:.6e}"
    i = "none" if interior is None else f"{interior:.6e}"
    ok = (
        wall is not None
        and wall <= WALL_MARGIN * (1 + 1e-6)
        and (interior is None or interior >= INTERIOR_MARGIN * (1 - 1e-6))
    )
    return f"n_acc={n_acc} wall={w} interior={i} meets={'YES' if ok else 'no'}"


for label, r_in, r_out, length, resolution in GEOMETRIES:
    rows = residuals(r_in, r_out, length)
    gap = r_out - r_in
    print(
        f"\n[geo13] {label}: r_in={r_in} r_out={r_out} L={length} "
        f"resolution={resolution} gap={gap:.6e}, {len(rows)} dim-2 entities"
    )
    for surf, res_out, res_in in rows:
        print(
            f"[geo13]   surf {surf:3d} residual_outer={res_out:.6e} "
            f"residual_inner={res_in:.6e}"
        )
    print(f"[geo13]   OLD tol=resolution={resolution:.6e}: " + show(*ratios(rows, resolution)))
    for f in FRACTIONS:
        tol = f * gap
        print(
            f"[geo13]   fraction={f:<8g} tol={tol:.6e}: " + show(*ratios(rows, tol))
        )
    # The inner-surface predicate runs on the same tolerance in the generator;
    # check it classifies the same set it does today.
    print(
        f"[geo13]   inner predicate, OLD tol={resolution:.6e}: "
        + show(*ratios(rows, resolution, index=2))
    )
    for f in FRACTIONS:
        tol = f * gap
        print(
            f"[geo13]   inner predicate, fraction={f:<8g} tol={tol:.6e}: "
            + show(*ratios(rows, tol, index=2))
        )

# The failure mode known-issues 13 names: a coarse resolution sweeps the inner
# cylinder into outer_boundary.  Show it explicitly on the default geometry.
rows = residuals(0.01, 0.1, 0.2)
for resolution in (0.02, 0.09, 0.12):
    n_acc, wall, interior = ratios(rows, resolution)
    print(
        f"[geo13] defaults, OLD predicate at resolution={resolution}: "
        f"{n_acc} of {len(rows)} surfaces accepted as outer_boundary"
    )
