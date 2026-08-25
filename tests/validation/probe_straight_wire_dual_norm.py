"""`MAG-19` step 1: run both norms on the *same* four straight-wire solves.

The gate `test_convergence.py::TestConvergence::test_h_refinement_straight_wire`
is red on `main` on the 0.11 image -- fitted rate **1.9038** against the
`MAG-13` band [0.7, 1.5], because the h = 0.0018 rung's sampled 10-point error
collapsed 9.26% -> 4.4605% while the two coarser rungs moved < 3 pp
(known-issues 2026-08-25, log `20260825T141636Z_EX-30-root-mag6-gate-probe`).
Two readings fit, and they are discriminable by measurement:

  (a) *anomalous rung* -- the h = 0.0018 rung's **sampled** reading is the
      outlier, exactly the way `MAG-13` once excluded h = 0.0035 (cell-wise
      constant curl(A) means the 10 point samples read whichever cell contains
      them, so each resolution carries O(h) sampling noise).
  (b) *wrong instrument* -- the sampled norm is unstable at every h on this
      image, and the duty belongs to the sampler-independent `MAG-18` `E_Omega`
      annulus norm, which is green on 0.11 at rate 1.6854.

The discriminator is to compute both norms **on the same solved field**, over a
ladder with one added interpolating rung at h = 0.0030, and read the *pairwise*
rates: reading (a) predicts the sampled pairwise rates are consistent on every
pair that does not involve h = 0.0018 while `E_Omega` is consistent across all
pairs; reading (b) predicts the sampled rates are scattered even on pairs that
avoid 0.0018. The decision rule is pre-stated in PROJECT_PLAN.md's `MAG-19`
entry and is applied to this probe's table, not chosen after seeing it.

Both norms are **imported** from the modules that own them (`ANS-1`), never
restated: the sampled norm is the gate's own `solve_h_refinement`, and
`E_Omega` is `test_straight_wire._domain_l2_error`. One solve per rung feeds
both, so any difference between the two columns is the instrument and nothing
else. No assertion: this is a measurement, and what it licenses is the §7
decision rule's.

    mpiexec -n 2 python3 -u tests/validation/probe_straight_wire_dual_norm.py
"""

import itertools
import os
import sys
import time

import numpy as np
from mpi4py import MPI

from tests.validation.test_convergence import (
    RATE_MAX,
    RATE_MIN,
    fit_convergence_rate,
    solve_h_refinement,
)
from tests.validation.test_straight_wire import (
    E_OMEGA_H0025_RECORD,
    E_OMEGA_RATE_MIN,
    E_OMEGA_RECORD_BAND,
    _domain_l2_error,
)

#: The gate's three rungs plus the added interpolating rung. 0.0030 sits
#: between 0.004 (38.7 k cells) and 0.0025 (147.2 k) and is the candidate
#: replacement for 0.0018 under reading (a): it is priced here so a
#: re-chosen sequence is never an unmeasured guess.
LADDER = [float(h) for h in os.environ.get("PROBE_H", "0.004,0.003,0.0025,0.0018").split(",")]

#: The red being disposed of, reproduced before it is disposed of: the sampled
#: 10-point errors of the three original rungs on 0.11, from the log the
#: known-issues entry quotes (`20260825T141636Z`, `-n 2`).
SAMPLED_RECORD_011 = {
    0.004: 0.21841667267163878,
    0.0025: 0.15384842035994292,
    0.0018: 0.04460534278989355,
}

#: Relative band for the reproduction check above. A direct solve on the same
#: image at the same width should reproduce to the solve's own cross-run floor
#: (~1e-7, MAG-18); 1e-4 is the record convention used elsewhere in this suite.
REPRODUCTION_BAND = 1e-4


def _pairwise_rate(h_a, e_a, h_b, e_b):
    """Two-point rate p in error ~ C h^p, from a single pair of rungs."""
    return float(np.log(e_a / e_b) / np.log(h_a / h_b))


