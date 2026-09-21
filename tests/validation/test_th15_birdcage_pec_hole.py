"""`TH-15` step 3 — the gapped 4-leg birdcage as a PEC hole, `PORT-9`/`PORT-11`'s gates.

The hole fixture is exactly what step 3a's gate builds
(``tests/mesh/test_birdcage_port_sheets._build(emit_port_sheets=True,
as_hole=True)``, `tests/mesh/test_birdcage_conductor_hole.py:170`): the coil is
cut from the box, its cavity wall is facet group
``BIRDCAGE_CONDUCTOR_SURFACE_TAG`` (401), the phantom stays.

**How tag 401 becomes PEC.**  ``TimeHarmonicProblem.pec_facet_tags`` narrows the
constrained set to the listed tags only.  ``birdcage_port_domain`` tags no
outer-box facet group, so ``pec_facet_tags=(401,)`` would *drop* the outer
box's PEC — a different fixture from `PORT-9`'s.  On the hole mesh the cavity
wall is itself exterior, so the default ``pec_facet_tags=None`` (every exterior
facet) pins the outer box **and** the cavity wall; the fixture asserts that
containment (every tag-401 facet is an exterior facet, reduced over ranks).
``run_lumped_sheet_port_case`` needs no keyword: it builds its solver from the
problem, which carries the PEC selection.  The natural-cavity control (tag 401
*not* pinned) is not constructible without an outer-box tag and is not run.

Anchors (bands imported, never restated): reciprocity ``RECIPROCITY_BAND``,
``σ_max ≤ 1 + PASSIVITY_SIGMA_TOLERANCE``, every C4 class spread
``≤ ADJACENT_SPREAD_BAND`` (the tightened (iii′) 0.5 %), and the power identity
``Re P_in = Σ_i ½ Re(V_i Ī_i) = ½∫_phantom σ|E|²`` to 1e-3 on the P1 drive (all
loss is in the phantom by construction on the hole route).

One frequency per window: ``TH15_STEP3_FREQ_MHZ`` ∈ {10, 64, 128}.
``TH15_STEP3_SOLID_CONTROL=1`` additionally runs the solid route through
`PORT-11`'s own ``_four_port_rung`` at 10 MHz and asserts `PORT-11`'s
``LEG_D_S_MATRIX_10MHZ`` record at ``FREQUENCY_CONTROL_BAND``.

**Step 3c (attribution of the hole's terminal-power excess).**  Both routes get
the same P1 power attribution (:func:`_power_attribution`): per port
``½Re(V I*)`` and the sheet's form-level dissipation ``P_sheet,field``,
``C/terminal − 1`` from ``fem_em_solver.ports.shares`` (imported), the phantom
loss and ``½∫_{Ω∖phantom} σ|E|²``.  Asserted: (a) ``P_src − ΣP_sheet,field =
P_phantom + P_{Ω∖phantom}`` at `PORT-16`'s imported ``DISCRETE_IDENTITY_RTOL``
on both routes — an identity of the discrete solve, true by construction — with
the hole's ``P_{Ω∖phantom} ≤ 1e-12 W`` (a conductor-free mesh, also by
construction); (b) the solid's P1 ``C/terminal − 1`` reproduces `PORT-14` step
2d's 1.059204e-02 (``20260912T123429Z_PORT-14-step2d-10mhz.log:1938``) at rtol
1e-3.  Printed, never asserted: the hole's ``C/terminal − 1`` beside the
solid's, the per-sheet split, the excess / ``P_src`` and the 5× filing ratio.
Because ``V = V_s − I Z_p`` per port, ``Σ½Re(V I*) = ½Re(V_s Ī₁) −
Σ½|I|²Re Z_p`` exactly, so the excess over the volume loss is printed as its
source part ``½Re(V_s Ī₁) − P_src`` plus its sheet part ``ΣP_sheet,field −
Σ½|I|²Re Z_p``.
"""

