"""`PORT-14` step 1 — a complex ``Z_p`` on a lumped sheet, and the
termination-reduction identity on the gated 4-leg birdcage at 10 MHz.

**The claim under test.**  `PORT-9` gave the gapped 4-leg birdcage four lumped
sheets, all at 50 Ω, and a 4×4 S-matrix that passes reciprocity, passivity and
C4 symmetry.  `PORT-14` lets a sheet carry ``Z_p(ω) = R + jωL + 1/(jωC)``, so a
capacitor in a ring gap is a boundary condition rather than a circuit
afterthought.  The gate is an **algebraic identity, no closed form needed**:

    the field-solved 3×3 with port P1 terminated in ``Z_p``
      ==  the circuit reduction of the 50 Ω 4×4 by that same termination
          (``S' = S_aa + S_ab Γ (I − S_bb Γ)⁻¹ S_ba``,
           :func:`~fem_em_solver.ports.circuit.reduce_terminated_ports`)

to ``‖S'_meas − S'_pred‖_F / ‖S'_pred‖_F ≤ 1e-3``, the `PORT-14` §7 entry's
pre-stated band, for a capacitor, an inductor and a resistor each.  The identity
is **exact for a single-mode port**, so the residual is not a discretisation
error in the usual sense — it measures how lumped the sheet actually is.  That
is why the band is not widened if it is missed: a miss is a *finding about the
sheet*, recorded as such.

**Step 1e (2026-09-11).**  Steps 1b–1d measured the miss as the sheet's
single-mode floor (edge fringing, step 1d reading (2)).  Per the 2026-09-06
weekly ruling it is now a (1*) record, ``REDUCTION_FLOOR_F_SMALL``, asserted at
``REDUCTION_FLOOR_RTOL`` at ``-n 2``; ``REDUCTION_BAND`` keeps its value and is
printed beside each residual as a named systematic, not gated.

**What this is not.**  Not an absolute-accuracy claim, not a resonance or tuning
claim, not a coil-loading number: it is a self-consistency identity between two
routes on one fixture at one frequency, exactly as `PORT-9`/`PORT-11` are.  Read
PROJECT_PLAN.md §2 before quoting anything here.  10 MHz by default; step 2
(``FEM_EM_PORT14_STEP2_64MHZ=1``) measures the same identity at 64 MHz on the
same record mesh, printed against the 10 MHz records and not asserted at them.
Step 2b (both frequencies, no flag of its own) fits the termination the field
solve *realised* — ``Γ_eff`` by a closed-form rank-1 projection — and prints it
beside the nominal ``Z_p``; it measures, and registers nothing.

**Construction is imported, never restated** (`ANS-1` rule): the mesh, the
narrowed sheets, the material map and the 50 Ω sweep all come from
:func:`tests.validation.test_port_birdcage_four_port.build_four_port_sweep`, and
the reciprocity/passivity bands come from the modules that pre-stated them.  The
one thing this module builds itself is the terminated solve, which
:func:`~fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep` cannot
express — that function drives *every* port it is given, and here P1 is a load,
not a port of the reduced network.  So the three drives go through
:func:`~fem_em_solver.ports.lumped.run_lumped_sheet_port_case` directly (the
``_solve_one_drive`` precedent of `test_port_birdcage_ring_column.py`) and the
3×3 is assembled from :func:`~fem_em_solver.ports.sparameters._power_waves` at
``z0 = 50`` over the three S ports only.
"""

from __future__ import annotations

import os
import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.ports.circuit import (
    reduce_terminated_ports,
    termination_reflection_coefficient,
)
from fem_em_solver.ports.lumped import (
    LumpedSheetPortSpec,
    run_lumped_sheet_port_case,
    series_rlc_impedance,
)
from fem_em_solver.ports.sparameters import _power_waves

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_leg_gaps import LEG_GAP_LENGTH
from tests.mesh.test_birdcage_port_sheet_prerequisite import CONDUCTOR_RESOLUTION
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.mesh.test_birdcage_port_tags import PORT_BOX_SIZE
from tests.validation.test_port_birdcage_four_port import (
    PASSIVITY_SIGMA_TOLERANCE,
    build_four_port_sweep,
)
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND
from tests.validation.test_port_package_sparameters import REFERENCE_IMPEDANCE_OHM

# The `PORT-14` §7 entry's pre-stated band for the reduction identity, asserted
# as written.  Never widened here: a residual above it is a finding about the
# lumped sheet (§9 item 2's negative-result protocol), not a tolerance to move.
REDUCTION_BAND = 1.0e-3

# --- `PORT-14` step 1e: the F-small single-mode floor as a (1*) record --------
REDUCTION_FLOOR_F_SMALL = {
    "C = 100 pF": 1.595580e-03,
    "L = 1 uH": 3.370512e-03,
    "R = 200 Ohm": 7.249519e-04,
}
"""F-small's measured single-mode floor of the lumped sheet, per element.

Source: ``20260905T020428Z_PORT-14.log:1858, 1865, 1872`` (`-n 2`, the
116 085-cell `GEO-19` record mesh, ``c4_congruent_sheets`` off, 10 MHz).

Registered as a (1*) **record**, not a band, by the 2026-09-06 weekly review's
ruling on `PORT-14` (PROJECT_PLAN §10, Phase 6: "the fixture's measured
single-mode floor is registered as a (1*) record on F-small ... the gate
asserts the residual at that record ... and prints against 1e-3").
``REDUCTION_BAND`` = 1e-3 is *not* re-registered: widening it to fit these
numbers would be fitting the band to the artifact.

What the floor is: step 1d's pre-registered **reading (2)** — no measured
geometric ratio predicts the −1.09 % effective-width offset, so the residual is
a field effect of the sheet (edge fringing, the single-mode residual proper;
``20260906T003627Z_PORT-14-step1d.log:2001–2040``).  It is carried as a **named
systematic of the lumped sheet**, the way `PORT-1` carries its two feed
systematics.  A later change that moves these digits is a change to the sheet
or the fixture and must say so — never a re-record in passing.
"""

# Reproduction tolerance on each record (relative).  The records reproduced to
# the printed digit across the step 1 / 1b ×1 / 1c ε = 0 runs (same mesh, same
# width), so 1e-3 is loose against run-to-run drift and tight against any
# change to the sheet: the cross-element negative control below misses by ~0.5.
REDUCTION_FLOOR_RTOL = 1.0e-3

# --- the records' rank width (the `OPS-41` precedent) -----------------------
# Every reproduction record above was set at `mpiexec -n 2`, the width CI runs.
# Another width is not a reproduction: off it the reading is still printed and
# every non-record assertion still runs, and only the record assertion skips.
# This constant declares the *domain* of the records; it relaxes nothing.
RECORD_RANK_WIDTH = 2

# --- `PORT-14` step 2: the same identity at 64 MHz, measured not recorded ----
# `FEM_EM_PORT14_STEP2_64MHZ` (unset/`0` = off, the default path bit-identical)
# drives the `rlc_termination_cases` fixture at STEP2_FREQUENCY_HZ: both the
# 50 Ohm sweep and `series_rlc_impedance` take it.  `FREQUENCY_HZ` is not
# mutated.  The 10 MHz records above are printed against and then *skipped*
# under the flag — 64 MHz has no record yet (the review rules on these numbers).
STEP2_ENV = "FEM_EM_PORT14_STEP2_64MHZ"
STEP2_FREQUENCY_HZ = 64.0e6

# The 10 MHz 50 Ohm baseline's first column, printed beside the 64 MHz one as
# proof the sweep was rebuilt at the new frequency.  Logged record, restated with
# its source (`20260911T123334Z_PORT-14-step1e.log:1871`): S11, S21.
STEP1E_S11_S21_10MHZ = (
    -3.712480826e-01 + 1.417750480e-01j,
    +4.671024075e-01 - 4.177746779e-02j,
)


def _step2_enabled():
    return os.environ.get(STEP2_ENV, "") not in ("", "0")


def _rlc_frequency_hz():
    return STEP2_FREQUENCY_HZ if _step2_enabled() else FREQUENCY_HZ

# The port terminated in the RLC element.  Index 0 of the 4×4, i.e. `P1`, whose
# 50 Ω column is `PORT-9` leg (d0)'s recorded column.
TERMINATED_PORT_INDEX = 0

# The three elements, one per case.  Values chosen so each is a *different kind*
# of Γ at 10 MHz and all three are far from matched:
#   C = 100 pF  ->  1/(jωC) = −j159.15 Ω, |Γ| = 1 (lossless, all power returns)
#   L = 1 µH    ->  +j62.83 Ω,            |Γ| = 1 (lossless, opposite sign)
#   R = 200 Ω   ->  +200 Ω,               Γ = +0.6 real (lossy, partial)
TERMINATIONS = (
    ("C = 100 pF", {"c_f": 100.0e-12}),
    ("L = 1 uH", {"l_h": 1.0e-6}),
    ("R = 200 Ohm", {"r_ohm": 200.0}),
)

# **Negative control, ceiling first.**  The Γ = 0 prediction is the 50 Ω
# sub-block `S_aa` — i.e. "the termination does nothing".  It must miss the
# measured terminated 3×3 by at least this multiple of the band, but only for a
# termination whose *computed* coupling term Δ reaches CONTROL_DELTA_FLOOR: no
# factor is claimed above the ceiling the 4×4 itself sets.
CONTROL_MISS_FACTOR = 5.0
CONTROL_DELTA_FLOOR = 5.0e-3


def _terminated_three_port(sweep, z_termination):
    """The field-solved 3×3 with P1's sheet carrying ``z_termination``.

    Three solves on the *same* mesh and facet tags as the 50 Ω sweep — only the
    terminated sheet's ``port_impedance_ohm`` differs, so any disagreement with
    the reduction is about the sheet's port model and nothing else.  Each drive
    re-assembles the system (there is no cached matrix on this route).
    """
    port_defs = sweep["port_defs"]
    base_specs = sweep["specs"]
    specs = []
    for idx, spec in enumerate(base_specs):
        impedance = (
            z_termination if idx == TERMINATED_PORT_INDEX else spec.port_impedance_ohm
        )
        specs.append(
            LumpedSheetPortSpec(
                port_id=spec.port_id,
                facet_tag=spec.facet_tag,
                port_impedance_ohm=impedance,
                gap_height_m=spec.gap_height_m,
                sheet_width_m=spec.sheet_width_m,
                drive_direction=spec.drive_direction,
                drive_voltage_v=spec.drive_voltage_v,
                interior=spec.interior,
            )
        )

    kept = [p for i, p in enumerate(port_defs) if i != TERMINATED_PORT_INDEX]
    results = {}
    for port in kept:
        results[port.port_id] = run_lumped_sheet_port_case(
            sweep["problem"],
            port_defs,
            specs,
            facet_tags=sweep["facet_tags"],
            driven_port_id=port.port_id,
            verbose=False,
        )

    # `_assemble_sparameter_matrix`'s body over the *kept* ports only: the
    # terminated sheet is a load, so it contributes no row and no column.
    z0 = float(REFERENCE_IMPEDANCE_OHM)
    s3 = np.zeros((len(kept), len(kept)), dtype=np.complex128)
    for col, driven in enumerate(kept):
        result = results[driven.port_id]
        drive = result.responses[driven.port_id]
        a_drive, _ = _power_waves(drive.voltage_v, drive.current_a, z0)
        assert abs(a_drive) > 0.0, f"incident wave at '{driven.port_id}' vanished"
        for row, recv in enumerate(kept):
            response = result.responses[recv.port_id]
            _, b_recv = _power_waves(response.voltage_v, response.current_a, z0)
            s3[row, col] = b_recv / a_drive
    return s3, [p.port_id for p in kept], results


@pytest.fixture(scope="module")
def rlc_termination_cases():
    """The gated 50 Ω 4×4 plus one terminated 3×3 per element — one mesh, 13 solves."""
    comm = MPI.COMM_WORLD
    frequency_hz = _rlc_frequency_hz()
    sweep = build_four_port_sweep(frequency_hz=frequency_hz)
    cases = []
    for label, element in TERMINATIONS:
        z_term = series_rlc_impedance(frequency_hz, **element)
        comm.Barrier()
        t0 = time.perf_counter()
        measured, kept_ids, results = _terminated_three_port(sweep, z_term)
        comm.Barrier()
        elapsed = time.perf_counter() - t0
        predicted = reduce_terminated_ports(
            sweep["s"], float(REFERENCE_IMPEDANCE_OHM), {TERMINATED_PORT_INDEX: z_term}
        )
        cases.append(
            {
                "label": label,
                "z": z_term,
                "gamma": termination_reflection_coefficient(
                    z_term, float(REFERENCE_IMPEDANCE_OHM)
                ),
                "measured": measured,
                "predicted": predicted,
                "kept_ids": kept_ids,
                "seconds": float(elapsed),
                # Step 2b reads the terminated sheet's current off these.
                "results": results,
            }
        )

    if comm.rank == 0:
        print(
            f"\n[PORT-14 step1] termination-reduction identity at "
            f"f = {frequency_hz:.3e} Hz on the {sweep['cells']}-cell 4-leg fixture; "
            f"terminated port index {TERMINATED_PORT_INDEX} "
            f"(z0 = {REFERENCE_IMPEDANCE_OHM:.6e} Ohm)",
            flush=True,
        )
        if _step2_enabled():
            print(
                f"[PORT-14 step2] {STEP2_ENV} on: f = {frequency_hz:.6e} Hz "
                f"(FREQUENCY_HZ = {FREQUENCY_HZ:.6e} Hz unmutated); the 10 MHz "
                "records are printed against and skipped",
                flush=True,
            )
        for case in cases:
            print(
                f"    {case['label']}: Z_p = {case['z'].real:+.6e}"
                f"{case['z'].imag:+.6e}j Ohm, Gamma = {case['gamma'].real:+.6f}"
                f"{case['gamma'].imag:+.6f}j (|Gamma| = {abs(case['gamma']):.6f}); "
                f"three drives in {case['seconds']:.2f} s wall",
                flush=True,
            )
    return {"sweep": sweep, "cases": cases}


