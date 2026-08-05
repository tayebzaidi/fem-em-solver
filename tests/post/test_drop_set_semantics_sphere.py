"""`POST-1` step 3: does the interface drop set help or hurt on a *solved* field?

Steps 1 and 2 made the interface guardrail partition invariant; neither asked
whether discarding the interface-adjacent layer of a tagged region **improves**
a statistic against a known answer.  Nothing in the repo has ever compared what
survives the guardrail with an analytic interface field, so `POST-1`'s ⚠️ is
still a semantics question, not a defect: ``prefer_interior=True`` drops 234 of
5073 tag-1 cells but 234 of 385 tag-2 cells on the minority-tag rank of the
piecewise-σ fixture, and "the guardrail is rank-safe" says nothing about
whether the surviving mean is the better number.

The fixture is the one solved field in the repo with a closed-form **interior**
value: the `TH-8` dielectric sphere, ``|E_in| = 3/(ε + 2) · E₀``, uniform inside
``r < R``, gated to 2.44% on 2026-07-31.  Its constants, its exact exterior
Dirichlet data and its material map are imported from
``tests/validation/test_dielectric_sphere.py`` rather than restated (`MAT-6`
step 3's method note); only the *return* differs — this module needs the mesh,
the cell tags and the field object, which the `TH-8` helper reduces away.

Three statistics of the phasor magnitude ``|E|`` over the sphere tag are scored
against that closed form:

* **(a)** ``prefer_interior=True`` — the guardrail's surviving set, i.e. what
  production reports today;
* **(b)** the full owned tagged set — every sphere cell, interface layer
  included;
* **(c)** the drop set alone — exactly the cells (a) discards.

**Anchor.** The closed form itself.  (a) is gated at a probe-measured band that
sits inside `TH-8`'s own 5% tolerance, and the partition of the tagged set is
gated as an exact integer identity, ``|interior| + |drop| = |tagged|``
globally, at whatever rank count CI runs.  The **(a)-vs-(b) comparison is
printed and reported, never gated** — the review adjudicates the semantics from
the numbers, and a test that asserted a preference would be picking the
statistic that flatters it.

**Negative control, and what the probe actually measured.**  (c) samples
exactly the smeared interface discontinuity — the sphere's ``ε = 78`` jump,
where the true field steps by a factor of 26.7 — so the plan expected its error
against the *interior* closed form to be the separation scale of the whole
experiment.  It is not.  Probe
``20260805T183210Z_POST-1-step3-probe.log`` (``-n 2``, 4.48 s, h = 0.00833):

===  =========================  =====  ========  ==========================
set  description                n      mean      error vs 3/(ε+2)E₀ = 0.0375
===  =========================  =====  ========  ==========================
(a)  ``prefer_interior=True``   3327   0.039095  4.253%
(b)  full owned tagged set      4431   0.039099  4.263%
(c)  drop set alone             1104   0.039110  4.293%
===  =========================  =====  ========  ==========================

The three **means** agree to 0.04% of each other; the drop set's error exceeds
the surviving set's by a factor of 1.009.  So on this field the interface layer
is *not* biased against the interior closed form, and dropping it moves the
reported mean by 0.01 percentage points — 1/400th of the error itself.  The
4.25% is discretisation of the bulk, which the guardrail cannot touch.

Where the layer does separate is the **spread**: the surviving set spans
``[0.035692, 0.043769]`` and the full set ``[0.033788, 0.044560]`` — the full
set's minimum *and* maximum both come from the drop layer, and the full range
is 1.334× the surviving range.  That is the measured separation this module
asserts (against a 1.2 ceiling read off the probe, per `POST-3` step 2's rule),
because it is the one that exists.  A guardrail that ate the interface layer to
protect a *mean* is solving a problem this fixture does not have; protecting an
**extremum** is a different claim, and SAR peaks are extrema.

Every number above reproduces to the last printed digit at ``-n 4``
(``20260805T183344Z_POST-1-step3-gate-n4.log``), which is what steps 1 and 2
bought: the classification and all three statistics are partition invariant, so
the comparison the review adjudicates is a property of the field rather than of
the rank count.

**Caveat this module records rather than resolves.** The sphere boundary is
curved, so chordal geometry error lives in the same cell layer the semantics
question is about.  Per-class cell counts are printed so a later reader can
tell the two effects apart; this step does not separate them.

**Does not close `POST-1`.**  It puts real numbers under the symbol.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/post/test_drop_set_semantics_sphere.py -v -s'
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.phantom_fields import (
    _cell_centroids,
    _evaluate_on_cells,
    _interior_tagged_cells,
    _tagged_cells,
    compute_tagged_vector_magnitude_stats,
)

from tests.complex_mode import complex_only
from tests.validation.test_dielectric_sphere import (
    BOX_HALF_WIDTH,
    EPSILON_R_SPHERE,
    FREQUENCY_HZ,
    SPHERE_RADIUS,
    SPHERE_TAG,
    _exact_exterior_numpy,
    interior_field_closed_form,
)

# `TH-8`'s middle resolution: the one its own negative control uses, and the
# coarsest mesh whose interior error is inside the 5% MVP bar.
RESOLUTION_SPHERE = 0.00833
RESOLUTION_FAR = 0.0167

# Probe-measured band for the guardrail's surviving mean, ±0.5 percentage points
# around the 4.253% of ``20260805T183210Z_POST-1-step3-probe.log``.  The upper
# end sits inside `TH-8`'s own 5% MVP tolerance on the same fixture, so this
# gate can never pass a field `TH-8` would reject.  The band moves only with a
# recorded measurement (`MAG-10`/`MAG-15` precedent), never to rescue a run.
SURVIVING_ERROR_BAND = (0.0375, 0.0475)

# Ceiling for the one separation the probe found: the full tagged set's spread
# is 1.334× the surviving set's, because both extrema live in the drop layer.
# 1.2 is a floor under that measurement, not a fit to it.
MIN_RANGE_RATIO = 1.2


def _solve_sphere_fields(resolution_sphere: float, resolution_far: float):
    """`TH-8`'s solve, returning the objects its own helper reduces away.

    Identical problem statement — same mesh generator, same exact exterior
    Dirichlet trace, same material map — so any number below is comparable with
    the `TH-8` gate log directly.
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
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0),
        cell_tags=cell_tags,
        material_map={
            SPHERE_TAG: HomogeneousMaterial(sigma=0.0, epsilon_r=EPSILON_R_SPHERE)
        },
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=_exact_exterior_numpy(EPSILON_R_SPHERE),
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()
    return msh, cell_tags, fields


