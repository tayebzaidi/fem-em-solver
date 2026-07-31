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

from dolfinx import fem, mesh as dmesh

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.core import build_material_fields
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


# `POST-3` step 2: the two conductivities `MAT-2` uses, but as one *piecewise*
# solve rather than two homogeneous ones — a slab interface at x = L/2, σ_low on
# the entry side and σ_high beyond it.  The interface lands on a mesh plane for
# every even n, so the DG0 σ field is exactly the geometry and the only error
# left is discretisation of the field.
SIGMA_LOW = 0.1
SIGMA_HIGH = 1.4
TAG_LOW = 1
TAG_HIGH = 2
# Mesh pair and bound, both set from measurement (log
# 20260731T183338Z_POST-3-step2-refine-probe.log): at 12³ → 24³ the imbalance is
# 11.85% → 5.98% at rate 0.987 in h, i.e. clean O(h) but 5.98% is just over the
# 5% MVP bar step 1 is held to.  Since the leg is O(h), the mesh moves rather
# than the bound: 32³ is predicted at 5.98% × 24/32 = 4.5%, and the pair below
# keeps the exact factor of 2 the rate needs.
PIECEWISE_N_COARSE = 16
PIECEWISE_N_FINE = 32
PIECEWISE_IMBALANCE_BOUND = 0.05


def _two_material_mesh(n: int):
    """n³ box tagged into two σ slabs split at x = L/2."""
    comm = MPI.COMM_WORLD
    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([BOX_L, BOX_L, BOX_L])],
        [n, n, n],
        cell_type=dmesh.CellType.tetrahedron,
    )
    tdim = msh.topology.dim
    low_cells = dmesh.locate_entities(msh, tdim, lambda x: x[0] <= 0.5 * BOX_L)
    high_cells = dmesh.locate_entities(msh, tdim, lambda x: x[0] >= 0.5 * BOX_L)
    # locate_entities is all-vertices-satisfy, so the two sets are disjoint and
    # together cover every cell when the split is a mesh plane; assert that
    # rather than trust it, since a cell left untagged would silently keep the
    # default material.
    n_cells_local = msh.topology.index_map(tdim).size_local
    tagged = np.concatenate([low_cells, high_cells])
    tagged = tagged[tagged < n_cells_local]
    assert tagged.size == n_cells_local, (
        f"{n_cells_local - tagged.size} owned cells fall on neither side of the "
        f"x = L/2 split at n = {n}: the interface is not a mesh plane"
    )

    indices = np.concatenate([low_cells, high_cells]).astype(np.int32)
    values = np.concatenate(
        [np.full(low_cells.size, TAG_LOW), np.full(high_cells.size, TAG_HIGH)]
    ).astype(np.int32)
    order = np.argsort(indices)
    cell_tags = dmesh.meshtags(msh, tdim, indices[order], values[order])
    return msh, cell_tags


