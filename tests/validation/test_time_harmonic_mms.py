"""`TH-1` steps 1–3 gate: manufactured solution for the complex curl-curl solve.

The operator being gated is

    ∇×(μᵣ⁻¹ ∇×E) − k₀² ε_c E = −jωμ₀ J,   ε_c = εᵣ − jσ/(ωε₀)

in the ``e^{+jωt}`` convention. The manufactured field

    E_ex = ( sin(k y), sin(k z), sin(k x) ),   k = π/L

satisfies ``∇×∇×E_ex = k² E_ex`` exactly, so the required source is
``−jωμ₀ J = (k²/μᵣ − k₀² ε_c) E_ex`` with **no** approximation — the only error
in the solve is discretisation error, which is what makes the convergence rate
a meaningful assertion rather than a tolerance fit.

Why this gate and not just "the field is finite": the source is built from the
same ``ε_c`` the solver assembles, so a wrong sign on the loss term, a missing
factor of ω in the load, or ``ufl.dot`` in place of ``ufl.inner`` all move the
solution away from ``E_ex`` and show up as a broken convergence rate. It also
pins step 3: the old ``E = −jωA`` proxy returned ``e_real ≡ 0`` by construction,
and here the exact answer has a large real part.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_time_harmonic_mms.py -v'
"""

from __future__ import annotations

import os

import numpy as np
import pytest
import ufl
from mpi4py import MPI
from petsc4py import PETSc

from dolfinx import fem, mesh as dmesh
from dolfinx.fem.petsc import assemble_matrix

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.core.time_harmonic import build_material_fields

IS_COMPLEX = np.issubdtype(np.dtype(PETSc.ScalarType), np.complexfloating)
REQUIRE_COMPLEX = os.environ.get("FEM_EM_REQUIRE_COMPLEX", "") == "1"

complex_only = pytest.mark.skipif(
    not IS_COMPLEX and not REQUIRE_COMPLEX,
    reason=f"TH-1 needs the complex build; this one is {np.dtype(PETSc.ScalarType)}",
)

# Box side, drive frequency and phantom-like material. At 127.74 MHz in
# εᵣ = 78, σ = 0.7 S/m saline the mass term k₀²|ε_c| ≈ 5.6e2 m⁻² is within an
# order of magnitude of the curl term at these mesh sizes, so the ε_c-dependent
# part of the operator is genuinely exercised (at, say, εᵣ = 1 it would be
# swamped by the curl-curl term and the gate would be blind to it).
BOX_L = 0.2
FREQUENCY_HZ = 127.74e6
SIGMA = 0.7
EPSILON_R = 78.0
MU_R = 1.0


def _material() -> HomogeneousMaterial:
    return HomogeneousMaterial(sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=MU_R)


def _exact_numpy(x: np.ndarray) -> np.ndarray:
    """E_ex sampled for interpolation (Dirichlet data / error reference)."""
    k = np.pi / BOX_L
    return np.array(
        [np.sin(k * x[1]), np.sin(k * x[2]), np.sin(k * x[0])],
        dtype=PETSc.ScalarType,
    )


def _exact_ufl(x):
    """The same field as a UFL expression of the spatial coordinate."""
    k = np.pi / BOX_L
    return ufl.as_vector([ufl.sin(k * x[1]), ufl.sin(k * x[2]), ufl.sin(k * x[0])])


def _manufactured_current(x):
    """J such that −jωμ₀J = (k²/μᵣ − k₀²ε_c) E_ex, i.e. E = E_ex solves the PDE."""
    from fem_em_solver.utils.constants import EPSILON_0, MU_0

    k = np.pi / BOX_L
    omega = 2.0 * np.pi * FREQUENCY_HZ
    k0_squared = omega * omega * MU_0 * EPSILON_0
    epsilon_c = EPSILON_R - 1j * SIGMA / (omega * EPSILON_0)
    rhs_scale = (k * k / MU_R) - k0_squared * epsilon_c
    return (rhs_scale / (-1j * omega * MU_0)) * _exact_ufl(x)


def _solve_mms(n: int, comm) -> tuple[float, float, float, float, int]:
    """Solve the manufactured problem on an n³ box.

    Returns ``(l2_error, l2_reference, real_part_error, imag_over_real, ncells)``.
    """
    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([BOX_L, BOX_L, BOX_L])],
        [n, n, n],
        cell_type=dmesh.CellType.tetrahedron,
    )

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=_material(),
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=_exact_numpy,
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    fields = solver.solve(current_density=_manufactured_current)

    e_h = fields.e_complex
    x = ufl.SpatialCoordinate(msh)
    exact = _exact_ufl(x)
    diff = e_h - exact

    # assemble_scalar is rank-local — reduce before taking a square root.
    err_sq = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(diff, diff) * ufl.dx)), op=MPI.SUM
    )
    ref_sq = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(exact, exact) * ufl.dx)), op=MPI.SUM
    )

    # Step-3 check on the DG split: the exact phasor is purely real here, so
    # e_real must carry the field and e_imag must be small. The retired
    # E = −jωA proxy had e_real ≡ 0 identically.
    real_local = float(np.max(np.abs(np.real(fields.e_real.x.array)))) if fields.e_real.x.array.size else 0.0
    imag_local = float(np.max(np.abs(np.real(fields.e_imag.x.array)))) if fields.e_imag.x.array.size else 0.0
    real_max = comm.allreduce(real_local, op=MPI.MAX)
    imag_max = comm.allreduce(imag_local, op=MPI.MAX)

    ncells = comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM)

    return (
        float(np.sqrt(abs(err_sq))),
        float(np.sqrt(abs(ref_sq))),
        real_max,
        imag_max / max(real_max, 1e-300),
        int(ncells),
    )


