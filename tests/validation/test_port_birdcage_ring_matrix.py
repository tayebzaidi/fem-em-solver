"""`PORT-13` step 3 — the full 32x32 ``S`` on the 16-leg / 32-ring-port rung.

**What this is.**  Step 2 read four columns of ``S`` off the longitudinal-sheet
birdcage rung.  This module reads **all thirty-two**, and then asserts on the
assembled matrix the three network-level identities four columns could not
support: reciprocity, passivity in its matrix form (``sigma_max(S) <= 1``), and
the ``C16 x mirror`` class identity over 18 symmetry classes built from the
**measured** azimuths and ring membership.

**Why three windows.**  Thirty-two solves do not fit one command inside the
project's 20-minute ceiling at step 1's measured price (27.96 s/solve,
`20260904T050538Z_PORT-13.log:10715`), and a window is sized for the price that
has already happened, not for the faster one step 2 happened to catch
(9.1-11.7 s, `20260904T093638Z_PORT-13.log:10758`).  So the sweep is split:

* **window A** — ``FEM_EM_RING_SWEEP_HALF=bottom``, ``-n 8``: build the rung,
  drive the sixteen **bottom-ring** ports in turn, cache the sixteen columns;
* **window B** — the same with ``top``, the sixteen top-ring ports;
* **window C** — ``-n 2``, **no solve**: load both caches, assemble ``S`` and
  assert.

The half is chosen by an **environment variable only**, never by a ``-k``
expression: a ``-k`` filter silently selects nothing when a name is mistyped,
and the cost of that mistake here is a 600 s window that proves nothing.  The
two ring halves are located from the **measured** sign of each sheet centre's
``z``, not from an ordinal, exactly as step 2 locates its mirror map.

The caches live under the gitignored ``output/port13_ring_columns/`` and never
enter a commit; window C **skips with a message** when either file is absent, so
the module stays collectable on a clean tree.

**Anchors (asserted in window C, every band imported and unmoved).**

(i)   **reciprocity** of the 32x32, ``‖S − Sᵀ‖_F/‖S‖_F <= RECIPROCITY_BAND``
      (1e-3).  Sharper here than in step 2: the two halves come off two
      *separately built* meshes in two separate processes, so this reads mesh
      reproducibility as well as column extraction.
(ii)  **passivity on the matrix**, ``sigma_max(S) <= 1`` — `PORT-9`'s own gate,
      and strictly stronger than step 2's per-column ``Σ|S|² <= 1`` (which the
      cached columns still satisfy at ≈ 0.916, so the margin here is small and
      is printed).
(iii) the **C16 x mirror class identity**: ``|S_ij|`` grouped by (same ring /
      other ring) x (azimuth separation 0…8 steps of 22.5 deg) — **18 classes**
      — each class's spread within the unmoved ``OPPOSITE_SPREAD_BAND`` (5%;
      step 2 measured the mirror class at 0.0308%).  The classes are built from
      the measured azimuths, so a port that matches no class to
      ``AZIMUTH_MATCH_DEG`` is an assertion failure, never a silent drop.
(iv)  the **tie to the audited step**: the four step-2 columns' ``Σ_i |S_ij|²``
      reproduced at rtol 1e-6 (same ``-n 8``, the `OPS-34` ~1e-9 scatter
      precedent).
(v)   both halves' **cell counts** equal to each other and to
      ``RING_LONGITUDINAL_SCALED_CELL_RECORD``; both azimuth tables equal to
      1e-9 deg.
(vi)  all **32 power-accounting residuals** inside the imported, unmoved
      ``POWER_BALANCE_BAND``.

**Negative control** (window C, no extra solve): one cached column scaled by
``CONTROL_COLUMN_SCALE`` (1.01) — the `PORT-9` leg (d2) per-column
normalisation defect class — must move the reciprocity ratio to at least
``MATRIX_CONTROL_MARGIN`` x the band.  Step 2's 5x bar is **not** reachable on
32 columns and is deliberately not imported; see the constant below.

**Scope.**  The 32x32 and its identities on one fixture at 10 MHz, degree 1.  No
``sigma_max`` *record*, no tuning, no resonance, no mode spectrum, no
absolute-accuracy claim.  No band is widened, renamed or moved here: a miss is a
known-issues entry with ``|S|`` printed.

Run (complex build required, three foreground windows)::

    scripts/testing/run_and_log.sh PORT-13 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       FEM_EM_RING_SWEEP_HALF=bottom timeout -k 30 600 mpiexec -n 8 python3 -m \\
       pytest tests/environment tests/validation/test_port_birdcage_ring_matrix.py \\
       -v -s'"

then the same with ``top``, then window C with neither
``FEM_EM_RING_SWEEP_HALF`` set, at ``-n 2``.
"""

