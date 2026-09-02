"""`WF-6` step 3f₀ — the phantom-sizing knob on `birdcage_port_domain`.

`birdcage_port_domain` has only ever had one global `resolution` (0.015) plus
an optional conductor Threshold, so the phantom's cells are simply the global
size: 537 tetrahedra in a pi*0.03^2*0.08 m^3 cylinder, h ~ 1.5 cm. Step 3f
wants to halve *the phantom's* sizing without touching air or coil, and step
3f₀ is the knob and its identity test — a mesh parameter, nothing solved.

Three builds of the four-port fixture, one knob between them:

* **the no-op control (the anchor)** — `phantom_resolution` absent reproduces
  the recorded mesh, 116 085 global cells and 537 tag-3 cells, at 0.000e+00
  relative. No existing record, gate or example can have moved, because with
  `None` the generator creates no size field at all;
* **the negative control** — `phantom_resolution = 0.015`, *equal* to the
  global sizing, must reproduce the same two counts at 0.000e+00. The field
  is then present but numerically constant at `resolution`, so a mesh that
  changes here would mean gmsh is honouring the field's *presence* and the
  `None` path is not a true no-op either;
* **the knob turned** — `phantom_resolution = 0.0075`, one halving. The tag-3
  count must rise by a factor in [5, 12] (the (0.015/0.0075)^3 = 8x prediction
  with a wide band for the size-field transition) while the cells *outside*
  tag 3 change by < 10%: the refinement is confined to the phantom.

On the refined mesh the two scale-free CAD identities already gated elsewhere
must still hold exactly — `GEO-18`'s port-sheet area 1.120000000e-04 m^2 on
all four ports and the `GEO-19` volume partition 1.000000000000 — because
neither is a discretisation quantity: the sheet is a planar rectangle a
conforming fragment meshes exactly, and the partition is a tautology about
cell tags that a finer mesh cannot break unless the tagging did.

Rank-safety: `cell_tags.values`/`.indices` are rank-local, so every tag-3
count here is a `size_local` restriction reduced with `MPI.SUM` — this module
runs at `-n 2` precisely so a missing reduction shows up as a halved count.

Scope: the parameter and its identities. No solve, no record moved, no
default changed; `WF-6` stays 🟡, and the finer-phantom *question* (does the
B1+ map move?) is step 3f, not this.
"""

from __future__ import annotations

import numpy as np
from mpi4py import MPI

from fem_em_solver.io.mesh import _interface_facet_tags
from tests.mesh.helpers import global_cell_tag_set
from tests.mesh.test_coil_phantom_conforming import _tag_volume, _total_volume
from tests.mesh.test_birdcage_leg_gaps import _analytic_box_volume
from tests.mesh.test_birdcage_port_terminals import _interface_area_or_zero
from tests.mesh.test_birdcage_port_sheets import (
    LEG_COUNT,
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
    _build,
)

# The default four-port fixture's records, restated (they are printed records
# in the §7 `GEO-19` step B / `WF-6` entries and their logs, not constants some
# module already exports). These are what "the parameter absent changes
# nothing" means, so they are asserted at exact equality, not in a band.
DEFAULT_CELL_COUNT = 116085
DEFAULT_PHANTOM_CELL_COUNT = 537

# `GEO-18`'s closed-form port-sheet area dx*g [m^2], and the tolerance that
# module gates it at. Imported here as a number rather than recomputed: the
# point is that the refined mesh returns the *same* number.
SHEET_AREA_M2 = 1.120000000e-04
SHEET_AREA_TOL = 1.0e-9

# The knob's rung and its pre-registered band.
PHANTOM_RESOLUTION_FINE = 0.0075
PHANTOM_GROWTH_BAND = (5.0, 12.0)
# The global sizing itself — the negative control's value.
PHANTOM_RESOLUTION_NOOP = 0.015
# The refinement must not spill out of the phantom.
OUTSIDE_CHANGE_CEILING = 0.10


def _global_tag_cell_count(mesh, cell_tags, tag, comm):
    """Number of **owned** cells carrying ``tag``, summed over ranks.

    ``cell_tags.indices`` is a rank-local array of local cell indices and
    includes ghosts, so both a bare ``len`` and an unreduced sum are wrong —
    the first double-counts cells on the partition boundary, the second
    reports one rank's share as if it were the mesh's.
    """
    size_local = int(mesh.topology.index_map(mesh.topology.dim).size_local)
    indices = np.asarray(cell_tags.indices)
    values = np.asarray(cell_tags.values)
    local = int(np.count_nonzero((values == tag) & (indices < size_local)))
    return int(comm.allreduce(local, op=MPI.SUM))


