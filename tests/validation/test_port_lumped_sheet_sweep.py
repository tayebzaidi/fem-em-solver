"""`PORT-9` step 2c — **the lumped-sheet route through the N-port sweep**.

Step 2b closed step 2's cross-route gate at the narrowed sheet (1.9222% at
``f = 0.5`` against the unmoved 5% band) but left one leg unrun: reciprocity
``‖S − Sᵀ‖/‖S‖ ≤ 1e-3`` **through**
:func:`~fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep`.  That
function had exactly two excitation routes — ``GapVoltagePortSpec`` and the
retiring `PORT-0` heuristic — and no lumped-sheet route at all, so the leg was
a package change, not a fixture wiring job.  `PORT-9` step 3's gate (i) asserts
reciprocity on birdcage lumped-sheet ports through that same function, which
makes this route its prerequisite.

**What this module does.**  One mesh of the step-1/2b fixture (`GEO-16`'s
emitted port sheets), the ``21x`` facet tags narrowed to the gated interior
width ``f = 0.5`` on **both** ports by step 2b's own midpoint filter and its
``w = A/h`` convention (both imported from
``test_port_lumped_narrowed_sheet``/``test_port_lumped_two_torus``, never
restated here), and the two-port sweep driven through the new route: one solve
per driven port, every port's sheet in the bilinear form, the driven port's
sheet carrying the impressed source.

**Bands, all pre-existing.**  Reciprocity ``‖S − Sᵀ‖/‖S‖ ≤ 1e-3`` (step 2's
band, unmoved) is the gate.  The cross-route reading — the sheet's terminal
voltage against the independent terminal-to-terminal path integral off the
*same* solve, now carried through the sweep in
``PortVoltageCurrentEstimate.path_voltage_v`` — is asserted against step 2's
unmoved ``CROSS_ROUTE_BAND`` (5%) and *printed* beside step 2b's ``f = 0.5``
record 1.9222%: the drive differs (an impressed sheet source here, an impressed
gap current there), so the reproduction is reported, not gated at 1e-4.

Cost: standard tier, ``-n 2``, one mesh (~40 s) and two solves (~25 s each).

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-9-step2c "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 500 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_lumped_sheet_sweep.py -v -s'"
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.lumped import LumpedSheetPortSpec
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep

from tests.complex_mode import complex_only
from tests.mesh.test_two_torus_port_facets import _facet_group_area
from tests.mesh.test_two_torus_port_sheet import (
    SHEET_FACET_TAGS,
    _sheet_extents,
    _sheet_facet_count,
)
from tests.validation.test_port_gap_voltage_impedance import (
    FREQUENCY_HZ,
    MAJOR_RADIUS,
    SIGMA_WIRE_S_PER_M,
    WIRE_TAGS,
    _gap_half_extents,
)
from tests.validation.test_port_package_sparameters import (
    PATH_QUADRATURE_ORDER,
    REFERENCE_IMPEDANCE_OHM,
    _arc_quadrature,
)
from tests.validation.test_port_lumped_narrowed_sheet import (
    GATED_WIDTH_FRACTION,
    _narrowed_sheet_tags,
)
from tests.validation.test_port_lumped_two_torus import (
    CROSS_ROUTE_BAND,
    PROBE_PORT_IMPEDANCE_OHM,
    _build,
)

# Step 2's band for ``‖S − Sᵀ‖/‖S‖``, pre-stated at scoping and unmoved; the
# same number `PORT-1` step 4 gated the gap-voltage sweep at.
RECIPROCITY_BAND = 1.0e-3
# Step 2b's gated rung, for the printed comparison only (the drive differs).
# Re-recorded (1*) 2026-09-02, `OPS-31`, from the `ports:3` anchor log
# `20260902T093147Z_OPS-31.log:2245` on image tag v0.11.0 (dolfinx 0.11.0.post0,
# gmsh 4.15.2), matching the same-run STEP1_CROSS_ROUTE_RECORD re-record.
STEP2B_CROSS_ROUTE_AT_HALF_WIDTH = 0.019222      # (v0.7.2 read 0.018333)
# The impressed terminal voltage of the driven sheet. Arbitrary — Z is a ratio
# — but recorded, because every printed V and I below scales with it.
DRIVE_VOLTAGE_V = 1.0 + 0.0j


@pytest.fixture(scope="module")
def sheet_sweep():
    """One mesh; the two-port lumped-sheet sweep (one solve per driven port)."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, facet_tags, t_mesh = _build(comm)
    assert facet_tags is not None, "model_to_mesh returned no facet tags"
    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    # Hoisted on every rank before any facet-restricted form (known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    half_xz, half_y = _gap_half_extents()

    # Both ports narrowed to the gated interior width, by step 2b's midpoint
    # filter applied in turn to the two ``21x`` groups: the filter rewrites one
    # tag and passes every other through, so composing it twice narrows both
    # sheets on one mesh — bit-identical to the ladder's mesh.
    tags_f = facet_tags
    for sheet_tag in SHEET_FACET_TAGS:
        tags_f = _narrowed_sheet_tags(
            msh, tags_f, int(sheet_tag), GATED_WIDTH_FRACTION, MAJOR_RADIUS, half_xz
        )

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            tag: HomogeneousMaterial(sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0)
            for tag in WIRE_TAGS
        },
        boundary_condition="pec_zero_tangential_a",
    )

    ports = []
    specs = []
    sheets = []
    for k, sheet_tag in enumerate(SHEET_FACET_TAGS):
        sheet_tag = int(sheet_tag)
        n_facets = _sheet_facet_count(msh, tags_f, sheet_tag, comm)
        assert n_facets > 0, f"sheet {sheet_tag}: no owned facets anywhere"
        area = _facet_group_area(msh, tags_f, sheet_tag, comm)
        extents = _sheet_extents(msh, tags_f, sheet_tag, comm)
        h = float(extents[1])
        # Step 2b's convention, imported in spirit and re-measured per sheet:
        # the area-based effective width A/h on the *filtered* facet set, never
        # ``f * w_full`` (the bbox extent overstates the ragged edge by 14-15%).
        w = area / h
        sheets.append(
            {
                "tag": sheet_tag,
                "facets": int(n_facets),
                "area": float(area),
                "w": w,
                "w_bbox": float(extents[0]),
                "h": h,
                "out_of_plane": float(extents[2]),
            }
        )
        points, tangents, weights = _arc_quadrature(k, PATH_QUADRATURE_ORDER)
        ports.append(
            PortDefinition(
                port_id=f"P{k + 1}",
                positive_tag=int(sheet_tag),
                negative_tag=WIRE_TAGS[k],
                orientation="gap_azimuthal_plus_y",
                z0_ohm=REFERENCE_IMPEDANCE_OHM,
            )
        )
        specs.append(
            LumpedSheetPortSpec(
                port_id=f"P{k + 1}",
                facet_tag=sheet_tag,
                port_impedance_ohm=PROBE_PORT_IMPEDANCE_OHM,
                gap_height_m=h,
                sheet_width_m=w,
                drive_direction=(0.0, 1.0, 0.0),
                drive_voltage_v=DRIVE_VOLTAGE_V,
                interior=True,
                path_points=points,
                path_tangents=tangents,
                path_weights=weights,
            )
        )

    comm.Barrier()
    t0 = time.perf_counter()
    result = run_n_port_sparameter_sweep(
        problem,
        ports,
        lumped_sheet_ports=specs,
        lumped_sheet_facet_tags=tags_f,
    )
    comm.Barrier()
    t_sweep = time.perf_counter() - t0

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step2c] fragmented two-torus fixture: {ncells} cells, "
            f"mesh {t_mesh:.1f} s; lumped sheets {SHEET_FACET_TAGS} at "
            f"f = {GATED_WIDTH_FRACTION}; two-port sweep {t_sweep:.1f} s",
            flush=True,
        )
        for s in sheets:
            print(
                f"    sheet {s['tag']}  facets {s['facets']:5d}  "
                f"area {s['area']:.9e} m^2  w = A/h = {s['w']:.9e} m "
                f"(bbox {s['w_bbox']:.9e})  h = {s['h']:.9e} m",
                flush=True,
            )

    return {
        "result": result,
        "sheets": sheets,
        "cells": int(ncells),
        "mesh_time": t_mesh,
        "sweep_time": t_sweep,
        "comm": comm,
    }