from __future__ import annotations

import os
import resource
import time
from pathlib import Path

import numpy as np
import pytest
from mpi4py import MPI

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheet_prerequisite import CELL_COUNT_BAND
from tests.mesh.test_birdcage_port_scaleup import SCALED_LEG_COUNT
from tests.mesh.test_birdcage_ring_sheet_orientation import (
    RING_LONGITUDINAL_SCALED_CELL_RECORD,
)
from tests.validation.test_birdcage_b1_plus_map import POWER_BALANCE_BAND
from tests.validation.test_port_birdcage_ring_column import (
    AZIMUTH_MATCH_DEG,
    CONTROL_COLUMN_SCALE,
    OPPOSITE_SPREAD_BAND,
    _build_ring_context,
    _reciprocity_ratio,
    _solve_one_drive,
)
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND

# The sweep half, and nothing else, selects which sixteen ports a solve window
# drives.  Unset means "assembly window": no solve runs.
SWEEP_ENV = "FEM_EM_RING_SWEEP_HALF"
SWEEP_HALVES = ("bottom", "top")

# Gitignored (`.gitignore:62`); the caches never enter a commit and window C
# skips with a message when they are absent.
CACHE_DIR = Path("output/port13_ring_columns")

# Anchor (ii).  Not a tolerance: a passive network's scattering matrix is a
# contraction, so the ceiling is exactly 1 and `1 − sigma_max` is a measurement
# that is printed, never a band that could be widened.  The cached column norms
# are ≈ 0.916, so `sigma_max` cannot be far below 1 and the margin is expected
# to be small.
MATRIX_PASSIVITY_CEILING = 1.0

# Anchor (iv): step 2's four measured column norms `Σ_i |S_ij|²`, at the digits
# the audited run printed (`20260904T093638Z_PORT-13.log:10797–10800`), keyed by
# the ring-port ordinal step 2 drove.  These are a **reproduction record** of a
# closed step, not a physical band: they tie this sweep to the four columns a
# review already read, and the tolerance is the run-to-run scatter `OPS-34`
# measured at ~1e-9 relative, asserted here two decades looser.
STEP2_COLUMN_POWER_SUMS = {
    17: 0.915817419,
    25: 0.915956086,
    33: 0.915816510,
    41: 0.915944997,
}
STEP2_COLUMN_POWER_RTOL = 1.0e-6

# The negative control's bar, **deliberately not** step 2's imported
# `CONTROL_MARGIN_FACTOR` (5.0): that number was 4-column arithmetic and is
# unreachable on 32.  Ceiling first, from the cached columns:
# `‖S‖_F ≈ √(32 × 0.916) = 5.41`, and a 1% scale on one column of norm
# √0.916 = 0.957 moves `‖S − Sᵀ‖_F` by ≈ 0.01 × 0.957 × √2 = 1.35e-2, so the
# ratio moves to ≈ 1.35e-2/5.41 = 2.5e-3 = 2.5x the 1e-3 band.  2x is assertable
# against that ceiling; 5x is not.
MATRIX_CONTROL_MARGIN = 2.0

# The C16 x mirror class table: azimuth separations 0…8 steps of 22.5 deg (the
# 16-fold layout's own step, and 8 steps is the diametrically-opposite one), on
# each of the two ring relations.
AZIMUTH_STEP_DEG = 360.0 / SCALED_LEG_COUNT
N_AZIMUTH_CLASSES = SCALED_LEG_COUNT // 2 + 1
N_SYMMETRY_CLASSES = 2 * N_AZIMUTH_CLASSES


def _half_file(half):
    return CACHE_DIR / f"{half}.npz"


