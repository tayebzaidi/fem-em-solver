"""`TH-17` — eigenmodes of the loaded F-small birdcage with the PEC coil and
`PORT-15` step 3's tuned capacitor sheets.

Fixture: `TH-15` step 3's hole mesh (``_sheets_build(True, as_hole=True)`` —
the coil cut from the air, its cavity wall exterior and therefore PEC under the
``pec_facet_tags=None`` reasoning that fixture documents), the phantom at
``SALINE_SIGMA`` / ``SALINE_EPSILON_R``, and the four gap sheets carrying
``Z_p = 1/(jωC)`` at `PORT-15` step 3's ``C_tuned`` (**imported** from
``tests.validation.test_port_circuit_layer_field`` — ``select_c_tuned`` on
``tuning_sweep``, never restated here).  No source, no termination: the whole
problem is the one non-Hermitian generalised pencil (G1) of
:func:`fem_em_solver.core.cavity.solve_general_mesh_modes`.

Step 1 lands the **cost probe** first (§5.1, §9 item 2): this mesh has never
carried an eigensolve — `TH-9` and `TH-14` were boxes.  ``TH17_PROBE=1`` runs
mesh + one shift-invert solve at the 64 MHz target with ``nev = 6`` and prints
cells / dofs / wall / ``ru_maxrss`` per rank.  The item's **pre-registered STOP
rule**: > 15 min or > 40 GiB at ``-n 4`` ⇒ the step re-prices to an XL cost
probe and nothing else runs.
"""

from __future__ import annotations

import os
import resource
import time

import numpy as np
import pytest
import ufl
from dolfinx import fem
from dolfinx.fem.petsc import assemble_matrix
from mpi4py import MPI
from petsc4py import PETSc

from fem_em_solver.core.cavity import (
    complex_relative_permittivity,
    solve_general_mesh_modes,
)
from fem_em_solver.ports.lumped import (
    LumpedPortSheet,
    lumped_port_bilinear_term,
    series_rlc_impedance,
)
from fem_em_solver.utils.constants import C_0

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
from tests.validation.test_port_birdcage_leg_offset_sweep import (
    _narrowed_radial,
    _port_frame,
)
from tests.validation.test_port_birdcage_lumped_column import (
    PHANTOM_CELL_TAG,
    SALINE_EPSILON_R,
    SALINE_SIGMA,
)
from tests.validation.test_port_circuit_layer_field import (
    S_64MHZ_EPS0_RECORD,
    STEP3_REGISTERED_FREQUENCY_HZ,
    select_c_tuned,
    tuning_sweep,
)
from tests.validation.test_port_lumped_narrowed_sheet import GATED_WIDTH_FRACTION

PROBE_ENV = "TH17_PROBE"
#: Step 1b's two diagnostics (§9 item 10 (i) and (ii)) — env-gated exactly as the
#: probe is, so the default collection of this module is unchanged.
STEP1B_ENV = "TH17_STEP1B"
#: (ii) the eight shift-invert targets [Hz], the item's list verbatim.
SCAN_TARGETS_HZ = (1e6, 4e6, 16e6, 32e6, 64e6, 128e6, 256e6, 512e6)
#: (ii) only converged eigenvalues above this are interesting — below it is the
#: N1curl gradient (null-space) cluster step 1 part (i) found (`Re f` ≈ 2 kHz).
SCAN_PRINT_FLOOR_HZ = 1.0e6
#: `PORT-15` step 3's registered tuning frequency is the eigen target.
TARGET_FREQUENCY_HZ = STEP3_REGISTERED_FREQUENCY_HZ
NEV = 6


def c_tuned_farad() -> float:
    """`PORT-15` step 3's ``C_tuned`` — imported, recomputed, never restated."""

    _, _, roots = tuning_sweep(S_64MHZ_EPS0_RECORD, STEP3_REGISTERED_FREQUENCY_HZ)
    tuned = select_c_tuned(roots)
    assert tuned is not None, "PORT-15 step 3 tuning found no zero of Im Z_in"
    return float(tuned["c_f"])


