"""`GEO-20` step 2 — the ring-gap port layout at 16 legs: **32 ring ports**.

Step 1 (2026-08-24) built the high-pass layout at four legs and closed its
identity family: eight ring ports, terminals at 0.974455 of the closed-form
``2·pi·r_ring²`` and equal across the eight to ~2e-8, closure / port volume /
sheet all 1.000000000000. This module runs the *same* construction at the
production leg count of item (b) of the §10 32-port directive — ``2·16 = 32``
ring ports — and re-reads every one of those identities there.

Two things are genuinely new at 16, and only two:

1. **The symmetry group is C16, not C4.** The exact forms (port volume, sheet
   area) are gated at `SYMMETRY` across all 32, as before; that band does not
   move with the count because those forms are exact under a linear mesh.
2. **The terminal equality is read per azimuth class.** `GEO-19` step C
   measured the *leg* terminals splitting into three azimuth classes at 16 legs
   (8.434e-04 between, <= 2e-7 inside) and the 2026-08-25 review **ruled** that
   reading: the inscribed triangulation of a disk varies with azimuth against a
   box the air mesh does not rotate with, so the flat 1e-5 band is a C4 band
   applied to C16. The ruling's per-class bands — `TERMINAL_INTRA_CLASS_BAND`
   1e-6 and `TERMINAL_INTER_CLASS_CEILING` 5e-3 — are imported and applied to
   the 32 ring terminals **from the start**, so this module never lands, and
   never has to widen, a flat band it already knows is the wrong shape. The
   class table is printed whatever it reads.

The ring gap centres sit at ``phi = 2·pi·j/N + pi/N``, i.e. 11.25 + 22.5·j deg
at 16 legs, so *none* of them is axis- or diagonal-aligned and the fold in
`_azimuth_class` predicts **four** classes (11.25 / 33.75 / 56.25 / 78.75 deg)
where the legs gave three. At four legs the gap centres are 45/135/225/315 deg,
which all fold to "aligned" — one class — so the 4-leg control below reduces to
step 1's flat gate exactly, which is what makes the per-class reading a
refinement rather than a different test.

Mesh-side only, as step 1 was: no port model at 32 ports, no drive, no solve,
and no F-human claim — this is F-small (0.07 m ring) at 16 legs.
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
from tests.mesh.test_birdcage_port_sheet_prerequisite import (
    CELL_COUNT_BAND,
    CONDUCTOR_RESOLUTION,
)
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
    PORT_BOX_SIZE,
    RESOLUTION,
    RING_MINOR_RADIUS,
    RING_RADIUS,
)
from tests.mesh.test_birdcage_leg_gaps import (
    TERMINAL_AREA_BAND,
    _analytic_box_volume,
)
from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER, SHEET_IFACE
from tests.mesh.test_birdcage_leg_offset import _sheet_azimuth_deg
from tests.mesh.test_birdcage_ring_gaps import (
    EXACT,
    RING_GAP_CELL_RECORD,
    RING_GAP_LENGTH,
    RING_TERMINAL_RATIO,
    RING_TERMINAL_RATIO_BAND,
    SYMMETRY,
    _out_of_plane_spread,
    _port_boundary_partition,
    _spread,
)
from tests.mesh.test_birdcage_port_scaleup import (
    CONTROL_CELL_COUNT_BAND,
    SCALED_LEG_COUNT,
    TERMINAL_INTER_CLASS_CEILING,
    TERMINAL_INTRA_CLASS_BAND,
    _azimuth_class,
    _measure,
)

CONTROL_LEG_COUNT = 4

# `GEO-19` step C's 16-leg cost rung, from the ruled record run
# `20260825T170523Z_GEO-19-stepC-ruled-record.log`: the *leg*-gapped, sheeted
# 16-leg build meshes 307 296 cells with a C16 sheet-area spread of 1.331e-15.
# Negative control (i) below rebuilds exactly that fixture — `ring_gap_length`
# off, everything else identical — so a ring-gap opt-in that leaked into the
# default geometry fails here rather than being absorbed into the 16-leg
# numbers. The band is the scale-up module's own 2%.
SCALED_CONTROL_CELL_COUNT = 307296
SCALED_CONTROL_SHEET_SPREAD = 1.331e-15

# The step-1 4-leg ring-gap record (`RING_GAP_CELL_RECORD` = 110 786 cells,
# `RING_TERMINAL_RATIO` = 0.974455) is imported, not restated — control (ii).

# Predicted from the construction, asserted as a structural claim: 16 gap
# centres at 11.25 + 22.5·j deg fold into four classes under `_azimuth_class`,
# and four gap centres at 45 + 90·j deg fold into one.
EXPECTED_CLASS_COUNT = {16: 4, 4: 1}


def _ring_ports(leg_count):
    """The ring-port ordinals at this leg count: ``2·N`` of them, after the legs."""
    first = leg_count + 1
    return list(range(first, first + 2 * leg_count))


def _mirror_pairs(leg_count):
    """Bottom/top ring port pairs — the same gap on the two rings.

    Build order is bottom ring then top, `leg_count` gaps each, so ordinal
    ``first + j`` and ``first + leg_count + j`` are one gap's two images.
    """
    first = leg_count + 1
    return [(first + j, first + leg_count + j) for j in range(leg_count)]


def _ring_gap_frame(ordinal, leg_count):
    """``(phi_hat, gap centre)`` for a ring port, from its ordinal alone.

    `test_birdcage_ring_gaps._ring_gap_frame` with the leg count lifted out of
    the module constant; the plane is the radial one at ``phi_c``, whose normal
    is azimuthal, which is why the flatness check needs it (no global coordinate
    is constant on a ring sheet).
    """
    first = leg_count + 1
    j = (ordinal - first) % leg_count
    z_sign = -1.0 if ordinal < first + leg_count else +1.0
    phi_c = 2.0 * np.pi * j / leg_count + np.pi / leg_count
    return (
        np.array([-np.sin(phi_c), np.cos(phi_c), 0.0]),
        np.array(
            [
                RING_RADIUS * np.cos(phi_c),
                RING_RADIUS * np.sin(phi_c),
                z_sign * 0.5 * LEG_SPACING,
            ]
        ),
    )


def _measure_ring(leg_count):
    """Everything the gates read, for one ring-gapped sheeted build at `N` legs."""
    comm = MPI.COMM_WORLD
    started = time.perf_counter()
    mesh, cells, _facets, diag = MeshGenerator.birdcage_port_domain(
        leg_count=leg_count,
        ring_radius=RING_RADIUS,
        leg_width=LEG_WIDTH,
        leg_spacing=LEG_SPACING,
        coil_length=COIL_LENGTH,
        ring_minor_radius=RING_MINOR_RADIUS,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        port_box_size=PORT_BOX_SIZE,
        leg_gap_length=None,
        ring_gap_length=RING_GAP_LENGTH,
        emit_port_sheets=True,
        air_padding=AIR_PADDING,
        resolution=RESOLUTION,
        conductor_resolution=CONDUCTOR_RESOLUTION,
        comm=comm,
        return_diagnostics=True,
    )
    elapsed = time.perf_counter() - started

    ring_ports = _ring_ports(leg_count)
    # The legs are uncut in the high-pass layout, so their boxes float as single
    # regions with no terminals; only the ring ports are split by a sheet. That
    # asymmetry *is* the high-pass fixture and is asserted, not assumed.
    port_cell_tags = {i: (PORT_LOWER + i,) for i in range(1, leg_count + 1)}
    port_cell_tags.update({i: (PORT_LOWER + i, PORT_UPPER + i) for i in ring_ports})
    expected_tags = {1, 2, 3, *[t for tags in port_cell_tags.values() for t in tags]}

    all_tags = sorted(expected_tags)
    volumes = {t: _tag_volume(mesh, cells, t, comm) for t in all_tags}
    counts, areas = _port_boundary_partition(mesh, cells, comm, port_cell_tags)
    sheet_tags = _interface_facet_tags(
        mesh, cells, {SHEET_IFACE + i: port_cell_tags[i] for i in ring_ports}
    )
    # Every collective below is entered by every rank, never inside a rank-0
    # print (`GEO-18` step 2 attempt 1: rank 0 blocked in an allreduce and the
    # command timed out at exit 124 with the tests green).
    return {
        "leg_count": leg_count,
        "ring_ports": ring_ports,
        # The mesh objects themselves are carried so a consumer can export them
        # without rebuilding (`EX-35`/`mesh:9` writes the 32-sheet XDMF from
        # this dict, the same hunk `EX-33` added to `_measure`). Additive: no
        # gate below reads them.
        "mesh": mesh,
        "cells": cells,
        "sheet_tags": sheet_tags,
        "port_cell_tags": port_cell_tags,
        "tag_set": global_cell_tag_set(mesh, cells),
        "expected_tags": expected_tags,
        "diag": diag,
        "elapsed": elapsed,
        "n_cells": mesh.topology.index_map(3).size_global,
        "volumes": volumes,
        "v_total": _total_volume(mesh, comm),
        "counts": counts,
        "areas": areas,
        "port_volume": {
            i: sum(volumes[t] for t in port_cell_tags[i]) for i in ring_ports
        },
        "sheet_area": {
            i: _interface_area_or_zero(mesh, sheet_tags, SHEET_IFACE + i, comm)
            for i in ring_ports
        },
        "sheet_count": {
            i: _global_facet_count(mesh, sheet_tags, SHEET_IFACE + i, comm)
            for i in ring_ports
        },
        "sheet_flatness": {
            i: _out_of_plane_spread(
                mesh, sheet_tags, SHEET_IFACE + i, *_ring_gap_frame(i, leg_count), comm
            )
            for i in ring_ports
        },
        # Read off the mesh, not assumed from the ordinal: the class key must
        # come from where the sheet actually is (`GEO-19` step C's reading).
        "azimuth_deg": {
            i: _sheet_azimuth_deg(mesh, sheet_tags, SHEET_IFACE + i, comm)
            for i in ring_ports
        },
        "cad_conductor": diag["cad_mass_by_group"]["conductor"],
    }


def _terminal_classes(m):
    """``{class key: [ring port ordinals]}``, ordered by key."""
    classes = {}
    for i in m["ring_ports"]:
        classes.setdefault(_azimuth_class(m["azimuth_deg"][i]), []).append(i)
    return {k: classes[k] for k in sorted(classes)}


def _report(label, m):
    """Rank-0 record for one ring-gapped build: per-port lines and the class table."""
    layout = m["diag"]["ring_port_layout"]
    terminal_analytic = layout["ring_terminal_area_m2"]
    port_volume = layout["ring_port_volume_m3"]
    port_surface = layout["ring_port_surface_m2"]
    sheet_analytic = layout["ring_port_sheet_area_m2"]
    n = m["leg_count"]
    print(
        f"\n[GEO-20 step 2 {label}] leg_count={n} ring-gapped+sheeted "
        f"g={RING_GAP_LENGTH:.4e} m, alpha="
        f"{layout['ring_gap_half_angle_rad']:.9e} rad, "
        f"w={layout['ring_port_box_width_m']:.6e} m, "
        f"h_c={CONDUCTOR_RESOLUTION:.4e} m: cells={m['n_cells']}  ports="
        f"{len(m['port_cell_tags'])} ({n} leg + {len(m['ring_ports'])} ring)  "
        f"mesh={m['diag']['mesh_wall_time_s']:.2f} s  rung={m['elapsed']:.2f} s"
        f"\n[GEO-20 step 2 {label}] closed forms: terminal (2 disks) "
        f"{terminal_analytic:.9e} m^2, port volume {port_volume:.9e} m^3, "
        f"port surface {port_surface:.9e} m^2, sheet {sheet_analytic:.9e} m^2"
        f"\n[GEO-20 step 2 {label}] partition sum(tags)/total="
        f"{sum(m['volumes'].values()) / m['v_total']:.12f}  total/analytic air "
        f"box={m['v_total'] / _analytic_box_volume(PORT_BOX_SIZE[1]):.12f}  "
        f"meshed/CAD conductor={m['volumes'][1] / m['cad_conductor']:.6f}"
        f"\n[GEO-20 step 2 {label}] ring primitives (Pappus, pre-boolean): "
        f"{m['diag']['ring_cad_mass_m3']:.12e} / "
        f"{m['diag']['ring_analytic_mass_m3']:.12e} = "
        f"{m['diag']['ring_cad_mass_m3'] / m['diag']['ring_analytic_mass_m3']:.12f}"
        f"\n[GEO-20 step 2 {label}] leg-arc clearance "
        f"{layout['ring_leg_arc_clearance_m']:.6e} m, phantom clearance "
        f"{layout['ring_phantom_radial_clearance_m']:.6e} m",
        flush=True,
    )
    for i in m["ring_ports"]:
        a_c = m["areas"][CONDUCTOR_IFACE + i]
        a_a = m["areas"][AIR_IFACE + i]
        a_p = m["areas"][PHANTOM_IFACE + i]
        print(
            f"[GEO-20 step 2 {label}] P{i}: azimuth {m['azimuth_deg'][i]:.3f} deg  "
            f"conductor {m['counts'][CONDUCTOR_IFACE + i]} facets {a_c:.9e} m^2 "
            f"meshed/analytic={a_c / terminal_analytic:.9f}  air "
            f"{m['counts'][AIR_IFACE + i]} facets {a_a:.9e} m^2  phantom "
            f"{a_p:.6e} m^2  closure {(a_c + a_a + a_p) / port_surface:.12f}  "
            f"volume/analytic {m['port_volume'][i] / port_volume:.12f}  sheet "
            f"{m['sheet_count'][i]} facets {m['sheet_area'][i]:.9e} m^2 "
            f"meshed/analytic={m['sheet_area'][i] / sheet_analytic:.12f}  "
            f"out-of-plane {m['sheet_flatness'][i]:.3e} m",
            flush=True,
        )
    sheets = np.array([m["sheet_area"][i] for i in m["ring_ports"]])
    terms = np.array([m["areas"][CONDUCTOR_IFACE + i] for i in m["ring_ports"]])
    print(
        f"[GEO-20 step 2 {label}] C{2 * n} sheet spread={_spread(sheets):.3e}  "
        f"terminal spread={_spread(terms):.3e}  terminal ratio min/max="
        f"{terms.min() / terminal_analytic:.9f}/"
        f"{terms.max() / terminal_analytic:.9f}",
        flush=True,
    )
    classes = _terminal_classes(m)
    means = []
    for key, members in classes.items():
        vals = np.array([m["areas"][CONDUCTOR_IFACE + i] for i in members])
        means.append(vals.mean())
        intra = (vals.max() - vals.min()) / vals.mean() if len(members) > 1 else 0.0
        azimuths = ", ".join(f"{m['azimuth_deg'][i]:.3f}" for i in members)
        print(
            f"[GEO-20 step 2 {label}] azimuth class '{key}': {len(members)} ports "
            f"[{azimuths}] deg  meshed/analytic={vals.mean() / terminal_analytic:.9f}"
            f"  intra-class spread={intra:.3e} (band {TERMINAL_INTRA_CLASS_BAND})",
            flush=True,
        )
    means = np.array(means)
    inter = (means.max() - means.min()) / means.mean() if len(means) > 1 else 0.0
    print(
        f"[GEO-20 step 2 {label}] {len(classes)} azimuth classes, inter-class "
        f"spread={inter:.3e} (ceiling {TERMINAL_INTER_CLASS_CEILING})",
        flush=True,
    )


def _report_safely(label, m, comm):
    """Rank-0 `_report`, with any failure deferred past the next collective.

    A raise inside ``if comm.rank == 0`` leaves the other ranks blocked in the
    next collective, so the job hangs until the wall clock kills it instead of
    failing (`GEO-19` step C, 2026-08-25: a `KeyError` in the report turned 97 s
    of pytest into a 561 s Status 124). The message is broadcast and asserted
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


