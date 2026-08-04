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

from typing import Mapping, Optional, Sequence, Union

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


def build_density_field(
    mesh,
    default_rho: float,
    *,
    cell_tags: Optional[dolfinx.mesh.MeshTags] = None,
    density_map: Optional[Mapping[int, float]] = None,
) -> fem.Function:
    """DG0 mass-density field [kg/m³], cell-wise, tagged regions overriding.

    The same cell-wise DG0 construction
    :func:`~fem_em_solver.core.time_harmonic.build_material_fields` uses for σ
    and εᵣ.  ρ lives here rather than there because it is a *post-processing*
    property: it never enters the curl-curl operator, and widening
    ``build_material_fields``' two-tuple return would touch every solver
    caller for a quantity none of them assembles.

    Density must be a field and not a python float multiplied in afterwards:
    :func:`mass_averaged_sar` divides an integral of σ|E|² by an integral of ρ
    over the *same* region, and once the region spans two materials those two
    integrals no longer share a constant.
    """
    q0 = fem.functionspace(mesh, ("DG", 0))
    rho_field = fem.Function(q0, name="rho")
    values = rho_field.x.array

    default_value = float(default_rho)
    if not np.isfinite(default_value) or default_value <= 0.0:
        raise ValueError(f"default_rho must be finite and positive (kg/m³), got {default_rho!r}")
    values[:] = default_value

    if density_map:
        if cell_tags is None:
            raise ValueError(
                "density_map requires cell_tags so each requested tag can be assigned a density"
            )
        # cell_tags.values is rank-local: a tag missing here may live on another
        # rank, so "unknown tag" is only an error after a MAX reduction.
        known_tags = {int(tag) for tag in np.asarray(cell_tags.values)}
        for tag, rho_tag in density_map.items():
            rho_value = float(rho_tag)
            if not np.isfinite(rho_value) or rho_value <= 0.0:
                raise ValueError(
                    f"density_map[{int(tag)}] must be finite and positive (kg/m³), got {rho_tag!r}"
                )
            anywhere = mesh.comm.allreduce(int(int(tag) in known_tags), op=MPI.MAX)
            if anywhere == 0:
                raise ValueError(
                    f"density_map references tag {int(tag)}, which is on no rank's cell_tags"
                )
            tag_cells = cell_tags.indices[cell_tags.values == int(tag)]
            for cell in tag_cells:
                values[q0.dofmap.cell_dofs(int(cell))] = rho_value

    rho_field.x.scatter_forward()
    return rho_field


def averaging_ball_radius(*, mass_kg: float, rho: float) -> float:
    """Radius of the ball holding ``mass_kg`` at uniform density ``rho``.

    ``m = ρ·4πa³/3`` ⇒ ``a = (3m/(4πρ))^(1/3)``.  IEEE C95.3 specifies a *cube*;
    the shape is irrelevant to the operator identities gated here (numerator and
    denominator share whatever region is used) and a ball keeps the averaging
    volume isotropic about the sample point.
    """
    mass = float(mass_kg)
    rho_value = float(rho)
    if not np.isfinite(mass) or mass <= 0.0:
        raise ValueError(f"mass_kg must be finite and positive, got {mass_kg!r}")
    if not np.isfinite(rho_value) or rho_value <= 0.0:
        raise ValueError(f"rho must be finite and positive (kg/m³), got {rho!r}")
    return float((3.0 * mass / (4.0 * np.pi * rho_value)) ** (1.0 / 3.0))


