"""`GEO-32` — force a C4-congruent port-sheet cut, and re-read the geometry.

A mesher lever and a geometric reading.  **No solve**, real build.

**Why.**  `GEO-31` measured the four birdcage port gap-sheets as the same patch
cut four different ways (facet-centroid Hausdorff 0.44-0.99 of a facet edge,
×1 included), and `PORT-18` printed that the N1curl-interpolant read-back
spread of a smooth C4-invariant field tracks the rungs whose cut broke.  The
lever is ``MeshGenerator.birdcage_port_domain(c4_congruent_sheets=True)``,
which binds sheets 2..4 to sheet 1 with ``gmsh.model.mesh.setPeriodic`` under
the snapped z-rotation.

**Rungs.**  ``geo30.RUNGS[0]`` (×1) and ``geo30.RUNGS[1]`` (×0.75); the builder
is ``geo30._build_rung`` with its additive ``c4_congruent_sheets`` pass-through
(default ``False``, the generator's own default).  Each rung is built with the
flag off and then on.

**Read.**  Imported, never retyped: ``geo31._measure_rung`` + ``geo31._analyse``
(facet counts, areas, sorted facet-area vectors, centroid and boundary-vertex
Hausdorff against rotated sheet 1, gathered to rank 0 first) and
``port18._measure_rung`` (the smooth-field ``R^+`` read-back, pinned quadrature,
ghosted DG0 indicators).

**Asserted.**

(A) *reproduction, flag off* — to `GEO-31`'s printed digits
    (``20260910T003835Z_GEO-31.log:7270-7286``): ×1 ``size_global`` within the
    imported, unmoved 1% ``CELL_COUNT_BAND`` of the 116 085 record; facet counts
    (58, 58, 58, 58) at ×1 and (80, 74, 80, 74) at ×0.75; ``d(P3)`` prints
    ``1.114339e-03`` m at ×1; ``d(P2)/ℓ`` and ``d(P4)/ℓ`` print ``0.9897`` at
    ×0.75.
(B) *congruence, flag on* — at both rungs the four facet counts are equal and
    every ``d_i`` (centroids, vs sheet 1 rotated by ``(i-1)·90°``) is ≤ 1e-12 m.

*Negative control* — flag-off ``max_i d_i ≥ 0.4 ℓ`` at both rungs (a metric
that reads 0 regardless fails here; a keyword that does nothing fails (B)).

**Printed, asserted nowhere (rule (e)):** per rung and flag ``size_global``,
mesh time, facet counts, sorted facet-area multisets, and `PORT-18`'s ``R^+``
q = 2 four-sheet spread.  Predicted at ×0.75: 3.52e-04 → ≈ 1e-5 with the flag.

Rank-safety: every quantity comes from the imported measurers, which allreduce
or gather before comparing; asserts run on every rank after all collectives
against ``bcast`` values.

Run (real build)::

    mpiexec -n 2 python3 -u scripts/probes/geo32_c4_congruent_sheet_cut.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "scripts" / "probes") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts" / "probes"))

import geo30_birdcage_c4_refinement_census as geo30  # noqa: E402
import geo31_birdcage_port_sheet_congruence as geo31  # noqa: E402
import port18_sheet_plus_side_census as port18  # noqa: E402

X1 = geo30.RUNGS[0][0]
X075 = geo30.RUNGS[1][0]

# `GEO-31`'s printed readings (`20260910T003835Z_GEO-31.log`): the counts at
# `:7271-7274`'s rungs as tabled above them, d(P3) at ×1 = the ×1 max
# (`:7271`), and the ×0.75 max 9.897e-01 l (`:7273`) carried by P2/P4.
GEO31_COUNTS = {X1: (58, 58, 58, 58), X075: (80, 74, 80, 74)}
GEO31_D_P3_X1 = "1.114339e-03"
GEO31_D_OVER_ELL_P2P4_X075 = "0.9897"
CONGRUENCE_BAR_M = 1.0e-12
NEG_CONTROL_BAR_ELL = 0.4
Q_SPREAD = 2


def _print(text, comm):
    if comm.rank == 0:
        print(text, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rungs", default="0,1")
    args = parser.parse_args()
    sel = [int(s) for s in args.rungs.split(",") if s.strip()]

    comm = MPI.COMM_WORLD
    started = time.perf_counter()
    _print(
        "\n[GEO-32] C4-congruent port-sheet cut by setPeriodic: flag off vs on "
        "(no solve; asserts (A) reproduction, (B) congruence, negative control)\n"
        f"[GEO-32] ranks={comm.size}  rungs={[geo30.RUNGS[k][0] for k in sel]}",
        comm,
    )

    rows = {}
    for k in sel:
        label, h_c, h = geo30.RUNGS[k]
        for flag in (False, True):
            key = (label, flag)
            _print(f"\n[GEO-32] --- rung {label}  c4_congruent_sheets={flag} ---", comm)
            mesh, cell_tags, diag, rung_s = geo30._build_rung(
                h_c, h, comm, c4_congruent_sheets=flag
            )
            size_global = int(mesh.topology.index_map(mesh.topology.dim).size_global)
            g = geo31._measure_rung(mesh, cell_tags, comm)
            t0 = time.perf_counter()
            p = port18._measure_rung(mesh, cell_tags, comm)
            measure_s = time.perf_counter() - t0
            row = {
                "size_global": size_global,
                "mesh_s": float(diag["mesh_wall_time_s"]),
                "rung_s": float(rung_s),
                "port18_s": float(measure_s),
                "counts": tuple(int(c) for c in g["counts"]),
                "areas": list(g["areas"]),
                "Rp": list(p["Rp"][Q_SPREAD]),
                "Rp_spread": port18._spread(p["Rp"][Q_SPREAD]),
                "Ravg_spread": port18._spread(p["Ravg"][Q_SPREAD]),
                "expr_spread": port18._spread(p["expr"]),
            }
            if comm.rank == 0:
                g = geo31._analyse(g, label)
                row["d"] = list(g["d_centroid"])
                row["d_boundary"] = list(g["d_boundary"])
                row["ell"] = float(g["ell"])
                row["sorted_area"] = [s["facet_area"] for s in g["sheets"]]
                row["sorted_area_delta"] = list(g["sorted_area_delta"])
            rows[key] = row
            _print(
                f"[GEO-32] {label} flag={flag}: size_global={size_global}  "
                f"mesh={row['mesh_s']:.2f} s  rung={rung_s:.2f} s  "
                f"port18 measure={measure_s:.2f} s  facets={row['counts']}  "
                f"R+ q={Q_SPREAD} spread={row['Rp_spread']:.6e}",
                comm,
            )
            del mesh, cell_tags

    elapsed = time.perf_counter() - started
    payload = None
    if comm.rank == 0:
        print("\n[GEO-32] === per rung and flag (printed; asserted only where marked) ===")
        for (label, flag), r in rows.items():
            ell = r["ell"]
            print(
                f"\n  rung {label}  c4_congruent_sheets={flag}  "
                f"(size_global={r['size_global']}, mesh {r['mesh_s']:.2f} s, "
                f"l={ell:.6e} m)"
            )
            print(f"    facet counts               {r['counts']}")
            print("    areas [m^2]                " + "  ".join(f"{a:.9e}" for a in r["areas"]))
            print("    d_i centroids [m]          " + "  ".join(f"{v:.6e}" for v in r["d"]))
            print("    d_i / l                    " + "  ".join(f"{v / ell:13.6f}" for v in r["d"]))
            print("    d_i boundary verts [m]     " + "  ".join(f"{v:.6e}" for v in r["d_boundary"]))
            print(
                "    |sorted(Pi)-sorted(P1)|_inf/mean  "
                + "  ".join(f"{v:.6e}" for v in r["sorted_area_delta"])
            )
            print(
                f"    PORT-18 R+ q={Q_SPREAD}               "
                + "  ".join(f"{v:.12e}" for v in r["Rp"])
                + f"  spread={r['Rp_spread']:.6e}  (Ravg spread={r['Ravg_spread']:.6e}, "
                f"expr q=8 spread={r['expr_spread']:.6e})"
            )
            print("    sorted facet-area multisets [m^2]:")
            for i, v in enumerate(r["sorted_area"]):
                print(f"      P{i + 1}  n={v.shape[0]}")
                for s in range(0, v.shape[0], 6):
                    print("          " + "  ".join(f"{x:.9e}" for x in v[s : s + 6]))

        print("\n[GEO-32] === printed spread, flag off vs on (rule (e); predicted x0.75: 3.52e-04 -> ~1e-5) ===")
        labels = []
        for label, _flag in rows:
            if label not in labels:
                labels.append(label)
        for label in labels:
            off, on = rows[(label, False)], rows[(label, True)]
            print(
                f"  {label:<28s} R+ q={Q_SPREAD} spread off={off['Rp_spread']:.6e}  "
                f"on={on['Rp_spread']:.6e}  size_global off={off['size_global']} "
                f"on={on['size_global']}  mesh off={off['mesh_s']:.2f} s on={on['mesh_s']:.2f} s"
            )

        payload = {"rows": {}}
        for (label, flag), r in rows.items():
            payload["rows"][(label, flag)] = {
                "size_global": r["size_global"],
                "counts": r["counts"],
                "d": r["d"],
                "ell": r["ell"],
            }

        print("\n[GEO-32] === asserted anchors ===")
        if (X1, False) in rows:
            r = rows[(X1, False)]
            print(
                f"  (A) x1 off: size_global={r['size_global']} vs {geo30.STEP2_CELL_COUNT} "
                f"(ratio {r['size_global'] / geo30.STEP2_CELL_COUNT:.6f}, band "
                f"{geo30.CELL_COUNT_BAND:.0e})  counts={r['counts']} vs {GEO31_COUNTS[X1]}  "
                f"d(P3)={r['d'][2]:.6e} m vs {GEO31_D_P3_X1}"
            )
        if (X075, False) in rows:
            r = rows[(X075, False)]
            print(
                f"  (A) x0.75 off: counts={r['counts']} vs {GEO31_COUNTS[X075]}  "
                f"d(P2)/l={r['d'][1] / r['ell']:.4f} d(P4)/l={r['d'][3] / r['ell']:.4f} "
                f"vs {GEO31_D_OVER_ELL_P2P4_X075}"
            )
        for label in labels:
            on, off = rows[(label, True)], rows[(label, False)]
            print(
                f"  (B) {label} on: counts={on['counts']}  max d_i={max(on['d']):.6e} m "
                f"(bar {CONGRUENCE_BAR_M:.0e} m)"
            )
            print(
                f"  (neg) {label} off: max d_i/l={max(off['d']) / off['ell']:.6f} "
                f"(bar >= {NEG_CONTROL_BAR_ELL})"
            )
        print(f"[GEO-32] probe wall time={elapsed:.2f} s", flush=True)

    payload = comm.bcast(payload, root=0)
    R = payload["rows"]
    if (X1, False) in R:
        r = R[(X1, False)]
        ratio = r["size_global"] / geo30.STEP2_CELL_COUNT
        assert abs(ratio - 1.0) < geo30.CELL_COUNT_BAND, (
            f"(A) x1 flag-off size_global {r['size_global']} vs record "
            f"{geo30.STEP2_CELL_COUNT} (ratio {ratio:.6f})"
        )
        assert r["counts"] == GEO31_COUNTS[X1], f"(A) x1 counts {r['counts']}"
        assert f"{r['d'][2]:.6e}" == GEO31_D_P3_X1, (
            f"(A) x1 d(P3)={r['d'][2]:.6e} m vs GEO-31's {GEO31_D_P3_X1}"
        )
    if (X075, False) in R:
        r = R[(X075, False)]
        assert r["counts"] == GEO31_COUNTS[X075], f"(A) x0.75 counts {r['counts']}"
        for i in (1, 3):
            got = f"{r['d'][i] / r['ell']:.4f}"
            assert got == GEO31_D_OVER_ELL_P2P4_X075, (
                f"(A) x0.75 d(P{i + 1})/l={got} vs GEO-31's {GEO31_D_OVER_ELL_P2P4_X075}"
            )
    for (label, flag), r in R.items():
        if flag:
            assert len(set(r["counts"])) == 1, f"(B) {label} on: counts {r['counts']}"
            assert max(r["d"]) <= CONGRUENCE_BAR_M, (
                f"(B) {label} on: d_i={r['d']} m, bar {CONGRUENCE_BAR_M:.0e} m"
            )
        else:
            assert max(r["d"]) >= NEG_CONTROL_BAR_ELL * r["ell"], (
                f"negative control {label} off: max d_i/l="
                f"{max(r['d']) / r['ell']:.6f} < {NEG_CONTROL_BAR_ELL}"
            )
    _print("[GEO-32] (A), (B) and the negative control green.", comm)


if __name__ == "__main__":
    main()
