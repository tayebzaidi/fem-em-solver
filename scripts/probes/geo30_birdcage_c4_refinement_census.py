"""`GEO-30` — does the four-port birdcage fixture stay C4-symmetric under refinement?

One geometric census across **both** refinement axes, on the meshes the two
blocked items actually build.  No solve, no linear algebra, real build.

`ANS-4` step 2a refined ``conductor_resolution`` ×1 → ×0.75 and the `Z` class
spreads went 0.1012 / 0.0916 / 0.0654% → 0.5390 / 0.4591 / 1.6886%.  `WF-6`
step 4f refined the *global* ``resolution`` 0.015 → 0.0095 and a
port-symmetric-to-five-figures power residual split between the ports and
doubled.  Two axes, one symptom class.  This probe asks the cheapest question
that separates "the mesh stopped being C4" from "the solve did": are the four
C4 images of this fixture's *mesh* still equal at every rung?

**Rungs** (four; ×1 and h = 0.015 are the same mesh and are measured once):

===================================  ===========================  ==========
label                                ``conductor_resolution``     ``resolution``
===================================  ===========================  ==========
``x1 / h=0.015`` (the control rung)  ``CONDUCTOR_RESOLUTION``     ``RESOLUTION``
``conductor_resolution x0.75``       ``0.75 * CONDUCTOR_RESOLUTION``  ``RESOLUTION``
``resolution 0.012``                 ``CONDUCTOR_RESOLUTION``     ``0.012``
``resolution 0.0095``                ``CONDUCTOR_RESOLUTION``     ``0.0095``
===================================  ===========================  ==========

The generator is called with exactly the parameter set
``tests/mesh/test_birdcage_port_sheets._build(True)`` passes — every constant
imported, none retyped — with the one swept keyword replaced.  That helper
hard-codes ``resolution=RESOLUTION``, which is why the call is made here
directly rather than through it (`GEO-29`'s precedent, same fixture).

**Measured per rung**, all comm-reduced, the quadrant partition imported in
spirit from `GEO-28` (the squared-projection sector test, verbatim):

1. the four C4-image **quadrant volumes** ``∫ dx`` and owned-cell counts, in
   total and split by the three core tags;
2. the four **leg/conductor** volumes and owned-cell counts, each inside its
   own leg's cylinder;
3. the four **port gap-sheet facet areas** ``∫ dS(210+i)`` and facet counts,
   rebuilt from the two port-box half tags exactly as
   `tests/mesh/test_birdcage_port_sheets` rebuilds them;
4. ``size_global``.

**What is asserted** — three anchors, and *only* these three.  They are
geometric identities and reproductions of numbers already on record; nothing
physical is asserted, no band is invented, widened or re-registered, and no
`src/` file, test or record is touched by this script.

(i)   the ×1 rung's ``size_global`` reproduces `GEO-19` step B's record
      (116 085, restated as `GEO-28`/`GEO-29` restate it) inside the imported, unmoved
      1% ``CELL_COUNT_BAND``, and its four quadrant conductor masses reproduce
      `GEO-28`'s ≲ 0.1% spread (9.5943e-04 at
      ``20260908T183317Z_GEO-28.log:1819``);
(ii)  the four gap-sheet areas agree across the C4 images to ≤ 1e-3 relative at
      the ×1 rung — the construction-identity tolerance `TH-15` step 2h met at
      2.53e-15 / 8.70e-15 on the two-torus gap tags;
(iii) **negative control**: the *mis-paired* quadrant assignment must exceed
      the ×1 spread by ≥ 10× (`ANS-2` step 1's control, measured there at
      87.01–87.06% against a 5% band).  A census in which the mis-paired and
      correctly-paired readings agree is measuring its own bug.

      The mis-pairing is the plan's own: **rotate the C4 pairing by one
      quadrant** — leg ``n``'s own cylinder is read against quadrant ``n+1``'s
      sector instead of quadrant ``n``'s, and the result is differenced against
      the correctly-paired value.  A partition that really localises reads
      ≈ 100% here; a broken one reads ≈ 0%.

      A **half**-quadrant rotation of the *sector* partition is also computed
      and printed, but is deliberately **not** asserted on: it was measured at
      3.96e-03, only 4.13× the ×1 spread (attempt 1,
      ``20260909T170657Z_GEO-30.log``), because it is mass-preserving by
      construction — the 45°-offset sector spans 0°…90°, so it loses leg ``n``
      and gains leg ``n+1``, each half-weighted on its boundary, and the ring
      is axisymmetric.  It is kept as an observation and as the record of why
      it cannot be the control.

**Printed and asserted nowhere**: all four quantities at all four rungs side by
side, with each rung's spread and its ratio to the ×1 spread.  That table is
the deliverable; the ruling on `ANS-4` and `WF-6` is the next review's, written
from it.

Rank-safety: ``cell_tags.values``/``.indices``, ``size_local`` and every
midpoint array are **rank-local** — every count, volume and area below is
reduced with ``MPI.SUM``/``MAX``/``MIN``, ghosts are counted once by
restricting to ``index_map(dim).size_local`` (`OPS-39`'s fix), and the three
asserts run *after* every collective on *every* rank against allreduced values,
so a failure cannot leave one rank inside a collective.  No ``sqrt`` and no
ordering comparison appears inside a UFL expression (`OPS-22`; `WF-6` step 4c);
the sector test compares squares.

Run (real build, no solve, no complex mode)::

    mpiexec -n 2 python3 -u scripts/probes/geo30_birdcage_c4_refinement_census.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.mesh import (  # noqa: E402
    MeshGenerator,
    _interface_facet_tags,
)
from tests.mesh.test_birdcage_leg_gaps import LEG_GAP_LENGTH  # noqa: E402
from tests.mesh.test_birdcage_port_sheet_prerequisite import (  # noqa: E402
    CELL_COUNT_BAND,
    CONDUCTOR_RESOLUTION,
)
from tests.mesh.test_birdcage_port_sheets import (  # noqa: E402
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
)
from tests.mesh.test_birdcage_port_tags import (  # noqa: E402
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
)
from tests.mesh.test_birdcage_port_terminals import (  # noqa: E402
    _global_facet_count,
    _interface_area_or_zero,
)

# The cell record, restated on `GEO-28`/`GEO-29`'s precedent (both probes carry
# it as `CONTROL_CELL_RECORD`): it is a printed record, backed to ratio
# 1.000000 by two independent probes at `20260908T183317Z_GEO-28.log:1786` and
# `20260909T003221Z_GEO-29.log:1792`, and it is the same 116 085 that
# `tests/validation/test_port_birdcage_lumped_column.STEP2_CELL_COUNT` holds.
# The *band* it is judged in is imported and unmoved (`CELL_COUNT_BAND`, 1%).
STEP2_CELL_COUNT = 116085

CONDUCTOR_TAG, AIR_TAG, PHANTOM_TAG = 1, 2, 3

# `GEO-28`'s measured quadrant conductor-mass spread on this very rung
# (`20260908T183317Z_GEO-28.log:1800, 1819` — 9.5943e-04).  Restated rather
# than imported, on `tests/mesh/test_birdcage_port_sheets.STEP1_*`'s precedent:
# it is a printed record in a log and a §7 row, not a module constant anywhere.
# The ceiling asserted against is the plan's own "≲ 0.1%" reading of it.
GEO28_QUADRANT_MASS_SPREAD = 9.5943e-04
GEO28_QUADRANT_MASS_CEILING = 1.0e-3

# `TH-15` step 2h's construction-identity tolerance on gap-sheet tags.
SHEET_AREA_BAND = 1.0e-3

# `ANS-2` step 1's negative-control bar: the mis-paired assignment must exceed
# the correctly-paired spread by this factor.
MISPAIRED_MIN_RATIO = 10.0

# The per-leg cylinder of `GEO-28`'s item (4).
LEG_HALF_Z = 0.05

RUNGS = (
    ("x1 / h=0.015", CONDUCTOR_RESOLUTION, float(RESOLUTION)),
    ("conductor_resolution x0.75", 0.75 * CONDUCTOR_RESOLUTION, float(RESOLUTION)),
    ("resolution 0.012", CONDUCTOR_RESOLUTION, 0.012),
    ("resolution 0.0095", CONDUCTOR_RESOLUTION, 0.0095),
)
CONTROL_LABEL = RUNGS[0][0]


def _print(text, comm):
    if comm.rank == 0:
        print(text, flush=True)


def _spread(values):
    v = np.asarray(values, dtype=float)
    mean = v.mean()
    if mean == 0.0:
        return float("nan")
    return float((v.max() - v.min()) / mean)


def _build_rung(conductor_resolution, resolution, comm):
    """`_build(True)`'s parameter set with the two swept keywords replaced."""
    started = time.perf_counter()
    mesh, cell_tags, _facet_tags, diagnostics = MeshGenerator.birdcage_port_domain(
        leg_count=LEG_COUNT,
        ring_radius=RING_RADIUS,
        leg_width=LEG_WIDTH,
        leg_spacing=LEG_SPACING,
        coil_length=COIL_LENGTH,
        ring_minor_radius=RING_MINOR_RADIUS,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        port_box_size=PORT_BOX_SIZE,
        leg_gap_length=LEG_GAP_LENGTH,
        emit_port_sheets=True,
        air_padding=AIR_PADDING,
        resolution=float(resolution),
        conductor_resolution=float(conductor_resolution),
        phantom_resolution=None,
        as_hole=False,
        comm=comm,
        return_diagnostics=True,
    )
    return mesh, cell_tags, diagnostics, time.perf_counter() - started


