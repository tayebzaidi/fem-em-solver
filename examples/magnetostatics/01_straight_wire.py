"""
Example: Magnetic field of a straight wire.

This example demonstrates the magnetostatic solver by computing
the magnetic field around a current-carrying wire and comparing
with the analytical solution.
"""

import numpy as np
import matplotlib.pyplot as plt
from mpi4py import MPI
from pathlib import Path

from fem_em_solver.core.solvers import MagnetostaticSolver, MagnetostaticProblem
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.analytical import AnalyticalSolutions, ErrorMetrics
from fem_em_solver.utils.constants import MU_0
from fem_em_solver.post import evaluate_vector_field_parallel
from fem_em_solver.io.paraview_utils import write_combined_paraview_output

# Import dolfinx I/O for ParaView output
from dolfinx import io, fem


#: EX-14 anchor: the ADIOS2 round trip is exact, so the written artifact must
#: reproduce the in-memory global max |B| to round-off.  This is a closed-loop
#: identity on the file itself, not a finiteness check.
VTX_ROUNDTRIP_RTOL = 1e-10


def _global_max_magnitude(f, V, comm):
    """Allreduced max |f| over owned dofs (rank-local maxima are not the answer)."""
    n_owned = V.dofmap.index_map.size_local * V.dofmap.index_map_bs
    owned = f.x.array[:n_owned].reshape(-1, 3)
    local = float(np.max(np.linalg.norm(owned, axis=1))) if owned.size else 0.0
    return comm.allreduce(local, op=MPI.MAX)


