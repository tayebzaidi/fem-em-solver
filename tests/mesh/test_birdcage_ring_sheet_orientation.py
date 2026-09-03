"""`GEO-26` steps 1–2 — the **longitudinal** ring-gap port sheet, and its control.

`PORT-13` step 1 (2026-09-03) measured that `GEO-20`'s ring-gap sheets are the
gap's *transverse* mid-section at ``phi = phi_c``: the ``w x w`` rectangle
spanned by ``û(phi_c)`` and ``ẑ``, normal ``phi_hat``, spanning **zero** along
the drive direction. The lumped-sheet port model
(:mod:`fem_em_solver.ports.lumped`, `PORT-9` step 2/2b) needs a sheet that
spans the gap *along* the drive: ``R_s = Z_p·w/h``,
``I = (1/R_s)∫_S E·ĥ dS / h``, ``E_src = V_src/h``, all of which divide by an
``h`` this layout offers as ``<= 1.43e-17`` m. That is a well-posedness gap,
not a solver result, and it is why `PORT-13` step 1 is blocked.

This module gates the fix: a keyword-only ``ring_sheet_orientation`` on
``MeshGenerator.birdcage_port_domain``.

* ``"transverse"`` (default) is `GEO-20`'s emission, unchanged. The first test
  below is `PORT-13` step 1's measurement re-headed as this chunk's **negative
  control**: with the kwarg at its default the mesh reproduces
  `RING_GAP_CELL_RECORD` and its eight sheets still read ``phi_hat``-extent
  ``<= 1e-12`` m. If the opt-in leaked into the default, this goes red.
* ``"longitudinal"`` emits instead the planar rectangle in the plane
  ``u = ring_radius`` — normal ``û(phi_c)``, spanning the gap **chord**
  ``2R·tan(alpha)`` along ``phi_hat`` and ``w = ring_port_box_width_m`` along
  ``ẑ``. The chord, not the arc ``ring_gap_length``: the port box's two radial
  cap faces are planar, so the chord is what they actually deliver (+0.10% at
  this fixture's ``g = 0.008 m`` / ``R = 0.07 m``, both diagnostics emitted).
  Its four edges lie on those caps and on the box's two ``z`` faces, so it
  spans the box and splits it into an inner (``u < R``, tag ``100+i``) and an
  outer (``u > R``, ``200+i``) half with closed-form volumes
  ``w·tan(alpha)·(R·w ∓ w²/4)`` summing to the box's own
  ``ring_port_volume_m3 = 2R·w²·tan(alpha)``.

The horizontal trapezoid at ``z = z_ring`` (normal ``ẑ``) was considered and
rejected in the 2026-09-03 03:00 ruling: planar and box-spanning too, but its
``h(u) = 2u·tan(alpha)`` varies by ``±w/(2R)`` = ±7% across the sheet and the
port model needs one ``h``.

Both tests below are parametrised over the two rungs: `CONTROL_LEG_COUNT` = 4
(step 1, eight ring ports, C8) and `SCALED_LEG_COUNT` = 16 (**step 2**, the
`EX-35` / `GEO-20` step-2 rung — 32 ring ports, C16, and four azimuth classes
where four legs folds to one). Step 2 adds no identity: it re-reads the same
family one rung up, where the terminal classes are the finding
(`LONGITUDINAL_TERMINAL_INTRA_BAND` unmoved at 2.0e-5, a class above it is a
stop, not a widening — 2026-09-03 10:30 ruling).

**That stop fired.** The 16-leg longitudinal case is a *deliberate red on
`main`* since 2026-09-03: two of the four azimuth classes read an intra-class
terminal-area covariance of **9.990e-05**, five times the 2.0e-5 band, at both
`-n 2` and `-n 12`. Every other anchor is green on that rung — the 32 sheets,
both halves, the C32 spread and the mirror, the whole `GEO-20` family — and the
negative control reproduces `EX-35`'s 265 621 at ratio 1.000000. See
`docs/testing/known-issues.md`; the band is **not** widened and `PORT-13` stays
blocked.

Anchors (i)-(v) of the §9 item, at ``RING_GAP_LENGTH = 0.008`` on both rungs:

(i)   every sheet reconstructs through the plumbed ``_interface_facet_tags``
      path with meshed area / (``chord·w``) = 1.000000000000 at `EXACT`;
(ii)  each sheet's extent along its own ``phi_hat`` equals the chord at
      `EXACT` relative — the analogue of ``test_birdcage_port_sheets.py``'s
      ``h_bbox/dz - 1 < 1e-9`` for a leg gap — its extent along ``ẑ`` equals
      ``w``, and its out-of-plane spread along ``û`` is below `SYMMETRY`;
(iii) the two port halves hit ``V_in``/``V_out`` at `EXACT` on all eight;
(iv)  C4 spread of the eight sheet areas and the top/bottom mirror below
      `SYMMETRY`;
(v)   every identity `GEO-20` step 1 gates on this rung — the `GEO-9`
      partition, the air-box closure, the Pappus arcs, the terminal ratio in
      [0.95, 1.0] — still holds on the new mesh.

One measured difference, recorded rather than absorbed: the longitudinal
sheet's two ``phi`` edges are **diameters** of the two terminal disks, so the
inscribed triangulation of a terminal is constrained where the transverse mesh
leaves it free. Every terminal stays inside the [0.95, 1.0] band anchor (v)
names (0.97422 against the transverse 0.974455) and every *exact* form is
unmoved, but the C4 covariance of that triangulation drops from 4.198e-08 to
1.605e-05 — see `LONGITUDINAL_TERMINAL_INTRA_BAND` below.
`TERMINAL_INTRA_CLASS_BAND` is not widened; only this call site passes the
measured value.

Mesh-side only: no port model, no drive, no solve, no `GEO-20` record moves
(the default is untouched), `EX-35` unchanged. `PORT-13` stays blocked until
step 2 produces the 16-leg longitudinal record.

Run (real or complex build; mesh-side only)::

    scripts/testing/run_and_log.sh GEO-26 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && PYTHONPATH=/workspace/src timeout -k 30 300 \\
       mpiexec -n 2 python3 -m pytest \\
       tests/mesh/test_birdcage_ring_sheet_orientation.py -v -s'"
"""

