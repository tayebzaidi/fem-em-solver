"""Placeholder lumped-port coupling model (chunks E3/D2).

.. warning::

   **This module does not compute port quantities from the solved field.**

   ``run_placeholder_port_coupling_case`` runs the frequency-domain solve, then
   discards the resulting field and derives port voltages and currents from a
   hardcoded proximity heuristic::

       coupling   = +/-0.20 / (1 + wrapped_ring_distance)
       admittance = material_response * (1e-3 * cell_count)

   The 0.20 is arbitrary and ``1e-3 * cell_count`` is dimensionally meaningless.
   Port orientation is compared as a *string label*, not a geometric normal.

   Everything downstream -- S-matrices, reciprocity and passivity metrics,
   Touchstone exports -- therefore describes this heuristic's arithmetic and
   not electromagnetics. The outputs are well-formed and physically meaningless.
   Do not use them for tuning, matching, or any downstream engineering decision,
   and do not cite them as simulation results.

   Tracked as PORT-0 (quarantine) and PORT-1 (replace with a real port
   excitation derived from the solved field). PORT-1 in turn depends on TH-1,
   since the time-harmonic solver is itself currently a proxy.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence

import numpy as np

from ..core import HomogeneousMaterial, TimeHarmonicFields, TimeHarmonicProblem, TimeHarmonicSolver
from ..core.solvers import DEFAULT_GAUGE_PENALTY
from ..utils.constants import EPSILON_0
from .definitions import PortDefinition, validate_required_port_tags_exist


@dataclass(frozen=True)
class PortVoltageCurrentEstimate:
    """Per-port complex voltage/current estimate for one excitation solve."""

    port_id: str
    voltage_v: complex
    current_a: complex
    is_driven: bool
    termination_ohm: float


@dataclass(frozen=True)
class PortSolveContext:
    """Deterministic per-port solve context for diagnostics/traceability."""

    port_id: str
    port_index: int
    driven_port_id: str
    driven_port_index: int
    is_driven: bool
    wrapped_ring_distance: int
    coupling_factor: float
    termination_ohm: float


class PlaceholderPortModelWarning(UserWarning):
    """Raised whenever port quantities come from the heuristic, not the field."""


PLACEHOLDER_PORT_MODEL_NOTICE = (
    "Port voltages/currents come from a hardcoded proximity heuristic, NOT from "
    "the solved field. S-parameters, sanity metrics, and Touchstone exports "
    "derived from them are physically meaningless. See PORT-0/PORT-1."
)


@dataclass(frozen=True)
class SinglePortExcitationResult:
    """Output container for one driven-port frequency-domain solve.

    ``is_placeholder`` marks results produced by the heuristic coupling model.
    It propagates into :class:`SParameterSweepResult` and gates Touchstone
    export, so fabricated data cannot be written to a file that looks like
    simulation output without an explicit opt-in.
    """

    driven_port_id: str
    frequency_hz: float
    responses: dict[str, PortVoltageCurrentEstimate]
    solve_context: dict[str, PortSolveContext]
    is_placeholder: bool = True


def _material_response_mean(fields: TimeHarmonicFields, fallback: HomogeneousMaterial) -> complex:
    """Return global mean of sigma + j*omega*epsilon from material fields."""
    omega = 2.0 * np.pi * fields.frequency_hz

    if fields.sigma_field is None or fields.epsilon_r_field is None:
        return complex(fallback.sigma, omega * EPSILON_0 * fallback.epsilon_r)

    sigma_values = np.asarray(fields.sigma_field.x.array, dtype=np.float64)
    epsilon_values = np.asarray(fields.epsilon_r_field.x.array, dtype=np.float64)
    response = sigma_values + 1j * omega * EPSILON_0 * epsilon_values

    comm = fields.sigma_field.function_space.mesh.comm
    local_count = np.array([response.size], dtype=np.float64)
    local_sum_real = np.array([float(np.sum(response.real))], dtype=np.float64)
    local_sum_imag = np.array([float(np.sum(response.imag))], dtype=np.float64)

    global_count = np.zeros_like(local_count)
    global_sum_real = np.zeros_like(local_sum_real)
    global_sum_imag = np.zeros_like(local_sum_imag)

    comm.Allreduce(local_count, global_count)
    comm.Allreduce(local_sum_real, global_sum_real)
    comm.Allreduce(local_sum_imag, global_sum_imag)

    if global_count[0] <= 0:
        return complex(fallback.sigma, omega * EPSILON_0 * fallback.epsilon_r)

    return complex(global_sum_real[0] / global_count[0], global_sum_imag[0] / global_count[0])


def _orientation_alignment_sign(driven_orientation: str, target_orientation: str) -> float:
    """Return orientation alignment sign (+1 aligned, -1 flipped).

    For this MVP convention, orientation metadata is treated as a directional label;
    a passive port with a different normalized orientation label than the driven
    port is interpreted as flipped polarity relative to the driven reference.
    """
    driven = str(driven_orientation).strip().lower()
    target = str(target_orientation).strip().lower()
    if not driven or not target:
        return 1.0
    return 1.0 if driven == target else -1.0


def _normalize_passive_termination_map(
    ports: Sequence[PortDefinition],
    *,
    driven_port_id: str,
    terminated_port_impedance_ohm: float,
    passive_port_terminations_ohm: Optional[Mapping[str, float]],
) -> dict[str, float]:
    """Validate and normalize passive-port termination settings."""
    if terminated_port_impedance_ohm <= 0.0:
        raise ValueError("terminated_port_impedance_ohm must be positive")

    port_ids = {port.port_id for port in ports}

    if passive_port_terminations_ohm is None:
        raw_map: Mapping[str, float] = {}
    else:
        raw_map = passive_port_terminations_ohm

    unknown = sorted(set(raw_map.keys()).difference(port_ids))
    if unknown:
        raise ValueError(f"passive_port_terminations_ohm has unknown ports: {unknown}")

    if driven_port_id in raw_map:
        raise ValueError(
            "passive_port_terminations_ohm must not include driven port "
            f"'{driven_port_id}'"
        )

    normalized: dict[str, float] = {}
    for port in ports:
        if port.port_id == driven_port_id:
            continue

        value = float(raw_map.get(port.port_id, terminated_port_impedance_ohm))
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(
                "passive termination must be finite and positive for port "
                f"'{port.port_id}', got {value!r}"
            )
        normalized[port.port_id] = value

    return normalized


def run_placeholder_port_coupling_case(
    problem: TimeHarmonicProblem,
    ports: Sequence[PortDefinition],
    *,
    driven_port_id: str,
    driven_port_index: Optional[int] = None,
    drive_voltage_v: complex = 1.0 + 0.0j,
    terminated_port_impedance_ohm: float = 50.0,
    passive_port_terminations_ohm: Optional[Mapping[str, float]] = None,
    current_density: Optional[Callable] = None,
    subdomain_id: Optional[int] = None,
    subdomain_ids: Optional[Sequence[int]] = None,
    gauge_penalty: float = DEFAULT_GAUGE_PENALTY,
    degree: int = 1,
) -> SinglePortExcitationResult:
    """Run one driven-port case and return per-port V/I estimates.

    .. warning::
       Results are **not** derived from the solved field. See the module
       docstring. This function emits :class:`PlaceholderPortModelWarning` on
       every call and marks its result ``is_placeholder=True``.

    The heuristic is:
    - driven port voltage is fixed to ``drive_voltage_v``
    - passive port induced voltages are scaled by inverse ring-distance coupling
    - passive ports are terminated by ``terminated_port_impedance_ohm`` or
      ``passive_port_terminations_ohm`` overrides.
    """
    warnings.warn(PLACEHOLDER_PORT_MODEL_NOTICE, PlaceholderPortModelWarning, stacklevel=2)

    if not ports:
        raise ValueError("ports must be non-empty")

    if problem.cell_tags is None:
        raise ValueError("single-port excitation requires problem.cell_tags for port-tag lookup")

    for port in ports:
        port.validate()

    port_ids = [port.port_id for port in ports]
    if len(set(port_ids)) != len(port_ids):
        raise ValueError("port_id values must be unique")
    if driven_port_id not in port_ids:
        raise ValueError(f"driven_port_id '{driven_port_id}' not found in ports")

    inferred_driven_index = port_ids.index(driven_port_id)
    if driven_port_index is not None:
        if driven_port_index < 0 or driven_port_index >= len(ports):
            raise ValueError(
                "driven_port_index must be within [0, len(ports)-1], got "
                f"{driven_port_index}"
            )
        if inferred_driven_index != driven_port_index:
            raise ValueError(
                "driven_port_id/index mismatch: "
                f"driven_port_id='{driven_port_id}' resolves to index {inferred_driven_index}, "
                f"but driven_port_index={driven_port_index}"
            )

    passive_termination_map = _normalize_passive_termination_map(
        ports,
        driven_port_id=driven_port_id,
        terminated_port_impedance_ohm=terminated_port_impedance_ohm,
        passive_port_terminations_ohm=passive_port_terminations_ohm,
    )

    validate_required_port_tags_exist(ports, available_tags=problem.cell_tags.values)

    solver = TimeHarmonicSolver(problem, degree=degree)
    fields = solver.solve(
        current_density=current_density,
        subdomain_id=subdomain_id,
        subdomain_ids=subdomain_ids,
        gauge_penalty=gauge_penalty,
    )

    material_response = _material_response_mean(fields, fallback=problem.material)

    tag_values = np.asarray(problem.cell_tags.values)
    comm = problem.mesh.comm

    driven_index = inferred_driven_index
    driven_orientation = ports[driven_index].orientation
    responses: dict[str, PortVoltageCurrentEstimate] = {}
    solve_context: dict[str, PortSolveContext] = {}

    for idx, port in enumerate(ports):
        local_pos = int(np.count_nonzero(tag_values == int(port.positive_tag)))
        local_neg = int(np.count_nonzero(tag_values == int(port.negative_tag)))

        global_pos = comm.allreduce(local_pos)
        global_neg = comm.allreduce(local_neg)
        support = max(global_pos + global_neg, 1)

        admittance = material_response * (1e-3 * support)

        ring_distance = abs(idx - driven_index)
        wrapped_distance = min(ring_distance, len(ports) - ring_distance)

        if port.port_id == driven_port_id:
            voltage = complex(drive_voltage_v)
            current = admittance * voltage
            is_driven = True
            term_ohm = float(port.z0_ohm)
            coupling = 1.0
        else:
            orientation_sign = _orientation_alignment_sign(driven_orientation, port.orientation)
            coupling = orientation_sign * (0.20 / (1.0 + wrapped_distance))
            induced_open_voltage = complex(drive_voltage_v) * coupling

            term_ohm = float(passive_termination_map[port.port_id])
            divider = term_ohm / (term_ohm + port.z0_ohm)
            voltage = induced_open_voltage * divider
            current = voltage / term_ohm
            is_driven = False

        responses[port.port_id] = PortVoltageCurrentEstimate(
            port_id=port.port_id,
            voltage_v=voltage,
            current_a=current,
            is_driven=is_driven,
            termination_ohm=term_ohm,
        )
        solve_context[port.port_id] = PortSolveContext(
            port_id=port.port_id,
            port_index=idx,
            driven_port_id=driven_port_id,
            driven_port_index=driven_index,
            is_driven=is_driven,
            wrapped_ring_distance=wrapped_distance,
            coupling_factor=float(coupling),
            termination_ohm=term_ohm,
        )

    if comm.rank == 0:
        print("*** PLACEHOLDER PORT MODEL -- values below are NOT from the solved field ***")
        print("single-port excitation diagnostics:")
        print(f"  driven_port: {driven_port_id} (index={driven_index})")
        print(f"  frequency [Hz]: {problem.frequency_hz:.6e}")
        for port in ports:
            response = responses[port.port_id]
            context = solve_context[port.port_id]
            print(
                "  "
                f"{response.port_id}: idx={context.port_index}, "
                f"driven={response.is_driven}, "
                f"orientation={port.orientation}, "
                f"distance={context.wrapped_ring_distance}, "
                f"coupling={context.coupling_factor:.6e}, "
                f"termination={response.termination_ohm:.6f} ohm, "
                f"V={response.voltage_v.real:.6e}+{response.voltage_v.imag:.6e}j V, "
                f"I={response.current_a.real:.6e}+{response.current_a.imag:.6e}j A"
            )

    return SinglePortExcitationResult(
        driven_port_id=driven_port_id,
        frequency_hz=problem.frequency_hz,
        responses=responses,
        solve_context=solve_context,
        is_placeholder=True,
    )


def run_single_port_excitation_case(*args, **kwargs) -> SinglePortExcitationResult:
    """Deprecated alias for :func:`run_placeholder_port_coupling_case`.

    The original name implied the result came from a port excitation solve. It
    does not -- see the module docstring. Renamed under PORT-0; this alias is
    kept so existing callers fail loudly rather than at import time.
    """
    warnings.warn(
        "run_single_port_excitation_case() is a misleading name for a "
        "placeholder model and will be removed; use "
        "run_placeholder_port_coupling_case(). " + PLACEHOLDER_PORT_MODEL_NOTICE,
        DeprecationWarning,
        stacklevel=2,
    )
    return run_placeholder_port_coupling_case(*args, **kwargs)
