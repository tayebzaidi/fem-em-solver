"""`PORT-22` step 1 — the tuned F-small resonance by a driven sweep, 44–84 MHz.

The HFSS user's route to "tuned": put the capacitors *in the model* and sweep
the drive frequency.  On the 116 085-cell F-small gate mesh (the `PORT-9` /
`PORT-14` / `PORT-15` fixture), degree 1, `-n 2`, at each of the 11 grid
frequencies 44 → 84 MHz in 4 MHz steps:

1. ``kappa`` is derived **in-run at that frequency** by `PORT-14` step 3's
   route — one uncorrected P1 solve keeping its field, then the package's
   ``ports.shares.terminal_form_deficit`` pooled over the four sheets.  Never
   fitted, never a literal, never carried across frequencies.
2. the **untuned matched 4×4** through ``build_four_port_sweep`` on the same
   mesh with every sheet's told width ``w/(1 + kappa)`` (four drives, one
   factorisation — `PORT-19`);
3. the **in-model tuned** single drive: the same corrected specs with P2..P4's
   sheets carrying ``Z_C(f, C_tuned)`` and P1 driven, through
   ``_terminated_kept_network`` (`PORT-15` step 3's own helper).

``C_tuned`` is `PORT-15` step 3's — recomputed here by that module's own
``tuning_sweep`` / ``select_c_tuned`` on its stored 64 MHz record, so it is
the same number by construction, not a literal copied across modules.  It is a
*fixed physical capacitor*: the same C at every grid frequency, which is what
makes ``Z_in(f)`` a resonance curve at all.

Anchors — all bands **imported**, none stated here:

* **(i)** *asserted*: at 64 MHz the two solves reproduce `PORT-15` step 3's
  result — the tuned ``S11`` residual (circuit prediction vs in-model) is
  ``<= REDUCTION_BAND`` (1e-3, imported from `PORT-14`).  ``C_tuned``,
  ``|S11|`` and ``R_in`` are printed beside step 3's readings.
* **(ii)** *asserted*: at **every** grid frequency in this window, the
  circuit-reduced ``S11`` from that frequency's untuned 4×4 equals the
  in-model tuned ``S11`` to ``<= REDUCTION_BAND``.  (i) is the 64 MHz member
  of this family, kept separate because it is the one with a prior record.
* **(iii)** *asserted*: ``Im Z_in(f)`` — read off the **in-model** tuned
  ``S11`` — changes sign exactly once on the full 11-point grid, in the
  bracket containing 64 MHz.  This is the only anchor that needs all 11
  frequencies, so it runs in the window that completes the grid and skips in
  any earlier one (the per-frequency readings are persisted under the
  gitignored ``logs/`` tree; see ``RESULTS_DIR``).
* **negative control**, *asserted* (backed by `PORT-15` step 3's measured
  ``|S11|`` 0.846 at 0.5 × ``C_tuned`` against 0.761 at ``C_tuned`` — the same
  comparison on the same fixture, `20260914T020419Z_PORT-15.log`): the circuit
  prediction built with ``0.5 * C_tuned`` misses the in-model tuned curve at
  64 MHz by more than ``CONTROL_MISS_FACTOR`` (10) × the band.

*Printed, never gated*: the interpolated zero of ``Im Z_in``, ``R_in`` there,
and the loaded Q from the ``Im Z`` slope.

**Scope.** One fixture, degree 1, series resonance.  No absolute ``S11`` claim
comes out of this (known-issues 2026-09-19): every anchor is a circuit-layer
vs field-solve *identity* on one mesh.  No mode-spectrum claim — that is
`TH-17`'s.

The window's frequency list is the env knob ``FEM_EM_PORT22_FREQUENCIES_MHZ``
(comma-separated MHz, each a grid point); unset, the module skips, so `main`'s
CI time is unchanged.
"""

from __future__ import annotations

