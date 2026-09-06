"""`TH-15` step 2a: the two-torus conductor as a *hole*, as a `MeshGenerator` route.

Step 0 proved the geometry meshes, but on a probe-local copy of the OCC
sequence (``tests/mesh/probe_two_torus_conductor_hole.py::_hole_build``).  Step
2's ``Re P_in = 0`` identity needs a route the `PORT-1` package can call, so
that sequence now lives behind the additive keyword
``MeshGenerator.two_torus_domain(..., as_hole=True)``.  This module asserts, on
the executed route, exactly what step 0 measured on the probe:

    (i)   the hole meshes to step 0's **161 461** cells at the imported
          ``CELL_COUNT_BAND`` (a version-tagged record under the (1*) licence);
    (ii)  conductor cell tags ``1`` / ``2`` are **absent** from the reduced cell
          census, while air ``3`` and the four gap-box halves are present;
    (iii) both port sheets still carry ``nominal_area`` to the imported
          ``SHEET_AREA_BAND`` (`GEO-18`'s EXACT band, 1e-9);
    (iv)  the tag-301 cavity area equals the ``as_hole=False`` route's
          conductor/air interface area to ``INTERFACE_AREA_RTOL`` — the reduced
          area identity, and the assertion that the port the hole exposes is
          the same surface the solid route's conductor presented.

The **negative control** is the landed solid route on the identical fixture:
`as_hole=False` must still mesh to the 0.11 record 184 176 cells *with* tags 1
and 2 present, and the hole must be strictly smaller.  Both meshes are built
once, in one module-scoped fixture; every census is reduced across ranks before
it is asserted (``cell_tags.values`` is rank-local).

Scope: a mesh route and its identities.  No solve, no ``Re P_in`` (step 2), no
birdcage hole (step 3).
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.io.mesh import (
    MeshGenerator,
    TWO_TORUS_CONDUCTOR_SURFACE_TAG,
    _interface_facet_tags,
)

# Bands and fixture arguments are imported, never restated (`ANS-1`).
from tests.mesh.test_birdcage_port_sheet_prerequisite import CELL_COUNT_BAND
from tests.mesh.test_birdcage_leg_offset import SHEET_AREA_BAND
from tests.validation.test_port_gap_voltage_impedance import (
    AIR_PADDING,
    GAP_ANGLE,
    GAP_ARC_RESOLUTION,
    GAP_BURIAL,
    GAP_OVERHANG,
    H_FAR,
    H_WIRE,
    MAJOR_RADIUS,
    MINOR_RADIUS,
    SEPARATION,
    _gap_half_extents,
)
from tests.validation.test_port_lumped_two_torus import _build

# The area helpers step 0 used, imported from the probe so the executed route is
# scored by the identical reduction.  `_census` is imported too, but only ever
# applied to an **owned** slice — see `_owned_census` below.
from tests.mesh.probe_two_torus_conductor_hole import (
    _census,
    _exterior_facet_area,
    _facet_area,
)

# --- step 0's records (`20260905T051023Z_TH-15.log:507–513` hole,
# `20260905T050518Z_TH-15.log:942–952` solid), both on image tag v0.11.0
# (dolfinx 0.11.0.post0, gmsh 4.15.2).  Version-tagged environment-dependent
# cell counts under the (1*) licence, judged at the imported 1% band; the probe
# reproduced each of them bit-identically inside one image.
HOLE_CELL_RECORD = 161461
SOLID_CELL_RECORD = 184176            # the landed 0.11 record, unchanged
SOLID_WIRE_CELL_RECORDS = {1: 9471, 2: 9348}

# The hole's cavity wall against the solid route's conductor/air interface.
# Step 0 measured 1.515910101e-02 (hole, tag 301) against
# 7.579509813e-03 + 7.579585585e-03 = 1.5159095398e-02 (solid, tags 311+312),
# i.e. **3.70e-07** relative.  1e-5 is ~30x that reading and is the same
# reduced-area identity `GEO-9` gates on.
INTERFACE_AREA_RTOL = 1.0e-5

# The solid route's conductor/air interface, rebuilt from the distributed cell
# tags: every facet between a conductor cell and air or gap.
SOLID_INTERFACES = {
    311: ((1, 3), (1, 101), (1, 111)),
    312: ((2, 3), (2, 102), (2, 112)),
}


def _hole_build(comm):
    """`_build`'s fixture with the conductors cut out — one keyword apart."""
    t0 = time.perf_counter()
    msh, cell_tags, facet_tags = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=H_FAR,
        air_padding=AIR_PADDING,
        wire_resolution=H_WIRE,
        far_resolution=H_FAR,
        port_gap=True,
        gap_angle=GAP_ANGLE,
        gap_burial=GAP_BURIAL,
        gap_overhang=GAP_OVERHANG,
        gap_arc_resolution=GAP_ARC_RESOLUTION,
        emit_port_sheet=True,
        as_hole=True,
        comm=comm,
    )
    return msh, cell_tags, facet_tags, time.perf_counter() - t0


