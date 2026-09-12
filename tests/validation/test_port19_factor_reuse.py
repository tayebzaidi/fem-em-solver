"""`PORT-19` step 2 — one factorisation per matched-termination sweep.

`PORT-19` step 1 measured that the lumped-sheet sweep's system matrix is
bit-identical across drives (``‖A_k − A_1‖_∞ = 0.0``,
``20260911T020253Z_PORT-19-step1.log:1832–1835``).  Step 2 lands
``run_n_port_sparameter_sweep(..., reuse_factorization=...)`` — default on for
the lumped-sheet route — which factorises for the first drive and
back-substitutes the other drives' right-hand sides through
``TimeHarmonicSolver.solve_with_held_factorization``.  This module measures the
reuse path against the per-drive path on the gated 4-leg fixture at 10 MHz
(``build_four_port_sweep(build_only=True)``), both in one process.

**Anchors (asserted).**

* (A) Reused and per-drive sweeps agree entry by entry on ``S`` and ``Z`` to
  relative ≤ 1e-12 — the same arithmetic up to the 1-ULP ``-n 2`` MUMPS drift
  (known-issues 2026-09-10).  Each drive's kept ``E`` phasor (``keep_fields``,
  `POST-6`) is a distinct ``Function`` per drive at every width, so a later
  back-substitution cannot overwrite an earlier drive's field.  **Which half
  asserts at which width (`PORT-19` step 5, ruling (1) of the 2026-09-12 03:00
  review):** ``S`` and ``Z`` are asserted at every width; the kept-``E``
  agreement to 1e-12 is asserted **only at ``-n 1``** (bit-identity: all four
  read 0.000e+00, ``20260912T051457Z_PORT-19-step4-n1.log:1872–1873``) and
  printed, then skipped, at ``-n 2``.  At ``-n 2`` the per-drive comparand's four
  separate factorisations are not bit-reproducible (~4e-11 measured,
  ``…PORT-19-step4-isolation.log:1891–1892``), so that comparison measures MUMPS
  drift, not the reuse path.  ``-n 1`` is the anchor width here by ruling — the
  only such case besides `OPS-43` (d).  The band does not move.
* (B) A counter on ``LinearProblem`` construction and on ``LinearProblem.solve``
  (each call re-assembles ``A`` and so re-factorises) reads exactly **1** on the
  reused sweep and **4** on the per-drive sweep.

**Negative control (asserted, ruling (3) of the 2026-09-11 03:00 review).**  A
*stale* factor — built with P2's spec at 51 Ohm (a ``dataclasses.replace``
copy, as step 1's control (ii)) — back-substitutes the 50 Ohm drives'
right-hand sides.  Its ``S`` must differ from the per-drive 50 Ohm ``S`` by
more than the 1e-12 band in max relative entry, or the anchor-(A) probe could
not see a wrong factor.  *Predicted, printed beside it, never asserted*
(standing rule (e)): ≥ 1e-10, since step 1's control (ii) moved the port
entries of ``A`` by 1.96e-2 relative (``…PORT-19-step1.log:1841``) and no prior
``S``-level measurement exists.

The raise on the other routes (``reuse_factorization=True`` without
``lumped_sheet_ports``) is asserted too; it solves nothing.

**Printed.** wall per drive on both paths, the factor counts, and MUMPS INFOG(22)
(MB effectively used, summed) of the stale factor, which has the same size as
the reused one.

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-19-step2 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       FEM_EM_REQUIRE_COMPLEX=1 PYTHONPATH=/workspace/src timeout -k 30 300 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port19_factor_reuse.py -v -s --tb=short'"
"""

from __future__ import annotations

import dataclasses
import time

import numpy as np
import pytest
from mpi4py import MPI

import fem_em_solver.core.time_harmonic as th_module
import fem_em_solver.ports.sparameters as sparam_module
from fem_em_solver.core import TimeHarmonicSolver
from fem_em_solver.ports.lumped import run_lumped_sheet_port_case
from fem_em_solver.ports.sparameters import (
    _assemble_impedance_matrix,
    _assemble_sparameter_matrix,
    run_n_port_sparameter_sweep,
)

from tests.complex_mode import complex_only
from tests.validation.test_port_birdcage_four_port import build_four_port_sweep