def _half_ordinals(sheets, half):
    """The sixteen ring-port ordinals of one ring, from the **measured** ``z``.

    The bottom ring is the one whose sheet centres sit at ``z < 0``; nothing
    here reads an ordinal.  A generator that renumbered or re-stacked its ring
    ports fails the count assert in the caller rather than quietly sweeping the
    same ring twice.
    """
    sign = -1.0 if half == "bottom" else 1.0
    return sorted(s["ordinal"] for s in sheets if s["z"] * sign > 0.0)


def _azimuth_class(az_i, az_j):
    """``(steps, residual_deg)``: the C16 azimuth-separation class of a pair.

    The separation is the circular distance folded to ``[0, 180]``, divided by
    the layout's own 22.5 deg step.  The residual is returned so the caller can
    *assert* the pair lands on a class rather than rounding it into one.
    """
    delta = abs((az_i - az_j + 180.0) % 360.0 - 180.0)
    steps = int(round(delta / AZIMUTH_STEP_DEG))
    return steps, abs(delta - steps * AZIMUTH_STEP_DEG)


# ---------------------------------------------------------------------------
# Windows A and B — one ring half, sixteen drives, sixteen cached columns
# ---------------------------------------------------------------------------


@complex_only
def test_the_sweep_half_solves_and_caches_its_sixteen_columns():
    """Drive one ring's sixteen ports and cache the columns (windows A / B).

    Skipped unless ``FEM_EM_RING_SWEEP_HALF`` names a half, so the module is
    collectable — and window C is runnable — without a solve.  The quantitative
    assertions here are the ones that must hold *before* the cache is trusted by
    the assembly window: the mesh is `GEO-26` step 2's record fixture, every
    column carries all 32 ports, and every one of the sixteen power-accounting
    residuals is inside the imported, unmoved band.
    """
    half = os.environ.get(SWEEP_ENV)
    if half is None:
        pytest.skip(
            f"{SWEEP_ENV} unset: this is the assembly window, which runs no solve"
        )
    assert half in SWEEP_HALVES, (
        f"{SWEEP_ENV}={half!r} is not one of {SWEEP_HALVES}; the half is selected "
        "by this variable alone, never by a -k expression"
    )

    t_window = time.perf_counter()
    built = _build_ring_context()
    comm = built["comm"]
    sheets = built["sheets"]
    m = built["m"]

    ratio = built["cells"] / RING_LONGITUDINAL_SCALED_CELL_RECORD
    assert abs(ratio - 1.0) < CELL_COUNT_BAND, (
        f"the {half} window meshed {built['cells']} cells against `GEO-26` step 2's "
        f"longitudinal record {RING_LONGITUDINAL_SCALED_CELL_RECORD} (ratio "
        f"{ratio:.6f}); the two halves must be one fixture or the assembled S is "
        "not a matrix of one network"
    )

    ordinals = _half_ordinals(sheets, half)
    assert len(ordinals) == SCALED_LEG_COUNT, (
        f"the {half} ring carries {len(ordinals)} measured ring ports, not the "
        f"{SCALED_LEG_COUNT} a 16-leg high-pass layout puts on one ring"
    )
    sigma_map = built["sigma_map"]
    assert len(sigma_map) == 2 * SCALED_LEG_COUNT

    port_ordinals = sorted(built["ring_ports"])
    assert len(port_ordinals) == 2 * SCALED_LEG_COUNT

    if comm.rank == 0:
        print(
            f"\n[PORT-13 step3] window {half.upper()}: {built['cells']} cells "
            f"(record {RING_LONGITUDINAL_SCALED_CELL_RECORD}, ratio {ratio:.6f}), "
            f"mesh {m['diag']['mesh_wall_time_s']:.2f} s, rung {m['elapsed']:.2f} s; "
            f"driving the {len(ordinals)} {half}-ring ports "
            f"P{ordinals[0]}…P{ordinals[-1]} at {comm.size} ranks",
            flush=True,
        )

    columns = {}
    for ordinal in ordinals:
        columns[ordinal] = _solve_one_drive(built["ctx"], f"P{ordinal}")
        if comm.rank == 0:
            col = columns[ordinal]
            print(
                f"[PORT-13 step3] {half} drive P{ordinal:<2d}  solve "
                f"{col['solve_time']:6.2f} s  sum|S|^2 "
                f"{sum(abs(s) ** 2 for s in col['s_column'].values()):.9f}  "
                f"residual {col['residual']:.6e} "
                f"({col['residual'] / POWER_BALANCE_BAND:.3f}x the band)",
                flush=True,
            )
        # The solved fields are not needed past the column and are the largest
        # object each drive produces; drop the reference so the peak RSS below
        # measures the solver, not sixteen retained field pairs.
        columns[ordinal].pop("fields", None)

    for ordinal, col in columns.items():
        assert len(col["s_column"]) == 2 * SCALED_LEG_COUNT
        assert all(
            np.isfinite(s.real) and np.isfinite(s.imag)
            for s in col["s_column"].values()
        )
        assert col["supplied"] > 0.0, (
            f"driving P{ordinal} the sheet supplies {col['supplied']:.9e} W — a "
            "passive load cannot absorb negative real power"
        )
        assert col["residual"] <= POWER_BALANCE_BAND, (
            f"driving P{ordinal}, power accounting misses by {col['residual']:.6e} "
            f"of the supplied {col['supplied']:.9e} W; band "
            f"{POWER_BALANCE_BAND:.0e}, imported and unmoved (§9 item 1 negative "
            "result: the residual into known-issues, stop)"
        )

    rss_gib = float(
        comm.allreduce(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, op=MPI.SUM)
    ) / (1024.0 * 1024.0)
    elapsed = time.perf_counter() - t_window

    # Every terminal current is already MPI-reduced inside `sheet_terminal_current`,
    # so the columns are identical on every rank; the barrier is what makes "rank 0
    # writes after every rank has finished" true rather than probable.
    comm.Barrier()
    if comm.rank == 0:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(
            _half_file(half),
            half=np.array(half),
            port_ordinals=np.array(port_ordinals, dtype=np.int64),
            drive_ordinals=np.array(ordinals, dtype=np.int64),
            s_columns=np.array(
                [[columns[o]["s_column"][f"P{p}"] for p in port_ordinals]
                 for o in ordinals],
                dtype=complex,
            ),
            residuals=np.array([columns[o]["residual"] for o in ordinals]),
            blind=np.array([columns[o]["blind"] for o in ordinals]),
            solve_times=np.array([columns[o]["solve_time"] for o in ordinals]),
            azimuth_deg=np.array(
                [built["azimuth_deg"][p] for p in port_ordinals], dtype=float
            ),
            z=np.array(
                [s["z"] for s in sorted(sheets, key=lambda s: s["ordinal"])],
                dtype=float,
            ),
            cells=np.array(built["cells"], dtype=np.int64),
            ranks=np.array(comm.size, dtype=np.int64),
        )
        print(
            f"[PORT-13 step3] window {half.upper()} PRICE: "
            f"{sum(c['solve_time'] for c in columns.values()):.2f} s of solve over "
            f"{len(ordinals)} drives (min {min(c['solve_time'] for c in columns.values()):.2f}, "
            f"max {max(c['solve_time'] for c in columns.values()):.2f}), window "
            f"{elapsed:.2f} s wall at -n {comm.size}; summed ru_maxrss "
            f"{rss_gib:.3f} GiB against the 128 G cap; cached 16 columns to "
            f"{_half_file(half)}",
            flush=True,
        )
    comm.Barrier()


