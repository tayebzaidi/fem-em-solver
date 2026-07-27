#!/usr/bin/env python3
"""Helmholtz coil: on-axis B_z compared against the analytic solution.

This is the corrected counterpart to ``03_helmholtz_coil.py``, which evaluates
fields with ``B.eval(points, np.arange(n))`` -- that asks dolfinx to evaluate each
point inside an *arbitrary* cell rather than the cell containing it, and produces
meaningless numbers. Here we use ``post.evaluation.evaluate_vector_field_parallel``,
which locates points properly via a bounding-box tree + collision search.

What is compared
----------------
Two coaxial tori of major radius R, minor radius a, separated by R (the Helmholtz
condition), carrying unit current density in the azimuthal direction. The total
current per loop is therefore::

    I = |J| * (wire cross-section) = 1.0 * pi * a**2

The reference is the filamentary on-axis Helmholtz field::

    B_z(z) = sum over both loops of  mu_0 * I * R**2 / (2 * (R**2 + (z-z_i)**2)**1.5)

Accuracy floors (these do NOT shrink with mesh refinement)
----------------------------------------------------------
1. Finite wire thickness. The analytic formula assumes a filament; the model uses a
   torus with a/R = 0.25 by default. This biases the centre field by O((a/R)^2),
   on the order of several percent.
2. Tight domain box. ``two_torus_domain`` builds a box only ~1.75*R in half-width
   and applies magnetic insulation on it, whereas the analytic solution is free
   space. This suppresses the field near the boundary.

So do not expect agreement below a few percent no matter how fine the mesh. The
useful signal is that the error *stops changing* as h shrinks -- at that point the
discretization error is below the systematic floors, which is what refinement can
actually buy you. Use --minor-radius to trade wire thinness against cost.

Cost
----
``resolution`` is applied as a single global gmsh size, so cell count scales with
the whole box volume, not just the wire. Roughly:

    h=0.005 -> ~10k cells,  a few seconds
    h=0.003 -> ~48k cells,  under a minute
    h=0.0025 -> ~82k cells, a couple of minutes

Keep h <= a/2 or the wire is not resolved at all.
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import ufl
from dolfinx import fem
from mpi4py import MPI

from fem_em_solver.core.solvers import MagnetostaticProblem, MagnetostaticSolver
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_combined_paraview_output,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import AnalyticalSolutions
from fem_em_solver.utils.constants import MU_0


def build_current_density(major_radius: float, minor_radius: float, separation: float):
    """Unit-magnitude azimuthal current density confined to the two tori."""
    z1 = -separation / 2.0
    z2 = separation / 2.0

    def current_density(x):
        rho = ufl.sqrt(x[0] ** 2 + x[1] ** 2)
        in_wire_1 = ((rho - major_radius) ** 2 + (x[2] - z1) ** 2) <= minor_radius**2
        in_wire_2 = ((rho - major_radius) ** 2 + (x[2] - z2) ** 2) <= minor_radius**2
        in_wire = ufl.Or(in_wire_1, in_wire_2)

        rho_safe = ufl.max_value(rho, 1e-12)
        return ufl.as_vector(
            [
                ufl.conditional(in_wire, -x[1] / rho_safe, 0.0),
                ufl.conditional(in_wire, x[0] / rho_safe, 0.0),
                0.0,
            ]
        )

    return current_density


def run_case(
    resolution,
    major_radius,
    minor_radius,
    separation,
    n_points,
    comm,
    air_padding=None,
    far_resolution=None,
    output_dir=None,
    basename="helmholtz",
):
    """Solve at one wire resolution; return diagnostics dict on rank 0."""
    t0 = time.time()
    mesh, cell_tags, facet_tags = MeshGenerator.two_torus_domain(
        separation=separation,
        major_radius=major_radius,
        minor_radius=minor_radius,
        resolution=resolution,
        comm=comm,
        air_padding=air_padding,
        wire_resolution=resolution if far_resolution is not None else None,
        far_resolution=far_resolution,
    )
    t_mesh = time.time() - t0
    n_cells = mesh.topology.index_map(mesh.topology.dim).size_global

    t0 = time.time()
    problem = MagnetostaticProblem(
        mesh=mesh, cell_tags=cell_tags, facet_tags=facet_tags, mu=MU_0
    )
    solver = MagnetostaticSolver(problem, degree=1)
    a_field = solver.solve(
        current_density=build_current_density(major_radius, minor_radius, separation)
    )
    b_field = solver.compute_b_field()
    t_solve = time.time() - t0

    written_files = {}
    if output_dir is not None:
        # XDMF point data requires a Lagrange space; A lives in N1curl and B in DG,
        # so interpolate both to CG1 vectors for export.
        v_lag = fem.functionspace(mesh, ("Lagrange", 1, (3,)))

        a_lag = fem.Function(v_lag, name="A")
        a_lag.interpolate(a_field)

        b_lag = fem.Function(v_lag, name="B")
        b_lag.interpolate(b_field)

        written_files = write_combined_paraview_output(
            output_dir,
            basename,
            mesh,
            cell_tags,
            {"A": (a_field, a_lag), "B": (b_field, b_lag)},
            comm=comm,
        )

    # Sample the on-axis line across the full coil span.
    z_eval = np.linspace(-0.6 * separation, 0.6 * separation, n_points)
    points = np.zeros((n_points, 3), dtype=np.float64)
    points[:, 2] = z_eval

    values, valid = evaluate_vector_field_parallel(b_field, points, comm=comm)
    bz_num = values[:, 2]

    # Total current implied by unit |J| over the wire cross-section.
    current = 1.0 * np.pi * minor_radius**2
    bz_ana = AnalyticalSolutions.helmholtz_coil_field_on_axis(
        z_eval, current, major_radius, separation
    )

    if comm.rank != 0:
        return None

    if not valid.all():
        n_bad = int((~valid).sum())
        print(f"  WARNING: {n_bad}/{n_points} sample points fell outside the mesh")

    ok = valid & (np.abs(bz_ana) > 0.0)
    rel = np.abs(bz_num[ok] - bz_ana[ok]) / np.abs(bz_ana[ok])

    # Uniformity over the central region, |z| <= 0.1*R. Fall back to the innermost
    # few samples when the grid is too coarse to place several points in that window.
    central = ok & (np.abs(z_eval) <= 0.1 * major_radius)
    if central.sum() < 3:
        central = np.zeros_like(ok)
        central[np.argsort(np.abs(z_eval))[: min(5, int(ok.sum()))]] = True
        central &= ok
    cv = (
        float(np.std(bz_num[central]) / abs(np.mean(bz_num[central])))
        if central.sum() > 1
        else float("nan")
    )

    centre = int(np.argmin(np.abs(z_eval)))
    return {
        "written_files": written_files,
        "resolution": resolution,
        "n_cells": n_cells,
        "t_mesh": t_mesh,
        "t_solve": t_solve,
        "current": current,
        "z": z_eval,
        "bz_num": bz_num,
        "bz_ana": bz_ana,
        "valid": valid,
        "centre_num": float(bz_num[centre]),
        "centre_ana": float(bz_ana[centre]),
        "centre_rel": float(abs(bz_num[centre] - bz_ana[centre]) / abs(bz_ana[centre])),
        "max_rel": float(rel.max()),
        "mean_rel": float(rel.mean()),
        "cv": cv,
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Compare FEM Helmholtz on-axis B_z against the analytic solution."
    )
    p.add_argument(
        "--resolutions",
        type=float,
        nargs="+",
        default=[0.005, 0.0035, 0.0025],
        help="Global mesh sizes to sweep, coarse to fine (m). Keep <= minor-radius/2.",
    )
    p.add_argument("--major-radius", type=float, default=0.02, help="Loop radius R (m)")
    p.add_argument(
        "--minor-radius",
        type=float,
        default=0.005,
        help="Wire radius a (m). Smaller is closer to the filamentary analytic model "
        "but needs a finer mesh.",
    )
    p.add_argument(
        "--separation",
        type=float,
        default=None,
        help="Loop separation (m). Defaults to the Helmholtz condition, separation = R.",
    )
    p.add_argument("--points", type=int, default=21, help="On-axis sample points")
    p.add_argument(
        "--air-padding",
        type=float,
        default=None,
        help="Clearance from coil envelope to outer box (m). Default reproduces the "
        "legacy 2*minor_radius box, which is far too tight for a free-space "
        "comparison. Use >= 2*major-radius.",
    )
    p.add_argument(
        "--far-resolution",
        type=float,
        default=None,
        help="Mesh size at the outer boundary (m). Setting this enables graded "
        "refinement, so --resolutions then controls the size at the wire only. "
        "Required to keep a large air box affordable.",
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Write ParaView output (XDMF/HDF5 + on-axis CSV) to this directory. "
        "Only the finest resolution in the sweep is exported.",
    )
    p.add_argument(
        "--basename",
        type=str,
        default="helmholtz",
        help="Base filename for ParaView output.",
    )
    args = p.parse_args()

    comm = MPI.COMM_WORLD
    separation = args.separation if args.separation is not None else args.major_radius
    rank0 = comm.rank == 0

    if rank0:
        print("=" * 72)
        print("Helmholtz coil - FEM vs analytic on-axis B_z")
        print("=" * 72)
        print(f"  major radius R : {args.major_radius:.4f} m")
        print(f"  minor radius a : {args.minor_radius:.4f} m   (a/R = "
              f"{args.minor_radius / args.major_radius:.3f})")
        print(f"  separation     : {separation:.4f} m")
        print(f"  MPI ranks      : {comm.size}")
        print()

    results = []
    ordered = sorted(args.resolutions, reverse=True)
    for res in ordered:
        if rank0:
            print(f"--- resolution h = {res:.4g} m "
                  f"(h/a = {res / args.minor_radius:.2f}) ---", flush=True)
        # Export only the finest case; coarse sweep levels would just overwrite it.
        export_dir = args.output_dir if res == ordered[-1] else None
        r = run_case(
            res,
            args.major_radius,
            args.minor_radius,
            separation,
            args.points,
            comm,
            air_padding=args.air_padding,
            far_resolution=args.far_resolution,
            output_dir=export_dir,
            basename=args.basename,
        )
        if rank0 and r is not None:
            results.append(r)
            print(f"  cells={r['n_cells']}  mesh={r['t_mesh']:.1f}s  "
                  f"solve={r['t_solve']:.1f}s", flush=True)
            print(f"  centre B_z: FEM={r['centre_num']:.6e} T  "
                  f"analytic={r['centre_ana']:.6e} T  "
                  f"rel err={r['centre_rel']:.2%}", flush=True)
            print(f"  on-axis rel err: mean={r['mean_rel']:.2%} "
                  f"max={r['max_rel']:.2%}   central CV={r['cv']:.3%}", flush=True)
            print(flush=True)

    if not rank0 or not results:
        return 0

    print("=" * 72)
    print("Convergence summary")
    print("=" * 72)
    print(f"{'h (m)':>9} {'cells':>9} {'centre rel err':>16} {'mean rel err':>14} {'solve s':>9}")
    for r in results:
        print(f"{r['resolution']:>9.4g} {r['n_cells']:>9d} "
              f"{r['centre_rel']:>15.2%} {r['mean_rel']:>13.2%} {r['t_solve']:>9.1f}")

    finest = results[-1]
    print()
    print(f"On-axis profile at h = {finest['resolution']:.4g} m")
    print(f"{'z (m)':>10} {'B_z FEM (T)':>15} {'B_z exact (T)':>15} {'rel err':>10}")
    for i in range(len(finest["z"])):
        if not finest["valid"][i]:
            continue
        z, bn, ba = finest["z"][i], finest["bz_num"][i], finest["bz_ana"][i]
        rel = abs(bn - ba) / abs(ba) if ba != 0 else float("nan")
        print(f"{z:>10.5f} {bn:>15.6e} {ba:>15.6e} {rel:>9.2%}")

    print()
    print("Interpretation: if 'centre rel err' stops improving as h shrinks, you have")
    print("hit the systematic floor from finite wire thickness (a/R) and the tight")
    print("domain box -- not a discretization limit. Reduce --minor-radius to close")
    print("the first gap; the second needs a larger --air-padding (use >= 2*R).")

    if args.output_dir:
        from pathlib import Path

        out = Path(args.output_dir)
        # On-axis FEM vs analytic, for overlaying on the field plot in ParaView.
        csv_path = out / f"{args.basename}_on_axis.csv"
        with open(csv_path, "w") as fh:
            fh.write("z_m,Bz_fem_T,Bz_analytic_T,rel_error\n")
            for i in range(len(finest["z"])):
                if not finest["valid"][i]:
                    continue
                z, bn, ba = finest["z"][i], finest["bz_num"][i], finest["bz_ana"][i]
                rel = abs(bn - ba) / abs(ba) if ba != 0 else float("nan")
                fh.write(f"{z:.8e},{bn:.8e},{ba:.8e},{rel:.8e}\n")

        # The CSV is written after write_combined_paraview_output() has already
        # re-owned the directory, so claim it too.
        adopt_host_ownership(out, comm=comm)

        print()
        print("=" * 72)
        print(f"ParaView output (resolution h = {finest['resolution']:.4g} m)")
        print("=" * 72)
        for name, path in sorted(finest["written_files"].items()):
            print(f"  {name:>10}: {path}")
        print(f"  {'on-axis':>10}: {csv_path}")
        print()
        print("  Open the *_combined.xdmf file in ParaView: it carries the mesh,")
        print("  cell tags (1/2 = wire tori, 3 = air), and A and B on a single grid,")
        print("  so a Threshold on the tags works together with the field data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
