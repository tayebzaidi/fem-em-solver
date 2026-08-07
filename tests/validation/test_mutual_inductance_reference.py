"""`PORT-1` step 3b-viii: audit the ``ωM₁₂`` reference in closed form.

No solve, no mesh — pure closed-form arithmetic.  This exists because the
gap-voltage port estimator on the two-torus pair reports
``V_gap = 0.4937/0.4917 × ωM₁₂`` (step 3b-vii, four estimator families spanning
a factor 15 off one solved field), and one of the two named suspects for that
factor-2 deficit is the **reference itself**: every ratio in
``test_port_gap_voltage_impedance.py`` is normalised by the *filamentary*
mutual inductance ``mutual_inductance(a, a, d)``, while the fixture's loops
have a finite minor radius ``r/a = 0.125``.

Two independent statements are made here, and neither of them touches the FEM:

1. **The filament closed form is not a transcription error.**
   ``mutual_inductance`` (used by every `PORT-1` gate) computes
   ``M = 2πρ·A_φ/I`` from
   :meth:`AnalyticalSolutions.circular_loop_vector_potential` — a
   vector-potential route.  Reimplementing the *same* closed form through the
   complete elliptic integrals,

       M = μ₀√(ab)·[(2/k − k)K(k) − (2/k)E(k)],   k² = 4ab/((a+b)² + d²)

   is an independent derivation of the identical quantity (Maxwell's formula,
   Jackson 5.37 in the other variable), so the two must agree to round-off.
   Gated at **1e-9 relative** at four coaxial configurations, including the
   fixture's ``d`` and step 2c's doubling control ``2d``.

2. **The finite-cross-section correction is percent-scale, not factor-2.**
   Averaging the filament kernel over both minor discs with a uniform current
   density gives the tube-to-tube mutual inductance

       M_tube = (1/(πr²)²) ∬ M_fil(a+u₁, a+u₂, d + w₂ − w₁) dA₁ dA₂

   evaluated by 2-D Gauss–Legendre × periodic-trapezoid quadrature per disc
   (polar in the minor cross-section; the trapezoid rule is spectrally accurate
   in the periodic angle).  The integrand is smooth: the discs are ``d = 8r``
   apart, so no filament pair ever coincides.  **Uniform current density is an
   assumption**, valid in the ``δ ≳ r`` limit; the gapped fixture runs at
   ``δ = 1.125 r_wire``, which is that limit's edge, and a non-uniform (skin)
   distribution would push current toward the surface — a *larger* effective
   spread, not a smaller one, so the number below is not an accidental floor.

**Ceiling, fixed before the calculation ran** (PROJECT_PLAN §7, step-3b-viii
plan): step 2's reaction route measured ``Im Z₁₂`` at −9.35% of this same
filamentary reference on the ungapped pair, and step 2c's box sweep attributes
−9.36% of that to the PEC wall — an independent *field-level* estimator agrees
with the filament closed form to within the box effect.  A legitimate
finite-cross-section correction is therefore bounded at ~10%; a computed
"correction" near the 2× the gap-voltage deficit would need means the
*calculation* here is wrong, not the reference.  ``TUBE_RATIO_CEILING``
asserts that bound, so a factor-2 answer fails loudly instead of being
reported as a finding.

**Which reference.**  The landed gates normalise by the **full-loop** ``M``
(``mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)``, see
``test_port_gap_voltage_impedance.py``), not by a ``2π − g`` wedge, even on the
gapped fixture.  This audit therefore also targets the full loop; the wedge
question is a separate one (and at ``g = 0.30 rad`` it is a 4.8% arc, the wrong
order to explain 0.49 either).

**Does not close** `PORT-1` or known-issues 3: it adjudicates one of two
suspects.

Scope: smoke tier, ``-n 1``, seconds.  Run::

    docker compose exec -T fem-em-solver bash -lc \\
      'cd /workspace && PYTHONPATH=/workspace/src \\
       mpiexec -n 1 python3 -m pytest \\
       tests/validation/test_mutual_inductance_reference.py -v -s'
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.special import ellipe, ellipk

from fem_em_solver.utils.constants import MU_0

from tests.validation.test_port_reaction_impedance import (
    MAJOR_RADIUS,
    MINOR_RADIUS,
    OMEGA,
    SEPARATION,
    SEPARATION_DOUBLE,
    mutual_inductance,
)

# Statement 1: two derivations of one closed form, so the only difference
# admissible is round-off in two different transcendental evaluations.
FILAMENT_ROUTE_TOLERANCE = 1.0e-9

# Cross-run anchor to executed history: the reaction gate's docstring and
# 20260802T183747Z_PORT-1-step1-boxsens.log print omega*M12 = 1.241755 Ohm at
# this configuration.  Seven significant figures, held to 1e-6 relative.
OMEGA_M12_LOGGED_OHM = 1.241755
OMEGA_M12_LOGGED_TOLERANCE = 1.0e-6

# Statement 2: the quadrature must be converged before the ratio means
# anything, and the ratio must respect the reaction route's ~10% ceiling.
TUBE_QUADRATURE_TOLERANCE = 1.0e-6
TUBE_RATIO_CEILING = 0.10

# (radial Gauss-Legendre order, angular trapezoid points) per disc, increasing.
TUBE_QUADRATURE_ORDERS = ((4, 8), (6, 12), (8, 16), (10, 20))


def mutual_inductance_elliptic(a: float, b: float, d: float) -> float:
    """Maxwell's formula for two coaxial filamentary loops.

    ``a``, ``b`` are the loop radii and ``d`` their axial separation.

    Trap, named in the step-3b-viii plan and honoured here: SciPy's
    :func:`~scipy.special.ellipk` / :func:`~scipy.special.ellipe` take the
    **parameter** ``m = k²``, not the modulus ``k``.  The ``μ₀/8π`` internal
    -inductance term belongs to self-inductance and is deliberately absent.
    """
    m = 4.0 * a * b / ((a + b) ** 2 + d**2)
    k = np.sqrt(m)
    return float(
        MU_0 * np.sqrt(a * b) * ((2.0 / k - k) * ellipk(m) - (2.0 / k) * ellipe(m))
    )


def _disc_nodes(radius: float, n_radial: int, n_angular: int):
    """Polar quadrature nodes on a disc of the given radius.

    Gauss–Legendre in ``s`` (absorbing the ``s ds`` Jacobian into the weight),
    uniform trapezoid in the periodic angle.  Weights are normalised to sum to
    one, so an average over the disc is ``Σ w f`` — a uniform current density.
    """
    s_nodes, s_weights = np.polynomial.legendre.leggauss(n_radial)
    s = 0.5 * radius * (s_nodes + 1.0)
    w_s = 0.5 * radius * s_weights * s  # s ds
    theta = 2.0 * np.pi * np.arange(n_angular) / n_angular
    w_theta = np.full(n_angular, 2.0 * np.pi / n_angular)

    u = np.outer(s, np.cos(theta)).ravel()
    w = np.outer(s, np.sin(theta)).ravel()
    weights = np.outer(w_s, w_theta).ravel()
    return u, w, weights / weights.sum()


def tube_mutual_inductance(
    a: float, r_wire: float, d: float, n_radial: int, n_angular: int
) -> float:
    """``M`` between two coaxial tori, uniform current density in each.

    Each filament pair contributes ``M_fil(a + u₁, a + u₂, d + w₂ − w₁)``,
    weighted by the product of the two normalised disc measures.
    """
    u1, w1, wt1 = _disc_nodes(r_wire, n_radial, n_angular)
    u2, w2, wt2 = _disc_nodes(r_wire, n_radial, n_angular)

    rho1 = a + u1[:, None]
    rho2 = a + u2[None, :]
    dz = d + w2[None, :] - w1[:, None]

    m = 4.0 * rho1 * rho2 / ((rho1 + rho2) ** 2 + dz**2)
    k = np.sqrt(m)
    kernel = (
        MU_0
        * np.sqrt(rho1 * rho2)
        * ((2.0 / k - k) * ellipk(m) - (2.0 / k) * ellipe(m))
    )
    return float(wt1 @ kernel @ wt2)


@pytest.mark.parametrize(
    "label,radius,separation",
    [
        ("fixture d", MAJOR_RADIUS, SEPARATION),
        ("doubling 2d", MAJOR_RADIUS, SEPARATION_DOUBLE),
        ("near d/4", MAJOR_RADIUS, 0.25 * SEPARATION),
        ("far 4d", MAJOR_RADIUS, 4.0 * SEPARATION),
    ],
)
def test_filament_reference_two_independent_routes(label, radius, separation):
    """The vector-potential route and Maxwell's formula are the same number."""
    m_vector_potential = mutual_inductance(radius, radius, separation)
    m_elliptic = mutual_inductance_elliptic(radius, radius, separation)
    rel = abs(m_elliptic - m_vector_potential) / abs(m_vector_potential)

    print(
        f"\n[3b-viii] {label:12s} a = {radius:.4f} m, d = {separation:.4f} m: "
        f"M_vecpot = {m_vector_potential:.12e} H, "
        f"M_elliptic = {m_elliptic:.12e} H, rel = {rel:.3e}"
    )
    assert rel < FILAMENT_ROUTE_TOLERANCE, (
        f"{label}: two routes to the same closed form disagree at {rel:.3e}"
    )


