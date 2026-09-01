"""`WF-6` step 2b — the B₁⁺ identities at 64 and 128 MHz.

Every ``B₁⁺`` number this repo holds is a **10 MHz** number: steps 1/1b/1c/1d
and step 2 all run ``build_four_port_sweep()``, whose frequency was hard-coded
until this step made it a keyword with the same default.  The identical
construction has run at the Larmor frequencies since `PORT-11` — through
``_four_port_rung(…, frequency_hz=…)`` — so what this module changes is one
argument, on one mesh, and nothing else.

**What is read at each of 10 / 64 / 128 MHz**, all of it in the *form* steps 1d
and 2 fixed and none of it a new band:

* **gate (i)** — the three-way real-power accounting at the P1 drive, ≤ 1% of
  the supplied power (``POWER_BALANCE_BAND``, imported);
* **gate (ii)** — the single-drive CG1 covariance of ``|B₁⁺|`` at ``+90°``,
  ``−90°`` and ``180°``, ≤ ``C4_COVARIANCE_BAND`` = 5% (imported), with the
  mis-rotated ``P3@+90deg`` control asserted *outside* the same band;
* **step 2's quadrature identities** — (a) C4-invariance of the superposed
  ``|B₁⁺|`` map and (b) the mirror identity ``|B₁⁻|_cw(Mx) = |B₁⁺|_ccw(x)``,
  both ≤ the same 5%, with the mis-paired control asserted outside it.

**The reproduction control.**  The 10 MHz rung is run here too, and its rows
must reproduce the records steps 1d and 2 measured — 2.1870 / 2.1146 / 1.8911%
and 0.9818 / 0.8087% — at their own rtol.  That is what makes the frequency the
only thing that moved: same mesh, same points, same estimator, same code.

**What is genuinely unknown, and why a miss here is a finding rather than a
failure.**  The 5% band's provenance is a *10 MHz* floor measurement (CG1
2.19 / 2.11 / 1.89%, 2.3× of headroom, `WF-6` step 1b).  Nobody has measured
whether that floor survives at 64 MHz (phantom cells/λ ≈ 21.9) or at 128 MHz
(≈ 12.5, against `PORT-11`'s pre-stated floor of 10, imported here and printed
at every rung).  A 128 MHz miss with 64 MHz green is a **resolution finding
about the B₁⁺ estimator on a frozen mesh**, not a formulation defect — and the
band is not to be widened or re-registered for it in-slot; only a review may do
that, with these tables as the provenance.

**Reported, ungated, labelled** at each frequency: centre polarisation purity
``|B₁⁺|/|B₁⁻|`` in each sense and for the P1 linear drive, mean ``|B₁⁺|`` at
1 V per port, the CV over the 51 phantom centroids and over step 1c's 96-point
ring set, and the phantom cells/λ.  These are the first Larmor-frequency B₁⁺
figures in the repo and they are **identities on one unconverged fixture**: no
homogeneity, absolute, tuning or SAR claim follows from any of them.

**Scope.**  Degree 1, F-small, the loaded 4-leg birdcage, symmetry identities
only.  No SAR (step 3), no simultaneous-source solve, no literature or AED
comparison.

Run (complex build required)::

    scripts/testing/run_and_log.sh WF-6-step2b "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 600 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_birdcage_b1_larmor.py -v -s'"
"""

from __future__ import annotations

import numpy as np
import pytest

from fem_em_solver.post import (
    magnetic_flux_density_from_e,
    project_to_cg1,
)

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.validation.test_birdcage_b1_plus_map import (
    C4_COVARIANCE_BAND,
    CG1_RECORD_RTOL,
    MIN_SAMPLE_POINTS,
    POWER_BALANCE_BAND,
    STEP1B_CG1_RECORDS,
    _power_shares,
    _read_b1_plus,
    _read_b1_plus_cg1,
    _relative_l2,
    _ring_points,
    _rotate_z,
    _sample_points,
    _solve_driven,
)
from tests.validation.test_birdcage_b1_quadrature import (
    CENTRE_POINT,
    QUADRATURE_STEP_DEG,
    _cv,
    _mirror_xy,
    _port_index,
    _read_senses,
    _superpose_dg0,
)
from tests.validation.test_lossy_sphere_fullwave import (
    FREQUENCY_128_HZ,
    FREQUENCY_64_HZ,
)
from tests.validation.test_port_birdcage_four_port import (
    TERMINATED_PORT_IMPEDANCE_OHM,
    build_four_port_sweep,
)
from tests.validation.test_port_birdcage_larmor_gate_128 import (
    PHANTOM_CELLS_PER_LAMBDA_FLOOR,
    _resolution,
)
from tests.validation.test_port_birdcage_lumped_column import (
    STEP2_CELL_COUNT,
    STEP2_CELL_COUNT_BAND,
)
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ

