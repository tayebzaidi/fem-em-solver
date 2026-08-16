"""Example (`EX-21`): graded conductor sizing on the birdcage port fixture.

The **first birdcage example of any kind** in this repo, and the example angle
`GEO-15` owes: that chunk gated *graded conductor sizing* — a gmsh
Distance→Threshold background field that refines only on and near the
conductor surfaces — and nothing you can open in ParaView showed it. This
script builds the same fixture twice, once each way, and asserts the
difference.

**The quantity.** Not "does it look finer": the fraction of the conductor's
**CAD (occ) mass** that survives into the mesh. The CAD mass counts every
fragment piece exactly once, so unlike the analytic ring+leg sum (which
double-counts the eight leg∩ring junctions) it tends to 1 under refinement and
the deficit is *resolution alone*. `GEO-15` step 1's gate is therefore a real
number with a real denominator:

* **graded** conductor, ``h_c = 0.4 x ring_minor_radius`` = 1.6 mm:
  meshed/CAD >= ``CAD_MASS_GATE`` (0.95). On record from `GEO-15`: **0.9670**.
* **baseline** single global ``setSize = 0.015``: asserted *to fail* the same
  0.95 — the `EX-18`/`EX-20` inverted-assertion pattern. On record:
  **0.740335**, i.e. a separation of **0.2267** below the gate, so the gate
  discriminates rather than merely being cleared.

Every constant here — the fixture parameters, the rung ladder, the gate, the
`GEO-9` identity checks — is **imported** from the `GEO-15` module that gated
them (`tests/mesh/test_birdcage_conductor_sizing.py`, the `ANS-1` rule);
nothing is restated, so this example cannot drift from the gate it
demonstrates.

**Also re-asserted, unmoved:** the `GEO-9` box-partition identities on *both*
rungs — total mesh volume / analytic air box = 1 to ``1e-9``, tagged volumes
summing to the total to ``1e-9``, and each of the four port boxes meshed to
``dx*dy*dz`` to ``1e-9``. Grading changes element sizes, not geometry, so an
identity that moves is a defect in the size field (a piece lost its physical
group, or a region got meshed twice), not a resolution effect. The CAD mass
itself is checked identical across the two rungs to ``1e-12`` for the same
reason: if the denominator moved, no ratio above means anything.

**Mesh only — no solve, no port claim.** The birdcage has no port model yet
(`PORT-9` is ⬜/🟡, PROJECT_PLAN.md §2); this script needs only the real
DolfinX build.

Run it through the example runner::

    ./run_examples.sh -e mesh:3

Output lands in ``examples/meshing/paraview_output/``: open
``birdcage_graded_conductors_combined.xdmf`` and threshold on ``CellTags``
(1 = conductor, 2 = air, 3 = phantom, 101-104 = the four leg port boxes).
Both rungs are exported, ``_baseline_`` and ``_graded_``, so the two can be
opened side by side — that comparison is the point of the example.

Measured 2026-08-16 at ``-n 2``: baseline 48 245 cells / 6.1-6.3 s mesh,
graded 98 474 cells / 16.7 s mesh; meshed/CAD **0.740335 -> 0.967019**,
separation **0.226685**; 26 s total including both exports. Cell counts and
ratios reproduced bit-identically across two runs; only the wall times move.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from mpi4py import MPI

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH, so the repo root goes on
# sys.path: the gate, the ladder and the fixture parameters live in the
# `GEO-15` test module and are imported, never restated (`ANS-1`).
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)

from tests.mesh.helpers import global_cell_tag_set  # noqa: E402
from tests.mesh.test_birdcage_conductor_sizing import (  # noqa: E402
    CAD_MASS_GATE,
    CONDUCTOR_RUNGS,
    _check_geo9_identities,
)
from tests.mesh.test_birdcage_port_tags import (  # noqa: E402
    AIR_PADDING,
    COIL_LENGTH,
    LEG_COUNT,
    LEG_SPACING,
    LEG_WIDTH,
    PHANTOM_HEIGHT,
    PHANTOM_RADIUS,
    PORT_BOX_SIZE,
    RESOLUTION,
    RING_MINOR_RADIUS,
    RING_RADIUS,
)
from tests.mesh.test_coil_phantom_conforming import _tag_volume, _total_volume  # noqa: E402

# The finest `GEO-15` rung — the one that carries the gate (0.4 x the ring
# minor radius, the `GEO-8` rule). The coarser rung of the ladder exists in
# the test to show monotonicity; an example needs the two ends only.
GRADED_H_C = CONDUCTOR_RUNGS[-1]

# `test_birdcage_port_tags.CELL_TAG_NAMES`, extended with the four port boxes
# the birdcage fixture tags 101..104.
CELL_TAG_NAMES = {1: "conductor", 2: "air", 3: "phantom"}

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "birdcage_graded_conductors"

# The example asserts the *inverted* control, so the separation it needs is
# the same one the `GEO-15` test enforces: a baseline sitting at 0.949 would
# clear "fails the gate" while saying nothing. Kept at the test's margin.
CONTROL_SEPARATION = 0.05


def _rung(conductor_resolution, comm):
    """One rung: mesh, tags, CAD mass, tagged volumes, wall time.

    Mirrors ``tests.mesh.test_birdcage_conductor_sizing._mesh`` but keeps the
    mesh and cell tags so the rung can be exported for ParaView — that helper
    discards them, and re-meshing purely to export would double the cost of
    the example.
    """
    started = time.perf_counter()
    mesh, cell_tags, _, diagnostics = MeshGenerator.birdcage_port_domain(
        leg_count=LEG_COUNT,
        ring_radius=RING_RADIUS,
        leg_width=LEG_WIDTH,
        leg_spacing=LEG_SPACING,
        coil_length=COIL_LENGTH,
        ring_minor_radius=RING_MINOR_RADIUS,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        port_box_size=PORT_BOX_SIZE,
        air_padding=AIR_PADDING,
        resolution=RESOLUTION,
        conductor_resolution=conductor_resolution,
        comm=comm,
        return_diagnostics=True,
    )
    elapsed = time.perf_counter() - started

    port_tags = [100 + i for i in range(1, LEG_COUNT + 1)]
    all_tags = [1, 2, 3, *port_tags]
    # `cell_tags.values` is rank-local; at -n 2 a rank can legitimately own no
    # cells of a small port box (`GEO-9` step 2b paid for this once already).
    assert global_cell_tag_set(mesh, cell_tags) == set(all_tags), (
        f"h_c={conductor_resolution}: global cell tag set is "
        f"{sorted(global_cell_tag_set(mesh, cell_tags))}, expected {all_tags}"
    )

    return {
        "h_c": conductor_resolution,
        "mesh": mesh,
        "cell_tags": cell_tags,
        "n_cells": mesh.topology.index_map(3).size_global,
        "wall_time_s": elapsed,
        "mesh_wall_time_s": diagnostics["mesh_wall_time_s"],
        "cad_mass": diagnostics["cad_mass_by_group"],
        "v": {tag: _tag_volume(mesh, cell_tags, tag, comm) for tag in all_tags},
        "v_total": _total_volume(mesh, comm),
        "port_tags": port_tags,
        "all_tags": all_tags,
    }


def _write_paraview(rung, label, comm):
    """Mesh + cell tags of one rung, as a DG0 ``CellTags`` array."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_{label}_combined",
        rung["mesh"],
        rung["cell_tags"],
        {},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if comm.rank == 0:
        print("=" * 72)
        print("EX-21 — birdcage fixture: graded vs global conductor sizing")
        print("=" * 72)
        print(
            f"\n[geometry] leg_count={LEG_COUNT}  ring_radius={RING_RADIUS} m  "
            f"ring_minor_radius={RING_MINOR_RADIUS} m  leg_width={LEG_WIDTH} m"
            f"\n[geometry] coil_length={COIL_LENGTH} m  leg_spacing={LEG_SPACING} m  "
            f"phantom {PHANTOM_RADIUS} x {PHANTOM_HEIGHT} m  air_padding={AIR_PADDING} m"
            f"\n[mesh]     global resolution={RESOLUTION} m; graded rung "
            f"h_c={GRADED_H_C:.4e} m (= 0.4 x ring_minor_radius, the GEO-8 rule)"
            f"\n[gate]     graded meshed/CAD >= {CAD_MASS_GATE}; baseline asserted to FAIL it",
            flush=True,
        )

    # ---- rung 1: the negative control, printed first ----------------------
    baseline = _rung(None, comm)
    _check_geo9_identities(baseline, comm)

    # ---- rung 2: the graded rung that carries the gate --------------------
    graded = _rung(GRADED_H_C, comm)
    _check_geo9_identities(graded, comm)

    cad_conductor = baseline["cad_mass"]["conductor"]
    baseline_ratio = baseline["v"][1] / cad_conductor
    graded_ratio = graded["v"][1] / cad_conductor

    if comm.rank == 0:
        print(
            f"\n[GEO-15] conductor CAD (occ) mass = {cad_conductor:.9e} m^3 "
            "(the denominator: every fragment piece counted once)"
        )
        for label, rung, ratio in (
            ("baseline (global setSize)", baseline, baseline_ratio),
            ("graded  (Distance/Threshold)", graded, graded_ratio),
        ):
            h_c = "global" if rung["h_c"] is None else f"{rung['h_c']:.4e}"
            print(
                f"  {label:<28s} h_c={h_c:>10s}"
                f"  cells={rung['n_cells']:>8d}  meshed/CAD={ratio:.6f}"
                f"  mesh={rung['mesh_wall_time_s']:6.2f} s  rung={rung['wall_time_s']:6.2f} s"
            )
        print(
            f"\n[GEO-15] gate  : graded {graded_ratio:.6f} >= {CAD_MASS_GATE}"
            f"\n[GEO-15] control: baseline {baseline_ratio:.6f} < {CAD_MASS_GATE} "
            "(inverted assertion — the control must FAIL the gate)"
            f"\n[GEO-15] separation = {graded_ratio - baseline_ratio:.6f} "
            "between the two rungs on the same denominator",
            flush=True,
        )

    # The CAD mass is a property of the CAD, not of the mesh: if the size field
    # moved the denominator, neither ratio means anything.
    assert abs(graded["cad_mass"]["conductor"] / cad_conductor - 1.0) < 1e-12, (
        f"graded rung reports conductor CAD mass {graded['cad_mass']['conductor']:.9e} "
        f"m^3 vs baseline {cad_conductor:.9e} m^3; the size field must not change "
        "the geometry"
    )

    # ---- the gate ---------------------------------------------------------
    assert graded_ratio >= CAD_MASS_GATE, (
        f"graded conductor keeps only {graded_ratio:.6f} of its CAD mass at "
        f"h_c={GRADED_H_C:.4e} m ({graded['n_cells']} cells, "
        f"{graded['mesh_wall_time_s']:.2f} s mesh) — below the {CAD_MASS_GATE} "
        f"`GEO-15` gate (on record: 0.9670). Record the measured frontier in the "
        "EX-21 entry rather than moving the gate."
    )

    # ---- the negative control: the same measurement must FAIL --------------
    assert baseline_ratio < CAD_MASS_GATE - CONTROL_SEPARATION, (
        f"baseline global-setSize mesh keeps {baseline_ratio:.6f} of the CAD mass, "
        f"within {CONTROL_SEPARATION} of the {CAD_MASS_GATE} gate (on record: "
        "0.740335). The control no longer separates, so this example would pass "
        "even if grading did nothing — the premise needs re-examining."
    )
    assert graded_ratio > baseline_ratio, (
        f"grading did not improve conductor fidelity: {graded_ratio:.6f} vs "
        f"{baseline_ratio:.6f} at the coarser global sizing"
    )

    # ---- ParaView ---------------------------------------------------------
    written = {
        "baseline": _write_paraview(baseline, "baseline", comm),
        "graded": _write_paraview(graded, "graded", comm),
    }
    if comm.rank == 0:
        print("\n[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<9s} {path}")
        print(
            "\n[paraview] threshold `CellTags` in each file "
            f"({', '.join(f'{t} = {n}' for t, n in CELL_TAG_NAMES.items())}, "
            "101-104 = the four leg port boxes);"
            "\n           open both side by side — the ring and leg surfaces are"
            "\n           faceted in the baseline and round in the graded rung."
            f"\n\nAll identities hold. Total elapsed {time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
