"""`POST-1` step 2: rank-safety of the interface-guardrail fallback.

``post/phantom_fields.py::_sampling_cells_with_interface_guardrails`` decides
**per rank** whether to fall back from the interior-only sample set to the full
tagged set: if *this rank's* interior set is empty it samples every tagged cell
it owns, interface-adjacent ones included.  A rank holding only a sliver of a
tag therefore samples a different population than its neighbours, and the
reported statistics depend on how the mesh happened to be partitioned — `POST-1`
step 1's defect class one layer up, coming from the classification rather than
from ghosts.  Step 1 measured the scoping fact: on the piecewise-σ fixture at
``-n 2`` the guardrail drops 234 of 385 tagged cells on the minority-tag rank,
so a rank with *zero* interior cells is one partition away.

No field is solved anywhere in this file.  The anchor is a **sentinel DG0
field** — magnitude ``k`` on interior tag-``k`` cells and ``100·k`` on
interface-adjacent tag-``k`` cells, with the adjacency computed here from facet
connectivity over the *full* tag set (ghosts inform classification, step 1's
rule) — so interface contamination is not a small perturbation of the mean but a
factor of ~100 in ``max``.  The reference statistics are exact integers and
exact floats, not a band.

Three regimes are gated:

* **interior regime** (a globally non-empty interior set): production
  ``prefer_interior=True`` statistics must equal the interior-only reference,
  count exactly and floats to ``1e-12``, identically at ``-n 2`` and ``-n 4``;
* **global-fallback regime** (a one-cell-thick tag, interior set empty on
  *every* rank): production must equal the full owned tagged-set reference —
  the guardrail is allowed to give up, but it must give up everywhere at once;
* **mixed regime** (some rank's interior set empty while the global one is
  not): the negative control.  Under the per-rank fallback the production count
  exceeds the interior-only reference by exactly the sliver ranks' tagged-cell
  counts — an integer identity — and ``max`` jumps to the sentinel's ``100·k``.

Run (complex build required by the standing environment gate; nothing here is
complex-valued)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/post/test_interface_guardrail_fallback.py -v -s'

and again at ``-n 4``: a defect that lives in the partition is not measured at
one rank count.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from mpi4py import MPI

import dolfinx.fem as fem
import dolfinx.mesh as dmesh

from fem_em_solver.post.phantom_fields import (
    _interior_tagged_cells,
    _owned_cell_count,
    _sampling_cells_with_interface_guardrails,
    _tagged_cells,
    compute_tagged_vector_magnitude_stats,
)

from tests.validation.test_poynting_balance import (
    TAG_HIGH,
    TAG_LOW,
    _two_material_mesh,
)

# The identities are exact — the two reductions differ only in summation order —
# so the tolerance is round-off, not physics.
IDENTITY_RTOL = 1e-12

TAGS = (TAG_LOW, TAG_HIGH)

# `POST-3` step 4's fixture size, reused for the probe.  Only its mesh and tags
# are needed here, so the solve is skipped entirely.
FIXTURE_N = 12

# Sentinel contrast: interface-adjacent tagged cells carry 100x the interior
# value, so any contamination of an interior-only statistic is visible in ``max``
# and ``mean`` at two orders of magnitude rather than in the last digits.
INTERFACE_SENTINEL_FACTOR = 100.0


# --------------------------------------------------------------------------
# Fixtures: two constructed meshes, no solves
# --------------------------------------------------------------------------


def _tag_mesh(msh, pieces):
    """Tag every owned cell of ``msh`` from ``pieces`` = [(tag, predicate), ...].

    Predicates are ``locate_entities`` markers (all-vertices-satisfy), so the
    pieces must be separated by mesh planes.  Coverage is asserted rather than
    trusted: an untagged cell would silently leave the sample sets incomplete.
    """
    tdim = msh.topology.dim
    indices_parts: list[np.ndarray] = []
    values_parts: list[np.ndarray] = []
    for tag, predicate in pieces:
        cells = dmesh.locate_entities(msh, tdim, predicate)
        indices_parts.append(np.asarray(cells, dtype=np.int32))
        values_parts.append(np.full(cells.size, int(tag), dtype=np.int32))

    indices = np.concatenate(indices_parts).astype(np.int32)
    values = np.concatenate(values_parts).astype(np.int32)

    n_owned = msh.topology.index_map(tdim).size_local
    owned = indices[indices < n_owned]
    assert np.unique(owned).size == owned.size, "a cell was tagged twice"
    assert owned.size == n_owned, (
        f"{n_owned - owned.size} owned cells fall in no piece: the piece "
        "boundaries are not mesh planes"
    )

    order = np.argsort(indices)
    return dmesh.meshtags(msh, tdim, indices[order], values[order])


@pytest.fixture(scope="module")
def piecewise_sigma_tags():
    """`POST-3` step 4's 12³ piecewise-σ mesh and tags — mesh only, no solve."""
    return _two_material_mesh(FIXTURE_N)


