"""ANS-6 — copper birdcage, phantom-loaded, four lumped ports: the runnable half.

`ANS-6` (PROJECT_PLAN §7), the fifth commissioned Ansys Electronics Desktop
benchmark (§5.4) and the first with a realistic conductor: the `ANS-4` fixture
with the coil's exterior treated as either a copper Leontovich surface
(σ = 5.8e7 S/m, `TH-14` step 2) or a PEC hole (`TH-15` step 3). `SPEC.md`
beside this file is the authority for the boundary-value problem the human
operator replicates in AED; this script produces *our* half of it and writes:

* ``metrics.json`` — the full complex 4×4 ``Z`` and ``S`` at each of the three
  frequencies, for both coil columns, the loss partition ``P_coil/P_in`` (Cu
  only), the σ-ladder negative control, and mesh/timing metadata
* ``COMPARISON.md`` — the SPEC's export tables with our columns filled and the
  AED columns (Cu **and** PEC, both blank) ready for the operator
* ``paraview_output/ans6_copper_birdcage_four_port_128mhz_combined.xdmf`` —
  mesh, CellTags and the port-1-driven copper ``E``/``B`` phasor magnitudes at
  128 MHz

**Nothing here is transcribed, and nothing is re-implemented (`ANS-1`).**
Every band, record and construction is imported from
``tests/validation/test_th14_birdcage_copper.py`` (the Cu column and the PEC
reference it already builds as "`TH-15` step 3's fixture verbatim") and
``tests/validation/test_th15_birdcage_pec_hole.py`` (the PEC column, as an
independent cross-check on its own separately-built mesh). The only change
either gate module needed was additive: `TH-14`'s ``ladder`` fixture body is
lifted, unchanged, to a module-level ``_build_ladder()`` so this script can
call it directly instead of through pytest's fixture machinery (rule (a));
`TH-14`'s own gate tests are re-run green in the same slot this change
landed.

**Anchors** (§7 `ANS-6`, §9 item 14).
(a) Per column (Cu, PEC) and frequency, the reciprocity / passivity / C4-class
    gates at their imported bands (`RECIPROCITY_BAND`, `PASSIVITY_SIGMA_TOLERANCE`,
    `ADJACENT_SPREAD_BAND`) — asserted here for both columns; `TH-14`'s own
    suite already asserts them for Cu, this script asserts them again on its
    own (separately built, for PEC) run.
(b) The copper surface-loss identity residual at the imported
    `DISCRETE_IDENTITY_RTOL` (1e-6).
(c) The PEC column reproduced to the digit: `TH-15` step 3's own
    ``_hole_rung`` — a *second*, independently meshed and solved PEC route —
    is called at 10 MHz and its ``S``/``Z`` compared to `TH-14`'s embedded PEC
    reference (`rec["pec"]`) from the *same* mesh `TH-14` builds; two
    independent builds of "the coil as a hole" agreeing at
    ``PEC_CROSS_CHECK_RTOL`` is the reproduction.
(d) `TH-14`'s own printed ``P_coil/P_in`` is not re-derived: this script calls
    `TH-14`'s own ``_build_ladder()`` fresh in this run and reads the ratio
    directly off its ``power`` dict, so the number in ``metrics.json`` *is*
    the value the `TH-14` module computes here — not a restated constant, and
    not a value read off an old log.

**Negative control (asserted, imported).** `TH-14`'s own σ-ladder PEC limit:
at σ = 5.8e11 S/m the per-class ``max|S_σ − S_PEC|`` is *predicted* (rule (e))
to fall at or below `PREDICTED_PEC_LIMIT_MAX_ABS_DS` (1e-4) — printed, never
asserted, exactly as `TH-14` treats it. Predicted and printed alongside it:
``|S(Cu) − S(PEC)|`` per C4 class per frequency (`TH-14`'s ``class_ds``).

**Out of scope** (SPEC "Out of scope", §7 `ANS-6`). Runnable half only: no
adjudication, no tuning / resonance / absolute-accuracy claim from our side,
degree 1 only (no order sweep — that is a later `ANS-6` step), no B1+, no SAR.
No absolute `S₁₁` / `Z_in` claim at 10 or 64 MHz (`PORT-21`, known-issues
2026-09-19).

Run it through the example runner (the ``ans:`` group sources the complex
build automatically)::

    ./run_examples.sh -e ans:6 -n 2 -t 590
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

from dolfinx import default_scalar_type

# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gate modules' constants and fixtures are importable rather than
# restated (the `ANS-1` rule, as `ANS-4` does for `EX-34`).
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.core.cavity import surface_resistance_ohm  # noqa: E402
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.setup_figure import write_setup_figure  # noqa: E402
from fem_em_solver.ports.lumped import run_lumped_sheet_port_case  # noqa: E402

from tests.mesh.test_birdcage_port_sheets import _build as _sheets_build  # noqa: E402
from tests.mesh.test_birdcage_port_tags import LEG_COUNT  # noqa: E402
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    PASSIVITY_SIGMA_TOLERANCE,
)
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND  # noqa: E402
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    ADJACENT_SPREAD_BAND,
    PHANTOM_CELL_TAG,
)
from tests.validation.test_port_package_sparameters import (  # noqa: E402
    REFERENCE_IMPEDANCE_OHM,
)
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    TERMINATED_PORT_IMPEDANCE_OHM,
)
from tests.validation.test_th14_birdcage_copper import (  # noqa: E402
    CLASSES,
    COPPER_SIGMA,
    DISCRETE_IDENTITY_RTOL,
    DRIVEN,
    FREQS_ENV,
    FREQUENCIES_HZ,
    OUTER_BOX_TAG,
    PREDICTED_PEC_LIMIT_MAX_ABS_DS,
    SIGMA_LADDER,
    _build_ladder,
    _build_ports,
    _leontovich_term,
    _outer_box_tags,
    _problem,
)
from tests.validation.test_th15_birdcage_pec_hole import _hole_rung  # noqa: E402


def _load_example(path: Path, module_name: str):
    """Import an ``examples/`` script by path (its basename starts with a digit).

    Same pattern as `ANS-4`: ``importlib`` by file location, not ``__import__``
    on a synthesised name — the `ans:` and `ports:` scripts both carry
    group-and-number prefixes and a name-based import silently depends on
    which prefix scheme was current when it was written (the `EX-37`
    regression this avoids).
    """
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# `EX-34`'s own ParaView field builder (E_real/E_imag/E_magnitude, B_magnitude
# from Faraday's law), imported rather than re-implemented -- the `ANS-4`
# pattern.
_EX34 = _load_example(
    _REPO_ROOT / "examples" / "ports" / "05_birdcage_larmor_frequency_ladder.py",
    "ex34_birdcage_larmor_frequency_ladder_for_ans6",
)
_paraview_fields = _EX34._paraview_fields

CASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = CASE_DIR / "paraview_output"
FIGURE_DIR = CASE_DIR / "figures"
BASENAME = "ans6_copper_birdcage_four_port_128mhz_combined"
#: The case-level name (no frequency suffix — the figure is one geometry,
#: shared by all three frequencies and both coil columns).
FIGURE_BASENAME = "ans6_copper_birdcage_four_port_10_64_128MHz"

LADDER = (("10 MHz", "10"), ("64 MHz", "64"), ("128 MHz", "128"))

#: `TH-15`'s ``_hole_rung`` and `TH-14`'s embedded PEC reference are two
#: independent mesh builds of the *same* geometry (`TH-14`'s own docstring:
#: "PEC reference: `TH-15` step 3's fixture verbatim") — deterministic gmsh
#: generation, so this identity is expected near machine precision.
PEC_CROSS_CHECK_RTOL = 1.0e-8

#: Our production discretization (`ANS-5` ruling, carried from `ANS-4`).
BASIS_ORDER = "Nedelec first kind, degree 1 (N1curl)"
BASIS_UNKNOWNS_PER_TET = 6
AED_ORDER_CORRESPONDENCE = "HFSS Zero Order (20 unknowns/tet = First Order, the AED default)"

#: `ANS-6` step 2 (T9b): the degree knob. Unset => byte-identical behaviour
#: (degree 1, full ladder, tracked ``metrics.json`` / ``COMPARISON.md``
#: rewritten as before). Set => one frequency (``FEM_EM_ANS6_FREQ_MHZ``), the
#: Cu and PEC columns only (no sigma-ladder, no PEC cross-check, no field
#: export), degree-tagged ``metrics_degree<p>_<f>MHz.json`` (untracked), the
#: tracked files never touched.
DEGREE_ENV = "FEM_EM_ANS6_DEGREE"
FREQ_ENV = "FEM_EM_ANS6_FREQ_MHZ"
#: Negative control (rule (e)): the knob reaches the solve -- every C4 class
#: moves by more than this relative amount between degree 1 (tracked
#: ``metrics.json``) and the knob's degree. ASSERTED floor.
KNOB_MOVE_FLOOR = 1.0e-6
#: ... and by no more than this (sanity ceiling, ASSERTED).
KNOB_MOVE_CEILING = 2.0
#: PREDICTED size, printed only: F-small's one-mesh order move, 6.09 / 5.38 /
#: 6.70 % at 128 MHz (`ANS-4` step 2b) => roughly 3e-2 .. 7e-2.
KNOB_MOVE_PREDICTED = (3.0e-2, 7.0e-2)


def _basis_order(degree: int) -> str:
    if degree == 1:
        return BASIS_ORDER
    return f"Nedelec first kind, degree {degree} (N1curl)"


def _basis_unknowns_per_tet(degree: int) -> int:
    # N1curl (first kind) dimension on a tetrahedron: p (p + 2)(p + 3) / 2.
    return degree * (degree + 2) * (degree + 3) // 2


def _knob_main(comm, degree: int) -> None:
    """The degree-knob route: Cu + PEC columns at one frequency, gates asserted."""
    import resource

    raw_f = os.environ.get(FREQ_ENV)
    if raw_f is None or raw_f.strip() not in FREQUENCIES_HZ:
        raise RuntimeError(
            f"{DEGREE_ENV} set requires {FREQ_ENV} in {sorted(FREQUENCIES_HZ)}; got {raw_f!r}"
        )
    key = raw_f.strip()
    label = f"{key} MHz"
    os.environ[FREQS_ENV] = key
    if comm.rank == 0:
        print(
            f"[ANS-6 step 2] degree knob: {DEGREE_ENV}={degree}, {FREQ_ENV}={key}; "
            f"basis {_basis_order(degree)}, {_basis_unknowns_per_tet(degree)} unknowns/tet; "
            "Cu + PEC columns only; tracked metrics.json / COMPARISON.md not rewritten",
            flush=True,
        )
    tracked = json.loads((CASE_DIR / "metrics.json").read_text())
    started = time.perf_counter()
    ladder = _build_ladder(degree=degree, sigmas=(COPPER_SIGMA,))
    comm.Barrier()
    elapsed = time.perf_counter() - started
    rec = ladder["freqs"][key]
    cu = rec["sigma"][COPPER_SIGMA]
    pec = rec["pec"]
    for name, sw in (("cu", cu), ("pec", pec)):
        assert sw["reciprocity"] <= RECIPROCITY_BAND, (label, name, sw["reciprocity"])
        sigma_max = float(np.max(sw["sigma"]))
        assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (label, name, sigma_max)
        for cname, value in sw["spreads"].items():
            assert value <= ADJACENT_SPREAD_BAND, (label, name, cname, value)
    assert rec["identity_residual"] <= DISCRETE_IDENTITY_RTOL, (label, rec["identity_residual"])

    moves = {}
    for name, sw in (("cu", cu), ("pec", pec)):
        s_d1 = np.asarray(
            [[complex(e["re"], e["im"]) for e in row]
             for row in tracked["rungs"][label][name]["s_matrix"]]
        )
        c1 = _class_entries(s_d1)
        cp = _class_entries(np.asarray(sw["s"]))
        moves[name] = {c: float(abs(cp[c] - c1[c]) / abs(c1[c])) for c in CLASSES}
    rss_kib = comm.allreduce(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, op=MPI.SUM)
    if comm.rank == 0:
        for name, sw in (("cu", cu), ("pec", pec)):
            print(
                f"[ANS-6 step 2] degree {degree} {label} {name}: reciprocity "
                f"{sw['reciprocity']:.3e} (band {RECIPROCITY_BAND:.0e}), sigma_max "
                f"{float(np.max(sw['sigma'])):.12f}, spreads "
                + ", ".join(f"{c} {v * 100:.4f}%" for c, v in sw["spreads"].items())
                + f"; class move vs degree 1 (ASSERTED > {KNOB_MOVE_FLOOR:.0e}, <= "
                f"{KNOB_MOVE_CEILING:g}; PREDICTED {KNOB_MOVE_PREDICTED[0]:.0e}.."
                f"{KNOB_MOVE_PREDICTED[1]:.0e}): "
                + ", ".join(f"{c} {v:.4e}" for c, v in moves[name].items()),
                flush=True,
            )
        print(
            f"[ANS-6 step 2] degree {degree} {label}: copper surface-loss identity residual "
            f"{rec['identity_residual']:.3e} (ASSERTED <= {DISCRETE_IDENTITY_RTOL:g}); "
            f"PEC sweep {rec['t_pec']:.1f} s, Cu sweep {cu['t']:.1f} s, P1 {rec['t_p1']:.1f} s; "
            f"total {elapsed:.1f} s at -n {comm.size}; summed ru_maxrss "
            f"{rss_kib / 1024 ** 2:.2f} GiB",
            flush=True,
        )
    for name in ("cu", "pec"):
        for c, v in moves[name].items():
            assert KNOB_MOVE_FLOOR < v <= KNOB_MOVE_CEILING, (name, c, v)
    if comm.rank == 0:
        out = CASE_DIR / f"metrics_degree{degree}_{key}MHz.json"
        payload = {
            "chunk": "ANS-6 step 2",
            "degree": degree,
            "basis": _basis_order(degree),
            "unknowns_per_tet": _basis_unknowns_per_tet(degree),
            "frequency": label,
            "n_cells": int(ladder["cells"]),
            "mpi_ranks": int(comm.size),
            "seconds": float(elapsed),
            "summed_ru_maxrss_gib": float(rss_kib / 1024 ** 2),
            "cu": {"s_matrix": _matrix_payload(np.asarray(cu["s"])),
                   "reciprocity": float(cu["reciprocity"]),
                   "sigma_max": float(np.max(cu["sigma"]))},
            "pec": {"s_matrix": _matrix_payload(np.asarray(pec["s"])),
                    "reciprocity": float(pec["reciprocity"]),
                    "sigma_max": float(np.max(pec["sigma"]))},
            "identity_residual": float(rec["identity_residual"]),
            "class_move_vs_degree1": moves,
        }
        out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"[ANS-6 step 2] wrote {out.name} (untracked); all gates green", flush=True)

_BLANK = " "


def _complex_entry(z: complex) -> dict:
    return {"re": float(np.real(z)), "im": float(np.imag(z))}


def _matrix_payload(m) -> list:
    return [[_complex_entry(m[i, j]) for j in range(m.shape[1])] for i in range(m.shape[0])]


def _fmt(z: complex) -> str:
    return f"{np.real(z):+.7e} {np.imag(z):+.7e}j"


def _class_entries(m):
    return {"self": m[0, 0], "adjacent": m[1, 0], "opposite": m[2, 0]}


def _write_metrics(payload) -> Path:
    path = CASE_DIR / "metrics.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def _write_comparison(m) -> Path:
    """``COMPARISON.md``: our columns filled, AED columns blank by construction.

    Ansys licence terms restrict disclosure of benchmark results (`ANS-1`,
    operator directive 2026-09-02) — this tracked table never reads
    ``aed_results/``.
    """
    path = CASE_DIR / "COMPARISON.md"

    def class_table(label, column):
        s = np.asarray(
            [[complex(e["re"], e["im"]) for e in row]
             for row in m["rungs"][label][column]["s_matrix"]]
        )
        cls = _class_entries(s)
        return "\n".join(
            f"| {label} | {column} | {name} "
            f"(S{'11' if name == 'self' else '21' if name == 'adjacent' else '31'}) "
            f"| {_fmt(value)} | {_BLANK} | {_BLANK} |"
            for name, value in cls.items()
        )

    def s_table(label, column):
        s = np.asarray(
            [[complex(e["re"], e["im"]) for e in row]
             for row in m["rungs"][label][column]["s_matrix"]]
        )
        return "\n".join(
            f"| S{i + 1}{j + 1} | {_fmt(s[i, j])} | {_BLANK} | {_BLANK} |"
            for i in range(LEG_COUNT)
            for j in range(LEG_COUNT)
        )

    def gates(column):
        return "\n".join(
            f"| {label} | {m['rungs'][label][column]['reciprocity']:.9e} | "
            f"{m['rungs'][label][column]['sigma_max']:.9f} | "
            f"{m['rungs'][label][column]['spreads']['self'] * 100:.4f} / "
            f"{m['rungs'][label][column]['spreads']['adjacent'] * 100:.4f} / "
            f"{m['rungs'][label][column]['spreads']['opposite'] * 100:.4f}% | {_BLANK} | {_BLANK} |"
            for label, _ in LADDER
        )

    classes_cu = "\n".join(class_table(label, "cu") for label, _ in LADDER)
    classes_pec = "\n".join(class_table(label, "pec") for label, _ in LADDER)
    loss = "\n".join(
        f"| {label} | {m['rungs'][label]['power']['p_coil_over_p_in']:.6f} | "
        f"{m['rungs'][label]['power']['p_phantom_over_p_in']:.6f} | {_BLANK} | {_BLANK} |"
        for label, _ in LADDER
    )
    coldiff = "\n".join(
        f"| {label} | {name} | {m['rungs'][label]['s_cu_minus_pec'][name]:.6e} |"
        for label, _ in LADDER
        for name in CLASSES
    )
    pec_cross = (
        f"10 MHz `TH-15` `_hole_rung` vs `TH-14` embedded PEC: worst relative "
        f"deviation {m['pec_cross_check']['worst_rel']:.3e} "
        f"(band {PEC_CROSS_CHECK_RTOL:.0e})"
    )

    path.write_text(
        f"""# ANS-6 — comparison table (our half filled, both AED halves blank)

