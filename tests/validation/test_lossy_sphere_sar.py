"""`MAT-4` step 1: SAR in a lossy sphere, against the quasi-static closed form.

This is the `TH-8` dielectric-sphere gate continued onto the **imaginary axis of
ε_c**.  `TH-8` runs at σ = 0 and asserts ``|Im E_z|/|Re E_z| < 1e-6`` — i.e. it
gates the lossless path and nothing else.  Here the same closed form is used
with complex permittivity,

    ε_c = εᵣ − j σ/(ωε₀)        (the ``e^{+jωt}`` convention of
                                 ``core/time_harmonic.py``'s mass term)
    E_in = 3 E₀ / (ε_c + 2)      — still uniform, now complex
    SAR  = σ |E_in|² / (2ρ) = σ · 9E₀²/|ε_c+2|² / (2ρ)      [W/kg]

and the **mean SAR over the sphere** is gated against that value at two σ and
two mesh resolutions.  The exterior (uniform + dipole) solution with complex
β = (ε_c−1)/(ε_c+2) is imposed on the box wall, exactly as in `TH-8`; nothing
in the boundary data states the interior value, so the interior SAR is a
quantity the solver is free to get wrong.

**Operating point (PROJECT_PLAN §7 `MAT-4`, control ceiling computed
2026-08-02).**  f = 64 MHz, R = 0.01 m, εᵣ = 78, σ = 0.05 / 0.57 S/m.  With
t ≡ σ/(ωε₀): t₁ = 14.0, t₂ = 160.  The point is chosen so the two-σ control
separates while quasi-statics still holds — ``|k_in|R = k₀√|ε_c| R = 0.179`` at
the lossy end, so the retardation the closed form drops is O((k_in R)²) ≈ 3.2%
in the field and ≈ 6% in SAR, which is the floor these bounds sit above.  Both
numbers are printed by the test rather than trusted.

**Negative control — the two-σ ratio, not a σ-blind solve.**  A solver blind to
σ returns E_in = 3E₀/(εᵣ+2) whatever σ is, so scoring it with the honest σ
inflates SAR by only ``((εᵣ+2)²+t²)/(εᵣ+2)² = 2.50`` at the saline point: a
direction check, not a gate.  The ratio between the two σ separates much
harder.  A σ-blind solver returns SAR₂/SAR₁ = σ₂/σ₁ = 11.40 **exactly**,
because E never moves; the honest solver returns
``(σ₂/σ₁)·|ε_c1+2|²/|ε_c2+2|² = 2.35``.  The ceiling on that separation is
``((εᵣ+2)²+t₂²)/((εᵣ+2)²+t₁²) = 4.86``, so the test asserts > 3 — below the
ceiling, never a round number chosen first.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_lossy_sphere_sar.py -v'
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
from fem_em_solver.post.sar import mean_sar, uniform_sphere_sar_closed_form
from fem_em_solver.utils.constants import EPSILON_0, MU_0

from tests.complex_mode import complex_only

# Geometry and drive.  R and f both move relative to `TH-8` (R = 0.05 m,
# k₀R = 5e-3): the two-σ control needs t₂ ≫ εᵣ+2, which inflates |ε_c| and
# therefore |k_in|R, so the sphere has to shrink to stay quasi-static.
SPHERE_RADIUS = 0.01
BOX_HALF_WIDTH = 0.02
E0 = 1.0
EPSILON_R_SPHERE = 78.0
SPHERE_TAG = 1

FREQUENCY_HZ = 64.0e6
RHO_KG_M3 = 1000.0  # water-like; `MAT-4` step 2 makes ρ a field
SIGMA_LOW = 0.05
SIGMA_HIGH = 0.57

OMEGA = 2.0 * np.pi * FREQUENCY_HZ
SPEED_OF_LIGHT = 1.0 / np.sqrt(MU_0 * EPSILON_0)
K0 = OMEGA / SPEED_OF_LIGHT


def _epsilon_c(sigma: float) -> complex:
    """``ε_c = εᵣ − jσ/(ωε₀)`` — the same expression the solver assembles."""
    return complex(EPSILON_R_SPHERE, -sigma / (OMEGA * EPSILON_0))


def _interior_field_closed_form(sigma: float) -> complex:
    return 3.0 * E0 / (_epsilon_c(sigma) + 2.0)


def _k_in_r(sigma: float) -> float:
    """``|k_in|R`` with ``k_in = k₀√ε_c`` — the quasi-static validity number."""
    return float(K0 * np.sqrt(abs(_epsilon_c(sigma))) * SPHERE_RADIUS)


def _exact_exterior_numpy(sigma: float):
    """Complex Dirichlet data on the box wall, dolfinx convention (3, n).

    Identical in form to `TH-8`'s, with β and E_in complex.  Written piecewise
    for all r so the callable can be probed anywhere.
    """
    epsilon_c = _epsilon_c(sigma)
    beta = (epsilon_c - 1.0) / (epsilon_c + 2.0)
    e_in = _interior_field_closed_form(sigma)
    R = SPHERE_RADIUS

    def field(x: np.ndarray) -> np.ndarray:
        r = np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
        r_safe = np.where(r > 0.0, r, 1.0)
        z = x[2]
        common = beta * E0 * R**3 / r_safe**5
        ex_out = common * 3.0 * z * x[0]
        ey_out = common * 3.0 * z * x[1]
        ez_out = E0 + common * (3.0 * z * z - r_safe**2)

        inside = r < R
        ex = np.where(inside, 0.0, ex_out)
        ey = np.where(inside, 0.0, ey_out)
        ez = np.where(inside, e_in, ez_out)
        return np.array([ex, ey, ez], dtype=PETSc.ScalarType)

    return field


def _interior_probe_points() -> np.ndarray:
    """Fibonacci shells at 0.30 R and 0.55 R plus an off-centre point.

    Same construction as `TH-8`: uniformity is a spatial claim, so the probe
    spans the interior rather than one line through it.
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


