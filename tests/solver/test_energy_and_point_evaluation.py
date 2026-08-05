"""Parallel-correctness guards for MagnetostaticSolver's public API (MAG-11/12).

Both defects here survived the 2026-07-27 audit because nothing in-tree called
the affected methods -- which is exactly why they needed tests before the next
consumer found them the hard way.

MAG-11: ``compute_magnetic_energy()`` returned the rank-local
``fem.assemble_scalar`` contribution, so under ``mpiexec -n N`` it reported
roughly 1/N of the true energy. Both flagship magnetostatics examples print
this figure. Two guards:

1. Exact agreement with an explicitly allreduced assembly of the same
   integrand -- the direct regression pin for the missing reduction.
2. The discrete work-energy identity ``W = 1/2 int J . A dx``, which holds
   for a ``GaugeMethod.LAGRANGE`` solution: testing the saddle point against
   (A, p) gives ``int mu^-1|curl A|^2 + 2 int grad(p).A = int J.A``, and the
   constraint row with q = p forces ``int A.grad(p) = 0`` exactly.

   The same identity on the PENALTY gauge is unusable, and measurably so:
   there ``W = (int J.A - gauge*int |A|^2)/2``, a difference of O(1) terms
   whose null-space content carries the operator's full conditioning
   (kappa ~ mu^-1/(gauge*h^2) ~ 1e10 on this fixture). Measured: identity
   error 1.4e-3 absolute against W ~ 1e-8 -- five orders above the signal,
   sign flipped. The Lagrange route has no cancelling terms: both sides are
   ~2W. The identity's right-hand side is assembled with explicit allreduces,
   so it cannot inherit the defect it guards against; a missing reduction in
   W shows up as a factor-~N violation.

MAG-12: ``evaluate_at_points()`` still used ``f.eval(points, np.arange(n))``
-- the arbitrary-cells pattern MAG-7 eradicated from the tests, left behind in
the API itself. The guard pins agreement with the collision-based machinery in
``post.evaluation`` and requires out-of-mesh points to raise rather than
return extrapolated garbage.
"""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core.solvers import (
    DEFAULT_GAUGE_PENALTY,
    ENERGY_IMAG_RTOL,
    GaugeMethod,
    MagnetostaticProblem,
    MagnetostaticSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.constants import MU_0

WIRE_RADIUS = 0.003
DOMAIN_RADIUS = 0.03
WIRE_LENGTH = 0.20
RESOLUTION = 0.006  # coarse: these tests probe reductions, not accuracy
J_MAGNITUDE = 1.0 / (np.pi * WIRE_RADIUS**2)

# MAG-16 cross-build pin. Measured in the *real* build at -n 2 on this fixture
# before compute_magnetic_energy() gained its real-part reduction, so the
# complex build is pinned to a number the fix cannot have influenced
# (20260805T213144Z_MAG-16-probe-real.log). Rank-count independent: both tests
# below assemble globally reduced quantities.
REAL_BUILD_ENERGY_J = {
    GaugeMethod.PENALTY: 1.121469318858e-08,
    GaugeMethod.LAGRANGE: 1.121466766900e-08,
}
# Measured deviations from the pins across four -n 2 runs (two real, two
# complex): the Lagrange gauge reproduces to 1.3e-13, the penalty gauge
# wanders 1.9e-08 .. 2.9e-07 run to run -- its operator carries the gauge null
# space at kappa ~ 1e10 (see the module docstring), so the direct LU is not
# bit-reproducible on it. The bound is set two decades above the largest
# observed wander; the defects it exists to catch (a missing allreduce, or
# abs() of a complex scalar with real imaginary content) are O(1), not O(1e-7).
PIN_RTOL = 1e-5
IMAG_RATIO_BAND = 1e-12  # measured |Im W| / |Re W| = 0.0 in both builds


@pytest.fixture(scope="module")
def solved_wire():
    """Coarse straight-wire solves (one per gauge) shared by every guard here."""
    comm = MPI.COMM_WORLD
    mesh, cell_tags, _ = MeshGenerator.straight_wire_domain(
        wire_length=WIRE_LENGTH,
        wire_radius=WIRE_RADIUS,
        domain_radius=DOMAIN_RADIUS,
        resolution=RESOLUTION,
        comm=comm,
    )

    solvers = {}
    for method in (GaugeMethod.PENALTY, GaugeMethod.LAGRANGE):
        solver = MagnetostaticSolver(
            MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0), degree=1
        )
        solver.solve(
            current_density=lambda x: ufl.as_vector([0.0, 0.0, J_MAGNITUDE]),
            subdomain_id=1,
            gauge_penalty=DEFAULT_GAUGE_PENALTY,
            gauge=method,
        )
        solvers[method] = solver

    return mesh, cell_tags, solvers


