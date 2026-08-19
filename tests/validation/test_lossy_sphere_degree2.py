"""`TH-12` step 1: the lossy sphere at **degree-2 N1curl** — accuracy per DOF.

Commissioned 2026-08-18 by operator directive (PROJECT_PLAN §7 `TH-12`).  Every
open accuracy question in the TH/MAT lineage is a cells-per-skin-depth question,
and `TH-11` step 5b/5c measured that the degree-1 route to a 64 MHz h → 0
bracket **does not fit this box** (2 807 309 cells peaks at `memory.max` =
64.00 GiB; even the shrunk 994 258-cell rung does).  Element order is the other
axis: ~20 DOFs/tet against 6, denser MUMPS blocks, but second-order field
convergence — so possibly far fewer cells at matched accuracy.
``TimeHarmonicSolver(problem, degree=2)`` has existed since `TH-1` and has never
been gated; this file gates it on the one fixture whose reference is a closed
form, `TH-10`'s lossy saline sphere at 64 MHz.

**The gate** (§7, stated before the run): interior relL2 against
``LossySphereSeries`` on the **coarse** rung (5 866 cells) must be **≤ the
degree-1 fine-rung record, 3.643% at 17 670 cells** — i.e. degree 2 must reach
degree-1's best accuracy at strictly fewer cells.  It is a one-sided gate on a
recorded number, not a band fitted after the fact.

**Negative control**: degree 1 on the *same* coarse rung must reproduce its
recorded 8.387% ohmic-power error in-run
(`20260813T170337Z_TH-10-step4-power-n2.log`).  Without it, a degree-2 number
alone cannot distinguish "second order helps" from "this rung was always better
than the record says" — the control pins the fixture to the record inside the
same process, same gmsh, same ranks.

**The deliverable is the cost table**, not the pass: DOF counts, solve wall time
(assembly + MUMPS factor + back-substitution, the number a cost model needs) and
``/sys/fs/cgroup/memory.peak`` are printed for both orders beside their cell
counts.  The weekly review reads accuracy-per-DOF and cost-per-DOF off this log
and sets the production element order (§7 decision clause); nothing here decides
it, and no recorded degree-1 number moves.

**Identity.** The complex-power identity ``Im Z = 4ω(W_m − W_e)/I′²`` of the
`TH-11` family needs a *driven port*; this fixture has no source at all (it is
driven by an imposed Dirichlet total field), so that family does not apply here
and is not restated.  The identity this fixture does carry is that the ohmic
integrand ``½σ E·Ē`` is real by construction — ``ufl.inner`` conjugates its
second argument — so ``|Im P| / Re P`` is round-off.  It is gated at the family's
unchanged **1e-9** on every solve: a conjugation slip in the assembled form (the
`TH-1` ``ufl.dot`` trap) shows up here as a nonzero imaginary power.

Scope: sphere fixture, 64 MHz, one rung.  No production-order decision, no coil
(that is step 2, serial on this), no `MAT-4`/coil-loading/SAR claim moves.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_lossy_sphere_degree2.py -v -s'
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.post.evaluation import evaluate_vector_field_parallel

from tests.complex_mode import complex_only
from tests.validation.test_lossy_sphere_fullwave import (
    FREQUENCY_64_HZ,
    REFERENCE_QUADRATURE_DEGREE,
    RESOLUTIONS_64,
    SPHERE_TAG,
    _integrate_over_sphere,
    _interior_probe_points,
    _mesh_and_solve,
    _rel_l2,
    _series,
    _series_interior_interpolant,
)

# The coarse rung of `TH-10`'s own 64 MHz ladder, imported not restated.
COARSE_RESOLUTION = RESOLUTIONS_64[0]

# ---------------------------------------------------------------------------
# Recorded degree-1 numbers this file gates against.  All three are quoted from
# `20260813T170337Z_TH-10-step4-power-n2.log` / the `TH-10` §7 entry; none of
# them moves in this chunk.
# ---------------------------------------------------------------------------
DEGREE1_FINE_FIELD_RECORD = 0.03643  # interior relL2 at 17 670 cells, 64 MHz
DEGREE1_FINE_CELLS = 17670
DEGREE1_COARSE_POWER_RECORD = 0.08387  # ohmic-power error at 5 866 cells

# Negative-control band.  The control re-runs the *same* fixture at the *same*
# rank count, so it is a reproduction, not a comparison: the only slack allowed
# is the two digits the record is quoted to.  Widening this would turn the
# control into a formality.
CONTROL_TOLERANCE_PP = 0.002

# The imaginary part of ½∫σE·Ē, relative to its real part.  The `TH-11` family
# bound, unchanged.
POWER_IMAGINARY_BOUND = 1.0e-9


def _rss_peak_bytes(comm) -> float:
    """Summed peak RSS across ranks, in bytes.

    ``/sys/fs/cgroup/memory.peak`` is the container's **lifetime** high-water
    mark and is not resettable from inside a test, so on a box where a
    `TH-11`-scale run has already touched the cap it reads 64 GiB for every
    subsequent job and measures nothing.  ``ru_maxrss`` is per process and
    starts fresh with the interpreter, so the summed value is the number a
    cost-per-DOF model actually wants.  It is still a high-water mark over the
    whole test process, which for this module is dominated by the solve.
    """
    import resource

    local = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024.0
    return float(comm.allreduce(local, op=MPI.SUM))


def _memory_peak_bytes() -> tuple[float, float]:
    """``(memory.peak, memory.max)`` of the container cgroup, in bytes.

    Printed only as the cgroup context for :func:`_rss_peak_bytes` — see its
    docstring for why the peak alone is not a per-run measurement.  Returns
    ``(nan, nan)`` off cgroup-v2 rather than failing: this is a printed cost
    measurement, not a gate, and it must never be the reason a physics gate
    cannot report.
    """

    def _read(name: str) -> float:
        try:
            with open(f"/sys/fs/cgroup/{name}") as handle:
                text = handle.read().strip()
        except OSError:
            return float("nan")
        if text == "max":
            return float("inf")
        try:
            return float(text)
        except ValueError:
            return float("nan")

    return _read("memory.peak"), _read("memory.max")


def _run_at_degree(degree: int) -> dict:
    """One solve of the coarse rung at ``degree``.  Returns the measured row.

    Field error, ohmic power (FEM and the series reference integrated over the
    same meshed cells with the same σ), the imaginary-power identity, DOFs,
    wall time and cgroup peak — everything both the gate and the cost table
    need, from a single solve.
    """
    comm = MPI.COMM_WORLD
    series = _series(FREQUENCY_64_HZ)

    t0 = time.perf_counter()
    msh, cell_tags, fields, ncells = _mesh_and_solve(
        series, COARSE_RESOLUTION[0], COARSE_RESOLUTION[1], degree=degree
    )
    # Barrier before stopping the clock: the ranks leave the solve at different
    # times and a rank-local wall time is not a cost number.
    comm.Barrier()
    solve_wall_s = time.perf_counter() - t0

    # The N1curl space the solve actually ran in.  Rebuilt rather than reached
    # for through the solver so this stays valid whatever `_mesh_and_solve`
    # returns; the dofmap on 5 866 cells is cheap.
    v_space = fem.functionspace(msh, ("N1curl", degree))
    index_map = v_space.dofmap.index_map
    n_dofs = int(index_map.size_global * v_space.dofmap.index_map_bs)

    points = _interior_probe_points()
    real_values, valid_real = evaluate_vector_field_parallel(fields.e_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(fields.e_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(
            f"{int((~valid).sum())} interior probe points were not evaluated "
            f"at degree {degree}"
        )
    e_fem = np.real(real_values) + 1j * np.real(imag_values)
    field_error = _rel_l2(e_fem, series.internal_field(points))

    # Ohmic power, kept complex so the imaginary part is available as the
    # identity below; `_ohmic_power` discards it by design.
    p_fem_complex = _integrate_over_sphere(
        0.5 * fields.sigma_field * ufl.inner(fields.e_complex, fields.e_complex),
        msh,
        cell_tags,
        comm,
        REFERENCE_QUADRATURE_DEGREE,
    )

    # Same meshed cells, same σ, only E differs — `TH-10` step 4's construction,
    # so the power error compares against its record and not a new definition.
    series_space = fem.functionspace(msh, ("Lagrange", 2, (3,)))
    e_series_fn = fem.Function(series_space, name="E_series")
    sphere_cells = np.asarray(
        cell_tags.indices[cell_tags.values == SPHERE_TAG], dtype=np.int32
    )
    e_series_fn.interpolate(_series_interior_interpolant(series), cells=sphere_cells)
    p_series = float(
        np.real(
            _integrate_over_sphere(
                0.5 * fields.sigma_field * ufl.inner(e_series_fn, e_series_fn),
                msh,
                cell_tags,
                comm,
                REFERENCE_QUADRATURE_DEGREE,
            )
        )
    )

    p_fem = float(np.real(p_fem_complex))
    peak, cap = _memory_peak_bytes()
    return {
        # `TH-12` step 3 (2026-08-19) reads the stored energies off this same
        # solve rather than re-running the fixture, so the solved fields are
        # handed back with the row.  Nothing in this file reads them, and no
        # recorded number moves: the addition is a new key on the returned
        # dict.
        "fields": fields,
        "degree": degree,
        "ncells": ncells,
        "n_dofs": n_dofs,
        "field_error": field_error,
        "p_fem": p_fem,
        "p_series": p_series,
        "power_error": abs(p_fem - p_series) / p_series,
        "power_imaginary": abs(float(np.imag(p_fem_complex))) / abs(p_fem),
        "solve_wall_s": solve_wall_s,
        "rss_peak": _rss_peak_bytes(comm),
        "memory_peak": peak,
        "memory_max": cap,
    }


@pytest.fixture(scope="module")
def degree_rows():
    """Both orders on the coarse rung, degree 1 first (the control)."""
    return {degree: _run_at_degree(degree) for degree in (1, 2)}


def _print_table(rows: dict) -> None:
    comm = MPI.COMM_WORLD
    if comm.rank != 0:
        return
    one = rows[1]
    two = rows[2]
    print(
        f"\n[TH-12 1] lossy saline sphere at 64 MHz, coarse rung "
        f"(h_sphere = {COARSE_RESOLUTION[0]:.5f}), N1curl degree 1 vs 2"
    )
    print(
        f"  degree-1 records gated against: interior relL2 "
        f"{DEGREE1_FINE_FIELD_RECORD:.3%} at {DEGREE1_FINE_CELLS} cells "
        f"(fine rung), coarse-rung power error "
        f"{DEGREE1_COARSE_POWER_RECORD:.3%}"
    )
    for row in (one, two):
        print(
            f"  degree {row['degree']}: {row['ncells']:6d} cells, "
            f"{row['n_dofs']:8d} DOFs, relL2 = {row['field_error']:.4%}, "
            f"power error = {row['power_error']:.4%}, "
            f"|Im P|/Re P = {row['power_imaginary']:.3e}, "
            f"solve wall = {row['solve_wall_s']:.2f} s, "
            f"peak RSS (summed over ranks) = "
            f"{row['rss_peak'] / 2**20:.1f} MiB"
        )
    print(
        f"  cgroup context: memory.peak = "
        f"{one['memory_peak'] / 2**30:.3f} GiB against memory.max = "
        f"{one['memory_max'] / 2**30:.2f} GiB — the container's *lifetime* "
        f"high-water mark, not this run's, and not resettable from here; the "
        f"per-run number is the RSS column above"
    )
    d_dofs = two["n_dofs"] / one["n_dofs"]
    print(
        f"  cost/accuracy per DOF: degree 2 costs {d_dofs:.2f}x the DOFs and "
        f"{two['solve_wall_s'] / one['solve_wall_s']:.2f}x the wall time of "
        f"degree 1 on the same {one['ncells']} cells, for "
        f"{one['field_error'] / two['field_error']:.2f}x the field accuracy; "
        f"against the degree-1 *fine* rung it is "
        f"{DEGREE1_FINE_CELLS / two['ncells']:.2f}x fewer cells at "
        f"{DEGREE1_FINE_FIELD_RECORD / two['field_error']:.2f}x the accuracy "
        f"(read by the weekly review, not gated here)"
    )


@complex_only
@pytest.mark.integration
def test_degree1_control_reproduces_the_recorded_coarse_rung_power_error(degree_rows):
    """Negative control: degree 1 on this rung is still the recorded 8.387%.

    Runs first (and the fixture solves in this order) so a degree-2 reading is
    never interpreted against an unpinned fixture.
    """
    _print_table(degree_rows)
    row = degree_rows[1]

    assert row["ncells"] == 5866, (
        f"the coarse rung meshed to {row['ncells']} cells, not the recorded "
        f"5 866 — the fixture moved under the record, so neither the control "
        f"below nor the degree-2 gate is comparing against what it names"
    )
    delta_pp = abs(row["power_error"] - DEGREE1_COARSE_POWER_RECORD) * 100.0
    assert delta_pp < CONTROL_TOLERANCE_PP, (
        f"degree 1 on the coarse rung reads {row['power_error']:.4%} ohmic-power "
        f"error against the recorded {DEGREE1_COARSE_POWER_RECORD:.3%} — a "
        f"{delta_pp:.4f} pp move, over the {CONTROL_TOLERANCE_PP} pp "
        f"reproduction band. The record was measured on this same fixture at "
        f"-n 2, so a drift here is a change in the fixture or the solver, and "
        f"it invalidates the degree-2 comparison before it is made"
    )
    assert row["power_imaginary"] < POWER_IMAGINARY_BOUND, (
        f"imaginary ohmic power at degree 1 is {row['power_imaginary']:.3e} of "
        f"the real part, over the {POWER_IMAGINARY_BOUND:.0e} family bound"
    )


@complex_only
@pytest.mark.integration
def test_degree2_beats_the_degree1_fine_rung_record_at_fewer_cells(degree_rows):
    """The gate: degree-2 relL2 ≤ 3.643% on 5 866 cells (record: 17 670)."""
    row = degree_rows[2]

    assert row["ncells"] < DEGREE1_FINE_CELLS, (
        f"degree 2 ran on {row['ncells']} cells against the record's "
        f"{DEGREE1_FINE_CELLS}: the gate is accuracy at *strictly fewer* cells "
        f"and this rung does not qualify"
    )
    assert row["power_imaginary"] < POWER_IMAGINARY_BOUND, (
        f"imaginary ohmic power at degree 2 is {row['power_imaginary']:.3e} of "
        f"the real part, over the {POWER_IMAGINARY_BOUND:.0e} family bound — a "
        f"conjugation slip in the degree-2 assembly would read exactly like "
        f"this, and it would also corrupt the field error above"
    )
    assert row["field_error"] <= DEGREE1_FINE_FIELD_RECORD, (
        f"degree 2 on {row['ncells']} cells reads {row['field_error']:.4%} "
        f"interior relL2, which does not beat the degree-1 fine-rung record "
        f"{DEGREE1_FINE_FIELD_RECORD:.3%} at {DEGREE1_FINE_CELLS} cells. Per "
        f"the §7 negative-result clause this is an answer, not a defect: "
        f"record it in the TH-12 entry and stop — no production-order change "
        f"is scopeable on it"
    )
