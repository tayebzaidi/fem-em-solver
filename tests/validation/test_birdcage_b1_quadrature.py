"""`WF-6` step 2 — the quadrature drive by exact superposition, 10 MHz.

Step 1 read ``|B₁⁺|`` from a *single* driven port.  A real birdcage is driven in
**quadrature**: every port at once, each 90° behind its neighbour, so that the
transverse field rotates.  This module builds that drive without a new solve.

**Why superposition is exact here, not an approximation.**  The four
single-drive solves in :func:`b1_plus_map` share one mesh, one problem, one
source amplitude, and — the part that matters — *every* port's sheet is in the
bilinear form of *every* solve, carrying the same linear law ``V = V_src − I·Z_p``
with the same ``Z_p = 50 Ω``.  The only difference between the four solves is
which sheet also carries the impressed source, i.e. the right-hand side.  A
linear system with a fixed operator and four right-hand sides superposes
exactly, so the field of all four ports driven with phases ``φ_k`` **is**
``Σ_k e^{jφ_k} E_k``.  The test asserts that premise (shared ``Z_p``, shared
``V_src``) rather than assuming it.

Two rotation senses are formed, on the fixture's own port-azimuth index
``k = 0…3`` (increasing with azimuth)::

    B_ccw = Σ_k e^{−jkπ/2} B_k        B_cw = Σ_k e^{+jkπ/2} B_k

``ccw`` names the sense that co-rotates with ``B₁⁺``; on an azimuth-*increasing*
index that is the phase pattern which lags, and the fixture's centre purity
measures it (see the sign-convention note in :func:`quadrature_map`).

each superposed on the raw DG0 curl and then pushed through
:func:`~fem_em_solver.post.project_to_cg1` — the production estimator `WF-6`
step 1d ruled on — before any point is read.  ``|B₁⁺|`` and ``|B₁⁻|`` are formed
from the *evaluated* complex vector: ``|·|`` is not linear.

**The two asserted identities**, both symmetry, both at the CG1 floor:

* **(a) C4-invariance of the quadrature map.**  Advancing the phase pattern by
  one port is the same drive rotated by 90°, and it multiplies the superposed
  field by a global phase: with ``B_k(Rx) = R B_{k−1}(x)`` on a C4-symmetric
  problem, ``B_ccw(Rx) = j·R B_ccw(x)``, and ``B_x + jB_y`` picks up ``e^{jα}``
  under a rotation by ``α`` about z.  The two phases multiply to ``−1``, so the
  *magnitude* is invariant: ``|B₁⁺|_ccw(Rx) = |B₁⁺|_ccw(x)``.  Relative ℓ² over
  the sample set ``≤ 5%`` — step 1d's ``C4_COVARIANCE_BAND``, imported, never
  re-derived here.
* **(b) The mirror identity.**  A 4-leg birdcage has a mirror plane through each
  port; ``M`` is the one through port 1's azimuth, read off the fixture.  It
  fixes ports 1 and 3 and swaps 2 with 4, and ``B`` is a pseudovector
  (``B → −MB``), so reversing the rotation sense is the same operation as
  reflecting: ``B_cw(Mx) = −M B_ccw(x)``, whence
  ``|B₁⁻|_cw(Mx) = |B₁⁺|_ccw(x)``.  Same 5% floor: a mesh that is not itself
  mirror-symmetric enters at the same order as it does in (a).

**Negative controls.**  (1) The mis-paired comparison ``|B₁⁺|_ccw(x)`` against
``|B₁⁺|_cw(Mx)`` must **miss** the band — it is ``|B₁⁻|_ccw`` in disguise, which
a working quadrature coil drives towards zero.  Asserted ``> 5%`` only, the way
step 1d's mis-rotated control is.  (2) The P1 single drive's centre purity is
printed as the "what a *non*-rotating field reads" line: a linear polarisation
is an equal mix of the two senses, ``|B₁⁺| ≈ |B₁⁻|``.

**Reported, ungated** (the first homogeneity figures this repo has produced, and
labelled as such): centre ``|B₁⁺|/|B₁⁻|`` in each sense, mean ``|B₁⁺|`` at 1 V
per port, and the CV of ``|B₁⁺|_ccw`` over the 51 phantom centroids and over
step 1c's 96-point ring set.  **None of them is asserted** and none is a
homogeneity *claim*: a CV needs a converged mesh and a real drive to mean
anything, and this is a 10 MHz identity fixture.

**Scope.**  10 MHz, F-small, degree 1, superposition only.  No
simultaneous-source solve, no 64/128 MHz (step 2b), no SAR (step 3), no
literature or AED comparison.

Run (complex build required)::

    scripts/testing/run_and_log.sh WF-6-step2 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 400 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_birdcage_b1_quadrature.py -v -s'"
"""

