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

Step 0c (2026-09-16, §9 item 1; the knob the `xl` window's command contracts
on): ``FEM_EM_WF7_PORTS`` chooses how many ring ports are driven in turn —
unset or ``1`` drives the first ring ordinal only and is byte-identical to
step 0, an integer ``k`` drives the first ``k`` ordinals in ``_ring_ports()``
order, ``all`` drives every ring port.  Each drive's fields are dropped before
the next solve (32 columns of F-human fields is the memory trap) and each
drive prints its own ``PRICE`` line with the cumulative wall clock, so a
killed window still prices how far it got.  The first drive always factorises
(``reuse_factorization`` at its default off); later drives reuse the held
MUMPS factor (`PORT-19` step 3 — the operator is drive-independent here) and
the probe prints the ``solve_kind`` it actually took.  With ``k >= 2`` the
``k x k`` `S` is assembled from the columns and its ``_reciprocity_ratio``,
``sigma_max`` and class spreads are printed beside `PORT-13`'s imported bands.

Asserted (heavy tier, ``-n 8``, `WF-7` step 0c): with the knob unset the
printed ``S_driven`` must reproduce step 0's record digits (the flag-off
control), and with ``FEM_EM_WF7_PORTS=2`` the 2x2's reciprocity ratio must sit
inside the imported ``RECIPROCITY_BAND`` while the second drive's ``S_driven``
differs from the first's (the loop reached a different port).  Everything
else, ``sigma_max`` included, is printed and never asserted.
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
from tests.validation.test_port_birdcage_ring_column import (  # noqa: E402
    COLUMN_PASSIVITY_CEILING,
    OPPOSITE_SPREAD_BAND,
    RECIPROCITY_BAND,
    _reciprocity_ratio,
    _solve_one_drive,
)
from tests.validation.test_port_gap_voltage_impedance import (  # noqa: E402
    SIGMA_WIRE_S_PER_M,
)

FREQUENCY_HZ = 64.0e6
DEGREE = int(os.environ.get("FEM_EM_WF7_DEGREE", "1"))
if DEGREE not in (1, 2):
    raise ValueError(f"FEM_EM_WF7_DEGREE must be 1 or 2, got {DEGREE}")
PREDICTED_SUMMED_RSS_GIB = {1: (11.0, 33.0), 2: (150.0, 350.0)}[DEGREE]
PREDICTED_SOLVE_MIN = {1: (3.0, 8.0), 2: (10.0, 60.0)}[DEGREE]

PORTS_ENV = os.environ.get("FEM_EM_WF7_PORTS", "1").strip().lower()
if PORTS_ENV != "all":
    try:
        _n_ports = int(PORTS_ENV)
    except ValueError as exc:  # pragma: no cover - argument validation
        raise ValueError(
            f"FEM_EM_WF7_PORTS must be a positive integer or 'all', got {PORTS_ENV!r}"
        ) from exc
    if _n_ports < 1:
        raise ValueError(f"FEM_EM_WF7_PORTS must be >= 1, got {_n_ports}")
else:
    _n_ports = None

