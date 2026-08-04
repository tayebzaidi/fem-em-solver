"""`PORT-1` step 2: the reaction Z-matrix gate on a two-loop air fixture.

The first S-matrix in this repository derived from a solved field rather than
from placeholder arithmetic.  Two coaxial tagged tori sit in air inside a PEC
box (`GEO-8`'s conforming ``two_torus_domain``); torus ``k`` is driven in turn
with an impressed azimuthal current and the reaction integral

    Z_ik = −(1/(I_k·I_i)) ∫_{torus i} E_k · J_i dV                        (1)

gives one column of the 2×2 impedance matrix per solve.  ``J_i`` is torus i's
*shape* current — the same azimuthal pattern, restricted by the measure to
torus i's tag — and every ``I`` is the **meshed** loop current ``∫J_φ dV/(2πa)``
rather than the nominal 1 A; using the nominal current was a 17% error that
looked like physics in `MAT-6` step 2a.

What is gated, and why each bound is what it is (every number below is a
`PORT-1` step-1 measurement, logs in PROJECT_PLAN §7):

  * **reciprocity** ``‖Z − Zᵀ‖/‖Z‖ < 1e-9``.  Step 1 measured 7.9e-14 …
    4.3e-13 across three mesh/box configurations, i.e. machine precision, so
    1e-9 is four orders of slack and still catches any real symmetry break.
    This is the identity `PORT-1`'s "done when" names.
  * **mutual coupling** ``Im Z₁₂`` within **10%** of the closed form
    ``ωM₁₂ = 1.241755 Ω``, ``M₁₂ = 2πa·A_φ(a,d)/I`` (Jackson 5.37, via
    :meth:`AnalyticalSolutions.circular_loop_vector_potential`).  Step 1
    measured −9.35% at exactly this configuration, and the residual gap is the
    PEC box rather than the mesh: refining h_far 0.02 → 0.03 moves it 0.09%
    while enlarging the padding 0.08 → 0.12 moves it 5.20%, monotonically
    toward the closed form.  The bound is **not** tightened here: the
    filamentary reference itself spans 66.5% of nominal when re-evaluated over
    ρ, z within ± r_wire, so at d = a it cannot support better.
  * **the doubling control** (step 2c, 2026-08-03): ``|Z₁₂|`` measured at a
    second separation ``2d = 0.08`` must fall to ``M(2d)/M(d) = 0.287120`` of
    its value at ``d``, to the same 10%.  This is what turns (ii) from a single
    magnitude into a *geometric* statement; a separation-blind solver returns
    1.000 against 0.287.  It costs two extra meshes and two extra solves (122 s
    measured): the ratio needs both separations in the *same* box, and that box
    is a larger one than step 2's for a measured reason — see
    ``AIR_PADDING_DOUBLING``.  One solve per separation suffices, since
    reciprocity is 3e-13 here.
  * **``Re Z₁₂`` structurally zero.**  In the lossless case the curl-curl
    operator is real-symmetric, so the real part is *absent*, not cancelled —
    step 1 measured exactly ``0.0``.  Asserted at 1e-30, which no convergence
    argument could ever justify and which only a structural zero passes.
  * **S symmetric and passive.**  ``S = (Z − Z₀I)(Z + Z₀I)⁻¹`` at Z₀ = 50 Ω.
    A lossless reciprocal 2-port has unitary S, so ``‖S‖₂ = 1``: passivity is
    asserted as ``≤ 1``, and unitarity to 1e-9 as the sharper statement of the
    same physics.

**Negative control.**  The pre-`GEO-8` fixture never fragmented the box against
the tori, so the two loops were meshed as disconnected islands and returned
``Z₁₂`` *identically zero* against a 1.2418 Ω closed form (PROJECT_PLAN §7,
`PORT-1` step-1 attempt of 2026-07-31).  The separation between the honest and
the broken fixture on assertion (ii) is therefore total, not a factor.

**The diagonal is deliberately not gated.**  Step 1 measured
``Im Z₁₁ ≈ −40.9 Ω``, negative where a lossless loop must be inductive and ~6×
a Grover estimate ``ωL ≈ 6.8 Ω``.  It is undiagnosed and `PORT-1` step 2b owns
it; gating "sign and order" here would gate a known-bad number.  The value is
printed instead.

Scope: this closes reciprocity and mutual coupling on a two-loop **air**
fixture.  It does not close `PORT-1` — gap-voltage ports on a real coil are
step 3 — and it does not resolve the two deliberately-red port tests
(known-issues 3).

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_reaction_impedance.py -v -s'
"""

from __future__ import annotations

import time
from typing import Optional

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
from fem_em_solver.ports import (
    sparameters_from_impedance,
    summarize_sparameter_sanity,
)
from fem_em_solver.utils.analytical import AnalyticalSolutions
from fem_em_solver.utils.constants import EPSILON_0, MU_0

from tests.complex_mode import complex_only

