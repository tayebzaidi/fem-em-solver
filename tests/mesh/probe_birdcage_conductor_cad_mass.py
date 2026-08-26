"""`GEO-21` step 1 — what does the coarse graded rung recover of the CAD mass?

`EX-30` leg (mesh) localised the `GEO-15` gate's red to the **ungraded**
conductor path: ``conductor_resolution=None`` no longer meshes on the 0.11
image at any global resolution tried (known-issues 2026-08-25,
`20260825T213926Z_EX-30-mesh-birdcage-resolution-probe.log`).  That probe
measured cell counts only — it never ran the gate's assertions, so the one
number the `GEO-21` ruling turns on is still unmeasured: the **meshed/CAD mass
ratio at the coarse rung** ``h_c = 2 x 0.4 x ring_minor_radius = 3.2e-3 m``,
the candidate replacement for the dead ``None`` control.

Decision rule, pre-stated in the `GEO-21` §7 entry: a reading **≤ 0.90** is
"clearly below" the 0.95 gate the way ``h_c = None``'s 0.7403 was, and the
baseline control moves there; a reading that *clears* the gate means the
inverted premise has no meshable carrier on 0.11 and the finding is reported
rather than manufactured around.  This probe measures, it does not rule.

Both rungs are printed — the coarse one is the candidate control, the fine one
(``1.6e-3``) is the rung that carries the gate, and its ratio is also the
thing the gate would re-assert.  `_mesh` is imported from the gate module, not
restated (`ANS-1` direction), so the ratios come off the *same* code path the
gate uses, including its `GEO-9` identity checks.

Measurement only: no assertion, nothing re-recorded here.  Runs at `-n 2` —
neither rung is expected to FAIL (both meshed OK in the resolution probe), so
the rank-0 gmsh-exception deadlock trap does not apply, and `-n 2` is the width
`_mesh`'s rank-local reductions are written for.

    mpiexec -n 2 python3 -u tests/mesh/probe_birdcage_conductor_cad_mass.py
"""

import os
import sys

from mpi4py import MPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from tests.mesh.test_birdcage_conductor_sizing import (  # noqa: E402
    CAD_MASS_GATE,
    CONDUCTOR_RUNGS,
    _check_geo9_identities,
    _mesh,
)


def main():
    comm = MPI.COMM_WORLD
    rank0 = comm.rank == 0

    if rank0:
        print(
            "birdcage conductor sizing: meshed/CAD mass by rung "
            f"(gate = {CAD_MASS_GATE}, {comm.size} rank(s))\n",
            flush=True,
        )

    for h_c in CONDUCTOR_RUNGS:
        rung = _mesh(conductor_resolution=h_c)
        _check_geo9_identities(rung, comm)
        cad = rung["cad_mass"]["conductor"]
        ratio = rung["v"][1] / cad
        if rank0:
            print(
                f"  h_c = {h_c:.4e}  cells={rung['n_cells']:>8d}  "
                f"meshed/CAD={ratio:.6f}  CAD={cad:.9e} m^3  "
                f"mesh={rung['mesh_wall_time_s']:6.2f} s  rung={rung['wall_time_s']:6.2f} s",
                flush=True,
            )

    if rank0:
        print("\nMeasurement only -- no assertion, nothing re-recorded.", flush=True)


if __name__ == "__main__":
    main()
