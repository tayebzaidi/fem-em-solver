"""`PORT-1` adjudication decision-(4) — state the PEC-box term as a number.

Zero-solve arithmetic on recorded digits.  No mesh, no solve, no complex mode,
nothing under ``src/`` touched.

Step 3b-xi measured the residual ``Im Z₁₂`` deficit against ``ωM₁₂`` at three
air paddings on the ungapped pair (projected drive, ``h_far`` 0.03):

    W = 0.08 m  ->  −8.0324 pp
    W = 0.10 m  ->  −5.0256 pp
    W = 0.12 m  ->  −3.2733 pp

3b-xi deliberately claimed only a *direction* ("three paddings inside a factor
1.5 cannot support a Richardson fit, and none was attempted").  The
operator-session adjudication of 2026-08-12, decision (4), commissioned the
arithmetic anyway under an explicitly stated ceiling, so that the deferred
port-pair gate can state the box term as an extrapolated **number** rather than
as "the suspect".

The model is `MAT-6` step 9's free-exponent form, carried over verbatim in
structure and re-stated on the deficit rather than a ratio::

    deficit(W) = D_inf + C·W**(−p)

Three unknowns, three points: this is a **solve, not a regression**.  The
residual is zero by construction and therefore carries no information — there
is no goodness-of-fit claim to be made here and this probe must not manufacture
one.  What *is* falsifiable, and what is enforced:

* **p > 0.**  A non-positive exponent is not a decaying tail; it would say the
  three rungs do not describe a box term that vanishes as the wall recedes.
* **|D_inf| < 3.2733 pp.**  A monotonically decaying tail cannot extrapolate to
  a magnitude above its own smallest measured rung.
* **the fitter recovers a planted answer.**  A synthetic triple generated from
  a known ``(D_inf, C, p)`` at the same three widths must be recovered to
  ``1e-9``.  This is the vacuity guard: it separates "the solve works" from
  "the solve returned something", which the by-construction-zero residual
  cannot.

The commissioning text asks for the solve to be seeded at ``p = 3``.  `MAT-6`
step 9's method needs no seed and is used unchanged instead: it eliminates
``C`` and ``p`` analytically and **bisects** on the one remaining unknown, so
there is no iterate to place and no complex or negative-``p`` root to converge
to silently — the failure modes the seed was meant to guard against are
structurally absent rather than assumed away.  The bracket is
``(smallest rung, smallest rung + 10·(|smallest rung| + 1))``; no sign change in
it returns "no fit" rather than a number.

The recovered ``p`` is reported beside `MAT-6` step 9's blind **p = 3.045** and
the dipolar expectation **p = 3** — the number of interest, since step 9's
fixture recovered the dipolar exponent it was never given.  The deliverable is
``D_inf``.

The rungs are signed deficits in percentage points and are composed as signed
quantities throughout (§7 `MAT-6` step-9 note: never compose relative
percentages).

Run through the harness::

    scripts/testing/run_and_log.sh PORT-1 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && PYTHONPATH=/workspace/src timeout -k 30 30 \\
      mpiexec -n 1 python3 scripts/probes/port1_padding_fit.py'"

Exit code 0 iff every assertion above holds.
"""

import math
import sys

# Recorded digits, PROJECT_PLAN.md §7 step 3b-xi table.  Transcribed, not
# re-derived: signed deficits in percentage points.
WIDTHS_M = (0.08, 0.10, 0.12)
DEFICITS_PP = (-8.0324, -5.0256, -3.2733)

# Pre-registered bounds (§9 item 4).  Neither may move in this slot.
SMALLEST_RUNG_PP = 3.2733
MAT6_STEP9_P = 3.045
DIPOLAR_P = 3.0


