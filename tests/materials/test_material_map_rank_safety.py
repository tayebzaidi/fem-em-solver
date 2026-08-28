"""Rank-safety gate for `material_map` tag validation (`OPS-13`).

The defect this file gates was measured in `PORT-1` step 3b-xiii: a material
map over a subdomain small enough to live entirely on one MPI rank was
rejected by `_validate_material_map_tags` on the ranks that owned none of its
cells, because the check read the **rank-local** `cell_tags.values`.  The ranks
then disagreed about whether to enter the solve and the accepting ones hung in
the first collective until the harness timeout killed the session (601 s of
wall clock for a 246 s test session).

Every assertion here is therefore made **on every rank**, and every quantity
compared is reduced first.  The fixture deliberately reproduces the worst case:
exactly **one** cell of the whole mesh is tagged, so at any rank count above
one there is at least one rank whose local tag array is empty.
"""

from __future__ import annotations

import dolfinx
import numpy as np
import pytest
import ufl
from dolfinx import fem
from mpi4py import MPI

from fem_em_solver.core.time_harmonic import (
    HomogeneousMaterial,
    build_material_fields,
    build_mu_r_field,
)
from fem_em_solver.materials import GelledSalinePhantomMaterial

# 3x3x3 hexes, each split into 6 tetrahedra by DolfinX's Kuhn subdivision, so
# every cell of the unit cube has the same volume 1/162 -- a closed form the
# tagged-cell volume is checked against below.
CELLS_PER_SIDE = 3
EXPECTED_CELL_COUNT = 6 * CELLS_PER_SIDE**3
EXPECTED_CELL_VOLUME = 1.0 / EXPECTED_CELL_COUNT

TAGGED_TAG = 7
ABSENT_TAG = 4242
# sigma_default = 0 makes the integral identity a bare product: with every
# untagged cell contributing exactly 0.0, the assembled integral of the DG0
# sigma field is sigma_tagged x (volume of the one tagged cell).
SIGMA_DEFAULT = 0.0
SIGMA_TAGGED = 200.0

DEFAULT_MATERIAL = HomogeneousMaterial(sigma=SIGMA_DEFAULT, epsilon_r=1.0, mu_r=1.0)
TAGGED_MATERIAL = HomogeneousMaterial(sigma=SIGMA_TAGGED, epsilon_r=4.0, mu_r=2.0)


def _global_tag_set(mesh, cell_tags) -> set[int]:
    """Union of `cell_tags.values` across all ranks (the property under test)."""
    local = {int(v) for v in np.unique(cell_tags.values).tolist()}
    return set().union(*mesh.comm.allgather(local))


def _tag_one_global_cell(mesh, tag: int):
    """Tag exactly one cell of the whole mesh, chosen partition-independently.

    The winner is the owned cell whose midpoint is closest to a fixed target
    point; ties break to the lowest rank.  The target is a fixed geometric
    location, so the same physical cell wins at every rank count -- which is
    what lets the volume identity below be compared against a closed form
    rather than against a partition-dependent number.
    """
    tdim = mesh.topology.dim
    owned = mesh.topology.index_map(tdim).size_local
    midpoints = dolfinx.mesh.compute_midpoints(mesh, tdim, np.arange(owned, dtype=np.int32))

    target = np.array([0.05, 0.05, 0.05])
    distances = np.linalg.norm(midpoints - target, axis=1)
    local_best = float(distances.min()) if owned > 0 else np.inf
    local_index = int(np.argmin(distances)) if owned > 0 else -1

    all_best = mesh.comm.allgather(local_best)
    winner_rank = int(np.argmin(all_best))

    if mesh.comm.rank == winner_rank:
        indices = np.array([local_index], dtype=np.int32)
        values = np.full(1, tag, dtype=np.int32)
    else:
        indices = np.zeros(0, dtype=np.int32)
        values = np.zeros(0, dtype=np.int32)

    cell_tags = dolfinx.mesh.meshtags(mesh, tdim, indices, values)

    tagged_globally = mesh.comm.allreduce(int(indices.size), op=MPI.SUM)
    assert tagged_globally == 1, f"fixture tagged {tagged_globally} cells globally, expected exactly 1"
    return cell_tags


def _assemble_dg0_integral(field: fem.Function) -> float:
    """Integral of a DG0 field over the whole mesh, reduced across ranks."""
    local = fem.assemble_scalar(fem.form(field * ufl.dx))
    return float(field.function_space.mesh.comm.allreduce(np.real(local), op=MPI.SUM))


