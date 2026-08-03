"""`PORT-1` step 2c — cost probe for the second separation, and the anchor.

Not a test.  Step 2c asserts the FEM ``|Z₁₂|`` ratio between ``d = 0.08`` and
``d = 0.04`` against the closed-form ``M(2d)/M(d)``, and the §7 plan requires
the *second* mesh to be cost-probed before the gate is sized: the ``d = 0.08``
box is taller than step 2's (half_z = d/2 + r_wire + padding grows 0.105 →
0.125 m at the same padding), so its cell count is not step 2's 119738 and its
MUMPS solve is not step 2's 21–31 s.  Padding 0.12 at h_far 0.02 (237926 cells)
was already killed at 180 s inside MUMPS, so the question this probe answers is
which side of that line the taller box lands on.

Reports:

  * the closed-form anchor ``M(2d)/M(d)`` evaluated here rather than quoted,
    from ``AnalyticalSolutions.circular_loop_vector_potential`` (Jackson 5.37);
  * cell count and mesh wall clock for ``d = 0.08`` at padding 0.08 /
    h_far 0.03, against step 2's measured 119738 cells / 21 s at ``d = 0.04``.

Mesh only: no solve, so this fits the smoke/standard tier and cannot itself
overrun MUMPS.  The solve time is extrapolated from the cell ratio.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 \\
       scripts/probes/port1_step2c_probe.py'
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
from fem_em_solver.utils.analytical import AnalyticalSolutions

MAJOR_RADIUS = 0.04
MINOR_RADIUS = 0.005
AIR_PADDING = 0.08
H_FAR = 0.03
H_WIRE = 0.0025
FREQUENCY_HZ = 10.0e6
CURRENT_A = 1.0
OMEGA = 2.0 * np.pi * FREQUENCY_HZ
TORUS_TAGS = (1, 2)

# Step 2's configuration, for the reference row.
SEPARATION = 0.04
SEPARATION_DOUBLE = 0.08

STEP2_CELLS = 119738  # 20260802T183747Z_PORT-1-step1-boxsens.log, d = 0.04


def mutual_inductance(a: float, rho: float, z: float) -> float:
    """``M = 2πρ·A_φ(ρ, z)/I`` for a unit-current filamentary loop of radius a."""
    pts = np.array([[rho, 0.0, z]], dtype=float)
    A = AnalyticalSolutions.circular_loop_vector_potential(pts, 1.0, a, loop_center=0.0)
    return 2.0 * np.pi * rho * float(A[0, 1])


def _azimuthal_current_density(j_magnitude: float):
    """Uniform azimuthal current; regularised inside the sqrt (complex build)."""

    def current_density(x):
        rho_safe = ufl.sqrt(x[0] ** 2 + x[1] ** 2 + 1e-24)
        return ufl.as_vector([
            -x[1] / rho_safe * j_magnitude,
            x[0] / rho_safe * j_magnitude,
            0.0,
        ])

    return current_density


def _z21(msh, cell_tags, comm) -> complex:
    """Drive torus 1, read the reaction on torus 2 — one column entry.

    Reciprocity is 3e-13 on this fixture, so ``Z₂₁`` stands in for ``Z₁₂`` and
    the second solve is not bought.
    """
    j_magnitude = CURRENT_A / (np.pi * MINOR_RADIUS**2)
    one = fem.Constant(msh, np.array(1.0, dtype=np.complex128).item())
    currents = []
    for tag in TORUS_TAGS:
        dx_tag = ufl.Measure(
            "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,)
        )
        # assemble_scalar is rank-local.
        volume = float(
            np.real(
                comm.allreduce(fem.assemble_scalar(fem.form(one * dx_tag)), op=MPI.SUM)
            )
        )
        currents.append(j_magnitude * volume / (2.0 * np.pi * MAJOR_RADIUS))

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map=None,
        boundary_condition="pec_zero_tangential_a",
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    fields = solver.solve(
        current_density=_azimuthal_current_density(j_magnitude),
        subdomain_ids=[TORUS_TAGS[0]],
    )

    x = ufl.SpatialCoordinate(msh)
    j_vec = _azimuthal_current_density(j_magnitude)(x)
    dx_test = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(TORUS_TAGS[1],)
    )
    # J is real, so inner()'s conjugation of the second argument is a no-op.
    local = fem.assemble_scalar(fem.form(ufl.inner(fields.e_complex, j_vec) * dx_test))
    total = comm.allreduce(local, op=MPI.SUM)
    return complex(-total / (currents[0] * currents[1]))


def solve_ratio(padding: float, comm) -> None:
    """``|Z₁₂(2d)|/|Z₁₂(d)|`` at one air padding, against the closed form.

    Step 2c failed at padding 0.08 (0.248854 vs 0.287120, −13.33%) with the
    per-separation errors −9.36% at ``d`` and −21.4% at ``2d``, i.e. the PEC box
    hurts the wider pair more.  This re-measures the whole ratio at a larger
    box: if the box is the cause, the ratio must move toward 0.287120.
    """
    magnitudes = {}
    for separation in (SEPARATION, SEPARATION_DOUBLE):
        t0 = time.perf_counter()
        msh, cell_tags, _ = MeshGenerator.two_torus_domain(
            separation=separation,
            major_radius=MAJOR_RADIUS,
            minor_radius=MINOR_RADIUS,
            resolution=H_FAR,
            air_padding=padding,
            wire_resolution=H_WIRE,
            far_resolution=H_FAR,
            comm=comm,
        )
        t_mesh = time.perf_counter() - t0
        tdim = msh.topology.dim
        ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
        if comm.rank == 0:
            print(
                f"[PORT-1 step 2c] padding {padding} m, d = {separation} m: "
                f"{ncells} cells, mesh {t_mesh:.1f} s",
                flush=True,
            )
        t0 = time.perf_counter()
        z = _z21(msh, cell_tags, comm)
        t_solve = time.perf_counter() - t0
        magnitudes[separation] = abs(z)
        closed = OMEGA * mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, separation)
        if comm.rank == 0:
            print(
                f"[PORT-1 step 2c] padding {padding} m, d = {separation} m: "
                f"|Z21| = {abs(z):.6e} Ohm vs omega*M = {closed:.6e} Ohm "
                f"({abs(z) / closed - 1.0:+.2%}), solve {t_solve:.1f} s",
                flush=True,
            )

    ratio_fem = magnitudes[SEPARATION_DOUBLE] / magnitudes[SEPARATION]
    ratio_cf = mutual_inductance(
        MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION_DOUBLE
    ) / mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    if comm.rank == 0:
        print(
            f"[PORT-1 step 2c] padding {padding} m: ratio {ratio_fem:.6f} vs "
            f"closed form {ratio_cf:.6f} ({ratio_fem / ratio_cf - 1.0:+.2%})",
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--solve-padding",
        type=float,
        default=None,
        help="If given, solve both separations at this air padding and report "
             "the |Z12| ratio instead of running the mesh-only cost probe.",
    )
    parser.add_argument(
        "--mesh-padding",
        type=float,
        default=AIR_PADDING,
        help="Air padding for the mesh-only cost probe (default: step 2's 0.08).",
    )
    args = parser.parse_args()

    if args.solve_padding is not None:
        solve_ratio(args.solve_padding, MPI.COMM_WORLD)
        return

    comm = MPI.COMM_WORLD
    padding = args.mesh_padding

    m_d = mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    m_2d = mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION_DOUBLE)
    if comm.rank == 0:
        print(
            f"[PORT-1 step 2c] M(d={SEPARATION}) = {m_d:.6e} H, "
            f"M(2d={SEPARATION_DOUBLE}) = {m_2d:.6e} H, "
            f"ratio M(2d)/M(d) = {m_2d / m_d:.6f}",
            flush=True,
        )

    for separation in (SEPARATION, SEPARATION_DOUBLE):
        t0 = time.perf_counter()
        msh, _, _ = MeshGenerator.two_torus_domain(
            separation=separation,
            major_radius=MAJOR_RADIUS,
            minor_radius=MINOR_RADIUS,
            resolution=H_FAR,
            air_padding=padding,
            wire_resolution=H_WIRE,
            far_resolution=H_FAR,
            comm=comm,
        )
        t_mesh = time.perf_counter() - t0
        tdim = msh.topology.dim
        # index_map(...).size_local is rank-local.
        ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
        half_z = separation / 2 + MINOR_RADIUS + padding
        if comm.rank == 0:
            print(
                f"[PORT-1 step 2c] padding {padding} m, d = {separation} m: "
                f"half_z = {half_z:.3f} m, "
                f"{ncells} cells ({ncells / STEP2_CELLS:.3f}x step 2), "
                f"mesh {t_mesh:.1f} s",
                flush=True,
            )


if __name__ == "__main__":
    main()
