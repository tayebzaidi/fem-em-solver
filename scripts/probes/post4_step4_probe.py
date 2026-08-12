"""`POST-4` step 4 — bound the Lagrange-P1 interpolant artifact on the export paths.

Measurement only: no ``src/`` change, no gate, no tolerance moved.  Step 1
measured that the P1 interpolant of a non-conforming field can sit **56x** off
its source at a centerline point even at ``-n 1``
(``20260811T140549Z_POST-4-step1-attribution.log``); step 3 took the *printed
diagnostics* off that path.  Every example's XDMF/VTX export still ships exactly
such interpolants, so this probe asks how big the artifact is on the export
path itself, and where it lives.

The hypothesis under test: the disagreement is a **vertex** phenomenon.  A P1
interpolant carries one dof per vertex; for a field that is not continuous
there (N1curl is only tangentially continuous across faces, DG is continuous
nowhere) that dof is written by whichever adjacent cell writes last locally, so
the interpolant at a shared vertex is a partition-dependent pick among several
distinct cell traces.  In a cell *interior* — the midpoint is the cleanest
probe point — the P1 interpolant is a barycentric average of the four vertex
dofs of that one cell, so it should track the source to interpolation-error
scale, not artifact scale.

Sampled per field, at two point sets on the same solves:

* **MID** — cell midpoints (interior; no shared entity involved);
* **VTX** — mesh vertices (shared by all incident cells; the suspect locus).

Both sets are built partition-independently: every rank contributes its owned
midpoints / geometry nodes, rank 0 sorts them lexicographically and subsamples
evenly, and the resulting point array is broadcast.  The same array therefore
reaches every field and every rank count.

Reported per (field, point set): max and median of the pointwise relative
disagreement ``|lag - src| / max(|src|, floor)``, plus a scale-normalized
variant ``|lag - src| / rms(|src|)`` that is immune to near-zero denominators,
and the count of sampled points.

Negative control: a **conforming** source — the P1 interpolant itself, fed back
through ``interpolate`` into a second P1 space — must reproduce itself to
solver/round-off tolerance at both point sets.  A control that fails says the
probe machinery is wrong, not the export.

Run through the harness::

    scripts/testing/run_and_log.sh POST-4 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && PYTHONPATH=/workspace/src \\
      FEM_EM_REQUIRE_COMPLEX=1 timeout 300 mpiexec -n 2 python3 \\
      scripts/probes/post4_step4_probe.py'"

Exit code 0 iff every asserted anchor below holds.
"""

import sys

import numpy as np
import ufl
from mpi4py import MPI
from dolfinx import fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    MagnetostaticProblem,
    MagnetostaticSolver,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.materials import GelledSalinePhantomMaterial
from fem_em_solver.post import evaluate_vector_field_parallel
from fem_em_solver.utils.constants import MU_0

# examples/mri/01_coil_phantom_fields.py, debug preset — identical to the
# step-1 probe's fixture so the two runs are directly comparable.
RESOLUTION_M = 0.02
FREQUENCY_HZ = 127.74e6
FIELD_FLOOR = 1e-30
N_SAMPLE = 400  # per point set; the debug mesh has ~9k cells / ~1.8k vertices

MESH_PARAMS = {
    "coil_major_radius": 0.08,
    "coil_minor_radius": 0.01,
    "coil_separation": 0.08,
    "phantom_radius": 0.04,
    "phantom_height": 0.10,
    "air_padding": 0.04,
    "resolution": RESOLUTION_M,
}

# ---- anchors (PROJECT_PLAN §7, `POST-4` step 4) ---------------------------
# "assert midpoint <= 1% where vertex shows the on-record O(50x)".  The
# pointwise-relative statistic is reported as both max and median; the assert
# is on the **median**, because a pointwise relative error is unbounded wherever
# the source field passes through zero and a max over 400 points is a statement
# about the sample's worst denominator, not about the export.  The max is
# printed unasserted alongside, and the scale-normalized column (normalized by
# the sample RMS of |src|, which has no small-denominator failure mode) carries
# its own assert.
MID_MEDIAN_MAX = 0.01          # 1%, the entry's number
MID_SCALED_MAX = 0.01          # 1% of the field scale at midpoints
SEPARATION_MIN = 5.0           # vertex/midpoint scale-normalized median ratio
CONTROL_MAX = 1e-10            # conforming P1 -> P1 round-trip

