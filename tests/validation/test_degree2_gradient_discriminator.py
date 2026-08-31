"""`TH-13` steps 1 / 1′: does *any* ``W_m ≫ W_e`` fixture display the degree-2
``W_e`` explosion, or only the coil's feed model?

Commissioned by the 2026-08-23 weekly review (PROJECT_PLAN §7 `TH-13`) from the
confound `TH-12` step 3 named against itself.  Step 3 read the explosion as
**COIL-SPECIFIC** — the smoke fixture's incompatible axial drive moves
``W_e/W_m`` by 1.155× across element order and the sphere's imposed field by
1.015×, against the coil's 3.426e+07× — but the three fixtures do not share a
baseline: ``W_e/W_m`` is 2.16 on the smoke box, 1.07 on the sphere and 6.7e-6 on
the coil.  A gradient contamination of fixed *absolute* size therefore moves the
coil's ratio ~1e6× more than either cheap fixture's, whatever injected it.  So
step 3 excluded "``J·n ≠ 0`` is sufficient" but could not separate

* **FEED** — the coil's feed model injects gradient content; from
* **CLASS** — only a fixture with ``W_m ≫ W_e`` can *display* a contamination
  that is present everywhere, and the defect is the ungauged second-order
  gradient space itself.

The discriminator this module runs is the missing cell of that table: a fixture
that is **magnetically dominated** *and* has a **compatible drive**.  It is the
smoke box's own cylindrical mesh, driven by `POST-5` step 2's closed azimuthal
loop (``J = (-y, x, 0)/a`` restricted to the rod: ``div J = 0`` pointwise and
``J·n = 0`` on every boundary, so there is no incompatible part for the gradient
subspace to absorb), driven at **two frequencies on one mesh**.

**Step 1 ran at 10 MHz and missed its own precondition** (2026-08-30): the
fixture read degree-1 ``W_e/W_m`` = 1.952350e-02 against the ≤ 1e-2 band, so it
is not magnetically dominated and is not the missing cell.  Worse, and this is
what step 1′ fixes: from a 1.95e-2 baseline a 1e3× CLASS move would have to
reach ``W_e/W_m`` ≈ 20, well past the O(1) equipartition every fixture in the
family sits at — CLASS was arithmetically unreachable before the run began, so
the bands and the fixture were never compatible.

**Step 1′ rescoped by ω²** (2026-08-30 weekly review, §7): at fixed impressed
current ``W_e/W_m ~ ω²``, so the *same* fixture at **1 MHz** was predicted to
read ≈ 1.95e-4 — inside the unchanged band by 50×, with ~5e3× of headroom under
equipartition, which would make both verdict bands representable for the first
time.  **Measured, it does not** (`20260830T200305Z_TH-13-step1prime.log`): the
1 MHz row reads **1.926692e-02**, 98.7× the prediction and 1.3% *below* the
10 MHz row across a full decade of ω.  ``W_e``, ``W_m`` and the dissipated power
are all frequency-independent on this fixture, so the quasi-static ``E ~ ωA``
argument does not describe this solve and **frequency is not the knob that makes
the fixture magnetically dominated**.  The precondition therefore still fails,
and per §7 the step stops on that finding with the assertion left red rather
than loosened — the red moves from the 10 MHz row to the 1 MHz one, it does not
multiply.

The 10 MHz row stays in the table as a **recorded** reading: its precondition is
no longer asserted (1.95e-2 against 1e-2 is a known number and re-asserting it
gates nothing), but its degree-1 ratio and its in-between 5.156e+01× move are
asserted as the rescope's negative control — both reproduced to rtol 1e-3.

**Pre-registered, before the run** (PROJECT_PLAN §7 `TH-13` steps 1 / 1′,
restated in :data:`MAGNETIC_DOMINANCE_MAX` / :data:`CLASS_RATIO_FACTOR` /
:data:`FEED_RATIO_FACTOR` / :data:`OMEGA_SQUARED_PREDICTED_RATIO`):

* **Precondition, asserted at 1 MHz** — the fixture must first *be* magnetically
  dominated: degree-1 ``W_e/W_m ≤ 1e-2``, the band unmoved from step 1.  If it
  is not, the fixture is wrong, the reading below means nothing, and §7 says the
  step stops with that as its finding rather than reinterpreting the ratio.
* **The ω² prediction, printed not asserted** — 1.95e-4, measured 1.9267e-2.
  Pre-registered as an assertion; demoted to a printed record *after* the
  measurement refuted it, with the numbers in-comment at
  :data:`OMEGA_SQUARED_PREDICTED_RATIO`, because a second red on the same dead
  premise gates nothing the precondition does not.
* **Verdict** — the cross-order move in ``W_e/W_m`` on the 1 MHz row:
  ``≥ 1e3×`` ⇒ **CLASS**, ``≤ 10×`` ⇒ **FEED**.  In between is the finding,
  recorded, with no band invented around it.  A degree-2 ``W_e/W_m ≈ 1`` here,
  as at 10 MHz, would mean the contamination *saturates* at equipartition and
  "cross-order move" is the wrong discriminant — itself the finding, and step
  2's cue.

**Negative controls** (§7): `TH-12` step 3's own two fixtures, run here on the
same code path and through the same imported helpers, must reproduce their
recorded moves — smoke 1.155×, sphere 1.015× — so a CLASS reading is a property
of the new fixture and not of a code change since 2026-08-19; and the 10 MHz
loop row must reproduce step 1's own two numbers at rtol 1e-3.  The `POST-5`
dissipated-power anchor (1.199162e-06 W at rtol 1e-6 on 1 405 cells) rides along
with the smoke column, as it does in step 3.

**Energy forms are imported, never restated** (§7 trap):
:func:`fem_em_solver.core.resonance.stored_electric_energy` and
``test_coil_loading_larmor_probe._stored_magnetic_energy`` — the two forms
`TH-12` step 2 measured the coil with, reached here through step 3's own
``_solve_smoke_at_degree`` / ``_energies_of_sphere_row`` so that all four
fixtures are literally the same quantity measured four times.  ``ufl.inner``
conjugates its second argument; a hand-rolled ``W_e`` would flip the convention.

Scope: mechanism attribution only.  No coil solve runs here (the coil at degree
2 is 61.94 GiB), no coil number moves, the two degree-2 coil identity tests stay
failing, the known-issues degree-2 entry stays open, and §10's production-order
decision stays the weekly review's with this verdict on record.  Step 2 (the
absolute gradient content of ``E``) is scoped from this verdict, not run here.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_degree2_gradient_discriminator.py -v -s'
"""