# (A): same arithmetic; the -n 2 MUMPS drift is 1 ULP (known-issues 2026-09-10).
REUSE_REPRODUCTION_RTOL = 1.0e-12
# (B): one factorisation per sweep, against one per drive on the 4-leg fixture.
EXPECTED_REUSED_FACTORISATIONS = 1
EXPECTED_PER_DRIVE_FACTORISATIONS = 4
# Negative control: P2's termination for the stale factor, and the *predicted*
# (printed, not asserted) floor of its S-level deviation.
STALE_PORT_ID = "P2"
STALE_PORT_IMPEDANCE_OHM = 51.0
STALE_PREDICTED_MIN_DEVIATION = 1.0e-10
Z0_OHM = 50.0


def _max_relative_entry(measured, reference):
    """``max_ij |m_ij − r_ij| / |r_ij|`` and the worst index."""
    rel = np.abs(np.asarray(measured) - np.asarray(reference)) / np.abs(
        np.asarray(reference)
    )
    idx = np.unravel_index(int(np.argmax(rel)), rel.shape)
    return float(rel[idx]), (int(idx[0]) + 1, int(idx[1]) + 1)


def _field_relative_difference(f_a, f_b, comm):
    """Global ``‖a − b‖₂ / ‖b‖₂`` over owned dofs (comm-reduced)."""
    n_owned = f_b.function_space.dofmap.index_map.size_local * f_b.function_space.dofmap.index_map_bs
    a = f_a.x.array[:n_owned]
    b = f_b.x.array[:n_owned]
    num = comm.allreduce(float(np.sum(np.abs(a - b) ** 2)), op=MPI.SUM)
    den = comm.allreduce(float(np.sum(np.abs(b) ** 2)), op=MPI.SUM)
    return float(np.sqrt(num / den))


class _Counters:
    def __init__(self):
        self.init = 0
        self.solve = 0
        self.drive_walls = []


