"""`MAT-8` — the finite-wire correction to the Dodd–Deeds closed form.

`MAT-6` gates a FEM coil-over-lossy-half-space solve against eq. (1) of
:mod:`fem_em_solver.utils.dodd_deeds`, which is derived for a *filament*.  The
FEM model it is compared against is not a filament: it is a 5 mm wire whose
cross-section spans lift-off 17.5–22.5 mm and radius 37.5–42.5 mm, i.e.
``r_wire/a = 0.0625``.  The difference between the two is a modelling term
nobody had quantified, and it is the floor under any sub-percent ΔR claim.
This module quantifies it, closed form only — no solve, no mesh, real mode.

`coil_impedance_change_finite_wire` averages eq. (1) over a uniform current
density on the wire's circular cross-section.  Because the generalised kernel
factorises into a source and an observation term (see
``_finite_wire_form_factor``), the double average is a single 2-D disc
quadrature applied twice, not a 4-D one.  Everything here is arithmetic; the
window is dominated by import overhead.

Tier: **smoke** (4 s measured, ``20260902T123618Z_MAT-8.log``; declared from
the footer by the 07:30 slot, corrected here by the 10:30 review), ``-n 1``,
real mode (no complex build needed).

    scripts/testing/run_and_log.sh MAT-8 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && PYTHONPATH=/workspace/src timeout -k 30 120 \\
      mpiexec -n 1 python3 -m pytest \\
      tests/validation/test_dodd_deeds_finite_wire.py -v -s --tb=short'"

``-s`` is not optional here: the fixture correction is an *ungated record*, and
pytest captures prints from passing tests without it.
"""

from __future__ import annotations

import numpy as np

from fem_em_solver.utils.dodd_deeds import (
    coil_impedance_change,
    coil_impedance_change_finite_wire,
    image_limit_inductance_change,
    image_limit_inductance_change_finite_wire,
)

# The `MAT-6` FEM fixture, verbatim from tests/validation/
# test_dodd_deeds_impedance.py (FEM_* constants).
FREQUENCY_HZ = 10.0e6
COIL_RADIUS = 0.04
LIFTOFF = 0.020
SIGMA = 100.0
WIRE_RADIUS = 0.0025


def test_zero_wire_radius_is_the_filament_form_identically():
    """``r_wire = 0`` must collapse to eq. (1) term by term, not approximately.

    The disc quadrature degenerates to the single centre node, so the two
    routines integrate the *same* integrand over the same panels; anything
    above round-off here is an algebra error in the generalised kernel's
    prefactor, which no tolerance on the finite-``r`` cases would catch.
    """
    z_filament = coil_impedance_change(FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, SIGMA)
    z_zero = coil_impedance_change_finite_wire(
        FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, SIGMA, 0.0
    )
    rel = abs(z_zero - z_filament) / abs(z_filament)
    print(f"\n  ΔZ filament   = {z_filament!r}")
    print(f"  ΔZ r_wire = 0 = {z_zero!r}")
    print(f"  relative difference = {rel:.3e}")
    assert rel < 1e-14, f"r_wire = 0 is not the filament form: rel = {rel:.3e}"


def test_shrinking_wire_recovers_the_filament_at_second_order():
    """``r_wire → 0`` recovers eq. (1), and does so as ``O(r_wire²)``.

    Scoped (2026-09-02 weekly) as "recovers the filament value to 1e-8
    relative at r = 1e-4 / 1e-5 / 1e-6 m".  Measured (log
    20260902T123343Z_MAT-8.log, this fixture):

        r = 1e-4  rel = 2.2222e-06
        r = 1e-5  rel = 2.2222e-08
        r = 1e-6  rel = 2.2222e-10

    Only the tightest radius clears 1e-8, and that is *correct physics, not a
    quadrature defect*: the leading finite-wire term is second order in
    ``r_wire``, so a 1e-8 bound at r = 1e-4 would require the correction this
    module exists to compute to be absent.  The ratios are 100.000 : 100.000 to
    six figures — a quadrature error would not scale that way — so the anchor
    is asserted here in the form the measurement supports and that is strictly
    stronger than a single tolerance: the tightest radius clears 1e-8 *and* the
    residual falls by exactly the second-order factor of 100 per decade.
    """
    z_filament = coil_impedance_change(FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, SIGMA)

    radii = (1e-4, 1e-5, 1e-6)
    residuals = []
    print()
    for r in radii:
        z = coil_impedance_change_finite_wire(
            FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, SIGMA, r
        )
        rel = abs(z - z_filament) / abs(z_filament)
        residuals.append(rel)
        print(f"  r_wire = {r:.0e} m   |ΔZ_wire − ΔZ_fil|/|ΔZ_fil| = {rel:.4e}")

    assert residuals[-1] < 1e-8, (
        f"r_wire = 1e-6 m did not recover the filament value: {residuals[-1]:.3e}"
    )

    ratios = [a / b for a, b in zip(residuals, residuals[1:])]
    print(f"  decade ratios (second order ⇒ 100) = {[f'{q:.4f}' for q in ratios]}")
    for q in ratios:
        assert abs(q - 100.0) / 100.0 < 1e-3, (
            f"residual is not second order in r_wire: decade ratio {q:.4f}"
        )


