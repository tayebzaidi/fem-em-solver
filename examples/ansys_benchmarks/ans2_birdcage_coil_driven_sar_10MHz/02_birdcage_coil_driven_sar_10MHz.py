"""ANS-2 step 1 — coil-driven SAR in the loaded four-leg birdcage at 10 MHz.

`ANS-2` (PROJECT_PLAN §7), the fourth commissioned Ansys Electronics Desktop
benchmark (§5.4) and the **first that can attack the absolute SAR claim**:
every coil-driven SAR number this repository holds is a C4 *symmetry identity*,
and a SAR wrong by a constant factor passes one exactly.  `SPEC.md` beside this
file is the authority for the boundary-value problem the human operator
replicates in AED; this script produces *our* half of it.

**Scope — the runnable half, SPEC export rows 1–3, 7 and 8 only.**  Rows 4–6
(mass-averaged and peak-over-phantom) are deliberately held for a step 2 for
the reason the SPEC pre-registers: our operator averages over a **sphere** of
equal mass and IEC 62704-1 (hence HFSS) over a **cube**, so those rows carry a
named systematic and the SPEC forbids reading a rows-4–6 miss as a finding
until rows 1–3 have agreed.  The shape-free rows adjudicate; they ship first.

What is written:

* ``metrics.json`` — pointwise SAR at the four named points per drive, the
  whole-phantom dissipated power and average SAR per drive, the excitation
  metadata (incident / supplied / accepted power, ``|Im P|/Re P``) and the
  solve metadata
* ``COMPARISON.md`` — the SPEC's export tables with our columns filled and the
  AED columns (**Zero Order** and **First Order**, the `ANS-5` ruling) blank,
  ready for the operator
* ``paraview_output/ans2_birdcage_coil_driven_sar_10mhz_combined.xdmf`` — mesh,
  CellTags and the port-1-driven ``E``/``B`` phasor magnitudes

**Nothing here is transcribed, and nothing is re-implemented.**  The fixture is
built by ``_build_mass_averaged`` — the `MAT-4` step 4 gate module's *own*
construction — called at ``PHANTOM_RESOLUTION_1G_RUNG``, the `GEO-27` rung, and
the mis-paired 1 g control comes from `MAT-4` step 5b's own
``_add_one_gram_control``.  Every band and every record below is imported from
those modules; none is restated and none is moved.  That is `ANS-1`'s rule: if
the gated path moves, this benchmark moves with it and its assertions fire.

**Anchors (asserted).**

* the four cyclic **10 g** C4 pairs and the four cyclic **1 g** C4 pairs, both
  against the imported, unmoved ``C4_COVARIANCE_BAND`` = 5 %
  (`MAT-4` step 4 / step 5b)
* the whole-phantom coverage identity — a ball of radius
  ``WHOLE_PHANTOM_BALL_RADIUS_M`` returns the tag-3 ``½∫σ|E|²`` and
  ``ρ·V_phantom`` at the imported ``EXACT_IDENTITY_RTOL`` = 1e-10
* the rung's two version-tagged mesh records (199 920 / 58 866 cells) at the
  imported ``CELL_COUNT_BAND`` = 1 %, never at equality

**Negative control (asserted).**  The *mis-paired* 1 g comparison
``|SAR₁g(c_{k+2}; k) − SAR₁g(c_k; k)| / SAR₁g(c_k; k)`` — the far-side ball
under the same drive, which the C4 identity says nothing about.  `MAT-4`
step 5b measured it at **87.01–87.06 %** on this exact rung
(`20260908T200629Z_MAT-4-step5b.log:1990–1993`) against the same 5 % band, a
separation of ≈ 17×.  Asserted here only as *at least* ``CONTROL_SEPARATION``
= 10× the band, so a C4 identity that were merely measuring a constant field
would fail this script.

**Normalisation — read this twice.**  Our drive is ``V_src`` = 1 V behind
50 Ω, i.e. ``|V_src|²/(8Z₀)`` = 2.5e-03 W incident — the solver's phasors are
**peak** amplitudes (``ports/superposition.py``: available power ``½|a|²``),
so the RMS form ``V²/(4Z₀)`` = 5.0e-03 W this file quoted until 2026-09-18 was
a factor of two high (found by the first AED comparison: the reported accepted
power matched ``1 − |S₁₁|²`` only of the halved figure); HFSS's default is 1 W.  SAR
is linear in incident power.  The incident, supplied and accepted powers are
*printed explicitly* here and in `COMPARISON.md`; HFSS's normalisation is
**not** matched and nothing is rescaled silently.  That is the one error mode
that passes every self-check on both sides.

**Out of scope.**  Runnable half only: no adjudication, no absolute-SAR,
C95.3-compliance, homogeneity, B₁⁺, Larmor or quadrature claim from our side.
The C4 identities are self-consistency statements on one fixture — which is
precisely why AED's opinion is being asked for.

**The phantom-resolution knob (`ANS-2` step 4a).**  ``FEM_EM_ANS2_PHANTOM_RESOLUTION``
overrides the rung this script meshes on, so the XL window pre-registered as
`xl-pending.md` entry 10 can run *this example* at the halved rung without a
second copy of it.  **Unset ⇒ byte-identical behaviour to the 0.0025 m rung**
(the `GEO-27` / `MAT-4` step 5b rung, the only rung with mesh records).  When
set: the two version-tagged mesh-record assertions are **skipped with a printed
line** (the halved rung has no record yet) while every other imported band stays
asserted; ``metrics.json`` and the XDMF take resolution-tagged names
(``metrics_h0.00125.json``, …); ``COMPARISON.md`` / ``COMPARISON_private.md``
are **not** rewritten — the tracked comparison stays the 0.0025 rung's, which is
also the reference the ``[ANS-2 step 4]`` readout lines print beside.

Run it through the example runner (the ``ans:`` group sources the complex
build automatically)::

    ./run_examples.sh -e ans:2 -n 4 -t 560
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gate modules' constants and construction are importable rather than
# restated (the `ANS-1` rule, as `ANS-3` and `ANS-4` do).
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.evaluation import (  # noqa: E402
    evaluate_vector_field_parallel,
)
from fem_em_solver.post.sar import mean_sar  # noqa: E402

from tests.mesh.test_birdcage_port_sheet_prerequisite import (  # noqa: E402
    CELL_COUNT_BAND,
)
from tests.mesh.test_birdcage_port_tags import (  # noqa: E402
    PHANTOM_HEIGHT,
    PHANTOM_RADIUS,
)
from tests.validation.test_birdcage_b1_plus_map import (  # noqa: E402
    C4_COVARIANCE_BAND,
)
from tests.validation.test_birdcage_sar_1g_rung import (  # noqa: E402
    ONE_GRAM_RUNG_CELL_RECORD,
    ONE_GRAM_RUNG_PHANTOM_CELL_RECORD,
    PHANTOM_RESOLUTION_1G_RUNG,
    _add_one_gram_control,
)
from tests.validation.test_birdcage_sar_mass_averaged import (  # noqa: E402
    CENTRE_RADIUS_M,
    EXACT_IDENTITY_RTOL,
    PHANTOM_RHO_KG_PER_M3,
    WHOLE_PHANTOM_BALL_RADIUS_M,
    _build_mass_averaged,
)
from tests.validation.test_lossy_sphere_fullwave import SALINE_SIGMA  # noqa: E402
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    TERMINATED_PORT_IMPEDANCE_OHM,
)
from tests.validation.test_port_gap_voltage_impedance import (  # noqa: E402
    FREQUENCY_HZ,
)
from tests.validation.test_port_package_sparameters import (  # noqa: E402
    REFERENCE_IMPEDANCE_OHM,
)

CASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = CASE_DIR / "paraview_output"
BASENAME = "ans2_birdcage_coil_driven_sar_10mhz_combined"

#: `ANS-2` step 4a — the phantom-resolution knob the XL window's command names
#: (`xl-pending.md` entry 10; the cost probe
#: ``tests/validation/probe_ans2_phantom_h_halving.py`` reads the same variable,
#: so the knob name is one contract, not two).  Unset is the *only* configuration
#: that writes the tracked ``metrics.json`` / ``COMPARISON.md`` and the only one
#: with mesh records to assert against.
PHANTOM_RESOLUTION_ENV = "FEM_EM_ANS2_PHANTOM_RESOLUTION"
_RESOLUTION_OVERRIDE = os.environ.get(PHANTOM_RESOLUTION_ENV)
RESOLUTION_OVERRIDDEN = _RESOLUTION_OVERRIDE is not None
PHANTOM_RESOLUTION_M = (
    float(_RESOLUTION_OVERRIDE) if RESOLUTION_OVERRIDDEN else PHANTOM_RESOLUTION_1G_RUNG
)

#: Output-name suffix.  Empty when the knob is unset — that is what makes the
#: unset run byte-identical to this file's behaviour before step 4a.
RESOLUTION_TAG = f"_h{PHANTOM_RESOLUTION_M:g}" if RESOLUTION_OVERRIDDEN else ""

#: The same tag with the decimal point written ``p``, for the XDMF basename only:
#: ``write_xdmf_with_tags`` treats everything after the last dot as a suffix and
#: replaces it, so ``..._h0.004`` was silently written as ``..._h0.xdmf`` — every
#: rung colliding on one filename (measured, 2026-09-19, `ANS-2` step 4a).
RESOLUTION_TAG_PATHSAFE = RESOLUTION_TAG.replace(".", "p")


def _load_example(path: Path, module_name: str):
    """Import an ``examples/`` script by path — its basename starts with a digit."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# `EX-34`'s ParaView field bundle, reused verbatim: the same fixture rendered
