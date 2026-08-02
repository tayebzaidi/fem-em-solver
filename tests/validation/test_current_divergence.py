"""`POST-3` step 3: the total-current divergence residual gate.

Outside an impressed source the total current is divergence free,

    ∇·J_tot = 0,    J_tot = (σ(x) + jωε₀εᵣ(x)) E

and :func:`~fem_em_solver.post.current_divergence.current_divergence_residual`
scores it as a dual norm over the degree-``p`` Lagrange space vanishing on the
wall, normalised by ``‖J_tot‖_{L²}``.  The derivation, the sign conventions and
the reason the identity is on the *total* current rather than on ``σE`` are in
that module's docstring.

What makes this a `POST-3` metric rather than another vacuous one is the
degree.  ``∇(CG1) ⊂ N1curl₁`` is inside the test space the solve already
enforced its equation against, so the CG1 residual is round-off by Galerkin
orthogonality no matter what the field is — it cannot fail.  ``∇(CG2)`` is not,
so the CG2 residual is an emergent property of the discrete solution.  The two
tests below are that pair: the CG2 residual converges under refinement at a
measured rate, and the CG1/CG2 contrast — 1.5e13× on this fixture — is the
negative control that shows the CG2 number is measuring something the solve
does not enforce.

(The control originally planned here, dropping σ from ``J_tot``, was measured
and does not work: it moves the relative residual by 1.07× and the absolute
dual norm *falls*, because ``‖J_tot‖`` falls with it.  At 64 MHz the conduction
and displacement currents are comparable and the O(h) N1curl interpolation
error dominates the σ interface jump.  See PROJECT_PLAN §7 `POST-3` step 3.)

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_current_divergence.py -v'
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
    build_material_fields,
)
from fem_em_solver.post.current_divergence import current_divergence_residual

from tests.complex_mode import complex_only
from tests.validation.test_lossy_plane_wave import _exact_factory
from tests.validation.test_poynting_balance import (
    EPSILON_R,
    FREQUENCY_HZ,
    MU_R,
    OMEGA,
    SIGMA_HIGH,
    SIGMA_LOW,
    TAG_HIGH,
    TAG_LOW,
    _two_material_mesh,
)

# The two meshes the step-3 probe measured (log
# 20260802T201000Z_POST-3-step3-probe2.log): 3072 and 10368 cells, ~65 s for
# the whole sweep at -n 2 including three residuals per mesh.  The gate takes
# two per mesh, so it sits inside the standard tier.
COARSE_N = 8
FINE_N = 12


def _solve_piecewise(n: int):
    """Solve the piecewise-σ box of `POST-3` step 2 and return field + σ(x), εᵣ(x).

    Boundary data is the σ_low plane wave, which is *not* the exact solution of
    the two-material problem — there is a reflection at the interface.  It does
    not need to be: the divergence identity has no free parameters, so it holds
    for whatever field the solve produces, and the fixture is boundary-driven so
    there is no volume source to put on the right-hand side.
    """
    msh, cell_tags = _two_material_mesh(n)
    background = HomogeneousMaterial(sigma=0.0, epsilon_r=EPSILON_R, mu_r=MU_R)
    material_map = {
        TAG_LOW: HomogeneousMaterial(
            sigma=SIGMA_LOW, epsilon_r=EPSILON_R, mu_r=MU_R
        ),
        TAG_HIGH: HomogeneousMaterial(
            sigma=SIGMA_HIGH, epsilon_r=EPSILON_R, mu_r=MU_R
        ),
    }
    exact_numpy, _ = _exact_factory(SIGMA_LOW)
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=background,
        material_map=material_map,
        cell_tags=cell_tags,
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=exact_numpy,
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()
    sigma_field, eps_field = build_material_fields(
        msh, background, cell_tags=cell_tags, material_map=material_map
    )
    return fields, sigma_field, eps_field


def _residual(solved, label: str, *, degree: int) -> dict:
    """Score the residual and echo it, so the harness log carries the numbers.

    The gate asserts bounds; the log has to show what was actually measured,
    which is what makes a later run able to tell a drift from a regression.
    """
    fields, sigma_field, eps_field = solved
    out = current_divergence_residual(
        fields.e_complex,
        omega=OMEGA,
        sigma=sigma_field,
        epsilon_r=eps_field,
        degree=degree,
        comm=MPI.COMM_WORLD,
    )
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[POST-3 step 3] {label:22s} CG{degree}  "
            f"rel = {out['relative_residual']:.6e}  "
            f"dual = {out['residual_dual_norm']:.4e}  "
            f"|J| = {out['current_scale']:.4e}  its = {out['ksp_iterations']}"
        )
    return out


@pytest.fixture(scope="module")
def coarse_solve():
    return _solve_piecewise(COARSE_N)


@pytest.fixture(scope="module")
def fine_solve():
    return _solve_piecewise(FINE_N)


@complex_only
@pytest.mark.integration
def test_cg2_residual_converges_under_refinement(coarse_solve, fine_solve):
    """The emergent residual falls with h at close to first order.

    Measured 2026-08-02 (probe log 20260802T201000Z_POST-3-step3-probe2.log):
    9.316e-2 at n = 8, 6.358e-2 at n = 12, rate 0.942 in h — first order, the
    same order as the step-1/2 Poynting leg, which is what a degree-1 N1curl
    solve gives.  The bounds below sit around those numbers with room for
    partitioner-dependent variation; a rate near 0 would mean the residual has
    hit a floor that refinement cannot remove, which is the failure this gate
    exists to catch.
    """
    coarse = _residual(coarse_solve, f"n = {COARSE_N}", degree=2)["relative_residual"]
    fine = _residual(fine_solve, f"n = {FINE_N}", degree=2)["relative_residual"]

    assert fine < coarse, (
        f"CG2 relative residual did not fall under refinement: "
        f"{coarse:.4e} at n = {COARSE_N} -> {fine:.4e} at n = {FINE_N}"
    )
    rate = float(np.log(coarse / fine) / np.log(FINE_N / COARSE_N))
    assert rate > 0.7, (
        f"CG2 residual convergence rate {rate:.4f} is below first order "
        f"(measured 0.942): {coarse:.4e} -> {fine:.4e}"
    )
    # Upper bound on the magnitude itself: the identity has to actually hold to
    # a few percent, not merely converge.  0.15 is ~1.6x the measured 9.3e-2.
    assert coarse < 0.15, (
        f"CG2 relative residual {coarse:.4e} at n = {COARSE_N} is too large for "
        "the total current to be called divergence free"
    )


@complex_only
@pytest.mark.integration
def test_cg1_residual_is_vacuous_and_cg2_is_not(coarse_solve):
    """The vacuity control: CG1 cannot fail, CG2 can.

    Same solve, same field, same integral — only the space the residual is
    tested against changes.  ``∇(CG1) ⊂ N1curl₁`` is inside the test space the
    curl-curl form was assembled against, so the CG1 residual is enforced
    identically by Galerkin orthogonality; ``∇(CG2)`` is not.  Measured
    2026-08-02: CG1 6.14e-15 against CG2 9.316e-2, a separation of 1.5e13.

    If this ever collapsed to O(1) the CG2 number would be reporting the same
    identity the solver already imposes, and the metric would be back in the
    vacuous class `POST-3` exists to remove.
    """
    cg1 = _residual(coarse_solve, "vacuity control", degree=1)["relative_residual"]
    cg2 = _residual(coarse_solve, "vacuity control", degree=2)["relative_residual"]

    assert cg1 < 1.0e-10, (
        f"CG1 relative residual {cg1:.4e} is above round-off; Galerkin "
        "orthogonality against the degree-1 N1curl test space should force it "
        "to ~1e-15, so either the residual assembly or the solve is wrong"
    )
    separation = cg2 / cg1
    assert separation > 1.0e6, (
        f"CG2/CG1 residual separation is only {separation:.3e} (measured 1.5e13): "
        "the CG2 residual is no longer measuring anything the solve does not "
        "already enforce"
    )


@complex_only
def test_degree_zero_is_rejected(coarse_solve):
    """A degree-0 test space has no gradient; refuse it rather than return 0."""
    fields, sigma_field, eps_field = coarse_solve
    with pytest.raises(ValueError, match="degree must be >= 1"):
        current_divergence_residual(
            fields.e_complex,
            omega=OMEGA,
            sigma=sigma_field,
            epsilon_r=eps_field,
            degree=0,
            comm=MPI.COMM_WORLD,
        )
