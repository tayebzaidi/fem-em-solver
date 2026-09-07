"""`WF-6` step 4a — the birdcage mode-1 Biot-Savart closed form, gated.

`utils.analytical.birdcage_filament_field` is the pure-numpy filament anchor
step 4 proper will score the FEM ``|B1+|`` map against.  Nothing here solves,
meshes or imports dolfinx through the *module under test*; the fixture
constants come from the birdcage generator's own defaults so the anchor and
the mesh cannot drift apart.

**Scope.**  The closed form and its exact identities only.  No FEM, no
``|B1+|`` comparison, no homogeneity or tuning claim, no §2 change.

Anchors, all asserted, all exact (the field is analytic, so every band here is
a quadrature/round-off band, not a physics band):

  (i)   the infinite-line limit at ``L = 1e3 R``                   1e-5
  (ii)  the ring limit against ``circular_loop_magnetic_field_on_axis`` 1e-10
  (iii) ``div B = 0`` by central differences on the mode-1 pattern  1e-8 |B|/R
  (iv)  C4 covariance of the mode-1 pattern                        1e-12
  (v)   the finite-length factor ``L/sqrt(L^2 + 4R^2)`` = 0.7071    1e-6
        plus the end-ring transverse contribution at the centre in closed form
  (vi)  the mode-2 transverse zero at the centre                   1e-12

Negative control (asserted, ceiling computed): Ampere's law on a contour
around one leg.  See ``test_open_circuit_negative_control`` -- and read its
docstring before trusting the plan's original ``div B`` control, which this
module had to replace because it measures nothing (a Biot-Savart field is a
curl whether or not the circuit closes).
"""

from __future__ import annotations

import numpy as np

from fem_em_solver.utils.analytical import (
    AnalyticalSolutions,
    birdcage_filament_field,
)
from fem_em_solver.utils.constants import MU_0

# The generator's own F-small defaults, imported rather than restated.
from tests.mesh.test_birdcage_port_tags import (
    COIL_LENGTH,
    LEG_COUNT,
    RING_RADIUS,
)

DRIVE_CURRENT = 1.0

# Exact-identity bands, one per anchor above.
INFINITE_LINE_RTOL = 1e-5      # truncation 2(R/L)^2 = 2e-6 at L = 1e3 R
RING_LIMIT_RTOL = 1e-10
DIVERGENCE_BAND = 1e-8         # dimensionless: |div B| * R / |B|
C4_RTOL = 1e-12
FINITE_LENGTH_RTOL = 1e-6
MODE2_ZERO_RTOL = 1e-12

# Central-difference step for (iii), as a fraction of the ring radius.
# Truncation is O((h/R)^2) = 1e-10 and cancellation is O(eps R/h) = 2e-11,
# both a decade or more under DIVERGENCE_BAND.
DIVERGENCE_STEP_FRACTION = 1e-5


def _mode_currents(mode: int, n_legs: int = LEG_COUNT, amplitude=DRIVE_CURRENT):
    """``I_n = amplitude * cos(2 pi mode n / N)`` -- the standard drive."""
    n = np.arange(n_legs)
    return amplitude * np.cos(2.0 * np.pi * mode * n / n_legs)


def _interior_points(count: int, seed: int = 20260907) -> np.ndarray:
    """Points well inside the coil: rho <= 0.5 R, |z| <= 0.3 L."""
    rng = np.random.default_rng(seed)
    rho = 0.5 * RING_RADIUS * np.sqrt(rng.uniform(0.0, 1.0, count))
    phi = rng.uniform(0.0, 2.0 * np.pi, count)
    z = rng.uniform(-0.3 * COIL_LENGTH, 0.3 * COIL_LENGTH, count)
    return np.stack([rho * np.cos(phi), rho * np.sin(phi), z], axis=1)


def _field(points, currents, ring_currents=None):
    return birdcage_filament_field(
        points,
        ring_radius=RING_RADIUS,
        coil_length=COIL_LENGTH,
        leg_currents=currents,
        ring_currents=ring_currents,
    )


def _scaled_divergence(points, currents, ring_currents=None) -> np.ndarray:
    """``|div B| * R / |B|`` at each point, by central differences."""
    h = DIVERGENCE_STEP_FRACTION * RING_RADIUS
    divergence = np.zeros(points.shape[0])
    for axis in range(3):
        shift = np.zeros(3)
        shift[axis] = h
        plus = _field(points + shift, currents, ring_currents)
        minus = _field(points - shift, currents, ring_currents)
        divergence += (plus[:, axis] - minus[:, axis]) / (2.0 * h)
    magnitude = np.linalg.norm(_field(points, currents, ring_currents), axis=1)
    return np.abs(divergence) * RING_RADIUS / magnitude


