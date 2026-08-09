"""`ANS-1` — the runnable half of the first commissioned AED benchmark.

``SPEC.md`` in this directory is the authority for geometry, materials,
boundary conditions, excitation and mesh guidance; the human operator
replicates *that* document in Ansys Electronics Desktop. This script produces
our half of the comparison and nothing else:

* ``metrics.json`` — R and X at the coil terminals for both solves
  (σ_slab = 100 and 0 S/m), their differences ΔR/ΔX, the Dodd-Deeds closed
  form, the cell count and the elapsed times;
* ``paraview_output/ans1_loop_over_lossy_slab_combined.xdmf`` — |J| in the
  slab, so the operator can compare *where* the eddy current sits, not only
  the terminal numbers;
* ``COMPARISON.md`` — the SPEC's export table with our column filled in, the
  closed-form column **regenerated** from :mod:`fem_em_solver.utils.dodd_deeds`
  at run time (never transcribed), and the AED columns left blank.

**The physics is `MAT-6`'s, and it is imported, not restated.** Every constant,
the mesh, the azimuthal drive and the solve come from the modules that closed
`MAT-6` steps 2b/3 and from the `EX-11` example that shares this compute path,
so the benchmark cannot drift away from the landed gate:

* *The anchor:* ΔR against ``coil_impedance_change`` at the same fixture, gated
  at 2% (1.5834% on the `MAT-6` step-3 record), **and** within 1e-3 relative of
  the pinned ``+3.2770406e-01 Ω`` — `EX-11` reproduced that pin digit for digit
  on 2026-08-09, so a drift here at matched fixture is a regression finding,
  never a tolerance question.
* *The negative control, in-fixture:* the σ = 0 solve is the free half of the
  same pair. Its ohmic power in the slab and its |J| are identically ``0.0`` —
  asserted with no tolerance, because with σ zero cell by cell the integrand is
  zero cell by cell.
* *Reported, never gated:* ΔX. It is **not converged in box size** on this
  fixture (`MAT-6` step 4), which is precisely why the AED number for it is
  worth commissioning — see ``SPEC.md`` §"Why this case". The absolute R and X
  of each solve are likewise reported only: the reaction integral gates the
  *difference*, and the free solve's Re Z is a numerical zero against a finite
  Im Z, printed so its size is visible rather than hidden.

**10 MHz, eddy-current regime — no Larmor claim.** PROJECT_PLAN §2.1 is
explicit that the saline/Larmor case is an extrapolation; this case is
commissioned in the regime where our number is gated, on purpose.

Run it through the example runner (the ``ans:`` group sources the complex
build automatically)::

    ./run_examples.sh -e ans:1
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

# The gated constants, the fixture and the solve live in the tests that closed
# `MAT-6` steps 2b/3, and the assembled compute path in the `EX-11` example.
# The runner puts only ``src`` on PYTHONPATH, so the repo root goes on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.utils.dodd_deeds import coil_impedance_change  # noqa: E402

from tests.validation.test_dodd_deeds_impedance import (  # noqa: E402
    FEM_BOX_HALF_WIDTH,
    FEM_CURRENT_A,
    FEM_FREQUENCY_HZ,
    FEM_LIFTOFF,
    FEM_LOOP_RADIUS,
    FEM_SIGMA_SLAB,
    FEM_WIRE_RADIUS,
    SLAB_TAG,
    WIRE_TAG,
    _azimuthal_current_density,
)
from tests.validation.test_dodd_deeds_projected_drive import (  # noqa: E402
    _solve_projected,
)

# `EX-11` already assembled mesh + σ-field + |J| + ohmic power around that gate;
# the §9 `ANS-1` item requires sharing its path rather than duplicating it.
_EX11 = _REPO_ROOT / "examples" / "materials" / "01_dodd_deeds_coil_loading.py"
sys.path.insert(0, str(_EX11.parent))
_ex11 = __import__("01_dodd_deeds_coil_loading")  # noqa: E402  (leading digit)

_build_fixture = _ex11._build_fixture
_sigma_field = _ex11._sigma_field
_ohmic_power_in_slab = _ex11._ohmic_power_in_slab
_current_density_magnitude = _ex11._current_density_magnitude
_reduced_real = _ex11._reduced_real

#: The §7 `ANS-1` anchor's first leg: ΔR against the closed form. 1.5834% on the
#: `MAT-6` step-3 record; 2% is what the fixture can honestly claim, and it is
#: not a knob — a run outside it is a regression finding.
DELTA_R_RTOL = 0.02

#: The second leg: the pinned ΔR of the landed gate, reproduced digit for digit
#: by `EX-11` on 2026-08-09. This is a *fixture-identity* check — it says the
#: benchmark is solving the same problem the gate solved, not merely a problem
#: with the same closed-form answer.
DELTA_R_PIN_OHM = 3.2770406e-01
DELTA_R_PIN_RTOL = 1e-3

MU0 = 4.0e-7 * np.pi

CASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = CASE_DIR / "paraview_output"
BASENAME = "ans1_loop_over_lossy_slab_combined"


def _terminal_impedance(e_complex, j_prime, current, comm) -> complex:
    """``Z = -(1/I'²) ∫ E·J' dV`` over the whole domain — the reaction integral.

    ``J'`` is the projected drive and is real, so ``ufl.inner``'s conjugation of
    its second argument is a no-op and this is the reaction integral, not a
    power. Taking it per solve rather than on the difference is what gives the
    SPEC's R and X columns; the *difference* of the two is algebraically the
    ΔZ the `MAT-6` gate asserts.
    """
    reaction = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(e_complex, j_prime) * ufl.dx)),
        op=MPI.SUM,
    )
    return complex(-reaction / current**2)


def _write_metrics(payload) -> Path:
    path = CASE_DIR / "metrics.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def _write_comparison(m) -> Path:
    """``COMPARISON.md``: our column filled, AED blank, closed form regenerated.

    Every number below comes from ``m``, which came from this run — nothing is
    transcribed from a prior log, and the closed-form column is
    ``coil_impedance_change`` evaluated seconds ago.
    """
    exact = m["closed_form"]
    loaded = m["solve_loaded"]
    free = m["solve_free"]
    path = CASE_DIR / "COMPARISON.md"
    path.write_text(
        f"""# ANS-1 — comparison table (our half filled, AED half blank)

Generated by `01_loop_over_lossy_slab_10MHz.py` on {m["generated_utc"]}; every
number in the "Ours (FEM)" and "Dodd-Deeds closed form" columns is produced by
that run — the closed form is evaluated from `utils/dodd_deeds.py` at run time,
not transcribed. Re-run `./run_examples.sh -e ans:1` to regenerate.

`SPEC.md` is the authority for the problem to be replicated. Fill the AED
columns from the Maxwell 3D eddy-current solve of that spec, reporting **all**
digits AED prints.

## Terminal quantities

| Quantity | Dodd-Deeds closed form | Ours (FEM) | AED | AED vs ours |
|---|---|---|---|---|
| R, σ_slab = 100 S/m [Ω] | — (closed form gives ΔZ only) | {loaded["R_ohm"]:+.7e} | | |
| X, σ_slab = 100 S/m [Ω] | — | {loaded["X_ohm"]:+.7e} | | |
| R, σ_slab = 0 [Ω] | — | {free["R_ohm"]:+.7e} | | |
| X, σ_slab = 0 [Ω] | — | {free["X_ohm"]:+.7e} | | |
| **ΔR** [Ω] | {exact["delta_R_ohm"]:+.7e} | **{m["delta_R_ohm"]:+.7e}** | | |
| ΔX [Ω] | {exact["delta_X_ohm"]:+.7e} | {m["delta_X_ohm"]:+.7e} | | |

**ΔR is the gated row** — ours is within {m["delta_R_rel_error"]:.4%} of the
closed form (ceiling {DELTA_R_RTOL:.0%}; 1.5834% on the `MAT-6` step-3 record)
and within {m["delta_R_pin_rel_error"]:.2e} relative of the pinned
`{DELTA_R_PIN_OHM:+.7e} Ω`.

**ΔX is reported, never gated.** Ours is a ratio {m["delta_X_ratio"]:.4f} of the
closed form and is **not converged in box size** (`MAT-6` step 4: 5.57% still
moving between W = 0.15 and 0.20). This row is the main reason the case was
commissioned — the AED number is an adjudication input, not a formality.

**The absolute R and X rows are reported, never gated.** The reaction integral
gates the *difference*; each solve's own R and X carry the box truncation. In
particular the σ = 0 solve's R is a numerical zero
({free["R_ohm"]:+.3e} Ω) against its finite X — printed so its size is visible.

## Negative control (in-fixture, ours)

| Check | σ = 100 S/m | σ = 0 |
|---|---|---|
| Ohmic power in the slab ∫(σ/2)\\|E\\|² dV [W] | {m["ohmic_power_loaded_W"]:.6e} | {m["ohmic_power_free_W"]:.6e} |
| max \\|J\\| in the domain [A/m²] | {m["max_J_loaded_A_per_m2"]:.6e} | {m["max_J_free_A_per_m2"]:.6e} |

The control's two entries are asserted `== 0.0` with **no tolerance**: with σ
identically zero the integrand is zero cell by cell, so anything but exactly
zero would mean the control is not lossless.

Independent energy cross-check, reported not gated:
½ ΔR I'² = {m["power_from_delta_R_W"]:.6e} W from the reaction integral vs
{m["ohmic_power_loaded_W"]:.6e} W from the solved field —
ratio {m["ohmic_power_ratio"]:.4f}.

## Solve metadata

| Item | Ours (FEM) | AED |
|---|---|---|
| Elements | {m["n_cells"]} tetrahedra, lowest-order Nédélec edge elements (`N1curl`, degree 1) | |
| Adaptive passes | n/a — fixed graded mesh | |
| Final energy error | n/a | |
| Solve time | {loaded["solve_seconds"]:.1f} s (loaded) + {free["solve_seconds"]:.1f} s (free) at `mpiexec -n {m["mpi_ranks"]}` | |
| Drive current I' | {m["current_A"]:.6f} A against the nominal {FEM_CURRENT_A:.1f} A | |
| Skin depth δ | {m["skin_depth_m"] * 1e3:.2f} mm = {m["skin_depth_over_a"]:.3f} a | |

Mesh sizing (from the gate fixture): wire {m["mesh"]["resolution_wire"]} m,
near field {m["mesh"]["resolution_near"]} m, far field
{m["mesh"]["resolution_far"]} m, near box half-width
{m["mesh"]["near_half_width"]} m × depth {m["mesh"]["near_depth"]} m × height
{m["mesh"]["near_height"]} m. Box half-width W = {m["box_half_width_m"]} m.

## Field export

`paraview_output/{BASENAME}.xdmf` (regenerated by each run; not tracked, like
every other `paraview_output/` in the repo). Threshold on `CellTags`
(3 = lossy slab, 1 = wire) and colour by `J_magnitude` [A/m²]. The induced
current hugs the slab surface under the loop and decays over the skin depth.
For the AED half, export the current-density magnitude on the same cut so the
spatial distributions can be compared, not just the terminal numbers.

## Provenance

* Fixture and drive: `tests/validation/test_dodd_deeds_impedance.py`
  (constants, mesh, azimuthal source) and
  `tests/validation/test_dodd_deeds_projected_drive.py` (`_solve_projected`,
  the production projected drive) — imported by this script, never restated.
* Shared compute path: `examples/materials/01_dodd_deeds_coil_loading.py`
  (`EX-11`), whose helpers this script reuses directly.
* Closed form: `src/fem_em_solver/utils/dodd_deeds.py`,
  `coil_impedance_change(f={FEM_FREQUENCY_HZ:.0f}, a={FEM_LOOP_RADIUS},
  h={FEM_LIFTOFF}, σ={FEM_SIGMA_SLAB})`.
* Gate of record: `MAT-6` step 3 (PROJECT_PLAN §7), ΔR to 1.5834%.
"""
    )
    return path


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "this benchmark needs the complex DolfinX build "
            "(source /usr/local/bin/dolfinx-complex-mode); the runner's `ans:` "
            "group sources it automatically"
        )

    skin_depth = 1.0 / np.sqrt(np.pi * FEM_FREQUENCY_HZ * MU0 * FEM_SIGMA_SLAB)

    if comm.rank == 0:
        print("=" * 72)
        print("ANS-1 — loop over a lossy slab at 10 MHz (runnable half)")
        print("=" * 72)
        print(
            f"\n[spec]  SPEC.md in this directory is what the operator "
            f"replicates in Ansys Electronics Desktop"
            f"\n[geometry] a = {FEM_LOOP_RADIUS * 1e3:.0f} mm loop "
            f"(wire r = {FEM_WIRE_RADIUS * 1e3:.1f} mm) at liftoff "
            f"h = {FEM_LIFTOFF * 1e3:.0f} mm over a half-space, in a "
            f"W = {FEM_BOX_HALF_WIDTH} m half-width PEC box"
            f"\n[material] slab σ = {FEM_SIGMA_SLAB} S/m at f = "
            f"{FEM_FREQUENCY_HZ / 1e6:.0f} MHz; skin depth δ = "
            f"{skin_depth * 1e3:.2f} mm = {skin_depth / FEM_LOOP_RADIUS:.3f} a"
            f"\n[caveat] eddy-current regime at 10 MHz — nothing here is a "
            f"claim about saline at the Larmor frequency (§2.1)",
            flush=True,
        )

    mesh_started = time.perf_counter()
    msh, cell_tags = _build_fixture(comm)
    mesh_seconds = time.perf_counter() - mesh_started
    n_cells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )

    if comm.rank == 0:
        print(f"\n[mesh] {n_cells} cells built in {mesh_seconds:.1f} s", flush=True)

    # ---- the two solves the SPEC commissions --------------------------------
    e_loaded, j_prime, t_loaded = _solve_projected(msh, cell_tags, FEM_SIGMA_SLAB, comm)
    e_free, _, t_free = _solve_projected(msh, cell_tags, 0.0, comm)

    # I': the projected drive's circuit current, the same cross-section integral
    # the `MAT-6` step-3 gate uses.
    x = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_current_density(1.0)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    current = _reduced_real(ufl.inner(j_prime, phi_hat) * dx_wire, comm) / (
        2.0 * np.pi * FEM_LOOP_RADIUS
    )

    z_loaded = _terminal_impedance(e_loaded, j_prime, current, comm)
    z_free = _terminal_impedance(e_free, j_prime, current, comm)
    dz = z_loaded - z_free
    dz_ref = coil_impedance_change(
        FEM_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )
    delta_r_error = abs(dz.real / dz_ref.real - 1.0)
    delta_r_pin_error = abs(dz.real / DELTA_R_PIN_OHM - 1.0)

    if comm.rank == 0:
        print(
            f"\n[solve] loaded {t_loaded:.1f} s, free {t_free:.1f} s "
            f"(each incl. the CG1 Poisson projection of the drive)"
            f"\n[drive] I' = {current:.6f} A against the nominal "
            f"{FEM_CURRENT_A:.1f} A"
            f"\n[Z]     σ=100: {z_loaded.real:+.7e} + j({z_loaded.imag:+.7e}) Ω"
            f"\n[Z]     σ=0  : {z_free.real:+.7e} + j({z_free.imag:+.7e}) Ω"
            f"   — R here is a numerical zero; both rows reported, never gated"
            f"\n[ΔZ]    FEM   = {dz.real:+.7e} + j({dz.imag:+.7e}) Ω"
            f"\n[ΔZ]    exact = {dz_ref.real:+.7e} + j({dz_ref.imag:+.7e}) Ω"
            f"\n[ΔR]    relative error {delta_r_error:.4%} against the "
            f"{DELTA_R_RTOL:.0%} ceiling (1.5834% on the `MAT-6` step-3 record)"
            f"\n[ΔR]    against the pinned {DELTA_R_PIN_OHM:+.7e} Ω: "
            f"{delta_r_pin_error:.3e} relative, ceiling {DELTA_R_PIN_RTOL:.0e}"
            f"\n[ΔX]    ratio {dz.imag / dz_ref.imag:.4f} — reported, never "
            f"gated: not converged in box size (`MAT-6` step 4). This row is "
            f"why the case was commissioned.",
            flush=True,
        )

    # ---- the anchor: both legs ----------------------------------------------
    assert dz.real > 0.0, (
        f"a conductive half-space must dissipate, got ΔR = {dz.real:.6e} Ω"
    )
    assert delta_r_error < DELTA_R_RTOL, (
        f"ΔR = {dz.real:.7e} Ω misses the Dodd-Deeds closed form "
        f"{dz_ref.real:.7e} Ω by {delta_r_error:.2%}, against the "
        f"{DELTA_R_RTOL:.0%} ceiling and 1.5834% on the `MAT-6` step-3 record "
        f"— a regression finding, not a tolerance to move"
    )
    assert delta_r_pin_error < DELTA_R_PIN_RTOL, (
        f"ΔR = {dz.real:.7e} Ω drifts {delta_r_pin_error:.3e} relative from the "
        f"pinned {DELTA_R_PIN_OHM:.7e} Ω that `EX-11` reproduced digit for digit "
        f"on 2026-08-09 — at a matched fixture that is a regression finding, and "
        f"the benchmark must not be published against a moved number"
    )
    assert dz.imag < 0.0, (
        f"the induced currents must expel flux, got ΔX = {dz.imag:.6e} Ω"
    )

    # ---- negative control: the free solve dissipates nothing -----------------
    sigma_loaded = _sigma_field(msh, cell_tags, FEM_SIGMA_SLAB)
    sigma_free = _sigma_field(msh, cell_tags, 0.0)
    power_loaded = _ohmic_power_in_slab(e_loaded, sigma_loaded, msh, cell_tags, comm)
    power_free = _ohmic_power_in_slab(e_free, sigma_free, msh, cell_tags, comm)
    power_from_dr = 0.5 * dz.real * current**2

    if comm.rank == 0:
        print(
            f"\n[control] ohmic power in the slab: loaded {power_loaded:.6e} W, "
            f"free {power_free:.6e} W — the σ = 0 half of the same pair, so "
            f"every other input is shared"
            f"\n[control] ½ ΔR I'² = {power_from_dr:.6e} W from the reaction "
            f"integral vs {power_loaded:.6e} W from the field "
            f"[ratio {power_loaded / power_from_dr:.4f}] — reported, not gated",
            flush=True,
        )

    assert power_loaded > 0.0, (
        f"the loaded solve dissipates no power in the slab: {power_loaded:.6e} W"
    )
    assert power_free == 0.0, (
        f"the σ = 0 control dissipates {power_free:.6e} W — with σ identically "
        f"zero the integrand is zero cell by cell, so anything but exactly 0.0 "
        f"means the control is not lossless"
    )

    # ---- the field export the operator compares against ---------------------
    j_mag = _current_density_magnitude(e_loaded, sigma_loaded, msh)
    j_mag_free = _current_density_magnitude(e_free, sigma_free, msh)
    # ``x.array`` is complex-typed in the complex build even though |J| is real
    # by construction; take the real part explicitly rather than let float()
    # discard an imaginary part behind a ComplexWarning. Rank-local max, reduced.
    j_max = comm.allreduce(
        float(np.max(np.real(j_mag.x.array))) if j_mag.x.array.size else 0.0,
        op=MPI.MAX,
    )
    j_max_free = comm.allreduce(
        float(np.max(np.real(j_mag_free.x.array))) if j_mag_free.x.array.size else 0.0,
        op=MPI.MAX,
    )
    assert j_max_free == 0.0, (
        f"the lossless control carries eddy current: max |J| = {j_max_free:.6e} A/m²"
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / BASENAME, msh, cell_tags, {"J_magnitude": j_mag}, comm=comm
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    total_seconds = time.perf_counter() - started

    # ---- the deliverables ---------------------------------------------------
    metrics = {
        "case": "loop_over_lossy_slab_10MHz",
        "chunk": "ANS-1",
        "spec": "SPEC.md (authority for geometry/materials/BCs/excitation)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regime": "eddy-current at 10 MHz; NOT the Larmor frequency (§2.1)",
        "frequency_hz": FEM_FREQUENCY_HZ,
        "loop_radius_m": FEM_LOOP_RADIUS,
        "wire_radius_m": FEM_WIRE_RADIUS,
        "liftoff_m": FEM_LIFTOFF,
        "box_half_width_m": FEM_BOX_HALF_WIDTH,
        "sigma_slab_S_per_m": FEM_SIGMA_SLAB,
        "nominal_current_A": FEM_CURRENT_A,
        "current_A": current,
        "skin_depth_m": skin_depth,
        "skin_depth_over_a": skin_depth / FEM_LOOP_RADIUS,
        "mesh": {
            "resolution_wire": 0.002,
            "resolution_near": 0.005,
            "resolution_far": 0.025,
            "near_half_width": 0.06,
            "near_depth": 0.05,
            "near_height": 0.03,
        },
        "n_cells": int(n_cells),
        "mpi_ranks": comm.size,
        "mesh_seconds": mesh_seconds,
        "total_seconds": total_seconds,
        "solve_loaded": {
            "sigma_slab_S_per_m": FEM_SIGMA_SLAB,
            "R_ohm": z_loaded.real,
            "X_ohm": z_loaded.imag,
            "solve_seconds": t_loaded,
        },
        "solve_free": {
            "sigma_slab_S_per_m": 0.0,
            "R_ohm": z_free.real,
            "X_ohm": z_free.imag,
            "solve_seconds": t_free,
        },
        "delta_R_ohm": dz.real,
        "delta_X_ohm": dz.imag,
        "closed_form": {
            "source": "fem_em_solver.utils.dodd_deeds.coil_impedance_change",
            "delta_R_ohm": dz_ref.real,
            "delta_X_ohm": dz_ref.imag,
        },
        "delta_R_rel_error": delta_r_error,
        "delta_R_rtol": DELTA_R_RTOL,
        "delta_R_pin_ohm": DELTA_R_PIN_OHM,
        "delta_R_pin_rel_error": delta_r_pin_error,
        "delta_R_pin_rtol": DELTA_R_PIN_RTOL,
        "delta_X_ratio": dz.imag / dz_ref.imag,
        "delta_X_gated": False,
        "delta_X_note": "not converged in box size (MAT-6 step 4); reported only",
        "ohmic_power_loaded_W": power_loaded,
        "ohmic_power_free_W": power_free,
        "power_from_delta_R_W": power_from_dr,
        "ohmic_power_ratio": power_loaded / power_from_dr,
        "max_J_loaded_A_per_m2": j_max,
        "max_J_free_A_per_m2": j_max_free,
        "xdmf": f"paraview_output/{BASENAME}.xdmf",
        "aed": None,
    }

    if comm.rank == 0:
        metrics_path = _write_metrics(metrics)
        comparison_path = _write_comparison(metrics)
        print(
            f"\n[paraview] wrote {xdmf_path}"
            f"\n[paraview] max |J| = {j_max:.6e} A/m² loaded, "
            f"{j_max_free:.6e} A/m² in the lossless control"
            f"\n[deliverable] {metrics_path}"
            f"\n[deliverable] {comparison_path} — AED columns blank, awaiting "
            f"the operator's Maxwell 3D replication of SPEC.md"
            f"\n\nAll assertions hold. Total elapsed {total_seconds:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