from __future__ import annotations

import numpy as np
import pytest
from dolfinx import fem

from fem_em_solver.post import (
    b1_minus,
    evaluate_vector_field_parallel,
    magnetic_flux_density_from_e,
    project_to_cg1,
)

from tests.complex_mode import complex_only
from tests.validation.test_birdcage_b1_plus_map import (  # noqa: F401 — fixtures
    C4_COVARIANCE_BAND,
    CG1_RECORD_RTOL,
    RECORD_RTOL,
    STEP1B_CG1_RECORDS,
    STEP1_GATE_I_P1_RESIDUAL,
    TERMINATED_PORT_IMPEDANCE_OHM,
    _relative_l2,
    _ring_points,
    _rotate_z,
    b1_plus_map,
    cg1_estimator_table,
)

# The port ordering the phase pattern is built on is *read off the fixture*: a
# port's index is its azimuth relative to P1 divided by the fixture's own
# P1→P2 separation.  The legs need not sit on the coordinate axes and this
# module never assumes they do.
QUADRATURE_STEP_DEG = 90.0

# The mis-paired control must miss the covariance band.  Asserted as a lower
# bound only — the size of the miss is a property of the coil's polarisation
# purity, not something this step pre-registers (step 1d's 23.26% control is
# the precedent for the shape of this assertion).
CONTROL_MIN_MISMATCH = C4_COVARIANCE_BAND

# Reading exactly one point (the magnet isocentre) through the parallel
# evaluator: the centre purity lines below.
CENTRE_POINT = np.zeros((1, 3), dtype=np.float64)


def _port_index(azimuth_deg: float, reference_deg: float, step_deg: float) -> int:
    """``k`` in ``e^{±jkπ/2}`` for a sheet at ``azimuth_deg``.

    Rounded from the measured azimuth, then checked: a fixture whose sheets are
    not on a 90° grid would make the whole superposition meaningless, and the
    check below is what would say so instead of a quiet wrong answer.
    """
    turns = ((azimuth_deg - reference_deg) % 360.0) / step_deg
    k = int(round(turns))
    assert abs(turns - k) < 1.0e-6, (
        f"sheet at {azimuth_deg:.6f} deg is {turns:.6f} quadrature steps from the "
        f"reference {reference_deg:.6f} deg — not on the 90 deg grid a quadrature "
        "phase pattern is defined on"
    )
    return k % 4


def quadrature_phase_weights(port_indices, sense):
    """``e^{∓jkπ/2}`` on the fixture's own azimuth-increasing port index.

    The single source of truth for the phase convention: this module's fixture
    and `WF-6` step 3's SAR module both call it, so the two legs cannot drift
    apart on the one thing that took a run to get right (see the sign-convention
    note in :func:`quadrature_map`).  ``ccw`` is the sense that co-rotates with
    ``B₁⁺``; on an azimuth-*increasing* index that is the pattern which lags.
    """
    ks = np.asarray(port_indices, dtype=float)
    signs = {"ccw": -1.0, "cw": +1.0}
    if sense not in signs:
        raise ValueError(f"sense must be one of {sorted(signs)}, not {sense!r}")
    return np.exp(signs[sense] * 1j * ks * np.pi / 2.0)


def _superpose_dg0(b_fields, coefficients, name):
    """``Σ_k c_k B_k`` as a fresh DG0 vector ``Function`` on the shared space."""
    space = b_fields[0].function_space
    out = fem.Function(space, name=name)
    acc = np.zeros_like(np.asarray(out.x.array))
    for coeff, field in zip(coefficients, b_fields):
        acc += complex(coeff) * np.asarray(field.x.array)
    out.x.array[:] = acc
    out.x.scatter_forward()
    return out


