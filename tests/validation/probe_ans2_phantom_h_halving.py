"""`ANS-2` step 4 (i) — the cost probe for the halved phantom rung.

Measurement only: no assertion, no band, no gate.  Builds the `MAT-4` /
`GEO-27` four-port birdcage fixture at ``phantom_resolution`` = 0.00125 m (half
the `GEO-27` rung the `ANS-2` benchmark runs on) and performs **one** driven
solve, printing the numbers §9's item 1 pre-registers as the go/no-go reading:
cells, phantom (tag-3) cells, global unknowns, solve seconds, and
``ru_maxrss`` per rank.

The §9 stop rule (2026-09-19 03:00 review): **if this probe reads > 15 min or
> 40 GiB summed, the step re-prices to an XL cost probe and nothing else in
the item runs.**

Run it (complex build required)::

    mpiexec -n 8 python3 tests/validation/probe_ans2_phantom_h_halving.py
"""

from __future__ import annotations

import os
import resource
import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import default_scalar_type

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.validation.test_birdcage_b1_plus_map import _solve_driven  # noqa: E402
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    build_four_port_sweep,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    PHANTOM_CELL_TAG,
)

#: The rung under probe — half the `GEO-27` rung (0.0025 m) the `ANS-2`
#: benchmark runs on.  Overridable so a cheaper bracket can be taken first.
HALVED_RUNG_PHANTOM_RESOLUTION_M = float(
    os.environ.get("FEM_EM_ANS2_PHANTOM_RESOLUTION", "0.00125")
)


def _global_phantom_cells(msh, cell_tags, comm) -> int:
    """Tag-3 cell count, owned cells only, reduced — ``.values`` is rank-local."""
    n_local = msh.topology.index_map(msh.topology.dim).size_local
    local = int(
        np.count_nonzero(
            (cell_tags.values == PHANTOM_CELL_TAG) & (cell_tags.indices < n_local)
        )
    )
    return int(comm.allreduce(local, op=MPI.SUM))


def main() -> None:
    comm = MPI.COMM_WORLD
    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "complex build required: source /usr/local/bin/dolfinx-complex-mode"
        )

    res = HALVED_RUNG_PHANTOM_RESOLUTION_M
    if comm.rank == 0:
        print(
            f"[probe] ANS-2 step 4 cost probe: phantom_resolution = {res} m at "
            f"mpiexec -n {comm.size}",
            flush=True,
        )

    comm.Barrier()
    t_mesh = time.perf_counter()
    sweep = build_four_port_sweep(phantom_resolution=res)
    comm.Barrier()
    t_mesh = time.perf_counter() - t_mesh

    msh = sweep["mesh"]
    cells = int(sweep["cells"])
    phantom_cells = _global_phantom_cells(msh, sweep["cell_tags"], comm)
    if comm.rank == 0:
        print(
            f"[probe] mesh built in {t_mesh:.1f} s: {cells} cells, "
            f"{phantom_cells} phantom (tag-{PHANTOM_CELL_TAG}) cells",
            flush=True,
        )

    solved = _solve_driven(sweep, "P1")
    imap = solved["fields"].e_complex.function_space.dofmap.index_map
    bs = solved["fields"].e_complex.function_space.dofmap.index_map_bs
    unknowns = int(imap.size_global) * int(bs)
    t_solve = float(solved["solve_time"])

    rss_gib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0)
    per_rank = comm.gather(rss_gib, root=0)

    if comm.rank == 0:
        total = t_mesh + t_solve
        print(
            f"[probe] unknowns (global, degree-1 N1curl) {unknowns}\n"
            f"[probe] one drive (P1) solved in {t_solve:.1f} s; mesh + one drive "
            f"= {total:.1f} s",
            flush=True,
        )
        print(
            "[probe] ru_maxrss per rank [GiB]: "
            + "  ".join(f"{v:.2f}" for v in per_rank)
            + f"   summed {sum(per_rank):.2f} GiB   max {max(per_rank):.2f} GiB",
            flush=True,
        )
        four_drives = t_mesh + 4.0 * t_solve
        print(
            f"[probe] EXTRAPOLATION to the four-drive run: {four_drives:.0f} s "
            f"({four_drives / 60.0:.1f} min) plus post-processing\n"
            f"[probe] STOP RULE (§9 item 1): stop if > 900 s or > 40 GiB summed "
            f"-> reads {four_drives:.0f} s / {sum(per_rank):.2f} GiB -> "
            + ("STOP (re-price to XL)" if (four_drives > 900.0 or sum(per_rank) > 40.0) else "PROCEED"),
            flush=True,
        )


if __name__ == "__main__":
    main()