@pytest.fixture()
def unit_cube_with_one_tagged_cell():
    mesh = dolfinx.mesh.create_unit_cube(
        MPI.COMM_WORLD, CELLS_PER_SIDE, CELLS_PER_SIDE, CELLS_PER_SIDE
    )
    cell_tags = _tag_one_global_cell(mesh, TAGGED_TAG)
    return mesh, cell_tags


def test_single_rank_owned_tag_is_accepted_on_every_rank(unit_cube_with_one_tagged_cell):
    """The fix: a globally valid map over a one-rank subdomain builds everywhere.

    Anchors, both asserted on every rank:

    1. exact set identity -- the allgathered tag set equals the enumerated
       global tag set `{TAGGED_TAG}` (the fixture tagged one cell, so the set is
       known by construction, not by measurement);
    2. exact volume identity -- the assembled DG0 sigma field integrates to
       `SIGMA_TAGGED x` the tagged cell's volume, and that volume is the closed
       form `1/162`.
    """
    mesh, cell_tags = unit_cube_with_one_tagged_cell
    comm = mesh.comm

    # Anchor 1: the tag set is a global property; assert it as one, on all ranks.
    assert _global_tag_set(mesh, cell_tags) == {TAGGED_TAG}

    total_cells = comm.allreduce(mesh.topology.index_map(mesh.topology.dim).size_local, op=MPI.SUM)
    assert total_cells == EXPECTED_CELL_COUNT

    material_map = {TAGGED_TAG: TAGGED_MATERIAL}

    # The call the old code failed on the non-owning ranks.
    sigma_field, epsilon_field = build_material_fields(
        mesh, DEFAULT_MATERIAL, cell_tags=cell_tags, material_map=material_map
    )
    mu_field = build_mu_r_field(
        mesh, DEFAULT_MATERIAL, cell_tags=cell_tags, material_map=material_map
    )

    # Every rank got here: agreement is the property being fixed, so prove it
    # collectively rather than trusting rank 0's word for it.
    assert comm.allreduce(1, op=MPI.SUM) == comm.size

    # An indicator built through the production code path, so the volume below
    # is measured with the same dofmap/quadrature as the sigma field.
    indicator = build_material_fields(
        mesh,
        HomogeneousMaterial(sigma=0.0, epsilon_r=1.0),
        cell_tags=cell_tags,
        material_map={TAGGED_TAG: HomogeneousMaterial(sigma=1.0, epsilon_r=1.0)},
    )[0]

    tagged_volume = _assemble_dg0_integral(indicator)
    sigma_integral = _assemble_dg0_integral(sigma_field)

    if comm.rank == 0:
        print(
            f"[OPS-13] ranks={comm.size} cells={total_cells} "
            f"V_tagged={tagged_volume:.17e} (closed form {EXPECTED_CELL_VOLUME:.17e}) "
            f"int(sigma)={sigma_integral:.17e} "
            f"sigma*V={SIGMA_TAGGED * tagged_volume:.17e}"
        )

    # Anchor 2a: the tagged cell is one Kuhn tetrahedron of the unit cube.
    assert tagged_volume == pytest.approx(EXPECTED_CELL_VOLUME, rel=1e-12)

    # Anchor 2b: the identity itself. Only the floating-point summation order
    # differs between the two sides, hence 1e-12 rather than `==`.
    assert sigma_integral == pytest.approx(SIGMA_TAGGED * tagged_volume, rel=1e-12)
    assert sigma_integral == pytest.approx(SIGMA_TAGGED * EXPECTED_CELL_VOLUME, rel=1e-12)

    # The untagged remainder kept the default, so mu integrates over the tagged
    # cell at 2.0 and everywhere else at 1.0 -- a second, independent reading of
    # the same one-cell partition.
    expected_mu_integral = (
        float(DEFAULT_MATERIAL.mu_r) * (1.0 - EXPECTED_CELL_VOLUME)
        + float(TAGGED_MATERIAL.mu_r) * EXPECTED_CELL_VOLUME
    )
    assert _assemble_dg0_integral(mu_field) == pytest.approx(expected_mu_integral, rel=1e-12)

    expected_eps_integral = (
        float(DEFAULT_MATERIAL.epsilon_r) * (1.0 - EXPECTED_CELL_VOLUME)
        + float(TAGGED_MATERIAL.epsilon_r) * EXPECTED_CELL_VOLUME
    )
    assert _assemble_dg0_integral(epsilon_field) == pytest.approx(expected_eps_integral, rel=1e-12)


