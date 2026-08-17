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
from tests.validation.test_circular_loop import azimuthal_current_density

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
# Coulomb-gauge multiplier is identically zero in the continuum. Deliberately
# coarse — this test compares multiplier behaviour between two sources, not
# absolute field accuracy, so it buys nothing from refinement.
LOOP_RADIUS = 0.02
LOOP_WIRE_RADIUS = 0.003
LOOP_DOMAIN_RADIUS = 0.06
LOOP_RESOLUTION = 0.005

# The step-1 anchor: for a divergence-free source the multiplier is identically
# zero in the continuum, so its spread should be a solver-tolerance residual.
# Measured at 7.836781e+00 — see the xfail'd test below.
LOOP_SPREAD_MAX = 1.0e-9


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


@pytest.fixture(scope="module")
def loop_lagrange_solution():
    """LAGRANGE solve of a closed loop — a source compatible by construction."""
    comm = MPI.COMM_WORLD
    mesh, cell_tags, _ = MeshGenerator.circular_loop_domain(
        loop_radius=LOOP_RADIUS,
        wire_radius=LOOP_WIRE_RADIUS,
        domain_radius=LOOP_DOMAIN_RADIUS,
        resolution=LOOP_RESOLUTION,
        comm=comm,
    )
    j = 1.0 / (np.pi * LOOP_WIRE_RADIUS**2)

    solver = MagnetostaticSolver(
        MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0), degree=1
    )
    A = solver.solve(
        current_density=azimuthal_current_density(j),
        subdomain_id=1,
        gauge=GaugeMethod.LAGRANGE,
    )
    local_max = float(np.max(np.abs(A.x.array))) if A.x.array.size else 0.0
    return {
        "max_a": comm.allreduce(local_max, op=MPI.MAX),
        "multiplier_spread": solver.gauge_multiplier_spread(),
    }


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
    ``isfinite(spread)`` half was finiteness-class, and the quantitative
    statement that was supposed to replace it is the xfail'd test below.
    """
    pen_spread = wire_solutions[GaugeMethod.PENALTY]["multiplier_spread"]
    assert np.isnan(pen_spread), "spread should be nan when no multiplier exists"

    spread = wire_solutions[GaugeMethod.LAGRANGE]["multiplier_spread"]
    assert np.isfinite(spread), "a LAGRANGE solve must expose a finite spread"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "known-issues 2026-08-17 (OPS-17 step 2): the Coulomb-gauge multiplier "
        "does NOT vanish for a divergence-free source — measured spread "
        "7.836781e+00 on a closed current loop against the 1e-9 the step-1 "
        "anchor expects. Not diagnosed; band left strict so a fix shows as "
        "XPASS."
    ),
)
def test_gauge_multiplier_vanishes_for_a_divergence_free_source(
    loop_lagrange_solution, wire_solutions
):
    """The multiplier should be zero when the source is compatible.

    `OPS-17` step 2 (2026-08-17) — **this test is a finding, not a pass.** The
    step-1 table named "multiplier spread -> 0 to solver tolerance for a
    divergence-free source" as the anchor that would replace
    ``isfinite(spread)``. Executed, it does not hold.

    Measured at `-n 2`, ``20260817T111217Z_OPS-17-step2-solver-n2.log``:

        incompatible straight wire (J.n != 0 on the end caps): spread 2.083064e+02
        divergence-free closed loop (div J = 0, J.n = 0 everywhere): spread 7.836781e+00

    A closed loop carrying azimuthal current has ``div J = 0`` in the interior
    and ``J.n = 0`` on both the torus surface (phi-hat is tangent to it) and
    the outer sphere, so ``p`` is identically zero in the continuum and the
    discrete spread should sit at solver tolerance. 7.84 is not that. The
    multiplier *is* doing something — it is 26.6x larger on the genuinely
    incompatible fixture, so it has not stopped responding to compatibility —
    but "vanishes for a compatible source" is false as written.

    Two candidate explanations, neither settled here and both cheap to
    distinguish with an h-ladder the timebox did not allow:

    1. **Benign discretisation.** The source enters the FE functional through
       an interpolated ``J``, whose discrete divergence is only O(h). Then the
       spread should fall with refinement, and the anchor should have been
       "-> 0 with refinement", not "-> 0 to solver tolerance". This fixture is
       deliberately coarse (h = 0.005 against a 0.003 wire radius).
    2. **A real defect** in how the constraint is assembled, in which case the
       spread is h-independent.

    Note also that ``max|A|`` is *not* a usable normaliser here: the whole
    point of LAGRANGE is that the null space is removed, so
    ``test_lagrange_removes_the_null_space`` requires its ``max|A|`` to be six
    orders below the penalty solve's. Both spreads are therefore reported raw.

    Diagnosing this is `MAG`/`OPS` work on the gauge formulation, not `OPS-17`
    test hygiene. The band stays where the anchor put it and the marker is
    ``strict=True`` so a fix is reported as XPASS.
    """
    spread = wire_solutions[GaugeMethod.LAGRANGE]["multiplier_spread"]
    loop_spread = loop_lagrange_solution["multiplier_spread"]

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[OPS-17] gauge multiplier spread (raw):"
            f"\n  incompatible straight wire: {spread:.6e}"
            f"\n  divergence-free loop:       {loop_spread:.6e}"
            f"\n  ratio: {spread / loop_spread:.3f}x",
            flush=True,
        )

    assert loop_spread < LOOP_SPREAD_MAX, (
        f"multiplier spread {loop_spread:.6e} on a divergence-free source is "
        f"above the {LOOP_SPREAD_MAX:.0e} solver-tolerance band: the Coulomb "
        "gauge constraint is absorbing something that should not be there"
    )
