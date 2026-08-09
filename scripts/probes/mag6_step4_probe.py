"""`MAG-6` step 4 — diagnose the centerline jump-ratio metric's 88% rank scatter.

Diagnosis only: this script touches no ``src/`` and changes no gate.  It
rebuilds the *recorded* step-3 fixture (``resolution = 0.010`` m, uniform
``mu = MU_0``), solves once, and then samples the DG0 ``curl A`` on the same
9-point centerline the gate uses — but with the point evaluation
**instrumented** so that the two candidate mechanisms step 3 measured without
separating can be told apart:

* **partition-owned sampling** — a centerline point lying on a facet/vertex
  shared by several cells collides with a cell on more than one rank.
  ``evaluate_vector_field_parallel`` gathers per-rank contributions and writes
  them into the result in rank order, so the **last** claiming rank wins.  The
  sampled value is then a function of the partition, not of the field.
* **mesh noise** — gmsh/Netgen is not bit-reproducible run to run, so two
  identical invocations at the same rank count give different meshes and hence
  different cell-wise values (step 3 measured 6.8% drift at fixed ``-n 2``).

The instrumentation records, per centerline point: how many ranks claim it,
which rank wins under the library's rank-order overwrite, every claimant's
value, and the owning cell's midpoint.  A mesh fingerprint (global cell count
plus partition-independent coordinate moments) is printed so a fixed-rank
repeat can be checked for mesh identity before its metric is compared.

The mirror-symmetry metric is computed on the *same solve* as the in-fixture
control: it spreads 7.00% across ranks where the centerline metric spreads
88%, so whatever mechanism is found must explain the difference between the
two, not merely the centerline number.

Run through the harness, e.g.::

    scripts/testing/run_and_log.sh MAG-6 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && PYTHONPATH=/workspace/src MAG6_STEP4_TAG=n4a \\
      timeout 180 mpiexec -n 4 python3 scripts/probes/mag6_step4_probe.py'"

Environment: ``MAG6_STEP4_TAG`` labels the run in the output (used to tell a
fixed-rank repeat from its original).
"""

import os

import numpy as np
import ufl
from mpi4py import MPI
from dolfinx import fem, geometry

from fem_em_solver.core.solvers import MagnetostaticProblem, MagnetostaticSolver
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post import evaluate_vector_field_parallel
from fem_em_solver.utils.constants import MU_0

# The gate's numbers, verbatim from tests/tolerances.py at the time of writing.
# Printed for comparison only; nothing here asserts against them.
FIELD_SCALE_FLOOR = 1e-30
CENTERLINE_JUMP_RATIO_MAX = 0.60
SYMMETRY_REL_TOL = 0.35


def mesh_fingerprint(mesh, comm):
    """Partition-independent fingerprint of the mesh geometry.

    Global cell count plus low-order moments of the cell midpoints.  Sums are
    reduced across ranks, so the value is independent of how the mesh was
    partitioned but changes if the mesh itself changes (which is exactly the
    run-to-run non-reproducibility we need to detect).  Floating-point
    summation order still varies, so compare these at ~10 significant digits,
    not bitwise.
    """
    tdim = mesh.topology.dim
    n_local = mesh.topology.index_map(tdim).size_local
    cells = np.arange(n_local, dtype=np.int32)
    midpoints = mesh.geometry.x[mesh.geometry.dofmap[cells]].mean(axis=1)

    n_global = comm.allreduce(n_local, op=MPI.SUM)
    m1 = comm.allreduce(float(np.sum(midpoints)), op=MPI.SUM)
    m2 = comm.allreduce(float(np.sum(midpoints**2)), op=MPI.SUM)
    return n_global, m1, m2


