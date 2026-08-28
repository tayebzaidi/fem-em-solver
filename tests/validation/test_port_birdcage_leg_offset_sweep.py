"""`PORT-9` step 3 leg (d1'), solve side — does gate (iii') notice a broken C4?

Leg (d) assembled the gapped birdcage's 4x4 on the **undisplaced** mesh and
found it reciprocal, passive and circulant; on `GEO-19` step B's 116 085-cell
mesh, through leg (d3)'s **power-wave** ``S`` assembly, the three class spreads
read 0.0553 / 0.0353 / 0.0214% and ``σ_max(S)`` = 0.999992805.  A symmetry gate
that has only ever been shown a symmetric layout is a consistency check, not a
validated gate — so this module breaks the symmetry on purpose, on the mesh-side
knob leg (d1')'s mesh half built and gated (``leg_azimuth_offsets_rad``,
`tests/mesh/test_birdcage_leg_offset.py`, 2026-08-25), and asks the gate to
notice.

**Two rungs, eight driven solves**, both through step 2c's lumped-sheet route on
leg (d)'s fixture exactly (four ``f = 0.5`` sheets, ``w = A/h``, 10 MHz,
``Z_p = 50 Ohm`` on every port):

* **zero** — ``leg_azimuth_offsets_rad`` all zero.  The offsets are *added* to
  the nominal azimuths and adding an exact zero is exact, so this rung is not a
  zero-angle rotation of the fixture but the same construction leg (d) meshed:
  it must reproduce leg (d0)'s recorded terminated column and step B's
  ``σ_max``.  It is the knob's identity control on the *solve*, and it is what
  makes the displaced rung comparable at all;
* **displaced** — leg 1 alone rotated by ``+pi/(2*leg_count)`` = 22.5 deg, so its
  two azimuthal neighbours sit 67.5 and 112.5 deg away instead of 90 and 90 and
  the leg opposite it 157.5 deg away instead of 180.  The coil has lost C4.

**The three anchors**, pre-stated by the 2026-08-25 03:00 review (§9 item 1) and
not moved here:

* **(a)** the undisplaced control reproduces step B's records — 116 085 cells at
  ratio 1.000000, leg (d0)'s terminated column to its print precision,
  ``σ_max(S)`` = 0.999992805, and all three class spreads inside (iii');
* **(b)** displaced, ``‖S − Sᵀ‖/‖S‖`` stays ``≤ 1e-3``.  This is the first test
  of leg (d3)'s power-wave fix on an asymmetric **3D** fixture (the asymmetric
  two-torus read 1.324e-16).  The **negative control** is on record: the
  pre-fix, terminated-`Z`-normalisation route read **5.57e-03** on this exact
  displaced fixture (`20260823T140422Z_PORT-9-step3d1.log`), so a power-wave
  reading anywhere near machine precision is a ≥ 5x10^5 separation against a
  ≥ 100x bar.  Reciprocity is a property of the materials, not of the layout:
  holding it here separates "the gate measured geometry" from "the displaced
  solve fell apart".  Per (d3c) it records as an **order of magnitude only** —
  power-wave readings sit at ~1e-16…1e-11 and are never pinned at a print band;
* **(c)** displaced, the ``{Z_ii}`` (self) and ``{Z_i,i±1}`` (adjacent) class
  spreads must **exceed** ``ADJACENT_SPREAD_BAND`` — now (iii')'s 0.5%.  The
  ``{Z_i,i+2}`` (opposite) class is physically the flattest of the three and the
  review pre-ruled that it is *reported*, not gated, here: if it stays under
  0.5% that is a reading for the review, never a licence to widen (iii').

**The negative control of the control** travels with the displaced rung: every
sheet it solves on is still a full rectangle of closed-form area ``dx·g`` to
1e-9 and still planar in its own port frame.  The mesh half gates this on its
own three rungs; it is re-asserted here on the *solved* mesh so that a class
spread measured below cannot be blamed on a broken port.

**Frame awareness.**  At 22.5 deg a sheet is neither x- nor y-normal, so leg
(c)/(d)'s global-axis extent and midpoint filter cannot narrow it: both are
generalised here to the port's own radial/azimuthal/axial frame, read off the
sheet's bounding-box centre.  For an undisplaced port the two coincide term by
term, which is why the zero rung can be held to leg (d0)'s digits.

**Scope.**  10 MHz, the port model's frequency.  With leg (d) green, a green
displaced rung here closes `PORT-9` step 3 and the chunk — as measured on this
gated fixture, with no Larmor claim and no S-parameter claim beyond it.  A
displaced self/adjacent spread *under* 0.5% is the pre-stated negative result:
gate (iii') is blind at this grain, the spreads are recorded, `PORT-9` stays 🟡
and the review re-specifies (iii').

Cost: standard tier, ``-n 2``, two meshes (~21 s each) and eight solves (leg
(d) priced four at 31.6 s together).

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-9-step3d1 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 590 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_birdcage_leg_offset_sweep.py -v -s'"
"""

