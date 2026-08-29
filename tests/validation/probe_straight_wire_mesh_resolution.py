"""Localise where `MeshGenerator.straight_wire_domain` stops meshing on 0.11.

`EX-30` leg (root), 2026-08-25: `examples/magnetostatics/01_straight_wire.py`
aborts in gmsh with "Invalid boundary mesh (overlapping facets) on surface 1"
before any solve, at its own parameter set -- `wire_length = 0.3`,
`domain_radius = 0.04`, `resolution = 0.01` (source comment: "coarse,
cron-safe runtime").  The generator itself is fine: the same call meshed
38 740 / 147 235 / 383 146 cells in the next run of that slot, at the gates'
0.2 / 0.03 / {0.004, 0.0025, 0.0018}.  So the break lives somewhere between
the two parameter sets, and the known-issues entry records it as *not
diagnosed*.

This probe walks the one axis the example calls out as deliberately chosen
for runtime -- `resolution` -- holding the example's own geometry fixed, and
then walks the geometry back to the gate's at the example's resolution.  It
reports per-case success or the gmsh message, and never asserts: which side
of the line moves (the example's parameters, or the generator's robustness)
is the review's ruling, not this probe's.

Nothing here is imported by a gate, and no record is restated.

**Run this at `-n 1`, deliberately.** `straight_wire_domain` builds its gmsh
model inside `if comm.rank == rank:` and only the other ranks' `_model_to_mesh`
call is collective, so a gmsh exception on rank 0 leaves every other rank
blocked -- the multi-rank run deadlocks instead of reporting.  Nothing measured
here is rank-dependent: gmsh's boundary reconstruction is serial on rank 0
whatever the width, and the cell counts are the same mesh.

    mpiexec -n 1 python3 -u tests/validation/probe_straight_wire_mesh_resolution.py

**Leg C (`GEO-22` step 1, 2026-08-28).**  Legs A and B left the floor
localised but *unbisected*: 0.008 meshes, 0.010 fails, nothing in between was
tried, so no guard constant could be written without guessing.  Leg C closes
that by sweeping the whole open interval `[0.008, 0.010]` on a uniform 2.5e-4
grid -- nine rungs -- on **both** geometries.  A uniform sweep rather than a
true bisection deliberately: at 0.3 s per failing rung and ~2.6 s per meshing
one the full grid costs about what three bisection steps would, and it is the
only form of the measurement that can *see* a non-monotone floor (a failing
rung between two meshing ones), which `GEO-22` names as a stop condition.

    mpiexec -n 1 python3 -u tests/validation/probe_straight_wire_mesh_resolution.py bisect

**Leg D (`GEO-22` step 2, 2026-08-29).**  Step 1's second finding was that
*every* rung in `[0.008, 0.010]` -- the meshing ones included -- falls back
`Frontal-Delaunay` -> `MeshAdapt` on the wire surface after gmsh reports "N
triangles are equivalent", which localises the mechanism to the wire-surface
mesh.  The 08-28 10:30 review ruled that the one candidate which could
actually *fix* that is an explicit size field on the wire cylinder in place of
the global `resolution`, and commissioned this leg to measure it -- no `src/`
change, no record moved, no guard.  Leg D re-runs leg C's nine rungs on both
geometries with a gmsh `Distance`/`Threshold` field anchored on the
`wire_surface` physical group, and reports per rung the count of "triangles
are equivalent" lines alongside OK/FAIL.  The hypothesis predicts 0 fallbacks
and 18/18 OK.

The size field is installed without touching `MeshGenerator`: leg D patches
`gmsh.model.mesh.generate` for the duration of one call, so the field is added
to the finished model just before meshing starts and the generator's own
`setSize(points, resolution)` is switched off via `Mesh.MeshSizeFromPoints`.
Everything upstream -- geometry, fragment, physical groups, the collective
raise path, `_model_to_mesh` -- is the shipped code.

    mpiexec -n 1 python3 -u tests/validation/probe_straight_wire_mesh_resolution.py sizefield

**One leg per process, deliberately.**  `GEO-23` finding F is that in-process
meshing ladders can read gmsh contamination rather than geometry.  Leg C's own
answer to that is empirical -- step 1 ran it twice and the 18 cells reproduced
bit-identically -- and leg D keeps the same in-process shape so that its table
is comparable rung for rung.  What is *not* shared is the process: leg C and
leg D are separate command-line modes and must be run as two commands, so
leg C's re-run sees exactly the process history step 1 gave it and is a true
control.  (The `GEO-22` step 2 ruling describes leg C as forking per rung; it
does not, and never did -- the reproducibility evidence is the repeat run.)
"""

