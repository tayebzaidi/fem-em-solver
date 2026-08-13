"""Analytical solutions for electromagnetic validation cases."""

import numpy as np
from typing import Union, Callable


class AnalyticalSolutions:
    """Collection of analytical solutions for EM validation."""
    
    @staticmethod
    def straight_wire_magnetic_field(
        points: np.ndarray,
        current: float,
        wire_position: np.ndarray = None
    ) -> np.ndarray:
        """Analytical B-field for infinite straight wire.
        
        For a wire along the z-axis carrying current I:
            B_φ = μ₀I / (2πr)
        
        In Cartesian coordinates:
            B_x = -μ₀I * y / (2πr²)
            B_y =  μ₀I * x / (2πr²)
            B_z = 0
        
        Parameters
        ----------
        points : np.ndarray
            Array of shape (n, 3) with evaluation points
        current : float
            Current in wire [A]
        wire_position : np.ndarray, optional
            (x, y) position of wire. Default is (0, 0)
            
        Returns
        -------
        np.ndarray
            B-field at points, shape (n, 3)
        """
        if wire_position is None:
            wire_position = np.array([0.0, 0.0])
        
        mu_0 = 4 * np.pi * 1e-7  # H/m
        
        # Extract coordinates relative to wire
        x = points[:, 0] - wire_position[0]
        y = points[:, 1] - wire_position[1]
        
        # Cylindrical radius
        r = np.sqrt(x**2 + y**2)
        
        # Avoid division by zero at wire location
        r = np.maximum(r, 1e-10)
        
        # B-field magnitude (azimuthal direction)
        B_phi = mu_0 * current / (2 * np.pi * r)
        
        # Convert to Cartesian
        # B_φ direction is (-y/r, x/r, 0)
        B = np.zeros_like(points)
        B[:, 0] = -B_phi * y / r  # B_x
        B[:, 1] =  B_phi * x / r  # B_y
        B[:, 2] = 0.0              # B_z
        
        return B
    
    @staticmethod
    def straight_wire_vector_potential(
        points: np.ndarray,
        current: float,
        wire_position: np.ndarray = None,
        A_ref: float = 0.0,
        wire_radius: float = None
    ) -> np.ndarray:
        """Analytical A-field for infinite straight wire.

        The magnetic vector potential for a wire along z-axis:
            A_z = -μ₀I / (2π) * ln(r/r_ref)

        Choosing r_ref such that A=0 at some reference point.

        With ``wire_radius = a`` the uniform-current-density conductor form is
        used instead, gauged so that A_z(a) = 0::

            A_z(r) = -μ₀I/(2π) · ln(r/a)          r ≥ a
            A_z(r) =  μ₀I/(4π) · (1 - r²/a²)      r ≤ a

        Both branches have the same curl as the filament solution outside the
        conductor, and the interior branch is *finite on the axis*. That
        matters when this field is imposed as Dirichlet data (MAG-13): the
        domain end caps of ``straight_wire_domain`` cross r = 0, where the
        filament form diverges logarithmically.

        Parameters
        ----------
        points : np.ndarray
            Array of shape (n, 3) with evaluation points
        current : float
            Current in wire [A]
        wire_position : np.ndarray, optional
            (x, y) position of wire
        A_ref : float
            Reference potential (gauge choice)
        wire_radius : float, optional
            Conductor radius [m]. If given, use the finite-conductor form
            above; if None (default) the pure filament form ``-μ₀I/(2π)·ln r``
            is returned unchanged.

        Returns
        -------
        np.ndarray
            A-field at points, shape (n, 3)
        """
        if wire_position is None:
            wire_position = np.array([0.0, 0.0])

        mu_0 = 4 * np.pi * 1e-7

        x = points[:, 0] - wire_position[0]
        y = points[:, 1] - wire_position[1]
        r = np.sqrt(x**2 + y**2)

        # A has only z-component
        A = np.zeros_like(points)

        if wire_radius is None:
            # Avoid log(0)
            r = np.maximum(r, 1e-10)
            A[:, 2] = -mu_0 * current / (2 * np.pi) * np.log(r) + A_ref
            return A

        if wire_radius <= 0:
            raise ValueError(f"wire_radius must be positive, got {wire_radius!r}")

        outside = r >= wire_radius
        a_z = np.empty_like(r)
        a_z[outside] = (
            -mu_0 * current / (2 * np.pi) * np.log(r[outside] / wire_radius)
        )
        a_z[~outside] = (
            mu_0 * current / (4 * np.pi) * (1.0 - (r[~outside] / wire_radius) ** 2)
        )
        A[:, 2] = a_z + A_ref
        return A

    @staticmethod
    def circular_loop_vector_potential(
        points: np.ndarray,
        current: float,
        radius: float,
        loop_center: float = 0.0
    ) -> np.ndarray:
        """Off-axis vector potential of a circular current loop (Jackson 5.37).

        For a loop of radius ``a`` in the plane z = z0, carrying current I
        counter-clockwise seen from +z, the only non-zero component is
        azimuthal::

            A_φ(ρ,z) = (μ₀I/π)·√(a/ρ)·[(1 − k²/2)·K(k) − E(k)] / k
            k² = 4aρ / ((a+ρ)² + (z−z0)²)

        Two conventions matter here. ``scipy.special.ellipk``/``ellipe`` take
        the *parameter* ``m = k²``, not the modulus ``k`` — passing ``k`` is a
        silent factor error. And ρ → 0 needs its own branch: A_φ = 0 on the
        axis by symmetry, while the formula there is 0/0.

        Parameters
        ----------
        points : np.ndarray
            Array of shape (n, 3) with evaluation points
        current : float
            Loop current [A]
        radius : float
            Loop radius ``a`` [m]
        loop_center : float
            z-position of the loop plane [m]

        Returns
        -------
        np.ndarray
            A-field at points in Cartesian components, shape (n, 3)
        """
        from scipy.special import ellipe, ellipk

        if radius <= 0:
            raise ValueError(f"radius must be positive, got {radius!r}")

        mu_0 = 4 * np.pi * 1e-7

        x = points[:, 0]
        y = points[:, 1]
        z = points[:, 2] - loop_center
        rho = np.sqrt(x**2 + y**2)

        A = np.zeros_like(points)
        # On-axis (and at the wire itself, where the potential diverges) the
        # azimuthal direction is undefined; A_φ = 0 is the symmetry answer.
        on_axis = rho < 1e-14 * radius
        active = ~on_axis
        if not np.any(active):
            return A

        rho_a = rho[active]
        z_a = z[active]
        m = 4.0 * radius * rho_a / ((radius + rho_a) ** 2 + z_a**2)  # m = k²
        k = np.sqrt(m)
        a_phi = (
            mu_0 * current / np.pi
            * np.sqrt(radius / rho_a)
            * ((1.0 - m / 2.0) * ellipk(m) - ellipe(m))
            / k
        )

        # φ̂ = (-y, x, 0)/ρ
        A[active, 0] = -a_phi * y[active] / rho_a
        A[active, 1] = a_phi * x[active] / rho_a
        return A

    @staticmethod
    def circular_loop_magnetic_field(
        points: np.ndarray,
        current: float,
        radius: float,
        loop_center: float = 0.0
    ) -> np.ndarray:
        """Off-axis B-field of a circular current loop (elliptic integrals).

        For a loop of radius ``a`` in the plane z = z0, carrying current I
        counter-clockwise seen from +z, with α² = (a−ρ)² + (z−z0)²,
        β² = (a+ρ)² + (z−z0)² and parameter m = k² = 4aρ/β²::

            B_ρ = μ₀I (z−z0) / (2π ρ α² β) · [(a² + ρ² + (z−z0)²)·E(m) − α²·K(m)]
            B_z = μ₀I / (2π α² β) · [(a² − ρ² − (z−z0)²)·E(m) + α²·K(m)]

        As with :meth:`circular_loop_vector_potential`, scipy's ``ellipk`` /
        ``ellipe`` take the *parameter* m = k², not the modulus k. The ρ → 0
        limit reduces to :meth:`circular_loop_magnetic_field_on_axis` and is
        handled on a separate branch (B_ρ = 0 by symmetry). The field diverges
        on the filament itself (α → 0); α² is clamped there so evaluation stays
        finite for visualization, but values near the wire are not meaningful.

        Parameters
        ----------
        points : np.ndarray
            Array of shape (n, 3) with evaluation points
        current : float
            Loop current [A]
        radius : float
            Loop radius ``a`` [m]
        loop_center : float
            z-position of the loop plane [m]

        Returns
        -------
        np.ndarray
            B-field at points in Cartesian components, shape (n, 3)
        """
        from scipy.special import ellipe, ellipk

        if radius <= 0:
            raise ValueError(f"radius must be positive, got {radius!r}")

        mu_0 = 4 * np.pi * 1e-7

        x = points[:, 0]
        y = points[:, 1]
        z = points[:, 2] - loop_center
        rho = np.sqrt(x**2 + y**2)

        B = np.zeros_like(points, dtype=np.float64)

        on_axis = rho < 1e-14 * radius
        # On-axis branch: B_ρ = 0 by symmetry, closed-form B_z.
        B[on_axis, 2] = AnalyticalSolutions.circular_loop_magnetic_field_on_axis(
            points[on_axis, 2], current, radius, loop_center
        )

        active = ~on_axis
        if not np.any(active):
            return B

        rho_a = rho[active]
        z_a = z[active]

        alpha2 = (radius - rho_a) ** 2 + z_a**2
        beta = np.sqrt((radius + rho_a) ** 2 + z_a**2)
        # Clamp the filament singularity so evaluation stays finite.
        alpha2 = np.maximum(alpha2, (1e-6 * radius) ** 2)
        m = 4.0 * radius * rho_a / beta**2
        m = np.minimum(m, 1.0 - 1e-12)

        K = ellipk(m)
        E = ellipe(m)
        pref = mu_0 * current / (2 * np.pi * alpha2 * beta)
        s2 = radius**2 + rho_a**2 + z_a**2

        B_rho = pref * (z_a / rho_a) * (s2 * E - alpha2 * K)
        B_z = pref * ((radius**2 - rho_a**2 - z_a**2) * E + alpha2 * K)

        # ρ̂ = (x, y, 0)/ρ
        B[active, 0] = B_rho * x[active] / rho_a
        B[active, 1] = B_rho * y[active] / rho_a
        B[active, 2] = B_z
        return B

    @staticmethod
    def circular_loop_magnetic_field_on_axis(
        z: np.ndarray,
        current: float,
        radius: float,
        loop_center: float = 0.0
    ) -> np.ndarray:
        """B-field on axis of circular current loop.
        
        For a loop of radius a in the xy-plane, centered at z=z0:
            B_z(z) = μ₀Ia² / (2(a² + (z-z0)²)^(3/2))
        
        Parameters
        ----------
        z : np.ndarray
            Positions along z-axis [m]
        current : float
            Current in loop [A]
        radius : float
            Loop radius [m]
        loop_center : float
            z-position of loop center [m]
            
        Returns
        -------
        np.ndarray
            B_z at positions z
        """
        mu_0 = 4 * np.pi * 1e-7
        
        dz = z - loop_center
        denom = 2 * (radius**2 + dz**2)**(3/2)
        
        B_z = mu_0 * current * radius**2 / denom
        
        return B_z
    
    @staticmethod
    def helmholtz_coil_field_on_axis(
        z: np.ndarray,
        current: float,
        radius: float,
        separation: float = None
    ) -> np.ndarray:
        """B-field on axis of Helmholtz coil.
        
        Helmholtz coil: two identical loops separated by distance = radius,
        carrying current in same direction. This configuration gives
        maximally uniform field in the center.
        
        Parameters
        ----------
        z : np.ndarray
            Positions along z-axis [m]
        current : float
            Current in each loop [A]
        radius : float
            Loop radius [m]
        separation : float, optional
            Distance between loops. Default is radius (Helmholtz condition)
            
        Returns
        -------
        np.ndarray
            B_z at positions z
        """
        if separation is None:
            separation = radius  # Helmholtz condition
        
        # Center the configuration at z=0
        z1 = -separation / 2
        z2 = separation / 2
        
        B1 = AnalyticalSolutions.circular_loop_magnetic_field_on_axis(
            z, current, radius, z1
        )
        B2 = AnalyticalSolutions.circular_loop_magnetic_field_on_axis(
            z, current, radius, z2
        )
        
        return B1 + B2


