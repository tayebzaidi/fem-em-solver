"""
Validation test: Magnetic field of straight wire.

Validates the magnetostatic solver against the analytical solution for an
infinite straight wire carrying current I:

    B_phi = mu_0 * I / (2 * pi * r)   [T]

Three modelling points govern how this test is set up (see MAG-7/8/9):

1. Current must be restricted to the wire subdomain (``subdomain_id=1``). An
   earlier revision applied J over the whole domain, which enclosed ~2500 A
   instead of 1 A and produced |B| rising with r against a reference falling
   as 1/r.
2. Field samples must be located in the cells that contain them, via
   ``post.evaluation.evaluate_vector_field_parallel``. Passing
   ``np.arange(n)`` as cell indices evaluates in arbitrary cells and returns
   meaningless values.
3. The outer wall carries the analytic potential as Dirichlet data (MAG-13).
   The natural condition ``n x (mu^-1 curl A) = 0`` means ``n x H = 0``, which
   on the outer cylinder forces the azimuthal H to zero -- exactly the
   component being compared -- and contradicts Ampere's law for a net axial
   current. That is a modeling error no refinement removes; it was previously
   hidden by sampling only at r <= 0.4 * domain_radius. Imposing
   ``A_z = -mu_0 I/(2 pi) ln(r/a)`` on the exterior instead makes the continuum
   limit the analytic field, lets sampling run back out to 0.8 * domain_radius,
   and restores clean O(h^1.2) convergence (22.19% -> 12.75% -> 9.26% at
   h = 0.004 / 0.0025 / 0.0018).

A *fat* wire costs no accuracy here: for uniform current density the external
field of a cylindrical conductor is identical to a filament for r > a. So the
wire radius is chosen large enough to be meshed cheaply, and samples start at
2a. This is what keeps the case inside the runtime budget -- the previous
parameters meshed a 5 cm x 1 m cylinder at h = 5 mm (~4e5 cells) and exceeded
400 s without completing.
"""

import numpy as np
import pytest
import ufl
from dolfinx import fem
from dolfinx import mesh as dmesh
from mpi4py import MPI

