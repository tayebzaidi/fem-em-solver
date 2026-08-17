"""`PORT-9` step 1 (re-run) — the lumped-port sheet **on the two-torus fixture**.

The parked 2026-08-16 attempt wrote the formulation
(:mod:`fem_em_solver.ports.lumped`, Jin 3e §1.5.4 (1.60)–(1.63) in the
variational form of §6.5 (6.93)–(6.98)) and pinned it against six exact
identities on a one-square unit sheet, but could not instantiate it on the
fixture: a lumped-port sheet spans terminal to terminal with the port current
flowing **in** its plane, and the fixture's only tagged surfaces (201/202) are
gap↔conductor cross-sections **normal** to the current.  `GEO-16` ✅ 2026-08-17
put the right surface in the mesh — ``two_torus_domain(emit_port_sheet=True)``
fragments each gap box on its longitudinal mid-plane and rebuilds facet tags
``211``/``212`` from the cell tags, area = CAD mid-plane to
``1.000000000000``.  This module is the wiring job that follows.

**What it measures.**  One solve of the gapped two-torus fixture at 10 MHz on
the *fragmented* mesh, gap 101 driven exactly as `PORT-1`/`PORT-10` drive it,
with a **passive lumped-port sheet on the undriven port** (facet tag 212).  Off
that one field two routes to the same mutual impedance are read side by side:

  * the gated **gap-voltage route** — ``V = −∫E·t̂ dl`` terminal to terminal on
    the undriven port at the 4097-point rule, normalised by the meshed
    conduction current (`PORT-1` step 3b-x/3b-xiv, raw record 0.894543 × ωM₁₂,
    corrected 0.939849 × ωM₁₂ through ``ports.systematics``);
  * the **lumped-port route** — the sheet's own constitutive law read back off
    the solved field, ``I = (1/R)∫_S(E·ĥ)dS/h`` with ``R = Z_p·w/h`` from the
    sheet's **measured** extents, and its terminal voltage ``V = I·Z_p``.

``Z_p`` is deliberately **near-open** (1e6 Ω): the gap route measures an
open-circuit voltage, so the only lumped reading comparable to it is the one
taken through a termination that draws no appreciable current.  The sheet term
scales as ``1/R``, so at this ``Z_p`` it perturbs the solved field by ~1e-5 of
what a 50 Ω port would — the field the two routes read is, to that accuracy,
the field the gap route was gated on.  In this limit the lumped reading reduces
analytically to ``V = (1/w)∫_S E·ĥ dS``: the gap voltage **averaged over the
sheet**, against the gap route's single centreline path.  The two are different
functionals of the same field and are *expected* to differ by the transverse
variation of ``E·ŷ`` across the gap box; measuring that difference is the whole
point of the step, and adjudicating it is step 2's.

**Nothing here is a port-impedance claim, and nothing here is gated on the
comparison.**  Per §7 `PORT-9` step 1 and the §9 item that scoped this re-run,
this step is measurement-only: the assertions below are the structural
identities that say the two routes read the fixture they claim to (sheet area
against its CAD denominator, gap-box volume against its analytic volume, path
quadrature converged), and the cross-route bands — 10% mutual, 5% cross-route,
1e-3 reciprocity — are pre-stated in step 2 and are step 2's to test.  The
gap-route number is *re-measured* here on the fragmented mesh and printed
beside its unfragmented record: if it moved, that delta is step 2's first
exhibit, not a gate.

Cost: standard tier, ``-n 2``, one mesh (~40 s) and one solve (~25 s).

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-9-step1 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 500 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_lumped_bc.py \\
       tests/validation/test_port_lumped_two_torus.py -v -s'"
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.ports.lumped import (
    LumpedPortSheet,
    lumped_port_bilinear_term,
    sheet_terminal_current,
)
from fem_em_solver.ports.systematics import mutual_systematics_ladder

from tests.complex_mode import complex_only
from tests.mesh.test_two_torus_port_facets import _facet_group_area
from tests.mesh.test_two_torus_port_sheet import (
    SHEET_FACET_TAGS,
    _sheet_extents,
    _sheet_facet_count,
)
from tests.validation.test_port_gap_voltage_impedance import (
    AIR_PADDING,
    DRIVE_CURRENT_A,
    FREQUENCY_HZ,
    GAP_ANGLE,
    GAP_ARC_RESOLUTION,
    GAP_BURIAL,
    GAP_OVERHANG,
    GAP_TAGS,
    H_FAR,
    H_WIRE,
    MAJOR_RADIUS,
    MINOR_RADIUS,
    OMEGA,
    PATH_QUADRATURE_GATE_ORDERS,
    PRODUCTION_LADDER_DRIVEN_COLUMN,
    SEPARATION,
    SIGMA_WIRE_S_PER_M,
    WIRE_TAGS,
    _azimuthal_unit,
    _gap_drive,
    _gap_half_extents,
    _path_voltage,
    _reduce,
    _tag_measure,
    _tag_volume,
)
from tests.validation.test_port_reaction_impedance import mutual_inductance

# `GEO-16`'s fragment: each gap box becomes two cell groups, told apart by
# centroid z. A caller selecting the gap volume by tag must take BOTH halves —
# the caveat that chunk's §7 entry leaves for this step.
GAP_CELL_TAGS_WITH_SHEET = {101: (101, 111), 102: (102, 112)}

# Near-open termination: the sheet term scales as 1/R, so 1e6 Ω makes the
# lumped sheet a probe of the field rather than a load on it — the only reading
# comparable to the gap route's open-circuit voltage. Not a matched port; a 50 Ω
# sheet is a different measurement (step 2's, with its own solve).
PROBE_PORT_IMPEDANCE_OHM = 1.0e6

# The gap-voltage route's records at this configuration (padding 0.08, baseline
# h_box), imported in spirit from `PORT-1` step 3b-xiv/3b-xviii but restated
# here as *printed comparators only* — nothing below asserts on them, because
# the fragmented mesh is a mesh no record was measured on and whether the route
# moved is this step's measurement.
GAP_ROUTE_RAW_RECORD = 0.894543          # × ωM₁₂, unfragmented mesh
GAP_ROUTE_CORRECTED_RECORD = 0.939849    # × ωM₁₂, through ports.systematics

# Structural identity bands, all inherited, none invented here.
VOLUME_IDENTITY_BAND = 1.0e-9            # `PORT-1` 3b-i measured 1.000000000000
AREA_IDENTITY_BAND = 1.0e-9              # `GEO-16` / `GEO-15` CAD denominator
QUADRATURE_DRIFT_TOLERANCE = 1.0e-3      # 3b-x, unmoved


def _build(comm):
    """The gapped two-torus fixture, `PORT-10`'s base corner, sheet emitted.

    Every argument is the landed fixture's except ``emit_port_sheet``: the point
    of the run is to read the gated route on a mesh that differs from the
    record's only by the fragment `GEO-16` introduced.
    """
    t0 = time.perf_counter()
    msh, cell_tags, facet_tags = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=H_FAR,
        air_padding=AIR_PADDING,
        wire_resolution=H_WIRE,
        far_resolution=H_FAR,
        port_gap=True,
        gap_angle=GAP_ANGLE,
        gap_burial=GAP_BURIAL,
        gap_overhang=GAP_OVERHANG,
        gap_arc_resolution=GAP_ARC_RESOLUTION,
        emit_port_sheet=True,
        comm=comm,
    )
    return msh, cell_tags, facet_tags, time.perf_counter() - t0


@pytest.fixture(scope="module")
def lumped_run():
    """One mesh, one solve, both routes read off the same field."""
    comm = MPI.COMM_WORLD
    col = PRODUCTION_LADDER_DRIVEN_COLUMN          # 0 → gap 101 driven
    driven_tags = GAP_CELL_TAGS_WITH_SHEET[GAP_TAGS[col]]
    sheet_tag = SHEET_FACET_TAGS[1 - col]          # 212 — the undriven port

    msh, cell_tags, facet_tags, t_mesh = _build(comm)
    assert facet_tags is not None, "model_to_mesh returned no facet tags"
    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    # Hoisted on every rank before any facet-restricted form (known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    half_xz, half_y = _gap_half_extents()
    gap_length = 2.0 * half_y
    gap_volume = sum(_tag_volume(msh, cell_tags, t, comm) for t in driven_tags)
    gap_area = gap_volume / gap_length
    gap_volume_analytic = (2.0 * half_xz) ** 2 * gap_length
    wire_volume = _tag_volume(msh, cell_tags, WIRE_TAGS[col], comm)
    arc_length = wire_volume / (np.pi * MINOR_RADIUS**2)

    # The sheet, measured — never nominal. `GEO-16`'s entry is explicit that the
    # gap box crosses a round arc, so ``R = Z_p·w/h`` needs extents read off the
    # facet set that was actually reconstructed on this mesh.
    sheet_facets = {t: _sheet_facet_count(msh, facet_tags, t, comm)
                    for t in SHEET_FACET_TAGS}
    sheet_areas = {t: _facet_group_area(msh, facet_tags, t, comm)
                   for t in SHEET_FACET_TAGS}
    sheet_extents = {t: _sheet_extents(msh, facet_tags, t, comm)
                     for t in SHEET_FACET_TAGS}
    sheet_area_cad = 4.0 * half_xz * half_y
    w_measured = float(sheet_extents[sheet_tag][0])     # transverse, x
    h_measured = float(sheet_extents[sheet_tag][1])     # along the current, y

    sheet = LumpedPortSheet(
        port_id=f"p{1 - col}",
        facet_tag=int(sheet_tag),
        port_impedance_ohm=PROBE_PORT_IMPEDANCE_OHM,
        gap_height_m=h_measured,
        sheet_width_m=w_measured,
        # At the gap (x ≈ +a, y ≈ 0) the azimuthal direction is +ŷ — the same
        # direction ``_gap_drive`` impresses its current along, and it lies in
        # the mid-plane the sheet occupies.
        drive_direction=(0.0, 1.0, 0.0),
        source_voltage_v=0.0,
        interior=True,
    )

    x_ufl = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_unit(x_ufl)
    j = DRIVE_CURRENT_A / gap_area
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
    solver = TimeHarmonicSolver(problem, degree=1)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=_gap_drive(j),
        subdomain_ids=list(driven_tags),
        project_source=False,
        extra_bilinear_terms=[
            lambda trial, test: lumped_port_bilinear_term(
                msh, facet_tags, sheet, trial, test, omega_rad_per_s=OMEGA
            )
        ],
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    e = fields.e_complex
    i_conduction = (
        SIGMA_WIRE_S_PER_M
        * _reduce(
            ufl.inner(e, phi_hat) * _tag_measure(msh, cell_tags, WIRE_TAGS[col]), comm
        )
        / arc_length
    )
    # The gap route, unchanged: terminal-to-terminal path integral on the
    # undriven port at the gated order, certified by the coarser one.
    v_gap = _path_voltage(e, 1 - col, PATH_QUADRATURE_GATE_ORDERS[-1], comm)
    v_gap_coarse = _path_voltage(e, 1 - col, PATH_QUADRATURE_GATE_ORDERS[0], comm)
    # The lumped route: the sheet's own law, V = I·Z_p across the termination.
    #
    # Sign: ``sheet_terminal_current`` returns the current in the *generator*
    # convention of ``ports/lumped.py`` — a passive sheet in ``E = +ĥ`` carries
    # ``I = +1/Z_p``, i.e. current along E. A terminal *voltage* in the gap
    # route's convention is ``V = −∫E·t̂ dl`` (note the minus, `PORT-1` 3b-x),
    # so the comparable terminal voltage across the same termination is
    # ``−I·Z_p``. Without this the two routes disagree in sign by construction
    # and the comparison would read as a physics discrepancy that is only a
    # choice of reference direction.
    i_sheet = sheet_terminal_current(msh, facet_tags, sheet, e, comm)
    v_lumped = -i_sheet * PROBE_PORT_IMPEDANCE_OHM

    omega_m = OMEGA * mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    z12_gap = v_gap / i_conduction
    z12_lumped = v_lumped / i_conduction
    ratio_gap = abs(z12_gap.imag) / omega_m
    ratio_lumped = abs(z12_lumped.imag) / omega_m

    record = {
        "cells": int(ncells),
        "mesh_time": t_mesh,
        "solve_time": t_solve,
        "driven_tags": driven_tags,
        "sheet_tag": int(sheet_tag),
        "sheet_facets": sheet_facets,
        "sheet_areas": sheet_areas,
        "sheet_area_cad": sheet_area_cad,
        "w": w_measured,
        "h": h_measured,
        "out_of_plane": float(sheet_extents[sheet_tag][2]),
        "sheet_resistivity": sheet.sheet_resistivity,
        "gap_volume_ratio": gap_volume / gap_volume_analytic,
        "i_conduction": i_conduction,
        "i_sheet": i_sheet,
        "quadrature_drift": abs(v_gap - v_gap_coarse) / abs(v_gap),
        "v_gap": v_gap,
        "v_lumped": v_lumped,
        "z12_gap": z12_gap,
        "z12_lumped": z12_lumped,
        "omega_m": omega_m,
        "ratio_gap": ratio_gap,
        "ratio_lumped": ratio_lumped,
        "corrected_gap": mutual_systematics_ladder(z12_gap.imag, omega_m)["corrected"],
        "corrected_lumped": mutual_systematics_ladder(
            z12_lumped.imag, omega_m
        )["corrected"],
        # Step 2's own metric, computed here so the number it will gate on is
        # on record from the run that first read both routes.
        "cross_route_complex": abs(z12_lumped - z12_gap) / abs(z12_gap),
    }
    if comm.rank == 0:
        print(
            f"\n[PORT-9 step1] fragmented two-torus fixture: {ncells} cells, "
            f"mesh {t_mesh:.1f} s, solve {t_solve:.1f} s; driven gap cell tags "
            f"{driven_tags}, lumped sheet on facet tag {sheet_tag} "
            f"(Z_p = {PROBE_PORT_IMPEDANCE_OHM:.1e} Ohm, near-open probe)",
            flush=True,
        )
    del msh, cell_tags, facet_tags
    return record


@complex_only
def test_the_solved_fixture_carries_the_sheet_and_the_gap_box(lumped_run):
    """Structural identities, asserted before either route is read.

    Three statements, each of which would invalidate both routes if it failed:
    the reconstructed sheet is non-empty and has its CAD mid-plane's area (so
    ``R = Z_p·w/h`` is scaled by the surface the port model thinks it is on);
    the *two-halved* gap box still has its analytic volume (so the drive
    normalisation ``j = I/A`` is the record's, `PORT-1` 3b-i's
    1.000000000000); and the terminal path integral is converged in its
    quadrature.
    """
    for tag in SHEET_FACET_TAGS:
        assert lumped_run["sheet_facets"][tag] > 0, (
            f"sheet facet group {tag} is empty on the solve fixture — the area "
            "identity below would pass vacuously and the port sheet would be a "
            "form over nothing"
        )
    for tag in SHEET_FACET_TAGS:
        ratio = lumped_run["sheet_areas"][tag] / lumped_run["sheet_area_cad"]
        assert abs(ratio - 1.0) < AREA_IDENTITY_BAND, (
            f"sheet {tag}: meshed/CAD area {ratio:.12f} — the surface carrying "
            "the lumped port is not the gap box's mid-plane"
        )
    assert abs(lumped_run["gap_volume_ratio"] - 1.0) < VOLUME_IDENTITY_BAND, (
        f"meshed/analytic gap-box volume {lumped_run['gap_volume_ratio']:.12f} "
        "over both halves — the fragment moved the volume the drive normalises "
        "through"
    )
    assert lumped_run["quadrature_drift"] < QUADRATURE_DRIFT_TOLERANCE, (
        f"the terminal path integral moved {lumped_run['quadrature_drift']:.3e} "
        f"between orders {PATH_QUADRATURE_GATE_ORDERS} — above "
        f"{QUADRATURE_DRIFT_TOLERANCE:.1e}"
    )
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-9 step1] sheet {lumped_run['sheet_tag']}: "
            f"{lumped_run['sheet_facets'][lumped_run['sheet_tag']]} owned facets, "
            f"meshed/CAD area "
            f"{lumped_run['sheet_areas'][lumped_run['sheet_tag']] / lumped_run['sheet_area_cad']:.12f}, "
            f"measured w = {lumped_run['w']:.9e} m, h = {lumped_run['h']:.9e} m, "
            f"w/h = {lumped_run['w'] / lumped_run['h']:.9f} squares "
            f"(out-of-plane spread {lumped_run['out_of_plane']:.1e} m) "
            f"=> R = Z_p*w/h = {lumped_run['sheet_resistivity']:.6e} Ohm/square; "
            f"meshed/analytic gap volume "
            f"{lumped_run['gap_volume_ratio']:.12f}",
            flush=True,
        )


@complex_only
def test_two_routes_printed_on_one_solved_field(lumped_run):
    """**The measurement.**  Lumped-port ``Z`` beside the gap-voltage route.

    Measurement-only by the chunk's own scoping: the cross-route bands are step
    2's and are not asserted here.  What *is* asserted is that both routes
    returned finite numbers off a field that carries current — a route that
    silently read zero (an empty facet set, a restriction that picked the wrong
    side) would otherwise be printed as a comparison.

    The gap route is re-measured on the fragmented mesh and printed against its
    unfragmented record; per the §9 item, a delta there is step 2's first
    exhibit, not a gate.
    """
    r = lumped_run
    assert np.isfinite(abs(r["i_conduction"])) and abs(r["i_conduction"]) > 0.0
    assert np.isfinite(abs(r["v_gap"])) and abs(r["v_gap"]) > 0.0
    assert np.isfinite(abs(r["v_lumped"])) and abs(r["v_lumped"]) > 0.0

    if MPI.COMM_WORLD.rank == 0:
        gap_drift = r["ratio_gap"] - GAP_ROUTE_RAW_RECORD
        cross = (r["ratio_lumped"] - r["ratio_gap"]) / r["ratio_gap"]
        print(
            f"\n[PORT-9 step1] I_cond = {r['i_conduction']:+.6e} A; "
            f"omega*M12 = {r['omega_m']:.6f} Ohm",
            flush=True,
        )
        print(
            f"[PORT-9 step1] GAP route:    V = {r['v_gap']:+.9e} V, "
            f"Im Z12 = {r['z12_gap'].imag:+.9e} Ohm = {r['ratio_gap']:.6f} x "
            f"omega*M12 (corrected {r['corrected_gap']:.6f}); unfragmented "
            f"record {GAP_ROUTE_RAW_RECORD:.6f} raw / "
            f"{GAP_ROUTE_CORRECTED_RECORD:.6f} corrected — delta on the "
            f"fragmented mesh {gap_drift:+.6e} ({gap_drift * 100:+.4f} pp)",
            flush=True,
        )
        print(
            f"[PORT-9 step1] LUMPED route: I_sheet = {r['i_sheet']:+.6e} A, "
            f"V = {r['v_lumped']:+.9e} V, Im Z12 = {r['z12_lumped'].imag:+.9e} "
            f"Ohm = {r['ratio_lumped']:.6f} x omega*M12 "
            f"(corrected {r['corrected_lumped']:.6f})",
            flush=True,
        )
        print(
            f"[PORT-9 step1] CROSS-ROUTE deviation: on the |Im Z12| ratios "
            f"{cross:+.6e} ({cross * 100:+.4f}%); on the complex Z12 "
            f"|Z12(lumped) - Z12(gap)|/|Z12(gap)| = "
            f"{r['cross_route_complex']:.6e} "
            f"({r['cross_route_complex'] * 100:.4f}%) — both PRINTED, neither "
            "gated; step 2's pre-stated band is 5% on the second",
            flush=True,
        )
