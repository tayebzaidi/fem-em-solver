"""`TH-10` step 1: self-check the lossy-dielectric-sphere series anchor.

`TH-10` exists to close a §2.1 honesty gap: every coil-loading/SAR gate in the
repo today is eddy-current (`MAT-6`, 10 MHz) or imposed-field (`MAT-4`), so
gelled saline at 64/128 MHz is an *extrapolation*.  The named target is the
lossy dielectric sphere in a full-wave time-harmonic field against its analytic
series solution.  Step 1 authors that series
(``fem_em_solver.utils.analytical.LossySphereSeries``) and does nothing else —
no mesh, no solve, no DolfinX (§9 item 4's scope boundary).

The series is the classical Mie solution (Bohren & Huffman ch. 4,
eqs. 4.37/4.40/4.45/4.50/4.53) imported into the project's ``e^{+jωt}``
convention by conjugation; special-function definitions follow Jin,
*The FEM in Electromagnetics* 3rd ed., App. E.2 (eqs. E.24-E.31), and the
FEM-side dielectric-sphere fixture it will anchor is Jin §9.4 (Fig. 9.11).

An anchor nobody has checked is a liability, so the exit code is driven by six
gates and nothing else:

* ``GATE 1`` **empty limit** (εᵣ = 1, σ = 0): the *internal* series must return
  the incident plane wave ``E₀x̂e^{−jk₀z}`` to machine precision, and the
  internal coefficients must be ``c_n = d_n = 1`` exactly (the Wronskian
  identity B&H 4.53 collapses to).  This exercises the vector spherical
  harmonics, the Riccati-Bessel derivatives and the truncation in one shot —
  a bug in any of them shows up here at ``1e0``, not at ``1e-13``.  Machine
  precision is a statement about the *series*, so the gate reads it at a
  converged term count; the Wiscombe default's own tail is printed beside it.
* ``GATE 2`` **quasi-static limit, lossless** (§9 item 4's stated anchor): at
  the `TH-8` fixture's parameters (a = 0.05 m, εᵣ = 78, k₀a = 5e-3) the
  interior field reproduces `TH-8`'s *validated* closed form ``3E₀/(εᵣ+2)`` to
  < 0.5%, **on the quantity `TH-8` itself gates** — the mean polarisation
  component over an interior probe (`TH-8`'s ``ez_mean``).  Measured first
  attempt: the *pointwise* deviation at that fixture is 3.47e-2, and a
  radius-halving sweep shows why — it falls at **rate 1** in ``|m|k₀a`` (a
  linear interior phase ramp ``e^{−j k_in z}``, which the closed form has no
  term for), while the mean falls at **rate 2**.  Both rates are gated
  (1.00 ± 0.10 and 2.00 ± 0.15 over three rungs), which is a much stronger
  statement than the level alone: it says the series *limits to* `TH-8`'s
  closed form in the way the physics requires, rather than merely sitting near
  it.  `TH-8`'s own fixture comment ("the retardation correction the closed
  form drops is O((k_in R)²) ≈ 0.2%") is thereby confirmed as a statement about
  its mean, and shown to be wrong pointwise.
* ``GATE 3`` **quasi-static limit, lossy**: gates 2's two rates and level on
  the *imaginary* axis of ``ε_c`` (εᵣ = 78, σ = 0.5 S/m at 64 MHz, radius
  shrunk to 2 mm so ``|m|k₀a`` stays ≪ 1), against ``3E₀/(ε_c+2)`` — the
  complex continuation `MAT-4` step 1 already uses.  Amplitude *and* phase.
* ``GATE 4`` **tangential-E continuity at r = a** on the real Larmor fixture
  (a = 0.05 m, saline, 64 and 128 MHz): interior and exterior series agree in
  tangential ``E`` to < 1e-10 relative.  Unlike gates 2-3 this is a *full-wave*
  identity — it holds at ``ka`` of order one, where no quasi-static reference
  exists, and it is the only gate that tests the scattered-field coefficients
  ``a_n``/``b_n`` at all.
* ``GATE 5`` **negative control** (§9 item 4, verbatim): evaluating with the
  conjugated convention ``ε_c = εᵣ + jσ/(ωε₀)`` must break GATE 3 *by orders*.
  Required: the wrong-sign error exceeds 100× the spec error and 10% outright.
  The sign convention is load-bearing (`TH-1` formulation note).
* ``GATE 6`` **truncation**: refining the term count by +6 beyond Wiscombe's
  ``x + 4x^{1/3} + 2`` must move the Larmor interior field by < 1e-10
  relative.  The last-term bound is printed for every fixture — never assumed
  (§9 item 4's trap list).

The physical reading (printed, deliberately **not** gated — this is an anchor,
not a result): how far the saline sphere's full-wave interior field departs
from the quasi-static value `TH-8` gates, at 64 and 128 MHz.  That number is
the size of the gap `TH-10`'s later steps exist to close.

Cost: smoke, ``-n 1``, seconds; numpy/scipy arithmetic only.

Run:
    scripts/testing/run_and_log.sh TH-10 "docker compose exec -T fem-em-solver \
      bash -lc 'cd /workspace && PYTHONPATH=/workspace/src timeout -k 30 30 \
      python3 scripts/probes/th10_step1_sphere_series.py'"
"""

