"""`PORT-21` step 1 — the public sensitivity table of the birdcage 4x4's class
entries to three port-model conventions.

**What this is.**  `ANS-4`'s order-matched comparison disagrees with the
independent code on the *self* class at 10 and 64 MHz and agrees on the
couplings (known-issues 2026-09-19; verdict qualitative, numbers private).
This module measures how much **our own** 4x4 moves under each port-model
convention an independent code could legitimately differ in, so a later
(private) reading can be taken against a public table.  **Nothing absolute is
claimed here** — no `S11`, no `Z_in`, no resonance, no tuning.  The identities
below are self-consistency statements on one fixture at degree 1.

**The control comes first.**  If the control solve does not reproduce the gate
record at rtol 1e-9, no variant is read (the step's own negative result).

**Variants, one knob each, all of them knobs
`test_port_birdcage_four_port.build_four_port_sweep` already exposes:**

  (a) the sheet width told as ``w/(1 + kappa)`` with the **in-run** kappa —
      `PORT-14` step 3's default-off opt-in (``width_correction_kappa``);
  (b) the full-width sheet ``f = 1.0`` against the gated interior half
      ``f = 0.5`` — **SKIPPED AND NAMED**: `build_four_port_sweep` narrows every
      sheet with the module-level ``GATED_WIDTH_FRACTION`` and exposes **no**
      width-fraction parameter (`:351-361` of that module, the ninth additive
      parameter is ``width_correction_kappa``, not the fraction).  The step
      forbids building the knob ("a variant whose knob the generator does not
      already expose is skipped and named, not built — this step adds no `src/`
      surface"), so this row of the table is empty by construction, not by
      failure;
  (c) the port-box conductor-side grading halved — ``conductor_resolution =
      0.5 * CONDUCTOR_RESOLUTION`` (`PORT-14` step 1b's fourth additive
      parameter).  This **re-meshes**, so the cell count is *not* the gate
      mesh's and is printed rather than pinned.

      **Step 1b (2026-09-21 review ruling): (c) is REPLACED by (c').**  As
      first built — halved grading on the *uncongruent* cut, 259 509 cells —
      its C4 class spread (self 2.3607 % at 10 MHz) was up to 4x the move it
      was to measure: mesh asymmetry (`GEO-30`..`-32`), not a feed
      sensitivity.  Those numbers stay in the table as a PRINTED RECORD with
      the three parked logs cited (``UNCONGRUENT_C_RECORD``); their gate
      assert is removed *because the variant is replaced*, not because the
      band moved (it did not — 0.5 % stays asserted on every run).  (c') is
      ``c4_congruent_sheets=True`` plus the halved grading, and its
      ``|dS|/|S|`` is read against its own **control'**
      (``c4_congruent_sheets=True`` alone), never against the gate-record
      control.  Both control' and (c') carry every imported identity gate.

**Asserted (identity anchors, every band imported, none restated):**
  * the control reproduces leg (d0)'s registered ``Z`` column at
    ``LEG_D0_REPRODUCTION_BAND`` (1e-9) at 10 MHz, and meshes
    ``STEP1_CELL_RECORD`` cells at every frequency;
  * **every** variant run still passes the imported reciprocity
    (``RECIPROCITY_BAND``), passivity (``PASSIVITY_SIGMA_TOLERANCE``) and C4
    class-spread (``ADJACENT_SPREAD_BAND``) gates;
  * variant (a) reproduces `PORT-14` step 3's registered residual — the
    terminated ``C = 100 pF`` 3x3 against the circuit reduction at
    ``REDUCTION_BAND`` — at its registered frequency
    ``STEP3_REGISTERED_FREQUENCY_HZ`` (64 MHz).

**Negative control (asserted).**  Each variant must move the **self** class by
more than ``KNOB_REACHES_THE_SOLVE`` (1e-6) relative.  A variant that moves
nothing did not reach the solve (the `OPS-41` knob-reaches-the-solve pattern).
The ceiling is O(1e-2) from `PORT-14` step 3's kappa ~ 1 %, so 1e-6 carries
>= 1e4 of headroom; this floor is a wiring check, never a physics band.

**Printed, never asserted:** ``|dS|/|S|`` per class per variant per frequency —
the sensitivity table — and whether each variant's self-class move *falls with
frequency*.

**Trap, from the item:** (b) at ``f = 1.0`` was the pre-`PORT-9` configuration;
had it been runnable, a red gate there would be the row's printed finding, not
a defect to fix.  It is not runnable, so it is named and skipped.

Gated on ``FEM_EM_PORT21_FREQUENCIES_MHZ`` (unset: every test skips, so
`main`'s default collection time and red set are unchanged — the `PORT-22`
step 1 precedent, 2026-09-20).  Per-frequency readings are persisted as JSON
under the gitignored ``logs/port21/`` so a second window can print the table
across frequencies the first window produced.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.ports.shares import terminal_form_deficit

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheet_prerequisite import CONDUCTOR_RESOLUTION
from tests.validation.test_port_birdcage_four_port import (
    ADJACENT_SPREAD_BAND,
    LEG_D0_REPRODUCTION_BAND,
    LEG_D0_Z_COLUMN,
    PASSIVITY_SIGMA_TOLERANCE,
    RECIPROCITY_BAND,
    _circulant_classes,
    build_four_port_sweep,
)
from tests.validation.test_port_lumped_rlc_termination import (
    REDUCTION_BAND,
    STEP1_CELL_RECORD,
    STEP1B_TERMINATIONS,
    STEP3_REGISTERED_FREQUENCY_HZ,
    TERMINATED_PORT_INDEX,
    _terminated_three_port,
    reduce_terminated_ports,
    series_rlc_impedance,
)
from tests.validation.test_port_package_sparameters import REFERENCE_IMPEDANCE_OHM

FREQUENCIES_ENV = "FEM_EM_PORT21_FREQUENCIES_MHZ"

# The `OPS-41` knob-reaches-the-solve floor.  Not a physics band: the moves are
# O(1e-2) by `PORT-14` step 3's kappa ~ 1 %, so this sits >= 1e4 below them and
# only catches a knob that was silently dropped on the way to the solve.
KNOB_REACHES_THE_SOLVE = 1.0e-6

# The frequency at which leg (d0)'s `Z` column was registered (the gate record
# the control must reproduce); at the two Larmor frequencies no `Z` record of
# this column exists, so the control there is the baseline of the table only.
GATE_RECORD_FREQUENCY_HZ = 10.0e6

# Variant (b)'s knob, named for the report and for any later slot that adds it.
SKIPPED_VARIANT_B = (
    "(b) full-width sheet f = 1.0: `build_four_port_sweep` narrows with the "
    "module-level GATED_WIDTH_FRACTION and exposes no width-fraction "
    "parameter; the step forbids building one (no `src/` surface here)"
)

_READINGS_DIR = Path("logs/port21")

# control' (the C4-congruent cut, `c4_congruent_sheets=True`): its cell count
# and class spreads on record, PRINTED BESIDE this run's, never asserted (the
# records were taken at a different rank width).  No congruent-cut record
# exists at 10 MHz; that reading is new here and is printed.
CONTROL_PRIME_CELL_RECORD = 116118
CONTROL_PRIME_SPREAD_RECORDS = {
    64.0e6: ((0.0475, 0.0529, 0.0366), "20260920T070008Z_ANS-4-step3d.log:2548"),
    128.0e6: ((0.0739, 0.0822, 0.0506), "20260917T070008Z_ANS-4-step3b.log:2548"),
}

# Variant (c) AS FIRST BUILT (halved conductor grading on the *uncongruent*
# cut, 259 509 cells), kept as a PRINTED RECORD only.  Its gate assert is
# removed because the variant is REPLACED by (c') - the 2026-09-21 review
# ruled its class spread (self 2.3607 % at 10 MHz, up to 4x the move it was to
# measure) mesh asymmetry (`GEO-30`..`-32`'s mechanism), not a feed
# sensitivity; the 0.5 % band was not moved.  Values copied from the three
# parked-attempt logs, per frequency: (self, adjacent, opposite) moves against
# the gate-record control, (self, adjacent, opposite) spreads in %, log.
UNCONGRUENT_C_RECORD = {
    10.0e6: (
        (5.982326e-03, 2.205190e-03, 7.502789e-04),
        (2.3607, 1.2387, 1.0399),
        "20260920T112548Z_PORT-21.log (also 20260920T111725Z_PORT-21.log)",
    ),
    64.0e6: (
        (1.607415e-02, 6.406405e-03, 1.110089e-02),
        (1.0508, 0.9719, 0.9038),
        "20260920T112548Z_PORT-21.log",
    ),
    128.0e6: (
        (1.668383e-02, 1.296737e-02, 1.846200e-02),
        (0.5553, 0.6751, 0.6914),
        "20260920T112242Z_PORT-21.log",
    ),
}
UNCONGRUENT_C_CELLS = 259509


def _frequencies_hz():
    raw = os.environ.get(FREQUENCIES_ENV, "").strip()
    if raw in ("", "0"):
        return ()
    return tuple(float(tok) * 1.0e6 for tok in raw.split(",") if tok.strip())


def _class_means(s_matrix):
    """Mean complex entry of each C4 class of ``S`` (self / adjacent / opposite)."""
    classes = _circulant_classes(np.asarray(s_matrix, dtype=np.complex128))
    return {name: complex(np.mean(v)) for name, v in classes.items()}


def _relative_move(variant_means, control_means):
    return {
        name: float(
            abs(variant_means[name] - control_means[name]) / abs(control_means[name])
        )
        for name in ("self", "adjacent", "opposite")
    }


def _gate_readings(sweep):
    return {
        "reciprocity": float(sweep["reciprocity"]),
        "sigma_max": float(np.max(sweep["sigma"])),
        "column_power_max": float(np.max(sweep["column_power"])),
        "spreads": {k: float(v) for k, v in sweep["spreads"].items()},
        "cells": int(sweep["cells"]),
    }


def _run_one_frequency(frequency_hz):
    """Control + variants (a) and (c) at one frequency.  (b) is skipped, named."""
    comm = MPI.COMM_WORLD
    record = {"frequency_hz": float(frequency_hz), "skipped": [SKIPPED_VARIANT_B]}

    comm.Barrier()
    t0 = time.perf_counter()
    control = build_four_port_sweep(frequency_hz=frequency_hz)
    comm.Barrier()
    t_control = time.perf_counter() - t0

    control_means = _class_means(control["s"])
    record["control"] = _gate_readings(control)
    record["control"]["seconds"] = float(t_control)
    record["control"]["z_column1"] = [
        [float(z.real), float(z.imag)] for z in control["z"][:, 0]
    ]
    record["control"]["class_means"] = {
        k: [v.real, v.imag] for k, v in control_means.items()
    }

    # --- variant (a): the width told as w/(1 + kappa), kappa computed in-run ---
    from tests.validation.test_birdcage_b1_plus_map import _solve_driven

    comm.Barrier()
    t1 = time.perf_counter()
    solved = _solve_driven(control, "P1")
    sheets = [spec.sheet(driven=(spec.port_id == "P1")) for spec in control["specs"]]
    kappa = float(
        terminal_form_deficit(
            control["mesh"],
            control["facet_tags"],
            sheets,
            solved["fields"].e_complex,
            comm,
        )["pooled"]
    )
    reuse = {
        "mesh": control["mesh"],
        "cell_tags": control["cell_tags"],
        "facet_tags": control["facet_tags"],
        "sheets": control["sheets"],
        "halves": control["halves"],
        "cells": control["cells"],
    }
    variant_a = build_four_port_sweep(
        frequency_hz=frequency_hz, reuse=reuse, width_correction_kappa=kappa
    )
    comm.Barrier()
    t_a = time.perf_counter() - t1

    record["a"] = _gate_readings(variant_a)
    record["a"]["seconds"] = float(t_a)
    record["a"]["kappa"] = kappa
    record["a"]["move"] = _relative_move(_class_means(variant_a["s"]), control_means)

    # `PORT-14` step 3's registered residual, at its registered frequency only.
    if abs(frequency_hz - STEP3_REGISTERED_FREQUENCY_HZ) <= 1.0e-9 * frequency_hz:
        label, element = next(
            (lab, el) for lab, el in STEP1B_TERMINATIONS if lab.startswith("C")
        )
        z_term = series_rlc_impedance(frequency_hz, **element)
        measured, _kept, _res = _terminated_three_port(variant_a, z_term)
        predicted = reduce_terminated_ports(
            variant_a["s"],
            float(REFERENCE_IMPEDANCE_OHM),
            {TERMINATED_PORT_INDEX: z_term},
        )
        record["a"]["registered_residual"] = {
            "label": label,
            "value": float(
                np.linalg.norm(measured - predicted) / np.linalg.norm(predicted)
            ),
        }

    # --- variant (c'): the port-box conductor-side grading halved, measured on
    # the C4-congruent cut against its own congruent control' (step 1b, the
    # 2026-09-21 review ruling).  Both sides of the difference re-mesh together.
    comm.Barrier()
    t3 = time.perf_counter()
    control_prime = build_four_port_sweep(
        frequency_hz=frequency_hz, c4_congruent_sheets=True
    )
    comm.Barrier()
    t_cp0 = time.perf_counter() - t3
    control_prime_means = _class_means(control_prime["s"])
    record["control_prime"] = _gate_readings(control_prime)
    record["control_prime"]["seconds"] = float(t_cp0)
    del control_prime

    comm.Barrier()
    t2 = time.perf_counter()
    variant_c = build_four_port_sweep(
        frequency_hz=frequency_hz,
        c4_congruent_sheets=True,
        conductor_resolution=0.5 * CONDUCTOR_RESOLUTION,
    )
    comm.Barrier()
    t_c = time.perf_counter() - t2

    record["c_prime"] = _gate_readings(variant_c)
    record["c_prime"]["seconds"] = float(t_c)
    record["c_prime"]["conductor_resolution"] = float(0.5 * CONDUCTOR_RESOLUTION)
    record["c_prime"]["move"] = _relative_move(
        _class_means(variant_c["s"]), control_prime_means
    )
    del variant_c

    if comm.rank == 0:
        print(
            f"\n[PORT-21 step1] f = {frequency_hz:.6e} Hz  -n {comm.size}: "
            f"control {t_control:.2f} s ({record['control']['cells']} cells), "
            f"(a) kappa route {t_a:.2f} s (kappa = {kappa:.9e}), "
            f"control' (C4-congruent cut) {t_cp0:.2f} s "
            f"({record['control_prime']['cells']} cells; record "
            f"{CONTROL_PRIME_CELL_RECORD}, printed not asserted), "
            f"(c') halved conductor grading on the congruent cut {t_c:.2f} s "
            f"({record['c_prime']['cells']} cells, h_c = "
            f"{0.5 * CONDUCTOR_RESOLUTION:.4e} m vs "
            f"{CONDUCTOR_RESOLUTION:.4e} m)\n"
            f"    SKIPPED, not built: {SKIPPED_VARIANT_B}",
            flush=True,
        )
        _READINGS_DIR.mkdir(parents=True, exist_ok=True)
        path = _READINGS_DIR / f"f_{frequency_hz / 1.0e6:.3f}MHz.json"
        path.write_text(json.dumps(record, indent=2))
        print(f"[PORT-21 step1] readings persisted to {path}", flush=True)
    return record


@pytest.fixture(scope="module")
def port21_runs():
    frequencies = _frequencies_hz()
    if not frequencies:
        pytest.skip(
            f"{FREQUENCIES_ENV} unset — `PORT-21` step 1 runs only when a slot asks"
        )
    return [_run_one_frequency(f) for f in frequencies]


@complex_only
def test_the_control_reproduces_the_gate_record(port21_runs):
    """**The control.**  Nothing else is read if this fails (the step's own rule).

    At 10 MHz the control column must land on leg (d0)'s registered ``Z``
    column at the imported ``LEG_D0_REPRODUCTION_BAND`` (1e-9); at every
    frequency the control must mesh the imported ``STEP1_CELL_RECORD`` cells,
    or the variants below are not perturbations of the gate fixture at all.
    """
    comm = MPI.COMM_WORLD
    for record in port21_runs:
        cells = record["control"]["cells"]
        assert cells == STEP1_CELL_RECORD, (
            f"the control at f = {record['frequency_hz']:.3e} Hz meshed {cells} "
            f"cells against the gate record {STEP1_CELL_RECORD} — this is not "
            "the gate fixture and no variant below is readable"
        )

    at_record = [
        r
        for r in port21_runs
        if abs(r["frequency_hz"] - GATE_RECORD_FREQUENCY_HZ)
        <= 1.0e-9 * GATE_RECORD_FREQUENCY_HZ
    ]
    if not at_record:
        pytest.skip(
            "this window carries no 10 MHz rung, so leg (d0)'s registered Z "
            "column is not reproducible here; the cell-count control above ran"
        )
    column = np.array(
        [complex(re, im) for re, im in at_record[0]["control"]["z_column1"]],
        dtype=np.complex128,
    )
    if comm.rank == 0:
        print(
            f"\n[PORT-21 step1] CONTROL: the P1-driven column vs leg (d0)'s "
            f"record, imported band {LEG_D0_REPRODUCTION_BAND:.0e}:",
            flush=True,
        )
        for k, (z, z_rec) in enumerate(zip(column, LEG_D0_Z_COLUMN), start=1):
            print(
                f"    Z_{k}1 {z:+.9e} vs record {z_rec:+.9e}  rel "
                f"{abs(z - z_rec) / abs(z_rec):.3e}",
                flush=True,
            )
    for k, (z, z_rec) in enumerate(zip(column, LEG_D0_Z_COLUMN), start=1):
        err = abs(z - z_rec) / abs(z_rec)
        assert err < LEG_D0_REPRODUCTION_BAND, (
            f"Z_{k}1 deviates {err:.3e} from leg (d0)'s record against the "
            f"imported {LEG_D0_REPRODUCTION_BAND:.0e} band — record drift on "
            "`main`; no variant in this table is read (known-issues, stop)"
        )


@complex_only
def test_every_variant_still_passes_the_imported_identity_gates(port21_runs):
    """**Anchor (asserted).**  Reciprocity, passivity and C4 hold under each knob.

    Every band is imported from `test_port_birdcage_four_port`; none is
    restated and none is moved.  A red row here would be this row's printed
    finding about that convention, not a defect to fix — but it is still
    asserted, because the step's anchor says every variant run passes.
    """
    comm = MPI.COMM_WORLD
    # Collected, not short-circuited: the step wants the *whole* table printed
    # even when a row is red, because a red row is a printed finding about that
    # convention.  Every band below is still the imported one and every failure
    # below is still a failure — only the reporting order changes.
    misses = []
    for record in port21_runs:
        for key in ("control", "a", "control_prime", "c_prime"):
            g = record[key]
            if comm.rank == 0:
                print(
                    f"\n[PORT-21 step1] gates, f = {record['frequency_hz']:.3e} Hz, "
                    f"variant {key} ({g['cells']} cells):\n"
                    f"    ||S - S^T||/||S|| = {g['reciprocity']:.9e} "
                    f"(band {RECIPROCITY_BAND:.0e})\n"
                    f"    sigma_max = {g['sigma_max']:.9f}, max column power "
                    f"{g['column_power_max']:.9f} "
                    f"(tol {PASSIVITY_SIGMA_TOLERANCE:.0e})\n"
                    f"    class spreads: self {g['spreads']['self'] * 100:.4f}%  "
                    f"adjacent {g['spreads']['adjacent'] * 100:.4f}%  "
                    f"opposite {g['spreads']['opposite'] * 100:.4f}%  "
                    f"(band {ADJACENT_SPREAD_BAND * 100:.1f}%)",
                    flush=True,
                )
                if key == "control_prime":
                    rec = CONTROL_PRIME_SPREAD_RECORDS.get(record["frequency_hz"])
                    if rec:
                        beside = (
                            f"{rec[0][0]:.4f} / {rec[0][1]:.4f} / "
                            f"{rec[0][2]:.4f}% ({rec[1]})"
                        )
                    else:
                        beside = (
                            "NONE - no congruent-cut record exists at this "
                            "frequency; this reading is new"
                        )
                    print(
                        "    control' spreads on record (printed beside, not "
                        f"asserted; different rank width): {beside}; cells on "
                        f"record {CONTROL_PRIME_CELL_RECORD}",
                        flush=True,
                    )
            tag = f"variant {key} at {record['frequency_hz']:.3e} Hz"
            if g["reciprocity"] > RECIPROCITY_BAND:
                misses.append(
                    f"{tag}: ||S - S^T||/||S|| = {g['reciprocity']:.9e} against "
                    f"the imported {RECIPROCITY_BAND:.0e}"
                )
            if g["sigma_max"] > 1.0 + PASSIVITY_SIGMA_TOLERANCE:
                misses.append(
                    f"{tag}: sigma_max = {g['sigma_max']:.9f} — the network is active"
                )
            if g["column_power_max"] > 1.0 + PASSIVITY_SIGMA_TOLERANCE:
                misses.append(
                    f"{tag}: column power {g['column_power_max']:.9f} > 1 — it "
                    "returns more power than it is fed"
                )
            for name, spread in g["spreads"].items():
                if spread > ADJACENT_SPREAD_BAND:
                    misses.append(
                        f"{tag}: the {name} class spreads {spread * 100:.4f}% "
                        f"against the imported {ADJACENT_SPREAD_BAND * 100:.1f}%"
                    )
    assert not misses, (
        "imported identity gates missed under a port-model convention (bands "
        "imported and unmoved; a red row is a finding about that convention, "
        "never a licence to widen):\n  " + "\n  ".join(misses)
    )


@complex_only
def test_variant_a_reproduces_the_port14_step3_registered_residual(port21_runs):
    """**Anchor (asserted).**  (a)'s terminated ``C`` residual <= ``REDUCTION_BAND``.

    `PORT-14` step 3's registered reading, at its registered frequency, on the
    identical corrected route: the terminated 3x3 measured in the field against
    the circuit reduction of the corrected 4x4.  Band imported, not restated.
    """
    comm = MPI.COMM_WORLD
    rows = [r for r in port21_runs if "registered_residual" in r["a"]]
    if not rows:
        pytest.skip(
            "this window carries no "
            f"{STEP3_REGISTERED_FREQUENCY_HZ:.3e} Hz rung, so `PORT-14` step 3's "
            "registered residual is not reproducible here"
        )
    for record in rows:
        entry = record["a"]["registered_residual"]
        if comm.rank == 0:
            print(
                f"\n[PORT-21 step1] anchor (a), f = {record['frequency_hz']:.3e} Hz: "
                f"`PORT-14` step 3's registered residual, termination "
                f"{entry['label']}: {entry['value']:.6e} "
                f"({entry['value'] / REDUCTION_BAND:.3f}x the imported band "
                f"{REDUCTION_BAND:.0e})   kappa in-run = {record['a']['kappa']:.9e}",
                flush=True,
            )
        assert entry["value"] <= REDUCTION_BAND, (
            f"variant (a) reads residual {entry['value']:.6e} against the "
            f"imported REDUCTION_BAND {REDUCTION_BAND:.0e} — the corrected "
            "route here is not `PORT-14` step 3's"
        )


@complex_only
def test_each_variant_reached_the_solve(port21_runs):
    """**Negative control (asserted).**  Each knob moves the self class > 1e-6.

    The `OPS-41` knob-reaches-the-solve pattern: a variant that moves nothing
    was dropped somewhere between the keyword and the assembled form, and its
    table row would read as "this convention does not matter" when in fact it
    was never applied.  The floor is a wiring check with >= 1e4 of headroom
    against the O(1e-2) moves `PORT-14` step 3's kappa ~ 1 % implies.
    """
    comm = MPI.COMM_WORLD
    for record in port21_runs:
        for key in ("a", "c_prime"):
            move = record[key]["move"]["self"]
            if comm.rank == 0:
                print(
                    f"[PORT-21 step1] knob-reaches-the-solve, f = "
                    f"{record['frequency_hz']:.3e} Hz, variant {key}: self-class "
                    f"move {move:.6e} against the {KNOB_REACHES_THE_SOLVE:.0e} "
                    f"floor ({move / KNOB_REACHES_THE_SOLVE:.3e}x)",
                    flush=True,
                )
            assert move > KNOB_REACHES_THE_SOLVE, (
                f"variant {key} at {record['frequency_hz']:.3e} Hz moved the "
                f"self class by {move:.6e} <= {KNOB_REACHES_THE_SOLVE:.0e} — the "
                "knob did not reach the solve, so its table row is not a "
                "measurement of that convention"
            )


@complex_only
def test_the_sensitivity_table_is_printed(port21_runs):
    """**Printed, never asserted.**  ``|dS|/|S|`` per class per variant per frequency.

    Reads every per-frequency JSON this slot's windows persisted, so the last
    window prints the whole table even though each window solved part of it.
    The frequency trend of each variant's self-class move — whether it *falls*
    with frequency — is printed as a word, and asserted nowhere: it is the
    reading a later private step takes against the residual, not a gate.
    """
    comm = MPI.COMM_WORLD
    if comm.rank != 0:
        return
    rows = []
    for path in sorted(_READINGS_DIR.glob("f_*MHz.json")):
        rows.append(json.loads(path.read_text()))
    rows.sort(key=lambda r: r["frequency_hz"])
    print(
        "\n[PORT-21 step1] SENSITIVITY TABLE — |dS|/|S| per C4 class, variant "
        "against the control on the same fixture (PRINTED, NEVER ASSERTED; no "
        "absolute S11 claim is licensed here — known-issues 2026-09-19):",
        flush=True,
    )
    print(
        f"    {'f (MHz)':>9s}  {'variant':<8s}  {'self':>13s}  {'adjacent':>13s}  "
        f"{'opposite':>13s}   cells",
        flush=True,
    )
    for record in rows:
        for key in ("a", "c_prime"):
            if key not in record:
                continue
            m = record[key]["move"]
            print(
                f"    {record['frequency_hz'] / 1e6:9.3f}  {key:<8s}  "
                f"{m['self']:13.6e}  {m['adjacent']:13.6e}  "
                f"{m['opposite']:13.6e}   {record[key]['cells']}",
                flush=True,
            )
    for key in ("a", "c_prime"):
        series = [
            (r["frequency_hz"] / 1e6, r[key]["move"]["self"])
            for r in rows
            if key in r
        ]
        if len(series) < 2:
            print(
                f"    variant {key}: frequency trend needs >= 2 rungs; this run "
                f"has {len(series)}",
                flush=True,
            )
            continue
        falls = all(b[1] < a[1] for a, b in zip(series, series[1:]))
        rises = all(b[1] > a[1] for a, b in zip(series, series[1:]))
        trend = "FALLS with frequency" if falls else (
            "RISES with frequency" if rises else "is non-monotonic in frequency"
        )
        print(
            f"    variant {key}: the self-class move {trend} — "
            + ", ".join(f"{f:.0f} MHz {v:.3e}" for f, v in series),
            flush=True,
        )
    print(
        "    (c') is read against control' (the C4-congruent cut), never against "
        "the gate-record control; (a) against the gate-record control.",
        flush=True,
    )
    print(
        "    RECORD, not re-run - variant (c) as first built on the UNCONGRUENT "
        f"cut ({UNCONGRUENT_C_CELLS} cells), replaced by (c'); its class spread "
        "exceeds the move it was to measure (mesh asymmetry, 2026-09-21 ruling):",
        flush=True,
    )
    for f_hz, (mv, sp, log) in sorted(UNCONGRUENT_C_RECORD.items()):
        print(
            f"    {f_hz / 1e6:9.3f}  c(rec)    {mv[0]:13.6e}  {mv[1]:13.6e}  "
            f"{mv[2]:13.6e}   spreads {sp[0]:.4f}/{sp[1]:.4f}/{sp[2]:.4f}%  "
            f"[{log}]",
            flush=True,
        )
    print(f"    SKIPPED, not built: {SKIPPED_VARIANT_B}", flush=True)
