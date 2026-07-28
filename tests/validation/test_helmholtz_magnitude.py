"""Validation test: Helmholtz centre-field *magnitude* against the closed form.

`MAG-14`. `test_helmholtz_v2.py` asserts only that the central field is uniform
(`CV < 1%`), which is **scale-invariant**: a solver wrong by any constant factor
-- a missing `mu_0`, a mis-normalized current -- passes it untouched. The
magnitude comparison that actually validates the solver has only ever lived in
`examples/magnetostatics/04_helmholtz_analytic_comparison.py`, which CI never
runs. This test lands it in the suite.

Reference
---------
Two coaxial tori, major radius `R`, minor radius `a`, separated by `R` (the
Helmholtz condition), carrying unit-magnitude azimuthal current density. The
current per loop is therefore `I = |J| * pi * a**2 = pi * a**2` -- the
normalization is the entire point of this test, since `CV` cannot see it.

At the centre the filamentary Helmholtz field is

    B_z(0) = (4/5)**1.5 * mu_0 * I / R

which is checked here both against `AnalyticalSolutions.helmholtz_coil_field_on_axis`
(so a bug in that helper cannot hide) and against the FEM solution.

Sizing (measured, `docs/testing/logs/20260727T171928Z_MAG-4.log` and the
`MAG-1`/`MAG-4` convergence table in PROJECT_PLAN.md §7)
------------------------------------------------------
Accuracy here is dominated by the air box, not by `h`: the outer boundary
carries `n x H = 0`, a perfect *magnetic* conductor that mirrors flux back in.
Measured centre-field error at wire `h = 0.003` with graded far-field sizing:

    air padding 1R -> 51k cells -> 7.43%
    air padding 2R -> 76k cells -> 1.73%     <- used here
    air padding 4R -> 163k cells -> 0.01%    (26 s at 8 ranks)

2R padding is chosen to stay inside the `standard` tier at `mpiexec -n 2`; the
5% tolerance has margin over the 1.73% measured there. If the measured error at
2R ever approaches the bound, the fix is a larger air box (`AIR_PADDING = 4 * R`),
never a looser tolerance.
"""

from __future__ import annotations

import numpy as np
import ufl
from mpi4py import MPI

from fem_em_solver.core.solvers import MagnetostaticProblem, MagnetostaticSolver
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import AnalyticalSolutions
from fem_em_solver.utils.constants import MU_0

MAJOR_RADIUS = 0.02  # R [m]
MINOR_RADIUS = 0.005  # a [m]
SEPARATION = MAJOR_RADIUS  # Helmholtz condition
AIR_PADDING = 2.0 * MAJOR_RADIUS  # see module docstring; 1.73% measured
WIRE_RESOLUTION = 0.003  # mesh size at the tori [m]
FAR_RESOLUTION = 0.010  # mesh size at the outer box [m]; graded sizing
N_POINTS = 21

# Relative tolerance on magnitude (PROJECT_PLAN.md section 10 MVP criterion).
MAGNITUDE_REL_TOL = 0.05
# Window for the mean-error assertion: the region between the coils, where the
# Helmholtz configuration is meant to be usable.
CENTRAL_WINDOW = 0.25 * MAJOR_RADIUS
# Secondary uniformity check, so this test supersedes test_helmholtz_v2 rather
# than duplicating it.
UNIFORMITY_CV_MAX = 0.01


def _current_density(x):
    """Unit-magnitude azimuthal current density confined to the two tori."""
    z1 = -SEPARATION / 2.0
    z2 = SEPARATION / 2.0

    rho = ufl.sqrt(x[0] ** 2 + x[1] ** 2)
    in_wire_1 = ((rho - MAJOR_RADIUS) ** 2 + (x[2] - z1) ** 2) <= MINOR_RADIUS**2
    in_wire_2 = ((rho - MAJOR_RADIUS) ** 2 + (x[2] - z2) ** 2) <= MINOR_RADIUS**2
    in_wire = ufl.Or(in_wire_1, in_wire_2)

    rho_safe = ufl.max_value(rho, 1e-12)
    return ufl.as_vector(
        [
            ufl.conditional(in_wire, -x[1] / rho_safe, 0.0),
            ufl.conditional(in_wire, x[0] / rho_safe, 0.0),
            0.0,
        ]
    )


