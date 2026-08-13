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
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep
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
