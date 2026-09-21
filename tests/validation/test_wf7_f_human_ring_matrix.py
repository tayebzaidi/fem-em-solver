"""`WF-7` step 1 — the F-human 32x32 at 64 MHz, degree 1, gated on `PORT-13`'s
identities and `PORT-16`'s exact discrete power identity.

§9 item 21 (2026-09-21 review, chain step H3).  One window, heavy tier,
``-n 8``, complex build.  Self-consistency identities on one fixture at degree 1
— **no field, no B1+, no SAR, no absolute S**; degree 1 at human scale carries
the 2026-09-19 weekly's 5.50 % order caveat (`WF-7` step 0b: ``|S_2 - S_1|/|S_1|``
on ``S_driven(P17)``).

Fixture: built exactly as ``scripts/probes/wf7_step0_f_human_cost.py:229–293``
builds it — `GEO-25`'s F-human rung (``_params(F_HUMAN_RING_RADIUS,
scale_sizing=False)``, branch B) with ``ring_sheet_orientation="longitudinal"``,
all 32 ring sheets at the terminated ``z0``, `PORT-13`'s materials, PEC outer
boundary, 64 MHz.  All 32 ring ports are driven in turn through
`test_port_birdcage_ring_column._solve_one_drive`, the first factorising and the
other 31 back-substituting the held MUMPS factor (`PORT-19` step 3).  Per drive,
**before the fields are dropped**, the exact identity
``P_src,exact = P_vol + P_sheet,exact`` is evaluated with `PORT-16`'s own
helpers (`test_birdcage_power_identity`, imported) and the package's
`terminal_form_deficit` is printed beside it.

Anchors (asserted, every band imported, none restated):
  (i)   the cell record inside ``CELL_COUNT_BAND``;
  (ii)  32x32 reciprocity ``<= RECIPROCITY_BAND``;
  (iii) ``sigma_max <= MATRIX_PASSIVITY_CEILING`` (exactly 1.0, `PORT-13`);
  (iv)  exactly ``N_SYMMETRY_CLASSES`` (18) C16 x mirror classes from the
        **measured** sheet azimuths and ring membership, every pair within
        ``AZIMUTH_MATCH_DEG`` of a class, worst spread ``<= OPPOSITE_SPREAD_BAND``;
  (v)   the exact discrete power identity ``<= DISCRETE_IDENTITY_RTOL`` on the
        driven columns (all 32, unless the first identity evaluation costs more
        than ``IDENTITY_PRICE_STOP_S``, or the projected window exceeds
        ``WINDOW_BUDGET_S`` — then drives 1, 9, 17, 25 only, and the window
        says so).

Negative controls:
  * *asserted* (mesh level, no solve on the degenerate build): the same
    fixture with ``ring_sheet_orientation`` at its default has every ring
    sheet's extent along its drive direction ``< DEGENERATE_EXTENT_M``, while
    the longitudinal build's gap chord and every sheet's extent along its drive
    direction are ``> DEGENERATE_EXTENT_M``;
  * *asserted* (arithmetic): one column x ``CONTROL_COLUMN_SCALE`` raises the
    reciprocity ratio by more than ``CONTROL_RATIO_LIFT`` x the measured one;
  * *predicted, printed, never asserted* (rule (e)): the same control against
    ``MATRIX_CONTROL_MARGIN x RECIPROCITY_BAND`` — the review's arithmetic puts
    this fixture's ceiling at ~1.5–2.1e-3, at or past the 2e-3 bar.

Printed, never gated: per-drive terminal residual beside the in-run pooled
``C/terminal - 1``; full-column ``sum_i |S_ij|^2``; ``S_driven(P17)`` beside the
step-0 record.
"""

from __future__ import annotations

import resource
import time

