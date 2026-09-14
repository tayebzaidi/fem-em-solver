"""`TH-14` step 2 — the copper F-small birdcage as a surface-impedance hole.

The fixture is `TH-15` step 3's hole (``tests/mesh/test_birdcage_port_sheets.
_build(True, as_hole=True)``, four lumped-sheet ports, phantom present) with the
cavity wall's Dirichlet pin replaced by Jin §5.8.3's third-kind term

    a_s(E, W) = jωμ₀ (1/Z_s) ∫_Γc (n × E)·conj(n × W) dS,
    Z_s = (1 + j) R_s,  R_s = √(ωμ₀/(2σ))       (Jin §1.5.3 (1.54)–(1.56))

through `PORT-9`'s ``extra_bilinear_terms`` hook, forwarded by the additive
``run_n_port_sparameter_sweep(extra_bilinear_terms=)`` keyword this step adds.

**The outer box stays pinned without a mesh change.**  ``birdcage_port_domain``
tags no outer-box facet group and ``pec_facet_tags=None`` pins every exterior
facet (tag 401 included).  Instead of adding a tag to ``io/mesh.py`` this module
builds a *separate* facet ``MeshTags`` holding one group, ``OUTER_BOX_TAG``, =
exterior facets ∖ tag-401 facets (rank-local set difference on local indices,
counts asserted after reduction), and hands it to the problem as
``facet_tags`` with ``pec_facet_tags=(OUTER_BOX_TAG,)``.  The mesh itself is
untouched, so `GEO-18`'s / step 3a's mesh identity records cannot move.  The
N1curl DOFs on tag 401 are then free (no ``_cavity_dofs`` pattern).

Anchors (asserted; bands imported, never restated):
(a) copper (σ = 5.8e7 S/m) at 10 / 64 / 128 MHz: ``RECIPROCITY_BAND``,
    ``σ_max ≤ 1 + PASSIVITY_SIGMA_TOLERANCE``, class spreads ≤
    ``ADJACENT_SPREAD_BAND``;
(b) P1 drive, copper: ``P_src − ΣP_sheet = P_phantom + P_(Ω∖phantom) +
    ½∫_Γc Re(1/Z_s)|n × E|²`` at ``DISCRETE_IDENTITY_RTOL``;
(c) the bracket at 10 MHz, per C4 class, ``max|S_cu − S_PEC| ≤ max|S_800 −
    S_PEC|`` with ``S_PEC`` the `TH-15` step 3 hole 4×4 solved in-window
    (``pec_facet_tags=None``, the step-3 fixture verbatim) and ``S_800``
    `PORT-11`'s stored solid record ``LEG_D_S_MATRIX_10MHZ`` (the only stored
    σ = 800 4×4 on this fixture — no 64/128 MHz record exists, so the bracket's
    solid side is 10 MHz only, disclosed); and at all three frequencies the σ
    ladder {5.8e7, 5.8e9, 5.8e11} has per-class ``max|S_σ − S_PEC|`` strictly
    decreasing.
*Predicted, printed only:* σ = 5.8e11 reproduces the PEC 4×4 to ≤ 1e-4 per
entry.  Printed: ``P_coil/P_in`` per frequency (the σ = 800 solid's share is
`TH-15` step 3c's solid-control attribution, 10 MHz, not recomputed here).

``TH14_STEP2_FREQS_MHZ`` (comma list, default ``10,64,128``) selects the
frequencies; the mesh and ports are built once.
"""

from __future__ import annotations

import os
import time

