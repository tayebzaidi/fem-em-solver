"""Example (`EX-48`): the ring rung's quarter turn in ParaView.

`PORT-13` step 3 (2026-09-04) gated the full 32x32 on the 16-leg /
32-ring-port longitudinal rung: an 18-class ``C16 x mirror`` identity built
from every pair of the 32 measured azimuths
(``tests/validation/test_port_birdcage_ring_matrix.py``). That module needs
all 32 columns; `ports:11` (`EX-47`) shows the cheaper two-column slice for
the *mirror* (z-flip) symmetry. No example before this one shows a
**rotation** pair — two independently solved columns 4 steps (90 deg) apart
on the same ring — or the C16 class identity that a rotation, not a mirror,
tests.

**It asserts, it does not merely render** (the `ANS-1` rule). Every record,
band and helper below is imported from
``tests/validation/test_port_birdcage_ring_column.py`` (context, the two
solves) and ``tests/validation/test_port_birdcage_ring_matrix.py``
(``AZIMUTH_STEP_DEG``, the C16 step size) — nothing here is restated. The
context comes from ``_build_ring_context`` (`PORT-13` step 3, additive, the
`ports:11` precedent):

* cells = ``RING_LONGITUDINAL_SCALED_CELL_RECORD`` at ``CELL_COUNT_BAND``;
* both columns' power-accounting residual <= ``POWER_BALANCE_BAND``;
* both columns' ``Sigma_i |S_ij|^2`` <= ``COLUMN_PASSIVITY_CEILING``;
* the ``P17`` column's ``Sigma |S_ij|^2`` reproduces step 2's own recorded
  **0.915817419** (`20260904T093638Z_PORT-13.log:10797`) at rtol 1e-3 (this
  run is at ``-n 4`` against the gate's ``-n 8`` — the `EX-46`/`EX-47`
  precedent for a cross-rank-count reproduction);
* **the C16 column identity** — for every ring port ``i``,
  ``|S_{i,P21}|`` vs ``|S_{rho^-4(i),P17}|``, with ``rho`` the 4-step (90 deg)
  rotation on measured azimuths **within each ring** (top rotates onto top,
  bottom onto bottom — the physical rotation of the whole coil about ``z``),
  worst relative mismatch <= ``OPPOSITE_SPREAD_BAND`` (5%; step 3 measured
  every 18-class mean <= 0.4426%, `20260904T171419Z_PORT-13.log:93-111`).

``P21`` itself is never assumed from the ordinal: it is found the same way
``_driven_and_opposite``/``_ring_mirror_map`` find their partners in the gate
module — the one ring port sharing ``P17``'s ring whose measured azimuth
sits ``4 * AZIMUTH_STEP_DEG`` away, to ``AZIMUTH_MATCH_DEG``. Likewise
``rho^-4(i)`` for every port is found by measured-azimuth search, never
ordinal arithmetic; a port with no such partner is an assertion failure, not
a silent drop.

**Negative control, ceiling first.** The same per-port comparison with a
**3-step** (67.5 deg) rotation instead of 4 pairs each port against a
partner one class off from the one the driven pair ``P21`` actually sits at
— from step 3's class means this is expected to miss by roughly the 14x
factor between the 0-step/1-step class-mean gap step 3 measured
(`20260904T171419Z_PORT-13.log:93-111`: same-ring 4.307e-2 vs 7.418e-2, a
72% mismatch; other-ring 0.8948 vs 4.995e-2, 94%). Asserted only to
``CONTROL_MARGIN_FACTOR`` (5x) the band, the measured factor printed, none
larger claimed than what this run computes.

**One ungated reading, printed only.** ``|E|`` sampled through
``post.evaluation.evaluate_vector_field_parallel`` on a 64-point ring
(r = 0.02 m, z = 0) inside the phantom, for both drives; the ``P21`` samples
compared against the ``P17`` samples rotated by 90 deg (a 16-sample index
shift on the 64-point ring). No band: this is the field-level statement the
mesh cannot make exactly at CG1 (`WF-6` step 1's C4 field identities read
~2% on the 4-leg mesh) — printed for inspection, never asserted.

**Scope.** An example of two columns and one field-level reading: no band,
no gate, no 32x32, no ``src/`` change. `PORT-13` step 3's full 32x32 lives in
``tests/validation/test_port_birdcage_ring_matrix.py`` and is not touched
here.

Needs the complex DolfinX build. Run it through the example runner, which
sources complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:12 -n 4 -t 600

Outputs
``paraview_output/ports_12_birdcage_ring_quarter_turn_combined.xdmf`` — the
mesh, ``CellTags``, the 32 sheet facet tags (as ``mesh_tags``) and **two**
distinctly named DG0 arrays, ``E_magnitude_P17`` and ``E_magnitude_P21``, so
ParaView's *Transform* filter (rotate 90 deg about ``z``) can overlay one on
the other.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import fem

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gate's constants, helpers and construction can be imported rather than
# restated (the `ANS-1` rule).
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel  # noqa: E402

from tests.validation.test_port_birdcage_ring_column import (  # noqa: E402
    AZIMUTH_MATCH_DEG,
    CELL_COUNT_BAND,
    COLUMN_PASSIVITY_CEILING,
    CONTROL_MARGIN_FACTOR,
    FREQUENCY_HZ,
    OPPOSITE_SPREAD_BAND,
    POWER_BALANCE_BAND,
    RING_LONGITUDINAL_SCALED_CELL_RECORD,
    SOLVE_PRICE_STOP_RULE_S,
    TERMINATED_PORT_IMPEDANCE_OHM,
    _build_ring_context,
    _solve_one_drive,
)
from tests.validation.test_port_birdcage_ring_matrix import AZIMUTH_STEP_DEG  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "ports_12_birdcage_ring_quarter_turn"

# `PORT-13` step 2's own recorded `P17` column passivity sum, read off its
# printed GATE (iv) line at `-n 8` (`20260904T093638Z_PORT-13.log:10797`).
# Not an importable module constant (a fixture-computed reading, printed, not
# a module-level record), so carried here as a literal, checked at rtol 1e-3
# rather than restated as if it were a closed form — the `EX-46`/`EX-47`
# precedent for a printed-not-named record.
STEP2_P17_PASSIVITY_SUM_RECORD = 0.915817419
PASSIVITY_SUM_RTOL = 1.0e-3

# Field-level ring sample (ungated, printed only): 64 points, r = 0.02 m
# (inside the phantom bore), z = 0 (the port sheet's own longitudinal
# midplane).
N_FIELD_SAMPLES = 64
FIELD_SAMPLE_RADIUS_M = 0.02
# 90 deg on a 64-point ring is exactly a 16-sample index shift.
assert N_FIELD_SAMPLES % 4 == 0
FIELD_SAMPLE_QUARTER_SHIFT = N_FIELD_SAMPLES // 4


def _same_ring(sheets, ordinal):
    """The list of sheets sharing ``ordinal``'s ring (its ``z``-centre sign)."""
    src = next(s for s in sheets if s["ordinal"] == ordinal)
    sign = src["z"] > 0.0
    return src, [s for s in sheets if (s["z"] > 0.0) == sign]


