"""Mesh test for two-torus Helmholtz prototype geometry.

`OPS-17` step 2 (2026-08-17) replaced this file's finiteness-only assertions
(``n_cells > 0`` plus tag presence) with the volume-partition identity the
`GEO-16` / `GEO-8` fixtures use: the three tagged volumes tile the analytic
box to 1e-9.

The step-1 table named "the two wire volumes = CAD 2·(2π²Rr²) to 1e-9" as the
anchor. That identity does **not** hold at this test's ``resolution=0.01``:
the cells are twice the wire minor radius and the meshed torus loses ~40% of
its volume to chordal deficit (5.905213e-06 vs 9.869604e-06 m³, measured
2026-08-01 — see ``tests/mesh/test_two_torus_conforming.py``). Tightening to
1e-9 there would be a statement about resolution, not about the mesh, so the
anchor used here is the identity that *is* exact at any resolution — the
partition — with the wires held to the inscribed band. The 1e-9 CAD-wire
equality is already gated at the resolved ``wire_resolution=0.002`` rung by
``test_two_torus_volumes_partition_the_box``.
"""

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.io.mesh import MeshGenerator
from tests.mesh.helpers import global_cell_tag_set

SEPARATION = 0.05
MAJOR_RADIUS = 0.02
MINOR_RADIUS = 0.005
RESOLUTION = 0.01

WIRE_TAGS = (1, 2)
AIR_TAG = 3

# Exact-arithmetic band: the box boundary is planar, so a linear-tet mesh
# reproduces its volume to roundoff, and the curved torus surfaces are
# interior — their deficit cancels between the wire and air sides.
VOLUME_IDENTITY_BAND = 1.0e-9


def _tag_volume(msh, cell_tags, tag, comm):
    """``∫_tag 1 dV``, reduced — ``assemble_scalar`` is rank-local."""
    dx_tag = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,)
    )
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * dx_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _total_volume(msh, comm):
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * ufl.dx))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def test_two_torus_mesh_volumes_partition_the_box():
    """Generate the two-torus mesh; the tagged volumes tile the box exactly."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=RESOLUTION,
        comm=comm,
    )

    # Tag presence must be checked globally: cell_tags.values is rank-local, and
    # a wire volume can land entirely on one rank under decomposition.
    assert global_cell_tag_set(msh, cell_tags) == {1, 2, 3}, (
        "expected exactly the wire_1 / wire_2 / domain volume tags"
    )

    v_total = _total_volume(msh, comm)
    v_wires = [_tag_volume(msh, cell_tags, t, comm) for t in WIRE_TAGS]
    v_air = _tag_volume(msh, cell_tags, AIR_TAG, comm)

    # Tags partition the mesh: air is the box *minus* the tori, not the box.
    # The non-fragmented (doubly-meshed torus) failure mode shows up here.
    ratio = (v_air + sum(v_wires)) / v_total
    assert abs(ratio - 1.0) < VOLUME_IDENTITY_BAND, (
        f"tagged volumes {v_air + sum(v_wires):.9e} m^3 vs total mesh volume "
        f"{v_total:.9e} m^3 (ratio {ratio:.12f}) — the tags do not partition"
    )

    # Each meshed torus inscribes its CAD volume: a linear-tet approximation to
    # a curved surface can only lose volume, never gain it. At this resolution
    # the deficit is large (see the module docstring); the upper edge is the
    # exact statement, the lower edge just keeps the test non-vacuous.
    v_torus = 2.0 * np.pi**2 * MAJOR_RADIUS * MINOR_RADIUS**2
    for tag, v in zip(WIRE_TAGS, v_wires):
        assert 0.50 * v_torus < v < v_torus, (
            f"tag {tag} meshed volume {v:.6e} m^3 outside the inscribed band "
            f"(0.50, 1.00) x CAD {v_torus:.6e} m^3"
        )

    if comm.rank == 0:
        print(
            f"\n[OPS-17] two-torus at h={RESOLUTION}: total {v_total:.9e} m^3, "
            f"partition ratio {ratio:.12f}, wires "
            f"{[f'{v:.6e}' for v in v_wires]} vs CAD {v_torus:.6e} m^3",
            flush=True,
        )
