"""`TH-15` step 3a: the birdcage coil as a *hole*, as a `MeshGenerator` route.

Step 2a landed the same route on the two-torus fixture
(`tests/mesh/test_two_torus_conductor_hole.py`).  This module is that pattern on
the coil the `PORT-9` four-port gate actually drives: the F-small 4-leg gapped
birdcage, every parameter imported from
`tests/mesh/test_birdcage_port_sheets._build` (which is the fixture
`tests/validation/test_port_birdcage_four_port.py` builds its 4x4 on), one
keyword apart —
``MeshGenerator.birdcage_port_domain(..., as_hole=True)``.

Asserted, on the executed route:

    (i)   all four port sheets still carry the `GEO-18` closed-form area
          ``dx*g`` (= 1.12e-04 m^2 on this fixture, taken from the generator's
          own realised ``port_box_size_m`` and never restated) at the imported
          ``SHEET_AREA_BAND`` (1e-9).  The sheets live *between* the two halves
          of a port box, and the box's z-faces are the leg stubs' cut faces, so
          this is the identity that proves the cut did not detach a terminal;
    (ii)  the phantom, air and port-box **CAD** volumes partition the air box
          minus the coil's CAD volume — the `GEO-18` partition identity with the
          conductor mass subtracted from the CAD side, at 1e-9 against the solid
          route's own decomposition and at a measured 1e-7 against the analytic
          box (see the test's own docstring for why the two bands differ).  It
          is a CAD identity, not a meshed one: the meshed hole is the box minus
          an *inscribed* triangulation of the coil, a per-cent-level object;
    (iii) the meshed cavity-wall area (facet group
          :data:`BIRDCAGE_CONDUCTOR_SURFACE_TAG`) equals the solid route's whole
          conductor interface — conductor/air, conductor/phantom and
          conductor/port-half — to ``INTERFACE_AREA_RTOL`` (`GEO-9`'s reduced
          area identity; step 2a read 3.7e-7 on the two-torus);
    (iv)  conductor cell tag ``1`` is absent from the reduced hole census while
          air, phantom and the eight port halves are present, and every census
          sums to the global owned cell count.

The **negative control** is the landed solid route on the identical fixture:
``as_hole=False`` must still mesh to the `PORT-9` record 116 085 cells *with*
tag 1 present, and the hole must be strictly smaller.  The hole's own cell count
has no record and no band — it is *printed*, and this run opens it.

A note on anchor (iii)'s comparand.  The §9 item names "conductor/air +
conductor/phantom"; the executed identity here also includes the
conductor/port-half faces (the two terminal disks per port).  That is not a
loosening — it is the same 1e-5 band on the *complete* boundary of the removed
solid, which is what the cavity wall geometrically is, and it is what step 2a
compared on the two-torus (whose ``SOLID_INTERFACES`` likewise carried the
conductor/gap-box faces (1, 101) / (1, 111) alongside (1, 3)).  Excluding the
terminals would miss 8 disks of pi*r_leg^2 each, ~3.5% of the coil surface.
The air-only subtotal is printed beside it so both readings are on the record.

Scope: a mesh route and its identities.  No solve, no S-matrix, no PEC gate, no
16-leg or F-human variant.  `TH-15` step 3 proper stays open.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.io.mesh import (
    BIRDCAGE_CONDUCTOR_SURFACE_TAG,
    MeshGenerator,
    _interface_facet_tags,
)

# Bands, fixture and layout are imported, never restated (`ANS-1`).
from tests.mesh.test_birdcage_port_sheet_prerequisite import CELL_COUNT_BAND
from tests.mesh.test_birdcage_leg_offset import SHEET_AREA_BAND
from tests.mesh.test_birdcage_leg_gaps import _analytic_box_volume
from tests.mesh.test_birdcage_port_sheets import (
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
    _build,
)
from tests.mesh.test_birdcage_port_tags import LEG_COUNT

# The reduction helpers step 0/2a scored the two-torus with, so the birdcage is
# measured by the identical machinery.  `_census` is only ever applied to an
# **owned** slice — see `_owned_census`.
from tests.mesh.probe_two_torus_conductor_hole import (
    _census,
    _exterior_facet_area,
    _facet_area,
)

# The `PORT-9` record of this exact solid fixture: 116 085 cells on the 0.11
# image (`20260905T201151Z_EX-49.log`, and the `GEO-19` step-B re-record in
# `tests/validation/test_port_birdcage_four_port.py`).  A version-tagged
# environment-dependent cell count under the (1*) licence, judged at the
# imported 1% band.
SOLID_CELL_RECORD = 116085

# Cell tag of the meshed coil in the solid route (`birdcage_port_domain` group
# 1); the hole route must not emit it at all.
CONDUCTOR_CELL_TAG = 1

# The hole's cavity wall against the solid route's conductor interface.  Step 2a
# measured 3.70e-07 relative through this same reduction on the two-torus and
# set 1e-5, ~30x that reading and the band `GEO-9` gates the reduced-area
# identity at; carried over unchanged.
INTERFACE_AREA_RTOL = 1.0e-5

# Facet tag for the reconstructed solid-route conductor interface.  Interior
# facet groups are rebuilt from cell tags on the dolfinx side (`GEO-16`).
SOLID_CONDUCTOR_IFACE = 900
SOLID_CONDUCTOR_AIR_IFACE = 901

AIR_CELL_TAG = 2
PHANTOM_CELL_TAG = 3

# The exact band the `GEO-18`/`GEO-20` partition identities use for a CAD sum
# whose terms are the same OCC numbers on both sides.
EXACT = 1.0e-9

# ...and the band for a CAD sum compared with the *analytic* box.  Set from
# measurement, not guessed: see `test_the_hole_partitions_the_box_minus_the_coil`
# — the solid route (which this chunk does not touch) misses the analytic box by
# 3.379e-08 relative because OCC integrates the tori and cylinders numerically.
CAD_ANALYTIC_BAND = 1.0e-7


def _owned_census(msh, tags, dim, comm):
    """Per-tag global counts over **owned** entities only (`OPS-39`).

    The fixture is partitioned with ``GhostMode.shared_facet``, so a rank's
    ``MeshTags`` also carries the ghost layer and a naive cross-rank sum counts
    every shared entity once per rank holding it.  Masking on ``size_local`` is
    what makes the census width-invariant, and so comparable with a record.
    """
    n_owned = msh.topology.index_map(dim).size_local
    owned = np.asarray(tags.indices) < n_owned
    return _census(np.asarray(tags.values)[owned], comm)


def _sheet_areas(msh, cell_tags, ports, comm):
    """Meshed area of each port's mid-plane sheet, from the cell tags."""
    sheet_tags = _interface_facet_tags(
        msh,
        cell_tags,
        {SHEET_IFACE + i: (PORT_LOWER + i, PORT_UPPER + i) for i in ports},
    )
    return {i: _facet_area(msh, sheet_tags, SHEET_IFACE + i, comm) for i in ports}


