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
from fem_em_solver.core import build_material_fields, build_mu_r_field
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


# `POST-3` step 5: the same two-slab pattern, now on μᵣ.  σ is uniform and the
# permeability jumps at x = L/2 (μᵣ = 1 on the entry side, 2 beyond it), so the
# only thing that changed relative to step 2 is which coefficient is piecewise.
# μᵣ enters BOTH legs of the identity — the curl-curl operator through
# `bilinear_form` and H = ∇×E/(−jωμ₀μᵣ) in the boundary flux — and a version
# that fixed only one of the two could not fail for the right reason.
MU_ENTRY = 2.0
MU_FAR = 1.0
# Mesh pair and separation factors, all set from measurement (probe logs
# 20260805T003302Z / 20260805T003431Z_POST-3-step5-probe*.log).  Orientation
# matters and was measured, not assumed: with the magnetic slab on the *far*
# side the plane wave has already decayed where μᵣ ≠ 1, and the μᵣ-blind flux
# leg separated by only 1.141× — a control that cannot fail is no control.  On
# the entry side the honest imbalance is 11.44% (12³) → 5.76% (24³) at rate
# 0.9899 in h, so the 5% MVP bar (unmoved, step 1's) needs 32³: predicted
# 5.76% × 24/32 = 4.32%.  The 16³/32³ pair keeps the exact factor of 2 the
# rate measurement needs, exactly as step 2 did.
MU_N_COARSE = 16
MU_N_FINE = 32
MU_IMBALANCE_BOUND = 0.05
# Both controls measured at 12³ against the honest 11.44%: flux-blind 42.26%
# (3.693×), solve-blind 58.30% (5.096×), against an arithmetic ceiling of
# 1/0.1144 = 8.741× — the imbalance cannot exceed 1.  The asserted factors sit
# below the measurements with room, and far below the ceiling.
MU_FLUX_BLIND_FACTOR = 3.0
MU_SOLVE_BLIND_FACTOR = 4.0


def _solve_two_mu_and_balance(
    n: int,
    *,
    mu_r_for_flux: float | None = None,
    mu_material_blind: bool = False,
    mu_entry: float = MU_ENTRY,
    mu_far: float = MU_FAR,
):
    """Solve the piecewise-μᵣ box and score the balance against μᵣ(x).

    ``mu_r_for_flux`` overrides the permeability the *flux leg* is scored with
    while the solve keeps the honest μᵣ(x); passing 1.0 is the μᵣ-blind
    negative control (the H it computes is wrong by a factor of 2 over half the
    boundary-adjacent material).  Left at ``None`` the identity is scored with
    the very DG0 field the solver assembled its curl-curl term from.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags = _two_material_mesh(n)

    mu_map = {
        TAG_LOW: HomogeneousMaterial(
            sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=mu_entry
        ),
        TAG_HIGH: HomogeneousMaterial(
            sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=mu_far
        ),
    }
    solve_map = (
        {
            tag: HomogeneousMaterial(sigma=m.sigma, epsilon_r=m.epsilon_r, mu_r=1.0)
            for tag, m in mu_map.items()
        }
        if mu_material_blind
        else mu_map
    )

    # As in step 2 the Dirichlet data is a plane wave of the *entry-side*
    # material; it is not the exact solution of the two-material problem (the
    # μᵣ jump reflects), and the identity does not need it to be.
    exact_numpy, _ = _exact_factory(SIGMA)
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=1.0),
        material_map=solve_map,
        cell_tags=cell_tags,
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=exact_numpy,
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()
    assert fields.mu_r_field is not None, "solver did not expose the DG0 mu_r field"

    # The honest μᵣ(x), built independently of the solve so the operator-side
    # control can disagree with the solver on purpose (step 2's pattern).
    honest_mu = build_mu_r_field(
        msh,
        HomogeneousMaterial(sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=1.0),
        cell_tags=cell_tags,
        material_map=mu_map,
    )

    balance = poynting_power_balance(
        fields.e_complex,
        omega=OMEGA,
        sigma=fields.sigma_field,
        mu_r=honest_mu if mu_r_for_flux is None else mu_r_for_flux,
        comm=comm,
    )
    balance["ncells"] = int(
        comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM)
    )
    return balance


@complex_only
def test_uniform_mu_r_field_reproduces_the_scalar_path():
    """Step 5 must not move the scalar path: a constant μᵣ(x) gives the same numbers.

    No solve — the same arbitrary interpolated field the σ pin uses, because the
    two calls differ only in how μᵣ reaches the boundary flux leg.  Agreement to
    round-off means the DG0 field enters ``H = ∇×E/(−jωμ₀μᵣ)`` exactly where the
    float did.
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
    e_field.interpolate(
        lambda x: np.array(
            [
                np.sin(3.0 * x[1] / BOX_L) + 0j,
                np.cos(2.0 * x[2] / BOX_L) + 0.5j * x[0] / BOX_L,
                np.exp(-x[0] / BOX_L) + 0j,
            ]
        )
    )

    mu_field = build_mu_r_field(
        msh, HomogeneousMaterial(sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=1.0)
    )
    scalar = poynting_power_balance(
        e_field, omega=OMEGA, sigma=SIGMA, mu_r=1.0, comm=comm
    )
    fielded = poynting_power_balance(
        e_field, omega=OMEGA, sigma=SIGMA, mu_r=mu_field, comm=comm
    )

    if comm.rank == 0:
        print("\n[POST-3] scalar vs uniform-field mu_r path (4^3, no solve):")
        _report("scalar mu_r", dict(scalar, ncells=0))
        _report("field  mu_r", dict(fielded, ncells=0))

    assert abs(scalar["net_inward_power_w"]) > 0.0, "the test field carries no flux"
    for key in ("dissipated_power_w", "net_inward_power_w", "reactive_inward_power_var"):
        assert np.isclose(scalar[key], fielded[key], rtol=1e-12, atol=0.0), (
            f"{key} moved when mu_r was passed as a uniform DG0 field: "
            f"{scalar[key]:.12e} vs {fielded[key]:.12e}"
        )


