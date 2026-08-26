"""`GEO-16` — the gap boxes' longitudinal port-sheet mid-plane, mesh only.

``two_torus_domain(port_gap=True, emit_port_sheet=True)`` fragments each gap
box with its own mid-plane ``z = ±separation/2``, so the tet mesh conforms to
the surface a lumped-element port BC needs (`PORT-9` step 1, Jin ch. 11).
Nothing is solved here.

**Why a new surface at all.** A lumped sheet spans terminal to terminal with
the port current flowing *in* its plane. The fixture's existing tagged
surfaces — facet tags ``201`` / ``202``, gated by
``test_two_torus_port_facets.py`` — are the gap↔conductor cross-sections,
which are *normal* to that current: the wrong constitutive law for
``R = Z_p · w / h``. The mid-plane contains both the gap's centreline arc and
the current direction ``ŷ``, so it is the surface that law is written for.

**The anchor.** The mid-plane is planar and the fragment makes the mesh
conform to it, so a linear-tet triangulation of it is *exact*: the MPI-reduced
``dS`` area of the reconstructed facet set must equal the CAD area of the same
surface — here the gap box's own cross-section ``(2·gap_half_xz)·(2·gap_half_y)``,
which is what OCC's ``getMass(2, ·)`` returns for the rectangle (printed by
the generator beside it) — to < 1e-9 relative, on **both** gap boxes. That is
the `GEO-15` CAD-denominator pattern, and unlike the 2.55% chordal deficit the
arc-end discs carry (3b-iv), a plane section has no curvature to inscribe.

**Negative controls.** (i) The facet set is asserted non-empty *before* the
area identity, so a reconstruction that silently matches zero facets fails at
100% separation rather than passing vacuously — 0/0 is not an identity.
(ii) With the kwarg off the mesh must bit-match the record: same global cell
count, same cell-tag set ``{1, 2, 3, 101, 102}``, same facet-tag set
``{1, 201, 202}``, no ``21x`` group anywhere. Every `PORT-1` / `PORT-10`
number was measured on that mesh and must stay reproducible.

**Printed, never gated:** the sheet's measured extents — area, length ``h``
along the current direction, transverse width ``w``, and ``w/h``, the "number
of squares" `PORT-9` step 1 converts a port impedance through. The gap box
crosses a round arc, so those are measured quantities on this fixture rather
than the box's nominal dimensions (the premise the 2026-08-16T17:08Z attempt
was blocked on).
"""

from __future__ import annotations

import numpy as np
from mpi4py import MPI

import dolfinx

from fem_em_solver.io.mesh import MeshGenerator

from tests.mesh.test_two_torus_port_facets import (
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

SHEET_FACET_TAGS = (211, 212)
GAP_CELL_TAGS_WITH_SHEET = (101, 111, 102, 112)

# The kwarg-off record: 79 070 cells, measured on this fixture at `-n 2` on the
# **0.11 image** (dolfinx 0.11 / gmsh 4.15.2) in
# ``20260825T213632Z_EX-30-mesh-gate-probe.log``. It read 79 534 until
# 2026-08-26, measured on the 0.7.2 image in ``20260817T003524Z_GEO-16.log``;
# that digit is stale, not a regression. The sheet is exonerated by two
# independent no-sheet builds on 0.11 agreeing exactly at 79 070 (`mesh:1`,
# which asserts no count, and `mesh:4`'s own kwarg-off control) while the
# sheeted build stays properly distinct at 79 940, and by this module's five
# other assertions staying green through the move — including the 0.970–0.980
# meshed-band cross-check named below, which is the constant's actual guard.
# The −0.58% move is in family with the 0.11-gmsh mesh motion already recorded
# elsewhere (two-torus solve fixture −0.40%, `TH-10` −0.02%). Re-record ruled
# by the 2026-08-25 18:00 review; version-tag this constant if the image moves
# again. `PORT-1`/`PORT-10` pin no cell count for
# *this* (mesh-only, RESOLUTION = 0.01) fixture, so the count is pinned from
# that run rather than imported; what is imported and independently on record
# is the CAD port-interface area 1.604721e-04 m^2 and the 0.970–0.980 meshed
# band that ``test_two_torus_port_facets.py`` gates on the same default mesh —
# run alongside this file, it is the cross-check that the shared code path did
# not move. The point of the constant is that the *opt-in* sheet may not
# perturb the mesh every gated `PORT-1` / `PORT-10` number was measured on.
NCELLS_UNGATED_RECORD = 79_070

# A planar surface meshed by linear tets is exact; the only slack is roundoff
# in the sum. 1e-9 relative is the `GEO-15` CAD-denominator band.
AREA_IDENTITY_BAND = 1.0e-9


def _mesh(comm, emit_port_sheet):
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
        emit_port_sheet=emit_port_sheet,
        comm=comm,
    )


