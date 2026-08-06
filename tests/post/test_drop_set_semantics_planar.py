"""`POST-1` step 4: drop-set semantics on a *planar* interface.

Step 3 scored the guardrail's three sets against the `TH-8` sphere and left one
confound explicitly unresolved: the sphere boundary is curved, so chordal
geometry error lives in the very cell layer the semantics question is about.
This module moves the question onto a **planar** interface, where facets are
represented exactly and that confound is identically zero, so what remains is
the interface-smearing term alone.

The fixture is the `POST-3` step-2 two-slab box — σ = 0.1 | 1.4 S/m split at
``x = L/2``, a mesh plane for even ``n`` — whose mesh, tags and conductivities
are imported from ``tests/validation/test_poynting_balance.py`` rather than
restated.

**Why the Dirichlet trace is not imported with them.**  The §7 plan asks for
"the fixture and its piecewise closed form"; the fixture has none.  `POST-3`
step 2 imposes the *σ_low* plane wave on all six faces and its own comment says
so — that trace is not the two-material solution, because of the reflection at
the interface.  It is not merely approximate either: on ``y = 0`` and ``y = L``
it pins ``E_z(x) = e^{-j k_low x}`` right through slab 2, which no piecewise
solution can match.  A Poynting *identity* has no free parameters and does not
care (which is why step 2 was sound); a **pointwise closed-form comparison**
does.  So this module keeps the mesh, the tags and the material map unchanged
and replaces only the boundary data with the self-consistent one — the classic
normal-incidence transmission problem across the same interface:

.. math::

    E = (0, 0, f(x)), \\quad f'' + k(x)^2 f = 0

    f_1(x) = e^{-j k_1 x} + R\\, e^{-j k_1 (2 x_i - x)}      \\quad 0 \\le x \\le x_i
    f_2(x) = T\\, e^{-j k_1 x_i} e^{-j k_2 (x - x_i)}        \\quad x_i \\le x \\le L

    R = (k_1 - k_2)/(k_1 + k_2), \\qquad T = 2 k_1/(k_1 + k_2)

For ``E = (0,0,f(x))`` one has ``curl curl E = (0,0,-f'')``, so the equation
above *is* ``curl curl E - k^2 E = 0``; ``f`` continuous is tangential-E
continuity and ``f'`` continuous is tangential-H continuity at uniform μ.  The
pair is therefore an exact solution of the piecewise-``ε_c`` curl-curl problem,
and imposing it on all six faces makes it **the** solution.  That claim is not
assumed — :func:`test_supplied_closed_form_is_the_solution` measures the global
relative L2 error at 16³ and 32³ and requires clean O(h) convergence, which a
wrong closed form cannot produce.

**What the sampled object had to be.**  The anchor is ``|E|``, the phasor
magnitude, so the sampled function is ``fields.e_complex``.  ``fields.e_real``
— what step 3 sampled on the sphere — is ``np.real`` of the phasor, a phase-0
snapshot; on the sphere's nearly in-phase interior the two are close, but on
this propagating decaying field ``Re E`` crosses zero and the same measurement
returns a 61.8% "error" against a solve whose global L2 error is 2.16%
(probe ``20260806T020312Z_POST-1-step4-probe.log``, before the switch;
``…020449Z_POST-1-step4-probe2.log`` after).

**Measured** (probe ``20260806T020449Z_POST-1-step4-probe2.log``, ``-n 2``,
32³ = 196 608 cells, per-centroid ``|E|`` against the closed form evaluated at
the *same* centroids, slab-2 tag):

===  =========================  =====  ==============  ===================
set  description                n      mean rel error  ``|E|`` range
===  =========================  =====  ==============  ===================
(a)  ``prefer_interior=True``   96256  1.1472%         [0.237386, 0.692107]
(b)  full owned tagged set      98304  1.1420%         [0.237386, 0.698349]
(c)  drop set alone             2048   **0.8974%**     [0.697742, 0.698349]
===  =========================  =====  ==============  ===================

**The interface-smearing hypothesis is refuted, and refuted with a sign.**  The
(c)/(a) ratio is **0.7822** — on a geometry-error-free interface the dropped
layer is 22% **more** accurate than the interior the guardrail keeps, not less.
(The sphere's 1.009 was consistent with "harmless"; this is stronger, and points
the other way.)  The layer sits at the entry face, pinned by continuity to the
well-resolved slab-1 side, while the surviving set carries the accumulated
phase-and-decay error of the whole slab.  There is nothing smeared for the
guardrail to protect a mean from — here or, by step 3, on the sphere.

**The extremum claim, now closed-form predictable and measured.**  ``|f_2|``
decays monotonically, so the true maximum over slab 2 sits *at the interface*:
``|E| = 0.703744``.  Dropping the interface layer therefore discards the peak by
construction, and the closed form prices the loss in advance:

* full set (b) max = 0.698349 — **0.7666%** below the closed-form entry-face value
* surviving set (a) max = 0.692107 — **1.6536%** below it, i.e. **2.157×** worse

So ``prefer_interior=True`` is unsafe for any peak statistic, which is what the
2026-08-05 review's adjudication was waiting on: SAR peaks are extrema.  This
module gates the full set's max against the closed form and gates the
(a)-vs-(b) separation.

**The production default followed** (`POST-1` step 5, 2026-08-06):
``prefer_interior_samples`` now defaults to ``False``, and
:func:`test_production_default_reproduces_row_b_on_this_fixture` pins row (b) to
the production entry point itself — the rows above were measured through this
module's helper, which is not what a caller invokes.  The retired default is
kept reachable and pinned to row (a) in the same test.

**Does not close `POST-1`.**  The coil+phantom application is still where the
chunk earns its ✅; this step decides only the extremum-semantics rule.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/post/test_drop_set_semantics_planar.py -v -s'
"""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.post.phantom_fields import (
    _cell_centroids,
    _evaluate_on_cells,
    _interior_tagged_cells,
    _tagged_cells,
    compute_tagged_vector_magnitude_stats,
)