@pytest.fixture(scope="module")
def thin_tag_mesh():
    """Global-fallback regime: tag 2 is one cell layer thick, so no cell of it
    is interior on *any* rank.

    **Hexahedra, deliberately.**  A one-layer slab of *tetrahedra* is not one
    cell thick in the facet-adjacency sense: the six-tet decomposition of a hex
    leaves two tets per hex with no facet on either bounding plane, so they are
    interior after all — measured on the first probe
    (``20260804T183351Z_POST-1-step2-probe-n2.log``: 32 interior cells out of
    96).  Every hexahedron of a one-layer slab has a facet on each bounding
    plane, so the interior set is empty by construction rather than by hope.

    16 layers over [0, 1] put mesh planes at multiples of 1/16; the tag-2 slab
    is the single layer [8/16, 9/16].
    """
    comm = MPI.COMM_WORLD
    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([1.0, 0.25, 0.25])],
        [16, 4, 4],
        cell_type=dmesh.CellType.hexahedron,
    )
    eps = 1e-9
    slab_lo, slab_hi = 8.0 / 16.0, 9.0 / 16.0
    tags = _tag_mesh(
        msh,
        [
            (TAG_HIGH, lambda x: (x[0] >= slab_lo - eps) & (x[0] <= slab_hi + eps)),
            (TAG_LOW, lambda x: x[0] <= slab_lo + eps),
            (TAG_LOW, lambda x: x[0] >= slab_hi - eps),
        ],
    )
    return msh, tags


@pytest.fixture(scope="module")
def mixed_regime_mesh():
    """Mixed regime (attempted): tag 2 is a thick blob **plus** a distant
    one-cell-thick sliver.

    The blob has interior cells; the sliver has none, anywhere (hexahedra, for
    the reason :func:`thin_tag_mesh` records).  On a box long in ``x`` the graph
    partitioner slices along ``x``, so a rank owning only the sliver holds
    tagged cells with an empty interior set while other ranks hold the blob —
    exactly the per-rank fallback's failure mode.  Whether a given rank count
    realises that split is a property of the partitioner, so the tests below
    *measure* the regime and say so instead of assuming it.
    """
    comm = MPI.COMM_WORLD
    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([1.0, 0.0625, 0.0625])],
        [32, 2, 2],
        cell_type=dmesh.CellType.hexahedron,
    )
    eps = 1e-9
    blob_hi = 8.0 / 32.0
    sliver_lo, sliver_hi = 24.0 / 32.0, 25.0 / 32.0
    tags = _tag_mesh(
        msh,
        [
            (TAG_HIGH, lambda x: x[0] <= blob_hi + eps),
            (TAG_HIGH, lambda x: (x[0] >= sliver_lo - eps) & (x[0] <= sliver_hi + eps)),
            (TAG_LOW, lambda x: (x[0] >= blob_hi - eps) & (x[0] <= sliver_lo + eps)),
            (TAG_LOW, lambda x: x[0] >= sliver_hi - eps),
        ],
    )
    return msh, tags


# --------------------------------------------------------------------------
# Test-side classification and sentinel field
# --------------------------------------------------------------------------


