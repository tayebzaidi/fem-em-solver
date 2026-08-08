"""Convergence/conditioning diagnostics tests for time-harmonic solve path."""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
    classify_residual_trend,
)
from fem_em_solver.io.mesh import MeshGenerator

from tests.complex_mode import complex_only


def test_classify_residual_trend_summaries_are_deterministic():
    assert classify_residual_trend([]) == "unavailable"
    assert classify_residual_trend([1.0]) == "single-sample"
    assert classify_residual_trend([1.0, 0.2, 0.05]) == "monotone-decrease"
    assert classify_residual_trend([1.0, 0.4, 0.45, 0.1]) == "mostly-decreasing"
    assert classify_residual_trend([1.0, 0.8, 0.9, 0.7, 0.75]) == "mixed"
    assert classify_residual_trend([0.1, 0.2, 0.3, 0.5]) == "mostly-increasing"


def _sequence_with_decrease_fraction(n_down: int, n_up: int) -> list[float]:
    """Build a positive residual history with an exactly known decrease fraction.

    ``n_down`` steps halve the residual and ``n_up`` steps multiply it by 1.5,
    interleaved so the result is not accidentally sorted. The decrease fraction
    of the returned history is exactly ``n_down / (n_down + n_up)``.
    """
    steps = []
    remaining_down, remaining_up = n_down, n_up
    while remaining_down or remaining_up:
        if remaining_down:
            steps.append(0.5)
            remaining_down -= 1
        if remaining_up:
            steps.append(1.5)
            remaining_up -= 1

    history = [1.0]
    for factor in steps:
        history.append(history[-1] * factor)
    return history


# `OPS-12`: the classifier's label is an exact function of the decrease
# fraction f (see `classify_residual_trend`), so the identity is asserted with
# `==`, never a tolerance. The family spans both sides of the specified
# threshold f = 0.5 *and* both sides of the undocumented f = 0.75 the
# classifier used to carry, so the four rows with 0.5 < f < 0.75 are exactly
# the ones the previous thresholds got wrong — they mislabelled them `mixed`.
# The 2/3 row is the fraction of the on-record disputed sequence
# [1.0, 0.4, 0.45, 0.1].
@pytest.mark.parametrize(
    "n_down, n_up, expected",
    [
        (4, 0, "monotone-decrease"),  # f = 1
        (7, 1, "mostly-decreasing"),  # f = 0.875, above the old 0.75
        (3, 1, "mostly-decreasing"),  # f = 0.75, the old threshold itself
        (5, 3, "mostly-decreasing"),  # f = 0.625, old code said `mixed`
        (2, 1, "mostly-decreasing"),  # f = 2/3,   old code said `mixed`
        (1, 1, "mixed"),  # f = 0.5,   the tie
        (2, 2, "mixed"),  # f = 0.5,   the tie
        (3, 5, "mostly-increasing"),  # f = 0.375
        (1, 3, "mostly-increasing"),  # f = 0.25
        (1, 2, "mostly-increasing"),  # f = 1/3
        (0, 4, "mostly-increasing"),  # f = 0
    ],
)
def test_classify_residual_trend_is_an_exact_function_of_the_decrease_fraction(
    n_down, n_up, expected
):
    history = _sequence_with_decrease_fraction(n_down, n_up)

    deltas = np.diff(np.asarray(history))
    measured_fraction = float(np.count_nonzero(deltas <= 0.0)) / float(len(deltas))
    assert measured_fraction == pytest.approx(n_down / (n_down + n_up), abs=0.0)

    assert classify_residual_trend(history) == expected


def test_classify_residual_trend_negative_controls():
    """A wrong label must be reachable, or the identity above has no teeth."""
    # Genuinely alternating: every other step increases, f = 0.5 exactly.
    alternating = _sequence_with_decrease_fraction(4, 4)
    assert classify_residual_trend(alternating) == "mixed"

    # Strictly increasing may never be reported as decreasing of any kind.
    increasing = [0.1, 0.2, 0.3, 0.5, 0.9]
    assert classify_residual_trend(increasing) == "mostly-increasing"
    assert classify_residual_trend(increasing) not in {
        "mostly-decreasing",
        "monotone-decrease",
    }

    # Non-finite and negative histories are neither, they are `invalid`.
    assert classify_residual_trend([1.0, float("nan"), 0.5]) == "invalid"
    assert classify_residual_trend([1.0, float("inf"), 0.5]) == "invalid"
    assert classify_residual_trend([1.0, -0.5, 0.25]) == "invalid"


@complex_only
def test_time_harmonic_solver_emits_optional_solve_health_diagnostics():
    comm = MPI.COMM_WORLD

    mesh, cell_tags, facet_tags = MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.08,
        length=0.12,
        resolution=0.03,
        comm=comm,
    )

    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=127.74e6,
        material=HomogeneousMaterial(sigma=0.7, epsilon_r=78.0, mu_r=1.0),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
        # `OPS-12`: `ksp_max_it` was 300 and this fixture's gmres+jacobi solve
        # needs **1409** iterations to reach `ksp_rtol = 1e-8` (measured on the
        # 1405-cell fixture, log 20260808T050338Z_OPS-12-probe.log: reason -3 /
        # 300 its / residual 1.4999e-06 at the old cap, reason 2 / 1409 its /
        # residual 4.26e-12 at 5000). `assert diagnostics.converged` below is
        # unchanged — the cap was under-resourced, the assertion was not wrong.
        # jacobi is kept deliberately: it is the weak preconditioner that makes
        # the residual history long enough to classify.
        solver_petsc_options={
            "ksp_type": "gmres",
            "pc_type": "jacobi",
            "ksp_rtol": 1e-8,
            "ksp_max_it": 5000,
        },
        collect_solver_diagnostics=True,
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    def current_density(_x):
        return ufl.as_vector([0.0, 0.0, 1.0])

    fields = solver.solve(current_density=current_density, subdomain_id=1, gauge_penalty=1e-3)

    diagnostics = fields.solve_diagnostics
    assert diagnostics is not None
    assert diagnostics.ksp_type == "gmres"
    assert diagnostics.pc_type == "jacobi"
    assert diagnostics.converged
    assert diagnostics.iterations > 0
    assert np.isfinite(diagnostics.residual_norm)
    assert diagnostics.residual_trend in {
        "unavailable",
        "single-sample",
        "monotone-decrease",
        "mostly-decreasing",
        "mixed",
        "mostly-increasing",
    }

    # `OPS-12`: this path never armed `ksp.setConvergenceHistory()`, so the
    # history came back empty and the trend was permanently `unavailable` — the
    # classifier was unreachable in production and the label above passed
    # vacuously. Both halves are now gated: the history has one entry per
    # iteration plus the initial residual, and the reported label is exactly
    # what the classifier makes of that history.
    assert len(diagnostics.residual_history) == diagnostics.iterations + 1
    assert diagnostics.residual_trend != "unavailable"
    assert diagnostics.residual_trend == classify_residual_trend(diagnostics.residual_history)
