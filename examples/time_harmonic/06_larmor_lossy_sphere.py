"""Example (`EX-19`): the lossy saline sphere at the MRI Larmor frequencies.

The first example in this repository that **solves at 64 and 128 MHz** — the
1.5 T and 3 T proton Larmor frequencies this project exists for. Every earlier
time-harmonic example runs where the physics is easier: `EX-6` (`th:3`) sits at
``k₀R = 5e-3``, deep in the quasi-static limit, and `EX-3` imposes its field
rather than solving for it. `TH-10` closed that gap on 2026-08-13, and this
example is that capability made runnable.

The fixture is `TH-10`'s, **imported** from the module that closed it
(``tests/validation/test_lossy_sphere_fullwave.py``) rather than restated:
geometry (a = 0.05 m saline sphere in a 0.2 m box), material (εᵣ = 78,
σ = 0.5 S/m), the two rung ladders, the probe cloud, the ``LossySphereSeries``
reference, the ohmic-power machinery, and every bound. The example and the
landed gate therefore cannot drift apart — a change to the gate changes this
run's numbers, and the reproduction assertions below fail loudly when it does.

Why this regime is not a correction away from `EX-6`'s: at 64 MHz
``σ/(ωε₀) = 140`` dominates ``εᵣ = 78``, so ``ε_c = 78 − j140`` and
``|m|k₀a = 0.850`` (1.374 at 128 MHz). The quasi-static interior field
``3E₀/(ε_c+2)`` is not a nearby answer — it is off by 102.3% at 64 MHz and
154.6% at 128 MHz in max-norm (`TH-10` step 1). That gap is what makes the
solve falsifiable, and this example measures it in every run:

* *The anchors, reproduced digit-for-digit through the example path* — the
  fine-rung interior relative L2 against the series, **3.643%** at 64 MHz and
  **1.769%** at 128 MHz, at the gate's own unmoved 5% band; the quasi-static
  separations, **18.68×** and **59.16×**, against the gate's > 10× floor; and
  the SAR-relevant volume integral ½∫σ|E|², **3.629%** from the series integral
  over the same meshed cells. Records: ``20260813T093212Z_TH-10-step2-64mhz.log``,
  ``20260813T123211Z_TH-10-step3-128mhz.log``,
  ``20260813T170337Z_TH-10-step4-power.log``; the 128 MHz pair is the
  **0.11** re-record (1.826% / 57.31× on 0.7.2, moved with its mesh
  55 251 → 55 241), ``20260822T123746Z_OPS-18-step3-th10-rerun.log``.
* *The negative controls are executed here, not cited* — the quasi-static
  separations and the > 50% quasi-static power miss are computed on this run's
  own solved field, because they come from the imported fixture's own helpers.
  A solve that had merely reproduced `EX-6`'s physics fails them by
  construction.
* *Convergence, not a single level* — each frequency runs the gate's coarse
  rung as well, and the error must decrease with h. A level without a direction
  is a coincidence.

Scope, deliberately narrow: the interior field and the total ohmic power. **No
mass averaging, no C95.3 wording, no SAR claim, and nothing about a coil** —
`MAT-4` and `TH-11` own those, and this example inherits `TH-10`'s scope
exactly.

Run it through the example runner (the ``th:`` group sources the complex build
automatically; a real build raises)::

    ./run_examples.sh -e th:6 -n 2 -t 540

Output lands in ``examples/time_harmonic/paraview_output``: one combined XDMF
per frequency, ``larmor_sphere_64MHz_combined.xdmf`` and
``larmor_sphere_128MHz_combined.xdmf``. Colour by ``E_magnitude`` and the
saline ball is dark inside a bright box — but unlike `EX-6`'s uniform interior,
this one carries structure, and the 128 MHz picture carries more of it than the
64 MHz one. That is ``|m|k₀a`` growing from 0.850 to 1.374: the interior
wavelength is now comparable to the sphere.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel

# The gated fixture lives in the test that closed `TH-10`; the §9 `EX-19` item
# requires importing it rather than restating it. The runner puts only ``src``
# on PYTHONPATH, so the repo root goes on sys.path (same route `EX-6` takes).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.validation.test_lossy_sphere_fullwave import (  # noqa: E402
    BOX_HALF_WIDTH,
    FREQUENCY_64_HZ,
    FREQUENCY_128_HZ,
    INTERIOR_L2_BOUND,
    OHMIC_POWER_BOUND,
    QUASISTATIC_POWER_MISS_FLOOR,
    QUASISTATIC_SEPARATION,
    RESOLUTIONS_64,
    RESOLUTIONS_128,
    SALINE_EPSILON_R,
    SALINE_SIGMA,
    SPHERE_RADIUS,
    _exact_sphere_series_power,
    _interior_probe_points,
    _mesh_and_solve,
    _power_rung,
    _rel_l2,
    _series,
    _solve,
)

#: The `TH-10` records this example reproduces, all at the fine rung of the
#: gate's own ladder and all measured at ``-n 2`` on the logs named in the
#: module docstring. These are anchors, never targets: a run outside the band
#: below is a regression finding about the solver or the fixture, not a
#: tolerance question.
#:
#: **Version-tagged (2026-08-25, `EX-30` leg (th)).** The two 128 MHz constants
#: are the DolfinX **0.11** digits, re-recorded from `TH-10`'s own gate module
#: re-run on the 0.11 image (`OPS-18` step 3 attempt 1, green log
#: ``20260822T123746Z_OPS-18-step3-th10-rerun.log``: relL2 1.769%, separation
#: 59.16× at 55 241 cells). The 0.7.2 digits they replace — ``0.01826`` and
#: ``57.31``, measured on 55 251 cells — are history, not a target: the record
#: moved *with its mesh* at that re-record and this restated copy was never
#: updated, which is the example/gate divergence the `th:6` known-issues entry
#: documents. The 64 MHz constants are unchanged and reproduce to 4.04e-05 on
#: both images.
RECORD_INTERIOR_L2 = {FREQUENCY_64_HZ: 0.03643, FREQUENCY_128_HZ: 0.01769}
RECORD_SEPARATION = {FREQUENCY_64_HZ: 18.68, FREQUENCY_128_HZ: 59.16}
RECORD_COARSE_L2_64 = 0.08154
RECORD_POWER_ERROR = 0.03629
RECORD_POWER_QS_MISS = 0.581

#: Reproduction band on those records. The example runs the gate's own code on
#: the gate's own meshes at the gate's own rank count, so agreement to round-off
#: is what is expected; 1% relative allows for mesh-generator and Krylov
#: run-to-run noise (`MAG-13` rung 2 measured that class of noise directly)
#: while being far tighter than any physics change could hide behind — the
#: quasi-static answer this gate discriminates against is 100%+ away.
REPRODUCTION_BAND = 0.01

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"


def _interior_errors(series, fields, comm: MPI.Comm) -> tuple[float, float]:
    """``(relL2 vs series, relL2 vs quasi-static)`` on the imported probe cloud.

    The same measurement `TH-10`'s ``_solve`` makes, taken off a solve whose
    fields this example also exports — that is the only reason it is not simply
    a call to ``_solve``, which discards the fields it solved for. Everything
    physical (probe cloud, series, quasi-static closed form, the norm) is the
    fixture's; if this plumbing ever diverged from it, the reproduction
    assertions on ``RECORD_INTERIOR_L2`` would fail, which is what makes the
    duplication safe.
    """
    points = _interior_probe_points()
    real_values, valid_real = evaluate_vector_field_parallel(fields.e_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(fields.e_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(
            f"{int((~valid).sum())} interior probe points were not evaluated"
        )
    e_fem = np.real(real_values) + 1j * np.real(imag_values)

    e_series = series.internal_field(points)
    e_quasistatic = np.zeros_like(e_series)
    e_quasistatic[:, 0] = series.quasistatic_internal_field()
    return _rel_l2(e_fem, e_series), _rel_l2(e_fem, e_quasistatic)


def _paraview_fields(msh, fields):
    """CG1 ``E_real`` / ``E_imag`` / ``E_magnitude`` from the solved phasor.

    XDMF cannot carry N1curl, so the solution is interpolated once into a CG1
    vector space and split; ``|E|`` is the phasor magnitude taken on the array,
    so no complex ``sqrt`` is formed. Identical to `EX-6`'s export path.
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
        f"{label}: this run measured {measured:.6g} against the `TH-10` record "
        f"{record:.6g}, a drift of {drift:.2%} outside the "
        f"{REPRODUCTION_BAND:.0%} reproduction band. The example runs the gate's "
        f"own code on the gate's own mesh, so a drift this large means the "
        f"example path and the gate are no longer the same computation — that is "
        f"a finding about one of them, not a band to widen"
    )
    return drift


