"""`GEO-25` step 2 — the F-human 0.15 m rung as an executed gate.

`GEO-25` step 1 (2026-09-04 16:30 implementer slot) *measured* the
``ring_radius`` 0.07 → 0.15 m ladder on `birdcage_port_domain` and asserted
nothing — the probe script says so in its own docstring — so the chunk was
demoted ✅ → 🧪 by the 2026-09-04 18:00 review on the §3 rule. This module is
the route back: it re-executes the ladder's **top rung** and turns the
readings that were merely printed into asserts.

What is gated here, and only this:

* **the fixture** — the **branch-B** 0.15 m rung (`scale_sizing=False`: the
  global `resolution` is held at `mesh:9`'s 0.015 m, so element size is
  absolute and only the geometry grows). Its cell count is registered as a
  new version-tagged record at the imported `CELL_COUNT_BAND`; the scale-free
  `GEO-18` volume-partition identity and the `GEO-19` terminal-area ratio on
  all 32 ring ports are asserted at their own imported bands; and its
  meshed/CAD conductor mass recovery must clear the imported `CAD_MASS_GATE`.
* **the negative control** — the **branch-A** 0.15 m rung
  (`scale_sizing=True`: the mesh sizing scales with the radius too, so the
  meshes are geometrically *similar*). Step 1 measured its conductor mass
  recovery falling to 0.893028, i.e. *below* the same gate. That separation
  is the finding this module makes durable: **fixed absolute sizing is the
  right scaling for this generator at human scale**, and a similar-mesh
  F-human coil would fail the existing `GEO-15`/`GEO-21` conductor-mass gate.
  Its cell count is registered as a second, control-only record.

**Not** a solve, **not** a port gate, **not** a physics fixture: F-human
physics is Phase 6's and the weekly review's. This module owns the rung's CAD
identities and its cell records, nothing else.

Tier: heavy by ceiling (`timeout -k 30 600`), `-n 2`, real build. Step 1
measured the two builds at 112.27 s and 69.98 s at `-n 1`
(`20260904T214031Z_GEO-25.log:9733`, `20260904T213646Z_GEO-25.log:10331`), so
≈ 200–250 s is expected. Both rungs are known to mesh, which is what licenses
`-n 2` here: a gmsh build that *fails* deadlocks at rank > 1 (`GEO-23`).
"""

from __future__ import annotations

import time

import numpy as np
from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator

from tests.mesh.test_coil_phantom_conforming import _tag_volume, _total_volume
from tests.mesh.test_birdcage_conductor_sizing import CAD_MASS_GATE
from tests.mesh.test_birdcage_port_sheet_prerequisite import (
    CELL_COUNT_BAND,
    CONDUCTOR_RESOLUTION,
)
from tests.mesh.test_birdcage_port_terminals import CONDUCTOR_IFACE
from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER
from tests.mesh.test_birdcage_port_tags import (
    AIR_PADDING,
    COIL_LENGTH,
    LEG_SPACING,
    LEG_WIDTH,
    PHANTOM_HEIGHT,
    PHANTOM_RADIUS,
    PORT_BOX_SIZE,
    RESOLUTION,
    RING_MINOR_RADIUS,
    RING_RADIUS,
)
from tests.mesh.test_birdcage_ring_gaps import (
    EXACT,
    RING_GAP_LENGTH,
    _port_boundary_partition,
)

# `mesh:9` / `EX-35`'s own rung — the base of the `GEO-25` ladder.
BASE_RING_RADIUS = RING_RADIUS  # 0.07 m
LEG_COUNT = 16

# The F-human rung: a 30 cm coil, the operator's 2026-08-25 directive.
F_HUMAN_RING_RADIUS = 0.15

# Version-tagged cell records, registered by `GEO-25` step 2 under the (1*)
# licence on the 0.11 image (dolfinx 0.11 / gmsh 4.15.2), measured by step 1
# at `-n 1`. Asserted at the imported `CELL_COUNT_BAND` (1%), never at
# equality — the `OPS-27` stale-exact-record class is what equality buys.
#   branch B (fixed absolute sizing): 504 642  `20260904T214031Z_GEO-25.log:9733`
#   branch A (similar meshes)      : 204 977  `20260904T213646Z_GEO-25.log:10331`
F_HUMAN_BRANCH_B_CELL_RECORD = 504642
F_HUMAN_BRANCH_A_CELL_RECORD = 204977

