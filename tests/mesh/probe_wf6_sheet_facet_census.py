"""`WF-6` step 4k: a no-solve geometric census of P1's narrowed port sheet.

Measurement only -- asserts nothing, imported by nothing, no solve.

`WF-6` step 4j (`docs/testing/logs/20260912T033518Z_WF-6-step4j.log:4108`) put
42.25 % of P1's drive-component variance on one facet at (u 0.164, v 0.422),
area share 6.726 %, on the flag-on x0.0095 mesh.  The hypothesis under test is
that this facet (or a tet adjacent to it) is a sliver / rim cell.  That is a
mesh property, so this probe builds the identical fixture with
``build_four_port_sweep(build_only=True, resolution=r, c4_congruent_sheets=True)``
(`tests/validation/test_port_birdcage_four_port.py:219`) and reads, for every
owned facet of each sheet:

* facet edge ratio (longest / shortest edge) and circumradius / inradius
  (2 for an equilateral triangle);
* facet area / sheet median area, and area share (the 4j column);
* for the (two, interior sheet) adjacent tets: normalised radius ratio
  ``3 r_in / R_circ`` (1 for a regular tet) and minimum dihedral angle, the
  worse of the adjacent tets reported;
* whether the facet shares an edge with the sheet's boundary, split into a
  *terminal* edge (both vertices on the gap-end planes v = 0 or v = 1) and a
  *lateral rim* edge (any other sheet-boundary edge), plus a vertex-only touch.

The (u, v) coordinates are the 4j bbox mapping copied verbatim from
`_sheet_profile` (`tests/validation/test_birdcage_b1_plus_closed_form.py:715-720`),
so a (u, v) printed here names the facet 4j named.  The 4j top-5 lists are
matched by nearest (u, v) and their area shares printed beside 4j's.

One rung per process (fresh gmsh), ``-n 1``:

    mpiexec -n 1 python3 -u tests/mesh/probe_wf6_sheet_facet_census.py x0.0095
"""

import hashlib
import os
import sys
import time

import numpy as np
from mpi4py import MPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import dolfinx  # noqa: E402

from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE  # noqa: E402
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    build_four_port_sweep,
)

RUNGS = {"x1": 0.015, "x0.012": 0.012, "x0.0095": 0.0095}

# 4j's printed P1 top-5 (u_width, v_gap, var share %, area share %), per rung.
TOP5_4J = {
    # 20260912T033518Z_WF-6-step4j.log:2061
    "x1": [
        (0.193, 0.415, 33.34, 9.776),
        (0.216, 0.068, 19.34, 2.106),
        (0.727, 0.379, 17.26, 8.965),
        (0.833, 0.700, 14.61, 5.599),
        (0.288, 0.128, 5.70, 3.199),
    ],
    # 20260912T033918Z_WF-6-step4j-x0.012.log:2032
    "x0.012": [
        (0.195, 0.394, 27.62, 9.067),
        (0.823, 0.699, 20.38, 5.408),
        (0.211, 0.064, 20.05, 2.024),
        (0.726, 0.379, 13.32, 9.413),
        (0.797, 0.944, 6.36, 1.786),
    ],
    # 20260912T033518Z_WF-6-step4j.log:4108
    "x0.0095": [
        (0.164, 0.422, 42.25, 6.726),
        (0.309, 0.313, 9.94, 5.609),
        (0.267, 0.066, 8.58, 2.259),
        (0.246, 0.718, 7.47, 3.093),
        (0.359, 0.710, 7.10, 3.038),
    ],
}