from __future__ import annotations

import dolfinx
import numpy as np
import pytest
import ufl
from dolfinx import fem
from dolfinx.fem.petsc import LinearProblem
from mpi4py import MPI
from petsc4py import PETSc

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.core.resonance import stored_electric_energy
from fem_em_solver.core.time_harmonic import TimeHarmonicBoundaryCondition
from fem_em_solver.utils.constants import EPSILON_0, MU_0

from tests.complex_mode import complex_only
from tests.solver.test_time_harmonic_smoke import (
    AXIAL_RECORD_DISSIPATED_W,
    EPSILON_R,
    SIGMA,
    _azimuthal_current,
    _smoke_mesh,
)
from tests.validation.test_coil_loading_larmor_probe import _stored_magnetic_energy
from tests.validation.test_degree2_energy_mechanism import (
    COIL_W_E_W_M_DEGREE1,
    COIL_W_E_W_M_DEGREE2,
    RECORD_REPRODUCTION_RTOL,
    SMOKE_RESOLUTION,
    _energies_of_sphere_row,
    _ratio_move,
    _solve_smoke_at_degree,
)
from tests.validation.test_lossy_sphere_degree2 import (
    POWER_IMAGINARY_BOUND,
    _run_at_degree,
)

# ---------------------------------------------------------------------------
# The pre-registered bands (PROJECT_PLAN §7 `TH-13` step 1).
# ---------------------------------------------------------------------------
# The precondition: the fixture must be magnetically dominated at degree 1, or
# it is not the missing cell of `TH-12` step 3's table at all.
MAGNETIC_DOMINANCE_MAX = 1.0e-2
# The verdict bands, the same two factors step 3 pre-registered so the two
# readings are commensurable.
CLASS_RATIO_FACTOR = 1.0e3
FEED_RATIO_FACTOR = 10.0

# The loop fixture's frequency.  With an impressed current held fixed, a
# quasi-static solve has ``B`` frequency-independent and ``E ~ ωA``, so
# ``W_e/W_m ~ ω²``; the frequency is therefore the one knob that moves this
# fixture's baseline without touching mesh, material, drive or forms.
#
# Step 1 ran at the coil's own 10 MHz and missed the precondition: it read
# ``W_e/W_m`` = 1.952350e-02 at degree 1 against the ≤ 1e-2 band, and — the
# defect in the step as written — from that baseline a 1e3× CLASS move would
# have had to reach ``W_e/W_m`` ≈ 20, far past the O(1) equipartition every
# fixture in the family sits at, so CLASS was arithmetically unreachable before
# the run began.  Step 1′ rescopes by ω²: at 1 MHz the same fixture is predicted
# to read ≈ 1.95e-4, inside the *unchanged* band by 50×, with ~5e3× of headroom
# under equipartition, so both verdict bands are representable for the first
# time.  Everything else about the box (material, mesh, tags, drive) is the
# smoke fixture's, imported.
LOOP_FREQUENCY_HZ = 1.0e6
# The step-1 frequency, kept as a *recorded* row rather than a gate: the 10 MHz
# fixture is now known not to be magnetically dominated, so asserting its
# precondition again gates nothing.  What it does still do is anchor the run
# against step 1's own reading on the same code path.
LOOP_RECORD_FREQUENCY_HZ = 10.0e6
LOOP_FREQUENCIES_HZ = (LOOP_FREQUENCY_HZ, LOOP_RECORD_FREQUENCY_HZ)

# `TH-13` step 1's recorded readings at 10 MHz
# (`20260830T020301Z_TH-13-step1.log`, PROJECT_PLAN §7): the degree-1 ratio that
# failed the precondition, and the in-between cross-order move.  Both are
# reproduced here as the negative control for the rescope — a moved 10 MHz
# column means this run is not comparable with step 1's.
STEP1_RECORD_DEGREE1_RATIO = 1.952350e-02
STEP1_RECORD_MOVE = 5.156e01
STEP1_RECORD_RTOL = 1.0e-3

# The ω² prediction for the 1 MHz row, pre-registered in §7 before the run:
# 1.952350e-02 × (1/10)² ≈ 1.95e-4, to be asserted within a factor of two.
#
# MEASURED 2026-08-30 (`20260830T200305Z_TH-13-step1prime.log`), REFUTED:
# the 1 MHz row reads W_e/W_m = **1.926692e-02** at degree 1 — 98.7× the
# prediction, and only 1.3% below the 10 MHz row's 1.952350e-02 across a full
# decade of ω.  On this fixture ``W_e/W_m`` is frequency-INDEPENDENT: W_e moves
# 5.621559e-19 → 5.544787e-19 J and W_m 2.879380e-17 → 2.877879e-17 J, i.e.
# both `E` and `H` are unchanged by the frequency, so the quasi-static
# ``E ~ ωA`` argument the rescope rests on does not describe this solve.  The
# prediction is therefore kept as a *printed* record rather than an assertion:
# re-asserting a premise that measurement has killed would only duplicate the
# precondition red below, and per §7 no band is invented around a negative.
# The factor stays defined for the print and for whoever scopes step 2.
OMEGA_SQUARED_PREDICTED_RATIO = STEP1_RECORD_DEGREE1_RATIO * (
    LOOP_FREQUENCY_HZ / LOOP_RECORD_FREQUENCY_HZ
) ** 2
OMEGA_SQUARED_PREDICTION_FACTOR = 2.0