def test_two_gauss_legendre_rule_orders_agree():
    """The cross-section average is converged, not adaptively approximated.

    ``scipy.integrate.dblquad`` on this kernel converges slowly near the disc
    edge; the integrand is analytic in ``(ρ, θ)``, so a fixed Gauss–Legendre
    product rule converges geometrically instead.  16 × 16 against 24 × 24
    measured 9.8e-15 relative (log 20260902T123618Z_MAT-8.log) — the bound is
    1e-9 as scoped, six orders above the measurement.
    """
    z16 = coil_impedance_change_finite_wire(
        FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, SIGMA, WIRE_RADIUS, quadrature_order=16
    )
    z24 = coil_impedance_change_finite_wire(
        FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, SIGMA, WIRE_RADIUS, quadrature_order=24
    )
    rel = abs(z24 - z16) / abs(z16)
    print(f"\n  16×16 = {z16!r}\n  24×24 = {z24!r}\n  relative = {rel:.3e}")
    assert rel < 1e-9, f"disc quadrature not converged: {rel:.3e}"


def test_perfect_conductor_limit_matches_disc_averaged_image_mutual():
    """σ → ∞ ⇒ ΔX = −ω·⟨⟨M_image⟩⟩ from the elliptic-integral ``A_φ``.

    The same constant-pinning check `MAT-6` step 1 used, lifted to the finite
    wire.  The two routes share no algebra beyond μ₀: this one is a Hankel
    integral of ``J₁`` with a *separable* 2-D disc average, the reference is a
    4-D double disc average of Jackson 5.37 elliptic integrals.

    The residual is dominated by the σ = 1e16 S/m approach to Γ = −1, which is
    O(1/σ): measured 5.783e-6 at σ = 1e12, 5.783e-8 at σ = 1e16 (log
    20260902T123343Z_MAT-8.log), so σ = 1e16 is the value at which the 1e-6
    scoped bound is a statement about the two derivations rather than about
    how close Γ is to −1.
    """
    omega = 2.0 * np.pi * FREQUENCY_HZ
    delta_l_image = image_limit_inductance_change_finite_wire(
        COIL_RADIUS, LIFTOFF, WIRE_RADIUS
    )
    assert delta_l_image < 0.0, "image theory must *reduce* the inductance"

    dz = coil_impedance_change_finite_wire(
        FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, 1.0e16, WIRE_RADIUS
    )
    delta_l_hankel = dz.imag / omega
    rel = abs(delta_l_hankel - delta_l_image) / abs(delta_l_image)
    print(
        f"\n  ΔL image  (4-D elliptic disc average) = {delta_l_image:.10e} H"
        f"\n  ΔL Hankel (σ = 1e16, disc-averaged)   = {delta_l_hankel:.10e} H"
        f"\n  relative difference = {rel:.4e}"
        f"\n  ΔL image, filament (for scale)        = "
        f"{image_limit_inductance_change(COIL_RADIUS, LIFTOFF):.10e} H"
    )
    assert rel < 1e-6, f"finite-wire image limit off by {rel:.4e}"
    assert abs(dz.real) / abs(dz.imag) < 1e-6, f"spurious loss: ΔZ = {dz!r}"


def test_disc_averaged_image_mutual_is_quadrature_converged():
    """The 4-D elliptic reference is itself converged in the rule order.

    Without this the anchor above could be two routines agreeing on a
    half-resolved number.  Measured 12 → 16 → 24 nodes per direction:
    −1.97868402062e-08, −1.97868402031e-08, −1.97868402031e-08 H.
    """
    values = [
        image_limit_inductance_change_finite_wire(
            COIL_RADIUS, LIFTOFF, WIRE_RADIUS, quadrature_order=order
        )
        for order in (12, 16, 24)
    ]
    print()
    for order, v in zip((12, 16, 24), values):
        print(f"  order {order:2d}: ΔL = {v:.14e} H")
    rel = abs(values[2] - values[1]) / abs(values[2])
    assert rel < 1e-9, f"elliptic disc average not converged: {rel:.3e}"