# Geometry and frequency are step 1's, unchanged.  f is a free knob — nothing
# about a reaction Z-matrix ties it to the Larmor frequency — and 10 MHz keeps
# k₀·(box diagonal) ≈ 0.086, well inside the quasistatic regime the ωM
# reference needs.
FREQUENCY_HZ = 10.0e6
MAJOR_RADIUS = 0.04   # a
MINOR_RADIUS = 0.005  # r_wire
SEPARATION = 0.04     # d, centre to centre along z
SEPARATION_DOUBLE = 0.08  # 2d, step 2c's doubling control
CURRENT_A = 1.0

# padding 0.08 / h_far 0.03 = 119738 cells, mesh 21 s + solves 21 s and 31 s
# (step 1, log 20260802T183747Z_PORT-1-step1-boxsens.log).  Padding 0.12 at
# h_far 0.02 (237926 cells) was killed at 180 s inside MUMPS and must not be
# used here.
AIR_PADDING = 0.08
H_FAR = 0.03
H_WIRE = 0.0025

# Step 2c's pair runs in a *larger* box than step 2's, and the size is measured,
# not chosen: the PEC wall costs the wider separation more than the narrower one,
# so the box error does not cancel out of the ratio.  Sweep of the ratio error
# against padding, all at h_far 0.03 (logs 20260803T093329Z_PORT-1-step2c-gate,
# 20260803T093617Z_PORT-1-step2c-boxsens, 20260803T110209Z_PORT-1-step2c-ratio12):
#
#   padding 0.08 -> -13.33%   (per-separation -9.36% at d, -21.4% at 2d)
#   padding 0.10 ->  -8.78%   (-6.38%, -14.60%)
#   padding 0.12 ->  -5.93%   (-4.64%, -10.30%)
#
# Monotone toward the closed form.  0.12 is taken over 0.10 because 8.78% against
# a 10% bound is 1.1x of margin picked after seeing it pass; 5.93% is 1.69x.  The
# cost is measured too (20260803T110058Z_PORT-1-step2c-costprobe12.log):
# 154493 cells at d and 169502 at 2d, 1.29x and 1.42x step 2's box -- well clear
# of the 237926-cell case (padding 0.12 at h_far 0.02) MUMPS was killed on.
# Both separations of the ratio must share a padding, so step 2c pays for its own
# two meshes rather than reusing step 2's; measured 122 s for the pair.
AIR_PADDING_DOUBLING = 0.12

TORUS_TAGS = (1, 2)
REFERENCE_IMPEDANCE_OHM = 50.0

# Step 3a's cross-run anchor: the Z and S the step-2 gate printed, verbatim from
# 20260803T003217Z_PORT-1-step2-gate.log:430-431 and :442.
#
# **Re-pointed at Z by step 2f (2026-08-04).**  Until 2f the anchor compared the
# *live* fixture's S against the logged S.  That coupled a statement about the
# Z→S conversion to the drive: 2f makes the solenoidal projection the default,
# which deliberately moves the diagonal from Im Z11 = -4.108550e+01 Ohm to
# +7.437122e+00 Ohm, so the live S legitimately no longer matches the logged S.
# Rebaselining the logged S to the projected run would have thrown away the
# executed history rather than preserved it, so the anchor now converts the
# **logged Z** — the matrix that log actually printed — and holds the result to
# the logged S.  That is the same cross-run claim about the conversion, made
# against the run it came from, and it is now independent of which drive the
# fixture uses.  The live fixture keeps its own drive-independent gates
# (unitarity, symmetry, passivity, code-path equivalence at 1e-12).
#
# Seven significant figures printed, so a comparison can only be held to the
# rounding of the printed value (5e-8 on the mantissa's last digit); 1e-6
# absolute is that with an order of slack.
STEP2_LOGGED_Z = np.array(
    [
        [-4.108550e01j, +1.125614e00j],
        [+1.125614e00j, -4.092413e01j],
    ],
    dtype=complex,
)
STEP2_LOGGED_S11 = -1.941026e-01 - 9.806119e-01j
STEP2_LOGGED_S21 = -2.639550e-02 + 5.277699e-03j
STEP2_LOGGED_S_TOLERANCE = 1e-6

# Step 2f: the projected diagonal, gated below.  Grover's omega*L = 6.818343 Ohm
# for this loop; step 2e measured Im Z11/omega*L = 1.090770 on the *hand*
# projection of this identical mesh and banded it (1.042, 1.140) — +-4.5%, a
# statement about this fixture's PEC box at padding 0.08 rather than about
# Grover.  The production path measured 1.090752 (Z11) and 1.090663 (Z22) in the
# step-2f probe (20260804T110411Z_PORT-1-step2f-probe.log:444), i.e. the same
# number to 2e-5, so the band is carried over unchanged rather than re-derived.
GROVER_RATIO_BAND = (1.042, 1.140)

