"""`TH-7`: evanescent TE₁₀ below waveguide cutoff, against the closed form.

Second physical closed-form gate on the complex curl-curl solve, in the same
mould as `TH-6` (`tests/validation/test_lossy_plane_wave.py`) but exercising a
*different* term: `TH-6` measures decay driven by `Im ε_c` (the mass term's
imaginary part), this one measures decay in a **lossless** medium driven purely
by the transverse geometry — the operator's real part.  A solver that dropped
`k₀²ε` entirely would still decay here, but at the wrong rate.

In an a×b PEC waveguide the TE₁₀ mode has transverse profile ``sin(πx/a)`` and
cutoff wavenumber ``k_c = π/a`` (cutoff ``f_c = c/2a``).  Below cutoff
``k₀ < k_c`` the axial dependence is a real exponential:

    E(x, y, z) = ŷ · sin(πx/a) · e^{−γz},    γ = √(k_c² − k₀²)   [Np/m]

This is an exact **source-free** solution of the solved PDE: ``∇·E = 0`` (E_y
does not depend on y), so ``∇×∇×E = −∇²E = (k_c² − γ²)E = k₀²E``, which is
``∇×(μᵣ⁻¹∇×E) − k₀²ε_c E = 0`` at ``εᵣ = μᵣ = 1``, ``σ = 0``.  It also satisfies
PEC on the four side walls identically (``E_y = 0`` at ``x = 0, a``; ``E_y`` is
normal at ``y = 0, b``).

The gate imposes the field on the whole boundary via ``dirichlet_e_field`` and
fits the *interior* log-amplitude slope along z.  The boundary data pins the two
end faces only; nothing in it tells the interior how fast to fall between them —
that is ``k₀²`` acting through the mass term.  Set ``k₀ = 0`` and the measured γ
collapses to ``k_c``; the frequency-sensitivity test below is exactly that
negative control, run at two frequencies whose closed-form γ differ by 2.6×.

Below cutoff there is no resonance risk (γ real ⇒ no pole in the sweep band), so
the `TH-1` step-5 energy-continuity guard is asserted **quiet** here rather than
being worked around.  Real, source-free, lossless data ⇒ the solved phasor is
real; the residual imaginary part is checked as a further convention control.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_waveguide_cutoff.py -v'
"""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI
from petsc4py import PETSc

from dolfinx import fem, mesh as dmesh

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
    check_energy_continuity,
    stored_electric_energy,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.constants import EPSILON_0, MU_0

from tests.complex_mode import complex_only

# Guide cross-section and length.  a = 0.05 m puts the TE₁₀ cutoff at
# f_c = c/2a = 2.998 GHz.  L = a so that the main gate at 2.4 GHz gives
# γL ≈ 1.885 — an amplitude drop of ~6.6×, deep enough to fit a slope over the
# clipped interior and far above the discretisation floor.  b = a/2 keeps TE₀₁
# (cutoff c/2b = 6 GHz) and every other mode well above the band.
A_M = 0.05
B_M = 0.025
L_M = 0.05

FREQUENCY_HZ = 2.4e9

# Sweep for the frequency-sensitivity test and the resonance guard, all below
# cutoff: closed-form γ = 59.2 / 37.7 / 22.6 Np/m, a 2.6× span that a k₀-blind
# solver (γ ≡ k_c = 62.83 at every frequency) cannot reproduce.
SWEEP_HZ = (1.0e9, 2.4e9, 2.8e9)

# Probe line parallel to z, at an off-lattice (x, y) so points never land on a
# facet plane of the structured mesh, and near x = a/2 where |E_y| is largest.
LINE_X_FRACTION = 0.4863
LINE_Y_FRACTION = 0.5137
FIT_Z_MIN_FRACTION = 0.15
FIT_Z_MAX_FRACTION = 0.85
N_PROBE = 41


def _k0(frequency_hz: float) -> float:
    return float(2.0 * np.pi * frequency_hz * np.sqrt(MU_0 * EPSILON_0))


def cutoff_frequency_hz() -> float:
    """TE₁₀ cutoff ``f_c = c/2a``."""
    return float(1.0 / (2.0 * A_M * np.sqrt(MU_0 * EPSILON_0)))


def _analytic_gamma(frequency_hz: float) -> float:
    """``γ = √(k_c² − k₀²)`` [Np/m]; requires operation below cutoff."""
    k_c = np.pi / A_M
    k0 = _k0(frequency_hz)
    assert k0 < k_c, (
        f"f = {frequency_hz:.4e} Hz is at or above the TE10 cutoff "
        f"{cutoff_frequency_hz():.4e} Hz — the mode propagates, γ is imaginary"
    )
    return float(np.sqrt(k_c * k_c - k0 * k0))