def _assert_ring_identity_family(m, label):
    """Step 1's gates at whatever leg count `m` was built at, terminals per class."""
    layout = m["diag"]["ring_port_layout"]
    terminal_analytic = layout["ring_terminal_area_m2"]
    port_volume = layout["ring_port_volume_m3"]
    port_surface = layout["ring_port_surface_m2"]
    sheet_analytic = layout["ring_port_sheet_area_m2"]
    ring_ports = m["ring_ports"]

    assert m["tag_set"] == m["expected_tags"], (
        f"{label}: the ring-gapped mesh does not carry both halves of every ring "
        f"port as their own cell tags (got {sorted(m['tag_set'])}, expected "
        f"{sorted(m['expected_tags'])}), so there is no interface to rebuild the "
        "sheets from"
    )

    # `GEO-9`: still a partition of the same air box.
    box = _analytic_box_volume(PORT_BOX_SIZE[1])
    assert abs(m["v_total"] / box - 1.0) < EXACT, (
        f"{label}: meshed total {m['v_total']:.12e} m^3 against the analytic air "
        f"box {box:.12e} m^3"
    )
    assert abs(sum(m["volumes"].values()) / m["v_total"] - 1.0) < EXACT, (
        f"{label}: the tagged volumes do not partition the mesh "
        f"({sum(m['volumes'].values()) / m['v_total']:.12f})"
    )

    # Mass: the arcs are the arcs asked for, by Pappus on the primitives. The
    # union form (gapped = uncut - removed) is deliberately *not* gated — step 1
    # measured it 1e-6 off at four legs from OCC quadrature over 28 curved
    # pieces, and 16 legs has more of them, not fewer. It is printed above.
    primitive = m["diag"]["ring_cad_mass_m3"] / m["diag"]["ring_analytic_mass_m3"]
    assert abs(primitive - 1.0) < EXACT, (
        f"{label}: the {len(ring_ports)} ring arcs have CAD mass "
        f"{m['diag']['ring_cad_mass_m3']:.12e} m^3 against Pappus' "
        f"{m['diag']['ring_analytic_mass_m3']:.12e} m^3 (ratio {primitive:.12f}); "
        f"the swept angle is not `2*pi/N - g/R`"
    )
    cad_ratio = m["volumes"][1] / m["cad_conductor"]
    assert cad_ratio >= CAD_MASS_GATE, (
        f"{label}: the ring-gapped graded conductor keeps {cad_ratio:.6f} of its "
        f"own CAD mass {m['cad_conductor']:.9e} m^3, below the imported "
        f"{CAD_MASS_GATE} gate"
    )

    low, high = TERMINAL_AREA_BAND
    for i in ring_ports:
        a_c = m["areas"][CONDUCTOR_IFACE + i]
        total = a_c + m["areas"][AIR_IFACE + i] + m["areas"][PHANTOM_IFACE + i]
        assert abs(total / port_surface - 1.0) < EXACT, (
            f"{label}: ring port P{i} boundary areas sum to {total:.9e} m^2 "
            f"against the analytic wedge surface {port_surface:.9e} m^2 (ratio "
            f"{total / port_surface:.12f}); the partition is not exhaustive, so "
            "the terminal reading would be a fragment, not the terminal"
        )
        assert abs(m["port_volume"][i] / port_volume - 1.0) < EXACT, (
            f"{label}: ring port P{i} meshed volume {m['port_volume'][i]:.9e} m^3 "
            f"against the analytic wedge {port_volume:.9e} m^3 — the solid does "
            "not span the gap exactly, so its radial faces are not the ring's "
            "cut faces"
        )
        ratio = a_c / terminal_analytic
        assert low <= ratio <= high, (
            f"{label}: ring port P{i} terminal area {a_c:.9e} m^2 is "
            f"{ratio:.9f} of the closed-form {terminal_analytic:.9e} m^2 (two "
            f"disks of radius {RING_MINOR_RADIUS:.6e} m); an inscribed "
            f"triangulation must land in [{low}, {high}]"
        )
        assert m["areas"][PHANTOM_IFACE + i] == 0.0, (
            f"{label}: ring port P{i} touches the phantom "
            f"({m['areas'][PHANTOM_IFACE + i]:.6e} m^2); the gap solid is "
            "supposed to meet metal and air only"
        )
        assert abs(m["sheet_area"][i] / sheet_analytic - 1.0) < EXACT, (
            f"{label}: ring port P{i} sheet area {m['sheet_area'][i]:.9e} m^2 "
            f"against the analytic mid-section {sheet_analytic:.9e} m^2 (ratio "
            f"{m['sheet_area'][i] / sheet_analytic:.12f}); the reconstructed "
            "facet set is not the whole w x w rectangle"
        )
        assert m["sheet_flatness"][i] < SYMMETRY, (
            f"{label}: ring port P{i} sheet is {m['sheet_flatness'][i]:.3e} m out "
            "of its own radial plane; the reconstructed facet set is not the "
            "mid-section"
        )

    # C_{2N} on the exact forms, and the top/bottom ring mirror.
    for tag, values in (
        ("volume", [m["port_volume"][i] for i in ring_ports]),
        ("sheet", [m["sheet_area"][i] for i in ring_ports]),
    ):
        assert _spread(values) < SYMMETRY, (
            f"{label}: ring port {tag}s are not C{len(ring_ports)}-symmetric to "
            f"{SYMMETRY} (spread {_spread(values):.3e}); the {len(ring_ports)} "
            "ring ports are not the same port"
        )
    for lo_port, hi_port in _mirror_pairs(m["leg_count"]):
        for tag, table in (("volume", m["port_volume"]), ("sheet", m["sheet_area"])):
            lo_v, hi_v = table[lo_port], table[hi_port]
            assert abs(hi_v / lo_v - 1.0) < SYMMETRY, (
                f"{label}: ring {tag} mirror pair P{lo_port}/P{hi_port} reads "
                f"{lo_v:.12e} / {hi_v:.12e} (ratio {hi_v / lo_v:.12f}); the top "
                "and bottom rings are not mirror images"
            )

    # Terminal equality, per azimuth class — the 2026-08-25 ruling, applied to
    # the ring family from the start rather than after a red flat band.
    classes = _terminal_classes(m)
    assert len(classes) == EXPECTED_CLASS_COUNT[m["leg_count"]], (
        f"{label}: the {len(ring_ports)} ring terminals fall into "
        f"{len(classes)} azimuth classes ({list(classes)}), not the "
        f"{EXPECTED_CLASS_COUNT[m['leg_count']]} the construction predicts; the "
        "gap centres are not at `2*pi*j/N + pi/N`"
    )
    means = []
    for key, members in classes.items():
        vals = np.array([m["areas"][CONDUCTOR_IFACE + i] for i in members])
        means.append(vals.mean())
        intra = (vals.max() - vals.min()) / vals.mean() if len(members) > 1 else 0.0
        assert intra < TERMINAL_INTRA_CLASS_BAND, (
            f"{label}: azimuth class '{key}' ({len(members)} ports) has "
            f"intra-class terminal spread {intra:.3e} against the imported "
            f"{TERMINAL_INTRA_CLASS_BAND}; inside one class the construction is "
            "exactly covariant, so this is a generator finding, not a band to "
            "widen"
        )
    means = np.array(means)
    inter = (means.max() - means.min()) / means.mean() if len(means) > 1 else 0.0
    assert inter < TERMINAL_INTER_CLASS_CEILING, (
        f"{label}: inter-class terminal spread {inter:.3e} against the imported "
        f"ceiling {TERMINAL_INTER_CLASS_CEILING}; that is the scale of the "
        "inscribed triangulation's own under-read, so a port is genuinely broken"
    )


