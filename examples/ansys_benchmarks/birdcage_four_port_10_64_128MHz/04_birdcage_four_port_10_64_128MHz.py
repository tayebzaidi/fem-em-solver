"""ANS-4 — loaded four-leg birdcage, four lumped ports, 10 / 64 / 128 MHz: the runnable half.

`ANS-4` (PROJECT_PLAN §7), the third commissioned Ansys Electronics Desktop
benchmark (§5.4) and the first at a **Larmor** frequency.  `SPEC.md` beside this
file is the authority for the boundary-value problem the human operator
replicates in AED; this script produces *our* half of it and writes:

* ``metrics.json`` — the full complex 4×4 ``Z`` and ``S`` at each of the three
  frequencies, the three gate figures per rung, ``|Im P|/Re P`` at the driven
  port, and mesh / timing / basis-order metadata
* ``COMPARISON.md`` — the SPEC's export tables with our columns filled and the
  AED columns (**Zero Order** and **First Order**, the `ANS-5` ruling) blank,
  ready for the operator
* ``paraview_output/ans4_birdcage_four_port_128mhz_combined.xdmf`` — mesh,
  CellTags and the port-1-driven ``E``/``B`` phasor magnitudes at 128 MHz

**Nothing here is transcribed, and nothing is re-implemented.**  The ladder is
built by ``_four_port_rung`` — the `PORT-9`/`PORT-11` gate modules' *own* rung
constructor — and every band, record and helper comes from those modules or from
`EX-34` (``examples/ports/05_birdcage_larmor_frequency_ladder.py``), the gated
example path this case regenerates.  That is `ANS-1`'s rule: if the gated path
moves, this benchmark moves with it and its reproduction assertions fire.

**Anchors** (§7 `ANS-4`).  All three gates on all three rungs at the imported
bands — ``‖S − Sᵀ‖/‖S‖ ≤ 1e-3``, ``σ_max(S) ≤ 1 + 1e-9``, each C4 class of ``Z``
spreading ``≤ 0.5%`` with the pooled/worst separation above its floor — plus the
records: the 10 MHz rung reproduces leg (d)'s recorded 4×4 ``S`` to **1e-6** and
leg (d0)'s terminated ``Z`` column to its own band, and the 64 / 128 MHz rungs
reproduce `PORT-11` steps 2/3 (σ_max 0.999721388 / 0.998974779 and the class
spreads) inside `EX-34`'s pre-stated ``LARMOR_RECORD_BAND`` of 1%.  The mesh is
asserted to be `GEO-19` step B's **116 085** cells at ratio 1.000000 and to be
*reused* by the two Larmor rungs — one meshed object, three frequencies.

**Negative control, printed first.**  The retired `PORT-0` coupling heuristic on
the same problem and the same mesh at 128 MHz: its ``DeprecationWarning`` shown,
``is_placeholder`` asserted True, its identically-zero off-diagonal printed, and
its separation from the field-derived ``S`` asserted above `EX-20`'s 2e-3 floor.

**Out of scope** (SPEC "Out of scope", §7 `ANS-4`).  Runnable half only: no
adjudication, no tuning / resonance / absolute-accuracy claim from our side.
The three gates are **self-consistency identities on one fixture** (`PORT-11`'s
claim verbatim, PROJECT_PLAN §2.2) — a port model wrong by a constant factor
passes all of them, which is precisely why AED's opinion is being asked for.
There is no B1+ and no SAR figure here; ``|Im P|/Re P`` is exported and never
gated.

Run it through the example runner (the ``ans:`` group sources the complex build
automatically)::

    ./run_examples.sh -e ans:4 -n 2 -t 500
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import default_scalar_type

# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gate modules' constants and rung constructor are importable rather than
# restated (the `ANS-1` rule, as `ANS-3` does for `EX-20`).
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)

from tests.mesh.test_birdcage_port_tags import LEG_COUNT  # noqa: E402
from tests.validation.test_lossy_sphere_fullwave import (  # noqa: E402
    FREQUENCY_64_HZ,
    FREQUENCY_128_HZ,
)
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    LEG_D0_REPRODUCTION_BAND,
    LEG_D0_Z_COLUMN,
    PASSIVITY_SIGMA_TOLERANCE,
    POOLED_SEPARATION_FLOOR,
    TERMINATED_PORT_IMPEDANCE_OHM,
)
from tests.validation.test_port_birdcage_larmor_gate import (  # noqa: E402
    FREQUENCY_CONTROL_BAND,
    LEG_D_S_MATRIX_10MHZ,
    _terminal_power,
)
from tests.validation.test_port_birdcage_larmor_gate_128 import (  # noqa: E402
    PHANTOM_CELLS_PER_LAMBDA_FLOOR,
    STEP2_64MHZ,
    _require_resolution,
    _resolution,
)
from tests.validation.test_port_birdcage_leg_offset_sweep import (  # noqa: E402
    _four_port_rung,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    ADJACENT_SPREAD_BAND,
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
    STEP2_CELL_COUNT,
)
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ  # noqa: E402
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND  # noqa: E402
from tests.validation.test_port_package_sparameters import (  # noqa: E402
    REFERENCE_IMPEDANCE_OHM,
)


def _load_example(path: Path, module_name: str):
    """Import an ``examples/`` script by path — its basename starts with a digit.

    ``importlib`` by file location rather than ``__import__`` on a synthesised
    name: the `ans:` scripts and the `ports:` scripts both carry group-and-number
    prefixes, and a name-based import silently depends on which prefix scheme was
    current when it was written.
    """
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# `EX-34` is the gated example path this case regenerates: the one-mesh
# 10/64/128 MHz ladder through the gate modules' own rung constructor. Its
# records, its 1% reproduction band, its heuristic floor, its gate assertions and
# its ParaView field builder are imported, never restated.
_EX34 = _load_example(
    _REPO_ROOT / "examples" / "ports" / "05_birdcage_larmor_frequency_ladder.py",
    "ex34_birdcage_larmor_frequency_ladder",
)

STEP3_128MHZ = _EX34.STEP3_128MHZ
LARMOR_RECORD_BAND = _EX34.LARMOR_RECORD_BAND
LARMOR_RECORDS = _EX34.LARMOR_RECORDS
HEURISTIC_SEPARATION_FLOOR = _EX34.HEURISTIC_SEPARATION_FLOOR

_assert_three_gates = _EX34._assert_three_gates
_assert_larmor_record = _EX34._assert_larmor_record
_heuristic_control = _EX34._heuristic_control
_paraview_fields = _EX34._paraview_fields
_solve_driven_p1 = _EX34._solve_driven_p1

CASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = CASE_DIR / "paraview_output"
BASENAME = "ans4_birdcage_four_port_128mhz_combined"

#: Our production discretization, and the AED correspondence the `ANS-5` ruling
#: (2026-08-30) put in the SPEC: degree-1 Nédélec = 6 unknowns per tetrahedron =
#: HFSS **Zero Order**, which is *not* AED's default. Both AED columns are asked
#: for; only the Zero Order one adjudicates.
BASIS_ORDER = "Nedelec first kind, degree 1 (N1curl)"
BASIS_UNKNOWNS_PER_TET = 6
AED_ORDER_CORRESPONDENCE = "HFSS Zero Order (20 unknowns/tet = First Order, the AED default, is the order-sensitivity column)"

LADDER = (("10 MHz", FREQUENCY_HZ), ("64 MHz", FREQUENCY_64_HZ), ("128 MHz", FREQUENCY_128_HZ))


def _complex_entry(z: complex) -> dict:
    return {"re": float(np.real(z)), "im": float(np.imag(z))}


def _matrix_payload(m) -> list:
    return [[_complex_entry(m[i, j]) for j in range(m.shape[1])] for i in range(m.shape[0])]


def _fmt(z: complex) -> str:
    return f"{np.real(z):+.7e} {np.imag(z):+.7e}j"


def _class_entries(m):
    """The three C4 classes of a circulant 4×4: self, adjacent (90°), opposite."""
    return {"self": m[0, 0], "adjacent": m[1, 0], "opposite": m[2, 0]}


def _write_metrics(payload) -> Path:
    path = CASE_DIR / "metrics.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def _write_comparison(m) -> Path:
    """``COMPARISON.md``: our columns filled, the two AED columns blank per SPEC."""
    path = CASE_DIR / "COMPARISON.md"

    def s_table(label):
        s = np.asarray(
            [[complex(e["re"], e["im"]) for e in row] for row in m["rungs"][label]["s_matrix"]]
        )
        return "\n".join(
            "| "
            + f"S{i + 1}{j + 1}"
            + f" | {_fmt(s[i, j])} | | | |"
            for i in range(LEG_COUNT)
            for j in range(LEG_COUNT)
        )

    def z_diag(label):
        z = np.asarray(
            [[complex(e["re"], e["im"]) for e in row] for row in m["rungs"][label]["z_matrix_ohm"]]
        )
        return _fmt(z[0, 0])

    def class_table(label):
        s = np.asarray(
            [[complex(e["re"], e["im"]) for e in row] for row in m["rungs"][label]["s_matrix"]]
        )
        cls = _class_entries(s)
        return "\n".join(
            f"| {label} | {name} (S{'11' if name == 'self' else '21' if name == 'adjacent' else '31'}) "
            f"| {_fmt(value)} | | | |"
            for name, value in cls.items()
        )

    gates = "\n".join(
        f"| {label} | {m['rungs'][label]['reciprocity']:.9e} | "
        f"{m['rungs'][label]['sigma_max']:.9f} | "
        f"{m['rungs'][label]['spreads']['self'] * 100:.4f} / "
        f"{m['rungs'][label]['spreads']['adjacent'] * 100:.4f} / "
        f"{m['rungs'][label]['spreads']['opposite'] * 100:.4f}% | | |"
        for label, _ in LADDER
    )
    power = "\n".join(
        f"| {label} | {m['rungs'][label]['terminal_power_va']['re']:+.9e} | "
        f"{m['rungs'][label]['terminal_power_va']['im']:+.9e} | "
        f"{m['rungs'][label]['im_over_re_power']:.6f} | | |"
        for label, _ in LADDER
    )
    reproduction = "\n".join(
        f"| {label} | {name} | {ref:.9f} | {value:.9f} | {miss:.2e} |"
        for label in ("64 MHz", "128 MHz")
        for name, (value, ref, miss) in m["rungs"][label]["reproduction"].items()
    )
    classes = "\n".join(class_table(label) for label, _ in LADDER)

    path.write_text(
        f"""# ANS-4 — comparison table (our half filled, both AED halves blank)