from __future__ import annotations

import numpy as np
import dolfinx
import pytest
from mpi4py import MPI

from tests.mesh.test_birdcage_port_sheet_prerequisite import CELL_COUNT_BAND
from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER, SHEET_IFACE
from tests.mesh.test_birdcage_port_tags import RING_RADIUS
from tests.mesh.test_birdcage_port_terminals import CONDUCTOR_IFACE
from tests.mesh.test_birdcage_ring_gaps import (
    EXACT,
    RING_GAP_CELL_RECORD,
    RING_GAP_LENGTH,
    SYMMETRY,
    _spread,
)
from tests.mesh.test_birdcage_ring_gaps_scaleup import (
    CONTROL_LEG_COUNT,
    _assert_ring_identity_family,
    _measure_ring,
    _mirror_pairs,
    _report_safely,
    _ring_gap_frame,
    _terminal_classes,
)
from tests.mesh.test_birdcage_port_scaleup import (
    SCALED_LEG_COUNT,
    TERMINAL_INTRA_CLASS_BAND,
)

# The lumped-sheet route needs a strictly positive extent along the drive
# direction; this is the "is it zero" band, not a tolerance on a physical
# quantity.  The gap boxes are ~1e-2 m, so 1e-12 m is 1e-10 of the geometry.
DEGENERATE_EXTENT_M = 1.0e-12

# The in-plane extents are two exact linear-mesh readings of the generator's own
# `ring_port_box_width_m`; a planar rectangle meshed conformingly has no
# discretisation error to spend on its bounding box.
BOX_WIDTH_BAND = 1.0e-9

# `GEO-26` step 1, 0.11 image, `-n 2`: the 4-leg ring-gapped rung meshed with
# **longitudinal** sheets. Measured, not predicted — the sheet is a different
# dim-2 fragment tool from the transverse one, so it constrains the tets
# differently and the count is not `RING_GAP_CELL_RECORD` (110 786).
# Read 111 898 at `-n 2` in 20260903T093604Z_GEO-26.log:13904.
RING_LONGITUDINAL_CELL_RECORD = 111898

