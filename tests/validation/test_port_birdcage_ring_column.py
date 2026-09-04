"""`PORT-13` step 1 — the first solve on the 16-leg / 32-ring-port layout.

**What this is.**  One lumped-sheet solve on the high-pass birdcage rung
`GEO-20` step 2 built and `GEO-26` step 2 re-emitted with **longitudinal** ring
sheets: 16 legs (uncut), 32 ring-gap ports (two rings x 16 gaps), the phantom
loaded, at `PORT-9`'s 10 MHz, degree 1, the first ring port driven at 1 V and
every other one of the 32 terminated at the same ``Z_p = z0 = 50 Ohm`` `PORT-9`
leg (d) terminates its ports at.

**Why it could not run before.**  `PORT-13`'s first attempt (2026-09-03)
measured that `GEO-20`'s ring sheets are the gap's *transverse* mid-section:
they span ``<= 1.43e-17`` m along ``phi_hat``, the direction the lumped-sheet
port model divides by (``R_s = Z_p·w/h``, ``I = (1/R_s)∫E·ĥ dS / h``,
``E_src = V_src/h``).  ``gap_height_m`` is caller-supplied
(`ports/lumped.py:148,322`) — nothing in `ports/` derives ``h`` from the mesh —
so a solve on that sheet would not have raised; it would have integrated the
*normal* trace of an H(curl) field on an interior facet, which is not a defined
quantity.  `GEO-26` emits the longitudinal sheet instead, and gates it: the
sheet spans the gap **chord** ``ring_port_gap_chord_m`` along ``phi_hat`` at
1.000000000000 and reconstructs at ``chord·w`` at the same twelve digits.  This
module is the first field on it.

**The port spec, as the §9 item pre-registered it.**  ``h`` is the generator's
own ``ring_port_gap_chord_m`` and ``w = A/h`` is measured on the reconstructed
sheet — exactly the convention
`test_port_birdcage_lumped_column.py:286-287` uses for a leg gap (`PORT-9`
step 2b's area-based effective width, never a bounding-box extent).  Both are
printed.  The drive direction is each port's own ``phi_hat``, from its ordinal;
unlike the leg ports, no two ring ports share one.

**Anchors (asserted).**

(i)  the three-way real-power accounting `WF-6` step 1 gate (i) uses, inside
     that gate's own imported ``POWER_BALANCE_BAND`` (1e-2): the driven sheet's
     ``½Re(V_src I*)`` against the phantom's and the conductor's ``½∫σ|E|²`` and
     the 32 sheets' ``½|I|²Re Z_p``.  The domain is PEC-walled, so that list is
     exhaustive.  Its in-run negative control is `WF-6`'s: dropping the
     conductor term must put the residual *outside* the band, so the identity is
     not insensitive to a term it weighs.
(ii) the two ports diametrically opposite the driven one — one per ring, found
     from the **measured** sheet azimuths, not assumed from the ordinal — agree
     to the 5% `PORT-9` C4-class spread, with the full 32-vector of ring-port
     voltages printed for step 2.

**Scope.**  One solve, one identity, one price.  No 32x32, no C16 gate, no
tuning, no resonance and no absolute-accuracy claim: 10 MHz is the port model's
frequency, one column is not a network, and a full S-matrix is 32 solves —
that is step 2, for a review to scope from the price below.

Cost: heavy tier, ``-n 8``.  Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-13 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 570 \\
       mpiexec -n 8 python3 -m pytest tests/environment \\
       tests/validation/test_port_birdcage_ring_column.py -v -s'"
"""

from __future__ import annotations