def power_law_extrapolation(widths, values):
    """Fit ``value(W) = v_inf − C·W**(−p)`` through exactly three points.

    Carried over from ``tests/validation/test_dodd_deeds_reactance_box_truncation.py``
    (`MAT-6` step 9) unchanged in method: writing ``e_i = v_inf − value_i`` the
    model is linear in logs — ``ln e_i = ln C − p ln W_i`` — so the correct
    ``v_inf`` is the one making the three ``(ln W_i, ln e_i)`` collinear, i.e.
    the one where the two adjacent-pair slopes agree.  Bisect on that residual.

    Note the sign convention: ``v_inf − C·W**(−p)`` here is the commissioning
    text's ``D_inf + C·W**(−p)`` with ``C`` negated.  The reported ``C`` below
    is stated in the commissioning text's convention.

    Returns ``(v_inf, p)``, or ``(None, None)`` when the trend does not admit
    such a fit (non-monotone rungs, or no sign change in the bracket).
    """
    w = [float(x) for x in widths]
    r = [float(x) for x in values]
    if not (r[0] < r[1] < r[2]):
        return None, None

    def slope_mismatch(v_inf):
        e = [v_inf - x for x in r]
        if min(e) <= 0.0:
            return float("nan")
        p_lo = (math.log(e[0]) - math.log(e[1])) / (math.log(w[1]) - math.log(w[0]))
        p_hi = (math.log(e[1]) - math.log(e[2])) / (math.log(w[2]) - math.log(w[1]))
        return p_lo - p_hi

    lo = r[2] + 1.0e-12
    hi = r[2] + 10.0 * (abs(r[2]) + 1.0)
    f_lo, f_hi = slope_mismatch(lo), slope_mismatch(hi)
    if not (math.isfinite(f_lo) and math.isfinite(f_hi)) or f_lo * f_hi > 0.0:
        return None, None
    for _ in range(400):
        mid = 0.5 * (lo + hi)
        f_mid = slope_mismatch(mid)
        if not math.isfinite(f_mid):
            return None, None
        if f_lo * f_mid <= 0.0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    v_inf = 0.5 * (lo + hi)
    e = [v_inf - x for x in r]
    p = (math.log(e[0]) - math.log(e[2])) / (math.log(w[2]) - math.log(w[0]))
    return v_inf, p


