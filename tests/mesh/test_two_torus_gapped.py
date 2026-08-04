"""`PORT-1` step 3b-i — gapped two-torus fixture, mesh only.

``two_torus_domain(port_gap=True)`` opens a wedge in each torus and bridges the
arc ends with a rectangular gap box, tagged ``101`` / ``102``. This file gates
the *geometry*, not any field: the volume-partition identities plus the exact
gap-box volume, which is what a lumped-port drive (step 3b-ii) will integrate
``V = -∫E·dl`` over.

Why the gap box takes precedence over the conductor in the fragment piece
policy: the two arc-end planes meet at ``gap_angle``, so no box can be flush
with both. The box therefore buries ``gap_clearance`` past each end-face
centre, and the pieces it swallows are gap, not metal — which makes the gap
volume exactly ``dx·dy·dz`` (planar faces, meshed to roundoff, the `GEO-9`
step-2b precedent) and the conductor the arc minus what the box took.

**Negative control, on record, not re-solved here:** the unfragmented ancestor
of this fixture meshed the box *solid* through the torus regions and the tori
as disconnected islands — total/box volume ratio 1.002633 and ``Z12 == 0``
exactly (`PORT-1` step-1 logs `20260731T213222Z_PORT-1-step1-costprobe.log`,
`…213423Z_…-meshconformity.log`). The identities below separate from that by
six orders of magnitude.
"""

from __future__ import annotations

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
AIR_PADDING = 2.0 * MINOR_RADIUS
WIRE_RESOLUTION = 0.002

GAP_ANGLE = 0.30
GAP_CLEARANCE = 1.0e-3

WIRE_TAGS = (1, 2)
AIR_TAG = 3
GAP_TAGS = (101, 102)


def _analytic_box_volume():
    half_x = MAJOR_RADIUS + MINOR_RADIUS + AIR_PADDING
    half_z = SEPARATION / 2.0 + MINOR_RADIUS + AIR_PADDING
    return 8.0 * half_x * half_x * half_z


def _analytic_gap_box_volume():
    half_xz = MINOR_RADIUS + GAP_CLEARANCE
    half_y = MAJOR_RADIUS * np.sin(0.5 * GAP_ANGLE) + GAP_CLEARANCE
    return (2.0 * half_xz) * (2.0 * half_y) * (2.0 * half_xz)


def _analytic_partial_torus_volume():
    return (1.0 - GAP_ANGLE / (2.0 * np.pi)) * 2.0 * np.pi**2 * MAJOR_RADIUS * MINOR_RADIUS**2


def _tag_volume(msh, cell_tags, tag, comm):
    """``∫_tag 1 dV``, reduced — ``assemble_scalar`` is rank-local."""
    dx_tag = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,))
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * dx_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _total_volume(msh, comm):
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * ufl.dx))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _gapped_mesh(comm):
    return MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=RESOLUTION,
        air_padding=AIR_PADDING,
        wire_resolution=WIRE_RESOLUTION,
        far_resolution=RESOLUTION,
        port_gap=True,
        gap_angle=GAP_ANGLE,
        gap_clearance=GAP_CLEARANCE,
        comm=comm,
    )


