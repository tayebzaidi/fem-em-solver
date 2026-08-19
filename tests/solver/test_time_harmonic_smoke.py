"""Smoke test for minimal time-harmonic E-field scaffold."""

from __future__ import annotations

import dolfinx
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
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post import evaluate_vector_field_parallel
from fem_em_solver.post.power_balance import poynting_power_balance

from tests.complex_mode import complex_only

# The fixture's material, in one place — the same lossy saline the `TH-6`
# plane-wave gate uses, so the two tests exercise one material model.
SIGMA = 0.7
EPSILON_R = 78.0
FREQUENCY_HZ = 127.74e6

# Pre-stated; see test_time_harmonic_smoke_solve_conserves_real_power.
POYNTING_IMBALANCE_MAX = 0.25
BLIND_SEPARATION = 10.0
# The real sigma-blind control.  Was `1e-12 * SIGMA` until `POST-5` step 1
# (2026-08-18) fixed the helper defect that made an exact zero raise
# (known-issues 2026-08-17, `OPS-17` step-2 defect 4).
SIGMA_BLIND = 0.0

# `POST-5` step 1's h-ladder discriminator.  The record rung first, then two
# refinements; the smoke fixture's in-medium wavelength is
# lambda = c/(f sqrt(78)) = 0.266 m, so these are ~9 / ~13 / ~18 cells per
# wavelength.
LADDER_RESOLUTIONS = (0.03, 0.02, 0.015)
# Pre-registered before the run (PROJECT_PLAN §7 `POST-5` step 1): imbalance
# falling at a fitted rate >= this AND the net-inward flux sign correcting to
# positive on the finest rung  =>  RESOLUTION; an h-independent imbalance or a
# sign that never corrects  =>  SOURCE/ASSEMBLY.
LADDER_RATE_FOR_RESOLUTION = 0.7

# The smoke fixture's inner conductor radius, in one place: the azimuthal drive
# of `POST-5` step 2 scales by it so |J| = 1 A/m^2 at the rod surface, matching
# the axial drive's unit magnitude.
INNER_RADIUS = 0.01
# `POST-5` step 2's pre-registered discriminator band (PROJECT_PLAN §7):
# imbalance collapsing under the xfail's 25% band AND the net-inward flux sign
# turning positive on the closed drive  =>  SOURCE (the axial drive's J.n != 0
# end-cap incompatibility); imbalance persisting at O(100%) with the sign
# unmoved  =>  ASSEMBLY.
CLOSED_DRIVE_IMBALANCE_FOR_SOURCE = POYNTING_IMBALANCE_MAX

# The coarse-rung record the axial drive must reproduce as this step's negative
# control (`POST-5` step 1 ladder, 20260818T215101Z, and `OPS-17` step 2's
# 20260817T112448Z before it).  Imported by nothing else; restated here only
# because the step-1 numbers live in the plan, not in code.
AXIAL_RECORD_DISSIPATED_W = 1.199162e-06
AXIAL_RECORD_NET_INWARD_W = -2.008179e-07
AXIAL_RECORD_IMBALANCE = 1.167465


