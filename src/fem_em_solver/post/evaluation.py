"""Utilities for robust field evaluation on distributed meshes."""

from __future__ import annotations

import hashlib

import numpy as np
from mpi4py import MPI
from dolfinx import geometry


def evaluate_vector_field_parallel(function, points: np.ndarray, comm: MPI.Intracomm | None = None):
    """Evaluate a vector-valued dolfinx function at points across MPI ranks.

    Parameters
    ----------
    function:
        dolfinx function to evaluate.
    points:
        Array with shape (N, 3).
    comm:
        MPI communicator. Defaults to ``function.function_space.mesh.comm``.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        values:
            Array of shape (N, value_size) with point evaluations.
            Invalid/outside points are filled with zeros.
        valid_mask:
            Boolean mask with shape (N,) marking which points were evaluated.
    """
    mesh = function.function_space.mesh
    comm = comm or mesh.comm

    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"points must have shape (N, 3), got {points.shape}")

    n_points = points.shape[0]

    # OPS-40: this routine is collective — rank 0's output buffer is sized by
    # ``n_points`` and every rank's hits are scattered into it by index, so a
    # caller that hands each rank its own *local* points corrupts the gather
    # (it died with ``IndexError: index 36378 is out of bounds for axis 0 with
    # size 36378`` at -n 2, EX-52, 20260907T033551Z_EX-52.log:400) and passes
    # silently at -n 1. Refuse it on EVERY rank — a rank-0-only raise ahead of
    # the gather below would hang the other ranks.
    #
    # OPS-55: equal counts are not enough — with equal counts and different
    # coordinates each rank locates ITS OWN rows and rank 0 scatters the hits
    # by positional index, so ``values[i]`` silently becomes the field at some
    # other rank's row ``i``. A digest rides the same allgather (no extra round
    # on the valid path). Validate, never broadcast: a broadcast would hide a
    # caller that still indexes the result against its own local ``points``.
    # The contract is bitwise identity.
    points = np.ascontiguousarray(points)
    digest = hashlib.blake2b(points.tobytes(), digest_size=16).digest()
    gathered_keys = comm.allgather((n_points, digest))
    counts = [c for c, _ in gathered_keys]
    if len(set(counts)) > 1:
        per_rank = ", ".join(f"rank {r}: {c}" for r, c in enumerate(counts))
        raise ValueError(
            "evaluate_vector_field_parallel received a different number of "
            f"points on different ranks ({per_rank}). This routine is "
            "collective: the point list must be identical on every rank — "
            "allgather your points first."
        )
    if len({d for _, d in gathered_keys}) > 1:
        # Every rank knows the digests differ, so further collectives are safe
        # here: compare against rank 0's list and raise on EVERY rank.
        ref = comm.bcast(points if comm.rank == 0 else None, root=0)
        diff = np.abs(points - ref)
        rows = np.flatnonzero(np.any(points != ref, axis=1))
        first_row = int(rows[0]) if rows.size else -1
        max_dev = float(np.max(diff)) if diff.size else 0.0
        stats = comm.allgather((first_row, max_dev))
        per_rank = "; ".join(
            f"rank {r}: first differing row {row}, max abs deviation {dev:.3e}"
            for r, (row, dev) in enumerate(stats)
        )
        raise ValueError(
            "evaluate_vector_field_parallel received point lists of equal "
            "length but different coordinates on different ranks (vs rank 0 — "
            f"{per_rank}). This routine is collective: the point list must be "
            "bitwise identical on every rank — broadcast the points from "
            "rank 0 (a gross deviation means rank-local points; ~1e-16 means "
            "rank-dependent floating-point ordering)."
        )

    value_shape = function.function_space.element.value_shape
    value_size = int(np.prod(value_shape)) if len(value_shape) > 0 else 1

    # Follow the function's own scalar dtype: in the complex DolfinX build
    # ``function.eval`` returns complex128, and gathering it into a float64
    # buffer raises a casting error (or, worse, would drop the phase).
    scalar_dtype = np.asarray(function.x.array).dtype

    bb_tree = geometry.bb_tree(mesh, mesh.topology.dim)
    candidate_cells = geometry.compute_collisions_points(bb_tree, points)
    colliding_cells = geometry.compute_colliding_cells(mesh, candidate_cells, points)

    local_point_idx: list[int] = []
    local_cells: list[int] = []
    for i in range(n_points):
        links = colliding_cells.links(i)
        if len(links) > 0:
            local_point_idx.append(i)
            local_cells.append(links[0])

    local_point_idx_arr = np.asarray(local_point_idx, dtype=np.int32)

    if local_point_idx_arr.size > 0:
        local_points = points[local_point_idx_arr]
        local_cells_arr = np.asarray(local_cells, dtype=np.int32)
        local_values = function.eval(local_points, local_cells_arr)
    else:
        local_values = np.zeros((0, value_size), dtype=scalar_dtype)

    gathered_values = comm.gather(local_values, root=0)
    gathered_indices = comm.gather(local_point_idx_arr, root=0)

    if comm.rank == 0:
        values = np.zeros((n_points, value_size), dtype=scalar_dtype)
        valid_mask = np.zeros(n_points, dtype=bool)
        for rank_values, rank_indices in zip(gathered_values, gathered_indices):
            if rank_indices.size > 0:
                values[rank_indices] = rank_values
                valid_mask[rank_indices] = True
    else:
        values = None
        valid_mask = None

    values = comm.bcast(values, root=0)
    valid_mask = comm.bcast(valid_mask, root=0)
    return values, valid_mask
