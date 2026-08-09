"""Sanity metrics validation for coil+phantom magnetostatic B-field.

**What the symmetry metric gates: discretisation symmetry, not phantom
physics.** ``MagnetostaticProblem`` is built here with a *uniform*
``mu = MU_0``, so the phantom is physically invisible to the solve; the
geometry is mirror-symmetric about ``x = 0`` by construction and the exact
±x mismatch is therefore **0**. Every digit the metric reads is
discretisation error, and no claim about phantom material behaviour may be
drawn from it (`MAG-6` steps 1-3; known-issues 4's fixture caveat, which
retires into this docstring).

**Why the symmetry sampling goes through DG0** (`MAG-6` step 1/2, 2026-08-08):
``curl A`` for N1curl degree 1 is cell-wise constant, so interpolating it
into CG1 asks for a nodal value where the field jumps and gets it from
whichever cell the partition supplies. On record, the CG1 path swings
**3.03x** across rank counts (0.727907 / 0.240541 / 0.321468 at ``-n 1/2/4``
on one unchanged mesh) and does **not** converge under refinement
(0.240541 -> 0.760519 -> 0.723637 at ``-n 2`` on an h-ladder where DG0 falls
monotonically). DG0 keeps the cell-wise value: it is rank-stable to 4.69%
and falls at ``p ~ 1.07``, meeting the unchanged 0.350 bound at
``resolution = 0.010`` m. The CG1 number is still printed for continuity —
it is never gated.

**Why the solve runs at ``gauge_penalty=1.0``** (`MAG-6` step 5, 2026-08-09):
1.0 is the validated gauge floor, and the fixture used to solve below it at
1e-3. Step 4 measured the cost of the sub-floor solve — the centerline metric
rank-scatters **88%** at 1e-3 and **0.341%** at 1.0 — so the gate now
exercises the solver in its validated regime. Both bounds (0.350 / 0.60) are
unchanged by that move, and both metrics tightened: at penalty 1.0 this
fixture reads centerline 0.250414 / 0.250474 and mirror 0.311170 / 0.311166
at ``-n 2/4``.
"""

import numpy as np
import ufl
from mpi4py import MPI
from dolfinx import fem

from fem_em_solver.core.solvers import MagnetostaticProblem, MagnetostaticSolver
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post import evaluate_vector_field_parallel
from fem_em_solver.utils.constants import MU_0

from tests.tolerances import (
    B_FIELD_MAX_NONTRIVIAL_ABS_MIN,
    B_FIELD_MEAN_NONTRIVIAL_ABS_MIN,
    FIELD_SCALE_FLOOR,
    PHANTOM_CENTERLINE_JUMP_RATIO_MAX,
    PHANTOM_SYMMETRY_ABS_TOL_FACTOR,
    PHANTOM_SYMMETRY_REL_TOL,
)