@complex_only
def test_the_fifty_ohm_baseline_reproduces_the_port9_gates(rlc_termination_cases):
    """Anchor 0: the 4×4 this run reduces is `PORT-9`'s gated matrix.

    If the baseline does not reproduce reciprocity and passivity on this run's
    mesh, the reduction has nothing trustworthy to reduce and every residual
    below is meaningless.  Both bands are **imported** from the modules that
    pre-stated them; neither is restated here.
    """
    sweep = rlc_termination_cases["sweep"]
    reciprocity = float(sweep["reciprocity"])
    sigma_max = float(np.max(sweep["sigma"]))
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-14 step1] 50 Ohm baseline: ||S - S^T||/||S|| = "
            f"{reciprocity:.9e} (band {RECIPROCITY_BAND:.0e}); "
            f"sigma_max = {sigma_max:.9f} "
            f"(band 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e})",
            flush=True,
        )
        if _step2_enabled():
            s4 = np.asarray(sweep["s"], dtype=np.complex128)
            for name, now, then in zip(
                ("S11", "S21"), (s4[0, 0], s4[1, 0]), STEP1E_S11_S21_10MHZ
            ):
                print(
                    f"[PORT-14 step2] 50 Ohm {name} at {_rlc_frequency_hz():.3e} Hz = "
                    f"{now.real:+.9e}{now.imag:+.9e}j   10 MHz baseline = "
                    f"{then.real:+.9e}{then.imag:+.9e}j   |diff| = "
                    f"{abs(now - then):.6e}",
                    flush=True,
                )
    assert reciprocity <= RECIPROCITY_BAND, (
        f"the 50 Ohm 4x4 is reciprocal only to {reciprocity:.3e} against the "
        f"imported {RECIPROCITY_BAND:.0e} band — this is not `PORT-9`'s matrix"
    )
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"the 50 Ohm 4x4 has sigma_max = {sigma_max:.9f} > 1 + "
        f"{PASSIVITY_SIGMA_TOLERANCE:.0e}: a passive network cannot"
    )


def _reduction_residuals(cases):
    """``‖S'_meas − S'_pred‖_F / ‖S'_pred‖_F`` per case, keyed by label.

    Both matrices come from the comm-reduced sweep / `_power_waves` route, so the
    number is identical on every rank.
    """
    out = {}
    for case in cases:
        predicted = case["predicted"]
        out[case["label"]] = float(
            np.linalg.norm(case["measured"] - predicted) / np.linalg.norm(predicted)
        )
    return out


@complex_only
def test_the_terminated_solve_matches_the_circuit_reduction(rlc_termination_cases):
    """**The gate.**  Field-solved terminated 3×3 == reduction of the 50 Ω 4×4.

    Step 1e (the 2026-09-06 weekly ruling): each residual is **asserted at its
    F-small record** ``REDUCTION_FLOOR_F_SMALL`` to ``REDUCTION_FLOOR_RTOL``
    relative, and **printed** against the pre-stated ``REDUCTION_BAND`` = 1e-3 as
    a named systematic of the lumped sheet — not gated, and not widened.  Every
    residual is printed before any assertion.  The record assertion runs only
    at ``RECORD_RANK_WIDTH`` (`OPS-41`): another width is not a reproduction.
    """
    comm = MPI.COMM_WORLD
    residuals = _reduction_residuals(rlc_termination_cases["cases"])
    for case in rlc_termination_cases["cases"]:
        case["residual"] = residuals[case["label"]]

    if comm.rank == 0:
        print(
            "[PORT-14 step1e] reduction identity residuals: asserted at the "
            f"F-small record (rtol {REDUCTION_FLOOR_RTOL:.0e}, -n "
            f"{RECORD_RANK_WIDTH} records; this run -n {comm.size}); printed "
            f"against REDUCTION_BAND = {REDUCTION_BAND:.0e} (systematic, not gated):",
            flush=True,
        )
        for case in rlc_termination_cases["cases"]:
            record = REDUCTION_FLOOR_F_SMALL[case["label"]]
            residual = case["residual"]
            print(
                f"    {case['label']:<12s} ||S'_meas - S'_pred||_F/||S'_pred||_F = "
                f"{residual:.6e}   record {record:.6e}   ratio "
                f"{residual / record:.9f}   |ratio - 1| = "
                f"{abs(residual / record - 1.0):.3e}   vs band: "
                f"{residual / REDUCTION_BAND:.6f}x "
                f"({'over' if residual > REDUCTION_BAND else 'under'}; "
                "systematic, not gated)",
                flush=True,
            )
            for row in range(case["measured"].shape[0]):
                meas = "  ".join(f"{v:+.6e}" for v in case["measured"][row])
                pred = "  ".join(f"{v:+.6e}" for v in case["predicted"][row])
                print(f"        meas row {row}: {meas}", flush=True)
                print(f"        pred row {row}: {pred}", flush=True)

    assert set(residuals) == set(REDUCTION_FLOOR_F_SMALL), (
        f"terminations {sorted(residuals)} do not match the records' keys "
        f"{sorted(REDUCTION_FLOOR_F_SMALL)}"
    )
    if _step2_enabled():
        # `PORT-14` step 2e: this window's eps = 0 point, read by step 1d's
        # configuration-D print at 64 MHz (flag off: nothing is stored).
        _STEP2E_EPS0_IN_WINDOW.update(residuals)
        pytest.skip("10 MHz record; 64 MHz has none yet")
    if comm.size != RECORD_RANK_WIDTH:
        pytest.skip(
            f"REDUCTION_FLOOR_F_SMALL records were set at -n {RECORD_RANK_WIDTH}; "
            f"this is -n {comm.size}, which is not a reproduction (OPS-41 "
            "precedent) — readings printed above"
        )
    for label, residual in residuals.items():
        record = REDUCTION_FLOOR_F_SMALL[label]
        miss = abs(residual / record - 1.0)
        assert miss <= REDUCTION_FLOOR_RTOL, (
            f"{label}: the reduction residual {residual:.6e} does not reproduce the "
            f"F-small record {record:.6e} (|ratio - 1| = {miss:.3e} > "
            f"{REDUCTION_FLOOR_RTOL:.0e}). The floor is a (1*) record of the lumped "
            "sheet on the GEO-19 mesh at -n 2: a move is a change to the sheet or "
            "the fixture — report it, do not re-register it in passing "
            "(PROJECT_PLAN §7 PORT-14 step 1e)"
        )


# Pre-registered cross-element pairs for the discrimination control, with the
# miss each one produces on the step 1 log's own digits
# (`20260905T020428Z_PORT-14.log:1858, 1865, 1872`): 1.595580/3.370512 and
# 0.7249519/1.595580.  *Asserted* under §9 rule (e) — same comparison, same
# fixture, backed by that log.
CROSS_ELEMENT_CONTROLS = (
    ("C = 100 pF", "L = 1 uH", 0.527),
    ("R = 200 Ohm", "C = 100 pF", 0.546),
)


@complex_only
def test_a_mis_keyed_floor_record_cannot_reproduce(rlc_termination_cases):
    """**Negative control: the rtol discriminates between elements.**

    Each element's measured residual, held against *another* element's record,
    must miss reproduction by far more than ``REDUCTION_FLOOR_RTOL``.  The two
    pre-registered pairs are asserted at their log-backed misses (0.527 / 0.546
    to ±0.005, i.e. the third printed digit) and ≫ the rtol; every other
    off-diagonal pair is asserted to miss the rtol too.  So a swapped or
    mis-keyed record cannot pass the gate above.  Width-independent: a 0.5
    separation does not ride a 1e-4 rank sensitivity.
    """
    residuals = _reduction_residuals(rlc_termination_cases["cases"])
    pairs = []
    for measured_label, residual in residuals.items():
        for record_label, record in REDUCTION_FLOOR_F_SMALL.items():
            if measured_label != record_label:
                pairs.append(
                    (measured_label, record_label, abs(residual / record - 1.0))
                )

    if MPI.COMM_WORLD.rank == 0:
        print(
            "[PORT-14 step1e] negative control, cross-element reproduction "
            f"(each must miss rtol {REDUCTION_FLOOR_RTOL:.0e}):",
            flush=True,
        )
        backed = {(m, r): v for m, r, v in CROSS_ELEMENT_CONTROLS}
        for measured_label, record_label, miss in pairs:
            note = (
                f"  pre-registered {backed[(measured_label, record_label)]:.3f}"
                if (measured_label, record_label) in backed
                else ""
            )
            print(
                f"    r[{measured_label}] / rec[{record_label}] - 1 | = "
                f"{miss:.6f}   ({miss / REDUCTION_FLOOR_RTOL:.1f}x rtol){note}",
                flush=True,
            )

    if _step2_enabled():
        pytest.skip("10 MHz record; 64 MHz has none yet")
    misses = {(m, r): v for m, r, v in pairs}
    for measured_label, record_label, expected in CROSS_ELEMENT_CONTROLS:
        miss = misses[(measured_label, record_label)]
        assert abs(miss - expected) <= 5.0e-3, (
            f"|r[{measured_label}]/rec[{record_label}] - 1| = {miss:.6f}, not the "
            f"log-backed {expected:.3f}: the residuals no longer order as step 1 "
            "measured them"
        )
    for measured_label, record_label, miss in pairs:
        assert miss > 100.0 * REDUCTION_FLOOR_RTOL, (
            f"r[{measured_label}] reproduces rec[{record_label}] to {miss:.3e}, "
            f"within 100x the {REDUCTION_FLOOR_RTOL:.0e} rtol: the record gate "
            "cannot tell these two elements apart"
        )


@complex_only
def test_the_zero_gamma_control_misses(rlc_termination_cases):
    """**Negative control, ceiling first.**  ``Γ = 0`` (i.e. ``S_aa``) must fail.

    The reduction is only evidence if the termination *does something*: if the
    50 Ω sub-block ``S_aa`` fitted the terminated measurement just as well, the
    gate above would be passing on a network too weakly coupled to notice its own
    load.  So the coupling term's size

        ``Δ = ||S_ab Γ (I − S_bb Γ)⁻¹ S_ba||_F / ||S'||_F``

    is computed **in-run from the 4×4** and printed as the ceiling; the ≥ 5×-band
    miss is asserted only for terminations that reach ``Δ ≥ 5e-3``.  If none
    reaches it, that is the finding — the 4-leg coupling is too weak for this
    control — and no factor is claimed above the computed ceiling.
    """
    sweep = rlc_termination_cases["sweep"]
    s4 = np.asarray(sweep["s"], dtype=np.complex128)
    kept = [i for i in range(s4.shape[0]) if i != TERMINATED_PORT_INDEX]
    s_aa = s4[np.ix_(kept, kept)]

    rows = []
    for case in rlc_termination_cases["cases"]:
        predicted = case["predicted"]
        delta = float(np.linalg.norm(predicted - s_aa) / np.linalg.norm(predicted))
        miss = float(
            np.linalg.norm(case["measured"] - s_aa) / np.linalg.norm(predicted)
        )
        rows.append((case["label"], delta, miss))

    reached = [row for row in rows if row[1] >= CONTROL_DELTA_FLOOR]
    if MPI.COMM_WORLD.rank == 0:
        print(
            "[PORT-14 step1] Gamma = 0 control (ceiling first): Delta is the "
            f"coupling term the 4x4 itself predicts, floor {CONTROL_DELTA_FLOOR:.0e}",
            flush=True,
        )
        for label, delta, miss in rows:
            print(
                f"    {label:<12s} Delta = {delta:.6e}   "
                f"||S'_meas - S_aa||_F/||S'_pred||_F = {miss:.6e}   "
                f"({'asserted' if delta >= CONTROL_DELTA_FLOOR else 'below floor'})",
                flush=True,
            )
        if not reached:
            print(
                "    FINDING: no termination reaches the Delta floor — the 4-leg "
                "coupling is too weak for this control at "
                f"{_rlc_frequency_hz() / 1e6:g} MHz; no factor is "
                "claimed above the computed ceiling",
                flush=True,
            )

    for label, delta, miss in reached:
        assert miss >= CONTROL_MISS_FACTOR * REDUCTION_BAND, (
            f"{label}: the Gamma = 0 prediction S_aa misses the measured "
            f"terminated 3x3 by only {miss:.3e}, under {CONTROL_MISS_FACTOR:g}x the "
            f"{REDUCTION_BAND:.0e} band, even though the 4x4 predicts a coupling "
            f"term Delta = {delta:.3e}. The gate above is then not resolving the "
            "termination and means nothing"
        )