from __future__ import annotations

import os
import time

import dolfinx
import numpy as np
import pytest
import ufl
from dolfinx import fem
from mpi4py import MPI

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.io.mesh import BIRDCAGE_CONDUCTOR_SURFACE_TAG
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.lumped import LumpedSheetPortSpec, run_lumped_sheet_port_case
from fem_em_solver.ports.shares import terminal_form_deficit
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_leg_offset import (
    _projected_extents,
    _sheet_areas,
    _sheet_azimuth_deg,
)
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE, _build as _sheets_build
from tests.mesh.test_birdcage_port_tags import LEG_COUNT
from tests.mesh.test_two_torus_port_facets import _facet_group_area
from tests.mesh.test_two_torus_port_sheet import _sheet_facet_count
from tests.validation.test_birdcage_power_identity import (
    DISCRETE_IDENTITY_RTOL,
    _sheet_field_dissipation_w,
    _source_power_w,
)
from tests.validation.test_lossy_sphere_fullwave import (
    FREQUENCY_64_HZ,
    SALINE_EPSILON_R,
    SALINE_SIGMA,
)
from tests.validation.test_port_birdcage_four_port import (
    PASSIVITY_SIGMA_TOLERANCE,
    TERMINATED_PORT_IMPEDANCE_OHM,
    _circulant_classes,
    _class_spread,
)
from tests.validation.test_port_birdcage_larmor_gate import (
    FREQUENCY_CONTROL_BAND,
    LEG_D_S_MATRIX_10MHZ,
)
from tests.validation.test_port_birdcage_leg_offset_sweep import (
    _four_port_rung,
    _narrowed_radial,
    _port_frame,
)
from tests.validation.test_port_birdcage_lumped_column import (
    ADJACENT_SPREAD_BAND,
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ
from tests.validation.test_port_lumped_narrowed_sheet import GATED_WIDTH_FRACTION
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND
from tests.validation.test_port_package_sparameters import REFERENCE_IMPEDANCE_OHM

FREQ_ENV = "TH15_STEP3_FREQ_MHZ"
CONTROL_ENV = "TH15_STEP3_SOLID_CONTROL"
FREQUENCIES_HZ = {"10": FREQUENCY_HZ, "64": FREQUENCY_64_HZ, "128": 128.0e6}
DRIVEN = "P1"
# Pre-registered in §9 item 8 (2026-09-13): the hole route's lossless power
# identity, P1 drive, terminal form against the phantom volume loss.
POWER_IDENTITY_BAND = 1.0e-3

# Step 3c anchor (b): `PORT-14` step 2d's P1 pooled C/terminal − 1 on the solid
# 10 MHz fixture (`20260912T123429Z_PORT-14-step2d-10mhz.log:1938`).
SOLID_P1_C_OVER_TERMINAL_10MHZ = 1.059204217e-02
SOLID_C_OVER_TERMINAL_RTOL = 1.0e-3
# Step 3c anchor (a), hole: no lossy volume outside the phantom exists.
HOLE_NON_PHANTOM_LOSS_MAX_W = 1.0e-12
# *Predicted, printed only* (§9 item 3): excess / P_src ≈ 7.6937e-05 / 2.657e-03,
# and the filing threshold hole/solid C/terminal − 1 ratio.
PREDICTED_EXCESS_OVER_P_SRC = 7.6937e-05 / 2.657078677e-03
PREDICTED_FILING_RATIO = 5.0


def _power_attribution(msh, cell_tags, tags_f, specs, p1, fields, frequency_hz):
    """The P1 drive's power terms on one route, every scalar MPI-reduced."""
    comm = msh.comm
    e = fields.e_complex
    sigma = fields.sigma_field
    assert sigma is not None, "solved fields carry no sigma_field"
    omega = 2.0 * np.pi * float(frequency_hz)
    acct = {"mesh": msh, "facet_tags": tags_f}
    sheet_objs = {sp.port_id: sp.sheet(driven=(sp.port_id == DRIVEN)) for sp in specs}
    p_sheets = {
        pid: _sheet_field_dissipation_w(acct, sh, e, omega) for pid, sh in sheet_objs.items()
    }
    p_src = _source_power_w(acct, sheet_objs[DRIVEN], e, omega)
    dx = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)

    def _vol(measure):
        form = fem.form(0.5 * sigma * ufl.inner(e, e) * measure)
        return float(np.real(comm.allreduce(fem.assemble_scalar(form), op=MPI.SUM)))

    p_total_vol = _vol(dx)
    p_phantom = _vol(dx(PHANTOM_CELL_TAG))
    terms = {
        pid: 0.5 * complex(r.voltage_v) * np.conjugate(complex(r.current_a))
        for pid, r in p1.responses.items()
    }
    currents = {pid: complex(r.current_a) for pid, r in p1.responses.items()}
    deficit = terminal_form_deficit(msh, tags_f, list(sheet_objs.values()), e, comm)
    v_s = complex(sheet_objs[DRIVEN].source_voltage_v)
    p_src_terminal = float(np.real(0.5 * v_s * np.conjugate(currents[DRIVEN])))
    terminal_sum = float(np.real(sum(terms.values())))
    return {
        "p_src": float(p_src),
        "p_sheets": p_sheets,
        "p_sheets_total": float(sum(p_sheets.values())),
        "p_phantom": p_phantom,
        # Whole-domain minus phantom: the conductor on the solid, 0 on the hole.
        "p_non_phantom": float(p_total_vol - p_phantom),
        "terms": terms,
        "currents": currents,
        "terminal_sum": terminal_sum,
        "p_src_terminal": p_src_terminal,
        "deficit": deficit,
    }


