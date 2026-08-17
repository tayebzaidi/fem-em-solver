"""Chunk E2/B2: birdcage-like geometry fixture with explicit robust port tags."""

from __future__ import annotations

import numpy as np
from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.io.mesh_qa import print_cell_tag_summary
from tests.mesh.helpers import global_cell_tag_set
from tests.mesh.test_coil_phantom_conforming import _tag_volume, _total_volume


BIRDCAGE_CORE_TAGS = {
    1: "conductor",
    2: "air",
    3: "phantom",
}

# The fixture parameters, in one place: the analytic box volume below is built
# from them with the generator's own arithmetic (`io/mesh.py:2058-2059`).
LEG_COUNT = 4
RING_RADIUS = 0.07
LEG_WIDTH = 0.012
LEG_SPACING = 0.11
COIL_LENGTH = 0.14
RING_MINOR_RADIUS = 0.004
PHANTOM_RADIUS = 0.03
PHANTOM_HEIGHT = 0.08
PORT_BOX_SIZE = (0.010, 0.008, 0.010)
AIR_PADDING = 0.03
RESOLUTION = 0.015


def _analytic_box_volume() -> float:
    """``8·radial_extent²·z_extent``, the generator's own extents."""
    leg_radius_eff = 0.5 * LEG_WIDTH
    radial_extent = (
        RING_RADIUS
        + max(leg_radius_eff, RING_MINOR_RADIUS)
        + PORT_BOX_SIZE[1]
        + AIR_PADDING
    )
    z_extent = (
        max(
            0.5 * COIL_LENGTH,
            0.5 * LEG_SPACING + RING_MINOR_RADIUS,
            0.5 * PHANTOM_HEIGHT,
        )
        + AIR_PADDING
    )
    return 8.0 * radial_extent * radial_extent * z_extent


# `OPS-17` step 2 (2026-08-17). The old
# ``test_birdcage_like_mesh_has_core_and_port_tags`` meshed this fixture and
# asserted ``n_cells > 0``, ``n_cells < 50000`` and "no required tag missing" —
# all finiteness-class. The step-1 table named the tagged-volume partition
# identity as its anchor, but ``test_birdcage_volumes_partition_the_box`` below
# already gates exactly that identity on the *identical* fixture (LEG_COUNT is
# 4, the same leg count the old test passed) and already asserts the exact
# global tag set. Landing the named anchor here would have duplicated a gate
# and paid for a second mesh of the same geometry to do it; the step-1 table
# pre-authorises deleting rather than duplicating when step 2 finds this, so
# the mesh-side content is left to that test.
#
# What is *not* covered there is ``birdcage_port_layout_diagnostics``, which the
# old test called and only printed. It is meshless, so gating it is free, and
# its outputs are closed forms of the fixture parameters:
#
#   port face area          = port_dx * port_dz
#   port radius             = ring_radius + max(leg_width/2, ring_minor_radius)
#                             + port_dy/2 + port_clearance
#   min centre separation   = 2 * port_radius * sin(pi / leg_count)
#     (the ports sit at the leg midpoint angles, so they are as equally spaced
#      as the legs; nearest neighbours subtend 2*pi/leg_count)
#   conductor clearance     = port_radius - port_dy/2 - conductor_outer_radius
#   phantom clearance       = port_radius - port_dy/2 - phantom_radius
#
# Every one is exact arithmetic on floats, so the band is roundoff.

PORT_CLEARANCE = 1.0e-3
DIAGNOSTICS_BAND = 1.0e-12


