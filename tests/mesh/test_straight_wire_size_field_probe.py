#!/usr/bin/env python3
"""The wire-surface size field removes gmsh's triangle-collapse fallback.

`GEO-22` step 2c: the assert behind step 2's probe.  Step 2 ran leg D of
``tests/validation/probe_straight_wire_mesh_resolution.py`` and read 18/18
rungs meshing with 0/18 "N triangles are equivalent" lines, against leg C's
18/18 fallbacks — but a probe asserts nothing, which is why the chunk was
demoted on §4 clause 3 (2026-08-29 10:30 review).  This module turns the
finding into a gate on the single rung both tables share with the ``mag:1``
example: the example geometry at ``resolution = 0.008``, built twice in one
process — once under leg D's ``_SizeFieldPatch``, once without it.

The field parameters are never restated here; they are imported, so a change
to the probe's field moves this gate with it.

**Anchors** (§4 3(iv), documented prior-run references, ±1%):

* patched:  19 823 cells, fallback count **== 0**
  (``20260829T123331Z_GEO-22-step2-sizefield.log``, leg D/example at 0.008)
* control:  21 830 cells, fallback count **>= 1**
  (``mag:1``'s own record, reproduced by step 2's leg-C control at the same
  rung in its own process)

The control build *is* the negative control: same geometry, same ``h``, no
field.  If the two builds agree, the patch did not install — the
``Mesh.MeshSizeFromPoints``/``…ExtendFromBoundary``/``…FromCurvature`` trio
is what makes the field bite — and that is a stop, not a pass.

The 1% band is the `GEO-23` step-2c precedent: gmsh cell counts reproduce
bit-identically on this image, so 1% is loose by measurement, not tight.

Scope, per the step: an assert on the probe's finding and nothing else — no
size field in ``src/``, no record moved, no resolution guard.

Rank-safety: gmsh builds on rank 0 only, so ``_SizeFieldPatch.fallbacks`` is
``None`` everywhere else and is broadcast before it is asserted on.  Cell
counts come from the probe's own ``attempt``, which reduces across ranks.
"""

from mpi4py import MPI

from tests.validation.probe_straight_wire_mesh_resolution import (
    EXAMPLE_DOMAIN_RADIUS,
    EXAMPLE_WIRE_LENGTH,
    FALLBACK_MARKER,
    _SizeFieldPatch,
    attempt,
)

# The rung `mag:1` and both probe legs share.
RESOLUTION = 0.008

# Prior-run references (see the module docstring for the logs).
PATCHED_CELLS_REF = 19823
CONTROL_CELLS_REF = 21830
CELL_BAND = 0.01


def _build(comm, install):
    """One `straight_wire_domain` build, with or without the size field.

    Returns (ok, cells, message, fallbacks).  `install=False` keeps the
    logger counting so the two builds are compared on the same instrument.
    """
    patch = _SizeFieldPatch(RESOLUTION, install=install)
    ok, cells, message, _elapsed = attempt(
        comm,
        EXAMPLE_WIRE_LENGTH,
        EXAMPLE_DOMAIN_RADIUS,
        RESOLUTION,
        patch=patch,
    )
    comm.Barrier()
    # Counted inside the patched `generate`, which only runs on the building
    # rank; asserting the rank-local `None` elsewhere is the trap.
    fallbacks = comm.bcast(patch.fallbacks, root=0)
    return ok, cells, message, fallbacks


def test_wire_surface_size_field_removes_the_meshing_fallback():
    comm = MPI.COMM_WORLD

    patched_ok, patched_cells, patched_message, patched_fallbacks = _build(
        comm, install=True
    )
    control_ok, control_cells, control_message, control_fallbacks = _build(
        comm, install=False
    )

    if comm.rank == 0:
        print(
            f"\nGEO-22 step 2c -- straight_wire_domain example geometry at "
            f"h = {RESOLUTION}, {comm.size} rank(s):\n"
            f"  patched  ok = {patched_ok}  cells = {patched_cells}  "
            f"fallbacks = {patched_fallbacks}  (ref {PATCHED_CELLS_REF})\n"
            f"  control  ok = {control_ok}  cells = {control_cells}  "
            f"fallbacks = {control_fallbacks}  (ref {CONTROL_CELLS_REF})"
        )

    assert patched_ok, f"patched build failed to mesh: {patched_message}"
    assert control_ok, f"control build failed to mesh: {control_message}"

    assert patched_fallbacks == 0, (
        f"the size field left {patched_fallbacks} '{FALLBACK_MARKER}' line(s) "
        f"at h = {RESOLUTION}; step 2 read 0 over all 18 rungs"
    )
    assert control_fallbacks >= 1, (
        "the unpatched control showed no triangle-collapse fallback at "
        f"h = {RESOLUTION}; step 2 read one per rung, so either the mechanism "
        "moved or the logger was not running"
    )

    assert abs(patched_cells / PATCHED_CELLS_REF - 1) <= CELL_BAND, (
        f"patched cell count {patched_cells} is outside {CELL_BAND:.0%} of the "
        f"step-2 reference {PATCHED_CELLS_REF}"
    )
    assert abs(control_cells / CONTROL_CELLS_REF - 1) <= CELL_BAND, (
        f"control cell count {control_cells} is outside {CELL_BAND:.0%} of the "
        f"mag:1 reference {CONTROL_CELLS_REF}"
    )
