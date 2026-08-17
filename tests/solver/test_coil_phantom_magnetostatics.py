"""Magnetostatic solve test on the coil+phantom mesh.

`OPS-17` step 2 (2026-08-17). This file was the step-1 table's *archetype* of
the finiteness-only pattern: solve, then assert ``isfinite`` and ``|B|`` above a
nontrivial-magnitude floor. It is now gated against the closed form the table
named — on-axis ``B_z`` from the Biot–Savart superposition of the two coil
loops, ``B_z(z) = sum_loops mu_0 I a^2 / (2 (a^2 + (z-z0)^2)^(3/2))``.

Two defects in the old fixture had to be fixed before that comparison could
mean anything, and both are findings in their own right:

1. **The source drove no loop current.** The current density was
   ``(0, 0, J)`` over the two *toroidal* coil tags. A torus lying in the
   xy-plane carries azimuthal current; a z-directed J drives essentially none
   of it, and ``tests/validation/test_circular_loop.py`` records the same
   mistake costing a factor of ~1000 in the on-axis field (100.3% relative
   error). Replaced with the azimuthal pattern that module already defines.
2. **The outer wall was left natural.** ``n x (mu^-1 curl A) = 0`` is a PMC
   image condition, and the box wall here sits at only ~1.6x the coil radius,
   so the image term is not small (`MAG-13`). The analytic two-loop A is now
   imposed on the exterior, which is what makes the discrete problem converge
   to the analytic field rather than to a different one.

The band is **pre-stated from the `MAG-13` measurements, not fitted to a run.**
``test_circular_loop`` measures 7.07% / 10.37% / 16.23% on-axis L2 error at
wire-radius-to-h ratios of 1.5 / 1.2 / 0.86 with this same wall. This fixture's
coil minor radius is 0.01 m at h = 0.015 m — a ratio of 0.67, coarser than
every rung in that table — so 30% is the honest ceiling to pre-state here, and
it still excludes everything the old nontrivial-magnitude floor admitted (which
the z-directed source passed while being ~1000x low). The tight gate on this
closed form lives in ``test_circular_loop``; this is the cross-check that the
coil+phantom mesh path reaches the same physics.
"""

import numpy as np
from mpi4py import MPI

from fem_em_solver.core.solvers import (
    MagnetostaticProblem,
    MagnetostaticSolver,
    exterior_dirichlet_bc,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import AnalyticalSolutions, ErrorMetrics
from fem_em_solver.utils.constants import MU_0

from tests.validation.test_circular_loop import azimuthal_current_density

COIL_MAJOR_RADIUS = 0.08
COIL_MINOR_RADIUS = 0.01
COIL_SEPARATION = 0.08
PHANTOM_RADIUS = 0.04
PHANTOM_HEIGHT = 0.10
AIR_PADDING = 0.04
RESOLUTION = 0.015
COIL_CURRENT = 1.0  # A per loop

# The two loops sit at z = +/- separation/2.
LOOP_CENTERS = (-0.5 * COIL_SEPARATION, +0.5 * COIL_SEPARATION)

# Sampling window on the axis, inside the phantom (half-height 0.05 m).
N_AXIS_POINTS = 9
Z_MAX = 0.03

# See the module docstring: pre-stated from the MAG-13 resolution table.
ON_AXIS_L2_ERROR_MAX = 0.30


def _two_loop_potential_interp(x):
    """Analytic A of the loop pair, dolfinx convention (3, n) -> (3, n)."""
    points = np.ascontiguousarray(x[:3].T)
    a = np.zeros_like(points)
    for z0 in LOOP_CENTERS:
        a += AnalyticalSolutions.circular_loop_vector_potential(
            points, COIL_CURRENT, COIL_MAJOR_RADIUS, loop_center=z0
        )
    return a.T


def _two_loop_b_z_on_axis(z):
    """Biot-Savart superposition of the pair, on the axis."""
    b_z = np.zeros_like(np.asarray(z, dtype=np.float64))
    for z0 in LOOP_CENTERS:
        b_z += AnalyticalSolutions.circular_loop_magnetic_field_on_axis(
            z, COIL_CURRENT, COIL_MAJOR_RADIUS, loop_center=z0
        )
    return b_z


def test_coil_phantom_magnetostatics_matches_the_two_loop_closed_form():
    """Solve with azimuthal current on the coil tags; B_z on axis vs Biot-Savart."""
    comm = MPI.COMM_WORLD

    mesh, cell_tags, facet_tags = MeshGenerator.coil_phantom_domain(
        coil_major_radius=COIL_MAJOR_RADIUS,
        coil_minor_radius=COIL_MINOR_RADIUS,
        coil_separation=COIL_SEPARATION,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        air_padding=AIR_PADDING,
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

    # Uniform azimuthal J over each torus cross-section carrying COIL_CURRENT.
    j_magnitude = COIL_CURRENT / (np.pi * COIL_MINOR_RADIUS**2)
    bcs = [exterior_dirichlet_bc(solver.V, _two_loop_potential_interp)]
    solver.solve(
        current_density=azimuthal_current_density(j_magnitude),
        subdomain_ids=[1, 2],
        gauge_penalty=1e-3,
        bc_functions=bcs,
    )
    b_field = solver.compute_b_field()

    # Point evaluation goes through the parallel helper, never f.eval with
    # np.arange(n) — that evaluates in arbitrary cells.
    z_eval = np.linspace(-Z_MAX, Z_MAX, N_AXIS_POINTS)
    points = np.zeros((N_AXIS_POINTS, 3))
    points[:, 2] = z_eval

    b_num, valid = evaluate_vector_field_parallel(b_field, points, comm=comm)
    assert valid.all(), (
        f"{(~valid).sum()}/{N_AXIS_POINTS} on-axis sample points outside mesh"
    )

    b_num_z = b_num[:, 2]
    b_ana_z = _two_loop_b_z_on_axis(z_eval)
    rel_error = ErrorMetrics.l2_relative_error(b_num_z, b_ana_z)

    if comm.rank == 0:
        n_cells = mesh.topology.index_map(mesh.topology.dim).size_global
        print(f"\n[OPS-17] coil+phantom on-axis B_z, {n_cells} cells at "
              f"h={RESOLUTION} m:")
        for z, bn, ba in zip(z_eval, b_num_z, b_ana_z):
            print(f"    z = {z:+.4f} m: B_z = {bn:+.6e} T vs {ba:+.6e} T "
                  f"({bn / ba - 1.0:+.2%})")
        print(f"    L2 relative error: {rel_error:.4%}", flush=True)

    assert rel_error < ON_AXIS_L2_ERROR_MAX, (
        f"on-axis B_z is {rel_error:.4%} from the two-loop Biot-Savart "
        f"superposition, outside the pre-stated {ON_AXIS_L2_ERROR_MAX:.0%} "
        f"band; sampled over |z| <= {Z_MAX} m at h = {RESOLUTION} m"
    )
