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

`PORT-13` **step 2** — the ring column becomes a 4x4 sub-block
=============================================================

Same mesh, same port spec, same terminations: the fixture below now solves
**four** drives over the one 270 728-cell rung — ``P17`` (step 1's), ``P33``
(the top-ring port at ``P17``'s azimuth) and step 1's two opposites
``P25`` / ``P41`` — each located from the *measured* sheet azimuths, never from
an ordinal.  Step 1's three tests keep reading the ``P17`` column and are
unchanged.

**Assembly, no inversion.**  Every port is matched at ``Z_p = z0 = 50 Ohm``, so
the incident wave is non-zero only at the driven port and a drive of port ``j``
reads column ``j`` of ``S`` straight off the generator-convention pair
``V_i = V_src δ_ij − I_i Z_p``::

    S_ij = (V_i − z0 I_i) / V_src

— i.e. ``−2 z0 I_i / V_src`` off the diagonal and ``1 − 2 z0 I_j / V_src`` on
it, from the *same* expression.  ``Z`` is never formed: `PORT-9` leg (d2)'s
per-column normalisation defect lived in the ``Z`` assembly, and four columns
cannot be inverted anyway.

**Anchors (asserted).**

(iii) **reciprocity** of the 4x4 sub-block among the four driven ports,
      ``‖S₄ − S₄ᵀ‖_F/‖S₄‖_F <= RECIPROCITY_BAND`` (1e-3, imported from
      `test_port_lumped_sheet_sweep` exactly as `PORT-9` imports it), with an
      in-run **negative control** for the (d2) defect class: a 1% scale on one
      measured column — an error column passivity cannot see — must push the
      ratio to ``>= 5x`` the band.
(iv)  **column passivity**, a *necessary* condition on a passive network:
      ``Σ_i |S_ij|² <= 1`` on each of the four measured columns, margins
      printed.
(v)   the **top/bottom mirror identity**: the ``P33`` column is the z-mirror of
      the ``P17`` column, every pair ``|S_{σ(i),33}|`` vs ``|S_{i,17}|`` (``σ``
      the ring swap at equal measured azimuth) inside the unmoved
      ``OPPOSITE_SPREAD_BAND``.
(vi)  step 1's power accounting re-asserted on **each** of the four columns at
      the unmoved imported ``POWER_BALANCE_BAND``.

No band is widened or renamed here, and step 1's 0.97-of-band power residual
gets no new band (03:00 2026-09-04 review ruling): a column crossing 1e-2, or a
reciprocity / mirror pair outside its band, is a known-issues entry with the
4x4 printed and nothing loosened.  **Still not** the 32x32 (that is step 3),
no C16 class gate, no sigma_max on a full matrix, no tuning or resonance claim.

Cost: heavy tier, ``-n 8``.  Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-13 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 600 \\
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
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND

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

# Step 2, anchor (iv).  Not a tolerance: `Σ_i |S_ij|² <= 1` is the necessary
# condition a passive network's scattering column obeys exactly, so the ceiling
# is 1 and the margin `1 − Σ` is a measurement, printed, never a band that could
# be widened.  Step 1's printed `P17` currents project to ≈ 0.914 (0.8946² on
# `S_33,17` plus 30 entries near 0.061 and 0.043 on the diagonal), so the
# expected margin is ≈ 8.6%.
COLUMN_PASSIVITY_CEILING = 1.0

# Step 2's in-run negative control for the `PORT-9` leg (d2) defect class — a
# *per-column* normalisation error, which column passivity cannot see (a 1%
# scale moves `Σ|S|²` by 2%, still far under 1) and which reciprocity can.
# Ceiling from step 1's printed column: the sub-block's large entries are the
# two mirror couplings ≈ 0.893, so `‖S₄‖_F ≈ 1.79` and a 1% scale on one column
# moves the ratio by ≈ 0.01·√2·0.893/1.79 ≈ 7.0e-3 = 7x the 1e-3 band.  5x is
# assertable against that ceiling; 10x is not.
CONTROL_COLUMN_SCALE = 1.01
CONTROL_MARGIN_FACTOR = 5.0


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


def _ring_mirror_map(sheets):
    """``σ``: the ring swap at equal **measured** azimuth, as a dict of ordinals.

    The z-mirror of the fixture maps the bottom ring onto the top ring at the
    same azimuth.  Both the ring membership (the sign of the sheet centre's
    ``z``) and the azimuth come off the reconstructed sheets, so a generator
    that renumbered or re-stacked its ring ports fails the bijection assert
    below instead of quietly mirroring the wrong pair.
    """
    bottom = [s for s in sheets if s["z"] < 0.0]
    top = [s for s in sheets if s["z"] > 0.0]
    sigma = {}
    for a in bottom:
        for b in top:
            delta = abs((a["azimuth_deg"] - b["azimuth_deg"] + 180.0) % 360.0 - 180.0)
            if delta < AZIMUTH_MATCH_DEG:
                sigma[a["ordinal"]] = b["ordinal"]
                sigma[b["ordinal"]] = a["ordinal"]
    return sigma


def _solve_one_drive(ctx, driven_id):
    """Solve the fixture with ``driven_id`` at 1 V and all 32 ports at ``z0``.

    Step 1's route verbatim, with only the driven port's identity varying: the
    bilinear side is drive-independent (every sheet is a `z0` termination, L1),
    the linear side carries the impressed source on one sheet (L3).
    """
    comm = ctx["comm"]
    msh, tags_f, omega = ctx["msh"], ctx["tags_f"], ctx["omega"]
    port_sheets = [
        spec.sheet(driven=(spec.port_id == driven_id)) for spec in ctx["specs"]
    ]
    driven_sheet = next(s for s in port_sheets if s.port_id == driven_id)

    comm.Barrier()
    t0 = time.perf_counter()
    fields = ctx["solver"].solve(
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
        sheet.port_id: sheet_terminal_current(msh, tags_f, sheet, fields.e_complex, comm)
        for sheet in port_sheets
    }
    z_p = complex(TERMINATED_PORT_IMPEDANCE_OHM)
    voltages = {
        sheet.port_id: complex(sheet.source_voltage_v) - currents[sheet.port_id] * z_p
        for sheet in port_sheets
    }

    # Column `j` of `S`, from the one expression — the diagonal is not a second
    # convention, it is `V_j = V_src − I_j z0` put through the same formula.
    v_src = complex(driven_sheet.source_voltage_v)
    s_column = {
        pid: (voltages[pid] - z_p * currents[pid]) / v_src for pid in voltages
    }

    kwargs = dict(
        sigma=fields.sigma_field,
        rho=PHANTOM_RHO_KG_PER_M3,
        cell_tags=ctx["cell_tags"],
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
    supplied = 0.5 * float(np.real(v_src * np.conjugate(currents[driven_id])))
    total = phantom + conductor + sum(sheet_powers.values())
    residual = abs(supplied - total) / abs(supplied) if supplied else float("inf")
    blind = (
        abs(supplied - (total - conductor)) / abs(supplied) if supplied else float("inf")
    )

    return {
        "driven_id": driven_id,
        "solve_time": float(t_solve),
        "currents": currents,
        "voltages": voltages,
        "s_column": s_column,
        "v_src": v_src,
        "supplied": supplied,
        "phantom": phantom,
        "conductor": conductor,
        "sheet_total": float(sum(sheet_powers.values())),
        "residual": float(residual),
        "blind": float(blind),
    }


@pytest.fixture(scope="module")
def ring_four_columns():
    """One longitudinal-sheet mesh; **four** drives, four columns of ``S``.

    Step 1 drove one port (``P17``) and is still read, unchanged, out of this
    fixture's ``P17`` column.  Step 2 adds ``P33`` (``P17``'s z-mirror at the
    same measured azimuth) and step 1's two measured opposites ``P25`` / ``P41``
    — four drives over the one mesh, four columns, no ``Z``.
    """
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
    z_p = complex(TERMINATED_PORT_IMPEDANCE_OHM)
    ctx = {
        "comm": comm,
        "msh": msh,
        "tags_f": tags_f,
        "cell_tags": cell_tags,
        "omega": omega,
        "specs": specs,
        # One solver for the four drives: the function space is built once and
        # every drive re-assembles the same terminated bilinear form with a
        # different `L3` sheet, so nothing is carried between columns but the
        # discretisation itself.
        "solver": TimeHarmonicSolver(problem, degree=1),
    }

    # The four drives, every one of them *located*: `P17` (step 1's, the lowest
    # ring-port ordinal), its z-mirror at the same measured azimuth, and step 1's
    # two measured opposites (one per ring).  No ordinal arithmetic anywhere.
    sigma_map = _ring_mirror_map(sheets)
    mirror = sigma_map[driven]
    drive_ordinals = sorted({driven, mirror, *opposite})

    columns = {}
    for ordinal in drive_ordinals:
        columns[f"P{ordinal}"] = _solve_one_drive(ctx, f"P{ordinal}")

    step1 = columns[driven_id]
    currents = step1["currents"]
    voltages = step1["voltages"]
    t_solve = step1["solve_time"]
    phantom, conductor = step1["phantom"], step1["conductor"]
    supplied, residual, blind = step1["supplied"], step1["residual"], step1["blind"]
    sheet_powers = {
        pid: 0.5 * abs(i) ** 2 * float(np.real(z_p)) for pid, i in currents.items()
    }

    # Peak RSS against the 128 G cap: rank-local by construction, summed over the
    # ranks (ru_maxrss is in KiB on Linux), which is the `PORT-11` step 1
    # convention.
    rss_gib = float(
        comm.allreduce(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, op=MPI.SUM)
    ) / (1024.0 * 1024.0)

    if comm.rank == 0:
        print(
            f"\n[PORT-13 step1] 16-leg / 32-ring-port longitudinal fixture: "
            f"{m['n_cells']} cells (record "
            f"{RING_LONGITUDINAL_SCALED_CELL_RECORD}, ratio "
            f"{m['n_cells'] / RING_LONGITUDINAL_SCALED_CELL_RECORD:.6f}), "
            f"orientation {m['diag']['ring_sheet_orientation']!r}, mesh "
            f"{m['diag']['mesh_wall_time_s']:.2f} s, rung {m['elapsed']:.2f} s; "
            f"{len(ring_ports)} ring ports, driven {driven_id} at "
            f"{abs(step1['v_src']):.3f} V, f = "
            f"{FREQUENCY_HZ:.3e} Hz, Z_p = {z_p:.6e} Ohm, degree 1, "
            f"{comm.size} ranks\n"
            f"[PORT-13 step1] PRICE: one solve **{t_solve:.2f} s** wall at -n "
            f"{comm.size} (stop rule {SOLVE_PRICE_STOP_RULE_S:.0f} s; a 32-drive "
            f"sweep projects to {32.0 * t_solve:.0f} s of solve time); summed "
            f"ru_maxrss {rss_gib:.3f} GiB after four drives\n"
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
        print(
            f"\n[PORT-13 step2] four drives over the one mesh: "
            f"{', '.join('P%d' % o for o in drive_ordinals)} "
            f"(driven P{driven}, its z-mirror P{mirror} at the same measured "
            f"azimuth, and the two measured opposites "
            f"{', '.join('P%d' % o for o in opposite)}); solve wall times "
            + ", ".join(
                f"P{o} {columns['P%d' % o]['solve_time']:.2f} s"
                for o in drive_ordinals
            )
            + f"; four-drive total "
            f"{sum(c['solve_time'] for c in columns.values()):.2f} s",
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
        # --- step 2 ---
        "columns": columns,
        "drive_ordinals": drive_ordinals,
        "mirror": mirror,
        "sigma_map": sigma_map,
        "z_p": z_p,
    }


@pytest.fixture(scope="module")
def ring_column(ring_four_columns):
    """Step 1's view of the fixture: the ``P17`` column, keys unchanged.

    Step 1's three tests are not re-scoped by step 2 — they read exactly the
    dictionary they read at `052bd61`, off the same drive.
    """
    return ring_four_columns


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


# ---------------------------------------------------------------------------
# `PORT-13` step 2 — the four columns as a network reading
# ---------------------------------------------------------------------------


def _sub_block(four):
    """The 4x4 ``S`` sub-block among the four driven ports, and its port ids.

    ``S4[i, j]`` is entry ``i`` of the column measured by driving ``j`` — the
    columns are read, never assembled from a ``Z`` and never inverted.
    """
    ids = [f"P{o}" for o in four["drive_ordinals"]]
    s4 = np.array(
        [[four["columns"][pj]["s_column"][pi] for pj in ids] for pi in ids],
        dtype=complex,
    )
    return ids, s4


def _reciprocity_ratio(s4):
    return float(np.linalg.norm(s4 - s4.T, ord="fro") / np.linalg.norm(s4, ord="fro"))


@complex_only
def test_the_four_columns_came_off_one_mesh_and_one_convention(ring_four_columns):
    """Structural for step 2: which four drives, and one ``S`` convention.

    Not the identity — what the identities need in order to mean anything.  The
    four drives must be the *located* ones (step 1's port, its measured z-mirror
    and step 1's two measured opposites), each column must carry all 32 ports,
    and every entry — diagonal included — must come from the single expression
    ``S_ij = (V_i − z0 I_i)/V_src``, which is what the `PORT-9` leg (d2) defect
    class taught: a second convention on the diagonal is invisible to every gate
    below.
    """
    four = ring_four_columns
    sigma_map = four["sigma_map"]
    assert len(sigma_map) == 2 * SCALED_LEG_COUNT, (
        f"the ring mirror map pairs {len(sigma_map)} ports, not the "
        f"{2 * SCALED_LEG_COUNT} a two-ring C16 layout carries"
    )
    by_ord = {s["ordinal"]: s for s in four["sheets"]}
    for i, j in sigma_map.items():
        assert sigma_map[j] == i, f"sigma is not an involution at P{i} -> P{j}"
        assert i != j
        assert by_ord[i]["z"] * by_ord[j]["z"] < 0.0, (
            f"P{i} and P{j} are mirrored onto one another but sit on the same ring"
        )
        delta = abs(
            (by_ord[i]["azimuth_deg"] - by_ord[j]["azimuth_deg"] + 180.0) % 360.0
            - 180.0
        )
        assert delta < AZIMUTH_MATCH_DEG, (
            f"P{i} and P{j} are mirrored but {delta:.9f} deg apart in azimuth"
        )

    assert four["mirror"] == sigma_map[four["driven"]]
    assert len(four["drive_ordinals"]) == 4, (
        f"{four['drive_ordinals']} is not the four-drive set the item pre-registered"
    )
    assert set(four["drive_ordinals"]) == {
        four["driven"],
        four["mirror"],
        *four["opposite"],
    }

    z_p = four["z_p"]
    for pid, col in four["columns"].items():
        assert len(col["s_column"]) == 2 * SCALED_LEG_COUNT
        assert all(
            np.isfinite(s.real) and np.isfinite(s.imag)
            for s in col["s_column"].values()
        )
        for other, s in col["s_column"].items():
            # The one convention, re-derived: `−2 z0 I/V_src` everywhere, plus
            # the unit incident wave on the driven port and nowhere else.
            expected = -2.0 * z_p * col["currents"][other] / col["v_src"]
            if other == pid:
                expected = expected + 1.0
            assert abs(s - expected) <= 1.0e-12 * max(1.0, abs(s)), (
                f"S_{other},{pid} = {s:+.9e} is not the single expression "
                f"(V - z0 I)/V_src = {expected:+.9e}"
            )


@complex_only
def test_the_four_by_four_sub_block_is_reciprocal(ring_four_columns):
    """**Anchor (iii)** — ``‖S₄ − S₄ᵀ‖/‖S₄‖ <= 1e-3``, with the (d2) control.

    Reciprocity is a property of the *physics* (an isotropic, reciprocal medium
    with no gyrotropy), not of the port model, so it is the sharpest available
    check that four independently solved columns belong to one network.  The
    band is `PORT-9`'s own imported ``RECIPROCITY_BAND``, unmoved; a miss is a
    known-issues entry carrying the printed 4x4 and nothing is widened.

    The in-run negative control is the `PORT-9` leg (d2) defect class: a
    per-column normalisation error.  Scaling **one measured column** by 1% is
    invisible to column passivity (it moves ``Σ|S|²`` by 2%, still far below 1)
    and must move this ratio to at least 5x the band.
    """
    four = ring_four_columns
    ids, s4 = _sub_block(four)
    ratio = _reciprocity_ratio(s4)

    control = s4.copy()
    control[:, 0] *= CONTROL_COLUMN_SCALE
    control_ratio = _reciprocity_ratio(control)

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-13 step2] GATE (iii) reciprocity of the 4x4 sub-block "
            f"(band {RECIPROCITY_BAND:.0e}, imported from "
            f"`test_port_lumped_sheet_sweep`, unmoved); rows/cols "
            f"{', '.join(ids)}:",
            flush=True,
        )
        for i, pid in enumerate(ids):
            print(
                f"    {pid:>4s}  "
                + "  ".join(f"{s4[i, j]:+.9e}" for j in range(len(ids))),
                flush=True,
            )
        print(
            f"    ||S4 - S4^T||_F/||S4||_F = {ratio:.6e}  "
            f"({ratio / RECIPROCITY_BAND:.3f}x the band, "
            f"{'INSIDE' if ratio <= RECIPROCITY_BAND else 'MISS'})\n"
            f"    negative control, column {ids[0]} scaled by "
            f"{CONTROL_COLUMN_SCALE:.2f}: {control_ratio:.6e} "
            f"({control_ratio / RECIPROCITY_BAND:.3f}x the band; the item's "
            f"ceiling is ~7x, the bar {CONTROL_MARGIN_FACTOR:.0f}x)",
            flush=True,
        )

    assert ratio <= RECIPROCITY_BAND, (
        f"the 4x4 sub-block over {ids} is asymmetric at {ratio:.6e}, outside the "
        f"pre-stated {RECIPROCITY_BAND:.0e} band — four columns of one reciprocal "
        f"network cannot disagree this much (§9 item 1 negative result: the 4x4 "
        f"into known-issues, band not widened, stop)"
    )
    assert control_ratio >= CONTROL_MARGIN_FACTOR * RECIPROCITY_BAND, (
        f"a {(CONTROL_COLUMN_SCALE - 1.0) * 100:.0f}% per-column normalisation "
        f"error — the `PORT-9` leg (d2) defect class — moves the reciprocity "
        f"ratio only to {control_ratio:.6e}, under the "
        f"{CONTROL_MARGIN_FACTOR:.0f}x{RECIPROCITY_BAND:.0e} bar; the gate above "
        f"is then not sensitive to the defect it exists to catch"
    )


@complex_only
def test_every_measured_column_is_passive(ring_four_columns):
    """**Anchor (iv)** — ``Σ_i |S_ij|² <= 1`` on each of the four columns.

    A necessary condition, not a sufficient one: a passive network scatters no
    more power than it is fed, so no column of ``S`` may have norm above 1.  It
    is exactly the reading a mis-normalised port model fails at O(1), and it
    needs no second solve.  The ceiling is the physical 1, never a widenable
    band; the margins are measurements and are printed.
    """
    four = ring_four_columns
    norms = {
        pid: float(sum(abs(s) ** 2 for s in col["s_column"].values()))
        for pid, col in four["columns"].items()
    }

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-13 step2] GATE (iv) column passivity, "
            f"sum_i |S_ij|^2 <= {COLUMN_PASSIVITY_CEILING:.0f} "
            f"(a necessary condition on a passive network, not a band):",
            flush=True,
        )
        for o in four["drive_ordinals"]:
            pid = f"P{o}"
            print(
                f"    column {pid:>4s}  sum|S|^2 = {norms[pid]:.9f}  margin "
                f"{COLUMN_PASSIVITY_CEILING - norms[pid]:+.9f} "
                f"({(COLUMN_PASSIVITY_CEILING - norms[pid]) * 100:+.4f}%)  "
                f"{'PASSIVE' if norms[pid] <= COLUMN_PASSIVITY_CEILING else 'ACTIVE'}",
                flush=True,
            )

    for o in four["drive_ordinals"]:
        pid = f"P{o}"
        assert norms[pid] > 0.0
        assert norms[pid] <= COLUMN_PASSIVITY_CEILING, (
            f"column {pid} scatters sum_i |S_ij|^2 = {norms[pid]:.9f} > 1: the "
            f"passive 32-port ring network would be delivering more power than "
            f"the generator supplies, which is a port-normalisation defect, not "
            f"a tolerance (§9 item 1 negative result: all four column norms into "
            f"known-issues, stop)"
        )


