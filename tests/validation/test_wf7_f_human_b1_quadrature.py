"""`WF-7` step 2 — the 32-port ccw quadrature ``|B1+|`` on the F-human rung,
C16-gated.

§9 item 36 (2026-09-23 review, chain step H4).  One window, heavy tier,
``-n 8``, complex build, **selected by environment only**
(``FEM_EM_WF7_STEP2=1``), never by ``-k``.

The F-human fixture is assembled as step 1 assembles it
(``test_wf7_f_human_ring_matrix.py:170–247``: `GEO-25`'s branch-B rung at
``F_HUMAN_RING_RADIUS`` with longitudinal ring sheets, `PORT-13`'s materials,
PEC outer boundary, 64 MHz, degree 1) and handed to `POST-6` step 3's lifted
``_build_ring_quadrature_case(built=..., cell_record=...)`` — the quadrature
weights, ``superpose_drives``, ``project_to_cg1``, the fifteen C16 rotations,
the mirror, the exact identity and the prints are that function's, imported.

Anchors (asserted, every band imported, none restated):
  (i)   cells inside ``CELL_COUNT_BAND`` of ``F_HUMAN_BRANCH_B_CELL_RECORD``;
  (ii)  ``_ring_quadrature_slots``' own asserts (16 ports per ring on the
        22.5 deg grid within ``AZIMUTH_MATCH_DEG``) — executed inside the lifted
        function;
  (iii) worst C16 image of ``|B1+|_ccw`` ``<= C4_COVARIANCE_BAND``;
  (iv)  mirror ``|B1-|_cw(Mx)`` vs ``|B1+|_ccw(x)`` ``<= C4_COVARIANCE_BAND``;
  (v)   `PORT-16`'s exact discrete identity on the superposed ccw field
        ``<= DISCRETE_IDENTITY_RTOL``;
  (vi)  the unit-weight identity: ``e_P17`` returns drive P17's own field (and
        terminal currents) within ``UNIT_WEIGHT_CONTROL_RTOL``.

Negative controls — *predicted, printed, never asserted* (§9 rule (e); no
record on this fixture): the cw mis-paired reading with its ccw-only prediction
(printed by the lifted function), and the single-drive P17 field's worst C16
spread (predicted >> 5 %: one port is not a rotation-invariant drive).

Scope: C16 invariance of ``|B1+|`` at human scale, 64 MHz, degree 1, one
fixture — no homogeneity, absolute B1+, SAR or Larmor-accuracy claim; degree 1
at human scale carries the 2026-09-19 weekly's 5.50 % order caveat (`WF-7`
step 0b).
"""

from __future__ import annotations

import os
import resource
import time

import numpy as np
import pytest
from mpi4py import MPI

from tests.complex_mode import complex_only

STEP2_ENV = "FEM_EM_WF7_STEP2"
FREQUENCY_HZ = 64.0e6
DEGREE = 1
CONTROL_PORT = "P17"
# Step 1's printed S_driven(P17) (`20260921T093429Z_WF-7-step1.log:10541`),
# printed beside the package route's S[P17,P17] — never compared.
S_DRIVEN_STEP1_PRINTED = "0.407423+0.344417j"


def _step2_on() -> bool:
    return os.environ.get(STEP2_ENV, "").strip() == "1"


