"""Example (`EX-58`): the tuned birdcage — sweep, ``C_tuned``, the in-model field.

`PORT-15` step 3 (closed 2026-09-14) found the capacitor value that zeroes
``Im Z_in`` on the stored 64 MHz ε = 0 4×4 (`PORT-14`'s κ-corrected width) —
P1 driven at 50 Ω, P2..P4 terminated in a series capacitor — and confirmed
the circuit-predicted tuned S against **one** in-model solve at that
capacitance. `ports:3` (`EX-24`) already shows lumped sheets, but nothing in
the example corpus terminates a port in a capacitor or tunes one; this is
that example.

**It asserts, and it does not re-implement** (the `ANS-1` rule, `EX-32`/
`EX-33`'s precedent). ``S_64MHZ_EPS0_RECORD``, ``tuning_sweep``,
``select_c_tuned``, ``tuned_input``, ``TUNING_IM_Z_RTOL`` and
``REDUCTION_BAND`` (re-exported from `PORT-14`'s module) are imported
verbatim from ``tests/validation/test_port_circuit_layer_field.py``
(`PORT-15` step 3's gate module) — never copied.

**Rule (a) additive lift, disclosed.** The gate module's
``step3_in_model`` fixture body and ``_terminated_kept_network`` were
module-private (a pytest fixture and an underscore helper). Two additive
changes make them importable, with no existing test's behaviour changed:

1. ``step3_in_model``'s body is lifted to a new module-level function
   ``build_step3_in_model(tuned, frequency_hz)``; the fixture itself now
   only unwraps ``step3_tuning`` and delegates to it.
2. ``_terminated_kept_network`` gained an additive ``return_fields=False``
   parameter (default off, bit-for-bit the old behaviour for every existing
   caller) that, when ``True``, also returns ``{port_id: fields}`` from
   ``run_lumped_sheet_port_case``'s own ``return_fields`` option — so a
   consumer can get the solved ``E`` field, not just the reduced S. A public
   alias ``terminated_kept_network`` is added (the name itself stayed
   private for the gate module's own callers).

The gate module (``tests/validation/test_port_circuit_layer_field.py``) was
re-run green from `main` in this slot after both changes — see the guide's
harness log for the rerun window.

**What runs.** ``tuning_sweep`` on the imported ``S_64MHZ_EPS0_RECORD`` at
`PORT-15`'s registered 64 MHz finds the sign changes of ``Im Z_in(C)``
(P1 driven, P2..P4 in series C, 50 Ω reference) and ``select_c_tuned`` picks
the lowest-|S11| zero. ``build_step3_in_model`` then builds the κ-corrected
mesh once (`PORT-14` step 3's opt-in width) and drives it in-model at
``C_tuned`` for the 1×1 (P1 kept) and 2×2 (P1, P2 kept) reduced networks —
the identical construction the gate's own ``step3_in_model`` fixture runs.
Beside that, ``terminated_kept_network`` is called twice more directly, both
with ``return_fields=True`` and P1 the only kept (driven) port: once at
``C_tuned`` on P2..P4, once at the plain 50 Ω baseline (P2..P4 pinned to the
reference impedance explicitly — numerically identical to the untouched
sweep, the same helper, so the two field solves are the same construction
apart from the one impedance value) — one field for each of the guide's two
XDMF time steps.

**Anchors (asserted):**

* the sweep's ``Im Z_in(C_tuned)`` — ``|Im Z_in|/|Z_in| <= TUNING_IM_Z_RTOL``
  (1e-6), pure numpy on the stored record;
* the in-model tuned ``S11`` residual against the circuit-predicted value
  (``tuned_input`` on the same stored 4×4) — ``<= REDUCTION_BAND`` (1e-3),
  **only at this runner's record width `-n 2`**; at any other width the
  residual is printed with the width disclosed and not asserted (the gate
  module's own rule, `PORT-15` step 3(b)).

**Printed, never asserted:** ``|S11|`` at 0.5× and 2× ``C_tuned`` (predicted
above the tuned value); the ladder closed form's mode-1 frequency read off
the de-embedded self/mutual reactances (indicative only, leg-gap fixture vs
ring-capacitor ladder — the gate module's own caveat).

**Negative result (§7's own clause, unchanged here):** a red imported band
⇒ known-issues naming this example, stop; never re-band or widen the grid
in-slot.

**Scope.** A series resonance on one fixture, `-n 2`, 64 MHz. No match, no
mode-frequency claim, no Larmor-accuracy claim, no AED comparison.

Needs the complex DolfinX build; the runner sources it for the ``ports:``
group automatically::

    ./run_examples.sh -e ports:17 -t 600

Outputs one ``…_combined.xdmf`` in ``paraview_output/`` carrying ``|E|``
(DG0) on the phantom as **two time steps of the same file** (same mesh, so —
unlike `EX-56`'s two-resolution ladder — one combined file is feasible):
``t=0`` the 50 Ω baseline, ``t=1`` the ``C_tuned`` drive. Step between the
two time steps with a common colour range to see the tuned drive redistribute
the field.
"""