import resource
import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem, TimeHarmonicSolver
from fem_em_solver.ports.lumped import (
    LumpedSheetPortSpec,
    lumped_port_bilinear_term,
    lumped_port_linear_term,
    sheet_terminal_current,
)
from fem_em_solver.post import mean_sar

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheet_prerequisite import CELL_COUNT_BAND
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.mesh.test_birdcage_port_scaleup import SCALED_LEG_COUNT
from tests.mesh.test_birdcage_ring_gaps_scaleup import _measure_ring, _ring_gap_frame
from tests.mesh.test_birdcage_ring_sheet_orientation import (
    RING_LONGITUDINAL_SCALED_CELL_RECORD,
)
from tests.validation.test_birdcage_b1_plus_map import (
    PHANTOM_RHO_KG_PER_M3,
    POWER_BALANCE_BAND,
)
from tests.validation.test_lossy_sphere_fullwave import SALINE_EPSILON_R, SALINE_SIGMA
from tests.validation.test_port_birdcage_four_port import TERMINATED_PORT_IMPEDANCE_OHM
from tests.validation.test_port_birdcage_lumped_column import (
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)
from tests.validation.test_port_gap_voltage_impedance import (
    FREQUENCY_HZ,
    SIGMA_WIRE_S_PER_M,
)

# Anchor (ii)'s band: the C4-class spread `PORT-9` measured, imported at its
# pre-tightening value **as the §9 item pre-registered it** for this fixture.
# It is deliberately not `ADJACENT_SPREAD_BAND` (0.005): that tightening was
# measured on the *4-leg leg-gap* fixture, where the two adjacent ports are exact
# mirror images of one another about the driven leg.  Nothing on this rung has
# been measured yet, so the item's 5% is the honest first band — and it is a
# band this module may not widen: a miss is a known-issues entry.
OPPOSITE_SPREAD_BAND = 0.05

# The two ports "diametrically opposite" the driven one are found by azimuth,
# to this tolerance in degrees, off the sheet centroids the mesh reports.
AZIMUTH_MATCH_DEG = 1.0e-6

# The item's stop rule, in seconds of solve wall clock: above this the price is
# the deliverable and step 2's 32 solves are not affordable as scoped.  Printed
# with the price, never used to skip an assert.
SOLVE_PRICE_STOP_RULE_S = 900.0


def _driven_and_opposite(azimuth_deg, ring_ports):
    """``(driven ordinal, [the two ordinals 180 deg away])`` from the mesh.

    The azimuths are read off the reconstructed sheets (`_measure_ring` measures
    them with :func:`_sheet_azimuth_deg`), never assumed from the ordinal, so a
    generator that renumbered its ring ports would fail the count assert below
    rather than silently gate the wrong pair.
    """
    driven = min(ring_ports)
    target = (azimuth_deg[driven] + 180.0) % 360.0
    opposite = [
        i
        for i in ring_ports
        if abs((azimuth_deg[i] - target + 180.0) % 360.0 - 180.0) < AZIMUTH_MATCH_DEG
    ]
    return driven, sorted(opposite)


