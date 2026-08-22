"""Mesh QA checks for required and distinct coil+phantom tags.

`OPS-17` step 2 (2026-08-17): both tests here asserted only that the required
tags were non-empty and (in the first) that two centroids were far apart —
finiteness-class, and in the first test the function body carried no assert of
its own at all. Both now gate the tagged-volume partition identity from
``tests/mesh/helpers.py``: the four required volumes sum to the mesh volume to
``VOLUME_PARTITION_BAND``. An empty tag contributes exactly zero and misses it;
so does a region meshed twice.

The third test gates what region-specific sizing is *for*: a finer size on a
curved region must move that region's meshed volume up, toward the CAD volume
its linear tets inscribe, and never past it. `GEO-17` step 1 (2026-08-20)
replaced its earlier band — "the two sizings agree to 5%" — with that
identity, because the band's premise was wrong: a real 0.015 -> 0.012
refinement of a torus of minor radius 0.01 must move the meshed volume, and by
more than 5% (measured +10.72%). See that test's docstring for the sizing
defect it was carried as a strict xfail for, and for the fix.
"""

import math

from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.io.mesh_qa import print_cell_tag_summary

from tests.mesh.helpers import (
    REQUIRED_COIL_PHANTOM_TAGS,
    assert_required_tags_nonempty,
    assert_tag_volumes_partition_domain,
    assert_tags_distinct_by_centroid,
)

GEOMETRY = dict(
    coil_major_radius=0.08,
    coil_minor_radius=0.01,
    coil_separation=0.08,
    phantom_radius=0.04,
    phantom_height=0.10,
    air_padding=0.04,
    resolution=0.015,
)

# Analytic CAD volumes of the curved regions, for the meshed/CAD recovery
# bounds: two tori ``2 pi^2 R r^2`` and a cylinder ``pi r^2 h``. The air is a
# box minus these and is not gated here.
CAD_VOLUMES = {
    1: 2.0 * math.pi**2 * GEOMETRY["coil_major_radius"] * GEOMETRY["coil_minor_radius"] ** 2,
    2: 2.0 * math.pi**2 * GEOMETRY["coil_major_radius"] * GEOMETRY["coil_minor_radius"] ** 2,
    3: math.pi * GEOMETRY["phantom_radius"] ** 2 * GEOMETRY["phantom_height"],
}

# The region-resolution policy under test: coil 0.012 and phantom 0.010 against
# ``GEOMETRY["resolution"]`` = 0.015, with the air coarsened to 0.020. Hoisted
# to module level by `EX-27` (2026-08-22) so the example imports the sizing it
# demonstrates instead of restating it (`ANS-1`).
POLICY_RESOLUTIONS = dict(
    coil_resolution=0.012,
    phantom_resolution=0.010,
    air_resolution=0.020,
)

# The tags the policy above asks to REFINE relative to ``GEOMETRY["resolution"]``;
# the air (tag 4) is coarsened and is expected to lose the volume its neighbours
# gain.
REFINED_TAGS = (1, 2, 3)

# Pre-stated in the `GEO-17` step-1 plan: under the policy the coil recovery
# must beat the uniform mesh's own 75.5%. Not fitted — measured 83.56% / 83.37%.
POLICY_MIN_CAD_RECOVERY = 0.755

# `OPS-17` step 2's recorded uniform-sizing table (known-issues "Four defects"
# §1, `20260817T111054Z_OPS-17-step2-mesh-n2.log`), carried here as the
# negative control on the `GEO-17` sizing fix.
UNIFORM_VOLUMES_RECORD = {
    1: 1.191750413e-04,
    2: 1.188402981e-04,
    3: 4.943767949e-04,
    4: 1.143560787e-02,
}