from __future__ import annotations

import time

import dolfinx
import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.lumped import LumpedSheetPortSpec
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_leg_offset import (
    LEG_OFFSET_RAD,
    SHEET_AREA_BAND,
    _build,
    _projected_extents,
    _sheet_areas,
    _sheet_azimuth_deg,
)
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.mesh.test_birdcage_port_tags import LEG_COUNT
from tests.mesh.test_two_torus_port_facets import _facet_group_area
from tests.mesh.test_two_torus_port_sheet import _sheet_facet_count
from tests.validation.test_lossy_sphere_fullwave import SALINE_EPSILON_R, SALINE_SIGMA
from tests.validation.test_port_birdcage_four_port import (
    LEG_D0_REPRODUCTION_BAND,
    LEG_D0_Z_COLUMN,
    PASSIVITY_SIGMA_TOLERANCE,
    TERMINATED_PORT_IMPEDANCE_OHM,
    _circulant_classes,
    _class_spread,
)
from tests.validation.test_port_birdcage_lumped_column import (
    ADJACENT_SPREAD_BAND,
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
    STEP2_CELL_COUNT,
    STEP2_CELL_COUNT_BAND,
)
from tests.validation.test_port_gap_voltage_impedance import (
    FREQUENCY_HZ,
    SIGMA_WIRE_S_PER_M,
)
from tests.validation.test_port_lumped_narrowed_sheet import GATED_WIDTH_FRACTION
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND
from tests.validation.test_port_package_sparameters import REFERENCE_IMPEDANCE_OHM

# **Anchor (a)'s passivity record**, mesh-tagged to `GEO-19` step B's 116 085-cell
# mesh and route-tagged to leg (d3)'s power-wave `S` assembly:
# `test_port_birdcage_four_port.py`'s module docstring records
# `σ_max(S)` = 0.999992805 there.  Restated rather than imported because leg (d)
# keeps it in prose, not in a constant; the band on it is the log's print
# precision (9 decimals), the same reproduction band leg (d0)'s column carries
# and for the same reason — this rung is supposed to run the identical code path
# on the identical mesh, so anything above print noise means the knob moved the
# solve.  It is **not** a physics tolerance and nothing here widens gate (ii),
# which is asserted separately below at its own `1 + 1e-9`.
STEP_B_SIGMA_MAX = 0.999992805

# **Leg (d1')'s pre-fix negative control**, for the record and printed, not
# gated: the terminated-`Z` per-column normalisation leg (d2) traced the loss to
# read `‖S − Sᵀ‖/‖S‖` = 5.57e-03 on *this* displaced fixture
# (`20260823T140422Z_PORT-9-step3d1.log`), 223x outside the 1e-3 band.  The
# power-wave route's separation against it is the leg's route finding.
PRE_FIX_Z_ROUTE_RECIPROCITY = 5.57e-03


def _port_frame(azimuth_deg):
    """The (radial, azimuthal, axial) unit triad of a port at this azimuth.

    The sheet spans the box radially and along the leg (``z``); its normal is the
    azimuthal direction.  At azimuth 0 / 90 / 180 / 270 deg this triad *is* the
    global one up to signs, which is what makes the zero rung comparable to leg
    (d0)'s global-axis reading term by term.
    """
    beta = np.radians(azimuth_deg)
    radial = np.array([np.cos(beta), np.sin(beta), 0.0])
    azimuthal = np.array([-np.sin(beta), np.cos(beta), 0.0])
    axial = np.array([0.0, 0.0, 1.0])
    return radial, azimuthal, axial