import numpy as np
from mpi4py import MPI

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator, _interface_facet_tags
from fem_em_solver.ports.lumped import LumpedSheetPortSpec
from fem_em_solver.ports.shares import terminal_form_deficit

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_leg_offset import _sheet_azimuth_deg, _sheet_nodes
from tests.mesh.test_birdcage_port_sheet_prerequisite import CELL_COUNT_BAND
from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER, SHEET_IFACE
from tests.mesh.test_birdcage_port_terminals import _interface_area_or_zero
from tests.mesh.test_birdcage_ring_gaps_scaleup import _ring_gap_frame
from tests.mesh.test_birdcage_ring_sheet_orientation import (
    DEGENERATE_EXTENT_M,
    _sheet_extent_along,
)
from tests.validation.test_birdcage_f_human_rung import (
    F_HUMAN_BRANCH_B_CELL_RECORD,
    F_HUMAN_RING_RADIUS,
    LEG_COUNT,
    _params,
    _ring_ports,
)
from tests.validation.test_birdcage_power_identity import (
    DISCRETE_IDENTITY_RTOL,
    _sheet_field_dissipation_w,
    _source_power_w,
)
from tests.validation.test_lossy_sphere_fullwave import SALINE_EPSILON_R, SALINE_SIGMA
from tests.validation.test_port_birdcage_four_port import TERMINATED_PORT_IMPEDANCE_OHM
from tests.validation.test_port_birdcage_lumped_column import (
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)
from tests.validation.test_port_birdcage_ring_column import (
    AZIMUTH_MATCH_DEG,
    CONTROL_COLUMN_SCALE,
    OPPOSITE_SPREAD_BAND,
    _reciprocity_ratio,
    _solve_one_drive,
)
from tests.validation.test_port_birdcage_ring_matrix import (
    AZIMUTH_STEP_DEG,
    MATRIX_CONTROL_MARGIN,
    MATRIX_PASSIVITY_CEILING,
    N_AZIMUTH_CLASSES,
    N_SYMMETRY_CLASSES,
    _azimuth_class,
)
from tests.validation.test_port_gap_voltage_impedance import SIGMA_WIRE_S_PER_M
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND

FREQUENCY_HZ = 64.0e6
DEGREE = 1

# §9 item 21's cost rule: the identity's facet assembly per drive is
# unmeasured; if the first one exceeds this, the identity runs on drives
# 1, 9, 17, 25 only and the window prints that it did.
IDENTITY_PRICE_STOP_S = 15.0
IDENTITY_FALLBACK_DRIVES = (0, 8, 16, 24)
# The slot's wall budget for this one window (container ``timeout`` 590 s,
# the scheduled slot's cap on a single foreground command), and the two
# measured prices the projection uses: a held back-substitution 0.59 s and the
# F-human build 120.98 s, both at -n 8
# (`20260916T093548Z_WF-7-step0c.log:10419–10431`), rounded up.
WINDOW_BUDGET_S = 540.0
HELD_SOLVE_ESTIMATE_S = 1.0
CONTROL_BUILD_ESTIMATE_S = 135.0

# The asserted arithmetic control: a 1 % scale on one column must lift the
# reciprocity ratio by more than this factor over the measured ratio (§9 item
# 21; step 0c measured 1.084e-14 at -n 16, so the lift available is ~1e11).
CONTROL_RATIO_LIFT = 1.0e6

# The step-0 record, printed beside S_driven(P17) — never compared here
# (version- and width-tagged, `OPS-41`; `WF-7` step 0c anchor (a) owns it).
S_DRIVEN_STEP0_RECORD = "0.407423+0.344417j"


def _sheet_centre_z(msh, facet_tags, tag, comm) -> float:
    """``z`` of one sheet's bounding-box centre [m], reduced over ranks."""
    pts = _sheet_nodes(msh, facet_tags, tag)
    lo = float(pts[:, 2].min()) if pts.shape[0] else np.inf
    hi = float(pts[:, 2].max()) if pts.shape[0] else -np.inf
    lo = comm.allreduce(lo, op=MPI.MIN)
    hi = comm.allreduce(hi, op=MPI.MAX)
    return 0.5 * (lo + hi)


