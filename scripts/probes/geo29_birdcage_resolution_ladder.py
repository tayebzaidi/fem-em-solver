"""`GEO-29` — global-resolution cost ladder of the unloaded F-small birdcage.

MEASUREMENT ONLY. This script asserts nothing (beyond printing the 116 085
``size_global`` control on the 0.015 rung and its ratio), is imported by
nothing, and changes no `src/` file, band or record. It answers one question:
what does refining the *global* ``resolution`` of the `WF-6` step-4 birdcage
port fixture cost in cells / time / memory, and does the interior air cell size
the B1+ gate samples at actually fall with ``resolution`` — or is it pinned by
the conductor refinement's gradient?

The mesh is `birdcage_port_domain` with exactly the parameter set
``tests/mesh/test_birdcage_port_sheets._build(True)`` passes (constants
imported, never retyped); only the global ``resolution`` is swept.  ``_build``
itself hard-codes ``resolution=RESOLUTION``, so the generator is called here
directly with that one keyword replaced and every other keyword taken from the
same module-level constants the helper uses.

Rungs: 0.015 (the control), 0.012, 0.0095, 0.0075.

Stop rule, pre-registered in the §7 `GEO-29` row and implemented literally
below: a rung above 900 000 cells or 300 s to mesh is recorded and the ladder
stops; the next rung is attempted only if the previous rung's count scaled by
``(h_prev/h_next)**3`` stays under both ceilings.

Rank-safety: ``size_global`` is read after distribution; every count is
rank-local and reduced with ``MPI.SUM``; ghost cells are counted once by
restricting to ``index_map(3).size_local`` (`OPS-39`'s ``_census`` fix);
``dolfinx.cpp.mesh.h`` takes *local* cell indices.  gmsh is serial and meshes
on rank 0, so this is run at ``-n 1``.

Run (real build, no solve, no complex mode):

    mpiexec -n 1 python3 -u scripts/probes/geo29_birdcage_resolution_ladder.py
"""

from __future__ import annotations

import resource
import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

import dolfinx.cpp as _dcpp

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402
from tests.mesh.test_birdcage_leg_gaps import LEG_GAP_LENGTH  # noqa: E402
from tests.mesh.test_birdcage_port_sheet_prerequisite import (  # noqa: E402
    CONDUCTOR_RESOLUTION,
)
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

# The control: `20260908T004020Z_WF-6.log:1881`. Printed and compared, never
# asserted — a miss is an `OPS-18`-class drift to record and stop on.
CONTROL_CELL_RECORD = 116085

CONDUCTOR_TAG, AIR_TAG, PHANTOM_TAG = 1, 2, 3

# The rungs, coarse to fine. The first is `RESOLUTION` itself (0.015).
RUNGS = (RESOLUTION, 0.012, 0.0095, 0.0075)

# Pre-registered ceilings.
MAX_CELLS = 900_000
MAX_MESH_SECONDS = 300.0

# The interior region the B1+ gate samples at.
INTERIOR_R_FRAC = 0.5
INTERIOR_HALF_Z = 0.01


def _print(text, comm):
    if comm.rank == 0:
        print(text, flush=True)


def _peak_rss_gib(comm):
    """Peak RSS of this process, max-reduced across ranks. Linux: KiB."""
    local = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / (1024.0**2)
    return float(comm.allreduce(local, op=MPI.MAX))


def _build_rung(resolution, comm):
    """One rung: `_build(True)`'s parameter set with `resolution` replaced."""
    started = time.perf_counter()
    mesh, cell_tags, _facet_tags, diagnostics = MeshGenerator.birdcage_port_domain(
        leg_count=LEG_COUNT,
        ring_radius=RING_RADIUS,
        leg_width=LEG_WIDTH,
        leg_spacing=LEG_SPACING,
        coil_length=COIL_LENGTH,
        ring_minor_radius=RING_MINOR_RADIUS,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        port_box_size=PORT_BOX_SIZE,
        leg_gap_length=LEG_GAP_LENGTH,
        emit_port_sheets=True,
        air_padding=AIR_PADDING,
        resolution=float(resolution),
        conductor_resolution=CONDUCTOR_RESOLUTION,
        phantom_resolution=None,
        as_hole=False,
        comm=comm,
        return_diagnostics=True,
    )
    return mesh, cell_tags, diagnostics, time.perf_counter() - started


