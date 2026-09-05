"""Probe (not a test): the two-torus conductor as a *hole* instead of a solid.

`TH-15` step 0, commissioned as PROJECT_PLAN §9 item 4.  Two variants, one OS
process each (`GEO-23` step 1's gmsh contamination rule), `-n 1` (gmsh is
serial and a rung that may FAIL must not deadlock a second rank):

    A -- the landed solid build, ``MeshGenerator.two_torus_domain(port_gap=True,
         emit_port_sheet=True, ...)`` with every argument imported from
         ``tests.validation.test_port_lumped_two_torus._build``.  The control:
         it must reproduce the 0.11 record (184 176 cells / 31 550 vertices).

    B -- a **probe-local** copy of that generator's OCC sequence
         (``io/mesh.py:1185--1835``) in which the two conductors are *cut* from
         the air box (``removeTool=False``) and their volumes then dropped from
         the model, so the conductor is a cavity whose surface survives as a
         dim-2 physical group.  ``MeshGenerator`` is NOT edited; nothing in
         ``src/`` changes.

Measured per variant: cells per tag, vertices, port-sheet facet count and area
against ``nominal_area = 4 * gap_half_xz * gap_half_y``, the conductor-surface
facet count, and mesh wall time.

**This script asserts nothing.**  It prints; the review reads.  Run:

    mpiexec -n 1 python3 -u tests/mesh/probe_two_torus_conductor_hole.py --variant A
    mpiexec -n 1 python3 -u tests/mesh/probe_two_torus_conductor_hole.py --variant B
"""

from __future__ import annotations

import argparse
import time
from typing import Dict, List

import numpy as np
import ufl
from mpi4py import MPI

import dolfinx

from fem_em_solver.io.mesh import _interface_facet_tags, _model_to_mesh

# Every fixture argument is imported, never restated (`ANS-1`).
from tests.validation.test_port_gap_voltage_impedance import (
    AIR_PADDING,
    GAP_ANGLE,
    GAP_ARC_RESOLUTION,
    GAP_BURIAL,
    GAP_OVERHANG,
    H_FAR,
    H_WIRE,
    MAJOR_RADIUS,
    MINOR_RADIUS,
    SEPARATION,
    _gap_half_extents,
)
from tests.validation.test_port_lumped_two_torus import _build

CONDUCTOR_SURFACE_TAG = 301          # probe-local, variant B only
OUTER_BOUNDARY_TAG = 1


