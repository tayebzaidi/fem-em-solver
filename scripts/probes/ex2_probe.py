"""`EX-2` probe: cost and measured margins/volumes of ``cylindrical_domain``.

Read-only measurement for the `EX-2` example authoring step. Prints, at the
generator defaults:

* the CAD-stage two-sided classification margins (the `GEO-11`/`GEO-13`
  identity, computed exactly as tests/mesh/test_boundary_classification_margins
  does, importing ``_WALL_TOL_FRACTION``);
* the meshed cell count and build time (cost sizing);
* the per-tag meshed volumes against the closed-form cylinder volumes, so the
  example's chordal-deficit band is written from measurement rather than from
  an estimate of gmsh's circle discretisation.

No assertions: this decides the bands the example will assert.
"""

from __future__ import annotations

import time

import gmsh
import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.io.mesh import MeshGenerator, _WALL_TOL_FRACTION

INNER_RADIUS = 0.01
OUTER_RADIUS = 0.1
LENGTH = 0.2
RESOLUTION = 0.02

INNER_TAG = 1
OUTER_TAG = 2


def _classification_rows():
    """CAD stage only: build, classify every dim-2 entity, return residuals."""
    gmsh.initialize()
    try:
        gmsh.model.add("ex2_probe_cylindrical")
        inner = gmsh.model.occ.addCylinder(
            0, 0, -LENGTH / 2, 0, 0, LENGTH, INNER_RADIUS
        )
        outer = gmsh.model.occ.addCylinder(
            0, 0, -LENGTH / 2, 0, 0, LENGTH, OUTER_RADIUS
        )
        gmsh.model.occ.fragment([(3, outer)], [(3, inner)])
        gmsh.model.occ.synchronize()

        tol = _WALL_TOL_FRACTION * (OUTER_RADIUS - INNER_RADIUS)
        rows = []
        for dim, surf in gmsh.model.getEntities(dim=2):
            _, _, _, x_max, y_max, _ = gmsh.model.getBoundingBox(dim, surf)
            r_max = float(np.sqrt(max(x_max**2, y_max**2)))
            residual = abs(r_max - OUTER_RADIUS)
            rows.append((surf, residual, residual < tol))
    finally:
        gmsh.finalize()
    return rows, tol


def _tag_volume(msh, cell_tags, tag, comm):
    dx_tag = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,))
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * dx_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _total_volume(msh, comm):
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * ufl.dx))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _facet_group_area(msh, facet_tags, tag, comm):
    msh.topology.create_entity_permutations()
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    ds_tag = ufl.Measure("ds", domain=msh, subdomain_data=facet_tags, subdomain_id=(tag,))
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * ds_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def main() -> None:
    comm = MPI.COMM_WORLD

    if comm.rank == 0:
        rows, tol = _classification_rows()
        accepted = [r for _, r, ok in rows if ok]
        rejected = [r for _, r, ok in rows if not ok]
        print(f"\n[ex2] tol = {_WALL_TOL_FRACTION} * gap = {tol:.6e}")
        print(f"[ex2] {len(rows)} dim-2 entities, {len(accepted)} accepted")
        for surf, residual, ok in rows:
            print(
                f"[ex2]   surf {surf:3d} residual={residual:.6e} "
                f"ratio={residual / tol:.6e} accepted={ok}"
            )
        print(
            f"[ex2] wall_ratio={max(accepted) / tol:.6e}  "
            f"interior_ratio={min(rejected) / tol:.6e}"
        )

    comm.barrier()
    started = time.perf_counter()
    msh, cell_tags, facet_tags = MeshGenerator.cylindrical_domain(
        inner_radius=INNER_RADIUS,
        outer_radius=OUTER_RADIUS,
        length=LENGTH,
        resolution=RESOLUTION,
        comm=comm,
    )
    mesh_seconds = time.perf_counter() - started

    n_cells = comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, MPI.SUM)

    cell_tag_local = set(np.unique(cell_tags.values).tolist()) if cell_tags is not None else set()
    cell_tag_set = set().union(*comm.allgather(cell_tag_local))
    facet_tag_local = set(np.unique(facet_tags.values).tolist()) if facet_tags is not None else set()
    facet_tag_set = set().union(*comm.allgather(facet_tag_local))

    v_total = _total_volume(msh, comm)
    v_inner = _tag_volume(msh, cell_tags, INNER_TAG, comm)
    v_outer = _tag_volume(msh, cell_tags, OUTER_TAG, comm)

    a_total = np.pi * OUTER_RADIUS**2 * LENGTH
    a_inner = np.pi * INNER_RADIUS**2 * LENGTH
    a_outer = a_total - a_inner

    area_outer_bnd = _facet_group_area(msh, facet_tags, 1, comm)
    area_inner_bnd = _facet_group_area(msh, facet_tags, 2, comm)
    a_outer_bnd = 2.0 * np.pi * OUTER_RADIUS * LENGTH + 2.0 * np.pi * OUTER_RADIUS**2
    a_inner_bnd = 2.0 * np.pi * INNER_RADIUS * LENGTH + 2.0 * np.pi * INNER_RADIUS**2
    total_ext = _facet_group_area(msh, facet_tags, 1, comm)

    if comm.rank == 0:
        print(
            f"\n[ex2] A_outer_bnd={area_outer_bnd:.9e}  analytic(full surf)="
            f"{a_outer_bnd:.9e}  ratio={area_outer_bnd / a_outer_bnd:.9f}"
            f"\n[ex2] A_inner_bnd={area_inner_bnd:.9e}  analytic(full surf)="
            f"{a_inner_bnd:.9e}  ratio={area_inner_bnd / a_inner_bnd:.9f}"
            f"   (lateral is an INTERIOR interface; ds sees the end caps only:"
            f" caps={2.0 * np.pi * INNER_RADIUS**2:.9e})"
            f"\n[ex2] ds(tag=1) recomputed={total_ext:.9e}",
            flush=True,
        )

    if comm.rank == 0:
        print(f"\n[ex2] {n_cells} cells in {mesh_seconds:.1f} s at resolution={RESOLUTION}")
        print(f"[ex2] cell tags {sorted(cell_tag_set)}  facet tags {sorted(facet_tag_set)}")
        print(
            f"\n[ex2] V_total ={v_total:.9e}  analytic={a_total:.9e}  "
            f"ratio={v_total / a_total:.9f}"
            f"\n[ex2] V_inner ={v_inner:.9e}  analytic={a_inner:.9e}  "
            f"ratio={v_inner / a_inner:.9f}"
            f"\n[ex2] V_outer ={v_outer:.9e}  analytic={a_outer:.9e}  "
            f"ratio={v_outer / a_outer:.9f}"
            f"\n[ex2] partition sum/total={(v_inner + v_outer) / v_total:.15f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