from fem_em_solver.core.solvers import (
    MagnetostaticProblem,
    MagnetostaticSolver,
    exterior_dirichlet_bc,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import AnalyticalSolutions, ErrorMetrics
from fem_em_solver.utils.constants import MU_0
from tests.validation.test_convergence import (
    RATE_MAX,
    RATE_MIN,
    fit_convergence_rate,
)

# Geometry chosen so the wire is resolvable at a coarse global mesh size while
# the sampling annulus stays clear of both the conductor and the outer boundary.
WIRE_RADIUS = 0.003
DOMAIN_RADIUS = 0.03
WIRE_LENGTH = 0.20
RESOLUTION = 0.0025
CURRENT = 1.0

# Sample between 2a and 0.4 * domain_radius: outside the conductor, inside the
# region the outer boundary meaningfully perturbs.
R_MIN = 2.0 * WIRE_RADIUS
R_MAX = 0.4 * DOMAIN_RADIUS

# With the analytic Dirichlet BC of MAG-13 the outer wall no longer forces
# H_phi = 0, so samples may run out to it. Measured at h=0.0025: 12.48% over
# 2a -> 0.4R vs 12.75% over 2a -> 0.8R, i.e. the near-boundary region is no
# longer where the error lives.
R_MAX_BC = 0.8 * DOMAIN_RADIUS

# --- MAG-18: the sampler-independent gate -----------------------------------
# The 10-point radial statistic below is a *sample* of the field, and OPS-18
# step 3 attempt 5 measured what that costs: on the recording image (0.7.2 /
# gmsh 4.11.1) the same solved field at h = 0.0025 reads 15.8028% / 12.7485% /
# 11.4984% at n_points = 8 / 10 / 20 -- a 34% swing of the statistic under a
# choice the physics does not see, with the 15% band already failing at
# n_points = 8 (log 20260822T201014Z_OPS-18-step3-wire-ladder-npoints-072.log,
# known-issues 2026-08-22). MAG-18 replaces it with a reduced integral that has
# no sample count:
#
#   E_Omega = || |B_h| - |B_ana| ||_L2(Omega) / || |B_ana| ||_L2(Omega)
#   Omega   = {2a <= r <= 0.8 R_domain, |z| <= 0.25 L}
#
# i.e. the same region the samples span. Omega is a DG0 indicator built from a
# numpy mask on *owned* cell midpoints -- deliberately not a ufl.conditional on
# SpatialCoordinate, which would compare complex numbers in the complex build
# (OPS-22) and this file must stay importable in both.
E_OMEGA_R_MIN = 2.0 * WIRE_RADIUS
E_OMEGA_R_MAX = 0.8 * DOMAIN_RADIUS
E_OMEGA_Z_MAX = 0.25 * WIRE_LENGTH

# The recorded h-ladder (MAG-13 fixture, analytic Dirichlet wall).
E_OMEGA_LADDER = [0.004, 0.0025, 0.0018]

# Pre-registered before any E_Omega was measured (PROJECT_PLAN MAG-18): a DG
# projection of the curl of an N1curl degree-1 potential should show >= 1;
# 0.7 is the headroom, the MAG-17 convention.
E_OMEGA_RATE_MIN = 0.7

# Reproduction record, NOT a physics bound -- the physics bound is the rate.
# Version-tagged: measured on the h = 0.0025 rung, 145 884 cells, image
# 0.7.2 / gmsh 4.11.1, mpiexec -n 2, log
# 20260823T003327Z_MAG-18-record-probe.log.
#
# Rank independence (MAG-18 anchor (ii)), measured: -n 2 1.0728835983e-01 vs
# -n 4 1.0728836764e-01, i.e. 7.28e-08 relative -- NOT the 1e-10 the anchor
# pre-registered. The cause is not the statistic: the magnetostatic solve is a
# direct LU (ksp_type=preonly, pc_type=lu), whose factorization order changes
# with the partition, and the retired 10-point statistic moves the same way on
# the same two runs (15.802788% vs 15.802785%, 1.9e-07 relative). So ~1e-7 is
# the solve's own cross-width floor, shared by both statistics, and no norm
# defined on this field can beat it. The band below is the pre-registered
# *record* band 1e-4; the 1e-10 clause is a finding for the review, recorded in
# docs/testing/known-issues.md, not something loosened here.
#
# OPS-18 step 3a re-record, 2026-08-23 (18:00 review ruling (1) of 2026-08-22
# extended to leg 2 by ruling (2); condition (b) as restated (b') on
# 2026-08-23). The value below is the one measured on image tag v0.11.0
# (dolfinx 0.11.0.post0, gmsh 4.15.2), where the rung meshes to 147 235 cells;
# on 0.7.2 / 145 884 cells it read 1.0728835983e-01, quoted above and kept here
# as the record's provenance. The mesh moved +0.92% with the image's gmsh and
# the record moved -1.04% with it, while the *gate* -- the fitted rate -- moved
# 7e-04 (1.6842 -> 1.6854), which is the point of MAG-18. Under (b') the record
# printed twice in one 0.11 run agrees to 7e-10, i.e. 7e-06 of its 1e-4 band.
# No band moved.
E_OMEGA_H0025_RECORD = 1.061717e-01
E_OMEGA_RECORD_BAND = 1e-4

# Attempt-5 row reproduced as the negative control: the statistic MAG-18
# replaces, printed beside E_Omega on the gated rung so the log carries the
# sampler swing side by side with the norm that removes it.
#
# Keyed by image, because *that* is what this control exists to say. The
# retired statistic is not version-portable -- the same solved field on the
# same fixture reads a 21% different 10-point number on 0.11 -- so a single
# row would either fail on one image or have to be banded loosely enough to
# hide the effect. Both rows are measurements, neither is a physics bound:
#   0.7.2  / gmsh 4.11.1, 145 884 cells --
#     20260822T201014Z_OPS-18-step3-wire-ladder-npoints-072.log
#   0.11.0 / gmsh 4.15.2, 147 235 cells --
#     20260823T051410Z_OPS-18-step3a-leg2-wire-011.log
NPOINTS_CONTROL_BY_VERSION = {
    "0.7": {8: 0.158028, 10: 0.127485, 20: 0.114984},
    "0.11": {8: 0.166033, 10: 0.153848, 20: 0.136986},
}


def _npoints_control():
    """The sampler control row recorded on the image this run is using.

    Raises rather than defaulting: an unrecognised image means the control has
    no record on it, and silently reusing another image's row is exactly the
    mis-attribution OPS-18 step 3 spent four attempts untangling.
    """
    import dolfinx

    key = ".".join(dolfinx.__version__.split(".")[:2])
    if key not in NPOINTS_CONTROL_BY_VERSION:
        raise AssertionError(
            f"no n_points control recorded for dolfinx {dolfinx.__version__} "
            f"(have {sorted(NPOINTS_CONTROL_BY_VERSION)}); measure it, do not "
            f"borrow another image's row"
        )
    return key, NPOINTS_CONTROL_BY_VERSION[key]


NPOINTS_CONTROL_BAND = 1e-4


def _annulus_indicator(mesh):
    """DG0 indicator of Omega = {2a <= r <= 0.8R, |z| <= 0.25L}.

    Built from a numpy mask on owned-cell midpoints (``indices <
    size_local``); ghost dofs are filled by ``scatter_forward`` so the form
    compiler sees a consistent Function, though only owned cells contribute to
    ``dx``.
    """
    tdim = mesh.topology.dim
    n_owned = mesh.topology.index_map(tdim).size_local
    owned = np.arange(n_owned, dtype=np.int32)
    mid = dmesh.compute_midpoints(mesh, tdim, owned)

    r = np.hypot(mid[:, 0], mid[:, 1])
    inside = (
        (r >= E_OMEGA_R_MIN) & (r <= E_OMEGA_R_MAX) & (np.abs(mid[:, 2]) <= E_OMEGA_Z_MAX)
    )

    V0 = fem.functionspace(mesh, ("DG", 0))
    chi = fem.Function(V0, name="chi_Omega")
    chi.x.array[:] = 0.0
    dofs = np.asarray(V0.dofmap.list)[:n_owned].reshape(-1)
    chi.x.array[dofs] = inside.astype(np.float64)
    chi.x.scatter_forward()
    return chi


def _domain_l2_error(mesh, b_field):
    """Annulus-restricted relative domain L2 error of |B| (MAG-18).

    Both integrals are ``assemble_scalar`` (rank-local!) reduced with
    ``allreduce(SUM)`` before the ratio is formed.
    """
    chi = _annulus_indicator(mesh)

    b_ana = fem.Function(b_field.function_space, name="B_analytic")

    def _b_ana_interp(x):
        points = np.ascontiguousarray(x[:3].T)
        return AnalyticalSolutions.straight_wire_magnetic_field(points, CURRENT).T

    b_ana.interpolate(_b_ana_interp)

    # Fixed quadrature degree: the integrands carry a sqrt, whose UFL degree
    # estimate is neither cheap nor reproducible across versions.
    dx = ufl.dx(domain=mesh, metadata={"quadrature_degree": 4})
    mag_h = ufl.sqrt(ufl.inner(b_field, b_field))
    mag_a = ufl.sqrt(ufl.inner(b_ana, b_ana))

    num_local = fem.assemble_scalar(fem.form(chi * (mag_h - mag_a) ** 2 * dx))
    den_local = fem.assemble_scalar(fem.form(chi * mag_a**2 * dx))
    num = mesh.comm.allreduce(num_local, op=MPI.SUM)
    den = mesh.comm.allreduce(den_local, op=MPI.SUM)
    assert den > 0.0, "Omega is empty -- the annulus mask caught no cells"
    return float(np.sqrt(num / den))


def _wire_potential_interp(x):
    """Analytic wire A in dolfinx interpolation convention (3, n) -> (3, n).

    The finite-conductor branch is required: the domain end caps of
    ``straight_wire_domain`` cross r = 0, where the filament ln r diverges.
    """
    points = np.ascontiguousarray(x[:3].T)
    A = AnalyticalSolutions.straight_wire_vector_potential(
        points, CURRENT, wire_radius=WIRE_RADIUS
    )
    return A.T


def _solve_straight_wire(resolution, comm, analytic_bc=True):
    """Mesh and solve the straight-wire problem at one resolution."""
    mesh, cell_tags, facet_tags = MeshGenerator.straight_wire_domain(
        wire_length=WIRE_LENGTH,
        wire_radius=WIRE_RADIUS,
        domain_radius=DOMAIN_RADIUS,
        resolution=resolution,
        comm=comm,
    )

    problem = MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0)
    # Degree 1 is deliberate. Measured on this fixture (8 ranks):
    #   res=0.005  deg=1 -> 35.5%      res=0.005  deg=2 -> 31.7%
    #   res=0.0025 deg=1 -> 18.2%      res=0.004  deg=2 -> 24.9%
    #                                  res=0.003  deg=2 -> 2724%  (diverges)
    # Degree 2 costs ~8x the solve for a marginal accuracy gain and becomes
    # unstable as the mesh refines, which points at the gauge-penalty
    # formulation rather than at the element order. Do not raise the degree here
    # without re-measuring; see MAG-10.
    solver = MagnetostaticSolver(problem, degree=1)

    # Uniform J inside the wire only; tag 1 is the wire volume.
    j_magnitude = CURRENT / (np.pi * WIRE_RADIUS**2)

    def current_density(x):
        import ufl

        return ufl.as_vector([0.0, 0.0, j_magnitude])

    bcs = [exterior_dirichlet_bc(solver.V, _wire_potential_interp)] if analytic_bc else None
    solver.solve(current_density=current_density, subdomain_id=1, bc_functions=bcs)
    return mesh, solver.compute_b_field()