# `GEO-26` step 2, 0.11 image: the **16-leg** ring-gapped rung meshed with
# longitudinal sheets — the record `PORT-13` step 1's cell-count control becomes
# (not the transverse 265 621). Measured, not predicted, and identical at both
# widths: 20260903T170351Z_GEO-26.log:53400 (`-n 2`) and
# 20260903T170701Z_GEO-26.log:53490 (`-n 12`).
#
# **This assert is currently unreachable**: the terminal azimuth-class
# covariance below fires first on this rung (see the known-issues entry of
# 2026-09-03). The constant is recorded because it is measured twice, not
# because anything green depends on it.
RING_LONGITUDINAL_SCALED_CELL_RECORD = 270728

# `EX-35`'s transverse 16-leg record (`SCALED_CELL_RECORD`,
# `examples/meshing/09_birdcage_sixteen_ring_gaps.py:147`), restated here rather
# than imported because that record lives in an example script this test must
# not execute. It is the *negative control* for step 2: the default orientation
# at 16 legs must still be `GEO-20` step 2's mesh, unmoved.
RING_GAP_SCALED_CELL_RECORD = 265621

# Rung -> record, so the two parametrised cases read one table instead of
# branching. `None` means "not yet measured": the discovery window fails by
# construction on the assert at the bottom of the longitudinal test.
TRANSVERSE_CELL_RECORD = {
    CONTROL_LEG_COUNT: RING_GAP_CELL_RECORD,
    SCALED_LEG_COUNT: RING_GAP_SCALED_CELL_RECORD,
}
LONGITUDINAL_CELL_RECORD = {
    CONTROL_LEG_COUNT: RING_LONGITUDINAL_CELL_RECORD,
    SCALED_LEG_COUNT: RING_LONGITUDINAL_SCALED_CELL_RECORD,
}

# `GEO-26` step 1, measured 20260903T093604Z_GEO-26.log:13913 — a property of
# the new mode, recorded here, **not** a widening of `GEO-20`'s band.
#
# The longitudinal sheet spans the full gap at ``u = R``, so each of its two
# ``phi`` edges lies in a terminal plane ``phi = phi_c ± alpha`` and runs from
# ``z_ring − w/2`` to ``z_ring + w/2`` through the terminal disk's centre: the
# edge is a **diameter** of each disk (``w = 1e-2 m`` against the disk's
# ``2·r_ring = 8e-3 m``). The transverse sheet sits at ``phi_c``, mid-gap,
# and touches neither terminal. A disk whose inscribed triangulation is
# constrained to contain a diameter is not the one gmsh builds unconstrained,
# and in global coordinates that constrained triangulation is no longer
# exactly C4-covariant: six of the eight terminals read 9.793917647e-05 m² and
# the two at 225 deg read 9.794074883e-05 m², an intra-class spread of
# **1.605e-05** where the transverse mesh reads 4.198e-08
# (`20260828T093839Z_GEO-20-step2-record.log:50833`).
#
# What is unmoved: all eight sit at 0.974219/0.974235 of the closed-form two
# disks, inside the [0.95, 1.0] inscribed band anchor (v) names (transverse:
# 0.974455); the port-boundary closure is 1.000000000000; and every *exact*
# form — sheet area, port volume, both halves, the C8 spread 4.273e-16 — is
# untouched, because those are polyhedral and carry no discretisation error.
# `TERMINAL_INTRA_CLASS_BAND` itself is untouched and still gates every
# transverse fixture; only this call site passes the measured value.
LONGITUDINAL_TERMINAL_INTRA_BAND = 2.0e-5