# ---------------------------------------------------------------------------
# `PORT-14` step 2b — the termination the field solve actually realised
# ---------------------------------------------------------------------------
#
# For one terminated port the reduction is rank 1 in the kept block:
# ``S' - S_aa = t * M`` with ``M = S_a1 S_1a`` (outer product) and
# ``t = Gamma/(1 - S11 Gamma)``.  So the least-squares ``t`` against the
# *measured* 3x3 is a closed-form projection, it inverts to
# ``Gamma_eff = t/(1 + S11 t)``, and ``Z_eff = z0 (1 + Gamma_eff)/(1 - Gamma_eff)``
# is the termination the field solve behaves as if it saw.  What the fit cannot
# absorb — the non-rank-1 remainder — is error living in the kept block itself.
# Measures only: no record, no band, no ``Z_p`` correction anywhere.

# Step 2's printed 64 MHz residuals, `20260911T183201Z_PORT-14-step2.log:1891,
# :1898, :1905` (`-n 2`, flag on).  Logged readings restated with their source
# for the reproduction anchor; *not* a registered record (the review owns that).
STEP2_RESIDUALS_64MHZ = {
    "C = 100 pF": 1.354202e-02,
    "L = 1 uH": 5.021261e-04,
    "R = 200 Ohm": 7.445387e-04,
}

# Reproduction rtol on the nominal-Gamma residuals.  The records are printed to
# 7 significant figures (rounding <= 3.7e-7 relative) and the step 2 default
# window reproduced the 10 MHz ones to <= 2.380e-07
# (`20260911T183421Z_PORT-14-step2-default.log:1888, :1895, :1903`).
STEP2B_REPRODUCTION_RTOL = 1.0e-5

# Anchor (a): the fitter recovers Z_p from the exact reduction (C2).
STEP2B_RECOVERY_RTOL = 1.0e-9
# Anchor (b): it follows a 1 % shift in the termination rather than echoing Z_p.
STEP2B_SENSITIVITY_FACTOR = 1.01
STEP2B_SENSITIVITY_TOL = 1.0e-6
# Negative control: a residual held against the *other* frequency's reading must
# miss the reproduction rtol by more than this multiple.  Asserted, backed by
# step 2's × record column (`…183201Z_PORT-14-step2.log:1891, :1898, :1905`):
# the tightest pair is R at |1.027018 - 1| = 2.7e-2, i.e. 2 700x the rtol.
STEP2B_CONTROL_MISS_FACTOR = 100.0


def _realised_termination(s4, measured, z0, index=TERMINATED_PORT_INDEX):
    """Fit the single termination that best explains ``measured``, all numpy.

    ``s4`` is the 50 Ohm N×N at the real ``z0``; ``measured`` is the (N−1)×(N−1)
    with port ``index`` terminated, kept ports in ascending index order (the
    order :func:`reduce_terminated_ports` returns).  Returns ``t``,
    ``gamma_eff``, ``z_eff`` and the absolute Frobenius norm of the non-rank-1
    remainder ``S'_meas − S_aa − t M``.
    """
    matrix = np.asarray(s4, dtype=np.complex128)
    kept = [i for i in range(matrix.shape[0]) if i != index]
    s_aa = matrix[np.ix_(kept, kept)]
    m = np.outer(matrix[kept, index], matrix[index, kept])
    d = np.asarray(measured, dtype=np.complex128) - s_aa
    # `np.vdot` conjugates its first argument: <M, D>/<M, M> is the projection.
    t = complex(np.vdot(m, d) / np.vdot(m, m))
    gamma_eff = t / (1.0 + complex(matrix[index, index]) * t)
    z_eff = float(z0) * (1.0 + gamma_eff) / (1.0 - gamma_eff)
    return {
        "t": t,
        "gamma_eff": complex(gamma_eff),
        "z_eff": complex(z_eff),
        "remainder_fro": float(np.linalg.norm(d - t * m)),
    }


def _spread_note(values):
    """max|x|/min|x| and whether the signs agree, for the predicted readings."""
    mags = [abs(v) for v in values]
    signs = {np.sign(v) for v in values if v != 0.0}
    ratio = max(mags) / min(mags) if min(mags) > 0.0 else float("inf")
    return f"max/min |.| = {ratio:.4f}, signs {'agree' if len(signs) <= 1 else 'DIFFER'}"


@complex_only
def test_step2b_the_realised_termination_is_printed(rlc_termination_cases):
    """**`PORT-14` step 2b — fit ``Γ_eff``, print ``ΔZ``; three anchors asserted.**

    (a) The fitter returns ``Z_p`` from the exact reduction to 1e-9; (b) it
    returns ``1.01·Z_p`` from the reduction at ``1.01·Z_p`` to 1e-6, so it does
    not echo the nominal value; (c) at ``RECORD_RANK_WIDTH`` the nominal-Γ
    residuals reproduce this frequency's reading to 1e-5 (step 2's 64 MHz
    residuals under the flag, ``REDUCTION_FLOOR_F_SMALL`` without it).  Negative
    control: held against the other frequency's reading, every residual misses
    by > 100× that rtol.  Everything else is printed, never asserted.
    """
    comm = MPI.COMM_WORLD
    sweep = rlc_termination_cases["sweep"]
    cases = rlc_termination_cases["cases"]
    s4 = np.asarray(sweep["s"], dtype=np.complex128)
    z0 = float(REFERENCE_IMPEDANCE_OHM)
    frequency_hz = _rlc_frequency_hz()
    omega = 2.0 * np.pi * frequency_hz
    step2 = _step2_enabled()
    reading = STEP2_RESIDUALS_64MHZ if step2 else REDUCTION_FLOOR_F_SMALL
    other = REDUCTION_FLOOR_F_SMALL if step2 else STEP2_RESIDUALS_64MHZ
    terminated_id = sweep["port_defs"][TERMINATED_PORT_INDEX].port_id
    nominal = _reduction_residuals(cases)

    rows = []
    for case in cases:
        label = case["label"]
        z_p = complex(case["z"])
        exact = _realised_termination(
            s4, reduce_terminated_ports(s4, z0, {TERMINATED_PORT_INDEX: z_p}), z0
        )
        shifted = _realised_termination(
            s4,
            reduce_terminated_ports(
                s4, z0, {TERMINATED_PORT_INDEX: STEP2B_SENSITIVITY_FACTOR * z_p}
            ),
            z0,
        )
        fit = _realised_termination(s4, case["measured"], z0)
        dz = fit["z_eff"] - z_p
        currents = []
        for driven_id in case["kept_ids"]:
            responses = case["results"][driven_id].responses
            if terminated_id in responses:
                currents.append(
                    (
                        driven_id,
                        abs(responses[terminated_id].current_a)
                        / abs(responses[driven_id].current_a),
                    )
                )
        rows.append(
            {
                "label": label,
                "z_p": z_p,
                "gamma": complex(case["gamma"]),
                "recovery": abs(exact["z_eff"] / z_p - 1.0),
                "sensitivity": abs(shifted["z_eff"] / z_p - STEP2B_SENSITIVITY_FACTOR),
                "fit": fit,
                "dz": dz,
                "l_series_h": dz.imag / omega,
                "rel": fit["z_eff"] / z_p - 1.0,
                "kappa": dz / (z_p - z0),
                "remainder": fit["remainder_fro"] / float(np.linalg.norm(case["predicted"])),
                "nominal": nominal[label],
                "currents": currents,
            }
        )

    if comm.rank == 0:
        print(
            f"\n[PORT-14 step2b] realised termination at f = {frequency_hz:.6e} Hz "
            f"(omega = {omega:.6e} rad/s), terminated port '{terminated_id}', "
            f"z0 = {z0:.6e} Ohm. Printed, not asserted, except anchors (a)-(c):",
            flush=True,
        )
        for row in rows:
            fit = row["fit"]
            print(
                f"    {row['label']:<12s} Gamma = {row['gamma'].real:+.9f}"
                f"{row['gamma'].imag:+.9f}j   Gamma_eff = {fit['gamma_eff'].real:+.9f}"
                f"{fit['gamma_eff'].imag:+.9f}j   |Gamma_eff| = "
                f"{abs(fit['gamma_eff']):.9f}",
                flush=True,
            )
            print(
                f"        Z_p = {row['z_p'].real:+.9e}{row['z_p'].imag:+.9e}j Ohm   "
                f"Z_eff = {fit['z_eff'].real:+.9e}{fit['z_eff'].imag:+.9e}j Ohm",
                flush=True,
            )
            print(
                f"        dZ = Z_eff - Z_p = {row['dz'].real:+.9e} (Re) "
                f"{row['dz'].imag:+.9e} (Im) Ohm   Im dZ/omega = "
                f"{row['l_series_h']:+.9e} H   Z_eff/Z_p - 1 = "
                f"{row['rel'].real:+.9e}{row['rel'].imag:+.9e}j "
                f"(|.| = {abs(row['rel']):.9e})",
                flush=True,
            )
            print(
                f"        non-rank-1 remainder = {row['remainder']:.6e}   nominal "
                f"residual = {row['nominal']:.6e}   remainder/nominal = "
                f"{row['remainder'] / row['nominal']:.6f}   t = "
                f"{fit['t'].real:+.9e}{fit['t'].imag:+.9e}j",
                flush=True,
            )
            if row["currents"]:
                print(
                    "        |I_" + terminated_id + "|/|I_drive| = "
                    + "  ".join(f"{did}: {ratio:.9e}" for did, ratio in row["currents"]),
                    flush=True,
                )
            else:
                print(f"        |I_{terminated_id}|/|I_drive|: not exposed", flush=True)
            print(
                f"        anchor (a) |Z_eff/Z_p - 1| on the exact reduction = "
                f"{row['recovery']:.3e} (<= {STEP2B_RECOVERY_RTOL:.0e});   anchor (b) "
                f"|Z_eff/Z_p - {STEP2B_SENSITIVITY_FACTOR:g}| on the x"
                f"{STEP2B_SENSITIVITY_FACTOR:g} reduction = {row['sensitivity']:.3e} "
                f"(<= {STEP2B_SENSITIVITY_TOL:.0e})",
                flush=True,
            )
        print(
            "    predicted (never asserted): series inductance Im dZ/omega across "
            "C/L/R: " + _spread_note([row["l_series_h"] for row in rows])
            + ";   |Z_eff/Z_p - 1| across C/L/R: "
            + _spread_note([abs(row["rel"]) for row in rows]),
            flush=True,
        )
        # Post-hoc, printed only: registered by the 2026-09-11 21:00 slot after
        # its first two windows read Re dZ ~ -0.53 Ohm on C and L and +1.59 Ohm
        # on R, i.e. dZ = kappa (Z_p - z0) with one kappa ~ 1.06e-2.  Complex
        # least squares over the three elements; per-element kappa beside it.
        v = np.array([row["z_p"] - z0 for row in rows], dtype=np.complex128)
        dzs = np.array([row["dz"] for row in rows], dtype=np.complex128)
        kappa = complex(np.vdot(v, dzs) / np.vdot(v, v))
        print(
            f"    post-hoc (printed only): dZ = kappa (Z_p - z0), pooled kappa = "
            f"{kappa.real:+.9e}{kappa.imag:+.9e}j",
            flush=True,
        )
        for row, vk, dzk in zip(rows, v, dzs):
            print(
                f"        {row['label']:<12s} kappa_k = dZ/(Z_p - z0) = "
                f"{row['kappa'].real:+.9e}{row['kappa'].imag:+.9e}j   "
                f"|dZ - kappa (Z_p - z0)|/|dZ| = {abs(dzk - kappa * vk) / abs(dzk):.3e}",
                flush=True,
            )
        print(
            f"    reproduction (c) against {'step 2 64 MHz' if step2 else '10 MHz record'} "
            f"(rtol {STEP2B_REPRODUCTION_RTOL:.0e}, -n {RECORD_RANK_WIDTH} only; this "
            f"run -n {comm.size}); control against "
            f"{'10 MHz record' if step2 else 'step 2 64 MHz'} (> "
            f"{STEP2B_CONTROL_MISS_FACTOR:g}x rtol):",
            flush=True,
        )
        for row in rows:
            label = row["label"]
            print(
                f"    {label:<12s} nominal {row['nominal']:.6e}   reading "
                f"{reading[label]:.6e} |ratio - 1| = "
                f"{abs(row['nominal'] / reading[label] - 1.0):.3e}   other "
                f"{other[label]:.6e} |ratio - 1| = "
                f"{abs(row['nominal'] / other[label] - 1.0):.3e} "
                f"({abs(row['nominal'] / other[label] - 1.0) / STEP2B_REPRODUCTION_RTOL:.1f}x rtol)",
                flush=True,
            )

    for row in rows:
        assert row["recovery"] <= STEP2B_RECOVERY_RTOL, (
            f"{row['label']}: the fitter returns Z_eff/Z_p - 1 = {row['recovery']:.3e} "
            f"on the exact (C2) reduction, above {STEP2B_RECOVERY_RTOL:.0e} — the "
            "fitter or reduce_terminated_ports is wrong (step 2b: known-issues, stop)"
        )
        assert row["sensitivity"] <= STEP2B_SENSITIVITY_TOL, (
            f"{row['label']}: fed the reduction at {STEP2B_SENSITIVITY_FACTOR:g} Z_p "
            f"the fitter misses {STEP2B_SENSITIVITY_FACTOR:g} by {row['sensitivity']:.3e} "
            f"> {STEP2B_SENSITIVITY_TOL:.0e} — it does not follow the termination"
        )
    for row in rows:
        miss = abs(row["nominal"] / other[row["label"]] - 1.0)
        assert miss > STEP2B_CONTROL_MISS_FACTOR * STEP2B_REPRODUCTION_RTOL, (
            f"{row['label']}: the residual {row['nominal']:.6e} reproduces the other "
            f"frequency's reading {other[row['label']]:.6e} to {miss:.3e}, within "
            f"{STEP2B_CONTROL_MISS_FACTOR:g}x the rtol — the reproduction anchor "
            "cannot tell the two frequencies apart"
        )
    if comm.size != RECORD_RANK_WIDTH:
        pytest.skip(
            f"step 2b's reproduction readings were set at -n {RECORD_RANK_WIDTH}; "
            f"this is -n {comm.size} — readings printed above"
        )
    for row in rows:
        miss = abs(row["nominal"] / reading[row["label"]] - 1.0)
        assert miss <= STEP2B_REPRODUCTION_RTOL, (
            f"{row['label']}: the nominal-Gamma residual {row['nominal']:.6e} does "
            f"not reproduce {reading[row['label']]:.6e} (|ratio - 1| = {miss:.3e} > "
            f"{STEP2B_REPRODUCTION_RTOL:.0e})"
        )


