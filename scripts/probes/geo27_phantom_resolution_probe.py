"""`GEO-27` — the phantom-resolution cost probe for the 1 g SAR rung.

MEASUREMENT ONLY. This script asserts nothing, is imported by nothing, and
changes nothing in `src/` or `tests/`. It ladders
``MeshGenerator.birdcage_port_domain(phantom_resolution=...)`` exactly as
`tests/mesh/test_birdcage_phantom_resolution.py` calls it — through that
module's own ``_build`` helper on the F-small four-port fixture, real build,
no solve — and prints per rung:

* total cells, as ``mesh.topology.index_map(dim).size_global`` **after
  distribution** (never a rank-local ``cell_tags.values`` length: gmsh meshes
  on rank 0 and the tag arrays include ghosts);
* phantom cells (tag 3), the owned-cell count reduced with ``MPI.SUM`` — the
  test module's own ``_global_tag_cell_count``, reused rather than re-derived;
* the mesh wall time reported by the generator's diagnostics, and the rung's
  own wall time;
* the phantom share of the cells;
* the cells across each C95.3 averaging ball, ``2a/h`` with
  ``a_1g = 6.2 mm`` and ``a_10g = 13.4 mm`` (the radii `MAT-4` step 4's gate
  computes for a 1 g / 10 g ball at rho = 1000 kg/m^3).

Why this exists: `MAT-4` step 4's printed 1 g column reads a worst C4 pair of
6.8383% on the 0.0075 m rung, where the 1 g ball spans ~1.7 cells. That is a
mesh statement, not an operator one, and the route to a 1 g gate is ``h``.
The question the ladder answers is the **first rung with >= 4 cells across
the 1 g ball, and what that rung costs**.

Pre-registered stop rule: a rung above **300 000 cells** or **120 s** to mesh
is recorded and the ladder stops there — no finer rung is attempted.

Pre-registered control: the 0.0075 rung must reproduce **120 499** cells and
**2 746** tag-3 cells (`20260907T140658Z_EX-53.log:1875`, first measured at
`20260902T140410Z_WF-6-step3f0.log:13720`). A miss there is an `OPS-18`-class
mesher-drift negative result: it is recorded and the ladder stops, and nothing
is fixed.

A rung that fails to mesh ("Invalid boundary mesh (overlapping facets)") is a
`GEO-23`-class record — it is caught, printed, and the ladder continues. Note
that a gmsh raise on rank 0 alone would deadlock at ``-n 2``; the rungs here
are *refinements* of a rung known to mesh, and every rung's line is flushed
before the next build starts, so a hang leaves the completed rungs in the log.

Run (inside the container, through the harness)::

    mpiexec -n 2 python3 scripts/probes/geo27_phantom_resolution_probe.py
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

from mpi4py import MPI

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.mesh.test_birdcage_phantom_resolution import (  # noqa: E402
    _global_tag_cell_count,
)
from tests.mesh.test_birdcage_port_sheets import _build  # noqa: E402

# The ladder, coarse first — the control rung leads so the anchor is in hand
# before any finer build can hang or fail.
RUNGS = (0.0075, 0.005, 0.00375, 0.0025)

# The control rung's records (printed records in the logs above, not module
# constants). Compared and printed; never asserted.
CONTROL_RESOLUTION = 0.0075
CONTROL_CELL_RECORD = 120499
CONTROL_PHANTOM_RECORD = 2746

# C95.3 averaging-ball radii at rho = 1000 kg/m^3 [m]: a = (3m/(4 pi rho))^(1/3).
A_1G_M = 6.2e-3
A_10G_M = 13.4e-3

# Pre-registered stop rule.
MAX_CELLS = 300_000
MAX_MESH_SECONDS = 120.0


def _read(phantom_resolution, comm):
    """One rung, reduced to the numbers the table prints."""
    started = time.perf_counter()
    mesh, cells, _facets, diag, build_elapsed = _build(
        True, phantom_resolution=phantom_resolution
    )
    n_cells = int(mesh.topology.index_map(mesh.topology.dim).size_global)
    n_phantom = _global_tag_cell_count(mesh, cells, 3, comm)
    return {
        "h": phantom_resolution,
        "cells": n_cells,
        "phantom_cells": n_phantom,
        "phantom_share": n_phantom / n_cells if n_cells else float("nan"),
        "mesh_wall_time_s": float(diag["mesh_wall_time_s"]),
        "rung_s": float(build_elapsed),
        "wall_s": time.perf_counter() - started,
        "cells_across_1g": 2.0 * A_1G_M / phantom_resolution,
        "cells_across_10g": 2.0 * A_10G_M / phantom_resolution,
    }


def _print(text, comm):
    if comm.rank == 0:
        print(text, flush=True)


def main():
    comm = MPI.COMM_WORLD
    _print(
        "=" * 78
        + "\n[GEO-27] phantom-resolution ladder on birdcage_port_domain "
        "(F-small, real, no solve)"
        f"\n[GEO-27] rungs {RUNGS}  stop rule: > {MAX_CELLS} cells or "
        f"> {MAX_MESH_SECONDS:.0f} s to mesh"
        f"\n[GEO-27] balls: a_1g = {A_1G_M * 1e3:.1f} mm, "
        f"a_10g = {A_10G_M * 1e3:.1f} mm (rho = 1000 kg/m^3)"
        + "\n"
        + "=" * 78,
        comm,
    )

    rows = []
    for h in RUNGS:
        _print(f"\n[GEO-27 rung] starting h_p = {h} ...", comm)
        try:
            r = _read(h, comm)
        except Exception:  # noqa: BLE001 — a GEO-23-class record, not a fix
            _print(
                f"[GEO-27 rung] h_p = {h}: FAILED TO MESH — GEO-23-class record, "
                "continuing to the next rung\n"
                + traceback.format_exc(),
                comm,
            )
            rows.append({"h": h, "failed": True})
            continue

        rows.append(r)
        _print(
            f"[GEO-27 rung] h_p = {r['h']}"
            f"\n  cells (size_global)   {r['cells']}"
            f"\n  phantom cells (tag 3) {r['phantom_cells']}"
            f"\n  phantom share         {r['phantom_share']:.6f}"
            f"\n  mesh_wall_time_s      {r['mesh_wall_time_s']:.2f}"
            f"\n  rung_s                {r['rung_s']:.2f}"
            f"\n  cells across 1 g ball {r['cells_across_1g']:.3f}  (2a/h)"
            f"\n  cells across 10 g ball {r['cells_across_10g']:.3f}  (2a/h)",
            comm,
        )

        if h == CONTROL_RESOLUTION:
            ok = (
                r["cells"] == CONTROL_CELL_RECORD
                and r["phantom_cells"] == CONTROL_PHANTOM_RECORD
            )
            _print(
                f"  control vs record     cells {r['cells']} vs "
                f"{CONTROL_CELL_RECORD}, phantom {r['phantom_cells']} vs "
                f"{CONTROL_PHANTOM_RECORD} -> "
                + ("REPRODUCED" if ok else "MISS (OPS-18-class mesher drift)"),
                comm,
            )
            if not ok:
                _print(
                    "[GEO-27] NEGATIVE RESULT: the control did not reproduce; "
                    "the ladder stops here and nothing is fixed.",
                    comm,
                )
                break

        if r["cells"] > MAX_CELLS or r["mesh_wall_time_s"] > MAX_MESH_SECONDS:
            _print(
                f"[GEO-27] STOP RULE HIT at h_p = {h}: {r['cells']} cells / "
                f"{r['mesh_wall_time_s']:.2f} s to mesh; no finer rung is "
                "attempted.",
                comm,
            )
            break

    _print("\n" + "=" * 78 + "\n[GEO-27 table]", comm)
    _print(
        "| h_p (m) | OK/FAIL | cells | phantom cells | phantom share | "
        "mesh s | rung s | 2a_1g/h | 2a_10g/h |",
        comm,
    )
    for r in rows:
        if r.get("failed"):
            _print(
                f"| {r['h']} | FAIL | - | - | - | - | - | "
                f"{2.0 * A_1G_M / r['h']:.2f} | {2.0 * A_10G_M / r['h']:.2f} |",
                comm,
            )
            continue
        _print(
            f"| {r['h']} | OK | {r['cells']} | {r['phantom_cells']} | "
            f"{r['phantom_share']:.4f} | {r['mesh_wall_time_s']:.2f} | "
            f"{r['rung_s']:.2f} | {r['cells_across_1g']:.2f} | "
            f"{r['cells_across_10g']:.2f} |",
            comm,
        )

    good = [r for r in rows if not r.get("failed") and r["cells_across_1g"] >= 4.0]
    if good:
        first = good[0]
        _print(
            f"\n[GEO-27 answer] first rung with >= 4 cells across the 1 g ball: "
            f"h_p = {first['h']} m ({first['cells_across_1g']:.2f} cells across), "
            f"costing {first['cells']} cells and {first['mesh_wall_time_s']:.2f} s "
            f"to mesh ({first['phantom_cells']} phantom cells, share "
            f"{first['phantom_share']:.4f}).",
            comm,
        )
    else:
        _print(
            "\n[GEO-27 answer] no rung reached >= 4 cells across the 1 g ball "
            "before the ladder stopped.",
            comm,
        )
    _print("=" * 78, comm)


if __name__ == "__main__":
    main()
