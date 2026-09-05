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

**What this is not.**  Not an absolute-accuracy claim, not a resonance or tuning
claim, not a coil-loading number: it is a self-consistency identity between two
routes on one fixture at one frequency, exactly as `PORT-9`/`PORT-11` are.  Read
PROJECT_PLAN.md §2 before quoting anything here.  10 MHz only — 64 MHz is step 2
on `PORT-11`'s fixture.

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
from tests.mesh.test_birdcage_port_sheet_prerequisite import CONDUCTOR_RESOLUTION
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
    sweep = build_four_port_sweep(frequency_hz=FREQUENCY_HZ)
    cases = []
    for label, element in TERMINATIONS:
        z_term = series_rlc_impedance(FREQUENCY_HZ, **element)
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
            f"f = {FREQUENCY_HZ:.3e} Hz on the {sweep['cells']}-cell 4-leg fixture; "
            f"terminated port index {TERMINATED_PORT_INDEX} "
            f"(z0 = {REFERENCE_IMPEDANCE_OHM:.6e} Ohm)",
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
    assert reciprocity <= RECIPROCITY_BAND, (
        f"the 50 Ohm 4x4 is reciprocal only to {reciprocity:.3e} against the "
        f"imported {RECIPROCITY_BAND:.0e} band — this is not `PORT-9`'s matrix"
    )
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"the 50 Ohm 4x4 has sigma_max = {sigma_max:.9f} > 1 + "
        f"{PASSIVITY_SIGMA_TOLERANCE:.0e}: a passive network cannot"
    )


@complex_only
def test_the_terminated_solve_matches_the_circuit_reduction(rlc_termination_cases):
    """**The gate.**  Field-solved terminated 3×3 == reduction of the 50 Ω 4×4.

    Pre-stated band ``1e-3`` (`PORT-14` §7 entry), asserted as written for each
    of the capacitor, the inductor and the resistor.  Every residual is printed
    before any assertion, so a miss is a measurement in the log whether or not
    the assertion survives it.
    """
    residuals = []
    for case in rlc_termination_cases["cases"]:
        predicted = case["predicted"]
        residual = float(
            np.linalg.norm(case["measured"] - predicted) / np.linalg.norm(predicted)
        )
        case["residual"] = residual
        residuals.append((case["label"], residual))

    if MPI.COMM_WORLD.rank == 0:
        print("[PORT-14 step1] reduction identity residuals (band 1e-3):", flush=True)
        for case in rlc_termination_cases["cases"]:
            print(
                f"    {case['label']:<12s} ||S'_meas - S'_pred||_F/||S'_pred||_F = "
                f"{case['residual']:.6e}",
                flush=True,
            )
            for row in range(case["measured"].shape[0]):
                meas = "  ".join(f"{v:+.6e}" for v in case["measured"][row])
                pred = "  ".join(f"{v:+.6e}" for v in case["predicted"][row])
                print(f"        meas row {row}: {meas}", flush=True)
                print(f"        pred row {row}: {pred}", flush=True)

    for label, residual in residuals:
        assert residual <= REDUCTION_BAND, (
            f"{label}: the field-solved terminated 3x3 differs from the circuit "
            f"reduction of the 50 Ohm 4x4 by {residual:.3e}, above the pre-stated "
            f"{REDUCTION_BAND:.0e} band. The identity is exact for a single-mode "
            "port, so this is a statement about how lumped the sheet is — do not "
            "widen the band (PROJECT_PLAN §9 item 2, negative-result protocol)"
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
                "coupling is too weak for this control at 10 MHz; no factor is "
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

# Step 1's printed record, `20260905T020428Z_PORT-14.log`, restated here as the
# comparison line for the printout (it is a logged number, not a constant any
# module exports).
STEP1_CELL_RECORD = 116085
STEP1_RESIDUAL_RECORD = {"C = 100 pF": 1.595580e-03, "L = 1 uH": 3.370512e-03}

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
