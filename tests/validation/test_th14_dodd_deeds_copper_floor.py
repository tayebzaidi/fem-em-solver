"""`TH-14` step 2 (§9 2026-09-14) — copper Dodd–Deeds slab as a Leontovich floor.

`MAT-6`'s loop fixture (``test_dodd_deeds_impedance``: loop radius 0.04 m,
liftoff 0.020 m, wire 2.5 mm, 10 MHz, 1 A, box half-width 0.15 m,
``project_source=False``) with the **slab volume removed**.  Removal goes
through ``dolfinx.mesh.create_submesh`` on MAT-6's own mesh (wire + air cells,
i.e. every cell not tagged ``SLAB_TAG``) instead of a new mesher option.
``MeshGenerator.loop_over_half_space_domain`` has no air-only switch, and the
§9 item forbids adding one.  The submesh shares every wire and air cell with
the parent, so the parent's meshed loop current applies unchanged (asserted
below).  On the submesh ``z = 0`` is a true **domain boundary** Γ_c:

    a_s(E, W) = jωμ₀ (1/Z_s) ∫_Γc (n × E)·conj(n × W) dS,
    Z_s = (1 + j) R_s,  R_s = √(ωμ₀/(2σ))       (Jin §1.5.3 (1.54)–(1.56), §5.8.3)

(`TH-14` birdcage step's ``_leontovich_term`` / ``_surface_loss_w``, imported;
both integrate facet tag 401 = ``BIRDCAGE_CONDUCTOR_SURFACE_TAG``, which is the
floor tag here).  The other five box faces are tag 499, pinned PEC through
``pec_facet_tags=(499,)``.  The PEC control is the same box with every exterior
facet pinned (``pec_facet_tags=None``).

ΔZ(σ) = Z(σ) − Z_PEC by `MAT-6`'s ``_reaction_impedance`` on the submesh.
Since R_PEC = 0, Re ΔZ(σ) is ΔR(σ) and Im ΔZ(σ) is ΔX(σ) − ΔX_PEC.

Asserted:
(a) ΔR(5.8e7) against ``coil_impedance_change`` (what
    ``test_fem_resistance_change_matches_dodd_deeds`` calls) within 2 %;
(b) Re ΔZ·½|I|² = ½∫_401 Re(1/Z_s)|n × E|² at ``DISCRETE_IDENTITY_RTOL``;
(c) ΔR(5.8e7)/ΔR(5.8e9) = 10 within 1 %;
(d) (ΔX(σ) − ΔX_PEC)/ΔR(σ) = 1 within 2 %, copper;
negative control: the PEC-floor control's |ΔR| ≤ 1e-6·|ΔX|.  Here the control's
ΔZ is Z_PEC(submesh) − Z_free(parent).  Z_free is MAT-6's own untagged σ = 0
solve (``_solve_loop(..., tag_the_slab=False)``) on the full box, and the two
self-impedances are taken as separate reaction scalars because the meshes
differ.  Census: floor ∩ others = ∅ and floor + others = exterior, rank-reduced,
plus the floor area against 4W².
Printed only: ΔX(copper) beside ``image_limit_inductance_change``·ω; δ beside
the near-loop h.
"""

from __future__ import annotations

import time

import dolfinx
import numpy as np
import pytest
import ufl
from dolfinx import default_scalar_type, fem
from mpi4py import MPI

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem, TimeHarmonicSolver
from fem_em_solver.core.cavity import surface_resistance_ohm
from fem_em_solver.io.mesh import BIRDCAGE_CONDUCTOR_SURFACE_TAG, MeshGenerator
from fem_em_solver.utils.dodd_deeds import (
    coil_impedance_change,
    image_limit_inductance_change,
    skin_depth,
)

