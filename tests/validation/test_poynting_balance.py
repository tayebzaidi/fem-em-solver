"""`POST-3` step 1: Poynting power balance on the `TH-6` lossy plane wave.

The identity is

    −∮ ½ Re(E × H̄)·n̂ dS  =  ½ ∫ σ|E|² dV,    H = ∇×E / (−jωμ₀μᵣ)

(real power in through the boundary = Ohmic power dissipated inside), see
:mod:`fem_em_solver.post.power_balance` for the derivation and the sign
conventions.  This is what `POST-3` puts in place of ``e_to_b_mean_ratio``,
which is ``≈ ω|A|/|∇×A|`` by construction and cannot fail.

Both sides come from the same discrete ``E`` but through different operators —
a volume mass term against a boundary curl trace — so agreement is a statement
about the solve, and the two disagree wildly when the physics is wrong: the
σ = 0 negative control below scores an imbalance of order 1.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_poynting_balance.py -v'
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from dolfinx import mesh as dmesh

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.post.power_balance import poynting_power_balance

from tests.complex_mode import complex_only
from tests.validation.test_lossy_plane_wave import (
    BOX_L,
    EPSILON_R,
    FREQUENCY_HZ,
    MU_R,
    SIGMA,
    _exact_factory,
)

OMEGA = 2.0 * np.pi * FREQUENCY_HZ


def _solve_and_balance(
    n: int,
    sigma: float,
    *,
    sigma_material: float | None = None,
    sigma_for_balance: float | None = None,
):
    """Solve the `TH-6` plane wave on an n³ box and return its power balance.

    ``sigma`` sets the imposed Dirichlet plane wave.  ``sigma_material`` (the
    conductivity the solver is given) and ``sigma_for_balance`` (the one the
    identity is scored against) both default to it; splitting them apart is the
    negative control, which drives the solve at σ = 0 while still crediting it
    with the Ohmic loss of the σ it was supposed to model.
    """
    comm = MPI.COMM_WORLD
    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([BOX_L, BOX_L, BOX_L])],
        [n, n, n],
        cell_type=dmesh.CellType.tetrahedron,
    )
    exact_numpy, _ = _exact_factory(sigma)
    solve_sigma = sigma if sigma_material is None else sigma_material
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(
            sigma=solve_sigma, epsilon_r=EPSILON_R, mu_r=MU_R
        ),
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=exact_numpy,
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()

    balance = poynting_power_balance(
        fields.e_complex,
        omega=OMEGA,
        sigma=sigma if sigma_for_balance is None else sigma_for_balance,
        mu_r=MU_R,
        comm=comm,
    )
    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    balance["ncells"] = int(ncells)
    return balance


def _report(label: str, b: dict) -> None:
    print(
        f"  {label} ({b['ncells']:6d} cells): "
        f"dissipated = {b['dissipated_power_w']:.6e} W, "
        f"net inward = {b['net_inward_power_w']:.6e} W, "
        f"reactive = {b['reactive_inward_power_var']:.6e} var, "
        f"imbalance = {b['relative_imbalance']:.4%}"
    )


@complex_only
@pytest.mark.integration
def test_poynting_balance_holds_and_converges():
    """Real power in = Ohmic power dissipated, to < 5%, and shrinking with h."""
    comm = MPI.COMM_WORLD

    coarse = _solve_and_balance(12, SIGMA)
    fine = _solve_and_balance(24, SIGMA)
    rate = float(
        np.log(coarse["relative_imbalance"] / fine["relative_imbalance"])
        / np.log(2.0)
    )

    if comm.rank == 0:
        print(
            f"\n[POST-3] Poynting balance, sigma = {SIGMA} S/m, "
            f"eps_r = {EPSILON_R}, f = {FREQUENCY_HZ:.4g} Hz:"
        )
        _report("coarse 12^3", coarse)
        _report("fine   24^3", fine)
        print(f"  measured imbalance rate in h: {rate:.4f}")

    assert coarse["dissipated_power_w"] > 0.0, (
        "no Ohmic dissipation at sigma = %.3f S/m — the sigma mass term is "
        "not reaching the solved field" % SIGMA
    )
    assert fine["relative_imbalance"] < coarse["relative_imbalance"], (
        "power imbalance did not fall under refinement: "
        f"{coarse['relative_imbalance']:.4e} -> {fine['relative_imbalance']:.4e}"
    )
    # 5% is PROJECT_PLAN §10's MVP bar, the same one `TH-6` is held to on the
    # very same fixture — not a bound fitted to the measured imbalance.
    assert fine["relative_imbalance"] < 0.05, (
        f"relative power imbalance {fine['relative_imbalance']:.4%} exceeds the "
        "5% MVP criterion: the boundary Poynting flux and the volumetric Ohmic "
        "loss disagree about how much power this solve is absorbing"
    )
    assert fine["net_inward_power_w"] > 0.0, (
        f"net real power flows *out* of a passive lossy box "
        f"({fine['net_inward_power_w']:.4e} W) — the e^{{+jωt}} convention is "
        "conjugated somewhere between Faraday's law and the flux integral"
    )


@complex_only
@pytest.mark.integration
def test_poynting_balance_fails_when_the_solve_ignores_sigma():
    """Negative control: the identity must break for a σ-blind solve.

    Same boundary data, same mesh, same frequency — only the σ inside the
    solver is zeroed, which is what dropping ``Im ε_c`` does.  The solved field
    then carries essentially no net real power into the box while the σ it was
    supposed to model says it should absorb ~1.2e−4 W.  The old
    ``e_to_b_mean_ratio`` is finite and unremarkable in both cases.
    """
    comm = MPI.COMM_WORLD

    honest = _solve_and_balance(12, SIGMA)
    blind = _solve_and_balance(12, SIGMA, sigma_material=0.0, sigma_for_balance=SIGMA)

    if comm.rank == 0:
        print("\n[POST-3] negative control (sigma-blind solve, 12^3):")
        _report("honest solve      ", honest)
        _report("sigma-blind solve ", blind)

    assert blind["relative_imbalance"] > 10.0 * honest["relative_imbalance"], (
        "a solve run at sigma = 0 and scored against sigma = 0.7 S/m produced "
        f"an imbalance of only {blind['relative_imbalance']:.4%} against the "
        f"honest solve's {honest['relative_imbalance']:.4%} — the metric is not "
        "sensitive to the physics it is supposed to gate"
    )
    assert blind["relative_imbalance"] > 0.5, (
        "the sigma-blind control should absorb essentially none of the power it "
        f"is credited with; imbalance was {blind['relative_imbalance']:.4%}"
    )