def build_hole_fixture():
    """`TH-15` step 3's hole mesh + its four narrowed gap sheets' geometry."""

    comm = MPI.COMM_WORLD
    ports_idx = list(range(1, LEG_COUNT + 1))
    t0 = time.perf_counter()
    msh, cell_tags, facet_tags, _diag, t_mesh = _sheets_build(True, as_hole=True)
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    tags_f, _full_areas = _sheet_areas(msh, cell_tags, ports_idx, comm)
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
    return {
        "mesh": msh,
        "cell_tags": cell_tags,
        "facet_tags": facet_tags,
        "sheet_facet_tags": tags_f,
        "sheets": sheets,
        "n_cells": int(msh.topology.index_map(tdim).size_global),
        "t_mesh_s": float(t_mesh),
        "t_fixture_s": float(time.perf_counter() - t0),
    }


def permittivity_field(msh, cell_tags, omega_lin_rad_s):
    """DG0 ``ε_r,c``: the phantom linearised at ``ω_lin``, air elsewhere."""

    Q = fem.functionspace(msh, ("DG", 0))
    eps = fem.Function(Q, name="epsilon_r_complex")
    eps.x.array[:] = 1.0 + 0.0j
    phantom_cells = np.asarray(cell_tags.find(PHANTOM_CELL_TAG), dtype=np.int32)
    if phantom_cells.size:
        dofs = fem.locate_dofs_topological(Q, msh.topology.dim, phantom_cells)
        eps.x.array[dofs] = complex_relative_permittivity(
            SALINE_EPSILON_R, SALINE_SIGMA, omega_lin_rad_s
        )
    eps.x.scatter_forward()
    return eps


def _capacitor_mass_forms(msh, sheet_facet_tags, sheets, c_f, trial, test,
                          *, omega_ref_rad_s, live=None):
    """``−(c²/ω_ref²)·L1(ω_ref)`` per sheet — the (L1) law, moved onto ``k₀²``.

    ``live`` (default: all) selects which sheets carry the capacitor; the
    shuffled-sheet negative control passes a subset of tags.
    """

    z_p = series_rlc_impedance(TARGET_FREQUENCY_HZ, c_f=float(c_f))
    scale = -(C_0 ** 2) / (float(omega_ref_rad_s) ** 2)
    forms = []
    for s in sheets:
        if live is not None and s["tag"] not in live:
            continue
        sheet = LumpedPortSheet(
            port_id=f"P{s['tag'] - SHEET_IFACE}",
            facet_tag=int(s["tag"]),
            port_impedance_ohm=z_p,
            gap_height_m=s["h"],
            sheet_width_m=s["w"],
            drive_direction=(0.0, 0.0, 1.0),
            source_voltage_v=0.0 + 0.0j,
            interior=True,
        )
        forms.append(
            scale
            * lumped_port_bilinear_term(
                msh, sheet_facet_tags, sheet, trial, test,
                omega_rad_per_s=float(omega_ref_rad_s),
            )
        )
    return forms


def solve_modes(fx, c_f, *, omega_lin_rad_s, degree=1, nev=NEV, live=None,
                target_hz=TARGET_FREQUENCY_HZ):
    """One (G1) solve; returns ``(eigenvalues, n_converged, n_dofs, wall_s)``.

    ``target_hz`` (default: the registered 64 MHz target, so step 1's probe is
    unchanged) is the shift-invert target; step 1b (ii) sweeps it.
    """

    msh = fx["mesh"]
    V = fem.functionspace(msh, ("N1curl", degree))
    eps = permittivity_field(msh, fx["cell_tags"], omega_lin_rad_s)
    trial, test = ufl.TrialFunction(V), ufl.TestFunction(V)
    forms = _capacitor_mass_forms(
        msh, fx["sheet_facet_tags"], fx["sheets"], c_f, trial, test,
        omega_ref_rad_s=omega_lin_rad_s, live=live,
    )
    k0_sq = (2.0 * np.pi * float(target_hz) / C_0) ** 2
    t0 = time.perf_counter()
    values, n_converged, n_bc = solve_general_mesh_modes(
        V, eps, target_k0_sq=k0_sq, sheet_mass_forms=forms, nev=nev,
        comm=msh.comm,
    )
    wall = float(time.perf_counter() - t0)
    n_dofs = int(V.dofmap.index_map.size_global * V.dofmap.index_map_bs)
    return values, int(n_converged), n_dofs, wall, int(n_bc)


def frequency_of(lam: complex) -> complex:
    """``f = c√λ / 2π`` [Hz], complex."""

    return C_0 * np.sqrt(complex(lam)) / (2.0 * np.pi)


