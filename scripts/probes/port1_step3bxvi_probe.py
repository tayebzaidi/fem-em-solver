"""`PORT-1` step 3b-xvi — gap-region h-refinement of the terminal-to-terminal estimator.

Not a test.  Two modes, run as two separate harness commands:

``mesh``
    Builds the gapped padding-0.08 fixture twice — the landed sizing and the
    same sizing plus a **local** gap-box size field (``gap_box_resolution``) —
    and prints, for each: cell count, the measured cells-across-arc and
    cells-across-overhang the adjudication only ever inferred, the gap-box
    volume identity (1.000000000000 on record), the port facet tags, and the
    cell count *outside* the gap boxes.  No solve is bought until this has
    priced the refined mesh.

``solve``
    One σ = 800 S/m solve on each mesh — the production ladder's own rung,
    driven at gap ``GAP_TAGS[0]`` — and reads the terminal-to-terminal
    estimator on the record's ``I_cond`` normalisation.  The unrefined arm is
    the fixture-identity anchor: it must reproduce ``0.894543 × ωM₁₂``.

Pre-registered bands (§7 step 3b-xvi, adjudication decision (3)):

* |Δ| < 0.5 pp   ⇒ feed discretisation exonerated, offset is gap physics;
* |Δ| ≥ 0.5 pp   ⇒ feed discretisation owns part of the offset.

Either band proceeds; neither loops back.  Negative control: the cell count
outside the gap boxes **dilated by ``CONTROL_COLLAR_M`` = 5 mm** must move
< 5%, or the refinement is not local and the PEC-box deficit is no longer
common-mode with the unrefined record (re-pointed from the undilated boxes by
the 2026-08-12 10:30 daily review; see ``CONTROL_COLLAR_M``, and the undilated
count is still printed, never gated).  The closed-loop control (0.922423) is
**not** re-solved — a gap-local size field cannot touch its mesh — and is cited
from the record.

Run (complex build required for ``solve``)::

    docker compose exec -T fem-em-solver bash -lc \\
      'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 590 \\
       mpiexec -n 2 python3 scripts/probes/port1_step3bxvi_probe.py solve'
"""

from __future__ import annotations

import sys
import time

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import mesh as dmesh
from dolfinx.cpp import mesh as dcppmesh

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.constants import MU_0

from tests.validation.test_port_gap_voltage_impedance import (
    AIR_PADDING,
    DRIVE_CURRENT_A,
    FREQUENCY_HZ,
    GAP_ANGLE,
    GAP_ARC_RESOLUTION,
    GAP_BURIAL,
    GAP_OVERHANG,
    GAP_TAGS,
    H_FAR,
    H_WIRE,
    MAJOR_RADIUS,
    MINOR_RADIUS,
    OMEGA,
    PATH_QUADRATURE_GATE_ORDERS,
    PORT_DISC_AREA_EXACT_M2,
    PORT_FACET_TAGS,
    PRODUCTION_LADDER_DRIVEN_COLUMN,
    SEPARATION,
    SIGMA_WIRE_S_PER_M,
    WIRE_TAGS,
    _azimuthal_unit,
    _gap_drive,
    _gap_half_extents,
    _path_voltage,
    _port_facet_measure,
    _reduce,
    _side_indicator,
    _tag_measure,
    _tag_volume,
    mutual_inductance,
)

# The refinement: halve the conductor field's h inside the gap boxes.  The arc
# tube (4 * 3e-4 = 1.2e-3 radius) never reaches the tube wall at 5e-3, so the
# box's transverse structure — the overhang shell included — is sized at
# H_WIRE = 2.5e-3 today.
GAP_BOX_RESOLUTION = 1.25e-3
# Fallback factor if the mesh probe prices the refined solve out of the
# envelope: halve the refinement, never the region (§7).
GAP_BOX_RESOLUTION_FALLBACK = 1.875e-3

# Cell-count stop rule for the refined mesh, pre-registered here rather than
# after the fact.  178 055 cells is the unrefined record; 237 926 once died in
# MUMPS at 180 s on the *ungapped* padding-0.12 fixture (step 1), and this
# fixture's solves run ~25 s at 178 k.
CELL_CEILING = 350_000