from __future__ import annotations

import numpy as np

from fem_em_solver.utils.analytical import (
    LossySphereSeries,
    complex_permittivity,
)
from fem_em_solver.utils.constants import EPSILON_0, MU_0

# --- fixtures ---------------------------------------------------------------

# TH-8's own fixture, restated from tests/validation/test_dielectric_sphere.py
# so the quasi-static tie is to *that* gate's numbers and not to fresh ones.
TH8_RADIUS = 0.05
TH8_EPSILON_R = 78.0
TH8_K0_R = 5.0e-3
E0 = 1.0
SPEED_OF_LIGHT = 1.0 / np.sqrt(MU_0 * EPSILON_0)
TH8_FREQUENCY_HZ = float(TH8_K0_R / TH8_RADIUS * SPEED_OF_LIGHT / (2.0 * np.pi))

# Larmor fixture: gelled saline at 1.5 T / 3 T (§10 subgoal 3).
LARMOR_RADIUS = 0.05
SALINE_EPSILON_R = 78.0
SALINE_SIGMA = 0.5
LARMOR_FREQUENCIES = (64.0e6, 128.0e6)

# GATE 3's lossy quasi-static corner: 64 MHz saline, but a radius small enough
# that |m|k₀a ≪ 1.  |m| = |√ε_c| ≈ 12.7 at these numbers, so a = 2 mm gives
# |m|k₀a ≈ 0.034 and the dropped retardation is O(1e-3) — under the 0.5% band.
QS_LOSSY_RADIUS = 2.0e-3
QS_LOSSY_FREQUENCY_HZ = 64.0e6

QS_TOLERANCE = 5.0e-3  # < 0.5%, §9 item 4
QS_RUNGS = 3  # radius halvings, at fixed frequency, for the two rate fits
QS_MEAN_RATE = (1.85, 2.15)  # O((|m|k₀a)²) on the mean
QS_POINTWISE_RATE = (0.90, 1.10)  # O(|m|k₀a) pointwise — the phase ramp
CONTINUITY_TOLERANCE = 1.0e-10
EMPTY_LIMIT_TOLERANCE = 1.0e-12
EMPTY_LIMIT_N_TERMS = 16
TRUNCATION_TOLERANCE = 1.0e-10
CONTROL_RATIO = 100.0  # "by orders"
CONTROL_FLOOR = 0.10


def _interior_points(radius: float) -> np.ndarray:
    """Points strictly inside, off every symmetry plane and off the origin.

    Uniformity in the quasi-static limit is a *spatial* claim, so the probe
    spans the interior instead of sampling one ray (the `TH-8` test makes the
    same argument for the same reason).
    """
    n_per_shell = 12
    pts = [np.array([0.0031, -0.0027, 0.0043]) * radius]
    idx = np.arange(n_per_shell) + 0.5
    phi = np.arccos(1.0 - 2.0 * idx / n_per_shell)
    golden = np.pi * (1.0 + 5.0**0.5) * idx
    for shell in (0.3, 0.55):
        r = shell * radius
        pts.append(
            np.stack(
                [
                    r * np.cos(golden) * np.sin(phi),
                    r * np.sin(golden) * np.sin(phi),
                    r * np.cos(phi),
                ],
                axis=1,
            )
        )
    return np.vstack([np.atleast_2d(pts[0]), pts[1], pts[2]])


