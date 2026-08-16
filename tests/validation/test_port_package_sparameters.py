"""`PORT-1` step 4 — the *package* entry point reads the solved field.

Until this file existed, every S-matrix the package produced came from
``ports/excitation.py``'s proximity heuristic (`PORT-0`, known-issues 3): the one
real S-matrix in the repository lived in a test, on the two-torus fixture, and
never travelled through :func:`run_n_port_sparameter_sweep`.  This gate drives
that entry point with ``gap_voltage_ports=`` and asserts it reproduces the
step-3b-xviii record:

  * raw mutual within ``RAW_REPRODUCTION_BAND = 2e-3`` of **0.894283** x omega*M12
    — printed first, as the **miss** it is against the 10% band;
  * corrected mutual (the two named systematics, via
    ``ports/systematics.py``) inside the unmoved ``MUTUAL_TOLERANCE = 0.10``;
  * ``||S - S^T||/||S|| < 1e-3`` — a measured network identity here (two solves,
    two integrands), not an algebraic one;
  * ``||S||_2 <= 1`` (passivity, an inequality, not a reproduction);
  * ``is_placeholder`` False on the result the package returns.

**Negative controls, both executed.**

  * *The retiring heuristic on the same fixture, same mesh, same ports*: its
    S-matrix must differ from the solved-field S beyond the reproduction band.
    A heuristic that accidentally agreed would be a finding about the gate.
  * *The blind fixture*: step 1's unfragmented ancestor returned ``Im Z12``
    identically zero; the same ladder on that number is asserted to **fail** the
    mutual band (cited, not re-solved —
    ``20260731T213222Z_PORT-1-step1-costprobe.log``).

**`PORT-5` step 1 — sweep-level sanity metrics on the field route.**  The
three ``test_sanity_*`` cases at the bottom of this module are a separate
chunk riding the same module-scoped fixture (the metrics are pure numpy; a
second sweep would buy nothing but 160 s of solve).  Until they existed
``summarize_sparameter_sanity`` had only ever seen a placeholder or a
hand-built matrix — §10 target 3's "sweep-level path is untouched".  They
assert the report the *sweep* returns against the step-4 records by a second
route, and drive the warning paths with a heuristic and an asymmetrised S.

**Scope.**  Two-torus fixture only.  No birdcage ports, no B1+, no ``S11``
claim: `PORT-1` step 2b localised an electric-energy excess on this fixture's
diagonal, so nothing here reads ``Z_in`` or ``S11``.  The systematics are this
geometry's at this padding.
"""

from __future__ import annotations

import warnings

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.gap_voltage import GapVoltagePortSpec
from fem_em_solver.ports.sparameters import (
    run_n_port_sparameter_sweep,
    summarize_sparameter_sanity,
)
from fem_em_solver.ports.systematics import mutual_systematics_ladder
from fem_em_solver.utils.analytical import AnalyticalSolutions

# --- the fixture, identical to the step-3b-xviii / EX-18 geometry -----------
FREQUENCY_HZ = 10.0e6
OMEGA = 2.0 * np.pi * FREQUENCY_HZ
MAJOR_RADIUS = 0.04
MINOR_RADIUS = 0.005
SEPARATION = 0.04
AIR_PADDING = 0.08
H_FAR = 0.03
H_WIRE = 0.0025

GAP_ANGLE = 0.30
GAP_BURIAL = 1.0e-3
GAP_OVERHANG = 2.0e-4
GAP_ARC_RESOLUTION = 3.0e-4

WIRE_TAGS = (1, 2)
GAP_TAGS = (101, 102)
SIGMA_WIRE_S_PER_M = 8.0e2
DRIVE_CURRENT_A = 1.0
REFERENCE_IMPEDANCE_OHM = 50.0

# Step 3b-x's converged order; its quadrature-convergence precondition
# (|dV|/|V| = 3.9e-4 at 4097 on the undriven port) is on record in the gate
# module and in EX-18 — the reproduction of the raw ratio below is what carries
# it here.
PATH_QUADRATURE_ORDER = 4097

