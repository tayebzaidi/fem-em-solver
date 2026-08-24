"""N-port sweep and S-parameter assembly helpers (chunk E4/D3)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import numpy as np

from ..core import TimeHarmonicProblem
from ..core.solvers import DEFAULT_GAUGE_PENALTY
from .definitions import PortDefinition
from .excitation import (
    SinglePortExcitationResult,
    run_placeholder_port_coupling_case,
)
from .gap_voltage import GapVoltagePortSpec, run_gap_voltage_port_case
from .lumped import LumpedSheetPortSpec, run_lumped_sheet_port_case


@dataclass(frozen=True)
class SMatrixSanityReport:
    """First-line physical sanity metrics for an S-matrix (chunk D3)."""

    reciprocity_max_abs_delta: float
    reciprocity_max_rel_delta: float
    passivity_max_sigma: float
    passivity_max_column_power_sum: float
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class SParameterSweepResult:
    """Container for one frequency-point N-port S-parameter sweep.

    ``is_placeholder`` is True whenever any contributing excitation came from
    the heuristic coupling model rather than the solved field, in which case the
    S-matrix and its sanity metrics are physically meaningless. Touchstone
    export refuses such data unless explicitly allowed. See PORT-0/PORT-1.
    """

    frequency_hz: float
    port_ids: tuple[str, ...]
    s_matrix: np.ndarray
    excitation_results: dict[str, SinglePortExcitationResult]
    sanity_report: SMatrixSanityReport
    is_placeholder: bool = True
    # Present only on the solved-field routes (gap-voltage, lumped sheet), as a
    # **diagnostic**: it is the *terminated transimpedance* assembled by
    # :func:`_assemble_impedance_matrix`, not the open-circuit impedance matrix
    # reciprocity symmetrises, so it is never reciprocity-gated (`PORT-9` leg
    # (d2) mechanism (ii), leg (d3)).  S itself comes from power waves.  `None`
    # on the heuristic route, which has no impedance matrix to speak of.
    z_matrix: Optional[np.ndarray] = None


def _power_waves(voltage_v: complex, current_a: complex, z0_ohm: float) -> tuple[complex, complex]:
    """Return (a, b) power-wave amplitudes for a port state."""
    if z0_ohm <= 0.0:
        raise ValueError("z0_ohm must be positive")

    sqrt_z0 = np.sqrt(float(z0_ohm))
    a_wave = (voltage_v + z0_ohm * current_a) / (2.0 * sqrt_z0)
    b_wave = (voltage_v - z0_ohm * current_a) / (2.0 * sqrt_z0)
    return a_wave, b_wave


def sparameters_from_impedance(z_matrix: np.ndarray, *, z0_ohm: float) -> np.ndarray:
    """Return ``S = (Z − Z₀I)(Z + Z₀I)⁻¹`` for a real reference impedance.

    The packaged form of the conversion `PORT-1` step 2 first ran as three numpy
    lines inside `tests/validation/test_port_reaction_impedance.py`.  Deliberately
    pure numpy: it takes an impedance matrix from *any* source — the reaction
    integral of a solved field, a measurement, a circuit model — and knows
    nothing about `excitation.py`'s placeholder coupling path.  That separation
    is the point of the step: it is what lets an S-matrix derived from a solved
    field reach `summarize_sparameter_sanity` without routing through the
    heuristic (`PORT-0`/`PORT-5`, known-issues 3).

    ``Z₀`` is scalar here, matching the single-reference-impedance convention the
    step-2 fixture uses.  Per-port references need the generalised (power-wave)
    form and are not this function's job.
    """
    z = np.asarray(z_matrix)
    if z.ndim != 2:
        raise ValueError("z_matrix must be rank-2")
    if z.shape[0] != z.shape[1]:
        raise ValueError("z_matrix must be square")
    if not np.all(np.isfinite(z.real)) or not np.all(np.isfinite(z.imag)):
        raise ValueError("z_matrix contains non-finite values")
    if z0_ohm <= 0.0:
        raise ValueError("z0_ohm must be positive")

    identity = np.eye(z.shape[0], dtype=np.complex128)
    z0_identity = float(z0_ohm) * identity
    return (z - z0_identity) @ np.linalg.inv(z + z0_identity)


def summarize_sparameter_sanity(
    s_matrix: np.ndarray,
    *,
    reciprocity_abs_warn_threshold: float = 5e-2,
    reciprocity_rel_warn_threshold: float = 2e-1,
    passivity_warn_margin: float = 5e-2,
) -> SMatrixSanityReport:
    """Compute reciprocity/passivity sanity metrics with warning-oriented thresholds."""
    if s_matrix.ndim != 2:
        raise ValueError("s_matrix must be rank-2")
    if s_matrix.shape[0] != s_matrix.shape[1]:
        raise ValueError("s_matrix must be square")
    if not np.all(np.isfinite(s_matrix.real)) or not np.all(np.isfinite(s_matrix.imag)):
        raise ValueError("s_matrix contains non-finite values")

    reciprocity_delta = s_matrix - s_matrix.T
    reciprocity_max_abs_delta = float(np.max(np.abs(reciprocity_delta)))

    scale = np.maximum(np.maximum(np.abs(s_matrix), np.abs(s_matrix.T)), 1e-12)
    reciprocity_max_rel_delta = float(np.max(np.abs(reciprocity_delta) / scale))

    singular_values = np.linalg.svd(s_matrix, compute_uv=False)
    passivity_max_sigma = float(np.max(singular_values))

    column_power_sums = np.sum(np.abs(s_matrix) ** 2, axis=0)
    passivity_max_column_power_sum = float(np.max(column_power_sums))

    warnings: list[str] = []
    if reciprocity_max_abs_delta > reciprocity_abs_warn_threshold:
        warnings.append(
            "reciprocity abs delta exceeds warning threshold: "
            f"{reciprocity_max_abs_delta:.3e} > {reciprocity_abs_warn_threshold:.3e}"
        )
    if reciprocity_max_rel_delta > reciprocity_rel_warn_threshold:
        warnings.append(
            "reciprocity rel delta exceeds warning threshold: "
            f"{reciprocity_max_rel_delta:.3e} > {reciprocity_rel_warn_threshold:.3e}"
        )

    sigma_limit = 1.0 + passivity_warn_margin
    if passivity_max_sigma > sigma_limit:
        warnings.append(
            "passivity sigma exceeds warning threshold: "
            f"{passivity_max_sigma:.3e} > {sigma_limit:.3e}"
        )

    power_sum_limit = 1.0 + passivity_warn_margin
    if passivity_max_column_power_sum > power_sum_limit:
        warnings.append(
            "passivity column power sum exceeds warning threshold: "
            f"{passivity_max_column_power_sum:.3e} > {power_sum_limit:.3e}"
        )

    return SMatrixSanityReport(
        reciprocity_max_abs_delta=reciprocity_max_abs_delta,
        reciprocity_max_rel_delta=reciprocity_max_rel_delta,
        passivity_max_sigma=passivity_max_sigma,
        passivity_max_column_power_sum=passivity_max_column_power_sum,
        warnings=tuple(warnings),
    )


def _assemble_sparameter_matrix(
    ports: Sequence[PortDefinition],
    excitation_results: dict[str, SinglePortExcitationResult],
    *,
    z0_ohm: Optional[float] = None,
) -> np.ndarray:
    """Assemble S from per-port power waves: ``S_ij = b_i / a_j``.

    ``a`` and ``b`` are the incident/reflected amplitudes of :func:`_power_waves`
    read off the port states of the solve driven at ``j``.  On the gated
    solved-field routes this is what makes S reciprocal: with every port
    terminated in ``Z_p`` and the reference ``z0 = Z_p``, the undriven ports give
    ``b_i = −√z0 · I_i`` and the driven port gives ``a_j = V_src/(2√z0)``, so
    ``S_ij ∝ I_i(drive j)``, which leg (d2) measured to be symmetric to 1.33e-10
    (the readout *is* the impressed source's adjoint).  The terminated ``Z``
    assembled alongside carries a per-column normalisation by the driven port's
    own current and is a diagnostic only (`PORT-9` leg (d3), ruling (2*) of the
    2026-08-23 18:00 review).

    ``z0_ohm`` overrides the ports' own ``z0_ohm`` for both waves, matching the
    scalar-reference convention of the sweep.
    """
    n_ports = len(ports)
    s_matrix = np.zeros((n_ports, n_ports), dtype=np.complex128)

    for drive_col, driven_port in enumerate(ports):
        result = excitation_results[driven_port.port_id]
        if result.driven_port_id != driven_port.port_id:
            raise ValueError(
                "excitation_results key mismatch: "
                f"expected driven_port_id={driven_port.port_id}, got {result.driven_port_id}"
            )

        drive_response = result.responses[driven_port.port_id]
        a_drive, _ = _power_waves(
            drive_response.voltage_v,
            drive_response.current_a,
            driven_port.z0_ohm if z0_ohm is None else float(z0_ohm),
        )
        if np.isclose(abs(a_drive), 0.0):
            raise ValueError(
                f"incident wave for driven port '{driven_port.port_id}' is zero; cannot assemble S-matrix"
            )

        for recv_row, recv_port in enumerate(ports):
            recv_response = result.responses[recv_port.port_id]
            _, b_recv = _power_waves(
                recv_response.voltage_v,
                recv_response.current_a,
                recv_port.z0_ohm if z0_ohm is None else float(z0_ohm),
            )
            s_matrix[recv_row, drive_col] = b_recv / a_drive

    if not np.all(np.isfinite(s_matrix.real)) or not np.all(np.isfinite(s_matrix.imag)):
        raise ValueError("assembled S-matrix contains non-finite values")

    return s_matrix


def _assemble_impedance_matrix(
    ports: Sequence[PortDefinition],
    excitation_results: dict[str, SinglePortExcitationResult],
) -> np.ndarray:
    """``Z[i, k] = V_i / I_k`` from one driven-port solve per column.

    The column-by-column definition `PORT-1` step 3b gated: ``I_k`` is the
    driven port's own (conduction) current in solve ``k``, and ``V_i`` is the
    terminal-to-terminal path voltage read off that same solve.  Power waves are
    deliberately not used here — S comes from Z through
    :func:`sparameters_from_impedance`, which is the route with a gate behind it.
    """
    n_ports = len(ports)
    z_matrix = np.zeros((n_ports, n_ports), dtype=np.complex128)
    for col, driven_port in enumerate(ports):
        result = excitation_results[driven_port.port_id]
        i_driven = result.responses[driven_port.port_id].current_a
        if np.isclose(abs(i_driven), 0.0):
            raise ValueError(
                f"driven-port current for '{driven_port.port_id}' is zero; "
                "cannot assemble an impedance matrix"
            )
        for row, recv_port in enumerate(ports):
            z_matrix[row, col] = result.responses[recv_port.port_id].voltage_v / i_driven

    if not np.all(np.isfinite(z_matrix.real)) or not np.all(np.isfinite(z_matrix.imag)):
        raise ValueError("assembled Z-matrix contains non-finite values")
    return z_matrix


def run_n_port_sparameter_sweep(
    problem: TimeHarmonicProblem,
    ports: Sequence[PortDefinition],
    *,
    gap_voltage_ports: Optional[Sequence[GapVoltagePortSpec]] = None,
    lumped_sheet_ports: Optional[Sequence[LumpedSheetPortSpec]] = None,
    lumped_sheet_facet_tags=None,
    reference_impedance_ohm: Optional[float] = None,
    drive_voltage_v: complex = 1.0 + 0.0j,
    terminated_port_impedance_ohm: float = 50.0,
    current_density: Optional[Callable] = None,
    subdomain_id: Optional[int] = None,
    subdomain_ids: Optional[Sequence[int]] = None,
    gauge_penalty: float = DEFAULT_GAUGE_PENALTY,
    degree: int = 1,
) -> SParameterSweepResult:
    """Run an N-port excitation sweep and assemble an NxN S-matrix.

    Three routes, selected by ``gap_voltage_ports`` / ``lumped_sheet_ports``
    (passing both is an error — an S-matrix mixing two port models means
    nothing):

    * **solved field** (`PORT-1` step 4) — pass one
      :class:`~fem_em_solver.ports.gap_voltage.GapVoltagePortSpec` per port and
      the sweep runs one impressed-gap solve per port, reads ``V`` and ``I`` off
      the field, and assembles ``S = b_i/a_j`` from the per-port power waves.
      ``is_placeholder`` is False and ``z_matrix`` is populated with the
      *terminated transimpedance* as a diagnostic.
    * **lumped sheet** (`PORT-9` step 2c) — pass one
      :class:`~fem_em_solver.ports.lumped.LumpedSheetPortSpec` per port plus the
      mesh's ``lumped_sheet_facet_tags``, and every port becomes a resistive
      sheet in the bilinear form with the driven one carrying the impressed
      source.  ``V`` and ``I`` come from the sheets' own constitutive law on the
      generator convention (``V = V_src − I·Z_p``); ``Z`` and ``S`` are then
      assembled exactly as on the gap-voltage route.  This is the route
      `PORT-9` step 3's reciprocity gate runs through — and that gate is only
      exact at a **matched** drive, ``Z_p = z0``, where ``a_j`` reduces to
      ``V_src/(2√z0)`` and the driven port's own current drops out of the
      normalisation (leg (d3)).
    * **heuristic** (the retiring `PORT-0` path, kept reachable and deprecated)
      — with ``gap_voltage_ports=None`` the port quantities come from
      ``excitation.py``'s proximity model and mean nothing physically.  It emits
      a :class:`DeprecationWarning` on top of the existing
      :class:`~fem_em_solver.ports.excitation.PlaceholderPortModelWarning`.

    ``reference_impedance_ohm`` overrides the scalar ``Z0`` of the conversion;
    by default the ports' common ``z0_ohm`` is used (the converter is scalar-Z0
    by construction, so mixed per-port references are rejected rather than
    silently averaged).
    """
    if not ports:
        raise ValueError("ports must be non-empty")

    for port in ports:
        port.validate()

    port_ids = [port.port_id for port in ports]
    if len(set(port_ids)) != len(port_ids):
        raise ValueError("port_id values must be unique")

    if gap_voltage_ports is not None and lumped_sheet_ports is not None:
        raise ValueError(
            "pass gap_voltage_ports or lumped_sheet_ports, not both: they are two "
            "different port models and an S-matrix mixing them means nothing"
        )

    excitation_results: dict[str, SinglePortExcitationResult] = {}
    z_matrix: Optional[np.ndarray] = None

    if gap_voltage_ports is not None or lumped_sheet_ports is not None:
        for port in ports:
            if gap_voltage_ports is not None:
                excitation_results[port.port_id] = run_gap_voltage_port_case(
                    problem,
                    ports,
                    gap_voltage_ports,
                    driven_port_id=port.port_id,
                    gauge_penalty=gauge_penalty,
                    degree=degree,
                )
            else:
                excitation_results[port.port_id] = run_lumped_sheet_port_case(
                    problem,
                    ports,
                    lumped_sheet_ports,
                    facet_tags=lumped_sheet_facet_tags,
                    driven_port_id=port.port_id,
                    gauge_penalty=gauge_penalty,
                    degree=degree,
                )
        if reference_impedance_ohm is None:
            references = {float(port.z0_ohm) for port in ports}
            if len(references) != 1:
                raise ValueError(
                    "sparameters_from_impedance takes a scalar Z0: the ports carry "
                    f"{sorted(references)}; pass reference_impedance_ohm explicitly"
                )
            z0_ohm = references.pop()
        else:
            z0_ohm = float(reference_impedance_ohm)
        # S from power waves (`PORT-9` leg (d3)).  The terminated Z is retained
        # beside it as a diagnostic, never as S's source: pushing it through
        # `sparameters_from_impedance` — which assumes the open-circuit matrix —
        # inherits the per-column normalisation asymmetry leg (d2) measured and
        # adds a conversion bias on top of it.
        z_matrix = _assemble_impedance_matrix(ports, excitation_results)
        s_matrix = _assemble_sparameter_matrix(ports, excitation_results, z0_ohm=z0_ohm)
    else:
        warnings.warn(
            "run_n_port_sparameter_sweep() without gap_voltage_ports uses the "
            "PORT-0 coupling heuristic, not the solved field; pass "
            "gap_voltage_ports=[GapVoltagePortSpec(...)] for the gated route "
            "(PORT-1 step 4). The heuristic path is deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )
        for drive_idx, port in enumerate(ports):
            excitation_results[port.port_id] = run_placeholder_port_coupling_case(
                problem,
                ports,
                driven_port_id=port.port_id,
                driven_port_index=drive_idx,
                drive_voltage_v=drive_voltage_v,
                terminated_port_impedance_ohm=terminated_port_impedance_ohm,
                current_density=current_density,
                subdomain_id=subdomain_id,
                subdomain_ids=subdomain_ids,
                gauge_penalty=gauge_penalty,
                degree=degree,
            )
        s_matrix = _assemble_sparameter_matrix(ports, excitation_results)

    sanity_report = summarize_sparameter_sanity(s_matrix)

    if problem.mesh.comm.rank == 0:
        print("n-port S-parameter sweep diagnostics:")
        print(f"  frequency [Hz]: {problem.frequency_hz:.6e}")
        print(f"  ports: {', '.join(port_ids)}")
        print(f"  S-matrix shape: {s_matrix.shape}")
        diagonal = np.diag(s_matrix)
        diag_text = ", ".join(
            f"S{idx + 1}{idx + 1}={value.real:.3e}+{value.imag:.3e}j"
            for idx, value in enumerate(diagonal)
        )
        print(f"  diagonal terms: {diag_text}")
        print("  S-matrix sanity metrics:")
        print(
            "    reciprocity: "
            f"max|Sij-Sji|={sanity_report.reciprocity_max_abs_delta:.3e}, "
            f"max rel={sanity_report.reciprocity_max_rel_delta:.3e}"
        )
        print(
            "    passivity: "
            f"sigma_max={sanity_report.passivity_max_sigma:.3e}, "
            f"max column power sum={sanity_report.passivity_max_column_power_sum:.3e}"
        )
        if sanity_report.warnings:
            print("    warnings:")
            for warning in sanity_report.warnings:
                print(f"      - {warning}")
        else:
            print("    warnings: none")

    return SParameterSweepResult(
        frequency_hz=problem.frequency_hz,
        port_ids=tuple(port_ids),
        s_matrix=s_matrix,
        excitation_results=excitation_results,
        sanity_report=sanity_report,
        is_placeholder=any(r.is_placeholder for r in excitation_results.values()),
        z_matrix=z_matrix,
    )