def _rotate_within_ring(sheets, ordinal, steps):
    """The ring port ``steps * AZIMUTH_STEP_DEG`` from ``ordinal``, same ring.

    Found from the **measured** sheet azimuths, never ordinal arithmetic
    (`_driven_and_opposite`/`_ring_mirror_map`'s own pattern in the gate
    module) — a port with no partner at that separation is an assertion
    failure, never a silent drop.
    """
    src, ring = _same_ring(sheets, ordinal)
    target = (src["azimuth_deg"] + steps * AZIMUTH_STEP_DEG) % 360.0
    candidates = [
        s
        for s in ring
        if abs((s["azimuth_deg"] - target + 180.0) % 360.0 - 180.0) < AZIMUTH_MATCH_DEG
    ]
    assert len(candidates) == 1, (
        f"P{ordinal} has {len(candidates)} same-ring partners at "
        f"{steps} x {AZIMUTH_STEP_DEG:.3f} deg (target {target:.3f} deg), "
        "not 1 — the rotation is off a class and must not be silently dropped"
    )
    return candidates[0]["ordinal"]


def _magnitude_field(e_complex, name):
    """DG0 ``|E|`` [V/m] over the whole domain — the honest, cell-wise
    resolution of a degree-1 curl element (`EX-26`'s convention, `EX-46`'s
    and `EX-47`'s reuse), never interpolated onto a smoother CG space than
    the discretisation supports.
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
    **one** XDMF file, through the shared ``OPS-38`` helper. Both fields
    carry distinct ``name``s (`EX-46`'s trap: one shared name and ParaView
    shows only one of the two).
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        cell_tags,
        fields,
        comm=comm,
        facet_tags=sheet_tags,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def _ring_sample_points(radius_m, n_samples):
    angles = 2.0 * np.pi * np.arange(n_samples) / n_samples
    points = np.zeros((n_samples, 3), dtype=np.float64)
    points[:, 0] = radius_m * np.cos(angles)
    points[:, 1] = radius_m * np.sin(angles)
    points[:, 2] = 0.0
    return points


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
            "EX-48 — the ring rung's quarter turn in ParaView: |E| for the "
            "P17 and P21 drives side by side and the C16 column identity",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            "\n[fixture] `PORT-13` step 3 context (`_build_ring_context`, "
            f"imported): 16-leg / 32-ring-port longitudinal rung, phantom "
            f"loaded, {FREQUENCY_HZ:.3e} Hz, degree 1, 31 ports at "
            f"Z_p = {TERMINATED_PORT_IMPEDANCE_OHM} Ohm\n"
            "[gates]   cells = RING_LONGITUDINAL_SCALED_CELL_RECORD at "
            "CELL_COUNT_BAND; column passivity <= COLUMN_PASSIVITY_CEILING; "
            "residual <= POWER_BALANCE_BAND; P17 passivity sum vs step 2's "
            "own record at rtol 1e-3; the C16 column identity |S_i,P21| vs "
            "|S_rho^-4(i),P17| <= OPPOSITE_SPREAD_BAND\n"
            "[control] the same comparison at a 3-step (67.5 deg) rotation "
            f"must miss by >= {CONTROL_MARGIN_FACTOR:.0f}x the band",
            flush=True,
        )

    built = _build_ring_context()
    ctx = built["ctx"]
    sheets = built["sheets"]
    driven, driven_id = built["driven"], built["driven_id"]

    cell_ratio = built["cells"] / RING_LONGITUDINAL_SCALED_CELL_RECORD
    if comm.rank == 0:
        print(
            f"\n[mesh] {built['cells']} cells (record "
            f"{RING_LONGITUDINAL_SCALED_CELL_RECORD}, ratio {cell_ratio:.6f})",
            flush=True,
        )
    assert abs(cell_ratio - 1.0) < CELL_COUNT_BAND, (
        f"the rung meshed {built['cells']} cells against "
        f"RING_LONGITUDINAL_SCALED_CELL_RECORD "
        f"{RING_LONGITUDINAL_SCALED_CELL_RECORD} (ratio {cell_ratio:.6f}) — "
        "this is not the fixture `PORT-13` gates"
    )

    # ---- locate P21: P17's same-ring 4-step (90 deg) rotation partner -------
    rotated_ordinal = _rotate_within_ring(sheets, driven, 4)
    rotated_id = f"P{rotated_ordinal}"
    if comm.rank == 0:
        print(
            f"\n[located] {driven_id}'s same-ring 4-step "
            f"({4 * AZIMUTH_STEP_DEG:.3f} deg) rotation partner, found by "
            f"measured azimuth (AZIMUTH_MATCH_DEG = {AZIMUTH_MATCH_DEG:.0e}): "
            f"{rotated_id}",
            flush=True,
        )

    # ---- the two drives -----------------------------------------------------
    comm.Barrier()
    col_p17 = _solve_one_drive(ctx, driven_id)
    col_p21 = _solve_one_drive(ctx, rotated_id)
    two_drive_total = col_p17["solve_time"] + col_p21["solve_time"]
    if comm.rank == 0:
        print(
            f"\n[solve] two drives over the one mesh: {driven_id} "
            f"{col_p17['solve_time']:.2f} s, {rotated_id} "
            f"{col_p21['solve_time']:.2f} s wall at -n {comm.size} (stop "
            f"rule {SOLVE_PRICE_STOP_RULE_S:.0f} s; total "
            f"{two_drive_total:.2f} s)",
            flush=True,
        )

    columns = {driven_id: col_p17, rotated_id: col_p21}

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
            "(§7 `EX-48` negative result: example/test divergence, "
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
            "port-normalisation defect, not a tolerance (§7 `EX-48` "
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
        "`EX-48` negative result: example/test divergence, known-issues "
        "entry, stop; never re-record from the example side)"
    )

    # ---- gate: the C16 column identity, with the wrong-rotation control ------
    ring_ports = sorted({s["ordinal"] for s in sheets})

    def _class_mismatches(steps):
        rows = []
        for i in ring_ports:
            partner = _rotate_within_ring(sheets, i, -steps)
            a = abs(col_p21["s_column"][f"P{i}"])
            b = abs(col_p17["s_column"][f"P{partner}"])
            rel = abs(a - b) / a if a else float("inf")
            rows.append((i, partner, a, b, rel))
        return rows

    rows = _class_mismatches(4)
    worst = max(rows, key=lambda r: r[4])
    if comm.rank == 0:
        print(
            f"\n[gate] the C16 column identity, |S_i,{rotated_id}| vs "
            f"|S_rho^-4(i),{driven_id}| over all {len(rows)} ring ports "
            f"(band {OPPOSITE_SPREAD_BAND * 100:.0f}%, imported, unmoved):",
            flush=True,
        )
        print(
            f"    worst: i=P{worst[0]}, rho^-4(i)=P{worst[1]}  "
            f"|S_P{worst[0]},{rotated_id}| = {worst[2]:.9e}  "
            f"|S_P{worst[1]},{driven_id}| = {worst[3]:.9e}  rel "
            f"{worst[4] * 100:.4f}%  "
            f"{'INSIDE' if worst[4] <= OPPOSITE_SPREAD_BAND else 'MISS'}",
            flush=True,
        )
    assert len(rows) == 32
    assert worst[4] <= OPPOSITE_SPREAD_BAND, (
        f"the C16 identity misses worst at i=P{worst[0]}: "
        f"|S_P{worst[0]},{rotated_id}| = {worst[2]:.9e} against "
        f"|S_P{worst[1]},{driven_id}| = {worst[3]:.9e}, {worst[4] * 100:.4f}% "
        f"apart against the unmoved {OPPOSITE_SPREAD_BAND * 100:.0f}% band "
        "(§7 `EX-48` negative result: example/test divergence, "
        "known-issues entry, stop; never re-record from the example side)"
    )

    # ---- negative control: a 3-step (67.5 deg) wrong rotation ----------------
    control_rows = _class_mismatches(3)
    control_worst = max(control_rows, key=lambda r: r[4])
    control_factor = control_worst[4] / OPPOSITE_SPREAD_BAND
    if comm.rank == 0:
        print(
            f"\n[control] the same comparison at a 3-step (67.5 deg) wrong "
            f"rotation — pairs each port against a partner one class off "
            f"from the true 4-step separation:",
            flush=True,
        )
        print(
            f"    worst: i=P{control_worst[0]}, rho^-3(i)=P{control_worst[1]}  "
            f"rel {control_worst[4] * 100:.4f}%  "
            f"({control_factor:.3f}x the band, bar "
            f"{CONTROL_MARGIN_FACTOR:.0f}x, none larger claimed than what is "
            "computed)",
            flush=True,
        )
    assert control_worst[4] >= CONTROL_MARGIN_FACTOR * OPPOSITE_SPREAD_BAND, (
        f"the 3-step wrong rotation moves the worst mismatch only to "
        f"{control_worst[4]:.6e} ({control_factor:.3f}x the band), under "
        f"the {CONTROL_MARGIN_FACTOR:.0f}x bar — the control failed to "
        "separate (§7 `EX-48` negative result: known-issues entry, stop)"
    )

    # ---- ungated: |E| on a 64-point ring, printed only -----------------------
    points = _ring_sample_points(FIELD_SAMPLE_RADIUS_M, N_FIELD_SAMPLES)
    e17_vals, e17_valid = evaluate_vector_field_parallel(
        col_p17["fields"].e_complex, points, comm=comm
    )
    e21_vals, e21_valid = evaluate_vector_field_parallel(
        col_p21["fields"].e_complex, points, comm=comm
    )
    mag17 = np.linalg.norm(e17_vals, axis=1).real
    mag21 = np.linalg.norm(e21_vals, axis=1).real
    valid = e17_valid & e21_valid
    # P21 is P17 rotated by +4 steps (+90 deg); its field pattern should read
    # like P17's own pattern rotated the same way — sample k of P21 lines up
    # with sample (k - 16) mod 64 of P17.
    mag17_rotated = np.roll(mag17, FIELD_SAMPLE_QUARTER_SHIFT)
    valid_rotated = np.roll(valid, FIELD_SAMPLE_QUARTER_SHIFT)
    both_valid = valid & valid_rotated
    n_valid = int(both_valid.sum())
    if n_valid > 0:
        diffs = np.abs(mag21[both_valid] - mag17_rotated[both_valid])
        denom = np.abs(mag17_rotated[both_valid])
        denom = np.where(denom > 0.0, denom, np.nan)
        rel = diffs / denom
        rms_rel = float(np.sqrt(np.nanmean(rel**2)))
        worst_rel = float(np.nanmax(rel))
    else:
        rms_rel = float("nan")
        worst_rel = float("nan")
    if comm.rank == 0:
        print(
            f"\n[ungated] |E| on a {N_FIELD_SAMPLES}-point ring "
            f"(r = {FIELD_SAMPLE_RADIUS_M} m, z = 0), {rotated_id} samples "
            f"vs {driven_id} samples rotated 90 deg "
            f"({FIELD_SAMPLE_QUARTER_SHIFT}-sample index shift), "
            f"{n_valid}/{N_FIELD_SAMPLES} points valid on both sides: "
            f"RMS relative difference {rms_rel * 100:.4f}%, worst "
            f"{worst_rel * 100:.4f}%. No band: at CG1 on this mesh a rotated "
            f"discrete field is not exactly the discrete rotated field "
            "(`WF-6` step 1's C4 field identities on the 4-leg mesh read "
            "~2% for the same reason) — printed for inspection only, never "
            "asserted.",
            flush=True,
        )

    # ---- the deliverable: |E|_P17 and |E|_P21 in ParaView --------------------
    e_p17 = _magnitude_field(col_p17["fields"].e_complex, "E_magnitude_P17")
    e_p21 = _magnitude_field(col_p21["fields"].e_complex, "E_magnitude_P21")
    written = _write_combined(
        ctx["msh"],
        ctx["cell_tags"],
        ctx["tags_f"],
        {"E_magnitude_P17": e_p17, "E_magnitude_P21": e_p21},
        comm,
    )

    if comm.rank == 0:
        print(f"\n[paraview] wrote {written}")
        print(
            "\n[paraview] threshold `CellTags` (1 conductor, 2 air, 3 "
            "phantom, 101-116 the sixteen uncut leg boxes, 117-148/217-248 "
            "the inner/outer halves of the 32 ring-port boxes) or the "
            "`mesh_tags` facet array for the 32 reconstructed longitudinal "
            f"sheets. Colour by `E_magnitude_P17` and `E_magnitude_P21` "
            f"(both DG0, V/m, distinct names) — apply ParaView's *Transform* "
            "filter, rotate 90 deg about `z`, to one of the two arrays and "
            "it overlays onto the other.",
            flush=True,
        )
        print(
            f"\nAll gates hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