import os
import sys
import time

import gmsh
from mpi4py import MPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.fem_em_solver.io.mesh import MeshGenerator  # noqa: E402

# The example's own geometry (`01_straight_wire.py:118`-`121`).
EXAMPLE_WIRE_LENGTH = 0.3
EXAMPLE_DOMAIN_RADIUS = 0.04
EXAMPLE_WIRE_RADIUS = 0.003
EXAMPLE_RESOLUTION = 0.01

# The gate's geometry (`test_straight_wire.py:62`-`65`), for the second leg.
GATE_WIRE_LENGTH = 0.20
GATE_DOMAIN_RADIUS = 0.03

# Leg A: the example's geometry, resolution swept from its own value down
# towards the coarsest gated rung (0.004).  Coarse first, so the cheap cases
# report before the expensive ones.
RESOLUTION_LADDER = [0.01, 0.008, 0.006, 0.005, 0.004]

# Leg B: the example's resolution, geometry stepped to the gate's.  If leg A
# shows resolution alone explains it, this leg costs ~1 s each and settles
# whether the box size participates.
GEOMETRY_LADDER = [
    (EXAMPLE_WIRE_LENGTH, EXAMPLE_DOMAIN_RADIUS),
    (EXAMPLE_WIRE_LENGTH, GATE_DOMAIN_RADIUS),
    (GATE_WIRE_LENGTH, EXAMPLE_DOMAIN_RADIUS),
    (GATE_WIRE_LENGTH, GATE_DOMAIN_RADIUS),
]


# Leg C: the open interval legs A/B bracketed, on a uniform 2.5e-4 grid --
# 0.00800, 0.00825, ... 0.01000.  Built with integer arithmetic so the rungs
# are exact multiples of 2.5e-4 and reproduce bit-for-bit between runs.
BISECT_GRID = [round(80 + 2.5 * i, 4) / 10000.0 for i in range(9)]

# Both geometries get the same grid: `GEO-22` step 1 must say whether the
# floor is geometry-dependent, and leg B already showed h = 0.01 fails on all
# four (L, R) pairs.  These are the two that matter -- the example's and the
# gate's.
BISECT_GEOMETRIES = [
    ("example", EXAMPLE_WIRE_LENGTH, EXAMPLE_DOMAIN_RADIUS),
    ("gate", GATE_WIRE_LENGTH, GATE_DOMAIN_RADIUS),
]


# Leg D: the wire-surface size field.  `SizeMin` on the wire, growing to the
# rung's own `resolution` by `DIST_MAX`, so away from the wire leg D meshes at
# exactly leg C's size and the only difference between the two tables is the
# wire surface -- which is where step 1 localised the fallback.
#
# `SizeMin = wire_radius` is chosen against the mechanism, not tuned: the
# fallback is gmsh collapsing triangles on a cylinder of circumference
# 2*pi*0.003 = 0.0188 m meshed at h = 0.008-0.010, i.e. two points around the
# circle.  One element per wire radius puts ~6 there.  `DIST_MAX = 2*R` keeps
# the refined shell thin enough that the cell count stays in leg C's decade.
FIELD_SIZE_MIN = EXAMPLE_WIRE_RADIUS
FIELD_DIST_MIN = EXAMPLE_WIRE_RADIUS
FIELD_DIST_MAX = 2 * EXAMPLE_WIRE_RADIUS

# The generator's own physical group for the wire lateral+cap surfaces
# (`mesh.py:332`-`334`: dim 2, tag 2, name "wire_surface").
WIRE_SURFACE_PHYSICAL_TAG = 2

