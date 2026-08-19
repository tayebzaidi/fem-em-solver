"""`POST-3`: Poynting power balance — a consistency identity that can fail.

The metric this replaces (``e_to_b_mean_ratio``, :mod:`.consistency`) is by
construction ``≈ ω|A|/|∇×A|``: it reports a mesh length scale and stays happy
whatever the solver does.  Complex Poynting on the *solved* field does not.

For ``e^{+jωt}`` phasors Faraday's law is ``∇×E = −jωμH``, so

    H = ∇×E / (−j ω μ₀ μᵣ)

and the complex Poynting vector is ``S = ½ E × H̄``.  Integrating
``∇·S = −½σ|E|² − 2jω(w_m − w_e)`` over the domain and taking the **real**
part leaves a statement with no free parameters:

    −∮ ½ Re(E × H̄)·n̂ dS  =  ½ ∫ σ(x)|E|² dV

i.e. the real power entering through the boundary equals the Ohmic power
dissipated inside it.  The imaginary part carries the reactive
(stored-energy) imbalance and is reported but not asserted on.

**That two-term statement is the *source-free* identity** (`POST-5` step 4,
2026-08-19).  With an impressed current ``J`` inside the domain Ampère's law
carries the extra term and ``∇·S = −½σ|E|² − ½E·J̄ − 2jω(w_m − w_e)``, so the
real part integrates to

    −∮ ½ Re(E × H̄)·n̂ dS  =  ½ ∫ σ(x)|E|² dV  +  ½ Re ∫ E·J̄ dV

Scoring a *driven* domain against the two-term form is scoring the wrong
identity: on the time-harmonic smoke fixture the omitted source term is the
whole of an O(100%) "imbalance" (`POST-5` step 3 — 116.7465% → 16.7465% on the
axial drive, 105.9632% → 5.9632% on the azimuthal one, the remainder being the
curl trace's discretisation error at ~9 cells per wavelength).  Pass
``current_density`` (and the measure the solver assembled it on) and the
returned ``relative_imbalance`` scores the three-term statement; omit it and
nothing changes, which is the right call for a source-free domain, where the
two-term form is the stronger check.  The two-term readings stay computable
either way as ``two_term_relative_imbalance`` / ``two_term_power_scale_w``,
so the `POST-5` step-1 h-ladder journal keeps reconciling.

Nothing in the derivation needs σ to be uniform — the divergence theorem is
applied to the whole domain, and a piecewise σ only changes the integrand of
the volume leg (`POST-3` step 2).  ``sigma`` therefore accepts either a scalar
or the DG0 ``sigma_field`` the solver already builds, which is what makes the
identity usable on a coil+phantom solve.

Both sides are computed from the same discrete ``E``, but by different
operators — a volume mass term against a boundary curl trace — so the identity
is a genuine check on the discrete solution rather than an algebraic tautology.
Dropping ``Im ε_c``, conjugating the time convention, or losing the ``σ`` mass
term breaks it.

``fem.assemble_scalar`` is rank-local; every integral here is reduced across
``comm`` before it is combined with another.
"""

from __future__ import annotations

from typing import Optional, Union

import dolfinx
import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import fem

from ..utils.constants import MU_0