# The unprojected control, executed history, cited not re-run: the same fixture,
# mesh, padding and frequency gave Im Z11 = -4.108550e+01 Ohm
# (20260803T003217Z_PORT-1-step2-gate.log:432).  A sign flip plus 48.5 Ohm.
UNPROJECTED_IM_Z11_OHM = -4.108550e01

# Step 2b's house bound for the complex-power identity Im Z11 = 4*omega*(W_m -
# W_e)/I'^2, met at 1.8128e-10 there and 1.6242e-14 on step 2e's hand-projected
# drive.  Exact for the discrete solution, so it gates bookkeeping, not physics.
IDENTITY_TOLERANCE = 1e-9

OMEGA = 2.0 * np.pi * FREQUENCY_HZ


def _azimuthal_current_density(j_magnitude: float):
    """Uniform azimuthal current about the z-axis.

    Regularised inside the sqrt rather than with ``ufl.max_value``: in complex
    mode UFL refuses conditionals on complex-valued operands, so the
    magnetostatic loop fixture's ``max_value`` form does not compile here.
    """

    def current_density(x):
        rho_safe = ufl.sqrt(x[0] ** 2 + x[1] ** 2 + 1e-24)
        return ufl.as_vector([
            -x[1] / rho_safe * j_magnitude,
            x[0] / rho_safe * j_magnitude,
            0.0,
        ])

    return current_density


def _tag_volume(msh, cell_tags, tag: int, comm) -> float:
    dx_tag = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,)
    )
    one = fem.Constant(msh, np.array(1.0, dtype=np.complex128).item())
    # assemble_scalar is rank-local.
    return float(
        np.real(comm.allreduce(fem.assemble_scalar(fem.form(one * dx_tag)), op=MPI.SUM))
    )


def _reaction(msh, cell_tags, e_field, tag, i_driven, i_test, comm) -> complex:
    """Equation (1) for one (driven, test) pair, reduced across ranks."""
    j_magnitude = CURRENT_A / (np.pi * MINOR_RADIUS**2)
    x = ufl.SpatialCoordinate(msh)
    j_vec = _azimuthal_current_density(j_magnitude)(x)
    dx_tag = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,)
    )
    # J is real, so inner()'s conjugation of its second argument is a no-op:
    # this is the reaction integral ∫E·J, not ∫E·J̄.
    local = fem.assemble_scalar(fem.form(ufl.inner(e_field, j_vec) * dx_tag))
    total = comm.allreduce(local, op=MPI.SUM)
    return complex(-total / (i_driven * i_test))


def mutual_inductance(a: float, rho: float, z: float) -> float:
    """``M = 2πρ·A_φ(ρ, z)/I`` for a unit-current filamentary loop of radius a."""
    pts = np.array([[rho, 0.0, z]], dtype=float)
    A = AnalyticalSolutions.circular_loop_vector_potential(pts, 1.0, a, loop_center=0.0)
    # At (x=ρ, y=0) the azimuthal direction is +y.
    return 2.0 * np.pi * rho * float(A[0, 1])


def scattering_from_impedance(z_matrix: np.ndarray, z0_ohm: float) -> np.ndarray:
    """``S = (Z − Z₀I)(Z + Z₀I)⁻¹`` — the normalised-reference conversion."""
    identity = np.eye(z_matrix.shape[0], dtype=complex)
    return (z_matrix - z0_ohm * identity) @ np.linalg.inv(z_matrix + z0_ohm * identity)


def _reduced_real(form, comm) -> float:
    """``assemble_scalar`` is rank-local — reduce, then take the real part."""
    return float(np.real(comm.allreduce(fem.assemble_scalar(fem.form(form)), op=MPI.SUM)))