FALLBACK_MARKER = "triangles are equivalent"


class _SizeFieldPatch:
    """Run one `straight_wire_domain` call with a wire-surface size field.

    Patches `gmsh.model.mesh.generate` rather than `MeshGenerator`: the wrapper
    fires after the model is built and its physical groups are set, adds the
    `Distance`/`Threshold` pair on the wire surface, disables the point sizes
    the generator wrote from `resolution`, and then calls the real `generate`.
    `src/` is untouched, which is this step's scope.

    Also counts gmsh's "N triangles are equivalent" lines over that same call
    (via `gmsh.logger`), which is leg D's anchor.  `install=False` gives the
    counting without the field, for a same-process comparison.
    """

    def __init__(self, resolution, install=True):
        self.resolution = resolution
        self.install = install
        self.fallbacks = None
        self._original = None

    def __enter__(self):
        self._original = gmsh.model.mesh.generate
        gmsh.model.mesh.generate = self._generate
        return self

    def __exit__(self, *_exc):
        gmsh.model.mesh.generate = self._original
        return False

    def _generate(self, *args, **kwargs):
        if self.install:
            surfaces = gmsh.model.getEntitiesForPhysicalGroup(
                2, WIRE_SURFACE_PHYSICAL_TAG
            )
            distance = gmsh.model.mesh.field.add("Distance")
            gmsh.model.mesh.field.setNumbers(
                distance, "SurfacesList", [int(s) for s in surfaces]
            )
            gmsh.model.mesh.field.setNumber(distance, "Sampling", 100)
            threshold = gmsh.model.mesh.field.add("Threshold")
            gmsh.model.mesh.field.setNumber(threshold, "InField", distance)
            gmsh.model.mesh.field.setNumber(threshold, "SizeMin", FIELD_SIZE_MIN)
            gmsh.model.mesh.field.setNumber(threshold, "SizeMax", self.resolution)
            gmsh.model.mesh.field.setNumber(threshold, "DistMin", FIELD_DIST_MIN)
            gmsh.model.mesh.field.setNumber(threshold, "DistMax", FIELD_DIST_MAX)
            gmsh.model.mesh.field.setAsBackgroundMesh(threshold)
            # Without these the generator's `setSize(points, resolution)` and
            # gmsh's boundary-extension still drive the wire surface and the
            # field would be advisory only.
            gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
            gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
            gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
        gmsh.logger.start()
        try:
            return self._original(*args, **kwargs)
        finally:
            # Read before the caller's `gmsh.finalize()` on the failure path.
            lines = gmsh.logger.get()
            gmsh.logger.stop()
            self.fallbacks = sum(1 for line in lines if FALLBACK_MARKER in line)


def attempt(comm, wire_length, domain_radius, resolution, patch=None):
    """Mesh one case.  Returns (ok, cells_or_None, message, seconds).

    The cell count is reduced across ranks -- `mesh.topology.index_map(3).size_local`
    is rank-local and a rank-local count is not a number worth printing.

    `patch` is an unentered `_SizeFieldPatch` (leg D) or None (legs A/B/C).
    """
    t0 = time.time()
    if patch is not None:
        with patch:
            return _attempt_inner(comm, wire_length, domain_radius, resolution, t0)
    return _attempt_inner(comm, wire_length, domain_radius, resolution, t0)


def _attempt_inner(comm, wire_length, domain_radius, resolution, t0):
    try:
        mesh, _cell_tags, _facet_tags = MeshGenerator.straight_wire_domain(
            wire_length=wire_length,
            wire_radius=EXAMPLE_WIRE_RADIUS,
            domain_radius=domain_radius,
            resolution=resolution,
            comm=comm,
        )
    except Exception as exc:  # gmsh raises a bare Exception with its own text
        elapsed = time.time() - t0
        # `straight_wire_domain` only reaches its `gmsh.finalize()` on the
        # success path, so a failed case would otherwise leave the library
        # initialised and leak model state into the next one.
        try:
            gmsh.finalize()
        except Exception:
            pass
        return False, None, str(exc).strip().splitlines()[-1], elapsed
    local = mesh.topology.index_map(mesh.topology.dim).size_local
    cells = comm.allreduce(local, op=MPI.SUM)
    return True, cells, "", time.time() - t0