The AED columns are blank **by construction** in this tracked file: AED
numbers live only in the gitignored `aed_results/` on the operator's box and
are never written here (Ansys licence terms, `ANS-1`).

Generated by `06_copper_birdcage_four_port_10_64_128MHz.py` on
{m["generated_utc"]}; every number in the "Ours (FEM)" column comes from
`tests/validation/test_th14_birdcage_copper.py`'s own `_build_ladder()` (Cu
and the embedded PEC reference) and, for the PEC cross-check,
`tests/validation/test_th15_birdcage_pec_hole.py`'s own `_hole_rung`. Nothing
is transcribed. Re-run `./run_examples.sh -e ans:6 -n 2 -t 590` to regenerate.

`SPEC.md` is the authority for the problem to be replicated: coil surface
treated as HFSS **Finite Conductivity** (Cu, σ = 5.8e7 S/m) or **Perfect E**
(PEC), both with Solve Inside off.

**Scope, before any of these numbers is quoted.** The gates below are
**self-consistency identities on one fixture** (`PORT-11`, PROJECT_PLAN §2.2)
— a port model wrong by a constant factor passes every one of them. No
resonance, tuning or absolute-accuracy claim is made from our side; no
absolute `S₁₁` / `Z_in` claim at 10 or 64 MHz (`PORT-21`). Adjudication is a
future weekly review's, after the AED numbers land.