# The record this step moves, from step 3b-xiv (re-reproduced by 3b-xv):
# estimator on the I_cond normalisation, gapped, sigma = 800, padding 0.08.
ESTIMATOR_RECORD = 0.894543
# Cited, not re-solved: the closed sigma = 0 reaction control and the deviation.
CONTROL_RECORD = 0.922423
DEVIATION_RECORD = -3.0224e-02

# Bands.
BAND_PP = 0.5          # estimator movement, percentage points of omega*M12
OUTSIDE_BAND = 0.05    # cells outside the (dilated) gap boxes may move < 5%
# The locality control's region, re-pointed by the 2026-08-12 10:30 daily
# review from the bare gap boxes to boxes dilated by this collar, same < 5%
# band.  Grounds (§7, and the 06:00 slot's own calibration): a size field
# stepping h_box = 6.0e-4 to the conductor field's h_wire = 2.5e-3 cannot do it
# in zero cells, so gmsh lays a mandatory gradation shell just outside the box
# and the bare-box control counts it as "outside" (+16.3159% at h_box = 6.0e-4
# even with the Thickness capped at 5 mm).  Counted outside a 5 mm-dilated box
# the same refinement moves the mesh -0.1658% (-0.3098% at 10 mm, -0.2937% at
# 20 mm) — every added cell sits within 5 mm of the box, so the claim this
# control protects (the PEC-box deficit at the wall 0.08 m away stays
# common-mode with the unrefined record) is what the dilated count tests.  As
# written the bare-box control admitted only refinements too weak to answer the
# question: the 1.0430x arm passed, the 1.5223x arm failed.  5 mm is the
# smallest measured collar that already contains every added cell.  The band
# itself does not move.
CONTROL_COLLAR_M = 5.0e-3
# Diagnostic collar widths [m] for the same count on a dilated box; the
# CONTROL_COLLAR_M entry is the gated one, the rest gate nothing and are
# reported beside it so a review can see how far the added cells reach.
COLLAR_PADS_M = (5.0e-3, 1.0e-2, 2.0e-2)
VOLUME_IDENTITY_TOL = 1.0e-9


def _build(comm, gap_box_resolution):
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
        gap_box_resolution=gap_box_resolution,
        comm=comm,
    )
    return msh, cell_tags, facet_tags, time.perf_counter() - t0


def _axis_distance(points):
    """Distance from the nearer gap box's tube axis (the centreline circle)."""
    z_offset = SEPARATION / 2.0
    rho = np.sqrt(points[:, 0] ** 2 + points[:, 1] ** 2)
    out = None
    for z_c in (-z_offset, z_offset):
        d = np.sqrt((rho - MAJOR_RADIUS) ** 2 + (points[:, 2] - z_c) ** 2)
        out = d if out is None else np.minimum(out, d)
    return out


def _gather(comm, values):
    """Rank-local arrays are not a distribution — concatenate before any median."""
    chunks = comm.allgather(np.asarray(values, dtype=float))
    if not chunks:
        return np.zeros(0)
    return np.concatenate(chunks) if len(chunks) > 1 else np.asarray(chunks[0])


