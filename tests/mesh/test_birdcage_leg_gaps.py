"""`GEO-18` step 1 — cut the birdcage legs so the port boxes have terminals.

`PORT-9` step 3 could not run: leg (a) measured that the birdcage carries no
port-sheet facet, and leg (b) measured *why that is not fixable by splitting a
box* — every port box's conductor-facing area is exactly ``0.000000e+00 m²``
under a closure identity at ``1.000000000000``. The boxes are isolated air
blocks at the midpoint azimuth between adjacent legs, outside an **uncut** coil.
A sheet spanning such a box drives nothing.

This module measures the fix. `leg_gap_length` removes the segment
``|z| <= g/2`` from every leg and re-places each port box centred on its own leg
axis spanning exactly the gap, so the two stub cut faces *are* the box's
z-faces. Legs are axis-aligned cylinders, so those faces are planar disks with
the closed form ``pi*r_leg**2`` each — which is what makes this the cheap cut
(the end-ring alternative gives oblique torus sections at 45 degrees and no
closed form at all). Two of leg (a)'s open questions dissolve by construction:
the drive direction is ``z-hat`` for every port, and a square transverse section
makes the four-port layout exactly C4-invariant.

Mesh-only: no port model, no solve, no resonance claim. A gapped birdcage
without lumped elements still cannot resonate; the point here is that the
terminals now exist and the mesh identities survive the cut.
"""

from __future__ import annotations

import time

import numpy as np
from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator, _interface_facet_tags
from tests.mesh.helpers import global_cell_tag_set
from tests.mesh.test_coil_phantom_conforming import _tag_volume, _total_volume
from tests.mesh.test_birdcage_conductor_sizing import CAD_MASS_GATE
from tests.mesh.test_two_torus_port_facets import _facet_group_area
from tests.mesh.test_birdcage_port_sheet_prerequisite import (
    CELL_COUNT_BAND,
    CONDUCTOR_RESOLUTION,
    STEP3_CELL_COUNT_RECORD,
)
from tests.mesh.test_birdcage_port_terminals import (
    AIR_IFACE,
    CONDUCTOR_IFACE,
    PHANTOM_IFACE,
    _global_facet_count,
    _interface_area_or_zero,
)
from tests.mesh.test_birdcage_port_tags import (
    AIR_PADDING,
    COIL_LENGTH,
    LEG_COUNT,
    LEG_SPACING,
    LEG_WIDTH,
    PHANTOM_HEIGHT,
    PHANTOM_RADIUS,
    PORT_BOX_SIZE,
    RESOLUTION,
    RING_MINOR_RADIUS,
    RING_RADIUS,
)

# The gap. 8 mm on a 140 mm leg: long enough that the port box is not a sliver
# against the 1.6 mm conductor sizing, short enough to stay far clear of the
# rings (their inner face is at |z| = 51 mm) and to leave the coil recognisable.
LEG_GAP_LENGTH = 0.008

# Pre-stated band for the meshed terminal area against its closed form. The
# meshed disk is an *inscribed* triangulation of the stub's circular face, so
# the ratio must land at or below 1; leg (b)'s phantom<->air control read
# 0.971035 through this same machinery on the same fixture, which sets the
# scale of the lower end.
TERMINAL_AREA_BAND = (0.95, 1.0)

# `EX-21`'s recorded meshed/CAD conductor ratio for the *uncut* graded rung, the
# negative control's anchor. Restated here rather than imported because
# `EX-21`'s example holds it as a printed record, not as a module constant.
UNCUT_CAD_RATIO_RECORD = 0.967019
UNCUT_CAD_RATIO_BAND = 1.0e-4


def _analytic_box_volume(port_dy: float) -> float:
    """``8·radial_extent²·z_extent`` — the generator's own extents.

    Not imported from `test_birdcage_port_tags`: that copy hard-codes
    ``PORT_BOX_SIZE[1]`` for the radial extent, and the gapped variant *derives*
    a different transverse box size, so the air box is a different air box.
    """
    leg_radius_eff = 0.5 * LEG_WIDTH
    radial_extent = (
        RING_RADIUS + max(leg_radius_eff, RING_MINOR_RADIUS) + port_dy + AIR_PADDING
    )
    z_extent = (
        max(0.5 * COIL_LENGTH, 0.5 * LEG_SPACING + RING_MINOR_RADIUS, 0.5 * PHANTOM_HEIGHT)
        + AIR_PADDING
    )
    return 8.0 * radial_extent * radial_extent * z_extent


def _analytic_terminal_area() -> float:
    """Two planar disks per port: the two stub cut faces bounding the gap."""
    return 2.0 * np.pi * (0.5 * LEG_WIDTH) ** 2