# The three rungs, in build order.  10 MHz is first because it is the mesh
# build *and* the reproduction control; the two Larmor rungs reuse its mesh.
RUNGS = (
    ("10 MHz", FREQUENCY_HZ),
    ("64 MHz", FREQUENCY_64_HZ),
    ("128 MHz", FREQUENCY_128_HZ),
)
BASE_RUNG = "10 MHz"

# Step 2's quadrature records at 10 MHz, from `20260831T033704Z_WF-6-step2.log`:
# (a) C4-invariance of the superposed |B1+| map and (b) the mirror identity.
# Asserted only on the 10 MHz rung, at step 1d's Krylov-figure rtol — the
# control that the frequency argument is the only thing that moved.
STEP2_QUADRATURE_RECORDS = {
    "(a) C4": 0.9818e-2,
    "(b) mirror": 0.8087e-2,
}

# Step 2's mis-paired control at 10 MHz (95.1975%), printed beside each rung's
# own reading.  The *assertion* below is the pre-registered one — strictly
# outside the 5% band — never a reproduction of this number at a Larmor
# frequency, where nothing predicts it.
STEP2_MISPAIRED_CONTROL_10MHZ = 0.951975

# What *this* module measured at the two Larmor rungs, read off its own closing
# log `20260831T140418Z_WF-6-step2b.log` (the per-rung blocks and the summary
# table).  Exported as constants only — no assertion in this module is moved or
# restated by their presence — so that `EX-40`'s example path can reproduce the
# records rather than hard-code a second copy of them (`ANS-1`'s rule; the same
# export `EX-39` made of the step-2 records).
#
#   gate_i_p1_residual      the three-way real-power residual at the P1 drive
#   cg1_p2_at_plus90        gate (ii)'s CG1 C4 covariance, P1 -> P2 at +90 deg
#   control_p3_at_plus90    the mis-rotated control (P3 read at +90 deg)
#   cells_per_lambda_phantom  phantom resolution at that frequency
#   mean_b1_plus_ccw_t      mean |B1+| of the *quadrature* (ccw) map, ungated
STEP2B_LARMOR_RECORDS = {
    "64 MHz": {
        "gate_i_p1_residual": 9.523130e-03,
        "cg1_p2_at_plus90": 2.2187e-2,
        "control_p3_at_plus90": 24.7535e-2,
        "cells_per_lambda_phantom": 21.8936,
        "mean_b1_plus_ccw_t": 6.500452e-08,
    },
    "128 MHz": {
        "gate_i_p1_residual": 9.244511e-03,
        "cg1_p2_at_plus90": 2.1315e-2,
        "control_p3_at_plus90": 25.2589e-2,
        "cells_per_lambda_phantom": 12.5024,
        "mean_b1_plus_ccw_t": 4.936577e-08,
    },
}


