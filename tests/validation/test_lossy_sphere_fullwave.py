"""`TH-10` steps 2-4: the Larmor-regime full-wave gates (64 and 128 MHz).

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

Step 3 repeats the identical recipe at 128 MHz, where ``|m|k₀a = 1.374`` and the
quasi-static departure step 1 recorded is larger still (**154.6%** in max-norm).
The interior wavelength shortens with ``|m|k₀``, so the resolution demand roughly
doubles: the 128 MHz rungs start at 64 MHz's *fine* rung and refine once from
there.  A 64 MHz green beside a 128 MHz red would itself be the frequency-scaling
finding — the two errors and rates are printed side by side for exactly that
reading.

Step 4 adds the **volume** gate the field gates do not imply: ½∫σ|E|² over the
sphere, the integral any Larmor-regime SAR number routes through.  Its
reference is the series interior field integrated over the *same meshed cells*
with the *same* σ field, so only ``E`` differs between the two integrals —
the meshed sphere carries 98.6% of the exact-ball power at the fine rung, and
folding that geometry defect into a 5% field band would have been a different
(weaker) test.  The exact-ball integral is computed independently in numpy and
printed beside it.

Scope: the interior field and the total ohmic power.  No mass averaging, no
C95.3 wording, no `MAT-4` or coil-loading claim follows from this file.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_lossy_sphere_fullwave.py -v -s'

Pass ``-k 64mhz`` or ``-k 128mhz`` to run one gate; each is priced separately
(§9 items 1 and 3) and neither depends on the other's solve.
"""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI
from petsc4py import PETSc

import dolfinx
from dolfinx import fem

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
FREQUENCY_64_HZ = 64.0e6
FREQUENCY_128_HZ = 128.0e6
SPHERE_TAG = 1

# `TH-8`'s own two coarser recorded resolutions, carried over unchanged so the
# rungs are the ones the quasi-static gate is priced at (§9 item 1).
RESOLUTIONS_64 = [(0.0125, 0.025), (0.00833, 0.0167)]
# Step 3 (§9 item 3): "start at item 1's fine rung plus one refinement" — the
# same 1.5× ladder `TH-8` uses, one rung further, because the interior
# wavelength scales with |m|k₀ and that roughly doubles from 64 to 128 MHz.
RESOLUTIONS_128 = [(0.00833, 0.0167), (0.00556, 0.0111)]

# Bounds are the §9 item-1 / item-3 recipes', stated before the run and
# identical at both frequencies — step 3 inherits step 2's band unchanged.
INTERIOR_L2_BOUND = 0.05
QUASISTATIC_SEPARATION = 10.0


def _series(frequency_hz: float) -> LossySphereSeries:
    return LossySphereSeries(
        radius=SPHERE_RADIUS,
        epsilon_c=complex_permittivity(SALINE_EPSILON_R, SALINE_SIGMA, frequency_hz),
        frequency_hz=frequency_hz,
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


def _mesh_and_solve(
    series: LossySphereSeries,
    resolution_sphere: float,
    resolution_far: float,
    degree: int = 1,
):
    """Mesh + solve one rung.  Returns ``(msh, cell_tags, fields, ncells)``.

    Steps 2/3 read only the interior field out of this; step 4 needs the mesh
    and the σ field as well, so the solve itself lives here and both gates run
    on demonstrably the same fixture rather than on two copies of it.

    ``degree`` is the N1curl order (`TH-12` step 1).  It defaults to 1, which is
    the order every recorded `TH-10` number was measured at — no gated result of
    this module moves when a degree-2 caller passes 2.
    """
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
        frequency_hz=series.frequency_hz,
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
    fields = TimeHarmonicSolver(problem, degree=degree).solve()
    ncells = int(
        comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM)
    )
    return msh, cell_tags, fields, ncells


def _solve(series: LossySphereSeries, resolution_sphere: float, resolution_far: float):
    """One rung.  Returns ``(err_series, err_quasistatic, ncells)``."""
    comm = MPI.COMM_WORLD
    _, _, fields, ncells = _mesh_and_solve(series, resolution_sphere, resolution_far)

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

    return _rel_l2(e_fem, e_series), _rel_l2(e_fem, e_quasistatic), ncells


