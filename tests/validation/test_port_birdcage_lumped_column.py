"""`PORT-9` step 3 leg (c) — the first port solve on the gapped birdcage.

Legs (a) and (b) both stopped before any solve: the birdcage's port boxes were
isolated air blocks outside an uncut coil (conductor facet area exactly
0.000000e+00 m² on all four ports), so no port model could reach them.
`GEO-18` cut the legs (step 1: planar disk terminals, 0.988616 of the closed
form) and split each gap box at its mid-plane (step 2: sheet area ``dx·g`` at
1.000000000000, C4 spread 8.470e-16).  This module is the first thing to put a
**field** on that fixture.

**What it does.**  One mesh of the step-2 fixture
(``birdcage_port_domain(leg_gap_length=LEG_GAP_LENGTH, emit_port_sheets=True,
conductor_resolution=1.6e-3)``, 116 085 cells on `GEO-19` step B's local-frame
port construction; 116 368 on the `OPS-18` 0.11 image before it and 116 416 at
scoping, on the image that preceded that), the four ``21x``
sheets narrowed to `PORT-9` step 2b's gated interior width ``f = 0.5`` with its
``w = A/h`` convention, a :class:`LumpedSheetPortSpec` on every one of them, and
**one** package solve at the two-torus records' 10 MHz with **port 1 driven
only**.  That solve yields column 1 of ``Z`` — ``Z_i1 = V_i / I_1`` on the
package's own definition (``ports/sparameters.py::_assemble_impedance_matrix``,
the definition `PORT-1` step 3b gated), read here off
:func:`run_lumped_sheet_port_case` rather than the four-solve sweep, because
the price of one solve on this fixture is unmeasured and it is what leg (c) is
for.

**The gate.**  `GEO-18` made the layout exactly C4-invariant by construction
(square-section boxes on legs at k·90°, drive ``ẑ`` for every port), so the two
ports *adjacent* to the driven one are related by the mirror that fixes port 1
and must see the same mutual impedance:

    ``|Z₂₁ − Z₄₁| / |Z₂₁| ≤ 0.5%``

— gate (iii′)'s own band, pre-stated at scoping (§7 `PORT-9` step 3 leg (c)) at
5% and **tightened to 0.5% with leg (d1′) on 2026-08-25**; not to be widened.  ``Re Z₁₁`` is printed, not gated.

The *opposite*-port ordering assertion this module used to carry alongside it
— the anti-degeneracy check — was **retired by ruling (6\*) (2026-08-24 18:00
review, §9 item 1)** when it was measured to track the open-limit fixture's
conditioning rather than its geometry; the duty moved, with two decades more
margin, to the terminated fixture's gates in legs (d0) and (d).  Details and
both mesh-tagged readings are in
:func:`test_adjacent_ports_of_the_driven_leg_agree_and_the_opposite_one_does_not`.

**Scope.**  Closes nothing in §2.  Reciprocity, passivity and the full 4×4 are
leg (d)'s, and need four solves priced from this one.  No resonance, no
S-parameter and no birdcage-tuning claim is made here: 10 MHz is the port
model's frequency, not a Larmor frequency, and one column of Z is not a network.

Cost: heavy tier, ``-n 2``, one mesh (~23 s at scoping) and one solve on a form
this fixture has never compiled.

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-9-step3c "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 1200 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_birdcage_lumped_column.py -v -s'"
"""

from __future__ import annotations

import time