def poynting_power_balance(
    e_complex: fem.Function,
    *,
    omega: float,
    sigma: Union[float, fem.Function],
    mu_r: Union[float, fem.Function] = 1.0,
    current_density: Optional[object] = None,
    source_measure: Optional[ufl.Measure] = None,
    comm: Optional[MPI.Comm] = None,
) -> dict[str, float]:
    """Real-power balance for a time-harmonic solve.

    Parameters
    ----------
    e_complex:
        The solved complex ``E`` phasor (N1curl), as produced by
        :class:`~fem_em_solver.core.TimeHarmonicSolver`.
    omega:
        Angular frequency in rad/s.
    sigma:
        Conductivity in S/m: either a uniform scalar, or a
        :class:`dolfinx.fem.Function` giving σ(x) cell-wise — pass the
        ``sigma_field`` the solver returns in
        :class:`~fem_em_solver.core.TimeHarmonicFields` and the volume term
        becomes ``½∫σ(x)|E|²dV`` over the actual material distribution.  The
        field must live on the same mesh as ``e_complex``; the identity is
        scored against whatever σ is handed in, which is what makes the
        σ-blind negative control possible.
    mu_r:
        Relative permeability: a uniform scalar, or the DG0 ``mu_r_field`` the
        solver built (`POST-3` step 5).  A piecewise μᵣ enters ``H`` inside the
        boundary integral as well as the curl-curl operator, and scoring a
        two-μᵣ solve with a scalar here is exactly the vacuous version of this
        identity — so the field path exists on both sides.  DG0 is
        single-valued on exterior facets, so the boundary trace of ``μᵣ`` is
        well-defined; the identity is scored against whatever μᵣ is handed in,
        which is what makes the μᵣ-blind negative control possible.
    current_density:
        The impressed current-density phasor ``J`` (any UFL-valid vector
        expression, including the ``fem.Function`` or ``ufl.as_vector`` a
        caller handed the solver), or ``None`` for a source-free domain.  When
        given, ``½Re∫E·J̄dV`` is assembled over ``source_measure`` and the
        scored identity becomes the three-term one.  ``None`` is not the same
        as zero only in bookkeeping: both give ``source_power_w = 0.0``, but
        ``None`` skips the assembly entirely.
    source_measure:
        The cell measure ``J`` was assembled on — pass exactly the one the
        solver used, e.g.
        ``ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)(1)`` for a
        drive restricted to a tagged conductor.  Defaults to ``ufl.dx`` over
        the whole mesh, which is right only when ``J`` is defined (and zero)
        everywhere.  Ignored when ``current_density`` is ``None``.
    comm:
        Communicator to reduce over; defaults to the mesh's own.

    Returns
    -------
    dict with ``dissipated_power_w`` (``½∫σ|E|²dV``), ``net_inward_power_w``
    (``−∮½Re(E×H̄)·n̂dS``), ``source_power_w`` (``½Re∫E·J̄dV``, exactly ``0.0``
    when no ``current_density`` is given), ``reactive_inward_power_var`` (the
    imaginary part of the flux, reported only), ``power_scale_w`` (the largest
    magnitude among the terms of the *scored* identity) and
    ``relative_imbalance`` (its residual over that scale).  The source-free
    readings are always reported alongside as ``two_term_power_scale_w`` and
    ``two_term_relative_imbalance``; with no ``current_density`` they are equal
    to the scored pair by construction, so a caller that never passes ``J``
    sees the pre-`POST-5`-step-4 dict plus two aliases and a zero.
    """
    msh = e_complex.function_space.mesh
    if comm is None:
        comm = msh.comm

    if isinstance(sigma, fem.Function):
        if sigma.function_space.mesh is not msh:
            raise ValueError(
                "sigma field and e_complex must live on the same mesh; got "
                "functions from two different meshes, which would silently "
                "integrate one material distribution against another field"
            )
        sigma_ufl: object = sigma
    else:
        sigma_value = float(sigma)
        if not np.isfinite(sigma_value) or sigma_value < 0.0:
            raise ValueError(
                f"sigma must be finite and non-negative (S/m), got {sigma!r}"
            )
        # Wrapped in a Constant rather than left as a Python float: at the
        # documented sigma = 0.0 negative control, `0.5 * 0.0 * inner(E, E)`
        # constant-folds to a domain-less UFL zero and `* ufl.dx` then raises
        # "This integral is missing an integration domain" (known-issues
        # 2026-08-17, `OPS-17` step-2 defect 4).  A Constant carries the mesh,
        # so the zero integral survives as an integral and assembles to 0.0.
        sigma_ufl = fem.Constant(msh, dolfinx.default_scalar_type(sigma_value))

    if isinstance(mu_r, fem.Function):
        if mu_r.function_space.mesh is not msh:
            raise ValueError(
                "mu_r field and e_complex must live on the same mesh; got "
                "functions from two different meshes, which would silently "
                "score one material distribution against another field"
            )
        mu_r_ufl: object = mu_r
    else:
        mu_r_ufl = float(mu_r)
        if not np.isfinite(mu_r_ufl) or mu_r_ufl <= 0.0:
            raise ValueError(
                f"mu_r must be finite and positive, got {mu_r!r}"
            )

    normal = ufl.FacetNormal(msh)
    h_field = ufl.curl(e_complex) / (-1j * omega * MU_0 * mu_r_ufl)

    # ufl.inner conjugates its second argument, so inner(E, E) is |E|² already.
    # σ is real, so the product's imaginary part is round-off and Re() below is
    # exact rather than a truncation — true for the DG0 field path too.
    dissipated_form = fem.form(
        0.5 * sigma_ufl * ufl.inner(e_complex, e_complex) * ufl.dx
    )
    # Outward complex Poynting flux.  Written with an explicit conj() rather
    # than inner() so the cross product keeps the ½E×H̄ ordering of the theorem;
    # ufl.dot against the outward FacetNormal then gives the *outgoing* power.
    outward_form = fem.form(
        0.5 * ufl.dot(ufl.cross(e_complex, ufl.conj(h_field)), normal) * ufl.ds
    )

    dissipated_c = comm.allreduce(fem.assemble_scalar(dissipated_form), op=MPI.SUM)
    outward_c = comm.allreduce(fem.assemble_scalar(outward_form), op=MPI.SUM)

    dissipated = float(np.real(dissipated_c))
    net_inward = -float(np.real(outward_c))
    reactive_inward = -float(np.imag(outward_c))

    source = 0.0
    if current_density is not None:
        dx_src = (
            ufl.Measure("dx", domain=msh) if source_measure is None else source_measure
        )
        if dx_src.integral_type() != "cell":
            raise ValueError(
                "source_measure must be a cell measure (dx); got integral type "
                f"{dx_src.integral_type()!r}. The impressed-source term is a "
                "volume integral over the region J was assembled on"
            )
        # ufl.inner conjugates its second argument, which is exactly the E·J̄ of
        # the theorem.  A caller passing a literal zero vector would fold this
        # to a domain-less UFL zero, and `* dx` then raises the same way the
        # scalar σ = 0 branch above once did — so short-circuit instead, which
        # also makes the J = 0 negative control assemble-free and exactly 0.0.
        integrand = 0.5 * ufl.inner(e_complex, current_density)
        if not isinstance(integrand, ufl.constantvalue.Zero):
            source_c = comm.allreduce(
                fem.assemble_scalar(fem.form(integrand * dx_src)), op=MPI.SUM
            )
            source = float(np.real(source_c))

    # The two-term (source-free) reading is always reported: it is the stronger
    # check where it applies, and the `POST-5` step-1 h-ladder journal is
    # recorded in it.  `power_scale_w` therefore never silently changes meaning
    # — it is the scale of whichever identity was actually scored, and the
    # source-free scale keeps its own name.
    two_term_scale = max(abs(dissipated), abs(net_inward))
    two_term_imbalance = (
        abs(net_inward - dissipated) / two_term_scale
        if two_term_scale > 0.0
        else float("inf")
    )

    if current_density is None:
        scale = two_term_scale
        relative_imbalance = two_term_imbalance
    else:
        scale = max(abs(dissipated), abs(net_inward), abs(source))
        relative_imbalance = (
            abs(net_inward - (dissipated + source)) / scale
            if scale > 0.0
            else float("inf")
        )

    return {
        "dissipated_power_w": dissipated,
        "net_inward_power_w": net_inward,
        "source_power_w": float(source),
        "reactive_inward_power_var": reactive_inward,
        "power_scale_w": float(scale),
        "relative_imbalance": float(relative_imbalance),
        "two_term_power_scale_w": float(two_term_scale),
        "two_term_relative_imbalance": float(two_term_imbalance),
    }