# ---------------------------------------------------------------------------
# `PORT-14` step 1b — does the reduction residual fall with sheet resolution?
# ---------------------------------------------------------------------------
#
# Step 1's residuals ordered by |Gamma| (1.6e-3 and 3.4e-3 at |Gamma| = 1,
# 7.2e-4 at |Gamma| = 0.6), which is what you would see if total reflection
# re-excites the sheet's non-single-mode content.  That hypothesis predicts the
# residual **falls with sheet resolution**.  This block measures exactly that on
# refined rungs of the same fixture: the mesh's `conductor_resolution` is scaled
# by a factor read from the environment, so the **gate rung (factor 1) above is
# untouched** — no rung here runs unless the env var is set.
#
# Nothing about the residual is asserted here (`REDUCTION_BAND` stays 1e-3 and
# the residual is only printed): the residuals are printed beside step 1's
# 116 085-cell record.  What **is** asserted is that the rung is a valid 4x4 at
# all (reciprocity and passivity, both imported and unmoved), that refining
# actually refined (cell count strictly above the record for a factor < 1), and
# the same ceiling-first Gamma = 0 control step 1 ran.
STEP1B_FACTOR_ENV = "FEM_EM_PORT14_CONDUCTOR_RESOLUTION_FACTOR"

# Step 1's printed record, `20260905T020428Z_PORT-14.log`.  The cell count is
# restated as the comparison line for the printout; the residuals are taken from
# step 1e's `REDUCTION_FLOOR_F_SMALL` (lossless pair only — the resistor stays
# step 1's business, and `STEP1B_TERMINATIONS` below filters on these keys).
STEP1_CELL_RECORD = 116085
STEP1_RESIDUAL_RECORD = {
    label: REDUCTION_FLOOR_F_SMALL[label] for label in ("C = 100 pF", "L = 1 uH")
}

# The two lossless terminations — |Gamma| = 1, the worst pair — taken from the
# gate's own tuple so no value is restated.  The resistor is step 1's business.
STEP1B_TERMINATIONS = tuple(
    entry for entry in TERMINATIONS if entry[0] in STEP1_RESIDUAL_RECORD
)


def _step1b_factor():
    raw = os.environ.get(STEP1B_FACTOR_ENV, "")
    if not raw:
        return None
    return float(raw)


@pytest.fixture(scope="module")
def refined_rung_cases():
    """One refined rung: the 50 Ohm 4x4 (4 solves) plus C and L terminated (6)."""
    factor = _step1b_factor()
    if factor is None:
        pytest.skip(
            f"{STEP1B_FACTOR_ENV} unset — `PORT-14` step 1b's refined rungs run "
            "only when a slot asks for one, so the gate rung is untouched"
        )
    comm = MPI.COMM_WORLD
    h_c = factor * CONDUCTOR_RESOLUTION

    comm.Barrier()
    t_sweep0 = time.perf_counter()
    sweep = build_four_port_sweep(frequency_hz=FREQUENCY_HZ, conductor_resolution=h_c)
    comm.Barrier()
    baseline_seconds = time.perf_counter() - t_sweep0

    cases = []
    for label, element in STEP1B_TERMINATIONS:
        z_term = series_rlc_impedance(FREQUENCY_HZ, **element)
        comm.Barrier()
        t0 = time.perf_counter()
        measured, kept_ids, _results = _terminated_three_port(sweep, z_term)
        comm.Barrier()
        elapsed = time.perf_counter() - t0
        predicted = reduce_terminated_ports(
            sweep["s"], float(REFERENCE_IMPEDANCE_OHM), {TERMINATED_PORT_INDEX: z_term}
        )
        residual = float(
            np.linalg.norm(measured - predicted) / np.linalg.norm(predicted)
        )
        cases.append(
            {
                "label": label,
                "z": z_term,
                "gamma": termination_reflection_coefficient(
                    z_term, float(REFERENCE_IMPEDANCE_OHM)
                ),
                "measured": measured,
                "predicted": predicted,
                "residual": residual,
                "kept_ids": kept_ids,
                "seconds": float(elapsed),
            }
        )

    return {
        "factor": factor,
        "h_c": float(h_c),
        "sweep": sweep,
        "cases": cases,
        "baseline_seconds": float(baseline_seconds),
    }


@complex_only
def test_the_refined_rung_is_a_valid_four_port(refined_rung_cases):
    """Anchor: the refined rung's 50 Ohm 4x4 is still `PORT-9`'s matrix.

    Both bands are **imported** from the modules that pre-stated them and
    neither is touched.  A rung that fails here is a fixture finding: its
    residual would mean nothing.  The cell count is asserted strictly above
    step 1's record for a refining factor — otherwise "refined" is a claim the
    mesher did not honour.
    """
    rung = refined_rung_cases
    sweep = rung["sweep"]
    reciprocity = float(sweep["reciprocity"])
    sigma_max = float(np.max(sweep["sigma"]))
    cells = int(sweep["cells"])
    widths = [float(spec.sheet_width_m) for spec in sweep["specs"]]
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-14 step1b] refined rung: conductor_resolution x"
            f"{rung['factor']:.4g} = {rung['h_c']:.6e} m; {cells} cells "
            f"(step 1 record {STEP1_CELL_RECORD}, ratio "
            f"{cells / STEP1_CELL_RECORD:.6f}); four 50 Ohm drives in "
            f"{rung['baseline_seconds']:.2f} s wall",
            flush=True,
        )
        print(
            "    sheet_width_m per port (A/h off the *measured* extents, so a "
            "finer mesh moves it): " + ", ".join(f"{w:.9e}" for w in widths),
            flush=True,
        )
        print(
            f"    50 Ohm baseline: ||S - S^T||/||S|| = {reciprocity:.9e} "
            f"(band {RECIPROCITY_BAND:.0e}); sigma_max = {sigma_max:.9f} "
            f"(band 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e})",
            flush=True,
        )
    assert reciprocity <= RECIPROCITY_BAND, (
        f"the refined rung's 50 Ohm 4x4 is reciprocal only to {reciprocity:.3e} "
        f"against the imported {RECIPROCITY_BAND:.0e} band — this rung is not a "
        "valid four-port and its residual means nothing"
    )
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"the refined rung's 4x4 has sigma_max = {sigma_max:.9f} > 1 + "
        f"{PASSIVITY_SIGMA_TOLERANCE:.0e}: a passive network cannot"
    )
    if rung["factor"] < 1.0:
        assert cells > STEP1_CELL_RECORD, (
            f"conductor_resolution x{rung['factor']:.4g} gave {cells} cells, not "
            f"more than step 1's {STEP1_CELL_RECORD} — the keyword did not refine "
            "anything and the measurement below would be a re-run, not a rung"
        )


@complex_only
def test_the_refined_rung_residuals_are_printed(refined_rung_cases):
    """**The measurement, printed not asserted.**  Residual vs sheet resolution.

    Monotone decrease against step 1's 1.595580e-03 / 3.370512e-03 confirms the
    |Gamma| hypothesis; flat or rising refutes it and names the sheet law's
    area-based effective width (`lumped.py:353`) as the next suspect — a step
    1c, never a band change.  `REDUCTION_BAND` is deliberately not read here.
    """
    rung = refined_rung_cases
    if MPI.COMM_WORLD.rank != 0:
        return
    print(
        f"[PORT-14 step1b] reduction identity residuals at "
        f"f = {FREQUENCY_HZ:.3e} Hz, {int(rung['sweep']['cells'])} cells "
        f"(conductor_resolution x{rung['factor']:.4g}); step 1's record is on "
        f"{STEP1_CELL_RECORD} cells. Printed, not asserted:",
        flush=True,
    )
    for case in rung["cases"]:
        record = STEP1_RESIDUAL_RECORD[case["label"]]
        fell = "FELL" if case["residual"] < record else "DID NOT FALL"
        print(
            f"    {case['label']:<12s} |Gamma| = {abs(case['gamma']):.6f}   "
            f"residual = {case['residual']:.6e}   "
            f"(step 1 on {STEP1_CELL_RECORD} cells: {record:.6e}; "
            f"ratio {case['residual'] / record:.6f}, {fell})   "
            f"three drives in {case['seconds']:.2f} s wall",
            flush=True,
        )


@complex_only
def test_the_zero_gamma_control_misses_on_the_refined_rung(refined_rung_cases):
    """**Negative control, ceiling first**, exactly as step 1 ran it.

    Delta — the coupling term the rung's own 4x4 predicts — is computed first
    and printed as the ceiling; the >= 5x-band miss is asserted only where
    Delta reaches the floor, so no factor is claimed above that ceiling.
    """
    rung = refined_rung_cases
    s4 = np.asarray(rung["sweep"]["s"], dtype=np.complex128)
    kept = [i for i in range(s4.shape[0]) if i != TERMINATED_PORT_INDEX]
    s_aa = s4[np.ix_(kept, kept)]

    rows = []
    for case in rung["cases"]:
        predicted = case["predicted"]
        delta = float(np.linalg.norm(predicted - s_aa) / np.linalg.norm(predicted))
        miss = float(
            np.linalg.norm(case["measured"] - s_aa) / np.linalg.norm(predicted)
        )
        rows.append((case["label"], delta, miss))

    reached = [row for row in rows if row[1] >= CONTROL_DELTA_FLOOR]
    if MPI.COMM_WORLD.rank == 0:
        print(
            "[PORT-14 step1b] Gamma = 0 control (ceiling first), floor "
            f"{CONTROL_DELTA_FLOOR:.0e}:",
            flush=True,
        )
        for label, delta, miss in rows:
            print(
                f"    {label:<12s} Delta = {delta:.6e}   "
                f"||S'_meas - S_aa||_F/||S'_pred||_F = {miss:.6e}   "
                f"({'asserted' if delta >= CONTROL_DELTA_FLOOR else 'below floor'})",
                flush=True,
            )
        if not reached:
            print(
                "    FINDING: no termination reaches the Delta floor on this rung",
                flush=True,
            )

    for label, delta, miss in reached:
        assert miss >= CONTROL_MISS_FACTOR * REDUCTION_BAND, (
            f"{label}: on the refined rung the Gamma = 0 prediction S_aa misses "
            f"the measured terminated 3x3 by only {miss:.3e}, under "
            f"{CONTROL_MISS_FACTOR:g}x the {REDUCTION_BAND:.0e} band, though the "
            f"4x4 predicts a coupling term Delta = {delta:.3e}"
        )


