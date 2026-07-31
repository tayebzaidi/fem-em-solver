"""Near-resonance guard for frequency-domain sweeps (`TH-1` step 5).

PROJECT_PLAN §7 names the silent-failure mode of Phase 2: with PEC boundaries
and low-loss interior the curl-curl operator is *exactly singular* at the
cavity eigenfrequencies of the truncation box, and an MRI coil is deliberately
operated near resonance. MUMPS returns a clean exit code on a near-singular
system — the same shape as `MAG-10`'s "converged, residual 0.0, 920% error".

The guard here is the energy-continuity check: stored electric energy

    W(f) = (ε₀/4) ∫ εᵣ |E|² dx

is a smooth, slowly varying function of frequency away from any mode, and near
a mode at ``f₀`` it behaves like a simple pole, ``W ∼ |f − f₀|⁻²``.  The
logarithmic sensitivity

    S = |d ln W / d ln f| ≈ 2f / |f − f₀|

is therefore ``O(1)`` in a quiet band and grows without bound on approach, which
makes it a *calibrated* detector rather than a heuristic: the default threshold
of 50 fires exactly when a sweep point is within ``2/50 = 4%`` of a pole.  It
needs no eigen-solve and no knowledge of the geometry — only two solves that a
sweep is performing anyway.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import ufl
from mpi4py import MPI
from dolfinx import fem

from ..utils.constants import EPSILON_0

#: |d ln W / d ln f| above which a sweep interval is called near-resonant.
#: S ≈ 2f/|f − f₀| near a pole, so 50 corresponds to ~4% fractional detuning.
DEFAULT_SLOPE_THRESHOLD = 50.0


@dataclass(frozen=True)
class ResonanceGuardReport:
    """Outcome of an energy-continuity check across sweep points."""

    frequencies_hz: tuple[float, ...]
    energies_j: tuple[float, ...]
    slopes: tuple[float, ...]
    max_slope: float
    slope_threshold: float
    triggered: bool
    worst_interval_hz: tuple[float, float]

    @property
    def implied_detuning_fraction(self) -> float:
        """Fractional distance to the implied pole, ``2/S`` — ∞ when quiet."""
        if self.max_slope <= 0.0:
            return float("inf")
        return float(2.0 / self.max_slope)

    def describe(self) -> str:
        state = "NEAR-RESONANT" if self.triggered else "clear"
        return (
            f"resonance guard: {state}; max |dlnW/dlnf| = {self.max_slope:.3f} "
            f"(threshold {self.slope_threshold:.1f}) on "
            f"[{self.worst_interval_hz[0]:.6e}, {self.worst_interval_hz[1]:.6e}] Hz; "
            f"implied detuning {self.implied_detuning_fraction:.3%}"
        )


def stored_electric_energy(fields, comm: MPI.Intracomm | None = None) -> float:
    """``W = (ε₀/4)∫ εᵣ|E|² dx`` for a solved :class:`TimeHarmonicFields` [J].

    ``ufl.inner`` conjugates its second argument, so ``inner(E, E)`` is ``|E|²``
    and the integral is real up to round-off. ``assemble_scalar`` is rank-local
    — reduced here before the caller ever sees a number.
    """
    e_field = fields.e_complex
    if e_field is None:
        raise ValueError(
            "stored_electric_energy needs the complex phasor; this "
            "TimeHarmonicFields has e_complex=None"
        )
    mesh = e_field.function_space.mesh
    comm = comm or mesh.comm

    epsilon_r = fields.epsilon_r_field
    integrand = ufl.inner(e_field, e_field)
    if epsilon_r is not None:
        integrand = epsilon_r * integrand

    local = fem.assemble_scalar(fem.form(integrand * ufl.dx))
    total = comm.allreduce(local, op=MPI.SUM)
    return float(0.25 * EPSILON_0 * np.real(total))


def check_energy_continuity(
    frequencies_hz: Sequence[float],
    energies_j: Sequence[float],
    *,
    slope_threshold: float = DEFAULT_SLOPE_THRESHOLD,
) -> ResonanceGuardReport:
    """Flag sweep intervals where stored energy moves faster than a pole allows.

    Parameters
    ----------
    frequencies_hz, energies_j:
        Matching sequences of at least two sweep points; ``energies_j`` is what
        :func:`stored_electric_energy` returns at each.
    slope_threshold:
        ``|d ln W / d ln f|`` at which to trigger. See
        :data:`DEFAULT_SLOPE_THRESHOLD` for the calibration.
    """
    freqs = np.asarray(frequencies_hz, dtype=float)
    energies = np.asarray(energies_j, dtype=float)

    if freqs.size != energies.size:
        raise ValueError(
            f"frequencies_hz and energies_j must match in length; got "
            f"{freqs.size} and {energies.size}"
        )
    if freqs.size < 2:
        raise ValueError("energy continuity needs at least two sweep points")
    if np.any(freqs <= 0.0):
        raise ValueError("sweep frequencies must be positive (Hz)")
    if np.any(energies <= 0.0):
        raise ValueError(
            "stored energies must be positive; a zero or negative energy means "
            "the solve returned no field, which is a failure in its own right"
        )

    log_f = np.log(freqs)
    log_w = np.log(energies)
    if np.any(np.diff(log_f) == 0.0):
        raise ValueError("sweep frequencies must be distinct")

    slopes = np.abs(np.diff(log_w) / np.diff(log_f))
    worst = int(np.argmax(slopes))

    return ResonanceGuardReport(
        frequencies_hz=tuple(float(f) for f in freqs),
        energies_j=tuple(float(w) for w in energies),
        slopes=tuple(float(s) for s in slopes),
        max_slope=float(slopes[worst]),
        slope_threshold=float(slope_threshold),
        triggered=bool(slopes[worst] > slope_threshold),
        worst_interval_hz=(float(freqs[worst]), float(freqs[worst + 1])),
    )
