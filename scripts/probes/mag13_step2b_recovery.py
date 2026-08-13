"""`MAG-13` step 2b: price higher-order B recovery on the solved rung.

PROJECT_PLAN §7 (`MAG-13` step 2b) scopes this as a *measurement only* step.
The step-2 profile established the mechanism behind the 5.65%: ``A`` is
lowest-order N1curl, so ``B = ∇ × A`` is **cell-wise constant**, and
``compute_b_field`` interpolates that constant into DG1 (``solvers.py:637``) —
a container that carries no gradient.  The measured consequences were a
log-log slope of -1.069 (relative error ∝ h/r) and a *staircase*: adjacent
radii returning ``|B|_num`` identical to all printed digits in eight groups.

This step prices the route the staircase surfaced: recover ``B`` continuously
by **L2-projecting ``curl A`` into CG1** (one mass solve, ``cg`` + ``gamg``
per ``post/current_divergence.py``'s pattern) beside the existing DG1
interpolation, and evaluate **both** recoveries on the recorded 45-radius
grid through ``evaluate_vector_field_parallel``.

Order of operations, deliberately:

1. **Fixture identity first**, enforced (exit nonzero on miss): cell count
   digit-identical to 1 097 873 and the DG1 ten-point relative L2 reproducing
   5.6494% to its printed digits.  The DG1 path's own recorded numbers are
   this step's declared negative control, so reproducing them *is* the
   identity check.
2. **Both recoveries on the same 45 radii**, same sampler, same points.
3. **The staircase test**: the eight recorded groups of adjacent radii must
   still return identical DG1 values (control), and the reading is whether
   the CG1 values inside those groups are *distinct*.

Gates (exit code is gated on these — all four are reproductions of numbers
already on record, never on the CG1 reading, which is a measurement and whose
every band is a finding per §7):

* ``GATE 1`` cell count == ``REF_CELLS`` exactly;
* ``GATE 2`` DG1 ten-point relative L2 reproduces ``REF_REL_L2_10``;
* ``GATE 3`` DG1 dense relL2 over the recorded metric span reproduces
  ``REF_DG1_DENSE_SPAN`` (4.7235%) and the near-wire/wall bands reproduce
  5.4939% / 2.3341%, each to printed digits;
* ``GATE 4`` the DG1 staircase reproduces: inside all eight recorded groups
  the DG1 ``|B|_num`` values agree to the five significant figures the record
  prints.

**Pre-registered read** (§7): CG1 relL2 < 5.00% on the dense grid says
recovery alone reaches the target without any new mesh; >= 5.00% still
prices the route.  Either band is reported, neither gates.

The verdict is decided on rank 0 and broadcast, so every rank exits with the
same code.

Run (real build, no complex mode)::

    docker compose exec -T fem-em-solver bash -lc \
      'cd /workspace && PYTHONPATH=/workspace/src timeout -k 30 590 mpiexec \
       -n 8 python3 scripts/probes/mag13_step2b_recovery.py'
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
import ufl
from mpi4py import MPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dolfinx import fem  # noqa: E402

from fem_em_solver.core.solvers import (  # noqa: E402
    MagnetostaticProblem,
    MagnetostaticSolver,
    exterior_dirichlet_bc,
)
from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402
from fem_em_solver.post.evaluation import (  # noqa: E402
    evaluate_vector_field_parallel,
)
from fem_em_solver.utils.analytical import (  # noqa: E402
    AnalyticalSolutions,
    ErrorMetrics,
)
from fem_em_solver.utils.constants import MU_0  # noqa: E402
from tests.validation.test_straight_wire import (  # noqa: E402
    CURRENT,
    DOMAIN_RADIUS,
    R_MAX_BC,
    R_MIN,
    WIRE_LENGTH,
    WIRE_RADIUS,
    _wire_potential_interp,
)

RESOLUTION_FINE = float(os.environ.get("MAG13_STEP2_RES", "0.00125"))

# On record: 20260811T200040Z (rung), 20260812T123255Z (re-gated profile).
# Cite, never recompute.
REF_CELLS = 1097873
REF_REL_L2_10 = 0.056494
REF_DG1_DENSE_SPAN = 0.047235  # 0.006 -> 0.024 m, n=37
REF_DG1_DENSE_FULL = 0.046500  # 0.006 -> 0.028 m, n=45
REF_DG1_NEAR = 0.054939
REF_DG1_WALL = 0.023341

# The step's pre-registered read, on the recorded metric span.
CG1_TARGET = 0.0500

# Dense grid: 45 radii, 0.5 mm apart — the profile step's grid, unchanged.
PROFILE_R_MIN = 0.006
PROFILE_R_MAX = 0.028
PROFILE_DR = 0.0005

# The eight staircase groups the profile step recorded: adjacent radii whose
# DG1 |B|_num agreed to all printed digits (five significant figures).
STAIRCASE_GROUPS = [
    (0.0070, 0.0075),
    (0.0080, 0.0085),
    (0.0105, 0.0110, 0.0115),
    (0.0120, 0.0125),
    (0.0145, 0.0150),
    (0.0160, 0.0165),
    (0.0175, 0.0180, 0.0185),
    (0.0190, 0.0195, 0.0200),
]

# Mass-matrix solve.  `gamg` per post/current_divergence.py's note: hypre's
# BoomerAMG setup aborts this image's MPI.  A mass matrix is far better
# conditioned than that module's Poisson operator, so the same rtol is cheap.
PROJECTION_OPTIONS: dict[str, object] = {
    "ksp_type": "cg",
    "pc_type": "gamg",
    "ksp_rtol": 1.0e-12,
    "ksp_atol": 1.0e-50,
    "ksp_max_it": 500,
}


def _solve_straight_wire_keep_solver(resolution, comm):
    """`tests/validation/test_straight_wire.py::_solve_straight_wire`, verbatim,
    returning the solver as well so ``curl A`` is reachable for the projection.

    Every constant is imported from the test module rather than restated, and
    GATES 1-3 reproduce the fixture's recorded cell count and errors, so a
    drift between this copy and the helper cannot pass silently.
    """
    mesh, cell_tags, facet_tags = MeshGenerator.straight_wire_domain(
        wire_length=WIRE_LENGTH,
        wire_radius=WIRE_RADIUS,
        domain_radius=DOMAIN_RADIUS,
        resolution=resolution,
        comm=comm,
    )

    problem = MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0)
    solver = MagnetostaticSolver(problem, degree=1)

    j_magnitude = CURRENT / (np.pi * WIRE_RADIUS**2)

    def current_density(x):
        return ufl.as_vector([0.0, 0.0, j_magnitude])

    bcs = [exterior_dirichlet_bc(solver.V, _wire_potential_interp)]
    solver.solve(current_density=current_density, subdomain_id=1, bc_functions=bcs)
    return mesh, solver, solver.compute_b_field()


def _project_curl_to_cg1(solver, comm):
    """L2-project ``curl A`` into vector CG1.  Returns (function, seconds, its)."""
    mesh = solver.A.function_space.mesh
    V = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    u = ufl.TrialFunction(V)
    v = ufl.TestFunction(V)
    a = ufl.inner(u, v) * ufl.dx
    rhs = ufl.inner(ufl.curl(solver.A), v) * ufl.dx

    from dolfinx.fem.petsc import LinearProblem  # local: needs a PETSc build

    comm.Barrier()
    t0 = time.perf_counter()
    problem = LinearProblem(a, rhs, bcs=[], petsc_options=dict(PROJECTION_OPTIONS))
    b_cg1 = problem.solve()
    comm.Barrier()
    dt = time.perf_counter() - t0
    return b_cg1, dt, int(problem.solver.getIterationNumber())


def _sample(field, points, comm):
    values, valid = evaluate_vector_field_parallel(field, points, comm=comm)
    return values, valid


def _bands(r_dense, b_num, b_ana):
    rel = np.abs((b_num - b_ana) / b_ana)
    out = {}
    for lo, hi, label in [
        (0.006, 0.010, "near-wire"),
        (0.010, 0.016, "mid"),
        (0.016, 0.024, "outer"),
        (0.024, 0.028, "wall"),
        (0.006, 0.024, "span"),
        (0.006, 0.028, "full"),
    ]:
        m = (r_dense >= lo - 1e-12) & (r_dense <= hi + 1e-12)
        out[label] = (
            int(m.sum()),
            ErrorMetrics.l2_relative_error(b_num[m], b_ana[m]),
            float(rel[m].mean()),
            float(rel[m].max()),
        )
    return out


def main() -> int:
    comm = MPI.COMM_WORLD
    rank0 = comm.rank == 0

    if rank0:
        print(
            f"[MAG-13 2b] re-solve h = {RESOLUTION_FINE} m at -n {comm.size}; "
            f"identity targets {REF_CELLS} cells / {REF_REL_L2_10:.4%} "
            f"ten-point relative L2 (DG1)",
            flush=True,
        )

    comm.Barrier()
    t0 = time.perf_counter()
    mesh, solver, b_dg1 = _solve_straight_wire_keep_solver(RESOLUTION_FINE, comm)
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    ncells = comm.allreduce(
        mesh.topology.index_map(mesh.topology.dim).size_local, op=MPI.SUM
    )
    ndofs = b_dg1.function_space.dofmap.index_map.size_global

    # --- 1. fixture identity: the DG1 ten-point relL2 ------------------------
    r10 = np.linspace(R_MIN, R_MAX_BC, 10)
    p10 = np.zeros((10, 3))
    p10[:, 0] = r10
    v10, valid10 = _sample(b_dg1, p10, comm)
    b10_num = np.linalg.norm(v10, axis=1)
    b10_ana = np.linalg.norm(
        AnalyticalSolutions.straight_wire_magnetic_field(p10, CURRENT), axis=1
    )
    rel_l2_10 = ErrorMetrics.l2_relative_error(b10_num, b10_ana)
    cells_ok = ncells == REF_CELLS
    l2_ok = f"{rel_l2_10:.4%}" == f"{REF_REL_L2_10:.4%}"

    if rank0:
        print(
            f"[MAG-13 2b] mesh+solve {t_solve:.1f} s at -n {comm.size}, "
            f"{ncells} cells / {ndofs} global DG1 dofs "
            f"({int(valid10.sum())}/10 identity points inside mesh)",
            flush=True,
        )
        print(
            f"[MAG-13 2b] IDENTITY cells: {ncells} vs {REF_CELLS} on record "
            f"-> {'PASS' if cells_ok else 'FAIL'}",
            flush=True,
        )
        print(
            f"[MAG-13 2b] IDENTITY DG1 relative L2 (10 pts): {rel_l2_10:.4%} vs "
            f"{REF_REL_L2_10:.4%} on record -> {'PASS' if l2_ok else 'FAIL'}",
            flush=True,
        )

    # --- 2. the CG1 recovery ------------------------------------------------
    b_cg1, t_proj, ksp_its = _project_curl_to_cg1(solver, comm)
    n_cg1 = b_cg1.function_space.dofmap.index_map.size_global * 3
    if rank0:
        print(
            f"[MAG-13 2b] CG1 L2 projection of curl A: {t_proj:.2f} s, "
            f"{ksp_its} CG iterations (cg+gamg, rtol 1e-12), "
            f"{n_cg1} global dofs",
            flush=True,
        )

    # --- 3. both recoveries on the recorded 45-radius grid -------------------
    n_profile = int(round((PROFILE_R_MAX - PROFILE_R_MIN) / PROFILE_DR)) + 1
    r_dense = PROFILE_R_MIN + PROFILE_DR * np.arange(n_profile)
    points = np.zeros((n_profile, 3))
    points[:, 0] = r_dense

    v_dg1, valid_dg1 = _sample(b_dg1, points, comm)
    v_cg1, valid_cg1 = _sample(b_cg1, points, comm)

    b_ana = np.linalg.norm(
        AnalyticalSolutions.straight_wire_magnetic_field(points, CURRENT), axis=1
    )
    n_dg1 = np.linalg.norm(v_dg1, axis=1)
    n_cg1_mag = np.linalg.norm(v_cg1, axis=1)

    if not rank0:
        # Matching receive for rank 0's verdict broadcast at the end of main().
        return int(comm.bcast(None, root=0))

    print(
        f"[MAG-13 2b] dense sample: {n_profile} radii "
        f"{PROFILE_R_MIN:.4f} -> {PROFILE_R_MAX:.4f} m, step "
        f"{PROFILE_DR * 1e3:.1f} mm; outside mesh: "
        f"DG1 {int((~valid_dg1).sum())}, CG1 {int((~valid_cg1).sum())}",
        flush=True,
    )

    s_dg1 = (n_dg1 - b_ana) / b_ana
    s_cg1 = (n_cg1_mag - b_ana) / b_ana
    print("    r [m]     |B|_DG1      |B|_CG1      |B|_ana      DG1      CG1")
    for i in range(n_profile):
        print(
            f"    {r_dense[i]:.4f}  {n_dg1[i]:.4e}  {n_cg1_mag[i]:.4e}  "
            f"{b_ana[i]:.4e}  {s_dg1[i]:+7.2%}  {s_cg1[i]:+7.2%}",
            flush=True,
        )

    # --- 4. band tables, both recoveries ------------------------------------
    bands_dg1 = _bands(r_dense, n_dg1, b_ana)
    bands_cg1 = _bands(r_dense, n_cg1_mag, b_ana)
    print(
        "[MAG-13 2b] error by radial band (relL2 / mean|rel| / max|rel|), "
        "DG1 record vs CG1 recovery:",
        flush=True,
    )
    labels = {
        "near-wire": "near-wire  2.0a - 3.3a",
        "mid": "mid        3.3a - 5.3a",
        "outer": "outer      5.3a - 8.0a (to 0.8R)",
        "wall": "wall band  0.8R - 0.93R",
        "span": "recorded metric span",
        "full": "full dense span",
    }
    for key, label in labels.items():
        nd, l2d, md, xd = bands_dg1[key]
        _, l2c, mc, xc = bands_cg1[key]
        print(
            f"    {label:<34s} n={nd:2d}  DG1 {l2d:.4%}/{md:.4%}/{xd:.4%}   "
            f"CG1 {l2c:.4%}/{mc:.4%}/{xc:.4%}   "
            f"delta relL2 {(l2c - l2d) * 100:+.4f} pp",
            flush=True,
        )

    # --- 5. does the staircase break? ---------------------------------------
    def _sig5(x):
        return f"{x:.5g}"

    print(
        "[MAG-13 2b] STAIRCASE: the eight recorded groups of adjacent radii "
        "(DG1 identical to 5 sig figs on record); CG1 must differ if the "
        "recovery carries a gradient:",
        flush=True,
    )
    dg1_flat_all = True
    cg1_distinct_groups = 0
    for group in STAIRCASE_GROUPS:
        idx = [int(np.argmin(np.abs(r_dense - rc))) for rc in group]
        dg1_vals = [_sig5(n_dg1[i]) for i in idx]
        cg1_vals = [_sig5(n_cg1_mag[i]) for i in idx]
        dg1_flat = len(set(dg1_vals)) == 1
        cg1_distinct = len(set(cg1_vals)) == len(cg1_vals)
        dg1_flat_all = dg1_flat_all and dg1_flat
        cg1_distinct_groups += int(cg1_distinct)
        rs = "/".join(f"{rc:.4f}" for rc in group)
        print(
            f"    r={rs:<20s} DG1 {'/'.join(dg1_vals)} -> "
            f"{'flat' if dg1_flat else 'VARIES'}; CG1 {'/'.join(cg1_vals)} -> "
            f"{'distinct' if cg1_distinct else 'not distinct'}",
            flush=True,
        )
    print(
        f"[MAG-13 2b] staircase: DG1 flat in "
        f"{'all 8' if dg1_flat_all else 'NOT all'} groups (control); CG1 "
        f"distinct in {cg1_distinct_groups}/8 groups (reading)",
        flush=True,
    )

    # --- 6. the pre-registered read -----------------------------------------
    cg1_span = bands_cg1["span"][1]
    cg1_full = bands_cg1["full"][1]
    print(
        f"[MAG-13 2b] READING (pre-registered, never gated): CG1 relL2 over "
        f"the recorded metric span {cg1_span:.4%} vs DG1 "
        f"{bands_dg1['span'][1]:.4%} and the < {CG1_TARGET:.2%} target -> "
        f"{'BELOW target' if cg1_span < CG1_TARGET else 'AT/ABOVE target'}; "
        f"full dense span CG1 {cg1_full:.4%} vs DG1 "
        f"{bands_dg1['full'][1]:.4%}",
        flush=True,
    )
    print(
        f"[MAG-13 2b] provenance: rung h = {RESOLUTION_FINE} m, current "
        f"{CURRENT} A, wire radius {WIRE_RADIUS} m; real build, no complex "
        f"mode; projection {t_proj:.2f} s beside a {t_solve:.1f} s mesh+solve",
        flush=True,
    )

    # --- 7. gates ------------------------------------------------------------
    span_ok = f"{bands_dg1['span'][1]:.4%}" == f"{REF_DG1_DENSE_SPAN:.4%}"
    near_ok = f"{bands_dg1['near-wire'][1]:.4%}" == f"{REF_DG1_NEAR:.4%}"
    wall_ok = f"{bands_dg1['wall'][1]:.4%}" == f"{REF_DG1_WALL:.4%}"
    dense_ok = span_ok and near_ok and wall_ok
    gates = [
        ("GATE 1 fixture cells", cells_ok, f"{ncells} vs {REF_CELLS} on record"),
        (
            "GATE 2 DG1 relL2 (10 pt)",
            l2_ok,
            f"{rel_l2_10:.4%} vs {REF_REL_L2_10:.4%} on record",
        ),
        (
            "GATE 3 DG1 dense bands",
            dense_ok,
            f"span {bands_dg1['span'][1]:.4%} vs {REF_DG1_DENSE_SPAN:.4%} "
            f"-> {'PASS' if span_ok else 'FAIL'}; near-wire "
            f"{bands_dg1['near-wire'][1]:.4%} vs {REF_DG1_NEAR:.4%} "
            f"-> {'PASS' if near_ok else 'FAIL'}; wall "
            f"{bands_dg1['wall'][1]:.4%} vs {REF_DG1_WALL:.4%} "
            f"-> {'PASS' if wall_ok else 'FAIL'}",
        ),
        (
            "GATE 4 DG1 staircase",
            dg1_flat_all,
            # The failure path must not print the passing claim (§7 nit,
            # 2026-08-12 18:00 review): at a rung other than the recorded one
            # the DG1 values inside these groups genuinely vary, and the old
            # static string said "flat" while the gate read FAIL.
            "DG1 |B| flat to 5 sig figs inside all eight recorded groups"
            if dg1_flat_all
            else "DG1 |B| VARIES to 5 sig figs inside at least one of the "
            "eight recorded groups (see the per-group lines above)",
        ),
    ]
    print("[MAG-13 2b] GATES (exit code is gated on these):", flush=True)
    for label, ok, detail in gates:
        print(f"    {label:<26s} {'PASS' if ok else 'FAIL'}  ({detail})", flush=True)
    n_failed = sum(1 for _, ok, _ in gates if not ok)
    code = 0 if n_failed == 0 else 1
    print(
        f"[MAG-13 2b] OVERALL: {len(gates) - n_failed}/{len(gates)} gates pass "
        f"-> exit {code}",
        flush=True,
    )
    return int(comm.bcast(code, root=0))


if __name__ == "__main__":
    raise SystemExit(main())