Generated by `04_birdcage_four_port_10_64_128MHz.py` on {m["generated_utc"]};
every number in the "Ours (FEM)" column is produced by that run through the
`PORT-9`/`PORT-11` gate modules' own `_four_port_rung` — the `EX-34` path —
on one {m["n_cells"]}-cell mesh. Nothing is transcribed. Re-run
`./run_examples.sh -e ans:4 -n 2 -t 500` to regenerate.

`SPEC.md` is the authority for the problem to be replicated. Fill the AED
columns from the HFSS driven solves of that spec, reporting **all** digits AED
prints.

**Two AED columns, per the `ANS-5` ruling (2026-08-30).** Our side is
`{BASIS_ORDER}`, {BASIS_UNKNOWNS_PER_TET} unknowns per tetrahedron =
**{AED_ORDER_CORRESPONDENCE}**. Column **AED (Zero Order)** is the matched
discretization and is the *adjudication* column; column **AED (First Order)** is
the AED default and is an order-sensitivity reading only. Mixed Order is
forbidden — we have no per-element order and could not reproduce it.

**Scope, before any of these numbers is quoted.** The three gates below are
**self-consistency identities on one fixture** (`PORT-11`, PROJECT_PLAN §2.2) —
a port model wrong by a constant factor passes every one of them. This case
exists because nothing in this repository has yet compared a Larmor-frequency
figure against anything outside the code. No resonance, tuning or
absolute-accuracy claim is made from our side; adjudication is the next weekly
review's, after the AED numbers land.