def test_infinite_line_limit_reproduces_the_straight_wire_closed_form():
    """(i) One very long leg is the infinite wire, to 1e-5.

    ``L = 1e3 R`` truncates the closed form ``L/sqrt(L^2 + 4 d^2)`` by
    ``2 (d/L)^2 = 2e-6`` at the farthest sample (``d = R``), a decade inside
    the band.  ``ring_currents`` is forced to zero: a single leg is not a
    closed circuit and the Kirchhoff branch would (correctly) refuse it.
    """
    long_coil = 1.0e3 * RING_RADIUS
    wire_position = np.array([RING_RADIUS, 0.0])

    angles = np.linspace(0.0, 2.0 * np.pi, 8, endpoint=False)
    offsets = np.concatenate(
        [0.5 * RING_RADIUS * np.ones(8), 1.0 * RING_RADIUS * np.ones(8)]
    )
    ang = np.concatenate([angles, angles])
    points = np.stack(
        [
            wire_position[0] + offsets * np.cos(ang),
            wire_position[1] + offsets * np.sin(ang),
            np.zeros(16),
        ],
        axis=1,
    )

    got = birdcage_filament_field(
        points,
        ring_radius=RING_RADIUS,
        coil_length=long_coil,
        leg_currents=np.array([DRIVE_CURRENT]),
        ring_currents=np.zeros(1),
    )
    expected = AnalyticalSolutions.straight_wire_magnetic_field(
        points, DRIVE_CURRENT, wire_position=wire_position
    )

    relative = np.max(np.abs(got - expected)) / np.max(np.abs(expected))
    print(f"(i) infinite-line limit: rel dev {relative:.6e} (band {INFINITE_LINE_RTOL:.1e})")
    assert relative <= INFINITE_LINE_RTOL


def test_ring_limit_reproduces_the_circular_loop_on_axis_closed_form():
    """(ii) One ring's N arcs are the circular loop, on axis, to 1e-10.

    ``leg_currents`` is all-zero and ``ring_currents`` is given as ``(2, N)``
    so the *bottom* ring is switched off too: what is left is exactly one
    uniform loop at ``z = +L/2``, which is what the imported closed form
    describes.
    """
    n_arcs = 8
    loop_current = 3.0
    z_centre = 0.5 * COIL_LENGTH

    z = np.array([-0.06, -0.02, 0.0, 0.03, 0.05])
    points = np.stack([np.zeros_like(z), np.zeros_like(z), z], axis=1)

    got = birdcage_filament_field(
        points,
        ring_radius=RING_RADIUS,
        coil_length=COIL_LENGTH,
        leg_currents=np.zeros(n_arcs),
        ring_currents=np.array(
            [loop_current * np.ones(n_arcs), np.zeros(n_arcs)]
        ),
    )
    expected = AnalyticalSolutions.circular_loop_magnetic_field_on_axis(
        z, loop_current, RING_RADIUS, loop_center=z_centre
    )

    axial = np.max(np.abs(got[:, 2] - expected)) / np.max(np.abs(expected))
    transverse = np.max(np.abs(got[:, :2])) / np.max(np.abs(expected))
    print(f"(ii) ring limit: axial rel dev {axial:.6e}, on-axis transverse "
          f"{transverse:.6e} (band {RING_LIMIT_RTOL:.1e})")
    assert axial <= RING_LIMIT_RTOL
    assert transverse <= RING_LIMIT_RTOL


def test_mode_one_field_is_solenoidal():
    """(iii) ``div B = 0`` on the closed mode-1 circuit, to 1e-8 |B|/R.

    A genuine Biot-Savart field is a curl, so this is an exact identity; it is
    the assertion that catches an algebra or sign error in either kernel.  It
    is *not* sensitive to whether the circuit closes -- see the negative
    control's docstring.
    """
    points = _interior_points(20)
    scaled = _scaled_divergence(points, _mode_currents(1))
    print(f"(iii) mode-1 div B: max {scaled.max():.6e} |B|/R over 20 interior "
          f"points (band {DIVERGENCE_BAND:.1e})")
    assert scaled.max() <= DIVERGENCE_BAND


def test_mode_one_pattern_is_c4_covariant():
    """(iv) Rotating points by 2 pi / N and the drive by one leg, to 1e-12.

    Rotating the coil by ``alpha = 2 pi / N`` carries leg ``n`` onto the site
    of leg ``n+1``, so the rotated drive is ``np.roll(I, 1)`` and the field
    must satisfy ``B'(R x) = R B(x)``.
    """
    currents = _mode_currents(1)
    alpha = 2.0 * np.pi / LEG_COUNT
    c, s = np.cos(alpha), np.sin(alpha)
    rotation = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])

    points = _interior_points(24, seed=4242)
    reference = _field(points, currents)
    rotated = _field(points @ rotation.T, np.roll(currents, 1))

    relative = (
        np.max(np.abs(rotated - reference @ rotation.T))
        / np.max(np.abs(reference))
    )
    print(f"(iv) C4 covariance: rel dev {relative:.6e} (band {C4_RTOL:.1e})")
    assert relative <= C4_RTOL