def _solve_reaction_z(
    separation: float,
    driven_tags,
    label: str,
    air_padding: float = AIR_PADDING,
    diagonal_out: Optional[dict] = None,
) -> np.ndarray:
    """One mesh at ``separation``, one solve per entry of ``driven_tags``.

    Returns the 2×2 Z with the driven columns filled and the rest left at zero,
    so step 2c can buy a second separation for one solve instead of two: it
    needs only ``Z₂₁``, and reciprocity is measured at 3e-13 here.
    """
    comm = MPI.COMM_WORLD
    t_mesh = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.two_torus_domain(
        separation=separation,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=H_FAR,
        air_padding=air_padding,
        wire_resolution=H_WIRE,
        far_resolution=H_FAR,
        comm=comm,
    )
    t_mesh = time.perf_counter() - t_mesh

    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)

    j_magnitude = CURRENT_A / (np.pi * MINOR_RADIUS**2)
    # ∫J_φ dV = I·2πa for an ideal torus, so the meshed volume fixes the current
    # the solver actually sees.
    volumes = [_tag_volume(msh, cell_tags, t, comm) for t in TORUS_TAGS]
    currents = [j_magnitude * v / (2.0 * np.pi * MAJOR_RADIUS) for v in volumes]

    z_matrix = np.zeros((2, 2), dtype=complex)
    solve_times = []
    # Step 2f's diagonal bookkeeping, filled per driven column: the *driven*
    # current I' (the projected J', not the prescribed J) and the two routes to
    # Im Z_ii.  Cheap — assemblies on the field the column already solved for.
    # ``stored_magnetic_energy`` is imported here, not at module scope: the
    # module it lives in imports *this* one for the fixture constants.
    from tests.validation.test_port_self_impedance_energy import stored_magnetic_energy

    diagonal = {} if diagonal_out is None else diagonal_out
    x_ufl = ufl.SpatialCoordinate(msh)
    for driven_tag in driven_tags:
        col = TORUS_TAGS.index(driven_tag)
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
        t0 = time.perf_counter()
        fields = solver.solve(
            current_density=_azimuthal_current_density(j_magnitude),
            subdomain_ids=[driven_tag],
        )
        comm.Barrier()
        solve_times.append(time.perf_counter() - t0)
        for row, test_tag in enumerate(TORUS_TAGS):
            z_matrix[row, col] = _reaction(
                msh, cell_tags, fields.e_complex, test_tag,
                currents[col], currents[row], comm,
            )

        # --- Step 2f: the diagonal on the drive that was actually applied. ----
        # ∫E·∇q = 0 for every interior CG1 q at ω > 0 (the Galerkin equation
        # with test function ∇q, whose load ∫J'·∇q the projection annihilated),
        # so ∫_tag E·J = ∫_Ω E·J' exactly: the reaction number above needs no
        # re-assembly, only the driven current I' in place of the prescribed I.
        projection = solver.projection()
        i_prime = _reduced_real(
            ufl.inner(projection.current, _azimuthal_current_density(1.0)(x_ufl))
            * ufl.Measure(
                "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(driven_tag,)
            ),
            comm,
        ) / (2.0 * np.pi * MAJOR_RADIUS)
        w_e = stored_electric_energy(fields, comm=comm)
        w_m = stored_magnetic_energy(fields.e_complex, comm)
        diagonal[driven_tag] = {
            "reaction": complex(
                z_matrix[col, col] * (currents[col] ** 2) / (i_prime**2)
            ).imag,
            "energy": 4.0 * OMEGA * (w_m - w_e) / i_prime**2,
            "x_electric": 4.0 * OMEGA * w_e / i_prime**2,
            "current_prime": i_prime,
            "current": currents[col],
            "imag_ratio": projection.imag_ratio,
        }

    if comm.rank == 0:
        k0 = OMEGA * np.sqrt(MU_0 * EPSILON_0)
        half_x = MAJOR_RADIUS + MINOR_RADIUS + air_padding
        half_z = separation / 2 + MINOR_RADIUS + air_padding
        diag = 2.0 * np.sqrt(2.0 * half_x**2 + half_z**2)
        print(
            f"\n[{label}] d {separation} m, padding {air_padding} m, h_far "
            f"{H_FAR} m, {ncells} cells, mesh {t_mesh:.1f} s, solves "
            + ", ".join(f"{t:.1f} s" for t in solve_times),
            flush=True,
        )
        print(
            f"[{label}] k0*box_diagonal = {k0 * diag:.5f} (quasistatic), "
            f"meshed currents {currents[0]:.6f}, {currents[1]:.6f} A",
            flush=True,
        )
        print(
            f"[{label}] Z = [[{z_matrix[0,0]:+.6e}, {z_matrix[0,1]:+.6e}],\n"
            f"          [{z_matrix[1,0]:+.6e}, {z_matrix[1,1]:+.6e}]] Ohm",
            flush=True,
        )
        # Gated from step 2f (it was "ungated — step 2b owns the diagonal"
        # while the prescribed drive made it capacitive).  Both the prescribed
        # normalisation, kept for continuity with the logs, and the driven one.
        print(
            f"[{label}] diagonal (prescribed I): Im Z11, Im Z22 = "
            f"{z_matrix[0,0].imag:+.6e}, {z_matrix[1,1].imag:+.6e} Ohm "
            f"(unprojected control {UNPROJECTED_IM_Z11_OHM:+.6e} Ohm)",
            flush=True,
        )
        for tag, d in diagonal.items():
            print(
                f"[{label}] tag {tag} driven: I = {d['current']:.6f} A, "
                f"I' = {d['current_prime']:.6f} A (ratio "
                f"{d['current_prime'] / d['current']:.6f}); Im Z = "
                f"{d['reaction']:+.6e} Ohm (reaction) / {d['energy']:+.6e} Ohm "
                f"(energy), residual "
                f"{abs(d['reaction'] - d['energy']) / abs(d['reaction']):.4e}; "
                f"4*omega*W_e/I'^2 = {d['x_electric']:+.6e} Ohm; "
                f"Im(psi)/max|psi| = {d['imag_ratio']:.3e}",
                flush=True,
            )
    return z_matrix