def _owned_census(msh, tags, dim, comm):
    """Per-tag global counts over **owned** entities only.

    This fixture is partitioned with ``GhostMode.shared_facet``, so a rank's
    ``MeshTags`` also carries the ghost layer: summing ``tags.values`` across
    ranks counts every shared entity twice, and the per-tag census then depends
    on the rank width (measured 2026-09-06 at ``-n 2``: the solid route's
    conductor tags read 9556 / 9448 against step 0's ``-n 1`` 9471 / 9348, and
    the tag sum overshot the global cell count by 2972 = the ghost layer).
    Masking on ``size_local`` is the same discipline the global cell count
    already uses, and it makes the census width-invariant — which is what lets
    it be compared with a record at all.
    """
    n_owned = msh.topology.index_map(dim).size_local
    owned = np.asarray(tags.indices) < n_owned
    return _census(np.asarray(tags.values)[owned], comm)


def _measure(msh, cell_tags, facet_tags, comm):
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()
    out = {
        "n_cells": comm.allreduce(
            msh.topology.index_map(tdim).size_local, op=MPI.SUM
        ),
        "n_verts": comm.allreduce(msh.topology.index_map(0).size_local, op=MPI.SUM),
        "cells": _owned_census(msh, cell_tags, tdim, comm),
        "facets": _owned_census(msh, facet_tags, tdim - 1, comm),
    }
    out["sheet_area"] = {
        tag: _facet_area(msh, facet_tags, tag, comm) for tag in (211, 212)
    }
    return out


@pytest.fixture(scope="module")
def routes():
    """Both meshes, built once: `as_hole=True` and the solid negative control."""
    comm = MPI.COMM_WORLD

    hole_msh, hole_cells, hole_facets, t_hole = _hole_build(comm)
    hole = _measure(hole_msh, hole_cells, hole_facets, comm)
    hole["t_mesh"] = t_hole
    hole["cavity_area"] = _exterior_facet_area(
        hole_msh, hole_facets, TWO_TORUS_CONDUCTOR_SURFACE_TAG, comm
    )
    hole["cavity_facets"] = hole["facets"].get(TWO_TORUS_CONDUCTOR_SURFACE_TAG, 0)

    solid_msh, solid_cells, solid_facets, t_solid = _build(comm)
    solid = _measure(solid_msh, solid_cells, solid_facets, comm)
    solid["t_mesh"] = t_solid
    cond_ft = _interface_facet_tags(solid_msh, solid_cells, SOLID_INTERFACES)
    cond_census = _owned_census(
        solid_msh, cond_ft, solid_msh.topology.dim - 1, comm
    )
    solid["interface_facets"] = {
        1: cond_census.get(311, 0), 2: cond_census.get(312, 0)
    }
    solid["interface_area"] = {
        1: _facet_area(solid_msh, cond_ft, 311, comm),
        2: _facet_area(solid_msh, cond_ft, 312, comm),
    }

    if comm.rank == 0:
        print(
            f"\n[TH-15 step 2a] hole : {hole['n_cells']} cells "
            f"{hole['n_verts']} vertices, cell census {hole['cells']}, "
            f"facet census {hole['facets']}, mesh {hole['t_mesh']:.2f} s"
            f"\n[TH-15 step 2a] solid: {solid['n_cells']} cells "
            f"{solid['n_verts']} vertices, cell census {solid['cells']}, "
            f"facet census {solid['facets']}, mesh {solid['t_mesh']:.2f} s",
            flush=True,
        )
    return hole, solid


def test_hole_route_reproduces_the_step0_cell_record(routes):
    """(i) + the control: 161 461 hole cells, 184 176 solid, hole < solid."""
    hole, solid = routes
    hole_ratio = hole["n_cells"] / HOLE_CELL_RECORD
    solid_ratio = solid["n_cells"] / SOLID_CELL_RECORD
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[TH-15 step 2a] cell records: hole {hole['n_cells']} / "
            f"{HOLE_CELL_RECORD} = {hole_ratio:.6f}, solid {solid['n_cells']} / "
            f"{SOLID_CELL_RECORD} = {solid_ratio:.6f} (band {CELL_COUNT_BAND})",
            flush=True,
        )
    assert abs(hole_ratio - 1.0) < CELL_COUNT_BAND, (
        f"as_hole=True meshed {hole['n_cells']} cells against step 0's record "
        f"{HOLE_CELL_RECORD} (ratio {hole_ratio:.6f}); outside the imported "
        f"{CELL_COUNT_BAND} band this is not the mesh step 0 measured"
    )
    assert abs(solid_ratio - 1.0) < CELL_COUNT_BAND, (
        f"as_hole=False meshed {solid['n_cells']} cells against the 0.11 record "
        f"{SOLID_CELL_RECORD} (ratio {solid_ratio:.6f}); the additive keyword "
        "moved the landed fixture, which is the one thing it may not do"
    )
    for label, route in (("hole", hole), ("solid", solid)):
        assert sum(route["cells"].values()) == route["n_cells"], (
            f"the {label} route's per-tag census sums to "
            f"{sum(route['cells'].values())} against {route['n_cells']} owned "
            "cells — the reduction is counting the ghost layer, so no per-tag "
            "count here is width-invariant"
        )
    assert hole["n_cells"] < solid["n_cells"], (
        f"the hole ({hole['n_cells']} cells) is not smaller than the solid "
        f"({solid['n_cells']}); cutting the conductors out must remove the "
        "cells that filled them"
    )