# ---------------------------------------------------------------------------
# Window C — assembly, no solve
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ring_matrix():
    """Load both cached halves and assemble the 32x32 ``S``; no solve.

    Skips with a message (never fails) when either cache is missing, so the
    module collects and the two solve windows remain the only thing that costs
    compute.
    """
    missing = [str(_half_file(h)) for h in SWEEP_HALVES if not _half_file(h).exists()]
    if missing:
        pytest.skip(
            "the cached sweep halves "
            + ", ".join(missing)
            + " are absent: run windows A and B (FEM_EM_RING_SWEEP_HALF=bottom|top) "
            "first; `output/` is gitignored, so a clean tree has no caches"
        )

    data = {h: np.load(_half_file(h), allow_pickle=False) for h in SWEEP_HALVES}

    port_ordinals = data["bottom"]["port_ordinals"]
    index = {int(p): k for k, p in enumerate(port_ordinals)}
    n = len(port_ordinals)

    s = np.zeros((n, n), dtype=complex)
    filled = np.zeros(n, dtype=bool)
    residuals = {}
    for h in SWEEP_HALVES:
        for k, o in enumerate(data[h]["drive_ordinals"]):
            j = index[int(o)]
            s[:, j] = data[h]["s_columns"][k]
            filled[j] = True
            residuals[int(o)] = float(data[h]["residuals"][k])

    return {
        "data": data,
        "port_ordinals": [int(p) for p in port_ordinals],
        "index": index,
        "S": s,
        "filled": filled,
        "residuals": residuals,
        "azimuth_deg": np.asarray(data["bottom"]["azimuth_deg"], dtype=float),
        "z": np.asarray(data["bottom"]["z"], dtype=float),
    }