import dolfinx
import numpy as np
import pytest
import ufl
from dolfinx import default_scalar_type, fem
from mpi4py import MPI

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.core.cavity import surface_resistance_ohm
from fem_em_solver.io.mesh import BIRDCAGE_CONDUCTOR_SURFACE_TAG
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.lumped import LumpedSheetPortSpec, run_lumped_sheet_port_case
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep
from fem_em_solver.utils.constants import MU_0

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
from tests.validation.test_port_birdcage_larmor_gate import LEG_D_S_MATRIX_10MHZ
from tests.validation.test_port_birdcage_leg_offset_sweep import (
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

FREQS_ENV = "TH14_STEP2_FREQS_MHZ"
FREQUENCIES_HZ = {"10": FREQUENCY_HZ, "64": FREQUENCY_64_HZ, "128": 128.0e6}
DRIVEN = "P1"
COPPER_SIGMA = 5.8e7
# §9 item 6 (2026-09-13): the σ ladder, copper first.
SIGMA_LADDER = (5.8e7, 5.8e9, 5.8e11)
# A facet tag for the in-module outer-box group; asserted absent from the mesh's
# own facet tags before use.
OUTER_BOX_TAG = 499
# *Predicted, printed only* (§9 item 6 negative control).
PREDICTED_PEC_LIMIT_MAX_ABS_DS = 1.0e-4
CLASSES = ("self", "adjacent", "opposite")


def _selected_keys():
    raw = os.environ.get(FREQS_ENV, "10,64,128")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    bad = [k for k in keys if k not in FREQUENCIES_HZ]
    if bad or not keys:
        raise RuntimeError(f"{FREQS_ENV} entries must be in {sorted(FREQUENCIES_HZ)}; got {raw!r}")
    return keys


def _class_max_abs(ds):
    return {name: float(np.max(np.abs(v))) for name, v in _circulant_classes(ds).items()}


def _outer_box_tags(msh, facet_tags, comm):
    """Exterior facets minus tag 401, as their own MeshTags; reduced census."""
    fdim = msh.topology.dim - 1
    msh.topology.create_connectivity(fdim, msh.topology.dim)
    n_owned = msh.topology.index_map(fdim).size_local
    exterior = np.asarray(dolfinx.mesh.exterior_facet_indices(msh.topology), dtype=np.int32)
    cavity = np.asarray(facet_tags.find(BIRDCAGE_CONDUCTOR_SURFACE_TAG), dtype=np.int32)
    outer = np.setdiff1d(exterior, cavity).astype(np.int32)
    tags = dolfinx.mesh.meshtags(
        msh, fdim, outer, np.full(outer.size, OUTER_BOX_TAG, dtype=np.int32)
    )

    def _owned(a):
        return comm.allreduce(int(np.count_nonzero(a < n_owned)), op=MPI.SUM)

    census = {
        "exterior": _owned(exterior),
        "cavity": _owned(cavity),
        "cavity_exterior": _owned(np.intersect1d(cavity, exterior)),
        "outer": _owned(outer),
        "tag_collision": comm.allreduce(
            int(np.count_nonzero(np.asarray(facet_tags.values) == OUTER_BOX_TAG)), op=MPI.SUM
        ),
    }
    return tags, census


def _leontovich_term(msh, facet_tags, z_s, omega):
    """Jin §5.8.3's third-kind term on tag 401 — SpatialCoordinate-free."""
    ds_c = ufl.Measure(
        "ds", domain=msh, subdomain_data=facet_tags, subdomain_id=BIRDCAGE_CONDUCTOR_SURFACE_TAG
    )
    n = ufl.FacetNormal(msh)
    gamma = fem.Constant(msh, default_scalar_type(1j * omega * MU_0 / complex(z_s)))

    def term(trial, test):
        return gamma * ufl.inner(ufl.cross(n, trial), ufl.cross(n, test)) * ds_c

    return term


def _surface_loss_w(msh, facet_tags, z_s, e, comm):
    """½∫_Γc Re(1/Z_s)|n × E|² dS, reduced."""
    ds_c = ufl.Measure(
        "ds", domain=msh, subdomain_data=facet_tags, subdomain_id=BIRDCAGE_CONDUCTOR_SURFACE_TAG
    )
    n = ufl.FacetNormal(msh)
    re_y = fem.Constant(msh, default_scalar_type(0.5 * np.real(1.0 / complex(z_s))))
    form = fem.form(re_y * ufl.inner(ufl.cross(n, e), ufl.cross(n, e)) * ds_c)
    return float(np.real(comm.allreduce(fem.assemble_scalar(form), op=MPI.SUM)))


def _build_ports(msh, cell_tags, comm):
    """`TH-15` step 3's `_hole_rung` port construction, verbatim."""
    ports_idx = list(range(1, LEG_COUNT + 1))
    tags_f, _full = _sheet_areas(msh, cell_tags, ports_idx, comm)
    geometry = {}
    for i in ports_idx:
        tag = SHEET_IFACE + i
        azimuth = _sheet_azimuth_deg(msh, tags_f, tag, comm)
        radial, azimuthal, axial = _port_frame(azimuth)
        spans, centres = _projected_extents(msh, tags_f, tag, comm, [radial, azimuthal, axial])
        geometry[i] = {"tag": tag, "azimuth_deg": float(azimuth), "radial": radial,
                       "w_full": float(spans[0]), "centre_radial": float(centres[0])}
    for i in ports_idx:
        g = geometry[i]
        tags_f = _narrowed_radial(msh, tags_f, g["tag"], GATED_WIDTH_FRACTION,
                                  g["centre_radial"], g["radial"], 0.5 * g["w_full"])
    port_defs, specs = [], []
    for i in ports_idx:
        g = geometry[i]
        assert _sheet_facet_count(msh, tags_f, g["tag"], comm) > 0
        area = _facet_group_area(msh, tags_f, g["tag"], comm)
        radial, azimuthal, axial = _port_frame(g["azimuth_deg"])
        spans, _c = _projected_extents(msh, tags_f, g["tag"], comm, [radial, azimuthal, axial])
        pid = f"P{i}"
        port_defs.append(PortDefinition(
            port_id=pid, positive_tag=int(g["tag"]), negative_tag=CONDUCTOR_CELL_TAG,
            orientation="leg_gap_axial_plus_z", z0_ohm=REFERENCE_IMPEDANCE_OHM,
        ))
        specs.append(LumpedSheetPortSpec(
            port_id=pid, facet_tag=int(g["tag"]),
            port_impedance_ohm=TERMINATED_PORT_IMPEDANCE_OHM, gap_height_m=float(spans[2]),
            sheet_width_m=float(area / spans[2]), drive_direction=(0.0, 0.0, 1.0),
            drive_voltage_v=1.0 + 0.0j, interior=True,
        ))
    return tags_f, port_defs, specs


def _problem(msh, cell_tags, f_hz, facet_tags, pec_facet_tags):
    return TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=f_hz,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            PHANTOM_CELL_TAG: HomogeneousMaterial(
                sigma=SALINE_SIGMA, epsilon_r=SALINE_EPSILON_R, mu_r=1.0
            ),
        },
        boundary_condition="pec_zero_tangential_a",
        facet_tags=facet_tags,
        pec_facet_tags=pec_facet_tags,
    )