@complex_only
@pytest.mark.integration
def test_manufactured_solution_converges_at_first_order():
    """L2 error against the exact manufactured field halves under refinement.

    N1curl degree 1 is O(h) in L2, so the measured rate between an 8³ and a
    16³ box must be close to 1. A formulation error (wrong ε_c sign, missing
    ω in the load, `dot` for `inner`) does not converge to the exact field at
    all — the coarse and fine errors stay comparable and the rate collapses.
    """
    comm = MPI.COMM_WORLD

    err_coarse, ref_coarse, _, _, cells_coarse = _solve_mms(8, comm)
    err_fine, ref_fine, real_max, imag_ratio, cells_fine = _solve_mms(16, comm)

    rel_coarse = err_coarse / ref_coarse
    rel_fine = err_fine / ref_fine
    rate = float(np.log(err_coarse / err_fine) / np.log(2.0))

    if comm.rank == 0:
        print("\n[TH-1 steps 1-3] manufactured-solution convergence:")
        print(f"  coarse 8^3  ({cells_coarse:6d} cells): ||E_h-E_ex||/||E_ex|| = {rel_coarse:.6e}")
        print(f"  fine   16^3 ({cells_fine:6d} cells): ||E_h-E_ex||/||E_ex|| = {rel_fine:.6e}")
        print(f"  measured L2 rate in h: {rate:.4f} (expected ~1 for N1curl deg 1)")
        print(f"  max|Re E| = {real_max:.6e}, max|Im E| / max|Re E| = {imag_ratio:.3e}")

    assert rel_fine < 0.10, (
        f"fine-mesh relative L2 error {rel_fine:.4e} is too large for a "
        "manufactured solution the discretisation can represent"
    )
    assert rel_fine < rel_coarse, (
        f"refinement did not reduce the error: {rel_coarse:.4e} -> {rel_fine:.4e}"
    )
    assert rate > 0.9, (
        f"measured L2 convergence rate {rate:.3f} is below the O(h) expectation "
        "for N1curl degree 1 — the solve is not converging to E_ex"
    )

    # Step 3: the phasor split is real, not the proxy's e_real ≡ 0.
    assert real_max > 0.5, (
        f"max|Re E| = {real_max:.3e}; the manufactured field has amplitude 1, so "
        "a near-zero real part means the split (or the phase) is wrong"
    )
    assert imag_ratio < 0.15, (
        f"max|Im E|/max|Re E| = {imag_ratio:.3e}; the exact phasor is real here, "
        "so a large imaginary part means the load phase is wrong"
    )


@complex_only
@pytest.mark.integration
def test_operator_is_complex_symmetric():
    """Reciprocity: the assembled operator satisfies ``A = Aᵀ`` (not ``A = Aᴴ``).

    The curl-curl form is symmetric-but-not-Hermitian once σ > 0 — that is the
    structural signature of a lossy medium in the ``e^{+jωt}`` convention. If
    the imaginary part of ε_c were dropped (real build, or a lost sign) the
    matrix would come out Hermitian instead, which this test separates.
    """
    comm = MPI.COMM_WORLD
    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([BOX_L, BOX_L, BOX_L])],
        [4, 4, 4],
        cell_type=dmesh.CellType.tetrahedron,
    )
    problem = TimeHarmonicProblem(mesh=msh, frequency_hz=FREQUENCY_HZ, material=_material())
    solver = TimeHarmonicSolver(problem, degree=1)
    sigma_field, epsilon_r_field = build_material_fields(msh, _material())

    matrix = assemble_matrix(fem.form(solver.bilinear_form(sigma_field, epsilon_r_field)))
    matrix.assemble()

    frobenius = matrix.norm(PETSc.NormType.FROBENIUS)

    transpose = matrix.copy()
    transpose.transpose()
    sym_residual = transpose.copy()
    sym_residual.axpy(-1.0, matrix, structure=PETSc.Mat.Structure.DIFFERENT_NONZERO_PATTERN)
    sym_norm = sym_residual.norm(PETSc.NormType.FROBENIUS)

    hermitian = matrix.copy()
    hermitian.hermitianTranspose()
    herm_residual = hermitian.copy()
    herm_residual.axpy(-1.0, matrix, structure=PETSc.Mat.Structure.DIFFERENT_NONZERO_PATTERN)
    herm_norm = herm_residual.norm(PETSc.NormType.FROBENIUS)

    if comm.rank == 0:
        print("\n[TH-1 steps 1-3] operator structure:")
        print(f"  ||A||_F        = {frobenius:.6e}")
        print(f"  ||A - A^T||_F  = {sym_norm:.3e} (must vanish)")
        print(f"  ||A - A^H||_F  = {herm_norm:.3e} (must NOT vanish: sigma > 0)")

    assert frobenius > 0.0
    assert sym_norm < 1e-10 * frobenius, (
        f"operator is not complex-symmetric: ||A-A^T||_F = {sym_norm:.3e} vs "
        f"||A||_F = {frobenius:.3e}"
    )
    assert herm_norm > 1e-6 * frobenius, (
        f"operator is Hermitian (||A-A^H||_F = {herm_norm:.3e}), which means the "
        "loss term -j*sigma/(omega*eps0) was lost from the assembly"
    )