def _analytic_removed_conductor_mass() -> float:
    """``leg_count · pi·r_leg²·g`` — what the cut takes out of the conductor.

    Exact, not approximate: the layout helper refuses a gap that reaches the
    rings, so every removed segment is a plain cylinder that overlaps nothing.
    """
    return LEG_COUNT * np.pi * (0.5 * LEG_WIDTH) ** 2 * LEG_GAP_LENGTH


def _build(leg_gap_length):
    """One graded birdcage rung, gapped or not, with its wall time."""
    comm = MPI.COMM_WORLD
    started = time.perf_counter()
    mesh, cell_tags, facet_tags, diagnostics = MeshGenerator.birdcage_port_domain(
        leg_count=LEG_COUNT,
        ring_radius=RING_RADIUS,
        leg_width=LEG_WIDTH,
        leg_spacing=LEG_SPACING,
        coil_length=COIL_LENGTH,
        ring_minor_radius=RING_MINOR_RADIUS,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        port_box_size=PORT_BOX_SIZE,
        leg_gap_length=leg_gap_length,
        air_padding=AIR_PADDING,
        resolution=RESOLUTION,
        conductor_resolution=CONDUCTOR_RESOLUTION,
        comm=comm,
        return_diagnostics=True,
    )
    return mesh, cell_tags, facet_tags, diagnostics, time.perf_counter() - started


def _port_boundary_partition(mesh, cell_tags, comm):
    """Per-port boundary areas against conductor / air / phantom.

    Leg (b)'s machinery verbatim, one rebuild for the whole set so
    `_interface_facet_tags` runs its own uniqueness check across it: no facet
    may be claimed by two groups.
    """
    port_tags = [100 + i for i in range(1, LEG_COUNT + 1)]
    interfaces = {}
    for i, tag in enumerate(port_tags, start=1):
        interfaces[CONDUCTOR_IFACE + i] = (tag, 1)
        interfaces[AIR_IFACE + i] = (tag, 2)
        interfaces[PHANTOM_IFACE + i] = (tag, 3)
    audit_tags = _interface_facet_tags(mesh, cell_tags, interfaces)
    counts = {t: _global_facet_count(mesh, audit_tags, t, comm) for t in interfaces}
    areas = {t: _interface_area_or_zero(mesh, audit_tags, t, comm) for t in interfaces}
    return counts, areas