@pytest.fixture(scope="module")
def reuse_case():
    comm = MPI.COMM_WORLD
    t0 = time.perf_counter()
    built = build_four_port_sweep(build_only=True)
    t_build = time.perf_counter() - t0

    problem = built["problem"]
    port_defs = built["port_defs"]
    specs = built["specs"]
    facet_tags = built["facet_tags"]

    counters = _Counters()
    original_lp = th_module.LinearProblem
    original_case = sparam_module.run_lumped_sheet_port_case

    class _CountingLinearProblem(original_lp):
        def __init__(self, *args, **kwargs):
            counters.init += 1
            super().__init__(*args, **kwargs)

        def solve(self):
            counters.solve += 1
            return super().solve()

    def _timed_case(*args, **kwargs):
        comm.Barrier()
        t = time.perf_counter()
        out = original_case(*args, **kwargs)
        comm.Barrier()
        counters.drive_walls.append(time.perf_counter() - t)
        return out

    def _reduced(value):
        return int(comm.allreduce(value, op=MPI.MIN)), int(comm.allreduce(value, op=MPI.MAX))

    th_module.LinearProblem = _CountingLinearProblem
    sparam_module.run_lumped_sheet_port_case = _timed_case
    try:
        runs = {}
        for label, flag in (("reused", None), ("per_drive", False)):
            counters.init = counters.solve = 0
            counters.drive_walls = []
            comm.Barrier()
            t = time.perf_counter()
            result = run_n_port_sparameter_sweep(
                problem,
                port_defs,
                lumped_sheet_ports=specs,
                lumped_sheet_facet_tags=facet_tags,
                keep_fields=True,
                reuse_factorization=flag,
            )
            comm.Barrier()
            runs[label] = {
                "result": result,
                "s": np.asarray(result.s_matrix, dtype=np.complex128),
                "z": np.asarray(result.z_matrix, dtype=np.complex128),
                "init": _reduced(counters.init),
                "solve": _reduced(counters.solve),
                "walls": list(counters.drive_walls),
                "total": time.perf_counter() - t,
            }

        # Negative control: a factor built with P2 at 51 Ohm, then the 50 Ohm
        # drives' right-hand sides back-substituted through it.
        counters.init = counters.solve = 0
        stale_specs = [
            dataclasses.replace(s, port_impedance_ohm=STALE_PORT_IMPEDANCE_OHM)
            if s.port_id == STALE_PORT_ID
            else s
            for s in specs
        ]
        stale = TimeHarmonicSolver(problem, degree=1)
        comm.Barrier()
        t = time.perf_counter()
        run_lumped_sheet_port_case(
            problem,
            port_defs,
            stale_specs,
            facet_tags=facet_tags,
            driven_port_id=port_defs[0].port_id,
            verbose=False,
            solver=stale,
        )
        comm.Barrier()
        t_stale_factor = time.perf_counter() - t
        stale_results = {}
        for port in port_defs:
            stale_results[port.port_id] = run_lumped_sheet_port_case(
                problem,
                port_defs,
                specs,
                facet_tags=facet_tags,
                driven_port_id=port.port_id,
                verbose=False,
                solver=stale,
            )
        stale_s = _assemble_sparameter_matrix(port_defs, stale_results, z0_ohm=Z0_OHM)
        stale_z = _assemble_impedance_matrix(port_defs, stale_results)
        stale_counts = (_reduced(counters.init), _reduced(counters.solve))
        infog22 = None
        try:
            factor = stale._linear_problem.solver.getPC().getFactorMatrix()
            infog22 = int(factor.getMumpsInfog(22))
        except Exception as exc:  # diagnostic print only
            infog22 = f"unavailable ({type(exc).__name__})"
    finally:
        th_module.LinearProblem = original_lp
        sparam_module.run_lumped_sheet_port_case = original_case

    reused, per_drive = runs["reused"], runs["per_drive"]
    s_dev = _max_relative_entry(reused["s"], per_drive["s"])
    z_dev = _max_relative_entry(reused["z"], per_drive["z"])
    stale_s_dev = _max_relative_entry(stale_s, per_drive["s"])
    stale_z_dev = _max_relative_entry(stale_z, per_drive["z"])

    port_ids = [p.port_id for p in port_defs]
    field_devs = {
        pid: _field_relative_difference(
            reused["result"].fields[pid].e_complex,
            per_drive["result"].fields[pid].e_complex,
            comm,
        )
        for pid in port_ids
    }
    distinct_fields = len(
        {id(reused["result"].fields[pid].e_complex) for pid in port_ids}
    ) == len(port_ids)

    if comm.rank == 0:
        print(
            f"\n[PORT-19 step2] gated 4-leg fixture: {built['cells']} cells, "
            f"f = {problem.frequency_hz:.3e} Hz, build {t_build:.2f} s at -n {comm.size}",
            flush=True,
        )
        for label in ("reused", "per_drive"):
            r = runs[label]
            print(
                f"    {label:9s}: LinearProblem constructions (min,max over ranks) "
                f"{r['init']}, LinearProblem.solve calls {r['solve']}; wall per drive "
                + ", ".join(f"{w:.2f}" for w in r["walls"])
                + f" s; sweep {r['total']:.2f} s",
                flush=True,
            )
        print(
            f"    (A) max rel |S_reused - S_per_drive| = {s_dev[0]:.3e} at S_{s_dev[1]}; "
            f"max rel |Z_reused - Z_per_drive| = {z_dev[0]:.3e} at Z_{z_dev[1]} "
            f"(band {REUSE_REPRODUCTION_RTOL:.0e})",
            flush=True,
        )
        print(
            "    (A) kept E phasors, rel ||E_reused - E_per_drive||_2: "
            + ", ".join(f"{pid} {d:.3e}" for pid, d in field_devs.items())
            + f"; distinct Function per drive: {distinct_fields}",
            flush=True,
        )
        for row in range(len(port_ids)):
            print(
                "    S_reused row "
                + f"{row + 1}: "
                + "  ".join(f"{v:+.12e}" for v in reused["s"][row]),
                flush=True,
            )
        print(
            f"    control: stale factor (P2 at {STALE_PORT_IMPEDANCE_OHM} Ohm) built in "
            f"{t_stale_factor:.2f} s; counts (constructions, solves) {stale_counts}; "
            f"MUMPS INFOG(22) = {infog22} MB",
            flush=True,
        )
        print(
            f"    control: max rel |S_stale - S_per_drive| = {stale_s_dev[0]:.3e} at "
            f"S_{stale_s_dev[1]} (asserted > {REUSE_REPRODUCTION_RTOL:.0e}; predicted "
            f">= {STALE_PREDICTED_MIN_DEVIATION:.0e}, printed only: "
            f"{'meets' if stale_s_dev[0] >= STALE_PREDICTED_MIN_DEVIATION else 'MISSES'} "
            f"the prediction); max rel |Z_stale - Z_per_drive| = {stale_z_dev[0]:.3e} "
            f"at Z_{stale_z_dev[1]}",
            flush=True,
        )

    return {
        "problem": problem,
        "port_defs": port_defs,
        "specs": specs,
        "runs": runs,
        "s_dev": s_dev,
        "z_dev": z_dev,
        "field_devs": field_devs,
        "distinct_fields": distinct_fields,
        "stale_s_dev": stale_s_dev,
        "stale_counts": stale_counts,
    }


