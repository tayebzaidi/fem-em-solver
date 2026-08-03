"""`PORT-1` step 2: the reaction Z-matrix gate on a two-loop air fixture.

The first S-matrix in this repository derived from a solved field rather than
from placeholder arithmetic.  Two coaxial tagged tori sit in air inside a PEC
box (`GEO-8`'s conforming ``two_torus_domain``); torus ``k`` is driven in turn
with an impressed azimuthal current and the reaction integral

    Z_ik = −(1/(I_k·I_i)) ∫_{torus i} E_k · J_i dV                        (1)

gives one column of the 2×2 impedance matrix per solve.  ``J_i`` is torus i's
*shape* current — the same azimuthal pattern, restricted by the measure to
torus i's tag — and every ``I`` is the **meshed** loop current ``∫J_φ dV/(2πa)``
rather than the nominal 1 A; using the nominal current was a 17% error that
looked like physics in `MAT-6` step 2a.

What is gated, and why each bound is what it is (every number below is a
`PORT-1` step-1 measurement, logs in PROJECT_PLAN §7):

  * **reciprocity** ``‖Z − Zᵀ‖/‖Z‖ < 1e-9``.  Step 1 measured 7.9e-14 …
    4.3e-13 across three mesh/box configurations, i.e. machine precision, so
    1e-9 is four orders of slack and still catches any real symmetry break.
    This is the identity `PORT-1`'s "done when" names.
  * **mutual coupling** ``Im Z₁₂`` within **10%** of the closed form
    ``ωM₁₂ = 1.241755 Ω``, ``M₁₂ = 2πa·A_φ(a,d)/I`` (Jackson 5.37, via
    :meth:`AnalyticalSolutions.circular_loop_vector_potential`).  Step 1
    measured −9.35% at exactly this configuration, and the residual gap is the
    PEC box rather than the mesh: refining h_far 0.02 → 0.03 moves it 0.09%
    while enlarging the padding 0.08 → 0.12 moves it 5.20%, monotonically
    toward the closed form.  The bound is **not** tightened here: the
    filamentary reference itself spans 66.5% of nominal when re-evaluated over
    ρ, z within ± r_wire, so at d = a it cannot support better.
  * **``Re Z₁₂`` structurally zero.**  In the lossless case the curl-curl
    operator is real-symmetric, so the real part is *absent*, not cancelled —
    step 1 measured exactly ``0.0``.  Asserted at 1e-30, which no convergence
    argument could ever justify and which only a structural zero passes.
  * **S symmetric and passive.**  ``S = (Z − Z₀I)(Z + Z₀I)⁻¹`` at Z₀ = 50 Ω.
    A lossless reciprocal 2-port has unitary S, so ``‖S‖₂ = 1``: passivity is
    asserted as ``≤ 1``, and unitarity to 1e-9 as the sharper statement of the
    same physics.

**Negative control.**  The pre-`GEO-8` fixture never fragmented the box against
the tori, so the two loops were meshed as disconnected islands and returned
``Z₁₂`` *identically zero* against a 1.2418 Ω closed form (PROJECT_PLAN §7,
`PORT-1` step-1 attempt of 2026-07-31).  The separation between the honest and
the broken fixture on assertion (ii) is therefore total, not a factor.

**The diagonal is deliberately not gated.**  Step 1 measured
``Im Z₁₁ ≈ −40.9 Ω``, negative where a lossless loop must be inductive and ~6×
a Grover estimate ``ωL ≈ 6.8 Ω``.  It is undiagnosed and `PORT-1` step 2b owns
it; gating "sign and order" here would gate a known-bad number.  The value is
printed instead.

Scope: this closes reciprocity and mutual coupling on a two-loop **air**
fixture.  It does not close `PORT-1` — gap-voltage ports on a real coil are
step 3 — and it does not resolve the two deliberately-red port tests
(known-issues 3).

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_reaction_impedance.py -v -s'
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.analytical import AnalyticalSolutions
from fem_em_solver.utils.constants import EPSILON_0, MU_0

from tests.complex_mode import complex_only

# Geometry and frequency are step 1's, unchanged.  f is a free knob — nothing
# about a reaction Z-matrix ties it to the Larmor frequency — and 10 MHz keeps
# k₀·(box diagonal) ≈ 0.086, well inside the quasistatic regime the ωM
# reference needs.
FREQUENCY_HZ = 10.0e6
MAJOR_RADIUS = 0.04   # a
MINOR_RADIUS = 0.005  # r_wire
SEPARATION = 0.04     # d, centre to centre along z
CURRENT_A = 1.0

# padding 0.08 / h_far 0.03 = 119738 cells, mesh 21 s + solves 21 s and 31 s
# (step 1, log 20260802T183747Z_PORT-1-step1-boxsens.log).  Padding 0.12 at
# h_far 0.02 (237926 cells) was killed at 180 s inside MUMPS and must not be
# used here.
AIR_PADDING = 0.08
H_FAR = 0.03
H_WIRE = 0.0025

TORUS_TAGS = (1, 2)
REFERENCE_IMPEDANCE_OHM = 50.0

OMEGA = 2.0 * np.pi * FREQUENCY_HZ


def _azimuthal_current_density(j_magnitude: float):
    """Uniform azimuthal current about the z-axis.

    Regularised inside the sqrt rather than with ``ufl.max_value``: in complex
    mode UFL refuses conditionals on complex-valued operands, so the
    magnetostatic loop fixture's ``max_value`` form does not compile here.
    """

    def current_density(x):
        rho_safe = ufl.sqrt(x[0] ** 2 + x[1] ** 2 + 1e-24)
        return ufl.as_vector([
            -x[1] / rho_safe * j_magnitude,
            x[0] / rho_safe * j_magnitude,
            0.0,
        ])

    return current_density


def _tag_volume(msh, cell_tags, tag: int, comm) -> float:
    dx_tag = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,)
    )
    one = fem.Constant(msh, np.array(1.0, dtype=np.complex128).item())
    # assemble_scalar is rank-local.
    return float(
        np.real(comm.allreduce(fem.assemble_scalar(fem.form(one * dx_tag)), op=MPI.SUM))
    )


def _reaction(msh, cell_tags, e_field, tag, i_driven, i_test, comm) -> complex:
    """Equation (1) for one (driven, test) pair, reduced across ranks."""
    j_magnitude = CURRENT_A / (np.pi * MINOR_RADIUS**2)
    x = ufl.SpatialCoordinate(msh)
    j_vec = _azimuthal_current_density(j_magnitude)(x)
    dx_tag = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,)
    )
    # J is real, so inner()'s conjugation of its second argument is a no-op:
    # this is the reaction integral ∫E·J, not ∫E·J̄.
    local = fem.assemble_scalar(fem.form(ufl.inner(e_field, j_vec) * dx_tag))
    total = comm.allreduce(local, op=MPI.SUM)
    return complex(-total / (i_driven * i_test))


def mutual_inductance(a: float, rho: float, z: float) -> float:
    """``M = 2πρ·A_φ(ρ, z)/I`` for a unit-current filamentary loop of radius a."""
    pts = np.array([[rho, 0.0, z]], dtype=float)
    A = AnalyticalSolutions.circular_loop_vector_potential(pts, 1.0, a, loop_center=0.0)
    # At (x=ρ, y=0) the azimuthal direction is +y.
    return 2.0 * np.pi * rho * float(A[0, 1])


def scattering_from_impedance(z_matrix: np.ndarray, z0_ohm: float) -> np.ndarray:
    """``S = (Z − Z₀I)(Z + Z₀I)⁻¹`` — the normalised-reference conversion."""
    identity = np.eye(z_matrix.shape[0], dtype=complex)
    return (z_matrix - z0_ohm * identity) @ np.linalg.inv(z_matrix + z0_ohm * identity)


@pytest.fixture(scope="module")
def reaction_z():
    """One mesh, two solves — the whole cost of this file.

    Module-scoped so the four assertions below share it; every rank runs the
    same fixture, so the collective calls inside stay matched.
    """
    comm = MPI.COMM_WORLD
    t_mesh = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=H_FAR,
        air_padding=AIR_PADDING,
        wire_resolution=H_WIRE,
        far_resolution=H_FAR,
        comm=comm,
    )
    t_mesh = time.perf_counter() - t_mesh

    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)

    j_magnitude = CURRENT_A / (np.pi * MINOR_RADIUS**2)
    # ∫J_φ dV = I·2πa for an ideal torus, so the meshed volume fixes the current
    # the solver actually sees.
    volumes = [_tag_volume(msh, cell_tags, t, comm) for t in TORUS_TAGS]
    currents = [j_magnitude * v / (2.0 * np.pi * MAJOR_RADIUS) for v in volumes]

    z_matrix = np.zeros((2, 2), dtype=complex)
    solve_times = []
    for col, driven_tag in enumerate(TORUS_TAGS):
        problem = TimeHarmonicProblem(
            mesh=msh,
            frequency_hz=FREQUENCY_HZ,
            material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
            cell_tags=cell_tags,
            material_map=None,
            boundary_condition="pec_zero_tangential_a",
        )
        solver = TimeHarmonicSolver(problem, degree=1)
        comm.Barrier()
        t0 = time.perf_counter()
        fields = solver.solve(
            current_density=_azimuthal_current_density(j_magnitude),
            subdomain_ids=[driven_tag],
        )
        comm.Barrier()
        solve_times.append(time.perf_counter() - t0)
        for row, test_tag in enumerate(TORUS_TAGS):
            z_matrix[row, col] = _reaction(
                msh, cell_tags, fields.e_complex, test_tag,
                currents[col], currents[row], comm,
            )

    if comm.rank == 0:
        k0 = OMEGA * np.sqrt(MU_0 * EPSILON_0)
        half_x = MAJOR_RADIUS + MINOR_RADIUS + AIR_PADDING
        half_z = SEPARATION / 2 + MINOR_RADIUS + AIR_PADDING
        diag = 2.0 * np.sqrt(2.0 * half_x**2 + half_z**2)
        print(
            f"\n[PORT-1 step 2] padding {AIR_PADDING} m, h_far {H_FAR} m, "
            f"{ncells} cells, mesh {t_mesh:.1f} s, solves "
            + ", ".join(f"{t:.1f} s" for t in solve_times),
            flush=True,
        )
        print(
            f"[PORT-1 step 2] k0*box_diagonal = {k0 * diag:.5f} (quasistatic), "
            f"meshed currents {currents[0]:.6f}, {currents[1]:.6f} A",
            flush=True,
        )
        print(
            f"[PORT-1 step 2] Z = [[{z_matrix[0,0]:+.6e}, {z_matrix[0,1]:+.6e}],\n"
            f"                     [{z_matrix[1,0]:+.6e}, {z_matrix[1,1]:+.6e}]] Ohm",
            flush=True,
        )
        # Not gated — PORT-1 step 2b owns the diagonal (wrong sign, undiagnosed).
        print(
            f"[PORT-1 step 2] ungated diagonal: Im Z11, Im Z22 = "
            f"{z_matrix[0,0].imag:+.6e}, {z_matrix[1,1].imag:+.6e} Ohm",
            flush=True,
        )
    return z_matrix


@complex_only
def test_reaction_z_matrix_is_reciprocal(reaction_z):
    """``‖Z − Zᵀ‖/‖Z‖ < 1e-9`` — the identity `PORT-1`'s "done when" names.

    Step 1 measured 7.86e-14 (padding 0.08 / h_far 0.02), 3.06e-13 (0.08/0.03,
    this configuration) and 4.31e-13 (0.12/0.03): machine precision, so the
    bound is not sensitivity-limited.
    """
    residual = np.linalg.norm(reaction_z - reaction_z.T) / np.linalg.norm(reaction_z)
    if MPI.COMM_WORLD.rank == 0:
        print(f"[PORT-1 step 2] reciprocity ||Z-Z^T||/||Z|| = {residual:.4e}", flush=True)
    assert residual < 1e-9, f"reciprocity residual {residual:.4e} exceeds 1e-9"


@complex_only
def test_mutual_impedance_matches_closed_form(reaction_z):
    """``Im Z₁₂`` within 10% of ``ωM₁₂`` (Jackson 5.37).

    The broken (non-fragmented) fixture returned ``Z₁₂`` identically zero
    against this closed form, so the negative control here is total separation
    rather than a ratio.  10% is the box error at padding 0.08 measured in
    step 1 (−9.35%); see the module docstring for why it is not tightened.
    """
    m12 = mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    omega_m12 = OMEGA * m12
    z12 = 0.5 * (reaction_z[0, 1] + reaction_z[1, 0])
    relative_error = z12.imag / omega_m12 - 1.0
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 2] M12 = {m12:.6e} H, omega*M12 = {omega_m12:+.6e} Ohm; "
            f"Im Z12 = {z12.imag:+.6e} Ohm ({relative_error:+.2%})",
            flush=True,
        )
    assert abs(relative_error) < 0.10, (
        f"Im Z12 = {z12.imag:.6e} Ohm is {relative_error:+.2%} from the closed "
        f"form omega*M12 = {omega_m12:.6e} Ohm"
    )


@complex_only
def test_mutual_impedance_real_part_is_structurally_zero(reaction_z):
    """``Re Z₁₂`` is absent, not small.

    The domain is lossless air, so the curl-curl operator is real-symmetric and
    the reaction integral has no real part to cancel — step 1 measured exactly
    ``0.0``.  1e-30 is far below anything a convergence argument could deliver;
    only a structural zero passes it.
    """
    z12 = 0.5 * (reaction_z[0, 1] + reaction_z[1, 0])
    if MPI.COMM_WORLD.rank == 0:
        print(f"[PORT-1 step 2] Re Z12 = {z12.real:+.6e} Ohm", flush=True)
    assert abs(z12.real) < 1e-30, f"Re Z12 = {z12.real:.6e} Ohm is not structurally zero"


@complex_only
def test_scattering_matrix_is_symmetric_and_passive(reaction_z):
    """``S = (Z − Z₀I)(Z + Z₀I)⁻¹`` at Z₀ = 50 Ω: symmetric and passive.

    The first S-matrix in this repository computed from a solved field.  A
    lossless reciprocal 2-port has *unitary* S, so ``‖S‖₂ = 1`` exactly;
    passivity (``≤ 1``) is the requirement and unitarity to 1e-9 is the sharper
    statement of the same physics, which a real part leaking into Z would break.
    """
    s = scattering_from_impedance(reaction_z, REFERENCE_IMPEDANCE_OHM)
    asymmetry = np.linalg.norm(s - s.T) / np.linalg.norm(s)
    spectral_norm = float(np.linalg.norm(s, 2))
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 2] S (Z0 = {REFERENCE_IMPEDANCE_OHM:.0f} Ohm): "
            f"S11 = {s[0,0]:+.6e}, S21 = {s[1,0]:+.6e}; "
            f"||S-S^T||/||S|| = {asymmetry:.4e}, ||S||_2 = {spectral_norm:.12f}",
            flush=True,
        )
    assert asymmetry < 1e-9, f"S asymmetry {asymmetry:.4e} exceeds 1e-9"
    assert spectral_norm <= 1.0 + 1e-9, f"||S||_2 = {spectral_norm:.12f} is not passive"
    assert abs(spectral_norm - 1.0) < 1e-9, (
        f"lossless network must have unitary S, got ||S||_2 = {spectral_norm:.12f}"
    )
