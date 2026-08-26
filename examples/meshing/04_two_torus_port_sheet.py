"""Example (`EX-23`): the gap boxes' port-sheet mid-plane, meshed and tagged.

The first example in this repo showing an **interior sheet surface**. Example
`mesh:1` shows the gapped two-torus and `mesh:3` the graded birdcage; neither
shows the geometry `GEO-16` gated — a surface *inside* the volume, whose facet
tags are not a dim-2 gmsh physical group at all but are rebuilt on the dolfinx
side from the cell tags either side of it (the known-issues-9 pattern that
`PORT-9` step 1's lumped port now builds on).

**What the surface is for.** A lumped-element port sheet spans terminal to
terminal with the port current flowing *in* its plane, so ``R = Z_p · w / h``
is written for a surface containing the current direction. The fixture's
existing port facets ``201`` / ``202`` are the gap↔conductor cross-sections —
*normal* to that current, the wrong constitutive law. Passing
``emit_port_sheet=True`` fragments each gap box with its own mid-plane
``z = ±separation/2``, so the tet mesh conforms to the surface the port BC
needs, and each gap volume becomes **two** cell groups (``101``+``111``,
``102``+``112``).

**It asserts, it does not merely render.** Both identities are `GEO-16`'s own,
re-executed here on the example's own mesh:

* the reconstructed facet set's MPI-reduced ``dS`` area equals the CAD
  mid-plane area ``(2·gap_half_xz)·(2·gap_half_y)`` to ``AREA_IDENTITY_BAND``
  (1e-9) on **both** sheets. A plane section has no curvature to inscribe, so
  a linear-tet triangulation of it is exact — this is an identity, not a band.
  On record: ``1.000000000000``.
* the two sheets, built from the same solid mirrored in ``z``, have equal
  areas to ``1e-12``.

Each facet group is asserted **non-empty first**: a reconstruction matching
zero facets would otherwise pass the area identity vacuously at 0 == 0.

**Negative control — the kwarg-off mesh, asserted to lack the sheet.** With
``emit_port_sheet=False`` the mesh must bit-match its record: 79 070 cells,
cell tags ``{1, 2, 3, 101, 102}``, facet tags ``{1, 201, 202}``, and **no**
``21x`` group anywhere (the `EX-18` / `EX-21` inverted-assertion pattern).
Every gated `PORT-1` / `PORT-10` number was measured on that mesh, so the
opt-in sheet may not perturb it.

**Printed, never gated:** the measured sheet extents — transverse width ``w``,
length ``h`` along the current direction, and ``w/h``, the "number of squares"
a port impedance converts through. The gap box crosses a round arc, so these
are measured rather than nominal quantities. On this fixture's
parameterisation ``w/h = 1.504225878``; the `PORT-9` solve fixture is
parameterised differently (``w/h = 0.745249896``) and belongs to that chunk.

Every constant is **imported** from `tests/mesh/test_two_torus_port_sheet.py`
and the `GEO-16` module it imports in turn (the `ANS-1` rule); nothing is
restated, so this example cannot drift from the gate it demonstrates.

**Mesh only — no port, no solve, no `Z` claim.** `PORT-9` is 🟡
(PROJECT_PLAN.md §2); this script needs only the real DolfinX build.

Run it through the example runner::

    ./run_examples.sh -e mesh:4

Output lands in ``examples/meshing/paraview_output/``: open
``two_torus_port_sheet_combined.xdmf`` and threshold on ``CellTags``
(1 = wire 1, 2 = wire 2, 3 = air, 101/111 and 102/112 = the two halves of each
gap box), and ``two_torus_port_sheet_facets.xdmf`` alongside it for the facet
groups — the array is ``mesh_tags`` (1 = outer boundary, 201/202 = the port
cuts, **211/212 = the port sheets**).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from mpi4py import MPI

from dolfinx import io

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gate's constants and helpers can be imported rather than restated.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)

from tests.mesh.test_two_torus_port_facets import (  # noqa: E402
    AIR_PADDING,
    GAP_ANGLE,
    GAP_CLEARANCE,
    MAJOR_RADIUS,
    MINOR_RADIUS,
    PORT_FACET_TAGS,
    RESOLUTION,
    SEPARATION,
    WIRE_RESOLUTION,
    _facet_group_area,
    _gap_half_xz,
    _gap_half_y,
    _global_facet_tag_set,
)
from tests.mesh.test_two_torus_port_sheet import (  # noqa: E402
    AREA_IDENTITY_BAND,
    GAP_CELL_TAGS_WITH_SHEET,
    NCELLS_UNGATED_RECORD,
    SHEET_FACET_TAGS,
    _global_cell_tag_set,
    _mesh,
    _sheet_extents,
    _sheet_facet_count,
)

CELL_TAG_NAMES = {
    1: "wire 1 (z<0)",
    2: "wire 2 (z>0)",
    3: "air",
    101: "gap 1 lower",
    111: "gap 1 upper",
    102: "gap 2 lower",
    112: "gap 2 upper",
}
FACET_TAG_NAMES = {
    1: "outer_boundary",
    201: "port cut 1",
    202: "port cut 2",
    211: "port sheet 1",
    212: "port sheet 2",
}

# The two sheets are the same solid mirrored in z; `GEO-16` gates their equality
# at this band.
SHEET_SYMMETRY_BAND = 1.0e-12

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "two_torus_port_sheet"


def _write_paraview(msh, cell_tags, facet_tags, comm):
    """Mesh + cell tags in one file, mesh + facet tags in a second.

    Cell tags ride as a DG0 ``CellTags`` array on the *cell* grid. Facet tags
    live on the tdim-1 topology and cannot share that grid, so they go to their
    own file (the `EX-1` pattern) — which is where 211/212 become visible.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    written = {}

    cells_xdmf, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined", msh, cell_tags, {}, comm=comm
    )
    if cells_xdmf is not None:
        written["cell tags"] = cells_xdmf

    facets_path = OUTPUT_DIR / f"{BASENAME}_facets.xdmf"
    msh.topology.create_connectivity(msh.topology.dim - 1, msh.topology.dim)
    with io.XDMFFile(comm, facets_path, "w") as xdmf:
        xdmf.write_mesh(msh)
        xdmf.write_meshtags(facet_tags, msh.geometry)
    if comm.rank == 0:
        written["facet tags"] = facets_path

    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return written


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if comm.rank == 0:
        print("=" * 72)
        print("EX-23 — two-torus port sheet: the gap-box mid-plane, meshed")
        print("=" * 72)
        print(
            f"\n[geometry] separation={SEPARATION} m  R={MAJOR_RADIUS} m  "
            f"r={MINOR_RADIUS} m  air_padding={AIR_PADDING} m"
            f"\n[geometry] port_gap=True  gap_angle={GAP_ANGLE} rad  "
            f"gap_clearance={GAP_CLEARANCE} m"
            f"\n[mesh]     resolution={RESOLUTION} m  "
            f"wire_resolution={WIRE_RESOLUTION} m; emit_port_sheet=True"
            f"\n[gate]     both sheets meshed/CAD = 1 to "
            f"{AREA_IDENTITY_BAND:.0e}; kwarg-off control asserted to LACK the "
            "sheet",
            flush=True,
        )

    # ---- the sheet mesh ---------------------------------------------------
    msh, cell_tags, facet_tags = _mesh(comm, emit_port_sheet=True)
    assert cell_tags is not None, "model_to_mesh returned no cell tags"
    assert facet_tags is not None, "model_to_mesh returned no facet tags"
    mesh_seconds = time.perf_counter() - started

    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    n_cells = msh.topology.index_map(tdim).size_global

    cell_tag_set = _global_cell_tag_set(cell_tags, comm)
    facet_tag_set = _global_facet_tag_set(msh, facet_tags, comm)

    assert cell_tag_set == {1, 2, 3, *GAP_CELL_TAGS_WITH_SHEET}, (
        "the sheet path must split each gap box into two cell groups; found "
        f"{sorted(cell_tag_set)}"
    )
    assert set(SHEET_FACET_TAGS) <= facet_tag_set, (
        f"sheet facet tags missing; found {sorted(facet_tag_set)}"
    )
    assert set(PORT_FACET_TAGS) <= facet_tag_set, (
        f"the sheet path dropped the port facet groups; found "
        f"{sorted(facet_tag_set)}"
    )

    # Non-empty BEFORE any area is divided by anything: 0 == 0 is not an
    # identity, and a reconstruction matching no facet would pass vacuously.
    counts = {t: _sheet_facet_count(msh, facet_tags, t, comm) for t in SHEET_FACET_TAGS}
    for tag, n in counts.items():
        assert n > 0, (
            f"sheet facet group {tag} is empty; the area identity below would "
            "have passed vacuously"
        )

    a_cad = 4.0 * _gap_half_xz() * _gap_half_y()
    areas = {t: _facet_group_area(msh, facet_tags, t, comm) for t in SHEET_FACET_TAGS}
    extents = {t: _sheet_extents(msh, facet_tags, t, comm) for t in SHEET_FACET_TAGS}
    port_areas = {t: _facet_group_area(msh, facet_tags, t, comm) for t in PORT_FACET_TAGS}

    if comm.rank == 0:
        print(f"\n[mesh] {n_cells} cells built in {mesh_seconds:.1f} s")
        print("[tags] cell groups:  " + ", ".join(
            f"{t} = {CELL_TAG_NAMES.get(t, '?')}" for t in sorted(cell_tag_set)))
        print("[tags] facet groups: " + ", ".join(
            f"{t} = {FACET_TAG_NAMES.get(t, '?')}" for t in sorted(facet_tag_set)))
        print(
            f"\n[GEO-16] CAD mid-plane area={a_cad:.12e} m^2 "
            f"(nominal {2 * _gap_half_xz():.6e} x {2 * _gap_half_y():.6e} m)",
            flush=True,
        )
        for tag in SHEET_FACET_TAGS:
            w, h, dz = extents[tag]
            print(
                f"[GEO-16] sheet {tag}: {counts[tag]} facets "
                f"area={areas[tag]:.12e} m^2 "
                f"meshed/CAD={areas[tag] / a_cad:.12f} "
                f"| measured w={w:.9e} h={h:.9e} m, w/h={w / h:.9f} squares, "
                f"area/(w*h)={areas[tag] / (w * h):.9f}, out-of-plane "
                f"spread={dz:.3e} m"
            )
        for tag in PORT_FACET_TAGS:
            print(f"[GEO-16] port {tag} area (unmoved check) "
                  f"{port_areas[tag]:.9e} m^2", flush=True)

    for tag in SHEET_FACET_TAGS:
        rel = abs(areas[tag] - a_cad) / a_cad
        assert rel < AREA_IDENTITY_BAND, (
            f"sheet facet group {tag} area {areas[tag]:.12e} m^2 differs from "
            f"the CAD mid-plane {a_cad:.12e} m^2 by {rel:.3e} relative, outside "
            f"{AREA_IDENTITY_BAND:.0e} — a regression against the `GEO-16` gate; "
            "record it in the EX-23 entry rather than moving the band"
        )

    sheet_symmetry = abs(areas[SHEET_FACET_TAGS[0]] / areas[SHEET_FACET_TAGS[1]] - 1.0)
    assert sheet_symmetry < SHEET_SYMMETRY_BAND, (
        f"sheet areas differ by {sheet_symmetry:.3e} relative: "
        f"{areas[SHEET_FACET_TAGS[0]]:.12e} vs {areas[SHEET_FACET_TAGS[1]]:.12e} — "
        "the two sheets are the same solid mirrored in z"
    )

    # ---- negative control: the kwarg-off mesh, asserted to LACK the sheet --
    control_started = time.perf_counter()
    msh_off, cell_tags_off, facet_tags_off = _mesh(comm, emit_port_sheet=False)
    control_seconds = time.perf_counter() - control_started

    n_cells_off = msh_off.topology.index_map(msh_off.topology.dim).size_global
    cell_tag_set_off = _global_cell_tag_set(cell_tags_off, comm)
    facet_tag_set_off = _global_facet_tag_set(msh_off, facet_tags_off, comm)

    if comm.rank == 0:
        print(
            f"\n[control] emit_port_sheet=False: {n_cells_off} cells in "
            f"{control_seconds:.1f} s (record {NCELLS_UNGATED_RECORD})"
            f"\n[control] cell tags {sorted(cell_tag_set_off)}  "
            f"facet tags {sorted(facet_tag_set_off)}"
            f"\n[control] sheet tags present: "
            f"{sorted(set(SHEET_FACET_TAGS) & facet_tag_set_off)} "
            "(inverted assertion — the control must LACK them)",
            flush=True,
        )

    assert not (set(SHEET_FACET_TAGS) & facet_tag_set_off), (
        "the default path emitted sheet facet tags: the sheet is opt-in, and a "
        "control that already carries it would make the identities above say "
        "nothing about the kwarg"
    )
    assert cell_tag_set_off == {1, 2, 3, 101, 102}, (
        f"the default path changed its cell-tag set: {sorted(cell_tag_set_off)}"
    )
    assert facet_tag_set_off == {1, *PORT_FACET_TAGS}, (
        f"the default path changed its facet-tag set: {sorted(facet_tag_set_off)}"
    )
    assert n_cells_off == NCELLS_UNGATED_RECORD, (
        f"the default path meshed {n_cells_off} cells against the recorded "
        f"{NCELLS_UNGATED_RECORD}: the opt-in sheet perturbed the mesh every "
        "gated PORT-1 / PORT-10 number was measured on"
    )

    # ---- ParaView ---------------------------------------------------------
    written = _write_paraview(msh, cell_tags, facet_tags, comm)
    if comm.rank == 0:
        print("\n[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<11s} {path}")
        print(
            "\n[paraview] threshold `CellTags` in the _combined file "
            "(1/2 wire, 3 air, 101/111 and 102/112 the two halves of each gap "
            "box);"
            "\n           open the _facets file for `mesh_tags` — 211/212 are "
            "the port sheets,"
            "\n           the interior surface this example exists to show."
            f"\n\nAll identities hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
