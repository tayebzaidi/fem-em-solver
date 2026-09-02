"""`GEO-18` step 2 — the port-sheet mid-plane on the gapped birdcage legs.

Step 1 cut the legs, so every port box now meets metal on two planar disks
(2.236196e-04 m² per port, 0.988616 of the closed form). What it did not give is
the *sheet*: the surface a lumped-element port model puts its impressed source
on. `GEO-16` built that for the two-torus fixture by adding the gap box's own
mid-section to the fragment as a dim-2 tool, carrying the halves as separate
cell tags, and rebuilding the interface dolfinx-side. This module measures the
same construction on the leg gaps.

The plane contains the leg axis and the radial direction, so the sheet spans the
gap along the current direction ``ẑ`` (``h = g``) and the box transversely
(``w = dx``): a full rectangle of closed-form area ``dx·g``, which is what makes
the identity here exact rather than banded. Per `PORT-9` step 2b the width that
counts is the area-based effective width ``A/h``, and for a full rectangle that
must equal the bounding-box extent — a mismatch means the reconstructed facet
set is not the whole mid-section.

Mesh-side only: no port model, no solve, no impedance or resonance claim.
"""

from __future__ import annotations

import time

import numpy as np
from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator, _interface_facet_tags
from tests.mesh.helpers import global_cell_tag_set
from tests.mesh.test_coil_phantom_conforming import _tag_volume, _total_volume
from tests.mesh.test_birdcage_port_sheet_prerequisite import CONDUCTOR_RESOLUTION
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
from tests.mesh.test_birdcage_leg_gaps import (
    LEG_GAP_LENGTH,
    TERMINAL_AREA_BAND,
    _analytic_box_volume,
    _analytic_terminal_area,
)
from tests.mesh.test_two_torus_port_sheet import _sheet_extents

# Step 1's records on this fixture, the negative control's anchors. Restated
# rather than imported: they are printed records in the `GEO-18` step-1 §7 entry
# and its log, not module constants.
STEP1_CELL_COUNT = 114846
STEP1_CELL_COUNT_BAND = 0.02
STEP1_TERMINAL_RATIO = 0.988616
STEP1_TERMINAL_RATIO_BAND = 1.0e-5

# Interface facet tags for the reconstructed sheets, one per port.
SHEET_IFACE = 210

# Lower/upper cell tags of a split port box, as the generator writes them.
PORT_LOWER = 100
# `GEO-19` widened the upper base 110 -> 200 so the encoding survives
# leg_count > 9 (at 16 legs, 110+i overlaps 100+i for i >= 11); the lower
# tags are untouched, so every 4-leg value here is the value step 2 recorded.
PORT_UPPER = 200


def _build(emit_port_sheets, phantom_resolution=None):
    """One graded, gapped birdcage rung, sheeted or not, with its wall time.

    ``phantom_resolution`` is `WF-6` step 3f₀'s additive keyword (the
    `frequency_hz` / `reuse` precedent in
    `tests/validation/test_port_birdcage_four_port.build_four_port_sweep`):
    ``None``, the default every gate in this repo takes, passes ``None`` down
    to `birdcage_port_domain` and so builds the identical mesh this helper has
    always built.
    """
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
        leg_gap_length=LEG_GAP_LENGTH,
        emit_port_sheets=emit_port_sheets,
        air_padding=AIR_PADDING,
        resolution=RESOLUTION,
        conductor_resolution=CONDUCTOR_RESOLUTION,
        phantom_resolution=phantom_resolution,
        comm=comm,
        return_diagnostics=True,
    )
    return mesh, cell_tags, facet_tags, diagnostics, time.perf_counter() - started


def _port_boundary_partition(mesh, cell_tags, comm, port_cell_tags):
    """Per-port boundary areas against conductor / air / phantom.

    `port_cell_tags[i]` is the set of cell tags that make up port ``i`` — one
    tag unsheeted, the two halves sheeted. Summing the halves' interfaces gives
    the box's *outer* boundary either way: the sheet itself lies between the two
    halves and so appears against neither conductor, air nor phantom, which is
    exactly why the closure identity is the same identity in both modes.
    """
    interfaces = {}
    for i, tags in port_cell_tags.items():
        for j, tag in enumerate(tags):
            interfaces[(CONDUCTOR_IFACE + i) * 10 + j] = (tag, 1)
            interfaces[(AIR_IFACE + i) * 10 + j] = (tag, 2)
            interfaces[(PHANTOM_IFACE + i) * 10 + j] = (tag, 3)
    audit_tags = _interface_facet_tags(mesh, cell_tags, interfaces)
    counts, areas = {}, {}
    for base in (CONDUCTOR_IFACE, AIR_IFACE, PHANTOM_IFACE):
        for i, tags in port_cell_tags.items():
            keys = [(base + i) * 10 + j for j in range(len(tags))]
            counts[base + i] = sum(
                _global_facet_count(mesh, audit_tags, k, comm) for k in keys
            )
            areas[base + i] = sum(
                _interface_area_or_zero(mesh, audit_tags, k, comm) for k in keys
            )
    return counts, areas


