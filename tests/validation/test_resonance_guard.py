"""`TH-1` step 5: the near-resonance guard, fired against a known `TH-9` mode.

A guard nobody has seen trigger is decoration. This test drives an empty PEC
box — the same 1.0 × 0.8 × 0.6 m fixture whose spectrum `TH-9` validated against
the closed form — and sweeps *toward* its fundamental mode, where the curl-curl
operator is exactly singular and MUMPS nonetheless exits cleanly. The stored
electric energy must blow up like a simple pole and
``core.resonance.check_energy_continuity`` must fire; in a quiet band between
modes, the same machinery must stay silent.

The discrete fundamental is taken from the `TH-9` eigen-solver on the *same*
mesh and degree rather than from the closed form, so the sweep is placed
relative to the pole the driven solve actually has (the discretisation moves it
by a fraction of a percent at degree 2 and more at degree 1 — enough to matter
when the sweep sits 1% away).

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_resonance_guard.py -v'
"""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import mesh as dmesh

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
    check_energy_continuity,
    stored_electric_energy,
)
from fem_em_solver.core.cavity import solve_pec_cavity_modes

from tests.complex_mode import complex_only

EDGES = (1.0, 0.8, 0.6)
DIVISIONS = (8, 7, 5)
DEGREE = 2

# Empty, essentially lossless cavity: this is the configuration §7 warns about,
# where the PEC operator is singular at the mode and the solve reports success.
AIR = HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0)


def _uniform_drive(x):
    """A constant ẑ current density — overlaps the fundamental, so it excites it."""
    zero = 0.0 * x[0]
    return ufl.as_vector([zero, zero, 1.0 + zero])


def _solve_at(msh, frequency_hz: float):
    """The driven solve behind one sweep point, returning the fields themselves.

    Factored out of :func:`_energy_at` (additively, 2026-08-09, `EX-8`) so the
    example can export the field a sweep point was scored from rather than
    re-deriving an equivalent one. No assertion here depends on it.
    """
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=frequency_hz,
        material=AIR,
        boundary_condition="pec_zero_tangential_a",
    )
    solver = TimeHarmonicSolver(problem, degree=DEGREE)
    return solver.solve(current_density=_uniform_drive)


def _energy_at(msh, frequency_hz: float, comm) -> float:
    return stored_electric_energy(_solve_at(msh, frequency_hz), comm)


def _sweep(msh, frequencies, comm) -> list[float]:
    return [_energy_at(msh, f, comm) for f in frequencies]