@pytest.fixture(scope="module")
def ring_column():
    """One longitudinal-sheet mesh; one solve, the first ring port driven."""
    comm = MPI.COMM_WORLD

    # `GEO-26` step 2's build, unchanged and imported rather than re-parametrised:
    # 16 legs, ring gaps at `RING_GAP_LENGTH`, longitudinal sheets, `EX-35`'s
    # geometry.  The cell-count control at the bottom of the structural test is
    # what makes that an assertion rather than a hope.
    m = _measure_ring(SCALED_LEG_COUNT, orientation="longitudinal")
    msh = m["mesh"]
    cell_tags = m["cells"]
    tags_f = m["sheet_tags"]
    ring_ports = list(m["ring_ports"])
    layout = m["diag"]["ring_port_layout"]

    tdim = msh.topology.dim
    # Hoisted on every rank before any facet-restricted form (known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    # The pre-registered port spec: `h` is the generator's own chord (the port
    # box's radial cap faces are planar, so the chord — not the arc — is what
    # they deliver), `w = A/h` on the reconstructed sheet.
    chord = float(layout["ring_port_gap_chord_m"])
    sheets = []
    for i in ring_ports:
        area = float(m["sheet_area"][i])
        phi_hat, centre = _ring_gap_frame(i, SCALED_LEG_COUNT)
        sheets.append(
            {
                "ordinal": i,
                "tag": SHEET_IFACE + i,
                "area": area,
                "h": chord,
                "w": area / chord,
                "drive": tuple(float(c) for c in phi_hat),
                "azimuth_deg": float(m["azimuth_deg"][i]),
                "z": float(centre[2]),
            }
        )

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

    driven, opposite = _driven_and_opposite(m["azimuth_deg"], ring_ports)
    driven_id = f"P{driven}"
    specs = [
        LumpedSheetPortSpec(
            port_id=f"P{s['ordinal']}",
            facet_tag=int(s["tag"]),
            port_impedance_ohm=TERMINATED_PORT_IMPEDANCE_OHM,
            gap_height_m=s["h"],
            sheet_width_m=s["w"],
            # Each ring port drives along its **own** `phi_hat`; unlike the leg
            # ports (all ẑ) no two of the 32 share a drive direction.
            drive_direction=s["drive"],
            drive_voltage_v=1.0 + 0.0j,
            interior=True,
        )
        for s in sheets
    ]

    omega = 2.0 * np.pi * float(FREQUENCY_HZ)
    port_sheets = [spec.sheet(driven=(spec.port_id == driven_id)) for spec in specs]
    driven_sheet = next(s for s in port_sheets if s.port_id == driven_id)

    solver = TimeHarmonicSolver(problem, degree=1)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=None,
        project_source=False,
        extra_bilinear_terms=[
            lambda trial, test, _s=sheet: lumped_port_bilinear_term(
                msh, tags_f, _s, trial, test, omega_rad_per_s=omega
            )
            for sheet in port_sheets
        ],
        extra_linear_terms=[
            lambda test, _s=driven_sheet: lumped_port_linear_term(
                msh, tags_f, _s, test, omega_rad_per_s=omega
            )
        ],
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    # Every current is already MPI-reduced inside `sheet_terminal_current`.
    currents = {
        sheet.port_id: sheet_terminal_current(
            msh, tags_f, sheet, fields.e_complex, comm
        )
        for sheet in port_sheets
    }
    z_p = complex(TERMINATED_PORT_IMPEDANCE_OHM)
    voltages = {
        sheet.port_id: complex(sheet.source_voltage_v) - currents[sheet.port_id] * z_p
        for sheet in port_sheets
    }

    kwargs = dict(
        sigma=fields.sigma_field,
        rho=PHANTOM_RHO_KG_PER_M3,
        cell_tags=cell_tags,
        comm=comm,
    )
    phantom = float(
        mean_sar(fields.e_complex, subdomain_ids=PHANTOM_CELL_TAG, **kwargs)[
            "dissipated_power_w"
        ]
    )
    conductor = float(
        mean_sar(fields.e_complex, subdomain_ids=CONDUCTOR_CELL_TAG, **kwargs)[
            "dissipated_power_w"
        ]
    )
    sheet_powers = {
        pid: 0.5 * abs(i) ** 2 * float(np.real(z_p)) for pid, i in currents.items()
    }
    supplied = 0.5 * float(
        np.real(complex(driven_sheet.source_voltage_v) * np.conjugate(currents[driven_id]))
    )

    # Peak RSS against the 128 G cap: rank-local by construction, summed over the
    # ranks (ru_maxrss is in KiB on Linux), which is the `PORT-11` step 1
    # convention.
    rss_gib = float(
        comm.allreduce(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, op=MPI.SUM)
    ) / (1024.0 * 1024.0)

    total = phantom + conductor + sum(sheet_powers.values())
    residual = abs(supplied - total) / abs(supplied) if supplied else float("inf")
    blind = (
        abs(supplied - (total - conductor)) / abs(supplied) if supplied else float("inf")
    )

    if comm.rank == 0:
        print(
            f"\n[PORT-13 step1] 16-leg / 32-ring-port longitudinal fixture: "
            f"{m['n_cells']} cells (record "
            f"{RING_LONGITUDINAL_SCALED_CELL_RECORD}, ratio "
            f"{m['n_cells'] / RING_LONGITUDINAL_SCALED_CELL_RECORD:.6f}), "
            f"orientation {m['diag']['ring_sheet_orientation']!r}, mesh "
            f"{m['diag']['mesh_wall_time_s']:.2f} s, rung {m['elapsed']:.2f} s; "
            f"{len(ring_ports)} ring ports, driven {driven_id} at "
            f"{abs(complex(driven_sheet.source_voltage_v)):.3f} V, f = "
            f"{FREQUENCY_HZ:.3e} Hz, Z_p = {z_p:.6e} Ohm, degree 1, "
            f"{comm.size} ranks\n"
            f"[PORT-13 step1] PRICE: one solve **{t_solve:.2f} s** wall at -n "
            f"{comm.size} (stop rule {SOLVE_PRICE_STOP_RULE_S:.0f} s; step 2's 32 "
            f"solves project to {32.0 * t_solve:.0f} s of solve time); summed "
            f"ru_maxrss {rss_gib:.3f} GiB\n"
            f"[PORT-13 step1] port spec: h = ring_port_gap_chord_m = "
            f"{chord:.9e} m (arc 8.000000000e-03 m), w = A/h from the "
            f"reconstructed sheet, A = {sheets[0]['area']:.9e} m^2 -> w = "
            f"{sheets[0]['w']:.9e} m (C32 w spread "
            f"{(max(s['w'] for s in sheets) - min(s['w'] for s in sheets)) / np.mean([s['w'] for s in sheets]):.3e})",
            flush=True,
        )
        print(
            f"[PORT-13 step1] the 32-vector of ring-port voltages "
            f"(V = V_src - I·Z_p, generator convention), printed for step 2:",
            flush=True,
        )
        for s in sheets:
            pid = f"P{s['ordinal']}"
            v, i_a = voltages[pid], currents[pid]
            print(
                f"    {pid:>4s} ring {'bottom' if s['z'] < 0 else 'top   '} "
                f"azimuth {s['azimuth_deg']:8.3f} deg  V = {v:+.9e} V  "
                f"|V| = {abs(v):.9e}  I = {i_a:+.9e} A  "
                f"h = {s['h']:.9e} m  w = {s['w']:.9e} m"
                + ("   <-- DRIVEN" if pid == f"P{driven}" else "")
                + ("   <-- OPPOSITE" if s["ordinal"] in opposite else ""),
                flush=True,
            )
        print(
            f"[PORT-13 step1] GATE (i) three-way power accounting (band "
            f"{POWER_BALANCE_BAND:.0e}, imported from `WF-6` step 1):\n"
            f"    supplied 1/2 Re(V_src I*) = {supplied:.9e} W\n"
            f"    phantom  1/2 int sigma|E|^2 = {phantom:.9e} W "
            f"({phantom / supplied * 100:.4f}%)\n"
            f"    conductor 1/2 int sigma|E|^2 = {conductor:.9e} W "
            f"({conductor / supplied * 100:.4f}%)\n"
            f"    32 sheets 1/2 |I|^2 Re Z_p = {sum(sheet_powers.values()):.9e} W "
            f"({sum(sheet_powers.values()) / supplied * 100:.4f}%)\n"
            f"    residual |supplied - sum|/supplied = {residual:.6e}  "
            f"{'INSIDE' if residual <= POWER_BALANCE_BAND else 'MISS'}\n"
            f"    negative control, conductor term dropped: {blind:.6e} "
            f"({blind / POWER_BALANCE_BAND:.2f}x the band)",
            flush=True,
        )

    return {
        "cells": int(m["n_cells"]),
        "solve_time": float(t_solve),
        "rss_gib": rss_gib,
        "sheets": sheets,
        "ring_ports": ring_ports,
        "driven": driven,
        "opposite": opposite,
        "currents": currents,
        "voltages": voltages,
        "supplied": supplied,
        "phantom": phantom,
        "conductor": conductor,
        "sheet_total": float(sum(sheet_powers.values())),
        "chord": chord,
        "azimuth_deg": {i: float(m["azimuth_deg"][i]) for i in ring_ports},
    }


