"""`GEO-12` — the meshed `outer_boundary` group on the two `1e-9` fixtures.

`GEO-11` measured, and known-issues 12 recorded, that
``loop_over_half_space_domain`` (`MAT-6`) and ``sphere_in_box_domain``
(`TH-8`/`MAT-4`) classified **zero** wall surfaces: their flat-against-wall
test used ``tol = 1e-9`` against gmsh's OCC bounding-box padding of
``1.000e-07``, so ``boundary_surfaces`` came out empty and the
``if boundary_surfaces:`` guard silently skipped ``addPhysicalGroup`` — facet
tag ``1`` did not exist.  Identical to retired known-issues 10 on
``two_torus_domain``, and fixed the same way: ``tol = 1e-6``, which clears the
padding by 10x while staying five orders below the nearest interior face
(``9.000010e-02`` and ``1.500001e-01``, `20260806T183203Z_GEO-12-probe.log`).

The defect survived because **nothing gated the group**, so the tolerance
change lands with this file.  `GEO-11`'s CAD-stage margin test cannot see this:
it never meshes, so it cannot tell a declared physical group from one that
reached the dolfinx facet tags.

**The anchor is an identity, not a band.**  Both fixtures wrap their content in
the cube ``[-W, W]³``, whose six planar walls a linear-tet surface mesh
partitions exactly, so the assembled ``ds`` area over tag ``1`` must equal
``6·(2W)² = 24W²`` to roundoff — gated at ``1e-9`` relative, allreduced.  The
loop fixture's cube is built as two stacked boxes (air ``z ∈ [0, W]`` over slab
``z ∈ [-W, 0]``), so its wall is 10 surfaces rather than 6 — the four sides are
split at ``z = 0`` — and the same total area.

Standard tier, ``-n 2``: both fixtures mesh routinely inside the `MAT-6` and
`TH-8`/`MAT-4` suites.
"""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.io.mesh import MeshGenerator

OUTER_BOUNDARY_TAG = 1

#: Planar walls under a linear-tet surface mesh: an identity, not a band.
AREA_RTOL = 1e-9

#: Both fixtures' default ``box_half_width`` (io/mesh.py). The gate meshes at
#: the defaults its callers use, so a sizing change is caught here too.
BOX_HALF_WIDTH = 0.10


def _analytic_cube_surface_area(half_width: float) -> float:
    """``6·(2W)²`` — the outer surface of the cube ``[-W, W]³``."""
    return 6.0 * (2.0 * half_width) ** 2


def _global_facet_tag_set(facet_tags, comm):
    """Rank-local ``facet_tags.values`` reduced to the global set."""
    local = set(np.unique(facet_tags.values).tolist()) if facet_tags is not None else set()
    return set().union(*comm.allgather(local))


def _global_facet_count(facet_tags, tag, comm) -> int:
    local = int(np.count_nonzero(facet_tags.values == tag)) if facet_tags is not None else 0
    return int(comm.allreduce(local, op=MPI.SUM))


def _exterior_facet_group_area(msh, facet_tags, tag, comm) -> float:
    """``∫_tag ds``, reduced.

    These facets are exterior, so the measure is ``ds``.
    ``create_entity_permutations`` is called unconditionally on every rank
    (known-issues 9's lazy-collective lesson: a rank owning no tagged facet must
    still enter the collective), and ``assemble_scalar`` is rank-local, hence
    the allreduce.
    """
    msh.topology.create_entity_permutations()
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)

    ds_tag = ufl.Measure("ds", domain=msh, subdomain_data=facet_tags, subdomain_id=(tag,))
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * ds_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _check_outer_boundary(label, generator, comm):
    msh, _, facet_tags = generator(comm)
    assert facet_tags is not None, f"{label}: model_to_mesh returned no facet tags"

    tags_present = _global_facet_tag_set(facet_tags, comm)
    n_facets = _global_facet_count(facet_tags, OUTER_BOUNDARY_TAG, comm)
    area = _exterior_facet_group_area(msh, facet_tags, OUTER_BOUNDARY_TAG, comm)
    analytic = _analytic_cube_surface_area(BOX_HALF_WIDTH)

    if comm.rank == 0:
        print(
            f"\n[GEO-12 {label}] facet tags: {sorted(tags_present)}"
            f"  n_facets(tag {OUTER_BOUNDARY_TAG})={n_facets}"
            f"\nA_outer={area:.12e} m^2  analytic={analytic:.12e} m^2"
            f"  ratio={area / analytic:.15f}",
            flush=True,
        )

    # The broken state, on record: this set was empty — the group was never
    # declared, so tag 1 did not exist at all (known-issues 12).
    assert OUTER_BOUNDARY_TAG in tags_present, (
        f"{label}: facet tag set is {sorted(tags_present)}, missing the "
        f"outer_boundary tag {OUTER_BOUNDARY_TAG} — this is known-issues 12."
    )
    assert n_facets > 0, (
        f"{label}: tag {OUTER_BOUNDARY_TAG} exists but carries zero facets "
        "globally."
    )
    assert area / analytic == pytest.approx(1.0, abs=AREA_RTOL), (
        f"{label}: tagged outer-boundary area {area:.12e} m^2 differs from the "
        f"analytic cube surface {analytic:.12e} m^2 by "
        f"{abs(area / analytic - 1.0):.3e} relative, above {AREA_RTOL:.0e}"
    )


def test_loop_over_half_space_outer_boundary_area():
    """`MAT-6`'s fixture: tag 1 exists and covers the cube exactly."""
    _check_outer_boundary(
        "loop_over_half_space_domain",
        lambda comm: MeshGenerator.loop_over_half_space_domain(
            box_half_width=BOX_HALF_WIDTH, comm=comm
        ),
        MPI.COMM_WORLD,
    )


def test_sphere_in_box_outer_boundary_area():
    """`TH-8`/`MAT-4`'s fixture: tag 1 exists and covers the cube exactly."""
    _check_outer_boundary(
        "sphere_in_box_domain",
        lambda comm: MeshGenerator.sphere_in_box_domain(
            box_half_width=BOX_HALF_WIDTH, comm=comm
        ),
        MPI.COMM_WORLD,
    )
