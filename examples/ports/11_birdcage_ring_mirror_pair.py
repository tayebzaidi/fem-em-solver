"""Example (`EX-47`): the ring rung's mirror pair in ParaView.

`PORT-13` step 2 (2026-09-04) put a second, independently solved drive on
the 16-leg / 32-ring-port longitudinal rung `EX-46` first solved: the
z-mirror port `P33` alongside `P17`, and with it a **network**-level
identity between two solved columns — the top/bottom mirror table (anchor
v), a 2x2 `S` sub-block (`{P17, P33}`) and its reciprocity (anchor iii), and
per-column passivity (anchor iv). `ports:10` (`EX-46`) drives one ring port
and writes one field; no example before this one drives two ports of one
coil and puts their fields side by side in one file, and none prints an `S`
sub-block on the ring rung.

**It asserts, it does not merely render** (the `ANS-1` rule). Every record,
band and helper below is imported from
``tests/validation/test_port_birdcage_ring_column.py`` — nothing here is
restated. The context comes from that module's own ``_build_ring_context``
(`PORT-13` step 3, additive, landed 2026-09-04 — the fixture body is not
typed a third time: `ports:10` reimplemented it inline before this function
existed, this script imports it instead):

* cells = ``RING_LONGITUDINAL_SCALED_CELL_RECORD`` at ``CELL_COUNT_BAND``;
* the 2x2 sub-block ``{P17, P33}``'s ``_reciprocity_ratio`` <=
  ``RECIPROCITY_BAND``;
* the worst of the 32 measured top/bottom mirror pairs <=
  ``OPPOSITE_SPREAD_BAND``;
* each column's ``Sigma_i |S_ij|^2`` <= ``COLUMN_PASSIVITY_CEILING`` and its
  power-accounting residual <= ``POWER_BALANCE_BAND``;
* the ``P17`` column's ``Sigma |S_ij|^2`` reproduces step 2's own recorded
  **0.915817419** (`20260904T093638Z_PORT-13.log:10797`) at rtol 1e-3 (this
  run is at ``-n 4`` against the gate's ``-n 8`` — the `EX-46` precedent for
  a cross-rank-count reproduction).

**Negative control.** The ``P17`` column of the 2x2 sub-block scaled by the
imported ``CONTROL_COLUMN_SCALE`` (1.01, the `PORT-9` leg (d2)
per-column-normalisation defect class) must move the reciprocity ratio to at
least ``CONTROL_MARGIN_FACTOR`` (5x) times ``RECIPROCITY_BAND`` — the exact
in-run control the gate module's own reciprocity test uses.

**Scope.** An example of two columns: no band, no gate, no 32x32, no
``src/`` change. `PORT-13` step 3's full 32x32 is a separate rung
(`tests/validation/test_port_birdcage_ring_matrix.py`), not touched here.

Needs the complex DolfinX build. Run it through the example runner, which
sources complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:11 -n 4 -t 600

Outputs
``paraview_output/ports_11_birdcage_ring_mirror_pair_combined.xdmf`` — the
mesh, ``CellTags``, the 32 sheet facet tags (as ``mesh_tags``) and **two**
distinctly named DG0 arrays, ``E_magnitude_P17`` and ``E_magnitude_P33``, so
ParaView's *Reflect* filter on ``z`` can overlay one on the other.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import fem, io

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gate's constants, helpers and construction can be imported rather than
# restated (the `ANS-1` rule).
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    cell_tags_to_function,
    consolidate_xdmf_grids,
)

from tests.validation.test_port_birdcage_ring_column import (  # noqa: E402
    CELL_COUNT_BAND,
    COLUMN_PASSIVITY_CEILING,
    CONTROL_COLUMN_SCALE,
    CONTROL_MARGIN_FACTOR,
    FREQUENCY_HZ,
    OPPOSITE_SPREAD_BAND,
    POWER_BALANCE_BAND,
    RECIPROCITY_BAND,
    RING_LONGITUDINAL_SCALED_CELL_RECORD,
    SOLVE_PRICE_STOP_RULE_S,
    TERMINATED_PORT_IMPEDANCE_OHM,
    _build_ring_context,
    _reciprocity_ratio,
    _solve_one_drive,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "ports_11_birdcage_ring_mirror_pair"

# `PORT-13` step 2's own recorded `P17` column passivity sum, read off its
# printed GATE (iv) line at `-n 8` (`20260904T093638Z_PORT-13.log:10797`).
# Not an importable module constant (a fixture-computed reading, printed, not
# a module-level record), so carried here as a literal, checked at rtol 1e-3
# rather than restated as if it were a closed form — the `EX-42`/`EX-46`
# precedent for a printed-not-named record.
STEP2_P17_PASSIVITY_SUM_RECORD = 0.915817419
PASSIVITY_SUM_RTOL = 1.0e-3


def _magnitude_field(e_complex, name):
    """DG0 ``|E|`` [V/m] over the whole domain — the honest, cell-wise
    resolution of a degree-1 curl element (`EX-26`'s convention, `EX-46`'s
    reuse), never interpolated onto a smoother CG space than the
    discretisation supports.
    """
    msh = e_complex.function_space.mesh
    dg0 = fem.functionspace(msh, ("DG", 0))
    expr_ufl = ufl.sqrt(ufl.inner(e_complex, e_complex))
    # OPS-18: on the 0.11 image, `interpolation_points` is a property, not a
    # method.
    expr = fem.Expression(expr_ufl, dg0.element.interpolation_points)
    field = fem.Function(dg0, name=name)
    field.interpolate(expr)
    # `|E|` is real by construction (inner(E, conj(E))); XDMF carries no
    # complex array (`EX-14`/`EX-17`), so the real part is what is written.
    out = fem.Function(dg0, name=name)
    out.x.array[:] = np.real(field.x.array)
    out.x.scatter_forward()
    return out


def _write_combined(msh, cell_tags, sheet_tags, fields, comm):
    """Mesh + ``CellTags`` + the two DG0 fields + the 32 sheet facet tags, in
    **one** XDMF file. Both fields carry distinct ``name``s (``EX-46``'s
    trap: one shared name and ParaView shows only one of the two).
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{BASENAME}_combined.xdmf"
    msh.topology.create_connectivity(msh.topology.dim - 1, msh.topology.dim)
    with io.XDMFFile(comm, path, "w") as xdmf:
        xdmf.write_mesh(msh)
        xdmf.write_function(cell_tags_to_function(msh, cell_tags))
        for func in fields.values():
            xdmf.write_function(func)
        xdmf.write_meshtags(sheet_tags, msh.geometry)
    consolidate_xdmf_grids(path, comm=comm)
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path if comm.rank == 0 else None


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    from dolfinx import default_scalar_type

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ports:` group)."
        )

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            "EX-47 — the ring rung's mirror pair in ParaView: |E| for the "
            "P17 and P33 drives side by side, the 2x2 S sub-block and its "
            "reciprocity",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            "\n[fixture] `PORT-13` step 2 context (`_build_ring_context`, "
            f"imported): 16-leg / 32-ring-port longitudinal rung, phantom "
            f"loaded, {FREQUENCY_HZ:.3e} Hz, degree 1, 31 ports at "
            f"Z_p = {TERMINATED_PORT_IMPEDANCE_OHM} Ohm\n"
            "[gates]   cells = RING_LONGITUDINAL_SCALED_CELL_RECORD at "
            "CELL_COUNT_BAND; 2x2 reciprocity <= RECIPROCITY_BAND; worst "
            "mirror pair <= OPPOSITE_SPREAD_BAND; column passivity <= "
            "COLUMN_PASSIVITY_CEILING; residual <= POWER_BALANCE_BAND; P17 "
            "passivity sum vs step 2's own record at rtol 1e-3\n"
            "[control] the P17 column of the 2x2 scaled by "
            f"{CONTROL_COLUMN_SCALE:.2f} must move reciprocity to >= "
            f"{CONTROL_MARGIN_FACTOR:.0f}x the band",
            flush=True,
        )

    built = _build_ring_context()
    ctx = built["ctx"]
    m = built["m"]
    sheets = built["sheets"]
    driven, driven_id = built["driven"], built["driven_id"]
    mirror = built["mirror"]
    mirror_id = f"P{mirror}"
    sigma_map = built["sigma_map"]

    cell_ratio = built["cells"] / RING_LONGITUDINAL_SCALED_CELL_RECORD
    if comm.rank == 0:
        print(
            f"\n[mesh] {built['cells']} cells (record "
            f"{RING_LONGITUDINAL_SCALED_CELL_RECORD}, ratio {cell_ratio:.6f}), "
            f"mesh {m['diag']['mesh_wall_time_s']:.2f} s, rung "
            f"{m['elapsed']:.2f} s",
            flush=True,
        )
    assert abs(cell_ratio - 1.0) < CELL_COUNT_BAND, (
        f"the rung meshed {built['cells']} cells against "
        f"RING_LONGITUDINAL_SCALED_CELL_RECORD "
        f"{RING_LONGITUDINAL_SCALED_CELL_RECORD} (ratio {cell_ratio:.6f}) — "
        "this is not the fixture `PORT-13` gates"
    )

    # ---- the two drives -----------------------------------------------------
    comm.Barrier()
    col_p17 = _solve_one_drive(ctx, driven_id)
    col_p33 = _solve_one_drive(ctx, mirror_id)
    two_drive_total = col_p17["solve_time"] + col_p33["solve_time"]
    if comm.rank == 0:
        print(
            f"\n[solve] two drives over the one mesh: {driven_id} "
            f"{col_p17['solve_time']:.2f} s, {mirror_id} "
            f"{col_p33['solve_time']:.2f} s wall at -n {comm.size} (stop "
            f"rule {SOLVE_PRICE_STOP_RULE_S:.0f} s; total "
            f"{two_drive_total:.2f} s)",
            flush=True,
        )

    columns = {driven_id: col_p17, mirror_id: col_p33}

    # ---- gate (i): power accounting on both columns --------------------------
    if comm.rank == 0:
        print(
            f"\n[gate i] power accounting on both columns (band "
            f"{POWER_BALANCE_BAND:.0e}, imported):",
            flush=True,
        )
        for pid, col in columns.items():
            print(
                f"    {pid:>4s}  supplied {col['supplied']:.9e} W  phantom "
                f"{col['phantom']:.9e} W  conductor {col['conductor']:.9e} W  "
                f"32 sheets {col['sheet_total']:.9e} W  residual "
                f"{col['residual']:.6e}  "
                f"{'INSIDE' if col['residual'] <= POWER_BALANCE_BAND else 'MISS'}",
                flush=True,
            )
    for pid, col in columns.items():
        assert col["supplied"] > 0.0, (
            f"{pid} supplies {col['supplied']:.9e} W — a passive load "
            "cannot absorb negative real power"
        )
        assert col["residual"] <= POWER_BALANCE_BAND, (
            f"{pid} power accounting misses by {col['residual']:.6e} of the "
            f"supplied {col['supplied']:.9e} W; band {POWER_BALANCE_BAND:.0e} "
            "(§7 `EX-47` negative result: example/test divergence, "
            "known-issues entry, stop; never re-record from the example side)"
        )

    # ---- gate (iv): column passivity, both columns ---------------------------
    norms = {
        pid: float(sum(abs(s) ** 2 for s in col["s_column"].values()))
        for pid, col in columns.items()
    }
    if comm.rank == 0:
        print(
            f"\n[gate iv] column passivity, sum_i |S_ij|^2 <= "
            f"{COLUMN_PASSIVITY_CEILING:.0f} (imported ceiling, not a band):",
            flush=True,
        )
        for pid, norm in norms.items():
            print(
                f"    column {pid:>4s}  sum|S|^2 = {norm:.9f}  margin "
                f"{COLUMN_PASSIVITY_CEILING - norm:+.9f}  "
                f"{'PASSIVE' if norm <= COLUMN_PASSIVITY_CEILING else 'ACTIVE'}",
                flush=True,
            )
    for pid, norm in norms.items():
        assert norm > 0.0
        assert norm <= COLUMN_PASSIVITY_CEILING, (
            f"column {pid} scatters sum_i |S_ij|^2 = {norm:.9f} > 1 — a "
            "port-normalisation defect, not a tolerance (§7 `EX-47` "
            "negative result: known-issues entry, stop)"
        )

    # ---- the P17 passivity sum reproduces step 2's own record ---------------
    p17_relative = abs(norms[driven_id] - STEP2_P17_PASSIVITY_SUM_RECORD) / abs(
        STEP2_P17_PASSIVITY_SUM_RECORD
    )
    if comm.rank == 0:
        print(
            f"\n[gate] {driven_id} passivity sum {norms[driven_id]:.9f} vs "
            f"step 2's own record {STEP2_P17_PASSIVITY_SUM_RECORD:.9f} at "
            f"-n 8 (relative {p17_relative:.3e}, rtol "
            f"{PASSIVITY_SUM_RTOL:.0e} — rank count differs from the gate's "
            "-n 8, so 1e-6 is not claimed)",
            flush=True,
        )
    assert p17_relative <= PASSIVITY_SUM_RTOL, (
        f"the {driven_id} passivity sum {norms[driven_id]:.9f} misses step "
        f"2's own recorded {STEP2_P17_PASSIVITY_SUM_RECORD:.9f} by "
        f"{p17_relative:.3e}, outside rtol {PASSIVITY_SUM_RTOL:.0e} (§7 "
        "`EX-47` negative result: example/test divergence, known-issues "
        "entry, stop; never re-record from the example side)"
    )

    # ---- gate (iii): the 2x2 sub-block and its reciprocity, with control ----
    ids = [driven_id, mirror_id]
    s2 = np.array(
        [[columns[pj]["s_column"][pi] for pj in ids] for pi in ids],
        dtype=complex,
    )
    ratio = _reciprocity_ratio(s2)

    control = s2.copy()
    control[:, 0] *= CONTROL_COLUMN_SCALE
    control_ratio = _reciprocity_ratio(control)
    control_factor = control_ratio / RECIPROCITY_BAND

    if comm.rank == 0:
        print(
            f"\n[gate iii] the 2x2 S sub-block, rows/cols {', '.join(ids)} "
            f"(band {RECIPROCITY_BAND:.0e}, imported, unmoved):",
            flush=True,
        )
        for i, pid in enumerate(ids):
            print(
                f"    {pid:>4s}  "
                + "  ".join(f"{s2[i, j]:+.9e}" for j in range(len(ids))),
                flush=True,
            )
        print(
            f"    ||S2 - S2^T||_F/||S2||_F = {ratio:.6e}  "
            f"({ratio / RECIPROCITY_BAND:.3f}x the band, "
            f"{'INSIDE' if ratio <= RECIPROCITY_BAND else 'MISS'})\n"
            f"    negative control, column {ids[0]} scaled by "
            f"{CONTROL_COLUMN_SCALE:.2f}: {control_ratio:.6e} "
            f"({control_factor:.3f}x the band; the item's estimate was "
            f"~9.3x, the bar {CONTROL_MARGIN_FACTOR:.0f}x, none larger "
            "claimed than what is computed)",
            flush=True,
        )

    assert ratio <= RECIPROCITY_BAND, (
        f"the 2x2 sub-block over {ids} is asymmetric at {ratio:.6e}, "
        f"outside the pre-stated {RECIPROCITY_BAND:.0e} band (§7 `EX-47` "
        "negative result: example/test divergence, known-issues entry, "
        "stop; never re-record from the example side)"
    )
    assert control_ratio >= CONTROL_MARGIN_FACTOR * RECIPROCITY_BAND, (
        f"a {(CONTROL_COLUMN_SCALE - 1.0) * 100:.0f}% per-column "
        f"normalisation error moves the reciprocity ratio only to "
        f"{control_ratio:.6e} ({control_factor:.3f}x the band), under the "
        f"{CONTROL_MARGIN_FACTOR:.0f}x bar — the control failed to separate "
        "(§7 `EX-47` negative result: known-issues entry, stop)"
    )

    # ---- gate (v): the top/bottom mirror identity over all 32 pairs ---------
    col_a = columns[driven_id]["s_column"]
    col_b = columns[mirror_id]["s_column"]
    pairs = []
    for o in sorted(sigma_map):
        a = abs(col_a[f"P{o}"])
        b = abs(col_b[f"P{sigma_map[o]}"])
        pairs.append((o, sigma_map[o], a, b, abs(a - b) / a if a else float("inf")))
    worst = max(pairs, key=lambda p: p[4])

    if comm.rank == 0:
        print(
            f"\n[gate v] the top/bottom mirror identity "
            f"|S_(sigma(i)),{mirror_id}| vs |S_i,{driven_id}| over all "
            f"{len(pairs)} ring ports (band {OPPOSITE_SPREAD_BAND * 100:.0f}%, "
            "imported, unmoved):",
            flush=True,
        )
        print(
            f"    worst pair P{worst[0]}/P{worst[1]}: |S_P{worst[0]},"
            f"{driven_id}| = {worst[2]:.9e}  |S_P{worst[1]},{mirror_id}| = "
            f"{worst[3]:.9e}  rel {worst[4] * 100:.4f}%  "
            f"{'INSIDE' if worst[4] <= OPPOSITE_SPREAD_BAND else 'MISS'}",
            flush=True,
        )
    assert len(pairs) == 32
    assert worst[4] <= OPPOSITE_SPREAD_BAND, (
        f"the mirror pair P{worst[0]}/P{worst[1]} reads "
        f"|S_P{worst[0]},{driven_id}| = {worst[2]:.9e} against "
        f"|S_P{worst[1]},{mirror_id}| = {worst[3]:.9e}, {worst[4] * 100:.4f}% "
        f"apart against the unmoved {OPPOSITE_SPREAD_BAND * 100:.0f}% band "
        "(§7 `EX-47` negative result: example/test divergence, "
        "known-issues entry, stop; never re-record from the example side)"
    )

    # ---- the deliverable: |E|_P17 and |E|_P33 in ParaView --------------------
    e_p17 = _magnitude_field(col_p17["fields"].e_complex, "E_magnitude_P17")
    e_p33 = _magnitude_field(col_p33["fields"].e_complex, "E_magnitude_P33")
    written = _write_combined(
        ctx["msh"],
        ctx["cell_tags"],
        ctx["tags_f"],
        {"E_magnitude_P17": e_p17, "E_magnitude_P33": e_p33},
        comm,
    )

    if comm.rank == 0:
        print(f"\n[paraview] wrote {written}")
        print(
            "\n[paraview] threshold `CellTags` (1 conductor, 2 air, 3 "
            "phantom, 101-116 the sixteen uncut leg boxes, 117-148/217-248 "
            "the inner/outer halves of the 32 ring-port boxes) or the "
            "`mesh_tags` facet array for the 32 reconstructed longitudinal "
            f"sheets. Colour by `E_magnitude_P17` and `E_magnitude_P33` "
            f"(both DG0, V/m, distinct names) — apply ParaView's *Reflect* "
            "filter on `z` to one of the two arrays and it overlays the "
            "driven port onto its z-mirror.",
            flush=True,
        )
        print(
            f"\nAll gates hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