# the same way, so the picture cannot drift from the gated example path.
_EX34 = _load_example(
    _REPO_ROOT / "examples" / "ports" / "05_birdcage_larmor_frequency_ladder.py",
    "ex34_birdcage_larmor_frequency_ladder",
)
_paraview_fields = _EX34._paraview_fields

#: Our production discretization and the AED correspondence the `ANS-5` ruling
#: (2026-08-30) put in every SPEC: degree-1 Nédélec = 6 unknowns per
#: tetrahedron = HFSS **Zero Order**, which is *not* AED's default.
BASIS_ORDER = "Nedelec first kind, degree 1 (N1curl)"
BASIS_UNKNOWNS_PER_TET = 6
AED_ORDER_CORRESPONDENCE = (
    "HFSS Zero Order (20 unknowns/tet = First Order, the AED default, is the "
    "order-sensitivity column)"
)

#: The negative control's asserted separation, in multiples of the imported C4
#: band.  `MAT-4` step 5b measured the mis-paired 1 g control at 87.01–87.06 %
#: against the 5 % band on this exact rung
#: (`20260908T200629Z_MAT-4-step5b.log:1990–1993`) — a separation of ≈ 17×.
#: Asserted at 10× so the assertion is a floor with headroom rather than a
#: re-record of a gate digit inside an example (the `ANS-1` rule).
CONTROL_SEPARATION = 10.0

#: The phantom's mass and volume, closed form from the SPEC's geometry.  Printed
#: beside the meshed volume; the *meshed* volume is what divides the power.
PHANTOM_VOLUME_CLOSED_FORM_M3 = float(np.pi * PHANTOM_RADIUS**2 * PHANTOM_HEIGHT)


def _incident_power_w(source_voltage_v: complex) -> float:
    """``|V_src|²/(8Z₀)`` — the available (incident-wave) power of our drive.

    Peak-phasor convention, the package's (``ports/superposition.py``: the
    incident amplitude is ``a = V_src/(2√z₀)`` and the available power
    ``½|a|²``): a 1 V source behind 50 Ω delivers 2.5000000e-03 W, against
    HFSS's default 1 W.  Until 2026-09-18 this read ``/(4Z₀)`` — the RMS form,
    a factor of two high and inconsistent with this file's own ``½·Re(V·I*)``
    power bookkeeping; the first AED comparison exposed it.  Computed from the
    sheet's own source voltage and the imported reference impedance so it
    cannot drift from the drive actually applied.
    """
    return float(abs(source_voltage_v) ** 2 / (8.0 * float(REFERENCE_IMPEDANCE_OHM)))


