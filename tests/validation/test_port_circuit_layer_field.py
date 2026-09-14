"""`PORT-15` step 2 — gate (i) from the circuit side, on stored field records.

The 116 085-cell F-small gate mesh (the `PORT-9` / `PORT-14` fixture), `-n 2`:

* at 64 MHz, the ε = 0 4×4 through ``build_four_port_sweep`` with the
  (1 + κ)-corrected width (`PORT-14` step 3's opt-in, κ = the registered
  ``STEP2D_C_OVER_TERMINAL_64MHZ_P1``), and the capacitor- and
  inductor-terminated 3×3s on the same corrected specs;
* at 10 MHz (``FREQUENCY_HZ``), the uncorrected 4×4 and the C / L / R
  terminated 3×3s — `PORT-14` step 1e's ``REDUCTION_FLOOR_F_SMALL`` route.

All matrices are stored below as module records (full-precision complex, 50 Ω
reference impedance, set at ``RECORD_RANK_WIDTH``).  Anchors:

(a) *asserted*: the live matrices reproduce the records, ‖live − rec‖_F /
    ‖rec‖_F ≤ ``RECORD_RTOL`` = 1e-6 (at ``RECORD_RANK_WIDTH`` only);
(b) *asserted*: ``reduce_terminated_ports`` on the *stored* 64 MHz 4×4 against
    the *stored* terminated 3×3s ≤ the imported ``REDUCTION_BAND`` (C and L) —
    field-free, so step 3 can reduce without a solve;
(c) *asserted*: ``REDUCTION_FLOOR_F_SMALL`` reproduces from the stored 10 MHz
    4×4 and 3×3s at the imported ``REDUCTION_FLOOR_RTOL`` (1e-3).

*Predicted, printed, never asserted*: terminating the stored 4×4 in 2 × C moves
(b)'s residual by ≫ 1e-3.  *Printed*: inductances read off ``Im Z / ω`` of the
stored 10 MHz 4×4 (``s_to_z``); no closed form claims them.

Scope: no tuning, no resonance, no mode frequencies.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.ports.circuit import reduce_terminated_ports, s_to_z
from fem_em_solver.ports.lumped import series_rlc_impedance

from tests.complex_mode import complex_only
from tests.validation.test_port_birdcage_four_port import build_four_port_sweep
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ
from tests.validation.test_port_lumped_rlc_termination import (
    RECORD_RANK_WIDTH as PORT14_RECORD_RANK_WIDTH,
    REDUCTION_BAND,
    REDUCTION_FLOOR_F_SMALL,
    REDUCTION_FLOOR_RTOL,
    STEP1_CELL_RECORD,
    STEP2D_C_OVER_TERMINAL_64MHZ_P1,
    STEP3_REGISTERED_FREQUENCY_HZ,
    TERMINATED_PORT_INDEX,
    TERMINATIONS,
    _terminated_three_port,
)
from tests.validation.test_port_package_sparameters import REFERENCE_IMPEDANCE_OHM

# Records are `-n 2` records (the `OPS-41` pattern); another width prints only.
RECORD_RANK_WIDTH = 2
assert RECORD_RANK_WIDTH == PORT14_RECORD_RANK_WIDTH

RECORD_RTOL = 1.0e-6

# The 2 x C negative control's *predicted* floor on the residual move — printed
# beside the measured move, never asserted (§9 rule (e): no prior measurement of
# this comparison on this fixture).
NEGATIVE_CONTROL_PREDICTED_MOVE = 1.0e-3

_LABELS_64 = ("C = 100 pF", "L = 1 uH")
_LABELS_10 = ("C = 100 pF", "L = 1 uH", "R = 200 Ohm")

# --- the records -----------------------------------------------------------
# Source of every record: ``docs/testing/logs/20260914T010149Z_PORT-15.log``
# (this module's measurement window, `-n 2`, 116 085 cells); line numbers per
# record.  New records — a later change that moves them is a change to the sheet,
# the width or the fixture and must say so, never a re-record in passing.
S_64MHZ_EPS0_RECORD = np.array([
    [(0.04096032094515905+0.588438126273243j), (0.36869876847822247-0.20763176502125394j), (0.2175640063260772-0.2589766893184673j), (0.36885610834042515-0.20750858519022258j)],
    [(0.3686987684782226-0.20763176502125388j), (0.0410990690416122+0.588462522735609j), (0.36865120652430045-0.20756213008361019j), (0.2176478860085907-0.2589825900939549j)],
    [(0.21756400632607795-0.25897668931846657j), (0.3686512065243011-0.20756213008360905j), (0.04128575558847447+0.5883159795863748j), (0.36862349903114905-0.20749025534563978j)],
    [(0.3688561083404254-0.2075085851902212j), (0.21764788600859156-0.25898259009395413j), (0.36862349903114905-0.2074902553456397j), (0.040899285519791384+0.5883497836949023j)],
], dtype=np.complex128)
"""64 MHz ε = 0 4×4, **50 Ω reference impedance**, κ-corrected width
(κ = ``STEP2D_C_OVER_TERMINAL_64MHZ_P1``), ports P1..P4.  Log :1902–1907."""

S_64MHZ_TERMINATED_C_RECORD = np.array([
    [(-0.15896440742355208+0.7611698008127739j), (0.26746775861313826-0.02210515224469384j), (0.017472861817405805-0.08633128660988987j)],
    [(0.26746775861312616-0.02210515224468717j), (0.017679229408695596+0.7555295770616381j), (0.2673408487665807-0.022043820811387258j)],
    [(0.01747286181740617-0.08633128660988985j), (0.2673408487665842-0.022043820811380715j), (-0.15938728172611794+0.760945053997503j)],
], dtype=np.complex128)
"""64 MHz 3×3 (P2..P4), **50 Ω reference**, P1 terminated in 100 pF, corrected
width.  Log :1908–1912."""

S_64MHZ_TERMINATED_L_RECORD = np.array([
    [(0.1784314264161706+0.5468241980907841j), (0.45972047252613346-0.2773101463144525j), (0.35502328034306674-0.30056856575583146j)],
    [(0.45972047252613363-0.27731014631445017j), (0.08983665645822514+0.5105322507454544j), (0.45973968015355254-0.2772111905245347j)],
    [(0.35502328034306724-0.30056856575583j), (0.45973968015355254-0.27721119052453536j), (0.1783177017632695+0.5468161854897234j)],
], dtype=np.complex128)
"""64 MHz 3×3 (P2..P4), **50 Ω reference**, P1 terminated in 1 µH, corrected
width.  Log :1913–1917."""

S_10MHZ_EPS0_RECORD = np.array([
    [(-0.3712480826229221+0.1417750480315299j), (0.46710240751656223-0.041777467794962254j), (0.43692879315524397-0.07151541640516348j), (0.4671206517942747-0.04178189147804042j)],
    [(0.46710240751656146-0.041777467794969825j), (-0.37122380826283563+0.14175320711906597j), (0.4670287302578389-0.041745836524977674j), (0.43699814599286685-0.07153035555845971j)],
    [(0.43692879315524336-0.0715154164051673j), (0.4670287302578397-0.04174583652497423j), (-0.3710071039219082+0.14172799249526263j), (0.46695595163695913-0.041765219669900815j)],
    [(0.4671206517942744-0.04178189147803934j), (0.43699814599286824-0.07153035555845194j), (0.4669559516369588-0.04176521966989565j), (-0.37117289843528445+0.14177968427047544j)],
], dtype=np.complex128)
"""10 MHz 4×4, **50 Ω reference impedance**, uncorrected width (the step 1e
route; S11/S21 agree with ``STEP1E_S11_S21_10MHZ`` to the printed digit).  Log
:1918–1923."""

S_10MHZ_TERMINATED_RECORDS = {
    "C = 100 pF": np.array([
        [(-0.22052238260823231+0.055497976800163835j), (0.6029815666218163-0.13334267459628804j), (0.5877050260671661-0.15778989419733452j)],
        [(0.6029815666217788-0.13334267459639468j), (-0.24930900074654927+0.04611773613902059j), (0.6029136268873555-0.13336649006510604j)],
        [(0.5877050260671222-0.1577898941974242j), (0.6029136268873567-0.13336649006509965j), (-0.2204605637547934+0.05551583710999344j)],
    ], dtype=np.complex128),
    "L = 1 uH": np.array([
        [(-0.26172946163106475+0.27765637055387615j), (0.5794872181046065+0.07867251624413349j), (0.5464976333238316+0.06437753930020826j)],
        [(0.5794872181046555+0.07867251624396865j), (-0.25682445432130646+0.2473621989075926j), (0.5794196057418518+0.07865723389338376j)],
        [(0.5464976333238585+0.0643775393000692j), (0.5794196057418515+0.07865723389339112j), (-0.26166827017746486+0.2776923107067478j)],
    ], dtype=np.complex128),
    "R = 200 Ohm": np.array([
        [(-0.2638340723487933+0.1300324741074908j), (0.5673356030084661-0.06017986740403015j), (0.5443920637930691-0.08325218927408856j)],
        [(0.5673356030084662-0.060179867404030966j), (-0.2778316886500638+0.11746090786602438j), (0.5672666860773957-0.06020057502815716j)],
        [(0.5443920637930705-0.08325218927407826j), (0.567266686077396-0.06020057502814554j), (-0.2637747985927443+0.13005674978250828j)],
    ], dtype=np.complex128),
}
"""10 MHz 3×3s (P2..P4), **50 Ω reference**, keyed by `TERMINATIONS` label,
uncorrected width.  Log :1924–1938."""


def _element(label):
    return dict(TERMINATIONS)[label]


def _residual(measured, predicted):
    return float(np.linalg.norm(measured - predicted) / np.linalg.norm(predicted))


def _reduce(s4, frequency_hz, element):
    z_term = series_rlc_impedance(frequency_hz, **element)
    return reduce_terminated_ports(
        np.asarray(s4, dtype=np.complex128),
        float(REFERENCE_IMPEDANCE_OHM),
        {TERMINATED_PORT_INDEX: z_term},
    )


def _literal(name, matrix):
    rows = ",\n".join(
        "    [" + ", ".join(repr(complex(v)) for v in row) + "]" for row in matrix
    )
    return f"{name} = np.array([\n{rows},\n], dtype=np.complex128)"


@pytest.fixture(scope="module")
def live_matrices():
    comm = MPI.COMM_WORLD
    comm.Barrier()
    t0 = time.perf_counter()
    s10 = build_four_port_sweep(frequency_hz=FREQUENCY_HZ)
    terminated_10 = {}
    for label in _LABELS_10:
        z = series_rlc_impedance(FREQUENCY_HZ, **_element(label))
        terminated_10[label], _, _ = _terminated_three_port(s10, z)
    comm.Barrier()
    t10 = time.perf_counter() - t0

    reuse = {k: s10[k] for k in ("mesh", "cell_tags", "facet_tags", "sheets", "halves", "cells")}
    comm.Barrier()
    t1 = time.perf_counter()
    s64 = build_four_port_sweep(
        frequency_hz=STEP3_REGISTERED_FREQUENCY_HZ,
        reuse=reuse,
        width_correction_kappa=float(STEP2D_C_OVER_TERMINAL_64MHZ_P1),
    )
    terminated_64 = {}
    for label in _LABELS_64:
        z = series_rlc_impedance(STEP3_REGISTERED_FREQUENCY_HZ, **_element(label))
        terminated_64[label], _, _ = _terminated_three_port(s64, z)
    comm.Barrier()
    t64 = time.perf_counter() - t1

    out = {
        "cells": int(s10["cells"]),
        "S_10MHZ_EPS0": np.asarray(s10["s"], dtype=np.complex128),
        "S_10MHZ_TERMINATED": {k: np.asarray(v) for k, v in terminated_10.items()},
        "S_64MHZ_EPS0": np.asarray(s64["s"], dtype=np.complex128),
        "S_64MHZ_TERMINATED_C": np.asarray(terminated_64["C = 100 pF"]),
        "S_64MHZ_TERMINATED_L": np.asarray(terminated_64["L = 1 uH"]),
    }
    if comm.rank == 0:
        print(
            f"\n[PORT-15 step2] {out['cells']}-cell gate mesh, -n {comm.size}: 10 MHz "
            f"4x4 + C/L/R 3x3s {t10:.2f} s; 64 MHz corrected (kappa "
            f"{STEP2D_C_OVER_TERMINAL_64MHZ_P1:.6e}) 4x4 + C/L 3x3s {t64:.2f} s",
            flush=True,
        )
        print("[PORT-15 step2] live matrices, full precision (50 Ohm reference):")
        print(_literal("S_64MHZ_EPS0_RECORD", out["S_64MHZ_EPS0"]))
        print(_literal("S_64MHZ_TERMINATED_C_RECORD", out["S_64MHZ_TERMINATED_C"]))
        print(_literal("S_64MHZ_TERMINATED_L_RECORD", out["S_64MHZ_TERMINATED_L"]))
        print(_literal("S_10MHZ_EPS0_RECORD", out["S_10MHZ_EPS0"]))
        for label in _LABELS_10:
            print(_literal(f"S_10MHZ_TERMINATED[{label!r}]", out["S_10MHZ_TERMINATED"][label]))
        print("", flush=True)
    return out


def _pairs():
    return [
        ("S_64MHZ_EPS0_RECORD", "S_64MHZ_EPS0", S_64MHZ_EPS0_RECORD, None),
        ("S_64MHZ_TERMINATED_C_RECORD", "S_64MHZ_TERMINATED_C", S_64MHZ_TERMINATED_C_RECORD, None),
        ("S_64MHZ_TERMINATED_L_RECORD", "S_64MHZ_TERMINATED_L", S_64MHZ_TERMINATED_L_RECORD, None),
        ("S_10MHZ_EPS0_RECORD", "S_10MHZ_EPS0", S_10MHZ_EPS0_RECORD, None),
    ] + [
        (
            f"S_10MHZ_TERMINATED_RECORDS[{label!r}]",
            "S_10MHZ_TERMINATED",
            None if S_10MHZ_TERMINATED_RECORDS is None else S_10MHZ_TERMINATED_RECORDS[label],
            label,
        )
        for label in _LABELS_10
    ]


def _records_present():
    return all(rec is not None for _, _, rec, _ in _pairs())


@complex_only
def test_a_live_matrices_reproduce_the_stored_records(live_matrices):
    """(a) ‖live − record‖_F / ‖record‖_F ≤ 1e-6, each matrix, at -n 2."""
    comm = MPI.COMM_WORLD
    assert live_matrices["cells"] == STEP1_CELL_RECORD
    rows = []
    for name, key, record, label in _pairs():
        live = live_matrices[key] if label is None else live_matrices[key][label]
        rel = None if record is None else _residual(live, np.asarray(record))
        rows.append((name, rel))
    if comm.rank == 0:
        print(f"\n[PORT-15 step2] (a) record reproduction (ASSERTED rtol {RECORD_RTOL:.0e}):")
        for name, rel in rows:
            print(f"    {name:<44s} " + ("no record" if rel is None else f"{rel:.3e}"), flush=True)
    if not _records_present():
        pytest.skip("records not yet stored — measurement window")
    if comm.size != RECORD_RANK_WIDTH:
        pytest.skip(f"records are -n {RECORD_RANK_WIDTH}; this is -n {comm.size}")
    for name, rel in rows:
        assert rel <= RECORD_RTOL, (
            f"{name}: live matrix misses its record by {rel:.3e} > {RECORD_RTOL:.0e} — "
            "a width or reproducibility drift: known-issues, stop, never re-record in-slot"
        )


@complex_only
def test_b_reduction_identity_from_the_stored_64mhz_records():
    """(b) stored 4×4 reduced at C / L vs stored 3×3s ≤ REDUCTION_BAND; 2×C printed."""
    if not _records_present():
        pytest.skip("records not yet stored — measurement window")
    f = STEP3_REGISTERED_FREQUENCY_HZ
    stored = {"C = 100 pF": S_64MHZ_TERMINATED_C_RECORD, "L = 1 uH": S_64MHZ_TERMINATED_L_RECORD}
    residuals = {
        label: _residual(np.asarray(stored[label]), _reduce(S_64MHZ_EPS0_RECORD, f, _element(label)))
        for label in _LABELS_64
    }
    doubled = {"c_f": 2.0 * _element("C = 100 pF")["c_f"]}
    residual_2c = _residual(
        np.asarray(S_64MHZ_TERMINATED_C_RECORD), _reduce(S_64MHZ_EPS0_RECORD, f, doubled)
    )
    move = residual_2c - residuals["C = 100 pF"]
    if MPI.COMM_WORLD.rank == 0:
        print(f"\n[PORT-15 step2] (b) reduction identity on stored records at {f:.3e} Hz "
              f"(ASSERTED <= REDUCTION_BAND {REDUCTION_BAND:.0e}):")
        for label, r in residuals.items():
            print(f"    {label:<12s} residual {r:.6e}   ratio to band {r / REDUCTION_BAND:.6f}")
        print(
            f"    negative control 2 x C (200 pF) vs the stored 100 pF 3x3: residual "
            f"{residual_2c:.6e}, move {move:.6e} (PREDICTED >> "
            f"{NEGATIVE_CONTROL_PREDICTED_MOVE:.0e}: "
            f"{'held' if move > 10 * NEGATIVE_CONTROL_PREDICTED_MOVE else 'NOT held'}; "
            "printed, never asserted)",
            flush=True,
        )
    for label, r in residuals.items():
        assert r <= REDUCTION_BAND, f"{label}: stored-record residual {r:.6e} > {REDUCTION_BAND:.0e}"


@complex_only
def test_c_reduction_floor_reproduces_from_the_stored_10mhz_records():
    """(c) REDUCTION_FLOOR_F_SMALL from the stored 10 MHz 4×4 + 3×3s at rtol 1e-3."""
    if not _records_present():
        pytest.skip("records not yet stored — measurement window")
    rows = []
    for label in _LABELS_10:
        r = _residual(
            np.asarray(S_10MHZ_TERMINATED_RECORDS[label]),
            _reduce(S_10MHZ_EPS0_RECORD, FREQUENCY_HZ, _element(label)),
        )
        rows.append((label, r, REDUCTION_FLOOR_F_SMALL[label]))
    if MPI.COMM_WORLD.rank == 0:
        print(f"\n[PORT-15 step2] (c) 10 MHz floor from stored records "
              f"(ASSERTED rtol {REDUCTION_FLOOR_RTOL:.0e}):")
        for label, r, rec in rows:
            print(f"    {label:<12s} {r:.6e}   record {rec:.6e}   |ratio - 1| {abs(r / rec - 1):.3e}",
                  flush=True)
    for label, r, rec in rows:
        assert abs(r / rec - 1.0) <= REDUCTION_FLOOR_RTOL, (label, r, rec)


@complex_only
def test_inductance_readoff_from_the_stored_10mhz_record_is_printed():
    """Printed only: Im Z / ω of the stored 10 MHz 4×4 (no closed form claims it)."""
    if not _records_present():
        pytest.skip("records not yet stored — measurement window")
    omega = 2.0 * np.pi * FREQUENCY_HZ
    z = s_to_z(np.asarray(S_10MHZ_EPS0_RECORD), float(REFERENCE_IMPEDANCE_OHM))
    l_matrix = z.imag / omega
    n = l_matrix.shape[0]
    self_l = float(np.mean(np.diag(l_matrix)))
    adjacent = float(np.mean([l_matrix[i, (i + 1) % n] for i in range(n)]))
    opposite = float(np.mean([l_matrix[i, (i + 2) % n] for i in range(n)]))
    if MPI.COMM_WORLD.rank == 0:
        print("\n[PORT-15 step2] Im Z / omega at 10 MHz from the stored 4x4 (H), PRINTED:")
        for row in l_matrix:
            print("    " + "  ".join(f"{v:+.6e}" for v in row))
        print(
            f"    port self L = {self_l:.6e} H; adjacent mutual {adjacent:+.6e} H; opposite "
            f"mutual {opposite:+.6e} H.  Ladder mapping (step 1 model, 4 meshes, "
            f"Z_self = j w (2 L_leg + L_ring) with the port in a leg shared by two meshes "
            "is not unique from port-side Z alone): L_leg ~ -adjacent mutual = "
            f"{-adjacent:.6e} H, L_ring ~ self - 2 L_leg = {self_l + 2 * adjacent:.6e} H "
            "(indicative only)",
            flush=True,
        )
