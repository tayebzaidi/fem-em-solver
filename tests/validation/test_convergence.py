"""
Convergence study tests for magnetostatic solver.

These tests verify that the numerical solution converges to the analytical
solution as the mesh is refined (h-refinement) or polynomial degree is
increased (p-refinement).
"""

import pytest
import numpy as np
import ufl
from mpi4py import MPI

# Import solver components
from fem_em_solver.core.solvers import (
    MagnetostaticProblem,
    MagnetostaticSolver,
    exterior_dirichlet_bc,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import AnalyticalSolutions, ErrorMetrics
from fem_em_solver.utils.constants import MU_0

# ---------------------------------------------------------------------------
# h-refinement fixture, at module scope so it can be imported.
#
# `EX-9` (examples/magnetostatics/06_h_convergence_rate.py) runs this exact
# fixture as a runnable example. The parameters, the per-resolution solve and
# the rate fit live here rather than inside the test body so the example
# imports them instead of restating them -- a restated copy would drift, and
# then the example would no longer be showing the gated measurement. This
# refactor is additive: what the test computes and asserts is unchanged.
# ---------------------------------------------------------------------------

# Problem parameters. Sized to match tests/validation/test_straight_wire.py
# so both stay inside the runtime budget: a fat wire meshes cheaply and,
# for uniform current density, has an external field identical to a
# filament for r > a. See MAG-9.
CURRENT = 1.0
WIRE_LENGTH = 0.2
WIRE_RADIUS = 0.003
DOMAIN_RADIUS = 0.03

# Three resolutions: two points fit any rate exactly, so a two-resolution
# "rate" is not a measurement. This particular triple is measured (MAG-13, log
# 20260730T034614Z_MAG-13-probe2 and 20260730T124930Z_MAG-13-conv2), at -n 2
# with the analytic BC:
#   h=0.004   38.8k cells   22.19%    (~8 s)
#   h=0.0025  145.9k cells  12.75%    (~27 s)
#   h=0.0018  383.2k cells   9.26%    (~92 s)
# Coarser starting points do not belong here: at h=0.005 (23.2k cells) the
# error is 30.34%, because 5 mm cells cannot resolve the 3 mm wire -- that is a
# geometry-resolution artifact, not the asymptotic regime, and it inflates the
# fitted rate. At h=0.0035 (61.3k) the error is 11.77%, i.e. *below* the
# h=0.0025 value: cell-wise constant curl(A) means the pointwise samples read
# whichever cell contains them, so individual resolutions carry O(h) sampling
# noise and a sequence containing 0.0035 is non-monotone. Total ~140 s of
# solve; MAG-13 is a heavy-tier chunk (§5.1: convergence studies). Shrink the
# case rather than raising the timeout.
RESOLUTIONS = [0.004, 0.0025, 0.0018]

# --- MAG-19 (2026-08-25): the rate duty left this statistic -------------------
# The rate gate below WAS `RATE_MIN < rate < RATE_MAX` on the sampled 10-point
# statistic (MAG-13 step 5, band [0.7, 1.5], fit 1.10 on record in
# 20260730T125522Z_MAG-13.log over 22.19% -> 12.75% -> 9.26%). It is retired as
# a *gate* by the 2026-08-25 18:00 review's ruling (i) on MAG-19 -- retired with
# its basis measured, never widened, and the duty moved rather than dropped:
#
# * On the 0.11 image the fit reads **1.9038** over 21.8417% -> 15.3848% ->
#   4.4605% (reproduced this slot, 20260826T020124Z_MAG-19-step2-red.log).
#   MAG-19 step 1 ran both norms on the *same four solves*
#   (20260825T183555Z_MAG-19-step1-dualnorm-fits.log) and the sampled ladder is
#   not anomalous at one rung: its pairwise rates are 0.5822 / 0.7456 / 1.9894 /
#   1.0034 / 2.7819 / 3.7690, i.e. out of band on both ends and on pairs that do
#   not involve the finest rung.
# * The statistic itself is the defect: OPS-18 step 3 attempt 5 measured a
#   **34%** swing of this norm under its own sample count (15.8028 / 12.7485 /
#   11.4984% at n_points = 8 / 10 / 20 on the recording image), and the band
#   already failed on 0.7.2 at n_points = 8 -- i.e. it was passing on a sampler
#   choice (known-issues 2026-08-22 / 2026-08-25).
# * MAG-18 built the sampler-free replacement for exactly this reason. The rate
#   duty now belongs to its E_Omega annulus ladder, which is live and green on
#   0.11 at fit **1.6854** with 6/6 pairwise rates above its own one-sided
#   >= 0.7 (20260824T003059Z_MAG-18-regate-run1.log).
#
# No upper edge is re-imposed here or anywhere: none has a validated basis on
# 0.11 (both statistics fit above 1.5 on the full ladder), and under-convergence
# is the failure mode a rate gate exists to catch. A superconvergence guard, if
# ever wanted, needs its own measured basis and a commissioning.
RATE_DUTY_OWNER = (
    "tests/validation/test_straight_wire.py::TestStraightWire::"
    "test_domain_l2_convergence (MAG-18: E_Omega rate >= 0.7, one-sided)"
)

# Retained, and still consumed, but no longer this ladder's gate:
#   * this module and examples/magnetostatics/06_h_convergence_rate.py print
#     them beside the fitted rate as the *report* band;
#   * test_straight_wire.py::test_straight_wire_convergence gates its own
#     two-rung 8-point fit on them. That test was not in MAG-19's scope and is
#     left untouched (MAG-18's module is this disposition's negative control);
#     its residual upper edge is a finding for the review, not this chunk's.
RATE_MIN = 0.7
RATE_MAX = 1.5

# Evaluation points along +x at the midplane, outside the conductor. The
# window runs out to 0.8 * domain_radius: with the analytic Dirichlet wall the
# near-boundary region is no longer where the error lives (measured 12.48%
# over 2a -> 0.4R vs 12.75% over 2a -> 0.8R at h = 0.0025), and the wider
# window is the harder test.
N_EVAL_POINTS = 10


def evaluation_points():
    """The (N_EVAL_POINTS, 3) sample line used for every resolution."""
    r_eval = np.linspace(2.0 * WIRE_RADIUS, 0.8 * DOMAIN_RADIUS, N_EVAL_POINTS)
    points = np.zeros((N_EVAL_POINTS, 3))
    points[:, 0] = r_eval
    points[:, 2] = 0.0
    return points


def _wire_potential_interp(x):
    """Analytic wire A, dolfinx interpolation convention (3, n)."""
    pts = np.ascontiguousarray(x[:3].T)
    return AnalyticalSolutions.straight_wire_vector_potential(
        pts, CURRENT, wire_radius=WIRE_RADIUS
    ).T


def solve_h_refinement(resolution, comm):
    """One resolution of the h-refinement sequence.

    Meshes, solves with the analytic Dirichlet wall, samples ``|B|`` on the
    evaluation line and returns the relative L2 error against the closed form
    together with the objects an example needs to export.
    """
    points = evaluation_points()
    b_analytic = AnalyticalSolutions.straight_wire_magnetic_field(points, CURRENT)
    b_analytic_mag = np.linalg.norm(b_analytic, axis=1)

    mesh, cell_tags, _ = MeshGenerator.straight_wire_domain(
        wire_length=WIRE_LENGTH,
        wire_radius=WIRE_RADIUS,
        domain_radius=DOMAIN_RADIUS,
        resolution=resolution,
        comm=comm,
    )

    problem = MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0)
    solver = MagnetostaticSolver(problem, degree=1)

    j_magnitude = CURRENT / (np.pi * WIRE_RADIUS**2)

    def current_density(x):
        return ufl.as_vector([0.0, 0.0, j_magnitude])

    bc = exterior_dirichlet_bc(solver.V, _wire_potential_interp)
    solver.solve(current_density=current_density, subdomain_id=1, bc_functions=[bc])
    b_field = solver.compute_b_field()

    # Evaluate in the cells actually containing each point.
    b_num, valid = evaluate_vector_field_parallel(b_field, points, comm=comm)
    assert valid.all(), f"{(~valid).sum()}/{N_EVAL_POINTS} sample points outside mesh"
    b_num_mag = np.linalg.norm(b_num, axis=1)

    return {
        "resolution": resolution,
        "n_cells": mesh.topology.index_map(mesh.topology.dim).size_global,
        "rel_error": ErrorMetrics.l2_relative_error(b_num_mag, b_analytic_mag),
        "mesh": mesh,
        "cell_tags": cell_tags,
        "b_field": b_field,
        "b_numeric_mag": b_num_mag,
        "b_analytic_mag": b_analytic_mag,
    }