def _census(mesh, cell_tags, comm):
    """Owned-cell tag counts and the interior air mean circumradius."""
    tdim = mesh.topology.dim
    n_owned = int(mesh.topology.index_map(tdim).size_local)

    tag_of = np.zeros(n_owned, dtype=np.int32)
    idx = np.asarray(cell_tags.indices)
    val = np.asarray(cell_tags.values)
    keep = idx < n_owned
    tag_of[idx[keep]] = val[keep]

    counts = {}
    for name, tag in (
        ("air", AIR_TAG),
        ("coil", CONDUCTOR_TAG),
        ("phantom", PHANTOM_TAG),
    ):
        counts[name] = comm.allreduce(
            int(np.count_nonzero(tag_of == tag)), op=MPI.SUM
        )
    # The gap: every owned cell in neither core tag — the port-box halves
    # tagged 100+i / 200+i by the generator.
    is_core = np.isin(tag_of, (CONDUCTOR_TAG, AIR_TAG, PHANTOM_TAG))
    counts["gap"] = comm.allreduce(int(np.count_nonzero(~is_core)), op=MPI.SUM)

    # Interior air cell size: r <= 0.5R, |z| <= 0.01 m.
    x = mesh.geometry.x
    dofmap = np.asarray(mesh.geometry.dofmap)
    if dofmap.ndim == 1:
        dofmap = dofmap.reshape(-1, 4)
    mid = x[dofmap[:n_owned, :4]].mean(axis=1)
    r2 = mid[:, 0] ** 2 + mid[:, 1] ** 2
    sel = (
        (tag_of == AIR_TAG)
        & (r2 <= (INTERIOR_R_FRAC * RING_RADIUS) ** 2)
        & (np.abs(mid[:, 2]) <= INTERIOR_HALF_Z)
    )
    local_ids = np.arange(n_owned, dtype=np.int32)
    h_all = np.asarray(_dcpp.mesh.h(mesh._cpp_object, tdim, local_ids))
    n_int = comm.allreduce(int(np.count_nonzero(sel)), op=MPI.SUM)
    h_sum = comm.allreduce(float(h_all[sel].sum()), op=MPI.SUM)
    h_max = comm.allreduce(
        float(h_all[sel].max()) if np.any(sel) else -np.inf, op=MPI.MAX
    )
    h_min = comm.allreduce(
        float(h_all[sel].min()) if np.any(sel) else np.inf, op=MPI.MIN
    )
    counts["interior_air_cells"] = n_int
    counts["interior_h_mean"] = (h_sum / n_int) if n_int else float("nan")
    counts["interior_h_max"] = h_max if n_int else float("nan")
    counts["interior_h_min"] = h_min if n_int else float("nan")
    return counts