def _tet_quality(x):
    """(radius ratio 3 r_in / R_circ, min dihedral angle in degrees) per tet; x (n,4,3)."""
    a = x[:, 1] - x[:, 0]
    b = x[:, 2] - x[:, 0]
    c = x[:, 3] - x[:, 0]
    vol6 = np.abs(np.einsum("ij,ij->i", a, np.cross(b, c)))
    faces = ((1, 2, 3), (0, 2, 3), (0, 1, 3), (0, 1, 2))
    s_tot = sum(
        0.5 * np.linalg.norm(np.cross(x[:, j] - x[:, i], x[:, k] - x[:, i]), axis=1)
        for i, j, k in faces
    )
    r_in = 0.5 * vol6 / s_tot  # 3V/S with V = vol6/6
    num = (
        np.einsum("ij,ij->i", a, a)[:, None] * np.cross(b, c)
        + np.einsum("ij,ij->i", b, b)[:, None] * np.cross(c, a)
        + np.einsum("ij,ij->i", c, c)[:, None] * np.cross(a, b)
    )
    r_circ = np.linalg.norm(num, axis=1) / (2.0 * vol6)
    dihedral = []
    for i, j, k, m in ((0, 1, 2, 3), (0, 2, 1, 3), (0, 3, 1, 2), (1, 2, 0, 3), (1, 3, 0, 2), (2, 3, 0, 1)):
        e = x[:, j] - x[:, i]
        n1 = np.cross(e, x[:, k] - x[:, i])
        n2 = np.cross(e, x[:, m] - x[:, i])
        cos = np.einsum("ij,ij->i", n1, n2) / (
            np.linalg.norm(n1, axis=1) * np.linalg.norm(n2, axis=1)
        )
        dihedral.append(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))
    return 3.0 * r_in / r_circ, np.min(dihedral, axis=0)


def _census(sweep, g, comm):
    msh = sweep["mesh"]
    tdim = msh.topology.dim
    fdim = tdim - 1
    msh.topology.create_connectivity(fdim, tdim)
    owned = int(msh.topology.index_map(fdim).size_local)
    spec = {s.port_id: s for s in sweep["specs"]}[f"P{g['tag'] - SHEET_IFACE}"]
    facets = np.asarray(sweep["facet_tags"].find(g["tag"]), dtype=np.int32)
    facets = facets[facets < owned]
    nodes = np.asarray(
        dolfinx.cpp.mesh.entities_to_geometry(msh._cpp_object, fdim, facets, False)
    )[:, :3]
    tri = msh.geometry.x[nodes]
    mid = np.asarray(dolfinx.mesh.compute_midpoints(msh, fdim, facets), dtype=np.float64)

    # --- 4j (u, v) mapping, verbatim from _sheet_profile
    #     (tests/validation/test_birdcage_b1_plus_closed_form.py:687, 715-720);
    #     at -n 1 every facet is evaluated, so mu = mid.
    d = spec.unit_drive() if hasattr(spec, "unit_drive") else (
        np.asarray(spec.drive_direction, dtype=float)
        / float(np.linalg.norm(spec.drive_direction))
    )
    mu = mid
    axis = int(g["axis"])
    wlo, whi = float(tri[:, :, axis].min()), float(tri[:, :, axis].max())
    zc = int(np.argmax(np.abs(d)))
    zlo, zhi = float(tri[:, :, zc].min()), float(tri[:, :, zc].max())
    u = np.clip((mu[:, axis] - wlo) / (whi - wlo), 0.0, 1.0 - 1e-12)
    v = np.clip((mu[:, zc] - zlo) / (zhi - zlo), 0.0, 1.0 - 1e-12)
    # --- end verbatim

    cr = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(cr, axis=1)
    edges = np.stack(
        [np.linalg.norm(tri[:, p] - tri[:, q], axis=1) for p, q in ((0, 1), (1, 2), (2, 0))],
        axis=1,
    )
    edge_ratio = edges.max(axis=1) / edges.min(axis=1)
    s = 0.5 * edges.sum(axis=1)
    r_in = area / s
    r_circ = edges.prod(axis=1) / (4.0 * area)
    tri_ratio = r_circ / r_in

    # Adjacent tets (worse of the two).
    f2c = msh.topology.connectivity(fdim, tdim)
    rho = np.empty(facets.size)
    dih = np.empty(facets.size)
    n_adj = np.empty(facets.size, dtype=int)
    for n, f in enumerate(facets):
        cells = np.asarray(f2c.links(int(f)), dtype=np.int32)
        cnodes = np.asarray(
            dolfinx.cpp.mesh.entities_to_geometry(msh._cpp_object, tdim, cells, False)
        )[:, :4]
        q_rho, q_dih = _tet_quality(msh.geometry.x[cnodes])
        rho[n], dih[n], n_adj[n] = q_rho.min(), q_dih.min(), cells.size

    # Sheet-boundary edges: used by exactly one sheet facet.
    edge_use = {}
    for n in range(facets.size):
        for p, q in ((0, 1), (1, 2), (2, 0)):
            key = tuple(sorted((int(nodes[n, p]), int(nodes[n, q]))))
            edge_use.setdefault(key, []).append(n)
    tol = 1e-6 * (zhi - zlo)
    zval = msh.geometry.x[:, zc]
    boundary_nodes = set()
    terminal = np.zeros(facets.size, dtype=bool)
    rim = np.zeros(facets.size, dtype=bool)
    for (p, q), users in edge_use.items():
        if len(users) != 1:
            continue
        boundary_nodes.update((p, q))
        on_end = all(
            abs(zval[k] - zlo) < tol or abs(zval[k] - zhi) < tol for k in (p, q)
        ) and (abs(zval[p] - zval[q]) < tol)
        if on_end:
            terminal[users[0]] = True
        else:
            rim[users[0]] = True
    touch = np.array(
        [bool(set(int(k) for k in nodes[n]) & boundary_nodes) for n in range(facets.size)]
    )
    return {
        "facets": facets,
        "tri": tri,
        "u": u,
        "v": v,
        "area": area,
        "area_share": area / area.sum(),
        "area_by_median": area / np.median(area),
        "edge_ratio": edge_ratio,
        "tri_ratio": tri_ratio,
        "tet_rho": rho,
        "tet_min_dihedral": dih,
        "n_adj": n_adj,
        "terminal": terminal,
        "rim": rim,
        "touch": touch,
        "boundary_edges": sum(1 for us in edge_use.values() if len(us) == 1),
    }


