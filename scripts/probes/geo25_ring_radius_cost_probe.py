"""`GEO-25` — the F-human cost probe: `birdcage_port_domain` vs `ring_radius`.

MEASUREMENT ONLY. This script asserts nothing, is imported by nothing, and
changes nothing in `src/` or `tests/`. It builds **one** rung of the
`ring_radius` ladder per OS process — the rung is selected by the environment
variable ``FEM_EM_PROBE_RING_RADIUS`` (metres), never by a pytest ``-k``
expression — and prints cell count, mesh wall time, the scale-free `GEO-18` /
`GEO-19` CAD identities, and peak RSS.

One process per rung is not a style choice: `GEO-23` step 1 measured that a
failed gmsh build poisons every later build in the same process
(``IndexError ... size 0`` in 0.0 s), so a one-process ladder reads FAIL on
every rung after the first real failure. gmsh is serial (rank 0 builds), so
this runs at ``-n 1`` with no ``mpiexec``.

Geometry: `mesh:9` / `EX-35` exactly at ``ring_radius = 0.07`` — 16 legs, the
high-pass **ring-gap** layout on both end rings, `emit_port_sheets=True`,
`leg_gap_length=None` — so the 0.07 m rung is a wiring negative control that
must reproduce that example's 265 621 cells at 0.000e+00 relative.

Scaling rule for a rung at radius ``r`` (factor ``s = r / 0.07``):

* scaled by ``s`` — `ring_radius`, `coil_length`, `leg_spacing`,
  `phantom_radius`, `phantom_height`, `air_padding`, `ring_gap_length`,
  `port_box_size`, and the global `resolution` (the "phantom/air sizing" the
  `GEO-25` §7 row says scales with the radius);
* **held fixed** — `leg_width`, `ring_minor_radius` (the conductor's own
  cross-section) and `conductor_resolution`, which stays at `mesh:9`'s
  ``0.4 * ring_minor_radius = 1.6e-3`` m. That is *finer* than the 4.8e-3 m
  `GEO-21` control sizing, so the "never coarser than the 4.8 mm floor" rule
  is satisfied with room to spare; coarsening it is what the row forbids, and
  it is also the only value that can reproduce the 265 621-cell control.

Run one rung::

    FEM_EM_PROBE_RING_RADIUS=0.07 python3 scripts/probes/geo25_ring_radius_cost_probe.py
"""

from __future__ import annotations

import os
import resource
import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402

from tests.mesh.test_coil_phantom_conforming import (  # noqa: E402
    _tag_volume,
    _total_volume,
)
from tests.mesh.test_birdcage_port_terminals import CONDUCTOR_IFACE  # noqa: E402
from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER  # noqa: E402
from tests.mesh.test_birdcage_ring_gaps import (  # noqa: E402
    _port_boundary_partition,
)

# `GEO-25` step 2 (2026-09-05) moved `_params` and its two anchors verbatim into
# the gate module, which is now the single source of the F-human parameter set;
# this probe imports them back so the two can never drift. Additive only — the
# probe's printed digits are unchanged.
from tests.validation.test_birdcage_f_human_rung import (  # noqa: E402
    BASE_RING_RADIUS,
    LEG_COUNT,
    _params,
)

# The number the 0.07 m control must hit (`mesh:9` / `EX-35`).
MESH9_CELL_RECORD = 265621


def main() -> None:
    comm = MPI.COMM_WORLD
    raw = os.environ.get("FEM_EM_PROBE_RING_RADIUS")
    if raw is None:
        raise SystemExit(
            "set FEM_EM_PROBE_RING_RADIUS to the rung's ring_radius in metres"
        )
    radius = float(raw)
    scale_sizing = os.environ.get("FEM_EM_PROBE_SCALE_MESH_SIZING", "1") != "0"
    kwargs = _params(radius, scale_sizing=scale_sizing)
    s = radius / BASE_RING_RADIUS

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            f"[GEO-25 probe] scale_mesh_sizing={scale_sizing}  "
            f"rung ring_radius={radius:.6f} m  scale s={s:.9f}  "
            f"leg_count={LEG_COUNT}  ring-gap (high-pass), sheets on, legs uncut",
            flush=True,
        )
        for key in sorted(kwargs):
            print(f"[GEO-25 param] {key} = {kwargs[key]!r}", flush=True)

    started = time.perf_counter()
    mesh, cells, _facets, diag = MeshGenerator.birdcage_port_domain(
        comm=comm, return_diagnostics=True, **kwargs
    )
    build_elapsed = time.perf_counter() - started

    n_cells = mesh.topology.index_map(3).size_global
    mesh_wall = float(diag["mesh_wall_time_s"])

    # --- the scale-free CAD identities (`GEO-18` / `GEO-19`), measured ------
    ring_ports = list(range(LEG_COUNT + 1, LEG_COUNT + 2 * LEG_COUNT + 1))
    port_cell_tags = {i: (PORT_LOWER + i,) for i in range(1, LEG_COUNT + 1)}
    port_cell_tags.update({i: (PORT_LOWER + i, PORT_UPPER + i) for i in ring_ports})
    all_tags = sorted({1, 2, 3, *[t for v in port_cell_tags.values() for t in v]})
    volumes = {t: _tag_volume(mesh, cells, t, comm) for t in all_tags}
    v_total = _total_volume(mesh, comm)
    partition = sum(volumes.values()) / v_total

    _counts, areas = _port_boundary_partition(mesh, cells, comm, port_cell_tags)
    layout = diag["ring_port_layout"]
    terminal_analytic = float(layout["ring_terminal_area_m2"])
    ratios = np.array(
        [areas[CONDUCTOR_IFACE + i] / terminal_analytic for i in ring_ports]
    )
    cad_ratio = volumes[1] / diag["cad_mass_by_group"]["conductor"]

    self_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    child_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    total_rss = comm.allreduce(self_rss + child_rss, op=MPI.SUM)

    if comm.rank == 0:
        rel = n_cells / MESH9_CELL_RECORD - 1.0
        print(
            f"\n[GEO-25 result] ring_radius = {radius:.6f} m"
            f"\n  cells                 {n_cells}"
            f"\n  mesh_wall_time_s      {mesh_wall:.3f}"
            f"\n  build_rung_s          {build_elapsed:.3f}"
            f"\n  volume partition      {partition:.12f}"
            f"\n  total volume m3       {v_total:.9e}",
            flush=True,
        )
        print(
            f"  terminal ratio        min {ratios.min():.9f}  "
            f"max {ratios.max():.9f}  n_ports {len(ratios)}  "
            f"in [0.95, 1.0]: {bool(ratios.min() >= 0.95 and ratios.max() <= 1.0)}"
            f"\n  meshed/CAD conductor  {cad_ratio:.6f}"
            f"\n  ru_maxrss summed      {total_rss} kB "
            f"({total_rss / 1.048576e6:.3f} GiB)"
            f"\n  vs mesh:9 record      {n_cells} vs {MESH9_CELL_RECORD}  "
            f"relative {rel:.3e}",
            flush=True,
        )
        for k, i in enumerate(ring_ports):
            print(
                f"  [terminal] P{i:<3d} ratio {ratios[k]:.9f}",
                flush=True,
            )
        print("=" * 78, flush=True)


if __name__ == "__main__":
    main()