def _mirror_xy(points, azimuth_deg):
    """Reflection in the plane containing z and the ray at ``azimuth_deg``."""
    two_phi = 2.0 * np.radians(azimuth_deg)
    c, s = np.cos(two_phi), np.sin(two_phi)
    out = np.empty_like(points)
    out[:, 0] = c * points[:, 0] + s * points[:, 1]
    out[:, 1] = s * points[:, 0] - c * points[:, 1]
    out[:, 2] = points[:, 2]
    return out


def _read_senses(projected, points):
    """``|B₁⁺|``, ``|B₁⁻|`` and validity at ``points`` from a CG1 vector phasor.

    Both magnitudes come from one point evaluation of the complex vector, after
    the evaluation and never before it.
    """
    values, valid = evaluate_vector_field_parallel(projected, points)
    values = np.asarray(values).reshape(-1, 3)
    transverse_plus = values[:, 0] + 1j * values[:, 1]
    transverse_minus = values[:, 0] - 1j * values[:, 1]
    return (
        np.abs(transverse_plus) / 2.0,
        np.abs(transverse_minus) / 2.0,
        np.asarray(valid, dtype=bool),
    )


def _cv(values):
    """Coefficient of variation, the homogeneity figure — reported, never gated."""
    return float(np.std(values) / np.mean(values))