from tests.complex_mode import complex_only
from tests.validation.test_lossy_plane_wave import (
    BOX_L,
    EPSILON_R,
    FREQUENCY_HZ,
    MU_R,
    _wavenumber,
)
from tests.validation.test_poynting_balance import (
    SIGMA_HIGH,
    SIGMA_LOW,
    TAG_HIGH,
    TAG_LOW,
    _two_material_mesh,
)

INTERFACE_X = 0.5 * BOX_L

# The `POST-3` step-2 pair, unchanged: the interface is a mesh plane at both.
N_COARSE = 16
N_FINE = 32

# Probe-measured bands (20260806T020449Z_POST-1-step4-probe2.log).  Every number
# below is a floor/ceiling set around a measurement, never a value fitted to
# rescue a run; the measurement each brackets is named in the comment.

# The supplied closed form must be the solution: 4.3147% -> 2.1568% at rate
# 1.0004.  0.9 is a floor under a clean O(h); 5% is §10's MVP bar, the same one
# `TH-6` and `POST-3` step 2 are held to on this box.
MIN_CONVERGENCE_RATE = 0.9
MAX_FINE_L2_ERROR = 0.05

# (a)'s per-centroid mean error, measured 1.1472%; ±0.3 pp.  The upper end sits
# far inside the 4.49% `POST-3` step 2 holds this fixture to, so this gate can
# never pass a solve that fixture would reject.
SURVIVING_MEAN_ERROR_BAND = (0.0085, 0.0145)

# (c)/(a) mean-error ratio, measured 0.7822.  The claim being gated is the
# refutation's *direction* — the drop layer is more accurate, not less — so the
# ceiling sits just below unity rather than snug against 0.7822.  Step 3's
# sphere measured 1.009 with curvature confounded; a planar value at ~1.0 would
# have refuted interface smearing outright, and a value below 1 refutes it
# harder.
MAX_DROP_TO_SURVIVING_RATIO = 0.95

