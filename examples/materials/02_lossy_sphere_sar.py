"""Example (`EX-52`): imposed-field SAR on the lossy sphere, against its
closed form, in ParaView.

`MAT-4` step 1 (2026-08-03) gates mean SAR in a lossy sphere on an **imposed
uniform field** against the quasi-static closed form
``SAR = sigma|3E0/(eps_c+2)|^2/(2 rho)`` at 64 MHz — to a 10% bound whose own
floor is the closed form's own O((k_in R)^2) retardation error, not a fitted
mesh tolerance. Nothing under ``examples/`` shows this angle: `th:6` shows the
lossy plane wave, `mri:2` shows the *mass-averaging operator* on an imposed
field with no closed-form SAR target, `ports:9` shows coil-driven quadrant
powers with no closed form at all. This example is the missing member of
Phase 3's SAR ramp — the imposed-field-vs-closed-form angle — named by the
2026-09-06 weekly review's audit of that ramp.

**Imposed uniform field via a solved sphere-in-box problem, no coil, no mass
averaging, no Larmor-coil claim.** The field is not literally imposed the way
`mri:2` imposes it: this reruns the `MAT-4` step 1 fixture itself (the
exterior uniform + dipole boundary condition, solved to get the interior
field) because that is the gate this example demonstrates. What is *not* here
is a coil, a phantom, or mass averaging — those are `mri:2`, `ports:9`, and
`mri:2`/`mat:4` respectively, and none of their claims are made here.

**Import, never restate.** Every constant, mesh resolution, closed form and
solve is imported from ``tests/validation/test_lossy_sphere_sar.py`` — the
module that closed `MAT-4` step 1 — so this example and that gate cannot
drift apart. The one change to that module is additive and disclosed: a
``return_fields`` keyword on ``_solve_lossy_sphere`` (default ``False``,
existing callers unaffected) that hands back the mesh/cell_tags/fields the
existing return dict does not carry, needed here to write ParaView output.
The gate module itself is re-run through the harness in the same slot.

**Anchors (asserted, the gate module's own bands):**

* mean SAR vs the closed form at both `SIGMA_LOW` and `SIGMA_HIGH`, at the
  fine mesh rung only (`SPHERE_RADIUS/10`, `SPHERE_RADIUS/5`), inside the
  module's own 10% bound. The module's own printed record for these two
  numbers is 3.42% / 3.54% (a plan figure, not a module constant) — this
  example reproduces to the printed digits and asserts only the imported
  10% bound, never the plan figures themselves.
* interior `E_z` spread < 0.02 inside 0.55 R (module's own bound).
* `Im/Re E_z` vs `t/(eps_r+2)` within 10% (module's own bound).

**Negative controls, both asserted:**

1. The two-sigma ratio `SAR2/SAR1` separates from the sigma-blind ratio
   `sigma2/sigma1` by >= 3x (the module's own bound, backed by
   `20260803T020448Z_MAT-4-step1-gate.log`); the ceiling
   ``((eps_r+2)^2+t2^2)/((eps_r+2)^2+t1^2) = 4.86`` is the module's own
   arithmetic and is printed alongside, never asserted (it is a ceiling, not
   a floor).
2. A third, sigma=0 (vacuum) solve on the same fixture: `dissipated_power_w`
   is exactly `0.0` and mean SAR <= 1e-12 — exact, because with sigma
   identically zero cell by cell the integrand is zero cell by cell.

**Writes** one combined XDMF
(``materials_02_lossy_sphere_sar_combined.xdmf``): the pointwise SAR
``sigma|E|^2/(2 rho)`` from ``post.sar.point_sar`` (at cell centroids, so it
renders as a DG0 field) at ``sigma = SIGMA_HIGH``, named ``SAR_pointwise``,
and the closed-form uniform SAR as a constant DG0 field on the sphere cells
only, named ``SAR_closed_form`` — two distinct arrays so ParaView can show the
FEM field against the flat closed form (`Clip` through y=0). `CellTags`
carried through `write_xdmf_with_tags`.

Run it through the example runner (the ``mat:`` group sources the complex
build automatically)::

    ./run_examples.sh -e mat:2

**Traps already paid for:** ``ufl.real`` is not needed here (no non-zero
centre comparison — that is `mri:2`'s trap); ``point_sar`` takes
``e_real``/``e_imag``, not ``e_complex``; two arrays need two distinct
``name``s in the XDMF; full-filename guide references; census ``exit != 1``
(exit 2 is staleness info).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

import dolfinx
from dolfinx import default_scalar_type, fem

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.sar import point_sar, uniform_sphere_sar_closed_form  # noqa: E402

from tests.validation.test_lossy_sphere_sar import (  # noqa: E402
    BOX_HALF_WIDTH,
    E0,
    EPSILON_R_SPHERE,
    FREQUENCY_HZ,
    OMEGA,
    RHO_KG_M3,
    SIGMA_HIGH,
    SIGMA_LOW,
    SPHERE_RADIUS,
    SPHERE_TAG,
    _interior_field_closed_form,
    _k_in_r,
    _solve_lossy_sphere,
)
from fem_em_solver.utils.constants import EPSILON_0  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "materials_02_lossy_sphere_sar_combined"

#: The fine mesh rung only, per the §9 item — the coarse rung exists in the
#: gate to demonstrate refinement, which is not this example's job.
RESOLUTION_SPHERE = SPHERE_RADIUS / 10.0
RESOLUTION_FAR = SPHERE_RADIUS / 5.0

#: The gate's own 10% mean-SAR bound (`MAT-4` step 1,
#: `test_lossy_sphere_sar.py::test_lossy_sphere_mean_sar_matches_closed_form`).
MEAN_SAR_RTOL = 0.10
#: The gate's own interior-uniformity bound.
EZ_SPREAD_BOUND = 0.02
#: The gate's own Im/Re phase-ratio bound.
PHASE_RATIO_RTOL = 0.10
#: The gate's own two-sigma separation floor.
SEPARATION_FLOOR = 3.0

#: §7 plan record for the printed mean-SAR errors at the fine rung — a plan
#: figure, reproduced to the printed digits, never asserted as a band.
PLAN_RECORD_ERROR_LOW_PCT = 3.42
PLAN_RECORD_ERROR_HIGH_PCT = 3.54


def _build_dg0_sar_fields(fields_high, closed_high_sar):
    """The two named DG0 arrays this example writes: pointwise SAR and the
    closed-form constant, both on the SIGMA_HIGH solve's mesh/cell_tags."""
    msh = fields_high["mesh"]
    cell_tags = fields_high["cell_tags"]
    comm = msh.comm

    num_cells_local = msh.topology.index_map(msh.topology.dim).size_local
    cells = np.arange(num_cells_local, dtype=np.int32)
    centroids = dolfinx.mesh.compute_midpoints(msh, msh.topology.dim, cells)

    # `evaluate_vector_field_parallel` (and so `point_sar`) is a COLLECTIVE over
    # a point list that must be identical on every rank: it sizes its output by
    # the caller's `points` and scatters each rank's hits into it by index.
    # Handing each rank only its own local centroids therefore indexes rank 0's
    # buffer with rank 1's indices -- `IndexError: index 36378 is out of bounds`
    # at `-n 2` (20260907T033551Z_EX-52.log). Concatenate the owned centroids in
    # rank order, evaluate once on that global list, and slice the owned segment
    # back out.
    gathered = comm.allgather(centroids)
    global_points = (
        np.vstack(gathered) if len(gathered) > 1 else np.atleast_2d(gathered[0])
    )
    offset = int(sum(chunk.shape[0] for chunk in gathered[: comm.rank]))

    # point_sar takes e_real/e_imag, NOT e_complex.
    sar_global = point_sar(
        fields_high["e_real"],
        fields_high["e_imag"],
        global_points,
        sigma=SIGMA_HIGH,
        rho=RHO_KG_M3,
        comm=comm,
    )
    sar_values = sar_global[offset : offset + num_cells_local]

    dg0 = fem.functionspace(msh, ("DG", 0))
    sar_pointwise = fem.Function(dg0, name="SAR_pointwise")
    sar_pointwise.x.array[:num_cells_local] = sar_values
    sar_pointwise.x.scatter_forward()

    sar_closed_form = fem.Function(dg0, name="SAR_closed_form")
    sar_closed_form.x.array[:] = 0.0
    sphere_cells = cell_tags.indices[cell_tags.values == SPHERE_TAG]
    for cell in sphere_cells:
        sar_closed_form.x.array[dg0.dofmap.cell_dofs(int(cell))] = closed_high_sar

    sar_closed_form.x.scatter_forward()
    return sar_pointwise, sar_closed_form


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "this example needs the complex DolfinX build "
            "(source /usr/local/bin/dolfinx-complex-mode); the runner's `mat:` "
            "group sources it automatically"
        )

    if comm.rank == 0:
        print("=" * 72)
        print("EX-52 -- imposed-field SAR on the lossy sphere vs its closed form")
        print("=" * 72)
        print(
            f"\n[geometry] R = {SPHERE_RADIUS * 1e3:.1f} mm sphere, eps_r = "
            f"{EPSILON_R_SPHERE}, f = {FREQUENCY_HZ / 1e6:.0f} MHz, "
            f"rho = {RHO_KG_M3:.0f} kg/m^3, box half-width "
            f"{BOX_HALF_WIDTH * 1e3:.0f} mm"
            f"\n[mesh] fine rung only: h_sphere = {RESOLUTION_SPHERE:.5f} m, "
            f"h_far = {RESOLUTION_FAR:.5f} m"
            f"\n[caveat] imposed uniform field on the box wall, solved for the "
            f"interior -- no coil, no mass averaging, no Larmor-coil claim",
            flush=True,
        )

    # ---- three solves: SIGMA_LOW, SIGMA_HIGH (fields kept), and sigma=0 -----
    solve_started = time.perf_counter()
    run_low = _solve_lossy_sphere(SIGMA_LOW, RESOLUTION_SPHERE, RESOLUTION_FAR)
    run_high = _solve_lossy_sphere(
        SIGMA_HIGH, RESOLUTION_SPHERE, RESOLUTION_FAR, return_fields=True
    )
    run_vacuum = _solve_lossy_sphere(0.0, RESOLUTION_SPHERE, RESOLUTION_FAR)
    solve_seconds = time.perf_counter() - solve_started

    closed = {
        s: uniform_sphere_sar_closed_form(
            e0=E0,
            epsilon_r=EPSILON_R_SPHERE,
            sigma=s,
            omega=OMEGA,
            rho=RHO_KG_M3,
            epsilon_0=EPSILON_0,
        )
        for s in (SIGMA_LOW, SIGMA_HIGH)
    }

    errors = {
        s: abs(run["mean_sar"] - closed[s]["sar_w_per_kg"]) / closed[s]["sar_w_per_kg"]
        for s, run in ((SIGMA_LOW, run_low), (SIGMA_HIGH, run_high))
    }

    if comm.rank == 0:
        print(
            f"\n[solve] {solve_seconds:.1f} s for three solves "
            f"(sigma = {SIGMA_LOW}, {SIGMA_HIGH}, 0.0 S/m) at "
            f"{run_high['ncells']} cells",
            flush=True,
        )
        for s, run in ((SIGMA_LOW, run_low), (SIGMA_HIGH, run_high)):
            e_in = _interior_field_closed_form(s)
            print(
                f"\n[sigma = {s:.2f} S/m] |k_in|R = {_k_in_r(s):.4f}, "
                f"closed-form SAR = {closed[s]['sar_w_per_kg']:.6e} W/kg, "
                f"measured mean SAR = {run['mean_sar']:.6e} W/kg "
                f"({errors[s]:.3%} vs 10% bound), "
                f"E_z spread = {run['ez_spread']:.3%} (bound {EZ_SPREAD_BOUND:.0%}), "
                f"Im/Re E_z measured {run['ez_mean'].imag / run['ez_mean'].real:.4f} "
                f"vs closed {e_in.imag / e_in.real:.4f}",
                flush=True,
            )

    # ---- negative control 1: the two-sigma ratio, asserted -----------------
    ratio_fem = run_high["mean_sar"] / run_low["mean_sar"]
    ratio_closed = closed[SIGMA_HIGH]["sar_w_per_kg"] / closed[SIGMA_LOW]["sar_w_per_kg"]
    ratio_blind = SIGMA_HIGH / SIGMA_LOW
    separation = ratio_blind / ratio_fem
    separation_ceiling = ratio_blind / ratio_closed

    # ---- negative control 2: the sigma=0 vacuum sphere, asserted ------------
    if comm.rank == 0:
        print(
            f"\n[control 1] two-sigma ratio: FEM {ratio_fem:.4f}, closed form "
            f"{ratio_closed:.4f}, sigma-blind {ratio_blind:.4f} => separation "
            f"{separation:.3f}x (ceiling {separation_ceiling:.3f}x, module's own "
            "arithmetic, printed not asserted)"
            f"\n[control 2] sigma = 0 (vacuum): dissipated_power_w = "
            f"{run_vacuum['dissipated_power_w']:.6e} W, mean SAR = "
            f"{run_vacuum['mean_sar']:.6e} W/kg",
            flush=True,
        )

    # ---- the anchors ---------------------------------------------------------
    for s, run in ((SIGMA_LOW, run_low), (SIGMA_HIGH, run_high)):
        assert errors[s] < MEAN_SAR_RTOL, (
            f"mean SAR at sigma = {s} S/m is {run['mean_sar']:.6e} W/kg against "
            f"the closed form {closed[s]['sar_w_per_kg']:.6e} W/kg, off by "
            f"{errors[s]:.2%} -- over the {MEAN_SAR_RTOL:.0%} bound imported from "
            "the MAT-4 step 1 gate"
        )
    assert run_low["ez_spread"] < EZ_SPREAD_BOUND, (
        f"interior field at sigma = {SIGMA_LOW} S/m is not uniform: spread "
        f"{run_low['ez_spread']:.2%} inside 0.55 R"
    )
    assert run_high["ez_spread"] < EZ_SPREAD_BOUND, (
        f"interior field at sigma = {SIGMA_HIGH} S/m is not uniform: spread "
        f"{run_high['ez_spread']:.2%} inside 0.55 R"
    )
    for s, run in ((SIGMA_LOW, run_low), (SIGMA_HIGH, run_high)):
        e_in = _interior_field_closed_form(s)
        expected_phase_ratio = e_in.imag / e_in.real
        measured_phase_ratio = run["ez_mean"].imag / run["ez_mean"].real
        phase_error = abs(measured_phase_ratio - expected_phase_ratio) / abs(
            expected_phase_ratio
        )
        assert phase_error < PHASE_RATIO_RTOL, (
            f"Im/Re of the interior E_z at sigma = {s} S/m is "
            f"{measured_phase_ratio:.4f} against the closed-form "
            f"{expected_phase_ratio:.4f} ({phase_error:.2%}) -- over the "
            f"{PHASE_RATIO_RTOL:.0%} bound"
        )

    # ---- negative control 1, asserted ---------------------------------------
    assert separation > SEPARATION_FLOOR, (
        f"the two-sigma SAR ratio {ratio_fem:.4f} sits only {separation:.3f}x from "
        f"the sigma-blind {ratio_blind:.4f} -- below the {SEPARATION_FLOOR}x floor "
        f"imported from the MAT-4 step 1 gate (ceiling {separation_ceiling:.3f})"
    )

    # ---- negative control 2, asserted, exact --------------------------------
    assert run_vacuum["dissipated_power_w"] == 0.0, (
        f"the sigma=0 vacuum sphere dissipated {run_vacuum['dissipated_power_w']:.6e} W "
        "-- should be exactly 0.0 since the integrand is identically zero"
    )
    assert run_vacuum["mean_sar"] <= 1e-12, (
        f"the sigma=0 vacuum sphere's mean SAR is {run_vacuum['mean_sar']:.6e} W/kg "
        "-- should be <= 1e-12"
    )

    # ---- the combined XDMF ---------------------------------------------------
    sar_pointwise, sar_closed_form = _build_dg0_sar_fields(
        run_high, closed[SIGMA_HIGH]["sar_w_per_kg"]
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_xdmf_with_tags(
        OUTPUT_DIR / BASENAME,
        run_high["mesh"],
        run_high["cell_tags"],
        {"SAR_pointwise": sar_pointwise, "SAR_closed_form": sar_closed_form},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm)

    elapsed = time.perf_counter() - started
    if comm.rank == 0:
        print(
            f"\n[write] {BASENAME}.xdmf: SAR_pointwise (DG0, sigma={SIGMA_HIGH}), "
            "SAR_closed_form (DG0 constant on sphere cells), CellTags"
            f"\n[plan record] fine-rung mean-SAR error vs closed form -- printed "
            f"{errors[SIGMA_LOW]:.2%} against plan record "
            f"{PLAN_RECORD_ERROR_LOW_PCT:.2f}%, {errors[SIGMA_HIGH]:.2%} against "
            f"plan record {PLAN_RECORD_ERROR_HIGH_PCT:.2f}% (assertion is only "
            f"the {MEAN_SAR_RTOL:.0%} bound above, not these figures)"
            f"\n\nEX-52 complete in {elapsed:.1f} s. All anchors and both "
            "negative controls held.",
            flush=True,
        )


if __name__ == "__main__":
    main()