def instrumented_eval(function, points, comm):
    """Evaluate like ``evaluate_vector_field_parallel``, but keep the claimants.

    Returns ``(values, claims)`` where ``values`` reproduces the library's
    result exactly — same collision calls, same rank-order overwrite — and
    ``claims`` is, on rank 0, a list of per-point lists of
    ``(rank, cell_midpoint, |value|)`` for every rank that claimed the point.
    """
    mesh = function.function_space.mesh
    n_points = points.shape[0]

    bb_tree = geometry.bb_tree(mesh, mesh.topology.dim)
    candidate_cells = geometry.compute_collisions_points(bb_tree, points)
    colliding_cells = geometry.compute_colliding_cells(mesh, candidate_cells, points)

    local_idx = []
    local_cells = []
    local_ncand = []
    for i in range(n_points):
        links = colliding_cells.links(i)
        if len(links) > 0:
            local_idx.append(i)
            # The library takes links[0].  `links` is ordered by *local* cell
            # index, which is partition-dependent, so when a point sits on a
            # facet/edge shared by several cells on this rank, which one wins
            # is a property of the partition and not of the field.
            local_cells.append(links[0])
            local_ncand.append(len(links))

    idx_arr = np.asarray(local_idx, dtype=np.int32)
    if idx_arr.size > 0:
        cells_arr = np.asarray(local_cells, dtype=np.int32)
        # ``Function.eval`` squeezes to shape (3,) when a rank claims exactly
        # ONE point.  ``rank_vals[k]`` is then the *scalar* x-component and
        # ``values[i] = rank_vals[k]`` broadcasts it into all three components,
        # inflating |B| by exactly sqrt(3) — measured 1.7320508 at points i=1
        # and i=3, the only two the probe's first pass got wrong.  The library
        # path is immune: it assigns `values[rank_indices] = rank_values`, and
        # numpy broadcasts a (3,) row into a (1, 3) slice correctly.  Reshape
        # so the two paths really are the same algorithm.
        local_values = np.asarray(function.eval(points[idx_arr], cells_arr)).reshape(-1, 3)
        local_mids = mesh.geometry.x[mesh.geometry.dofmap[cells_arr]].mean(axis=1)
        ncand_arr = np.asarray(local_ncand, dtype=np.int32)
    else:
        local_values = np.zeros((0, 3), dtype=np.float64)
        local_mids = np.zeros((0, 3), dtype=np.float64)
        ncand_arr = np.zeros(0, dtype=np.int32)

    gathered = comm.gather((comm.rank, idx_arr, local_values, local_mids, ncand_arr), root=0)

    values = None
    claims = None
    if comm.rank == 0:
        values = np.zeros((n_points, 3), dtype=np.float64)
        claims = [[] for _ in range(n_points)]
        # Same loop order as the library: ranks in ascending order, later
        # writes overwrite earlier ones.
        for rank, rank_idx, rank_vals, rank_mids, rank_ncand in gathered:
            for k, i in enumerate(rank_idx):
                values[i] = rank_vals[k]
                claims[i].append(
                    (
                        int(rank),
                        np.asarray(rank_mids[k]),
                        float(np.linalg.norm(rank_vals[k])),
                        int(rank_ncand[k]),
                    )
                )
    if comm.rank == 0 and os.environ.get("MAG6_STEP4_WRITECHECK") == "1":
        # Write-time consistency check: ``values[i]`` and ``claims[i][-1]`` are
        # written from the same ``rank_vals[k]`` one line apart, so they cannot
        # disagree unless something after this loop mutates ``values``.  Print
        # both here, before the bcast, to date the divergence.
        for i in range(n_points):
            if claims[i]:
                w = float(np.linalg.norm(values[i]))
                c = claims[i][-1][2]
                print(f"WRITECHECK {i:>2} values={w:.12e} claim={c:.12e} "
                      f"{'SAME' if w == c else 'DIFF'}", flush=True)

    values = comm.bcast(values, root=0)
    return values, claims


def jump_ratio(mag):
    return float(np.max(np.abs(np.diff(mag)))) / max(float(np.max(mag)), FIELD_SCALE_FLOOR)


