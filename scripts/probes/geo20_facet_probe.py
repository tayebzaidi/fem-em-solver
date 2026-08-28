"""Localize the facet P8 loses at -n 12: is it dropped by `counts == 2`?"""
import sys
sys.path.insert(0, "/workspace"); sys.path.insert(0, "/workspace/src")
import numpy as np, dolfinx
from mpi4py import MPI
from tests.mesh.test_birdcage_ring_gaps import (
    LEG_GAP_LENGTH, RING_GAP_LENGTH, _build,
)
from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER

comm = MPI.COMM_WORLD
mesh, cells, _, diag, _ = _build(
    ring_gap_length=RING_GAP_LENGTH, leg_gap_length=LEG_GAP_LENGTH,
    emit_port_sheets=True,
)
PORT = 8
port_tags = (PORT_LOWER + PORT, PORT_UPPER + PORT)

tdim = mesh.topology.dim; fdim = tdim - 1
mesh.topology.create_entities(fdim)
mesh.topology.create_connectivity(fdim, tdim)

V = dolfinx.fem.functionspace(mesh, ("DG", 0))
m = dolfinx.fem.Function(V); m.x.array[:] = 0.0
c2d = V.dofmap.list.reshape(-1)
m.x.array[c2d[cells.indices]] = cells.values
m.x.scatter_forward()
cv = np.rint(np.real(m.x.array[c2d])).astype(np.int32)

f2c = mesh.topology.connectivity(fdim, tdim)
off, links = f2c.offsets, f2c.array
counts = off[1:] - off[:-1]
fmap = mesh.topology.index_map(fdim)
n_owned_facets = fmap.size_local

# Facets with at least one side in port 8's two cell tags.
touch, one_sided = [], []
for f in range(len(counts)):
    sides = cv[links[off[f]:off[f + 1]]]
    if not np.isin(sides, port_tags).any():
        continue
    if f < n_owned_facets:
        touch.append(f)
        if counts[f] == 1:
            one_sided.append((f, int(sides[0])))

n_touch = comm.allreduce(len(touch), op=MPI.SUM)
n_one = comm.allreduce(len(one_sided), op=MPI.SUM)
detail = comm.gather([(comm.rank, f, s) for f, s in one_sided], root=0)

if comm.rank == 0:
    print(f"WIDTH {comm.size}: owned facets touching P8 = {n_touch}, "
          f"of which locally one-sided (counts==1) = {n_one}", flush=True)
    for chunk in detail:
        for r, f, s in chunk:
            print(f"    rank {r} facet {f} sole-side cell tag {s}", flush=True)