def _sheet_extent_along(msh, facet_tags, tag, axis, comm) -> float:
    """Global ``max − min`` of one sheet's node coordinates along ``axis`` [m].

    ``entities_to_geometry`` and the local max/min are rank-local; both
    reductions happen here so no caller can read an unreduced extent (a rank
    that owns none of the sheet contributes the neutral sentinels).
    """
    fdim = msh.topology.dim - 1
    facets = np.asarray(facet_tags.find(tag), dtype=np.int32)
    axis = np.asarray(axis, dtype=np.float64)
    if facets.size:
        nodes = dolfinx.cpp.mesh.entities_to_geometry(
            msh._cpp_object, fdim, facets, False
        )
        proj = msh.geometry.x[nodes.reshape(-1)] @ axis
        local_hi, local_lo = float(proj.max()), float(proj.min())
    else:
        local_hi, local_lo = -np.inf, np.inf
    hi = comm.allreduce(local_hi, op=MPI.MAX)
    lo = comm.allreduce(local_lo, op=MPI.MIN)
    return float(hi - lo)


def _record_ratio(n_cells, record=RING_LONGITUDINAL_CELL_RECORD) -> str:
    """``n_cells / record`` as text, safe when the record is unmeasured.

    The record print runs inside ``if comm.rank == 0``; a `TypeError` there
    would leave the other ranks in the next collective and turn a red test into
    a wall-clock hang (`GEO-19` step C, 2026-08-25). `record` defaults to the
    4-leg step-1 constant so the signature step 1 shipped still works.
    """
    if record is None:
        return "unmeasured"
    return f"{n_cells / record:.6f}"


def _sheet_axes(ordinal, leg_count):
    """``(phi_hat, u_hat, z_hat)`` for a ring port, from its ordinal alone."""
    phi_hat, centre = _ring_gap_frame(ordinal, leg_count)
    phi_c = float(np.arctan2(centre[1], centre[0]))
    return (
        phi_hat,
        np.array([np.cos(phi_c), np.sin(phi_c), 0.0]),
        np.array([0.0, 0.0, 1.0]),
    )


@pytest.mark.parametrize("leg_count", [CONTROL_LEG_COUNT, SCALED_LEG_COUNT])
def test_the_default_ring_sheets_stay_transverse_with_zero_gap_height(leg_count):
    """`GEO-26`'s **negative control** on both rungs (was `PORT-13` step 1's).

    With `ring_sheet_orientation` at its default the mesh must be `GEO-20`'s,
    unchanged: the recorded cell count (110 786 at four legs, `EX-35`'s 265 621
    at sixteen), and 2·N transverse sheets whose extent along their own
    ``phi_hat`` is zero to machine precision. Three readings per ring port —
    the extent along ``phi_hat`` (the drive direction a ring port would use),
    and the two in-plane extents along ``û`` at ``phi_c`` and along ``ẑ``.
    """
    comm = MPI.COMM_WORLD
    record = TRANSVERSE_CELL_RECORD[leg_count]
    m = _measure_ring(leg_count)
    msh = m["mesh"]
    layout = m["diag"]["ring_port_layout"]
    box_width = float(layout["ring_port_box_width_m"])

    rows = {}
    for i in m["ring_ports"]:
        phi_hat, u_hat, z_hat = _sheet_axes(i, leg_count)
        tag = SHEET_IFACE + i
        rows[i] = {
            "phi": _sheet_extent_along(msh, m["sheet_tags"], tag, phi_hat, comm),
            "u": _sheet_extent_along(msh, m["sheet_tags"], tag, u_hat, comm),
            "z": _sheet_extent_along(msh, m["sheet_tags"], tag, z_hat, comm),
            "area": float(m["sheet_area"][i]),
        }

    if comm.rank == 0:
        print(
            f"\n[GEO-26 control] default (transverse) ring sheets at "
            f"{leg_count} legs: {m['n_cells']} cells (record "
            f"{record}, ratio "
            f"{m['n_cells'] / record:.6f}), "
            f"{len(m['ring_ports'])} ring ports, orientation "
            f"{m['diag']['ring_sheet_orientation']!r}, mesh "
            f"{m['diag']['mesh_wall_time_s']:.2f} s, rung {m['elapsed']:.2f} s\n"
            f"    generator's ring_port_box_width_m w = {box_width:.9e} m; "
            f"analytic transverse sheet area w^2 = {box_width ** 2:.9e} m^2",
            flush=True,
        )
        for i, r in rows.items():
            print(
                f"    P{i}: extent along phi_hat (drive) = {r['phi']:.6e} m  "
                f"along u_hat = {r['u']:.9e} m ({r['u'] / box_width:.12f} w)  "
                f"along z_hat = {r['z']:.9e} m ({r['z'] / box_width:.12f} w)  "
                f"area = {r['area']:.9e} m^2 "
                f"({r['area'] / box_width ** 2:.12f} w^2)",
                flush=True,
            )

    assert abs(m["n_cells"] / record - 1.0) < CELL_COUNT_BAND, (
        f"the {leg_count}-leg ring-gapped rung meshed {m['n_cells']} "
        f"cells against the transverse record {record}; the "
        "`GEO-26` opt-in is not opt-in"
    )
    assert m["diag"]["ring_sheet_orientation"] == "transverse"

    for i, r in rows.items():
        assert r["phi"] < DEGENERATE_EXTENT_M, (
            f"ring port P{i}'s default sheet spans {r['phi']:.6e} m along its "
            f"own drive direction phi_hat, above the {DEGENERATE_EXTENT_M:.0e} m "
            "degeneracy band — the default emission is no longer `GEO-20`'s "
            "transverse mid-section"
        )
        for axis_name in ("u", "z"):
            ratio = r[axis_name] / box_width
            assert abs(ratio - 1.0) < BOX_WIDTH_BAND, (
                f"ring port P{i}'s default sheet extends {r[axis_name]:.9e} m "
                f"along {axis_name}_hat against the generator's closed-form "
                f"ring_port_box_width_m {box_width:.9e} m (ratio {ratio:.12f}); "
                "the reconstructed facet set is not the w x w rectangle"
            )
        assert abs(r["area"] / box_width**2 - 1.0) < BOX_WIDTH_BAND, (
            f"ring port P{i}'s default sheet area {r['area']:.9e} m^2 against "
            f"the closed-form w^2 = {box_width ** 2:.9e} m^2"
        )