def _solve_two_material_and_balance(n: int, *, sigma_material_scale: float = 1.0):
    """Solve the piecewise-σ box and score the balance against the solver's σ(x).

    ``sigma_material_scale`` multiplies the conductivities *given to the solver*
    only; the identity is always scored against the honest σ(x) field.  Setting
    it to 0 is the σ-blind negative control of step 1, now on the field path.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags = _two_material_mesh(n)

    honest_map = {
        TAG_LOW: HomogeneousMaterial(
            sigma=SIGMA_LOW, epsilon_r=EPSILON_R, mu_r=MU_R
        ),
        TAG_HIGH: HomogeneousMaterial(
            sigma=SIGMA_HIGH, epsilon_r=EPSILON_R, mu_r=MU_R
        ),
    }
    solve_map = {
        tag: HomogeneousMaterial(
            sigma=m.sigma * sigma_material_scale,
            epsilon_r=m.epsilon_r,
            mu_r=m.mu_r,
        )
        for tag, m in honest_map.items()
    }

    # Boundary data: the σ_low plane wave.  It is *not* the exact solution of
    # the two-material problem (there is a reflection at the interface), and it
    # does not need to be — the Poynting identity has no free parameters, so it
    # holds for whatever field the solve produces.
    exact_numpy, _ = _exact_factory(SIGMA_LOW)
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=EPSILON_R, mu_r=MU_R),
        material_map=solve_map,
        cell_tags=cell_tags,
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=exact_numpy,
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()

    # The σ(x) the identity is scored against, built independently of the solve
    # so the negative control can disagree with the solver on purpose.
    honest_sigma, _ = build_material_fields(
        msh,
        HomogeneousMaterial(sigma=0.0, epsilon_r=EPSILON_R, mu_r=MU_R),
        cell_tags=cell_tags,
        material_map=honest_map,
    )

    balance = poynting_power_balance(
        fields.e_complex,
        omega=OMEGA,
        sigma=honest_sigma,
        mu_r=MU_R,
        comm=comm,
    )
    balance["ncells"] = int(
        comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM)
    )
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


@complex_only
def test_uniform_sigma_field_reproduces_the_scalar_path():
    """Step 2 must not move the scalar path: a constant σ(x) gives the same numbers.

    No solve — an arbitrary interpolated field is enough, because the two calls
    differ only in how σ reaches the volume form.  This is the regression guard
    on generalising ``sigma``; agreement to round-off means the DG0 field enters
    the ``½∫σ|E|²dV`` term exactly where the float did.
    """
    comm = MPI.COMM_WORLD
    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([BOX_L, BOX_L, BOX_L])],
        [4, 4, 4],
        cell_type=dmesh.CellType.tetrahedron,
    )
    space = fem.functionspace(msh, ("N1curl", 1))
    e_field = fem.Function(space)
    # Something with a non-trivial curl and a non-trivial boundary trace, so
    # both legs of the identity are non-zero; it need not solve anything.
    e_field.interpolate(
        lambda x: np.array(
            [
                np.sin(3.0 * x[1] / BOX_L) + 0j,
                np.cos(2.0 * x[2] / BOX_L) + 0.5j * x[0] / BOX_L,
                np.exp(-x[0] / BOX_L) + 0j,
            ]
        )
    )

    sigma_field, _ = build_material_fields(
        msh, HomogeneousMaterial(sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=MU_R)
    )
    scalar = poynting_power_balance(
        e_field, omega=OMEGA, sigma=SIGMA, mu_r=MU_R, comm=comm
    )
    fielded = poynting_power_balance(
        e_field, omega=OMEGA, sigma=sigma_field, mu_r=MU_R, comm=comm
    )

    if comm.rank == 0:
        print("\n[POST-3] scalar vs uniform-field sigma path (4^3, no solve):")
        _report("scalar sigma", dict(scalar, ncells=0))
        _report("field  sigma", dict(fielded, ncells=0))

    assert scalar["dissipated_power_w"] > 0.0, "the test field dissipates nothing"
    for key in ("dissipated_power_w", "net_inward_power_w", "reactive_inward_power_var"):
        assert np.isclose(scalar[key], fielded[key], rtol=1e-12, atol=0.0), (
            f"{key} moved when sigma was passed as a uniform DG0 field: "
            f"{scalar[key]:.12e} vs {fielded[key]:.12e}"
        )


@complex_only
@pytest.mark.integration
def test_poynting_balance_holds_for_piecewise_sigma():
    """`POST-3` step 2: the identity survives a two-material solve.

    σ = 0.1 S/m for x < L/2 and 1.4 S/m beyond it — one solve, not `MAT-2`'s two
    homogeneous ones — with the volume leg now ``½∫σ(x)|E|²dV`` over the DG0
    field the solver built.  The rate is set by step 1's weakest link, the O(h)
    N1curl curl trace on the boundary; the interface adds a second O(h) source
    but does not change the order.
    """
    comm = MPI.COMM_WORLD

    coarse = _solve_two_material_and_balance(PIECEWISE_N_COARSE)
    fine = _solve_two_material_and_balance(PIECEWISE_N_FINE)
    rate = float(
        np.log(coarse["relative_imbalance"] / fine["relative_imbalance"])
        / np.log(2.0)
    )

    if comm.rank == 0:
        print(
            f"\n[POST-3] piecewise-sigma balance, sigma = {SIGMA_LOW}"
            f" | {SIGMA_HIGH} S/m across x = L/2, eps_r = {EPSILON_R}:"
        )
        _report(f"coarse {PIECEWISE_N_COARSE}^3", coarse)
        _report(f"fine   {PIECEWISE_N_FINE}^3", fine)
        print(f"  measured imbalance rate in h: {rate:.4f}")

    assert rate > 0.9, (
        f"measured imbalance rate {rate:.3f} is below the O(h) expectation the "
        "boundary curl trace sets — step 1 measured 0.987 on one material and "
        "the interface should not change the order"
    )
    assert coarse["dissipated_power_w"] > 0.0, (
        "no Ohmic dissipation from the piecewise sigma field — sigma(x) is not "
        "reaching the volume term"
    )
    assert fine["relative_imbalance"] < coarse["relative_imbalance"], (
        "power imbalance did not fall under refinement: "
        f"{coarse['relative_imbalance']:.4e} -> {fine['relative_imbalance']:.4e}"
    )
    assert fine["relative_imbalance"] < PIECEWISE_IMBALANCE_BOUND, (
        f"relative power imbalance {fine['relative_imbalance']:.4%} exceeds the "
        f"{PIECEWISE_IMBALANCE_BOUND:.1%} bound: the boundary Poynting flux and "
        "the volumetric Ohmic loss disagree about how much power this "
        "two-material solve absorbs"
    )
    assert fine["net_inward_power_w"] > 0.0, (
        f"net real power flows *out* of a passive lossy box "
        f"({fine['net_inward_power_w']:.4e} W)"
    )


@complex_only
@pytest.mark.integration
def test_piecewise_balance_fails_when_the_solve_ignores_sigma():
    """Negative control on the field path: σ-blind solve, honest σ(x) score.

    Both σ slabs are zeroed in the solver while the identity is still scored
    against the honest σ(x) DG0 field, so the solved field carries essentially
    no real power in while being credited with the full Ohmic loss.

    The separation factor is 5×, not step 1's 10×: the blind imbalance
    saturates just under 100% (it cannot exceed 1 — the two legs differ by at
    most the scale), so on a fixture whose honest imbalance is 11.85% at 12³
    the largest attainable ratio is 1/0.1185 = 8.4×.  Measured 8.4×
    (99.19% vs 11.85%, log 20260731T183316Z_POST-3-step2-probe.log); 10× is
    arithmetically unreachable here rather than merely unmet.
    """
    comm = MPI.COMM_WORLD

    honest = _solve_two_material_and_balance(12)
    blind = _solve_two_material_and_balance(12, sigma_material_scale=0.0)

    if comm.rank == 0:
        print("\n[POST-3] negative control, piecewise sigma (12^3):")
        _report("honest solve      ", honest)
        _report("sigma-blind solve ", blind)

    assert blind["relative_imbalance"] > 5.0 * honest["relative_imbalance"], (
        "a two-material solve run at sigma = 0 and scored against the honest "
        f"sigma(x) gave an imbalance of only {blind['relative_imbalance']:.4%} "
        f"against the honest solve's {honest['relative_imbalance']:.4%} — the "
        "field-sigma path is not sensitive to the physics it gates"
    )
    assert blind["relative_imbalance"] > 0.5, (
        "the sigma-blind control should absorb essentially none of the power it "
        f"is credited with; imbalance was {blind['relative_imbalance']:.4%}"
    )