def _run_frequency(frequency_hz: float, resolutions, comm: MPI.Comm) -> dict:
    """One frequency: coarse rung, fine rung (kept for export), both gates."""
    series = _series(frequency_hz)
    label = f"{frequency_hz / 1e6:.0f} MHz"

    if comm.rank == 0:
        print(
            f"\n[{label}] eps_c = {series.epsilon_c:.6g}, m = {series.m:.6g}, "
            f"k0a = {series.size_parameter:.6g}, "
            f"|m|k0a = {abs(series.m) * series.size_parameter:.6g}, "
            f"series N = {series.n_terms}, "
            f"last-term bound = {series.last_term_bound():.3e}",
            flush=True,
        )

    started = time.perf_counter()
    err_coarse, qs_coarse, ncells_coarse = _solve(series, *resolutions[0])
    coarse_seconds = time.perf_counter() - started

    started = time.perf_counter()
    msh, cell_tags, fields, ncells_fine = _mesh_and_solve(series, *resolutions[-1])
    err_fine, qs_fine = _interior_errors(series, fields, comm)
    fine_seconds = time.perf_counter() - started
    separation = qs_fine / err_fine

    if comm.rank == 0:
        print(
            f"[{label}] h_sphere = {resolutions[0][0]:.5f} "
            f"({ncells_coarse:7d} cells, {coarse_seconds:.1f} s): "
            f"relL2(FEM vs series) = {err_coarse:.3%}, "
            f"separation from quasi-static = {qs_coarse / err_coarse:.2f}x"
            f"\n[{label}] h_sphere = {resolutions[-1][0]:.5f} "
            f"({ncells_fine:7d} cells, {fine_seconds:.1f} s): "
            f"relL2(FEM vs series) = {err_fine:.3%}, "
            f"relL2(FEM vs quasi-static) = {qs_fine:.3%}, "
            f"separation = {separation:.2f}x",
            flush=True,
        )

    # ---- the gate's own two assertions, on this run's field ------------------
    assert err_fine < err_coarse, (
        f"[{label}] refinement did not improve the interior field: "
        f"{err_coarse:.4%} -> {err_fine:.4%}; without a decreasing sequence the "
        f"level below is a coincidence, not convergence"
    )
    assert err_fine < INTERIOR_L2_BOUND, (
        f"[{label}] interior E differs from the full-wave series by "
        f"{err_fine:.2%} relL2, over the {INTERIOR_L2_BOUND:.0%} band `TH-10` "
        f"gates at. A miss near 170% is the conjugated-convention signature "
        f"(step 1: 173.8%), not a solver defect"
    )
    assert separation > QUASISTATIC_SEPARATION, (
        f"[{label}] the solve sits only {separation:.2f}x closer to the "
        f"full-wave series than to the quasi-static closed form (required > "
        f"{QUASISTATIC_SEPARATION:.0f}x) — it has not entered the Larmor regime, "
        f"and this example would be advertising `EX-6` physics at 64/128 MHz"
    )

    # ---- and the reproduction of the record it closed with -------------------
    drift_err = _check_record(
        f"[{label}] fine-rung interior relL2",
        err_fine,
        RECORD_INTERIOR_L2[frequency_hz],
    )
    drift_sep = _check_record(
        f"[{label}] fine-rung quasi-static separation",
        separation,
        RECORD_SEPARATION[frequency_hz],
    )
    if comm.rank == 0:
        print(
            f"[{label}] vs the TH-10 record: relL2 {err_fine:.3%} against "
            f"{RECORD_INTERIOR_L2[frequency_hz]:.3%} (drift {drift_err:.2e}), "
            f"separation {separation:.2f}x against "
            f"{RECORD_SEPARATION[frequency_hz]:.2f}x (drift {drift_sep:.2e}) — "
            f"band {REPRODUCTION_BAND:.0%}",
            flush=True,
        )

    return {
        "series": series,
        "label": label,
        "msh": msh,
        "cell_tags": cell_tags,
        "fields": fields,
        "err_coarse": err_coarse,
        "err_fine": err_fine,
        "separation": separation,
        "ncells_fine": ncells_fine,
    }