# `TH-12` step 3's recorded cross-order moves
# (`20260819T183425Z_TH-12-step3-warm.log`, PROJECT_PLAN §7): the negative
# control this step needs, so a CLASS reading below is the new fixture's and not
# a code change.  Reproduced at step 3's own imported `EX-25` 1% band —
# `RECORD_REPRODUCTION_RTOL` — rather than a tighter one invented here.
SMOKE_MOVE_RECORD = 1.155
SPHERE_MOVE_RECORD = 1.015

# ---------------------------------------------------------------------------
# `TH-13` step 2: the gradient-projection identity (PROJECT_PLAN §7, rescoped
# 2026-08-30 18:00 review).  Pre-registered before the run.
# ---------------------------------------------------------------------------
# (A) the discriminant: ‖∇χ − c∇φ‖/‖∇χ‖ at both degrees and both frequencies.
# Both potentials come out of direct MUMPS solves of the *same* Laplace matrix
# with proportional right-hand sides IF the discrete gradient equation holds,
# so the expected reading is round-off (~1e-10) and 1e-6 is a generous bar.
GRADIENT_IDENTITY_MAX = 1.0e-6
# The load-bearing probe (`PORT-12` step 2 precedent), asserted rather than
# run-and-reverted so it stays load-bearing: mistuning `c` by 10% must move the
# residual to ≈ 0.1.  Exactly 0.1 when (A) holds to round-off, so the bar sits
# just under it — the control fails loudly if the residual is insensitive to
# `c`, which is what a vacuous (A) would look like.
MISTUNED_C_FACTOR = 1.1
MISTUNED_C_MIN = 9.0e-2


def _complex_ohmic_power(e_complex, sigma: float, comm) -> complex:
    """``½σ∫ E·conj(E) dV`` over the whole box, kept complex.

    ``ufl.inner`` conjugates its second argument, so the imaginary part is
    round-off rather than a truncated quantity; ``|Im P|/Re P`` is therefore a
    consistency read on the solve at each order, the same one
    `TH-12` step 1 gates the sphere with (:data:`POWER_IMAGINARY_BOUND`).
    ``assemble_scalar`` is rank-local — reduced here before the caller sees it.
    """
    local = fem.assemble_scalar(
        fem.form(0.5 * sigma * ufl.inner(e_complex, e_complex) * ufl.dx)
    )
    return complex(comm.allreduce(local, op=MPI.SUM))


def _subdomain_indicator(mesh, cell_tags, tag: int):
    """The DG0 indicator of one cell tag — the same one the projection builds.

    Needed for the unprojected negative control: with ``project_source=False``
    the load integrates ``J`` over the tagged measure only, so the field whose
    gradient content is being read is ``χ_tag J``, not the whole-domain ``J``.
    """
    dg0 = fem.functionspace(mesh, ("DG", 0))
    indicator = fem.Function(dg0, name="source_indicator")
    indicator.x.array[:] = 0.0
    indicator.x.array[cell_tags.find(int(tag))] = 1.0
    indicator.x.scatter_forward()
    return indicator


def _l2_norm(expression, comm) -> float:
    """``(∫ expr·conj(expr) dx)^{1/2}`` over the whole domain, reduced.

    ``ufl.inner`` conjugates its second argument, so this is the modulus norm
    for a complex field and the ordinary L² norm for a real one — the same
    convention on both sides of every ratio below.  ``assemble_scalar`` is
    rank-local (§7 trap): the reduction happens here, once.
    """
    local = fem.assemble_scalar(
        fem.form(ufl.inner(expression, expression) * ufl.dx)
    )
    return float(np.sqrt(abs(complex(comm.allreduce(local, op=MPI.SUM)))))


def _gradient_potential(mesh, degree: int, source, comm, *, dirichlet_h10: bool):
    """``χ ∈ Lagrange_degree`` with ``(∇χ, ∇q) = (source, ∇q) ∀ q``.

    ``∇χ`` is the L²-projection of ``source`` onto ``∇Lagrange_degree`` — the
    subspace the N1curl test space of the *same* degree contains, which is the
    whole point: `core/source_projection.py` removes gradient content against
    ``("Lagrange", 1) ∩ H¹₀`` at every solve degree and under every boundary
    mode, so a degree-2 solve and a PMC box each test directions the projection
    never touched.

    The Dirichlet set is the one the N1curl boundary mode implies, read off
    :meth:`TimeHarmonicSolver.build_boundary_conditions` by the caller rather
    than assumed: PEC pins the tangential trace, so only ``q ∈ H¹₀`` has an
    admissible ``∇q``; ``NATURAL`` (PMC) constrains nothing and *every*
    ``q ∈ Lagrange`` is admissible.  In the PMC case the Laplacian is singular
    on constants, so a single dof is pinned — that fixes the additive constant
    without touching ``∇χ``, and both potentials of a pair are pinned at the
    same dof so their difference is exact.
    """
    q_space = fem.functionspace(mesh, ("Lagrange", degree))
    u = ufl.TrialFunction(q_space)
    q = ufl.TestFunction(q_space)

    if dirichlet_h10:
        tdim = mesh.topology.dim
        mesh.topology.create_connectivity(tdim - 1, tdim)
        facets = dolfinx.mesh.exterior_facet_indices(mesh.topology)
        zero = fem.Function(q_space)
        zero.x.array[:] = 0.0
        bcs = [
            fem.dirichletbc(
                zero, fem.locate_dofs_topological(q_space, tdim - 1, facets)
            )
        ]
    else:
        pin = (
            np.array([0], dtype=np.int32)
            if comm.rank == 0
            else np.zeros(0, dtype=np.int32)
        )
        bcs = [fem.dirichletbc(PETSc.ScalarType(0), pin, q_space)]

    problem = LinearProblem(
        ufl.inner(ufl.grad(u), ufl.grad(q)) * ufl.dx,
        ufl.inner(source, ufl.grad(q)) * ufl.dx,
        bcs=bcs,
        petsc_options={
            "ksp_type": "preonly",
            "pc_type": "lu",
            "pc_factor_mat_solver_type": "mumps",
        },
        petsc_options_prefix="fem_em_th13_step2_",
    )
    chi = problem.solve()
    chi.x.scatter_forward()
    return chi