@complex_only
@pytest.mark.integration
def test_poynting_balance_holds_for_piecewise_mu_r():
    """`POST-3` step 5: the identity survives a two-permeability solve.

    μᵣ = 2 for x < L/2 and 1 beyond it, σ uniform — the mirror image of step 2,
    with the piecewise coefficient moved from the volume term into the operator
    *and* the boundary flux.  The rate is still set by step 1's weakest link,
    the O(h) N1curl curl trace on the boundary; the μᵣ interface adds a second
    O(h) source without changing the order (0.9899 measured at 12³ → 24³).
    """
    comm = MPI.COMM_WORLD

    coarse = _solve_two_mu_and_balance(MU_N_COARSE)
    fine = _solve_two_mu_and_balance(MU_N_FINE)
    rate = float(
        np.log(coarse["relative_imbalance"] / fine["relative_imbalance"])
        / np.log(2.0)
    )

    if comm.rank == 0:
        print(
            f"\n[POST-3] piecewise-mu_r balance, mu_r = {MU_ENTRY} | {MU_FAR}"
            f" across x = L/2, sigma = {SIGMA} S/m, eps_r = {EPSILON_R}:"
        )
        _report(f"coarse {MU_N_COARSE}^3", coarse)
        _report(f"fine   {MU_N_FINE}^3", fine)
        print(f"  measured imbalance rate in h: {rate:.4f}")

    assert rate > 0.9, (
        f"measured imbalance rate {rate:.3f} is below the O(h) expectation the "
        "boundary curl trace sets — steps 1-2 measured 0.987/0.9915 and the "
        "mu_r interface should not change the order"
    )
    assert coarse["dissipated_power_w"] > 0.0, (
        "no Ohmic dissipation from the piecewise-mu_r solve"
    )
    assert fine["relative_imbalance"] < coarse["relative_imbalance"], (
        "power imbalance did not fall under refinement: "
        f"{coarse['relative_imbalance']:.4e} -> {fine['relative_imbalance']:.4e}"
    )
    assert fine["relative_imbalance"] < MU_IMBALANCE_BOUND, (
        f"relative power imbalance {fine['relative_imbalance']:.4%} exceeds the "
        f"{MU_IMBALANCE_BOUND:.1%} bound: the boundary Poynting flux and the "
        "volumetric Ohmic loss disagree about how much power this "
        "two-permeability solve absorbs"
    )
    assert fine["net_inward_power_w"] > 0.0, (
        f"net real power flows *out* of a passive lossy box "
        f"({fine['net_inward_power_w']:.4e} W)"
    )