def _read_rung(sweep, label):
    """Every step-1d and step-2 reading, on one sweep, at one frequency.

    The readings are computed here rather than imported as fixtures because the
    step-1/step-2 fixtures are module-scoped around a single 10 MHz sweep; the
    *helpers* they are built from are all imported, so nothing about the
    estimator, the sample set or the phase convention is restated.

    Only floats, numpy arrays and plain dicts of them are returned — no dolfinx
    object escapes (the `TH-13` step-2 teardown deadlock).
    """
    comm = sweep["mesh"].comm
    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    delta_deg = (azimuths["P2"] - azimuths["P1"]) % 360.0
    delta = np.radians(delta_deg)

    order = ("P1", "P2", "P3", "P4")
    solves = {pid: _solve_driven(sweep, pid) for pid in order}
    points = _sample_points(sweep)

    # --- gate (i): the three-way power accounting at each of the two drives ---
    shares = {pid: _power_shares(sweep, solves[pid]) for pid in ("P1", "P2")}
    power = {}
    for pid, sh in shares.items():
        total = sh["phantom"] + sh["conductor"] + sh["sheet_total"]
        power[pid] = {
            "supplied": float(sh["supplied"]),
            "phantom": float(sh["phantom"]),
            "conductor": float(sh["conductor"]),
            "sheet_total": float(sh["sheet_total"]),
            "residual": float(abs(sh["supplied"] - total) / abs(sh["supplied"])),
            "blind": float(
                abs(sh["supplied"] - (total - sh["conductor"])) / abs(sh["supplied"])
            ),
        }

    # --- gate (ii): the single-drive CG1 covariance table (step 1d's form) ---
    projections = {
        pid: project_to_cg1(
            magnetic_flux_density_from_e(
                solves[pid]["fields"].e_complex, solves[pid]["omega"]
            )
        )
        for pid in order
    }
    images = {
        "P1@0deg": ("P1", points),
        "P2@+90deg": ("P2", _rotate_z(points, delta)),
        "P4@-90deg": ("P4", _rotate_z(points, -delta)),
        "P3@180deg": ("P3", _rotate_z(points, 2.0 * delta)),
        "P3@+90deg": ("P3", _rotate_z(points, delta)),
    }
    cg1_values, cg1_valid = {}, {}
    for name, (pid, pts) in images.items():
        cg1_values[name], v_cg1 = _read_b1_plus_cg1(projections[pid], pts)
        _dg0, v_dg0 = _read_b1_plus(solves[pid], pts)
        cg1_valid[name] = v_cg1 & v_dg0
    single_mask = np.logical_and.reduce([cg1_valid[n] for n in images])
    covariance = {
        name: _relative_l2(cg1_values[name], cg1_values["P1@0deg"], single_mask)
        for name in images
        if name != "P1@0deg"
    }

    # --- step 2: the quadrature drive by exact superposition -----------------
    indices = {
        pid: _port_index(azimuths[pid], azimuths["P1"], QUADRATURE_STEP_DEG)
        for pid in order
    }
    assert sorted(indices.values()) == [0, 1, 2, 3], (
        f"[{label}] the four sheets do not occupy the four quadrature slots: "
        f"{indices}"
    )
    b_dg0 = [
        magnetic_flux_density_from_e(
            solves[pid]["fields"].e_complex, solves[pid]["omega"]
        )
        for pid in order
    ]
    ks = np.array([indices[pid] for pid in order], dtype=float)
    # Step 2's convention, lifted verbatim: on an azimuth-*increasing* index the
    # sense `B1+` reads is driven by the pattern that lags, `e^{-jk pi/2}`.
    cg1_senses = {
        "ccw": project_to_cg1(
            _superpose_dg0(b_dg0, np.exp(-1j * ks * np.pi / 2.0), "B_phasor_ccw")
        ),
        "cw": project_to_cg1(
            _superpose_dg0(b_dg0, np.exp(+1j * ks * np.pi / 2.0), "B_phasor_cw")
        ),
    }
    rotated = _rotate_z(points, delta)
    mirrored = _mirror_xy(points, azimuths["P1"])
    reads = {}
    for sense in ("ccw", "cw"):
        for name, pts in (("x", points), ("Rx", rotated), ("Mx", mirrored)):
            plus, minus, valid = _read_senses(cg1_senses[sense], pts)
            reads[(sense, name)] = {"plus": plus, "minus": minus, "valid": valid}
    quad_mask = np.logical_and.reduce([r["valid"] for r in reads.values()])
    identities = {
        "(a) C4": _relative_l2(
            reads[("ccw", "Rx")]["plus"], reads[("ccw", "x")]["plus"], quad_mask
        ),
        "(b) mirror": _relative_l2(
            reads[("cw", "Mx")]["minus"], reads[("ccw", "x")]["plus"], quad_mask
        ),
        "control mis-paired": _relative_l2(
            reads[("cw", "Mx")]["plus"], reads[("ccw", "x")]["plus"], quad_mask
        ),
    }

    # --- reported, ungated ----------------------------------------------------
    centre = {}
    for sense in ("ccw", "cw"):
        plus, minus, valid = _read_senses(cg1_senses[sense], CENTRE_POINT)
        centre[sense] = {
            "plus": float(plus[0]),
            "minus": float(minus[0]),
            "valid": bool(valid[0]),
        }
    p1_cg1 = project_to_cg1(b_dg0[order.index("P1")], name="B_phasor_p1_cg1")
    p1_plus, p1_minus, p1_valid = _read_senses(p1_cg1, CENTRE_POINT)
    centre["P1 single drive"] = {
        "plus": float(p1_plus[0]),
        "minus": float(p1_minus[0]),
        "valid": bool(p1_valid[0]),
    }

    ring = _ring_points()
    ring_plus, _ring_minus, ring_valid = _read_senses(cg1_senses["ccw"], ring)
    ring_mask = np.asarray(ring_valid, dtype=bool)
    homogeneity = {
        "mean_b1_plus_ccw_t": float(np.mean(reads[("ccw", "x")]["plus"][quad_mask])),
        "cv_centroids": _cv(reads[("ccw", "x")]["plus"][quad_mask]),
        "cv_ring": _cv(ring_plus[ring_mask]) if ring_mask.any() else float("nan"),
        "n_ring_valid": int(ring_mask.sum()),
        "n_ring": int(ring.shape[0]),
    }

    row = {
        "label": label,
        "frequency_hz": float(sweep["problem"].frequency_hz),
        "cells": int(sweep["cells"]),
        "azimuths": azimuths,
        "delta_deg": float(delta_deg),
        "indices": indices,
        "power": power,
        "covariance": covariance,
        "identities": identities,
        "centre": centre,
        "homogeneity": homogeneity,
        # The superposition premise, carried out as plain numbers so the
        # structural test can assert it per frequency: one Z_p and one V_src
        # across the four ports, and the solved drives are the fixture's.
        "port_impedances": sorted(
            {complex(spec.port_impedance_ohm) for spec in sweep["specs"]},
            key=lambda z: (z.real, z.imag),
        ),
        "drive_voltages": sorted(
            {complex(spec.drive_voltage_v) for spec in sweep["specs"]},
            key=lambda z: (z.real, z.imag),
        ),
        "solved_drives": sorted(
            {complex(solves[pid]["source_voltage_v"]) for pid in order},
            key=lambda z: (z.real, z.imag),
        ),
        "n_points": int(points.shape[0]),
        "n_single_valid": int(single_mask.sum()),
        "n_quad_valid": int(quad_mask.sum()),
        "b1_plus_p1": np.asarray(cg1_values["P1@0deg"])[single_mask],
        "solve_times": {pid: float(solves[pid]["solve_time"]) for pid in order},
    }

    if comm.rank == 0:
        print(
            f"\n[WF-6 step2b] rung {label}: f = {row['frequency_hz']:.6e} Hz, "
            f"{row['cells']} cells, degree 1, CG1 estimator; drive rotation "
            f"{delta_deg:.6f} deg; solve times "
            + ", ".join(f"{p} {t:.2f} s" for p, t in row["solve_times"].items()),
            flush=True,
        )
        for pid, p in power.items():
            print(
                f"    gate (i) [{pid}] supplied {p['supplied']:.9e} W; residual "
                f"{p['residual']:.6e} (band {POWER_BALANCE_BAND:.0e}); without the "
                f"conductor term {p['blind']:.6e}",
                flush=True,
            )
        print(
            f"    gate (ii) single-drive CG1 covariance on {row['n_single_valid']} "
            f"of {row['n_points']} centroids (band "
            f"{C4_COVARIANCE_BAND * 100:.1f}%, imported):",
            flush=True,
        )
        for name in ("P2@+90deg", "P4@-90deg", "P3@180deg", "P3@+90deg"):
            role = (
                "mis-rotated control, ASSERTED > band"
                if name == "P3@+90deg"
                else "covariance identity, ASSERTED <= band"
            )
            print(
                f"        {name:<12} {covariance[name] * 100:9.4f}%   {role}",
                flush=True,
            )
        print(
            f"    step-2 quadrature identities on {row['n_quad_valid']} centroids "
            f"(same band):",
            flush=True,
        )
        for name, value in identities.items():
            role = (
                "control, ASSERTED > band"
                if name.startswith("control")
                else "ASSERTED <= band"
            )
            print(f"        {name:<20} {value * 100:9.4f}%   {role}", flush=True)
        print(
            "    centre polarisation purity |B1+|/|B1-| (REPORTED, UNGATED):",
            flush=True,
        )
        for name, cr in centre.items():
            ratio = cr["plus"] / cr["minus"] if cr["minus"] > 0.0 else float("inf")
            print(
                f"        {name:<18} |B1+| {cr['plus']:.6e} T, |B1-| "
                f"{cr['minus']:.6e} T, ratio {ratio:10.4f}"
                + ("" if cr["valid"] else "   (POINT NOT FOUND)"),
                flush=True,
            )
        print(
            f"    homogeneity (REPORTED, NOT GATED — no converged mesh, no real "
            f"drive): mean |B1+|_ccw = "
            f"{homogeneity['mean_b1_plus_ccw_t']:.6e} T at 1 V per port; CV over "
            f"{row['n_quad_valid']} centroids = "
            f"{homogeneity['cv_centroids'] * 100:.4f}%, CV over "
            f"{homogeneity['n_ring_valid']} of {homogeneity['n_ring']} ring points "
            f"= {homogeneity['cv_ring'] * 100:.4f}%",
            flush=True,
        )
    return row


