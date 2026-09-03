"""Example (`EX-43`): the first **coil-driven SAR quantity** in ParaView — loaded birdcage, 10 MHz.

`EX-38`/`39`/`40` write `|B₁⁺|`; `mri:2` writes mass-averaged SAR, but on an
**imposed** uniform field, never a solved coil. `WF-6` step 3g/3h/3i gated the
first coil-driven SAR identities — quadrant powers of the primal N1curl
``σ|E|²`` read as **cell integrals**, symmetric under the birdcage's C4
rotation and its own mirror — but, like every other gate before this project's
port examples started, that construction lives in a test module. This example
is the output-quantity angle: it writes the phantom's local SAR map
``σ|E|²/(2ρ)`` for ParaView, and prints the same twelve C4 pairs and four
mirror pairs the gate asserts.

**What runs.** `PORT-9` leg (d)'s own ``build_four_port_sweep`` — the gapped,
sheeted, phantom-loaded four-leg birdcage on the default 116 085-cell mesh,
10 MHz — then the same four single-port driven solves step 3g/h/i use, plus
the CCW quadrature superposition. Every helper is imported from
``tests/validation/test_birdcage_sar_integral.py`` as it stands at `642bfc5`:
``_quadrant_weight`` (the smooth, ordering-free azimuthal partition ``w_j``),
``_quadrant_powers`` (the reduced cell integrals ``P_j^{(k)} = ½∫_tag3 σ w_j
|E|² dV``), the C4 rotation sense (imported from step 3's own pairing, never
re-derived), and the mirror identity's flank/opposite construction. Nothing
here re-implements the integral or the pairing; this script only adds the
XDMF write and the print.

**It asserts, and it does not re-implement.** Every band, tolerance and
record comes from the gate module, imported:

* the twelve C4 pairs reproduce ``STEP3G_INTEGRAL_PAIR_RECORDS`` at rtol
  ``CG1_RECORD_RTOL`` (1e-3) and sit ≤ the imported ``C4_COVARIANCE_BAND``
  (5%);
* the four mirror pairs reproduce ``STEP3I_MIRROR_RECORDS`` at the same rtol
  and the same band;
* the partition identity ``Σ_j P_j^{(k)} = P_phantom^{(k)}`` at rtol
  ``PARTITION_RTOL`` (1e-10) for all five drives (four single ports plus the
  quadrature superposition);
* the P1 drive's phantom total reproduces step 1's recorded
  ``STEP1_GATE_I_P1_PHANTOM_POWER_W`` = 5.637745667e-08 W at rtol 1e-3;
* the fixture — cell ratio 1.000000 against the recorded 116 085.

**Negative control.** The mis-paired 180°-quadrant control (pairing quadrant
``j`` under drive ``k`` with quadrant ``j+2`` under drive ``k+1``) reads
strictly larger than the C4 pairing at every ``k`` (3g/3h measured 89–159×).

**Scope: an example of a gated quantity, nothing more.** No band moves, no
new gate, no §2 change. The SAR *map* this script writes is a **viewing
quantity**: it is the pointwise ``σ|E|²/(2ρ)`` per cell (the construction
step 3's own pointwise rungs retired as a *gate* for the 25–41% miss that
motivated the cell-integral construction in the first place) — it carries no
assertion of its own and no absolute-accuracy claim. Only the twelve C4 pairs,
the four mirror pairs, the partition identity and the P1 total are gated, and
only as self-consistency identities on one fixture at 10 MHz at fixed ``h``.

Needs the complex DolfinX build. Run it through the example runner, which
sources complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:9

Outputs ``paraview_output/ports_09_birdcage_sar_quadrant_powers_combined.xdmf``
— the P1-drive and quadrature-drive SAR maps (DG0, W/kg, phantom cells only)
and the four quadrant weights ``w_j`` (DG0) so ParaView can threshold a
quadrant, all on one grid with ``CellTags``.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gates' constants, helpers and construction can be imported rather than
# restated.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)

from tests.mesh.test_birdcage_phantom_resolution import DEFAULT_CELL_COUNT  # noqa: E402
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE  # noqa: E402
from tests.validation.test_birdcage_b1_plus_map import (  # noqa: E402
    C4_COVARIANCE_BAND,
    CG1_RECORD_RTOL,
    PHANTOM_RHO_KG_PER_M3,
    _solve_driven,
)
from tests.validation.test_birdcage_b1_quadrature import (  # noqa: E402
    QUADRATURE_STEP_DEG,
    _port_index,
    quadrature_phase_weights,
)
from tests.validation.test_birdcage_sar_integral import (  # noqa: E402
    PARTITION_EPS_M,
    PARTITION_RTOL,
    QUADRATURE_DEGREE,
    STEP3G_INTEGRAL_PAIR_RECORDS,
    STEP3I_MIRROR_RECORDS,
    _quadrant_powers,
    _quadrant_weight,
)
from tests.validation.test_birdcage_sar_map import (  # noqa: E402
    STEP1_GATE_I_P1_PHANTOM_POWER_W,
    _superpose_complex,
)
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    build_four_port_sweep,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    PHANTOM_CELL_TAG,
    STEP2_CELL_COUNT,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "ports_09_birdcage_sar_quadrant_powers"

# The mesh this example must be standing on is step 3g/h/i's default one, to
# the cell — every record it reproduces was measured there.
CELL_RATIO_BAND = 1.0e-9

# rtol the twelve C4 pairs, the four mirror pairs and the P1 total are all
# checked against their gate-module records at.
RECORD_RTOL = CG1_RECORD_RTOL


def _reproduces(value, record, rtol):
    """``|value − record| ≤ rtol·|record|`` — ``pytest.approx``'s relative test."""
    return abs(value - record) <= rtol * abs(record)


