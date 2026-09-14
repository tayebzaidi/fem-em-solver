"""`WF-7` step 0 — the F-human cost probe: one single-drive degree-1
lumped-sheet solve on the `GEO-25` F-human rung at 64 MHz.

MEASUREMENT ONLY apart from one assert: the cell count against `GEO-25`'s
branch-B record (504 642) at the imported `CELL_COUNT_BAND`. Everything else
(cells, unknowns, mesh-build time, solve time, ru_maxrss per rank / summed /
max) is printed, each phase flushed as it completes so a killed window still
records how far it got.

Fixture: `tests/validation/test_birdcage_f_human_rung._params(0.15,
scale_sizing=False)` — branch B, fixed absolute sizing — imported, never
copied, with ``ring_sheet_orientation="longitudinal"`` added: the fixture's own
default is the transverse sheet (normal = phi_hat), on which a phi_hat drive is
not tangential; the §9 item names the 32-ring-port longitudinal layout. Whether
the orientation moves the cell count off the transverse record is part of the
reading — the cell assert is therefore evaluated *after* the solve, so one
window yields both.

Drive: `test_port_birdcage_ring_column._solve_one_drive` (imported) — the
lowest ring ordinal driven at 1 V, all 32 ring sheets terminated at 50 Ohm,
degree 1, PEC outer boundary, same materials as `PORT-13`.

Run (complex build, heavy, -n 8)::

    FEM_EM_REQUIRE_COMPLEX=1 mpiexec -n 8 python3 scripts/probes/wf7_step0_f_human_cost.py

Step 0b (2026-09-13, the XXL window): ``FEM_EM_WF7_DEGREE=2`` runs the same
single drive at degree 2 — the human-scale order-sensitivity reading. Unset
or ``1`` is byte-identical to step 0. The prediction brackets printed beside
the readings are per degree: degree 2 is bracketed from `ANS-4` step 2d's
3.79 M-unknown / 290.2 GiB / ≈ 1 400 s-per-drive point scaled to ≈ 3.2 M
unknowns (memory ∝ N^1.35, time ∝ N^1.8), widened both ways.
"""

from __future__ import annotations

import os
import resource
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
from mpi4py import MPI  # noqa: E402

from fem_em_solver.core import (  # noqa: E402
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator, _interface_facet_tags  # noqa: E402
from fem_em_solver.ports.lumped import LumpedSheetPortSpec  # noqa: E402

from tests.mesh.test_birdcage_port_sheet_prerequisite import CELL_COUNT_BAND  # noqa: E402
from tests.mesh.test_birdcage_port_sheets import (  # noqa: E402
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
)
from tests.mesh.test_birdcage_port_terminals import _interface_area_or_zero  # noqa: E402
from tests.mesh.test_birdcage_ring_gaps_scaleup import _ring_gap_frame  # noqa: E402
from tests.validation.test_birdcage_f_human_rung import (  # noqa: E402
    F_HUMAN_BRANCH_B_CELL_RECORD,
    F_HUMAN_RING_RADIUS,
    LEG_COUNT,
    _params,
    _ring_ports,
)
from tests.validation.test_lossy_sphere_fullwave import (  # noqa: E402
    SALINE_EPSILON_R,
    SALINE_SIGMA,
)
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    TERMINATED_PORT_IMPEDANCE_OHM,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)
from tests.validation.test_port_birdcage_ring_column import _solve_one_drive  # noqa: E402
from tests.validation.test_port_gap_voltage_impedance import (  # noqa: E402
    SIGMA_WIRE_S_PER_M,
)

FREQUENCY_HZ = 64.0e6
DEGREE = int(os.environ.get("FEM_EM_WF7_DEGREE", "1"))
if DEGREE not in (1, 2):
    raise ValueError(f"FEM_EM_WF7_DEGREE must be 1 or 2, got {DEGREE}")
PREDICTED_SUMMED_RSS_GIB = {1: (11.0, 33.0), 2: (150.0, 350.0)}[DEGREE]
PREDICTED_SOLVE_MIN = {1: (3.0, 8.0), 2: (10.0, 60.0)}[DEGREE]


def _rss(comm, phase: str, t_window: float) -> None:
    """``ru_maxrss`` on every rank (OPS-43), gathered; printed on rank 0."""
    local = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024.0 / 2**30
    per_rank = comm.allgather(local)
    if comm.rank == 0:
        print(
            f"[WF-7 step0] {phase}: t={time.perf_counter() - t_window:.1f} s  "
            f"ru_maxrss per rank GiB {[round(v, 3) for v in per_rank]}  "
            f"summed {sum(per_rank):.3f} GiB  max {max(per_rank):.3f} GiB",
            flush=True,
        )