@pytest.fixture(scope="module")
def larmor_rungs():
    """The three rungs on **one** mesh: 10 MHz (the control), 64 and 128 MHz.

    The 10 MHz sweep builds the mesh and the narrowed sheets; both Larmor rungs
    take them through ``build_four_port_sweep(frequency_hz=…, reuse=…)``, so the
    frequency is demonstrably the only thing that differs between them.
    """
    base = build_four_port_sweep(frequency_hz=FREQUENCY_HZ)
    comm = base["mesh"].comm
    resolution = _resolution(base)

    sweeps = {BASE_RUNG: base}
    for label, freq in RUNGS:
        if label == BASE_RUNG:
            continue
        sweeps[label] = build_four_port_sweep(frequency_hz=freq, reuse=base)

    rows = {label: _read_rung(sweeps[label], label) for label, _f in RUNGS}

    if comm.rank == 0:
        print(
            f"\n[WF-6 step2b] the first Larmor-frequency B1+ figures in the repo "
            f"— identities on one unconverged fixture, {base['cells']} cells "
            f"(record {STEP2_CELL_COUNT}, ratio "
            f"{base['cells'] / STEP2_CELL_COUNT:.6f}), one mesh for all three "
            f"rungs.  Phantom cells/lambda floor "
            f"{PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f} (`PORT-11` step 3, imported):",
            flush=True,
        )
        print(
            "    rung        cells/lambda   gate(i) P1   (ii) +90     (ii) -90  "
            "   (ii) 180     (a) C4       (b) mirror   control",
            flush=True,
        )
        for label, _f in RUNGS:
            row = rows[label]
            res = resolution["table"][label]["cells_per_lambda_phantom"]
            print(
                f"    {label:<10} {res:9.4f}    "
                f"{row['power']['P1']['residual']:.4e}   "
                f"{row['covariance']['P2@+90deg'] * 100:8.4f}%   "
                f"{row['covariance']['P4@-90deg'] * 100:8.4f}%   "
                f"{row['covariance']['P3@180deg'] * 100:8.4f}%   "
                f"{row['identities']['(a) C4'] * 100:8.4f}%   "
                f"{row['identities']['(b) mirror'] * 100:8.4f}%   "
                f"{row['identities']['control mis-paired'] * 100:8.4f}%",
                flush=True,
            )
        print(
            f"    10 MHz reproduction control: step 1d recorded "
            + ", ".join(
                f"{k} {v * 100:.4f}%" for k, v in STEP1B_CG1_RECORDS.items()
            )
            + "; step 2 recorded "
            + ", ".join(
                f"{k} {v * 100:.4f}%" for k, v in STEP2_QUADRATURE_RECORDS.items()
            )
            + f", mis-paired {STEP2_MISPAIRED_CONTROL_10MHZ * 100:.4f}%",
            flush=True,
        )

    return {"rows": rows, "resolution": resolution, "cells": int(base["cells"])}


