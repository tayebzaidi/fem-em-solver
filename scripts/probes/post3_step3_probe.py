"""`POST-3` step 3 probe: cost and magnitude of the total-current residual.

Product is measurements, not assertions: how big the CG2 relative residual is
on the existing piecewise-σ fixture, whether it falls with h, whether the CG1
residual really is round-off (the vacuity trap), what the σ-dropped negative
control gives, and how long the extra Poisson solve costs at each mesh.

Run (complex build)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src:/workspace mpiexec -n 2 python3 \\
       scripts/probes/post3_step3_probe.py'
"""

from __future__ import annotations

import sys
import time

import numpy as np
from mpi4py import MPI

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
    build_material_fields,
)
from fem_em_solver.post.current_divergence import current_divergence_residual

from tests.validation.test_poynting_balance import (
    EPSILON_R,
    FREQUENCY_HZ,
    MU_R,
    OMEGA,
    SIGMA_HIGH,
    SIGMA_LOW,
    TAG_HIGH,
    TAG_LOW,
    _two_material_mesh,
)
from tests.validation.test_lossy_plane_wave import _exact_factory


def solve_piecewise(n: int):
    comm = MPI.COMM_WORLD
    msh, cell_tags = _two_material_mesh(n)
    material_map = {
        TAG_LOW: HomogeneousMaterial(sigma=SIGMA_LOW, epsilon_r=EPSILON_R, mu_r=MU_R),
        TAG_HIGH: HomogeneousMaterial(sigma=SIGMA_HIGH, epsilon_r=EPSILON_R, mu_r=MU_R),
    }
    exact_numpy, _ = _exact_factory(SIGMA_LOW)
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=EPSILON_R, mu_r=MU_R),
        material_map=material_map,
        cell_tags=cell_tags,
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=exact_numpy,
    )
    t0 = time.perf_counter()
    fields = TimeHarmonicSolver(problem, degree=1).solve()
    solve_s = time.perf_counter() - t0
    sigma_field, eps_field = build_material_fields(
        msh,
        HomogeneousMaterial(sigma=0.0, epsilon_r=EPSILON_R, mu_r=MU_R),
        cell_tags=cell_tags,
        material_map=material_map,
    )
    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    return fields, sigma_field, eps_field, int(ncells), solve_s


def measure(fields, sigma_field, eps_field, **kwargs):
    comm = MPI.COMM_WORLD
    t0 = time.perf_counter()
    out = current_divergence_residual(
        fields.e_complex,
        omega=OMEGA,
        sigma=sigma_field,
        epsilon_r=eps_field,
        comm=comm,
        **kwargs,
    )
    out["seconds"] = time.perf_counter() - t0
    return out


def show(label: str, r: dict) -> None:
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"  {label:34s} rel = {r['relative_residual']:.6e}  "
            f"dual = {r['residual_dual_norm']:.4e}  "
            f"|J| = {r['current_scale']:.4e}  "
            f"its = {r['ksp_iterations']:4d}  {r['seconds']:6.2f} s"
        )
        sys.stdout.flush()


def main() -> None:
    comm = MPI.COMM_WORLD
    rels = {}
    for n in (8, 12):
        fields, sig, eps, ncells, solve_s = solve_piecewise(n)
        if comm.rank == 0:
            print(f"\n[POST-3 step 3] n = {n} ({ncells} cells), solve {solve_s:.2f} s")
        cg2 = measure(fields, sig, eps, degree=2)
        show("CG2 residual (the metric)", cg2)
        rels[n] = cg2["relative_residual"]
        cg1 = measure(fields, sig, eps, degree=1)
        show("CG1 residual (vacuity check)", cg1)
        blind = measure(fields, sig, eps, degree=2, include_sigma=False)
        show("CG2, sigma dropped from J_tot", blind)
        if comm.rank == 0:
            print(
                f"    separation blind/honest = "
                f"{blind['relative_residual'] / cg2['relative_residual']:.3f}x, "
                f"CG2/CG1 = {cg2['relative_residual'] / cg1['relative_residual']:.3e}x"
            )
            sys.stdout.flush()

    if comm.rank == 0:
        print("\n[POST-3 step 3] CG2 relative residual vs h:")
        for n, r in rels.items():
            print(f"  n = {n:3d}: {r:.6e}")
        for a, b in ((8, 12),):
            rate = np.log(rels[a] / rels[b]) / np.log(b / a)
            print(f"  rate {a}->{b}: {rate:.4f}")


if __name__ == "__main__":
    main()
