"""Solver test on cylindrical two-volume mesh.

`OPS-17` step 2 (2026-08-17) replaced this file's finiteness-only assertions
(``isfinite`` plus a weak nontrivial-magnitude floor) with the closed form the
step-1 table named: the infinite-straight-wire field ``B_phi = mu_0 I/(2 pi r)``
sampled at the mid-length plane, exactly as
``tests/validation/test_straight_wire.py`` gates it.

Two changes to the fixture were needed for that comparison to mean anything,
both carried over from `MAG-13` and stated here rather than tuned afterwards:

1. The geometry moves to the straight-wire proportions (conductor radius
   0.003 m in a 0.03 m domain, 0.2 m long, h = 0.0025 m). At the previous
   ``inner_radius=0.01`` with ``resolution=0.03`` the conductor was a third of
   one cell across — no closed form is recoverable from that mesh.
2. The outer wall carries the analytic potential as Dirichlet data. The
   natural condition ``n x (mu^-1 curl A) = 0`` forces the azimuthal H to zero
   on the outer cylinder, which is the component being compared and
   contradicts Ampere's law for a net axial current (`MAG-13`); without the BC
   this test would be gating a known-wrong boundary treatment.

The band is **pre-stated, not fitted**: ``test_straight_wire`` measures 12.48%
L2 relative error over 2a -> 0.4R at this h on its own mesh, so 25% here
leaves a factor of two of headroom for the different mesher path while still
excluding everything the old floor admitted. The tight gate on this closed
form lives in ``test_straight_wire``; this is the cheap cross-check that the
cylindrical mesh path reaches the same physics.
"""

import numpy as np
import ufl
from mpi4py import MPI

from fem_em_solver.core.solvers import (
    MagnetostaticProblem,
    MagnetostaticSolver,
    exterior_dirichlet_bc,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import AnalyticalSolutions, ErrorMetrics
from fem_em_solver.utils.constants import MU_0

INNER_RADIUS = 0.003
OUTER_RADIUS = 0.03
LENGTH = 0.20
RESOLUTION = 0.0025
CURRENT = 1.0

# Sample outside the conductor and inside the region the outer wall perturbs.
R_MIN = 2.0 * INNER_RADIUS
R_MAX = 0.4 * OUTER_RADIUS
N_POINTS = 8

# See the module docstring: pre-stated with headroom over the 12.48% that
# test_straight_wire measures at this h, never fitted to a run.
L2_ERROR_MAX = 0.25


def _wire_potential_interp(x):
    """Analytic wire A in dolfinx interpolation convention (3, n) -> (3, n)."""
    points = np.ascontiguousarray(x[:3].T)
    A = AnalyticalSolutions.straight_wire_vector_potential(
        points, CURRENT, wire_radius=INNER_RADIUS
    )
    return A.T


def test_cylinder_solver_b_field_matches_the_straight_wire_closed_form():
    """Solve on the cylindrical mesh; |B| matches mu_0 I / (2 pi r)."""
    comm = MPI.COMM_WORLD
    mesh, cell_tags, facet_tags = MeshGenerator.cylindrical_domain(
        inner_radius=INNER_RADIUS,
        outer_radius=OUTER_RADIUS,
        length=LENGTH,
        resolution=RESOLUTION,
        comm=comm,
    )

    problem = MagnetostaticProblem(
        mesh=mesh,
        cell_tags=cell_tags,
        facet_tags=facet_tags,
        mu=MU_0,
    )
    solver = MagnetostaticSolver(problem, degree=1)

    # Uniform J over the inner cylinder (tag 1) carrying CURRENT in total.
    j_magnitude = CURRENT / (np.pi * INNER_RADIUS**2)

    def current_density(x):
        return ufl.as_vector([0.0, 0.0, j_magnitude])

    bcs = [exterior_dirichlet_bc(solver.V, _wire_potential_interp)]
    solver.solve(current_density=current_density, subdomain_id=1, bc_functions=bcs)
    b_field = solver.compute_b_field()

    # Point evaluation goes through the parallel helper: f.eval with
    # np.arange(n) evaluates in arbitrary cells and returns meaningless values.
    r_test = np.linspace(R_MIN, R_MAX, N_POINTS)
    points = np.zeros((N_POINTS, 3))
    points[:, 0] = r_test  # +x at the mid-length plane z = 0
    values, valid = evaluate_vector_field_parallel(b_field, points, comm=comm)
    assert valid.all(), f"{(~valid).sum()}/{N_POINTS} sample points outside mesh"

    b_num_mag = np.linalg.norm(values, axis=1)
    b_ana = AnalyticalSolutions.straight_wire_magnetic_field(points, CURRENT)
    b_ana_mag = np.linalg.norm(b_ana, axis=1)
    err = ErrorMetrics.l2_relative_error(b_num_mag, b_ana_mag)

    if comm.rank == 0:
        print(f"\n[OPS-17] cylindrical-mesh straight-wire cross-check at "
              f"h={RESOLUTION} m:")
        for r, bn, ba in zip(r_test, b_num_mag, b_ana_mag):
            print(f"    r = {r:.4f} m: |B| = {bn:.6e} T vs {ba:.6e} T "
                  f"({bn / ba - 1.0:+.2%})")
        print(f"    L2 relative error: {err:.4%}", flush=True)

    assert err < L2_ERROR_MAX, (
        f"|B| on the cylindrical mesh is {err:.4%} from mu_0 I/(2 pi r), "
        f"outside the pre-stated {L2_ERROR_MAX:.0%} band; sampled over "
        f"r in [{R_MIN:.4f}, {R_MAX:.4f}] m at h = {RESOLUTION} m"
    )