@complex_only
@pytest.mark.skipif(os.environ.get(PROBE_ENV) != "1", reason=f"set {PROBE_ENV}=1")
def test_cost_probe():
    """§9 item 2 (i): the unmeasured cost of one (G1) solve on the hole mesh.

    Prints cells / dofs / wall / ``ru_maxrss`` per rank and evaluates the
    item's pre-registered STOP rule (> 15 min or > 40 GiB at ``-n 4``).
    Asserts nothing but that an eigenpair converged — this is a probe.
    """

    comm = MPI.COMM_WORLD
    t_all = time.perf_counter()
    c_f = c_tuned_farad()
    fx = build_hole_fixture()
    omega_lin = 2.0 * np.pi * TARGET_FREQUENCY_HZ
    values, n_converged, n_dofs, wall, n_bc = solve_modes(
        fx, c_f, omega_lin_rad_s=omega_lin
    )
    total = float(time.perf_counter() - t_all)

    rss_gib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 ** 2)
    all_rss = comm.allgather(float(rss_gib))
    summed = float(sum(all_rss))

    if comm.rank == 0:
        print(f"\n[TH-17 probe] ranks = {comm.size}, cells = {fx['n_cells']}, "
              f"dofs (N1curl deg 1) = {n_dofs}, constrained (rank-local) = {n_bc}")
        print(f"[TH-17 probe] mesh {fx['t_mesh_s']:.2f} s, fixture {fx['t_fixture_s']:.2f} s, "
              f"eigensolve {wall:.2f} s, probe total {total:.2f} s")
        print("[TH-17 probe] ru_maxrss per rank [GiB]: "
              + ", ".join(f"{v:.3f}" for v in all_rss)
              + f"; summed {summed:.3f}, max {max(all_rss):.3f}")
        print(f"[TH-17 probe] C_tuned = {c_f:.15e} F (imported, PORT-15 step 3); "
              f"target f = {TARGET_FREQUENCY_HZ:.6e} Hz")
        print(f"[TH-17 probe] n_converged = {n_converged} of nev = {NEV}")
        for i, lam in enumerate(values[:NEV]):
            f_c = frequency_of(lam)
            q = abs(f_c.real / (2.0 * f_c.imag)) if f_c.imag != 0 else float("inf")
            print(f"    lam[{i}] = {lam.real:+.9e} {lam.imag:+.9e}j  "
                  f"f = {f_c.real:.9e} {f_c.imag:+.9e}j Hz  Q = {q:.6e}")
        stop_time = total > 15.0 * 60.0
        stop_mem = summed > 40.0
        print(f"[TH-17 probe] STOP rule (> 15 min or > 40 GiB at -n 4): "
              f"time {total / 60.0:.3f} min -> {'STOP' if stop_time else 'ok'}; "
              f"summed rss {summed:.3f} GiB -> {'STOP' if stop_mem else 'ok'}")
        print(f"[TH-17 probe] VERDICT: {'STOP' if (stop_time or stop_mem) else 'PROCEED'}")
    assert n_converged > 0, "no eigenpair converged near the 64 MHz target"


# ---------------------------------------------------------------------------
# Step 1b (§9 item 10) — the two diagnostics, printed and never gated.
#
# Step 1 part (i) found only the N1curl gradient cluster at the 64 MHz target
# (`Re f` ~ 2 kHz, `f085e51`).  Two things have to be ruled out before the
# formulation is blamed: that the (L1) sheet forms never reached the pencil at
# all (facet tags / restriction — diagnostic (i) below), and that the loaded
# modes simply sit somewhere other than 64 MHz (diagnostic (ii)).  Neither
# asserts a physical number: the item's asserted anchor is the closed-form LC
# loop control (iii), which is a different fixture.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def step1b_fixture():
    """One hole-mesh build shared by both step 1b diagnostics."""

    return build_hole_fixture()


def _sheet_dof_indicator(V, fx):
    """A ``V``-Function that is 1 on the four gap sheets' dofs and 0 elsewhere.

    Returns ``(indicator, n_sheet_dofs_global_owned)``; the owned count is
    reduced across ranks (``locate_dofs_topological`` is rank-local).
    """

    msh = V.mesh
    tdim = msh.topology.dim
    tags = fx["sheet_facet_tags"]
    pieces = [np.asarray(tags.find(int(s["tag"])), dtype=np.int32) for s in fx["sheets"]]
    facets = (
        np.unique(np.concatenate(pieces)) if pieces else np.empty(0, dtype=np.int32)
    )
    dofs = fem.locate_dofs_topological(V, tdim - 1, facets)
    ind = fem.Function(V)
    ind.x.array[:] = 0.0
    ind.x.array[dofs] = 1.0
    ind.x.scatter_forward()
    n_owned_local = int(
        np.count_nonzero(dofs < V.dofmap.index_map.size_local * V.dofmap.index_map_bs)
    )
    return ind, int(msh.comm.allreduce(n_owned_local, op=MPI.SUM))