# The hypothesis above was measured **REFUTED** on 2026-08-12 (log
# `20260812T003344Z_POST-4-step4-discrim-n2.log`, `-n 2`, 9261-cell debug
# mesh): midpoint relative medians are 5.117084e-01 / 5.247224e-01 /
# 2.018185e-01 for A / B / E — fifty times the 1% the entry expected — and the
# vertex/midpoint separations are 0.4185x / 0.4818x / 0.6835x, i.e. the
# vertices are *quieter* than the interiors, the opposite of the predicted
# O(50x).  The hypothesis check therefore reports a verdict and no longer sets
# the exit code (the entry's own "Negative result" clause: report, annotate,
# stop).  What the exit code enforces instead are the three facts the same run
# measured, each of which is a real regression guard:
#
#   1. CONTROL — a conforming (P1) source round-trips through the same
#      machinery exactly (measured 0.0, bound 1e-10);
#   2. DISCRIM — interpolating the *same* sources onto a **DG1** target, which
#      shares no dofs between cells, reproduces them to round-off (measured
#      3.370236e-17 / 0.0 / 0.0 scaled median at midpoints, bound 1e-14).  All
#      three sources are degree-1 discontinuous polynomials, so degree-1
#      interpolation error is exactly zero and **every** part of the P1
#      disagreement is the shared-vertex continuity constraint;
#   3. REFUTATION PIN — the artifact is present at the magnitude measured
#      (midpoint relative median >= 10%, vertex <= midpoint on the scaled
#      median).  If an export-path change ever collapses this, the pin fires
#      and forces a re-read of this entry rather than passing silently.
DISCRIM_MAX = 1e-14            # DG1 target vs source, scaled median
PIN_MID_MEDIAN_MIN = 0.10      # measured 0.2018 (E, the smallest of the three)


def mesh_fingerprint(mesh, comm):
    """Partition-independent fingerprint: global cell count + midpoint moments."""
    tdim = mesh.topology.dim
    n_local = mesh.topology.index_map(tdim).size_local
    cells = np.arange(n_local, dtype=np.int32)
    midpoints = mesh.geometry.x[mesh.geometry.dofmap[cells]].mean(axis=1)
    n_global = comm.allreduce(n_local, op=MPI.SUM)
    m1 = comm.allreduce(float(np.sum(midpoints)), op=MPI.SUM)
    m2 = comm.allreduce(float(np.sum(midpoints ** 2)), op=MPI.SUM)
    return n_global, m1, m2


def _collect_points(local_points, comm, n_sample):
    """Gather owned points, sort lexicographically, subsample evenly, broadcast.

    The sort makes the selection a function of the *geometry* only, so the same
    physical points are sampled at every rank count.
    """
    gathered = comm.gather(np.ascontiguousarray(local_points, dtype=np.float64), root=0)
    if comm.rank == 0:
        allpts = np.vstack([g for g in gathered if g.size])
        order = np.lexsort((allpts[:, 0], allpts[:, 1], allpts[:, 2]))
        allpts = allpts[order]
        if allpts.shape[0] > n_sample:
            idx = np.linspace(0, allpts.shape[0] - 1, n_sample).astype(np.int64)
            allpts = allpts[idx]
        out = np.ascontiguousarray(allpts)
    else:
        out = None
    return comm.bcast(out, root=0)


def build_point_sets(mesh, comm):
    """MID = owned cell midpoints; VTX = owned geometry nodes (P1 mesh: vertices)."""
    tdim = mesh.topology.dim
    n_cells = mesh.topology.index_map(tdim).size_local
    cells = np.arange(n_cells, dtype=np.int32)
    mids = mesh.geometry.x[mesh.geometry.dofmap[cells]].mean(axis=1)

    n_nodes = mesh.geometry.index_map().size_local
    verts = mesh.geometry.x[:n_nodes]

    return (
        _collect_points(mids, comm, N_SAMPLE),
        _collect_points(verts, comm, N_SAMPLE),
    )


