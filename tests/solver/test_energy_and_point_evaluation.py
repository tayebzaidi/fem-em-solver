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


def _global_scalar(mesh, form_expr):
    """Assemble a scalar form with an explicit global reduction."""
    local = fem.assemble_scalar(fem.form(form_expr))
    return float(mesh.comm.allreduce(local, op=MPI.SUM))


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