def test_finite_wire_correction_at_the_mat6_fixture_is_recorded():
    """**Ungated record.**  The number `MAT-6`'s ΔR comparison rests on.

    `MAT-6`'s FEM-vs-closed-form ΔR discrepancy is 1.58% in the production
    fixture and 0.2829% in the step-8 slab-refined one.  This test asserts
    nothing about the correction's size — it prints it, so the reading lands in
    the harness log and can be quoted against those two figures.
    """
    z_fil = coil_impedance_change(FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, SIGMA)
    z_wire = coil_impedance_change_finite_wire(
        FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, SIGMA, WIRE_RADIUS
    )
    d_r = (z_wire.real - z_fil.real) / z_fil.real
    d_x = (z_wire.imag - z_fil.imag) / z_fil.imag
    print(
        f"\n  MAT-6 fixture: f = {FREQUENCY_HZ:.3e} Hz, a = {COIL_RADIUS} m, "
        f"h = {LIFTOFF} m, σ = {SIGMA} S/m, r_wire = {WIRE_RADIUS} m "
        f"(r/a = {WIRE_RADIUS / COIL_RADIUS:.4f})"
        f"\n  ΔR filament  = {z_fil.real:.8e} Ω"
        f"\n  ΔR finite wire = {z_wire.real:.8e} Ω    correction = {d_r:+.6%}"
        f"\n  ΔX filament  = {z_fil.imag:.8e} Ω"
        f"\n  ΔX finite wire = {z_wire.imag:.8e} Ω    correction = {d_x:+.6%}"
        f"\n  for scale: MAT-6 FEM ΔR discrepancy is 1.58% (production) / "
        f"0.2829% (step-8 slab-refined fixture)"
    )


def test_correction_approaches_the_mean_square_radius_limit_with_liftoff():
    """The scoped negative control, corrected — and it now has a closed form.

    Scoped (2026-09-02 weekly) as "the correction vanishes for h ≫ r_wire
    faster than (r/a)²  — assert monotone *decrease* across lift-offs 20 / 40 /
    80 mm".  That premise is false, and the measurement says so cleanly
    (log 20260902T123442Z_MAT-8.log, this fixture):

        h = 20 mm  1.152366e-03      h = 160 mm  1.889138e-03
        h = 40 mm  1.473159e-03      h = 320 mm  1.936224e-03
        h = 80 mm  1.750262e-03      h = 640 mm  1.945731e-03

    monotone *increasing*, toward 1.953125e-03.  The reason is analytic, not a
    quadrature defect.  As h grows the α-integral is dominated by α ≲ 1/(2h),
    where J₁(αρ) → αρ/2, so the form factor tends to (α/2)⟨ρ'²⟩ and

        ⟨ρ'²⟩ = ⟨(a + ρcosθ)²⟩ = a² + ⟨ρ²⟩/2 = a²(1 + r_wire²/(4a²)),

    which enters ΔZ squared:  ΔZ_wire/ΔZ_fil → 1 + r_wire²/(2a²).  The
    lift-off dependence of the *coupling* does vanish, but the wire's own
    mean-square-radius shift does not — it is a property of the loop, not of
    the half-space, so the correction saturates instead of decaying.  The
    control is therefore asserted in the form the physics dictates, which is
    quantitative where the scoped one was only monotone: the sequence rises
    monotonically and the gap to the closed-form limit r_wire²/(2a²) closes
    monotonically to 0.38% of it.
    """
    limit = WIRE_RADIUS**2 / (2.0 * COIL_RADIUS**2)
    liftoffs = (0.020, 0.040, 0.080, 0.160, 0.320, 0.640)

    corrections = []
    print(f"\n  closed-form h→∞ limit r_wire²/(2a²) = {limit:.6e}")
    for h in liftoffs:
        z_fil = coil_impedance_change(FREQUENCY_HZ, COIL_RADIUS, h, SIGMA)
        z_wire = coil_impedance_change_finite_wire(
            FREQUENCY_HZ, COIL_RADIUS, h, SIGMA, WIRE_RADIUS
        )
        d_r = (z_wire.real - z_fil.real) / z_fil.real
        corrections.append(d_r)
        print(
            f"  h = {h * 1e3:6.1f} mm  ΔR correction = {d_r:.6e}"
            f"  gap to limit = {abs(d_r - limit):.3e}"
        )

    assert all(
        b > a for a, b in zip(corrections, corrections[1:])
    ), f"ΔR correction not monotone in lift-off: {corrections}"
    assert all(
        c < limit for c in corrections
    ), f"ΔR correction exceeded its h→∞ limit {limit:.6e}: {corrections}"

    gaps = [abs(c - limit) for c in corrections]
    assert all(
        b < a for a, b in zip(gaps, gaps[1:])
    ), f"gap to the mean-square-radius limit not closing: {gaps}"
    assert gaps[-1] / limit < 0.01, (
        f"h = 640 mm still {gaps[-1] / limit:.3%} from r_wire²/(2a²)"
    )
