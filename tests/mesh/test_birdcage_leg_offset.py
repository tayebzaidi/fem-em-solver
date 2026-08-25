"""`PORT-9` step 3 leg (d1), mesh side — one leg rotated off the C4 layout.

Leg (d) read the birdcage's 4x4 on the *undisplaced* mesh and found it
reciprocal, passive and circulant: the three class spreads came in at
0.0199 / 0.0180 / 0.0108% against a 5% band.  A symmetry gate that has only ever
seen a symmetric layout is a consistency check, not a validated gate, so leg
(d1) breaks the symmetry on purpose and asks the gate to notice.

The knob is `MeshGenerator.birdcage_port_domain`'s new
``leg_azimuth_offsets_rad``: one angle per leg, added to that leg's azimuth, so
leg *i* **and everything that belongs to it** — its two stubs, its gap, its
terminals, its port box and its sheet — rotates rigidly about the z axis while
the rings, the phantom and the other legs stay put.  Displacing the port *box*
off its leg, which the 2026-08-16 text literally proposed, would leave a sheet
in air facing no terminal: a degenerate port, not an asymmetric coil.

This module is the **mesh-side half** of leg (d1) and gates two things, neither
of which involves a solve:

* **the knob's identity control** — all-zero offsets reproduce the undisplaced
  fixture exactly (same global cell count, same cell-tag set, same per-port
  sheet area to 1e-12 relative).  The offsets are *added* to the nominal
  azimuths and adding an exact zero is exact, so the all-zero build runs the
  same arithmetic the undisplaced one does: this is an identity, not a
  small-angle limit;
* **the negative control of the control** — on the displaced mesh every
  `GEO-18` identity still holds: each sheet is a full rectangle of area
  ``dx·g`` to 1e-9, each port's two terminal disks reproduce the closed form
  inside `GEO-18` step 1's own band, each port box's two halves partition its
  volume, and each sheet is still planar in *its own* port frame.  The
  asymmetry is the only thing that moved.

The frame matters: at 22.5 deg a sheet is no longer x- or y-normal, so its
extents are measured by projecting node coordinates onto that port's own radial
and azimuthal directions rather than onto the global axes.  For an undisplaced
port the two readings coincide term by term.  The *generator* side of that was
already paid by `GEO-19` step B, which replaced the axis-aligned box/sheet
construction (and its ``NotImplementedError`` for any leg off a coordinate axis)
with the general local-frame one, so leg (d1) adds a layout knob here and no new
geometry kernel work.

Mesh-side only: no port model, no drive, no impedance.  The displaced 4x4 and
gate (iii)'s response to it are leg (d1)'s solve half.

Run (real build is enough)::

    scripts/testing/run_and_log.sh PORT-9-step3d1-mesh "docker compose exec -T \\
      fem-em-solver bash -lc 'cd /workspace && PYTHONPATH=/workspace/src \\
      timeout -k 30 400 mpiexec -n 2 python3 -m pytest \\
      tests/mesh/test_birdcage_leg_offset.py -v -s'"
"""

from __future__ import annotations

import time

import dolfinx
import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator, _interface_facet_tags
from tests.mesh.helpers import global_cell_tag_set
from tests.mesh.test_coil_phantom_conforming import _tag_volume
from tests.mesh.test_birdcage_port_sheet_prerequisite import CONDUCTOR_RESOLUTION
from tests.mesh.test_birdcage_port_terminals import (
    CONDUCTOR_IFACE,
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
    _analytic_terminal_area,
)
from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER, SHEET_IFACE

# A quarter of the inter-leg spacing: leg 1 moves to 22.5 deg, so its two
# azimuthal neighbours sit 67.5 and 112.5 deg away instead of 90 and 90.  Large
# enough that the adjacent mutuals cannot stay one class, small enough that the
# port boxes keep the layout helper's centre-separation floor with room (the
# nearest pair is 0.0778 m against a 0.0175 m requirement).
LEG_OFFSET_RAD = np.pi / (2.0 * LEG_COUNT)