import json
import os
import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.ports.shares import terminal_form_deficit

from tests.complex_mode import complex_only
from tests.validation.test_birdcage_b1_plus_map import _solve_driven
from tests.validation.test_port_birdcage_four_port import build_four_port_sweep
from tests.validation.test_port_circuit_layer_field import (
    S_64MHZ_EPS0_RECORD,
    TUNING_TERMINATED_INDICES,
    _capacitor_impedance,
    _residual,
    _terminated_kept_network,
    select_c_tuned,
    tuned_input,
    tuning_sweep,
)
from tests.validation.test_port_lumped_rlc_termination import (
    RECORD_RANK_WIDTH,
    REDUCTION_BAND,
    STEP1_CELL_RECORD,
    STEP3_REGISTERED_FREQUENCY_HZ,
)
from tests.validation.test_port_package_sparameters import REFERENCE_IMPEDANCE_OHM

# --- the grid --------------------------------------------------------------
GRID_MHZ = tuple(float(44 + 4 * i) for i in range(11))  # 44, 48, ... 84
"""11 grid frequencies; 64 MHz is a grid point so `PORT-15` step 3's record is
reproduced *on the grid* and (iii)'s bracket is named by it."""

FREQUENCY_ENV = "FEM_EM_PORT22_FREQUENCIES_MHZ"
RESULTS_DIR_ENV = "FEM_EM_PORT22_RESULTS_DIR"
DEFAULT_RESULTS_DIR = "/workspace/logs/port22"

# The negative control's asserted factor (§9 rule (e): *asserted*, backed by
# `PORT-15` step 3's 0.846 vs 0.761 at 64 MHz on this fixture).
CONTROL_MISS_FACTOR = 10.0
CONTROL_C_FACTOR = 0.5

# `PORT-15` step 3's printed comparands (`20260914T020419Z_PORT-15.log`, §7
# `PORT-15` row).  PRINTED beside the live readings, never asserted here —
# anchor (i)'s assertion is the residual against the imported band.
PORT15_STEP3_C_TUNED_F = 15.570e-12
PORT15_STEP3_ABS_S11 = 0.761
PORT15_STEP3_R_IN_OHM = 6.77
PORT15_STEP3_TUNED_S11_RESIDUAL = 8.26e-5

_TERMINATED = tuple(int(k) for k in TUNING_TERMINATED_INDICES)


def _results_dir():
    return os.environ.get(RESULTS_DIR_ENV, "") or DEFAULT_RESULTS_DIR


def _window_frequencies_mhz():
    raw = os.environ.get(FREQUENCY_ENV, "").strip()
    if raw in ("", "0"):
        return None
    out = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        value = float(token)
        match = [g for g in GRID_MHZ if abs(value - g) <= 1.0e-9 * g]
        if not match:
            raise ValueError(
                f"{FREQUENCY_ENV}={raw!r}: {value} MHz is not a grid point {GRID_MHZ}"
            )
        out.append(match[0])
    if not out:
        return None
    return tuple(sorted(set(out)))


def _z_in(s11, z0=None):
    """``Z_in`` from a 1-port ``S11`` at the 50 Ω reference."""
    z0 = float(REFERENCE_IMPEDANCE_OHM) if z0 is None else float(z0)
    s11 = complex(s11)
    if abs(1.0 - s11) <= 1.0e-14:
        return complex(np.inf, np.inf)
    return z0 * (1.0 + s11) / (1.0 - s11)


def _tag(value):
    return f"{value:.0f}"


def _kappa_at(built, comm):
    """`PORT-14` step 3's route, in-run: one uncorrected P1 solve → pooled κ."""
    solved = _solve_driven(built, "P1")
    sheets = [spec.sheet(driven=(spec.port_id == "P1")) for spec in built["specs"]]
    deficit = terminal_form_deficit(
        built["mesh"], built["facet_tags"], sheets, solved["fields"].e_complex, comm
    )
    return float(deficit["pooled"]), {
        k: float(v) for k, v in deficit["per_sheet"].items()
    }


