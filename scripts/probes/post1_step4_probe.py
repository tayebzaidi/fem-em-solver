"""`POST-1` step 4 probe: drop-set semantics on a *planar* interface.

Step 3 measured the guardrail's drop set against the `TH-8` sphere and found the
mean unmoved (1.009x) but both extrema living in the drop layer.  Its unresolved
confound is geometry: the sphere boundary is curved, so chordal error sits in the
very cell layer the semantics question is about.  This probe moves the question
onto the `POST-3` step-2 **two-slab** fixture, whose interface is a mesh plane and
therefore carries **zero** chordal error.

**The fixture as landed has no closed form**, and the §7 plan's instruction to
"import ... its piecewise closed form" cannot be followed literally: the
`POST-3` step-2 solve imposes the *σ_low* plane wave on all six faces, which the
module's own comment says is not the exact solution of the two-material problem
(there is a reflection at the interface).  Worse, that Dirichlet trace is
inconsistent in principle, not just approximately: on the ``y = 0`` and ``y = L``
faces it pins ``E_z(x) = e^{-j k_low x}`` all the way through slab 2, where no
piecewise solution can match it.

So this probe supplies the closed form the step needs, on the *same* mesh, tags
and material map, by making the Dirichlet trace self-consistent — the classic
normal-incidence half-space transmission problem:

    E = (0, 0, f(x)),   f'' + k(x)^2 f = 0,   f and f' continuous at x = L/2

    f1(x) = e^{-j k1 x} + R e^{-j k1 (2 xi - x)}          0 <= x <= xi
    f2(x) = T e^{-j k1 xi} e^{-j k2 (x - xi)}             xi <= x <= L

    R = (k1 - k2)/(k1 + k2),   T = 2 k1/(k1 + k2)

For ``E = (0,0,f(x))`` one has ``curl curl E = (0, 0, -f'')``, so the Helmholtz
equation above is exactly ``curl curl E - k^2 E = 0``; ``f`` continuous is
tangential-E continuity and ``f'`` continuous is tangential-H continuity at
uniform mu.  Hence the pair above is an **exact** solution of the piecewise-eps_c
curl-curl problem, and imposing it on all six faces makes it *the* solution.  The
probe checks that claim before using it, by measuring the global relative L2
error under refinement: a wrong closed form does not converge.

Slab 2 (tag 2, sigma = 1.4 S/m) is the scored region.  ``|f2|`` decays
monotonically in x, so its true maximum over the slab sits **at the interface** —
which makes the surviving-set max deficit closed-form predictable, per the plan.

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \
       PYTHONPATH=/workspace/src timeout 180 mpiexec -n 2 python3 \
       scripts/probes/post1_step4_probe.py'
"""

from __future__ import annotations

import time

import numpy as np
from mpi4py import MPI

from fem_em_solver.post.phantom_fields import (
    _interior_tagged_cells,
    _tagged_cells,
)

# One definition of the closed form, the trace and the solve: the gate module's.
from tests.post.test_drop_set_semantics_planar import (
    INTERFACE_X,
    N_COARSE,
    N_FINE,
    SIGMA_HIGH,
    SIGMA_LOW,
    TAG_HIGH,
    BOX_L,
    closed_form_magnitude,
    global_l2_error,
    pointwise_stats,
    solve_two_slab,
    transmission_coefficients,
)