def _measure(msh, cell_tags, comm):
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()
    ports = list(range(1, LEG_COUNT + 1))
    return {
        "n_cells": comm.allreduce(
            msh.topology.index_map(tdim).size_local, op=MPI.SUM
        ),
        "n_verts": comm.allreduce(msh.topology.index_map(0).size_local, op=MPI.SUM),
        "cells": _owned_census(msh, cell_tags, tdim, comm),
        "sheet_area": _sheet_areas(msh, cell_tags, ports, comm),
    }


@pytest.fixture(scope="module")
def routes():
    """Both meshes, built once: ``as_hole=True`` and the solid control."""
    comm = MPI.COMM_WORLD
    ports = list(range(1, LEG_COUNT + 1))

    hole_msh, hole_cells, hole_facets, hole_diag, t_hole = _build(
        emit_port_sheets=True, as_hole=True
    )
    hole = _measure(hole_msh, hole_cells, comm)
    hole["diag"] = hole_diag
    hole["t_mesh"] = t_hole
    hole["cavity_area"] = _exterior_facet_area(
        hole_msh, hole_facets, BIRDCAGE_CONDUCTOR_SURFACE_TAG, comm
    )
    hole["cavity_facets"] = comm.allreduce(
        int(
            np.count_nonzero(
                np.asarray(hole_facets.values) == BIRDCAGE_CONDUCTOR_SURFACE_TAG
            )
        ),
        op=MPI.SUM,
    )

    solid_msh, solid_cells, _solid_facets, solid_diag, t_solid = _build(
        emit_port_sheets=True
    )
    solid = _measure(solid_msh, solid_cells, comm)
    solid["diag"] = solid_diag
    solid["t_mesh"] = t_solid

    # The whole boundary of the meshed coil: air, phantom and both halves of
    # every port box (the terminal disks).  The air-only subtotal is carried
    # alongside so both readings of anchor (iii) are printed.
    conductor_pairs = [(CONDUCTOR_CELL_TAG, AIR_CELL_TAG),
                       (CONDUCTOR_CELL_TAG, PHANTOM_CELL_TAG)]
    for i in ports:
        conductor_pairs.append((CONDUCTOR_CELL_TAG, PORT_LOWER + i))
        conductor_pairs.append((CONDUCTOR_CELL_TAG, PORT_UPPER + i))
    # One call per group: a facet belongs to both, and `_interface_facet_tags`
    # concatenates its groups rather than merging duplicate indices.
    iface = _interface_facet_tags(
        solid_msh, solid_cells, {SOLID_CONDUCTOR_IFACE: tuple(conductor_pairs)}
    )
    iface_air = _interface_facet_tags(
        solid_msh,
        solid_cells,
        {
            SOLID_CONDUCTOR_AIR_IFACE: (
                (CONDUCTOR_CELL_TAG, AIR_CELL_TAG),
                (CONDUCTOR_CELL_TAG, PHANTOM_CELL_TAG),
            )
        },
    )
    solid["interface_area"] = _facet_area(
        solid_msh, iface, SOLID_CONDUCTOR_IFACE, comm
    )
    solid["interface_area_air"] = _facet_area(
        solid_msh, iface_air, SOLID_CONDUCTOR_AIR_IFACE, comm
    )
    solid["interface_facets"] = comm.allreduce(
        int(np.count_nonzero(np.asarray(iface.values) == SOLID_CONDUCTOR_IFACE)),
        op=MPI.SUM,
    )

    if comm.rank == 0:
        print(
            f"\n[TH-15 step 3a] hole : {hole['n_cells']} cells "
            f"{hole['n_verts']} vertices, census {hole['cells']}, "
            f"cavity {hole['cavity_facets']} facets, mesh {hole['t_mesh']:.2f} s"
            f"\n[TH-15 step 3a] solid: {solid['n_cells']} cells "
            f"{solid['n_verts']} vertices, census {solid['cells']}, "
            f"mesh {solid['t_mesh']:.2f} s"
            f"\n[TH-15 step 3a] hole CAD masses {hole['diag']['cad_mass_by_group']}"
            f"\n[TH-15 step 3a] cavity CAD {hole['diag']['conductor_cavity_cad']}",
            flush=True,
        )
    return hole, solid


