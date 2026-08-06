"""`POST-1` step 1: ghost-cell partition invariance of the tagged-cell aggregation.

``post/phantom_fields.py::_tagged_cells`` filters ``cell_tags.indices`` by value
with **no owned-cell restriction**.  A DolfinX ``MeshTags`` built from
``locate_entities`` carries ghost cells as well as owned ones (the piecewise-σ
fixture below does exactly that), so under MPI the same cell can enter the
sample set on two ranks at once and every reported statistic — ``count``,
``min``, ``max``, ``mean`` — becomes rank-count dependent.  Neither identity
`POST-3` step 4 gated could see it: both compare the *same* sample set through
two code paths.

The anchor here is a partition-invariance identity.  For each tag and for both
``prefer_interior`` paths, the production statistics must equal a reference
built over the **owned** sampling cells only (``cells < index_map.size_local``,
then allreduced): ``count`` exactly, the floats to ``1e-12``.  The owned cells
of all ranks are a true partition of the mesh, so that reference is the
rank-count-independent answer by construction.

The negative control is the pre-fix aggregation itself, kept in this file: a
deliberately ghost-inclusive reduction over every tagged cell must exceed the
owned reference's ``count`` by **exactly** the number of tagged ghost sampling
cells, measured in the same test.  If that separation is 0 the fixture cannot
exhibit the defect at all and this file proves nothing — so it is asserted
positive rather than assumed.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/post/test_tagged_cell_partition_invariance.py -v -s'

and again at ``-n 4``: a defect in a ghost-cell filter is a function of the
partition, so one rank count is not a measurement.
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.post.phantom_fields import (
    _cell_centroids,
    _evaluate_on_cells,
    _interior_tagged_cells,
    _sampling_cells_with_interface_guardrails,
    _tagged_cells,
    compute_tagged_vector_magnitude_stats,
)

from tests.complex_mode import complex_only
from tests.post.test_phantom_phasor_semantics import (
    FIXTURE_N,
    _solve_two_material_fixture,
)
from tests.validation.test_poynting_balance import TAG_HIGH, TAG_LOW

# The identity is exact — the two reductions differ only in summation order —
# so the tolerance is round-off, not physics.
IDENTITY_RTOL = 1e-12

TAGS = (TAG_LOW, TAG_HIGH)
PREFER_INTERIOR = (True, False)


@pytest.fixture(scope="module")
def piecewise_sigma_field():
    """`POST-3` step 4's fixture, unchanged: one 12³ piecewise-σ complex solve."""
    return _solve_two_material_fixture(FIXTURE_N)


def _n_owned(mesh) -> int:
    return int(mesh.topology.index_map(mesh.topology.dim).size_local)


def _stats_over_cells(field, cells: np.ndarray, comm) -> dict[str, float]:
    """Allreduced count/min/max/mean of the phasor magnitude over ``cells``.

    Mirrors :func:`compute_tagged_vector_magnitude_stats`'s reduction exactly —
    the only degree of freedom under test is *which cells* go in.
    """
    mesh = field.function_space.mesh
    points = _cell_centroids(mesh, cells)
    values, _points, _cells, _invalid = _evaluate_on_cells(field, points, cells)

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


def _all_tagged_cells(cell_tags, tag: int) -> np.ndarray:
    """Every tagged cell, owned and ghost — the pre-fix ``_tagged_cells`` body."""
    return np.asarray(cell_tags.indices[cell_tags.values == int(tag)], dtype=np.int32)


