"""`GEO-9` step-2a gate: a failed birdcage must not poison the process.

Known-issues 7 recorded three `tests/mesh` tests failing at
``dolfinx/io/gmshio.py:118: AssertionError``. `GEO-9` step 1 measured the cause:
the coil+phantom generator is innocent and passes in a fresh process; it fails
only when ``test_birdcage_port_tags.py`` has run **earlier in the same
process**. ``birdcage_port_domain`` raises inside its rank-0 block (overlapping
facets — that geometry defect is step 2b's, and is untouched here) and so never
reached ``gmsh.finalize()``. gmsh stayed initialised and mid-command, every
later ``occ`` call was refused, and ``model_to_mesh`` read the stale birdcage
model.

The 03:00 review's audit added the sharper half of the before-state: the
contaminated process does not merely fail, it **hangs**. Rank 0 raised and left
the collective ``model_to_mesh``, so the other rank blocked in it forever —
``20260803T123116Z_GEO-9-step2a-before.log``: pytest reports 5 failed 2 passed
in 3.16 s, but the harness exits **124 at the 180 s ceiling**.

This file gates both halves in one process, in the order that used to break:
the birdcage still fails loudly, gmsh is left finalized, and the coil+phantom
volume-partition identities then hold to ``1e-9`` — identities that previously
could not execute here at all.
"""

from __future__ import annotations

import gmsh
import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator
from tests.mesh.helpers import global_cell_tag_set
from tests.mesh.test_coil_phantom_conforming import (
    AIR_TAG,
    COIL_TAGS,
    PHANTOM_RADIUS,
    PHANTOM_HEIGHT,
    PHANTOM_TAG,
    _analytic_box_volume,
    _generate,
    _tag_volume,
    _total_volume,
)


def _attempt_birdcage(comm):
    """The `test_birdcage_port_tags.py` fixture, verbatim in its failing form."""
    return MeshGenerator.birdcage_port_domain(
        leg_count=4,
        ring_radius=0.07,
        leg_width=0.012,
        leg_spacing=0.11,
        coil_length=0.14,
        ring_minor_radius=0.004,
        phantom_radius=0.03,
        phantom_height=0.08,
        port_box_size=(0.010, 0.008, 0.010),
        air_padding=0.03,
        resolution=0.015,
        comm=comm,
    )


def test_failed_birdcage_leaves_gmsh_clean_and_later_meshes_still_conform():
    """Birdcage first, coil+phantom second, one process — the poisoning order."""
    comm = MPI.COMM_WORLD

    # 1. The birdcage still fails loudly. Swallowing it would hide step 2b's
    #    real geometry defect, which this step does not touch.
    with pytest.raises(Exception) as excinfo:  # noqa: PT011 — gmsh raises bare Exception
        _attempt_birdcage(comm)
    message = str(excinfo.value)
    assert message.strip(), "the birdcage failure must not be swallowed or blanked"

    # 2. gmsh is finalized on the rank that built the model. This is the fix
    #    itself: before it, gmsh stayed initialised and answered every later
    #    `occ` call with "I'm busy! Ask me that later...".
    if comm.rank == 0:
        assert not gmsh.isInitialized(), (
            "a failed birdcage_port_domain left gmsh initialised; every later "
            "occ call in this process will be refused (known-issues 7)"
        )

    # 3. Every rank raised, so none is still blocked in the collective
    #    model_to_mesh. Reaching this line at -n 2 is that assertion: the
    #    before-state hung here until the 180 s timeout killed it.
    assert comm.allreduce(1, op=MPI.SUM) == comm.size

    # 4. The `GEO-8`/`GEO-9`-step-1 volume-partition identity, now evaluated in
    #    the contaminated process. Before this change these two lines could not
    #    run here at all — model_to_mesh read the stale birdcage model.
    msh, cell_tags, _ = _generate(phantom_placement_preset="centered")
    assert global_cell_tag_set(msh, cell_tags) == {1, 2, 3, 4}

    v_box = _analytic_box_volume()
    v_total = _total_volume(msh, comm)
    v_tagged = sum(
        _tag_volume(msh, cell_tags, t, comm)
        for t in (*COIL_TAGS, PHANTOM_TAG, AIR_TAG)
    )
    v_phantom = _tag_volume(msh, cell_tags, PHANTOM_TAG, comm)
    v_cylinder = np.pi * PHANTOM_RADIUS**2 * PHANTOM_HEIGHT

    if comm.rank == 0:
        print(
            f"\n[after failed birdcage] V_box={v_box:.6e}  V_mesh={v_total:.6e}  "
            f"ratio={v_total / v_box:.12f}  sum(tagged)/V_mesh="
            f"{v_tagged / v_total:.12f}"
            f"\n[after failed birdcage] V_phantom={v_phantom:.6e}  "
            f"meshed/analytic={v_phantom / v_cylinder:.4f}"
            f"\n[after failed birdcage] birdcage error: {message.splitlines()[0]}",
            flush=True,
        )

    assert abs(v_total / v_box - 1.0) < 1e-9, (
        f"total mesh volume {v_total:.6e} m^3 vs analytic box {v_box:.6e} m^3 "
        f"(ratio {v_total / v_box:.12f}) after a failed birdcage in the same "
        "process"
    )
    assert abs(v_tagged / v_total - 1.0) < 1e-9
    assert 0.90 * v_cylinder < v_phantom < v_cylinder