def _quadratic_form(mat, vec):
    """``|xᴴ M x|`` — the mass a matrix carries on the indicator's support."""

    out = mat.createVecLeft()
    mat.mult(vec, out)
    value = complex(vec.dot(out))
    out.destroy()
    return abs(value), value


@complex_only
@pytest.mark.skipif(os.environ.get(STEP1B_ENV) != "1", reason=f"set {STEP1B_ENV}=1")
def test_step1b_sheet_mass_norms(step1b_fixture):
    """(i) ``‖B_sheet‖`` against ``‖B‖`` on the sheet dofs — printed, not gated.

    A zero (or a ratio at round-off) says the (L1) forms never reached the
    pencil — the facet tags or the interior restriction — and is the first thing
    the item rules out.  The only assertion is that the sheet term is nonzero and
    finite, which is the premise every later step of `TH-17` rests on; the ratio
    itself is a diagnostic reading and carries no band.
    """

    fx = step1b_fixture
    comm = fx["mesh"].comm
    c_f = c_tuned_farad()
    omega_lin = 2.0 * np.pi * TARGET_FREQUENCY_HZ
    V = fem.functionspace(fx["mesh"], ("N1curl", 1))
    eps = permittivity_field(fx["mesh"], fx["cell_tags"], omega_lin)
    trial, test = ufl.TrialFunction(V), ufl.TestFunction(V)

    volume_ufl = ufl.inner(eps * trial, test) * ufl.dx
    forms = _capacitor_mass_forms(
        fx["mesh"], fx["sheet_facet_tags"], fx["sheets"], c_f, trial, test,
        omega_ref_rad_s=omega_lin,
    )
    assert forms, "no capacitor sheet forms were built at all"
    sheet_ufl = forms[0]
    for form in forms[1:]:
        sheet_ufl = sheet_ufl + form

    b_vol = assemble_matrix(fem.form(volume_ufl))
    b_vol.assemble()
    b_sheet = assemble_matrix(fem.form(sheet_ufl))
    b_sheet.assemble()

    n_vol = float(b_vol.norm(PETSc.NormType.FROBENIUS))
    n_sheet = float(b_sheet.norm(PETSc.NormType.FROBENIUS))

    ind, n_sheet_dofs = _sheet_dof_indicator(V, fx)
    x = ind.x.petsc_vec
    q_vol, q_vol_c = _quadratic_form(b_vol, x)
    q_sheet, q_sheet_c = _quadratic_form(b_sheet, x)

    n_dofs = int(V.dofmap.index_map.size_global * V.dofmap.index_map_bs)
    if comm.rank == 0:
        print(f"\n[TH-17 1b(i)] cells = {fx['n_cells']}, N1curl deg-1 dofs = {n_dofs}, "
              f"sheet dofs (owned, reduced) = {n_sheet_dofs}, "
              f"C_tuned = {c_f:.9e} F")
        for s in fx["sheets"]:
            print(f"    sheet tag {s['tag']}: facets {s['facets']}, area {s['area']:.6e} m^2, "
                  f"h {s['h']:.6e} m, w {s['w']:.6e} m, h/w {s['h'] / s['w']:.6e}")
        print(f"[TH-17 1b(i)] Frobenius: ||B_volume|| = {n_vol:.9e}, "
              f"||B_sheet|| = {n_sheet:.9e}, ratio = {n_sheet / n_vol:.9e}")
        print(f"[TH-17 1b(i)] on the sheet-dof indicator: x^H B_volume x = {q_vol_c:.9e}, "
              f"x^H B_sheet x = {q_sheet_c:.9e}, ratio |sheet/volume| = "
              f"{(q_sheet / q_vol if q_vol else float('inf')):.9e}")
    b_vol.destroy()
    b_sheet.destroy()

    assert np.isfinite(n_sheet) and n_sheet > 0.0, (
        f"||B_sheet|| = {n_sheet!r}: the (L1) sheet forms never reached the pencil"
    )
    assert np.isfinite(q_sheet) and q_sheet > 0.0, (
        f"x^H B_sheet x = {q_sheet!r} on the sheet dofs: the restriction is empty"
    )