@complex_only
@pytest.mark.integration
def test_probe_tagged_ghost_cell_separation(piecewise_sigma_field):
    """Probe: how many tagged cells on this fixture are ghosts, per rank?

    This sizes the defect before anything is gated.  A tagged ghost count of 0
    would mean the fixture cannot exhibit rank-count dependence at all, and the
    invariance tests below would be vacuous rather than exonerating — so the
    count is asserted positive, not merely printed.
    """
    comm = MPI.COMM_WORLD
    e_field, cell_tags = piecewise_sigma_field
    mesh = e_field.function_space.mesh
    n_owned = _n_owned(mesh)
    n_ghost = int(mesh.topology.index_map(mesh.topology.dim).num_ghosts)

    lines = [f"  rank {comm.rank}: owned cells {n_owned}, ghost cells {n_ghost}"]
    total_ghost_tagged = 0
    for tag in TAGS:
        all_tagged = _all_tagged_cells(cell_tags, tag)
        ghost_tagged = int(np.count_nonzero(all_tagged >= n_owned))
        total_ghost_tagged += ghost_tagged
        lines.append(
            f"    tag {tag}: tagged {all_tagged.size} "
            f"(owned {all_tagged.size - ghost_tagged}, ghost {ghost_tagged})"
        )
        for prefer in PREFER_INTERIOR:
            sampling, dropped = _sampling_cells_with_interface_guardrails(
                mesh, cell_tags, tag, prefer_interior=prefer
            )
            ghost_sampling = int(np.count_nonzero(sampling >= n_owned))
            lines.append(
                f"      prefer_interior={prefer}: sampling {sampling.size} "
                f"(ghost {ghost_sampling}, boundary-dropped {dropped})"
            )

    for rank in range(comm.size):
        comm.Barrier()
        if comm.rank == rank:
            print(f"\n[POST-1 step 1] probe at -n {comm.size}:")
            print("\n".join(lines), flush=True)
    comm.Barrier()

    global_ghost_tagged = comm.allreduce(total_ghost_tagged, op=MPI.SUM)
    if comm.rank == 0:
        print(
            f"  total tagged ghost cells across ranks: {global_ghost_tagged}",
            flush=True,
        )

    if comm.size == 1:
        pytest.skip("serial run has no ghost cells; the defect is an MPI one")

    assert global_ghost_tagged > 0, (
        f"no tagged cell on any of {comm.size} ranks is a ghost, so this fixture "
        "cannot exhibit the double-counting defect: the invariance assertions "
        "below would be vacuous, not exonerating"
    )


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("tag", TAGS)
@pytest.mark.parametrize("prefer_interior", PREFER_INTERIOR)
def test_statistics_are_owned_cell_partition_invariant(
    piecewise_sigma_field, tag, prefer_interior
):
    """Anchor: production statistics equal the owned-cells-only reference.

    Owned cells partition the mesh exactly once across ranks, so the reference
    is what a serial run would report.  Any disagreement is a cell sampled by
    two ranks at once — i.e. a statistic that depends on how many ranks the job
    happened to use.
    """
    comm = MPI.COMM_WORLD
    e_field, cell_tags = piecewise_sigma_field
    mesh = e_field.function_space.mesh
    n_owned = _n_owned(mesh)

    production = compute_tagged_vector_magnitude_stats(
        e_field, cell_tags, tag, comm=comm, prefer_interior_samples=prefer_interior
    )

    sampling, _dropped = _sampling_cells_with_interface_guardrails(
        mesh, cell_tags, tag, prefer_interior=prefer_interior
    )
    owned_reference = _stats_over_cells(e_field, sampling[sampling < n_owned], comm)

    if comm.rank == 0:
        print(
            f"\n[POST-1 step 1] tag {tag}, prefer_interior={prefer_interior}, "
            f"-n {comm.size}:"
        )
        for key in ("count", "min", "max", "mean"):
            print(
                f"  {key:<6}: production {production[key]!r:>24}  "
                f"owned-only {owned_reference[key]!r:>24}",
                flush=True,
            )

    assert production["count"] == owned_reference["count"], (
        f"production count {production['count']} != owned-cells-only "
        f"{owned_reference['count']} at -n {comm.size}: "
        f"{production['count'] - owned_reference['count']} tagged cells are "
        "sampled by more than one rank, so the statistic depends on the rank count"
    )
    for key in ("min", "max", "mean"):
        assert np.isclose(
            production[key], owned_reference[key], rtol=IDENTITY_RTOL, atol=0.0
        ), (
            f"production '{key}' = {production[key]:.15e} vs owned-cells-only "
            f"{owned_reference[key]:.15e} at -n {comm.size} — the aggregation is "
            "not partition invariant"
        )


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("tag", TAGS)
def test_production_default_samples_the_full_owned_tagged_set(
    piecewise_sigma_field, tag
):
    """`POST-1` step 5: the *default* path is the full owned tagged set.

    Every other test in this file passes ``prefer_interior_samples`` explicitly,
    so none of them can see which value the production entry point picks when a
    caller passes nothing — and that is exactly what step 5 changed.  Here the
    call carries **no** sampling kwarg, and its statistics are required to equal
    the reference built over every owned tagged cell: ``count`` exactly, the
    floats to ``1e-12``.  Reusing :func:`_stats_over_cells` keeps the reduction
    identical, so the only degree of freedom is the default itself.

    The negative control is the retired behaviour, still reachable: passing
    ``prefer_interior_samples=True`` must sample **strictly fewer** cells, short
    by exactly the number of boundary-adjacent tagged cells the guardrail drops.
    If that difference were 0 the default would be unobservable on this fixture
    and the assertion above would prove nothing.
    """
    comm = MPI.COMM_WORLD
    e_field, cell_tags = piecewise_sigma_field
    mesh = e_field.function_space.mesh

    # No ``prefer_interior_samples`` — this is the production call.
    production = compute_tagged_vector_magnitude_stats(e_field, cell_tags, tag, comm=comm)
    full_owned = _stats_over_cells(e_field, _tagged_cells(cell_tags, tag), comm)

    guarded = compute_tagged_vector_magnitude_stats(
        e_field, cell_tags, tag, comm=comm, prefer_interior_samples=True
    )
    interior = _interior_tagged_cells(mesh, cell_tags, tag)
    n_dropped = comm.allreduce(
        int(_tagged_cells(cell_tags, tag).size - interior.size), op=MPI.SUM
    )

    if comm.rank == 0:
        print(f"\n[POST-1 step 5] tag {tag}, -n {comm.size}, default sampling:")
        for key in ("count", "min", "max", "mean"):
            print(
                f"  {key:<6}: default {production[key]!r:>24}  "
                f"full-owned {full_owned[key]!r:>24}  "
                f"prefer_interior=True {guarded[key]!r:>24}",
                flush=True,
            )
        print(
            f"  guardrail drops {n_dropped} boundary-adjacent tagged cells "
            f"({production['count'] - guarded['count']} fewer samples)",
            flush=True,
        )

    assert production["count"] == full_owned["count"], (
        f"the default path sampled {production['count']} cells, not the "
        f"{full_owned['count']} owned tagged cells: ``prefer_interior_samples`` "
        "does not default to False"
    )
    for key in ("min", "max", "mean"):
        assert np.isclose(
            production[key], full_owned[key], rtol=IDENTITY_RTOL, atol=0.0
        ), (
            f"default '{key}' = {production[key]:.15e} vs full-owned-set "
            f"{full_owned[key]:.15e} — the default path is not sampling the "
            "full owned tagged set"
        )

    assert n_dropped > 0, (
        f"the guardrail drops no cell of tag {tag} at -n {comm.size}; the two "
        "sampling rules coincide here, so this fixture cannot see the default"
    )
    assert production["count"] - guarded["count"] == n_dropped, (
        f"the retained ``prefer_interior_samples=True`` path sampled "
        f"{guarded['count']} cells, {production['count'] - guarded['count']} "
        f"fewer than the default, not the {n_dropped} boundary-adjacent cells "
        "it drops: the old behaviour is not reproduced by passing True"
    )


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("tag", TAGS)
def test_ghost_inclusive_control_overcounts_by_exactly_the_ghost_count(
    piecewise_sigma_field, tag
):
    """Negative control: the pre-fix aggregation, reproduced beside the fix.

    Summing over *every* tagged cell (the old ``_tagged_cells`` body) counts each
    tagged ghost once more than the owned partition does.  The excess must equal
    the tagged ghost count exactly — an integer identity, not a band — which is
    what says the invariance above is a property of the fix rather than of a
    fixture with no ghosts in it.
    """
    comm = MPI.COMM_WORLD
    if comm.size == 1:
        pytest.skip("serial run has no ghost cells; the control needs a partition")

    e_field, cell_tags = piecewise_sigma_field
    mesh = e_field.function_space.mesh
    n_owned = _n_owned(mesh)

    all_tagged = _all_tagged_cells(cell_tags, tag)
    owned_tagged = all_tagged[all_tagged < n_owned]

    ghost_inclusive = _stats_over_cells(e_field, all_tagged, comm)
    owned_reference = _stats_over_cells(e_field, owned_tagged, comm)
    ghost_count = comm.allreduce(int(all_tagged.size - owned_tagged.size), op=MPI.SUM)

    excess = ghost_inclusive["count"] - owned_reference["count"]
    if comm.rank == 0:
        print(
            f"\n[POST-1 step 1] negative control, tag {tag}, -n {comm.size}: "
            f"ghost-inclusive count {ghost_inclusive['count']}, owned "
            f"{owned_reference['count']}, excess {excess}, tagged ghosts "
            f"{ghost_count}",
            flush=True,
        )
        print(
            f"  mean: ghost-inclusive {ghost_inclusive['mean']:.12e} vs owned "
            f"{owned_reference['mean']:.12e}",
            flush=True,
        )

    assert ghost_count > 0, (
        f"tag {tag} has no ghost cells at -n {comm.size}; the control cannot "
        "separate the two aggregations"
    )
    assert excess == ghost_count, (
        f"ghost-inclusive aggregation exceeds the owned reference by {excess}, "
        f"not by the {ghost_count} tagged ghost cells: the two aggregations do "
        "not differ in the way the defect predicts"
    )