def _narrowed_radial(msh, facet_tags, tag, fraction, centre, radial, half_width):
    """Step 2b's midpoint filter, applied along a port's own radial direction.

    Leg (c)/(d)'s `_narrowed_transverse` filters on a *global* axis chosen off
    the bounding box, which cannot name the transverse direction of a sheet at
    22.5 deg.  Everything else is step 2b's rule unchanged: facet **midpoints**,
    not nodes; every other tag passed through untouched; and ``w`` re-measured
    from the filtered set as ``A/h`` rather than computed as ``f x w_full``.  For
    a port on a coordinate axis ``radial`` is that axis and the filter reduces to
    the global-axis one.
    """
    fdim = msh.topology.dim - 1
    idx = np.asarray(facet_tags.indices, dtype=np.int32)
    val = np.asarray(facet_tags.values, dtype=np.int32)
    on_sheet = val == int(tag)
    sheet_facets = idx[on_sheet]
    keep = np.ones(sheet_facets.size, dtype=bool)
    if sheet_facets.size:
        mid = dolfinx.mesh.compute_midpoints(msh, fdim, sheet_facets)
        keep = np.abs(mid @ np.asarray(radial, dtype=float) - centre) <= (
            fraction * half_width
        )
    new_idx = np.concatenate([idx[~on_sheet], sheet_facets[keep]]).astype(np.int32)
    new_val = np.concatenate(
        [
            val[~on_sheet],
            np.full(int(np.count_nonzero(keep)), int(tag), dtype=np.int32),
        ]
    ).astype(np.int32)
    order = np.argsort(new_idx, kind="stable")
    return dolfinx.mesh.meshtags(msh, fdim, new_idx[order], new_val[order])


