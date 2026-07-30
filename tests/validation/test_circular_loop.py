"""
Validation test: Magnetic field of circular current loop.

This test validates the magnetostatic solver against the analytical
solution for B_z on the axis of a circular current loop.

Analytical solution on axis (z-axis):
    B_z(z) = μ₀Ia² / (2(a² + z²)^(3/2))  [Tesla]

Where:
    a = loop radius
    I = current
    z = distance along axis from loop center

The outer sphere carries the analytic vector potential as Dirichlet data
(MAG-13 step 4, ``exterior_dirichlet_bc`` + the Jackson 5.37 off-axis
``A_φ``). The natural condition ``n × H = 0`` is a PMC wall, i.e. a physical
statement about the truncation surface rather than a neutral one; for this
fixture it images the loop and biases the on-axis field at O((a/R_domain)³) ≈
3.7%. Measured, that bias is *not* the dominant error at the resolutions this
test can afford — see the table on ``test_circular_loop_on_axis`` — but the
Dirichlet wall is the condition whose continuum limit is the analytic field, so
it is what the fixture converges under.
"""

import pytest
import numpy as np
from mpi4py import MPI

import ufl

from fem_em_solver.core.solvers import (
    MagnetostaticProblem,
    MagnetostaticSolver,
    exterior_dirichlet_bc,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import AnalyticalSolutions, ErrorMetrics
from fem_em_solver.utils.constants import MU_0


def azimuthal_current_density(j_magnitude):
    """Return a UFL callable for uniform current circulating about the z-axis.

    A torus lying in the xy-plane carries azimuthal current. Earlier revisions
    of both tests in this module returned a z-directed vector, which drives no
    current around the loop: the on-axis field came out ~1000x too small
    (100.3% relative error against the analytic solution).
    """

    def current_density(x):
        rho = ufl.sqrt(x[0] ** 2 + x[1] ** 2)
        rho_safe = ufl.max_value(rho, 1e-12)
        return ufl.as_vector([
            -x[1] / rho_safe * j_magnitude,
            x[0] / rho_safe * j_magnitude,
            0.0,
        ])

    return current_density


def loop_potential_interp(current, loop_radius):
    """Analytic loop A in dolfinx interpolation convention (3, n) -> (3, n).

    ``utils.analytical`` uses the (n, 3) convention, so both ends transpose.
    The Jackson 5.37 form diverges on the wire itself (m -> 1), but only
    exterior-boundary dofs of the interpolant are constrained and the outer
    sphere is 3x the loop radius away, so the constrained values are smooth.
    """

    def field(x):
        points = np.ascontiguousarray(x[:3].T)
        return AnalyticalSolutions.circular_loop_vector_potential(
            points, current, loop_radius
        ).T

    return field


def solve_loop(params, comm, resolution=None, analytic_bc=True):
    """Mesh and solve the circular-loop problem; return (mesh, B)."""
    resolution = params['resolution'] if resolution is None else resolution
    mesh, cell_tags, _ = MeshGenerator.circular_loop_domain(
        loop_radius=params['loop_radius'],
        wire_radius=params['wire_radius'],
        domain_radius=params['domain_radius'],
        resolution=resolution,
        comm=comm,
    )

    problem = MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0)
    solver = MagnetostaticSolver(problem, degree=1)

    j_magnitude = params['current'] / (np.pi * params['wire_radius'] ** 2)
    bcs = None
    if analytic_bc:
        bcs = [
            exterior_dirichlet_bc(
                solver.V,
                loop_potential_interp(params['current'], params['loop_radius']),
            )
        ]

    solver.solve(
        current_density=azimuthal_current_density(j_magnitude),
        subdomain_id=1,
        bc_functions=bcs,
    )
    return mesh, solver.compute_b_field()


