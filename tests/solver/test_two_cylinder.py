"""Solver test on two-cylinder mesh with current in both cylinders."""

import numpy as np
import ufl
from mpi4py import MPI

from fem_em_solver.core.solvers import MagnetostaticProblem, MagnetostaticSolver
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.constants import MU_0

from tests.tolerances import (
    B_FIELD_MAX_NONTRIVIAL_ABS_MIN,
    CENTERLINE_CV_MAX,
    FIELD_STD_NEAR_ZERO_MAX,
)


def test_two_cylinder_solver_centerline_field_is_roughly_constant():
    """Apply current in both cylinders and check centerline B-field behavior."""
    separation = 0.05
    radius = 0.01
    length = 0.1

    mesh, cell_tags, facet_tags = MeshGenerator.two_cylinder_domain(
        separation=separation,
        radius=radius,
        length=length,
        resolution=0.02,
        comm=MPI.COMM_WORLD,
    )

    problem = MagnetostaticProblem(
        mesh=mesh,
        cell_tags=cell_tags,
        facet_tags=facet_tags,
        mu=MU_0,
    )
    solver = MagnetostaticSolver(problem, degree=1)

    x_offset = separation / 2

    def current_density(x):
        in_cyl_1 = ufl.And(
            (x[0] + x_offset) ** 2 + x[1] ** 2 <= radius**2,
            abs(x[2]) <= length / 2,
        )
        in_cyl_2 = ufl.And(
            (x[0] - x_offset) ** 2 + x[1] ** 2 <= radius**2,
            abs(x[2]) <= length / 2,
        )

        in_any_cyl = ufl.Or(in_cyl_1, in_cyl_2)
        jz = ufl.conditional(in_any_cyl, 1.0, 0.0)
        return ufl.as_vector([0.0, 0.0, jz])

    solver.solve(current_density=current_density)
    b_field = solver.compute_b_field()

    b_values = np.asarray(b_field.x.array)
    assert np.isfinite(b_values).all(), "B-field contains non-finite values"

    # Non-triviality is asserted below on *located* field samples rather than on
    # raw DOF values. max|b_field.x.array| is the largest coefficient anywhere in
    # the mesh, including cells where the gauge-regularised gradient component of
    # A leaves a large spurious curl; that quantity scales as 1/gauge_penalty and
    # says nothing about the physical field. Probed properly, B is
    # gauge-independent for penalties >= 1e-3 (measured 1.009e-9, 9.978e-10,
    # 9.978e-10 T at 1e-3, 1e0, 1e3). Asserting on the raw array made this test
    # a function of the regularisation parameter -- it began failing purely
    # because MAG-10 corrected the gauge default. Same defect family as MAG-7:
    # never read fields out of a DOF array when you mean a value at a point.

    # Check B-field along centerline (x=0, y=0, varying z)
    n_points = 11
    z_eval = np.linspace(-0.02, 0.02, n_points)
    points = np.zeros((n_points, 3))
    points[:, 2] = z_eval

    # Evaluate in the cells actually containing each point.
    b_center, valid = evaluate_vector_field_parallel(b_field, points)
    assert valid.all(), f"{(~valid).sum()}/{n_points} centerline points outside mesh"
    b_mag = np.linalg.norm(b_center, axis=1)

    # Non-triviality, probed outboard of cylinder 1 where the field is strong.
    # The centerline is a poor place for this: both conductors carry current in
    # the same direction, so their contributions oppose at x=0.
    probe = np.array([[-x_offset - 2.0 * radius, 0.0, 0.0]])
    b_probe, probe_valid = evaluate_vector_field_parallel(b_field, probe)
    assert probe_valid.all(), "non-triviality probe point fell outside the mesh"
    b_probe_mag = float(np.linalg.norm(b_probe[0]))
    assert b_probe_mag > B_FIELD_MAX_NONTRIVIAL_ABS_MIN, (
        f"B-field should be non-zero outboard of the conductor, got {b_probe_mag:.3e} T"
    )

    mean_mag = float(np.mean(b_mag))
    std_mag = float(np.std(b_mag))

    # "Roughly constant" criterion in the center region
    if mean_mag > 0:
        cv = std_mag / mean_mag
        assert cv < CENTERLINE_CV_MAX, f"Centerline B-field not roughly constant (CV={cv:.3f})"
    else:
        assert std_mag < FIELD_STD_NEAR_ZERO_MAX, "Centerline B-field magnitude varies unexpectedly"
