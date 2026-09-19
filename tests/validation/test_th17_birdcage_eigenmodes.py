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
from mpi4py import MPI

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


def solve_modes(fx, c_f, *, omega_lin_rad_s, degree=1, nev=NEV, live=None):
    """One (G1) solve; returns ``(eigenvalues, n_converged, n_dofs, wall_s)``."""

    msh = fx["mesh"]
    V = fem.functionspace(msh, ("N1curl", degree))
    eps = permittivity_field(msh, fx["cell_tags"], omega_lin_rad_s)
    trial, test = ufl.TrialFunction(V), ufl.TestFunction(V)
    forms = _capacitor_mass_forms(
        msh, fx["sheet_facet_tags"], fx["sheets"], c_f, trial, test,
        omega_ref_rad_s=omega_lin_rad_s, live=live,
    )
    k0_sq = (2.0 * np.pi * TARGET_FREQUENCY_HZ / C_0) ** 2
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