@complex_only
@pytest.mark.xfail(
    strict=True,
    reason=(
        "known-issues 2026-08-17 (OPS-17 step 2): real Poynting power does not "
        "balance on this smoke fixture — dissipated 1.199162e-06 W against a "
        "net inward flux of -2.008179e-07 W (imbalance 116.7465%, and the flux "
        "has the wrong SIGN). `POST-5` step 1 (2026-08-18) discriminated the "
        "cause: the imbalance is h-independent (116.7465 / 115.4059 / "
        "114.4227% at h = 0.03 / 0.02 / 0.015, fitted rate 0.0290 against the "
        "pre-registered 0.7) and the sign never corrects => SOURCE/ASSEMBLY, "
        "so the band does NOT rescope to convergence. Band left strict so a "
        "fix shows as XPASS."
    ),
)
def test_time_harmonic_smoke_solve_conserves_real_power():
    """Solve a small frequency-domain case; real Poynting power balances.

    **This test is a finding, not a pass** (`OPS-17` step 2, 2026-08-17).
    Measured at `-n 2`, ``20260817T112448Z_OPS-17-step2-th-smoke2-n2.log``:

        dissipated  = +1.199162e-06 W   (1/2 int sigma |E|^2 dV)
        net inward  = -2.008179e-07 W   (-oint 1/2 Re(E x conj(H)).n dS)
        relative imbalance: 116.7465%   (pre-stated band 25%)

    The sign is the interesting part: real power leaves through the boundary
    while the medium dissipates, which the identity forbids for any solution of
    Maxwell's equations regardless of boundary condition. Two candidates, and
    the timebox did not allow separating them:

    1. **Resolution.** 0.16 m domain at h = 0.03 m is ~9 cells per in-medium
       wavelength, and the boundary leg is a curl trace — the least accurate
       quantity a degree-1 N1curl solution has. ``test_poynting_balance`` needs
       a refined mesh to reach 5%, and gates the *convergence* of this
       imbalance for exactly that reason.
    2. **The source.** The drive is an axial current in the inner cylinder that
       terminates on the end caps, so ``J.n != 0`` there — the same
       incompatibility ``test_gauge_lagrange`` measures on its wire fixture.

    An h-ladder distinguishes them in one command and belongs to a `TH`/`POST`
    chunk, not to `OPS-17` test hygiene. The band stays at the pre-stated value
    and the marker is ``strict=True``.

    `OPS-17` step 2 (2026-08-17). This was the step-1 table's second archetype
    of the finiteness-only pattern: solve, then assert ``isfinite(|E|)`` and
    ``max|E|`` above a floor.

    The table named "attenuation constant alpha from |E| at two depths vs the
    `TH-1`/`TH-6` lossy plane wave" as the anchor, with a standing instruction
    to delete instead if step 2 found that only duplicates the `TH-6` gate.
    Step 2's finding is the stronger version of that: **alpha is not
    measurable on this fixture at all.** There is no plane wave here — the
    source is an interior axial current in a cylinder, so the field decays by
    geometric spreading as well as by absorption, and the two are not separable
    from |E| at two depths. Building a fixture on which alpha *is* measurable
    means rebuilding ``tests/validation/test_lossy_plane_wave.py``, which
    already gates alpha to 5% at exactly this material and frequency
    (sigma = 0.7 S/m, eps_r = 78, f = 127.74 MHz).

    So the test was neither deleted nor given a duplicate anchor. It keeps the
    one thing it uniquely covers — the time-harmonic solver driven by an
    interior current on a *tagged cylindrical* mesh, the only such solve in the
    tree — and gates it on a conservation identity that is valid on any
    geometry and has no free parameters (`POST-3`):

        -oint 1/2 Re(E x conj(H)).n dS  =  1/2 int sigma |E|^2 dV

    The band is pre-stated. ``test_poynting_balance`` holds this identity to 5%
    on a refined mesh; this fixture is a 0.16 m domain at h = 0.03 m, roughly 9
    cells per in-medium wavelength (lambda = c/(f sqrt(78)) = 0.266 m), so 25%
    is the honest ceiling here. What makes a loose band meaningful is the
    negative control below it: the same field scored blind to sigma must miss
    the identity by an order of magnitude, which is what proves the metric is
    live on this fixture rather than trivially satisfied.
    """
    comm = MPI.COMM_WORLD

    mesh, cell_tags, facet_tags = MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.08,
        length=0.12,
        resolution=0.03,
        comm=comm,
    )

    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(
            sigma=SIGMA,
            epsilon_r=EPSILON_R,
            mu_r=1.0,
        ),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    def current_density(x):
        return ufl.as_vector([0.0, 0.0, 1.0])

    fields = solver.solve(current_density=current_density, subdomain_id=1, gauge_penalty=1e-3)

    # Interpolate to Lagrange space for robust point sampling.
    v_lagrange = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    e_imag_lagrange = fem.Function(v_lagrange, name="E_imag_lagrange")
    e_imag_lagrange.interpolate(fields.e_imag)

    sample_points = np.array(
        [
            [0.0, 0.0, -0.02],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.02],
            [0.005, 0.0, 0.0],
            [0.0, 0.005, 0.0],
        ],
        dtype=np.float64,
    )

    e_samples, valid_mask = evaluate_vector_field_parallel(e_imag_lagrange, sample_points, comm=comm)

    assert valid_mask.all(), (
        "Expected all smoke-test sample points to be evaluable, "
        f"but got {np.count_nonzero(valid_mask)}/{len(valid_mask)}"
    )

    e_mag = np.linalg.norm(e_samples, axis=1)
    max_mag = float(np.max(e_mag))
    mean_mag = float(np.mean(e_mag))

    # The real gate: a conservation identity on the solved phasor. Both sides
    # come from the same E but through different operators (a volume mass term
    # against a boundary curl trace), so this is a check on the solution, not
    # an algebraic tautology. Every integral inside is reduced across comm.
    honest = poynting_power_balance(
        fields.e_complex, omega=fields.omega, sigma=SIGMA, comm=comm
    )
    # Negative control: score the same field as if the medium were lossless.
    # The boundary flux is unchanged and the volume leg collapses to ~zero, so
    # a solve that is genuinely balanced must fail this by an order of
    # magnitude. If it does not, the identity is not live on this fixture and
    # the band above means nothing.
    #
    # SIGMA_BLIND is exactly 0.0 since `POST-5` step 1 (2026-08-18): the
    # 1e-12 * SIGMA workaround stood only because poynting_power_balance
    # raised on a scalar zero (known-issues, `OPS-17` step-2 defect 4). The
    # fix wraps the scalar in fem.Constant; the control below is now the
    # lossless medium it always claimed to be, and its volume leg is exactly
    # zero rather than twelve orders down.
    blind = poynting_power_balance(
        fields.e_complex, omega=fields.omega, sigma=SIGMA_BLIND, comm=comm
    )
    assert blind["dissipated_power_w"] == 0.0, (
        "the sigma-blind control dissipated "
        f"{blind['dissipated_power_w']:.6e} W at sigma = 0 exactly; the volume "
        "leg must vanish identically, not approximately"
    )

    if comm.rank == 0:
        print("\n[OPS-17] time-harmonic smoke diagnostics:")
        print(f"  frequency [Hz]: {problem.frequency_hz:.6e}")
        print(f"  |E_imag| min/max/mean at {len(sample_points)} points: "
              f"{np.min(e_mag):.6e} / {max_mag:.6e} / {mean_mag:.6e}")
        print(f"  dissipated  = {honest['dissipated_power_w']:.6e} W")
        print(f"  net inward  = {honest['net_inward_power_w']:.6e} W")
        print(f"  reactive    = {honest['reactive_inward_power_var']:.6e} var")
        print(f"  relative imbalance: honest {honest['relative_imbalance']:.4%}, "
              f"sigma-blind {blind['relative_imbalance']:.4%}", flush=True)

    assert honest["relative_imbalance"] < POYNTING_IMBALANCE_MAX, (
        f"real power in through the boundary "
        f"({honest['net_inward_power_w']:.6e} W) and Ohmic dissipation "
        f"({honest['dissipated_power_w']:.6e} W) disagree by "
        f"{honest['relative_imbalance']:.4%}, outside the pre-stated "
        f"{POYNTING_IMBALANCE_MAX:.0%} band for this coarse fixture"
    )
    assert blind["relative_imbalance"] > BLIND_SEPARATION * honest["relative_imbalance"], (
        f"scoring the same field with sigma = 0 gave an imbalance of only "
        f"{blind['relative_imbalance']:.4%} against the honest solve's "
        f"{honest['relative_imbalance']:.4%} — the identity is not sensitive "
        "to the loss it is supposed to be accounting for"
    )