def _exact_factory(frequency_hz: float):
    """Dirichlet/reference callables for the evanescent TE₁₀ field."""
    gamma = _analytic_gamma(frequency_hz)

    def exact_numpy(x: np.ndarray) -> np.ndarray:
        value = np.sin(np.pi * x[0] / A_M) * np.exp(-gamma * x[2])
        zeros = np.zeros_like(value)
        return np.array([zeros, value, zeros], dtype=PETSc.ScalarType)

    def exact_ufl(x):
        value = ufl.sin(np.pi * x[0] / A_M) * ufl.exp(-gamma * x[2])
        return ufl.as_vector([0.0 * value, value, 0.0 * value])

    return exact_numpy, exact_ufl


def _probe_points() -> np.ndarray:
    zs = np.linspace(FIT_Z_MIN_FRACTION * L_M, FIT_Z_MAX_FRACTION * L_M, N_PROBE)
    return np.column_stack(
        [
            np.full_like(zs, LINE_X_FRACTION * A_M),
            np.full_like(zs, LINE_Y_FRACTION * B_M),
            zs,
        ]
    )


def _solve_evanescent(n: int, frequency_hz: float, degree: int = 1):
    """Solve the source-free below-cutoff TE₁₀ field on an n × n/2 × n box.

    Returns ``(rel_l2_error, gamma_fit, imag_ratio, energy_j, ncells)``.
    """
    comm = MPI.COMM_WORLD
    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([A_M, B_M, L_M])],
        [n, max(1, n // 2), n],
        cell_type=dmesh.CellType.tetrahedron,
    )

    exact_numpy, exact_ufl = _exact_factory(frequency_hz)
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=frequency_hz,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=exact_numpy,
    )
    solver = TimeHarmonicSolver(problem, degree=degree)
    # No current: the evanescent mode is an exact source-free solution.
    fields = solver.solve()

    x = ufl.SpatialCoordinate(msh)
    exact = exact_ufl(x)
    diff = fields.e_complex - exact
    # assemble_scalar is rank-local — reduce before the square root.
    err_sq = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(diff, diff) * ufl.dx)), op=MPI.SUM
    )
    ref_sq = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(exact, exact) * ufl.dx)), op=MPI.SUM
    )
    rel_error = float(np.sqrt(abs(err_sq)) / np.sqrt(abs(ref_sq)))

    points = _probe_points()
    real_values, valid_real = evaluate_vector_field_parallel(fields.e_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(fields.e_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(f"{int((~valid).sum())} probe points were not evaluated")

    ey_real = np.real(real_values[:, 1])
    ey_imag = np.real(imag_values[:, 1])
    zs = points[:, 2]

    # ln|E_y| = −γz + const, a straight line in z.
    gamma_fit = -float(np.polyfit(zs, np.log(np.abs(ey_real + 1j * ey_imag)), 1)[0])
    imag_ratio = float(np.max(np.abs(ey_imag)) / np.max(np.abs(ey_real)))

    energy = stored_electric_energy(fields, comm)
    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    return rel_error, gamma_fit, imag_ratio, energy, int(ncells)


@complex_only
@pytest.mark.integration
def test_evanescent_te10_decay_matches_cutoff_closed_form():
    """Interior decay constant matches ``γ = √(k_c² − k₀²)`` to < 5%.

    The 5% is PROJECT_PLAN §10's MVP criterion, not a fitted tolerance, and the
    field error is required to fall under refinement so a coincidental match at
    one mesh size cannot pass.
    """
    comm = MPI.COMM_WORLD
    gamma_exact = _analytic_gamma(FREQUENCY_HZ)
    k_c = float(np.pi / A_M)

    rel_coarse, gamma_coarse, _, _, cells_coarse = _solve_evanescent(12, FREQUENCY_HZ)
    rel_fine, gamma_fine, imag_ratio, _, cells_fine = _solve_evanescent(24, FREQUENCY_HZ)

    rate = float(np.log(rel_coarse / rel_fine) / np.log(2.0))
    gamma_err = abs(gamma_fine - gamma_exact) / gamma_exact

    if comm.rank == 0:
        print(
            "\n[TH-7] evanescent TE10, a = %.3f m, f = %.4g Hz (f_c = %.4g Hz):"
            % (A_M, FREQUENCY_HZ, cutoff_frequency_hz())
        )
        print(
            f"  closed form: k_c = {k_c:.4f} 1/m, k0 = {_k0(FREQUENCY_HZ):.4f} 1/m, "
            f"gamma = {gamma_exact:.6f} Np/m (gamma*L = {gamma_exact * L_M:.3f})"
        )
        print(
            f"  coarse ({cells_coarse:6d} cells): rel L2 = {rel_coarse:.6e}, "
            f"gamma = {gamma_coarse:.6f}"
        )
        print(
            f"  fine   ({cells_fine:6d} cells): rel L2 = {rel_fine:.6e}, "
            f"gamma = {gamma_fine:.6f}"
        )
        print(f"  measured L2 rate in h: {rate:.4f} (expected ~1 for N1curl deg 1)")
        print(f"  fine-mesh error vs closed form: gamma {gamma_err:.3%}")
        print(f"  residual |Im E_y| / |Re E_y| on the probe line: {imag_ratio:.3e}")

    assert rel_fine < rel_coarse, (
        f"refinement did not reduce the field error: {rel_coarse:.4e} -> {rel_fine:.4e}"
    )
    assert rate > 0.9, (
        f"measured L2 convergence rate {rate:.3f} is below the O(h) expectation "
        "for N1curl degree 1 — the solve is not converging to the TE10 mode"
    )
    assert rel_fine < 0.05, (
        f"relative L2 error {rel_fine:.4e} against the analytic evanescent TE10 "
        "field exceeds the 5% MVP criterion (PROJECT_PLAN §10)"
    )
    assert gamma_err < 0.05, (
        f"measured decay constant {gamma_fine:.4f} Np/m differs from the closed "
        f"form {gamma_exact:.4f} Np/m by {gamma_err:.2%}"
    )
    # The k₀-blind control: dropping the mass term leaves γ = k_c exactly, which
    # is 66% above the true value here.  The measured γ must sit strictly below.
    assert gamma_fine < k_c, (
        f"measured gamma {gamma_fine:.4f} is not below the cutoff wavenumber "
        f"{k_c:.4f} — the k0^2*eps term is not reaching the operator"
    )
    # Lossless material and real boundary data give a real operator and a real
    # RHS, so the phasor carries no quadrature component: measured exactly 0.0
    # (log 20260731T123328Z_TH-7-gate-numbers.log).  A conjugated convention or
    # a stray Im(ε_c) shows up here before it shows up in γ.
    assert imag_ratio < 1e-10, (
        f"residual |Im E_y|/|Re E_y| = {imag_ratio:.3e} on a lossless, real-data "
        "solve — the phasor should be real to round-off"
    )


@complex_only
@pytest.mark.integration
def test_decay_tracks_frequency_and_the_resonance_guard_stays_quiet():
    """γ(f) tracks ``√(k_c² − k₀²)`` across the band, and no pole is implied.

    Three below-cutoff frequencies on one mesh.  Each measured γ is checked
    against its own closed form and the end-to-end ratio against the closed-form
    ratio, so this is not "the numbers differ" but "they differ by the amount the
    dispersion relation requires".  The stored energies then go through the
    `TH-1` step-5 guard, which must report *clear*: below cutoff the operator has
    no real eigenfrequency, so a triggered guard would mean the band is not what
    the geometry says it is.
    """
    comm = MPI.COMM_WORLD

    gammas_exact = [_analytic_gamma(f) for f in SWEEP_HZ]
    measured = [_solve_evanescent(16, f) for f in SWEEP_HZ]
    gammas = [m[1] for m in measured]
    energies = [m[3] for m in measured]

    errors = [abs(g - ge) / ge for g, ge in zip(gammas, gammas_exact)]
    ratio = gammas[0] / gammas[-1]
    ratio_exact = gammas_exact[0] / gammas_exact[-1]
    ratio_err = abs(ratio - ratio_exact) / ratio_exact

    report = check_energy_continuity(SWEEP_HZ, energies)

    if comm.rank == 0:
        print("\n[TH-7] frequency sweep below cutoff (16^3-equivalent mesh):")
        for f, g, ge, err, w in zip(SWEEP_HZ, gammas, gammas_exact, errors, energies):
            print(
                f"  f = {f:.4g} Hz: gamma = {g:.6f} vs {ge:.6f} Np/m ({err:.3%}), "
                f"W = {w:.6e} J"
            )
        print(
            f"  gamma ratio {ratio:.4f} vs closed form {ratio_exact:.4f} "
            f"({ratio_err:.3%})"
        )
        print(f"  {report.describe()}")

    for f, err in zip(SWEEP_HZ, errors):
        assert err < 0.05, f"decay constant at {f:.4g} Hz is off by {err:.2%}"
    assert ratio_err < 0.05, (
        f"the frequency response has the wrong magnitude: measured gamma ratio "
        f"{ratio:.3f} vs closed-form {ratio_exact:.3f} ({ratio_err:.2%})"
    )
    # The negative control a k₀-blind solver fails: it returns γ = k_c at every
    # frequency, i.e. a ratio of exactly 1.
    assert ratio > 2.0, (
        f"a 2.8x change in frequency moved the decay constant by only "
        f"{ratio:.3f}x — the solved field is not responding to k0"
    )
    assert not report.triggered, (
        f"the resonance guard fired below cutoff, where the operator has no real "
        f"pole: {report.describe()}"
    )
