"""`GEO-19` — the gapped, sheeted birdcage port fixture at ``leg_count = 16``.

Item (a) of the 32-port directive (§10 Phase 6). `GEO-18` built the gapped leg
box and its mid-plane sheet and gated the identity family at four legs; nothing
above four had ever been meshed, so Phase 6 had no cost and no evidence that the
identities are a property of the *construction* rather than of C4.

This module measures both at sixteen. The gates are `GEO-18`'s, restated at the
new count: the `GEO-9` tagged-volume partition, the terminal disks against
``2·π·r_leg²``, the sheets against their closed-form ``dx·g`` with the C16
spread, the conductor against its own CAD mass, and the layout's port-centre
separation against the generator's floor. The four-leg build in the same run is
the negative control: same code path, `GEO-18` step 2's records.

One gate reads differently here than at four legs, and only one: the terminal
*equality* half, which the 2026-08-25 review ruled asserts C_N symmetry of the
construction and so is read per azimuth class — see `TERMINAL_INTRA_CLASS_BAND`
and `_azimuth_class`. It is tighter than the flat band it replaces, reduces to
that band exactly at four legs, and moves no constant outside this module.

Two defects had to be cleared to get here, both on `main` before this module
runs. (a) The port halves were encoded as cell tags ``100+i`` and ``110+i``,
which collide for ``i >= 11`` — so the generator refused ``emit_port_sheets``
above nine legs outright, and the fixture this chunk was commissioned to measure
could not be built at all. The upper base is now ``200+i``; the lower tags are
untouched. (b) Step B replaced the axis-aligned box/sheet construction — which
raised ``NotImplementedError`` for any leg off a coordinate axis, i.e. for every
count above four — with the general local-frame one.

Step B is why the sheet readings below are frame-aware. At 22.5 deg a sheet is
neither x- nor y-normal, so its extents are the projections of its node
coordinates onto that port's own radial, azimuthal and axial directions; for a
port on a coordinate axis the projection reduces to the global bounding box term
by term, which is why the four-leg control still reads step 2's numbers. The
projection helpers are `PORT-9` leg (d1)'s, imported rather than restated.

Mesh-side only: no port model, no solve, no impedance, no resonance claim.
"""

from __future__ import annotations

import time
import traceback

import numpy as np
from mpi4py import MPI

