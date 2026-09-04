"""Example (`EX-44`): the longitudinal ring-gap port sheet, in ParaView.

`GEO-26` step 1 (2026-09-03) gated a new keyword on
`MeshGenerator.birdcage_port_domain` — `ring_sheet_orientation="longitudinal"`
— that emits, per ring gap on the 4-leg rung, the planar rectangle in the
plane ``u = ring_radius``: normal ``û(phi_c)``, spanning the gap **chord**
along ``phi_hat`` (the drive direction a lumped-sheet port needs) and
``w = ring_port_box_width_m`` along ``ẑ``. Every existing ring-gap example
(`mesh:7`, `mesh:9`) shows only the *default* **transverse** section at
``phi = phi_c`` — a sheet with **zero** extent along the drive direction,
which is why `PORT-13` step 1 found it un-terminable (`h = 0`). No example
shows the sheet the port model can actually drive; this one does.

This is a **geometry** example, one rung below the un-adjudicated 16-leg
finding (`GEO-26` step 2's bistable terminal triangulation, `main` red,
known-issues 2026-09-03): only the 4-leg rung is shown here, at
`GEO-26` step 1's own record, and nothing about the 16-leg rung is claimed.

**What this builds, in one run:** the default (transverse) 4-leg ring-gapped
mesh as the negative control, and the longitudinal 4-leg mesh as the subject.
The longitudinal mesh is written as one combined XDMF carrying the cell tags
(the inner ``100+i`` / outer ``200+i`` halves of each ring port's box, split
by the sheet at ``u = R``) and, separately, the reconstructed sheet facet
tags — so ParaView can threshold one ring port's two halves either side of
the sheet, and the sheet itself edge-on.

**It asserts, it does not merely render** (the `ANS-1` rule): every anchor
below is imported from the gate module and read off *this run's own mesh*,
never restated.

* Cell counts: the longitudinal mesh against `RING_LONGITUDINAL_CELL_RECORD`
  and the transverse control against `RING_GAP_CELL_RECORD`, both at
  `CELL_COUNT_BAND`.
* `_assert_ring_identity_family` — the whole `GEO-20` step 1 identity family
  (partition, air-box closure, Pappus arcs, terminal ratio band, C4 sheet
  spread and top/bottom mirror) plus the sheet's own chord/`w`/half-volume
  identities — green on the longitudinal mesh at its measured
  `LONGITUDINAL_TERMINAL_INTRA_BAND` and on the control at the function's own
  default band.
* Negative control: the transverse control's eight sheets read a `phi_hat`
  extent at machine-precision zero (`<= 1e-12` m — the drive direction a ring
  port would use) where the longitudinal sheets read the `8.0e-3` m gap
  chord — fourteen decades apart, asserted.

**Mesh only.** No port model, no drive, no solve, no `GEO-20` record moves,
no §2 change. The 16-leg longitudinal rung is `GEO-26` step 2's own red and
is not shown here.

Run it through the example runner::

    ./run_examples.sh -e mesh:10 -n 2 -t 300

Output lands in ``examples/meshing/paraview_output/``: open
``meshing_10_birdcage_ring_sheet_longitudinal_combined.xdmf`` and threshold on
``CellTags`` (1 = conductor, 2 = air, 3 = phantom, 101-104 = the four uncut
leg boxes, 105-112 / 205-212 = the inner/outer halves of the eight ring gap
boxes — both end rings, four gaps each), then
``meshing_10_birdcage_ring_sheet_longitudinal_facets.xdmf`` for
``mesh_tags`` 215-222, the eight reconstructed longitudinal sheets.
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

from tests.mesh.test_birdcage_port_sheet_prerequisite import CELL_COUNT_BAND  # noqa: E402
from tests.mesh.test_birdcage_port_tags import RING_RADIUS  # noqa: E402
from tests.mesh.test_birdcage_ring_gaps import RING_GAP_CELL_RECORD, RING_GAP_LENGTH  # noqa: E402
from tests.mesh.test_birdcage_ring_gaps_scaleup import (  # noqa: E402
    CONTROL_LEG_COUNT,
    _assert_ring_identity_family,
    _measure_ring,
    _report_safely,
)
from tests.mesh.test_birdcage_ring_sheet_orientation import (  # noqa: E402
    DEGENERATE_EXTENT_M,
    LONGITUDINAL_TERMINAL_INTRA_BAND,
    RING_LONGITUDINAL_CELL_RECORD,
    _record_ratio,
    _sheet_axes,
    _sheet_extent_along,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "meshing_10_birdcage_ring_sheet_longitudinal"


def _write_cells(mesh, cell_tags, comm):
    """The longitudinal mesh + cell tags as a DG0 ``CellTags`` array."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined", mesh, cell_tags, {}, comm=comm
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def _write_facets(mesh, facet_tags, comm):
    """The eight reconstructed longitudinal sheets, on their own tdim-1 grid."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{BASENAME}_facets.xdmf"
    mesh.topology.create_connectivity(mesh.topology.dim - 1, mesh.topology.dim)
    with io.XDMFFile(comm, path, "w") as xdmf:
        xdmf.write_mesh(mesh)
        xdmf.write_meshtags(facet_tags, mesh.geometry)
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path if comm.rank == 0 else None


def _sheet_rows(m, leg_count):
    """Per-port ``phi_hat``/``ẑ`` extents and the two half volumes."""
    from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER, SHEET_IFACE

    comm = MPI.COMM_WORLD
    msh = m["mesh"]
    rows = {}
    for i in m["ring_ports"]:
        phi_hat, u_hat, z_hat = _sheet_axes(i, leg_count)
        tag = SHEET_IFACE + i
        rows[i] = {
            "phi": _sheet_extent_along(msh, m["sheet_tags"], tag, phi_hat, comm),
            "z": _sheet_extent_along(msh, m["sheet_tags"], tag, z_hat, comm),
            "v_in": float(m["volumes"][PORT_LOWER + i]),
            "v_out": float(m["volumes"][PORT_UPPER + i]),
        }
    return rows


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if comm.rank == 0:
        print("=" * 72)
        print("EX-44 — the longitudinal ring-gap port sheet, in ParaView")
        print("=" * 72)
        print(
            f"\n[geometry] leg_count={CONTROL_LEG_COUNT}  ring_radius={RING_RADIUS} m  "
            f"ring_gap_length={RING_GAP_LENGTH:.4e} m"
            "\n[gate]     tests/mesh/test_birdcage_ring_sheet_orientation.py "
            "(`GEO-26` step 1)"
            "\n[scope]    mesh only: no port model, no drive, no solve, no "
            "`GEO-20` record moves; 4 legs only",
            flush=True,
        )

    # ---- the subject: longitudinal sheets on the 4-leg rung ----------------
    long_m = _measure_ring(CONTROL_LEG_COUNT, orientation="longitudinal")
    long_problem = _report_safely("longitudinal (subject)", long_m, comm)

    # ---- the negative control: default (transverse) sheets, same rung ------
    trans_m = _measure_ring(CONTROL_LEG_COUNT)
    trans_problem = _report_safely("transverse (control)", trans_m, comm)

    layout = long_m["diag"]["ring_port_layout"]
    box_width = float(layout["ring_port_box_width_m"])
    chord = float(layout["ring_port_gap_chord_m"])
    tan_a = float(np.tan(float(layout["ring_gap_half_angle_rad"])))
    port_volume = float(layout["ring_port_volume_m3"])

    # The two closed-form halves, cut at u = R — `GEO-26`'s own derivation,
    # not restated: V(u0..u1) = w·tan(alpha)·(u1² − u0²).
    v_in = box_width * tan_a * (RING_RADIUS * box_width - 0.25 * box_width**2)
    v_out = box_width * tan_a * (RING_RADIUS * box_width + 0.25 * box_width**2)

    long_rows = _sheet_rows(long_m, CONTROL_LEG_COUNT)
    trans_rows = _sheet_rows(trans_m, CONTROL_LEG_COUNT)

    if comm.rank == 0:
        print(
            f"\n[EX-44] longitudinal mesh: {long_m['n_cells']} cells (record "
            f"{RING_LONGITUDINAL_CELL_RECORD}, ratio "
            f"{_record_ratio(long_m['n_cells'])}), mesh "
            f"{long_m['diag']['mesh_wall_time_s']:.2f} s, rung "
            f"{long_m['elapsed']:.2f} s"
            f"\n[EX-44] transverse control: {trans_m['n_cells']} cells (record "
            f"{RING_GAP_CELL_RECORD}, ratio "
            f"{trans_m['n_cells'] / RING_GAP_CELL_RECORD:.6f}), mesh "
            f"{trans_m['diag']['mesh_wall_time_s']:.2f} s, rung "
            f"{trans_m['elapsed']:.2f} s"
            f"\n[EX-44] chord = {chord:.9e} m (arc ring_gap_length = "
            f"{RING_GAP_LENGTH:.9e} m, chord/arc = {chord / RING_GAP_LENGTH:.9f}), "
            f"w = {box_width:.9e} m"
            f"\n[EX-44] closed-form halves: V_in = {v_in:.9e} m^3, V_out = "
            f"{v_out:.9e} m^3, sum/ring_port_volume_m3 = "
            f"{(v_in + v_out) / port_volume:.12f}",
            flush=True,
        )
        print(
            "\n[EX-44] per-port table — phi_hat extent is the drive direction a "
            "lumped-sheet port divides by:",
            flush=True,
        )
        for i in long_m["ring_ports"]:
            lr, tr = long_rows[i], trans_rows[i]
            print(
                f"    P{i}: longitudinal phi_hat/chord = {lr['phi'] / chord:.12f} "
                f"({lr['phi']:.6e} m)  z/w = {lr['z'] / box_width:.12f} "
                f"({lr['z']:.6e} m)  V_in/analytic = {lr['v_in'] / v_in:.12f}  "
                f"V_out/analytic = {lr['v_out'] / v_out:.12f}  |  transverse "
                f"phi_hat extent = {tr['phi']:.3e} m",
                flush=True,
            )

    # ---- the gates, imported ------------------------------------------------
    assert not long_problem, long_problem
    assert not trans_problem, trans_problem

    assert abs(long_m["n_cells"] / RING_LONGITUDINAL_CELL_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"the longitudinal 4-leg rung meshed {long_m['n_cells']} cells against "
        f"`GEO-26` step 1's record {RING_LONGITUDINAL_CELL_RECORD}"
    )
    assert abs(trans_m["n_cells"] / RING_GAP_CELL_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"the transverse control meshed {trans_m['n_cells']} cells against "
        f"`GEO-20` step 1's record {RING_GAP_CELL_RECORD}"
    )

    _assert_ring_identity_family(
        long_m,
        "longitudinal (subject)",
        terminal_intra_band=LONGITUDINAL_TERMINAL_INTRA_BAND,
    )
    _assert_ring_identity_family(trans_m, "transverse (control)")

    # The negative control proper: the transverse sheet's drive-direction
    # extent is degenerate where the longitudinal one is the full chord —
    # fourteen decades apart.
    for i in trans_m["ring_ports"]:
        assert trans_rows[i]["phi"] < DEGENERATE_EXTENT_M, (
            f"transverse control ring port P{i}'s sheet spans "
            f"{trans_rows[i]['phi']:.6e} m along its own drive direction "
            f"phi_hat, above the {DEGENERATE_EXTENT_M:.0e} m degeneracy band"
        )
    for i in long_m["ring_ports"]:
        ratio = long_rows[i]["phi"] / chord
        assert abs(ratio - 1.0) < 1.0e-9, (
            f"longitudinal ring port P{i}'s sheet spans {long_rows[i]['phi']:.9e} "
            f"m against the closed-form chord {chord:.9e} m (ratio {ratio:.12f})"
        )
        separation = long_rows[i]["phi"] / max(trans_rows[i]["phi"], 1e-300)
        assert separation > 1.0e13, (
            f"ring port P{i}'s longitudinal/transverse drive-extent ratio "
            f"{separation:.3e} is not the fourteen-decade separation the two "
            "orientations are supposed to show"
        )

    # ---- ParaView ------------------------------------------------------------
    written = {
        "combined": _write_cells(long_m["mesh"], long_m["cells"], comm),
        "facets": _write_facets(long_m["mesh"], long_m["sheet_tags"], comm),
    }
    if comm.rank == 0:
        print("\n[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<10s} {path}")
        first = CONTROL_LEG_COUNT + 1
        last = CONTROL_LEG_COUNT + 2 * CONTROL_LEG_COUNT
        print(
            "\n[paraview] threshold `CellTags` in the _combined file (1 = "
            "conductor, 2 = air, 3 = phantom, "
            f"101-{100 + CONTROL_LEG_COUNT} = the {CONTROL_LEG_COUNT} uncut leg "
            f"boxes, {100 + first}-{100 + last} / {200 + first}-{200 + last} = "
            "the inner/outer halves of the ring gap boxes split by the "
            "longitudinal sheet at u = R); threshold `100+i` and `200+i` "
            "separately for one port to see the two halves either side of the "
            "sheet. In the _facets file threshold `mesh_tags` to "
            f"{210 + first}-{210 + last} for the sheets themselves — planar "
            "rectangles in the u = R plane, each spanning its gap's full chord "
            "and running through both terminal disks' centres."
            f"\n\nAll identities hold on both the longitudinal subject and the "
            f"transverse control at {CONTROL_LEG_COUNT} legs. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