## S-matrix, C4 classes, column Cu — the primary adjudication rows

| Frequency | Column | Class | Ours (FEM) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|---|---|
{classes_cu}

## S-matrix, C4 classes, column PEC

| Frequency | Column | Class | Ours (FEM) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|---|---|
{classes_pec}

## Full S-matrix at Z₀ = {REFERENCE_IMPEDANCE_OHM:.0f} Ω — column Cu

### 10 MHz

| Entry | Ours (FEM) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|
{s_table("10 MHz", "cu")}

### 64 MHz

| Entry | Ours (FEM) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|
{s_table("64 MHz", "cu")}

### 128 MHz

| Entry | Ours (FEM) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|
{s_table("128 MHz", "cu")}

The full complex 4×4 `Z` at every frequency and column is in `metrics.json`
(`rungs.<label>.<cu|pec>.z_matrix_ohm`); only the diagonal C4 classes are
reproduced above for PEC.

## Identities (computable by AED from its exported S) — column Cu

| Frequency | ‖S − Sᵀ‖/‖S‖ (gate {RECIPROCITY_BAND:.0e}) | σ_max(S) (gate ≤ 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e}) | C4 class spreads self / adjacent / opposite (gate {ADJACENT_SPREAD_BAND * 100:.1f}%) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|---|---|
{gates("cu")}