# --- the anchor, from 20260813T020352Z_PORT-1-step3bxviii-pairgate-n2.log ---
RECORDED_RAW_RATIO = 0.894283
RECORDED_CORRECTED_RATIO = 0.939581
RAW_REPRODUCTION_BAND = 2.0e-3
MUTUAL_TOLERANCE = 0.10
S_SYMMETRY_BAND = 1.0e-3
S_SPECTRAL_NORM_CEILING = 1.0
BLIND_FIXTURE_IM_Z12_OHM = 0.0

# --- PORT-5 step 1 anchors, same log ----------------------------------------
# ||S||_2 as step 4 gated it; the sanity report's `passivity_max_sigma` is the
# largest singular value, i.e. the same quantity reached through
# summarize_sparameter_sanity instead of numpy.linalg.norm(..., 2).
RECORDED_PASSIVITY_MAX_SIGMA = 0.861449
PASSIVITY_REPRODUCTION_BAND = 1.0e-6
# ||S - S^T||/||S|| = 2.5494e-05 (Frobenius) is what step 4 gated.  For a 2x2,
# S - S^T has exactly two non-zero entries of equal magnitude, so
# ||S - S^T||_F = sqrt(2) * max|Sij - Sji| — the report's
# `reciprocity_max_abs_delta` converts to the gated ratio exactly.  The band is
# 2% of the record: the record carries five significant figures and the ratio
# rides a KSP-tolerance solve, so a tighter band would gate the solver's noise.
RECORDED_S_SYMMETRY_RATIO = 2.5494e-05
SYMMETRY_RATIO_BAND = 5.0e-7
# The heuristic route's S is perfectly matched at every driven port (b = 0 on
# the diagonal), so its S is numerically unitary and sigma_max sits at 1.
# MEASURED on this fixture, 20260816T093226Z: 0.999985964171, i.e. 1 to
# 1.4036e-05 — *not* the exact 1.000000000000 the §9 item quoted, which is the
# reaction-route fixture's number (`PORT-1` step 2 iv, plan-archive) and the
# hand-built unitary S of test_port_reaction_impedance.py, both different
# matrices.  Here the off-diagonal comes from the proximity heuristic on this
# mesh and is not exactly reciprocal-unitary.  The band below is 3.5x the
# measured departure; the discriminating assertion is the separation, which
# passed at its pre-stated 0.13 in the same run (measured 0.138537).
RECORDED_HEURISTIC_MAX_SIGMA = 1.0
HEURISTIC_MAX_SIGMA_BAND = 5.0e-5
HEURISTIC_SIGMA_SEPARATION = 0.13


def _mutual_inductance(a: float, rho: float, z: float) -> float:
    pts = np.array([[rho, 0.0, z]], dtype=float)
    A = AnalyticalSolutions.circular_loop_vector_potential(pts, 1.0, a, loop_center=0.0)
    return 2.0 * np.pi * rho * float(A[0, 1])


def _gap_half_extents():
    half_xz = MINOR_RADIUS + GAP_OVERHANG
    half_y = MAJOR_RADIUS * np.sin(0.5 * GAP_ANGLE) + GAP_BURIAL
    return half_xz, half_y


def _gap_box_edge_angle() -> float:
    _, half_y = _gap_half_extents()
    return float(np.arcsin(half_y / MAJOR_RADIUS))


def _azimuthal_unit(x):
    rho = ufl.sqrt(x[0] ** 2 + x[1] ** 2 + 1e-24)
    return ufl.as_vector([-x[1] / rho, x[0] / rho, 0.0])


