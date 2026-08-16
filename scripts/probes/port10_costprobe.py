"""`PORT-10` cost probe: the two padding-0.10 corners, mesh only.

The chunk's cost rule is binding — "cost-probe first ... single command under
1200 s or the case shrinks" — and two of the factorial's four corners have
never been meshed: ``(0.10, baseline)`` is known at 194 985 cells from the
3b-xii probe, but ``(0.10, 6.0e-4)`` has no measurement at all, and 3b-xvi's
own stop rule exists because 237 926 cells once died in MUMPS at 180 s on the
ungapped padding-0.12 fixture.  This builds both padded corners, prints cells
and mesh time, and asserts nothing: it exists so the gate command is sized
from a measurement instead of an extrapolation.

Run (complex build not required — no solve here, but the import chain is the
test module's, so it is run under the same environment as the gate)::

    scripts/testing/run_and_log.sh PORT-10-costprobe "docker compose exec -T \\
      fem-em-solver bash -lc 'cd /workspace && \\
      source /usr/local/bin/dolfinx-complex-mode && \\
      PYTHONPATH=/workspace/src:/workspace FEM_EM_REQUIRE_COMPLEX=1 \\
      timeout -k 30 300 mpiexec -n 2 python3 scripts/probes/port10_costprobe.py'"
"""

from __future__ import annotations

from mpi4py import MPI

from tests.validation.test_port_systematics_composition import (
    BASELINE_GAP_BOX_RESOLUTION,
    CELL_CEILING,
    PADDED_AIR_PADDING,
    REFINED_GAP_BOX_RESOLUTION,
    _build,
)

# Measured, for the extrapolation the probe replaces: padding 0.08 meshes at
# 178 055 cells (baseline, 35.8 s) and 246 364 (h_box 6.0e-4, 49.3 s), and
# padding 0.10 baseline at 194 985 (1.0951x the 0.08 baseline).
CELLS_008_BASE = 178_055
CELLS_008_REFINED = 246_364
CELLS_010_BASE = 194_985


def main() -> int:
    comm = MPI.COMM_WORLD
    for label, box in (
        ("padded", BASELINE_GAP_BOX_RESOLUTION),
        ("joint", REFINED_GAP_BOX_RESOLUTION),
    ):
        msh, cell_tags, facet_tags, t_mesh = _build(comm, PADDED_AIR_PADDING, box)
        tdim = msh.topology.dim
        ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
        if comm.rank == 0:
            print(
                f"[PORT-10 costprobe] {label}: padding {PADDED_AIR_PADDING} m, "
                f"h_box {'baseline' if box is None else f'{box:.1e} m'} -> "
                f"{ncells} cells in {t_mesh:.1f} s "
                f"({ncells / CELLS_008_BASE:.4f}x the padding-0.08 baseline "
                f"{CELLS_008_BASE}; ceiling {CELL_CEILING})",
                flush=True,
            )
        del msh, cell_tags, facet_tags
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