def _sample_radial(b_field, n_points, comm, r_min=R_MIN, r_max=R_MAX):
    """Return (r, |B|_numeric, |B|_analytic) along +x at the wire midplane."""
    r_test = np.linspace(r_min, r_max, n_points)
    points = np.zeros((n_points, 3))
    points[:, 0] = r_test
    points[:, 2] = 0.0  # midplane, where the finite-length error is smallest

    values, valid = evaluate_vector_field_parallel(b_field, points, comm=comm)
    assert valid.all(), f"{(~valid).sum()}/{n_points} sample points outside mesh"

    b_num_mag = np.linalg.norm(values, axis=1)
    b_ana = AnalyticalSolutions.straight_wire_magnetic_field(points, CURRENT)
    b_ana_mag = np.linalg.norm(b_ana, axis=1)
    return r_test, b_num_mag, b_ana_mag, values


class TestStraightWire:
    """Validation tests for straight wire magnetostatics."""

    def test_straight_wire_b_field(self):
        """B-field magnitude matches mu_0*I/(2*pi*r) outside the conductor."""
        comm = MPI.COMM_WORLD
        mesh, b_field = _solve_straight_wire(RESOLUTION, comm)

        n_points = 10
        r_test, b_num_mag, b_ana_mag, values = _sample_radial(
            b_field, n_points, comm, R_MIN, R_MAX_BC
        )

        # Field should be azimuthal: negligible axial component.
        b_z_max = float(np.max(np.abs(values[:, 2])))
        b_ref = float(np.max(b_ana_mag))
        assert b_z_max < 0.10 * b_ref, (
            f"B_z should be small compared to |B|; got {b_z_max:.3e} vs {b_ref:.3e}"
        )

        rel_error = ErrorMetrics.l2_relative_error(b_num_mag, b_ana_mag)

        if comm.rank == 0:
            n_cells = mesh.topology.index_map(mesh.topology.dim).size_global
            print("\nStraight wire validation:")
            print(f"  Cells: {n_cells}")
            print(f"  Current: {CURRENT} A (restricted to wire tag 1)")
            print(f"  Sampling r: {R_MIN:.4f} -> {R_MAX_BC:.4f} m "
                  f"(a={WIRE_RADIUS}, R_domain={DOMAIN_RADIUS})")
            print(f"  Relative L2 error: {rel_error:.4%}")
            for r, bn, ba in zip(r_test, b_num_mag, b_ana_mag):
                print(f"    r={r:.4f}  |B|_num={bn:.4e}  |B|_ana={ba:.4e}  "
                      f"rel={abs(bn - ba) / ba:.2%}")

        # Bound set from measurement (MAG-13, log 20260730T034614Z_MAG-13-probe2),
        # analytic Dirichlet BC, sampling 2a -> 0.8 R_domain, mpiexec -n 2:
        #   h=0.004   38.8k cells   22.19%
        #   h=0.0025  145.9k cells  12.75%   <- this test
        #   h=0.0018  383.2k cells   9.26%
        # i.e. O(h^1.2), still converging: there is no plateau left to hit, which
        # is the point of the BC. With the natural n x H = 0 wall the same meshes
        # give 35.13% at h=0.004 (see test_analytic_bc_improves_on_natural_bc) and
        # the error stops responding to refinement.
        # Reaching the < 5% target needs h ~ 0.00125 (~1.1M cells, > 5 min at
        # -n 2), which is outside the standard tier; the remaining error is
        # discretization of a 1/r field on a uniform mesh near a thin conductor,
        # so graded refinement (MAG-9) is the cheaper route, not more uniform h.
        #
        # MAG-18 (2026-08-22): the `rel_error < 0.15` assertion this comment
        # used to justify is REPORTED, NOT GATED. It was never a bound on the
        # solver: OPS-18 step 3 attempt 5 read the same solved field at
        # n_points 8 / 10 / 20 as 15.8028% / 12.7485% / 11.4984% on the
        # recording image itself, so the 15% band was already failing at
        # n_points = 8 on 0.7.2 and passing at 10 only by the sampler choice
        # this test happens to make (known-issues 2026-08-22, log
        # 20260822T201014Z_OPS-18-step3-wire-ladder-npoints-072.log). The gate
        # is replaced, not loosened: TestStraightWire::test_domain_l2_* gate
        # the sampler-free E_Omega and its convergence rate. The number is
        # still printed above, and reproduced under assertion at all three
        # sample counts in test_domain_l2_record, so a real regression in the
        # field is still caught here.
        if comm.rank == 0:
            print(f"  [reported, not gated] 10-point rel_error {rel_error:.4%} "
                  f"vs the retired 15% band")

    def test_analytic_bc_improves_on_natural_bc(self):
        """The analytic Dirichlet wall beats n x H = 0 on the same mesh.

        This is the MAG-13 claim stated as a test: the natural condition
        ``n x H = 0`` on the outer cylinder contradicts Ampere's law for a net
        axial current, so it is a modeling error, not a discretization one, and
        removing it must lower the error at fixed h. Run at the coarse
        resolution so both solves fit the smoke budget.
        """
        comm = MPI.COMM_WORLD
        res = 0.004
        n_points = 10
        errors = {}

        for use_bc in (False, True):
            _, b_field = _solve_straight_wire(res, comm, analytic_bc=use_bc)
            _, b_num_mag, b_ana_mag, _ = _sample_radial(
                b_field, n_points, comm, R_MIN, R_MAX_BC
            )
            errors[use_bc] = ErrorMetrics.l2_relative_error(b_num_mag, b_ana_mag)

        if comm.rank == 0:
            print(f"\n  h={res}: natural BC {errors[False]:.4%}, "
                  f"analytic BC {errors[True]:.4%}")

        # Measured at h=0.004, -n 2 (log 20260730T034541Z_MAG-13-probe):
        # 35.13% natural -> 22.19% analytic, a factor 0.63. The 0.85 bound
        # leaves room for mesh-partition noise while still failing if the BC
        # stops being applied at all.
        assert errors[True] < 0.85 * errors[False], (
            f"Analytic BC {errors[True]:.4%} should beat natural BC "
            f"{errors[False]:.4%} at h={res}"
        )

    def test_straight_wire_convergence(self):
        """The measured h-refinement *rate* sits in the N1curl degree-1 band.

        `OPS-17` step 2 (2026-08-17): the previous assertion was
        ``errors[-1] < errors[0]`` — monotone improvement with no rate, which
        a solve converging at any rate at all (or by luck) passes. Replaced
        with the fitted log-log slope gated on the same ``[RATE_MIN, RATE_MAX]``
        band ``test_convergence.py::test_h_refinement_straight_wire`` uses, and
        with the same fitting routine, imported rather than re-derived.

        MAG-20 step 1 (2026-08-28): this band **survived a pre-stated
        sampler sweep and is kept on measurement, not on inertia**. See the
        n_points table at the assertion below.
        """
        comm = MPI.COMM_WORLD
        resolutions = [0.004, 0.0025]
        n_points = 8
        errors = []

        for res in resolutions:
            _, b_field = _solve_straight_wire(res, comm)
            _, b_num_mag, b_ana_mag, _ = _sample_radial(b_field, n_points, comm)
            err = ErrorMetrics.l2_relative_error(b_num_mag, b_ana_mag)
            errors.append(err)
            if comm.rank == 0:
                print(f"  Resolution {res:.4f} m: error = {err:.4%}")

        rate = fit_convergence_rate(np.array(resolutions), np.array(errors))
        if comm.rank == 0:
            print(f"  Fitted convergence rate: {rate:.4f}")

        # MAG-20 step 1, 2026-08-28 — the band below is VALIDATED by
        # measurement, under a decision rule stated before the numbers existed
        # (PROJECT_PLAN MAG-20 step 1): sweep n_points over this test's own two
        # rungs; any crossing of *either* edge retires the two-sided band under
        # the MAG-19 ruling-(i) pattern, stability inside it at every count
        # keeps the band and records the stability. Measured on the 0.11 image
        # (dolfinx 0.11.0.post0 / gmsh 4.15.2, -n 2, one solve per rung
        # re-sampled at each count, window r in [R_MIN, R_MAX] = the 0.4 R
        # default this test uses; probe
        # tests/validation/probe_straight_wire_convergence_npoints.py, log
        # 20260828T050130Z_MAG-20-step1-npoints-probe.log, 49 s):
        #
        #   h        cells      n=8         n=10        n=20
        #   0.0040    38 740    21.5512%    21.1826%    22.6647%   (swing +7.00%)
        #   0.0025   147 235    14.8669%    15.0685%    14.2097%   (swing +6.04%)
        #   fitted two-rung rate:  0.7900      0.7246      0.9934
        #
        # No count crosses either edge => VALIDATED, band kept, nothing moved.
        # Two things the measurement says that the verdict does not:
        #  - the sampler swing on *this* window is ~6-7% of the error, not the
        #    34% MAG-19 measured on the 0.8 R window (NPOINTS_CONTROL_BY_VERSION
        #    above) — the statistic this test samples is the better-behaved one;
        #  - but the swing still moves the *rate* by 37% of its own value
        #    (0.7246 .. 0.9934), and the n=10 row clears RATE_MIN by only
        #    0.0246. The band holds at all three counts; the margin is thin, and
        #    that is filed for the review rather than acted on here — a band is
        #    never widened, and this one was not narrowed either.
        # The n=8 fit reproduces MAG-19 step 2's recorded 0.7900 exactly, which
        # is the probe's negative control on the imported machinery.
        assert RATE_MIN < rate < RATE_MAX, (
            f"Convergence rate {rate:.4f} outside [{RATE_MIN}, {RATE_MAX}] "
            f"(expected ~1.0 for N1curl degree 1); errors "
            f"{[f'{e:.4%}' for e in errors]} at h {resolutions}"
        )

    def test_domain_l2_convergence(self):
        """MAG-18: E_Omega falls monotonically at rate >= 0.7 on the ladder.

        This is the gate the 10-point radial statistic could not be: a reduced
        integral over Omega, with no sample count for the answer to depend on.
        The gated quantity is the *rate* -- the h = 0.0025 value is a separate,
        version-tagged reproduction record (test_domain_l2_record).
        """
        comm = MPI.COMM_WORLD
        errors = []

        for res in E_OMEGA_LADDER:
            mesh, b_field = _solve_straight_wire(res, comm)
            e_omega = _domain_l2_error(mesh, b_field)
            errors.append(e_omega)
            if comm.rank == 0:
                n_cells = mesh.topology.index_map(mesh.topology.dim).size_global
                print(f"  h={res:.4f}  cells {n_cells}  E_Omega {e_omega:.10e} "
                      f"({e_omega:.4%})")

        rate = fit_convergence_rate(np.array(E_OMEGA_LADDER), np.array(errors))
        if comm.rank == 0:
            print(f"  MAG-18 fitted E_Omega rate: {rate:.4f}")

        assert all(errors[i + 1] < errors[i] for i in range(len(errors) - 1)), (
            f"E_Omega not monotone decreasing on {E_OMEGA_LADDER}: "
            f"{[f'{e:.6e}' for e in errors]}"
        )
        assert rate >= E_OMEGA_RATE_MIN, (
            f"E_Omega rate {rate:.4f} below the pre-registered "
            f"{E_OMEGA_RATE_MIN}; errors {[f'{e:.6e}' for e in errors]} at "
            f"h {E_OMEGA_LADDER}"
        )

    def test_domain_l2_record(self):
        """MAG-18: the h = 0.0025 E_Omega reproduction record.

        Run at ``-n 2`` and ``-n 4`` this is also anchor (ii), rank
        independence: a reduced integral has no sampler, so the two widths must
        agree -- the control that the new statistic lacks the defect the old
        one had. The negative control prints beside it: the old 10-point
        statistic at n_points 8 / 10 / 20 on the *same* solved field,
        reproducing the attempt-5 row.
        """
        comm = MPI.COMM_WORLD
        res = 0.0025
        mesh, b_field = _solve_straight_wire(res, comm)
        e_omega = _domain_l2_error(mesh, b_field)

        image_key, npoints_control = _npoints_control()
        sampled = {}
        for n_points in sorted(npoints_control):
            _, b_num_mag, b_ana_mag, _ = _sample_radial(
                b_field, n_points, comm, R_MIN, R_MAX_BC
            )
            sampled[n_points] = ErrorMetrics.l2_relative_error(b_num_mag, b_ana_mag)

        if comm.rank == 0:
            n_cells = mesh.topology.index_map(mesh.topology.dim).size_global
            print(f"\nMAG-18 record rung h={res}, {n_cells} cells, "
                  f"{comm.size} ranks:")
            print(f"  E_Omega = {e_omega:.10e}  ({e_omega:.4%})")
            print(f"  negative control -- the statistic this replaces "
                  f"(dolfinx {image_key} row):")
            for n_points, err in sampled.items():
                ref = npoints_control[n_points]
                print(f"    n_points {n_points:3d}  rel_error {err:.6%} "
                      f"(recorded {ref:.4%}, "
                      f"{(err - ref) / ref:+.3e} relative)")

        # The sampler swing is the finding, so it is asserted, not just
        # printed: on 0.7.2 the same field read three ways spans 15.80% ->
        # 11.50%, on 0.11 16.60% -> 13.70%.
        for n_points, err in sampled.items():
            ref = npoints_control[n_points]
            assert abs(err - ref) / ref < NPOINTS_CONTROL_BAND, (
                f"n_points={n_points} control {err:.6%} does not reproduce the "
                f"dolfinx {image_key} record {ref:.4%} within "
                f"{NPOINTS_CONTROL_BAND}"
            )

        if E_OMEGA_H0025_RECORD is None:
            pytest.skip("E_OMEGA_H0025_RECORD not yet measured on this image")
        dev = abs(e_omega - E_OMEGA_H0025_RECORD) / E_OMEGA_H0025_RECORD
        assert dev < E_OMEGA_RECORD_BAND, (
            f"E_Omega {e_omega:.10e} deviates {dev:.3e} from the record "
            f"{E_OMEGA_H0025_RECORD:.10e} (band {E_OMEGA_RECORD_BAND}); "
            f"{comm.size} ranks"
        )

    def test_domain_l2_analytic_bc_beats_natural(self):
        """MAG-18 anchor (iii): MAG-13's claim restated in the new norm.

        The natural ``n x H = 0`` wall contradicts Ampere's law for a net axial
        current, so at fixed h the analytic Dirichlet wall must read strictly
        better -- now measured as a domain integral rather than 10 samples.
        """
        comm = MPI.COMM_WORLD
        res = 0.0025
        errors = {}

        for use_bc in (False, True):
            mesh, b_field = _solve_straight_wire(res, comm, analytic_bc=use_bc)
            errors[use_bc] = _domain_l2_error(mesh, b_field)

        if comm.rank == 0:
            print(f"\n  MAG-18 h={res}: E_Omega natural BC {errors[False]:.6%}, "
                  f"analytic BC {errors[True]:.6%}, "
                  f"ratio {errors[True] / errors[False]:.4f}")

        assert errors[True] < errors[False], (
            f"Analytic BC E_Omega {errors[True]:.6%} should be strictly better "
            f"than natural BC {errors[False]:.6%} at h={res}"
        )


def test_analytical_straight_wire():
    """Unit test for analytical solution calculation."""
    current = 1.0  # A

    # Test at r = 0.01 m
    points = np.array([[0.01, 0, 0]])
    B = AnalyticalSolutions.straight_wire_magnetic_field(points, current)

    # Expected: B_phi = mu_0*I/(2*pi*r) = 4*pi*1e-7 * 1 / (2*pi*0.01)
    expected = 4e-7 * np.pi * 1.0 / (2 * np.pi * 0.01)

    B_mag = np.linalg.norm(B)
    assert np.abs(B_mag - expected) < 1e-10, "Analytical B-field incorrect"

    # Direction should be in y-direction at x-axis (azimuthal)
    assert np.abs(B[0, 1] - expected) < 1e-10, "B-field direction incorrect"
    assert np.abs(B[0, 0]) < 1e-15, "B_x should be zero"
    assert np.abs(B[0, 2]) < 1e-15, "B_z should be zero"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