def test_modulus_convention_control_is_detectable():
    """Vacuity control for the 1e-9 identity: the ``m = k²`` trap must show.

    The plan names SciPy's parameter convention as the trap most likely to
    produce a silently-wrong reference.  Feeding the *modulus* ``k`` where the
    *parameter* ``m`` belongs is the natural mistake, and the check above would
    be worthless if that mistake were invisible to it.  It is not: the wrong
    convention moves ``M`` by tens of percent, i.e. more than ten orders of
    magnitude above the 1e-9 gate.
    """
    a, d = MAJOR_RADIUS, SEPARATION
    m = 4.0 * a * a / ((2.0 * a) ** 2 + d**2)
    k = np.sqrt(m)
    m_correct = mutual_inductance_elliptic(a, a, d)
    m_wrong = float(
        MU_0 * a * ((2.0 / k - k) * ellipk(k) - (2.0 / k) * ellipe(k))
    )
    rel = abs(m_wrong - m_correct) / abs(m_correct)
    print(
        f"\n[3b-viii] modulus-convention control: M(m={m:.6f}) = "
        f"{m_correct:.12e} H vs M(k={k:.6f}) = {m_wrong:.12e} H, "
        f"rel = {rel:.3e}"
    )
    assert rel > 1.0e-2, (
        "the m-vs-k convention is invisible to this fixture, so the 1e-9 "
        "two-route identity proves nothing"
    )