# The identity control's band.  This is a *reproduction* band on a mesh that is
# supposed to be built by the same code path, not a physics tolerance: an exact
# zero offset leaves every azimuth bit-for-bit unchanged, so the only admissible
# difference is floating-point reassociation in the area reduction itself.
IDENTITY_BAND = 1.0e-12

# `GEO-18` step 2's own band on the sheet area, restated from that entry.
SHEET_AREA_BAND = 1.0e-9


def _build(offsets):
    """One graded, gapped, sheeted birdcage rung at the given leg offsets."""
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
        leg_azimuth_offsets_rad=offsets,
        emit_port_sheets=True,
        air_padding=AIR_PADDING,
        resolution=RESOLUTION,
        conductor_resolution=CONDUCTOR_RESOLUTION,
        comm=MPI.COMM_WORLD,
        return_diagnostics=True,
    )
    return mesh, cell_tags, facet_tags, diagnostics, time.perf_counter() - started


def _sheet_nodes(msh, facet_tags, tag):
    """Rank-local node coordinates of one sheet's facet set, ``(n, 3)``."""
    fdim = msh.topology.dim - 1
    facets = np.asarray(facet_tags.find(tag), dtype=np.int32)
    if not facets.size:
        return np.zeros((0, 3))
    nodes = dolfinx.cpp.mesh.entities_to_geometry(
        msh._cpp_object, fdim, facets, False
    )
    return msh.geometry.x[nodes.reshape(-1)]


def _projected_extents(msh, facet_tags, tag, comm, directions):
    """Global min/max spread of one sheet along each given unit direction.

    The global-axis bounding box `_sheet_extents` returns is only the port's own
    frame when the leg sits on a coordinate axis.  Projecting instead makes the
    reading frame-aware, and reduces to the bounding box term by term when the
    frame *is* the global one.  ``allreduce`` on arrays falls through to
    Python's ``min``, so gather and reduce elementwise (the `PORT-9` step 3c
    trap).
    """
    pts = _sheet_nodes(msh, facet_tags, tag)
    directions = np.asarray(directions, dtype=float)
    if pts.shape[0]:
        proj = pts @ directions.T
        lo, hi = proj.min(axis=0), proj.max(axis=0)
    else:
        lo = np.full(directions.shape[0], np.inf)
        hi = np.full(directions.shape[0], -np.inf)
    lo = np.min(np.array(comm.allgather(lo)), axis=0)
    hi = np.max(np.array(comm.allgather(hi)), axis=0)
    return hi - lo, 0.5 * (hi + lo)


def _sheet_azimuth_deg(msh, facet_tags, tag, comm):
    """Azimuth of a sheet's bounding-box centre [deg], reduced over ranks.

    The bbox centre and not the mean facet midpoint: the sheet is a full
    rectangle, so on an unstructured triangulation the two differ by ~4e-4
    relative, which is a property of the triangle-size distribution and of
    nothing physical (`PORT-9` step 3c, 2026-08-22).
    """
    pts = _sheet_nodes(msh, facet_tags, tag)
    if pts.shape[0]:
        lo, hi = pts.min(axis=0), pts.max(axis=0)
    else:
        lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    lo = np.min(np.array(comm.allgather(lo)), axis=0)
    hi = np.max(np.array(comm.allgather(hi)), axis=0)
    centre = 0.5 * (lo + hi)
    return float(np.degrees(np.arctan2(centre[1], centre[0])) % 360.0)


def _sheet_areas(msh, cell_tags, ports, comm):
    """Per-port reconstructed sheet area and the facet tags they came from."""
    tags_f = _interface_facet_tags(
        msh,
        cell_tags,
        {SHEET_IFACE + i: (PORT_LOWER + i, PORT_UPPER + i) for i in ports},
    )
    areas = {
        i: _interface_area_or_zero(msh, tags_f, SHEET_IFACE + i, comm) for i in ports
    }
    return tags_f, areas