# ---------------------------------------------------------------------------
# `PORT-14` step 1c — the width law on a *fixed* mesh
# ---------------------------------------------------------------------------
#
# Step 1b refuted the resolution hypothesis and named the next suspect.  Its
# table has one clean discriminator in it: the x0.75 rung is the only rung whose
# four `sheet_width_m` values are unequal (6.884e-03 / 7.650e-03 alternating,
# +-5.3% about their mean) and the only rung whose residual *rose* (x2.6).  So
# hold the gate mesh fixed — 116 085 cells, no new mesh, no `src/` change — and
# perturb the width the sheet law is *told*, per port, through the
# `LumpedSheetPortSpec` rebuild `build_four_port_sweep`'s `reuse` route already
# performs off the measured sheet geometry.
#
# The sheet resistivity is `Z_p · w/h` (`lumped.py:111`), so a *common* factor
# (1+eps) on `w` scales every sheet's effective Z by (1+eps), while the
# reduction's Gamma is built from the nominal `Z_p/z0` ratio (invariant under a
# common factor) and the field-solved S is referenced to the nominal z0 = 50
# through `_power_waves` (not invariant).  The three pre-registered readings are
# in the `PORT-14` §7 entry, "Step 1c", and are not restated here.
#
# **Nothing about the residual is asserted.**  What *is* asserted, per
# configuration, is that the perturbed 4x4 is still a valid passive reciprocal
# network (imported bands, unmoved), that the mesh really did not move (cell
# count bitwise equal to the record), and the same ceiling-first Gamma = 0
# control step 1 ran.  `REDUCTION_BAND` is deliberately not read below.
STEP1C_ENV = "FEM_EM_PORT14_WIDTH_SWEEP"

# The three configurations, per the §7 entry.  Index k of the tuple is port
# `P(k+1)`, so (C) is +5.3% on P1/P3 and -5.3% on P2/P4 — step 1b's x0.75 rung's
# C4 break reproduced on the gate mesh with the mesh itself untouched.
WIDTH_CONFIGURATIONS = (
    ("A", "common +5%", (+0.05, +0.05, +0.05, +0.05)),
    ("B", "common -5%", (-0.05, -0.05, -0.05, -0.05)),
    ("C", "alternating +-5.3%", (+0.053, -0.053, +0.053, -0.053)),
)


def _width_sweep_enabled():
    return bool(os.environ.get(STEP1C_ENV, ""))


# --- `PORT-14` step 2c: the width lever at 64 MHz, read against kappa ---------
# With `FEM_EM_PORT14_STEP2_64MHZ` on, both width fixtures run at 64 MHz (flag
# unset: FREQUENCY_HZ, bit-identical).  The three-point eps* fit needs the
# eps = 0 residual at the frequency that ran; at 64 MHz that is step 2's
# printed reading on the same mesh and the same terminations, restated as a
# logged record with its source
# (`20260911T183201Z_PORT-14-step2.log:1891, :1898`).  At 10 MHz it is step 1's
# record, exactly as step 1c printed against.
STEP2C_EPS0_RESIDUALS_64MHZ = {"C = 100 pF": 1.354202e-02, "L = 1 uH": 5.021261e-04}

# Step 2b's post-hoc per-element kappa_k = dZ/(Z_p - z0) (real parts; the
# imaginary parts are <= 4.1e-05), the comparand of eps* under the proportional
# law.  64 MHz: `20260912T020824Z_PORT-14-step2b-w2.log:1948-1949`; 10 MHz:
# `20260912T021021Z_PORT-14-step2b-default-w2.log:1949-1950`.  Logged records,
# printed beside the fit and never asserted.
STEP2B_KAPPA_K = {
    STEP2_FREQUENCY_HZ: {"C = 100 pF": 1.057617e-02, "L = 1 uH": 1.064945e-02},
    FREQUENCY_HZ: {"C = 100 pF": 1.058471e-02, "L = 1 uH": 1.059024e-02},
}

# The §9 item's pre-registered predictions and negative-result bars (rule (e):
# all *predicted*, printed beside the measurement, never asserted).
STEP2C_PREDICTED_KAPPA_FRACTION = 0.10  # eps* within 10 % of -kappa_k
STEP2C_PREDICTED_C_OVER_L = 0.02  # eps*(C), eps*(L) within 2 % of each other
STEP2C_NEGATIVE_KAPPA_FRACTION = 0.30  # eps* off -kappa_k by > 30 % => stop
STEP2C_NEGATIVE_C_OVER_L_FACTOR = 2.0  # C and L eps* differ by > 2x => stop
STEP2C_FLAT_FRACTION = 0.10  # every residual within +-10 % of eps = 0 => stop

# Per-configuration residuals, filled by the fit test as each configuration
# completes; the fit prints once all three are in (order-independent).
_STEP2C_READINGS = {}


def _width_sweep_eps0_residuals(frequency_hz):
    """The eps = 0 residual per lossless element at ``frequency_hz``, with source."""
    if float(frequency_hz) == float(STEP2_FREQUENCY_HZ):
        return {
            "residuals": dict(STEP2C_EPS0_RESIDUALS_64MHZ),
            "source": "step 2, 20260911T183201Z_PORT-14-step2.log:1891, :1898",
        }
    return {
        "residuals": dict(STEP1_RESIDUAL_RECORD),
        "source": "step 1's record",
    }


@pytest.fixture(scope="module")
def width_sweep_baseline():
    """The gate mesh and its unperturbed sheet geometry, built once.

    This is `build_four_port_sweep`'s own construction at its own defaults, so
    the mesh, the facet tags and the *measured* sheet extents are the gate
    rung's exactly.  The perturbed configurations below reuse this mesh through
    the function's `reuse` route: only the widths handed to the sheet law
    differ.
    """
    if not _width_sweep_enabled():
        pytest.skip(
            f"{STEP1C_ENV} unset — `PORT-14` step 1c's width configurations run "
            "only when a slot asks for them, so `main`'s red set is unchanged"
        )
    comm = MPI.COMM_WORLD
    # Step 2c: the frequency the module was asked for (10 MHz unless
    # `FEM_EM_PORT14_STEP2_64MHZ` is on) — flag unset, this is FREQUENCY_HZ.
    frequency_hz = _rlc_frequency_hz()
    comm.Barrier()
    t0 = time.perf_counter()
    sweep = build_four_port_sweep(frequency_hz=frequency_hz)
    comm.Barrier()
    seconds = time.perf_counter() - t0
    widths = [float(spec.sheet_width_m) for spec in sweep["specs"]]
    if comm.rank == 0:
        print(
            f"\n[PORT-14 step1c] baseline (unperturbed) gate rung at "
            f"f = {frequency_hz:.6e} Hz: "
            f"{int(sweep['cells'])} cells (record {STEP1_CELL_RECORD}); "
            f"mesh + four 50 Ohm drives in {seconds:.2f} s wall; "
            "sheet_width_m per port = " + ", ".join(f"{w:.9e}" for w in widths),
            flush=True,
        )
    return {"sweep": sweep, "widths": widths, "seconds": float(seconds)}


@pytest.fixture(
    scope="module",
    params=WIDTH_CONFIGURATIONS,
    ids=[c[0] for c in WIDTH_CONFIGURATIONS],
)
def width_sweep_case(request, width_sweep_baseline):
    """One width configuration: the perturbed 50 Ohm 4x4 plus C and L terminated.

    Ten solves on the **same mesh** as the baseline: four for the perturbed
    50 Ohm 4x4 and three each for the two lossless terminated 3x3s.  The
    perturbation enters through `sheets[k]["w"]` — which is the only thing
    `build_four_port_sweep` reads to fill `LumpedSheetPortSpec.sheet_width_m` —
    so the mesh, the facet tags and the measured areas/heights are bit-identical
    to the baseline's by construction, not by assertion.
    """
    key, description, epsilons = request.param
    comm = MPI.COMM_WORLD
    base = width_sweep_baseline["sweep"]

    perturbed_sheets = []
    for sheet, eps in zip(base["sheets"], epsilons):
        entry = dict(sheet)
        entry["w"] = float(sheet["w"]) * (1.0 + float(eps))
        perturbed_sheets.append(entry)

    reuse = {
        "mesh": base["mesh"],
        "cell_tags": base["cell_tags"],
        "facet_tags": base["facet_tags"],
        "sheets": perturbed_sheets,
        "halves": base["halves"],
        "cells": base["cells"],
    }

    # Step 2c: the sweep is rebuilt at the module's frequency (the `reuse` route
    # is mesh-only) and the termination is evaluated at the same frequency.
    frequency_hz = _rlc_frequency_hz()
    comm.Barrier()
    t0 = time.perf_counter()
    sweep = build_four_port_sweep(frequency_hz=frequency_hz, reuse=reuse)
    comm.Barrier()
    baseline_seconds = time.perf_counter() - t0

    cases = []
    for label, element in STEP1B_TERMINATIONS:
        z_term = series_rlc_impedance(frequency_hz, **element)
        comm.Barrier()
        t1 = time.perf_counter()
        measured, kept_ids, _results = _terminated_three_port(sweep, z_term)
        comm.Barrier()
        elapsed = time.perf_counter() - t1
        predicted = reduce_terminated_ports(
            sweep["s"], float(REFERENCE_IMPEDANCE_OHM), {TERMINATED_PORT_INDEX: z_term}
        )
        residual = float(
            np.linalg.norm(measured - predicted) / np.linalg.norm(predicted)
        )
        cases.append(
            {
                "label": label,
                "z": z_term,
                "gamma": termination_reflection_coefficient(
                    z_term, float(REFERENCE_IMPEDANCE_OHM)
                ),
                "measured": measured,
                "predicted": predicted,
                "residual": residual,
                "kept_ids": kept_ids,
                "seconds": float(elapsed),
            }
        )

    return {
        "key": key,
        "description": description,
        "frequency_hz": float(frequency_hz),
        "epsilons": tuple(float(e) for e in epsilons),
        "sweep": sweep,
        "baseline_widths": list(width_sweep_baseline["widths"]),
        "widths": [float(spec.sheet_width_m) for spec in sweep["specs"]],
        "cases": cases,
        "baseline_seconds": float(baseline_seconds),
        "baseline_cells": int(base["cells"]),
    }


@complex_only
def test_the_width_sweep_configuration_is_a_valid_four_port(width_sweep_case):
    """Anchor: a perturbed width still gives a passive, reciprocal 4x4.

    Both bands are **imported** from the modules that pre-stated them and
    neither is touched.  A configuration that fails here is a fixture finding —
    its residual would mean nothing — and the §7 entry says to record it in
    known-issues and stop.  The cell count is asserted **bitwise** equal to the
    record: the whole point of step 1c is that the mesh did not move.
    """
    case = width_sweep_case
    sweep = case["sweep"]
    reciprocity = float(sweep["reciprocity"])
    sigma_max = float(np.max(sweep["sigma"]))
    cells = int(sweep["cells"])
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-14 step1c] configuration {case['key']} ({case['description']}) "
            f"at f = {case['frequency_hz']:.6e} Hz: "
            f"{cells} cells (record {STEP1_CELL_RECORD}, same mesh); four 50 Ohm "
            f"drives in {case['baseline_seconds']:.2f} s wall",
            flush=True,
        )
        for idx, (w0, w1, eps) in enumerate(
            zip(case["baseline_widths"], case["widths"], case["epsilons"]), start=1
        ):
            print(
                f"    P{idx}: sheet_width_m {w0:.9e} -> {w1:.9e} m "
                f"(eps = {eps:+.4f}, ratio {w1 / w0:.9f})",
                flush=True,
            )
        print(
            f"    50 Ohm baseline: ||S - S^T||/||S|| = {reciprocity:.9e} "
            f"(band {RECIPROCITY_BAND:.0e}); sigma_max = {sigma_max:.9f} "
            f"(band 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e})",
            flush=True,
        )
    assert cells == STEP1_CELL_RECORD, (
        f"configuration {case['key']} solved on {cells} cells, not the "
        f"{STEP1_CELL_RECORD}-cell gate mesh — the width perturbation moved the "
        "mesh, so this is not a fixed-mesh measurement"
    )
    assert reciprocity <= RECIPROCITY_BAND, (
        f"configuration {case['key']}'s 50 Ohm 4x4 is reciprocal only to "
        f"{reciprocity:.3e} against the imported {RECIPROCITY_BAND:.0e} band — a "
        "perturbed width does not give a valid four-port and its residual means "
        "nothing (§7 `PORT-14` step 1c: known-issues with its widths, stop)"
    )
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"configuration {case['key']}'s 4x4 has sigma_max = {sigma_max:.9f} > 1 + "
        f"{PASSIVITY_SIGMA_TOLERANCE:.0e}: a passive network cannot"
    )