## Identities — column PEC

| Frequency | ‖S − Sᵀ‖/‖S‖ | σ_max(S) | C4 class spreads self / adjacent / opposite | AED (Zero Order) | AED (First Order) |
|---|---|---|---|---|---|
{gates("pec")}

## Loss partition (column Cu only) — a secondary adjudication row

| Frequency | P_coil / P_in | P_phantom / P_in | AED (Zero Order) | AED (First Order) |
|---|---|---|---|---|
{loss}

`P_coil/P_in` is not re-derived by this script: it is read directly off
`TH-14`'s own `_build_ladder()`, called fresh in this run.

## Column difference S(Cu) − S(PEC) — predicted, never asserted (rule (e))

| Frequency | Class | max\\|S_Cu − S_PEC\\| |
|---|---|---|
{coldiff}

Predicted, printed only: at σ = 5.8e11 S/m, `TH-14`'s own σ-ladder puts
`max|S_σ − S_PEC|` per class at or below {PREDICTED_PEC_LIMIT_MAX_ABS_DS:.0e}
(`PREDICTED_PEC_LIMIT_MAX_ABS_DS`) — printed in `metrics.json`, never a gate.

## PEC cross-check

{pec_cross}

## Solve metadata

| Item | Ours (FEM) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|
| Elements | {m["n_cells"]} tetrahedra | {_BLANK} | {_BLANK} |
| Basis order | {BASIS_ORDER}, {BASIS_UNKNOWNS_PER_TET} unknowns/tet | {_BLANK} | {_BLANK} |
| Port model | {LEG_COUNT} lumped-element sheets, Z_p = {TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ω on every undriven port, Z₀ = {REFERENCE_IMPEDANCE_OHM:.1f} Ω | {_BLANK} | {_BLANK} |

## Field export

`paraview_output/{BASENAME}.xdmf` (regenerated by each run, not tracked). The
port-1-driven copper case at **128 MHz**, carrying `E_real`/`E_imag`/
`E_magnitude` (CG1) and `B_magnitude` (DG0), beside `CellTags`.

## Out of scope

No tuning capacitors, no resonance or mode claim, no B₁⁺, no SAR, degree 1
only (the order sweep is a later `ANS-6` step). No absolute `S₁₁` / `Z_in`
figure at 10 or 64 MHz (`PORT-21`, known-issues 2026-09-19).

## Provenance

* Gate modules: `tests/validation/test_th14_birdcage_copper.py` (`TH-14` step
  2, ✅ 2026-09-14) and `tests/validation/test_th15_birdcage_pec_hole.py`
  (`TH-15` step 3). Every band, record and construction above is imported
  from them, never restated.
* Fixture: `GEO-18` gapped + sheeted four-leg birdcage, phantom loaded, coil
  cut from the mesh as a hole (`TH-15` step 3a).
* Element-order correspondence: `ANS-5` ruling, 2026-08-30.
"""
    )
    return path


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ans:` group)."
        )

    raw_degree = os.environ.get(DEGREE_ENV)
    if raw_degree is not None:
        _knob_main(comm, int(raw_degree))
        return

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            "ANS-6 - copper birdcage, four lumped ports, Cu and PEC columns, "
            "10 / 64 / 128 MHz (runnable half)",
            flush=True,
        )
        print("=" * 78, flush=True)

    # -- build our own mesh for the setup figure and the export solve -------
    comm.Barrier()
    t0 = time.perf_counter()
    msh, cell_tags, facet_tags, _diag, t_mesh = _sheets_build(True, as_hole=True)
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()
    ncells = int(msh.topology.index_map(tdim).size_global)
    outer_tags, census = _outer_box_tags(msh, facet_tags, comm)
    tags_f, port_defs, specs = _build_ports(msh, cell_tags, comm)
    comm.Barrier()
    t_build = time.perf_counter() - t0
    if comm.rank == 0:
        print(
            f"\n[ANS-6] fixture: hole mesh {ncells} cells, mesh+ports {t_build:.1f} s "
            f"at -n {comm.size}; outer-box census {census}",
            flush=True,
        )

    region_names = {2: "air", PHANTOM_CELL_TAG: "phantom"}
    for spec in specs:
        region_names[int(spec.facet_tag)] = f"port {spec.port_id}"
    write_setup_figure(
        msh,
        cell_tags,
        FIGURE_DIR / f"{FIGURE_BASENAME}_setup.png",
        region_names=region_names,
        hide_tags=(2,),
        translucent_tags=(PHANTOM_CELL_TAG,),
        slice_normal=(0.0, 0.0, 1.0),
        title="ans:6 -- copper birdcage, Cu and PEC coil columns (tag 401)",
        comm=comm,
    )

    # -- TH-14's own ladder: Cu column, embedded PEC reference, the sigma ----
    # -- ladder negative control and the P1 power accounting, all 3 freqs ---
    ladder_started = time.perf_counter()
    ladder = _build_ladder()
    t_ladder = time.perf_counter() - ladder_started
    if comm.rank == 0:
        print(f"[ANS-6] TH-14 _build_ladder(): {t_ladder:.1f} s", flush=True)

    # -- (c) PEC cross-check: TH-15's own, independently-built hole route ----
    t0 = time.perf_counter()
    hole_10mhz = _hole_rung(FREQUENCIES_HZ["10"])
    comm.Barrier()
    t_hole = time.perf_counter() - t0
    pec_ref = ladder["freqs"]["10"]["pec"]
    s_dev = np.abs(hole_10mhz["s"] - pec_ref["s"]) / np.abs(pec_ref["s"])
    z_dev = np.abs(hole_10mhz["z"] - pec_ref["z"]) / np.abs(pec_ref["z"])
    worst_rel = float(max(np.max(s_dev), np.max(z_dev)))
    if comm.rank == 0:
        print(
            f"[ANS-6] (c) PEC cross-check @ 10 MHz: TH-15's _hole_rung ({t_hole:.1f} s) "
            f"vs TH-14's embedded PEC reference, worst relative deviation "
            f"{worst_rel:.3e} (band {PEC_CROSS_CHECK_RTOL:.0e})",
            flush=True,
        )
    assert worst_rel <= PEC_CROSS_CHECK_RTOL, (
        f"TH-15's independently-built PEC hole route deviates {worst_rel:.3e} from "
        f"TH-14's embedded PEC reference at 10 MHz, outside {PEC_CROSS_CHECK_RTOL:.0e} "
        "-- the two gate modules' PEC constructions have diverged (§7 ANS-6 "
        "negative result: report both, commit nothing, park on attempt/*)"
    )

    # -- (a) reciprocity / passivity / C4 gates, both columns, all 3 freqs --
    rungs_payload = {}
    for label, key in LADDER:
        rec = ladder["freqs"][key]
        cu = rec["sigma"][COPPER_SIGMA]
        pec = rec["pec"]
        for name, sw in (("cu", cu), ("pec", pec)):
            assert sw["reciprocity"] <= RECIPROCITY_BAND, (label, name, sw["reciprocity"])
            sigma_max = float(np.max(sw["sigma"]))
            assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (label, name, sigma_max)
            for cname, value in sw["spreads"].items():
                assert value <= ADJACENT_SPREAD_BAND, (label, name, cname, value)
        # -- (b) copper surface-loss identity ---------------------------
        assert rec["identity_residual"] <= DISCRETE_IDENTITY_RTOL, (
            label, rec["identity_residual"]
        )
        p = rec["power"]
        p_in = p["p_src"] - p["p_sheets"]
        # -- (d) not re-derived: read directly off TH-14's own dict ------
        p_coil_over_p_in = p["p_surf"] / p_in
        p_phantom_over_p_in = p["p_phantom"] / p_in
        if comm.rank == 0:
            print(
                f"[ANS-6] {label}: Cu reciprocity {cu['reciprocity']:.3e}, PEC "
                f"reciprocity {pec['reciprocity']:.3e}; Cu sigma_max "
                f"{float(np.max(cu['sigma'])):.9f}, PEC sigma_max "
                f"{float(np.max(pec['sigma'])):.9f}; P_coil/P_in = "
                f"{p_coil_over_p_in:.6e}, P_phantom/P_in = {p_phantom_over_p_in:.6e}",
                flush=True,
            )
            last_sigma = SIGMA_LADDER[-1]
            last_ds = rec["sigma"][last_sigma]["max_abs_ds"]
            print(
                f"[ANS-6] {label}: negative control (PREDICTED, printed): "
                f"sigma={last_sigma:.1e} max|S-S_PEC|={last_ds:.3e} vs predicted "
                f"<= {PREDICTED_PEC_LIMIT_MAX_ABS_DS:.0e}: "
                f"{'met' if last_ds <= PREDICTED_PEC_LIMIT_MAX_ABS_DS else 'NOT met'}",
                flush=True,
            )
            print(
                "[ANS-6] {}: PREDICTED |S(Cu)-S(PEC)| per class: {}".format(
                    label,
                    ", ".join(f"{c} {cu['class_ds'][c]:.9e}" for c in CLASSES),
                ),
                flush=True,
            )

        rungs_payload[label] = {
            "cu": {
                "z_matrix_ohm": _matrix_payload(np.asarray(cu["z"])),
                "s_matrix": _matrix_payload(np.asarray(cu["s"])),
                "reciprocity": float(cu["reciprocity"]),
                "sigma_max": float(np.max(cu["sigma"])),
                "spreads": {k: float(v) for k, v in cu["spreads"].items()},
            },
            "pec": {
                "z_matrix_ohm": _matrix_payload(np.asarray(pec["z"])),
                "s_matrix": _matrix_payload(np.asarray(pec["s"])),
                "reciprocity": float(pec["reciprocity"]),
                "sigma_max": float(np.max(pec["sigma"])),
                "spreads": {k: float(v) for k, v in pec["spreads"].items()},
            },
            "power": {
                "p_src": p["p_src"],
                "p_sheets": p["p_sheets"],
                "p_phantom": p["p_phantom"],
                "p_non_phantom": p["p_non_phantom"],
                "p_surf": p["p_surf"],
                "identity_residual": float(rec["identity_residual"]),
                "p_coil_over_p_in": float(p_coil_over_p_in),
                "p_phantom_over_p_in": float(p_phantom_over_p_in),
            },
            "s_cu_minus_pec": {c: float(cu["class_ds"][c]) for c in CLASSES},
            "sigma_ladder_control": {
                "sigma": float(SIGMA_LADDER[-1]),
                "max_abs_ds": float(rec["sigma"][SIGMA_LADDER[-1]]["max_abs_ds"]),
                "predicted_limit": float(PREDICTED_PEC_LIMIT_MAX_ABS_DS),
            },
        }

    # -- one extra P1 solve at 128 MHz, copper, for the field export --------
    f_export = FREQUENCIES_HZ["128"]
    omega = 2.0 * np.pi * f_export
    r_s = surface_resistance_ohm(omega, COPPER_SIGMA)
    z_s = (1.0 + 1.0j) * r_s
    export_problem = _problem(msh, cell_tags, f_export, outer_tags, (OUTER_BOX_TAG,))
    term = _leontovich_term(msh, facet_tags, z_s, omega)
    t0 = time.perf_counter()
    _p1, fields = run_lumped_sheet_port_case(
        export_problem, port_defs, specs, facet_tags=tags_f, driven_port_id=DRIVEN,
        verbose=False, return_fields=True, extra_bilinear_terms=[term],
    )
    comm.Barrier()
    t_export_solve = time.perf_counter() - t0

    OUTPUT_DIR.mkdir(exist_ok=True)
    written, _ = write_xdmf_with_tags(
        OUTPUT_DIR / BASENAME,
        msh,
        cell_tags,
        _paraview_fields(msh, fields.e_complex, omega),
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    elapsed = time.perf_counter() - started
    if comm.rank != 0:
        return

    metrics = {
        "case": "copper_birdcage_four_port_10_64_128MHz",
        "chunk": "ANS-6",
        "spec": "SPEC.md (authority for geometry/materials/BCs/ports)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gated_path": (
            "_build_ladder (tests/validation/test_th14_birdcage_copper.py, lifted "
            "from its `ladder` fixture, rule (a)); PEC cross-check via "
            "tests/validation/test_th15_birdcage_pec_hole.py:_hole_rung"
        ),
        "gates_of_record": ["TH-14 step 2 (Cu)", "TH-15 step 3 (PEC)"],
        "scope": (
            "self-consistency identities on one fixture (PORT-11 verbatim); no "
            "resonance, tuning or absolute-accuracy claim; no B1+/SAR figure; "
            "no absolute S11/Z_in at 10 or 64 MHz (PORT-21)"
        ),
        "basis": {
            "ours": BASIS_ORDER,
            "unknowns_per_tet": BASIS_UNKNOWNS_PER_TET,
            "aed_correspondence": AED_ORDER_CORRESPONDENCE,
            "ruling": "ANS-5, 2026-08-30",
        },
        "reference_impedance_ohm": float(REFERENCE_IMPEDANCE_OHM),
        "terminated_port_impedance_ohm": float(TERMINATED_PORT_IMPEDANCE_OHM),
        "leg_count": int(LEG_COUNT),
        "n_cells": int(ncells),
        "mpi_ranks": int(comm.size),
        "mesh_seconds": float(t_build),
        "ladder_seconds": float(t_ladder),
        "pec_cross_check_seconds": float(t_hole),
        "export_solve_seconds": float(t_export_solve),
        "total_seconds": float(elapsed),
        "pec_cross_check": {
            "frequency": "10 MHz",
            "worst_rel": worst_rel,
            "band": float(PEC_CROSS_CHECK_RTOL),
        },
        "bands": {
            "reciprocity": float(RECIPROCITY_BAND),
            "passivity_sigma_tolerance": float(PASSIVITY_SIGMA_TOLERANCE),
            "class_spread": float(ADJACENT_SPREAD_BAND),
            "discrete_identity_rtol": float(DISCRETE_IDENTITY_RTOL),
            "predicted_pec_limit_max_abs_ds": float(PREDICTED_PEC_LIMIT_MAX_ABS_DS),
        },
        "rungs": rungs_payload,
        "xdmf": f"paraview_output/{BASENAME}.xdmf",
        "aed": None,
    }
    metrics_path = _write_metrics(metrics)
    comparison_path = _write_comparison(metrics)
    if written is not None:
        print(f"[ANS-6] wrote {written} (+ .h5), P1-driven copper at 128 MHz "
              f"({t_export_solve:.1f} s)", flush=True)
    print(
        f"[ANS-6] wrote {metrics_path.name} and {comparison_path.name} "
        "(AED columns blank by construction)",
        flush=True,
    )
    print(
        f"[ANS-6] all gates green on both columns, all three frequencies, "
        f"{ncells}-cell mesh; PEC cross-check {worst_rel:.3e}; elapsed "
        f"{elapsed:.1f} s on {comm.size} rank(s)",
        flush=True,
    )
    print(
        "[ANS-6] runnable half complete -- the AED replication of SPEC.md is "
        "the operator's (PROJECT_PLAN §5.4 Waiting-on-you); adjudication is a "
        "future weekly review's",
        flush=True,
    )


if __name__ == "__main__":
    main()
