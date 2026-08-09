"""`TH-6` / `TH-1` step 4: plane wave in a lossy medium, against the closed form.

This is the first *physical* closed-form check on the complex curl-curl solve
(`TH-1` steps 1–3 were a manufactured source — right operator, no physics).
In the ``e^{+jωt}`` convention a plane wave travelling in ``+x`` and polarised
along ``z`` inside a homogeneous lossy medium is

    E(x) = ẑ · exp(−j k x),    k = k₀ √(ε_c),   ε_c = εᵣ − j σ/(ω ε₀)

with the branch of the square root that has ``Im k < 0`` (so the wave decays
forward rather than growing).  Writing ``k = β − j α``:

    |E_z(x)| = e^{−α x},    arg E_z(x) = −β x

and ``α = 1/δ`` reduces to the textbook skin depth ``δ = √(2/(ω μ σ))`` in the
good-conductor limit.  The general forms used here are

    α = k₀ √(εᵣ/2) · √(√(1 + t²) − 1),   β = k₀ √(εᵣ/2) · √(√(1 + t²) + 1)

with loss tangent ``t = σ/(ω ε₀ εᵣ)``.

``E`` above satisfies ``∇×∇×E = k² E`` exactly and ``k² = k₀² ε_c``, so it is an
exact **source-free** solution of the solved PDE.  The gate imposes it as
Dirichlet data on the whole boundary of a box (``dirichlet_e_field`` under the
PEC mode) and measures the *interior* decay and phase slopes, which the solver
is free to get wrong: nothing in the boundary data tells the interior how fast
to decay — that is `ε_c` acting through the mass term.  Drop the imaginary part
of ε_c and α collapses to 0; conjugate the convention and α changes sign.

`MAT-2` rides on the same machinery: two conductivities an order of magnitude
apart must produce interior decay constants that each match their own closed
form and differ from each other far beyond discretisation error.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_lossy_plane_wave.py -v'
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
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.constants import EPSILON_0, MU_0

from tests.complex_mode import complex_only

# Box side and drive frequency.  At 127.74 MHz in εᵣ = 78 the wavelength in the
# medium is ~0.23 m, so an L = 0.1 m box holds ~0.43 wavelengths (βL ≈ 2.7 rad,
# enough phase travel to fit a slope) and, at σ = 0.7 S/m, ~1.3 decay lengths
# (αL ≈ 1.3, an amplitude drop of ~3.7×, well above the discretisation floor
# but not so deep the far side is numerical noise).
BOX_L = 0.1
FREQUENCY_HZ = 127.74e6
SIGMA = 0.7
EPSILON_R = 78.0
MU_R = 1.0

# Sampling line for the interior fit: parallel to x at an off-lattice y/z so the
# probe points never land on a facet plane of the structured box mesh, and
# clipped away from the Dirichlet faces where the solution is pinned exactly.
LINE_YZ_FRACTION = 0.5137
FIT_X_MIN_FRACTION = 0.15
FIT_X_MAX_FRACTION = 0.85
N_PROBE = 41


def _wavenumber(sigma: float) -> complex:
    """k = k₀√(ε_c) on the decaying branch (Im k < 0) for e^{+jωt}."""
    omega = 2.0 * np.pi * FREQUENCY_HZ
    k0 = omega * np.sqrt(MU_0 * EPSILON_0)
    epsilon_c = EPSILON_R - 1j * sigma / (omega * EPSILON_0)
    k = k0 * np.sqrt(epsilon_c)
    # numpy's principal branch already returns Im < 0 for Im(ε_c) < 0; assert it
    # rather than trust it, because the whole gate hinges on this sign.
    assert k.imag < 0.0, f"non-decaying branch selected: k = {k}"
    return complex(k)


def _analytic_alpha_beta(sigma: float) -> tuple[float, float]:
    """Closed-form (α, β) from the loss tangent, independent of ``_wavenumber``.

    Deliberately a second, algebraically distinct derivation: if the branch
    choice in :func:`_wavenumber` were wrong the two would disagree.
    """
    omega = 2.0 * np.pi * FREQUENCY_HZ
    k0 = omega * np.sqrt(MU_0 * EPSILON_0)
    loss_tangent = sigma / (omega * EPSILON_0 * EPSILON_R)
    root = np.sqrt(1.0 + loss_tangent * loss_tangent)
    alpha = k0 * np.sqrt(EPSILON_R / 2.0) * np.sqrt(root - 1.0)
    beta = k0 * np.sqrt(EPSILON_R / 2.0) * np.sqrt(root + 1.0)
    return float(alpha), float(beta)


def _exact_factory(sigma: float):
    """Dirichlet/reference callables for the plane wave at this σ."""
    k = _wavenumber(sigma)

    def exact_numpy(x: np.ndarray) -> np.ndarray:
        phasor = np.exp(-1j * k * x[0])
        zeros = np.zeros_like(phasor)
        return np.array([zeros, zeros, phasor], dtype=PETSc.ScalarType)

    def exact_ufl(x):
        # exp(-j k x) with complex k, written out so UFL sees real arithmetic
        # in the exponent: e^{-α'x}(cos βx − j sin βx) with α' = −Im k > 0.
        decay = ufl.exp(k.imag * x[0])
        phase = -k.real * x[0]
        value = decay * (ufl.cos(phase) + 1j * ufl.sin(phase))
        return ufl.as_vector([0.0 * value, 0.0 * value, value])

    return exact_numpy, exact_ufl


def _probe_points() -> np.ndarray:
    xs = np.linspace(FIT_X_MIN_FRACTION * BOX_L, FIT_X_MAX_FRACTION * BOX_L, N_PROBE)
    yz = LINE_YZ_FRACTION * BOX_L
    return np.column_stack([xs, np.full_like(xs, yz), np.full_like(xs, yz)])


def _solve_plane_wave(n: int, sigma: float, degree: int = 1, return_fields: bool = False):
    """Solve the source-free lossy plane wave on an n³ box.

    Returns ``(rel_l2_error, alpha_fit, beta_fit, ncells)``, or the same tuple
    followed by ``(mesh, fields)`` when ``return_fields`` is set.  The extra
    return exists so `EX-4` can export the *gated* solve rather than a
    look-alike re-implementation of it (examples/time_harmonic/01_...); no
    assertion in this module depends on it.
    """
    comm = MPI.COMM_WORLD
    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([BOX_L, BOX_L, BOX_L])],
        [n, n, n],
        cell_type=dmesh.CellType.tetrahedron,
    )

    exact_numpy, exact_ufl = _exact_factory(sigma)
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=sigma, epsilon_r=EPSILON_R, mu_r=MU_R),
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=exact_numpy,
    )
    solver = TimeHarmonicSolver(problem, degree=degree)
    # No current: the plane wave is an exact source-free solution.
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
    # Point evaluation must go through the parallel helper (CLAUDE.md); the
    # real/imag DG split is recombined into the phasor here.
    real_values, valid_real = evaluate_vector_field_parallel(fields.e_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(fields.e_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(f"{int((~valid).sum())} probe points were not evaluated")

    ez = np.real(real_values[:, 2]) + 1j * np.real(imag_values[:, 2])
    xs = points[:, 0]

    # ln|E_z| = -α x  and  unwrapped arg E_z = -β x, both straight lines.
    alpha_fit = -float(np.polyfit(xs, np.log(np.abs(ez)), 1)[0])
    beta_fit = -float(np.polyfit(xs, np.unwrap(np.angle(ez)), 1)[0])

    ncells = comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM)
    if return_fields:
        return rel_error, alpha_fit, beta_fit, int(ncells), msh, fields
    return rel_error, alpha_fit, beta_fit, int(ncells)


@complex_only
@pytest.mark.integration
def test_lossy_plane_wave_matches_closed_form():
    """Interior decay and phase constants match ``k = k₀√(ε_c)`` to < 5%.

    The 5% is PROJECT_PLAN §10's MVP criterion, not a fitted tolerance.  The
    error is also required to fall under refinement, so a coincidental match at
    one mesh size cannot pass.
    """
    comm = MPI.COMM_WORLD
    alpha_exact, beta_exact = _analytic_alpha_beta(SIGMA)
    k = _wavenumber(SIGMA)
    skin_depth = 1.0 / alpha_exact

    # 12³ and 24³: at 16³ the L2 error is 5.41e-2, just above the 5% MVP bar
    # (measured, log 20260731T020308Z_TH-6-gate.log), while α and β were already
    # good to 0.23% / 0.13%. The mesh moves, not the tolerance.
    rel_coarse, alpha_coarse, beta_coarse, cells_coarse = _solve_plane_wave(12, SIGMA)
    rel_fine, alpha_fine, beta_fine, cells_fine = _solve_plane_wave(24, SIGMA)

    rate = float(np.log(rel_coarse / rel_fine) / np.log(2.0))
    alpha_err = abs(alpha_fine - alpha_exact) / alpha_exact
    beta_err = abs(beta_fine - beta_exact) / beta_exact

    if comm.rank == 0:
        print("\n[TH-6] lossy plane wave, sigma = %.3f S/m, eps_r = %.1f:" % (SIGMA, EPSILON_R))
        print(f"  closed form: k = {k:.6g}, alpha = {alpha_exact:.6f} Np/m, "
              f"beta = {beta_exact:.6f} rad/m, delta = {skin_depth:.6f} m")
        print(f"  coarse 12^3 ({cells_coarse:6d} cells): rel L2 = {rel_coarse:.6e}, "
              f"alpha = {alpha_coarse:.6f}, beta = {beta_coarse:.6f}")
        print(f"  fine   24^3 ({cells_fine:6d} cells): rel L2 = {rel_fine:.6e}, "
              f"alpha = {alpha_fine:.6f}, beta = {beta_fine:.6f}")
        print(f"  measured L2 rate in h: {rate:.4f} (expected ~1 for N1curl deg 1)")
        print(f"  fine-mesh error vs closed form: alpha {alpha_err:.3%}, beta {beta_err:.3%}")

    assert rel_fine < rel_coarse, (
        f"refinement did not reduce the field error: {rel_coarse:.4e} -> {rel_fine:.4e}"
    )
    assert rate > 0.9, (
        f"measured L2 convergence rate {rate:.3f} is below the O(h) expectation "
        "for N1curl degree 1 — the solve is not converging to the plane wave"
    )
    assert rel_fine < 0.05, (
        f"relative L2 error {rel_fine:.4e} against the analytic lossy plane wave "
        "exceeds the 5% MVP criterion (PROJECT_PLAN §10)"
    )
    assert alpha_err < 0.05, (
        f"measured decay constant {alpha_fine:.4f} Np/m differs from the closed "
        f"form {alpha_exact:.4f} Np/m by {alpha_err:.2%}; a lost Im(ε_c) drives "
        "this to zero"
    )
    assert beta_err < 0.05, (
        f"measured phase constant {beta_fine:.4f} rad/m differs from the closed "
        f"form {beta_exact:.4f} rad/m by {beta_err:.2%}"
    )
    assert alpha_fine > 0.0, (
        f"measured decay constant {alpha_fine:.4f} Np/m is not positive — the "
        "wave grows into the medium, i.e. the e^{+jωt} convention is conjugated"
    )


@complex_only
@pytest.mark.integration
def test_conductivity_measurably_changes_the_field():
    """`MAT-2`: σ changes the solved field, and changes it by the right amount.

    Two conductivities a factor of 14 apart are solved on the same mesh at the
    same frequency.  Each interior decay constant is checked against its own
    closed form, and the ratio between them is checked against the closed-form
    ratio — so this is not merely "the numbers differ", it is "they differ by
    the amount the physics requires".
    """
    comm = MPI.COMM_WORLD
    sigma_low, sigma_high = 0.1, 1.4

    alpha_low_exact, _ = _analytic_alpha_beta(sigma_low)
    alpha_high_exact, _ = _analytic_alpha_beta(sigma_high)

    _, alpha_low, _, _ = _solve_plane_wave(16, sigma_low)
    _, alpha_high, _, _ = _solve_plane_wave(16, sigma_high)

    err_low = abs(alpha_low - alpha_low_exact) / alpha_low_exact
    err_high = abs(alpha_high - alpha_high_exact) / alpha_high_exact
    ratio = alpha_high / alpha_low
    ratio_exact = alpha_high_exact / alpha_low_exact
    ratio_err = abs(ratio - ratio_exact) / ratio_exact

    if comm.rank == 0:
        print("\n[MAT-2] sigma sensitivity of the solved field (16^3):")
        print(f"  sigma = {sigma_low} S/m: alpha = {alpha_low:.6f} vs "
              f"{alpha_low_exact:.6f} Np/m ({err_low:.3%})")
        print(f"  sigma = {sigma_high} S/m: alpha = {alpha_high:.6f} vs "
              f"{alpha_high_exact:.6f} Np/m ({err_high:.3%})")
        print(f"  ratio {ratio:.4f} vs closed form {ratio_exact:.4f} ({ratio_err:.3%})")

    assert err_low < 0.05, f"low-sigma decay constant off by {err_low:.2%}"
    assert err_high < 0.05, f"high-sigma decay constant off by {err_high:.2%}"
    assert ratio_err < 0.05, (
        f"the σ-response has the wrong magnitude: measured α ratio {ratio:.3f} vs "
        f"closed-form {ratio_exact:.3f} ({ratio_err:.2%})"
    )
    # The negative control the proxy would have failed: a σ-independent solve
    # returns the same α twice.
    assert ratio > 2.0, (
        f"a 14x change in sigma moved the decay constant by only {ratio:.3f}x — "
        "the solved field is not responding to conductivity"
    )