from tests.complex_mode import complex_only
from tests.validation.test_birdcage_power_identity import DISCRETE_IDENTITY_RTOL
from tests.validation.test_dodd_deeds_impedance import (
    FEM_BOX_HALF_WIDTH,
    FEM_CURRENT_A,
    FEM_FREQUENCY_HZ,
    FEM_LIFTOFF,
    FEM_LOOP_RADIUS,
    FEM_RESOLUTION_NEAR,
    FEM_WIRE_RADIUS,
    SLAB_TAG,
    WIRE_TAG,
    _azimuthal_current_density,
    _reaction_impedance,
    _solve_loop,
)
from tests.validation.test_th14_birdcage_copper import _leontovich_term, _surface_loss_w

FLOOR_TAG = BIRDCAGE_CONDUCTOR_SURFACE_TAG  # 401, the tag the imported term integrates
OTHER_FACES_TAG = 499
COPPER_SIGMA = 5.8e7
SCALING_SIGMA = 5.8e9
# Pre-registered bands (§9 2026-09-14 item 2).
DODD_DEEDS_BAND = 0.02  # (a)
SCALING_BAND = 0.01  # (c)
THIN_SKIN_BAND = 0.02  # (d)
PEC_CONTROL_BOUND = 1.0e-6  # negative control, asserted
FLOOR_AREA_RTOL = 1.0e-9


def _say(msg):
    if MPI.COMM_WORLD.rank == 0:
        print(msg, flush=True)


def _air_submesh(msh, cell_tags):
    """Wire + air cells of MAT-6's mesh as their own mesh, cell tags carried over."""
    tdim = msh.topology.dim
    imap = msh.topology.index_map(tdim)
    n_parent = imap.size_local + imap.num_ghosts
    parent_values = np.full(n_parent, -1, dtype=np.int32)
    parent_values[cell_tags.indices] = cell_tags.values
    keep = np.flatnonzero((parent_values != SLAB_TAG) & (parent_values >= 0)).astype(np.int32)
    sub, emap, _vmap, _gmap = dolfinx.mesh.create_submesh(msh, tdim, keep)
    simap = sub.topology.index_map(tdim)
    n_sub = simap.size_local + simap.num_ghosts
    parent_ids = np.asarray(
        emap.sub_topology_to_topology(np.arange(n_sub, dtype=np.int32), False), dtype=np.int64
    )
    sub_tags = dolfinx.mesh.meshtags(
        sub, tdim, np.arange(n_sub, dtype=np.int32), parent_values[parent_ids].astype(np.int32)
    )
    return sub, sub_tags


def _floor_facet_tags(sub, comm):
    """Floor (z ≈ 0) 401, the other exterior facets 499; reduced census."""
    tdim = sub.topology.dim
    fdim = tdim - 1
    sub.topology.create_connectivity(fdim, tdim)
    n_owned = sub.topology.index_map(fdim).size_local
    exterior = np.asarray(dolfinx.mesh.exterior_facet_indices(sub.topology), dtype=np.int32)
    floor = np.asarray(
        dolfinx.mesh.locate_entities_boundary(sub, fdim, lambda x: np.isclose(x[2], 0.0, atol=1e-8)),
        dtype=np.int32,
    )
    others = np.setdiff1d(exterior, floor).astype(np.int32)
    indices = np.concatenate([floor, others])
    values = np.concatenate([
        np.full(floor.size, FLOOR_TAG, dtype=np.int32),
        np.full(others.size, OTHER_FACES_TAG, dtype=np.int32),
    ])
    order = np.argsort(indices)
    tags = dolfinx.mesh.meshtags(sub, fdim, indices[order], values[order])

    def _owned(a):
        return comm.allreduce(int(np.count_nonzero(a < n_owned)), op=MPI.SUM)

    census = {
        "exterior": _owned(exterior),
        "floor": _owned(floor),
        "floor_in_exterior": _owned(np.intersect1d(floor, exterior)),
        "others": _owned(others),
        "overlap": _owned(np.intersect1d(floor, others)),
    }
    return tags, census


