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
from ..utils.constants import EPSILON_0
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

_CURRENT_ROUTES = frozenset({"conduction", "gap_displacement"})


@dataclass(frozen=True)
class GapVoltagePortSpec:
    """The fixture geometry one gap-voltage port needs.

    Parameters
    ----------
    port_id
        Must match a :class:`~fem_em_solver.ports.definitions.PortDefinition`.
    gap_cell_tag
        Cell tag of the gap (source) volume the impressed density lives on.
    gap_cell_tags
        Optional tuple of cell tags whose **summed** meshed volume is the gap
        volume, defaulting to ``(gap_cell_tag,)`` — i.e. today's behaviour for
        every caller that does not set it (`TH-15` step 3).  It exists because
        ``MeshGenerator.two_torus_domain(emit_port_sheet=True)`` fragments each
        gap box at its mid-plane into ``101``/``111`` and ``102``/``112``, so
        ``gap_cell_tag`` alone selects **half** the box on that fixture
        (measured ``V_tag``/box = 0.500000, `TH-15` step 2h,
        ``20260909T110257Z_TH-15-step2h.log:513-519``) and the generator's own
        docstring says a caller taking the gap volume "must take both halves"
        (``io/mesh.py:1179-1182``).  Only the drive cross-section
        ``A_gap = V_gap / gap_length_m`` reads this tuple; the impressed
        density's support and the ``gap_displacement`` current integral still
        live on ``gap_cell_tag`` alone, so the two are deliberately *not*
        equivalent and no default is flipped here.
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
    # `TH-15` step 3.  ``None`` means ``(gap_cell_tag,)``: byte-for-byte the
    # selection every pre-existing caller gets today.
    gap_cell_tags: Optional[tuple[int, ...]] = None
    drive_direction: tuple[float, float, float] = (0.0, 1.0, 0.0)
    drive_current_a: float = 1.0
    # `TH-15` step 2c.  ``"conduction"`` (the default, and the route every
    # pre-existing caller takes) is ``I = sigma/L int_conductor E . that dV``.
    # ``"gap_displacement"`` reads the port current at the gap face instead,
    # by continuity of the total current across it:
    #     ``I_k = [I_drive if driven] + (1/g_k) int_{gap k} (sigma + j w eps)
    #             E . hhat_k dV``
    # with the gap material taken from the problem, ``g_k = gap_length_m`` and
    # ``hhat_k`` the unit ``drive_direction``.  This definition needs no
    # conductor cells, which is why it exists (a PEC conductor solved as a hole
    # has none) — and its error scales with the *port's own* current rather
    # than with the drive.
    current_route: str = "conduction"

    @property
    def gap_volume_tags(self) -> tuple[int, ...]:
        """The cell tags whose summed volume is this port's gap volume."""
        if self.gap_cell_tags is None:
            return (int(self.gap_cell_tag),)
        return tuple(int(tag) for tag in self.gap_cell_tags)

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
        if self.gap_cell_tags is not None and len(tuple(self.gap_cell_tags)) == 0:
            raise ValueError(
                f"port '{self.port_id}': gap_cell_tags must be a non-empty tuple "
                "of cell tags (leave it None for the default (gap_cell_tag,))"
            )
        if self.current_route not in _CURRENT_ROUTES:
            raise ValueError(
                f"port '{self.port_id}': current_route must be one of "
                f"{sorted(_CURRENT_ROUTES)}, got {self.current_route!r}"
            )


def _reduce(form, comm) -> complex:
    """``assemble_scalar`` is rank-local — reduce before anyone reads it."""
    return complex(comm.allreduce(fem.assemble_scalar(fem.form(form)), op=MPI.SUM))


def _as_tag_tuple(tag) -> tuple[int, ...]:
    """``101`` -> ``(101,)``; ``(101, 111)`` -> ``(101, 111)`` (`TH-15` step 3)."""
    if isinstance(tag, (int, np.integer)):
        return (int(tag),)
    tags = tuple(int(t) for t in tag)
    if not tags:
        raise ValueError("a tag selection must name at least one cell tag")
    return tags


def _tag_measure(msh, cell_tags, tag):
    return ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=_as_tag_tuple(tag)
    )


def _tag_volume(msh, cell_tags, tag, comm) -> float:
    """Meshed volume of one cell tag, or the **sum** over a tuple of tags.

    A ``dx`` measure with several subdomain ids integrates over their union, and
    the gap-box halves are disjoint, so the tuple form is exactly the sum
    (`TH-15` step 3).  ``assemble_scalar`` is rank-local — ``_reduce`` fixes it.
    """
    one = fem.Constant(msh, default_scalar_type(1.0))
    return float(np.real(_reduce(one * _tag_measure(msh, cell_tags, tag), comm)))


def _unit(direction) -> np.ndarray:
    vec = np.asarray(direction, dtype=float)
    norm = float(np.linalg.norm(vec))
    if norm <= 0.0:
        raise ValueError("direction must be non-zero")
    return vec / norm


def _tag_material(problem: TimeHarmonicProblem, tag: int):
    """The ``(sigma, epsilon_r)`` the *solve* used on cell tag ``tag``.

    Read off the problem rather than re-declared, so the current this route
    reports cannot silently disagree with the material the field was solved in.
    """
    tag = int(tag)
    if problem.phantom_material is not None and tag == int(problem.phantom_tag):
        raise ValueError(
            f"the gap_displacement route cannot read the gap material on tag {tag}: "
            "it is the phantom tag, whose dispersive material this route does not "
            "unpack — put the port gap on its own tag"
        )
    material = None
    if problem.material_map is not None:
        material = problem.material_map.get(tag)
    if material is None:
        material = problem.material
    return float(material.sigma), float(material.epsilon_r)


