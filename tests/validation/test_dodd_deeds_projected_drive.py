"""`MAT-6` step 3: the Dodd-Deeds loading gate under the *production* drive.

`MAT-6`'s landed 1.58% agreement (step 2b) was measured with
``project_source=False``.  Since `PORT-1` step 2f the package default is
``project_source=True`` — ``TimeHarmonicSolver`` drives with the CG1-weakly
solenoidal part ``J' = J - grad(psi)`` — so the headline coil-loading number
became a *non-default-path* result (PROJECT_PLAN §2.1).  This module re-gates
the same physics on the default path.

Deliberately a separate module from ``test_dodd_deeds_impedance.py``:

* that file's ``project_source=False`` pins are the provenance of the landed
  number and are never flipped — the geometry, the current density and the
  reaction integral are *imported* from it instead, so there is exactly one
  definition of the fixture;
* two more solves inside its module-scoped fixture would push a single pytest
  command past the standard tier's 180 s ceiling (the step-2b gate measured
  85 s).  Two commands, each ~75 s, is the split PROJECT_PLAN §7 asks for.

The comparison is like-for-like by construction: same mesh, same tagging, same
reaction integral, one thing changed.  ``remove_gradient_content`` sees only the
mesh, ``J`` and the cell tags — not the material — so the loaded and free solves
must be driven by the *identical* ``J'``, otherwise their reaction difference
would measure the drive rather than the half-space.  That is not assumed here;
:func:`test_both_solves_are_driven_by_the_same_projected_current` measures it.

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_dodd_deeds_projected_drive.py -v -s'
"""

from __future__ import annotations

import time

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
from fem_em_solver.utils.dodd_deeds import coil_impedance_change
from tests.complex_mode import complex_only
from tests.validation.test_dodd_deeds_impedance import (
    FEM_BOX_HALF_WIDTH,
    FEM_CURRENT_A,
    FEM_FREQUENCY_HZ,
    FEM_LIFTOFF,
    FEM_LOOP_RADIUS,
    FEM_SIGMA_SLAB,
    FEM_WIRE_RADIUS,
    SLAB_TAG,
    WIRE_TAG,
    _azimuthal_current_density,
)


def _reduced_real(form, comm) -> float:
    """``assemble_scalar`` is rank-local; reduce, then take the real part."""
    return float(np.real(comm.allreduce(fem.assemble_scalar(fem.form(form)), op=MPI.SUM)))


def _solve_projected(msh, cell_tags, sigma_slab, comm):
    """One solve on the production default path, returning ``(E, J', seconds)``.

    Identical to ``test_dodd_deeds_impedance._solve_loop`` except for the one
    thing under test: ``project_source`` is left at its default (on).
    """
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FEM_FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            SLAB_TAG: HomogeneousMaterial(sigma=sigma_slab, epsilon_r=1.0, mu_r=1.0)
        },
        boundary_condition="pec_zero_tangential_a",
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=_azimuthal_current_density(j_magnitude),
        subdomain_ids=[WIRE_TAG],
        # The point of the module: the step-2f default, not the pinned False.
    )
    comm.Barrier()
    elapsed = time.perf_counter() - t0
    projection = solver.projection()
    assert projection is not None, "the default path must have projected the drive"
    return fields.e_complex, projection.current, elapsed


