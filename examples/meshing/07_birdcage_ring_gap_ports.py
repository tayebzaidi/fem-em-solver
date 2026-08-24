"""Example (`EX-31`): the high-pass birdcage — ring-gap ports, and both families at once.

`EX-28` (`mesh:6`) cuts the **legs** — the low-pass drive element — and its
terminals are the axis-aligned stub faces of a cylinder. This example shows the
geometry `GEO-20` step 1 gated, which `EX-28` does not cover at any angle:

* the **end rings** cut instead, at the mid-azimuth between each adjacent leg
  pair on both rings, so a 4-leg fixture carries ``2·4 = 8`` ring ports (32 at
  the 16-leg production count — item (b) of the §10 32-port directive);
* the cut made by the two **radial half-planes** ``phi = phi_c ± alpha``,
  ``alpha = g/(2·R)``, which every partial-torus arc already ends on. That is
  why a closed form exists at all: each cut face is an exact planar disk of area
  ``pi·r_ring²``. An axis-aligned box cutting a torus would have given oblique
  sections at 45 degrees and no closed form — the construction the leg-gap
  module named and rejected;
* the port solid as the `GEO-18` box **rotated into the gap's own frame**, all
  six faces planar, so volume ``2·R·w²·tan(alpha)``, surface
  ``2·w²/cos(alpha) + 8·R·w·tan(alpha)`` and mid-plane section ``w²`` are exact
  under a linear mesh rather than faceting bands;
* and the first **12-port dual-family mesh** in the repo: leg gaps and ring gaps
  switched on together, with *both* identity families holding on the same mesh.

**It asserts, it does not merely render.** Every constant is imported from
`tests/mesh/test_birdcage_ring_gaps.py` and the modules it imports in turn (the
`ANS-1` rule); nothing is restated, so this example cannot drift from the gate
it demonstrates. On the ring-gapped rung:

* each ring port's terminal is the two exact disks bounding its gap — inside the
  pre-stated inscribed band against ``2·pi·r_ring²`` and reproducing step 1's
  record ``0.974455`` to ``1e-5``, equal across the 8 to ``1e-5``, with the
  closure identity saying the boundary partition is exhaustive so the reading is
  the whole terminal;
* port volume / analytic wedge and sheet area / ``w²`` are ``1`` to ``1e-9``;
* the sheet is planar to roundoff **along its own azimuthal normal** — a ring
  sheet is radial, so no global coordinate is constant on it and the
  bounding-box planarity check `GEO-18` uses cannot be reused here;
* C4 spread and the top/bottom ring mirror are below ``1e-12`` on those exact
  forms, and the `GEO-9` box partition holds.

**Negative control — the kwarg off, asserted to lack all of it** (the `EX-18` /
`EX-21` / `EX-28` inverted-assertion pattern): ``ring_gap_length=None``
reproduces the uncut birdcage's cell-count record and `EX-21`'s meshed/CAD
ratio, carries **no ring port tag at all**, and — measured, not implied — the
same ``_interface_facet_tags`` rebuild finds **0** facets on every ring sheet
group.

**Mesh only — no port model, no drive, no solve, no impedance or resonance
claim.** A gapped birdcage without lumped elements cannot resonate; a high-pass
*layout* is not a high-pass *circuit*. `PORT-9` is 🟡 (PROJECT_PLAN.md §2) and
nothing here is a port claim. Real DolfinX build.

Run it through the example runner::

    ./run_examples.sh -e mesh:7 -n 2 -t 400

Output lands in ``examples/meshing/paraview_output/``: open
``birdcage_ring_gap_ports_ring_combined.xdmf`` and threshold on ``CellTags``
(1 = conductor, 2 = air, 3 = phantom, 101-104 = the four uncut leg boxes,
105-112 / 205-212 = the lower/upper halves of the eight ring gap boxes) — the
gaps are visible as breaks in the two end rings, at the mid-azimuth between
adjacent legs. ``..._legring_combined.xdmf`` is the 12-port mesh with both
families cut, ``..._uncut_combined.xdmf`` the control, and
``..._ring_facets.xdmf`` carries the reconstructed ring sheets as ``mesh_tags``
215-222 — radial rectangles seen edge-on at 45 degrees.
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
# the gate's constants and helpers can be imported rather than restated.
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
)
from tests.mesh.test_birdcage_port_sheets import (  # noqa: E402
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
    STEP1_TERMINAL_RATIO,
    STEP1_TERMINAL_RATIO_BAND,
)
from tests.mesh.test_birdcage_ring_gaps import (  # noqa: E402
    EXACT,
    LEG_RING_CELL_RECORD,
    MIRROR_PAIRS,
    RING_GAP_CELL_RECORD,
    RING_GAP_LENGTH,
    RING_PORTS,
    RING_TERMINAL_RATIO,
    RING_TERMINAL_RATIO_BAND,
    SYMMETRY,
    TERMINAL_EQUALITY,
    _build,
    _out_of_plane_spread,
    _port_boundary_partition,
    _ring_gap_frame,
    _spread,
)
from tests.mesh.test_two_torus_port_sheet import _sheet_extents  # noqa: E402

CELL_TAG_NAMES = {1: "conductor", 2: "air", 3: "phantom"}

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "birdcage_ring_gap_ports"

LEG_PORTS = list(range(1, LEG_COUNT + 1))


def _write_cells(mesh, cell_tags, label, comm):
    """Mesh + cell tags of one rung as a DG0 ``CellTags`` array."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_{label}_combined", mesh, cell_tags, {}, comm=comm
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def _write_facets(mesh, facet_tags, label, comm):
    """The reconstructed ring sheets, on their own tdim-1 grid (the `EX-1` pattern)."""
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
        print("EX-31 — high-pass birdcage: ring-gap ports and the 12-port dual family")
        print("=" * 72)
        print(
            f"\n[geometry] leg_count={LEG_COUNT}  ring_radius={RING_RADIUS} m  "
            f"ring_minor_radius={RING_MINOR_RADIUS} m  leg_width={LEG_WIDTH} m"
            f"\n[geometry] coil_length={COIL_LENGTH} m  leg_spacing={LEG_SPACING} m  "
            f"phantom {PHANTOM_RADIUS} x {PHANTOM_HEIGHT} m  air_padding={AIR_PADDING} m"
            f"\n[mesh]     resolution={RESOLUTION} m  h_c={CONDUCTOR_RESOLUTION:.4e} m "
            f"(graded, the GEO-8 rule)"
            f"\n[cut]      ring_gap_length={RING_GAP_LENGTH:.4e} m on both end rings, "
            f"at the mid-azimuth; leg_gap_length={LEG_GAP_LENGTH:.4e} m on rung 2"
            f"\n[gate]     ring terminal / (2*pi*r_ring^2) = "
            f"{RING_TERMINAL_RATIO} to {RING_TERMINAL_RATIO_BAND:.0e}; closure, "
            f"volume and sheet = 1 to {EXACT:.0e}; control asserted to LACK "
            "every ring port",
            flush=True,
        )

    # ---- rung 1: the ring-gapped, sheeted coil ----------------------------
    mesh, cells, _, diag, elapsed = _build(
        ring_gap_length=RING_GAP_LENGTH, emit_port_sheets=True
    )
    layout = diag["ring_port_layout"]
    # The four leg boxes are floating air blocks here (no leg gap ⇒ no terminal
    # and nothing to split); only the ring ports are sheeted. That asymmetry is
    # the high-pass fixture, and it is asserted rather than assumed.
    port_cell_tags = {i: (PORT_LOWER + i,) for i in LEG_PORTS}
    port_cell_tags.update({i: (PORT_LOWER + i, PORT_UPPER + i) for i in RING_PORTS})
    expected_tags = {1, 2, 3, *[t for tags in port_cell_tags.values() for t in tags]}

    tag_set = global_cell_tag_set(mesh, cells)
    assert tag_set == expected_tags, (
        "the ring-gapped mesh does not carry both halves of every ring port as "
        f"their own cell tags; found {sorted(tag_set)}"
    )

    n_cells = mesh.topology.index_map(3).size_global
    all_tags = sorted(expected_tags)
    volumes = {t: _tag_volume(mesh, cells, t, comm) for t in all_tags}
    v_total = _total_volume(mesh, comm)
    cad_gap = diag["cad_mass_by_group"]["conductor"]
    cad_ratio = volumes[1] / cad_gap
    counts, areas = _port_boundary_partition(mesh, cells, comm, port_cell_tags)

    sheet_tags = _interface_facet_tags(
        mesh, cells, {SHEET_IFACE + i: port_cell_tags[i] for i in RING_PORTS}
    )
    # All four are collective: every rank must enter them, so none may live
    # inside a rank-0 print (`GEO-18` step 2 attempt 1 paid an exit 124 for
    # exactly that).
    sheet_count = {
        i: _global_facet_count(mesh, sheet_tags, SHEET_IFACE + i, comm)
        for i in RING_PORTS
    }
    sheet_area = {
        i: _interface_area_or_zero(mesh, sheet_tags, SHEET_IFACE + i, comm)
        for i in RING_PORTS
    }
    sheet_extent = {
        i: _sheet_extents(mesh, sheet_tags, SHEET_IFACE + i, comm) for i in RING_PORTS
    }
    sheet_flatness = {
        i: _out_of_plane_spread(
            mesh, sheet_tags, SHEET_IFACE + i, *_ring_gap_frame(i), comm
        )
        for i in RING_PORTS
    }

    terminal_analytic = layout["ring_terminal_area_m2"]
    port_volume = layout["ring_port_volume_m3"]
    port_surface = layout["ring_port_surface_m2"]
    sheet_analytic = layout["ring_port_sheet_area_m2"]
    port_total_volume = {
        i: sum(volumes[t] for t in port_cell_tags[i]) for i in RING_PORTS
    }
    # Pappus on the ring primitives, before any boolean: the identity that is a
    # claim about *this* construction. The union form (gapped conductor = uncut
    # conductor − removed arcs) is a difference of two O(1e-4) OCC unions and so
    # carries their quadrature error — printed below, never gated (the gate
    # module's own reading, `GEO-18` step 1's precedent on the leg cut).
    ring_primitive = diag["ring_cad_mass_m3"] / diag["ring_analytic_mass_m3"]

    # A group matched by zero facets would pass every ratio below vacuously at
    # 0 == 0, so non-emptiness is asserted before anything is divided.
    for i in RING_PORTS:
        assert sheet_count[i] > 0, (
            f"ring port P{i}'s sheet group is empty; the area identities below "
            "would have passed vacuously"
        )

    if comm.rank == 0:
        print(
            f"\n[GEO-20] ring-gapped rung: cells={n_cells}  "
            f"alpha={layout['ring_gap_half_angle_rad']:.9e} rad  "
            f"w={layout['ring_port_box_width_m']:.6e} m  "
            f"ports={len(port_cell_tags)} ({LEG_COUNT} leg + {len(RING_PORTS)} "
            f"ring)  meshed/CAD conductor={cad_ratio:.6f} (gate {CAD_MASS_GATE})  "
            f"mesh={diag['mesh_wall_time_s']:.2f} s  rung={elapsed:.2f} s"
            f"\n[GEO-20] closed forms: terminal (2 disks) "
            f"{terminal_analytic:.9e} m^2, port volume {port_volume:.9e} m^3, "
            f"port surface {port_surface:.9e} m^2, sheet (w^2) "
            f"{sheet_analytic:.9e} m^2"
            f"\n[GEO-20] ring primitives (Pappus, pre-boolean): "
            f"{diag['ring_cad_mass_m3']:.12e} / "
            f"{diag['ring_analytic_mass_m3']:.12e} = {ring_primitive:.12f}"
            f"\n[GEO-20] clearances: leg arc "
            f"{layout['ring_leg_arc_clearance_m']:.6e} m, phantom "
            f"{layout['ring_phantom_radial_clearance_m']:.6e} m",
            flush=True,
        )
        for i in RING_PORTS:
            a_c = areas[CONDUCTOR_IFACE + i]
            a_a = areas[AIR_IFACE + i]
            a_p = areas[PHANTOM_IFACE + i]
            print(
                f"[GEO-20] P{i}: terminal {counts[CONDUCTOR_IFACE + i]} facets "
                f"{a_c:.9e} m^2 meshed/analytic={a_c / terminal_analytic:.9f} "
                f"(step 1 record {RING_TERMINAL_RATIO})  air "
                f"{counts[AIR_IFACE + i]} facets {a_a:.9e} m^2  phantom "
                f"{a_p:.6e} m^2  closure {(a_c + a_a + a_p) / port_surface:.12f}  "
                f"volume/analytic {port_total_volume[i] / port_volume:.12f}  "
                f"sheet {sheet_count[i]} facets {sheet_area[i]:.9e} m^2 "
                f"meshed/analytic={sheet_area[i] / sheet_analytic:.12f}  "
                f"extents=({sheet_extent[i][0]:.6e}, {sheet_extent[i][1]:.6e}, "
                f"{sheet_extent[i][2]:.6e})  out-of-plane "
                f"{sheet_flatness[i]:.3e} m",
                flush=True,
            )
        terminals = np.array([areas[CONDUCTOR_IFACE + i] for i in RING_PORTS])
        print(
            f"[GEO-20] C4+mirror spreads: volume "
            f"{_spread([port_total_volume[i] for i in RING_PORTS]):.3e}  sheet "
            f"{_spread([sheet_area[i] for i in RING_PORTS]):.3e} (band "
            f"{SYMMETRY:.0e})  terminal {_spread(terminals):.3e} (band "
            f"{TERMINAL_EQUALITY:.0e})",
            flush=True,
        )

    # `GEO-9` on the ring-gapped rung: the cut and the split move cell groups,
    # not geometry, so the box partition may not move at all.
    assert abs(v_total / _analytic_box_volume(PORT_BOX_SIZE[1]) - 1.0) < EXACT, (
        f"ring-gapped rung total mesh volume {v_total:.9e} m^3 vs the analytic "
        f"air box {_analytic_box_volume(PORT_BOX_SIZE[1]):.9e} m^3"
    )
    assert abs(sum(volumes.values()) / v_total - 1.0) < EXACT, (
        f"ring-gapped rung tagged volumes sum to {sum(volumes.values()):.9e} m^3 "
        f"of a {v_total:.9e} m^3 mesh; a fragment piece carries no physical group"
    )
    assert abs(ring_primitive - 1.0) < EXACT, (
        f"the {2 * LEG_COUNT} ring arcs have CAD mass "
        f"{diag['ring_cad_mass_m3']:.12e} m^3 against Pappus' "
        f"{diag['ring_analytic_mass_m3']:.12e} m^3 (ratio {ring_primitive:.12f}); "
        "the swept angle is not `2*pi/N - g/R`"
    )
    assert cad_ratio >= CAD_MASS_GATE, (
        f"the ring-gapped graded conductor keeps {cad_ratio:.6f} of its own CAD "
        f"mass {cad_gap:.9e} m^3, below the imported {CAD_MASS_GATE} gate"
    )
    assert abs(n_cells / RING_GAP_CELL_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"the ring-gapped rung meshed {n_cells} cells vs `GEO-20` step 1's record "
        f"{RING_GAP_CELL_RECORD} (ratio {n_cells / RING_GAP_CELL_RECORD:.6f})"
    )

    low, high = TERMINAL_AREA_BAND
    for i in RING_PORTS:
        a_c = areas[CONDUCTOR_IFACE + i]
        total = a_c + areas[AIR_IFACE + i] + areas[PHANTOM_IFACE + i]
        assert abs(total / port_surface - 1.0) < EXACT, (
            f"ring port P{i} boundary areas sum to {total:.9e} m^2 against the "
            f"analytic wedge surface {port_surface:.9e} m^2 (ratio "
            f"{total / port_surface:.12f}); the partition is not exhaustive, so "
            "the terminal reading would be a fragment, not the terminal"
        )
        assert abs(port_total_volume[i] / port_volume - 1.0) < EXACT, (
            f"ring port P{i} meshed volume {port_total_volume[i]:.9e} m^3 against "
            f"the analytic wedge {port_volume:.9e} m^3 — the solid does not span "
            "the gap exactly, so its radial faces are not the ring's cut faces"
        )
        ratio = a_c / terminal_analytic
        assert low <= ratio <= high, (
            f"ring port P{i} terminal area {a_c:.9e} m^2 is {ratio:.9f} of the "
            f"closed form {terminal_analytic:.9e} m^2 (two disks of radius "
            f"{RING_MINOR_RADIUS:.6e} m); an inscribed triangulation must land in "
            f"[{low}, {high}]"
        )
        assert abs(ratio - RING_TERMINAL_RATIO) < RING_TERMINAL_RATIO_BAND, (
            f"ring port P{i}'s terminal ratio {ratio:.9f} vs `GEO-20` step 1's "
            f"record {RING_TERMINAL_RATIO} (band {RING_TERMINAL_RATIO_BAND:.0e}) "
            "— record the drift in the EX-31 / GEO-20 entries rather than moving "
            "the band"
        )
        assert areas[PHANTOM_IFACE + i] == 0.0, (
            f"ring port P{i} touches the phantom "
            f"({areas[PHANTOM_IFACE + i]:.6e} m^2); the gap solid meets metal and "
            "air only"
        )
        assert abs(sheet_area[i] / sheet_analytic - 1.0) < EXACT, (
            f"ring port P{i} sheet area {sheet_area[i]:.9e} m^2 against the "
            f"analytic mid-section w^2={sheet_analytic:.9e} m^2 (ratio "
            f"{sheet_area[i] / sheet_analytic:.12f}); the reconstructed facet set "
            "is not the whole w x w rectangle"
        )
        assert sheet_flatness[i] < SYMMETRY, (
            f"ring port P{i}'s sheet is {sheet_flatness[i]:.3e} m out of its own "
            f"radial plane (extents {sheet_extent[i]}); measured along the sheet's "
            "azimuthal normal, because no global coordinate is constant on it"
        )

    for label, values in (
        ("volume", [port_total_volume[i] for i in RING_PORTS]),
        ("sheet", [sheet_area[i] for i in RING_PORTS]),
    ):
        assert _spread(values) < SYMMETRY, (
            f"ring port {label}s {values} are not C4-symmetric to {SYMMETRY} "
            f"(spread {_spread(values):.3e}); the eight ring ports are not the "
            "same port"
        )
    for lo_port, hi_port in MIRROR_PAIRS:
        for label, table in (("volume", port_total_volume), ("sheet", sheet_area)):
            lo_v, hi_v = table[lo_port], table[hi_port]
            assert abs(hi_v / lo_v - 1.0) < SYMMETRY, (
                f"ring {label} mirror pair P{lo_port}/P{hi_port} reads "
                f"{lo_v:.12e} / {hi_v:.12e} (ratio {hi_v / lo_v:.12f}); the top "
                "and bottom rings are not mirror images"
            )
    terminals = np.array([areas[CONDUCTOR_IFACE + i] for i in RING_PORTS])
    assert _spread(terminals) < TERMINAL_EQUALITY, (
        f"ring terminal areas {terminals} are not equal to {TERMINAL_EQUALITY} "
        f"(spread {_spread(terminals):.3e}); a circulant premise would fail"
    )

    # ---- rung 2: both gap families at once, the 12-port mesh ---------------
    lr_mesh, lr_cells, _, lr_diag, lr_elapsed = _build(
        ring_gap_length=RING_GAP_LENGTH,
        leg_gap_length=LEG_GAP_LENGTH,
        emit_port_sheets=True,
    )
    lr_layout = lr_diag["ring_port_layout"]
    lr_port_cell_tags = {
        i: (PORT_LOWER + i, PORT_UPPER + i) for i in LEG_PORTS + RING_PORTS
    }
    lr_expected = {1, 2, 3, *[t for tags in lr_port_cell_tags.values() for t in tags]}
    assert global_cell_tag_set(lr_mesh, lr_cells) == lr_expected, (
        "the doubly-gapped mesh does not carry all 12 ports as split cell-tag pairs"
    )

    n_cells_lr = lr_mesh.topology.index_map(3).size_global
    lr_volumes = {
        t: _tag_volume(lr_mesh, lr_cells, t, comm) for t in sorted(lr_expected)
    }
    lr_v_total = _total_volume(lr_mesh, comm)
    lr_counts, lr_areas = _port_boundary_partition(
        lr_mesh, lr_cells, comm, lr_port_cell_tags
    )

    gap_dx, gap_dy, gap_dz = lr_diag["port_box_size_m"]
    leg_surface = 2.0 * (gap_dx * gap_dy + gap_dy * gap_dz + gap_dz * gap_dx)
    leg_volume = gap_dx * gap_dy * gap_dz
    leg_terminal = 2.0 * np.pi * (0.5 * LEG_WIDTH) ** 2
    ring_surface = lr_layout["ring_port_surface_m2"]
    ring_volume = lr_layout["ring_port_volume_m3"]
    ring_terminal = lr_layout["ring_terminal_area_m2"]

    if comm.rank == 0:
        print(
            f"\n[GEO-20] leg+ring rung: cells={n_cells_lr}  "
            f"ports={len(lr_port_cell_tags)} ({LEG_COUNT} leg + {len(RING_PORTS)} "
            f"ring, all sheeted)  mesh={lr_diag['mesh_wall_time_s']:.2f} s  "
            f"rung={lr_elapsed:.2f} s",
            flush=True,
        )
        for i in LEG_PORTS + RING_PORTS:
            family = "leg " if i in LEG_PORTS else "ring"
            surface = leg_surface if i in LEG_PORTS else ring_surface
            volume = leg_volume if i in LEG_PORTS else ring_volume
            terminal = leg_terminal if i in LEG_PORTS else ring_terminal
            record = STEP1_TERMINAL_RATIO if i in LEG_PORTS else RING_TERMINAL_RATIO
            a_c = lr_areas[CONDUCTOR_IFACE + i]
            total = a_c + lr_areas[AIR_IFACE + i] + lr_areas[PHANTOM_IFACE + i]
            v = sum(lr_volumes[t] for t in lr_port_cell_tags[i])
            print(
                f"[GEO-20] {family} P{i}: terminal {lr_counts[CONDUCTOR_IFACE + i]} "
                f"facets {a_c:.9e} m^2 meshed/analytic={a_c / terminal:.9f} "
                f"(record {record})  closure {total / surface:.12f}  "
                f"volume/analytic {v / volume:.12f}",
                flush=True,
            )

    assert abs(lr_v_total / _analytic_box_volume(gap_dy) - 1.0) < EXACT
    assert abs(sum(lr_volumes.values()) / lr_v_total - 1.0) < EXACT
    assert abs(n_cells_lr / LEG_RING_CELL_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"the leg+ring rung meshed {n_cells_lr} cells vs `GEO-20` step 1's record "
        f"{LEG_RING_CELL_RECORD} (ratio {n_cells_lr / LEG_RING_CELL_RECORD:.6f})"
    )
    for i in LEG_PORTS + RING_PORTS:
        surface = leg_surface if i in LEG_PORTS else ring_surface
        volume = leg_volume if i in LEG_PORTS else ring_volume
        terminal = leg_terminal if i in LEG_PORTS else ring_terminal
        record, band = (
            (STEP1_TERMINAL_RATIO, STEP1_TERMINAL_RATIO_BAND)
            if i in LEG_PORTS
            else (RING_TERMINAL_RATIO, RING_TERMINAL_RATIO_BAND)
        )
        a_c = lr_areas[CONDUCTOR_IFACE + i]
        total = a_c + lr_areas[AIR_IFACE + i] + lr_areas[PHANTOM_IFACE + i]
        v = sum(lr_volumes[t] for t in lr_port_cell_tags[i])
        assert abs(total / surface - 1.0) < EXACT, (
            f"port P{i} closure {total / surface:.12f} on the doubly-gapped mesh"
        )
        assert abs(v / volume - 1.0) < EXACT, (
            f"port P{i} volume/analytic {v / volume:.12f} on the doubly-gapped "
            "mesh — the two gap families interact"
        )
        ratio = a_c / terminal
        assert low <= ratio <= high, (
            f"port P{i} terminal ratio {ratio:.9f} outside [{low}, {high}] on the "
            "doubly-gapped mesh"
        )
        assert abs(ratio - record) < band, (
            f"port P{i}'s terminal ratio {ratio:.9f} vs its family record {record} "
            f"(band {band:.0e}); switching the other family on moved a terminal"
        )

    # ---- rung 3: the kwarg off, the inverted control -----------------------
    ctl_mesh, ctl_cells, _, ctl_diag, ctl_elapsed = _build(ring_gap_length=None)
    ctl_tag_set = global_cell_tag_set(ctl_mesh, ctl_cells)
    ctl_expected = {1, 2, 3, *[PORT_LOWER + i for i in LEG_PORTS]}
    n_cells_ctl = ctl_mesh.topology.index_map(3).size_global
    ctl_v_total = _total_volume(ctl_mesh, comm)
    ctl_cad_ratio = (
        _tag_volume(ctl_mesh, ctl_cells, 1, comm)
        / ctl_diag["cad_mass_by_group"]["conductor"]
    )
    # Absence measured, not implied (the `EX-28` clause): run the *same* rebuild
    # on the control mesh and count what it finds on every ring sheet group.
    ctl_sheet_tags = _interface_facet_tags(
        ctl_mesh,
        ctl_cells,
        {SHEET_IFACE + i: (PORT_LOWER + i, PORT_UPPER + i) for i in RING_PORTS},
    )
    ctl_sheet_count = {
        i: _global_facet_count(ctl_mesh, ctl_sheet_tags, SHEET_IFACE + i, comm)
        for i in RING_PORTS
    }

    if comm.rank == 0:
        print(
            f"\n[control] kwarg off (ring_gap_length=None): cells={n_cells_ctl} "
            f"(record {STEP3_CELL_COUNT_RECORD}, ratio "
            f"{n_cells_ctl / STEP3_CELL_COUNT_RECORD:.6f})  meshed/CAD "
            f"conductor={ctl_cad_ratio:.6f} (record {UNCUT_CAD_RATIO_RECORD})  "
            f"rung={ctl_elapsed:.2f} s"
            f"\n[control] cell tags {sorted(ctl_tag_set)} — the four leg boxes and "
            "no ring port tag at all"
            f"\n[control] ring sheet facets found by the same rebuild: "
            + " ".join(f"P{i}={ctl_sheet_count[i]}" for i in RING_PORTS)
            + " (measured absence, not implied)",
            flush=True,
        )

    assert ctl_tag_set == ctl_expected, (
        f"the control rung carries cell tags {sorted(ctl_tag_set)}; the opt-in cut "
        "the rings anyway"
    )
    for i in RING_PORTS:
        assert ctl_sheet_count[i] == 0, (
            f"the control rung has {ctl_sheet_count[i]} facets on ring sheet group "
            f"{SHEET_IFACE + i}; the ring gap is opt-in, and a control that already "
            "carries it would make the identities above say nothing about the kwarg"
        )
    assert abs(n_cells_ctl / STEP3_CELL_COUNT_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"the control meshed {n_cells_ctl} cells vs the uncut record "
        f"{STEP3_CELL_COUNT_RECORD}; the opt-in changed the default geometry"
    )
    assert abs(ctl_cad_ratio - UNCUT_CAD_RATIO_RECORD) < UNCUT_CAD_RATIO_BAND, (
        f"the control keeps {ctl_cad_ratio:.6f} of its CAD conductor mass vs "
        f"`EX-21`'s record {UNCUT_CAD_RATIO_RECORD}"
    )
    assert abs(ctl_v_total / _analytic_box_volume(PORT_BOX_SIZE[1]) - 1.0) < EXACT

    # ---- ParaView ---------------------------------------------------------
    written = {
        "ring cells": _write_cells(mesh, cells, "ring", comm),
        "ring sheets": _write_facets(mesh, sheet_tags, "ring", comm),
        "leg+ring cells": _write_cells(lr_mesh, lr_cells, "legring", comm),
        "uncut cells": _write_cells(ctl_mesh, ctl_cells, "uncut", comm),
    }
    if comm.rank == 0:
        print("\n[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<15s} {path}")
        print(
            "\n[paraview] threshold `CellTags` in each _combined file "
            f"({', '.join(f'{t} = {n}' for t, n in CELL_TAG_NAMES.items())}, "
            "101-104 = the leg boxes, 105-112 / 205-212 = the lower/upper halves"
            "\n           of the eight ring gap boxes); open the ring rung beside "
            "the uncut"
            "\n           control — the end rings are continuous there and broken "
            "by an 8 mm"
            "\n           arc at each mid-azimuth here; then the _facets file for "
            "`mesh_tags`"
            "\n           215-222, the radial sheets seen edge-on at 45 degrees."
            f"\n\nAll identities hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
