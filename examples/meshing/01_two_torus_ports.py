"""Example (`EX-1`): the gapped two-torus port fixture, meshed and tagged.

Every other example in this repo shows a *solved field*. This one shows the
**geometry and its tag structure** — the thing you actually need to look at in
ParaView when a `PORT-1` number comes out wrong. It builds
``MeshGenerator.two_torus_domain(port_gap=True)`` at the parameters the
`GEO-8` / `GEO-10` / `GEO-11` gates use, writes ParaView-ready XDMF carrying
the mesh, the cell tags (wire / gap / air) and the facet tags (the `GEO-10`
``outer_boundary`` group plus the `PORT-1` step-3b-iv port cuts), and prints a
short report.

**It asserts, it does not merely render.** Three closed-form identities, all
allreduced, all of them landed gates re-executed here on the example's own
mesh:

* `GEO-10` — summed ``outer_boundary`` (facet tag ``1``) area / analytic box
  surface ``2(LW + LH + WH)`` = 1 to ``1e-9``. The box walls are planar, so a
  linear-tet surface mesh partitions them exactly; this is an identity, not a
  band. On record: ``1.000000000000``.
* `GEO-8` — total mesh volume / analytic box volume = 1 to ``1e-9``, and the
  five tagged volumes sum to the total to ``1e-9``: the tori are meshed once
  and the tags partition the box.
* `PORT-1` step 3b-i — each gap box is a rectangular solid with planar faces,
  so its meshed volume equals ``dx·dy·dz`` to ``1e-9``.

**Negative controls, on record — not re-run here.** Before `GEO-8`
(2026-08-01) the fixture never fragmented: gmsh meshed the box *solid* through
the torus regions and the tori as two disconnected islands, so the total/box
volume ratio was ``1.002633`` (the tori counted twice) and a source restricted
to torus 1 produced ``Z12 == 0`` *exactly* — the field could not leave its
island (`PORT-1` step-1 logs ``20260731T213222Z_…`` /
``…213423Z_…meshconformity.log``). Before `GEO-10` (2026-08-06) the
``outer_boundary`` physical group never reached the dolfinx facet tags at all:
the ungapped global facet-tag set was ``[]`` and the gapped one ``[201, 202]``
(known-issues 10). Both defects are invisible in a rendering and loud in the
identities above.

**No solve.** Port voltages and S-parameters are ungated (`PORT-1` is 🟡,
PROJECT_PLAN.md §2) and deliberately absent from this example; it needs only
the real DolfinX build.

Run it through the example runner::

    ./run_examples.sh -e mesh:1

Output lands in ``examples/meshing/paraview_output/``: open
``meshing_01_two_torus_ports_combined.xdmf`` and threshold on ``CellTags``
(1 = wire 1, 2 = wire 2, 3 = air, 101/102 = the two gap boxes), and open
``meshing_01_two_torus_ports_facets.xdmf`` alongside it for the facet groups — the array
is ``mesh_tags`` (1 = outer boundary, 201/202 = the port cuts).

Measured at ``-n 2`` on the **0.11 image** (dolfinx 0.11 / gmsh 4.15.2):
79 070 cells in 14.1 s, 14.2 s total (measured 2026-08-26). The 0.7.2 image
meshed 79 534 cells in 12.9 s (13.1 s total,
measured 2026-08-06); the −0.58% move is the documented image change, ruled
re-recordable 2026-08-25 alongside the `GEO-16` gate constant this count
shares a code path with.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem, io

from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_xdmf_with_tags,
)

# Geometry — the parameter set the `GEO-8`/`GEO-10`/`PORT-1` step-3b gates use
# (tests/mesh/test_two_torus_gapped.py, test_two_torus_outer_boundary.py), not
# the bare signature defaults: at the uniform 0.02 the cells are four times the
# wire minor radius and the meshed torus loses most of its volume to chordal
# deficit, which would say nothing about the fragment.
SEPARATION = 0.05
MAJOR_RADIUS = 0.02
MINOR_RADIUS = 0.005
RESOLUTION = 0.01
AIR_PADDING = 2.0 * MINOR_RADIUS
WIRE_RESOLUTION = 0.002

GAP_ANGLE = 0.30
GAP_CLEARANCE = 1.0e-3

WIRE_TAGS = (1, 2)
AIR_TAG = 3
GAP_TAGS = (101, 102)

OUTER_BOUNDARY_TAG = 1
PORT_FACET_TAGS = (201, 202)

CELL_TAG_NAMES = {1: "wire 1 (z<0)", 2: "wire 2 (z>0)", 3: "air", 101: "gap 1", 102: "gap 2"}
FACET_TAG_NAMES = {1: "outer_boundary", 201: "port cut 1", 202: "port cut 2"}

VOLUME_RTOL = 1e-9
AREA_RTOL = 1e-9

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "meshing_01_two_torus_ports"


def _box_halves():
    """The fixture's own box sizing, restated from ``io/mesh.py``."""
    radial_extent = MAJOR_RADIUS + MINOR_RADIUS
    return (
        radial_extent + AIR_PADDING,
        radial_extent + AIR_PADDING,
        SEPARATION / 2.0 + MINOR_RADIUS + AIR_PADDING,
    )