def _magnitude_stats_on_cells(field, cells: np.ndarray, comm) -> dict[str, float]:
    """``compute_tagged_vector_magnitude_stats``' reduction over an explicit set.

    Production takes its sampling cells from the guardrail, so scoring the drop
    set needs this one extra entry point.  The sampling and the reduction are
    the module's own helpers, not a reimplementation: same centroids, same
    ``eval``, same phasor magnitude ``|F| = sqrt(Σ|F_i|²)``, same allreduces.
    """
    mesh = field.function_space.mesh
    points = _cell_centroids(mesh, cells)
    values, _pts, _valid_cells, _invalid = _evaluate_on_cells(field, points, cells)

    if values.shape[0] > 0:
        mags = np.abs(np.linalg.norm(values, axis=1))
        local_count, local_sum = int(mags.size), float(np.sum(mags))
        local_min, local_max = float(np.min(mags)), float(np.max(mags))
    else:
        local_count, local_sum = 0, 0.0
        local_min, local_max = float("inf"), float("-inf")

    count = comm.allreduce(local_count, op=MPI.SUM)
    total = comm.allreduce(local_sum, op=MPI.SUM)
    return {
        "count": count,
        "mean": total / count if count else float("nan"),
        "min": comm.allreduce(local_min, op=MPI.MIN),
        "max": comm.allreduce(local_max, op=MPI.MAX),
    }