@pytest.mark.parametrize("leg_count", [CONTROL_LEG_COUNT, SCALED_LEG_COUNT])
def test_the_longitudinal_ring_sheets_span_the_gap_chord_and_split_the_box(leg_count):
    """`GEO-26` anchors (i)-(v) on both rungs — step 1 at 4 legs, step 2 at 16.

    The sheet is now a section *through* the gap: it spans the chord along the
    drive direction (fourteen decades above the transverse 1e-17), reconstructs
    at ``chord·w``, is flat in its own plane ``u = R``, and cuts its port box
    into the two closed-form halves. None of the closed forms depends on the
    leg count — ``alpha = g/2R``, ``w``, ``V_in``/``V_out`` are all fixed by the
    ring radius and the gap length — so 16 legs is the same arithmetic on 32
    sheets, with C16 in place of C8 and four azimuth classes in place of one.
    """
    comm = MPI.COMM_WORLD
    record = LONGITUDINAL_CELL_RECORD[leg_count]
    m = _measure_ring(leg_count, orientation="longitudinal")
    msh = m["mesh"]
    layout = m["diag"]["ring_port_layout"]
    box_width = float(layout["ring_port_box_width_m"])
    chord = float(layout["ring_port_gap_chord_m"])
    sheet_analytic = float(layout["ring_port_sheet_longitudinal_area_m2"])
    port_volume = float(layout["ring_port_volume_m3"])
    tan_a = float(np.tan(float(layout["ring_gap_half_angle_rad"])))

    # (iii) the two halves of the wedge-slab-slab solid, cut at u = R:
    #   V(u0..u1) = w · tan(alpha) · (u1² − u0²)
    # so the inner half [R − w/2, R] and the outer half [R, R + w/2] are
    #   V_in  = w·tan(alpha)·(R·w − w²/4),  V_out = w·tan(alpha)·(R·w + w²/4),
    # summing to 2·R·w²·tan(alpha) = `ring_port_volume_m3`.
    v_in = box_width * tan_a * (RING_RADIUS * box_width - 0.25 * box_width**2)
    v_out = box_width * tan_a * (RING_RADIUS * box_width + 0.25 * box_width**2)

    rows = {}
    for i in m["ring_ports"]:
        phi_hat, u_hat, z_hat = _sheet_axes(i, leg_count)
        tag = SHEET_IFACE + i
        rows[i] = {
            "phi": _sheet_extent_along(msh, m["sheet_tags"], tag, phi_hat, comm),
            "u": _sheet_extent_along(msh, m["sheet_tags"], tag, u_hat, comm),
            "z": _sheet_extent_along(msh, m["sheet_tags"], tag, z_hat, comm),
            "area": float(m["sheet_area"][i]),
            "flat": float(m["sheet_flatness"][i]),
            "v_in": float(m["volumes"][PORT_LOWER + i]),
            "v_out": float(m["volumes"][PORT_UPPER + i]),
        }

    label = f"{leg_count} legs longitudinal"
    problem = _report_safely(label, m, comm)

    if comm.rank == 0:
        print(
            f"\n[GEO-26] longitudinal ring sheets at {leg_count} "
            f"legs: {m['n_cells']} cells (record "
            f"{record}, ratio "
            f"{_record_ratio(m['n_cells'], record)}; the "
            f"transverse rung is {TRANSVERSE_CELL_RECORD[leg_count]}), orientation "
            f"{m['diag']['ring_sheet_orientation']!r}, mesh "
            f"{m['diag']['mesh_wall_time_s']:.2f} s, rung {m['elapsed']:.2f} s\n"
            f"    arc ring_gap_length_m = {RING_GAP_LENGTH:.9e} m, chord "
            f"ring_port_gap_chord_m = {chord:.9e} m "
            f"(chord/arc = {chord / RING_GAP_LENGTH:.9f}), w = "
            f"{box_width:.9e} m, sheet chord*w = {sheet_analytic:.9e} m^2\n"
            f"    closed-form halves: V_in = {v_in:.9e} m^3, V_out = "
            f"{v_out:.9e} m^3, sum/ring_port_volume_m3 = "
            f"{(v_in + v_out) / port_volume:.12f}",
            flush=True,
        )
        for i, r in rows.items():
            print(
                f"    P{i}: along phi_hat (drive) = {r['phi']:.9e} m "
                f"({r['phi'] / chord:.12f} chord)  along z_hat = "
                f"{r['z']:.9e} m ({r['z'] / box_width:.12f} w)  along u_hat "
                f"(out of plane) = {r['u']:.3e} m  flatness {r['flat']:.3e} m  "
                f"area = {r['area']:.9e} m^2 "
                f"({r['area'] / sheet_analytic:.12f} chord*w)  V_in/analytic = "
                f"{r['v_in'] / v_in:.12f}  V_out/analytic = "
                f"{r['v_out'] / v_out:.12f}",
                flush=True,
            )
        sheets = np.array([rows[i]["area"] for i in m["ring_ports"]])
        mirror = max(
            abs(m["sheet_area"][hi] / m["sheet_area"][lo] - 1.0)
            for lo, hi in _mirror_pairs(leg_count)
        )
        print(
            f"[GEO-26] C{2 * leg_count} longitudinal sheet spread "
            f"= {_spread(sheets):.3e}, top/bottom mirror spread = "
            f"{mirror:.3e} (band {SYMMETRY})",
            flush=True,
        )
        # The step-2 finding: every azimuth class's terminal-area covariance
        # against the mode's measured band. Four classes at 16 legs, one at 4.
        # `TERMINAL_INTRA_CLASS_BAND` (the transverse 1e-6) is printed beside
        # each so the log carries the comparison the ruling turned on; the
        # assert lives in `_assert_ring_identity_family` below.
        classes = _terminal_classes(m)
        for key, members in classes.items():
            vals = np.array(
                [float(m["areas"][CONDUCTOR_IFACE + i]) for i in members]
            )
            spread = (
                float((vals.max() - vals.min()) / vals.mean())
                if len(members) > 1
                else 0.0
            )
            azimuths = ", ".join("%.3f" % m["azimuth_deg"][i] for i in members)
            print(
                f"[GEO-26] terminal azimuth class '{key}': {len(members)} ports "
                f"[{azimuths}] deg"
                f"  mean {vals.mean():.9e} m^2  intra-class spread {spread:.6e} "
                f"against this mode's band {LONGITUDINAL_TERMINAL_INTRA_BAND} "
                f"(transverse band {TERMINAL_INTRA_CLASS_BAND}; the sheet's phi "
                f"edges are diameters of the two terminal disks, see the module "
                f"constant)",
                flush=True,
            )

    # Closed-form consistency of the two halves against the box's own volume —
    # a same-rank arithmetic identity, so it gates the formulae before the mesh
    # is asked to reproduce them.
    assert abs((v_in + v_out) / port_volume - 1.0) < 1.0e-15, (
        f"the closed-form halves sum to {v_in + v_out:.12e} m^3 against the "
        f"generator's ring_port_volume_m3 {port_volume:.12e} m^3"
    )
    assert abs(sheet_analytic / (chord * box_width) - 1.0) < 1.0e-15

    for i, r in rows.items():
        # (ii) the drive-direction extent: this is the `h` the port model
        # divides by, and the whole point of the mode.
        ratio = r["phi"] / chord
        assert abs(ratio - 1.0) < EXACT, (
            f"longitudinal ring port P{i}'s sheet spans {r['phi']:.9e} m along "
            f"its own drive direction phi_hat against the closed-form chord "
            f"{chord:.9e} m (ratio {ratio:.12f}); the sheet does not span the "
            "gap, so the lumped-sheet `h` it offers is not the chord"
        )
        ratio_z = r["z"] / box_width
        assert abs(ratio_z - 1.0) < EXACT, (
            f"longitudinal ring port P{i}'s sheet extends {r['z']:.9e} m along "
            f"z_hat against ring_port_box_width_m {box_width:.9e} m (ratio "
            f"{ratio_z:.12f}); it does not span its box in z"
        )
        assert r["u"] < DEGENERATE_EXTENT_M, (
            f"longitudinal ring port P{i}'s sheet spreads {r['u']:.6e} m along "
            f"its own normal u_hat, above {DEGENERATE_EXTENT_M:.0e} m; it is "
            "not the planar rectangle in the plane u = R"
        )
        assert r["flat"] < SYMMETRY, (
            f"longitudinal ring port P{i}'s sheet is {r['flat']:.3e} m out of "
            "the plane u = R"
        )
        # (iii) the halves. `100+i` is the inner (u < R) piece and `200+i` the
        # outer, by the sign of (centroid − gap centre)·û in `io/mesh.py`; a
        # sheet that failed to span its box would leave the port one piece and
        # `birdcage_port_domain` would already have raised on the missing group.
        for tag, meshed, analytic in (
            ("inner", r["v_in"], v_in),
            ("outer", r["v_out"], v_out),
        ):
            assert abs(meshed / analytic - 1.0) < EXACT, (
                f"longitudinal ring port P{i}'s {tag} half has meshed volume "
                f"{meshed:.9e} m^3 against the closed form {analytic:.9e} m^3 "
                f"(ratio {meshed / analytic:.12f}); the sheet does not cut the "
                "box at u = R"
            )

    # (i), (iv), (v): the whole `GEO-20` step-1 identity family, re-read on the
    # new mesh with the longitudinal closed form as the sheet's analytic — the
    # partition, the air-box closure, the Pappus arcs, the terminal ratio band,
    # the per-port sheet area and flatness, the C4 spread and the top/bottom
    # mirror.
    _assert_ring_identity_family(
        m,
        label,
        terminal_intra_band=LONGITUDINAL_TERMINAL_INTRA_BAND,
    )
    assert not problem, problem

    # The version-tagged record, last so every anchor above is already in the
    # log when it fires.
    assert record is not None, (
        f"the longitudinal cell record at {leg_count} legs is unmeasured; this "
        f"run reads {m['n_cells']} cells at {comm.size} ranks"
    )
    assert abs(m["n_cells"] / record - 1.0) < CELL_COUNT_BAND, (
        f"the {leg_count}-leg longitudinal rung meshed {m['n_cells']} "
        f"cells against the `GEO-26` record "
        f"{record} (ratio "
        f"{_record_ratio(m['n_cells'], record)}); the sheet "
        "geometry or the grading moved"
    )