def _attribution_residual(a):
    return abs(a["p_src"] - a["p_sheets_total"] - a["p_phantom"] - a["p_non_phantom"]) / abs(
        a["p_src"]
    )


def _print_attribution(label, a):
    if MPI.COMM_WORLD.rank != 0:
        return
    d = a["deficit"]
    excess = a["terminal_sum"] - a["p_phantom"] - a["p_non_phantom"]
    src_part = a["p_src_terminal"] - a["p_src"]
    sheet_part = a["p_sheets_total"] - d["terminal_total"]
    print(f"\n[TH-15 step3c] {label}: P1 drive power attribution", flush=True)
    for pid in a["terms"]:
        print(
            f"    {pid}: 1/2 Re(V I*) {a['terms'][pid].real:+.9e} W   P_sheet,field "
            f"{a['p_sheets'][pid]:.9e} W   1/2|I|^2 Re Z_p {d['terminal'][pid]:.9e} W   "
            f"ceiling C {d['ceiling'][pid]:.9e} W   C/terminal - 1 "
            f"{d['per_sheet'][pid]:+.9e} (per-sheet split, PRINTED)",
            flush=True,
        )
    print(
        f"    P_src {a['p_src']:.9e} W   sum P_sheet,field {a['p_sheets_total']:.9e} W   "
        f"P_phantom {a['p_phantom']:.9e} W   P_(Omega\\phantom) {a['p_non_phantom']:.9e} W\n"
        f"    (a) |P_src - sum P_sheet - P_phantom - P_nonphantom|/P_src = "
        f"{_attribution_residual(a):.3e} (ASSERTED <= {DISCRETE_IDENTITY_RTOL:g}; "
        "discrete identity, true by construction)\n"
        f"    driven-port C/terminal - 1 (pooled) = {d['pooled']:.9e}\n"
        f"    sum 1/2 Re(V I*) {a['terminal_sum']:.9e} W; excess over volume loss "
        f"{excess:.9e} W = {excess / a['p_src']:.4e} of P_src (PRINTED; predicted "
        f"{PREDICTED_EXCESS_OVER_P_SRC:.4e} on the hole)\n"
        f"    split (exact algebra, V = V_s - I Z_p): source part 1/2 Re(V_s I1*) - P_src = "
        f"{a['p_src_terminal']:.9e} - {a['p_src']:.9e} = {src_part:+.9e} W; sheet part "
        f"sum P_sheet,field - sum 1/2|I|^2 Re Z_p = {sheet_part:+.9e} W; "
        f"sum {src_part + sheet_part:+.9e} W; C_total - terminal_total "
        f"{d['ceiling_total'] - d['terminal_total']:+.9e} W",
        flush=True,
    )


