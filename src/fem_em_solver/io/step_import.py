"""`GEO-34` step 1a — STEP import through Gmsh/OpenCASCADE with a group map.

``import_step(path, config, comm)`` reads a STEP file with
``gmsh.model.occ.importShapes``, restores shared faces with
``occ.removeAllDuplicates()`` (a fragment of everything, so two solids that
touch share one face again and the mesh is conforming), then claims **every**
imported volume for exactly one configured group by geometric selectors, tags
it with the group's physical tag, sizes it, meshes it and distributes it
through the project's ``_model_to_mesh``.  It returns the same
``(mesh, cell_tags, facet_tags, diagnostics)`` tuple the primitive generators
in ``io/mesh.py`` return.

Config (a dict, or a path to a JSON file)::

    {
      "occ_target_unit": null,          # optional Geometry.OCCTargetUnit
      "resolution": 0.015,              # global size [m] on every CAD point
      "outer_boundary_tag": 1,          # optional dim-2 group on the bbox walls
      "volume_groups": [
        {"name": "conductor", "tag": 1,
         "selectors": [{"centroid_in_box": [x0, y0, z0, x1, y1, z1]}, ...],
         "grading": {"size": 0.0016, "distance": 0.012}},   # optional
        ...
      ]
    }

A *selector* is a dict of predicates that must all hold; a group matches a
volume when any of its selectors does.  Predicates: ``centroid_in_box``
(OCC centre of mass inside the box), ``bbox_within`` (the volume's bounding
box inside the box), ``bbox_contains`` (the volume's bounding box contains
the box).  A volume matched by no group, a volume matched by two, and a group
that matches no volume are each a ``ValueError`` naming the offender — a
silent untagged port is the failure a config invites.

Grading mirrors ``birdcage_port_domain``'s conductor grading: a Distance field
over the group's boundary surfaces into a Threshold that is ``size`` at the
surface and the global ``resolution`` past ``distance``; the MeshSizeFrom*
switches are turned off exactly as the generator does, then
``generate(3)`` + ``optimize("Netgen")``.

gmsh runs on ``rank`` only (one session per call, finalised on the way out,
also on failure); a failure on the building rank is re-raised on every rank
with the same type and message before the collective ``_model_to_mesh``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import dolfinx
import gmsh
import numpy as np
from mpi4py import MPI

from fem_em_solver.io.mesh import _model_to_mesh

_PREDICATES = ("centroid_in_box", "bbox_within", "bbox_contains")


def load_step_config(config) -> Dict[str, object]:
    """A config dict, from a dict or a JSON file path."""
    if isinstance(config, (str, Path)):
        with open(config, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return dict(config)


def _in_box(point, box) -> bool:
    x0, y0, z0, x1, y1, z1 = box
    x, y, z = point
    return x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1


def _selector_matches(selector, centroid, bbox) -> bool:
    unknown = set(selector) - set(_PREDICATES)
    if unknown or not selector:
        raise ValueError(
            f"import_step: selector {selector!r} has unknown or no predicates "
            f"(known: {', '.join(_PREDICATES)})"
        )
    lo, hi = bbox[:3], bbox[3:]
    if "centroid_in_box" in selector and not _in_box(
        centroid, selector["centroid_in_box"]
    ):
        return False
    if "bbox_within" in selector:
        box = selector["bbox_within"]
        if not (_in_box(lo, box) and _in_box(hi, box)):
            return False
    if "bbox_contains" in selector:
        box = selector["bbox_contains"]
        if not (_in_box(box[:3], bbox) and _in_box(box[3:], bbox)):
            return False
    return True


def claim_volumes(volumes, groups) -> Dict[str, List[int]]:
    """Map every volume to exactly one group, or raise ``ValueError``.

    ``volumes`` is ``{tag: (centroid, bbox)}``; ``groups`` the config's
    ``volume_groups`` list.  Pure function: no gmsh call, so the claim rules
    are checkable without a CAD model.
    """
    claimed: Dict[str, List[int]] = {g["name"]: [] for g in groups}
    unclaimed, doubly = [], []
    for tag, (centroid, bbox) in sorted(volumes.items()):
        owners = [
            g["name"]
            for g in groups
            if any(_selector_matches(s, centroid, bbox) for s in g["selectors"])
        ]
        if not owners:
            unclaimed.append((tag, centroid))
        elif len(owners) > 1:
            doubly.append((tag, centroid, owners))
        else:
            claimed[owners[0]].append(tag)
    if unclaimed:
        raise ValueError(
            "import_step: volume(s) claimed by no config group: "
            + "; ".join(
                f"volume {tag} centroid=({c[0]:.6e}, {c[1]:.6e}, {c[2]:.6e})"
                for tag, c in unclaimed
            )
        )
    if doubly:
        raise ValueError(
            "import_step: volume(s) claimed by more than one config group: "
            + "; ".join(
                f"volume {tag} centroid=({c[0]:.6e}, {c[1]:.6e}, {c[2]:.6e}) "
                f"groups {owners}"
                for tag, c, owners in doubly
            )
        )
    empty = [name for name, tags in claimed.items() if not tags]
    if empty:
        raise ValueError(
            "import_step: config group(s) matched no volume: " + ", ".join(empty)
        )
    return claimed


def _build(path, config) -> Dict[str, object]:
    """Import, claim, tag, size and mesh on the calling rank."""
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.model.add("step_import")
    unit = config.get("occ_target_unit")
    if unit:
        gmsh.option.setString("Geometry.OCCTargetUnit", str(unit))

    started = time.perf_counter()
    gmsh.model.occ.importShapes(str(path))
    gmsh.model.occ.removeAllDuplicates()
    gmsh.model.occ.synchronize()
    import_wall_time = time.perf_counter() - started

    volumes = {}
    masses = {}
    for _, tag in gmsh.model.getEntities(dim=3):
        centroid = tuple(float(v) for v in gmsh.model.occ.getCenterOfMass(3, tag))
        bbox = tuple(float(v) for v in gmsh.model.getBoundingBox(3, tag))
        volumes[tag] = (centroid, bbox)
        masses[tag] = float(gmsh.model.occ.getMass(3, tag))
    model_bbox = tuple(float(v) for v in gmsh.model.getBoundingBox(-1, -1))
    print(
        f"[step-import] {path}: {len(volumes)} volumes in {import_wall_time:.2f} s, "
        f"model bbox={tuple(f'{v:.6e}' for v in model_bbox)}",
        flush=True,
    )
    for tag, (c, b) in sorted(volumes.items()):
        print(
            f"[step-import]   volume {tag}: mass={masses[tag]:.9e} "
            f"centroid=({c[0]:.6e}, {c[1]:.6e}, {c[2]:.6e}) "
            f"bbox=({b[0]:.4e}, {b[1]:.4e}, {b[2]:.4e}, {b[3]:.4e}, {b[4]:.4e}, {b[5]:.4e})",
            flush=True,
        )

    groups = config["volume_groups"]
    claimed = claim_volumes(volumes, groups)
    for group in groups:
        gmsh.model.addPhysicalGroup(3, claimed[group["name"]], tag=int(group["tag"]))
        gmsh.model.setPhysicalName(3, int(group["tag"]), group["name"])

    outer_tag = config.get("outer_boundary_tag")
    if outer_tag is not None:
        x0, y0, z0, x1, y1, z1 = model_bbox
        tol = 1.0e-9 * max(x1 - x0, y1 - y0, z1 - z0)
        walls = []
        for _, surf in gmsh.model.getEntities(dim=2):
            b = gmsh.model.getBoundingBox(2, surf)
            if (
                abs(b[0] - b[3]) < tol and (abs(b[0] - x0) < tol or abs(b[0] - x1) < tol)
                or abs(b[1] - b[4]) < tol and (abs(b[1] - y0) < tol or abs(b[1] - y1) < tol)
                or abs(b[2] - b[5]) < tol and (abs(b[2] - z0) < tol or abs(b[2] - z1) < tol)
            ):
                walls.append(surf)
        if walls:
            gmsh.model.addPhysicalGroup(2, walls, tag=int(outer_tag))
            gmsh.model.setPhysicalName(2, int(outer_tag), "outer_boundary")

    resolution = float(config["resolution"])
    gmsh.model.mesh.setSize(gmsh.model.getEntities(0), resolution)
    size_fields: List[int] = []
    for group in groups:
        grading = group.get("grading")
        if not grading:
            continue
        surfaces = sorted(
            {
                s
                for d, s in gmsh.model.getBoundary(
                    [(3, v) for v in claimed[group["name"]]],
                    combined=True,
                    oriented=False,
                    recursive=False,
                )
                if d == 2
            }
        )
        distance = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(distance, "SurfacesList", surfaces)
        gmsh.model.mesh.field.setNumber(distance, "Sampling", 20)
        threshold = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(threshold, "InField", distance)
        gmsh.model.mesh.field.setNumber(threshold, "SizeMin", float(grading["size"]))
        gmsh.model.mesh.field.setNumber(threshold, "SizeMax", resolution)
        gmsh.model.mesh.field.setNumber(threshold, "DistMin", 0.0)
        gmsh.model.mesh.field.setNumber(
            threshold, "DistMax", float(grading["distance"])
        )
        size_fields.append(threshold)
    if size_fields:
        if len(size_fields) == 1:
            background = size_fields[0]
        else:
            background = gmsh.model.mesh.field.add("Min")
            gmsh.model.mesh.field.setNumbers(background, "FieldsList", size_fields)
        gmsh.model.mesh.field.setAsBackgroundMesh(background)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

    mesh_start = time.perf_counter()
    gmsh.model.mesh.generate(3)
    gmsh.model.mesh.optimize("Netgen")
    mesh_wall_time = time.perf_counter() - mesh_start

    return {
        "cad_mass_by_group": {
            g["name"]: float(sum(masses[v] for v in claimed[g["name"]]))
            for g in groups
        },
        "volumes_by_group": {g["name"]: len(claimed[g["name"]]) for g in groups},
        "tag_by_group": {g["name"]: int(g["tag"]) for g in groups},
        "model_bbox": model_bbox,
        "import_wall_time_s": float(import_wall_time),
        "mesh_wall_time_s": float(mesh_wall_time),
        "n_volumes": len(volumes),
    }


def import_step(
    path,
    config,
    comm: MPI.Intracomm = MPI.COMM_WORLD,
    rank: int = 0,
) -> Tuple[object, object, object, Dict[str, object]]:
    """``(mesh, cell_tags, facet_tags, diagnostics)`` from a STEP file + config.

    Collective over ``comm``.  ``path`` need only be readable on ``rank``.
    """
    config = load_step_config(config)
    build_error: Optional[BaseException] = None
    build_diagnostics = None
    if comm.rank == rank:
        try:
            build_diagnostics = _build(path, config)
        except BaseException as exc:  # noqa: BLE001 — re-raised below, on every rank
            build_error = exc
            if gmsh.isInitialized():
                gmsh.finalize()

    failure = comm.bcast(
        None
        if build_error is None
        else (isinstance(build_error, ValueError), str(build_error)),
        root=rank,
    )
    if failure is not None:
        if build_error is not None:
            raise build_error
        is_value_error, message = failure
        raise (ValueError if is_value_error else RuntimeError)(
            f"{message} (raised on rank {rank}; this is rank {comm.rank})"
        )

    partitioner = dolfinx.mesh.create_cell_partitioner(
        dolfinx.mesh.GhostMode.shared_facet, 2
    )
    try:
        mesh, cell_tags, facet_tags = _model_to_mesh(
            gmsh.model, comm, rank, gdim=3, partitioner=partitioner
        )
    finally:
        if comm.rank == rank and gmsh.isInitialized():
            gmsh.finalize()
    diagnostics = dict(comm.bcast(build_diagnostics, root=rank))
    return mesh, cell_tags, facet_tags, diagnostics