def test_the_hole_route_meshes_and_the_solid_control_holds_its_record(routes):
    """(the control) 116 085 solid cells at the imported band; hole < solid.

    The hole's own count is a **first measurement** — printed, no band, no
    record: this run opens the version-tagged (1*) record for it.
    """
    hole, solid = routes
    ratio = solid["n_cells"] / SOLID_CELL_RECORD
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[TH-15 step 3a] cells: hole {hole['n_cells']} (first measurement, "
            f"no band) vs solid {solid['n_cells']} / {SOLID_CELL_RECORD} = "
            f"{ratio:.6f} (band {CELL_COUNT_BAND}); hole/solid = "
            f"{hole['n_cells'] / solid['n_cells']:.6f}",
            flush=True,
        )
    assert abs(ratio - 1.0) < CELL_COUNT_BAND, (
        f"as_hole=False meshed {solid['n_cells']} cells against the `PORT-9` "
        f"record {SOLID_CELL_RECORD} (ratio {ratio:.6f}); the additive keyword "
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
        f"({solid['n_cells']}); cutting the coil out must remove the cells "
        "that filled it"
    )


def test_the_hole_route_drops_the_conductor_cell_tag(routes):
    """(iv): tag 1 gone from the hole, present in the solid control."""
    hole, solid = routes
    ports = list(range(1, LEG_COUNT + 1))
    expected = {AIR_CELL_TAG, PHANTOM_CELL_TAG}
    expected |= {PORT_LOWER + i for i in ports} | {PORT_UPPER + i for i in ports}
    assert set(hole["cells"]) == expected, (
        f"as_hole=True cell census is {hole['cells']}; the meshed set must be "
        f"air, phantom and the {2 * LEG_COUNT} port halves and nothing else"
    )
    assert CONDUCTOR_CELL_TAG not in hole["cells"], (
        f"conductor cell tag {CONDUCTOR_CELL_TAG} survives in the hole census "
        f"{hole['cells']} — the coil is still meshed"
    )
    assert CONDUCTOR_CELL_TAG in solid["cells"], (
        f"conductor cell tag {CONDUCTOR_CELL_TAG} is missing from the *solid* "
        f"census {solid['cells']}; the negative control is not a control"
    )


