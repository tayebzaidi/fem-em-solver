"""
Example: Magnetic field of a circular current loop.

This example demonstrates the magnetostatic solver for a circular loop
coil and compares the on-axis B-field with the analytical solution.
"""

import numpy as np
from mpi4py import MPI
from pathlib import Path

from fem_em_solver.core.solvers import (
    MagnetostaticSolver,
    MagnetostaticProblem,
    exterior_dirichlet_bc,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import AnalyticalSolutions, ErrorMetrics
from fem_em_solver.utils.constants import MU_0
from fem_em_solver.io.paraview_utils import write_combined_paraview_output

# Import dolfinx I/O for ParaView output
from dolfinx import io, fem


#: EX-17 anchor (ported from EX-14): the ADIOS2 round trip is exact, so the
#: written artifact must reproduce the in-memory global max |B| to round-off.
#: This is a closed-loop identity on the file itself, not a finiteness check.
VTX_ROUNDTRIP_RTOL = 1e-10


def _global_max_magnitude(f, V, comm):
    """Allreduced max |f| over owned dofs (rank-local maxima are not the answer)."""
    n_owned = V.dofmap.index_map.size_local * V.dofmap.index_map_bs
    owned = f.x.array[:n_owned].reshape(-1, 3)
    local = float(np.max(np.linalg.norm(owned, axis=1))) if owned.size else 0.0
    return comm.allreduce(local, op=MPI.MAX)


def _check_vtx_roundtrip(bp_path, B_lag, V_lag, comm):
    """Read the written .bp back through ADIOS2 and compare max |B| (EX-17).

    The writer is collective; the read-back is done on rank 0 only (the BP file
    holds the *global* array) and the verdict is broadcast, so every rank
    raises or none does.
    """
    in_memory = _global_max_magnitude(B_lag, V_lag, comm)
    comm.Barrier()

    readback = None
    failure = None
    if comm.rank == 0:
        try:
            import adios2

            adios = adios2.ADIOS()
            reader_io = adios.DeclareIO("ex17_vtx_readback")
            reader_io.SetEngine("BP4")
            engine = reader_io.Open(str(bp_path), adios2.Mode.ReadRandomAccess)
            try:
                available = reader_io.AvailableVariables()
                if "B" not in available:
                    raise RuntimeError(
                        f"no 'B' variable in {bp_path.name}; found {sorted(available)}"
                    )
                # VTX writes point data as an ADIOS2 *local* array -- one block
                # per writer rank, no global shape -- so the read-back walks the
                # blocks rather than asking for a shape.
                var = reader_io.InquireVariable("B")
                blocks = engine.BlocksInfo("B", 0)
                if not blocks:
                    raise RuntimeError(f"'B' in {bp_path.name} has no data blocks")
                readback = 0.0
                for block_id, block in enumerate(blocks):
                    count = [int(n) for n in block["Count"].split(",")]
                    var.SetBlockSelection(block_id)
                    data = np.zeros(count, dtype=np.float64)
                    engine.Get(var, data, adios2.Mode.Sync)
                    readback = max(
                        readback, float(np.max(np.linalg.norm(data, axis=1)))
                    )
            finally:
                engine.Close()
        except Exception as e:  # noqa: BLE001 - reported, then re-raised below
            failure = f"{type(e).__name__}: {e}"

    readback, failure = comm.bcast((readback, failure), root=0)

    if failure is not None:
        print(f"    ⚠ VTX round-trip read-back unavailable: {failure}")
        return False

    rel = abs(readback - in_memory) / in_memory if in_memory else abs(readback)
    if comm.rank == 0:
        print("\n  VTX round-trip check (EX-17 anchor):")
        print(f"    in-memory  max|B| = {in_memory:.12e} T")
        print(f"    read-back  max|B| = {readback:.12e} T")
        print(f"    relative difference = {rel:.3e}  (tol {VTX_ROUNDTRIP_RTOL:.0e})")
    if rel > VTX_ROUNDTRIP_RTOL:
        raise RuntimeError(
            f"VTX round-trip mismatch: in-memory max|B| = {in_memory:.12e} vs "
            f"read-back {readback:.12e} (relative {rel:.3e} > {VTX_ROUNDTRIP_RTOL:.0e})"
        )
    if comm.rank == 0:
        print("    ✓ written .bp reproduces the in-memory field")
    return True


def main():
    """Run circular loop example."""
    comm = MPI.COMM_WORLD
    
    print("=" * 60)
    print("Example: Magnetic field of circular current loop")
    print("=" * 60)
    
    # Problem parameters. Geometry matches the gated fixture in
    # tests/validation/test_circular_loop.py: the domain must be ~3x the loop
    # radius because the natural boundary condition (n x H = 0) acts as a
    # magnetic mirror and inflates the field when the wall is close.
    current = 1.0              # Current [A]
    loop_radius = 0.02         # Loop radius [m] (2 cm)
    wire_radius = 0.003        # Wire cross-section [m] (fat wire, cheap to mesh;
                               # on-axis field is insensitive to wire thickness)
    domain_radius = 0.06       # Domain radius [m] (3x loop radius)
    resolution = 0.002         # Mesh resolution [m]. The analytic Dirichlet
                               # wall (below) needs this; 0.0025 costs ~2% extra
                               # L2 error (see tests/validation/test_circular_loop.py)
    
    print(f"\nParameters:")
    print(f"  Current: {current} A")
    print(f"  Loop radius: {loop_radius} m ({loop_radius*100:.1f} cm)")
    print(f"  Wire radius: {wire_radius} m ({wire_radius*1000:.1f} mm)")
    print(f"  Domain radius: {domain_radius} m")
    print(f"  Mesh resolution: {resolution} m")
    
    # Generate mesh
    print("\nGenerating mesh...")
    mesh, cell_tags, facet_tags = MeshGenerator.circular_loop_domain(
        loop_radius=loop_radius,
        wire_radius=wire_radius,
        domain_radius=domain_radius,
        resolution=resolution,
        comm=comm
    )
    print(f"  Mesh created: {mesh.topology.index_map(3).size_global} cells")
    
    # Set up problem
    problem = MagnetostaticProblem(
        mesh=mesh, 
        cell_tags=cell_tags,
        mu=MU_0
    )
    
    # Create solver
    solver = MagnetostaticSolver(problem, degree=1)
    
    # Define current density in wire
    wire_cross_section = np.pi * wire_radius**2
    J_magnitude = current / wire_cross_section
    
    import ufl
    def current_density(x):
        """Azimuthal current density circulating around the loop.

        The current flows along the wire, i.e. in the phi direction
        (-y, x, 0)/rho — NOT uniformly in z. A z-directed J here produces
        an on-axis B_z of ~zero (the field of straight vertical current
        filaments cancels on the axis by symmetry).
        """
        rho = ufl.sqrt(x[0] ** 2 + x[1] ** 2)
        rho_safe = ufl.max_value(rho, 1e-12)
        return ufl.as_vector([
            -x[1] / rho_safe * J_magnitude,
            x[0] / rho_safe * J_magnitude,
            0.0,
        ])
    
    # Constrain the outer sphere with the analytic vector potential (Jackson
    # 5.37). The natural condition n x H = 0 is a perfect-magnetic-conductor
    # wall that images the loop and biases the field at this domain size; the
    # analytic Dirichlet data is the condition whose continuum limit is the
    # free-space solution (same setup as tests/validation/test_circular_loop.py).
    def loop_potential(x):
        points = np.ascontiguousarray(x[:3].T)
        return AnalyticalSolutions.circular_loop_vector_potential(
            points, current, loop_radius
        ).T

    bcs = [exterior_dirichlet_bc(solver.V, loop_potential)]

    # Solve with current restricted to wire subdomain (tag=1)
    print("\nSolving magnetostatic problem...")
    A = solver.solve(current_density=current_density, subdomain_id=1,
                     bc_functions=bcs)
    print("  Solution computed!")
    
    # Compute B-field
    print("\nComputing B-field...")
    B = solver.compute_b_field()
    
    # Evaluate along z-axis
    n_points = 25
    # Sample well inside the domain (0.4 * domain_radius, as in the gated
    # test): the outermost mesh layer near the spherical wall carries the
    # largest boundary-condition error.
    z_eval = np.linspace(-0.4 * domain_radius, 0.4 * domain_radius, n_points)
    
    points = np.zeros((n_points, 3))
    points[:, 2] = z_eval  # z positions along axis
    
    # Evaluate in the cells actually containing each point. Passing np.arange(n)
    # evaluates in arbitrary cells and yields meaningless values.
    B_num, valid = evaluate_vector_field_parallel(B, points)
    if not valid.all():
        print(f"  WARNING: {(~valid).sum()}/{n_points} sample points outside mesh")
    B_num_z = B_num[:, 2]  # z-component only
    
    # Analytical solution
    B_ana_z = AnalyticalSolutions.circular_loop_magnetic_field_on_axis(
        z_eval, current, loop_radius
    )
    
    # Error metrics
    rel_error = ErrorMetrics.l2_relative_error(B_num_z, B_ana_z)
    max_error = ErrorMetrics.max_relative_error(B_num_z, B_ana_z)
    
    print(f"\nResults:")
    print(f"  B_z at center (numerical): {B_num_z[n_points//2]:.6e} T")
    print(f"  B_z at center (analytical): {B_ana_z[n_points//2]:.6e} T")
    print(f"  Max B_z (analytical): {np.max(B_ana_z):.6e} T")
    print(f"  Relative L2 error: {rel_error:.4%}")
    print(f"  Max relative error: {max_error:.4%}")
    
    # Expected B_z at center
    B_center_expected = MU_0 * current / (2 * loop_radius)
    print(f"\n  Expected B_z(0) = μ₀I/(2a) = {B_center_expected:.6e} T")
    
    # Compute magnetic energy
    energy = solver.compute_magnetic_energy()
    print(f"\n  Magnetic energy: {energy:.6e} J")

    # =========================================================================
    # Save results for ParaView visualization
    # =========================================================================
    print("\n" + "=" * 60)
    print("Saving results for ParaView visualization...")
    print("=" * 60)

    # Create output directory
    output_dir = Path("paraview_output")
    output_dir.mkdir(exist_ok=True)

    # Standardized XDMF exports (individual + combined tag/field output)
    print("\n  Writing XDMF files (traditional + combined)...")

    # Create Lagrange function space for visualization
    V_lag = fem.functionspace(mesh, ("Lagrange", 1, (3,)))

    # Interpolate A and B to Lagrange space
    A_lag = fem.Function(V_lag, name="A")
    A_lag.interpolate(A)
    B_lag = fem.Function(V_lag, name="B")
    B_lag.interpolate(B)

    # Analytical off-axis loop field (elliptic integrals) on the same grid,
    # for direct FEM-vs-exact comparison in ParaView. The formula assumes a
    # filament, so values inside the wire cross-section are not meaningful.
    B_analytical = fem.Function(V_lag, name="B_analytical")
    B_analytical.interpolate(
        lambda x: AnalyticalSolutions.circular_loop_magnetic_field(
            x.T, current, loop_radius
        ).T
    )

    written_files = write_combined_paraview_output(
        output_dir=output_dir,
        basename="circular_loop",
        mesh=mesh,
        cell_tags=cell_tags,
        fields={
            "A": (A, A_lag),
            "B": (B, B_lag),
            "B_analytical": (B_analytical, B_analytical),
        },
        comm=comm,
    )
    if comm.rank == 0:
        print("    ✓ Standardized XDMF export complete")
        if "combined" in written_files:
            print(f"    ✓ Combined file saved to {written_files['combined'].name}")

    # Method 2: VTX format (modern, supports higher-order elements)
    #
    # EX-17: VTXWriter accepts only (discontinuous) Lagrange functions, so it is
    # handed the A_lag/B_lag interpolants built above -- never the N1curl `A` or
    # the DG-space `B` object.  The two writers also get one `try` each: the
    # original single block meant a failure on `A` silently skipped `B` as well.
    print("\n  Writing VTX files...")
    b_bp_path = output_dir / "circular_loop_B.bp"
    vtx_B_written = False
    try:
        # VTXWriter for the vector potential A (Lagrange interpolant of N1curl A)
        vtx_A = io.VTXWriter(comm, output_dir / "circular_loop_A.bp", [A_lag], engine="BP4")
        vtx_A.write(0.0)
        vtx_A.close()
        print("    ✓ Vector potential A saved to circular_loop_A.bp/")
    except Exception as e:
        print(f"    ⚠ VTX output of A failed: {e}")

    try:
        # VTXWriter for the magnetic field B (Lagrange interpolant of DG B)
        vtx_B = io.VTXWriter(comm, b_bp_path, [B_lag], engine="BP4")
        vtx_B.write(0.0)
        vtx_B.close()
        vtx_B_written = True
        print("    ✓ Magnetic field B saved to circular_loop_B.bp/")
    except Exception as e:
        print(f"    ⚠ VTX output of B failed: {e}")

    if not (vtx_B_written and _check_vtx_roundtrip(b_bp_path, B_lag, V_lag, comm)):
        print("    Note: XDMF files were still created and can be used instead")

    print("\n  ✓ ParaView files saved to paraview_output/")
    print("    Open circular_loop_combined.xdmf in ParaView: it carries the")
    print("    'CellTags' cell array plus A, B, and B_analytical on one grid,")
    print("    so Threshold on CellTags and Calculator mag(B - B_analytical)")
    print("    both work directly.")

    # Save results for plotting (text format)
    if comm.rank == 0:
        print("\n  Saving results...")
        data = np.column_stack([z_eval, B_num_z, B_ana_z, 
                                 np.abs(B_num_z - B_ana_z)])
        np.savetxt('circular_loop_results.txt', data, 
                   header='z[m] Bz_num[T] Bz_ana[T] error[T]',
                   fmt='%.6e')
        print("  Results saved to: circular_loop_results.txt")
        
        # Print some values
        print("\n  Sample values:")
        print(f"    {'z [m]':<12} {'B_z num [T]':<15} {'B_z ana [T]':<15} {'Error':<10}")
        print("    " + "-" * 52)
        for i in [0, n_points//4, n_points//2, 3*n_points//4, n_points-1]:
            err_pct = 100 * abs(B_num_z[i] - B_ana_z[i]) / abs(B_ana_z[i])
            print(f"    {z_eval[i]:<12.4f} {B_num_z[i]:<15.6e} "
                  f"{B_ana_z[i]:<15.6e} {err_pct:<10.2f}%")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    
    return solver, B


if __name__ == "__main__":
    main()
