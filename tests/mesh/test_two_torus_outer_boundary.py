"""`GEO-10` — `two_torus_domain`'s `outer_boundary` facet group (tag ``1``).

Until 2026-08-06 the fixture declared an ``outer_boundary`` physical group that
never reached the dolfinx facet tags: the ungapped fixture's global facet-tag
set was ``[]`` and the gapped one's was ``[201, 202]`` (known-issues 10,
measured in ``20260805T020843Z_PORT-1-step3biv-serial-gate.log``).

**What it was.** Not fragment renumbering — the group is re-derived from
bounding boxes *after* ``fragment`` + ``synchronize``, so renumbering cannot
reach it. gmsh inflates an OCC entity's bounding box by its geometric
tolerance, measured at exactly ``1.000e-07`` on all six walls of this box
(``20260806T050143Z_GEO-10-probe.log``), and the fixture's flat-against-wall
test used ``tol = 1e-9``. Every wall failed it, ``boundary_surfaces`` came out
empty, and the ``if boundary_surfaces:`` guard meant no group was ever added.
The nearest *interior* face's residual in the same probe is ``2.000e-02``, four
orders above the ``1e-6`` the fixture now uses, so widening the tolerance does
not risk sweeping an interior face into the boundary condition — which is what
the tight test was defending against in the first place.

**The anchor is an identity, not a band.** The six box walls are planar, so a
linear-tet surface mesh partitions them exactly: the assembled ``ds`` area over
tag ``1`` must equal ``2(LW + LH + WH)`` to roundoff. That is gated at ``1e-9``
relative, allreduced, and it holds in both configurations — the gap boxes are
strictly interior, so gapping must not move the outer area by a single digit.
"""

from __future__ import annotations

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.io.mesh import MeshGenerator

SEPARATION = 0.05
MAJOR_RADIUS = 0.02
MINOR_RADIUS = 0.005
RESOLUTION = 0.01
AIR_PADDING = 2.0 * MINOR_RADIUS
WIRE_RESOLUTION = 0.002

GAP_ANGLE = 0.30
GAP_CLEARANCE = 1.0e-3

OUTER_BOUNDARY_TAG = 1
PORT_FACET_TAGS = (201, 202)

AREA_RTOL = 1e-9


def _box_halves():
    """The fixture's own box sizing, restated from `io/mesh.py`."""
    radial_extent = MAJOR_RADIUS + MINOR_RADIUS
    half_x = radial_extent + AIR_PADDING
    half_y = radial_extent + AIR_PADDING
    half_z = SEPARATION / 2 + MINOR_RADIUS + AIR_PADDING
    return half_x, half_y, half_z


def _analytic_box_surface_area():
    half_x, half_y, half_z = _box_halves()
    length, width, height = 2 * half_x, 2 * half_y, 2 * half_z
    return 2.0 * (length * width + length * height + width * height)


def _mesh(comm, *, port_gap):
    return MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=RESOLUTION,
        air_padding=AIR_PADDING,
        wire_resolution=WIRE_RESOLUTION,
        far_resolution=RESOLUTION,
        port_gap=port_gap,
        gap_angle=GAP_ANGLE,
        gap_clearance=GAP_CLEARANCE,
        comm=comm,
    )


def _global_facet_tag_set(facet_tags, comm):
    local = set(np.unique(facet_tags.values).tolist()) if facet_tags is not None else set()
    return set().union(*comm.allgather(local))


def _exterior_facet_group_area(msh, facet_tags, tag, comm):
    """``int_tag 1 ds``, reduced.

    These facets are exterior — the measure is ``ds``, unlike the *interior*
    port cuts of `PORT-1` step 3b-iv, which need ``dS`` with ``avg``.
    ``create_entity_permutations`` is called unconditionally on every rank
    anyway (the 3b-iv lazy-collective lesson, known-issues 9): a rank that owns
    no tagged facet must still enter any collective the assembler might reach.
    ``assemble_scalar`` is rank-local, hence the allreduce.
    """
    msh.topology.create_entity_permutations()
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)

    ds_tag = ufl.Measure(
        "ds", domain=msh, subdomain_data=facet_tags, subdomain_id=(tag,)
    )
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * ds_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _check_outer_boundary(comm, *, port_gap):
    msh, _, facet_tags = _mesh(comm, port_gap=port_gap)
    assert facet_tags is not None, "model_to_mesh returned no facet tags"

    tags_present = _global_facet_tag_set(facet_tags, comm)
    area = _exterior_facet_group_area(msh, facet_tags, OUTER_BOUNDARY_TAG, comm)
    analytic = _analytic_box_surface_area()

    if comm.rank == 0:
        print(
            f"\n[GEO-10 port_gap={port_gap}] facet tags: {sorted(tags_present)}"
            f"\nA_outer={area:.12e} m^2  analytic={analytic:.12e} m^2"
            f"  ratio={area / analytic:.15f}",
            flush=True,
        )

    # The broken state, on record: this set was `[]` ungapped and `[201, 202]`
    # gapped (known-issues 10). It is an exact set, not a containment.
    expected = {OUTER_BOUNDARY_TAG}
    if port_gap:
        expected |= set(PORT_FACET_TAGS)
    assert tags_present == expected, (
        f"facet tag set is {sorted(tags_present)}, expected {sorted(expected)}"
    )

    assert abs(area / analytic - 1.0) < AREA_RTOL, (
        f"tagged outer-boundary area {area:.12e} m^2 differs from the analytic "
        f"box surface {analytic:.12e} m^2 by "
        f"{abs(area / analytic - 1.0):.3e} relative, above {AREA_RTOL:.0e}"
    )
    return area


def test_outer_boundary_tag_covers_the_box_ungapped():
    """Ungapped: tag set is exactly `{1}` and its area is the box surface."""
    _check_outer_boundary(MPI.COMM_WORLD, port_gap=False)


def test_outer_boundary_tag_covers_the_box_gapped():
    """Gapped: `{1, 201, 202}`, and the outer area is unmoved by the gaps."""
    comm = MPI.COMM_WORLD
    area = _check_outer_boundary(comm, port_gap=True)

    # The gap boxes are strictly interior, so this must be the *same* number the
    # ungapped path gives, not merely within the identity band of the analytic
    # value. Both are pinned to the analytic surface at 1e-9, so comparing each
    # to it pins them to each other; assert it directly so a future change that
    # moved both together would still be caught.
    assert abs(area / _analytic_box_surface_area() - 1.0) < AREA_RTOL
