"""`PORT-9` step 3, leg (b) — does the birdcage port box have *terminals*?

Leg (a) (`test_birdcage_port_sheet_prerequisite.py`) measured that the birdcage
carries no port-sheet mid-plane facet, and prescribed a `GEO-16`-for-the-
birdcage chunk: split each port box at its mid-plane and rebuild the interface.
That prescription silently assumes the thing this module measures — that the
port box *touches conductor on two sides*, so a sheet spanning it would span
terminal to terminal.

On the two-torus fixture that holds by construction: the gap box replaces a
removed arc of the wire, so its two arc-end faces are conductor and facet group
``201``/``202`` (gap <-> wire) is exactly the terminal pair a lumped sheet
drives between. `birdcage_port_domain` places its boxes differently — at the
*midpoint angle* between adjacent legs and at
``port_radius = conductor_outer_radius + port_dy/2 + port_clearance``, with
``port_clearance > 0`` enforced by
:func:`MeshGenerator.birdcage_port_layout_diagnostics`.

So the question is measurable and worth measuring before a mesh chunk is
commissioned on the leg-(a) prescription: partition each port region's boundary
by what sits on the other side, and see how much of it is metal.

Mesh-only: no solve, no port claim, no S-parameter. Same graded rung leg (a)
priced (``conductor_resolution = 1.6e-3``, the `GEO-15`/`EX-21` sizing), so the
anchors are re-asserted on the object step 3 budgets from.
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
    _analytic_box_volume,
)

# Facet tags this module invents for the audit only — they exist for the length
# of the test and never reach the mesh generator. 300+i is port i against the
# conductor (the terminal interface, if any), 400+i against air, 500+i against
# the phantom.
CONDUCTOR_IFACE = 300
AIR_IFACE = 400
PHANTOM_IFACE = 500

# The phantom's closed-form lateral+end area, the positive control's anchor. The
# meshed surface is an inscribed polyhedron, so it must come in *below* the
# analytic value; 5% is loose enough for the coarse air sizing (15 mm) and tight
# enough that a wrong surface cannot hide.
PHANTOM_AREA_BAND = 0.05


def _analytic_phantom_area() -> float:
    return 2.0 * np.pi * PHANTOM_RADIUS**2 + 2.0 * np.pi * PHANTOM_RADIUS * PHANTOM_HEIGHT


def _analytic_port_box_area() -> float:
    dx, dy, dz = PORT_BOX_SIZE
    return 2.0 * (dx * dy + dy * dz + dz * dx)


def _global_facet_count(mesh, facet_tags, tag, comm) -> int:
    """Number of facets carrying ``tag``, counting each facet once.

    ``facet_tags.indices`` is rank-local *and* includes ghosts, so a plain
    ``np.count_nonzero`` double-counts every partition-boundary facet. Only
    indices below the facet index map's ``size_local`` are owned by this rank;
    those are summed.
    """
    fdim = mesh.topology.dim - 1
    n_owned = mesh.topology.index_map(fdim).size_local
    indices = np.asarray(facet_tags.indices)
    values = np.asarray(facet_tags.values)
    local = int(np.count_nonzero((values == tag) & (indices < n_owned)))
    return int(comm.allreduce(local, op=MPI.SUM))


def _interface_area_or_zero(mesh, facet_tags, tag, comm) -> float:
    """Area of facet group ``tag``, or exactly 0.0 when the group is empty.

    The empty case is short-circuited rather than assembled: a ``dS`` measure
    whose subdomain id appears nowhere in the mesh tags has no integration
    entities at all, and the point of the zero readings below is that the group
    is *absent*, which the facet count already says exactly.
    """
    if _global_facet_count(mesh, facet_tags, tag, comm) == 0:
        return 0.0
    return _facet_group_area(mesh, facet_tags, tag, comm)


def test_birdcage_port_boxes_touch_no_conductor():
    """Leg (b): partition each port box's boundary by the region behind it.

    1. **Anchors** — leg (a)'s, re-asserted: cell count within 1% of the step-3
       record, meshed/CAD conductor at or above the imported gate, `GEO-9`
       partition identities < 1e-9.
    2. **Positive control** — the same interface machinery, on the same mesh,
       measures the phantom's surface against its closed form. A zero reading
       from broken machinery would otherwise be indistinguishable from the
       finding.
    3. **Closure identity** — each port box's boundary areas against conductor,
       air and phantom must sum to the analytic box surface area. This is the
       quantitative assertion: it says the partition is exhaustive, so a zero
       conductor reading is an absence and not a miss.
    4. **The finding** — the conductor interface facet count per port.
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
        air_padding=AIR_PADDING,
        resolution=RESOLUTION,
        conductor_resolution=CONDUCTOR_RESOLUTION,
        comm=comm,
        return_diagnostics=True,
    )
    elapsed = time.perf_counter() - started

    port_tags = [100 + i for i in range(1, LEG_COUNT + 1)]
    all_tags = [1, 2, 3, *port_tags]
    assert global_cell_tag_set(mesh, cell_tags) == set(all_tags)

    n_cells = mesh.topology.index_map(3).size_global
    v = {tag: _tag_volume(mesh, cell_tags, tag, comm) for tag in all_tags}
    v_total = _total_volume(mesh, comm)
    cad_ratio = v[1] / diagnostics["cad_mass_by_group"]["conductor"]

    # One rebuild for every interface this audit needs, so `_interface_facet_tags`
    # runs its own uniqueness check across the whole set: no facet may be claimed
    # by two of these groups.
    interfaces = {}
    for i, tag in enumerate(port_tags, start=1):
        interfaces[CONDUCTOR_IFACE + i] = (tag, 1)
        interfaces[AIR_IFACE + i] = (tag, 2)
        interfaces[PHANTOM_IFACE + i] = (tag, 3)
    # The positive control rides in the same rebuild: phantom against air.
    interfaces[999] = (3, 2)
    audit_tags = _interface_facet_tags(mesh, cell_tags, interfaces)

    counts = {
        tag: _global_facet_count(mesh, audit_tags, tag, comm) for tag in interfaces
    }
    areas = {
        tag: _interface_area_or_zero(mesh, audit_tags, tag, comm) for tag in interfaces
    }

    box_area = _analytic_port_box_area()
    phantom_area_ratio = areas[999] / _analytic_phantom_area()

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step 3b] graded birdcage h_c={CONDUCTOR_RESOLUTION:.4e} m: "
            f"cells={n_cells} (record {STEP3_CELL_COUNT_RECORD}, "
            f"ratio {n_cells / STEP3_CELL_COUNT_RECORD:.6f})  "
            f"meshed/CAD conductor={cad_ratio:.6f}  rung={elapsed:.2f} s"
            f"\n[PORT-9 step 3b] positive control: phantom<->air "
            f"{counts[999]} facets, {areas[999]:.6e} m^2, "
            f"meshed/analytic={phantom_area_ratio:.6f}"
            f"\n[PORT-9 step 3b] analytic port box surface area "
            f"{box_area:.6e} m^2",
            flush=True,
        )
        for i in range(1, LEG_COUNT + 1):
            a_c = areas[CONDUCTOR_IFACE + i]
            a_a = areas[AIR_IFACE + i]
            a_p = areas[PHANTOM_IFACE + i]
            print(
                f"[PORT-9 step 3b] P{i}: conductor {counts[CONDUCTOR_IFACE + i]} facets "
                f"{a_c:.6e} m^2 ({a_c / box_area:.9f} of the box)  "
                f"air {counts[AIR_IFACE + i]} facets {a_a:.6e} m^2 "
                f"({a_a / box_area:.9f})  "
                f"phantom {counts[PHANTOM_IFACE + i]} facets {a_p:.6e} m^2  "
                f"closure {(a_c + a_a + a_p) / box_area:.12f}",
                flush=True,
            )

    # 1. Anchors — the object measured is the object step 3 budgets from.
    assert abs(n_cells / STEP3_CELL_COUNT_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"graded birdcage meshed {n_cells} cells vs the step-3 record "
        f"{STEP3_CELL_COUNT_RECORD}; outside 1% this is not that mesh"
    )
    assert cad_ratio >= CAD_MASS_GATE
    assert abs(v_total / _analytic_box_volume() - 1.0) < 1e-9
    assert abs(sum(v.values()) / v_total - 1.0) < 1e-9

    # 2. Positive control — the machinery finds an interface that does exist,
    #    and gets its area right against a closed form.
    assert counts[999] > 0, (
        "phantom<->air interface is empty; the audit machinery is not seeing "
        "interfaces at all and no zero below means anything"
    )
    assert 1.0 - PHANTOM_AREA_BAND <= phantom_area_ratio <= 1.0, (
        f"phantom surface measures {areas[999]:.6e} m^2, "
        f"{phantom_area_ratio:.6f} of the closed-form "
        f"{_analytic_phantom_area():.6e} m^2 — an inscribed triangulation must "
        f"land in [{1.0 - PHANTOM_AREA_BAND}, 1.0]"
    )

    # 3. Closure — the three regions exhaust each port box's boundary.
    for i in range(1, LEG_COUNT + 1):
        total = (
            areas[CONDUCTOR_IFACE + i]
            + areas[AIR_IFACE + i]
            + areas[PHANTOM_IFACE + i]
        )
        assert abs(total / box_area - 1.0) < 1e-9, (
            f"port P{i} boundary areas sum to {total:.9e} m^2 against the "
            f"analytic box surface {box_area:.9e} m^2 (ratio "
            f"{total / box_area:.12f}); the partition is not exhaustive, so a "
            "zero conductor reading would be a miss rather than an absence"
        )

    # 4. The finding. Written to fail loudly *if terminals ever appear*: the day
    #    the port boxes are moved onto conductor gaps, this test goes red and is
    #    deleted in the same commit that lands them.
    with_metal = {
        i: counts[CONDUCTOR_IFACE + i]
        for i in range(1, LEG_COUNT + 1)
        if counts[CONDUCTOR_IFACE + i] > 0
    }
    assert not with_metal, (
        f"port boxes {sorted(with_metal)} now touch conductor "
        f"({with_metal}) — the birdcage has terminals after all and the leg-(a) "
        "mid-plane prescription is executable; delete this test and run it"
    )