def _solve_air(sub, sub_tags, ftags, comm, *, z_s=None):
    """One solve on the air-only box: PEC floor (z_s None) or Leontovich floor."""
    omega = 2.0 * np.pi * FEM_FREQUENCY_HZ
    problem = TimeHarmonicProblem(
        mesh=sub,
        frequency_hz=FEM_FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=sub_tags,
        material_map=None,
        boundary_condition="pec_zero_tangential_a",
        facet_tags=ftags,
        pec_facet_tags=None if z_s is None else (OTHER_FACES_TAG,),
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    terms = None if z_s is None else [_leontovich_term(sub, ftags, z_s, omega)]
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=_azimuthal_current_density(j_magnitude),
        subdomain_ids=[WIRE_TAG],
        project_source=False,
        extra_bilinear_terms=terms,
    )
    comm.Barrier()
    return fields.e_complex, time.perf_counter() - t0


def _wire_volume(msh, cell_tags, comm):
    dx_wire = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,))
    one = fem.Constant(msh, default_scalar_type(1.0))
    return float(np.real(comm.allreduce(fem.assemble_scalar(fem.form(one * dx_wire)), op=MPI.SUM)))


def _self_impedance(msh, cell_tags, e, current, comm):
    """Z = −(1/I²)∫_wire E·J — `_reaction_impedance` against a zero field."""
    zero = fem.Function(e.function_space)
    zero.x.array[:] = 0.0
    return _reaction_impedance(msh, cell_tags, e, zero, current, comm)


