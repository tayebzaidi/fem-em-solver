"""`OPS-39` — the step-0 probe's `_census` is rank-safe.

The probe `tests/mesh/probe_two_torus_conductor_hole.py` was written for and
read at ``-n 1`` (`TH-15` step 0, 2026-09-05), where owned entities and local
entities coincide.  Under ``GhostMode.shared_facet`` at any width above 1 a
rank's ``MeshTags`` also carries the ghost layer, so summing ``tags.values``
across ranks counts every shared entity once per rank that holds it: the solid
two-torus census overshot the owned cell count by 2972 at ``-n 2``
(`20260906T050521Z_TH-15.log:1464`, known-issues 2026-09-06).

This module gates the fix on an **exact count identity** on a mesh whose
answer is known in closed form:

  * anchor — with the owned mask, ``Σ_tag census[tag] == index_map(tdim).size_global``
    exactly, at every rank width.  Every owned cell carries exactly one tag and
    is counted exactly once, so equality is the only admissible reading.

  * negative control — the *naive* census (the old code path, kept below as a
    private helper for this module only) exceeds ``size_global`` by exactly
    ``Σ_ranks index_map(tdim).num_ghosts``: every ghost cell is a second copy
    of an owned cell on another rank.  The overshoot is **computed from the
    index map, never predicted**, so the identity holds at ``-n 1`` (where the
    ghost count is 0) and at ``-n 2`` without a hard-coded digit.

Smoke tier, real build, ``-n 1`` and ``-n 2``.
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

import dolfinx

from tests.mesh.probe_two_torus_conductor_hole import _census, _owned_census

# Small enough for the smoke tier at either width; large enough that a two-rank
# partition of it has a non-trivial ghost layer.
N_PER_SIDE = 8


def _naive_census(values, comm):
    """The pre-`OPS-39` code path, verbatim, kept only as this test's control.

    `tests/mesh/probe_two_torus_conductor_hole.py::_census` as it stood at
    commit b30ca2b (`:431–440`): ``np.unique`` over the whole rank-local
    ``tags.values`` — ghosts included — then an ``allreduce``.
    """
    local_tags, local_counts = np.unique(values, return_counts=True)
    all_tags = sorted({int(t) for t in comm.allreduce(list(local_tags),
                                                      op=MPI.SUM)})
    out = {}
    for tag in all_tags:
        local = (int(local_counts[local_tags == tag].sum())
                 if tag in local_tags else 0)
        out[tag] = comm.allreduce(local, op=MPI.SUM)
    return out


def _tagged_box(comm):
    """A ``create_box`` mesh with ``shared_facet`` ghosting and a cell tag on
    **every** local cell (owned and ghost), the way `_model_to_mesh` hands the
    probe its ``cell_tags``."""
    msh = dolfinx.mesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([1.0, 1.0, 1.0])],
        [N_PER_SIDE, N_PER_SIDE, N_PER_SIDE],
        cell_type=dolfinx.mesh.CellType.tetrahedron,
        ghost_mode=dolfinx.mesh.GhostMode.shared_facet,
    )
    tdim = msh.topology.dim
    imap = msh.topology.index_map(tdim)
    n_local = imap.size_local + imap.num_ghosts
    indices = np.arange(n_local, dtype=np.int32)
    # Three tags, keyed on geometry so the assignment is partition-independent:
    # a ghost cell carries the same tag on every rank that holds it.
    midpoints = dolfinx.mesh.compute_midpoints(msh, tdim, indices)
    values = np.full(n_local, 3, dtype=np.int32)
    values[midpoints[:, 0] < 0.25] = 1
    values[midpoints[:, 0] > 0.75] = 2
    return msh, dolfinx.mesh.meshtags(msh, tdim, indices, values)


def test_the_owned_census_sums_to_the_global_cell_count():
    """Anchor: ``Σ_tag census[tag] == size_global`` exactly.

    Negative control in the same window: the naive sum overshoots by exactly
    the total ghost count.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags = _tagged_box(comm)
    tdim = msh.topology.dim
    imap = msh.topology.index_map(tdim)

    size_global = imap.size_global
    total_ghosts = comm.allreduce(imap.num_ghosts, op=MPI.SUM)
    total_local = comm.allreduce(imap.size_local + imap.num_ghosts, op=MPI.SUM)

    owned = _owned_census(msh, cell_tags, tdim, comm)
    naive = _naive_census(np.asarray(cell_tags.values), comm)

    owned_sum = sum(owned.values())
    naive_sum = sum(naive.values())

    if comm.rank == 0:
        print(f"\n[OPS-39] ranks={comm.size} size_global={size_global} "
              f"Σ_ranks(size_local+num_ghosts)={total_local} "
              f"Σ_ranks num_ghosts={total_ghosts}")
        print(f"[OPS-39] owned census {dict(sorted(owned.items()))} "
              f"sum={owned_sum}")
        print(f"[OPS-39] naive census {dict(sorted(naive.items()))} "
              f"sum={naive_sum} overshoot={naive_sum - size_global}")

    # Anchor: an exact conservation identity, no tolerance.
    assert owned_sum == size_global, (
        f"masked census sums to {owned_sum}, global cell count "
        f"{size_global} (ranks={comm.size})"
    )

    # Negative control: the overshoot is the ghost layer, measured not assumed.
    assert naive_sum - size_global == total_ghosts, (
        f"naive census overshoot {naive_sum - size_global} != Σ num_ghosts "
        f"{total_ghosts} (ranks={comm.size})"
    )
    if comm.size == 1:
        assert total_ghosts == 0
        assert naive_sum == owned_sum
    else:
        # The control must actually control something: at width > 1 this
        # fixture's ghost layer is non-empty, so the two censuses differ.
        assert total_ghosts > 0
        assert naive_sum > owned_sum


def test_the_masked_census_is_width_invariant_per_tag():
    """Each tag's owned count is the number of cells whose midpoint is in its
    slab — a closed form independent of the partition."""
    comm = MPI.COMM_WORLD
    msh, cell_tags = _tagged_box(comm)
    tdim = msh.topology.dim
    imap = msh.topology.index_map(tdim)

    owned = _owned_census(msh, cell_tags, tdim, comm)

    # 6 tets per hexahedral cell of an N^3 grid; the x < 0.25 and x > 0.75
    # slabs are each 2 of the 8 columns, exactly, for N_PER_SIDE = 8.
    per_column = 6 * N_PER_SIDE * N_PER_SIDE
    expected = {1: 2 * per_column, 2: 2 * per_column, 3: 4 * per_column}
    if comm.rank == 0:
        print(f"[OPS-39] per-tag owned census {dict(sorted(owned.items()))} "
              f"expected {expected} (ranks={comm.size})")
    assert dict(sorted(owned.items())) == expected
    assert sum(expected.values()) == imap.size_global


def test_the_census_positional_signature_is_unchanged():
    """The gate module calls ``_census(values, comm)`` on an already-masked
    array (`tests/mesh/test_two_torus_conductor_hole.py:134`); that call must
    keep working and keep returning ``{tag: count}``."""
    comm = MPI.COMM_WORLD
    msh, cell_tags = _tagged_box(comm)
    tdim = msh.topology.dim
    n_owned = msh.topology.index_map(tdim).size_local
    mask = np.asarray(cell_tags.indices) < n_owned

    by_hand = _census(np.asarray(cell_tags.values)[mask], comm)
    by_kwarg = _owned_census(msh, cell_tags, tdim, comm)

    assert isinstance(by_hand, dict)
    assert by_hand == by_kwarg
    assert sum(by_hand.values()) == msh.topology.index_map(tdim).size_global


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