def mass_averaged_sar(
    e_complex: fem.Function,
    *,
    sigma: Union[float, fem.Function],
    rho: Union[float, fem.Function],
    center: Sequence[float],
    radius: float,
    comm: Optional[MPI.Comm] = None,
    quadrature_degree: int = 12,
) -> dict[str, float]:
    """SAR averaged over a ball of radius ``radius`` centred at ``center``.

        SAR_avg = ∫_B ½σ|E|² dV  /  ∫_B ρ dV          [W/kg]

    i.e. absorbed power in the averaging volume divided by the *mass* of the
    averaging volume — the mass-averaging definition, not a volume average of
    the pointwise SAR.  The two agree only where σ, ρ and |E| are all uniform,
    which is exactly the identity :mod:`tests.validation.test_mass_averaged_sar`
    gates.

    The ball is imposed as a UFL ``conditional`` on the spatial coordinate, so
    cells straddling ``r = radius`` contribute the fraction their quadrature
    points see.  ``quadrature_degree`` therefore sets the accuracy of the region
    itself, not of the integrand: the default 12 was chosen by measurement (see
    the `MAT-4` step-2 probe log), not by taste.

    ``center`` is built into the form as plain floats.  A ``fem.Constant`` would
    be complex-typed in the complex build and ``ufl.lt`` cannot compare complex
    numbers.

    Returns
    -------
    dict with ``averaged_sar_w_per_kg``, ``mass_kg`` (``∫_B ρ dV``, the meshed
    mass of the averaging volume), ``volume_m3`` and ``dissipated_power_w``.
    """
    msh = e_complex.function_space.mesh
    if comm is None:
        comm = msh.comm

    radius_value = float(radius)
    if not np.isfinite(radius_value) or radius_value <= 0.0:
        raise ValueError(f"radius must be finite and positive (m), got {radius!r}")

    center_values = [float(c) for c in center]
    if len(center_values) != 3 or not all(np.isfinite(c) for c in center_values):
        raise ValueError(f"center must be three finite coordinates, got {center!r}")

    sigma_ufl = _sigma_as_ufl(sigma, msh)
    if isinstance(rho, fem.Function):
        if rho.function_space.mesh is not msh:
            raise ValueError("rho field and e_complex must live on the same mesh")
        rho_ufl: object = rho
    else:
        rho_scalar = float(rho)
        if not np.isfinite(rho_scalar) or rho_scalar <= 0.0:
            raise ValueError(f"rho must be finite and positive (kg/m³), got {rho!r}")
        rho_ufl = rho_scalar

    x = ufl.SpatialCoordinate(msh)
    offset = x - ufl.as_vector(center_values)
    # ufl.real is not cosmetic: in the complex build the literal centre vector is
    # complex-typed, so for a non-zero centre ``dot(offset, offset)`` reaches the
    # comparison checker as complex and ufl.lt raises ComplexComparisonError.  A
    # zero centre simplifies away and hides it — which is exactly how the step-2
    # probe passed the identity test and failed the surface control.
    inside = ufl.conditional(
        ufl.lt(ufl.real(ufl.dot(offset, offset)), radius_value**2), 1.0, 0.0
    )
    dx = ufl.Measure(
        "dx", domain=msh, metadata={"quadrature_degree": int(quadrature_degree)}
    )

    def _integrate(integrand) -> complex:
        return comm.allreduce(
            fem.assemble_scalar(fem.form(inside * integrand * dx)), op=MPI.SUM
        )

    # Numerator and denominator are reduced separately and divided only after:
    # an averaging ball straddles rank boundaries by construction, so a local
    # ratio would be wrong on every rank that holds part of it.
    dissipated = float(
        np.real(_integrate(0.5 * sigma_ufl * ufl.inner(e_complex, e_complex)))
    )
    mass = float(np.real(_integrate(rho_ufl)))
    one = fem.Constant(msh, dolfinx.default_scalar_type(1.0))
    volume = float(np.real(_integrate(one)))

    if mass <= 0.0 or volume <= 0.0:
        raise ValueError(
            f"the averaging ball (center {center_values}, radius {radius_value}) "
            "encloses no meshed volume — check that it lies inside the mesh"
        )

    return {
        "averaged_sar_w_per_kg": dissipated / mass,
        "mass_kg": mass,
        "volume_m3": volume,
        "dissipated_power_w": dissipated,
    }


def point_sar(
    e_real: fem.Function,
    e_imag: fem.Function,
    points: np.ndarray,
    *,
    sigma: float,
    rho: float,
    comm: Optional[MPI.Comm] = None,
) -> np.ndarray:
    """Pointwise ``σ|E|²/(2ρ)`` at ``points``, from the split real/imag fields.

    Point evaluation goes through
    :func:`~fem_em_solver.post.evaluation.evaluate_vector_field_parallel`, which
    is the only rank-safe path; a point outside the mesh raises rather than
    returning a zero that would read as "no absorption here".
    """
    from .evaluation import evaluate_vector_field_parallel

    if comm is None:
        comm = e_real.function_space.mesh.comm

    points = np.atleast_2d(np.asarray(points, dtype=np.float64))
    real_values, valid_real = evaluate_vector_field_parallel(e_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(e_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(
            f"{int((~valid).sum())} of {points.shape[0]} SAR probe points were not "
            "evaluated on any rank"
        )

    e = np.real(real_values) + 1j * np.real(imag_values)
    e_sq = np.sum(np.abs(e) ** 2, axis=1)
    return float(sigma) * e_sq / (2.0 * float(rho))


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