def test_thirty_two_ring_ports_at_sixteen_legs():
    """`GEO-20` step 2: the high-pass layout at the production leg count.

    1. **32 ring ports** — step 1's identity family re-read at 16 legs: the
       `GEO-9` partition and the air-box closure, the 64 half-boxes, every port
       solid at its analytic wedge volume and every sheet at ``w²`` to 1e-9 with
       C32 spread and the top/bottom mirror below 1e-12, the terminals inside
       the inscribed [0.95, 1.0] band and equal **per azimuth class** (intra
       1e-6, inter 5e-3), the ring arcs against Pappus, and the conductor
       against its own CAD mass.
    2. **Control (i), the kwarg off at 16 legs** — the leg-gapped sheeted
       fixture `GEO-19` step C recorded: 307 296 cells inside 2% with its C16
       sheet spread. The ring opt-in must not touch the default geometry.
    3. **Control (ii), four legs on this same code path** — step 1's 110 786
       cells and 0.974455 terminal ratio inside their own bands, and **one**
       azimuth class, which is where the per-class reading reduces to step 1's
       flat gate exactly.
    """
    comm = MPI.COMM_WORLD

    scaled = _measure_ring(SCALED_LEG_COUNT)
    problems = [_report_safely("16 legs", scaled, comm)]

    # The controls after, so the 16-leg numbers are already in the log if gmsh
    # dies on a later build (`GEO-18` step 1's ordering, same reason).
    uncut = _measure(SCALED_LEG_COUNT)
    control = _measure_ring(CONTROL_LEG_COUNT)
    problems.append(_report_safely("4 legs (control)", control, comm))

    uncut_sheets = np.array([uncut["sheet_area"][i] for i in uncut["ports"]])
    # Step C's 1.331e-15 is a (max - min)/mean figure, so the comparison uses
    # that convention rather than this module's std/mean `_spread`.
    uncut_spread = float(
        (uncut_sheets.max() - uncut_sheets.min()) / uncut_sheets.mean()
    )
    if comm.rank == 0:
        print(
            f"\n[GEO-20 step 2 control i] kwarg off at {SCALED_LEG_COUNT} legs: "
            f"cells {uncut['n_cells']} vs `GEO-19` step C's "
            f"{SCALED_CONTROL_CELL_COUNT} (ratio "
            f"{uncut['n_cells'] / SCALED_CONTROL_CELL_COUNT:.6f})  C16 sheet "
            f"spread {uncut_spread:.3e} (record {SCALED_CONTROL_SHEET_SPREAD:.3e})"
            f"  rung={uncut['elapsed']:.2f} s"
            f"\n[GEO-20 step 2 control ii] 4 legs ring-gapped: cells "
            f"{control['n_cells']} vs step 1's {RING_GAP_CELL_RECORD} (ratio "
            f"{control['n_cells'] / RING_GAP_CELL_RECORD:.6f})  rung="
            f"{control['elapsed']:.2f} s"
            f"\n[GEO-20 step 2 cost rung] 4 -> 16 legs, ring-gapped: cells "
            f"{control['n_cells']} -> {scaled['n_cells']} "
            f"({scaled['n_cells'] / control['n_cells']:.4f}x)  mesh "
            f"{control['diag']['mesh_wall_time_s']:.2f} -> "
            f"{scaled['diag']['mesh_wall_time_s']:.2f} s "
            f"({scaled['diag']['mesh_wall_time_s'] / control['diag']['mesh_wall_time_s']:.4f}x)",
            flush=True,
        )

    _assert_ring_identity_family(scaled, "16 legs")
    _assert_ring_identity_family(control, "4 legs (control)")
    assert not [p for p in problems if p], [p for p in problems if p]

    # Control (i): the ring opt-in left the leg-gapped default geometry alone.
    assert (
        abs(uncut["n_cells"] / SCALED_CONTROL_CELL_COUNT - 1.0)
        < CONTROL_CELL_COUNT_BAND
    ), (
        f"the kwarg off at {SCALED_LEG_COUNT} legs meshed {uncut['n_cells']} cells "
        f"against `GEO-19` step C's record {SCALED_CONTROL_CELL_COUNT}; the "
        "ring-gap opt-in is not opt-in"
    )
    assert uncut_spread < SYMMETRY, (
        f"the kwarg-off control's C16 sheet spread is {uncut_spread:.3e} against "
        f"{SYMMETRY} (step C recorded {SCALED_CONTROL_SHEET_SPREAD:.3e})"
    )

    # Control (ii): four legs reproduces step 1's record on this same path.
    assert abs(control["n_cells"] / RING_GAP_CELL_RECORD - 1.0) < CELL_COUNT_BAND, (
        f"the 4-leg ring-gapped rung meshed {control['n_cells']} cells vs step 1's "
        f"record {RING_GAP_CELL_RECORD} (ratio "
        f"{control['n_cells'] / RING_GAP_CELL_RECORD:.6f}); the gap geometry or "
        "the grading moved"
    )
    ctl_terminal = control["diag"]["ring_port_layout"]["ring_terminal_area_m2"]
    for i in control["ring_ports"]:
        ratio = control["areas"][CONDUCTOR_IFACE + i] / ctl_terminal
        assert abs(ratio - RING_TERMINAL_RATIO) < RING_TERMINAL_RATIO_BAND, (
            f"the 4-leg control's ring port P{i} terminal ratio {ratio:.9f} "
            f"against step 1's record {RING_TERMINAL_RATIO}"
        )
