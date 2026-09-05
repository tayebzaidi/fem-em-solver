"""`TH-15` step 1 probe: does the PEC hole's exterior miss fall with h?

Measurement only — no assertions.  The step-1 gate module fits the exterior
dipole coefficient β and *also* asserts a pointwise field miss at the same band;
the middle rung fits β to 1.97% while the pointwise miss on the same points is
46%.  This probe solves the same fixture on the `TH-8` resolution ladder and
prints both, so the two can be told apart: a discretisation floor falls with h,
a defect does not.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src timeout -k 30 300 mpiexec -n 2 python3 \\
       scripts/probes/th15_pec_hole_resolution.py'
"""

from __future__ import annotations

import numpy as np
from mpi4py import MPI

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel

from tests.validation.test_pec_sphere_hole import (
    BETA_PEC,
    BOX_HALF_WIDTH,
    E0,
    FREQUENCY_HZ,
    SPHERE_RADIUS,
    _dipole_basis,
    _pec_exterior_numpy,
    _probe_shells,
    _uniform_field,
)

LADDER = [(0.0125, 0.025), (0.00833, 0.0167), (0.00625, 0.0125)]


def run(resolution_sphere: float, resolution_far: float):
    comm = MPI.COMM_WORLD
    msh, cell_tags, facet_tags = MeshGenerator.sphere_in_box_domain(
        sphere_radius=SPHERE_RADIUS,
        box_half_width=BOX_HALF_WIDTH,
        resolution_sphere=resolution_sphere,
        resolution_far=resolution_far,
        comm=comm,
        as_hole=True,
    )
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=_pec_exterior_numpy(),
        pec_facet_tags=(1, 2),
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()

    points = _probe_shells()
    values, valid = evaluate_vector_field_parallel(fields.e_real, points, comm)
    if not np.all(valid):
        raise RuntimeError("probe points not evaluated")
    e = np.real(values[:, :3])
    basis = _dipole_basis(points)
    beta = float(np.sum((e - _uniform_field(points)) * basis) / np.sum(basis * basis))
    closed = _uniform_field(points) + BETA_PEC * basis
    misses = np.linalg.norm(e - closed, axis=1) / E0
    rel_l2 = float(np.linalg.norm(e - closed) / np.linalg.norm(closed))
    ncells = int(comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM))
    return beta, float(np.max(misses)), float(np.sqrt(np.mean(misses**2))), rel_l2, ncells


def main() -> None:
    comm = MPI.COMM_WORLD
    rows = [run(hs, hf) for hs, hf in LADDER]
    if comm.rank == 0:
        print("\n[TH-15 step 1 probe] PEC sphere as a hole, exterior shells r = 1.2R, 1.5R")
        print(f"{'h_sphere':>10} {'cells':>8} {'beta':>10} {'|b-1|':>9} "
              f"{'max miss':>10} {'rms miss':>10} {'rel L2':>9}")
        for (hs, _), (beta, mx, rms, l2, n) in zip(LADDER, rows):
            print(f"{hs:10.5f} {n:8d} {beta:10.6f} {abs(beta - 1.0):8.3%} "
                  f"{mx:9.3%} {rms:9.3%} {l2:8.3%}")
        h = np.array([hs for hs, _ in LADDER])
        for name, col in (("|beta-1|", [abs(r[0] - 1.0) for r in rows]),
                          ("max miss", [r[1] for r in rows]),
                          ("rms miss", [r[2] for r in rows]),
                          ("rel L2", [r[3] for r in rows])):
            rate = float(np.polyfit(np.log(h), np.log(np.array(col)), 1)[0])
            print(f"  fitted rate in h for {name:>9}: {rate:+.4f}")


if __name__ == "__main__":
    main()