def main() -> int:
    comm = MPI.COMM_WORLD
    t_window = time.perf_counter()

    def say(msg: str) -> None:
        if comm.rank == 0:
            print(f"[WF-7 step0] {msg}", flush=True)

    say(f"start: -n {comm.size}, f = {FREQUENCY_HZ:.3e} Hz, degree {DEGREE}, "
        f"ring_radius {F_HUMAN_RING_RADIUS} m, branch B (fixed sizing), longitudinal")
    _rss(comm, "phase 0 (imports)", t_window)

    # ---- phase 1: mesh --------------------------------------------------
    kwargs = _params(F_HUMAN_RING_RADIUS, scale_sizing=False)
    kwargs["ring_sheet_orientation"] = "longitudinal"
    t0 = time.perf_counter()
    msh, cell_tags, _facets, diag = MeshGenerator.birdcage_port_domain(
        comm=comm, return_diagnostics=True, **kwargs
    )
    build_s = time.perf_counter() - t0
    n_cells = msh.topology.index_map(3).size_global
    rel = n_cells / F_HUMAN_BRANCH_B_CELL_RECORD - 1.0
    say(f"phase 1 mesh: cells {n_cells} vs record {F_HUMAN_BRANCH_B_CELL_RECORD} "
        f"relative {rel:.3e} (band {CELL_COUNT_BAND}; "
        f"{'INSIDE' if abs(rel) < CELL_COUNT_BAND else 'OUTSIDE'})  "
        f"mesh_wall_time_s {float(diag['mesh_wall_time_s']):.2f}  build_s {build_s:.2f}")
    _rss(comm, "phase 1 (mesh built)", t_window)

    # ---- phase 2: sheets + solver context -------------------------------
    t0 = time.perf_counter()
    ring_ports = _ring_ports()
    port_cell_tags = {i: (PORT_LOWER + i, PORT_UPPER + i) for i in ring_ports}
    tags_f = _interface_facet_tags(
        msh, cell_tags, {SHEET_IFACE + i: port_cell_tags[i] for i in ring_ports}
    )
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()
    chord = float(diag["ring_port_layout"]["ring_port_gap_chord_m"])
    areas = {i: _interface_area_or_zero(msh, tags_f, SHEET_IFACE + i, comm)
             for i in ring_ports}
    specs = []
    for i in ring_ports:
        # phi_hat depends on the ordinal and leg count only (the centre uses the
        # base radius and is not read here).
        phi_hat, _centre = _ring_gap_frame(i, LEG_COUNT)
        specs.append(
            LumpedSheetPortSpec(
                port_id=f"P{i}",
                facet_tag=int(SHEET_IFACE + i),
                port_impedance_ohm=TERMINATED_PORT_IMPEDANCE_OHM,
                gap_height_m=chord,
                sheet_width_m=areas[i] / chord,
                drive_direction=tuple(float(c) for c in phi_hat),
                drive_voltage_v=1.0 + 0.0j,
                interior=True,
            )
        )
    a = np.array([areas[i] for i in ring_ports])
    say(f"phase 2 sheets: {len(specs)} ring sheets, area min {a.min():.6e} "
        f"max {a.max():.6e} m^2, chord {chord:.6e} m, "
        f"zero-area sheets {int((a <= 0).sum())}  ({time.perf_counter() - t0:.2f} s)")

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            CONDUCTOR_CELL_TAG: HomogeneousMaterial(
                sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0
            ),
            PHANTOM_CELL_TAG: HomogeneousMaterial(
                sigma=SALINE_SIGMA, epsilon_r=SALINE_EPSILON_R, mu_r=1.0
            ),
        },
        boundary_condition="pec_zero_tangential_a",
    )
    ctx = {
        "comm": comm,
        "msh": msh,
        "tags_f": tags_f,
        "cell_tags": cell_tags,
        "omega": 2.0 * np.pi * FREQUENCY_HZ,
        "specs": specs,
        "solver": TimeHarmonicSolver(problem, degree=DEGREE),
    }
    _rss(comm, "phase 2 (sheets + solver built)", t_window)

    # ---- phase 3: one drive (assemble + factorise + solve) --------------
    driven = f"P{min(ring_ports)}"
    say(f"phase 3 solve: driving {driven}, 31 terminated at "
        f"{TERMINATED_PORT_IMPEDANCE_OHM} Ohm")
    col = _solve_one_drive(ctx, driven)
    fields = col.pop("fields")
    V = fields.e_complex.function_space
    unknowns = V.dofmap.index_map.size_global * V.dofmap.index_map_bs
    solve_s = col["solve_time"]
    lo_t, hi_t = PREDICTED_SOLVE_MIN
    say(f"phase 3 done: unknowns {unknowns}  solve (assemble+factorise+solve) "
        f"{solve_s:.2f} s = {solve_s / 60:.2f} min  "
        f"({'INSIDE' if lo_t <= solve_s / 60 <= hi_t else 'OUTSIDE'} predicted "
        f"{lo_t}-{hi_t} min)")
    say(f"phase 3 accounting (printed, not asserted): supplied {col['supplied']:.6e} W  "
        f"phantom {col['phantom']:.6e}  conductor {col['conductor']:.6e}  "
        f"sheets {col['sheet_total']:.6e}  residual {col['residual']:.3e}  "
        f"S_driven {col['s_column'][driven]:.6f}")
    local = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024.0 / 2**30
    per_rank = comm.allgather(local)
    if comm.rank == 0:
        s = sum(per_rank)
        lo, hi = PREDICTED_SUMMED_RSS_GIB
        print(
            f"[WF-7 step0] PRICE: degree {DEGREE}  cells {n_cells}  unknowns {unknowns}  ranks {comm.size}  "
            f"mesh build {build_s:.2f} s  solve {solve_s:.2f} s  "
            f"window {time.perf_counter() - t_window:.2f} s\n"
            f"[WF-7 step0] PRICE: ru_maxrss per rank GiB {[round(v, 3) for v in per_rank]}  "
            f"summed {s:.3f} GiB  max {max(per_rank):.3f} GiB  "
            f"({'INSIDE' if lo <= s <= hi else 'OUTSIDE'} predicted {lo}-{hi} GiB)",
            flush=True,
        )

    # ---- the one asserted anchor: the cell record -----------------------
    assert abs(rel) < CELL_COUNT_BAND, (
        f"F-human longitudinal build meshed {n_cells} cells, relative {rel:.3e} to "
        f"the GEO-25 branch-B record {F_HUMAN_BRANCH_B_CELL_RECORD} (band "
        f"{CELL_COUNT_BAND}) — record the reading, do not move the band"
    )
    say("ANCHOR PASS: cell record inside the imported band")
    return 0


if __name__ == "__main__":
    sys.exit(main())