@complex_only
def test_the_width_sweep_residuals_are_printed(width_sweep_case):
    """**The measurement, printed not asserted.**  Residual vs the width told.

    Each residual is printed beside step 1's 116 085-cell record and as a factor
    of it.  The three pre-registered readings — linear-in-eps with a common
    zero-crossing, flat under (A)/(B) but moved by (C), or flat under all three
    — are named in the `PORT-14` §7 entry and are a review's call, not this
    module's.  `REDUCTION_BAND` is deliberately not read here.
    """
    case = width_sweep_case
    if MPI.COMM_WORLD.rank != 0:
        return
    print(
        f"[PORT-14 step1c] configuration {case['key']} ({case['description']}) "
        f"reduction identity residuals at f = {case['frequency_hz']:.6e} Hz on the "
        f"{int(case['sweep']['cells'])}-cell gate mesh; the eps = 0 reading at this "
        "frequency is on the same mesh with the unperturbed widths. Printed, not "
        "asserted:",
        flush=True,
    )
    eps0 = _width_sweep_eps0_residuals(case["frequency_hz"])
    for entry in case["cases"]:
        record = eps0["residuals"][entry["label"]]
        print(
            f"    {entry['label']:<12s} |Gamma| = {abs(entry['gamma']):.6f}   "
            f"residual = {entry['residual']:.6e}   "
            f"(eps = 0 at this frequency {record:.6e}, {eps0['source']}; factor "
            f"{entry['residual'] / record:.6f})   "
            f"three drives in {entry['seconds']:.2f} s wall",
            flush=True,
        )


@complex_only
def test_the_zero_gamma_control_misses_on_the_width_sweep(width_sweep_case):
    """**Negative control, ceiling first**, exactly as step 1 ran it.

    Delta — the coupling term this configuration's own 4x4 predicts — is
    computed first and printed as the ceiling; the >= 5x-band miss is asserted
    only where Delta reaches the floor, so no factor is claimed above that
    ceiling.  Step 1 measured Delta = 0.32 / 0.33 on these two terminations.
    """
    case = width_sweep_case
    s4 = np.asarray(case["sweep"]["s"], dtype=np.complex128)
    kept = [i for i in range(s4.shape[0]) if i != TERMINATED_PORT_INDEX]
    s_aa = s4[np.ix_(kept, kept)]

    rows = []
    for entry in case["cases"]:
        predicted = entry["predicted"]
        delta = float(np.linalg.norm(predicted - s_aa) / np.linalg.norm(predicted))
        miss = float(
            np.linalg.norm(entry["measured"] - s_aa) / np.linalg.norm(predicted)
        )
        rows.append((entry["label"], delta, miss))

    reached = [row for row in rows if row[1] >= CONTROL_DELTA_FLOOR]
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-14 step1c] configuration {case['key']} Gamma = 0 control at "
            f"f = {case['frequency_hz']:.6e} Hz "
            f"(ceiling first), floor {CONTROL_DELTA_FLOOR:.0e}:",
            flush=True,
        )
        for label, delta, miss in rows:
            print(
                f"    {label:<12s} Delta = {delta:.6e}   "
                f"||S'_meas - S_aa||_F/||S'_pred||_F = {miss:.6e}   "
                f"({'asserted' if delta >= CONTROL_DELTA_FLOOR else 'below floor'})",
                flush=True,
            )
        if not reached:
            print(
                "    FINDING: no termination reaches the Delta floor on this "
                "configuration",
                flush=True,
            )

    for label, delta, miss in reached:
        assert miss >= CONTROL_MISS_FACTOR * REDUCTION_BAND, (
            f"{label}: on width configuration {case['key']} the Gamma = 0 "
            f"prediction S_aa misses the measured terminated 3x3 by only "
            f"{miss:.3e}, under {CONTROL_MISS_FACTOR:g}x the "
            f"{REDUCTION_BAND:.0e} band, though the 4x4 predicts a coupling term "
            f"Delta = {delta:.3e}"
        )


