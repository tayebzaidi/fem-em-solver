"""Localise where `MeshGenerator.birdcage_port_domain` stops meshing on 0.11.

`EX-30` leg (mesh), 2026-08-25: `examples/meshing/03_birdcage_graded_conductors.py`
and its own gate, `tests/mesh/test_birdcage_conductor_sizing.py::
test_graded_conductor_sizing_recovers_the_cad_mass`, both abort in gmsh with
"Invalid boundary mesh (overlapping facets) on surface 59 surface 79" on the
**baseline** rung -- `conductor_resolution=None` at the fixture's global
`RESOLUTION = 0.015`.  Because the baseline is built first, the *graded* rung
(`h_c = 0.4 x ring_minor_radius`) never ran in either, so nothing measured on
2026-08-25 says whether grading meshes on 0.11 at all.

The generator is not broken in general: `GEO-18`/`GEO-19` mesh this same
fixture at their own (finer) resolutions, most recently 116 085 and 307 296
cells the same day.  So the break lives between those parameter sets and this
one, which is the same shape as leg (root)'s `straight_wire_domain` finding
(`probe_straight_wire_mesh_resolution.py`, 2026-08-25) -- there, `resolution`
alone explained it and every geometry failed at h = 0.01.

Two legs, both measurement only:

* **Leg A** holds the fixture's global `RESOLUTION` and walks
  `conductor_resolution` across the two `GEO-15` rungs.  It answers the
  question the aborted runs could not: does grading the conductor rescue the
  build, i.e. is the red the *baseline* rung's alone or the fixture's?
* **Leg B** holds `conductor_resolution=None` and steps the global resolution
  finer.  If a floor exists, this brackets it.

Neither leg asserts.  Whether the baseline rung moves, the generator is
hardened, or the gate's control is re-chosen is the review's ruling, not this
probe's; nothing here is imported by a gate and no record is restated.

**Run this at `-n 1`, deliberately** -- for the reason the straight-wire probe
documents: the generator builds its gmsh model under `if comm.rank == rank:`
while the `_model_to_mesh` call is collective, so a gmsh exception on rank 0
deadlocks every other rank instead of reporting.  gmsh's boundary
reconstruction is serial on rank 0 at any width, and the cell counts are the
same mesh.

    mpiexec -n 1 python3 -u tests/mesh/probe_birdcage_conductor_resolution.py
"""

import os
import sys
import time

import gmsh
from mpi4py import MPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402

from tests.mesh.test_birdcage_conductor_sizing import CONDUCTOR_RUNGS  # noqa: E402
from tests.mesh.test_birdcage_port_tags import (  # noqa: E402
    AIR_PADDING,
    COIL_LENGTH,
    LEG_COUNT,
    LEG_SPACING,
    LEG_WIDTH,
    PHANTOM_HEIGHT,
    PHANTOM_RADIUS,
    PORT_BOX_SIZE,
    RESOLUTION,
    RING_MINOR_RADIUS,
    RING_RADIUS,
)

# Leg A: the fixture's own global resolution, conductor sizing swept.  `None`
# is the failing baseline; the two rungs are `GEO-15`'s ladder, coarse end
# first so the cheap cases report before the expensive ones.
CONDUCTOR_LADDER = [None, *CONDUCTOR_RUNGS]

# Leg B: the baseline's conductor sizing, global resolution stepped finer.
# Stops at 0.011 on purpose -- the fixture's air box is 0.03 m of padding
# around a 0.14 m coil, so each step costs several times the last, and a
# bracket is all the review needs.
RESOLUTION_LADDER = [RESOLUTION, 0.013, 0.011]


def attempt(comm, resolution, conductor_resolution):
    """Mesh one case.  Returns (ok, cells_or_None, message, seconds).

    The cell count is reduced across ranks -- `index_map(3).size_local` is
    rank-local and a rank-local count is not a number worth printing.
    """
    t0 = time.time()
    try:
        mesh, _cell_tags, _facet_tags = MeshGenerator.birdcage_port_domain(
            leg_count=LEG_COUNT,
            ring_radius=RING_RADIUS,
            leg_width=LEG_WIDTH,
            leg_spacing=LEG_SPACING,
            coil_length=COIL_LENGTH,
            ring_minor_radius=RING_MINOR_RADIUS,
            phantom_radius=PHANTOM_RADIUS,
            phantom_height=PHANTOM_HEIGHT,
            port_box_size=PORT_BOX_SIZE,
            air_padding=AIR_PADDING,
            resolution=resolution,
            conductor_resolution=conductor_resolution,
            comm=comm,
        )
    except Exception as exc:  # gmsh raises a bare Exception carrying its text
        elapsed = time.time() - t0
        # The generator only reaches its `gmsh.finalize()` on the success
        # path, so a failed case would otherwise leak model state forward.
        try:
            gmsh.finalize()
        except Exception:
            pass
        return False, None, str(exc).strip().splitlines()[-1], elapsed
    local = mesh.topology.index_map(mesh.topology.dim).size_local
    cells = comm.allreduce(local, op=MPI.SUM)
    return True, cells, "", time.time() - t0


def _report(rank0, label, ok, cells, message, elapsed):
    if not rank0:
        return
    if ok:
        print(f"  {label} OK    {cells:>8d} cells ({elapsed:.1f} s)", flush=True)
    else:
        print(f"  {label} FAIL  {message} ({elapsed:.1f} s)", flush=True)


def main():
    comm = MPI.COMM_WORLD
    rank0 = comm.rank == 0

    if rank0:
        print("birdcage_port_domain: where does the 0.11 image stop meshing?")
        print(
            f"  fixture: leg_count={LEG_COUNT}  ring_radius={RING_RADIUS} m  "
            f"ring_minor_radius={RING_MINOR_RADIUS} m; {comm.size} rank(s)\n"
        )
        print(
            f"Leg A -- the fixture's global resolution ({RESOLUTION}), "
            "conductor sizing swept:"
        )

    for conductor_resolution in CONDUCTOR_LADDER:
        ok, cells, message, elapsed = attempt(comm, RESOLUTION, conductor_resolution)
        comm.Barrier()
        if conductor_resolution is None:
            label = "h_c = None    (baseline)"
        else:
            label = f"h_c = {conductor_resolution:<9.4e}        "
        _report(rank0, label, ok, cells, message, elapsed)

    if rank0:
        print(
            "\nLeg B -- the baseline's conductor sizing (h_c = None), "
            "global resolution stepped finer:"
        )

    for resolution in RESOLUTION_LADDER:
        ok, cells, message, elapsed = attempt(comm, resolution, None)
        comm.Barrier()
        _report(rank0, f"h = {resolution:<7.4f}            ", ok, cells, message, elapsed)

    if rank0:
        print("\nMeasurement only -- no assertion, nothing re-recorded.")


if __name__ == "__main__":
    main()