def _read(phantom_resolution, comm):
    """One build, reduced to the numbers this module asserts on."""
    mesh, cells, _facets, diag, elapsed = _build(
        True, phantom_resolution=phantom_resolution
    )
    ports = list(range(1, LEG_COUNT + 1))
    halves = {i: (PORT_LOWER + i, PORT_UPPER + i) for i in ports}
    n_cells = int(mesh.topology.index_map(mesh.topology.dim).size_global)
    n_phantom = _global_tag_cell_count(mesh, cells, 3, comm)

    dx, dy, dz = diag["port_box_size_m"]
    all_tags = [1, 2, 3, *[t for pair in halves.values() for t in pair]]
    volumes = {t: _tag_volume(mesh, cells, t, comm) for t in all_tags}
    v_total = _total_volume(mesh, comm)

    sheet_tags = _interface_facet_tags(
        mesh, cells, {SHEET_IFACE + i: halves[i] for i in ports}
    )
    sheet_area = {
        i: _interface_area_or_zero(mesh, sheet_tags, SHEET_IFACE + i, comm)
        for i in ports
    }
    return {
        "cells": n_cells,
        "phantom_cells": n_phantom,
        "outside_cells": n_cells - n_phantom,
        "partition": sum(volumes.values()) / v_total,
        "box_closure": v_total / _analytic_box_volume(dy),
        "sheet_area": sheet_area,
        "tag_set": global_cell_tag_set(mesh, cells),
        "mesh_wall_time_s": float(diag["mesh_wall_time_s"]),
        "phantom_resolution_m": diag["phantom_resolution_m"],
        "elapsed_s": elapsed,
        "box": (dx, dy, dz),
    }


def _report(label, r):
    return (
        f"[WF-6 step 3f0] {label}: h_p={r['phantom_resolution_m']}  "
        f"cells={r['cells']}  phantom(tag 3)={r['phantom_cells']}  "
        f"outside={r['outside_cells']}  partition={r['partition']:.12f}  "
        f"box closure={r['box_closure']:.12f}  sheets "
        + " ".join(f"P{i}={a:.9e}" for i, a in sorted(r["sheet_area"].items()))
        + f"  mesh={r['mesh_wall_time_s']:.2f} s  rung={r['elapsed_s']:.2f} s"
    )


