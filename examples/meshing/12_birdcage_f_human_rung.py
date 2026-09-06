"""Example (`EX-51`): the F-human birdcage — 16 legs, 32 ring ports, in ParaView.

`GEO-25` step 2 (`tests/validation/test_birdcage_f_human_rung.py`) gates the
30 cm-coil (0.15 m `ring_radius`) rung of the `GEO-25` ladder: the 16-leg,
high-pass (both-end-ring) layout at human scale. Two branches are built from
the same imported ``_params(F_HUMAN_RING_RADIUS, scale_sizing=...)``:

* **branch B** (``scale_sizing=False``): the mesh sizing stays at `mesh:9`'s
  0.015 m absolute value while only the geometry grows — the fixture. Its
  cell count (504 642) is a new version-tagged record, and its meshed/CAD
  conductor mass recovery clears the imported `CAD_MASS_GATE`.
* **branch A** (``scale_sizing=True``): the mesh sizing scales with the
  radius too, so every rung is geometrically similar — the negative control.
  Step 1 measured its conductor mass falling to 0.893028, *below* the same
  gate: at 0.15 m the conductor's 1.6 mm graded region is swamped by a global
  element size that grew 2.14x. This is the finding that fixed absolute
  sizing, not similar-mesh scaling, is the right choice for this generator at
  human scale.

**It asserts, it does not merely render** (the `ANS-1` rule): every anchor
below is imported from the gate module and read off *this run's own mesh*,
never restated.

* branch-B cell count against `F_HUMAN_BRANCH_B_CELL_RECORD` (504 642) at
  `CELL_COUNT_BAND`;
* `GEO-18` volume partition (tagged volumes sum to the air box) at `EXACT`;
* `GEO-19` terminal-area ratio, all 32 ring ports, inside `TERMINAL_RATIO_BAND`;
* meshed/CAD conductor mass >= `CAD_MASS_GATE` (record 0.965414).

**Negative control, asserted:** branch A's conductor mass ratio falls below
`CAD_MASS_GATE` while branch B's clears it — the two-sided separation
`control["cad_ratio"] < CAD_MASS_GATE <= fixture["cad_ratio"]`, backed by the
gate module's own measurement of the same comparison on the same rungs
(`20260905T183654Z_GEO-25.log:20024-20027`).

**Scope: a mesh, not a solve.** No field, no port gate, no physics claim, no
Phase 6 cost claim. `GEO-25` step 2's own bands are unmoved by this example.

Run it through the example runner::

    ./run_examples.sh -e mesh:12 -n 2 -t 600

Output lands in ``examples/meshing/paraview_output/``: open
``meshing_12_birdcage_f_human_rung_combined.xdmf`` (branch B, the fixture,
only — the branch-A control mesh is not written to disk) and threshold on
``CellTags`` (1 = conductor, 2 = air, 3 = phantom, 101-116 the sixteen
uncut leg boxes, 117-148 / 217-248 the lower/upper halves of the 32 ring
gap boxes), or on the DG0 ``cell_diameter`` field for a per-cell mesh-size
picture; the same file's facet block carries ``mesh_tags`` 227-258, the 32
reconstructed ring sheets.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path
# so the gate's constants, helpers and assertions can be imported rather than
# restated (the `ANS-1` rule).
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.mesh import _interface_facet_tags  # noqa: E402
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)

from tests.mesh.test_birdcage_port_sheets import (  # noqa: E402
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
)
from tests.validation.test_birdcage_f_human_rung import (  # noqa: E402
    CAD_MASS_GATE,
    CELL_COUNT_BAND,
    EXACT,
    F_HUMAN_BRANCH_A_CELL_RECORD,
    F_HUMAN_BRANCH_B_CELL_RECORD,
    F_HUMAN_RING_RADIUS,
    LEG_COUNT,
    STEP1_BRANCH_A_CAD_RATIO,
    STEP1_BRANCH_B_CAD_RATIO,
    TERMINAL_RATIO_BAND,
    _build_rung,
    _ring_ports,
)

CELL_TAG_NAMES = {1: "conductor", 2: "air", 3: "phantom"}

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "meshing_12_birdcage_f_human_rung"


def _cell_diameter_function(mesh):
    """Per-cell max vertex-to-vertex distance as a DG0 ``cell_diameter`` field.

    Same construction as `cell_tags_to_function` (DG0, one dof per cell via
    the dofmap, not the cell index) so the array lands as an ordinary cell
    array on the same grid the ``CellTags`` array uses — a distinct ``name``
    so ParaView shows both.
    """
    import dolfinx.cpp.mesh as cpp_mesh
    from dolfinx import fem

    tdim = mesh.topology.dim
    imap = mesh.topology.index_map(tdim)
    n_local = imap.size_local + imap.num_ghosts
    cells = np.arange(n_local, dtype=np.int32)
    h = cpp_mesh.h(mesh._cpp_object, tdim, cells)

    v0 = fem.functionspace(mesh, ("DG", 0))
    diam = fem.Function(v0, name="cell_diameter")
    cell_dofs = v0.dofmap.list.reshape(-1)
    diam.x.array[cell_dofs[cells]] = h
    diam.x.scatter_forward()
    return diam


def _write_combined(mesh, cell_tags, sheet_tags, comm):
    OUTPUT_DIR.mkdir(exist_ok=True)
    diam = _cell_diameter_function(mesh)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        mesh,
        cell_tags,
        {"cell_diameter": diam},
        comm=comm,
        facet_tags=sheet_tags,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if comm.rank == 0:
        print("=" * 72)
        print("EX-51 — the F-human birdcage: 16 legs, 32 ring ports, at 0.15 m")
        print("=" * 72)
        print(
            f"\n[geometry] leg_count={LEG_COUNT}  ring_radius={F_HUMAN_RING_RADIUS} m"
            "\n[branches] B: scale_sizing=False (fixed absolute sizing, the "
            "fixture)"
            "\n           A: scale_sizing=True  (mesh sizing scales with radius "
            "too, the CONTROL)"
            f"\n[gate]     cell record (band {CELL_COUNT_BAND}), GEO-18 volume "
            f"partition (band {EXACT}),"
            f"\n           GEO-19 terminal ratio band {TERMINAL_RATIO_BAND} on all "
            f"{2 * LEG_COUNT} ring ports, CAD mass gate {CAD_MASS_GATE}"
            "\n[scope]    mesh only: no solve, no port model, no drive, no "
            "resonance, no Phase 6 cost claim",
            flush=True,
        )

    # ---- branch B: fixed absolute sizing, the fixture — mesh kept for export
    fixture = _build_rung(F_HUMAN_RING_RADIUS, scale_sizing=False, keep_mesh=True)
    # ---- branch A: mesh sizing scaled too, the negative control ------------
    control = _build_rung(F_HUMAN_RING_RADIUS, scale_sizing=True, keep_mesh=False)

    if comm.rank == 0:
        ratios = fixture["terminal_ratios"]
        print(
            f"\n[branch B — fixed absolute sizing, the fixture]"
            f"\n  cells                 {fixture['n_cells']} vs record "
            f"{F_HUMAN_BRANCH_B_CELL_RECORD}  relative "
            f"{fixture['n_cells'] / F_HUMAN_BRANCH_B_CELL_RECORD - 1.0:.3e}  "
            f"(band {CELL_COUNT_BAND})"
            f"\n  volume partition      {fixture['partition']:.12f}  (band "
            f"{EXACT})"
            f"\n  terminal ratio        min {ratios.min():.9f}  max "
            f"{ratios.max():.9f}  n_ports {len(ratios)}  (band "
            f"{TERMINAL_RATIO_BAND})"
            f"\n  meshed/CAD conductor  {fixture['cad_ratio']:.6f}  (step 1 "
            f"printed {STEP1_BRANCH_B_CAD_RATIO:.6f}; gate {CAD_MASS_GATE})",
            flush=True,
        )
        cratios = control["terminal_ratios"]
        print(
            f"\n[branch A — mesh sizing scaled, the CONTROL]"
            f"\n  cells                 {control['n_cells']} vs record "
            f"{F_HUMAN_BRANCH_A_CELL_RECORD}  relative "
            f"{control['n_cells'] / F_HUMAN_BRANCH_A_CELL_RECORD - 1.0:.3e}  "
            f"(band {CELL_COUNT_BAND})"
            f"\n  volume partition      {control['partition']:.12f}  (band "
            f"{EXACT})"
            f"\n  terminal ratio        min {cratios.min():.9f}  max "
            f"{cratios.max():.9f}  n_ports {len(cratios)}  (band "
            f"{TERMINAL_RATIO_BAND})"
            f"\n  meshed/CAD conductor  {control['cad_ratio']:.6f}  (step 1 "
            f"printed {STEP1_BRANCH_A_CAD_RATIO:.6f}; gate {CAD_MASS_GATE})",
            flush=True,
        )
        print(
            f"\n[EX-51 separation] fixed absolute sizing vs similar-mesh scaling "
            f"at ring_radius = {F_HUMAN_RING_RADIUS:.3f} m:"
            f"\n  control  (branch A) meshed/CAD {control['cad_ratio']:.6f}  "
            f"{CAD_MASS_GATE - control['cad_ratio']:.6f} BELOW the "
            f"{CAD_MASS_GATE} gate"
            f"\n  fixture  (branch B) meshed/CAD {fixture['cad_ratio']:.6f}  "
            f"{fixture['cad_ratio'] - CAD_MASS_GATE:.6f} ABOVE it"
            f"\n  separation          "
            f"{fixture['cad_ratio'] - control['cad_ratio']:.6f}",
            flush=True,
        )

    # ---- the gates, imported (`GEO-25` step 2's own asserts) ---------------
    assert (
        abs(fixture["n_cells"] / F_HUMAN_BRANCH_B_CELL_RECORD - 1.0) < CELL_COUNT_BAND
    ), (
        f"branch-B F-human rung meshes {fixture['n_cells']} cells against the "
        f"{F_HUMAN_BRANCH_B_CELL_RECORD} record (band {CELL_COUNT_BAND})"
    )
    assert abs(fixture["partition"] - 1.0) < EXACT, (
        f"branch-B F-human rung: tagged volumes sum to "
        f"{fixture['partition']:.12f} of the mesh volume (band {EXACT})"
    )
    ratios = fixture["terminal_ratios"]
    lo, hi = TERMINAL_RATIO_BAND
    assert len(ratios) == 2 * LEG_COUNT, (
        f"expected {2 * LEG_COUNT} ring ports, read {len(ratios)}"
    )
    assert ratios.min() >= lo and ratios.max() <= hi, (
        f"branch-B F-human rung: terminal-area ratios span "
        f"[{ratios.min():.9f}, {ratios.max():.9f}] outside [{lo}, {hi}]"
    )
    assert fixture["cad_ratio"] >= CAD_MASS_GATE, (
        f"branch-B F-human rung keeps only {fixture['cad_ratio']:.6f} of the "
        f"conductor's CAD mass, below the {CAD_MASS_GATE} gate"
    )

    # The control's own record, control-only.
    assert (
        abs(control["n_cells"] / F_HUMAN_BRANCH_A_CELL_RECORD - 1.0) < CELL_COUNT_BAND
    ), (
        f"branch-A F-human control meshes {control['n_cells']} cells against "
        f"the {F_HUMAN_BRANCH_A_CELL_RECORD} record (band {CELL_COUNT_BAND})"
    )

    # The negative control, asserted (not just printed) — a two-sided
    # separation, backed by the gate module's own measurement of the same
    # comparison on the same rungs (`20260905T183654Z_GEO-25.log:20024-20027`).
    assert control["cad_ratio"] < CAD_MASS_GATE <= fixture["cad_ratio"], (
        f"the F-human conductor-mass separation collapsed: branch-A control "
        f"{control['cad_ratio']:.6f}, gate {CAD_MASS_GATE}, branch-B fixture "
        f"{fixture['cad_ratio']:.6f}"
    )

    # ---- ParaView: the fixture (branch B) mesh only -------------------------
    ring_ports = fixture["ring_ports"]
    assert ring_ports == _ring_ports(), (
        "the fixture's own ring-port ids disagree with `_ring_ports()` — a "
        "wiring defect in this example, not a mesh finding"
    )
    sheet_tags = _interface_facet_tags(
        fixture["mesh"],
        fixture["cell_tags"],
        {SHEET_IFACE + i: (PORT_LOWER + i, PORT_UPPER + i) for i in ring_ports},
    )
    written = _write_combined(fixture["mesh"], fixture["cell_tags"], sheet_tags, comm)

    if comm.rank == 0:
        print(f"\n[paraview] wrote branch-B (fixture) mesh only: {written}")
        print(
            "\n[paraview] threshold `CellTags` in the _combined file "
            f"({', '.join(f'{t} = {n}' for t, n in CELL_TAG_NAMES.items())}, "
            f"101-{100 + LEG_COUNT} = the sixteen UNCUT leg boxes,"
            f"\n           {100 + LEG_COUNT + 1}-{100 + 3 * LEG_COUNT} / "
            f"{200 + LEG_COUNT + 1}-{200 + 3 * LEG_COUNT} = the lower/upper "
            "halves of the 32 ring gap boxes), or the DG0 `cell_diameter` "
            "field for a per-cell mesh-size picture;"
            f"\n           the same file's facet block carries `mesh_tags` "
            f"{210 + LEG_COUNT + 1}-{210 + 3 * LEG_COUNT} for the 32 "
            "reconstructed ring sheets. The branch-A control mesh is not "
            "written to disk."
            f"\n\nAll branch-B anchors hold at {LEG_COUNT} legs / "
            f"{2 * LEG_COUNT} ring ports; the branch-A control separates "
            "below the same gate. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
