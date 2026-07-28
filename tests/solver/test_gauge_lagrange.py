"""Lagrange-multiplier Coulomb gauge cross-checks (MAG-15).

``GaugeMethod.LAGRANGE`` solves the (A, p) saddle point in N1curl x H1,
enforcing div(A) = 0 weakly. Its value over the penalty method is that the
curl-curl null space is *removed* rather than priced: the penalty leaves a
gradient component of magnitude ~1/gauge in A, and B = curl(A) recovers the
physical field only through floating-point cancellation (see MAG-10 for how
that fails silently).

These tests pin the two properties that make LAGRANGE a trustworthy
cross-check of the penalty default:

1. Agreement — both methods produce the same B field on the same mesh.
2. Null-space removal — the Lagrange A carries no ~1/gauge gradient
   component, so its max|A| sits orders of magnitude below the penalty
   solution's.

Fixture note: the straight wire terminates on the domain end caps, so
J.n != 0 there and the source is incompatible with the curl-curl operator.
The multiplier absorbs exactly that component, which is why its spread is
reported as a diagnostic rather than asserted against zero.
"""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from fem_em_solver.core.solvers import (
    GaugeMethod,
    MagnetostaticProblem,
    MagnetostaticSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import AnalyticalSolutions, ErrorMetrics
from fem_em_solver.utils.constants import MU_0

WIRE_RADIUS = 0.003
DOMAIN_RADIUS = 0.03
WIRE_LENGTH = 0.20
RESOLUTION = 0.006  # coarse: these tests compare methods, not absolute accuracy

# Sample outside the conductor, inside the region the outer boundary perturbs
# least — same window as tests/validation/test_straight_wire.py.
N_POINTS = 8
_POINTS = np.zeros((N_POINTS, 3))
_POINTS[:, 0] = np.linspace(2.0 * WIRE_RADIUS, 0.4 * DOMAIN_RADIUS, N_POINTS)


@pytest.fixture(scope="module")
def wire_solutions():
    """Solve the straight-wire fixture once per gauge method on a shared mesh."""
    comm = MPI.COMM_WORLD
    mesh, cell_tags, _ = MeshGenerator.straight_wire_domain(
        wire_length=WIRE_LENGTH,
        wire_radius=WIRE_RADIUS,
        domain_radius=DOMAIN_RADIUS,
        resolution=RESOLUTION,
        comm=comm,
    )
    j = 1.0 / (np.pi * WIRE_RADIUS**2)

    results = {}
    for method in (GaugeMethod.PENALTY, GaugeMethod.LAGRANGE):
        solver = MagnetostaticSolver(
            MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0), degree=1
        )
        A = solver.solve(
            current_density=lambda x: ufl.as_vector([0.0, 0.0, j]),
            subdomain_id=1,
            gauge=method,
        )
        local_max = float(np.max(np.abs(A.x.array))) if A.x.array.size else 0.0
        b_vals, valid = evaluate_vector_field_parallel(
            solver.compute_b_field(), _POINTS, comm=comm
        )
        assert valid.all(), f"{(~valid).sum()}/{N_POINTS} sample points outside mesh"
        results[method] = {
            "b": b_vals,
            "max_a": comm.allreduce(local_max, op=MPI.MAX),
            "multiplier_spread": solver.gauge_multiplier_spread(),
        }
    return results


def test_penalty_and_lagrange_agree_on_b_field(wire_solutions):
    """Both gauges must yield the same physical field on the same mesh.

    Measured on this fixture family: identical analytic error to 4 significant
    figures at h=0.003 (24.67% both, degree 1). 5% here is generous headroom
    for the coarser mesh; a gauge-treatment defect shows up as orders, not
    percent.
    """
    b_pen = wire_solutions[GaugeMethod.PENALTY]["b"]
    b_lag = wire_solutions[GaugeMethod.LAGRANGE]["b"]

    rel_diff = ErrorMetrics.l2_relative_error(b_lag, b_pen)
    assert rel_diff < 0.05, (
        f"penalty and Lagrange B fields disagree by {rel_diff:.2%}"
    )

    # Trend sanity: both should track mu0*I/(2*pi*r). Measured 52.5% at this
    # deliberately coarse h=0.006 (35.5% at h=0.005), on a fixture that also
    # carries a modeling floor (PMC side wall + incompatible source; MAG-13).
    # The bound only needs to catch gross errors: a wrong current direction
    # measured ~88-100% on the loop fixtures, and null-space corruption shows
    # up as orders of magnitude, not percent.
    b_ana = np.linalg.norm(
        AnalyticalSolutions.straight_wire_magnetic_field(_POINTS, 1.0), axis=1
    )
    for method in (GaugeMethod.PENALTY, GaugeMethod.LAGRANGE):
        b_mag = np.linalg.norm(wire_solutions[method]["b"], axis=1)
        err = ErrorMetrics.l2_relative_error(b_mag, b_ana)
        assert err < 0.70, f"{method.value}: {err:.2%} vs analytic 1/r reference"


def test_lagrange_removes_null_space_component(wire_solutions):
    """The saddle point must not carry the penalty's ~1/gauge gradient part.

    Measured at h=0.003: max|A| = 1.6e-09 (Lagrange) vs 5.2e+01 (penalty at
    gauge 1.0) — eleven orders. The 1e-6 bound leaves five orders of margin;
    if it trips, the multiplier equation has stopped constraining A and the
    method must not be trusted as a cross-check.
    """
    max_a_pen = wire_solutions[GaugeMethod.PENALTY]["max_a"]
    max_a_lag = wire_solutions[GaugeMethod.LAGRANGE]["max_a"]

    assert max_a_pen > 0.0
    assert max_a_lag < 1e-6 * max_a_pen, (
        f"Lagrange max|A|={max_a_lag:.3e} not far below penalty "
        f"max|A|={max_a_pen:.3e}; null space not removed"
    )


def test_gauge_multiplier_spread_is_reported(wire_solutions):
    """The multiplier diagnostic must be available after a LAGRANGE solve.

    This fixture's source is incompatible by construction (J.n != 0 on the end
    caps), so the spread is expected to be non-zero; its magnitude is
    mesh-dependent and is printed rather than pinned.
    """
    spread = wire_solutions[GaugeMethod.LAGRANGE]["multiplier_spread"]
    assert np.isfinite(spread)

    pen_spread = wire_solutions[GaugeMethod.PENALTY]["multiplier_spread"]
    assert np.isnan(pen_spread), "spread should be nan when no multiplier exists"

    if MPI.COMM_WORLD.rank == 0:
        print(f"\ngauge multiplier spread (incompatible source): {spread:.6e}")