@complex_only
def test_the_three_rungs_ran_on_one_mesh_at_the_three_frequencies(larmor_rungs):
    """Structural: the frequency is the only thing that differs between rungs.

    Not a gate; what the gates need in order to mean anything.  One mesh at the
    `PORT-9` cell record, three distinct frequencies, the same C4 sheet layout
    and enough evaluated points for a map reading rather than a few cells.
    """
    assert larmor_rungs["cells"] == pytest.approx(
        STEP2_CELL_COUNT, rel=STEP2_CELL_COUNT_BAND
    ), (
        f"the fixture meshed {larmor_rungs['cells']} cells, not the "
        f"{STEP2_CELL_COUNT} `PORT-9` record — this is not the gated fixture"
    )

    frequencies = {}
    for label, expected in RUNGS:
        row = larmor_rungs["rows"][label]
        assert row["frequency_hz"] == pytest.approx(float(expected), rel=1.0e-12), (
            f"[{label}] the rung solved at {row['frequency_hz']:.6e} Hz, not "
            f"{float(expected):.6e} Hz"
        )
        assert row["cells"] == larmor_rungs["cells"], (
            f"[{label}] the rung reports {row['cells']} cells against the base "
            f"rung's {larmor_rungs['cells']} — the mesh was not reused"
        )
        assert abs(row["delta_deg"] - 90.0) < 1.0e-6, (
            f"[{label}] the P1->P2 sheet separation reads {row['delta_deg']:.9f} "
            "deg, not 90 deg — not the C4 layout the identities assume"
        )
        assert row["n_single_valid"] >= MIN_SAMPLE_POINTS, (
            f"[{label}] only {row['n_single_valid']} of {row['n_points']} sample "
            f"points evaluated in every drive and image; below "
            f"{MIN_SAMPLE_POINTS} the covariance reading is a handful of cells"
        )
        assert row["n_quad_valid"] == row["n_points"], (
            f"[{label}] only {row['n_quad_valid']} of {row['n_points']} points "
            "evaluated in every sense on every image set — the rotated and "
            "mirrored images are fresh points and a miss would silently drop "
            "them from the l2"
        )
        values = row["b1_plus_p1"]
        assert np.all(np.isfinite(values)), f"[{label}] |B1+| is not finite"
        assert float(np.min(values)) > 0.0, (
            f"[{label}] |B1+| vanishes identically on the sample set"
        )
        # The premise superposition rests on, asserted at every frequency: one
        # operator across the four solves (`WF-6` step 2's leading test).
        assert row["port_impedances"] == [complex(TERMINATED_PORT_IMPEDANCE_OHM)], (
            f"[{label}] the four ports do not share one terminal impedance: "
            f"{row['port_impedances']} — the operator then differs between the "
            "drives and the superposed field is not the quadrature field"
        )
        assert len(row["drive_voltages"]) == 1, (
            f"[{label}] the four ports do not share one drive amplitude: "
            f"{row['drive_voltages']}"
        )
        assert row["solved_drives"] == row["drive_voltages"], (
            f"[{label}] the solved drives {row['solved_drives']} are not the "
            f"fixture's {row['drive_voltages']}"
        )

        frequencies[label] = row["frequency_hz"]

    assert len(set(frequencies.values())) == len(RUNGS), (
        f"the three rungs did not run at three distinct frequencies: {frequencies}"
    )