def _analytic_box_volume():
    half_x, half_y, half_z = _box_halves()
    return 8.0 * half_x * half_y * half_z


def _analytic_box_surface_area():
    half_x, half_y, half_z = _box_halves()
    length, width, height = 2 * half_x, 2 * half_y, 2 * half_z
    return 2.0 * (length * width + length * height + width * height)


def _analytic_gap_box_volume():
    half_xz = MINOR_RADIUS + GAP_CLEARANCE
    half_y = MAJOR_RADIUS * np.sin(0.5 * GAP_ANGLE) + GAP_CLEARANCE
    return (2.0 * half_xz) * (2.0 * half_y) * (2.0 * half_xz)


def _analytic_partial_torus_volume():
    """The wedge-opened torus: the gap box then swallows a little more."""
    return (
        (1.0 - GAP_ANGLE / (2.0 * np.pi))
        * 2.0
        * np.pi**2
        * MAJOR_RADIUS
        * MINOR_RADIUS**2
    )


def _tag_volume(msh, cell_tags, tag, comm):
    """``∫_tag 1 dV``, reduced — ``assemble_scalar`` is rank-local."""
    dx_tag = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,))
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * dx_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _total_volume(msh, comm):
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * ufl.dx))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _exterior_facet_group_area(msh, facet_tags, tag, comm):
    """``∫_tag 1 ds``, reduced.

    ``create_entity_permutations`` is called unconditionally on every rank: a
    rank that owns no tagged facet must still enter any collective the
    assembler might reach (known-issues 9).
    """
    msh.topology.create_entity_permutations()
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)

    ds_tag = ufl.Measure("ds", domain=msh, subdomain_data=facet_tags, subdomain_id=(tag,))
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * ds_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _global_tag_set(values, comm):
    local = set(np.unique(values).tolist())
    return set().union(*comm.allgather(local))


def _global_tag_count(values, tag, comm):
    return int(comm.allreduce(int(np.count_nonzero(values == tag)), op=MPI.SUM))


def _build_mesh(comm):
    return MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=RESOLUTION,
        air_padding=AIR_PADDING,
        wire_resolution=WIRE_RESOLUTION,
        far_resolution=RESOLUTION,
        port_gap=True,
        gap_angle=GAP_ANGLE,
        gap_clearance=GAP_CLEARANCE,
        comm=comm,
    )


