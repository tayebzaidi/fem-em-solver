"""`POST-1` step 4b probe: re-score the sphere drop-set table on ``|E|``.

Step 3 measured the three drop-set statistics on the `TH-8` sphere and read two
conclusions off them: the mean is unmoved by the guardrail (1.009x) and both
extrema of the tag live in the drop layer (range ratio 1.334x).  Step 4 then
found that the sampled object in that measurement was ``fields.e_real`` — the
phase-0 snapshot ``np.real`` of the phasor — where the anchor
``3/(eps_r + 2) E0 = 0.0375`` is a **magnitude**.  On step 4's propagating,
decaying planar field the same substitution scored 61.8232% against a solve
whose global L2 error is 2.1568%.

On the sphere the two are expected to nearly agree — the interior field is
nearly in phase — but "expected" is not "measured", and this probe measures it:
the identical three-set table, once on ``e_real`` (reproducing the step-3
numbers) and once on ``e_complex``, off **one** solve so the comparison is a
change of quantity and nothing else.

Prints, per quantity: the three means and their errors against the closed form,
the (c)/(a) mean-error ratio, the per-set min/max, and the full/surviving range
ratio.  The step-3 gate's two bands — ``SURVIVING_ERROR_BAND`` (3.75%, 4.75%)
and ``MIN_RANGE_RATIO`` 1.2 — are printed beside the ``|E|`` values so the new
gate's band can be read off a measurement rather than fitted after a failure.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src:/workspace timeout 180 \\
       mpiexec -n 2 python3 scripts/probes/post1_step4b_probe.py'
"""

from __future__ import annotations

import time

import numpy as np
from mpi4py import MPI

from fem_em_solver.post.phantom_fields import (
    _cell_centroids,
    _evaluate_on_cells,
    _interior_tagged_cells,
    _tagged_cells,
    compute_tagged_vector_magnitude_stats,
)

from tests.post.test_drop_set_semantics_sphere import (
    MIN_RANGE_RATIO,
    RESOLUTION_FAR,
    RESOLUTION_SPHERE,
    SURVIVING_ERROR_BAND,
    _magnitude_stats_on_cells,
    _solve_sphere_fields,
)
from tests.validation.test_dielectric_sphere import (
    EPSILON_R_SPHERE,
    SPHERE_TAG,
    interior_field_closed_form,
)


def _table(field, cell_tags, drop, comm, expected):
    surviving = compute_tagged_vector_magnitude_stats(
        field, cell_tags, SPHERE_TAG, comm=comm, prefer_interior_samples=True
    )
    full = compute_tagged_vector_magnitude_stats(
        field, cell_tags, SPHERE_TAG, comm=comm, prefer_interior_samples=False
    )
    dropped = _magnitude_stats_on_cells(field, drop, comm)
    rows = [
        ("(a) prefer_interior=True ", surviving),
        ("(b) full tagged set      ", full),
        ("(c) drop set alone       ", dropped),
    ]
    for _label, stats in rows:
        stats["error"] = abs(stats["mean"] - expected) / expected
    return dict(rows)


def main() -> None:
    comm = MPI.COMM_WORLD
    expected = interior_field_closed_form(EPSILON_R_SPHERE)

    t0 = time.time()
    msh, cell_tags, fields = _solve_sphere_fields(RESOLUTION_SPHERE, RESOLUTION_FAR)
    t_solve = time.time() - t0

    tagged = _tagged_cells(cell_tags, SPHERE_TAG)
    interior = _interior_tagged_cells(msh, cell_tags, SPHERE_TAG)
    drop = np.setdiff1d(tagged, interior).astype(np.int32)

    n_tagged = comm.allreduce(int(tagged.size), op=MPI.SUM)
    n_interior = comm.allreduce(int(interior.size), op=MPI.SUM)
    n_drop = comm.allreduce(int(drop.size), op=MPI.SUM)

    tables = {
        "Re E  (fields.e_real, step 3's quantity)": _table(
            fields.e_real, cell_tags, drop, comm, expected
        ),
        "|E|   (fields.e_complex, the anchored one)": _table(
            fields.e_complex, cell_tags, drop, comm, expected
        ),
    }

    # Why the two tables can coincide: sigma = 0 everywhere and the exact
    # exterior Dirichlet data is real, so nothing in the operator or the data
    # carries a phase and the solved phasor should be real to solver tolerance.
    # Measured, not assumed.
    points = _cell_centroids(msh, tagged)
    values, _p, _vc, _iv = _evaluate_on_cells(fields.e_complex, points, tagged)
    if values.shape[0] > 0:
        local_imag = float(np.max(np.abs(np.imag(values))))
        local_mag = float(np.max(np.abs(np.linalg.norm(values, axis=1))))
    else:
        local_imag = local_mag = 0.0
    imag_max = comm.allreduce(local_imag, op=MPI.MAX)
    mag_max = comm.allreduce(local_mag, op=MPI.MAX)

    if comm.rank != 0:
        return

    print(
        f"\n[POST-1 step 4b probe] TH-8 sphere, h_sphere = {RESOLUTION_SPHERE}, "
        f"eps_r = {EPSILON_R_SPHERE}, closed form = {expected:.6f}"
    )
    print(f"  solve {t_solve:.2f} s; ranks {comm.size}")
    print(
        f"  cell classes (global, owned): tagged {n_tagged}, interior "
        f"{n_interior}, drop {n_drop} ({n_drop / n_tagged:.2%} of the tag)"
    )
    for quantity, rows in tables.items():
        print(f"\n  --- scored on {quantity} ---")
        for label, s in rows.items():
            print(
                f"  {label}: n = {int(s['count']):5d}  "
                f"mean = {s['mean']:.6f} ({s['error']:.4%})  "
                f"min = {s['min']:.6f}  max = {s['max']:.6f}"
            )
        a, b, c = rows.values()
        range_a = a["max"] - a["min"]
        range_b = b["max"] - b["min"]
        print(
            f"  separation (c)/(a) in mean error: {c['error'] / a['error']:.4f}x"
        )
        print(
            f"  spread: surviving {range_a:.6f}, full {range_b:.6f} "
            f"-> ratio {range_b / range_a:.4f}x  (step-3 floor {MIN_RANGE_RATIO})"
        )
        print(
            f"  extrema in the drop layer? max {b['max'] > a['max']}, "
            f"min {b['min'] < a['min']}"
        )
        lo, hi = SURVIVING_ERROR_BAND
        print(
            f"  (a) error {a['error']:.4%} vs step-3 band "
            f"({lo:.2%}, {hi:.2%}): inside = {lo < a['error'] < hi}"
        )

    print("\n  --- why: imaginary content of the phasor over the tag ---")
    print(
        f"  max|Im E| = {imag_max:.6e}, max|E| = {mag_max:.6e} "
        f"-> ratio {imag_max / mag_max:.3e}"
    )
    for key in ("count", "mean", "min", "max"):
        re_row = tables["Re E  (fields.e_real, step 3's quantity)"]
        cx_row = tables["|E|   (fields.e_complex, the anchored one)"]
        for label in re_row:
            v_re, v_cx = re_row[label][key], cx_row[label][key]
            denom = abs(v_re) if v_re else 1.0
            print(
                f"  {label} {key:5s}: Re E {v_re:.12g}  |E| {v_cx:.12g}  "
                f"rel diff {abs(v_cx - v_re) / denom:.3e}"
            )


if __name__ == "__main__":
    main()
