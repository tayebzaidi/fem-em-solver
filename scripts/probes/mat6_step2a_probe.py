"""`MAT-6` step 2a — loop-over-half-space cost/air-box probe.

Not a test: this is the measurement that *sizes* the step-2b gate.  It solves
the same filamentary-loop-over-conductor problem twice per air box — once with
the half-space conducting ("loaded"), once with it identical to the air above
it ("free") — and extracts the impedance change by the reaction integral

    ΔZ = −(1/I²) ∫_wire (E_loaded − E_free) · J dV                        (1)

The difference is what makes this tractable: the loop's own self-impedance and
most of the PEC-truncation error are common to both solves and cancel in (1).
What does *not* cancel is the box's image of the currents the conductor
carries, which is why the probe runs every configuration at two box sizes and
reports the sensitivity.  That number is the tolerance budget for step 2b.

Regime.  The step-1 kernel (`utils/dodd_deeds.py`) is the 1968 eddy-current
form: displacement current is neglected on both sides.  The 2026-07-31 review
took decision (a) — gate inside that regime rather than upgrade the kernel — so
the configuration below is chosen to satisfy all three constraints at once:

  * loss tangent σ/(ωε₀) ≫ 10²  (displacement current negligible in the slab),
  * skin depth δ = √(2/(ωμ₀σ)) resolved by ≥ 3 cells and the conductor ≥ 3δ deep,
  * k₀ · (box diagonal) ≪ 1     (air-side retardation negligible).

εᵣ = 1 in the slab, per the same decision: the kernel has no εᵣ at all.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 \\
       scripts/probes/mat6_step2a_probe.py --boxes 0.10 0.15'
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils import dodd_deeds
from fem_em_solver.utils.constants import EPSILON_0, MU_0

# --- the configuration under test -------------------------------------------
# f and σ are free knobs (nothing ties this gate to 127.74 MHz); they are picked
# together so that δ is a resolvable centimetre-scale length while k₀ stays
# small over the whole box.  δ ∝ 1/√(fσ) and k₀ ∝ f, so a low frequency with a
# high conductivity satisfies both.  Numbers printed by main() rather than
# asserted here.
FREQUENCY_HZ = 10.0e6
SIGMA_SLAB = 100.0
EPSILON_R_SLAB = 1.0

LOOP_RADIUS = 0.04
CURRENT_A = 1.0
# Overridden from the command line by main(): the reference in
# ``utils/dodd_deeds.py`` is *filamentary*, so the ratio h/r_wire is a knob the
# probe has to sweep — evaluating the closed form at h ± r_wire shows how much
# of the disagreement is the finite wire section rather than the field solve.
WIRE_RADIUS = 0.0025
LIFTOFF = 0.020

WIRE_TAG = 1
SLAB_TAG = 3


def _azimuthal_current_density(j_magnitude: float):
    """Uniform azimuthal current about the z-axis (same pattern as the
    magnetostatic loop fixture, `tests/validation/test_circular_loop.py`)."""

    def current_density(x):
        # Regularised inside the sqrt rather than with ufl.max_value: in complex
        # mode UFL refuses conditionals on complex-valued operands, and the
        # magnetostatic fixture's max_value form fails to compile there.
        rho_safe = ufl.sqrt(x[0] ** 2 + x[1] ** 2 + 1e-24)
        return ufl.as_vector([
            -x[1] / rho_safe * j_magnitude,
            x[0] / rho_safe * j_magnitude,
            0.0,
        ])

    return current_density


def _solve(msh, cell_tags, sigma_slab: float, comm):
    """One time-harmonic solve; returns (e_complex, seconds)."""
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            SLAB_TAG: HomogeneousMaterial(
                sigma=sigma_slab, epsilon_r=EPSILON_R_SLAB, mu_r=1.0
            )
        },
        boundary_condition="pec_zero_tangential_a",
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    j_magnitude = CURRENT_A / (np.pi * WIRE_RADIUS**2)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=_azimuthal_current_density(j_magnitude),
        subdomain_ids=[WIRE_TAG],
    )
    comm.Barrier()
    return fields.e_complex, time.perf_counter() - t0


def _reaction_impedance(msh, cell_tags, e_loaded, e_free, current_a, comm) -> complex:
    """Equation (1), reduced across ranks (``assemble_scalar`` is rank-local).

    ``current_a`` is the *meshed* loop current, not the nominal one: the
    discretised torus does not have the exact volume of the analytic one, and
    ΔZ goes as 1/I², so a 17% volume deficit would show up as a 30% impedance
    error that has nothing to do with the field solve.
    """
    j_magnitude = CURRENT_A / (np.pi * WIRE_RADIUS**2)
    x = ufl.SpatialCoordinate(msh)
    j_vec = _azimuthal_current_density(j_magnitude)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    # J is real, so inner()'s conjugation of its second argument is a no-op —
    # this is the reaction integral ∫ΔE·J, not ∫ΔE·J̄.
    local = fem.assemble_scalar(
        fem.form(ufl.inner(e_loaded - e_free, j_vec) * dx_wire)
    )
    total = comm.allreduce(local, op=MPI.SUM)
    return complex(-total / current_a**2)


def _wire_volume(msh, cell_tags, comm) -> float:
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    one = fem.Constant(msh, np.array(1.0, dtype=np.complex128).item())
    return float(
        np.real(comm.allreduce(fem.assemble_scalar(fem.form(one * dx_wire)), op=MPI.SUM))
    )


def run_box(box_half_width: float, args, comm):
    log = comm.rank == 0
    t_mesh = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=LOOP_RADIUS,
        wire_radius=WIRE_RADIUS,
        liftoff=LIFTOFF,
        box_half_width=box_half_width,
        resolution_wire=args.h_wire,
        resolution_near=args.h_near,
        resolution_far=args.h_far,
        near_half_width=args.near_half_width,
        near_depth=args.near_depth,
        near_height=args.near_height,
        comm=comm,
    )
    t_mesh = time.perf_counter() - t_mesh

    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    v_wire = _wire_volume(msh, cell_tags, comm)
    v_wire_exact = 2.0 * np.pi**2 * LOOP_RADIUS * WIRE_RADIUS**2
    # ∫J_φ dV = I · 2πa for an ideal torus, so the meshed volume fixes the
    # current the solver actually sees.
    j_magnitude = CURRENT_A / (np.pi * WIRE_RADIUS**2)
    current_meshed = j_magnitude * v_wire / (2.0 * np.pi * LOOP_RADIUS)

    if log:
        print(f"\n=== box half-width W = {box_half_width:.4f} m ===", flush=True)
        print(f"  mesh: {ncells} cells, generated in {t_mesh:.1f} s", flush=True)
        print(
            f"  wire volume (meshed / exact torus): {v_wire:.6e} / "
            f"{v_wire_exact:.6e} m^3  ({v_wire / v_wire_exact - 1.0:+.2%}); "
            f"meshed loop current {current_meshed:.6f} A",
            flush=True,
        )

    e_loaded, t_loaded = _solve(msh, cell_tags, SIGMA_SLAB, comm)
    e_free, t_free = _solve(msh, cell_tags, 0.0, comm)
    dz = _reaction_impedance(msh, cell_tags, e_loaded, e_free, current_meshed, comm)
    zero = fem.Function(e_free.function_space)
    z_loaded = _reaction_impedance(msh, cell_tags, e_loaded, zero, current_meshed, comm)
    z_free = _reaction_impedance(msh, cell_tags, e_free, zero, current_meshed, comm)

    if log:
        print(f"  solve wall clock: loaded {t_loaded:.1f} s, free {t_free:.1f} s", flush=True)
        # Absolute terminal impedances, for diagnosis only: they carry the coil
        # self-inductance and the PEC-box error, which is precisely what the
        # difference is meant to remove.
        print(f"  Z_free   = {z_free.real:+.6e} + j({z_free.imag:+.6e}) Ohm", flush=True)
        print(f"  Z_loaded = {z_loaded.real:+.6e} + j({z_loaded.imag:+.6e}) Ohm", flush=True)
        print(f"  FEM  dZ = {dz.real:+.6e} + j({dz.imag:+.6e}) Ohm", flush=True)
    return dict(
        W=box_half_width, ncells=int(ncells), dz=dz,
        t_mesh=t_mesh, t_loaded=t_loaded, t_free=t_free,
    )


def main() -> None:
    # Rebound from the command line below rather than threaded through every
    # helper: this is a probe whose whole job is to sweep these two numbers.
    global WIRE_RADIUS, LIFTOFF

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boxes", type=float, nargs="+", default=[0.10, 0.15])
    parser.add_argument("--wire-radius", type=float, default=WIRE_RADIUS)
    parser.add_argument("--liftoff", type=float, default=LIFTOFF)
    parser.add_argument("--h-wire", type=float, default=0.004)
    parser.add_argument("--h-near", type=float, default=0.005)
    parser.add_argument("--h-far", type=float, default=0.02)
    parser.add_argument("--near-half-width", type=float, default=0.06)
    parser.add_argument("--near-depth", type=float, default=0.05)
    parser.add_argument("--near-height", type=float, default=0.025)
    args = parser.parse_args()
    WIRE_RADIUS = args.wire_radius
    LIFTOFF = args.liftoff

    comm = MPI.COMM_WORLD
    log = comm.rank == 0

    omega = 2.0 * np.pi * FREQUENCY_HZ
    k0 = omega * np.sqrt(MU_0 * EPSILON_0)
    loss_tangent = SIGMA_SLAB / (omega * EPSILON_0 * EPSILON_R_SLAB)
    delta = dodd_deeds.skin_depth(FREQUENCY_HZ, SIGMA_SLAB)

    if log:
        print("=== MAT-6 step 2a: loop over lossy half-space, probe ===", flush=True)
        print(
            f"  f = {FREQUENCY_HZ:.4g} Hz, sigma = {SIGMA_SLAB:g} S/m, eps_r = "
            f"{EPSILON_R_SLAB:g}, a = {LOOP_RADIUS} m, h = {LIFTOFF} m, "
            f"r_wire = {WIRE_RADIUS} m",
            flush=True,
        )
        print(f"  loss tangent sigma/(w eps0 eps_r) = {loss_tangent:.4g}  (want >> 1e2)", flush=True)
        print(
            f"  skin depth delta = {delta:.6f} m -> {delta / args.h_near:.2f} near-cells "
            f"per delta; slab depth/delta = {min(args.boxes) / delta:.2f}",
            flush=True,
        )
        for W in args.boxes:
            print(
                f"  k0 * box diagonal (W={W}) = {k0 * 2 * W * np.sqrt(3.0):.4f}  (want << 1)",
                flush=True,
            )

    # Closed form, filamentary loop.  Also evaluated a wire radius either side of
    # the nominal liftoff, because the FEM source is a torus of finite section
    # and the filamentary reference has no such spread.
    dz_ref = dodd_deeds.coil_impedance_change(
        FREQUENCY_HZ, LOOP_RADIUS, LIFTOFF, SIGMA_SLAB
    )
    dz_lo = dodd_deeds.coil_impedance_change(
        FREQUENCY_HZ, LOOP_RADIUS, LIFTOFF - WIRE_RADIUS, SIGMA_SLAB
    )
    dz_hi = dodd_deeds.coil_impedance_change(
        FREQUENCY_HZ, LOOP_RADIUS, LIFTOFF + WIRE_RADIUS, SIGMA_SLAB
    )
    if log:
        print(
            f"\n  closed form (filamentary, h = {LIFTOFF}): dZ = {dz_ref.real:+.6e} "
            f"+ j({dz_ref.imag:+.6e}) Ohm",
            flush=True,
        )
        print(
            f"  same at h -/+ r_wire: dR {dz_lo.real:.4e} .. {dz_hi.real:.4e}, "
            f"dX {dz_lo.imag:.4e} .. {dz_hi.imag:.4e}  "
            f"(finite-section spread: dR {abs(dz_hi.real - dz_lo.real) / abs(dz_ref.real):.1%}, "
            f"dX {abs(dz_hi.imag - dz_lo.imag) / abs(dz_ref.imag):.1%})",
            flush=True,
        )

    results = [run_box(W, args, comm) for W in args.boxes]

    if log:
        print("\n=== summary ===", flush=True)
        print("  W [m]   cells      dR [Ohm]        dX [Ohm]     dR/ref-1   dX/ref-1", flush=True)
        for r in results:
            print(
                f"  {r['W']:.3f}  {r['ncells']:7d}  {r['dz'].real:+.6e}  "
                f"{r['dz'].imag:+.6e}  {r['dz'].real / dz_ref.real - 1.0:+8.2%}  "
                f"{r['dz'].imag / dz_ref.imag - 1.0:+8.2%}",
                flush=True,
            )
        if len(results) >= 2:
            a, b = results[0], results[1]
            print(
                f"\n  box-size sensitivity {a['W']:.3f} -> {b['W']:.3f} m: "
                f"dR {abs(b['dz'].real / a['dz'].real - 1.0):.3%}, "
                f"dX {abs(b['dz'].imag / a['dz'].imag - 1.0):.3%}",
                flush=True,
            )
        slowest = max(r["t_loaded"] for r in results)
        print(f"  slowest single solve: {slowest:.1f} s", flush=True)
        print("  NOTE: nothing is asserted here — this is the step-2a probe.", flush=True)


if __name__ == "__main__":
    main()