def test_finite_length_factor_and_the_end_ring_contribution_at_the_centre():
    """(v) The centre field, split exactly into its leg and ring halves.

    Legs.  Each finite leg's centre field is its infinite-line value times
    ``sin(theta) = L / sqrt(L^2 + 4 R^2)``, so the legs-only centre field over
    the infinite-line sum is exactly that factor -- 0.70711 on F-small, where
    ``L = 2R``.

    Rings.  **The `WF-6` step-4a item asserted that the end rings contribute
    *zero* transverse field at the centre "by symmetry".  That is false, and
    the correct closed form is asserted here instead** (rule: a failing
    analytic comparison is evidence about the test).  Derivation: on a ring at
    ``z = h`` the source distance ``rho = sqrt(R^2 + h^2)`` is constant, and
    for ``dl = R dphi phi_hat`` the transverse part of ``dl x (-r')`` is
    ``-R h dphi (cos phi, sin phi)``.  The mode-1 Kirchhoff arc currents on
    ``N = 4`` are ``J = (I/2)(1, 1, -1, -1)``, i.e. ``J(phi) = (I/2)
    sgn(sin phi)``; ``int sgn(sin phi) cos phi dphi = 0`` and
    ``int sgn(sin phi) sin phi dphi = 4``, so one ring gives
    ``B_y = -mu_0 I R h / (2 pi rho^3)``.  Reflecting a transverse source
    element through ``z = 0`` flips the transverse field and keeps the axial
    one, and the bottom ring carries ``-J``, so the two rings' transverse
    contributions **add** and their axial ones cancel::

        B_ring(centre) = (0, -mu_0 I R h / (pi rho^3), 0),  h = L/2

    On F-small (``h = R``) that is exactly ``R^2/rho^2 = 1/2`` of the legs'
    own centre field -- a 50% end-ring contribution, not a zero one.
    """
    currents = _mode_currents(1)
    centre = np.zeros((1, 3))

    full = _field(centre, currents)[0]
    legs_only = _field(centre, currents, ring_currents=np.zeros(LEG_COUNT))[0]
    ring_only = full - legs_only

    # -- the infinite-line sum over the same legs
    theta = 2.0 * np.pi * np.arange(LEG_COUNT) / LEG_COUNT
    infinite = np.zeros(3)
    for n in range(LEG_COUNT):
        if currents[n] == 0.0:
            continue
        infinite += AnalyticalSolutions.straight_wire_magnetic_field(
            centre,
            currents[n],
            wire_position=np.array(
                [RING_RADIUS * np.cos(theta[n]), RING_RADIUS * np.sin(theta[n])]
            ),
        )[0]

    expected_factor = COIL_LENGTH / np.sqrt(COIL_LENGTH**2 + 4.0 * RING_RADIUS**2)
    factor = legs_only[1] / infinite[1]
    print(f"(v) finite-length factor: {factor:.9f} against closed form "
          f"{expected_factor:.9f} (band {FINITE_LENGTH_RTOL:.1e})")
    assert abs(factor - expected_factor) <= FINITE_LENGTH_RTOL * expected_factor
    assert abs(factor - 0.7071) <= 1e-4  # the item's stated digits
    # the legs' centre field is purely -y for the mode-1 drive
    assert abs(legs_only[0]) <= 1e-12 * abs(legs_only[1])
    assert abs(legs_only[2]) <= 1e-12 * abs(legs_only[1])

    # -- the end-ring half, in closed form
    h = 0.5 * COIL_LENGTH
    rho = np.sqrt(RING_RADIUS**2 + h**2)
    expected_ring_y = -MU_0 * DRIVE_CURRENT * RING_RADIUS * h / (np.pi * rho**3)
    ring_dev = abs(ring_only[1] - expected_ring_y) / abs(expected_ring_y)
    print(f"(v) end-ring transverse at the centre: {ring_only[1]:.9e} T against "
          f"closed form {expected_ring_y:.9e} T, rel dev {ring_dev:.6e}; "
          f"ring/leg = {ring_only[1] / legs_only[1]:.9f} "
          f"(R^2/rho^2 = {RING_RADIUS**2 / rho**2:.9f})")
    assert ring_dev <= FINITE_LENGTH_RTOL
    assert abs(ring_only[0]) <= 1e-12 * abs(ring_only[1])
    assert abs(ring_only[2]) <= 1e-12 * abs(ring_only[1])
    assert abs(ring_only[1] / legs_only[1] - RING_RADIUS**2 / rho**2) <= 1e-9