def _frequency_key() -> str:
    raw = os.environ.get(FREQ_ENV, "").strip()
    if raw not in FREQUENCIES_HZ:
        raise RuntimeError(
            f"{FREQ_ENV} must be one of {sorted(FREQUENCIES_HZ)} (one frequency "
            f"per window); got {raw!r}"
        )
    return raw


def _cavity_census(msh, facet_tags, comm):
    """Tag-401 facets (owned), and how many of them are *not* exterior."""
    fdim = msh.topology.dim - 1
    msh.topology.create_connectivity(fdim, msh.topology.dim)
    n_owned = msh.topology.index_map(fdim).size_local
    cavity = np.asarray(facet_tags.find(BIRDCAGE_CONDUCTOR_SURFACE_TAG), dtype=np.int32)
    cavity = cavity[cavity < n_owned]
    exterior = dolfinx.mesh.exterior_facet_indices(msh.topology)
    not_exterior = np.setdiff1d(cavity, exterior)
    return (
        comm.allreduce(int(cavity.size), op=MPI.SUM),
        comm.allreduce(int(not_exterior.size), op=MPI.SUM),
    )


def _hole_rung(frequency_hz, degree: int = 1):
    """`_four_port_rung`'s construction on the hole mesh; no conductor material.

    ``degree`` (`ANS-6` step 2, additive): N1curl order forwarded to both
    solves; the default 1 is this module's gate, unchanged.
    """
    comm = MPI.COMM_WORLD
    ports_idx = list(range(1, LEG_COUNT + 1))
    msh, cell_tags, facet_tags, diag, t_mesh = _sheets_build(True, as_hole=True)
    tdim = msh.topology.dim
    ncells = int(msh.topology.index_map(tdim).size_global)
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()
    n_cavity, n_cavity_interior = _cavity_census(msh, facet_tags, comm)

    tags_f, full_areas = _sheet_areas(msh, cell_tags, ports_idx, comm)
    geometry = {}
    for i in ports_idx:
        tag = SHEET_IFACE + i
        azimuth = _sheet_azimuth_deg(msh, tags_f, tag, comm)
        radial, azimuthal, axial = _port_frame(azimuth)
        spans, centres = _projected_extents(msh, tags_f, tag, comm, [radial, azimuthal, axial])
        geometry[i] = {
            "tag": tag,
            "azimuth_deg": float(azimuth),
            "radial": radial,
            "w_full": float(spans[0]),
            "centre_radial": float(centres[0]),
        }
    for i in ports_idx:
        g = geometry[i]
        tags_f = _narrowed_radial(
            msh, tags_f, g["tag"], GATED_WIDTH_FRACTION, g["centre_radial"],
            g["radial"], 0.5 * g["w_full"],
        )
    sheets = []
    for i in ports_idx:
        g = geometry[i]
        n_facets = _sheet_facet_count(msh, tags_f, g["tag"], comm)
        assert n_facets > 0, f"sheet {g['tag']}: no owned facets anywhere"
        area = _facet_group_area(msh, tags_f, g["tag"], comm)
        radial, azimuthal, axial = _port_frame(g["azimuth_deg"])
        spans, _c = _projected_extents(msh, tags_f, g["tag"], comm, [radial, azimuthal, axial])
        sheets.append({**g, "facets": int(n_facets), "area": float(area),
                       "h": float(spans[2]), "w": float(area / spans[2])})

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=frequency_hz,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            PHANTOM_CELL_TAG: HomogeneousMaterial(
                sigma=SALINE_SIGMA, epsilon_r=SALINE_EPSILON_R, mu_r=1.0
            ),
        },
        boundary_condition="pec_zero_tangential_a",
        facet_tags=facet_tags,
        pec_facet_tags=None,
    )
    port_defs, specs = [], []
    for s in sheets:
        pid = f"P{s['tag'] - SHEET_IFACE}"
        port_defs.append(PortDefinition(
            port_id=pid, positive_tag=int(s["tag"]), negative_tag=CONDUCTOR_CELL_TAG,
            orientation="leg_gap_axial_plus_z", z0_ohm=REFERENCE_IMPEDANCE_OHM,
        ))
        specs.append(LumpedSheetPortSpec(
            port_id=pid, facet_tag=int(s["tag"]),
            port_impedance_ohm=TERMINATED_PORT_IMPEDANCE_OHM, gap_height_m=s["h"],
            sheet_width_m=s["w"], drive_direction=(0.0, 0.0, 1.0),
            drive_voltage_v=1.0 + 0.0j, interior=True,
        ))

    comm.Barrier()
    t0 = time.perf_counter()
    result = run_n_port_sparameter_sweep(
        problem, port_defs, lumped_sheet_ports=specs, lumped_sheet_facet_tags=tags_f,
        degree=degree,
    )
    comm.Barrier()
    t_sweep = time.perf_counter() - t0

    # The power identity needs the field; one extra P1 solve (own factorisation).
    t0 = time.perf_counter()
    p1, fields = run_lumped_sheet_port_case(
        problem, port_defs, specs, facet_tags=tags_f, driven_port_id=DRIVEN,
        verbose=False, return_fields=True, degree=degree,
    )
    comm.Barrier()
    t_p1 = time.perf_counter() - t0
    e = fields.e_complex
    dx = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)
    loss_form = fem.form(0.5 * SALINE_SIGMA * ufl.inner(e, e) * dx(PHANTOM_CELL_TAG))
    p_phantom = float(np.real(comm.allreduce(fem.assemble_scalar(loss_form), op=MPI.SUM)))
    # Terminal form, printed only: the first window (20260913T202311Z_TH-15.log:958)
    # asserted it and read 7.700e-05 W against 6.376e-08 W — the terminal
    # ½|I|²R of a sheet is not its form-level dissipation (`PORT-16`/`TH-19`),
    # so that comparand was mis-registered.  The asserted P_in is the exact
    # accounting the solve assembled: source power minus the sheets' own
    # bilinear-term dissipation, through `TH-19`'s imported helpers.
    p_in_terms = {
        pid: 0.5 * complex(r.voltage_v) * np.conjugate(complex(r.current_a))
        for pid, r in p1.responses.items()
    }
    p_in_terminal = float(np.real(sum(p_in_terms.values())))
    omega = 2.0 * np.pi * float(frequency_hz)
    acct = {"mesh": msh, "facet_tags": tags_f}
    sheet_objs = {sp.port_id: sp.sheet(driven=(sp.port_id == DRIVEN)) for sp in specs}
    p_sheets = {
        pid: _sheet_field_dissipation_w(acct, sh, e, omega) for pid, sh in sheet_objs.items()
    }
    p_src = _source_power_w(acct, sheet_objs[DRIVEN], e, omega)
    p_in = float(p_src - sum(p_sheets.values()))

    z = np.asarray(result.z_matrix, dtype=np.complex128)
    s = np.asarray(result.s_matrix, dtype=np.complex128)
    classes = _circulant_classes(z)
    return {
        "cells": ncells,
        "t_mesh": float(t_mesh),
        "n_cavity": n_cavity,
        "n_cavity_interior": n_cavity_interior,
        "sheets": sheets,
        # Additive (EX-54, `ANS-1`/rule (a)): the mesh, tags and solved P1
        # field, so an example can render `|E|` and the cavity wall's
        # `n x E` without re-solving or re-meshing. Nothing above was
        # renamed or removed. Two distinct facet-tags objects exist in this
        # function: `facet_tags` (from `_sheets_build`, carries tag 401, the
        # cavity wall, and is what the problem itself was built with) and
        # `tags_f` (the sheet-only tags, narrowed radially for the ports) --
        # both are returned, under their own keys, so a caller cannot
        # silently reach for the wrong one.
        "mesh": msh,
        "cell_tags": cell_tags,
        "wall_facet_tags": facet_tags,
        "sheet_facet_tags": tags_f,
        "fields": fields,
        "z": z,
        "s": s,
        "spreads": {n: _class_spread(v) for n, v in classes.items()},
        "sigma": np.linalg.svd(s, compute_uv=False),
        "reciprocity": float(np.linalg.norm(s - s.T) / np.linalg.norm(s)),
        "t_sweep": float(t_sweep),
        "t_p1": float(t_p1),
        "p_in": p_in,
        "p_in_terminal": p_in_terminal,
        "p_src": p_src,
        "p_sheets": p_sheets,
        "p_in_terms": p_in_terms,
        "p_phantom": p_phantom,
        "p1_s_column": s[:, 0].copy(),
        "p1_currents": {pid: complex(r.current_a) for pid, r in p1.responses.items()},
        "attr": _power_attribution(msh, cell_tags, tags_f, specs, p1, fields, frequency_hz),
    }