def fit_convergence_rate(resolutions, errors):
    """Least-squares slope of log(error) against log(h).

    For error ~ C * h^p we have log(error) = log(C) + p*log(h), so the rate is
    the slope -- positive when the error shrinks with the mesh. An earlier
    revision negated this slope, which reported a negative rate for genuinely
    convergent data and tripped the assertion in the test below.
    """
    log_h = np.log(resolutions)
    log_err = np.log(errors)
    return float(
        np.sum((log_h - np.mean(log_h)) * (log_err - np.mean(log_err)))
        / np.sum((log_h - np.mean(log_h)) ** 2)
    )


class TestConvergence:
    """Convergence study tests for magnetostatic solver."""
    
    def test_h_refinement_straight_wire(self):
        """
        Test h-convergence (mesh refinement) for straight wire problem.

        **The rate duty is not here any more** (MAG-19, ruling (i) of the
        2026-08-25 18:00 review): the sampled 10-point statistic swings 34%
        under its own sample count, so its fitted slope cannot gate anything.
        The owner of the h-convergence rate is ``RATE_DUTY_OWNER`` -- MAG-18's
        sampler-free E_Omega annulus ladder, one-sided ``rate >= 0.7``, live and
        green on 0.11. See the retirement block above ``RATE_DUTY_OWNER`` for
        the measurements; nothing was widened.

        What this test still gates is the part of the sequence that does not
        depend on the sampler's accidents: the errors must decay
        **monotonically** coarse to fine. A discretization blind to h shows no
        systematic decay and fails this. The fitted rate and the error table are
        printed as a *report* beside the retired band.

        The outer wall carries the analytic potential as Dirichlet data
        (MAG-13, ``exterior_dirichlet_bc``). This is what makes the test a
        convergence gate at all: with the natural condition ``n x H = 0`` the
        continuum limit is *not* the analytic field -- the wall forces the very
        azimuthal component being compared to zero, contradicting Ampere's law
        for a net axial current -- so the measured error plateaus at a modeling
        floor and the fitted rate decays toward zero as h shrinks. Do not
        revert to the natural BC and loosen the bounds below; see the MAG-13
        entry in PROJECT_PLAN.md §7.
        """
        comm = MPI.COMM_WORLD

        # Fixture, sample line and rate fit are module-level (see the block
        # above the class) so examples/magnetostatics/06_h_convergence_rate.py
        # runs this measurement rather than a copy of it.
        resolutions = RESOLUTIONS
        errors = []

        for res in resolutions:
            if comm.rank == 0:
                print(f"\n  Testing resolution h = {res}...")

            result = solve_h_refinement(res, comm)
            errors.append(result["rel_error"])

            if comm.rank == 0:
                print(f"    Cells: {result['n_cells']}")
                print(f"    Relative L2 error: {result['rel_error']:.4%}")

        rate = fit_convergence_rate(resolutions, errors)

        if comm.rank == 0:
            print(f"\n  Convergence Results (report -- the rate is NOT gated here):")
            print(f"    Resolutions (h): {resolutions}")
            print(f"    Errors: {[f'{e:.4%}' for e in errors]}")
            print(f"    Convergence rate: {rate:.4f}")
            print(f"    Retired report band: [{RATE_MIN}, {RATE_MAX}] (MAG-19)")
            print(f"    Rate duty owner: {RATE_DUTY_OWNER}")

        # The gate: systematic decay, coarse to fine. The rate the retired band
        # used to bound is reported above and owned by RATE_DUTY_OWNER.
        for i in range(1, len(errors)):
            assert errors[i] < errors[i - 1], (
                f"error rose from {errors[i - 1]:.4%} at h = {resolutions[i - 1]} "
                f"to {errors[i]:.4%} at h = {resolutions[i]}: the sampled error "
                "is not decaying with the mesh, which no sampler accident "
                f"explains; errors {errors} at h {resolutions}"
            )


# OPS-17 step 2 (2026-08-17): test_p_refinement_straight_wire and
# test_convergence_data_export deleted — both were bare
# pytest.skip("Not yet implemented") stubs that inflated the pass count
# without asserting anything.


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