@complex_only
@pytest.mark.skipif(os.environ.get(STEP1B_ENV) != "1", reason=f"set {STEP1B_ENV}=1")
def test_step1b_target_scan(step1b_fixture):
    """(ii) shift-invert at eight targets; every converged `Re f` > 1 MHz printed.

    Printed, never gated (the item): this locates where the capacitor-loaded
    modes of the F-small hole mesh actually sit, so a later step can say whether
    the circuit layer's `C_tuned` puts the *eigen* resonance at 64 MHz.  The one
    assertion is that at least one target converged something — a scan that
    converges nothing is a solver report, not a spectrum.
    """

    fx = step1b_fixture
    comm = fx["mesh"].comm
    c_f = c_tuned_farad()
    omega_lin = 2.0 * np.pi * TARGET_FREQUENCY_HZ
    total_converged = 0
    above_floor = []
    for target in SCAN_TARGETS_HZ:
        values, n_converged, n_dofs, wall, _n_bc = solve_modes(
            fx, c_f, omega_lin_rad_s=omega_lin, target_hz=target
        )
        total_converged += int(n_converged)
        k0_sq = (2.0 * np.pi * float(target) / C_0) ** 2
        if comm.rank == 0:
            print(f"\n[TH-17 1b(ii)] target {target / 1e6:.0f} MHz "
                  f"(k0^2 = {k0_sq:.6e}), nev = {NEV}, converged = {n_converged}, "
                  f"{wall:.2f} s, dofs = {n_dofs}")
        for lam in values:
            f_c = frequency_of(lam)
            if abs(f_c.real) <= SCAN_PRINT_FLOOR_HZ:
                continue
            above_floor.append((float(target), complex(lam), complex(f_c)))
            q = abs(f_c.real / (2.0 * f_c.imag)) if f_c.imag != 0 else float("inf")
            if comm.rank == 0:
                print(f"    lam = {lam.real:+.9e} {lam.imag:+.9e}j  "
                      f"f = {f_c.real:.9e} {f_c.imag:+.9e}j Hz  Q = {q:.6e}  "
                      f"|lam - target| = {abs(lam - k0_sq):.6e}")
        if comm.rank == 0 and not any(t == float(target) for t, _l, _f in above_floor):
            print(f"    (nothing above {SCAN_PRINT_FLOOR_HZ / 1e6:.0f} MHz at this target "
                  f"— gradient cluster only)")
    if comm.rank == 0:
        print(f"\n[TH-17 1b(ii)] summary: {len(above_floor)} converged eigenvalue(s) "
              f"with Re f > {SCAN_PRINT_FLOOR_HZ / 1e6:.0f} MHz across "
              f"{len(SCAN_TARGETS_HZ)} targets")
        for t, lam, f_c in above_floor:
            print(f"    target {t / 1e6:.0f} MHz -> Re f = {f_c.real:.9e} Hz, "
                  f"lam = {lam.real:+.9e} {lam.imag:+.9e}j")
    assert total_converged > 0, "no eigenpair converged at any of the eight targets"


# ---------------------------------------------------------------------------
# Step 1c (§9 item 24) — the closed-form LC control on the two-torus hole
# fixture.  One gapped PEC loop (torus 1's hole, its sheet 211 carrying the
# capacitor mass form exactly as `_capacitor_mass_forms` builds it) is an LC
# circuit: `f_LC = 1/(2π√(L·C))`.  `L` is this fixture's own driven reading,
# `L_fem = Im Z_in/ω` of sheet 211 at the target, so both sides of the 5 % are
# this mesh's numbers and the box's effect on `L` cancels.  Torus 2's gap is
# left open in both solves (no sheet form in the pencil; ≥ 1e9 Ω driven).
#
# Note on the facet tag: the item text names "facet tag 201"; on the
# ``as_hole=True`` route the gap<->conductor groups 201/202 do not exist
# (`io/mesh.py` docstring, `as_hole`) — torus 1's port **sheet** is 211, the
# group every lumped-sheet caller of this fixture uses (``SHEET_FACET_TAGS``).
# ---------------------------------------------------------------------------