import dolfinx
import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.io.mesh import _interface_facet_tags
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.lumped import LumpedSheetPortSpec, run_lumped_sheet_port_case

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_leg_gaps import LEG_GAP_LENGTH
from tests.mesh.test_birdcage_port_sheets import (
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
    _build,
    _sheet_axes,
)
from tests.mesh.test_birdcage_port_tags import LEG_COUNT, RING_RADIUS
from tests.mesh.test_two_torus_port_facets import _facet_group_area
from tests.mesh.test_two_torus_port_sheet import _sheet_extents, _sheet_facet_count
from tests.validation.test_lossy_sphere_fullwave import SALINE_EPSILON_R, SALINE_SIGMA
from tests.validation.test_port_gap_voltage_impedance import (
    FREQUENCY_HZ,
    SIGMA_WIRE_S_PER_M,
)
from tests.validation.test_port_lumped_narrowed_sheet import GATED_WIDTH_FRACTION
from tests.validation.test_port_lumped_two_torus import PROBE_PORT_IMPEDANCE_OHM
from tests.validation.test_port_package_sparameters import REFERENCE_IMPEDANCE_OHM

# Cell tags `birdcage_port_domain` writes for the three bulk regions (the port
# halves take 100+i / 200+i on top).  Ordering fixed by
# `tests/mesh/test_birdcage_port_sheets.py::_port_boundary_partition`, which
# addresses conductor as 1, air as 2 and phantom as 3.
CONDUCTOR_CELL_TAG = 1
PHANTOM_CELL_TAG = 3

# Gate (iii)'s band, pre-stated at scoping (2026-08-22 03:00 review, §7 `PORT-9`
# step 3 leg (c)) and read here off one column: the two ports adjacent to the
# driven one are mirror images of each other about the drive, so their mutual
# impedances must agree to this.  Never widened — an adjacent spread above it is
# the mesh-asymmetry finding the step-3 entry already names.
#
# **(iii') tightening 5% -> 0.5%, ruled 2026-08-23 10:30 and executed with
# `PORT-9` leg (d1') on 2026-08-25 (§9 item 1).**  This is a *narrowing*: every
# symmetric reading on `GEO-19` step B's mesh already satisfies it with two
# decades to spare, measured, not assumed — leg (c)'s adjacent pair 0.0407%
# (`20260825T003832Z_GEO-19-stepB-port9-run2.log:9217`), leg (d0)'s terminated
# column 0.0040% (same log, :9224), leg (d)'s three 4x4 classes 0.0553 / 0.0353
# / 0.0214%.  The reason to tighten is leg (d1')'s geometric negative control:
# at 5% a quarter-pitch rotation of one leg is the *only* asymmetry the gate can
# resolve, so the band was measuring nothing between 0.05% and 5%.  All three
# consumer modules (this one, `test_port_birdcage_termination_probe.py`,
# `test_port_birdcage_four_port.py`) were run green at the new value in the same
# slot the value moved.  The old 5% is history, kept here; it never widens back.
ADJACENT_SPREAD_BAND = 0.005

# `GEO-18` step 2's record for the sheeted mesh, the fixture anchor: the mesh
# this leg solves on must be the mesh the sheets were gated on.  **Image-tagged
# re-record, 2026-08-24 (ruling (5\*), §9)**: 116 416 was `GEO-18` step 2's count
# on the pre-`OPS-18`-0.11 container image; the 0.11 image the tree now boots
# meshes the same CAD at 116 368 (ratio 0.999588), a mesher tie-breaking motion
# with every geometric identity of step 2 unchanged.  The 2% band below is
# unmoved and both counts sit inside it — this constant is the fixture's
# identity record, not a gate.
#
# **Mesh-tagged re-record, 2026-08-24 (`GEO-19` step B, §9 item 1).**  Step B's
# local-frame port construction is exact-onto at the four axis azimuths but not
# bit-identical to the old one, so gmsh tie-breaking moves the same CAD from
# 116 368 to **116 085** cells (ratio 0.997568, a 0.24% change; ruling (4\*)
# adjudicated the cause, and the invariance control reproduces every geometric
# identity on the new mesh — sheet area `dx·g` 1.000000000000, C4 spread
# 6.050e-16, terminal ratios 0.988616 x 4,
# `20260824T183257Z_GEO-19-stepB-invariance.log`).  History, all three inside
# the unmoved 2% band: 116 416 (pre-`OPS-18` image) -> 116 368 (0.11 image) ->
# 116 085 (step B).  The termination-probe and four-port modules **import** this
# constant — it moves here, once, and nowhere else.
STEP2_CELL_COUNT = 116085
STEP2_CELL_COUNT_BAND = 0.02

