"""`GEO-20` step 1 — the high-pass birdcage's ring-gap port layout at 4 legs.

`GEO-18` cut the *legs*, which is the low-pass drive element. A high-pass
birdcage drives the **end rings**: the gap sits at the mid-azimuth between each
adjacent leg pair, on both rings, so a 4-leg fixture carries ``2·4 = 8``
ring-gap ports (32 at the 16-leg production count — item (b) of the §10 32-port
directive).

The construction the leg-gap module called "the end-ring alternative ... oblique
torus sections at 45 degrees and no closed form at all" is the one where an
**axis-aligned** box cuts the ring. That is not what is built here. The gap is
cut by the two *radial* half-planes ``phi = phi_c ± alpha``,
``alpha = g/(2·R)``, which every partial-torus arc already ends on, so each cut
face is an exact planar disk of area ``pi·r_ring²`` — the closed form exists
precisely because the cut is radial. The port solid spanning the gap is then the
`GEO-18` box **rotated into the gap's own frame**: the wedge
``|phi − phi_c| <= alpha`` intersected with ``|z − z_ring| <= w/2`` and
``|u − R| <= w/2``, where ``u = rho·cos(phi − phi_c)`` is the radial coordinate
of that frame. All six of its faces are planar, so

* volume ``2·R·w²·tan(alpha)``,
* surface ``2·w²/cos(alpha) + 8·R·w·tan(alpha)``,
* mid-plane section ``w²`` (the sheet),

are exact under a linear mesh. A constant-``rho`` face would have made all three
faceting bands instead of identities.

Mesh-side only: no port model, no drive, no solve. A gapped birdcage without
lumped elements still cannot resonate; the point is that the ring terminals
exist and the mesh identities survive the cut.
"""

from __future__ import annotations

import time

import dolfinx
import numpy as np
from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator, _interface_facet_tags
from tests.mesh.helpers import global_cell_tag_set
from tests.mesh.test_coil_phantom_conforming import _tag_volume, _total_volume
from tests.mesh.test_birdcage_conductor_sizing import CAD_MASS_GATE
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
from tests.mesh.test_birdcage_leg_gaps import (
    LEG_GAP_LENGTH,
    TERMINAL_AREA_BAND,
    UNCUT_CAD_RATIO_BAND,
    UNCUT_CAD_RATIO_RECORD,
    _analytic_box_volume,
)
from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER, SHEET_IFACE
from tests.mesh.test_two_torus_port_sheet import _sheet_extents

# The ring gap. 8 mm of arc on a 70 mm ring is 0.114 rad — a sixth of the 0.785
# rad between the gap centre and the neighbouring leg, so the arc clearance to
# the leg surface (50.9 mm) is far larger than anything the mesh resolves. Same
# figure as `LEG_GAP_LENGTH` so the two families are compared at one length.
RING_GAP_LENGTH = 0.008

# Gate bands, all pre-stated in the `GEO-20` §7 entry.
EXACT = 1.0e-9              # closure, sheet area, GEO-9 partition
SYMMETRY = 1.0e-12          # C_N spread and top/bottom mirror on exact forms
TERMINAL_EQUALITY = 1.0e-5  # meshed terminal equality across the ring ports

RING_PORT_FIRST = LEG_COUNT + 1
RING_PORT_LAST = LEG_COUNT + 2 * LEG_COUNT
RING_PORTS = list(range(RING_PORT_FIRST, RING_PORT_LAST + 1))
# Build order is bottom ring then top, `leg_count` gaps each, so port
# ``RING_PORT_FIRST + j`` and ``RING_PORT_FIRST + LEG_COUNT + j`` are the same
# gap on the two rings — the mirror pair.
MIRROR_PAIRS = [
    (RING_PORT_FIRST + j, RING_PORT_FIRST + LEG_COUNT + j) for j in range(LEG_COUNT)
]


def _build(*, ring_gap_length, leg_gap_length=None, emit_port_sheets=False):
    """One graded birdcage rung with the requested gaps, and its wall time."""
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
        ring_gap_length=ring_gap_length,
        emit_port_sheets=emit_port_sheets,
        air_padding=AIR_PADDING,
        resolution=RESOLUTION,
        conductor_resolution=CONDUCTOR_RESOLUTION,
        comm=comm,
        return_diagnostics=True,
    )
    return mesh, cell_tags, facet_tags, diagnostics, time.perf_counter() - started


