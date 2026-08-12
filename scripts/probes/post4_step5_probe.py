"""`POST-4` step 5 — price the faithful-export route before the P1-vs-DG1 call.

Measurement only: no ``src/`` change, no example switches its export, no
tolerance moved.  Step 4 measured that every XDMF/VTX export of a Nedelec or DG
field ships a Lagrange-P1 interpolant sitting at **51.17% / 52.47% / 20.18%**
(``A`` / ``B`` / ``E``, midpoint relative median) from its source, and that the
whole of that is the P1 **continuity constraint**: the same three sources
interpolated onto a **DG1** target reproduce them to round-off (3.25e-17 scaled
median).  That leaves an open call — export DG1 (faithful, discontinuous
rendering, larger files) or keep P1 under the caveat — and the call needs the
DG1 route *priced*, which is what this probe does.

Three things are measured on one run of the ``examples/mri/01`` debug fixture:

1. **Round-trip fidelity.** The three fields are written through the DG1/VTX
   route (``VTXWriter`` to ``.bp``, BP4), read back through ADIOS2, poured into
   a fresh ``DG1`` function on the same space, and compared with the in-memory
   DG1 function at the step-4 point sets.  Anchor: scaled median <= ``1e-14``.
   A read-back that is *not* faithful is the finding that kills the DG1 route.
2. **Fidelity to the source.** The step-4 comparison, re-run with the read-back
   DG1 fields in the interpolant slot: these must read round-off where the P1
   path reads the step-4 numbers.  The P1 path is measured in the *same* run,
   and its refutation pin (midpoint relative median >= 10%, vertex <= midpoint)
   must still fire — if the P1 numbers moved, the fixture drifted and the whole
   comparison is void.
3. **Cost.** Writer wall-clock and on-disk size for both routes.  ADIOS2 ``.bp``
   is a *directory*: it is sized by a tree walk, never ``stat``.

The read-back is deliberately literal.  ``VTXWriter`` on a discontinuous space
emits point data as an ADIOS2 **local** array — one block per writer rank, no
global shape — and for DG1 the emitted points are exactly the space's owned
dofs, in dofmap order.  Each rank therefore opens the file serially and reads
**its own** block; the block-vs-rank correspondence is not assumed but
*checked* (the local dof count must match the block count, and a mismatch is
reported with every block's shape rather than silently repaired).

ParaView-side rendering of a DG1 ``.bp`` cannot be asserted headless.  It is a
one-click operator check on the dashboard, never a gate here.

Run through the harness::

    scripts/testing/run_and_log.sh POST-4 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && PYTHONPATH=/workspace/src \\
      FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 180 mpiexec -n 2 python3 \\
      scripts/probes/post4_step5_probe.py'"

``smoke`` as argv[1] runs the write/read-back mechanics alone on a unit cube
(no solve); the default runs the real fixture.  Exit code 0 iff every asserted
anchor below holds.
"""

import os
import shutil
import sys
import time

import numpy as np
import ufl
from mpi4py import MPI
from dolfinx import fem, io, mesh as dmesh

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

# Fixture: examples/mri/01_coil_phantom_fields.py, debug preset -- identical to
# the step-1 and step-4 probes so all three runs are directly comparable.
RESOLUTION_M = 0.02
FREQUENCY_HZ = 127.74e6
FIELD_FLOOR = 1e-30
N_SAMPLE = 400
STEP4_CELLS = 9261  # fixture identity: step-4's recorded global cell count

MESH_PARAMS = {
    "coil_major_radius": 0.08,
    "coil_minor_radius": 0.01,
    "coil_separation": 0.08,
    "phantom_radius": 0.04,
    "phantom_height": 0.10,
    "air_padding": 0.04,
    "resolution": RESOLUTION_M,
}

OUT_DIR = "/workspace/output/post4_step5"