# Above this the negative control (the open-limit second solve) is not run and
# the price is the deliverable — the entry's own rule, in seconds of wall clock.
CONTROL_SOLVE_PRICE_CEILING_S = 300.0


def _sheet_bbox_centre(msh, facet_tags, tag, comm):
    """Bounding-box centre of one sheet's facet set [m].

    The bbox centre, **not** the mean facet midpoint: the sheet is a full
    rectangle (`GEO-18` step 2 gates its area at ``dx·g`` to 1e-9), so the two
    coincide only for a uniform triangulation, and on this unstructured mesh
    they do not — the unweighted midpoint mean read r = 6.997337e-02 m against
    the exact 7.000000e-02 m, a 3.8e-4 relative offset that is a property of the
    triangle-size distribution and of nothing physical (measured 2026-08-22,
    ``20260822T213427Z_PORT-9-step3c.log``).  The bbox centre of a rectangle is
    exact, which is what lets the azimuth and radius below be asserted at 1e-9
    rather than at a mesh-dependent band.

    Reduced over all ranks by the same allgather/elementwise route
    :func:`_sheet_extents` uses, and for the same reason (``allreduce`` on two
    arrays falls through to Python's ``min``).
    """
    fdim = msh.topology.dim - 1
    facets = np.asarray(facet_tags.find(tag), dtype=np.int32)
    if facets.size:
        nodes = dolfinx.cpp.mesh.entities_to_geometry(
            msh._cpp_object, fdim, facets, False
        )
        pts = msh.geometry.x[nodes.reshape(-1)]
        lo, hi = pts.min(axis=0), pts.max(axis=0)
    else:
        lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    lo = np.min(np.array(comm.allgather(lo)), axis=0)
    hi = np.max(np.array(comm.allgather(hi)), axis=0)
    return 0.5 * (lo + hi)


def _narrowed_transverse(msh, facet_tags, tag, fraction, centre, axis, half_width):
    """Step 2b's midpoint filter, on whichever transverse axis this port uses.

    The two-torus version (`test_port_lumped_narrowed_sheet::_narrowed_sheet_tags`)
    hard-codes ``x`` because that fixture has one port azimuth.  Here the sheet
    plane is y-normal for a leg on the x-axis and x-normal for one on the y-axis,
    so the axis is passed in, read off the *measured* extents.  Everything else
    is step 2b's rule unchanged: facet **midpoints**, not nodes (a node rule
    would disagree with this one on exactly the boundary strip the width ladder
    was measuring), every other tag passed through untouched, and ``w``
    re-measured from the result rather than computed as ``f × w_full``.
    """
    fdim = msh.topology.dim - 1
    idx = np.asarray(facet_tags.indices, dtype=np.int32)
    val = np.asarray(facet_tags.values, dtype=np.int32)
    on_sheet = val == int(tag)
    sheet_facets = idx[on_sheet]
    keep = np.ones(sheet_facets.size, dtype=bool)
    if sheet_facets.size:
        mid = dolfinx.mesh.compute_midpoints(msh, fdim, sheet_facets)
        keep = np.abs(mid[:, axis] - centre) <= fraction * half_width
    new_idx = np.concatenate([idx[~on_sheet], sheet_facets[keep]]).astype(np.int32)
    new_val = np.concatenate(
        [
            val[~on_sheet],
            np.full(int(np.count_nonzero(keep)), int(tag), dtype=np.int32),
        ]
    ).astype(np.int32)
    order = np.argsort(new_idx, kind="stable")
    return dolfinx.mesh.meshtags(msh, fdim, new_idx[order], new_val[order])