def _excitation(solved) -> dict:
    """Row 7: incident, supplied and accepted power at the driven port.

    ``supplied`` is ``½·Re(V_src·conj(I))`` — what the ideal source delivers
    into the series combination of its own 50 Ω and the network.  ``accepted``
    is the same product formed with the *port* voltage ``V = V_src − I·Z_p``,
    i.e. what crosses the sheet into the coil.  Both currents come from the
    package's ``sheet_terminal_current`` through ``_solve_driven`` and are
    already MPI-reduced.
    """
    driven = solved["driven"]
    v_src = complex(solved["source_voltage_v"])
    current = complex(solved["currents"][driven])
    z_p = complex(TERMINATED_PORT_IMPEDANCE_OHM)
    v_port = v_src - current * z_p
    p_supplied = 0.5 * v_src * np.conjugate(current)
    p_accepted = 0.5 * v_port * np.conjugate(current)
    return {
        "driven_port": driven,
        "source_voltage_v": {"re": float(np.real(v_src)), "im": float(np.imag(v_src))},
        "port_voltage_v": {
            "re": float(np.real(v_port)),
            "im": float(np.imag(v_port)),
        },
        "port_current_a": {
            "re": float(np.real(current)),
            "im": float(np.imag(current)),
        },
        "incident_power_w": _incident_power_w(v_src),
        "supplied_power_re_w": float(np.real(p_supplied)),
        "supplied_power_im_va": float(np.imag(p_supplied)),
        "accepted_power_re_w": float(np.real(p_accepted)),
        "accepted_power_im_va": float(np.imag(p_accepted)),
        "accepted_im_over_re": float(
            abs(np.imag(p_accepted)) / abs(np.real(p_accepted))
        ),
    }


def _pointwise_sar(built, points, comm):
    """Row 1: ``σ|E|²/(2ρ)`` at the four named points, per driven port.

    The phasor is N1curl; XDMF and point evaluation both want a Lagrange
    interpolant, so ``E`` is interpolated to CG1 exactly as `EX-34`'s ParaView
    bundle does and evaluated through
    :func:`~fem_em_solver.post.evaluation.evaluate_vector_field_parallel` —
    never ``f.eval(points, arange(n))``, which is rank-local (the standing
    rule).  That routine is collective and broadcasts its result, so every rank
    below holds the same numbers.

    ``σ`` is the imported ``SALINE_SIGMA``, which
    ``tests/validation/test_birdcage_sar_map.py`` gates as *uniform* over the
    phantom to 1e-12; the four points sit at r = 0.015 m, well inside the
    phantom's 0.03 m radius, so no point samples the σ jump.
    """
    msh = built["mesh"]
    v_cg = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    out = {}
    for k in range(4):
        solved = built["solves"][f"P{k + 1}"]
        e_cg = fem.Function(v_cg)
        e_cg.interpolate(solved["fields"].e_complex)
        e_cg.x.scatter_forward()
        values, valid = evaluate_vector_field_parallel(e_cg, points, comm)
        if not bool(np.all(valid)):
            missing = [int(i) for i in np.flatnonzero(~valid)]
            raise RuntimeError(
                f"point evaluation found no cell for centre index/indices "
                f"{missing} on drive P{k + 1}; every named point must lie in the "
                "phantom"
            )
        e_sq = np.sum(np.abs(values) ** 2, axis=1)
        out[k] = {
            "e_magnitude_v_per_m": [float(np.sqrt(v)) for v in e_sq],
            "sar_w_per_kg": [
                float(SALINE_SIGMA * v / (2.0 * PHANTOM_RHO_KG_PER_M3)) for v in e_sq
            ],
        }
    return out


def _phantom_power(built):
    """Rows 2 and 3: ``½∫_phantom σ|E|²`` and its mass average, per driven port.

    ``mean_sar`` restricted to the phantom tag; the reduction over ``comm``
    happens inside it (``assemble_scalar`` is rank-local and this is the only
    place a number entering ``metrics.json`` could have escaped one).
    """
    out = {}
    for k in range(4):
        solved = built["solves"][f"P{k + 1}"]
        reading = mean_sar(
            solved["fields"].e_complex,
            sigma=solved["fields"].sigma_field,
            rho=PHANTOM_RHO_KG_PER_M3,
            cell_tags=built["cell_tags"],
            comm=built["mesh"].comm,
            subdomain_ids=PHANTOM_CELL_TAG,
        )
        out[k] = {
            "dissipated_power_w": float(reading["dissipated_power_w"]),
            "meshed_volume_m3": float(reading["volume_m3"]),
            "meshed_mass_kg": float(PHANTOM_RHO_KG_PER_M3 * reading["volume_m3"]),
            "average_sar_w_per_kg": float(reading["mean_sar_w_per_kg"]),
        }
    return out