def _smoke_mesh(resolution: float, comm):
    """The smoke fixture's cylindrical domain at one resolution."""
    return MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.08,
        length=0.12,
        resolution=resolution,
        comm=comm,
    )


def _azimuthal_current(mesh):
    """A **closed** loop drive for the smoke fixture: ``J = (-y, x, 0)/a``.

    `POST-5` step 2's discriminator.  The axial drive is an interior current
    that terminates on the end caps, so ``J.n != 0`` there; this one closes on
    itself inside the rod:

    * ``div J = 0`` pointwise — ``d/dx(-y) + d/dy(x) = 0`` identically;
    * ``J.n = 0`` on every boundary of the *domain* — the field is restricted
      to the inner-cylinder tag, and on the end caps (``n = +-z``) its
      z-component is identically zero anyway;
    * ``J.n = 0`` on the rod's own lateral surface — azimuthal is tangential
      to a coaxial cylinder — so the restriction to tag 1 introduces no
      surface divergence either.

    Returned as an interpolated **vector P1 Function**, not as a UFL expression
    in ``SpatialCoordinate``, for two reasons.  It is exact: the field is
    linear in x, so the P1 interpolant *is* the field, with no quadrature or
    representation error to confound the reading.  And it keeps
    ``SpatialCoordinate`` out of the assembled source and projection forms on
    this gmsh mesh, which is the trap that cost `POST-5` step 1 two windows
    (unpinned quadrature degree -> FFCx compile that never returned; see
    ``test_smoke_fixture_boundary_measure_is_outward_oriented``).  A coefficient
    from a P1 space carries its own degree estimate, so nothing is left to
    guess.
    """
    v_space = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    j = fem.Function(v_space, name="J_azimuthal")
    j.interpolate(
        lambda x: np.array(
            [-x[1] / INNER_RADIUS, x[0] / INNER_RADIUS, np.zeros_like(x[0])],
            dtype=dolfinx.default_scalar_type,
        )
    )
    return j


