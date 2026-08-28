#!/usr/bin/env python3
"""A gmsh geometry failure must raise on *every* rank, not deadlock the job.

`GEO-23` step 2a's gate, and `GEO-22`'s restated done-when.  The generators in
``io/mesh.py`` build their gmsh model on one rank and then call the collective
``_model_to_mesh``; before step 2a, a throw on the building rank left the other
ranks blocked there forever, so a two-second geometry failure cost the harness
its whole window (step 1 measured Status 124 at 120-121 s on three sites where
the already-wrapped ``birdcage_port_domain`` footered at Status 1 in 5 s).

The rung below is a *measured* failure, not an invented one: `GEO-22` step 1
bisected ``straight_wire_domain`` on the ``mag:1`` example's own geometry over
nine rungs and found h = 0.00875 among the failing ones, bit-reproducibly over
two independent runs.  It is asserted here as a raise-path property only — the
chunk's finding is that the failing set is non-monotone in h, so this test says
nothing about which resolutions mesh and must never be read as a floor.

Rank-safety: ``pytest.raises`` on one rank is exactly the trap this test
exists to catch, so the caught flag is reduced with ``allreduce`` and the
messages are ``allgather``ed before anything is asserted.
"""

from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator

# `mag:1` / `EX-30`'s own straight-wire geometry, as `GEO-22` step 1 swept it
# (tests/validation/probe_straight_wire_mesh_resolution.py:56-59).
EXAMPLE_WIRE_LENGTH = 0.3
EXAMPLE_WIRE_RADIUS = 0.003
EXAMPLE_DOMAIN_RADIUS = 0.04

# A rung `GEO-22` step 1 measured as FAIL on that geometry, twice, identically.
FAILING_RESOLUTION = 0.00875


def test_a_failing_straight_wire_rung_raises_on_every_rank():
    comm = MPI.COMM_WORLD

    caught = 0
    message = ""
    try:
        MeshGenerator.straight_wire_domain(
            wire_length=EXAMPLE_WIRE_LENGTH,
            wire_radius=EXAMPLE_WIRE_RADIUS,
            domain_radius=EXAMPLE_DOMAIN_RADIUS,
            resolution=FAILING_RESOLUTION,
            comm=comm,
        )
    except BaseException as exc:  # noqa: BLE001 - the raise path is the subject
        caught = 1
        message = f"{type(exc).__name__}: {exc}"

    # Collective, and before any assertion: a rank that sailed past the throw
    # is the defect, and it can only be seen from another rank.
    total_caught = comm.allreduce(caught, op=MPI.SUM)
    messages = comm.allgather(message)

    assert total_caught == comm.size, (
        f"{comm.size - total_caught} of {comm.size} ranks did not raise for a "
        f"straight_wire_domain geometry that fails at resolution="
        f"{FAILING_RESOLUTION}; per-rank messages: {messages}"
    )

    # The non-building ranks carry the wrapped diagnostic, so a reader of one
    # rank's traceback learns which generator and which sizing failed.
    for non_building_rank in range(1, comm.size):
        text = messages[non_building_rank]
        assert "straight_wire_domain" in text, text
        assert str(FAILING_RESOLUTION) in text, text