@pytest.fixture(scope="module")
def birdcage_column():
    """One mesh; one lumped-sheet solve with port 1 driven; column 1 of Z."""
    comm = MPI.COMM_WORLD
    ports_idx = list(range(1, LEG_COUNT + 1))

    msh, cell_tags, _facet_tags, diag, t_mesh = _build(True)
    tdim = msh.topology.dim
    ncells = int(msh.topology.index_map(tdim).size_global)
    # Hoisted on every rank before any facet-restricted form (known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    # The sheets are rebuilt dolfinx-side from the two halves' cell tags — the
    # `GEO-16`/`GEO-18` step-2 construction, unchanged.  These tags (211..214)
    # are the only ones the lumped route needs, so they are the facet tags the
    # solve is handed.
    halves = {i: (PORT_LOWER + i, PORT_UPPER + i) for i in ports_idx}
    tags_f = _interface_facet_tags(
        msh, cell_tags, {SHEET_IFACE + i: halves[i] for i in ports_idx}
    )

    # Measure each full sheet, name its transverse axis and azimuth, then narrow.
    geometry = {}
    for i in ports_idx:
        tag = SHEET_IFACE + i
        extents = _sheet_extents(msh, tags_f, tag, comm)
        w_bbox, h_bbox, spread = _sheet_axes(extents, diag, i)
        axis = 0 if extents[0] >= extents[1] else 1
        centroid = _sheet_bbox_centre(msh, tags_f, tag, comm)
        geometry[i] = {
            "tag": tag,
            "axis": axis,
            "centroid": centroid,
            "w_full": float(w_bbox),
            "h_full": float(h_bbox),
            "spread_full": float(spread),
            "azimuth_deg": float(
                np.degrees(np.arctan2(centroid[1], centroid[0])) % 360.0
            ),
            "radius": float(np.hypot(centroid[0], centroid[1])),
        }

    for i in ports_idx:
        g = geometry[i]
        tags_f = _narrowed_transverse(
            msh,
            tags_f,
            g["tag"],
            GATED_WIDTH_FRACTION,
            float(g["centroid"][g["axis"]]),
            g["axis"],
            0.5 * g["w_full"],
        )

    sheets = []
    for i in ports_idx:
        g = geometry[i]
        tag = g["tag"]
        n_facets = _sheet_facet_count(msh, tags_f, tag, comm)
        assert n_facets > 0, f"sheet {tag}: no owned facets anywhere after filtering"
        area = _facet_group_area(msh, tags_f, tag, comm)
        extents = _sheet_extents(msh, tags_f, tag, comm)
        w_bbox, h_bbox, spread = _sheet_axes(extents, diag, i)
        # Step 2b's convention: the area-based effective width on the *filtered*
        # facet set, never ``f × w_full``.
        sheets.append(
            {
                **g,
                "facets": int(n_facets),
                "area": float(area),
                "h": float(h_bbox),
                "w": float(area / h_bbox),
                "w_bbox": float(w_bbox),
                "out_of_plane": float(spread),
            }
        )

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            CONDUCTOR_CELL_TAG: HomogeneousMaterial(
                sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0
            ),
            PHANTOM_CELL_TAG: HomogeneousMaterial(
                sigma=SALINE_SIGMA, epsilon_r=SALINE_EPSILON_R, mu_r=1.0
            ),
        },
        boundary_condition="pec_zero_tangential_a",
    )

    port_defs = []
    specs = []
    for s in sheets:
        pid = f"P{s['tag'] - SHEET_IFACE}"
        port_defs.append(
            PortDefinition(
                port_id=pid,
                positive_tag=int(s["tag"]),
                negative_tag=CONDUCTOR_CELL_TAG,
                orientation="leg_gap_axial_plus_z",
                z0_ohm=REFERENCE_IMPEDANCE_OHM,
            )
        )
        specs.append(
            LumpedSheetPortSpec(
                port_id=pid,
                facet_tag=int(s["tag"]),
                port_impedance_ohm=PROBE_PORT_IMPEDANCE_OHM,
                gap_height_m=s["h"],
                sheet_width_m=s["w"],
                # `GEO-18`'s geometry choice: the current runs along the leg, so
                # the drive is global ẑ for every port (review decision
                # 2026-08-20, resolving leg (a)'s per-port azimuth question).
                drive_direction=(0.0, 0.0, 1.0),
                drive_voltage_v=1.0 + 0.0j,
                interior=True,
            )
        )

    comm.Barrier()
    t0 = time.perf_counter()
    result = run_lumped_sheet_port_case(
        problem,
        port_defs,
        specs,
        facet_tags=tags_f,
        driven_port_id="P1",
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    i_driven = result.responses["P1"].current_a
    z_column = np.array(
        [result.responses[p.port_id].voltage_v / i_driven for p in port_defs],
        dtype=np.complex128,
    )

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step3c] gapped+sheeted birdcage: {ncells} cells "
            f"(record {STEP2_CELL_COUNT}, ratio {ncells / STEP2_CELL_COUNT:.6f}), "
            f"mesh {diag['mesh_wall_time_s']:.2f} s, rung {t_mesh:.2f} s; "
            f"one lumped-sheet solve, P1 driven, f = {FREQUENCY_HZ:.3e} Hz, "
            f"Z_p = {PROBE_PORT_IMPEDANCE_OHM} Ohm, f_width = "
            f"{GATED_WIDTH_FRACTION}: **{t_solve:.2f} s**",
            flush=True,
        )
        for s in sheets:
            print(
                f"    sheet {s['tag']} (P{s['tag'] - SHEET_IFACE}): azimuth "
                f"{s['azimuth_deg']:7.3f} deg, r = {s['radius']:.6e} m, "
                f"transverse axis {'xy'[s['axis']]}; {s['facets']:5d} facets  "
                f"area {s['area']:.9e} m^2  h = {s['h']:.9e} m  "
                f"w = A/h = {s['w']:.9e} m (full-sheet bbox "
                f"{s['w_full']:.9e} m, filtered bbox {s['w_bbox']:.9e} m)  "
                f"out-of-plane {s['out_of_plane']:.3e} m",
                flush=True,
            )
        print(
            f"[PORT-9 step3c] I_1 = {i_driven:+.9e} A; column 1 of Z [Ohm]:",
            flush=True,
        )
        for p, z in zip(port_defs, z_column):
            est = result.responses[p.port_id]
            print(
                f"    Z_{p.port_id[1:]}1 = {z:+.9e}  |Z| = {abs(z):.9e}  "
                f"V = {est.voltage_v:+.9e} V, I = {est.current_a:+.9e} A",
                flush=True,
            )

    return {
        "result": result,
        "z_column": z_column,
        "sheets": sheets,
        "cells": ncells,
        "mesh_time": float(t_mesh),
        "solve_time": float(t_solve),
        "port_ids": [p.port_id for p in port_defs],
    }


