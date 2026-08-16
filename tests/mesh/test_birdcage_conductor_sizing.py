"""`GEO-15` step 1 — is graded birdcage conductor sizing a `PORT-9` prerequisite?

The birdcage mesh keeps only **0.7091** of the conductor's *analytic sum*
(`GEO-9` step 2b) under the single global ``setSize = 0.015``. Two causes are
tangled in that one number: the analytic ring+leg sum double-counts the eight
leg∩ring junctions, and 0.015 m is ~10x coarser than `GEO-8`'s measured rule
(``wire_resolution <= 0.4 x minor_radius`` = 0.0016 m here). This module
separates them by changing the denominator: the **CAD (occ) mass** of the
conductor physical group, which counts every fragment piece exactly once and
therefore tends to 1 under refinement. Against that denominator the deficit is
resolution alone, so grading is measurable.

Mesh-only: no solve, no port claim. The output feeds `PORT-9` step 3's gate.
"""

from __future__ import annotations

import time

import numpy as np
from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator
from tests.mesh.helpers import global_cell_tag_set
from tests.mesh.test_coil_phantom_conforming import _tag_volume, _total_volume
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

# The `GEO-8` rule at this fixture's ring minor radius: 0.4 x 0.004 = 0.0016 m.
# The ladder approaches it from above so a cell explosion is visible one rung
# before it costs the tier ceiling; the finest rung that completes carries the
# gate.
CONDUCTOR_RUNGS = (2.0 * 0.4 * RING_MINOR_RADIUS, 0.4 * RING_MINOR_RADIUS)

# Standard tier is 180 s and this module owns the whole command. Stop laddering
# once the elapsed budget is gone and gate on the finest rung that finished —
# per the `GEO-15` entry, an unreachable 0.95 inside the tier *is* the answer,
# and it has to be reported as a measured frontier rather than a timeout.
LADDER_BUDGET_S = 300.0

CAD_MASS_GATE = 0.95


def _mesh(conductor_resolution=None):
    """One rung: mesh, tags, CAD-mass diagnostics, cell count, wall time."""
    comm = MPI.COMM_WORLD
    started = time.perf_counter()
    mesh, cell_tags, _, diagnostics = MeshGenerator.birdcage_port_domain(
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
        conductor_resolution=conductor_resolution,
        comm=comm,
        return_diagnostics=True,
    )
    elapsed = time.perf_counter() - started

    port_tags = [100 + i for i in range(1, LEG_COUNT + 1)]
    all_tags = [1, 2, 3, *port_tags]
    # Rank-local read; `global_cell_tag_set` reduces (at -n 2 rank 0 owns no
    # P2/P3 cells — `GEO-9` step 2b paid for this once already).
    assert global_cell_tag_set(mesh, cell_tags) == set(all_tags)

    v = {tag: _tag_volume(mesh, cell_tags, tag, comm) for tag in all_tags}
    return {
        "h_c": conductor_resolution,
        "n_cells": mesh.topology.index_map(3).size_global,
        "wall_time_s": elapsed,
        "mesh_wall_time_s": diagnostics["mesh_wall_time_s"],
        "cad_mass": diagnostics["cad_mass_by_group"],
        "v": v,
        "v_total": _total_volume(mesh, comm),
        "port_tags": port_tags,
        "all_tags": all_tags,
    }


def _check_geo9_identities(rung, comm):
    """The `GEO-9` identities, unmoved: they must survive the sizing change.

    Grading changes only element sizes, so a partition identity that moves is a
    defect in the size field (a piece lost its group, or a region got meshed
    twice), not a resolution effect.
    """
    v_box = _analytic_box_volume()
    v = rung["v"]
    v_port_analytic = PORT_BOX_SIZE[0] * PORT_BOX_SIZE[1] * PORT_BOX_SIZE[2]

    assert abs(rung["v_total"] / v_box - 1.0) < 1e-9, (
        f"h_c={rung['h_c']}: total mesh volume {rung['v_total']:.6e} m^3 vs "
        f"analytic box {v_box:.6e} m^3 (ratio {rung['v_total'] / v_box:.12f}); "
        "above 1 means a region is meshed twice, i.e. the fragment did not conform"
    )
    assert abs(sum(v.values()) / rung["v_total"] - 1.0) < 1e-9, (
        f"h_c={rung['h_c']}: tagged volumes sum to {sum(v.values()):.6e} m^3 of "
        f"a {rung['v_total']:.6e} m^3 mesh; a deficit means a fragment piece "
        "carries no physical group"
    )
    for i, tag in enumerate(rung["port_tags"], start=1):
        assert abs(v[tag] / v_port_analytic - 1.0) < 1e-9, (
            f"h_c={rung['h_c']}: port P{i} meshed volume {v[tag]:.6e} m^3 vs "
            f"analytic box {v_port_analytic:.6e} m^3 (ratio "
            f"{v[tag] / v_port_analytic:.12f}); the port region is a rectangular "
            "box, so a linear-tet mesh of it is exact to roundoff"
        )