def _sweep_record(result):
    z = np.asarray(result.z_matrix, dtype=np.complex128)
    s = np.asarray(result.s_matrix, dtype=np.complex128)
    return {
        "z": z,
        "s": s,
        "spreads": {n: _class_spread(v) for n, v in _circulant_classes(z).items()},
        "sigma": np.linalg.svd(s, compute_uv=False),
        "reciprocity": float(np.linalg.norm(s - s.T) / np.linalg.norm(s)),
    }


@pytest.fixture(scope="module")
def ladder():
    comm = MPI.COMM_WORLD
    t0 = time.perf_counter()
    msh, cell_tags, facet_tags, _diag, t_mesh = _sheets_build(True, as_hole=True)
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()
    ncells = int(msh.topology.index_map(tdim).size_global)
    outer_tags, census = _outer_box_tags(msh, facet_tags, comm)
    tags_f, port_defs, specs = _build_ports(msh, cell_tags, comm)
    out = {"cells": ncells, "census": census, "freqs": {}}
    if comm.rank == 0:
        print(f"\n[TH-14 step2] hole mesh {ncells} cells, mesh {t_mesh:.1f} s, -n {comm.size}; "
              f"census {census}", flush=True)

    for key in _selected_keys():
        f_hz = FREQUENCIES_HZ[key]
        omega = 2.0 * np.pi * f_hz
        rec = {"f_hz": f_hz, "sigma": {}}
        # PEC reference: `TH-15` step 3's fixture verbatim (every exterior facet pinned).
        t1 = time.perf_counter()
        pec_problem = _problem(msh, cell_tags, f_hz, facet_tags, None)
        rec["pec"] = _sweep_record(run_n_port_sparameter_sweep(
            pec_problem, port_defs, lumped_sheet_ports=specs, lumped_sheet_facet_tags=tags_f))
        comm.Barrier()
        rec["t_pec"] = time.perf_counter() - t1
        imp_problem = _problem(msh, cell_tags, f_hz, outer_tags, (OUTER_BOX_TAG,))
        for sig in SIGMA_LADDER:
            r_s = surface_resistance_ohm(omega, sig)
            z_s = (1.0 + 1.0j) * r_s
            t1 = time.perf_counter()
            term = _leontovich_term(msh, facet_tags, z_s, omega)
            sw = _sweep_record(run_n_port_sparameter_sweep(
                imp_problem, port_defs, lumped_sheet_ports=specs, lumped_sheet_facet_tags=tags_f,
                extra_bilinear_terms=[term]))
            comm.Barrier()
            sw["t"] = time.perf_counter() - t1
            sw["z_s"] = z_s
            ds = sw["s"] - rec["pec"]["s"]
            sw["max_abs_ds"] = float(np.max(np.abs(ds)))
            sw["class_ds"] = _class_max_abs(ds)
            rec["sigma"][sig] = sw
        # (b) the P1 field solve on copper.
        z_cu = rec["sigma"][COPPER_SIGMA]["z_s"]
        term_cu = _leontovich_term(msh, facet_tags, z_cu, omega)
        t1 = time.perf_counter()
        p1, fields = run_lumped_sheet_port_case(
            imp_problem, port_defs, specs, facet_tags=tags_f, driven_port_id=DRIVEN,
            verbose=False, return_fields=True, extra_bilinear_terms=[term_cu])
        comm.Barrier()
        rec["t_p1"] = time.perf_counter() - t1
        e = fields.e_complex
        sigma_f = fields.sigma_field
        dx = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)

        def _vol(measure):
            form = fem.form(0.5 * sigma_f * ufl.inner(e, e) * measure)
            return float(np.real(comm.allreduce(fem.assemble_scalar(form), op=MPI.SUM)))

        acct = {"mesh": msh, "facet_tags": tags_f}
        sheet_objs = {sp.port_id: sp.sheet(driven=(sp.port_id == DRIVEN)) for sp in specs}
        p_sheets = sum(_sheet_field_dissipation_w(acct, sh, e, omega) for sh in sheet_objs.values())
        p_src = float(_source_power_w(acct, sheet_objs[DRIVEN], e, omega))
        p_total = _vol(dx)
        p_phantom = _vol(dx(PHANTOM_CELL_TAG))
        p_surf = _surface_loss_w(msh, facet_tags, z_cu, e, comm)
        rec["power"] = {
            "p_src": p_src, "p_sheets": float(p_sheets), "p_phantom": p_phantom,
            "p_non_phantom": float(p_total - p_phantom), "p_surf": p_surf,
        }
        p = rec["power"]
        rec["identity_residual"] = abs(
            p["p_src"] - p["p_sheets"] - p["p_phantom"] - p["p_non_phantom"] - p["p_surf"]
        ) / abs(p["p_src"])
        p_in = p["p_src"] - p["p_sheets"]
        if comm.rank == 0:
            print(f"\n[TH-14 step2] f = {f_hz:.6e} Hz: PEC sweep {rec['t_pec']:.1f} s, "
                  f"P1 copper field solve {rec['t_p1']:.1f} s", flush=True)
            pec = rec["pec"]
            for row in range(LEG_COUNT):
                print("    S_PEC_%dk = " % (row + 1)
                      + "  ".join(f"{v:+.9e}" for v in pec["s"][row]), flush=True)
            for sig, sw in rec["sigma"].items():
                sp = sw["spreads"]
                print(f"  sigma = {sig:.1e} S/m: Z_s = {sw['z_s'].real:.6e}(1+j) ohm, sweep "
                      f"{sw['t']:.1f} s", flush=True)
                for row in range(LEG_COUNT):
                    print("    S_%dk = " % (row + 1)
                          + "  ".join(f"{v:+.9e}" for v in sw["s"][row]), flush=True)
                print(f"    ||S-S^T||/||S|| = {sw['reciprocity']:.9e} (band {RECIPROCITY_BAND:.0e}); "
                      f"sigma_max(S) = {float(np.max(sw['sigma'])):.12f}; spreads self "
                      f"{sp['self'] * 100:.4f}% adjacent {sp['adjacent'] * 100:.4f}% opposite "
                      f"{sp['opposite'] * 100:.4f}% (band {ADJACENT_SPREAD_BAND * 100:.1f}%)",
                      flush=True)
                print("    max|S_sigma - S_PEC| per class: " + ", ".join(
                    f"{c} {sw['class_ds'][c]:.9e}" for c in CLASSES)
                    + f"; max entry {sw['max_abs_ds']:.9e}", flush=True)
            last = rec["sigma"][SIGMA_LADDER[-1]]["max_abs_ds"]
            print(f"    negative control (PREDICTED, printed): sigma = {SIGMA_LADDER[-1]:.1e} "
                  f"max|S - S_PEC| = {last:.3e} vs predicted <= {PREDICTED_PEC_LIMIT_MAX_ABS_DS:.0e}: "
                  f"{'met' if last <= PREDICTED_PEC_LIMIT_MAX_ABS_DS else 'NOT met'}", flush=True)
            print(f"    (b) P1 copper: P_src {p['p_src']:.9e} W, sum P_sheet {p['p_sheets']:.9e} W, "
                  f"P_phantom {p['p_phantom']:.9e} W, P_(Omega\\phantom) {p['p_non_phantom']:.9e} W, "
                  f"P_surf {p['p_surf']:.9e} W; residual/P_src {rec['identity_residual']:.3e} "
                  f"(ASSERTED <= {DISCRETE_IDENTITY_RTOL:g})", flush=True)
            print(f"    PRINTED: P_coil/P_in = {p['p_surf'] / p_in:.6e}, "
                  f"P_phantom/P_in = {p['p_phantom'] / p_in:.6e} (copper, f = {f_hz:.3e} Hz)",
                  flush=True)
        out["freqs"][key] = rec

    out["t_total"] = time.perf_counter() - t0
    if comm.rank == 0:
        print(f"[TH-14 step2] total {out['t_total']:.1f} s at -n {comm.size}", flush=True)
    return out


