"""`TH-10` step 2: the first Larmor-regime full-wave solve gate (64 MHz).

Every coil-loading/SAR gate in this repo is either eddy-current (`MAT-6`,
10 MHz) or imposed-field (`MAT-4`); `TH-8` gates a *quasi-static* sphere at
``k₀R = 5e-3``.  Gelled saline at the Larmor frequencies is therefore an
**extrapolation** (§2.1), and `TH-10` step 1 put a number on its size: at
a = 0.05 m, εᵣ = 78, σ = 0.5 S/m, 64 MHz the full-wave interior field departs
from ``3E₀/(ε_c+2)`` by **102.3%**.  At these parameters ``σ/(ωε₀) = 140``
dominates ``εᵣ = 78``, so ``ε_c = 78 − j140`` and ``|m|k₀a = 0.850`` — the
quasi-static answer is not a correction away from the truth, it is a different
answer.

This gate drives the `sphere_in_box_domain` wall with the **series total**
exterior field (``LossySphereSeries.total_field``, gated 6/6 in step 1) and
measures the *interior* field, which nothing in the boundary data states.  The
same discriminator argument `TH-8` makes applies here and is stronger: the
interior field is set by ``ε_c`` acting through the mass term ``−k₀²ε_c E`` and
by the normal-``D`` jump at r = a, and it is 12.9× smaller than ``|E₀|``.

Two gates, both quantitative:

* **Positive** — interior relative L2 of ``E_FEM`` against the series is
  < 5% at the finer of two `TH-8`-class rungs, *and* decreasing rung to rung
  (`TH-1`'s plane-wave precedent measured 3.61% L2).
* **Negative control** — the quasi-static closed form on the *same* solved
  field.  Its departure from the series is on record at 102.3%, so the solve
  must sit at least **10×** closer to the series than to quasi-static.  A
  solver that had merely reproduced `TH-8` physics would fail this by
  construction; the ceiling at the 5% band is ≈ 20×.

The ``e^{+jωt}`` convention is load-bearing (`TH-1` formulation note): a solve
landing ~170% off matches the conjugated-convention signature step 1 recorded
at 173.8%, and that is a convention bug, not a solver bug.

Scope: 64 MHz only.  128 MHz is step 3, ½∫σ|E|² is step 4, and no `MAT-4` or
coil-loading claim follows from this file.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_lossy_sphere_fullwave.py -v -s'
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI
from petsc4py import PETSc

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import LossySphereSeries, complex_permittivity

from tests.complex_mode import complex_only

SPHERE_RADIUS = 0.05
BOX_HALF_WIDTH = 0.10
E0 = 1.0
SALINE_EPSILON_R = 78.0
SALINE_SIGMA = 0.5
FREQUENCY_HZ = 64.0e6
SPHERE_TAG = 1

# `TH-8`'s own two coarser recorded resolutions, carried over unchanged so the
# rungs are the ones the quasi-static gate is priced at (§9 item 1).
RESOLUTIONS = [(0.0125, 0.025), (0.00833, 0.0167)]

# Bounds are the §9 item-1 recipe's, stated before the run.
INTERIOR_L2_BOUND = 0.05
QUASISTATIC_SEPARATION = 10.0


def _series() -> LossySphereSeries:
    return LossySphereSeries(
        radius=SPHERE_RADIUS,
        epsilon_c=complex_permittivity(SALINE_EPSILON_R, SALINE_SIGMA, FREQUENCY_HZ),
        frequency_hz=FREQUENCY_HZ,
        e0=E0,
    )


def _dirichlet_total_field(series: LossySphereSeries):
    """Series total field in dolfinx interpolation convention, ``x`` is (3, n).

    ``total_field`` is piecewise (interior series inside r = a, incident +
    scattered outside), so the same callable is safe anywhere; the solver only
    reads it on the box wall, where it is the exact exterior solution.
    """

    def field(x: np.ndarray) -> np.ndarray:
        values = series.total_field(np.asarray(x).T)
        return np.ascontiguousarray(values.T, dtype=PETSc.ScalarType)

    return field


def _interior_probe_points() -> np.ndarray:
    """Fibonacci spirals on two interior shells plus one off-centre point.

    Identical construction to the `TH-8` fixture, deliberately: the two gates
    then measure the same interior region and the 102.3% departure step 1
    recorded on this very point set is directly comparable.
    """
    n_per_shell = 12
    points = [np.array([0.0031, -0.0027, 0.0043]) * SPHERE_RADIUS]
    indices = np.arange(n_per_shell) + 0.5
    phi = np.arccos(1.0 - 2.0 * indices / n_per_shell)
    theta = np.pi * (1.0 + 5.0**0.5) * indices
    for shell in (0.30, 0.55):
        rr = shell * SPHERE_RADIUS
        points.append(
            np.column_stack(
                [
                    rr * np.cos(theta) * np.sin(phi),
                    rr * np.sin(theta) * np.sin(phi),
                    rr * np.cos(phi),
                ]
            )
        )
    return np.vstack([np.atleast_2d(points[0]), points[1], points[2]])


def _rel_l2(a: np.ndarray, b: np.ndarray) -> float:
    """‖a − b‖₂ / ‖b‖₂ over the whole complex sample (all three components)."""
    return float(np.linalg.norm(a - b) / np.linalg.norm(b))


def _solve(series: LossySphereSeries, resolution_sphere: float, resolution_far: float):
    """One rung.  Returns ``(err_series, err_quasistatic, ncells)``."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = MeshGenerator.sphere_in_box_domain(
        sphere_radius=SPHERE_RADIUS,
        box_half_width=BOX_HALF_WIDTH,
        resolution_sphere=resolution_sphere,
        resolution_far=resolution_far,
        comm=comm,
    )

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0),
        cell_tags=cell_tags,
        material_map={
            SPHERE_TAG: HomogeneousMaterial(
                sigma=SALINE_SIGMA, epsilon_r=SALINE_EPSILON_R
            )
        },
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=_dirichlet_total_field(series),
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()

    points = _interior_probe_points()
    real_values, valid_real = evaluate_vector_field_parallel(fields.e_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(fields.e_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(
            f"{int((~valid).sum())} interior probe points were not evaluated"
        )
    e_fem = np.real(real_values) + 1j * np.real(imag_values)

    e_series = series.internal_field(points)
    e_quasistatic = np.zeros_like(e_series)
    e_quasistatic[:, 0] = series.quasistatic_internal_field()

    ncells = int(
        comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM)
    )
    return _rel_l2(e_fem, e_series), _rel_l2(e_fem, e_quasistatic), ncells


@complex_only
@pytest.mark.integration
def test_lossy_sphere_interior_field_matches_full_wave_series_at_64mhz():
    """Interior ``E`` matches `LossySphereSeries` to < 5% and improves with h."""
    comm = MPI.COMM_WORLD
    series = _series()

    runs = [_solve(series, hs, hf) for hs, hf in RESOLUTIONS]
    err_coarse, err_fine = runs[0][0], runs[-1][0]
    qs_fine = runs[-1][1]
    separation = qs_fine / err_fine if err_fine > 0.0 else np.inf

    # The reference's own departure from quasi-static, independent of any solve:
    # step 1 recorded 102.3% here on this same point set (max-norm; this is the
    # L2 restatement of it, printed so the two are never conflated).
    points = _interior_probe_points()
    e_series = series.internal_field(points)
    e_quasistatic = np.zeros_like(e_series)
    e_quasistatic[:, 0] = series.quasistatic_internal_field()
    series_vs_qs = _rel_l2(e_quasistatic, e_series)

    if comm.rank == 0:
        print(
            f"\n[TH-10 2] lossy saline sphere, full-wave, a = {SPHERE_RADIUS} m, "
            f"eps_r = {SALINE_EPSILON_R}, sigma = {SALINE_SIGMA} S/m, "
            f"f = {FREQUENCY_HZ / 1e6:.0f} MHz"
        )
        print(
            f"  eps_c = {series.epsilon_c:.6g}, m = {series.m:.6g}, "
            f"k0a = {series.size_parameter:.6g}, "
            f"|m|k0a = {abs(series.m) * series.size_parameter:.6g}, "
            f"N = {series.n_terms}, last-term bound = {series.last_term_bound():.3e}"
        )
        print(
            f"  reference: series vs quasi-static 3E0/(eps_c+2) = "
            f"{series_vs_qs:.3%} relL2 (step 1 recorded 102.3% in max-norm)"
        )
        for (hs, _), (err, qs, ncells) in zip(RESOLUTIONS, runs):
            print(
                f"  h_sphere = {hs:.5f} ({ncells:7d} cells): "
                f"relL2(FEM vs series) = {err:.3%}, "
                f"relL2(FEM vs quasi-static) = {qs:.3%}, "
                f"separation = {qs / err:.2f}x"
            )
        print(
            f"  plane-wave precedent (TH-1): 3.61% L2; "
            f"this gate: {err_fine:.3%} at the fine rung"
        )

    assert err_fine < err_coarse, (
        f"refinement did not improve the interior field: {err_coarse:.4%} -> "
        f"{err_fine:.4%}; without a decreasing sequence the level below is a "
        "coincidence, not convergence"
    )
    assert err_fine < INTERIOR_L2_BOUND, (
        f"interior E differs from the full-wave series by {err_fine:.2%} relL2, "
        f"over the {INTERIOR_L2_BOUND:.0%} band (PROJECT_PLAN §9 item 1, "
        f"§10 MVP criterion; TH-1's plane wave reached 3.61%). A miss near 170% "
        "is the conjugated-convention signature (step 1: 173.8%), not a solver "
        "defect — check the e^{+jwt} convention first"
    )
    assert separation > QUASISTATIC_SEPARATION, (
        f"the solve sits only {separation:.2f}x closer to the full-wave series "
        f"than to the quasi-static closed form (required > "
        f"{QUASISTATIC_SEPARATION:.0f}x). The series and quasi-static values "
        f"differ by {series_vs_qs:.1%} here, so a solve that could not tell them "
        "apart has not entered the Larmor regime at all"
    )
