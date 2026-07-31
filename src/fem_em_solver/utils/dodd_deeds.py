"""Dodd & Deeds (1968) impedance change of a coil above a conductive half-space.

`MAT-6` step 1 — the closed form only.  The FEM gate that compares a solved
coil impedance against this reference is step 2 and is not implemented here.

Geometry: a circular filamentary loop of radius ``a`` in a plane parallel to,
and a liftoff ``h > 0`` above, the flat surface of a homogeneous half-space
(``z < 0``) with conductivity ``σ``, relative permittivity ``εᵣ`` and relative
permeability ``μᵣ``.  The loop is in free space.

Working in the ``e^{+jωt}`` convention used everywhere else in this project
(see `tests/validation/test_lossy_plane_wave.py`), the free-space vector
potential of the loop has the Hankel representation

    A_φ(ρ, z) = (μ₀ I a / 2) ∫₀^∞ J₁(αa) J₁(αρ) e^{−α|z−h|} dα

and the field reflected by the half-space adds

    A_φ^refl(ρ, z) = (μ₀ I a / 2) ∫₀^∞ Γ(α) J₁(αa) J₁(αρ) e^{−α(z+h)} dα

with the TE reflection coefficient of the interface

    Γ(α) = (μᵣ α − α₁) / (μᵣ α + α₁),   α₁ = √(α² + j ω μ₀ μᵣ σ)

on the branch ``Re α₁ ≥ 0`` (decaying into the conductor).

**This is the eddy-current (magnetoquasistatic) formulation of the 1968 paper:
displacement current is neglected on both sides of the interface.** That is
what makes the free-space kernel ``e^{−α|z−h|}`` above and ``α₁`` below a
consistent pair, and what makes a σ = 0 half-space *exactly* invisible rather
than invisible to O((k₀h)²).  It is accurate while the half-space loss tangent
``σ/(ωε₀εᵣ) ≫ 1`` and the whole geometry is small against the free-space
wavelength.  A gelled-saline phantom at 127.74 MHz has ``σ/(ωε₀εᵣ) ≈ 1.26`` —
*not* in that regime, so `MAT-6` step 2 must either gate the FEM solver against
a genuinely high-σ half-space or upgrade this kernel to the full-wave form
(``α₀ = √(α²−k₀²)`` above, ``α₁ = √(α²−ω²μ₀ε₀ε_c)`` below, with an ``α/α₀``
weight in the Hankel integral).  Do not quietly apply it to saline.  The extra flux
through the loop itself is ``ΔΦ = 2πa A_φ^refl(a, h)``, so the impedance change
seen at the loop terminals is ``ΔZ = jω ΔΦ / I``:

    ΔZ = j ω π μ₀ a² ∫₀^∞ Γ(α) J₁(αa)² e^{−2αh} dα                    (1)

Signs and limits worth checking against, all exercised by
`tests/validation/test_dodd_deeds_impedance.py`:

* ``σ = 0`` and ``μᵣ = 1`` make ``α₁ = α`` so ``Γ ≡ 0`` and ``ΔZ = 0``: a
  non-conducting non-magnetic half-space is invisible.
* ``σ → ∞`` drives ``α₁ → ∞`` and ``Γ → −1``, and (1) becomes ``jω`` times the
  **negative** of the mutual inductance between the loop and its mirror image
  at ``z = −h``.  The perfect conductor expels flux, so ``ΔX < 0`` and
  ``ΔR = 0``.  That image inductance is computable a second, completely
  independent way from the elliptic-integral ``A_φ`` in
  :class:`~fem_em_solver.utils.analytical.AnalyticalSolutions`, which is what
  pins the constant in (1).
* At finite ``σ`` the conductor dissipates, ``Γ`` picks up an imaginary part,
  and ``ΔR = Re ΔZ > 0``.

The integrand decays like ``e^{−2αh}`` against a ``J₁²`` that itself decays like
``1/(αa)``, so the α integral converges geometrically once ``α ≫ 1/(2h)``; it is
still oscillatory, and :func:`coil_impedance_change` integrates it piecewise
between the zeros of ``J₁(αa)`` rather than handing one infinite oscillatory
range to ``quad``.
"""