@complex_only
def test_outer_box_group_is_exterior_minus_cavity(ladder):
    c = ladder["census"]
    assert c["tag_collision"] == 0, f"OUTER_BOX_TAG {OUTER_BOX_TAG} already used by the mesh"
    assert c["cavity"] > 0 and c["cavity_exterior"] == c["cavity"], c
    assert c["outer"] > 0 and c["outer"] + c["cavity"] == c["exterior"], c


@complex_only
@pytest.mark.parametrize("key", ["10", "64", "128"])
def test_copper_birdcage_port_gates(ladder, key):
    """(a) reciprocity, passivity and C4 class spreads, copper."""
    if key not in ladder["freqs"]:
        pytest.skip(f"{key} MHz not selected by {FREQS_ENV}")
    sw = ladder["freqs"][key]["sigma"][COPPER_SIGMA]
    assert sw["reciprocity"] <= RECIPROCITY_BAND, sw["reciprocity"]
    assert float(np.max(sw["sigma"])) <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, sw["sigma"]
    for name, value in sw["spreads"].items():
        assert value <= ADJACENT_SPREAD_BAND, (name, value)


@complex_only
@pytest.mark.parametrize("key", ["10", "64", "128"])
def test_copper_surface_loss_identity(ladder, key):
    """(b) P_src − ΣP_sheet = P_phantom + P_(Ω∖phantom) + ½∫Re(1/Z_s)|n×E|²."""
    if key not in ladder["freqs"]:
        pytest.skip(f"{key} MHz not selected by {FREQS_ENV}")
    rec = ladder["freqs"][key]
    assert rec["power"]["p_surf"] > 0.0, rec["power"]
    assert rec["identity_residual"] <= DISCRETE_IDENTITY_RTOL, rec["identity_residual"]