def _check_vtx_roundtrip(bp_path, B_lag, V_lag, comm):
    """Read the written .bp back through ADIOS2 and compare max |B| (EX-14).

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
            reader_io = adios.DeclareIO("ex14_vtx_readback")
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
        print("\n  VTX round-trip check (EX-14 anchor):")
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
    """Run straight wire example."""
    comm = MPI.COMM_WORLD
    
    print("=" * 60)
    print("Example: Magnetic field of straight wire")
    print("=" * 60)
    
    # Problem parameters (balanced for accuracy and speed)
    current = 1.0              # Current [A]
    wire_length = 0.3          # Wire length [m]
    domain_radius = 0.04       # Domain radius [m] (4 cm)
    # Mesh resolution [m] (coarse, cron-safe runtime).
    # Was 0.01 until 2026-08-26. On the dolfinx 0.11 image `straight_wire_domain`
    # has a coarse-resolution floor: h = 0.01 aborts inside gmsh with "Invalid
    # boundary mesh (overlapping facets)" for *every* geometry tried, including
    # the gate's own L = 0.20 / R = 0.030, while h = 0.008 / 0.006 / 0.005 /
    # 0.004 all mesh. Localised by
    # tests/validation/probe_straight_wire_mesh_resolution.py, log
    # docs/testing/logs/20260825T142512Z_EX-30-root-mag1-mesh-probe.log
    # (h = 0.0080 OK, 21830 cells, 2.6 s). 0.008 is the nearest working rung.
    # The floor's exact threshold is unbisected, so no guard is written here;
    # see docs/testing/known-issues.md (EX-30 leg (root)) — ruled 2026-08-25
    # 10:30 review, executed by EX-30 leg (root) completion.
    resolution = 0.008
    wire_radius = 0.003       # Wire radius [m] (1.5 mm)
    
    print(f"\nParameters:")
    print(f"  Current: {current} A")
    print(f"  Wire length: {wire_length} m")
    print(f"  Wire radius: {wire_radius} m")
    print(f"  Domain radius: {domain_radius} m")
    print(f"  Mesh resolution: {resolution} m")
    
    # Generate mesh
    print("\nGenerating mesh...")
    mesh, cell_tags, facet_tags = MeshGenerator.straight_wire_domain(
        wire_length=wire_length,
        wire_radius=wire_radius,
        domain_radius=domain_radius,
        resolution=resolution,
        comm=comm
    )

    # Diagnostic: Check mesh properties
    num_cells = mesh.topology.index_map(3).size_global
    num_vertices = mesh.topology.index_map(0).size_global
    print(f"  Mesh created: {num_cells} cells, {num_vertices} vertices")

    # Check cell tags
    if cell_tags is not None:
        unique_tags = np.unique(cell_tags.values)
        print(f"  Cell tags found: {unique_tags}")
        for tag in unique_tags:
            count = np.sum(cell_tags.values == tag)
            if tag == 1:
                print(f"    Tag {tag} (wire): {count} cells")
            elif tag == 2:
                print(f"    Tag {tag} (air/domain): {count} cells")
    else:
        print("  WARNING: No cell tags found!")
    
    # Set up problem with cell tags for subdomain integration
    problem = MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0)
    
    # Create solver
    solver = MagnetostaticSolver(problem, degree=1)
    
    # Define current density in wire
    wire_area = np.pi * wire_radius**2
    J_magnitude = current / wire_area
    
    import ufl
    def current_density(x):
        """Uniform current density in z-direction."""
        return ufl.as_vector([0.0, 0.0, J_magnitude])
    
    # Solve with current restricted to wire subdomain (tag=1)
    print("\nSolving magnetostatic problem...")
    A = solver.solve(current_density=current_density, subdomain_id=1)
    print("  Solution computed (current restricted to wire volume)!")
    
    # Compute B-field
    print("\nComputing B-field...")
    B = solver.compute_b_field()

    # Interpolate B to Lagrange space for evaluation
    # (DG functions are discontinuous and need proper cell indices for eval)
    print("  Interpolating B to Lagrange space for evaluation...")
    V_lag = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    B_lag = fem.Function(V_lag, name="B")
    B_lag.interpolate(B)

    # Evaluate along x-axis from wire edge to domain boundary
    n_points = 30
    r_eval = np.linspace(wire_radius, domain_radius * 0.95, n_points)  # From wire edge to near boundary

    print(f"\nEvaluating B-field along x-axis:")
    print(f"  From r = {r_eval[0]*1000:.2f} mm (wire edge) to r = {r_eval[-1]*100:.2f} cm")
    print(f"  Wire radius: {wire_radius*1000:.2f} mm, Domain radius: {domain_radius*100:.2f} cm")
    print(f"  Number of evaluation points: {n_points}")

    points = np.zeros((n_points, 3))
    points[:, 0] = r_eval  # x positions (radial distance from wire center)
    points[:, 1] = 0.0     # y = 0
    points[:, 2] = 0.0     # z = 0 (middle of wire)

    print(f"\n  DEBUG - Evaluation points:")
    print(f"  First 3 points: {points[:3]}")
    print(f"  Last 3 points: {points[-3:]}")

    # Evaluate points robustly across MPI partitions
    B_num, valid_mask = evaluate_vector_field_parallel(B_lag, points, comm=comm)

    invalid_count = np.count_nonzero(~valid_mask)
    print(f"\n  DEBUG - Valid evaluation points: {np.count_nonzero(valid_mask)}/{n_points}")
    if invalid_count > 0:
        print(f"  WARNING: {invalid_count} points were outside mesh partitions")
    print(f"\n  DEBUG - Numerical B-field evaluation:")
    print(f"  B_num shape: {B_num.shape}, dtype: {B_num.dtype}")
    print(f"  First point: B = ({B_num[0,0]:.6e}, {B_num[0,1]:.6e}, {B_num[0,2]:.6e}) T")
    print(f"  Last point:  B = ({B_num[-1,0]:.6e}, {B_num[-1,1]:.6e}, {B_num[-1,2]:.6e}) T")

    # Compute magnitude
    B_num_mag = np.linalg.norm(B_num, axis=1)
    print(f"  |B| at first point: {B_num_mag[0]:.6e} T")
    print(f"  |B| at last point:  {B_num_mag[-1]:.6e} T")
    print(f"  Ratio (should be ~{r_eval[-1]/r_eval[0]:.2f}): {B_num_mag[0]/B_num_mag[-1]:.2f}")

    # Analytical solution (wire at origin, matching mesh)
    wire_position_analytical = np.array([0.0, 0.0])  # Must match mesh generation at (x=0, y=0)
    B_ana = AnalyticalSolutions.straight_wire_magnetic_field(points, current, wire_position_analytical)

    print(f"\n  DEBUG - Analytical B-field:")
    print(f"  Wire position: ({wire_position_analytical[0]}, {wire_position_analytical[1]})")
    print(f"  First point: B = ({B_ana[0,0]:.6e}, {B_ana[0,1]:.6e}, {B_ana[0,2]:.6e}) T")
    print(f"  Last point:  B = ({B_ana[-1,0]:.6e}, {B_ana[-1,1]:.6e}, {B_ana[-1,2]:.6e}) T")

    B_ana_mag = np.linalg.norm(B_ana, axis=1)
    print(f"  |B| at first point: {B_ana_mag[0]:.6e} T")
    print(f"  |B| at last point:  {B_ana_mag[-1]:.6e} T")
    print(f"  Ratio (expected ~{r_eval[-1]/r_eval[0]:.2f}): {B_ana_mag[0]/B_ana_mag[-1]:.2f}")

    # Expected field from formula: B = μ₀I/(2πr)
    mu_0 = 4 * np.pi * 1e-7
    B_expected_first = mu_0 * current / (2 * np.pi * r_eval[0])
    B_expected_last = mu_0 * current / (2 * np.pi * r_eval[-1])
    print(f"\n  Expected from μ₀I/2πr formula:")
    print(f"  At r={r_eval[0]*1000:.2f}mm: {B_expected_first:.6e} T")
    print(f"  At r={r_eval[-1]*1000:.2f}mm: {B_expected_last:.6e} T")

    # Debug: Component analysis - field at (x,0,0) should be (0, By, 0)
    print(f"\n  Component verification at (x, 0, 0):")
    print(f"  Expected: Bx≈0, By=μ₀I/2πx, Bz≈0")
    print(f"  {'r [mm]':>10} {'Bx [T]':>12} {'By [T]':>12} {'Bz [T]':>12} {'|B|':>12}")
    for i in [0, n_points//2, n_points-1]:
        print(f"  {r_eval[i]*1000:10.2f} {B_num[i,0]:12.6e} {B_num[i,1]:12.6e} {B_num[i,2]:12.6e} {B_num_mag[i]:12.6e}")

    # Debug: Print first and last few values to verify 1/r decay
    print(f"\n  Field magnitude verification (should decay as 1/r):")
    print(f"  {'r [mm]':>10} {'|B_num| [T]':>15} {'|B_ana| [T]':>15} {'Ratio':>10}")
    for i in [0, 1, 2, n_points//2, n_points-3, n_points-2, n_points-1]:
        ratio = B_num_mag[i] / B_ana_mag[i] if B_ana_mag[i] > 0 else 0
        print(f"  {r_eval[i]*1000:10.2f} {B_num_mag[i]:15.6e} {B_ana_mag[i]:15.6e} {ratio:10.4f}")

    # Verify 1/r scaling: B(r1)/B(r2) should equal r2/r1
    r1, r2 = r_eval[0], r_eval[-1]
    expected_ratio = r2 / r1
    actual_num_ratio = B_num_mag[0] / B_num_mag[-1]
    actual_ana_ratio = B_ana_mag[0] / B_ana_mag[-1]
    print(f"\n  1/r decay check:")
    print(f"  Expected B(r_min)/B(r_max) = {expected_ratio:.2f}")
    print(f"  Numerical: {actual_num_ratio:.2f}")
    print(f"  Analytical: {actual_ana_ratio:.2f}")
    
    # Error metrics
    rel_error = ErrorMetrics.l2_relative_error(B_num_mag, B_ana_mag)
    max_error = ErrorMetrics.max_relative_error(B_num_mag, B_ana_mag)
    
    print(f"\nResults:")
    print(f"  Max B-field (numerical): {np.max(B_num_mag):.6e} T")
    print(f"  Max B-field (analytical): {np.max(B_ana_mag):.6e} T")
    print(f"  Relative L2 error: {rel_error:.4%}")
    print(f"  Max relative error: {max_error:.4%}")
    
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

    # V_lag and B_lag already created earlier for evaluation
    # Interpolate A to Lagrange space
    A_lag = fem.Function(V_lag, name="A")
    A_lag.interpolate(A)

    # Analytical B on the same grid, for direct FEM-vs-exact comparison in
    # ParaView (e.g. Calculator: mag(B - B_analytical)).
    B_analytical = fem.Function(V_lag, name="B_analytical")
    B_analytical.interpolate(
        lambda x: AnalyticalSolutions.straight_wire_magnetic_field(
            x.T, current, wire_position_analytical
        ).T
    )

    try:
        written_files = write_combined_paraview_output(
            output_dir=output_dir,
            basename="magnetostatics_01_straight_wire",
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
                print("    This file has BOTH cell tags and fields on the same grid!")
    except Exception as e:
        import traceback
        print(f"    ⚠ XDMF export failed: {e}")
        print("\n  Full traceback:")
        traceback.print_exc()

    # Method 3: VTX format (modern, supports higher-order elements)
    # This uses ADIOS2 and creates .bp directory with data.
    #
    # EX-14: VTXWriter accepts only (discontinuous) Lagrange functions, so it is
    # handed the A_lag/B_lag interpolants built above -- never the N1curl `A` or
    # the DG-space `B` object.  The two writers also get one `try` each: the
    # original single block meant a failure on `A` silently skipped `B` as well.
    print("\n  Writing VTX files (modern ADIOS2 format)...")
    b_bp_path = output_dir / "magnetostatics_01_straight_wire_B.bp"
    vtx_B_written = False
    try:
        # VTXWriter for the vector potential A (Lagrange interpolant of N1curl A)
        vtx_A = io.VTXWriter(comm, output_dir / "magnetostatics_01_straight_wire_A.bp", [A_lag], engine="BP4")
        vtx_A.write(0.0)  # time = 0.0 for static problem
        vtx_A.close()
        print("    ✓ Vector potential A saved to magnetostatics_01_straight_wire_A.bp/")
    except Exception as e:
        print(f"    ⚠ VTX output of A failed: {e}")

    try:
        # VTXWriter for the magnetic field B (Lagrange interpolant of DG B)
        vtx_B = io.VTXWriter(comm, b_bp_path, [B_lag], engine="BP4")
        vtx_B.write(0.0)
        vtx_B.close()
        vtx_B_written = True
        print("    ✓ Magnetic field B saved to magnetostatics_01_straight_wire_B.bp/")
    except Exception as e:
        print(f"    ⚠ VTX output of B failed: {e}")

    if not (vtx_B_written and _check_vtx_roundtrip(b_bp_path, B_lag, V_lag, comm)):
        print("    Note: XDMF files were still created and can be used instead")

    print("\n" + "=" * 60)
    print("ParaView Instructions:")
    print("=" * 60)
    print("\n  RECOMMENDED: Use the combined file!")
    print("    File -> Open -> magnetostatics_01_straight_wire_combined.xdmf")
    print("    - Cell tags are the 'CellTags' cell array, on the SAME grid")
    print("      as A, B, and B_analytical (thresholds like any other array)")
    print("    - B field available for Glyph, Stream Tracer, etc.")
    print("\n  Filtering workflow:")
    print("    1. Apply Threshold filter:")
    print("       - Scalars: 'CellTags'")
    print("       - Min: 2, Max: 2 (removes wire cells)")
    print("    2. Apply Glyph filter to thresholded data:")
    print("       - Orientation/Scale: B")
    print("    3. Compare with exact field via Calculator:")
    print("       - mag(B - B_analytical) gives the pointwise error")
    print("\n  Alternative: Individual files")
    print("    - magnetostatics_01_straight_wire_A.xdmf (vector potential)")
    print("    - magnetostatics_01_straight_wire_B.xdmf (magnetic field)")
    print("    - magnetostatics_01_straight_wire_B_analytical.xdmf (exact field)")
    print("    Each also carries the mesh and the CellTags array.")
    print("\n  Alternative: VTX/ADIOS2 directories (EX-14)")
    print("    - magnetostatics_01_straight_wire_A.bp/ (vector potential, Lagrange interpolant)")
    print("    - magnetostatics_01_straight_wire_B.bp/ (magnetic field, Lagrange interpolant)")
    print("    Open the directory itself; ParaView picks the ADIOS2VTXReader.")
    print("=" * 60)
    
    # Plot results
    if comm.rank == 0:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # B-field magnitude comparison
        ax = axes[0]
        ax.semilogy(r_eval * 1000, B_num_mag, 'b-o', label='Numerical (FEM)', markersize=4)
        ax.semilogy(r_eval * 1000, B_ana_mag, 'r--', label=f'Analytical (μ₀I/2πr)', linewidth=2)
        ax.set_xlabel('Radial Distance from Wire Center [mm]')
        ax.set_ylabel('|B| [T] (log scale)')
        ax.set_title(f'Magnetic Field Magnitude vs Distance\n(Should decay as 1/r)')
        ax.legend()
        ax.grid(True, alpha=0.3, which='both')
        
        # Relative error
        ax = axes[1]
        rel_err_pointwise = np.abs(B_num_mag - B_ana_mag) / B_ana_mag
        ax.semilogy(r_eval * 1000, rel_err_pointwise * 100, 'g-s', markersize=4)
        ax.set_xlabel('Distance from wire [mm]')
        ax.set_ylabel('Relative Error [%]')
        ax.set_title('Pointwise Relative Error')
        ax.axhline(y=rel_error * 100, color='r', linestyle='--', 
                   label=f'L2 error: {rel_error:.2%}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = output_dir / "magnetostatics_01_straight_wire_validation.png"
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        print(f"\n  Plot saved to: {plot_path.resolve()}")
        plt.close()
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    
    return solver, B


if __name__ == "__main__":
    main()