@complex_only
@pytest.mark.integration
def test_drop_set_semantics_against_the_sphere_closed_form():
    """Score the guardrail's surviving set, the full set and the drop set."""
    comm = MPI.COMM_WORLD
    expected = interior_field_closed_form(EPSILON_R_SPHERE)

    msh, cell_tags, fields = _solve_sphere_fields(RESOLUTION_SPHERE, RESOLUTION_FAR)
    field = fields.e_real

    tagged = _tagged_cells(cell_tags, SPHERE_TAG)
    interior = _interior_tagged_cells(msh, cell_tags, SPHERE_TAG)
    drop = np.setdiff1d(tagged, interior).astype(np.int32)

    n_tagged = comm.allreduce(int(tagged.size), op=MPI.SUM)
    n_interior = comm.allreduce(int(interior.size), op=MPI.SUM)
    n_drop = comm.allreduce(int(drop.size), op=MPI.SUM)

    surviving = compute_tagged_vector_magnitude_stats(
        field, cell_tags, SPHERE_TAG, comm=comm, prefer_interior_samples=True
    )
    full = compute_tagged_vector_magnitude_stats(
        field, cell_tags, SPHERE_TAG, comm=comm, prefer_interior_samples=False
    )
    dropped = _magnitude_stats_on_cells(field, drop, comm)

    err_a = abs(surviving["mean"] - expected) / expected
    err_b = abs(full["mean"] - expected) / expected
    err_c = abs(dropped["mean"] - expected) / expected

    range_a = surviving["max"] - surviving["min"]
    range_b = full["max"] - full["min"]
    range_ratio = range_b / range_a

    if comm.rank == 0:
        print(
            f"\n[POST-1 step 3] TH-8 sphere, h_sphere = {RESOLUTION_SPHERE}, "
            f"eps_r = {EPSILON_R_SPHERE}, closed form |E_in|/E0 = {expected:.6f}"
        )
        print(
            f"  cell classes (global, owned): tagged {n_tagged}, "
            f"interior {n_interior}, drop {n_drop} "
            f"({n_drop / n_tagged:.2%} of the tag)"
        )
        for label, stats, err in (
            ("(a) prefer_interior=True ", surviving, err_a),
            ("(b) full tagged set      ", full, err_b),
            ("(c) drop set alone       ", dropped, err_c),
        ):
            print(
                f"  {label}: n = {int(stats['count']):5d}  "
                f"mean = {stats['mean']:.6f} ({err:.3%})  "
                f"min = {stats['min']:.6f}  max = {stats['max']:.6f}"
            )
        print(f"  (a) vs (b): {err_a:.3%} vs {err_b:.3%}  [reported, not gated]")
        print(f"  separation (c)/(a) in mean error: {err_c / err_a:.3f}x")
        print(
            f"  spread: surviving {range_a:.6f}, full {range_b:.6f} "
            f"-> ratio {range_ratio:.3f}x"
        )

    # Exact integer identity: the guardrail partitions the owned tagged set.
    assert n_interior + n_drop == n_tagged, (
        f"interior {n_interior} + drop {n_drop} != tagged {n_tagged}; the "
        "guardrail's classes are not a partition of the owned tagged cells"
    )
    assert n_drop > 0 and n_interior > 0, (
        f"degenerate classification (interior {n_interior}, drop {n_drop}); "
        "with an empty class this module compares nothing"
    )
    assert surviving["count"] == n_interior and full["count"] == n_tagged, (
        "production sampled a different set than the classification says"
    )

    # Anchor: what production reports today, against the closed form.
    lo, hi = SURVIVING_ERROR_BAND
    assert lo < err_a < hi, (
        f"the guardrail's surviving mean |E| = {surviving['mean']:.6f} is "
        f"{err_a:.3%} from the closed form {expected:.6f}, outside the "
        f"probe-measured band ({lo:.2%}, {hi:.2%}); TH-8 itself bounds this "
        "fixture at 5%, so a value outside this band is a change in the solve, "
        "not in the sampling semantics"
    )

    # Negative control: the interface layer separates in spread, not in mean.
    # Both extrema of the tag must come from the drop set — that is the whole
    # content of "the guardrail discards the interface-adjacent layer".
    assert full["max"] > surviving["max"] and full["min"] < surviving["min"], (
        f"the surviving set's range [{surviving['min']:.6f}, "
        f"{surviving['max']:.6f}] is not strictly inside the full set's "
        f"[{full['min']:.6f}, {full['max']:.6f}]; the dropped layer then "
        "contributes no extremum and this fixture cannot see the semantics"
    )
    assert range_ratio > MIN_RANGE_RATIO, (
        f"full-set spread is only {range_ratio:.3f}x the surviving spread "
        f"(measured 1.334x); below {MIN_RANGE_RATIO} the drop set is "
        "indistinguishable from the interior and this module proves nothing"
    )