def test_leg_gaps_give_every_port_two_disk_terminals():
    """The cut, measured; and the kwarg off, measured on the same machinery.

    1. **The finding** — per-port conductor-facing area against the closed form
       ``2·pi·r_leg²`` inside the pre-stated inscribed band, with the closure
       identity saying the partition is exhaustive so the number is the whole
       terminal and not part of one.
    2. **Mass** — the gapped conductor's CAD mass is the uncut CAD mass minus
       the four analytic segments (an exact identity, < 1e-9), and the graded
       mesh still keeps >= 0.95 of it. Never the uncut record as denominator.
    3. **Volumes** — each port region is the whole analytic gap box, and the
       `GEO-9` partition identities hold on the gapped mesh.
    4. **Negative control** — the same run with the kwarg off reproduces leg
       (b): conductor-facing area exactly 0 on all four ports, the 98 474-cell
       record, `EX-21`'s 0.967019.
    """
    comm = MPI.COMM_WORLD
    port_tags = [100 + i for i in range(1, LEG_COUNT + 1)]
    all_tags = [1, 2, 3, *port_tags]

    gap_mesh, gap_cells, _, gap_diag, gap_elapsed = _build(LEG_GAP_LENGTH)
    gap_dx, gap_dy, gap_dz = gap_diag["port_box_size_m"]
    assert global_cell_tag_set(gap_mesh, gap_cells) == set(all_tags)

    n_cells_gap = gap_mesh.topology.index_map(3).size_global
    v_gap = {t: _tag_volume(gap_mesh, gap_cells, t, comm) for t in all_tags}
    v_gap_total = _total_volume(gap_mesh, comm)
    cad_gap = gap_diag["cad_mass_by_group"]["conductor"]
    cad_ratio_gap = v_gap[1] / cad_gap
    counts_gap, areas_gap = _port_boundary_partition(gap_mesh, gap_cells, comm)

    box_area_gap = 2.0 * (gap_dx * gap_dy + gap_dy * gap_dz + gap_dz * gap_dx)
    box_volume_gap = gap_dx * gap_dy * gap_dz
    terminal_analytic = _analytic_terminal_area()

    # The control. Built second so the gapped rung's numbers are already in hand
    # if gmsh dies on the second build.
    unc_mesh, unc_cells, _, unc_diag, unc_elapsed = _build(None)
    assert global_cell_tag_set(unc_mesh, unc_cells) == set(all_tags)
    n_cells_unc = unc_mesh.topology.index_map(3).size_global
    v_unc = {t: _tag_volume(unc_mesh, unc_cells, t, comm) for t in all_tags}
    v_unc_total = _total_volume(unc_mesh, comm)
    cad_unc = unc_diag["cad_mass_by_group"]["conductor"]
    cad_ratio_unc = v_unc[1] / cad_unc
    counts_unc, areas_unc = _port_boundary_partition(unc_mesh, unc_cells, comm)

    removed_analytic = _analytic_removed_conductor_mass()
    removed_cad = cad_unc - cad_gap
    # The identity is asserted on the *mass*, not on the difference. Stating it
    # as `removed_cad / removed_analytic` subtracts two masses of order 1e-4 m^3
    # to get 3.6e-6 m^3 and amplifies each one's integration error by
    # 1.03e-4/3.62e-6 = 28x: measured 2026-08-20, that reading is 0.999999994733,
    # i.e. 5.27e-9 off — real cancellation, not a wrong geometry (the same run's
    # closure and port-volume identities are exactly 1.000000000000). Predicting
    # the gapped mass instead keeps the error on the O(1e-4) quantity where the
    # project's other CAD identities live, and it lands at 1.9e-10.
    cad_gap_predicted = cad_unc - removed_analytic

    if comm.rank == 0:
        print(
            f"\n[GEO-18 step 1] gapped birdcage g={LEG_GAP_LENGTH:.4e} m, "
            f"box=({gap_dx:.6e}, {gap_dy:.6e}, {gap_dz:.6e}) m, "
            f"h_c={CONDUCTOR_RESOLUTION:.4e} m: cells={n_cells_gap}  "
            f"meshed/CAD conductor={cad_ratio_gap:.6f}  "
            f"mesh={gap_diag['mesh_wall_time_s']:.2f} s  rung={gap_elapsed:.2f} s"
            f"\n[GEO-18 step 1] CAD conductor uncut={cad_unc:.9e} m^3  "
            f"gapped={cad_gap:.9e} m^3  removed={removed_cad:.9e} m^3  "
            f"analytic={removed_analytic:.9e} m^3  "
            f"difference ratio={removed_cad / removed_analytic:.12f}  "
            f"mass ratio={cad_gap / cad_gap_predicted:.12f}"
            f"\n[GEO-18 step 1] analytic terminal area (2 disks) "
            f"{terminal_analytic:.6e} m^2; analytic gap box surface "
            f"{box_area_gap:.6e} m^2, volume {box_volume_gap:.6e} m^3",
            flush=True,
        )
        for i in range(1, LEG_COUNT + 1):
            a_c = areas_gap[CONDUCTOR_IFACE + i]
            a_a = areas_gap[AIR_IFACE + i]
            a_p = areas_gap[PHANTOM_IFACE + i]
            print(
                f"[GEO-18 step 1] P{i}: conductor {counts_gap[CONDUCTOR_IFACE + i]} "
                f"facets {a_c:.6e} m^2 meshed/analytic={a_c / terminal_analytic:.9f}  "
                f"air {counts_gap[AIR_IFACE + i]} facets {a_a:.6e} m^2  "
                f"phantom {counts_gap[PHANTOM_IFACE + i]} facets {a_p:.6e} m^2  "
                f"closure {(a_c + a_a + a_p) / box_area_gap:.12f}  "
                f"volume/analytic {v_gap[100 + i] / box_volume_gap:.12f}",
                flush=True,
            )
        print(
            f"[GEO-18 step 1] control (kwarg off): cells={n_cells_unc} "
            f"(record {STEP3_CELL_COUNT_RECORD}, "
            f"ratio {n_cells_unc / STEP3_CELL_COUNT_RECORD:.6f})  "
            f"meshed/CAD conductor={cad_ratio_unc:.6f} "
            f"(record {UNCUT_CAD_RATIO_RECORD})  rung={unc_elapsed:.2f} s  "
            "conductor-facing areas "
            + " ".join(
                f"P{i}={areas_unc[CONDUCTOR_IFACE + i]:.6e}"
                for i in range(1, LEG_COUNT + 1)
            ),
            flush=True,
        )

    # 3. The gapped mesh is still a partition of the same air box (`GEO-9`).
    assert abs(v_gap_total / _analytic_box_volume(gap_dy) - 1.0) < 1e-9
    assert abs(sum(v_gap.values()) / v_gap_total - 1.0) < 1e-9
    for i in range(1, LEG_COUNT + 1):
        assert abs(v_gap[100 + i] / box_volume_gap - 1.0) < 1e-9, (
            f"port P{i} meshed volume {v_gap[100 + i]:.9e} m^3 against the "
            f"analytic gap box {box_volume_gap:.9e} m^3 — the box does not span "
            "the gap exactly, so its z-faces are not the stub cut faces"
        )

    # 2. Mass: the cut removed exactly the four analytic cylinders, and the
    #    graded mesh keeps its gate share of what is left.
    assert abs(cad_gap / cad_gap_predicted - 1.0) < 1e-9, (
        f"the gapped CAD conductor is {cad_gap:.9e} m^3 against the predicted "
        f"{cad_gap_predicted:.9e} m^3 = uncut {cad_unc:.9e} minus the analytic "
        f"{removed_analytic:.9e} (ratio {cad_gap / cad_gap_predicted:.12f}); the "
        "removed segments are not the four clean cylinders the closed forms "
        "above assume"
    )
    assert cad_ratio_gap >= CAD_MASS_GATE, (
        f"gapped graded conductor keeps {cad_ratio_gap:.6f} of its *own* CAD "
        f"mass {cad_gap:.9e} m^3, below the imported {CAD_MASS_GATE} gate"
    )

    # 1. The finding: each port box now meets metal on two disks.
    for i in range(1, LEG_COUNT + 1):
        total = (
            areas_gap[CONDUCTOR_IFACE + i]
            + areas_gap[AIR_IFACE + i]
            + areas_gap[PHANTOM_IFACE + i]
        )
        assert abs(total / box_area_gap - 1.0) < 1e-9, (
            f"port P{i} boundary areas sum to {total:.9e} m^2 against the "
            f"analytic box surface {box_area_gap:.9e} m^2 (ratio "
            f"{total / box_area_gap:.12f}); the partition is not exhaustive, so "
            "the terminal reading below would be a fragment, not the terminal"
        )
        ratio = areas_gap[CONDUCTOR_IFACE + i] / terminal_analytic
        low, high = TERMINAL_AREA_BAND
        assert low <= ratio <= high, (
            f"port P{i} terminal area {areas_gap[CONDUCTOR_IFACE + i]:.9e} m^2 is "
            f"{ratio:.9f} of the closed-form {terminal_analytic:.9e} m^2 (two "
            f"disks of radius {0.5 * LEG_WIDTH:.6e} m); an inscribed "
            f"triangulation must land in [{low}, {high}]"
        )
        assert areas_gap[PHANTOM_IFACE + i] == 0.0, (
            f"port P{i} touches the phantom ({areas_gap[PHANTOM_IFACE + i]:.6e} "
            "m^2); the gap box is supposed to meet metal and air only"
        )

    # C4 by construction, checked rather than assumed: the four terminals are
    # the same terminal, so their meshed areas may differ only by the mesh.
    terminals = np.array(
        [areas_gap[CONDUCTOR_IFACE + i] for i in range(1, LEG_COUNT + 1)]
    )
    assert terminals.std() / terminals.mean() < 0.02, (
        f"terminal areas {terminals} are not C4-symmetric to 2% "
        f"(spread {terminals.std() / terminals.mean():.6f}); the four ports are "
        "not the same port and gate (iii)'s circulant premise fails"
    )

    # 4. Negative control — the kwarg off is the geometry leg (b) measured.
    assert abs(n_cells_unc / STEP3_CELL_COUNT_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"kwarg off meshed {n_cells_unc} cells vs the record "
        f"{STEP3_CELL_COUNT_RECORD}; the opt-in changed the default geometry"
    )
    assert abs(cad_ratio_unc - UNCUT_CAD_RATIO_RECORD) < UNCUT_CAD_RATIO_BAND, (
        f"kwarg off keeps {cad_ratio_unc:.6f} of its CAD conductor mass vs "
        f"`EX-21`'s record {UNCUT_CAD_RATIO_RECORD}"
    )
    assert abs(v_unc_total / _analytic_box_volume(PORT_BOX_SIZE[1]) - 1.0) < 1e-9
    for i in range(1, LEG_COUNT + 1):
        assert counts_unc[CONDUCTOR_IFACE + i] == 0
        assert areas_unc[CONDUCTOR_IFACE + i] == 0.0, (
            f"kwarg off: port P{i} conductor-facing area "
            f"{areas_unc[CONDUCTOR_IFACE + i]:.6e} m^2 is not leg (b)'s exact "
            "zero — the opt-in is not opt-in"
        )