def _run_gate(
    step_label: str,
    frequency_hz: float,
    resolutions: list[tuple[float, float]],
    quasistatic_max_norm_pct: float,
) -> float:
    """Both gates at one frequency.  Returns the fine-rung relL2 for reporting.

    Nothing here is frequency-specific except the printed labels: step 3 is
    step 2's recipe with ``frequency_hz`` and the rung ladder changed, which is
    the point — a difference in the measured error is then a statement about the
    physics, not about two hand-tuned fixtures.
    """
    comm = MPI.COMM_WORLD
    series = _series(frequency_hz)

    runs = [_solve(series, hs, hf) for hs, hf in resolutions]
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

    # Pairwise rate over the two rungs, printed for the frequency-scaling
    # comparison §9 item 3 asks for.  Both ladders step h by the same 1.5×, so
    # the two frequencies' rates are directly comparable.
    h_ratio = resolutions[0][0] / resolutions[-1][0]
    rate = float(np.log(err_coarse / err_fine) / np.log(h_ratio))

    if comm.rank == 0:
        print(
            f"\n[{step_label}] lossy saline sphere, full-wave, "
            f"a = {SPHERE_RADIUS} m, eps_r = {SALINE_EPSILON_R}, "
            f"sigma = {SALINE_SIGMA} S/m, f = {frequency_hz / 1e6:.0f} MHz"
        )
        print(
            f"  eps_c = {series.epsilon_c:.6g}, m = {series.m:.6g}, "
            f"k0a = {series.size_parameter:.6g}, "
            f"|m|k0a = {abs(series.m) * series.size_parameter:.6g}, "
            f"N = {series.n_terms}, last-term bound = {series.last_term_bound():.3e}"
        )
        print(
            f"  reference: series vs quasi-static 3E0/(eps_c+2) = "
            f"{series_vs_qs:.3%} relL2 (step 1 recorded "
            f"{quasistatic_max_norm_pct:.1f}% in max-norm — different norms, "
            f"never interchangeable)"
        )
        for (hs, _), (err, qs, ncells) in zip(resolutions, runs):
            print(
                f"  h_sphere = {hs:.5f} ({ncells:7d} cells): "
                f"relL2(FEM vs series) = {err:.3%}, "
                f"relL2(FEM vs quasi-static) = {qs:.3%}, "
                f"separation = {qs / err:.2f}x"
            )
        print(
            f"  plane-wave precedent (TH-1): 3.61% L2; "
            f"this gate: {err_fine:.3%} at the fine rung, "
            f"observed pairwise rate in h = {rate:.3f} "
            f"(read, not gated — the gate is the level and the direction)"
        )

    assert err_fine < err_coarse, (
        f"refinement did not improve the interior field: {err_coarse:.4%} -> "
        f"{err_fine:.4%}; without a decreasing sequence the level below is a "
        "coincidence, not convergence"
    )
    assert err_fine < INTERIOR_L2_BOUND, (
        f"interior E at {frequency_hz / 1e6:.0f} MHz differs from the full-wave "
        f"series by {err_fine:.2%} relL2, over the {INTERIOR_L2_BOUND:.0%} band "
        f"(PROJECT_PLAN §9, §10 MVP criterion; TH-1's plane wave reached 3.61%). "
        "A miss near 170% is the conjugated-convention signature (step 1: "
        "173.8%), not a solver defect — check the e^{+jwt} convention first"
    )
    assert separation > QUASISTATIC_SEPARATION, (
        f"the solve sits only {separation:.2f}x closer to the full-wave series "
        f"than to the quasi-static closed form (required > "
        f"{QUASISTATIC_SEPARATION:.0f}x). The series and quasi-static values "
        f"differ by {series_vs_qs:.1%} here, so a solve that could not tell them "
        "apart has not entered the Larmor regime at all"
    )
    return err_fine


# ---------------------------------------------------------------------------
# Step 4: the SAR-relevant volume integral, ½∫σ|E|² over the sphere.
# ---------------------------------------------------------------------------
#
# Steps 2/3 gate the interior field at 27 probe points; SAR is a *volume*
# functional of |E|², so the field gate does not imply this one — a solve can
# be right where it is sampled and carry its error in the volume, and squaring
# turns a signed field error into a one-signed power error.  Bounds (§9 item 5,
# stated before the run): FEM-vs-series total ohmic power < 5%, and the
# quasi-static uniform-field power route must miss by > 50% (a conservative
# floor — the interior *field* is 102.3% off in max-norm at 64 MHz, and power
# goes as |E|²).
OHMIC_POWER_BOUND = 0.05
QUASISTATIC_POWER_MISS_FLOOR = 0.50
# `MAT-4` step 2's measured degree, reused rather than re-tuned; the log prints
# the value and the degree-16 recomputation beside it (the "latent degree"
# lesson: a quadrature degree that is never stated is never checked).
REFERENCE_QUADRATURE_DEGREE = 12
REFERENCE_QUADRATURE_DEGREE_CHECK = 16