@pytest.fixture(scope="module")
def c_tuned():
    """`PORT-15` step 3's ``C_tuned``, recomputed by that module on its record."""
    _, _, roots = tuning_sweep(S_64MHZ_EPS0_RECORD, STEP3_REGISTERED_FREQUENCY_HZ)
    tuned = select_c_tuned(roots)
    assert tuned is not None, (
        "no zero of Im Z_in on `PORT-15` step 3's C grid — report, never widen in-slot"
    )
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-22 step1] C_tuned (recomputed through `PORT-15` step 3's own "
            f"tuning_sweep on S_64MHZ_EPS0_RECORD) = {tuned['c_f']:.15e} F   "
            f"step 3 printed {PORT15_STEP3_C_TUNED_F:.6e} F (PRINTED)   "
            f"|S11(C_tuned)| on the record = {abs(tuned['s11']):.9f}",
            flush=True,
        )
    return tuned


@pytest.fixture(scope="module")
def window(c_tuned):
    """One mesh build, then per grid frequency: κ, the untuned 4×4, the tuned drive."""
    frequencies_mhz = _window_frequencies_mhz()
    if frequencies_mhz is None:
        pytest.skip(f"{FREQUENCY_ENV} unset — `PORT-22` step 1 runs only when a slot asks")

    comm = MPI.COMM_WORLD
    c_f = float(c_tuned["c_f"])
    outdir = _results_dir()
    if comm.rank == 0:
        os.makedirs(outdir, exist_ok=True)
    comm.Barrier()

    t0 = time.perf_counter()
    first = build_four_port_sweep(frequency_hz=frequencies_mhz[0] * 1.0e6, build_only=True)
    comm.Barrier()
    t_mesh = time.perf_counter() - t0
    reuse = {k: first[k] for k in ("mesh", "cell_tags", "facet_tags", "sheets", "halves", "cells")}
    cells = int(first["cells"])

    rows = {}
    for mhz in frequencies_mhz:
        f_hz = mhz * 1.0e6
        comm.Barrier()
        t1 = time.perf_counter()
        uncorrected = build_four_port_sweep(
            frequency_hz=f_hz, reuse=reuse, build_only=True
        )
        kappa, per_sheet = _kappa_at(uncorrected, comm)
        comm.Barrier()
        t_kappa = time.perf_counter() - t1

        comm.Barrier()
        t2 = time.perf_counter()
        corrected = build_four_port_sweep(
            frequency_hz=f_hz, reuse=reuse, width_correction_kappa=kappa
        )
        comm.Barrier()
        t_sweep = time.perf_counter() - t2
        s4 = np.asarray(corrected["s"], dtype=np.complex128)

        corrected_built = build_four_port_sweep(
            frequency_hz=f_hz, reuse=reuse, width_correction_kappa=kappa, build_only=True
        )
        z_c = _capacitor_impedance(f_hz, c_f)
        comm.Barrier()
        t3 = time.perf_counter()
        s_in_model = _terminated_kept_network(corrected_built, {k: z_c for k in _TERMINATED})
        comm.Barrier()
        t_tuned = time.perf_counter() - t3

        _, pred = tuned_input(s4, f_hz, c_f)
        s11_pred = complex(pred[0, 0])
        s11_meas = complex(np.asarray(s_in_model)[0, 0])
        residual = float(_residual(np.asarray(s_in_model), np.asarray(pred)))
        _, pred_half = tuned_input(s4, f_hz, CONTROL_C_FACTOR * c_f)
        s11_half = complex(pred_half[0, 0])
        control_miss = float(_residual(np.asarray(s_in_model), np.asarray(pred_half)))

        row = {
            "frequency_mhz": float(mhz),
            "cells": cells,
            "kappa": float(kappa),
            "kappa_per_sheet": per_sheet,
            "c_tuned_f": c_f,
            "z_c_ohm": [float(z_c.real), float(z_c.imag)],
            "s11_circuit": [s11_pred.real, s11_pred.imag],
            "s11_in_model": [s11_meas.real, s11_meas.imag],
            "residual": residual,
            "s11_circuit_half_c": [s11_half.real, s11_half.imag],
            "control_miss": control_miss,
            "z_in_model": [_z_in(s11_meas).real, _z_in(s11_meas).imag],
            "z_in_circuit": [_z_in(s11_pred).real, _z_in(s11_pred).imag],
            "rank_width": int(comm.size),
            "seconds": {
                "kappa": float(t_kappa),
                "untuned_4x4": float(t_sweep),
                "tuned_drive": float(t_tuned),
            },
        }
        rows[mhz] = row
        if comm.rank == 0:
            z_m = _z_in(s11_meas)
            print(
                f"\n[PORT-22 step1] f = {mhz:.0f} MHz on the {cells}-cell gate mesh, "
                f"-n {comm.size}: kappa {t_kappa:.2f} s, untuned 4x4 {t_sweep:.2f} s, "
                f"tuned drive {t_tuned:.2f} s\n"
                f"    kappa(in-run, pooled) = {kappa:.9e}   told width factor "
                f"1/(1+kappa) = {1.0 / (1.0 + kappa):.9f}   Z_C = {z_c:.9e} Ohm\n"
                f"    S11 circuit {s11_pred:.12e}   in-model {s11_meas:.12e}   "
                f"residual {residual:.6e}\n"
                f"    Z_in (in-model) = {z_m.real:+.9e} {z_m.imag:+.9e}j Ohm   "
                f"|S11| in-model {abs(s11_meas):.9f}",
                flush=True,
            )
            with open(os.path.join(outdir, f"f{_tag(mhz)}.json"), "w") as fh:
                json.dump(row, fh, indent=1, sort_keys=True)
    comm.Barrier()
    if comm.rank == 0:
        print(
            f"\n[PORT-22 step1] window {[int(m) for m in frequencies_mhz]} MHz done: "
            f"mesh build {t_mesh:.2f} s, "
            f"{sum(sum(r['seconds'].values()) for r in rows.values()):.2f} s of solves, "
            f"results under {outdir}",
            flush=True,
        )
    return {"rows": rows, "frequencies_mhz": frequencies_mhz, "cells": cells, "c_f": c_f}


