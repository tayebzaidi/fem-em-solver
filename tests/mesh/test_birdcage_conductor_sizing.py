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

**What this gate claims, since 2026-08-26 (`GEO-21` step 2) — read this before
citing it.** It compared *graded vs ungraded* sizing until the 0.11 image
(dolfinx 0.11 / gmsh 4.15.2) stopped meshing the ungraded rung entirely; see
``BASELINE_CONTROL_RESOLUTION`` below. Its control is now a **coarse graded**
rung, so what it demonstrates is **fine-vs-coarse conductor grading** — still
quantitative, still monotone, but *no longer* evidence that grading is
*required*. That stronger claim closed on the 0.7.2 image (`GEO-15`,
2026-08-16, 0.740335 ungraded vs 0.967019 graded) and **stays closed there**;
do not restate it off this module's present numbers.
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

# The negative control's conductor sizing — COARSER than every `CONDUCTOR_RUNGS`
# rung, and the rung the gate's separation guard measures against.
#
# It was ``None`` (one global ``setSize = 0.015``, no conductor grading at all)
# until 2026-08-26. On the 0.11 image that build stopped meshing: it aborts in
# gmsh with "Invalid boundary mesh (overlapping facets) on surface 59 surface
# 79" *before* the graded rung ever runs, so this whole gate had been
# non-executing on `main` since the 0.11 merge (found by `EX-30` leg (mesh),
# 2026-08-25; red reproduced in ``20260826T050100Z_GEO-21-step1-red-repro.log``).
# Refining the global size does not walk out of it — three finer steps fail on
# three different surface pairs.
#
# `GEO-21` step 1 measured the replacement candidates instead of guessing.
# Through this module's own ``_mesh``
# (``20260826T050134Z_GEO-21-step1-cad-mass-probe.log``, -n 2) and the
# coarse-ward ladder (``20260826T050319Z_GEO-21-step1-control-ladder.log``,
# -n 1 because the coarse end can FAIL — the rank-0 gmsh deadlock trap),
# meshed/CAD against this same denominator:
#     h_c = None     FAIL  "overlapping facets" on surfaces 59/79
#     h_c = 9.6e-3   FAIL  same family, surfaces 54/86
#     h_c = 6.4e-3   0.767219   27 912 cells
#     h_c = 4.8e-3   0.846150   33 185 cells   <- adopted
#     h_c = 3.2e-3   0.916742   47 975 cells   (width control exact vs -n 2)
#     h_c = 1.6e-3   0.966977   98 666 cells   (the graded rung, the gate)
# The 2026-08-26 03:00 review ruled 4.8e-3: 3.2e-3 fails this module's own
# ``CAD_MASS_GATE - 0.05`` = 0.90 separation guard (0.916742, by 0.016742) and
# the only route to green from there is loosening a guard whose message says the
# premise needs re-examining; 6.4e-3 was rejected for cliff adjacency, the
# meshability cliff having already moved once at the 0.11 merge and 9.6e-3
# failing today. 4.8e-3 clears the 0.90 guard by 0.0538 and sits 0.104 below the
# 0.95 gate — 2x the guard width. ``CAD_MASS_GATE``, the 0.05 guard and
# ``CONDUCTOR_RUNGS`` are all untouched: the control moved, the gate did not.
# Version-tag this if the image moves again. Note the demoted claim in the
# module docstring — this is fine-vs-coarse grading now, not graded-vs-ungraded.
# The generator limitation itself (coarse conductor sizings, ``None`` included,
# cannot mesh on 0.11) stays open in docs/testing/known-issues.md.
BASELINE_CONTROL_RESOLUTION = 4.8e-3


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

    Negative control: the coarse-graded ``BASELINE_CONTROL_RESOLUTION`` mesh
    re-measured in-run on the *same* CAD-mass denominator. Its distance below
    the band is the effect size; the 0.7091-vs-analytic-sum number on record
    cannot serve, because it is a different denominator.

    Since the control went coarse-graded (`GEO-21` step 2, 2026-08-26) this
    measures **fine vs coarse** conductor grading — see the module docstring for
    what that does and does not claim.
    """
    comm = MPI.COMM_WORLD

    baseline = _mesh(conductor_resolution=BASELINE_CONTROL_RESOLUTION)
    _check_geo9_identities(baseline, comm)

    v_conductor_analytic = 2.0 * (
        2.0 * np.pi**2 * RING_RADIUS * RING_MINOR_RADIUS**2
    ) + LEG_COUNT * np.pi * (0.5 * LEG_WIDTH) ** 2 * COIL_LENGTH
    cad_conductor = baseline["cad_mass"]["conductor"]

    rungs = [baseline]
    started = time.perf_counter()
    for h_c in CONDUCTOR_RUNGS:
        remaining = LADDER_BUDGET_S - (time.perf_counter() - started)
        # Guarded on ``len(rungs) > 1``, not on ``h_c is not None``: since the
        # control went coarse-graded it also carries an ``h_c``, and the budget
        # rule is about *ladder* rungs, not about which sizing is set.
        if len(rungs) > 1 and remaining < 2.0 * rungs[-1]["wall_time_s"]:
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

    # ``rungs[0]`` is the control; everything after it is a ladder rung. Sliced
    # positionally rather than filtered on ``h_c is not None`` — the control has
    # an ``h_c`` too now, and filtering would fold it into its own comparison.
    graded = rungs[1:]
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
        f"Coarse-graded control at h_c={BASELINE_CONTROL_RESOLUTION:.4e} m keeps "
        f"{baseline_ratio:.6f}. This is the measured "
        "frontier: record it in the GEO-15 entry rather than moving the gate."
    )

    # The negative control has to be *separated* from the gate, not merely below
    # it: a baseline that already sat at 0.949 would make the gate meaningless.
    assert baseline_ratio < CAD_MASS_GATE - 0.05, (
        f"coarse-graded control (h_c={BASELINE_CONTROL_RESOLUTION:.4e} m) keeps "
        f"{baseline_ratio:.6f} of the CAD mass, "
        f"within 0.05 of the {CAD_MASS_GATE} gate; the negative control no longer "
        "separates and the chunk's premise needs re-examining (on record from "
        "GEO-21 step 1: 0.846150 — see BASELINE_CONTROL_RESOLUTION)"
    )