def _sar_map_field(e_complex, sigma_field, rho, cell_tags, phantom_tag, name):
    """DG0 ``σ|E|²/(2ρ)`` [W/kg], phantom cells only — a **viewing** quantity.

    Built exactly the way ``mean_sar``/``point_sar`` (`MAT-4`) read the same
    integrand, just interpolated per cell instead of integrated: the pointwise
    construction step 3's own rungs retired as a *gate* (the 25–41% miss that
    motivated 3g's cell-integral construction). It carries no assertion here —
    only the C4/mirror/partition integrals below are gated. Cells outside the
    phantom are zeroed: ``rho`` is the phantom's density and would misprice a
    conductor or air cell.
    """
    msh = e_complex.function_space.mesh
    dg0 = fem.functionspace(msh, ("DG", 0))
    expr_ufl = sigma_field * ufl.inner(e_complex, e_complex) / (2.0 * rho)
    # OPS-18: on the 0.11 image, `interpolation_points` is a property, not a
    # method — calling it raises "'numpy.ndarray' object is not callable".
    expr = fem.Expression(expr_ufl, dg0.element.interpolation_points)
    field = fem.Function(dg0, name=name)
    field.interpolate(expr)

    num_local = msh.topology.index_map(msh.topology.dim).size_local
    keep = np.zeros(num_local, dtype=bool)
    phantom_local = cell_tags.indices[
        (cell_tags.values == phantom_tag) & (cell_tags.indices < num_local)
    ]
    keep[phantom_local] = True
    values = field.x.array
    for cell in np.nonzero(~keep)[0]:
        values[dg0.dofmap.cell_dofs(int(cell))] = 0.0
    field.x.scatter_forward()
    return field


def _quadrant_weight_field(msh, j, eps, name):
    """DG0 ``w_j`` over the whole mesh, so ParaView can threshold a quadrant."""
    x = ufl.SpatialCoordinate(msh)
    dg0 = fem.functionspace(msh, ("DG", 0))
    # OPS-18: `interpolation_points` is a property on the 0.11 image, not a
    # method.
    expr = fem.Expression(_quadrant_weight(x, j, eps), dg0.element.interpolation_points)
    field = fem.Function(dg0, name=name)
    field.interpolate(expr)
    field.x.scatter_forward()
    return field


def _real_copy(field, name):
    """A real-valued copy of a (complex-dtype, zero-imaginary) DG0 Function.

    XDMF carries no complex array (`EX-14`/`EX-17`); every SAR/weight field
    here is a real magnitude stored in a complex array, so ``.real`` is taken
    before the write.
    """
    out = fem.Function(field.function_space, name=name)
    out.x.array[:] = np.real(field.x.array)
    out.x.scatter_forward()
    return out