@complex_only
def test_the_top_and_bottom_ring_columns_are_z_mirrors(ring_four_columns):
    """**Anchor (v)** — the top-ring column is the z-mirror of the bottom one.

    The fixture is symmetric about ``z = 0``, so the ring swap ``σ`` at equal
    measured azimuth is a symmetry of the network: ``S_{σ(i),σ(j)} = S_{i,j}``.
    With ``σ(P17) = P33`` that says every entry of the top-ring column matches
    its partner in the bottom-ring column.  This is an identity between two
    *independently solved* columns — the one check in this module that a second
    solve buys, and the reason step 2 drives the mirror port at all.  The band
    is step 1's unmoved ``OPPOSITE_SPREAD_BAND``.
    """
    four = ring_four_columns
    driven, mirror = four["driven"], four["mirror"]
    sigma_map = four["sigma_map"]
    col_a = four["columns"][f"P{driven}"]["s_column"]
    col_b = four["columns"][f"P{mirror}"]["s_column"]

    pairs = []
    for o in sorted(sigma_map):
        a = abs(col_a[f"P{o}"])
        b = abs(col_b[f"P{sigma_map[o]}"])
        pairs.append((o, sigma_map[o], a, b, abs(a - b) / a if a else float("inf")))
    worst = max(pairs, key=lambda p: p[4])

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-13 step2] GATE (v) the top/bottom mirror identity "
            f"|S_(sigma(i)),P{mirror}| vs |S_i,P{driven}| (band "
            f"{OPPOSITE_SPREAD_BAND * 100:.0f}%, step 1's, unmoved):",
            flush=True,
        )
        for o, so, a, b, rel in pairs:
            print(
                f"    |S_P{o},P{driven}| = {a:.9e}   "
                f"|S_P{so},P{mirror}| = {b:.9e}   rel {rel * 100:8.4f}%"
                + ("   <-- worst" if o == worst[0] else ""),
                flush=True,
            )
        print(
            f"    worst pair P{worst[0]}/P{worst[1]} at {worst[4] * 100:.4f}%  "
            f"{'INSIDE' if worst[4] <= OPPOSITE_SPREAD_BAND else 'MISS'}",
            flush=True,
        )

    assert len(pairs) == 2 * SCALED_LEG_COUNT
    assert worst[4] <= OPPOSITE_SPREAD_BAND, (
        f"the mirror pair P{worst[0]}/P{worst[1]} reads "
        f"|S_P{worst[0]},P{driven}| = {worst[2]:.9e} against "
        f"|S_P{worst[1]},P{mirror}| = {worst[3]:.9e}, {worst[4] * 100:.4f}% apart "
        f"against the unmoved {OPPOSITE_SPREAD_BAND * 100:.0f}% band — the two "
        f"independently solved columns do not carry the fixture's z-mirror "
        f"symmetry (§9 item 1 negative result: the pair table into known-issues, "
        f"band not widened, stop)"
    )


