"""`PORT-20` step 1 — the current-drive route's S is the closed-form ``z_to_s(Z)``.

Pure numpy, no mesh and no solve: the assertion is about the *assembly*, not
about any field.  Two synthetic reciprocal networks with a **known** impedance
matrix are turned into exactly the per-drive port states the gap-voltage
(impressed-current) route produces — port ``j`` carries the impressed current
``I_j``, every other port is **open** (``I_i = 0``), and the terminal voltages
are ``V = Z I`` — and the route's own assembly
(:func:`~fem_em_solver.ports.sparameters._assemble_current_drive_route_matrices`)
must return the analytic ``S = (Z − z0 I)(Z + z0 I)⁻¹`` to 1e-12.

**Negative control, asserted.**  The per-port power-wave assembly this route used
before `PORT-20` (:func:`_assemble_sparameter_matrix`, still in the module and
still correct for the *lumped-sheet* route's matched drive) is run on the same
port states and must miss the analytic ``S₂₁`` by more than ``NEGATIVE_CONTROL_
FLOOR = 1e-2``.  An open undriven port has ``a_i ≠ 0``, so ``b_i/a_j`` is not an
S entry — that is the defect known-issues 2026-09-19 records, and this control
makes it a measured separation on a network whose S is known in closed form
rather than a reading.  The floor is stated against the ceiling ``|ΔS| ≤ 2``
(any two entries of two matrices bounded by 1 in magnitude); the miss is printed
and never copied from the plan.

The networks:

  * a **T-network 2-port** — series ``Z_a``/``Z_b`` into a shunt ``Z_c``, so
    ``Z₁₁ = Z_a + Z_c``, ``Z₂₂ = Z_b + Z_c``, ``Z₁₂ = Z₂₁ = Z_c``.  Symmetric by
    construction, and ``Re Z`` positive-definite for the chosen values, so it is
    a passive reciprocal network and ``Z + z0 I`` is nonsingular.
  * a **seeded random reciprocal 3-port** with positive-definite ``R`` (built as
    ``R = A Aᵀ + n I`` from a seeded ``A``) and a symmetric ``X``.  The seed is
    fixed so the case is a fixture, not a lottery.

Scope: the route's reported ``S``.  No record in this repository is re-recorded
here — the S-derived records of `EX-20`, `ans:3` and `PORT-1` step 4 move when
this lands and are `PORT-20` step 3's.
"""

from __future__ import annotations

import numpy as np
import pytest

from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.excitation import (
    PortVoltageCurrentEstimate,
    SinglePortExcitationResult,
)
from fem_em_solver.ports.sparameters import (
    _assemble_current_drive_route_matrices,
    _assemble_sparameter_matrix,
)

Z0_OHM = 50.0
FREQUENCY_HZ = 10.0e6
DRIVE_CURRENT_A = 1.0 + 0.0j

# The closed-form identity's band.  Both sides are numpy linear algebra on a
# 2x2/3x3, so this is a round-off band, not a physics tolerance.
CLOSED_FORM_BAND = 1.0e-12
# Negative control: how far the pre-PORT-20 power-wave assembly must sit from the
# analytic off-diagonal.  Ceiling |dS| <= 2 (two entries each bounded by 1).
NEGATIVE_CONTROL_FLOOR = 1.0e-2
NEGATIVE_CONTROL_CEILING = 2.0

# T-network element values (`PORT-20` step 1, pre-registered).
Z_A = 10.0 + 20.0j
Z_B = 15.0 - 5.0j
Z_C = 40.0 + 30.0j

RANDOM_3PORT_SEED = 20260920


def _t_network_z() -> np.ndarray:
    """``Z`` of the series-series-shunt T, the textbook open-circuit matrix."""
    return np.array(
        [[Z_A + Z_C, Z_C], [Z_C, Z_B + Z_C]],
        dtype=np.complex128,
    )


def _random_reciprocal_z(n: int = 3) -> np.ndarray:
    """A seeded reciprocal ``Z`` with positive-definite ``R`` (so: passive)."""
    rng = np.random.default_rng(RANDOM_3PORT_SEED)
    a = rng.normal(size=(n, n))
    r = a @ a.T + float(n) * np.eye(n)  # symmetric, strictly positive-definite
    b = rng.normal(size=(n, n))
    x = 0.5 * (b + b.T)  # symmetric reactance, no definiteness needed
    return (r + 1j * x).astype(np.complex128)


def _ports(n: int) -> list[PortDefinition]:
    return [
        PortDefinition(
            port_id=f"P{k + 1}",
            positive_tag=10 * (k + 1),
            negative_tag=10 * (k + 1) + 1,
            orientation=f"synthetic_port_{k + 1}",
            z0_ohm=Z0_OHM,
        )
        for k in range(n)
    ]


def _current_drive_states(
    z_matrix: np.ndarray, ports: list[PortDefinition]
) -> dict[str, SinglePortExcitationResult]:
    """The per-drive port states the gap-voltage route produces.

    One entry per driven port ``k``: ``I_k = DRIVE_CURRENT_A``, every other
    port's current **zero** (open), and ``V = Z I`` — i.e. column ``k`` of ``Z``
    scaled by the impressed current.  This is the *only* modelling assumption in
    the test, and it is the one known-issues 2026-09-19 names.
    """
    n = len(ports)
    results: dict[str, SinglePortExcitationResult] = {}
    for k, driven in enumerate(ports):
        currents = np.zeros(n, dtype=np.complex128)
        currents[k] = DRIVE_CURRENT_A
        voltages = z_matrix @ currents
        responses = {
            port.port_id: PortVoltageCurrentEstimate(
                port_id=port.port_id,
                voltage_v=complex(voltages[i]),
                current_a=complex(currents[i]),
                is_driven=(i == k),
                termination_ohm=float("inf"),  # open, on this route
            )
            for i, port in enumerate(ports)
        }
        results[driven.port_id] = SinglePortExcitationResult(
            driven_port_id=driven.port_id,
            frequency_hz=FREQUENCY_HZ,
            responses=responses,
            solve_context={},
            is_placeholder=False,
        )
    return results