# Full-set max against the closed-form entry-face value, measured 0.7666%.
MAX_FULL_SET_PEAK_ERROR = 0.012

# (a)'s peak deficit over (b)'s: measured 1.6536% / 0.7666% = 2.157x.  1.5 is a
# floor under that, per `POST-3` step 2's ceiling rule (gate the separation only
# where the probe shows a clean one).
MIN_PEAK_ERROR_RATIO = 1.5


def transmission_coefficients() -> tuple[complex, complex, complex, complex]:
    """``(k1, k2, R, T)`` for the σ_low | σ_high interface at ``x = L/2``."""
    k1 = _wavenumber(SIGMA_LOW)
    k2 = _wavenumber(SIGMA_HIGH)
    return k1, k2, complex((k1 - k2) / (k1 + k2)), complex(2.0 * k1 / (k1 + k2))


def closed_form_ez(x: np.ndarray) -> np.ndarray:
    """``f(x)`` of the module docstring, vectorised over a coordinate array."""
    k1, k2, r, t = transmission_coefficients()
    xs = np.asarray(x, dtype=float)
    left = np.exp(-1j * k1 * xs) + r * np.exp(-1j * k1 * (2.0 * INTERFACE_X - xs))
    right = t * np.exp(-1j * k1 * INTERFACE_X) * np.exp(-1j * k2 * (xs - INTERFACE_X))
    return np.where(xs <= INTERFACE_X, left, right)


def closed_form_magnitude(x: np.ndarray) -> np.ndarray:
    """``|E|`` of the closed form — the pointwise anchor the three sets score against."""
    return np.abs(closed_form_ez(x))


def dirichlet_e_field(x: np.ndarray) -> np.ndarray:
    """The self-consistent Dirichlet trace ``(0, 0, f(x))``."""
    ez = closed_form_ez(x[0])
    zeros = np.zeros_like(ez)
    return np.array([zeros, zeros, ez])


def closed_form_ufl(x):
    """The same ``f(x)`` in UFL, for the global L2 check that it is the solution."""
    k1, k2, r, t = transmission_coefficients()

    def cplx_exp(arg_real, arg_imag):
        # exp(arg_real + j arg_imag) written so UFL sees real arithmetic only,
        # the `TH-6` ``_exact_factory`` convention.
        return ufl.exp(arg_real) * (ufl.cos(arg_imag) + 1j * ufl.sin(arg_imag))

    xx = x[0]
    inc = cplx_exp(k1.imag * xx, -k1.real * xx)
    refl = r * cplx_exp(
        k1.imag * (2.0 * INTERFACE_X - xx), -k1.real * (2.0 * INTERFACE_X - xx)
    )
    trans = (
        t
        * cplx_exp(k1.imag * INTERFACE_X, -k1.real * INTERFACE_X)
        * cplx_exp(k2.imag * (xx - INTERFACE_X), -k2.real * (xx - INTERFACE_X))
    )
    value = ufl.conditional(ufl.le(xx, INTERFACE_X), inc + refl, trans)
    return ufl.as_vector([0.0 * value, 0.0 * value, value])


def solve_two_slab(n: int):
    """`POST-3` step 2's mesh, tags and materials with the consistent trace."""
    msh, cell_tags = _two_material_mesh(n)
    material_map = {
        TAG_LOW: HomogeneousMaterial(sigma=SIGMA_LOW, epsilon_r=EPSILON_R, mu_r=MU_R),
        TAG_HIGH: HomogeneousMaterial(sigma=SIGMA_HIGH, epsilon_r=EPSILON_R, mu_r=MU_R),
    }
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=EPSILON_R, mu_r=MU_R),
        material_map=material_map,
        cell_tags=cell_tags,
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=dirichlet_e_field,
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()
    return msh, cell_tags, fields


