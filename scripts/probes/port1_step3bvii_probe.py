"""`PORT-1` step 3b-vii cost probe: what does arc refinement cost?

Meshes the gapped two-torus fixture at the step 3b-vi geometry with and
without the new ``gap_arc_resolution`` field and prints cell counts and mesh
wall time, so the gate run can be sized before it is launched (the plan's
"probe mesh + one solve first"; drop to ``h_gap = 6e-4`` if two solves project
past 300 s).
"""

import sys
import time

from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402

# Mirrored from tests/validation/test_port_reaction_impedance.py -- importing
# that module pulls in the tests package, which is not on the path here.
MAJOR_RADIUS = 0.04
MINOR_RADIUS = 0.005
SEPARATION = 0.04
AIR_PADDING = 0.08
H_FAR = 0.03
H_WIRE = 0.0025
GAP_ANGLE = 0.30
GAP_BURIAL = 1.0e-3
GAP_OVERHANG = 2.0e-4


def probe(h_gap):
    comm = MPI.COMM_WORLD
    t0 = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=H_FAR,
        air_padding=AIR_PADDING,
        wire_resolution=H_WIRE,
        far_resolution=H_FAR,
        port_gap=True,
        gap_angle=GAP_ANGLE,
        gap_burial=GAP_BURIAL,
        gap_overhang=GAP_OVERHANG,
        gap_arc_resolution=h_gap,
        comm=comm,
    )
    dt = time.perf_counter() - t0
    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    per_tag = {
        tag: comm.allreduce(int((cell_tags.values == tag).sum()), op=MPI.SUM)
        for tag in (1, 2, 3, 101, 102)
    }
    if comm.rank == 0:
        print(
            f"[probe] h_gap={h_gap} cells={ncells} mesh_s={dt:.1f} "
            f"per_tag={per_tag}",
            flush=True,
        )
    return ncells, dt


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        probe(None if arg == "none" else float(arg))