@pytest.fixture(scope="module")
def hole():
    key = _frequency_key()
    f_hz = FREQUENCIES_HZ[key]
    comm = MPI.COMM_WORLD
    t0 = time.perf_counter()
    rung = _hole_rung(f_hz)
    rung["f_hz"] = f_hz
    rung["t_total"] = time.perf_counter() - t0
    if comm.rank == 0:
        print(
            f"\n[TH-15 step3] hole f = {f_hz:.6e} Hz: {rung['cells']} cells, mesh "
            f"{rung['t_mesh']:.1f} s, sweep {rung['t_sweep']:.1f} s, P1 field solve "
            f"{rung['t_p1']:.1f} s, total {rung['t_total']:.1f} s at -n {comm.size}; "
            f"tag {BIRDCAGE_CONDUCTOR_SURFACE_TAG}: {rung['n_cavity']} owned facets, "
            f"{rung['n_cavity_interior']} not exterior",
            flush=True,
        )
        for sh in rung["sheets"]:
            print(f"    sheet {sh['tag']}: az {sh['azimuth_deg']:8.4f} deg, "
                  f"{sh['facets']} facets, h {sh['h']:.6e} m, w {sh['w']:.6e} m", flush=True)
        for row in range(LEG_COUNT):
            print("    Z_%dk = " % (row + 1) + "  ".join(f"{v:+.9e}" for v in rung["z"][row]), flush=True)
        for row in range(LEG_COUNT):
            print("    S_%dk = " % (row + 1) + "  ".join(f"{v:+.9e}" for v in rung["s"][row]), flush=True)
        sp = rung["spreads"]
        print(
            f"    ||S-S^T||/||S|| = {rung['reciprocity']:.9e} (band {RECIPROCITY_BAND:.0e})\n"
            f"    sigma(S) = " + ", ".join(f"{v:.9f}" for v in rung["sigma"])
            + f" (band 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e})\n"
            f"    class spreads: self {sp['self'] * 100:.4f}%  adjacent "
            f"{sp['adjacent'] * 100:.4f}%  opposite {sp['opposite'] * 100:.4f}% "
            f"(band {ADJACENT_SPREAD_BAND * 100:.1f}%)\n"
            f"    power (exact form): P_src {rung['p_src']:.9e} W - sheets "
            f"{sum(rung['p_sheets'].values()):.9e} W = Re P_in {rung['p_in']:.9e} W; "
            f"terminal-form sum 1/2 Re(V I*) {rung['p_in_terminal']:.9e} W (record only); "
            f"1/2 int_phantom sigma|E|^2 = {rung['p_phantom']:.9e} W; rel dev "
            f"{abs(rung['p_in'] - rung['p_phantom']) / abs(rung['p_phantom']):.3e} "
            f"(band {POWER_IDENTITY_BAND:.0e})",
            flush=True,
        )
        for pid, v in rung["p_in_terms"].items():
            print(f"      {pid}: 1/2 V I* = {v:+.9e} VA", flush=True)
        # Consistency of the extra P1 solve with the sweep's P1 column.
        print("    P1 currents (field solve): " + ", ".join(
            f"{pid} {c:+.9e}" for pid, c in rung["p1_currents"].items()), flush=True)
    _print_attribution(f"hole f = {f_hz:.3e} Hz", rung["attr"])
    return rung


