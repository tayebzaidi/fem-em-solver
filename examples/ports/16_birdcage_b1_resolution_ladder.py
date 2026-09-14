"""Example (`EX-56`): the ``|B₁⁺|`` spread against resolution, two rungs in ParaView.

`WF-6` step 5 (2026-09-13, gated in
``tests/validation/test_birdcage_b1_plus_closed_form.py``) asked whether the
FEM ``|B₁⁺|``'s C4 four-copy spread on the *unloaded* F-small birdcage falls
with the mesh, and registered the answer as a **convergence statement**: the
worst-radius spread at global sizing ×1 (5.2506%) and ×0.012 (2.0719%), the
fall asserted monotone. No example has ever put a resolution ladder into
ParaView — every prior ladder in ``examples/ports/`` (`ports:5`, `ports:8`)
climbs *frequency*, not mesh size — and nobody opens a test module to see the
field this statement is about.

**It asserts, and it does not re-implement** (the `ANS-1` rule, `EX-32`/
`EX-33`'s precedent). ``LADDER``, ``STEP5_RECORDED_SPREADS`` and
``STEP5_SPREAD_RTOL`` are imported from the gate module verbatim, and so is
every helper the rung construction needs (``_master_points``,
``_read_b1_plus``, ``_radial_spreads``, ``_interior_cv``,
``_filament_interior_cv``, ``VACUUM``) — the gate module already exposes all
of it at module scope, so no lift was needed. The quadrature machinery
(``_port_index``, ``_superpose_dg0``, ``quadrature_phase_weights``,
``QUADRATURE_STEP_DEG``) comes from ``test_birdcage_b1_quadrature.py``, the
same module the gate itself imports it from, and ``_solve_driven`` /
``build_four_port_sweep`` come from their own owning modules — the identical
import set the gate module uses to build one rung.

**What runs.** For each of the gate's two trustworthy ``LADDER`` rungs (×1 at
global ``resolution`` 0.015 m / 116 085 cells, ×0.012 at 0.012 m / 149 049
cells; the ×0.0095 rung stays off — its power residual is a banked
known-issues negative, `WF-6` step 4f), ``build_four_port_sweep`` builds the
**unloaded** (vacuum-phantom) fixture at that resolution, all four ports are
driven singly, and the ccw quadrature superposition of the four DG0 ``B``
fields is projected to CG1 — the identical construction the gate's ``rung``
fixture runs, called here as a plain function rather than through pytest.

**Anchors (asserted):**

* **the fall** — ``STEP5_RECORDED_SPREADS``' worst-radius C4 four-copy spread
  of the ccw ``|B₁⁺|`` falls monotonically, ``spread(×0.012) <
  spread(×1)`` — the convergence statement itself, `WF-6` step 5 anchor (ii);
* **the records** — reproduced at the gate's own ``STEP5_SPREAD_RTOL``
  (1e-3) **only when this example runs at the gate's record width, `-n 4`**;
  at any other width (including this runner's default `-n 2`, which the gate
  module's own docstring says carries 1e-4-class MUMPS drift on this
  fixture) the two spreads are printed with the width disclosed and only the
  fall above is asserted.

**Printed, never asserted (the gate module's own rule (e) practice):** the
21-point interior CV of ``|B₁⁺|`` on both rungs, beside the free-space
filament closed form's CV on the same 21 points (`_filament_interior_cv`,
step 4a's function, no shield — context, never a comparand, since the FEM
domain is shielded and the filament is not).

**Negative result (§7's own clause, unchanged here):** if the fall is not
observed, that is reported to known-issues and the run stops — no band
widens, no rung is added or dropped to make it pass.

**Scope.** A convergence statement on one unloaded F-small fixture at
10 MHz, CG1, degree 1. No closed-form, homogeneity, C95.3, Larmor or
absolute-accuracy claim.

Needs the complex DolfinX build; the runner sources it for the ``ports:``
group automatically::

    ./run_examples.sh -e ports:16 -t 900

Outputs one ``…_x1_combined.xdmf`` and one ``…_x0p012_combined.xdmf`` in
``paraview_output/`` — **a deviation from the item's "one combined XDMF with
the rung as the time step"**, recorded in this slot's report: the two rungs
mesh at different resolutions (116 085 vs 149 049 cells), so their fields do
not share one topology, and this example writes the two established,
already-tested single-mesh combined files (`EX-40`'s pattern) rather than
risk an unverified multi-mesh temporal-grid write inside the compute window.
Each carries the ccw ``|B₁⁺|`` (CG1) and ``CellTags``; step between the two
files with a common colour range to see the ladder converge.
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
    write_xdmf_with_tags,
)
from fem_em_solver.post import (  # noqa: E402
    magnetic_flux_density_from_e,
    project_to_cg1,
)
from fem_em_solver.post.setup_figure import write_setup_figure  # noqa: E402

from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE  # noqa: E402
from tests.validation.test_birdcage_b1_plus_closed_form import (  # noqa: E402
    LADDER,
    STEP5_RECORDED_SPREADS,
    STEP5_SPREAD_RTOL,
    VACUUM,
    _filament_interior_cv,
    _interior_cv,
    _master_points,
    _radial_spreads,
    _read_b1_plus,
)
from tests.validation.test_birdcage_b1_plus_map import _solve_driven  # noqa: E402
from tests.validation.test_birdcage_b1_quadrature import (  # noqa: E402
    QUADRATURE_STEP_DEG,
    _port_index,
    _superpose_dg0,
    quadrature_phase_weights,
)
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    build_four_port_sweep,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
FIGURE_DIR = Path(__file__).resolve().parent / "figures"
BASENAME = "ports_16_birdcage_b1_resolution_ladder"


def _build_rung(spec, comm):
    """One ``LADDER`` rung: the gate's own ``rung`` fixture, called directly.

    Mirrors ``tests/validation/test_birdcage_b1_plus_closed_form.py``'s
    ``rung`` fixture body exactly (unloaded phantom, four single drives, ccw
    quadrature superposition, CG1 projection, master-lattice read, radial
    spreads) using only that module's own imported helpers — nothing here is
    a restatement of its logic, only a non-pytest call of it.
    """
    sweep = build_four_port_sweep(
        phantom_material=VACUUM, resolution=spec["resolution"]
    )
    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    order = sorted(azimuths)
    indices = {
        pid: _port_index(azimuths[pid], azimuths["P1"], QUADRATURE_STEP_DEG)
        for pid in order
    }
    assert sorted(indices.values()) == [0, 1, 2, 3], (
        f"[{spec['key']}] the four sheets do not occupy the four quadrature "
        f"slots: {indices}"
    )

    t0 = time.perf_counter()
    solves = {pid: _solve_driven(sweep, pid) for pid in order}
    solve_time = time.perf_counter() - t0
    b_dg0 = [
        magnetic_flux_density_from_e(
            solves[pid]["fields"].e_complex, solves[pid]["omega"]
        )
        for pid in order
    ]
    ks = np.array([indices[pid] for pid in order], dtype=float)
    weights = quadrature_phase_weights(ks, "ccw")
    cg1_ccw = project_to_cg1(
        _superpose_dg0(b_dg0, weights, f"B_{spec['key']}_ccw"),
        name=f"B_{spec['key']}_ccw_cg1",
    )

    points = _master_points()
    ccw, valid = _read_b1_plus(cg1_ccw, points)
    assert bool(valid.all()), (
        f"[{spec['key']}] not every one of the {points.shape[0]} master-lattice "
        "points evaluated on the ccw map — the spread/CV below would be a "
        "silently reduced sample"
    )
    ccw_spreads = _radial_spreads(ccw)
    worst_radius = int(np.argmax(ccw_spreads))

    return {
        "spec": spec,
        "sweep": sweep,
        "cells": int(sweep["cells"]),
        "cg1_ccw": cg1_ccw,
        "ccw": ccw,
        "worst_spread": float(ccw_spreads[worst_radius]),
        "worst_radius": worst_radius,
        "interior_cv": _interior_cv(ccw),
        "solve_time": solve_time,
    }


def _b1_plus_cg1_real(projected, name):
    """``|B_x + jB_y|/2`` at the CG1 nodes, as a real ``fem.Function`` for XDMF."""
    space = projected.function_space
    scalar = fem.functionspace(space.mesh, ("Lagrange", 1))
    out = fem.Function(scalar, name=name)
    components = np.asarray(projected.x.array).reshape(-1, 3)
    out.x.array[:] = np.abs(components[:, 0] + 1j * components[:, 1]) / 2.0
    out.x.scatter_forward()
    return out


def _write_combined(stem, msh, cell_tags, field, comm):
    OUTPUT_DIR.mkdir(exist_ok=True)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_{stem}_combined",
        msh,
        cell_tags,
        {"B1_plus_ccw_cg1": field},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ports:` group)."
        )

    record_width = comm.size == 4

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            "EX-56 -- |B1+| spread against resolution, the two-rung ladder",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            f"\n[fixture] PORT-9's build_four_port_sweep, VACUUM phantom "
            f"(unloaded), two LADDER rungs; -n {comm.size} "
            f"({'RECORD WIDTH' if record_width else 'not the record width -- '
               'records printed, not asserted'})",
            flush=True,
        )

    filament_cv = _filament_interior_cv()

    rungs = {}
    for spec in LADDER:
        rung = _build_rung(spec, comm)
        rungs[spec["key"]] = rung
        record = STEP5_RECORDED_SPREADS.get(spec["key"])
        rel = abs(rung["worst_spread"] - record) / abs(record) if record else None
        if comm.rank == 0:
            print(
                f"\n[rung {spec['key']}] resolution {spec['resolution']} m, "
                f"{rung['cells']} cells (LADDER record {spec['cells']}), "
                f"4 solves {rung['solve_time']:.1f} s\n"
                f"    worst-radius C4 spread  {rung['worst_spread'] * 100:.4f}%  "
                f"(record {record * 100:.4f}%, relative {rel:.3e})\n"
                f"    21-pt interior CV       {rung['interior_cv'] * 100:.4f}%  "
                f"(PRINTED only, filament closed-form CV on the same points "
                f"{filament_cv * 100:.4f}%)",
                flush=True,
            )
        if record_width:
            assert rel <= STEP5_SPREAD_RTOL, (
                f"[{spec['key']}] worst-radius spread {rung['worst_spread']:.6e} "
                f"misses the gate's STEP5_RECORDED_SPREADS record {record:.6e} "
                f"by relative {rel:.3e}, outside STEP5_SPREAD_RTOL "
                f"{STEP5_SPREAD_RTOL:g} at the record width -n 4"
            )

    x1 = rungs["x1"]["worst_spread"]
    x0012 = rungs["x0.012"]["worst_spread"]
    if comm.rank == 0:
        print(
            f"\n[fall] worst-radius C4 spread: x1 {x1 * 100:.4f}% -> x0.012 "
            f"{x0012 * 100:.4f}% (ASSERTED monotone fall)",
            flush=True,
        )
    assert x0012 < x1, (
        f"the worst-radius C4 spread did not fall with resolution: x1 "
        f"{x1:.6e}, x0.012 {x0012:.6e} -- the convergence statement's negative "
        "result (§7 EX-56): report to known-issues, stop, do not widen"
    )

    # ---- setup figure (EX-57), on the x1 rung's own mesh ---------------------
    x1_sweep = rungs["x1"]["sweep"]
    region_names = {CONDUCTOR_CELL_TAG: "conductor", PHANTOM_CELL_TAG: "vacuum phantom"}
    for s in x1_sweep["sheets"]:
        region_names[int(s["tag"])] = f"port {s['tag'] - SHEET_IFACE}"
    write_setup_figure(
        x1_sweep["mesh"],
        x1_sweep["cell_tags"],
        FIGURE_DIR / f"{BASENAME}_setup.png",
        region_names=region_names,
        translucent_tags=(PHANTOM_CELL_TAG,),
        slice_normal=(0.0, 0.0, 1.0),
        title="ports:16 -- unloaded F-small birdcage, resolution ladder (x1 rung)",
        comm=comm,
    )

    written = {}
    for key, rung in rungs.items():
        # ``write_xdmf_with_tags`` applies ".xdmf" via ``Path.with_suffix``,
        # which treats everything after the *last* dot as the suffix to
        # replace -- "x0.012" would silently truncate to "x0.xdmf". The file
        # stem is therefore dot-free; the key itself (with its dot) is kept
        # as the printed label and the dict key above.
        stem = key.replace(".", "p")
        field = _b1_plus_cg1_real(rung["cg1_ccw"], f"B1_plus_ccw_cg1_{key}")
        path = _write_combined(
            stem, rung["sweep"]["mesh"], rung["sweep"]["cell_tags"], field, comm
        )
        written[key] = path

    if comm.rank == 0:
        print("\n[paraview]", flush=True)
        for key, path in written.items():
            print(f"  {key:<8s} {path}", flush=True)
        print(
            "\n[paraview] each _combined file carries B1_plus_ccw_cg1 (the "
            "production CG1 estimator) and CellTags on that rung's own mesh; "
            "step between the two files with a common colour range to see the "
            "spread narrow."
            f"\n\nAll asserted anchors hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