def bisect_main(comm):
    """Leg C -- sweep [0.008, 0.010] at 2.5e-4 on both geometries."""
    rank0 = comm.rank == 0
    if rank0:
        print("straight_wire_domain: bisecting the coarse-resolution floor")
        print(f"  grid {BISECT_GRID[0]} .. {BISECT_GRID[-1]} at 2.5e-4, "
              f"fixed wire_radius = {EXAMPLE_WIRE_RADIUS} m; "
              f"{comm.size} rank(s)\n")

    summary = []
    for name, wire_length, domain_radius in BISECT_GEOMETRIES:
        if rank0:
            print(f"Leg C/{name} -- L = {wire_length}, R = {domain_radius}:")
        h_ok, h_fail, cells_at_h_ok = None, None, None
        for resolution in BISECT_GRID:
            ok, cells, message, elapsed = attempt(
                comm, wire_length, domain_radius, resolution
            )
            comm.Barrier()
            # `h_ok` is the *coarsest* meshing rung and `h_fail` the *finest*
            # failing one; the grid runs fine-to-coarse, so each keeps its
            # last observation of the respective kind.
            if ok:
                h_ok, cells_at_h_ok = resolution, cells
            else:
                if h_fail is None:
                    h_fail = resolution
            if rank0:
                if ok:
                    print(f"  h = {resolution:<8.5f} OK    {cells:>8d} cells "
                          f"({elapsed:.1f} s)")
                else:
                    print(f"  h = {resolution:<8.5f} FAIL  {message} "
                          f"({elapsed:.1f} s)")
        summary.append((name, h_ok, cells_at_h_ok, h_fail))
        if rank0:
            print("")

    if rank0:
        print("Summary -- coarsest meshing rung / finest failing rung:")
        for name, h_ok, cells_at_h_ok, h_fail in summary:
            print(f"  {name:<8s} h_ok = {h_ok}  ({cells_at_h_ok} cells)   "
                  f"h_fail = {h_fail}")
        # Monotone means: every rung at or below h_ok meshed and every rung
        # above it failed.  A violation is `GEO-22`'s stop condition, so it is
        # printed as such rather than inferred by the reader.
        for name, h_ok, _cells, h_fail in summary:
            if h_ok is not None and h_fail is not None and h_fail < h_ok:
                print(f"  {name}: NON-MONOTONE -- a failing rung "
                      f"({h_fail}) lies below a meshing one ({h_ok}).")
        print("\nMeasurement only -- no assertion, nothing re-recorded.")