def _terminal_areas(msh, cell_tags, ports, comm):
    """Per-port conductor-facing area, summed over both halves of the box."""
    interfaces = {}
    for i in ports:
        for j, tag in enumerate((PORT_LOWER + i, PORT_UPPER + i)):
            interfaces[(CONDUCTOR_IFACE + i) * 10 + j] = (tag, 1)
    audit = _interface_facet_tags(msh, cell_tags, interfaces)
    return {
        i: sum(
            _interface_area_or_zero(msh, audit, (CONDUCTOR_IFACE + i) * 10 + j, comm)
            for j in (0, 1)
        )
        for i in ports
    }


@pytest.fixture(scope="module")
def rungs():
    """Three meshes: undisplaced (no kwarg), all-zero offsets, leg 1 displaced."""
    comm = MPI.COMM_WORLD
    ports = list(range(1, LEG_COUNT + 1))
    offsets_displaced = np.zeros(LEG_COUNT)
    offsets_displaced[0] = LEG_OFFSET_RAD

    built = {}
    for name, offsets in (
        ("baseline", None),
        ("zero", np.zeros(LEG_COUNT)),
        ("displaced", offsets_displaced),
    ):
        msh, cells, _facets, diag, elapsed = _build(offsets)
        tdim = msh.topology.dim
        msh.topology.create_connectivity(tdim - 1, tdim)
        tags_f, areas = _sheet_areas(msh, cells, ports, comm)
        built[name] = {
            "mesh": msh,
            "cells": cells,
            "sheet_tags": tags_f,
            "sheet_area": areas,
            "n_cells": int(msh.topology.index_map(tdim).size_global),
            "tag_set": global_cell_tag_set(msh, cells),
            "azimuth_deg": {
                i: _sheet_azimuth_deg(msh, tags_f, SHEET_IFACE + i, comm)
                for i in ports
            },
            "diag": diag,
            "elapsed": elapsed,
        }

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step3d1-mesh] offset = {LEG_OFFSET_RAD:.9f} rad = "
            f"{np.degrees(LEG_OFFSET_RAD):.4f} deg on leg 1 only",
            flush=True,
        )
        for name, r in built.items():
            print(
                f"    {name:10s} cells={r['n_cells']:7d}  "
                f"mesh={r['diag']['mesh_wall_time_s']:.2f} s  "
                f"rung={r['elapsed']:.2f} s  azimuths="
                + " ".join(f"{r['azimuth_deg'][i]:8.4f}" for i in ports)
                + "  sheet areas="
                + " ".join(f"{r['sheet_area'][i]:.9e}" for i in ports),
                flush=True,
            )
    return built


def test_zero_offsets_reproduce_the_undisplaced_fixture(rungs):
    """**The knob's identity control.**  All-zero offsets change nothing.

    The offsets are added to the nominal azimuths, and adding an exact zero is
    exact, so the all-zero build is not a zero-angle rotation of the fixture but
    the same construction leg (d) meshed.  Anything but exact agreement in the cell count
    and the tag set — and 1e-12 in the sheet areas, floating-point reassociation
    being the only admissible difference — means the knob perturbs the layout it
    is supposed to leave alone, and every displaced reading built on it would be
    measuring the knob rather than the asymmetry.
    """
    base, zero = rungs["baseline"], rungs["zero"]
    assert zero["n_cells"] == base["n_cells"], (
        f"all-zero offsets meshed {zero['n_cells']} cells against the "
        f"undisplaced {base['n_cells']} — the knob is not inert at zero"
    )
    assert zero["tag_set"] == base["tag_set"], (
        f"all-zero offsets carry cell tags {sorted(zero['tag_set'])} against "
        f"the undisplaced {sorted(base['tag_set'])}"
    )
    for i in sorted(base["sheet_area"]):
        a0, a1 = base["sheet_area"][i], zero["sheet_area"][i]
        err = abs(a1 - a0) / a0
        assert err < IDENTITY_BAND, (
            f"port P{i}: all-zero-offset sheet area {a1:.12e} m^2 deviates "
            f"{err:.3e} from the undisplaced {a0:.12e} m^2"
        )


