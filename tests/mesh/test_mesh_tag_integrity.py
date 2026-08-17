"""Mesh QA checks for required and distinct coil+phantom tags.

`OPS-17` step 2 (2026-08-17): both tests here asserted only that the required
tags were non-empty and (in the first) that two centroids were far apart —
finiteness-class, and in the first test the function body carried no assert of
its own at all. Both now gate the tagged-volume partition identity from
``tests/mesh/helpers.py``: the four required volumes sum to the mesh volume to
``VOLUME_PARTITION_BAND``. An empty tag contributes exactly zero and misses it;
so does a region meshed twice.

The second test's point is that region-specific sizing must not move the
geometry, so it asserts the stronger thing directly: every tag's volume agrees
with the uniform-sizing run's to ``POLICY_VOLUME_RTOL``. Both runs mesh the
same CAD, so the only difference between the two volume sets is the chordal
deficit of the curved coil and phantom surfaces at the two different cell
sizes — a percent-level effect on the curved regions, which is what the band
admits, and which the old ``size_global > 0`` said nothing about.
"""

import pytest
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

# Curved-surface chordal deficit between the two sizings; see the module
# docstring. Pre-stated, not fitted.
POLICY_VOLUME_RTOL = 0.05


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
        coil_resolution=0.012,
        phantom_resolution=0.010,
        air_resolution=0.020,
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "known-issues 2026-08-17 (OPS-17 step 2): region-specific sizing "
        "shrinks the meshed coil volumes by ~22% even though it specifies a "
        "FINER coil size than the uniform run. Measured, not tolerated — the "
        "band below is the correct one and is deliberately left strict so this "
        "flips to XPASS the moment the sizing path is fixed."
    ),
)
def test_region_resolution_policy_does_not_move_the_tagged_volumes():
    """Region-specific sizing must change cell sizes, not geometry.

    `OPS-17` step 2 (2026-08-17) — **this test is a finding, not a pass.**

    Measured at `-n 2`, `20260817T111054Z_OPS-17-step2-mesh-n2.log`, uniform
    h = 0.015 against coil 0.012 / phantom 0.010 / air 0.020:

        tag 1 (coil_1):  1.191750413e-04 -> 9.333354960e-05 m^3  (-21.68%)
        tag 2 (coil_2):  1.188402981e-04 -> 9.195675344e-05 m^3  (-22.62%)
        tag 3 (phantom): 4.943767949e-04 -> 4.880940997e-04 m^3  ( -1.27%)
        tag 4 (air):     1.143560787e-02 -> 1.149461560e-02 m^3  ( +0.52%)

    The CAD torus volume is ``2 pi^2 R r^2`` = 1.579137e-04 m^3, so the uniform
    mesh recovers 75.5% of each coil and the policy mesh only 59.1%. The sign is
    the finding: every region named in the policy is given a **finer** size than
    the uniform run, and every one of them comes out with *less* volume — a
    linear-tet mesh inscribes a curved surface, so refining can only move the
    meshed volume up towards CAD, never down by 22%. The phantom moves the same
    way, an order of magnitude less, and the air takes up exactly what the
    curved regions lose. That points at the region size fields being applied as
    a replacement for, rather than a refinement of, the surface sizing on the
    shared curved interfaces — plausibly the coarser air field (0.020) winning
    on the coil and phantom boundaries.

    Diagnosing that is `GEO` work on ``coil_phantom_domain``, not this chunk's
    (`OPS-17` is test hygiene). The band stays at the value physics says it
    should be, the marker is ``strict=True`` so a fix is reported as XPASS, and
    the known-issues entry carries the same numbers.
    """
    comm = MPI.COMM_WORLD
    uniform_volumes, policy_volumes = _policy_volume_pair(comm)

    for tag, name in sorted(REQUIRED_COIL_PHANTOM_TAGS.items()):
        v_uniform = uniform_volumes[tag]
        v_policy = policy_volumes[tag]
        rel = abs(v_policy / v_uniform - 1.0)
        if comm.rank == 0:
            print(
                f"[OPS-17] tag {tag} ({name}): uniform {v_uniform:.9e} m^3 vs "
                f"policy {v_policy:.9e} m^3 ({v_policy / v_uniform - 1.0:+.4%})",
                flush=True,
            )
        assert rel < POLICY_VOLUME_RTOL, (
            f"region-resolution policy moved tag {tag} ({name}) by {rel:.4%}, "
            f"outside the {POLICY_VOLUME_RTOL:.0%} chordal-deficit band: "
            f"{v_uniform:.9e} -> {v_policy:.9e} m^3; the policy is meant to "
            "change cell sizes, not geometry"
        )