def _mesh_metrics(comm, msh, cell_tags, facet_tags):
    tdim = msh.topology.dim
    n_local = msh.topology.index_map(tdim).size_local
    ncells = comm.allreduce(n_local, op=MPI.SUM)

    owned = np.arange(n_local, dtype=np.int32)
    # dolfinx 0.7.2 exposes the cell-size helper on the C++ side only.
    h_all = dcppmesh.h(msh._cpp_object, tdim, owned)
    mids = dmesh.compute_midpoints(msh, tdim, owned)

    # Gap-box cells, owned only (cell_tags carries ghosts too).
    tagged = cell_tags.indices[np.isin(cell_tags.values, GAP_TAGS)]
    gap_local = tagged[tagged < n_local]
    h_gap = h_all[gap_local]
    d_gap = _axis_distance(mids[gap_local])

    tube = 4.0 * GAP_ARC_RESOLUTION
    h_tube = _gather(comm, h_gap[d_gap < tube])
    # The wall band: the outer half of the box cross-section, which is where
    # the conductor wall and the `gap_overhang` shell outside it live.
    h_wall = _gather(comm, h_gap[d_gap > 0.5 * MINOR_RADIUS])
    h_gap_all = _gather(comm, h_gap)

    # Cells outside both gap boxes — the common-mode negative control.
    half_xz, half_y = _gap_half_extents()
    z_offset = SEPARATION / 2.0
    inside = np.zeros(mids.shape[0], dtype=bool)
    for z_c in (-z_offset, z_offset):
        inside |= (
            (np.abs(mids[:, 0] - MAJOR_RADIUS) <= half_xz)
            & (np.abs(mids[:, 1]) <= half_y)
            & (np.abs(mids[:, 2] - z_c) <= half_xz)
        )
    n_outside = comm.allreduce(int((~inside).sum()), op=MPI.SUM)

    # Diagnostic only — the pre-registered control above is untouched.  A size
    # field that steps from `h_box` to the conductor field's `h_wire` cannot do
    # it inside zero cells: gmsh lays a gradation collar just outside the box
    # whatever the `Thickness` says, and those cells are counted "outside" by
    # the control.  Counting again at a few collar widths separates that
    # unavoidable collar from a refinement that genuinely leaks toward the PEC
    # wall (0.08 m away), which is what the common-mode claim is about.
    outside_dilated = {}
    for pad in COLLAR_PADS_M:
        inside_pad = np.zeros(mids.shape[0], dtype=bool)
        for z_c in (-z_offset, z_offset):
            inside_pad |= (
                (np.abs(mids[:, 0] - MAJOR_RADIUS) <= half_xz + pad)
                & (np.abs(mids[:, 1]) <= half_y + pad)
                & (np.abs(mids[:, 2] - z_c) <= half_xz + pad)
            )
        outside_dilated[pad] = comm.allreduce(
            int((~inside_pad).sum()), op=MPI.SUM
        )

    # Identities, before any estimator is trusted.
    gap_volumes = [_tag_volume(msh, cell_tags, t, comm) for t in GAP_TAGS]
    volume_analytic = 8.0 * half_xz**2 * half_y
    volume_ratios = [v / volume_analytic for v in gap_volumes]

    local_ftags = set(int(v) for v in np.unique(facet_tags.values))
    all_ftags = sorted(set().union(*comm.allgather(local_ftags)))

    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()
    chi_gap = _side_indicator(msh, cell_tags, GAP_TAGS)
    disc_areas = []
    for t in PORT_FACET_TAGS:
        dS_port = _port_facet_measure(msh, facet_tags, t)
        both = chi_gap("+") + chi_gap("-")
        disc_areas.append(float(np.real(_reduce(both * dS_port, comm))))

    arc_length = MAJOR_RADIUS * GAP_ANGLE
    med_tube = float(np.median(h_tube)) if h_tube.size else float("nan")
    med_wall = float(np.median(h_wall)) if h_wall.size else float("nan")
    return {
        "cells": ncells,
        "cells_outside_gap": n_outside,
        "cells_outside_dilated": outside_dilated,
        "h_tube_median": med_tube,
        "h_wall_median": med_wall,
        "h_gap_median": float(np.median(h_gap_all)) if h_gap_all.size else float("nan"),
        "h_gap_min": float(h_gap_all.min()) if h_gap_all.size else float("nan"),
        "h_gap_max": float(h_gap_all.max()) if h_gap_all.size else float("nan"),
        "n_gap_cells": int(h_gap_all.size),
        "cells_across_arc": arc_length / med_tube,
        "cells_across_overhang": GAP_OVERHANG / med_wall,
        "gap_volume_ratios": volume_ratios,
        "facet_tags": all_ftags,
        "disc_area_ratios": [a / PORT_DISC_AREA_EXACT_M2 for a in disc_areas],
        "half_xz": half_xz,
        "half_y": half_y,
    }