# ---- anchors (PROJECT_PLAN §7, `POST-4` step 5) ---------------------------
# (1) round-trip read-back vs the in-memory DG1 function, scaled median.
ROUNDTRIP_MAX = 1e-14
# (2) the read-back DG1 fields vs their sources: round-off, same bound step 4
#     used for its DG1 discriminator.
DG1_VS_SOURCE_MAX = 1e-14
# Negative control -- step 4's refutation pin on the P1 path, measured in this
# same run.  These are step 4's own recorded digits, not new bounds: midpoint
# relative medians were 5.117084e-01 / 5.247224e-01 / 2.018185e-01 and the
# vertex/midpoint scaled-median separations 0.4185x / 0.4818x / 0.6835x.
PIN_MID_MEDIAN_MIN = 0.10
# Fixture-drift guard: the P1 midpoint relative medians must reproduce step 4's
# to this relative tolerance, else the fixture moved and the comparison is void.
PIN_REPRO_RTOL = 0.02
STEP4_MID_REL_MED = {
    "A": 5.117084e-01,
    "B": 5.247224e-01,
    "E": 2.018185e-01,
}


def _collect_points(local_points, comm, n_sample):
    """Gather owned points, sort lexicographically, subsample evenly, broadcast.

    Verbatim from the step-4 probe: the sort makes the selection a function of
    the geometry only, so the same physical points are sampled at every rank
    count and the two probes' tables are comparable line for line.
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


def build_point_sets(msh, comm):
    """MID = owned cell midpoints; VTX = owned geometry nodes (P1 mesh: vertices)."""
    tdim = msh.topology.dim
    n_cells = msh.topology.index_map(tdim).size_local
    cells = np.arange(n_cells, dtype=np.int32)
    mids = msh.geometry.x[msh.geometry.dofmap[cells]].mean(axis=1)

    n_nodes = msh.geometry.index_map().size_local
    verts = msh.geometry.x[:n_nodes]

    return (
        _collect_points(mids, comm, N_SAMPLE),
        _collect_points(verts, comm, N_SAMPLE),
    )


def compare(label, tag, source, target, points, comm):
    """Target-vs-source disagreement at ``points``; returns a stats dict on rank 0."""
    src_vals, src_valid = evaluate_vector_field_parallel(source, points, comm=comm)
    tgt_vals, tgt_valid = evaluate_vector_field_parallel(target, points, comm=comm)
    if comm.rank != 0:
        return None

    valid = np.logical_and(np.asarray(src_valid, dtype=bool), np.asarray(tgt_valid, dtype=bool))
    src = np.asarray(src_vals).reshape(points.shape[0], -1)[valid]
    tgt = np.asarray(tgt_vals).reshape(points.shape[0], -1)[valid]

    src_mag = np.linalg.norm(src, axis=1).astype(np.float64)
    diff_mag = np.linalg.norm(tgt - src, axis=1).astype(np.float64)

    rel = diff_mag / np.maximum(src_mag, FIELD_FLOOR)
    rms = float(np.sqrt(np.mean(src_mag ** 2))) if src_mag.size else 0.0
    scaled = diff_mag / max(rms, FIELD_FLOOR)

    stats = {
        "n": int(valid.sum()),
        "rel_max": float(np.max(rel)) if rel.size else 0.0,
        "rel_med": float(np.median(rel)) if rel.size else 0.0,
        "scaled_max": float(np.max(scaled)) if scaled.size else 0.0,
        "scaled_med": float(np.median(scaled)) if scaled.size else 0.0,
        "rms": rms,
    }
    print(
        f"DISAGREE {label:<14} {tag:<3} n={stats['n']:>4} "
        f"rel_max={stats['rel_max']:.6e} rel_med={stats['rel_med']:.6e} "
        f"scaled_max={stats['scaled_max']:.6e} scaled_med={stats['scaled_med']:.6e} "
        f"rms_src={stats['rms']:.6e}",
        flush=True,
    )
    return stats


def tree_size(path):
    """On-disk bytes under ``path``.  ADIOS2 `.bp` is a directory -- `stat` lies."""
    if os.path.isfile(path):
        return os.path.getsize(path), 1
    total = 0
    nfiles = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
                nfiles += 1
    return total, nfiles


def read_vtx_block(bp_path, name, block_id, comm):
    """Read one writer rank's block of a VTX point-data variable, serially.

    Returns ``(array, shapes)`` where ``shapes`` lists every block's ``Count``
    so a mismatch can be *reported* rather than silently worked around.

    In the **complex** build ``VTXWriter`` has no complex point-data type: it
    emits two real arrays per function, ``<name>_real`` and ``<name>_imag``
    (measured 2026-08-12, ``20260812T200439Z_POST-4-step5-n2.log``).  They are
    read separately and recombined here, so the route's fidelity is judged on
    the complex field the solver actually produced, not on its real part.
    """
    import adios2

    adios = adios2.ADIOS()
    reader_io = adios.DeclareIO(f"post4_step5_read_{name}_{comm.rank}")
    reader_io.SetEngine("BP4")
    engine = reader_io.Open(str(bp_path), adios2.Mode.ReadRandomAccess)

    def _one(var_name):
        var = reader_io.InquireVariable(var_name)
        blocks = engine.BlocksInfo(var_name, 0)
        shp = [[int(n) for n in b["Count"].split(",")] for b in blocks]
        if block_id >= len(blocks):
            raise RuntimeError(
                f"'{var_name}' has {len(blocks)} blocks, rank {comm.rank} wanted {block_id}"
            )
        var.SetBlockSelection(block_id)
        buf = np.zeros(shp[block_id], dtype=np.float64)
        engine.Get(var, buf, adios2.Mode.Sync)
        return buf, shp

    try:
        available = reader_io.AvailableVariables()
        if name in available:
            data, shapes = _one(name)
        elif f"{name}_real" in available and f"{name}_imag" in available:
            re_part, shapes = _one(f"{name}_real")
            im_part, _ = _one(f"{name}_imag")
            data = re_part + 1j * im_part
        else:
            raise RuntimeError(
                f"no '{name}' (nor '{name}_real'/'{name}_imag') in {bp_path}; "
                f"found {sorted(available)}"
            )
    finally:
        engine.Close()
    return data, shapes


def restore_dg1(space, name, bp_path, varname, comm):
    """Rebuild a DG1 ``Function`` from its VTX ``.bp`` point data.

    For a discontinuous space, VTX emits one point per dof coordinate, in
    dofmap order, one block per writer rank.  The smoke arm
    (``20260812T200316Z_POST-4-step5-smoke.log``) measured that the block
    carries ``size_local + num_ghosts`` rows -- i.e. the full
    ``tabulate_dof_coordinates`` extent, ghosts included -- so only the leading
    owned rows are poured back and the ghost layer is rebuilt by
    ``scatter_forward``.  Both extents are accepted and the one actually seen
    is printed; a block matching neither is reported, never silently repaired.
    """
    f = fem.Function(space, name=name)
    bs = space.dofmap.index_map_bs
    n_local = space.dofmap.index_map.size_local
    n_ghost = space.dofmap.index_map.num_ghosts

    data, shapes = read_vtx_block(bp_path, varname, comm.rank, comm)
    ok = data.shape[0] in (n_local, n_local + n_ghost) and data.shape[1] >= bs
    all_ok = comm.allreduce(1 if ok else 0, op=MPI.MIN)
    if not all_ok:
        extents = comm.gather((comm.rank, data.shape[0], n_local, n_ghost), root=0)
        if comm.rank == 0:
            print(
                f"FAIL BLOCKSHAPE {varname}: block shapes {shapes} match neither the owned "
                f"nor the owned+ghost dof counts per rank {extents} -- the VTX point order "
                f"is not the dofmap order and the read-back cannot be reconstructed",
                flush=True,
            )
        return None
    if comm.rank == 0:
        print(
            f"BLOCKSHAPE {varname} rows={data.shape[0]} size_local={n_local} "
            f"num_ghosts={n_ghost} (rank 0)",
            flush=True,
        )
    f.x.array[: n_local * bs] = data[:n_local, :bs].reshape(-1)
    f.x.scatter_forward()
    return f


def build_smoke_case(comm):
    """Unit cube + analytic DG1 fields: exercises write/read-back only."""
    msh = dmesh.create_unit_cube(comm, 6, 6, 6)
    v_dg1 = fem.functionspace(msh, ("DG", 1, (3,)))
    fields = {}
    for i, nm in enumerate(("A", "B", "E")):
        f = fem.Function(v_dg1, name=nm)
        f.interpolate(
            lambda x, k=i: np.vstack(
                [x[0] + k, 2.0 * x[1] - k, 3.0 * x[2] * (k + 1.0)]
            )
        )
        fields[nm] = f
    return msh, v_dg1, fields


def build_real_case(comm):
    """The examples/mri/01 debug preset: mesh, magnetostatic solve, TH solve."""
    msh, cell_tags, facet_tags = MeshGenerator.coil_phantom_domain(**MESH_PARAMS, comm=comm)
    tdim = msh.topology.dim
    n_global = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    if comm.rank == 0:
        print(f"MESH_FINGERPRINT cells={n_global} (step-4 record {STEP4_CELLS})", flush=True)

    j_magnitude = 1.0 / (np.pi * 0.01 ** 2)

    def current_density(_x):
        return ufl.as_vector([0.0, 0.0, j_magnitude])

    mag_problem = MagnetostaticProblem(
        mesh=msh, cell_tags=cell_tags, facet_tags=facet_tags, mu=MU_0
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
        mesh=msh,
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

    return msh, n_global, {"A": a_field, "B": b_field, "E": e_field}


def main():
    comm = MPI.COMM_WORLD
    smoke = len(sys.argv) > 1 and sys.argv[1] == "smoke"

    if comm.rank == 0:
        print("=" * 78)
        print(f"POST-4 step 5 probe — ranks={comm.size} mode={'smoke' if smoke else 'full'}")
        print("=" * 78, flush=True)
        os.makedirs(OUT_DIR, exist_ok=True)
    comm.Barrier()

    failures = []

    if smoke:
        msh, v_dg1, dg_fields = build_smoke_case(comm)
        sources = None
        n_global = None
    else:
        msh, n_global, sources = build_real_case(comm)
        v_dg1 = fem.functionspace(msh, ("DG", 1, (3,)))
        dg_fields = {}
        for nm, src in sources.items():
            f = fem.Function(v_dg1, name=nm)
            f.interpolate(src)
            dg_fields[nm] = f
        if comm.rank == 0 and n_global != STEP4_CELLS:
            failures.append(
                f"FIXTURE: {n_global} cells != step-4 record {STEP4_CELLS} — the "
                f"fixture drifted and the step-4 comparison is void"
            )

    # ---- route 1: DG1 -> VTX/.bp --------------------------------------------
    bp_path = os.path.join(OUT_DIR, "post4_step5_dg1.bp")
    if comm.rank == 0 and os.path.isdir(bp_path):
        shutil.rmtree(bp_path)
    comm.Barrier()

    comm.Barrier()
    t0 = time.perf_counter()
    vtx_error = None
    try:
        writer = io.VTXWriter(comm, bp_path, list(dg_fields.values()), engine="BP4")
        writer.write(0.0)
        writer.close()
    except Exception as e:  # noqa: BLE001 - a writer that refuses these fields IS the finding
        vtx_error = f"{type(e).__name__}: {e}"
    comm.Barrier()
    dg1_write_s = comm.allreduce(time.perf_counter() - t0, op=MPI.MAX)
    vtx_error = comm.bcast(vtx_error, root=0)
    if vtx_error is not None:
        failures.append(
            f"VTXWRITE: the DG1/VTX route could not write these fields ({vtx_error}) — "
            f"this kills the DG1 route on its own"
        )

    # ---- route 2: P1 -> XDMF (the current export path) ----------------------
    v_p1 = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    p1_fields = {}
    for nm in ("A", "B", "E"):
        f = fem.Function(v_p1, name=nm)
        f.interpolate(sources[nm] if sources is not None else dg_fields[nm])
        p1_fields[nm] = f

    xdmf_path = os.path.join(OUT_DIR, "post4_step5_p1.xdmf")
    comm.Barrier()
    t0 = time.perf_counter()
    xdmf_error = None
    try:
        with io.XDMFFile(comm, xdmf_path, "w") as xf:
            xf.write_mesh(msh)
            for f in p1_fields.values():
                xf.write_function(f, 0.0)
    except Exception as e:  # noqa: BLE001 - reported in the cost table, not fatal
        xdmf_error = f"{type(e).__name__}: {e}"
    comm.Barrier()
    p1_write_s = comm.allreduce(time.perf_counter() - t0, op=MPI.MAX)
    xdmf_error = comm.bcast(xdmf_error, root=0)
    if xdmf_error is not None and comm.rank == 0:
        print(f"COST p1_xdmf UNAVAILABLE ({xdmf_error})", flush=True)

    # ---- read the DG1 route back -------------------------------------------
    readback = {"A": None, "B": None, "E": None}
    for nm in ("A", "B", "E"):
        if vtx_error is not None:
            break
        rb = restore_dg1(v_dg1, f"{nm}_rb", bp_path, nm, comm)
        if rb is None:
            failures.append(f"READBACK {nm}: block/dof shape mismatch (see FAIL BLOCKSHAPE)")
        readback[nm] = rb

    mid_points, vtx_points = build_point_sets(msh, comm)
    if comm.rank == 0:
        print(f"POINTS mid={mid_points.shape[0]} vtx={vtx_points.shape[0]}", flush=True)

    # Anchor (1): read-back vs in-memory DG1.
    for nm in ("A", "B", "E"):
        if readback[nm] is None:
            continue
        for tag, pts in (("MID", mid_points), ("VTX", vtx_points)):
            st = compare(f"RT_{nm}", tag, dg_fields[nm], readback[nm], pts, comm)
            if comm.rank == 0 and st["scaled_med"] > ROUNDTRIP_MAX:
                failures.append(
                    f"ROUNDTRIP {nm} {tag}: scaled median {st['scaled_med']:.6e} > "
                    f"{ROUNDTRIP_MAX} — the ADIOS2 write path degrades the DG1 field"
                )
        # dof-level round-trip, independent of point evaluation
        n_own = v_dg1.dofmap.index_map.size_local * v_dg1.dofmap.index_map_bs
        loc = float(np.max(np.abs(readback[nm].x.array[:n_own] - dg_fields[nm].x.array[:n_own])))
        scale = comm.allreduce(
            float(np.max(np.abs(dg_fields[nm].x.array[:n_own]))) if n_own else 0.0, op=MPI.MAX
        )
        gmax = comm.allreduce(loc, op=MPI.MAX)
        if comm.rank == 0:
            print(
                f"RT_DOF {nm} max_abs_diff={gmax:.6e} field_max={scale:.6e} "
                f"scaled={gmax / max(scale, FIELD_FLOOR):.6e}",
                flush=True,
            )
            if gmax / max(scale, FIELD_FLOOR) > ROUNDTRIP_MAX:
                failures.append(
                    f"ROUNDTRIP {nm} DOF: scaled max {gmax / max(scale, FIELD_FLOOR):.6e} > "
                    f"{ROUNDTRIP_MAX}"
                )

    # Anchor (2) + the negative control: both routes against the sources.
    if sources is not None:
        p1_scaled = {}
        for nm in ("A", "B", "E"):
            for tag, pts in (("MID", mid_points), ("VTX", vtx_points)):
                p1 = compare(f"P1_{nm}", tag, sources[nm], p1_fields[nm], pts, comm)
                dg = compare(f"DG1rb_{nm}", tag, sources[nm], readback[nm], pts, comm) \
                    if readback[nm] is not None else None
                if comm.rank != 0:
                    continue
                p1_scaled[(nm, tag)] = p1["scaled_med"]
                if dg is not None:
                    print(
                        f"ROUTE {nm:<2} {tag:<3} p1_rel_med={p1['rel_med']:.6e} "
                        f"dg1_rb_scaled_med={dg['scaled_med']:.6e} "
                        f"p1_scaled_med={p1['scaled_med']:.6e}",
                        flush=True,
                    )
                    if dg["scaled_med"] > DG1_VS_SOURCE_MAX:
                        failures.append(
                            f"DG1SRC {nm} {tag}: read-back DG1 disagrees with its source at "
                            f"{dg['scaled_med']:.6e} > {DG1_VS_SOURCE_MAX}"
                        )
                if tag == "MID":
                    # step-4 refutation pin + fixture-drift guard
                    if p1["rel_med"] < PIN_MID_MEDIAN_MIN:
                        failures.append(
                            f"PIN {nm}: P1 midpoint rel median {p1['rel_med']:.6e} < "
                            f"{PIN_MID_MEDIAN_MIN} — the step-4 artifact has moved"
                        )
                    rec = STEP4_MID_REL_MED[nm]
                    drift = abs(p1["rel_med"] - rec) / rec
                    print(
                        f"REPRO {nm} p1_mid_rel_med={p1['rel_med']:.6e} "
                        f"step4_record={rec:.6e} drift={drift:.6e}",
                        flush=True,
                    )
                    if drift > PIN_REPRO_RTOL:
                        failures.append(
                            f"REPRO {nm}: P1 midpoint rel median drifted {drift:.4%} from the "
                            f"step-4 record — the fixture moved, the comparison is void"
                        )
        # vertex <= midpoint half of step 4's refutation pin
        if comm.rank == 0:
            for nm in ("A", "B", "E"):
                mid_s = p1_scaled[(nm, "MID")]
                vtx_s = p1_scaled[(nm, "VTX")]
                sep = vtx_s / max(mid_s, FIELD_FLOOR)
                print(
                    f"PIN_SEP {nm} p1_vtx_scaled_med={vtx_s:.6e} "
                    f"p1_mid_scaled_med={mid_s:.6e} separation={sep:.4f}x",
                    flush=True,
                )
                if vtx_s > mid_s:
                    failures.append(
                        f"PIN {nm}: P1 vertex scaled median {vtx_s:.6e} now exceeds midpoint "
                        f"{mid_s:.6e} — step 4's measured localization has flipped"
                    )

    # ---- cost table ---------------------------------------------------------
    comm.Barrier()
    if comm.rank == 0:
        bp_bytes, bp_files = tree_size(bp_path)
        xdmf_bytes, _ = tree_size(xdmf_path)
        h5_path = xdmf_path.replace(".xdmf", ".h5")
        h5_bytes, _ = tree_size(h5_path) if os.path.exists(h5_path) else (0, 0)
        p1_bytes = xdmf_bytes + h5_bytes
        print("-" * 78, flush=True)
        print(
            f"COST dg1_vtx_bp bytes={bp_bytes} files={bp_files} write_s={dg1_write_s:.4f}",
            flush=True,
        )
        print(
            f"COST p1_xdmf   bytes={p1_bytes} (xdmf={xdmf_bytes} h5={h5_bytes}) "
            f"write_s={p1_write_s:.4f}",
            flush=True,
        )
        print(
            f"COST ratio size_dg1_over_p1={bp_bytes / max(p1_bytes, 1):.4f} "
            f"time_dg1_over_p1={dg1_write_s / max(p1_write_s, 1e-12):.4f}",
            flush=True,
        )

    ok = comm.bcast(0 if failures else 1, root=0)
    if comm.rank == 0:
        for f in failures:
            print(f"FAIL {f}", flush=True)
        print(f"PROBE_RESULT {'PASS' if ok else 'FAIL'}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