def test_absent_tag_is_rejected_on_every_rank(unit_cube_with_one_tagged_cell):
    """Negative control: a genuinely missing tag must raise on **all** ranks.

    Ranks disagreeing is the failure mode being fixed, so a rejection that
    happens on only some ranks is exactly as broken as an acceptance that
    happens on only some ranks. Both `build_material_fields` and
    `build_mu_r_field` are checked, and the message must name the missing tag.
    """
    mesh, cell_tags = unit_cube_with_one_tagged_cell
    comm = mesh.comm
    material_map = {ABSENT_TAG: TAGGED_MATERIAL}

    with pytest.raises(ValueError) as excinfo:
        build_material_fields(mesh, DEFAULT_MATERIAL, cell_tags=cell_tags, material_map=material_map)
    assert str(ABSENT_TAG) in str(excinfo.value)
    # The remaining known tag is reported, and it is the *global* one -- a rank
    # owning no tagged cell used to report "Known tags: []".
    assert str(TAGGED_TAG) in str(excinfo.value)

    raised = comm.allgather(True)
    assert len(raised) == comm.size and all(raised)

    with pytest.raises(ValueError) as excinfo_mu:
        build_mu_r_field(mesh, DEFAULT_MATERIAL, cell_tags=cell_tags, material_map=material_map)
    assert str(ABSENT_TAG) in str(excinfo_mu.value)
    assert comm.allreduce(1, op=MPI.SUM) == comm.size


def test_material_map_without_cell_tags_still_raises(unit_cube_with_one_tagged_cell):
    """The pre-existing guard is untouched by the reduction: no tags, no map."""
    mesh, _ = unit_cube_with_one_tagged_cell

    with pytest.raises(ValueError, match="problem.cell_tags"):
        build_material_fields(
            mesh, DEFAULT_MATERIAL, cell_tags=None, material_map={TAGGED_TAG: TAGGED_MATERIAL}
        )
    assert mesh.comm.allreduce(1, op=MPI.SUM) == mesh.comm.size


# ---------------------------------------------------------------------------
# `OPS-29` — the same defect, twenty lines below its own fix.
#
# `build_material_fields`'s `phantom_material` branch was added after `OPS-13`
# and never got the reduction: it tested `phantom_cells.size == 0` on the
# rank-local `cell_tags.values` and raised on every rank that happened to own
# none of the phantom.  Measured on the real fixture (interactive session,
# 2026-08-28, `examples/mri/01_coil_phantom_fields.py`, `coil_phantom_domain`
# at resolution 0.02, 9291 cells, 493 phantom cells globally): at `-n 8` every
# rank owns phantom cells and the example runs; at `-n 12` the per-rank counts
# are [22, 0, 73, 35, 71, 0, 58, 0, 102, 27, 0, 105] and four ranks raise while
# eight walk on into the first collective.  The tag exists globally at both
# widths -- only the partition differs.
#
# The fixture below is the `OPS-13` one unchanged: exactly one cell of the whole
# mesh carries the tag, so at any rank count above 1 some rank's local phantom
# array is empty.  That is the worst case, reached deterministically at smoke
# cost, and it is the same case the coil+phantom mesh reaches by accident.
# ---------------------------------------------------------------------------

PHANTOM_TAG = 3
PHANTOM_SIGMA = 0.72
PHANTOM_EPSILON_R = 76.5
# The example's frequency; the phantom model needs one to validate, and no
# assertion here depends on its value.
PHANTOM_FREQUENCY_HZ = 1.2774e8


def _phantom_material(sigma: float = PHANTOM_SIGMA) -> GelledSalinePhantomMaterial:
    return GelledSalinePhantomMaterial(
        sigma=sigma,
        epsilon_r=PHANTOM_EPSILON_R,
        frequency_hz=PHANTOM_FREQUENCY_HZ,
        mu_r=1.0,
    )