# ---------------------------------------------------------------------------
# Variant B: the hole build, a probe-local copy of the generator's OCC sequence
# ---------------------------------------------------------------------------
def _hole_build(comm, rank: int = 0, conductor_group: bool = True):
    """``two_torus_domain``'s geometry with the conductors cut out as cavities.

    The sequence follows ``io/mesh.py`` step for step, with exactly one
    substitution: instead of ``occ.fragment([box], [tori, gap boxes, sheets])``
    it does

        conductors = cut(tori, gap boxes, removeTool=False)   # arc minus box
        air        = cut(box, conductors, removeTool=False)   # the cavity
        fragment(air, [gap boxes, sheets])                    # gap + mid-plane

    and then drops the retained conductor volumes from the model, keeping their
    surfaces for a dim-2 physical group.  ``removeTool=False`` throughout: with
    ``True`` the cut deletes the tool's surfaces and any group on them.
    """
    import gmsh

    t0 = time.perf_counter()
    if comm.rank == rank:
        gmsh.initialize()
        gmsh.model.add("two_torus_hole")

        z_offset = SEPARATION / 2.0
        burial = float(GAP_BURIAL)
        overhang = float(GAP_OVERHANG)

        # --- partial tori, the generator's construction verbatim -------------
        wire_1 = gmsh.model.occ.addTorus(
            0, 0, -z_offset, MAJOR_RADIUS, MINOR_RADIUS,
            angle=2.0 * np.pi - GAP_ANGLE,
        )
        wire_2 = gmsh.model.occ.addTorus(
            0, 0, z_offset, MAJOR_RADIUS, MINOR_RADIUS,
            angle=2.0 * np.pi - GAP_ANGLE,
        )
        for wire in (wire_1, wire_2):
            gmsh.model.occ.rotate([(3, wire)], 0, 0, 0, 0, 0, 1, 0.5 * GAP_ANGLE)

        gap_half_xz = MINOR_RADIUS + overhang
        gap_half_y = MAJOR_RADIUS * np.sin(0.5 * GAP_ANGLE) + burial
        gap_size = (2.0 * gap_half_xz, 2.0 * gap_half_y, 2.0 * gap_half_xz)
        gap_1 = gmsh.model.occ.addBox(
            MAJOR_RADIUS - gap_half_xz, -gap_half_y, -z_offset - gap_half_xz,
            *gap_size,
        )
        gap_2 = gmsh.model.occ.addBox(
            MAJOR_RADIUS - gap_half_xz, -gap_half_y, z_offset - gap_half_xz,
            *gap_size,
        )
        sheet_1 = gmsh.model.occ.addRectangle(
            MAJOR_RADIUS - gap_half_xz, -gap_half_y, -z_offset,
            2.0 * gap_half_xz, 2.0 * gap_half_y,
        )
        sheet_2 = gmsh.model.occ.addRectangle(
            MAJOR_RADIUS - gap_half_xz, -gap_half_y, z_offset,
            2.0 * gap_half_xz, 2.0 * gap_half_y,
        )

        padding = float(AIR_PADDING)
        radial_extent = MAJOR_RADIUS + MINOR_RADIUS
        box_half_x = radial_extent + padding
        box_half_y = radial_extent + padding
        box_half_z = z_offset + MINOR_RADIUS + padding
        domain = gmsh.model.occ.addBox(
            -box_half_x, -box_half_y, -box_half_z,
            2.0 * box_half_x, 2.0 * box_half_y, 2.0 * box_half_z,
        )

        # --- step 1: the conductor is the arc minus what the gap box swallows.
        # The gap box keeps its own volume (removeTool=False) -- the generator
        # gives the gap precedence over metal for exactly the same reason.
        conductors, _ = gmsh.model.occ.cut(
            [(3, wire_1), (3, wire_2)], [(3, gap_1), (3, gap_2)],
            removeObject=True, removeTool=False,
        )
        cond_of = {}                       # conductor volume -> 1 or 2
        gmsh.model.occ.synchronize()
        for dim, tag in conductors:
            _, _, zc = gmsh.model.occ.getCenterOfMass(dim, tag)
            cond_of[tag] = 1 if zc < 0.0 else 2
        print(f"[hole] conductor solids after arc cut: {conductors} "
              f"masses="
              + " ".join(f"{t}:{gmsh.model.occ.getMass(3, t):.6e}"
                         for _, t in conductors),
              flush=True)

        # --- step 2: subtract them from the air box.  removeTool=False keeps
        # the conductor solids alive so their surfaces are addressable.
        air_pieces, _ = gmsh.model.occ.cut(
            [(3, domain)], conductors, removeObject=True, removeTool=False,
        )

        # --- step 3: the gap boxes and the port sheets fragment into the cut
        # result, AFTER the cut, in the generator's order.
        tool_dimtags = [(3, gap_1), (3, gap_2), (2, sheet_1), (2, sheet_2)]
        _, fragment_map = gmsh.model.occ.fragment(air_pieces, tool_dimtags)
        gmsh.model.occ.synchronize()

        # --- groups, re-derived from the fragment out-map exactly as the
        # generator does (fragment renumbers; pre-call tags mean nothing).
        input_dimtags = list(air_pieces) + tool_dimtags
        ancestors: Dict[int, set] = {}
        for input_dimtag, pieces in zip(input_dimtags, fragment_map):
            for dim, piece in pieces:
                if dim == 3:
                    ancestors.setdefault(piece, set()).add(input_dimtag)

        gap_of = {(3, gap_1): (101, 111, -z_offset),
                  (3, gap_2): (102, 112, z_offset)}
        group_of_piece: Dict[int, int] = {}
        for piece, sources in ancestors.items():
            hit_gap = sources & gap_of.keys()
            if hit_gap:
                lower, upper, z_c = gap_of[min(hit_gap)]
                _, _, zc_piece = gmsh.model.occ.getCenterOfMass(3, piece)
                group_of_piece[piece] = upper if zc_piece > z_c else lower
            else:
                group_of_piece[piece] = 3

        pieces_by_group: Dict[int, List[int]] = {}
        for piece, group in sorted(group_of_piece.items()):
            pieces_by_group.setdefault(group, []).append(piece)

        group_names = {3: "domain", 101: "gap_1", 102: "gap_2",
                       111: "gap_1_upper", 112: "gap_2_upper"}
        volumes = [t for _, t in gmsh.model.getEntities(dim=3)]
        masses = {t: gmsh.model.occ.getMass(3, t) for t in volumes}
        missing = [group_names[g] for g in (3, 101, 102, 111, 112)
                   if g not in pieces_by_group]
        print(
            f"[hole] fragment volumes={len(volumes)} "
            + " ".join(
                f"{group_names[g]}={sum(masses[p] for p in ps):.6e}({len(ps)}p)"
                for g, ps in sorted(pieces_by_group.items())
            )
            + f" gap_box_analytic={gap_size[0] * gap_size[1] * gap_size[2]:.6e}"
            + (f" MISSING={missing}" if missing else ""),
            flush=True,
        )

        for group, pieces in sorted(pieces_by_group.items()):
            gmsh.model.addPhysicalGroup(3, pieces, tag=group)
            gmsh.model.setPhysicalName(3, group, group_names[group])

        # --- the cavity surface.  It must be identified from the *meshed*
        # volumes (air + gap pieces) alone: the retained conductor solids are
        # still in the model, and testing a face against a set that includes
        # them is self-satisfying.  A cavity wall is a face that bounds exactly
        # one meshed volume and does not lie on the outer box wall -- the
        # air/gap interfaces and the port-sheet mid-planes bound two, the outer
        # walls bound one but are flat against a wall.
        def _bnd(dimtags):
            return {s for dt in dimtags
                    for _, s in gmsh.model.getBoundary([dt], oriented=False,
                                                       recursive=False)}

        mesh_volumes = [v for v in volumes if v not in cond_of]
        face_use: Dict[int, int] = {}
        for v in mesh_volumes:
            for s in _bnd([(3, v)]):
                face_use[s] = face_use.get(s, 0) + 1

        def _on_wall(s):
            bb = gmsh.model.getBoundingBox(2, s)
            return any(abs(bb[i] - lo) < 1e-6 and abs(bb[i + 3] - lo) < 1e-6
                       for i, lo in ((0, -box_half_x), (0, box_half_x),
                                     (1, -box_half_y), (1, box_half_y),
                                     (2, -box_half_z), (2, box_half_z)))

        cavity_surfaces = sorted(s for s, n in face_use.items()
                                 if n == 1 and not _on_wall(s))

        # How much of the retained tool's own boundary the cut actually shared
        # with the cavity -- the question `removeTool=False` is there to ask.
        cond_surfaces = {tag: _bnd([(3, tag)]) for tag in cond_of}
        print("[hole] conductor solid surfaces: "
              + " ".join(
                  f"vol {t}: {len(cond_surfaces[t])} faces, "
                  f"{len(cond_surfaces[t] & set(cavity_surfaces))} of them "
                  "shared with the cavity"
                  for t in sorted(cond_of))
              + f"; cavity faces from the meshed volumes: "
                f"{len(cavity_surfaces)}",
              flush=True)

        cavity_area = sum(gmsh.model.occ.getMass(2, s) for s in cavity_surfaces)
        print(f"[hole] conductor-surface group {CONDUCTOR_SURFACE_TAG}: "
              f"{len(cavity_surfaces)} surface(s) CAD area={cavity_area:.9e}",
              flush=True)

        # Drop the conductor volumes: the cavity is the hole.  recursive=False
        # so the faces survive for the physical group.
        gmsh.model.occ.remove([(3, t) for t in cond_of], recursive=False)
        gmsh.model.occ.synchronize()
        if any((3, t) in gmsh.model.getEntities(dim=3) for t in cond_of):
            # occ.remove + synchronize did not propagate; drop them model-side.
            gmsh.model.removeEntities([(3, t) for t in cond_of],
                                      recursive=False)
        remaining = [t for _, t in gmsh.model.getEntities(dim=3)]
        print(f"[hole] volumes after dropping the conductors: {len(remaining)} "
              f"(was {len(volumes)})", flush=True)

        still_there = [s for s in cavity_surfaces
                       if (2, s) in gmsh.model.getEntities(dim=2)]
        print(f"[hole] cavity surfaces surviving the drop: {len(still_there)}"
              f"/{len(cavity_surfaces)}", flush=True)
        if still_there and conductor_group:
            gmsh.model.addPhysicalGroup(2, still_there,
                                        tag=CONDUCTOR_SURFACE_TAG)
            gmsh.model.setPhysicalName(2, CONDUCTOR_SURFACE_TAG,
                                       "conductor_surface")
        elif still_there:
            print("[hole] conductor-surface physical group SUPPRESSED "
                  "(--conductor-group off): isolating the model_to_mesh abort",
                  flush=True)

        # --- the outer boundary, the generator's own test verbatim -----------
        tol = 1e-6
        boundary_surfaces = []
        for dim, surf in gmsh.model.getEntities(dim=2):
            x0, y0, z0, x1, y1, z1 = gmsh.model.getBoundingBox(dim, surf)
            if (abs(x0 + box_half_x) < tol and abs(x1 + box_half_x) < tol
                    or abs(x0 - box_half_x) < tol and abs(x1 - box_half_x) < tol
                    or abs(y0 + box_half_y) < tol and abs(y1 + box_half_y) < tol
                    or abs(y0 - box_half_y) < tol and abs(y1 - box_half_y) < tol
                    or abs(z0 + box_half_z) < tol and abs(z1 + box_half_z) < tol
                    or abs(z0 - box_half_z) < tol and abs(z1 - box_half_z) < tol):
                boundary_surfaces.append(surf)
        if boundary_surfaces:
            gmsh.model.addPhysicalGroup(2, boundary_surfaces,
                                        tag=OUTER_BOUNDARY_TAG)
            gmsh.model.setPhysicalName(2, OUTER_BOUNDARY_TAG, "outer_boundary")

        # --- sizing: the generator's graded field, pointed at the same
        # surfaces (the conductor walls plus the gap-box faces), so the air
        # cell count is comparable to variant A's.
        h_wire = float(H_WIRE)
        h_far = float(H_FAR)
        refine_volumes = [p for g in (101, 102, 111, 112)
                          for p in pieces_by_group.get(g, [])]
        wire_surfaces = sorted(
            set(still_there)
            | {s for v in refine_volumes
               for _, s in gmsh.model.getBoundary([(3, v)], oriented=False,
                                                  recursive=False)}
        )
        dist = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(dist, "SurfacesList", wire_surfaces)
        gmsh.model.mesh.field.setNumber(dist, "Sampling", 200)
        thr = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(thr, "InField", dist)
        gmsh.model.mesh.field.setNumber(thr, "SizeMin", h_wire)
        gmsh.model.mesh.field.setNumber(thr, "SizeMax", h_far)
        gmsh.model.mesh.field.setNumber(thr, "DistMin", MINOR_RADIUS)
        gmsh.model.mesh.field.setNumber(thr, "DistMax", MAJOR_RADIUS + padding)

        h_gap = float(GAP_ARC_RESOLUTION)
        tube = 4.0 * h_gap
        dist_max = tube + (h_far - h_gap) / 0.3
        arc_half_y = float(MAJOR_RADIUS * np.sin(0.5 * GAP_ANGLE))
        r_major = float(MAJOR_RADIUS)
        local_fields = []
        for z_c in (-float(z_offset), float(z_offset)):
            band = (f"(0.5*((sqrt(y^2)-{arc_half_y!r})"
                    f"+sqrt((sqrt(y^2)-{arc_half_y!r})^2)))")
            expr = (f"sqrt((sqrt(x^2+y^2)-{r_major!r})^2"
                    f"+(z-({z_c!r}))^2"
                    f"+{band}^2"
                    f"+(0.5*(sqrt(x^2)-x))^2)")
            arc_dist = gmsh.model.mesh.field.add("MathEval")
            gmsh.model.mesh.field.setString(arc_dist, "F", expr)
            arc_thr = gmsh.model.mesh.field.add("Threshold")
            gmsh.model.mesh.field.setNumber(arc_thr, "InField", arc_dist)
            gmsh.model.mesh.field.setNumber(arc_thr, "SizeMin", h_gap)
            gmsh.model.mesh.field.setNumber(arc_thr, "SizeMax", h_far)
            gmsh.model.mesh.field.setNumber(arc_thr, "DistMin", tube)
            gmsh.model.mesh.field.setNumber(arc_thr, "DistMax", dist_max)
            local_fields.append(arc_thr)

        background = gmsh.model.mesh.field.add("Min")
        gmsh.model.mesh.field.setNumbers(background, "FieldsList",
                                         [thr] + local_fields)
        gmsh.model.mesh.field.setAsBackgroundMesh(background)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("Netgen")

        # --- gmsh-side census, before `model_to_mesh` gets a chance to abort.
        node_tags_all, _, _ = gmsh.model.mesh.getNodes()
        tet_nodes = set()
        for _, vol in gmsh.model.getEntities(dim=3):
            etypes, _, enodes = gmsh.model.mesh.getElements(3, vol)
            for et, en in zip(etypes, enodes):
                tet_nodes.update(int(n) for n in en)
        tri_count = 0
        tri_keys = set()
        dup = 0
        orphan_nodes = set()
        for s in still_there:
            etypes, etags, enodes = gmsh.model.mesh.getElements(2, s)
            for et, tg, en in zip(etypes, etags, enodes):
                arr = np.asarray(en, dtype=np.int64).reshape(len(tg), -1)
                tri_count += arr.shape[0]
                for row in arr:
                    key = tuple(sorted(int(v) for v in row))
                    if key in tri_keys:
                        dup += 1
                    tri_keys.add(key)
                    orphan_nodes.update(v for v in key if v not in tet_nodes)
        print(f"[hole] gmsh census: nodes={len(node_tags_all)} "
              f"tet-attached nodes={len(tet_nodes)} "
              f"conductor-surface triangles={tri_count} duplicates={dup} "
              f"nodes not attached to any tet={len(orphan_nodes)}", flush=True)
        print("[hole] physical groups: "
              + " ".join(f"{d}/{t}" for d, t in gmsh.model.getPhysicalGroups()),
              flush=True)

    partitioner = dolfinx.mesh.create_cell_partitioner(
        dolfinx.mesh.GhostMode.shared_facet, 2
    )
    mesh, cell_tags, facet_tags = _model_to_mesh(
        gmsh.model, comm, rank, gdim=3, partitioner=partitioner
    )
    if comm.rank == rank:
        gmsh.finalize()

    # The sheet groups are rebuilt from the distributed cell tags, exactly as
    # the generator does (known-issues 9): the halves against each other.
    facet_tags = _interface_facet_tags(
        mesh, cell_tags, {211: ((101, 111),), 212: ((102, 112),)}, facet_tags
    )
    return mesh, cell_tags, facet_tags, time.perf_counter() - t0


