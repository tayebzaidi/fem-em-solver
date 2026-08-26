"""`GEO-17` / `mesh:5` control re-choice probe (2026-08-26 implementer slot).

Measure-first half of the 18:00 review's ruling: the `mesh:5` inverted control
(clamps-only uniform h = 0.015) clears the 0.755 CAD-recovery floor by 6.0e-6
on the 0.11 image, so it no longer separates.  This probe meshes the same
coil+phantom fixture at progressively COARSER uniform sizings and prints the
coil-tag meshed/CAD recovery for each, so the landing can adopt the first
sizing that fails the floor by >= 0.05 relative separation.

Prints only — asserts nothing, so a coarse sizing that meshes badly shows up as
a number rather than a traceback.  Run at ``-n 1`` (a rank-0 gmsh exception
deadlocks at higher widths; documented in the `GEO-17` resolution probe).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from mpi4py import MPI

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402

from tests.mesh.helpers import (  # noqa: E402
    REQUIRED_COIL_PHANTOM_TAGS,
    assert_tag_volumes_partition_domain,
)
from tests.mesh.test_mesh_tag_integrity import (  # noqa: E402
    CAD_VOLUMES,
    GEOMETRY,
    POLICY_MIN_CAD_RECOVERY,
)

COIL_TAGS = (1, 2)
TARGET_SEPARATION = 0.05  # the CONTROL_SEPARATION precedent, per the ruling

# Coarser than the fixture's own 0.015, in order.  Stop at the first that
# separates: the ruling forbids hunting past it.
CANDIDATES = (0.018, 0.020, 0.025)


def main() -> None:
    comm = MPI.COMM_WORLD
    target = POLICY_MIN_CAD_RECOVERY - TARGET_SEPARATION

    if comm.rank == 0:
        print(
            f"[probe] floor={POLICY_MIN_CAD_RECOVERY}  "
            f"need recovery <= {target:.6f} on both coil tags",
            flush=True,
        )

    for h in (GEOMETRY["resolution"], *CANDIDATES):
        geom = dict(GEOMETRY)
        geom["resolution"] = h
        started = time.perf_counter()
        mesh, cell_tags, _ = MeshGenerator.coil_phantom_domain(comm=comm, **geom)
        elapsed = time.perf_counter() - started
        volumes = assert_tag_volumes_partition_domain(
            mesh, cell_tags, REQUIRED_COIL_PHANTOM_TAGS, comm=comm,
            label=f"probe h={h}",
        )
        rec = {tag: volumes[tag] / cad for tag, cad in CAD_VOLUMES.items()}
        n_cells = mesh.topology.index_map(3).size_global
        if comm.rank == 0:
            worst = max(rec[t] for t in COIL_TAGS)
            print(
                f"\n[probe] h={h:<6} cells={n_cells:>8d} mesh={elapsed:6.2f} s  "
                f"coil recovery {rec[1]:.6f} / {rec[2]:.6f}  "
                f"phantom {rec[3]:.6f}  "
                f"margin below floor {POLICY_MIN_CAD_RECOVERY - worst:+.6f}  "
                f"{'SEPARATES' if worst <= target else 'no'}",
                flush=True,
            )


if __name__ == "__main__":
    main()