def _solve_smoke_and_balance(resolution: float, comm, drive: str = "axial"):
    """Solve the smoke fixture at ``resolution`` and score the identity.

    ``drive`` selects the source: ``"axial"`` is the fixture's own unit
    z-directed current (the one every record was measured on) and ``"azimuthal"``
    is `POST-5` step 2's closed loop, :func:`_azimuthal_current`.
    """
    mesh, cell_tags, facet_tags = _smoke_mesh(resolution, comm)
    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=1.0),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    if drive == "axial":
        def current_density(x):
            return ufl.as_vector([0.0, 0.0, 1.0])
    elif drive == "azimuthal":
        j_azimuthal = _azimuthal_current(mesh)

        def current_density(x):
            # The coefficient is already the field; x is the solver's
            # SpatialCoordinate and is deliberately unused.
            return j_azimuthal
    else:
        raise ValueError(f"unknown drive {drive!r}; use 'axial' or 'azimuthal'")

    fields = solver.solve(
        current_density=current_density, subdomain_id=1, gauge_penalty=1e-3
    )
    balance = poynting_power_balance(
        fields.e_complex, omega=fields.omega, sigma=SIGMA, comm=comm
    )
    blind = poynting_power_balance(
        fields.e_complex, omega=fields.omega, sigma=SIGMA_BLIND, comm=comm
    )
    tdim = mesh.topology.dim
    balance["ncells"] = int(
        comm.allreduce(mesh.topology.index_map(tdim).size_local, op=MPI.SUM)
    )
    balance["h"] = float(resolution)
    balance["drive"] = drive
    balance["blind_dissipated_w"] = blind["dissipated_power_w"]
    balance["mesh"] = mesh
    return balance


@complex_only
def test_smoke_fixture_boundary_measure_is_outward_oriented():
    """``ds``/``FacetNormal`` on the smoke mesh point *out*, exactly.

    Candidate (c) for the wrong-sign Poynting flux (known-issues 2026-08-17,
    `OPS-17` step-2 defect 3) is a flipped outward measure: if ``ufl.ds`` with
    ``ufl.FacetNormal`` were inward on this fixture, every boundary-flux sign
    in the repo would be reversed and the 116.7465% imbalance would be an
    artefact of the measure rather than of the solution.  The divergence
    theorem settles it with no free parameters and no solve —

        oint x . n dS = int div(x) dV = 3 |Omega|

    — so the ratio of the assembled surface integral to three times the
    assembled volume is exactly +1 for an outward normal and exactly -1 for an
    inward one.  Both legs use the same ``dx``/``ds`` pair the power balance
    uses.  Run before the h-ladder, per the step plan: this is the cheap
    candidate the wrong sign points at.
    """
    comm = MPI.COMM_WORLD
    mesh, _, _ = _smoke_mesh(LADDER_RESOLUTIONS[0], comm)

    normal = ufl.FacetNormal(mesh)
    position = ufl.SpatialCoordinate(mesh)
    # The quadrature degree is pinned rather than estimated. Left to UFL, the
    # SpatialCoordinate-times-FacetNormal integrand on this gmsh mesh sends
    # FFCx into a compile that had not finished after nine minutes
    # (`POST-5` step 1, 2026-08-18, logs 20260818T213256Z / 20260818T214040Z —
    # both windows died there and poisoned the JIT cache entry). Both legs are
    # exactly linear in x, so degree 2 integrates them without error.
    meta = {"quadrature_degree": 2}
    surface = comm.allreduce(
        fem.assemble_scalar(
            fem.form(ufl.dot(position, normal) * ufl.ds(metadata=meta))
        ),
        op=MPI.SUM,
    )
    # div(x) = 3 identically, so this volume leg *is* 3|Omega| and carries the
    # mesh without needing a scalar-type-matched Constant.
    volume3 = comm.allreduce(
        fem.assemble_scalar(
            fem.form(ufl.div(position) * ufl.dx(metadata=meta))
        ),
        op=MPI.SUM,
    )
    ratio = float(np.real(surface)) / float(np.real(volume3))

    if comm.rank == 0:
        print("\n[POST-5 step 1] ds orientation check on the smoke fixture:")
        print(f"  oint x.n dS = {float(np.real(surface)):.9e} m^3")
        print(f"  3 |Omega|   = {float(np.real(volume3)):.9e} m^3")
        print(f"  ratio       = {ratio:.12f}  (+1 outward, -1 inward)",
              flush=True)

    assert abs(ratio - 1.0) < 1.0e-10, (
        f"oint x.n dS / (3|Omega|) = {ratio:.12f} on the smoke fixture; the "
        "outward measure is not outward (or the mesh is not closed), which "
        "would make every boundary-flux sign in the power balance wrong"
    )


