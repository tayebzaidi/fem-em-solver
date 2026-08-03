"""`MAT-4`: specific absorption rate from the solved complex field.

For ``e^{+jωt}`` **peak** phasors the time-averaged Ohmic dissipation density is

    p(x) = ½ σ(x) |E(x)|²        [W/m³]

and the specific absorption rate is that density divided by the mass density,

    SAR(x) = σ(x) |E(x)|² / (2 ρ(x))      [W/kg]

The ½ is the same peak-phasor convention
:func:`~fem_em_solver.post.power_balance.poynting_power_balance` uses — its
``dissipated_power_w`` is exactly ``∫ ρ·SAR dV`` for uniform ρ, and the two
must not be allowed to drift apart.  An RMS-phasor code would drop the ½; this
package does not use RMS phasors anywhere.

Everything here reads ``e_complex`` (the N1curl solution) through UFL.  It
deliberately does **not** go through :mod:`.phantom_fields`, whose
``dtype=np.float64`` cast discards ``Im(E)`` (the `POST-1` defect): on a lossy
material the imaginary part is the loss, so a SAR built from the real part
alone would be silently wrong by a factor of ``|Re E|²/|E|²``.

``fem.assemble_scalar`` is rank-local; every integral below is reduced across
the communicator before it is divided by another.
"""

from __future__ import annotations

from typing import Optional, Sequence, Union

import numpy as np
import ufl
from mpi4py import MPI

import dolfinx
from dolfinx import fem


def _sigma_as_ufl(sigma: Union[float, fem.Function], msh) -> object:
    if isinstance(sigma, fem.Function):
        if sigma.function_space.mesh is not msh:
            raise ValueError(
                "sigma field and e_complex must live on the same mesh; got "
                "functions from two different meshes, which would integrate "
                "one material distribution against another field"
            )
        return sigma
    value = float(sigma)
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"sigma must be finite and non-negative (S/m), got {sigma!r}")
    return value


def mean_sar(
    e_complex: fem.Function,
    *,
    sigma: Union[float, fem.Function],
    rho: float,
    cell_tags: Optional[dolfinx.mesh.MeshTags] = None,
    subdomain_ids: Optional[Union[int, Sequence[int]]] = None,
    comm: Optional[MPI.Comm] = None,
) -> dict[str, float]:
    """Volume-averaged SAR over a subdomain (or the whole mesh).

    Parameters
    ----------
    e_complex:
        Solved complex ``E`` phasor, peak convention, as produced by
        :class:`~fem_em_solver.core.TimeHarmonicSolver`.
    sigma:
        Conductivity [S/m]: a uniform scalar, or the DG0 ``sigma_field`` the
        solver returns, in which case the integrand carries σ(x).  The average
        is scored against whatever σ is handed in — that is what makes a
        σ-blind control possible.
    rho:
        Mass density [kg/m³], uniform.  A ρ *field* is `MAT-4` step 2
        (mass-averaged 1 g/10 g SAR) and is deliberately not smuggled in here.
    cell_tags, subdomain_ids:
        Restrict the average to the tagged cells.  Both must be given
        together; omitting them averages over the whole mesh.

    Returns
    -------
    dict with ``mean_sar_w_per_kg`` (``∫σ|E|²/(2ρ) dV / ∫dV``),
    ``volume_m3`` (the integration volume actually seen by the form) and
    ``dissipated_power_w`` (``½∫σ|E|²dV`` over the same region, which is the
    :func:`poynting_power_balance` volume leg restricted to the subdomain).
    """
    msh = e_complex.function_space.mesh
    if comm is None:
        comm = msh.comm

    rho_value = float(rho)
    if not np.isfinite(rho_value) or rho_value <= 0.0:
        raise ValueError(f"rho must be finite and positive (kg/m³), got {rho!r}")

    sigma_ufl = _sigma_as_ufl(sigma, msh)

    if (cell_tags is None) != (subdomain_ids is None):
        raise ValueError(
            "cell_tags and subdomain_ids must be given together: a subdomain id "
            "without tags silently integrates over nothing"
        )

    if cell_tags is None:
        dx = ufl.dx
        ids: object = None
    else:
        dx = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)
        ids = (
            [int(subdomain_ids)]
            if np.isscalar(subdomain_ids)
            else [int(i) for i in subdomain_ids]
        )

    def _integrate(integrand) -> complex:
        if ids is None:
            integral = integrand * dx
        else:
            integral = integrand * dx(ids[0])
            for i in ids[1:]:
                integral = integral + integrand * dx(i)
        return comm.allreduce(fem.assemble_scalar(fem.form(integral)), op=MPI.SUM)

    # ufl.inner conjugates its second argument, so inner(E, E) is |E|² — real up
    # to round-off, which is why Re() below is exact rather than a truncation.
    dissipated = float(np.real(_integrate(0.5 * sigma_ufl * ufl.inner(e_complex, e_complex))))
    one = fem.Constant(msh, dolfinx.default_scalar_type(1.0))
    volume = float(np.real(_integrate(one)))

    if volume <= 0.0:
        raise ValueError(
            "the SAR integration region has zero volume — check subdomain_ids "
            f"({subdomain_ids!r}) against the cell tags actually present"
        )

    return {
        "mean_sar_w_per_kg": dissipated / (rho_value * volume),
        "volume_m3": volume,
        "dissipated_power_w": dissipated,
    }


def uniform_sphere_sar_closed_form(
    *,
    e0: float,
    epsilon_r: float,
    sigma: float,
    omega: float,
    rho: float,
    epsilon_0: float,
) -> dict[str, float]:
    """Quasi-static lossy-sphere SAR: ``σ|3E₀/(ε_c+2)|²/(2ρ)``.

    ``ε_c = εᵣ − jσ/(ωε₀)`` in the ``e^{+jωt}`` convention the solver's mass
    term uses (``core/time_harmonic.py``).  The interior field of a sphere in a
    uniform quasi-static field is ``E_in = 3E₀/(ε_c + 2)``, uniform, so the mean
    SAR over the sphere equals the pointwise value.  Returns the loss-tangent
    numerator ``t = σ/(ωε₀)`` and ``|ε_c|`` alongside, because the closed form
    is only valid while ``k₀√|ε_c|·R ≪ 1`` and loss inflates ``|ε_c|``.
    """
    loss_tangent_numerator = sigma / (omega * epsilon_0)
    epsilon_c = complex(epsilon_r, -loss_tangent_numerator)
    e_in = 3.0 * e0 / (epsilon_c + 2.0)
    e_in_sq = float(abs(e_in) ** 2)
    return {
        "sar_w_per_kg": sigma * e_in_sq / (2.0 * rho),
        "e_in_magnitude": float(abs(e_in)),
        "e_in_magnitude_squared": e_in_sq,
        "loss_tangent_numerator": float(loss_tangent_numerator),
        "epsilon_c_magnitude": float(abs(epsilon_c)),
    }