@complex_only
def test_the_sweep_ran_the_lumped_sheet_route(sheet_sweep):
    """Structural: the sweep took the new route, on two narrowed sheets.

    A solved-field route must report ``is_placeholder=False`` (the flag that
    gates Touchstone export, `PORT-0`/known-issues 3) and must return the ``Z``
    the S-matrix came from; the sheets must be the narrowed, planar ones the
    band was gated on.
    """
    r = sheet_sweep["result"]
    assert not r.is_placeholder, (
        "the lumped-sheet route returned is_placeholder=True — the sweep fell "
        "back to the PORT-0 coupling heuristic"
    )
    assert r.z_matrix is not None, "the lumped-sheet route must return its Z"
    assert r.z_matrix.shape == (2, 2)
    for s in sheet_sweep["sheets"]:
        assert s["out_of_plane"] < 1.0e-12, (
            f"sheet {s['tag']}: out-of-plane spread {s['out_of_plane']:.3e} m "
            "— the filtered facet set is not a plane"
        )
        assert s["w"] < s["w_bbox"], (
            f"sheet {s['tag']}: A/h = {s['w']:.9e} m is not below the bbox "
            f"extent {s['w_bbox']:.9e} m — the narrowed sheet is not ragged, "
            "so the filter did not run"
        )
    for pid, response in r.excitation_results.items():
        for port_id, est in response.responses.items():
            assert est.path_voltage_v is not None, (
                f"driven {pid}, port {port_id}: the route dropped the path "
                "voltage the cross-route comparison is read from"
            )