def _surface_points(radius: float) -> np.ndarray:
    """A Fibonacci spiral on the sphere itself, avoiding the poles."""
    n = 40
    idx = np.arange(n) + 0.5
    theta = np.arccos(1.0 - 2.0 * idx / n)
    golden = np.pi * (1.0 + 5.0**0.5) * idx
    return radius * np.stack(
        [np.cos(golden) * np.sin(theta), np.sin(golden) * np.sin(theta), np.cos(theta)],
        axis=1,
    )


def _rel(a: np.ndarray, b: np.ndarray) -> float:
    """max |a − b| / max |b| over the sample."""
    denom = np.max(np.abs(b))
    denom = denom if denom > 1e-300 else 1.0
    return float(np.max(np.abs(a - b)) / denom)


def _describe(series: LossySphereSeries, label: str) -> None:
    print(
        f"[TH-10 1] {label}: a = {series.radius:.4g} m, f = "
        f"{series.frequency_hz / 1e6:.4g} MHz, eps_c = {series.epsilon_c:.6g}, "
        f"m = {series.m:.6g}, k0a = {series.size_parameter:.6g}, "
        f"|m|k0a = {abs(series.m) * series.size_parameter:.6g}, "
        f"N = {series.n_terms}, last-term bound = {series.last_term_bound():.3e}",
        flush=True,
    )


def _quasistatic_sweep(radius: float, epsilon_c: complex, frequency_hz: float):
    """Mean and pointwise deviation from ``3E₀/(ε_c+2)`` over halved radii.

    Halving the radius at fixed frequency halves ``|m|k₀a`` with ``ε_c`` — and
    therefore the closed-form reference — untouched, so the two fitted rates
    are rates in the retardation parameter and nothing else.
    """
    radii, mean_err, ptwise_err = [], [], []
    for rung in range(QS_RUNGS):
        a = radius / (2.0**rung)
        series = LossySphereSeries(
            radius=a, epsilon_c=epsilon_c, frequency_hz=frequency_hz, e0=E0
        )
        pts = _interior_points(a)
        e_in = series.internal_field(pts)
        ref = series.quasistatic_internal_field()
        ref_vec = np.zeros_like(e_in)
        ref_vec[:, 0] = ref
        radii.append(abs(series.m) * series.size_parameter)
        mean_err.append(abs(np.mean(e_in[:, 0]) - ref) / abs(ref))
        ptwise_err.append(_rel(e_in, ref_vec))
        if rung == 0:
            _describe(series, "  rung 0     ")
            print(
                f"[TH-10 1]   E_in/E0 = {np.mean(e_in[:, 0]):.6f} vs "
                f"3/(eps_c+2) = {ref:.6f} (|.| {abs(ref):.6f}, arg "
                f"{np.angle(ref, deg=True):.3f} deg)",
                flush=True,
            )
            head = (series, e_in, ref_vec, pts)
    rate_mean = float(np.polyfit(np.log(radii), np.log(mean_err), 1)[0])
    rate_ptwise = float(np.polyfit(np.log(radii), np.log(ptwise_err), 1)[0])
    print(
        "[TH-10 1]   |m|k0a rungs "
        + ", ".join(
            f"{p:.5f}: mean {m:.4e} / ptwise {q:.4e}"
            for p, m, q in zip(radii, mean_err, ptwise_err)
        )
        + f"; fitted rates mean {rate_mean:.4f}, pointwise {rate_ptwise:.4f}",
        flush=True,
    )
    return mean_err[0], rate_mean, rate_ptwise, head


