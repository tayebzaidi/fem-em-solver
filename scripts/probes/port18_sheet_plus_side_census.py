"""`PORT-18` — does the lumped-sheet port read a discontinuous normal component
off a cut-dependent ``'+'`` side?

Measurement only.  No solve, no linear algebra, real build, no `src/` change,
no band moved and no record re-registered.  Asserted: (A) a partition identity,
(B) an interpolation-exactness closed form, and a negative control on the
spread metric.  Everything else is printed (§9 rule (e)).

**Why.**  `GEO-31` (``20260910T003835Z_GEO-31.log:7270-7286``) found the four
port gap-sheets are the same patch with a *different interior cut* on every
rung, ×1 included.  ``sheet_terminal_current`` and ``lumped_port_linear_term``
(``src/fem_em_solver/ports/lumped.py:306, 333``) restrict ``E`` / ``v`` to
``'+'`` and dot it with ``ĥ = ẑ`` (the fixture's ``drive_direction``,
``tests/validation/test_port_birdcage_four_port.py:397``).  If the sheet normal
is ``±ẑ`` that is the *normal* component, which N1curl leaves discontinuous,
and which cell is ``'+'`` is a per-facet property of the cut.

**Rungs, geometry, tags.**  Imported verbatim: ``RUNGS`` / ``_build_rung`` from
``scripts/probes/geo30_birdcage_c4_refinement_census.py`` and `GEO-31`'s
``SHEET_IFACE + i`` selection (``geo30._interface_facet_tags`` with
``{SHEET_IFACE + i: (PORT_LOWER + i, PORT_UPPER + i)}``).

**Measured per rung, per sheet** (§7 `PORT-18` row):

0. premise ``∫(n('+')·ẑ)² dS / A_i``;
1. ``f_i = ∫χ_L('+') dS / A_i``, ``χ_L`` the DG0 indicator of ``PORT_LOWER+i``
   (owned values set from ``cell_tags``, then ``scatter_forward`` onto ghosts);
2. ``E = ẑ cos(2π(z − z̄)/λ)(1 + (x²+y²)/ρ₀²)`` interpolated into N1curl
   degree 1; ``R^+``, ``R^−``, ``R^avg`` at ``q ∈ {2, 4, 8}`` and the expression
   comparand ``∫g dS / A_i`` at ``q = 8``; four-sheet spreads
   ``(max − min)/|mean|``.  ``z̄`` = mean sheet-centroid height, ``λ`` = 4 × the
   gap height (z-extent of the ``PORT_LOWER+i ∪ PORT_UPPER+i`` cells, the
   terminal separation along ``ĥ = ẑ``), ``ρ₀`` = mean sheet-centroid radius
   (the radius the negative control's ``x̄_i = ρ₀ cos θ_i`` needs); all measured
   and printed;
3. (1) again at ``-n 1`` on ×1 and ×0.75 — a separate invocation with
   ``--rungs 0,1``.

**Asserted.**  (A) ``|∫(χ_L+χ_U)('+') dS − A_i| / A_i ≤ 1e-12``.  (B)
``E_lin = (−z/ρ₀, 0, 1 + x/ρ₀)`` = ``a + b × x`` is exact in N1curl degree 1:
``R_i^± = 1 + x̄_i/ρ₀`` at ``q = 2``.  The relative denominator is
``max(|1 + x̄_i/ρ₀|, 1)`` — the sheet at θ = 180° has ``1 + x̄_i/ρ₀ ≈ 0``, where
a bare relative error is undefined; ``1`` is ``E_lin``'s own constant scale.
Negative control: the ``E_lin`` four-sheet ``R^+`` spread ≥ 1.40.

**Traps.**  Every facet form pins ``quadrature_degree`` (`POST-5`); every
interior-facet argument is restricted; no UFL comparison or ``sqrt``
(`OPS-22`); every assembled number is allreduced; asserts run on every rank
after all collectives against bcast values.

Run (real build)::

    mpiexec -n 2 python3 -u scripts/probes/port18_sheet_plus_side_census.py
    mpiexec -n 1 python3 -u scripts/probes/port18_sheet_plus_side_census.py --rungs 0,1
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

import dolfinx
import ufl
from dolfinx import default_scalar_type, fem

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "scripts" / "probes") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts" / "probes"))

import geo30_birdcage_c4_refinement_census as geo30  # noqa: E402

LEG_COUNT = geo30.LEG_COUNT
PORTS = tuple(range(1, LEG_COUNT + 1))
QUAD_DEGREES = (2, 4, 8)

PARTITION_BAND = 1.0e-12
EXACTNESS_BAND = 1.0e-9
NEG_CONTROL_BAR = 1.40
PREMISE_BAND = 1.0e-6  # "far from 1" reading for (0); printed verdict only

# `ANS-4` step 2a's Z class spreads [%], known-issues 2026-09-09 — printed
# beside the table as records, on `GEO-30`'s precedent (its docstring line 7).
ANS4_CLASS_SPREADS_PCT = {
    "x1 / h=0.015": (0.1012, 0.0916, 0.0654),
    "conductor_resolution x0.75": (0.5390, 0.4591, 1.6886),
}
BEHAVED = ("x1 / h=0.015", "resolution 0.012")
BROKE = ("conductor_resolution x0.75", "resolution 0.0095")


def _print(text, comm):
    if comm.rank == 0:
        print(text, flush=True)


def _spread(values):
    v = np.asarray(values, dtype=float)
    mean = v.mean()
    if mean == 0.0:
        return float("nan")
    return float((v.max() - v.min()) / abs(mean))


class _PerSheet:
    """One compiled form per quantity, four assemblies selected by Constants."""

    def __init__(self, mesh, sheet_tags, comm):
        self.mesh = mesh
        self.sheet_tags = sheet_tags
        self.comm = comm
        self.w = [fem.Constant(mesh, default_scalar_type(0.0)) for _ in PORTS]

    def eval(self, builder, q):
        dS = ufl.Measure(
            "dS",
            domain=self.mesh,
            subdomain_data=self.sheet_tags,
            metadata={"quadrature_degree": int(q)},
        )
        integrand = None
        for k, i in enumerate(PORTS):
            term = self.w[k] * builder(i) * dS(geo30.SHEET_IFACE + i)
            integrand = term if integrand is None else integrand + term
        form = fem.form(integrand)
        out = []
        for k in range(len(PORTS)):
            for j, c in enumerate(self.w):
                c.value = 1.0 if j == k else 0.0
            local = fem.assemble_scalar(form)
            out.append(float(np.real(self.comm.allreduce(local, op=MPI.SUM))))
        return out


def _indicator(Q, cell_tags, tag, n_owned):
    chi = fem.Function(Q)
    chi.x.array[:] = 0.0
    idx = np.asarray(cell_tags.indices)
    val = np.asarray(cell_tags.values)
    keep = (idx < n_owned) & (val == tag)
    dofs = np.asarray(Q.dofmap.list)[idx[keep], 0]
    chi.x.array[dofs] = 1.0
    chi.x.scatter_forward()
    return chi


def _port_box_z_extent(mesh, cell_tags, i, comm):
    tdim = mesh.topology.dim
    n_owned = int(mesh.topology.index_map(tdim).size_local)
    idx = np.asarray(cell_tags.indices)
    val = np.asarray(cell_tags.values)
    keep = (idx < n_owned) & (
        (val == geo30.PORT_LOWER + i) | (val == geo30.PORT_UPPER + i)
    )
    dofmap = np.asarray(mesh.geometry.dofmap).reshape(-1, 4)
    z = mesh.geometry.x[dofmap[idx[keep], :4].reshape(-1), 2]
    zmin = float(z.min()) if z.size else np.inf
    zmax = float(z.max()) if z.size else -np.inf
    zmin = comm.allreduce(zmin, op=MPI.MIN)
    zmax = comm.allreduce(zmax, op=MPI.MAX)
    return zmin, zmax


def _sheet_bbox(mesh, sheet_tags, tag, comm):
    fdim = mesh.topology.dim - 1
    n_owned = int(mesh.topology.index_map(fdim).size_local)
    facets = np.asarray(sheet_tags.find(tag), dtype=np.int32)
    facets = facets[facets < n_owned]
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    if facets.size:
        nodes = np.asarray(
            dolfinx.cpp.mesh.entities_to_geometry(mesh._cpp_object, fdim, facets, False)
        ).reshape(facets.size, -1)[:, :3]
        pts = mesh.geometry.x[nodes.reshape(-1)]
        lo = pts.min(axis=0)
        hi = pts.max(axis=0)
    lo = np.array([comm.allreduce(float(v), op=MPI.MIN) for v in lo])
    hi = np.array([comm.allreduce(float(v), op=MPI.MAX) for v in hi])
    return hi - lo


def _measure_rung(mesh, cell_tags, comm):
    tdim = mesh.topology.dim
    sheet_tags = geo30._interface_facet_tags(
        mesh,
        cell_tags,
        {
            geo30.SHEET_IFACE + i: (geo30.PORT_LOWER + i, geo30.PORT_UPPER + i)
            for i in PORTS
        },
    )
    counts = [
        geo30._global_facet_count(mesh, sheet_tags, geo30.SHEET_IFACE + i, comm)
        for i in PORTS
    ]
    areas = [
        geo30._interface_area_or_zero(mesh, sheet_tags, geo30.SHEET_IFACE + i, comm)
        for i in PORTS
    ]
    ps = _PerSheet(mesh, sheet_tags, comm)
    x = ufl.SpatialCoordinate(mesh)
    n = ufl.FacetNormal(mesh)
    A = np.asarray(areas)
    r = {"counts": counts, "areas": areas}

    r["area_q2"] = ps.eval(lambda i: fem.Constant(mesh, default_scalar_type(1.0)), 2)
    # (0) premise
    r["premise"] = list(np.asarray(ps.eval(lambda i: n("+")[2] * n("+")[2], 2)) / A)
    # (1) '+'-side lower fraction and (A) partition identity
    n_owned = int(mesh.topology.index_map(tdim).size_local)
    Q = fem.functionspace(mesh, ("DG", 0))
    chiL = {i: _indicator(Q, cell_tags, geo30.PORT_LOWER + i, n_owned) for i in PORTS}
    chiU = {i: _indicator(Q, cell_tags, geo30.PORT_UPPER + i, n_owned) for i in PORTS}
    r["f"] = list(np.asarray(ps.eval(lambda i: chiL[i]("+"), 2)) / A)
    r["f_minus"] = list(np.asarray(ps.eval(lambda i: chiL[i]("-"), 2)) / A)
    part = np.asarray(ps.eval(lambda i: (chiL[i] + chiU[i])("+"), 2))
    r["partition_int"] = list(part)
    r["partition_rel"] = list(np.abs(part - A) / A)
    # centroids
    xb = np.asarray(ps.eval(lambda i: x("+")[0], 2)) / A
    yb = np.asarray(ps.eval(lambda i: x("+")[1], 2)) / A
    zb = np.asarray(ps.eval(lambda i: x("+")[2], 2)) / A
    r["xbar"], r["ybar"], r["zbar_i"] = list(xb), list(yb), list(zb)
    rho0 = float(np.mean(np.hypot(xb, yb)))
    zbar = float(np.mean(zb))
    zext = [_port_box_z_extent(mesh, cell_tags, i, comm) for i in PORTS]
    gap_h = float(np.mean([hi - lo for lo, hi in zext]))
    lam = 4.0 * gap_h
    r["rho0"], r["zbar"], r["gap_h"], r["lam"] = rho0, zbar, gap_h, lam
    r["gap_h_i"] = [hi - lo for lo, hi in zext]
    r["sheet_bbox"] = [
        _sheet_bbox(mesh, sheet_tags, geo30.SHEET_IFACE + i, comm) for i in PORTS
    ]

    # (2) smooth C4-invariant field in N1curl degree 1
    V = fem.functionspace(mesh, ("N1curl", 1))
    Es = fem.Function(V)
    Es.interpolate(
        lambda X: np.vstack(
            (
                np.zeros(X.shape[1]),
                np.zeros(X.shape[1]),
                np.cos(2.0 * np.pi * (X[2] - zbar) / lam)
                * (1.0 + (X[0] ** 2 + X[1] ** 2) / rho0**2),
            )
        )
    )
    Es.x.scatter_forward()
    r["Rp"], r["Rm"], r["Ravg"] = {}, {}, {}
    for q in QUAD_DEGREES:
        r["Rp"][q] = list(np.asarray(ps.eval(lambda i: Es("+")[2], q)) / A)
        r["Rm"][q] = list(np.asarray(ps.eval(lambda i: Es("-")[2], q)) / A)
        r["Ravg"][q] = list(np.asarray(ps.eval(lambda i: ufl.avg(Es)[2], q)) / A)
    zc = fem.Constant(mesh, default_scalar_type(zbar))
    lc = fem.Constant(mesh, default_scalar_type(lam))
    rc = fem.Constant(mesh, default_scalar_type(rho0))
    r["expr"] = list(
        np.asarray(
            ps.eval(
                lambda i: ufl.cos(2.0 * ufl.pi * (x("+")[2] - zc) / lc)
                * (1.0 + (x("+")[0] * x("+")[0] + x("+")[1] * x("+")[1]) / (rc * rc)),
                8,
            )
        )
        / A
    )

    # (B) E_lin exactness and the negative control
    El = fem.Function(V)
    El.interpolate(
        lambda X: np.vstack(
            (-X[2] / rho0, np.zeros(X.shape[1]), 1.0 + X[0] / rho0)
        )
    )
    El.x.scatter_forward()
    r["Lp"] = list(np.asarray(ps.eval(lambda i: El("+")[2], 2)) / A)
    r["Lm"] = list(np.asarray(ps.eval(lambda i: El("-")[2], 2)) / A)
    r["Lavg"] = list(np.asarray(ps.eval(lambda i: ufl.avg(El)[2], 2)) / A)
    target = 1.0 + xb / rho0
    denom = np.maximum(np.abs(target), 1.0)
    r["L_target"] = list(target)
    r["Lp_rel"] = list(np.abs(np.asarray(r["Lp"]) - target) / denom)
    r["Lm_rel"] = list(np.abs(np.asarray(r["Lm"]) - target) / denom)
    r["size_global"] = int(mesh.topology.index_map(tdim).size_global)
    return r


def _fmt(vals, f="{:.10e}"):
    return "  ".join(f.format(v) for v in vals)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rungs", default="0,1,2,3")
    args = parser.parse_args()
    sel = [int(s) for s in args.rungs.split(",") if s.strip()]

    comm = MPI.COMM_WORLD
    started = time.perf_counter()
    _print(
        "\n[PORT-18] '+'-side census of the four birdcage port gap-sheets "
        "(no solve; asserts (A) partition identity, (B) E_lin exactness, "
        "negative control; everything else printed)\n"
        f"[PORT-18] ranks={comm.size}  rungs={[geo30.RUNGS[k][0] for k in sel]}  "
        f"SHEET_IFACE={geo30.SHEET_IFACE} PORT_LOWER={geo30.PORT_LOWER} "
        f"PORT_UPPER={geo30.PORT_UPPER}",
        comm,
    )

    rows, order = {}, []
    for k in sel:
        label, h_c, h = geo30.RUNGS[k]
        _print(f"\n[PORT-18] --- rung {label} ---", comm)
        mesh, cell_tags, diag, rung_s = geo30._build_rung(h_c, h, comm)
        t0 = time.perf_counter()
        row = _measure_rung(mesh, cell_tags, comm)
        row["measure_s"] = time.perf_counter() - t0
        row["mesh_s"] = float(diag["mesh_wall_time_s"])
        rows[label] = row
        order.append(label)
        _print(
            f"[PORT-18] {label}: size_global={row['size_global']} "
            f"mesh={row['mesh_s']:.2f} s rung={rung_s:.2f} s "
            f"measure={row['measure_s']:.2f} s facets={row['counts']}",
            comm,
        )
        del mesh, cell_tags

    elapsed = time.perf_counter() - started
    payload = None
    if comm.rank == 0:
        print(
            "\n[PORT-18] === per-rung table (columns P1..P4; printed, asserted "
            "nowhere except where marked [A]/[B]) ==="
        )
        for label in order:
            r = rows[label]
            print(
                f"\n  rung {label}  (size_global={r['size_global']}, "
                f"ranks={comm.size})"
            )
            print(f"    facets                      {r['counts']}")
            print(f"    area A_i [m^2]              {_fmt(r['areas'])}  spread={_spread(r['areas']):.3e}")
            print(f"    area (q=2 const) [m^2]      {_fmt(r['area_q2'])}")
            print(f"    x_bar_i [m]                 {_fmt(r['xbar'])}")
            print(f"    y_bar_i [m]                 {_fmt(r['ybar'])}")
            print(f"    z_bar_i [m]                 {_fmt(r['zbar_i'])}")
            print(
                f"    rho0={r['rho0']:.10e} m (RING_RADIUS={geo30.RING_RADIUS})  "
                f"z_bar={r['zbar']:.10e} m  gap_h={r['gap_h']:.10e} m "
                f"(per sheet {_fmt(r['gap_h_i'], '{:.6e}')}; LEG_GAP_LENGTH="
                f"{geo30.LEG_GAP_LENGTH})  lambda={r['lam']:.10e} m"
            )
            print(
                "    sheet bbox extents dx,dy,dz "
                + "  ".join(
                    "(" + ",".join(f"{v:.3e}" for v in b) + ")" for b in r["sheet_bbox"]
                )
            )
            print(f"    (0) premise int(n+.z)^2/A   {_fmt(r['premise'], '{:.15f}')}")
            print(f"    (1) f_i = int chiL(+)/A     {_fmt(r['f'], '{:.12f}')}  max-min={max(r['f']) - min(r['f']):.6e}")
            print(f"    (1) int chiL(-)/A           {_fmt(r['f_minus'], '{:.12f}')}")
            print(f"    [A] |int(chiL+chiU)(+)-A|/A {_fmt(r['partition_rel'], '{:.3e}')}  band {PARTITION_BAND:.0e}")
            for q in QUAD_DEGREES:
                print(f"    (2) R+   q={q}               {_fmt(r['Rp'][q], '{:.12e}')}  spread={_spread(r['Rp'][q]):.6e}")
                print(f"    (2) R-   q={q}               {_fmt(r['Rm'][q], '{:.12e}')}  spread={_spread(r['Rm'][q]):.6e}")
                print(f"    (2) Ravg q={q}               {_fmt(r['Ravg'][q], '{:.12e}')}  spread={_spread(r['Ravg'][q]):.6e}")
            print(f"    (2) expr int g/A q=8        {_fmt(r['expr'], '{:.12e}')}  spread={_spread(r['expr']):.6e}")
            print(f"    [B] E_lin target 1+x_bar/rho0 {_fmt(r['L_target'], '{:.12e}')}")
            print(f"    [B] E_lin R+ q=2            {_fmt(r['Lp'], '{:.12e}')}  spread={_spread(r['Lp']):.6e}  rel err {_fmt(r['Lp_rel'], '{:.2e}')}")
            print(f"    [B] E_lin R- q=2            {_fmt(r['Lm'], '{:.12e}')}  spread={_spread(r['Lm']):.6e}  rel err {_fmt(r['Lm_rel'], '{:.2e}')}")
            print(f"    [B] E_lin Ravg q=2          {_fmt(r['Lavg'], '{:.12e}')}  spread={_spread(r['Lavg']):.6e}")
            print(f"    timings: mesh={r['mesh_s']:.2f} s measure={r['measure_s']:.2f} s")

        print("\n[PORT-18] === f_i side by side ===")
        for label in order:
            f = rows[label]["f"]
            print(f"  {label:<28s} {_fmt(f, '{:.12f}')}  max-min={max(f) - min(f):.6e}")

        print(
            "\n[PORT-18] === four-sheet spreads (max-min)/|mean| by q, beside "
            "ANS-4 Z class spreads [%] (records) ==="
        )
        print(f"  {'rung':<28s} {'q':>2s} {'R+':>13s} {'R-':>13s} {'Ravg':>13s} {'expr(q=8)':>13s}  ANS-4 Z classes %")
        for label in order:
            r = rows[label]
            for q in QUAD_DEGREES:
                ans = ANS4_CLASS_SPREADS_PCT.get(label, None)
                print(
                    f"  {label:<28s} {q:>2d} {_spread(r['Rp'][q]):13.6e} "
                    f"{_spread(r['Rm'][q]):13.6e} {_spread(r['Ravg'][q]):13.6e} "
                    f"{_spread(r['expr']):13.6e}  "
                    + (("/".join(f"{v:.4f}" for v in ans)) if ans else "(no record)")
                )

        # ---- discriminator (derived; printed, asserted nowhere)
        print("\n[PORT-18] === the discriminator (derived from the table; printed, asserted nowhere) ===")
        premise_dev = max(max(abs(p - 1.0) for p in rows[l]["premise"]) for l in order)
        f_diff = {l: max(rows[l]["f"]) - min(rows[l]["f"]) for l in order}
        qmax = QUAD_DEGREES[-1]
        sp = {
            l: {
                key: {q: _spread(rows[l][key][q]) for q in QUAD_DEGREES}
                for key in ("Rp", "Rm", "Ravg")
            }
            for l in order
        }
        print(f"  (0) max |premise - 1| over all sheets and rungs = {premise_dev:.3e}")
        for l in order:
            print(
                f"  {l:<28s} f max-min={f_diff[l]:.3e}  "
                + "  ".join(
                    f"q={q}: R+/Ravg spread ratio="
                    + (
                        f"{sp[l]['Rp'][q] / sp[l]['Ravg'][q]:.3e}"
                        if sp[l]["Ravg"][q] > 0
                        else "inf"
                    )
                    for q in QUAD_DEGREES
                )
            )
        if premise_dev > PREMISE_BAND:
            print(
                "  => PREMISE FALSE: the sheet normal is not +-z, so h_hat is not "
                "parallel to n_hat and the '+'-restricted read-back is not a normal "
                "component. Printed; stop."
            )
        else:
            f_equal_all = all(f_diff[l] <= 1.0e-9 for l in order)
            a_ok = f_equal_all and all(
                sp[l]["Rp"][q] <= 1.1 * sp[l]["Ravg"][q] + 1.0e-12
                for l in order
                for q in QUAD_DEGREES
            )
            b_ok = (not f_equal_all) and all(
                sp[l]["Rp"][qmax] > sp[l]["Ravg"][qmax] for l in order if f_diff[l] > 1.0e-9
            )
            behaved = [l for l in order if l in BEHAVED]
            broke = [l for l in order if l in BROKE]
            if b_ok and behaved and broke:
                tracks = min(sp[l]["Rp"][qmax] for l in broke) > max(
                    sp[l]["Rp"][qmax] for l in behaved
                )
                print(f"  (b) R+ spread on broken rungs > on behaved rungs at q={qmax}: {tracks}")
                b_ok = b_ok and tracks
            c_ok = all(
                sp[l][key][QUAD_DEGREES[0]] > 2.0 * sp[l][key][qmax]
                for l in order
                for key in ("Rp", "Ravg")
            )
            print(f"  predicates: (a)={a_ok}  (b)={b_ok}  (c)={c_ok}  [f equal at every rung: {f_equal_all}]")
            if a_ok:
                print(
                    "  => (a) f_i equal across the four sheets at every rung and the R+ "
                    "spread <~ the Ravg spread: the read-back's side choice is excluded; "
                    "the solve (source term v('+').z included) is the remaining suspect."
                )
            if b_ok:
                print(
                    "  => (b) f_i differs across sheets and the R+ spread exceeds the Ravg "
                    "spread and tracks the rungs that broke: the '+' restriction of a "
                    "normal component is a port-model defect in lumped.py "
                    "(sheet_terminal_current, lumped_port_linear_term)."
                )
            if c_ok:
                print("  => (c) spreads fall with q at fixed f_i: quadrature, curable.")
            if not (a_ok or b_ok or c_ok):
                print(
                    "  => none of (a)/(b)/(c) holds cleanly; the per-rung readings above "
                    "are the answer and the review owns the ruling."
                )

        print(f"[PORT-18] probe wall time={elapsed:.2f} s", flush=True)
        payload = {
            "partition": {l: rows[l]["partition_rel"] for l in order},
            "lin": {l: rows[l]["Lp_rel"] + rows[l]["Lm_rel"] for l in order},
            "neg": {l: _spread(rows[l]["Lp"]) for l in order},
        }

    payload = comm.bcast(payload, root=0)
    for l, rel in payload["partition"].items():
        assert max(rel) <= PARTITION_BAND, (
            f"(A) rung {l}: partition identity off by {max(rel):.3e} relative — "
            "the DG0 indicators are broken, so f_i measures nothing"
        )
    for l, rel in payload["lin"].items():
        assert max(rel) <= EXACTNESS_BAND, (
            f"(B) rung {l}: E_lin read-back off 1 + x_bar/rho0 by {max(rel):.3e} "
            "— N1curl degree 1 represents it exactly, so the read-back is broken"
        )
    for l, s in payload["neg"].items():
        assert s >= NEG_CONTROL_BAR, (
            f"negative control, rung {l}: E_lin four-sheet spread {s:.6e} < "
            f"{NEG_CONTROL_BAR} — the spread metric cannot see a non-C4 field"
        )
    _print("[PORT-18] (A), (B) and the negative control green.", comm)


if __name__ == "__main__":
    main()