@complex_only
def test_power_accounting_closes_at_every_frequency(larmor_rungs):
    """**Gate (i)** at each rung, with its conductor-blind negative control.

    The domain is PEC-walled at 128 MHz exactly as it is at 10: real power
    supplied at the driven sheet has nowhere to go but the phantom, the
    conductor and the four sheets.  The band is step 1's, imported.
    """
    for label, _f in RUNGS:
        row = larmor_rungs["rows"][label]
        for pid, p in row["power"].items():
            assert p["supplied"] > 0.0, (
                f"[{label} {pid}] the driven sheet supplies {p['supplied']:.9e} W "
                "— a passive load cannot absorb negative real power"
            )
            assert p["residual"] <= POWER_BALANCE_BAND, (
                f"[{label} {pid}] power accounting misses by {p['residual']:.6e} "
                f"of the supplied {p['supplied']:.9e} W (phantom "
                f"{p['phantom']:.9e}, conductor {p['conductor']:.9e}, sheets "
                f"{p['sheet_total']:.9e}); band {POWER_BALANCE_BAND:.0e}"
            )
            assert p["blind"] > POWER_BALANCE_BAND, (
                f"[{label} {pid}] dropping the conductor's 1/2 int sigma|E|^2 "
                f"still closes to {p['blind']:.6e}, inside the "
                f"{POWER_BALANCE_BAND:.0e} band — the identity is then "
                "insensitive to a term it is supposed to weigh"
            )