def _write_paraview(built, comm):
    """Cells + tags + the port-1-driven field, into this case's own directory.

    No extra solve: unlike `ANS-3`/`ANS-4`, whose sweeps return terminal
    quantities only, this construction already holds all four solved phasors.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    solved = built["solves"]["P1"]
    written, _ = write_xdmf_with_tags(
        OUTPUT_DIR / (BASENAME + RESOLUTION_TAG_PATHSAFE),
        built["mesh"],
        built["cell_tags"],
        _paraview_fields(built["mesh"], solved["fields"].e_complex, solved["omega"]),
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return written


#: The 0.0025 m rung's own ``metrics.json`` — tracked, and left untouched by any
#: overridden run, so it is the reference the step-4 readout prints beside.
REFERENCE_METRICS_PATH = CASE_DIR / "metrics.json"


def _write_metrics(payload) -> Path:
    path = CASE_DIR / f"metrics{RESOLUTION_TAG}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def _load_reference_metrics():
    """The tracked 0.0025-rung metrics, or ``None`` if this clone has none."""
    if not REFERENCE_METRICS_PATH.exists():
        return None
    return json.loads(REFERENCE_METRICS_PATH.read_text())


def _spread(values):
    """``(max − min)/min`` — the arithmetic behind the adjudication's 15.7 %.

    Applied to the four *driven-point* samples (drive ``Pk`` read at the k-th
    named point), which C4 symmetry makes equal in the exact problem, this
    reproduces the 2026-09-18 `ANS-2` adjudication's quoted point-sampling
    scatter on the tracked 0.0025-rung ``metrics.json`` against HFSS's 0.02 %.
    Whether it collapses under h-halving is the whole question of step 4.
    """
    return (max(values) - min(values)) / min(values)


#: The operator's AED half, if it has ever run on this box.  Gitignored since
#: `ANS-1` (14305c5): Ansys licence terms restrict disclosure of benchmark
#: results, so nothing read from here may reach a tracked file.
AED_RESULTS_PATH = CASE_DIR / "aed_results" / "ans2_aed_results.json"


def _load_aed_results():
    if not AED_RESULTS_PATH.exists():
        return None
    return json.loads(AED_RESULTS_PATH.read_text())


def _write_comparison(m, *, private: bool = False) -> Path:
    """The SPEC's export tables, our columns regenerated, AED columns blank.

    `ANS-1`'s rule: our side is written from ``m`` — the payload this run just
    produced — and never transcribed, so a benchmark cannot drift from the
    gate.  When ``private`` is set the AED columns are filled from the
    gitignored results file into the gitignored ``COMPARISON_private.md``; the
    tracked file's AED columns stay verbatim blank.
    """
    aed = _load_aed_results() if private else None

    def a(order, key):
        if not aed:
            return "  "
        return f" {aed.get(order, {}).get(key, '')} "

    points = m["named_points_m"]

    def point_rows(field, fmt):
        rows = []
        for j, p in enumerate(points):
            cells = "|".join(
                f" {fmt(m['pointwise'][str(k)][field][j])} " for k in range(4)
            )
            rows.append(
                f"| ({p[0]:+.3f}, {p[1]:+.3f}, {p[2]:+.3f}) |{cells}|"
                f"{a('zero_order', f'sar_point_{j}')}|"
                f"{a('first_order', f'sar_point_{j}')}|"
            )
        return "\n".join(rows)

    def per_drive(getter, fmt):
        return "|".join(f" {fmt(getter(str(k)))} " for k in range(4))

    path = CASE_DIR / ("COMPARISON_private.md" if private else "COMPARISON.md")
    path.write_text(
        f"""# ANS-2 — coil-driven SAR, loaded four-leg birdcage, 10 MHz: comparison table

{'**PRIVATE FILE — gitignored.** AED numbers appear below; nothing here may be quoted in a tracked file, a journal or a commit message (operator directive 2026-09-02, Ansys licence terms).' if private else '**Our columns are regenerated by `02_birdcage_coil_driven_sar_10MHz.py` on every run — never transcribed** (`ANS-1`\'s rule: a benchmark cannot drift from the gate). **The AED columns are deliberately blank**; the human operator fills them from the replication described in `SPEC.md`, into the gitignored `aed_results/` (never here).'}

Generated {m["generated_utc"]} at `mpiexec -n {m["mpi_ranks"]}`.

**Scope: SPEC export rows 1–3, 7 and 8 only.** Rows 4–6 (mass-averaged and
peak-over-phantom SAR) are held for `ANS-2` step 2 — our operator averages over
a **sphere** of equal mass, IEC 62704-1 and hence HFSS over a **cube**, and the
SPEC forbids reading a rows-4–6 miss as a finding until rows 1–3 have agreed.

## Normalisation — the one mismatch that passes every self-check on both sides