def _global_cell_tag_set(cell_tags, comm):
    local = set(np.unique(cell_tags.values).tolist())
    return set().union(*comm.allgather(local))


def _sheet_facet_count(msh, facet_tags, tag, comm):
    """Owned facets carrying ``tag``, reduced. Ghost facets would double-count."""
    fdim = msh.topology.dim - 1
    n_local = msh.topology.index_map(fdim).size_local
    facets = facet_tags.find(tag)
    return int(comm.allreduce(int(np.count_nonzero(facets < n_local)), op=MPI.SUM))


def _sheet_extents(msh, facet_tags, tag, comm):
    """Measured ``(w, h, z)`` bounding extents of one sheet's facet set [m].

    ``w`` is transverse (x), ``h`` runs along the current direction (y), and
    ``z`` is the out-of-plane spread — zero to roundoff if the facet set really
    is the plane it claims to be. Node coordinates come through
    ``entities_to_geometry`` (the `PORT-1` 3b-ix pattern); ghosts are harmless
    for a min/max, and the reduction is over ranks either way.
    """
    fdim = msh.topology.dim - 1
    facets = np.asarray(facet_tags.find(tag), dtype=np.int32)
    if facets.size:
        nodes = dolfinx.cpp.mesh.entities_to_geometry(
            msh._cpp_object, fdim, facets, False
        )
        pts = msh.geometry.x[nodes.reshape(-1)]
        lo, hi = pts.min(axis=0), pts.max(axis=0)
    else:
        lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    # ``comm.allreduce(array, op=MPI.MIN)`` would fall through to Python's
    # ``min`` on two arrays and raise on the ambiguous truth value; gather and
    # reduce elementwise instead.
    lo = np.min(np.array(comm.allgather(lo)), axis=0)
    hi = np.max(np.array(comm.allgather(hi)), axis=0)
    return hi - lo