def main() -> None:
    comm = MPI.COMM_WORLD
    rank0 = comm.rank == 0
    k1, k2, r, t = transmission_coefficients()
    if rank0:
        print("\n[POST-1 step 4 probe] two-slab planar interface")
        print(f"  k1 (sigma={SIGMA_LOW}) = {k1:.6e}   k2 (sigma={SIGMA_HIGH}) = {k2:.6e}")
        print(f"  R = {r:.6f}   T = {t:.6f}   |R| = {abs(r):.6f}  |T| = {abs(t):.6f}")
        print(f"  interface at x = {INTERFACE_X:.4f} m, box L = {BOX_L} m")
        print(
            f"  closed-form |E| at interface = {closed_form_magnitude(np.array([INTERFACE_X]))[0]:.6f}"
            f", at exit face = {closed_form_magnitude(np.array([BOX_L]))[0]:.6f}"
        )
        print(f"  slab-2 decay length 1/alpha2 = {-1.0/k2.imag:.6e} m")

    # Step A: is the closed form actually the solution?  Two meshes, O(h) expected.
    errs = {}
    for n in (N_COARSE, N_FINE):
        t0 = time.time()
        msh, cell_tags, fields = solve_two_slab(n)
        errs[n] = global_l2_error(msh, fields)
        ncells = comm.allreduce(
            msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
        )
        if rank0:
            print(
                f"  n = {n:2d}: {ncells:7d} cells, rel L2 vs closed form = "
                f"{errs[n]:.4%}  ({time.time() - t0:.1f} s)"
            )
        if n == N_FINE:
            fine = (msh, cell_tags, fields)
    if rank0:
        rate = np.log(errs[N_COARSE] / errs[N_FINE]) / np.log(2.0)
        print(f"  convergence rate in h: {rate:.4f}")

    # Step B: the three drop sets on the slab-2 tag, at the fine mesh.
    msh, cell_tags, fields = fine
    # The anchor is |E|, the *phasor magnitude*, so the sampled object must be
    # the complex phasor.  ``fields.e_real`` (what step 3 sampled on the sphere)
    # is ``np.real`` of it — a phase-0 snapshot, which on a propagating decaying
    # field crosses zero and is not |E| at all.
    field = fields.e_complex
    tagged = _tagged_cells(cell_tags, TAG_HIGH)
    interior = _interior_tagged_cells(msh, cell_tags, TAG_HIGH)
    drop = np.setdiff1d(tagged, interior).astype(np.int32)

    n_tagged = comm.allreduce(int(tagged.size), op=MPI.SUM)
    n_interior = comm.allreduce(int(interior.size), op=MPI.SUM)
    n_drop = comm.allreduce(int(drop.size), op=MPI.SUM)

    sets = (
        ("(a) prefer_interior=True ", interior),
        ("(b) full tagged set      ", tagged),
        ("(c) drop set alone       ", drop),
    )
    stats = {}
    for label, cells in sets:
        stats[label] = pointwise_stats(field, cells, comm)

    if rank0:
        print(
            f"\n  cell classes (global, owned): tagged {n_tagged}, interior "
            f"{n_interior}, drop {n_drop} ({n_drop / n_tagged:.2%} of the tag)"
        )
        for label, _ in sets:
            s = stats[label]
            print(
                f"  {label}: n = {int(s['count']):5d}  "
                f"mean rel err = {s['mean_rel_error']:.4%}  "
                f"max rel err = {s['max_rel_error']:.4%}  "
                f"|E| in [{s['min_mag']:.6f}, {s['max_mag']:.6f}]  "
                f"x_min = {s['min_x']:.6f}"
            )
        ea = stats["(a) prefer_interior=True "]["mean_rel_error"]
        eb = stats["(b) full tagged set      "]["mean_rel_error"]
        ec = stats["(c) drop set alone       "]["mean_rel_error"]
        print(f"  separation (c)/(a) in mean error: {ec / ea:.4f}x   (sphere: 1.009x)")
        print(f"  (a) vs (b): {ea:.4%} vs {eb:.4%}")

        # The predicted extremum deficit: the true max over the slab sits at the
        # interface, and the surviving set's nearest centroid sits x_a - xi past
        # it, so the closed form predicts the deficit before anything is asserted.
        xa = stats["(a) prefer_interior=True "]["min_x"]
        xb = stats["(b) full tagged set      "]["min_x"]
        pred_a = closed_form_magnitude(np.array([xa]))[0]
        pred_b = closed_form_magnitude(np.array([xb]))[0]
        entry = closed_form_magnitude(np.array([INTERFACE_X]))[0]
        print(
            f"  predicted max: closed form at x_a = {xa:.6f} -> {pred_a:.6f}; "
            f"at x_b = {xb:.6f} -> {pred_b:.6f}; at interface -> {entry:.6f}"
        )
        print(
            f"  measured max:  (a) {stats['(a) prefer_interior=True ']['max_mag']:.6f}"
            f"  (b) {stats['(b) full tagged set      ']['max_mag']:.6f}"
        )
        print(
            f"  max ratio (b)/(a) = "
            f"{stats['(b) full tagged set      ']['max_mag'] / stats['(a) prefer_interior=True ']['max_mag']:.4f}x"
            f"   predicted {pred_b / pred_a:.4f}x"
        )
        print(
            f"  full-set max vs closed-form entry-face value: "
            f"{abs(stats['(b) full tagged set      ']['max_mag'] - entry) / entry:.4%}"
        )


if __name__ == "__main__":
    main()
