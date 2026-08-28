"""Example (`EX-28`): the gapped birdcage — leg terminals and port sheets.

The first example in this repo showing a **discontinuous conductor**. `EX-21`
(`mesh:3`) is the *uncut* graded birdcage and `EX-23` (`mesh:4`) is an interior
port sheet on the two-torus fixture; neither shows the geometry `GEO-18` gated,
which is both at once on a coil: every leg cut by a gap so the port box's
z-faces *are* the two stub cut faces (planar disks with the closed form
``pi*r_leg**2`` each), and the box then split at its own mid-plane so a lumped
port has a surface spanning metal to metal to put its source on.

**Why the cut is the whole point.** `PORT-9` step 3 leg (b) measured that on the
uncut coil every port box's conductor-facing area is **exactly**
``0.000000e+00 m²`` under a closure identity at ``1.000000000000`` — the boxes
are isolated air blocks sitting at the midpoint azimuth between adjacent legs,
outside the metal. A sheet spanning such a box drives nothing. `leg_gap_length`
removes ``|z| <= g/2`` from every leg and re-places each port box on its own leg
axis spanning exactly the gap; `emit_port_sheets` then fragments that box with
its mid-plane, so each port becomes **two** cell groups (``10x`` + ``11x``) and
the sheet is rebuilt dolfinx-side from the interface between them (the
known-issues-9 pattern — an interior dim-2 physical group hangs
``model_to_mesh`` at ``-n 2``).

**It asserts, it does not merely render.** Every identity is `GEO-18`'s own,
re-executed here on the example's own two meshes:

* each sheet's MPI-reduced ``dS`` area equals the analytic mid-section ``dx·g``
  to ``1e-9`` — a planar rectangle meshed by a conforming fragment has no
  discretisation error to spend — and its effective width ``A/h`` equals its
  bounding-box transverse extent to ``1e-9``, which is what says the
  reconstructed facet set is the *whole* rectangle rather than a ragged part of
  one (the `PORT-9` step 2b width convention ``w = A/h``);
* the four sheets agree to ``1e-12`` relative (C4 by construction, checked);
* each port's two halves are ``0.5`` of the analytic gap box to ``1e-9``;
* the terminal ratio against the closed-form ``2·pi·r_leg²`` lands in the
  pre-stated inscribed band and reproduces step 1's record ``0.988616`` to
  ``1e-5``, with the closure identity saying the boundary partition is
  exhaustive so that reading is the whole terminal, not a fragment;
* the `GEO-9` box partition holds on **both** rungs to ``1e-9``.

**Negative control — the uncut coil, asserted to lack all of it** (the
`EX-18` / `EX-21` / `EX-23` inverted-assertion pattern). Built with
``leg_gap_length=None``, the default rung must reproduce `EX-21`'s record
(98 474 cells, meshed/CAD ``0.967019``) and carry:

* conductor-facing port area **exactly 0.0** on all four ports — leg (b)'s
  finding, re-measured;
* no ``11x`` cell tag, so there is no interface to rebuild a sheet from;
* and — measured, not implied — ``_global_facet_count`` **= 0** on every
  ``210+i`` after running the same `_interface_facet_tags` rebuild on the uncut
  mesh. `GEO-18` step 2's audit found that clause asserted on the *cell* tags
  and only implied for the facet groups; this example closes it directly.

Every constant is **imported** from the two `GEO-18` gate modules and the
modules they import in turn (the `ANS-1` rule); nothing is restated, so this
example cannot drift from the gates it demonstrates.

**Mesh only — no port model, no solve, no impedance or resonance claim.** A
gapped birdcage without lumped elements cannot resonate; this is the mesh
`PORT-9` step 3 solves on, and nothing downstream of it. Real DolfinX build.

Run it through the example runner::

    ./run_examples.sh -e mesh:6 -n 2 -t 400

Output lands in ``examples/meshing/paraview_output/``: open
``meshing_06_birdcage_leg_gaps_port_sheets_sheeted_combined.xdmf`` and threshold on
``CellTags`` (1 = conductor, 2 = air, 3 = phantom, 101-104 and 111-114 = the
lower/upper halves of the four gap boxes) — the gaps are visible as breaks in
the legs. ``..._uncut_combined.xdmf`` is the same view of `EX-21`'s coil for
side-by-side comparison, and ``..._sheeted_facets.xdmf`` carries the
reconstructed sheets as ``mesh_tags`` 211-214, the interior surfaces this
example exists to show.
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
# the gates' constants and helpers can be imported rather than restated.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.mesh import _interface_facet_tags  # noqa: E402
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)

from tests.mesh.helpers import global_cell_tag_set  # noqa: E402
from tests.mesh.test_coil_phantom_conforming import _tag_volume, _total_volume  # noqa: E402
from tests.mesh.test_birdcage_conductor_sizing import CAD_MASS_GATE  # noqa: E402
from tests.mesh.test_birdcage_port_sheet_prerequisite import (  # noqa: E402
    CELL_COUNT_BAND,
    CONDUCTOR_RESOLUTION,
    STEP3_CELL_COUNT_RECORD,
)
from tests.mesh.test_birdcage_port_terminals import (  # noqa: E402
    AIR_IFACE,
    CONDUCTOR_IFACE,
    PHANTOM_IFACE,
    _global_facet_count,
    _interface_area_or_zero,
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
from tests.mesh.test_birdcage_leg_gaps import (  # noqa: E402
    LEG_GAP_LENGTH,
    TERMINAL_AREA_BAND,
    UNCUT_CAD_RATIO_BAND,
    UNCUT_CAD_RATIO_RECORD,
    _analytic_box_volume,
    _analytic_terminal_area,
)
from tests.mesh.test_birdcage_leg_gaps import _build as _build_gapped  # noqa: E402
from tests.mesh.test_birdcage_leg_gaps import (  # noqa: E402
    _port_boundary_partition as _partition_single,
)
from tests.mesh.test_birdcage_port_sheets import (  # noqa: E402
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
    STEP1_TERMINAL_RATIO,
    STEP1_TERMINAL_RATIO_BAND,
    _build as _build_sheeted,
    _port_boundary_partition as _partition_halves,
    _sheet_axes,
)
from tests.mesh.test_two_torus_port_sheet import _sheet_extents  # noqa: E402

CELL_TAG_NAMES = {1: "conductor", 2: "air", 3: "phantom"}

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "meshing_06_birdcage_leg_gaps_port_sheets"

PORTS = list(range(1, LEG_COUNT + 1))

# `GEO-18`'s own bands, restated nowhere else: the mid-section area, the
# effective-width convention, the half split and the closure are all exact
# identities on a conforming fragment of a rectangular box.
IDENTITY_BAND = 1.0e-9
# The four sheets are the same rectangle rotated by C4, so they may differ only
# by the mesh — and a plane rectangle's triangulation is exact, so not even by
# that.
C4_SHEET_BAND = 1.0e-12
# The sheet facets must lie in their own plane; step 2 measured 2.512e-16 m.
PLANARITY_BAND = 1.0e-12


def _write_cells(mesh, cell_tags, label, comm):
    """Mesh + cell tags of one rung as a DG0 ``CellTags`` array."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_{label}_combined", mesh, cell_tags, {}, comm=comm
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def _write_facets(mesh, facet_tags, label, comm):
    """The reconstructed sheets, on their own tdim-1 grid (the `EX-1` pattern).

    Facet tags cannot ride the cell grid, so they go to a second file — which is
    where 211-214 become visible.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{BASENAME}_{label}_facets.xdmf"
    mesh.topology.create_connectivity(mesh.topology.dim - 1, mesh.topology.dim)
    with io.XDMFFile(comm, path, "w") as xdmf:
        xdmf.write_mesh(mesh)
        xdmf.write_meshtags(facet_tags, mesh.geometry)
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path if comm.rank == 0 else None


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if comm.rank == 0:
        print("=" * 72)
        print("EX-28 — gapped birdcage: leg terminals and port sheets")
        print("=" * 72)
        print(
            f"\n[geometry] leg_count={LEG_COUNT}  ring_radius={RING_RADIUS} m  "
            f"ring_minor_radius={RING_MINOR_RADIUS} m  leg_width={LEG_WIDTH} m"
            f"\n[geometry] coil_length={COIL_LENGTH} m  leg_spacing={LEG_SPACING} m  "
            f"phantom {PHANTOM_RADIUS} x {PHANTOM_HEIGHT} m  air_padding={AIR_PADDING} m"
            f"\n[mesh]     resolution={RESOLUTION} m  h_c={CONDUCTOR_RESOLUTION:.4e} m "
            f"(graded, the GEO-8 rule)"
            f"\n[cut]      leg_gap_length={LEG_GAP_LENGTH:.4e} m; "
            "emit_port_sheets=True on the sheeted rung"
            f"\n[gate]     sheet area / (dx*g) = 1 to {IDENTITY_BAND:.0e}; "
            "uncut control asserted to LACK terminals, halves and sheets",
            flush=True,
        )

    # ---- rung 1: the gapped, sheeted coil ---------------------------------
    mesh, cells, _, diag, elapsed = _build_sheeted(True)
    dx, dy, dz = diag["port_box_size_m"]
    halves = {i: (PORT_LOWER + i, PORT_UPPER + i) for i in PORTS}
    all_tags = [1, 2, 3, *[t for pair in halves.values() for t in pair]]

    tag_set = global_cell_tag_set(mesh, cells)
    assert tag_set == set(all_tags), (
        "the sheeted mesh does not carry both halves of every port box as their "
        f"own cell tags; found {sorted(tag_set)}"
    )

    n_cells = mesh.topology.index_map(3).size_global
    volumes = {t: _tag_volume(mesh, cells, t, comm) for t in all_tags}
    v_total = _total_volume(mesh, comm)
    cad_conductor = diag["cad_mass_by_group"]["conductor"]
    cad_ratio = volumes[1] / cad_conductor
    counts, areas = _partition_halves(mesh, cells, comm, halves)

    sheet_tags = _interface_facet_tags(
        mesh, cells, {SHEET_IFACE + i: halves[i] for i in PORTS}
    )
    # All three are collective: every rank must enter them, so none may live
    # inside a rank-0 print (`GEO-18` step 2 attempt 1 paid an exit 124 for
    # exactly that).
    sheet_count = {
        i: _global_facet_count(mesh, sheet_tags, SHEET_IFACE + i, comm) for i in PORTS
    }
    sheet_area = {
        i: _interface_area_or_zero(mesh, sheet_tags, SHEET_IFACE + i, comm)
        for i in PORTS
    }
    sheet_extent = {
        i: _sheet_extents(mesh, sheet_tags, SHEET_IFACE + i, comm) for i in PORTS
    }

    box_area = 2.0 * (dx * dy + dy * dz + dz * dx)
    box_volume = dx * dy * dz
    sheet_analytic = dx * dz
    terminal_analytic = _analytic_terminal_area()

    # A group matched by zero facets would pass every ratio below vacuously at
    # 0 == 0, so non-emptiness is asserted before anything is divided.
    for i in PORTS:
        assert sheet_count[i] > 0, (
            f"port P{i}'s sheet group is empty; the area identities below would "
            "have passed vacuously"
        )

    if comm.rank == 0:
        print(
            f"\n[GEO-18] sheeted rung: cells={n_cells}  "
            f"box=({dx:.6e}, {dy:.6e}, {dz:.6e}) m  "
            f"meshed/CAD conductor={cad_ratio:.6f} (gate {CAD_MASS_GATE})  "
            f"mesh={diag['mesh_wall_time_s']:.2f} s  rung={elapsed:.2f} s"
            f"\n[GEO-18] analytic sheet dx*g={sheet_analytic:.9e} m^2; gap box "
            f"volume={box_volume:.9e} m^3, surface={box_area:.9e} m^2; "
            f"terminal (2 disks)={terminal_analytic:.9e} m^2",
            flush=True,
        )
        for i in PORTS:
            w_bbox, h_bbox, spread = _sheet_axes(sheet_extent[i], diag, i)
            a_c = areas[CONDUCTOR_IFACE + i]
            a_a = areas[AIR_IFACE + i]
            a_p = areas[PHANTOM_IFACE + i]
            print(
                f"[GEO-18] P{i}: sheet {sheet_count[i]} facets "
                f"{sheet_area[i]:.9e} m^2  "
                f"meshed/analytic={sheet_area[i] / sheet_analytic:.12f}  "
                f"h={h_bbox:.9e} m  w_eff/w_bbox="
                f"{sheet_area[i] / h_bbox / w_bbox:.12f}  "
                f"out-of-plane spread={spread:.3e} m  "
                f"halves {volumes[PORT_LOWER + i] / box_volume:.12f}/"
                f"{volumes[PORT_UPPER + i] / box_volume:.12f}  "
                f"terminal {counts[CONDUCTOR_IFACE + i]} facets {a_c:.9e} m^2 "
                f"meshed/analytic={a_c / terminal_analytic:.9f} "
                f"(step 1 record {STEP1_TERMINAL_RATIO})  "
                f"closure {(a_c + a_a + a_p) / box_area:.12f}",
                flush=True,
            )
        sheets = np.array([sheet_area[i] for i in PORTS])
        print(
            f"[GEO-18] C4 sheet spread="
            f"{(sheets.max() - sheets.min()) / sheets.mean():.3e} "
            f"(band {C4_SHEET_BAND:.0e})",
            flush=True,
        )

    # `GEO-9` on the sheeted rung: the cut and the split move cell groups, not
    # geometry, so the box partition may not move at all.
    assert abs(v_total / _analytic_box_volume(dy) - 1.0) < IDENTITY_BAND, (
        f"sheeted rung total mesh volume {v_total:.9e} m^3 vs the analytic air "
        f"box {_analytic_box_volume(dy):.9e} m^3"
    )
    assert abs(sum(volumes.values()) / v_total - 1.0) < IDENTITY_BAND, (
        f"sheeted rung tagged volumes sum to {sum(volumes.values()):.9e} m^3 of a "
        f"{v_total:.9e} m^3 mesh; a fragment piece carries no physical group"
    )
    assert cad_ratio >= CAD_MASS_GATE, (
        f"the gapped graded conductor keeps {cad_ratio:.6f} of its own CAD mass "
        f"{cad_conductor:.9e} m^3, below the imported {CAD_MASS_GATE} gate"
    )

    for i in PORTS:
        w_bbox, h_bbox, spread = _sheet_axes(sheet_extent[i], diag, i)
        assert spread < PLANARITY_BAND, (
            f"port P{i}'s sheet facets spread {spread:.3e} m out of their own "
            "plane; the reconstructed interface is not planar"
        )
        assert abs(h_bbox / dz - 1.0) < IDENTITY_BAND, (
            f"port P{i}'s sheet runs {h_bbox:.9e} m along the current direction "
            f"against the gap {dz:.9e} m; it does not span the gap"
        )
        assert abs(sheet_area[i] / sheet_analytic - 1.0) < IDENTITY_BAND, (
            f"port P{i}'s sheet area {sheet_area[i]:.9e} m^2 against the analytic "
            f"mid-section dx*g={sheet_analytic:.9e} m^2 (ratio "
            f"{sheet_area[i] / sheet_analytic:.12f}); a planar rectangle meshed by "
            "a conforming fragment has no discretisation error to spend here — "
            "record the drift in the EX-28 entry rather than moving the band"
        )
        assert abs(sheet_area[i] / h_bbox / w_bbox - 1.0) < IDENTITY_BAND, (
            f"port P{i}'s effective width A/h={sheet_area[i] / h_bbox:.9e} m "
            f"differs from its bounding-box extent {w_bbox:.9e} m; by the `PORT-9` "
            "step 2b convention these are equal exactly when the facet set is the "
            "full rectangle, so this one is ragged or partial"
        )
        for tag in halves[i]:
            assert abs(volumes[tag] / box_volume - 0.5) < IDENTITY_BAND, (
                f"port P{i} cell tag {tag} is {volumes[tag] / box_volume:.12f} of "
                f"the analytic gap box {box_volume:.9e} m^3, not the half the "
                "mid-plane split must give; the plane does not pass through the "
                "box centre, i.e. not through the leg axis"
            )
        total = (
            areas[CONDUCTOR_IFACE + i]
            + areas[AIR_IFACE + i]
            + areas[PHANTOM_IFACE + i]
        )
        assert abs(total / box_area - 1.0) < IDENTITY_BAND, (
            f"port P{i}'s two halves bound {total:.9e} m^2 against the analytic "
            f"box surface {box_area:.9e} m^2 (ratio {total / box_area:.12f}); the "
            "split leaked boundary, so the terminal reading is not the terminal"
        )
        ratio = areas[CONDUCTOR_IFACE + i] / terminal_analytic
        low, high = TERMINAL_AREA_BAND
        assert low <= ratio <= high, (
            f"port P{i}'s terminal area {areas[CONDUCTOR_IFACE + i]:.9e} m^2 is "
            f"{ratio:.9f} of the closed form {terminal_analytic:.9e} m^2, outside "
            f"the inscribed band [{low}, {high}]"
        )
        assert abs(ratio - STEP1_TERMINAL_RATIO) < STEP1_TERMINAL_RATIO_BAND, (
            f"port P{i}'s terminal ratio {ratio:.9f} vs `GEO-18` step 1's record "
            f"{STEP1_TERMINAL_RATIO} (band {STEP1_TERMINAL_RATIO_BAND:.0e})"
        )
        assert areas[PHANTOM_IFACE + i] == 0.0, (
            f"port P{i} touches the phantom "
            f"({areas[PHANTOM_IFACE + i]:.9e} m^2); the gap box meets metal and "
            "air only"
        )

    sheets = np.array([sheet_area[i] for i in PORTS])
    assert (sheets.max() - sheets.min()) / sheets.mean() < C4_SHEET_BAND, (
        f"the four sheet areas {sheets} differ by "
        f"{(sheets.max() - sheets.min()) / sheets.mean():.3e} relative; the ports "
        "are not C4-equivalent"
    )

    # ---- rung 2: the uncut coil, the inverted control ----------------------
    ctl_mesh, ctl_cells, _, ctl_diag, ctl_elapsed = _build_gapped(None)
    ctl_tag_set = global_cell_tag_set(ctl_mesh, ctl_cells)
    ctl_port_tags = [PORT_LOWER + i for i in PORTS]
    ctl_all_tags = [1, 2, 3, *ctl_port_tags]
    n_cells_ctl = ctl_mesh.topology.index_map(3).size_global
    ctl_volumes = {t: _tag_volume(ctl_mesh, ctl_cells, t, comm) for t in ctl_all_tags}
    ctl_v_total = _total_volume(ctl_mesh, comm)
    ctl_cad_ratio = ctl_volumes[1] / ctl_diag["cad_mass_by_group"]["conductor"]
    ctl_counts, ctl_areas = _partition_single(ctl_mesh, ctl_cells, comm)
    ctl_box_volume = PORT_BOX_SIZE[0] * PORT_BOX_SIZE[1] * PORT_BOX_SIZE[2]

    # The clause `GEO-18` step 2's audit found implied rather than measured: run
    # the *same* rebuild on the uncut mesh and count what it finds. The upper
    # halves do not exist there, so the interface is empty — but "empty" is a
    # measurement, and this is the measurement.
    ctl_sheet_tags = _interface_facet_tags(
        ctl_mesh,
        ctl_cells,
        {SHEET_IFACE + i: (PORT_LOWER + i, PORT_UPPER + i) for i in PORTS},
    )
    ctl_sheet_count = {
        i: _global_facet_count(ctl_mesh, ctl_sheet_tags, SHEET_IFACE + i, comm)
        for i in PORTS
    }

    if comm.rank == 0:
        print(
            f"\n[control] uncut coil (leg_gap_length=None): cells={n_cells_ctl} "
            f"(EX-21 record {STEP3_CELL_COUNT_RECORD}, ratio "
            f"{n_cells_ctl / STEP3_CELL_COUNT_RECORD:.6f})  "
            f"meshed/CAD conductor={ctl_cad_ratio:.6f} (record "
            f"{UNCUT_CAD_RATIO_RECORD})  rung={ctl_elapsed:.2f} s"
            f"\n[control] cell tags {sorted(ctl_tag_set)} — no 11x half tag, so "
            "there is no interface a sheet could be rebuilt from"
            f"\n[control] conductor-facing port areas "
            + " ".join(
                f"P{i}={ctl_areas[CONDUCTOR_IFACE + i]:.6e}" for i in PORTS
            )
            + " m^2 (inverted assertion — the control must read exactly 0)"
            f"\n[control] 21x sheet facets found by the same rebuild: "
            + " ".join(f"P{i}={ctl_sheet_count[i]}" for i in PORTS)
            + " (measured absence, not implied)",
            flush=True,
        )

    assert ctl_tag_set == {1, 2, 3, *ctl_port_tags}, (
        f"the uncut rung carries cell tags {sorted(ctl_tag_set)}; the opt-in "
        "split the boxes anyway"
    )
    for i in PORTS:
        assert PORT_UPPER + i not in ctl_tag_set
        assert ctl_sheet_count[i] == 0, (
            f"the uncut rung has {ctl_sheet_count[i]} facets on sheet group "
            f"{SHEET_IFACE + i}; the sheet is opt-in, and a control that already "
            "carries it would make the identities above say nothing about the "
            "kwarg"
        )
        assert ctl_counts[CONDUCTOR_IFACE + i] == 0
        assert ctl_areas[CONDUCTOR_IFACE + i] == 0.0, (
            f"uncut: port P{i}'s conductor-facing area "
            f"{ctl_areas[CONDUCTOR_IFACE + i]:.9e} m^2 is not leg (b)'s exact "
            "zero — the port box is supposed to sit outside the metal here"
        )
        assert abs(ctl_volumes[PORT_LOWER + i] / ctl_box_volume - 1.0) < IDENTITY_BAND
    assert abs(n_cells_ctl / STEP3_CELL_COUNT_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"the uncut rung meshed {n_cells_ctl} cells vs `EX-21`'s record "
        f"{STEP3_CELL_COUNT_RECORD}; the opt-in changed the default geometry"
    )
    assert abs(ctl_cad_ratio - UNCUT_CAD_RATIO_RECORD) < UNCUT_CAD_RATIO_BAND, (
        f"the uncut rung keeps {ctl_cad_ratio:.6f} of its CAD conductor mass vs "
        f"`EX-21`'s record {UNCUT_CAD_RATIO_RECORD}"
    )
    assert (
        abs(ctl_v_total / _analytic_box_volume(PORT_BOX_SIZE[1]) - 1.0) < IDENTITY_BAND
    )
    assert abs(sum(ctl_volumes.values()) / ctl_v_total - 1.0) < IDENTITY_BAND

    # ---- ParaView ---------------------------------------------------------
    written = {
        "sheeted cells": _write_cells(mesh, cells, "sheeted", comm),
        "sheeted sheets": _write_facets(mesh, sheet_tags, "sheeted", comm),
        "uncut cells": _write_cells(ctl_mesh, ctl_cells, "uncut", comm),
    }
    if comm.rank == 0:
        print("\n[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<15s} {path}")
        print(
            "\n[paraview] threshold `CellTags` in each _combined file "
            f"({', '.join(f'{t} = {n}' for t, n in CELL_TAG_NAMES.items())}, "
            "101-104 / 111-114 = the lower/upper halves of the four gap boxes);"
            "\n           open the two side by side — the legs are continuous in "
            "the uncut"
            "\n           rung and broken by an 8 mm gap in the sheeted one;"
            "\n           then open the _facets file for `mesh_tags` — 211-214 "
            "are the port"
            "\n           sheets, the interior surfaces this example exists to "
            "show."
            f"\n\nAll identities hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
