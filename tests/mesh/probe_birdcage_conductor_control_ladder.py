"""`GEO-21` step 1, second measurement — how coarse must a *graded* conductor
sizing be before it separates from the 0.95 CAD-mass gate?

The first probe (`probe_birdcage_conductor_cad_mass.py`,
`20260826T050134Z_GEO-21-step1-cad-mass-probe.log`) answered the question the
`GEO-21` ruling turns on and landed in **neither** pre-stated branch: the
candidate control ``h_c = 3.2e-3`` recovers **0.916742** of the conductor's CAD
mass — not "clearly below" the gate (the rule's ≤ 0.90), and not clearing it
(0.95) either.  It is also *inside* the gate module's own negative-control
guard, ``baseline_ratio < CAD_MASS_GATE - 0.05`` = 0.90, which that module
pre-registered as the reading at which "the negative control no longer
separates and the chunk's premise needs re-examining".  So adopting 3.2e-3
would turn the gate red on an assertion no licence permits loosening.

This probe measures the axis the review would need to rule on option (b) —
a *coarser graded* sizing as the control — without adopting anything.  It is
measurement handed to the review, not a control chosen in-slot: the `GEO-21`
entry's "never manufacture a control by hunting sizings until one fails"
stands, and nothing here is imported by a gate.

**The reading is not free of a caveat, and the caveat is the point.** The dead
``h_c = None`` control made the gate demonstrate *grading vs no grading*.  Any
coarse-graded replacement demotes it to *fine grading vs coarse grading* — a
weaker claim about the same fixture, and one that no longer speaks to whether
grading is a `PORT-9` prerequisite.  That is a ruling for the review to make
knowingly, which is why this probe prints the ladder rather than picking off it.

Rungs run coarse-ward from the measured 3.2e-3 toward the fixture's global
``RESOLUTION = 0.015``, where the ungraded build is known to abort.  A rung may
therefore FAIL, so this runs at **`-n 1`**: the generator builds its gmsh model
under ``if comm.rank == rank:`` while `_model_to_mesh` is collective, so a
rank-0 gmsh exception deadlocks the other ranks instead of reporting (the
resolution probe documents this trap).  The 3.2e-3 rung repeats here as the
**width control** — at `-n 1` it must reproduce the `-n 2` reading 0.916742,
since gmsh's meshing is serial at either width and the tagged volumes are exact
sums; a move there would mean the number is an artefact of the reduction, not
of the sizing.

    mpiexec -n 1 python3 -u tests/mesh/probe_birdcage_conductor_control_ladder.py
"""

import os
import sys

import gmsh
from mpi4py import MPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from tests.mesh.test_birdcage_conductor_sizing import (  # noqa: E402
    CAD_MASS_GATE,
    CONDUCTOR_RUNGS,
    _check_geo9_identities,
    _mesh,
)

# The `-n 2` reading this ladder's first rung must reproduce.
WIDTH_CONTROL_RATIO = 0.916742

# Coarse-ward from the measured rung toward the global 0.015 the ungraded build
# fails at.  Deliberately short: a bracket is what the review needs, and each
# step walks nearer the failing build, not further from it.
CONTROL_LADDER = (CONDUCTOR_RUNGS[0], 4.8e-3, 6.4e-3, 9.6e-3)


def main():
    comm = MPI.COMM_WORLD
    rank0 = comm.rank == 0

    if rank0:
        print(
            "birdcage graded-conductor control ladder: meshed/CAD mass, coarse-ward "
            f"(gate = {CAD_MASS_GATE}, separation guard = {CAD_MASS_GATE - 0.05:.2f}, "
            f"{comm.size} rank(s))\n",
            flush=True,
        )

    for h_c in CONTROL_LADDER:
        try:
            rung = _mesh(conductor_resolution=h_c)
            _check_geo9_identities(rung, comm)
        except Exception as exc:  # gmsh raises a bare Exception carrying its text
            # The generator only reaches `gmsh.finalize()` on the success path,
            # so a failed case would otherwise leak model state into the next.
            try:
                gmsh.finalize()
            except Exception:
                pass
            if rank0:
                print(
                    f"  h_c = {h_c:.4e}  FAIL  {str(exc).strip().splitlines()[-1]}",
                    flush=True,
                )
            continue
        ratio = rung["v"][1] / rung["cad_mass"]["conductor"]
        if rank0:
            note = ""
            if h_c == CONDUCTOR_RUNGS[0]:
                note = f"  [width control vs -n 2: {ratio - WIDTH_CONTROL_RATIO:+.6f}]"
            print(
                f"  h_c = {h_c:.4e}  cells={rung['n_cells']:>8d}  "
                f"meshed/CAD={ratio:.6f}  mesh={rung['mesh_wall_time_s']:6.2f} s{note}",
                flush=True,
            )

    if rank0:
        print("\nMeasurement only -- no assertion, no control adopted.", flush=True)


if __name__ == "__main__":
    main()