def global_l2_error(msh, fields) -> float:
    """Relative L2 error of the solve against the closed form, allreduced."""
    comm = msh.comm
    exact = closed_form_ufl(ufl.SpatialCoordinate(msh))
    diff = fields.e_complex - exact
    err_sq = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(diff, diff) * ufl.dx)), op=MPI.SUM
    )
    ref_sq = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(exact, exact) * ufl.dx)), op=MPI.SUM
    )
    return float(np.sqrt(abs(err_sq) / abs(ref_sq)))


def pointwise_stats(field, cells: np.ndarray, comm) -> dict[str, float]:
    """Per-centroid ``|E|`` vs the closed form at the *same* centroids.

    Sampling is ``phantom_fields``' own machinery — same centroids, same
    ``eval``, same phasor magnitude ``|F| = sqrt(Σ|F_i|²)`` — so these numbers
    are comparable with production's directly; only the reduction is local to
    this module, because production reduces the magnitude and this step needs
    the *error*.  Callers pass owned-cell sets only, so ghosts classify but
    never contribute a sample.  Every statistic below is allreduced.
    """
    mesh = field.function_space.mesh
    points = _cell_centroids(mesh, cells)
    values, pts, _valid, _invalid = _evaluate_on_cells(field, points, cells)

    if values.shape[0] > 0:
        mags = np.abs(np.linalg.norm(values, axis=1))
        rel = np.abs(mags - closed_form_magnitude(pts[:, 0])) / closed_form_magnitude(
            pts[:, 0]
        )
        loc = dict(
            count=int(mags.size),
            err_sum=float(np.sum(rel)),
            mag_min=float(np.min(mags)),
            mag_max=float(np.max(mags)),
            x_min=float(np.min(pts[:, 0])),
            err_max=float(np.max(rel)),
        )
    else:
        loc = dict(
            count=0,
            err_sum=0.0,
            mag_min=float("inf"),
            mag_max=float("-inf"),
            x_min=float("inf"),
            err_max=float("-inf"),
        )

    count = comm.allreduce(loc["count"], op=MPI.SUM)
    return {
        "count": count,
        "mean_rel_error": (
            comm.allreduce(loc["err_sum"], op=MPI.SUM) / count if count else float("nan")
        ),
        "min_mag": comm.allreduce(loc["mag_min"], op=MPI.MIN),
        "max_mag": comm.allreduce(loc["mag_max"], op=MPI.MAX),
        "min_x": comm.allreduce(loc["x_min"], op=MPI.MIN),
        "max_rel_error": comm.allreduce(loc["err_max"], op=MPI.MAX),
    }


@complex_only
@pytest.mark.integration
def test_supplied_closed_form_is_the_solution():
    """The precondition: a wrong closed form does not converge at O(h).

    This module replaces `POST-3` step 2's Dirichlet trace with a piecewise one
    it derives, so nothing may be scored against that closed form until the
    solve is shown to reproduce it under refinement.
    """
    comm = MPI.COMM_WORLD
    msh_c, _, fields_c = solve_two_slab(N_COARSE)
    err_coarse = global_l2_error(msh_c, fields_c)
    msh_f, _, fields_f = solve_two_slab(N_FINE)
    err_fine = global_l2_error(msh_f, fields_f)
    rate = float(np.log(err_coarse / err_fine) / np.log(2.0))

    k1, k2, r, t = transmission_coefficients()
    if comm.rank == 0:
        print(
            f"\n[POST-1 step 4] two-slab planar interface, sigma = {SIGMA_LOW} | "
            f"{SIGMA_HIGH} S/m at x = {INTERFACE_X} m"
        )
        print(f"  k1 = {k1:.6e}   k2 = {k2:.6e}   |R| = {abs(r):.6f}  |T| = {abs(t):.6f}")
        print(
            f"  rel L2 vs closed form: {N_COARSE}^3 {err_coarse:.4%} -> "
            f"{N_FINE}^3 {err_fine:.4%}, rate in h = {rate:.4f}"
        )

    assert rate > MIN_CONVERGENCE_RATE, (
        f"the supplied piecewise closed form is not the solution this fixture "
        f"converges to: rel L2 {err_coarse:.4%} -> {err_fine:.4%} is rate "
        f"{rate:.4f}, below {MIN_CONVERGENCE_RATE} (measured 1.0004)"
    )
    assert err_fine < MAX_FINE_L2_ERROR, (
        f"rel L2 error {err_fine:.4%} at {N_FINE}^3 exceeds the {MAX_FINE_L2_ERROR:.0%} "
        "MVP bar this box is held to elsewhere (TH-6, POST-3 step 2)"
    )