@complex_only
def test_poynting_imbalance_h_ladder_discriminates_resolution_from_source():
    """`POST-5` step 1: is the smoke fixture's power imbalance resolution?

    Three rungs of the smoke fixture, h in ``LADDER_RESOLUTIONS``, each solved
    and scored with the same identity that reads 116.7465% at the record rung.
    The classification band is pre-registered (PROJECT_PLAN §7 `POST-5`
    step 1, and ``LADDER_RATE_FOR_RESOLUTION`` above):

    * imbalance falling with a fitted rate >= 0.7 in h **and** the net inward
      flux turning positive on the finest rung  =>  RESOLUTION, and the xfail
      gate rescopes to convergence;
    * an h-independent imbalance, or a sign that never corrects  =>
      SOURCE/ASSEMBLY, and the fix is a follow-on step.

    The rate is fitted by least squares on log(imbalance) against log(h) over
    all three rungs.  This test asserts the two things that are true whatever
    the reading is — the sigma-blind control's volume leg is *exactly* zero
    (the `POST-5` step-1 anchor, defect 4's fix) and the three rungs really do
    refine — and prints the table; the classification itself is a reading
    recorded in the plan, not a gate, because the outcome is what the step is
    measuring.
    """
    comm = MPI.COMM_WORLD
    rungs = [_solve_smoke_and_balance(h, comm) for h in LADDER_RESOLUTIONS]

    log_h = np.log(np.array([r["h"] for r in rungs]))
    log_imb = np.log(np.array([r["relative_imbalance"] for r in rungs]))
    rate = float(np.polyfit(log_h, log_imb, 1)[0])
    sign_corrected = rungs[-1]["net_inward_power_w"] > 0.0
    verdict = (
        "RESOLUTION"
        if (rate >= LADDER_RATE_FOR_RESOLUTION and sign_corrected)
        else "SOURCE/ASSEMBLY"
    )

    if comm.rank == 0:
        print("\n[POST-5 step 1] Poynting h-ladder on the smoke fixture:")
        print("      h      cells    dissipated [W]   net inward [W]  sign   "
              "imbalance   blind diss [W]")
        for r in rungs:
            print(
                f"  {r['h']:.3f}  {r['ncells']:7d}   "
                f"{r['dissipated_power_w']:.6e}   "
                f"{r['net_inward_power_w']:+.6e}   "
                f"{'+' if r['net_inward_power_w'] > 0 else '-'}    "
                f"{r['relative_imbalance']:9.4%}   "
                f"{r['blind_dissipated_w']:.6e}"
            )
        print(f"  fitted rate in h: {rate:.4f} "
              f"(>= {LADDER_RATE_FOR_RESOLUTION} required for RESOLUTION)")
        print(f"  finest-rung flux sign corrected: {sign_corrected}")
        print(f"  VERDICT: {verdict}", flush=True)

    for r in rungs:
        assert r["blind_dissipated_w"] == 0.0, (
            f"at h = {r['h']} the sigma-blind control dissipated "
            f"{r['blind_dissipated_w']:.6e} W; at sigma = 0 exactly the volume "
            "leg must vanish identically, which is the `POST-5` step-1 anchor"
        )
    cells = [r["ncells"] for r in rungs]
    assert cells[0] < cells[1] < cells[2], (
        f"the ladder did not refine: cell counts {cells} are not increasing, "
        "so the fitted rate is not a rate in h"
    )


