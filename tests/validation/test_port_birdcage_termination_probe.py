"""`PORT-9` step 3 leg (d0) — the termination probe on the gapped birdcage.

Leg (c) put the first field on `GEO-18`'s gapped, sheeted birdcage and read
column 1 of ``Z`` off one solve at ``Z_p = 1e6 Ω`` (the two-torus probe value).
Its pre-stated C4 gate held at **0.0159%** — but its own anti-degeneracy control
passed at a discrimination margin of only **1.0060×**: at 1e6 Ω every undriven
leg is *open* at its gap, the driven current has no closed conduction path, and
the three mutuals are the electrostatic division of the ring potentials, nearly
equal by construction.  So the symmetry gate was evidence about the *mesh*, not
about port-to-port coupling (§7 `PORT-9` step 3 leg (c), and the 18:00 review's
reading of it 2026-08-22).

``Z_p`` on a gapped birdcage is therefore **not a numerical knob**: it is the
capacitor the structure needs at every gap to carry current at all.  This module
turns it, once, to the ports' own reference impedance and measures what
separates:

* ``Z_p = 1e6 Ω`` on every port — leg (c)'s control, re-solved here so the run is
  anchored to the record *before* the knob turns;
* ``Z_p = 50 Ω`` on every port — ``REFERENCE_IMPEDANCE_OHM``, the ports' own
  ``z0_ohm``, not an impedance guessed in-slot.

Both solves are on one mesh, P1 driven only, 10 MHz — the port model's
frequency, not a Larmor claim.

**The gate** (pre-stated, §7 leg (d0), scoped by the 18:00 review 2026-08-22):
at 50 Ω the discrimination margin

    ``|Z₃₁ − ½(Z₂₁ + Z₄₁)| / |Z₂₁ − Z₄₁| ≥ 10``

**while** the adjacent spread ``|Z₂₁ − Z₄₁|/|Z₂₁|`` stays ``≤ 5%``.  Leg (c)'s
floor is 1.0060× at 0.0159%, so 10× is a 0.16% separation on the same floor —
reachable rather than wished for.  The spread condition is not decoration: a
margin bought by breaking the layout's C4 symmetry is a mesh finding, not a
result, so both must hold in the same solve.

**Negative controls.**  (1) The 1e6 Ω column reproduces leg (c)'s record to its
printed digits — if it does not, the fixture moved and nothing measured at 50 Ω
is comparable to anything.  (2) ``|I₁|`` at 50 Ω is more than 10× the open
value 9.992734880e-07 A: the termination must have closed a current path, and if
it did not, the sheets are not in the circuit and the margin below means nothing.

**Scope.**  Closes nothing in §2 and does not close step 3, which stays 🟡 until
leg (d)'s 4×4 (reciprocity, passivity, all three circulant classes).  No
resonance, S-parameter, tuning or Larmor claim is made here.  Leg (c)'s module is
untouched — this one adds, so the record-owning tests still run unchanged.

Cost: standard tier, ``-n 2``, one mesh (~21 s) and two solves (~7.6 s each at
leg (c)'s price) plus cold JIT.

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-9-step3d0 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 400 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_birdcage_termination_probe.py -v -s'"
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.io.mesh import _interface_facet_tags
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.lumped import LumpedSheetPortSpec, run_lumped_sheet_port_case

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheets import (
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
    _build,
    _sheet_axes,
)
from tests.mesh.test_birdcage_port_tags import LEG_COUNT
from tests.mesh.test_two_torus_port_facets import _facet_group_area
from tests.mesh.test_two_torus_port_sheet import _sheet_extents, _sheet_facet_count
from tests.validation.test_lossy_sphere_fullwave import SALINE_EPSILON_R, SALINE_SIGMA
from tests.validation.test_port_birdcage_lumped_column import (
    ADJACENT_SPREAD_BAND,
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
    STEP2_CELL_COUNT,
    STEP2_CELL_COUNT_BAND,
    _narrowed_transverse,
    _sheet_bbox_centre,
)
from tests.validation.test_port_gap_voltage_impedance import (
    FREQUENCY_HZ,
    SIGMA_WIRE_S_PER_M,
)
from tests.validation.test_port_lumped_narrowed_sheet import GATED_WIDTH_FRACTION
from tests.validation.test_port_lumped_two_torus import PROBE_PORT_IMPEDANCE_OHM
from tests.validation.test_port_package_sparameters import REFERENCE_IMPEDANCE_OHM

# The two terminations, in the order they are solved: the control first, so the
# run is anchored to leg (c)'s record before the knob turns.
OPEN_PORT_IMPEDANCE_OHM = PROBE_PORT_IMPEDANCE_OHM  # 1e6 Ohm, leg (c)'s value
TERMINATED_PORT_IMPEDANCE_OHM = REFERENCE_IMPEDANCE_OHM  # 50 Ohm, the ports' z0

# Leg (c)'s record — `20260822T213612Z_PORT-9-step3c-rerun.log`, 116 416 cells,
# f = 0.5 sheets, P1 driven, 10 MHz, `-n 2`, reproduced bit-identically across
# that slot's two runs.  Compared here to the digits the log printed (9 decimal
# places = 10 significant figures), which is what "bit-identical" can be checked
# to through a record; the band below is that print precision, not a physics
# tolerance.
LEG_C_I1_A = +9.992734880e-07 + 3.351870842e-09j
LEG_C_Z_COLUMN = np.array(
    [
        +7.157807613e02 - 3.356708736e03j,
        +1.234475890e01 - 1.879647891e03j,
        +1.190817590e01 - 1.879802412e03j,
        +1.231173574e01 - 1.879351468e03j,
    ],
    dtype=np.complex128,
)
LEG_C_REPRODUCTION_BAND = 1.0e-9

# **The gate**, pre-stated at scoping (18:00 review 2026-08-22, §7 `PORT-9` step
# 3 leg (d0)) and never widened: at 50 Ohm the opposite port must sit at least
# this many adjacent-pair spreads away from the adjacent pair's mean.  Leg (c)
# read 1.0060x at 1e6 Ohm.
DISCRIMINATION_MARGIN_FLOOR = 10.0

# Negative control (2): the termination has to close a current path.  Leg (c)'s
# open |I_1| is 9.9927e-07 A; at 50 Ohm the driven current must exceed it by this
# factor, or the sheets are not in the circuit and the margin means nothing.
CURRENT_GAIN_FLOOR = 10.0


def _margin(z_column):
    """``|Z₃₁ − ½(Z₂₁ + Z₄₁)| / |Z₂₁ − Z₄₁|`` and the adjacent spread.

    The margin is taken on the **complex** entries, as leg (d0) was scoped: the
    opposite port's departure from the adjacent pair's mean, measured in units of
    the pair's own disagreement.  Leg (c)'s magnitude-only version of the same
    idea is reported alongside it so the two readings of the record can be
    compared, but the gate is this one.
    """
    _z11, z21, z31, z41 = (complex(v) for v in z_column)
    pair_gap = abs(z21 - z41)
    adjacent_mean = 0.5 * (z21 + z41)
    return {
        "spread": pair_gap / abs(z21),
        "pair_gap": pair_gap,
        "opposite_gap": abs(z31 - adjacent_mean),
        "margin": abs(z31 - adjacent_mean) / pair_gap if pair_gap > 0.0 else np.inf,
        # Leg (c)'s definition, on magnitudes, reported only.
        "margin_legc": (
            abs(abs(z31) - 0.5 * (abs(z21) + abs(z41)))
            / (0.5 * (abs(z21) + abs(z41)))
            / (pair_gap / abs(z21))
            if pair_gap > 0.0
            else np.inf
        ),
    }


@pytest.fixture(scope="module")
def termination_probe():
    """One mesh; two lumped-sheet solves at 1e6 Ω and 50 Ω; both Z columns."""
    comm = MPI.COMM_WORLD
    ports_idx = list(range(1, LEG_COUNT + 1))

    msh, cell_tags, _facet_tags, diag, t_mesh = _build(True)
    tdim = msh.topology.dim
    ncells = int(msh.topology.index_map(tdim).size_global)
    # Hoisted on every rank before any facet-restricted form (known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    halves = {i: (PORT_LOWER + i, PORT_UPPER + i) for i in ports_idx}
    tags_f = _interface_facet_tags(
        msh, cell_tags, {SHEET_IFACE + i: halves[i] for i in ports_idx}
    )

    # Leg (c)'s sheet construction, unchanged: measure each full sheet, name its
    # transverse axis off the measured extents, narrow to step 2b's f = 0.5 with
    # the midpoint filter, then re-measure `w = A/h` on the filtered set.
    geometry = {}
    for i in ports_idx:
        tag = SHEET_IFACE + i
        extents = _sheet_extents(msh, tags_f, tag, comm)
        w_bbox, _h_bbox, _spread = _sheet_axes(extents, diag, i)
        centroid = _sheet_bbox_centre(msh, tags_f, tag, comm)
        geometry[i] = {
            "tag": tag,
            "axis": 0 if extents[0] >= extents[1] else 1,
            "centroid": centroid,
            "w_full": float(w_bbox),
            "azimuth_deg": float(
                np.degrees(np.arctan2(centroid[1], centroid[0])) % 360.0
            ),
        }

    for i in ports_idx:
        g = geometry[i]
        tags_f = _narrowed_transverse(
            msh,
            tags_f,
            g["tag"],
            GATED_WIDTH_FRACTION,
            float(g["centroid"][g["axis"]]),
            g["axis"],
            0.5 * g["w_full"],
        )

    sheets = []
    for i in ports_idx:
        g = geometry[i]
        n_facets = _sheet_facet_count(msh, tags_f, g["tag"], comm)
        assert n_facets > 0, f"sheet {g['tag']}: no owned facets anywhere"
        area = _facet_group_area(msh, tags_f, g["tag"], comm)
        extents = _sheet_extents(msh, tags_f, g["tag"], comm)
        w_bbox, h_bbox, spread = _sheet_axes(extents, diag, i)
        sheets.append(
            {
                **g,
                "facets": int(n_facets),
                "area": float(area),
                "h": float(h_bbox),
                "w": float(area / h_bbox),
                "w_bbox": float(w_bbox),
                "out_of_plane": float(spread),
            }
        )

    def _solve(z_p):
        problem = TimeHarmonicProblem(
            mesh=msh,
            frequency_hz=FREQUENCY_HZ,
            material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
            cell_tags=cell_tags,
            material_map={
                CONDUCTOR_CELL_TAG: HomogeneousMaterial(
                    sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0
                ),
                PHANTOM_CELL_TAG: HomogeneousMaterial(
                    sigma=SALINE_SIGMA, epsilon_r=SALINE_EPSILON_R, mu_r=1.0
                ),
            },
            boundary_condition="pec_zero_tangential_a",
        )
        port_defs = []
        specs = []
        for s in sheets:
            pid = f"P{s['tag'] - SHEET_IFACE}"
            port_defs.append(
                PortDefinition(
                    port_id=pid,
                    positive_tag=int(s["tag"]),
                    negative_tag=CONDUCTOR_CELL_TAG,
                    orientation="leg_gap_axial_plus_z",
                    z0_ohm=REFERENCE_IMPEDANCE_OHM,
                )
            )
            specs.append(
                LumpedSheetPortSpec(
                    port_id=pid,
                    facet_tag=int(s["tag"]),
                    port_impedance_ohm=z_p,
                    gap_height_m=s["h"],
                    sheet_width_m=s["w"],
                    drive_direction=(0.0, 0.0, 1.0),
                    drive_voltage_v=1.0 + 0.0j,
                    interior=True,
                )
            )
        comm.Barrier()
        t0 = time.perf_counter()
        result = run_lumped_sheet_port_case(
            problem, port_defs, specs, facet_tags=tags_f, driven_port_id="P1"
        )
        comm.Barrier()
        t_solve = time.perf_counter() - t0
        i_driven = result.responses["P1"].current_a
        z_column = np.array(
            [result.responses[p.port_id].voltage_v / i_driven for p in port_defs],
            dtype=np.complex128,
        )
        return {
            "z_p": float(z_p),
            "result": result,
            "z_column": z_column,
            "i_driven": complex(i_driven),
            "solve_time": float(t_solve),
            **_margin(z_column),
        }

    # Control first, then the knob.
    solves = {
        "open": _solve(OPEN_PORT_IMPEDANCE_OHM),
        "terminated": _solve(TERMINATED_PORT_IMPEDANCE_OHM),
    }

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step3d0] gapped+sheeted birdcage: {ncells} cells "
            f"(record {STEP2_CELL_COUNT}, ratio {ncells / STEP2_CELL_COUNT:.6f}), "
            f"mesh {diag['mesh_wall_time_s']:.2f} s, rung {t_mesh:.2f} s; "
            f"f = {FREQUENCY_HZ:.3e} Hz, f_width = {GATED_WIDTH_FRACTION}, "
            f"P1 driven; two solves at Z_p = "
            f"{OPEN_PORT_IMPEDANCE_OHM:.6e} / {TERMINATED_PORT_IMPEDANCE_OHM:.6e} "
            f"Ohm",
            flush=True,
        )
        for s in sheets:
            print(
                f"    sheet {s['tag']} (P{s['tag'] - SHEET_IFACE}): azimuth "
                f"{s['azimuth_deg']:7.3f} deg; {s['facets']:5d} facets  "
                f"area {s['area']:.9e} m^2  h = {s['h']:.9e} m  "
                f"w = A/h = {s['w']:.9e} m  out-of-plane "
                f"{s['out_of_plane']:.3e} m",
                flush=True,
            )
        for name, sv in solves.items():
            print(
                f"[PORT-9 step3d0] {name} (Z_p = {sv['z_p']:.6e} Ohm), solve "
                f"{sv['solve_time']:.2f} s wall at -n 2: "
                f"I_1 = {sv['i_driven']:+.9e} A  |I_1| = {abs(sv['i_driven']):.9e} A",
                flush=True,
            )
            for k, z in enumerate(sv["z_column"], start=1):
                print(f"    Z_{k}1 = {z:+.9e} Ohm  |Z| = {abs(z):.9e}", flush=True)
            print(
                f"    adjacent spread |Z21 - Z41|/|Z21| = {sv['spread'] * 100:.4f}%  "
                f"(band {ADJACENT_SPREAD_BAND * 100:.0f}%, "
                f"{'INSIDE' if sv['spread'] <= ADJACENT_SPREAD_BAND else 'MISS'})\n"
                f"    |Z31 - (Z21+Z41)/2| = {sv['opposite_gap']:.9e} Ohm, "
                f"|Z21 - Z41| = {sv['pair_gap']:.9e} Ohm  =>  discrimination "
                f"margin {sv['margin']:.4f}x (floor "
                f"{DISCRIMINATION_MARGIN_FLOOR:.0f}x; leg (c)'s magnitude-only "
                f"reading {sv['margin_legc']:.4f}x, reported)",
                flush=True,
            )

    return {
        "solves": solves,
        "sheets": sheets,
        "cells": ncells,
        "mesh_time": float(t_mesh),
    }


@complex_only
def test_the_probe_solved_the_gated_fixture_through_the_field_route(
    termination_probe,
):
    """Structural: the leg (c) fixture, two real solves, four planar sheets.

    None of this is the gate; all of it is what the gate needs to mean anything.
    """
    assert termination_probe["cells"] > 0
    ratio = termination_probe["cells"] / STEP2_CELL_COUNT
    assert abs(ratio - 1.0) < STEP2_CELL_COUNT_BAND, (
        f"the probe meshed {termination_probe['cells']} cells against `GEO-18` "
        f"step 2's record {STEP2_CELL_COUNT}; this is not the fixture leg (c) "
        "measured, so its record is not comparable"
    )
    for s in termination_probe["sheets"]:
        assert s["out_of_plane"] < 1.0e-12, (
            f"sheet {s['tag']}: out-of-plane spread {s['out_of_plane']:.3e} m — "
            "the filtered facet set is not a plane"
        )
        assert s["w"] < s["w_full"], (
            f"sheet {s['tag']}: A/h = {s['w']:.9e} m is not below the full "
            f"sheet's extent {s['w_full']:.9e} m — the interior-width filter did "
            "not run"
        )
    for name, sv in termination_probe["solves"].items():
        r = sv["result"]
        assert not r.is_placeholder, (
            f"the {name} solve returned is_placeholder=True — it fell back to the "
            "PORT-0 coupling heuristic, so no impedance here came off a field"
        )
        assert len(r.responses) == LEG_COUNT
        assert r.responses["P1"].is_driven
        for pid in ("P2", "P3", "P4"):
            assert not r.responses[pid].is_driven
        assert np.all(np.isfinite(sv["z_column"].real))
        assert np.all(np.isfinite(sv["z_column"].imag))


@complex_only
def test_the_open_control_reproduces_leg_c_before_the_knob_turns(termination_probe):
    """**Negative control (1).**  Z_p = 1e6 Ω reproduces leg (c)'s record.

    Leg (c)'s column was reproduced bit-identically across two runs in its own
    slot; this run must land on the same digits, or the fixture moved and nothing
    measured at 50 Ω is comparable to the record it is being read against.  The
    band is the log's print precision (1e-9 relative), not a physics tolerance —
    no physics band is defined here and none moves.
    """
    sv = termination_probe["solves"]["open"]
    assert sv["z_p"] == pytest.approx(1.0e6)

    i_err = abs(sv["i_driven"] - LEG_C_I1_A) / abs(LEG_C_I1_A)
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d0] control (1): 1e6 Ohm vs leg (c)'s record "
            f"(`20260822T213612Z_PORT-9-step3c-rerun.log`), band "
            f"{LEG_C_REPRODUCTION_BAND:.0e} relative:\n"
            f"    I_1 rel. deviation {i_err:.3e}",
            flush=True,
        )
        for k, (z, z_rec) in enumerate(
            zip(sv["z_column"], LEG_C_Z_COLUMN), start=1
        ):
            print(
                f"    Z_{k}1 {z:+.9e} vs record {z_rec:+.9e}  rel. deviation "
                f"{abs(z - z_rec) / abs(z_rec):.3e}",
                flush=True,
            )

    assert i_err < LEG_C_REPRODUCTION_BAND, (
        f"the open solve's driven current {sv['i_driven']:+.9e} A deviates "
        f"{i_err:.3e} from leg (c)'s recorded {LEG_C_I1_A:+.9e} A — the fixture "
        "moved; the 50 Ohm reading is not comparable to the record"
    )
    for k, (z, z_rec) in enumerate(zip(sv["z_column"], LEG_C_Z_COLUMN), start=1):
        err = abs(z - z_rec) / abs(z_rec)
        assert err < LEG_C_REPRODUCTION_BAND, (
            f"Z_{k}1 = {z:+.9e} Ohm deviates {err:.3e} from leg (c)'s recorded "
            f"{z_rec:+.9e} Ohm against the {LEG_C_REPRODUCTION_BAND:.0e} print-"
            "precision band — this is not leg (c)'s solve"
        )


@complex_only
def test_the_termination_closed_a_current_path(termination_probe):
    """**Negative control (2).**  ``|I₁|`` at 50 Ω > 10× the open value.

    At 1e6 Ω every undriven leg is open at its gap and the driven leg carries
    ≈ 1 µA against a ~3.4 kΩ capacitive self-impedance.  If terminating all four
    gaps at 50 Ω does not raise the driven current by at least an order of
    magnitude, the sheets are not in the circuit and whatever the margin below
    reads is not about port coupling.
    """
    opened = termination_probe["solves"]["open"]
    closed = termination_probe["solves"]["terminated"]
    gain = abs(closed["i_driven"]) / abs(opened["i_driven"])

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d0] control (2): |I_1| "
            f"{abs(opened['i_driven']):.9e} A (open) -> "
            f"{abs(closed['i_driven']):.9e} A (50 Ohm), gain {gain:.4f}x "
            f"against a floor of {CURRENT_GAIN_FLOOR:.0f}x  "
            f"{'PASS' if gain > CURRENT_GAIN_FLOOR else 'FAIL'}",
            flush=True,
        )

    assert gain > CURRENT_GAIN_FLOOR, (
        f"terminating every port at {TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ohm moved "
        f"the driven current only {gain:.4f}x, from "
        f"{abs(opened['i_driven']):.9e} A to {abs(closed['i_driven']):.9e} A, "
        f"against the pre-stated {CURRENT_GAIN_FLOOR:.0f}x floor — the "
        "termination did not close a conduction path, so the sheets are not in "
        "the circuit (§7 `PORT-9` leg (d0), negative control 2)"
    )


@complex_only
def test_fifty_ohm_termination_separates_adjacent_from_opposite_coupling(
    termination_probe,
):
    """**Leg (d0)'s gate.**  Margin ≥ 10× at 50 Ω, C4 spread still ≤ 5%.

    Both conditions in the same solve, both pre-stated (18:00 review 2026-08-22,
    §7 `PORT-9` step 3 leg (d0)), neither widened.  A margin bought by breaking
    the layout's C4 symmetry is a mesh finding, not a pass — which is why the
    spread is gated here and not merely reported.

    Negative result, if the margin misses: the four ports are too weakly coupled
    at 10 MHz for a circulant reading of Z.  Both columns go to §7 and
    known-issues and the leg stops — the review picks the next knob (frequency,
    or a reactive ``Z_p`` at the birdcage's tuning capacitance), never a third
    impedance guessed in-slot.
    """
    sv = termination_probe["solves"]["terminated"]
    control = termination_probe["solves"]["open"]
    assert sv["z_p"] == pytest.approx(REFERENCE_IMPEDANCE_OHM)

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d0] GATE at Z_p = {sv['z_p']:.1f} Ohm "
            f"(margin floor {DISCRIMINATION_MARGIN_FLOOR:.0f}x, spread band "
            f"{ADJACENT_SPREAD_BAND * 100:.0f}%, both pre-stated and unmoved):\n"
            f"    margin  {sv['margin']:.4f}x  "
            f"{'PASS' if sv['margin'] >= DISCRIMINATION_MARGIN_FLOOR else 'MISS'}"
            f"   (control at 1e6 Ohm: {control['margin']:.4f}x)\n"
            f"    spread  {sv['spread'] * 100:.4f}%  "
            f"{'INSIDE' if sv['spread'] <= ADJACENT_SPREAD_BAND else 'MISS'}"
            f"   (control at 1e6 Ohm: {control['spread'] * 100:.4f}%)\n"
            f"    Re Z11 = {sv['z_column'][0].real:+.9e} Ohm (reported, not gated)",
            flush=True,
        )

    assert sv["spread"] <= ADJACENT_SPREAD_BAND, (
        f"at {sv['z_p']:.1f} Ohm the ports adjacent to the driven leg read a "
        f"spread of {sv['spread'] * 100:.4f}% against the pre-stated "
        f"{ADJACENT_SPREAD_BAND * 100:.0f}% band — the termination broke the "
        "layout's C4 symmetry, so any margin it buys is a mesh finding, not a "
        "result"
    )
    assert sv["margin"] >= DISCRIMINATION_MARGIN_FLOOR, (
        f"at {sv['z_p']:.1f} Ohm the opposite port sits "
        f"{sv['opposite_gap']:.9e} Ohm from the adjacent pair's mean against the "
        f"pair's own {sv['pair_gap']:.9e} Ohm disagreement, a discrimination "
        f"margin of {sv['margin']:.4f}x against the pre-stated "
        f"{DISCRIMINATION_MARGIN_FLOOR:.0f}x floor (leg (c) read "
        f"{control['margin']:.4f}x at 1e6 Ohm) — the four ports are too weakly "
        "coupled at this frequency for a circulant reading of Z (§7 `PORT-9` leg "
        "(d0), negative result: both columns to §7 + known-issues, stop; never "
        "widen, and never guess a third impedance in-slot)"
    )
