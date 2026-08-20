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

The multiplier's behaviour on a *compatible* source is gated next door, in
``test_gauge_multiplier_convergence.py``: `OPS-17` step 2 asserted it vanishes
to solver tolerance on a divergence-free closed loop and carried the failure
here as a strict xfail; `MAG-17` step 1 (2026-08-20) measured the h-ladder,
found the spread converging at rate 2.4476, and moved the claim to where a
convergence rate can actually be asserted. The loop geometry constants below
are shared with that file.
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

# `OPS-17` step 2: the divergence-free counter-fixture. A closed loop carries
# azimuthal current with div J = 0 and J.n = 0 on the whole boundary, so the
# Coulomb-gauge multiplier is identically zero in the continuum. 0.005 is the
# `OPS-17` record's own mesh and the base rung of `MAG-17`'s ladder.
LOOP_RADIUS = 0.02
LOOP_WIRE_RADIUS = 0.003
LOOP_DOMAIN_RADIUS = 0.06
LOOP_RESOLUTION = 0.005


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


def test_gauge_multiplier_is_nan_without_a_lagrange_solve(wire_solutions):
    """Structural contract: no multiplier exists after a PENALTY solve.

    `OPS-17` step 2 (2026-08-17) split the old
    ``test_gauge_multiplier_spread_is_reported`` in two. Its ``isnan`` half is
    a genuine structural contract and is kept here unchanged; its
    ``isfinite(spread)`` half was finiteness-class; the quantitative statement
    that replaces it is the wire-scale gate below plus the convergence gate in
    ``test_gauge_multiplier_convergence.py`` (`MAG-17` step 1).
    """
    pen_spread = wire_solutions[GaugeMethod.PENALTY]["multiplier_spread"]
    assert np.isnan(pen_spread), "spread should be nan when no multiplier exists"

    spread = wire_solutions[GaugeMethod.LAGRANGE]["multiplier_spread"]
    assert np.isfinite(spread), "a LAGRANGE solve must expose a finite spread"


def test_incompatible_wire_multiplier_stays_at_its_recorded_scale(
    wire_solutions,
):
    """An incompatible source must keep the multiplier O(1)-large.

    `OPS-17` step 2 wrote the anchor "multiplier spread -> 0 to solver
    tolerance for a divergence-free source" and carried its failure here as a
    strict xfail at 1e-9 (measured 7.836781e+00 on the closed loop,
    ``20260817T111217Z_OPS-17-step2-solver-n2.log``). `MAG-17` step 1
    (2026-08-20) ran the h-ladder that was left undone and **refuted the
    anchor, not the code**: the spread converges at fitted rate 2.4476
    (7.836781e+00 -> 3.052022e+00 -> 1.438617e+00 over h = 0.005/0.0035/0.0025,
    ``20260820T123307Z_MAG-17-step1-ladder.log``), which is the pre-registered
    DISCRETE-SOURCE verdict: ``p`` absorbs the interpolated ``J``'s O(h)
    discrete divergence, so it is a discretisation residual and *cannot* sit at
    solver tolerance on any single mesh. The claim moved to the file where a
    rate can be asserted; what stays here is the wire-side record this file's
    fixture already carries.
    """
    spread = wire_solutions[GaugeMethod.LAGRANGE]["multiplier_spread"]

    # Recorded 2.083064e+02 on the incompatible wire, 26.6x the loop's base-h
    # value: this fixture's source is genuinely incompatible, so the multiplier
    # must be O(1)-large, not a residual. The band is an order of magnitude
    # either side of the record.
    assert 2.0e1 < spread < 2.0e3, (
        f"incompatible-wire multiplier spread {spread:.6e} is outside the "
        "recorded 2.083064e+02 band: the fixture or the constraint block moved"
    )