def _form_constant(frequency_hz: float) -> complex:
    """``c = −load_factor / (k₀² ε_c)``, read off the form, not off theory.

    Testing the assembled weak form with ``v = ∇ψ`` kills the curl term
    (``∇×∇ψ = 0``) and leaves ``−k₀²ε_c (E_h, ∇ψ) = load_factor (J′, ∇ψ)``,
    i.e. ``(E_h, ∇ψ) = c (J′, ∇ψ)`` for every admissible ``ψ``.  The three
    ingredients are exactly the solver's own — ``load_factor = −jωμ₀``
    (`time_harmonic.py:448`), ``k₀² = ω²μ₀ε₀`` and
    ``ε_c = ε_r − jσ/(ωε₀)`` (`:582–583`) — restated here only because the
    material is homogeneous on this fixture, so the DG0 fields are the two
    imported scalars.

    Algebraically ``c = −1/(σ + jωε₀ε_r)``, whose *magnitude* is
    ``1/|σ + jωε|`` — frequency-flat while ``σ ≫ ωε``, which is what step 1′
    measured as "``W_e`` is frequency-independent on this fixture".  The test
    prints both forms so the identity is visible, and asserts on the one built
    from the form's coefficients.
    """
    omega = 2.0 * np.pi * frequency_hz
    load_factor = -1j * omega * MU_0
    k0_squared = omega * omega * MU_0 * EPSILON_0
    epsilon_c = EPSILON_R - 1j * SIGMA / (omega * EPSILON_0)
    return complex(-load_factor / (k0_squared * epsilon_c))


def _gradient_identity_row(
    *, mesh, cell_tags, solver, e_complex, j_raw, degree, frequency_hz, comm
) -> dict:
    """`TH-13` step 2 (A)/(B) for one solved row — floats only, nothing held.

    ``J′_used`` is the expression the load actually integrated: the projection's
    own ``χJ − ∇ψ`` when ``project_source`` was on (`time_harmonic.py:461`), and
    the tag-restricted ``χJ`` when it was off, because that is what the tagged
    measure integrates.  ``χ`` and ``φ`` are the two degree-matched Laplace
    projections; the Dirichlet set comes from
    :meth:`TimeHarmonicSolver.build_boundary_conditions` rather than from an
    assumption about the mode (§7 trap).
    """
    boundary_mode = solver.build_boundary_conditions()[1]
    dirichlet_h10 = boundary_mode != TimeHarmonicBoundaryCondition.NATURAL

    indicator = None
    if solver._projection is not None:
        j_used = solver._projection.current
        projected = True
    else:
        indicator = _subdomain_indicator(mesh, cell_tags, 1)
        j_used = indicator * j_raw
        projected = False

    chi = _gradient_potential(
        mesh, degree, e_complex, comm, dirichlet_h10=dirichlet_h10
    )
    phi = _gradient_potential(mesh, degree, j_used, comm, dirichlet_h10=dirichlet_h10)

    c = _form_constant(frequency_hz)
    c_const = fem.Constant(mesh, PETSc.ScalarType(c))
    c_mistuned = fem.Constant(mesh, PETSc.ScalarType(MISTUNED_C_FACTOR * c))
    grad_chi = ufl.grad(chi)
    grad_phi = ufl.grad(phi)
    norm_chi = _l2_norm(grad_chi, comm)

    return {
        "c": c,
        "projected": projected,
        "boundary_mode": boundary_mode.value,
        "norm_grad_chi": norm_chi,
        "norm_grad_phi": _l2_norm(grad_phi, comm),
        "norm_j_used": _l2_norm(j_used, comm),
        "residual": _l2_norm(grad_chi - c_const * grad_phi, comm) / norm_chi,
        "residual_mistuned": (
            _l2_norm(grad_chi - c_mistuned * grad_phi, comm) / norm_chi
        ),
        # (B): the electric energy carried by the gradient part of E, in the
        # module's own imported convention — `stored_electric_energy` is
        # (ε₀/4)∫εᵣ|E|², not the ε₀εᵣ‖·‖²/2 §7 wrote, and the share is only
        # meaningful against the same convention it is a share of.
        "w_e_gradient_j": 0.25 * EPSILON_0 * EPSILON_R * norm_chi**2,
    }