@complex_only
def test_the_width_sweep_epsilon_star_fit_is_printed(width_sweep_case):
    """**`PORT-14` step 2c — eps* at the frequency that ran, beside -kappa_k.**

    Printed, never asserted (rule (e): no prior measurement of this comparison
    at 64 MHz).  Each configuration's residuals are kept as it completes; once
    A, B and C are all in, the three-point ``_epsilon_star`` fit through
    (0, eps = 0 residual), (+0.05, A), (-0.05, B) prints per element beside
    step 1c's 10 MHz eps*, the eps = 0 residual, -kappa_k and eps*/(-kappa_k),
    with the §9 item's predictions and negative-result bars evaluated in words.
    Residuals are comm-identical, so the bookkeeping is the same on every rank.
    """
    case = width_sweep_case
    _STEP2C_READINGS[case["key"]] = {
        "frequency_hz": float(case["frequency_hz"]),
        "residuals": {e["label"]: float(e["residual"]) for e in case["cases"]},
    }
    if not {"A", "B", "C"} <= set(_STEP2C_READINGS):
        return
    if MPI.COMM_WORLD.rank != 0:
        return

    frequency_hz = case["frequency_hz"]
    eps0 = _width_sweep_eps0_residuals(frequency_hz)
    kappa = STEP2B_KAPPA_K.get(frequency_hz, {})
    configs = {k: v["residuals"] for k, v in _STEP2C_READINGS.items()}
    signed_eps = {key: eps[0] for key, _d, eps in WIDTH_CONFIGURATIONS}
    print(
        f"\n[PORT-14 step2c] eps* fit at f = {frequency_hz:.6e} Hz through "
        f"(0, eps = 0 from {eps0['source']}), (+{signed_eps['A']:.2f}, A), "
        f"({signed_eps['B']:+.2f}, B). Printed, never asserted:",
        flush=True,
    )
    stars = {}
    for label in STEP1C_RESIDUALS:
        points = (
            (0.0, eps0["residuals"][label]),
            (signed_eps["A"], configs["A"][label]),
            (signed_eps["B"], configs["B"][label]),
        )
        star, r2_star, a, b, c = _epsilon_star(points)
        star_10, _r2_10, _a10, _b10, _c10 = _epsilon_star(STEP1C_RESIDUALS[label])
        stars[label] = star
        line = (
            f"    {label:<12s} eps* = {star:+.6f}   r^2(eps*) = {r2_star:+.6e}   "
            f"(r^2 = {a:.6e} eps^2 + {b:.6e} eps + {c:.6e})   "
            f"step 1c 10 MHz eps* = {star_10:+.6f}   "
            f"eps = 0 residual = {eps0['residuals'][label]:.6e}"
        )
        if label in kappa:
            neg_kappa = -float(kappa[label])
            ratio = star / neg_kappa
            off = abs(ratio - 1.0)
            line += (
                f"   -kappa_k = {neg_kappa:+.6e}   eps*/(-kappa_k) = {ratio:.6f} "
                f"(|ratio - 1| = {off:.4f}; predicted <= "
                f"{STEP2C_PREDICTED_KAPPA_FRACTION:g}: "
                f"{'HELD' if off <= STEP2C_PREDICTED_KAPPA_FRACTION else 'FAILED'}; "
                f"negative-result bar > {STEP2C_NEGATIVE_KAPPA_FRACTION:g}: "
                f"{'FIRES' if off > STEP2C_NEGATIVE_KAPPA_FRACTION else 'clear'})"
            )
        print(line, flush=True)

    c_label, l_label = "C = 100 pF", "L = 1 uH"
    c_over_l = stars[c_label] / stars[l_label]
    spread = max(abs(c_over_l), 1.0 / abs(c_over_l)) if c_over_l != 0.0 else np.inf
    print(
        f"    eps*(C)/eps*(L) = {c_over_l:.6f} (|ratio - 1| = {abs(c_over_l - 1.0):.4f}; "
        f"predicted <= {STEP2C_PREDICTED_C_OVER_L:g}: "
        f"{'HELD' if abs(c_over_l - 1.0) <= STEP2C_PREDICTED_C_OVER_L else 'FAILED'}; "
        f"negative-result bar: differ by > {STEP2C_NEGATIVE_C_OVER_L_FACTOR:g}x or "
        f"opposite sign: "
        f"{'FIRES' if (c_over_l <= 0.0 or spread > STEP2C_NEGATIVE_C_OVER_L_FACTOR) else 'clear'})",
        flush=True,
    )

    l_zero = eps0["residuals"][l_label]
    l_plus, l_minus = configs["A"][l_label], configs["B"][l_label]
    raised = l_plus > l_zero and l_minus > l_zero
    print(
        f"    L residual: eps = 0 {l_zero:.6e}, +5% {l_plus:.6e} "
        f"(x{l_plus / l_zero:.6f}), -5% {l_minus:.6e} (x{l_minus / l_zero:.6f}); "
        f"predicted both directions raise it: {'HELD' if raised else 'FAILED'}",
        flush=True,
    )

    factors = []
    for key in ("A", "B", "C"):
        for label in STEP1C_RESIDUALS:
            factors.append(configs[key][label] / eps0["residuals"][label])
    flat = all(abs(f - 1.0) <= STEP2C_FLAT_FRACTION for f in factors)
    print(
        "    residual / eps = 0 across A, B, C x (C, L) = "
        + ", ".join(f"{f:.6f}" for f in factors)
        + f"; negative-result bar (all within +-{STEP2C_FLAT_FRACTION:g}, width "
        f"not a lever): {'FIRES' if flat else 'clear'}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# `PORT-14` step 1d — where does eps* come from, and does the fit hold on a
# fourth point?
# ---------------------------------------------------------------------------
#
# Step 1c measured the residual at three told widths (eps = 0, +5%, -5%) on the
# fixed 116 085-cell gate mesh and a three-point fit of `|r0 + k*eps|` put the
# zero-crossing at eps* ~ -1.1% for *both* lossless elements.  Step 1d does two
# things with that, and **tunes nothing**:
#
#   (a) reads the sheet geometry `build_four_port_sweep` already measures and
#       expresses each ratio as a candidate `eps_geom` — a *prediction* of eps*
#       from geometry alone.  The pre-registered comparison is
#       |eps_geom - eps*| <= 0.3*|eps*| for **one** candidate; none there means
#       the origin is not geometric.
#   (b) recomputes eps* **in code** from step 1c's printed residuals (below,
#       constants — eps* is never typed in) and runs configuration **D**, every
#       told width scaled by (1 + mean eps*), through the same `reuse` route.
#       The fit predicts a residual ~ 0; whether it lands under `REDUCTION_BAND`
#       is **printed, not asserted**, because the width was fitted *to* that
#       residual and asserting it would be circular.
#
# Asserted here (imported bands, none moved): D is still a valid passive
# reciprocal four-port on the bitwise-unchanged mesh, and the same ceiling-first
# Gamma = 0 control step 1 / 1c ran.
STEP1D_ENV = STEP1C_ENV

# Step 1c's six printed residuals, `20260905T213322Z_PORT-14-step1c.log`
# (`:1943` and the per-configuration blocks `:1985-1986`, `:2054-2055`), keyed by
# the told-width perturbation that produced them.  These are *logged records*,
# not module constants any other file exports, so they are restated here with
# their source.  eps* is derived from them below and never written down.
STEP1C_RESIDUALS = {
    "C = 100 pF": ((0.0, 1.595580e-03), (+0.05, 9.260556e-03), (-0.05, 5.980286e-03)),
    "L = 1 uH": ((0.0, 3.370512e-03), (+0.05, 1.965102e-02), (-0.05, 1.255208e-02)),
}

# The pre-registered geometric-match window: a candidate ratio predicts eps* if
# it lands within this fraction of |eps*| of it (~0.3 pp at eps* ~ -1.1%).
GEOM_MATCH_FRACTION = 0.3

# --- `PORT-14` step 2e: step 1d's pattern moved to 64 MHz --------------------
# With `FEM_EM_PORT14_STEP2_64MHZ` on, step 1d's baseline and configuration D
# build at 64 MHz and `step1d_fit` takes its three points from step 2c's
# 64 MHz readings instead of step 1c's 10 MHz ones (flag off: unchanged).
# Logged records, restated with their sources: eps = 0 is step 2's
# (`20260911T183201Z_PORT-14-step2.log:1891, :1898`), +5% / -5% are step 2c's
# configurations A / B (`20260912T140430Z_PORT-14-step2c.log:1941-1942,
# :2012-2013`).
STEP2C_RESIDUALS = {
    "C = 100 pF": ((0.0, 1.354202e-02), (+0.05, 7.879573e-02), (-0.05, 5.047888e-02)),
    "L = 1 uH": ((0.0, 5.021261e-04), (+0.05, 2.862518e-03), (-0.05, 1.895173e-03)),
}

# Step 2c's printed eps* per element (`…step2c.log:2094-2095`) and their mean,
# asserted reproduced by the fit above — arithmetic on the same constants.  The
# six printed decimals carry <= 5e-7, i.e. <= 5e-5 relative, under the rtol.  The
# mean is not printed by 2c: it is the 09:00 journal's half-up rounding of the two
# printed values (`docs/testing/attempts.md`, 2026-09-12T14:09Z entry), so it
# carries up to ~1e-6 (measured 2026-09-12: |ratio - 1| = 6.938e-05,
# `20260912T183330Z_PORT-14-step2e.log:3758`), still under the rtol.
STEP2C_PRINTED_EPS_STAR = {"C = 100 pF": -0.010908, "L = 1 uH": -0.010199}
STEP2C_PRINTED_MEAN_EPS_STAR = -0.010554
STEP2E_FIT_RTOL = 1.0e-4

# Step 1d's 10 MHz ratio D / (eps = 0), `20260906T003627Z_PORT-14-step1d.log:2103-2104`.
# Printed beside the 64 MHz ratio, never asserted.
STEP1D_D_RATIO_10MHZ = {"C = 100 pF": 0.036078, "L = 1 uH": 0.035507}

# *Predicted* (rule (e), printed only, stop-on-miss for the slot): the in-window
# eps = 0 residual reproduces step 2's to this rtol (step 2d's flag-off window
# reproduced C/terminal - 1 across windows to 1.45e-10).
STEP2E_EPS0_REPRODUCTION_RTOL = 1.0e-6

# Asserted: the 64 MHz baseline's S11 differs from the 10 MHz record by more than
# this, so a flag that did not reach step 1d's builder cannot pass (step 2d's
# control, `20260912T123236Z_PORT-14-step2d-64mhz.log:1940`: |diff| = 6.05e-01).
STEP2E_S11_MOVE_FLOOR = 1.0e-7

# The eps = 0 residuals measured in *this* window by
# `test_the_terminated_solve_matches_the_circuit_reduction` under the 64 MHz flag.
_STEP2E_EPS0_IN_WINDOW = {}


def _epsilon_star(points):
    """The vertex of ``r^2(eps)`` through three ``(eps, r)`` points.

    Step 1c's model is ``r(eps) = |r0 + k*eps|``, so ``r^2`` is an exact
    parabola in ``eps`` and three points determine it.  The zero-crossing of the
    linear model is the vertex of that parabola, ``eps* = -b/(2a)``.  Returned
    with the fitted minimum ``r^2(eps*)`` so the log can show how close to zero
    the fit itself claims to get.
    """
    eps = np.array([float(p[0]) for p in points], dtype=float)
    r2 = np.array([float(p[1]) ** 2 for p in points], dtype=float)
    vandermonde = np.vstack([eps**2, eps, np.ones_like(eps)]).T
    a, b, c = np.linalg.solve(vandermonde, r2)
    star = float(-b / (2.0 * a))
    return star, float(a * star * star + b * star + c), float(a), float(b), float(c)


def _geometric_candidates(sheet):
    """Candidate ``eps_geom`` values for one sheet, from measured geometry only.

    Every quantity here is already reduced across ranks by
    `build_four_port_sweep` (`area` and `w_bbox` come from
    `_facet_group_area` / `_sheet_extents`, both of which allreduce), so nothing
    below is rank-local and no facet vertex is touched on this rank.

    The law is ``R = Z_p * w / h`` with ``w = area/h_bbox``.  If the *effective*
    terminal separation is ``h_true`` rather than the bounding box ``h_bbox``,
    the width the law should have been told is ``area/h_true``, i.e.
    ``eps_geom = h_bbox/h_true - 1``.  Both orientations of each ratio are
    listed, labelled, because which way round a candidate enters the law is
    exactly what a match would establish.
    """
    area = float(sheet["area"])
    h_bbox = float(sheet["h"])
    w_bbox = float(sheet["w_bbox"])
    w_law = float(sheet["w"])
    h_mean = area / w_bbox
    return {
        # The bounding box's fill fraction; algebraically identical to
        # w_law/w_bbox - 1 and to h_mean/h_bbox - 1 (step 2b's "ragged edge").
        "area/(w_bbox*h_bbox) - 1": area / (w_bbox * h_bbox) - 1.0,
        "w_law/w_bbox - 1": w_law / w_bbox - 1.0,
        "h_mean/h_bbox - 1": h_mean / h_bbox - 1.0,
        "h_bbox/h_mean - 1": h_bbox / h_mean - 1.0,
        "h_bbox/leg_gap_told - 1": h_bbox / float(LEG_GAP_LENGTH) - 1.0,
        "leg_gap_told/h_bbox - 1": float(LEG_GAP_LENGTH) / h_bbox - 1.0,
        "h_bbox/port_box_z_told - 1": h_bbox / float(PORT_BOX_SIZE[2]) - 1.0,
        "port_box_z_told/h_bbox - 1": float(PORT_BOX_SIZE[2]) / h_bbox - 1.0,
    }


@pytest.fixture(scope="module")
def step1d_fit():
    """eps* per element from step 1c's constants — arithmetic, no solve.

    Under `FEM_EM_PORT14_STEP2_64MHZ` the points are step 2c's 64 MHz readings
    (`STEP2C_RESIDUALS`, `PORT-14` step 2e).
    """
    if _step2_enabled():
        table, source = STEP2C_RESIDUALS, "step 2c's 64 MHz residuals (eps = 0 from step 2)"
    else:
        table, source = STEP1C_RESIDUALS, "step 1c's three printed residuals"
    fit = {}
    for label, points in table.items():
        star, r2_star, a, b, c = _epsilon_star(points)
        fit[label] = {
            "eps_star": star,
            "r2_star": r2_star,
            "a": a,
            "b": b,
            "c": c,
        }
    mean_star = float(np.mean([v["eps_star"] for v in fit.values()]))
    return {"per_element": fit, "mean_eps_star": mean_star, "source": source}


@pytest.fixture(scope="module")
def step1d_baseline():
    """The unperturbed gate rung: the mesh, its sheet geometry, its told widths."""
    if not _width_sweep_enabled():
        pytest.skip(
            f"{STEP1D_ENV} unset — `PORT-14` step 1d runs only when a slot asks "
            "for it, so `main`'s red set is unchanged"
        )
    comm = MPI.COMM_WORLD
    comm.Barrier()
    t0 = time.perf_counter()
    sweep = build_four_port_sweep(frequency_hz=_rlc_frequency_hz())
    comm.Barrier()
    seconds = time.perf_counter() - t0
    widths = [float(spec.sheet_width_m) for spec in sweep["specs"]]
    if comm.rank == 0:
        print(
            f"\n[PORT-14 step1d] baseline (unperturbed) gate rung: "
            f"{int(sweep['cells'])} cells (record {STEP1_CELL_RECORD}); "
            f"mesh + four 50 Ohm drives in {seconds:.2f} s wall; "
            "sheet_width_m per port = " + ", ".join(f"{w:.9e}" for w in widths),
            flush=True,
        )
    return {"sweep": sweep, "widths": widths, "seconds": float(seconds)}


@pytest.fixture(scope="module")
def step1d_configuration_d(step1d_baseline, step1d_fit):
    """Configuration **D**: every told width scaled by ``(1 + mean eps*)``.

    Ten solves on the same mesh, through the same `reuse` route step 1c used —
    `sheets[k]["w"]` is the only thing `build_four_port_sweep` reads to fill
    `LumpedSheetPortSpec.sheet_width_m`, so the mesh, the facet tags and the
    measured areas/heights are bit-identical to the baseline's by construction.
    """
    comm = MPI.COMM_WORLD
    base = step1d_baseline["sweep"]
    eps = float(step1d_fit["mean_eps_star"])

    perturbed_sheets = []
    for sheet in base["sheets"]:
        entry = dict(sheet)
        entry["w"] = float(sheet["w"]) * (1.0 + eps)
        perturbed_sheets.append(entry)

    reuse = {
        "mesh": base["mesh"],
        "cell_tags": base["cell_tags"],
        "facet_tags": base["facet_tags"],
        "sheets": perturbed_sheets,
        "halves": base["halves"],
        "cells": base["cells"],
    }

    comm.Barrier()
    t0 = time.perf_counter()
    frequency_hz = _rlc_frequency_hz()
    sweep = build_four_port_sweep(frequency_hz=frequency_hz, reuse=reuse)
    comm.Barrier()
    baseline_seconds = time.perf_counter() - t0

    cases = []
    for label, element in STEP1B_TERMINATIONS:
        z_term = series_rlc_impedance(frequency_hz, **element)
        comm.Barrier()
        t1 = time.perf_counter()
        measured, kept_ids, _results = _terminated_three_port(sweep, z_term)
        comm.Barrier()
        elapsed = time.perf_counter() - t1
        predicted = reduce_terminated_ports(
            sweep["s"], float(REFERENCE_IMPEDANCE_OHM), {TERMINATED_PORT_INDEX: z_term}
        )
        residual = float(
            np.linalg.norm(measured - predicted) / np.linalg.norm(predicted)
        )
        cases.append(
            {
                "label": label,
                "z": z_term,
                "gamma": termination_reflection_coefficient(
                    z_term, float(REFERENCE_IMPEDANCE_OHM)
                ),
                "measured": measured,
                "predicted": predicted,
                "residual": residual,
                "kept_ids": kept_ids,
                "seconds": float(elapsed),
            }
        )

    return {
        "epsilon": eps,
        "sweep": sweep,
        "baseline_widths": list(step1d_baseline["widths"]),
        "widths": [float(spec.sheet_width_m) for spec in sweep["specs"]],
        "cases": cases,
        "baseline_seconds": float(baseline_seconds),
        "baseline_cells": int(base["cells"]),
    }


@complex_only
def test_step1d_the_sheet_geometry_candidates_are_printed(step1d_baseline, step1d_fit):
    """**(a) Name a geometric origin** — printed, not asserted.

    Per port: the measured `area`, `h` (= `h_bbox`), `w` (= area/h_bbox, the
    number the law is told), `w_bbox`, `facets`, the reduced mean height
    `area/w_bbox`, and the gap length the *generator* was told — each ratio
    expressed as a candidate `eps_geom`.  A candidate within
    `GEOM_MATCH_FRACTION*|eps*|` of the fitted eps* would be a geometric origin
    for the 1.1%; none there means the offset is not geometric (pre-registered
    reading (2)).  Nothing is asserted: this is a measurement.
    """
    if MPI.COMM_WORLD.rank != 0:
        return
    sheets = step1d_baseline["sweep"]["sheets"]
    fit = step1d_fit
    print(
        "\n[PORT-14 step1d] (a) sheet geometry on the "
        f"{int(step1d_baseline['sweep']['cells'])}-cell gate mesh, per port "
        f"(leg_gap_length told to the generator = {float(LEG_GAP_LENGTH):.9e} m, "
        f"port_box z told = {float(PORT_BOX_SIZE[2]):.9e} m). Printed, not "
        "asserted:",
        flush=True,
    )
    for sheet in sheets:
        area = float(sheet["area"])
        h_bbox = float(sheet["h"])
        w_bbox = float(sheet["w_bbox"])
        print(
            f"    P{int(sheet['tag']) - SHEET_IFACE}: facets = {int(sheet['facets'])}   "
            f"area = {area:.9e} m^2   h_bbox = {h_bbox:.9e} m   "
            f"w_law = area/h_bbox = {float(sheet['w']):.9e} m   "
            f"w_bbox = {w_bbox:.9e} m   h_mean = area/w_bbox = "
            f"{area / w_bbox:.9e} m   out_of_plane = "
            f"{float(sheet['out_of_plane']):.9e} m",
            flush=True,
        )

    for label, entry in fit["per_element"].items():
        print(
            f"    fit {label:<12s} eps* = {entry['eps_star']:+.6f}   "
            f"r^2(eps*) = {entry['r2_star']:+.6e}   "
            f"(r^2 = {entry['a']:.6e} eps^2 + {entry['b']:.6e} eps + "
            f"{entry['c']:.6e}, from {fit['source']})",
            flush=True,
        )
    eps_star = float(fit["mean_eps_star"])
    window = GEOM_MATCH_FRACTION * abs(eps_star)
    print(
        f"    mean eps* = {eps_star:+.6f}; pre-registered match window "
        f"+-{window:.6f} ({GEOM_MATCH_FRACTION:g} x |eps*|)",
        flush=True,
    )

    matches = []
    for sheet in sheets:
        pid = f"P{int(sheet['tag']) - SHEET_IFACE}"
        for name, value in _geometric_candidates(sheet).items():
            hit = abs(value - eps_star) <= window
            if hit:
                matches.append((pid, name, value))
            print(
                f"    {pid} candidate {name:<28s} eps_geom = {value:+.6f}   "
                f"|eps_geom - eps*| = {abs(value - eps_star):.6f}   "
                f"({'MATCH' if hit else 'no'})",
                flush=True,
            )
    if matches:
        print(
            "    READING: at least one measured geometric ratio predicts eps* "
            "on its own — " + "; ".join(
                f"{pid} {name} = {value:+.6f}" for pid, name, value in matches
            ),
            flush=True,
        )
    else:
        print(
            "    READING: no measured geometric ratio predicts eps* within the "
            "pre-registered window — the origin is not one of these geometric "
            "quantities",
            flush=True,
        )


@complex_only
def test_step1d_step2e_the_64mhz_fit_reproduces_step2c(step1d_fit):
    """`PORT-14` step 2e: the 64 MHz eps* is step 2c's, recomputed in code.

    Asserted, arithmetic on the same constants: the fit through
    `STEP2C_RESIDUALS` reproduces step 2c's printed eps* per element and their
    mean to `STEP2E_FIT_RTOL`.  Runs only under `FEM_EM_PORT14_STEP2_64MHZ`.
    """
    if not _step2_enabled():
        pytest.skip(f"{STEP2_ENV} unset — step 2e's 64 MHz fit is not in use")
    rows = [
        (label, float(step1d_fit["per_element"][label]["eps_star"]), printed)
        for label, printed in STEP2C_PRINTED_EPS_STAR.items()
    ]
    rows.append(
        ("mean", float(step1d_fit["mean_eps_star"]), STEP2C_PRINTED_MEAN_EPS_STAR)
    )
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-14 step2e] eps* at 64 MHz from {step1d_fit['source']} "
            f"against step 2c's printed values (rtol {STEP2E_FIT_RTOL:.0e}, asserted):",
            flush=True,
        )
        for label, star, printed in rows:
            print(
                f"    {label:<12s} eps* = {star:+.9f}   step 2c printed {printed:+.6f}   "
                f"|ratio - 1| = {abs(star / printed - 1.0):.3e}",
                flush=True,
            )
    for label, star, printed in rows:
        assert abs(star / printed - 1.0) <= STEP2E_FIT_RTOL, (
            f"{label}: eps* = {star:+.9f} from STEP2C_RESIDUALS does not reproduce "
            f"step 2c's printed {printed:+.6f} to {STEP2E_FIT_RTOL:.0e} — a restated "
            "constant is wrong"
        )


