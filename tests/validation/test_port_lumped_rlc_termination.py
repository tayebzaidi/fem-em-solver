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