def main():
    comm = MPI.COMM_WORLD
    rungs = sorted(LADDER, reverse=True)

    if comm.rank == 0:
        import dolfinx
        import gmsh

        print(f"  ranks {comm.size}  rungs {rungs}")
        print(f"  dolfinx {dolfinx.__version__}  gmsh {gmsh.__version__}")
        print(f"  gate band [{RATE_MIN}, {RATE_MAX}]")
        sys.stdout.flush()

    rows = []
    for res in rungs:
        t0 = time.perf_counter()
        result = solve_h_refinement(res, comm)
        e_sampled = result["rel_error"]
        # Same mesh, same solved B: the only thing that changes is the norm.
        e_omega = _domain_l2_error(result["mesh"], result["b_field"])
        elapsed = time.perf_counter() - t0

        rows.append(
            {
                "h": res,
                "cells": result["n_cells"],
                "sampled": e_sampled,
                "e_omega": e_omega,
                "seconds": elapsed,
            }
        )
        if comm.rank == 0:
            rec = SAMPLED_RECORD_011.get(res)
            rec_txt = (
                f"  (record {rec:.6%}, {(e_sampled - rec) / rec:+.3e} rel)"
                if rec is not None
                else "  (no record -- added rung)"
            )
            print(
                f"  h={res:.4f}  cells {result['n_cells']:>7}  "
                f"sampled {e_sampled:.6%}  E_Omega {e_omega:.6%}  "
                f"{elapsed:.1f} s{rec_txt}"
            )
            sys.stdout.flush()

    if comm.rank != 0:
        return

    print("\n  MAG-19 step 1 -- 4x2 error table (one solve per rung):")
    print(f"  {'h':>8}  {'cells':>8}  {'sampled 10-pt':>14}  {'E_Omega':>12}")
    for r in rows:
        print(
            f"  {r['h']:>8.4f}  {r['cells']:>8}  {r['sampled']:>13.6%}  "
            f"{r['e_omega']:>11.6%}"
        )

    print("\n  Pairwise rates (in-band = inside the gate's [0.7, 1.5]):")
    print(f"  {'pair':>18}  {'sampled':>9} {'':>4}  {'E_Omega':>9} {'':>4}")
    verdicts = {"sampled": [], "e_omega": []}
    for a, b in itertools.combinations(rows, 2):
        line = f"  {a['h']:.4f}->{b['h']:.4f}"
        cells = []
        for key in ("sampled", "e_omega"):
            p = _pairwise_rate(a["h"], a[key], b["h"], b[key])
            in_band = RATE_MIN < p < RATE_MAX
            verdicts[key].append(
                {"pair": (a["h"], b["h"]), "rate": p, "in_band": in_band}
            )
            cells.append(f"{p:>9.4f} {'ok ' if in_band else 'OUT'}")
        print(f"{line:>18}  " + "  ".join(cells))

    print("\n  Decision-rule inputs (PROJECT_PLAN MAG-19 step 1):")
    for key, label in (("sampled", "sampled 10-pt"), ("e_omega", "E_Omega")):
        avoiding = [v for v in verdicts[key] if 0.0018 not in v["pair"]]
        involving = [v for v in verdicts[key] if 0.0018 in v["pair"]]
        print(
            f"    {label:>13}: pairs avoiding h=0.0018 in band "
            f"{sum(v['in_band'] for v in avoiding)}/{len(avoiding)}; "
            f"pairs involving it in band "
            f"{sum(v['in_band'] for v in involving)}/{len(involving)}; "
            f"all pairs in band {sum(v['in_band'] for v in verdicts[key])}/"
            f"{len(verdicts[key])}"
        )

    # Least-squares fits, for comparison with the two live gates: the sampled
    # norm's three-rung fit is the red itself (1.9038 on record), and the
    # E_Omega three-rung fit is the MAG-18 negative control -- it must
    # reproduce 1.6854 through the imported machinery, or the import is wrong
    # rather than the physics.
    print("\n  Least-squares fits (the gates' own statistic):")
    by_h = {r["h"]: r for r in rows}
    original = [h for h in (0.004, 0.0025, 0.0018) if h in by_h]
    no_finest = [r["h"] for r in rows if r["h"] != 0.0018]
    for label, hs in (
        ("original 3 rungs", original),
        ("all rungs", [r["h"] for r in rows]),
        ("without h=0.0018", no_finest),
    ):
        if len(hs) < 3:
            continue
        hh = np.array(sorted(hs, reverse=True))
        fits = {
            key: fit_convergence_rate(hh, np.array([by_h[h][key] for h in hh]))
            for key in ("sampled", "e_omega")
        }
        print(
            f"    {label:>18} ({len(hs)}): sampled {fits['sampled']:.4f} "
            f"({'in' if RATE_MIN < fits['sampled'] < RATE_MAX else 'OUT of'} "
            f"[{RATE_MIN}, {RATE_MAX}])   "
            f"E_Omega {fits['e_omega']:.4f} "
            f"({'meets' if fits['e_omega'] >= E_OMEGA_RATE_MIN else 'BELOW'} "
            f"its own one-sided >= {E_OMEGA_RATE_MIN})"
        )

    print("\n  Reproduction of the red (before it is disposed of):")
    reproduced = True
    for r in rows:
        rec = SAMPLED_RECORD_011.get(r["h"])
        if rec is None:
            continue
        dev = abs(r["sampled"] - rec) / rec
        ok = dev < REPRODUCTION_BAND
        reproduced &= ok
        print(
            f"    h={r['h']:.4f}  {r['sampled']:.6%} vs record {rec:.6%}  "
            f"{dev:.3e} rel  {'ok' if ok else 'DOES NOT REPRODUCE'}"
        )
    print(f"    all three original rungs reproduce: {reproduced}")

    # The other half of the negative control: E_Omega's own version-tagged
    # record on the h = 0.0025 rung, reached here through the imported
    # `_domain_l2_error` rather than through its owning test.
    if 0.0025 in by_h:
        got = by_h[0.0025]["e_omega"]
        dev = abs(got - E_OMEGA_H0025_RECORD) / E_OMEGA_H0025_RECORD
        print(
            f"    E_Omega h=0.0025 {got:.10e} vs MAG-18 record "
            f"{E_OMEGA_H0025_RECORD:.10e}  {dev:.3e} rel  "
            f"{'ok' if dev < E_OMEGA_RECORD_BAND else 'DOES NOT REPRODUCE'}"
        )

    print(f"\n  total {sum(r['seconds'] for r in rows):.1f} s")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