def test_gapped_two_torus_volumes_partition_the_box():
    """Five tagged volumes tile the box, and each gap box is meshed exactly."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = _gapped_mesh(comm)

    assert global_cell_tag_set(msh, cell_tags) == {1, 2, 3, 101, 102}

    v_box = _analytic_box_volume()
    v_total = _total_volume(msh, comm)
    v_wires = [_tag_volume(msh, cell_tags, t, comm) for t in WIRE_TAGS]
    v_gaps = [_tag_volume(msh, cell_tags, t, comm) for t in GAP_TAGS]
    v_air = _tag_volume(msh, cell_tags, AIR_TAG, comm)
    v_gap_exact = _analytic_gap_box_volume()
    v_arc = _analytic_partial_torus_volume()

    if comm.rank == 0:
        print(
            f"\nV_box={v_box:.9e}  V_mesh={v_total:.9e}  "
            f"ratio={v_total / v_box:.12f}"
            f"\nsum(tagged)/V_mesh="
            f"{(v_air + sum(v_wires) + sum(v_gaps)) / v_total:.12f}"
            f"\nV_gap1={v_gaps[0]:.9e}  V_gap2={v_gaps[1]:.9e}  "
            f"analytic={v_gap_exact:.9e}  "
            f"meshed/analytic={v_gaps[0] / v_gap_exact:.12f}, "
            f"{v_gaps[1] / v_gap_exact:.12f}"
            f"\nV_wire1={v_wires[0]:.9e}  V_wire2={v_wires[1]:.9e}  "
            f"partial-torus analytic={v_arc:.9e}  "
            f"meshed/analytic={v_wires[0] / v_arc:.6f}, {v_wires[1] / v_arc:.6f}"
            f"\nV_air={v_air:.9e}",
            flush=True,
        )

    # The union of the tagged volumes is the box; its boundary is planar, so a
    # linear-tet mesh reproduces it to roundoff. The unfragmented ancestor gave
    # 1.002633 here.
    assert abs(v_total / v_box - 1.0) < 1e-9, (
        f"total mesh volume {v_total:.9e} m^3 vs analytic box {v_box:.9e} m^3 "
        f"(ratio {v_total / v_box:.9f})"
    )
    assert abs((v_air + sum(v_wires) + sum(v_gaps)) / v_total - 1.0) < 1e-9

    # Each gap box is a rectangular solid with planar faces: meshed exactly.
    for tag, v in zip(GAP_TAGS, v_gaps):
        assert abs(v / v_gap_exact - 1.0) < 1e-9, (
            f"gap tag {tag} meshed volume {v:.9e} m^3 vs dx*dy*dz "
            f"{v_gap_exact:.9e} m^3 (ratio {v / v_gap_exact:.12f})"
        )

    # The conductor is the arc minus the piece the gap box swallowed, minus the
    # chordal deficit of a linear-tet torus surface. Band measured 2026-08-04
    # (probe log 20260804T093449Z_PORT-1-step3bi-costprobe.log): 0.963633 and
    # 0.963756 of the analytic partial torus at WIRE_RESOLUTION = 0.002. The
    # two factors separate in that log: gmsh's exact arc mass was 9.238604e-06
    # (98.30% of analytic — the box took 1.70%), and 9.056573/9.238604 =
    # 0.98030 is the chordal deficit, the same 0.980079 the ungapped test below
    # measures on the full torus.
    for tag, v in zip(WIRE_TAGS, v_wires):
        assert 0.955 < v / v_arc < 0.975, (
            f"wire tag {tag} meshed volume {v:.9e} m^3 is "
            f"{v / v_arc:.6f} of the analytic partial torus {v_arc:.9e} m^3, "
            "outside the measured band (0.955, 0.975)"
        )
        # Vacuity control: a box that failed to reach the arc ends would leave
        # the conductor at the pure chordal deficit (0.980079, measured on the
        # ungapped fixture in this same file) and the gap would not be bridged.
        assert v / v_arc < 0.9790, (
            f"wire tag {tag} lost no volume to the gap box "
            f"(ratio {v / v_arc:.6f} vs the ungapped chordal deficit 0.980079) "
            "— the box is not crossing the arc ends"
        )

    # The two loops discretise alike — they are the same solid, mirrored.
    assert abs(v_wires[0] / v_wires[1] - 1.0) < 5e-3
    assert abs(v_gaps[0] / v_gaps[1] - 1.0) < 1e-9


def test_ungapped_default_is_unaffected():
    """`port_gap` defaults off: the seven existing callers mesh as before."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=RESOLUTION,
        air_padding=AIR_PADDING,
        wire_resolution=WIRE_RESOLUTION,
        far_resolution=RESOLUTION,
        comm=comm,
    )

    assert global_cell_tag_set(msh, cell_tags) == {1, 2, 3}, (
        "the default path must not emit gap tags"
    )

    v_box = _analytic_box_volume()
    v_total = _total_volume(msh, comm)
    v_wires = [_tag_volume(msh, cell_tags, t, comm) for t in WIRE_TAGS]
    v_air = _tag_volume(msh, cell_tags, AIR_TAG, comm)
    v_torus = 2.0 * np.pi**2 * MAJOR_RADIUS * MINOR_RADIUS**2

    if comm.rank == 0:
        print(
            f"\n[ungapped regression] V_mesh/V_box={v_total / v_box:.12f}  "
            f"meshed/analytic torus={v_wires[0] / v_torus:.6f}, "
            f"{v_wires[1] / v_torus:.6f}",
            flush=True,
        )

    assert abs(v_total / v_box - 1.0) < 1e-9
    assert abs((v_air + sum(v_wires)) / v_total - 1.0) < 1e-9
    for v in v_wires:
        assert 0.80 * v_torus < v < v_torus
