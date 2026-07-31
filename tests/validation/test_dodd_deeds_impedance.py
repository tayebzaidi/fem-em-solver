"""`MAT-6` step 1: the Dodd–Deeds closed form against independent limits.

This file gates :mod:`fem_em_solver.utils.dodd_deeds` — the reference solution
only.  The FEM comparison (solve a loop over a lossy half-space, extract ΔZ,
match it here) is `MAT-6` step 2 and does not live here yet, so nothing in this
file touches dolfinx and it runs in the real build.

A closed form nobody has checked is worth exactly as much as the proxy solver
was (PROJECT_PLAN §2), so every assertion below is against something derived a
different way:

* **σ = 0** — a non-conducting, non-magnetic half-space must be *exactly*
  invisible, because Γ(α) ≡ 0 identically, not merely small.  This is what
  forced the module to the consistent eddy-current kernel: a first draft kept
  displacement current in the half-space while using the magnetoquasistatic
  free-space kernel above it, and vacuum reflected Γ = −1 at α = 0
  (log ``20260731T050326Z_MAT-6-step1.log``).
* **σ → ∞** — the reactance change must equal ``−ω M_image``, with the image
  mutual inductance computed from the elliptic-integral ``A_φ`` in
  ``AnalyticalSolutions``.  The Hankel integral of eq. (1) and Maxwell's
  elliptic-integral mutual inductance share no algebra beyond ``μ₀``, so this
  pins both the ``jωπμ₀a²`` prefactor and the sign of Γ.
* **thin skin** — ``Γ + 1 ≈ αδ(1−j)`` makes the departure from the perfect
  conductor equal in its real and imaginary parts, so ``ΔR = ΔX − ΔX_pec``
  to leading order, and ``ΔR ∝ √ω`` at fixed σ.  Both are asymptotic identities
  the integral is free to violate if the branch of ``α₁`` is wrong.

Geometry throughout: a 5 cm loop 1 cm above the surface — the same length
scales as the MRI surface-coil-over-phantom case this chunk exists to gate.

Run::

    docker compose exec -T fem-em-solver bash -lc \\
      'cd /workspace && PYTHONPATH=/workspace/src \\
       mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_dodd_deeds_impedance.py -v'
"""

from __future__ import annotations

import numpy as np

from fem_em_solver.utils.constants import MU_0
from fem_em_solver.utils.dodd_deeds import (
    coil_impedance_change,
    half_space_reflection_coefficient,
    image_limit_inductance_change,
    skin_depth,
)

COIL_RADIUS = 0.05
LIFTOFF = 0.01
FREQUENCY_HZ = 127.74e6  # 3 T proton Larmor, as everywhere else in the project


def test_nonconducting_half_space_is_exactly_invisible():
    """σ = 0, εᵣ = μᵣ = 1 ⇒ Γ ≡ 0 ⇒ ΔZ = 0, identically."""
    alphas = np.linspace(0.0, 500.0, 50)
    gamma = half_space_reflection_coefficient(alphas, FREQUENCY_HZ, sigma=0.0)
    assert np.max(np.abs(gamma)) < 1e-14, f"Γ not identically zero: {gamma}"

    dz = coil_impedance_change(
        FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, sigma=0.0
    )
    # Scale against the perfect-conductor reactance, which is what "small"
    # means here: the vacuum answer is ~14 orders of magnitude below it.
    scale = abs(
        2.0
        * np.pi
        * FREQUENCY_HZ
        * image_limit_inductance_change(COIL_RADIUS, LIFTOFF)
    )
    assert abs(dz) / scale < 1e-12, f"vacuum half-space gave ΔZ = {dz}"


def test_perfect_conductor_limit_matches_image_mutual_inductance():
    """σ → ∞: ΔX = −ω M_image from the elliptic-integral A_φ, and ΔR → 0.

    This is the quantitative anchor of the whole module.  ``M_image`` is the
    mutual inductance between the loop and its mirror at z = −h, evaluated
    from Jackson 5.37 with complete elliptic integrals; ``coil_impedance_change``
    reaches the same number through a Hankel integral of Bessel functions.
    """
    omega = 2.0 * np.pi * FREQUENCY_HZ
    delta_l_image = image_limit_inductance_change(COIL_RADIUS, LIFTOFF)
    assert delta_l_image < 0.0, "image theory must *reduce* the inductance"

    dz = coil_impedance_change(
        FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, sigma=1.0e12
    )
    delta_l_hankel = dz.imag / omega

    rel = abs(delta_l_hankel - delta_l_image) / abs(delta_l_image)
    print(
        f"\n  ΔL image (elliptic) = {delta_l_image:.6e} H"
        f"\n  ΔL Hankel (σ=1e12)  = {delta_l_hankel:.6e} H"
        f"\n  relative difference = {rel:.4%}"
    )
    # Measured 0.0002% (log 20260731T050449Z_MAT-6-step1b.log): the residual is
    # the σ = 1e12 S/m approach to Γ = −1 plus the α-panel truncation, and the
    # bound is set an order of magnitude above it rather than at a round number.
    # Two independent derivations agreeing to 2e-6 is the anchor for eq. (1).
    assert rel < 2e-5, f"image limit off by {rel:.4%}"

    # A perfect conductor dissipates nothing: the residual loss must be a
    # vanishing fraction of the reactive part.
    assert abs(dz.real) / abs(dz.imag) < 1e-4, f"spurious loss: ΔZ = {dz}"