def _solve_loop_at_degree(
    degree: int, comm, frequency_hz: float, *, project_source: bool = True
) -> dict:
    """The closed azimuthal loop drive on the smoke box at ``frequency_hz``.

    Byte-for-byte the smoke fixture except for the two things this step varies:
    the drive (`POST-5` step 2's :func:`_azimuthal_current`, imported) and the
    frequency (:data:`LOOP_FREQUENCIES_HZ`).  ``gauge_penalty`` is left at the
    solver default, which is what `TH-12` steps 2 and 3 measured every recorded
    ratio on — the ungauged second-order gradient space is the object under
    test, so gauging it here would answer a different question.
    """
    mesh, cell_tags, facet_tags = _smoke_mesh(SMOKE_RESOLUTION, comm)
    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=frequency_hz,
        material=HomogeneousMaterial(sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=1.0),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
    )
    solver = TimeHarmonicSolver(problem, degree=degree)

    j_azimuthal = _azimuthal_current(mesh)

    def current_density(x):
        # The coefficient is already the field; x is the solver's
        # SpatialCoordinate and is deliberately unused (`POST-5` step 2).
        return j_azimuthal

    fields = solver.solve(
        current_density=current_density, subdomain_id=1, project_source=project_source
    )

    tdim = mesh.topology.dim
    ncells = int(comm.allreduce(mesh.topology.index_map(tdim).size_local, op=MPI.SUM))
    v_space = fields.e_complex.function_space
    n_dofs = int(v_space.dofmap.index_map.size_global * v_space.dofmap.index_map_bs)
    p_complex = _complex_ohmic_power(fields.e_complex, SIGMA, comm)
    # `TH-13` step 2 rides on this solve rather than on a stored handle to it.
    # Every mesh, Function and PETSc object below dies when this call returns,
    # on both ranks at the same point in the program — holding them alive in a
    # module-scoped fixture instead let Python collect them in rank-dependent
    # order, and PETSc destruction is collective: measured 2026-08-31, the
    # module ran every assertion green and then deadlocked in teardown
    # (`20260831T020528Z_TH-13-step2.log`, killed at the 300 s ceiling).
    step2 = _gradient_identity_row(
        mesh=mesh,
        cell_tags=cell_tags,
        solver=solver,
        e_complex=fields.e_complex,
        j_raw=j_azimuthal,
        degree=degree,
        frequency_hz=frequency_hz,
        comm=comm,
    )

    return {
        "degree": degree,
        "frequency_hz": frequency_hz,
        "step2": step2,
        "ncells": ncells,
        "n_dofs": n_dofs,
        "w_e": stored_electric_energy(fields, comm=comm),
        "w_m": _stored_magnetic_energy(fields.e_complex, fields.omega, comm),
        "dissipated_power_w": float(np.real(p_complex)),
        "power_imaginary": abs(float(np.imag(p_complex))) / abs(float(np.real(p_complex))),
    }


def _verdict(loop_move: float) -> str:
    if loop_move >= CLASS_RATIO_FACTOR:
        return "CLASS (the ungauged second-order gradient space itself)"
    if loop_move <= FEED_RATIO_FACTOR:
        return "FEED (the coil's feed model injects it)"
    return "IN-BETWEEN (recorded, not forced)"


def _label(frequency_hz: float) -> str:
    return f"loop {frequency_hz / 1e6:.0f} MHz"


@pytest.fixture(scope="module")
def discriminator_rows():
    """Both loop rows at both orders, plus step 3's two control fixtures."""
    comm = MPI.COMM_WORLD
    loop = {
        frequency_hz: {
            degree: _solve_loop_at_degree(degree, comm, frequency_hz)
            for degree in (1, 2)
        }
        for frequency_hz in LOOP_FREQUENCIES_HZ
    }
    smoke = {degree: _solve_smoke_at_degree(degree, comm) for degree in (1, 2)}
    sphere = {
        degree: _energies_of_sphere_row(_run_at_degree(degree), comm)
        for degree in (1, 2)
    }
    # Step 2's negative control (§7): the same fixture solved once with the
    # source projection OFF, so `‖P_∇₁J‖/‖J‖` can be read against the projected
    # `‖P_∇₁J′‖/‖J′‖` and the projection is seen doing something (`PORT-1`
    # step 2d/2e precedent).  Degree 1, one extra solve, no energy is read off
    # it and no recorded number depends on it.
    unprojected = _solve_loop_at_degree(
        1, comm, LOOP_FREQUENCY_HZ, project_source=False
    )
    return {
        "loop": loop,
        "smoke": smoke,
        "sphere": sphere,
        "loop_unprojected": unprojected,
    }


def _print_table(rows: dict) -> None:
    comm = MPI.COMM_WORLD
    if comm.rank != 0:
        return
    print("\n[TH-13 step 1'] stored energies at N1curl degree 1 vs 2:")
    print(
        "  fixture         deg   cells     DOFs        W_m [J]        W_e [J]"
        "      W_e/W_m"
    )
    named = [
        (_label(frequency_hz), rows["loop"][frequency_hz])
        for frequency_hz in LOOP_FREQUENCIES_HZ
    ] + [("smoke", rows["smoke"]), ("sphere", rows["sphere"])]
    for name, pair in named:
        for degree in (1, 2):
            row = pair[degree]
            print(
                f"  {name:<14s}  {degree:d}  {row['ncells']:6d}  "
                f"{row['n_dofs']:8d}  {row['w_m']:.6e}  {row['w_e']:.6e}  "
                f"{row['w_e'] / row['w_m']:.6e}"
            )
    for frequency_hz in LOOP_FREQUENCIES_HZ:
        for degree in (1, 2):
            row = rows["loop"][frequency_hz][degree]
            print(
                f"  {_label(frequency_hz)} degree {degree}: dissipated "
                f"{row['dissipated_power_w']:.6e} W, |Im P|/Re P = "
                f"{row['power_imaginary']:.3e}"
            )
    print(
        f"  coil (printed, `TH-12` step 2 record, not re-run): "
        f"W_e/W_m = {COIL_W_E_W_M_DEGREE1:.6e} at degree 1 -> "
        f"{COIL_W_E_W_M_DEGREE2:.6e} at degree 2, a "
        f"{COIL_W_E_W_M_DEGREE2 / COIL_W_E_W_M_DEGREE1:.3e}x move"
    )
    moves = ", ".join(
        f"{_label(frequency_hz)} {_ratio_move(rows['loop'][frequency_hz]):.3e}x"
        for frequency_hz in LOOP_FREQUENCIES_HZ
    )
    print(
        f"  cross-order move in W_e/W_m: {moves} (compatible drive), "
        f"smoke {_ratio_move(rows['smoke']):.3e}x (J.n != 0, control), "
        f"sphere {_ratio_move(rows['sphere']):.3e}x (imposed field, control)"
    )
    for frequency_hz in LOOP_FREQUENCIES_HZ:
        gated = "GATED" if frequency_hz == LOOP_FREQUENCY_HZ else "RECORDED, not gated"
        one = rows["loop"][frequency_hz][1]
        print(
            f"  precondition ({gated}): {_label(frequency_hz)} degree-1 W_e/W_m "
            f"= {one['w_e'] / one['w_m']:.6e} against the pre-registered "
            f"<= {MAGNETIC_DOMINANCE_MAX:.0e}"
        )
    measured = (
        rows["loop"][LOOP_FREQUENCY_HZ][1]["w_e"]
        / rows["loop"][LOOP_FREQUENCY_HZ][1]["w_m"]
    )
    print(
        f"  omega^2 rescope: predicted {OMEGA_SQUARED_PREDICTED_RATIO:.6e} at "
        f"{LOOP_FREQUENCY_HZ / 1e6:.0f} MHz from the "
        f"{STEP1_RECORD_DEGREE1_RATIO:.6e} step-1 record at "
        f"{LOOP_RECORD_FREQUENCY_HZ / 1e6:.0f} MHz; measured "
        f"{measured:.6e}, i.e. {measured / OMEGA_SQUARED_PREDICTED_RATIO:.1f}x "
        f"the prediction and {measured / STEP1_RECORD_DEGREE1_RATIO:.4f}x the "
        f"10 MHz reading -- W_e/W_m is frequency-INDEPENDENT on this fixture "
        f"and the omega^2 premise is REFUTED"
    )
    print(
        f"  bands: >= {CLASS_RATIO_FACTOR:.0e}x on the loop => CLASS; "
        f"<= {FEED_RATIO_FACTOR:.0f}x => FEED"
    )
    print(
        f"  VERDICT ({_label(LOOP_FREQUENCY_HZ)}): "
        f"{_verdict(_ratio_move(rows['loop'][LOOP_FREQUENCY_HZ]))}",
        flush=True,
    )