# Step 1's measured conductor mass recovery at this rung, for the log line
# only — the asserts are against `CAD_MASS_GATE`, not against these.
STEP1_BRANCH_B_CAD_RATIO = 0.965414
STEP1_BRANCH_A_CAD_RATIO = 0.893028

# The `GEO-19` closed-form terminal-area band: a meshed terminal disk is
# inscribed in the analytic one, so the ratio is at most 1 and `GEO-18`/
# `GEO-19` measured it never below 0.95 at any radius or leg count.
TERMINAL_RATIO_BAND = (0.95, 1.0)


def _params(radius: float, *, scale_sizing: bool = True) -> dict:
    """`mesh:9`'s call, geometrically scaled by ``s = radius / 0.07``.

    ``scale_sizing`` resolves the one ambiguity in the `GEO-25` §7 row's
    phrase "phantom/air **sizing** scaled with the radius". ``True`` (default,
    the row read literally, since "sizing" elsewhere in this repo means a mesh
    size field) scales the global `resolution` too, so every rung is a
    geometrically *similar* mesh. ``False`` (env
    ``FEM_EM_PROBE_SCALE_MESH_SIZING=0``) holds `resolution` at `mesh:9`'s
    0.015 m, so the air/phantom volume grows as ``r^3`` at a fixed absolute
    element size — the only reading under which the row's own ``r^3`` cell
    count prediction is even testable. Both are reported; neither is asserted.
    """
    s = radius / BASE_RING_RADIUS
    return dict(
        leg_count=LEG_COUNT,
        ring_radius=BASE_RING_RADIUS * s,
        leg_width=LEG_WIDTH,  # conductor cross-section: NOT scaled
        leg_spacing=LEG_SPACING * s,
        coil_length=COIL_LENGTH * s,
        ring_minor_radius=RING_MINOR_RADIUS,  # conductor: NOT scaled
        phantom_radius=PHANTOM_RADIUS * s,
        phantom_height=PHANTOM_HEIGHT * s,
        port_box_size=tuple(v * s for v in PORT_BOX_SIZE),
        leg_gap_length=None,
        ring_gap_length=RING_GAP_LENGTH * s,
        emit_port_sheets=True,
        air_padding=AIR_PADDING * s,
        resolution=RESOLUTION * (s if scale_sizing else 1.0),
        conductor_resolution=CONDUCTOR_RESOLUTION,  # pinned, 1.6e-3 m
    )


def _ring_ports() -> list[int]:
    """The 2N ring port ids of the high-pass (ring-gap) layout."""
    return list(range(LEG_COUNT + 1, LEG_COUNT + 2 * LEG_COUNT + 1))


def _build_rung(radius: float, *, scale_sizing: bool) -> dict:
    """One rung: mesh it and read the scale-free CAD identities off it.

    Every reduction here is global. ``_tag_volume``, ``_total_volume`` and
    ``_port_boundary_partition`` each take ``comm`` and reduce internally —
    cell tags and facet areas are rank-local, and at `-n 2` rank 0 does not
    own every port (`GEO-9` step 2b paid for that once already).
    """
    comm = MPI.COMM_WORLD
    kwargs = _params(radius, scale_sizing=scale_sizing)

    started = time.perf_counter()
    mesh, cells, _facets, diag = MeshGenerator.birdcage_port_domain(
        comm=comm, return_diagnostics=True, **kwargs
    )
    build_elapsed = time.perf_counter() - started

    ring_ports = _ring_ports()
    port_cell_tags = {i: (PORT_LOWER + i,) for i in range(1, LEG_COUNT + 1)}
    port_cell_tags.update({i: (PORT_LOWER + i, PORT_UPPER + i) for i in ring_ports})
    all_tags = sorted({1, 2, 3, *[t for v in port_cell_tags.values() for t in v]})

    volumes = {t: _tag_volume(mesh, cells, t, comm) for t in all_tags}
    v_total = _total_volume(mesh, comm)

    _counts, areas = _port_boundary_partition(mesh, cells, comm, port_cell_tags)
    terminal_analytic = float(diag["ring_port_layout"]["ring_terminal_area_m2"])
    ratios = np.array(
        [areas[CONDUCTOR_IFACE + i] / terminal_analytic for i in ring_ports]
    )

    return {
        "radius": radius,
        "scale_sizing": scale_sizing,
        "n_cells": mesh.topology.index_map(3).size_global,
        "mesh_wall_time_s": float(diag["mesh_wall_time_s"]),
        "build_s": build_elapsed,
        "partition": sum(volumes.values()) / v_total,
        "v_total": v_total,
        "terminal_ratios": ratios,
        "cad_ratio": volumes[1] / diag["cad_mass_by_group"]["conductor"],
    }