## S-matrix, C4 classes — the primary adjudication rows

Nine complex numbers: the three classes of the circulant 4×4 at each frequency.

| Frequency | Class | Ours (FEM) | AED (Zero Order) | AED (First Order) | AED vs ours |
|---|---|---|---|---|---|
{classes}

## Full S-matrix at Z₀ = {REFERENCE_IMPEDANCE_OHM:.0f} Ω

### 10 MHz

| Entry | Ours (FEM) | AED (Zero Order) | AED (First Order) | AED vs ours |
|---|---|---|---|---|
{s_table("10 MHz")}

### 64 MHz

| Entry | Ours (FEM) | AED (Zero Order) | AED (First Order) | AED vs ours |
|---|---|---|---|---|
{s_table("64 MHz")}

### 128 MHz

| Entry | Ours (FEM) | AED (Zero Order) | AED (First Order) | AED vs ours |
|---|---|---|---|---|
{s_table("128 MHz")}

The full complex 4×4 `Z` at every frequency is in `metrics.json`
(`rungs.<label>.z_matrix_ohm`); only the diagonal is reproduced here.

## Z₁₁ — a secondary row, never gated

| Frequency | Ours (FEM) [Ω] | AED (Zero Order) | AED (First Order) | AED vs ours |
|---|---|---|---|---|
| 10 MHz | {z_diag("10 MHz")} | | | |
| 64 MHz | {z_diag("64 MHz")} | | | |
| 128 MHz | {z_diag("128 MHz")} | | | |

