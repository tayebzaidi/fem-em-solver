"""
Convergence study tests for magnetostatic solver.

These tests verify that the numerical solution converges to the analytical
solution as the mesh is refined (h-refinement) or polynomial degree is
increased (p-refinement).
"""

import pytest
import numpy as np
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

        # Problem parameters. Sized to match tests/validation/test_straight_wire.py
        # so both stay inside the runtime budget: a fat wire meshes cheaply and,
        # for uniform current density, has an external field identical to a
        # filament for r > a. See MAG-9.
        current = 1.0
        wire_length = 0.2
        wire_radius = 0.003
        domain_radius = 0.03

        # Three resolutions: two points fit any rate exactly, so a
        # two-resolution "rate" is not a measurement. This particular triple is
        # measured (MAG-13, log 20260730T034614Z_MAG-13-probe2 and
        # 20260730T124930Z_MAG-13-conv2), at -n 2 with the analytic BC:
        #   h=0.004   38.8k cells   22.19%    (~8 s)
        #   h=0.0025  145.9k cells  12.75%    (~27 s)
        #   h=0.0018  383.2k cells   9.26%    (~92 s)
        # Coarser starting points do not belong here: at h=0.005 (23.2k cells)
        # the error is 30.34%, because 5 mm cells cannot resolve the 3 mm wire
        # -- that is a geometry-resolution artifact, not the asymptotic regime,
        # and it inflates the fitted rate. At h=0.0035 (61.3k) the error is
        # 11.77%, i.e. *below* the h=0.0025 value: cell-wise constant curl(A)
        # means the pointwise samples read whichever cell contains them, so
        # individual resolutions carry O(h) sampling noise and a sequence
        # containing 0.0035 is non-monotone. Total ~140 s: standard tier, close
        # to its ceiling. Shrink the case rather than raising the timeout.
        resolutions = [0.004, 0.0025, 0.0018]
        errors = []

        # Evaluation points along +x at the midplane, outside the conductor.
        # The window runs out to 0.8 * domain_radius: with the analytic
        # Dirichlet wall the near-boundary region is no longer where the error
        # lives (measured 12.48% over 2a -> 0.4R vs 12.75% over 2a -> 0.8R at
        # h = 0.0025), and the wider window is the harder test.
        n_points = 10
        r_eval = np.linspace(2.0 * wire_radius, 0.8 * domain_radius, n_points)
        points = np.zeros((n_points, 3))
        points[:, 0] = r_eval
        points[:, 2] = 0.0

        # Analytical solution
        B_ana = AnalyticalSolutions.straight_wire_magnetic_field(points, current)
        B_ana_mag = np.linalg.norm(B_ana, axis=1)

        def wire_potential_interp(x):
            """Analytic wire A, dolfinx interpolation convention (3, n)."""
            pts = np.ascontiguousarray(x[:3].T)
            return AnalyticalSolutions.straight_wire_vector_potential(
                pts, current, wire_radius=wire_radius
            ).T

        import ufl

        for res in resolutions:
            if comm.rank == 0:
                print(f"\n  Testing resolution h = {res}...")

            # Generate mesh
            mesh, cell_tags, _ = MeshGenerator.straight_wire_domain(
                wire_length=wire_length,
                wire_radius=wire_radius,
                domain_radius=domain_radius,
                resolution=res,
                comm=comm
            )

            # Solve
            problem = MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0)
            solver = MagnetostaticSolver(problem, degree=1)

            wire_area = np.pi * wire_radius**2
            J_magnitude = current / wire_area

            def current_density(x):
                return ufl.as_vector([0.0, 0.0, J_magnitude])

            bc = exterior_dirichlet_bc(solver.V, wire_potential_interp)
            solver.solve(
                current_density=current_density, subdomain_id=1, bc_functions=[bc]
            )
            B = solver.compute_b_field()

            # Evaluate in the cells actually containing each point.
            B_num, valid = evaluate_vector_field_parallel(B, points, comm=comm)
            assert valid.all(), f"{(~valid).sum()}/{n_points} sample points outside mesh"
            B_num_mag = np.linalg.norm(B_num, axis=1)

            # Error
            rel_error = ErrorMetrics.l2_relative_error(B_num_mag, B_ana_mag)
            errors.append(rel_error)

            if comm.rank == 0:
                n_cells = mesh.topology.index_map(mesh.topology.dim).size_global
                print(f"    Cells: {n_cells}")
                print(f"    Relative L2 error: {rel_error:.4%}")

        # Compute convergence rate.
        # For error ~ C * h^p we have log(error) = log(C) + p*log(h), so the
        # rate is the slope of log(error) against log(h) -- positive when the
        # error shrinks with the mesh. An earlier revision negated this slope,
        # which reported a negative rate for genuinely convergent data and
        # tripped the assertion below.
        log_h = np.log(resolutions)
        log_err = np.log(errors)

        # Linear regression
        rate = np.sum((log_h - np.mean(log_h)) * (log_err - np.mean(log_err))) / np.sum((log_h - np.mean(log_h))**2)
        
        if comm.rank == 0:
            print(f"\n  Convergence Results:")
            print(f"    Resolutions (h): {resolutions}")
            print(f"    Errors: {[f'{e:.4%}' for e in errors]}")
            print(f"    Convergence rate: {rate:.2f}")
            print(f"    Expected rate for linear elements: ~1.0")

        # Two-sided bound (MAG-13 step 5). N1curl degree 1 predicts ~1.0 for
        # this quantity; the measured three-point fit over
        # h = 0.004 / 0.0025 / 0.0018 (22.19% -> 12.75% -> 9.26%) is **1.10**
        # (log 20260730T125522Z_MAG-13).
        # The upper bound matters as much as the lower one: a rate well above
        # 1.5 is not "better than expected" convergence but a sign that one
        # resolution in the sequence is anomalous (a mesh whose cells happen to
        # straddle the sample points favourably), which is exactly how the old
        # `rate > 0.5` check would have kept passing while the fixture drifted.
        assert 0.7 < rate < 1.5, (
            f"Convergence rate {rate:.2f} outside [0.7, 1.5] "
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