@complex_only
def test_the_ring_column_came_off_the_longitudinal_fixture(ring_column):
    """Structural: the mesh, the sheets and the pair the gate reads.

    None of this is the identity; all of it is what the identity needs in order
    to mean anything.  The mesh must be `GEO-26` step 2's longitudinal record
    (not `EX-35`'s transverse 265 621); every one of the 32 sheets must carry the
    pre-registered ``h``/``w``; and the two ports the gate compares must be the
    two the *measured* azimuths put 180 deg from the driven one.
    """
    ratio = ring_column["cells"] / RING_LONGITUDINAL_SCALED_CELL_RECORD
    assert abs(ratio - 1.0) < CELL_COUNT_BAND, (
        f"the solve meshed {ring_column['cells']} cells against `GEO-26` step 2's "
        f"longitudinal record {RING_LONGITUDINAL_SCALED_CELL_RECORD} (ratio "
        f"{ratio:.6f}); this is not the fixture the 32 sheets were gated on"
    )

    sheets = ring_column["sheets"]
    assert len(sheets) == 2 * SCALED_LEG_COUNT, (
        f"{len(sheets)} ring ports, not the {2 * SCALED_LEG_COUNT} the high-pass "
        "layout puts on two rings"
    )
    for s in sheets:
        assert s["h"] > 0.0 and np.isfinite(s["h"])
        assert s["w"] > 0.0 and np.isfinite(s["w"])
        # `w = A/h` on a sheet gated at `chord·w` must reproduce the generator's
        # own box width; a transverse sheet (the blocked fixture) would divide a
        # `w²` area by the chord and land ~25% off.
        assert abs(s["w"] / s["area"] * s["h"] - 1.0) < 1.0e-12

    driven, opposite = ring_column["driven"], ring_column["opposite"]
    assert len(opposite) == 2, (
        f"the ports diametrically opposite {driven} are {opposite}, not the two "
        "(one per ring) a C16 two-ring layout puts 180 deg away"
    )
    az = ring_column["azimuth_deg"]
    for i in opposite:
        delta = abs((az[i] - az[driven] + 180.0) % 360.0 - 180.0)
        assert abs(delta - 180.0) < 1.0e-6, (
            f"P{i} sits {delta:.9f} deg from the driven port, not 180 deg"
        )
    assert driven not in opposite

    currents = ring_column["currents"]
    assert len(currents) == 2 * SCALED_LEG_COUNT
    assert all(np.isfinite(v.real) and np.isfinite(v.imag) for v in currents.values())
    assert abs(currents[f"P{driven}"]) > 0.0, (
        "the driven sheet carries no terminal current — the impressed source did "
        "not reach the form"
    )