# One gmsh build per branch per process, not per assert. The `GEO-25` §7 row
# sizes this step at "≈ 200-250 s" = the two step-1 builds (112.27 + 69.98 s at
# `-n 1`); rebuilding branch B for the separation assert would double that for
# a mesh that is deterministic in-process. Keyed on the branch flag only —
# this module has exactly one radius.
_RUNG_CACHE: dict[bool, dict] = {}


def _rung(*, scale_sizing: bool) -> dict:
    if scale_sizing not in _RUNG_CACHE:
        _RUNG_CACHE[scale_sizing] = _build_rung(
            F_HUMAN_RING_RADIUS, scale_sizing=scale_sizing
        )
    return _RUNG_CACHE[scale_sizing]


def _report(comm, tag: str, rung: dict, record: int, step1_cad: float) -> None:
    if comm.rank != 0:
        return
    ratios = rung["terminal_ratios"]
    print(
        f"\n[GEO-25 step 2] {tag}  ring_radius = {rung['radius']:.6f} m  "
        f"scale_mesh_sizing={rung['scale_sizing']}"
        f"\n  cells                 {rung['n_cells']} vs record {record}  "
        f"relative {rung['n_cells'] / record - 1.0:.3e}  (band {CELL_COUNT_BAND})"
        f"\n  mesh_wall_time_s      {rung['mesh_wall_time_s']:.3f}"
        f"  build_s {rung['build_s']:.3f}"
        f"\n  volume partition      {rung['partition']:.12f}  "
        f"(total {rung['v_total']:.9e} m^3)"
        f"\n  terminal ratio        min {ratios.min():.9f}  max {ratios.max():.9f}  "
        f"n_ports {len(ratios)}"
        f"\n  meshed/CAD conductor  {rung['cad_ratio']:.6f}  "
        f"(step 1 printed {step1_cad:.6f}; gate {CAD_MASS_GATE}, margin "
        f"{rung['cad_ratio'] - CAD_MASS_GATE:+.6f})",
        flush=True,
    )


def test_f_human_branch_b_rung_reproduces_its_record_and_cad_identities():
    """The F-human 0.15 m rung at fixed absolute sizing is a gated fixture.

    Four asserts on the fixture (cell record, `GEO-18` volume partition,
    `GEO-19` terminal ratios on all 32 ring ports, `GEO-15`/`GEO-21`
    conductor-mass recovery) and a two-sided separation against the branch-A
    control, which must sit *below* the same conductor-mass gate.
    """
    comm = MPI.COMM_WORLD

    fixture = _rung(scale_sizing=False)
    _report(
        comm, "branch B (fixed absolute sizing)", fixture,
        F_HUMAN_BRANCH_B_CELL_RECORD, STEP1_BRANCH_B_CAD_RATIO,
    )

    # (i) the new version-tagged cell record, at the imported band.
    assert (
        abs(fixture["n_cells"] / F_HUMAN_BRANCH_B_CELL_RECORD - 1.0) < CELL_COUNT_BAND
    ), (
        f"branch-B F-human rung meshes {fixture['n_cells']} cells against the "
        f"{F_HUMAN_BRANCH_B_CELL_RECORD} record (relative "
        f"{fixture['n_cells'] / F_HUMAN_BRANCH_B_CELL_RECORD - 1.0:.3e}, band "
        f"{CELL_COUNT_BAND}); GEO-25 step 1's determinism repeat was on the "
        "0.10 m rung, so a spread here is a finding to record with its measured "
        "size, not a band to widen"
    )

    # (ii) `GEO-18`: the tagged volumes partition the air box exactly.
    assert abs(fixture["partition"] - 1.0) < EXACT, (
        f"branch-B F-human rung: tagged volumes sum to "
        f"{fixture['partition']:.12f} of the mesh volume (band {EXACT}); a "
        "deficit means a fragment piece carries no physical group, an excess "
        "that a region is meshed twice"
    )

    # (iii) `GEO-19`: the closed-form terminal-area ratio, all 32 ring ports.
    ratios = fixture["terminal_ratios"]
    lo, hi = TERMINAL_RATIO_BAND
    assert len(ratios) == 2 * LEG_COUNT, (
        f"expected {2 * LEG_COUNT} ring ports on the high-pass layout, read "
        f"{len(ratios)}"
    )
    assert ratios.min() >= lo and ratios.max() <= hi, (
        f"branch-B F-human rung: terminal-area ratios span "
        f"[{ratios.min():.9f}, {ratios.max():.9f}] outside the GEO-19 closed-form "
        f"band [{lo}, {hi}] on {len(ratios)} ring ports; above 1 means the meshed "
        "terminal is not inscribed in the analytic disk"
    )

    # (iv) the conductor-mass gate, imported from the `GEO-15` module.
    assert fixture["cad_ratio"] >= CAD_MASS_GATE, (
        f"branch-B F-human rung keeps only {fixture['cad_ratio']:.6f} of the "
        f"conductor's CAD mass, below the {CAD_MASS_GATE} gate (step 1 printed "
        f"{STEP1_BRANCH_B_CAD_RATIO:.6f}); that is the finding that the F-human "
        "coil needs its own conductor sizing — record it, do not move the gate"
    )