def test_the_displaced_leg_moved_and_nothing_else_did(rungs):
    """Leg 1 sits at 22.5 deg; legs 2-4 sit where they always did.

    Read off the sheets' own bounding-box centres, so it is the *port* that is
    asserted to have travelled with its leg — a rotated leg under an unmoved box
    is exactly the degenerate case leg (d1) exists to avoid.
    """
    base, disp = rungs["baseline"], rungs["displaced"]
    expected = np.degrees(LEG_OFFSET_RAD)

    assert abs(disp["azimuth_deg"][1] - expected) < 1.0e-6, (
        f"port P1's sheet sits at {disp['azimuth_deg'][1]:.9f} deg against the "
        f"requested {expected:.9f} deg"
    )
    for i in sorted(base["azimuth_deg"]):
        if i == 1:
            continue
        assert abs(disp["azimuth_deg"][i] - base["azimuth_deg"][i]) < 1.0e-6, (
            f"port P{i} moved to {disp['azimuth_deg'][i]:.9f} deg from "
            f"{base['azimuth_deg'][i]:.9f} deg, but only leg 1 was displaced"
        )


def test_the_displaced_mesh_keeps_every_geo18_identity(rungs):
    """**The negative control of the control.**  The mesh is still conforming.

    Every port on the displaced mesh must still be the clean construction
    `GEO-18` gated: a full-rectangle sheet of closed-form area ``dx·g``, two
    planar terminal disks of closed-form area, and two box halves that partition
    the box.  If any of these moved, a class spread measured on this mesh would
    be reporting a broken port rather than a broken symmetry.
    """
    comm = MPI.COMM_WORLD
    disp = rungs["displaced"]
    ports = sorted(disp["sheet_area"])
    dx, _dy, dz = disp["diag"]["port_box_size_m"]
    sheet_analytic = dx * dz
    box_volume = float(np.prod(disp["diag"]["port_box_size_m"]))
    terminal_analytic = _analytic_terminal_area()
    terminals = _terminal_areas(disp["mesh"], disp["cells"], ports, comm)
    halves = {
        i: (
            _tag_volume(disp["mesh"], disp["cells"], PORT_LOWER + i, comm),
            _tag_volume(disp["mesh"], disp["cells"], PORT_UPPER + i, comm),
        )
        for i in ports
    }

    frames = {}
    for i in ports:
        beta = np.radians(disp["azimuth_deg"][i])
        radial = np.array([np.cos(beta), np.sin(beta), 0.0])
        azimuthal = np.array([-np.sin(beta), np.cos(beta), 0.0])
        axial = np.array([0.0, 0.0, 1.0])
        spans, _centre = _projected_extents(
            disp["mesh"],
            disp["sheet_tags"],
            SHEET_IFACE + i,
            comm,
            [radial, azimuthal, axial],
        )
        frames[i] = spans

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step3d1-mesh] displaced mesh, analytic sheet dx*g="
            f"{sheet_analytic:.9e} m^2, terminals (2 disks)="
            f"{terminal_analytic:.9e} m^2, box={box_volume:.9e} m^3:",
            flush=True,
        )
        for i in ports:
            w, out_of_plane, h = frames[i]
            print(
                f"    P{i}: sheet {disp['sheet_area'][i]:.9e} m^2  "
                f"meshed/analytic={disp['sheet_area'][i] / sheet_analytic:.12f}  "
                f"frame w={w:.9e} h={h:.9e} out-of-plane={out_of_plane:.3e} m  "
                f"terminals {terminals[i]:.9e} m^2 "
                f"ratio={terminals[i] / terminal_analytic:.9f}  "
                f"halves {halves[i][0] / box_volume:.12f}/"
                f"{halves[i][1] / box_volume:.12f} "
                f"sum={sum(halves[i]) / box_volume:.12f}",
                flush=True,
            )

    for i in ports:
        ratio = disp["sheet_area"][i] / sheet_analytic
        assert abs(ratio - 1.0) < SHEET_AREA_BAND, (
            f"port P{i}: the displaced mesh's sheet reads {ratio:.12f} of the "
            f"closed-form dx*g against the {SHEET_AREA_BAND:.0e} band — the "
            "rotated port box's mid-plane is not a full rectangle"
        )
        t_ratio = terminals[i] / terminal_analytic
        # `GEO-18` step 1's band is an *interval*, [0.95, 1.0]: an inscribed
        # triangulation of a disk always under-reads its area, so the closed
        # form is a ceiling and not a centre.  Imported and used as written.
        low, high = TERMINAL_AREA_BAND
        assert low <= t_ratio <= high, (
            f"port P{i}: terminal area {terminals[i]:.9e} m^2 is {t_ratio:.9f} "
            f"of the closed form, outside `GEO-18` step 1's [{low}, {high}]"
        )
        partition = sum(halves[i]) / box_volume
        assert abs(partition - 1.0) < 1.0e-9, (
            f"port P{i}: its two halves hold {partition:.12f} of the box volume "
            "— the sheet did not split the rotated box cleanly"
        )
        w, out_of_plane, h = frames[i]
        assert out_of_plane < 1.0e-12, (
            f"port P{i}: the sheet spreads {out_of_plane:.3e} m along its own "
            "azimuthal direction — the rotated facet set is not a plane"
        )
        assert abs(h / dz - 1.0) < SHEET_AREA_BAND, (
            f"port P{i}: the sheet spans {h:.9e} m along the leg against the "
            f"gap {dz:.9e} m"
        )
        assert abs(w / dx - 1.0) < SHEET_AREA_BAND, (
            f"port P{i}: the sheet spans {w:.9e} m radially against the box's "
            f"{dx:.9e} m"
        )