def _series_interior_interpolant(series: LossySphereSeries):
    """``internal_field`` in dolfinx interpolation convention, ``x`` is (3, n).

    The series is written in spherical coordinates and raises at ``r = 0``
    (a removable singularity it does not take the limit of).  The mesh has a
    node at the sphere centre, so those points are evaluated a nanometre off
    axis instead — |m|k₀·1e-9 ≈ 2e-8 rad, i.e. below round-off in the field.
    """

    def field(x: np.ndarray) -> np.ndarray:
        points = np.ascontiguousarray(np.asarray(x).T, dtype=np.float64)
        r = np.linalg.norm(points, axis=1)
        at_centre = r < 1.0e-12
        if np.any(at_centre):
            points = points.copy()
            points[at_centre, 0] = 1.0e-9
        values = series.internal_field(points)
        return np.ascontiguousarray(values.T, dtype=PETSc.ScalarType)

    return field


def _integrate_over_sphere(integrand, msh, cell_tags, comm, quadrature_degree: int):
    """``∫_sphere integrand dV``, allreduced.

    ``fem.assemble_scalar`` is rank-local (CLAUDE.md rank-safety rule); the
    reduction happens here so no caller can forget it.
    """
    dx = ufl.Measure(
        "dx",
        domain=msh,
        subdomain_data=cell_tags,
        metadata={"quadrature_degree": int(quadrature_degree)},
    )
    local = fem.assemble_scalar(fem.form(integrand * dx(SPHERE_TAG)))
    return complex(comm.allreduce(local, op=MPI.SUM))


def _ohmic_power(e_field, sigma_field, msh, cell_tags, comm, quadrature_degree: int):
    """``½∫σ|E|²dV`` over the meshed sphere [W].

    ``ufl.inner`` conjugates its second argument, so ``inner(E, E)`` is |E|²
    and the imaginary part is round-off, not a truncated quantity.
    """
    integrand = 0.5 * sigma_field * ufl.inner(e_field, e_field)
    return float(
        np.real(
            _integrate_over_sphere(integrand, msh, cell_tags, comm, quadrature_degree)
        )
    )


def _exact_sphere_series_power(series: LossySphereSeries, sigma: float, n_radial: int):
    """``½σ∫|E_series|²dV`` over the **exact** ball, by product Gauss quadrature.

    Independent of the mesh and of dolfinx: Gauss-Legendre in r (weighted r²)
    and in cosθ, uniform-trapezoid in φ (spectrally accurate, the integrand is
    periodic).  Printed as a read beside the meshed reference so a mesh-side
    defect (volume defect, interpolation, quadrature degree) is separable from
    a series-side one.
    """
    a = series.radius
    r_nodes, r_weights = np.polynomial.legendre.leggauss(n_radial)
    r = 0.5 * a * (r_nodes + 1.0)
    wr = 0.5 * a * r_weights * r**2
    mu_nodes, mu_weights = np.polynomial.legendre.leggauss(n_radial)
    n_phi = 2 * n_radial
    phi = 2.0 * np.pi * np.arange(n_phi) / n_phi
    w_phi = 2.0 * np.pi / n_phi

    sin_theta = np.sqrt(np.maximum(0.0, 1.0 - mu_nodes**2))
    rr, mm, pp = np.meshgrid(r, np.arange(mu_nodes.size), np.arange(n_phi), indexing="ij")
    points = np.column_stack(
        [
            (rr * sin_theta[mm] * np.cos(phi[pp])).ravel(),
            (rr * sin_theta[mm] * np.sin(phi[pp])).ravel(),
            (rr * mu_nodes[mm]).ravel(),
        ]
    )
    e = series.internal_field(points)
    e_sq = np.sum(np.abs(e) ** 2, axis=1).reshape(rr.shape)
    weights = wr[:, None, None] * mu_weights[None, :, None] * w_phi
    return float(0.5 * sigma * np.sum(weights * e_sq))


