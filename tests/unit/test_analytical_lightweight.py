import numpy as np

from fem_em_solver.utils.analytical import AnalyticalSolutions, ErrorMetrics
from fem_em_solver.utils.constants import MU_0


def test_straight_wire_analytical_direction_and_magnitude():
    current = 1.0
    points = np.array([[0.01, 0.0, 0.0]])
    b = AnalyticalSolutions.straight_wire_magnetic_field(points, current)

    expected_mag = MU_0 * current / (2 * np.pi * 0.01)
    got_mag = np.linalg.norm(b[0])

    assert np.isclose(got_mag, expected_mag, rtol=1e-10)
    assert abs(b[0, 0]) < 1e-14
    assert abs(b[0, 2]) < 1e-14
    assert b[0, 1] > 0


def test_helmholtz_center_formula_matches_closed_form():
    current = 1.0
    radius = 0.05
    z = np.array([0.0])

    b_center = AnalyticalSolutions.helmholtz_coil_field_on_axis(z, current, radius)[0]
    expected = (4 / 5) ** (3 / 2) * MU_0 * current / radius

    assert np.isclose(b_center, expected, rtol=1e-12)


def test_wire_vector_potential_conductor_branch_is_finite_and_curls_correctly():
    """Finite-conductor A_z is continuous, finite on axis, and gives mu0 I/(2 pi r).

    The conductor branch exists so the potential can be imposed as Dirichlet
    data on boundaries that cross r = 0 (MAG-13); the filament form diverges
    there.
    """
    current = 1.0
    a = 0.003

    # Continuity and gauge: A_z(a) = 0 from both sides, finite on the axis.
    at_a = AnalyticalSolutions.straight_wire_vector_potential(
        np.array([[a, 0.0, 0.0]]), current, wire_radius=a
    )[0, 2]
    on_axis = AnalyticalSolutions.straight_wire_vector_potential(
        np.array([[0.0, 0.0, 0.0]]), current, wire_radius=a
    )[0, 2]
    assert abs(at_a) < 1e-18
    assert np.isclose(on_axis, MU_0 * current / (4 * np.pi), rtol=1e-12)

    # B_phi = -dA_z/dr outside the conductor, against mu0 I / (2 pi r).
    r0, h = 0.01, 1e-6
    a_plus = AnalyticalSolutions.straight_wire_vector_potential(
        np.array([[r0 + h, 0.0, 0.0]]), current, wire_radius=a
    )[0, 2]
    a_minus = AnalyticalSolutions.straight_wire_vector_potential(
        np.array([[r0 - h, 0.0, 0.0]]), current, wire_radius=a
    )[0, 2]
    b_phi = -(a_plus - a_minus) / (2 * h)
    assert np.isclose(b_phi, MU_0 * current / (2 * np.pi * r0), rtol=1e-8)

    # Default (filament) behaviour is unchanged.
    filament = AnalyticalSolutions.straight_wire_vector_potential(
        np.array([[0.01, 0.0, 0.0]]), current
    )[0, 2]
    assert np.isclose(filament, -MU_0 * current / (2 * np.pi) * np.log(0.01), rtol=1e-14)


def test_loop_vector_potential_reproduces_on_axis_closed_form():
    """curl of the elliptic-integral A_phi matches B_z = mu0 I a^2 / (2(a^2+z^2)^{3/2}).

    Guards the two traps named in the MAG-13 plan: scipy's ellipk/ellipe take
    the parameter m = k^2 (passing k instead is a silent factor error, which a
    curl check against the closed form catches), and rho -> 0 needs its own
    A_phi = 0 branch.
    """
    current = 2.5
    a = 0.05

    # On the axis A_phi must vanish exactly, not evaluate 0/0.
    axis = AnalyticalSolutions.circular_loop_vector_potential(
        np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.02]]), current, a
    )
    assert np.all(np.abs(axis) == 0.0)

    # B_z = (1/rho) d(rho A_phi)/drho, evaluated near the axis where the
    # closed form applies. A_phi ~ rho there, so a centred difference of
    # rho*A_phi over a small rho window recovers B_z(0, z).
    for z in (0.0, 0.02, -0.03):
        rho = 1e-4 * a
        pts = np.array([[2 * rho, 0.0, z], [rho, 0.0, z]])
        A = AnalyticalSolutions.circular_loop_vector_potential(pts, current, a)
        # d(rho A_phi)/drho on [rho, 2rho], divided by the midpoint rho.
        flux_deriv = (2 * rho * A[0, 1] - rho * A[1, 1]) / rho
        b_z = flux_deriv / (1.5 * rho)
        expected = AnalyticalSolutions.circular_loop_magnetic_field_on_axis(
            np.array([z]), current, a
        )[0]
        assert np.isclose(b_z, expected, rtol=1e-6), f"z={z}: {b_z} vs {expected}"


def test_error_metrics_are_zero_for_identical_arrays():
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([1.0, 2.0, 3.0])

    assert ErrorMetrics.l2_error(a, b) == 0.0
    assert ErrorMetrics.max_error(a, b) == 0.0
    assert ErrorMetrics.l2_relative_error(a, b) == 0.0
    assert ErrorMetrics.max_relative_error(a, b) == 0.0