def test_phantom_resolution_is_a_confined_knob_with_a_no_op_default():
    """The knob refines the phantom and only the phantom; absent, it is nothing.

    The no-op control is the anchor: the parameter absent must reproduce
    116 085 / 537 exactly. A miss there is a stop, not a re-record — it would
    mean adding the parameter moved every existing four-port record.
    """
    comm = MPI.COMM_WORLD

    # The control first: if gmsh dies on a later build the anchor is in hand.
    base = _read(None, comm)
    noop = _read(PHANTOM_RESOLUTION_NOOP, comm)
    fine = _read(PHANTOM_RESOLUTION_FINE, comm)

    growth = fine["phantom_cells"] / base["phantom_cells"]
    outside_change = abs(fine["outside_cells"] / base["outside_cells"] - 1.0)

    if comm.rank == 0:
        print(
            "\n"
            + _report("control (parameter absent)", base)
            + f"\n[WF-6 step 3f0] control vs record: cells {base['cells']} vs "
            f"{DEFAULT_CELL_COUNT} (relative "
            f"{abs(base['cells'] / DEFAULT_CELL_COUNT - 1.0):.3e}), phantom "
            f"{base['phantom_cells']} vs {DEFAULT_PHANTOM_CELL_COUNT} (relative "
            f"{abs(base['phantom_cells'] / DEFAULT_PHANTOM_CELL_COUNT - 1.0):.3e})"
            + "\n"
            + _report(f"negative control (h_p = h_global = {PHANTOM_RESOLUTION_NOOP})", noop)
            + "\n"
            + _report(f"refined (h_p = {PHANTOM_RESOLUTION_FINE})", fine)
            + f"\n[WF-6 step 3f0] phantom growth {base['phantom_cells']} -> "
            f"{fine['phantom_cells']} = {growth:.4f}x (band "
            f"{PHANTOM_GROWTH_BAND}, (h/h_p)^3 = "
            f"{(PHANTOM_RESOLUTION_NOOP / PHANTOM_RESOLUTION_FINE) ** 3:.1f}x); "
            f"outside tag 3 {base['outside_cells']} -> {fine['outside_cells']} "
            f"= {outside_change:.4%} (ceiling {OUTSIDE_CHANGE_CEILING:.0%}); "
            f"total {base['cells']} -> {fine['cells']}",
            flush=True,
        )

    # (i) The no-op control — the anchor. Exact equality: `None` builds no
    #     field, so this is the same construction, not a close one.
    assert base["phantom_resolution_m"] is None
    assert base["cells"] == DEFAULT_CELL_COUNT, (
        f"the parameter absent meshed {base['cells']} cells against the "
        f"recorded {DEFAULT_CELL_COUNT}; adding `phantom_resolution` moved the "
        "default four-port mesh, so every record, gate and example built on it "
        "moved too — this is a stop, not a re-record"
    )
    assert base["phantom_cells"] == DEFAULT_PHANTOM_CELL_COUNT, (
        f"the parameter absent gives {base['phantom_cells']} tag-3 cells "
        f"against the recorded {DEFAULT_PHANTOM_CELL_COUNT}"
    )

    # (i') The negative control — a field present but inactive changes nothing.
    assert noop["cells"] == DEFAULT_CELL_COUNT, (
        f"`phantom_resolution = {PHANTOM_RESOLUTION_NOOP}` (equal to the global "
        f"sizing) meshed {noop['cells']} cells against {DEFAULT_CELL_COUNT}; the "
        "field is numerically constant at `resolution`, so gmsh is honouring "
        "its *presence*, which means the `None` path is not a true no-op either"
    )
    assert noop["phantom_cells"] == DEFAULT_PHANTOM_CELL_COUNT, (
        f"`phantom_resolution = {PHANTOM_RESOLUTION_NOOP}` gives "
        f"{noop['phantom_cells']} tag-3 cells against "
        f"{DEFAULT_PHANTOM_CELL_COUNT}"
    )

    # (ii) The knob turned: refinement lands in the phantom, and stays there.
    low, high = PHANTOM_GROWTH_BAND
    assert low <= growth <= high, (
        f"halving the phantom sizing took the tag-3 count "
        f"{base['phantom_cells']} -> {fine['phantom_cells']} ({growth:.4f}x), "
        f"outside the pre-registered band [{low}, {high}] around the "
        f"(h/h_p)^3 = 8x prediction; the Box field is not covering the phantom "
        "(too small) or is not confined to it (too large)"
    )
    assert outside_change < OUTSIDE_CHANGE_CEILING, (
        f"the cells outside tag 3 moved {outside_change:.4%} "
        f"({base['outside_cells']} -> {fine['outside_cells']}), past the "
        f"{OUTSIDE_CHANGE_CEILING:.0%} ceiling; a phantom knob that also "
        "refines the air box is the global halving step 3f is trying to avoid"
    )

    # (iii) The scale-free CAD identities hold on the refined mesh.
    for label, r in (("refined", fine), ("negative control", noop)):
        assert r["tag_set"] == base["tag_set"], (
            f"{label} carries cell tags {sorted(r['tag_set'])} against the "
            f"control's {sorted(base['tag_set'])}; the sizing knob changed the "
            "tagging"
        )
        assert abs(r["partition"] - 1.0) < 1e-9, (
            f"{label}: the tagged volumes sum to {r['partition']:.12f} of the "
            "mesh volume; `GEO-19`'s partition is a tautology about cell tags "
            "and cannot be broken by refinement unless the tagging broke"
        )
        assert abs(r["box_closure"] - 1.0) < 1e-9, (
            f"{label}: the meshed domain is {r['box_closure']:.12f} of the "
            "analytic air box"
        )
        for i, area in sorted(r["sheet_area"].items()):
            assert abs(area / SHEET_AREA_M2 - 1.0) < SHEET_AREA_TOL, (
                f"{label}: port P{i}'s sheet area {area:.9e} m^2 against "
                f"`GEO-18`'s closed form {SHEET_AREA_M2:.9e} m^2 (ratio "
                f"{area / SHEET_AREA_M2:.12f}); a planar rectangle meshed by a "
                "conforming fragment has no discretisation error to spend, at "
                "any sizing"
            )