@complex_only
@pytest.mark.integration
def test_energy_continuity_guard_fires_near_a_cavity_mode():
    """Fires within ~1% of the fundamental; silent in the band between modes.

    Both halves are needed: a guard that always triggers is as useless as one
    that never does, so the quiet sweep is the false-positive control and the
    separation between the two maximum slopes is the quantitative assertion.
    """
    comm = MPI.COMM_WORLD

    spectrum = solve_pec_cavity_modes(
        edges=EDGES, divisions=DIVISIONS, degree=DEGREE, n_modes=2, comm=comm
    )
    f1, f2 = float(spectrum.frequencies_hz[0]), float(spectrum.frequencies_hz[1])

    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array(EDGES)],
        list(DIVISIONS),
        cell_type=dmesh.CellType.tetrahedron,
    )

    # Approach: 4%, 2%, 1% below the discrete pole. The last interval implies a
    # detuning of ~1%, i.e. a slope near 2/0.01 = 200.
    near_freqs = [f1 * (1.0 - d) for d in (0.04, 0.02, 0.01)]
    # Quiet: the midpoint between the two lowest modes, which is as far from
    # both poles as the band allows. A first attempt put this at f1 + 0.35(f2-f1)
    # and measured a slope of 48.9 — that point is only 6% above f1 and still on
    # its skirt, which the guard correctly reported as an implied detuning of
    # 4.1% (log 20260731T021415Z_TH-1-step5.log). The control sweep moved; the
    # threshold did not.
    mid = 0.5 * (f1 + f2)
    quiet_freqs = [mid * (1.0 + d) for d in (-0.02, 0.0, 0.02)]

    near_energies = _sweep(msh, near_freqs, comm)
    quiet_energies = _sweep(msh, quiet_freqs, comm)

    near = check_energy_continuity(near_freqs, near_energies)
    quiet = check_energy_continuity(quiet_freqs, quiet_energies)

    amplification = near_energies[-1] / near_energies[0]
    # W ∼ |f − f₀|⁻², so moving from 4% to 1% detuning must raise the stored
    # energy by (0.04/0.01)² = 16. This is the quantitative gate: it checks the
    # pole *law*, not merely that the numbers grew.
    predicted_amplification = (0.04 / 0.01) ** 2
    amplification_error = abs(amplification - predicted_amplification) / predicted_amplification
    separation = near.max_slope / quiet.max_slope

    if comm.rank == 0:
        print("\n[TH-1 step 5] resonance guard against the TH-9 fixture:")
        print(f"  discrete modes: f1 = {f1:.6e} Hz, f2 = {f2:.6e} Hz")
        print(f"  approach sweep {[f'{f:.4e}' for f in near_freqs]}")
        print(f"    energies {[f'{w:.4e}' for w in near_energies]}")
        print(f"    {near.describe()}")
        print(f"  quiet sweep    {[f'{f:.4e}' for f in quiet_freqs]}")
        print(f"    energies {[f'{w:.4e}' for w in quiet_energies]}")
        print(f"    {quiet.describe()}")
        print(f"  energy amplification over the approach: {amplification:.3f}x "
              f"vs pole law {predicted_amplification:.1f}x ({amplification_error:.3%})")
        print(f"  slope separation near/quiet: {separation:.3f}x")

    assert near.triggered, (
        f"the guard did not fire 1% from a cavity mode: {near.describe()}"
    )
    assert not quiet.triggered, (
        f"the guard fired in a quiet band, so it cannot distinguish resonance "
        f"from ordinary dispersion: {quiet.describe()}"
    )
    assert amplification_error < 0.10, (
        f"stored energy rose {amplification:.3f}x from 4% to 1% detuning, but the "
        f"|f−f₀|⁻² pole law requires {predicted_amplification:.1f}x "
        f"({amplification_error:.2%} off) — either the drive does not couple to "
        "the fundamental or the pole is not where TH-9 says it is"
    )
    # The threshold must not be perched on the data: a factor of two of margin
    # on each side, so neither verdict turns on the third significant figure.
    assert near.max_slope > 2.0 * near.slope_threshold, (
        f"near-resonant slope {near.max_slope:.2f} clears the threshold "
        f"{near.slope_threshold:.1f} by less than 2x"
    )
    assert quiet.max_slope < 0.5 * quiet.slope_threshold, (
        f"quiet-band slope {quiet.max_slope:.2f} sits within 2x of the threshold "
        f"{quiet.slope_threshold:.1f}; the guard has no false-positive margin"
    )
    # The implied detuning is a physical read-out, not just a flag: 2/S should
    # recover the ~1% the sweep was actually placed at, within a factor of 3.
    assert 0.003 < near.implied_detuning_fraction < 0.03, (
        f"implied detuning {near.implied_detuning_fraction:.4%} does not recover "
        "the 1% the sweep was placed at — the pole model is not describing this "
        "energy rise"
    )


@pytest.mark.integration
def test_guard_rejects_malformed_sweeps():
    """Input validation: the guard refuses to report on data it cannot read."""
    with pytest.raises(ValueError, match="at least two"):
        check_energy_continuity([1.0e8], [1.0])
    with pytest.raises(ValueError, match="match in length"):
        check_energy_continuity([1.0e8, 2.0e8], [1.0])
    with pytest.raises(ValueError, match="positive"):
        check_energy_continuity([1.0e8, 2.0e8], [1.0, 0.0])