# Filled by the ``reaction_z`` fixture's solves and read by ``reaction_diagonal``
# so the step-2f gates below cost no extra solve.  Module-level rather than a
# second fixture return value because every existing test takes ``reaction_z``
# as the bare matrix.
_REACTION_DIAGONAL: dict = {}


@pytest.fixture(scope="module")
def reaction_z():
    """One mesh, two solves — step 2's fixture at ``d = 0.04``.

    Module-scoped so the assertions below share it; every rank runs the same
    fixture, so the collective calls inside stay matched.
    """
    return _solve_reaction_z(
        SEPARATION, TORUS_TAGS, "PORT-1 step 2", diagonal_out=_REACTION_DIAGONAL
    )


@pytest.fixture(scope="module")
def reaction_diagonal(reaction_z):
    """Step 2f's per-port diagonal bookkeeping from the same two solves."""
    return _REACTION_DIAGONAL


@pytest.fixture(scope="module")
def doubling_pair():
    """Step 2c's pair: ``d`` and ``2d``, both at ``AIR_PADDING_DOUBLING``.

    Two meshes, **one** solve each — only ``Z₂₁`` is read, and reciprocity is
    3.06e-13 on this fixture, so the second column buys nothing but time.  The
    pair does *not* reuse step 2's ``d`` solve: the ratio is only meaningful if
    both separations sit in the same box, and step 2's box is the padding-0.08
    one whose wall error the constant's comment tabulates.  Measured 122 s for
    the pair (`20260803T110209Z_PORT-1-step2c-ratio12.log`).
    """
    return {
        separation: _solve_reaction_z(
            separation,
            (TORUS_TAGS[0],),
            "PORT-1 step 2c",
            air_padding=AIR_PADDING_DOUBLING,
        )
        for separation in (SEPARATION, SEPARATION_DOUBLE)
    }


@complex_only
def test_reaction_z_matrix_is_reciprocal(reaction_z):
    """``‖Z − Zᵀ‖/‖Z‖ < 1e-9`` — the identity `PORT-1`'s "done when" names.

    Step 1 measured 7.86e-14 (padding 0.08 / h_far 0.02), 3.06e-13 (0.08/0.03,
    this configuration) and 4.31e-13 (0.12/0.03): machine precision, so the
    bound is not sensitivity-limited.
    """
    residual = np.linalg.norm(reaction_z - reaction_z.T) / np.linalg.norm(reaction_z)
    if MPI.COMM_WORLD.rank == 0:
        print(f"[PORT-1 step 2] reciprocity ||Z-Z^T||/||Z|| = {residual:.4e}", flush=True)
    assert residual < 1e-9, f"reciprocity residual {residual:.4e} exceeds 1e-9"


@complex_only
def test_mutual_impedance_matches_closed_form(reaction_z):
    """``Im Z₁₂`` within 10% of ``ωM₁₂`` (Jackson 5.37).

    The broken (non-fragmented) fixture returned ``Z₁₂`` identically zero
    against this closed form, so the negative control here is total separation
    rather than a ratio.  10% is the box error at padding 0.08 measured in
    step 1 (−9.35%); see the module docstring for why it is not tightened.
    """
    m12 = mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    omega_m12 = OMEGA * m12
    z12 = 0.5 * (reaction_z[0, 1] + reaction_z[1, 0])
    relative_error = z12.imag / omega_m12 - 1.0
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 2] M12 = {m12:.6e} H, omega*M12 = {omega_m12:+.6e} Ohm; "
            f"Im Z12 = {z12.imag:+.6e} Ohm ({relative_error:+.2%})",
            flush=True,
        )
    assert abs(relative_error) < 0.10, (
        f"Im Z12 = {z12.imag:.6e} Ohm is {relative_error:+.2%} from the closed "
        f"form omega*M12 = {omega_m12:.6e} Ohm"
    )