def test_filament_reference_matches_logged_omega_m12():
    """Anchor to executed history: the gates' printed ``ωM₁₂ = 1.241755 Ω``."""
    omega_m = OMEGA * mutual_inductance_elliptic(
        MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION
    )
    rel = abs(omega_m - OMEGA_M12_LOGGED_OHM) / OMEGA_M12_LOGGED_OHM
    print(
        f"\n[3b-viii] omega*M12 (elliptic) = {omega_m:.6f} Ohm vs logged "
        f"{OMEGA_M12_LOGGED_OHM:.6f} Ohm, rel = {rel:.3e}"
    )
    assert rel < OMEGA_M12_LOGGED_TOLERANCE


def test_finite_cross_section_correction_is_percent_scale():
    """``M_tube/M_fil`` at ``r/a = 0.125``, converged, against the ~10% ceiling."""
    m_fil = mutual_inductance_elliptic(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)

    values = []
    for n_radial, n_angular in TUBE_QUADRATURE_ORDERS:
        m_tube = tube_mutual_inductance(
            MAJOR_RADIUS, MINOR_RADIUS, SEPARATION, n_radial, n_angular
        )
        values.append(m_tube)
        print(
            f"\n[3b-viii] tube quadrature ({n_radial:2d}, {n_angular:2d}): "
            f"M_tube = {m_tube:.12e} H, ratio = {m_tube / m_fil:.12f}"
        )

    deltas = [
        abs(values[i + 1] - values[i]) / abs(values[i + 1])
        for i in range(len(values) - 1)
    ]
    print(
        "[3b-viii] successive quadrature deltas: "
        + ", ".join(f"{d:.3e}" for d in deltas)
    )
    assert deltas[-1] < TUBE_QUADRATURE_TOLERANCE, (
        f"tube quadrature not converged: last delta {deltas[-1]:.3e}"
    )

    ratio = values[-1] / m_fil
    print(
        f"[3b-viii] r/a = {MINOR_RADIUS / MAJOR_RADIUS:.3f}: "
        f"M_tube/M_fil = {ratio:.9f} "
        f"({100.0 * (ratio - 1.0):+.4f}% correction); "
        f"omega*M_tube = {OMEGA * values[-1]:.6f} Ohm vs "
        f"omega*M_fil = {OMEGA * m_fil:.6f} Ohm"
    )
    # The reaction route bounds a legitimate correction at ~10% (PROJECT_PLAN
    # §7, step-3b-viii plan).  This is a ceiling on the *calculation*, not a
    # tuned band: exceeding it means the quadrature is wrong, and it would
    # contradict step 2's field-level agreement with the same reference.
    assert abs(ratio - 1.0) < TUBE_RATIO_CEILING, (
        f"finite-cross-section correction {100.0 * (ratio - 1.0):+.4f}% exceeds "
        f"the reaction route's {100.0 * TUBE_RATIO_CEILING:.0f}% ceiling"
    )