def test_coil_phantom_mesh_tag_integrity():
    """The four required tags partition the coarse coil+phantom mesh volume."""
    comm = MPI.COMM_WORLD

    mesh, cell_tags, _ = MeshGenerator.coil_phantom_domain(comm=comm, **GEOMETRY)

    print_cell_tag_summary(cell_tags, tag_names=REQUIRED_COIL_PHANTOM_TAGS, comm=comm, prefix="[mesh-qa] ")

    assert_required_tags_nonempty(cell_tags, REQUIRED_COIL_PHANTOM_TAGS, comm=comm)

    assert_tag_volumes_partition_domain(
        mesh,
        cell_tags,
        REQUIRED_COIL_PHANTOM_TAGS,
        comm=comm,
        label="OPS-17 coil+phantom",
    )

    # Distinctness checks requested by roadmap chunk B2.
    assert_tags_distinct_by_centroid(mesh, cell_tags, tag_a=1, tag_b=3, comm=comm)
    assert_tags_distinct_by_centroid(mesh, cell_tags, tag_a=2, tag_b=3, comm=comm)


def _policy_volume_pair(comm):
    """Tagged volumes of the same CAD under uniform and region-policy sizing."""
    uniform_mesh, uniform_tags, _ = MeshGenerator.coil_phantom_domain(
        comm=comm, **GEOMETRY
    )
    uniform_volumes = assert_tag_volumes_partition_domain(
        uniform_mesh,
        uniform_tags,
        REQUIRED_COIL_PHANTOM_TAGS,
        comm=comm,
        label="OPS-17 uniform sizing",
    )

    mesh, cell_tags, _ = MeshGenerator.coil_phantom_domain(
        comm=comm,
        **POLICY_RESOLUTIONS,
        **GEOMETRY,
    )

    print_cell_tag_summary(cell_tags, tag_names=REQUIRED_COIL_PHANTOM_TAGS, comm=comm, prefix="[mesh-qa] ")
    assert_required_tags_nonempty(cell_tags, REQUIRED_COIL_PHANTOM_TAGS, comm=comm)

    policy_volumes = assert_tag_volumes_partition_domain(
        mesh,
        cell_tags,
        REQUIRED_COIL_PHANTOM_TAGS,
        comm=comm,
        label="OPS-17 region-resolution policy",
    )
    return uniform_volumes, policy_volumes


def test_coil_phantom_mesh_tag_integrity_with_region_resolution_policy():
    """The policy mesh's tags still partition its own volume exactly."""
    comm = MPI.COMM_WORLD
    _policy_volume_pair(comm)