def main() -> int:
    gates = []
    print(
        "[TH-10 1] lossy dielectric sphere, full-wave series anchor "
        "(smoke, -n 1, zero-solve)",
        flush=True,
    )

    # --- GATE 1: empty limit ------------------------------------------------
    empty = LossySphereSeries(
        radius=LARMOR_RADIUS,
        epsilon_c=complex_permittivity(1.0, 0.0, LARMOR_FREQUENCIES[0]),
        frequency_hz=LARMOR_FREQUENCIES[0],
        e0=E0,
    )
    _describe(empty, "empty limit  ")
    pts = _interior_points(LARMOR_RADIUS)
    default_err = _rel(empty.internal_field(pts), empty.incident_field_closed_form(pts))
    converged = LossySphereSeries(
        radius=LARMOR_RADIUS,
        epsilon_c=complex_permittivity(1.0, 0.0, LARMOR_FREQUENCIES[0]),
        frequency_hz=LARMOR_FREQUENCIES[0],
        e0=E0,
        n_terms=EMPTY_LIMIT_N_TERMS,
    )
    empty_err = _rel(
        converged.internal_field(pts), converged.incident_field_closed_form(pts)
    )
    coeff_err = float(
        max(
            np.max(np.abs(converged.coefficients["c"] - 1.0)),
            np.max(np.abs(converged.coefficients["d"] - 1.0)),
        )
    )
    empty_ok = empty_err < EMPTY_LIMIT_TOLERANCE and coeff_err < 1e-13
    print(
        f"[TH-10 1]   internal series vs E0 x_hat e^(-j k0 z): rel "
        f"{empty_err:.3e} at N = {EMPTY_LIMIT_N_TERMS} "
        f"({default_err:.3e} at the Wiscombe default N = {empty.n_terms}); "
        f"max|c_n-1|,|d_n-1| = {coeff_err:.3e}",
        flush=True,
    )
    gates.append(
        (
            "GATE 1 empty limit",
            empty_ok,
            f"field {empty_err:.3e} < {EMPTY_LIMIT_TOLERANCE:.0e} and "
            f"coefficients {coeff_err:.3e} < 1e-13",
        )
    )

    # --- GATE 2: quasi-static limit, lossless (the TH-8 tie) ----------------
    print("[TH-10 1] TH-8 fixture, lossless quasi-static sweep:", flush=True)
    qs_err, qs_rate_mean, qs_rate_pt, _ = _quasistatic_sweep(
        TH8_RADIUS,
        complex_permittivity(TH8_EPSILON_R, 0.0, TH8_FREQUENCY_HZ),
        TH8_FREQUENCY_HZ,
    )
    level_ok = qs_err < QS_TOLERANCE
    mean_rate_ok = QS_MEAN_RATE[0] < qs_rate_mean < QS_MEAN_RATE[1]
    pt_rate_ok = QS_POINTWISE_RATE[0] < qs_rate_pt < QS_POINTWISE_RATE[1]
    gates.append(
        (
            "GATE 2 quasi-static (TH-8)",
            level_ok and mean_rate_ok and pt_rate_ok,
            f"mean {qs_err:.4%} < {QS_TOLERANCE:.2%}; rate mean "
            f"{qs_rate_mean:.4f} in {QS_MEAN_RATE}; rate pointwise "
            f"{qs_rate_pt:.4f} in {QS_POINTWISE_RATE}",
        )
    )

    # --- GATE 3 / GATE 5: quasi-static limit on the imaginary axis ----------
    eps_c_lossy = complex_permittivity(
        SALINE_EPSILON_R, SALINE_SIGMA, QS_LOSSY_FREQUENCY_HZ
    )
    print("[TH-10 1] lossy quasi-static sweep (imaginary axis of eps_c):", flush=True)
    qs_lossy_err, l_rate_mean, l_rate_pt, head = _quasistatic_sweep(
        QS_LOSSY_RADIUS, eps_c_lossy, QS_LOSSY_FREQUENCY_HZ
    )
    level_ok = qs_lossy_err < QS_TOLERANCE
    mean_rate_ok = QS_MEAN_RATE[0] < l_rate_mean < QS_MEAN_RATE[1]
    pt_rate_ok = QS_POINTWISE_RATE[0] < l_rate_pt < QS_POINTWISE_RATE[1]
    gates.append(
        (
            "GATE 3 quasi-static (lossy)",
            level_ok and mean_rate_ok and pt_rate_ok,
            f"mean {qs_lossy_err:.4%} < {QS_TOLERANCE:.2%}; rate mean "
            f"{l_rate_mean:.4f} in {QS_MEAN_RATE}; rate pointwise "
            f"{l_rate_pt:.4f} in {QS_POINTWISE_RATE}",
        )
    )

    _, _, ref_vec, pts = head
    wrong = LossySphereSeries(
        radius=QS_LOSSY_RADIUS,
        epsilon_c=eps_c_lossy,
        frequency_hz=QS_LOSSY_FREQUENCY_HZ,
        e0=E0,
        conjugate_convention=True,
    )
    e_wrong = wrong.internal_field(pts)
    wrong_err = abs(np.mean(e_wrong[:, 0]) - ref_vec[0, 0]) / abs(ref_vec[0, 0])
    ratio = wrong_err / qs_lossy_err if qs_lossy_err > 0.0 else np.inf
    control_ok = wrong_err > CONTROL_FLOOR and ratio > CONTROL_RATIO
    print(
        f"[TH-10 1]   negative control (eps_c = eps_r + j sigma/(w eps0)): "
        f"E_in/E0 = {np.mean(e_wrong[:, 0]):.6f}, rel {wrong_err:.3%} = "
        f"{ratio:.3g}x the spec error",
        flush=True,
    )
    gates.append(
        (
            "GATE 5 conjugated control",
            control_ok,
            f"{wrong_err:.3%} > {CONTROL_FLOOR:.0%} and {ratio:.3g}x > "
            f"{CONTROL_RATIO:.0f}x the spec error",
        )
    )

    # --- GATE 4 / GATE 6: the real Larmor fixture ---------------------------
    continuity = []
    truncation = []
    for freq in LARMOR_FREQUENCIES:
        larmor = LossySphereSeries(
            radius=LARMOR_RADIUS,
            epsilon_c=complex_permittivity(SALINE_EPSILON_R, SALINE_SIGMA, freq),
            frequency_hz=freq,
            e0=E0,
        )
        _describe(larmor, f"saline {freq / 1e6:.0f} MHz")

        surf = _surface_points(LARMOR_RADIUS)
        normals = surf / LARMOR_RADIUS
        e_int = larmor.internal_field(surf)
        e_ext = larmor.incident_field(surf) + larmor.scattered_field(surf)
        tan_int = e_int - (np.sum(e_int * normals, axis=1))[:, None] * normals
        tan_ext = e_ext - (np.sum(e_ext * normals, axis=1))[:, None] * normals
        jump = _rel(tan_int, tan_ext)
        continuity.append(jump)

        refined = LossySphereSeries(
            radius=LARMOR_RADIUS,
            epsilon_c=complex_permittivity(SALINE_EPSILON_R, SALINE_SIGMA, freq),
            frequency_hz=freq,
            e0=E0,
            n_terms=larmor.n_terms + 6,
        )
        ipts = _interior_points(LARMOR_RADIUS)
        drift = _rel(refined.internal_field(ipts), larmor.internal_field(ipts))
        truncation.append(drift)

        e_in = larmor.internal_field(ipts)
        qs_vec = np.zeros_like(e_in)
        qs_vec[:, 0] = larmor.quasistatic_internal_field()
        departure = _rel(e_in, qs_vec)
        print(
            f"[TH-10 1]   tangential-E jump at r=a {jump:.3e}; truncation "
            f"drift at N+6 {drift:.3e}; READING full-wave vs quasi-static "
            f"interior departure {departure:.3%} (ungated)",
            flush=True,
        )

    continuity_ok = max(continuity) < CONTINUITY_TOLERANCE
    truncation_ok = max(truncation) < TRUNCATION_TOLERANCE
    gates.append(
        (
            "GATE 4 tangential continuity",
            continuity_ok,
            f"max {max(continuity):.3e} < {CONTINUITY_TOLERANCE:.0e} over "
            f"{len(continuity)} frequencies",
        )
    )
    gates.append(
        (
            "GATE 6 truncation stability",
            truncation_ok,
            f"max {max(truncation):.3e} < {TRUNCATION_TOLERANCE:.0e} at N+6",
        )
    )

    # --- verdict ------------------------------------------------------------
    order = [
        "GATE 1 empty limit",
        "GATE 2 quasi-static (TH-8)",
        "GATE 3 quasi-static (lossy)",
        "GATE 4 tangential continuity",
        "GATE 5 conjugated control",
        "GATE 6 truncation stability",
    ]
    gates.sort(key=lambda g: order.index(g[0]))
    print("[TH-10 1] GATES (exit code is gated on these, and on nothing else):",
          flush=True)
    for label, ok, detail in gates:
        print(f"    {label:<30s} {'PASS' if ok else 'FAIL'}  ({detail})", flush=True)
    n_failed = sum(1 for _, ok, _ in gates if not ok)
    code = 0 if n_failed == 0 else 1
    print(
        f"[TH-10 1] OVERALL: {len(gates) - n_failed}/{len(gates)} gates pass "
        f"-> exit {code}",
        flush=True,
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