def test_port_sheet_facet_set_is_the_gap_box_mid_plane():
    """The reconstructed sheet has exactly the CAD mid-plane's area."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, facet_tags = _mesh(comm, emit_port_sheet=True)
    assert facet_tags is not None, "model_to_mesh returned no facet tags"

    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)

    cell_tags_present = _global_cell_tag_set(cell_tags, comm)
    facet_tags_present = _global_facet_tag_set(msh, facet_tags, comm)
    assert cell_tags_present == {1, 2, 3, *GAP_CELL_TAGS_WITH_SHEET}, (
        "the sheet path must split each gap box into two cell groups; found "
        f"{sorted(cell_tags_present)}"
    )
    assert set(SHEET_FACET_TAGS) <= facet_tags_present, (
        f"sheet facet tags missing; found {sorted(facet_tags_present)}"
    )
    assert set(PORT_FACET_TAGS) <= facet_tags_present, (
        "the sheet path dropped the port facet groups; found "
        f"{sorted(facet_tags_present)}"
    )

    # Non-empty BEFORE the identity: 0 == 0 is not a match.
    counts = {t: _sheet_facet_count(msh, facet_tags, t, comm)
              for t in SHEET_FACET_TAGS}
    for tag, n in counts.items():
        assert n > 0, (
            f"sheet facet group {tag} is empty; the area identity below would "
            "have passed vacuously"
        )

    # The CAD denominator: the gap box's own cross-section. Planar, so this is
    # what OCC's getMass(2, .) returns for the fragment surface (the generator
    # prints its value beside this one).
    a_cad = 4.0 * _gap_half_xz() * _gap_half_y()

    areas = {t: _facet_group_area(msh, facet_tags, t, comm)
             for t in SHEET_FACET_TAGS}
    extents = {t: _sheet_extents(msh, facet_tags, t, comm)
               for t in SHEET_FACET_TAGS}
    port_areas = {t: _facet_group_area(msh, facet_tags, t, comm)
                  for t in PORT_FACET_TAGS}

    if comm.rank == 0:
        print(
            f"\n[GEO-16] cell tags {sorted(cell_tags_present)}; facet tags "
            f"{sorted(facet_tags_present)}"
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
                f"spread={dz:.3e} m",
                flush=True,
            )
        for tag in PORT_FACET_TAGS:
            print(f"[GEO-16] port {tag} area (unmoved check) "
                  f"{port_areas[tag]:.9e} m^2", flush=True)

    for tag in SHEET_FACET_TAGS:
        rel = abs(areas[tag] - a_cad) / a_cad
        assert rel < AREA_IDENTITY_BAND, (
            f"sheet facet group {tag} area {areas[tag]:.12e} m^2 differs from "
            f"the CAD mid-plane {a_cad:.12e} m^2 by {rel:.3e} relative, "
            f"outside {AREA_IDENTITY_BAND:.0e}"
        )

    # Same solid mirrored in z: the two sheets are built identically.
    assert abs(areas[211] / areas[212] - 1.0) < 1e-12, (
        f"sheet areas differ: {areas[211]:.12e} vs {areas[212]:.12e}"
    )


def test_kwarg_off_reproduces_the_recorded_mesh():
    """Negative control: the default path is untouched, bit for bit."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, facet_tags = _mesh(comm, emit_port_sheet=False)

    ncells = msh.topology.index_map(msh.topology.dim).size_global
    cell_tags_present = _global_cell_tag_set(cell_tags, comm)
    facet_tags_present = _global_facet_tag_set(msh, facet_tags, comm)

    if comm.rank == 0:
        print(
            f"\n[GEO-16 control] cells={ncells} cell tags "
            f"{sorted(cell_tags_present)} facet tags "
            f"{sorted(facet_tags_present)}",
            flush=True,
        )

    assert cell_tags_present == {1, 2, 3, 101, 102}, (
        f"the default path changed its cell-tag set: {sorted(cell_tags_present)}"
    )
    assert facet_tags_present == {1, *PORT_FACET_TAGS}, (
        f"the default path changed its facet-tag set: "
        f"{sorted(facet_tags_present)}"
    )
    assert not (set(SHEET_FACET_TAGS) & facet_tags_present), (
        "the default path emitted sheet facet tags"
    )
    if NCELLS_UNGATED_RECORD is not None:
        assert ncells == NCELLS_UNGATED_RECORD, (
            f"the default path meshed {ncells} cells against the recorded "
            f"{NCELLS_UNGATED_RECORD}: the opt-in sheet perturbed the mesh "
            "every gated PORT-1 / PORT-10 number was measured on"
        )


def test_sheet_kwarg_requires_the_gap():
    """The sheet is the gap box's mid-plane; without a gap box there is none."""
    import pytest

    with pytest.raises(ValueError, match="emit_port_sheet needs port_gap"):
        MeshGenerator.two_torus_domain(
            separation=SEPARATION,
            major_radius=MAJOR_RADIUS,
            minor_radius=MINOR_RADIUS,
            resolution=RESOLUTION,
            emit_port_sheet=True,
            comm=MPI.COMM_WORLD,
        )