@complex_only
def test_mutual_impedance_falls_off_like_the_closed_form(doubling_pair):
    """`PORT-1` step 2c: ``|Z₁₂(2d)|/|Z₁₂(d)|`` against ``M(2d)/M(d)``.

    The step-2 gate compares one ``Im Z₁₂`` against one closed-form ``ωM₁₂``, so
    a solver that got the *scale* right for the wrong reason passes it.  This
    asserts the geometric fall-off instead: doubling the separation from
    ``d = 0.04`` to ``2d = 0.08`` must divide the coupling by the ratio Jackson
    5.37 gives for the same two loop radii, **0.287120** (evaluated here, not
    quoted; the probe log reproduces it to six figures).

    **Negative control.**  A solver blind to separation — one whose ``Z₁₂``
    came from the source magnitude rather than the field between the loops —
    returns ratio 1.000 against 0.287.  That is a 3.5× separation, which is the
    ceiling this control can offer, and it is ample against a 10% bound.

    10% is the bound step 2's ``Im Z₁₂`` carries, justified by the PEC box
    sensitivity measured in step 1, and it is **not** tightened on this run's
    margin.  The two boxes are not the same even at a shared padding (half_z
    0.145 → 0.165 m), so part of the wall error cancels in the ratio and part
    does not; that residue is exactly what forced the pair into the larger box —
    see ``AIR_PADDING_DOUBLING``, whose comment tabulates the measured sweep
    −13.33% / −8.78% / −5.93% at padding 0.08 / 0.10 / 0.12.  ``Z₂₁`` stands in
    for ``Z₁₂`` — reciprocity is 3.06e-13 on this fixture, so the second solve
    at each separation buys nothing but time.
    """
    ratio_closed_form = mutual_inductance(
        MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION_DOUBLE
    ) / mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    z12_d = doubling_pair[SEPARATION][1, 0]
    z12_2d = doubling_pair[SEPARATION_DOUBLE][1, 0]
    ratio_fem = abs(z12_2d) / abs(z12_d)
    relative_error = ratio_fem / ratio_closed_form - 1.0
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 2c] |Z12(d)| = {abs(z12_d):.6e} Ohm, "
            f"|Z12(2d)| = {abs(z12_2d):.6e} Ohm; ratio {ratio_fem:.6f} vs "
            f"closed form {ratio_closed_form:.6f} ({relative_error:+.2%}); "
            f"separation-blind control would give 1.000000",
            flush=True,
        )
    assert abs(relative_error) < 0.10, (
        f"|Z12(2d)|/|Z12(d)| = {ratio_fem:.6f} is {relative_error:+.2%} from the "
        f"closed-form M(2d)/M(d) = {ratio_closed_form:.6f}"
    )


@complex_only
def test_projected_port_diagonal_is_inductive(reaction_diagonal):
    """``Im Z_ii > 0`` on the production port path — gateable a priori.

    `PORT-1` step 2f's point.  A lossless loop in air stores more magnetic than
    electric energy, so the diagonal of a reaction Z-matrix must be inductive;
    with the prescribed (unprojected) drive this fixture measured
    ``−4.108550e+01 Ω`` (`20260803T003217Z_PORT-1-step2-gate.log:432`), because
    the discrete gradient content of ``J`` carried 48.52 Ω of spurious electric
    energy (step 2d, ratio 0.999998 of the excess).  The control is therefore a
    sign flip, not a margin.  Asserted on both routes so that neither a sign
    slip in the reaction bookkeeping nor one in the energies passes alone, and
    on **both** ports so a rank-local or tag-specific error cannot hide in one.
    """
    assert reaction_diagonal, "the reaction fixture recorded no diagonal"
    for tag, d in reaction_diagonal.items():
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 2f] tag {tag}: Im Z = {d['reaction']:+.6e} Ohm "
                f"(reaction), {d['energy']:+.6e} Ohm (energy); control "
                f"{UNPROJECTED_IM_Z11_OHM:+.6e} Ohm",
                flush=True,
            )
        assert d["reaction"] > 0.0, (
            f"tag {tag}: Im Z = {d['reaction']:.6e} Ohm (reaction) is not "
            f"inductive; the production drive is still unprojected "
            f"(control {UNPROJECTED_IM_Z11_OHM:.6e} Ohm)"
        )
        assert d["energy"] > 0.0, (
            f"tag {tag}: Im Z = {d['energy']:.6e} Ohm (energy) is not "
            f"inductive; W_e still exceeds W_m"
        )


@complex_only
def test_projected_port_diagonal_satisfies_the_complex_power_identity(reaction_diagonal):
    """``Im Z_ii = 4ω(W_m − W_e)/I′²`` to 1e-9 through ``solve()``.

    Exact for the discrete solution, so it gates the *bookkeeping* of the
    production path rather than its physics: the reaction route integrates
    ``E·J`` over the driven tag while the energy route never sees the source at
    all, so a wrong ``I′`` cancels (it divides both) but a load assembled on the
    wrong measure, an indicator that missed cells, or an unreduced rank does
    not.  This is the assertion that would catch ``project_source=True``
    building ``J′`` from one tag set and normalising by another.
    """
    for tag, d in reaction_diagonal.items():
        residual = abs(d["reaction"] - d["energy"]) / abs(d["reaction"])
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 2f] tag {tag}: identity residual = "
                f"{residual:.4e}; I = {d['current']:.6f} A, I' = "
                f"{d['current_prime']:.6f} A",
                flush=True,
            )
        assert residual < IDENTITY_TOLERANCE, (
            f"tag {tag}: complex-power identity broken on the production "
            f"projected drive: reaction {d['reaction']:.6e} Ohm vs energy "
            f"{d['energy']:.6e} Ohm, relative {residual:.4e}"
        )


