"""Example (`EX-2`): the cylindrical phantom domain, classified and tagged.

`mesh:1` shows a *box-bounded* two-conductor fixture. This one shows the
**cylindrical** geometry — a curved outer wall, a phantom cylinder inside it —
and the boundary classification that decides which surfaces become
``outer_boundary``. That classification is what you are actually looking at
when a coil+phantom mesh comes out wrong, and the birdcage path runs through
cylinders.

It builds ``MeshGenerator.cylindrical_domain()`` at the generator defaults
`GEO-13` swept, writes ParaView-ready XDMF (mesh + cell tags, plus a second
file carrying the facet groups), and prints a report.

**It asserts, it does not merely render.**

* `GEO-13` — the live two-sided classification margin, recomputed here on the
  example's own CAD model with ``_WALL_TOL_FRACTION`` imported from the
  generator, exactly as ``tests/mesh/test_boundary_classification_margins.py``
  does: 3 of 6 surfaces accepted, worst accepted at ``1.111111e-04 x tol``
  (ceiling 0.1) and nearest rejected at ``9.999989e+01 x tol`` (floor 10).
* An exact partition identity: the two tagged volumes sum to the mesh total to
  ``1e-9``. Linear tets partition exactly, curvature or not.
* Closed-form volumes and areas, **with the curvature stated honestly**. A
  linear-tet mesh *inscribes* a curved wall, so every meshed/analytic ratio is
  strictly below 1 and no exact identity exists here — `GEO-12`'s planar
  ``1e-15`` does not transfer. Where the outer wall is resolved the deficit is
  the O(h²) chordal loss and the ratio sits in ``(0.98, 1)``; the inner
  cylinder is *not* resolved at these defaults and gets its own closed form,
  below.

**The inner cylinder is under-resolved by construction, and the example says
so in closed form.** At the defaults the cell size ``0.02`` is *twice* the
inner radius ``0.01``, so gmsh falls back to its minimum circle
discretisation — 7 nodes — and the inner cylinder meshes as a heptagonal
prism. The end-cap area ratio is therefore the inscribed-heptagon ratio
``(7/2pi) sin(2pi/7) = 0.8710264``, and the mesh hits it to **1.11e-16
relative**: the cap is not approximately that polygon, it *is* that polygon.
The inner *volume* ratio falls further still (``0.718170``) as the lateral
triangulation cuts inside the prism. Both are asserted against closed forms —
the heptagon value for the caps, and a two-sided bracket between the
degenerate-square floor ``2/pi`` and the heptagonal-prism ceiling for the
volume. This is the honest reading of these defaults: the outer wall is a
converged curved surface, the inner one is a polygon.

**Negative control, on record — not re-run here.** Before `GEO-13`
(2026-08-07) the predicate used ``tol = resolution``, keying a *geometric*
classification to *mesh size*. At ``resolution = 0.09`` it accepted **6 of 6**
surfaces — the inner cylinder swept whole into ``outer_boundary`` — and even
at the defaults the interior margin was only 4.50x the tolerance, below the
10x floor (`20260807T033127Z_GEO-13-probe.log`, known-issues 13, now
retired). A rendering shows none of that; the margins above do.

**No solve.** Fields, ports and SAR are out of scope here — this is geometry
and tags only, so it needs just the real DolfinX build.

Run it through the example runner::

    ./run_examples.sh -e mesh:2

Output lands in ``examples/meshing/paraview_output/``: open
``meshing_02_cylindrical_phantom_combined.xdmf`` and threshold on ``CellTags``
(1 = inner phantom cylinder, 2 = surrounding domain), and open
``meshing_02_cylindrical_phantom_facets.xdmf`` alongside it for ``mesh_tags``
(1 = outer_boundary, 2 = inner_boundary).

Measured 2026-08-07 at ``-n 2``: 5 717 cells, mesh built in 0.7 s.
"""

from __future__ import annotations

import time
from pathlib import Path

import gmsh
import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem, io

from fem_em_solver.io.mesh import MeshGenerator, _WALL_TOL_FRACTION
from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_xdmf_with_tags,
)

# Geometry — ``cylindrical_domain``'s own signature defaults, which are the
# argument set `GEO-13` swept and the margins test replicates.
INNER_RADIUS = 0.01
OUTER_RADIUS = 0.1
LENGTH = 0.2
RESOLUTION = 0.02