def test_birdcage_port_layout_diagnostics_match_the_closed_forms():
    """The meshless port-layout diagnostics reproduce their geometry formulas."""
    comm = MPI.COMM_WORLD

    diagnostics = MeshGenerator.birdcage_port_layout_diagnostics(
        leg_count=LEG_COUNT,
        ring_radius=RING_RADIUS,
        leg_width=LEG_WIDTH,
        ring_minor_radius=RING_MINOR_RADIUS,
        phantom_radius=PHANTOM_RADIUS,
        port_box_size=PORT_BOX_SIZE,
        port_clearance=PORT_CLEARANCE,
    )

    port_dx, port_dy, port_dz = PORT_BOX_SIZE
    conductor_outer_radius = RING_RADIUS + max(0.5 * LEG_WIDTH, RING_MINOR_RADIUS)
    port_radius = conductor_outer_radius + 0.5 * port_dy + PORT_CLEARANCE

    expected = {
        "port_face_area_m2": port_dx * port_dz,
        "conductor_outer_radius_m": conductor_outer_radius,
        "port_radius_m": port_radius,
        "min_port_center_separation_m": 2.0 * port_radius * np.sin(np.pi / LEG_COUNT),
        "conductor_radial_clearance_m": (
            port_radius - 0.5 * port_dy - conductor_outer_radius
        ),
        "phantom_radial_clearance_m": port_radius - 0.5 * port_dy - PHANTOM_RADIUS,
    }

    if comm.rank == 0:
        print("\n[OPS-17] birdcage port-layout diagnostics vs closed forms:")
        for key, want in expected.items():
            got = float(diagnostics[key])
            print(
                f"    {key}: {got:.12e} vs {want:.12e} "
                f"(rel {abs(got / want - 1.0):.3e})",
                flush=True,
            )

    for key, want in expected.items():
        got = float(diagnostics[key])
        rel = abs(got / want - 1.0)
        assert rel < DIAGNOSTICS_BAND, (
            f"{key} = {got:.12e} vs closed form {want:.12e} "
            f"(relative {rel:.3e}, band {DIAGNOSTICS_BAND:.0e})"
        )

    # The layout must actually clear both bulk regions and its own minima. The
    # diagnostics raise otherwise, but the margins are what make the fixture
    # usable, so pin their sign here rather than trusting the raise.
    assert expected["conductor_radial_clearance_m"] > 0.0
    assert expected["phantom_radial_clearance_m"] > 0.0
    assert (
        diagnostics["min_port_center_separation_m"]
        > diagnostics["required_port_center_separation_m"]
    )
    assert diagnostics["port_face_area_m2"] > diagnostics["min_port_face_area_m2"]