def test_f_human_branch_a_control_falls_below_the_conductor_mass_gate():
    """Negative control: scaling the *mesh sizing* with the radius fails.

    Branch A keeps every rung geometrically similar, which sounds like the
    conservative choice and is not: at 0.15 m the conductor's 1.6 mm graded
    region is swamped by a global size that grew 2.14x, and the meshed
    conductor loses mass until it drops under the same `CAD_MASS_GATE` the
    branch-B rung clears. Both sides are measured in this run — the gate is
    asserted as a *separation*, not as two independent readings.
    """
    comm = MPI.COMM_WORLD

    control = _rung(scale_sizing=True)
    _report(
        comm, "branch A (mesh sizing scaled — CONTROL)", control,
        F_HUMAN_BRANCH_A_CELL_RECORD, STEP1_BRANCH_A_CAD_RATIO,
    )
    fixture = _rung(scale_sizing=False)

    if comm.rank == 0:
        print(
            f"\n[GEO-25 step 2] separation at ring_radius = "
            f"{F_HUMAN_RING_RADIUS:.3f} m:"
            f"\n  control  (branch A) meshed/CAD {control['cad_ratio']:.6f}  "
            f"{CAD_MASS_GATE - control['cad_ratio']:.6f} BELOW the "
            f"{CAD_MASS_GATE} gate"
            f"\n  fixture  (branch B) meshed/CAD {fixture['cad_ratio']:.6f}  "
            f"{fixture['cad_ratio'] - CAD_MASS_GATE:.6f} ABOVE it"
            f"\n  separation          {fixture['cad_ratio'] - control['cad_ratio']:.6f}",
            flush=True,
        )

    # The control's own cell record, control-only.
    assert (
        abs(control["n_cells"] / F_HUMAN_BRANCH_A_CELL_RECORD - 1.0) < CELL_COUNT_BAND
    ), (
        f"branch-A F-human control meshes {control['n_cells']} cells against the "
        f"{F_HUMAN_BRANCH_A_CELL_RECORD} record (relative "
        f"{control['n_cells'] / F_HUMAN_BRANCH_A_CELL_RECORD - 1.0:.3e}, band "
        f"{CELL_COUNT_BAND})"
    )

    # The scale-free identities do not care which branch built the mesh.
    assert abs(control["partition"] - 1.0) < EXACT, (
        f"branch-A F-human control: tagged volumes sum to "
        f"{control['partition']:.12f} of the mesh volume (band {EXACT})"
    )
    lo, hi = TERMINAL_RATIO_BAND
    ratios = control["terminal_ratios"]
    assert ratios.min() >= lo and ratios.max() <= hi, (
        f"branch-A F-human control: terminal-area ratios span "
        f"[{ratios.min():.9f}, {ratios.max():.9f}] outside [{lo}, {hi}] on "
        f"{len(ratios)} ring ports"
    )

    # The separation itself: this is what makes fixed absolute sizing the
    # right scaling for this generator at human scale.
    assert control["cad_ratio"] < CAD_MASS_GATE <= fixture["cad_ratio"], (
        f"the F-human conductor-mass separation collapsed: branch-A control "
        f"{control['cad_ratio']:.6f}, gate {CAD_MASS_GATE}, branch-B fixture "
        f"{fixture['cad_ratio']:.6f} (step 1 printed "
        f"{STEP1_BRANCH_A_CAD_RATIO:.6f} and {STEP1_BRANCH_B_CAD_RATIO:.6f}); "
        "either branch A no longer fails the gate — in which case the argument "
        "for fixed absolute sizing is gone — or branch B no longer clears it"
    )