@pytest.fixture(scope="module")
def fine_two_slab():
    """One 32³ solve, shared by the step-4 semantics gate and the step-5 default gate.

    Both need the *same* fixture — step 5's claim is that the production default
    reproduces step 4's row (b) digit-for-digit — and a second solve of 196 608
    cells would cost ~35 s for nothing.
    """
    return solve_two_slab(N_FINE)


@complex_only
@pytest.mark.integration
def test_drop_set_semantics_on_a_planar_interface(fine_two_slab):
    """Score (a) survivors, (b) full set and (c) drop set against the closed form."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, fields = fine_two_slab
    # The anchor is |E|, the phasor magnitude, so the sampled object is the
    # complex phasor.  ``e_real`` is a phase-0 snapshot of it and on this
    # propagating field crosses zero — it scores 61.8% against a 2.16% solve
    # (20260806T020312Z_POST-1-step4-probe.log).
    field = fields.e_complex

    tagged = _tagged_cells(cell_tags, TAG_HIGH)
    interior = _interior_tagged_cells(msh, cell_tags, TAG_HIGH)
    drop = np.setdiff1d(tagged, interior).astype(np.int32)

    n_tagged = comm.allreduce(int(tagged.size), op=MPI.SUM)
    n_interior = comm.allreduce(int(interior.size), op=MPI.SUM)
    n_drop = comm.allreduce(int(drop.size), op=MPI.SUM)

    surviving = pointwise_stats(field, interior, comm)
    full = pointwise_stats(field, tagged, comm)
    dropped = pointwise_stats(field, drop, comm)

    entry_face = float(closed_form_magnitude(np.array([INTERFACE_X]))[0])
    peak_err_full = abs(full["max_mag"] - entry_face) / entry_face
    peak_err_surviving = abs(surviving["max_mag"] - entry_face) / entry_face
    drop_ratio = dropped["mean_rel_error"] / surviving["mean_rel_error"]

    if comm.rank == 0:
        print(
            f"\n[POST-1 step 4] slab-2 tag at {N_FINE}^3; closed-form |E| at the "
            f"interface = {entry_face:.6f} (the slab's true maximum)"
        )
        print(
            f"  cell classes (global, owned): tagged {n_tagged}, interior "
            f"{n_interior}, drop {n_drop} ({n_drop / n_tagged:.2%} of the tag)"
        )
        for label, s in (
            ("(a) prefer_interior=True ", surviving),
            ("(b) full tagged set      ", full),
            ("(c) drop set alone       ", dropped),
        ):
            print(
                f"  {label}: n = {int(s['count']):5d}  "
                f"mean rel err = {s['mean_rel_error']:.4%}  "
                f"max rel err = {s['max_rel_error']:.4%}  "
                f"|E| in [{s['min_mag']:.6f}, {s['max_mag']:.6f}]  "
                f"x_min = {s['min_x']:.6f}"
            )
        print(
            f"  separation (c)/(a) in mean error: {drop_ratio:.4f}x   "
            "(sphere, curvature-confounded: 1.009x)"
        )
        print(
            f"  peak vs closed-form entry face: (b) {peak_err_full:.4%}, "
            f"(a) {peak_err_surviving:.4%} -> {peak_err_surviving / peak_err_full:.3f}x worse"
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
        "a set was sampled at a different size than the classification says"
    )

    # Anchor: what production reports today, per centroid against the closed form.
    lo, hi = SURVIVING_MEAN_ERROR_BAND
    assert lo < surviving["mean_rel_error"] < hi, (
        f"the surviving set's mean per-centroid error {surviving['mean_rel_error']:.4%} "
        f"is outside the probe-measured band ({lo:.2%}, {hi:.2%}); POST-3 step 2 "
        "bounds this fixture at 4.49%, so a value outside this band is a change "
        "in the solve, not in the sampling semantics"
    )

    # The result: on a geometry-error-free interface the dropped layer is *more*
    # accurate than the interior, so there is no smearing for the guardrail to
    # protect a mean from.
    assert drop_ratio < MAX_DROP_TO_SURVIVING_RATIO, (
        f"the drop layer's mean error is {drop_ratio:.4f}x the surviving set's "
        f"(measured 0.7822x); at or above {MAX_DROP_TO_SURVIVING_RATIO} the "
        "interface-smearing hypothesis this fixture was built to refute is not "
        "refuted, and the extremum reading below loses its premise"
    )

    # The extremum: the true maximum sits at the interface, in the layer the
    # guardrail discards, and the closed form prices the loss.
    assert peak_err_full < MAX_FULL_SET_PEAK_ERROR, (
        f"the full tagged set's maximum |E| = {full['max_mag']:.6f} is "
        f"{peak_err_full:.4%} from the closed-form entry-face value "
        f"{entry_face:.6f}, outside the probe-measured {MAX_FULL_SET_PEAK_ERROR:.1%}"
    )
    assert full["max_mag"] > surviving["max_mag"], (
        f"the surviving set's maximum {surviving['max_mag']:.6f} is not below the "
        f"full set's {full['max_mag']:.6f}; the dropped layer then contributes no "
        "extremum and this fixture cannot see the semantics"
    )
    assert peak_err_surviving / peak_err_full > MIN_PEAK_ERROR_RATIO, (
        f"dropping the interface layer costs only "
        f"{peak_err_surviving / peak_err_full:.3f}x in peak error (measured "
        f"2.157x); below {MIN_PEAK_ERROR_RATIO} the peak is not measurably "
        "harmed and prefer_interior=True would be safe for extrema after all"
    )


@complex_only
@pytest.mark.integration
def test_production_default_reproduces_row_b_on_this_fixture(fine_two_slab):
    """`POST-1` step 5: the production entry point now reports row (b), not row (a).

    Step 4 measured the three sets through this module's own reduction over
    explicit cell sets.  The production statistic is
    :func:`compute_tagged_vector_magnitude_stats`, and until step 5 it reported
    row (a) — so the adjudication above was about a path production did not
    take.  Here the same solved field goes through the production call with
    **no** sampling kwarg, and its ``count``/``min``/``max`` must equal row
    (b)'s to ``1e-12``: same cells, same centroids, same magnitude.  The peak
    deficit against the closed-form entry-face value is then recomputed from
    production's own ``max`` and held to the *same* landed ceiling.

    The negative control is the retired default: ``prefer_interior_samples=True``
    passed explicitly must reproduce row (a) — a strictly smaller set, a strictly
    smaller ``max``, and the landed 2.157x peak-error penalty.  Both rows are
    therefore pinned to production, not merely to this module's helper.
    """
    comm = MPI.COMM_WORLD
    _msh, cell_tags, fields = fine_two_slab
    field = fields.e_complex

    tagged = _tagged_cells(cell_tags, TAG_HIGH)
    interior = _interior_tagged_cells(_msh, cell_tags, TAG_HIGH)
    row_b = pointwise_stats(field, tagged, comm)
    row_a = pointwise_stats(field, interior, comm)

    production = compute_tagged_vector_magnitude_stats(
        field, cell_tags, TAG_HIGH, comm=comm
    )
    guarded = compute_tagged_vector_magnitude_stats(
        field, cell_tags, TAG_HIGH, comm=comm, prefer_interior_samples=True
    )

    entry_face = float(closed_form_magnitude(np.array([INTERFACE_X]))[0])
    peak_err_production = abs(production["max"] - entry_face) / entry_face
    peak_err_guarded = abs(guarded["max"] - entry_face) / entry_face

    if comm.rank == 0:
        print(
            f"\n[POST-1 step 5] production path on the step-4 planar fixture, "
            f"-n {comm.size}; closed-form |E| at the interface = {entry_face:.6f}"
        )
        print(
            f"  default (no kwarg)     : n = {production['count']:5d}  "
            f"|E| in [{production['min']:.6f}, {production['max']:.6f}]  "
            f"peak deficit {peak_err_production:.4%}   [row (b), measured 0.7666%]"
        )
        print(
            f"  row (b) helper         : n = {int(row_b['count']):5d}  "
            f"|E| in [{row_b['min_mag']:.6f}, {row_b['max_mag']:.6f}]"
        )
        print(
            f"  prefer_interior=True   : n = {guarded['count']:5d}  "
            f"|E| in [{guarded['min']:.6f}, {guarded['max']:.6f}]  "
            f"peak deficit {peak_err_guarded:.4%}   [row (a), measured 1.6536%]"
        )
        print(
            f"  row (a) helper         : n = {int(row_a['count']):5d}  "
            f"|E| in [{row_a['min_mag']:.6f}, {row_a['max_mag']:.6f}]"
        )
        print(
            f"  retired-default penalty: {peak_err_guarded / peak_err_production:.3f}x "
            "(measured 2.157x)",
            flush=True,
        )

    # The default path *is* row (b).
    assert production["count"] == int(row_b["count"]), (
        f"the production default sampled {production['count']} cells, not row "
        f"(b)'s {int(row_b['count'])}: prefer_interior_samples does not default "
        "to False"
    )
    for prod_key, row_key in (("min", "min_mag"), ("max", "max_mag")):
        assert np.isclose(
            production[prod_key], row_b[row_key], rtol=1e-12, atol=0.0
        ), (
            f"production '{prod_key}' = {production[prod_key]:.15e} vs row (b) "
            f"{row_b[row_key]:.15e}: the default path is not scoring the set "
            "step 4 adjudicated"
        )
    assert peak_err_production < MAX_FULL_SET_PEAK_ERROR, (
        f"the production maximum |E| = {production['max']:.6f} is "
        f"{peak_err_production:.4%} from the closed-form entry-face value "
        f"{entry_face:.6f}, outside the landed {MAX_FULL_SET_PEAK_ERROR:.1%}"
    )

    # Negative control: the retired default, still reachable and still worse.
    assert guarded["count"] == int(row_a["count"]), (
        f"prefer_interior_samples=True sampled {guarded['count']} cells, not row "
        f"(a)'s {int(row_a['count'])}: the old behaviour is not pinned"
    )
    assert np.isclose(guarded["max"], row_a["max_mag"], rtol=1e-12, atol=0.0), (
        f"prefer_interior_samples=True max {guarded['max']:.15e} != row (a)'s "
        f"{row_a['max_mag']:.15e}"
    )
    assert peak_err_guarded / peak_err_production > MIN_PEAK_ERROR_RATIO, (
        f"through production, the retired default costs only "
        f"{peak_err_guarded / peak_err_production:.3f}x in peak error (measured "
        f"2.157x); below {MIN_PEAK_ERROR_RATIO} the flip is not measurably an "
        "improvement on this fixture"
    )