def _four_port_rung(name, offsets, frequency_hz=FREQUENCY_HZ, reuse=None):
    """Build one rung, narrow its four sheets in their own frames, drive all four.

    Returns the assembled ``Z``/``S``, the circulant class spreads, the
    reciprocity readings and the per-port sheet geometry, all reduced over ranks.

    ``frequency_hz`` defaults to `PORT-9`'s 10 MHz, which is the only frequency
    this module runs; it is a parameter so that `PORT-11` step 2 can drive the
    identical construction at 64 MHz without a second copy of it (the frequency
    is then demonstrably the only knob turned — see
    `tests/validation/test_port_birdcage_larmor_gate.py`).  Nothing else about
    this function moved when the parameter was added, and every rung below still
    calls it at the default.

    ``reuse`` is the second additive parameter, for `EX-34`: hand it a rung this
    function already returned and the mesh, the narrowed sheet tags and the sheet
    geometry are taken from it instead of being rebuilt, so a frequency ladder
    runs on **one** mesh.  ``offsets`` is then unread — the reused rung's geometry
    *is* the geometry, which is exactly the property the ladder needs.  Every
    caller in this repo's gates passes ``reuse=None`` (the default) and rebuilds
    as before; nothing below reads the extra return keys.
    """
    comm = MPI.COMM_WORLD
    ports_idx = list(range(1, LEG_COUNT + 1))

    if reuse is not None:
        msh = reuse["mesh"]
        cell_tags = reuse["cell_tags"]
        tags_f = reuse["facet_tags"]
        sheets = reuse["sheets"]
        ncells = int(reuse["cells"])
        sheet_analytic = float(reuse["sheet_analytic"])
        diag = {"mesh_wall_time_s": 0.0}
        t_mesh = 0.0
    else:
        msh, cell_tags, _facet_tags, diag, t_mesh = _build(offsets)
        tdim = msh.topology.dim
        ncells = int(msh.topology.index_map(tdim).size_global)
        # Hoisted on every rank before any facet-restricted form (known-issues 9).
        msh.topology.create_connectivity(tdim - 1, tdim)
        msh.topology.create_entity_permutations()

        tags_f, full_areas = _sheet_areas(msh, cell_tags, ports_idx, comm)
        dx, _dy, dz = diag["port_box_size_m"]
        sheet_analytic = float(dx) * float(dz)

        # Measure each full sheet in its own frame, then narrow radially to step
        # 2b's gated fraction and re-measure `w = A/h` on the filtered set.
        geometry = {}
        for i in ports_idx:
            tag = SHEET_IFACE + i
            azimuth = _sheet_azimuth_deg(msh, tags_f, tag, comm)
            radial, azimuthal, axial = _port_frame(azimuth)
            spans, centres = _projected_extents(
                msh, tags_f, tag, comm, [radial, azimuthal, axial]
            )
            geometry[i] = {
                "tag": tag,
                "azimuth_deg": float(azimuth),
                "radial": radial,
                "w_full": float(spans[0]),
                "out_of_plane_full": float(spans[1]),
                "h_full": float(spans[2]),
                "centre_radial": float(centres[0]),
                "area_full": float(full_areas[i]),
                "area_ratio_full": float(full_areas[i] / sheet_analytic),
            }

        for i in ports_idx:
            g = geometry[i]
            tags_f = _narrowed_radial(
                msh,
                tags_f,
                g["tag"],
                GATED_WIDTH_FRACTION,
                g["centre_radial"],
                g["radial"],
                0.5 * g["w_full"],
            )

        sheets = []
        for i in ports_idx:
            g = geometry[i]
            n_facets = _sheet_facet_count(msh, tags_f, g["tag"], comm)
            assert n_facets > 0, f"sheet {g['tag']}: no owned facets anywhere"
            area = _facet_group_area(msh, tags_f, g["tag"], comm)
            radial, azimuthal, axial = _port_frame(g["azimuth_deg"])
            spans, _centres = _projected_extents(
                msh, tags_f, g["tag"], comm, [radial, azimuthal, axial]
            )
            sheets.append(
                {
                    **g,
                    "facets": int(n_facets),
                    "area": float(area),
                    "h": float(spans[2]),
                    "w": float(area / spans[2]),
                    "w_bbox": float(spans[0]),
                    "out_of_plane": float(spans[1]),
                }
            )

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=frequency_hz,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            CONDUCTOR_CELL_TAG: HomogeneousMaterial(
                sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0
            ),
            PHANTOM_CELL_TAG: HomogeneousMaterial(
                sigma=SALINE_SIGMA, epsilon_r=SALINE_EPSILON_R, mu_r=1.0
            ),
        },
        boundary_condition="pec_zero_tangential_a",
    )

    port_defs = []
    specs = []
    for s in sheets:
        pid = f"P{s['tag'] - SHEET_IFACE}"
        port_defs.append(
            PortDefinition(
                port_id=pid,
                positive_tag=int(s["tag"]),
                negative_tag=CONDUCTOR_CELL_TAG,
                orientation="leg_gap_axial_plus_z",
                z0_ohm=REFERENCE_IMPEDANCE_OHM,
            )
        )
        specs.append(
            LumpedSheetPortSpec(
                port_id=pid,
                facet_tag=int(s["tag"]),
                port_impedance_ohm=TERMINATED_PORT_IMPEDANCE_OHM,
                gap_height_m=s["h"],
                sheet_width_m=s["w"],
                drive_direction=(0.0, 0.0, 1.0),
                drive_voltage_v=1.0 + 0.0j,
                interior=True,
            )
        )

    comm.Barrier()
    t0 = time.perf_counter()
    result = run_n_port_sparameter_sweep(
        problem,
        port_defs,
        lumped_sheet_ports=specs,
        lumped_sheet_facet_tags=tags_f,
    )
    comm.Barrier()
    t_sweep = time.perf_counter() - t0

    z_matrix = np.asarray(result.z_matrix, dtype=np.complex128)
    s_matrix = np.asarray(result.s_matrix, dtype=np.complex128)
    classes = _circulant_classes(z_matrix)
    spreads = {n: _class_spread(v) for n, v in classes.items()}
    sigma = np.linalg.svd(s_matrix, compute_uv=False)
    column_power = np.sum(np.abs(s_matrix) ** 2, axis=0)
    reciprocity = float(
        np.linalg.norm(s_matrix - s_matrix.T) / np.linalg.norm(s_matrix)
    )
    z_reciprocity = float(
        np.linalg.norm(z_matrix - z_matrix.T) / np.linalg.norm(z_matrix)
    )
    pooled = _class_spread(
        np.concatenate([classes["adjacent"], classes["opposite"]])
    )

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step3d1] rung '{name}': {ncells} cells (record "
            f"{STEP2_CELL_COUNT}, ratio {ncells / STEP2_CELL_COUNT:.6f}), mesh "
            f"{diag['mesh_wall_time_s']:.2f} s, rung {t_mesh:.2f} s; f = "
            f"{frequency_hz:.6e} Hz; four driven "
            f"solves in {t_sweep:.2f} s wall at -n 2; analytic sheet dx*g = "
            f"{sheet_analytic:.9e} m^2",
            flush=True,
        )
        for s in sheets:
            print(
                f"    sheet {s['tag']} (P{s['tag'] - SHEET_IFACE}): azimuth "
                f"{s['azimuth_deg']:8.4f} deg;  full sheet "
                f"{s['area_full']:.9e} m^2  meshed/analytic "
                f"{s['area_ratio_full']:.12f};  narrowed {s['facets']:5d} facets "
                f"area {s['area']:.9e} m^2  h = {s['h']:.9e} m  w = A/h = "
                f"{s['w']:.9e} m  out-of-plane {s['out_of_plane']:.3e} m",
                flush=True,
            )
        print(f"[PORT-9 step3d1] rung '{name}' Z (Ohm), column k = port k driven:")
        for row in range(LEG_COUNT):
            entries = "  ".join(f"{z:+.9e}" for z in z_matrix[row])
            print(f"    Z_{row + 1}k = {entries}", flush=True)
        print(f"[PORT-9 step3d1] rung '{name}' S (z0 = 50 Ohm, power-wave):")
        for row in range(LEG_COUNT):
            entries = "  ".join(f"{s:+.9e}" for s in s_matrix[row])
            print(f"    S_{row + 1}k = {entries}", flush=True)
        print(
            f"    ||S - S^T||/||S|| = {reciprocity:.9e}   "
            f"||Z - Z^T||/||Z|| = {z_reciprocity:.9e}\n"
            f"    sigma(S) = " + ", ".join(f"{v:.9f}" for v in sigma) + "\n"
            f"    column power sums = "
            + ", ".join(f"{v:.9f}" for v in column_power)
            + f"\n    class spreads: self {spreads['self'] * 100:.4f}%  adjacent "
            f"{spreads['adjacent'] * 100:.4f}%  opposite "
            f"{spreads['opposite'] * 100:.4f}%  (band "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}%); pooled off-diagonal "
            f"{pooled * 100:.4f}%",
            flush=True,
        )

    return {
        "name": name,
        "frequency_hz": float(frequency_hz),
        "column_power": column_power,
        "pooled": pooled,
        "result": result,
        "z": z_matrix,
        "s": s_matrix,
        "classes": classes,
        "spreads": spreads,
        "sigma": sigma,
        "reciprocity": reciprocity,
        "z_reciprocity": z_reciprocity,
        "sheets": sheets,
        "cells": ncells,
        "sheet_analytic": sheet_analytic,
        "sweep_time": float(t_sweep),
        # Additive, for `PORT-11` step 3's pre-gate resolution reading: the mesh
        # and its cell tags travel with the rung so a consumer can measure the
        # phantom's cell size (cells per skin depth / per wavelength) on the
        # *solved* mesh instead of building a fourth one.  Nothing in this module
        # reads them and no rung's numbers moved when they were added.
        "mesh": msh,
        "cell_tags": cell_tags,
        # Additive again, for `EX-34`'s one-mesh frequency ladder: the narrowed
        # sheet tags and the assembled problem/port objects, so a consumer can
        # hand this rung back as ``reuse=`` (and re-solve one driven case for a
        # field the sweep does not retain).  No gate in this repo reads them.
        "facet_tags": tags_f,
        "problem": problem,
        "port_defs": port_defs,
        "specs": specs,
        "mesh_time": float(diag["mesh_wall_time_s"]),
        "reused_mesh": reuse is not None,
    }