def test_region_resolution_policy_refines_the_tagged_volumes_toward_cad():
    """A finer region size must move that region's meshed volume up, toward CAD.

    `GEO-17` step 1 (2026-08-20) — this test was carried as
    ``xfail(strict=True)`` from `OPS-17` step 2 (2026-08-17), where the policy
    mesh *lost* 21.68% / 22.62% of the two coil volumes while asking for a
    finer coil size. Diagnosed and fixed: ``coil_phantom_domain`` never applied
    the per-region sizes at all — it walked volume -> surfaces -> curves ->
    points through ``gmsh.model.getBoundary`` with the default
    ``combined=True``, whose result for a closed shell is empty, so every
    region collected zero points and ``mesh.setSize`` was never called
    (`20260820T110127Z_GEO-17-step1-diag.log`: "NO SIZE SET" x4, both sizings).
    Only the global CharacteristicLength clamps survived, so the policy run
    meshed the coil at the air's 0.020 ceiling. The sizes are now carried by a
    ``Min`` over per-volume Constant size fields.

    The band this test used to assert (5% between the two sizings) went with
    the old claim that region sizing "must not move the geometry". That claim
    is false for a curved region: an inscribing linear-tet mesh recovers a
    fraction of the CAD volume that grows with refinement, so a real 0.015 ->
    0.012 refinement of a torus of minor radius 0.01 *must* move the volume,
    and by more than 5%. The gate is therefore the identity `GEO-17` step 1
    pre-registered: the **sign** of the move, plus the CAD recovery bounds.

    Measured at `-n 2`, `20260820T110407Z_GEO-17-step1-probe-defaults.log`,
    uniform h = 0.015 against coil 0.012 / phantom 0.010 / air 0.020:

        tag 1 (coil_1):  1.191750413e-04 -> 1.319468693e-04 m^3  (+10.72%)
        tag 2 (coil_2):  1.188402981e-04 -> 1.316573175e-04 m^3  (+10.79%)
        tag 3 (phantom): 4.943767949e-04 -> 4.990112950e-04 m^3  ( +0.94%)
        tag 4 (air):     1.143560787e-02 -> 1.140538452e-02 m^3  ( -0.26%)

    Coil recovery against ``2 pi^2 R r^2`` = 1.579137e-04 m^3 goes 75.47% ->
    83.56% and 75.26% -> 83.37%; the air is the one region the policy
    *coarsens* (0.015 -> 0.020), and it is the one region that loses volume,
    to its refined neighbours. The uniform column is unmoved from the
    `OPS-17` record to every printed digit — the fix does not touch a mesh
    that asks for one size everywhere.
    """
    comm = MPI.COMM_WORLD
    uniform_volumes, policy_volumes = _policy_volume_pair(comm)

    for tag, name in sorted(REQUIRED_COIL_PHANTOM_TAGS.items()):
        v_uniform = uniform_volumes[tag]
        v_policy = policy_volumes[tag]
        if comm.rank == 0:
            print(
                f"[GEO-17] tag {tag} ({name}): uniform {v_uniform:.9e} m^3 vs "
                f"policy {v_policy:.9e} m^3 ({v_policy / v_uniform - 1.0:+.4%})",
                flush=True,
            )

    # Negative control: the fix may not move the uniform path. Recorded in
    # known-issues "Four defects" §1 from `20260817T111054Z_OPS-17-step2-mesh-n2.log`.
    for tag, v_recorded in UNIFORM_VOLUMES_RECORD.items():
        rel = abs(uniform_volumes[tag] / v_recorded - 1.0)
        assert rel < 1.0e-9, (
            f"uniform sizing moved tag {tag} "
            f"({REQUIRED_COIL_PHANTOM_TAGS[tag]}) by {rel:.3e} against its "
            f"OPS-17 record: {v_recorded:.9e} -> {uniform_volumes[tag]:.9e} m^3"
        )

    # The identity: every region the policy refines gains meshed volume.
    for tag in REFINED_TAGS:
        name = REQUIRED_COIL_PHANTOM_TAGS[tag]
        assert policy_volumes[tag] > uniform_volumes[tag], (
            f"region-resolution policy asked for a FINER size on tag {tag} "
            f"({name}) and the meshed volume did not grow: "
            f"{uniform_volumes[tag]:.9e} -> {policy_volumes[tag]:.9e} m^3. "
            "A linear-tet mesh inscribes a curved surface, so refinement can "
            "only move meshed volume up toward CAD"
        )

    # ... and toward, never past, the CAD volume it inscribes.
    for tag, cad_volume in CAD_VOLUMES.items():
        name = REQUIRED_COIL_PHANTOM_TAGS[tag]
        for label, volumes in (("uniform", uniform_volumes), ("policy", policy_volumes)):
            recovery = volumes[tag] / cad_volume
            if comm.rank == 0:
                print(
                    f"[GEO-17] tag {tag} ({name}) {label} meshed/CAD = "
                    f"{recovery:.6f}",
                    flush=True,
                )
            assert recovery <= 1.0, (
                f"{label} mesh recovers {recovery:.6f} of tag {tag} ({name})'s "
                f"CAD volume {cad_volume:.9e} m^3 — an inscribing linear-tet "
                "mesh cannot exceed 1.0"
            )

        assert policy_volumes[tag] / cad_volume >= POLICY_MIN_CAD_RECOVERY, (
            f"policy mesh recovers only "
            f"{policy_volumes[tag] / cad_volume:.6f} of tag {tag} ({name})'s "
            f"CAD volume, below the pre-stated {POLICY_MIN_CAD_RECOVERY} "
            "(the uniform mesh's own recovery, which a finer request must beat)"
        )