def _arc_quadrature(port_index: int, order: int):
    """Gauss-Legendre nodes on the centreline arc, terminal to terminal.

    Weights carry the arc-length factor ``a`` so the spec's contract
    (``V = -sum(w_i (E.that)_i)``) holds.  Legendre nodes are strictly interior,
    so the terminals themselves — where a point locates into a cell on either
    side of the material interface — are never sampled.
    """
    phi_term = _gap_box_edge_angle()
    nodes, weights = np.polynomial.legendre.leggauss(order)
    phi = phi_term * nodes
    z_c = (-1.0) ** (port_index + 1) * SEPARATION / 2.0
    points = np.column_stack(
        [
            MAJOR_RADIUS * np.cos(phi),
            MAJOR_RADIUS * np.sin(phi),
            np.full_like(phi, z_c),
        ]
    )
    tangents = np.column_stack([-np.sin(phi), np.cos(phi), np.zeros_like(phi)])
    return points, tangents, MAJOR_RADIUS * phi_term * weights


@pytest.fixture(scope="module")
def package_sweep():
    """Mesh once, then run both routes through the package entry point."""
    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        pytest.skip("needs the complex DolfinX build")

    comm = MPI.COMM_WORLD
    msh, cell_tags, _facet_tags = MeshGenerator.two_torus_domain(
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
        comm=comm,
    )
    tdim = msh.topology.dim
    # Unconditionally on every rank, before any tagged form: the assembler
    # reaches `create_entity_permutations` lazily and only on ranks owning
    # integration entities (PORT-1 step 3b-iv, known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

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

    _, half_y = _gap_half_extents()
    ports = [
        PortDefinition(
            port_id=f"P{k + 1}",
            positive_tag=GAP_TAGS[k],
            negative_tag=WIRE_TAGS[k],
            orientation="gap_azimuthal_plus_y",
            z0_ohm=REFERENCE_IMPEDANCE_OHM,
        )
        for k in range(2)
    ]
    specs = []
    for k in range(2):
        points, tangents, weights = _arc_quadrature(k, PATH_QUADRATURE_ORDER)
        specs.append(
            GapVoltagePortSpec(
                port_id=f"P{k + 1}",
                gap_cell_tag=GAP_TAGS[k],
                gap_length_m=2.0 * half_y,
                conductor_cell_tag=WIRE_TAGS[k],
                conductor_sigma_s_per_m=SIGMA_WIRE_S_PER_M,
                conductor_direction=_azimuthal_unit,
                # Meshed arc length: the gap box buries into the arc ends, so
                # a(2*pi - g) overstates the conductor by the 3.6% step 3b-i
                # measured — the length comes from the meshed volume instead.
                conductor_cross_section_m2=float(np.pi * MINOR_RADIUS**2),
                path_points=points,
                path_tangents=tangents,
                path_weights=weights,
                drive_direction=(0.0, 1.0, 0.0),
                drive_current_a=DRIVE_CURRENT_A,
            )
        )

    solved = run_n_port_sparameter_sweep(problem, ports, gap_voltage_ports=specs)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        heuristic = run_n_port_sparameter_sweep(problem, ports)
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]

    omega_m12 = OMEGA * _mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    return {
        "solved": solved,
        "heuristic": heuristic,
        "deprecations": deprecations,
        "omega_m12": omega_m12,
        "comm": comm,
    }