@pytest.fixture(scope="module")
def offset_rungs():
    """Two rungs of the same fixture: zero offsets, then leg 1 at 22.5 deg."""
    displaced = np.zeros(LEG_COUNT)
    displaced[0] = LEG_OFFSET_RAD
    rungs = {
        "zero": _four_port_rung("zero", np.zeros(LEG_COUNT)),
        "displaced": _four_port_rung("displaced", displaced),
    }
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d1] offset = {LEG_OFFSET_RAD:.9f} rad = "
            f"{np.degrees(LEG_OFFSET_RAD):.4f} deg on leg 1 only; sweeps "
            f"{rungs['zero']['sweep_time']:.2f} s + "
            f"{rungs['displaced']['sweep_time']:.2f} s at -n 2",
            flush=True,
        )
    return rungs


@complex_only
def test_both_rungs_drove_four_solved_field_ports(offset_rungs):
    """Structural: eight driven field solves on two conforming rungs.

    None of this is a gate; all of it is what the gates need in order to mean
    anything.  ``is_placeholder=False`` is what separates a solved field from the
    retired `PORT-0` coupling heuristic, and the zero rung's cell count is what
    says this is still leg (d)'s fixture.
    """
    for name, rung in offset_rungs.items():
        r = rung["result"]
        assert not r.is_placeholder, (
            f"rung '{name}': the sweep returned is_placeholder=True — it fell "
            "back to the PORT-0 coupling heuristic, so no impedance here came "
            "off a field"
        )
        assert rung["z"].shape == (LEG_COUNT, LEG_COUNT)
        assert np.all(np.isfinite(rung["z"].real))
        assert np.all(np.isfinite(rung["z"].imag))
        assert set(r.excitation_results) == {
            f"P{i}" for i in range(1, LEG_COUNT + 1)
        }
        for driven, response in r.excitation_results.items():
            assert response.responses[driven].is_driven
            for pid, est in response.responses.items():
                if pid != driven:
                    assert not est.is_driven

    ratio = offset_rungs["zero"]["cells"] / STEP2_CELL_COUNT
    assert abs(ratio - 1.0) < STEP2_CELL_COUNT_BAND, (
        f"the zero-offset rung meshed {offset_rungs['zero']['cells']} cells "
        f"against `GEO-19` step B's record {STEP2_CELL_COUNT}; this is not the "
        "fixture leg (d) measured, so its 4x4 is not comparable"
    )


