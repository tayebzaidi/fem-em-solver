"""Example (`EX-46`): the first field on the 32-ring-port birdcage, in ParaView.

`PORT-13` step 1 (2026-09-04) put the first solve on the 16-leg / 32-ring-port
high-pass birdcage: the `GEO-26` step 2 rung with **longitudinal** ring
sheets — the sheet orientation the lumped-sheet port model can actually
drive (`ports:6`–`ports:9` are all the 4-leg *leg*-gap fixture at 116 085
cells; no example before this one solves a 16-leg coil or drives a ring-gap
port). This example is the geometry angle on that new capability: it
re-implements the gate's own module-scoped fixture body (a pytest fixture is
not callable outside pytest) to run the one drive step 1 gates — port `P17`
at 1 V, the other 31 ring ports terminated at ``z0 = 50 Ohm`` — then writes
``|E|`` (DG0) over the whole domain, with the cell tags and the 32 sheet
facet tags, into one combined XDMF.

**It asserts, it does not merely render** (the `ANS-1` rule). Every record,
band and helper is imported from
``tests/validation/test_port_birdcage_ring_column.py`` as it stands at
`052bd61` — nothing here is restated:

* cells = ``RING_LONGITUDINAL_SCALED_CELL_RECORD`` (270 728) at
  ``CELL_COUNT_BAND``;
* the three-way power-accounting residual <= ``POWER_BALANCE_BAND`` (1e-2);
* the two ports diametrically opposite the driven one (found from the
  *measured* sheet azimuths, `_driven_and_opposite`) agree to
  ``OPPOSITE_SPREAD_BAND`` (5%);
* the supplied power ``1/2 Re(V_src I*)`` reproduces step 1's own recorded
  **5.078728668e-03 W** at rtol 1e-3 (`20260904T050538Z_PORT-13.log:10751`;
  the `EX-43` precedent — the rank count here differs from the gate's
  ``-n 8``, so 1e-6 is not claimed, only 1e-3).

**Negative control (free, step 1's own).** Drop the conductor's
``1/2 int sigma|E|^2`` term from the accounting and the residual must land
*outside* the power band — step 1 measured 4.14x the band at ``-n 8``; that
is the printed ceiling this run does not claim to exceed.

**Scope: one solve, one column, one price.** No 32x32, no C16 gate, no
tuning, no resonance and no absolute-accuracy claim — `PORT-13` step 1's own
scope, unchanged. The SAR/power terms and the terminal currents are read
straight off ``mean_sar(...)["dissipated_power_w"]`` and
``sheet_terminal_current`` exactly as the gate module does; this script
re-derives no accounting term.

Needs the complex DolfinX build. Run it through the example runner, which
sources complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:10 -n 4 -t 600

Outputs ``paraview_output/ports_10_birdcage_ring_column_combined.xdmf`` — the
mesh, ``CellTags`` (phantom, conductor, the 32 ring-port halves), the 32
sheet facet tags (as ``mesh_tags``, on the same file) and ``E_magnitude``
(DG0, V/m) — so ParaView can threshold the driven gap (`P17`), its top-ring
partner (`P33`) and the phantom in one view.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import fem, io

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gate's constants, helpers and construction can be imported rather than
# restated (the `ANS-1` rule).
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.core import (  # noqa: E402
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    cell_tags_to_function,
    consolidate_xdmf_grids,
)
from fem_em_solver.ports.lumped import LumpedSheetPortSpec  # noqa: E402

from tests.validation.test_port_birdcage_ring_column import (  # noqa: E402
    CELL_COUNT_BAND,
    CONDUCTOR_CELL_TAG,
    FREQUENCY_HZ,
    OPPOSITE_SPREAD_BAND,
    PHANTOM_CELL_TAG,
    POWER_BALANCE_BAND,
    RING_LONGITUDINAL_SCALED_CELL_RECORD,
    SALINE_EPSILON_R,
    SALINE_SIGMA,
    SCALED_LEG_COUNT,
    SHEET_IFACE,
    SIGMA_WIRE_S_PER_M,
    SOLVE_PRICE_STOP_RULE_S,
    TERMINATED_PORT_IMPEDANCE_OHM,
    _driven_and_opposite,
    _measure_ring,
    _ring_gap_frame,
    _solve_one_drive,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "ports_10_birdcage_ring_column"

# `PORT-13` step 1's own recorded supplied power, read off its printed GATE
# (i) line at `-n 8` (`20260904T050538Z_PORT-13.log:10751`). Not an importable
# constant in the gate module (it is a fixture-computed reading, printed, not
# a module-level record) so it is carried here as a literal, checked at rtol
# 1e-3 rather than restated as if it were a closed form — the `EX-42`
# precedent for a printed-not-named record.
STEP1_SUPPLIED_POWER_RECORD_W = 5.078728668e-03
SUPPLIED_POWER_RTOL = 1.0e-3


def _build_ring_column(comm):
    """`PORT-13` step 1's module-scoped fixture body, re-implemented here.

    A pytest fixture (``ring_four_columns`` in the gate module) is not
    callable outside pytest, so the setup it performs is reproduced verbatim
    up to (and not including) step 2's four-drive sweep: this example needs
    only the one drive step 1 itself gates. ``_solve_one_drive`` — the
    per-drive solve-and-account routine both step 1 and step 2 share — is
    imported and called unmodified; nothing about the accounting is
    re-derived here.
    """
    m = _measure_ring(SCALED_LEG_COUNT, orientation="longitudinal")
    msh = m["mesh"]
    cell_tags = m["cells"]
    tags_f = m["sheet_tags"]
    ring_ports = list(m["ring_ports"])

    tdim = msh.topology.dim
    # Hoisted on every rank before any facet-restricted form (known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    chord = float(m["diag"]["ring_port_layout"]["ring_port_gap_chord_m"])
    sheets = []
    for i in ring_ports:
        area = float(m["sheet_area"][i])
        phi_hat, centre = _ring_gap_frame(i, SCALED_LEG_COUNT)
        sheets.append(
            {
                "ordinal": i,
                "tag": SHEET_IFACE + i,
                "area": area,
                "h": chord,
                "w": area / chord,
                "drive": tuple(float(c) for c in phi_hat),
                "azimuth_deg": float(m["azimuth_deg"][i]),
                "z": float(centre[2]),
            }
        )

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

    driven, opposite = _driven_and_opposite(m["azimuth_deg"], ring_ports)
    specs = [
        LumpedSheetPortSpec(
            port_id=f"P{s['ordinal']}",
            facet_tag=int(s["tag"]),
            port_impedance_ohm=TERMINATED_PORT_IMPEDANCE_OHM,
            gap_height_m=s["h"],
            sheet_width_m=s["w"],
            drive_direction=s["drive"],
            drive_voltage_v=1.0 + 0.0j,
            interior=True,
        )
        for s in sheets
    ]

    omega = 2.0 * np.pi * float(FREQUENCY_HZ)
    ctx = {
        "comm": comm,
        "msh": msh,
        "tags_f": tags_f,
        "cell_tags": cell_tags,
        "omega": omega,
        "specs": specs,
        "solver": TimeHarmonicSolver(problem, degree=1),
    }

    result = _solve_one_drive(ctx, f"P{driven}")

    return {
        "m": m,
        "msh": msh,
        "cell_tags": cell_tags,
        "sheet_tags": tags_f,
        "sheets": sheets,
        "driven": driven,
        "opposite": opposite,
        "azimuth_deg": {i: float(m["azimuth_deg"][i]) for i in ring_ports},
        "result": result,
    }


def _magnitude_field(e_complex, name):
    """DG0 ``|E|`` [V/m] over the whole domain — the honest, cell-wise
    resolution of a degree-1 curl element (`EX-26`'s convention), never
    interpolated onto a smoother CG space than the discretisation supports.
    """
    msh = e_complex.function_space.mesh
    dg0 = fem.functionspace(msh, ("DG", 0))
    expr_ufl = ufl.sqrt(ufl.inner(e_complex, e_complex))
    # OPS-18: on the 0.11 image, `interpolation_points` is a property, not a
    # method.
    expr = fem.Expression(expr_ufl, dg0.element.interpolation_points)
    field = fem.Function(dg0, name=name)
    field.interpolate(expr)
    # `|E|` is real by construction (inner(E, conj(E))); XDMF carries no
    # complex array (`EX-14`/`EX-17`), so the real part is what is written.
    out = fem.Function(dg0, name=name)
    out.x.array[:] = np.real(field.x.array)
    out.x.scatter_forward()
    return out


def _write_combined(msh, cell_tags, sheet_tags, fields, comm):
    """Mesh + ``CellTags`` + the DG0 fields + the 32 sheet facet tags, in
    **one** XDMF file. ``write_xdmf_with_tags`` writes cell-based data only
    (no facet ``MeshTags`` parameter), so this inlines its pattern —
    ``cell_tags_to_function``/``consolidate_xdmf_grids`` imported, not
    reimplemented — and adds ``xdmf.write_meshtags`` for the sheets before
    the file closes, rather than opening a second file the way `EX-44`/`EX-45`
    did for the same rung's mesh-only examples.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{BASENAME}_combined.xdmf"
    msh.topology.create_connectivity(msh.topology.dim - 1, msh.topology.dim)
    with io.XDMFFile(comm, path, "w") as xdmf:
        xdmf.write_mesh(msh)
        xdmf.write_function(cell_tags_to_function(msh, cell_tags))
        for func in fields.values():
            xdmf.write_function(func)
        xdmf.write_meshtags(sheet_tags, msh.geometry)
    consolidate_xdmf_grids(path, comm=comm)
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path if comm.rank == 0 else None


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    from dolfinx import default_scalar_type

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ports:` group)."
        )

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            "EX-46 — the first field on the 32-ring-port birdcage in "
            "ParaView: |E| on the longitudinal ring sheets and the phantom, "
            "P17 driven",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            "\n[fixture] `PORT-13` step 1: 16-leg / 32-ring-port longitudinal "
            f"rung, phantom loaded, {FREQUENCY_HZ:.3e} Hz, degree 1, P17 at "
            f"1 V, 31 ports at Z_p = {TERMINATED_PORT_IMPEDANCE_OHM} Ohm\n"
            "[gates]   cells = RING_LONGITUDINAL_SCALED_CELL_RECORD at "
            "CELL_COUNT_BAND; power accounting <= POWER_BALANCE_BAND; "
            "opposite pair <= OPPOSITE_SPREAD_BAND; supplied power vs step "
            "1's own record at rtol 1e-3\n"
            "[control] conductor term dropped from the power accounting "
            "must miss the band (step 1's own, free)",
            flush=True,
        )

    ctx = _build_ring_column(comm)
    m = ctx["m"]
    result = ctx["result"]
    driven, opposite = ctx["driven"], ctx["opposite"]
    az = ctx["azimuth_deg"]

    cell_ratio = m["n_cells"] / RING_LONGITUDINAL_SCALED_CELL_RECORD
    if comm.rank == 0:
        print(
            f"\n[mesh] {m['n_cells']} cells (record "
            f"{RING_LONGITUDINAL_SCALED_CELL_RECORD}, ratio {cell_ratio:.6f}), "
            f"mesh {m['diag']['mesh_wall_time_s']:.2f} s, rung "
            f"{m['elapsed']:.2f} s\n"
            f"[solve] one drive P{driven}: {result['solve_time']:.2f} s wall "
            f"at -n {comm.size} (stop rule {SOLVE_PRICE_STOP_RULE_S:.0f} s)",
            flush=True,
        )

    assert abs(cell_ratio - 1.0) < CELL_COUNT_BAND, (
        f"the rung meshed {m['n_cells']} cells against "
        f"RING_LONGITUDINAL_SCALED_CELL_RECORD "
        f"{RING_LONGITUDINAL_SCALED_CELL_RECORD} (ratio {cell_ratio:.6f}) — "
        "this is not the fixture `PORT-13` step 1 gated"
    )

    # ---- the 32-vector V = V_src - I*Z_p, printed --------------------------
    if comm.rank == 0:
        print(
            "\n[32-vector] V = V_src - I*Z_p (generator convention), "
            "printed:",
            flush=True,
        )
        for s in ctx["sheets"]:
            pid = f"P{s['ordinal']}"
            v, i_a = result["voltages"][pid], result["currents"][pid]
            print(
                f"    {pid:>4s} ring {'bottom' if s['z'] < 0 else 'top   '} "
                f"azimuth {s['azimuth_deg']:8.3f} deg  V = {v:+.9e} V  "
                f"|V| = {abs(v):.9e}  I = {i_a:+.9e} A"
                + ("   <-- DRIVEN" if s["ordinal"] == driven else "")
                + ("   <-- OPPOSITE" if s["ordinal"] in opposite else ""),
                flush=True,
            )

    # ---- gate (i): three-way power accounting, plus the free control ------
    supplied = result["supplied"]
    residual = result["residual"]
    blind = result["blind"]
    if comm.rank == 0:
        print(
            f"\n[gate i] power accounting (band {POWER_BALANCE_BAND:.0e}, "
            "imported):\n"
            f"    supplied 1/2 Re(V_src I*) = {supplied:.9e} W\n"
            f"    phantom  1/2 int sigma|E|^2 = {result['phantom']:.9e} W\n"
            f"    conductor 1/2 int sigma|E|^2 = {result['conductor']:.9e} W\n"
            f"    32 sheets 1/2 |I|^2 Re Z_p = {result['sheet_total']:.9e} W\n"
            f"    residual = {residual:.6e}  "
            f"{'INSIDE' if residual <= POWER_BALANCE_BAND else 'MISS'}\n"
            f"    negative control, conductor term dropped: {blind:.6e} "
            f"({blind / POWER_BALANCE_BAND:.2f}x the band; step 1's own "
            "-n 8 measurement was 4.14x)",
            flush=True,
        )

    assert supplied > 0.0, (
        f"the driven sheet supplies {supplied:.9e} W — a passive load "
        "cannot absorb negative real power"
    )
    assert residual <= POWER_BALANCE_BAND, (
        f"power accounting misses by {residual:.6e} of the supplied "
        f"{supplied:.9e} W; band {POWER_BALANCE_BAND:.0e} (§7 `EX-46` "
        "negative result: example/test divergence, known-issues entry, "
        "stop; never re-record from the example side)"
    )
    assert blind > POWER_BALANCE_BAND, (
        f"dropping the conductor's 1/2 int sigma|E|^2 still closes to "
        f"{blind:.6e}, inside the {POWER_BALANCE_BAND:.0e} band — the "
        "negative control failed to separate"
    )

    # ---- gate: the supplied power reproduces step 1's own record ----------
    supplied_relative = abs(supplied - STEP1_SUPPLIED_POWER_RECORD_W) / abs(
        STEP1_SUPPLIED_POWER_RECORD_W
    )
    if comm.rank == 0:
        print(
            f"\n[gate] supplied power {supplied:.9e} W vs step 1's own "
            f"record {STEP1_SUPPLIED_POWER_RECORD_W:.9e} W at -n 8 "
            f"(relative {supplied_relative:.3e}, rtol "
            f"{SUPPLIED_POWER_RTOL:.0e} — rank count differs from the "
            "gate's -n 8, so 1e-6 is not claimed)",
            flush=True,
        )
    assert supplied_relative <= SUPPLIED_POWER_RTOL, (
        f"the supplied power {supplied:.9e} W misses step 1's own recorded "
        f"{STEP1_SUPPLIED_POWER_RECORD_W:.9e} W by {supplied_relative:.3e}, "
        f"outside rtol {SUPPLIED_POWER_RTOL:.0e} (§7 `EX-46` negative "
        "result: example/test divergence, known-issues entry, stop; never "
        "re-record from the example side)"
    )

    # ---- gate (ii): the opposite pair ---------------------------------------
    a_id, b_id = (f"P{i}" for i in opposite)
    v_a = result["voltages"][a_id]
    v_b = result["voltages"][b_id]
    spread = abs(v_a - v_b) / abs(v_a)
    if comm.rank == 0:
        print(
            f"\n[gate ii] the two ring ports diametrically opposite "
            f"P{driven} (band {OPPOSITE_SPREAD_BAND * 100:.0f}%):\n"
            f"    {a_id} ({az[opposite[0]]:.3f} deg)  V = {v_a:+.9e} V  "
            f"|V| = {abs(v_a):.9e}\n"
            f"    {b_id} ({az[opposite[1]]:.3f} deg)  V = {v_b:+.9e} V  "
            f"|V| = {abs(v_b):.9e}\n"
            f"    |V_a - V_b|/|V_a| = {spread * 100:.4f}%  "
            f"{'INSIDE' if spread <= OPPOSITE_SPREAD_BAND else 'MISS'}",
            flush=True,
        )
    assert spread <= OPPOSITE_SPREAD_BAND, (
        f"the two ring ports diametrically opposite the driven one read "
        f"V = {v_a:+.9e} and {v_b:+.9e} V, a spread of {spread * 100:.4f}% "
        f"against the {OPPOSITE_SPREAD_BAND * 100:.0f}% band (§7 `EX-46` "
        "negative result: example/test divergence, known-issues entry, "
        "stop; never re-record from the example side)"
    )

    # ---- the deliverable: |E| in ParaView ------------------------------------
    e_mag = _magnitude_field(result["fields"].e_complex, "E_magnitude")
    written = _write_combined(
        ctx["msh"], ctx["cell_tags"], ctx["sheet_tags"], {"E_magnitude": e_mag}, comm
    )

    if comm.rank == 0:
        print(f"\n[paraview] wrote {written}")
        print(
            "\n[paraview] threshold `CellTags` (1 conductor, 2 air, 3 "
            "phantom, 101-116 the sixteen uncut leg boxes, 117-148/217-248 "
            "the inner/outer halves of the 32 ring-port boxes) or the "
            "`mesh_tags` facet array (227-258, the 32 reconstructed "
            f"longitudinal sheets) and colour by `E_magnitude` (DG0, V/m). "
            f"Driven port P{driven}'s sheet tag is "
            f"{SHEET_IFACE + driven}; its top-ring z-mirror is "
            "the ring port at the same measured azimuth on the other ring "
            "(see the printed 32-vector above).",
            flush=True,
        )
        print(
            f"\nAll gates hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
