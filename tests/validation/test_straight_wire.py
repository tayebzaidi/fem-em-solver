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
3. The outer wall carries the analytic potential as Dirichlet data (MAG-13).
   The natural condition ``n x (mu^-1 curl A) = 0`` means ``n x H = 0``, which
   on the outer cylinder forces the azimuthal H to zero -- exactly the
   component being compared -- and contradicts Ampere's law for a net axial
   current. That is a modeling error no refinement removes; it was previously
   hidden by sampling only at r <= 0.4 * domain_radius. Imposing
   ``A_z = -mu_0 I/(2 pi) ln(r/a)`` on the exterior instead makes the continuum
   limit the analytic field, lets sampling run back out to 0.8 * domain_radius,
   and restores clean O(h^1.2) convergence (22.19% -> 12.75% -> 9.26% at
   h = 0.004 / 0.0025 / 0.0018).

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

from fem_em_solver.core.solvers import (
    MagnetostaticProblem,
    MagnetostaticSolver,
    exterior_dirichlet_bc,
)
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

# With the analytic Dirichlet BC of MAG-13 the outer wall no longer forces
# H_phi = 0, so samples may run out to it. Measured at h=0.0025: 12.48% over
# 2a -> 0.4R vs 12.75% over 2a -> 0.8R, i.e. the near-boundary region is no
# longer where the error lives.
R_MAX_BC = 0.8 * DOMAIN_RADIUS


def _wire_potential_interp(x):
    """Analytic wire A in dolfinx interpolation convention (3, n) -> (3, n).

    The finite-conductor branch is required: the domain end caps of
    ``straight_wire_domain`` cross r = 0, where the filament ln r diverges.
    """
    points = np.ascontiguousarray(x[:3].T)
    A = AnalyticalSolutions.straight_wire_vector_potential(
        points, CURRENT, wire_radius=WIRE_RADIUS
    )
    return A.T


def _solve_straight_wire(resolution, comm, analytic_bc=True):
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

    bcs = [exterior_dirichlet_bc(solver.V, _wire_potential_interp)] if analytic_bc else None
    solver.solve(current_density=current_density, subdomain_id=1, bc_functions=bcs)
    return mesh, solver.compute_b_field()


def _sample_radial(b_field, n_points, comm, r_min=R_MIN, r_max=R_MAX):
    """Return (r, |B|_numeric, |B|_analytic) along +x at the wire midplane."""
    r_test = np.linspace(r_min, r_max, n_points)
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
        r_test, b_num_mag, b_ana_mag, values = _sample_radial(
            b_field, n_points, comm, R_MIN, R_MAX_BC
        )

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
            print(f"  Sampling r: {R_MIN:.4f} -> {R_MAX_BC:.4f} m "
                  f"(a={WIRE_RADIUS}, R_domain={DOMAIN_RADIUS})")
            print(f"  Relative L2 error: {rel_error:.4%}")
            for r, bn, ba in zip(r_test, b_num_mag, b_ana_mag):
                print(f"    r={r:.4f}  |B|_num={bn:.4e}  |B|_ana={ba:.4e}  "
                      f"rel={abs(bn - ba) / ba:.2%}")

        # Bound set from measurement (MAG-13, log 20260730T034614Z_MAG-13-probe2),
        # analytic Dirichlet BC, sampling 2a -> 0.8 R_domain, mpiexec -n 2:
        #   h=0.004   38.8k cells   22.19%
        #   h=0.0025  145.9k cells  12.75%   <- this test
        #   h=0.0018  383.2k cells   9.26%
        # i.e. O(h^1.2), still converging: there is no plateau left to hit, which
        # is the point of the BC. With the natural n x H = 0 wall the same meshes
        # give 35.13% at h=0.004 (see test_analytic_bc_improves_on_natural_bc) and
        # the error stops responding to refinement.
        # Reaching the < 5% target needs h ~ 0.00125 (~1.1M cells, > 5 min at
        # -n 2), which is outside the standard tier; the remaining error is
        # discretization of a 1/r field on a uniform mesh near a thin conductor,
        # so graded refinement (MAG-9) is the cheaper route, not more uniform h.
        assert rel_error < 0.15, f"Relative error {rel_error:.4%} exceeds 15%"

    def test_analytic_bc_improves_on_natural_bc(self):
        """The analytic Dirichlet wall beats n x H = 0 on the same mesh.

        This is the MAG-13 claim stated as a test: the natural condition
        ``n x H = 0`` on the outer cylinder contradicts Ampere's law for a net
        axial current, so it is a modeling error, not a discretization one, and
        removing it must lower the error at fixed h. Run at the coarse
        resolution so both solves fit the smoke budget.
        """
        comm = MPI.COMM_WORLD
        res = 0.004
        n_points = 10
        errors = {}

        for use_bc in (False, True):
            _, b_field = _solve_straight_wire(res, comm, analytic_bc=use_bc)
            _, b_num_mag, b_ana_mag, _ = _sample_radial(
                b_field, n_points, comm, R_MIN, R_MAX_BC
            )
            errors[use_bc] = ErrorMetrics.l2_relative_error(b_num_mag, b_ana_mag)

        if comm.rank == 0:
            print(f"\n  h={res}: natural BC {errors[False]:.4%}, "
                  f"analytic BC {errors[True]:.4%}")

        # Measured at h=0.004, -n 2 (log 20260730T034541Z_MAG-13-probe):
        # 35.13% natural -> 22.19% analytic, a factor 0.63. The 0.85 bound
        # leaves room for mesh-partition noise while still failing if the BC
        # stops being applied at all.
        assert errors[True] < 0.85 * errors[False], (
            f"Analytic BC {errors[True]:.4%} should beat natural BC "
            f"{errors[False]:.4%} at h={res}"
        )

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