def test_port_sheets_are_the_gap_box_mid_sections():
    """The split, measured; and the kwarg off, measured on the same machinery.

    1. **The sheet** — each reconstructed interface facet set has the analytic
       mid-section area ``dx·g`` to 1e-9, lies in a plane to 1e-12 m, and its
       effective width ``A/h`` equals its bounding-box transverse extent, so the
       facet set is the *whole* section and not a fragment of one.
    2. **The halves** — each port's two cell groups are half the step-1 gap box
       to 1e-9, and the `GEO-9` partition identities still hold.
    3. **Step 1's gates, re-asserted on the sheeted mesh** — terminal ratio in
       the pre-stated inscribed band, closure exhaustive, four sheets equal.
    4. **Negative control** — the same build with sheets off reproduces step 1
       (114 846 cells, 0.988616) and carries no ``200+i`` cell tag and no
       ``210+i`` facet group at all.
    """
    comm = MPI.COMM_WORLD
    ports = list(range(1, LEG_COUNT + 1))

    mesh, cells, _, diag, elapsed = _build(True)
    dx, dy, dz = diag["port_box_size_m"]
    halves = {i: (PORT_LOWER + i, PORT_UPPER + i) for i in ports}
    expected_tags = {1, 2, 3, *[t for pair in halves.values() for t in pair]}
    assert global_cell_tag_set(mesh, cells) == expected_tags, (
        "the sheeted mesh does not carry both halves of every port box as their "
        "own cell tags, so there is no interface to rebuild the sheet from"
    )

    n_cells = mesh.topology.index_map(3).size_global
    all_tags = [1, 2, 3, *[t for pair in halves.values() for t in pair]]
    volumes = {t: _tag_volume(mesh, cells, t, comm) for t in all_tags}
    v_total = _total_volume(mesh, comm)
    counts, areas = _port_boundary_partition(mesh, cells, comm, halves)

    sheet_tags = _interface_facet_tags(
        mesh, cells, {SHEET_IFACE + i: halves[i] for i in ports}
    )
    sheet_area = {
        i: _interface_area_or_zero(mesh, sheet_tags, SHEET_IFACE + i, comm)
        for i in ports
    }
    sheet_extent = {
        i: _sheet_extents(mesh, sheet_tags, SHEET_IFACE + i, comm) for i in ports
    }
    # Collective: every rank must enter it, so it cannot live inside the rank-0
    # record print (attempt 1, 2026-08-22 — rank 0 blocked in the allreduce and
    # the command timed out at exit 124 with both tests green on rank 1).
    sheet_count = {
        i: _global_facet_count(mesh, sheet_tags, SHEET_IFACE + i, comm) for i in ports
    }

    box_area = 2.0 * (dx * dy + dy * dz + dz * dx)
    box_volume = dx * dy * dz
    sheet_analytic = dx * dz
    terminal_analytic = _analytic_terminal_area()

    # The control, built second so the sheeted numbers are in hand if gmsh dies
    # on the second build (step 1's ordering, same reason).
    ctl_mesh, ctl_cells, _, ctl_diag, ctl_elapsed = _build(False)
    ctl_tag_set = global_cell_tag_set(ctl_mesh, ctl_cells)
    n_cells_ctl = ctl_mesh.topology.index_map(3).size_global
    ctl_counts, ctl_areas = _port_boundary_partition(
        ctl_mesh, ctl_cells, comm, {i: (PORT_LOWER + i,) for i in ports}
    )

    if comm.rank == 0:
        print(
            f"\n[GEO-18 step 2] sheeted birdcage g={LEG_GAP_LENGTH:.4e} m, "
            f"box=({dx:.6e}, {dy:.6e}, {dz:.6e}) m, h_c={CONDUCTOR_RESOLUTION:.4e} m: "
            f"cells={n_cells}  mesh={diag['mesh_wall_time_s']:.2f} s  "
            f"rung={elapsed:.2f} s"
            f"\n[GEO-18 step 2] analytic sheet area dx*g={sheet_analytic:.9e} m^2; "
            f"analytic gap box volume={box_volume:.9e} m^3, "
            f"surface={box_area:.9e} m^2; analytic terminal (2 disks)="
            f"{terminal_analytic:.6e} m^2",
            flush=True,
        )
        for i in ports:
            w_bbox, h_bbox, spread = _sheet_axes(sheet_extent[i], diag, i)
            a_c = areas[CONDUCTOR_IFACE + i]
            a_a = areas[AIR_IFACE + i]
            a_p = areas[PHANTOM_IFACE + i]
            print(
                f"[GEO-18 step 2] P{i}: sheet "
                f"{sheet_count[i]} "
                f"facets {sheet_area[i]:.9e} m^2 "
                f"meshed/analytic={sheet_area[i] / sheet_analytic:.12f}  "
                f"h={h_bbox:.9e} m  w_bbox={w_bbox:.9e} m  "
                f"w_eff=A/h={sheet_area[i] / h_bbox:.9e} m  "
                f"w_eff/w_bbox={sheet_area[i] / h_bbox / w_bbox:.12f}  "
                f"out-of-plane spread={spread:.3e} m  "
                f"halves {volumes[PORT_LOWER + i] / box_volume:.12f}/"
                f"{volumes[PORT_UPPER + i] / box_volume:.12f} of the box  "
                f"terminal {counts[CONDUCTOR_IFACE + i]} facets {a_c:.6e} m^2 "
                f"meshed/analytic={a_c / terminal_analytic:.9f}  "
                f"closure {(a_c + a_a + a_p) / box_area:.12f}",
                flush=True,
            )
        sheets = np.array([sheet_area[i] for i in ports])
        print(
            f"[GEO-18 step 2] C4 sheet spread="
            f"{(sheets.max() - sheets.min()) / sheets.mean():.3e}"
            f"\n[GEO-18 step 2] control (sheets off): cells={n_cells_ctl} "
            f"(record {STEP1_CELL_COUNT}, "
            f"ratio {n_cells_ctl / STEP1_CELL_COUNT:.6f})  cell tags "
            f"{sorted(ctl_tag_set)}  rung={ctl_elapsed:.2f} s  terminal ratios "
            + " ".join(
                f"P{i}={ctl_areas[CONDUCTOR_IFACE + i] / terminal_analytic:.6f}"
                for i in ports
            ),
            flush=True,
        )

    # 2. The halves partition the same box, and the mesh the same air domain.
    assert abs(v_total / _analytic_box_volume(dy) - 1.0) < 1e-9
    assert abs(sum(volumes.values()) / v_total - 1.0) < 1e-9
    for i in ports:
        for tag in halves[i]:
            assert abs(volumes[tag] / box_volume - 0.5) < 1e-9, (
                f"port P{i} cell tag {tag} is {volumes[tag] / box_volume:.12f} of "
                f"the analytic gap box {box_volume:.9e} m^3, not the half the "
                "mid-plane split must give; the plane does not pass through the "
                "box centre, i.e. not through the leg axis"
            )

    # 1. The sheet: the whole mid-section, in a plane, at its closed-form area.
    for i in ports:
        w_bbox, h_bbox, spread = _sheet_axes(sheet_extent[i], diag, i)
        assert spread < 1e-12, (
            f"port P{i}'s sheet facets spread {spread:.3e} m out of their own "
            "plane; the reconstructed interface is not planar"
        )
        assert abs(h_bbox / dz - 1.0) < 1e-9, (
            f"port P{i}'s sheet runs {h_bbox:.9e} m along the current direction "
            f"against the gap {dz:.9e} m; it does not span the gap"
        )
        assert abs(sheet_area[i] / sheet_analytic - 1.0) < 1e-9, (
            f"port P{i}'s sheet area {sheet_area[i]:.9e} m^2 against the analytic "
            f"mid-section dx*g={sheet_analytic:.9e} m^2 (ratio "
            f"{sheet_area[i] / sheet_analytic:.12f}); a planar rectangle meshed by "
            "a conforming fragment has no discretisation error to spend here"
        )
        assert abs(sheet_area[i] / h_bbox / w_bbox - 1.0) < 1e-9, (
            f"port P{i}'s effective width A/h={sheet_area[i] / h_bbox:.9e} m "
            f"differs from its bounding-box extent {w_bbox:.9e} m; by `PORT-9` "
            "step 2b these are equal exactly when the facet set is the full "
            "rectangle, so this one is ragged or partial"
        )

    # 3. Step 1's gates survive the split.
    for i in ports:
        total = (
            areas[CONDUCTOR_IFACE + i]
            + areas[AIR_IFACE + i]
            + areas[PHANTOM_IFACE + i]
        )
        assert abs(total / box_area - 1.0) < 1e-9, (
            f"port P{i}'s two halves bound {total:.9e} m^2 against the analytic "
            f"box surface {box_area:.9e} m^2 (ratio {total / box_area:.12f}); the "
            "split leaked boundary, so the terminal reading is not the terminal"
        )
        ratio = areas[CONDUCTOR_IFACE + i] / terminal_analytic
        low, high = TERMINAL_AREA_BAND
        assert low <= ratio <= high, (
            f"port P{i}'s terminal area {areas[CONDUCTOR_IFACE + i]:.9e} m^2 is "
            f"{ratio:.9f} of the closed form {terminal_analytic:.9e} m^2, outside "
            f"step 1's inscribed band [{low}, {high}]"
        )
        assert areas[PHANTOM_IFACE + i] == 0.0

    sheets = np.array([sheet_area[i] for i in ports])
    assert (sheets.max() - sheets.min()) / sheets.mean() < 1e-12, (
        f"the four sheet areas {sheets} differ by "
        f"{(sheets.max() - sheets.min()) / sheets.mean():.3e} relative; the ports "
        "are not C4-equivalent and gate (iii)'s circulant premise fails"
    )

    # 4. Negative control — sheets off is step 1's mesh, with no half tags and
    #    no sheet to find (the `EX-23` inverted pattern).
    assert ctl_tag_set == {1, 2, 3, *[PORT_LOWER + i for i in ports]}, (
        f"sheets off carries cell tags {sorted(ctl_tag_set)}; the opt-in split "
        "the boxes anyway"
    )
    for i in ports:
        assert PORT_UPPER + i not in ctl_tag_set
    assert abs(n_cells_ctl / STEP1_CELL_COUNT - 1.0) < STEP1_CELL_COUNT_BAND, (
        f"sheets off meshed {n_cells_ctl} cells vs step 1's record "
        f"{STEP1_CELL_COUNT}; the opt-in changed the gapped geometry"
    )
    for i in ports:
        total = (
            ctl_areas[CONDUCTOR_IFACE + i]
            + ctl_areas[AIR_IFACE + i]
            + ctl_areas[PHANTOM_IFACE + i]
        )
        assert abs(total / box_area - 1.0) < 1e-9
        assert (
            abs(
                ctl_areas[CONDUCTOR_IFACE + i] / terminal_analytic
                - STEP1_TERMINAL_RATIO
            )
            < STEP1_TERMINAL_RATIO_BAND
        ), (
            f"sheets off: port P{i}'s terminal ratio "
            f"{ctl_areas[CONDUCTOR_IFACE + i] / terminal_analytic:.6f} vs step 1's "
            f"record {STEP1_TERMINAL_RATIO}"
        )
        assert ctl_counts[CONDUCTOR_IFACE + i] > 0