def main():
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    _print(
        "\n[GEO-29] global-resolution cost ladder of the unloaded F-small "
        "birdcage port fixture (measurement-only; asserts nothing)\n"
        f"[GEO-29] ranks={comm.size}  rungs={RUNGS}  "
        f"conductor_resolution={CONDUCTOR_RESOLUTION:.6e} (pinned)  "
        f"phantom_resolution=None (default)\n"
        f"[GEO-29] stop rule: record and stop above {MAX_CELLS} cells or "
        f"{MAX_MESH_SECONDS:.0f} s to mesh; next rung attempted only if "
        f"count*(h_prev/h_next)^3 stays under both\n"
        f"[GEO-29] interior region for the cell-size statistic: air cells with "
        f"r <= {INTERIOR_R_FRAC}R = {INTERIOR_R_FRAC * RING_RADIUS:.4f} m and "
        f"|z| <= {INTERIOR_HALF_Z} m",
        comm,
    )

    rows = []
    stopped_at = None
    for i, h in enumerate(RUNGS):
        if i > 0:
            prev = rows[-1]
            scale = (rows[-1]["h"] / h) ** 3
            pred_cells = prev["cells"] * scale
            pred_time = prev["mesh_s"] * scale
            _print(
                f"[GEO-29] licence check for h={h:g}: previous {prev['cells']} "
                f"cells x (h_prev/h_next)^3={scale:.4f} -> {pred_cells:.0f} "
                f"cells, {pred_time:.1f} s predicted",
                comm,
            )
            if pred_cells > MAX_CELLS or pred_time > MAX_MESH_SECONDS:
                stopped_at = (
                    f"licence arithmetic before h={h:g} "
                    f"({pred_cells:.0f} cells / {pred_time:.1f} s predicted)"
                )
                _print(f"[GEO-29] STOP: {stopped_at}", comm)
                break

        _print(f"\n[GEO-29] --- rung resolution={h:g} m ---", comm)
        mesh, cell_tags, diag, rung_elapsed = _build_rung(h, comm)
        n_global = int(mesh.topology.index_map(mesh.topology.dim).size_global)
        mesh_s = float(diag["mesh_wall_time_s"])
        rss = _peak_rss_gib(comm)
        c = _census(mesh, cell_tags, comm)

        row = {
            "h": float(h),
            "cells": n_global,
            "mesh_s": mesh_s,
            "rung_s": rung_elapsed,
            "rss_gib": rss,
            **c,
        }
        rows.append(row)

        control = ""
        if i == 0:
            control = (
                f"  CONTROL record={CONTROL_CELL_RECORD} ratio="
                f"{n_global / CONTROL_CELL_RECORD:.6f}"
            )
        _print(
            f"[GEO-29] h={h:g}  size_global={n_global}{control}\n"
            f"[GEO-29]   tags: air={c['air']}  coil={c['coil']}  "
            f"phantom={c['phantom']}  gap(port-box 100+i/200+i)={c['gap']}  "
            f"(sum={c['air'] + c['coil'] + c['phantom'] + c['gap']})\n"
            f"[GEO-29]   mesh wall time={mesh_s:.2f} s  rung wall time="
            f"{rung_elapsed:.2f} s  peak RSS={rss:.3f} GiB\n"
            f"[GEO-29]   interior air cells={c['interior_air_cells']}  "
            f"mean h={c['interior_h_mean']:.6e} m  "
            f"min={c['interior_h_min']:.6e}  max={c['interior_h_max']:.6e}",
            comm,
        )

        if n_global > MAX_CELLS or mesh_s > MAX_MESH_SECONDS:
            stopped_at = (
                f"h={h:g} exceeded a ceiling ({n_global} cells, {mesh_s:.1f} s)"
            )
            _print(f"[GEO-29] STOP: {stopped_at}", comm)
            break

        if i == 0 and n_global != CONTROL_CELL_RECORD:
            stopped_at = (
                f"control h={h:g} read {n_global} != {CONTROL_CELL_RECORD} "
                f"(`OPS-18`-class mesher drift)"
            )
            _print(f"[GEO-29] STOP: {stopped_at}", comm)
            break

    elapsed = time.perf_counter() - started

    if comm.rank == 0:
        print("\n[GEO-29] ladder table")
        print(
            "  {:>9s} {:>10s} {:>9s} {:>9s} {:>9s} {:>8s} {:>9s} {:>7s} "
            "{:>7s} {:>12s} {:>7s}".format(
                "h [m]", "cells", "air", "coil", "phantom", "gap",
                "mesh s", "RSS GiB", "int N", "int mean h", "h/h_0",
            )
        )
        h0 = rows[0]["interior_h_mean"] if rows else float("nan")
        c0 = rows[0]["cells"] if rows else 1
        for r in rows:
            print(
                "  {:9.5f} {:10d} {:9d} {:9d} {:9d} {:8d} {:9.2f} {:7.3f} "
                "{:7d} {:12.6e} {:7.4f}".format(
                    r["h"], r["cells"], r["air"], r["coil"], r["phantom"],
                    r["gap"], r["mesh_s"], r["rss_gib"],
                    r["interior_air_cells"], r["interior_h_mean"],
                    r["interior_h_mean"] / h0,
                )
            )
        print("\n[GEO-29] growth against the coarsest rung (ideal 1/h^3)")
        for r in rows:
            ideal = (rows[0]["h"] / r["h"]) ** 3
            print(
                "    h={:7.5f}  cells/cells_0={:7.4f}  ideal (h_0/h)^3={:7.4f}"
                "  air/air_0={:7.4f}  mesh_s/mesh_s_0={:7.4f}".format(
                    r["h"], r["cells"] / c0, ideal,
                    r["air"] / rows[0]["air"], r["mesh_s"] / rows[0]["mesh_s"],
                )
            )
        monotone = all(
            rows[i + 1]["cells"] > rows[i]["cells"] for i in range(len(rows) - 1)
        )
        print(
            f"\n[GEO-29] cell count monotone in 1/h: {monotone} "
            f"(a `GEO-22`-class non-monotonicity is a finding, not a failure)"
        )
        print(
            f"[GEO-29] stop rule fired: "
            f"{stopped_at if stopped_at else 'no — ladder ran to completion'}"
        )
        print(f"[GEO-29] probe wall time={elapsed:.2f} s", flush=True)


if __name__ == "__main__":
    main()