@complex_only
def test_the_lumped_sheet_sweep_is_reciprocal(sheet_sweep):
    """**Step 2c's gate.**  ``‖S − Sᵀ‖/‖S‖ ≤ 1e-3`` through the sweep.

    Step 2's unrun leg and `PORT-9` step 3's gate (i), asserted here on the
    two-torus fixture: the network is passive and made of reciprocal materials,
    so the S-matrix assembled column by column from two independent solves —
    each with a different port driven — must be symmetric.  It is the identity
    that catches a route wiring the wrong port's sheet, the wrong width, or the
    source into the bilinear form.  The band is step 2's, never widened; an
    asymmetry above it is a finding about the lumped BC's reciprocity.
    """
    r = sheet_sweep["result"]
    s = r.s_matrix
    ratio = float(np.linalg.norm(s - s.T) / np.linalg.norm(s))
    z = r.z_matrix
    z_ratio = float(np.linalg.norm(z - z.T) / np.linalg.norm(z))

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step2c] RECIPROCITY through run_n_port_sparameter_sweep "
            f"on lumped-sheet ports (band {RECIPROCITY_BAND:.0e}, step 2's, "
            f"unmoved):\n"
            f"    ||S - S^T||/||S|| = {ratio:.6e}\n"
            f"    ||Z - Z^T||/||Z|| = {z_ratio:.6e}\n"
            f"    Z12 = {z[0, 1]:+.9e} Ohm, Z21 = {z[1, 0]:+.9e} Ohm\n"
            f"    Z11 = {z[0, 0]:+.9e} Ohm, Z22 = {z[1, 1]:+.9e} Ohm",
            flush=True,
        )

    assert ratio <= RECIPROCITY_BAND, (
        f"lumped-sheet sweep reciprocity ||S - S^T||/||S|| = {ratio:.6e} above "
        f"the pre-stated {RECIPROCITY_BAND:.0e} band (||Z - Z^T||/||Z|| = "
        f"{z_ratio:.6e}) — a finding about the lumped BC's reciprocity through "
        "the sweep, not a licence to widen (§7 `PORT-9` step 2c, negative "
        "result: known-issues entry, step 3 stays blocked, report, stop)"
    )


@complex_only
def test_the_cross_route_reading_holds_inside_the_sweep(sheet_sweep):
    """The two feed models still agree, now read through the sweep.

    Each port reports two voltages off the *same* solve: the sheet's own
    terminal voltage ``V = V_src − I·Z_p`` and the independent
    terminal-to-terminal path integral ``−∫E·t̂ dl``.  Their relative deviation
    at the undriven port is step 2's cross-route quantity — the drive
    normalisation cancels — and it is asserted against step 2's unmoved 5%
    band.  Printed beside step 2b's ``f = 0.5`` record (1.9222%): the drive
    here is the impressed *sheet* source rather than the impressed gap current,
    so the two need not agree to the 1e-4 grain, and the comparison is reported
    rather than gated.
    """
    r = sheet_sweep["result"]
    rows = []
    for driven_id, response in sorted(r.excitation_results.items()):
        for port_id, est in sorted(response.responses.items()):
            if est.is_driven:
                continue
            deviation = abs(est.voltage_v - est.path_voltage_v) / abs(
                est.path_voltage_v
            )
            rows.append((driven_id, port_id, est, float(deviation)))

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step2c] CROSS-ROUTE inside the sweep (band "
            f"{CROSS_ROUTE_BAND * 100:.0f}%, step 2's, unmoved; step 2b read "
            f"{STEP2B_CROSS_ROUTE_AT_HALF_WIDTH * 100:.4f}% at the same width "
            f"under the impressed-gap drive):",
            flush=True,
        )
        for driven_id, port_id, est, deviation in rows:
            print(
                f"    driven {driven_id}, undriven {port_id}: "
                f"|dV|/|V| = {deviation * 100:8.4f}%  "
                f"(step 2b {STEP2B_CROSS_ROUTE_AT_HALF_WIDTH * 100:.4f}%, "
                f"delta {abs(deviation - STEP2B_CROSS_ROUTE_AT_HALF_WIDTH) * 100:.4f} pp)  "
                f"V_sheet = {est.voltage_v:+.9e}, V_path = "
                f"{est.path_voltage_v:+.9e} V",
                flush=True,
            )

    assert rows, "the sweep produced no undriven-port reading to compare"
    for driven_id, port_id, _est, deviation in rows:
        assert deviation <= CROSS_ROUTE_BAND, (
            f"driven {driven_id}, undriven {port_id}: the sheet's terminal "
            f"voltage and the path integral differ by {deviation * 100:.4f}%, "
            f"above step 2's unmoved {CROSS_ROUTE_BAND * 100:.0f}% band — the "
            "sweep route does not read what the fixture path read"
        )
