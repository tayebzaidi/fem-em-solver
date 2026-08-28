#!/usr/bin/env python3
"""Cylindrical-domain mesh generation: the tagged volumes partition the mesh.

Filed as a dead module by `OPS-26` step 2 leg (a) (2026-08-27) — it collected
**zero** tests, meshed at import time and only `print`ed its three counts, so
nothing it computed could ever fail.  `GEO-23` step 1 (d) converts it to the
quantitative form of the identity it was already printing: the inner and outer
tag volumes sum to the mesh volume to 1e-9.  Counts are rank-local and were
never reduced in the old body; the volume route goes through the shared helper,
which reduces.

The sizing is deliberately left at the module's original ``resolution=0.02``.
`GEO-23` step 1 (c) measured this generator's coarse floor on the *other* call
site's geometry (fails at h = 0.04, meshes from h = 0.032 down); 0.02 is well
inside the meshing range and is not this chunk's to move.
"""

from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator

from tests.mesh.helpers import assert_tag_volumes_partition_domain

INNER_TAG = 1
OUTER_TAG = 2


def test_cylindrical_domain_tag_volumes_partition_the_mesh():
    comm = MPI.COMM_WORLD
    mesh, cell_tags, _ = MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.1,
        length=0.2,
        resolution=0.02,
        comm=comm,
    )

    volumes = assert_tag_volumes_partition_domain(
        mesh,
        cell_tags,
        (INNER_TAG, OUTER_TAG),
        comm=comm,
        label="cylindrical_domain",
    )

    # The annulus is the bulk of the domain: r_o^2 - r_i^2 = 0.0099 against
    # r_i^2 = 0.0001, i.e. 99:1 by closed-form volume.  Ordering alone catches a
    # tag swap, which the partition sum cannot see.
    assert volumes[OUTER_TAG] > volumes[INNER_TAG], (
        f"outer tag {volumes[OUTER_TAG]:.6e} m^3 should exceed inner tag "
        f"{volumes[INNER_TAG]:.6e} m^3 -- tags may be swapped"
    )
