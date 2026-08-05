"""Probe (not a test): where does the gapped two-torus mesh stall at `-n 2`?

`PORT-1` step 3b-iv, known-issues 9. Run as a script, per rank, printing a
marker before and after every collective so the hang is localised to one call
rather than to a 120-frame C++ stack:

    mpiexec -n 2 python3 tests/mesh/probe_two_torus_facets.py

Coarse on purpose -- the question is *where* it stops, not what it measures.
"""

from __future__ import annotations

import sys

import numpy as np
import ufl
from mpi4py import MPI

import dolfinx

from fem_em_solver.io.mesh import MeshGenerator, _interface_facet_tags

COMM = MPI.COMM_WORLD


def mark(msg: str) -> None:
    print(f"[probe r{COMM.rank}] {msg}", flush=True)
    sys.stdout.flush()


def main() -> None:
    mark("start")
    msh, cell_tags, facet_tags = MeshGenerator.two_torus_domain(
        separation=0.05,
        major_radius=0.02,
        minor_radius=0.005,
        resolution=0.01,
        air_padding=0.01,
        wire_resolution=0.002,
        far_resolution=0.01,
        port_gap=True,
        gap_angle=0.30,
        gap_clearance=1.0e-3,
        comm=COMM,
    )
    tdim = msh.topology.dim
    mark(
        f"mesh built: cells_local={msh.topology.index_map(tdim).size_local} "
        f"cells_ghost={msh.topology.index_map(tdim).num_ghosts} "
        f"facet_tags={None if facet_tags is None else facet_tags.values.size}"
    )

    mark(f"facet index map before create_entities: "
         f"{msh.topology.index_map(tdim - 1)}")
    msh.topology.create_entities(tdim - 1)
    mark("create_entities(fdim) returned")
    msh.topology.create_connectivity(tdim - 1, tdim)
    mark("create_connectivity(fdim, tdim) returned")

    ft = _interface_facet_tags(msh, cell_tags, {201: (101, 1), 202: (102, 2)})
    mark(f"interface tags: {sorted(set(np.unique(ft.values).tolist()))} "
         f"n={ft.values.size}")
    COMM.Barrier()
    mark("mesh stage done")

    # Stage 2 (`PORT-1` step 3b-iv route 3): the gate's own `dS` area assembly,
    # one marker per separable collective, so the hang is named rather than
    # inferred from a stack.
    local_tags = set(np.unique(ft.values).tolist())
    mark(f"stage2 begin, local tags={sorted(local_tags)}")

    mark("allgather of tag sets ...")
    tags_present = set().union(*COMM.allgather(local_tags))
    mark(f"allgather returned: {sorted(tags_present)}")

    one = dolfinx.fem.Constant(msh, dolfinx.default_scalar_type(1.0))
    for tag in (201, 202):
        mark(f"tag {tag}: ufl.Measure ...")
        dS_tag = ufl.Measure("dS", domain=msh, subdomain_data=ft,
                             subdomain_id=(tag,))
        expr = ufl.avg(one) * dS_tag

        mark(f"tag {tag}: fem.form (JIT) ...")
        form = dolfinx.fem.form(expr)
        mark(f"tag {tag}: fem.form returned")

        mark(f"tag {tag}: create_entity_permutations ...")
        msh.topology.create_entity_permutations()
        mark(f"tag {tag}: create_entity_permutations returned")

        mark(f"tag {tag}: assemble_scalar ...")
        local = dolfinx.fem.assemble_scalar(form)
        mark(f"tag {tag}: assemble_scalar returned local={local!r}")

        mark(f"tag {tag}: allreduce ...")
        total = COMM.allreduce(local, op=MPI.SUM)
        mark(f"tag {tag}: allreduce returned total={total!r}")

    COMM.Barrier()
    mark("done")


if __name__ == "__main__":
    main()
