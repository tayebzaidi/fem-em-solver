"""`PORT-9` steps 1–2 — the lumped-port sheet **on the two-torus fixture**.

*(Step 2, 2026-08-17: the cross-route adjudication is written into this same
module because it adjudicates numbers read off **one** solved field — the field
step 1 already solves here.  A second module would have meant a second mesh and
a second solve of the same 184 919-cell fixture for no new physics.  Step 1's
fixture record and its two assertions are unchanged; step 2 only adds reads off
the field and the tests at the end of the file.)*


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
from tests.validation.test_port_gap_voltage_impedance import _fringe_fraction
from tests.validation.test_port_reaction_impedance import mutual_inductance
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel

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

# ---------------------------------------------------------------------------
# Step 2 — the cross-route adjudication and its diagnosis.
# ---------------------------------------------------------------------------
# Pre-stated at scoping (§7 `PORT-9` step 2), never widened here or anywhere.
# They are recorded as module constants so the numbers this run measures are
# printed against the band they were always going to be judged by; whether they
# hold is the step's finding, and the §7 entry carries the verdict.
CROSS_ROUTE_BAND = 0.05                  # |ΔZ12|/|Z12|, two feed models
MUTUAL_BAND = 0.10                       # |ratio − 1| against omega*M12

# Step 1's own measurements on this identical fixture (2026-08-17,
# `20260817T050734Z_PORT-9-step1-rerun-final.log`). Reproducing them is the
# run's anchor: step 2 adds reads off the same field and must not move it.
# OPS-18 step 3a re-record, 2026-08-23 (18:00 review ruling (1) of 2026-08-22,
# condition (b) as restated (b') on 2026-08-23; extended to the class as (1*)
# by the 10:30 review of 2026-08-23, which admits the two records this same
# assertion loop unmasked once the gap ratio was written).  All three are
# measured on image tag v0.11.0 (dolfinx 0.11.0.post0, gmsh 4.15.2), where this
# fixture meshes to 184 176 cells; the recording image v0.7.2 (184 919 cells)
# read 0.894310 / 0.829782 / 0.077095.  The mesh moved 4.017e-03 relative with
# the image's gmsh, ~24-40x these records' misses.  The 1e-4 REPRODUCTION_BAND
# below is unchanged, as are the physics bands; under (b') each record's own
# run-to-run move is 3.3e-10 (gap ratio, 3.3e-06 of band), 6.6e-10 (lumped
# ratio, 6.6e-06 of band) and below the printed six digits (cross-route).
STEP1_GAP_RATIO_RECORD = 0.894141        # × omega*M12, fragmented mesh
                                         # (v0.7.2 read 0.894310)
STEP1_LUMPED_RATIO_RECORD = 0.828893     # × omega*M12
                                         # (v0.7.2 read 0.829782)
STEP1_CROSS_ROUTE_RECORD = 0.077431      # |ΔZ12|/|Z12|
                                         # (v0.7.2 read 0.077095)
# The lumped route's own `Im Z12`, in ohms — the width-flat quantity.  Measured
# 1.029281338 / …337 / …336 / …338 at -n 2 / 4 / 8 / 12 (`PORT-12` step 1), i.e.
# flat to 2e-9 relative where the gap route moves 2.06e-04.
STEP1_LUMPED_IM_Z12_OHM = 1.029281338
LUMPED_WIDTH_FLATNESS_RTOL = 1.0e-8      # 5x the measured 2e-9 spread
REPRODUCTION_BAND = 1.0e-4               # 0.01 pp — the grain step 1 printed to
# `PORT-12` step 2 (ruled 2026-08-30 weekly review, option (i) with a bounded
# envelope).  REPRODUCTION_BAND above is a **`-n 2` record**: every
# `PORT-1`/`OPS-18`/`PORT-9` two-torus digit quoted in this module was measured
# at two ranks, and the gap route — a `V = -int E.dl` line integral whose path
# crosses partition boundaries — drifts with rank width on this fixture even
# with the `shared_facet` ghost layer present (`GEO-24` step 1b, `PORT-12`
# step 1).  The drift is non-monotone and confined to the gap route:
#   -n 2  gap 0.894141 (= record)   Im Z12(lumped) 1.029281338
#   -n 4  gap 0.894274 (+1.33e-04)  Im Z12(lumped) 1.029281337
#   -n 8  gap 0.894347 (+2.06e-04)  Im Z12(lumped) 1.029281336   <- worst width
#   -n 12 gap 0.894274 (+1.33e-04)  Im Z12(lumped) 1.029281338
# all on 184 176 cells, every reconstruction digit identical.  So at
# ``comm.size > 2`` the same assertion runs against this pre-registered
# envelope — 3e-4, 1.46x headroom over the worst observed +2.06e-04 — rather
# than being skipped: the drift stays *bounded on every width CI might run*.
# Widening the record band itself was declined (it would let the `-n 2` record
# drift); so was a root-cause step on the line integral (no birdcage or Larmor
# quantity reads a gap-route integral — see the lumped negative control below).
PARALLEL_DRIFT_ENVELOPE = 3.0e-4         # `comm.size > 2` only; provenance above

# Exact-arithmetic identities: these are algebra on one solved field, so they
# hold to round-off or the code is wrong.
DECOMPOSITION_IDENTITY_BAND = 1.0e-11

# The §9 item's threshold for "the hypothesis explains the miss": the
# sheet-average-minus-centreline term must account for the cross-route
# deviation to within ~1 pp.
HYPOTHESIS_EXPLANATION_BAND = 0.01

# Transverse stations across the sheet, as fractions of its half-width, at
# which the per-line voltage profile is sampled. Kept off the very edge
# (|s| ≤ 0.98) so every quadrature point is strictly inside the gap box.
PROFILE_STATIONS = np.linspace(-0.98, 0.98, 9)
PROFILE_ORDER = 513                      # per station; the chord uses the
                                         # gated orders instead


def _sheet_chord_voltage(e_field, x_station, z_c, half_y, order, comm) -> complex:
    """``V = −∫E·ŷ dy`` along a straight line **in the sheet**, at fixed ``x``.

    This is the lumped port's own path: the sheet spans terminal to terminal
    along ``ĥ = ŷ`` at every ``x`` across its width, and its reading is the
    ``x``-average of exactly this integral (see
    :func:`test_the_open_limit_reduces_to_the_sheet_average`).  The gated gap
    route instead integrates ``E·φ̂`` along the *curved centreline* between the
    same two terminal planes.  Comparing this chord at ``x = a`` against the gap
    route isolates the path/projection difference; comparing the ``x``-average
    against this chord isolates the transverse averaging.  That two-term split
    is the whole content of step 2's diagnosis.
    """
    nodes, weights = np.polynomial.legendre.leggauss(order)
    y = half_y * nodes
    points = np.column_stack(
        [np.full_like(y, float(x_station)), y, np.full_like(y, float(z_c))]
    )
    values, valid = evaluate_vector_field_parallel(e_field, points, comm)
    if not bool(np.all(valid)):
        raise RuntimeError(
            f"sheet chord at x = {x_station:.6e}: {int((~valid).sum())} of "
            f"{order} quadrature points located in no cell — the chord left the "
            "mesh"
        )
    return complex(-half_y * np.sum(weights * values[:, 1]))


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

    # --- step 2: the same field, read three more ways -------------------
    # (a) the sheet average, assembled independently of ``ports.lumped`` so the
    #     open-limit reduction V = −(1/w)∫_S E·ĥ dS is a *checked* identity and
    #     not a restatement of the module under test;
    # (b) the shadow/fringe partition of that average, the fringe hypothesis's
    #     own decomposition;
    # (c) straight chords in the sheet plane at nine transverse stations.
    ds_sheet = ufl.Measure(
        "dS", domain=msh, subdomain_data=facet_tags, subdomain_id=(int(sheet_tag),)
    )
    h_hat = ufl.as_vector([0.0, 1.0, 0.0])
    e_y = ufl.inner(e("+"), h_hat)
    # `GEO-16`'s sheet is the gap box's longitudinal mid-plane, so the tube's
    # intersection with it is the band |x − a| < r_minor: the sheet's own fringe
    # is the pair of outer strips of half-width GAP_OVERHANG, an area fraction
    # 1 − r/(r + overhang) — NOT 3b-xii's `_fringe_fraction`, which is the disc
    # shadow on a face *normal* to the current. Both are printed below; the
    # difference between them is exactly why the hypothesis needs measuring
    # rather than quoting.
    x_ufl_sheet = ufl.SpatialCoordinate(msh)("+")
    in_shadow = ufl.conditional(
        ufl.lt(abs(x_ufl_sheet[0] - MAJOR_RADIUS), MINOR_RADIUS), 1.0, 0.0
    )
    area_shadow = _reduce(in_shadow * ds_sheet, comm).real
    area_fringe = _reduce((1.0 - in_shadow) * ds_sheet, comm).real
    int_ey = _reduce(e_y * ds_sheet, comm)
    int_ey_shadow = _reduce(in_shadow * e_y * ds_sheet, comm)
    int_ey_fringe = _reduce((1.0 - in_shadow) * e_y * ds_sheet, comm)
    v_sheet_average = -int_ey / w_measured

    z_c = (-1.0) ** ((1 - col) + 1) * SEPARATION / 2.0
    v_chord = _sheet_chord_voltage(
        e, MAJOR_RADIUS, z_c, half_y, PATH_QUADRATURE_GATE_ORDERS[-1], comm
    )
    v_chord_coarse = _sheet_chord_voltage(
        e, MAJOR_RADIUS, z_c, half_y, PATH_QUADRATURE_GATE_ORDERS[0], comm
    )
    profile = [
        (
            float(s),
            _sheet_chord_voltage(
                e, MAJOR_RADIUS + s * half_xz, z_c, half_y, PROFILE_ORDER, comm
            ),
        )
        for s in PROFILE_STATIONS
    ]

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
        # --- step 2 ---
        "v_sheet_average": v_sheet_average,
        "v_chord": v_chord,
        "chord_drift": abs(v_chord - v_chord_coarse) / abs(v_chord),
        "area_shadow": area_shadow,
        "area_fringe": area_fringe,
        "int_ey": int_ey,
        "int_ey_shadow": int_ey_shadow,
        "int_ey_fringe": int_ey_fringe,
        "profile": profile,
        "z_c": z_c,
        "half_y": half_y,
        "half_xz": half_xz,
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


# ===========================================================================
# Step 2 — cross-route adjudication.
# ===========================================================================


@complex_only
def test_step_1_measurements_reproduce(lumped_run):
    """Step 2 reads more off step 1's field; it must not have moved the field.

    The three numbers step 1 put on record — gap ratio, lumped ratio,
    cross-route deviation — reproduce to ``REPRODUCTION_BAND`` (0.01 pp, the
    grain step 1 printed to).  This is the run's anchor in the §4 sense and its
    guard against the step-2 additions (an extra ``dS`` form over the sheet, a
    facet-tag-driven measure, ~5 000 point evaluations) having perturbed the
    assembly they read from.

    The records are `-n 2` records (see ``REPRODUCTION_BAND``); at wider
    partitions the gap route drifts by up to +2.06e-04 for reasons that are
    the fixture's, not this step's (`PORT-12`), so the comparison there runs
    against the pre-registered ``PARALLEL_DRIFT_ENVELOPE`` and the measured
    drift is printed.  The band is never widened at `-n 2`.
    """
    r = lumped_run
    comm = MPI.COMM_WORLD
    parallel = comm.size > 2
    band = PARALLEL_DRIFT_ENVELOPE if parallel else REPRODUCTION_BAND
    for name, measured, record in (
        ("gap ratio", r["ratio_gap"], STEP1_GAP_RATIO_RECORD),
        ("lumped ratio", r["ratio_lumped"], STEP1_LUMPED_RATIO_RECORD),
        ("cross-route", r["cross_route_complex"], STEP1_CROSS_ROUTE_RECORD),
    ):
        if parallel and comm.rank == 0:
            print(
                f"[PORT-12 step2] {name} at -n {comm.size}: {measured:.6f} "
                f"vs the -n 2 record {record:.6f} — drift "
                f"{measured - record:+.2e} against the "
                f"{PARALLEL_DRIFT_ENVELOPE:.0e} envelope",
                flush=True,
            )
        assert abs(measured - record) < band, (
            f"{name}: {measured:.6f} against step 1's record {record:.6f} — "
            f"moved by {abs(measured - record):.2e}, above {band:.0e} "
            f"at comm.size = {comm.size}; "
            + (
                "the parallel drift envelope is a bound on a known fixture "
                "effect (PORT-12), not a licence — a reading outside it is a "
                "new fact about the gap route"
                if parallel
                else "step 2's reads changed step 1's solve"
            )
        )


@complex_only
def test_the_lumped_route_is_width_flat(lumped_run):
    """The negative control for `PORT-12`'s width qualification.

    The gap route's rank-width drift is tolerated above only because the
    *lumped* route — the sheet's own constitutive law, which is what every
    production port model reads (`PORT-9`, `PORT-11`) — reads the same solved
    field and does not move: ``Im Z12(lumped)`` is 1.029281338 / …337 / …336 /
    …338 at 2 / 4 / 8 / 12 ranks, flat to 2e-9 where the gap route moves
    2.06e-04.  If this assertion ever fires, the field itself moved with the
    partition and `PORT-12`'s envelope stops being a statement about one
    line-integral estimator.

    It is load-bearing at 1e-8: the gap route's own ``Im Z12`` is 1.110303775,
    which misses this record by 7.9e-02 relative — seven orders outside.
    """
    r = lumped_run
    measured = r["z12_lumped"].imag
    rel = abs(measured - STEP1_LUMPED_IM_Z12_OHM) / abs(STEP1_LUMPED_IM_Z12_OHM)
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-12 step2] Im Z12(lumped) at -n {MPI.COMM_WORLD.size}: "
            f"{measured:.9f} Ohm vs the record "
            f"{STEP1_LUMPED_IM_Z12_OHM:.9f} — relative {rel:.3e} against "
            f"{LUMPED_WIDTH_FLATNESS_RTOL:.0e}",
            flush=True,
        )
    assert rel < LUMPED_WIDTH_FLATNESS_RTOL, (
        f"Im Z12(lumped) = {measured:.9f} Ohm against the width-flat record "
        f"{STEP1_LUMPED_IM_Z12_OHM:.9f} — relative {rel:.3e}, above "
        f"{LUMPED_WIDTH_FLATNESS_RTOL:.0e}: the lumped route moved with rank "
        "width, so PORT-12's drift is not confined to the gap-route integral"
    )


@complex_only
def test_the_open_limit_reduces_to_the_sheet_average(lumped_run):
    """``V_lumped = -(1/w) int_S E.hhat dS`` — the premise the diagnosis rests on.

    The whole hypothesis under test says the lumped route *is* the gap voltage
    averaged over the sheet.  That is algebra —
    ``I = (1/R) int_S (E.hhat) dS / h`` with ``R = Z_p*w/h`` gives
    ``I*Z_p = (1/w) int_S E.hhat dS`` — but it is algebra spread across
    :mod:`fem_em_solver.ports.lumped`, the fixture's measured ``w``/``h`` and
    the sign convention, so it is checked here against an independently
    assembled form rather than asserted in prose.

    The shadow/fringe partition of that same average is checked to close on the
    unsplit integral, so the decomposition printed below is a partition and not
    two overlapping reads.
    """
    r = lumped_run
    rel = abs(r["v_lumped"] - r["v_sheet_average"]) / abs(r["v_lumped"])
    assert rel < DECOMPOSITION_IDENTITY_BAND, (
        f"lumped terminal voltage {r['v_lumped']:+.9e} V against the "
        f"independently assembled sheet average {r['v_sheet_average']:+.9e} V "
        f"— relative {rel:.3e}, above {DECOMPOSITION_IDENTITY_BAND:.0e}: the "
        "open-limit reduction the diagnosis assumes does not hold for this code"
    )
    area_total = r["sheet_areas"][r["sheet_tag"]]
    area_split = r["area_shadow"] + r["area_fringe"]
    assert abs(area_split / area_total - 1.0) < DECOMPOSITION_IDENTITY_BAND, (
        f"shadow {r['area_shadow']:.9e} + fringe {r['area_fringe']:.9e} = "
        f"{area_split:.9e} m^2 against the sheet's {area_total:.9e} m^2 — the "
        "transverse partition is not a partition"
    )
    int_split = r["int_ey_shadow"] + r["int_ey_fringe"]
    assert abs(int_split - r["int_ey"]) < DECOMPOSITION_IDENTITY_BAND * abs(
        r["int_ey"]
    ), (
        f"partitioned sheet integral {int_split:+.9e} against the unsplit "
        f"{r['int_ey']:+.9e}"
    )


@complex_only
def test_the_cross_route_miss_is_the_transverse_average(lumped_run):
    """**Step 2's adjudication.**  Is the 7.71% miss the two feed definitions?

    Step 1 measured a cross-route deviation of **7.7095%** against the 5% band
    pre-stated at scoping.  The band does not move; what step 2 owes is a
    diagnosis, and the §7 entry's hypothesis is specific enough to be falsified:
    the lumped route is the gap voltage *transversely averaged over the sheet*
    while the gap route integrates the *centreline* only, so the miss should be
    the transverse variation of ``E.yhat`` and nothing else.

    That splits the deviation into two terms measured off one field:

      * **transverse** — ``|V_avg - V_chord| / |V_gap|``, the sheet average
        against the same functional evaluated on the centre chord ``x = a``;
      * **path** — ``|V_chord - V_gap| / |V_gap|``, the centre chord (straight,
        ``hhat = yhat``) against the gated route (curved, ``that = phihat``)
        between the same terminal planes.

    The hypothesis is that the **path** residual is negligible — i.e. the two
    routes differ only in how they average across the gap.  The §9 item fixes
    the threshold at ~1 pp, pre-stated, and that is what is asserted.  A path
    residual above it means the miss is *not* purely the two feed definitions,
    and is the informative negative result.

    Nothing here widens the 5% or 10% bands: their verdicts are printed with the
    numbers, and the §7 entry records them.
    """
    r = lumped_run
    assert r["chord_drift"] < QUADRATURE_DRIFT_TOLERANCE, (
        f"the sheet chord moved {r['chord_drift']:.3e} between orders "
        f"{PATH_QUADRATURE_GATE_ORDERS} — the diagnosis's own path integral is "
        "not converged"
    )
    v_gap, v_avg, v_chord = r["v_gap"], r["v_sheet_average"], r["v_chord"]
    transverse = abs(v_avg - v_chord) / abs(v_gap)
    path = abs(v_chord - v_gap) / abs(v_gap)
    total = abs(v_avg - v_gap) / abs(v_gap)
    # The metric step 2 gates on is |dZ12|/|Z12|; both routes divide by the same
    # I_cond, so the voltage ratio above IS that metric — checked, not assumed.
    assert abs(total - r["cross_route_complex"]) < DECOMPOSITION_IDENTITY_BAND, (
        f"voltage-space deviation {total:.9e} against the impedance-space "
        f"{r['cross_route_complex']:.9e} — the two routes do not share I_cond"
    )

    if MPI.COMM_WORLD.rank == 0:
        area_total = r["sheet_areas"][r["sheet_tag"]]
        f_fringe_sheet = r["area_fringe"] / area_total
        f_fringe_analytic = 1.0 - MINOR_RADIUS / (MINOR_RADIUS + GAP_OVERHANG)
        mean_shadow = r["int_ey_shadow"] / r["area_shadow"]
        mean_fringe = r["int_ey_fringe"] / r["area_fringe"]
        print(
            f"\n[PORT-9 step2] sheet transverse partition: shadow "
            f"{r['area_shadow']:.9e} m^2 ({1.0 - f_fringe_sheet:.6f}), fringe "
            f"{r['area_fringe']:.9e} m^2 ({f_fringe_sheet:.6f}) — analytic "
            f"strip fraction 1 - r/(r+overhang) = {f_fringe_analytic:.6f}; "
            f"3b-xii's disc `_fringe_fraction` (a face NORMAL to the current, "
            f"not this plane) = {_fringe_fraction(GAP_OVERHANG):.6f}",
            flush=True,
        )
        print(
            f"[PORT-9 step2] mean E.yhat over the sheet: shadow "
            f"{mean_shadow:+.6e}, fringe {mean_fringe:+.6e} V/m, ratio "
            f"fringe/shadow {abs(mean_fringe) / abs(mean_shadow):.6f}",
            flush=True,
        )
        print(
            f"[PORT-9 step2] transverse voltage profile (x = a + s*half_xz, "
            f"half_xz = {r['half_xz']:.6e} m), V = -int E_y dy:",
            flush=True,
        )
        for s, v in r["profile"]:
            print(
                f"    s = {s:+.3f}  x = {MAJOR_RADIUS + s * r['half_xz']:.9e} m  "
                f"V = {v:+.9e} V  |V|/|V_chord| = {abs(v) / abs(v_chord):.6f}",
                flush=True,
            )
        print(
            f"[PORT-9 step2] DECOMPOSITION of the cross-route miss "
            f"{total * 100:.4f}%: transverse averaging "
            f"{transverse * 100:.4f} pp, path/projection residual "
            f"{path * 100:.4f} pp (hypothesis threshold "
            f"{HYPOTHESIS_EXPLANATION_BAND * 100:.2f} pp)",
            flush=True,
        )
        print(
            f"[PORT-9 step2] V_gap = {v_gap:+.9e}, V_chord = {v_chord:+.9e}, "
            f"V_avg = {v_avg:+.9e} V",
            flush=True,
        )
        for name, ratio in (
            ("gap", r["corrected_gap"]),
            ("lumped", r["corrected_lumped"]),
        ):
            verdict = "INSIDE" if abs(ratio - 1.0) <= MUTUAL_BAND else "MISS"
            print(
                f"[PORT-9 step2] BAND {name} corrected ratio {ratio:.6f} vs "
                f"omega*M12: |ratio-1| = {abs(ratio - 1.0) * 100:.4f}% against "
                f"the {MUTUAL_BAND * 100:.0f}% mutual band — {verdict}",
                flush=True,
            )
        cross_verdict = "INSIDE" if total <= CROSS_ROUTE_BAND else "MISS"
        print(
            f"[PORT-9 step2] BAND cross-route {total * 100:.4f}% against the "
            f"{CROSS_ROUTE_BAND * 100:.0f}% band — {cross_verdict} (pre-stated "
            "at scoping; not widened)",
            flush=True,
        )

    assert path < HYPOTHESIS_EXPLANATION_BAND, (
        f"path/projection residual {path * 100:.4f} pp of the "
        f"{total * 100:.4f}% cross-route miss — above the pre-stated "
        f"{HYPOTHESIS_EXPLANATION_BAND * 100:.2f} pp, so the miss is NOT "
        "purely the sheet-average-vs-centreline difference between the two "
        "feed definitions: part of it is the path the gap route integrates "
        "along. Record both terms and report (§7 `PORT-9` step 2, negative "
        "result); never widen the 5% cross-route band to admit it."
    )
