"""
Validation test: Magnetic field of straight wire.

Validates the magnetostatic solver against the analytical solution for an
infinite straight wire carrying current I:

    B_phi = mu_0 * I / (2 * pi * r)   [T]

Three modelling points govern how this test is set up (see MAG-7/8/9):

1. Current must be restricted to the wire subdomain (``subdomain_id=1``). An
   earlier revision applied J over the whole domain, which enclosed ~2500 A
   instead of 1 A and produced |B| rising with r against a reference falling
   as 1/r.
2. Field samples must be located in the cells that contain them, via
   ``post.evaluation.evaluate_vector_field_parallel``. Passing
   ``np.arange(n)`` as cell indices evaluates in arbitrary cells and returns
   meaningless values.
3. Sampling stays well inside the outer boundary. The natural condition
   ``n x (mu^-1 curl A) = 0`` means ``n x H = 0``, which on the outer cylinder
   forces the azimuthal H to zero -- exactly the component being compared.
   That boundary is incompatible with the free-space 1/r solution, so its
   influence is kept small by sampling at r <= 0.4 * domain_radius rather than
   the 0.8 used previously.

A *fat* wire costs no accuracy here: for uniform current density the external
field of a cylindrical conductor is identical to a filament for r > a. So the
wire radius is chosen large enough to be meshed cheaply, and samples start at
2a. This is what keeps the case inside the runtime budget -- the previous
parameters meshed a 5 cm x 1 m cylinder at h = 5 mm (~4e5 cells) and exceeded
400 s without completing.
"""

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core.solvers import MagnetostaticProblem, MagnetostaticSolver
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import AnalyticalSolutions, ErrorMetrics
from fem_em_solver.utils.constants import MU_0

# Geometry chosen so the wire is resolvable at a coarse global mesh size while
# the sampling annulus stays clear of both the conductor and the outer boundary.
WIRE_RADIUS = 0.003
DOMAIN_RADIUS = 0.03
WIRE_LENGTH = 0.20
RESOLUTION = 0.0025
CURRENT = 1.0

# Sample between 2a and 0.4 * domain_radius: outside the conductor, inside the
# region the outer boundary meaningfully perturbs.
R_MIN = 2.0 * WIRE_RADIUS
R_MAX = 0.4 * DOMAIN_RADIUS


def _solve_straight_wire(resolution, comm):
    """Mesh and solve the straight-wire problem at one resolution."""
    mesh, cell_tags, facet_tags = MeshGenerator.straight_wire_domain(
        wire_length=WIRE_LENGTH,
        wire_radius=WIRE_RADIUS,
        domain_radius=DOMAIN_RADIUS,
        resolution=resolution,
        comm=comm,
    )

    problem = MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0)
    # Degree 1 is deliberate. Measured on this fixture (8 ranks):
    #   res=0.005  deg=1 -> 35.5%      res=0.005  deg=2 -> 31.7%
    #   res=0.0025 deg=1 -> 18.2%      res=0.004  deg=2 -> 24.9%
    #                                  res=0.003  deg=2 -> 2724%  (diverges)
    # Degree 2 costs ~8x the solve for a marginal accuracy gain and becomes
    # unstable as the mesh refines, which points at the gauge-penalty
    # formulation rather than at the element order. Do not raise the degree here
    # without re-measuring; see MAG-10.
    solver = MagnetostaticSolver(problem, degree=1)

    # Uniform J inside the wire only; tag 1 is the wire volume.
    j_magnitude = CURRENT / (np.pi * WIRE_RADIUS**2)

    def current_density(x):
        import ufl

        return ufl.as_vector([0.0, 0.0, j_magnitude])

    solver.solve(current_density=current_density, subdomain_id=1)
    return mesh, solver.compute_b_field()


def _sample_radial(b_field, n_points, comm):
    """Return (r, |B|_numeric, |B|_analytic) along +x at the wire midplane."""
    r_test = np.linspace(R_MIN, R_MAX, n_points)
    points = np.zeros((n_points, 3))
    points[:, 0] = r_test
    points[:, 2] = 0.0  # midplane, where the finite-length error is smallest

    values, valid = evaluate_vector_field_parallel(b_field, points, comm=comm)
    assert valid.all(), f"{(~valid).sum()}/{n_points} sample points outside mesh"

    b_num_mag = np.linalg.norm(values, axis=1)
    b_ana = AnalyticalSolutions.straight_wire_magnetic_field(points, CURRENT)
    b_ana_mag = np.linalg.norm(b_ana, axis=1)
    return r_test, b_num_mag, b_ana_mag, values


