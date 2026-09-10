"""`GEO-31` — are the four port gap-sheets C4-*congruent*, or only equal in area?

Measurement only.  No solve, no linear algebra, real build, no `src/` change,
no band moved and no record re-registered.  Two things are asserted and they
are both self-tests: a reproduction of numbers `GEO-30` already measured on
this fixture, and a negative control on the probe's own metric.  Everything
else is printed.

**Why.**  `GEO-30` (`20260909T171106Z_GEO-30.log`) excluded the mesh as the
mechanism behind `ANS-4` step 2a's `Z` spreads and `WF-6` step 4f's P1/P2
power residual *in mass* (conductor spreads ≤ 0.33% at every rung) and *in
gap-sheet area* (the four sheet areas agree to 1e-15 at every rung), and
handed back exactly one quantity that tracks both failures: the gap-sheets'
**facet counts** are C4-equal on the two rungs that behaved (×1
**58/58/58/58**, `resolution` 0.012 **62/62/62/62**, spread 0) and **C2, not
C4**, on precisely the two that broke (×0.75 **80/74/80/74**, 0.0095
**70/76/70/76**) — opposite ports equal, adjacent ports differing, the same
class split as the two symptoms.  Four surfaces of identical area and
different triangulation is exactly the object the lumped-sheet port model
integrates over.  This probe reads the triangulations.

**Rungs and geometry.**  Imported, not rebuilt: ``RUNGS`` and ``_build_rung``
come from ``scripts/probes/geo30_birdcage_c4_refinement_census.py``, and the
``SHEET_IFACE + i`` facet-tag selection is that module's own
``_interface_facet_tags(mesh, cell_tags, {SHEET_IFACE + i: (PORT_LOWER + i,
PORT_UPPER + i)})`` with the same imported constants.  Nothing about the
geometry or the tags is re-derived here.

**Measured per rung, per sheet ``i = 1…4`` (port index; C4 image index
``i - 1``):**

1. facet count and total area, through `GEO-30`'s own
   ``_global_facet_count`` / ``_interface_area_or_zero`` so the two probes'
   tables are directly comparable;
2. the sorted per-facet-area vector with min / mean / max (plain numpy on the
   facets' node coordinates — no UFL);
3. ``d_i`` = the symmetric Hausdorff distance between sheet ``i``'s
   facet-**centroid** set and sheet 1's centroid set rotated by
   ``(i - 1)·90°`` about ``ẑ``;
4. the same metric on the **boundary-vertex** sets alone (a mesh edge is on
   the sheet boundary when exactly one of the group's facets carries it);
5. whether the four supports coincide under the rotation at all — the
   bounding boxes of sheet ``i`` and of the rotated sheet-1 image, and the
   max corner discrepancy between them.

**Asserted — and only these.**

(A) *Reproduction anchor.*  At the ×1 rung the four facet counts are
    58/58/58/58 exactly and at ``resolution`` 0.012 they are 62/62/62/62
    exactly (`GEO-30` measured spread 0.0000e+00 at both), and at both rungs
    the four sheet areas agree to ≤ 1e-3 relative (`GEO-30` measured
    6.050235e-16 and 8.4703e-16).  Without this the finer rungs compare with
    nothing.

(B) *Probe self-test / negative control.*  The metric of (3) applied to sheet
    1's centroid set against **itself rigidly displaced** by one mean facet
    edge length ``ℓ = sqrt(4A/(n·sqrt(3)))`` must read ≥ ``ℓ/2``, while the
    same metric on sheet 1 against itself must read **exactly 0.0**.  The
    displacement direction is ``(1,1,1)/sqrt(3)``; the sheets are planar with
    an axis-aligned normal, so its out-of-plane component is ``ℓ/sqrt(3) =
    0.577 ℓ > ℓ/2`` and the bar is arithmetic rather than predicted.  A metric
    that returns 0 regardless — the one failure mode that would make the whole
    table meaningless — fails this and nothing else would catch it.  This is a
    self-test of the metric, **not** a symmetry claim: the symmetry readings
    are the deliverable and are printed, never asserted (§9 rule (e)).

**Printed, asserted nowhere:** all of (1)–(5) at all four rungs side by side,
and the discriminator the review needs — *same support and same boundary but a
different interior cut* (a triangulation/quadrature question) versus
*different support or different boundary* (a generator defect in
``birdcage_port_domain``'s sheet emission).

**Rank-safety.**  ``facet_tags.find`` and ``mesh.geometry.x`` are rank-local
and include ghosts: the facet set is restricted to
``index_map(fdim).size_local`` (`OPS-39`), so every facet is carried by
exactly one rank, and the node coordinates and their *global* geometry indices
are ``comm.gather``ed to rank 0 before any comparison — a rank-local Hausdorff
is meaningless (`OPS-40`'s lesson).  Every Hausdorff distance is plain numpy on
a gathered array, never UFL; no ``sqrt`` and no ordering comparison appears
inside a UFL expression (`OPS-22`; `WF-6` step 4c).  The only UFL forms are
`GEO-30`'s imported ``avg(1)*dS`` area assemblies, which carry no
``SpatialCoordinate`` and so need no ``quadrature_degree`` pin (`POST-5`
step 1's trap does not apply, and is not invited).  Both asserts run on every
rank against ``bcast``ed scalars, after every collective, so a failure cannot
strand a rank inside a collective.

Run (real build, no solve, no complex mode)::

    mpiexec -n 2 python3 -u scripts/probes/geo31_birdcage_port_sheet_congruence.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

import dolfinx

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "scripts" / "probes") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts" / "probes"))

# The rung construction and the facet-tag selection are `GEO-30`'s, imported
# from its module rather than restated, so the two probes cannot drift apart.
import geo30_birdcage_c4_refinement_census as geo30  # noqa: E402

LEG_COUNT = geo30.LEG_COUNT
PORTS = tuple(range(1, LEG_COUNT + 1))

# `GEO-30`'s measured facet counts on the two rungs that behaved
# (`20260909T171106Z_GEO-30.log:7016, 7044` — spread 0.0000e+00 at both).
# Restated as printed records, on `GEO-30`'s own precedent for `GEO-28`'s.
GEO30_FACET_COUNTS = {
    "x1 / h=0.015": (58, 58, 58, 58),
    "resolution 0.012": (62, 62, 62, 62),
}
# `TH-15` step 2h's construction-identity tolerance on gap-sheet tags, the same
# one `GEO-30` asserted the sheet areas in; imported in value, unmoved.
SHEET_AREA_BAND = geo30.SHEET_AREA_BAND

# The negative control's displacement direction; see the docstring for why its
# out-of-plane component makes the >= l/2 bar arithmetic.
DISPLACEMENT_DIR = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)


def _print(text, comm):
    if comm.rank == 0:
        print(text, flush=True)


def _spread(values):
    v = np.asarray(values, dtype=float)
    mean = v.mean()
    if mean == 0.0:
        return float("nan")
    return float((v.max() - v.min()) / mean)


def _gather_sheet(mesh, sheet_tags, tag, comm):
    """Owned facets of group ``tag`` as (coords, global node ids) on rank 0.

    ``coords`` is ``(n, 3, 3)`` — three nodes per triangle — and ``gids`` is
    ``(n, 3)`` of *global* geometry indices, which is what makes the shared-edge
    bookkeeping below well defined across the partition.  Ghost facets are
    dropped by the ``size_local`` restriction, so every facet appears once.
    """
    fdim = mesh.topology.dim - 1
    n_owned = int(mesh.topology.index_map(fdim).size_local)
    facets = np.asarray(sheet_tags.find(tag), dtype=np.int32)
    facets = facets[facets < n_owned]
    if facets.size:
        nodes = np.asarray(
            dolfinx.cpp.mesh.entities_to_geometry(
                mesh._cpp_object, fdim, facets, False
            )
        ).reshape(facets.size, -1)[:, :3]
        coords = mesh.geometry.x[nodes.reshape(-1)].reshape(-1, 3, 3).copy()
        gids = (
            np.asarray(
                mesh.geometry.index_map().local_to_global(
                    nodes.reshape(-1).astype(np.int32)
                )
            )
            .reshape(-1, 3)
            .astype(np.int64)
        )
    else:
        coords = np.zeros((0, 3, 3), dtype=float)
        gids = np.zeros((0, 3), dtype=np.int64)
    chunks = comm.gather((coords, gids), root=0)
    if comm.rank != 0:
        return None
    coords = np.concatenate([c[0] for c in chunks], axis=0)
    gids = np.concatenate([c[1] for c in chunks], axis=0)
    return coords, gids


def _facet_areas(coords):
    e1 = coords[:, 1, :] - coords[:, 0, :]
    e2 = coords[:, 2, :] - coords[:, 0, :]
    return 0.5 * np.linalg.norm(np.cross(e1, e2), axis=1)


def _boundary_vertices(coords, gids):
    """Coordinates of the vertices on the *boundary* of the triangulated sheet.

    A mesh edge belongs to the sheet's boundary when exactly one facet of the
    group carries it; the boundary vertices are that edge set's endpoints.
    Edges are keyed on **global** node ids, so the answer does not depend on
    how the facets were distributed.
    """
    if coords.shape[0] == 0:
        return np.zeros((0, 3), dtype=float)
    coord_of = {}
    for tri, g in zip(coords, gids):
        for k in range(3):
            coord_of[int(g[k])] = tri[k]
    counts = {}
    for g in gids:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            key = (int(min(g[a], g[b])), int(max(g[a], g[b])))
            counts[key] = counts.get(key, 0) + 1
    on_boundary = set()
    for (a, b), n in counts.items():
        if n == 1:
            on_boundary.add(a)
            on_boundary.add(b)
    return np.array([coord_of[g] for g in sorted(on_boundary)], dtype=float)


def _rotate_z(points, turns):
    """Rotate about ``ẑ`` by ``turns`` quarter-turns, with exact 90° entries."""
    angle = 0.5 * np.pi * turns
    c, s = float(np.cos(angle)), float(np.sin(angle))
    for exact in (-1.0, 0.0, 1.0):
        if abs(c - exact) < 1.0e-12:
            c = exact
        if abs(s - exact) < 1.0e-12:
            s = exact
    r = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    return points @ r.T


def _hausdorff(a, b):
    """Symmetric Hausdorff distance between two point sets.  Plain numpy."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape[0] == 0 or b.shape[0] == 0:
        return float("nan")
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    return float(max(d.min(axis=1).max(), d.min(axis=0).max()))


