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

# Two-sided bound (MAG-13 step 5). N1curl degree 1 predicts ~1.0 for this
# quantity; the measured three-point fit over the resolutions above
# (22.19% -> 12.75% -> 9.26%) is **1.10** (log 20260730T125522Z_MAG-13).
# The upper bound matters as much as the lower one: a rate well above 1.5 is
# not "better than expected" convergence but a sign that one resolution in the
# sequence is anomalous (a mesh whose cells happen to straddle the sample
# points favourably), which is exactly how the old `rate > 0.5` check would
# have kept passing while the fixture drifted.
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

        As mesh size h decreases, error should decrease at expected rate.
        For linear Nedelec elements, expect rate ~1.0.

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
            print(f"\n  Convergence Results:")
            print(f"    Resolutions (h): {resolutions}")
            print(f"    Errors: {[f'{e:.4%}' for e in errors]}")
            print(f"    Convergence rate: {rate:.2f}")
            print(f"    Expected rate for linear elements: ~1.0")

        # Two-sided bound (MAG-13 step 5); the band and the reason for its
        # upper edge are recorded at RATE_MIN / RATE_MAX above.
        assert RATE_MIN < rate < RATE_MAX, (
            f"Convergence rate {rate:.2f} outside [{RATE_MIN}, {RATE_MAX}] "
            f"(expected ~1.0 for N1curl degree 1); errors {errors} at h "
            f"{resolutions}"
        )
    
    def test_p_refinement_straight_wire(self):
        """
        Test p-convergence (polynomial degree) for straight wire problem.
        
        As polynomial degree increases, error should decrease.
        
        Steps:
        1. Fixed mesh resolution (e.g., 0.01)
        2. Loop over degrees: [1, 2, 3]
        3. For each degree:
           - Create solver with degree=N
           - Solve and compute error
        4. Assert error decreases with higher degree
        
        TODO: Implement this test
        """
        pytest.skip("Not yet implemented - Chunk 7")
    
    def test_convergence_data_export(self):
        """
        Export convergence data for visualization.
        
        Save h vs error and degree vs error to files in results/convergence/
        
        TODO: Implement data export
        """
        pytest.skip("Not yet implemented - Chunk 8")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
