"""`MAG-20` step 1: how much does the two-rung sampled fit move under `n_points`?

`test_straight_wire.py::TestStraightWire::test_straight_wire_convergence` gates
a **two-rung** ([0.004, 0.0025]), **8-point** *sampled* log-log fit on the
two-sided band ``[RATE_MIN, RATE_MAX] = [0.7, 1.5]``. It is green today at
**0.7900** -- but `MAG-19` step 1 measured that same sampled statistic swinging
34% of its own value under `n_points` on this fixture family (`OPS-18` step 3
attempt 5: 15.8028% / 12.7485% / 11.4984% at 8 / 10 / 20 on 0.7.2, and the 0.11
row 16.6033% / 15.3848% / 13.6986% is a live control in the module), so a fit
green at 0.7900 sits ~0.09 above the lower edge of a band whose instrument is
known to move by tens of percent. Whether the band is *validated* or *latently
red* is a measurement, and this probe is it.

Method: solve each of the test's own two rungs **once**, then re-sample the same
solved field at ``n_points`` in {8, 10, 20} over the test's own radial window
(``R_MIN`` -> ``R_MAX``, the 0.4 R default -- **not** ``R_MAX_BC``; the module's
`NPOINTS_CONTROL_BY_VERSION` row is the 0.8 R sampler and is a different
statistic) and fit the two-rung rate at each count. One solve per rung means any
difference between the rows is the sampler and nothing else.

Everything is **imported** from the module that owns it (`ANS-1`), never
restated: the solve is `test_straight_wire._solve_straight_wire`, the sampler is
`_sample_radial`, the fit is `test_convergence.fit_convergence_rate`, and the
band is that module's `RATE_MIN` / `RATE_MAX`. No assertion: this is a
measurement, and what it licenses is the pre-stated decision rule in
PROJECT_PLAN.md's `MAG-20` step 1 entry -- any crossing of *either* edge of
[0.7, 1.5] anywhere in the sweep retires the two-sided band under the `MAG-19`
ruling-(i) pattern; stability inside the band at every count validates it.

    mpiexec -n 2 python3 -u tests/validation/probe_straight_wire_convergence_npoints.py
"""

import itertools
import os
import sys
import time

import numpy as np
from mpi4py import MPI

from fem_em_solver.utils.analytical import ErrorMetrics
from tests.validation.test_convergence import (
    RATE_MAX,
    RATE_MIN,
    fit_convergence_rate,
)
from tests.validation.test_straight_wire import (
    R_MAX,
    R_MIN,
    _sample_radial,
    _solve_straight_wire,
)

#: The gated test's own two rungs, verbatim from its `resolutions` list.
LADDER = [float(h) for h in os.environ.get("PROBE_H", "0.004,0.0025").split(",")]

#: The sweep. 8 is what the gate uses; 10 and 20 are the counts `OPS-18` step 3
#: attempt 5 and the module's live control already exercise, so the three rows
#: are comparable with everything already recorded on this fixture family.
NPOINTS = [int(n) for n in os.environ.get("PROBE_NPOINTS", "8,10,20").split(",")]

#: The gate's own reading on `main` at n_points = 8, from `MAG-19` step 2 run
#: (3) (`20260826T020739Z_MAG-19-step2-mag18.log`): the residual this chunk
#: disposes of. Reproducing it is the probe's negative control on the import.
GATE_RATE_RECORD_8 = 0.7900
GATE_RATE_RECORD_BAND = 5e-3


