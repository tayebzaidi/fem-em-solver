"""`WF-7` step 3 — the 10 g SAR hotspot at human scale, C16- and mirror-gated,
on a refined phantom.

§9 item 39 (2026-09-25 review, chain step H5).  One window, heavy tier,
``-n 8``, complex build, **selected by environment only**
(``FEM_EM_WF7_STEP3=1``), never by ``-k``.

The F-human fixture is step 2's ``_build_f_human`` with the additive
``phantom_resolution=PHANTOM_RESOLUTION_M`` (0.0075 m: the 10 g ball of radius
13.365 mm spans ≈ 3.6 phantom cells, the regime `MAT-4` gated 10 g in, instead
of ≈ 1.8 at the default 15 mm — the regime of `MAT-4` step 4's 1 g column that
read 6.84 % against the 5 % band).  The 32-drive sweep and the ccw / cw
quadrature superpositions are `POST-6`'s lifted ``_build_ring_quadrature_case``,
imported.  SAR goes through the package only: ``mass_averaged_sar`` (one ball
per call, allreduced), ``mean_sar``, ``build_density_field`` with ρ =
``PHANTOM_RHO_KG_PER_M3`` on the phantom tag and 0 elsewhere, at the
``QUADRATURE_DEGREE`` the `MAT-4` module imports.

Candidate lattice (fixed, pre-registered): at azimuth ``case["az_ref"]``,
r ∈ {15, 30, 45} mm × z ∈ {z_c − 50, z_c, z_c + 50} mm; c* = the argmax.

Anchors (asserted, every band imported):
  (i)   coverage identity — the whole-phantom ball's dissipated power equals
        ``mean_sar`` over the phantom tag, and its mass equals ρ × the meshed
        phantom volume, both within ``EXACT_IDENTITY_RTOL``;
  (ii)  C16 — the 10 g SAR at the fifteen rotations ``R_m c*`` each within
        ``C4_COVARIANCE_BAND`` of SAR(c*);
  (iii) mirror — the cw drive's 10 g SAR at ``_mirror_xy(c*, az_ref)`` within
        the same band of the ccw drive's at c*;
  (iv)  containment of every averaging ball in the measured phantom, 1 mm clear.

Negative control — *predicted, printed, never asserted* (§9 rule (e); no SAR
record on this fixture): the single-drive P17 field's 10 g SAR at c* and its
three C4 images; predicted spread >> 5 % (step 2's P17 ``|B1+|`` C16 spread was
33.3 %).

Scope: one phantom, one fixture, 64 MHz, degree 1 — a SAR location and two
symmetry identities.  No C95.3, no compliance, no absolute SAR against anything
external; degree 1 at human scale carries the 2026-09-19 weekly's 5.50 % order
caveat (`WF-7` step 0b).
"""

from __future__ import annotations

import os
import resource
import time

import numpy as np
import pytest
from mpi4py import MPI

from tests.complex_mode import complex_only

STEP3_ENV = "FEM_EM_WF7_STEP3"
# The refined phantom element size (§9 item 39): 3.6 cells across the 10 g ball.
PHANTOM_RESOLUTION_M = 0.0075
# The pre-registered candidate lattice, relative to the coil axis / phantom centre.
LATTICE_R_M = (0.015, 0.030, 0.045)
LATTICE_DZ_M = (-0.050, 0.0, 0.050)
# Containment margin (every ball 1 mm clear of the phantom's measured surface)
# and the conductor clearance of the coverage ball (§9 item 39's
# "< 0.15 m − 10 mm").
CONTAINMENT_MARGIN_M = 1.0e-3
COVERAGE_BALL_PAD_M = 1.0e-3
CONDUCTOR_CLEARANCE_M = 0.010
CONTROL_PORT = "P17"
CONTROL_IMAGES = (4, 8, 12)
# STOP rules (§9 item 39): first lattice ball > 25 s ⇒ z = z_c row only;
# build > 300 s or summed ru_maxrss > 60 GiB ⇒ stop and report.
FIRST_BALL_STOP_S = 25.0
BUILD_STOP_S = 300.0
RSS_STOP_GIB = 60.0


def _step3_on() -> bool:
    return os.environ.get(STEP3_ENV, "").strip() == "1"