def _report_metrics(comm, label, m, t_mesh):
    if comm.rank != 0:
        return
    print(
        f"\n[3b-xvi {label}] {m['cells']} cells, mesh {t_mesh:.1f} s; "
        f"{m['cells_outside_gap']} of them outside the gap boxes; "
        f"{m['n_gap_cells']} gap-box cells "
        f"(h median {m['h_gap_median']:.4e}, min {m['h_gap_min']:.4e}, "
        f"max {m['h_gap_max']:.4e} m)",
        flush=True,
    )
    print(
        f"[3b-xvi {label}] measured resolution: cells_across_arc = "
        f"{m['cells_across_arc']:.2f} (arc {MAJOR_RADIUS * GAP_ANGLE:.4e} m / "
        f"median h {m['h_tube_median']:.4e} m in the r < "
        f"{4.0 * GAP_ARC_RESOLUTION:.1e} m tube); cells_across_overhang = "
        f"{m['cells_across_overhang']:.4f} (overhang {GAP_OVERHANG:.1e} m / "
        f"median h {m['h_wall_median']:.4e} m in the wall band)",
        flush=True,
    )
    print(
        f"[3b-xvi {label}] identities: gap-box volume ratios "
        + ", ".join(f"{r:.12f}" for r in m["gap_volume_ratios"])
        + f"; facet tags {m['facet_tags']}; port-disc meshed/exact "
        + ", ".join(f"{r:.9f}" for r in m["disc_area_ratios"]),
        flush=True,
    )


def _check_identities(label, m, failures):
    for k, r in enumerate(m["gap_volume_ratios"]):
        if abs(r - 1.0) >= VOLUME_IDENTITY_TOL:
            failures.append(
                f"{label}: gap box {GAP_TAGS[k]} meshed/analytic volume "
                f"{r:.12f}, off identity by {r - 1.0:+.3e} >= "
                f"{VOLUME_IDENTITY_TOL:.1e}"
            )
    for t in PORT_FACET_TAGS:
        if t not in m["facet_tags"]:
            failures.append(f"{label}: port facet tag {t} absent from the mesh")


def _one_solve(comm, label, msh, cell_tags):
    """The production ladder's sigma = 800 rung, driven at GAP_TAGS[col]."""
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    col = PRODUCTION_LADDER_DRIVEN_COLUMN
    half_xz, half_y = _gap_half_extents()
    gap_length = 2.0 * half_y
    gap_volume = _tag_volume(msh, cell_tags, GAP_TAGS[col], comm)
    gap_area = gap_volume / gap_length
    wire_volume = _tag_volume(msh, cell_tags, WIRE_TAGS[col], comm)
    arc_length = wire_volume / (np.pi * MINOR_RADIUS**2)

    x_ufl = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_unit(x_ufl)
    y_hat = ufl.as_vector([0.0, 1.0, 0.0])

    j = DRIVE_CURRENT_A / gap_area
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            tag: HomogeneousMaterial(
                sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0
            )
            for tag in WIRE_TAGS
        },
        boundary_condition="pec_zero_tangential_a",
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=_gap_drive(j),
        subdomain_ids=[GAP_TAGS[col]],
        project_source=False,
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    e = fields.e_complex
    i_impressed = (
        _reduce(
            ufl.inner(_gap_drive(j)(x_ufl), y_hat)
            * _tag_measure(msh, cell_tags, GAP_TAGS[col]),
            comm,
        )
        / gap_length
    )
    i_conduction = (
        SIGMA_WIRE_S_PER_M
        * _reduce(
            ufl.inner(e, phi_hat) * _tag_measure(msh, cell_tags, WIRE_TAGS[col]),
            comm,
        )
        / arc_length
    )
    v_undriven = _path_voltage(e, 1 - col, PATH_QUADRATURE_GATE_ORDERS[-1], comm)
    v_coarse = _path_voltage(e, 1 - col, PATH_QUADRATURE_GATE_ORDERS[0], comm)
    omega_m = OMEGA * mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    z_cond = v_undriven / i_conduction
    z_impressed = v_undriven / i_impressed
    rec = {
        "solve_time": t_solve,
        "gap_area": gap_area,
        "arc_length": arc_length,
        "i_impressed": i_impressed,
        "i_conduction": i_conduction,
        "conduction_ratio": abs(i_conduction) / abs(i_impressed),
        "v_undriven": v_undriven,
        "quadrature_drift": abs(v_undriven - v_coarse) / abs(v_undriven),
        "estimator_conduction": abs(z_cond.imag) / omega_m,
        "estimator_impressed": abs(z_impressed.imag) / omega_m,
        "omega_m": omega_m,
    }
    if comm.rank == 0:
        print(
            f"\n[3b-xvi {label}] solve {t_solve:.1f} s; I' = "
            f"{i_impressed:+.6e} A, I_cond = {i_conduction.real:+.6e}"
            f"{i_conduction.imag:+.6e}j A, |I_cond/I'| = "
            f"{rec['conduction_ratio']:.6f}; V_undriven = {v_undriven:+.9e} V "
            f"(quadrature drift {PATH_QUADRATURE_GATE_ORDERS[0]}->"
            f"{PATH_QUADRATURE_GATE_ORDERS[-1]}: {rec['quadrature_drift']:.3e})",
            flush=True,
        )
        print(
            f"[3b-xvi {label}] estimator = "
            f"{rec['estimator_conduction']:.6f} x omega*M12 (I_cond "
            f"normalisation, the record's) / {rec['estimator_impressed']:.6f} "
            "(impressed)",
            flush=True,
        )
    return rec