def _solve_lossy_sphere(sigma: float, resolution_sphere: float, resolution_far: float):
    """Solve at conductivity ``sigma`` and return the SAR/field measurements."""
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
            SPHERE_TAG: HomogeneousMaterial(sigma=sigma, epsilon_r=EPSILON_R_SPHERE)
        },
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=_exact_exterior_numpy(sigma),
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()

    # SAR straight from the N1curl solution in UFL, as an exact volume integral
    # rather than centroid samples.  (Before `POST-3` step 4 there was a second
    # reason: post/phantom_fields.py cast away Im(E), which on a lossy sphere is
    # most of the field.  That cast is fixed; the integral-vs-samples reason
    # stands.)
    sar = mean_sar(
        fields.e_complex,
        sigma=fields.sigma_field,
        rho=RHO_KG_M3,
        cell_tags=cell_tags,
        subdomain_ids=SPHERE_TAG,
        comm=comm,
    )

    points = _interior_probe_points()
    real_values, valid_real = evaluate_vector_field_parallel(fields.e_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(fields.e_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(f"{int((~valid).sum())} interior probe points were not evaluated")

    ez = np.real(real_values[:, 2]) + 1j * np.real(imag_values[:, 2])
    ez_mean = complex(np.mean(ez))

    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    return {
        "sigma": sigma,
        "mean_sar": sar["mean_sar_w_per_kg"],
        "sphere_volume_m3": sar["volume_m3"],
        "dissipated_power_w": sar["dissipated_power_w"],
        "ez_mean": ez_mean,
        "ez_spread": float(np.max(np.abs(ez - ez_mean)) / abs(ez_mean)),
        "ncells": int(ncells),
    }


@complex_only
@pytest.mark.integration
def test_lossy_sphere_mean_sar_matches_closed_form():
    """Mean SAR equals ``σ|3E₀/(ε_c+2)|²/(2ρ)`` at two σ and improves with h."""
    comm = MPI.COMM_WORLD
    resolutions = [
        (SPHERE_RADIUS / 6.0, SPHERE_RADIUS / 3.0),
        (SPHERE_RADIUS / 10.0, SPHERE_RADIUS / 5.0),
    ]
    sigmas = (SIGMA_LOW, SIGMA_HIGH)

    closed = {
        s: uniform_sphere_sar_closed_form(
            e0=E0,
            epsilon_r=EPSILON_R_SPHERE,
            sigma=s,
            omega=OMEGA,
            rho=RHO_KG_M3,
            epsilon_0=EPSILON_0,
        )
        for s in sigmas
    }
    runs = {
        (s, i): _solve_lossy_sphere(s, hs, hf)
        for s in sigmas
        for i, (hs, hf) in enumerate(resolutions)
    }
    errors = {
        key: abs(run["mean_sar"] - closed[key[0]]["sar_w_per_kg"]) / closed[key[0]]["sar_w_per_kg"]
        for key, run in runs.items()
    }

    # Analytic sphere volume: the mean is ∫σ|E|²/(2ρ)dV over the *meshed*
    # sphere, so a mesh that under-resolves the surface changes the denominator
    # as well as the field, and the volume defect belongs in the report.
    volume_exact = 4.0 / 3.0 * np.pi * SPHERE_RADIUS**3

    fine = 1
    ratio_fem = runs[(SIGMA_HIGH, fine)]["mean_sar"] / runs[(SIGMA_LOW, fine)]["mean_sar"]
    ratio_closed = closed[SIGMA_HIGH]["sar_w_per_kg"] / closed[SIGMA_LOW]["sar_w_per_kg"]
    ratio_blind = SIGMA_HIGH / SIGMA_LOW  # what a σ-blind solver returns, exactly
    separation = ratio_blind / ratio_fem
    separation_ceiling = ratio_blind / ratio_closed

    if comm.rank == 0:
        print(
            f"\n[MAT-4] lossy sphere, R = {SPHERE_RADIUS} m, eps_r = {EPSILON_R_SPHERE}, "
            f"f = {FREQUENCY_HZ / 1e6:.3f} MHz, rho = {RHO_KG_M3} kg/m^3"
        )
        for s in sigmas:
            c = closed[s]
            print(
                f"  sigma = {s:.3f} S/m: t = sigma/(w*eps0) = {c['loss_tangent_numerator']:.2f}, "
                f"|eps_c| = {c['epsilon_c_magnitude']:.2f}, |k_in|R = {_k_in_r(s):.4f}, "
                f"closed-form |E_in| = {c['e_in_magnitude']:.6f} V/m, "
                f"SAR = {c['sar_w_per_kg']:.6e} W/kg"
            )
            for i, (hs, _) in enumerate(resolutions):
                run = runs[(s, i)]
                e_in = _interior_field_closed_form(s)
                print(
                    f"    h_sphere = {hs:.5f} ({run['ncells']:6d} cells): "
                    f"mean SAR = {run['mean_sar']:.6e} ({errors[(s, i)]:.3%}), "
                    f"|E_z| = {abs(run['ez_mean']):.6f} (closed {abs(e_in):.6f}), "
                    f"Im/Re E_z = {run['ez_mean'].imag / run['ez_mean'].real:.4f} "
                    f"(closed {e_in.imag / e_in.real:.4f}), "
                    f"spread = {run['ez_spread']:.3%}, "
                    f"V_mesh/V_exact = {run['sphere_volume_m3'] / volume_exact:.6f}"
                )
        print(
            f"  two-sigma control: FEM SAR2/SAR1 = {ratio_fem:.4f}, closed form "
            f"{ratio_closed:.4f}, sigma-blind {ratio_blind:.4f} "
            f"=> separation {separation:.3f} (ceiling {separation_ceiling:.3f})"
        )

    # Bounds.  The closed form itself drops O((k_in R)²) ≈ 3.2% in the field at
    # σ = 0.57 S/m, i.e. ≈ 6% in SAR, so 10% is the model floor plus room for
    # the P1 discretisation — not a fitted tolerance.  Refinement is asserted
    # separately, which is the part a wrong-but-consistent SAR cannot fake.
    for s in sigmas:
        assert errors[(s, fine)] < 0.10, (
            f"mean SAR at sigma = {s} S/m is {runs[(s, fine)]['mean_sar']:.6e} W/kg "
            f"against the closed form {closed[s]['sar_w_per_kg']:.6e} W/kg, off by "
            f"{errors[(s, fine)]:.2%} — over the 10% bound "
            f"(|k_in|R = {_k_in_r(s):.3f}, so the closed form is good to ~6% in SAR)"
        )
        assert errors[(s, fine)] < errors[(s, 0)], (
            f"refinement did not improve the mean SAR at sigma = {s} S/m: "
            f"{errors[(s, 0)]:.4%} -> {errors[(s, fine)]:.4%}"
        )
        assert runs[(s, fine)]["ez_spread"] < 0.02, (
            f"interior field at sigma = {s} S/m is not uniform: spread "
            f"{runs[(s, fine)]['ez_spread']:.2%} inside 0.55 R, where the closed "
            "form is constant"
        )

    # The imaginary axis itself: Im/Re of the interior E_z is t/(εᵣ+2) in the
    # closed form (0.176 and 2.001 here).  `TH-8` measures this quantity as
    # exactly 0; a solver that dropped −jσ/(ωε₀) from ε_c would too, while still
    # passing a magnitude-only SAR check to within the σ-blind control's 2.5×.
    for s in sigmas:
        e_in = _interior_field_closed_form(s)
        expected_phase_ratio = e_in.imag / e_in.real
        measured = runs[(s, fine)]["ez_mean"]
        measured_phase_ratio = measured.imag / measured.real
        phase_error = abs(measured_phase_ratio - expected_phase_ratio) / abs(expected_phase_ratio)
        assert phase_error < 0.10, (
            f"Im/Re of the interior E_z at sigma = {s} S/m is "
            f"{measured_phase_ratio:.4f} against the closed-form "
            f"{expected_phase_ratio:.4f} ({phase_error:.2%}) — the loss term of "
            "eps_c is not entering the interior field correctly"
        )

    # Negative control: a σ-blind solve returns SAR₂/SAR₁ = σ₂/σ₁ exactly.  The
    # ceiling on the separation is ((εᵣ+2)²+t₂²)/((εᵣ+2)²+t₁²) = 4.86, so 3 is
    # a bound under the ceiling rather than a round number chosen first.
    assert separation > 3.0, (
        f"the two-sigma SAR ratio {ratio_fem:.4f} sits only {separation:.3f}x from "
        f"the sigma-blind {ratio_blind:.4f}; the closed form says {ratio_closed:.4f} "
        f"(ceiling {separation_ceiling:.3f}) — E is not responding to sigma"
    )