@complex_only
@pytest.mark.integration
def test_the_loop_fixture_is_magnetically_dominated(discriminator_rows):
    """Precondition (§7 step 1′), asserted at 1 MHz: degree-1 ``W_e/W_m ≤ 1e-2``.

    Runs first and prints the whole table, so no verdict is read against an
    unverified fixture.  This is the entire reason the fixture exists: `TH-12`
    step 3's two cheap fixtures sit at ``W_e/W_m`` 2.16 and 1.07, the coil at
    6.7e-6, and nothing in the tree occupied the magnetically-dominated cell
    with a *compatible* drive.  If this assertion fails the fixture is not that
    cell, the cross-order move below discriminates nothing, and §7 says the step
    stops on that finding rather than reinterpreting the number.

    The band is step 1's, unmoved: what step 1′ changed is the *fixture's*
    frequency, on the pre-registered ω² argument, not the bar it has to clear.
    **The rescope failed** — 1.926692e-02 at 1 MHz against 1.952350e-02 at
    10 MHz, so this assertion is red on `main` by design, as step 1's was at
    10 MHz.  It is the chunk's finding, not a defect to be tuned away: no band
    moves here without a fixture that actually clears it.
    """
    _print_table(discriminator_rows)
    one = discriminator_rows["loop"][LOOP_FREQUENCY_HZ][1]

    assert one["ncells"] == 1405, (
        f"the loop fixture meshed to {one['ncells']} cells, not the smoke box's "
        f"recorded 1 405 — the mesh moved under the control columns"
    )
    ratio = one["w_e"] / one["w_m"]
    assert ratio <= MAGNETIC_DOMINANCE_MAX, (
        f"the closed azimuthal drive at {LOOP_FREQUENCY_HZ / 1e6:.0f} MHz reads "
        f"W_e/W_m = {ratio:.6e} at degree 1, over the pre-registered "
        f"{MAGNETIC_DOMINANCE_MAX:.0e} — this fixture is not magnetically "
        f"dominated, so it is not the missing cell of `TH-12` step 3's table "
        f"and its cross-order move discriminates FEED from CLASS not at all"
    )
    for frequency_hz in LOOP_FREQUENCIES_HZ:
        for degree in (1, 2):
            row = discriminator_rows["loop"][frequency_hz][degree]
            assert row["power_imaginary"] < POWER_IMAGINARY_BOUND, (
                f"the {_label(frequency_hz)} fixture's ohmic power at degree "
                f"{degree} carries an imaginary part "
                f"{row['power_imaginary']:.3e} of the real part, over the "
                f"{POWER_IMAGINARY_BOUND:.0e} family bound — inner() "
                f"conjugates, so this is a solve defect, not a convention"
            )


@complex_only
@pytest.mark.integration
def test_the_step3_controls_reproduce_their_recorded_moves(discriminator_rows):
    """Negative control (§7): step 3's two fixtures still read 1.155× / 1.015×.

    Both run here through step 3's own imported helpers, so this is the same
    code path measured on 2026-08-19.  If either control has drifted, the loop
    fixture's move is not comparable with the recorded coil / smoke / sphere
    family and the verdict below is not attributable to the fixture.
    """
    smoke_move = _ratio_move(discriminator_rows["smoke"])
    sphere_move = _ratio_move(discriminator_rows["sphere"])

    assert np.isclose(smoke_move, SMOKE_MOVE_RECORD, rtol=RECORD_REPRODUCTION_RTOL), (
        f"the `TH-12` step 3 smoke control moved {smoke_move:.4f}x in W_e/W_m "
        f"across order against its recorded {SMOKE_MOVE_RECORD:.3f}x"
    )
    assert np.isclose(sphere_move, SPHERE_MOVE_RECORD, rtol=RECORD_REPRODUCTION_RTOL), (
        f"the `TH-12` step 3 sphere control moved {sphere_move:.4f}x in W_e/W_m "
        f"across order against its recorded {SPHERE_MOVE_RECORD:.3f}x"
    )

    dissipated = discriminator_rows["smoke"][1]["dissipated_power_w"]
    assert np.isclose(dissipated, AXIAL_RECORD_DISSIPATED_W, rtol=1e-6), (
        f"the degree-1 smoke column dissipated {dissipated:.6e} W against the "
        f"`POST-5` record {AXIAL_RECORD_DISSIPATED_W:.6e} W — the anchor that "
        f"says this is the same box, the same material and the same solve the "
        f"whole degree-2 family was measured on"
    )