def test_offsets_without_a_gap_are_rejected():
    """A leg cannot carry a port that is not on it.

    Without `leg_gap_length` the port boxes float at the *midpoint* azimuths
    between legs, so rotating a leg would move metal out from under an unmoved
    box.  The call is refused rather than silently doing that.
    """
    with pytest.raises(ValueError, match="leg_gap_length"):
        MeshGenerator.birdcage_port_domain(
            leg_count=LEG_COUNT,
            ring_radius=RING_RADIUS,
            leg_width=LEG_WIDTH,
            leg_spacing=LEG_SPACING,
            coil_length=COIL_LENGTH,
            leg_azimuth_offsets_rad=np.zeros(LEG_COUNT),
            comm=MPI.COMM_SELF,
        )


def test_offsets_with_ring_gaps_are_rejected():
    """`GEO-20`'s ring gaps are centred on the *uniform* mid-azimuths.

    A displaced leg no longer bisects the arc between its neighbours, so a
    combined build would leave every ring gap centred on nothing in particular.
    Refused rather than silently produced.
    """
    with pytest.raises(ValueError, match="ring_gap_length"):
        MeshGenerator.birdcage_port_domain(
            leg_count=LEG_COUNT,
            ring_radius=RING_RADIUS,
            leg_width=LEG_WIDTH,
            leg_spacing=LEG_SPACING,
            coil_length=COIL_LENGTH,
            leg_gap_length=LEG_GAP_LENGTH,
            ring_gap_length=LEG_GAP_LENGTH,
            leg_azimuth_offsets_rad=np.zeros(LEG_COUNT),
            comm=MPI.COMM_SELF,
        )


def test_offsets_must_carry_one_angle_per_leg():
    """A wrong-length offset vector is a rejected call, not a broadcast."""
    with pytest.raises(ValueError, match="one angle per leg"):
        MeshGenerator.birdcage_port_domain(
            leg_count=LEG_COUNT,
            ring_radius=RING_RADIUS,
            leg_width=LEG_WIDTH,
            leg_spacing=LEG_SPACING,
            coil_length=COIL_LENGTH,
            leg_gap_length=LEG_GAP_LENGTH,
            leg_azimuth_offsets_rad=np.zeros(LEG_COUNT + 1),
            comm=MPI.COMM_SELF,
        )