@complex_only
def test_power_accounting_closes_on_the_thirty_two_port_drive(ring_column):
    """**Anchor (i)** — the conservation identity, with `WF-6`'s own control.

    The domain is PEC-walled, so real power supplied at the driven sheet has
    nowhere to go but the phantom, the conductor and the 32 sheets.  The band is
    imported from `WF-6` step 1 gate (i) and is never widened here: a miss is a
    known-issues entry with the price, and nothing else moves.
    """
    supplied = ring_column["supplied"]
    assert supplied > 0.0, (
        f"the driven sheet supplies {supplied:.9e} W — a passive load cannot "
        "absorb negative real power, so the generator convention or the terminal "
        "current is wrong"
    )
    total = (
        ring_column["phantom"] + ring_column["conductor"] + ring_column["sheet_total"]
    )
    residual = abs(supplied - total) / abs(supplied)
    assert residual <= POWER_BALANCE_BAND, (
        f"power accounting misses by {residual:.6e} of the supplied "
        f"{supplied:.9e} W (phantom {ring_column['phantom']:.9e}, conductor "
        f"{ring_column['conductor']:.9e}, 32 sheets "
        f"{ring_column['sheet_total']:.9e}); band {POWER_BALANCE_BAND:.0e}"
    )

    # `WF-6`'s in-run negative control, free (no second solve): the conductor
    # term is not decorative.  The §9 item's ceiling argument — a mis-wired or
    # undefined port misses at O(1) — is the same statement one term further out.
    blind = abs(supplied - (total - ring_column["conductor"])) / abs(supplied)
    assert blind > POWER_BALANCE_BAND, (
        f"dropping the conductor's 1/2 int sigma|E|^2 still closes to "
        f"{blind:.6e}, inside the {POWER_BALANCE_BAND:.0e} band — the identity is "
        "then insensitive to a term it is supposed to weigh"
    )