def _export(result: dict, comm: MPI.Comm) -> Path:
    """Combined XDMF of the fine-rung field, in and around the sphere."""
    e_re, e_im, e_mag = _paraview_fields(result["msh"], result["fields"])
    OUTPUT_DIR.mkdir(exist_ok=True)
    basename = f"larmor_sphere_{result['label'].replace(' ', '')}_combined"
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / basename,
        result["msh"],
        result["cell_tags"],
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
        print("EX-19 — lossy saline sphere at the MRI Larmor frequencies")
        print("=" * 72)
        print(
            f"\n[geometry] sphere a = {SPHERE_RADIUS} m inside a "
            f"{2 * BOX_HALF_WIDTH} m box; the full-wave series total field is "
            f"Dirichlet data on the wall, the interior is the solver's output"
            f"\n[material] eps_r = {SALINE_EPSILON_R}, "
            f"sigma = {SALINE_SIGMA} S/m — gelled saline, lossy"
            f"\n[regime] 64 MHz (1.5 T) and 128 MHz (3 T); quasi-statics misses "
            f"the interior field by 102.3% and 154.6% in max-norm (TH-10 step 1), "
            f"so this is a different answer, not a correction to EX-6's"
            f"\n[fixture] imported wholesale from "
            f"tests/validation/test_lossy_sphere_fullwave.py — geometry, "
            f"materials, rungs, probe cloud, series and every bound",
            flush=True,
        )

    results = [
        _run_frequency(FREQUENCY_64_HZ, RESOLUTIONS_64, comm),
        _run_frequency(FREQUENCY_128_HZ, RESOLUTIONS_128, comm),
    ]

    _check_record(
        "[64 MHz] coarse-rung interior relL2", results[0]["err_coarse"], RECORD_COARSE_L2_64
    )

    # ---- the SAR-relevant volume integral, at 64 MHz -------------------------
    #
    # `TH-10` step 4's gate: ½∫σ|E|² over the sphere against the series field
    # integrated over the *same* meshed cells with the *same* σ, so only E
    # differs. Run at the fine rung only — that is the rung the gate asserts on
    # and the rung the record quotes; the coarse rung would cost a fourth solve
    # to reprint a number the gate does not gate.
    power_started = time.perf_counter()
    rung = _power_rung(results[0]["series"], *RESOLUTIONS_64[-1])
    power_seconds = time.perf_counter() - power_started
    power_error = abs(rung["p_fem"] - rung["p_series"]) / rung["p_series"]
    qs_miss = abs(rung["p_quasistatic"] - rung["p_series"]) / rung["p_series"]
    p_exact_ball = _exact_sphere_series_power(
        results[0]["series"], SALINE_SIGMA, n_radial=24
    )

    if comm.rank == 0:
        print(
            f"\n[power 64 MHz] fine rung ({rung['ncells']} cells, "
            f"{power_seconds:.1f} s): P_FEM = {rung['p_fem']:.9e} W vs "
            f"P_series(meshed) = {rung['p_series']:.9e} W => "
            f"{power_error:.3%} (band {OHMIC_POWER_BOUND:.0%}, record "
            f"{RECORD_POWER_ERROR:.3%})"
            f"\n[power 64 MHz] negative control: the quasi-static uniform-field "
            f"route gives {rung['p_quasistatic']:.9e} W, a miss of "
            f"{qs_miss:.3%} (floor {QUASISTATIC_POWER_MISS_FLOOR:.0%}, record "
            f"{RECORD_POWER_QS_MISS:.1%}) — quasi-statics cannot produce this "
            f"integral, so the band above is discriminating"
            f"\n[power 64 MHz] geometry, read not gated: the meshed sphere "
            f"carries {rung['p_series'] / p_exact_ball:.6f} of the exact-ball "
            f"series power {p_exact_ball:.9e} W (numpy Gauss product quadrature, "
            f"independent of dolfinx)"
            f"\n[scope] this is the volume integral a SAR number routes through, "
            f"and nothing more: no mass averaging, no C95.3 wording, no coil",
            flush=True,
        )

    assert power_error < OHMIC_POWER_BOUND, (
        f"total ohmic power from the FEM solve is {rung['p_fem']:.6e} W against "
        f"the series integral {rung['p_series']:.6e} W over the same meshed "
        f"sphere — off by {power_error:.2%}, outside `TH-10`'s "
        f"{OHMIC_POWER_BOUND:.0%} band"
    )
    assert qs_miss > QUASISTATIC_POWER_MISS_FLOOR, (
        f"the quasi-static power route misses by only {qs_miss:.2%}, under the "
        f"{QUASISTATIC_POWER_MISS_FLOOR:.0%} floor — if quasi-statics can "
        f"reproduce this integral, the gate above is not discriminating"
    )
    _check_record("[power 64 MHz] ohmic-power error", power_error, RECORD_POWER_ERROR)
    _check_record(
        "[power 64 MHz] quasi-static miss", qs_miss, RECORD_POWER_QS_MISS
    )

    # ---- ParaView -----------------------------------------------------------
    paths = [_export(result, comm) for result in results]

    if comm.rank == 0:
        for result, path in zip(results, paths):
            print(f"\n[paraview] wrote {path} ({result['ncells_fine']} cells)")
        print(
            f"[paraview] colour by `E_magnitude` and `Threshold` on `CellTags` "
            f"(1 = sphere, 2 = surrounding box) to isolate the saline. Unlike "
            f"`EX-6`'s uniform interior, this one has structure, and the 128 MHz "
            f"file has more of it than the 64 MHz one — |m|k0a grows 0.850 -> "
            f"1.374, so the interior wavelength approaches the sphere."
            f"\n\nAll assertions hold, both Larmor frequencies. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
