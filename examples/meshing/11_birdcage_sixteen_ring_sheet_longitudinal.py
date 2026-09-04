"""Example (`EX-45`): the 16-leg longitudinal ring-gap rung, in ParaView.

`GEO-26` step 3 (2026-09-04) gave the 16-leg longitudinal ring-gap rung —
32 ring ports, the sheet the lumped-sheet port model can actually drive
(`mesh:10` / `EX-44` shows the same sheet orientation at 4 legs only) — its
own record band after the 16-leg rung's constrained-diameter terminal
triangulation turned out to be **bistable**, not monostable: the inscribed
triangulation of a terminal disk whose boundary edge must contain a diameter
settles into one of exactly two discrete areas depending on how that
diameter falls against the surrounding air mesh, 10 of the 32 terminals on
the low state. No existing example shows the 32 drivable sheets at once, or
makes that two-state census visible; this one does both, as a mesh + a
diagnostic on the mesh, not a solve.

**One mesh, no transverse control.** `mesh:9` (`EX-35`) already shows the
default (transverse) 32-sheet layout at 16 legs; this example calls
`_measure_ring(SCALED_LEG_COUNT, orientation="longitudinal")` once. Nothing
here claims anything about the transverse orientation.

**It asserts, it does not merely render** (the `ANS-1` rule): every anchor
below is imported from the gate module(s) and read off *this run's own
mesh*, never restated.

* Cell count against `RING_LONGITUDINAL_SCALED_CELL_RECORD` (270 728) at
  `CELL_COUNT_BAND`.
* `_assert_ring_identity_family(m, ..., terminal_intra_band=
  LONGITUDINAL_TERMINAL_BAND[16])` — the whole `GEO-20` step-1 identity
  family (partition, air-box closure, Pappus arcs, terminal ratio band, C32
  sheet spread and top/bottom mirror) plus the chord/`w`/half-volume
  identities the longitudinal mode adds, green at the rung's own measured
  band.
* The terminal-area state census: exactly two states, the low one taken by
  10 of the 32 terminals — `GEO-26` step 3's own record, read off this run.

**Negative control, free (no second mesh).** The largest of the four
azimuth classes' intra-class terminal-area spreads is asserted strictly
above `LONGITUDINAL_TERMINAL_INTRA_BAND` (2.0e-5, the 4-leg rung's
monostable reading) and strictly below `LONGITUDINAL_TERMINAL_BAND[16]`
(2.0e-4) — the 5.0x separation `GEO-26` step 3's own control window
measured, which is the ceiling this measurement allows; no larger factor is
claimed here.

**Mesh only.** No port model, no drive, no solve, no `GEO-20` / `GEO-26`
record moves, no §2 change. A cell-count miss, a bistable-family assertion
failure, a low-state count off 10, or a third terminal state is a wiring
defect or a fresh generator finding respectively — journaled in the `EX-45`
§7 row, nothing widened.

Run it through the example runner::

    ./run_examples.sh -e mesh:11 -n 2 -t 400

Output lands in ``examples/meshing/paraview_output/``: open
``meshing_11_birdcage_sixteen_ring_sheet_longitudinal_combined.xdmf`` and
threshold on ``CellTags`` (1 = conductor, 2 = air, 3 = phantom, 101-116 the
sixteen uncut leg boxes, 117-148 / 217-248 the inner/outer halves of the 32
ring gap boxes, split by the longitudinal sheet at ``u = R``) or on the DG0
field ``RingPortTerminalArea`` (each ring port's own measured terminal area,
broadcast to both its halves, 0 elsewhere) to isolate the low-state ports;
then ``meshing_11_birdcage_sixteen_ring_sheet_longitudinal_facets.xdmf`` for
``mesh_tags`` 227-258, the 32 reconstructed longitudinal sheets.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import fem, io

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
from tests.mesh.test_birdcage_port_scaleup import SCALED_LEG_COUNT  # noqa: E402
from tests.mesh.test_birdcage_port_sheets import (  # noqa: E402
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
)
from tests.mesh.test_birdcage_port_tags import RING_RADIUS  # noqa: E402
from tests.mesh.test_birdcage_port_terminals import CONDUCTOR_IFACE  # noqa: E402
from tests.mesh.test_birdcage_ring_gaps import EXACT, SYMMETRY, _spread  # noqa: E402
from tests.mesh.test_birdcage_ring_gaps_scaleup import (  # noqa: E402
    _assert_ring_identity_family,
    _measure_ring,
    _mirror_pairs,
    _report_safely,
    _terminal_classes,
)
from tests.mesh.test_birdcage_ring_sheet_orientation import (  # noqa: E402
    LONGITUDINAL_TERMINAL_BAND,
    LONGITUDINAL_TERMINAL_INTRA_BAND,
    RING_LONGITUDINAL_SCALED_CELL_RECORD,
    TERMINAL_STATE_TOL,
    _record_ratio,
    _sheet_axes,
    _sheet_extent_along,
    _terminal_area_states,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "meshing_11_birdcage_sixteen_ring_sheet_longitudinal"

# `GEO-26` step 3's own record: 10 of 32 terminals on the low area state
# (`20260904T034052Z_GEO-26.log:26272`). Printed and asserted; not a band.
EXPECTED_LOW_STATE_COUNT = 10
EXPECTED_TERMINAL_COUNT = 2 * SCALED_LEG_COUNT


def _write_cells(mesh, cell_tags, field, comm):
    """The longitudinal mesh + cell tags + the per-port terminal-area field."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        mesh,
        cell_tags,
        {"RingPortTerminalArea": field},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def _write_facets(mesh, facet_tags, comm):
    """The 32 reconstructed longitudinal sheets, on their own tdim-1 grid."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{BASENAME}_facets.xdmf"
    mesh.topology.create_connectivity(mesh.topology.dim - 1, mesh.topology.dim)
    with io.XDMFFile(comm, path, "w") as xdmf:
        xdmf.write_mesh(mesh)
        xdmf.write_meshtags(facet_tags, mesh.geometry)
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path if comm.rank == 0 else None


def _terminal_area_field(m):
    """DG0 cell field: each of the 32 ring ports' own measured terminal area
    (``m["areas"][CONDUCTOR_IFACE + i]``), broadcast to both cell-tag halves
    of that port's box (``PORT_LOWER + i`` and ``PORT_UPPER + i``). Untagged
    cells — the conductor, air, phantom and the 16 uncut leg boxes — read
    0.0; no ring port's terminal area is ever zero, so a threshold at > 0
    isolates the 32 ring-port boxes and the field's own value distinguishes
    the two terminal-area states directly.

    Purely a per-rank relabelling of this rank's own owned cells (the
    `cell_tags_to_function` pattern in `io/paraview_utils.py`) — no collective
    is needed, since every rank only ever touches the cells it owns.
    """
    mesh = m["mesh"]
    cell_tags = m["cells"]
    V0 = fem.functionspace(mesh, ("DG", 0))
    field = fem.Function(V0, name="RingPortTerminalArea")
    field.x.array[:] = 0.0
    cell_dofs = V0.dofmap.list.reshape(-1)

    tag_to_area = {}
    for i in m["ring_ports"]:
        area = float(m["areas"][CONDUCTOR_IFACE + i])
        tag_to_area[PORT_LOWER + i] = area
        tag_to_area[PORT_UPPER + i] = area

    values = cell_tags.values
    mask = np.isin(values, np.fromiter(tag_to_area.keys(), dtype=values.dtype))
    matched_indices = cell_tags.indices[mask]
    matched_areas = np.array(
        [tag_to_area[int(t)] for t in values[mask]], dtype=np.float64
    )
    field.x.array[cell_dofs[matched_indices]] = matched_areas
    field.x.scatter_forward()
    return field


def _sheet_rows(m, leg_count, chord, box_width, v_in, v_out):
    """Per-port ``phi_hat``/``ẑ`` extents, the two half volumes and the
    terminal area — the 32-sheet identity table."""
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
            "v_in_ratio": float(m["volumes"][PORT_LOWER + i]) / v_in,
            "v_out_ratio": float(m["volumes"][PORT_UPPER + i]) / v_out,
            "phi_ratio": _sheet_extent_along(
                msh, m["sheet_tags"], tag, phi_hat, comm
            )
            / chord,
            "z_ratio": _sheet_extent_along(msh, m["sheet_tags"], tag, z_hat, comm)
            / box_width,
            "azimuth": m["azimuth_deg"][i],
            "terminal_area": float(m["areas"][CONDUCTOR_IFACE + i]),
        }
    return rows


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if comm.rank == 0:
        print("=" * 72)
        print(
            "EX-45 — the 16-leg longitudinal ring-gap rung, in ParaView: "
            "32 sheets, the two-state terminal triangulation"
        )
        print("=" * 72)
        print(
            f"\n[geometry] leg_count={SCALED_LEG_COUNT}  ring_radius={RING_RADIUS} m"
            "\n[gate]     tests/mesh/test_birdcage_ring_sheet_orientation.py "
            "(`GEO-26` step 2-3), tests/mesh/test_birdcage_ring_gaps_scaleup.py"
            "\n[scope]    mesh only: no port model, no drive, no solve, no "
            "record moves; no transverse control mesh (`mesh:9` is that "
            "example)",
            flush=True,
        )

    # ---- the rung: 16 legs, both end rings cut, longitudinal sheets --------
    m = _measure_ring(SCALED_LEG_COUNT, orientation="longitudinal")
    problem = _report_safely(f"{SCALED_LEG_COUNT} legs longitudinal", m, comm)

    layout = m["diag"]["ring_port_layout"]
    box_width = float(layout["ring_port_box_width_m"])
    chord = float(layout["ring_port_gap_chord_m"])
    tan_a = float(np.tan(float(layout["ring_gap_half_angle_rad"])))
    port_volume = float(layout["ring_port_volume_m3"])
    sheet_analytic = float(layout["ring_port_sheet_longitudinal_area_m2"])

    # The two closed-form halves, cut at u = R — `GEO-26`'s own derivation,
    # not restated: V(u0..u1) = w·tan(alpha)·(u1^2 - u0^2).
    v_in = box_width * tan_a * (RING_RADIUS * box_width - 0.25 * box_width**2)
    v_out = box_width * tan_a * (RING_RADIUS * box_width + 0.25 * box_width**2)

    rows = _sheet_rows(m, SCALED_LEG_COUNT, chord, box_width, v_in, v_out)

    classes = _terminal_classes(m)
    class_rows = []
    for key, members in classes.items():
        vals = np.array([m["areas"][CONDUCTOR_IFACE + i] for i in members])
        intra = (vals.max() - vals.min()) / vals.mean() if len(members) > 1 else 0.0
        class_rows.append((key, len(members), vals.mean(), intra))
    max_intra = max(r[3] for r in class_rows)

    all_terminals = [float(m["areas"][CONDUCTOR_IFACE + i]) for i in m["ring_ports"]]
    states = _terminal_area_states(all_terminals)
    low_count = states[0][1]

    sheets = np.array([m["sheet_area"][i] for i in m["ring_ports"]])
    mirror = max(
        abs(m["sheet_area"][hi] / m["sheet_area"][lo] - 1.0)
        for lo, hi in _mirror_pairs(SCALED_LEG_COUNT)
    )
    census = "  ".join(f"{a:.9e} m^2 x{n}" for a, n in states)

    if comm.rank == 0:
        print(
            f"\n[EX-45] mesh: {m['n_cells']} cells (record "
            f"{RING_LONGITUDINAL_SCALED_CELL_RECORD}, ratio "
            f"{_record_ratio(m['n_cells'], RING_LONGITUDINAL_SCALED_CELL_RECORD)}), "
            f"mesh {m['diag']['mesh_wall_time_s']:.2f} s, rung {m['elapsed']:.2f} s"
            f"\n[EX-45] chord = {chord:.9e} m, w = {box_width:.9e} m, sheet "
            f"chord*w = {sheet_analytic:.9e} m^2"
            f"\n[EX-45] closed-form halves: V_in = {v_in:.9e} m^3, V_out = "
            f"{v_out:.9e} m^3, sum/ring_port_volume_m3 = "
            f"{(v_in + v_out) / port_volume:.12f}",
            flush=True,
        )
        print(
            f"\n[EX-45] four azimuth-class spreads (intra-class terminal-area "
            f"spread; this rung's band {LONGITUDINAL_TERMINAL_BAND[SCALED_LEG_COUNT]}, "
            f"the 4-leg band {LONGITUDINAL_TERMINAL_INTRA_BAND}):",
            flush=True,
        )
        for key, n, mean_area, intra in class_rows:
            print(
                f"    class '{key}': {n:2d} ports  mean terminal area "
                f"{mean_area:.9e} m^2  intra-class spread {intra:.6e}",
                flush=True,
            )
        print(
            f"\n[EX-45] terminal-area state census ({len(all_terminals)} "
            f"terminals, {TERMINAL_STATE_TOL:.0e} relative clustering): "
            f"{len(states)} state(s)  {census}"
            f"\n[EX-45] terminals on the LOW state: {low_count} of "
            f"{len(all_terminals)} (record: {EXPECTED_LOW_STATE_COUNT} of "
            f"{EXPECTED_TERMINAL_COUNT})",
            flush=True,
        )
        print(
            f"\n[EX-45] C{2 * SCALED_LEG_COUNT} sheet spread = "
            f"{_spread(sheets):.3e}, top/bottom mirror spread = {mirror:.3e} "
            f"(band {SYMMETRY})",
            flush=True,
        )
        print(
            "\n[EX-45] 32-sheet identity table — phi_hat/chord and z/w should "
            "both read 1.000000000000, V_in/V_out/analytic 1.000000000000:",
            flush=True,
        )
        for i in m["ring_ports"]:
            r = rows[i]
            print(
                f"    P{i:2d} ({r['azimuth']:6.3f} deg): phi_hat/chord = "
                f"{r['phi_ratio']:.12f}  z/w = {r['z_ratio']:.12f}  "
                f"V_in/analytic = {r['v_in_ratio']:.12f}  V_out/analytic = "
                f"{r['v_out_ratio']:.12f}  terminal area = "
                f"{r['terminal_area']:.9e} m^2",
                flush=True,
            )

    # ---- the gates, imported -------------------------------------------------
    assert not problem, problem

    assert (
        abs(m["n_cells"] / RING_LONGITUDINAL_SCALED_CELL_RECORD - 1.0) < CELL_COUNT_BAND
    ), (
        f"the {SCALED_LEG_COUNT}-leg longitudinal rung meshed {m['n_cells']} "
        f"cells against `GEO-26`'s record {RING_LONGITUDINAL_SCALED_CELL_RECORD}"
    )

    _assert_ring_identity_family(
        m,
        f"{SCALED_LEG_COUNT} legs longitudinal",
        terminal_intra_band=LONGITUDINAL_TERMINAL_BAND[SCALED_LEG_COUNT],
    )

    assert len(all_terminals) == EXPECTED_TERMINAL_COUNT, (
        f"{len(all_terminals)} ring terminals read against the construction's "
        f"{EXPECTED_TERMINAL_COUNT}"
    )
    assert len(states) == 2, (
        f"the terminal-area state census reads {len(states)} state(s) "
        f"({census}) against `GEO-26` step 3's record of exactly two — a new "
        "generator finding, not a band to widen"
    )
    assert low_count == EXPECTED_LOW_STATE_COUNT, (
        f"{low_count} of {len(all_terminals)} terminals sit on the low area "
        f"state against `GEO-26` step 3's record of "
        f"{EXPECTED_LOW_STATE_COUNT} of {EXPECTED_TERMINAL_COUNT}"
    )

    # The negative control proper, free (no second mesh): the largest
    # intra-class terminal spread on this bistable rung must sit strictly
    # between the unmoved 4-leg (monostable) band and this rung's own
    # (bistable) band — the 5.0x separation `GEO-26` step 3 measured, and the
    # ceiling this measurement allows.
    assert max_intra > LONGITUDINAL_TERMINAL_INTRA_BAND, (
        f"the largest intra-class terminal spread {max_intra:.6e} does not "
        f"exceed the 4-leg (monostable) band {LONGITUDINAL_TERMINAL_INTRA_BAND}; "
        "the 16-leg rung is supposed to be measurably bistable"
    )
    assert max_intra < LONGITUDINAL_TERMINAL_BAND[SCALED_LEG_COUNT], (
        f"the largest intra-class terminal spread {max_intra:.6e} exceeds this "
        f"rung's own band {LONGITUDINAL_TERMINAL_BAND[SCALED_LEG_COUNT]}; a "
        "third triangulation state or a regression, not a wider band"
    )

    # ---- ParaView ------------------------------------------------------------
    field = _terminal_area_field(m)
    written = {
        "combined": _write_cells(m["mesh"], m["cells"], field, comm),
        "facets": _write_facets(m["mesh"], m["sheet_tags"], comm),
    }
    if comm.rank == 0:
        print("\n[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<10s} {path}")
        first = SCALED_LEG_COUNT + 1
        last = SCALED_LEG_COUNT + 2 * SCALED_LEG_COUNT
        print(
            "\n[paraview] threshold `CellTags` in the _combined file (1 = "
            "conductor, 2 = air, 3 = phantom, "
            f"101-{100 + SCALED_LEG_COUNT} = the {SCALED_LEG_COUNT} uncut leg "
            f"boxes, {100 + first}-{100 + last} / {200 + first}-{200 + last} = "
            "the inner/outer halves of the 32 ring gap boxes split by the "
            "longitudinal sheet at u = R); or threshold the DG0 field "
            "`RingPortTerminalArea` (> 0 isolates the 32 ring-port boxes, and "
            "its own two values are the two terminal-area states directly). "
            "In the _facets file threshold `mesh_tags` to "
            f"{210 + first}-{210 + last} for the 32 sheets themselves."
            f"\n\nAll identities hold at {SCALED_LEG_COUNT} legs across "
            f"{len(m['ring_ports'])} ring ports; {low_count} of "
            f"{len(all_terminals)} terminals on the low area state. Total "
            f"elapsed {time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