@complex_only
def test_the_displaced_mesh_still_carries_four_clean_ports(offset_rungs):
    """**Negative control of the control**, on the mesh the solves ran on.

    Every sheet the displaced rung solved on must still be a full rectangle of
    closed-form area ``dx·g`` to 1e-9 before narrowing, still planar in its own
    port frame after it, and still narrower than the full sheet.  The mesh half
    of leg (d1') gates this on its own rungs; re-asserting it here means a class
    spread measured below cannot be blamed on a port that broke when it rotated.
    """
    for name, rung in offset_rungs.items():
        for s in rung["sheets"]:
            assert abs(s["area_ratio_full"] - 1.0) < SHEET_AREA_BAND, (
                f"rung '{name}' sheet {s['tag']}: the full sheet reads "
                f"{s['area_ratio_full']:.12f} of the closed-form dx*g against "
                f"the {SHEET_AREA_BAND:.0e} band — this port is not the clean "
                "`GEO-18` construction, so nothing solved on it is comparable"
            )
            assert s["out_of_plane"] < 1.0e-12, (
                f"rung '{name}' sheet {s['tag']}: spreads "
                f"{s['out_of_plane']:.3e} m along its own azimuthal direction — "
                "the narrowed facet set is not a plane"
            )
            assert s["w"] < s["w_full"], (
                f"rung '{name}' sheet {s['tag']}: A/h = {s['w']:.9e} m is not "
                f"below the full sheet's radial extent {s['w_full']:.9e} m — the "
                "interior-width filter did not run"
            )


