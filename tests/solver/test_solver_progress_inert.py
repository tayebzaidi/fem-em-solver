"""`OPS-43` (d) gate: ``FEM_EM_SOLVER_PROGRESS`` is bit-inert on child ``-n 1``
solves and visible only when set (PROJECT_PLAN §9 item 1, re-anchored by the
2026-09-10 10:30 review; §7 `OPS-43`).

(d1) raises MUMPS's ``ICNTL(4)`` and (d2) prints dof / degree / cell counts and
the solve's elapsed, both gated on one environment variable, both landed in
``81861d0`` (``src/fem_em_solver/core/time_harmonic.py``).  This module executes
the claim.

**Case.**  The existing smoke time-harmonic fixture, reused rather than rebuilt:
``tests/solver/test_time_harmonic_smoke.py``'s cylindrical domain at h = 0.03
(1 405 cells / 2 004 dofs), unit axial drive on tag 1, ``gauge_penalty=1e-3``,
degree 1, scored by the three-term Poynting identity that test gates.  No
``solver_petsc_options`` is passed — an explicit one is applied after the gate
and would win, masking it.

**Separation mechanism (disclosed).**  Every solve is a separate child
``mpiexec`` launched from **rank 0 only** of the ``-n 2`` pytest job — the
variable is read at solve time, so a same-process toggle proves less.  Rank 1
waits on a broadcast of the parsed results; every rank then asserts on the same
payload.  The children's environment is scrubbed of the parent job's
``PMI_``/``PMIX_``/``HYDRA_``/``MPICH_``/``OMPI_``/``MPIEXEC_`` variables: a
child of an ``mpiexec``-launched rank inherits Hydra's handshake and aborts
``PMI_Init failed``, exit 15 (measured 2026-09-10,
``tests/unit/test_memory_instrument.py``).

**Why ``-n 1`` (re-anchor, not a relaxation).**  The first design asserted one
unset-vs-set pair at child ``-n 2``.  The 06:00 windows showed that the complex
MUMPS smoke solve is not bit-reproducible across processes at ``-n 2``: 2 of 22
identical child solves drifted by 1 ULP (``…fd9fp-5`` / ``…fda1p-5`` against the
modal ``0x1.2bbe0e158fda0p-5``), in *both* settings, with bit-identical
geometry / ``‖A‖_F`` / ``‖b‖`` fingerprints — while 8/8 ``-n 1`` children read
``0x1.2bbe0e158fdb3p-5`` (``20260910T110803Z_OPS-43d.log:269–270``; known-issues
2026-09-10).  (d1)/(d2) change MUMPS verbosity and a print, nothing
partition-dependent, so the identity moves to ``-n 1``.

**Anchor (asserted, bit-identity, no tolerance).**  4 unset + 4 set child
``-n 1`` solves, interleaved.  The ``float.hex`` of the solution's global
2-norm, and of the three-term relative imbalance, must each form **one** value
across all eight children — a single set assertion carrying same-setting
reproducibility *and* unset == set, which cannot be green by selection.  No
child is dropped from the set.

**Negative controls (asserted — green on this fixture in all four 06:00
windows at ``-n 2``: ``20260910T110803Z_OPS-43d.log:81,144–145,155,218–219``).**
Progress-tagged lines (d2's ``[solve]`` prefix) number exactly 0 on every unset
child and >= 1 on every set child; the options dict handed to
``LinearProblem`` equals the pre-``81861d0`` literal below when unset and that
literal plus ``mat_mumps_icntl_4: 2`` when set; MUMPS ``ICNTL(4)`` reads back 0
unset and 2 set.

**Printed, asserted nowhere (rule (e)).**  6 unset + 6 set child ``-n 2``
solves, interleaved; each setting's distinct ``float.hex`` values with their
counts, beside the 2-of-22 record.  *Predicted:* the modal value is the same for
both settings.  The smoke case's own scalars (three-term < 25 %, two-term on its
116.7465 % record) are printed for the ``-n 1`` value, not asserted here — the
smoke test itself gates them.

Tier: smoke.  20 children of a 1 405-cell solve (the 06:00 window 4 ran 24 in
61 s, ``…110803Z:403``).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from mpi4py import MPI

from tests.complex_mode import complex_only

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The solver options dict ``TimeHarmonicSolver.solve`` built before `OPS-43`
#: existed — copied literally from
#: ``git show 81861d0^:src/fem_em_solver/core/time_harmonic.py`` lines 545-549.
#: Not imported from the code on purpose: the claim under test is that the
#: current code still produces exactly this when the variable is unset.
PRE_OPS43_BASELINE_OPTIONS = {
    "ksp_type": "preonly",
    "pc_type": "lu",
    "pc_factor_mat_solver_type": "mumps",
}

#: The level set in the "on" runs: d1's documented "useful one"
#: (``time_harmonic.py``: "2 = + main statistics").
PROGRESS_LEVEL = "2"

#: d2's print prefix, the progress tag counted by the negative control.
PROGRESS_TAG = "[solve]"

RESULT_SENTINEL = "OPS43D_RESULT "

#: Environment prefixes of the parent job that must not reach a child mpiexec.
_MPI_ENV_PREFIXES = ("PMI_", "PMIX_", "HYDRA_", "MPICH_", "OMPI_", "MPIEXEC_")

#: Per-child wall cap.  A child measured 1.3–1.8 s of solve-and-report in the
#: 06:00 windows; the cap only turns a hung child into a failure message.
CHILD_TIMEOUT_S = 60

#: Anchor: 4 unset + 4 set child solves at ``-n 1``, interleaved.
ANCHOR_NRANKS = 1
ANCHOR_PAIRS = 4

#: Printed only: 6 unset + 6 set child solves at ``-n 2``, interleaved.
PROBE_NRANKS = 2
PROBE_PAIRS = 6

#: The keys whose ``float.hex`` must form one value across the anchor children.
ANCHOR_KEYS = ("norm2", "relative_imbalance")

#: Records the printed ``-n 2`` distribution is read beside (not asserted).
RECORD_N1_NORM2 = "0x1.2bbe0e158fdb3p-5"  # 8/8, 20260910T110803Z_OPS-43d.log:270
RECORD_N2_MODAL_NORM2 = "0x1.2bbe0e158fda0p-5"  # 20 of 22, known-issues 2026-09-10


def _child_main() -> None:
    """One smoke solve in a fresh ``mpiexec`` job; prints a result line."""
    import numpy as np
    import ufl
    from petsc4py import PETSc

    import fem_em_solver.core.time_harmonic as th
    from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
    from fem_em_solver.post.power_balance import poynting_power_balance
    from tests.solver.test_time_harmonic_smoke import (
        EPSILON_R,
        FREQUENCY_HZ,
        SIGMA,
        _smoke_mesh,
    )

    comm = MPI.COMM_WORLD

    # Capture the options dict exactly as handed to LinearProblem.  Wrapping
    # the name the solver module resolves at call time changes nothing else.
    captured: list[dict] = []
    real_linear_problem = th.LinearProblem

    def _capturing_linear_problem(*args, **kwargs):
        captured.append(dict(kwargs.get("petsc_options") or {}))
        return real_linear_problem(*args, **kwargs)

    th.LinearProblem = _capturing_linear_problem

    # Same construction as test_time_harmonic_smoke_solve_conserves_real_power.
    mesh, cell_tags, facet_tags = _smoke_mesh(0.03, comm)
    problem = th.TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=1.0),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
    )
    assert isinstance(problem, TimeHarmonicProblem)
    solver = th.TimeHarmonicSolver(problem, degree=1)
    j_expr = ufl.as_vector([0.0, 0.0, 1.0])

    def current_density(x):
        return j_expr

    fields = solver.solve(
        current_density=current_density, subdomain_id=1, gauge_penalty=1e-3
    )
    dx_source = ufl.Measure("dx", domain=mesh, subdomain_data=cell_tags)(1)
    balance = poynting_power_balance(
        fields.e_complex,
        omega=fields.omega,
        sigma=SIGMA,
        current_density=j_expr,
        source_measure=dx_source,
        comm=comm,
    )

    # Global, rank-reduced reads of the solution vector.
    vec = fields.e_complex.x.petsc_vec
    norm2 = float(vec.norm(PETSc.NormType.NORM_2))  # collective
    n_owned = fields.e_complex.function_space.dofmap.index_map.size_local * (
        fields.e_complex.function_space.dofmap.index_map_bs
    )
    local_sum = complex(np.sum(fields.e_complex.x.array[:n_owned]))
    global_sum = comm.allreduce(local_sum, op=MPI.SUM)
    tdim = mesh.topology.dim
    ncells = int(comm.allreduce(mesh.topology.index_map(tdim).size_local, op=MPI.SUM))
    ndofs = int(fields.e_complex.function_space.dofmap.index_map.size_global)

    # The factor's own ICNTL(4), read back from MUMPS.
    try:
        icntl4 = int(
            solver._linear_problem.solver.getPC().getFactorMatrix().getMumpsIcntl(4)
        )
    except Exception as exc:  # pragma: no cover - reported, then fails the assert
        icntl4 = f"unreadable: {exc!r}"
    cells_per_rank = comm.gather(int(mesh.topology.index_map(tdim).size_local), root=0)
    # Fingerprints that localise a run-to-run difference (printed only): mesh
    # geometry (owned nodes), then the assembled operator and load.
    n_geom = mesh.geometry.index_map().size_local
    geom_sum = comm.allreduce(float(np.sum(mesh.geometry.x[:n_geom])), op=MPI.SUM)
    lp = solver._linear_problem
    a_norm = float(lp.A.norm(PETSc.NormType.FROBENIUS))  # collective
    b_norm = float(lp.b.norm(PETSc.NormType.NORM_2))  # collective
    all_options = comm.gather(captured, root=0)
    all_icntl4 = comm.gather(icntl4, root=0)

    if comm.rank == 0:
        payload = {
            "env_progress": os.environ.get("FEM_EM_SOLVER_PROGRESS"),
            "nranks": comm.size,
            "ncells": ncells,
            "ndofs": ndofs,
            "cells_per_rank": cells_per_rank,
            "geom_sum": geom_sum.hex(),
            "A_fro": a_norm.hex(),
            "b_norm": b_norm.hex(),
            "options_per_rank": all_options,
            "icntl4_per_rank": all_icntl4,
            "norm2": norm2.hex(),
            "sum_real": float(global_sum.real).hex(),
            "sum_imag": float(global_sum.imag).hex(),
            "relative_imbalance": float(balance["relative_imbalance"]).hex(),
            "two_term_relative_imbalance": float(
                balance["two_term_relative_imbalance"]
            ).hex(),
        }
        print(RESULT_SENTINEL + json.dumps(payload), flush=True)


def _scrubbed_env(progress: str | None) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(_MPI_ENV_PREFIXES)}
    env.pop("FEM_EM_SOLVER_PROGRESS", None)
    if progress is not None:
        env["FEM_EM_SOLVER_PROGRESS"] = progress
    env["PYTHONPATH"] = (
        str(REPO_ROOT / "src") + os.pathsep + str(REPO_ROOT) + os.pathsep
        + env.get("PYTHONPATH", "")
    )
    return env


def _run_child(progress: str | None, nranks: int) -> dict:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            ["mpiexec", "-n", str(nranks), sys.executable,
             str(Path(__file__).resolve()), "--child"],
            env=_scrubbed_env(progress),
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=CHILD_TIMEOUT_S,
            check=False,
        )
        returncode, output = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as exc:
        returncode = f"timeout after {CHILD_TIMEOUT_S} s"
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
    elapsed = time.perf_counter() - t0
    lines = output.splitlines()
    result = None
    for line in lines:
        if line.startswith(RESULT_SENTINEL):
            result = json.loads(line[len(RESULT_SENTINEL):])
    return {
        "progress": progress,
        "nranks": nranks,
        "returncode": returncode,
        "elapsed_s": elapsed,
        "tagged_lines": [ln for ln in lines if ln.lstrip().startswith(PROGRESS_TAG)],
        "n_output_lines": len(lines),
        "output_tail": lines[-40:],
        "result": result,
    }


def _interleaved(pairs: int, nranks: int) -> list[dict]:
    runs = []
    for _ in range(pairs):
        runs.append(_run_child(None, nranks))
        runs.append(_run_child(PROGRESS_LEVEL, nranks))
    return runs


def _print_child(i: int, run: dict) -> None:
    res = run["result"] or {}
    print(
        f"  #{i:02d} -n {run['nranks']} progress={run['progress']!s:<4s} "
        f"exit {run['returncode']} {run['elapsed_s']:.1f} s "
        f"'{PROGRESS_TAG}' lines {len(run['tagged_lines'])}  "
        f"norm2 {res.get('norm2')}  rel_imb {res.get('relative_imbalance')}  "
        f"two_term {res.get('two_term_relative_imbalance')}  "
        f"sum {res.get('sum_real')} {res.get('sum_imag')}  "
        f"A {res.get('A_fro')}  b {res.get('b_norm')}  geom {res.get('geom_sum')}  "
        f"cells/rank {res.get('cells_per_rank')}  "
        f"ICNTL(4) {res.get('icntl4_per_rank')}  "
        f"options {res.get('options_per_rank')}",
        flush=True,
    )


def _distribution(runs: list[dict], key: str) -> dict:
    vals = [r["result"][key] for r in runs if r["result"] is not None]
    return {v: vals.count(v) for v in sorted(set(vals))}


@complex_only
def test_solver_progress_variable_is_bit_inert_at_n1_and_visible_only_when_set():
    comm = MPI.COMM_WORLD

    payload = None
    if comm.rank == 0:
        try:
            payload = {
                "anchor": _interleaved(ANCHOR_PAIRS, ANCHOR_NRANKS),
                "probe": _interleaved(PROBE_PAIRS, PROBE_NRANKS),
            }
        except Exception as exc:  # keep rank 1 out of a hang
            payload = {"error": repr(exc)}
    payload = comm.bcast(payload, root=0)
    assert "error" not in payload, payload.get("error")

    anchor, probe = payload["anchor"], payload["probe"]
    anchor_unset = [r for r in anchor if r["progress"] is None]
    anchor_set = [r for r in anchor if r["progress"] == PROGRESS_LEVEL]

    if comm.rank == 0:
        print(f"\n[OPS-43(d)] anchor children, mpiexec -n {ANCHOR_NRANKS}, "
              f"{ANCHOR_PAIRS} unset + {ANCHOR_PAIRS} set, launch order:")
        for i, run in enumerate(anchor):
            _print_child(i, run)
        for run in anchor:
            if run["result"] is None or run["returncode"] != 0:
                print(f"  --- failed child (progress={run['progress']}) tail ---")
                for ln in run["output_tail"]:
                    print("  | " + ln)
        for key in ANCHOR_KEYS:
            print(f"  -n {ANCHOR_NRANKS} all 8: distinct {key} "
                  f"{_distribution(anchor, key)}  (one value required; record "
                  f"norm2 {RECORD_N1_NORM2} 8/8)")
        res0 = anchor[0]["result"]
        if res0 is not None:
            from tests.solver.test_time_harmonic_smoke import (
                AXIAL_RECORD_IMBALANCE,
                POYNTING_IMBALANCE_MAX,
            )

            print(f"  cells {res0['ncells']}, dofs {res0['ndofs']}")
            print(f"  smoke scalars (printed, not asserted here): three-term "
                  f"{float.fromhex(res0['relative_imbalance']):.9f} "
                  f"(smoke band < {POYNTING_IMBALANCE_MAX}); two-term "
                  f"{float.fromhex(res0['two_term_relative_imbalance']):.9f} "
                  f"(smoke record {AXIAL_RECORD_IMBALANCE})")

        print(f"\n[OPS-43(d)] -n {PROBE_NRANKS} children (printed, asserted nowhere), "
              f"{PROBE_PAIRS} unset + {PROBE_PAIRS} set, launch order:")
        for i, run in enumerate(probe):
            _print_child(i, run)
        for label, prog in (("unset", None), ("set", PROGRESS_LEVEL)):
            sub = [r for r in probe if r["progress"] == prog]
            n_ok = sum(1 for r in sub if r["result"] is not None)
            for key in ANCHOR_KEYS:
                print(f"  -n {PROBE_NRANKS} {label:<5s} ({n_ok}/{len(sub)} reported): "
                      f"distinct {key} {_distribution(sub, key)}")
        print(f"  record: 2 of 22 -n 2 children drifted 1 ULP, modal norm2 "
              f"{RECORD_N2_MODAL_NORM2} (known-issues 2026-09-10). "
              f"Predicted: the modal value is the same for both settings.")
        sys.stdout.flush()

    # --- Every anchor child ran and reported; none is dropped. ---
    assert len(anchor_unset) == ANCHOR_PAIRS and len(anchor_set) == ANCHOR_PAIRS
    for run in anchor:
        assert run["returncode"] == 0 and run["result"] is not None, (
            f"-n {ANCHOR_NRANKS} child progress={run['progress']} failed: exit "
            f"{run['returncode']}; tail\n" + "\n".join(run["output_tail"])
        )
        assert run["result"]["nranks"] == ANCHOR_NRANKS
        assert run["result"]["env_progress"] == run["progress"]

    # --- Anchor: one float.hex value across all eight children, no tolerance. ---
    for key in ANCHOR_KEYS:
        values = {run["result"][key] for run in anchor}
        assert len(values) == 1, (
            f"{key} is not one value across the {len(anchor)} -n {ANCHOR_NRANKS} "
            f"children (unset and set interleaved): "
            + ", ".join(f"progress={r['progress']}:{r['result'][key]}" for r in anchor)
        )

    # --- Negative controls: visibility, the options dict, ICNTL(4) read-back. ---
    expected_set = dict(PRE_OPS43_BASELINE_OPTIONS, mat_mumps_icntl_4=int(PROGRESS_LEVEL))
    for run in anchor_unset:
        assert len(run["tagged_lines"]) == 0, (
            f"progress output leaked with the variable unset: {run['tagged_lines']}"
        )
        for rank_opts in run["result"]["options_per_rank"]:
            assert rank_opts == [PRE_OPS43_BASELINE_OPTIONS], (
                f"unset-run options {rank_opts} differ from the pre-OPS-43 baseline "
                f"{PRE_OPS43_BASELINE_OPTIONS}"
            )
        assert run["result"]["icntl4_per_rank"] == [0] * ANCHOR_NRANKS
    for run in anchor_set:
        assert len(run["tagged_lines"]) >= 1, (
            "FEM_EM_SOLVER_PROGRESS set but no progress-tagged line was printed"
        )
        for rank_opts in run["result"]["options_per_rank"]:
            assert rank_opts == [expected_set], (
                f"set-run options {rank_opts} are not the baseline plus "
                f"mat_mumps_icntl_4={PROGRESS_LEVEL}: the gate did not fire as wired"
            )
        assert run["result"]["icntl4_per_rank"] == [int(PROGRESS_LEVEL)] * ANCHOR_NRANKS


if __name__ == "__main__" and "--child" in sys.argv:
    _child_main()
