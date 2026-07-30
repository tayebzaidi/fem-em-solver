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