# The flag-off control record (`WF-7` step 0c anchor (a)): the printed digits of
# `S_driven` from the step-0 window, restated here as the record it is —
# 0.407423+0.344417j, degree 1, -n 8, unset knob, F-human longitudinal,
# `20260913T190102Z_WF-7-step0.log:10423` at commit fa55a0f (`OPS-41`:
# version-tagged, compared only where it was measured; printed elsewhere).
S_DRIVEN_STEP0_RECORD = "0.407423+0.344417j"
S_DRIVEN_RECORD_RANKS = 8


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

    # ---- phase 3: the drives (assemble + factorise + solve) -------------
    drives = (
        list(ring_ports) if _n_ports is None else list(ring_ports)[:_n_ports]
    )
    driven_ids = [f"P{i}" for i in drives]
    say(f"phase 3 solve: FEM_EM_WF7_PORTS={PORTS_ENV} -> {len(driven_ids)} drive(s) "
        f"{driven_ids[0]}..{driven_ids[-1]}, the rest of the {len(ring_ports)} ring "
        f"sheets terminated at {TERMINATED_PORT_IMPEDANCE_OHM} Ohm")

    columns: dict[str, dict] = {}
    unknowns = None
    lo_t, hi_t = PREDICTED_SOLVE_MIN
    lo_m, hi_m = PREDICTED_SUMMED_RSS_GIB
    for k, driven in enumerate(driven_ids):
        # First drive factorises (default off, step 0's route bit for bit);
        # later drives back-substitute the held factor (`PORT-19` step 3).
        col = _solve_one_drive(ctx, driven, reuse_factorization=(k > 0))
        fields = col.pop("fields")  # 32 columns of F-human fields is the trap
        if unknowns is None:
            V = fields.e_complex.function_space
            unknowns = V.dofmap.index_map.size_global * V.dofmap.index_map_bs
        del fields
        columns[driven] = col
        solve_s = col["solve_time"]
        say(f"phase 3 drive {k + 1}/{len(driven_ids)} {driven}: solve {solve_s:.2f} s "
            f"= {solve_s / 60:.2f} min ({col.get('solve_kind', 'solve')})  "
            f"({'INSIDE' if lo_t <= solve_s / 60 <= hi_t else 'OUTSIDE'} predicted "
            f"{lo_t}-{hi_t} min per drive)")
        say(f"phase 3 drive {k + 1} accounting (printed, not asserted): "
            f"supplied {col['supplied']:.6e} W  phantom {col['phantom']:.6e}  "
            f"conductor {col['conductor']:.6e}  sheets {col['sheet_total']:.6e}  "
            f"residual {col['residual']:.3e}  "
            f"S_driven {col['s_column'][driven]:.6f}")
        local = (
            float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024.0 / 2**30
        )
        per_rank = comm.allgather(local)
        if comm.rank == 0:
            s = sum(per_rank)
            print(
                f"[WF-7 step0] PRICE drive {k + 1}/{len(driven_ids)} {driven}: "
                f"degree {DEGREE}  cells {n_cells}  unknowns {unknowns}  "
                f"ranks {comm.size}  mesh build {build_s:.2f} s  "
                f"solve {solve_s:.2f} s ({col.get('solve_kind', 'solve')})  "
                f"cumulative window {time.perf_counter() - t_window:.2f} s\n"
                f"[WF-7 step0] PRICE drive {k + 1}: ru_maxrss per rank GiB "
                f"{[round(v, 3) for v in per_rank]}  summed {s:.3f} GiB  "
                f"max {max(per_rank):.3f} GiB  "
                f"({'INSIDE' if lo_m <= s <= hi_m else 'OUTSIDE'} predicted "
                f"{lo_m}-{hi_m} GiB)",
                flush=True,
            )

    # ---- phase 4: the k x k S, its identities (printed) -----------------
    first = driven_ids[0]
    s_first_str = f"{columns[first]['s_column'][first]:.6f}"
    say(f"phase 4 flag-off control: S_driven({first}) printed {s_first_str} vs the "
        f"step-0 record {S_DRIVEN_STEP0_RECORD} "
        f"(asserted only at -n {S_DRIVEN_RECORD_RANKS} with one drive; here "
        f"{'ASSERTED' if (comm.size == S_DRIVEN_RECORD_RANKS and len(driven_ids) == 1 and DEGREE == 1) else 'printed only'})")

    ratio = None
    if len(driven_ids) >= 2:
        s_k = np.array(
            [[columns[pj]["s_column"][pi] for pj in driven_ids] for pi in driven_ids],
            dtype=complex,
        )
        ratio = _reciprocity_ratio(s_k)
        sigma_max = float(np.linalg.svd(s_k, compute_uv=False)[0])
        s_diag = np.array([columns[p]["s_column"][p] for p in driven_ids])
        spread = float(
            (np.abs(s_diag).max() - np.abs(s_diag).min()) / np.abs(s_diag).mean()
        )
        col_norms = {
            p: float(sum(abs(s) ** 2 for s in columns[p]["s_column"].values()))
            for p in driven_ids
        }
        say(f"phase 4 identities on the {len(driven_ids)}x{len(driven_ids)} S: "
            f"reciprocity {ratio:.3e} (band {RECIPROCITY_BAND:.0e}, imported; "
            f"{'INSIDE' if ratio <= RECIPROCITY_BAND else 'MISS'})")
        say(f"phase 4 negative control (predicted, printed, never asserted): "
            f"sigma_max {sigma_max:.6f} vs COLUMN_PASSIVITY_CEILING "
            f"{COLUMN_PASSIVITY_CEILING:.0f} "
            f"({'<= ceiling' if sigma_max <= COLUMN_PASSIVITY_CEILING else 'ABOVE ceiling'})")
        say(f"phase 4 class spreads (printed): |S_jj| spread {spread:.4e} "
            f"(OPPOSITE_SPREAD_BAND {OPPOSITE_SPREAD_BAND}); full-column "
            f"sum_i |S_ij|^2 " + "  ".join(f"{p} {col_norms[p]:.6f}" for p in driven_ids))

    # ---- the asserted anchors -------------------------------------------
    assert abs(rel) < CELL_COUNT_BAND, (
        f"F-human longitudinal build meshed {n_cells} cells, relative {rel:.3e} to "
        f"the GEO-25 branch-B record {F_HUMAN_BRANCH_B_CELL_RECORD} (band "
        f"{CELL_COUNT_BAND}) — record the reading, do not move the band"
    )
    say("ANCHOR PASS: cell record inside the imported band")

    # (a) the flag-off control: with the knob unset this probe is step 0, and
    #     the printed digits of `S_driven` are step 0's.  Only where the record
    #     was measured (-n 8, one drive, degree 1); printed everywhere else.
    if comm.size == S_DRIVEN_RECORD_RANKS and len(driven_ids) == 1 and DEGREE == 1:
        assert s_first_str == S_DRIVEN_STEP0_RECORD, (
            f"flag-off control: S_driven({first}) printed {s_first_str}, the step-0 "
            f"record is {S_DRIVEN_STEP0_RECORD} "
            f"(20260913T190102Z_WF-7-step0.log:10423, -n 8, degree 1) — the "
            f"F-human probe has drifted; report the digits, do not move the record"
        )
        say("ANCHOR PASS: flag-off control reproduces the step-0 S_driven digits")

    # (b) the knob does something: reciprocity on the k x k, and the second
    #     drive is a different port.
    if len(driven_ids) >= 2:
        assert ratio <= RECIPROCITY_BAND, (
            f"the {len(driven_ids)}x{len(driven_ids)} S off the drive loop has "
            f"reciprocity ratio {ratio:.3e} > the imported {RECIPROCITY_BAND:.0e} "
            f"band — a drive-indexing defect in the loop, not a band to move"
        )
        second = driven_ids[1]
        delta = abs(columns[second]["s_column"][second] - columns[first]["s_column"][first])
        assert delta > 1e-6, (
            f"drive 2 ({second}) returned S_driven within {delta:.3e} of drive 1 "
            f"({first}) — the loop did not reach a different port"
        )
        say(f"ANCHOR PASS: reciprocity {ratio:.3e} <= {RECIPROCITY_BAND:.0e} and "
            f"drive 2 differs from drive 1 by {delta:.3e} > 1e-6")
    return 0


if __name__ == "__main__":
    sys.exit(main())