def test_package_sweep_reproduces_the_gated_mutual(package_sweep):
    """The package entry point lands on the 3b-xviii record, raw first."""
    result = package_sweep["solved"]
    omega_m12 = package_sweep["omega_m12"]
    comm = package_sweep["comm"]

    assert result.z_matrix is not None, "the solved-field route must return its Z"
    assert not result.is_placeholder, (
        "the solved-field route returned is_placeholder=True — the flag that "
        "gates Touchstone export must distinguish it from the heuristic"
    )

    im_z12 = float(result.z_matrix[1, 0].imag)
    ladder = mutual_systematics_ladder(im_z12, omega_m12)
    blind = mutual_systematics_ladder(BLIND_FIXTURE_IM_Z12_OHM, omega_m12)

    if comm.rank == 0:
        print(
            f"[PORT-1 step 4] package path: Im Z12 = {im_z12:+.9e} Ohm, "
            f"omega*M12 = {omega_m12:.6f} Ohm; ladder raw {ladder['raw']:.6f} "
            f"({100.0 * ladder['raw_deviation']:+.2f}%, a MISS against the "
            f"{100.0 * MUTUAL_TOLERANCE:.0f}% band) -> +PEC box "
            f"{ladder['box_corrected']:.6f} -> +gap physics "
            f"{ladder['corrected']:.6f} ({100.0 * ladder['deviation']:+.2f}%); "
            f"record raw {RECORDED_RAW_RATIO:.6f}, corrected "
            f"{RECORDED_CORRECTED_RATIO:.6f}",
            flush=True,
        )
        print(f"[PORT-1 step 4] Z (Ohm) through the package:\n{result.z_matrix}", flush=True)

    assert abs(ladder["raw"] - RECORDED_RAW_RATIO) < RAW_REPRODUCTION_BAND, (
        f"raw mutual {ladder['raw']:.6f} does not reproduce the 3b-xviii record "
        f"{RECORDED_RAW_RATIO:.6f} within {RAW_REPRODUCTION_BAND:.1e} — the "
        "package route is not the gated route"
    )
    assert abs(ladder["corrected"] - RECORDED_CORRECTED_RATIO) < RAW_REPRODUCTION_BAND
    assert abs(ladder["deviation"]) < MUTUAL_TOLERANCE, (
        f"corrected mutual {ladder['corrected']:.6f} is "
        f"{100.0 * ladder['deviation']:+.2f}% against the closed form, outside the "
        f"unmoved {100.0 * MUTUAL_TOLERANCE:.0f}% band"
    )
    assert abs(blind["deviation"]) >= MUTUAL_TOLERANCE, (
        "the blind (unfragmented) fixture's Im Z12 = 0 passed the mutual band — "
        "the band is gating nothing"
    )


def test_package_smatrix_is_symmetric_and_passive(package_sweep):
    """S off the package path: reciprocity as a measured identity, passivity."""
    result = package_sweep["solved"]
    comm = package_sweep["comm"]
    s = result.s_matrix

    symmetry = float(np.linalg.norm(s - s.T) / np.linalg.norm(s))
    spectral = float(np.linalg.norm(s, 2))
    if comm.rank == 0:
        print(
            f"[PORT-1 step 4] S at Z0 = {REFERENCE_IMPEDANCE_OHM:.0f} Ohm:\n{s}\n"
            f"    ||S - S^T||/||S|| = {symmetry:.4e} (band {S_SYMMETRY_BAND:.1e}), "
            f"||S||_2 = {spectral:.6f} (ceiling {S_SPECTRAL_NORM_CEILING:.1f})",
            flush=True,
        )
    assert symmetry < S_SYMMETRY_BAND, (
        f"S is not symmetric: ||S - S^T||/||S|| = {symmetry:.4e} >= {S_SYMMETRY_BAND:.1e}"
    )
    assert spectral <= S_SPECTRAL_NORM_CEILING, (
        f"S is not passive: ||S||_2 = {spectral:.6f} > {S_SPECTRAL_NORM_CEILING:.1f}"
    )


def test_retiring_heuristic_differs_from_the_solved_field(package_sweep):
    """Negative control: the heuristic's S on the same fixture is a different S.

    If these agreed, the gate above would be measuring nothing about the field.
    """
    solved = package_sweep["solved"]
    heuristic = package_sweep["heuristic"]
    comm = package_sweep["comm"]

    assert heuristic.is_placeholder, "the heuristic route must keep marking itself"
    assert package_sweep["deprecations"], (
        "the heuristic route must emit a DeprecationWarning now that the "
        "solved-field route exists"
    )

    delta = float(np.max(np.abs(heuristic.s_matrix - solved.s_matrix)))
    if comm.rank == 0:
        print(
            f"[PORT-1 step 4] negative control — retiring heuristic S:\n"
            f"{heuristic.s_matrix}\n    max|S_heuristic - S_field| = {delta:.6e} "
            f"(must exceed the reproduction band {RAW_REPRODUCTION_BAND:.1e})",
            flush=True,
        )
    assert delta > RAW_REPRODUCTION_BAND, (
        f"the retiring heuristic reproduces the solved-field S to {delta:.3e} — "
        "that is a finding about the heuristic, not a passing gate"
    )