@complex_only
def test_the_two_halves_came_off_one_fixture(ring_matrix):
    """**Anchor (v)** — the two windows meshed the same rung, port for port.

    Structural, and load-bearing for every identity below: the halves are built
    in two separate processes, so if the mesh were not deterministic the 32x32
    would be a matrix of two different networks and its reciprocity would be
    measuring the mesh.  Both cell counts must equal each other and `GEO-26`
    step 2's record, and both azimuth tables must agree to 1e-9 deg.
    """
    d = ring_matrix["data"]
    cells = {h: int(d[h]["cells"]) for h in SWEEP_HALVES}
    assert cells["bottom"] == cells["top"], (
        f"the two windows meshed {cells['bottom']} and {cells['top']} cells; the "
        "assembled S would then mix two networks"
    )
    assert cells["bottom"] == RING_LONGITUDINAL_SCALED_CELL_RECORD, (
        f"the sweep meshed {cells['bottom']} cells against `GEO-26` step 2's "
        f"record {RING_LONGITUDINAL_SCALED_CELL_RECORD}"
    )

    assert list(d["bottom"]["port_ordinals"]) == list(d["top"]["port_ordinals"])
    az_gap = float(
        np.max(np.abs(d["bottom"]["azimuth_deg"] - d["top"]["azimuth_deg"]))
    )
    z_gap = float(np.max(np.abs(d["bottom"]["z"] - d["top"]["z"])))
    assert az_gap < 1.0e-9, (
        f"the two windows' measured azimuth tables differ by {az_gap:.3e} deg"
    )
    assert z_gap < 1.0e-12

    drives = sorted(
        int(o) for h in SWEEP_HALVES for o in d[h]["drive_ordinals"]
    )
    assert drives == ring_matrix["port_ordinals"], (
        f"the two halves drove {len(drives)} ports, which are not the "
        f"{len(ring_matrix['port_ordinals'])} ring ports of the layout"
    )
    assert bool(np.all(ring_matrix["filled"])), "a column of S was never driven"

    # The halves must be the two *rings*, located by measured z, not two
    # arbitrary sixteens.
    z = ring_matrix["z"]
    for h, sign in (("bottom", -1.0), ("top", 1.0)):
        for o in d[h]["drive_ordinals"]:
            assert z[ring_matrix["index"][int(o)]] * sign > 0.0, (
                f"P{int(o)} was driven in the {h} window but its sheet centre "
                f"sits at z = {z[ring_matrix['index'][int(o)]]:+.6e}"
            )

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-13 step3] GATE (v) one fixture, two windows: "
            f"{cells['bottom']} cells in both (record "
            f"{RING_LONGITUDINAL_SCALED_CELL_RECORD}), azimuth tables agree to "
            f"{az_gap:.3e} deg, all {len(drives)} columns driven; window solve "
            + ", ".join(
                f"{h} {float(np.sum(d[h]['solve_times'])):.2f} s at -n "
                f"{int(d[h]['ranks'])}"
                for h in SWEEP_HALVES
            ),
            flush=True,
        )