INNER_TAG = 1
OUTER_TAG = 2
OUTER_BOUNDARY_TAG = 1
INNER_BOUNDARY_TAG = 2

CELL_TAG_NAMES = {1: "inner (phantom)", 2: "outer (domain)"}
FACET_TAG_NAMES = {1: "outer_boundary", 2: "inner_boundary"}

# `GEO-11`'s two-sided margin, restated (test_boundary_classification_margins).
WALL_MARGIN = 0.1
INTERIOR_MARGIN = 10.0
#: The `GEO-13` record this example must reproduce through the example path
#: (`20260807T033127Z_GEO-13-probe.log`, re-measured
#: `20260807T140258Z_EX-2-probe.log`).
RECORDED_N_SURFACES = 6
RECORDED_N_ACCEPTED = 3
RECORDED_WALL_RATIO = 1.111111e-04
RECORDED_INTERIOR_RATIO = 9.999989e01
RATIO_RTOL = 1e-6

#: Linear tets inscribe a curved wall: every meshed/analytic ratio is below 1,
#: and where the wall is resolved the O(h²) chordal deficit keeps it above this.
CHORDAL_FLOOR = 0.98
#: The two tagged volumes partition the mesh exactly — this one *is* an identity.
PARTITION_RTOL = 1e-9

#: gmsh's minimum circle discretisation, which the inner cylinder falls back to
#: because ``RESOLUTION`` is twice ``INNER_RADIUS``.
MIN_CIRCLE_NODES = 7
#: Closed-form ceiling for anything built on that polygon: the inscribed regular
#: n-gon's area as a fraction of its circle.
HEPTAGON_RATIO = (MIN_CIRCLE_NODES / (2.0 * np.pi)) * np.sin(
    2.0 * np.pi / MIN_CIRCLE_NODES
)
#: The meshed end caps hit that closed form at machine precision — measured
#: 1.11e-16 relative (`20260807T140522Z_EX-2.log`), i.e. the cap really *is* the
#: inscribed heptagon, not merely close to it. The bound keeps four orders of
#: headroom over the measurement rather than pinning a printed digit string.
CAP_RTOL = 1e-12
#: The coarsest polygon a circle can degenerate to before the geometry stops
#: being a cylinder at all — the floor for the inner volume's further loss.
SQUARE_RATIO = 2.0 / np.pi

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "meshing_02_cylindrical_phantom"


def _analytic_volumes():
    """Closed-form cylinder volumes: total, inner, and the annulus between."""
    v_total = np.pi * OUTER_RADIUS**2 * LENGTH
    v_inner = np.pi * INNER_RADIUS**2 * LENGTH
    return v_total, v_inner, v_total - v_inner


def _analytic_outer_surface():
    """The whole outer cylinder surface — lateral plus both end caps.

    All three of those are what the wall test accepts (their bounding boxes
    reach ``r_max = outer_radius``), so this is the analytic partner of the
    tagged ``outer_boundary`` group.
    """
    return 2.0 * np.pi * OUTER_RADIUS * LENGTH + 2.0 * np.pi * OUTER_RADIUS**2


def _analytic_inner_end_caps():
    """Only the caps: the inner cylinder's lateral face is an *interior*
    interface, so an exterior-facet measure never sees it."""
    return 2.0 * np.pi * INNER_RADIUS**2


def _classification_margins():
    """Replicate the CAD stage and classify every dim-2 entity.

    Serial, rank 0 only, and bracketed in ``try/finally``: gmsh state poisons
    every later build in the same process (`GEO-9` step 2a), and the generator
    called next runs its own ``initialize``.
    """
    gmsh.initialize()
    try:
        gmsh.model.add("ex2_cylindrical")
        inner = gmsh.model.occ.addCylinder(
            0, 0, -LENGTH / 2, 0, 0, LENGTH, INNER_RADIUS
        )
        outer = gmsh.model.occ.addCylinder(
            0, 0, -LENGTH / 2, 0, 0, LENGTH, OUTER_RADIUS
        )
        gmsh.model.occ.fragment([(3, outer)], [(3, inner)])
        gmsh.model.occ.synchronize()

        # Read from the generator so the example and the shipped predicate
        # cannot drift apart — the margins test does exactly this.
        tol = _WALL_TOL_FRACTION * (OUTER_RADIUS - INNER_RADIUS)

        rows = []
        for dim, surf in gmsh.model.getEntities(dim=2):
            _, _, _, x_max, y_max, _ = gmsh.model.getBoundingBox(dim, surf)
            r_max = float(np.sqrt(max(x_max**2, y_max**2)))
            residual = abs(r_max - OUTER_RADIUS)
            rows.append((surf, residual, residual < tol))
    finally:
        gmsh.finalize()
    return rows, tol


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

    ``create_entity_permutations`` runs on every rank unconditionally: a rank
    owning no tagged facet must still enter the collective (known-issues 9).
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