def test_single_rank_owned_phantom_tag_is_accepted_on_every_rank(unit_cube_with_one_tagged_cell):
    """The fix: a phantom tag living on one rank builds on **all** ranks.

    Anchors, both asserted on every rank:

    1. exact set identity -- the allgathered tag set is `{PHANTOM_TAG}`, so the
       tag is present globally and absent locally on at least one rank at any
       width above 1 (the second half is asserted directly below);
    2. exact volume identity -- the assembled DG0 sigma field integrates to
       `PHANTOM_SIGMA x 1/162`, the closed-form volume of one Kuhn tetrahedron
       of the 3x3x3 unit cube.  Partition-independent by construction, so the
       same digits are owed at every rank count.
    """
    mesh, cell_tags = unit_cube_with_one_tagged_cell
    comm = mesh.comm

    # Re-tag the single cell with the phantom tag, keeping the fixture's
    # "exactly one cell globally" property.
    tdim = mesh.topology.dim
    local_indices = np.asarray(cell_tags.indices[cell_tags.values == TAGGED_TAG], dtype=np.int32)
    phantom_tags = dolfinx.mesh.meshtags(
        mesh, tdim, local_indices, np.full(local_indices.size, PHANTOM_TAG, dtype=np.int32)
    )

    assert _global_tag_set(mesh, phantom_tags) == {PHANTOM_TAG}

    # The precondition that makes this a rank-safety test rather than a
    # tautology: at least one rank owns no phantom cell whenever there is more
    # than one rank.  Asserted, not assumed -- if a future partitioner change
    # broke it, the test would silently stop covering the defect.
    local_phantom_cells = int(local_indices.size)
    empty_ranks = comm.allreduce(int(local_phantom_cells == 0), op=MPI.SUM)
    if comm.size > 1:
        assert empty_ranks >= 1, (
            f"fixture no longer reproduces the defect: all {comm.size} ranks own phantom cells"
        )

    # The call the old code failed on every rank owning no phantom cell.
    sigma_field, epsilon_field = build_material_fields(
        mesh,
        DEFAULT_MATERIAL,
        cell_tags=phantom_tags,
        phantom_material=_phantom_material(),
        phantom_tag=PHANTOM_TAG,
    )

    # Every rank got here: agreement is the property under test, so prove it
    # collectively rather than trusting rank 0's word for it.
    assert comm.allreduce(1, op=MPI.SUM) == comm.size

    sigma_integral = _assemble_dg0_integral(sigma_field)
    epsilon_integral = _assemble_dg0_integral(epsilon_field)

    if comm.rank == 0:
        print(
            f"[OPS-29] ranks={comm.size} empty_phantom_ranks={empty_ranks} "
            f"int(sigma)={sigma_integral:.17e} "
            f"closed form={PHANTOM_SIGMA * EXPECTED_CELL_VOLUME:.17e}"
        )

    # Anchor 2: sigma_default is 0.0, so the integral is the bare product
    # sigma_phantom x (volume of the one tagged cell) = 0.72 / 162.
    assert sigma_integral == pytest.approx(PHANTOM_SIGMA * EXPECTED_CELL_VOLUME, rel=1e-12)

    expected_eps_integral = (
        float(DEFAULT_MATERIAL.epsilon_r) * (1.0 - EXPECTED_CELL_VOLUME)
        + PHANTOM_EPSILON_R * EXPECTED_CELL_VOLUME
    )
    assert epsilon_integral == pytest.approx(expected_eps_integral, rel=1e-12)


def test_absent_phantom_tag_is_rejected_on_every_rank(unit_cube_with_one_tagged_cell):
    """Negative control: a globally missing phantom tag must raise on all ranks.

    The reduction must not turn the guard off.  A tag no rank owns is a real
    error -- silently building a phantom-free field would hand back a lossless
    answer for a lossy problem, the same class of silent-wrong-answer the
    module's real-mode refusal exists to prevent.
    """
    mesh, cell_tags = unit_cube_with_one_tagged_cell
    comm = mesh.comm

    with pytest.raises(ValueError) as excinfo:
        build_material_fields(
            mesh,
            DEFAULT_MATERIAL,
            cell_tags=cell_tags,
            phantom_material=_phantom_material(),
            phantom_tag=ABSENT_TAG,
        )
    assert str(ABSENT_TAG) in str(excinfo.value)

    # Raised everywhere, not just where the local array happened to be empty.
    raised = comm.allgather(True)
    assert len(raised) == comm.size and all(raised)


def test_phantom_guards_survive_the_reduction(unit_cube_with_one_tagged_cell):
    """The two pre-existing phantom guards are untouched by the fix."""
    mesh, cell_tags = unit_cube_with_one_tagged_cell

    with pytest.raises(ValueError, match="problem.cell_tags"):
        build_material_fields(
            mesh,
            DEFAULT_MATERIAL,
            cell_tags=None,
            phantom_material=_phantom_material(),
            phantom_tag=PHANTOM_TAG,
        )

    # Same tag claimed by both assignment paths: still rejected, on every rank.
    with pytest.raises(ValueError, match="choose one assignment path"):
        build_material_fields(
            mesh,
            DEFAULT_MATERIAL,
            cell_tags=cell_tags,
            material_map={TAGGED_TAG: TAGGED_MATERIAL},
            phantom_material=_phantom_material(),
            phantom_tag=TAGGED_TAG,
        )

    assert mesh.comm.allreduce(1, op=MPI.SUM) == mesh.comm.size
