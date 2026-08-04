"""`PORT-1` step 2b: the self-impedance diagnosis via complex power.

Step 1 and step 2 both measured a **negative** reaction-integral diagonal on the
two-torus air fixture — ``Im Z₁₁ ≈ −40.9 Ω`` where a lossless loop must be
inductive, and ~6× the magnitude of a Grover estimate ``ωL ≈ 6.8 Ω``.  The
step-2 gate deliberately leaves the diagonal ungated because nothing in the plan
could say whether the *reaction integral* was wrong or the *fixture* is
genuinely electric-energy-dominated.  This file settles that with a second,
independent derivation of the same number from the same solved field.

**The identity.**  The solver's sesquilinear form is
``∫ μᵣ⁻¹(∇×E)·(∇×v̄) − k₀²ε_c E·v̄ dx = −jωμ₀ ∫ J·v̄ dx``.  The homogeneous PEC
boundary condition puts ``E`` itself in the test space, so taking ``v = E`` and
dividing by ``μ₀`` gives, in lossless air,

    4ω²(W_m − W_e) = jω I² conj(Z₁₁),     Z₁₁ = −(1/I²)∫E·J dV

    ⇒  Im Z₁₁ = 4ω(W_m − W_e)/I²                                          (1)

with the peak-phasor energies ``W_e = (ε₀/4)∫εᵣ|E|²dV`` (already implemented as
:func:`core.resonance.stored_electric_energy`, §11 convention) and
``W_m = (1/(4μ₀ω²))∫|∇×E|²dV``.  Route (1) touches neither the reaction integral
nor the meshed-current bookkeeping beyond ``I``: it reads the diagonal off the
energy content of the field.  The two routes agreeing therefore says the
reaction integral is computing what it claims, and pushes the anomaly onto the
fixture; the two routes disagreeing localises the bug to the reaction
integral's self-term (the source-region integral, the only place the diagonal
differs from the off-diagonal that step 2 already validated to 9.35% of ωM₁₂).

**What is gated.**  The relative agreement between the two routes.  Equation (1)
is an exact consequence of the discrete equation, so with a direct (MUMPS LU)
solve it holds to the solver residual and to quadrature-rule agreement between
the two form pairs — **measured 1.8128e-10** (2026-08-03, `-n 2`, log
``20260803T050252Z_PORT-1-step2b-gate.log``), against the 1e-9 bound.  Any sign
error, factor of 2, ½-vs-peak convention slip or missing rank reduction in
either route is O(1), so the negative control is total rather than a ratio: a
reaction integral that got the self-term wrong does not miss (1) by percents.
The residual is solver-limited rather than physics-limited, so the margin here
is 5.5× and not the usual four orders — if a change of rank count, solver or
mesh moves it, **re-measure and record; do not widen the bound reflexively**,
because a drift of that residual is itself information about the solve.

**Third anchor, printed and not gated.**  Grover's
``L ≈ μ₀a(ln(8a/r_wire) − 2)`` — computed here in code, it was prose-only in the
plan — gives ``ωL = 6.818 Ω``, and the magnetic energy alone gives an inductive
reactance ``4ωW_m/I²``.  Their comparison says whether ``W_m`` is the physical
loop inductance (in which case the negative total is an *electric* energy
excess, a statement about the fixture) or whether both energies are wrong.  It
is printed, not asserted: the PEC box at padding 0.08 m perturbs the isolated
loop's inductance by an unmeasured amount, so no bound here would be honest.

**The answer this file returned (2026-08-03).**  Both routes give
``Im Z₁₁ = −4.108550e+01 Ω`` to 1.8e-10, so **the reaction integral is not the
bug**; and ``4ωW_m/I² = 7.437 Ω`` sits 9.1% above Grover's 6.818 Ω, so the
magnetic half is the physical loop inductance.  The entire anomaly is in the
electric energy: ``W_e/W_m = 6.524``, ``4ωW_e/I² = 48.52 Ω``, and
``−40.9 = 7.44 − 48.52``.  The two-torus box at 10 MHz is electric-energy
dominated, which invalidates any input impedance read off this fixture's
diagonal.  See known-issues 8 and PROJECT_PLAN §7 `PORT-1` step 2b for the
leading hypothesis (low-frequency gradient-space contamination, whose ω-scaling
is the next measurement).

Scope: this is a **diagnosis**.  It closes nothing — not `PORT-1`, not the
diagonal, which stays ungated in `test_port_reaction_impedance.py` until a later
step fixes whatever this localises.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_self_impedance_energy.py -v -s'
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
from fem_em_solver.core.resonance import stored_electric_energy
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.constants import MU_0

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
    TORUS_TAGS,
    _azimuthal_current_density,
    _reaction,
    _tag_volume,
)

# One mesh, ONE solve (torus 1 driven) — half of step 2's cost, ~50 s at -n 2.
DRIVEN_TAG = TORUS_TAGS[0]


def stored_magnetic_energy(e_complex, comm) -> float:
    """``W_m = (1/(4μ₀ω²))∫|∇×E|²dV`` [J], peak-phasor, reduced across ranks.

    The Faraday partner of :func:`stored_electric_energy`: ``B = ∇×E/(−jω)`` in
    the ``e^{+jωt}`` convention, so ``|B|² = |∇×E|²/ω²`` and
    ``W_m = (1/(4μ₀))∫|B|²``.  ``ufl.inner`` conjugates its second argument, so
    ``inner(curl E, curl E)`` is ``|∇×E|²`` and is real up to round-off;
    ``assemble_scalar`` is rank-local and is reduced here, as
    :func:`stored_electric_energy` already does for ``W_e``.
    """
    integrand = ufl.inner(ufl.curl(e_complex), ufl.curl(e_complex))
    local = fem.assemble_scalar(fem.form(integrand * ufl.dx))
    total = comm.allreduce(local, op=MPI.SUM)
    return float(np.real(total) / (4.0 * MU_0 * OMEGA**2))


def grover_loop_inductance(a: float, r_wire: float) -> float:
    """``L ≈ μ₀a(ln(8a/r_wire) − 2)`` [H] — a circular loop of round wire.

    Grover's low-frequency (uniform-current) formula.  At a = 0.04 m,
    r_wire = 0.005 m this is 1.085e-7 H, i.e. ωL = 6.82 Ω at 10 MHz.
    """
    return MU_0 * a * (np.log(8.0 * a / r_wire) - 2.0)


@pytest.fixture(scope="module")
def self_impedance_routes():
    """Solve once with torus 1 driven; return both derivations of ``Z₁₁``."""
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
    # The meshed loop current, never the nominal 1 A (MAT-6 step 2a's 17% error).
    volume = _tag_volume(msh, cell_tags, DRIVEN_TAG, comm)
    current = j_magnitude * volume / (2.0 * np.pi * MAJOR_RADIUS)

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
    fields = solver.solve(
        current_density=_azimuthal_current_density(j_magnitude),
        subdomain_ids=[DRIVEN_TAG],
        # Step 2b is the diagnosis of the *unprojected* drive: every number in
        # this file (Im Z11 = -41.09 Ohm, 4*omega*W_e/I^2 = 48.52 Ohm) is the
        # measurement that step 2f's default would remove.  Explicitly off.
        project_source=False,
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t_solve

    z11_reaction = _reaction(
        msh, cell_tags, fields.e_complex, DRIVEN_TAG, current, current, comm
    )
    w_e = stored_electric_energy(fields, comm=comm)
    w_m = stored_magnetic_energy(fields.e_complex, comm)
    im_z11_energy = 4.0 * OMEGA * (w_m - w_e) / current**2

    if comm.rank == 0:
        print(
            f"\n[PORT-1 step 2b] padding {AIR_PADDING} m, h_far {H_FAR} m, "
            f"{ncells} cells, mesh {t_mesh:.1f} s, solve {t_solve:.1f} s, "
            f"meshed current {current:.6f} A",
            flush=True,
        )
        print(
            f"[PORT-1 step 2b] W_m = {w_m:.6e} J, W_e = {w_e:.6e} J, "
            f"W_e/W_m = {w_e / w_m:.6f}",
            flush=True,
        )
        print(
            f"[PORT-1 step 2b] Z11 (reaction) = {z11_reaction:+.6e} Ohm; "
            f"Im Z11 (energy) = {im_z11_energy:+.6e} Ohm",
            flush=True,
        )
    return {
        "z11_reaction": z11_reaction,
        "im_z11_energy": im_z11_energy,
        "w_m": w_m,
        "w_e": w_e,
        "current": current,
    }


@complex_only
def test_reaction_diagonal_matches_complex_power_identity(self_impedance_routes):
    """Equation (1): the two routes to ``Im Z₁₁`` agree to 1e-9 relative.

    This is the whole point of step 2b.  The identity is exact for the discrete
    solution, so the residual measures the direct solve plus the quadrature
    agreement of the two form pairs — measured **1.8128e-10** (2026-08-03,
    ``-n 2``, log ``20260803T050252Z_PORT-1-step2b-gate.log``).  Any sign error,
    factor of two, or missing rank reduction in either route is O(1) and cannot
    pass.  Both routes returned ``Im Z₁₁ = −41.086 Ω``: the reaction integral is
    right and the negative diagonal is the fixture's, not the formula's.
    """
    reaction = self_impedance_routes["z11_reaction"].imag
    energy = self_impedance_routes["im_z11_energy"]
    relative = abs(reaction - energy) / abs(reaction)
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 2b] identity residual "
            f"|Im Z11(reaction) - Im Z11(energy)|/|Im Z11| = {relative:.4e}",
            flush=True,
        )
    assert relative < 1e-9, (
        f"complex-power identity broken: reaction {reaction:.6e} Ohm vs energy "
        f"{energy:.6e} Ohm, relative {relative:.4e}"
    )


@complex_only
def test_reaction_diagonal_real_part_is_structurally_zero(self_impedance_routes):
    """``Re Z₁₁`` is absent, not small — the diagonal counterpart of step 2 (iii).

    Lossless air makes the operator real-symmetric, so there is no real part to
    cancel; 1e-30 is below anything convergence could deliver and only a
    structural zero passes it.  Stated here because equation (1) constrains only
    the imaginary part, so a real part leaking into the diagonal would otherwise
    go unremarked by this file.
    """
    real_part = self_impedance_routes["z11_reaction"].real
    if MPI.COMM_WORLD.rank == 0:
        print(f"[PORT-1 step 2b] Re Z11 = {real_part:+.6e} Ohm", flush=True)
    assert abs(real_part) < 1e-30, (
        f"Re Z11 = {real_part:.6e} Ohm is not structurally zero"
    )


@complex_only
def test_magnetic_energy_reactance_against_grover(self_impedance_routes):
    """Third anchor, **printed not gated**: ``4ωW_m/I²`` vs Grover's ``ωL``.

    ``W_m = ¼L I²`` in the peak-phasor convention, so the magnetic energy alone
    gives an inductive reactance ``4ωW_m/I²``.  Comparing it with Grover says
    which half of equation (1) is anomalous when the total comes out negative.
    No bound: the PEC box at padding 0.08 m perturbs the isolated-loop
    inductance by an amount nobody here has measured.  The one assertion is
    that ``W_m`` is a positive, finite energy — the premise the print relies on.
    Measured 2026-08-03: ``4ωW_m/I² = 7.437 Ω`` against Grover's 6.818 Ω, ratio
    1.0908 — close enough that the magnetic half is physical and the anomaly is
    the electric half (``4ωW_e/I² = 48.52 Ω``).
    """
    w_m = self_impedance_routes["w_m"]
    current = self_impedance_routes["current"]
    x_from_wm = 4.0 * OMEGA * w_m / current**2
    omega_l_grover = OMEGA * grover_loop_inductance(MAJOR_RADIUS, MINOR_RADIUS)
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 2b] 4*omega*W_m/I^2 = {x_from_wm:+.6e} Ohm vs Grover "
            f"omega*L = {omega_l_grover:+.6e} Ohm "
            f"(ratio {x_from_wm / omega_l_grover:.4f}); "
            f"electric-energy reactance 4*omega*W_e/I^2 = "
            f"{4.0 * OMEGA * self_impedance_routes['w_e'] / current**2:+.6e} Ohm",
            flush=True,
        )
    assert np.isfinite(w_m) and w_m > 0.0, f"W_m = {w_m!r} is not a positive energy"
