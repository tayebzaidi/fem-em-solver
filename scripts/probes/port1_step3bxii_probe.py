"""`PORT-1` step 3b-xii — mesh-only cost probe for the gapped fixture at padding 0.10.

Not a test.  Step 3b-xii rebuilds the **gapped** two-torus pair at
``air_padding = 0.10`` (nothing else moves) and computes both routes on it —
the corrected terminal-to-terminal estimator and the σ = 0 closed-footprint
control — to discriminate between 3b-x-b's two open dispositions.

The §7 plan requires the mesh cost to be measured before any solve is bought,
with the stop rule: **> ~230 000 cells ⇒ report the count and stop**.  On
record, the gapped fixture at padding 0.08 gives 178 055 cells
(``20260807T110513Z_PORT-1-step3bxb-gate-n2.log``); the *ungapped* sweep of
step 3b-xi grew 1.132× from padding 0.08 to 0.10 (119 738 → 135 542), so
~201 000 is the expectation.  237 926 cells once died in MUMPS at 180 s.

This probe also re-meshes padding 0.08 so the 178 055 on record is confirmed
on today's build rather than assumed — the fixture-identity anchor the plan
demands, at the mesh level.

Run (complex build not required — meshing only)::

    docker compose exec -T fem-em-solver bash -lc \\
      'cd /workspace && PYTHONPATH=/workspace/src mpiexec -n 2 python3 \\
       scripts/probes/port1_step3bxii_probe.py'
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

# The gapped fixture's own parameters, copied from
# tests/validation/test_port_gap_voltage_impedance.py so the probe meshes the
# same solid the gates will.
GAP_ANGLE = 0.30
GAP_BURIAL = 1.0e-3
GAP_OVERHANG = 2.0e-4
GAP_ARC_RESOLUTION = 3.0e-4

PADDINGS = (0.08, 0.10)

# The stop rule from the §7 step-3b-xii plan.
CELL_CEILING = 230_000

# Cells measured previously on the *gapped* fixture (None = never meshed here).
ON_RECORD = {0.08: 178_055, 0.10: None}


def main() -> None:
    comm = MPI.COMM_WORLD
    counts = {}
    for padding in PADDINGS:
        t0 = time.perf_counter()
        msh, cell_tags, facet_tags = MeshGenerator.two_torus_domain(
            separation=SEPARATION,
            major_radius=MAJOR_RADIUS,
            minor_radius=MINOR_RADIUS,
            resolution=H_FAR,
            air_padding=padding,
            wire_resolution=H_WIRE,
            far_resolution=H_FAR,
            port_gap=True,
            gap_angle=GAP_ANGLE,
            gap_burial=GAP_BURIAL,
            gap_overhang=GAP_OVERHANG,
            gap_arc_resolution=GAP_ARC_RESOLUTION,
            comm=comm,
        )
        t_mesh = time.perf_counter() - t0
        tdim = msh.topology.dim
        # index_map(...).size_local is rank-local.
        ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
        counts[padding] = ncells
        # The tag set is rank-local too; reduce it so a partition that gave one
        # rank no gap cells cannot look like a missing tag.
        local_tags = set(int(v) for v in np.unique(cell_tags.values))
        all_tags = sorted(set().union(*comm.allgather(local_tags)))
        local_ftags = set(int(v) for v in np.unique(facet_tags.values))
        all_ftags = sorted(set().union(*comm.allgather(local_ftags)))
        half_x = MAJOR_RADIUS + MINOR_RADIUS + padding
        half_z = SEPARATION / 2 + MINOR_RADIUS + padding
        recorded = ON_RECORD[padding]
        delta = "never meshed at this padding" if recorded is None else (
            f"{ncells / recorded:.6f}x the {recorded} on record"
        )
        if comm.rank == 0:
            print(
                f"[PORT-1 step 3b-xii probe] gapped, padding {padding} m: "
                f"half_x = {half_x:.3f} m, half_z = {half_z:.3f} m, "
                f"{ncells} cells ({delta}), mesh {t_mesh:.1f} s, "
                f"cell tags {all_tags}, facet tags {all_ftags}",
                flush=True,
            )

    over = [p for p, n in counts.items() if n > CELL_CEILING]
    if comm.rank == 0:
        print(
            "[PORT-1 step 3b-xii probe] counts "
            + ", ".join(f"{p}: {counts[p]}" for p in PADDINGS)
            + f"; ceiling {CELL_CEILING}; "
            + ("STOP — over ceiling at " + ", ".join(str(p) for p in over)
               if over else "all clear, discriminator may solve"),
            flush=True,
        )
        print(
            "[PORT-1 step 3b-xii probe] gapped cell growth 0.08 -> 0.10: "
            f"{counts[0.10] / counts[0.08]:.4f}x "
            "(ungapped sweep grew 1.1320x over the same step)",
            flush=True,
        )
    assert np.isfinite(list(counts.values())).all()


if __name__ == "__main__":
    main()