@complex_only
def test_projected_port_diagonal_matches_grover(reaction_diagonal):
    """``Im Z_ii/ωL_Grover`` inside step 2e's measured band.

    The independent physics anchor of the step: Grover's closed form for a
    circular loop of round cross-section, ``ωL = 6.818343 Ω`` here.  The band
    is measured rather than derived — the PEC box at padding 0.08 m perturbs
    the isolated-loop inductance by an amount nobody has measured — and it is
    step 2e's band on the hand-rolled projection, carried over unchanged
    because the production path reproduced that run's ratio to 2e-5.
    """
    from tests.validation.test_port_self_impedance_energy import grover_loop_inductance

    omega_l = OMEGA * grover_loop_inductance(MAJOR_RADIUS, MINOR_RADIUS)
    low, high = GROVER_RATIO_BAND
    for tag, d in reaction_diagonal.items():
        ratio = d["energy"] / omega_l
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 2f] tag {tag}: Im Z/omega*L_Grover = "
                f"{ratio:.6f} ({d['energy']:+.6e} / {omega_l:+.6e} Ohm)",
                flush=True,
            )
        assert low < ratio < high, (
            f"tag {tag}: Im Z/omega*L_Grover = {ratio:.6f} is outside the "
            f"banded [{low}, {high}]"
        )


@complex_only
def test_mutual_impedance_real_part_is_structurally_zero(reaction_z):
    """``Re Z₁₂`` is absent, not small.

    The domain is lossless air, so the curl-curl operator is real-symmetric and
    the reaction integral has no real part to cancel — step 1 measured exactly
    ``0.0``.  1e-30 is far below anything a convergence argument could deliver;
    only a structural zero passes it.
    """
    z12 = 0.5 * (reaction_z[0, 1] + reaction_z[1, 0])
    if MPI.COMM_WORLD.rank == 0:
        print(f"[PORT-1 step 2] Re Z12 = {z12.real:+.6e} Ohm", flush=True)
    assert abs(z12.real) < 1e-30, f"Re Z12 = {z12.real:.6e} Ohm is not structurally zero"


@complex_only
def test_scattering_matrix_is_symmetric_and_passive(reaction_z):
    """``S = (Z − Z₀I)(Z + Z₀I)⁻¹`` at Z₀ = 50 Ω: symmetric and passive.

    The first S-matrix in this repository computed from a solved field.  A
    lossless reciprocal 2-port has *unitary* S, so ``‖S‖₂ = 1`` exactly;
    passivity (``≤ 1``) is the requirement and unitarity to 1e-9 is the sharper
    statement of the same physics, which a real part leaking into Z would break.
    """
    s = scattering_from_impedance(reaction_z, REFERENCE_IMPEDANCE_OHM)
    asymmetry = np.linalg.norm(s - s.T) / np.linalg.norm(s)
    spectral_norm = float(np.linalg.norm(s, 2))
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 2] S (Z0 = {REFERENCE_IMPEDANCE_OHM:.0f} Ohm): "
            f"S11 = {s[0,0]:+.6e}, S21 = {s[1,0]:+.6e}; "
            f"||S-S^T||/||S|| = {asymmetry:.4e}, ||S||_2 = {spectral_norm:.12f}",
            flush=True,
        )
    assert asymmetry < 1e-9, f"S asymmetry {asymmetry:.4e} exceeds 1e-9"
    assert spectral_norm <= 1.0 + 1e-9, f"||S||_2 = {spectral_norm:.12f} is not passive"
    assert abs(spectral_norm - 1.0) < 1e-9, (
        f"lossless network must have unitary S, got ||S||_2 = {spectral_norm:.12f}"
    )