def _write_paraview(msh, cell_tags, facet_tags, comm):
    """Mesh + cell tags in one file, mesh + facet tags in a second.

    Cell tags ride as a DG0 ``CellTags`` array on the *cell* grid, so ParaView
    thresholds them like any field. Facet tags live on a different topology
    (tdim-1) and therefore cannot share that grid — they go to their own file,
    which is *not* grid-consolidated. In both files the mesh is written before
    the tags, or ParaView has nothing to bind them to.
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
        print("EX-1 — two-torus port fixture: mesh, cell tags, facet tags")
        print("=" * 72)
        print(
            f"\n[geometry] separation={SEPARATION} m  R={MAJOR_RADIUS} m  "
            f"r={MINOR_RADIUS} m  air_padding={AIR_PADDING} m"
            f"\n[geometry] port_gap=True  gap_angle={GAP_ANGLE} rad  "
            f"gap_clearance={GAP_CLEARANCE} m"
            f"\n[mesh] resolution={RESOLUTION} m  wire_resolution={WIRE_RESOLUTION} m",
            flush=True,
        )

    msh, cell_tags, facet_tags = _build_mesh(comm)
    assert cell_tags is not None, "model_to_mesh returned no cell tags"
    assert facet_tags is not None, "model_to_mesh returned no facet tags"

    n_cells = comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, MPI.SUM)
    mesh_seconds = time.perf_counter() - started

    # ---- tag inventory ---------------------------------------------------
    cell_tag_set = _global_tag_set(cell_tags.values, comm)
    facet_tag_set = _global_tag_set(facet_tags.values, comm)
    cell_counts = {t: _global_tag_count(cell_tags.values, t, comm) for t in sorted(cell_tag_set)}
    facet_counts = {t: _global_tag_count(facet_tags.values, t, comm) for t in sorted(facet_tag_set)}

    if comm.rank == 0:
        print(f"\n[mesh] {n_cells} cells built in {mesh_seconds:.1f} s")
        print("[tags] cell groups:")
        for tag, count in cell_counts.items():
            print(f"  {tag:>3d}  {CELL_TAG_NAMES.get(tag, '?'):<14s} {count:>7d} cells")
        print("[tags] facet groups:")
        for tag, count in facet_counts.items():
            print(f"  {tag:>3d}  {FACET_TAG_NAMES.get(tag, '?'):<14s} {count:>7d} facets")

    # The pre-`GEO-10` state was `[]` ungapped / `[201, 202]` gapped: the
    # outer-boundary group never reached the dolfinx tags (known-issues 10).
    assert cell_tag_set == set(WIRE_TAGS) | {AIR_TAG} | set(GAP_TAGS), (
        f"cell tag set is {sorted(cell_tag_set)}"
    )
    assert facet_tag_set == {OUTER_BOUNDARY_TAG} | set(PORT_FACET_TAGS), (
        f"facet tag set is {sorted(facet_tag_set)}, expected "
        f"{sorted({OUTER_BOUNDARY_TAG} | set(PORT_FACET_TAGS))} — a set missing "
        f"{OUTER_BOUNDARY_TAG} is the pre-`GEO-10` signature (known-issues 10)"
    )

    # ---- identity 1: `GEO-10` outer-boundary area ------------------------
    area = _exterior_facet_group_area(msh, facet_tags, OUTER_BOUNDARY_TAG, comm)
    a_box = _analytic_box_surface_area()

    # ---- identities 2-3: `GEO-8` volume partition, gap-box exactness -----
    v_total = _total_volume(msh, comm)
    v_box = _analytic_box_volume()
    v_wires = [_tag_volume(msh, cell_tags, t, comm) for t in WIRE_TAGS]
    v_gaps = [_tag_volume(msh, cell_tags, t, comm) for t in GAP_TAGS]
    v_air = _tag_volume(msh, cell_tags, AIR_TAG, comm)
    v_gap_exact = _analytic_gap_box_volume()
    v_arc = _analytic_partial_torus_volume()
    v_tagged = v_air + sum(v_wires) + sum(v_gaps)

    if comm.rank == 0:
        print(
            f"\n[GEO-10] A_outer={area:.12e} m^2  analytic={a_box:.12e} m^2"
            f"\n[GEO-10] ratio={area / a_box:.15f}   (gate: |ratio-1| < {AREA_RTOL:.0e})"
            f"\n\n[GEO-8]  V_mesh={v_total:.9e} m^3  analytic box={v_box:.9e} m^3"
            f"\n[GEO-8]  ratio={v_total / v_box:.12f}   "
            f"(the non-fragmented ancestor gave 1.002633)"
            f"\n[GEO-8]  sum(tagged)/V_mesh={v_tagged / v_total:.12f}"
            f"\n\n[3b-i]   V_gap1={v_gaps[0]:.9e}  V_gap2={v_gaps[1]:.9e}  "
            f"dx*dy*dz={v_gap_exact:.9e} m^3"
            f"\n[3b-i]   meshed/analytic={v_gaps[0] / v_gap_exact:.12f}, "
            f"{v_gaps[1] / v_gap_exact:.12f}"
            f"\n\n[wires]  V_wire1={v_wires[0]:.9e}  V_wire2={v_wires[1]:.9e}  "
            f"partial torus={v_arc:.9e} m^3"
            f"\n[wires]  meshed/analytic={v_wires[0] / v_arc:.6f}, "
            f"{v_wires[1] / v_arc:.6f}   (chordal deficit + what the gap box took)"
            f"\n[air]    V_air={v_air:.9e} m^3",
            flush=True,
        )

    assert abs(area / a_box - 1.0) < AREA_RTOL, (
        f"tagged outer-boundary area {area:.12e} m^2 differs from the analytic "
        f"box surface {a_box:.12e} m^2 by {abs(area / a_box - 1.0):.3e} relative"
    )
    assert abs(v_total / v_box - 1.0) < VOLUME_RTOL, (
        f"total mesh volume {v_total:.9e} m^3 vs analytic box {v_box:.9e} m^3 "
        f"(ratio {v_total / v_box:.9f}); ~1.0026 is the non-fragmented signature"
    )
    assert abs(v_tagged / v_total - 1.0) < VOLUME_RTOL, (
        f"the five tagged volumes sum to {v_tagged:.9e} m^3, not the mesh total "
        f"{v_total:.9e} m^3 — the tags do not partition the box"
    )
    for tag, v in zip(GAP_TAGS, v_gaps):
        assert abs(v / v_gap_exact - 1.0) < VOLUME_RTOL, (
            f"gap tag {tag} meshed volume {v:.9e} m^3 vs dx*dy*dz "
            f"{v_gap_exact:.9e} m^3 (ratio {v / v_gap_exact:.12f})"
        )

    # ---- ParaView ---------------------------------------------------------
    written = _write_paraview(msh, cell_tags, facet_tags, comm)
    if comm.rank == 0:
        print("\n[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<11s} {path}")
        print(
            "\n[paraview] threshold `CellTags` in the _combined file "
            "(1/2 wire, 3 air, 101/102 gap);"
            "\n           open the _facets file for `mesh_tags` "
            "(1 outer boundary, 201/202 port cuts)."
            f"\n\nAll identities hold. Total elapsed {time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
