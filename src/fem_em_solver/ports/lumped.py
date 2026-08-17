"""`PORT-9` step 1 — the lumped/circuit-element port boundary condition.

**What this is.**  The port model a birdcage leg gap actually wants: a
two-terminal circuit element smeared over a *port sheet*, rather than the
impressed-current gap drive the `PORT-1` gap-voltage route uses.  It is the
resistive-sheet transition condition of Jin, *The FEM in Electromagnetics*
3rd ed., **§1.5.4 eqs (1.60)–(1.63)**, driven by an impressed sheet source —
i.e. the frequency-domain form of a lumped port.

**Theory, with the citations the §7 entry asks for.**  A resistive sheet is a
thin sheet carrying an electric surface current proportional to the tangential
electric field at its surface (Jin §1.5.4).  Its transition conditions are

    n̂ × (E⁺ − E⁻) = 0                                            Jin (1.60)
    n̂ × (H⁺ − H⁻) = J_s ,      J_s = (1/R) n̂ × (n̂ × E) × n̂      Jin (1.61)–(1.62)

with ``R`` the sheet resistivity **in ohms per square**, so that eliminating
``J_s`` gives the single transition condition Jin (1.63).  The variational
statement of the same sheet — the term it contributes to the E-field
functional — is Jin **§6.5 eqs (6.93)–(6.98)**: splitting the domain at the
sheet and summing the two subdomain functionals of (6.63)/(5.118) adds one
surface integral over ``S_d``, quadratic in the tangential trace.  Taking the
variation of that functional (equivalently: Galerkin on the curl-curl equation,
keeping the ``n̂ × (∇×E)`` boundary term and substituting (1.63) for it) turns
the sheet into the sesquilinear surface term

    a_sheet(E, v) = jωμ₀ (1/R) ∫_S (n̂ × E)·conj(n̂ × v) dS                  (L1)

added to the volume form ``∫ μᵣ⁻¹(∇×E)·(∇×v̄) − k₀² ε_c E·v̄ dV`` this package
already assembles (:meth:`~fem_em_solver.core.time_harmonic.TimeHarmonicSolver.bilinear_form`).
The factor ``jωμ₀`` is the one the curl-curl equation carries in front of every
current density on this convention (``e^{+jωt}``; the volume load is
``−jωμ₀ ∫ J·v̄``), and the sign of (L1) is fixed by requiring the sheet to be
**dissipative**: for ``R > 0`` it must add positive resistance, which it does —
the term contributes ``+|n̂×E|²/R`` to the complex power balance.

**A lumped port** is that sheet plus an impressed source.  The physical element
bridges a gap of height ``h`` (the terminal-to-terminal direction, which lies
**in** the sheet plane — the current crosses the gap *along* the sheet, it does
not pass *through* it) and width ``w``.  A terminal impedance ``Z_p`` therefore
appears as the sheet resistivity

    R = Z_p · (w / h)      [ohms per square]                                (L2)

(the usual "number of squares" scaling: ``h/w`` squares in series across the
sheet).  Driving it with a terminal voltage ``V_src`` means an impressed sheet
current density ``K_imp = (V_src / (R h)) ĥ``, and the load term is

    L_sheet(v) = −jωμ₀ ∫_S K_imp·conj(v) dS                                 (L3)

so that with the field switched off the sheet delivers exactly ``V_src / Z_p``
of terminal current: ``∫ K_imp · ŵ dw = V_src w / (R h) = V_src / Z_p`` by (L2).

**Scope — read this before using it.**  Nothing here is validated.  This module
is `PORT-9` **step 1**, a measurement-only formulation step: it assembles the
forms and pins them against exact assembly identities on a trivial geometry
(``tests/validation/test_port_lumped_bc.py``).  It has *not* been compared
against the gated gap-voltage route on the two-torus fixture — that is step 2's
cross-route band (10% mutual, 5% cross-route, 1e-3 reciprocity, pre-stated at
scoping and never widened).  Do not read a port impedance out of this module
and quote it.

**Geometry is the caller's.**  As in
:mod:`fem_em_solver.ports.gap_voltage`, the sheet's facet tag, its gap height
and its width come from the caller: they are properties of a fixture, and
inventing them inside the package is how ``excitation.py`` became a heuristic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import ufl
from mpi4py import MPI

import dolfinx
from dolfinx import default_scalar_type, fem

from ..utils.constants import MU_0

__all__ = [
    "LumpedPortSheet",
    "sheet_resistivity_ohm_per_square",
    "lumped_port_bilinear_term",
    "lumped_port_linear_term",
    "sheet_terminal_current",
]


def sheet_resistivity_ohm_per_square(
    port_impedance_ohm: complex, *, gap_height_m: float, sheet_width_m: float
) -> complex:
    """``R = Z_p · w / h`` — Jin §1.5.4's ohms-per-square from a terminal ``Z_p``.

    ``gap_height_m`` is the terminal-to-terminal distance *along* the sheet (the
    direction the port current flows); ``sheet_width_m`` is the transverse
    extent.  ``h/w`` squares sit in series between the terminals, hence (L2).
    """
    if not np.isfinite(gap_height_m) or gap_height_m <= 0.0:
        raise ValueError(f"gap_height_m must be finite and positive, got {gap_height_m!r}")
    if not np.isfinite(sheet_width_m) or sheet_width_m <= 0.0:
        raise ValueError(f"sheet_width_m must be finite and positive, got {sheet_width_m!r}")
    z = complex(port_impedance_ohm)
    if z == 0.0:
        raise ValueError("port_impedance_ohm must be non-zero — R = Z_p·w/h is its sheet form")
    return z * (sheet_width_m / gap_height_m)


@dataclass(frozen=True)
class LumpedPortSheet:
    """One lumped port: a resistive sheet with an impressed terminal drive.

    Parameters
    ----------
    port_id
        Must match a :class:`~fem_em_solver.ports.definitions.PortDefinition`.
    facet_tag
        Facet tag of the port sheet ``S``.  The sheet spans terminal to terminal
        along ``drive_direction``; it is **not** a cross-section of the
        conductor (the port current runs in the sheet plane, not through it).
    port_impedance_ohm
        Terminal impedance ``Z_p`` of the circuit element, converted to a sheet
        resistivity by (L2).  ``50`` for a matched port; a large real value for
        a nearly-open sheet.
    gap_height_m, sheet_width_m
        The sheet's terminal-to-terminal length and its transverse width.
    drive_direction
        Unit vector from the negative to the positive terminal, lying in the
        sheet plane.  The impressed source current density is along it.
    source_voltage_v
        Terminal voltage ``V_src`` of the impressed source.  ``0`` makes the
        sheet a passive termination — which is how every undriven port of an
        N-port sweep is modelled.
    interior
        ``True`` when the tagged facets are interior to the mesh (the usual
        case for a gap sheet; the integrand is continuous across them because
        ``n̂ × E`` is, Jin (1.60), so the ``'+'`` restriction is well defined).
        ``False`` for an exterior boundary sheet.
    """

    port_id: str
    facet_tag: int
    port_impedance_ohm: complex
    gap_height_m: float
    sheet_width_m: float
    drive_direction: tuple[float, float, float] = (0.0, 1.0, 0.0)
    source_voltage_v: complex = 0.0 + 0.0j
    interior: bool = True

    def validate(self) -> None:
        if not self.port_id or not self.port_id.strip():
            raise ValueError("port_id must be a non-empty string")
        sheet_resistivity_ohm_per_square(
            self.port_impedance_ohm,
            gap_height_m=self.gap_height_m,
            sheet_width_m=self.sheet_width_m,
        )
        if float(np.linalg.norm(np.asarray(self.drive_direction, dtype=float))) <= 0.0:
            raise ValueError(f"port '{self.port_id}': drive_direction must be non-zero")

    @property
    def sheet_resistivity(self) -> complex:
        """``R`` in ohms per square, (L2)."""
        return sheet_resistivity_ohm_per_square(
            self.port_impedance_ohm,
            gap_height_m=self.gap_height_m,
            sheet_width_m=self.sheet_width_m,
        )

    def unit_drive(self) -> np.ndarray:
        d = np.asarray(self.drive_direction, dtype=float)
        return d / float(np.linalg.norm(d))


def _sheet_measure(mesh, facet_tags, sheet: LumpedPortSheet):
    """``dS`` for an interior sheet, ``ds`` for an exterior one."""
    if facet_tags is None:
        raise ValueError(
            f"port '{sheet.port_id}': the lumped-port sheet needs facet tags to find tag "
            f"{sheet.facet_tag}"
        )
    kind = "dS" if sheet.interior else "ds"
    return ufl.Measure(
        kind,
        domain=mesh,
        subdomain_data=facet_tags,
        subdomain_id=(int(sheet.facet_tag),),
    )


def _restrict(build, sheet: LumpedPortSheet):
    """Build an integrand under the right restriction.

    ``build`` takes a restriction function and applies it to every facet-valued
    argument.  Interior facets need one (UFL cannot know the trace is
    single-valued); exterior facets must not carry one.  ``n̂ × E`` *is*
    single-valued across the sheet — Jin (1.60) — so the ``'+'`` side is the
    trace, not an arbitrary choice.
    """
    if sheet.interior:
        return build(lambda f: f("+"))
    return build(lambda f: f)


def lumped_port_bilinear_term(
    mesh: dolfinx.mesh.Mesh,
    facet_tags: Optional[dolfinx.mesh.MeshTags],
    sheet: LumpedPortSheet,
    trial,
    test,
    *,
    omega_rad_per_s: float,
):
    """The sesquilinear sheet term (L1), ready to add to the volume form.

    ``jωμ₀ (1/R) ∫_S (n̂×E)·conj(n̂×v) dS`` — Jin §1.5.4 (1.63) in the
    variational form of §6.5 (6.95)/(6.98).  ``ufl.inner`` conjugates its second
    argument, which is what makes the term sesquilinear on the ``e^{+jωt}``
    convention this solver uses; ``ufl.dot`` here would silently flip it.
    """
    sheet.validate()
    ds_sheet = _sheet_measure(mesh, facet_tags, sheet)
    n = ufl.FacetNormal(mesh)
    factor = fem.Constant(
        mesh, default_scalar_type(1j * omega_rad_per_s * MU_0 / sheet.sheet_resistivity)
    )
    u_t = _restrict(lambda r: ufl.cross(r(n), r(trial)), sheet)
    v_t = _restrict(lambda r: ufl.cross(r(n), r(test)), sheet)
    return factor * ufl.inner(u_t, v_t) * ds_sheet


def lumped_port_linear_term(
    mesh: dolfinx.mesh.Mesh,
    facet_tags: Optional[dolfinx.mesh.MeshTags],
    sheet: LumpedPortSheet,
    test,
    *,
    omega_rad_per_s: float,
):
    """The impressed-source load term (L3).

    ``−jωμ₀ ∫_S K_imp·conj(v) dS`` with ``K_imp = V_src/(R h) ĥ`` — the same
    ``−jωμ₀`` prefactor the volume current load carries, so a sheet source and a
    volume source enter the right-hand side on one convention.
    """
    sheet.validate()
    ds_sheet = _sheet_measure(mesh, facet_tags, sheet)
    unit = sheet.unit_drive()
    magnitude = complex(sheet.source_voltage_v) / (sheet.sheet_resistivity * sheet.gap_height_m)
    k_imp = fem.Constant(
        mesh,
        np.array([default_scalar_type(magnitude * c) for c in unit], dtype=default_scalar_type),
    )
    factor = fem.Constant(mesh, default_scalar_type(-1j * omega_rad_per_s * MU_0))
    v = _restrict(lambda r: r(test), sheet)
    return factor * ufl.inner(k_imp, v) * ds_sheet


def sheet_terminal_current(
    mesh: dolfinx.mesh.Mesh,
    facet_tags: Optional[dolfinx.mesh.MeshTags],
    sheet: LumpedPortSheet,
    e_field,
    comm: MPI.Comm,
) -> complex:
    """Terminal current the sheet carries: ``I = (1/R) ∫_S (E + E_src)·ĥ dS / h``.

    The sheet's own constitutive law read back off the solved field.  ``J_s`` is
    a surface current density [A/m]; integrating its ``ĥ`` component over the
    sheet gives ``A/m · m²`` and dividing by the terminal separation ``h``
    recovers amperes — the standard reduction of a distributed sheet to a
    two-terminal element.

    ``assemble_scalar`` is rank-local; the reduction is done here so no caller
    can read an unreduced number.
    """
    sheet.validate()
    ds_sheet = _sheet_measure(mesh, facet_tags, sheet)
    unit = sheet.unit_drive()
    h_hat = ufl.as_vector([default_scalar_type(c) for c in unit])
    e_src = complex(sheet.source_voltage_v) / sheet.gap_height_m
    e_restricted = _restrict(lambda r: r(e_field), sheet)
    integrand = (ufl.inner(e_restricted, h_hat) + default_scalar_type(e_src)) / sheet.sheet_resistivity
    local = fem.assemble_scalar(fem.form(integrand * ds_sheet))
    return complex(comm.allreduce(local, op=MPI.SUM)) / sheet.gap_height_m