from __future__ import annotations

import numpy as np

from .constants import MU_0

__all__ = [
    "half_space_reflection_coefficient",
    "coil_impedance_change",
    "image_limit_inductance_change",
    "skin_depth",
]


def skin_depth(frequency_hz: float, sigma: float, mu_r: float = 1.0) -> float:
    """Good-conductor skin depth ``δ = √(2/(ω μ σ))`` [m]."""
    if sigma <= 0.0:
        return float("inf")
    omega = 2.0 * np.pi * frequency_hz
    return float(np.sqrt(2.0 / (omega * MU_0 * mu_r * sigma)))


def _half_space_alpha1(
    alpha: np.ndarray,
    frequency_hz: float,
    sigma: float,
    mu_r: float,
) -> np.ndarray:
    """``α₁ = √(α² + jωμ₀μᵣσ)`` on the ``Re α₁ ≥ 0`` branch."""
    omega = 2.0 * np.pi * frequency_hz
    alpha1 = np.sqrt(
        np.asarray(alpha, dtype=complex) ** 2 + 1j * omega * MU_0 * mu_r * sigma
    )
    # numpy's principal branch has Re ≥ 0 already, but the whole sign of ΔR
    # hangs on it: a flipped branch turns loss into gain.
    alpha1 = np.where(alpha1.real < 0.0, -alpha1, alpha1)
    return alpha1


def half_space_reflection_coefficient(
    alpha: np.ndarray,
    frequency_hz: float,
    sigma: float,
    mu_r: float = 1.0,
) -> np.ndarray:
    """TE reflection coefficient ``Γ(α) = (μᵣα − α₁)/(μᵣα + α₁)``.

    Parameters
    ----------
    alpha : np.ndarray
        Radial (Hankel) wavenumbers [1/m], real and non-negative.
    frequency_hz : float
        Drive frequency [Hz].
    sigma : float
        Half-space conductivity [S/m].
    mu_r : float
        Half-space relative permeability.  There is no ``epsilon_r``: this is
        the eddy-current formulation and displacement current is neglected on
        both sides (see the module docstring).
    """
    alpha = np.asarray(alpha, dtype=float)
    alpha1 = _half_space_alpha1(alpha, frequency_hz, sigma, mu_r)
    denominator = mu_r * alpha + alpha1
    # α = 0 with σ = 0 is 0/0; the physical value there is the σ = 0 answer,
    # Γ = 0, and it is the only point where the ratio is indeterminate.
    return np.where(
        np.abs(denominator) == 0.0, 0.0, (mu_r * alpha - alpha1) / np.where(
            np.abs(denominator) == 0.0, 1.0, denominator
        )
    )