@complex_only
def test_copper_is_bracketed_by_pec_and_the_solid_record_at_10mhz(ladder):
    """(c) per class max|S_cu − S_PEC| ≤ max|S_800 − S_PEC|, 10 MHz."""
    if "10" not in ladder["freqs"]:
        pytest.skip(f"10 MHz not selected by {FREQS_ENV}")
    rec = ladder["freqs"]["10"]
    solid = _class_max_abs(np.asarray(LEG_D_S_MATRIX_10MHZ, dtype=np.complex128) - rec["pec"]["s"])
    cu = rec["sigma"][COPPER_SIGMA]["class_ds"]
    if MPI.COMM_WORLD.rank == 0:
        print("[TH-14 step2] (c) 10 MHz per class max|dS|: " + "; ".join(
            f"{c}: copper {cu[c]:.9e} vs solid-800 record {solid[c]:.9e}" for c in CLASSES),
            flush=True)
    for c in CLASSES:
        assert cu[c] <= solid[c], (c, cu[c], solid[c])


@complex_only
@pytest.mark.parametrize("key", ["10", "64", "128"])
def test_sigma_ladder_approaches_pec_monotonically(ladder, key):
    """(c) per class max|S_σ − S_PEC| strictly decreasing along the σ ladder."""
    if key not in ladder["freqs"]:
        pytest.skip(f"{key} MHz not selected by {FREQS_ENV}")
    rungs = ladder["freqs"][key]["sigma"]
    for c in CLASSES:
        seq = [rungs[sig]["class_ds"][c] for sig in SIGMA_LADDER]
        assert all(b < a for a, b in zip(seq, seq[1:])), (c, seq)
