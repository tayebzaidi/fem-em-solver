"""Width discriminator for the GEO-20 closure defect on the 4-leg 12-port rung.

Builds the doubly-gapped mesh once and prints every port's boundary closure,
so the same geometry can be read at several `mpiexec -n` widths.
"""
import sys
sys.path.insert(0, "/workspace")
sys.path.insert(0, "/workspace/src")

import numpy as np
from mpi4py import MPI

from tests.mesh.test_birdcage_ring_gaps import (
    EXACT, LEG_GAP_LENGTH, RING_GAP_LENGTH, RING_PORTS, LEG_COUNT,
    _build, _port_boundary_partition,
)
from tests.mesh.test_birdcage_ring_gaps import (
    AIR_IFACE, CONDUCTOR_IFACE, PHANTOM_IFACE,
)
from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER

comm = MPI.COMM_WORLD
LEG_PORTS = list(range(1, LEG_COUNT + 1))

mesh, cells, _, diag, elapsed = _build(
    ring_gap_length=RING_GAP_LENGTH,
    leg_gap_length=LEG_GAP_LENGTH,
    emit_port_sheets=True,
)
port_cell_tags = {i: (PORT_LOWER + i, PORT_UPPER + i) for i in LEG_PORTS + RING_PORTS}
counts, areas = _port_boundary_partition(mesh, cells, comm, port_cell_tags)

layout = diag["ring_port_layout"]
gap_dx, gap_dy, gap_dz = diag["port_box_size_m"]
leg_surface = 2.0 * (gap_dx * gap_dy + gap_dy * gap_dz + gap_dz * gap_dx)
ring_surface = layout["ring_port_surface_m2"]

if comm.rank == 0:
    n = mesh.topology.index_map(3).size_global
    print(f"WIDTH {comm.size} cells {n} mesh {diag['mesh_wall_time_s']:.2f}s", flush=True)
    bad = []
    for i in LEG_PORTS + RING_PORTS:
        surface = leg_surface if i in LEG_PORTS else ring_surface
        total = (areas[CONDUCTOR_IFACE + i] + areas[AIR_IFACE + i]
                 + areas[PHANTOM_IFACE + i])
        closure = total / surface
        flag = "" if abs(closure - 1.0) < EXACT else "   <-- RED"
        print(f"  P{i:<2d} closure {closure:.12f}"
              f"  facets c/a/p {counts[CONDUCTOR_IFACE+i]}/{counts[AIR_IFACE+i]}"
              f"/{counts[PHANTOM_IFACE+i]}{flag}", flush=True)
        if flag:
            bad.append(i)
    print(f"WIDTH {comm.size} RED PORTS {bad}", flush=True)