| Item | Ours (FEM) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|
| Drive | `V_src` = {m["excitation"]["0"]["source_voltage_v"]["re"]:.4f} V behind {REFERENCE_IMPEDANCE_OHM:.1f} Ω, one port at a time, the other three terminated in {TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ω |{a("zero_order", "drive")}|{a("first_order", "drive")}|
| Incident power `\|V_src\|²/(8Z₀)` (peak phasors) | **{m["excitation"]["0"]["incident_power_w"]:.7e} W** (HFSS's default is 1 W; this read `V²/(4Z₀)` = 5.0e-03 W until 2026-09-18, a factor of two high) |{a("zero_order", "incident_power")}|{a("first_order", "incident_power")}|

SAR is quadratic in the field and therefore **linear in incident power**. The
ratio is carried explicitly and applied by the adjudicating review; **nothing is
rescaled here and HFSS's normalisation is not matched.**

## Row 1 — pointwise SAR `σ|E|²/(2ρ)` at the four named points [W/kg]

Rows are the named points, columns are the driven port.

| Point (x, y, z) [m] | driven P1 | driven P2 | driven P3 | driven P4 | AED (Zero Order) | AED (First Order) |
|---|---|---|---|---|---|---|
{point_rows("sar_w_per_kg", lambda v: f"{v:.9e}")}

`|E|` at the same points [V/m], for a normalisation-free cross-check:

| Point (x, y, z) [m] | driven P1 | driven P2 | driven P3 | driven P4 | AED (Zero Order) | AED (First Order) |
|---|---|---|---|---|---|---|
{point_rows("e_magnitude_v_per_m", lambda v: f"{v:.9e}")}

## Row 2 — whole-phantom dissipated power `½∫σ|E|² dV` [W]

| Quantity | driven P1 | driven P2 | driven P3 | driven P4 |
|---|---|---|---|---|
| Ours (FEM) |{per_drive(lambda k: m["phantom_power"][k]["dissipated_power_w"], lambda v: f"{v:.9e}")}|
| AED (Zero Order) |{a("zero_order", "power_p1")}|{a("zero_order", "power_p2")}|{a("zero_order", "power_p3")}|{a("zero_order", "power_p4")}|
| AED (First Order) |{a("first_order", "power_p1")}|{a("first_order", "power_p2")}|{a("first_order", "power_p3")}|{a("first_order", "power_p4")}|

**The cleanest single number in the case** (SPEC): one volume integral, no
sampling, no averaging convention.

## Row 3 — whole-phantom average SAR [W/kg]

Row 2 divided by the **meshed** phantom mass
{m["phantom_power"]["0"]["meshed_mass_kg"]:.9e} kg (meshed volume
{m["phantom_power"]["0"]["meshed_volume_m3"]:.9e} m³ against the CAD closed form
{m["phantom_volume_closed_form_m3"]:.9e} m³ — a faceted cylinder under-fills its
CAD volume, and the *meshed* mass is the honest denominator for our integral).

| Quantity | driven P1 | driven P2 | driven P3 | driven P4 |
|---|---|---|---|---|
| Ours (FEM) |{per_drive(lambda k: m["phantom_power"][k]["average_sar_w_per_kg"], lambda v: f"{v:.9e}")}|
| AED (Zero Order) |{a("zero_order", "avg_sar_p1")}|{a("zero_order", "avg_sar_p2")}|{a("zero_order", "avg_sar_p3")}|{a("zero_order", "avg_sar_p4")}|
| AED (First Order) |{a("first_order", "avg_sar_p1")}|{a("first_order", "avg_sar_p2")}|{a("first_order", "avg_sar_p3")}|{a("first_order", "avg_sar_p4")}|

## Row 7 — excitation metadata

| Quantity | driven P1 | driven P2 | driven P3 | driven P4 |
|---|---|---|---|---|
| Incident power [W] |{per_drive(lambda k: m["excitation"][k]["incident_power_w"], lambda v: f"{v:.7e}")}|
| Supplied Re P [W] |{per_drive(lambda k: m["excitation"][k]["supplied_power_re_w"], lambda v: f"{v:.9e}")}|
| Accepted Re P [W] |{per_drive(lambda k: m["excitation"][k]["accepted_power_re_w"], lambda v: f"{v:.9e}")}|
| Accepted \\|Im P\\|/Re P |{per_drive(lambda k: m["excitation"][k]["accepted_im_over_re"], lambda v: f"{v:.6f}")}|

AED's per-solve incident power (or incident voltage) and accepted power go in
`aed_results/`; the SPEC requires them **reported**, not matched.

## Row 8 — solve metadata

| Item | Ours (FEM) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|
| Elements | {m["n_cells"]} tetrahedra (`MAT-4` step 5b record {ONE_GRAM_RUNG_CELL_RECORD}, ratio {m["cell_ratio"]:.6f}, asserted inside {CELL_COUNT_BAND * 100:.0f}%) |{a("zero_order", "elements")}|{a("first_order", "elements")}|
| Phantom elements | {m["n_phantom_cells"]} (record {ONE_GRAM_RUNG_PHANTOM_CELL_RECORD}, ratio {m["phantom_cell_ratio"]:.6f}, asserted inside {CELL_COUNT_BAND * 100:.0f}%) |{a("zero_order", "phantom_elements")}|{a("first_order", "phantom_elements")}|
| Basis order | {BASIS_ORDER}, {BASIS_UNKNOWNS_PER_TET} unknowns/tet = {AED_ORDER_CORRESPONDENCE} |{a("zero_order", "basis_order")}|{a("first_order", "basis_order")}|
| Adaptive passes | n/a — fixed graded mesh at `phantom_resolution` = {PHANTOM_RESOLUTION_1G_RUNG} m (`GEO-27`'s rung), one non-adaptive solve per port |{a("zero_order", "passes")}|{a("first_order", "passes")}|
| Final ΔS | n/a — non-adaptive |{a("zero_order", "delta_s")}|{a("first_order", "delta_s")}|
| Solve time | {" + ".join(f"{t:.1f} s" for t in m["solve_seconds"])} for the four drives at `mpiexec -n {m["mpi_ranks"]}`; {m["total_seconds"]:.1f} s wall for the whole script |{a("zero_order", "solve_time")}|{a("first_order", "solve_time")}|
| Port model | 4 lumped-element sheets, `Z_p` = {TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ω on every undriven port, `Z₀` = {REFERENCE_IMPEDANCE_OHM:.1f} Ω |{a("zero_order", "port_model")}|{a("first_order", "port_model")}|
| Frequency | {m["frequency_hz"]:.6e} Hz |{a("zero_order", "frequency")}|{a("first_order", "frequency")}|

## What this run asserted (all bands and records imported, none moved)

| Anchor | Reading | Band | Source of the band |
|---|---|---|---|
| 10 g C4 cyclic pairs | {" / ".join(f"{m['ten_pairs'][str(k)] * 100:.4f}%" for k in range(4))} | {C4_COVARIANCE_BAND * 100:.1f}% | `MAT-4` step 4 |
| 1 g C4 cyclic pairs | {" / ".join(f"{m['one_pairs'][str(k)] * 100:.4f}%" for k in range(4))} | {C4_COVARIANCE_BAND * 100:.1f}% | `MAT-4` step 5b |
| Whole-phantom coverage identity (power) | {m["coverage"]["power_miss"]:.6e} | {EXACT_IDENTITY_RTOL:.0e} | `MAT-4` step 4 |
| Whole-phantom coverage identity (mass) | {m["coverage"]["mass_miss"]:.6e} | {EXACT_IDENTITY_RTOL:.0e} | `MAT-4` step 4 |
| Mesh, total / phantom | {m["n_cells"]} / {m["n_phantom_cells"]} | {CELL_COUNT_BAND * 100:.0f}% | `MAT-4` step 5b records |
| **Negative control** — mis-paired 1 g `(c_{{k+2}}; k)` | {" / ".join(f"{m['control_1g'][str(k)] * 100:.4f}%" for k in range(4))} | asserted **≥ {CONTROL_SEPARATION:.0f}×** the {C4_COVARIANCE_BAND * 100:.1f}% band | this run |

The negative control is the reason the C4 identity is not vacuous: the far-side
ball under the same drive misses by ~{min(m["control_1g"][str(k)] for k in range(4)) * 100:.0f}%
where the cyclic pair misses by ~{max(m["one_pairs"][str(k)] for k in range(4)) * 100:.2f}%.

## Provenance

* Gated path: `tests/validation/test_birdcage_sar_mass_averaged.py`
  (`MAT-4` step 4) and `tests/validation/test_birdcage_sar_1g_rung.py`
  (`MAT-4` step 5b) — the construction, every band and both mesh records above
  are imported from them, never restated.
* Fixture: `GEO-18` gapped + sheeted four-leg birdcage, phantom loaded, on
  `GEO-27`'s `phantom_resolution` = {PHANTOM_RESOLUTION_1G_RUNG} m rung.
* Element-order correspondence: `ANS-5` ruling, 2026-08-30.
* Field export: `paraview_output/{BASENAME}.xdmf` (regenerated each run, not
  tracked) — `E_real`/`E_imag`/`E_magnitude` (CG1) and `B_magnitude` (DG0) for
  the port-1 drive, beside `CellTags` ({CONDUCTOR_CELL_TAG} = conductor,
  {PHANTOM_CELL_TAG} = phantom).

## What an agreement would license — and what it would not

**Would license** the first absolute, externally checked statement about
coil-driven SAR in this repository, and promotion of the `MAT-4` C4 identity
from a self-consistency gate to a gate with an external absolute anchor.
**Would not license** anything at 64 or 128 MHz, any C95.3 *compliance*
statement, any homogeneity or B₁⁺ claim, or anything about a quadrature drive.
Until the AED columns are filled this file states **no** absolute-accuracy
claim at all.
"""
    )
    return path


def _print_step4_readout(m) -> None:
    """The `ANS-2` step 4 readout: the XL window's whole reason to exist.

    Prints the four driven-point SAR samples, their C4 sampling spread and the
    four whole-phantom powers **beside the 0.0025 rung's own tracked
    ``metrics.json``** — which an overridden run never overwrites, so the
    reference is the committed record and not a number restated here.  Printed
    only; the pre-registered decision rule
    (`docs/private/ans2-adjudication-2026-09-18.md`, §7 `ANS-2` step 4) is
    applied by the review that reads the ledger row, and **no band moves in the
    window**.
    """
    ref = _load_reference_metrics()
    ref_points = (
        [float(ref["pointwise"][str(k)]["sar_w_per_kg"][k]) for k in range(4)]
        if ref
        else None
    )
    mine = [float(m["pointwise"][str(k)]["sar_w_per_kg"][k]) for k in range(4)]
    powers = [float(m["phantom_power"][str(k)]["dissipated_power_w"]) for k in range(4)]
    print(
        f"\n[ANS-2 step 4] READOUT at phantom_resolution = "
        f"{m['phantom_resolution_m']} m ({m['n_cells']} cells / "
        f"{m['n_phantom_cells']} phantom), against the tracked "
        f"{PHANTOM_RESOLUTION_1G_RUNG} m rung "
        f"({'metrics.json' if ref else 'NO reference metrics.json in this clone'}):",
        flush=True,
    )
    print(
        "[ANS-2 step 4] driven-point SAR sigma|E|^2/(2 rho) [W/kg] — drive Pk "
        "read at the k-th named point, the four samples C4 symmetry makes equal:",
        flush=True,
    )
    for k in range(4):
        line = f"        drive P{k + 1} @ point {k}   {mine[k]:.9e}"
        if ref_points:
            r = ref_points[k]
            line += f"   (0.0025 rung {r:.9e}, change {(mine[k] / r - 1.0) * 100:+.3f}%)"
        print(line, flush=True)
    print(
        f"[ANS-2 step 4] C4 SAMPLING SPREAD (max-min)/min = "
        f"{_spread(mine) * 100:.3f}%"
        + (f"   (0.0025 rung {_spread(ref_points) * 100:.3f}%)" if ref_points else "")
        + "   — HFSS reads 0.02% on its own mesh; PRINTED, NEVER GATED",
        flush=True,
    )
    print(
        "[ANS-2 step 4] whole-phantom dissipated power [W] — one volume "
        "integral, no sampling, the cleanest number in the case:",
        flush=True,
    )
    for k in range(4):
        line = f"        drive P{k + 1}   {powers[k]:.12e}"
        if ref:
            r = float(ref["phantom_power"][str(k)]["dissipated_power_w"])
            line += f"   (0.0025 rung {r:.12e}, change {(powers[k] / r - 1.0) * 100:+.4f}%)"
        print(line, flush=True)
    print(
        "[ANS-2 step 4] the decision rule is the review's, not this run's: "
        "nothing above is asserted and no band is moved here.",
        flush=True,
    )


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ans:` group)."
        )

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            "ANS-2 step 1 - coil-driven SAR, loaded 4-leg birdcage, 10 MHz "
            "(runnable half, SPEC rows 1-3, 7, 8)",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            f"[ANS-2] fixture `GEO-18` gapped + sheeted birdcage, phantom loaded "
            f"(conductor tag {CONDUCTOR_CELL_TAG}, phantom tag {PHANTOM_CELL_TAG}) "
            f"on `GEO-27`'s phantom_resolution = {PHANTOM_RESOLUTION_M} m rung\n"
            f"[ANS-2] basis: {BASIS_ORDER}, {BASIS_UNKNOWNS_PER_TET} unknowns/tet "
            f"= {AED_ORDER_CORRESPONDENCE}\n"
            f"[ANS-2] scope: rows 1-3, 7, 8.  Rows 4-6 held for step 2 (the "
            "sphere-vs-cube averaging systematic the SPEC pre-registers).  NO "
            "absolute-SAR, compliance, homogeneity, B1+, Larmor or quadrature "
            "claim from our side.",
            flush=True,
        )
        if RESOLUTION_OVERRIDDEN:
            print(
                f"[ANS-2 step 4] {PHANTOM_RESOLUTION_ENV}="
                f"{_RESOLUTION_OVERRIDE} — running at phantom_resolution = "
                f"{PHANTOM_RESOLUTION_M} m instead of the "
                f"{PHANTOM_RESOLUTION_1G_RUNG} m record rung.  Outputs are "
                f"resolution-tagged (metrics{RESOLUTION_TAG}.json, "
                f"{BASENAME}{RESOLUTION_TAG_PATHSAFE}.xdmf) and COMPARISON.md / "
                "COMPARISON_private.md are NOT rewritten — the tracked "
                "comparison stays the 0.0025 rung's.",
                flush=True,
            )

    # -- the fixture: `MAT-4` step 4's own construction on step 5b's rung -----
    built = _build_mass_averaged(phantom_resolution=PHANTOM_RESOLUTION_M)
    _add_one_gram_control(built)

    named_points = np.array(
        [
            [+CENTRE_RADIUS_M, 0.0, 0.0],
            [0.0, +CENTRE_RADIUS_M, 0.0],
            [-CENTRE_RADIUS_M, 0.0, 0.0],
            [0.0, -CENTRE_RADIUS_M, 0.0],
        ],
        dtype=np.float64,
    )

    pointwise = _pointwise_sar(built, named_points, comm)
    powers = _phantom_power(built)
    excitation = {k: _excitation(built["solves"][f"P{k + 1}"]) for k in range(4)}

    coverage = {
        "power_miss": float(
            abs(
                built["whole"]["dissipated_power_w"]
                / built["tagged"]["dissipated_power_w"]
                - 1.0
            )
        ),
        "mass_miss": float(
            abs(
                built["whole"]["mass_kg"]
                / (PHANTOM_RHO_KG_PER_M3 * built["tagged"]["volume_m3"])
                - 1.0
            )
        ),
    }

    written = _write_paraview(built, comm)
    total = time.perf_counter() - started

    payload = {
        "case": "ANS-2 step 1 — coil-driven SAR, loaded four-leg birdcage, 10 MHz",
        "scope": (
            "SPEC export rows 1-3, 7, 8 only; rows 4-6 held for step 2 "
            "(sphere-vs-cube averaging systematic). Runnable half: no "
            "adjudication, no absolute-SAR or compliance claim."
        ),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mpi_ranks": int(comm.size),
        "frequency_hz": float(FREQUENCY_HZ),
        "basis_order": BASIS_ORDER,
        "basis_unknowns_per_tet": BASIS_UNKNOWNS_PER_TET,
        "aed_order_correspondence": AED_ORDER_CORRESPONDENCE,
        "phantom_resolution_m": float(PHANTOM_RESOLUTION_M),
        "phantom_sigma_s_per_m": float(SALINE_SIGMA),
        "phantom_rho_kg_per_m3": float(PHANTOM_RHO_KG_PER_M3),
        "phantom_volume_closed_form_m3": PHANTOM_VOLUME_CLOSED_FORM_M3,
        "n_cells": int(built["cells"]),
        "n_phantom_cells": int(built["phantom_cells"]),
        "cell_ratio": float(built["cells"] / ONE_GRAM_RUNG_CELL_RECORD),
        "phantom_cell_ratio": float(
            built["phantom_cells"] / ONE_GRAM_RUNG_PHANTOM_CELL_RECORD
        ),
        "named_points_m": named_points.tolist(),
        "pointwise": {str(k): v for k, v in pointwise.items()},
        "phantom_power": {str(k): v for k, v in powers.items()},
        "excitation": {str(k): v for k, v in excitation.items()},
        "coverage": coverage,
        "ten_pairs": {str(k): float(v) for k, v in built["ten_pairs"].items()},
        "one_pairs": {str(k): float(v) for k, v in built["one_pairs"].items()},
        "control_1g": {str(k): float(v) for k, v in built["control_1g"].items()},
        "c4_covariance_band": float(C4_COVARIANCE_BAND),
        "exact_identity_rtol": float(EXACT_IDENTITY_RTOL),
        "cell_count_band": float(CELL_COUNT_BAND),
        "control_separation_multiple": float(CONTROL_SEPARATION),
        "solve_seconds": [
            float(built["solves"][f"P{k + 1}"]["solve_time"]) for k in range(4)
        ],
        "total_seconds": float(total),
        "paraview_output": str(written),
    }

    if comm.rank == 0:
        print(
            f"\n[ANS-2] ROW 1 — POINTWISE SAR sigma|E|^2/(2 rho) at the four named "
            f"points (sigma = {SALINE_SIGMA:.9e} S/m imported and gated uniform, "
            f"rho = {PHANTOM_RHO_KG_PER_M3:.1f} kg/m^3); rows are drives, columns "
            f"are the points (+x, +y, -x, -y at r = {CENTRE_RADIUS_M} m):",
            flush=True,
        )
        for k in range(4):
            row = "  ".join(f"{v:.9e}" for v in pointwise[k]["sar_w_per_kg"])
            print(f"        drive P{k + 1}  {row}  W/kg", flush=True)
        print(
            "[ANS-2] ROW 2/3 — WHOLE-PHANTOM DISSIPATED POWER and AVERAGE SAR "
            f"(meshed phantom volume {powers[0]['meshed_volume_m3']:.9e} m^3 vs "
            f"the CAD closed form {PHANTOM_VOLUME_CLOSED_FORM_M3:.9e} m^3):",
            flush=True,
        )
        for k in range(4):
            print(
                f"        drive P{k + 1}  power {powers[k]['dissipated_power_w']:.12e} W"
                f"   average SAR {powers[k]['average_sar_w_per_kg']:.9e} W/kg",
                flush=True,
            )
        print(
            "[ANS-2] ROW 7 — EXCITATION.  NORMALISATION IS CARRIED, NEVER "
            "MATCHED: our incident power is "
            f"{excitation[0]['incident_power_w']:.7e} W (V_src = 1 V behind "
            f"{REFERENCE_IMPEDANCE_OHM:.0f} Ohm); HFSS's default is 1 W.  SAR is "
            "LINEAR in incident power; the adjudicating review applies the ratio.",
            flush=True,
        )
        for k in range(4):
            e = excitation[k]
            print(
                f"        drive P{k + 1}  incident {e['incident_power_w']:.7e} W   "
                f"supplied Re P {e['supplied_power_re_w']:.9e} W   "
                f"accepted Re P {e['accepted_power_re_w']:.9e} W   "
                f"|Im P|/Re P {e['accepted_im_over_re']:.6f} (PRINTED, NEVER GATED)",
                flush=True,
            )
        print(
            f"[ANS-2] ROW 8 — SOLVE METADATA: {built['cells']} cells "
            f"({built['phantom_cells']} tag-3) at mpiexec -n {comm.size}, "
            f"{BASIS_ORDER}, four drives in "
            + " + ".join(f"{t:.2f} s" for t in payload["solve_seconds"])
            + f", {total:.1f} s wall",
            flush=True,
        )
        print(
            "[ANS-2] ANCHORS — every band and every record IMPORTED from the "
            "`MAT-4` gate modules, none restated and none moved:",
            flush=True,
        )
        for k in range(4):
            print(
                f"        k={k}->{(k + 1) % 4}  10 g "
                f"{built['ten_pairs'][k] * 100:9.4f}%   1 g "
                f"{built['one_pairs'][k] * 100:9.4f}%   ASSERTED <= "
                f"{C4_COVARIANCE_BAND * 100:.1f}%   mis-paired 1 g control "
                f"(c_{(k + 2) % 4}; {k}) {built['control_1g'][k] * 100:9.4f}%  "
                f"ASSERTED >= {CONTROL_SEPARATION * C4_COVARIANCE_BAND * 100:.0f}% "
                f"({CONTROL_SEPARATION:.0f}x the band)",
                flush=True,
            )
        print(
            f"        coverage identity: power {coverage['power_miss']:.6e}, mass "
            f"{coverage['mass_miss']:.6e}, ASSERTED <= {EXACT_IDENTITY_RTOL:.0e}",
            flush=True,
        )
        if RESOLUTION_OVERRIDDEN:
            print(
                f"[ANS-2 step 4] MESH-RECORD ASSERTIONS SKIPPED — "
                f"phantom_resolution = {PHANTOM_RESOLUTION_M} m is not the "
                f"{PHANTOM_RESOLUTION_1G_RUNG} m rung the `MAT-4` step 5b records "
                f"({ONE_GRAM_RUNG_CELL_RECORD} / "
                f"{ONE_GRAM_RUNG_PHANTOM_CELL_RECORD} cells at the imported "
                f"{CELL_COUNT_BAND * 100:.0f}% CELL_COUNT_BAND) were measured on, "
                f"and this rung has no record yet.  Measured here: "
                f"{built['cells']} cells / {built['phantom_cells']} phantom "
                "(tag-3) cells — a CANDIDATE record for a review, asserted "
                "against nothing.  Every other band above stays asserted.",
                flush=True,
            )
        else:
            print(
                f"        mesh: {built['cells']} vs record "
                f"{ONE_GRAM_RUNG_CELL_RECORD} "
                f"(ratio {payload['cell_ratio']:.6f}), phantom "
                f"{built['phantom_cells']} vs {ONE_GRAM_RUNG_PHANTOM_CELL_RECORD} "
                f"(ratio {payload['phantom_cell_ratio']:.6f}), ASSERTED inside "
                f"{CELL_COUNT_BAND * 100:.0f}%",
                flush=True,
            )

    # -- the assertions.  Every band imported; none is restated or moved. -----
    for k in range(4):
        assert built["ten_pairs"][k] <= C4_COVARIANCE_BAND, (
            f"the 10 g C4 pair k={k}->{(k + 1) % 4} reads "
            f"{built['ten_pairs'][k] * 100:.4f}%, outside the imported "
            f"{C4_COVARIANCE_BAND * 100:.1f}% C4_COVARIANCE_BAND — the example "
            "and the `MAT-4` gate have diverged (report both readings; never "
            "widen the band here)"
        )
        assert built["one_pairs"][k] <= C4_COVARIANCE_BAND, (
            f"the 1 g C4 pair k={k}->{(k + 1) % 4} reads "
            f"{built['one_pairs'][k] * 100:.4f}%, outside the imported "
            f"{C4_COVARIANCE_BAND * 100:.1f}% C4_COVARIANCE_BAND — the example "
            "and the `MAT-4` step 5b gate have diverged"
        )
        # The negative control: the far-side ball under the same drive. Asserted
        # as a *floor* (>= 10x the band) rather than against step 5b's measured
        # 87.01-87.06% — an example must not re-record a gate digit (`ANS-1`).
        assert built["control_1g"][k] >= CONTROL_SEPARATION * C4_COVARIANCE_BAND, (
            f"the mis-paired 1 g control (c_{(k + 2) % 4}; {k}) reads "
            f"{built['control_1g'][k] * 100:.4f}%, under "
            f"{CONTROL_SEPARATION:.0f}x the {C4_COVARIANCE_BAND * 100:.1f}% band "
            "— the C4 identity above would then be measuring a constant field "
            "rather than a covariance, and nothing in rows 1-3 is trustworthy"
        )

    assert coverage["power_miss"] <= EXACT_IDENTITY_RTOL, (
        f"the enclosing-ball power misses the tag-3 integral by "
        f"{coverage['power_miss']:.6e} > {EXACT_IDENTITY_RTOL:.0e} — missed "
        "cells, double-counted ghosts, or an unreduced local sum"
    )
    assert coverage["mass_miss"] <= EXACT_IDENTITY_RTOL, (
        f"the enclosing-ball mass misses rho*V_phantom by "
        f"{coverage['mass_miss']:.6e} > {EXACT_IDENTITY_RTOL:.0e}"
    )
    # The two version-tagged mesh records belong to the 0.0025 m rung alone;
    # `ANS-2` step 4a skips them — and only them — when the knob moves the rung
    # (the skip is printed above, never silent).
    if not RESOLUTION_OVERRIDDEN:
        assert abs(payload["cell_ratio"] - 1.0) < CELL_COUNT_BAND, (
            f"the rung meshes to {built['cells']} cells against the `MAT-4` step 5b "
            f"record {ONE_GRAM_RUNG_CELL_RECORD} (ratio "
            f"{payload['cell_ratio']:.6f}) — outside the imported "
            f"{CELL_COUNT_BAND * 100:.0f}% CELL_COUNT_BAND"
        )
        assert abs(payload["phantom_cell_ratio"] - 1.0) < CELL_COUNT_BAND, (
            f"the phantom (tag 3) carries {built['phantom_cells']} cells against the "
            f"record {ONE_GRAM_RUNG_PHANTOM_CELL_RECORD} (ratio "
            f"{payload['phantom_cell_ratio']:.6f}) — outside the imported "
            f"{CELL_COUNT_BAND * 100:.0f}% CELL_COUNT_BAND"
        )

    if comm.rank == 0 and RESOLUTION_OVERRIDDEN:
        _print_step4_readout(payload)

    if comm.rank == 0:
        metrics_path = _write_metrics(payload)
        private_note = ""
        if RESOLUTION_OVERRIDDEN:
            comparison_note = (
                "COMPARISON.md NOT rewritten (`ANS-2` step 4a: the tracked "
                "comparison stays the 0.0025 rung's)"
            )
        else:
            comparison_path = _write_comparison(payload)
            comparison_note = f"{comparison_path.name} (AED columns verbatim blank)"
            if AED_RESULTS_PATH.exists():
                _write_comparison(payload, private=True)
                private_note = (
                    "\n[ANS-2] AED results found — COMPARISON_private.md rewritten "
                    "(gitignored; nothing from it may reach a tracked file)"
                )
        print(
            f"\n[ANS-2] wrote {metrics_path.name}, {comparison_note} and "
            f"{Path(written).name}{private_note}\n"
            "[ANS-2] ALL ANCHORS GREEN.  This closes the RUNNABLE HALF only: "
            "`ANS-2` stays amber pending SPEC rows 4-6 (step 2) and the "
            "operator's AED replication (step 3).  No absolute-SAR or "
            "compliance claim follows from this run.",
            flush=True,
        )


if __name__ == "__main__":
    main()