def _build_f_human(comm):
    """The F-human context in the dict shape ``_build_ring_quadrature_case`` reads."""
    from fem_em_solver.core import (
        HomogeneousMaterial,
        TimeHarmonicProblem,
        TimeHarmonicSolver,
    )
    from fem_em_solver.io.mesh import MeshGenerator, _interface_facet_tags
    from fem_em_solver.ports.lumped import LumpedSheetPortSpec

    from tests.mesh.test_birdcage_leg_offset import _sheet_azimuth_deg
    from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER, SHEET_IFACE
    from tests.mesh.test_birdcage_port_terminals import _interface_area_or_zero
    from tests.mesh.test_birdcage_ring_gaps_scaleup import _ring_gap_frame
    from tests.validation.test_birdcage_f_human_rung import (
        F_HUMAN_RING_RADIUS,
        LEG_COUNT,
        _params,
        _ring_ports,
    )
    from tests.validation.test_lossy_sphere_fullwave import (
        SALINE_EPSILON_R,
        SALINE_SIGMA,
    )
    from tests.validation.test_port_birdcage_four_port import (
        TERMINATED_PORT_IMPEDANCE_OHM,
    )
    from tests.validation.test_port_birdcage_lumped_column import (
        CONDUCTOR_CELL_TAG,
        PHANTOM_CELL_TAG,
    )
    from tests.validation.test_port_gap_voltage_impedance import SIGMA_WIRE_S_PER_M
    from tests.validation.test_wf7_f_human_ring_matrix import _sheet_centre_z

    kwargs = _params(F_HUMAN_RING_RADIUS, scale_sizing=False)
    kwargs["ring_sheet_orientation"] = "longitudinal"
    msh, cell_tags, _facets, diag = MeshGenerator.birdcage_port_domain(
        comm=comm, return_diagnostics=True, **kwargs
    )
    n_cells = int(msh.topology.index_map(3).size_global)
    ring_ports = _ring_ports()
    assert len(ring_ports) == 2 * LEG_COUNT
    tags_f = _interface_facet_tags(
        msh, cell_tags,
        {SHEET_IFACE + i: (PORT_LOWER + i, PORT_UPPER + i) for i in ring_ports},
    )
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()
    chord = float(diag["ring_port_layout"]["ring_port_gap_chord_m"])
    specs = []
    sheets = []
    for i in ring_ports:
        area = _interface_area_or_zero(msh, tags_f, SHEET_IFACE + i, comm)
        phi_hat, _centre = _ring_gap_frame(i, LEG_COUNT)
        specs.append(
            LumpedSheetPortSpec(
                port_id=f"P{i}",
                facet_tag=int(SHEET_IFACE + i),
                port_impedance_ohm=TERMINATED_PORT_IMPEDANCE_OHM,
                gap_height_m=chord,
                sheet_width_m=area / chord,
                drive_direction=tuple(float(c) for c in phi_hat),
                drive_voltage_v=1.0 + 0.0j,
                interior=True,
            )
        )
        sheets.append(
            {
                "ordinal": i,
                "tag": SHEET_IFACE + i,
                "azimuth_deg": float(_sheet_azimuth_deg(msh, tags_f, SHEET_IFACE + i, comm)),
                "z": float(_sheet_centre_z(msh, tags_f, SHEET_IFACE + i, comm)),
            }
        )
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
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
    ctx = {
        "comm": comm,
        "msh": msh,
        "tags_f": tags_f,
        "cell_tags": cell_tags,
        "omega": 2.0 * np.pi * FREQUENCY_HZ,
        "specs": specs,
        "solver": TimeHarmonicSolver(problem, degree=DEGREE),
    }
    return {"comm": comm, "ctx": ctx, "cells": n_cells, "sheets": sheets}


