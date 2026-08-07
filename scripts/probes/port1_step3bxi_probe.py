"""`PORT-1` step 3b-xi — mesh-only cost probe for the PEC-box padding sweep.

Not a test.  The sweep solves the *ungapped* two-torus pair at
``d = 0.04`` for air paddings ``{0.08, 0.10, 0.12}`` at ``h_far = 0.03`` and
reads ``Im Z₁₂/ωM₁₂`` at each.  The §7 plan requires the mesh cost to be
measured before any solve is bought: padding 0.12 at ``h_far = 0.02``
(237 926 cells) was once killed at 180 s inside MUMPS, and the plan's stop
rule is **any padding above ~250 000 cells ⇒ report and stop**.

On record for the two end points at ``h_far = 0.03``, ``d = 0.04``:
padding 0.08 → 119 738 cells (``20260802T183747Z_PORT-1-step1-boxsens.log``),
padding 0.12 → 154 493 cells (``20260803T110058Z_PORT-1-step2c-costprobe12.log``).
Padding 0.10 has never been meshed at this ``h_far``; that is the number this
probe buys, together with a re-measurement of the two known ones on today's
build.

Run (complex build not required — meshing only, but the sweep itself needs it)::

    docker compose exec -T fem-em-solver bash -lc \\
      'cd /workspace && PYTHONPATH=/workspace/src mpiexec -n 2 python3 \\
       scripts/probes/port1_step3bxi_probe.py'
"""

from __future__ import annotations

import time

import numpy as np
from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator

MAJOR_RADIUS = 0.04
MINOR_RADIUS = 0.005
SEPARATION = 0.04
H_FAR = 0.03
H_WIRE = 0.0025

PADDINGS = (0.08, 0.10, 0.12)

# The stop rule from the §7 step-3b-xi plan.
CELL_CEILING = 250_000

# Cells measured previously at h_far 0.03, d 0.04 (None = never meshed here).
ON_RECORD = {0.08: 119_738, 0.10: None, 0.12: 154_493}


def main() -> None:
    comm = MPI.COMM_WORLD
    counts = {}
    for padding in PADDINGS:
        t0 = time.perf_counter()
        msh, _, _ = MeshGenerator.two_torus_domain(
            separation=SEPARATION,
            major_radius=MAJOR_RADIUS,
            minor_radius=MINOR_RADIUS,
            resolution=H_FAR,
            air_padding=padding,
            wire_resolution=H_WIRE,
            far_resolution=H_FAR,
            comm=comm,
        )
        t_mesh = time.perf_counter() - t0
        tdim = msh.topology.dim
        # index_map(...).size_local is rank-local.
        ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
        counts[padding] = ncells
        half_x = MAJOR_RADIUS + MINOR_RADIUS + padding
        half_z = SEPARATION / 2 + MINOR_RADIUS + padding
        recorded = ON_RECORD[padding]
        delta = "never meshed at this h_far" if recorded is None else (
            f"{ncells / recorded:.4f}x the {recorded} on record"
        )
        if comm.rank == 0:
            print(
                f"[PORT-1 step 3b-xi probe] padding {padding} m: "
                f"half_x = {half_x:.3f} m, half_z = {half_z:.3f} m, "
                f"{ncells} cells ({delta}), mesh {t_mesh:.1f} s",
                flush=True,
            )

    over = [p for p, n in counts.items() if n > CELL_CEILING]
    if comm.rank == 0:
        print(
            "[PORT-1 step 3b-xi probe] counts "
            + ", ".join(f"{p}: {counts[p]}" for p in PADDINGS)
            + f"; ceiling {CELL_CEILING}; "
            + ("STOP — over ceiling at " + ", ".join(str(p) for p in over)
               if over else "all clear, sweep may solve"),
            flush=True,
        )
        # Solve time scales worse than linearly in cells for a direct solver;
        # step 2c measured padding 0.12 / h_far 0.03 at 167.7 s for two meshes
        # *and* two solves, so a per-padding single solve is the unit here.
        print(
            "[PORT-1 step 3b-xi probe] cell growth 0.08 -> 0.12: "
            f"{counts[PADDINGS[-1]] / counts[PADDINGS[0]]:.4f}x",
            flush=True,
        )
    assert np.isfinite(list(counts.values())).all()


if __name__ == "__main__":
    main()
