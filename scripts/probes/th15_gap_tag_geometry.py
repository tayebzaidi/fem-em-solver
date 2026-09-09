"""`TH-15` step 2h — is the gap cell tag a half-domain?  Geometry only, no solve.

Measurement-only probe (§9 item 2 of the 2026-09-09 03:00 review).  It builds the
two meshes the PEC-hole port module builds — `_hole_build` (`as_hole=True`) and
`_build` (the boxed solid) — and reads, per gap cell tag, per port:

  (1) the meshed volume ``int dx(tag)``, comm-reduced (`_tag_volume`, the very
      function `run_gap_voltage_port_case` divides the drive current by);
  (2) the tag's bounding extents in x/y/z from **owned** cell midpoints,
      reduced `MPI.MIN` / `MPI.MAX`;
  (3) the owned-cell count, reduced `MPI.SUM` (ghosts masked on
      ``index_map(dim).size_local`` — `OPS-39`'s fix);
  (4) both ratios against the two CAD candidates the plan names — the gap
      **box** ``(2(r_w + GAP_OVERHANG))^2 x 2 half_y`` (10.4 mm square x
      13.955 mm long, `_gap_half_extents`) and the **wire footprint x chord**
      ``pi r_w^2 . 2a sin(theta/2)`` — printed side by side to six digits;
  (5) ``A_gap = V_tag / g`` against the box cross-section.

Nothing physical is asserted and no solve is run: the two checks below are a
geometric closed form and a symmetry identity of the fixture's own C2.

  ANCHOR: the meshed gap-tag volume matches one of the two CAD candidates
  inside 5%.  The candidates differ by ~1.6x, so 5% cannot straddle them and
  the check decides the half-domain question by itself.  If it matches
  *neither*, that is the item's negative result: record the number, stop, do
  not guess a third candidate.

  NEGATIVE CONTROL: the two ports' gap tags are geometrically identical by
  construction, so their volumes must agree to <= 1e-3 relative.  A probe that
  cannot reproduce one tag from the other is measuring its own bug.

Every fixture parameter is imported, never restated (`ANS-1`).  Run through the
logging harness only:

    scripts/testing/run_and_log.sh TH-15-step2h "docker compose exec -T \
      fem-em-solver bash -lc 'cd /workspace && PYTHONPATH=/workspace/src:/workspace \
      timeout -k 30 300 mpiexec -n 2 python3 scripts/probes/th15_gap_tag_geometry.py'"

Asserts nothing physical, imported by nothing, closes nothing.
"""

from __future__ import annotations

import sys
import time

import numpy as np
from mpi4py import MPI

from dolfinx.mesh import compute_midpoints

from fem_em_solver.ports.gap_voltage import _tag_volume

from tests.validation.test_port_package_sparameters import (
    GAP_ANGLE,
    GAP_ARC_RESOLUTION,
    GAP_OVERHANG,
    GAP_TAGS,
    MAJOR_RADIUS,
    MINOR_RADIUS,
    _gap_half_extents,
)
from tests.mesh.test_two_torus_conductor_hole import _hole_build
from tests.validation.test_port_lumped_two_torus import _build

VOLUME_TOLERANCE = 0.05  # the item's 5% anchor band
C2_BAND = 1.0e-3  # the item's negative control


def _owned_cells_with_tag(msh, cell_tags, tag):
    """Owned cell indices carrying ``tag``; ghosts masked (`OPS-39`)."""
    tdim = msh.topology.dim
    n_owned = msh.topology.index_map(tdim).size_local
    idx = np.asarray(cell_tags.indices)
    val = np.asarray(cell_tags.values)
    sel = (val == int(tag)) & (idx < n_owned)
    return np.asarray(idx[sel], dtype=np.int32)


def _tag_extents(msh, cell_tags, tag, comm):
    """Bounding extents of the tag from owned cell midpoints, reduced."""
    cells = _owned_cells_with_tag(msh, cell_tags, tag)
    if cells.size:
        mids = compute_midpoints(msh, msh.topology.dim, cells)
        local_lo = mids.min(axis=0)
        local_hi = mids.max(axis=0)
    else:
        local_lo = np.full(3, np.inf)
        local_hi = np.full(3, -np.inf)
    lo = np.zeros(3)
    hi = np.zeros(3)
    for k in range(3):
        lo[k] = comm.allreduce(float(local_lo[k]), op=MPI.MIN)
        hi[k] = comm.allreduce(float(local_hi[k]), op=MPI.MAX)
    n_cells = comm.allreduce(int(cells.size), op=MPI.SUM)
    return lo, hi, n_cells