@complex_only
@pytest.mark.integration
def test_the_step1_10mhz_row_reproduces_its_recorded_reading(discriminator_rows):
    """Negative control for the rescope (§7 step 1′): the 10 MHz row is unmoved.

    Step 1's fixture is kept in the table as a *recorded* row — its precondition
    is no longer asserted, because 1.952350e-02 against a 1e-2 band is a known
    reading and re-asserting it gates nothing but a deliberate red.  What is
    asserted is that this run reproduces it: the degree-1 ratio and the
    in-between cross-order move 5.156e+01× at rtol 1e-3.  If either has drifted,
    the 1 MHz row is not step 1's fixture rescoped and the verdict below is not
    comparable with the recorded coil / smoke / sphere family.
    """
    record = discriminator_rows["loop"][LOOP_RECORD_FREQUENCY_HZ]
    ratio = record[1]["w_e"] / record[1]["w_m"]
    move = _ratio_move(record)

    assert np.isclose(ratio, STEP1_RECORD_DEGREE1_RATIO, rtol=STEP1_RECORD_RTOL), (
        f"the {LOOP_RECORD_FREQUENCY_HZ / 1e6:.0f} MHz row reads degree-1 "
        f"W_e/W_m = {ratio:.6e} against step 1's recorded "
        f"{STEP1_RECORD_DEGREE1_RATIO:.6e} — the fixture moved since "
        f"2026-08-30, so the rescope is not measuring the same thing"
    )
    assert np.isclose(move, STEP1_RECORD_MOVE, rtol=STEP1_RECORD_RTOL), (
        f"the {LOOP_RECORD_FREQUENCY_HZ / 1e6:.0f} MHz row moved {move:.4e}x "
        f"across order against step 1's recorded {STEP1_RECORD_MOVE:.4e}x"
    )


@complex_only
@pytest.mark.integration
def test_the_magnetically_dominated_compatible_drive_discriminates(
    discriminator_rows,
):
    """The reading: does a compatible drive with ``W_m ≫ W_e`` explode too?

    ``≥ 1e3×`` ⇒ **CLASS** — the ungauged second-order gradient space fills on
    any such fixture, the coil's feed is not special, and the next chunk is a
    gauged / tree-cotree / ``H¹``-augmented degree-2 formulation.  ``≤ 10×`` ⇒
    **FEED** — the coil's port feed is the injector and the next chunk is the
    feed model.  Whichever band the run lands in is *asserted*, so a later
    change that quietly moves second-order gradient behaviour shows up on a
    1 405-cell fixture instead of a 62 GiB one.  Only an in-between reading is
    left ungated: §7 says record it, invent no band around it.
    """
    rows = discriminator_rows["loop"][LOOP_FREQUENCY_HZ]
    loop_move = _ratio_move(rows)
    verdict = _verdict(loop_move)
    one = rows[1]
    two = rows[2]

    if verdict.startswith("CLASS"):
        assert loop_move >= CLASS_RATIO_FACTOR, (
            f"the magnetically-dominated compatible drive moved "
            f"{loop_move:.3e}x in W_e/W_m across order "
            f"({one['w_e'] / one['w_m']:.6e} -> {two['w_e'] / two['w_m']:.6e}), "
            f"under the pre-registered {CLASS_RATIO_FACTOR:.0e} that made this "
            f"reading CLASS"
        )
    elif verdict.startswith("FEED"):
        assert loop_move <= FEED_RATIO_FACTOR, (
            f"the magnetically-dominated compatible drive moved "
            f"{loop_move:.3e}x in W_e/W_m across order "
            f"({one['w_e'] / one['w_m']:.6e} -> {two['w_e'] / two['w_m']:.6e}), "
            f"outside the pre-registered {FEED_RATIO_FACTOR:.0f}x that made "
            f"this reading FEED"
        )
        assert loop_move < CLASS_RATIO_FACTOR
    else:
        pytest.skip(
            f"`TH-13` step 1 read {verdict}: the loop fixture moved "
            f"{loop_move:.3e}x across order, between the pre-registered "
            f"{FEED_RATIO_FACTOR:.0f}x and {CLASS_RATIO_FACTOR:.0e}. Per §7 the "
            f"reading is recorded in the plan and in known-issues and no band "
            f"is fabricated around it here"
        )


# ---------------------------------------------------------------------------
# `TH-13` step 2 — the gradient-projection identity.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gradient_projections(discriminator_rows):
    """Step 2's readings, computed inside each solve and collected here.

    No new physics solve and no live PETSc object: every ``χ``/``φ`` pair was
    built by :func:`_gradient_identity_row` while its own curl-curl solution was
    still in scope, and what survives is a dict of floats.
    """
    rows = {
        (frequency_hz, degree): dict(
            discriminator_rows["loop"][frequency_hz][degree]["step2"],
            w_e_j=discriminator_rows["loop"][frequency_hz][degree]["w_e"],
        )
        for frequency_hz in LOOP_FREQUENCIES_HZ
        for degree in (1, 2)
    }
    control = dict(discriminator_rows["loop_unprojected"]["step2"])
    control["gradient_share"] = control["norm_grad_phi"] / control["norm_j_used"]
    return {"rows": rows, "unprojected": control}