@pytest.fixture(scope="module")
def quadrature_map(b1_plus_map):
    """The two rotation senses, their CG1 projections, and every reading.

    Four DG0 curls off step 1's four solved fields, two phase-weighted sums, two
    projections, and point reads on three sets: the sample centroids, their 90°
    rotation, and their mirror images in port 1's plane.
    """
    sweep = b1_plus_map["sweep"]
    solves = b1_plus_map["solves"]
    azimuths = b1_plus_map["azimuths"]
    comm = sweep["mesh"].comm
    points = b1_plus_map["points"]

    order = sorted(solves)
    indices = {
        pid: _port_index(azimuths[pid], azimuths["P1"], QUADRATURE_STEP_DEG)
        for pid in order
    }
    assert sorted(indices.values()) == [0, 1, 2, 3], (
        f"the four sheets do not occupy the four quadrature slots: {indices}"
    )

    b_dg0 = {
        pid: magnetic_flux_density_from_e(
            solves[pid]["fields"].e_complex, solves[pid]["omega"]
        )
        for pid in order
    }
    fields = [b_dg0[pid] for pid in order]
    ks = np.array([indices[pid] for pid in order], dtype=float)
    # Sign convention, derived and then confirmed by measurement.  ``k``
    # increases with *increasing* azimuth, and in the ``e^{jωt}`` convention a
    # field rotating in ``+φ`` (the sense ``B₁⁺ = |B_x + jB_y|/2`` reads) is
    # produced by a drive whose phase **lags** with azimuth — i.e. ``e^{−jkπ/2}``
    # on an azimuth-increasing index, not ``e^{+jkπ/2}``.  The first run of this
    # module (`20260831T033416Z_WF-6-step2.log`) took the opposite pairing and
    # measured the consequence: the centre purity read ``|B₁⁺|/|B₁⁻| = 0.0081``
    # for the pattern it called ccw and ``127.91`` for the other, so the gated
    # sense was the near-null one and both identities came back at 18.8% / 20.2%
    # — 10× the CG1 floor, which is what a ~2% discretisation error looks like
    # on a quantity suppressed 120× by cancellation.  The band did not move; the
    # naming did.
    ccw_phases = quadrature_phase_weights(ks, "ccw")
    cw_phases = quadrature_phase_weights(ks, "cw")

    dg0_ccw = _superpose_dg0(fields, ccw_phases, "B_phasor_ccw")
    dg0_cw = _superpose_dg0(fields, cw_phases, "B_phasor_cw")
    cg1 = {
        "ccw": project_to_cg1(dg0_ccw, name="B_phasor_ccw_cg1"),
        "cw": project_to_cg1(dg0_cw, name="B_phasor_cw_cg1"),
    }

    rotated = _rotate_z(points, np.radians(b1_plus_map["delta_deg"]))
    mirrored = _mirror_xy(points, azimuths["P1"])

    reads = {}
    for sense in ("ccw", "cw"):
        for label, pts in (("x", points), ("Rx", rotated), ("Mx", mirrored)):
            plus, minus, valid = _read_senses(cg1[sense], pts)
            reads[(sense, label)] = {"plus": plus, "minus": minus, "valid": valid}
    mask = np.logical_and.reduce([r["valid"] for r in reads.values()])

    identities = {
        "(a) C4 |B1+|_ccw(Rx) vs |B1+|_ccw(x)": _relative_l2(
            reads[("ccw", "Rx")]["plus"], reads[("ccw", "x")]["plus"], mask
        ),
        "(b) mirror |B1-|_cw(Mx) vs |B1+|_ccw(x)": _relative_l2(
            reads[("cw", "Mx")]["minus"], reads[("ccw", "x")]["plus"], mask
        ),
        "control |B1+|_cw(Mx) vs |B1+|_ccw(x)": _relative_l2(
            reads[("cw", "Mx")]["plus"], reads[("ccw", "x")]["plus"], mask
        ),
    }

    # The DG0 partner of the new ``b1_minus`` export, read on the same points:
    # the package function and the after-evaluation magnitude must agree, which
    # is what makes ``b1_minus`` usable by an example (`EX-38`) rather than only
    # by this module's arithmetic.
    dg0_minus_fn = b1_minus(dg0_cw)
    dg0_minus_values, dg0_minus_valid = evaluate_vector_field_parallel(
        dg0_minus_fn, points
    )
    dg0_minus_values = np.real(np.asarray(dg0_minus_values).reshape(-1))
    raw_values, _ = evaluate_vector_field_parallel(dg0_cw, points)
    raw_values = np.asarray(raw_values).reshape(-1, 3)
    dg0_minus_direct = np.abs(raw_values[:, 0] - 1j * raw_values[:, 1]) / 2.0
    export_mask = np.asarray(dg0_minus_valid, dtype=bool) & mask
    export_mismatch = _relative_l2(dg0_minus_values, dg0_minus_direct, export_mask)

    centre = {}
    for sense in ("ccw", "cw"):
        plus, minus, valid = _read_senses(cg1[sense], CENTRE_POINT)
        centre[sense] = {
            "plus": float(plus[0]),
            "minus": float(minus[0]),
            "valid": bool(valid[0]),
        }
    p1_cg1 = project_to_cg1(b_dg0["P1"], name="B_phasor_p1_cg1")
    p1_plus, p1_minus, p1_valid = _read_senses(p1_cg1, CENTRE_POINT)
    centre["P1 single drive"] = {
        "plus": float(p1_plus[0]),
        "minus": float(p1_minus[0]),
        "valid": bool(p1_valid[0]),
    }

    ring = _ring_points()
    ring_plus, _, ring_valid = _read_senses(cg1["ccw"], ring)
    ring_mask = np.asarray(ring_valid, dtype=bool)

    homogeneity = {
        "mean_b1_plus_ccw_t": float(np.mean(reads[("ccw", "x")]["plus"][mask])),
        "cv_centroids": _cv(reads[("ccw", "x")]["plus"][mask]),
        "cv_ring": _cv(ring_plus[ring_mask]) if ring_mask.any() else float("nan"),
        "n_ring_valid": int(ring_mask.sum()),
        "n_ring": int(ring.shape[0]),
    }

    if comm.rank == 0:
        print(
            f"\n[WF-6 step2] quadrature drive by exact superposition, "
            f"{sweep['cells']} cells, f = {sweep['problem'].frequency_hz:.3e} Hz, "
            f"degree 1, CG1 estimator; port slots "
            + ", ".join(f"{pid} k={indices[pid]}" for pid in order)
            + f"; mirror plane at {azimuths['P1']:.3f} deg (port 1's azimuth)\n"
            f"    identities on {int(mask.sum())} of {points.shape[0]} phantom "
            f"centroids (band {C4_COVARIANCE_BAND * 100:.1f}%, imported from "
            "step 1d):",
            flush=True,
        )
        for label, value in identities.items():
            role = "ASSERTED <=" if label.startswith("(") else "control, ASSERTED >"
            print(f"        {label:<44} {value * 100:9.4f}%   {role} band", flush=True)
        print(
            f"    b1_minus export vs after-evaluation magnitude on the DG0 cw "
            f"field: {export_mismatch:.3e} relative l2\n"
            f"    centre polarisation purity |B1+|/|B1-| (reported, ungated):",
            flush=True,
        )
        for label, row in centre.items():
            ratio = row["plus"] / row["minus"] if row["minus"] > 0.0 else float("inf")
            print(
                f"        {label:<18} |B1+| {row['plus']:.6e} T, |B1-| "
                f"{row['minus']:.6e} T, ratio {ratio:10.4f}"
                + ("" if row["valid"] else "   (POINT NOT FOUND)"),
                flush=True,
            )
        print(
            f"    homogeneity (REPORTED, NOT GATED — no converged mesh, no real "
            f"drive): mean |B1+|_ccw = "
            f"{homogeneity['mean_b1_plus_ccw_t']:.6e} T at 1 V per port; CV over "
            f"{int(mask.sum())} centroids = {homogeneity['cv_centroids'] * 100:.4f}%, "
            f"CV over {homogeneity['n_ring_valid']} of {homogeneity['n_ring']} ring "
            f"points = {homogeneity['cv_ring'] * 100:.4f}%",
            flush=True,
        )

    return {
        "sweep": sweep,
        "indices": indices,
        "points": points,
        "mask": mask,
        "n_valid": int(mask.sum()),
        "n_points": int(points.shape[0]),
        "reads": reads,
        "identities": identities,
        "export_mismatch": export_mismatch,
        "centre": centre,
        "homogeneity": homogeneity,
    }