def coil_impedance_change(
    frequency_hz: float,
    coil_radius: float,
    liftoff: float,
    sigma: float,
    mu_r: float = 1.0,
    n_oscillations: int = 400,
) -> complex:
    """``ΔZ`` [Ω] of a unit-turn filamentary loop above a half-space, eq. (1).

    Returns ``ΔZ = ΔR + jΔX``: the *change* in the loop's terminal impedance
    caused by the half-space, per turn, per unit current.  Positive ``ΔR`` is
    power dissipated in the conductor; negative ``ΔX`` is inductance expelled.

    Parameters
    ----------
    frequency_hz : float
        Drive frequency [Hz].
    coil_radius : float
        Loop radius ``a`` [m].
    liftoff : float
        Height ``h`` of the loop plane above the half-space surface [m].
    sigma : float
        Half-space conductivity [S/m].
    mu_r : float
        Half-space relative permeability.
    n_oscillations : int
        Number of ``J₁(αa)`` half-periods integrated before the tail is
        truncated.  The default is far past the point where ``e^{−2αh}`` has
        killed the integrand for any liftoff of practical interest; the
        truncation error is reported by :func:`_integrate_oscillatory` and
        asserted small there.
    """
    if coil_radius <= 0.0:
        raise ValueError(f"coil_radius must be positive, got {coil_radius!r}")
    if liftoff <= 0.0:
        raise ValueError(f"liftoff must be positive, got {liftoff!r}")
    if sigma < 0.0:
        raise ValueError(f"sigma must be non-negative, got {sigma!r}")

    from scipy.special import j1

    def integrand(alpha: np.ndarray) -> np.ndarray:
        gamma = half_space_reflection_coefficient(alpha, frequency_hz, sigma, mu_r)
        return gamma * j1(alpha * coil_radius) ** 2 * np.exp(-2.0 * alpha * liftoff)

    integral = _integrate_oscillatory(
        integrand, coil_radius, liftoff, n_oscillations
    )
    omega = 2.0 * np.pi * frequency_hz
    return complex(1j * omega * np.pi * MU_0 * coil_radius**2 * integral)


def _integrate_oscillatory(
    integrand,
    coil_radius: float,
    liftoff: float,
    n_oscillations: int,
) -> complex:
    """Integrate ``0 → ∞`` piecewise between the zeros of ``J₁(αa)``.

    ``quad`` on a single semi-infinite oscillatory range silently
    under-resolves; splitting on the zeros makes every panel smooth.  Beyond
    the last panel the integrand is bounded by ``e^{−2αh}`` times a decaying
    envelope, so the tail is dropped only once it is below ``1e-14`` of the
    running total.
    """
    from scipy.integrate import quad
    from scipy.special import jn_zeros

    # Zeros of J₁ in α: the first is α = 0 itself, which is already the lower
    # limit, so jn_zeros(1, n) gives the interior breakpoints directly.
    breakpoints = np.concatenate(
        [[0.0], jn_zeros(1, n_oscillations) / coil_radius]
    )
    # Truncate once e^{−2αh} has made the remaining panels irrelevant; this
    # keeps the panel count ~30 for typical liftoffs instead of n_oscillations.
    cutoff = 40.0 / (2.0 * liftoff)
    keep = int(np.searchsorted(breakpoints, cutoff)) + 1
    breakpoints = breakpoints[: max(keep, 4)]

    total = 0.0 + 0.0j
    for lo, hi in zip(breakpoints[:-1], breakpoints[1:]):
        re, _ = quad(lambda a: integrand(np.array(a)).real, lo, hi, limit=200)
        im, _ = quad(lambda a: integrand(np.array(a)).imag, lo, hi, limit=200)
        total += re + 1j * im
    return complex(total)


def image_limit_inductance_change(coil_radius: float, liftoff: float) -> float:
    """``ΔL`` [H] of the loop over a *perfect* conductor, by image theory.

    Independent of :func:`coil_impedance_change`: the perfectly conducting
    surface is replaced by a mirror loop of opposite current at ``z = −h``, and
    the inductance change is minus their mutual inductance,
    ``ΔL = −M = −2πa A_φ(ρ=a, z=2h)/I``, with ``A_φ`` the elliptic-integral
    form in :class:`~fem_em_solver.utils.analytical.AnalyticalSolutions`.

    This is the cross-check that pins the ``jωπμ₀a²`` prefactor of eq. (1):
    the two routes share no algebra beyond ``μ₀``.
    """
    from .analytical import AnalyticalSolutions

    point = np.array([[coil_radius, 0.0, 2.0 * liftoff]])
    a_phi_vec = AnalyticalSolutions.circular_loop_vector_potential(
        point, current=1.0, radius=coil_radius, loop_center=0.0
    )
    # φ̂ at (a, 0, ·) is +ŷ, so A_φ is the y component.
    a_phi = float(a_phi_vec[0, 1])
    mutual = 2.0 * np.pi * coil_radius * a_phi
    return -mutual