@complex_only
def test_closed_azimuthal_drive_discriminates_source_from_assembly():
    """`POST-5` step 2: is the wrong-sign Poynting flux the *source*?

    Step 1 excluded resolution (imbalance h-independent, fitted rate 0.0290
    against the pre-registered 0.7) and excluded a flipped outward measure
    (``oint x.n dS / 3|Omega| = 1.000000000000``).  What is left of defect 3 is
    candidate (b): the fixture's axial drive terminates on the end caps, so
    ``J.n != 0`` there — the same incompatibility ``test_gauge_lagrange``
    measures on its wire.  The cheap discriminator is to re-drive the *same*
    fixture, mesh and material with a source that has no such incompatibility
    and re-read the identity.

    Pre-registered band (PROJECT_PLAN §7 `POST-5` step 2):

    * imbalance collapsing under the xfail's 25% band **and** the net inward
      flux turning positive  =>  SOURCE — the defect is the drive's
      compatibility, and the smoke fixture's source is what changes;
    * imbalance persisting at O(100%) with the sign unmoved  =>  ASSEMBLY —
      the boundary leg itself is wrong, and the next probe is the curl trace
      against the `TH-6` plane wave, where both legs have closed forms;
    * anything in between is the finding, recorded per-drive and not forced.

    As in step 1 the classification is a *reading* recorded in the plan, not a
    gate.  What this test asserts is what must hold whatever the reading is:
    the sigma-blind control is exactly zero on the new drive too, and the axial
    drive re-run in the same session reproduces the coarse-rung record, so a
    difference between the two columns is the drive and nothing else.
    """
    comm = MPI.COMM_WORLD
    h = LADDER_RESOLUTIONS[0]
    axial = _solve_smoke_and_balance(h, comm, drive="axial")
    closed = _solve_smoke_and_balance(h, comm, drive="azimuthal")

    collapsed = closed["relative_imbalance"] < CLOSED_DRIVE_IMBALANCE_FOR_SOURCE
    sign_positive = closed["net_inward_power_w"] > 0.0
    if collapsed and sign_positive:
        verdict = "SOURCE"
    elif not collapsed and not sign_positive:
        verdict = "ASSEMBLY"
    else:
        verdict = "IN-BETWEEN"

    if comm.rank == 0:
        print("\n[POST-5 step 2] closed-drive discriminator, "
              f"smoke fixture at h = {h:.3f} ({axial['ncells']} cells):")
        print("   drive        dissipated [W]   net inward [W]  sign   "
              "imbalance   blind diss [W]")
        for r in (axial, closed):
            print(
                f"  {r['drive']:<11s}  {r['dissipated_power_w']:.6e}   "
                f"{r['net_inward_power_w']:+.6e}   "
                f"{'+' if r['net_inward_power_w'] > 0 else '-'}    "
                f"{r['relative_imbalance']:9.4%}   "
                f"{r['blind_dissipated_w']:.6e}"
            )
        print(f"  closed-drive imbalance under "
              f"{CLOSED_DRIVE_IMBALANCE_FOR_SOURCE:.0%}: {collapsed}; "
              f"flux sign positive: {sign_positive}")
        print(f"  VERDICT: {verdict}", flush=True)

    # The `POST-5` step-1 anchor, re-asserted on the new drive.
    assert closed["blind_dissipated_w"] == 0.0, (
        "the sigma-blind control on the closed azimuthal drive dissipated "
        f"{closed['blind_dissipated_w']:.6e} W; at sigma = 0 exactly the "
        "volume leg must vanish identically"
    )
    # Negative control: the axial drive, same run, same mesh, reproduces the
    # step-1 coarse rung.  Without this the two columns could differ for any
    # reason; with it, the only thing that changed is J.
    assert np.isclose(
        axial["dissipated_power_w"], AXIAL_RECORD_DISSIPATED_W, rtol=1e-6
    ), (
        f"axial dissipated {axial['dissipated_power_w']:.6e} W against the "
        f"`POST-5` step-1 record {AXIAL_RECORD_DISSIPATED_W:.6e} W"
    )
    assert np.isclose(
        axial["net_inward_power_w"], AXIAL_RECORD_NET_INWARD_W, rtol=1e-6
    ), (
        f"axial net inward {axial['net_inward_power_w']:.6e} W against the "
        f"`POST-5` step-1 record {AXIAL_RECORD_NET_INWARD_W:.6e} W"
    )
    assert np.isclose(
        axial["relative_imbalance"], AXIAL_RECORD_IMBALANCE, rtol=1e-6
    ), (
        f"axial imbalance {axial['relative_imbalance']:.4%} against the "
        f"`POST-5` step-1 record {AXIAL_RECORD_IMBALANCE:.4%}"
    )