def _gap_displacement_current(
    e_field,
    problem: TimeHarmonicProblem,
    spec: GapVoltagePortSpec,
    comm,
) -> tuple[complex, float, float]:
    """``(1/g) int_gap (sigma + j w eps) E . hhat dV`` — the *field* part of ``I``.

    Continuity of the total current across the gap face: whatever conduction
    current the wire carries into the gap leaves it as the sum of the impressed
    drive and the gap's own conduction + displacement current.  The caller adds
    ``drive_current_a`` on the driven port.

    ``hhat`` is the unit ``drive_direction``; ``ufl.inner`` conjugates its
    second argument, which is a no-op here because ``hhat`` is a real constant.
    """
    sigma_gap, epsilon_r_gap = _tag_material(problem, spec.gap_cell_tag)
    omega = 2.0 * np.pi * float(problem.frequency_hz)
    admittivity = complex(sigma_gap + 1j * omega * EPSILON_0 * epsilon_r_gap)

    msh = problem.mesh
    h_hat = ufl.as_vector([float(c) for c in _unit(spec.drive_direction)])
    integral = _reduce(
        ufl.inner(e_field, h_hat) * _tag_measure(msh, problem.cell_tags, spec.gap_cell_tag),
        comm,
    )
    return admittivity * integral / float(spec.gap_length_m), sigma_gap, epsilon_r_gap


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
    # `TH-15` step 3: the selection is `gap_volume_tags`, which is
    # `(gap_cell_tag,)` unless a caller opted into the summed form.
    gap_volume = _tag_volume(msh, cell_tags, driven_spec.gap_volume_tags, comm)
    if gap_volume <= 0.0:
        raise ValueError(
            f"port '{driven_port_id}': gap cell tag(s) "
            f"{driven_spec.gap_volume_tags} have zero meshed volume globally"
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
    gap_material_note: dict[str, tuple[float, float]] = {}
    for idx, port in enumerate(ports):
        spec = spec_by_id[port.port_id]
        is_driven = port.port_id == driven_port_id

        def _conduction_current() -> complex:
            """Today's route, unchanged: ``I = sigma/L int_conductor E . that``."""
            conductor_volume = _tag_volume(msh, cell_tags, spec.conductor_cell_tag, comm)
            if spec.conductor_length_m is not None:
                length = float(spec.conductor_length_m)
            else:
                length = conductor_volume / float(spec.conductor_cross_section_m2)
            if length <= 0.0:
                raise ValueError(f"port '{port.port_id}': non-positive conductor length")
            return (
                spec.conductor_sigma_s_per_m
                * _reduce(
                    ufl.inner(e, spec.conductor_direction(x_ufl))
                    * _tag_measure(msh, cell_tags, spec.conductor_cell_tag),
                    comm,
                )
                / length
            )

        diagnostics: Optional[dict] = None
        if spec.current_route == "conduction":
            current = _conduction_current()
        else:
            field_part, sigma_gap, epsilon_r_gap = _gap_displacement_current(
                e, problem, spec, comm
            )
            gap_material_note[port.port_id] = (sigma_gap, epsilon_r_gap)
            drive_part = complex(spec.drive_current_a) if is_driven else 0.0 + 0.0j
            current = drive_part + field_part
            # The conduction current is the cross-check wherever the conductor
            # is actually meshed; on a PEC hole it is absent by construction.
            diagnostics = {
                "gap_field_part": complex(field_part),
                "drive_part": complex(drive_part),
            }
            if _tag_volume(msh, cell_tags, spec.conductor_cell_tag, comm) > 0.0:
                diagnostics["conduction"] = complex(_conduction_current())
            else:
                diagnostics["conduction"] = None
        voltage = _path_voltage(e, spec, comm)

        responses[port.port_id] = PortVoltageCurrentEstimate(
            port_id=port.port_id,
            voltage_v=voltage,
            current_a=current,
            is_driven=is_driven,
            termination_ohm=float(port.z0_ohm),
            current_diagnostics=diagnostics,
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
            spec = spec_by_id[port.port_id]
            extra = ""
            if port.port_id in gap_material_note:
                sigma_gap, epsilon_r_gap = gap_material_note[port.port_id]
                cond = (r.current_diagnostics or {}).get("conduction")
                extra = (
                    f" [route {spec.current_route}: gap sigma = {sigma_gap:.6e} S/m, "
                    f"eps_gap/eps_0 = {epsilon_r_gap:.6f}, I_cond = {cond!r}]"
                )
            print(
                f"    {r.port_id}: V = {r.voltage_v.real:+.9e}{r.voltage_v.imag:+.9e}j V, "
                f"I = {r.current_a.real:+.9e}{r.current_a.imag:+.9e}j A "
                f"({'driven' if r.is_driven else 'undriven'}){extra}"
            )

    return SinglePortExcitationResult(
        driven_port_id=driven_port_id,
        frequency_hz=problem.frequency_hz,
        responses=responses,
        solve_context=solve_context,
        is_placeholder=False,
    )