def sizefield_main(comm):
    """Leg D -- leg C's grid again, with a wire-surface size field."""
    rank0 = comm.rank == 0
    if rank0:
        print("straight_wire_domain: leg C's grid with a wire-surface size field")
        print(f"  grid {BISECT_GRID[0]} .. {BISECT_GRID[-1]} at 2.5e-4, "
              f"fixed wire_radius = {EXAMPLE_WIRE_RADIUS} m; "
              f"{comm.size} rank(s)")
        print(f"  Distance/Threshold on physical group (2, "
              f"{WIRE_SURFACE_PHYSICAL_TAG}): SizeMin = {FIELD_SIZE_MIN}, "
              f"SizeMax = the rung's own h, DistMin = {FIELD_DIST_MIN}, "
              f"DistMax = {FIELD_DIST_MAX}\n")

    # `sizefield <h>` runs the single named rung on both geometries -- the
    # cost probe the compute budget (§5.1) asks for before an unmeasured
    # 18-cell sweep.
    grid = BISECT_GRID
    if len(sys.argv) > 2:
        grid = [float(sys.argv[2])]
        if rank0:
            print(f"  COST PROBE: single rung {grid[0]}, not the full grid\n")

    summary = []
    for name, wire_length, domain_radius in BISECT_GEOMETRIES:
        if rank0:
            print(f"Leg D/{name} -- L = {wire_length}, R = {domain_radius}:")
        n_ok, n_fallback_cells = 0, 0
        for resolution in grid:
            patch = _SizeFieldPatch(resolution)
            ok, cells, message, elapsed = attempt(
                comm, wire_length, domain_radius, resolution, patch=patch
            )
            comm.Barrier()
            fallbacks = patch.fallbacks
            if ok:
                n_ok += 1
            if fallbacks:
                n_fallback_cells += 1
            if rank0:
                verdict = (f"OK    {cells:>8d} cells" if ok
                           else f"FAIL  {message}")
                print(f"  h = {resolution:<8.5f} {verdict}   "
                      f"fallbacks = {fallbacks}  ({elapsed:.1f} s)")
        summary.append((name, n_ok, n_fallback_cells))
        if rank0:
            print("")

    if rank0:
        total_ok = sum(n_ok for _n, n_ok, _f in summary)
        total_fallback = sum(f for _n, _o, f in summary)
        n_cells = len(BISECT_GEOMETRIES) * len(grid)
        print("Summary -- the two numbers `GEO-22` step 2 asked for:")
        for name, n_ok, n_fallback in summary:
            print(f"  {name:<8s} OK {n_ok}/{len(grid)}   "
                  f"rungs with >= 1 fallback: {n_fallback}/{len(grid)}")
        print(f"  total    OK {total_ok}/{n_cells}   "
              f"rungs with >= 1 fallback: {total_fallback}/{n_cells}")
        # The pre-registered hypothesis, printed as a verdict rather than left
        # to the reader: step 1 read >= 1 fallback in all 18 cells and 7 FAILs.
        if total_ok == n_cells and total_fallback == 0:
            print(f"  VERDICT: hypothesis CONFIRMED -- {n_cells}/{n_cells} OK, "
                  "0 fallbacks.")
        else:
            print("  VERDICT: hypothesis REFUTED -- the size field does not "
                  "give 18/18 OK with 0 fallbacks.")
        print("\nMeasurement only -- no assertion, nothing re-recorded.")


def main():
    comm = MPI.COMM_WORLD
    rank0 = comm.rank == 0

    if len(sys.argv) > 1 and sys.argv[1] == "bisect":
        bisect_main(comm)
        return

    if len(sys.argv) > 1 and sys.argv[1] == "sizefield":
        sizefield_main(comm)
        return

    if rank0:
        print("straight_wire_domain: where does the 0.11 image stop meshing?")
        print(
            f"  fixed wire_radius = {EXAMPLE_WIRE_RADIUS} m; "
            f"{comm.size} rank(s)\n"
        )
        print("Leg A -- the example's geometry "
              f"(L = {EXAMPLE_WIRE_LENGTH}, R = {EXAMPLE_DOMAIN_RADIUS}), "
              "resolution swept:")

    for resolution in RESOLUTION_LADDER:
        ok, cells, message, elapsed = attempt(
            comm, EXAMPLE_WIRE_LENGTH, EXAMPLE_DOMAIN_RADIUS, resolution
        )
        comm.Barrier()
        if rank0:
            if ok:
                print(f"  h = {resolution:<7.4f} OK    {cells:>8d} cells "
                      f"({elapsed:.1f} s)")
            else:
                print(f"  h = {resolution:<7.4f} FAIL  {message} "
                      f"({elapsed:.1f} s)")

    if rank0:
        print(f"\nLeg B -- the example's resolution "
              f"(h = {EXAMPLE_RESOLUTION}), geometry stepped to the gate's:")

    for wire_length, domain_radius in GEOMETRY_LADDER:
        ok, cells, message, elapsed = attempt(
            comm, wire_length, domain_radius, EXAMPLE_RESOLUTION
        )
        comm.Barrier()
        if rank0:
            label = f"L = {wire_length:<5.2f} R = {domain_radius:<5.3f}"
            if ok:
                print(f"  {label} OK    {cells:>8d} cells ({elapsed:.1f} s)")
            else:
                print(f"  {label} FAIL  {message} ({elapsed:.1f} s)")

    if rank0:
        print("\nMeasurement only -- no assertion, nothing re-recorded.")


if __name__ == "__main__":
    main()