Our diagonal carries the sheet-width convention `w = A/h` (`PORT-9` step 2b): the
lumped sheet is the interior half (`f = 0.5`) of the port box's mid-plane. An AED
disagreement here is expected to be informative about *our* feed model rather
than alarming — the `PORT-1` standing caution, carried forward.

## Identities (computable by AED from its exported S)

| Frequency | ‖S − Sᵀ‖/‖S‖ (gate {RECIPROCITY_BAND:.0e}) | σ_max(S) (gate ≤ 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e}) | C4 class spreads self / adjacent / opposite (gate {ADJACENT_SPREAD_BAND * 100:.1f}%) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|---|---|
{gates}

Reciprocity residuals of a power-wave S sit at ~1e-16…1e-11 and reproduce in
**order of magnitude only** (the `PORT-11` (d3c) rule) — compare the decade, not
the digits.

## Accepted power at the driven port

| Frequency | Re P [VA] | Im P [VA] | \\|Im P\\|/Re P | AED (Zero Order) | AED (First Order) |
|---|---|---|---|---|---|
{power}

`|Im P|/Re P` is **printed and never gated** — it is stored energy at the feed,
not a resonance reading. Its rise up the ladder is one of the two unratified
readings the SPEC asks AED's opinion on.

## Reproduction of the gated records

The 10 MHz rung reproduces leg (d)'s recorded 4×4 `S` to
{FREQUENCY_CONTROL_BAND:.0e} (worst entry {m["anchor_10mhz"]["s_worst"]:.3e}) and
leg (d0)'s terminated `Z` column to {LEG_D0_REPRODUCTION_BAND:.0e} (worst
{m["anchor_10mhz"]["z_worst"]:.3e}). The Larmor rungs reproduce `PORT-11` steps
2/3 inside `EX-34`'s pre-stated {LARMOR_RECORD_BAND:.0e} band:

| Frequency | Quantity | `PORT-11` record | This run | Relative miss |
|---|---|---|---|---|
{reproduction}

## Negative control (in-fixture, ours) — printed first

The retired `PORT-0` coupling heuristic, run on the **same problem and the same
mesh** at 128 MHz: `is_placeholder = True`, a `DeprecationWarning` emitted, an
**identically zero** off-diagonal (max |off-diag| =
{m["control"]["off_diagonal_max"]:.6e} — it predicts no coupling at all), and a
separation from the field-derived S of
max|S_heuristic − S_field| = {m["control"]["separation"]:.6f} against the `EX-20`
floor {HEURISTIC_SEPARATION_FLOOR:.0e}. A heuristic that happened to agree would
be a finding about the heuristic, not a passing benchmark.

## Solve metadata