def main():
    comm = MPI.COMM_WORLD
    tag = os.environ.get("MAG6_STEP4_TAG", "untagged")

    phantom_radius = 0.04
    phantom_height = 0.10
    resolution = 0.010
    sampling_clearance_resolution = 0.015

    if comm.rank == 0:
        print("=" * 72)
        print(f"MAG-6 step 4 probe — tag={tag}, ranks={comm.size}")
        print(f"fixture: resolution={resolution} m, uniform mu=MU_0 (phantom invisible)")
        print("=" * 72, flush=True)

    mesh, cell_tags, facet_tags = MeshGenerator.coil_phantom_domain(
        coil_major_radius=0.08,
        coil_minor_radius=0.01,
        coil_separation=0.08,
        phantom_radius=phantom_radius,
        phantom_height=phantom_height,
        air_padding=0.04,
        resolution=resolution,
        comm=comm,
    )

    n_global, m1, m2 = mesh_fingerprint(mesh, comm)
    if comm.rank == 0:
        print(f"MESH_FINGERPRINT cells={n_global} m1={m1:.12e} m2={m2:.12e}", flush=True)

    problem = MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, facet_tags=facet_tags, mu=MU_0)
    solver = MagnetostaticSolver(problem, degree=1)

    current_density_magnitude = 1.0 / (np.pi * 0.01**2)

    def current_density(x):
        return ufl.as_vector([0.0, 0.0, current_density_magnitude])

    # The gate fixture uses 1e-3, which is *below* the validated floor of 1 and
    # raises GaugeContaminationWarning: at that penalty the gradient null space
    # dominates A and B = curl(A) is round-off-corrupted.  Overridable here so
    # the scatter can be re-measured at a clean penalty — if the mechanism is
    # gauge contamination, the scatter must collapse at 1.0 on the same mesh.
    gauge_penalty = float(os.environ.get("MAG6_STEP4_GAUGE", "1e-3"))
    if comm.rank == 0:
        print(f"GAUGE_PENALTY {gauge_penalty:.6e}", flush=True)
    solver.solve(
        current_density=current_density, subdomain_ids=[1, 2], gauge_penalty=gauge_penalty
    )

    b_field = solver.compute_b_field()
    v_dg0 = fem.functionspace(mesh, ("DG", 0, (3,)))
    b_dg0 = fem.Function(v_dg0, name="B_dg0")
    b_dg0.interpolate(b_field)

    centerline_points = np.array(
        [[0.0, 0.0, z] for z in np.linspace(-0.03, 0.03, 9)], dtype=np.float64
    )

    values, claims = instrumented_eval(b_dg0, centerline_points, comm)
    mag = np.linalg.norm(values, axis=1)

    # Cross-check: the library path must reproduce the instrumented one exactly.
    lib_values, lib_valid = evaluate_vector_field_parallel(b_dg0, centerline_points, comm=comm)
    lib_mag = np.linalg.norm(lib_values, axis=1)

    # Second signal (step 4, second pass): the two evaluations above read the
    # *same unchanged* ``b_dg0`` at the *same* points inside one process, by two
    # algorithmically identical code paths (both take ``links[0]`` and both let
    # the highest-numbered claiming rank overwrite).  They must therefore agree
    # bitwise.  The first pass printed only the boolean and saw it go False at
    # ``-n 4``; print the magnitude here, and add a third call so a run-to-run
    # drift (successive calls keep moving) can be told from a one-off
    # instrumented-vs-library difference (call 2 and 3 agree, both differ from
    # call 1).
    lib2_values, _ = evaluate_vector_field_parallel(b_dg0, centerline_points, comm=comm)
    lib2_mag = np.linalg.norm(lib2_values, axis=1)

    # Third pass: repeat the *instrumented* evaluation so the two calls can be
    # compared by their claim sets, not just their values.  If call 1 and call 4
    # disagree the collision search itself is non-deterministic across identical
    # calls; if they agree (and both differ from the library calls) the
    # difference is between the two code paths, which are supposed to be
    # algorithmically identical.
    values_r, claims_r = instrumented_eval(b_dg0, centerline_points, comm)
    mag_r = np.linalg.norm(values_r, axis=1)

    # In-fixture control on the SAME solve: the mirror-symmetry metric.
    sample_clearance = max(0.75 * sampling_clearance_resolution, 0.004)
    safe_radius = phantom_radius - sample_clearance
    safe_half_height = (phantom_height / 2.0) - sample_clearance
    x_probe = np.array([0.35, 0.60, 0.85]) * safe_radius
    z_probe = np.array([-0.60, 0.0, 0.60]) * safe_half_height
    y_off = 0.15 * sample_clearance
    symmetry_points = np.array(
        [[sx * xv, y_off, zv] for zv in z_probe for xv in x_probe for sx in (1.0, -1.0)],
        dtype=np.float64,
    )
    sym_values, sym_claims = instrumented_eval(b_dg0, symmetry_points, comm)
    sym_mag = np.linalg.norm(sym_values, axis=1).reshape(-1, 2)
    sym_ref = np.maximum(np.maximum(sym_mag[:, 0], sym_mag[:, 1]), FIELD_SCALE_FLOOR)
    sym_max_rel = float(np.max(np.abs(sym_mag[:, 0] - sym_mag[:, 1]) / sym_ref))

    if comm.rank != 0:
        return

    print()
    print("--- centerline: per-point sampled |B| and ownership fingerprint ---")
    print(f"{'i':>2} {'z':>9} {'|B| used':>14} {'#rank':>5} {'win':>3} {'#cell':>5}  "
          f"chosen cell midpoint")
    multi = 0
    disagree = 0
    multicell = 0
    for i, pt in enumerate(centerline_points):
        cl = claims[i]
        winner = cl[-1][0] if cl else -1
        vals = [c[2] for c in cl]
        ncand = cl[-1][3] if cl else 0
        if ncand > 1:
            multicell += 1
        if len(cl) > 1:
            multi += 1
            spread = (max(vals) - min(vals)) / max(max(vals), FIELD_SCALE_FLOOR)
            if spread > 1e-12:
                disagree += 1
        mid = cl[-1][1] if cl else np.zeros(3)
        print(f"{i:>2} {pt[2]:>9.4f} {mag[i]:>14.6e} {len(cl):>5} {winner:>3} {ncand:>5}  "
              f"({mid[0]:+.9e}, {mid[1]:+.9e}, {mid[2]:+.9e})")

    print()
    print(f"CENTERLINE_MULTICLAIM points={multi}/{len(centerline_points)} "
          f"with_disagreeing_values={disagree}")
    print(f"CENTERLINE_MULTICELL points={multicell}/{len(centerline_points)} "
          f"(a point colliding with >1 cell on its own rank: the library takes "
          f"links[0], i.e. lowest local cell index)")
    print(f"LIB_AGREES_WITH_INSTRUMENTED = "
          f"{bool(np.allclose(mag, lib_mag, rtol=0, atol=0))} "
          f"(all_valid={bool(lib_valid.all())})")

    # --- second signal, quantified -------------------------------------------
    ref = np.maximum(np.maximum(np.abs(mag), np.abs(lib_mag)), FIELD_SCALE_FLOOR)
    rel_1v2 = np.abs(mag - lib_mag) / ref
    ref23 = np.maximum(np.maximum(np.abs(lib_mag), np.abs(lib2_mag)), FIELD_SCALE_FLOOR)
    rel_2v3 = np.abs(lib_mag - lib2_mag) / ref23
    print(f"LIB2_AGREES_WITH_LIB = "
          f"{bool(np.allclose(lib_mag, lib2_mag, rtol=0, atol=0))}")
    print(f"EVAL_REPEAT_MAXREL call1_vs_call2={float(np.max(rel_1v2)):.6e} "
          f"call2_vs_call3={float(np.max(rel_2v3)):.6e}")
    print("EVAL_REPEAT_PERPOINT i z |B|_call1 |B|_call2 |B|_call3 rel_1v2 rel_2v3")
    for i, pt in enumerate(centerline_points):
        print(f"EVAL_REPEAT {i:>2} {pt[2]:>9.4f} {mag[i]:.12e} {lib_mag[i]:.12e} "
              f"{lib2_mag[i]:.12e} {rel_1v2[i]:.3e} {rel_2v3[i]:.3e}")
    print(f"METRIC_FROM_CALL2 centerline_jump_ratio = {jump_ratio(lib_mag):.6f}")
    print(f"METRIC_FROM_CALL3 centerline_jump_ratio = {jump_ratio(lib2_mag):.6f}")
    print(f"INSTRUMENTED_REPEAT_AGREES = "
          f"{bool(np.allclose(mag, mag_r, rtol=0, atol=0))} "
          f"maxrel={float(np.max(np.abs(mag - mag_r) / ref)):.6e}")
    print(f"METRIC_FROM_CALL4 centerline_jump_ratio = {jump_ratio(mag_r):.6f}")
    print("--- claim sets, instrumented call 1 vs instrumented call 4 ---")
    for i in range(len(centerline_points)):
        c1 = [(r, f"{v:.12e}") for r, _m, v, _n in claims[i]]
        c4 = [(r, f"{v:.12e}") for r, _m, v, _n in claims_r[i]]
        flag = "SAME" if c1 == c4 else "DIFF"
        print(f"CLAIMS {i:>2} {flag} call1={c1} call4={c4}")

    jr = jump_ratio(mag)
    print()
    print(f"METRIC centerline_jump_ratio = {jr:.6f}  (gate bound {CENTERLINE_JUMP_RATIO_MAX})")
    print(f"CONTROL symmetry_max_rel_diff = {sym_max_rel:.6f}  (gate bound {SYMMETRY_REL_TOL})")

    sym_multi = sum(1 for c in sym_claims if len(c) > 1)
    sym_multicell = sum(1 for c in sym_claims if c and c[-1][3] > 1)
    print(f"SYMMETRY_MULTICLAIM points={sym_multi}/{len(symmetry_points)} "
          f"multicell={sym_multicell}/{len(symmetry_points)}")

    # Which point pair sets the jump ratio — the metric is a max over 8 diffs,
    # so a single rank-dependent point can move it on its own.
    diffs = np.abs(np.diff(mag))
    k = int(np.argmax(diffs))
    print(f"JUMP_ARGMAX between i={k} and i={k+1} "
          f"(|B| {mag[k]:.6e} -> {mag[k+1]:.6e}, diff {diffs[k]:.6e}, "
          f"max|B| {float(np.max(mag)):.6e})")
    print()
    print("--- centerline |B| vector, full precision (for cross-run diffing) ---")
    print("CENTERLINE_MAG " + " ".join(f"{v:.12e}" for v in mag))


if __name__ == "__main__":
    main()
