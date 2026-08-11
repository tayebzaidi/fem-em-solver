"""`POST-4` step 1 — diagnose the mri centerline's rank-count dependence.

Diagnosis only: this script touches no ``src/`` and changes no gate.  It
rebuilds ``examples/mri/01_coil_phantom_fields.py``'s **debug** preset exactly
as `EX-16` left it (coarse resolution, magnetostatics at ``gauge_penalty=1.0``,
time-harmonic on the solver's default direct path at ``gauge_penalty=1e-3``),
then samples the same five centerline points the example prints — but with the
point evaluation **instrumented** so the suspect mechanism can be confirmed or
refuted.

The suspect (PROJECT_PLAN §7, `POST-4`): ``evaluate_vector_field_parallel`` has
each rank claim ``links[0]`` — the first *locally* colliding cell — and rank 0
resolve multi-rank claims by last-writer-wins in rank order.  For a point on a
facet/edge shared by several cells the evaluating cell is then a property of the
partition, so a field that is not continuous across that entity is sampled
partition-dependently.

Recorded per point, per rank count, for each of four fields:

* (a) **claim multiplicity** — how many ranks' ``colliding_cells`` found it;
* (b) the set of **global** cell indices claiming it (``local_to_global`` on
  *all* the links, not just ``links[0]``), reduced across ranks;
* (c) the per-claiming-cell value and the max cross-cell relative disagreement;
* (d) ``valid_mask`` from the library call, plus the library's own value;
* (e) the ε-nudge discriminator — the same z, offset to x = y = 1e-6 m.

The four fields separate two candidate loci.  ``E_lag``/``B_lag`` are the
Lagrange-P1 interpolants the example actually samples; ``E_src``/``B_src`` are
the fields they were interpolated *from*.  A P1 interpolant is continuous, so
cross-cell disagreement on ``*_lag`` at a shared entity should vanish — if it
does while the sampled values still move with rank count, the ownership
tie-break is refuted and the locus is upstream, in the interpolation.

A mesh fingerprint (global cell count + partition-independent coordinate
moments) is printed so the three rank counts can be checked for mesh identity
before their values are compared: gmsh is not guaranteed bit-reproducible, and
a mesh difference would confound the whole comparison.

Run through the harness, one invocation per rank count, e.g.::

    scripts/testing/run_and_log.sh POST-4 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && PYTHONPATH=/workspace/src \\
      FEM_EM_REQUIRE_COMPLEX=1 timeout 180 mpiexec -n 2 python3 \\
      scripts/probes/post4_step1_probe.py'"

then compare the logs with ``scripts/probes/post4_step1_spread.py``.
"""

import os

import numpy as np
import ufl
from mpi4py import MPI
from dolfinx import fem, geometry