def compare(label, tag, source, interpolant, points, comm):
    """Interpolant-vs-source disagreement at ``points``; returns a stats dict."""
    src_vals, src_valid = evaluate_vector_field_parallel(source, points, comm=comm)
    lag_vals, lag_valid = evaluate_vector_field_parallel(interpolant, points, comm=comm)
    if comm.rank != 0:
        return None

    valid = np.logical_and(np.asarray(src_valid, dtype=bool), np.asarray(lag_valid, dtype=bool))
    src = np.asarray(src_vals).reshape(points.shape[0], -1)[valid]
    lag = np.asarray(lag_vals).reshape(points.shape[0], -1)[valid]

    src_mag = np.linalg.norm(src, axis=1).astype(np.float64)
    diff_mag = np.linalg.norm(lag - src, axis=1).astype(np.float64)

    rel = diff_mag / np.maximum(src_mag, FIELD_FLOOR)
    rms = float(np.sqrt(np.mean(src_mag ** 2))) if src_mag.size else 0.0
    scaled = diff_mag / max(rms, FIELD_FLOOR)

    stats = {
        "n": int(valid.sum()),
        "n_invalid": int((~valid).sum()),
        "rel_max": float(np.max(rel)) if rel.size else 0.0,
        "rel_med": float(np.median(rel)) if rel.size else 0.0,
        "scaled_max": float(np.max(scaled)) if scaled.size else 0.0,
        "scaled_med": float(np.median(scaled)) if scaled.size else 0.0,
        "rms": rms,
    }
    print(
        f"DISAGREE {label:<10} {tag:<3} n={stats['n']:>4} invalid={stats['n_invalid']:>3} "
        f"rel_max={stats['rel_max']:.6e} rel_med={stats['rel_med']:.6e} "
        f"scaled_max={stats['scaled_max']:.6e} scaled_med={stats['scaled_med']:.6e} "
        f"rms_src={stats['rms']:.6e}",
        flush=True,
    )
    return stats