def _global_complex_scalar(mesh, form_expr):
    """Assemble a scalar form with an explicit global reduction, unreduced type.

    In the complex build every ``fem.Function`` is complex, so
    ``assemble_scalar`` returns a complex scalar even for an integrand that is
    real by construction; the caller decides what to do with the imaginary
    part (MAG-16).
    """
    local = fem.assemble_scalar(fem.form(form_expr))
    return mesh.comm.allreduce(local, op=MPI.SUM)


def _global_scalar(mesh, form_expr):
    """Assemble a scalar form with an explicit global reduction, real part."""
    return float(np.real(_global_complex_scalar(mesh, form_expr)))


def _energy_integrand(solver):
    """The integrand of ``compute_magnetic_energy`` for this fixture (mu = MU_0)."""
    return 0.5 * (1.0 / MU_0) * ufl.inner(ufl.curl(solver.A), ufl.curl(solver.A)) * ufl.dx


def test_energy_matches_the_real_build_value(solved_wire, capsys):
    """MAG-16 cross-build pin: the complex build must reproduce the real one.

    ``compute_magnetic_energy`` discards an imaginary part in the complex
    build, and a wrong reduction (``abs()``, or the magnitude of a complex
    scalar) would still return a plausible positive number -- so the value
    itself is pinned against the real-build reference measured on this same
    fixture at ``-n 2`` before the reduction was written
    (``20260805T213144Z_MAG-16-probe-real.log``, pre-fix). Measured deviation
    of the complex build from those references
    (``20260805T213201Z_MAG-16-probe-complex-prefix.log``): 3.3e-08 for the
    penalty gauge and 0.0 -- bit-identical -- for the Lagrange gauge. The rtol
    below is two decades of headroom on that, not a fitted value; both builds
    solve the same real linear system, so anything larger is a real change.
    """
    _, _, solvers = solved_wire

    for method, expected in REAL_BUILD_ENERGY_J.items():
        w = solvers[method].compute_magnetic_energy()
        rel = abs(w - expected) / expected
        with capsys.disabled():
            print(f"MAG-16 {method.name}: W={w:.12e} J, real-build pin rel={rel:.3e}")
        assert isinstance(w, float), f"{method.name}: energy is {type(w)}, not float"
        assert rel < PIN_RTOL, (
            f"{method.name}: energy {w:.12e} deviates from the real-build value "
            f"{expected:.12e} by {rel:.3e} (> {PIN_RTOL:g})"
        )


def test_discarded_imaginary_part_of_the_energy_is_negligible(solved_wire, capsys):
    """The part ``compute_magnetic_energy`` throws away must be nothing.

    The magnetostatic load is real, so ``A`` is real-valued even when the build
    stores it as complex, and ``ufl.inner`` conjugates its second argument --
    the integrand is ``mu^-1|curl A|^2/2``. Measured ratio: exactly 0.0 in both
    builds and both gauges at ``-n 2`` (the two probe logs cited above); the
    band below is headroom. This is the assertion that makes the real-part
    reduction in ``core/solvers.py`` honest rather than a cast that hides
    whatever it is handed.
    """
    mesh, _, solvers = solved_wire

    for method, solver in solvers.items():
        total = _global_complex_scalar(mesh, _energy_integrand(solver))
        real = float(np.real(total))
        imag = float(np.imag(total))
        assert real > 0.0
        ratio = abs(imag) / real
        with capsys.disabled():
            print(
                f"MAG-16 {method.name}: W_re={real:.12e} W_im={imag:.12e} "
                f"|Im/Re|={ratio:.3e} dtype={np.asarray(total).dtype}"
            )
        assert ratio < IMAG_RATIO_BAND, (
            f"{method.name}: energy carries |Im/Re| = {ratio:.3e}, above the "
            f"probe-measured band {IMAG_RATIO_BAND:g} -- the real-part "
            "reduction would be discarding physics"
        )
        # The test's band must sit inside the solver's own refusal threshold,
        # or a ratio this test accepts would make the solver raise.
        assert IMAG_RATIO_BAND <= ENERGY_IMAG_RTOL