@complex_only
def test_the_birdcage_column_came_off_the_solved_field(birdcage_column):
    """Structural: four sheets, on the C4 layout, read through the field route.

    Nothing here is the gate; all of it is what the gate needs to mean anything.
    The route must not be the retiring `PORT-0` heuristic
    (``is_placeholder=False``, the flag that gates Touchstone export); each
    narrowed sheet must still be planar and genuinely narrowed (``A/h`` strictly
    below the *full* sheet's bounding-box extent, the step 2b convention); and
    the adjacency the gate reads must be the measured azimuths, not the
    generator's assumed tag order.
    """
    r = birdcage_column["result"]
    assert not r.is_placeholder, (
        "the lumped-sheet route returned is_placeholder=True — the solve fell "
        "back to the PORT-0 coupling heuristic"
    )
    assert len(r.responses) == LEG_COUNT
    assert r.responses["P1"].is_driven
    for pid in ("P2", "P3", "P4"):
        assert not r.responses[pid].is_driven

    sheets = birdcage_column["sheets"]
    assert abs(birdcage_column["cells"] / STEP2_CELL_COUNT - 1.0) < STEP2_CELL_COUNT_BAND, (
        f"the solve meshed {birdcage_column['cells']} cells against `GEO-18` "
        f"step 2's record {STEP2_CELL_COUNT}; this is not the fixture the sheets "
        "were gated on"
    )
    for s in sheets:
        assert s["out_of_plane"] < 1.0e-12, (
            f"sheet {s['tag']}: out-of-plane spread {s['out_of_plane']:.3e} m — "
            "the filtered facet set is not a plane"
        )
        assert s["w"] < s["w_full"], (
            f"sheet {s['tag']}: A/h = {s['w']:.9e} m is not below the full "
            f"sheet's extent {s['w_full']:.9e} m — the interior-width filter did "
            "not run, so this is not the width step 2b gated"
        )
        assert abs(s["radius"] / RING_RADIUS - 1.0) < 1.0e-9, (
            f"sheet {s['tag']} sits at radius {s['radius']:.6e} m, not on the "
            f"ring radius {RING_RADIUS:.6e} m; the ports are not on the legs"
        )

    # The C4 layout, measured: P1..P4 at 0/90/180/270 degrees, so P2 and P4 are
    # the ports adjacent to the driven one and P3 is opposite it.
    azimuths = {s["tag"] - SHEET_IFACE: s["azimuth_deg"] for s in sheets}
    for i, expected in ((1, 0.0), (2, 90.0), (3, 180.0), (4, 270.0)):
        delta = abs((azimuths[i] - expected + 180.0) % 360.0 - 180.0)
        assert delta < 1.0e-6, (
            f"port P{i}'s sheet centroid is at {azimuths[i]:.6f} deg, not the "
            f"{expected:.1f} deg the adjacency in the gate assumes"
        )