def test_coil_phantom_bfield_metrics_are_finite_smooth_and_symmetric():
    """Validate phantom |B| metrics, centerline smoothness, and symmetry sanity."""
    comm = MPI.COMM_WORLD

    phantom_radius = 0.04
    phantom_height = 0.10
    # `MAG-6` step 3: one refinement rung below the historical 0.015 m.  The DG0
    # metric was measured at 0.312197 / 0.304356 / 0.323844 (`-n 2/4/1`) here,
    # against the untouched 0.350 bound; 55 784 cells, 6.4 s mesh + 2.0 s solve
    # at `-n 2` (standard tier).
    resolution = 0.010
    # The ±x probe grid is pinned to the clearance the h-ladder was measured on
    # (the 0.015 m fixture's), *not* to `resolution`: the recorded numbers above
    # are for this fixed point set, and letting the grid track `h` would compare
    # a metric of one point set against a metric of another.
    sampling_clearance_resolution = 0.015

    mesh, cell_tags, facet_tags = MeshGenerator.coil_phantom_domain(
        coil_major_radius=0.08,
        coil_minor_radius=0.01,
        coil_separation=0.08,
        phantom_radius=phantom_radius,
        phantom_height=phantom_height,
        air_padding=0.04,
        resolution=resolution,
        comm=comm,
    )

    problem = MagnetostaticProblem(
        mesh=mesh,
        cell_tags=cell_tags,
        facet_tags=facet_tags,
        mu=MU_0,
    )
    solver = MagnetostaticSolver(problem, degree=1)

    coil_current = 1.0  # A
    coil_minor_radius = 0.01
    current_density_magnitude = coil_current / (np.pi * coil_minor_radius**2)

    def current_density(x):
        return ufl.as_vector([0.0, 0.0, current_density_magnitude])

    # `MAG-6` step 5 (2026-08-09): solve at the *validated* gauge floor.  The
    # fixture used to run at 1e-3, below that floor, and step 4 measured what
    # the sub-floor solve costs: the centerline metric rank-scatters 88%
    # there, against 0.341% at penalty 1.0 (0.251272 / 0.250416 / 0.250453 at
    # `-n 1/2/4`; the mirror metric moves 0.022%, 0.311226 / 0.311166 /
    # 0.311157).  Both bounds are untouched by this change.
    solver.solve(
        current_density=current_density,
        subdomain_ids=[1, 2],
        gauge_penalty=1.0,
    )

    b_field = solver.compute_b_field()
    v_lagrange = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    b_lagrange = fem.Function(v_lagrange, name="B")
    b_lagrange.interpolate(b_field)

    # The gated sampling path (see the module docstring): DG0 preserves the
    # cell-wise `curl A` instead of averaging it across a jump at a node.
    v_dg0 = fem.functionspace(mesh, ("DG", 0, (3,)))
    b_dg0 = fem.Function(v_dg0, name="B_dg0")
    b_dg0.interpolate(b_field)

    centerline_points = np.array(
        [[0.0, 0.0, z] for z in np.linspace(-0.03, 0.03, 9)],
        dtype=np.float64,
    )

    # Both centerline metrics below go through DG0 for the same reason the
    # symmetry metric does.  Measured 2026-08-08 at this rung: the CG1
    # centerline jump ratio reads 0.318029 at `-n 2` but 0.705 / 0.732 on two
    # *identical* `-n 4` runs — it is rank-dependent and not even run-to-run
    # reproducible, because a nodal average of a cell-wise-constant field
    # depends on which cells the partition hands the node.  (At the step-5
    # gauge floor the retired path still swings: 0.323398 / 0.714122 at
    # `-n 2/4`, 2.21×.)  DG0 at the same floor reads 0.250414 / 0.250474 at
    # `-n 2/4` — 0.024% apart.  The 0.60 tolerance is untouched.
    centerline_b, centerline_valid = evaluate_vector_field_parallel(
        b_dg0,
        centerline_points,
        comm=comm,
    )

    assert centerline_valid.all(), (
        "Expected all centerline phantom points to be evaluable, "
        f"but only {np.count_nonzero(centerline_valid)}/{len(centerline_valid)} were valid"
    )

    centerline_mag = np.linalg.norm(centerline_b, axis=1)
    assert np.isfinite(centerline_mag).all(), "Centerline |B| contains non-finite values"

    # Continuity print only — never gated.
    centerline_b_cg1, _ = evaluate_vector_field_parallel(
        b_lagrange,
        centerline_points,
        comm=comm,
    )
    centerline_mag_cg1 = np.linalg.norm(centerline_b_cg1, axis=1)
    cg1_jump = np.abs(np.diff(centerline_mag_cg1))
    cg1_jump_ratio = float(np.max(cg1_jump)) / max(
        float(np.max(centerline_mag_cg1)), FIELD_SCALE_FLOOR
    )

    b_min = float(np.min(centerline_mag))
    b_max = float(np.max(centerline_mag))
    b_mean = float(np.mean(centerline_mag))

    assert b_max > B_FIELD_MAX_NONTRIVIAL_ABS_MIN, (
        f"Expected nontrivial phantom B-field, got max |B|={b_max:.3e}"
    )
    assert b_mean > B_FIELD_MEAN_NONTRIVIAL_ABS_MIN, (
        f"Expected nontrivial average phantom B-field, got mean |B|={b_mean:.3e}"
    )

    # Centerline smoothness check: avoid large point-to-point jumps for symmetric setup
    point_to_point_jump = np.abs(np.diff(centerline_mag))
    max_jump = float(np.max(point_to_point_jump)) if point_to_point_jump.size else 0.0
    jump_ratio = max_jump / max(b_max, FIELD_SCALE_FLOOR)
    assert jump_ratio < PHANTOM_CENTERLINE_JUMP_RATIO_MAX, (
        "Centerline |B| is too jagged for a symmetric setup (DG0 sampling); "
        f"max jump ratio={jump_ratio:.6f} (tol {PHANTOM_CENTERLINE_JUMP_RATIO_MAX:.3f}); "
        f"CG1 print-only reads {cg1_jump_ratio:.6f}"
    )

    # Symmetry check for the symmetric two-coil setup.
    # Keep probes away from phantom interfaces to avoid boundary-cell artifacts.
    sample_clearance = max(0.75 * sampling_clearance_resolution, 0.004)
    safe_radius = phantom_radius - sample_clearance
    safe_half_height = (phantom_height / 2.0) - sample_clearance
    assert safe_radius > 0.0 and safe_half_height > 0.0, (
        "Sampling clearance is too large for phantom interior: "
        f"safe_radius={safe_radius:.3e}, safe_half_height={safe_half_height:.3e}"
    )

    x_probe_positions = np.array([0.35, 0.60, 0.85], dtype=np.float64) * safe_radius
    z_probe_positions = np.array([-0.60, 0.0, 0.60], dtype=np.float64) * safe_half_height
    y_probe_offset = 0.15 * sample_clearance

    symmetry_points = np.array(
        [
            [sx * x_val, y_probe_offset, z_val]
            for z_val in z_probe_positions
            for x_val in x_probe_positions
            for sx in (1.0, -1.0)
        ],
        dtype=np.float64,
    )
    symmetry_b, symmetry_valid = evaluate_vector_field_parallel(b_dg0, symmetry_points, comm=comm)

    assert symmetry_valid.all(), (
        "Expected all symmetry-check points to be evaluable, "
        f"but only {np.count_nonzero(symmetry_valid)}/{len(symmetry_valid)} were valid"
    )

    symmetry_mag = np.linalg.norm(symmetry_b, axis=1).reshape(-1, 2)
    pair_abs_diff = np.abs(symmetry_mag[:, 0] - symmetry_mag[:, 1])
    pair_ref = np.maximum(np.maximum(symmetry_mag[:, 0], symmetry_mag[:, 1]), FIELD_SCALE_FLOOR)
    pair_rel_diff = pair_abs_diff / pair_ref

    max_pair_abs_diff = float(np.max(pair_abs_diff))
    mean_pair_abs_diff = float(np.mean(pair_abs_diff))
    max_pair_rel_diff = float(np.max(pair_rel_diff))
    mean_pair_rel_diff = float(np.mean(pair_rel_diff))

    # The absolute scale is kept as a *diagnostic* only.  It used to sit on the
    # permissive side of an `or`, which let a relative failure pass whenever the
    # local field was small; on the rank-stable DG0 path there is a licensed
    # number to gate against, so the relative bound is asserted outright.  The
    # tolerance itself is unchanged (`PHANTOM_SYMMETRY_REL_TOL = 0.35`).
    symmetry_abs_tol = PHANTOM_SYMMETRY_ABS_TOL_FACTOR * b_max
    symmetry_rel_tol = PHANTOM_SYMMETRY_REL_TOL

    assert max_pair_rel_diff < symmetry_rel_tol, (
        "Mirror-symmetry (discretisation) check failed for ±x phantom points on the "
        f"DG0 sampling path; max_rel_diff={max_pair_rel_diff:.6f} (tol {symmetry_rel_tol:.3f}), "
        f"max_abs_diff={max_pair_abs_diff:.3e} (diagnostic scale {symmetry_abs_tol:.3e}). "
        "On record at this fixture (gauge_penalty=1.0, `MAG-6` step 5): "
        "0.311170 / 0.311166 at -n 2/4."
    )

    # Continuity print only — never gated.  CG1 is the retired path: 3.03x rank
    # swing and non-monotone under refinement (see the module docstring).
    cg1_b, cg1_valid = evaluate_vector_field_parallel(b_lagrange, symmetry_points, comm=comm)
    cg1_mag = np.linalg.norm(cg1_b, axis=1).reshape(-1, 2)
    cg1_ref = np.maximum(np.maximum(cg1_mag[:, 0], cg1_mag[:, 1]), FIELD_SCALE_FLOOR)
    cg1_max_rel_diff = float(np.max(np.abs(cg1_mag[:, 0] - cg1_mag[:, 1]) / cg1_ref))

    if comm.rank == 0:
        print("coil+phantom B-field metrics:")
        print(f"  centerline points: {len(centerline_points)}")
        print(f"  |B| min/max/mean on centerline (DG0): {b_min:.6e} / {b_max:.6e} / {b_mean:.6e}")
        print(f"  centerline max jump ratio (DG0, gated): {jump_ratio:.6f}")
        print(f"  RANKSPREAD_INPUT centerline_jump_ratio = {jump_ratio:.6f}")
        print(f"  centerline max jump ratio (CG1, print-only): {cg1_jump_ratio:.6f}")
        print("  symmetry probe setup:")
        print(f"    mesh resolution: {resolution:.6e} m")
        print(
            f"    interface clearance: {sample_clearance:.6e} m "
            f"(pinned to h = {sampling_clearance_resolution:.6e} m)"
        )
        print(f"    interior safe radius/half-height: {safe_radius:.6e} / {safe_half_height:.6e} m")
        print(f"    probe grid: {len(x_probe_positions)} x-positions × {len(z_probe_positions)} z-positions")
        print(f"    fixed y offset: {y_probe_offset:.6e} m")
        print("  symmetry mismatch, DG0 sampling (±x pairs) — the gated path:")
        print(
            "    abs diff max/mean: "
            f"{max_pair_abs_diff:.6e} / {mean_pair_abs_diff:.6e} "
            f"(diagnostic scale {symmetry_abs_tol:.6e})"
        )
        print(
            "    rel diff max/mean: "
            f"{max_pair_rel_diff:.6f} / {mean_pair_rel_diff:.6f} "
            f"(tol {symmetry_rel_tol:.6f})"
        )
        print(
            f"    on record at h = {resolution:.3f} m, gauge_penalty=1.0: "
            "0.311170 / 0.311166 at -n 2/4"
        )
        print(f"    RANKSPREAD_INPUT max_rel_diff = {max_pair_rel_diff:.6f}")
        print(f"  CG1 sampling, retired path (print-only, never gated): {cg1_max_rel_diff:.6f}")