@complex_only
@pytest.mark.integration
def test_piecewise_mu_r_balance_fails_when_a_leg_ignores_mu_r():
    """Negative control on both legs μᵣ enters — the vacuity trap of step 5.

    ``flux-blind`` keeps the honest two-μᵣ solve and scores the boundary flux
    with μᵣ = 1, i.e. the state of the code before this step; ``solve-blind``
    does the opposite, solving a uniform-μᵣ operator and scoring it with the
    honest μᵣ(x).  Both must break the identity, because a version that fixed
    only one of the two legs would be a metric that cannot fail for the right
    reason.  Factors are banded from the probe (3.693× / 5.096× measured
    against an 8.741× arithmetic ceiling — the imbalance saturates at 1).
    """
    comm = MPI.COMM_WORLD

    honest = _solve_two_mu_and_balance(12)
    flux_blind = _solve_two_mu_and_balance(12, mu_r_for_flux=1.0)
    solve_blind = _solve_two_mu_and_balance(12, mu_material_blind=True)

    if comm.rank == 0:
        print("\n[POST-3] negative controls, piecewise mu_r (12^3):")
        _report("honest solve     ", honest)
        _report("mu-blind flux leg", flux_blind)
        _report("mu-blind operator", solve_blind)
        for label, b in (("flux", flux_blind), ("solve", solve_blind)):
            print(
                f"  {label}-blind separation: "
                f"{b['relative_imbalance'] / honest['relative_imbalance']:.3f}x"
            )

    assert flux_blind["relative_imbalance"] > MU_FLUX_BLIND_FACTOR * honest[
        "relative_imbalance"
    ], (
        "scoring the honest two-mu_r solve with mu_r = 1 in the flux leg gave an "
        f"imbalance of only {flux_blind['relative_imbalance']:.4%} against the "
        f"honest {honest['relative_imbalance']:.4%} — H in the boundary integral "
        "is not seeing mu_r(x)"
    )
    assert solve_blind["relative_imbalance"] > MU_SOLVE_BLIND_FACTOR * honest[
        "relative_imbalance"
    ], (
        "a uniform-mu_r solve scored against the honest mu_r(x) gave an imbalance "
        f"of only {solve_blind['relative_imbalance']:.4%} against the honest "
        f"{honest['relative_imbalance']:.4%} — mu_r(x) is not reaching the "
        "curl-curl operator"
    )


# ---------------------------------------------------------------------------
# `POST-5` step 3: score the two legs of the identity *separately* against
# closed form, on the one fixture where each leg has one.
#
# Steps 1 and 2 excluded resolution, the `ds` orientation and the drive's
# compatibility as explanations for the smoke fixture's 116%/106% imbalance,
# leaving "the boundary leg itself is wrong" as the standing verdict — but
# that verdict was read off the *balance*, never off either leg alone.  The
# `TH-6` plane wave closes that gap: the exact solution is known, so both
#
#     P_flux  = -∮ ½Re(E×H̄)·n̂ dS      and      P_diss = ½∫σ|E|²dV
#
# have closed forms, and a wrong H reconstruction (a factor or a conjugation
# in `H = ∇×E/(−jωμᵣμ₀)`) or a wrong facet assembly shows up in P_flux's own
# error, with P_diss's error as the control that says the solve was fine.
#
# With E = ẑe^{−jkx}, k = β − jα, on the box [0,L]³ the Poynting vector is
# x-directed, so only the x = 0 and x = L faces carry flux:
#
#     P_flux_exact  = ½ β L² (1 − e^{−2αL}) / (ω μ₀ μᵣ)
#     P_diss_exact  = ½ σ L² (1 − e^{−2αL}) / (2α)
#
# and these are equal *identically*, because k² = k₀²ε_c gives 2αβ = ωμ₀σ.
# That algebraic coincidence is itself asserted below (no solve), so the two
# analytic references cannot drift together and hide a defect.
POST5_STEP3_LEG_BAND = 0.10


def _analytic_legs(sigma: float = SIGMA) -> dict[str, float]:
    """Closed-form values of both legs on the `TH-6` fixture, in W."""
    from tests.validation.test_lossy_plane_wave import _analytic_alpha_beta

    alpha, beta = _analytic_alpha_beta(sigma)
    from fem_em_solver.utils.constants import MU_0

    face = BOX_L * BOX_L
    depth = 1.0 - float(np.exp(-2.0 * alpha * BOX_L))
    return {
        "alpha": alpha,
        "beta": beta,
        "flux_w": 0.5 * beta * face * depth / (OMEGA * MU_0 * MU_R),
        "dissipated_w": 0.5 * sigma * face * depth / (2.0 * alpha),
    }