def test_lossy_half_space_dissipates_and_expels_flux():
    """A real conductor: ΔR > 0 (loss) and ΔX < 0 (flux expelled)."""
    dz = coil_impedance_change(FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, sigma=1.0e6)
    print(f"\n  ΔZ(σ=1e6 S/m) = {dz.real:.6e} + {dz.imag:.6e}j Ω")
    assert dz.real > 0.0, f"conductor must dissipate, got ΔR = {dz.real}"
    assert dz.imag < 0.0, f"conductor must expel flux, got ΔX = {dz.imag}"


def test_thin_skin_departure_from_perfect_conductor_is_equal_parts():
    """δ ≪ h ⇒ Γ + 1 ≈ αδ(1−j) ⇒ ΔR = ΔX − ΔX_pec to leading order.

    The identity is asymptotic in δ/h, so it is checked as a *limit*: the
    ratio must approach 1 as σ rises, and it must do so monotonically.
    """
    omega = 2.0 * np.pi * FREQUENCY_HZ
    dx_pec = omega * image_limit_inductance_change(COIL_RADIUS, LIFTOFF)

    ratios = []
    print()
    for sigma in (1.0e5, 1.0e6, 1.0e7, 1.0e8):
        dz = coil_impedance_change(FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, sigma=sigma)
        ratio = dz.real / (dz.imag - dx_pec)
        ratios.append(ratio)
        print(
            f"  σ = {sigma:8.1e} S/m  δ = {skin_depth(FREQUENCY_HZ, sigma):.3e} m"
            f"  ΔR = {dz.real:.5e} Ω  ΔR/(ΔX−ΔX_pec) = {ratio:.5f}"
        )

    errors = [abs(r - 1.0) for r in ratios]
    assert all(
        b < a for a, b in zip(errors, errors[1:])
    ), f"departure ratio not converging to 1: {ratios}"
    assert errors[-1] < 0.02, f"thin-skin identity off by {errors[-1]:.3%}"


def test_loss_scales_as_sqrt_frequency_in_the_thin_skin_regime():
    """ΔR ∝ ω^{1/2} once δ ≪ h, because ΔR ≈ ωδ·C and δ ∝ ω^{−1/2}.

    Measured as a log-log slope over a decade, so it cannot be satisfied by a
    wrong constant — only by the right power law.
    """
    sigma = 1.0e7
    freqs = np.array([1.0e7, 3.0e7, 1.0e8])
    resistances = np.array(
        [
            coil_impedance_change(f, COIL_RADIUS, LIFTOFF, sigma=sigma).real
            for f in freqs
        ]
    )
    for f in freqs:
        assert skin_depth(f, sigma) < 0.1 * LIFTOFF, "not in the thin-skin regime"

    slope = float(np.polyfit(np.log(freqs), np.log(resistances), 1)[0])
    print(f"\n  ΔR(f) = {resistances}\n  log-log slope = {slope:.4f} (expect 0.5)")
    assert abs(slope - 0.5) < 0.02, f"ΔR power law is ω^{slope:.3f}, not ω^0.5"


def test_liftoff_reduces_the_coupling_monotonically():
    """e^{−2αh} in eq. (1): more liftoff, less of everything."""
    magnitudes = [
        abs(coil_impedance_change(FREQUENCY_HZ, COIL_RADIUS, h, sigma=1.0e6))
        for h in (0.005, 0.01, 0.02, 0.04)
    ]
    assert all(
        b < a for a, b in zip(magnitudes, magnitudes[1:])
    ), f"|ΔZ| not decreasing with liftoff: {magnitudes}"
    # μ₀ is the only dimensional constant in the module; a units slip would
    # show up as an absurd impedance for a centimetre-scale loop at 128 MHz.
    assert 1e-6 < magnitudes[0] < 1e4, f"|ΔZ| implausible: {magnitudes[0]} Ω"
    assert MU_0 > 0.0