# ---------------------------------------------------------------------------
# Measurement, identical for both variants
# ---------------------------------------------------------------------------
def _facet_area(msh, facet_tags, tag, comm) -> float:
    """``dS`` area of one interior facet group; 0.0 when the group is empty."""
    present = comm.allreduce(int(np.count_nonzero(facet_tags.values == tag)),
                             op=MPI.SUM)
    if present == 0:
        return float("nan")
    one = dolfinx.fem.Constant(msh, dolfinx.default_scalar_type(1.0))
    dS = ufl.Measure("dS", domain=msh, subdomain_data=facet_tags,
                     subdomain_id=(tag,))
    local = dolfinx.fem.assemble_scalar(dolfinx.fem.form(ufl.avg(one) * dS))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _exterior_facet_area(msh, facet_tags, tag, comm) -> float:
    present = comm.allreduce(int(np.count_nonzero(facet_tags.values == tag)),
                             op=MPI.SUM)
    if present == 0:
        return float("nan")
    one = dolfinx.fem.Constant(msh, dolfinx.default_scalar_type(1.0))
    ds = ufl.Measure("ds", domain=msh, subdomain_data=facet_tags,
                     subdomain_id=(tag,))
    local = dolfinx.fem.assemble_scalar(dolfinx.fem.form(one * ds))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _census(values, comm):
    local_tags, local_counts = np.unique(values, return_counts=True)
    all_tags = sorted({int(t) for t in comm.allreduce(list(local_tags),
                                                      op=MPI.SUM)})
    out = {}
    for tag in all_tags:
        local = (int(local_counts[local_tags == tag].sum())
                 if tag in local_tags else 0)
        out[tag] = comm.allreduce(local, op=MPI.SUM)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("A", "B"), required=True)
    ap.add_argument("--conductor-group", choices=("on", "off"), default="on",
                    help="variant B only: emit the dim-2 conductor-surface "
                         "physical group (diagnostic switch)")
    args = ap.parse_args()

    comm = MPI.COMM_WORLD
    t0 = time.perf_counter()
    label = ("A: solid build (MeshGenerator.two_torus_domain)"
             if args.variant == "A"
             else "B: hole build (probe-local cut, conductor removed)")
    if comm.rank == 0:
        print(f"=== variant {label} ===", flush=True)

    if args.variant == "A":
        msh, cell_tags, facet_tags, t_mesh = _build(comm)
    else:
        msh, cell_tags, facet_tags, t_mesh = _hole_build(
            comm, conductor_group=(args.conductor_group == "on")
        )

    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    n_cells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    n_verts = comm.allreduce(msh.topology.index_map(0).size_local, op=MPI.SUM)
    cell_census = _census(cell_tags.values, comm)
    facet_census = _census(facet_tags.values, comm)

    # The conductor surface: in B the tagged cavity facets, in A the facets
    # between a conductor cell and anything else (air or gap).
    if args.variant == "A":
        cond_ft = _interface_facet_tags(
            msh, cell_tags,
            {311: ((1, 3), (1, 101), (1, 111)),
             312: ((2, 3), (2, 102), (2, 112))},
        )
        cond_counts = _census(cond_ft.values, comm)
        cond_n = {1: cond_counts.get(311, 0), 2: cond_counts.get(312, 0)}
        cond_area = {1: _facet_area(msh, cond_ft, 311, comm),
                     2: _facet_area(msh, cond_ft, 312, comm)}
    else:
        cond_n = {"all": facet_census.get(CONDUCTOR_SURFACE_TAG, 0)}
        cond_area = {"all": _exterior_facet_area(msh, facet_tags,
                                                 CONDUCTOR_SURFACE_TAG, comm)}

    half_xz, half_y = _gap_half_extents()
    nominal_area = 4.0 * half_xz * half_y
    sheet = {}
    for tag in (211, 212):
        sheet[tag] = (facet_census.get(tag, 0),
                      _facet_area(msh, facet_tags, tag, comm))

    if comm.rank == 0:
        import gmsh
        print(f"  dolfinx {dolfinx.__version__}  gmsh {gmsh.__version__}")
        print(f"  variant                : {args.variant}")
        print(f"  cells (global)         : {n_cells}")
        print(f"  vertices (global)      : {n_verts}")
        print(f"  cell-tag census        : {cell_census}")
        print(f"  facet-tag census       : {facet_census}")
        for tag, (n, area) in sorted(sheet.items()):
            print(f"  port sheet {tag}        : {n} facets  area={area:.9e}  "
                  f"nominal={nominal_area:.9e}  "
                  f"rel_dev={abs(area - nominal_area) / nominal_area:.3e}")
        for key in sorted(cond_n, key=str):
            print(f"  conductor surface {key} : {cond_n[key]} facets  "
                  f"area={cond_area[key]:.9e}")
        print(f"  mesh wall time         : {t_mesh:.2f} s")
        print(f"  probe wall time        : {time.perf_counter() - t0:.2f} s")


if __name__ == "__main__":
    main()