def _rss_summed_gib(comm) -> float:
    local = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024.0 / 2**30
    return float(comm.allreduce(local, op=MPI.SUM))


@complex_only
def test_the_f_human_ring_matrix_carries_port13_and_port16_identities():
    comm = MPI.COMM_WORLD
    t_window = time.perf_counter()

    def say(msg: str) -> None:
        if comm.rank == 0:
            print(f"[WF-7 step1] {msg}", flush=True)

    say(f"start: -n {comm.size}, f = {FREQUENCY_HZ:.3e} Hz, degree {DEGREE}, "
        f"ring_radius {F_HUMAN_RING_RADIUS} m, branch B, longitudinal ring sheets")

    # ---- the fixture, as the step-0 probe builds it (:229–293) -----------
    kwargs = _params(F_HUMAN_RING_RADIUS, scale_sizing=False)
    kwargs["ring_sheet_orientation"] = "longitudinal"
    t0 = time.perf_counter()
    msh, cell_tags, _facets, diag = MeshGenerator.birdcage_port_domain(
        comm=comm, return_diagnostics=True, **kwargs
    )
    build_s = time.perf_counter() - t0
    n_cells = msh.topology.index_map(3).size_global
    rel = n_cells / F_HUMAN_BRANCH_B_CELL_RECORD - 1.0
    say(f"mesh: cells {n_cells} vs record {F_HUMAN_BRANCH_B_CELL_RECORD}, relative "
        f"{rel:.3e} (band {CELL_COUNT_BAND}, imported)  build {build_s:.2f} s")

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
    areas = {i: _interface_area_or_zero(msh, tags_f, SHEET_IFACE + i, comm)
             for i in ring_ports}
    specs = []
    phi_hats = {}
    for i in ring_ports:
        phi_hat, _centre = _ring_gap_frame(i, LEG_COUNT)
        phi_hats[i] = np.asarray(phi_hat, dtype=float)
        specs.append(
            LumpedSheetPortSpec(
                port_id=f"P{i}",
                facet_tag=int(SHEET_IFACE + i),
                port_impedance_ohm=TERMINATED_PORT_IMPEDANCE_OHM,
                gap_height_m=chord,
                sheet_width_m=areas[i] / chord,
                drive_direction=tuple(float(c) for c in phi_hat),
                drive_voltage_v=1.0 + 0.0j,
                interior=True,
            )
        )
    # Measured geometry for the class table and the orientation control.
    azimuth = {i: _sheet_azimuth_deg(msh, tags_f, SHEET_IFACE + i, comm)
               for i in ring_ports}
    centre_z = {i: _sheet_centre_z(msh, tags_f, SHEET_IFACE + i, comm)
                for i in ring_ports}
    long_extent = {
        i: _sheet_extent_along(msh, tags_f, SHEET_IFACE + i, phi_hats[i], comm)
        for i in ring_ports
    }

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
    omega = 2.0 * np.pi * FREQUENCY_HZ
    ctx = {
        "comm": comm,
        "msh": msh,
        "tags_f": tags_f,
        "cell_tags": cell_tags,
        "omega": omega,
        "specs": specs,
        "solver": TimeHarmonicSolver(problem, degree=DEGREE),
    }
    # `PORT-16`'s helpers read the fixture through this dict shape.
    sweep = {"mesh": msh, "facet_tags": tags_f, "cell_tags": cell_tags, "specs": specs}

    # ---- the 32 drives ----------------------------------------------------
    driven_ids = [f"P{i}" for i in ring_ports]
    columns: dict[str, dict] = {}
    identity: dict[str, dict] = {}
    identity_drives = set(range(len(driven_ids)))
    identity_mode = "all 32 drives"
    for k, driven in enumerate(driven_ids):
        col = _solve_one_drive(ctx, driven, reuse_factorization=(k > 0))
        fields = col.pop("fields")
        if k in identity_drives:
            t_id = time.perf_counter()
            sheets = [spec.sheet(driven=(spec.port_id == driven)) for spec in specs]
            driven_sheet = next(s for s in sheets if s.port_id == driven)
            e = fields.e_complex
            p_src = _source_power_w(sweep, driven_sheet, e, omega)
            p_sheet = float(sum(
                _sheet_field_dissipation_w(sweep, s, e, omega) for s in sheets
            ))
            # P_vol is `_loss_power_w`'s ½∫σ|E|² over phantom + conductor, which
            # `_solve_one_drive` already evaluated through the same `mean_sar`.
            p_vol = float(col["phantom"] + col["conductor"])
            deficit = terminal_form_deficit(msh, tags_f, sheets, e, comm)
            identity[driven] = {
                "p_src": p_src,
                "p_vol": p_vol,
                "p_sheet": p_sheet,
                "rel": abs(p_src - p_vol - p_sheet) / abs(p_src),
                "pooled": float(deficit["pooled"]),
            }
            id_s = time.perf_counter() - t_id
            if k == 0:
                say(f"identity price, drive 1: {id_s:.2f} s (stop rule "
                    f"{IDENTITY_PRICE_STOP_S:.0f} s)")
                projected = (time.perf_counter() - t_window
                             + 31 * (HELD_SOLVE_ESTIMATE_S + id_s)
                             + CONTROL_BUILD_ESTIMATE_S)
                say(f"projected window with the identity on all 32: {projected:.0f} s "
                    f"(budget {WINDOW_BUDGET_S:.0f} s)")
                if id_s > IDENTITY_PRICE_STOP_S or projected > WINDOW_BUDGET_S:
                    identity_drives = set(IDENTITY_FALLBACK_DRIVES)
                    identity_mode = (
                        "drives 1, 9, 17, 25 only (first identity cost "
                        f"{id_s:.2f} s vs stop rule {IDENTITY_PRICE_STOP_S:.0f} s; "
                        f"projected window {projected:.0f} s vs budget "
                        f"{WINDOW_BUDGET_S:.0f} s)"
                    )
                    say(f"identity restricted to {identity_mode}")
        del fields  # 32 columns of F-human fields is the memory trap
        columns[driven] = col
        line = (f"drive {k + 1:2d}/32 {driven}: {col['solve_kind']} "
                f"{col['solve_time']:.2f} s  S_driven {col['s_column'][driven]:.6f}  "
                f"terminal residual {col['residual']:.3e}  "
                f"sum|S_ij|^2 {sum(abs(s) ** 2 for s in col['s_column'].values()):.6f}")
        if driven in identity:
            d = identity[driven]
            line += (f"  | P_src,exact {d['p_src']:.9e} W  P_vol {d['p_vol']:.9e} W  "
                     f"P_sheet,exact {d['p_sheet']:.9e} W  identity rel {d['rel']:.3e}  "
                     f"pooled C/terminal-1 {d['pooled']:.6e}")
        say(line + f"  t={time.perf_counter() - t_window:.1f} s")

    kinds = [columns[p]["solve_kind"] for p in driven_ids]
    say(f"solve kinds: {kinds.count('solve')} factorising, {kinds.count('held')} held; "
        f"summed ru_maxrss {_rss_summed_gib(comm):.3f} GiB")
    del ctx, problem

    # ---- the 32x32 and its identities -------------------------------------
    s = np.array(
        [[columns[pj]["s_column"][pi] for pj in driven_ids] for pi in driven_ids],
        dtype=complex,
    )
    ratio = _reciprocity_ratio(s)
    control = s.copy()
    control[:, 0] *= CONTROL_COLUMN_SCALE
    control_ratio = _reciprocity_ratio(control)
    sigma_max = float(np.linalg.norm(s, 2))
    col_norms = np.sum(np.abs(s) ** 2, axis=0)

    az = np.array([azimuth[i] for i in ring_ports])
    zc = np.array([centre_z[i] for i in ring_ports])
    n = len(ring_ports)
    classes: dict = {}
    worst_residual_deg = 0.0
    for i in range(n):
        for j in range(n):
            steps, residual_deg = _azimuth_class(az[i], az[j])
            worst_residual_deg = max(worst_residual_deg, residual_deg)
            classes.setdefault((bool(zc[i] * zc[j] > 0.0), steps), []).append(
                float(abs(s[i, j]))
            )
    spreads = {}
    for key, mags in classes.items():
        m = np.array(mags)
        spreads[key] = (float((m.max() - m.min()) / m.mean()), len(m), float(m.mean()))
    worst = max(spreads, key=lambda key: spreads[key][0])

    say(f"(i) cells {n_cells}, relative {rel:.3e} to {F_HUMAN_BRANCH_B_CELL_RECORD} "
        f"(band {CELL_COUNT_BAND}, ASSERTED)")
    say(f"(ii) reciprocity ||S-S^T||_F/||S||_F = {ratio:.6e} (band "
        f"{RECIPROCITY_BAND:.0e}, ASSERTED); ||S||_F = {np.linalg.norm(s, 'fro'):.6f}")
    say(f"(iii) sigma_max = {sigma_max:.9f} (ceiling {MATRIX_PASSIVITY_CEILING}, "
        f"ASSERTED), margin {MATRIX_PASSIVITY_CEILING - sigma_max:+.3e}; full-column "
        f"sum|S_ij|^2 min {col_norms.min():.6f} max {col_norms.max():.6f} (printed)")
    say(f"(iv) C16 x mirror classes: {len(classes)} (expected {N_SYMMETRY_CLASSES}, "
        f"ASSERTED); worst azimuth residual {worst_residual_deg:.3e} deg "
        f"(< {AZIMUTH_MATCH_DEG:.0e}, ASSERTED); step {AZIMUTH_STEP_DEG:.3f} deg")
    for same_ring in (True, False):
        for steps in range(N_AZIMUTH_CLASSES):
            if (same_ring, steps) not in spreads:
                say(f"     {'same ' if same_ring else 'other'} ring, {steps} steps: EMPTY")
                continue
            sp, cnt, mean = spreads[(same_ring, steps)]
            say(f"     {'same ' if same_ring else 'other'} ring, {steps} steps  "
                f"n = {cnt:4d}  mean |S| = {mean:.9e}  spread {sp * 100:8.4f}%"
                + ("   <-- worst" if (same_ring, steps) == worst else ""))
    say(f"     worst class spread {spreads[worst][0]:.4e} (band "
        f"{OPPOSITE_SPREAD_BAND}, ASSERTED)")
    id_rels = [identity[p]["rel"] for p in identity]
    pooled = [identity[p]["pooled"] for p in identity]
    resid = [columns[p]["residual"] for p in driven_ids]
    say(f"(v) exact discrete power identity on {identity_mode}: max rel "
        f"{max(id_rels):.3e} (band {DISCRETE_IDENTITY_RTOL:g}, ASSERTED); "
        f"pooled C/terminal-1 {min(pooled):.6e}..{max(pooled):.6e} beside the "
        f"terminal residual {min(resid):.3e}..{max(resid):.3e} (printed)")
    say(f"S_driven(P17) {columns['P17']['s_column']['P17']:.6f} beside the step-0 "
        f"record {S_DRIVEN_STEP0_RECORD} (printed, -n {comm.size})")
    say(f"control (asserted): column {driven_ids[0]} x {CONTROL_COLUMN_SCALE}: "
        f"ratio {control_ratio:.6e} = {control_ratio / max(ratio, 1e-300):.3e}x the "
        f"measured (bar {CONTROL_RATIO_LIFT:.0e}x)")
    bar = MATRIX_CONTROL_MARGIN * RECIPROCITY_BAND
    say(f"control (predicted, printed, never asserted — rule (e)): {control_ratio:.6e} "
        f"vs MATRIX_CONTROL_MARGIN x RECIPROCITY_BAND = {bar:.1e}: "
        f"{'at/above' if control_ratio >= bar else 'BELOW'} the bar "
        f"(predicted ~1.5-2.1e-3, at or past the fixture's ceiling)")

    # ---- the mesh-level orientation control (no solve) --------------------
    t0 = time.perf_counter()
    kwargs_default = _params(F_HUMAN_RING_RADIUS, scale_sizing=False)
    assert "ring_sheet_orientation" not in kwargs_default
    msh_d, cell_tags_d, _f_d, _diag_d = MeshGenerator.birdcage_port_domain(
        comm=comm, return_diagnostics=True, **kwargs_default
    )
    tags_d = _interface_facet_tags(
        msh_d, cell_tags_d,
        {SHEET_IFACE + i: (PORT_LOWER + i, PORT_UPPER + i) for i in ring_ports},
    )
    default_extent = {
        i: _sheet_extent_along(msh_d, tags_d, SHEET_IFACE + i, phi_hats[i], comm)
        for i in ring_ports
    }
    default_cells = msh_d.topology.index_map(3).size_global
    say(f"orientation control: default build {default_cells} cells "
        f"({time.perf_counter() - t0:.2f} s); max extent along phi_hat "
        f"{max(default_extent.values()):.3e} m (< {DEGENERATE_EXTENT_M:.0e}, ASSERTED); "
        f"longitudinal chord {chord:.6e} m, min extent along phi_hat "
        f"{min(long_extent.values()):.6e} m (> {DEGENERATE_EXTENT_M:.0e}, ASSERTED)")
    say(f"window elapsed {time.perf_counter() - t_window:.1f} s, summed ru_maxrss "
        f"{_rss_summed_gib(comm):.3f} GiB")

    # ---- the asserts, in the item's order -----------------------------------
    assert abs(rel) < CELL_COUNT_BAND, (
        f"(i) {n_cells} cells, relative {rel:.3e} to {F_HUMAN_BRANCH_B_CELL_RECORD}"
    )
    assert ratio <= RECIPROCITY_BAND, f"(ii) reciprocity {ratio:.6e} > {RECIPROCITY_BAND}"
    assert float(col_norms.max()) <= MATRIX_PASSIVITY_CEILING
    assert sigma_max <= MATRIX_PASSIVITY_CEILING, (
        f"(iii) sigma_max {sigma_max:.9f} > {MATRIX_PASSIVITY_CEILING}"
    )
    assert worst_residual_deg < AZIMUTH_MATCH_DEG, (
        f"(iv) a pair sits {worst_residual_deg:.3e} deg off every C16 class"
    )
    assert len(classes) == N_SYMMETRY_CLASSES, (
        f"(iv) {len(classes)} classes, not {N_SYMMETRY_CLASSES}"
    )
    assert sum(len(v) for v in classes.values()) == n * n
    assert spreads[worst][0] <= OPPOSITE_SPREAD_BAND, (
        f"(iv) class {worst} spreads {spreads[worst][0]:.4e} > {OPPOSITE_SPREAD_BAND}"
    )
    for pid, d in identity.items():
        assert d["p_src"] > 0.0, f"(v) {pid}: P_src,exact {d['p_src']:.6e} <= 0"
        assert d["rel"] <= DISCRETE_IDENTITY_RTOL, (
            f"(v) {pid}: identity misses by {d['rel']:.6e} — P_src {d['p_src']:.9e}, "
            f"P_vol {d['p_vol']:.9e}, P_sheet {d['p_sheet']:.9e}"
        )
    assert chord > DEGENERATE_EXTENT_M
    assert min(long_extent.values()) > DEGENERATE_EXTENT_M
    assert max(default_extent.values()) < DEGENERATE_EXTENT_M, (
        "the default-orientation ring sheets have extent along phi_hat — the "
        "mis-paired orientation control does not hold"
    )
    assert control_ratio > CONTROL_RATIO_LIFT * ratio, (
        f"a 1% column scale lifts the reciprocity ratio only to {control_ratio:.6e} "
        f"from {ratio:.6e}"
    )