@complex_only
def test_the_four_solves_share_one_operator_so_superposition_is_exact(b1_plus_map):
    """The premise of the whole step, asserted rather than assumed.

    Superposition of the four single-drive fields is exact **only** because the
    operator is the same in all four solves: every port carries the same
    ``Z_p`` in every one of them, and the source amplitude is the same wherever
    it is applied.  If a future fixture change made the ports non-identical this
    test — not a symmetry reading — is what should go red.
    """
    specs = b1_plus_map["sweep"]["specs"]
    impedances = {complex(spec.port_impedance_ohm) for spec in specs}
    assert impedances == {complex(TERMINATED_PORT_IMPEDANCE_OHM)}, (
        f"the four ports do not share one terminal impedance: {impedances}; the "
        "operator then differs between the drives and the superposed field is "
        "not the quadrature field"
    )

    drives = {complex(spec.drive_voltage_v) for spec in specs}
    assert len(drives) == 1, f"the four ports do not share one drive amplitude: {drives}"

    solved = {solve["source_voltage_v"] for solve in b1_plus_map["solves"].values()}
    assert solved == drives, (
        f"the solved drives {solved} are not the fixture's {drives} — the phase "
        "pattern would then be weighting fields of unequal excitation"
    )


@complex_only
def test_quadrature_map_is_c4_invariant(quadrature_map):
    """Identity (a): the quadrature ``|B₁⁺|`` map is unchanged by a 90° rotation.

    Advancing the phase pattern one port is a 90° rotation of the drive and
    multiplies the superposed field by a global phase; a global phase does not
    move a magnitude.  The band is step 1d's CG1 covariance floor, imported.
    """
    assert quadrature_map["n_valid"] == quadrature_map["n_points"], (
        f"only {quadrature_map['n_valid']} of {quadrature_map['n_points']} points "
        "evaluated in every sense on every image set — the rotated and mirrored "
        "images are fresh points and a miss would silently drop them from the l2"
    )

    reading = quadrature_map["identities"]["(a) C4 |B1+|_ccw(Rx) vs |B1+|_ccw(x)"]
    assert reading <= C4_COVARIANCE_BAND, (
        f"the quadrature |B1+| map misses C4 invariance by {reading * 100:.4f}%, "
        f"outside the {C4_COVARIANCE_BAND * 100:.1f}% CG1 floor step 1d measured "
        "on the single drives — a superposition of four fields each inside the "
        "floor should be inside it, so this is a finding about the superposition "
        "path, not a band to widen"
    )