def _analytic_s(z_matrix: np.ndarray) -> np.ndarray:
    """``S = (Z − z0 I)(Z + z0 I)⁻¹``, written out here and nowhere else."""
    identity = np.eye(z_matrix.shape[0], dtype=np.complex128)
    return (z_matrix - Z0_OHM * identity) @ np.linalg.inv(z_matrix + Z0_OHM * identity)


@pytest.mark.parametrize(
    "label, z_builder",
    [("T-network 2-port", _t_network_z), ("seeded random reciprocal 3-port", _random_reciprocal_z)],
)
def test_current_drive_route_s_is_the_closed_form(label, z_builder):
    """The route's assembly reproduces ``(Z − z0)(Z + z0)⁻¹`` at 1e-12."""
    z_matrix = z_builder()
    n = z_matrix.shape[0]
    ports = _ports(n)
    states = _current_drive_states(z_matrix, ports)

    # Premise checks: the network is reciprocal and passive, so the comparison
    # is against a physically meaningful S in the first place.
    assert np.allclose(z_matrix, z_matrix.T, atol=1e-14), "the fixture Z must be reciprocal"
    eigenvalues = np.linalg.eigvalsh(0.5 * (z_matrix + z_matrix.conj().T))
    assert float(np.min(eigenvalues.real)) > 0.0, (
        f"the fixture Z's Hermitian part is not positive-definite: {eigenvalues}"
    )

    assembled_z, assembled_s = _assemble_current_drive_route_matrices(
        ports, states, z0_ohm=Z0_OHM
    )
    analytic_s = _analytic_s(z_matrix)

    z_miss = float(np.max(np.abs(assembled_z - z_matrix)))
    s_miss = float(np.max(np.abs(assembled_s - analytic_s)))
    print(
        f"\n[PORT-20 step 1] {label}, z0 = {Z0_OHM:.0f} Ohm\n"
        f"    Z (known):\n{z_matrix}\n"
        f"    Z (route assembly) max|delta| = {z_miss:.3e}\n"
        f"    S (route assembly):\n{assembled_s}\n"
        f"    S (analytic (Z-z0)(Z+z0)^-1) max|delta| = {s_miss:.3e} "
        f"(band {CLOSED_FORM_BAND:.1e})",
        flush=True,
    )

    assert z_miss < CLOSED_FORM_BAND, (
        f"the route did not recover the open-circuit Z it was handed: "
        f"max|delta| = {z_miss:.3e} >= {CLOSED_FORM_BAND:.1e}"
    )
    assert s_miss < CLOSED_FORM_BAND, (
        f"the current-drive route's S is not the closed-form (Z-z0)(Z+z0)^-1: "
        f"max|delta| = {s_miss:.3e} >= {CLOSED_FORM_BAND:.1e}"
    )


def test_power_wave_assembly_misses_the_closed_form_s21():
    """Negative control (asserted): the pre-`PORT-20` assembly is not S here.

    Called directly, on the very port states the identity above passes on.  If
    this agreed, the fix would be measuring nothing and the 2026-09-19 finding
    would be wrong.
    """
    z_matrix = _t_network_z()
    ports = _ports(2)
    states = _current_drive_states(z_matrix, ports)

    analytic_s = _analytic_s(z_matrix)
    power_wave_s = _assemble_sparameter_matrix(ports, states, z0_ohm=Z0_OHM)

    delta = power_wave_s - analytic_s
    off_diagonal_miss = float(abs(delta[1, 0]))
    max_miss = float(np.max(np.abs(delta)))
    print(
        f"\n[PORT-20 step 1] negative control — the pre-PORT-20 power-wave "
        f"assembly on open undriven ports:\n"
        f"    S (power waves):\n{power_wave_s}\n"
        f"    S (analytic):\n{analytic_s}\n"
        f"    S21: power-wave {power_wave_s[1, 0]!r} vs analytic "
        f"{analytic_s[1, 0]!r}\n"
        f"    |dS21| = {off_diagonal_miss:.6e}, max|dS| = {max_miss:.6e} "
        f"(floor {NEGATIVE_CONTROL_FLOOR:.1e}, ceiling "
        f"{NEGATIVE_CONTROL_CEILING:.1f})",
        flush=True,
    )

    assert off_diagonal_miss > NEGATIVE_CONTROL_FLOOR, (
        f"the power-wave assembly reproduces the closed-form S21 to "
        f"{off_diagonal_miss:.3e} on open undriven ports — that would be a "
        "finding about known-issues 2026-09-19, not a passing control"
    )
    assert off_diagonal_miss <= NEGATIVE_CONTROL_CEILING, (
        f"|dS21| = {off_diagonal_miss:.3e} exceeds the algebraic ceiling "
        f"{NEGATIVE_CONTROL_CEILING:.1f} — one of the two matrices is not an "
        "S-matrix-shaped object and the control is not measuring what it says"
    )
