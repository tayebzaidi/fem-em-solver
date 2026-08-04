"""`POST-3` step 4: phasor-magnitude semantics for the phantom-field extraction.

``post/phantom_fields.py::_evaluate_on_cells`` used to cast every sample to
``float64`` at both of its evaluation sites, so under the complex build every
downstream phantom-field statistic was ``Re(E)`` at phase 0.  The fix is the
semantics, not the dtype: samples keep the function's own scalar type and the
statistics are taken on the **phasor magnitude** (§11 peak-phasor convention).

Two exact identities gate it, both on the piecewise-σ fixture from
``test_poynting_balance.py`` (σ = 0.1 | 1.4 S/m across x = L/2, complex solve):

1. *code-path equivalence* — the magnitudes ``phantom_fields`` reports equal
   ``|·|`` of the complex samples :func:`evaluate_vector_field_parallel`
   returns at the same points, to ``1e-12``;
2. *phase-rotation invariance* — every reported statistic is unchanged to
   ``1e-12`` when the solved ``Function`` is multiplied by ``e^{jπ/2}`` and by
   ``e^{jπ/5}``.

Neither can be satisfied by the ``Re``-cast, which is reproduced beside the fix
as the negative control.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/post/test_phantom_phasor_semantics.py -v -s'
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.post.phantom_fields import (
    _cell_centroids,
    _evaluate_on_cells,
    _sampling_cells_with_interface_guardrails,
    compute_tagged_vector_magnitude_stats,
)

from tests.complex_mode import complex_only
from tests.validation.test_lossy_plane_wave import EPSILON_R, FREQUENCY_HZ, MU_R, _exact_factory
from tests.validation.test_poynting_balance import (
    SIGMA_HIGH,
    SIGMA_LOW,
    TAG_HIGH,
    TAG_LOW,
    _two_material_mesh,
)

# One solve is enough for both identities; 12³ is the mesh the step-2 negative
# control already uses on this fixture (even n keeps the interface on a mesh
# plane), and no statement here depends on discretisation error.
FIXTURE_N = 12

# The identities are exact, so the tolerance is round-off, not physics.
IDENTITY_RTOL = 1e-12

ROTATION_ANGLES = (np.pi / 2.0, np.pi / 5.0)

# Negative control, banded from measurement (probe log
# 20260804T033354Z_POST-3-step4-probe.log).  The §7 plan's expectation was that
# the sampled phase would be roughly uniform, putting the ``Re``-cast deficit
# near 1 - 2/pi = 36.34% *at every* rotation angle and making the deficit, not
# its rotation variance, the load-bearing control.  Measurement says otherwise:
# the phase span over the σ_high slab's centroids is 1.2667 rad, about a fifth
# of a period, so the uniform-phase prediction does not apply here.  Measured
# instead: a 45.40% deficit at θ = 0, swinging to 20.48% at θ = π/2 and 75.91%
# at θ = π/5 — spread 0.554.  Both facts are therefore asserted, the second as a
# floor rather than the ceiling the plan anticipated: on this fixture the broken
# path is both badly wrong at phase 0 *and* wildly phase-dependent.  Bands are
# the measurements ±2 percentage points / a floor well under the measured
# spread, per the `GEO-9` step-1 precedent.
RE_CAST_DEFICIT_BAND = (0.4340, 0.4740)
RE_CAST_DEFICIT_ROTATION_SPREAD_MIN = 0.30
MEASURED_PHASE_SPAN_RAD = 1.2667


def _solve_two_material_fixture(n: int):
    """Solve the piecewise-σ box and return ``(E_complex, cell_tags)``.

    Mirrors ``test_poynting_balance._solve_two_material_and_balance`` up to the
    point where it scores the power balance; only the solved field is needed
    here.
    """
    msh, cell_tags = _two_material_mesh(n)
    solve_map = {
        TAG_LOW: HomogeneousMaterial(sigma=SIGMA_LOW, epsilon_r=EPSILON_R, mu_r=MU_R),
        TAG_HIGH: HomogeneousMaterial(sigma=SIGMA_HIGH, epsilon_r=EPSILON_R, mu_r=MU_R),
    }
    exact_numpy, _ = _exact_factory(SIGMA_LOW)
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=EPSILON_R, mu_r=MU_R),
        material_map=solve_map,
        cell_tags=cell_tags,
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=exact_numpy,
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()
    return fields.e_complex, cell_tags


def _module_samples(field, cell_tags, tag: int):
    """Rank-local ``(points, complex values)`` exactly as the module samples them."""
    mesh = field.function_space.mesh
    sampling_cells, _ = _sampling_cells_with_interface_guardrails(mesh, cell_tags, tag)
    points = _cell_centroids(mesh, sampling_cells)
    values, valid_points, _cells, _invalid = _evaluate_on_cells(field, points, sampling_cells)
    return valid_points, values


def _rotated_copy(field, theta: float):
    rotated = fem.Function(field.function_space)
    rotated.x.array[:] = field.x.array * np.exp(1j * theta)
    return rotated


def _global_mean(local_sum: float, local_count: int, comm) -> float:
    """Mean over all ranks — numerator and denominator reduced separately."""
    total = comm.allreduce(float(local_sum), op=MPI.SUM)
    count = comm.allreduce(int(local_count), op=MPI.SUM)
    assert count > 0, "no samples on any rank"
    return total / count


@pytest.fixture(scope="module")
def piecewise_sigma_field():
    return _solve_two_material_fixture(FIXTURE_N)


@complex_only
@pytest.mark.integration
def test_reported_magnitudes_match_the_complex_sampling_helper(piecewise_sigma_field):
    """Identity 1: the module's magnitudes are ``|·|`` of the complex samples.

    ``evaluate_vector_field_parallel`` is the project's rank-safe evaluator and
    already follows the function's own dtype; agreement to ``1e-12`` at the same
    points is what says ``phantom_fields`` now carries the phasor rather than
    its real part.  The ``Re``-cast the fix removes is printed beside it.
    """
    comm = MPI.COMM_WORLD
    e_field, cell_tags = piecewise_sigma_field

    points, values = _module_samples(e_field, cell_tags, TAG_HIGH)
    assert np.iscomplexobj(values), (
        "phantom_fields returned real samples on the complex build — the "
        "float64 cast is back"
    )
    module_mags = np.abs(np.linalg.norm(values, axis=1))

    # Same points, independent code path.  Every rank gets the full point list
    # so the helper's own gather/bcast returns values for all of them.
    gathered_points = comm.allgather(points)
    all_points = np.vstack([p for p in gathered_points if p.shape[0] > 0])
    ref_values, valid_mask = evaluate_vector_field_parallel(e_field, all_points)
    assert bool(np.all(valid_mask)), (
        f"{int((~valid_mask).sum())} of {valid_mask.size} centroids were not "
        "located by the reference evaluator"
    )

    offset = int(sum(p.shape[0] for p in gathered_points[: comm.rank]))
    mine = ref_values[offset : offset + points.shape[0]]
    ref_mags = np.abs(np.linalg.norm(mine, axis=1))

    if module_mags.size > 0:
        rel = np.abs(module_mags - ref_mags) / np.maximum(np.abs(ref_mags), 1e-300)
        local_worst = float(np.max(rel))
    else:
        local_worst = 0.0
    worst = comm.allreduce(local_worst, op=MPI.MAX)

    re_cast_mags = np.linalg.norm(values.real, axis=1)
    mean_honest = _global_mean(float(np.sum(module_mags)), module_mags.size, comm)
    mean_re_cast = _global_mean(float(np.sum(re_cast_mags)), re_cast_mags.size, comm)

    n_samples = comm.allreduce(int(module_mags.size), op=MPI.SUM)
    if comm.rank == 0:
        print(
            f"\n[POST-3 step 4] identity 1, tag {TAG_HIGH}, {n_samples} centroid samples:"
        )
        print(f"  worst relative disagreement vs evaluate_vector_field_parallel: {worst:.3e}")
        print(f"  mean |E| (phasor)  = {mean_honest:.6e}")
        print(f"  mean |Re E| (old)  = {mean_re_cast:.6e}")
        print(f"  Re-cast deficit    = {1.0 - mean_re_cast / mean_honest:.4%}")

    assert worst < IDENTITY_RTOL, (
        f"phantom_fields magnitudes disagree with |evaluate_vector_field_parallel| "
        f"by {worst:.3e} (> {IDENTITY_RTOL:.0e}) at the same centroids: the two "
        "sampling paths do not agree about what was solved"
    )


@complex_only
@pytest.mark.integration
def test_reported_statistics_are_phase_rotation_invariant(piecewise_sigma_field):
    """Identity 2: ``E → E e^{jθ}`` moves no reported statistic.

    A global phase rotation is unobservable in a time-harmonic problem, so every
    magnitude statistic must be exactly invariant.  The ``Re``-cast cannot be:
    it reports ``|Re(E e^{jθ})|``, which depends on θ.
    """
    comm = MPI.COMM_WORLD
    e_field, cell_tags = piecewise_sigma_field

    base = compute_tagged_vector_magnitude_stats(e_field, cell_tags, TAG_HIGH, comm=comm)

    if comm.rank == 0:
        print("\n[POST-3 step 4] identity 2, phase-rotation invariance:")
        print(
            f"  theta = 0        : min/max/mean = {base['min']:.9e} / "
            f"{base['max']:.9e} / {base['mean']:.9e}"
        )

    for theta in ROTATION_ANGLES:
        rotated_field = _rotated_copy(e_field, theta)
        rotated = compute_tagged_vector_magnitude_stats(
            rotated_field, cell_tags, TAG_HIGH, comm=comm
        )
        if comm.rank == 0:
            print(
                f"  theta = {theta:.6f} : min/max/mean = {rotated['min']:.9e} / "
                f"{rotated['max']:.9e} / {rotated['mean']:.9e}"
            )
        for key in ("min", "max", "mean"):
            assert np.isclose(base[key], rotated[key], rtol=IDENTITY_RTOL, atol=0.0), (
                f"reported '{key}' moved from {base[key]:.12e} to {rotated[key]:.12e} "
                f"under a global phase rotation of {theta:.6f} rad — the statistic "
                "is not taken on the phasor magnitude"
            )
        assert rotated["count"] == base["count"]


@complex_only
@pytest.mark.integration
def test_re_cast_negative_control_is_wrong_by_the_measured_deficit(piecewise_sigma_field):
    """Negative control: the old ``Re``-cast, reproduced beside the fix.

    Measured rather than predicted (see ``RE_CAST_DEFICIT_BAND``): this
    fixture's sampled phase spans only ~1.27 rad, so the plan's uniform-phase
    ``1 - 2/π`` expectation does not describe it.  What it does show is a 45.4%
    deficit at θ = 0 that swings across 20%–76% under rotations which cannot be
    observable — so here both the value *and* its phase dependence separate the
    broken path from the fixed one, and both are asserted.  On an in-phase field
    the deficit would go to zero at θ = 0, which is how this bug survived
    `TH-8`; the phase span is printed so a future fixture change is visible
    rather than silent.
    """
    comm = MPI.COMM_WORLD
    e_field, cell_tags = piecewise_sigma_field

    deficits = []
    for theta in (0.0,) + ROTATION_ANGLES:
        field = e_field if theta == 0.0 else _rotated_copy(e_field, theta)
        _points, values = _module_samples(field, cell_tags, TAG_HIGH)
        honest = np.abs(np.linalg.norm(values, axis=1))
        re_cast = np.linalg.norm(values.real, axis=1)
        mean_honest = _global_mean(float(np.sum(honest)), honest.size, comm)
        mean_re_cast = _global_mean(float(np.sum(re_cast)), re_cast.size, comm)
        deficits.append(1.0 - mean_re_cast / mean_honest)

    # Phase span of the samples, taken on each sample's dominant component so a
    # near-zero component's noisy argument does not widen it artificially.
    _points, values = _module_samples(e_field, cell_tags, TAG_HIGH)
    if values.shape[0] > 0:
        dominant = np.argmax(np.abs(values), axis=1)
        phases = np.angle(values[np.arange(values.shape[0]), dominant])
        local_lo, local_hi = float(np.min(phases)), float(np.max(phases))
    else:
        local_lo, local_hi = float("inf"), float("-inf")
    phase_lo = comm.allreduce(local_lo, op=MPI.MIN)
    phase_hi = comm.allreduce(local_hi, op=MPI.MAX)
    phase_span = phase_hi - phase_lo

    spread = float(max(deficits) - min(deficits))

    if comm.rank == 0:
        print("\n[POST-3 step 4] negative control, Re-cast against the phasor magnitude:")
        for theta, deficit in zip((0.0,) + ROTATION_ANGLES, deficits):
            print(f"  theta = {theta:.6f} : mean|Re E|/mean|E| deficit = {deficit:.4%}")
        print(f"  deficit spread across rotations: {spread:.5f}")
        print(
            f"  sampled phase span: {phase_span:.4f} rad "
            f"(measured at band time {MEASURED_PHASE_SPAN_RAD}; 2*pi = {2 * np.pi:.4f})"
        )
        print(f"  uniform-phase prediction 1 - 2/pi = {1.0 - 2.0 / np.pi:.4%} (does not apply here)")

    lo, hi = RE_CAST_DEFICIT_BAND
    assert lo < deficits[0] < hi, (
        f"the Re-cast path's deficit against the phasor magnitude is "
        f"{deficits[0]:.4%}, outside the measured band [{lo:.2%}, {hi:.2%}] — "
        "either the fixture's phase distribution moved or the control is no "
        "longer reproducing the old behaviour"
    )
    assert spread > RE_CAST_DEFICIT_ROTATION_SPREAD_MIN, (
        f"the broken path's deficit moved by only {spread:.5f} across the "
        f"rotations, under the measured {RE_CAST_DEFICIT_ROTATION_SPREAD_MIN} "
        "floor: on this fixture the Re-cast is strongly phase-dependent, so a "
        "small spread means the control is no longer reproducing it"
    )