def test_helmholtz_centre_field_magnitude():
    """FEM centre B_z matches (4/5)^1.5 * mu_0 * I / R to within 5%."""
    comm = MPI.COMM_WORLD

    mesh, cell_tags, facet_tags = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=WIRE_RESOLUTION,
        comm=comm,
        air_padding=AIR_PADDING,
        wire_resolution=WIRE_RESOLUTION,
        far_resolution=FAR_RESOLUTION,
    )
    # size_global is already reduced; local cell counts would differ per rank.
    n_cells = mesh.topology.index_map(mesh.topology.dim).size_global

    problem = MagnetostaticProblem(
        mesh=mesh, cell_tags=cell_tags, facet_tags=facet_tags, mu=MU_0
    )
    solver = MagnetostaticSolver(problem, degree=1)
    solver.solve(current_density=_current_density)
    b_field = solver.compute_b_field()

    z_eval = np.linspace(-0.6 * SEPARATION, 0.6 * SEPARATION, N_POINTS)
    points = np.zeros((N_POINTS, 3), dtype=np.float64)
    points[:, 2] = z_eval

    # Collision-based location, broadcast to every rank (MAG-7): Function.eval
    # with np.arange(n) evaluates in arbitrary cells and returns nonsense.
    values, valid = evaluate_vector_field_parallel(b_field, points, comm=comm)
    assert valid.all(), f"{int((~valid).sum())}/{N_POINTS} sample points outside mesh"
    bz_num = values[:, 2]

    # I = |J| * wire cross-section. This factor is what CV cannot see.
    current = 1.0 * np.pi * MINOR_RADIUS**2
    bz_ana = AnalyticalSolutions.helmholtz_coil_field_on_axis(
        z_eval, current, MAJOR_RADIUS, SEPARATION
    )

    centre = int(np.argmin(np.abs(z_eval)))
    assert z_eval[centre] == 0.0, "sample grid must contain z = 0"

    # Independent closed form, so a bug in the analytic helper cannot hide here.
    bz_closed_form = (0.8**1.5) * MU_0 * current / MAJOR_RADIUS
    helper_rel = abs(bz_ana[centre] - bz_closed_form) / abs(bz_closed_form)
    assert helper_rel < 1e-12, (
        f"helmholtz_coil_field_on_axis disagrees with (4/5)^1.5*mu_0*I/R by "
        f"{helper_rel:.3e}: analytic={bz_ana[centre]:.6e} T, "
        f"closed form={bz_closed_form:.6e} T"
    )

    centre_rel = abs(bz_num[centre] - bz_closed_form) / abs(bz_closed_form)

    window = np.abs(z_eval) <= CENTRAL_WINDOW
    mean_rel = float(
        np.mean(np.abs(bz_num[window] - bz_ana[window]) / np.abs(bz_ana[window]))
    )

    # Innermost samples: uniformity of the central region (the _v2 check).
    inner = np.argsort(np.abs(z_eval))[:5]
    cv = float(np.std(bz_num[inner]) / abs(np.mean(bz_num[inner])))

    if comm.rank == 0:
        print(
            f"\ncells={n_cells}  I={current:.6e} A"
            f"\ncentre B_z: FEM={bz_num[centre]:.6e} T  "
            f"closed form={bz_closed_form:.6e} T  rel err={centre_rel:.3%}"
            f"\nmean rel err over |z| <= {CENTRAL_WINDOW:.4f} m: {mean_rel:.3%}"
            f"\ncentral CV: {cv:.4%}",
            flush=True,
        )

    assert centre_rel < MAGNITUDE_REL_TOL, (
        f"centre B_z off by {centre_rel:.2%}: FEM={bz_num[centre]:.6e} T vs "
        f"closed form {bz_closed_form:.6e} T (tolerance {MAGNITUDE_REL_TOL:.0%}). "
        f"A constant-factor error (mu_0, current normalization) looks like this; "
        f"so does too small an air box -- check AIR_PADDING before anything else."
    )
    assert mean_rel < MAGNITUDE_REL_TOL, (
        f"mean on-axis rel err {mean_rel:.2%} over |z| <= {CENTRAL_WINDOW:.4f} m "
        f"exceeds {MAGNITUDE_REL_TOL:.0%}"
    )
    assert cv < UNIFORMITY_CV_MAX, (
        f"central field non-uniform: CV={cv:.4%} (expected < "
        f"{UNIFORMITY_CV_MAX:.0%})"
    )