@complex_only
def test_all_thirty_two_columns_balance_power(ring_matrix):
    """**Anchor (vi)** — every one of the 32 drives closed its accounting.

    The band is the imported ``POWER_BALANCE_BAND``, unmoved: the 2026-09-04
    03:00 review ruled that step 1's 0.97-of-band residual gets no new band, and
    32 drives agreeing on that offset is the ruling's own prediction made
    visible, not a licence to widen anything.
    """
    residuals = ring_matrix["residuals"]
    assert len(residuals) == 2 * SCALED_LEG_COUNT
    worst = max(residuals, key=lambda o: residuals[o])

    if MPI.COMM_WORLD.rank == 0:
        values = np.array([residuals[o] for o in sorted(residuals)])
        print(
            f"\n[PORT-13 step3] GATE (vi) power accounting over all 32 drives "
            f"(band {POWER_BALANCE_BAND:.0e}, imported, unmoved): min "
            f"{values.min():.6e}, max {values.max():.6e} (P{worst}, "
            f"{values.max() / POWER_BALANCE_BAND:.3f}x the band), spread "
            f"{values.max() - values.min():.3e}",
            flush=True,
        )

    assert residuals[worst] <= POWER_BALANCE_BAND, (
        f"driving P{worst}, power accounting misses by {residuals[worst]:.6e} "
        f"against the unmoved {POWER_BALANCE_BAND:.0e} band (§9 item 1 negative "
        "result: the residuals into known-issues, band not widened, stop)"
    )


@complex_only
def test_the_thirty_two_by_thirty_two_is_reciprocal(ring_matrix):
    """**Anchor (i)** — ``‖S − Sᵀ‖_F/‖S‖_F <= 1e-3``, with the (d2) control.

    Reciprocity is a property of the physics, not of the port model, and here it
    is also a mesh-reproducibility reading: columns 1-16 and 17-32 were solved in
    two different processes over two independently built meshes, so a
    non-deterministic mesher would show up as asymmetry.  The band is `PORT-9`'s
    imported ``RECIPROCITY_BAND``, unmoved.

    The in-run negative control is the `PORT-9` leg (d2) defect class — a
    per-column normalisation error, invisible to passivity — scaled onto one
    cached column at 1%.
    """
    s = ring_matrix["S"]
    ratio = _reciprocity_ratio(s)

    control = s.copy()
    control[:, 0] *= CONTROL_COLUMN_SCALE
    control_ratio = _reciprocity_ratio(control)

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-13 step3] GATE (i) reciprocity of the 32x32 (band "
            f"{RECIPROCITY_BAND:.0e}, imported, unmoved): "
            f"||S - S^T||_F/||S||_F = {ratio:.6e} "
            f"({ratio / RECIPROCITY_BAND:.3e}x the band, "
            f"{'INSIDE' if ratio <= RECIPROCITY_BAND else 'MISS'}); "
            f"||S||_F = {np.linalg.norm(s, ord='fro'):.6f}\n"
            f"    negative control, column P{ring_matrix['port_ordinals'][0]} "
            f"scaled by {CONTROL_COLUMN_SCALE:.2f}: {control_ratio:.6e} "
            f"({control_ratio / RECIPROCITY_BAND:.3f}x the band; the item's "
            f"ceiling is ~2.5x, the bar {MATRIX_CONTROL_MARGIN:.0f}x)",
            flush=True,
        )

    assert ratio <= RECIPROCITY_BAND, (
        f"the assembled 32x32 is asymmetric at {ratio:.6e}, outside the unmoved "
        f"{RECIPROCITY_BAND:.0e} band — 32 columns of one reciprocal network "
        f"cannot disagree this much (§9 item 1 negative result: |S| into "
        f"known-issues, band not widened, stop)"
    )
    assert control_ratio >= MATRIX_CONTROL_MARGIN * RECIPROCITY_BAND, (
        f"a {(CONTROL_COLUMN_SCALE - 1.0) * 100:.0f}% per-column normalisation "
        f"error moves the reciprocity ratio only to {control_ratio:.6e}, under "
        f"the {MATRIX_CONTROL_MARGIN:.0f}x{RECIPROCITY_BAND:.0e} bar; the gate "
        "above is then not sensitive to the defect it exists to catch"
    )