def _owned_cell_geometry(mesh):
    """Midpoints and volumes of the *owned* cells only (`OPS-39`'s fix)."""
    tdim = mesh.topology.dim
    n_owned = int(mesh.topology.index_map(tdim).size_local)
    x = mesh.geometry.x
    dofmap = np.asarray(mesh.geometry.dofmap)
    if dofmap.ndim == 1:
        dofmap = dofmap.reshape(-1, 4)
    verts = x[dofmap[:n_owned, :4]]
    mid = verts.mean(axis=1)
    e = verts[:, 1:, :] - verts[:, 0:1, :]
    vol = np.abs(np.linalg.det(e)) / 6.0
    return n_owned, mid, vol


def _sector_masks(mid, n_sectors, offset_turns=0.0):
    """`GEO-28`'s squared-projection sector test — no ``atan2``, no ``sqrt``.

    ``offset_turns`` rotates the whole partition by that fraction of a sector;
    0.0 is `GEO-28`'s partition verbatim and 0.5 is the mis-paired control's
    half-quadrant rotation.
    """
    x, y = mid[:, 0], mid[:, 1]
    r2 = x * x + y * y
    masks = []
    for n in range(n_sectors):
        phi = 2.0 * np.pi * (n + offset_turns) / n_sectors
        ux, uy = float(np.cos(phi)), float(np.sin(phi))
        d = x * ux + y * uy
        masks.append((d > 0.0) & (d * d > 0.5 * r2))
    return masks