@complex_only
def test_the_two_closed_forms_agree_by_the_dispersion_relation():
    """`POST-5` step 3, self-check: the analytic reference is one number.

    ``2αβ = ωμ₀σ`` is the imaginary part of ``k² = k₀²ε_c``; it is what makes
    the analytic inward flux equal the analytic dissipation.  Asserting it
    here means the two closed forms below are not two spellings of the same
    algebra — if the branch or the loss tangent were wrong they would part.
    No solve, no mesh.
    """
    from fem_em_solver.utils.constants import MU_0

    legs = _analytic_legs()
    product = 2.0 * legs["alpha"] * legs["beta"]
    expected = OMEGA * MU_0 * SIGMA

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[POST-5 step 3] dispersion self-check: 2*alpha*beta = "
            f"{product:.12e}, omega*mu0*sigma = {expected:.12e}"
        )
        print(
            f"  analytic legs: flux = {legs['flux_w']:.6e} W, "
            f"dissipated = {legs['dissipated_w']:.6e} W"
        )

    assert np.isclose(product, expected, rtol=1e-12, atol=0.0), (
        f"2*alpha*beta = {product:.12e} but omega*mu0*sigma = {expected:.12e} — "
        "the closed-form alpha/beta do not satisfy the dispersion relation, so "
        "neither analytic leg can be trusted as a reference"
    )
    assert np.isclose(legs["flux_w"], legs["dissipated_w"], rtol=1e-12, atol=0.0), (
        f"analytic flux {legs['flux_w']:.6e} W and analytic dissipation "
        f"{legs['dissipated_w']:.6e} W disagree — the closed forms are wrong"
    )


@complex_only
@pytest.mark.integration
def test_each_leg_scored_against_its_own_closed_form():
    """`POST-5` step 3: is the boundary leg wrong, or is the smoke fixture?

    Pre-registered band (`POST5_STEP3_LEG_BAND` = 10%, set to the 5% MVP bar
    the whole identity already meets on this fixture with a factor of 2 of
    headroom because a single leg is not required to be better than the
    balance): on the fine 24³ rung,

    * boundary leg inside 10% of its closed form  ⇒  the assembly and the
      ``H = ∇×E/(−jωμᵣμ₀)`` reconstruction are **sound**, and the smoke
      fixture's 106% is a property of that fixture, not of this code;
    * boundary leg outside 10% while the volume leg is inside  ⇒  the
      boundary leg itself is defective and
      `test_poynting_balance_holds_and_converges` passes by cancellation.

    Either reading is the finding; nothing is fixed in this step.
    """
    comm = MPI.COMM_WORLD
    exact = _analytic_legs()

    coarse = _solve_and_balance(12, SIGMA)
    fine = _solve_and_balance(24, SIGMA)

    def _errs(b: dict) -> tuple[float, float]:
        return (
            abs(b["net_inward_power_w"] - exact["flux_w"]) / exact["flux_w"],
            abs(b["dissipated_power_w"] - exact["dissipated_w"])
            / exact["dissipated_w"],
        )

    flux_c, diss_c = _errs(coarse)
    flux_f, diss_f = _errs(fine)

    if comm.rank == 0:
        print("\n[POST-5 step 3] per-leg scoring on the TH-6 plane wave:")
        print(
            f"  analytic: flux = {exact['flux_w']:.6e} W, "
            f"dissipated = {exact['dissipated_w']:.6e} W "
            f"(alpha = {exact['alpha']:.4f} 1/m, beta = {exact['beta']:.4f} rad/m)"
        )
        for label, b, ef, ed in (
            ("coarse 12^3", coarse, flux_c, diss_c),
            ("fine   24^3", fine, flux_f, diss_f),
        ):
            print(
                f"  {label} ({b['ncells']:6d} cells): "
                f"flux = {b['net_inward_power_w']:.6e} W (err {ef:.4%}), "
                f"dissipated = {b['dissipated_power_w']:.6e} W (err {ed:.4%}), "
                f"imbalance = {b['relative_imbalance']:.4%}"
            )
        verdict = "CONDITIONING (leg sound)" if flux_f < POST5_STEP3_LEG_BAND else "ASSEMBLY"
        print(f"  step-3 verdict: {verdict}")

    assert diss_f < POST5_STEP3_LEG_BAND, (
        f"the *volume* leg misses its own closed form by {diss_f:.4%} on the "
        f"fine rung — the control failed, so the boundary-leg reading "
        f"({flux_f:.4%}) attributes nothing"
    )
    assert flux_f < POST5_STEP3_LEG_BAND, (
        f"the boundary leg -oint 1/2 Re(E x Hbar).n dS = "
        f"{fine['net_inward_power_w']:.6e} W misses its closed form "
        f"{exact['flux_w']:.6e} W by {flux_f:.4%}, outside the pre-registered "
        f"{POST5_STEP3_LEG_BAND:.0%} band, while the volume leg is inside at "
        f"{diss_f:.4%} — the boundary leg is defective in its own right and "
        "the 5% whole-identity gate on this fixture passes by cancellation"
    )
    assert fine["net_inward_power_w"] > 0.0, (
        "net real power flows out of a passive lossy box on the fine rung"
    )