@pytest.fixture(scope="module")
def solid():
    """`PORT-11`'s own solid rung at 10 MHz plus one P1 field solve (step 3c)."""
    if os.environ.get(CONTROL_ENV, "").strip() != "1":
        pytest.skip(f"{CONTROL_ENV} != 1: solid control not requested in this window")
    rung = _four_port_rung("TH-15 solid control 10 MHz", np.zeros(LEG_COUNT), FREQUENCY_HZ)
    p1, fields = run_lumped_sheet_port_case(
        rung["problem"], rung["port_defs"], rung["specs"], facet_tags=rung["facet_tags"],
        driven_port_id=DRIVEN, verbose=False, return_fields=True,
    )
    rung["attr"] = _power_attribution(
        rung["mesh"], rung["cell_tags"], rung["facet_tags"], rung["specs"], p1, fields,
        FREQUENCY_HZ,
    )
    _print_attribution("solid control f = 1.000e+07 Hz", rung["attr"])
    return rung


@complex_only
def test_the_cavity_wall_is_pinned(hole):
    """Tag 401 exists and every facet of it is exterior, so ``None`` pins it."""
    assert hole["n_cavity"] > 0, "hole mesh has no tag-401 facets"
    assert hole["n_cavity_interior"] == 0, (
        f"{hole['n_cavity_interior']} tag-401 facets are not exterior facets; "
        "pec_facet_tags=None would not pin them"
    )