@pytest.fixture(scope="module")
def f_human_quadrature_case():
    if not _step2_on():
        pytest.skip(
            f"{STEP2_ENV} unset: the F-human 32-port quadrature drive is a heavy "
            "-n 8 window selected by environment only"
        )
    # Lazy: a module-level import of the POST-6 module cycles (its
    # ``_step3_imports`` docstring).
    from tests.validation import test_port_drive_superposition as post6
    from tests.validation.test_birdcage_f_human_rung import F_HUMAN_BRANCH_B_CELL_RECORD

    comm = MPI.COMM_WORLD
    t_window = time.perf_counter()
    t0 = time.perf_counter()
    built = _build_f_human(comm)
    build_s = time.perf_counter() - t0
    if comm.rank == 0:
        print(
            f"\n[WF-7 step2] F-human built: {built['cells']} cells (record "
            f"{F_HUMAN_BRANCH_B_CELL_RECORD}), {len(built['sheets'])} ring ports, "
            f"{build_s:.2f} s at -n {comm.size}; f = {FREQUENCY_HZ:.3e} Hz, degree {DEGREE}",
            flush=True,
        )
    case = post6._build_ring_quadrature_case(
        built=built, cell_record=F_HUMAN_BRANCH_B_CELL_RECORD
    )

    # ---- (vi) the unit-weight identity on drive P17 ------------------------
    result = case["result"]
    port_ids = case["port_ids"]
    index = port_ids.index(CONTROL_PORT)
    e_k = np.zeros(len(port_ids), dtype=np.complex128)
    e_k[index] = 1.0
    single = post6.superpose_drives(result, e_k, name="E_P17_unit")
    a = np.asarray(single.e_complex.x.array)
    b = np.asarray(result.fields[CONTROL_PORT].e_complex.x.array)
    num = comm.allreduce(float(np.sum(np.abs(a - b) ** 2)), op=MPI.SUM)
    den = comm.allreduce(float(np.sum(np.abs(b) ** 2)), op=MPI.SUM)
    field_dev = float(np.sqrt(num / den))
    current_dev = 0.0
    for other in port_ids:
        expected = complex(result.excitation_results[CONTROL_PORT].responses[other].current_a)
        got = complex(single.currents[other])
        current_dev = max(current_dev, abs(got - expected) / max(abs(expected), 1e-300))

    # ---- predicted control: single-drive P17's worst C16 spread -----------
    t0 = time.perf_counter()
    points = case["points"]
    cg1_single = post6.project_to_cg1(single.b_complex, name="B_P17_cg1")
    step = 360.0 / len(port_ids) * 2.0  # 22.5 deg on the 16-leg ring
    reads = {0: post6._read_senses(cg1_single, points)}
    for m in range(1, len(port_ids) // 2):
        reads[m] = post6._read_senses(
            cg1_single, post6._rotate_z(points, np.radians(m * step))
        )
    mask = np.logical_and.reduce([case["mask"]] + [r[2] for r in reads.values()])
    single_c16 = {
        m: post6._relative_l2(reads[m][0], reads[0][0], mask) for m in reads if m != 0
    }
    single_worst_m = max(single_c16, key=single_c16.get)
    t_control = time.perf_counter() - t0

    rss_gib = float(
        comm.allreduce(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, op=MPI.SUM)
    ) / (1024.0 * 1024.0)
    wall = time.perf_counter() - t_window
    s_pp = complex(result.s_matrix[index, index])
    worst = case["c16"][case["worst_m"]]
    if comm.rank == 0:
        print(
            f"[WF-7 step2] (vi) unit weight e_{CONTROL_PORT}: field rel L2 dev "
            f"{field_dev:.3e}, worst terminal-current rel dev {current_dev:.3e} "
            f"(ASSERTED <= UNIT_WEIGHT_CONTROL_RTOL {post6.UNIT_WEIGHT_CONTROL_RTOL:g})\n"
            f"[WF-7 step2] negative control (PREDICTED >> "
            f"{post6.C4_COVARIANCE_BAND * 100:.1f}%, never asserted): single-drive "
            f"{CONTROL_PORT} worst C16 spread {single_c16[single_worst_m] * 100:.4f}% at "
            f"R_{single_worst_m} ({single_c16[single_worst_m] / worst:.1f}x the ccw "
            f"worst {worst * 100:.4f}%), {int(np.count_nonzero(mask))} points\n"
            f"[WF-7 step2] package S[{CONTROL_PORT},{CONTROL_PORT}] = "
            f"{s_pp.real:.6f}{s_pp.imag:+.6f}j beside step 1's printed "
            f"{S_DRIVEN_STEP1_PRINTED} (printed, not compared)\n"
            f"[WF-7 step2] PRICE: build {build_s:.2f} s, single-drive control "
            f"{t_control:.2f} s, window {wall:.2f} s wall at -n {comm.size}; summed "
            f"ru_maxrss {rss_gib:.3f} GiB",
            flush=True,
        )
    case.update(
        field_dev=field_dev,
        current_dev=current_dev,
        cell_record=F_HUMAN_BRANCH_B_CELL_RECORD,
        post6=post6,
    )
    return case


@complex_only
def test_i_the_f_human_cell_record(f_human_quadrature_case):
    """**(i)** the imported cell band, and (ii) ran inside the lifted build."""
    from tests.mesh.test_birdcage_port_sheet_prerequisite import CELL_COUNT_BAND

    c = f_human_quadrature_case
    rel = c["cells"] / c["cell_record"] - 1.0
    assert abs(rel) < CELL_COUNT_BAND, (
        f"{c['cells']} cells vs record {c['cell_record']}: {rel:.3e}"
    )
    assert len(c["port_ids"]) == 32


@complex_only
def test_iii_ccw_b1_plus_is_c16_invariant(f_human_quadrature_case):
    c = f_human_quadrature_case
    band = c["post6"].C4_COVARIANCE_BAND
    worst = c["c16"][c["worst_m"]]
    assert worst <= band, (
        f"|B1+|_ccw not C16-invariant at human scale: R_{c['worst_m']} "
        f"{worst * 100:.4f}% > {band * 100:.1f}%"
    )


@complex_only
def test_iv_mirror_identity(f_human_quadrature_case):
    c = f_human_quadrature_case
    band = c["post6"].C4_COVARIANCE_BAND
    assert c["mirror"] <= band, f"mirror {c['mirror'] * 100:.4f}% > {band * 100:.1f}%"


@complex_only
def test_v_exact_identity_on_the_superposed_field(f_human_quadrature_case):
    c = f_human_quadrature_case
    assert c["identity_dev"] <= c["identity_rtol"], (
        f"identity {c['identity_dev']:.3e} > {c['identity_rtol']:g}"
    )


@complex_only
def test_vi_unit_weight_returns_p17(f_human_quadrature_case):
    c = f_human_quadrature_case
    rtol = c["post6"].UNIT_WEIGHT_CONTROL_RTOL
    assert c["field_dev"] <= rtol, f"field dev {c['field_dev']:.3e} > {rtol:g}"
    assert c["current_dev"] <= rtol, f"current dev {c['current_dev']:.3e} > {rtol:g}"
