"""The gap-voltage port route, in ``src/``: solved field -> per-port V and I.

`PORT-1` step 4.  Everything here was validated inside
``tests/validation/test_port_gap_voltage_impedance.py`` (steps 3b-i ... 3b-xviii)
and demonstrated by ``examples/ports/01_two_torus_port_pair.py``; this module is
that route lifted into the package so
:func:`fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep` can read its
port quantities off the **solved field** instead of ``excitation.py``'s coupling
heuristic (`PORT-0`, known-issues 3).

The route, per driven port ``k``:

  * one solve with an impressed current density across port ``k``'s gap volume,
    ``J = I_drive / A_gap`` along the port's drive direction, ``project_source``
    off (the impressed density is deliberately not solenoidal — it terminates on
    the gap's end faces where the conduction current takes over);
  * ``I_k = (sigma / L_k) \\int_{conductor k} E . that dV`` on the **meshed**
    conductor length, so a mesh that lost part of the conductor shows up in the
    current rather than being papered over by analytic geometry;
  * ``V_i = -\\int E . that dl`` along port ``i``'s supplied quadrature, terminal
    to terminal, through
    :func:`~fem_em_solver.post.evaluation.evaluate_vector_field_parallel`
    (collective; never ``f.eval``).

**What this module does not own.**  The geometry.  Path quadrature, conductor
direction, conductor length and gap length come from the caller in
:class:`GapVoltagePortSpec`, because they are properties of a fixture and not of
the route — and because inventing them inside the package is exactly how
``excitation.py`` became a heuristic.  Nothing here is birdcage-specific or
two-torus-specific; the two-torus fixture is simply the only geometry on which
the route has been gated (`PORT-1` step 3b-xviii, raw ``0.894283 x omega*M12``,
corrected ``0.939581`` inside the unmoved 10% band).

**Systematics are not applied here.**  The ladder lives in
:mod:`fem_em_solver.ports.systematics` and its two corrections are specific to
the two-torus fixture at ``air_padding = 0.08``; a route that silently applied
them to another geometry would be a fitted knob.  Callers apply the ladder to
the ``Z`` this route returns, and print the raw rung first.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from ..core import TimeHarmonicProblem, TimeHarmonicSolver
from ..core.solvers import DEFAULT_GAUGE_PENALTY
from ..post.evaluation import evaluate_vector_field_parallel
from .definitions import PortDefinition
from .excitation import (
    PortSolveContext,
    PortVoltageCurrentEstimate,
    SinglePortExcitationResult,
)

__all__ = [
    "GapVoltagePortSpec",
    "run_gap_voltage_port_case",
]


@dataclass(frozen=True)
class GapVoltagePortSpec:
    """The fixture geometry one gap-voltage port needs.

    Parameters
    ----------
    port_id
        Must match a :class:`~fem_em_solver.ports.definitions.PortDefinition`.
    gap_cell_tag
        Cell tag of the gap (source) volume the impressed density lives on.
    gap_length_m
        Length of that gap volume along ``drive_direction``; the drive
        cross-section is taken as ``meshed gap volume / gap_length_m`` so the
        prescribed current is the one the *mesh* carries.
    conductor_cell_tag, conductor_length_m, conductor_sigma_s_per_m
        The conductor whose conduction current is this port's ``I``.
        ``conductor_length_m`` may be ``None``, in which case the meshed
        conductor volume divided by ``conductor_cross_section_m2`` is used.
    conductor_direction
        ``x -> ufl vector`` unit direction the conduction current is projected
        on (for a loop, the azimuthal unit vector).
    path_points, path_tangents, path_weights
        The terminal-to-terminal quadrature for ``V = -\\int E . that dl``:
        ``(n, 3)`` points, ``(n, 3)`` unit tangents, ``(n,)`` weights **already
        carrying the arc-length factor**, so ``V = -sum(w_i (E . that)_i)``.
        Identical on every rank (the evaluation is collective).
    drive_direction
        Unit direction of the impressed current density across the gap.
    drive_current_a
        Prescribed terminal current for the driven solve.
    """

    port_id: str
    gap_cell_tag: int
    gap_length_m: float
    conductor_cell_tag: int
    conductor_sigma_s_per_m: float
    conductor_direction: Callable
    path_points: np.ndarray
    path_tangents: np.ndarray
    path_weights: np.ndarray
    conductor_length_m: Optional[float] = None
    conductor_cross_section_m2: Optional[float] = None
    drive_direction: tuple[float, float, float] = (0.0, 1.0, 0.0)
    drive_current_a: float = 1.0

    def validate(self) -> None:
        if not self.port_id or not self.port_id.strip():
            raise ValueError("port_id must be a non-empty string")
        if self.gap_length_m <= 0.0:
            raise ValueError(f"port '{self.port_id}': gap_length_m must be positive")
        if self.conductor_sigma_s_per_m <= 0.0:
            raise ValueError(
                f"port '{self.port_id}': conductor_sigma_s_per_m must be positive "
                "— the port current is a conduction current"
            )
        if self.conductor_length_m is None and self.conductor_cross_section_m2 is None:
            raise ValueError(
                f"port '{self.port_id}': give conductor_length_m or "
                "conductor_cross_section_m2 (the meshed length comes from the latter)"
            )
        points = np.asarray(self.path_points, dtype=float)
        tangents = np.asarray(self.path_tangents, dtype=float)
        weights = np.asarray(self.path_weights, dtype=float)
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError(f"port '{self.port_id}': path_points must be (n, 3)")
        if tangents.shape != points.shape:
            raise ValueError(
                f"port '{self.port_id}': path_tangents must match path_points"
            )
        if weights.shape != (points.shape[0],):
            raise ValueError(
                f"port '{self.port_id}': path_weights must be (n,) for (n, 3) points"
            )


def _reduce(form, comm) -> complex:
    """``assemble_scalar`` is rank-local — reduce before anyone reads it."""
    return complex(comm.allreduce(fem.assemble_scalar(fem.form(form)), op=MPI.SUM))


def _tag_measure(msh, cell_tags, tag):
    return ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(int(tag),))


def _tag_volume(msh, cell_tags, tag, comm) -> float:
    one = fem.Constant(msh, default_scalar_type(1.0))
    return float(np.real(_reduce(one * _tag_measure(msh, cell_tags, tag), comm)))


def _path_voltage(e_field, spec: GapVoltagePortSpec, comm) -> complex:
    """``V = -\\int E . that dl`` on the spec's quadrature (collective)."""
    points = np.asarray(spec.path_points, dtype=float)
    tangents = np.asarray(spec.path_tangents, dtype=float)
    weights = np.asarray(spec.path_weights, dtype=float)
    values, valid = evaluate_vector_field_parallel(e_field, points, comm)
    if not bool(np.all(valid)):
        raise RuntimeError(
            f"port '{spec.port_id}': {int((~valid).sum())} of {points.shape[0]} path "
            "quadrature points located in no cell — the integration path left the mesh"
        )
    e_tangential = np.einsum("ij,ij->i", values, tangents)
    return complex(-np.sum(weights * e_tangential))