def complex_permittivity(
    epsilon_r: float, sigma: float, frequency_hz: float, conjugate: bool = False
) -> complex:
    """``ε_c = εᵣ − j·σ/(ωε₀)`` in the project's ``e^{+jωt}`` convention.

    ``conjugate=True`` returns the wrong-sign value ``εᵣ + j·σ/(ωε₀)`` and
    exists only so a negative control can pass it deliberately (`TH-1`
    formulation note: the sign convention is part of the spec).
    """
    from .constants import EPSILON_0

    omega = 2.0 * np.pi * frequency_hz
    loss = sigma / (omega * EPSILON_0)
    return complex(epsilon_r, loss if conjugate else -loss)


class LossySphereSeries:
    """Full-wave series solution for a lossy dielectric sphere in a plane wave.

    ``TH-10`` step 1 anchor.  The sphere of radius ``a`` and complex relative
    permittivity ``ε_c`` sits in free space; the incident wave travels along
    ``+z`` and is polarised along ``x``.  In the project's ``e^{+jωt}``
    convention (``TH-1`` formulation note) that incident field is

        E_inc(r) = E₀ x̂ · e^{−j k₀ z},      ε_c = εᵣ − j·σ/(ωε₀)

    and the interior/scattered fields are the classical Mie series.  Textbook
    Mie theory (Bohren & Huffman, *Absorption and Scattering of Light by Small
    Particles*, ch. 4, eqs. 4.37/4.40/4.45/4.50/4.53) is written in the
    ``e^{−iωt}`` convention, where the lossy permittivity is
    ``εᵣ + i·σ/(ωε₀)``.  **This class evaluates the textbook series with the
    conjugated permittivity and conjugates the resulting field**, which is the
    convention import the ``TH-1`` note demands; the conjugated-convention
    evaluation is available as ``conjugate_convention=True`` purely as a
    negative control and is *not* physical here.  Special-function definitions
    and the Wronskian follow Jin, *The FEM in Electromagnetics* 3rd ed.,
    App. E.2 (spherical Bessel/Hankel functions, eqs. E.24–E.31); the FEM-side
    dielectric-sphere scattering fixture this anchors is Jin §9.4 (Fig. 9.11).

    Only ``numpy``/``scipy`` — no mesh, no DolfinX.

    Notes
    -----
    ``scipy.special.spherical_jn`` rejects complex arguments, so the interior
    radial functions go through ``scipy.special.jv(n+½, z)``, which does not:
    ``j_n(z) = √(π/2z)·J_{n+½}(z)``.  The exterior argument ``k₀r`` is real.
    """

    def __init__(
        self,
        radius: float,
        epsilon_c: complex,
        frequency_hz: float,
        e0: float = 1.0,
        n_terms: int = None,
        conjugate_convention: bool = False,
    ):
        from .constants import EPSILON_0, MU_0

        if radius <= 0.0:
            raise ValueError("radius must be positive")
        if frequency_hz <= 0.0:
            raise ValueError("frequency_hz must be positive")

        self.radius = float(radius)
        self.frequency_hz = float(frequency_hz)
        self.e0 = float(e0)
        self.conjugate_convention = bool(conjugate_convention)

        # e^{+jωt} spec value, kept for reporting.
        self.epsilon_c = complex(epsilon_c)
        # Textbook (e^{-iωt}) permittivity.  The negative control skips the
        # conjugation, i.e. evaluates the series as if ε_c = εᵣ + jσ/(ωε₀).
        self.epsilon_c_textbook = (
            self.epsilon_c if conjugate_convention else np.conj(self.epsilon_c)
        )

        omega = 2.0 * np.pi * self.frequency_hz
        self.k0 = omega * np.sqrt(MU_0 * EPSILON_0)
        # Relative refractive index m = k_in/k₀ = √ε_c, principal branch with
        # Re m > 0 (the physical root for a passive medium in this convention).
        m = np.sqrt(complex(self.epsilon_c_textbook))
        self.m = m if m.real >= 0.0 else -m

        self.size_parameter = self.k0 * self.radius
        self.n_terms = int(n_terms) if n_terms is not None else self._wiscombe_n()
        if self.n_terms < 1:
            raise ValueError("n_terms must be >= 1")

        self._coefficients = self._mie_coefficients()

    # ------------------------------------------------------------------ setup

    def _wiscombe_n(self) -> int:
        """Wiscombe's truncation ``x + 4x^{1/3} + 2`` on the larger of the two
        size parameters ``k₀a`` and ``|m|k₀a``, floored at 4 terms."""
        x = max(self.size_parameter, abs(self.m) * self.size_parameter)
        return int(max(4, np.ceil(x + 4.0 * x ** (1.0 / 3.0) + 2.0)))

    @staticmethod
    def _sph_jn(n: np.ndarray, z):
        """``j_n(z)`` for complex ``z`` via ``J_{n+½}``."""
        from scipy.special import jv

        z = np.asarray(z, dtype=complex)
        return np.sqrt(np.pi / (2.0 * z)) * jv(n + 0.5, z)

    @staticmethod
    def _sph_h1(n: np.ndarray, z):
        """``h_n^{(1)}(z) = √(π/2z)·H^{(1)}_{n+½}(z)`` (Jin App. E, eq. E.28)."""
        from scipy.special import hankel1

        z = np.asarray(z, dtype=complex)
        return np.sqrt(np.pi / (2.0 * z)) * hankel1(n + 0.5, z)

    @classmethod
    def _riccati(cls, n_max: int, z, kind: str):
        """Riccati-Bessel ``ψ_n(z) = z·j_n(z)`` / ``ξ_n(z) = z·h_n^{(1)}(z)``
        and its derivative, for ``n = 1…n_max``.

        The derivative uses the standard downward relation
        ``ψ_n'(z) = ψ_{n-1}(z) − n·ψ_n(z)/z`` (Jin App. E, eq. E.30 applied to
        the Riccati form), which needs the ``n = 0`` value as well.
        """
        z = np.asarray(z, dtype=complex)
        orders = np.arange(0, n_max + 1)
        shape = (n_max + 1,) + z.shape
        zz = np.broadcast_to(z, shape)
        nn = orders.reshape((-1,) + (1,) * z.ndim)
        radial = cls._sph_jn(nn, zz) if kind == "j" else cls._sph_h1(nn, zz)
        psi = zz * radial
        d_psi = psi[:-1] - nn[1:] * psi[1:] / zz[1:]
        return psi[1:], d_psi  # both indexed n = 1…n_max

    def _mie_coefficients(self) -> dict:
        """``a_n, b_n`` (scattered) and ``c_n, d_n`` (internal), B&H eq. 4.53.

        For ``m = 1`` the numerators reduce to the Wronskian
        ``ψ_nξ_n' − ξ_nψ_n' = i`` and ``c_n = d_n = 1`` exactly — that identity
        is what the empty-limit gate exercises.
        """
        n_max = self.n_terms
        x = np.array([self.size_parameter], dtype=complex)
        m = self.m

        psi_x, dpsi_x = self._riccati(n_max, x, "j")
        xi_x, dxi_x = self._riccati(n_max, x, "h1")
        psi_mx, dpsi_mx = self._riccati(n_max, m * x, "j")

        psi_x, dpsi_x = psi_x[:, 0], dpsi_x[:, 0]
        xi_x, dxi_x = xi_x[:, 0], dxi_x[:, 0]
        psi_mx, dpsi_mx = psi_mx[:, 0], dpsi_mx[:, 0]

        a_n = (m * psi_mx * dpsi_x - psi_x * dpsi_mx) / (
            m * psi_mx * dxi_x - xi_x * dpsi_mx
        )
        b_n = (psi_mx * dpsi_x - m * psi_x * dpsi_mx) / (
            psi_mx * dxi_x - m * xi_x * dpsi_mx
        )
        wronskian = m * (psi_x * dxi_x - xi_x * dpsi_x)
        c_n = wronskian / (psi_mx * dxi_x - m * xi_x * dpsi_mx)
        d_n = wronskian / (m * psi_mx * dxi_x - xi_x * dpsi_mx)
        return {"a": a_n, "b": b_n, "c": c_n, "d": d_n}

    @property
    def coefficients(self) -> dict:
        return self._coefficients

    def last_term_bound(self) -> float:
        """``|E_N|·max(|c_N|,|d_N|)·|j_N(m k₀a)|/E₀`` — the dropped tail.

        The radial factor is what actually kills the tail for a small sphere
        (``j_N(z) ~ z^N/(2N+1)!!``), so leaving it out reports a bound of order
        one for the empty limit and reads as alarming when the true tail is
        ``1e-9``.  Printed rather than assumed: a sweep in ``n_terms`` is the
        honest check, and this is the cheap companion to it.
        """
        n = self.n_terms
        e_n = (2.0 * n + 1.0) / (n * (n + 1.0))
        radial = abs(
            complex(
                self._sph_jn(
                    np.array([n]), np.array([self.m * self.k0 * self.radius])
                )[0]
            )
        )
        return float(
            e_n
            * max(abs(self._coefficients["c"][-1]), abs(self._coefficients["d"][-1]))
            * radial
        )

    # ------------------------------------------------------------------ fields

    @staticmethod
    def _angular_functions(n_max: int, mu: np.ndarray):
        """``π_n(cosθ) = P_n¹/sinθ`` and ``τ_n = dP_n¹/dθ`` by upward recurrence
        (B&H eq. 4.47); both are finite on the axis."""
        pi_n = np.zeros((n_max + 1,) + mu.shape)
        tau_n = np.zeros((n_max + 1,) + mu.shape)
        pi_n[1] = 1.0
        tau_n[1] = mu
        for n in range(2, n_max + 1):
            pi_n[n] = ((2 * n - 1) / (n - 1)) * mu * pi_n[n - 1] - (n / (n - 1)) * pi_n[
                n - 2
            ]
            tau_n[n] = n * mu * pi_n[n] - (n + 1) * pi_n[n - 1]
        return pi_n[1:], tau_n[1:]

    def _spherical_frame(self, points: np.ndarray):
        points = np.asarray(points, dtype=float)
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError("points must have shape (n, 3)")
        r = np.linalg.norm(points, axis=1)
        if np.any(r < 1e-14):
            raise ValueError(
                "the series is evaluated in spherical coordinates; r = 0 is a "
                "removable singularity that this implementation does not take "
                "the limit of — offset the probe point"
            )
        mu = points[:, 2] / r
        mu = np.clip(mu, -1.0, 1.0)
        sin_theta = np.sqrt(np.maximum(0.0, 1.0 - mu**2))
        phi = np.arctan2(points[:, 1], points[:, 0])
        cos_phi, sin_phi = np.cos(phi), np.sin(phi)
        e_r = np.stack(
            [sin_theta * cos_phi, sin_theta * sin_phi, mu], axis=1
        )
        e_theta = np.stack(
            [mu * cos_phi, mu * sin_phi, -sin_theta], axis=1
        )
        e_phi = np.stack([-sin_phi, cos_phi, np.zeros_like(phi)], axis=1)
        return r, mu, sin_theta, cos_phi, sin_phi, e_r, e_theta, e_phi

    def _series(self, points: np.ndarray, which: str) -> np.ndarray:
        """Evaluate one of ``incident|internal|scattered`` at ``points``.

        Returns the textbook (``e^{-iωt}``) field; the public methods conjugate.
        """
        n_max = self.n_terms
        r, mu, sin_theta, cos_phi, sin_phi, e_r, e_theta, e_phi = (
            self._spherical_frame(points)
        )
        pi_n, tau_n = self._angular_functions(n_max, mu)
        n = np.arange(1, n_max + 1).reshape(-1, 1)

        if which == "internal":
            rho = self.m * self.k0 * r
            psi, d_psi = self._riccati(n_max, rho, "j")
            coeff_m, coeff_n = self._coefficients["c"], self._coefficients["d"]
        elif which == "incident":
            rho = (self.k0 * r).astype(complex)
            psi, d_psi = self._riccati(n_max, rho, "j")
            coeff_m = np.ones(n_max, dtype=complex)
            coeff_n = np.ones(n_max, dtype=complex)
        elif which == "scattered":
            rho = (self.k0 * r).astype(complex)
            psi, d_psi = self._riccati(n_max, rho, "h1")
            coeff_m, coeff_n = self._coefficients["b"], self._coefficients["a"]
        else:
            raise ValueError(f"unknown series {which!r}")

        z_n = psi / rho  # the radial function itself
        d_n = d_psi / rho  # [ρ z_n(ρ)]'/ρ
        e_n = 1j**n.astype(float) * self.e0 * (2.0 * n + 1.0) / (n * (n + 1.0))
        coeff_m = coeff_m.reshape(-1, 1)
        coeff_n = coeff_n.reshape(-1, 1)

        # M_o1n and N_e1n, B&H eq. 4.50.
        m_theta = cos_phi * pi_n * z_n
        m_phi = -sin_phi * tau_n * z_n
        n_r = cos_phi * n * (n + 1.0) * sin_theta * pi_n * z_n / rho
        n_theta = cos_phi * tau_n * d_n
        n_phi = -sin_phi * pi_n * d_n

        if which == "scattered":
            # E_s = Σ E_n (i a_n N^(3) − b_n M^(3));  coeff_m = b, coeff_n = a.
            w_m, w_n = -coeff_m, 1j * coeff_n
        else:
            # E = Σ E_n (c_n M^(1) − i d_n N^(1)); incident is c = d = 1.
            w_m, w_n = coeff_m, -1j * coeff_n

        comp_r = np.sum(e_n * w_n * n_r, axis=0)
        comp_theta = np.sum(e_n * (w_m * m_theta + w_n * n_theta), axis=0)
        comp_phi = np.sum(e_n * (w_m * m_phi + w_n * n_phi), axis=0)

        return (
            comp_r[:, None] * e_r
            + comp_theta[:, None] * e_theta
            + comp_phi[:, None] * e_phi
        )

    def incident_field(self, points: np.ndarray) -> np.ndarray:
        """Series form of the incident plane wave, shape (n, 3), complex."""
        return np.conj(self._series(points, "incident"))

    def incident_field_closed_form(self, points: np.ndarray) -> np.ndarray:
        """``E₀ x̂ e^{−j k₀ z}`` — what the incident series must reproduce."""
        points = np.asarray(points, dtype=float)
        field = np.zeros((points.shape[0], 3), dtype=complex)
        field[:, 0] = self.e0 * np.exp(-1j * self.k0 * points[:, 2])
        return field

    def internal_field(self, points: np.ndarray) -> np.ndarray:
        """Interior field (valid for ``r < a``), shape (n, 3), complex."""
        return np.conj(self._series(points, "internal"))

    def scattered_field(self, points: np.ndarray) -> np.ndarray:
        """Scattered field (valid for ``r > a``), shape (n, 3), complex."""
        return np.conj(self._series(points, "scattered"))

    def total_field(self, points: np.ndarray) -> np.ndarray:
        """Piecewise total field: interior series inside, incident + scattered
        outside.  This is the callable a later ``TH-10`` step drives the box
        wall with, exactly as ``TH-8`` drives its box with the quasi-static
        closed form."""
        points = np.asarray(points, dtype=float)
        r = np.linalg.norm(points, axis=1)
        inside = r < self.radius
        field = np.zeros((points.shape[0], 3), dtype=complex)
        if np.any(inside):
            field[inside] = self.internal_field(points[inside])
        outside = ~inside
        if np.any(outside):
            field[outside] = self.incident_field(points[outside]) + (
                self.scattered_field(points[outside])
            )
        return field

    def quasistatic_internal_field(self) -> complex:
        """``3E₀/(ε_c + 2)`` — the ``TH-8`` closed form continued onto the
        imaginary axis of ``ε_c``.  The full-wave interior field must approach
        this (uniform, x̂-directed) value as ``|m|k₀a → 0``."""
        return 3.0 * self.e0 / (self.epsilon_c + 2.0)