def _bbox(points):
    if points.shape[0] == 0:
        return np.full(3, np.nan), np.full(3, np.nan)
    return points.min(axis=0), points.max(axis=0)


def _bbox_discrepancy(a, b):
    lo_a, hi_a = _bbox(a)
    lo_b, hi_b = _bbox(b)
    return float(np.max(np.abs(np.concatenate([lo_a - lo_b, hi_a - hi_b]))))


def _measure_rung(mesh, cell_tags, comm):
    """Every quantity of one rung.  All collectives live here."""
    sheet_tags = geo30._interface_facet_tags(
        mesh,
        cell_tags,
        {
            geo30.SHEET_IFACE + i: (geo30.PORT_LOWER + i, geo30.PORT_UPPER + i)
            for i in PORTS
        },
    )
    # (1) — through `GEO-30`'s own helpers, so the tables are comparable.
    counts = [
        geo30._global_facet_count(mesh, sheet_tags, geo30.SHEET_IFACE + i, comm)
        for i in PORTS
    ]
    areas = [
        geo30._interface_area_or_zero(mesh, sheet_tags, geo30.SHEET_IFACE + i, comm)
        for i in PORTS
    ]
    gathered = [
        _gather_sheet(mesh, sheet_tags, geo30.SHEET_IFACE + i, comm) for i in PORTS
    ]
    if comm.rank != 0:
        return {"counts": counts, "areas": areas}

    out = {"counts": counts, "areas": areas, "sheets": []}
    for idx, (coords, gids) in enumerate(gathered):
        a = _facet_areas(coords)
        out["sheets"].append(
            {
                "n_gathered": int(coords.shape[0]),
                "facet_area": np.sort(a),
                "centroids": coords.mean(axis=1),
                "boundary": _boundary_vertices(coords, gids),
                "vertices": coords.reshape(-1, 3),
            }
        )
    return out