def test_graded_conductor_sizing_recovers_the_cad_mass():
    """Gate: graded conductor meshed volume >= 0.95 x its CAD (occ) mass.

    Negative control: the baseline global-``setSize`` mesh re-measured in-run on
    the *same* CAD-mass denominator. Its distance below the band is the effect
    size; the 0.7091-vs-analytic-sum number on record cannot serve, because it
    is a different denominator.
    """
    comm = MPI.COMM_WORLD

    baseline = _mesh(conductor_resolution=None)
    _check_geo9_identities(baseline, comm)

    v_conductor_analytic = 2.0 * (
        2.0 * np.pi**2 * RING_RADIUS * RING_MINOR_RADIUS**2
    ) + LEG_COUNT * np.pi * (0.5 * LEG_WIDTH) ** 2 * COIL_LENGTH
    cad_conductor = baseline["cad_mass"]["conductor"]

    rungs = [baseline]
    started = time.perf_counter()
    for h_c in CONDUCTOR_RUNGS:
        remaining = LADDER_BUDGET_S - (time.perf_counter() - started)
        if rungs[-1]["h_c"] is not None and remaining < 2.0 * rungs[-1]["wall_time_s"]:
            if comm.rank == 0:
                print(
                    f"[GEO-15] ladder stopped before h_c={h_c:.6e} m: "
                    f"{remaining:.1f} s of the {LADDER_BUDGET_S:.0f} s budget left, "
                    f"previous rung cost {rungs[-1]['wall_time_s']:.1f} s",
                    flush=True,
                )
            break
        rung = _mesh(conductor_resolution=h_c)
        _check_geo9_identities(rung, comm)
        rungs.append(rung)

    # The CAD mass is a property of the CAD, not of the mesh: every rung must
    # report the same denominator, or the fragment changed under the size field
    # and no ratio below means anything.
    for rung in rungs:
        assert abs(rung["cad_mass"]["conductor"] / cad_conductor - 1.0) < 1e-12, (
            f"h_c={rung['h_c']}: conductor CAD mass {rung['cad_mass']['conductor']:.9e} "
            f"m^3 != baseline {cad_conductor:.9e} m^3; the size field must not "
            "change the geometry"
        )

    if comm.rank == 0:
        print(
            f"\n[GEO-15 step 1] conductor CAD (occ) mass = {cad_conductor:.9e} m^3; "
            f"analytic ring+leg sum = {v_conductor_analytic:.9e} m^3 "
            f"(CAD/analytic = {cad_conductor / v_conductor_analytic:.6f}, "
            "below 1 by the 8 leg-ring junctions the sum double-counts)"
            + "".join(
                "\n  h_c={:>11}  cells={:>8d}  meshed/CAD={:.6f}  meshed/analytic={:.6f}"
                "  mesh={:6.2f} s  rung={:6.2f} s".format(
                    "global" if r["h_c"] is None else f"{r['h_c']:.4e}",
                    r["n_cells"],
                    r["v"][1] / cad_conductor,
                    r["v"][1] / v_conductor_analytic,
                    r["mesh_wall_time_s"],
                    r["wall_time_s"],
                )
                for r in rungs
            ),
            flush=True,
        )

    graded = [r for r in rungs if r["h_c"] is not None]
    assert graded, "no graded rung completed inside the ladder budget"

    baseline_ratio = baseline["v"][1] / cad_conductor
    ratios = [r["v"][1] / cad_conductor for r in graded]

    # Monotone in h: refining the conductor may not lose conductor volume.
    previous = baseline_ratio
    for rung, ratio in zip(graded, ratios):
        assert ratio > previous, (
            f"conductor volume fidelity did not improve at h_c={rung['h_c']:.4e} m: "
            f"meshed/CAD {ratio:.6f} vs {previous:.6f} at the coarser rung"
        )
        previous = ratio

    finest = graded[-1]
    assert ratios[-1] >= CAD_MASS_GATE, (
        f"graded conductor keeps only {ratios[-1]:.6f} of its CAD mass at "
        f"h_c={finest['h_c']:.4e} m ({finest['n_cells']} cells, "
        f"{finest['mesh_wall_time_s']:.2f} s mesh) — below the {CAD_MASS_GATE} gate. "
        f"Baseline global sizing keeps {baseline_ratio:.6f}. This is the measured "
        "frontier: record it in the GEO-15 entry rather than moving the gate."
    )

    # The negative control has to be *separated* from the gate, not merely below
    # it: a baseline that already sat at 0.949 would make the gate meaningless.
    assert baseline_ratio < CAD_MASS_GATE - 0.05, (
        f"baseline global-setSize mesh keeps {baseline_ratio:.6f} of the CAD mass, "
        f"within 0.05 of the {CAD_MASS_GATE} gate; the negative control no longer "
        "separates and the chunk's premise needs re-examining"
    )