class TestCircularLoop:
    """Validation tests for circular current loop."""
    
    @pytest.fixture
    def loop_params(self):
        """Standard loop parameters.

        Sized to fit the runtime budget. The previous values (loop 0.05 m,
        wire 0.001 m, domain 0.15 m, h 0.005) meshed a 15 cm sphere at 5 mm --
        roughly 6e5 cells before the 1 mm wire forced further refinement -- and
        exhausted the container's 16 GB limit before completing. The test had
        therefore never run. See MAG-9.

        The wire is deliberately fat: sampling happens on the axis, far from the
        conductor, so wire thickness barely affects the on-axis field while
        making the geometry cheap to mesh.
        """
        return {
            'current': 1.0,           # 1 Ampere
            'loop_radius': 0.02,      # 2 cm radius
            'wire_radius': 0.003,     # 3 mm wire, resolvable at h below
            'domain_radius': 0.06,    # 6 cm domain (3x loop radius)
            'resolution': 0.0025,     # 2.5 mm mesh size
        }

    # Resolution for the analytic-comparison test. Finer than the fixture
    # default because the analytic Dirichlet wall costs accuracy at fixed h on
    # this geometry (see the table on test_circular_loop_on_axis); 0.002 is
    # what makes the 10% -> 8% tightening honest rather than a re-tuned bound.
    ON_AXIS_RESOLUTION = 0.002

    def test_circular_loop_on_axis(self, loop_params, tmp_path):
        """Test B_z on axis matches analytical solution.

        This test:
        1. Creates a torus mesh for the loop
        2. Solves magnetostatic problem with the analytic A on the outer sphere
        3. Extracts B_z along the z-axis
        4. Compares with analytical solution
        5. Checks that relative error is within tolerance

        Measured, `mpiexec -n 2`, on-axis B_z L2 error over |z| <= 0.4 R_domain
        (MAG-13 step 4; logs 20260730T124356Z / 124523Z / 124829Z
        _MAG-13-loop-probe*):

        | h      | cells | natural n x H = 0 | analytic Dirichlet |
        |--------|-------|-------------------|--------------------|
        | 0.0035 | 82.8k | 14.98%            | 16.23%             |
        | 0.0025 | 208k  |  8.86%            | 10.37%             |
        | 0.002  | 411k  | --                |  7.07%             |

        The analytic wall is ~20% *worse* at fixed h here, unlike the wire
        (35.13% -> 22.19%), and this is the chunk's real finding: the wire's
        natural-BC error is a contradiction of Ampere's law that no refinement
        removes, whereas the loop's is a PMC image term of order (a/R)^3 ~ 3.7%
        -- smaller than the O(h) error the degree-1 interpolation of A_phi
        injects through the boundary data itself. What the Dirichlet wall buys
        is the limit: it converges monotonically (16.23 -> 10.37 -> 7.07,
        fitted rate ~1.4) to the analytic field, while the natural wall
        converges to a field that differs from it. Do not swap back to the
        natural BC for the lower number at coarse h.
        """
        comm = MPI.COMM_WORLD

        # Parameters
        current = loop_params['current']
        loop_radius = loop_params['loop_radius']
        wire_radius = loop_params['wire_radius']
        domain_radius = loop_params['domain_radius']
        resolution = self.ON_AXIS_RESOLUTION

        print(f"\nCircular loop test:")
        print(f"  Loop radius: {loop_radius} m")
        print(f"  Wire radius: {wire_radius} m")
        print(f"  Current: {current} A")
        print(f"  Resolution: {resolution} m")

        print("  Meshing and solving (analytic Dirichlet outer boundary)...")
        mesh, B = solve_loop(
            loop_params, comm, resolution=resolution, analytic_bc=True
        )
        n_cells = mesh.topology.index_map(mesh.topology.dim).size_global
        print(f"  Mesh: {n_cells} cells")

        # Evaluate along the z-axis. The window stays at |z| <= 0.4 *
        # domain_radius, unchanged from the natural-BC revision of this test, so
        # the two walls are compared on the same metric -- widening it to 0.8 R
        # lowers the reported error (6.28% vs 7.07% at h=0.002) by adding
        # far-field points where B is small, which would make the tightened
        # bound below meaningless.
        n_points = 15
        z_max = 0.4 * domain_radius
        z_eval = np.linspace(-z_max, z_max, n_points)

        points = np.zeros((n_points, 3))
        points[:, 2] = z_eval  # z positions
        
        # Locate each point in the cell that actually contains it. Passing
        # np.arange(n) here evaluates in arbitrary cells and yields garbage.
        B_num, valid = evaluate_vector_field_parallel(B, points, comm=comm)
        assert valid.all(), f"{(~valid).sum()}/{n_points} sample points outside mesh"
        B_num_z = B_num[:, 2]  # z-component
        
        # Analytical solution
        B_ana_z = AnalyticalSolutions.circular_loop_magnetic_field_on_axis(
            z_eval, current, loop_radius
        )
        
        # Error metrics
        rel_error = ErrorMetrics.l2_relative_error(B_num_z, B_ana_z)
        max_error = ErrorMetrics.max_relative_error(B_num_z, B_ana_z)
        
        print(f"\n  Results:")
        print(f"    Max B_z (numerical): {np.max(np.abs(B_num_z)):.6e} T")
        print(f"    Max B_z (analytical): {np.max(np.abs(B_ana_z)):.6e} T")
        print(f"    Relative L2 error: {rel_error:.4%}")
        print(f"    Max relative error: {max_error:.4%}")
        
        # Bound set from measurement: 7.07% at h=0.002 with the analytic
        # Dirichlet wall (log 20260730T124829Z_MAG-13-loop-probe3). Tightened
        # from the previous 10%, which the natural-BC revision met at 8.86%.
        assert rel_error < 0.08, f"Relative error {rel_error:.4%} exceeds 8%"
    
    def test_circular_loop_field_symmetry(self, loop_params):
        """Test that B-field has expected symmetry.
        
        For a loop in xy-plane:
        - B_z should be maximum at center (z=0)
        - B_z should be symmetric about z=0
        - B_x and B_y should be zero on z-axis
        """
        comm = MPI.COMM_WORLD
        
        # Parameters
        current = loop_params['current']
        loop_radius = loop_params['loop_radius']

        # Same analytic Dirichlet wall as the on-axis test, at the cheaper
        # fixture resolution: this test's tolerances are set by the pointwise
        # sampling of a cell-wise constant curl(A), not by the boundary, so it
        # does not need h = 0.002.
        _, B = solve_loop(loop_params, comm, analytic_bc=True)

        # Evaluate at symmetric points
        z = 0.4 * loop_params['domain_radius']  # inside the perturbed boundary layer
        points = np.array([[0, 0, z], [0, 0, -z]])
        
        B_vals, valid = evaluate_vector_field_parallel(B, points, comm=comm)
        assert valid.all(), "symmetry probe points fell outside the mesh"
        
        # B_z should be the same at +z and -z. Compare relatively: gmsh does not
        # produce a mesh that is exactly mirror-symmetric about z=0, so the
        # discrete solution carries a small asymmetry. The previous absolute
        # bound of 1e-10 against values of order 1e-5 demanded ~1e-5 relative
        # agreement, which no unstructured mesh will deliver.
        b_scale = max(abs(B_vals[0, 2]), abs(B_vals[1, 2]), 1e-30)
        rel_asymmetry = abs(B_vals[0, 2] - B_vals[1, 2]) / b_scale

        # Tolerance is set by discretization, not by the physics. With N1curl
        # degree 1, curl(A) is constant per cell, so the +z and -z probes read
        # whichever cell contains them; on a mesh that is not mirror-symmetric
        # those are different cells. The expected noise is O(h/z) =
        # 0.0025/0.024 ~ 10%, and 12.6% is measured. 20% leaves modest headroom
        # without hiding a real failure -- a wrong current direction showed up
        # here as ~88%, and a sign or geometry error would be far larger still.
        assert rel_asymmetry < 0.20, (
            f"B_z not symmetric: {B_vals[0, 2]:.6e} vs {B_vals[1, 2]:.6e} "
            f"({rel_asymmetry:.2%} relative)"
        )

        # Stronger check than symmetry alone: both probes should sit near the
        # analytic on-axis value at |z|.
        b_ana = AnalyticalSolutions.circular_loop_magnetic_field_on_axis(
            np.array([z]), current, loop_radius
        )[0]
        for label, value in (("+z", B_vals[0, 2]), ("-z", B_vals[1, 2])):
            rel = abs(value - b_ana) / abs(b_ana)
            assert rel < 0.25, (
                f"B_z at {label} disagrees with analytic: {value:.6e} vs "
                f"{b_ana:.6e} ({rel:.2%})"
            )
        
        # B_x and B_y should be zero (or very small) on axis
        assert np.abs(B_vals[0, 0]) < 1e-6, "B_x should be zero on axis"
        assert np.abs(B_vals[0, 1]) < 1e-6, "B_y should be zero on axis"


