"""`PORT-10` — the two `PORT-1` systematics: their **composition**, measured.

`PORT-1`'s port-pair gate (step 3b-xviii) carries two measured systematics
between the gapped two-torus fixture's ``Im Z₁₂`` and the filamentary closed
form, and ``fem_em_solver.ports.systematics.mutual_systematics_ladder``
composes them one after the other:

  * the **PEC box** — ``D∞ = +1.69 pp`` of ratio at ``p = 1.657``, an
    *effective-range* extrapolation of the padding sweep (3b-xi);
  * **gap physics** — ``÷(1 − 0.030224)``, the gap-generator feed model's
    documented, gap-geometry-dependent impedance error (Jin, *The FEM in
    Electromagnetics* 3rd ed., §10.4.2.1), which 3b-xvi showed is *not* feed
    discretisation (1.57× local refinement moves the estimator ``+0.0508 pp``
    against a 0.5 pp band).

Each term was measured **with the other held at its baseline**, and the ladder
then applies them in sequence — an assumption of separability that no
measurement has ever tested.  If the two interact, the corrected number the
port-pair gate quotes is wrong by the interaction, and the size of that error
is unknown rather than small.

**The design** is the 2×2 factorial that measures the interaction directly.
Each systematic has an experimental knob on this fixture — the PEC box is
``air_padding``, the gap/feed term is the gap-box mesh size ``h_box`` — so the
four corners

    (padding 0.08, h_box baseline)   (padding 0.10, h_box baseline)
    (padding 0.08, h_box 6.0e-4)     (padding 0.10, h_box 6.0e-4)

are one mesh + one solve each, all four in one command, all four reading the
*same* estimator: the terminal-to-terminal ``−∫E·t̂ dl`` on the undriven port
with gap 101 driven, normalised by the meshed conduction current, exactly as
3b-xvi's probe read it.  Writing ``r(pad, box)`` for the raw ratio
``|Im Z₁₂|/ωM₁₂``, the two individually-measured shifts are

    Δ_box  = r(0.10, base) − r(0.08, base)
    Δ_feed = r(0.08, 6e-4) − r(0.08, base)

and the **cross-term** is what this module gates:

    X = [r(0.10, 6e-4) − r(0.08, base)] − (Δ_box + Δ_feed)

``X = 0`` says the two knobs move the estimator independently at this grain,
which is the premise the sequential ladder rests on.  The band is the **±0.5 pp**
the scoping review pre-stated (§7 `PORT-10`) — the same grain 3b-xvi's own
band used, so a cross-term this factorial cannot resolve is one 3b-xvi could
not have seen either.

**A cross-term outside the band is a finding, not a licence to widen.**  Per
the chunk's negative-result clause it annotates ``systematics.py``'s quotation
rule and opens a known-issues entry; nothing in the ladder or in
``MUTUAL_TOLERANCE`` moves in-slot.

**What this does not claim.**  ``Δ_box`` here is one finite padding step
(0.08 → 0.10), not the ``W → ∞`` extrapolation ``D∞`` itself, and ``Δ_feed`` is
the feed-discretisation *probe* of the gap term, not the gap physics itself
(which has no knob short of changing the topology).  What the factorial tests is
whether the two knobs' effects add — i.e. whether measuring each with the other
at baseline, as both were measured, is legitimate.  It is silent on the
extrapolations layered on top of them.

**Anchors, asserted before the cross-term is read.**  Both baseline corners
reproduce numbers already on record at their own configuration: 0.894543 at
(0.08, base) — the 3b-xiv/3b-xv/3b-xvi record — and 0.895051 at (0.08, 6.0e-4),
3b-xvi's refined arm.  Reproducing them is what says this module's leaner solve
path is the same measurement as the record's; the band is 0.1 pp, 5× tighter
than the gate's own grain.

**Negative controls, both executed in-run on the same cross-term function.**
A joint corner displaced by +1.0 pp must fail the band (otherwise the gate
accepts everything), and the wedge-only estimator on record — 0.493653 × ωM₁₂,
the integral that misses the buried gap arc — substituted for the joint corner
must fail it by tens of pp.

Cost: heavy tier, ``-n 2``, four meshes and four solves in one command.
Measured envelope from the arms already on record: at padding 0.08 the
unrefined arm is 178 055 cells / 35.8 s mesh / 25.5 s solve and the 6.0e-4 arm
246 364 cells / 49.3 s / 29.8 s — 174 s for that pair end to end
(`20260812T170317Z_PORT-1-step3bxvi-solve6e4.log`); padding 0.10 costs
1.0951× the cells (194 985 unrefined, `20260807T170143Z_PORT-1-step3bxii-probe.log`).

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-10 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 560 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_systematics_composition.py -v -s'"
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

from tests.complex_mode import complex_only
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

# The factorial.  ``None`` is "no gap-box size field", i.e. the landed fixture;
# 6.0e-4 is 3b-xvi's refined arm, the one whose +0.0508 pp is on record.
BASELINE_AIR_PADDING = AIR_PADDING          # 0.08, the landed fixture
PADDED_AIR_PADDING = 0.10                   # 3b-xi/3b-xii's next rung
BASELINE_GAP_BOX_RESOLUTION = None
REFINED_GAP_BOX_RESOLUTION = 6.0e-4

CORNERS = (
    ("base", BASELINE_AIR_PADDING, BASELINE_GAP_BOX_RESOLUTION),
    ("padded", PADDED_AIR_PADDING, BASELINE_GAP_BOX_RESOLUTION),
    ("refined", BASELINE_AIR_PADDING, REFINED_GAP_BOX_RESOLUTION),
    ("joint", PADDED_AIR_PADDING, REFINED_GAP_BOX_RESOLUTION),
)

# The gate, pre-stated at scoping (§7 `PORT-10`) and not moved by what the
# measurement says: the cross-term, in ratio units, must be inside ±0.5 pp —
# 3b-xvi's grain.
CROSS_TERM_BAND = 5.0e-3

# The two corners already on record, and the band they must reproduce in.
# 0.894543: 3b-xiv, re-reproduced by 3b-xv and by 3b-xvi's unrefined arm.
# 0.895051: 3b-xvi's refined arm at h_box = 6.0e-4
# (`20260812T170317Z_PORT-1-step3bxvi-solve6e4.log`).  0.1 pp is 5x tighter
# than the cross-term band; it is a reproduction check on the same code path at
# the same rank count, not a physics claim.
ESTIMATOR_RECORD_BASE = 0.894543
ESTIMATOR_RECORD_REFINED = 0.895051
REPRODUCTION_BAND = 1.0e-3

# Quadrature precondition, inherited unmoved from 3b-x: the gated V is the
# 4097-point rule and the 2049-point one certifies it.  On record the drift is
# 3.911e-04 (unrefined) / 7.969e-04 (refined) at padding 0.08.
QUADRATURE_DRIFT_TOLERANCE = 1.0e-3

# The cell-count stop rule, inherited from 3b-xvi and applied to every corner:
# 237 926 cells once died in MUMPS at 180 s on the ungapped padding-0.12
# fixture, and the padded+refined corner is the largest mesh this lineage has
# solved.  A corner above the ceiling is reported, not silently solved.
CELL_CEILING = 350_000

# Negative control 1: a joint corner displaced by this much must fail the band.
# 1.0 pp is 2x CROSS_TERM_BAND, so a gate that accepts it is accepting a
# cross-term twice its own size.
DISPLACEMENT_PP = 1.0e-2

# Negative control 2, on record: the uncorrected wedge-only estimator — the
# integral over the nominal 0.30 rad wedge, which misses the buried gap arc
# carrying 45% of the EMF (3b-vi/3b-vii, corrected by 3b-x).
WEDGE_ONLY_ESTIMATOR = 0.493653


def _build(comm, air_padding, gap_box_resolution):
    """The gapped two-torus fixture at one corner of the factorial.

    Every argument except ``air_padding`` and ``gap_box_resolution`` is the
    landed fixture's, so the only things that differ between corners are the
    two knobs under test.
    """
    t0 = time.perf_counter()
    msh, cell_tags, facet_tags = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=H_FAR,
        air_padding=air_padding,
        wire_resolution=H_WIRE,
        far_resolution=H_FAR,
        port_gap=True,
        gap_angle=GAP_ANGLE,
        gap_burial=GAP_BURIAL,
        gap_overhang=GAP_OVERHANG,
        gap_arc_resolution=GAP_ARC_RESOLUTION,
        gap_box_resolution=gap_box_resolution,
        comm=comm,
    )
    return msh, cell_tags, facet_tags, time.perf_counter() - t0


def _solve_corner(comm, label, air_padding, gap_box_resolution):
    """One corner: mesh, one solve at gap 101, the raw ratio |Im Z₁₂|/ωM₁₂.

    Deliberately the *leanest* read of the estimator — one solve, one driven
    column, the undriven port's terminal-to-terminal voltage at the two gated
    quadrature orders.  The five-solve
    :func:`~tests.validation.test_port_gap_voltage_impedance._solve_gap_ports`
    would buy four corners' worth of closure decompositions, σ ladders and
    reaction controls that this chunk does not read; 3b-xvi's probe took the
    same lean path and the record this module reproduces was measured on it.
    """
    msh, cell_tags, facet_tags, t_mesh = _build(comm, air_padding, gap_box_resolution)
    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    # Hoisted on every rank before any facet-restricted form, unconditionally —
    # the lazy-collective hang of 3b-iv (known-issues 9, retired).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    col = PRODUCTION_LADDER_DRIVEN_COLUMN
    _half_xz, half_y = _gap_half_extents()
    gap_length = 2.0 * half_y
    gap_volume = _tag_volume(msh, cell_tags, GAP_TAGS[col], comm)
    gap_area = gap_volume / gap_length
    wire_volume = _tag_volume(msh, cell_tags, WIRE_TAGS[col], comm)
    arc_length = wire_volume / (np.pi * MINOR_RADIUS**2)

    # The meshed gap box against its analytic volume: an identity (3b-i measured
    # 1.000000000000), and the cheapest statement that this corner's mesh is the
    # fixture it claims to be before a solve is bought for it.
    half_xz, _half_y = _gap_half_extents()
    gap_volume_analytic = (2.0 * half_xz) ** 2 * gap_length
    gap_volume_ratio = gap_volume / gap_volume_analytic

    x_ufl = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_unit(x_ufl)

    j = DRIVE_CURRENT_A / gap_area
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            tag: HomogeneousMaterial(
                sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0
            )
            for tag in WIRE_TAGS
        },
        boundary_condition="pec_zero_tangential_a",
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=_gap_drive(j),
        subdomain_ids=[GAP_TAGS[col]],
        project_source=False,
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
    v_fine = _path_voltage(e, 1 - col, PATH_QUADRATURE_GATE_ORDERS[-1], comm)
    v_coarse = _path_voltage(e, 1 - col, PATH_QUADRATURE_GATE_ORDERS[0], comm)
    omega_m = OMEGA * mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    z12 = v_fine / i_conduction

    record = {
        "label": label,
        "air_padding": air_padding,
        "gap_box_resolution": gap_box_resolution,
        "cells": int(ncells),
        "mesh_time": t_mesh,
        "solve_time": t_solve,
        "gap_volume_ratio": gap_volume_ratio,
        "i_conduction": i_conduction,
        "v_undriven": v_fine,
        "quadrature_drift": abs(v_fine - v_coarse) / abs(v_fine),
        "z12_imag": z12.imag,
        "ratio": abs(z12.imag) / omega_m,
        "omega_m": omega_m,
    }
    if comm.rank == 0:
        print(
            f"\n[PORT-10 {label}] padding {air_padding} m, h_box "
            f"{'baseline' if gap_box_resolution is None else f'{gap_box_resolution:.1e} m'}: "
            f"{ncells} cells (ceiling {CELL_CEILING}), mesh {t_mesh:.1f} s, "
            f"solve {t_solve:.1f} s; meshed/analytic gap volume "
            f"{gap_volume_ratio:.12f}",
            flush=True,
        )
        print(
            f"[PORT-10 {label}] I_cond = {i_conduction:+.6e} A, V_undriven = "
            f"{v_fine:+.9e} V (quadrature drift "
            f"{PATH_QUADRATURE_GATE_ORDERS[0]}->"
            f"{PATH_QUADRATURE_GATE_ORDERS[-1]}: "
            f"{record['quadrature_drift']:.3e}); Im Z12 = {z12.imag:+.9e} Ohm "
            f"= {record['ratio']:.6f} x omega*M12",
            flush=True,
        )
    del msh, cell_tags, facet_tags
    return record


def _cross_term(ratios: dict) -> dict:
    """The interaction of the two knobs, from the four corner ratios.

    Pure arithmetic on four measured numbers, so the negative controls can be
    executed on it without buying a fifth solve — the same property that let
    3b-xviii's ladder be gated on the blind fixture's ``Z₁₂ ≡ 0``.
    """
    delta_box = ratios["padded"] - ratios["base"]
    delta_feed = ratios["refined"] - ratios["base"]
    delta_joint = ratios["joint"] - ratios["base"]
    cross = delta_joint - (delta_box + delta_feed)
    return {
        "delta_box": delta_box,
        "delta_feed": delta_feed,
        "delta_joint": delta_joint,
        "sum_of_parts": delta_box + delta_feed,
        "cross": cross,
    }


@pytest.fixture(scope="module")
def factorial():
    """All four corners, one command.  Module-scoped: the cross-term is a
    difference of differences, so the four ratios must come from one run of one
    code path or the interaction is confounded with everything that changed
    between runs."""
    comm = MPI.COMM_WORLD
    if comm.rank == 0:
        print(
            f"\n[PORT-10] 2x2 factorial: padding "
            f"{{{BASELINE_AIR_PADDING}, {PADDED_AIR_PADDING}}} x h_box "
            f"{{baseline, {REFINED_GAP_BOX_RESOLUTION:.1e}}}, four meshes, four "
            f"solves; estimator = terminal-to-terminal |Im Z12|/omega*M12 on the "
            f"undriven port with gap {GAP_TAGS[PRODUCTION_LADDER_DRIVEN_COLUMN]} "
            f"driven, I_cond normalisation. Cross-term band "
            f"{CROSS_TERM_BAND:.1e} (+-0.5 pp), pre-stated at scoping.",
            flush=True,
        )
    return {
        label: _solve_corner(comm, label, padding, box)
        for label, padding, box in CORNERS
    }


@complex_only
def test_every_corner_is_the_fixture_it_claims_to_be(factorial):
    """Structural gates on all four corners, before any interaction is read.

    Three cheap statements per corner, each of which would invalidate the
    cross-term if it failed: the mesh carries the gap box the estimator
    integrates through (meshed/analytic volume is an identity, 3b-i measured
    1.000000000000); the solve stayed inside the cell ceiling this lineage has
    demonstrated; and the gated 4097-point quadrature agrees with the 2049-point
    rule that certifies it, so each corner's voltage is converged in the
    quadrature before four of them are differenced.
    """
    for label, _padding, _box in CORNERS:
        record = factorial[label]
        assert abs(record["gap_volume_ratio"] - 1.0) < 1.0e-9, (
            f"{label}: meshed/analytic gap-box volume "
            f"{record['gap_volume_ratio']:.12f} — the gap the estimator "
            "integrates through is not the box the fixture specifies"
        )
        assert record["cells"] < CELL_CEILING, (
            f"{label}: {record['cells']} cells is above the {CELL_CEILING} "
            "ceiling this lineage has solved inside the tier"
        )
        assert record["quadrature_drift"] < QUADRATURE_DRIFT_TOLERANCE, (
            f"{label}: the terminal path integral moved "
            f"{record['quadrature_drift']:.3e} between orders "
            f"{PATH_QUADRATURE_GATE_ORDERS} — above "
            f"{QUADRATURE_DRIFT_TOLERANCE:.1e}, so this corner's voltage is not "
            "converged in the quadrature and cannot enter a difference of "
            "differences"
        )
    if MPI.COMM_WORLD.rank == 0:
        total_mesh = sum(factorial[c[0]]["mesh_time"] for c in CORNERS)
        total_solve = sum(factorial[c[0]]["solve_time"] for c in CORNERS)
        print(
            f"\n[PORT-10] four corners: cells "
            + ", ".join(f"{c[0]} {factorial[c[0]]['cells']}" for c in CORNERS)
            + f"; mesh {total_mesh:.1f} s, solve {total_solve:.1f} s total",
            flush=True,
        )


@complex_only
def test_the_two_baseline_corners_reproduce_their_records(factorial):
    """The anchors: this leaner solve path is the measurement the record was.

    ``(0.08, baseline)`` is the estimator 0.894543 × ωM₁₂ that 3b-xiv measured,
    3b-xv re-reproduced and 3b-xvi's unrefined arm reproduced again; ``(0.08,
    6.0e-4)`` is 3b-xvi's refined arm at 0.895051.  Both are asserted at 0.1 pp
    — 5× tighter than the cross-term band — because nothing about the *physics*
    changed here, only how much of the five-solve harness is bought.  A miss
    means this module's corners are not the record's quantity, and the
    interaction it computes would be an interaction of something else.
    """
    for label, record_value in (
        ("base", ESTIMATOR_RECORD_BASE),
        ("refined", ESTIMATOR_RECORD_REFINED),
    ):
        measured = factorial[label]["ratio"]
        miss = measured - record_value
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-10] anchor {label}: measured {measured:.6f} x omega*M12 "
                f"vs record {record_value:.6f} — miss {miss:+.3e} "
                f"({miss * 100:+.4f} pp, band {REPRODUCTION_BAND:.1e})",
                flush=True,
            )
        assert abs(miss) < REPRODUCTION_BAND, (
            f"corner {label} reads {measured:.6f} x omega*M12 against the "
            f"on-record {record_value:.6f} (miss {miss:+.3e} >= "
            f"{REPRODUCTION_BAND:.1e}) — this module's lean solve path is not "
            "reproducing the estimator the systematics were measured on, so its "
            "cross-term is not about them"
        )


@complex_only
def test_the_two_systematics_compose_without_a_cross_term(factorial):
    """**The gate.**  The interaction of the PEC-box and gap/feed knobs.

    ``systematics.mutual_systematics_ladder`` applies the two corrections in
    sequence, each measured with the other at baseline.  That is legitimate
    exactly when the two knobs' effects on the estimator add — when the joint
    corner sits where the two individual shifts predict.  The residual

        X = [r(joint) − r(base)] − ([r(padded) − r(base)] + [r(refined) − r(base)])

    is what a sequential ladder assumes is zero, and ±0.5 pp is the grain at
    which 3b-xvi's own band was set.

    Both negative controls run on the same arithmetic, off the same four
    numbers: a joint corner displaced 1.0 pp (twice the band) must fail, and the
    wedge-only estimator on record (0.493653 × ωM₁₂ — the integral that misses
    the buried gap arc) substituted for the joint corner must fail by tens of
    pp.  A band that admitted either would be gating nothing.

    A cross-term outside the band is a **finding**: annotate the quotation rule
    in ``ports/systematics.py``, open a known-issues entry, report.  The band
    does not move, and neither does the ladder, in the slot that measures it.
    """
    ratios = {label: factorial[label]["ratio"] for label, _p, _b in CORNERS}
    terms = _cross_term(ratios)

    displaced = _cross_term({**ratios, "joint": ratios["joint"] + DISPLACEMENT_PP})
    wedge = _cross_term({**ratios, "joint": WEDGE_ONLY_ESTIMATOR})

    if MPI.COMM_WORLD.rank == 0:
        print(
            "\n[PORT-10] corner ratios (x omega*M12): "
            + ", ".join(f"{k} {ratios[k]:.6f}" for k, _p, _b in CORNERS),
            flush=True,
        )
        print(
            f"[PORT-10] shifts off base: PEC box (padding "
            f"{BASELINE_AIR_PADDING} -> {PADDED_AIR_PADDING}) "
            f"{terms['delta_box']:+.6e} ({terms['delta_box'] * 100:+.4f} pp); "
            f"gap/feed (h_box baseline -> {REFINED_GAP_BOX_RESOLUTION:.1e}) "
            f"{terms['delta_feed']:+.6e} ({terms['delta_feed'] * 100:+.4f} pp; "
            f"3b-xvi measured +0.0508 pp); joint "
            f"{terms['delta_joint']:+.6e} ({terms['delta_joint'] * 100:+.4f} pp) "
            f"vs sum of parts {terms['sum_of_parts']:+.6e} "
            f"({terms['sum_of_parts'] * 100:+.4f} pp)",
            flush=True,
        )
        print(
            f"[PORT-10] CROSS-TERM X = {terms['cross']:+.6e} "
            f"({terms['cross'] * 100:+.4f} pp) against the pre-stated band "
            f"+-{CROSS_TERM_BAND:.1e} (+-{CROSS_TERM_BAND * 100:.1f} pp)",
            flush=True,
        )
        print(
            f"[PORT-10] negative controls: joint displaced "
            f"{DISPLACEMENT_PP * 100:+.1f} pp gives X = "
            f"{displaced['cross']:+.6e} ({displaced['cross'] * 100:+.4f} pp); "
            f"the wedge-only estimator {WEDGE_ONLY_ESTIMATOR:.6f} as the joint "
            f"corner gives X = {wedge['cross']:+.6e} "
            f"({wedge['cross'] * 100:+.4f} pp) — both must fail the band",
            flush=True,
        )

    assert abs(displaced["cross"]) > CROSS_TERM_BAND, (
        f"a joint corner displaced {DISPLACEMENT_PP:.1e} still gives "
        f"X = {displaced['cross']:+.3e}, inside the band — the gate below "
        "cannot see an interaction twice its own size"
    )
    assert abs(wedge["cross"]) > CROSS_TERM_BAND, (
        f"the wedge-only estimator as the joint corner gives "
        f"X = {wedge['cross']:+.3e}, inside the band — the gate below would "
        "pass an estimator that never found the buried gap arc"
    )
    assert np.isfinite(terms["cross"])
    assert abs(terms["cross"]) <= CROSS_TERM_BAND, (
        f"the PEC-box and gap/feed systematics do NOT compose additively at "
        f"this grain: cross-term X = {terms['cross']:+.6e} "
        f"({terms['cross'] * 100:+.4f} pp) against the pre-stated "
        f"+-{CROSS_TERM_BAND * 100:.1f} pp. Shifts: box "
        f"{terms['delta_box']:+.6e}, feed {terms['delta_feed']:+.6e}, joint "
        f"{terms['delta_joint']:+.6e}. This is `PORT-10`'s negative result — "
        "annotate the quotation rule in ports/systematics.py and open a "
        "known-issues entry; do NOT widen this band and do NOT change the "
        "ladder in the slot that measured it."
    )