class ErrorMetrics:
    """Error metrics for comparing numerical and analytical solutions."""
    
    @staticmethod
    def l2_error(numerical: np.ndarray, analytical: np.ndarray) -> float:
        """Compute L2 norm of error.
        
        ||u_num - u_ana||₂ = sqrt(∫ |u_num - u_ana|² dx)
        
        For discrete points:
            L2_error = sqrt(sum(|u_num - u_ana|²))
        """
        diff = numerical - analytical
        return np.sqrt(np.sum(diff**2))
    
    @staticmethod
    def l2_relative_error(numerical: np.ndarray, analytical: np.ndarray) -> float:
        """Compute relative L2 error."""
        l2_err = ErrorMetrics.l2_error(numerical, analytical)
        l2_ana = np.sqrt(np.sum(analytical**2))
        
        if l2_ana < 1e-15:
            return l2_err
        
        return l2_err / l2_ana
    
    @staticmethod
    def max_error(numerical: np.ndarray, analytical: np.ndarray) -> float:
        """Compute maximum absolute error (L∞ norm)."""
        return np.max(np.abs(numerical - analytical))
    
    @staticmethod
    def max_relative_error(numerical: np.ndarray, analytical: np.ndarray) -> float:
        """Compute maximum relative error."""
        abs_err = np.abs(numerical - analytical)
        max_abs_ana = np.max(np.abs(analytical))
        
        if max_abs_ana < 1e-15:
            return np.max(abs_err)
        
        return np.max(abs_err / (np.abs(analytical) + 1e-15))