@pytest.fixture(scope="module")
def floor():
    comm = MPI.COMM_WORLD
    t_start = time.perf_counter()
    omega = 2.0 * np.pi * FEM_FREQUENCY_HZ
    # MAT-6 fixture's mesher call, verbatim (its literal keyword values restated).
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=0.002,
        resolution_near=FEM_RESOLUTION_NEAR,
        resolution_far=0.025,
        near_half_width=0.06,
        near_depth=0.05,
        near_height=0.03,
        comm=comm,
    )
    tdim = msh.topology.dim
    t_mesh = time.perf_counter() - t_start
    n_parent = msh.topology.index_map(tdim).size_global

    v_wire = _wire_volume(msh, cell_tags, comm)
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)
    current = j_magnitude * v_wire / (2.0 * np.pi * FEM_LOOP_RADIUS)

    sub, sub_tags = _air_submesh(msh, cell_tags)
    sub.topology.create_connectivity(tdim - 1, tdim)
    sub.topology.create_entity_permutations()
    n_sub = sub.topology.index_map(tdim).size_global
    v_wire_sub = _wire_volume(sub, sub_tags, comm)
    ftags, census = _floor_facet_tags(sub, comm)
    ds_floor = ufl.Measure("ds", domain=sub, subdomain_data=ftags, subdomain_id=FLOOR_TAG)
    floor_area = float(np.real(comm.allreduce(
        fem.assemble_scalar(fem.form(fem.Constant(sub, default_scalar_type(1.0)) * ds_floor)),
        op=MPI.SUM)))
    _say(
        f"\n[TH-14 step2 floor] parent {n_parent} cells, air-only submesh {n_sub} cells "
        f"(mesh {t_mesh:.1f} s, -n {comm.size}); meshed loop current {current:.9f} A; "
        f"wire volume parent {v_wire:.12e} sub {v_wire_sub:.12e}"
        f"\n  census {census}; floor area {floor_area:.12e} m^2 vs 4W^2 = {4 * FEM_BOX_HALF_WIDTH**2:.12e}"
    )

    # Free reference: MAT-6's untagged σ = 0 solve on the full box (parent mesh).
    e_free, t_free = _solve_loop(msh, cell_tags, 0.0, comm, tag_the_slab=False)
    z_free = _self_impedance(msh, cell_tags, e_free, current, comm)
    _say(f"  free (parent, sigma=0 untagged) solve {t_free:.1f} s: Z_free = {z_free:+.12e} ohm")

    e_pec, t_pec = _solve_air(sub, sub_tags, ftags, comm)
    z_pec = _self_impedance(sub, sub_tags, e_pec, current, comm)
    dz_pec = z_pec - z_free
    _say(f"  PEC-floor control solve {t_pec:.1f} s: Z_PEC = {z_pec:+.12e} ohm; "
         f"dZ_PEC = Z_PEC - Z_free = {dz_pec.real:+.6e} + j({dz_pec.imag:+.6e}) ohm")

    out = {
        "census": census, "floor_area": floor_area, "v_wire": v_wire, "v_wire_sub": v_wire_sub,
        "current": current, "z_free": z_free, "z_pec": z_pec, "dz_pec": dz_pec, "sigma": {},
    }
    for sigma in (COPPER_SIGMA, SCALING_SIGMA):
        r_s = surface_resistance_ohm(omega, sigma)
        z_s = (1.0 + 1.0j) * r_s
        e_s, t_s = _solve_air(sub, sub_tags, ftags, comm, z_s=z_s)
        dz = _reaction_impedance(sub, sub_tags, e_s, e_pec, current, comm)
        z_abs = _self_impedance(sub, sub_tags, e_s, current, comm)
        p_surf = _surface_loss_w(sub, ftags, z_s, e_s, comm)
        p_reaction = dz.real * 0.5 * current**2
        identity = abs(p_reaction - p_surf) / abs(p_surf)
        dz_ref = coil_impedance_change(FEM_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, sigma)
        out["sigma"][sigma] = {
            "dz": dz, "z_abs": z_abs, "p_surf": p_surf, "p_reaction": p_reaction,
            "identity": identity, "dz_ref": dz_ref, "r_s": r_s, "t": t_s,
        }
        _say(
            f"  sigma = {sigma:.1e} S/m: R_s = {r_s:.9e} ohm, solve {t_s:.1f} s"
            f"\n    FEM   dZ = Z - Z_PEC = {dz.real:+.9e} + j({dz.imag:+.9e}) ohm"
            f"\n    Dodd-Deeds dZ (coil_impedance_change) = {dz_ref.real:+.9e} + j({dz_ref.imag:+.9e}) ohm"
            f"\n    dR/dR_DD - 1 = {dz.real / dz_ref.real - 1:+.4%} (ASSERTED for copper, band 2%)"
            f"\n    (dX - dX_PEC)/dR - 1 = {dz.imag / dz.real - 1:+.4%}; closed form "
            f"(dX_DD - w*dL_image)/dR_DD - 1 = "
            f"{(dz_ref.imag - omega * image_limit_inductance_change(FEM_LOOP_RADIUS, FEM_LIFTOFF)) / dz_ref.real - 1:+.4%}"
            f"\n    (b) Re dZ * |I|^2/2 = {p_reaction:.12e} W vs 1/2 int Re(1/Z_s)|n x E|^2 = {p_surf:.12e} W; "
            f"rel {identity:.3e} (band {DISCRETE_IDENTITY_RTOL:g}); Re Z(sigma) abs = {z_abs.real:+.9e} ohm"
        )

    cu = out["sigma"][COPPER_SIGMA]
    sc = out["sigma"][SCALING_SIGMA]
    out["scaling"] = cu["dz"].real / sc["dz"].real
    dx_image = omega * image_limit_inductance_change(FEM_LOOP_RADIUS, FEM_LIFTOFF)
    dx_cu_abs = dz_pec.imag + cu["dz"].imag
    delta = skin_depth(FEM_FREQUENCY_HZ, COPPER_SIGMA)
    _say(
        f"  (c) dR(5.8e7)/dR(5.8e9) = {out['scaling']:.9f} (expect 10, band 1%)"
        f"\n  negative control: |dR_PEC|/|dX_PEC| = {abs(dz_pec.real) / abs(dz_pec.imag):.3e} "
        f"(ASSERTED <= {PEC_CONTROL_BOUND:.0e})"
        f"\n  PRINTED: dX(copper) = dX_PEC + (dX - dX_PEC) = {dx_cu_abs:+.9e} ohm vs "
        f"w*dL_image = {dx_image:+.9e} ohm (ratio {dx_cu_abs / dx_image:.6f}; "
        f"dX_PEC/(w*dL_image) = {dz_pec.imag / dx_image:.6f}); Dodd-Deeds dX(copper) = {cu['dz_ref'].imag:+.9e} ohm"
        f"\n  PRINTED: delta(copper, 10 MHz) = {delta:.6e} m vs near-loop h = {FEM_RESOLUTION_NEAR:.4e} m "
        f"(delta/h = {delta / FEM_RESOLUTION_NEAR:.3e})"
        f"\n[TH-14 step2 floor] total {time.perf_counter() - t_start:.1f} s at -n {comm.size}"
    )
    return out