@pytest.fixture(scope="module")
def projected_impedance_change():
    """Mesh once, solve the loaded/free pair on the default path.

    Module-scoped for the same reason step 2b's fixture is: 138 619 cells and
    ~27 s per solve at ``-n 2``.
    """
    comm = MPI.COMM_WORLD
    comm.Barrier()
    t_mesh = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=0.002,
        resolution_near=0.005,
        resolution_far=0.025,
        near_half_width=0.06,
        near_depth=0.05,
        near_height=0.03,
        comm=comm,
    )
    comm.Barrier()
    t_mesh = time.perf_counter() - t_mesh
    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)

    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)
    x = ufl.SpatialCoordinate(msh)
    j_vec = _azimuthal_current_density(j_magnitude)(x)
    phi_hat = _azimuthal_current_density(1.0)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )

    # The unprojected meshed current, exactly as step 2b computes it: the
    # discretised torus carries less than the nominal 1 A because its volume is
    # short of pi r^2 * 2 pi a.
    v_wire = _reduced_real(
        fem.Constant(msh, np.array(1.0, dtype=np.complex128).item()) * dx_wire, comm
    )
    current_unprojected = j_magnitude * v_wire / (2.0 * np.pi * FEM_LOOP_RADIUS)

    e_loaded, j_prime_loaded, t_loaded = _solve_projected(
        msh, cell_tags, FEM_SIGMA_SLAB, comm
    )
    e_free, j_prime_free, t_free = _solve_projected(msh, cell_tags, 0.0, comm)

    # I': the same cross-section integral as step 2b (azimuthal current averaged
    # over the loop's length), applied to the drive that was actually used.  J'
    # has support on the whole domain, but the circuit current is what threads
    # the conductor, so the measure stays on the wire tag (`PORT-1` step 2e's
    # precedent).
    current = _reduced_real(ufl.inner(j_prime_loaded, phi_hat) * dx_wire, comm) / (
        2.0 * np.pi * FEM_LOOP_RADIUS
    )

    # Do the two solves see the same drive?  Relative L2 difference of the two
    # projected currents over the whole domain.
    j_prime_diff = j_prime_loaded - j_prime_free
    drive_mismatch = _reduced_real(
        ufl.inner(j_prime_diff, j_prime_diff) * ufl.dx, comm
    ) / _reduced_real(ufl.inner(j_prime_loaded, j_prime_loaded) * ufl.dx, comm)

    # dZ = -(1/I'^2) * integral over the WHOLE domain of (E_loaded - E_free).J',
    # because J' (unlike J) is supported everywhere.  J' is real -- psi's
    # imaginary part is discarded by remove_gradient_content -- so inner()'s
    # conjugation of its second argument is a no-op: this is the reaction
    # integral, not a power.
    reaction = comm.allreduce(
        fem.assemble_scalar(
            fem.form(ufl.inner(e_loaded - e_free, j_prime_loaded) * ufl.dx)
        ),
        op=MPI.SUM,
    )
    dz = complex(-reaction / current**2)
    dz_ref = coil_impedance_change(
        FEM_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )

    if comm.rank == 0:
        print(
            f"\n[MAT-6 step 3] mesh {ncells} cells in {t_mesh:.1f} s at "
            f"W = {FEM_BOX_HALF_WIDTH} m; solves (incl. CG1 Poisson): "
            f"loaded {t_loaded:.1f} s, free {t_free:.1f} s"
            f"\n[MAT-6 step 3] I (unprojected, meshed) = {current_unprojected:.6f} A, "
            f"I' (projected) = {current:.6f} A, ratio {current / current_unprojected:.6f}"
            f"\n[MAT-6 step 3] drive mismatch ||J'_loaded - J'_free||^2/||J'||^2 = "
            f"{drive_mismatch:.3e}"
            f"\n[MAT-6 step 3] FEM   dZ = {dz.real:+.7e} + j({dz.imag:+.7e}) Ohm"
            f"\n[MAT-6 step 3] exact dZ = {dz_ref.real:+.7e} + j({dz_ref.imag:+.7e}) Ohm"
            f"\n[MAT-6 step 3] dR rel. error {abs(dz.real / dz_ref.real - 1.0):.4%}, "
            f"dX ratio {dz.imag / dz_ref.imag:.4f}",
            flush=True,
        )
    return dict(
        dz=dz,
        dz_ref=dz_ref,
        current=current,
        current_unprojected=current_unprojected,
        drive_mismatch=drive_mismatch,
        ncells=int(ncells),
    )


@complex_only
@pytest.mark.integration
def test_both_solves_are_driven_by_the_same_projected_current(
    projected_impedance_change,
):
    """The two projections must be bit-for-bit the same drive.

    ``remove_gradient_content`` is a function of the mesh, ``J`` and the cell
    tags only — the material never reaches it — so the loaded and free solves
    solve the *same* CG1 Poisson problem.  If they did not, the reaction
    difference below would be measuring the change of drive and not the
    half-space, and the gate would be meaningless.  Measured 0.0 on the gate
    run and 8.774e-39 on the probe — the two CG1 Poisson solves agree to
    round-off, and which side of it they land on varies — bounded fifteen orders
    above that, because a drive that genuinely saw the material would differ at
    O(1), not at 1e-24.
    """
    mismatch = projected_impedance_change["drive_mismatch"]
    print(f"\n  ||J'_loaded - J'_free||^2 / ||J'||^2 = {mismatch:.3e}")
    assert mismatch < 1.0e-24, f"the two solves used different drives: {mismatch}"