def _write_paraview(msh, cell_tags, fields, comm):
    OUTPUT_DIR.mkdir(exist_ok=True)
    written = {}
    combined, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined", msh, cell_tags, fields, comm=comm
    )
    if combined is not None:
        written["cells + SAR map + quadrant weights"] = combined
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return written


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ports:` group)."
        )

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            "EX-43 — the first coil-driven SAR quantity in ParaView: "
            "quadrant powers of the primal SAR on the loaded birdcage",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            "\n[fixture] `GEO-18` gapped + sheeted 4-leg birdcage, phantom "
            "loaded, `PORT-9` leg (d)'s `build_four_port_sweep`, default mesh "
            f"({DEFAULT_CELL_COUNT} cells on record), 10 MHz, degree 1\n"
            "[gates]   (i) twelve C4 pairs and four mirror pairs of quadrant "
            "power <= {:.1f}% (imported, unmoved) and against step 3g/3i's "
            "records at rtol {:.0e}; (ii) partition identity Sigma_j P_j = "
            "P_phantom at rtol {:.0e}, all five drives; (iii) P1 phantom total "
            "vs step 1's record\n"
            "[control] mis-paired 180-degree quadrant control strictly > the "
            "C4 pairing at every k".format(
                C4_COVARIANCE_BAND * 100, RECORD_RTOL, PARTITION_RTOL
            ),
            flush=True,
        )

    # ---- the gated fixture, built by the gate module itself -----------------
    sweep = build_four_port_sweep()
    msh = sweep["mesh"]
    cell_ratio = sweep["cells"] / STEP2_CELL_COUNT
    assert abs(cell_ratio - 1.0) <= CELL_RATIO_BAND, (
        f"the fixture meshed {sweep['cells']} cells against the recorded "
        f"{STEP2_CELL_COUNT} (ratio {cell_ratio:.6f}) — every record this "
        "example reproduces was measured on that mesh"
    )

    # ---- the four single-port drives, exactly step 3g/h/i's construction ----
    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    order = sorted(azimuths)
    solves = {pid: _solve_driven(sweep, pid) for pid in order}
    indices = {
        pid: _port_index(azimuths[pid], azimuths["P1"], QUADRATURE_STEP_DEG)
        for pid in order
    }
    by_k = {indices[pid]: pid for pid in order}

    dx_phantom = ufl.Measure(
        "dx",
        domain=msh,
        subdomain_data=sweep["cell_tags"],
        metadata={"quadrature_degree": QUADRATURE_DEGREE},
    )(PHANTOM_CELL_TAG)
    sigma_field = solves["P1"]["fields"].sigma_field

    totals, quadrants = {}, {}
    for k in range(4):
        pid = by_k[k]
        totals[k], quadrants[k] = _quadrant_powers(
            solves[pid]["fields"].e_complex, sigma_field, dx_phantom, comm
        )

    ks = [indices[pid] for pid in order]
    e_quadrature = _superpose_complex(
        [solves[pid]["fields"].e_complex for pid in order],
        quadrature_phase_weights(ks, "ccw"),
        name="E_quadrature_ccw",
    )
    quad_total, quad_parts = _quadrant_powers(
        e_quadrature, sigma_field, dx_phantom, comm
    )

    if comm.rank == 0:
        print(
            f"\n[fixture] {sweep['cells']} cells (record {DEFAULT_CELL_COUNT}, "
            f"ratio {cell_ratio:.6f}), mesh {sweep['mesh_time']:.1f} s, "
            f"sweep {sweep['sweep_time']:.1f} s, four extra solves "
            + ", ".join(f"{p} {solves[p]['solve_time']:.2f} s" for p in order)
            + f" at -n {comm.size}",
            flush=True,
        )

    # ---- gate (ii): the partition identity, all five drives -----------------
    if comm.rank == 0:
        print(
            f"\n[gate ii] partition identity Sigma_j P_j^(k) = P_phantom^(k), "
            f"ASSERTED at rtol {PARTITION_RTOL:.0e}:",
            flush=True,
        )
    for k in range(4):
        partition_sum = sum(quadrants[k])
        residual = abs(partition_sum - totals[k]) / abs(totals[k])
        if comm.rank == 0:
            print(
                f"        k={k} ({by_k[k]})  sum {partition_sum:.9e}  total "
                f"{totals[k]:.9e}  residual {residual:.3e}",
                flush=True,
            )
        assert residual <= PARTITION_RTOL, (
            f"drive k={k} ({by_k[k]}): the quadrant partition sums to "
            f"{partition_sum:.9e} W, not the phantom total {totals[k]:.9e} W "
            f"(residual {residual:.3e}, band {PARTITION_RTOL:.0e}) — a wrong "
            "measure, a dropped reduction, or a partition that does not "
            "partition (§7 `EX-43` negative result: stop)"
        )
    quad_partition_sum = sum(quad_parts)
    quad_residual = abs(quad_partition_sum - quad_total) / abs(quad_total)
    if comm.rank == 0:
        print(
            f"        quadrature   sum {quad_partition_sum:.9e}  total "
            f"{quad_total:.9e}  residual {quad_residual:.3e}",
            flush=True,
        )
    assert quad_residual <= PARTITION_RTOL, (
        f"the quadrature drive's quadrant partition sums to "
        f"{quad_partition_sum:.9e} W, not its own total {quad_total:.9e} W "
        f"(residual {quad_residual:.3e}, band {PARTITION_RTOL:.0e})"
    )

    # ---- gate (iii): the P1 total vs step 1's recorded phantom power --------
    p1_total = totals[0]
    p1_relative = abs(p1_total - STEP1_GATE_I_P1_PHANTOM_POWER_W) / abs(
        STEP1_GATE_I_P1_PHANTOM_POWER_W
    )
    if comm.rank == 0:
        print(
            f"\n[gate iii] P1 phantom total {p1_total:.9e} W vs step 1's record "
            f"{STEP1_GATE_I_P1_PHANTOM_POWER_W:.9e} W (relative "
            f"{p1_relative:.3e}, rtol {RECORD_RTOL:.0e})",
            flush=True,
        )
    assert _reproduces(p1_total, STEP1_GATE_I_P1_PHANTOM_POWER_W, RECORD_RTOL), (
        f"the P1 drive's phantom total reads {p1_total:.9e} W, not step 1's "
        f"recorded {STEP1_GATE_I_P1_PHANTOM_POWER_W:.9e} W at rtol "
        f"{RECORD_RTOL:.0e} — same mesh, same fixture, so something upstream "
        "moved (§7 `EX-43` negative result: stop)"
    )

    # ---- gate (i): the twelve C4 pairs and the mis-paired negative control --
    pairs, control_pairs = {}, {}
    for k in range(3):
        for j in range(4):
            ref = quadrants[k][j]
            pairs[(k, j)] = abs(quadrants[k + 1][(j + 1) % 4] - ref) / ref
            control_pairs[(k, j)] = abs(quadrants[k + 1][(j + 2) % 4] - ref) / ref
    c4_by_k = {k: float(np.mean([pairs[(k, j)] for j in range(4)])) for k in range(3)}
    control_by_k = {
        k: float(np.mean([control_pairs[(k, j)] for j in range(4)])) for k in range(3)
    }

    if comm.rank == 0:
        print(
            f"\n[gate i] the twelve C4 pairs |P_(j+1)^(k+1) - P_j^(k)| / P_j^(k) "
            f"(ASSERTED <= {C4_COVARIANCE_BAND * 100:.1f}% and against step 3g's "
            f"records at rtol {RECORD_RTOL:.0e}):",
            flush=True,
        )
    for k in range(3):
        for j in range(4):
            value = pairs[(k, j)]
            record = STEP3G_INTEGRAL_PAIR_RECORDS[(k, j)]
            assert value <= C4_COVARIANCE_BAND, (
                f"C4 pair (k={k}, j={j}) reads {value * 100:.4f}%, outside the "
                f"imported {C4_COVARIANCE_BAND * 100:.1f}% band (§7 `EX-43` "
                "negative result: known-issues entry, report, stop; no band "
                "moves)"
            )
            assert _reproduces(value, record, RECORD_RTOL), (
                f"C4 pair (k={k}, j={j}) reads {value * 100:.6f}%, not step "
                f"3g's recorded {record * 100:.4f}% at rtol {RECORD_RTOL:.0e} — "
                "a wiring defect in this example, not physics (§7 `EX-43` "
                "negative result: journal, stop)"
            )
        if comm.rank == 0:
            row = "  ".join(f"{pairs[(k, j)] * 100:8.4f}%" for j in range(4))
            print(
                f"        k={k}->{k + 1}  {row}   mean {c4_by_k[k] * 100:8.4f}%"
                f"   mis-paired control {control_by_k[k] * 100:9.4f}%"
                f"   ratio {control_by_k[k] / c4_by_k[k]:7.3f}x",
                flush=True,
            )
        assert control_by_k[k] > c4_by_k[k], (
            f"the mis-paired 180-degree quadrant control at k={k} reads "
            f"{control_by_k[k] * 100:.4f}%, not strictly above the C4 pairing's "
            f"{c4_by_k[k] * 100:.4f}% — the negative control failed to separate"
        )

    # ---- the mirror identity (step 3i), one reading per drive ---------------
    mirror_pairs, mirror_control = {}, {}
    for k in range(4):
        ref = quadrants[k][(k - 1) % 4]
        flank = quadrants[k][(k + 1) % 4]
        opposite = quadrants[k][(k + 2) % 4]
        mirror_pairs[k] = abs(flank - ref) / ref
        mirror_control[k] = abs(flank - opposite) / opposite

    if comm.rank == 0:
        print(
            f"\n[mirror]  P_(k-1)^(k) = P_(k+1)^(k), one reading per drive "
            f"(ASSERTED <= {C4_COVARIANCE_BAND * 100:.1f}% and against step 3i's "
            f"records at rtol {RECORD_RTOL:.0e}):",
            flush=True,
        )
    for k in range(4):
        value = mirror_pairs[k]
        record = STEP3I_MIRROR_RECORDS[k]
        assert value <= C4_COVARIANCE_BAND, (
            f"mirror pair k={k} reads {value * 100:.4f}%, outside the imported "
            f"{C4_COVARIANCE_BAND * 100:.1f}% band (§7 `EX-43` negative result: "
            "known-issues entry, report, stop; no band moves)"
        )
        assert _reproduces(value, record, RECORD_RTOL), (
            f"mirror pair k={k} reads {value * 100:.6f}%, not step 3i's "
            f"recorded {record * 100:.4f}% at rtol {RECORD_RTOL:.0e} — a wiring "
            "defect in this example, not physics (§7 `EX-43` negative result: "
            "journal, stop)"
        )
        if comm.rank == 0:
            print(
                f"        k={k} ({by_k[k]})  {value * 100:8.4f}%   (record "
                f"{record * 100:.4f}%)   flank-vs-opposite control "
                f"{mirror_control[k] * 100:9.4f}%   ratio "
                f"{mirror_control[k] / value:7.3f}x",
                flush=True,
            )

    # ---- the deliverable: the SAR map and quadrant weights, ParaView --------
    rho = PHANTOM_RHO_KG_PER_M3
    cell_tags = sweep["cell_tags"]
    sar_p1 = _real_copy(
        _sar_map_field(
            solves["P1"]["fields"].e_complex,
            sigma_field,
            rho,
            cell_tags,
            PHANTOM_CELL_TAG,
            "SAR_P1_W_per_kg",
        ),
        "SAR_P1_W_per_kg",
    )
    sar_quadrature = _real_copy(
        _sar_map_field(
            e_quadrature,
            sigma_field,
            rho,
            cell_tags,
            PHANTOM_CELL_TAG,
            "SAR_quadrature_W_per_kg",
        ),
        "SAR_quadrature_W_per_kg",
    )
    weight_fields = {
        f"w_{j}": _real_copy(
            _quadrant_weight_field(msh, j, PARTITION_EPS_M, f"w_{j}"), f"w_{j}"
        )
        for j in range(4)
    }

    fields = {"SAR_P1_W_per_kg": sar_p1, "SAR_quadrature_W_per_kg": sar_quadrature}
    fields.update(weight_fields)
    written = _write_paraview(msh, cell_tags, fields, comm)

    if comm.rank == 0:
        print(
            "\n[paraview]",
            flush=True,
        )
        for what, path in written.items():
            print(f"  {what:<30s} {path}")
        print(
            "\n[paraview] the _combined file carries `SAR_P1_W_per_kg` and "
            "`SAR_quadrature_W_per_kg` (DG0, W/kg, phantom cells only — a "
            "VIEWING quantity, not the gate; the pointwise construction is the "
            "retired one), `w_0`..`w_3` (DG0, the azimuthal quadrant partition, "
            "for thresholding a quadrant) and `CellTags`."
            "\n           Threshold `CellTags` on "
            f"{PHANTOM_CELL_TAG} and colour by `SAR_P1_W_per_kg`, or by `w_0` "
            "to see one quadrant's weight.",
            flush=True,
        )
        print(
            f"\nAll gates hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