@complex_only
def test_single_drive_c4_covariance_holds_at_every_frequency(larmor_rungs):
    """**Gate (ii)** at each rung: the CG1 covariance identity at three angles.

    Step 1d's gate, read at 64 and 128 MHz for the first time.  The band is the
    5% floor step 1b *measured at 10 MHz*; whether it survives at 12.5 phantom
    cells/λ is the open question this rung answers, and a miss is a resolution
    finding to be recorded with its cells/λ — never a band to widen here.
    """
    for label, _f in RUNGS:
        row = larmor_rungs["rows"][label]
        per_lambda = larmor_rungs["resolution"]["table"][label][
            "cells_per_lambda_phantom"
        ]
        for name in STEP1B_CG1_RECORDS:
            reading = row["covariance"][name]
            assert reading <= C4_COVARIANCE_BAND, (
                f"[{label}] |B1+| from the {name} drive image disagrees with the "
                f"P1 map by {reading * 100:.4f}% under the CG1 estimator, outside "
                f"the {C4_COVARIANCE_BAND * 100:.1f}% band measured at 10 MHz; "
                f"phantom cells/lambda here is {per_lambda:.4f} against the "
                f"imported floor {PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f} — record "
                "both, do not widen"
            )

        control = row["covariance"]["P3@+90deg"]
        assert control > C4_COVARIANCE_BAND, (
            f"[{label}] the mis-rotated control (P3 at +90deg, 180deg from P1) "
            f"matches the P1 map to {control * 100:.4f}%, inside the "
            f"{C4_COVARIANCE_BAND * 100:.1f}% band — the covariance gate is then "
            "not resolving the drive's azimuth at all"
        )


@complex_only
def test_quadrature_identities_hold_at_every_frequency(larmor_rungs):
    """Step 2's two identities at each rung, with the mis-paired control.

    (a) advancing the phase pattern one port is a 90° rotation of the drive and
    multiplies the superposed field by a global phase, which does not move a
    magnitude; (b) ``B`` is a pseudovector, so reflecting exchanges the two
    rotation senses.  Neither derivation mentions frequency — which is exactly
    why running them at 64 and 128 MHz tests the *discretisation*, not the
    algebra.
    """
    for label, _f in RUNGS:
        row = larmor_rungs["rows"][label]
        per_lambda = larmor_rungs["resolution"]["table"][label][
            "cells_per_lambda_phantom"
        ]
        for name in ("(a) C4", "(b) mirror"):
            reading = row["identities"][name]
            assert reading <= C4_COVARIANCE_BAND, (
                f"[{label}] quadrature identity {name} misses by "
                f"{reading * 100:.4f}%, outside the "
                f"{C4_COVARIANCE_BAND * 100:.1f}% CG1 floor; phantom "
                f"cells/lambda {per_lambda:.4f} against the imported floor "
                f"{PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f} — a superposition of four "
                "fields each inside the floor should be inside it, so record the "
                "reading and do not widen the band"
            )

        control = row["identities"]["control mis-paired"]
        assert control > C4_COVARIANCE_BAND, (
            f"[{label}] the mis-paired comparison reads {control * 100:.4f}%, "
            f"inside the {C4_COVARIANCE_BAND * 100:.1f}% band — the two rotation "
            "senses are not being told apart, so identity (b) is passing on a "
            "degeneracy"
        )


@complex_only
def test_the_10mhz_rung_reproduces_the_step_1d_and_step_2_records(larmor_rungs):
    """The reproduction control: only the frequency moved.

    The 10 MHz rung of *this* module runs the same construction the Larmor rungs
    run, through the same new keyword.  If its five recorded figures come back
    where steps 1d and 2 left them, then the differences at 64 and 128 MHz are
    the frequency's; if they do not, nothing else in this module may be read.
    """
    row = larmor_rungs["rows"][BASE_RUNG]

    for name, record in STEP1B_CG1_RECORDS.items():
        reading = row["covariance"][name]
        assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
            f"the 10 MHz CG1 {name} mismatch reads {reading * 100:.6f}%, not step "
            f"1d's recorded {record * 100:.4f}% (rtol {CG1_RECORD_RTOL:.0e}) — "
            "same mesh, same points, same estimator, so the frequency keyword is "
            "not the only thing that moved"
        )

    for name, record in STEP2_QUADRATURE_RECORDS.items():
        reading = row["identities"][name]
        assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
            f"the 10 MHz quadrature identity {name} reads {reading * 100:.6f}%, "
            f"not step 2's recorded {record * 100:.4f}% (rtol "
            f"{CG1_RECORD_RTOL:.0e})"
        )