def main() -> int:
    comm = MPI.COMM_WORLD
    rank0 = comm.rank == 0

    half_xz, half_y = _gap_half_extents()
    g = 2.0 * half_y
    box_cross_section = (2.0 * half_xz) ** 2
    cad_box = box_cross_section * g
    chord = 2.0 * MAJOR_RADIUS * np.sin(0.5 * GAP_ANGLE)
    wire_footprint = np.pi * MINOR_RADIUS**2
    cad_wire_chord = wire_footprint * chord

    if rank0:
        print(
            "\n[TH-15 step 2h] geometry-only gap-tag probe, "
            f"{comm.size} rank(s), GAP_ARC_RESOLUTION = {GAP_ARC_RESOLUTION:.3e} m",
            flush=True,
        )
        print(
            f"    CAD box:        half_xz = {half_xz:.9e} m, "
            f"g = 2*half_y = {g:.9e} m, cross-section = "
            f"{box_cross_section:.9e} m^2 = {1.0e6 * box_cross_section:.6f} mm^2",
            flush=True,
        )
        print(
            f"    CAD box volume            = {1.0e9 * cad_box:.6f} mm^3",
            flush=True,
        )
        print(
            f"    CAD half-box volume       = {1.0e9 * 0.5 * cad_box:.6f} mm^3 "
            "(printed for reference, NOT a candidate)",
            flush=True,
        )
        print(
            f"    CAD wire footprint x chord = {1.0e9 * cad_wire_chord:.6f} mm^3 "
            f"(pi r_w^2 = {1.0e6 * wire_footprint:.6f} mm^2, "
            f"chord = {1.0e3 * chord:.6f} mm)",
            flush=True,
        )

    failures: list[str] = []
    for label, builder in (("HOLE", _hole_build), ("SOLID", _build)):
        t0 = time.perf_counter()
        msh, cell_tags, _facet_tags, t_mesh = builder(comm)
        tdim = msh.topology.dim
        msh.topology.create_connectivity(tdim - 1, tdim)
        msh.topology.create_entity_permutations()
        n_total = comm.allreduce(
            msh.topology.index_map(tdim).size_local, op=MPI.SUM
        )
        if rank0:
            print(
                f"\n[TH-15 step 2h] {label} mesh: {n_total} cells, "
                f"{t_mesh:.2f} s build",
                flush=True,
            )

        volumes = []
        for k, tag in enumerate(GAP_TAGS):
            vol = _tag_volume(msh, cell_tags, tag, comm)
            lo, hi, n_tag = _tag_extents(msh, cell_tags, tag, comm)
            volumes.append(vol)
            r_box = vol / cad_box
            r_wire = vol / cad_wire_chord
            a_gap = vol / g
            if rank0:
                print(
                    f"    {label:<5s} P{k + 1} tag {tag}: "
                    f"V_tag = {vol:.12e} m^3 = {1.0e9 * vol:.6f} mm^3, "
                    f"owned cells = {n_tag}",
                    flush=True,
                )
                print(
                    f"    {label:<5s} P{k + 1} tag {tag}: "
                    f"V_tag/box = {r_box:.6f}   "
                    f"V_tag/(pi r_w^2 . chord) = {r_wire:.6f}",
                    flush=True,
                )
                print(
                    f"    {label:<5s} P{k + 1} tag {tag}: "
                    f"A_gap = V_tag/g = {a_gap:.12e} m^2 "
                    f"= {1.0e6 * a_gap:.6f} mm^2, "
                    f"A_gap/box cross-section = {a_gap / box_cross_section:.6f}",
                    flush=True,
                )
                print(
                    f"    {label:<5s} P{k + 1} tag {tag}: midpoint extents "
                    f"x [{lo[0]:.9e}, {hi[0]:.9e}] span {hi[0] - lo[0]:.9e} | "
                    f"y [{lo[1]:.9e}, {hi[1]:.9e}] span {hi[1] - lo[1]:.9e} | "
                    f"z [{lo[2]:.9e}, {hi[2]:.9e}] span {hi[2] - lo[2]:.9e}",
                    flush=True,
                )

            # ANCHOR — one of the two CAD candidates, inside 5%.
            miss_box = abs(r_box - 1.0)
            miss_wire = abs(r_wire - 1.0)
            if min(miss_box, miss_wire) > VOLUME_TOLERANCE:
                failures.append(
                    f"{label} P{k + 1} tag {tag}: V_tag = {1.0e9 * vol:.6f} mm^3 "
                    f"matches NEITHER CAD candidate inside {VOLUME_TOLERANCE:.0%} "
                    f"(V/box = {r_box:.6f}, V/(pi r_w^2 . chord) = {r_wire:.6f})"
                )
            elif rank0:
                which = "box" if miss_box <= miss_wire else "wire footprint x chord"
                print(
                    f"    {label:<5s} P{k + 1} ANCHOR: matches the {which} "
                    f"candidate, miss {min(miss_box, miss_wire):.6f} "
                    f"<= {VOLUME_TOLERANCE}",
                    flush=True,
                )

        # NEGATIVE CONTROL — the fixture's own C2.
        c2 = abs(volumes[0] - volumes[1]) / abs(volumes[0])
        if rank0:
            print(
                f"    {label:<5s} C2 control: |V_P1 - V_P2|/|V_P1| = {c2:.6e} "
                f"against {C2_BAND:.0e}",
                flush=True,
            )
        if not (c2 <= C2_BAND):
            failures.append(
                f"{label}: the two ports' gap tags differ by {c2:.6e} > {C2_BAND:.0e} "
                "— the probe is wrong, not the mesh"
            )
        if rank0:
            print(
                f"    {label:<5s} elapsed {time.perf_counter() - t0:.2f} s",
                flush=True,
            )

    if rank0:
        if failures:
            print("\n[TH-15 step 2h] CHECKS FAILED:", flush=True)
            for line in failures:
                print(f"    {line}", flush=True)
        else:
            print("\n[TH-15 step 2h] both checks green.", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