def test_time_harmonic_solver_rejects_non_hz_frequency_unit_before_solve():
    """API should fail fast when users pass non-Hz units to avoid silent mistakes."""
    comm = MPI.COMM_WORLD

    mesh, _, _ = MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.08,
        length=0.12,
        resolution=0.03,
        comm=comm,
    )

    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=127.74e6,
        frequency_unit="rad/s",
        material=HomogeneousMaterial(sigma=0.7, epsilon_r=78.0, mu_r=1.0),
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    with pytest.raises(ValueError, match="frequency_unit"):
        solver.solve()


def test_time_harmonic_solver_rejects_material_map_without_cell_tags_before_solve():
    """Material-map API should explain that cell tags are required for tag assignments."""
    comm = MPI.COMM_WORLD

    mesh, _, _ = MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.08,
        length=0.12,
        resolution=0.03,
        comm=comm,
    )

    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=127.74e6,
        material=HomogeneousMaterial(sigma=0.7, epsilon_r=78.0, mu_r=1.0),
        material_map={3: HomogeneousMaterial(sigma=1.2, epsilon_r=68.0, mu_r=1.0)},
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    with pytest.raises(ValueError, match="material_map requires problem.cell_tags"):
        solver.solve()


def test_time_harmonic_solver_rejects_unknown_material_map_tag_before_solve():
    """Material-map API should report unknown tags with known-tag diagnostics."""
    comm = MPI.COMM_WORLD

    mesh, cell_tags, facet_tags = MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.08,
        length=0.12,
        resolution=0.03,
        comm=comm,
    )

    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=127.74e6,
        material=HomogeneousMaterial(sigma=0.7, epsilon_r=78.0, mu_r=1.0),
        material_map={999: HomogeneousMaterial(sigma=1.2, epsilon_r=68.0, mu_r=1.0)},
        cell_tags=cell_tags,
        facet_tags=facet_tags,
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    with pytest.raises(ValueError, match="material_map references tags"):
        solver.solve()


# ---------------------------------------------------------------------------
# `POST-5` step 3, reconciliation leg: why does this fixture read ~106-117%
# while `tests/validation/test_poynting_balance.py` holds the same identity to
# 5% on a refined mesh?
#
# The step plan named the small-denominator hypothesis first (net flux ~6x
# below dissipation, so `power_scale_w` is set by the volume leg and a small
# absolute boundary error reads as O(100%)).  It is checked here against a
# second, structural candidate that the step-1/step-2 discriminators cannot
# distinguish because *both* their drives are impressed currents.  Poynting's
# theorem for e^{+jwt} with an impressed source is
#
#     div(1/2 E x Hbar) = -1/2 sigma|E|^2 - 1/2 E.Jbar - 2jw(w_m - w_e)
#
# so the real part integrates to
#
#     -oint 1/2 Re(E x Hbar).n dS  =  1/2 int sigma|E|^2 dV  +  1/2 Re int E.Jbar dV
#                                     \_____ P_diss _____/     \____ P_source ____/
#
# `poynting_power_balance` scores only the first term on the right, which is
# the *source-free* identity.  On the `TH-6` fixture that is correct: the plane
# wave is an exact source-free solution and J = 0, so the omitted term is
# identically zero and the 5% gate is honest.  On this fixture J != 0 over the
# inner conductor, so the omitted term is not zero and the identity as scored
# is not the identity this problem satisfies.
#
# Pre-registered band, written before the run: the residual of the *full*
# three-term statement, relative to the largest of the three magnitudes, below
# `SOURCE_TERM_RESIDUAL_MAX` = 25% (the xfail's own band, so the reading is
# scored no more leniently than the gate it explains)
#   => the smoke fixture's imbalance is the **missing impressed-source term**,
#      not a defective boundary assembly;
# at or above 25% => the source term does not account for it and the ASSEMBLY
# verdict of step 2 stands unexplained.  No fix lands here: the xfail's 25%
# band and strict=True do not move.
SOURCE_TERM_RESIDUAL_MAX = 0.25