def _test_interface_adjacent(msh, cell_tags, tag: int) -> set[int]:
    """Owned tag-``tag`` cells with a facet neighbour of a different tag.

    Computed here from the **full** tag set (ghosts included in the lookup) so
    that a cell on a partition boundary is classified the same way on every
    rank — step 1's rule, restated independently of the production helper.
    """
    tdim = msh.topology.dim
    fdim = tdim - 1
    msh.topology.create_connectivity(tdim, fdim)
    msh.topology.create_connectivity(fdim, tdim)
    c_to_f = msh.topology.connectivity(tdim, fdim)
    f_to_c = msh.topology.connectivity(fdim, tdim)

    lookup = {
        int(c): int(v) for c, v in zip(cell_tags.indices, cell_tags.values)
    }
    n_owned = int(msh.topology.index_map(tdim).size_local)

    adjacent: set[int] = set()
    for cell, value in lookup.items():
        if value != int(tag) or cell >= n_owned:
            continue
        for facet in c_to_f.links(cell):
            for nbr in f_to_c.links(int(facet)):
                if int(nbr) == cell:
                    continue
                if lookup.get(int(nbr), None) != int(tag):
                    adjacent.add(cell)
                    break
            if cell in adjacent:
                break
    return adjacent


def _sentinel_field(msh, cell_tags):
    """DG0 vector field: magnitude ``k`` on interior tag-``k`` cells,
    ``100·k`` on interface-adjacent ones, ``0`` on untagged cells.

    Only the first component is set, so ``|F|`` is the assigned value exactly —
    the statistics under test then read as integers.
    """
    V = fem.functionspace(msh, ("DG", 0, (3,)))
    f = fem.Function(V)
    arr = f.x.array
    arr[:] = 0.0
    block = arr.reshape(-1, 3)

    tdim = msh.topology.dim
    n_local = int(msh.topology.index_map(tdim).size_local)
    n_ghost = int(msh.topology.index_map(tdim).num_ghosts)

    # Ghost cells get values too: the production path never samples them after
    # step 1's fix, but a stale ghost value would make any regression here look
    # like a classification error instead of a sampling one.
    adjacency = {tag: _test_interface_adjacent_all(msh, cell_tags, tag) for tag in TAGS}
    lookup = {int(c): int(v) for c, v in zip(cell_tags.indices, cell_tags.values)}

    for cell in range(n_local + n_ghost):
        tag = lookup.get(cell, None)
        if tag is None:
            continue
        value = float(tag)
        if cell in adjacency[tag]:
            value *= INTERFACE_SENTINEL_FACTOR
        dofs = V.dofmap.cell_dofs(cell)
        block[dofs[0], 0] = value

    return f


def _test_interface_adjacent_all(msh, cell_tags, tag: int) -> set[int]:
    """As :func:`_test_interface_adjacent` but without the owned restriction —
    used to give ghost cells consistent sentinel values."""
    tdim = msh.topology.dim
    fdim = tdim - 1
    msh.topology.create_connectivity(tdim, fdim)
    msh.topology.create_connectivity(fdim, tdim)
    c_to_f = msh.topology.connectivity(tdim, fdim)
    f_to_c = msh.topology.connectivity(fdim, tdim)
    lookup = {int(c): int(v) for c, v in zip(cell_tags.indices, cell_tags.values)}

    adjacent: set[int] = set()
    for cell, value in lookup.items():
        if value != int(tag):
            continue
        for facet in c_to_f.links(cell):
            for nbr in f_to_c.links(int(facet)):
                if int(nbr) == cell:
                    continue
                if lookup.get(int(nbr), None) != int(tag):
                    adjacent.add(cell)
                    break
            if cell in adjacent:
                break
    return adjacent


def _stats_over_cells(field, cells, comm) -> dict[str, float]:
    """Allreduced count/min/max/mean of ``|F|`` over ``cells`` — the same
    reduction ``compute_tagged_vector_magnitude_stats`` performs, so the only
    degree of freedom under test is *which cells* go in."""
    from fem_em_solver.post.phantom_fields import _cell_centroids, _evaluate_on_cells

    msh = field.function_space.mesh
    cells = np.asarray(cells, dtype=np.int32)
    points = _cell_centroids(msh, cells)
    values, _pts, _cls, _invalid = _evaluate_on_cells(field, points, cells)

    if values.shape[0] > 0:
        mags = np.abs(np.linalg.norm(values, axis=1))
        local_count = int(mags.size)
        local_sum = float(np.sum(mags))
        local_min = float(np.min(mags))
        local_max = float(np.max(mags))
    else:
        local_count, local_sum = 0, 0.0
        local_min, local_max = float("inf"), float("-inf")

    count = comm.allreduce(local_count, op=MPI.SUM)
    total = comm.allreduce(local_sum, op=MPI.SUM)
    assert count > 0, "no samples on any rank — the reference is vacuous"
    return {
        "count": int(count),
        "min": float(comm.allreduce(local_min, op=MPI.MIN)),
        "max": float(comm.allreduce(local_max, op=MPI.MAX)),
        "mean": float(total / count),
    }