# --- PORT-5 step 1 ----------------------------------------------------------


def test_sanity_report_reproduces_the_gated_metrics_on_the_field_route(package_sweep):
    """The sweep's own sanity report lands on the step-4 records.

    `PORT-5`'s metrics have run on placeholder and hand-built matrices since D3;
    this is the first time the report that ``run_n_port_sparameter_sweep``
    *returns* is checked against a gated number.  Both anchors are the step-4
    quantities reached by a second route — ``passivity_max_sigma`` is
    ``||S||_2`` through ``numpy.linalg.svd`` rather than
    ``numpy.linalg.norm(s, 2)``, and ``reciprocity_max_abs_delta`` converts to
    the gated Frobenius ratio exactly for a 2x2.
    """
    result = package_sweep["solved"]
    comm = package_sweep["comm"]
    report = result.sanity_report
    s = result.s_matrix

    assert not result.is_placeholder, "these anchors are the field route's, not the heuristic's"
    assert s.shape == (2, 2), "the 2x2 conversion below assumes a two-port S"

    symmetry_ratio = float(
        np.sqrt(2.0) * report.reciprocity_max_abs_delta / np.linalg.norm(s)
    )
    if comm.rank == 0:
        print(
            f"[PORT-5 step 1] sweep sanity report on the field route:\n"
            f"    passivity_max_sigma           = {report.passivity_max_sigma:.9f} "
            f"(record {RECORDED_PASSIVITY_MAX_SIGMA:.6f}, band "
            f"{PASSIVITY_REPRODUCTION_BAND:.1e})\n"
            f"    passivity_max_column_power_sum= "
            f"{report.passivity_max_column_power_sum:.9f}\n"
            f"    reciprocity_max_abs_delta     = "
            f"{report.reciprocity_max_abs_delta:.6e}\n"
            f"    reciprocity_max_rel_delta     = "
            f"{report.reciprocity_max_rel_delta:.6e}\n"
            f"    -> ||S-S^T||/||S|| = {symmetry_ratio:.6e} "
            f"(record {RECORDED_S_SYMMETRY_RATIO:.4e}, band "
            f"{SYMMETRY_RATIO_BAND:.1e})\n"
            f"    warnings: {report.warnings or 'none'}",
            flush=True,
        )

    # Same quantity, two implementations: the report must not disagree with the
    # spectral norm step 4 asserted on this very matrix.
    assert abs(report.passivity_max_sigma - float(np.linalg.norm(s, 2))) < 1.0e-12

    assert abs(report.passivity_max_sigma - RECORDED_PASSIVITY_MAX_SIGMA) < (
        PASSIVITY_REPRODUCTION_BAND
    ), (
        f"passivity_max_sigma {report.passivity_max_sigma:.9f} does not reproduce "
        f"the step-4 record {RECORDED_PASSIVITY_MAX_SIGMA:.6f} within "
        f"{PASSIVITY_REPRODUCTION_BAND:.1e}"
    )
    assert abs(symmetry_ratio - RECORDED_S_SYMMETRY_RATIO) < SYMMETRY_RATIO_BAND, (
        f"the report's reciprocity delta converts to ||S-S^T||/||S|| = "
        f"{symmetry_ratio:.6e}, not the gated {RECORDED_S_SYMMETRY_RATIO:.4e}"
    )
    assert report.warnings == (), (
        "the field route tripped a sanity warning it must not trip: "
        f"{report.warnings}"
    )
    # Passivity as an inequality, on the second metric step 4 never read.
    assert report.passivity_max_column_power_sum <= 1.0, (
        "a column of the field-derived S carries more power out than in: "
        f"{report.passivity_max_column_power_sum:.9f} > 1"
    )