@complex_only
def test_the_hole_birdcage_is_reciprocal(hole):
    assert hole["reciprocity"] <= RECIPROCITY_BAND, (
        f"hole ||S-S^T||/||S|| = {hole['reciprocity']:.3e} > {RECIPROCITY_BAND:.0e} "
        f"at {hole['f_hz']:.3e} Hz"
    )


@complex_only
def test_the_hole_birdcage_is_passive(hole):
    sigma_max = float(np.max(hole["sigma"]))
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"hole sigma_max(S) = {sigma_max:.12f} at {hole['f_hz']:.3e} Hz"
    )


@complex_only
def test_the_hole_impedance_matrix_is_c4_circulant(hole):
    for name, value in hole["spreads"].items():
        assert value <= ADJACENT_SPREAD_BAND, (
            f"hole class '{name}' spread {value * 100:.4f}% > "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}% at {hole['f_hz']:.3e} Hz"
        )


@complex_only
def test_the_hole_power_identity(hole):
    dev = abs(hole["p_in"] - hole["p_phantom"]) / abs(hole["p_phantom"])
    assert dev <= POWER_IDENTITY_BAND, (
        f"Re P_in {hole['p_in']:.9e} W vs phantom loss {hole['p_phantom']:.9e} W: "
        f"rel dev {dev:.3e} > {POWER_IDENTITY_BAND:.0e} at {hole['f_hz']:.3e} Hz"
    )


