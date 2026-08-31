"""Example (`EX-38`): the first **|B₁⁺| field** in ParaView — loaded birdcage, 10 MHz.

Every port example before this one stops at a **terminal** quantity. `ports:1`
(`EX-18`), `ports:2` (`EX-20`) and `ports:3` (`EX-24`) read impedances off the
two-torus pair; `ports:4` (`EX-32`) and `ports:5` (`EX-34`) read the birdcage's
4×4 ``Z``/``S`` at 10 MHz and across the Larmor ladder. None of them writes the
quantity an MRI transmit coil is actually judged on — the circularly polarised
transmit field ``|B₁⁺| = |B_x + jB_y|/2`` **inside the phantom**. `WF-6` step 1
(✅ 2026-08-30) gated that map, but it lives in a test module and nobody opens a
test module in ParaView. That is the angle this example adds, and it is the
§5.4 ramp `WF-6` step 1 owes.

**What runs.** `PORT-9` leg (d)'s own ``build_four_port_sweep`` — `GEO-18`'s
gapped, sheeted, phantom-loaded four-leg birdcage on `GEO-19` step B's mesh,
four ``f = 0.5`` lumped-element sheets at ``Z_p = 50 Ω``, 10 MHz — then **two**
extra driven solves (P1 and P2) kept for their fields, because the sweep returns
readings and not phasors. ``B = ∇×E/(−jω)`` comes from
:func:`~fem_em_solver.post.magnetic_flux_density_from_e` (DG0, Faraday), is
L²-projected to CG1 by :func:`~fem_em_solver.post.project_to_cg1` — the
production estimator since `WF-6` step 1d — and ``|B₁⁺|`` is formed from the
projected vector.

**It asserts, and it does not re-implement.** Every constant, band, record and
helper is imported from ``tests/validation/test_birdcage_b1_plus_map.py`` and
its upstream gate modules (the `EX-33` reading of the `ANS-1` rule: import the
construction, not only the constants). The anchors:

* **gate (i)**, the conservation identity — three-way real-power accounting at
  the P1 drive closes to ``POWER_BALANCE_BAND`` (1%), and reproduces step 1's
  recorded ``STEP1_GATE_I_P1_RESIDUAL`` = 9.795751e-03 at ``RECORD_RTOL``
  (1e-4);
* **gate (ii)**, the symmetry identity — the CG1 C4 covariance of the map,
  P1 → P2 at +90°, inside the imported ``C4_COVARIANCE_BAND`` (5%) and
  reproducing step 1b's recorded 2.1870% at ``CG1_RECORD_RTOL`` (1e-3);
* **the sample set** — every one of the tag-3 centroids in the sample cylinder
  evaluates in both drives *and* in the rotated image, at or above
  ``MIN_SAMPLE_POINTS``;
* **the fixture** — the mesh is `GEO-19` step B's to a cell ratio of 1.000000
  against ``STEP2_CELL_COUNT``, and both field solves run on the sweep's own
  mesh object (``reused_mesh``), so the map is demonstrably off the gated
  fixture and not off a rebuild.

**Negative control.** The same covariance is read on the raw **DG0** curl beside
the CG1 figure and asserted against step 1's recorded ``8.6516%`` at 1e-4. That
is the estimator floor gate (ii) was re-registered around (`WF-6` step 1d): a
DG0 column that moved would mean the *field* changed, not the estimator, and a
DG0 column that suddenly agreed with CG1 would mean the projection is no longer
doing anything.

**Scope: what gates (i)/(ii) license and nothing more.** A map and its symmetry
identity at 10 MHz on the F-small fixture, degree 1. **No** homogeneity or CV
number, no 64/128 MHz (`WF-6` step 2b), no quadrature drive (`ports:7`,
`EX-39`), no SAR claim — the phantom integral here is a power term — and no
absolute-accuracy claim about ``|B₁⁺|`` whatsoever. The identities are
self-consistency checks on one unconverged fixture.

Needs the complex DolfinX build. Run it through the example runner, which
sources complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:6

Outputs ``paraview_output/ports_06_birdcage_b1_plus_map_combined.xdmf`` — the
CG1 ``B`` phasor (real and imaginary vectors), the CG1 and DG0 ``|B₁⁺|`` scalars
and ``CellTags`` on one grid. Threshold ``CellTags`` on 3 to see the phantom and
colour it by ``B1_plus_cg1``: that picture is the deliverable.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
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
from fem_em_solver.post import (  # noqa: E402
    magnetic_flux_density_from_e,
    project_to_cg1,
)

from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE  # noqa: E402
from tests.validation.test_birdcage_b1_plus_map import (  # noqa: E402
    C4_COVARIANCE_BAND,
    CG1_RECORD_RTOL,
    MIN_SAMPLE_POINTS,
    POWER_BALANCE_BAND,
    RECORD_RTOL,
    SAMPLE_HALF_HEIGHT_M,
    SAMPLE_RADIUS_M,
    STEP1_DG0_C4_MISMATCH,
    STEP1_GATE_I_P1_RESIDUAL,
    STEP1B_CG1_RECORDS,
    _power_shares,
    _read_b1_plus,
    _read_b1_plus_cg1,
    _relative_l2,
    _rotate_z,
    _sample_points,
    _solve_driven,
)
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    TERMINATED_PORT_IMPEDANCE_OHM,
    build_four_port_sweep,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
    STEP2_CELL_COUNT,
)
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "ports_06_birdcage_b1_plus_map"

# The mesh this example must be standing on is `GEO-19` step B's, to the cell.
# A ratio band and not equality only because the count is read back through the
# sweep; nothing about this example is meaningful on a different mesh, since
# every record it reproduces was measured on that one.
CELL_RATIO_BAND = 1.0e-9


def _reproduces(value, record, rtol):
    """``|value − record| ≤ rtol·|record|`` — ``pytest.approx``'s relative test.

    The gate module states its record reproductions with ``pytest.approx``; the
    examples run as scripts, so the same comparison is written out here rather
    than pulling a test framework into the example path.
    """
    return abs(value - record) <= rtol * abs(record)


def _b1_plus_cg1_field(projected, name="B1_plus_cg1"):
    """``|B_x + jB_y|/2`` at the CG1 nodes of the projected ``B`` phasor.

    :func:`~fem_em_solver.post.b1_plus` is not reusable here: it builds its
    output on ``("DG", 0)`` by construction, so handing it a CG1 vector would
    write a nodal array into a cell array. The formula is the same one, applied
    on the projection's own space — and it is the field picture of exactly what
    ``_read_b1_plus_cg1`` reads at the sample points below (both take the
    magnitude *after* the projection, because ``|·|`` is not linear).
    """
    space = projected.function_space
    scalar = fem.functionspace(space.mesh, ("Lagrange", 1))
    out = fem.Function(scalar, name=name)
    components = np.asarray(projected.x.array).reshape(-1, 3)
    out.x.array[:] = np.abs(components[:, 0] + 1j * components[:, 1]) / 2.0
    out.x.scatter_forward()
    return out


def _paraview_fields(projected, b1_cg1, b1_dg0):
    """The CG1 ``B`` phasor split into real/imag, plus both ``|B₁⁺|`` reads.

    XDMF carries no complex array (`EX-14`/`EX-17`), so the projected phasor is
    split into two real vector fields on its own CG1 space. ``|B₁⁺|`` is a real
    magnitude stored in a complex array, hence the ``.real``.
    """
    space = projected.function_space
    b_re = fem.Function(space, name="B_real")
    b_re.x.array[:] = np.real(projected.x.array)
    b_im = fem.Function(space, name="B_imag")
    b_im.x.array[:] = np.imag(projected.x.array)

    b1_cg1_real = fem.Function(b1_cg1.function_space, name="B1_plus_cg1")
    b1_cg1_real.x.array[:] = np.real(b1_cg1.x.array)
    b1_dg0_real = fem.Function(b1_dg0.function_space, name="B1_plus_dg0")
    b1_dg0_real.x.array[:] = np.real(b1_dg0.x.array)

    for f in (b_re, b_im, b1_cg1_real, b1_dg0_real):
        f.x.scatter_forward()
    return {
        "B_real": b_re,
        "B_imag": b_im,
        "B1_plus_cg1": b1_cg1_real,
        "B1_plus_dg0": b1_dg0_real,
    }


def _write_paraview(msh, cell_tags, fields, comm):
    OUTPUT_DIR.mkdir(exist_ok=True)
    written = {}
    combined, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined", msh, cell_tags, fields, comm=comm
    )
    if combined is not None:
        written["cells + B / |B1+| fields"] = combined
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
            "EX-38 — the first |B1+| map of the loaded birdcage, 10 MHz",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            f"\n[fixture] `GEO-18` gapped + sheeted 4-leg birdcage, phantom "
            f"loaded (conductor tag {CONDUCTOR_CELL_TAG}, phantom tag "
            f"{PHANTOM_CELL_TAG}, air elsewhere)\n"
            f"[ports]   four lumped-element sheets, "
            f"Z_p = {TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ohm, "
            f"f = {FREQUENCY_HZ:.3e} Hz, degree 1\n"
            f"[gate i]  three-way real-power accounting at the P1 drive <= "
            f"{POWER_BALANCE_BAND:.0e} of the supplied power, reproducing "
            f"{STEP1_GATE_I_P1_RESIDUAL:.6e} at rtol {RECORD_RTOL:.0e}\n"
            f"[gate ii] CG1 C4 covariance P1 -> P2 at +90 deg <= "
            f"{C4_COVARIANCE_BAND * 100:.1f}%, reproducing step 1b's "
            f"{STEP1B_CG1_RECORDS['P2@+90deg'] * 100:.4f}% at rtol "
            f"{CG1_RECORD_RTOL:.0e}\n"
            f"[control] the same covariance on the raw DG0 curl reproduces step "
            f"1's {STEP1_DG0_C4_MISMATCH * 100:.4f}% at rtol {RECORD_RTOL:.0e} — "
            f"the estimator floor, printed beside the CG1 figure\n"
            f"[scope]   10 MHz, single drives, symmetry identity only — no "
            f"homogeneity/CV, no 64/128 MHz, no quadrature, no SAR, no absolute "
            f"claim",
            flush=True,
        )

    # ---- the gated fixture, built by the gate module itself -----------------
    sweep = build_four_port_sweep()
    msh = sweep["mesh"]
    cell_ratio = sweep["cells"] / STEP2_CELL_COUNT
    assert abs(cell_ratio - 1.0) <= CELL_RATIO_BAND, (
        f"the fixture meshed {sweep['cells']} cells against `GEO-19` step B's "
        f"recorded {STEP2_CELL_COUNT} (ratio {cell_ratio:.6f}) — every record "
        "this example reproduces was measured on that mesh, so a different one "
        "invalidates the comparison before any field is read"
    )

    # ---- two driven solves, kept for their fields ---------------------------
    solves = {pid: _solve_driven(sweep, pid) for pid in ("P1", "P2")}
    for pid, solved in solves.items():
        assert solved["fields"].e_complex.function_space.mesh is msh, (
            f"the {pid} solve did not run on the sweep's own mesh object — the "
            "map would then not be the gated fixture's"
        )
    reused_mesh = True

    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    # The rotation is read off the fixture's geometry, not chosen: it is the
    # azimuthal separation of the two sheets whose drives are compared.
    delta_deg = (azimuths["P2"] - azimuths["P1"]) % 360.0
    if comm.rank == 0:
        print(
            f"\n[fixture] {sweep['cells']} cells (`GEO-19` step B record "
            f"{STEP2_CELL_COUNT}, ratio {cell_ratio:.6f}), mesh "
            f"{sweep['mesh_time']:.1f} s, the gated sweep's four solves in "
            f"{sweep['sweep_time']:.1f} s at -n {comm.size}; reused_mesh = "
            f"{reused_mesh}\n"
            f"[solves]  two drives kept for their fields: "
            + ", ".join(f"{p} {solves[p]['solve_time']:.1f} s" for p in solves)
            + f"; drive rotation P1 -> P2 = {delta_deg:.6f} deg (from the "
            "fixture's own sheet azimuths)",
            flush=True,
        )
    assert abs(delta_deg - 90.0) < 1.0e-6, (
        f"the P1->P2 sheet separation reads {delta_deg:.9f} deg, not 90 deg — "
        "this is not the C4 layout the covariance identity assumes"
    )

    # ---- gate (i): the conservation identity at the P1 drive ----------------
    shares = _power_shares(sweep, solves["P1"])
    total = shares["phantom"] + shares["conductor"] + shares["sheet_total"]
    residual = abs(shares["supplied"] - total) / abs(shares["supplied"])
    blind = abs(shares["supplied"] - (total - shares["conductor"])) / abs(
        shares["supplied"]
    )
    if comm.rank == 0:
        print(
            f"\n[gate i] real-power accounting, P1 driven (V_src = 1 V):\n"
            f"    supplied  1/2 Re(V_src I*)          = {shares['supplied']:.9e} W\n"
            f"    phantom   1/2 int sigma|E|^2 (tag 3) = {shares['phantom']:.9e} W "
            f"({shares['phantom'] / shares['supplied'] * 100:.4f}%)\n"
            f"    conductor 1/2 int sigma|E|^2 (tag 1) = {shares['conductor']:.9e} W "
            f"({shares['conductor'] / shares['supplied'] * 100:.4f}%)\n"
            f"    sheets    sum 1/2 |I_i|^2 Re Z_p     = {shares['sheet_total']:.9e} W "
            f"({shares['sheet_total'] / shares['supplied'] * 100:.4f}%)\n"
            f"    residual |supplied - sum|/supplied   = {residual:.9e}  "
            f"(band {POWER_BALANCE_BAND:.0e}, step 1's record "
            f"{STEP1_GATE_I_P1_RESIDUAL:.6e}, relative "
            f"{abs(residual - STEP1_GATE_I_P1_RESIDUAL) / STEP1_GATE_I_P1_RESIDUAL:.3e})\n"
            f"    control: dropping the conductor term misses by {blind:.6e}, "
            f"outside the band — the term is weighed, not decorative",
            flush=True,
        )
    assert shares["supplied"] > 0.0, (
        f"the driven sheet supplies {shares['supplied']:.9e} W — a passive load "
        "cannot absorb negative real power, so the generator convention or the "
        "terminal current is wrong"
    )
    assert residual <= POWER_BALANCE_BAND, (
        f"power accounting misses by {residual:.6e} of the supplied "
        f"{shares['supplied']:.9e} W, outside the imported "
        f"{POWER_BALANCE_BAND:.0e} band (§7 `EX-38` negative result: "
        "known-issues entry, report, stop; no band moves)"
    )
    assert _reproduces(residual, STEP1_GATE_I_P1_RESIDUAL, RECORD_RTOL), (
        f"gate (i)'s P1 residual reads {residual:.9e}, not step 1's recorded "
        f"{STEP1_GATE_I_P1_RESIDUAL:.6e} at rtol {RECORD_RTOL:.0e} — same mesh, "
        "same fixture, so something upstream of this example moved"
    )
    assert blind > POWER_BALANCE_BAND, (
        f"dropping the conductor's 1/2 int sigma|E|^2 still closes to "
        f"{blind:.6e}, inside the {POWER_BALANCE_BAND:.0e} band — the identity "
        "is then insensitive to a term it is supposed to weigh"
    )

    # ---- gate (ii): the C4 covariance of the map, CG1 and DG0 ---------------
    points = _sample_points(sweep)
    rotated = _rotate_z(points, np.radians(delta_deg))
    projections = {
        pid: project_to_cg1(
            magnetic_flux_density_from_e(
                solves[pid]["fields"].e_complex, solves[pid]["omega"]
            )
        )
        for pid in ("P1", "P2")
    }

    dg0_p1, valid_a = _read_b1_plus(solves["P1"], points)
    dg0_p2, valid_b = _read_b1_plus(solves["P2"], rotated)
    cg1_p1, valid_c = _read_b1_plus_cg1(projections["P1"], points)
    cg1_p2, valid_d = _read_b1_plus_cg1(projections["P2"], rotated)
    mask = valid_a & valid_b & valid_c & valid_d
    n_valid, n_points = int(mask.sum()), int(points.shape[0])

    assert n_valid == n_points, (
        f"only {n_valid} of {n_points} sample points evaluated in both drives "
        "and in the rotated image; the set is inside the phantom by "
        "construction, so this is a geometry mistake and the l2 would silently "
        "read a subset"
    )
    assert n_valid >= MIN_SAMPLE_POINTS, (
        f"{n_valid} points is below the imported {MIN_SAMPLE_POINTS} floor — "
        "the covariance reading would be a handful of cells, not a map"
    )

    cg1_mismatch = _relative_l2(cg1_p2, cg1_p1, mask)
    dg0_mismatch = _relative_l2(dg0_p2, dg0_p1, mask)
    record = STEP1B_CG1_RECORDS["P2@+90deg"]
    if comm.rank == 0:
        print(
            f"\n[gate ii] C4 covariance of |B1+| on {n_valid} of {n_points} "
            f"phantom centroids (r <= {SAMPLE_RADIUS_M} m, |z| <= "
            f"{SAMPLE_HALF_HEIGHT_M} m), P2 read at the +{delta_deg:.3f} deg image "
            f"of the P1 set:\n"
            f"    CG1 (projected, the gated estimator) {cg1_mismatch * 100:.4f}%  "
            f"vs band {C4_COVARIANCE_BAND * 100:.1f}%  "
            f"{'PASS' if cg1_mismatch <= C4_COVARIANCE_BAND else 'MISS'}   "
            f"(step 1b record {record * 100:.4f}%, relative "
            f"{abs(cg1_mismatch - record) / record:.3e})\n"
            f"    DG0 (raw curl, the control)          {dg0_mismatch * 100:.4f}%  "
            f"(step 1 record {STEP1_DG0_C4_MISMATCH * 100:.4f}%, relative "
            f"{abs(dg0_mismatch - STEP1_DG0_C4_MISMATCH) / STEP1_DG0_C4_MISMATCH:.3e})\n"
            f"    the {dg0_mismatch / cg1_mismatch:.2f}x between them is the "
            "piecewise-constant cell scatter the CG1 projection removes — the "
            "estimator floor gate (ii) was re-registered around (`WF-6` step 1d),\n"
            f"    not a change in the field: both columns are asserted against "
            "their records",
            flush=True,
        )
    assert cg1_mismatch <= C4_COVARIANCE_BAND, (
        f"|B1+| from the P2 drive at the rotated image disagrees with the P1 map "
        f"by {cg1_mismatch * 100:.4f}% in relative l2 under the CG1 estimator, "
        f"outside the imported {C4_COVARIANCE_BAND * 100:.1f}% discretisation "
        "band (§7 `EX-38` negative result: known-issues entry, report, stop)"
    )
    assert _reproduces(cg1_mismatch, record, CG1_RECORD_RTOL), (
        f"the CG1 covariance reads {cg1_mismatch * 100:.6f}%, not step 1b's "
        f"recorded {record * 100:.4f}% at rtol {CG1_RECORD_RTOL:.0e} — same mesh, "
        "same points, same estimator, so something upstream moved"
    )
    assert _reproduces(dg0_mismatch, STEP1_DG0_C4_MISMATCH, RECORD_RTOL), (
        f"the DG0 control reads {dg0_mismatch * 100:.6f}%, not step 1's recorded "
        f"{STEP1_DG0_C4_MISMATCH * 100:.4f}% at rtol {RECORD_RTOL:.0e} — a moved "
        "DG0 column means the field changed, not the estimator"
    )
    assert dg0_mismatch > C4_COVARIANCE_BAND, (
        f"the raw DG0 curl now reads {dg0_mismatch * 100:.4f}%, inside the "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band — the projection would then not be "
        "the thing that made gate (ii) pass, and step 1d's provenance is wrong"
    )

    # ---- the deliverable: the map itself ------------------------------------
    b1_cg1_field = _b1_plus_cg1_field(projections["P1"])
    b1_dg0_field = solves["P1"]["b1_plus"]
    written = _write_paraview(
        msh,
        sweep["cell_tags"],
        _paraview_fields(projections["P1"], b1_cg1_field, b1_dg0_field),
        comm,
    )
    if comm.rank == 0:
        print(
            f"\n[map] |B1+| over the sample set, P1 driven at V_src = 1 V "
            f"(recorded, ungated — no absolute claim):\n"
            f"    CG1 mean {np.mean(cg1_p1[mask]):.6e} T, max "
            f"{np.max(cg1_p1[mask]):.6e} T, min {np.min(cg1_p1[mask]):.6e} T\n"
            f"    DG0 mean {np.mean(dg0_p1[mask]):.6e} T, max "
            f"{np.max(dg0_p1[mask]):.6e} T, min {np.min(dg0_p1[mask]):.6e} T",
            flush=True,
        )
        print("\n[paraview]", flush=True)
        for what, path in written.items():
            print(f"  {what:<26s} {path}")
        print(
            "\n[paraview] the _combined file carries `B_real` / `B_imag` (the "
            "CG1-projected B phasor),"
            "\n           `B1_plus_cg1` (CG1, the gated estimator), "
            "`B1_plus_dg0` (DG0, the raw curl)"
            "\n           and `CellTags`. Threshold `CellTags` on "
            f"{PHANTOM_CELL_TAG} for the phantom and colour it by"
            "\n           `B1_plus_cg1` — that is the transmit field this "
            "project has never pictured before."
            f"\n\nAll gates hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