def _phantom_geometry(msh, cell_tags, tag, comm):
    """Phantom centre, radius and half-height from the tag's vertex bounding box.

    Every extent is rank-local until the MIN / MAX allreduce; a rank holding no
    phantom cell contributes (+inf, −inf).
    """
    cells = np.asarray(cell_tags.indices)[np.asarray(cell_tags.values) == int(tag)]
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    if cells.size:
        dofs = np.asarray(msh.geometry.dofmap)[cells].ravel()
        xyz = np.real(np.asarray(msh.geometry.x)[np.unique(dofs), :3])
        lo = xyz.min(axis=0)
        hi = xyz.max(axis=0)
    lo = np.array([comm.allreduce(float(v), op=MPI.MIN) for v in lo])
    hi = np.array([comm.allreduce(float(v), op=MPI.MAX) for v in hi])
    centre = 0.5 * (lo + hi)
    radius = float(0.5 * max(hi[0] - lo[0], hi[1] - lo[1]))
    half_height = float(0.5 * (hi[2] - lo[2]))
    return centre, radius, half_height, lo, hi


@pytest.fixture(scope="module")
def sar10g_case():
    if not _step3_on():
        pytest.skip(
            f"{STEP3_ENV} unset: the F-human 10 g SAR hotspot is a heavy -n 8 window "
            "selected by environment only"
        )
    from fem_em_solver.post.sar import (
        averaging_ball_radius,
        build_density_field,
        mass_averaged_sar,
        mean_sar,
    )

    from tests.mesh.helpers import global_cell_tag_set
    from tests.mesh.test_birdcage_phantom_resolution import _global_tag_cell_count
    from tests.validation import test_port_drive_superposition as post6
    from tests.validation.test_birdcage_b1_plus_closed_form import _rotate_z
    from tests.validation.test_birdcage_b1_plus_map import (
        C4_COVARIANCE_BAND,
        PHANTOM_RHO_KG_PER_M3,
    )
    from tests.validation.test_birdcage_b1_quadrature import _mirror_xy
    from tests.validation.test_birdcage_f_human_rung import (
        F_HUMAN_BRANCH_B_CELL_RECORD,
        F_HUMAN_RING_RADIUS,
    )
    from tests.validation.test_birdcage_sar_mass_averaged import EXACT_IDENTITY_RTOL
    from tests.validation.test_mass_averaged_sar_standard_masses import (
        QUADRATURE_DEGREE,
        TEN_GRAM_KG,
    )
    from tests.validation.test_port_birdcage_lumped_column import PHANTOM_CELL_TAG
    from tests.validation.test_wf7_f_human_b1_quadrature import _build_f_human

    comm = MPI.COMM_WORLD

    def say(msg):
        if comm.rank == 0:
            print(f"[WF-7 step3] {msg}", flush=True)

    def rss_gib():
        return float(
            comm.allreduce(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, op=MPI.SUM)
        ) / (1024.0 * 1024.0)

    t_window = time.perf_counter()
    t0 = time.perf_counter()
    built = _build_f_human(comm, phantom_resolution=PHANTOM_RESOLUTION_M)
    # MAX-reduced so the STOP decision is identical on every rank.
    build_s = comm.allreduce(time.perf_counter() - t0, op=MPI.MAX)
    msh = built["ctx"]["msh"]
    cell_tags = built["ctx"]["cell_tags"]
    phantom_cells = _global_tag_cell_count(msh, cell_tags, PHANTOM_CELL_TAG, comm)
    say(
        f"F-human built with phantom_resolution = {PHANTOM_RESOLUTION_M} m: "
        f"{built['cells']} cells ({phantom_cells} phantom cells) beside the default "
        f"mesh's record {F_HUMAN_BRANCH_B_CELL_RECORD} (printed, NOT asserted — the "
        f"refined mesh has no record), {build_s:.2f} s at -n {comm.size}; summed "
        f"ru_maxrss {rss_gib():.3f} GiB"
    )
    if build_s > BUILD_STOP_S:
        pytest.fail(f"STOP rule: build {build_s:.1f} s > {BUILD_STOP_S:.0f} s")

    case = post6._build_ring_quadrature_case(
        built=built, cell_record=F_HUMAN_BRANCH_B_CELL_RECORD
    )
    t_sweep_done = time.perf_counter()
    rss_after_sweep = rss_gib()
    if rss_after_sweep > RSS_STOP_GIB:
        pytest.fail(f"STOP rule: summed ru_maxrss {rss_after_sweep:.1f} GiB > {RSS_STOP_GIB} GiB")
    result = case["result"]
    port_ids = case["port_ids"]
    az_ref = float(case["az_ref"])
    sigma = result.fields[port_ids[0]].sigma_field
    e_ccw = case["drives"]["ccw"].e_complex
    e_cw = case["drives"]["cw"].e_complex
    e_p17 = result.fields[CONTROL_PORT].e_complex

    # ---- phantom geometry, measured and allreduced -------------------------
    centre, radius, half_height, lo, hi = _phantom_geometry(
        msh, cell_tags, PHANTOM_CELL_TAG, comm
    )
    z_c = float(centre[2])
    a10 = averaging_ball_radius(mass_kg=TEN_GRAM_KG, rho=PHANTOM_RHO_KG_PER_M3)
    say(
        f"phantom (tag {PHANTOM_CELL_TAG}) vertex bbox lo {lo} hi {hi}: centre "
        f"({centre[0]:.6e}, {centre[1]:.6e}, {centre[2]:.6e}) m, R = {radius * 1e3:.4f} mm, "
        f"H/2 = {half_height * 1e3:.4f} mm; 10 g ball a = {a10 * 1e3:.4f} mm "
        f"({2 * a10 / PHANTOM_RESOLUTION_M:.2f} phantom h across its diameter); "
        f"az_ref {az_ref:.6f} deg"
    )

    all_tags = global_cell_tag_set(msh, cell_tags)
    rho_field = build_density_field(
        msh,
        PHANTOM_RHO_KG_PER_M3,
        cell_tags=cell_tags,
        density_map={int(t): 0.0 for t in sorted(all_tags) if int(t) != PHANTOM_CELL_TAG},
    )

    containment = []

    def contained(c):
        rr = float(np.hypot(c[0] - centre[0], c[1] - centre[1]))
        radial = rr + a10 - (radius - CONTAINMENT_MARGIN_M)
        axial = abs(c[2] - z_c) + a10 - (half_height - CONTAINMENT_MARGIN_M)
        return max(radial, axial)  # <= 0 means contained with the margin

    def ball(e, c, label):
        c = tuple(float(v) for v in c)
        containment.append((label, c, contained(c)))
        t = time.perf_counter()
        out = mass_averaged_sar(
            e,
            sigma=sigma,
            rho=rho_field,
            center=c,
            radius=a10,
            comm=comm,
            quadrature_degree=QUADRATURE_DEGREE,
        )
        # MAX-reduced: the reduced-lattice STOP decision must agree on every rank.
        out["wall_s"] = comm.allreduce(time.perf_counter() - t, op=MPI.MAX)
        say(
            f"  ball {label:<24s} at ({c[0] * 1e3:8.3f}, {c[1] * 1e3:8.3f}, "
            f"{c[2] * 1e3:8.3f}) mm: SAR10g {out['averaged_sar_w_per_kg']:.9e} W/kg, "
            f"mass {out['mass_kg'] * 1e3:.6f} g, {out['wall_s']:.2f} s"
        )
        return out

    # ---- the candidate lattice ---------------------------------------------
    t_sar = time.perf_counter()
    phi = np.radians(az_ref)
    lattice = [
        (r, dz, (r * np.cos(phi), r * np.sin(phi), z_c + dz))
        for dz in (0.0,) + tuple(d for d in LATTICE_DZ_M if d != 0.0)
        for r in LATTICE_R_M
    ]
    reads = {}
    reduced = False
    for idx, (r, dz, c) in enumerate(lattice):
        if reduced and dz != 0.0:
            continue
        reads[(r, dz)] = ball(e_ccw, c, f"lattice r={r * 1e3:.0f} dz={dz * 1e3:+.0f}")
        if idx == 0 and reads[(r, dz)]["wall_s"] > FIRST_BALL_STOP_S:
            reduced = True
            say(
                f"REDUCED LATTICE: first ball {reads[(r, dz)]['wall_s']:.2f} s > "
                f"{FIRST_BALL_STOP_S:.0f} s — z = z_c row only"
            )
    coords = {(r, dz): c for r, dz, c in lattice}
    key_star = max(reads, key=lambda k: reads[k]["averaged_sar_w_per_kg"])
    c_star = np.array([coords[key_star]])
    sar_star = reads[key_star]["averaged_sar_w_per_kg"]

    # ---- (ii) C16 ------------------------------------------------------------
    step_deg = 360.0 / (len(port_ids) // 2)
    c16 = {}
    for m in range(1, len(port_ids) // 2):
        cm = _rotate_z(c_star, np.radians(m * step_deg))[0]
        s = ball(e_ccw, cm, f"C16 R_{m}")["averaged_sar_w_per_kg"]
        c16[m] = abs(s - sar_star) / sar_star
    worst_m = max(c16, key=c16.get)

    # ---- (iii) mirror ----------------------------------------------------------
    c_mirror = _mirror_xy(c_star, az_ref)[0]
    sar_mirror_cw = ball(e_cw, c_mirror, "mirror cw(Mc*)")["averaged_sar_w_per_kg"]
    mirror = abs(sar_mirror_cw - sar_star) / sar_star

    # ---- negative control: single-drive P17 at c* and its C4 images ----------
    control_sar = {0: ball(e_p17, c_star[0], "control P17 c*")["averaged_sar_w_per_kg"]}
    for m in CONTROL_IMAGES:
        cm = _rotate_z(c_star, np.radians(m * step_deg))[0]
        control_sar[m] = ball(e_p17, cm, f"control P17 R_{m}")["averaged_sar_w_per_kg"]
    control = {
        m: abs(control_sar[m] - control_sar[0]) / control_sar[0] for m in CONTROL_IMAGES
    }
    control_worst = max(control.values())

    # ---- (i) coverage identity -------------------------------------------------
    coverage_radius = float(np.hypot(radius, half_height) + COVERAGE_BALL_PAD_M)
    t = time.perf_counter()
    whole = mass_averaged_sar(
        e_ccw,
        sigma=sigma,
        rho=rho_field,
        center=tuple(float(v) for v in centre),
        radius=coverage_radius,
        comm=comm,
        quadrature_degree=QUADRATURE_DEGREE,
    )
    tagged = mean_sar(
        e_ccw,
        sigma=sigma,
        rho=PHANTOM_RHO_KG_PER_M3,
        cell_tags=cell_tags,
        subdomain_ids=PHANTOM_CELL_TAG,
        comm=comm,
    )
    t_cov = time.perf_counter() - t
    power_miss = abs(whole["dissipated_power_w"] / tagged["dissipated_power_w"] - 1.0)
    mass_miss = abs(whole["mass_kg"] / (PHANTOM_RHO_KG_PER_M3 * tagged["volume_m3"]) - 1.0)
    t_sar = time.perf_counter() - t_sar
    rss_final = rss_gib()

    if comm.rank == 0:
        print(
            f"[WF-7 step3] nine-ball location table (ccw drive, az_ref {az_ref:.4f} deg"
            f"{', REDUCED LATTICE' if reduced else ''}):",
            flush=True,
        )
        for (r, dz), out in sorted(reads.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            print(
                f"[WF-7 step3]   r = {r * 1e3:4.0f} mm, z = z_c{dz * 1e3:+5.0f} mm: SAR10g "
                f"{out['averaged_sar_w_per_kg']:.9e} W/kg, mass {out['mass_kg'] * 1e3:.6f} g, "
                f"{out['wall_s']:.2f} s{'   <- c*' if (r, dz) == key_star else ''}",
                flush=True,
            )
        for m in sorted(c16):
            print(
                f"[WF-7 step3]   (ii) C16 R_{m:<2d} ({m * step_deg:6.1f} deg): "
                f"|SAR10g(R c*) - SAR10g(c*)|/SAR10g(c*) = {c16[m] * 100:.4f}%",
                flush=True,
            )
        print(
            f"[WF-7 step3] c* = r {key_star[0] * 1e3:.0f} mm, z = z_c{key_star[1] * 1e3:+.0f} mm "
            f"({c_star[0][0] * 1e3:.3f}, {c_star[0][1] * 1e3:.3f}, {c_star[0][2] * 1e3:.3f}) mm, "
            f"SAR10g(c*) {sar_star:.9e} W/kg\n"
            f"[WF-7 step3] (ii) worst C16 {c16[worst_m] * 100:.4f}% at R_{worst_m} "
            f"(ASSERTED <= C4_COVARIANCE_BAND {C4_COVARIANCE_BAND * 100:.1f}%)\n"
            f"[WF-7 step3] (iii) mirror SAR10g_cw(Mc*) {sar_mirror_cw:.9e} vs SAR10g_ccw(c*): "
            f"{mirror * 100:.4f}% (ASSERTED <= {C4_COVARIANCE_BAND * 100:.1f}%)\n"
            f"[WF-7 step3] (i) coverage ball radius {coverage_radius * 1e3:.4f} mm (clear of "
            f"the conductor: < {(F_HUMAN_RING_RADIUS - CONDUCTOR_CLEARANCE_M) * 1e3:.1f} mm): "
            f"power {whole['dissipated_power_w']:.12e} W vs tagged "
            f"{tagged['dissipated_power_w']:.12e} W, rel {power_miss:.3e}; mass "
            f"{whole['mass_kg']:.12e} kg vs rho*V {PHANTOM_RHO_KG_PER_M3 * tagged['volume_m3']:.12e} "
            f"kg, rel {mass_miss:.3e} (ASSERTED <= EXACT_IDENTITY_RTOL {EXACT_IDENTITY_RTOL:g}); "
            f"{t_cov:.2f} s\n"
            f"[WF-7 step3] whole-phantom mean SAR (ccw) {tagged['mean_sar_w_per_kg']:.9e} W/kg "
            f"over {tagged['volume_m3']:.9e} m^3 (printed)\n"
            f"[WF-7 step3] negative control (PREDICTED >> {C4_COVARIANCE_BAND * 100:.1f}%, "
            f"never asserted): single-drive {CONTROL_PORT} SAR10g at c* "
            f"{control_sar[0]:.6e} W/kg, C4 images "
            + ", ".join(f"R_{m} {control[m] * 100:.4f}%" for m in CONTROL_IMAGES)
            + f"; spread {control_worst * 100:.4f}% ({control_worst / max(c16[worst_m], 1e-300):.1f}x "
            f"the ccw worst {c16[worst_m] * 100:.4f}%)\n"
            f"[WF-7 step3] step 2's |B1+| on the refined mesh (printed): worst C16 "
            f"{case['c16'][case['worst_m']] * 100:.4f}% at R_{case['worst_m']}, mirror "
            f"{case['mirror'] * 100:.4f}%, {case['n_valid']}/{case['points'].shape[0]} valid "
            f"sample points, exact identity {case['identity_dev']:.3e}\n"
            f"[WF-7 step3] PRICE: build {build_s:.2f} s, sweep+case "
            f"{t_sweep_done - t_window - build_s:.2f} s, SAR phase {t_sar:.2f} s "
            f"({len(containment) + 1} balls), window {time.perf_counter() - t_window:.2f} s "
            f"wall at -n {comm.size}; summed ru_maxrss {rss_after_sweep:.3f} GiB after the "
            f"sweep, {rss_final:.3f} GiB at the end",
            flush=True,
        )

    return {
        "c16": c16,
        "worst_m": worst_m,
        "mirror": mirror,
        "band": C4_COVARIANCE_BAND,
        "power_miss": power_miss,
        "mass_miss": mass_miss,
        "rtol": EXACT_IDENTITY_RTOL,
        "containment": containment,
        "coverage_radius": coverage_radius,
        "conductor_limit": F_HUMAN_RING_RADIUS - CONDUCTOR_CLEARANCE_M,
        "reads": reads,
    }


@complex_only
def test_i_coverage_identity(sar10g_case):
    """**(i)** the whole-phantom ball reproduces the tagged integral (power, mass)."""
    c = sar10g_case
    assert c["coverage_radius"] < c["conductor_limit"], (
        f"coverage ball {c['coverage_radius']:.6f} m reaches within "
        f"{CONDUCTOR_CLEARANCE_M} m of the conductor"
    )
    assert c["power_miss"] <= c["rtol"], f"power {c['power_miss']:.3e} > {c['rtol']:g}"
    assert c["mass_miss"] <= c["rtol"], f"mass {c['mass_miss']:.3e} > {c['rtol']:g}"


@complex_only
def test_ii_sar10g_c16_invariant(sar10g_case):
    c = sar10g_case
    worst = c["c16"][c["worst_m"]]
    assert worst <= c["band"], (
        f"10 g SAR not C16-invariant: R_{c['worst_m']} {worst * 100:.4f}% > "
        f"{c['band'] * 100:.1f}%"
    )


@complex_only
def test_iii_sar10g_mirror(sar10g_case):
    c = sar10g_case
    assert c["mirror"] <= c["band"], (
        f"mirror {c['mirror'] * 100:.4f}% > {c['band'] * 100:.1f}%"
    )


@complex_only
def test_iv_every_ball_contained(sar10g_case):
    bad = [(lab, excess) for lab, _c, excess in sar10g_case["containment"] if excess > 0.0]
    assert not bad, f"balls outside the phantom (1 mm margin): {bad}"
