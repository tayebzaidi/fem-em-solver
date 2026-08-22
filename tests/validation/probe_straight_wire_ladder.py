"""Re-measure the recorded straight-wire h-ladder on whichever image is booted.

`OPS-18` step 3: `test_straight_wire_b_field` moved 12.75% -> 15.3848%
against its 15% band in the 0.11 image, on a mesh that grew 145 900 ->
147 235 cells.  The band is not a physics tolerance -- it is 1.18x the
measured error of *that* mesh on an O(h^1.2) ladder with no plateau
(`test_straight_wire.py:174`-`186`).  The known-issues entry names the
discriminating experiment: re-run the ladder's **other two rungs**.  If the
whole ladder shifts by roughly the same factor it is the mesh; if only the
middle rung moved, it is not, and the upgrade has found something real.

Recorded ladder (`MAG-13`, log `20260730T034614Z_MAG-13-probe2`, analytic
Dirichlet BC, sampling 2a -> 0.8 R_domain, `mpiexec -n 2`):

    h=0.004   38 800 cells  22.19%
    h=0.0025 145 900 cells  12.75%   <- the gated rung
    h=0.0018 383 200 cells   9.26%

Solver call, sampling and error metric are imported from the test module
that owns the record, never restated (`ANS-1`).  No assertion: this is a
measurement, and the ruling on whether a record may move is the review's.

    mpiexec -n 2 python3 -u tests/validation/probe_straight_wire_ladder.py
"""

import os
import sys
import time

from mpi4py import MPI

from fem_em_solver.utils.analytical import ErrorMetrics
from tests.validation.test_straight_wire import (
    R_MAX_BC,
    R_MIN,
    _sample_radial,
    _solve_straight_wire,
)

#: Rungs, cheapest first, with their recorded (cells, error) on dolfinx 0.7.2
#: / gmsh 4.11.  The gated rung h=0.0025 is deliberately absent: it was
#: measured twice already this chunk (147 235 cells, 15.3848%).
RECORD = {
    0.004: (38_800, 0.2219),
    0.0025: (145_900, 0.1275),
    0.0018: (383_200, 0.0926),
}

#: Rungs to run this invocation, as a comma-separated ``PROBE_H``.  Default is
#: the two rungs the gated test does *not* cover; set ``PROBE_H=0.0025`` to
#: interrogate the gated rung itself (`OPS-18` step 3 attempt 4 found it a
#: 1.8x outlier on its own 0.11 ladder, and rank dependence is untested).
RUNGS = [float(h) for h in os.environ.get("PROBE_H", "0.004,0.0018").split(",")]


def main():
    comm = MPI.COMM_WORLD
    n_points = 10

    if comm.rank == 0:
        print(f"  ranks {comm.size}  rungs {RUNGS}")
        import dolfinx
        import gmsh

        print(f"  dolfinx {dolfinx.__version__}  gmsh {gmsh.__version__}")

    for res in sorted(RUNGS, reverse=True):
        t0 = time.perf_counter()
        mesh, b_field = _solve_straight_wire(res, comm)
        _, b_num_mag, b_ana_mag, _ = _sample_radial(
            b_field, n_points, comm, R_MIN, R_MAX_BC
        )
        err = ErrorMetrics.l2_relative_error(b_num_mag, b_ana_mag)
        n_cells = mesh.topology.index_map(mesh.topology.dim).size_global
        if comm.rank == 0:
            cells_rec, err_rec = RECORD[res]
            print(
                f"  h={res:.4f}  cells {n_cells} (record {cells_rec}, "
                f"{(n_cells - cells_rec) / cells_rec:+.4%})  "
                f"error {err:.4%} (record {err_rec:.4%}, "
                f"{(err - err_rec) / err_rec:+.4%})  "
                f"{time.perf_counter() - t0:.1f} s"
            )
            sys.stdout.flush()


if __name__ == "__main__":
    main()