# Measures and the direction that is "bad" (for ranking worst-first).
MEASURES = [
    ("edge_ratio", "facet longest/shortest edge", "high"),
    ("tri_ratio", "facet R_circ/r_in (2 = equilateral)", "high"),
    ("area_by_median", "facet area / sheet median", "both"),
    ("tet_rho", "adjacent tet 3r/R, worse (1 = regular)", "low"),
    ("tet_min_dihedral", "adjacent tet min dihedral deg, worse", "low"),
]


def _describe(values, idx):
    """Rank (1 = smallest), percentile, IQR position of values[idx]."""
    n = values.size
    order = np.argsort(values, kind="stable")
    rank = int(np.nonzero(order == idx)[0][0]) + 1
    q1, q3 = np.percentile(values, [25, 75])
    x = values[idx]
    pos = "inside IQR" if q1 <= x <= q3 else ("below Q1" if x < q1 else "above Q3")
    return f"rank {rank:>2d}/{n} (asc) {pos}"


def main():
    comm = MPI.COMM_WORLD
    key = sys.argv[1]
    r = RUNGS[key]
    t0 = time.time()
    sweep = build_four_port_sweep(build_only=True, resolution=r, c4_congruent_sheets=True)
    t_build = time.time() - t0
    tdim = sweep["mesh"].topology.dim
    cells = comm.allreduce(sweep["mesh"].topology.index_map(tdim).size_local, op=MPI.SUM)
    if comm.rank != 0 or comm.size != 1:
        if comm.rank == 0:
            print("run at -n 1 (census gathers nothing)", flush=True)
        return
    print(
        f"[WF-6 step4k] rung {key}: resolution {r} m, c4_congruent_sheets=True, "
        f"{cells} cells (sweep['cells'] {sweep['cells']}), build {t_build:.1f} s, "
        f"{comm.size} rank(s) -- MEASUREMENT ONLY, no solve, nothing asserted",
        flush=True,
    )
    digest = hashlib.sha256()
    for g in sweep["sheets"]:
        pid = f"P{g['tag'] - SHEET_IFACE}"
        c = _census(sweep, g, comm)
        n = c["facets"].size
        digest.update(np.round(c["tri"], 12).tobytes())
        print(
            f"  [{pid}] facets {n} (sweep {g['facets']}), axis {g['axis']}, "
            f"area {c['area'].sum():.6e} m^2, sheet-boundary edges {c['boundary_edges']}, "
            f"adjacent tets per facet {sorted(set(c['n_adj'].tolist()))}",
            flush=True,
        )
        for name, label, _bad in MEASURES:
            vals = c[name]
            q1, med, q3 = np.percentile(vals, [25, 50, 75])
            print(
                f"      {label:<40s} min {vals.min():.4g}  Q1 {q1:.4g}  median {med:.4g}  "
                f"Q3 {q3:.4g}  max {vals.max():.4g}",
                flush=True,
            )
        if pid != "P1":
            continue
        # 4j top-5 facets: nearest (u, v), their ranks on every measure.
        print(f"    [P1] 4j top-5 ({key}) located by nearest (u, v):", flush=True)
        top_idx = []
        for k, (uu, vv, var, ash) in enumerate(TOP5_4J[key], 1):
            dist = np.hypot(c["u"] - uu, c["v"] - vv)
            i = int(np.argmin(dist))
            top_idx.append(i)
            print(
                f"      #{k} 4j ({uu:.3f}, {vv:.3f}) var {var:.2f}% area {ash:.3f}% -> facet "
                f"{int(c['facets'][i])} at ({c['u'][i]:.3f}, {c['v'][i]:.3f}) |duv| "
                f"{dist[i]:.1e}, area share {c['area_share'][i] * 100:.3f}%; flags: "
                f"terminal-edge {c['terminal'][i]} rim-edge {c['rim'][i]} "
                f"boundary-vertex {c['touch'][i]}",
                flush=True,
            )
            for name, label, _bad in MEASURES:
                print(
                    f"          {label:<40s} {c[name][i]:.4g}  {_describe(c[name], i)}",
                    flush=True,
                )
        print(
            "    [P1] every facet (u, v, area share %, edge ratio, R/r, area/median, "
            "tet 3r/R, tet min dihedral, T=terminal edge R=rim edge B=boundary vertex, "
            "* = 4j top-5 rank):",
            flush=True,
        )
        for i in np.lexsort((c["u"], c["v"])):
            mark = f"*{top_idx.index(i) + 1}" if i in top_idx else "  "
            flag = (
                ("T" if c["terminal"][i] else "-")
                + ("R" if c["rim"][i] else "-")
                + ("B" if c["touch"][i] else "-")
            )
            print(
                f"      {mark} ({c['u'][i]:.3f}, {c['v'][i]:.3f}) {c['area_share'][i] * 100:6.3f}  "
                f"{c['edge_ratio'][i]:6.3f}  {c['tri_ratio'][i]:6.3f}  "
                f"{c['area_by_median'][i]:6.3f}  {c['tet_rho'][i]:.4f}  "
                f"{c['tet_min_dihedral'][i]:7.3f}  {flag}",
                flush=True,
            )
        nt, nr, nb = int(c["terminal"].sum()), int(c["rim"].sum()), int(c["touch"].sum())
        print(
            f"    [P1] flag counts: terminal-edge {nt}/{n}, rim-edge {nr}/{n}, "
            f"boundary-vertex {nb}/{n}",
            flush=True,
        )
    print(
        f"[WF-6 step4k] rung {key}: sheet-geometry sha256 {digest.hexdigest()[:16]} "
        f"cells {cells} -- measurement only, no assertion",
        flush=True,
    )


if __name__ == "__main__":
    main()