@complex_only
def test_floor_and_other_faces_are_disjoint_and_complete(floor):
    c = floor["census"]
    assert c["floor"] > 0 and c["others"] > 0, c
    assert c["overlap"] == 0 and c["floor_in_exterior"] == c["floor"], c
    assert c["floor"] + c["others"] == c["exterior"], c
    assert abs(floor["floor_area"] / (4.0 * FEM_BOX_HALF_WIDTH**2) - 1.0) <= FLOOR_AREA_RTOL, floor["floor_area"]
    # The submesh keeps every wire cell, so MAT-6's meshed current applies to it.
    assert abs(floor["v_wire_sub"] / floor["v_wire"] - 1.0) <= 1.0e-10


@complex_only
def test_copper_floor_resistance_matches_dodd_deeds(floor):
    """(a) ΔR(5.8e7) against the closed form, 2 %."""
    cu = floor["sigma"][COPPER_SIGMA]
    rel = abs(cu["dz"].real / cu["dz_ref"].real - 1.0)
    _say(f"\n[TH-14 step2 floor] (a) dR {cu['dz'].real:.9e} vs {cu['dz_ref'].real:.9e} -> {rel:.4%}")
    assert cu["dz"].real > 0.0
    assert rel <= DODD_DEEDS_BAND, rel


@complex_only
def test_surface_loss_identity(floor):
    """(b) Re ΔZ·½|I|² = ½∫_401 Re(1/Z_s)|n × E|², copper."""
    cu = floor["sigma"][COPPER_SIGMA]
    assert cu["p_surf"] > 0.0
    assert cu["identity"] <= DISCRETE_IDENTITY_RTOL, cu["identity"]


@complex_only
def test_thin_skin_resistance_scales_as_inverse_sqrt_sigma(floor):
    """(c) ΔR(5.8e7)/ΔR(5.8e9) = 10 within 1 %."""
    assert abs(floor["scaling"] / 10.0 - 1.0) <= SCALING_BAND, floor["scaling"]


@complex_only
def test_thin_skin_reactance_departure_equals_resistance(floor):
    """(d) ΔX(σ) − ΔX_PEC = ΔR(σ) within 2 %, copper, same mesh."""
    cu = floor["sigma"][COPPER_SIGMA]
    ratio = cu["dz"].imag / cu["dz"].real
    _say(f"\n[TH-14 step2 floor] (d) (dX - dX_PEC)/dR = {ratio:.9f}")
    assert abs(ratio - 1.0) <= THIN_SKIN_BAND, ratio


@complex_only
def test_pec_floor_control_is_lossless(floor):
    """Negative control (asserted): no loss without the term."""
    dz = floor["dz_pec"]
    assert abs(dz.real) <= PEC_CONTROL_BOUND * abs(dz.imag), dz