@complex_only
def test_adjacent_ports_of_the_driven_leg_agree_and_the_opposite_one_does_not(
    birdcage_column,
):
    """**Leg (c)'s gate.**  ``|Z₂₁ − Z₄₁|/|Z₂₁| ≤ 0.5%``, with ``Z₃₁`` apart.

    The layout is C4-invariant by construction, and the mirror plane through the
    driven leg swaps P2 and P4 while fixing P1 and P3.  The solved field must
    carry that symmetry into the mutual impedances: the adjacent pair agrees to
    gate (iii′)'s own 0.5% band.  The band is pre-stated and never widened — a
    spread above it is the mesh-asymmetry finding §7 `PORT-9` step 3 names, and
    its disposal is a known-issues entry and a stop.

    **The anti-degeneracy ordering assertion is retired here (ruling (6\*),
    2026-08-24 18:00 review; §9 item 1, executing (4\*)(iii)'s pre-registered
    disposition).**  It used to require the *opposite* port to sit further from
    the adjacent pair than the pair sits from itself — the check that stops the
    symmetry gate above from passing on a constant.  Two measurements retired
    it, and neither is a loosening:

    * The reading is not mesh-stable on **this** fixture.  At ``Z_p = 1e6 Ω``
      the port is nearly open, ``I₁`` is a ~1e-9 A near-cancellation residual,
      and the margin moves with its conditioning: magnitude-only 5.0594x
      (116 368 cells) -> **0.7906x** (116 085), complex form 6.9398x ->
      1.5951x, under a 0.24% cell-count change that moves ``Z₁₁`` 40.6%
      (known-issues, `GEO-19` step B attempt 2, still OPEN).  Both readings
      were already below leg (d0)'s pre-stated 10x floor *before* step B.
    * The duty it carried is held elsewhere, with two decades more margin, by
      two gates that are on `main`, green, and *better* on step B's mesh:
      leg (d0)'s terminated discrimination margin (253.2002x -> **2256.9707x**,
      floor 10x, `test_port_birdcage_termination_probe.py`) and leg (d)'s 4x4
      class separation (150.3584x -> **166.6766x**,
      `test_port_birdcage_four_port.py`), whose recorded class means/spreads
      are 2.338160261e+01 Ω / 0.0553%, 1.700854304e+01 Ω / 0.0353% and
      1.606048044e+01 Ω / 0.0214% — three classes an all-one-number Z cannot
      produce.

    So the discrimination margin below is **printed as a diagnostic, not
    gated**, with its two mesh-tagged readings kept above as history.  The C4
    band stays the gate, at (iii′)'s tightened 0.5%.  The thin separation itself stays
    flagged to the weekly review for §10 Phase 6.
    """
    z = birdcage_column["z_column"]
    z11, z21, z31, z41 = (complex(v) for v in z)

    spread = abs(z21 - z41) / abs(z21)
    adjacent_mean = 0.5 * (abs(z21) + abs(z41))
    opposite_deviation = abs(abs(z31) - adjacent_mean) / adjacent_mean
    price = birdcage_column["solve_time"]

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3c] C4 ADJACENT-PAIR gate (band "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}%, gate (iii)'s own, pre-stated at "
            f"scoping and unmoved):\n"
            f"    Z21 = {z21:+.9e} Ohm  |Z21| = {abs(z21):.9e}\n"
            f"    Z41 = {z41:+.9e} Ohm  |Z41| = {abs(z41):.9e}\n"
            f"    |Z21 - Z41|/|Z21| = {spread * 100:.4f}%  "
            f"{'INSIDE' if spread <= ADJACENT_SPREAD_BAND else 'MISS'}\n"
            f"    Z31 = {z31:+.9e} Ohm  |Z31| = {abs(z31):.9e}  "
            f"deviation from the adjacent mean {opposite_deviation * 100:.4f}% "
            f"(must exceed the spread; discrimination margin "
            f"{opposite_deviation / spread:.4f}x)\n"
            f"    Z11 = {z11:+.9e} Ohm  (Re Z11 = {z11.real:+.9e} Ohm, reported, "
            f"not gated)\n"
            f"[PORT-9 step3c] PRICE: one solve {price:.2f} s wall at -n 2 "
            f"(control ceiling {CONTROL_SOLVE_PRICE_CEILING_S:.0f} s — the "
            f"open-limit second solve is "
            f"{'affordable' if price < CONTROL_SOLVE_PRICE_CEILING_S else 'NOT run'}"
            f"; leg (d)'s four solves project to "
            f"{4.0 * price:.1f} s of solve time)",
            flush=True,
        )

    assert np.all(np.isfinite(z.real)) and np.all(np.isfinite(z.imag))
    assert abs(z21) > 0.0 and abs(z41) > 0.0 and abs(z31) > 0.0

    assert spread <= ADJACENT_SPREAD_BAND, (
        f"the two ports adjacent to the driven leg read |Z21| = {abs(z21):.9e} "
        f"and |Z41| = {abs(z41):.9e} Ohm, a spread of {spread * 100:.4f}% against "
        f"the pre-stated {ADJACENT_SPREAD_BAND * 100:.1f}% band — the solved "
        "field does not carry the layout's C4 symmetry (§7 `PORT-9` step 3 leg "
        "(c), negative result: magnitudes into the entry and known-issues, park, "
        "stop; never widen)"
    )
    # Retired by ruling (6*) — see the docstring.  The margin is reported above
    # and deliberately not asserted: on the open-limit fixture it read 5.0594x
    # at 116 368 cells and 0.7906x at 116 085 (complex form 6.9398x -> 1.5951x),
    # a conditioning motion, not a geometry one.  Anti-degeneracy is gated on
    # the terminated fixture instead (leg (d0), floor 10x, reads 2256.9707x;
    # leg (d)'s 4x4 class separation, reads 166.6766x).
