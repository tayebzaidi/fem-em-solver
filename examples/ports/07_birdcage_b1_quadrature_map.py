"""Example (`EX-39`): the **quadrature drive** in ParaView — ``|B₁⁺|`` *and* ``|B₁⁻|``.

`ports:6` (`EX-38`) writes the ``|B₁⁺|`` map of a **single** driven port. No real
MRI birdcage is driven that way: every port is driven at once, each 90° behind
its neighbour, so that the transverse field *rotates* and one sense — the one
that co-rotates with the nuclear precession — is left standing while the other
cancels. `WF-6` step 2 (✅ 2026-08-31) gated that drive by exact superposition
and measured a centre polarisation purity of **127.9**, the number MRI actually
cares about, in a test module nobody opens in ParaView. This example is the
picture of it: the co-rotating map beside the near-null counter-rotating one.

**Why superposition is exact, not an approximation.** The four single-drive
solves share one mesh, one operator and one source amplitude — *every* port's
sheet is in the bilinear form of *every* solve, carrying the same
``V = V_src − I·Z_p`` at the same ``Z_p = 50 Ω``; only the right-hand side moves.
A linear system with a fixed operator and four right-hand sides superposes
exactly, so the field of all four ports driven with phases ``φ_k`` **is**
``Σ_k e^{jφ_k} E_k``. This example asserts that premise (one shared ``Z_p``, one
shared ``V_src``, the solved drives equal to the fixture's) rather than assuming
it, and then builds the two senses on the fixture's own azimuth-increasing port
index ``k``::

    B_ccw = Σ_k e^{−jkπ/2} B_k        B_cw = Σ_k e^{+jkπ/2} B_k

The phase convention is **not re-derived here**: the weights come from
:func:`tests.validation.test_birdcage_b1_quadrature.quadrature_phase_weights`,
the single source of truth for the one thing that cost step 2 a window (its
docstring records the sign slip and what the wrong pairing measured).

**It asserts, and it does not re-implement.** Every band, record, helper and the
fixture itself are imported from
``tests/validation/test_birdcage_b1_quadrature.py`` and its upstream gate modules
(the `EX-33` reading of the `ANS-1` rule). The anchors:

* **identity (a), C4-invariance** — advancing the phase pattern one port is the
  same drive rotated 90°, which multiplies the superposed field by a global
  phase, and a global phase does not move a magnitude: ``|B₁⁺|_ccw(Rx)`` matches
  ``|B₁⁺|_ccw(x)`` inside the imported ``C4_COVARIANCE_BAND`` (5%), reproducing
  step 2's recorded **0.9818%** at ``CG1_RECORD_RTOL`` (1e-3);
* **identity (b), the mirror** — ``B`` is a pseudovector, so reflecting in the
  plane through port 1 exchanges the two rotation senses:
  ``|B₁⁻|_cw(Mx) = |B₁⁺|_ccw(x)``, same band, reproducing **0.8087%**;
* **the superposition premise** — one ``Z_p``, one ``V_src``, four solved drives
  that match the fixture's;
* **gate (i)** — step 1's conservation identity at the P1 drive still closes to
  ``POWER_BALANCE_BAND`` and reproduces ``STEP1_GATE_I_P1_RESIDUAL`` =
  9.795751e-03 at ``RECORD_RTOL`` (1e-4): the proof this is step 1's field;
* **the sample set and the fixture** — every tag-3 centroid in the sample
  cylinder evaluates in **both** senses on **all three** point sets (x, Rx, Mx),
  at or above ``MIN_SAMPLE_POINTS``; cell ratio 1.000000 against
  ``STEP2_CELL_COUNT``; all four field solves on the sweep's own mesh object.

**Negative control.** The mis-paired ``|B₁⁺|_cw(Mx)`` against ``|B₁⁺|_ccw(x)``
is ``|B₁⁻|_ccw`` in disguise — the sense a working quadrature coil drives
*towards zero* — and must **miss** the band; it reads **95.1975%**. Without it,
identity (b) could be passing on a degeneracy in which the two senses are
indistinguishable.

**Scope: what step 2 licenses and nothing more.** Two maps and two symmetry
identities at 10 MHz on the F-small fixture, degree 1, by superposition. The
centre purity, the mean ``|B₁⁺|`` and the CV are **printed and never asserted**:
a CV is a homogeneity figure, and a homogeneity figure needs a converged mesh and
a real drive to mean anything — this is a 10 MHz identity fixture with neither.
**No** 64/128 MHz (`WF-6` step 2b; `EX-40` is that example), no SAR, no
simultaneous-source solve, no absolute-accuracy claim about either sense.

Needs the complex DolfinX build. Run it through the example runner, which sources
complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:7

Outputs ``paraview_output/ports_07_birdcage_b1_quadrature_map_combined.xdmf`` —
the ccw CG1 ``B`` phasor, ``|B₁⁺|`` and ``|B₁⁻|`` of that same drive, and
``CellTags`` on one grid. Threshold ``CellTags`` on 3 and colour the phantom by
``B1_plus_ccw``, then by ``B1_minus_ccw`` on the *same* colour range: the second
picture being nearly black is the quadrature drive working.
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
    STEP1_GATE_I_P1_RESIDUAL,
    _power_shares,
    _rotate_z,
    _sample_points,
    _solve_driven,
)
from tests.validation.test_birdcage_b1_quadrature import (  # noqa: E402
    CENTRE_POINT,
    CONTROL_MIN_MISMATCH,
    QUADRATURE_STEP_DEG,
    STEP2_CENTRE_PURITY,
    STEP2_CONTROL_MISMATCH,
    STEP2_CV_CENTROIDS,
    STEP2_IDENTITY_RECORDS,
    STEP2_MEAN_B1_PLUS_CCW_T,
    _cv,
    _mirror_xy,
    _port_index,
    _read_senses,
    _relative_l2,
    _superpose_dg0,
    quadrature_phase_weights,
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
BASENAME = "ports_07_birdcage_b1_quadrature_map"

# The mesh this example must be standing on is `GEO-19` step B's, to the cell.
# A ratio band and not equality only because the count is read back through the
# sweep; nothing here is meaningful on a different mesh, since every record it
# reproduces was measured on that one.
CELL_RATIO_BAND = 1.0e-9

# The two identity labels, spelled exactly as the gate module keys them — the
# records are imported under these keys, so a typo is an immediate KeyError
# rather than a silently unchecked identity.
IDENTITY_A = "(a) C4 |B1+|_ccw(Rx) vs |B1+|_ccw(x)"
IDENTITY_B = "(b) mirror |B1-|_cw(Mx) vs |B1+|_ccw(x)"


def _reproduces(value, record, rtol):
    """``|value − record| ≤ rtol·|record|`` — ``pytest.approx``'s relative test.

    The gate modules state their record reproductions with ``pytest.approx``; the
    examples run as scripts, so the same comparison is written out here rather
    than pulling a test framework into the example path.
    """
    return abs(value - record) <= rtol * abs(record)


def _transverse_cg1_field(projected, sense, name):
    """``|B_x ± jB_y|/2`` at the CG1 nodes of a projected ``B`` phasor.

    :func:`~fem_em_solver.post.b1_plus` / ``b1_minus`` are not reusable here: both
    build their output on ``("DG", 0)`` by construction, so handing either a CG1
    vector would write a nodal array into a cell array. The arithmetic is the
    same, applied on the projection's own space — and it is the field picture of
    exactly what ``_read_senses`` reads at the sample points, since both take the
    magnitude *after* the projection (``|·|`` is not linear).
    """
    signs = {"plus": +1.0, "minus": -1.0}
    space = projected.function_space
    scalar = fem.functionspace(space.mesh, ("Lagrange", 1))
    out = fem.Function(scalar, name=name)
    components = np.asarray(projected.x.array).reshape(-1, 3)
    out.x.array[:] = (
        np.abs(components[:, 0] + signs[sense] * 1j * components[:, 1]) / 2.0
    )
    out.x.scatter_forward()
    return out


def _paraview_fields(projected, b1_plus_field, b1_minus_field):
    """The ccw CG1 ``B`` phasor split into real/imag, plus both rotation senses.

    XDMF carries no complex array (`EX-14`/`EX-17`), so the projected phasor is
    split into two real vector fields on its own CG1 space. Each ``|B₁^±|`` is a
    real magnitude stored in a complex array, hence the ``.real``.
    """
    space = projected.function_space
    b_re = fem.Function(space, name="B_real_ccw")
    b_re.x.array[:] = np.real(projected.x.array)
    b_im = fem.Function(space, name="B_imag_ccw")
    b_im.x.array[:] = np.imag(projected.x.array)

    plus_real = fem.Function(b1_plus_field.function_space, name="B1_plus_ccw")
    plus_real.x.array[:] = np.real(b1_plus_field.x.array)
    minus_real = fem.Function(b1_minus_field.function_space, name="B1_minus_ccw")
    minus_real.x.array[:] = np.real(b1_minus_field.x.array)

    for f in (b_re, b_im, plus_real, minus_real):
        f.x.scatter_forward()
    return {
        "B_real_ccw": b_re,
        "B_imag_ccw": b_im,
        "B1_plus_ccw": plus_real,
        "B1_minus_ccw": minus_real,
    }


def _write_paraview(msh, cell_tags, fields, comm):
    OUTPUT_DIR.mkdir(exist_ok=True)
    written = {}
    combined, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined", msh, cell_tags, fields, comm=comm
    )
    if combined is not None:
        written["cells + ccw B / |B1+| / |B1-|"] = combined
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
            "EX-39 — the quadrature drive: |B1+| and |B1-| of the loaded "
            "birdcage, 10 MHz",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            f"\n[fixture] `GEO-18` gapped + sheeted 4-leg birdcage, phantom "
            f"loaded (conductor tag {CONDUCTOR_CELL_TAG}, phantom tag "
            f"{PHANTOM_CELL_TAG}, air elsewhere)\n"
            f"[ports]   four lumped-element sheets, "
            f"Z_p = {TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ohm, "
            f"f = {FREQUENCY_HZ:.3e} Hz, degree 1; all four driven at once by "
            f"exact superposition of the four single-drive fields\n"
            f"[id (a)]  C4 invariance of the quadrature |B1+| map <= "
            f"{C4_COVARIANCE_BAND * 100:.1f}%, reproducing step 2's "
            f"{STEP2_IDENTITY_RECORDS[IDENTITY_A] * 100:.4f}% at rtol "
            f"{CG1_RECORD_RTOL:.0e}\n"
            f"[id (b)]  |B1-|_cw(Mx) = |B1+|_ccw(x) <= "
            f"{C4_COVARIANCE_BAND * 100:.1f}%, reproducing "
            f"{STEP2_IDENTITY_RECORDS[IDENTITY_B] * 100:.4f}% at the same rtol\n"
            f"[control] the mis-paired |B1+|_cw(Mx) vs |B1+|_ccw(x) must miss the "
            f"band; step 2 measured {STEP2_CONTROL_MISMATCH * 100:.4f}%\n"
            f"[scope]   10 MHz, degree 1, symmetry identities only — the purity, "
            f"the mean |B1+| and the CV below are PRINTED, NEVER ASSERTED; no "
            f"64/128 MHz, no SAR, no absolute claim",
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

    # ---- four driven solves, kept for their fields --------------------------
    order = ("P1", "P2", "P3", "P4")
    solves = {pid: _solve_driven(sweep, pid) for pid in order}
    for pid, solved in solves.items():
        assert solved["fields"].e_complex.function_space.mesh is msh, (
            f"the {pid} solve did not run on the sweep's own mesh object — the "
            "superposed map would then not be the gated fixture's"
        )
    reused_mesh = True

    # ---- the superposition premise, asserted rather than assumed ------------
    specs = sweep["specs"]
    impedances = {complex(spec.port_impedance_ohm) for spec in specs}
    assert impedances == {complex(TERMINATED_PORT_IMPEDANCE_OHM)}, (
        f"the four ports do not share one terminal impedance: {impedances}; the "
        "operator then differs between the drives and the phase-weighted sum is "
        "not the quadrature field"
    )
    drives = {complex(spec.drive_voltage_v) for spec in specs}
    assert len(drives) == 1, (
        f"the four ports do not share one drive amplitude: {drives} — the phase "
        "pattern would be weighting fields of unequal excitation"
    )
    solved_drives = {solve["source_voltage_v"] for solve in solves.values()}
    assert solved_drives == drives, (
        f"the solved drives {solved_drives} are not the fixture's {drives}"
    )

    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    # Both the rotation and the mirror plane are read off the fixture's geometry,
    # never chosen: the legs need not sit on the coordinate axes.
    delta_deg = (azimuths["P2"] - azimuths["P1"]) % 360.0
    assert abs(delta_deg - 90.0) < 1.0e-6, (
        f"the P1->P2 sheet separation reads {delta_deg:.9f} deg, not 90 deg — "
        "this is not the C4 layout the quadrature phase pattern is defined on"
    )
    indices = {
        pid: _port_index(azimuths[pid], azimuths["P1"], QUADRATURE_STEP_DEG)
        for pid in order
    }
    assert sorted(indices.values()) == [0, 1, 2, 3], (
        f"the four sheets do not occupy the four quadrature slots: {indices}"
    )

    if comm.rank == 0:
        print(
            f"\n[fixture] {sweep['cells']} cells (`GEO-19` step B record "
            f"{STEP2_CELL_COUNT}, ratio {cell_ratio:.6f}), mesh "
            f"{sweep['mesh_time']:.1f} s, the gated sweep's four solves in "
            f"{sweep['sweep_time']:.1f} s at -n {comm.size}; reused_mesh = "
            f"{reused_mesh}\n"
            f"[solves]  four drives kept for their fields: "
            + ", ".join(f"{p} {solves[p]['solve_time']:.1f} s" for p in order)
            + f"\n[premise] one Z_p = {TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ohm and "
            f"one V_src = {next(iter(drives))} V across all four solves, so the "
            "superposition is exact and not an approximation\n"
            f"[slots]   port quadrature index k (from the fixture's own "
            "azimuths): "
            + ", ".join(f"{p} {azimuths[p]:7.3f} deg -> k={indices[p]}" for p in order)
            + f"; mirror plane at {azimuths['P1']:.3f} deg (port 1's azimuth)",
            flush=True,
        )

    # ---- gate (i): step 1's conservation identity, still on this fixture ----
    shares = _power_shares(sweep, solves["P1"])
    total = shares["phantom"] + shares["conductor"] + shares["sheet_total"]
    residual = abs(shares["supplied"] - total) / abs(shares["supplied"])
    blind = abs(shares["supplied"] - (total - shares["conductor"])) / abs(
        shares["supplied"]
    )
    if comm.rank == 0:
        print(
            f"\n[gate i] real-power accounting, P1 driven (V_src = 1 V) — the "
            f"proof this is step 1's field:\n"
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
        f"{POWER_BALANCE_BAND:.0e} band (§7 `EX-39` negative result: "
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

    # ---- the two rotation senses, by exact superposition --------------------
    b_dg0 = {
        pid: magnetic_flux_density_from_e(
            solves[pid]["fields"].e_complex, solves[pid]["omega"]
        )
        for pid in order
    }
    fields = [b_dg0[pid] for pid in order]
    ks = np.array([indices[pid] for pid in order], dtype=float)
    # The phase convention is imported, never re-derived: `quadrature_phase_weights`
    # is step 2's single source of truth for it, and its module docstring records
    # what the opposite pairing measured (a near-null "ccw" and both identities
    # 10x off the floor).
    cg1 = {
        sense: project_to_cg1(
            _superpose_dg0(
                fields, quadrature_phase_weights(ks, sense), f"B_phasor_{sense}"
            ),
            name=f"B_phasor_{sense}_cg1",
        )
        for sense in ("ccw", "cw")
    }

    points = _sample_points(sweep)
    rotated = _rotate_z(points, np.radians(delta_deg))
    mirrored = _mirror_xy(points, azimuths["P1"])

    reads = {}
    for sense in ("ccw", "cw"):
        for label, pts in (("x", points), ("Rx", rotated), ("Mx", mirrored)):
            plus, minus, valid = _read_senses(cg1[sense], pts)
            reads[(sense, label)] = {"plus": plus, "minus": minus, "valid": valid}
    mask = np.logical_and.reduce([r["valid"] for r in reads.values()])
    n_valid, n_points = int(mask.sum()), int(points.shape[0])

    assert n_valid == n_points, (
        f"only {n_valid} of {n_points} sample points evaluated in both senses on "
        "all three point sets; the rotated and mirrored images are fresh points "
        "inside the phantom by construction, so this is a geometry mistake and "
        "the l2 would silently read a subset"
    )
    assert n_valid >= MIN_SAMPLE_POINTS, (
        f"{n_valid} points is below the imported {MIN_SAMPLE_POINTS} floor — the "
        "identity readings would be a handful of cells, not a map"
    )

    # ---- the two identities and the mis-paired control ----------------------
    identities = {
        IDENTITY_A: _relative_l2(
            reads[("ccw", "Rx")]["plus"], reads[("ccw", "x")]["plus"], mask
        ),
        IDENTITY_B: _relative_l2(
            reads[("cw", "Mx")]["minus"], reads[("ccw", "x")]["plus"], mask
        ),
    }
    control = _relative_l2(
        reads[("cw", "Mx")]["plus"], reads[("ccw", "x")]["plus"], mask
    )

    if comm.rank == 0:
        print(
            f"\n[identities] on {n_valid} of {n_points} phantom centroids "
            f"(r <= {SAMPLE_RADIUS_M} m, |z| <= {SAMPLE_HALF_HEIGHT_M} m), band "
            f"{C4_COVARIANCE_BAND * 100:.1f}% imported from step 1d:",
            flush=True,
        )
        for label, value in identities.items():
            record = STEP2_IDENTITY_RECORDS[label]
            print(
                f"    {label:<44} {value * 100:8.4f}%  "
                f"{'PASS' if value <= C4_COVARIANCE_BAND else 'MISS'}   "
                f"(step 2 record {record * 100:.4f}%, relative "
                f"{abs(value - record) / record:.3e})",
                flush=True,
            )
        print(
            f"    {'control |B1+|_cw(Mx) vs |B1+|_ccw(x)':<44} "
            f"{control * 100:8.4f}%  {'MISSES' if control > CONTROL_MIN_MISMATCH else 'INSIDE'}"
            f" the band, as it must   (step 2 read "
            f"{STEP2_CONTROL_MISMATCH * 100:.4f}%)\n"
            f"    the control is |B1-|_ccw in disguise — the sense the coil is "
            f"driving against, suppressed {control / identities[IDENTITY_B]:.0f}x "
            "relative to identity (b) on the same points",
            flush=True,
        )

    for label, value in identities.items():
        record = STEP2_IDENTITY_RECORDS[label]
        assert value <= C4_COVARIANCE_BAND, (
            f"identity {label} misses by {value * 100:.4f}%, outside the imported "
            f"{C4_COVARIANCE_BAND * 100:.1f}% CG1 floor — a superposition of four "
            "fields each inside the floor should be inside it, so this is a "
            "finding about the superposition path and not a band to widen (§7 "
            "`EX-39` negative result: known-issues entry, report, stop)"
        )
        assert _reproduces(value, record, CG1_RECORD_RTOL), (
            f"identity {label} reads {value * 100:.6f}%, not step 2's recorded "
            f"{record * 100:.4f}% at rtol {CG1_RECORD_RTOL:.0e} — same mesh, same "
            "points, same phase convention, so something upstream moved"
        )
    assert control > CONTROL_MIN_MISMATCH, (
        f"the mis-paired comparison reads {control * 100:.4f}%, inside the "
        f"{CONTROL_MIN_MISMATCH * 100:.1f}% band — the two rotation senses are "
        "not being told apart, so identity (b) is passing on a degeneracy"
    )

    # ---- printed, never asserted: purity, mean and CV -----------------------
    centre = {}
    for sense in ("ccw", "cw"):
        plus, minus, valid = _read_senses(cg1[sense], CENTRE_POINT)
        centre[sense] = {
            "plus": float(plus[0]),
            "minus": float(minus[0]),
            "valid": bool(valid[0]),
        }
    mean_plus = float(np.mean(reads[("ccw", "x")]["plus"][mask]))
    cv_centroids = _cv(reads[("ccw", "x")]["plus"][mask])

    if comm.rank == 0:
        print(
            "\n[reported, NOT GATED — no converged mesh, no real drive; none of "
            "these is a homogeneity or absolute claim]",
            flush=True,
        )
        for sense in ("ccw", "cw"):
            row = centre[sense]
            ratio = row["plus"] / row["minus"] if row["minus"] > 0.0 else float("inf")
            print(
                f"    centre purity {sense:<3} |B1+| {row['plus']:.6e} T, |B1-| "
                f"{row['minus']:.6e} T, ratio {ratio:10.4f}  (step 2 read "
                f"{STEP2_CENTRE_PURITY[sense]:.4f})"
                + ("" if row["valid"] else "   (POINT NOT FOUND)"),
                flush=True,
            )
        print(
            f"    mean |B1+|_ccw over {n_valid} centroids = {mean_plus:.6e} T at "
            f"1 V per port (step 2 read {STEP2_MEAN_B1_PLUS_CCW_T:.6e} T)\n"
            f"    CV of |B1+|_ccw over the same set = {cv_centroids * 100:.4f}% "
            f"(step 2 read {STEP2_CV_CENTROIDS * 100:.4f}%) — a CV needs a "
            "converged mesh and a real drive to be a homogeneity statement, and "
            "this fixture is neither",
            flush=True,
        )

    # ---- the deliverable: both maps of the co-rotating drive ----------------
    written = _write_paraview(
        msh,
        sweep["cell_tags"],
        _paraview_fields(
            cg1["ccw"],
            _transverse_cg1_field(cg1["ccw"], "plus", "B1_plus_ccw"),
            _transverse_cg1_field(cg1["ccw"], "minus", "B1_minus_ccw"),
        ),
        comm,
    )
    if comm.rank == 0:
        print("\n[paraview]", flush=True)
        for what, path in written.items():
            print(f"  {what:<30s} {path}")
        print(
            "\n[paraview] the _combined file carries `B_real_ccw` / `B_imag_ccw` "
            "(the CG1-projected quadrature B phasor),"
            "\n           `B1_plus_ccw` and `B1_minus_ccw` (the two rotation "
            "senses of that same drive)"
            "\n           and `CellTags`. Threshold `CellTags` on "
            f"{PHANTOM_CELL_TAG}, colour the phantom by `B1_plus_ccw`, then"
            "\n           switch to `B1_minus_ccw` **keeping the same colour "
            "range**: the second picture going"
            "\n           nearly black is the quadrature drive doing its job."
            f"\n\nAll identities hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