def main():
    comm = MPI.COMM_WORLD

    if comm.rank == 0:
        print("=" * 78)
        print(f"POST-4 step 4 probe — ranks={comm.size}")
        print(
            f"fixture: examples/mri/01 debug preset, resolution={RESOLUTION_M} m, "
            f"f={FREQUENCY_HZ:.6e} Hz; N_SAMPLE={N_SAMPLE} per point set"
        )
        print("=" * 78, flush=True)

    mesh, cell_tags, facet_tags = MeshGenerator.coil_phantom_domain(**MESH_PARAMS, comm=comm)
    n_global, m1, m2 = mesh_fingerprint(mesh, comm)
    if comm.rank == 0:
        print(f"MESH_FINGERPRINT cells={n_global} m1={m1:.12e} m2={m2:.12e}", flush=True)

    j_magnitude = 1.0 / (np.pi * 0.01 ** 2)

    def current_density(_x):
        return ufl.as_vector([0.0, 0.0, j_magnitude])

    mag_problem = MagnetostaticProblem(
        mesh=mesh, cell_tags=cell_tags, facet_tags=facet_tags, mu=MU_0
    )
    mag_solver = MagnetostaticSolver(mag_problem, degree=1)
    a_field = mag_solver.solve(
        current_density=current_density, subdomain_ids=[1, 2], gauge_penalty=1.0
    )
    b_field = mag_solver.compute_b_field()

    background = HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0)
    phantom = GelledSalinePhantomMaterial(
        sigma=0.72, epsilon_r=76.5, frequency_hz=FREQUENCY_HZ, mu_r=1.0
    )
    th_problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=FREQUENCY_HZ,
        material=background,
        cell_tags=cell_tags,
        facet_tags=facet_tags,
        phantom_material=phantom,
        phantom_tag=3,
    )
    th_solver = TimeHarmonicSolver(th_problem, degree=1)
    th_fields = th_solver.solve(
        current_density=current_density, subdomain_ids=[1, 2], gauge_penalty=1e-3
    )
    e_field = th_fields.e_imag

    # The export path, verbatim from examples/mri/01_coil_phantom_fields.py.
    v_lagrange = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    a_lag = fem.Function(v_lagrange, name="A")
    a_lag.interpolate(a_field)
    b_lag = fem.Function(v_lagrange, name="B")
    b_lag.interpolate(b_field)
    e_lag = fem.Function(v_lagrange, name="E")
    e_lag.interpolate(e_field)

    # Negative control: a conforming (P1) source through the same machinery.
    v_control = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    b_lag_rt = fem.Function(v_control, name="B_roundtrip")
    b_lag_rt.interpolate(b_lag)

    # Discriminator: the same degree-1 interpolation onto a **DG1** target,
    # which has no dofs shared between cells and therefore no vertex
    # convention at all.  Whatever disagreement survives on this path is
    # ordinary degree-1 interpolation error on this (deliberately coarse)
    # debug mesh; the excess of the P1 path over it is the shared-vertex
    # component the step-4 hypothesis was about.
    v_dg1 = fem.functionspace(mesh, ("DG", 1, (3,)))
    a_dg = fem.Function(v_dg1, name="A_dg")
    a_dg.interpolate(a_field)
    b_dg = fem.Function(v_dg1, name="B_dg")
    b_dg.interpolate(b_field)
    e_dg = fem.Function(v_dg1, name="E_dg")
    e_dg.interpolate(e_field)

    mid_points, vtx_points = build_point_sets(mesh, comm)
    if comm.rank == 0:
        print(
            f"POINTS mid={mid_points.shape[0]} vtx={vtx_points.shape[0]}",
            flush=True,
        )

    cases = [
        ("A_N1curl", a_field, a_lag),
        ("B_DG1", b_field, b_lag),
        ("E_N1curl", e_field, e_lag),
        ("A_toDG1", a_field, a_dg),
        ("B_toDG1", b_field, b_dg),
        ("E_toDG1", e_field, e_dg),
        ("CTRL_P1", b_lag, b_lag_rt),
    ]

    results = {}
    for label, source, interpolant in cases:
        for tag, points in (("MID", mid_points), ("VTX", vtx_points)):
            stats = compare(label, tag, source, interpolant, points, comm)
            if comm.rank == 0:
                results[(label, tag)] = stats

    if comm.rank != 0:
        return 0

    print("-" * 78, flush=True)
    failures = []

    # --- the step-4 hypothesis, evaluated and reported (not exit-code-bearing)
    for label in ("A_N1curl", "B_DG1", "E_N1curl"):
        mid = results[(label, "MID")]
        vtx = results[(label, "VTX")]
        sep = vtx["scaled_med"] / max(mid["scaled_med"], FIELD_FLOOR)
        held = (
            mid["rel_med"] <= MID_MEDIAN_MAX
            and mid["scaled_med"] <= MID_SCALED_MAX
            and sep >= SEPARATION_MIN
        )
        print(
            f"HYPOTHESIS {label:<10} mid_rel_med={mid['rel_med']:.6e} "
            f"mid_scaled_med={mid['scaled_med']:.6e} "
            f"vtx_scaled_med={vtx['scaled_med']:.6e} separation={sep:.4f}x "
            f"verdict={'CONFIRMED' if held else 'REFUTED'}",
            flush=True,
        )
        # Refutation pin — see the block comment on PIN_MID_MEDIAN_MIN.
        if mid["rel_med"] < PIN_MID_MEDIAN_MIN:
            failures.append(
                f"PIN {label}: midpoint rel median {mid['rel_med']:.6e} < "
                f"{PIN_MID_MEDIAN_MIN} — the artifact this step measured has moved"
            )
        if vtx["scaled_med"] > mid["scaled_med"]:
            failures.append(
                f"PIN {label}: vertex scaled median {vtx['scaled_med']:.6e} now exceeds "
                f"midpoint {mid['scaled_med']:.6e} — the measured localization has flipped"
            )

    for p1_label, dg_label in (
        ("A_N1curl", "A_toDG1"),
        ("B_DG1", "B_toDG1"),
        ("E_N1curl", "E_toDG1"),
    ):
        for tag in ("MID", "VTX"):
            p1 = results[(p1_label, tag)]
            dg = results[(dg_label, tag)]
            excess = p1["scaled_med"] / max(dg["scaled_med"], FIELD_FLOOR)
            print(
                f"DISCRIM {p1_label:<10} {tag:<3} p1_scaled_med={p1['scaled_med']:.6e} "
                f"dg1_scaled_med={dg['scaled_med']:.6e} p1_over_dg1={excess:.6e}",
                flush=True,
            )
            if dg["scaled_med"] > DISCRIM_MAX:
                failures.append(
                    f"DISCRIM {p1_label} {tag}: DG1 target disagrees with source at "
                    f"{dg['scaled_med']:.6e} > {DISCRIM_MAX} — degree-1 interpolation "
                    f"error is not negligible, so the P1 excess is not purely the "
                    f"continuity constraint"
                )

    ctrl_mid = results[("CTRL_P1", "MID")]
    ctrl_vtx = results[("CTRL_P1", "VTX")]
    print(
        f"CONTROL CTRL_P1 mid_scaled_max={ctrl_mid['scaled_max']:.6e} "
        f"vtx_scaled_max={ctrl_vtx['scaled_max']:.6e}",
        flush=True,
    )
    for tag, stats in (("MID", ctrl_mid), ("VTX", ctrl_vtx)):
        if stats["scaled_max"] > CONTROL_MAX:
            failures.append(
                f"CTRL_P1 {tag}: scaled max {stats['scaled_max']:.6e} > {CONTROL_MAX}"
            )

    if failures:
        for f in failures:
            print(f"FAIL {f}", flush=True)
        print("PROBE_RESULT FAIL", flush=True)
        return 1

    print("PROBE_RESULT PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
