"""Example (`EX-61`): the tuned birdcage's resonance curve.

``ports:17`` (`EX-58`) shows the tuned state at one frequency; no example in
the corpus shows a frequency *response*. `PORT-22` step 1 (audited PASS
2026-09-21) built exactly that: on the 116 085-cell gate mesh, degree 1,
``-n 2``, at each of 11 grid frequencies 44-84 MHz in 4 MHz steps, a fixed
physical capacitor ``C_tuned`` (found once at 64 MHz by `PORT-15` step 3,
never re-fit per frequency) is placed in P2..P4 and the untuned matched 4x4
circuit reduction is checked against one in-model driven solve.

This example runs a **six-point** sub-window of that grid -- 52, 56, 60, 64,
68, 72 MHz -- and asserts exactly what `PORT-22` step 1 asserts, on those six
points. **It imports, and restates nothing** (the `ANS-1` rule): every
fixture, ``C_tuned``, band and helper comes from
``tests/validation/test_port22_driven_sweep_resonance.py``.

**Rule (a) additive lift, disclosed.** The gate module's ``c_tuned`` and
``window`` pytest fixtures were pytest-only (module-scoped fixtures cannot be
called from a plain script). Their bodies are lifted verbatim to two new
module-level functions -- ``build_c_tuned()`` and
``run_window(frequencies_mhz, c_f)`` -- with the fixtures reduced to thin
wrappers that resolve the env-var frequency list and delegate. No existing
test's behaviour changed; the gate module was re-run green from `main` in
this slot (see the guide's harness log for the rerun window).

**What runs.** ``build_c_tuned()`` reproduces `PORT-15` step 3's ``C_tuned``
on the stored 64 MHz record (the same call the gate module's own fixture
makes). ``run_window(FREQUENCIES_MHZ, c_tuned["c_f"])`` builds the gate mesh
once and, at each of the six frequencies, derives kappa in-run
(`PORT-14` step 3's route), builds the kappa-corrected untuned 4x4, and drives
the in-model tuned 1-port network at the fixed ``C_tuned`` -- the identical
construction `PORT-22` step 1 runs, just six of its eleven points.

**Anchors (asserted, all imported):**

* at 64 MHz, the tuned S11 residual (circuit-reduced vs in-model) is
  ``<= REDUCTION_BAND`` -- `PORT-22` step 1 anchor (i), reproducing `PORT-15`
  step 3;
* at **every** one of the six frequencies, the same residual is
  ``<= REDUCTION_BAND`` -- anchor (ii)'s family, on this sub-window;
* ``Im Z_in(f)`` (read off the in-model tuned S11) changes sign **exactly
  once** across the six points, in the bracket holding 64 MHz -- anchor
  (iii), on six points rather than eleven (64 MHz is a member of both grids,
  so the bracket is the same bracket);
* the negative control: the circuit prediction built with
  ``0.5 x C_tuned`` misses the in-model tuned curve at 64 MHz by more than
  ``CONTROL_MISS_FACTOR`` x ``REDUCTION_BAND`` (asserted, backed by
  `PORT-15` step 3's measured 0.846 vs 0.761 -- the same comparison on the
  same fixture).

**Printed, never gated:** the interpolated zero ``f0`` of ``Im Z_in``,
``R_in(f0)`` and the loaded Q from the ``Im Z`` slope there -- the same
formula `PORT-22` step 1's anchor (iii) prints.

**Not claimed:** any absolute S11 / Z_in figure (known-issues 2026-09-19,
`PORT-21`) -- every anchor here is a circuit-layer vs field-solve *identity*
on one mesh; no mode-spectrum claim (`TH-17` owns that); no match.

Needs the complex DolfinX build; the runner sources it for the ``ports:``
group automatically::

    ./run_examples.sh -e ports:19 -t 600

**Outputs** (``paraview_output/``, full filenames -- census references them
this way, never a stem):

* ``ports_19_birdcage_tuned_resonance_curve_rin_xin.csv`` -- ``R_in``,
  ``X_in`` vs frequency, six rows;
* ``ports_19_birdcage_tuned_resonance_curve_rin_xin.png`` -- the same data
  plotted, ``f0`` marked;
* ``ports_19_birdcage_tuned_resonance_curve_combined.xdmf`` (+ ``.h5``) --
  ``|E|`` (DG0) on the phantom at the 64 MHz tuned drive, plus ``CellTags``.

Setup figure per `EX-57` in ``figures/ports_19_birdcage_tuned_resonance_curve_setup.png``.
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    cell_tags_to_function,
)
from fem_em_solver.post.setup_figure import write_setup_figure  # noqa: E402

from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE  # noqa: E402
from tests.validation.test_port22_driven_sweep_resonance import (  # noqa: E402
    CONTROL_C_FACTOR,
    CONTROL_MISS_FACTOR,
    RECORD_RANK_WIDTH,
    REDUCTION_BAND,
    STEP1_CELL_RECORD,
    STEP3_REGISTERED_FREQUENCY_HZ,
    _capacitor_impedance,
    _z_in,
    build_c_tuned,
    build_four_port_sweep,
    run_window,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)
from tests.validation.test_port_circuit_layer_field import (  # noqa: E402
    TUNING_TERMINATED_INDICES,
    terminated_kept_network,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
FIGURE_DIR = Path(__file__).resolve().parent / "figures"
BASENAME = "ports_19_birdcage_tuned_resonance_curve"

# Six of `PORT-22` step 1's eleven grid points -- 52..72 MHz in 4 MHz steps,
# 64 MHz included (the bracket the sign-change anchor needs).
FREQUENCIES_MHZ = (52.0, 56.0, 60.0, 64.0, 68.0, 72.0)

_TERMINATED = tuple(int(k) for k in TUNING_TERMINATED_INDICES)


def _magnitude_field(e_complex, name):
    """DG0 ``|E|`` [V/m], real, the degree-1 curl element's honest resolution
    (`EX-26`'s convention; duplicated boilerplate, the corpus's own pattern --
    `EX-58`/`EX-59`/`ports:10-12` each carry the identical helper)."""
    msh = e_complex.function_space.mesh
    import ufl

    dg0 = fem.functionspace(msh, ("DG", 0))
    expr_ufl = ufl.sqrt(ufl.inner(e_complex, e_complex))
    expr = fem.Expression(expr_ufl, dg0.element.interpolation_points)
    field = fem.Function(dg0, name=name)
    field.interpolate(expr)
    out = fem.Function(dg0, name=name)
    out.x.array[:] = np.real(field.x.array)
    out.x.scatter_forward()
    return out


def _write_combined_xdmf(msh, cell_tags, field, comm):
    from dolfinx import io

    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{BASENAME}_combined.xdmf"
    with io.XDMFFile(comm, path, "w") as xdmf:
        xdmf.write_mesh(msh)
        xdmf.write_function(cell_tags_to_function(msh, cell_tags))
        xdmf.write_function(field, t=0.0)
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path if comm.rank == 0 else None


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ports:` group)."
        )

    record_width = comm.size == RECORD_RANK_WIDTH

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            "EX-61 -- the tuned birdcage's resonance curve: R_in(f), X_in(f), "
            "f0 and loaded Q",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            f"\n[gate import] build_c_tuned, run_window, REDUCTION_BAND, "
            f"CONTROL_MISS_FACTOR, CONTROL_C_FACTOR from "
            f"tests/validation/test_port22_driven_sweep_resonance.py "
            f"(rule (a) additive lift, disclosed above); -n {comm.size} "
            f"({'RECORD WIDTH' if record_width else 'not the record width'})",
            flush=True,
        )

    # ---- C_tuned, the gate module's own recomputation ---------------------
    c_tuned = build_c_tuned()
    c_f = float(c_tuned["c_f"])

    # ---- the six-point window ----------------------------------------------
    window = run_window(FREQUENCIES_MHZ, c_f)
    assert window["cells"] == STEP1_CELL_RECORD, (
        f"{window['cells']} cells, record {STEP1_CELL_RECORD} -- not the gate mesh"
    )
    rows = window["rows"]

    mhz_64 = STEP3_REGISTERED_FREQUENCY_HZ / 1.0e6
    row64 = rows[mhz_64]

    if comm.rank == 0:
        z64 = _z_in(complex(*row64["s11_in_model"]))
        print(
            f"\n[anchor i] 64 MHz tuned S11 residual {row64['residual']:.6e} "
            f"({'ASSERTED' if record_width else 'PRINTED, not asserted at this width'}"
            f" <= REDUCTION_BAND {REDUCTION_BAND:.0e}); Z_in = {z64.real:+.9e} "
            f"{z64.imag:+.9e}j Ohm",
            flush=True,
        )
    if record_width:
        assert row64["residual"] <= REDUCTION_BAND, (
            f"64 MHz tuned S11 residual {row64['residual']:.6e} > "
            f"{REDUCTION_BAND:.0e} -- known-issues, stop, never re-band"
        )

    mhz_sorted = sorted(rows)
    worst = max(rows.values(), key=lambda r: r["residual"])
    if comm.rank == 0:
        print(
            f"\n[anchor ii] circuit-vs-field residual, six points "
            f"(ASSERTED <= REDUCTION_BAND {REDUCTION_BAND:.0e} at every point):",
            flush=True,
        )
        for m in mhz_sorted:
            r = rows[m]
            print(
                f"    {m:5.1f} MHz  residual {r['residual']:.6e}  "
                f"({r['residual'] / REDUCTION_BAND:.4f} x band)",
                flush=True,
            )
    if record_width:
        assert worst["residual"] <= REDUCTION_BAND, (
            f"{worst['frequency_mhz']:.0f} MHz: residual {worst['residual']:.6e} > "
            f"{REDUCTION_BAND:.0e} -- known-issues, stop, never re-band"
        )

    floor = CONTROL_MISS_FACTOR * REDUCTION_BAND
    if comm.rank == 0:
        print(
            f"\n[negative control] 64 MHz, {CONTROL_C_FACTOR:g} x C_tuned "
            f"(ASSERTED miss > {CONTROL_MISS_FACTOR:g} x band = {floor:.0e}): "
            f"miss {row64['control_miss']:.6e} "
            f"({row64['control_miss'] / REDUCTION_BAND:.3f} x band)",
            flush=True,
        )
    if record_width:
        assert row64["control_miss"] > floor, (
            f"0.5 x C_tuned misses by only {row64['control_miss']:.6e}, under {floor:.0e}"
        )

    # ---- sign change of Im Z_in on the six-point grid ----------------------
    mhz_arr = np.array(mhz_sorted, dtype=float)
    z_arr = np.array([complex(*rows[m]["z_in_model"]) for m in mhz_sorted])
    im, re = z_arr.imag, z_arr.real
    brackets = [
        i for i in range(len(mhz_arr) - 1) if np.sign(im[i]) != np.sign(im[i + 1])
    ]
    if comm.rank == 0:
        print(
            "\n[anchor iii] Z_in(f) from the in-model tuned drive (ASSERTED: "
            "exactly one sign change of Im Z_in, in the bracket holding 64 MHz):",
            flush=True,
        )
        for i, m in enumerate(mhz_arr):
            print(
                f"    {m:5.1f} MHz  Z_in = {re[i]:+.9e} {im[i]:+.9e}j Ohm  "
                f"|S11| = {abs(complex(*rows[m]['s11_in_model'])):.9f}",
                flush=True,
            )
    if record_width:
        assert len(brackets) == 1, (
            f"Im Z_in changes sign {len(brackets)} times on the six-point grid "
            f"(brackets at {[(mhz_arr[i], mhz_arr[i + 1]) for i in brackets]}) -- "
            "report, never re-grid"
        )
        i = brackets[0]
        assert mhz_arr[i] <= 64.0 <= mhz_arr[i + 1], (
            f"the single sign change is in [{mhz_arr[i]:.0f}, {mhz_arr[i + 1]:.0f}] "
            "MHz, not the bracket containing 64 MHz"
        )
    else:
        i = brackets[0] if len(brackets) == 1 else 2  # fallback index, unused for gating

    # PRINTED, never gated -- same formula as the gate module's anchor (iii).
    slope = (im[i + 1] - im[i]) / (mhz_arr[i + 1] - mhz_arr[i])
    f0 = mhz_arr[i] - im[i] / slope
    r0 = re[i] + (re[i + 1] - re[i]) * (f0 - mhz_arr[i]) / (mhz_arr[i + 1] - mhz_arr[i])
    q = 0.5 * f0 * slope / r0 if r0 != 0.0 else float("nan")
    if comm.rank == 0:
        print(
            f"    single sign change in [{mhz_arr[i]:.0f}, {mhz_arr[i + 1]:.0f}] MHz "
            f"(ASSERTED, the 64 MHz bracket)\n"
            f"    PRINTED, never gated: interpolated zero f0 = {f0:.6f} MHz; "
            f"R_in(f0) = {r0:.6f} Ohm; loaded Q = (f0/2R) dX/df = {q:.4f}\n"
            "    one fixture, degree 1, series resonance -- no absolute S11 claim "
            "(known-issues 2026-09-19, `PORT-21`), no mode-spectrum claim (`TH-17`)",
            flush=True,
        )

    # ---- CSV + PNG of R_in / X_in vs f -------------------------------------
    if comm.rank == 0:
        OUTPUT_DIR.mkdir(exist_ok=True)
        csv_path = OUTPUT_DIR / f"{BASENAME}_rin_xin.csv"
        with open(csv_path, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["frequency_mhz", "r_in_ohm", "x_in_ohm"])
            for i2, m in enumerate(mhz_arr):
                writer.writerow([f"{m:.1f}", f"{re[i2]:.9e}", f"{im[i2]:.9e}"])
        adopt_host_ownership(OUTPUT_DIR, comm=comm)

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax1 = plt.subplots(figsize=(7, 4.5))
        ax1.plot(mhz_arr, re, "o-", color="tab:red", label="R_in")
        ax1.set_xlabel("frequency [MHz]")
        ax1.set_ylabel("R_in [Ohm]", color="tab:red")
        ax1.tick_params(axis="y", labelcolor="tab:red")
        ax2 = ax1.twinx()
        ax2.plot(mhz_arr, im, "s-", color="tab:blue", label="X_in")
        ax2.axhline(0.0, color="gray", linewidth=0.5)
        ax2.set_ylabel("X_in [Ohm]", color="tab:blue")
        ax2.tick_params(axis="y", labelcolor="tab:blue")
        ax2.axvline(f0, color="black", linestyle="--", linewidth=0.8)
        ax1.set_title(
            "ports:19 -- tuned birdcage R_in/X_in(f); f0 (dashed) = "
            f"{f0:.3f} MHz, Q = {q:.3f}"
        )
        fig.tight_layout()
        png_path = OUTPUT_DIR / f"{BASENAME}_rin_xin.png"
        fig.savefig(png_path, dpi=150)
        plt.close(fig)
        adopt_host_ownership(OUTPUT_DIR, comm=comm)
        print(f"\n[csv/png] {csv_path}\n[csv/png] {png_path}", flush=True)

    # ---- 64 MHz tuned field, for the combined XDMF + setup figure ---------
    kappa_64 = float(row64["kappa"])
    built_64 = build_four_port_sweep(
        frequency_hz=STEP3_REGISTERED_FREQUENCY_HZ,
        width_correction_kappa=kappa_64,
        build_only=True,
    )
    z_c_64 = _capacitor_impedance(STEP3_REGISTERED_FREQUENCY_HZ, c_f)
    t0 = time.perf_counter()
    s_tuned, fields_tuned = terminated_kept_network(
        built_64, {k: z_c_64 for k in _TERMINATED}, return_fields=True
    )
    field_time = time.perf_counter() - t0
    p1_id = built_64["port_defs"][0].port_id
    e_tuned = _magnitude_field(fields_tuned[p1_id].e_complex, "E_magnitude")
    if comm.rank == 0:
        print(
            f"\n[field] 64 MHz tuned drive for the combined XDMF: {field_time:.2f} s; "
            f"|S11| {abs(s_tuned[0, 0]):.9f} (consistent with anchor i above)",
            flush=True,
        )

    region_names = {CONDUCTOR_CELL_TAG: "conductor", PHANTOM_CELL_TAG: "phantom"}
    for s in built_64["sheets"]:
        region_names[int(s["tag"])] = f"port {s['tag'] - SHEET_IFACE}"
    write_setup_figure(
        built_64["mesh"],
        built_64["cell_tags"],
        FIGURE_DIR / f"{BASENAME}_setup.png",
        region_names=region_names,
        translucent_tags=(PHANTOM_CELL_TAG,),
        slice_normal=(0.0, 0.0, 1.0),
        title="ports:19 -- tuned birdcage resonance curve (P1 driven, P2..P4 at C_tuned)",
        comm=comm,
    )

    path = _write_combined_xdmf(built_64["mesh"], built_64["cell_tags"], e_tuned, comm)

    if comm.rank == 0:
        print(
            f"\n[paraview] {path} -- E_magnitude at the 64 MHz tuned drive, plus "
            "CellTags."
            f"\n\nAll asserted anchors hold at record width. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