def main():
    failures = []

    print("[PORT-1 dec-(4)] free-exponent padding fit — zero-solve arithmetic")
    print("  model: deficit(W) = D_inf + C·W**(-p);  3 points, 3 parameters,")
    print("         exactly determined -> residual is zero BY CONSTRUCTION and")
    print("         carries no goodness-of-fit information.  Stated up front.")
    print("  recorded rungs (§7 step 3b-xi, signed pp):")
    for w, d in zip(WIDTHS_M, DEFICITS_PP):
        print(f"    W = {w:.2f} m   deficit = {d:+.4f} pp")

    # ---- vacuity guard: recover a planted answer ------------------------
    plant_d_inf, plant_c, plant_p = -1.5, -4.0e-4, 3.0
    planted = tuple(plant_d_inf + plant_c * w ** (-plant_p) for w in WIDTHS_M)
    rec_d_inf, rec_p = power_law_extrapolation(WIDTHS_M, planted)
    print("\n[control] synthetic recovery at the same three widths")
    print(
        f"  planted   D_inf = {plant_d_inf:+.6f} pp, C = {plant_c:+.6e}, "
        f"p = {plant_p:.6f}"
    )
    if rec_d_inf is None:
        print("  recovered -> NO FIT")
        failures.append("synthetic control: fitter returned no fit on a planted triple")
    else:
        # solve for C in D_inf + C·W**(-p): C = (value - D_inf)·W**p
        rec_c = (planted[0] - rec_d_inf) * WIDTHS_M[0] ** rec_p
        print(
            f"  recovered D_inf = {rec_d_inf:+.6f} pp, C = {rec_c:+.6e}, "
            f"p = {rec_p:.6f}"
        )
        err_d = abs(rec_d_inf - plant_d_inf)
        err_p = abs(rec_p - plant_p)
        print(f"  |ΔD_inf| = {err_d:.3e} pp, |Δp| = {err_p:.3e}  (bound 1e-9)")
        if err_d > 1.0e-9 or err_p > 1.0e-9:
            failures.append(
                f"synthetic control: recovery off by ΔD_inf={err_d:.3e}, Δp={err_p:.3e}"
            )

    # ---- vacuity guard: a non-monotone triple must NOT produce a number --
    non_monotone = (DEFICITS_PP[0], DEFICITS_PP[2], DEFICITS_PP[1])
    nm_d_inf, _nm_p = power_law_extrapolation(WIDTHS_M, non_monotone)
    print("\n[control] non-monotone triple must be refused")
    print(
        "  input " + ", ".join(f"{v:+.4f}" for v in non_monotone) + " -> "
        + ("NO FIT (correct)" if nm_d_inf is None else f"D_inf = {nm_d_inf:+.4f} pp")
    )
    if nm_d_inf is not None:
        failures.append(
            "non-monotone control: fitter returned a number for a triple with no "
            "monotone tail"
        )

    # ---- the fit --------------------------------------------------------
    d_inf, p = power_law_extrapolation(WIDTHS_M, DEFICITS_PP)
    print("\n[fit] 3b-xi padding rungs")
    if d_inf is None:
        print("  NO FIT — the three rungs do not admit a power-law tail")
        failures.append("fit: no power-law tail through the three recorded rungs")
        c_coef = float("nan")
    else:
        c_coef = (DEFICITS_PP[0] - d_inf) * WIDTHS_M[0] ** p
        print(f"  D_inf = {d_inf:+.4f} pp   (the box-free deficit)")
        print(f"  C     = {c_coef:+.6e}      (pp·m**p, sign of the tail)")
        print(f"  p     = {p:.4f}")
        print(
            f"  p beside `MAT-6` step 9's blind p = {MAT6_STEP9_P:.3f} "
            f"(Δ = {p - MAT6_STEP9_P:+.4f}) and the dipolar p = {DIPOLAR_P:.1f} "
            f"(Δ = {p - DIPOLAR_P:+.4f})"
        )
        resid = [
            (d_inf + c_coef * w ** (-p)) - d for w, d in zip(WIDTHS_M, DEFICITS_PP)
        ]
        print(
            "  residuals (zero by construction; printed as an implementation "
            "check, NOT a fit-quality claim): "
            + ", ".join(f"{r:+.3e}" for r in resid)
        )
        if max(abs(r) for r in resid) > 1.0e-9:
            failures.append(
                "implementation: exactly-determined solve left a nonzero residual "
                f"({max(abs(r) for r in resid):.3e} pp)"
            )

    # ---- diagnostic: what the dipolar exponent would give ----------------
    # The free fit recovers p ≈ 1.66 where `MAT-6` step 9's fixture recovered
    # the dipolar p = 3.045 blind.  Since D_inf and p trade off against each
    # other, the review needs to know how much of D_inf rests on the free
    # exponent.  Pinning p = 3 leaves two parameters on three points, so unlike
    # the free fit this one HAS a residual and the residual is informative:
    # a large one is the three rungs saying they are not a 1/W³ tail.
    # Print-only.  No gate, no band — the free fit is the deliverable and this
    # does not compete with it.
    print("\n[diagnostic] the same rungs with p pinned at the dipolar 3.0")
    x = [w ** (-DIPOLAR_P) for w in WIDTHS_M]
    n = len(x)
    sx, sy = sum(x), sum(DEFICITS_PP)
    sxx = sum(v * v for v in x)
    sxy = sum(a * b for a, b in zip(x, DEFICITS_PP))
    det = n * sxx - sx * sx
    c_pin = (n * sxy - sx * sy) / det
    d_pin = (sy - c_pin * sx) / n
    pin_resid = [
        (d_pin + c_pin * w ** (-DIPOLAR_P)) - d for w, d in zip(WIDTHS_M, DEFICITS_PP)
    ]
    print(f"  D_inf(p=3) = {d_pin:+.4f} pp,  C = {c_pin:+.6e}")
    print(
        "  residuals (informative here — 2 params, 3 points): "
        + ", ".join(f"{r:+.4f}" for r in pin_resid)
        + f"  max |r| = {max(abs(r) for r in pin_resid):.4f} pp"
    )
    if d_inf is not None:
        print(
            f"  vs the free fit's D_inf = {d_inf:+.4f} pp -> the exponent choice "
            f"moves the deliverable by {abs(d_pin - d_inf):.4f} pp"
        )

    # ---- conditioning: does the deliverable survive the recorded digits? -
    # An exactly-determined fit has no residual to inspect, so the only
    # available statement about how *firm* D_inf is comes from perturbing the
    # inputs by their own rounding.  3b-xi records four decimals, so each rung
    # carries a half-ulp of 5e-5 pp; all eight sign corners are enumerated.
    # This is not a new physics gate and no band is invented for it: what is
    # asserted is that the perturbation does not overturn either pre-registered
    # gate or flip the sign of the deliverable.  If it does, the extrapolation
    # is ill-conditioned on its own inputs and the port-pair gate must not
    # quote the number.
    half_ulp = 5.0e-5
    print("\n[conditioning] half-ulp (±5e-5 pp) perturbation of the recorded rungs")
    corner_d, corner_p = [], []
    for mask in range(8):
        pert = tuple(
            d + (half_ulp if (mask >> i) & 1 else -half_ulp)
            for i, d in enumerate(DEFICITS_PP)
        )
        cd, cp = power_law_extrapolation(WIDTHS_M, pert)
        if cd is None:
            failures.append(
                f"conditioning: half-ulp corner {mask:03b} admits no fit at all"
            )
            continue
        corner_d.append(cd)
        corner_p.append(cp)
    if corner_d:
        d_lo, d_hi = min(corner_d), max(corner_d)
        p_lo, p_hi = min(corner_p), max(corner_p)
        print(f"  D_inf spans [{d_lo:+.4f}, {d_hi:+.4f}] pp  (span {d_hi - d_lo:.4f} pp)")
        print(f"  p     spans [{p_lo:.4f}, {p_hi:.4f}]        (span {p_hi - p_lo:.4f})")
        if d_inf is not None and abs(d_inf) > 0.0:
            print(
                f"  amplification: {(d_hi - d_lo) / (2.0 * half_ulp):.1f}× the input "
                "half-ulp width"
            )
        if d_lo * d_hi <= 0.0:
            failures.append(
                f"conditioning: D_inf sign is not determined by the recorded digits "
                f"(spans [{d_lo:+.4f}, {d_hi:+.4f}] pp)"
            )
        if max(abs(d_lo), abs(d_hi)) >= SMALLEST_RUNG_PP:
            failures.append(
                "conditioning: a half-ulp corner pushes |D_inf| to or above the "
                f"smallest measured rung ({max(abs(d_lo), abs(d_hi)):.4f} pp)"
            )
        if p_lo <= 0.0:
            failures.append(
                f"conditioning: a half-ulp corner drives p non-positive ({p_lo:.4f})"
            )

    # ---- pre-registered assertions --------------------------------------
    print("\n[gates] pre-registered, §9 item 4")
    if p is not None:
        ok_p = p > 0.0
        print(f"  (1) p > 0                : p = {p:.4f}            -> {'PASS' if ok_p else 'FAIL'}")
        if not ok_p:
            failures.append(f"gate 1: p = {p:.4f} is not > 0 — no decaying tail")
    if d_inf is not None:
        ok_d = abs(d_inf) < SMALLEST_RUNG_PP
        print(
            f"  (2) |D_inf| < {SMALLEST_RUNG_PP:.4f} pp : |D_inf| = {abs(d_inf):.4f} pp"
            f"   -> {'PASS' if ok_d else 'FAIL'}"
        )
        if not ok_d:
            failures.append(
                f"gate 2: |D_inf| = {abs(d_inf):.4f} pp is not below the smallest "
                f"measured rung {SMALLEST_RUNG_PP:.4f} pp"
            )

    print("\n[verdict]")
    if failures:
        for f in failures:
            print(f"  FAIL — {f}")
        print(f"  {len(failures)} failure(s)")
        return 1
    print("  all gates green")
    if d_inf is not None:
        print(
            f"  deliverable: the port-pair gate states the box term as "
            f"D_inf = {d_inf:+.4f} pp (p = {p:.4f})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
