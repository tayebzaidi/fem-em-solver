"""Example (`EX-40`): the `|B₁⁺|` ladder at the **Larmor frequencies**, 64 and 128 MHz.

`ports:6` (`EX-38`) put the first ``|B₁⁺|`` field of the loaded birdcage into
ParaView and `ports:7` (`EX-39`) added the quadrature drive — **both at
10 MHz**, which is the eddy-current rung this project meshes and gates on, and
not a frequency any MRI system runs at. `ports:5` (`EX-34`) does climb the
Larmor ladder, but it stops at the 4×4 ``S``-matrix: a terminal quantity, no
field. `WF-6` step 2b (✅ 2026-08-31) gated the B₁⁺ identities at 64 and
128 MHz for the first time — in a test module, and nobody opens a test module
in ParaView. **The frequency is the angle this example adds**, and it is the
§5.4 ramp step 2b owes.

**What runs.** `PORT-9` leg (d)'s own ``build_four_port_sweep`` — `GEO-18`'s
gapped, sheeted, phantom-loaded four-leg birdcage on `GEO-19` step B's mesh,
four ``f = 0.5`` lumped-element sheets at ``Z_p = 50 Ω`` — at **64 MHz**, then
at **128 MHz** through ``reuse=`` so both rungs stand on **one** mesh and the
frequency is demonstrably the only thing that moved. Three driven solves are
kept per rung for their fields (P1 and P2 for the identity, P3 for the
control), ``B = ∇×E/(−jω)`` comes from
:func:`~fem_em_solver.post.magnetic_flux_density_from_e` (DG0, Faraday), is
L²-projected to CG1 by :func:`~fem_em_solver.post.project_to_cg1` — the
production estimator since `WF-6` step 1d — and ``|B₁⁺|`` is formed from the
projected vector.

**It asserts, and it does not re-implement.** Every constant, band, record and
helper is imported from ``tests/validation/test_birdcage_b1_larmor.py`` and its
upstream gate modules (`ANS-1`'s rule, read as `EX-33` reads it: import the
construction, not only the constants). The anchors, per rung:

* **gate (i)**, the conservation identity — three-way real-power accounting at
  the P1 drive closes to the imported ``POWER_BALANCE_BAND`` (1%) and
  reproduces step 2b's recorded residual (**9.523130e-03** at 64 MHz,
  **9.244511e-03** at 128) at ``RECORD_RTOL`` (1e-4);
* **gate (ii)**, the symmetry identity — the CG1 C4 covariance of the map,
  P1 → P2 at +90°, inside the imported ``C4_COVARIANCE_BAND`` (5%) and
  reproducing step 2b's **2.2187%** / **2.1315%** at ``CG1_RECORD_RTOL``
  (1e-3);
* **the resolution** — phantom cells/λ prints **21.8936** / **12.5024** and is
  asserted above `PORT-11` step 3's imported floor of 10, because below it the
  gates are not to be read as a pass at all;
* **the sample set** — all 51 tag-3 centroids in the sample cylinder evaluate
  in both drives, in the control and in their rotated images, at or above
  ``MIN_SAMPLE_POINTS``;
* **the fixture** — one mesh for both rungs, at `GEO-19` step B's cell count to
  a ratio of 1.000000, with both rungs' solves on the sweep's own mesh object
  (``reused_mesh``).

**Negative control.** The mis-rotated comparison: P3 is 180° from P1, so
reading it at the *+90°* image is the same operation applied to the wrong
drive. It reproduces step 2b's **24.7535%** / **25.2589%** and is asserted
**outside** the 5% band — a covariance gate that passed on the wrong drive
would not be resolving the drive's azimuth at all.

**Printed, ungated, labelled.** The mean ``|B₁⁺|`` of the P1 single drive over
the sample set at 1 V per port, per rung, beside step 2b's recorded mean of
the *quadrature* map (6.500452e-08 / 4.936577e-08 T — a different drive, cited
for provenance and not reproduced here, since this example runs no quadrature).
The mean falls with frequency at fixed drive **voltage** because the terminal
current falls: that is a terminal-impedance effect, not a statement about the
coil's efficiency or homogeneity, and nothing here licenses reading it as one.

**Scope: what gates (i)/(ii) license and nothing more.** Single-drive maps and
one symmetry identity per rung, degree 1, F-small, on an unconverged fixture.
**No** quadrature (that is `ports:7`, at 10 MHz), no CV or homogeneity number,
no SAR, no tuning or resonance claim, and no absolute-accuracy claim about
``|B₁⁺|`` at either Larmor frequency whatsoever.

Needs the complex DolfinX build. Run it through the example runner, which
sources complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:8 -t 400

Outputs ``paraview_output/ports_08_birdcage_b1_larmor_ladder_64MHz_combined.xdmf``
and its ``…_128MHz_…`` twin — the CG1 ``B`` phasor (real and imaginary
vectors), the CG1 and DG0 ``|B₁⁺|`` scalars and ``CellTags`` on one grid.
Threshold ``CellTags`` on 3 to see the phantom and colour it by
``B1_plus_cg1``, then step between the two files with a common colour range:
that pair of pictures is the deliverable.
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
from tests.validation.test_birdcage_b1_larmor import (  # noqa: E402
    STEP2B_LARMOR_RECORDS,
)
from tests.validation.test_birdcage_b1_plus_map import (  # noqa: E402
    C4_COVARIANCE_BAND,
    CG1_RECORD_RTOL,
    MIN_SAMPLE_POINTS,
    POWER_BALANCE_BAND,
    RECORD_RTOL,
    SAMPLE_HALF_HEIGHT_M,
    SAMPLE_RADIUS_M,
    _power_shares,
    _read_b1_plus,
    _read_b1_plus_cg1,
    _relative_l2,
    _rotate_z,
    _sample_points,
    _solve_driven,
)
from tests.validation.test_lossy_sphere_fullwave import (  # noqa: E402
    FREQUENCY_128_HZ,
    FREQUENCY_64_HZ,
)
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    TERMINATED_PORT_IMPEDANCE_OHM,
    build_four_port_sweep,
)
from tests.validation.test_port_birdcage_larmor_gate_128 import (  # noqa: E402
    PHANTOM_CELLS_PER_LAMBDA_FLOOR,
    _resolution,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
    STEP2_CELL_COUNT,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "ports_08_birdcage_b1_larmor_ladder"

# The two rungs, in build order. 64 MHz builds the mesh and 128 MHz reuses it,
# so "one mesh" is a property of the construction and not of a comparison made
# afterwards. The labels are step 2b's, because its records are keyed by them.
RUNGS = (("64 MHz", FREQUENCY_64_HZ), ("128 MHz", FREQUENCY_128_HZ))
BASE_RUNG = "64 MHz"

# The mesh this example must be standing on is `GEO-19` step B's, to the cell.
# A ratio band and not equality only because the count is read back through the
# sweep; nothing here is meaningful on a different mesh, since every record it
# reproduces was measured on that one.
CELL_RATIO_BAND = 1.0e-9

# Phantom resolution is a mesh property, so the record is reproduced at the
# tighter of the two rtols in play rather than at the Krylov-figure one.
RESOLUTION_RECORD_RTOL = 1.0e-4


def _reproduces(value, record, rtol):
    """``|value − record| ≤ rtol·|record|`` — ``pytest.approx``'s relative test.

    The gate module states its record reproductions with ``pytest.approx``; the
    examples run as scripts, so the same comparison is written out here rather
    than pulling a test framework into the example path.
    """
    return abs(value - record) <= rtol * abs(record)


def _b1_plus_cg1_field(projected, name):
    """``|B_x + jB_y|/2`` at the CG1 nodes of the projected ``B`` phasor.

    :func:`~fem_em_solver.post.b1_plus` is not reusable here: it builds its
    output on ``("DG", 0)`` by construction, so handing it a CG1 vector would
    write a nodal array into a cell array. `EX-38`'s pattern, applied on the
    projection's own space — and it is the field picture of exactly what
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


