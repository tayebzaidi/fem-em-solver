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
        measured, kept_ids, _results = _terminated_three_port(sweep, z_term)
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
    comm.Barrier()
    t0 = time.perf_counter()
    sweep = build_four_port_sweep(frequency_hz=FREQUENCY_HZ)
    comm.Barrier()
    seconds = time.perf_counter() - t0
    widths = [float(spec.sheet_width_m) for spec in sweep["specs"]]
    if comm.rank == 0:
        print(
            f"\n[PORT-14 step1c] baseline (unperturbed) gate rung: "
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

    comm.Barrier()
    t0 = time.perf_counter()
    sweep = build_four_port_sweep(frequency_hz=FREQUENCY_HZ, reuse=reuse)
    comm.Barrier()
    baseline_seconds = time.perf_counter() - t0

    cases = []
    for label, element in STEP1B_TERMINATIONS:
        z_term = series_rlc_impedance(FREQUENCY_HZ, **element)
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
            f"\n[PORT-14 step1c] configuration {case['key']} ({case['description']}): "
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
        f"reduction identity residuals at f = {FREQUENCY_HZ:.3e} Hz on the "
        f"{int(case['sweep']['cells'])}-cell gate mesh; step 1's record is on the "
        "same mesh with the unperturbed widths. Printed, not asserted:",
        flush=True,
    )
    for entry in case["cases"]:
        record = STEP1_RESIDUAL_RECORD[entry["label"]]
        print(
            f"    {entry['label']:<12s} |Gamma| = {abs(entry['gamma']):.6f}   "
            f"residual = {entry['residual']:.6e}   "
            f"(step 1 record {record:.6e}; factor "
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
            f"[PORT-14 step1c] configuration {case['key']} Gamma = 0 control "
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
    """eps* per element from step 1c's constants — arithmetic, no solve."""
    fit = {}
    for label, points in STEP1C_RESIDUALS.items():
        star, r2_star, a, b, c = _epsilon_star(points)
        fit[label] = {
            "eps_star": star,
            "r2_star": r2_star,
            "a": a,
            "b": b,
            "c": c,
        }
    mean_star = float(np.mean([v["eps_star"] for v in fit.values()]))
    return {"per_element": fit, "mean_eps_star": mean_star}


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
    sweep = build_four_port_sweep(frequency_hz=FREQUENCY_HZ)
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
    sweep = build_four_port_sweep(frequency_hz=FREQUENCY_HZ, reuse=reuse)
    comm.Barrier()
    baseline_seconds = time.perf_counter() - t0

    cases = []
    for label, element in STEP1B_TERMINATIONS:
        z_term = series_rlc_impedance(FREQUENCY_HZ, **element)
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
            f"{entry['c']:.6e}, from step 1c's three printed residuals)",
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