def test_sanity_metrics_separate_the_heuristic_from_the_field_route(package_sweep):
    """Negative control: the same metrics on the deprecated heuristic's S.

    The heuristic terminates every driven port in its own ``z0``, so ``b = 0``
    on the diagonal and its largest singular value sits at 1 to 1.4e-05 —
    numerically indistinguishable from a lossless network, and 0.1385 away from
    the field route's.  A metric set that could not tell these apart would be
    reporting on arithmetic rather than on physics.
    """
    field = package_sweep["solved"].sanity_report
    heuristic = package_sweep["heuristic"].sanity_report
    comm = package_sweep["comm"]

    separation = abs(heuristic.passivity_max_sigma - field.passivity_max_sigma)
    if comm.rank == 0:
        print(
            f"[PORT-5 step 1] negative control — heuristic route through the same "
            f"metrics:\n"
            f"    passivity_max_sigma = {heuristic.passivity_max_sigma:.12f} "
            f"(unitary to {HEURISTIC_MAX_SIGMA_BAND:.1e})\n"
            f"    reciprocity_max_abs_delta = "
            f"{heuristic.reciprocity_max_abs_delta:.6e}\n"
            f"    separation from the field route's sigma = {separation:.6f} "
            f"(must exceed {HEURISTIC_SIGMA_SEPARATION:.2f})",
            flush=True,
        )

    assert package_sweep["heuristic"].is_placeholder
    assert abs(heuristic.passivity_max_sigma - RECORDED_HEURISTIC_MAX_SIGMA) < (
        HEURISTIC_MAX_SIGMA_BAND
    ), (
        f"the heuristic's sigma_max moved off 1 to "
        f"{heuristic.passivity_max_sigma:.12f} — the control's premise "
        "(a numerically unitary heuristic S) changed"
    )
    assert separation > HEURISTIC_SIGMA_SEPARATION, (
        f"the sanity metrics separate the heuristic from the solved field by only "
        f"{separation:.6f} — they are not discriminating between the routes"
    )


def test_reciprocity_warning_fires_on_an_asymmetrised_field_smatrix(package_sweep):
    """Negative control: the warning path is reachable, on this very matrix.

    "No warnings on the field route" is only evidence if a warning *can* fire.
    Perturbing one off-diagonal of the gated S by twice the absolute warning
    threshold must trip it — and must trip nothing on the untouched copy.
    """
    result = package_sweep["solved"]
    comm = package_sweep["comm"]

    perturbation = 2.0 * 5.0e-2  # 2x summarize_sparameter_sanity's abs default
    asymmetric = result.s_matrix.copy()
    asymmetric[0, 1] += perturbation
    report = summarize_sparameter_sanity(asymmetric)

    if comm.rank == 0:
        print(
            f"[PORT-5 step 1] negative control — S[0,1] perturbed by "
            f"{perturbation:.3f}: reciprocity_max_abs_delta = "
            f"{report.reciprocity_max_abs_delta:.6e}, warnings = {report.warnings}",
            flush=True,
        )

    assert report.reciprocity_max_abs_delta == pytest.approx(perturbation, rel=1.0e-3), (
        "the perturbation did not land in the reciprocity metric: "
        f"{report.reciprocity_max_abs_delta:.6e} vs {perturbation:.6e}"
    )
    assert any("reciprocity abs delta" in w for w in report.warnings), (
        "an S asymmetric by twice the warning threshold produced no reciprocity "
        f"warning: {report.warnings}"
    )
    # The untouched matrix must still be clean — the warning is about the
    # perturbation, not about the fixture.
    assert summarize_sparameter_sanity(result.s_matrix).warnings == ()