def test_birdcage_volumes_partition_the_box():
    """`GEO-9` step-2b anchor: the tagged regions tile the analytic air box.

    Before the `occ.fragment` rewrite this could not be evaluated at all — the
    legs pierce both rings, the un-booleaned solids were meshed twice, and gmsh
    raised ``Invalid boundary mesh (overlapping facets) on surface 3 surface
    49`` before any mesh existed. Mesh-exists versus raises is total separation,
    so the negative control here is the before-state itself, not a number.
    """
    comm = MPI.COMM_WORLD

    mesh, cell_tags, _ = MeshGenerator.birdcage_port_domain(
        leg_count=LEG_COUNT,
        ring_radius=RING_RADIUS,
        leg_width=LEG_WIDTH,
        leg_spacing=LEG_SPACING,
        coil_length=COIL_LENGTH,
        ring_minor_radius=RING_MINOR_RADIUS,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        port_box_size=PORT_BOX_SIZE,
        air_padding=AIR_PADDING,
        resolution=RESOLUTION,
        comm=comm,
    )

    port_tags = [100 + i for i in range(1, LEG_COUNT + 1)]
    all_tags = [1, 2, 3, *port_tags]
    assert global_cell_tag_set(mesh, cell_tags) == set(all_tags)

    # Tag summary inherited from the finiteness-only test `OPS-17` step 2
    # removed above: the QA output is worth keeping, the assertions it carried
    # are subsumed by the exact set identity on the line above.
    print_cell_tag_summary(
        cell_tags,
        tag_names={
            **BIRDCAGE_CORE_TAGS,
            **{tag: f"port_P{i}" for i, tag in enumerate(port_tags, start=1)},
        },
        comm=comm,
        prefix="[birdcage-mesh] ",
    )

    v_box = _analytic_box_volume()
    v_total = _total_volume(mesh, comm)
    v = {tag: _tag_volume(mesh, cell_tags, tag, comm) for tag in all_tags}

    # Analytic references. The conductor sum double-counts the eight leg∩ring
    # junctions, so the meshed conductor must come in *below* it — a `= 1` here
    # would be wrong physics. The port boxes and the air box are planar, so a
    # linear-tet mesh of them is exact to roundoff.
    v_rings = 2.0 * (2.0 * np.pi**2 * RING_RADIUS * RING_MINOR_RADIUS**2)
    v_legs = LEG_COUNT * np.pi * (0.5 * LEG_WIDTH) ** 2 * COIL_LENGTH
    v_conductor_analytic = v_rings + v_legs
    v_cylinder = np.pi * PHANTOM_RADIUS**2 * PHANTOM_HEIGHT
    v_port_analytic = PORT_BOX_SIZE[0] * PORT_BOX_SIZE[1] * PORT_BOX_SIZE[2]

    if comm.rank == 0:
        print(
            f"\nV_box={v_box:.6e}  V_mesh={v_total:.6e}  "
            f"ratio={v_total / v_box:.12f}"
            f"\nsum(tagged)/V_mesh={sum(v.values()) / v_total:.12f}"
            f"\nV_conductor={v[1]:.6e}  analytic_sum(rings+legs)="
            f"{v_conductor_analytic:.6e}  meshed/analytic="
            f"{v[1] / v_conductor_analytic:.4f}  (< 1 by the 8 leg-ring junctions)"
            f"\nV_phantom={v[3]:.6e}  V_cylinder_analytic={v_cylinder:.6e}  "
            f"meshed/analytic={v[3] / v_cylinder:.4f}"
            f"\nV_air={v[2]:.6e}"
            + "".join(
                f"\nV_port_P{i}={v[tag]:.6e}  analytic={v_port_analytic:.6e}  "
                f"meshed/analytic={v[tag] / v_port_analytic:.6f}"
                for i, tag in enumerate(port_tags, start=1)
            ),
            flush=True,
        )

    # The two identities. Both are exactly the "nothing meshed twice, nothing
    # left ungrouped" statement that `GEO-8` and `GEO-9` step 1 gate elsewhere.
    assert abs(v_total / v_box - 1.0) < 1e-9, (
        f"total mesh volume {v_total:.6e} m^3 vs analytic box {v_box:.6e} m^3 "
        f"(ratio {v_total / v_box:.12f}); a ratio above 1 means a region is "
        "meshed twice, i.e. the fragment did not conform"
    )
    assert abs(sum(v.values()) / v_total - 1.0) < 1e-9, (
        f"tagged volumes sum to {sum(v.values()):.6e} m^3 of a {v_total:.6e} "
        "m^3 mesh; a deficit means a fragment piece carries no physical group"
    )

    # Per-region bands, set from the measurement in
    # 20260803T200358Z_GEO-9-step2b-bands.log: conductor 0.7091, phantom 0.9734,
    # every port 1.000000. They are statements about resolution and about the
    # junction overlap, not tolerances on the identities above. The conductor
    # deficit has two sources at once — the 8 leg∩ring junctions the analytic
    # sum double-counts, and a global 0.015 setSize against a 0.004 ring minor
    # radius (the `GEO-9` step-1 tori kept 0.7547 for the second reason alone).
    assert 0.65 * v_conductor_analytic < v[1] < v_conductor_analytic, (
        f"conductor meshed volume {v[1]:.6e} m^3 outside the band "
        f"(0.65, 1.00) x the double-counting analytic sum {v_conductor_analytic:.6e} m^3"
    )
    assert 0.90 * v_cylinder < v[3] < v_cylinder, (
        f"phantom meshed volume {v[3]:.6e} m^3 outside the inscribed band "
        f"(0.90, 1.00) x analytic {v_cylinder:.6e} m^3"
    )
    for i, tag in enumerate(port_tags, start=1):
        assert abs(v[tag] / v_port_analytic - 1.0) < 1e-9, (
            f"port P{i} meshed volume {v[tag]:.6e} m^3 vs analytic box "
            f"{v_port_analytic:.6e} m^3 (ratio {v[tag] / v_port_analytic:.12f}); "
            "the port region is a rectangular box, so a linear-tet mesh of it "
            "is exact to roundoff"
        )
    assert v[2] < v_box - 0.9 * v_cylinder, (
        f"air volume {v[2]:.6e} m^3 is not the box minus the conductors, "
        f"phantom and ports (box {v_box:.6e}, cylinder {v_cylinder:.6e})"
    )


def test_birdcage_port_layout_rejects_too_small_or_overlapping_port_regions():
    """Reject implausible port geometry before meshing."""
    # Too-small face area check.
    try:
        MeshGenerator.birdcage_port_layout_diagnostics(
            leg_count=4,
            ring_radius=0.07,
            leg_width=0.012,
            ring_minor_radius=0.004,
            phantom_radius=0.03,
            port_box_size=(0.003, 0.008, 0.003),
            min_port_face_area=2.5e-5,
        )
        raise AssertionError("Expected ValueError for too-small port face area")
    except ValueError as exc:
        assert "Port face area too small" in str(exc)

    # Overlap/separation check via unrealistically dense port packing.
    try:
        MeshGenerator.birdcage_port_layout_diagnostics(
            leg_count=32,
            ring_radius=0.03,
            leg_width=0.010,
            ring_minor_radius=0.004,
            phantom_radius=0.02,
            port_box_size=(0.010, 0.010, 0.010),
            min_port_center_separation=0.015,
            port_clearance=0.0,
        )
        raise AssertionError("Expected ValueError for insufficient port center separation")
    except ValueError as exc:
        assert "Port center separation too small" in str(exc)