@complex_only
def test_a_reused_s_matches_per_drive_entrywise(reuse_case):
    dev, idx = reuse_case["s_dev"]
    assert dev <= REUSE_REPRODUCTION_RTOL, (
        f"reused S differs from per-drive S by {dev:.3e} relative at S_{idx} "
        f"(band {REUSE_REPRODUCTION_RTOL:.0e}) — the reuse path is not the same arithmetic"
    )


@complex_only
def test_a_reused_z_matches_per_drive_entrywise(reuse_case):
    dev, idx = reuse_case["z_dev"]
    assert dev <= REUSE_REPRODUCTION_RTOL, (
        f"reused Z differs from per-drive Z by {dev:.3e} relative at Z_{idx} "
        f"(band {REUSE_REPRODUCTION_RTOL:.0e})"
    )


@complex_only
def test_a_kept_fields_are_per_drive_and_match(reuse_case):
    assert reuse_case["distinct_fields"], (
        "reused sweep returned a shared E Function across drives — keep_fields "
        "would hold the last drive's field for every port"
    )
    comm = MPI.COMM_WORLD
    if comm.size > 1:
        # comm.size is identical on every rank; the deviations were printed by
        # the fixture, and are repeated here so the skip carries the reading.
        if comm.rank == 0:
            print(
                f"\n[PORT-19 step5] -n {comm.size}: kept E rel devs (printed only) "
                + ", ".join(f"{pid} {d:.3e}" for pid, d in reuse_case["field_devs"].items()),
                flush=True,
            )
        pytest.skip(
            f"kept-E agreement is asserted at -n 1 only (bit-identity); at -n {comm.size} "
            "the per-drive factorisations are not bit-reproducible — known-issues "
            "2026-09-12 ruling, OPS-43 (d) precedent; deviations printed above"
        )
    bad = {
        pid: d for pid, d in reuse_case["field_devs"].items() if not d <= REUSE_REPRODUCTION_RTOL
    }
    assert not bad, f"kept E phasors differ between paths beyond 1e-12: {bad}"


@complex_only
def test_b_reused_sweep_factorises_once(reuse_case):
    r = reuse_case["runs"]["reused"]
    expected = (EXPECTED_REUSED_FACTORISATIONS, EXPECTED_REUSED_FACTORISATIONS)
    assert r["init"] == expected and r["solve"] == expected, (
        f"reused sweep: LinearProblem constructions {r['init']}, solves {r['solve']}; "
        f"expected exactly {EXPECTED_REUSED_FACTORISATIONS} on every rank"
    )


@complex_only
def test_b_per_drive_sweep_factorises_per_drive(reuse_case):
    r = reuse_case["runs"]["per_drive"]
    expected = (EXPECTED_PER_DRIVE_FACTORISATIONS, EXPECTED_PER_DRIVE_FACTORISATIONS)
    assert r["init"] == expected and r["solve"] == expected, (
        f"per-drive sweep: LinearProblem constructions {r['init']}, solves {r['solve']}; "
        f"expected exactly {EXPECTED_PER_DRIVE_FACTORISATIONS} on every rank"
    )


@complex_only
def test_control_a_stale_factor_is_visible(reuse_case):
    dev, idx = reuse_case["stale_s_dev"]
    # The stale sweep itself factorised once (the 51 Ohm drive) and never again.
    assert reuse_case["stale_counts"] == ((1, 1), (1, 1))
    assert dev > REUSE_REPRODUCTION_RTOL, (
        f"a factor built with {STALE_PORT_ID} at {STALE_PORT_IMPEDANCE_OHM} Ohm reproduces "
        f"the 50 Ohm per-drive S to {dev:.3e} at S_{idx} — the 1e-12 probe cannot see a "
        "wrong factor"
    )


@complex_only
def test_reuse_true_raises_off_the_lumped_sheet_route(reuse_case):
    problem, port_defs = reuse_case["problem"], reuse_case["port_defs"]
    with pytest.raises(ValueError, match="lumped-sheet route only"):
        run_n_port_sparameter_sweep(
            problem, port_defs, gap_voltage_ports=[], reuse_factorization=True
        )
    with pytest.raises(ValueError, match="lumped-sheet route only"):
        run_n_port_sparameter_sweep(problem, port_defs, reuse_factorization=True)