def _analyse(rung, label):
    """Rank-0 only: (3), (4), (5) and the negative control for one rung."""
    sheets = rung["sheets"]
    ref = sheets[0]
    rung["d_centroid"] = []
    rung["d_boundary"] = []
    rung["bbox_delta_all"] = []
    rung["bbox_delta_boundary"] = []
    rung["n_boundary"] = [s["boundary"].shape[0] for s in sheets]
    for i, s in enumerate(sheets):
        rot_c = _rotate_z(ref["centroids"], i)
        rot_b = _rotate_z(ref["boundary"], i)
        rot_v = _rotate_z(ref["vertices"], i)
        rung["d_centroid"].append(_hausdorff(s["centroids"], rot_c))
        rung["d_boundary"].append(_hausdorff(s["boundary"], rot_b))
        rung["bbox_delta_all"].append(_bbox_discrepancy(s["vertices"], rot_v))
        rung["bbox_delta_boundary"].append(_bbox_discrepancy(s["boundary"], rot_b))

    # sorted-per-facet-area comparison, only where the counts allow it
    rung["sorted_area_delta"] = []
    for s in sheets:
        if s["facet_area"].shape[0] == ref["facet_area"].shape[0]:
            denom = ref["facet_area"].mean()
            rung["sorted_area_delta"].append(
                float(np.max(np.abs(s["facet_area"] - ref["facet_area"])) / denom)
            )
        else:
            rung["sorted_area_delta"].append(float("nan"))

    # the negative control (B), computed in-probe on this rung's own numbers
    n = ref["facet_area"].shape[0]
    total = float(ref["facet_area"].sum())
    ell = float(np.sqrt(4.0 * total / (n * np.sqrt(3.0)))) if n else float("nan")
    rung["ell"] = ell
    rung["ctl_zero"] = _hausdorff(ref["centroids"], ref["centroids"])
    rung["ctl_shift"] = _hausdorff(
        ref["centroids"], ref["centroids"] + ell * DISPLACEMENT_DIR
    )
    rung["label"] = label
    return rung