def test_analytical_circular_loop():
    """Unit test for analytical solution calculation."""
    current = 1.0  # A
    radius = 0.05  # m (5 cm)
    
    # Test at z = 0 (center)
    z = np.array([0.0])
    B_z = AnalyticalSolutions.circular_loop_magnetic_field_on_axis(z, current, radius)
    
    # Expected: B_z(0) = μ₀I / (2a)
    expected = MU_0 * current / (2 * radius)
    
    assert np.abs(B_z[0] - expected) < 1e-10, f"B_z(0) incorrect: got {B_z[0]}, expected {expected}"
    
    # Test at z = a (one radius away)
    z = np.array([radius])
    B_z = AnalyticalSolutions.circular_loop_magnetic_field_on_axis(z, current, radius)
    
    # B_z(z) = mu_0*I*a^2 / (2*(a^2+z^2)^(3/2)), so at z = a:
    #   = mu_0*I*a^2 / (2*(2a^2)^(3/2)) = mu_0*I / (2 * 2*sqrt(2) * a)
    #   = mu_0*I / (4*sqrt(2)*a)
    # An earlier revision expected mu_0*I/(2*sqrt(2)*a), which is 2x too large;
    # the implementation was correct. This went unnoticed because the whole
    # module was unrunnable (its mesh exhausted memory before collection).
    expected = MU_0 * current / (4 * np.sqrt(2) * radius)
    
    assert np.abs(B_z[0] - expected) < 1e-10, f"B_z(a) incorrect: got {B_z[0]}, expected {expected}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