@complex_only
def test_reversing_the_rotation_sense_equals_reflecting(quadrature_map):
    """Identity (b): ``|B₁⁻|_cw(Mx) = |B₁⁺|_ccw(x)``, ``M`` through port 1.

    ``B`` is a pseudovector, so a reflection in a plane containing z sends
    ``B → −MB`` and exchanges the two rotation senses; the mirror maps the port
    set to itself with 2 and 4 swapped, which is exactly what turns the ccw
    phase pattern into the cw one.  Same imported floor as (a).
    """
    reading = quadrature_map["identities"]["(b) mirror |B1-|_cw(Mx) vs |B1+|_ccw(x)"]
    assert reading <= C4_COVARIANCE_BAND, (
        f"the mirror identity misses by {reading * 100:.4f}%, outside the "
        f"{C4_COVARIANCE_BAND * 100:.1f}% floor — either the superposition or the "
        "pseudovector/mirror-plane reading is wrong; record both readings, do "
        "not widen"
    )


@complex_only
def test_the_mispaired_comparison_misses_the_band(quadrature_map):
    """Negative control: the wrong pairing must **not** pass identity (b).

    ``|B₁⁺|_cw(Mx)`` is ``|B₁⁻|_ccw(x)`` in disguise — the sense the coil is
    driving *against*.  If it also landed inside 5% the two senses would be
    indistinguishable and (b) would be measuring nothing.
    """
    control = quadrature_map["identities"]["control |B1+|_cw(Mx) vs |B1+|_ccw(x)"]
    assert control > CONTROL_MIN_MISMATCH, (
        f"the mis-paired comparison reads {control * 100:.4f}%, inside the "
        f"{CONTROL_MIN_MISMATCH * 100:.1f}% band — the two rotation senses are "
        "not being told apart, so identity (b) is passing on a degeneracy"
    )


@complex_only
def test_b1_minus_export_agrees_with_the_evaluated_magnitude(quadrature_map):
    """The new :func:`~fem_em_solver.post.b1_minus` reads what the arithmetic does.

    Cheap, and the only test the new export has: a DG0 scalar field of
    ``|B_x − jB_y|/2`` evaluated at the sample points must match the same
    magnitude formed from the evaluated DG0 vector, to solver noise.
    """
    mismatch = quadrature_map["export_mismatch"]
    assert mismatch <= 1.0e-12, (
        f"post.b1_minus and the after-evaluation |B_x - jB_y|/2 differ by "
        f"{mismatch:.3e} relative l2 on the same DG0 field — they are the same "
        "arithmetic and must agree to round-off"
    )


@complex_only
def test_step_1_records_reproduce_under_the_quadrature_leg(
    quadrature_map, cg1_estimator_table, b1_plus_map
):
    """Anchor (c): this leg is reading the field steps 1/1d recorded.

    Gate (i)'s power residual at rtol 1e-4 and step 1d's three CG1 covariance
    readings at rtol 1e-3 — the looser rtol is step 1d's own, for figures read
    through a Krylov solve.  Neither is a new claim.
    """
    p1 = b1_plus_map["shares"]["P1"]
    total = p1["phantom"] + p1["conductor"] + p1["sheet_total"]
    residual = abs(p1["supplied"] - total) / abs(p1["supplied"])
    assert residual == pytest.approx(STEP1_GATE_I_P1_RESIDUAL, rel=RECORD_RTOL), (
        f"gate (i)'s P1 residual reads {residual:.9e}, not step 1's "
        f"{STEP1_GATE_I_P1_RESIDUAL:.6e} — the quadrature leg is not on step 1's "
        "fixture"
    )

    for label, record in STEP1B_CG1_RECORDS.items():
        measured = cg1_estimator_table["table"][label]["cg1"]
        assert measured == pytest.approx(record, rel=CG1_RECORD_RTOL), (
            f"step 1d's CG1 covariance record {label} reads {measured * 100:.4f}%, "
            f"not {record * 100:.4f}%"
        )
