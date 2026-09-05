"""`TH-15` step 1 probe: does the PEC hole's exterior miss fall with h?

Measurement only — no assertions.  The step-1 gate module fits the exterior
dipole coefficient β on the middle rung to 1.97% while the *pointwise* miss on
the same points is 46%: a first-order N1curl floor next to the pinned curved
wall, not a defect, which is why the module's field anchor is the convergence
rate and the pointwise numbers are records (ruling, 2026-09-05 10:30 review).
This probe runs the module's own ladder and prints the full table.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src timeout -k 30 300 mpiexec -n 2 python3 \\
       scripts/probes/th15_pec_hole_resolution.py'
"""

from __future__ import annotations

import numpy as np
from mpi4py import MPI

# The ladder itself now lives in the gate module — this probe imports it back, so
# the assertion and the printed table are measurements of the same code path.
# The import must not go the other way: the module is the one under test.
from tests.validation.test_pec_sphere_hole import LADDER, run


def main() -> None:
    comm = MPI.COMM_WORLD
    rows = [run(hs, hf) for hs, hf in LADDER]
    if comm.rank == 0:
        print("\n[TH-15 step 1 probe] PEC sphere as a hole, exterior shells r = 1.2R, 1.5R")
        print(f"{'h_sphere':>10} {'cells':>8} {'beta':>10} {'|b-1|':>9} "
              f"{'max miss':>10} {'rms miss':>10} {'rel L2':>9}")
        for (hs, _), (beta, mx, rms, l2, n) in zip(LADDER, rows):
            print(f"{hs:10.5f} {n:8d} {beta:10.6f} {abs(beta - 1.0):8.3%} "
                  f"{mx:9.3%} {rms:9.3%} {l2:8.3%}")
        h = np.array([hs for hs, _ in LADDER])
        for name, col in (("|beta-1|", [abs(r[0] - 1.0) for r in rows]),
                          ("max miss", [r[1] for r in rows]),
                          ("rms miss", [r[2] for r in rows]),
                          ("rel L2", [r[3] for r in rows])):
            rate = float(np.polyfit(np.log(h), np.log(np.array(col)), 1)[0])
            print(f"  fitted rate in h for {name:>9}: {rate:+.4f}")


if __name__ == "__main__":
    main()