@complex_only
def test_the_two_diametrically_opposite_ring_ports_agree(ring_column):
    """**Anchor (ii)** — the two ports 180 deg from the drive, to 5%.

    The 32-vector itself is printed by the fixture, for step 2 to scope a full
    S-matrix from.  Asserted here is only the item's pre-registered pair
    comparison, in `PORT-9`'s own complex form
    (``|Z₂₁ − Z₄₁|/|Z₂₁|``, here on the port voltages at a single drive, which
    differ from the impedances by the one common factor ``I_driven``).  Both the
    complex and the magnitude-only readings are printed; the complex one is the
    gate, as it is in `PORT-9` leg (c).
    """
    a, b = (f"P{i}" for i in ring_column["opposite"])
    v_a = ring_column["voltages"][a]
    v_b = ring_column["voltages"][b]
    spread = abs(v_a - v_b) / abs(v_a)
    magnitude_spread = abs(abs(v_a) - abs(v_b)) / abs(v_a)

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-13 step1] GATE (ii) the two ports diametrically opposite "
            f"P{ring_column['driven']} (band {OPPOSITE_SPREAD_BAND * 100:.0f}%, "
            f"the `PORT-9` C4-class spread, pre-registered in the §9 item):\n"
            f"    {a} ({ring_column['azimuth_deg'][ring_column['opposite'][0]]:.3f} "
            f"deg)  V = {v_a:+.9e} V  |V| = {abs(v_a):.9e}\n"
            f"    {b} ({ring_column['azimuth_deg'][ring_column['opposite'][1]]:.3f} "
            f"deg)  V = {v_b:+.9e} V  |V| = {abs(v_b):.9e}\n"
            f"    |V_a - V_b|/|V_a| = {spread * 100:.4f}%  "
            f"{'INSIDE' if spread <= OPPOSITE_SPREAD_BAND else 'MISS'}   "
            f"(magnitude-only {magnitude_spread * 100:.4f}%)",
            flush=True,
        )

    assert abs(v_a) > 0.0 and abs(v_b) > 0.0
    assert spread <= OPPOSITE_SPREAD_BAND, (
        f"the two ring ports diametrically opposite the driven one read "
        f"V = {v_a:+.9e} and {v_b:+.9e} V, a spread of {spread * 100:.4f}% "
        f"(magnitude-only {magnitude_spread * 100:.4f}%) against the pre-stated "
        f"{OPPOSITE_SPREAD_BAND * 100:.0f}% band — the solved field does not "
        "carry the layout's symmetry into the two 180-deg ports (§7 `PORT-13` "
        "step 1, negative result: the readings and the price into known-issues, "
        "stop; never widen)"
    )
