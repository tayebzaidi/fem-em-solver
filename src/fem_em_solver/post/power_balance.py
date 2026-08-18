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
    comm:
        Communicator to reduce over; defaults to the mesh's own.

    Returns
    -------
    dict with ``dissipated_power_w`` (``½∫σ|E|²dV``), ``net_inward_power_w``
    (``−∮½Re(E×H̄)·n̂dS``), ``reactive_inward_power_var`` (the imaginary part of
    the same flux, reported only), ``power_scale_w`` (the larger magnitude of
    the two real quantities) and ``relative_imbalance`` (their difference over
    that scale).
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

    scale = max(abs(dissipated), abs(net_inward))
    relative_imbalance = (
        abs(net_inward - dissipated) / scale if scale > 0.0 else float("inf")
    )

    return {
        "dissipated_power_w": dissipated,
        "net_inward_power_w": net_inward,
        "reactive_inward_power_var": reactive_inward,
        "power_scale_w": float(scale),
        "relative_imbalance": float(relative_imbalance),
    }