def _power_rung(series: LossySphereSeries, resolution_sphere: float, resolution_far: float):
    """One rung of the power gate.  Returns a dict of the three integrals."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, fields, ncells = _mesh_and_solve(
        series, resolution_sphere, resolution_far
    )

    p_fem = _ohmic_power(
        fields.e_complex,
        fields.sigma_field,
        msh,
        cell_tags,
        comm,
        REFERENCE_QUADRATURE_DEGREE,
    )

    # The series reference is integrated over the *same meshed region* with the
    # *same* σ field: the only thing that differs between p_fem and p_series is
    # E, which is what this gate is about.  The exact-ball value below carries
    # the geometry question separately.
    v_space = fem.functionspace(msh, ("Lagrange", 2, (3,)))
    e_series_fn = fem.Function(v_space, name="E_series")
    sphere_cells = np.asarray(
        cell_tags.indices[cell_tags.values == SPHERE_TAG], dtype=np.int32
    )
    # `OPS-18` step 3: dolfinx 0.11 renamed `interpolate`'s cell restriction
    # `cells` -> `cells0` (the source-mesh list is now `cells1`).
    e_series_fn.interpolate(_series_interior_interpolant(series), cells0=sphere_cells)
    p_series = _ohmic_power(
        e_series_fn,
        fields.sigma_field,
        msh,
        cell_tags,
        comm,
        REFERENCE_QUADRATURE_DEGREE,
    )
    p_series_check = _ohmic_power(
        e_series_fn,
        fields.sigma_field,
        msh,
        cell_tags,
        comm,
        REFERENCE_QUADRATURE_DEGREE_CHECK,
    )

    # Negative control: the quasi-static uniform interior field, x̂-directed,
    # integrated over the same region with the same σ.
    e_qs = series.quasistatic_internal_field()
    e_qs_vector = ufl.as_vector(
        [
            fem.Constant(msh, dolfinx.default_scalar_type(e_qs)),
            fem.Constant(msh, dolfinx.default_scalar_type(0.0)),
            fem.Constant(msh, dolfinx.default_scalar_type(0.0)),
        ]
    )
    p_quasistatic = _ohmic_power(
        e_qs_vector,
        fields.sigma_field,
        msh,
        cell_tags,
        comm,
        REFERENCE_QUADRATURE_DEGREE,
    )

    one = fem.Constant(msh, dolfinx.default_scalar_type(1.0))
    volume = float(
        np.real(
            _integrate_over_sphere(
                one, msh, cell_tags, comm, REFERENCE_QUADRATURE_DEGREE
            )
        )
    )

    return {
        "ncells": ncells,
        "p_fem": p_fem,
        "p_series": p_series,
        "p_series_check": p_series_check,
        "p_quasistatic": p_quasistatic,
        "volume": volume,
    }


@complex_only
@pytest.mark.integration
def test_lossy_sphere_ohmic_power_matches_full_wave_series_at_64mhz():
    """``½∫σ|E|²`` over the sphere matches the series integral to < 5%.

    This is the volume integral any Larmor-regime SAR number routes through
    (`MAT-4`).  It gates the integral only: no mass averaging, no C95.3
    wording, and `MAT-4`/`TH-10` both stay 🟡 on the strength of it.
    """
    comm = MPI.COMM_WORLD
    series = _series(FREQUENCY_64_HZ)

    rungs = [_power_rung(series, hs, hf) for hs, hf in RESOLUTIONS_64]
    for rung in rungs:
        rung["error"] = abs(rung["p_fem"] - rung["p_series"]) / rung["p_series"]
        rung["qs_miss"] = (
            abs(rung["p_quasistatic"] - rung["p_series"]) / rung["p_series"]
        )
    fine = rungs[-1]

    volume_exact = 4.0 / 3.0 * np.pi * SPHERE_RADIUS**3
    p_exact_ball = _exact_sphere_series_power(series, SALINE_SIGMA, n_radial=24)
    p_exact_ball_check = _exact_sphere_series_power(series, SALINE_SIGMA, n_radial=32)

    if comm.rank == 0:
        print(
            f"\n[TH-10 4] ohmic power in the lossy saline sphere, "
            f"a = {SPHERE_RADIUS} m, eps_r = {SALINE_EPSILON_R}, "
            f"sigma = {SALINE_SIGMA} S/m, f = {FREQUENCY_64_HZ / 1e6:.0f} MHz, "
            f"|m|k0a = {abs(series.m) * series.size_parameter:.6g}"
        )
        print(
            f"  reference (exact ball, numpy Gauss product quadrature): "
            f"P_series = {p_exact_ball:.9e} W "
            f"(n_radial 24 -> 32: {p_exact_ball_check:.9e} W, "
            f"drift {abs(p_exact_ball_check - p_exact_ball) / p_exact_ball:.2e})"
        )
        for (hs, _), rung in zip(RESOLUTIONS_64, rungs):
            print(
                f"  h_sphere = {hs:.5f} ({rung['ncells']:7d} cells): "
                f"P_FEM = {rung['p_fem']:.9e} W, "
                f"P_series(meshed) = {rung['p_series']:.9e} W "
                f"=> error {rung['error']:.3%}; "
                f"P_quasistatic = {rung['p_quasistatic']:.9e} W "
                f"=> miss {rung['qs_miss']:.3%}; "
                f"V_mesh/V_exact = {rung['volume'] / volume_exact:.6f}, "
                f"P_series(meshed)/P_series(exact ball) = "
                f"{rung['p_series'] / p_exact_ball:.6f}"
            )
        print(
            f"  quadrature degree {REFERENCE_QUADRATURE_DEGREE} "
            f"(the MAT-4 step-2 measured degree); recomputed at "
            f"{REFERENCE_QUADRATURE_DEGREE_CHECK} the meshed series power moves "
            f"{abs(fine['p_series_check'] - fine['p_series']) / fine['p_series']:.2e} "
            f"at the fine rung"
        )

    # The level is gated below; this gates the *trend* (§9 item 2a, added
    # 2026-08-15).  The recorded pair in
    # `20260813T170337Z_TH-10-step4-power-n2.log` is 8.387% (5 866 cells) ->
    # 3.629% (17 670 cells), so strict decrease across consecutive rungs is a
    # real constraint here, not a tautology: a level-only gate would still pass
    # if the coarse rung were the better one, which is the signature of a
    # cancellation rather than convergence.  Never adjust the recorded digits
    # to make this hold — a failure is a finding about the coarse record.
    for coarse, finer in zip(rungs[:-1], rungs[1:]):
        assert finer["error"] < coarse["error"], (
            f"ohmic-power error does not decrease under refinement: "
            f"{coarse['ncells']} cells gives {coarse['error']:.3%} but "
            f"{finer['ncells']} cells gives {finer['error']:.3%}. The level "
            f"gate below can still pass on a non-converging sequence; a total "
            f"integral that stops improving with h points at the integration "
            f"path or at error cancellation, not at a tighter bound"
        )

    assert fine["error"] < OHMIC_POWER_BOUND, (
        f"total ohmic power from the FEM solve is {fine['p_fem']:.6e} W against "
        f"the series integral {fine['p_series']:.6e} W over the same meshed "
        f"sphere — off by {fine['error']:.2%}, outside the "
        f"{OHMIC_POWER_BOUND:.0%} band (PROJECT_PLAN §9 item 5). The interior "
        f"*field* gate passes at this rung, so a miss here points at the "
        f"integration path — cell-tag restriction, measure, quadrature degree — "
        f"before it points at the solver"
    )
    assert fine["qs_miss"] > QUASISTATIC_POWER_MISS_FLOOR, (
        f"the quasi-static uniform-field power route gives "
        f"{fine['p_quasistatic']:.6e} W against the series "
        f"{fine['p_series']:.6e} W, a miss of only {fine['qs_miss']:.2%} — under "
        f"the {QUASISTATIC_POWER_MISS_FLOOR:.0%} floor. If quasi-statics can "
        f"reproduce this integral, the gate above is not discriminating between "
        f"a Larmor-regime solve and TH-8 physics"
    )


@complex_only
@pytest.mark.integration
def test_lossy_sphere_interior_field_matches_full_wave_series_at_64mhz():
    """Interior ``E`` matches `LossySphereSeries` to < 5% and improves with h."""
    _run_gate("TH-10 2", FREQUENCY_64_HZ, RESOLUTIONS_64, 102.3)


@complex_only
@pytest.mark.integration
def test_lossy_sphere_interior_field_matches_full_wave_series_at_128mhz():
    """Step 2's gate at the 3 T Larmor frequency, |m|k₀a = 1.374.

    Identical bounds to 64 MHz: step 3 buys nothing if it needs a wider band.
    The rungs are the only thing that moves, and only because the interior
    wavelength does.
    """
    _run_gate("TH-10 3", FREQUENCY_128_HZ, RESOLUTIONS_128, 154.6)