@complex_only
@pytest.mark.integration
def test_the_discrete_gradient_equation_is_an_exact_identity(gradient_projections):
    """(A) — ``‖∇χ − c∇φ‖/‖∇χ‖ ≤ 1e-6`` at both degrees and both frequencies.

    The pre-registered discriminant of step 2 (PROJECT_PLAN §7, rescoped
    2026-08-30 18:00).  Testing the assembled weak form with ``v = ∇ψ`` kills
    the curl term identically, so the discrete system pins the
    ``∇Lagrange_p``-projection of ``E_h`` to ``c`` times that of ``J′`` for
    every admissible ``ψ`` — ``c`` being ``−load_factor/(k₀²ε_c)``, read off the
    form's own coefficients.  If it holds, the degree-2 electric energy the
    known-issues entry calls "spurious" is the drive's **unremoved** gradient
    residue divided by ``(σ + jωε)``, and no free "ungauged null-space mode"
    story survives (``k² ≠ 0`` pins it).  If it fails at either degree the
    discrete gradient equation is not what the form says, which is a
    formulation finding and not a tolerance to widen.

    The mistuned-``c`` reading is the load-bearing probe (`PORT-12` step 2
    precedent): a 10% error in ``c`` must show up as a ≈ 10% residual, or the
    ratio is insensitive to ``c`` and (A) passing means nothing.
    """
    comm = MPI.COMM_WORLD
    rows = gradient_projections["rows"]
    if comm.rank == 0:
        print("\n[TH-13 step 2] the discrete gradient equation, per row:")
        print(
            "  fixture         deg  bc        |c|          "
            "||grad chi||   ||grad phi||   residual    mistuned"
        )
        for frequency_hz in LOOP_FREQUENCIES_HZ:
            for degree in (1, 2):
                r = rows[(frequency_hz, degree)]
                print(
                    f"  {_label(frequency_hz):<14s}  {degree:d}  "
                    f"{r['boundary_mode']:<8s}  {abs(r['c']):.6e}  "
                    f"{r['norm_grad_chi']:.6e}  {r['norm_grad_phi']:.6e}  "
                    f"{r['residual']:.3e}  {r['residual_mistuned']:.3e}"
                )
        for frequency_hz in LOOP_FREQUENCIES_HZ:
            omega = 2.0 * np.pi * frequency_hz
            r = rows[(frequency_hz, 1)]
            ohmic = SIGMA + 1j * omega * EPSILON_0 * EPSILON_R
            print(
                f"  {_label(frequency_hz)}: c = {r['c']:.6e}, "
                f"-1/(sigma + j*omega*eps) = {-1.0 / ohmic:.6e}, "
                f"|c| * |sigma + j*omega*eps| = {abs(r['c']) * abs(ohmic):.9f}"
            )
        print(flush=True)

    for frequency_hz in LOOP_FREQUENCIES_HZ:
        for degree in (1, 2):
            r = rows[(frequency_hz, degree)]
            assert r["residual"] <= GRADIENT_IDENTITY_MAX, (
                f"the {_label(frequency_hz)} row at degree {degree} reads "
                f"||grad chi - c grad phi|| / ||grad chi|| = "
                f"{r['residual']:.6e}, over the pre-registered "
                f"{GRADIENT_IDENTITY_MAX:.0e} — the grad-Lagrange_{degree} "
                f"projection of E_h is NOT c times that of J', so the discrete "
                f"gradient equation is not what the assembled form says"
            )
            assert r["residual_mistuned"] >= MISTUNED_C_MIN, (
                f"the {_label(frequency_hz)} row at degree {degree} still reads "
                f"{r['residual_mistuned']:.6e} with c mistuned by "
                f"{MISTUNED_C_FACTOR:.2f}x — the residual is insensitive to c, "
                f"so the identity above is vacuous"
            )


@complex_only
@pytest.mark.integration
def test_the_source_projection_leaves_a_residue_the_solve_answers(
    gradient_projections,
):
    """(B) the mechanism's size, printed; plus the projection's own control.

    ``‖P_∇₂J′‖/‖P_∇₁J′‖`` and the share of the measured ``W_e`` carried by
    ``∇χ`` are recorded, not gated — §7 pre-registers them as readings with no
    band invented around them.  What *is* asserted is the control (`PORT-1`
    step 2d/2e precedent): the unprojected drive must read a visibly larger
    ``‖P_∇₁J‖/‖J‖`` than the projected one, or `remove_gradient_content` is not
    doing the thing whose *incompleteness* this step attributes the degree-2
    energy to.  Strict inequality only — no threshold is fabricated here.
    """
    comm = MPI.COMM_WORLD
    rows = gradient_projections["rows"]
    control = gradient_projections["unprojected"]

    projected_share = (
        rows[(LOOP_FREQUENCY_HZ, 1)]["norm_grad_phi"]
        / rows[(LOOP_FREQUENCY_HZ, 1)]["norm_j_used"]
    )

    if comm.rank == 0:
        print("\n[TH-13 step 2] (B) the residue's size, recorded not gated:")
        for frequency_hz in LOOP_FREQUENCIES_HZ:
            one = rows[(frequency_hz, 1)]
            two = rows[(frequency_hz, 2)]
            print(
                f"  {_label(frequency_hz)}: ||P_grad2 J'|| / ||P_grad1 J'|| = "
                f"{two['norm_grad_phi'] / one['norm_grad_phi']:.6e}"
            )
            for degree, r in ((1, one), (2, two)):
                print(
                    f"    degree {degree}: W_e(grad chi) = "
                    f"{r['w_e_gradient_j']:.6e} J of a measured W_e = "
                    f"{r['w_e_j']:.6e} J, share "
                    f"{r['w_e_gradient_j'] / r['w_e_j']:.6f}; "
                    f"||P_grad{degree} J'||/||J'|| = "
                    f"{r['norm_grad_phi'] / r['norm_j_used']:.6e}"
                )
        print(
            f"  projection control: unprojected ||P_grad1 J||/||J|| = "
            f"{control['gradient_share']:.6e} against the projected "
            f"{projected_share:.6e} "
            f"(project_source was {'ON' if control['projected'] else 'OFF'} "
            f"on the control solve)",
            flush=True,
        )

    assert not control["projected"], (
        "the negative-control solve kept its source projection — "
        "`project_source=False` did not reach the solver, so the comparison "
        "below is the projected drive against itself"
    )
    assert control["gradient_share"] > projected_share, (
        f"the unprojected drive reads ||P_grad1 J||/||J|| = "
        f"{control['gradient_share']:.6e}, not above the projected drive's "
        f"{projected_share:.6e} — `remove_gradient_content` is not visibly "
        f"removing CG1 gradient content, so attributing the degree-2 energy to "
        f"what it *fails* to remove is unsupported"
    )