def test_the_hole_route_keeps_all_four_port_sheets_exact(routes):
    """(i): every sheet still meshes the closed-form ``dx*g``."""
    hole, solid = routes
    for label, route in (("hole", hole), ("solid", solid)):
        dx, _dy, dz = route["diag"]["port_box_size_m"]
        nominal_area = dx * dz
        for i in sorted(route["sheet_area"]):
            area = route["sheet_area"][i]
            assert np.isfinite(area), (
                f"{label} route has no facets in sheet group {SHEET_IFACE + i}"
            )
            dev = abs(area / nominal_area - 1.0)
            if MPI.COMM_WORLD.rank == 0:
                print(
                    f"[TH-15 step 3a] {label} sheet P{i}: area={area:.9e} "
                    f"nominal={nominal_area:.9e} rel_dev={dev:.3e} "
                    f"(band {SHEET_AREA_BAND:.0e})",
                    flush=True,
                )
            assert dev < SHEET_AREA_BAND, (
                f"{label} port sheet P{i} meshes {area:.9e} m^2 against the "
                f"closed-form dx*g {nominal_area:.9e} ({dev:.3e} relative, band "
                f"{SHEET_AREA_BAND:.0e}) — on the hole route this is the cut "
                "having detached a terminal from its port box"
            )