def main() -> int:
    comm = MPI.COMM_WORLD
    mode = sys.argv[1] if len(sys.argv) > 1 else "mesh"
    if mode not in ("mesh", "solve"):
        raise SystemExit(f"usage: {sys.argv[0]} [mesh|solve]")
    h_box = GAP_BOX_RESOLUTION
    if len(sys.argv) > 2:
        h_box = float(sys.argv[2])
    failures = []

    if comm.rank == 0:
        delta_skin = np.sqrt(2.0 / (OMEGA * MU_0 * SIGMA_WIRE_S_PER_M))
        print(
            f"[3b-xvi] mode {mode}, gapped padding {AIR_PADDING} m, h_wire = "
            f"{H_WIRE:.3e}, h_arc = {GAP_ARC_RESOLUTION:.3e}, h_box = "
            f"{h_box:.3e} m; sigma = {SIGMA_WIRE_S_PER_M:.1e} S/m "
            f"(delta = {delta_skin:.4e} m); record estimator "
            f"{ESTIMATOR_RECORD:.6f}, control {CONTROL_RECORD:.6f} (cited, not "
            f"re-solved), deviation {DEVIATION_RECORD:+.4e}",
            flush=True,
        )

    arms = {}
    for label, box_res in (("unrefined", None), ("refined", h_box)):
        msh, cell_tags, facet_tags, t_mesh = _build(comm, box_res)
        m = _mesh_metrics(comm, msh, cell_tags, facet_tags)
        _report_metrics(comm, label, m, t_mesh)
        _check_identities(label, m, failures)
        arms[label] = {"metrics": m, "mesh_time": t_mesh}
        if mode == "solve" and not failures:
            arms[label]["solve"] = _one_solve(comm, label, msh, cell_tags)
        del msh, cell_tags, facet_tags

    u, r = arms["unrefined"]["metrics"], arms["refined"]["metrics"]
    # The gated control: outside the CONTROL_COLLAR_M-dilated gap boxes.
    u_ctl = u["cells_outside_dilated"][CONTROL_COLLAR_M]
    r_ctl = r["cells_outside_dilated"][CONTROL_COLLAR_M]
    outside_move = r_ctl / u_ctl - 1.0
    raw_move = r["cells_outside_gap"] / u["cells_outside_gap"] - 1.0
    if comm.rank == 0:
        print(
            f"\n[3b-xvi] cell counts {u['cells']} -> {r['cells']} "
            f"({r['cells'] / u['cells']:.4f}x, ceiling {CELL_CEILING}); "
            f"CONTROL: cells outside the gap boxes dilated by "
            f"{CONTROL_COLLAR_M * 1e3:.0f} mm {u_ctl} -> {r_ctl} "
            f"({outside_move:+.4%}, band < {OUTSIDE_BAND:.0%}) — the "
            f"common-mode PEC-box claim",
            flush=True,
        )
        print(
            f"[3b-xvi] for the record, never gated (gmsh's mandatory gradation "
            f"collar lives here): cells outside the *undilated* gap boxes "
            f"{u['cells_outside_gap']} -> {r['cells_outside_gap']} "
            f"({raw_move:+.4%})",
            flush=True,
        )
        for pad in COLLAR_PADS_M:
            u_pad = u["cells_outside_dilated"][pad]
            r_pad = r["cells_outside_dilated"][pad]
            role = "GATED" if pad == CONTROL_COLLAR_M else "gates nothing"
            print(
                f"[3b-xvi] diagnostic ({role}): outside the gap boxes "
                f"dilated by {pad * 1e3:.0f} mm, {u_pad} -> {r_pad} "
                f"({r_pad / u_pad - 1.0:+.4%})",
                flush=True,
            )
        print(
            f"[3b-xvi] cells_across_arc {u['cells_across_arc']:.2f} -> "
            f"{r['cells_across_arc']:.2f}; cells_across_overhang "
            f"{u['cells_across_overhang']:.4f} -> "
            f"{r['cells_across_overhang']:.4f}",
            flush=True,
        )
    if abs(outside_move) >= OUTSIDE_BAND:
        failures.append(
            f"the refinement is not local: cells outside the "
            f"{CONTROL_COLLAR_M * 1e3:.0f} mm-dilated gap boxes moved "
            f"{outside_move:+.4%}, band < {OUTSIDE_BAND:.0%}"
        )

    if mode == "mesh":
        if comm.rank == 0:
            verdict = (
                "STOP — over the cell ceiling; re-run with the fallback "
                f"h_box = {GAP_BOX_RESOLUTION_FALLBACK:.3e}"
                if r["cells"] > CELL_CEILING
                else "clear — the solve arm may be bought"
            )
            print(f"[3b-xvi] mesh-only verdict: {verdict}", flush=True)
        if r["cells"] > CELL_CEILING:
            failures.append(
                f"refined mesh {r['cells']} cells > ceiling {CELL_CEILING}"
            )
    else:
        est_u = arms["unrefined"]["solve"]["estimator_conduction"]
        est_r = arms["refined"]["solve"]["estimator_conduction"]
        anchor_pp = 100.0 * (est_u - ESTIMATOR_RECORD)
        delta_pp = 100.0 * (est_r - est_u)
        band = "under-resolved" if abs(delta_pp) >= BAND_PP else "converged at the feed"
        if comm.rank == 0:
            print(
                f"\n[3b-xvi] ANCHOR: unrefined estimator {est_u:.6f} vs the "
                f"{ESTIMATOR_RECORD:.6f} on record, {anchor_pp:+.4f} pp",
                flush=True,
            )
            print(
                f"[3b-xvi] READING: refined {est_r:.6f} vs unrefined "
                f"{est_u:.6f} = {delta_pp:+.4f} pp against the "
                f"{BAND_PP:.1f} pp band => band ({band}); against the cited "
                f"control {CONTROL_RECORD:.6f} the refined deviation is "
                f"{est_r / CONTROL_RECORD - 1.0:+.4e} "
                f"(record {DEVIATION_RECORD:+.4e})",
                flush=True,
            )
        # The anchor is a hard identity: a fixture that does not reproduce its
        # own record has nothing to report about the refinement.
        if abs(anchor_pp) >= 0.01:
            failures.append(
                f"fixture identity: unrefined estimator {est_u:.6f} does not "
                f"reproduce the record {ESTIMATOR_RECORD:.6f} "
                f"({anchor_pp:+.4f} pp >= 0.01 pp)"
            )

    if comm.rank == 0:
        if failures:
            for f in failures:
                print(f"[3b-xvi] FAIL: {f}", flush=True)
        else:
            print("[3b-xvi] all identities and controls PASS", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