def test_energy_matches_explicitly_reduced_assembly(solved_wire):
    """The method must return the global integral, not a rank-local slice.

    At 1 rank this is trivially true; at mpiexec -n 2+ a missing allreduce
    makes the method return roughly half of this reference. Tolerance is
    solver precision -- both sides assemble the identical integrand.
    """
    mesh, _, solvers = solved_wire
    solver = solvers[GaugeMethod.PENALTY]
    w_method = solver.compute_magnetic_energy()

    mu_inv = 1.0 / MU_0
    w_reference = _global_scalar(
        mesh, 0.5 * mu_inv * ufl.inner(ufl.curl(solver.A), ufl.curl(solver.A)) * ufl.dx
    )

    assert w_reference > 0.0
    assert abs(w_method - w_reference) <= 1e-12 * w_reference, (
        f"energy {w_method:.12e} != globally reduced assembly {w_reference:.12e}"
        " -- rank-local result?"
    )


def test_energy_satisfies_discrete_work_energy_identity(solved_wire):
    """W must equal 1/2 int J.A for the Lagrange-gauged solution.

    Exact for the discrete saddle point: testing against (A, p) gives
    int mu^-1|curl A|^2 + 2 int grad(p).A = int J.A, and the constraint row
    with q = p zeroes the middle term. Unlike the penalty variant (see the
    module docstring for why that one cannot work), both sides here are ~2W
    with no cancellation, so the tolerance can sit at solver precision with
    orders of headroom. A missing reduction in W violates this by a factor
    ~n_ranks.
    """
    mesh, cell_tags, solvers = solved_wire
    solver = solvers[GaugeMethod.LAGRANGE]

    w_method = solver.compute_magnetic_energy()

    j_vec = ufl.as_vector([0.0, 0.0, J_MAGNITUDE])
    dx_wire = ufl.Measure(
        "dx", domain=mesh, subdomain_data=cell_tags, subdomain_id=1
    )
    work = _global_scalar(mesh, ufl.inner(j_vec, solver.A) * dx_wire)
    w_identity = 0.5 * work

    assert w_identity > 0.0
    rel = abs(w_method - w_identity) / w_identity
    assert rel < 1e-4, (
        f"work-energy identity violated: W={w_method:.6e} vs "
        f"(1/2) int J.A = {w_identity:.6e} ({rel:.2%})"
    )


def test_evaluate_at_points_matches_collision_based_evaluation(solved_wire):
    """The API method must agree with post.evaluation on interior points."""
    _, _, solvers = solved_wire
    solver = solvers[GaugeMethod.PENALTY]

    n = 6
    points = np.zeros((n, 3))
    points[:, 0] = np.linspace(2.0 * WIRE_RADIUS, 0.4 * DOMAIN_RADIUS, n)

    for field in ("A", "B"):
        via_api = solver.evaluate_at_points(points, field=field)

        f = solver.A if field == "A" else solver.compute_b_field()
        reference, valid = evaluate_vector_field_parallel(f, points)
        assert valid.all()

        scale = float(np.max(np.abs(reference)))
        assert scale > 0.0
        max_diff = float(np.max(np.abs(via_api - reference)))
        assert max_diff <= 1e-9 * scale, (
            f"field {field}: evaluate_at_points deviates from collision-based "
            f"evaluation by {max_diff:.3e} (scale {scale:.3e})"
        )


def test_evaluate_at_points_rejects_points_outside_mesh(solved_wire):
    """Out-of-mesh points must raise, not return extrapolated values.

    The pre-MAG-12 implementation happily returned numbers for these -- basis
    functions evaluated far outside their support.
    """
    _, _, solvers = solved_wire
    solver = solvers[GaugeMethod.PENALTY]

    outside = np.array([[2.0 * DOMAIN_RADIUS, 0.0, 0.0]])
    with pytest.raises(ValueError, match="outside the mesh"):
        solver.evaluate_at_points(outside, field="B")