from fem_em_solver.core import (
    HomogeneousMaterial,
    MagnetostaticProblem,
    MagnetostaticSolver,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.materials import GelledSalinePhantomMaterial
from fem_em_solver.post import evaluate_vector_field_parallel
from fem_em_solver.utils.constants import MU_0

# examples/mri/01_coil_phantom_fields.py, debug preset (RESOLUTION_PRESETS
# "coarse", centerline_sample_count 5), verbatim at the time of writing.
RESOLUTION_M = 0.02
CENTERLINE_SAMPLES = 5
FREQUENCY_HZ = 127.74e6  # the example's --frequency-hz default
NUDGE_M = 1e-6
FIELD_FLOOR = 1e-30

MESH_PARAMS = {
    "coil_major_radius": 0.08,
    "coil_minor_radius": 0.01,
    "coil_separation": 0.08,
    "phantom_radius": 0.04,
    "phantom_height": 0.10,
    "air_padding": 0.04,
    "resolution": RESOLUTION_M,
}


def mesh_fingerprint(mesh, comm):
    """Partition-independent fingerprint: global cell count + midpoint moments.

    Sums are reduced across ranks, so the value does not depend on how the mesh
    was partitioned but does change if the mesh itself changes.  Summation order
    still varies, so compare at ~10 significant digits, not bitwise.
    """
    tdim = mesh.topology.dim
    n_local = mesh.topology.index_map(tdim).size_local
    cells = np.arange(n_local, dtype=np.int32)
    midpoints = mesh.geometry.x[mesh.geometry.dofmap[cells]].mean(axis=1)
    n_global = comm.allreduce(n_local, op=MPI.SUM)
    m1 = comm.allreduce(float(np.sum(midpoints)), op=MPI.SUM)
    m2 = comm.allreduce(float(np.sum(midpoints ** 2)), op=MPI.SUM)
    return n_global, m1, m2


def claim_census(function, points, comm):
    """Per point: every claiming (rank, global cell) and that cell's value.

    Unlike the library — which keeps only ``links[0]`` per rank and lets the
    highest-numbered claiming rank overwrite — this evaluates at **every**
    colliding cell, so the cross-cell disagreement that the tie-break would be
    choosing between is measured directly.

    Returns, on rank 0, a list of per-point lists of
    ``(rank, global_cell, local_is_links0, |value|)``; ``None`` elsewhere.
    """
    mesh = function.function_space.mesh
    tdim = mesh.topology.dim
    imap = mesh.topology.index_map(tdim)
    n_points = points.shape[0]

    bb_tree = geometry.bb_tree(mesh, tdim)
    candidate_cells = geometry.compute_collisions_points(bb_tree, points)
    colliding_cells = geometry.compute_colliding_cells(mesh, candidate_cells, points)

    idx, cells, is_first = [], [], []
    for i in range(n_points):
        links = colliding_cells.links(i)
        for j, cell in enumerate(links):
            idx.append(i)
            cells.append(int(cell))
            is_first.append(1 if j == 0 else 0)

    if idx:
        cells_arr = np.asarray(cells, dtype=np.int32)
        idx_arr = np.asarray(idx, dtype=np.int32)
        # ``Function.eval`` squeezes to shape (value_size,) for a single point
        # (`MAG-6` step 4's sqrt(3) artifact) — reshape before indexing.
        vals = np.asarray(function.eval(points[idx_arr], cells_arr)).reshape(len(idx), -1)
        mags = np.linalg.norm(vals, axis=1).astype(np.float64)
        gcells = imap.local_to_global(cells_arr).astype(np.int64)
    else:
        idx_arr = np.zeros(0, dtype=np.int32)
        mags = np.zeros(0, dtype=np.float64)
        gcells = np.zeros(0, dtype=np.int64)

    payload = (comm.rank, idx_arr, gcells, np.asarray(is_first, dtype=np.int32), mags)
    gathered = comm.gather(payload, root=0)
    if comm.rank != 0:
        return None

    census = [[] for _ in range(n_points)]
    for rank, r_idx, r_gcells, r_first, r_mags in gathered:
        for k, i in enumerate(r_idx):
            census[int(i)].append(
                (int(rank), int(r_gcells[k]), int(r_first[k]), float(r_mags[k]))
            )
    return census


def report(label, function, points, comm, tag):
    """Print the library value, mask, and the full claim census for one field."""
    lib_values, lib_valid = evaluate_vector_field_parallel(function, points, comm=comm)
    lib_mag = np.linalg.norm(lib_values, axis=1).astype(np.float64)
    census = claim_census(function, points, comm)
    if comm.rank != 0:
        return

    for i in range(points.shape[0]):
        rows = census[i]
        ranks = sorted({r for r, _g, _f, _v in rows})
        gcells = sorted({g for _r, g, _f, _v in rows})
        # One value per distinct *global* cell — the same ghosted cell claimed
        # by two ranks is one cell, not two.
        by_cell = {}
        for _r, g, _f, v in rows:
            by_cell.setdefault(g, []).append(v)
        cell_vals = [float(np.mean(v)) for v in by_cell.values()]
        if len(cell_vals) > 1:
            hi, lo = max(cell_vals), min(cell_vals)
            cross = (hi - lo) / max(abs(hi), FIELD_FLOOR)
        else:
            cross = 0.0
        print(
            f"CLAIM {tag} {label} {i:>2} z={points[i, 2]:+.6f} "
            f"nranks={len(ranks)} ncells={len(gcells)} "
            f"valid={bool(lib_valid[i])} maxcross={cross:.6e} "
            f"libmag={lib_mag[i]:.12e} ranks={ranks} gcells={gcells}",
            flush=True,
        )
    print(
        f"VALUES {tag} {label} " + " ".join(f"{v:.12e}" for v in lib_mag),
        flush=True,
    )


def main():
    comm = MPI.COMM_WORLD

    if comm.rank == 0:
        print("=" * 72)
        print(f"POST-4 step 1 probe — ranks={comm.size}")
        print(
            f"fixture: examples/mri/01 debug preset, resolution={RESOLUTION_M} m, "
            f"{CENTERLINE_SAMPLES} centerline points, f={FREQUENCY_HZ:.6e} Hz"
        )
        print("=" * 72, flush=True)

    mesh, cell_tags, facet_tags = MeshGenerator.coil_phantom_domain(**MESH_PARAMS, comm=comm)
    n_global, m1, m2 = mesh_fingerprint(mesh, comm)
    if comm.rank == 0:
        print(f"MESH_FINGERPRINT cells={n_global} m1={m1:.12e} m2={m2:.12e}", flush=True)

    j_magnitude = 1.0 / (np.pi * 0.01 ** 2)

    def current_density(_x):
        return ufl.as_vector([0.0, 0.0, j_magnitude])

    mag_problem = MagnetostaticProblem(
        mesh=mesh, cell_tags=cell_tags, facet_tags=facet_tags, mu=MU_0
    )
    mag_solver = MagnetostaticSolver(mag_problem, degree=1)
    a_field = mag_solver.solve(
        current_density=current_density, subdomain_ids=[1, 2], gauge_penalty=1.0
    )
    b_field = mag_solver.compute_b_field()

    background = HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0)
    phantom = GelledSalinePhantomMaterial(
        sigma=0.72, epsilon_r=76.5, frequency_hz=FREQUENCY_HZ, mu_r=1.0
    )
    th_problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=FREQUENCY_HZ,
        material=background,
        cell_tags=cell_tags,
        facet_tags=facet_tags,
        phantom_material=phantom,
        phantom_tag=3,
        collect_solver_diagnostics=True,
    )
    th_solver = TimeHarmonicSolver(th_problem, degree=1)
    th_fields = th_solver.solve(
        current_density=current_density, subdomain_ids=[1, 2], gauge_penalty=1e-3
    )
    e_field = th_fields.e_imag
    if comm.rank == 0 and th_fields.solve_diagnostics is not None:
        d = th_fields.solve_diagnostics
        print(
            f"SOLVE ksp={d.ksp_type} pc={d.pc_type} converged={d.converged} "
            f"reason={d.converged_reason} iterations={d.iterations}",
            flush=True,
        )

    # The example samples the *Lagrange interpolants*, not the source fields.
    v_lagrange = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    b_lagrange = fem.Function(v_lagrange, name="B")
    b_lagrange.interpolate(b_field)
    e_lagrange = fem.Function(v_lagrange, name="E")
    e_lagrange.interpolate(e_field)

    z_line = np.linspace(-0.045, 0.045, CENTERLINE_SAMPLES)
    axis_points = np.zeros((CENTERLINE_SAMPLES, 3), dtype=np.float64)
    axis_points[:, 2] = z_line
    nudge_points = axis_points.copy()
    nudge_points[:, 0] = NUDGE_M
    nudge_points[:, 1] = NUDGE_M

    fields = [("E_lag", e_lagrange), ("B_lag", b_lagrange), ("E_src", e_field), ("B_src", b_field)]
    for tag, points in (("axis", axis_points), ("nudge", nudge_points)):
        for label, function in fields:
            try:
                report(label, function, points, comm, tag)
            except Exception as exc:  # pragma: no cover - diagnostic resilience
                if comm.rank == 0:
                    print(f"SKIP {tag} {label}: {type(exc).__name__}: {exc}", flush=True)
                comm.Barrier()

    if comm.rank == 0:
        print("PROBE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
