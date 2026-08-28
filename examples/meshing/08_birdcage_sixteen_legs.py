"""Example (`EX-33`): the 16-leg gapped + sheeted birdcage — the first coil above four legs.

Every birdcage example in this repo is **four legs**: `EX-21` (`mesh:3`) grades
the conductors on the uncut coil, `EX-28` (`mesh:6`) cuts the legs and rebuilds
the port sheets, `EX-31` (`mesh:7`) cuts the end rings. Nothing had ever been
meshed above four until `GEO-19` (✅ 2026-08-25), which is exactly the angle
this example shows: the same construction at ``leg_count = 16``, the count item
(a) of the §10 32-port directive asks the pricing for.

**Why sixteen is a different measurement, not a bigger one.** At four legs every
port sits on a coordinate axis, so the sheets are x- or y-normal, the terminal
disks are all the same disk under a coordinate mirror, and *every* identity is
consistent with the construction being an accident of C4. At sixteen the pitch
is 22.5°, twelve of the sixteen ports are off-axis, and the sheet extents have
to be read as projections onto each port's **own** radial/azimuthal/axial frame
(`PORT-9` leg (d1)'s helpers, imported). The identities either survive that or
they were never properties of the construction. They survive:

* the `GEO-9` tagged-volume partition and the analytic air box, to ``1e-9``;
* all 32 half-boxes at ``0.5`` of the analytic gap box, to ``1e-9``;
* all 16 sheets at the closed-form mid-section ``dx·g``, planar, spanning the
  gap, with ``A/h`` equal to the transverse extent — the C16 spread under the
  imported ``SHEET_SPREAD_BAND``;
* all 16 terminal disks inside the imported inscribed band, with the boundary
  closure that makes them readable as terminals;
* the graded conductor still at its CAD mass, and the layout's own port-centre
  clearance floor at the new azimuthal pitch.

**The one gate that reads differently, and the table this example prints.** The
terminal *equality* half is read per azimuth class (the 2026-08-25 ruling,
`GEO-19` §7): the mesh's own mirror symmetries fold sixteen azimuths into three
classes, and the gate is intra-class ``TERMINAL_INTRA_CLASS_BAND`` with an
inter-class ceiling ``TERMINAL_INTER_CLASS_CEILING`` set at half the inscribed
triangulation's own azimuthal under-read. That three-value table — the thing a
flat equality band at four legs cannot show you — is the centrepiece print here.

**Negative control: the same code path at four legs reports ONE azimuth class.**
That is `GEO-19`'s own back-compat identity, asserted here rather than assumed:
if the class partition were reading the measured areas instead of the mesh's
symmetry, the four-leg build would not collapse. Its cell count and terminal
ratios are checked against the imported step-B records in the same rung.

**Phase 6's first cost rung, printed never asserted.** Cells and mesh wall time
for 4 → 16 legs come out of the same run, on the same box, so the ratio is a
measurement rather than a comparison across machines. Counts and timings are
prints; nothing here bands them.

Every constant is **imported** from `tests/mesh/test_birdcage_port_scaleup.py`
and the modules it imports in turn (the `ANS-1` rule), and the identity family
is asserted by the gate module's own ``_assert_identity_family`` rather than
re-implemented — so this example cannot drift from the gate it demonstrates.

**Mesh only — no solve, no port model, no drive, no impedance, no resonance or
F-human claim.** Nothing in this repo solves at sixteen legs. The 32-port ring
layout is `GEO-20` step 2 and is not built here. Real DolfinX build.

Run it through the example runner::

    ./run_examples.sh -e mesh:8 -n 2 -t 400

Output lands in ``examples/meshing/paraview_output/``: open
``meshing_08_birdcage_sixteen_legs_combined.xdmf`` and threshold on ``CellTags``
(1 = conductor, 2 = air, 3 = phantom, 101-116 and 201-216 = the lower/upper
halves of the sixteen gap boxes), and ``meshing_08_birdcage_sixteen_legs_facets.xdmf``
for ``mesh_tags`` 211-226, the sixteen reconstructed port sheets.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import io

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gate's constants, helpers and assertions can be imported rather than
# restated (the `ANS-1` rule).
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)

from tests.mesh.test_birdcage_conductor_sizing import CAD_MASS_GATE  # noqa: E402
from tests.mesh.test_birdcage_port_sheet_prerequisite import (  # noqa: E402
    CONDUCTOR_RESOLUTION,
)
from tests.mesh.test_birdcage_port_tags import (  # noqa: E402
    AIR_PADDING,
    COIL_LENGTH,
    LEG_SPACING,
    LEG_WIDTH,
    PHANTOM_HEIGHT,
    PHANTOM_RADIUS,
    RESOLUTION,
    RING_MINOR_RADIUS,
    RING_RADIUS,
)
from tests.mesh.test_birdcage_leg_gaps import LEG_GAP_LENGTH  # noqa: E402
from tests.mesh.test_birdcage_port_scaleup import (  # noqa: E402
    CONTROL_CELL_COUNT,
    CONTROL_CELL_COUNT_BAND,
    CONTROL_LEG_COUNT,
    CONTROL_TERMINAL_RATIO,
    CONTROL_TERMINAL_RATIO_BAND,
    SCALED_LEG_COUNT,
    SEPARATION_LEG_COUNT_CEILING,
    TERMINAL_INTER_CLASS_CEILING,
    TERMINAL_INTRA_CLASS_BAND,
    _assert_identity_family,
    _layout,
    _measure,
    _report_safely,
    _terminal_classes,
)
from tests.mesh.test_birdcage_port_terminals import CONDUCTOR_IFACE  # noqa: E402
from tests.mesh.test_birdcage_leg_gaps import _analytic_terminal_area  # noqa: E402

CELL_TAG_NAMES = {1: "conductor", 2: "air", 3: "phantom"}

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "meshing_08_birdcage_sixteen_legs"

# The back-compat identity `GEO-19`'s `_azimuth_class` docstring states and this
# example asserts as its negative control: at four legs every port is aligned,
# so the ruled per-class reading collapses to the old flat equality gate. The
# three at sixteen is the mesh's mirror fold {0,45,90} / 22.5 / 67.5, also from
# that docstring — a structural count, not a measured band.
CONTROL_AZIMUTH_CLASSES = 1
SCALED_AZIMUTH_CLASSES = 3


def _write_cells(mesh, cell_tags, comm):
    """Mesh + cell tags as a DG0 ``CellTags`` array."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined", mesh, cell_tags, {}, comm=comm
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def _write_facets(mesh, facet_tags, comm):
    """The sixteen reconstructed sheets, on their own tdim-1 grid (`EX-1`)."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{BASENAME}_facets.xdmf"
    mesh.topology.create_connectivity(mesh.topology.dim - 1, mesh.topology.dim)
    with io.XDMFFile(comm, path, "w") as xdmf:
        xdmf.write_mesh(mesh)
        xdmf.write_meshtags(facet_tags, mesh.geometry)
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path if comm.rank == 0 else None


def _class_table(m):
    """``[(key, n_ports, meshed/analytic, intra-class spread)]`` for one build."""
    analytic = _analytic_terminal_area()
    rows = []
    for key, members in _terminal_classes(m).items():
        vals = np.array([m["areas"][CONDUCTOR_IFACE + i] for i in members])
        intra = (vals.max() - vals.min()) / vals.mean() if len(members) > 1 else 0.0
        rows.append((key, len(members), vals.mean() / analytic, intra))
    return rows


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if comm.rank == 0:
        print("=" * 72)
        print("EX-33 — the 16-leg gapped + sheeted birdcage (GEO-19's capability)")
        print("=" * 72)
        print(
            f"\n[geometry] leg_count={SCALED_LEG_COUNT} (control {CONTROL_LEG_COUNT})  "
            f"ring_radius={RING_RADIUS} m  ring_minor_radius={RING_MINOR_RADIUS} m"
            f"\n[geometry] leg_width={LEG_WIDTH} m  coil_length={COIL_LENGTH} m  "
            f"leg_spacing={LEG_SPACING} m  phantom {PHANTOM_RADIUS} x "
            f"{PHANTOM_HEIGHT} m  air_padding={AIR_PADDING} m"
            f"\n[mesh]     resolution={RESOLUTION} m  h_c={CONDUCTOR_RESOLUTION:.4e} m "
            f"(graded, the GEO-8 rule)"
            f"\n[cut]      leg_gap_length={LEG_GAP_LENGTH:.4e} m, emit_port_sheets=True "
            "on both rungs"
            f"\n[gate]     identity family at 1e-9; terminal equality per azimuth "
            f"class (intra {TERMINAL_INTRA_CLASS_BAND:.0e}, inter ceiling "
            f"{TERMINAL_INTER_CLASS_CEILING:.0e}); CAD mass gate {CAD_MASS_GATE}"
            f"\n[layout]   this ring's clearance floor admits up to "
            f"{SEPARATION_LEG_COUNT_CEILING} legs — the directive's 32 is above it, "
            "which is why this rung is 16"
            "\n[scope]    mesh only: no solve, no port model, no resonance or "
            "F-human claim at any leg count",
            flush=True,
        )

    # ---- rung 1: sixteen legs ---------------------------------------------
    # `_measure` builds and reduces everything the gates read; every collective
    # inside it is entered by every rank before anything is printed (the
    # `GEO-18` step 2 attempt-1 deadlock).
    scaled = _measure(SCALED_LEG_COUNT)
    problems = [_report_safely(f"{SCALED_LEG_COUNT} legs", scaled, comm)]

    # ---- rung 2: four legs, same code path, the negative control -----------
    control = _measure(CONTROL_LEG_COUNT)
    problems.append(_report_safely(f"{CONTROL_LEG_COUNT} legs (control)", control, comm))

    scaled_rows = _class_table(scaled)
    control_rows = _class_table(control)

    if comm.rank == 0:
        print(
            f"\n[EX-33 class table] the reading a C4 fixture cannot show: "
            f"{len(scaled_rows)} azimuth classes at {SCALED_LEG_COUNT} legs vs "
            f"{len(control_rows)} at {CONTROL_LEG_COUNT}",
            flush=True,
        )
        for label, rows in ((f"{SCALED_LEG_COUNT} legs", scaled_rows),
                            (f"{CONTROL_LEG_COUNT} legs (control)", control_rows)):
            for key, n, ratio, intra in rows:
                print(
                    f"  {label:<22s} class '{key}': {n:2d} ports  "
                    f"meshed/analytic={ratio:.9f}  intra-class spread={intra:.3e}",
                    flush=True,
                )
        means = np.array([r[2] for r in scaled_rows])
        inter = (means.max() - means.min()) / means.mean()
        print(
            f"  inter-class spread at {SCALED_LEG_COUNT} legs: {inter:.3e} "
            f"(ceiling {TERMINAL_INTER_CLASS_CEILING})",
            flush=True,
        )
        print(
            f"\n[EX-33 cost rung] {CONTROL_LEG_COUNT} -> {SCALED_LEG_COUNT} legs "
            f"(same run, same box — Phase 6's first measured rung; printed, never "
            f"asserted):"
            f"\n  cells      {control['n_cells']} -> {scaled['n_cells']} "
            f"({scaled['n_cells'] / control['n_cells']:.4f}x)"
            f"\n  mesh       {control['diag']['mesh_wall_time_s']:.2f} -> "
            f"{scaled['diag']['mesh_wall_time_s']:.2f} s "
            f"({scaled['diag']['mesh_wall_time_s'] / control['diag']['mesh_wall_time_s']:.4f}x)"
            f"\n  build rung {control['elapsed']:.2f} -> {scaled['elapsed']:.2f} s "
            f"(mesh + every reduction the gates read)"
            f"\n  control cells vs the imported step-B record {CONTROL_CELL_COUNT}: "
            f"relative {control['n_cells'] / CONTROL_CELL_COUNT - 1.0:.3e} "
            f"(band {CONTROL_CELL_COUNT_BAND})"
            f"\n  port-centre separation margin "
            f"{_layout(control['diag'])['min_port_center_separation_m'] / _layout(control['diag'])['required_port_center_separation_m']:.6f}x "
            f"-> "
            f"{_layout(scaled['diag'])['min_port_center_separation_m'] / _layout(scaled['diag'])['required_port_center_separation_m']:.6f}x "
            "(the term that closes at 26 legs)",
            flush=True,
        )

    # ---- the gates, imported ----------------------------------------------
    _assert_identity_family(scaled, f"{SCALED_LEG_COUNT} legs")
    _assert_identity_family(control, f"{CONTROL_LEG_COUNT} legs (control)")
    assert not [p for p in problems if p], [p for p in problems if p]

    # The negative control proper: the class partition comes off the *mesh's*
    # symmetry, so at four legs it must collapse to one class and reproduce the
    # old flat equality gate exactly. A four-leg build reporting more than one
    # class means `_azimuth_class` is reading areas rather than azimuths.
    assert len(control_rows) == CONTROL_AZIMUTH_CLASSES, (
        f"the {CONTROL_LEG_COUNT}-leg control reports "
        f"{len(control_rows)} azimuth classes "
        f"{[r[0] for r in control_rows]}, not the {CONTROL_AZIMUTH_CLASSES} the "
        "back-compat identity requires; the per-class reading no longer reduces "
        "to the flat equality gate at C4"
    )
    assert len(scaled_rows) == SCALED_AZIMUTH_CLASSES, (
        f"the {SCALED_LEG_COUNT}-leg rung reports {len(scaled_rows)} azimuth "
        f"classes {[r[0] for r in scaled_rows]}, not the "
        f"{SCALED_AZIMUTH_CLASSES} the mesh's mirror fold gives "
        "({0,45,90} / 22.5 / 67.5 deg); the azimuths came off the mesh, so this "
        "is a construction finding — record it, do not re-record the count"
    )

    # The control's own records, imported with their bands.
    assert (
        abs(control["n_cells"] / CONTROL_CELL_COUNT - 1.0) < CONTROL_CELL_COUNT_BAND
    ), (
        f"the control meshed {control['n_cells']} cells against `GEO-18` step 2's "
        f"re-record {CONTROL_CELL_COUNT}; this example's rung is not the gate's"
    )
    analytic = _analytic_terminal_area()
    for i in control["ports"]:
        ratio = control["areas"][CONDUCTOR_IFACE + i] / analytic
        assert abs(ratio - CONTROL_TERMINAL_RATIO) < CONTROL_TERMINAL_RATIO_BAND, (
            f"the control's port P{i} terminal ratio {ratio:.9f} against step 2's "
            f"record {CONTROL_TERMINAL_RATIO}"
        )

    # ---- ParaView ----------------------------------------------------------
    written = {
        "16-leg cells": _write_cells(scaled["mesh"], scaled["cells"], comm),
        "16-leg sheets": _write_facets(scaled["mesh"], scaled["sheet_tags"], comm),
    }
    if comm.rank == 0:
        print("\n[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<14s} {path}")
        print(
            "\n[paraview] threshold `CellTags` in the _combined file "
            f"({', '.join(f'{t} = {n}' for t, n in CELL_TAG_NAMES.items())}, "
            f"101-{100 + SCALED_LEG_COUNT} / 201-{200 + SCALED_LEG_COUNT} = the "
            "lower/upper"
            "\n           halves of the sixteen gap boxes) — the sixteen legs are "
            "each broken by an"
            "\n           8 mm gap with a port box spanning it, at a 22.5 deg "
            "pitch; then open"
            "\n           the _facets file and threshold `mesh_tags` to "
            f"211-{210 + SCALED_LEG_COUNT} for the sheets"
            "\n           themselves — only four of the sixteen stand in a "
            "coordinate plane, which"
            "\n           is the picture the frame-aware extents exist for."
            f"\n\nAll identities hold at {SCALED_LEG_COUNT} legs and the "
            f"{CONTROL_LEG_COUNT}-leg control collapses to one class. "
            f"Total elapsed {time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