def _port_boundary_partition(mesh, cell_tags, comm, port_cell_tags):
    """Per-port boundary areas against conductor / air / phantom.

    `GEO-18` step 2's helper verbatim in behaviour: `port_cell_tags[i]` is the
    set of cell tags making up port ``i`` — one unsheeted, two sheeted — and
    summing the halves gives the port solid's *outer* boundary either way,
    because the sheet lies between the halves and so faces none of the three.
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


def _out_of_plane_spread(msh, facet_tags, tag, normal, point, comm) -> float:
    """Max ``|(p - point)·n|`` over one sheet's nodes [m].

    A ring sheet's plane is radial, so its normal is azimuthal and **no global
    coordinate is constant on it** — the two-torus/`GEO-18` planarity check
    (smallest bounding-box extent is zero) reads a diagonal rectangle's
    projected extents instead and cannot be reused. Measured 2026-08-24: P5's
    extents are (7.071068e-03, 7.071068e-03, 1.000000e-02), i.e. exactly the
    ``w = 1e-2`` rectangle seen edge-on at 45 degrees.
    """
    fdim = msh.topology.dim - 1
    facets = np.asarray(facet_tags.find(tag), dtype=np.int32)
    if facets.size:
        nodes = dolfinx.cpp.mesh.entities_to_geometry(
            msh._cpp_object, fdim, facets, False
        )
        pts = msh.geometry.x[nodes.reshape(-1)]
        local = float(np.abs((pts - np.asarray(point)) @ np.asarray(normal)).max())
    else:
        local = 0.0
    return float(comm.allreduce(local, op=MPI.MAX))


def _ring_gap_frame(ordinal):
    """``(phi_hat, gap centre)`` for a ring port, from its ordinal alone."""
    j = (ordinal - RING_PORT_FIRST) % LEG_COUNT
    z_sign = -1.0 if ordinal < RING_PORT_FIRST + LEG_COUNT else +1.0
    phi_c = 2.0 * np.pi * j / LEG_COUNT + np.pi / LEG_COUNT
    return (
        np.array([-np.sin(phi_c), np.cos(phi_c), 0.0]),
        np.array(
            [
                RING_RADIUS * np.cos(phi_c),
                RING_RADIUS * np.sin(phi_c),
                z_sign * 0.5 * LEG_SPACING,
            ]
        ),
    )


def _spread(values) -> float:
    a = np.asarray(values, dtype=float)
    return float(a.std() / a.mean())


def test_ring_gaps_give_every_end_ring_port_two_disk_terminals():
    """The high-pass layout, measured; and the kwarg off, on the same machinery.

    1. **Terminals** — each of the 8 ring ports meets metal on the two exact
       disks bounding its gap: area in the pre-stated inscribed band against
       ``2·pi·r_ring²``, equal across the 8 to 1e-5, with the closure identity
       saying the boundary partition is exhaustive so the reading is the whole
       terminal.
    2. **Mass** — the gapped CAD conductor is the uncut CAD conductor minus the
       ``2·leg_count`` analytic arc segments ``pi·r_ring²·g`` exactly (< 1e-9),
       and the graded mesh still keeps >= 0.95 of it.
    3. **Volumes and sheets** — every port region is its whole analytic wedge
       solid and every sheet its whole ``w²`` mid-section, both to 1e-9, with
       C4 spread and top/bottom mirror below 1e-12 on those exact forms; the
       `GEO-9` partition identities hold on the gapped mesh.
    4. **Negative control** — the same run with the kwarg off reproduces the
       uncut birdcage's cell-count record and `EX-21`'s 0.967019, and carries
       no ring port tag at all.
    """
    comm = MPI.COMM_WORLD

    mesh, cells, _, diag, elapsed = _build(
        ring_gap_length=RING_GAP_LENGTH, emit_port_sheets=True
    )
    layout = diag["ring_port_layout"]
    # Ring ports are sheeted; the four floating leg boxes are not (no gap in the
    # legs, so no terminals and nothing to split) — that asymmetry is the
    # high-pass fixture, and it is asserted rather than assumed.
    port_cell_tags = {i: (PORT_LOWER + i,) for i in range(1, LEG_COUNT + 1)}
    port_cell_tags.update({i: (PORT_LOWER + i, PORT_UPPER + i) for i in RING_PORTS})
    expected_tags = {1, 2, 3, *[t for tags in port_cell_tags.values() for t in tags]}
    assert global_cell_tag_set(mesh, cells) == expected_tags, (
        "the ring-gapped mesh does not carry both halves of every ring port as "
        "their own cell tags, so there is no interface to rebuild the sheet from"
    )

    n_cells = mesh.topology.index_map(3).size_global
    all_tags = sorted(expected_tags)
    volumes = {t: _tag_volume(mesh, cells, t, comm) for t in all_tags}
    v_total = _total_volume(mesh, comm)
    cad_gap = diag["cad_mass_by_group"]["conductor"]
    cad_ratio_gap = volumes[1] / cad_gap
    counts, areas = _port_boundary_partition(mesh, cells, comm, port_cell_tags)

    sheet_tags = _interface_facet_tags(
        mesh, cells, {SHEET_IFACE + i: port_cell_tags[i] for i in RING_PORTS}
    )
    sheet_area = {
        i: _interface_area_or_zero(mesh, sheet_tags, SHEET_IFACE + i, comm)
        for i in RING_PORTS
    }
    sheet_extent = {
        i: _sheet_extents(mesh, sheet_tags, SHEET_IFACE + i, comm) for i in RING_PORTS
    }
    sheet_count = {
        i: _global_facet_count(mesh, sheet_tags, SHEET_IFACE + i, comm)
        for i in RING_PORTS
    }
    sheet_flatness = {
        i: _out_of_plane_spread(
            mesh, sheet_tags, SHEET_IFACE + i, *_ring_gap_frame(i), comm
        )
        for i in RING_PORTS
    }

    terminal_analytic = layout["ring_terminal_area_m2"]
    port_volume = layout["ring_port_volume_m3"]
    port_surface = layout["ring_port_surface_m2"]
    sheet_analytic = layout["ring_port_sheet_area_m2"]
    port_total_volume = {
        i: sum(volumes[t] for t in port_cell_tags[i]) for i in RING_PORTS
    }

    # The control. Built second so the gapped rung's numbers are already in hand
    # if gmsh dies on the second build.
    unc_mesh, unc_cells, _, unc_diag, unc_elapsed = _build(ring_gap_length=None)
    unc_tags = {1, 2, 3, *[100 + i for i in range(1, LEG_COUNT + 1)]}
    assert global_cell_tag_set(unc_mesh, unc_cells) == unc_tags, (
        "the kwarg off does not reproduce the four-port uncut birdcage — the "
        "opt-in is not opt-in"
    )
    n_cells_unc = unc_mesh.topology.index_map(3).size_global
    v_unc_total = _total_volume(unc_mesh, comm)
    cad_unc = unc_diag["cad_mass_by_group"]["conductor"]
    cad_ratio_unc = _tag_volume(unc_mesh, unc_cells, 1, comm) / cad_unc

    removed_analytic = layout["ring_removed_mass_m3"]
    cad_gap_predicted = cad_unc - removed_analytic
    # The identity that is actually a claim about *this* construction: Pappus on
    # the ring primitives before any boolean, `pi·r²·R·angle` per sweep. The
    # union form below (gapped conductor = uncut conductor - removed arcs) is
    # recorded rather than gated: it is a difference of two O(1e-4) OCC unions
    # over 28 vs 20 curved pieces, so it carries their quadrature error, not a
    # statement about the arcs. `GEO-18` step 1 hit the same amplification on
    # the leg cut and moved its assertion off the difference for the same
    # reason; there the primitive was a cylinder and needed no separate check.
    ring_primitive = diag["ring_cad_mass_m3"] / diag["ring_analytic_mass_m3"]
    ring_primitive_unc = (
        unc_diag["ring_cad_mass_m3"] / unc_diag["ring_analytic_mass_m3"]
    )

    if comm.rank == 0:
        print(
            f"\n[GEO-20 step 1] ring-gapped birdcage g={RING_GAP_LENGTH:.4e} m, "
            f"alpha={layout['ring_gap_half_angle_rad']:.9e} rad, "
            f"w={layout['ring_port_box_width_m']:.6e} m, "
            f"h_c={CONDUCTOR_RESOLUTION:.4e} m: cells={n_cells}  "
            f"ports={len(port_cell_tags)} ({LEG_COUNT} leg + "
            f"{len(RING_PORTS)} ring)  meshed/CAD conductor={cad_ratio_gap:.6f}  "
            f"mesh={diag['mesh_wall_time_s']:.2f} s  rung={elapsed:.2f} s"
            f"\n[GEO-20 step 1] leg-arc clearance "
            f"{layout['ring_leg_arc_clearance_m']:.6e} m, phantom clearance "
            f"{layout['ring_phantom_radial_clearance_m']:.6e} m"
            f"\n[GEO-20 step 1] CAD conductor uncut={cad_unc:.9e} m^3  "
            f"gapped={cad_gap:.9e} m^3  removed analytic={removed_analytic:.9e} "
            f"m^3  union mass ratio={cad_gap / cad_gap_predicted:.12f}"
            f"\n[GEO-20 step 1] ring primitives (Pappus, pre-boolean): gapped "
            f"{diag['ring_cad_mass_m3']:.12e} / "
            f"{diag['ring_analytic_mass_m3']:.12e} = {ring_primitive:.12f}; "
            f"uncut {unc_diag['ring_cad_mass_m3']:.12e} / "
            f"{unc_diag['ring_analytic_mass_m3']:.12e} = "
            f"{ring_primitive_unc:.12f}"
            f"\n[GEO-20 step 1] closed forms: terminal (2 disks) "
            f"{terminal_analytic:.9e} m^2, port volume {port_volume:.9e} m^3, "
            f"port surface {port_surface:.9e} m^2, sheet {sheet_analytic:.9e} m^2",
            flush=True,
        )
        for i in RING_PORTS:
            a_c = areas[CONDUCTOR_IFACE + i]
            a_a = areas[AIR_IFACE + i]
            a_p = areas[PHANTOM_IFACE + i]
            print(
                f"[GEO-20 step 1] P{i}: conductor {counts[CONDUCTOR_IFACE + i]} "
                f"facets {a_c:.9e} m^2 meshed/analytic={a_c / terminal_analytic:.9f}"
                f"  air {counts[AIR_IFACE + i]} facets {a_a:.9e} m^2  phantom "
                f"{a_p:.6e} m^2  closure {(a_c + a_a + a_p) / port_surface:.12f}  "
                f"volume/analytic {port_total_volume[i] / port_volume:.12f}  "
                f"sheet {sheet_count[i]} facets {sheet_area[i]:.9e} m^2 "
                f"meshed/analytic={sheet_area[i] / sheet_analytic:.12f}  "
                f"extents=({sheet_extent[i][0]:.6e}, {sheet_extent[i][1]:.6e}, "
                f"{sheet_extent[i][2]:.6e})  out-of-plane "
                f"{sheet_flatness[i]:.3e} m",
                flush=True,
            )
        print(
            f"[GEO-20 step 1] control (kwarg off): cells={n_cells_unc} "
            f"(record {STEP3_CELL_COUNT_RECORD}, "
            f"ratio {n_cells_unc / STEP3_CELL_COUNT_RECORD:.6f})  "
            f"meshed/CAD conductor={cad_ratio_unc:.6f} "
            f"(record {UNCUT_CAD_RATIO_RECORD})  rung={unc_elapsed:.2f} s",
            flush=True,
        )

    # 3. `GEO-9`: the ring-gapped mesh is still a partition of the same air box.
    assert abs(v_total / _analytic_box_volume(PORT_BOX_SIZE[1]) - 1.0) < EXACT
    assert abs(sum(volumes.values()) / v_total - 1.0) < EXACT

    # 2. Mass: the arcs are the arcs asked for, by Pappus on the primitives.
    assert abs(ring_primitive - 1.0) < EXACT, (
        f"the {2 * LEG_COUNT} ring arcs have CAD mass "
        f"{diag['ring_cad_mass_m3']:.12e} m^3 against Pappus' "
        f"{diag['ring_analytic_mass_m3']:.12e} m^3 (ratio {ring_primitive:.12f})"
        f"; the swept angle is not `2*pi/N - g/R` and the removed arc is not "
        f"{RING_GAP_LENGTH:.4e} m long"
    )
    assert abs(ring_primitive_unc - 1.0) < EXACT, (
        "control: the two uncut tori do not satisfy Pappus to "
        f"{EXACT} (ratio {ring_primitive_unc:.12f}), so the gapped reading "
        "above is about OCC, not about the arcs"
    )
    assert cad_ratio_gap >= CAD_MASS_GATE, (
        f"ring-gapped graded conductor keeps {cad_ratio_gap:.6f} of its *own* "
        f"CAD mass {cad_gap:.9e} m^3, below the imported {CAD_MASS_GATE} gate"
    )

    # 1. and 3. per port.
    for i in RING_PORTS:
        a_c = areas[CONDUCTOR_IFACE + i]
        total = a_c + areas[AIR_IFACE + i] + areas[PHANTOM_IFACE + i]
        assert abs(total / port_surface - 1.0) < EXACT, (
            f"ring port P{i} boundary areas sum to {total:.9e} m^2 against the "
            f"analytic wedge surface {port_surface:.9e} m^2 (ratio "
            f"{total / port_surface:.12f}); the partition is not exhaustive, so "
            "the terminal reading below would be a fragment, not the terminal"
        )
        assert abs(port_total_volume[i] / port_volume - 1.0) < EXACT, (
            f"ring port P{i} meshed volume {port_total_volume[i]:.9e} m^3 "
            f"against the analytic wedge {port_volume:.9e} m^3 — the solid does "
            "not span the gap exactly, so its radial faces are not the ring's "
            "cut faces"
        )
        low, high = TERMINAL_AREA_BAND
        ratio = a_c / terminal_analytic
        assert low <= ratio <= high, (
            f"ring port P{i} terminal area {a_c:.9e} m^2 is {ratio:.9f} of the "
            f"closed-form {terminal_analytic:.9e} m^2 (two disks of radius "
            f"{RING_MINOR_RADIUS:.6e} m); an inscribed triangulation must land "
            f"in [{low}, {high}]"
        )
        assert areas[PHANTOM_IFACE + i] == 0.0, (
            f"ring port P{i} touches the phantom "
            f"({areas[PHANTOM_IFACE + i]:.6e} m^2); the gap solid is supposed "
            "to meet metal and air only"
        )
        assert abs(sheet_area[i] / sheet_analytic - 1.0) < EXACT, (
            f"ring port P{i} sheet area {sheet_area[i]:.9e} m^2 against the "
            f"analytic mid-section {sheet_analytic:.9e} m^2 (ratio "
            f"{sheet_area[i] / sheet_analytic:.12f}); the reconstructed facet "
            "set is not the whole w x w rectangle"
        )
        # Planar to roundoff, measured along the sheet's own azimuthal normal.
        assert sheet_flatness[i] < SYMMETRY, (
            f"ring port P{i} sheet is {sheet_flatness[i]:.3e} m out of its own "
            f"radial plane (extents {sheet_extent[i]}); the reconstructed facet "
            "set is not the mid-section"
        )

    # C4 and the ring mirror, on the exact forms rather than the banded ones.
    for label, values in (
        ("volume", [port_total_volume[i] for i in RING_PORTS]),
        ("sheet", [sheet_area[i] for i in RING_PORTS]),
    ):
        assert _spread(values) < SYMMETRY, (
            f"ring port {label}s {values} are not C4-symmetric to {SYMMETRY} "
            f"(spread {_spread(values):.3e}); the eight ring ports are not the "
            "same port"
        )
    for lo_port, hi_port in MIRROR_PAIRS:
        for label, table in (("volume", port_total_volume), ("sheet", sheet_area)):
            lo_v, hi_v = table[lo_port], table[hi_port]
            assert abs(hi_v / lo_v - 1.0) < SYMMETRY, (
                f"ring {label} mirror pair P{lo_port}/P{hi_port} reads "
                f"{lo_v:.12e} / {hi_v:.12e} (ratio {hi_v / lo_v:.12f}); the top "
                "and bottom rings are not mirror images"
            )

    terminals = np.array([areas[CONDUCTOR_IFACE + i] for i in RING_PORTS])
    assert _spread(terminals) < TERMINAL_EQUALITY, (
        f"ring terminal areas {terminals} are not equal to "
        f"{TERMINAL_EQUALITY} (spread {_spread(terminals):.3e}); the eight "
        "ports are not the same port and a circulant premise would fail"
    )

    # 4. Negative control.
    assert abs(n_cells_unc / STEP3_CELL_COUNT_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"kwarg off meshed {n_cells_unc} cells vs the record "
        f"{STEP3_CELL_COUNT_RECORD}; the opt-in changed the default geometry"
    )
    assert abs(cad_ratio_unc - UNCUT_CAD_RATIO_RECORD) < UNCUT_CAD_RATIO_BAND, (
        f"kwarg off keeps {cad_ratio_unc:.6f} of its CAD conductor mass vs "
        f"`EX-21`'s record {UNCUT_CAD_RATIO_RECORD}"
    )
    assert abs(v_unc_total / _analytic_box_volume(PORT_BOX_SIZE[1]) - 1.0) < EXACT


def test_leg_and_ring_gaps_coexist_as_a_twelve_port_mesh():
    """Both gap families at once: 4 leg ports + 8 ring ports, both identities.

    The two opt-ins are independent by construction — the leg gap is a z-cut on
    the leg axis, the ring gap an azimuthal cut at the mid-azimuth — and this is
    the check that they do not interact. Every port carries a sheet here, so the
    12-port mesh is the one a `PORT-9`-style assembly would consume.
    """
    comm = MPI.COMM_WORLD
    mesh, cells, _, diag, elapsed = _build(
        ring_gap_length=RING_GAP_LENGTH,
        leg_gap_length=LEG_GAP_LENGTH,
        emit_port_sheets=True,
    )
    layout = diag["ring_port_layout"]
    leg_ports = list(range(1, LEG_COUNT + 1))
    port_cell_tags = {
        i: (PORT_LOWER + i, PORT_UPPER + i) for i in leg_ports + RING_PORTS
    }
    expected_tags = {1, 2, 3, *[t for tags in port_cell_tags.values() for t in tags]}
    assert global_cell_tag_set(mesh, cells) == expected_tags, (
        "the doubly-gapped mesh does not carry all 12 ports as split cell-tag "
        "pairs"
    )

    n_cells = mesh.topology.index_map(3).size_global
    volumes = {t: _tag_volume(mesh, cells, t, comm) for t in sorted(expected_tags)}
    v_total = _total_volume(mesh, comm)
    counts, areas = _port_boundary_partition(mesh, cells, comm, port_cell_tags)

    gap_dx, gap_dy, gap_dz = diag["port_box_size_m"]
    leg_surface = 2.0 * (gap_dx * gap_dy + gap_dy * gap_dz + gap_dz * gap_dx)
    leg_volume = gap_dx * gap_dy * gap_dz
    leg_terminal = 2.0 * np.pi * (0.5 * LEG_WIDTH) ** 2
    ring_surface = layout["ring_port_surface_m2"]
    ring_volume = layout["ring_port_volume_m3"]
    ring_terminal = layout["ring_terminal_area_m2"]

    if comm.rank == 0:
        print(
            f"\n[GEO-20 step 1] leg+ring gapped birdcage: cells={n_cells}  "
            f"ports={len(port_cell_tags)}  mesh={diag['mesh_wall_time_s']:.2f} s "
            f" rung={elapsed:.2f} s",
            flush=True,
        )
        for i in leg_ports + RING_PORTS:
            family = "leg " if i in leg_ports else "ring"
            surface = leg_surface if i in leg_ports else ring_surface
            volume = leg_volume if i in leg_ports else ring_volume
            terminal = leg_terminal if i in leg_ports else ring_terminal
            a_c = areas[CONDUCTOR_IFACE + i]
            total = a_c + areas[AIR_IFACE + i] + areas[PHANTOM_IFACE + i]
            v = sum(volumes[t] for t in port_cell_tags[i])
            print(
                f"[GEO-20 step 1] {family} P{i}: terminal {a_c:.9e} m^2 "
                f"meshed/analytic={a_c / terminal:.9f}  closure "
                f"{total / surface:.12f}  volume/analytic {v / volume:.12f}",
                flush=True,
            )

    assert abs(v_total / _analytic_box_volume(gap_dy) - 1.0) < EXACT
    assert abs(sum(volumes.values()) / v_total - 1.0) < EXACT
    low, high = TERMINAL_AREA_BAND
    for i in leg_ports + RING_PORTS:
        surface = leg_surface if i in leg_ports else ring_surface
        volume = leg_volume if i in leg_ports else ring_volume
        terminal = leg_terminal if i in leg_ports else ring_terminal
        a_c = areas[CONDUCTOR_IFACE + i]
        total = a_c + areas[AIR_IFACE + i] + areas[PHANTOM_IFACE + i]
        v = sum(volumes[t] for t in port_cell_tags[i])
        assert abs(total / surface - 1.0) < EXACT, (
            f"port P{i} closure {total / surface:.12f} on the doubly-gapped mesh"
        )
        assert abs(v / volume - 1.0) < EXACT, (
            f"port P{i} volume/analytic {v / volume:.12f} on the doubly-gapped "
            "mesh — the two gap families interact"
        )
        assert low <= a_c / terminal <= high, (
            f"port P{i} terminal ratio {a_c / terminal:.9f} outside "
            f"[{low}, {high}] on the doubly-gapped mesh"
        )