@complex_only
@pytest.mark.integration
def test_projection_barely_moves_the_loop_current(projected_impedance_change):
    """``I'`` against ``I``: a closed loop drive is near-solenoidal already.

    The prescribed azimuthal ``J`` on a torus is divergence-free in the
    continuum, so ``P_G J`` is a purely discrete artefact and ``I'`` should sit
    within a few percent of the meshed ``I``.  A large shift would mean the
    projection is re-normalising the source, which would show up in ΔZ ∝ 1/I'^2
    as a spurious scale rather than as physics.  Measured ratio 0.999974 —
    26 ppm, so the projection is very nearly a no-op on this drive, as
    `PORT-1` step 2f predicted.  (`PORT-1` step 2e's two-torus fixture
    measured I'/I = 0.999992 against *its* re-measured I; the 0.969 quoted
    there is the meshed-versus-nominal deficit, a different ratio.)  The 5%
    band is three orders above the residual and still catches any
    re-normalisation worth the name.
    """
    i_prime = projected_impedance_change["current"]
    i_meshed = projected_impedance_change["current_unprojected"]
    ratio = i_prime / i_meshed
    print(f"\n  I' / I = {i_prime:.6f} / {i_meshed:.6f} = {ratio:.6f}")
    assert 0.95 < ratio < 1.05, f"the projection re-scaled the drive: I'/I = {ratio}"


@complex_only
@pytest.mark.integration
def test_projected_resistance_change_matches_dodd_deeds(projected_impedance_change):
    """**The `MAT-6` step-3 gate.** ΔR on the production default path.

    Same closed form, same mesh, same reaction integral as the step-2b gate —
    the drive is the only thing that changed.  The 5% ceiling is step 2b's,
    inherited unchanged and deliberately not widened: PROJECT_PLAN §7 makes it
    a hard ceiling for this step, because a projected ΔR that needed more than
    5% would be a finding about the projection in lossy media, not a tolerance
    to move.  Measured **1.5834%** (ΔR = +3.2770406e-01 Ω) against the
    unprojected path's 1.58% (+3.276882e-01 Ω, log
    ``20260731T110515Z_MAT-6-step2b-gate-numbers.log``): the two drives agree
    on the gated number to 5e-5 relative, so `MAT-6`'s coil-loading claim
    holds on the production default path and not merely on the pinned one.
    """
    dz, dz_ref = (
        projected_impedance_change["dz"],
        projected_impedance_change["dz_ref"],
    )
    rel = abs(dz.real / dz_ref.real - 1.0)
    print(f"\n  ΔR: FEM {dz.real:.7e} Ω vs exact {dz_ref.real:.7e} Ω → {rel:.4%}")
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert rel < 0.05, f"projected ΔR off the closed form by {rel:.2%}"


@complex_only
@pytest.mark.integration
def test_projected_reactance_change_has_the_right_sign_and_magnitude(
    projected_impedance_change,
):
    """ΔX: sign and order of magnitude, exactly as step 2b gates it.

    ΔX is not converged in box size on this fixture (−18.8% at W = 0.15,
    5.57% of motion still left at W = 0.20) and the filamentary reference
    spreads by 30% over h ± r_wire, so the projected run inherits the same
    deliberately weak gate rather than a tolerance sized to whatever it
    returns.  What this test adds is the comparison *between paths*: if the
    projection had broken the reactive part, the ratio would leave the band the
    unprojected path sits comfortably inside.

    Measured ratio **0.9200** (ΔX = −5.6657895e-01 Ω) against the unprojected
    path's 0.8123.  That the reactive part moves 13% while ΔR moves 5e-5 is a
    result, not noise, and it is reported rather than gated: both numbers sit
    inside an unconverged 5.57% of remaining box motion plus a 30% filamentary
    spread, so this fixture cannot say whether the projection *improved* ΔX or
    merely moved it.  Deciding that needs the converged fixture (h/r_wire ≥ 16
    or W ≥ 0.25) step 2b already named — see PROJECT_PLAN §7, `MAT-6` step 3.
    """
    dz, dz_ref = (
        projected_impedance_change["dz"],
        projected_impedance_change["dz_ref"],
    )
    ratio = dz.imag / dz_ref.imag
    print(f"\n  ΔX: FEM {dz.imag:.7e} Ω vs exact {dz_ref.imag:.7e} Ω → ratio {ratio:.4f}")
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
    assert 0.5 < ratio < 2.0, f"projected ΔX is not within an order of magnitude: {ratio}"