class TestStraightWire:
    """Validation tests for straight wire magnetostatics."""

    def test_straight_wire_b_field(self):
        """B-field magnitude matches mu_0*I/(2*pi*r) outside the conductor."""
        comm = MPI.COMM_WORLD
        mesh, b_field = _solve_straight_wire(RESOLUTION, comm)

        n_points = 10
        r_test, b_num_mag, b_ana_mag, values = _sample_radial(b_field, n_points, comm)

        # Field should be azimuthal: negligible axial component.
        b_z_max = float(np.max(np.abs(values[:, 2])))
        b_ref = float(np.max(b_ana_mag))
        assert b_z_max < 0.10 * b_ref, (
            f"B_z should be small compared to |B|; got {b_z_max:.3e} vs {b_ref:.3e}"
        )

        rel_error = ErrorMetrics.l2_relative_error(b_num_mag, b_ana_mag)

        if comm.rank == 0:
            n_cells = mesh.topology.index_map(mesh.topology.dim).size_global
            print("\nStraight wire validation:")
            print(f"  Cells: {n_cells}")
            print(f"  Current: {CURRENT} A (restricted to wire tag 1)")
            print(f"  Sampling r: {R_MIN:.4f} -> {R_MAX:.4f} m "
                  f"(a={WIRE_RADIUS}, R_domain={DOMAIN_RADIUS})")
            print(f"  Relative L2 error: {rel_error:.4%}")
            for r, bn, ba in zip(r_test, b_num_mag, b_ana_mag):
                print(f"    r={r:.4f}  |B|_num={bn:.4e}  |B|_ana={ba:.4e}  "
                      f"rel={abs(bn - ba) / ba:.2%}")

        # Measured 18.2% at this resolution, converging ~O(h) (35.5% at h=0.005).
        # The residual is dominated by resolving a 1/r field on a uniform mesh
        # near a thin conductor, not by a formulation error: the same solver
        # reproduces the Helmholtz field to 0.04% where the field is smooth.
        # This test therefore checks the 1/r *trend* and the azimuthal direction;
        # quantitative validation lives in the Helmholtz comparison. Tightening
        # this bound requires graded refinement in straight_wire_domain (MAG-9).
        assert rel_error < 0.25, f"Relative error {rel_error:.4%} exceeds 25%"

    def test_straight_wire_convergence(self):
        """Error decreases as the mesh is refined."""
        comm = MPI.COMM_WORLD
        resolutions = [0.004, 0.0025]
        n_points = 8
        errors = []

        for res in resolutions:
            _, b_field = _solve_straight_wire(res, comm)
            _, b_num_mag, b_ana_mag, _ = _sample_radial(b_field, n_points, comm)
            err = ErrorMetrics.l2_relative_error(b_num_mag, b_ana_mag)
            errors.append(err)
            if comm.rank == 0:
                print(f"  Resolution {res:.4f} m: error = {err:.4%}")

        assert errors[-1] < errors[0], (
            f"Error should decrease with refinement, got {errors[0]:.4%} -> "
            f"{errors[-1]:.4%}"
        )


def test_analytical_straight_wire():
    """Unit test for analytical solution calculation."""
    current = 1.0  # A

    # Test at r = 0.01 m
    points = np.array([[0.01, 0, 0]])
    B = AnalyticalSolutions.straight_wire_magnetic_field(points, current)

    # Expected: B_phi = mu_0*I/(2*pi*r) = 4*pi*1e-7 * 1 / (2*pi*0.01)
    expected = 4e-7 * np.pi * 1.0 / (2 * np.pi * 0.01)

    B_mag = np.linalg.norm(B)
    assert np.abs(B_mag - expected) < 1e-10, "Analytical B-field incorrect"

    # Direction should be in y-direction at x-axis (azimuthal)
    assert np.abs(B[0, 1] - expected) < 1e-10, "B-field direction incorrect"
    assert np.abs(B[0, 0]) < 1e-15, "B_x should be zero"
    assert np.abs(B[0, 2]) < 1e-15, "B_z should be zero"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