@complex_only
def test_zero_offsets_reproduce_step_b(offset_rungs):
    """**Anchor (a), the identity control.**  Zero offsets give back leg (d0).

    The offsets are added to the nominal azimuths and adding an exact zero is
    exact, and this module's frame-aware sheet handling reduces term by term to
    leg (c)/(d)'s global-axis one for a port on a coordinate axis.  So the zero
    rung must reproduce the terminated column leg (d0) recorded on `GEO-19` step
    B's mesh, and step B's ``σ_max(S)``, to their printed precision.  If it does
    not, the knob (or the frame rewrite) changed the solve, and the displaced
    rung below would be measuring that change rather than the broken symmetry.
    Both bands are print-precision reproduction bands, not physics tolerances.
    """
    zero = offset_rungs["zero"]
    column = zero["z"][:, 0]
    sigma_max = float(np.max(zero["sigma"]))
    sigma_err = abs(sigma_max - STEP_B_SIGMA_MAX) / STEP_B_SIGMA_MAX

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d1] anchor (a): the zero rung vs `GEO-19` step B's "
            f"records, band {LEG_D0_REPRODUCTION_BAND:.0e} relative:",
            flush=True,
        )
        for k, (z, z_rec) in enumerate(zip(column, LEG_D0_Z_COLUMN), start=1):
            print(
                f"    Z_{k}1 {z:+.9e} vs record {z_rec:+.9e}  rel. deviation "
                f"{abs(z - z_rec) / abs(z_rec):.3e}",
                flush=True,
            )
        print(
            f"    sigma_max(S) {sigma_max:.9f} vs record {STEP_B_SIGMA_MAX:.9f}"
            f"  rel. deviation {sigma_err:.3e}\n"
            f"    class spreads: self {zero['spreads']['self'] * 100:.4f}%  "
            f"adjacent {zero['spreads']['adjacent'] * 100:.4f}%  opposite "
            f"{zero['spreads']['opposite'] * 100:.4f}%  vs (iii') "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}%",
            flush=True,
        )

    for k, (z, z_rec) in enumerate(zip(column, LEG_D0_Z_COLUMN), start=1):
        err = abs(z - z_rec) / abs(z_rec)
        assert err < LEG_D0_REPRODUCTION_BAND, (
            f"the zero-offset rung's Z_{k}1 = {z:+.9e} Ohm deviates {err:.3e} "
            f"from leg (d0)'s recorded {z_rec:+.9e} Ohm against the "
            f"{LEG_D0_REPRODUCTION_BAND:.0e} print-precision band — the offset "
            "knob or the frame-aware sheet handling moved the solve, so the "
            "displaced rung is not a controlled comparison"
        )
    assert sigma_err < LEG_D0_REPRODUCTION_BAND, (
        f"the zero-offset rung reads sigma_max(S) = {sigma_max:.9f} against step "
        f"B's recorded {STEP_B_SIGMA_MAX:.9f}, a {sigma_err:.3e} deviation on a "
        f"{LEG_D0_REPRODUCTION_BAND:.0e} print-precision band — this is not leg "
        "(d)'s assembled 4x4"
    )
    for name, value in zero["spreads"].items():
        assert value <= ADJACENT_SPREAD_BAND, (
            f"the zero rung's {name} class of Z spreads {value * 100:.4f}% "
            f"against (iii')'s {ADJACENT_SPREAD_BAND * 100:.1f}% band — leg "
            "(d)'s symmetric reading did not reproduce, so the displaced "
            "comparison below has no baseline"
        )