@complex_only
def test_the_matrix_is_passive(ring_matrix):
    """**Anchor (ii)** — ``sigma_max(S) <= 1`` on the assembled 32x32.

    `PORT-9`'s passivity gate in its matrix form, and strictly stronger than
    step 2's per-column ``Σ_i|S_ij|² <= 1``: the column reading bounds the
    diagonal of ``SᴴS``, the singular value bounds the whole of it.  The ceiling
    is the physical 1, not a band; the margin is a measurement and is printed.
    """
    s = ring_matrix["S"]
    sigma_max = float(np.linalg.norm(s, 2))
    column_norms = np.sum(np.abs(s) ** 2, axis=0)

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-13 step3] GATE (ii) passivity of the matrix, sigma_max(S) "
            f"<= {MATRIX_PASSIVITY_CEILING:.0f} (`PORT-9`'s gate, a necessary "
            f"condition, not a band):\n"
            f"    sigma_max = {sigma_max:.9f}  margin "
            f"{MATRIX_PASSIVITY_CEILING - sigma_max:+.9f} "
            f"({(MATRIX_PASSIVITY_CEILING - sigma_max) * 100:+.4f}%)  "
            f"{'PASSIVE' if sigma_max <= MATRIX_PASSIVITY_CEILING else 'ACTIVE'}\n"
            f"    column sum|S|^2 over the 32 drives: min "
            f"{column_norms.min():.9f}, max {column_norms.max():.9f}",
            flush=True,
        )

    assert float(column_norms.max()) <= MATRIX_PASSIVITY_CEILING
    assert sigma_max <= MATRIX_PASSIVITY_CEILING, (
        f"sigma_max(S) = {sigma_max:.9f} > 1: the passive 32-port ring network "
        f"would amplify some excitation vector, which is a port-normalisation "
        f"defect, not a tolerance (§9 item 1 negative result: |S| and sigma_max "
        f"into known-issues; a reading in (1, 1+1e-2] names the 0.97-of-band "
        f"accounting offset as the suspect, and nothing is widened)"
    )