def _census(mesh, cell_tags, comm):
    """Every reduced quantity of one rung.  All collectives live here."""
    tdim = mesh.topology.dim
    n_owned, mid, vol = _owned_cell_geometry(mesh)

    tag_of = np.zeros(n_owned, dtype=np.int32)
    idx = np.asarray(cell_tags.indices)
    val = np.asarray(cell_tags.values)
    keep = idx < n_owned
    tag_of[idx[keep]] = val[keep]

    def s_int(v):
        return int(comm.allreduce(int(v), op=MPI.SUM))

    def s_float(v):
        return float(comm.allreduce(float(v), op=MPI.SUM))

    masks = _sector_masks(mid, LEG_COUNT)
    out = {
        "unassigned": s_int(np.count_nonzero(~np.any(masks, axis=0))),
        "counts": {},
        "volumes": {},
    }

    # ---- (1) quadrant volumes and owned-cell counts -------------------------
    out["quad_cells"] = [s_int(np.count_nonzero(m)) for m in masks]
    out["quad_volume"] = [s_float(vol[m].sum()) for m in masks]
    for name, tag in (
        ("coil", CONDUCTOR_TAG),
        ("air", AIR_TAG),
        ("phantom", PHANTOM_TAG),
    ):
        is_tag = tag_of == tag
        out["counts"][name] = [s_int(np.count_nonzero(is_tag & m)) for m in masks]
        out["volumes"][name] = [s_float(vol[is_tag & m].sum()) for m in masks]

    # ---- (2) per leg, conductor inside the leg's own cylinder ---------------
    r_leg = 0.5 * LEG_WIDTH
    leg_sel = []
    for n in range(LEG_COUNT):
        phi = 2.0 * np.pi * n / LEG_COUNT
        cx, cy = RING_RADIUS * np.cos(phi), RING_RADIUS * np.sin(phi)
        d2 = (mid[:, 0] - cx) ** 2 + (mid[:, 1] - cy) ** 2
        leg_sel.append(
            (tag_of == CONDUCTOR_TAG)
            & (d2 <= r_leg**2)
            & (np.abs(mid[:, 2]) <= LEG_HALF_Z)
        )
    out["leg_cells"] = [s_int(np.count_nonzero(s)) for s in leg_sel]
    out["leg_volume"] = [s_float(vol[s].sum()) for s in leg_sel]

    # ---- (3) the four port gap-sheet facet areas ----------------------------
    ports = list(range(1, LEG_COUNT + 1))
    halves = {i: (PORT_LOWER + i, PORT_UPPER + i) for i in ports}
    sheet_tags = _interface_facet_tags(
        mesh, cell_tags, {SHEET_IFACE + i: halves[i] for i in ports}
    )
    out["sheet_facets"] = [
        _global_facet_count(mesh, sheet_tags, SHEET_IFACE + i, comm) for i in ports
    ]
    out["sheet_area"] = [
        _interface_area_or_zero(mesh, sheet_tags, SHEET_IFACE + i, comm)
        for i in ports
    ]

    # ---- the negative controls ---------------------------------------------
    # (a) PRINTED ONLY, never asserted: the half-quadrant rotation of the
    #     sector partition. Mass-preserving by construction — see the module
    #     docstring — so it is an observation, not a control.
    off_masks = _sector_masks(mid, LEG_COUNT, offset_turns=0.5)
    is_coil = tag_of == CONDUCTOR_TAG
    out["mispaired_volume"] = [s_float(vol[is_coil & m].sum()) for m in off_masks]
    # (b) ASSERTED: the plan's mis-pairing — the C4 pairing rotated by one
    #     quadrant, so leg n's cylinder is read against quadrant n+1's sector.
    out["mispaired_leg_volume"] = [
        s_float(vol[leg_sel[n] & masks[(n + 1) % LEG_COUNT]].sum())
        for n in range(LEG_COUNT)
    ]
    out["paired_leg_volume"] = [
        s_float(vol[leg_sel[n] & masks[n]].sum()) for n in range(LEG_COUNT)
    ]

    out["size_global"] = int(mesh.topology.index_map(tdim).size_global)
    return out