def _sheet_axes(extent, diagnostics, ordinal):
    """``(w_bbox, h, out-of-plane spread)`` from a sheet's ``(dx, dy, dz)`` box.

    Which of x and y is transverse depends on the port's azimuth — the plane is
    y-normal for a leg on the x-axis and x-normal for one on the y-axis — so the
    pinned axis is read off the measurement (the smaller of the two) rather than
    assumed. ``h`` is always z: the current runs along the leg.
    """
    spread = min(extent[0], extent[1])
    w_bbox = max(extent[0], extent[1])
    return w_bbox, extent[2], spread


def test_sheet_kwarg_requires_the_gap():
    """Sheets without a gap is a rejected call, not a silently ignored one."""
    try:
        MeshGenerator.birdcage_port_domain(
            leg_count=LEG_COUNT,
            ring_radius=RING_RADIUS,
            leg_width=LEG_WIDTH,
            leg_spacing=LEG_SPACING,
            coil_length=COIL_LENGTH,
            emit_port_sheets=True,
            comm=MPI.COMM_SELF,
        )
    except ValueError as exc:
        assert "leg_gap_length" in str(exc)
    else:  # pragma: no cover — the guard is the point of the test
        raise AssertionError(
            "emit_port_sheets without leg_gap_length was accepted; there is no "
            "box on the leg to split, so the sheet would be silently absent"
        )
