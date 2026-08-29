"""Example (`EX-35`): the production high-pass birdcage — 16 legs, 32 ring ports.

Three birdcage-port examples exist and none of them shows the topology the §10
32-port directive actually asks for:

* `EX-28` (`mesh:6`) cuts the **legs** at four legs — the low-pass drive element;
* `EX-31` (`mesh:7`) cuts the **end rings** at four legs — the high-pass element,
  but at a leg count where every gap centre folds onto one azimuth class;
* `EX-33` (`mesh:8`) reaches the production leg count of sixteen, but with
  **leg** gaps.

This example is the missing corner: the high-pass cut (**both end rings**) at
the production leg count (**sixteen legs**), so ``2 x 16 = 32`` ring ports on
one mesh — the layout `GEO-20` step 2 gated on 2026-08-29 and that until now
lived only inside `tests/mesh/test_birdcage_ring_gaps_scaleup.py`.

**What is different at sixteen ring gaps, and it is not just "more".** The ring
gap centres sit at ``phi = 2*pi*j/N + pi/N`` — 11.25 + 22.5*j degrees at sixteen
legs — so *none* of the 32 sheets stands in a coordinate plane, and no global
coordinate is constant on any of them (a ring sheet is radial: its normal is
azimuthal). Every planarity and extent reading therefore has to be taken in each
port's **own** ring frame, which is what `_ring_gap_frame` provides and what a
four-leg fixture cannot exercise. The terminal *equality* half is read per
azimuth class, and the fold predicts **four** classes here (11.25 / 33.75 /
56.25 / 78.75 deg) where the four-leg build gives **one** — the structural count
this example prints as its centrepiece table.

**The legs are UNCUT on this rung: 32 sheets, not 48.** The high-pass layout
drives the ring gaps; the sixteen leg boxes are floating air blocks with no
terminal and nothing to split, and that asymmetry is asserted rather than
assumed (the cell-tag set carries ``100+i`` alone for a leg and both ``100+i``
and ``200+i`` for a ring port). The 48-sheet dual-family build — both gap
families switched on at once, as `EX-31` does at four legs — **has never been
meshed at sixteen legs** in this repo, and is not built here.

**It asserts, it does not merely render.** The identity family is asserted by
the gate module's own ``_assert_ring_identity_family`` on *this run's own mesh*
(the `ANS-1` rule): the `GEO-9` tagged-volume partition and the analytic air
box, every port solid at its analytic wedge volume and every sheet at ``w^2`` to
``EXACT``, the C32 spread and the top/bottom ring mirror under ``SYMMETRY``, the
terminals inside the inscribed band and equal per azimuth class (intra
``TERMINAL_INTRA_CLASS_BAND``, inter ceiling ``TERMINAL_INTER_CLASS_CEILING``),
the ring arcs against Pappus, the graded conductor against its own CAD mass.
Nothing is restated, so this example cannot drift from the gate it demonstrates.

**Negative control: the same code path at four legs returns ONE azimuth class**
and reproduces `GEO-20` step 1's cell-count and terminal-ratio records inside
their imported bands. If the class partition were reading measured areas rather
than the mesh's own symmetry, the four-leg build would not collapse.

**Phase 6 cost rung, printed never asserted.** Cells and mesh wall time for
4 -> 16 legs come out of the same run on the same box, so the ratio is a
measurement rather than a comparison across machines.

**Mesh only — no solve, no port model, no drive, no impedance, no resonance and
no F-human claim at any leg count.** A gapped birdcage without lumped elements
cannot resonate; a high-pass *layout* is not a high-pass *circuit*. Nothing in
this repo solves at sixteen legs, and `PORT-9` is 🟡 (PROJECT_PLAN.md §2). Real
DolfinX build.

Run it through the example runner::

    ./run_examples.sh -e mesh:9 -n 2 -t 400

Output lands in ``examples/meshing/paraview_output/``: open
``meshing_09_birdcage_sixteen_ring_gaps_combined.xdmf`` and threshold on
``CellTags`` (1 = conductor, 2 = air, 3 = phantom, 101-116 = the sixteen
**uncut** leg boxes, 117-148 / 217-248 = the lower/upper halves of the 32 ring
gap boxes), then ``meshing_09_birdcage_sixteen_ring_gaps_facets.xdmf`` for
``mesh_tags`` 227-258, the 32 reconstructed ring sheets — radial rectangles seen
edge-on, at a 22.5 degree pitch offset 11.25 degrees off every axis.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import io

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gate's constants, helpers and assertions can be imported rather than
# restated (the `ANS-1` rule).
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)

from tests.mesh.test_birdcage_conductor_sizing import CAD_MASS_GATE  # noqa: E402
from tests.mesh.test_birdcage_port_sheet_prerequisite import (  # noqa: E402
    CELL_COUNT_BAND,
    CONDUCTOR_RESOLUTION,
)
from tests.mesh.test_birdcage_port_tags import (  # noqa: E402
    AIR_PADDING,
    COIL_LENGTH,
    LEG_SPACING,
    LEG_WIDTH,
    PHANTOM_HEIGHT,
    PHANTOM_RADIUS,
    RESOLUTION,
    RING_MINOR_RADIUS,
    RING_RADIUS,
)
from tests.mesh.test_birdcage_port_terminals import CONDUCTOR_IFACE  # noqa: E402
from tests.mesh.test_birdcage_port_scaleup import (  # noqa: E402
    SCALED_LEG_COUNT,
    TERMINAL_INTER_CLASS_CEILING,
    TERMINAL_INTRA_CLASS_BAND,
)
from tests.mesh.test_birdcage_ring_gaps import (  # noqa: E402
    EXACT,
    RING_GAP_CELL_RECORD,
    RING_GAP_LENGTH,
    RING_TERMINAL_RATIO,
    RING_TERMINAL_RATIO_BAND,
    SYMMETRY,
    _spread,
)
from tests.mesh.test_birdcage_ring_gaps_scaleup import (  # noqa: E402
    CONTROL_LEG_COUNT,
    EXPECTED_CLASS_COUNT,
    _assert_ring_identity_family,
    _measure_ring,
    _report_safely,
    _terminal_classes,
)

CELL_TAG_NAMES = {1: "conductor", 2: "air", 3: "phantom"}

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "meshing_09_birdcage_sixteen_ring_gaps"

# `GEO-20` step 2's own record run at `-n 2`
# (`20260829T140037Z_GEO-20-step2-rerun-n2.log`, re-read at `-n 12` in the
# 09:00 slot of 2026-08-29). Printed for comparison only — the identity family
# below is what this example asserts, and the 16-leg ring cell count carries no
# band in the gate module either.
SCALED_CELL_RECORD = 265621
SCALED_TERMINAL_RATIO_RANGE = (0.974454791, 0.974455668)
SCALED_SHEET_SPREAD_RECORD = 5.0e-16
SCALED_CAD_RATIO_RECORD = 0.976465


def _write_cells(mesh, cell_tags, comm):
    """Mesh + cell tags as a DG0 ``CellTags`` array."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined", mesh, cell_tags, {}, comm=comm
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def _write_facets(mesh, facet_tags, comm):
    """The 32 reconstructed ring sheets, on their own tdim-1 grid (the `EX-1` pattern)."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{BASENAME}_facets.xdmf"
    mesh.topology.create_connectivity(mesh.topology.dim - 1, mesh.topology.dim)
    with io.XDMFFile(comm, path, "w") as xdmf:
        xdmf.write_mesh(mesh)
        xdmf.write_meshtags(facet_tags, mesh.geometry)
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path if comm.rank == 0 else None


def _class_table(m):
    """``[(key, n_ports, meshed/analytic, intra-class spread)]`` for one build."""
    analytic = m["diag"]["ring_port_layout"]["ring_terminal_area_m2"]
    rows = []
    for key, members in _terminal_classes(m).items():
        vals = np.array([m["areas"][CONDUCTOR_IFACE + i] for i in members])
        intra = (vals.max() - vals.min()) / vals.mean() if len(members) > 1 else 0.0
        rows.append((key, len(members), vals.mean() / analytic, intra))
    return rows


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if comm.rank == 0:
        print("=" * 72)
        print("EX-35 — the 16-leg ring-gapped birdcage: 32 ring ports, the high-pass layout")
        print("=" * 72)
        print(
            f"\n[geometry] leg_count={SCALED_LEG_COUNT} (control {CONTROL_LEG_COUNT})  "
            f"ring_radius={RING_RADIUS} m  ring_minor_radius={RING_MINOR_RADIUS} m"
            f"\n[geometry] leg_width={LEG_WIDTH} m  coil_length={COIL_LENGTH} m  "
            f"leg_spacing={LEG_SPACING} m  phantom {PHANTOM_RADIUS} x "
            f"{PHANTOM_HEIGHT} m  air_padding={AIR_PADDING} m"
            f"\n[mesh]     resolution={RESOLUTION} m  h_c={CONDUCTOR_RESOLUTION:.4e} m "
            f"(graded, the GEO-8 rule)"
            f"\n[cut]      ring_gap_length={RING_GAP_LENGTH:.4e} m on BOTH end rings at "
            f"the mid-azimuth, leg_gap_length=None, emit_port_sheets=True"
            f"\n[layout]   {2 * SCALED_LEG_COUNT} ring ports / "
            f"{2 * SCALED_LEG_COUNT} sheets — the legs are UNCUT on this rung, so "
            "32 sheets and not 48;"
            "\n           the 48-sheet dual-family build has never been meshed at 16 "
            "legs"
            f"\n[gate]     identity family at {EXACT:.0e} (closure, wedge volume, "
            f"w^2 sheet), C{2 * SCALED_LEG_COUNT} spread and ring mirror at "
            f"{SYMMETRY:.0e},"
            f"\n           terminals per azimuth class (intra "
            f"{TERMINAL_INTRA_CLASS_BAND:.0e}, inter ceiling "
            f"{TERMINAL_INTER_CLASS_CEILING:.0e}), CAD mass gate {CAD_MASS_GATE}"
            f"\n[records]  printed for comparison only: {SCALED_CELL_RECORD} cells, "
            f"terminals {SCALED_TERMINAL_RATIO_RANGE[0]}-"
            f"{SCALED_TERMINAL_RATIO_RANGE[1]},"
            f"\n           C{2 * SCALED_LEG_COUNT} sheet spread ~"
            f"{SCALED_SHEET_SPREAD_RECORD:.0e}, meshed/CAD conductor "
            f"{SCALED_CAD_RATIO_RECORD}"
            "\n[scope]    mesh only: no solve, no port model, no drive, no "
            "resonance or F-human claim",
            flush=True,
        )

    # ---- rung 1: sixteen legs, both end rings cut, 32 sheets ---------------
    # `_measure_ring` builds and reduces everything the gates read; every
    # collective inside it is entered by every rank before anything is printed
    # (the `GEO-18` step 2 attempt-1 deadlock).
    scaled = _measure_ring(SCALED_LEG_COUNT)
    problems = [_report_safely(f"{SCALED_LEG_COUNT} legs", scaled, comm)]

    # ---- rung 2: four legs, same code path, the negative control -----------
    control = _measure_ring(CONTROL_LEG_COUNT)
    problems.append(
        _report_safely(f"{CONTROL_LEG_COUNT} legs (control)", control, comm)
    )

    scaled_rows = _class_table(scaled)
    control_rows = _class_table(control)

    if comm.rank == 0:
        scaled_terminals = np.array(
            [scaled["areas"][CONDUCTOR_IFACE + i] for i in scaled["ring_ports"]]
        )
        scaled_analytic = scaled["diag"]["ring_port_layout"]["ring_terminal_area_m2"]
        scaled_sheets = [scaled["sheet_area"][i] for i in scaled["ring_ports"]]
        scaled_cad = scaled["volumes"][1] / scaled["cad_conductor"]
        print(
            f"\n[EX-35 class table] the reading a C4 ring fixture cannot show: "
            f"{len(scaled_rows)} azimuth classes at {SCALED_LEG_COUNT} legs vs "
            f"{len(control_rows)} at {CONTROL_LEG_COUNT} — the gap centres are at "
            f"11.25 + 22.5*j deg, none of them axis- or diagonal-aligned",
            flush=True,
        )
        for label, rows in (
            (f"{SCALED_LEG_COUNT} legs", scaled_rows),
            (f"{CONTROL_LEG_COUNT} legs (control)", control_rows),
        ):
            for key, n, ratio, intra in rows:
                print(
                    f"  {label:<22s} class '{key}': {n:2d} ports  "
                    f"meshed/analytic={ratio:.9f}  intra-class spread={intra:.3e}",
                    flush=True,
                )
        means = np.array([r[2] for r in scaled_rows])
        inter = (means.max() - means.min()) / means.mean() if len(means) > 1 else 0.0
        print(
            f"  inter-class spread at {SCALED_LEG_COUNT} legs: {inter:.3e} "
            f"(ceiling {TERMINAL_INTER_CLASS_CEILING})",
            flush=True,
        )
        print(
            f"\n[EX-35 vs the GEO-20 step 2 record run] printed, never asserted:"
            f"\n  cells                {scaled['n_cells']} vs {SCALED_CELL_RECORD} "
            f"(relative {scaled['n_cells'] / SCALED_CELL_RECORD - 1.0:.3e})"
            f"\n  terminal ratio range "
            f"{scaled_terminals.min() / scaled_analytic:.9f}-"
            f"{scaled_terminals.max() / scaled_analytic:.9f} vs "
            f"{SCALED_TERMINAL_RATIO_RANGE[0]}-{SCALED_TERMINAL_RATIO_RANGE[1]}"
            f"\n  C{2 * SCALED_LEG_COUNT} sheet spread      "
            f"{_spread(scaled_sheets):.3e} (record ~{SCALED_SHEET_SPREAD_RECORD:.0e}, "
            f"band {SYMMETRY:.0e})"
            f"\n  meshed/CAD conductor {scaled_cad:.6f} vs "
            f"{SCALED_CAD_RATIO_RECORD} (gate {CAD_MASS_GATE})"
            f"\n\n[EX-35 cost rung] {CONTROL_LEG_COUNT} -> {SCALED_LEG_COUNT} legs, "
            f"ring-gapped (same run, same box; printed, never asserted):"
            f"\n  cells      {control['n_cells']} -> {scaled['n_cells']} "
            f"({scaled['n_cells'] / control['n_cells']:.4f}x)"
            f"\n  ring ports {len(control['ring_ports'])} -> "
            f"{len(scaled['ring_ports'])} "
            f"({len(scaled['ring_ports']) / len(control['ring_ports']):.4f}x)"
            f"\n  mesh       {control['diag']['mesh_wall_time_s']:.2f} -> "
            f"{scaled['diag']['mesh_wall_time_s']:.2f} s "
            f"({scaled['diag']['mesh_wall_time_s'] / control['diag']['mesh_wall_time_s']:.4f}x)"
            f"\n  build rung {control['elapsed']:.2f} -> {scaled['elapsed']:.2f} s "
            f"(mesh + every reduction the gates read)"
            f"\n  control cells vs `GEO-20` step 1's record {RING_GAP_CELL_RECORD}: "
            f"relative {control['n_cells'] / RING_GAP_CELL_RECORD - 1.0:.3e} "
            f"(band {CELL_COUNT_BAND})",
            flush=True,
        )

    # ---- the gates, imported ----------------------------------------------
    _assert_ring_identity_family(scaled, f"{SCALED_LEG_COUNT} legs")
    _assert_ring_identity_family(control, f"{CONTROL_LEG_COUNT} legs (control)")
    assert not [p for p in problems if p], [p for p in problems if p]

    # The negative control proper. `_assert_ring_identity_family` already gates
    # the class *count* against `EXPECTED_CLASS_COUNT` on both rungs; restating
    # it here would be a second copy of the same assert, so what this example
    # adds is the pair read together: sixteen legs must give strictly more
    # classes than four, which is the whole reason the ring family had to be
    # re-read above C4 at all.
    assert len(control_rows) == EXPECTED_CLASS_COUNT[CONTROL_LEG_COUNT] and len(
        scaled_rows
    ) == EXPECTED_CLASS_COUNT[SCALED_LEG_COUNT], (
        f"class counts {len(control_rows)} at {CONTROL_LEG_COUNT} legs and "
        f"{len(scaled_rows)} at {SCALED_LEG_COUNT} against the construction's "
        f"{EXPECTED_CLASS_COUNT}"
    )
    assert len(scaled_rows) > len(control_rows), (
        f"the {SCALED_LEG_COUNT}-leg rung folds into {len(scaled_rows)} azimuth "
        f"classes {[r[0] for r in scaled_rows]} and the {CONTROL_LEG_COUNT}-leg "
        f"control into {len(control_rows)} {[r[0] for r in control_rows]}; if the "
        "production count does not split further than C4 then the per-class "
        "reading is not measuring azimuth at all"
    )

    # The control's own records, imported with their bands (`GEO-20` step 1).
    assert abs(control["n_cells"] / RING_GAP_CELL_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"the {CONTROL_LEG_COUNT}-leg control meshed {control['n_cells']} cells "
        f"against `GEO-20` step 1's record {RING_GAP_CELL_RECORD}; this example's "
        "rung is not the gate's"
    )
    ctl_analytic = control["diag"]["ring_port_layout"]["ring_terminal_area_m2"]
    for i in control["ring_ports"]:
        ratio = control["areas"][CONDUCTOR_IFACE + i] / ctl_analytic
        assert abs(ratio - RING_TERMINAL_RATIO) < RING_TERMINAL_RATIO_BAND, (
            f"the control's ring port P{i} terminal ratio {ratio:.9f} against "
            f"`GEO-20` step 1's record {RING_TERMINAL_RATIO}"
        )

    # ---- ParaView ----------------------------------------------------------
    written = {
        "16-leg cells": _write_cells(scaled["mesh"], scaled["cells"], comm),
        "16-leg sheets": _write_facets(scaled["mesh"], scaled["sheet_tags"], comm),
    }
    if comm.rank == 0:
        first = SCALED_LEG_COUNT + 1
        last = SCALED_LEG_COUNT + 2 * SCALED_LEG_COUNT
        print("\n[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<14s} {path}")
        print(
            "\n[paraview] threshold `CellTags` in the _combined file "
            f"({', '.join(f'{t} = {n}' for t, n in CELL_TAG_NAMES.items())}, "
            f"101-{100 + SCALED_LEG_COUNT} = the sixteen UNCUT leg"
            f"\n           boxes, {100 + first}-{100 + last} / "
            f"{200 + first}-{200 + last} = the lower/upper halves of the 32 ring gap"
            "\n           boxes) — both end rings are broken by an 8 mm arc at each "
            "mid-azimuth,"
            "\n           while the legs run through unbroken; then open the _facets "
            "file and"
            f"\n           threshold `mesh_tags` to {210 + first}-{210 + last} for "
            "the 32 sheets themselves,"
            "\n           radial rectangles seen edge-on at a 22.5 deg pitch offset "
            "11.25 deg"
            "\n           off every axis — which is the picture the ring-frame "
            "flatness check"
            "\n           exists for, since no global coordinate is constant on any "
            "of them."
            f"\n\nAll identities hold at {SCALED_LEG_COUNT} legs across "
            f"{len(scaled['ring_ports'])} ring ports, and the {CONTROL_LEG_COUNT}-leg "
            f"control collapses to one azimuth class. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