STEP1C_ENV = "TH17_STEP1C"
#: Open-gap termination for torus 2's sheet in the driven solve (the item: ≥ 1e9 Ω).
STEP1C_OPEN_OHM = 1.0e9
#: The driven P1 sheet's source impedance — any finite value; Z_in is V/I.
STEP1C_SOURCE_OHM = 50.0
#: The two driven frequencies (both printed; the target's `L` is the one used).
STEP1C_L_FREQUENCIES_HZ = (10.0e6, TARGET_FREQUENCY_HZ)
#: Anchor (a): the eigenvalue nearest f_LC within 5 % (item 24, registered).
STEP1C_FLC_BAND = 0.05
#: Anchor (b): at 2·C the same mode moves by 1/√2 within 2 % (item 24).
STEP1C_SQRT2_BAND = 0.02
#: Negative control: no eigenvalue with Re f in f_LC·[0.8, 1.2] without the form.
STEP1C_CONTROL_WINDOW = (0.8, 1.2)


def build_two_torus_hole_fixture():
    """`TH-15` step 2a's two-torus PEC-hole mesh + sheet 211/212 geometry.

    Every constant is imported (`test_port_reaction_impedance` for the torus
    and box, `test_port_gap_voltage_impedance` for the gap), never restated.
    """

    from fem_em_solver.io.mesh import MeshGenerator
    from tests.mesh.test_two_torus_port_sheet import SHEET_FACET_TAGS, _sheet_extents
    from tests.validation.test_port_gap_voltage_impedance import (
        GAP_ANGLE,
        GAP_ARC_RESOLUTION,
        GAP_BURIAL,
        GAP_OVERHANG,
    )
    from tests.validation.test_port_reaction_impedance import (
        AIR_PADDING,
        H_FAR,
        H_WIRE,
        MAJOR_RADIUS,
        MINOR_RADIUS,
        SEPARATION,
    )

    comm = MPI.COMM_WORLD
    t0 = time.perf_counter()
    msh, cell_tags, facet_tags = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=H_FAR,
        air_padding=AIR_PADDING,
        wire_resolution=H_WIRE,
        far_resolution=H_FAR,
        port_gap=True,
        gap_angle=GAP_ANGLE,
        gap_burial=GAP_BURIAL,
        gap_overhang=GAP_OVERHANG,
        gap_arc_resolution=GAP_ARC_RESOLUTION,
        emit_port_sheet=True,
        as_hole=True,
        comm=comm,
    )
    t_mesh = time.perf_counter() - t0
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()
    sheets = []
    for tag in SHEET_FACET_TAGS:
        tag = int(tag)
        n_facets = _sheet_facet_count(msh, facet_tags, tag, comm)
        assert n_facets > 0, f"sheet {tag}: no owned facets anywhere"
        area = _facet_group_area(msh, facet_tags, tag, comm)
        extents = _sheet_extents(msh, facet_tags, tag, comm)
        h = float(extents[1])
        sheets.append({"tag": tag, "facets": int(n_facets), "area": float(area),
                       "h": h, "w": float(area / h)})
    return {
        "mesh": msh,
        "cell_tags": cell_tags,
        "facet_tags": facet_tags,
        "sheets": sheets,
        "n_cells": int(comm.allreduce(msh.topology.index_map(tdim).size_local,
                                      op=MPI.SUM)),
        "t_mesh_s": float(t_mesh),
    }


def _driven_loop_impedance(fx, frequency_hz):
    """P1 driven, P2 open: ``(Z_in = V1/I1, Z21/Z11, wall_s)`` off the solved field."""

    from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
    from fem_em_solver.ports.definitions import PortDefinition
    from fem_em_solver.ports.lumped import LumpedSheetPortSpec, run_lumped_sheet_port_case

    msh = fx["mesh"]
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=float(frequency_hz),
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=fx["cell_tags"],
        boundary_condition="pec_zero_tangential_a",
        facet_tags=fx["facet_tags"],
        pec_facet_tags=None,
    )
    ports, specs = [], []
    for k, s in enumerate(fx["sheets"]):
        pid = f"P{k + 1}"
        ports.append(PortDefinition(
            port_id=pid, positive_tag=int(s["tag"]), negative_tag=int(s["tag"]),
            orientation="gap_azimuthal_plus_y", z0_ohm=STEP1C_SOURCE_OHM,
        ))
        specs.append(LumpedSheetPortSpec(
            port_id=pid, facet_tag=int(s["tag"]),
            port_impedance_ohm=STEP1C_SOURCE_OHM if k == 0 else STEP1C_OPEN_OHM,
            gap_height_m=s["h"], sheet_width_m=s["w"],
            drive_direction=(0.0, 1.0, 0.0), drive_voltage_v=1.0 + 0.0j,
            interior=True,
        ))
    t0 = time.perf_counter()
    res = run_lumped_sheet_port_case(
        problem, ports, specs, facet_tags=fx["facet_tags"], driven_port_id="P1",
        verbose=False,
    )
    wall = float(time.perf_counter() - t0)
    r1, r2 = res.responses["P1"], res.responses["P2"]
    z11 = complex(r1.voltage_v) / complex(r1.current_a)
    z21 = complex(r2.voltage_v) / complex(r1.current_a)
    return z11, z21 / z11, wall