@complex_only
def test_the_matrix_carries_the_c16_and_mirror_symmetry(ring_matrix):
    """**Anchor (iii)** — 18 symmetry classes, each spread inside 5%.

    The fixture is invariant under the 16-fold rotation about ``z`` and under
    the ``z``-mirror, so ``|S_ij|`` may depend only on (which ring relation the
    pair has) x (their azimuth separation).  That is 2 x 9 = 18 classes over the
    1024 entries, and it is the first identity on this rung that reads the
    matrix as a *network* rather than as a set of columns.  Classes are built
    from the **measured** azimuths and the measured ring membership; a pair that
    lands on no class to ``AZIMUTH_MATCH_DEG`` fails here rather than being
    dropped.  The band is step 1's unmoved ``OPPOSITE_SPREAD_BAND``.
    """
    s = ring_matrix["S"]
    az = ring_matrix["azimuth_deg"]
    z = ring_matrix["z"]
    n = len(az)

    classes = {}
    for i in range(n):
        for j in range(n):
            steps, residual_deg = _azimuth_class(az[i], az[j])
            assert residual_deg < AZIMUTH_MATCH_DEG, (
                f"the pair (P{ring_matrix['port_ordinals'][i]}, "
                f"P{ring_matrix['port_ordinals'][j]}) sits {residual_deg:.3e} deg "
                f"off every multiple of {AZIMUTH_STEP_DEG:.4f} deg — it belongs to "
                "no C16 class and must not be silently dropped"
            )
            assert 0 <= steps <= SCALED_LEG_COUNT // 2
            same_ring = bool(z[i] * z[j] > 0.0)
            classes.setdefault((same_ring, steps), []).append(
                (i, j, float(abs(s[i, j])))
            )

    assert len(classes) == N_SYMMETRY_CLASSES, (
        f"the measured geometry produced {len(classes)} symmetry classes, not the "
        f"{N_SYMMETRY_CLASSES} a C16 x mirror layout carries"
    )
    assert sum(len(v) for v in classes.values()) == n * n

    spreads = {}
    for key, entries in classes.items():
        mags = np.array([e[2] for e in entries])
        mean = float(mags.mean())
        spreads[key] = (
            float((mags.max() - mags.min()) / mean) if mean > 0.0 else float("inf"),
            len(entries),
            mean,
            entries[int(np.argmax(mags))],
            entries[int(np.argmin(mags))],
        )
    worst = max(spreads, key=lambda k: spreads[k][0])

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-13 step3] GATE (iii) the C16 x mirror class identity over "
            f"{N_SYMMETRY_CLASSES} classes (band {OPPOSITE_SPREAD_BAND * 100:.0f}%, "
            f"step 1's, unmoved); classes built from the measured azimuths and "
            f"ring membership:",
            flush=True,
        )
        for same_ring in (True, False):
            for steps in range(N_AZIMUTH_CLASSES):
                spread, count, mean, hi, lo = spreads[(same_ring, steps)]
                print(
                    f"    {'same ' if same_ring else 'other'} ring, "
                    f"{steps} x {AZIMUTH_STEP_DEG:.3f} deg  n = {count:4d}  "
                    f"mean |S| = {mean:.9e}  spread {spread * 100:8.4f}%"
                    + ("   <-- worst" if (same_ring, steps) == worst else ""),
                    flush=True,
                )
        spread, count, mean, hi, lo = spreads[worst]
        print(
            f"    worst class {'same' if worst[0] else 'other'} ring / "
            f"{worst[1]} steps at {spread * 100:.4f}%: max |S| = {hi[2]:.9e} at "
            f"(P{ring_matrix['port_ordinals'][hi[0]]}, "
            f"P{ring_matrix['port_ordinals'][hi[1]]}), min = {lo[2]:.9e} at "
            f"(P{ring_matrix['port_ordinals'][lo[0]]}, "
            f"P{ring_matrix['port_ordinals'][lo[1]]})  "
            f"{'INSIDE' if spread <= OPPOSITE_SPREAD_BAND else 'MISS'}",
            flush=True,
        )

    assert spreads[worst][0] <= OPPOSITE_SPREAD_BAND, (
        f"the symmetry class ({'same' if worst[0] else 'other'} ring, {worst[1]} "
        f"steps of {AZIMUTH_STEP_DEG:.3f} deg) spreads "
        f"{spreads[worst][0] * 100:.4f}% over its {spreads[worst][1]} entries, "
        f"against the unmoved {OPPOSITE_SPREAD_BAND * 100:.0f}% band — the "
        f"assembled matrix does not carry the fixture's C16 x mirror symmetry "
        f"(§9 item 1 negative result: the class table into known-issues, band not "
        f"widened, stop)"
    )


@complex_only
def test_the_sweep_reproduces_step_twos_audited_columns(ring_matrix):
    """**Anchor (iv)** — the four step-2 column norms, to rtol 1e-6.

    The tie to the audited step: four of these 32 columns were read, printed and
    reviewed on 2026-09-04 (`20260904T093638Z_PORT-13.log:10797–10800`).  If the
    sweep's refactor (the additive ``_build_ring_context``) or the split into two
    windows had moved anything, this is where it shows.  The tolerance is the
    run-to-run scatter, not a physical band.
    """
    s = ring_matrix["S"]
    index = ring_matrix["index"]
    measured = {
        o: float(np.sum(np.abs(s[:, index[o]]) ** 2))
        for o in STEP2_COLUMN_POWER_SUMS
    }

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-13 step3] GATE (iv) the four step-2 columns reproduced "
            f"(rtol {STEP2_COLUMN_POWER_RTOL:.0e}, the `OPS-34` scatter precedent):",
            flush=True,
        )
        for o, recorded in STEP2_COLUMN_POWER_SUMS.items():
            print(
                f"    column P{o:<2d}  sum|S|^2 = {measured[o]:.9f}  record "
                f"{recorded:.9f}  rel {abs(measured[o] - recorded) / recorded:.3e}",
                flush=True,
            )

    for o, recorded in STEP2_COLUMN_POWER_SUMS.items():
        rel = abs(measured[o] - recorded) / recorded
        assert rel <= STEP2_COLUMN_POWER_RTOL, (
            f"column P{o} now reads sum_i|S_ij|^2 = {measured[o]:.9f} against step "
            f"2's audited {recorded:.9f} ({rel:.3e} relative, rtol "
            f"{STEP2_COLUMN_POWER_RTOL:.0e}) — this sweep is not measuring the "
            "network step 2 measured"
        )