@complex_only
def test_the_displaced_rung_stays_reciprocal(offset_rungs):
    """**Anchor (b).**  Reciprocity survives the displacement, on power waves.

    Reciprocity is a property of the materials, not of the layout: a birdcage
    with one leg rotated is every bit as reciprocal as a symmetric one.  Holding
    it inside step 2c's band on the displaced rung is what separates "the gate
    measured geometry" from "the displaced solve fell apart", and it is the
    first test of leg (d3)'s power-wave `S` assembly on an asymmetric **3D**
    fixture — the pre-fix terminated-`Z` route read 5.57e-03 on this exact
    fixture, 223x outside the band.  Per (d3c) the reading itself is recorded as
    an order of magnitude, never pinned at a print band.
    """
    for name in ("zero", "displaced"):
        rung = offset_rungs[name]
        separation = PRE_FIX_Z_ROUTE_RECIPROCITY / max(rung["reciprocity"], 1.0e-300)
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"\n[PORT-9 step3d1] rung '{name}': ||S - S^T||/||S|| = "
                f"{rung['reciprocity']:.9e} (band {RECIPROCITY_BAND:.0e}, step "
                f"2c's, unmoved)  "
                f"{'PASS' if rung['reciprocity'] <= RECIPROCITY_BAND else 'MISS'}"
                f";  separation from the pre-fix Z-route reading "
                f"{PRE_FIX_Z_ROUTE_RECIPROCITY:.2e} is {separation:.3e}x"
                f";  sigma_max(S) = {np.max(rung['sigma']):.9f}",
                flush=True,
            )
        assert rung["reciprocity"] <= RECIPROCITY_BAND, (
            f"rung '{name}' reads ||S - S^T||/||S|| = {rung['reciprocity']:.9e} "
            f"against the pre-stated {RECIPROCITY_BAND:.0e} band — a route "
            "finding about the power-wave assembly on an asymmetric 3D fixture "
            "that the symmetric and 2D-asymmetric ones could not see, and on the "
            "displaced rung it would mean the class spreads below are measuring "
            "a broken solve rather than a broken symmetry (never widen)"
        )
        assert float(np.max(rung["sigma"])) <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
            f"rung '{name}': sigma_max(S) = {np.max(rung['sigma']):.9f} exceeds "
            f"1 by more than {PASSIVITY_SIGMA_TOLERANCE:.0e} — the assembled 4x4 "
            "is active"
        )


@complex_only
def test_gate_iii_detects_the_broken_c4(offset_rungs):
    """**Anchor (c), the leg's substance.**  Displaced, self and adjacent break.

    Leg 1 now sits 67.5 deg from P2 and 112.5 deg from P4 instead of 90 and 90,
    and 157.5 deg from P3 instead of 180, so the ``{Z_ii}`` and ``{Z_i,i±1}``
    classes are no longer classes at all: each mixes couplings at separations
    that leg (d0) already showed differ by 5.9% between 90 and 180 deg.  Gate
    (iii') is a symmetry gate only if it says so.

    The ``{Z_i,i+2}`` opposite class is **reported, not gated** here, by the
    2026-08-25 03:00 review's pre-ruling: it is physically the flattest of the
    three (the displacement moves one pair from 180 to 157.5 deg and leaves the
    other at 180), so if it stays under 0.5% that is a reading for the review to
    rule on, not a failure of this leg — and never a licence to widen (iii').

    A self *or* adjacent spread under the band is the pre-stated negative
    result and equally not a licence to move anything: it would mean gate (iii')
    is blind at this grain, `PORT-9` stays 🟡, and the review re-specifies (iii')
    (§7 `PORT-9` step 3 leg (d1')).
    """
    zero = offset_rungs["zero"]["spreads"]
    disp = offset_rungs["displaced"]["spreads"]

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d1] GATE (iii')'s negative control (band "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}%, the 2026-08-23 10:30 tightening "
            f"— the displaced rung must EXCEED it on self and adjacent; opposite "
            f"is reported only):",
            flush=True,
        )
        for cls in ("self", "adjacent", "opposite"):
            gated = "gated" if cls in ("self", "adjacent") else "reported"
            verdict = (
                "EXCEEDS (detected)"
                if disp[cls] > ADJACENT_SPREAD_BAND
                else "inside (blind)"
            )
            print(
                f"    {cls:9s} [{gated:8s}]  zero {zero[cls] * 100:9.4f}%   "
                f"displaced {disp[cls] * 100:9.4f}%   amplification "
                f"{disp[cls] / zero[cls]:12.2f}x   {verdict}",
                flush=True,
            )

    for cls in ("self", "adjacent"):
        assert disp[cls] > ADJACENT_SPREAD_BAND, (
            f"with leg 1 rotated {np.degrees(LEG_OFFSET_RAD):.1f} deg off the C4 "
            f"layout the {cls} class of Z still spreads only "
            f"{disp[cls] * 100:.4f}%, inside the "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}% band it passes on the symmetric "
            f"layout ({zero[cls] * 100:.4f}%) — gate (iii') does not detect a "
            "broken C4 at this grain, so its passing in leg (d) is a consistency "
            "check and not a symmetry gate (§7 `PORT-9` step 3 leg (d1'), "
            "negative result: record and stop; never widen (i)-(iii'))"
        )