@complex_only
def test_power_accounting_closes_on_all_four_columns(ring_four_columns):
    """**Anchor (vi)** — step 1's conservation identity, on every column.

    One column closing is a solve that balanced; four columns closing on four
    different drives is the port model closing.  The band is the same imported
    ``POWER_BALANCE_BAND`` and it does not move here: the 2026-09-04 03:00
    review ruled explicitly that step 1's 0.97-of-band residual gets **no new
    band**, because it did not shrink from `WF-6` step 1's 9.80e-3 at 116 085
    cells to this rung's 9.68e-3 at 270 728 and so is a term-accounting reading
    rather than an h-effect.  A column crossing 1e-2 is a known-issues entry
    carrying all four residuals.
    """
    four = ring_four_columns

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-13 step2] GATE (vi) power accounting on each of the four "
            f"columns (band {POWER_BALANCE_BAND:.0e}, imported from `WF-6` step 1, "
            f"unmoved):",
            flush=True,
        )
        for o in four["drive_ordinals"]:
            col = four["columns"][f"P{o}"]
            print(
                f"    driven P{o:<2d}  supplied {col['supplied']:.9e} W  "
                f"phantom {col['phantom']:.9e}  conductor {col['conductor']:.9e}  "
                f"32 sheets {col['sheet_total']:.9e}\n"
                f"                residual {col['residual']:.6e} "
                f"({col['residual'] / POWER_BALANCE_BAND:.3f}x the band, margin "
                f"{POWER_BALANCE_BAND - col['residual']:+.6e})  "
                f"{'INSIDE' if col['residual'] <= POWER_BALANCE_BAND else 'MISS'}  "
                f"[conductor-blind control {col['blind']:.6e}, "
                f"{col['blind'] / POWER_BALANCE_BAND:.2f}x]",
                flush=True,
            )

    for o in four["drive_ordinals"]:
        col = four["columns"][f"P{o}"]
        assert col["supplied"] > 0.0, (
            f"driving P{o} the sheet supplies {col['supplied']:.9e} W — a passive "
            "load cannot absorb negative real power"
        )
        assert col["residual"] <= POWER_BALANCE_BAND, (
            f"driving P{o}, power accounting misses by {col['residual']:.6e} of "
            f"the supplied {col['supplied']:.9e} W (phantom {col['phantom']:.9e}, "
            f"conductor {col['conductor']:.9e}, 32 sheets "
            f"{col['sheet_total']:.9e}); band {POWER_BALANCE_BAND:.0e}, unmoved "
            f"(§9 item 1: all four residuals into known-issues, stop)"
        )
        assert col["blind"] > POWER_BALANCE_BAND, (
            f"driving P{o}, dropping the conductor's 1/2 int sigma|E|^2 still "
            f"closes to {col['blind']:.6e}, inside the band — the identity is "
            "then insensitive to a term it is supposed to weigh"
        )