@complex_only
def test_the_window_ran_on_the_gate_mesh(window):
    """Fixture guard: the 116 085-cell gate mesh, one build, at the record width."""
    assert window["cells"] == STEP1_CELL_RECORD, (
        f"{window['cells']} cells, record {STEP1_CELL_RECORD} — not the gate mesh"
    )


@complex_only
def test_anchor_i_the_64mhz_tuned_s11_reproduces_port15_step3(window):
    """(i) at 64 MHz the tuned S11 residual is <= the imported REDUCTION_BAND."""
    mhz = STEP3_REGISTERED_FREQUENCY_HZ / 1.0e6
    if mhz not in window["rows"]:
        pytest.skip("64 MHz is not in this window — anchor (i) runs in the window that holds it")
    row = window["rows"][mhz]
    comm = MPI.COMM_WORLD
    s11 = complex(*row["s11_in_model"])
    z = _z_in(s11)
    if comm.rank == 0:
        print(
            f"\n[PORT-22 step1] (i) 64 MHz vs `PORT-15` step 3 "
            f"(ASSERTED residual <= REDUCTION_BAND {REDUCTION_BAND:.0e}):\n"
            f"    tuned S11 residual {row['residual']:.6e}   step 3 recorded "
            f"{PORT15_STEP3_TUNED_S11_RESIDUAL:.3e} (PRINTED)\n"
            f"    C_tuned {row['c_tuned_f']:.15e} F vs step 3's printed "
            f"{PORT15_STEP3_C_TUNED_F:.6e} F (PRINTED)\n"
            f"    |S11| in-model {abs(s11):.9f} vs step 3's {PORT15_STEP3_ABS_S11:.3f}; "
            f"R_in {z.real:.9f} Ohm vs step 3's {PORT15_STEP3_R_IN_OHM:.2f} Ohm "
            f"(both PRINTED — no absolute S11 claim, known-issues 2026-09-19)",
            flush=True,
        )
    if comm.size != RECORD_RANK_WIDTH:
        pytest.skip(f"`PORT-15` step 3's record is -n {RECORD_RANK_WIDTH}; this is -n {comm.size}")
    assert row["residual"] <= REDUCTION_BAND, (
        f"64 MHz tuned S11 residual {row['residual']:.6e} > {REDUCTION_BAND:.0e} — "
        "report, never re-band"
    )