def _write_paraview(msh, cell_tags, facet_tags, comm):
    """Mesh + cell tags in one file, mesh + facet tags in a second.

    Cell tags ride as a DG0 ``CellTags`` array on the cell grid; facet tags
    live on the tdim-1 topology and cannot share it. In both files the mesh is
    written before the tags, or ParaView has nothing to bind them to.
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
        print("EX-2 — cylindrical phantom domain: mesh, cell tags, wall classification")
        print("=" * 72)
        print(
            f"\n[geometry] inner_radius={INNER_RADIUS} m  "
            f"outer_radius={OUTER_RADIUS} m  length={LENGTH} m"
            f"\n[mesh] resolution={RESOLUTION} m "
            f"(= {RESOLUTION / INNER_RADIUS:g} x the inner radius — see below)",
            flush=True,
        )

    # ---- identity 1: the `GEO-13` two-sided classification margin ---------
    # CAD only, so rank 0 measures and broadcasts; every rank asserts.
    measured = _classification_margins() if comm.rank == 0 else None
    rows, tol = comm.bcast(measured, root=0)

    accepted = [r for _, r, ok in rows if ok]
    rejected = [r for _, r, ok in rows if not ok]
    wall_ratio = max(accepted) / tol if accepted else None
    interior_ratio = min(rejected) / tol if rejected else None

    if comm.rank == 0:
        print(
            f"\n[GEO-13] tol = {_WALL_TOL_FRACTION} x (outer-inner) = {tol:.6e} m "
            f"(never `resolution` — that was the defect)"
        )
        for surf, residual, ok in rows:
            print(
                f"[GEO-13]   surf {surf:3d} residual={residual:.6e} "
                f"ratio={residual / tol:.6e} accepted={ok}"
            )
        print(
            f"[GEO-13] {len(accepted)}/{len(rows)} accepted   "
            f"wall_ratio={wall_ratio:.6e} (ceiling {WALL_MARGIN})   "
            f"interior_ratio={interior_ratio:.6e} (floor {INTERIOR_MARGIN})"
            f"\n[GEO-13] the pre-`GEO-13` predicate accepted 6/6 at resolution=0.09 "
            f"— the phantom swept into outer_boundary (known-issues 13, retired)",
            flush=True,
        )

    assert len(rows) == RECORDED_N_SURFACES, (
        f"the CAD model has {len(rows)} dim-2 entities, the `GEO-13` record has "
        f"{RECORDED_N_SURFACES} — the geometry changed; re-measure before trusting "
        f"any margin here"
    )
    assert len(accepted) == RECORDED_N_ACCEPTED, (
        f"the wall test accepted {len(accepted)} of {len(rows)} surfaces at "
        f"tol={tol:.3e}, the `GEO-13` record has {RECORDED_N_ACCEPTED}; 6 of 6 is "
        f"the pre-`GEO-13` signature (known-issues 13)"
    )
    assert wall_ratio <= WALL_MARGIN * (1.0 + RATIO_RTOL), (
        f"an accepted surface sits at residual/tol = {wall_ratio:.6e}, above the "
        f"{WALL_MARGIN} ceiling — the tolerance no longer clears the gmsh OCC "
        f"bounding-box padding by 10x and the group could silently empty "
        f"(that is known-issues 10's mechanism)"
    )
    assert interior_ratio >= INTERIOR_MARGIN * (1.0 - RATIO_RTOL), (
        f"a rejected surface sits at residual/tol = {interior_ratio:.6e}, below the "
        f"{INTERIOR_MARGIN} floor — an interior face is within an order of "
        f"magnitude of being swept into outer_boundary"
    )
    assert abs(wall_ratio / RECORDED_WALL_RATIO - 1.0) < RATIO_RTOL, (
        f"worst accepted residual/tol = {wall_ratio:.6e}, the `GEO-13` record is "
        f"{RECORDED_WALL_RATIO:.6e} — a regression against a landed gate"
    )
    assert abs(interior_ratio / RECORDED_INTERIOR_RATIO - 1.0) < RATIO_RTOL, (
        f"nearest rejected residual/tol = {interior_ratio:.6e}, the `GEO-13` record "
        f"is {RECORDED_INTERIOR_RATIO:.6e} — a regression against a landed gate"
    )

    # ---- mesh -------------------------------------------------------------
    mesh_started = time.perf_counter()
    msh, cell_tags, facet_tags = MeshGenerator.cylindrical_domain(
        inner_radius=INNER_RADIUS,
        outer_radius=OUTER_RADIUS,
        length=LENGTH,
        resolution=RESOLUTION,
        comm=comm,
    )
    mesh_seconds = time.perf_counter() - mesh_started
    assert cell_tags is not None, "model_to_mesh returned no cell tags"
    assert facet_tags is not None, "model_to_mesh returned no facet tags"

    n_cells = comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, MPI.SUM)

    cell_tag_set = _global_tag_set(cell_tags.values, comm)
    facet_tag_set = _global_tag_set(facet_tags.values, comm)
    cell_counts = {t: _global_tag_count(cell_tags.values, t, comm) for t in sorted(cell_tag_set)}
    facet_counts = {t: _global_tag_count(facet_tags.values, t, comm) for t in sorted(facet_tag_set)}

    if comm.rank == 0:
        print(f"\n[mesh] {n_cells} cells built in {mesh_seconds:.1f} s")
        print("[tags] cell groups:")
        for tag, count in cell_counts.items():
            print(f"  {tag:>3d}  {CELL_TAG_NAMES.get(tag, '?'):<16s} {count:>7d} cells")
        print("[tags] facet groups:")
        for tag, count in facet_counts.items():
            print(f"  {tag:>3d}  {FACET_TAG_NAMES.get(tag, '?'):<16s} {count:>7d} facets")

    assert cell_tag_set == {INNER_TAG, OUTER_TAG}, f"cell tag set is {sorted(cell_tag_set)}"
    assert facet_tag_set == {OUTER_BOUNDARY_TAG, INNER_BOUNDARY_TAG}, (
        f"facet tag set is {sorted(facet_tag_set)}; a set missing "
        f"{OUTER_BOUNDARY_TAG} means the outer_boundary group never reached the "
        f"dolfinx tags (known-issues 10's signature)"
    )

    # ---- identities 2-4: volumes, areas, and the honest curvature ---------
    v_total = _total_volume(msh, comm)
    v_inner = _tag_volume(msh, cell_tags, INNER_TAG, comm)
    v_outer = _tag_volume(msh, cell_tags, OUTER_TAG, comm)
    a_total, a_inner, a_annulus = _analytic_volumes()

    area_outer = _exterior_facet_group_area(msh, facet_tags, OUTER_BOUNDARY_TAG, comm)
    area_inner = _exterior_facet_group_area(msh, facet_tags, INNER_BOUNDARY_TAG, comm)
    a_outer_surf = _analytic_outer_surface()
    a_inner_caps = _analytic_inner_end_caps()

    if comm.rank == 0:
        print(
            f"\n[partition] (V_inner + V_outer)/V_mesh = "
            f"{(v_inner + v_outer) / v_total:.15f}   (exact: linear tets partition)"
            f"\n\n[volume] V_mesh  ={v_total:.9e}  analytic cylinder={a_total:.9e}  "
            f"ratio={v_total / a_total:.9f}  deficit={1.0 - v_total / a_total:.3%}"
            f"\n[volume] V_outer ={v_outer:.9e}  analytic annulus ={a_annulus:.9e}  "
            f"ratio={v_outer / a_annulus:.9f}  deficit={1.0 - v_outer / a_annulus:.3%}"
            f"\n[volume] V_inner ={v_inner:.9e}  analytic cylinder={a_inner:.9e}  "
            f"ratio={v_inner / a_inner:.9f}  deficit={1.0 - v_inner / a_inner:.3%}"
            f"\n\n[area]   A_outer_boundary={area_outer:.9e}  "
            f"analytic (lateral + 2 caps)={a_outer_surf:.9e}  "
            f"ratio={area_outer / a_outer_surf:.9f}"
            f"\n[area]   A_inner_boundary={area_inner:.9e}  analytic end caps="
            f"{a_inner_caps:.9e}  ratio={area_inner / a_inner_caps:.9f}"
            f"\n[area]   (the inner lateral face is an INTERIOR interface, so an "
            f"exterior-facet measure sees the caps only)"
            f"\n\n[coarse] resolution/inner_radius = {RESOLUTION / INNER_RADIUS:g}: the "
            f"inner circle falls back to gmsh's {MIN_CIRCLE_NODES}-node minimum, so the "
            f"phantom is a heptagonal prism."
            f"\n[coarse] inscribed heptagon/circle = {HEPTAGON_RATIO:.7f}; the measured "
            f"cap ratio is {area_inner / a_inner_caps:.7f} "
            f"({abs(area_inner / a_inner_caps / HEPTAGON_RATIO - 1.0):.2e} relative)."
            f"\n[coarse] the inner VOLUME falls further ({v_inner / a_inner:.6f}) — the "
            f"lateral triangulation cuts inside that prism; bracket "
            f"({SQUARE_RATIO:.6f}, {HEPTAGON_RATIO:.6f}).",
            flush=True,
        )

    # The one exact identity available on a curved geometry.
    assert abs((v_inner + v_outer) / v_total - 1.0) < PARTITION_RTOL, (
        f"the two tagged volumes sum to {v_inner + v_outer:.9e} m^3, not the mesh "
        f"total {v_total:.9e} m^3 — the tags do not partition the domain"
    )

    # Inscription: a linear-tet mesh is strictly inside a curved wall. A ratio
    # at or above 1 would mean the mesh escaped the analytic body.
    for label, ratio in (
        ("V_mesh/cylinder", v_total / a_total),
        ("V_outer/annulus", v_outer / a_annulus),
        ("V_inner/cylinder", v_inner / a_inner),
        ("A_outer_boundary/surface", area_outer / a_outer_surf),
        ("A_inner_boundary/caps", area_inner / a_inner_caps),
    ):
        assert ratio < 1.0, (
            f"{label} = {ratio:.9f} >= 1: an inscribed linear-tet mesh cannot "
            f"exceed the curved analytic body"
        )

    # Where the outer wall is resolved, the deficit is the O(h^2) chordal loss.
    for label, ratio in (
        ("V_mesh/cylinder", v_total / a_total),
        ("V_outer/annulus", v_outer / a_annulus),
        ("A_outer_boundary/surface", area_outer / a_outer_surf),
    ):
        assert ratio > CHORDAL_FLOOR, (
            f"{label} = {ratio:.9f} is below the {CHORDAL_FLOOR} chordal-deficit "
            f"floor — that is more than O(h^2) loss on a wall this resolution "
            f"resolves; the mesh or the geometry changed"
        )

    # The inner cylinder is a heptagonal prism, and its caps say so exactly.
    cap_ratio = area_inner / a_inner_caps
    assert abs(cap_ratio / HEPTAGON_RATIO - 1.0) < CAP_RTOL, (
        f"the inner end-cap area ratio is {cap_ratio:.7f}, not the inscribed "
        f"regular {MIN_CIRCLE_NODES}-gon's {HEPTAGON_RATIO:.7f} — gmsh's minimum "
        f"circle node count is no longer {MIN_CIRCLE_NODES}, or the inner circle "
        f"is now resolved by `resolution`; re-derive before trusting the deficits"
    )
    inner_volume_ratio = v_inner / a_inner
    assert SQUARE_RATIO < inner_volume_ratio < HEPTAGON_RATIO, (
        f"the inner volume ratio {inner_volume_ratio:.6f} is outside the "
        f"({SQUARE_RATIO:.6f}, {HEPTAGON_RATIO:.6f}) bracket — below the "
        f"degenerate-square floor the phantom is not a cylinder at all, and above "
        f"the heptagonal-prism ceiling it cannot be built from {MIN_CIRCLE_NODES} "
        f"circle nodes"
    )

    # ---- ParaView ---------------------------------------------------------
    written = _write_paraview(msh, cell_tags, facet_tags, comm)
    if comm.rank == 0:
        print("\n[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<11s} {path}")
        print(
            "\n[paraview] threshold `CellTags` in the _combined file "
            "(1 = inner phantom, 2 = surrounding domain);"
            "\n           open the _facets file for `mesh_tags` "
            "(1 = outer_boundary, 2 = inner_boundary)."
            f"\n\nAll identities hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
