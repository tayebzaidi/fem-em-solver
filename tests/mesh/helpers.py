"""Test helpers for mesh tag integrity checks."""

from __future__ import annotations

from typing import Mapping

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.io.mesh_qa import (
    cell_tag_counts,
    format_expected_tag_counts,
    print_required_tag_failure_summary,
)


def global_cell_tag_set(mesh, cell_tags) -> set[int]:
    """Union of cell tag values across all MPI ranks.

    ``cell_tags.values`` is rank-local. Under domain decomposition a rank can
    legitimately own no cells of a given tag -- a small wire volume easily lands
    entirely on one rank -- so asserting tag presence against the local array
    produces failures that depend on rank count rather than on mesh validity.
    Always compare against this global set instead.
    """
    local = set(int(v) for v in np.unique(cell_tags.values).tolist())
    return set().union(*mesh.comm.allgather(local))


REQUIRED_COIL_PHANTOM_TAGS = {
    1: "coil_1",
    2: "coil_2",
    3: "phantom",
    4: "air",
}


def assert_required_tags_nonempty(cell_tags, required_tags: Mapping[int, str], comm: MPI.Intracomm) -> None:
    """Assert that each required tag exists and has at least one cell."""
    counts = cell_tag_counts(cell_tags, comm=comm)

    missing = []
    for tag, name in required_tags.items():
        if counts.get(tag, 0) <= 0:
            missing.append(f"{name} (tag={tag})")

    if missing:
        print_required_tag_failure_summary(counts, required_tags, comm=comm, prefix="[mesh-qa] ")

    expected_vs_actual = format_expected_tag_counts(counts, required_tags)
    assert not missing, (
        f"Required mesh tags missing/empty: {', '.join(missing)} | "
        f"expected-vs-actual: {expected_vs_actual}"
    )


# `OPS-17` step 2 (2026-08-17): the tagged-volume partition identity, the
# anchor that replaced the finiteness-only tag-presence assertions in
# test_mesh_tag_integrity.py and test_birdcage_port_tags.py.  Modelled on
# tests/mesh/test_two_torus_conforming.py, which gates the same identity on
# the two-torus fixture, and on test_wall_boundary_tag_areas.py, which does it
# for areas.
#
# The band is exact-arithmetic, not a tolerance to tune: the tagged volumes are
# assembled over a partition of the *same* cells that make up the total, so the
# only difference is floating-point summation order.  A mesh whose volumes are
# doubly counted (a non-conforming fragment) misses it by percent, not by ulps.
VOLUME_PARTITION_BAND = 1.0e-9


def tag_volume(mesh, cell_tags, tag: int, comm: MPI.Intracomm) -> float:
    """``int_tag 1 dV``, reduced -- ``assemble_scalar`` is rank-local."""
    dx_tag = ufl.Measure(
        "dx", domain=mesh, subdomain_data=cell_tags, subdomain_id=(int(tag),)
    )
    one = fem.Constant(mesh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * dx_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def total_volume(mesh, comm: MPI.Intracomm) -> float:
    """``int_Omega 1 dV`` over the whole mesh, reduced."""
    one = fem.Constant(mesh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * ufl.dx))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def assert_tag_volumes_partition_domain(
    mesh,
    cell_tags,
    tags,
    comm: MPI.Intracomm,
    band: float = VOLUME_PARTITION_BAND,
    label: str = "",
) -> dict[int, float]:
    """Assert the tagged volumes sum to the mesh volume; return them per tag.

    Quantitative replacement for "every required tag is non-empty": a tag that
    is empty contributes exactly zero and the sum misses, and so does a tag
    whose cells are shared with another region.  Returns the per-tag volumes so
    callers can pin geometry-specific numbers on top.
    """
    volumes = {int(t): tag_volume(mesh, cell_tags, t, comm) for t in tags}
    v_total = total_volume(mesh, comm)
    v_tagged = sum(volumes.values())
    ratio = v_tagged / v_total

    if comm.rank == 0:
        prefix = f"[{label}] " if label else ""
        print(
            f"\n{prefix}tagged-volume partition: total {v_total:.9e} m^3, "
            f"tagged {v_tagged:.9e} m^3, ratio {ratio:.12f}",
            flush=True,
        )
        for tag, v in sorted(volumes.items()):
            print(f"{prefix}  tag {tag}: {v:.9e} m^3", flush=True)

    assert abs(ratio - 1.0) < band, (
        f"tagged volumes {v_tagged:.9e} m^3 do not partition the mesh volume "
        f"{v_total:.9e} m^3 (ratio {ratio:.12f}, band {band:.0e}); per-tag "
        f"{ {t: f'{v:.6e}' for t, v in sorted(volumes.items())} }"
    )
    for tag, v in volumes.items():
        assert v > 0.0, f"tag {tag} contributes zero volume -- it is empty"
    return volumes


def compute_tag_cell_centroid(mesh, cell_tags, tag: int, comm: MPI.Intracomm) -> np.ndarray:
    """Compute global centroid of cell centroids for a given tag."""
    tagged_cells = cell_tags.indices[cell_tags.values == tag]

    local_sum = np.zeros(3, dtype=np.float64)
    local_count = np.array([0], dtype=np.int64)

    if tagged_cells.size:
        dofmap = mesh.geometry.dofmap
        coords = mesh.geometry.x
        centroids = np.array([coords[dofmap[cell]].mean(axis=0) for cell in tagged_cells])
        local_sum = centroids.sum(axis=0)
        local_count[0] = centroids.shape[0]

    global_sum = np.zeros(3, dtype=np.float64)
    global_count = np.array([0], dtype=np.int64)

    comm.Allreduce(local_sum, global_sum, op=MPI.SUM)
    comm.Allreduce(local_count, global_count, op=MPI.SUM)

    if global_count[0] == 0:
        raise AssertionError(f"Tag {tag} has no cells; centroid is undefined")

    return global_sum / float(global_count[0])


def assert_tags_distinct_by_centroid(
    mesh,
    cell_tags,
    tag_a: int,
    tag_b: int,
    comm: MPI.Intracomm,
    min_distance: float = 1.0e-4,
) -> None:
    """Assert that two tagged regions are spatially distinct."""
    centroid_a = compute_tag_cell_centroid(mesh, cell_tags, tag_a, comm=comm)
    centroid_b = compute_tag_cell_centroid(mesh, cell_tags, tag_b, comm=comm)

    distance = np.linalg.norm(centroid_a - centroid_b)
    assert distance > min_distance, (
        f"Tagged regions should be distinct but centroids are too close: "
        f"tag {tag_a} vs {tag_b}, distance={distance:.3e}"
    )