@complex_only
def test_packaged_conversion_and_sanity_metrics_on_a_solved_field(reaction_z):
    """`PORT-1` step 3a: the *packaged* Z→S path, gated against a solved field.

    Step 2 produced this repository's first S-matrix from a solved field, but as
    three numpy lines inside this test file; the package itself still reached an
    S-matrix only through `excitation.py`'s placeholder coupling model.  This
    asserts three things about
    :func:`fem_em_solver.ports.sparameters_from_impedance`:

      * **code-path equivalence, 1e-12 entry by entry** against
        ``scattering_from_impedance`` above — the two must be the same
        conversion, not merely close, so the bound is set at the level where
        only the ordering of the same floating-point operations can differ;
      * **the same physical answer as the logged run** — the logged ``Z``
        converted to the logged ``S₁₁``/``S₂₁``
        (`20260803T003217Z_PORT-1-step2-gate.log`) to
        ``STEP2_LOGGED_S_TOLERANCE`` (see ``STEP2_LOGGED_Z`` for why 1e-6 and
        not 1e-12, and why step 2f moved this anchor off the live fixture);
      * **the existing sanity metrics, evaluated on a real matrix for the first
        time.**  ``summarize_sparameter_sanity`` has only ever seen placeholder
        arithmetic, which is why `PORT-5` is ⚠️.  A lossless reciprocal 2-port
        has unitary S, so both ``passivity_max_sigma`` and every column power
        sum are **exactly** 1: asserted to 1e-9, an identity rather than a
        tolerance, and the same physics the unitarity assertion above states.

    **Negative control — total separation, not a ratio.**  The placeholder path
    on two ports returns an *identically zero* diagonal: both fakes set
    ``current = voltage/z0`` at the driven port, so ``b = (V − Z₀I)/(2√Z₀) = 0``
    exactly (known-issues 3).  Here ``|S₁₁| = 0.9996``.  As with step 2's
    pre-`GEO-8` ``Z₁₂ ≡ 0``, the honest and the broken path do not overlap.

    **Does not close** `PORT-1`, `PORT-5` (its sweep-level metrics still run on
    the placeholder path, untouched here), or §10 criterion 2 in full — a
    two-loop air fixture is not a coil.
    """
    s_packaged = sparameters_from_impedance(
        reaction_z, z0_ohm=REFERENCE_IMPEDANCE_OHM
    )
    s_test_path = scattering_from_impedance(reaction_z, REFERENCE_IMPEDANCE_OHM)
    max_entry_difference = float(np.max(np.abs(s_packaged - s_test_path)))

    report = summarize_sparameter_sanity(s_packaged)
    column_power_sums = np.sum(np.abs(s_packaged) ** 2, axis=0)

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 3a] packaged S: S11 = {s_packaged[0,0]:+.6e}, "
            f"S21 = {s_packaged[1,0]:+.6e}; max|S_pkg - S_test| = "
            f"{max_entry_difference:.4e}",
            flush=True,
        )
        print(
            f"[PORT-1 step 3a] vs step-2 log: |dS11| = "
            f"{abs(s_packaged[0,0] - STEP2_LOGGED_S11):.4e}, |dS21| = "
            f"{abs(s_packaged[1,0] - STEP2_LOGGED_S21):.4e}; |S11| = "
            f"{abs(s_packaged[0,0]):.6f} (placeholder path gives 0 exactly)",
            flush=True,
        )
        print(
            f"[PORT-1 step 3a] sanity metrics on a solved field: "
            f"passivity_max_sigma = {report.passivity_max_sigma:.12f}, "
            f"max column power sum = "
            f"{report.passivity_max_column_power_sum:.12f}, "
            f"reciprocity max|Sij-Sji| = {report.reciprocity_max_abs_delta:.4e}, "
            f"max rel = {report.reciprocity_max_rel_delta:.4e}, "
            f"warnings = {report.warnings}",
            flush=True,
        )

    assert max_entry_difference < 1e-12, (
        f"packaged conversion differs from the test path by "
        f"{max_entry_difference:.4e}; S_pkg = {s_packaged.tolist()}, "
        f"S_test = {s_test_path.tolist()}"
    )
    # The cross-run anchor, on the logged *Z* (see STEP2_LOGGED_Z for why it
    # moved there in step 2f): the packaged conversion must still reproduce the
    # S that run printed, from the Z that run printed.
    s_logged = sparameters_from_impedance(
        STEP2_LOGGED_Z, z0_ohm=REFERENCE_IMPEDANCE_OHM
    )
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 3a] logged-Z anchor: S11 = {s_logged[0,0]:+.6e} vs "
            f"{STEP2_LOGGED_S11:+.6e}, S21 = {s_logged[1,0]:+.6e} vs "
            f"{STEP2_LOGGED_S21:+.6e}",
            flush=True,
        )
    for label, value, expected in (
        ("S11", s_logged[0, 0], STEP2_LOGGED_S11),
        ("S21", s_logged[1, 0], STEP2_LOGGED_S21),
    ):
        assert abs(value - expected) < STEP2_LOGGED_S_TOLERANCE, (
            f"{label} = {value:+.6e} from the logged Z differs from the step-2 "
            f"gate log's {expected:+.6e} by {abs(value - expected):.4e}"
        )

    # Unitarity, read through the packaged metrics: both are exact identities
    # for a lossless reciprocal network, not fitted bounds.
    assert abs(report.passivity_max_sigma - 1.0) < 1e-9, (
        f"passivity_max_sigma = {report.passivity_max_sigma:.12f} is not the "
        "unitary 1.0 a lossless 2-port must give"
    )
    assert np.max(np.abs(column_power_sums - 1.0)) < 1e-9, (
        f"column power sums {column_power_sums.tolist()} are not unity"
    )
    # Reciprocity: step 2 measured ||S-S^T||/||S|| = 2.5993e-13 on this fixture,
    # and for a 2x2 with ||S||_F = sqrt(2) that ratio *is* max|Sij-Sji|.  1e-11
    # is two orders of slack on a machine-precision quantity.
    assert report.reciprocity_max_abs_delta < 1e-11, (
        f"reciprocity max|Sij-Sji| = {report.reciprocity_max_abs_delta:.4e} "
        "exceeds 1e-11"
    )
    assert report.warnings == (), f"unexpected sanity warnings: {report.warnings}"