def test_hole_route_drops_the_conductor_cell_tags(routes):
    """(ii): tags 1 / 2 gone from the hole, present in the solid control."""
    hole, solid = routes
    assert set(hole["cells"]) == {3, 101, 102, 111, 112}, (
        f"as_hole=True cell census is {hole['cells']}; the meshed set must be "
        "air (3) plus the four gap-box halves and nothing else"
    )
    for tag in (1, 2):
        assert tag not in hole["cells"], (
            f"conductor cell tag {tag} survives in the hole census "
            f"{hole['cells']} — the conductor is still meshed"
        )
        assert tag in solid["cells"], (
            f"conductor cell tag {tag} is missing from the *solid* census "
            f"{solid['cells']}; the negative control is not a control"
        )
        ratio = solid["cells"][tag] / SOLID_WIRE_CELL_RECORDS[tag]
        assert abs(ratio - 1.0) < CELL_COUNT_BAND, (
            f"solid conductor tag {tag} holds {solid['cells'][tag]} cells "
            f"against step 0's {SOLID_WIRE_CELL_RECORDS[tag]} "
            f"(ratio {ratio:.6f}, band {CELL_COUNT_BAND})"
        )


def test_hole_route_keeps_both_port_sheets_exact(routes):
    """(iii): 211 / 212 still carry the nominal gap-box cross-section."""
    hole, solid = routes
    half_xz, half_y = _gap_half_extents()
    nominal_area = 4.0 * half_xz * half_y
    for label, route in (("hole", hole), ("solid", solid)):
        for tag in (211, 212):
            area = route["sheet_area"][tag]
            assert np.isfinite(area), (
                f"{label} route has no facets in sheet group {tag}: census "
                f"{route['facets']}"
            )
            dev = abs(area / nominal_area - 1.0)
            if MPI.COMM_WORLD.rank == 0:
                print(
                    f"[TH-15 step 2a] {label} sheet {tag}: "
                    f"{route['facets'].get(tag, 0)} facets area={area:.9e} "
                    f"nominal={nominal_area:.9e} rel_dev={dev:.3e} "
                    f"(band {SHEET_AREA_BAND:.0e})",
                    flush=True,
                )
            assert dev < SHEET_AREA_BAND, (
                f"{label} port sheet {tag} meshes {area:.9e} m^2 against the "
                f"nominal {nominal_area:.9e} ({dev:.3e} relative, band "
                f"{SHEET_AREA_BAND:.0e}) — the mid-plane is not the gap box's "
                "cross-section"
            )


def test_cavity_area_equals_the_solid_routes_conductor_interface(routes):
    """(iv): tag 301 is the same surface the solid route's conductor presented."""
    hole, solid = routes
    cavity = hole["cavity_area"]
    interface = solid["interface_area"][1] + solid["interface_area"][2]
    assert np.isfinite(cavity), (
        f"the hole has no facets in group {TWO_TORUS_CONDUCTOR_SURFACE_TAG}: "
        f"census {hole['facets']}"
    )
    dev = abs(cavity / interface - 1.0)
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[TH-15 step 2a] cavity tag {TWO_TORUS_CONDUCTOR_SURFACE_TAG}: "
            f"{hole['cavity_facets']} facets area={cavity:.9e} vs the solid "
            f"conductor interface {interface:.9e} "
            f"({solid['interface_area'][1]:.9e} + "
            f"{solid['interface_area'][2]:.9e}, "
            f"{solid['interface_facets'][1]} + {solid['interface_facets'][2]} "
            f"facets) rel_dev={dev:.3e} (band {INTERFACE_AREA_RTOL:.0e})",
            flush=True,
        )
    assert dev < INTERFACE_AREA_RTOL, (
        f"the cavity wall measures {cavity:.9e} m^2 against the solid route's "
        f"conductor/air interface {interface:.9e} ({dev:.3e} relative, band "
        f"{INTERFACE_AREA_RTOL:.0e}) — the MeshGenerator port exposes a "
        "different surface from the one the conductor presented"
    )


def test_as_hole_requires_the_gapped_sheet_fixture():
    """The keyword's own contract, and it costs no mesh."""
    with pytest.raises(ValueError, match="as_hole"):
        MeshGenerator.two_torus_domain(as_hole=True)
    with pytest.raises(ValueError, match="as_hole"):
        MeshGenerator.two_torus_domain(port_gap=True, as_hole=True)
