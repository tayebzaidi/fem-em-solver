"""`PORT-9` step 3, leg (a) — can the lumped-sheet port be instantiated on the
birdcage at all?

Step 3 runs its 4x4 sweep through :class:`LumpedSheetPortSpec`, and that spec
addresses a port by a **facet tag**: the port sheet ``S`` is the gap box's
longitudinal mid-plane, spanning terminal to terminal. On the two-torus fixture
that surface exists because `GEO-16` split each gap box into two halves
(cell tags ``101``/``111`` and ``102``/``112``) and rebuilt the interface between
them as facet tag ``211``/``212`` (`io/mesh.py`, `_interface_facet_tags`).

`birdcage_port_domain` has had no equivalent. Its port regions are whole boxes
(cell tags ``101…100+leg_count``) with no mid-plane and therefore no interface
facet to tag. This module measures that — it does not assume it from a code
read — on the very mesh step 3 budgets from (graded conductors,
``conductor_resolution = 1.6e-3``, the `GEO-15`/`EX-21` rung), so the same run
also prices the mesh and reproduces that rung's record.

Mesh-only: no solve, no port claim, no S-parameter. The output is the input to
the step-3 go/no-go.
"""

from __future__ import annotations

import time

import numpy as np
from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator
from tests.mesh.helpers import global_cell_tag_set
from tests.mesh.test_coil_phantom_conforming import _tag_volume, _total_volume
from tests.mesh.test_birdcage_conductor_sizing import CAD_MASS_GATE
from tests.mesh.test_birdcage_port_tags import (
    AIR_PADDING,
    COIL_LENGTH,
    LEG_COUNT,
    LEG_SPACING,
    LEG_WIDTH,
    PHANTOM_HEIGHT,
    PHANTOM_RADIUS,
    PORT_BOX_SIZE,
    RESOLUTION,
    RING_MINOR_RADIUS,
    RING_RADIUS,
    _analytic_box_volume,
)

# The sizing `PORT-9` step 3 assumes and budgets from (§7 `PORT-9` step 3:
# "*assumes* it (`conductor_resolution = 1.6e-3`; budget from **98 474 cells**,
# mesh 16.74 s)"). Imported constants only where they exist; these two are the
# step-3 entry's own recorded numbers, reproduced here as anchors.
CONDUCTOR_RESOLUTION = 0.4 * RING_MINOR_RADIUS
STEP3_CELL_COUNT_RECORD = 98474
# The mesh is deterministic for fixed inputs, but gmsh version drift moves cell
# counts by a fraction of a percent; 1% is loose enough to survive that and
# tight enough that a different *mesh* cannot hide inside it.
CELL_COUNT_BAND = 0.01

# Every facet tag any lumped-sheet port route could address on this fixture.
# `GEO-16`'s convention is 200+i for the port face groups and 210+i for the
# sheets; the birdcage would follow it with i = 1…leg_count.
CANDIDATE_SHEET_TAGS = tuple(210 + i for i in range(1, LEG_COUNT + 1))


def _global_facet_tag_set(mesh, facet_tags, comm) -> set[int]:
    """Union of `facet_tags.values` over all ranks.

    `facet_tags.values` is rank-local — at ``-n 2`` a tag can live entirely on
    one rank, so the rank-local set is not the mesh's set (the trap `GEO-9`
    step 2b paid for on the cell side).
    """
    local = set() if facet_tags is None else {int(v) for v in np.unique(facet_tags.values)}
    return set().union(*comm.allgather(local))