@complex_only
def test_step3c_hole_discrete_identity_with_non_phantom_term(hole):
    """(a) on the hole: exact by construction; no loss outside the phantom."""
    a = hole["attr"]
    assert _attribution_residual(a) <= DISCRETE_IDENTITY_RTOL, (
        f"hole: P_src {a['p_src']:.9e} - sheets {a['p_sheets_total']:.9e} - phantom "
        f"{a['p_phantom']:.9e} - non-phantom {a['p_non_phantom']:.9e}: rel "
        f"{_attribution_residual(a):.3e} > {DISCRETE_IDENTITY_RTOL:g}"
    )
    assert abs(a["p_non_phantom"]) <= HOLE_NON_PHANTOM_LOSS_MAX_W, (
        f"hole P_(Omega\\phantom) = {a['p_non_phantom']:.3e} W > "
        f"{HOLE_NON_PHANTOM_LOSS_MAX_W:.0e} W on a conductor-free mesh"
    )


@complex_only
def test_step3c_solid_discrete_identity_with_non_phantom_term(solid):
    """(a) on the solid: the non-phantom term is the conductor loss."""
    a = solid["attr"]
    assert _attribution_residual(a) <= DISCRETE_IDENTITY_RTOL, (
        f"solid: rel {_attribution_residual(a):.3e} > {DISCRETE_IDENTITY_RTOL:g}"
    )


@complex_only
def test_step3c_solid_c_over_terminal_reproduces_the_2d_record(solid):
    """(b) the control: the solid's P1 pooled C/terminal − 1 is `PORT-14` 2d's."""
    pooled = solid["attr"]["deficit"]["pooled"]
    rel = abs(pooled / SOLID_P1_C_OVER_TERMINAL_10MHZ - 1.0)
    if MPI.COMM_WORLD.rank == 0:
        print(f"[TH-15 step3c] solid P1 C/terminal - 1 = {pooled:.9e} vs record "
              f"{SOLID_P1_C_OVER_TERMINAL_10MHZ:.9e}: rel {rel:.3e} "
              f"(ASSERTED rtol {SOLID_C_OVER_TERMINAL_RTOL:g})", flush=True)
    assert rel <= SOLID_C_OVER_TERMINAL_RTOL


@complex_only
def test_step3c_hole_beside_solid_is_printed(hole, solid):
    """Printed only: the hole's readout systematic beside the solid's."""
    h, s = hole["attr"], solid["attr"]
    if MPI.COMM_WORLD.rank == 0:
        ratio = h["deficit"]["pooled"] / s["deficit"]["pooled"]
        print(
            f"[TH-15 step3c] P1 C/terminal - 1: hole {h['deficit']['pooled']:.9e} "
            f"(f = {hole['f_hz']:.3e} Hz)  solid {s['deficit']['pooled']:.9e} (10 MHz); "
            f"hole/solid {ratio:.4f} (PRINTED; filing threshold "
            f"{PREDICTED_FILING_RATIO:g}x predicted, {'above' if ratio > PREDICTED_FILING_RATIO else 'not above'})",
            flush=True,
        )


@complex_only
def test_the_solid_route_reproduces_port11_10mhz_record(solid):
    """Negative control: `PORT-11`'s own rung reproduces its 10 MHz 4x4 record."""
    comm = MPI.COMM_WORLD
    rung = solid
    s = np.asarray(rung["s"], dtype=np.complex128)
    dev = np.abs(s - LEG_D_S_MATRIX_10MHZ) / np.abs(LEG_D_S_MATRIX_10MHZ)
    if comm.rank == 0:
        print(f"[TH-15 step3] solid control 10 MHz: {rung['cells']} cells, sweep "
              f"{rung['sweep_time']:.1f} s, max rel |dS| vs record {float(np.max(dev)):.3e} "
              f"(band {FREQUENCY_CONTROL_BAND:.0e})", flush=True)
    assert float(np.max(dev)) < FREQUENCY_CONTROL_BAND