@complex_only
def test_step1d_step2e_the_baseline_was_built_at_64mhz(step1d_baseline):
    """Control: step 1d's baseline really was rebuilt at 64 MHz.

    Asserted: S11 differs from the 10 MHz record `STEP1E_S11_S21_10MHZ` by more
    than `STEP2E_S11_MOVE_FLOOR` (step 2d measured 6.05e-01 on this comparison).
    """
    if not _step2_enabled():
        pytest.skip(f"{STEP2_ENV} unset — step 1d's baseline is the 10 MHz one")
    s11 = complex(np.asarray(step1d_baseline["sweep"]["s"], dtype=np.complex128)[0, 0])
    diff = abs(s11 - STEP1E_S11_S21_10MHZ[0])
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-14 step2e] step 1d baseline at f = {_rlc_frequency_hz():.3e} Hz: "
            f"S11 = {s11.real:+.9e}{s11.imag:+.9e}j   10 MHz record = "
            f"{STEP1E_S11_S21_10MHZ[0].real:+.9e}{STEP1E_S11_S21_10MHZ[0].imag:+.9e}j   "
            f"|diff| = {diff:.6e} (asserted > {STEP2E_S11_MOVE_FLOOR:.1e})",
            flush=True,
        )
    assert diff > STEP2E_S11_MOVE_FLOOR, (
        f"step 1d's baseline S11 moved only {diff:.3e} from the 10 MHz record: "
        f"{STEP2_ENV} did not reach the builder"
    )


def _print_step2e_configuration_d(case, fit):
    """Step 2e's 64 MHz reading of configuration D — printed, never asserted."""
    eps = float(case["epsilon"])
    print(
        f"[PORT-14 step2e] configuration D reduction identity residuals at "
        f"f = {_rlc_frequency_hz():.3e} Hz on the {int(case['sweep']['cells'])}-cell "
        f"gate mesh, told widths x (1 + mean eps*(64) = {1.0 + eps:.6f}). Printed, "
        "not asserted (the width was fitted to these numbers):",
        flush=True,
    )
    under = {}
    for entry in case["cases"]:
        label = entry["label"]
        residual = float(abs(entry["residual"]))
        under[label] = residual <= REDUCTION_BAND
        per = fit["per_element"][label]
        r2 = per["a"] * eps * eps + per["b"] * eps + per["c"]
        predicted = (
            f"{np.sqrt(r2):.6e}" if r2 > 0.0 else f"~0 (fitted r^2 = {r2:+.3e} < 0)"
        )
        record = STEP2C_EPS0_RESIDUALS_64MHZ[label]
        in_window = _STEP2E_EPS0_IN_WINDOW.get(label)
        if in_window is None:
            eps0_note = (
                "in-window eps = 0 NOT MEASURED (terminated-solve test not in this "
                f"window); step 2's {record:.6e}   D/(step 2 eps = 0) = "
                f"{residual / record:.6f}"
            )
        else:
            miss = abs(in_window / record - 1.0)
            eps0_note = (
                f"in-window eps = 0 = {in_window:.6e}   D/(eps = 0) = "
                f"{residual / in_window:.6f}   step 2's eps = 0 {record:.6e}, "
                f"|ratio - 1| = {miss:.3e} (predicted <= "
                f"{STEP2E_EPS0_REPRODUCTION_RTOL:.0e}: "
                f"{'HELD' if miss <= STEP2E_EPS0_REPRODUCTION_RTOL else 'MISSED — stop and report'})"
            )
        print(
            f"    {label:<12s} |Gamma| = {abs(entry['gamma']):.6f}   "
            f"residual = {residual:.6e}   (predicted from the fit {predicted})   "
            f"{eps0_note}   step 1d 10 MHz D/(eps = 0) = "
            f"{STEP1D_D_RATIO_10MHZ[label]:.6f}   (band {REDUCTION_BAND:.0e}; ratio "
            f"to band {residual / REDUCTION_BAND:.6f}; "
            f"{'UNDER' if under[label] else 'OVER'})   three drives in "
            f"{entry['seconds']:.2f} s wall",
            flush=True,
        )
    c_under, l_under = under.get("C = 100 pF"), under.get("L = 1 uH")
    if c_under and l_under:
        reading = (
            "both under the band — the (1 + kappa)-corrected width is a working "
            "64 MHz lever on this fixture; the route is the weekly's to scope"
        )
    elif l_under and not c_under:
        reading = (
            "C over, L under — the linear |r0 + k eps| model is broken for C at "
            "64 MHz: record in §7 and stop"
        )
    elif not c_under and not l_under:
        reading = (
            "both over — the width lever does not undo kappa at 64 MHz: record "
            "and stop"
        )
    else:
        reading = "C under, L over — not pre-registered: record and stop"
    print(f"    READING: {reading}", flush=True)


@complex_only
def test_step1d_configuration_d_is_a_valid_four_port(step1d_configuration_d):
    """Anchor: the fitted width still gives a passive, reciprocal 4x4.

    Imported bands, neither touched; the cell count asserted **bitwise** equal
    to the record, because the whole measurement is fixed-mesh.  A failure here
    is a fixture finding (known-issues with its widths, stop) and D's residual
    would mean nothing.
    """
    case = step1d_configuration_d
    sweep = case["sweep"]
    reciprocity = float(sweep["reciprocity"])
    sigma_max = float(np.max(sweep["sigma"]))
    cells = int(sweep["cells"])
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-14 step1d] configuration D (all four told widths x "
            f"(1 + mean eps* = {1.0 + case['epsilon']:.9f})): {cells} cells "
            f"(record {STEP1_CELL_RECORD}, same mesh); four 50 Ohm drives in "
            f"{case['baseline_seconds']:.2f} s wall",
            flush=True,
        )
        for idx, (w0, w1) in enumerate(
            zip(case["baseline_widths"], case["widths"]), start=1
        ):
            print(
                f"    P{idx}: sheet_width_m {w0:.9e} -> {w1:.9e} m "
                f"(ratio {w1 / w0:.9f})",
                flush=True,
            )
        print(
            f"    50 Ohm baseline: ||S - S^T||/||S|| = {reciprocity:.9e} "
            f"(band {RECIPROCITY_BAND:.0e}); sigma_max = {sigma_max:.9f} "
            f"(band 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e})",
            flush=True,
        )
    assert cells == STEP1_CELL_RECORD, (
        f"configuration D solved on {cells} cells, not the "
        f"{STEP1_CELL_RECORD}-cell gate mesh — the width perturbation moved the "
        "mesh, so this is not a fixed-mesh measurement"
    )
    assert reciprocity <= RECIPROCITY_BAND, (
        f"configuration D's 50 Ohm 4x4 is reciprocal only to {reciprocity:.3e} "
        f"against the imported {RECIPROCITY_BAND:.0e} band — the fitted width "
        "does not give a valid four-port and its residual means nothing "
        "(§7 `PORT-14` step 1d: known-issues with its widths, stop)"
    )
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"configuration D's 4x4 has sigma_max = {sigma_max:.9f} > 1 + "
        f"{PASSIVITY_SIGMA_TOLERANCE:.0e}: a passive network cannot"
    )


@complex_only
def test_step1d_configuration_d_residuals_are_printed(
    step1d_configuration_d, step1d_fit
):
    """**(b) The fit on a fourth point** — printed, not asserted.

    D's told width was *fitted to* this residual, so asserting the residual
    would be circular; it is printed beside step 1's record and beside
    `REDUCTION_BAND`, and the pre-registered reading it selects is printed with
    it.  The readings are (1) D <= band on both **and** a geometric candidate
    predicts eps*; (2) D <= band with no geometric candidate; (3) D above the
    band — the linear model fails beyond three points.
    """
    case = step1d_configuration_d
    if MPI.COMM_WORLD.rank != 0:
        return
    if _step2_enabled():
        _print_step2e_configuration_d(case, step1d_fit)
        return
    print(
        f"[PORT-14 step1d] configuration D reduction identity residuals at "
        f"f = {FREQUENCY_HZ:.3e} Hz on the {int(case['sweep']['cells'])}-cell "
        "gate mesh. Printed, not asserted (the width was fitted to these "
        "numbers):",
        flush=True,
    )
    under = []
    for entry in case["cases"]:
        record = STEP1_RESIDUAL_RECORD[entry["label"]]
        residual = float(abs(entry["residual"]))
        under.append(residual <= REDUCTION_BAND)
        print(
            f"    {entry['label']:<12s} |Gamma| = {abs(entry['gamma']):.6f}   "
            f"residual = {residual:.6e}   "
            f"(step 1 record {record:.6e}; factor {residual / record:.6f})   "
            f"(band {REDUCTION_BAND:.0e}; ratio to band "
            f"{residual / REDUCTION_BAND:.6f}; "
            f"{'UNDER' if residual <= REDUCTION_BAND else 'OVER'})   "
            f"three drives in {entry['seconds']:.2f} s wall",
            flush=True,
        )
    print(
        f"    r(eps*) predicted ~ 0 by the fit; measured "
        + ", ".join(
            f"{entry['label']} = {float(abs(entry['residual'])):.6e}"
            for entry in case["cases"]
        )
        + f" at eps* = {case['epsilon']:+.6f}",
        flush=True,
    )
    if all(under):
        print(
            "    READING: D is under the band on both elements — reading (1) or "
            "(2), decided by whether a geometric candidate above matched eps*",
            flush=True,
        )
    else:
        print(
            "    READING (3): D is not under the band on both elements — the "
            "linear |r0 + k eps| model does not hold beyond step 1c's three "
            "points; r(eps*) is printed above and step 1d stops here",
            flush=True,
        )


@complex_only
def test_step1d_the_zero_gamma_control_misses_on_configuration_d(
    step1d_configuration_d,
):
    """**Negative control, ceiling first**, exactly as step 1 / 1c ran it.

    Asserted, and backed by the same comparison measured on this mesh
    (`20260905T213322Z_PORT-14-step1c.log:1990-1991`, Delta = 0.31-0.33): Delta
    is computed from D's own 4x4 first and printed as the ceiling, and the
    >= 5x-band miss is asserted only where Delta reaches the floor.
    """
    case = step1d_configuration_d
    s4 = np.asarray(case["sweep"]["s"], dtype=np.complex128)
    kept = [i for i in range(s4.shape[0]) if i != TERMINATED_PORT_INDEX]
    s_aa = s4[np.ix_(kept, kept)]

    rows = []
    for entry in case["cases"]:
        predicted = entry["predicted"]
        delta = float(np.linalg.norm(predicted - s_aa) / np.linalg.norm(predicted))
        miss = float(
            np.linalg.norm(entry["measured"] - s_aa) / np.linalg.norm(predicted)
        )
        rows.append((entry["label"], delta, miss))

    reached = [row for row in rows if row[1] >= CONTROL_DELTA_FLOOR]
    if MPI.COMM_WORLD.rank == 0:
        print(
            "[PORT-14 step1d] configuration D Gamma = 0 control (ceiling first), "
            f"floor {CONTROL_DELTA_FLOOR:.0e}:",
            flush=True,
        )
        for label, delta, miss in rows:
            print(
                f"    {label:<12s} Delta = {delta:.6e}   "
                f"||S'_meas - S_aa||_F/||S'_pred||_F = {miss:.6e}   "
                f"({'asserted' if delta >= CONTROL_DELTA_FLOOR else 'below floor'})",
                flush=True,
            )
        if not reached:
            print(
                "    FINDING: no termination reaches the Delta floor on "
                "configuration D",
                flush=True,
            )

    for label, delta, miss in reached:
        assert miss >= CONTROL_MISS_FACTOR * REDUCTION_BAND, (
            f"{label}: on configuration D the Gamma = 0 prediction S_aa misses "
            f"the measured terminated 3x3 by only {miss:.3e}, under "
            f"{CONTROL_MISS_FACTOR:g}x the {REDUCTION_BAND:.0e} band, though the "
            f"4x4 predicts a coupling term Delta = {delta:.3e}"
        )