| Item | Ours (FEM) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|
| Elements | {m["n_cells"]} tetrahedra (`GEO-19` step B record {STEP2_CELL_COUNT}, ratio {m["cell_ratio"]:.6f}) | | |
| Basis order | {BASIS_ORDER}, {BASIS_UNKNOWNS_PER_TET} unknowns/tet | | |
| Adaptive passes | n/a — fixed graded mesh, **built once and reused by all three frequencies** | | |
| Final ΔS | n/a — single non-adaptive driven solve per port per frequency | | |
| Solve time | {m["mesh_seconds"]:.1f} s mesh + {" + ".join(f"{m['rungs'][l]['sweep_seconds']:.1f} s" for l, _ in LADDER)} for the three 4-column sweeps at `mpiexec -n {m["mpi_ranks"]}` (+ {m["export_solve_seconds"]:.1f} s export solve, {m["control_seconds"]:.1f} s control) | | |
| Port model | {LEG_COUNT} lumped-element sheets, Z_p = {TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ω on every undriven port, renormalized to Z₀ = {REFERENCE_IMPEDANCE_OHM:.1f} Ω | | |

### Resolution on the one mesh

| Frequency | phantom tan δ | δ [m] | λ [m] | cells/δ | cells/λ |
|---|---|---|---|---|---|
{chr(10).join(
    f"| {label} | {m['rungs'][label]['resolution']['loss_tangent']:.4f} | "
    f"{m['rungs'][label]['resolution']['delta_m']:.6e} | "
    f"{m['rungs'][label]['resolution']['lambda_m']:.6e} | "
    f"{m['rungs'][label]['resolution']['cells_per_delta_phantom']:.4f} | "
    f"{m['rungs'][label]['resolution']['cells_per_lambda_phantom']:.4f} |"
    for label, _ in LADDER
)}

The pre-gate stop rule (imported, enforced **before** any 128 MHz gate is read):
phantom cells/λ at 128 MHz = {m["rungs"]["128 MHz"]["resolution"]["cells_per_lambda_phantom"]:.4f}
against the floor {PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f}.

## Field export

`paraview_output/{BASENAME}.xdmf` (regenerated by each run; not tracked, like
every other `paraview_output/` in the repo). The port-1-driven case at **128 MHz**,
carrying `E_real` / `E_imag` / `E_magnitude` (CG1) and `B_magnitude` (DG0,
`B = ∇×E/(−jω)` from Faraday's law through `fem_em_solver.post`), beside
`CellTags` ({CONDUCTOR_CELL_TAG} = conductor, {PHANTOM_CELL_TAG} = phantom).

**A named limitation** (`EX-20`'s, carried by every case in this directory): the
sweep returns port quantities, not fields — so the export costs **one extra
solve** of port 1's drive, run exactly as the sweep runs it. The script says so
rather than pretending the sweep produced the file.

For the AED half, export |E| and |B1+| on the coil mid-plane so the spatial
distributions can be compared, not just the terminal numbers.

## Provenance

* Gated path: `examples/ports/05_birdcage_larmor_frequency_ladder.py` (`EX-34`)
  and the gate modules' own `_four_port_rung`
  (`tests/validation/test_port_birdcage_leg_offset_sweep.py`) — every band,
  record and construction above is imported from them, never restated.
* Gates of record: `PORT-9` ✅ 2026-08-25 (10 MHz), `PORT-11` ✅ 2026-08-26
  (64 and 128 MHz), PROJECT_PLAN §7.
* Fixture: `GEO-18` gapped + sheeted four-leg birdcage, phantom loaded,
  `GEO-19` step B mesh.
* Element-order correspondence: `ANS-5` ruling, 2026-08-30.
"""
    )
    return path


def _write_paraview(rung, comm):
    """Cells + tags + the 128 MHz driven field, into this case's own directory."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    e_driven, omega, driven_id, t_solve = _solve_driven_p1(rung, comm)
    written, _ = write_xdmf_with_tags(
        OUTPUT_DIR / BASENAME,
        rung["mesh"],
        rung["cell_tags"],
        _paraview_fields(rung["mesh"], e_driven, omega),
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return written, driven_id, t_solve


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
            "ANS-4 - loaded 4-leg birdcage, four lumped ports, 10 / 64 / 128 MHz "
            "(runnable half)",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            f"[ANS-4] fixture `GEO-18` gapped + sheeted birdcage, phantom loaded "
            f"(conductor tag {CONDUCTOR_CELL_TAG}, phantom tag {PHANTOM_CELL_TAG}); "
            f"{LEG_COUNT} lumped sheets at Z_p = "
            f"{TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ohm, z0 = "
            f"{REFERENCE_IMPEDANCE_OHM:.1f} Ohm\n"
            f"[ANS-4] basis: {BASIS_ORDER}, {BASIS_UNKNOWNS_PER_TET} unknowns/tet "
            f"= {AED_ORDER_CORRESPONDENCE}\n"
            f"[ANS-4] scope: self-consistency identities on one fixture "
            "(`PORT-11` verbatim) - NOT a resonance, tuning or absolute-accuracy "
            "claim, and no B1+/SAR figure",
            flush=True,
        )

    # -- the ladder: one mesh, three rungs, twelve driven solves --------------
    zeros = np.zeros(LEG_COUNT)
    rungs = {}
    for label, frequency in LADDER:
        rungs[label] = _four_port_rung(
            f"ANS-4 {label}", zeros, frequency, reuse=rungs.get("10 MHz")
        )

    cell_ratio = rungs["10 MHz"]["cells"] / STEP2_CELL_COUNT
    if comm.rank == 0:
        print(
            f"[ANS-4] mesh: {rungs['10 MHz']['cells']} cells (`GEO-19` step B "
            f"record {STEP2_CELL_COUNT}, ratio {cell_ratio:.6f}) built once in "
            f"{rungs['10 MHz']['mesh_time']:.1f} s; sweeps "
            + " + ".join(f"{rungs[l]['sweep_time']:.1f} s" for l, _ in LADDER)
            + f" at -n {comm.size}",
            flush=True,
        )
    assert abs(cell_ratio - 1.0) < 1e-9, (
        f"the ladder meshed {rungs['10 MHz']['cells']} cells against `GEO-19` "
        f"step B's record {STEP2_CELL_COUNT} (ratio {cell_ratio:.6f}) — this is "
        "not the fixture the SPEC describes, so no column below is comparable"
    )
    for label, _ in LADDER[1:]:
        assert rungs[label]["reused_mesh"], (
            f"the {label} rung rebuilt its mesh — the SPEC promises AED one "
            "geometry solved at three frequencies, not three meshes"
        )
        assert rungs[label]["mesh"] is rungs["10 MHz"]["mesh"]
        assert rungs[label]["cells"] == rungs["10 MHz"]["cells"]

    # -- the negative control, FIRST (the `EX-34`/`ANS-3` pattern) ------------
    heuristic, deprecations, t_control = _heuristic_control(rungs["128 MHz"], comm)
    separation = float(np.max(np.abs(heuristic.s_matrix - rungs["128 MHz"]["s"])))
    off_diagonal_max = float(
        np.max(np.abs(heuristic.s_matrix[~np.eye(LEG_COUNT, dtype=bool)]))
    )
    if comm.rank == 0:
        print(
            f"[ANS-4] NEGATIVE CONTROL FIRST — the retired PORT-0 coupling "
            f"heuristic on the same problem and the same mesh at 128 MHz "
            f"({t_control:.1f} s, {len(deprecations)} DeprecationWarning(s)): "
            f"is_placeholder = {heuristic.is_placeholder}, max|off-diagonal| = "
            f"{off_diagonal_max:.6e} (identically zero — it predicts no coupling "
            f"at all), max|S_heuristic - S_field| = {separation:.6f} against the "
            f"EX-20 floor {HEURISTIC_SEPARATION_FLOOR:.0e}",
            flush=True,
        )
    assert heuristic.is_placeholder, "the heuristic route must keep marking itself"
    assert deprecations, (
        "the heuristic route must emit a DeprecationWarning now that the "
        "solved-field route exists"
    )
    assert separation > HEURISTIC_SEPARATION_FLOOR, (
        f"at 128 MHz the retired heuristic reproduces the field-derived S to "
        f"{separation:.3e} — that is a finding about the heuristic, not a "
        "passing benchmark"
    )

    # -- the pre-gate stop rule, before any 128 MHz gate is read --------------
    resolution = _resolution(rungs["10 MHz"])
    row_128 = resolution["table"]["128 MHz"]
    if comm.rank == 0:
        print(
            f"[ANS-4] stop rule: 128 MHz phantom cells/lambda = "
            f"{row_128['cells_per_lambda_phantom']:.4f} against the imported "
            f"floor {PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f} "
            f"{'CLEAR' if row_128['cells_per_lambda_phantom'] >= PHANTOM_CELLS_PER_LAMBDA_FLOOR else 'FAIL'}",
            flush=True,
        )
    _require_resolution(resolution)
    assert row_128["cells_per_lambda_phantom"] >= PHANTOM_CELLS_PER_LAMBDA_FLOOR

    # -- the three gates on every rung ---------------------------------------
    gate_readings = {}
    for label, _ in LADDER:
        gate_readings[label] = _assert_three_gates(label, rungs[label], comm)

    # -- the 10 MHz anchors: leg (d)'s 4x4 and leg (d0)'s column -------------
    control = rungs["10 MHz"]
    s_dev = float(
        np.max(np.abs(control["s"] - LEG_D_S_MATRIX_10MHZ) / np.abs(LEG_D_S_MATRIX_10MHZ))
    )
    z_dev = float(
        np.max(np.abs(control["z"][:, 0] - LEG_D0_Z_COLUMN) / np.abs(LEG_D0_Z_COLUMN))
    )
    if comm.rank == 0:
        print(
            f"\n[ANS-4] anchor @ 10 MHz: leg (d)'s recorded 4x4 worst entry "
            f"{s_dev:.3e} vs {FREQUENCY_CONTROL_BAND:.0e}; leg (d0)'s column "
            f"worst {z_dev:.3e} vs {LEG_D0_REPRODUCTION_BAND:.0e}",
            flush=True,
        )
    assert s_dev < FREQUENCY_CONTROL_BAND, (
        f"the 10 MHz rung deviates {s_dev:.3e} from leg (d)'s recorded 4x4, "
        f"outside the imported {FREQUENCY_CONTROL_BAND:.0e} band — the harness "
        "moved, not the frequency, and nothing this benchmark exports is "
        "comparable (§7 `ANS-4` negative result)"
    )
    assert z_dev < LEG_D0_REPRODUCTION_BAND, (
        f"the 10 MHz rung's driven column deviates {z_dev:.3e} from leg (d0)'s "
        f"record, outside the imported {LEG_D0_REPRODUCTION_BAND:.0e} band"
    )

    # -- the Larmor anchors: `PORT-11` steps 2/3 at 1% ------------------------
    for label, record in LARMOR_RECORDS.items():
        _assert_larmor_record(label, rungs[label], record, comm)

    # -- ParaView: one extra solve at 128 MHz, into this case's directory -----
    written, driven_id, t_export = _write_paraview(rungs["128 MHz"], comm)

    elapsed = time.perf_counter() - started

    if comm.rank != 0:
        return

    rung_payload = {}
    for label, frequency in LADDER:
        rung = rungs[label]
        power = _terminal_power(rung)
        row = resolution["table"][label]
        record = LARMOR_RECORDS.get(label)
        reproduction = {}
        if record is not None:
            readings = {
                "sigma_max": (float(np.max(rung["sigma"])), record["sigma_max"]),
                "column_power_max": (
                    float(np.max(rung["column_power"])),
                    record["column_power_max"],
                ),
                **{
                    f"spread_{name}": (rung["spreads"][name], record["spreads"][name])
                    for name in ("self", "adjacent", "opposite")
                },
            }
            reproduction = {
                name: (value, ref, abs(value - ref) / abs(ref))
                for name, (value, ref) in readings.items()
            }
        rung_payload[label] = {
            "frequency_hz": float(frequency),
            "z_matrix_ohm": _matrix_payload(np.asarray(rung["z"])),
            "s_matrix": _matrix_payload(np.asarray(rung["s"])),
            "reciprocity": gate_readings[label]["reciprocity"],
            "z_reciprocity": float(rung["z_reciprocity"]),
            "sigma_max": gate_readings[label]["sigma_max"],
            "column_power_max": gate_readings[label]["power_max"],
            "column_power": [float(v) for v in rung["column_power"]],
            "spreads": {k: float(v) for k, v in rung["spreads"].items()},
            "pooled_off_diagonal": float(rung["pooled"]),
            "terminal_power_va": _complex_entry(power),
            "im_over_re_power": float(abs(power.imag) / abs(power.real)),
            "sweep_seconds": float(rung["sweep_time"]),
            "resolution": {
                "loss_tangent": float(row["phantom"]["loss_tangent"]),
                "delta_m": float(row["phantom"]["delta"]),
                "lambda_m": float(row["phantom"]["lambda"]),
                "cells_per_delta_phantom": float(row["cells_per_delta_phantom"]),
                "cells_per_lambda_phantom": float(row["cells_per_lambda_phantom"]),
                "cells_per_lambda_air": float(row["cells_per_lambda_air"]),
            },
            "reproduction": reproduction,
        }

    metrics = {
        "case": "birdcage_four_port_10_64_128MHz",
        "chunk": "ANS-4",
        "spec": "SPEC.md (authority for geometry/materials/BCs/ports)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regime": "10 MHz eddy-current plus the two Larmor frequencies (§2.1)",
        "gated_path": (
            "_four_port_rung (tests/validation/test_port_birdcage_leg_offset_sweep.py) "
            "via examples/ports/05_birdcage_larmor_frequency_ladder.py (EX-34)"
        ),
        "gates_of_record": ["PORT-9 (10 MHz)", "PORT-11 steps 2/3 (64 and 128 MHz)"],
        "scope": (
            "self-consistency identities on one fixture (PORT-11 verbatim); no "
            "resonance, tuning or absolute-accuracy claim; no B1+/SAR figure"
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
        "n_cells": int(rungs["10 MHz"]["cells"]),
        "cell_ratio": float(cell_ratio),
        "reused_mesh": True,
        "mpi_ranks": int(comm.size),
        "mesh_seconds": float(rungs["10 MHz"]["mesh_time"]),
        "export_solve_seconds": float(t_export),
        "control_seconds": float(t_control),
        "total_seconds": float(elapsed),
        "bands": {
            "reciprocity": float(RECIPROCITY_BAND),
            "passivity_sigma_tolerance": float(PASSIVITY_SIGMA_TOLERANCE),
            "class_spread": float(ADJACENT_SPREAD_BAND),
            "pooled_separation_floor": float(POOLED_SEPARATION_FLOOR),
            "larmor_record": float(LARMOR_RECORD_BAND),
            "frequency_control": float(FREQUENCY_CONTROL_BAND),
            "leg_d0_reproduction": float(LEG_D0_REPRODUCTION_BAND),
            "phantom_cells_per_lambda_floor": float(PHANTOM_CELLS_PER_LAMBDA_FLOOR),
            "heuristic_separation_floor": float(HEURISTIC_SEPARATION_FLOOR),
        },
        "anchor_10mhz": {"s_worst": s_dev, "z_worst": z_dev},
        "control": {
            "route": "retired PORT-0 coupling heuristic, same problem and mesh, 128 MHz",
            "is_placeholder": bool(heuristic.is_placeholder),
            "deprecation_warnings": len(deprecations),
            "off_diagonal_max": off_diagonal_max,
            "separation": separation,
        },
        "rungs": rung_payload,
        "xdmf": f"paraview_output/{BASENAME}.xdmf",
        "aed": None,
    }
    metrics_path = _write_metrics(metrics)
    comparison_path = _write_comparison(metrics)
    if written is not None:
        print(f"[ANS-4] wrote {written} (+ .h5), {driven_id}-driven at 128 MHz "
              f"({t_export:.1f} s)", flush=True)
    print(f"[ANS-4] wrote {metrics_path.name} and {comparison_path.name}", flush=True)
    print(
        f"[ANS-4] all three gates green on all three rungs of one "
        f"{metrics['n_cells']}-cell mesh; elapsed {elapsed:.1f} s on "
        f"{comm.size} rank(s)",
        flush=True,
    )
    print(
        "[ANS-4] runnable half complete — the AED replication of SPEC.md at BOTH "
        "orders is the operator's (PROJECT_PLAN §5.4 Waiting-on-you); "
        "adjudication is the next weekly review's",
        flush=True,
    )


if __name__ == "__main__":
    main()