def _write_paraview(stem, msh, cell_tags, fields, comm):
    OUTPUT_DIR.mkdir(exist_ok=True)
    written = {}
    combined, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_{stem}_combined", msh, cell_tags, fields, comm=comm
    )
    if combined is not None:
        written[f"cells + B / |B1+| fields, {stem}"] = combined
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return written


def _read_rung(sweep, label, records, per_lambda, comm):
    """One rung: gate (i), gate (ii), the mis-rotated control, and the map.

    Returns the readings plus the CG1 projection of the P1 drive, which is what
    the ParaView file for this rung is written from.
    """
    msh = sweep["mesh"]
    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    # The rotation is read off the fixture's geometry, not chosen: it is the
    # azimuthal separation of the two sheets whose drives are compared.
    delta_deg = (azimuths["P2"] - azimuths["P1"]) % 360.0
    assert abs(delta_deg - 90.0) < 1.0e-6, (
        f"[{label}] the P1->P2 sheet separation reads {delta_deg:.9f} deg, not "
        "90 deg — this is not the C4 layout the covariance identity assumes"
    )

    # P1 and P2 carry the identity; P3 (180 deg from P1) is the control's drive.
    solves = {pid: _solve_driven(sweep, pid) for pid in ("P1", "P2", "P3")}
    for pid, solved in solves.items():
        assert solved["fields"].e_complex.function_space.mesh is msh, (
            f"[{label}] the {pid} solve did not run on the sweep's own mesh "
            "object — the map would then not be the gated fixture's"
        )

    if comm.rank == 0:
        print(
            f"\n[rung {label}] f = {sweep['problem'].frequency_hz:.6e} Hz, "
            f"{sweep['cells']} cells, degree 1, CG1 estimator; drive rotation "
            f"P1 -> P2 = {delta_deg:.6f} deg (from the fixture's own sheet "
            f"azimuths); phantom cells/lambda {per_lambda:.4f} (step 2b record "
            f"{records['cells_per_lambda_phantom']:.4f}, imported floor "
            f"{PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f})\n"
            f"[solves]  "
            + ", ".join(f"{p} {solves[p]['solve_time']:.2f} s" for p in solves),
            flush=True,
        )

    # The pre-gate stop rule, `PORT-11` step 3: below the floor the gates below
    # are not to be read as a pass, so they are not read at all.
    assert per_lambda >= PHANTOM_CELLS_PER_LAMBDA_FLOOR, (
        f"[{label}] the phantom resolves {per_lambda:.4f} cells per wavelength, "
        f"below the imported {PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f} floor — the "
        "identities below would be unreadable as a pass on this mesh"
    )
    assert _reproduces(
        per_lambda, records["cells_per_lambda_phantom"], RESOLUTION_RECORD_RTOL
    ), (
        f"[{label}] phantom cells/lambda reads {per_lambda:.6f}, not step 2b's "
        f"recorded {records['cells_per_lambda_phantom']:.4f} at rtol "
        f"{RESOLUTION_RECORD_RTOL:.0e} — the mesh or the media constants moved"
    )

    # ---- gate (i): the conservation identity at the P1 drive ----------------
    shares = _power_shares(sweep, solves["P1"])
    total = shares["phantom"] + shares["conductor"] + shares["sheet_total"]
    residual = abs(shares["supplied"] - total) / abs(shares["supplied"])
    blind = abs(shares["supplied"] - (total - shares["conductor"])) / abs(
        shares["supplied"]
    )
    record_i = records["gate_i_p1_residual"]
    if comm.rank == 0:
        print(
            f"[gate i]  real-power accounting, P1 driven (V_src = 1 V):\n"
            f"    supplied  1/2 Re(V_src I*)          = {shares['supplied']:.9e} W\n"
            f"    phantom   1/2 int sigma|E|^2 (tag 3) = {shares['phantom']:.9e} W "
            f"({shares['phantom'] / shares['supplied'] * 100:.4f}%)\n"
            f"    conductor 1/2 int sigma|E|^2 (tag 1) = {shares['conductor']:.9e} W "
            f"({shares['conductor'] / shares['supplied'] * 100:.4f}%)\n"
            f"    sheets    sum 1/2 |I_i|^2 Re Z_p     = {shares['sheet_total']:.9e} W "
            f"({shares['sheet_total'] / shares['supplied'] * 100:.4f}%)\n"
            f"    residual |supplied - sum|/supplied   = {residual:.9e}  "
            f"(band {POWER_BALANCE_BAND:.0e}, step 2b record {record_i:.6e}, "
            f"relative {abs(residual - record_i) / record_i:.3e})\n"
            f"    control: dropping the conductor term misses by {blind:.6e}, "
            f"outside the band — the term is weighed, not decorative",
            flush=True,
        )
    assert shares["supplied"] > 0.0, (
        f"[{label}] the driven sheet supplies {shares['supplied']:.9e} W — a "
        "passive load cannot absorb negative real power, so the generator "
        "convention or the terminal current is wrong"
    )
    assert residual <= POWER_BALANCE_BAND, (
        f"[{label}] power accounting misses by {residual:.6e} of the supplied "
        f"{shares['supplied']:.9e} W, outside the imported "
        f"{POWER_BALANCE_BAND:.0e} band (§7 `EX-40` negative result: "
        "known-issues entry, report, stop; no band moves)"
    )
    assert _reproduces(residual, record_i, RECORD_RTOL), (
        f"[{label}] gate (i)'s P1 residual reads {residual:.9e}, not step 2b's "
        f"recorded {record_i:.6e} at rtol {RECORD_RTOL:.0e} — same mesh, same "
        "fixture, same frequency, so something upstream of this example moved"
    )
    assert blind > POWER_BALANCE_BAND, (
        f"[{label}] dropping the conductor's 1/2 int sigma|E|^2 still closes to "
        f"{blind:.6e}, inside the {POWER_BALANCE_BAND:.0e} band — the identity "
        "is then insensitive to a term it is supposed to weigh"
    )

    # ---- gate (ii): the C4 covariance, and the mis-rotated control -----------
    points = _sample_points(sweep)
    rotated = _rotate_z(points, np.radians(delta_deg))
    projections = {
        pid: project_to_cg1(
            magnetic_flux_density_from_e(
                solves[pid]["fields"].e_complex, solves[pid]["omega"]
            ),
            name=f"B_phasor_cg1_{pid}",
        )
        for pid in solves
    }

    cg1_p1, valid_a = _read_b1_plus_cg1(projections["P1"], points)
    cg1_p2, valid_b = _read_b1_plus_cg1(projections["P2"], rotated)
    cg1_p3, valid_c = _read_b1_plus_cg1(projections["P3"], rotated)
    # The DG0 read is not asserted here (`EX-38` owns that control at 10 MHz);
    # its validity mask is kept so the map written below is read on the same
    # point set the identity was.
    _dg0_p1, valid_d = _read_b1_plus(solves["P1"], points)
    mask = valid_a & valid_b & valid_c & valid_d
    n_valid, n_points = int(mask.sum()), int(points.shape[0])

    assert n_valid == n_points, (
        f"[{label}] only {n_valid} of {n_points} sample points evaluated in "
        "every drive and in the rotated image; the set is inside the phantom by "
        "construction, so this is a geometry mistake and the l2 would silently "
        "read a subset"
    )
    assert n_valid >= MIN_SAMPLE_POINTS, (
        f"[{label}] {n_valid} points is below the imported {MIN_SAMPLE_POINTS} "
        "floor — the covariance reading would be a handful of cells, not a map"
    )

    covariance = _relative_l2(cg1_p2, cg1_p1, mask)
    control = _relative_l2(cg1_p3, cg1_p1, mask)
    record_ii = records["cg1_p2_at_plus90"]
    record_ctl = records["control_p3_at_plus90"]
    mean_p1 = float(np.mean(cg1_p1[mask]))
    if comm.rank == 0:
        print(
            f"[gate ii] C4 covariance of |B1+| on {n_valid} of {n_points} phantom "
            f"centroids (r <= {SAMPLE_RADIUS_M} m, |z| <= {SAMPLE_HALF_HEIGHT_M} "
            f"m), read at the +{delta_deg:.3f} deg image of the P1 set:\n"
            f"    P2@+90deg (the identity)   {covariance * 100:8.4f}%  vs band "
            f"{C4_COVARIANCE_BAND * 100:.1f}%  "
            f"{'PASS' if covariance <= C4_COVARIANCE_BAND else 'MISS'}   "
            f"(step 2b record {record_ii * 100:.4f}%, relative "
            f"{abs(covariance - record_ii) / record_ii:.3e})\n"
            f"    P3@+90deg (the control)    {control * 100:8.4f}%  ASSERTED > "
            f"band  (step 2b record {record_ctl * 100:.4f}%, relative "
            f"{abs(control - record_ctl) / record_ctl:.3e})\n"
            f"    the {control / covariance:.1f}x between them is the gate "
            "resolving the drive's azimuth: P3 sits 180 deg from P1, so reading "
            "it at\n"
            f"    the +90 deg image is the right operation on the wrong drive\n"
            f"[map]     mean |B1+| over the sample set, P1 single drive at "
            f"V_src = 1 V (REPORTED, UNGATED, no absolute claim): "
            f"{mean_p1:.6e} T\n"
            f"          step 2b's recorded mean for the *quadrature* (ccw) map at "
            f"this rung was {records['mean_b1_plus_ccw_t']:.6e} T — a different "
            "drive,\n"
            f"          cited for provenance and not reproduced here (this "
            "example runs no quadrature)",
            flush=True,
        )
    assert covariance <= C4_COVARIANCE_BAND, (
        f"[{label}] |B1+| from the P2 drive at the rotated image disagrees with "
        f"the P1 map by {covariance * 100:.4f}% in relative l2 under the CG1 "
        f"estimator, outside the imported {C4_COVARIANCE_BAND * 100:.1f}% band "
        f"(measured at 10 MHz); phantom cells/lambda here is {per_lambda:.4f} — "
        "record both, do not widen (§7 `EX-40` negative result)"
    )
    assert _reproduces(covariance, record_ii, CG1_RECORD_RTOL), (
        f"[{label}] the CG1 covariance reads {covariance * 100:.6f}%, not step "
        f"2b's recorded {record_ii * 100:.4f}% at rtol {CG1_RECORD_RTOL:.0e} — "
        "same mesh, same points, same estimator, so something upstream moved"
    )
    assert control > C4_COVARIANCE_BAND, (
        f"[{label}] the mis-rotated control (P3 at +90 deg, 180 deg from P1) "
        f"matches the P1 map to {control * 100:.4f}%, inside the "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band — the covariance gate is then not "
        "resolving the drive's azimuth at all"
    )
    assert _reproduces(control, record_ctl, CG1_RECORD_RTOL), (
        f"[{label}] the control reads {control * 100:.6f}%, not step 2b's "
        f"recorded {record_ctl * 100:.4f}% at rtol {CG1_RECORD_RTOL:.0e}"
    )

    return {
        "projection": projections["P1"],
        "b1_dg0": solves["P1"]["b1_plus"],
        "covariance": covariance,
        "control": control,
        "residual": residual,
        "mean_p1": mean_p1,
        "per_lambda": per_lambda,
        "n_valid": n_valid,
        "n_points": n_points,
    }


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
            "EX-40 — the |B1+| ladder at the Larmor frequencies, 64 and 128 MHz",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            f"\n[fixture] `GEO-18` gapped + sheeted 4-leg birdcage, phantom "
            f"loaded (conductor tag {CONDUCTOR_CELL_TAG}, phantom tag "
            f"{PHANTOM_CELL_TAG}, air elsewhere)\n"
            f"[ports]   four lumped-element sheets, "
            f"Z_p = {TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ohm, degree 1; two rungs "
            f"on ONE mesh: "
            + ", ".join(f"{lab} ({f:.3e} Hz)" for lab, f in RUNGS)
            + "\n"
            f"[gate i]  three-way real-power accounting at the P1 drive <= "
            f"{POWER_BALANCE_BAND:.0e} of the supplied power, reproducing step "
            f"2b's residual at rtol {RECORD_RTOL:.0e}\n"
            f"[gate ii] CG1 C4 covariance P1 -> P2 at +90 deg <= "
            f"{C4_COVARIANCE_BAND * 100:.1f}%, reproducing step 2b's record at "
            f"rtol {CG1_RECORD_RTOL:.0e}\n"
            f"[control] the mis-rotated P3 read at +90 deg, ASSERTED outside the "
            f"same band and reproducing its own record\n"
            f"[scope]   single drives, symmetry identity only — no quadrature "
            f"(`ports:7`), no homogeneity/CV, no SAR, no tuning, no absolute "
            f"claim",
            flush=True,
        )

    # ---- the gated fixture, built by the gate module itself -----------------
    sweeps = {}
    base = build_four_port_sweep(frequency_hz=dict(RUNGS)[BASE_RUNG])
    sweeps[BASE_RUNG] = base
    for label, freq in RUNGS:
        if label == BASE_RUNG:
            continue
        sweeps[label] = build_four_port_sweep(frequency_hz=freq, reuse=base)

    cell_ratio = base["cells"] / STEP2_CELL_COUNT
    assert abs(cell_ratio - 1.0) <= CELL_RATIO_BAND, (
        f"the fixture meshed {base['cells']} cells against `GEO-19` step B's "
        f"recorded {STEP2_CELL_COUNT} (ratio {cell_ratio:.6f}) — every record "
        "this example reproduces was measured on that mesh, so a different one "
        "invalidates the comparison before any field is read"
    )
    for label, _f in RUNGS:
        assert sweeps[label]["mesh"] is base["mesh"], (
            f"the {label} rung did not stand on the base rung's mesh object — "
            "the ladder is then two fixtures and not one"
        )
    reused_mesh = True

    # ``_resolution`` reads cell sizes off the mesh, so one solved rung supplies
    # the table for every frequency in it.
    resolution = _resolution(base)

    frequencies = {
        label: float(sweeps[label]["problem"].frequency_hz) for label, _f in RUNGS
    }
    assert len(set(frequencies.values())) == len(RUNGS), (
        f"the two rungs did not run at two distinct frequencies: {frequencies}"
    )
    if comm.rank == 0:
        print(
            f"\n[fixture] {base['cells']} cells (`GEO-19` step B record "
            f"{STEP2_CELL_COUNT}, ratio {cell_ratio:.6f}), mesh "
            f"{base['mesh_time']:.1f} s at -n {comm.size}; reused_mesh = "
            f"{reused_mesh}; frequencies "
            + ", ".join(f"{lab} {f:.6e} Hz" for lab, f in frequencies.items()),
            flush=True,
        )

    rows, written = {}, {}
    for label, _f in RUNGS:
        row = _read_rung(
            sweeps[label],
            label,
            STEP2B_LARMOR_RECORDS[label],
            resolution["table"][label]["cells_per_lambda_phantom"],
            comm,
        )
        rows[label] = row
        stem = label.replace(" ", "")
        written.update(
            _write_paraview(
                stem,
                base["mesh"],
                base["cell_tags"],
                _paraview_fields(
                    row["projection"],
                    _b1_plus_cg1_field(row["projection"], f"B1_plus_cg1_{stem}"),
                    row["b1_dg0"],
                ),
                comm,
            )
        )

    if comm.rank == 0:
        print(
            f"\n[ladder] both rungs on one {base['cells']}-cell mesh, degree 1, "
            f"CG1 estimator:",
            flush=True,
        )
        print(
            "    rung       cells/lambda   gate(i) P1     (ii) P2@+90   "
            "control P3@+90   mean |B1+| (P1)",
            flush=True,
        )
        for label, _f in RUNGS:
            row = rows[label]
            print(
                f"    {label:<10} {row['per_lambda']:9.4f}    "
                f"{row['residual']:.4e}     {row['covariance'] * 100:8.4f}%   "
                f"{row['control'] * 100:11.4f}%   {row['mean_p1']:.6e} T",
                flush=True,
            )
        print(
            f"    every column asserted against step 2b's record "
            f"(`20260831T140418Z_WF-6-step2b.log`); the identity column inside "
            f"the {C4_COVARIANCE_BAND * 100:.1f}% band, the control outside it.",
            flush=True,
        )
        print("\n[paraview]", flush=True)
        for what, path in written.items():
            print(f"  {what:<38s} {path}")
        print(
            "\n[paraview] each _combined file carries `B_real` / `B_imag` (the "
            "CG1-projected B phasor),"
            "\n           `B1_plus_cg1` (CG1, the gated estimator), "
            "`B1_plus_dg0` (DG0, the raw curl)"
            "\n           and `CellTags`. Threshold `CellTags` on "
            f"{PHANTOM_CELL_TAG} for the phantom, colour it by"
            "\n           `B1_plus_cg1`, and put both rungs on a common range: "
            "that pair is the first"
            "\n           picture this project has of the transmit field at the "
            "frequencies it exists for."
            f"\n\nAll gates hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