@complex_only
def test_anchor_ii_the_circuit_reduction_matches_the_in_model_drive_at_every_frequency(window):
    """(ii) circuit-reduced S11 == in-model tuned S11 to the band, every grid point."""
    comm = MPI.COMM_WORLD
    rows = [window["rows"][m] for m in window["frequencies_mhz"]]
    if comm.rank == 0:
        print(
            f"\n[PORT-22 step1] (ii) circuit (untuned 4x4 reduced in C_tuned) vs in-model "
            f"tuned drive, ASSERTED <= REDUCTION_BAND {REDUCTION_BAND:.0e}:",
            flush=True,
        )
        for row in rows:
            print(
                f"    {row['frequency_mhz']:5.1f} MHz  kappa {row['kappa']:.6e}  "
                f"S11 circuit {complex(*row['s11_circuit']):.9e}  in-model "
                f"{complex(*row['s11_in_model']):.9e}  residual {row['residual']:.6e}  "
                f"({row['residual'] / REDUCTION_BAND:.4f} x band)",
                flush=True,
            )
    worst = max(rows, key=lambda r: r["residual"])
    assert worst["residual"] <= REDUCTION_BAND, (
        f"{worst['frequency_mhz']:.0f} MHz: residual {worst['residual']:.6e} > "
        f"{REDUCTION_BAND:.0e} — the item's negative result (the circuit layer's "
        "frequency range): known-issues, row holds, never re-band"
    )


@complex_only
def test_negative_control_the_half_c_prediction_misses_the_in_model_curve(window):
    """Control (asserted): 0.5 x C_tuned misses the in-model curve by > 10 x the band."""
    mhz = STEP3_REGISTERED_FREQUENCY_HZ / 1.0e6
    if mhz not in window["rows"]:
        pytest.skip("the control is registered at 64 MHz — it runs in that window")
    row = window["rows"][mhz]
    floor = CONTROL_MISS_FACTOR * REDUCTION_BAND
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-22 step1] negative control at 64 MHz (ASSERTED > "
            f"{CONTROL_MISS_FACTOR:g} x band = {floor:.0e}): circuit prediction at "
            f"{CONTROL_C_FACTOR:g} x C_tuned S11 {complex(*row['s11_circuit_half_c']):.9e} "
            f"(|S11| {abs(complex(*row['s11_circuit_half_c'])):.9f}, step 3's 0.846 PRINTED) "
            f"vs in-model {complex(*row['s11_in_model']):.9e}: miss {row['control_miss']:.6e} "
            f"({row['control_miss'] / REDUCTION_BAND:.3f} x band); the tuned prediction "
            f"misses by {row['residual']:.6e}",
            flush=True,
        )
    assert row["control_miss"] > floor, (
        f"0.5 x C_tuned misses by only {row['control_miss']:.6e}, under {floor:.0e}"
    )


