"""Print the global cell count of the `PORT-1` two-torus fixture.

`OPS-18` step 3: the two failing two-torus records (`passivity_max_sigma`,
the step-1 gap ratio) move at 1e-4 in the 0.11 image while every physics
identity holds.  The known-issues entry names one discriminating experiment
and says nobody has run it: *print the two-torus cell count on both images*.
If the mesh moved, the moved records are the mesh (the precedent the review
already granted `TH-10`'s 55 251 -> 55 241); if it is bit-identical, the
delta is in the solve and the upgrade has found something real.

Mesh only -- no solve, no assertion.  Every fixture argument is imported
from the test module that owns the record, never restated (`ANS-1`).

    mpiexec -n 2 python3 -u tests/mesh/probe_two_torus_cell_count.py
"""

import time

import numpy as np
from mpi4py import MPI

from tests.validation.test_port_lumped_two_torus import _build


def main():
    comm = MPI.COMM_WORLD
    t0 = time.perf_counter()
    msh, cell_tags, facet_tags, t_mesh = _build(comm)
    tdim = msh.topology.dim

    n_cells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    n_verts = comm.allreduce(msh.topology.index_map(0).size_local, op=MPI.SUM)

    # Cell-tag census, reduced: `cell_tags.values` is rank-local.
    local_tags, local_counts = np.unique(cell_tags.values, return_counts=True)
    all_tags = sorted({int(t) for t in comm.allreduce(list(local_tags), op=MPI.SUM)})
    census = {}
    for tag in all_tags:
        local = int(local_counts[local_tags == tag].sum()) if tag in local_tags else 0
        census[tag] = comm.allreduce(local, op=MPI.SUM)

    if comm.rank == 0:
        import dolfinx
        import gmsh

        print(f"  dolfinx {dolfinx.__version__}  gmsh {gmsh.__version__}")
        print(f"  two_torus_domain cells (global): {n_cells}")
        print(f"  two_torus_domain vertices (global): {n_verts}")
        print(f"  cell-tag census: {census}")
        print(f"  mesh build {t_mesh:.2f} s, probe {time.perf_counter() - t0:.2f} s")


if __name__ == "__main__":
    main()
