"""Example (`EX-25`): element order as an accuracy knob — degree 1 vs degree 2.

Every other example in this repository solves at **element order 1**. That is
not a physics choice, it is a habit: ``TimeHarmonicSolver(problem, degree=2)``
has existed since `TH-1` and was first gated on 2026-08-18 (`TH-12` step 1).
This example is that capability made runnable — the **discretization** angle no
other example covers.

The fixture is `TH-10`'s lossy saline sphere at 64 MHz, on the **coarse** rung
of its own ladder (5 866 cells), **imported** from the gate that closed it
(``tests/validation/test_lossy_sphere_degree2.py`` and, through it,
``tests/validation/test_lossy_sphere_fullwave.py``) rather than restated:
geometry, material, the rung, the probe cloud, the ``LossySphereSeries``
reference, the ohmic-power machinery, the degree-1 records and every bound.
One run solves that **same mesh twice**, once at each order, and prints the
side-by-side table `TH-12` reads its cost model off.

What the run demonstrates, and asserts:

* *Second order is not a small correction here.* On the same 5 866 cells the
  interior relative L2 against the series falls **8.1541% → 0.1405%** and the
  ohmic-power error **8.3869% → 0.0058%**. The ohmic power is the integral a
  SAR number routes through, so this is the accuracy axis the MRI slice cares
  about — measured, not argued.
* *The negative control is the capability statement.* Degree 1 on this rung is
  asserted to **miss** the degree-1 *fine*-rung record (3.643% at 17 670 cells)
  while degree 2 on the **same coarse mesh** is asserted to beat it — the
  `EX-18` inverted-assertion pattern. Degree 2 reaching a finer mesh's accuracy
  at 3.01× fewer cells is exactly what `TH-12` step 1 gated, re-executed here.
* *And it costs something.* 7 591 → 39 634 DOFs (5.22×), and the solve wall and
  summed peak RSS are printed beside them. Both grow **sublinearly in DOFs** on
  this fixture — which is the good case, and emphatically not what `TH-12`
  step 2 measured on the coil (~20× the wall for 5.42× the DOFs, at 96.8% of
  the container's memory cap).

Scope, deliberately narrow: the sphere fixture, one frequency, one rung.
**No production-order claim** — that decision belongs to the weekly review per
`TH-12`'s decision clause — and no coil, no mass averaging, no SAR wording.
The degree-2 complex-power identity defect `TH-12` step 2 found on the *coil*
does not arise here: this fixture has no driven port, so the identity that
family gates is not defined on it (see the `TH-12` step-1 module docstring).

Run it through the example runner (the ``th:`` group sources the complex build
automatically; a real build raises)::

    ./run_examples.sh -e th:7 -n 2 -t 400

Output lands in ``examples/time_harmonic/paraview_output``: one combined XDMF
per order, ``element_order_sphere_degree1_combined.xdmf`` and
``element_order_sphere_degree2_combined.xdmf``, on the identical mesh. In the
complex build the XDMF writer splits every attribute into ``real_<name>`` /
``imag_<name>`` (correct writer behaviour — see the `OPS-21` known-issues
entry), so in ParaView the fields are ``real_E_magnitude``, ``real_E_real``,
``imag_E_imag`` and so on. Colour by ``real_E_magnitude``, ``Threshold`` on
``real_CellTags`` (1 = sphere, 2 = box), and open the two files side by side:
the degree-2 interior is the smooth answer, the degree-1 one carries the 8%
error as visible faceting on the same tetrahedra.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel

# The gated fixture lives in the tests that closed `TH-10`/`TH-12` step 1; the
# §7 `EX-25` entry requires importing it rather than restating it. The runner
# puts only ``src`` on PYTHONPATH, so the repo root goes on sys.path (the route
# `EX-19` takes).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.validation.test_lossy_sphere_degree2 import (  # noqa: E402
    COARSE_RESOLUTION,
    DEGREE1_COARSE_POWER_RECORD,
    DEGREE1_FINE_CELLS,
    DEGREE1_FINE_FIELD_RECORD,
    POWER_IMAGINARY_BOUND,
    _rss_peak_bytes,
)
from tests.validation.test_lossy_sphere_fullwave import (  # noqa: E402
    BOX_HALF_WIDTH,
    FREQUENCY_64_HZ,
    REFERENCE_QUADRATURE_DEGREE,
    SALINE_EPSILON_R,
    SALINE_SIGMA,
    SPHERE_RADIUS,
    _integrate_over_sphere,
    _interior_probe_points,
    _mesh_and_solve,
    _rel_l2,
    _series,
    series_interior_function,
)

#: The `TH-12` step-1 records this example reproduces, measured at ``-n 2`` on
#: ``20260818T110442Z_TH-12-step1-sphere-degree2-rss.log``. The degree-1 power
#: error is *imported* (the gate holds it as
#: ``DEGREE1_COARSE_POWER_RECORD``); the other three are held here because the
#: gate asserts on them only through its own printed table. Anchors, never
#: targets: a run outside the band below is a finding about the example path or
#: the solver, not a tolerance question.
RECORD_FIELD_ERROR = {1: 0.081541, 2: 0.001405}
RECORD_POWER_ERROR = {1: DEGREE1_COARSE_POWER_RECORD, 2: 0.000058}

#: Global DOF counts of the two N1curl spaces on this mesh. Deterministic given
#: the mesh and the order — asserted exactly, not banded.
RECORD_DOFS = {1: 7591, 2: 39634}

#: Cell count of the coarse rung. The gate holds it as an inline literal
#: (``test_lossy_sphere_degree2.py`` line 298) rather than a named constant, so
#: it is restated here unloosened and asserted, not merely printed.
COARSE_CELLS = 5866

#: Reproduction band on those records — the `EX-19` precedent, unchanged. The
#: example runs the gate's own fixture on the gate's own mesh at the gate's own
#: rank count, so agreement to round-off is what is expected; 1% relative allows
#: for mesh-generator and Krylov run-to-run noise while being far tighter than
#: any physics change could hide behind (the two orders are 58× apart).
REPRODUCTION_BAND = 0.01

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"


def _row_and_fields(degree: int, comm: MPI.Comm) -> dict:
    """One solve of the coarse rung at ``degree``: the measured row *and* the
    solved fields.

    This is `TH-12` step 1's ``_run_at_degree`` with the mesh and fields kept
    instead of discarded — the example exports them to ParaView, which that
    helper cannot do because it returns only scalars. Everything physical (the
    rung, the series, the probe cloud, the norm, the power construction and its
    quadrature degree) is the gate's own, imported; the duplication is
    plumbing, and the reproduction assertions on ``RECORD_FIELD_ERROR`` /
    ``RECORD_POWER_ERROR`` fail loudly if it ever drifts from the gate, which is
    what makes it safe (the `EX-19` argument, same shape).
    """
    series = _series(FREQUENCY_64_HZ)

    started = time.perf_counter()
    msh, cell_tags, fields, ncells = _mesh_and_solve(
        series, COARSE_RESOLUTION[0], COARSE_RESOLUTION[1], degree=degree
    )
    # Barrier before stopping the clock: the ranks leave the solve at different
    # times and a rank-local wall time is not a cost number.
    comm.Barrier()
    solve_wall_s = time.perf_counter() - started

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
    # identity below (`½σE·Ē` is real by construction — ``ufl.inner``
    # conjugates its second argument — so |Im P|/Re P is round-off, and a
    # conjugation slip in the degree-2 assembly reads exactly like a nonzero).
    p_fem_complex = _integrate_over_sphere(
        0.5 * fields.sigma_field * ufl.inner(fields.e_complex, fields.e_complex),
        msh,
        cell_tags,
        comm,
        REFERENCE_QUADRATURE_DEGREE,
    )

    # Same meshed cells, same σ, only E differs — `TH-10` step 4's construction,
    # so the power error compares against its record and not a new definition.
    # `OPS-25`: imported, not re-derived. The private copy that used to live
    # here rotted independently of the gate across the 0.11 migration.
    e_series_fn = series_interior_function(series, msh, cell_tags)
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
    return {
        "degree": degree,
        "msh": msh,
        "cell_tags": cell_tags,
        "fields": fields,
        "ncells": ncells,
        "n_dofs": n_dofs,
        "field_error": field_error,
        "power_error": abs(p_fem - p_series) / p_series,
        "power_imaginary": abs(float(np.imag(p_fem_complex))) / abs(p_fem),
        "solve_wall_s": solve_wall_s,
        "rss_peak": _rss_peak_bytes(comm),
    }


def _paraview_fields(msh, fields):
    """CG1 ``E_real`` / ``E_imag`` / ``E_magnitude`` from the solved phasor.

    XDMF cannot carry N1curl at any order, so the solution is interpolated once
    into a CG1 vector space and split; ``|E|`` is the phasor magnitude taken on
    the array, so no complex ``sqrt`` is formed. `EX-19`'s export path, and
    note that it makes the two orders directly comparable in ParaView: both
    land on the same CG1 space over the same 5 866 cells, so the difference in
    the picture is the difference in the solution.
    """
    v_cg = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    e_cg = fem.Function(v_cg, name="E_phasor")
    e_cg.interpolate(fields.e_complex)
    e_cg.x.scatter_forward()

    e_re = fem.Function(v_cg, name="E_real")
    e_re.x.array[:] = np.real(e_cg.x.array)
    e_im = fem.Function(v_cg, name="E_imag")
    e_im.x.array[:] = np.imag(e_cg.x.array)

    s_cg = fem.functionspace(msh, ("Lagrange", 1))
    e_mag = fem.Function(s_cg, name="E_magnitude")
    components = np.abs(e_cg.x.array.reshape(-1, 3))
    e_mag.x.array[:] = np.sqrt(np.sum(components * components, axis=1))

    for f in (e_re, e_im, e_mag):
        f.x.scatter_forward()
    return e_re, e_im, e_mag


def _check_record(label: str, measured: float, record: float) -> float:
    """Relative distance from the record, asserted inside ``REPRODUCTION_BAND``."""
    drift = abs(measured - record) / record
    assert drift < REPRODUCTION_BAND, (
        f"{label}: this run measured {measured:.6g} against the `TH-12` step-1 "
        f"record {record:.6g}, a drift of {drift:.2%} outside the "
        f"{REPRODUCTION_BAND:.0%} reproduction band. The example runs the gate's "
        f"own fixture on the gate's own mesh, so a drift this large means the "
        f"example path and the gate are no longer the same computation — that is "
        f"a finding about one of them, not a band to widen"
    )
    return drift


def _export(row: dict, comm: MPI.Comm) -> Path:
    """Combined XDMF of one order's solved field, in and around the sphere."""
    e_re, e_im, e_mag = _paraview_fields(row["msh"], row["fields"])
    OUTPUT_DIR.mkdir(exist_ok=True)
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"element_order_sphere_degree{row['degree']}_combined",
        row["msh"],
        row["cell_tags"],
        {"E_real": e_re, "E_imag": e_im, "E_magnitude": e_mag},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return xdmf_path


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "this example needs the complex DolfinX build "
            "(source /usr/local/bin/dolfinx-complex-mode); the runner's `th:` "
            "group sources it automatically"
        )

    if comm.rank == 0:
        print("=" * 72)
        print("EX-25 — element order as an accuracy knob: N1curl degree 1 vs 2")
        print("=" * 72)
        print(
            f"\n[geometry] sphere a = {SPHERE_RADIUS} m inside a "
            f"{2 * BOX_HALF_WIDTH} m box; the full-wave series total field is "
            f"Dirichlet data on the wall, the interior is the solver's output"
            f"\n[material] eps_r = {SALINE_EPSILON_R}, "
            f"sigma = {SALINE_SIGMA} S/m — gelled saline, lossy"
            f"\n[rung] the COARSE rung of TH-10's own 64 MHz ladder, "
            f"h_sphere = {COARSE_RESOLUTION[0]:.5f} — the same mesh at both "
            f"orders, so the only thing that changes below is the element"
            f"\n[fixture] imported wholesale from "
            f"tests/validation/test_lossy_sphere_degree2.py and the TH-10 "
            f"module it builds on — rung, probe cloud, series, power "
            f"machinery, degree-1 records and every bound",
            flush=True,
        )

    # Degree 1 first: it is the control, and a degree-2 reading should never be
    # interpreted against an unpinned fixture (the gate solves in this order too).
    rows = {degree: _row_and_fields(degree, comm) for degree in (1, 2)}
    one, two = rows[1], rows[2]

    # ---- the side-by-side table, the TH-12 deliverable shape -----------------
    if comm.rank == 0:
        print(
            f"\n[table] lossy saline sphere at {FREQUENCY_64_HZ / 1e6:.0f} MHz, "
            f"{one['ncells']} cells, N1curl degree 1 vs 2"
        )
        header = (
            f"  {'order':>5}  {'cells':>6}  {'DOFs':>7}  {'relL2':>9}  "
            f"{'power err':>9}  {'|ImP|/ReP':>10}  {'solve s':>8}  "
            f"{'peak RSS':>10}"
        )
        print(header)
        for row in (one, two):
            print(
                f"  {row['degree']:>5d}  {row['ncells']:>6d}  "
                f"{row['n_dofs']:>7d}  {row['field_error']:>8.4%}  "
                f"{row['power_error']:>8.4%}  {row['power_imaginary']:>10.3e}  "
                f"{row['solve_wall_s']:>8.2f}  "
                f"{row['rss_peak'] / 2**20:>7.1f} MiB"
            )
        print(
            f"  (peak RSS is summed ru_maxrss over ranks, not "
            f"/sys/fs/cgroup/memory.peak — that file is a container-lifetime "
            f"high-water mark and is not resettable from inside a run; TH-12 "
            f"step 1's instrument note)"
        )
        print(
            f"\n[cost] degree 2 buys {one['field_error'] / two['field_error']:.1f}x "
            f"the field accuracy and "
            f"{one['power_error'] / two['power_error']:.0f}x the power accuracy "
            f"for {two['n_dofs'] / one['n_dofs']:.2f}x the DOFs, "
            f"{two['solve_wall_s'] / one['solve_wall_s']:.2f}x the solve wall "
            f"and {two['rss_peak'] / one['rss_peak']:.2f}x the peak RSS — "
            f"sublinear in DOFs on both cost axes here. That is *this* fixture: "
            f"TH-12 step 2 measured ~20x the wall for 5.42x the DOFs on the "
            f"coil, at 96.8% of the container memory cap. No production-order "
            f"claim is made here (TH-12's decision clause is the weekly "
            f"review's)",
            flush=True,
        )

    # ---- the fixture is the one the records name ----------------------------
    for row in (one, two):
        assert row["ncells"] == COARSE_CELLS, (
            f"the coarse rung meshed to {row['ncells']} cells at degree "
            f"{row['degree']}, not the recorded {COARSE_CELLS} — the fixture "
            f"moved under the records, so nothing below is comparing against "
            f"what it names"
        )
        assert row["n_dofs"] == RECORD_DOFS[row["degree"]], (
            f"degree {row['degree']} built {row['n_dofs']} global N1curl DOFs "
            f"against the recorded {RECORD_DOFS[row['degree']]}; the DOF count "
            f"is deterministic given mesh and order, so a move here means the "
            f"space is not the one TH-12 step 1 priced"
        )
        assert row["power_imaginary"] < POWER_IMAGINARY_BOUND, (
            f"imaginary ohmic power at degree {row['degree']} is "
            f"{row['power_imaginary']:.3e} of the real part, over the "
            f"{POWER_IMAGINARY_BOUND:.0e} family bound — a conjugation slip in "
            f"the assembled form reads exactly like this, and it would also "
            f"corrupt the field error above"
        )

    # ---- the negative control: the EX-18 inverted assertion ------------------
    #
    # This pair *is* the §5.4 capability statement. Degree 1 on this rung must
    # miss the degree-1 fine-rung record while degree 2 on the same cells beats
    # it — without the miss, "degree 2 reaches fine-rung accuracy coarsely"
    # would be indistinguishable from "this rung was always that good".
    assert one["field_error"] > DEGREE1_FINE_FIELD_RECORD, (
        f"degree 1 on {one['ncells']} cells reads {one['field_error']:.4%} "
        f"interior relL2, which already meets the degree-1 *fine*-rung record "
        f"{DEGREE1_FINE_FIELD_RECORD:.3%} at {DEGREE1_FINE_CELLS} cells — the "
        f"control has stopped discriminating and the degree-2 result below "
        f"claims nothing"
    )
    assert two["ncells"] < DEGREE1_FINE_CELLS, (
        f"degree 2 ran on {two['ncells']} cells against the record's "
        f"{DEGREE1_FINE_CELLS}: the claim is accuracy at *strictly fewer* cells "
        f"and this rung does not qualify"
    )
    assert two["field_error"] <= DEGREE1_FINE_FIELD_RECORD, (
        f"degree 2 on {two['ncells']} cells reads {two['field_error']:.4%} "
        f"interior relL2, which does not beat the degree-1 fine-rung record "
        f"{DEGREE1_FINE_FIELD_RECORD:.3%} at {DEGREE1_FINE_CELLS} cells — the "
        f"capability this example exists to demonstrate (TH-12 step 1's gate) "
        f"has regressed"
    )

    # ---- and the reproduction of the records step 1 closed with --------------
    drifts = {}
    for degree in (1, 2):
        drifts[(degree, "relL2")] = _check_record(
            f"[degree {degree}] interior relL2",
            rows[degree]["field_error"],
            RECORD_FIELD_ERROR[degree],
        )
        drifts[(degree, "power")] = _check_record(
            f"[degree {degree}] ohmic-power error",
            rows[degree]["power_error"],
            RECORD_POWER_ERROR[degree],
        )

    if comm.rank == 0:
        print(
            f"\n[control] degree 1 misses the degree-1 fine-rung record "
            f"({one['field_error']:.4%} > {DEGREE1_FINE_FIELD_RECORD:.3%} at "
            f"{DEGREE1_FINE_CELLS} cells) while degree 2 beats it on "
            f"{two['ncells']} cells ({two['field_error']:.4%}) — "
            f"{DEGREE1_FINE_CELLS / two['ncells']:.2f}x fewer cells at "
            f"{DEGREE1_FINE_FIELD_RECORD / two['field_error']:.1f}x the accuracy"
        )
        for degree in (1, 2):
            print(
                f"[record] degree {degree}: relL2 "
                f"{rows[degree]['field_error']:.4%} vs "
                f"{RECORD_FIELD_ERROR[degree]:.4%} "
                f"(drift {drifts[(degree, 'relL2')]:.2e}), power error "
                f"{rows[degree]['power_error']:.4%} vs "
                f"{RECORD_POWER_ERROR[degree]:.4%} "
                f"(drift {drifts[(degree, 'power')]:.2e}) — band "
                f"{REPRODUCTION_BAND:.0%}"
            )
        print(
            f"[identity] |Im P|/Re P = {one['power_imaginary']:.3e} (degree 1) "
            f"and {two['power_imaginary']:.3e} (degree 2), both under the "
            f"{POWER_IMAGINARY_BOUND:.0e} family bound: the ohmic integrand "
            f"1/2 sigma E.conj(E) is real by construction at either order",
            flush=True,
        )

    # ---- ParaView -----------------------------------------------------------
    paths = [_export(rows[degree], comm) for degree in (1, 2)]

    if comm.rank == 0:
        for degree, path in zip((1, 2), paths):
            print(f"\n[paraview] wrote {path} (degree {degree}, "
                  f"{rows[degree]['ncells']} cells)")
        print(
            f"[paraview] the complex build's XDMF writer splits attributes into "
            f"`real_*`/`imag_*` (correct behaviour, OPS-21 known-issues entry), "
            f"so colour by `real_E_magnitude` and `Threshold` on `real_CellTags` "
            f"(1 = sphere, 2 = box). Open both files together: same tetrahedra, "
            f"same CG1 output space, and the degree-1 interior carries its 8% "
            f"error as faceting the degree-2 one does not have."
            f"\n\nAll assertions hold at both orders. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