def test_birdcage_has_no_port_sheet_facet_and_the_step3_mesh_is_priced():
    """Leg (a): the step-3 mesh, priced, with its port-sheet surface absent.

    Three measurements in one mesh:

    1. **Anchor** — the graded rung reproduces its `GEO-15`/`EX-21` record
       (cell count within 1%, CAD-mass ratio at or above the imported 0.95
       gate), so the object measured below is the object step 3 budgets from.
    2. **The blocker** — the global facet-tag set contains none of the sheet
       tags a `LumpedSheetPortSpec` could address.
    3. **Why** — each port region's meshed volume is the *whole* analytic box
       to < 1e-9, i.e. it is one undivided region: there is no mid-plane
       interface for `_interface_facet_tags` to rebuild a sheet from.
    """
    comm = MPI.COMM_WORLD
    started = time.perf_counter()
    mesh, cell_tags, facet_tags, diagnostics = MeshGenerator.birdcage_port_domain(
        leg_count=LEG_COUNT,
        ring_radius=RING_RADIUS,
        leg_width=LEG_WIDTH,
        leg_spacing=LEG_SPACING,
        coil_length=COIL_LENGTH,
        ring_minor_radius=RING_MINOR_RADIUS,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        port_box_size=PORT_BOX_SIZE,
        air_padding=AIR_PADDING,
        resolution=RESOLUTION,
        conductor_resolution=CONDUCTOR_RESOLUTION,
        comm=comm,
        return_diagnostics=True,
    )
    elapsed = time.perf_counter() - started

    port_tags = [100 + i for i in range(1, LEG_COUNT + 1)]
    all_tags = [1, 2, 3, *port_tags]
    assert global_cell_tag_set(mesh, cell_tags) == set(all_tags)

    n_cells = mesh.topology.index_map(3).size_global
    v = {tag: _tag_volume(mesh, cell_tags, tag, comm) for tag in all_tags}
    v_total = _total_volume(mesh, comm)
    cad_conductor = diagnostics["cad_mass_by_group"]["conductor"]
    cad_ratio = v[1] / cad_conductor
    facet_tag_set = _global_facet_tag_set(mesh, facet_tags, comm)

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step 3a] graded birdcage h_c={CONDUCTOR_RESOLUTION:.4e} m: "
            f"cells={n_cells} (record {STEP3_CELL_COUNT_RECORD}, "
            f"ratio {n_cells / STEP3_CELL_COUNT_RECORD:.6f})  "
            f"meshed/CAD conductor={cad_ratio:.6f}  "
            f"mesh={diagnostics['mesh_wall_time_s']:.2f} s  rung={elapsed:.2f} s"
            f"\n[PORT-9 step 3a] global facet tags = "
            f"{sorted(facet_tag_set) if facet_tag_set else '{} (none)'}; "
            f"candidate sheet tags {list(CANDIDATE_SHEET_TAGS)}"
            f"\n[PORT-9 step 3a] port meshed volumes / analytic box: "
            + " ".join(
                "P{}={:.12f}".format(
                    i, v[tag] / (PORT_BOX_SIZE[0] * PORT_BOX_SIZE[1] * PORT_BOX_SIZE[2])
                )
                for i, tag in enumerate(port_tags, start=1)
            ),
            flush=True,
        )

    # 1. Anchor — same mesh as the record.
    assert abs(n_cells / STEP3_CELL_COUNT_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"graded birdcage meshed {n_cells} cells vs the step-3 record "
        f"{STEP3_CELL_COUNT_RECORD} (ratio {n_cells / STEP3_CELL_COUNT_RECORD:.6f}); "
        "outside 1% this is not the mesh step 3 budgets from"
    )
    assert cad_ratio >= CAD_MASS_GATE, (
        f"graded conductor keeps {cad_ratio:.6f} of its CAD mass, below the "
        f"imported {CAD_MASS_GATE} gate — the `GEO-15` rung did not reproduce"
    )
    # The `GEO-9` partition identities, which say the tags mean what they say.
    assert abs(v_total / _analytic_box_volume() - 1.0) < 1e-9
    assert abs(sum(v.values()) / v_total - 1.0) < 1e-9

    # 3. Why (measured before 2 is asserted, because it is the mechanism): each
    #    port region is the entire box, undivided.
    v_port_analytic = PORT_BOX_SIZE[0] * PORT_BOX_SIZE[1] * PORT_BOX_SIZE[2]
    for i, tag in enumerate(port_tags, start=1):
        assert abs(v[tag] / v_port_analytic - 1.0) < 1e-9, (
            f"port P{i} meshed volume {v[tag]:.6e} m^3 vs analytic box "
            f"{v_port_analytic:.6e} m^3; a port region that is *not* the whole "
            "box would mean the mid-plane split already exists"
        )

    # 2. The blocker.
    present = sorted(facet_tag_set & set(CANDIDATE_SHEET_TAGS))
    assert not present, (
        f"birdcage facet tags {present} match the lumped-sheet convention — the "
        "port-sheet mid-plane exists after all and `PORT-9` step 3 is unblocked "
        "on this side; delete this test and run the sweep"
    )