from __future__ import annotations

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
    consolidate_xdmf_grids,
)
from fem_em_solver.post.setup_figure import write_setup_figure  # noqa: E402

from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE  # noqa: E402
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)
from tests.validation.test_port_circuit_layer_field import (  # noqa: E402
    REDUCTION_BAND,
    S_64MHZ_EPS0_RECORD,
    STEP3_REGISTERED_FREQUENCY_HZ,
    TUNING_2X2_TERMINATED_INDICES,
    TUNING_CONTROL_FACTORS,
    TUNING_IM_Z_RTOL,
    TUNING_TERMINATED_INDICES,
    _capacitor_impedance,
    _residual,
    build_step3_in_model,
    select_c_tuned,
    terminated_kept_network,
    tuned_input,
    tuning_sweep,
)
from tests.validation.test_port_package_sparameters import (  # noqa: E402
    REFERENCE_IMPEDANCE_OHM,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
FIGURE_DIR = Path(__file__).resolve().parent / "figures"
BASENAME = "ports_17_birdcage_tuned_circuit"


def _magnitude_field(e_complex, name):
    """DG0 ``|E|`` [V/m], real, the degree-1 curl element's honest resolution
    (`EX-26`'s convention)."""
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


def _write_two_time_steps(msh, cell_tags, baseline_field, tuned_field, comm):
    """One combined XDMF, ``E_magnitude`` at ``t=0`` (baseline) and ``t=1``
    (``C_tuned``), plus ``CellTags`` (untimed). Written directly with
    ``dolfinx.io.XDMFFile`` rather than through ``write_xdmf_with_tags``:
    that helper's ``consolidate_xdmf_grids`` step explicitly collapses time
    collections (single-timestep files only, per its own docstring), which
    would destroy the very thing this file needs to carry.
    """
    from dolfinx import io

    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{BASENAME}_combined.xdmf"
    with io.XDMFFile(comm, path, "w") as xdmf:
        xdmf.write_mesh(msh)
        xdmf.write_function(cell_tags_to_function(msh, cell_tags))
        baseline_field.name = "E_magnitude"
        xdmf.write_function(baseline_field, t=0.0)
        tuned_field.name = "E_magnitude"
        xdmf.write_function(tuned_field, t=1.0)
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

    record_width = comm.size == 2

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print("EX-58 -- the tuned birdcage: sweep, C_tuned, the in-model field", flush=True)
        print("=" * 78, flush=True)
        print(
            f"\n[gate import] S_64MHZ_EPS0_RECORD, tuning_sweep, select_c_tuned, "
            f"tuned_input, TUNING_IM_Z_RTOL, REDUCTION_BAND from "
            f"tests/validation/test_port_circuit_layer_field.py; -n {comm.size} "
            f"({'RECORD WIDTH' if record_width else 'not the record width -- '
               'the S11 residual is printed, not asserted'})",
            flush=True,
        )

    # ---- (a) the sweep on the stored record ------------------------------
    f = STEP3_REGISTERED_FREQUENCY_HZ
    grid, values, roots = tuning_sweep(S_64MHZ_EPS0_RECORD, f)
    tuned = select_c_tuned(roots)
    if comm.rank == 0:
        print(
            f"\n[sweep] Im Z_in(C) on S_64MHZ_EPS0_RECORD at {f:.3e} Hz, P1 driven "
            f"(50 Ohm), P2..P4 in C, grid {grid[0]:.1e}..{grid[-1]:.1e} F "
            f"({grid.size} pts): {len(roots)} sign change(s)",
            flush=True,
        )
        for r in roots:
            print(
                f"    C = {r['c_f']:.15e} F  Z_in = {r['z'].real:+.9e} "
                f"{r['z'].imag:+.9e}j Ohm  |S11| = {abs(r['s11']):.9f}  "
                f"|Im Z|/|Z| = {r['im_rel']:.3e}  "
                f"{'ZERO' if r['zero'] else 'pole (rejected)'}",
                flush=True,
            )
    assert tuned is not None, (
        "no zero of Im Z_in on the imported grid -- report, never widen in-slot"
    )
    rel = tuned["im_rel"]
    s11_t = abs(tuned["s11"])
    controls = []
    for factor in TUNING_CONTROL_FACTORS:
        _, s_red = tuned_input(S_64MHZ_EPS0_RECORD, f, factor * tuned["c_f"])
        controls.append((factor, abs(complex(s_red[0, 0]))))
    if comm.rank == 0:
        print(
            f"\n[sweep] C_tuned = {tuned['c_f']:.15e} F: |Im Z_in|/|Z_in| = {rel:.3e} "
            f"(ASSERTED <= TUNING_IM_Z_RTOL {TUNING_IM_Z_RTOL:.0e}); "
            f"Z_in = {tuned['z']:.9e} Ohm; S11 = {tuned['s11']:.9e}, |S11| = {s11_t:.9f}",
            flush=True,
        )
        for factor, s in controls:
            print(
                f"    control {factor:g} x C_tuned: |S11| = {s:.9f} "
                f"(PREDICTED > |S11(C_tuned)| {s11_t:.9f}: "
                f"{'held' if s > s11_t else 'NOT held'}; printed, never asserted)",
                flush=True,
            )
    assert rel <= TUNING_IM_Z_RTOL, f"|Im Z|/|Z| = {rel:.3e} > {TUNING_IM_Z_RTOL:.0e}"

    # ---- one in-model 64 MHz solve at C_tuned -----------------------------
    in_model = build_step3_in_model(tuned, f)
    built = in_model["built"]
    _, pred1 = tuned_input(S_64MHZ_EPS0_RECORD, f, tuned["c_f"])
    _, pred2 = tuned_input(
        S_64MHZ_EPS0_RECORD, f, tuned["c_f"], terminated=TUNING_2X2_TERMINATED_INDICES
    )
    meas1, meas2 = in_model["s1"], in_model["s2"]
    r1, r2 = _residual(meas1, pred1), _residual(meas2, pred2)
    if comm.rank == 0:
        print(
            f"\n[in-model] C_tuned = {tuned['c_f']:.15e} F, {in_model['cells']} cells, "
            f"-n {comm.size}",
            flush=True,
        )
        print(
            f"    S11  predicted {complex(pred1[0, 0]):.12e}  "
            f"in-model {complex(meas1[0, 0]):.12e}  residual {r1:.6e} "
            f"({'ASSERTED' if record_width else 'PRINTED, not asserted at this width'} "
            f"<= REDUCTION_BAND {REDUCTION_BAND:.0e})",
            flush=True,
        )
        print(f"    2x2 residual {r2:.6e}", flush=True)
    if record_width:
        assert r1 <= REDUCTION_BAND, (
            f"tuned S11 residual {r1:.6e} > {REDUCTION_BAND:.0e} at record width "
            "-n 2 -- known-issues, stop, never re-band"
        )
        assert r2 <= REDUCTION_BAND, (
            f"tuned 2x2 residual {r2:.6e} > {REDUCTION_BAND:.0e} at record width "
            "-n 2 -- known-issues, stop, never re-band"
        )

    # ---- the two |E| fields: 50 Ohm baseline vs C_tuned, P1 driven -------
    z0 = float(REFERENCE_IMPEDANCE_OHM)
    z_c = _capacitor_impedance(f, tuned["c_f"])
    t0 = time.perf_counter()
    s_base, fields_base = terminated_kept_network(
        built, {k: z0 for k in TUNING_TERMINATED_INDICES}, return_fields=True
    )
    s_tuned, fields_tuned = terminated_kept_network(
        built, {k: z_c for k in TUNING_TERMINATED_INDICES}, return_fields=True
    )
    field_time = time.perf_counter() - t0
    p1_id = built["port_defs"][0].port_id
    e_base = _magnitude_field(fields_base[p1_id].e_complex, "E_magnitude_baseline")
    e_tuned = _magnitude_field(fields_tuned[p1_id].e_complex, "E_magnitude_tuned")
    if comm.rank == 0:
        print(
            f"\n[field] two P1-driven solves (50 Ohm baseline, C_tuned) for the "
            f"|E| XDMF time steps: {field_time:.2f} s; baseline |S11| "
            f"{abs(s_base[0, 0]):.9f}, tuned |S11| {abs(s_tuned[0, 0]):.9f}",
            flush=True,
        )

    # ---- setup figure (EX-57), on the built mesh --------------------------
    region_names = {CONDUCTOR_CELL_TAG: "conductor", PHANTOM_CELL_TAG: "phantom"}
    for s in built["sheets"]:
        region_names[int(s["tag"])] = f"port {s['tag'] - SHEET_IFACE}"
    write_setup_figure(
        built["mesh"],
        built["cell_tags"],
        FIGURE_DIR / f"{BASENAME}_setup.png",
        region_names=region_names,
        translucent_tags=(PHANTOM_CELL_TAG,),
        slice_normal=(0.0, 0.0, 1.0),
        title="ports:17 -- the tuned birdcage (C_tuned at P2..P4, P1 driven)",
        comm=comm,
    )

    path = _write_two_time_steps(
        built["mesh"], built["cell_tags"], e_base, e_tuned, comm
    )

    if comm.rank == 0:
        print(
            f"\n[paraview] {path} -- E_magnitude, two time steps (t=0 the 50 Ohm "
            "baseline, t=1 C_tuned), plus CellTags; step between them with a "
            "common colour range."
            f"\n\nAll asserted anchors hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