def test_mode_two_drive_has_no_transverse_field_at_the_centre():
    """(vi) ``I_n = I cos(4 pi n / N)`` gives ``B_x = B_y = 0``, to 1e-12.

    On ``N = 4`` the mode-2 drive is ``(I, -I, I, -I)``, which the C4 rotation
    carries onto its own negative (legs *and* Kirchhoff arcs), so
    ``B(0) = -R_90 B(0)``; ``R_90`` has no real eigenvalue ``-1`` in the
    transverse plane, hence the transverse field must vanish identically.
    """
    mode1_centre = np.linalg.norm(_field(np.zeros((1, 3)), _mode_currents(1))[0])
    centre = _field(np.zeros((1, 3)), _mode_currents(2))[0]

    transverse = np.max(np.abs(centre[:2])) / mode1_centre
    print(f"(vi) mode-2 transverse at the centre: {transverse:.6e} of the "
          f"mode-1 centre field (band {MODE2_ZERO_RTOL:.1e}); "
          f"mode-1 |B| = {mode1_centre:.6e} T")
    assert transverse <= MODE2_ZERO_RTOL


def test_open_circuit_negative_control():
    """Negative control (asserted, ceiling computed): Ampere's law on one leg.

    **The control the `WF-6` step-4a item pre-registered -- that legs without
    their ring arcs read >= 100x the closed pattern's ``div B`` -- cannot
    hold, and this module does not assert it.**  Biot-Savart writes
    ``B = curl A`` with ``A = (mu_0 I / 4 pi) int dl' / |r - r'|`` for *any*
    filament, open or closed, so ``div B = 0`` identically either way; the
    reading is printed below and is indeed the same order for both.  What an
    open circuit actually breaks is *Ampere's* law: ``curl B = mu_0 J +
    grad(div A)`` and ``div A = -(mu_0 I / 4 pi)(1/|r-b| - 1/|r-a|)`` is
    non-zero only when the ends ``a``, ``b`` are exposed.

    So the control is the circulation on a circle of radius ``a = 0.2 R``
    about leg 0's axis in the ``z = 0`` plane, which encloses leg 0 and
    nothing else:

      * closed circuit: ``circ = mu_0 I_0`` exactly (band 1e-9, quadrature);
      * legs only: the single finite segment gives
        ``mu_0 I_0 L / sqrt(L^2 + 4 a^2)``, a **computed O(1) ceiling** of
        ``1 - L/sqrt(L^2 + 4a^2) = 2 a^2 / L^2`` ~ 2e-2 on the deviation,
        bracketed [0.5, 1.5]x here because the other three open legs
        contribute their own ``grad(div A)`` flux through the same disc.

    Asserted: the open deviation is >= 100x the closed one, and lies inside
    the computed bracket.
    """
    currents = _mode_currents(1)
    contour_radius = 0.2 * RING_RADIUS
    n_contour = 256  # periodic trapezoid: spectral on this smooth integrand

    psi = 2.0 * np.pi * np.arange(n_contour) / n_contour
    points = np.stack(
        [
            RING_RADIUS + contour_radius * np.cos(psi),
            contour_radius * np.sin(psi),
            np.zeros(n_contour),
        ],
        axis=1,
    )
    tangent = np.stack(
        [-np.sin(psi), np.cos(psi), np.zeros(n_contour)], axis=1
    ) * contour_radius
    d_psi = 2.0 * np.pi / n_contour

    def circulation(ring_currents):
        b = _field(points, currents, ring_currents)
        return float(np.sum(np.einsum("ij,ij->i", b, tangent)) * d_psi)

    enclosed = MU_0 * currents[0]
    closed_dev = abs(circulation(None) / enclosed - 1.0)
    open_dev = abs(circulation(np.zeros(LEG_COUNT)) / enclosed - 1.0)

    ceiling = 1.0 - COIL_LENGTH / np.sqrt(
        COIL_LENGTH**2 + 4.0 * contour_radius**2
    )
    closed_div = _scaled_divergence(_interior_points(20), currents).max()
    open_div = _scaled_divergence(
        _interior_points(20), currents, ring_currents=np.zeros(LEG_COUNT)
    ).max()

    print(f"control: Ampere deviation closed {closed_dev:.6e}, open "
          f"{open_dev:.6e} ({open_dev / max(closed_dev, 1e-300):.3e}x), "
          f"computed ceiling {ceiling:.6e}")
    print(f"control (printed, NOT asserted): div B closed {closed_div:.6e}, "
          f"open {open_div:.6e} |B|/R -- both machine level, which is the "
          f"point: div B is blind to circuit closure")

    assert closed_dev <= 1e-9          # Ampere's law, exactly, on the closed coil
    assert open_dev >= 100.0 * closed_dev
    assert 0.5 * ceiling <= open_dev <= 1.5 * ceiling