def _regime(msh, cell_tags, tag: int, comm):
    """(ranks with tagged cells, ranks with empty interior *and* tagged cells,
    global interior count) — the fallback regime, measured."""
    tagged = _tagged_cells(cell_tags, tag)
    interior = _interior_tagged_cells(msh, cell_tags, tag)
    has_tagged = int(tagged.size > 0)
    sliver = int(tagged.size > 0 and interior.size == 0)
    return (
        comm.allreduce(has_tagged, op=MPI.SUM),
        comm.allreduce(sliver, op=MPI.SUM),
        comm.allreduce(int(interior.size), op=MPI.SUM),
        comm.allreduce(int(tagged.size), op=MPI.SUM),
    )


# --------------------------------------------------------------------------
# 1. Probe
# --------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    "fixture_name", ["piecewise_sigma_tags", "thin_tag_mesh", "mixed_regime_mesh"]
)
def test_probe_fallback_regimes(request, fixture_name):
    """Probe: which fallback regime does each fixture realise, per rank?

    Prints, for every tag, each rank's tagged / interior / dropped counts and
    whether that rank would take the per-rank fallback.  This is what sizes the
    defect: a rank with tagged cells and an empty interior set, on a mesh whose
    global interior set is non-empty, is the mixed regime the anchor gates.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags = request.getfixturevalue(fixture_name)

    lines = []
    for tag in TAGS:
        tagged = _tagged_cells(cell_tags, tag)
        interior = _interior_tagged_cells(msh, cell_tags, tag)
        sampling, dropped = _sampling_cells_with_interface_guardrails(
            msh, cell_tags, tag, prefer_interior=True
        )
        fallback = tagged.size > 0 and interior.size == 0
        lines.append(
            f"    tag {tag}: tagged {tagged.size}, interior {interior.size}, "
            f"dropped {dropped}, sampling {sampling.size}, "
            f"per-rank fallback {'YES' if fallback else 'no'}"
        )

    for rank in range(comm.size):
        comm.Barrier()
        if comm.rank == rank:
            print(f"\n[POST-1 step 2] {fixture_name} at -n {comm.size}, rank {rank}:")
            print("\n".join(lines), flush=True)
    comm.Barrier()

    if comm.rank == 0:
        print(f"  regimes ({fixture_name}, -n {comm.size}):", flush=True)
    for tag in TAGS:
        n_with_tag, n_sliver, n_interior, n_tagged = _regime(msh, cell_tags, tag, comm)
        if comm.rank == 0:
            regime = (
                "global-fallback"
                if n_interior == 0
                else ("MIXED" if n_sliver > 0 else "interior")
            )
            print(
                f"    tag {tag}: {regime} — ranks holding the tag {n_with_tag}, "
                f"sliver ranks {n_sliver}, global interior {n_interior}, "
                f"global tagged {n_tagged}",
                flush=True,
            )


# --------------------------------------------------------------------------
# 2. Anchor: the interior regime is partition invariant
# --------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("tag", TAGS)
def test_interior_regime_statistics_equal_the_interior_only_reference(
    piecewise_sigma_tags, tag
):
    """Anchor: with a globally non-empty interior set, production samples the
    interior only — on every rank.

    The sentinel makes this exact: an interior-only statistic reads ``max == k``
    and ``mean == k``; a single contaminated sample drags ``max`` to ``100·k``.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags = piecewise_sigma_tags
    field = _sentinel_field(msh, cell_tags)

    _n_with_tag, n_sliver, n_interior, _n_tagged = _regime(msh, cell_tags, tag, comm)
    assert n_interior > 0, (
        f"tag {tag} has no interior cell anywhere at -n {comm.size}: this is the "
        "global-fallback regime, gated elsewhere, not the interior regime"
    )

    interior_ref_cells = np.asarray(
        sorted(
            set(int(c) for c in _tagged_cells(cell_tags, tag))
            - _test_interface_adjacent(msh, cell_tags, tag)
        ),
        dtype=np.int32,
    )
    reference = _stats_over_cells(field, interior_ref_cells, comm)
    production = compute_tagged_vector_magnitude_stats(
        field, cell_tags, tag, comm=comm, prefer_interior_samples=True
    )

    if comm.rank == 0:
        print(
            f"\n[POST-1 step 2] interior regime, tag {tag}, -n {comm.size}, "
            f"sliver ranks {n_sliver}:"
        )
        for key in ("count", "min", "max", "mean"):
            print(
                f"  {key:<6}: production {production[key]!r:>20}  "
                f"interior-only {reference[key]!r:>20}",
                flush=True,
            )

    assert production["count"] == reference["count"], (
        f"production sampled {production['count']} cells against the "
        f"interior-only reference's {reference['count']} at -n {comm.size}: "
        f"{production['count'] - reference['count']} interface-adjacent cells "
        "entered the sample set on some rank, so the statistic depends on the "
        "partition"
    )
    for key in ("min", "max", "mean"):
        assert np.isclose(
            production[key], reference[key], rtol=IDENTITY_RTOL, atol=0.0
        ), (
            f"production '{key}' = {production[key]:.15e} vs interior-only "
            f"{reference[key]:.15e} at -n {comm.size}"
        )

    # The sentinel's own contrast, stated: an interior-only sample set cannot
    # contain the 100x value, so this is what the count identity above is worth.
    assert np.isclose(production["max"], float(tag), rtol=IDENTITY_RTOL, atol=0.0), (
        f"interior-only max is {production['max']} rather than the sentinel's "
        f"interior value {float(tag)}: an interface-adjacent cell "
        f"({INTERFACE_SENTINEL_FACTOR * tag}) was sampled"
    )


