"""Validation test: PEC rectangular-cavity resonances (TH-9).

Closed form for a box of edges ``a × b × d``::

    f_mnp = (c/2)·√((m/a)² + (n/b)² + (p/d)²)

with at most one index zero. This is the purest available gate on the
curl-curl and mass assembly — no materials, no sources, real scalar type — and
it is the fixture the `TH-1` resonance guard will be verified against.

Geometry: 1.0 × 0.8 × 0.6 m. The edges are deliberately non-commensurate so
the first four modes are non-degenerate and well separated (239.95, 291.35,
312.28, 346.40 MHz — the closest pair is 7% apart, and the fifth mode at
353.53 MHz sits 2% above the fourth, which is why the gate stops at four).
The band is MRI-adjacent.

Measured on 2026-07-30 at N1curl degree 2, mpiexec -n 2:

    divisions   cells   dofs    max |Δf|/f    per-mode error (%)
    (6, 5, 4)     720    5330      0.0436%     0.0123 0.0153 0.0201 0.0436
    (9, 7, 6)    2268   15998      0.0102%     0.0030 0.0025 0.0049 0.0102

i.e. every mode improves under the refinement and the max-error rate is 3.85
in h — consistent with the O(h^{2k}) eigenvalue convergence expected of
degree-2 edge elements.
"""

import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core.cavity import (
    analytic_cavity_frequencies,
    smallest_cavity_eigenvalues,
    solve_pec_cavity_modes,
)

EDGES = (1.0, 0.8, 0.6)
N_MODES = 4

# The gate stated in PROJECT_PLAN §7 TH-9. The measured value at the budgeted
# mesh is 0.0436%, two orders of magnitude inside it; the tolerance is kept at
# the specified 1% so the test remains a gate on assembly correctness rather
# than a lock on one mesh.
FREQUENCY_TOLERANCE_PCT = 1.0


@pytest.mark.validation
def test_pec_cavity_resonances_match_closed_form():
    """First four cavity resonances match ``f_mnp`` to < 1%."""

    comm = MPI.COMM_WORLD
    t0 = time.perf_counter()
    spectrum = solve_pec_cavity_modes(
        edges=EDGES, divisions=(6, 5, 4), degree=2, n_modes=N_MODES, comm=comm
    )
    elapsed = time.perf_counter() - t0

    analytic = analytic_cavity_frequencies(EDGES, N_MODES)
    rel_error_pct = 100.0 * np.abs(spectrum.frequencies_hz - analytic) / analytic

    if comm.rank == 0:
        print(
            f"\n[TH-9] cells={spectrum.n_cells} dofs={spectrum.n_dofs} "
            f"converged={spectrum.n_converged} null_modes_in_band="
            f"{spectrum.null_mode_count} elapsed={elapsed:.1f}s"
        )
        for f_num, f_exact, err in zip(spectrum.frequencies_hz, analytic, rel_error_pct):
            print(f"  {f_num/1e6:9.4f} MHz vs {f_exact/1e6:9.4f} MHz  ({err:.4f}%)")

    assert spectrum.frequencies_hz.size == N_MODES
    # No gradient mode leaked into the requested band: the shift-and-invert
    # target sits between the first and fourth physical eigenvalues, so the
    # cluster at zero is strictly farther from it than any mode of interest.
    assert spectrum.null_mode_count == 0, (
        f"{spectrum.null_mode_count} eigenvalues below the null cutoff "
        f"{spectrum.null_cutoff:.3e} were returned inside the physical band"
    )
    assert np.all(rel_error_pct < FREQUENCY_TOLERANCE_PCT), (
        f"cavity resonances off closed form by {rel_error_pct} % "
        f"(tolerance {FREQUENCY_TOLERANCE_PCT}%)"
    )


@pytest.mark.validation
def test_pec_cavity_resonances_improve_under_refinement():
    """Every mode's error shrinks under one refinement step, at rate > 2 in h."""

    comm = MPI.COMM_WORLD
    analytic = analytic_cavity_frequencies(EDGES, N_MODES)

    t0 = time.perf_counter()
    coarse = solve_pec_cavity_modes(
        edges=EDGES, divisions=(6, 5, 4), degree=2, n_modes=N_MODES, comm=comm
    )
    fine = solve_pec_cavity_modes(
        edges=EDGES, divisions=(9, 7, 6), degree=2, n_modes=N_MODES, comm=comm
    )
    elapsed = time.perf_counter() - t0

    err_coarse = np.abs(coarse.frequencies_hz - analytic) / analytic
    err_fine = np.abs(fine.frequencies_hz - analytic) / analytic
    rate = np.log(err_coarse.max() / err_fine.max()) / np.log(
        coarse.cell_size / fine.cell_size
    )

    if comm.rank == 0:
        print(
            f"\n[TH-9] refinement h={coarse.cell_size:.4f} -> {fine.cell_size:.4f}; "
            f"max err {err_coarse.max()*100:.4f}% -> {err_fine.max()*100:.4f}%; "
            f"rate={rate:.2f}; elapsed={elapsed:.1f}s"
        )

    assert np.all(err_fine < err_coarse), (
        f"refinement did not improve every mode: coarse={err_coarse}, fine={err_fine}"
    )
    # Degree-2 edge elements converge as O(h^4) in the eigenvalue; the measured
    # rate on 2026-07-30 was 3.85. The floor is set at 2.0 so a genuine loss of
    # order fails while mode-to-mode variation does not.
    assert rate > 2.0, f"observed eigenvalue convergence rate {rate:.2f} <= 2.0"


@pytest.mark.validation
def test_n1curl_gradient_modes_form_a_clean_zero_cluster():
    """The N1curl null space returns as machine zero, separated from mode 1.

    Counted, not skipped: the number of near-zero eigenvalues returned when the
    solver targets zero is itself the diagnostic. A curl-curl form with a sign
    error, or a mass matrix that is not the plain L² inner product, pollutes
    this cluster.
    """

    comm = MPI.COMM_WORLD
    n_values = 8
    t0 = time.perf_counter()
    values, lam_1 = smallest_cavity_eigenvalues(
        edges=EDGES, divisions=(6, 5, 4), degree=1, n_values=n_values, comm=comm
    )
    elapsed = time.perf_counter() - t0

    cutoff = 1e-8 * lam_1
    null_count = int(np.sum(np.abs(values) < cutoff))

    if comm.rank == 0:
        print(
            f"\n[TH-9] null cluster: {null_count}/{n_values} below "
            f"{cutoff:.3e} (k1^2={lam_1:.4f}); max|lambda|={np.abs(values).max():.3e}; "
            f"elapsed={elapsed:.1f}s"
        )

    assert null_count == n_values, (
        f"only {null_count} of {n_values} eigenvalues nearest zero are below the "
        f"{cutoff:.3e} cutoff: {values}"
    )
    # Separation from the physical spectrum, stated as a ratio rather than an
    # absolute: measured 2026-07-30 at ~3e-15, i.e. 13 orders of margin.
    assert np.abs(values).max() / lam_1 < 1e-8
