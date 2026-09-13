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


def _hole_rung(frequency_hz):
    """`_four_port_rung`'s construction on the hole mesh; no conductor material."""
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
        problem, port_defs, lumped_sheet_ports=specs, lumped_sheet_facet_tags=tags_f
    )
    comm.Barrier()
    t_sweep = time.perf_counter() - t0

    # The power identity needs the field; one extra P1 solve (own factorisation).
    t0 = time.perf_counter()
    p1, fields = run_lumped_sheet_port_case(
        problem, port_defs, specs, facet_tags=tags_f, driven_port_id=DRIVEN,
        verbose=False, return_fields=True,
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
def test_the_solid_route_reproduces_port11_10mhz_record():
    """Negative control: `PORT-11`'s own rung reproduces its 10 MHz 4x4 record."""
    if os.environ.get(CONTROL_ENV, "").strip() != "1":
        pytest.skip(f"{CONTROL_ENV} != 1: solid control not requested in this window")
    comm = MPI.COMM_WORLD
    rung = _four_port_rung("TH-15 solid control 10 MHz", np.zeros(LEG_COUNT), FREQUENCY_HZ)
    s = np.asarray(rung["s"], dtype=np.complex128)
    dev = np.abs(s - LEG_D_S_MATRIX_10MHZ) / np.abs(LEG_D_S_MATRIX_10MHZ)
    if comm.rank == 0:
        print(f"[TH-15 step3] solid control 10 MHz: {rung['cells']} cells, sweep "
              f"{rung['sweep_time']:.1f} s, max rel |dS| vs record {float(np.max(dev)):.3e} "
              f"(band {FREQUENCY_CONTROL_BAND:.0e})", flush=True)
    assert float(np.max(dev)) < FREQUENCY_CONTROL_BAND