def _solve_loop_modes(fx, c_f, *, target_hz, live):
    """One (G1) solve with torus 1's sheet (211) carrying ``C``; torus 2 open."""

    msh = fx["mesh"]
    V = fem.functionspace(msh, ("N1curl", 1))
    Q = fem.functionspace(msh, ("DG", 0))
    eps = fem.Function(Q, name="epsilon_r_air")
    eps.x.array[:] = 1.0 + 0.0j
    trial, test = ufl.TrialFunction(V), ufl.TestFunction(V)
    loop_sheet = [fx["sheets"][0]]
    forms = _capacitor_mass_forms(
        msh, fx["facet_tags"], loop_sheet, c_f, trial, test,
        omega_ref_rad_s=2.0 * np.pi * TARGET_FREQUENCY_HZ, live=live,
    )
    k0_sq = (2.0 * np.pi * float(target_hz) / C_0) ** 2
    t0 = time.perf_counter()
    values, n_converged, _n_bc = solve_general_mesh_modes(
        V, eps, target_k0_sq=k0_sq, sheet_mass_forms=forms, nev=NEV, comm=msh.comm,
    )
    wall = float(time.perf_counter() - t0)
    n_dofs = int(V.dofmap.index_map.size_global * V.dofmap.index_map_bs)
    freqs = [frequency_of(lam) for lam in values]
    return freqs, int(n_converged), n_dofs, wall, len(forms)


def _nearest(freqs, f_hz):
    return min(freqs, key=lambda f: abs(f.real - f_hz))