def main():
    comm = MPI.COMM_WORLD
    rungs = sorted(LADDER, reverse=True)

    if comm.rank == 0:
        import dolfinx
        import gmsh

        print(f"  ranks {comm.size}  rungs {rungs}  n_points {NPOINTS}")
        print(f"  dolfinx {dolfinx.__version__}  gmsh {gmsh.__version__}")
        print(f"  gate band [{RATE_MIN}, {RATE_MAX}]  window r in "
              f"[{R_MIN}, {R_MAX}] (the test's default, 0.4 R)")
        sys.stdout.flush()

    # errors[n_points] -> list over rungs, in the same order as `rungs`.
    errors = {n: [] for n in NPOINTS}
    cells = []
    for res in rungs:
        t0 = time.perf_counter()
        mesh, b_field = _solve_straight_wire(res, comm)
        n_cells = mesh.topology.index_map(mesh.topology.dim).size_global
        cells.append(n_cells)
        for n in NPOINTS:
            _, b_num_mag, b_ana_mag, _ = _sample_radial(b_field, n, comm)
            errors[n].append(ErrorMetrics.l2_relative_error(b_num_mag, b_ana_mag))
        elapsed = time.perf_counter() - t0
        if comm.rank == 0:
            row = "  ".join(f"n={n}: {errors[n][-1]:.6%}" for n in NPOINTS)
            print(f"  h={res:.4f}  cells {n_cells:>7}  {row}  ({elapsed:.1f} s)")
            sys.stdout.flush()

    if comm.rank != 0:
        return

    print(f"\n  MAG-20 step 1 -- {len(rungs)}x{len(NPOINTS)} sampled-error table "
          f"(one solve per rung):")
    header = "  ".join(f"{'n=' + str(n):>13}" for n in NPOINTS)
    print(f"  {'h':>8}  {'cells':>8}  {header}")
    for i, res in enumerate(rungs):
        row = "  ".join(f"{errors[n][i]:>13.6%}" for n in NPOINTS)
        print(f"  {res:>8.4f}  {cells[i]:>8}  {row}")

    print("\n  Sampler swing at fixed h (max/min - 1 across n_points):")
    for i, res in enumerate(rungs):
        vals = [errors[n][i] for n in NPOINTS]
        print(f"    h={res:.4f}  {min(vals):.6%} .. {max(vals):.6%}  "
              f"swing {max(vals) / min(vals) - 1:+.2%}")

    print("\n  Fitted two-rung rate per n_points (the gate's own statistic):")
    fits = {}
    hh = np.array(rungs)
    for n in NPOINTS:
        p = fit_convergence_rate(hh, np.array(errors[n]))
        fits[n] = p
        verdict = "in band" if RATE_MIN < p < RATE_MAX else "OUT OF BAND"
        margin_lo = p - RATE_MIN
        margin_hi = RATE_MAX - p
        print(f"    n_points {n:>3}: rate {p:.4f}  {verdict:>11}  "
              f"(margin to {RATE_MIN}: {margin_lo:+.4f}; to {RATE_MAX}: {margin_hi:+.4f})")

    crossed = [n for n in NPOINTS if not (RATE_MIN < fits[n] < RATE_MAX)]
    spread = max(fits.values()) - min(fits.values())
    print("\n  Decision-rule input (PROJECT_PLAN MAG-20 step 1):")
    print(f"    counts crossing an edge of [{RATE_MIN}, {RATE_MAX}]: "
          f"{crossed if crossed else 'none'}")
    print(f"    rate spread over the sweep: {min(fits.values()):.4f} .. "
          f"{max(fits.values()):.4f}  (absolute {spread:.4f}, "
          f"relative {spread / min(fits.values()):+.2%})")
    print(f"    RULE: any crossing => retire the two-sided band under the "
          f"MAG-19 ruling-(i) pattern; none => the band is validated.")
    print(f"    => {'RETIRE' if crossed else 'VALIDATED'}")

    print("\n  Pairwise-rate check (identical to the fit at two rungs; a third "
          "rung would separate them):")
    for a, b in itertools.combinations(range(len(rungs)), 2):
        for n in NPOINTS:
            p = float(
                np.log(errors[n][a] / errors[n][b])
                / np.log(rungs[a] / rungs[b])
            )
            print(f"    {rungs[a]:.4f}->{rungs[b]:.4f}  n={n:<3} {p:.4f}")

    print("\n  Negative control -- the gate's recorded reading on `main`:")
    dev = abs(fits[8] - GATE_RATE_RECORD_8)
    print(f"    n_points 8 fit {fits[8]:.4f} vs MAG-19 step 2 record "
          f"{GATE_RATE_RECORD_8:.4f}  |delta| {dev:.4f}  "
          f"{'ok' if dev < GATE_RATE_RECORD_BAND else 'DOES NOT REPRODUCE'}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
