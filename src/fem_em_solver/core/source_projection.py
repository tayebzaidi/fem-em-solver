"""Solenoidal projection of a prescribed current density (`PORT-1` step 2f).

The load vector of the N1curl curl-curl system sees the source only through
``∫J·v̄`` for ``v`` in N1curl, and every gradient ``∇q`` of an interior CG1
function ``q`` is such a ``v``.  A prescribed ``J`` that is divergence-free as
a continuum field is generally **not** divergence-free against that discrete
pairing: the two-torus port fixture measured ``‖P_G J‖²/‖J‖² = 8.175e-06``
(`PORT-1` step 2d), and that residue alone accounted for the whole of the
fixture's spurious electric energy — ``‖P_G J‖²/(ωε₀I²) = 4.852262e+01 Ω``
against a measured ``4ωW_e/I² = 4.852271e+01 Ω``, ratio 0.999998 — which is
what drove ``Im Z₁₁`` to ``−41.09 Ω`` on a lossless loop that must be
inductive.

The fix, measured in `PORT-1` step 2e and moved here from the test that
measured it, is to drive with the gradient content removed:

.. math::

    J' = J - ∇ψ,  \\qquad ∫∇ψ·∇q = ∫J·∇q \\;\\; ∀\\, q ∈ CG1 ∩ H¹₀ .

``ψ`` is pinned to zero on the exterior facets because the PEC wall pins the
potential, which is the space in which ``∇q`` is an admissible N1curl test
function.  ``J'`` is then divergence-free *weakly against CG1* — not
pointwise, and pointwise is not what the load vector integrates.

`TH-13` step 3a (2026-08-31) makes both of those choices explicit rather than
hard-coded, because step 2 measured what they cost when the solve does not
match them.  The defaults are unchanged — ``degree=1``, ``pin_exterior=True``
— but a degree-2 N1curl solve tests ``∇Lagrange₂``, and a PMC (``NATURAL``)
box admits every ``q ∈ Lagrange``, not only ``q ∈ H¹₀``.  Against those spaces
the CG1 ∩ H¹₀ projection leaves a residue, and step 2 showed the residue is
not benign: the discrete gradient equation pins ``P_∇ E_h = c·P_∇ J'`` exactly
(residuals 2.970e-12 … 3.697e-13), so whatever gradient content survives the
projection reappears in ``E_h`` divided by ``σ + jωε`` and carried 99.98% of
the loop fixture's degree-1 ``W_e`` and 99.9997% of its degree-2 ``W_e``.
Passing ``degree`` = the solve's and ``pin_exterior`` = whether the solve
actually applies PEC removes it.

Two consequences the caller inherits:

* ``J'`` has support on the whole mesh even when ``J`` is confined to a tagged
  subdomain, because ``∇ψ`` does.  The tag restriction therefore has to move
  into the integrand as a DG0 indicator (exact, cellwise, for a cell tag) and
  the load must then be assembled on ``ufl.dx``.  Both are done here.
* ``ψ`` is real to round-off (its right-hand side is real) but lives in the
  complex CG1 space of a complex build.  The imaginary part is discarded
  explicitly so that ``∇ψ`` is exactly real and ``ufl.inner``'s conjugation of
  ``J'`` stays the no-op it already is for ``J``; the discarded magnitude is
  reported in :class:`GradientProjection` rather than assumed (measured
  0.000e+00 relative in step 2e).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
import ufl
import dolfinx
from dolfinx import fem
from dolfinx.fem.petsc import LinearProblem
from mpi4py import MPI
from petsc4py import PETSc


@dataclass
class GradientProjection:
    """Result of :func:`remove_gradient_content`.

    Attributes
    ----------
    current:
        The projected source ``J' = χJ − ∇ψ`` as a UFL expression, to be
        integrated over the **whole** domain (``ufl.dx``).
    potential:
        The Lagrange potential ``ψ`` (degree 1 unless the caller asked for
        another), kept alive because ``current`` refers to it.
    indicator:
        The DG0 subdomain indicator ``χ``, or ``None`` when the source was
        already whole-domain.  Also kept alive for the same reason.
    imag_ratio:
        ``max|Im ψ| / max|Re ψ|`` before the imaginary part was discarded — a
        diagnostic, not a gate.  Round-off (0.000e+00 measured, step 2e).
    """

    current: object
    potential: fem.Function
    indicator: Optional[fem.Function]
    imag_ratio: float


def remove_gradient_content(
    mesh,
    current,
    *,
    cell_tags=None,
    subdomain_ids: Optional[Sequence[int]] = None,
    degree: int = 1,
    pin_exterior: bool = True,
    petsc_options: Optional[dict] = None,
) -> GradientProjection:
    """Return ``J' = χJ − ∇ψ``, the weakly-solenoidal part of ``current``.

    Parameters
    ----------
    mesh:
        The mesh ``current`` is expressed on.
    current:
        A UFL vector expression (already evaluated at
        ``ufl.SpatialCoordinate(mesh)``).
    cell_tags, subdomain_ids:
        The tagged cells the source is confined to.  When ``subdomain_ids`` is
        ``None`` the source is taken to live on the whole domain and no
        indicator is built.
    degree:
        The Lagrange degree of ``ψ``, i.e. of the gradient subspace the residue
        is removed against.  Default 1, which is what every gated record was
        measured on; pass the N1curl solve's own degree to match it
        (`TH-13` step 3a).
    pin_exterior:
        Whether ``ψ`` is pinned to zero on the exterior facets (``H¹₀``).
        Default ``True``, correct when the solve applies PEC.  Pass ``False``
        under a natural/PMC boundary, where every ``q ∈ Lagrange`` has an
        admissible ``∇q``: the Laplacian is then singular on constants, so a
        single dof — the globally lowest-numbered one, pinned on the rank that
        owns it — fixes the additive constant, which leaves ``∇ψ`` untouched.
    petsc_options:
        Overrides for the Poisson solve; defaults to the same direct LU/MUMPS
        settings the curl-curl solve uses.

    Notes
    -----
    ``create_connectivity(tdim-1, tdim)`` before ``exterior_facet_indices`` is
    mandatory — omitting it is what failed the step-2e probe.
    """
    q_space = fem.functionspace(mesh, ("Lagrange", degree))
    q = ufl.TestFunction(q_space)

    indicator = None
    if subdomain_ids is None:
        restricted = current
        rhs = ufl.inner(current, ufl.grad(q)) * ufl.dx
    else:
        if cell_tags is None:
            raise ValueError("subdomain_ids requested but cell_tags is None")
        dg0 = fem.functionspace(mesh, ("DG", 0))
        indicator = fem.Function(dg0, name="source_indicator")
        indicator.x.array[:] = 0.0
        for tag in subdomain_ids:
            indicator.x.array[cell_tags.find(int(tag))] = 1.0
        indicator.x.scatter_forward()
        restricted = indicator * current
        rhs = ufl.inner(current, ufl.grad(q)) * ufl.Measure(
            "dx",
            domain=mesh,
            subdomain_data=cell_tags,
            subdomain_id=tuple(int(tag) for tag in subdomain_ids),
        )

    if pin_exterior:
        tdim = mesh.topology.dim
        mesh.topology.create_connectivity(tdim - 1, tdim)
        facets = dolfinx.mesh.exterior_facet_indices(mesh.topology)
        boundary_dofs = fem.locate_dofs_topological(q_space, tdim - 1, facets)
        zero = fem.Function(q_space)
        zero.x.array[:] = 0.0
        bcs = [fem.dirichletbc(zero, boundary_dofs)]
    else:
        # PMC: nothing pins the potential, so the Laplacian is singular on
        # constants.  Pin the globally lowest-numbered dof — local index 0 on
        # rank 0, dolfinx numbering the owned ranges in rank order — which is
        # rank-safe and fixes only the additive constant.  Lifted from the
        # `TH-13` step-2 projection helper that measured the identity.
        pin = (
            np.array([0], dtype=np.int32)
            if mesh.comm.rank == 0
            else np.zeros(0, dtype=np.int32)
        )
        bcs = [fem.dirichletbc(PETSc.ScalarType(0), pin, q_space)]

    options = {
        "ksp_type": "preonly",
        "pc_type": "lu",
        "pc_factor_mat_solver_type": "mumps",
    }
    if petsc_options:
        options.update(dict(petsc_options))

    problem = LinearProblem(
        ufl.inner(ufl.grad(ufl.TrialFunction(q_space)), ufl.grad(q)) * ufl.dx,
        rhs,
        bcs=bcs,
        petsc_options=options,
        petsc_options_prefix="fem_em_source_projection_",
    )
    psi = problem.solve()
    psi.x.scatter_forward()

    # max| | is rank-local — reduce before forming the ratio.
    n_owned = q_space.dofmap.index_map.size_local
    local_imag = float(np.max(np.abs(np.imag(psi.x.array[:n_owned])))) if n_owned else 0.0
    local_real = float(np.max(np.abs(np.real(psi.x.array[:n_owned])))) if n_owned else 0.0
    imag_max = mesh.comm.allreduce(local_imag, op=MPI.MAX)
    real_max = mesh.comm.allreduce(local_real, op=MPI.MAX)
    psi.x.array[:] = np.real(psi.x.array)
    psi.x.scatter_forward()

    return GradientProjection(
        current=restricted - ufl.grad(psi),
        potential=psi,
        indicator=indicator,
        imag_ratio=(imag_max / real_max if real_max > 0.0 else 0.0),
    )