def test_the_hole_partitions_the_box_minus_the_coil(routes):
    """(ii): the `GEO-18` CAD partition identity, coil subtracted.

    Two readings, and they are not the same identity:

    * against the **solid route's own** CAD decomposition the cut is exact —
      the hole's groups plus the conductor group reproduce the solid's groups
      at ``EXACT`` (1e-9).  This is the identity that says the cut removed the
      coil and nothing else, because both sides are the same OCC numbers;
    * against the **analytic** air box the sum carries OCC's own mass
      quadrature on the curved coil.  Measured 2026-09-06 at `-n 2` on this
      fixture (``20260906T213704Z_TH-15.log:2647``, first window): the *solid*
      route — untouched by this chunk, no cut in it at all — misses the
      analytic box by 3.379e-08 relative, and the hole misses ``box - coil`` by
      3.408e-08, i.e. the same ~3.9e-10 m^3 absolute, which is 3.9e-06 of the
      coil's own 9.939e-05 m^3.  1e-09 was the wrong bound for a CAD sum that
      contains tori and cylinders; ``CAD_ANALYTIC_BAND`` is set from that
      measurement, applies to **both** routes equally, and is still four orders
      tighter than any mesh-level effect.
    """
    hole, solid = routes
    box = _analytic_box_volume(hole["diag"]["port_box_size_m"][1])
    coil = solid["diag"]["cad_mass_by_group"]["conductor"]
    hole_sum = sum(hole["diag"]["cad_mass_by_group"].values())
    solid_sum = sum(solid["diag"]["cad_mass_by_group"].values())
    cut_ratio = (hole_sum + coil) / solid_sum
    hole_ratio = hole_sum / (box - coil)
    solid_ratio = solid_sum / box
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[TH-15 step 3a] CAD partition: hole groups {hole_sum:.12e} + coil "
            f"{coil:.12e} vs solid groups {solid_sum:.12e}, ratio "
            f"{cut_ratio:.12f} (band {EXACT:.0e}); against the analytic box "
            f"{box:.12e}: hole/(box-coil) {hole_ratio:.12f}, solid/box "
            f"{solid_ratio:.12f} (band {CAD_ANALYTIC_BAND:.0e})",
            flush=True,
        )
    assert abs(cut_ratio - 1.0) < EXACT, (
        f"the hole's CAD volumes sum to {hole_sum:.12e} m^3, and with the "
        f"conductor's {coil:.12e} m^3 added back they give {hole_sum + coil:.12e} "
        f"against the solid route's {solid_sum:.12e} (ratio {cut_ratio:.12f}); "
        "the cut removed something other than exactly the conductor"
    )
    assert abs(hole_ratio - 1.0) < CAD_ANALYTIC_BAND, (
        f"the hole's CAD volumes sum to {hole_sum:.12e} m^3 against the analytic "
        f"air box minus the coil {box - coil:.12e} m^3 "
        f"(ratio {hole_ratio:.12f}, band {CAD_ANALYTIC_BAND:.0e})"
    )
    assert abs(solid_ratio - 1.0) < CAD_ANALYTIC_BAND, (
        f"the solid control's CAD groups sum to {solid_sum:.12e} m^3 against "
        f"the analytic air box {box:.12e} (ratio {solid_ratio:.12f}, band "
        f"{CAD_ANALYTIC_BAND:.0e}) — the control moved, not the hole"
    )


def test_the_cavity_wall_is_the_solid_routes_conductor_interface(routes):
    """(iii): the reduced area identity between the two routes."""
    hole, solid = routes
    cavity = hole["cavity_area"]
    interface = solid["interface_area"]
    assert np.isfinite(cavity), (
        f"the hole has no facets in group {BIRDCAGE_CONDUCTOR_SURFACE_TAG}"
    )
    dev = abs(cavity / interface - 1.0)
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[TH-15 step 3a] cavity tag {BIRDCAGE_CONDUCTOR_SURFACE_TAG}: "
            f"{hole['cavity_facets']} facets area={cavity:.9e} vs the solid "
            f"conductor interface {interface:.9e} "
            f"({solid['interface_facets']} facets; air+phantom subtotal "
            f"{solid['interface_area_air']:.9e}, terminals "
            f"{interface - solid['interface_area_air']:.9e}) rel_dev={dev:.3e} "
            f"(band {INTERFACE_AREA_RTOL:.0e})",
            flush=True,
        )
    assert dev < INTERFACE_AREA_RTOL, (
        f"the cavity wall measures {cavity:.9e} m^2 against the solid route's "
        f"conductor interface {interface:.9e} ({dev:.3e} relative, band "
        f"{INTERFACE_AREA_RTOL:.0e}) — the surface group is not the surface the "
        "meshed coil presented"
    )


def test_as_hole_requires_the_port_sheets():
    """The keyword's own contract, and it costs no mesh."""
    with pytest.raises(ValueError, match="as_hole"):
        MeshGenerator.birdcage_port_domain(emit_port_sheets=False, as_hole=True)