def _mispaired_discrepancy(correct, mispaired):
    """max_n |B_n - A_n| / mean(A) — `ANS-2` step 1's control statistic."""
    a = np.asarray(correct, dtype=float)
    b = np.asarray(mispaired, dtype=float)
    mean = a.mean()
    if mean == 0.0:
        return float("nan")
    return float(np.max(np.abs(b - a)) / mean)


def _row(label, values, fmt="{:.6e}"):
    body = "  ".join(fmt.format(v) for v in values)
    return f"    {label:<30s} {body}   spread={_spread(values):.4e}"


def main():
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    _print(
        "\n[GEO-30] C4 census of the four-port gapped birdcage across BOTH "
        "refinement axes (no solve; asserts three geometric anchors and "
        "nothing else)\n"
        f"[GEO-30] ranks={comm.size}  quadrants about leg azimuths "
        "0/90/180/270 deg, +-45 deg, squared-projection test on owned cell "
        "midpoints (GEO-28's partition)\n"
        f"[GEO-30] CONDUCTOR_RESOLUTION={CONDUCTOR_RESOLUTION:.6e} m  "
        f"RESOLUTION={float(RESOLUTION):.6e} m  R={RING_RADIUS} m  "
        f"r_leg={0.5 * LEG_WIDTH} m  g={LEG_GAP_LENGTH} m",
        comm,
    )
    for label, h_c, h in RUNGS:
        _print(
            f"[GEO-30]   rung {label:<28s} conductor_resolution={h_c:.6e} "
            f"resolution={h:.6e}",
            comm,
        )

    rows = {}
    order = []
    for label, h_c, h in RUNGS:
        _print(f"\n[GEO-30] --- rung {label} ---", comm)
        mesh, cell_tags, diag, rung_s = _build_rung(h_c, h, comm)
        row = _census(mesh, cell_tags, comm)
        row["label"] = label
        row["conductor_resolution"] = float(h_c)
        row["resolution"] = float(h)
        row["mesh_s"] = float(diag["mesh_wall_time_s"])
        row["rung_s"] = float(rung_s)
        rows[label] = row
        order.append(label)
        _print(
            f"[GEO-30] {label}: size_global={row['size_global']}  "
            f"mesh={row['mesh_s']:.2f} s  rung={row['rung_s']:.2f} s  "
            f"unassigned cells={row['unassigned']}",
            comm,
        )
        del mesh, cell_tags

    control = rows[CONTROL_LABEL]
    cell_ratio = control["size_global"] / STEP2_CELL_COUNT
    spread_ctl_coil = _spread(control["volumes"]["coil"])
    spread_ctl_sheet = _spread(control["sheet_area"])
    mis_half = _mispaired_discrepancy(
        control["volumes"]["coil"], control["mispaired_volume"]
    )
    mis_leg = _mispaired_discrepancy(
        control["paired_leg_volume"], control["mispaired_leg_volume"]
    )

    elapsed = time.perf_counter() - started

    # ---- the table (printed; asserted nowhere) ------------------------------
    if comm.rank == 0:
        labels = " ".join(f"Q{n + 1:<12d}" for n in range(LEG_COUNT))
        print(
            f"\n[GEO-30] === the table: four quantities at four rungs "
            f"(columns Q1..Q4 / P1..P4) ===\n    {'':30s} {labels}"
        )
        for label in order:
            r = rows[label]
            print(
                f"\n  rung {label}  (h_c={r['conductor_resolution']:.4e}, "
                f"h={r['resolution']:.4e}, size_global={r['size_global']}, "
                f"mesh {r['mesh_s']:.2f} s)"
            )
            print(_row("(1) quadrant cells", r["quad_cells"], "{:13d}"))
            print(_row("(1) quadrant volume [m^3]", r["quad_volume"]))
            print(_row("(1) coil cells", r["counts"]["coil"], "{:13d}"))
            print(_row("(1) coil volume [m^3]", r["volumes"]["coil"]))
            print(_row("(1) air cells", r["counts"]["air"], "{:13d}"))
            print(_row("(1) air volume [m^3]", r["volumes"]["air"]))
            print(_row("(1) phantom cells", r["counts"]["phantom"], "{:13d}"))
            print(_row("(1) phantom volume [m^3]", r["volumes"]["phantom"]))
            print(_row("(2) leg cells", r["leg_cells"], "{:13d}"))
            print(_row("(2) leg volume [m^3]", r["leg_volume"]))
            print(_row("(3) gap-sheet facets", r["sheet_facets"], "{:13d}"))
            print(_row("(3) gap-sheet area [m^2]", r["sheet_area"]))

        print(
            "\n[GEO-30] === spreads (max-min)/mean, and each rung's ratio to "
            "the x1 rung's spread ==="
        )
        quantities = (
            ("quadrant cells", lambda r: r["quad_cells"]),
            ("quadrant volume", lambda r: r["quad_volume"]),
            ("coil cells", lambda r: r["counts"]["coil"]),
            ("coil volume", lambda r: r["volumes"]["coil"]),
            ("air cells", lambda r: r["counts"]["air"]),
            ("air volume", lambda r: r["volumes"]["air"]),
            ("phantom cells", lambda r: r["counts"]["phantom"]),
            ("phantom volume", lambda r: r["volumes"]["phantom"]),
            ("leg cells", lambda r: r["leg_cells"]),
            ("leg volume", lambda r: r["leg_volume"]),
            ("gap-sheet facets", lambda r: r["sheet_facets"]),
            ("gap-sheet area", lambda r: r["sheet_area"]),
        )
        header = "  {:<20s}".format("quantity") + "".join(
            f"{label[:22]:>24s}" for label in order
        )
        print(header)
        for name, get in quantities:
            base = _spread(get(control))
            cells = []
            for label in order:
                s = _spread(get(rows[label]))
                if base > 0.0 and np.isfinite(base):
                    cells.append(f"{s:.4e} ({s / base:6.2f}x)")
                else:
                    cells.append(f"{s:.4e} (  base 0)")
            print("  {:<20s}".format(name) + "".join(f"{c:>24s}" for c in cells))

        print(
            f"\n[GEO-30] size_global by rung: "
            + "  ".join(f"{label}={rows[label]['size_global']}" for label in order)
        )
        print(
            f"\n[GEO-30] === the three asserted anchors ===\n"
            f"  (i)   x1 size_global={control['size_global']} vs record "
            f"{STEP2_CELL_COUNT} (ratio {cell_ratio:.6f}), band "
            f"{CELL_COUNT_BAND:.0e} [imported, unmoved]\n"
            f"        x1 quadrant coil-mass spread={spread_ctl_coil:.6e} vs "
            f"`GEO-28`'s {GEO28_QUADRANT_MASS_SPREAD:.6e}, ceiling "
            f"{GEO28_QUADRANT_MASS_CEILING:.1e}\n"
            f"  (ii)  x1 gap-sheet area spread={spread_ctl_sheet:.6e}, band "
            f"{SHEET_AREA_BAND:.0e}\n"
            f"  (iii) mis-paired (C4 pairing rotated by ONE quadrant: leg n's "
            f"cylinder against quadrant n+1) discrepancy={mis_leg:.6e} = "
            f"{mis_leg / spread_ctl_coil:.2f}x the x1 spread, bar "
            f"{MISPAIRED_MIN_RATIO:.0f}x\n"
            f"        half-quadrant sector rotation (PRINTED, NEVER ASSERTED — "
            f"mass-preserving by construction)={mis_half:.6e} = "
            f"{mis_half / spread_ctl_coil:.2f}x\n"
            f"[GEO-30] probe wall time={elapsed:.2f} s",
            flush=True,
        )

    # ---- the three anchors.  Every collective above is complete, and every
    # value below is allreduced and therefore identical on every rank, so
    # asserting on all ranks cannot strand one inside a collective.
    assert abs(cell_ratio - 1.0) < CELL_COUNT_BAND, (
        f"the x1 rung meshed {control['size_global']} cells against the record "
        f"{STEP2_CELL_COUNT} (ratio {cell_ratio:.6f}) — this is not the fixture "
        "`ANS-4` and `WF-6` refine, so no rung below compares with anything"
    )
    assert spread_ctl_coil <= GEO28_QUADRANT_MASS_CEILING, (
        f"the x1 rung's four quadrant conductor masses spread "
        f"{spread_ctl_coil:.6e}, past `GEO-28`'s {GEO28_QUADRANT_MASS_SPREAD:.6e} "
        f"and the {GEO28_QUADRANT_MASS_CEILING:.1e} ceiling — the control rung "
        "does not reproduce the census it is the control for"
    )
    assert spread_ctl_sheet <= SHEET_AREA_BAND, (
        f"the x1 rung's four gap-sheet areas spread {spread_ctl_sheet:.6e}, past "
        f"{SHEET_AREA_BAND:.0e} — the four ports are not C4 images of each other "
        "even on the fixture every gate builds"
    )
    assert mis_leg >= MISPAIRED_MIN_RATIO * spread_ctl_coil, (
        f"the mis-paired quadrant assignment read {mis_leg:.6e} against the "
        f"correctly-paired {spread_ctl_coil:.6e} — under "
        f"{MISPAIRED_MIN_RATIO:.0f}x, so this census cannot tell a C4 image from "
        "a non-image and is measuring its own bug"
    )
    _print("[GEO-30] all three anchors green.", comm)


if __name__ == "__main__":
    main()