def _impressed_gap_drive(direction: tuple[float, float, float], magnitude: float):
    """Uniform impressed current density across a gap volume."""
    unit = np.asarray(direction, dtype=float)
    norm = float(np.linalg.norm(unit))
    if norm <= 0.0:
        raise ValueError("drive_direction must be non-zero")
    unit = unit / norm

    def current_density(x):
        return ufl.as_vector([float(magnitude * c) for c in unit])

    return current_density


def run_gap_voltage_port_case(
    problem: TimeHarmonicProblem,
    ports: Sequence[PortDefinition],
    specs: Sequence[GapVoltagePortSpec],
    *,
    driven_port_id: str,
    gauge_penalty: float = DEFAULT_GAUGE_PENALTY,
    degree: int = 1,
    verbose: bool = True,
) -> SinglePortExcitationResult:
    """One impressed-gap solve; per-port ``V`` and ``I`` off the solved field.

    Returns the same container the heuristic returns, with
    ``is_placeholder=False`` — the flag that lets a caller tell a solved-field
    result from a fabricated one, and that gates Touchstone export.
    """
    if problem.cell_tags is None:
        raise ValueError("the gap-voltage route needs problem.cell_tags to find the gap volume")

    spec_by_id = {spec.port_id: spec for spec in specs}
    for spec in specs:
        spec.validate()
    port_ids = [port.port_id for port in ports]
    missing = [pid for pid in port_ids if pid not in spec_by_id]
    if missing:
        raise ValueError(f"missing GapVoltagePortSpec for ports: {missing}")
    if driven_port_id not in port_ids:
        raise ValueError(f"driven_port_id '{driven_port_id}' not found in ports")

    msh = problem.mesh
    comm = msh.comm
    cell_tags = problem.cell_tags
    driven_index = port_ids.index(driven_port_id)
    driven_spec = spec_by_id[driven_port_id]

    # The drive cross-section from the *meshed* gap volume, not from nominal
    # geometry: this is what makes the prescribed current the mesh's current.
    gap_volume = _tag_volume(msh, cell_tags, driven_spec.gap_cell_tag, comm)
    if gap_volume <= 0.0:
        raise ValueError(
            f"port '{driven_port_id}': gap cell tag {driven_spec.gap_cell_tag} has "
            "zero meshed volume globally"
        )
    gap_area = gap_volume / driven_spec.gap_length_m

    solver = TimeHarmonicSolver(problem, degree=degree)
    fields = solver.solve(
        current_density=_impressed_gap_drive(
            driven_spec.drive_direction, driven_spec.drive_current_a / gap_area
        ),
        subdomain_ids=[int(driven_spec.gap_cell_tag)],
        gauge_penalty=gauge_penalty,
        project_source=False,
    )

    e = fields.e_complex
    x_ufl = ufl.SpatialCoordinate(msh)

    responses: dict[str, PortVoltageCurrentEstimate] = {}
    solve_context: dict[str, PortSolveContext] = {}
    for idx, port in enumerate(ports):
        spec = spec_by_id[port.port_id]
        conductor_volume = _tag_volume(msh, cell_tags, spec.conductor_cell_tag, comm)
        if spec.conductor_length_m is not None:
            length = float(spec.conductor_length_m)
        else:
            length = conductor_volume / float(spec.conductor_cross_section_m2)
        if length <= 0.0:
            raise ValueError(f"port '{port.port_id}': non-positive conductor length")

        current = (
            spec.conductor_sigma_s_per_m
            * _reduce(
                ufl.inner(e, spec.conductor_direction(x_ufl))
                * _tag_measure(msh, cell_tags, spec.conductor_cell_tag),
                comm,
            )
            / length
        )
        voltage = _path_voltage(e, spec, comm)

        is_driven = port.port_id == driven_port_id
        responses[port.port_id] = PortVoltageCurrentEstimate(
            port_id=port.port_id,
            voltage_v=voltage,
            current_a=current,
            is_driven=is_driven,
            termination_ohm=float(port.z0_ohm),
        )
        solve_context[port.port_id] = PortSolveContext(
            port_id=port.port_id,
            port_index=idx,
            driven_port_id=driven_port_id,
            driven_port_index=driven_index,
            is_driven=is_driven,
            wrapped_ring_distance=abs(idx - driven_index),
            # No coupling model exists on this route: the field is the coupling.
            coupling_factor=float("nan"),
            termination_ohm=float(port.z0_ohm),
        )

    if verbose and comm.rank == 0:
        print(
            f"[gap-voltage] driven port '{driven_port_id}' (gap tag "
            f"{driven_spec.gap_cell_tag}, meshed area {gap_area:.6e} m^2, "
            f"J = {driven_spec.drive_current_a / gap_area:.6e} A/m^2):"
        )
        for port in ports:
            r = responses[port.port_id]
            print(
                f"    {r.port_id}: V = {r.voltage_v.real:+.9e}{r.voltage_v.imag:+.9e}j V, "
                f"I = {r.current_a.real:+.9e}{r.current_a.imag:+.9e}j A "
                f"({'driven' if r.is_driven else 'undriven'})"
            )

    return SinglePortExcitationResult(
        driven_port_id=driven_port_id,
        frequency_hz=problem.frequency_hz,
        responses=responses,
        solve_context=solve_context,
        is_placeholder=False,
    )
