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
  meshed/CAD >= ``CAD_MASS_GATE`` (0.95). On record: **0.966977** (0.11 image;
  0.967019 on 0.7.2).
* **control**, the coarse-graded ``BASELINE_CONTROL_RESOLUTION`` = 4.8 mm:
  asserted *to fail* the same 0.95 — the `EX-18`/`EX-20` inverted-assertion
  pattern. On record: **0.846150**, i.e. a separation of **0.120826** below the
  graded rung, so the gate discriminates rather than merely being cleared.

**What this example claims, and what it stopped claiming on 2026-08-26.** The
control was a single global ``setSize = 0.015`` with *no* conductor grading at
all, at **0.740335**, so the comparison was graded-vs-ungraded. On the 0.11
image (dolfinx 0.11 / gmsh 4.15.2) that ungraded mesh stopped building — gmsh
aborts with "Invalid boundary mesh (overlapping facets)" before the graded rung
ever runs — and this example, like the gate it imports, was red and
non-executing from the 0.11 merge until `GEO-21` disposed of it. Every meshable
replacement is itself graded, so what is demonstrated now is **fine vs coarse
conductor grading**: still quantitative, still monotone, but no longer evidence
that grading is *required*. That stronger claim closed on 0.7.2 (`GEO-15`,
2026-08-16) and stays closed there. The control's sizing is imported from the
gate module, whose comment carries the six-rung probe table it was chosen from.

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
Both rungs are exported, ``_baseline_`` (the coarse-graded control; the stem is
kept for continuity with the guide and the on-disk record) and ``_graded_``, so
the two can be opened side by side — that comparison is the point of the
example.

Measured 2026-08-26 at ``-n 2`` on the 0.11 image (`GEO-21` step 2): control
33 185 cells / 6.43 s mesh, graded 98 666 cells / 18.32 s mesh; meshed/CAD
**0.846150 -> 0.966977**, separation **0.120826**; 27.7 s total including both
exports (``20260826T093403Z_GEO-21-step2-mesh3.log``, Status 0). Superseded
record, 2026-08-16 on 0.7.2 with the
ungraded control: 48 245 -> 98 474 cells, **0.740335 -> 0.967019**, separation
**0.226685**, 26 s total including both exports.
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
    BASELINE_CONTROL_RESOLUTION,
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
            f"h_c={GRADED_H_C:.4e} m (= 0.4 x ring_minor_radius, the GEO-8 rule);"
            f"\n[mesh]     coarse-graded control h_c={BASELINE_CONTROL_RESOLUTION:.4e} m"
            f"\n[gate]     graded meshed/CAD >= {CAD_MASS_GATE}; control asserted to FAIL it"
            "\n[claim]    fine vs coarse grading (GEO-21 step 2, 2026-08-26) — the"
            "\n[claim]    graded-vs-ungraded claim closed on 0.7.2 and stays there",
            flush=True,
        )

    # ---- rung 1: the negative control, printed first ----------------------
    baseline = _rung(BASELINE_CONTROL_RESOLUTION, comm)
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
            ("control (coarse graded)", baseline, baseline_ratio),
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
            f"\n[GEO-15] control: coarse-graded {baseline_ratio:.6f} < {CAD_MASS_GATE} "
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
        f"`GEO-15` gate (on record: 0.966977). Record the measured frontier in the "
        "EX-21 entry rather than moving the gate."
    )

    # ---- the negative control: the same measurement must FAIL --------------
    assert baseline_ratio < CAD_MASS_GATE - CONTROL_SEPARATION, (
        f"coarse-graded control (h_c={BASELINE_CONTROL_RESOLUTION:.4e} m) keeps "
        f"{baseline_ratio:.6f} of the CAD mass, "
        f"within {CONTROL_SEPARATION} of the {CAD_MASS_GATE} gate (on record: "
        "0.846150). The control no longer separates, so this example would pass "
        "even if grading did nothing — the premise needs re-examining."
    )
    assert graded_ratio > baseline_ratio, (
        f"refining the conductor grading did not improve fidelity: "
        f"{graded_ratio:.6f} vs {baseline_ratio:.6f} at the coarser conductor sizing"
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
            "\n           coarsely faceted in the control and round in the graded rung"
            "\n           (both are graded; the control's shell is 3x coarser)."
            f"\n\nAll identities hold. Total elapsed {time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
