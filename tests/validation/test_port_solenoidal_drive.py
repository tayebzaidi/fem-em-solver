"""`PORT-1` step 2e: drive the two-torus fixture with the solenoidal projection.

Step 2b localised the fixture's ``Im Z₁₁ = −40.9 Ω`` entirely to the electric
half (``4ωW_e/I² = 48.52 Ω`` against a physical ``4ωW_m/I² = 7.437 Ω``), and
step 2d charged that excess to the **current representation**: one CG1 Poisson
solve gave the gradient part ``P_G J`` of the discretised load, and
``‖P_G J‖²/(ωε₀I²) = 4.852262e+01 Ω`` against the measured ``4.852271e+01 Ω`` —
ratio **0.999998**, i.e. the whole of it, with no residue for a second
mechanism.

This step acts on that diagnosis.  Drive the *same* fixture with

    J′ = J − P_G J = J − ∇ψ,     ∫∇ψ·∇q = ∫J·∇q  ∀ q ∈ CG1 ∩ H¹₀      (4)

which is divergence-free **weakly against CG1** — not pointwise, and that is
exactly the subspace the load vector sees, since the N1curl/CG1 pair makes
``∇q`` an admissible test function for every interior ``q`` (step 2d, eq. (2)).
Re-solve once and re-measure the diagonal.  Step 2d's prediction is arithmetic
rather than hopeful: removing the gradient content removes ``W_e^spur``, so

    Im Z₁₁ → 4ωW_m/I′² ≈ +7.44 Ω,

within ~9% of Grover's ``ωL = 6.818 Ω`` for this loop — a sign flip plus
48.5 Ω of movement against the unprojected drive.

**Negative control — executed history, deliberately not re-run.**  The
unprojected drive on this exact mesh, padding and frequency measured
``Im Z₁₁ = −4.108550e+01 Ω`` with ``4ωW_e/I² = 4.852271e+01 Ω``
(``20260803T050252Z_PORT-1-step2b-gate.log``,
``20260803T183556Z_PORT-1-step2d-gate.log``).  The separation this file must
clear is therefore total in sign and ~48.5 Ω in magnitude, and the spurious
load 4.852262e+01 Ω is the arithmetic ceiling of what the projection can
remove.  Re-solving it here would cost a second curl-curl solve to reproduce a
number already on record at the same commit-time fixture.

**What is gated.**

1. ``Im Z₁₁ > 0`` — gateable a priori.  A lossless loop is inductive; the whole
   anomaly was that it was not.
2. The complex-power identity ``Im Z₁₁ = 4ω(W_m − W_e)/I′²`` against the
   reaction integral ``−(1/I′²)∫E·J′``, to 1e-9 (step 2b's house bound, met
   there at 1.8e-10).  Exact for the discrete solution, so it gates the
   *bookkeeping* of the new drive — a wrong ``I′``, a measure that missed the
   projection term, or an unreduced rank cancels in neither route.
3. ``‖P_G J′‖²/‖J′‖²`` — the projection's own near-exact anchor.  A second
   Poisson solve on ``J′`` must return ``P_G J′ = P_G J − P_G²J = 0`` up to
   solve accuracy, since ``P_G`` is idempotent by construction.  Banded from
   the probe.
4. ``Im Z₁₁`` against Grover's ``ωL = 6.818 Ω``, banded from the probe
   measurement rather than from the plan's ~9% guess (house precedent: `GEO-9`
   step 1).  The PEC box at padding 0.08 m perturbs the isolated-loop
   inductance by an amount nobody has measured, so the band is a statement
   about *this* fixture, not about Grover.

**Traps handled here** (from the §7 plan): the meshed current of ``J′`` is
**not** step 2d's 0.969009 A — the projection has an azimuthal component inside
the torus — so ``I′`` is re-measured with the same cross-section integral and
both are printed; ``ψ`` is real to round-off but lives in a complex space, so
its imaginary part is discarded explicitly (and the discarded magnitude
reported) which makes ``ufl.inner``'s conjugation of ``J′`` a true no-op as it
already is for ``J``; the driven-tag restriction is carried into the
whole-domain load by a **DG0 indicator**, exact for a cellwise tag, because
``J′`` has support everywhere while ``J`` does not.

**The answer this file returned (2026-08-04).**  The prediction, to three
figures: ``Im Z₁₁ = +7.437243 Ω`` on both routes (step 2d predicted +7.44),
ratio to Grover **1.090770**, identity residual 1.6242e-14.  The electric half
is gone rather than reduced — ``4ωW_e/I′² = 8.761041e-05 Ω`` against the
unprojected 4.852271e+01 Ω, a factor 5.5e5 — and ``‖P_G J′‖²/‖J′‖² =
4.5758e-33`` says the driven current really is solenoidal in the CG1-weak
sense.  ``I′ = 0.969001 A`` against ``I = 0.969009 A``: the projection's
azimuthal content inside the torus is 8 ppm, far smaller than the trap in the
plan anticipated, but it was measured rather than assumed.  So the negative
diagonal was the current representation and nothing else, and the fixture's
inductance was physical all along — ``4ωW_m/I²`` is unchanged from step 2b's
7.437 Ω, as it must be: the projection moves ``W_e``, not ``W_m``.

Scope: this **closes nothing** — not `PORT-1`, not the diagonal gate on the
*production* port path, not known-issues 8.  The production driver still builds
the unprojected load; a green 2e licenses making the projection the
port-excitation default, which is its own step.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_solenoidal_drive.py -v -s'
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import ufl
from mpi4py import MPI

import dolfinx
from dolfinx import fem
from dolfinx.fem.petsc import LinearProblem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.core.resonance import stored_electric_energy
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.constants import EPSILON_0

from tests.complex_mode import complex_only
from tests.validation.test_port_reaction_impedance import (
    AIR_PADDING,
    CURRENT_A,
    FREQUENCY_HZ,
    H_FAR,
    H_WIRE,
    MAJOR_RADIUS,
    MINOR_RADIUS,
    OMEGA,
    SEPARATION,
    _azimuthal_current_density,
    _tag_volume,
)
from tests.validation.test_port_self_impedance_energy import (
    DRIVEN_TAG,
    grover_loop_inductance,
    stored_magnetic_energy,
)

# Executed history on this exact fixture — the negative control, cited not
# re-run (see the module docstring).
UNPROJECTED_IM_Z11_OHM = -4.108550e01  # 20260803T050252Z_PORT-1-step2b-gate.log:436
UNPROJECTED_SPUR_OHM = 4.852262e01  # 20260803T183556Z_PORT-1-step2d-gate.log

# Step 2b's house bound for the complex-power identity, met there at 1.8128e-10.
# Both routes are built from the same solved field, so this is solve accuracy
# plus quadrature agreement; any bookkeeping error in I' is O(1).
IDENTITY_TOLERANCE = 1e-9

# Banded from the probe run (20260804T050406Z_PORT-1-step2e-probe2.log:442-444),
# -n 2, 119738 cells.
#
# ||P_G J'||^2/||J'||^2 measured 4.5758e-33 — not solve accuracy but structural:
# the second Poisson solve's right-hand side ∫J'·∇q is annihilated at *assembly*
# for every interior q, so what is left is the round-off of that cancellation,
# not the residual of an LU solve.  1e-24 keeps nine orders of margin over the
# measurement while sitting 18 orders below the unprojected drive's own value
# (2.534713e-02/3.100805e+03 = 8.175e-06), so the control separation is 27
# orders.  A rank-count or mesh change that lifts this to solve accuracy
# (~1e-18 of the same ratio) is information: re-measure and record.
PROJECTION_RESIDUAL_TOLERANCE = 1e-24

# Im Z11/omega*L_Grover measured 1.090770.  Banded ±4.5% around it rather than
# from step 2d's ~9% prose estimate: the number is a statement about *this*
# fixture (PEC box at padding 0.08 m, which perturbs the isolated-loop
# inductance by an unmeasured amount), and its stability is measured rather
# than assumed — step 2b's independent 4*omega*W_m/I^2 on the *unprojected*
# drive gave the same 1.0908 (7.437 Ohm), because the projection changes W_e,
# not W_m.
GROVER_RATIO_BAND = (1.042, 1.140)

# 4*omega*W_e/I'^2 measured 8.761041e-05 Ohm against the unprojected drive's
# 4.852271e+01 Ohm — a collapse by 5.5e5.  Gated at 1e-4 of the control (a 56x
# margin on the measurement) as an *independent* witness to the projection
# working: this number comes out of the curl-curl solve, while the residual
# above comes out of the Poisson solves.
UNPROJECTED_ELECTRIC_OHM = 4.852271e01  # 20260803T050252Z_PORT-1-step2b-gate.log:436
ELECTRIC_COLLAPSE_FRACTION = 1e-4


def _solve_gradient_potential(q_space, msh, rhs_form):
    """``ψ ∈ CG1 ∩ H¹₀`` with ``∫∇ψ·∇q = rhs_form`` — the ``P_G`` of step 2d.

    Same machinery as ``test_port_gradient_load.py`` (direct LU, homogeneous
    Dirichlet on the exterior facets: the PEC wall pins ``φ``, so ``H¹₀`` is the
    space in which ``∇q`` is an admissible N1curl test function).  Factored out
    because step 2e needs it twice — once to build ``J′`` and once to verify
    that ``P_G J′`` vanishes.  The imaginary part of ``ψ`` is round-off (the
    right-hand side is real), and is discarded here so that ``∇ψ`` is exactly
    real and ``ufl.inner``'s conjugation of ``J′`` is a genuine no-op; the
    discarded magnitude is returned so it can be reported rather than assumed.
    """
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    facets = dolfinx.mesh.exterior_facet_indices(msh.topology)
    bdofs = fem.locate_dofs_topological(q_space, tdim - 1, facets)
    zero = fem.Function(q_space)
    zero.x.array[:] = 0.0
    problem = LinearProblem(
        ufl.inner(ufl.grad(ufl.TrialFunction(q_space)), ufl.grad(ufl.TestFunction(q_space)))
        * ufl.dx,
        rhs_form,
        bcs=[fem.dirichletbc(zero, bdofs)],
        petsc_options={
            "ksp_type": "preonly",
            "pc_type": "lu",
            "pc_factor_mat_solver_type": "mumps",
        },
    )
    psi = problem.solve()
    psi.x.scatter_forward()
    n_owned = q_space.dofmap.index_map.size_local
    local_imag = float(np.max(np.abs(np.imag(psi.x.array[:n_owned])))) if n_owned else 0.0
    local_real = float(np.max(np.abs(np.real(psi.x.array[:n_owned])))) if n_owned else 0.0
    comm = msh.comm
    imag_max = comm.allreduce(local_imag, op=MPI.MAX)
    real_max = comm.allreduce(local_real, op=MPI.MAX)
    psi.x.array[:] = np.real(psi.x.array)
    psi.x.scatter_forward()
    return psi, (imag_max / real_max if real_max > 0.0 else 0.0)


def _reduced_real(form, comm) -> float:
    """``assemble_scalar`` is rank-local — reduce, then take the real part."""
    return float(np.real(comm.allreduce(fem.assemble_scalar(fem.form(form)), op=MPI.SUM)))


@pytest.fixture(scope="module")
def solenoidal_drive():
    """One mesh, two CG1 Poisson solves, one curl-curl solve on ``J′``."""
    comm = MPI.COMM_WORLD
    t_mesh = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=H_FAR,
        air_padding=AIR_PADDING,
        wire_resolution=H_WIRE,
        far_resolution=H_FAR,
        comm=comm,
    )
    t_mesh = time.perf_counter() - t_mesh

    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)

    j_magnitude = CURRENT_A / (np.pi * MINOR_RADIUS**2)
    volume = _tag_volume(msh, cell_tags, DRIVEN_TAG, comm)
    # Step 2d's meshed current, for reference only: I' is re-measured below.
    current_unprojected = j_magnitude * volume / (2.0 * np.pi * MAJOR_RADIUS)

    x = ufl.SpatialCoordinate(msh)
    j_vec = _azimuthal_current_density(j_magnitude)(x)
    phi_hat = _azimuthal_current_density(1.0)(x)
    dx_driven = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(DRIVEN_TAG,)
    )

    # The driven-tag restriction as a DG0 indicator.  J' has support on the
    # whole domain (grad(psi) does), so the load can no longer be written on a
    # tagged measure; chi is exact for a cellwise tag, so chi*J on ufl.dx is the
    # same integrand as J on dx_driven, cell for cell.
    dg0 = fem.functionspace(msh, ("DG", 0))
    chi = fem.Function(dg0, name="driven_indicator")
    chi.x.array[:] = 0.0
    chi.x.array[cell_tags.find(DRIVEN_TAG)] = 1.0
    chi.x.scatter_forward()

    q_space = fem.functionspace(msh, ("Lagrange", 1))
    q = ufl.TestFunction(q_space)

    comm.Barrier()
    t_poisson1 = time.perf_counter()
    psi, psi_imag_ratio = _solve_gradient_potential(
        q_space, msh, ufl.inner(j_vec, ufl.grad(q)) * dx_driven
    )
    comm.Barrier()
    t_poisson1 = time.perf_counter() - t_poisson1

    j_prime = chi * j_vec - ufl.grad(psi)

    # --- The re-measured meshed current I'. -----------------------------------
    # Same cross-section integral as step 2d — the azimuthal current averaged
    # over the loop's length — applied to J' rather than J.  The projection has
    # an azimuthal component inside the torus, so this is NOT 0.969009 A.
    current = _reduced_real(ufl.inner(j_prime, phi_hat) * dx_driven, comm) / (
        2.0 * np.pi * MAJOR_RADIUS
    )

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map=None,
        boundary_condition="pec_zero_tangential_a",
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    comm.Barrier()
    t_solve = time.perf_counter()
    # subdomain_ids=None: the load is assembled over the whole domain because
    # J' is supported there.  The callable ignores its argument — j_prime is
    # already a UFL expression on this mesh's SpatialCoordinate.
    # project_source=False: this file does the projection by hand — that is its
    # subject — so the step-2f default would apply P_G a second time.  It is
    # idempotent (test_projection_is_idempotent_on_its_own_output measures
    # 4.6e-33), so the difference would be round-off and one wasted Poisson
    # solve; off explicitly so the file keeps measuring its own recipe.
    fields = solver.solve(current_density=lambda _x: j_prime, project_source=False)
    comm.Barrier()
    t_solve = time.perf_counter() - t_solve

    # --- Route A: the reaction integral on the projected drive. ---------------
    # J' is real (psi's imaginary part was discarded), so inner()'s conjugation
    # of the second argument is a no-op: this is ∫E·J', not ∫E·J̄'.
    reaction_local = fem.assemble_scalar(
        fem.form(ufl.inner(fields.e_complex, j_prime) * ufl.dx)
    )
    z11_reaction = complex(-comm.allreduce(reaction_local, op=MPI.SUM) / current**2)

    # --- Route B: complex power, equation (1) of step 2b. ---------------------
    w_e = stored_electric_energy(fields, comm=comm)
    w_m = stored_magnetic_energy(fields.e_complex, comm)
    im_z11_energy = 4.0 * OMEGA * (w_m - w_e) / current**2
    x_electric = 4.0 * OMEGA * w_e / current**2
    x_magnetic = 4.0 * OMEGA * w_m / current**2

    # --- The projection's own anchor: P_G J' = P_G J − P_G²J = 0. -------------
    comm.Barrier()
    t_poisson2 = time.perf_counter()
    psi_prime, psi_prime_imag_ratio = _solve_gradient_potential(
        q_space, msh, ufl.inner(j_prime, ufl.grad(q)) * ufl.dx
    )
    comm.Barrier()
    t_poisson2 = time.perf_counter() - t_poisson2

    pg_prime_norm2 = _reduced_real(
        ufl.inner(ufl.grad(psi_prime), ufl.grad(psi_prime)) * ufl.dx, comm
    )
    j_prime_norm2 = _reduced_real(ufl.inner(j_prime, j_prime) * ufl.dx, comm)
    pg_norm2 = _reduced_real(ufl.inner(ufl.grad(psi), ufl.grad(psi)) * ufl.dx, comm)
    projection_residual = pg_prime_norm2 / j_prime_norm2
    x_spurious = pg_prime_norm2 / (OMEGA * EPSILON_0 * current**2)

    omega_l_grover = OMEGA * grover_loop_inductance(MAJOR_RADIUS, MINOR_RADIUS)

    if comm.rank == 0:
        print(
            f"\n[PORT-1 step 2e] padding {AIR_PADDING} m, h_far {H_FAR} m, "
            f"{ncells} cells, mesh {t_mesh:.1f} s, curl-curl solve {t_solve:.1f} s, "
            f"Poisson solves {t_poisson1:.1f} s / {t_poisson2:.1f} s",
            flush=True,
        )
        print(
            f"[PORT-1 step 2e] meshed current: I (unprojected, step 2d) = "
            f"{current_unprojected:.6f} A, I' (projected) = {current:.6f} A, "
            f"ratio {current / current_unprojected:.6f}; "
            f"Im(psi)/max|psi| = {psi_imag_ratio:.3e}, "
            f"Im(psi')/max|psi'| = {psi_prime_imag_ratio:.3e}",
            flush=True,
        )
        print(
            f"[PORT-1 step 2e] ||P_G J||^2 = {pg_norm2:.6e}, "
            f"||P_G J'||^2 = {pg_prime_norm2:.6e}, ||J'||^2 = {j_prime_norm2:.6e}, "
            f"||P_G J'||^2/||J'||^2 = {projection_residual:.4e}; "
            f"4*omega*W_e^spur/I'^2 = {x_spurious:.6e} Ohm "
            f"(unprojected: {UNPROJECTED_SPUR_OHM:.6e} Ohm)",
            flush=True,
        )
        print(
            f"[PORT-1 step 2e] W_m = {w_m:.6e} J, W_e = {w_e:.6e} J, "
            f"4*omega*W_m/I'^2 = {x_magnetic:+.6e} Ohm, "
            f"4*omega*W_e/I'^2 = {x_electric:+.6e} Ohm",
            flush=True,
        )
        print(
            f"[PORT-1 step 2e] Z11 (reaction) = {z11_reaction:+.6e} Ohm; "
            f"Im Z11 (energy) = {im_z11_energy:+.6e} Ohm; "
            f"Grover omega*L = {omega_l_grover:+.6e} Ohm "
            f"(ratio {im_z11_energy / omega_l_grover:.6f}); "
            f"unprojected control = {UNPROJECTED_IM_Z11_OHM:+.6e} Ohm",
            flush=True,
        )
    return {
        "z11_reaction": z11_reaction,
        "im_z11_energy": im_z11_energy,
        "x_magnetic": x_magnetic,
        "x_electric": x_electric,
        "x_spurious": x_spurious,
        "projection_residual": projection_residual,
        "current": current,
        "current_unprojected": current_unprojected,
        "omega_l_grover": omega_l_grover,
        "w_m": w_m,
        "w_e": w_e,
    }


@complex_only
def test_projected_drive_diagonal_is_inductive(solenoidal_drive):
    """``Im Z₁₁ > 0`` on both routes — gateable a priori, and the whole point.

    A lossless loop stores more magnetic than electric energy; the unprojected
    drive measured ``−41.086 Ω`` on this same mesh, so the sign alone is a
    total separation against the executed control.  Asserted on both the
    reaction integral and the complex-power route so that neither a sign slip
    in the reaction bookkeeping nor one in the energies can pass alone.
    """
    reaction = solenoidal_drive["z11_reaction"].imag
    energy = solenoidal_drive["im_z11_energy"]
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 2e] Im Z11: reaction {reaction:+.6e} Ohm, "
            f"energy {energy:+.6e} Ohm (control {UNPROJECTED_IM_Z11_OHM:+.6e} Ohm)",
            flush=True,
        )
    assert reaction > 0.0, (
        f"Im Z11 (reaction) = {reaction:.6e} Ohm is not inductive; the projection "
        f"did not repair the sign (unprojected control {UNPROJECTED_IM_Z11_OHM:.6e})"
    )
    assert energy > 0.0, (
        f"Im Z11 (energy) = {energy:.6e} Ohm is not inductive; W_e = "
        f"{solenoidal_drive['w_e']:.6e} J still exceeds W_m = "
        f"{solenoidal_drive['w_m']:.6e} J"
    )


@complex_only
def test_complex_power_identity_holds_on_the_projected_drive(solenoidal_drive):
    """``Im Z₁₁ = 4ω(W_m − W_e)/I′²`` to 1e-9 — step 2b's identity, re-run.

    Exact for the discrete solution, so on the new drive it gates the
    *bookkeeping*: the reaction route integrates ``E·J′`` over the whole domain
    while the energy route never sees ``J′`` at all, so a wrong ``I′`` cancels
    (it divides both), but a load assembled on the wrong measure, a missed
    projection term, or an unreduced rank does not.
    """
    reaction = solenoidal_drive["z11_reaction"].imag
    energy = solenoidal_drive["im_z11_energy"]
    relative = abs(reaction - energy) / abs(reaction)
    if MPI.COMM_WORLD.rank == 0:
        print(f"[PORT-1 step 2e] identity residual = {relative:.4e}", flush=True)
    assert relative < IDENTITY_TOLERANCE, (
        f"complex-power identity broken on the projected drive: reaction "
        f"{reaction:.6e} Ohm vs energy {energy:.6e} Ohm, relative {relative:.4e}"
    )


@complex_only
def test_projection_is_idempotent_on_its_own_output(solenoidal_drive):
    """``‖P_G J′‖²/‖J′‖²`` — ``P_G`` applied twice must return zero.

    ``P_G J′ = P_G J − P_G²J``, and ``P_G`` is a projection by construction, so
    this vanishes up to the accuracy of the two Poisson solves.  It is the
    near-exact anchor of the step: it says the thing being driven really is the
    solenoidal part, independently of anything the curl-curl solve returns.
    Banded from the probe run.
    """
    residual = solenoidal_drive["projection_residual"]
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 2e] ||P_G J'||^2/||J'||^2 = {residual:.4e}; "
            f"4*omega*W_e^spur/I'^2 = {solenoidal_drive['x_spurious']:.6e} Ohm "
            f"vs unprojected {UNPROJECTED_SPUR_OHM:.6e} Ohm",
            flush=True,
        )
    assert residual < PROJECTION_RESIDUAL_TOLERANCE, (
        f"P_G is not idempotent on its own output: {residual:.4e} exceeds "
        f"{PROJECTION_RESIDUAL_TOLERANCE:.0e}"
    )


@complex_only
def test_spurious_electric_energy_collapses(solenoidal_drive):
    """``4ωW_e/I′²`` collapses against the unprojected drive's 48.52 Ω.

    The independent witness: this number is read off the *curl-curl* solve,
    while :func:`test_projection_is_idempotent_on_its_own_output` is read off
    the Poisson solves.  Step 2d measured that the gradient content of the load
    accounts for the electric-energy excess to two parts in a million, so
    removing it must remove essentially all of ``W_e`` — measured
    **8.761041e-05 Ω** against 4.852271e+01 Ω, a factor 5.5e5.  Gated as a
    fraction of the executed control rather than as an absolute reactance, so
    the assertion carries the comparison it is actually making.
    """
    x_electric = solenoidal_drive["x_electric"]
    fraction = x_electric / UNPROJECTED_ELECTRIC_OHM
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 2e] 4*omega*W_e/I'^2 = {x_electric:.6e} Ohm = "
            f"{fraction:.4e} of the unprojected {UNPROJECTED_ELECTRIC_OHM:.6e} Ohm",
            flush=True,
        )
    assert fraction < ELECTRIC_COLLAPSE_FRACTION, (
        f"the electric-energy excess did not collapse: 4*omega*W_e/I'^2 = "
        f"{x_electric:.6e} Ohm is {fraction:.4e} of the unprojected "
        f"{UNPROJECTED_ELECTRIC_OHM:.6e} Ohm"
    )


@complex_only
def test_projected_diagonal_against_grover(solenoidal_drive):
    """``Im Z₁₁`` against Grover's ``ωL = 6.818 Ω``, banded from the probe.

    Step 2d predicted ``Im Z₁₁ → 4ωW_m/I′² ≈ +7.44 Ω`` once ``W_e^spur`` is
    removed, i.e. ~9% above Grover — but the PEC box at padding 0.08 m perturbs
    the isolated-loop inductance by an unmeasured amount, so the band is set
    from the measurement, not from that estimate.
    """
    energy = solenoidal_drive["im_z11_energy"]
    ratio = energy / solenoidal_drive["omega_l_grover"]
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 2e] Im Z11 / Grover omega*L = {ratio:.6f} "
            f"({energy:+.6e} / {solenoidal_drive['omega_l_grover']:+.6e} Ohm)",
            flush=True,
        )
    low, high = GROVER_RATIO_BAND
    assert low < ratio < high, (
        f"Im Z11/omega*L_Grover = {ratio:.6f} is outside the banded "
        f"[{low}, {high}]"
    )