# --------------------------------------------------------------------------
# 3. The global-fallback regime: give up everywhere, or nowhere
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_global_fallback_regime_equals_the_full_owned_tagged_set(thin_tag_mesh):
    """A one-cell-thick tag has no interior cell on any rank.

    The guardrail is allowed to give up there — the alternative is no statistic
    at all — but it must give up *globally*, and the result must equal the full
    owned tagged-set reference at any rank count.  Every sample is then an
    interface-adjacent one, so the sentinel reads ``100·k`` exactly.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags = thin_tag_mesh
    field = _sentinel_field(msh, cell_tags)

    _n_with_tag, _n_sliver, n_interior, n_tagged = _regime(
        msh, cell_tags, TAG_HIGH, comm
    )
    assert n_interior == 0, (
        f"the thin slab has {n_interior} interior cells at -n {comm.size}: it is "
        "not one cell thick, so this fixture does not exercise the global "
        "fallback"
    )
    assert n_tagged > 0, "the thin slab is empty — the fixture is vacuous"

    reference = _stats_over_cells(field, _tagged_cells(cell_tags, TAG_HIGH), comm)
    production = compute_tagged_vector_magnitude_stats(
        field, cell_tags, TAG_HIGH, comm=comm, prefer_interior_samples=True
    )

    if comm.rank == 0:
        print(
            f"\n[POST-1 step 2] global-fallback regime, tag {TAG_HIGH}, "
            f"-n {comm.size}: production count {production['count']}, full owned "
            f"tagged {reference['count']}, max {production['max']}",
            flush=True,
        )

    assert production["count"] == reference["count"] == n_tagged
    for key in ("min", "max", "mean"):
        assert np.isclose(production[key], reference[key], rtol=IDENTITY_RTOL, atol=0.0)
    expected = INTERFACE_SENTINEL_FACTOR * TAG_HIGH
    assert np.isclose(production["max"], expected, rtol=IDENTITY_RTOL, atol=0.0), (
        f"every cell of a one-cell-thick tag is interface adjacent, so the "
        f"sentinel max must be {expected}, not {production['max']}"
    )


# --------------------------------------------------------------------------
# 4. Negative control: the mixed regime
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_mixed_regime_is_not_contaminated_by_sliver_ranks(mixed_regime_mesh):
    """Negative control: a rank holding only the sliver must not fall back
    while other ranks sample interiors.

    Under the per-rank fallback the sliver rank contributes its whole tagged
    set, so production exceeds the interior-only reference by exactly those
    ranks' tagged-cell counts — an integer identity — and ``max`` jumps from
    ``k`` to ``100·k``.  If this rank count does not realise the split, the test
    says so and skips rather than claiming exoneration.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags = mixed_regime_mesh
    tag = TAG_HIGH

    _n_with_tag, n_sliver, n_interior, _n_tagged = _regime(msh, cell_tags, tag, comm)

    tagged = _tagged_cells(cell_tags, tag)
    interior = _interior_tagged_cells(msh, cell_tags, tag)
    sliver_tagged = int(tagged.size) if (tagged.size > 0 and interior.size == 0) else 0
    contamination = comm.allreduce(sliver_tagged, op=MPI.SUM)

    if comm.rank == 0:
        print(
            f"\n[POST-1 step 2] mixed regime, tag {tag}, -n {comm.size}: sliver "
            f"ranks {n_sliver}, global interior {n_interior}, predicted "
            f"contamination {contamination} samples",
            flush=True,
        )

    if n_interior == 0 or n_sliver == 0:
        pytest.skip(
            f"at -n {comm.size} the partitioner did not give any rank a "
            f"tagged-but-interior-empty share (sliver ranks {n_sliver}, global "
            f"interior {n_interior}); this rank count does not exhibit the mixed "
            "regime, so it exonerates nothing"
        )

    field = _sentinel_field(msh, cell_tags)
    interior_ref_cells = np.asarray(
        sorted(
            set(int(c) for c in tagged) - _test_interface_adjacent(msh, cell_tags, tag)
        ),
        dtype=np.int32,
    )
    reference = _stats_over_cells(field, interior_ref_cells, comm)
    production = compute_tagged_vector_magnitude_stats(
        field, cell_tags, tag, comm=comm, prefer_interior_samples=True
    )

    if comm.rank == 0:
        print(
            f"  production count {production['count']}, interior-only "
            f"{reference['count']}, excess "
            f"{production['count'] - reference['count']}; max production "
            f"{production['max']} vs interior-only {reference['max']}",
            flush=True,
        )

    assert production["count"] == reference["count"], (
        f"production sampled {production['count'] - reference['count']} cells "
        f"more than the interior-only reference at -n {comm.size} — the "
        f"predicted per-rank-fallback contamination was {contamination} samples "
        "from the sliver ranks, so the fallback decision is being taken rank by "
        "rank instead of globally"
    )
    assert np.isclose(production["max"], float(tag), rtol=IDENTITY_RTOL, atol=0.0), (
        f"max {production['max']} is the sentinel's interface value "
        f"{INTERFACE_SENTINEL_FACTOR * tag}, not its interior value {float(tag)}: "
        "a sliver rank sampled interface-adjacent cells"
    )


# --------------------------------------------------------------------------
# 5. Escape hatch pinned (step 1 audit caveat)
# --------------------------------------------------------------------------


def test_owned_cell_count_escape_hatch_is_characterised():
    """`_owned_cell_count` returns ``None`` for a tags-like object without
    ``.topology``, and `_tagged_cells` then applies **no** ghost filter.

    Pinned, not fixed: production only ever passes a real ``MeshTags``, and the
    fallback exists so the helpers stay usable on a stub.  The assertion is here
    so that the day a caller passes something else, the silent loss of step 1's
    owned-cell restriction is a documented behaviour change rather than a
    rediscovery.
    """
    stub = SimpleNamespace(
        indices=np.array([0, 1, 2, 3], dtype=np.int32),
        values=np.array([1, 1, 2, 1], dtype=np.int32),
        dim=3,
    )
    assert _owned_cell_count(stub) is None
    assert np.array_equal(_tagged_cells(stub, 1), np.array([0, 1, 3], dtype=np.int32))