def _solve_smoke_with_source_power(resolution: float, comm, drive: str = "axial"):
    """The smoke solve, plus the impressed-source power 1/2 Re int E.Jbar dV.

    A near-copy of :func:`_solve_smoke_and_balance` rather than a refactor of
    it: that helper owns three recorded `POST-5` rows and this step is
    attribution only, so it is left byte-identical.  Neither form here carries
    a `SpatialCoordinate` (the axial drive is a `Constant`-like `as_vector` of
    literals, the azimuthal one an interpolated P1 coefficient), so the step-1
    unpinned-quadrature trap is dodged by construction.
    """
    mesh, cell_tags, facet_tags = _smoke_mesh(resolution, comm)
    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=1.0),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    if drive == "axial":
        j_expr = ufl.as_vector([0.0, 0.0, 1.0])

        def current_density(x):
            return j_expr
    elif drive == "azimuthal":
        j_azimuthal = _azimuthal_current(mesh)
        j_expr = j_azimuthal

        def current_density(x):
            return j_azimuthal
    else:
        raise ValueError(f"unknown drive {drive!r}; use 'axial' or 'azimuthal'")

    fields = solver.solve(
        current_density=current_density, subdomain_id=1, gauge_penalty=1e-3
    )
    balance = poynting_power_balance(
        fields.e_complex, omega=fields.omega, sigma=SIGMA, comm=comm
    )

    # 1/2 Re int_{tag 1} E . conj(J) dV, over exactly the measure the solver
    # assembled the source on.  ufl.inner conjugates its second argument, which
    # is the conjugation this term needs.
    dx_src = ufl.Measure("dx", domain=mesh, subdomain_data=cell_tags)(1)
    source_form = fem.form(0.5 * ufl.inner(fields.e_complex, j_expr) * dx_src)
    source_c = comm.allreduce(fem.assemble_scalar(source_form), op=MPI.SUM)

    balance["source_power_w"] = float(np.real(source_c))
    balance["drive"] = drive
    tdim = mesh.topology.dim
    balance["ncells"] = int(
        comm.allreduce(mesh.topology.index_map(tdim).size_local, op=MPI.SUM)
    )
    return balance


@complex_only
@pytest.mark.integration
def test_the_missing_impressed_source_term_accounts_for_the_smoke_imbalance():
    """`POST-5` step 3: close the *full* balance on the driven fixture.

    Both `POST-5` drives are scored here.  The quantity asserted on is the
    residual of

        net_inward_flux  -  (P_diss + P_source)

    over the largest of the three magnitudes.  See the module comment above
    for the pre-registered band and both verdicts.
    """
    comm = MPI.COMM_WORLD

    rows = [
        _solve_smoke_with_source_power(LADDER_RESOLUTIONS[0], comm, drive=drive)
        for drive in ("axial", "azimuthal")
    ]

    residuals = []
    for row in rows:
        diss = row["dissipated_power_w"]
        flux = row["net_inward_power_w"]
        src = row["source_power_w"]
        scale = max(abs(diss), abs(flux), abs(src))
        residuals.append(abs(flux - (diss + src)) / scale if scale > 0.0 else float("inf"))

    if comm.rank == 0:
        print("\n[POST-5 step 3] full balance on the driven smoke fixture:")
        for row, res in zip(rows, residuals):
            print(
                f"  {row['drive']:>9s} ({row['ncells']:5d} cells): "
                f"dissipated = {row['dissipated_power_w']:.6e} W, "
                f"net inward = {row['net_inward_power_w']:.6e} W, "
                f"source = {row['source_power_w']:.6e} W, "
                f"two-term imbalance = {row['relative_imbalance']:.4%}, "
                f"three-term residual = {res:.4%}"
            )
        verdict = (
            "MISSING SOURCE TERM"
            if max(residuals) < SOURCE_TERM_RESIDUAL_MAX
            else "UNEXPLAINED (assembly verdict stands)"
        )
        print(f"  step-3 reconciliation verdict: {verdict}")

    for row, res in zip(rows, residuals):
        assert res < SOURCE_TERM_RESIDUAL_MAX, (
            f"the {row['drive']} drive's full three-term balance leaves a "
            f"residual of {res:.4%}, at or above the pre-registered "
            f"{SOURCE_TERM_RESIDUAL_MAX:.0%} — the omitted impressed-source "
            f"term (1/2 Re int E.Jbar = {row['source_power_w']:.6e} W) does not "
            f"account for the {row['relative_imbalance']:.4%} two-term "
            "imbalance, so step 2's ASSEMBLY verdict stands unexplained"
        )