def main():
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    _print(
        "\n[GEO-31] triangulation congruence of the four birdcage port "
        "gap-sheets under the C4 rotation (no solve; asserts one reproduction "
        "anchor and one probe self-test, nothing else)\n"
        f"[GEO-31] ranks={comm.size}  rungs and geometry imported verbatim "
        "from scripts/probes/geo30_birdcage_c4_refinement_census.py; facet "
        f"tags are its SHEET_IFACE+i = {geo30.SHEET_IFACE}+i selection\n"
        f"[GEO-31] CONDUCTOR_RESOLUTION={geo30.CONDUCTOR_RESOLUTION:.6e} m  "
        f"RESOLUTION={float(geo30.RESOLUTION):.6e} m",
        comm,
    )

    rows = {}
    order = []
    for label, h_c, h in geo30.RUNGS:
        _print(f"\n[GEO-31] --- rung {label} ---", comm)
        mesh, cell_tags, diag, rung_s = geo30._build_rung(h_c, h, comm)
        row = _measure_rung(mesh, cell_tags, comm)
        size_global = int(mesh.topology.index_map(mesh.topology.dim).size_global)
        if comm.rank == 0:
            row = _analyse(row, label)
            row["size_global"] = size_global
            row["mesh_s"] = float(diag["mesh_wall_time_s"])
            row["rung_s"] = float(rung_s)
        rows[label] = row
        order.append(label)
        _print(
            f"[GEO-31] {label}: size_global={size_global}  "
            f"mesh={float(diag['mesh_wall_time_s']):.2f} s  "
            f"rung={rung_s:.2f} s  facets={row['counts']}",
            comm,
        )
        del mesh, cell_tags

    elapsed = time.perf_counter() - started

    # ---- the table (printed; asserted nowhere) -----------------------------
    payload = None
    if comm.rank == 0:
        print(
            "\n[GEO-31] === the table: (1)-(5) at four rungs, columns P1..P4 "
            "(P1 is the C4 reference; Pi is compared against P1 rotated by "
            "(i-1)*90 deg about z) ==="
        )
        for label in order:
            r = rows[label]
            print(
                f"\n  rung {label}  (size_global={r['size_global']}, "
                f"mesh {r['mesh_s']:.2f} s, l={r['ell']:.6e} m)"
            )
            print(
                "    (1) facet count            "
                + "  ".join(f"{c:13d}" for c in r["counts"])
                + f"   spread={_spread(r['counts']):.4e}"
            )
            print(
                "    (1) gathered facets        "
                + "  ".join(f"{s['n_gathered']:13d}" for s in r["sheets"])
            )
            print(
                "    (1) total area [m^2]       "
                + "  ".join(f"{a:.6e}" for a in r["areas"])
                + f"   spread={_spread(r['areas']):.4e}"
            )
            for key, name in (
                ("min", "(2) facet area min [m^2]  "),
                ("mean", "(2) facet area mean [m^2] "),
                ("max", "(2) facet area max [m^2]  "),
            ):
                vals = [getattr(s["facet_area"], key)() for s in r["sheets"]]
                print(
                    f"    {name} "
                    + "  ".join(f"{v:.6e}" for v in vals)
                    + f"   spread={_spread(vals):.4e}"
                )
            print(
                "    (2) |sorted(Pi)-sorted(P1)|_inf / mean(P1)  "
                + "  ".join(f"{v:.6e}" for v in r["sorted_area_delta"])
                + "   (nan = facet counts differ, vectors not comparable)"
            )
            print(
                "    (3) d_i centroids [m]      "
                + "  ".join(f"{v:.6e}" for v in r["d_centroid"])
            )
            print(
                "    (4) d_i boundary verts [m] "
                + "  ".join(f"{v:.6e}" for v in r["d_boundary"])
            )
            print(
                "    (4) boundary vertex count  "
                + "  ".join(f"{v:13d}" for v in r["n_boundary"])
            )
            print(
                "    (5) bbox delta, all verts  "
                + "  ".join(f"{v:.6e}" for v in r["bbox_delta_all"])
            )
            print(
                "    (5) bbox delta, boundary   "
                + "  ".join(f"{v:.6e}" for v in r["bbox_delta_boundary"])
            )
            print(
                f"    (3) d_i / l                "
                + "  ".join(f"{v / r['ell']:13.6f}" for v in r["d_centroid"])
            )

        print(
            "\n[GEO-31] === sorted per-facet-area vectors [m^2] "
            "(printed in full; asserted nowhere) ==="
        )
        for label in order:
            r = rows[label]
            print(f"\n  rung {label}")
            for i, s in enumerate(r["sheets"]):
                v = s["facet_area"]
                print(f"    P{i + 1}  n={v.shape[0]}")
                for start in range(0, v.shape[0], 6):
                    print(
                        "        "
                        + "  ".join(f"{x:.9e}" for x in v[start : start + 6])
                    )

        # ---- the discriminator the review reads off the table, stated in
        # words and derived here from the measured columns above -- never
        # hardcoded, and asserted nowhere (rule (e)).
        print(
            "\n[GEO-31] === the discriminator (derived from (3)-(5) above; "
            "printed, asserted nowhere) ==="
        )
        for label in order:
            r = rows[label]
            ell = r["ell"]
            sup = max(r["bbox_delta_all"] + r["bbox_delta_boundary"])
            bdry = max(r["d_boundary"])
            cut = max(r["d_centroid"])
            # scale-free readings: a support or boundary that differs does so
            # by a fraction of a facet edge length, not by round-off.
            if sup > 1.0e-3 * ell:
                verdict = "DIFFERENT SUPPORT — a generator defect in the sheet emission"
            elif bdry > 1.0e-3 * ell:
                verdict = "SAME SUPPORT, DIFFERENT BOUNDARY — a generator defect in the sheet emission"
            elif cut > 1.0e-3 * ell:
                verdict = (
                    "SAME SUPPORT AND SAME BOUNDARY, DIFFERENT INTERIOR CUT — "
                    "a triangulation/quadrature question, not a generator defect"
                )
            else:
                verdict = (
                    "C4-CONGRUENT TO MESH ROUND-OFF — the sheet is excluded too"
                )
            print(
                f"  {label:<26s} max bbox delta={sup:.6e} m ({sup / ell:.3e} l)"
                f"  max d_boundary={bdry:.6e} m ({bdry / ell:.3e} l)"
                f"  max d_centroid={cut:.6e} m ({cut / ell:.3e} l)\n"
                f"  {'':<26s} => {verdict}"
            )

        print(
            "\n[GEO-31] === the two asserted self-tests ===\n"
            "  (A) reproduction anchor — `GEO-30`'s facet counts and sheet-area "
            "agreement on the two rungs that behaved"
        )
        for label, expect in GEO30_FACET_COUNTS.items():
            r = rows[label]
            print(
                f"        {label:<22s} counts={tuple(r['counts'])} vs GEO-30 "
                f"{expect}   area spread={_spread(r['areas']):.6e} vs band "
                f"{SHEET_AREA_BAND:.0e}"
            )
        ctl = rows[geo30.CONTROL_LABEL]
        print(
            f"  (B) probe self-test / negative control on the x1 rung's sheet "
            f"P1 (l = sqrt(4A/(n*sqrt(3))) = {ctl['ell']:.6e} m from "
            f"A={ctl['areas'][0]:.6e} m^2, n={ctl['counts'][0]})\n"
            f"        d(P1, P1)             = {ctl['ctl_zero']:.6e} m   "
            f"(must be exactly 0.0)\n"
            f"        d(P1, P1 + l*(1,1,1)/sqrt(3)) = {ctl['ctl_shift']:.6e} m "
            f"= {ctl['ctl_shift'] / ctl['ell']:.6f} l   (bar l/2 = "
            f"{0.5 * ctl['ell']:.6e} m)"
        )
        print(f"[GEO-31] probe wall time={elapsed:.2f} s", flush=True)

        payload = {
            "anchor_counts": {
                label: tuple(int(c) for c in rows[label]["counts"])
                for label in GEO30_FACET_COUNTS
            },
            "anchor_area_spread": {
                label: _spread(rows[label]["areas"]) for label in GEO30_FACET_COUNTS
            },
            "ell": ctl["ell"],
            "ctl_zero": ctl["ctl_zero"],
            "ctl_shift": ctl["ctl_shift"],
        }

    payload = comm.bcast(payload, root=0)

    # ---- the two asserts.  Every collective above is complete and every value
    # below is bcast, so asserting on all ranks cannot strand one.
    for label, expect in GEO30_FACET_COUNTS.items():
        got = payload["anchor_counts"][label]
        assert got == expect, (
            f"(A) the {label} rung's gap-sheet facet counts read {got} against "
            f"`GEO-30`'s {expect} — this is not the mesh `GEO-30` censused, so "
            "no rung below compares with anything"
        )
        spread = payload["anchor_area_spread"][label]
        assert spread <= SHEET_AREA_BAND, (
            f"(A) the {label} rung's four gap-sheet areas spread {spread:.6e}, "
            f"past the imported, unmoved {SHEET_AREA_BAND:.0e} — `GEO-30` "
            "measured 1e-15 here"
        )
    assert payload["ctl_zero"] == 0.0, (
        f"(B) the congruence metric read {payload['ctl_zero']:.6e} for a set "
        "against itself; it is not a distance"
    )
    assert payload["ctl_shift"] >= 0.5 * payload["ell"], (
        f"(B) the congruence metric read {payload['ctl_shift']:.6e} m for a set "
        f"against itself displaced by l={payload['ell']:.6e} m, under the l/2 "
        f"bar {0.5 * payload['ell']:.6e} m — this metric cannot tell a C4 image "
        "from a non-image and the whole table above means nothing"
    )
    _print(
        "[GEO-31] both asserted self-tests green; every symmetry reading above "
        "is printed and asserted nowhere.",
        comm,
    )


if __name__ == "__main__":
    main()