def _load_grid():
    outdir = _results_dir()
    rows, missing = {}, []
    for mhz in GRID_MHZ:
        path = os.path.join(outdir, f"f{_tag(mhz)}.json")
        if not os.path.exists(path):
            missing.append(mhz)
            continue
        with open(path) as fh:
            rows[mhz] = json.load(fh)
    return rows, missing


@complex_only
def test_anchor_iii_im_z_in_changes_sign_once_in_the_64mhz_bracket(window):
    """(iii) Im Z_in changes sign exactly once on the 11-point grid, across 64 MHz.

    Needs the whole grid, so it asserts in the window that completes it and
    skips in any earlier one.  The interpolated zero, ``R_in`` there and the
    loaded Q are PRINTED, never gated.
    """
    MPI.COMM_WORLD.Barrier()
    rows, missing = _load_grid()
    comm = MPI.COMM_WORLD
    if missing:
        if comm.rank == 0:
            print(
                f"\n[PORT-22 step1] (iii) deferred: {len(rows)}/{len(GRID_MHZ)} grid "
                f"frequencies present, missing {[int(m) for m in missing]} MHz — "
                "asserts in the window that completes the grid",
                flush=True,
            )
        pytest.skip(f"grid incomplete: missing {[int(m) for m in missing]} MHz")

    mhz = np.array(sorted(rows), dtype=float)
    z = np.array([complex(*rows[m]["z_in_model"]) for m in mhz])
    im, re = z.imag, z.real
    brackets = [
        i for i in range(len(mhz) - 1) if np.sign(im[i]) != np.sign(im[i + 1])
    ]
    if comm.rank == 0:
        print(
            f"\n[PORT-22 step1] (iii) Z_in(f) from the in-model tuned drive, C_tuned = "
            f"{window['c_f']:.12e} F (ASSERTED: exactly one sign change of Im Z_in, in "
            "the bracket holding 64 MHz):",
            flush=True,
        )
        for i, m in enumerate(mhz):
            print(
                f"    {m:5.1f} MHz  Z_in = {re[i]:+.9e} {im[i]:+.9e}j Ohm  "
                f"|S11| = {abs(complex(*rows[m]['s11_in_model'])):.9f}",
                flush=True,
            )
    assert len(brackets) == 1, (
        f"Im Z_in changes sign {len(brackets)} times on 44-84 MHz "
        f"(brackets at {[(mhz[i], mhz[i + 1]) for i in brackets]}) — report, never re-grid"
    )
    i = brackets[0]
    assert mhz[i] <= 64.0 <= mhz[i + 1], (
        f"the single sign change is in [{mhz[i]:.0f}, {mhz[i + 1]:.0f}] MHz, not the "
        "bracket containing 64 MHz"
    )
    # PRINTED, never gated: the interpolated zero, R_in there, loaded Q.
    slope = (im[i + 1] - im[i]) / (mhz[i + 1] - mhz[i])  # Ohm / MHz
    f0 = mhz[i] - im[i] / slope
    r0 = re[i] + (re[i + 1] - re[i]) * (f0 - mhz[i]) / (mhz[i + 1] - mhz[i])
    q = 0.5 * f0 * slope / r0 if r0 != 0.0 else float("nan")
    if comm.rank == 0:
        print(
            f"    single sign change in [{mhz[i]:.0f}, {mhz[i + 1]:.0f}] MHz (ASSERTED, "
            "the 64 MHz bracket)\n"
            f"    PRINTED, never gated: interpolated zero f0 = {f0:.6f} MHz; R_in(f0) = "
            f"{r0:.6f} Ohm; d(Im Z)/df = {slope:.6f} Ohm/MHz; loaded Q = "
            f"(f0/2R) dX/df = {q:.4f}\n"
            "    one fixture, degree 1, series resonance — no absolute S11 and no "
            "mode-spectrum claim (known-issues 2026-09-19; `TH-17` owns the spectrum)",
            flush=True,
        )