@complex_only
@pytest.mark.skipif(os.environ.get(STEP1C_ENV) != "1", reason=f"set {STEP1C_ENV}=1")
def test_step1c_lc_loop_closed_form():
    """(iii) the pencil-with-sheet-mass reproduces ``f_LC = 1/(2π√(LC))``.

    Anchors (asserted): (a) nearest eigenvalue to ``f_LC`` within 5 %;
    (b) at ``2·C`` the same mode moves by ``1/√2`` within 2 %.  Negative
    control (asserted): with the capacitor form removed (``live=()``) no
    eigenvalue has ``Re f`` in ``f_LC·[0.8, 1.2]``.
    """

    from tests.validation.test_port_self_impedance_energy import grover_loop_inductance
    from tests.validation.test_port_reaction_impedance import MAJOR_RADIUS, MINOR_RADIUS

    comm = MPI.COMM_WORLD
    t_all = time.perf_counter()
    fx = build_two_torus_hole_fixture()
    rank0 = comm.rank == 0
    if rank0:
        print(f"\n[TH-17 1c] two-torus hole fixture: {fx['n_cells']} cells, "
              f"mesh {fx['t_mesh_s']:.1f} s, ranks {comm.size}")
        for s in fx["sheets"]:
            print(f"    sheet {s['tag']}: facets {s['facets']}, area {s['area']:.9e} m^2, "
                  f"h {s['h']:.9e} m, w = A/h {s['w']:.9e} m, h/w {s['h'] / s['w']:.9e}")

    l_fem = {}
    for f_hz in STEP1C_L_FREQUENCIES_HZ:
        z11, ratio21, wall = _driven_loop_impedance(fx, f_hz)
        omega = 2.0 * np.pi * f_hz
        l_fem[f_hz] = z11.imag / omega
        if rank0:
            print(f"[TH-17 1c] driven f = {f_hz / 1e6:.3f} MHz: Z_in = "
                  f"{z11.real:+.9e} {z11.imag:+.9e}j Ohm, L_fem = Im Z_in/w = "
                  f"{l_fem[f_hz]:.9e} H, Z21/Z11 = {ratio21.real:+.6e} "
                  f"{ratio21.imag:+.6e}j (|.| = {abs(ratio21):.6e}), {wall:.1f} s")
    l_use = l_fem[TARGET_FREQUENCY_HZ]
    assert l_use > 0.0, f"L_fem = {l_use!r} H at the target: not an inductive loop"
    l_grover = grover_loop_inductance(MAJOR_RADIUS, MINOR_RADIUS)
    omega_t = 2.0 * np.pi * TARGET_FREQUENCY_HZ
    c_f = 1.0 / (omega_t ** 2 * l_use)
    f_lc = 1.0 / (2.0 * np.pi * np.sqrt(l_use * c_f))
    if rank0:
        print(f"[TH-17 1c] Grover (printed, never gated) = {l_grover:.9e} H; "
              f"L_fem(target)/Grover = {l_use / l_grover:.6f}, "
              f"L_fem(10 MHz)/Grover = {l_fem[STEP1C_L_FREQUENCIES_HZ[0]] / l_grover:.6f}")
        print(f"[TH-17 1c] C = 1/(w_t^2 L_fem) = {c_f:.9e} F; f_LC = {f_lc:.9e} Hz")

    freqs_c, n_c, n_dofs, wall_c, n_forms = _solve_loop_modes(
        fx, c_f, target_hz=f_lc, live=None)
    f_c = _nearest(freqs_c, f_lc)
    f_lc2 = f_lc / np.sqrt(2.0)
    freqs_2c, n_2c, _d, wall_2c, _n = _solve_loop_modes(
        fx, 2.0 * c_f, target_hz=f_lc2, live=None)
    f_2c = _nearest(freqs_2c, f_lc2)
    freqs_0, n_0, _d, wall_0, n_forms0 = _solve_loop_modes(
        fx, c_f, target_hz=f_lc, live=())
    lo, hi = (w * f_lc for w in STEP1C_CONTROL_WINDOW)
    in_window = [f for f in freqs_0 if lo <= f.real <= hi]

    err_a = abs(f_c.real - f_lc) / f_lc
    ratio_b = f_2c.real / f_c.real
    err_b = abs(ratio_b * np.sqrt(2.0) - 1.0)
    if rank0:
        print(f"[TH-17 1c] N1curl deg-1 dofs = {n_dofs}; sheet forms in pencil = "
              f"{n_forms}, control = {n_forms0}")
        for label, freqs, n, wall in (("C", freqs_c, n_c, wall_c),
                                      ("2C", freqs_2c, n_2c, wall_2c),
                                      ("no-C control", freqs_0, n_0, wall_0)):
            print(f"[TH-17 1c] {label}: converged {n} of nev {NEV}, {wall:.1f} s")
            for f in freqs:
                print(f"    f = {f.real:.9e} {f.imag:+.9e}j Hz")
        print(f"[TH-17 1c] (a) nearest Re f = {f_c.real:.9e} Hz (Im {f_c.imag:+.6e}) vs "
              f"f_LC = {f_lc:.9e} Hz: rel err {err_a:.6e} (band {STEP1C_FLC_BAND})")
        print(f"[TH-17 1c] (b) Re f(2C) = {f_2c.real:.9e} Hz; f(2C)/f(C) = {ratio_b:.9e} "
              f"vs 1/sqrt2 = {1.0 / np.sqrt(2.0):.9e}: rel err {err_b:.6e} "
              f"(band {STEP1C_SQRT2_BAND})")
        above = sorted((f for f in freqs_0 if f.real > SCAN_PRINT_FLOOR_HZ),
                       key=lambda f: f.real)
        first = f"{above[0].real:.9e} Hz" if above else "none (gradient cluster only)"
        print(f"[TH-17 1c] control: {len(in_window)} eigenvalue(s) in "
              f"f_LC*{STEP1C_CONTROL_WINDOW}; first converged Re f above "
              f"{SCAN_PRINT_FLOOR_HZ / 1e6:.0f} MHz = {first}")
        print(f"[TH-17 1c] total {time.perf_counter() - t_all:.1f} s")

    assert n_forms == 1 and n_forms0 == 0, "the capacitor form did not reach/leave the pencil"
    assert n_c > 0 and n_2c > 0, "no eigenpair converged near f_LC or f_LC/sqrt2"
    assert err_a <= STEP1C_FLC_BAND, (
        f"(a) nearest Re f {f_c.real:.6e} Hz vs f_LC {f_lc:.6e} Hz: {err_a:.3e} > 5 %")
    assert err_b <= STEP1C_SQRT2_BAND, (
        f"(b) f(2C)/f(C) = {ratio_b:.6e} vs 1/sqrt2: {err_b:.3e} > 2 %")
    assert not in_window, (
        f"negative control: {len(in_window)} eigenvalue(s) in f_LC*[0.8,1.2] "
        f"with no capacitor")