from fem_em_solver.io.mesh import MeshGenerator, _interface_facet_tags
from tests.mesh.helpers import global_cell_tag_set
from tests.mesh.test_coil_phantom_conforming import _tag_volume, _total_volume
from tests.mesh.test_birdcage_conductor_sizing import CAD_MASS_GATE
from tests.mesh.test_birdcage_port_sheet_prerequisite import CONDUCTOR_RESOLUTION
from tests.mesh.test_birdcage_port_terminals import (
    AIR_IFACE,
    CONDUCTOR_IFACE,
    PHANTOM_IFACE,
    _global_facet_count,
    _interface_area_or_zero,
)
from tests.mesh.test_birdcage_port_tags import (
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
from tests.mesh.test_birdcage_leg_gaps import (
    LEG_GAP_LENGTH,
    TERMINAL_AREA_BAND,
    _analytic_box_volume,
    _analytic_terminal_area,
)
from tests.mesh.test_birdcage_port_sheets import (
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
    _port_boundary_partition,
)
from tests.mesh.test_birdcage_leg_offset import (
    _projected_extents,
    _sheet_azimuth_deg,
)

# The production count the 32-port directive asks the pricing for.
SCALED_LEG_COUNT = 16

# `birdcage_port_domain`'s default port clearance, the term that sets the gapped
# box width and so the layout's own separation floor.
PORT_CLEARANCE = 1.0e-3

# Measured 2026-08-23: the largest leg count whose azimuthal pitch on
# `RING_RADIUS` clears ``1.25·box_width``. The tag encoding admits 99; the
# geometry admits this. The 32-port directive's count is above it.
SEPARATION_LEG_COUNT_CEILING = 25

# `GEO-18` step 2's records on the four-leg fixture, **mesh-tagged to step B's
# local-frame construction** — the mesh this module actually builds. Two earlier
# digits are history and are deliberately not the asserted value: 116 416 on
# gmsh 4.13 / dolfinx 0.7.2, and 116 368 on the 0.11 image with the old
# axis-aligned construction (`20260823T213127Z_GEO-19-probe4.log`). Step B's own
# invariance control from `main` reads **116 085** sheeted (114 655 gapped, C4
# sheet spread 6.050e-16, terminal ratio 0.988616 x 4;
# `20260825T003437Z_GEO-19-stepB-invariance-main.log`), and the drift is ulp
# level in the box positions rather than geometry — ruling (4*), §7. The
# cell-count band is step 2's own 2%; the terminal ratio keeps its 1e-5, which
# neither re-measurement needed.
CONTROL_LEG_COUNT = 4
CONTROL_CELL_COUNT = 116085
CONTROL_CELL_COUNT_BAND = 0.02
CONTROL_TERMINAL_RATIO = 0.988616
CONTROL_TERMINAL_RATIO_BAND = 1.0e-5

# Step B's C4 sheet-area spread on the same fixture. Printed against the
# control's own reading rather than asserted at its own magnitude: the gate is
# `SHEET_SPREAD_BAND` below, and a summation-order difference at 1e-16 is not a
# finding. The digit is the reproduction evidence the §9 item asked for.
CONTROL_SHEET_SPREAD = 6.050e-16

# Gate (ii)'s equality half, under the **construction-symmetry ruling**
# (2026-08-25 10:30 review, `GEO-19` §7). Step C attempt 1 measured the sixteen
# terminal ratios taking exactly three values sorted by azimuth — 0.988616 at
# the eight multiples of 45 deg, 0.989367 at 22.5/157.5/202.5/337.5 deg,
# 0.989450 at 67.5/112.5/247.5/292.5 deg — with <= 2e-7 spread *inside* each
# class and 8.434e-04 *between* them
# (`20260825T124357Z_GEO-19-stepC-run1.log`). The ruling reads that as: the
# construction is exactly C16-covariant (sixteen copies of one disk), while the
# between-class term is the inscribed triangulation's azimuthal variation — it
# sits 13x below that triangulation's own ~1.1e-2 closed-form under-read of the
# disk. So the equality gate is per-class, and it is *tighter* than the old flat
# band, not looser:
#
#   * intra-class 1e-6 — measured basis <= 2e-7 at 16 legs (5x headroom) and
#     3.184e-08 at four, i.e. 10x tighter than the 1.0e-5 it replaces here;
#   * inter-class 5e-3 — measured basis 8.434e-04 (~6x headroom), the ceiling
#     placed at half the ~1.1e-2 under-read scale that owns the effect, so a
#     genuinely broken port cannot hide inside "reported structure".
#
# The 1.0e-5 is unmoved as the *C4 modules'* band (`test_birdcage_leg_gaps`,
# `test_birdcage_port_terminals`, `GEO-20`'s ring ports): nothing outside this
# module changes. The absolute inscribed band `TERMINAL_AREA_BAND` = [0.95, 1.0]
# is likewise unmoved and still asserted per port below.
TERMINAL_INTRA_CLASS_BAND = 1.0e-6
TERMINAL_INTER_CLASS_CEILING = 5.0e-3

# Azimuths come off the mesh (`_sheet_azimuth_deg`), so the class key snaps.
# The pitch at 16 legs is 22.5 deg and the readings land within ~1e-9 of it;
# 1e-3 deg is four orders below the pitch and four above the noise.
AZIMUTH_SNAP_DEG = 1.0e-3

# The sheet is a planar rectangle meshed by a conforming fragment: exact, and
# identical across ports up to floating-point summation order.
SHEET_SPREAD_BAND = 1.0e-12


def _azimuth_class(azimuth_deg):
    """The construction-symmetry class a port at this azimuth belongs to.

    The partition the ruling gates is not chosen from the measured areas — that
    would be circular — but from the *mesh's own* symmetry, then checked against
    the measurement:

    1. The air box and the phantom are symmetric under the coordinate mirrors
       ``x -> -x`` (``phi -> 180 - phi``) and ``y -> -y`` (``phi -> -phi``), so
       every azimuth folds into ``[0, 90]`` deg. That fold alone already
       reproduces the measured table: 22.5/157.5/202.5/337.5 all fold to 22.5,
       and 67.5/112.5/247.5/292.5 all fold to 67.5 — the two off-axis classes,
       exactly as read.
    2. The folds 0, 45 and 90 deg — the axis- and diagonal-aligned ports — read
       one value to <= 2e-7, so they are one class. That merge is empirical, and
       deliberately kept on the *asserting* side: if a future geometry splits
       them, it shows up as an intra-class red, which is a generator finding to
       report, not a re-record. The 90 deg rotation is **not** assumed anywhere
       else — assuming it would merge 22.5 with 67.5, and the measurement says
       those differ by 8.4e-05, well above the intra-class band.

    At ``leg_count = 4`` every port is aligned, so this returns one class and the
    per-class reading reduces to the old flat equality gate exactly. That
    identity is the back-compat control.
    """
    r = float(azimuth_deg) % 180.0
    if r > 90.0:
        r = 180.0 - r
    if abs(r - 45.0 * round(r / 45.0)) < AZIMUTH_SNAP_DEG:
        return "aligned"
    return f"{r:.3f} deg"


def _terminal_classes(m):
    """``{class key: [port indices]}``, ordered by class key."""
    classes = {}
    for i in m["ports"]:
        classes.setdefault(_azimuth_class(m["azimuth_deg"][i]), []).append(i)
    return {k: classes[k] for k in sorted(classes)}


def _layout(diagnostics):
    """The layout block of `birdcage_port_domain`'s diagnostics.

    `birdcage_port_layout_diagnostics`' own keys are nested under
    ``"port_layout"`` by the generator (`GEO-20` added a parallel
    ``"ring_port_layout"`` beside it), so gate (v) reads them through here
    rather than off the top level.
    """
    return diagnostics["port_layout"]


def _build(leg_count, emit_port_sheets):
    """The `GEO-18` step-2 fixture at an arbitrary leg count, with its wall time."""
    comm = MPI.COMM_WORLD
    started = time.perf_counter()
    mesh, cell_tags, facet_tags, diagnostics = MeshGenerator.birdcage_port_domain(
        leg_count=leg_count,
        ring_radius=RING_RADIUS,
        leg_width=LEG_WIDTH,
        leg_spacing=LEG_SPACING,
        coil_length=COIL_LENGTH,
        ring_minor_radius=RING_MINOR_RADIUS,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        leg_gap_length=LEG_GAP_LENGTH,
        emit_port_sheets=emit_port_sheets,
        air_padding=AIR_PADDING,
        resolution=RESOLUTION,
        conductor_resolution=CONDUCTOR_RESOLUTION,
        comm=comm,
        return_diagnostics=True,
    )
    return mesh, cell_tags, facet_tags, diagnostics, time.perf_counter() - started


def _measure(leg_count):
    """Every quantity the gates below read, for one sheeted build."""
    comm = MPI.COMM_WORLD
    ports = list(range(1, leg_count + 1))
    mesh, cells, _, diag, elapsed = _build(leg_count, True)

    halves = {i: (PORT_LOWER + i, PORT_UPPER + i) for i in ports}
    all_tags = [1, 2, 3, *[t for pair in halves.values() for t in pair]]
    tag_set = global_cell_tag_set(mesh, cells)

    volumes = {t: _tag_volume(mesh, cells, t, comm) for t in all_tags}
    v_total = _total_volume(mesh, comm)
    counts, areas = _port_boundary_partition(mesh, cells, comm, halves)

    sheet_tags = _interface_facet_tags(
        mesh, cells, {SHEET_IFACE + i: halves[i] for i in ports}
    )
    # Collective calls: every rank enters them here, never inside a rank-0
    # print (`GEO-18` step 2 attempt 1, 2026-08-22 — rank 0 blocked in the
    # allreduce and the command timed out at exit 124 with both tests green).
    sheet_area = {
        i: _interface_area_or_zero(mesh, sheet_tags, SHEET_IFACE + i, comm)
        for i in ports
    }
    # The port's own frame, read off the sheet rather than assumed: at 16 legs
    # only four of the sixteen sit on a coordinate axis. `_projected_extents`
    # returns the spans along (radial, azimuthal, axial) = (w, out-of-plane, h).
    azimuth_deg = {
        i: _sheet_azimuth_deg(mesh, sheet_tags, SHEET_IFACE + i, comm) for i in ports
    }
    sheet_frame = {}
    for i in ports:
        beta = np.radians(azimuth_deg[i])
        sheet_frame[i], _centre = _projected_extents(
            mesh,
            sheet_tags,
            SHEET_IFACE + i,
            comm,
            [
                [np.cos(beta), np.sin(beta), 0.0],
                [-np.sin(beta), np.cos(beta), 0.0],
                [0.0, 0.0, 1.0],
            ],
        )
    sheet_count = {
        i: _global_facet_count(mesh, sheet_tags, SHEET_IFACE + i, comm) for i in ports
    }
    return {
        "leg_count": leg_count,
        "ports": ports,
        "halves": halves,
        "tag_set": tag_set,
        "diag": diag,
        "elapsed": elapsed,
        "n_cells": mesh.topology.index_map(3).size_global,
        "volumes": volumes,
        "v_total": v_total,
        "counts": counts,
        "areas": areas,
        "sheet_area": sheet_area,
        "sheet_frame": sheet_frame,
        "azimuth_deg": azimuth_deg,
        "sheet_count": sheet_count,
        "cad_conductor": diag["cad_mass_by_group"]["conductor"],
    }


def _report(label, m):
    """Rank-0 record for one build. Per-port lines, printed once."""
    diag = m["diag"]
    dx, dy, dz = diag["port_box_size_m"]
    sheet_analytic = dx * dz
    box_area = 2.0 * (dx * dy + dy * dz + dz * dx)
    box_volume = dx * dy * dz
    terminal_analytic = _analytic_terminal_area()
    print(
        f"\n[GEO-19 {label}] leg_count={m['leg_count']} gapped+sheeted "
        f"g={LEG_GAP_LENGTH:.4e} m, box=({dx:.6e}, {dy:.6e}, {dz:.6e}) m, "
        f"h_c={CONDUCTOR_RESOLUTION:.4e} m: cells={m['n_cells']}  "
        f"mesh={diag['mesh_wall_time_s']:.2f} s  rung={m['elapsed']:.2f} s"
        f"\n[GEO-19 {label}] analytic sheet dx*g={sheet_analytic:.9e} m^2  "
        f"terminal (2 disks)={terminal_analytic:.9e} m^2  "
        f"box volume={box_volume:.9e} m^3  surface={box_area:.9e} m^2"
        f"\n[GEO-19 {label}] partition sum(tags)/total="
        f"{sum(m['volumes'].values()) / m['v_total']:.12f}  "
        f"total/analytic air box={m['v_total'] / _analytic_box_volume(dy):.12f}  "
        f"meshed/CAD conductor={m['volumes'][1] / m['cad_conductor']:.6f}  "
        f"port-centre separation={_layout(diag)['min_port_center_separation_m']:.6e} m "
        f"vs required {_layout(diag)['required_port_center_separation_m']:.6e} m "
        f"(margin {_layout(diag)['min_port_center_separation_m'] / _layout(diag)['required_port_center_separation_m']:.6f}x)",
        flush=True,
    )
    for i in m["ports"]:
        w_bbox, spread, h_bbox = m["sheet_frame"][i]
        a_c = m["areas"][CONDUCTOR_IFACE + i]
        a_a = m["areas"][AIR_IFACE + i]
        a_p = m["areas"][PHANTOM_IFACE + i]
        print(
            f"[GEO-19 {label}] P{i}: azimuth {m['azimuth_deg'][i]:.3f} deg  "
            f"sheet {m['sheet_count'][i]} facets "
            f"{m['sheet_area'][i]:.9e} m^2 "
            f"meshed/analytic={m['sheet_area'][i] / sheet_analytic:.12f}  "
            f"h={h_bbox:.9e} m  w_eff/w_bbox="
            f"{m['sheet_area'][i] / h_bbox / w_bbox:.12f}  "
            f"out-of-plane spread={spread:.3e} m  halves "
            f"{m['volumes'][PORT_LOWER + i] / box_volume:.12f}/"
            f"{m['volumes'][PORT_UPPER + i] / box_volume:.12f}  terminal "
            f"{m['counts'][CONDUCTOR_IFACE + i]} facets {a_c:.9e} m^2 "
            f"meshed/analytic={a_c / terminal_analytic:.9f}  "
            f"closure {(a_c + a_a + a_p) / box_area:.12f}",
            flush=True,
        )
    sheets = np.array([m["sheet_area"][i] for i in m["ports"]])
    terms = np.array([m["areas"][CONDUCTOR_IFACE + i] for i in m["ports"]])
    print(
        f"[GEO-19 {label}] C{m['leg_count']} sheet spread="
        f"{(sheets.max() - sheets.min()) / sheets.mean():.3e}  "
        f"terminal spread={(terms.max() - terms.min()) / terms.mean():.3e}  "
        f"terminal ratio min/max="
        f"{terms.min() / _analytic_terminal_area():.9f}/"
        f"{terms.max() / _analytic_terminal_area():.9f}",
        flush=True,
    )
    # Gate (ii)'s ruled reading, printed as the table it asserts.
    classes = _terminal_classes(m)
    means = []
    for key, members in classes.items():
        vals = np.array([m["areas"][CONDUCTOR_IFACE + i] for i in members])
        means.append(vals.mean())
        intra = (vals.max() - vals.min()) / vals.mean() if len(members) > 1 else 0.0
        azimuths = ", ".join(f"{m['azimuth_deg'][i]:.3f}" for i in members)
        print(
            f"[GEO-19 {label}] azimuth class '{key}': {len(members)} ports "
            f"[{azimuths}] deg  meshed/analytic="
            f"{vals.mean() / terminal_analytic:.9f}  intra-class spread="
            f"{intra:.3e} (band {TERMINAL_INTRA_CLASS_BAND})",
            flush=True,
        )
    means = np.array(means)
    inter = (means.max() - means.min()) / means.mean() if len(means) > 1 else 0.0
    print(
        f"[GEO-19 {label}] {len(classes)} azimuth classes, inter-class spread="
        f"{inter:.3e} (ceiling {TERMINAL_INTER_CLASS_CEILING})",
        flush=True,
    )


def _report_safely(label, m, comm):
    """Rank-0 `_report`, with any failure deferred past the next collective.

    A raise inside ``if comm.rank == 0`` leaves the other ranks blocked in the
    next collective, so the job hangs until the wall clock kills it instead of
    failing the test. Measured 2026-08-25 on this module's first run: a
    diagnostics `KeyError` in the 16-leg report turned 97 s of pytest into a
    561 s Status 124 (`20260825T123320Z_GEO-19-stepC.log`) — the whole heavy
    window for one wrong dictionary key. The message is broadcast and asserted
    after the gates, so nothing is swallowed.
    """
    problem = None
    if comm.rank == 0:
        try:
            _report(label, m)
        except Exception as exc:  # pragma: no cover - the deadlock guard itself
            traceback.print_exc()
            problem = f"{label}: the rank-0 record raised {exc!r}"
    return comm.bcast(problem, root=0)


def _assert_identity_family(m, label):
    """`GEO-18`'s gates (i)-(v), at whatever leg count `m` was built at."""
    diag = m["diag"]
    dx, dy, dz = diag["port_box_size_m"]
    sheet_analytic = dx * dz
    box_area = 2.0 * (dx * dy + dy * dz + dz * dx)
    box_volume = dx * dy * dz
    terminal_analytic = _analytic_terminal_area()
    ports = m["ports"]

    expected_tags = {1, 2, 3, *[t for pair in m["halves"].values() for t in pair]}
    assert m["tag_set"] == expected_tags, (
        f"{label}: the sheeted mesh carries cell tags {sorted(m['tag_set'])} "
        f"against the expected {sorted(expected_tags)}; at {m['leg_count']} legs "
        "the half encoding must still give every port its own disjoint pair"
    )

    # (i) `GEO-9` partition.
    assert abs(m["v_total"] / _analytic_box_volume(dy) - 1.0) < 1e-9, (
        f"{label}: meshed air box {m['v_total']:.9e} m^3 against its analytic "
        f"volume, ratio {m['v_total'] / _analytic_box_volume(dy):.12f}"
    )
    assert abs(sum(m["volumes"].values()) / m["v_total"] - 1.0) < 1e-9, (
        f"{label}: the tagged volumes sum to "
        f"{sum(m['volumes'].values()) / m['v_total']:.12f} of the mesh; at "
        f"{m['leg_count']} legs the tags no longer partition the domain"
    )

    for i in ports:
        for tag in m["halves"][i]:
            assert abs(m["volumes"][tag] / box_volume - 0.5) < 1e-9, (
                f"{label}: port P{i} cell tag {tag} is "
                f"{m['volumes'][tag] / box_volume:.12f} of the analytic gap box, "
                "not the half the mid-plane split must give"
            )

    # (iii) the sheets: whole, planar, at their closed-form area.
    for i in ports:
        w_bbox, spread, h_bbox = m["sheet_frame"][i]
        assert spread < 1e-12, (
            f"{label}: port P{i}'s sheet facets spread {spread:.3e} m out of "
            "their own plane; the reconstructed interface is not planar"
        )
        assert abs(h_bbox / dz - 1.0) < 1e-9, (
            f"{label}: port P{i}'s sheet runs {h_bbox:.9e} m along the current "
            f"direction against the gap {dz:.9e} m; it does not span the gap"
        )
        assert abs(m["sheet_area"][i] / sheet_analytic - 1.0) < 1e-9, (
            f"{label}: port P{i}'s sheet area {m['sheet_area'][i]:.9e} m^2 "
            f"against the analytic mid-section {sheet_analytic:.9e} m^2 (ratio "
            f"{m['sheet_area'][i] / sheet_analytic:.12f})"
        )
        assert abs(m["sheet_area"][i] / h_bbox / w_bbox - 1.0) < 1e-9, (
            f"{label}: port P{i}'s effective width A/h="
            f"{m['sheet_area'][i] / h_bbox:.9e} m differs from its bounding-box "
            f"extent {w_bbox:.9e} m; the facet set is ragged or partial"
        )

    sheets = np.array([m["sheet_area"][i] for i in ports])
    spread = (sheets.max() - sheets.min()) / sheets.mean()
    assert spread < SHEET_SPREAD_BAND, (
        f"{label}: the {m['leg_count']} sheet areas differ by {spread:.3e} "
        f"relative against the pre-stated {SHEET_SPREAD_BAND}; the ports are not "
        f"C{m['leg_count']}-equivalent"
    )

    # (ii) the terminals, and the closure that makes them readable as terminals.
    for i in ports:
        total = (
            m["areas"][CONDUCTOR_IFACE + i]
            + m["areas"][AIR_IFACE + i]
            + m["areas"][PHANTOM_IFACE + i]
        )
        assert abs(total / box_area - 1.0) < 1e-9, (
            f"{label}: port P{i}'s halves bound {total:.9e} m^2 against the "
            f"analytic box surface {box_area:.9e} m^2 (ratio "
            f"{total / box_area:.12f}); the split leaked boundary"
        )
        ratio = m["areas"][CONDUCTOR_IFACE + i] / terminal_analytic
        low, high = TERMINAL_AREA_BAND
        assert low <= ratio <= high, (
            f"{label}: port P{i}'s terminal area is {ratio:.9f} of the closed "
            f"form, outside `GEO-18` step 1's inscribed band [{low}, {high}]"
        )
        assert m["areas"][PHANTOM_IFACE + i] == 0.0
        assert m["counts"][CONDUCTOR_IFACE + i] > 0

    # The equality half, per azimuth class (the 2026-08-25 ruling). Intra-class
    # is the C_N covariance of the *construction*; inter-class is the
    # discretization's azimuthal variation under a coarse ceiling.
    classes = _terminal_classes(m)
    class_means = {}
    for key, members in classes.items():
        vals = np.array([m["areas"][CONDUCTOR_IFACE + i] for i in members])
        class_means[key] = vals.mean()
        if len(members) == 1:
            continue
        intra = (vals.max() - vals.min()) / vals.mean()
        assert intra < TERMINAL_INTRA_CLASS_BAND, (
            f"{label}: the {len(members)} terminal areas in azimuth class "
            f"'{key}' (ports {members}) differ by {intra:.3e} relative against "
            f"the pre-stated {TERMINAL_INTRA_CLASS_BAND}; within one class the "
            "ports are the same disk under a symmetry of the mesh, so this is "
            "the construction losing C_N covariance — a generator finding, not "
            "a band to widen"
        )

    means = np.array(list(class_means.values()))
    inter = (means.max() - means.min()) / means.mean() if len(means) > 1 else 0.0
    assert inter < TERMINAL_INTER_CLASS_CEILING, (
        f"{label}: the {len(class_means)} azimuth-class terminal means "
        f"{ {k: float(v) for k, v in class_means.items()} } spread "
        f"{inter:.3e} relative against the discretization ceiling "
        f"{TERMINAL_INTER_CLASS_CEILING}; that is the scale of the inscribed "
        "triangulation's own ~1.1e-2 under-read, so a spread this large is a "
        "broken port rather than azimuthal meshing variation"
    )

    # (iv) the conductor still carries its CAD mass at the graded sizing.
    cad_ratio = m["volumes"][1] / m["cad_conductor"]
    assert cad_ratio >= CAD_MASS_GATE, (
        f"{label}: the graded conductor keeps {cad_ratio:.6f} of its own CAD "
        f"mass {m['cad_conductor']:.9e} m^3, below the imported {CAD_MASS_GATE} "
        f"gate; {m['leg_count']} legs at h_c={CONDUCTOR_RESOLUTION:.4e} m are "
        "under-resolved"
    )

    # (v) the layout's own clearance floor, at the new azimuthal pitch.
    sep = _layout(diag)["min_port_center_separation_m"]
    required = _layout(diag)["required_port_center_separation_m"]
    assert sep >= required, (
        f"{label}: minimum port-centre separation {sep:.6e} m is below the "
        f"generator's floor {required:.6e} m; the production geometry needs a "
        "larger ring or narrower boxes, which is the finding — do not shrink "
        "the boxes to make this pass"
    )


def test_sixteen_leg_identity_family_and_cost_rung():
    """The `GEO-18` identity family at 16 legs, with 4 legs as the control.

    1. **Sixteen legs** — gates (i)-(v) of the `GEO-19` entry: the `GEO-9`
       partition, the 32 half-boxes, the 16 sheets at ``dx·g`` with the C16
       spread, the 16 terminal disks in the inscribed band and equal per
       azimuth class (intra 1e-6, inter 5e-3 — the 2026-08-25 ruling),
       the conductor against its CAD mass, and the port-centre separation
       against the generator's floor. Cells and mesh wall time are printed:
       Phase 6's first measured cost rung.
    2. **Four legs, same code path** — `GEO-18` step 2's records, which fixes
       that anything gate 1 measures is the construction and not the count.
    """
    comm = MPI.COMM_WORLD

    scaled = _measure(SCALED_LEG_COUNT)
    problems = [_report_safely("16 legs", scaled, comm)]

    # The control second, so the 16-leg numbers are already in the log if gmsh
    # dies on the second build (`GEO-18` step 1's ordering, same reason).
    control = _measure(CONTROL_LEG_COUNT)
    problems.append(_report_safely("4 legs (control)", control, comm))
    if comm.rank == 0:
        ctl_sheets = np.array([control["sheet_area"][i] for i in control["ports"]])
        ctl_spread = (ctl_sheets.max() - ctl_sheets.min()) / ctl_sheets.mean()
        print(
            f"[GEO-19 control vs step B record] cells {control['n_cells']} vs "
            f"{CONTROL_CELL_COUNT} (delta "
            f"{control['n_cells'] - CONTROL_CELL_COUNT}, relative "
            f"{control['n_cells'] / CONTROL_CELL_COUNT - 1.0:.3e})  C4 sheet "
            f"spread {ctl_spread:.3e} vs {CONTROL_SHEET_SPREAD:.3e}",
            flush=True,
        )
        print(
            f"[GEO-19 cost rung] 4 -> 16 legs: cells "
            f"{control['n_cells']} -> {scaled['n_cells']} "
            f"({scaled['n_cells'] / control['n_cells']:.4f}x)  mesh "
            f"{control['diag']['mesh_wall_time_s']:.2f} -> "
            f"{scaled['diag']['mesh_wall_time_s']:.2f} s "
            f"({scaled['diag']['mesh_wall_time_s'] / control['diag']['mesh_wall_time_s']:.4f}x)",
            flush=True,
        )

    _assert_identity_family(scaled, "16 legs")
    _assert_identity_family(control, "4 legs (control)")
    assert not [p for p in problems if p], [p for p in problems if p]

    assert (
        abs(control["n_cells"] / CONTROL_CELL_COUNT - 1.0) < CONTROL_CELL_COUNT_BAND
    ), (
        f"the control meshed {control['n_cells']} cells against `GEO-18` step 2's "
        f"0.11 re-record {CONTROL_CELL_COUNT}; the tag-encoding change moved the "
        "geometry, which it must not"
    )
    terminal_analytic = _analytic_terminal_area()
    for i in control["ports"]:
        ratio = control["areas"][CONDUCTOR_IFACE + i] / terminal_analytic
        assert abs(ratio - CONTROL_TERMINAL_RATIO) < CONTROL_TERMINAL_RATIO_BAND, (
            f"the control's port P{i} terminal ratio {ratio:.9f} against step 2's "
            f"record {CONTROL_TERMINAL_RATIO}"
        )


def test_sheet_encoding_admits_the_production_leg_count():
    """The half tags stay disjoint up to the encoding's stated ceiling.

    The ``110+i`` encoding collided at ``i >= 11``, so the generator refused
    ``emit_port_sheets`` above nine legs — `GEO-19`'s fixture could not be
    built. This is the arithmetic that replaced it, asserted without meshing:
    disjoint through 99 legs, which covers the 32-port directive's 16, and a
    rejected call above it rather than a silent collision — and the leg count
    the *layout* admits on this ring, which turns out to be the smaller number.
    """
    for leg_count in (4, 16, 32, 99):
        lower = {PORT_LOWER + i for i in range(1, leg_count + 1)}
        upper = {PORT_UPPER + i for i in range(1, leg_count + 1)}
        assert not (lower & upper), (
            f"the half tags collide at leg_count={leg_count}: "
            f"{sorted(lower & upper)} is both a lower and an upper port tag"
        )

    # The encoding ceiling is not the binding one. On this ring the layout's
    # own clearance floor bites first: the leg pitch is
    # ``2·ring_radius·sin(pi/N)`` against ``1.25·box_width`` = 1.750000e-02 m,
    # so N <= 25 (measured 2026-08-23: N=100 is rejected at 4.397506e-03 m, not
    # at the tag encoding). Recorded, not worked around — the 32-port
    # directive's own count is on the wrong side of it.
    box_width = 2.0 * (0.5 * LEG_WIDTH) + 2.0 * PORT_CLEARANCE
    required = max(5.0e-4, 1.25 * box_width)
    fits = [
        n
        for n in range(3, 65)
        if 2.0 * RING_RADIUS * np.sin(np.pi / n) >= required
    ]
    assert max(fits) == SEPARATION_LEG_COUNT_CEILING, (
        f"the clearance floor {required:.6e} m on ring_radius={RING_RADIUS} m "
        f"admits up to {max(fits)} legs, not the recorded "
        f"{SEPARATION_LEG_COUNT_CEILING}"
    )
    assert SCALED_LEG_COUNT in fits
    assert 32 not in fits, (
        "32 legs now clear the separation floor; the directive's production "
        "count was measured below it on 2026-08-23 and the record must move "
        "with the geometry that changed it"
    )
