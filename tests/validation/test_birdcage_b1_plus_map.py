"""`WF-6` step 1 — the first ``|B₁⁺|`` map, on the loaded birdcage at 10 MHz.

Nothing in this repo has ever computed a ``B₁⁺`` — the quantity an MRI transmit
coil is actually judged on.  `PORT-9` closed the four-port network on
`GEO-18`'s gapped, sheeted, phantom-loaded four-leg birdcage (✅ 2026-08-25) and
`PORT-11` carried it to both Larmor frequencies (✅ 2026-08-26), but every one
of those readings is a *terminal* quantity: ``Z``, ``S``, class spreads.  This
module takes the same fixture and the same single-drive solves and reads the
**field inside the phantom**, through
:func:`~fem_em_solver.post.magnetic_flux_density_from_e` (``B = ∇×E/(−jω)``,
Faraday) and :func:`~fem_em_solver.post.b1_plus` (``|B_x + jB_y|/2``, the peak
phasor convention the solver works in).

**The fixture is imported, not rebuilt**: ``build_four_port_sweep`` from
`PORT-9` leg (d)'s module gives the mesh, the four ``f = 0.5`` sheets at
``Z_p = 50 Ω`` and the problem (the `EX-33` reading of `ANS-1` — import the
construction).  The sweep returns readings and not fields, so each drive is
re-solved here exactly as ``run_lumped_sheet_port_case`` solves it, and every
port's terminal current is read back with the package's own
:func:`~fem_em_solver.ports.lumped.sheet_terminal_current`.

**The two gates**, both pre-registered by the 2026-08-29 10:30 review and
neither widened here:

* **(i) a conservation identity** — three-way real-power accounting at each
  drive.  ``½ Re(V_src · Ī)`` supplied at the driven sheet equals the phantom's
  ``½∫σ|E|²`` (tag 3) **+** the conductor's (tag 1) **+**
  ``Σ_i ½|I_i|² Re Z_p,i`` over all four sheets, driven included, inside
  **1%** of the supplied power.  The domain is PEC-walled, so there is nowhere
  else for real power to go.  The band is 1% because the sheet-resistance term
  has never been closed on this fixture; the measured residual is the record
  either way.
* **(ii) a symmetry identity** — C4 covariance of the map.  Rotating the drive
  from P1 to P2 rotates the whole problem by the two sheets' azimuthal
  separation, and ``|B₁⁺|`` is invariant in magnitude under a rotation about z
  (``B_x + jB_y`` picks up ``e^{jα}``), so ``|B₁⁺|`` from the P2 drive at the
  rotated point must equal ``|B₁⁺|`` from the P1 drive at the point.  The
  relative ℓ² mismatch over the sample set is asserted ``≤ 5%`` — a
  *discretisation* band, pre-registered: ``B`` is DG0 on a gmsh mesh that is
  not itself C4-symmetric, so the ceiling is cell-to-cell scatter, not the
  0.5% ``ADJACENT_SPREAD_BAND`` the S-matrix classes meet.

**Negative controls, both in-run.**  (1) Drop the conductor term from (i): the
identity must then miss by more than the 1% band (σ = 800 S/m in the wire
against the phantom's 0.5).  (2) Take (ii) against the **P3** drive, 180° from
P1 rather than 90°: the mismatch must *exceed* 5%, since the opposite port's
map is the 180° image and not the 90° one.

**Scope.**  10 MHz, F-small, single drives, degree 1.  No quadrature drive, no
homogeneity/CV number, no 64/128 MHz, no literature or AED comparison, and **no
SAR claim** — the phantom integral is a power term here, not a SAR map.

Run (complex build required)::

    scripts/testing/run_and_log.sh WF-6-step1 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 400 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_birdcage_b1_plus_map.py -v -s'"
"""

from __future__ import annotations

import time

import dolfinx
import numpy as np
import pytest
import ufl
from dolfinx import fem
from dolfinx.fem.petsc import LinearProblem
from mpi4py import MPI

from fem_em_solver.core import TimeHarmonicSolver
from fem_em_solver.ports.lumped import (
    lumped_port_bilinear_term,
    lumped_port_linear_term,
    sheet_terminal_current,
)
from fem_em_solver.post import (
    b1_plus,
    evaluate_vector_field_parallel,
    magnetic_flux_density_from_e,
    mean_sar,
)

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.validation.test_port_birdcage_four_port import (
    TERMINATED_PORT_IMPEDANCE_OHM,
    build_four_port_sweep,
)
from tests.validation.test_port_birdcage_lumped_column import (
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)

# **Gate (i)**, pre-registered 2026-08-29 (10:30 review): the three-way power
# accounting closes to this fraction of the supplied power.  The `TH-11` family
# reads its complex-power identity at 1e-9, but the sheet-resistance term
# ``½|I|²Re Z_p`` has never been closed on this fixture, so 1% is the honest
# first band and the measured residual is the record either way.
POWER_BALANCE_BAND = 1.0e-2

# **Gate (ii)**, pre-registered the same day: the C4 covariance mismatch of the
# ``|B₁⁺|`` map.  A *discretisation* band — ``B`` is DG0 on a gmsh mesh that is
# not itself C4-symmetric, so a sample point and its 90°-rotated image sit in
# different cells and the ceiling is cell-to-cell scatter.  It is deliberately
# an order of magnitude looser than the 0.5% ``ADJACENT_SPREAD_BAND`` the
# terminal quantities meet, and is never to be widened in-slot.
C4_COVARIANCE_BAND = 5.0e-2

# The sample set for (ii): tag-3 cell centroids inside this cylinder, so that a
# point's 90°-rotated image is still well inside the phantom (radius 0.03 m,
# half-height 0.04 m) rather than on its curved boundary.
SAMPLE_RADIUS_M = 0.02
SAMPLE_HALF_HEIGHT_M = 0.02

# Deterministic cap on the sample count: the set is sorted and strided, never
# subsampled at random, so the reading reproduces at any rank count.
MAX_SAMPLE_POINTS = 400

# Below this many points evaluated successfully in *every* drive the covariance
# reading is not a map reading at all, and the gate would be passing on a
# handful of cells.
MIN_SAMPLE_POINTS = 50

# ρ for `mean_sar`: it divides out of ``dissipated_power_w`` entirely (that key
# is ``½∫σ|E|²dV``), and this module makes no SAR claim.  Saline.
PHANTOM_RHO_KG_PER_M3 = 1000.0


def _solve_driven(sweep, driven_port_id):
    """One lumped-sheet solve, driven at ``driven_port_id``, keeping the field.

    Exactly the case :func:`~fem_em_solver.ports.lumped.run_lumped_sheet_port_case`
    runs — every port's sheet in the bilinear form, the driven port's sheet also
    carrying the impressed source — inlined only because that function returns
    terminal readings and not the solved phasor.  The per-port currents below
    come from the package's own ``sheet_terminal_current``, already MPI-reduced.
    """
    msh = sweep["mesh"]
    comm = msh.comm
    problem = sweep["problem"]
    tags_f = sweep["facet_tags"]
    specs = sweep["specs"]
    omega = 2.0 * np.pi * float(problem.frequency_hz)

    sheets = [spec.sheet(driven=(spec.port_id == driven_port_id)) for spec in specs]
    driven_sheet = next(s for s in sheets if s.port_id == driven_port_id)

    solver = TimeHarmonicSolver(problem, degree=1)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=None,
        project_source=False,
        extra_bilinear_terms=[
            lambda trial, test, _s=sheet: lumped_port_bilinear_term(
                msh, tags_f, _s, trial, test, omega_rad_per_s=omega
            )
            for sheet in sheets
        ],
        extra_linear_terms=[
            lambda test, _s=driven_sheet: lumped_port_linear_term(
                msh, tags_f, _s, test, omega_rad_per_s=omega
            )
        ],
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    currents = {
        sheet.port_id: sheet_terminal_current(
            msh, tags_f, sheet, fields.e_complex, comm
        )
        for sheet in sheets
    }

    b_phasor = magnetic_flux_density_from_e(fields.e_complex, omega)
    return {
        "driven": driven_port_id,
        "fields": fields,
        "omega": omega,
        "currents": currents,
        "source_voltage_v": complex(driven_sheet.source_voltage_v),
        "b1_plus": b1_plus(b_phasor),
        "solve_time": float(t_solve),
    }


def _power_shares(sweep, solved):
    """The four real-power terms of gate (i), all MPI-reduced before returning."""
    fields = solved["fields"]
    cell_tags = sweep["cell_tags"]
    kwargs = dict(
        sigma=fields.sigma_field,
        rho=PHANTOM_RHO_KG_PER_M3,
        cell_tags=cell_tags,
        comm=sweep["mesh"].comm,
    )
    phantom = float(
        mean_sar(fields.e_complex, subdomain_ids=PHANTOM_CELL_TAG, **kwargs)[
            "dissipated_power_w"
        ]
    )
    conductor = float(
        mean_sar(fields.e_complex, subdomain_ids=CONDUCTOR_CELL_TAG, **kwargs)[
            "dissipated_power_w"
        ]
    )
    # ``Z_p`` is the same 50 Ohm on every sheet by leg (d0)'s finding; each
    # sheet dissipates ½|I|²Re Z_p, the driven one included.
    sheets = {
        pid: 0.5 * abs(i) ** 2 * float(np.real(TERMINATED_PORT_IMPEDANCE_OHM))
        for pid, i in solved["currents"].items()
    }
    supplied = 0.5 * float(
        np.real(solved["source_voltage_v"] * np.conjugate(solved["currents"][solved["driven"]]))
    )
    return {
        "supplied": supplied,
        "phantom": phantom,
        "conductor": conductor,
        "sheets": sheets,
        "sheet_total": float(sum(sheets.values())),
    }


def _sample_points(sweep):
    """Tag-3 cell centroids in the sample cylinder, identical on every rank.

    ``cell_tags.find`` and ``compute_midpoints`` are rank-local; the owned
    centroids are gathered, concatenated, sorted and strided, so the point set
    (and therefore the covariance reading) does not depend on the rank count.
    """
    msh = sweep["mesh"]
    comm = msh.comm
    tdim = msh.topology.dim
    owned = int(msh.topology.index_map(tdim).size_local)

    tagged = sweep["cell_tags"].find(PHANTOM_CELL_TAG)
    local_cells = np.asarray(tagged[tagged < owned], dtype=np.int32)
    mids = (
        dolfinx.mesh.compute_midpoints(msh, tdim, local_cells)
        if local_cells.size
        else np.zeros((0, 3), dtype=np.float64)
    )
    if mids.size:
        radius = np.hypot(mids[:, 0], mids[:, 1])
        keep = (radius <= SAMPLE_RADIUS_M) & (np.abs(mids[:, 2]) <= SAMPLE_HALF_HEIGHT_M)
        mids = mids[keep]

    gathered = comm.allgather(np.ascontiguousarray(mids, dtype=np.float64))
    points = np.concatenate([g for g in gathered if g.size], axis=0) if any(
        g.size for g in gathered
    ) else np.zeros((0, 3), dtype=np.float64)

    order = np.lexsort((points[:, 2], points[:, 1], points[:, 0]))
    points = points[order]
    if points.shape[0] > MAX_SAMPLE_POINTS:
        stride = int(np.ceil(points.shape[0] / MAX_SAMPLE_POINTS))
        points = points[::stride]
    return points


def _rotate_z(points, angle_rad):
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    out = np.empty_like(points)
    out[:, 0] = c * points[:, 0] - s * points[:, 1]
    out[:, 1] = s * points[:, 0] + c * points[:, 1]
    out[:, 2] = points[:, 2]
    return out


def _read_b1_plus(solved, points):
    """``|B₁⁺|`` at ``points`` through the parallel evaluator (never ``f.eval``)."""
    values, valid = evaluate_vector_field_parallel(solved["b1_plus"], points)
    return np.real(np.asarray(values).reshape(-1)), np.asarray(valid, dtype=bool)


@pytest.fixture(scope="module")
def b1_plus_map():
    """One mesh, the gated 4x4, and four single-drive maps (P1…P4).

    P1 and P2 carry gate (ii); P3 is its 180° negative control; P4 is the
    second, ungated instance of the same 90° identity, printed so a review can
    see whether a miss is peculiar to one drive.
    """
    sweep = build_four_port_sweep()
    comm = sweep["mesh"].comm
    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    # The rotation is read off the *fixture's* geometry, not chosen: it is the
    # azimuthal separation of the two sheets whose drives are being compared.
    delta_deg = (azimuths["P2"] - azimuths["P1"]) % 360.0
    solves = {pid: _solve_driven(sweep, pid) for pid in ("P1", "P2", "P3", "P4")}

    points = _sample_points(sweep)
    rotated = _rotate_z(points, np.radians(delta_deg))
    # P4 sits at −90° from P1 and is the *second* instance of the same identity;
    # it is printed and never gated, so that a review can tell a discretisation
    # scatter (both instances alike) from something particular to P2.
    counter_rotated = _rotate_z(points, np.radians(-delta_deg))
    a, valid_a = _read_b1_plus(solves["P1"], points)
    b, valid_b = _read_b1_plus(solves["P2"], rotated)
    c, valid_c = _read_b1_plus(solves["P3"], rotated)
    d, valid_d = _read_b1_plus(solves["P4"], counter_rotated)
    mask = valid_a & valid_b & valid_c & valid_d

    def mismatch(other):
        return float(
            np.linalg.norm(other[mask] - a[mask]) / np.linalg.norm(a[mask])
        ) if mask.sum() else float("inf")

    deviation = (
        np.abs(b[mask] - a[mask]) / np.abs(a[mask])
        if mask.sum()
        else np.array([np.inf])
    )
    shares = {pid: _power_shares(sweep, solves[pid]) for pid in ("P1", "P2")}

    if comm.rank == 0:
        print(
            f"\n[WF-6 step1] |B1+| on the loaded birdcage, {sweep['cells']} cells, "
            f"f = {sweep['problem'].frequency_hz:.3e} Hz, degree 1; sheet azimuths "
            + ", ".join(f"{p} {azimuths[p]:.3f} deg" for p in sorted(azimuths))
            + f"\n    drive rotation P1 -> P2 = {delta_deg:.6f} deg (from the "
            "fixture's own sheet azimuths); solve times "
            + ", ".join(f"{p} {solves[p]['solve_time']:.2f} s" for p in solves),
            flush=True,
        )
        for pid, sh in shares.items():
            total = sh["phantom"] + sh["conductor"] + sh["sheet_total"]
            print(
                f"    [{pid} driven] supplied 1/2 Re(V_src I*) = {sh['supplied']:.9e} W\n"
                f"        phantom  1/2 int sigma|E|^2 (tag 3) = {sh['phantom']:.9e} W "
                f"({sh['phantom'] / sh['supplied'] * 100:.4f}%)\n"
                f"        conductor 1/2 int sigma|E|^2 (tag 1) = {sh['conductor']:.9e} W "
                f"({sh['conductor'] / sh['supplied'] * 100:.4f}%)\n"
                f"        sheets   sum 1/2 |I_i|^2 Re Z_p     = {sh['sheet_total']:.9e} W "
                f"({sh['sheet_total'] / sh['supplied'] * 100:.4f}%)  "
                + ", ".join(f"{p} {v:.6e}" for p, v in sorted(sh["sheets"].items()))
                + f"\n        residual |supplied - sum|/supplied = "
                f"{abs(sh['supplied'] - total) / abs(sh['supplied']):.6e} "
                f"(band {POWER_BALANCE_BAND:.0e}); without the conductor term "
                f"{abs(sh['supplied'] - (total - sh['conductor'])) / abs(sh['supplied']):.6e}",
                flush=True,
            )
        print(
            f"    C4 covariance on {int(mask.sum())} of {points.shape[0]} phantom "
            f"centroids (r <= {SAMPLE_RADIUS_M} m, |z| <= {SAMPLE_HALF_HEIGHT_M} m): "
            f"P2-at-rotated vs P1 = {mismatch(b) * 100:.4f}% "
            f"(band {C4_COVARIANCE_BAND * 100:.1f}%); negative control P3-at-rotated "
            f"vs P1 = {mismatch(c) * 100:.4f}%; second instance P4-at-(-90deg) "
            f"vs P1 = {mismatch(d) * 100:.4f}% (printed, never gated)\n"
            f"    pointwise |B1+| deviation, P2-at-rotated vs P1: median "
            f"{np.median(deviation) * 100:.4f}%, p90 "
            f"{np.percentile(deviation, 90) * 100:.4f}%, max "
            f"{np.max(deviation) * 100:.4f}% — a systematic offset and a "
            "few-cell scatter read differently here\n"
            f"    |B1+| over the sample set: mean {np.mean(a[mask]):.6e} T, max "
            f"{np.max(a[mask]):.6e} T, min {np.min(a[mask]):.6e} T (P1 driven, "
            f"V_src = 1 V)",
            flush=True,
        )

    return {
        "sweep": sweep,
        "solves": solves,
        "shares": shares,
        "azimuths": azimuths,
        "delta_deg": delta_deg,
        "points": points,
        "n_valid": int(mask.sum()),
        "covariance": mismatch(b),
        "opposite": mismatch(c),
        "counter_rotated": mismatch(d),
        "deviation": deviation,
        "b1_plus_p1": a[mask],
    }


@complex_only
def test_the_map_came_off_three_solved_single_drive_fields(b1_plus_map):
    """Structural: four re-solves on the gated fixture, one sample set.

    Not a gate; what the gates need in order to mean anything.  In particular a
    non-trivial ``|B₁⁺|`` is what separates a solved map from an empty array.
    """
    assert set(b1_plus_map["solves"]) == {"P1", "P2", "P3", "P4"}
    assert b1_plus_map["n_valid"] >= MIN_SAMPLE_POINTS, (
        f"only {b1_plus_map['n_valid']} of {b1_plus_map['points'].shape[0]} sample "
        f"points evaluated in all three drives; below {MIN_SAMPLE_POINTS} the "
        "covariance reading is a handful of cells, not a map"
    )
    values = b1_plus_map["b1_plus_p1"]
    assert np.all(np.isfinite(values))
    assert float(np.min(values)) > 0.0, "|B1+| vanishes identically on the sample set"
    assert abs(b1_plus_map["delta_deg"] - 90.0) < 1.0e-6, (
        f"the P1->P2 sheet separation reads {b1_plus_map['delta_deg']:.9f} deg, not "
        "90 deg — this is not the C4 layout the covariance gate assumes"
    )


@complex_only
def test_power_accounting_closes_at_each_single_drive(b1_plus_map):
    """**Gate (i)** — the conservation identity, with its negative control.

    The domain is PEC-walled: real power supplied at the driven sheet has
    nowhere to go but the phantom, the conductor and the four sheets.
    """
    for pid, sh in b1_plus_map["shares"].items():
        supplied = sh["supplied"]
        assert supplied > 0.0, (
            f"[{pid}] the driven sheet supplies {supplied:.9e} W — a passive load "
            "cannot absorb negative real power, so the generator convention or "
            "the terminal current is wrong"
        )
        total = sh["phantom"] + sh["conductor"] + sh["sheet_total"]
        residual = abs(supplied - total) / abs(supplied)
        assert residual <= POWER_BALANCE_BAND, (
            f"[{pid}] power accounting misses by {residual:.6e} of the supplied "
            f"{supplied:.9e} W (phantom {sh['phantom']:.9e}, conductor "
            f"{sh['conductor']:.9e}, sheets {sh['sheet_total']:.9e}); band "
            f"{POWER_BALANCE_BAND:.0e}"
        )

        # Negative control (1): the conductor term is not decorative.
        blind = abs(supplied - (total - sh["conductor"])) / abs(supplied)
        assert blind > POWER_BALANCE_BAND, (
            f"[{pid}] dropping the conductor's 1/2 int sigma|E|^2 still closes to "
            f"{blind:.6e}, inside the {POWER_BALANCE_BAND:.0e} band — the "
            "identity is then insensitive to a term it is supposed to weigh"
        )


@complex_only
def test_b1_plus_map_is_c4_covariant_under_the_drive_rotation(b1_plus_map):
    """**Gate (ii)** — the symmetry identity, with its 180° negative control."""
    mismatch = b1_plus_map["covariance"]
    assert mismatch <= C4_COVARIANCE_BAND, (
        f"|B1+| from the P2 drive at the 90deg-rotated point disagrees with the P1 "
        f"drive by {mismatch * 100:.4f}% in relative l2 over "
        f"{b1_plus_map['n_valid']} phantom centroids, outside the pre-registered "
        f"{C4_COVARIANCE_BAND * 100:.1f}% discretisation band"
    )

    # Negative control (2): the opposite port is the 180 deg image, not the 90.
    opposite = b1_plus_map["opposite"]
    assert opposite > C4_COVARIANCE_BAND, (
        f"the P3 drive (180deg from P1) matches the 90deg-rotated map to "
        f"{opposite * 100:.4f}%, inside the {C4_COVARIANCE_BAND * 100:.1f}% band — "
        "the covariance gate is then not resolving the drive's azimuth at all"
    )


# ---------------------------------------------------------------------------
# `WF-6` step 1b — the estimator leg (scoped 2026-08-29 18:00 review)
# ---------------------------------------------------------------------------
#
# Step 1 left gate (ii) red at 8.6516% against its 5% band with two candidate
# explanations that its own readings cannot separate: **(a)** the band
# underestimated the DG0 cell-scatter floor — the sample set is 51 centroids in
# a 0.02 m-radius × 0.04 m cylinder, i.e. ≈ 1 cm phantom cells on the
# 116 085-cell fixture, and a DG0 curl is piecewise constant over cells that
# size; or **(b)** a real C4 asymmetry in the field.
#
# This leg changes the *estimator* and holds everything else fixed: the same
# fixture, the same four solves, the same 51 points.  ``B_phasor`` is L²-projected
# from DG0 onto ``("Lagrange", 1, (3,))`` through a mass-matrix solve (never
# ``interpolate`` — DG0 → CG1 interpolation is ill-defined at vertices, where
# the value depends on which incident cell the interpolator happens to pick),
# and ``|B₁⁺| = |B_x + jB_y|/2`` is formed from the projected vector at the
# evaluation points.  The three covariance angles are read side by side under
# both estimators, the 180° one for the first time — it is the sharpest
# discriminator available here, because a DG0 scatter floor is the same at 90°
# and at 180°, while a C2-preserving, C4-breaking field asymmetry is not.
#
# **Nothing here moves a band.**  Gate (ii) stays red, the chunk stays 🧪, and
# the verdict bands below are *recorded, not asserted*; only a review may
# re-register gate (ii) on a different estimator, and only with these tables as
# the provenance of the new band.

# Step 1's own records, reproduced here at rtol 1e-4 — the proof that this leg
# reads the same field on the same points as the run that made them.  Logs
# `…183450Z_WF-6-step1.log` (89 s) and `…183728Z_WF-6-step1-diagnostic.log`.
STEP1_DG0_C4_MISMATCH = 8.6516e-2
STEP1_GATE_I_P1_RESIDUAL = 9.795751e-03
RECORD_RTOL = 1.0e-4

# The verdict bands, pre-registered by the 2026-08-29 18:00 review.  Recorded,
# never asserted: (a) CG1 ≤ 5% at all three angles ⇒ estimator floor;
# (b) CG1 ≥ 7% at ±90° with 180° ≤ 5% ⇒ a C4-breaking field asymmetry;
# all three ≥ 7% ⇒ neither, and step 1c's sample set decides.
VERDICT_RESOLVED_BAND = 5.0e-2
VERDICT_ASYMMETRY_BAND = 7.0e-2


def _project_to_cg1(b_dg0):
    """L² projection of the DG0 vector phasor onto ``("Lagrange", 1, (3,))``.

    A mass-matrix solve, not ``interpolate``: a DG0 field has no vertex value,
    so interpolating it into CG1 picks whichever incident cell the interpolation
    machinery visits last, which is neither the average nor reproducible.  The
    mass matrix is Hermitian positive definite in the complex build, so CG with
    Jacobi is the right solver; ``ksp_rtol`` is tightened well below any
    difference this leg is trying to measure.
    """
    msh = b_dg0.function_space.mesh
    space = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    trial, test = ufl.TrialFunction(space), ufl.TestFunction(space)
    problem = LinearProblem(
        ufl.inner(trial, test) * ufl.dx,
        ufl.inner(b_dg0, test) * ufl.dx,
        bcs=[],
        petsc_options={
            "ksp_type": "cg",
            "pc_type": "jacobi",
            "ksp_rtol": 1.0e-12,
            "ksp_atol": 1.0e-30,
        },
        petsc_options_prefix="wf6_step1b_mass_",
    )
    projected = problem.solve()
    projected.x.scatter_forward()
    return projected


def _read_b1_plus_cg1(projected, points):
    """``|B_x + jB_y|/2`` from the projected CG1 vector, at ``points``.

    Formed from the *evaluated* complex vector rather than from a projected
    scalar: ``|·|`` is not linear, so taking the magnitude after the point
    evaluation is the faithful reading of the projected field.
    """
    values, valid = evaluate_vector_field_parallel(projected, points)
    values = np.asarray(values).reshape(-1, 3)
    return np.abs(values[:, 0] + 1j * values[:, 1]) / 2.0, np.asarray(valid, dtype=bool)


def _relative_l2(other, reference, mask):
    return float(
        np.linalg.norm(other[mask] - reference[mask]) / np.linalg.norm(reference[mask])
    )


@pytest.fixture(scope="module")
def cg1_estimator_table(b1_plus_map):
    """The three covariance angles under both estimators, on step 1's points.

    ``+90°`` is P2, ``−90°`` is P4, ``180°`` is P3 — each drive read at the
    correspondingly rotated image of the P1 sample set.  ``P3-at-+90°`` is the
    mis-rotated negative control, and must stay outside the 5% band under
    *both* estimators: a projection that smooths it away has smoothed the map
    away with it.
    """
    solves = b1_plus_map["solves"]
    points = b1_plus_map["points"]
    delta = np.radians(b1_plus_map["delta_deg"])

    images = {
        "P1@0deg": ("P1", points),
        "P2@+90deg": ("P2", _rotate_z(points, delta)),
        "P4@-90deg": ("P4", _rotate_z(points, -delta)),
        "P3@180deg": ("P3", _rotate_z(points, 2.0 * delta)),
        "P3@+90deg": ("P3", _rotate_z(points, delta)),
    }
    projections = {
        pid: _project_to_cg1(
            magnetic_flux_density_from_e(solves[pid]["fields"].e_complex, solves[pid]["omega"])
        )
        for pid in ("P1", "P2", "P3", "P4")
    }

    dg0, cg1, valid = {}, {}, {}
    for label, (pid, pts) in images.items():
        dg0[label], v_dg0 = _read_b1_plus(solves[pid], pts)
        cg1[label], v_cg1 = _read_b1_plus_cg1(projections[pid], pts)
        valid[label] = v_dg0 & v_cg1

    mask = np.logical_and.reduce([valid[label] for label in images])
    reference = "P1@0deg"
    table = {
        label: {
            "dg0": _relative_l2(dg0[label], dg0[reference], mask),
            "cg1": _relative_l2(cg1[label], cg1[reference], mask),
            "dg0_pointwise": np.abs(dg0[label][mask] - dg0[reference][mask])
            / np.abs(dg0[reference][mask]),
            "cg1_pointwise": np.abs(cg1[label][mask] - cg1[reference][mask])
            / np.abs(cg1[reference][mask]),
        }
        for label in images
        if label != reference
    }

    covariance_angles = ("P2@+90deg", "P4@-90deg", "P3@180deg")
    cg1_readings = [table[label]["cg1"] for label in covariance_angles]
    if max(cg1_readings) <= VERDICT_RESOLVED_BAND:
        verdict = (
            "(a) ESTIMATOR FLOOR — CG1 is inside 5% at all three covariance "
            "angles; the DG0 miss was cell scatter and a review may re-register "
            "gate (ii) on the CG1 estimator with this table as its provenance"
        )
    elif (
        min(table[label]["cg1"] for label in ("P2@+90deg", "P4@-90deg"))
        >= VERDICT_ASYMMETRY_BAND
        and table["P3@180deg"]["cg1"] <= VERDICT_RESOLVED_BAND
    ):
        verdict = (
            "(b) FIELD ASYMMETRY — CG1 holds the 180deg identity but not the "
            "90deg ones; C2 survives and C4 does not, so the review commissions "
            "a field-side hunt (per-port sheet current phases, the phantom fit)"
        )
    elif min(cg1_readings) >= VERDICT_ASYMMETRY_BAND:
        verdict = (
            "NEITHER — every CG1 angle is at or above 7%; the map's azimuthal "
            "structure is not resolved at ~1 cm cells and step 1c's sample set "
            "decides"
        )
    else:
        verdict = (
            "UNCLASSIFIED — the readings fall between the pre-registered bands; "
            "recorded as measured, no band is invented in-slot"
        )

    if b1_plus_map["sweep"]["mesh"].comm.rank == 0:
        print(
            f"\n[WF-6 step1b] estimator leg on step 1's own sample set: "
            f"{int(mask.sum())} of {points.shape[0]} phantom centroids, "
            f"{b1_plus_map['sweep']['cells']} cells, degree 1, "
            f"drive rotation {b1_plus_map['delta_deg']:.6f} deg\n"
            f"    reference reproductions: DG0 P2-at-+90deg "
            f"{b1_plus_map['covariance'] * 100:.4f}% vs step 1's "
            f"{STEP1_DG0_C4_MISMATCH * 100:.4f}%; gate (i) P1 residual "
            f"{abs(b1_plus_map['shares']['P1']['supplied'] - (b1_plus_map['shares']['P1']['phantom'] + b1_plus_map['shares']['P1']['conductor'] + b1_plus_map['shares']['P1']['sheet_total'])) / abs(b1_plus_map['shares']['P1']['supplied']):.6e}"
            f" vs step 1's {STEP1_GATE_I_P1_RESIDUAL:.6e}",
            flush=True,
        )
        print(
            "    relative l2 mismatch vs the P1 map, DG0 | CG1 (median, p90 pointwise):",
            flush=True,
        )
        for label in ("P2@+90deg", "P4@-90deg", "P3@180deg", "P3@+90deg"):
            row = table[label]
            role = (
                "mis-rotated control (must stay > 5% under both)"
                if label == "P3@+90deg"
                else "covariance identity"
            )
            print(
                f"        {label:<12} DG0 {row['dg0'] * 100:8.4f}%  "
                f"(med {np.median(row['dg0_pointwise']) * 100:7.4f}%, p90 "
                f"{np.percentile(row['dg0_pointwise'], 90) * 100:7.4f}%)   |   "
                f"CG1 {row['cg1'] * 100:8.4f}%  "
                f"(med {np.median(row['cg1_pointwise']) * 100:7.4f}%, p90 "
                f"{np.percentile(row['cg1_pointwise'], 90) * 100:7.4f}%)   {role}",
                flush=True,
            )
        print(
            f"    |B1+| over the set, P1 driven: DG0 mean "
            f"{np.mean(dg0['P1@0deg'][mask]):.6e} T, CG1 mean "
            f"{np.mean(cg1['P1@0deg'][mask]):.6e} T\n"
            f"    VERDICT (pre-registered, recorded not asserted): {verdict}",
            flush=True,
        )

    return {
        "table": table,
        "mask": mask,
        "n_valid": int(mask.sum()),
        "n_points": int(points.shape[0]),
        "all_valid": bool(np.all(mask)),
        "dg0_p1": dg0["P1@0deg"],
        "cg1_p1": cg1["P1@0deg"],
        "verdict": verdict,
    }


@complex_only
def test_cg1_projection_reads_the_same_field_as_step_1(cg1_estimator_table, b1_plus_map):
    """Anchors (1) and (2): step 1's two records reproduce on this fixture.

    Neither is a new claim — they are the proof that the estimator leg is
    reading the same solved field, on the same points, as the run that recorded
    the 8.6516% miss and the 9.795751e-03 power residual.
    """
    assert cg1_estimator_table["all_valid"], (
        f"only {cg1_estimator_table['n_valid']} of "
        f"{cg1_estimator_table['n_points']} sample points evaluated in every "
        "drive and every rotated image; the set is inside the phantom by "
        "construction, so a false here is a geometry mistake and the l2 would "
        "silently drop points"
    )

    assert b1_plus_map["covariance"] == pytest.approx(
        STEP1_DG0_C4_MISMATCH, rel=RECORD_RTOL
    ), (
        f"the DG0 P2-at-+90deg covariance mismatch reads "
        f"{b1_plus_map['covariance'] * 100:.6f}%, not step 1's "
        f"{STEP1_DG0_C4_MISMATCH * 100:.4f}% — same mesh, same points, so the "
        "estimator leg is not reading the field step 1 recorded"
    )

    p1 = b1_plus_map["shares"]["P1"]
    total = p1["phantom"] + p1["conductor"] + p1["sheet_total"]
    residual = abs(p1["supplied"] - total) / abs(p1["supplied"])
    assert residual == pytest.approx(STEP1_GATE_I_P1_RESIDUAL, rel=RECORD_RTOL), (
        f"gate (i)'s P1 residual reads {residual:.9e}, not step 1's "
        f"{STEP1_GATE_I_P1_RESIDUAL:.6e}"
    )

    for name, values in (("DG0", cg1_estimator_table["dg0_p1"]), ("CG1", cg1_estimator_table["cg1_p1"])):
        masked = values[cg1_estimator_table["mask"]]
        assert np.all(np.isfinite(masked)), f"{name} |B1+| is not finite on the sample set"
        assert float(np.min(masked)) > 0.0, f"{name} |B1+| vanishes identically on the sample set"


@complex_only
def test_the_cg1_estimator_still_resolves_the_drive_azimuth(cg1_estimator_table):
    """Anchor (3), the negative control: the mis-rotated P3 stays outside 5%.

    A CG1 projection that smooths step 1's 27.3% control below the band has
    smoothed the map away, and any comfortable reading at the covariance angles
    would then be the projection's, not the field's.  That is a negative result
    for this leg, not a pass — hence an assert and not a printed row.
    """
    control = cg1_estimator_table["table"]["P3@+90deg"]
    for estimator in ("dg0", "cg1"):
        assert control[estimator] > C4_COVARIANCE_BAND, (
            f"the mis-rotated control (P3 at +90deg, 180deg from P1) matches the "
            f"P1 map to {control[estimator] * 100:.4f}% under the {estimator.upper()} "
            f"estimator, inside the {C4_COVARIANCE_BAND * 100:.1f}% band — that "
            "estimator no longer resolves the drive's azimuth, so its covariance "
            "readings carry no information about the field"
        )


# ---------------------------------------------------------------------------
# `WF-6` step 1c — the sample-set leg (scoped 2026-08-29 18:00 review)
# ---------------------------------------------------------------------------
#
# Independent of step 1b and not reading its result: this leg holds the
# *estimator* fixed at DG0 and changes the **sample set**.  Step 1's 51 points
# are tag-3 cell centroids, and a centroid set is not closed under the C4
# rotation — the 90°-rotated image of a centroid is an arbitrary interior point
# of some other cell.  Under a piecewise-constant estimator that alone can
# manufacture a mismatch, because the two readings are then never the "same
# place in the cell" in any sense.
#
# The set here is closed under the rotation by construction: rings at
# ``r ∈ {0.005, 0.010, 0.015, 0.020}`` m × ``z ∈ {−0.015, 0, +0.015}`` m × 8
# azimuths in 45° steps, 96 points, every point's ±90° and 180° image a member
# of the set.  The azimuth start is jittered by 3.7° so no point lands on a
# cell facet, where the locator's answer is whichever incident cell it finds
# first and therefore rank-dependent.  The rotation angle is the fixture's own
# P1→P2 sheet separation, read from ``b1_plus_map``, not a literal 90°.
#
# **Nothing here moves a band.**  Gate (ii) stays red, the chunk stays 🧪, and
# the ring-set figures are recorded, not asserted, against the centroid set's
# 8.65 / 9.58 / 8.60% — agreement within ±2 pp says the sample set is not the
# mechanism and the floor is the DG0 scatter itself; a per-ring radial pattern
# is a structure the review reads against the coil geometry.

# The ring set.  Every radius is well inside the tag-3 phantom (radius 0.03 m,
# |z| ≤ 0.04 m), so a rotated image is interior too and ``valid`` must be
# all-true — a false is a geometry mistake, not a sampling accident.
RING_RADII_M = (0.005, 0.010, 0.015, 0.020)
RING_HEIGHTS_M = (-0.015, 0.0, 0.015)
RING_AZIMUTH_COUNT = 8
# Jitter, in degrees, of the azimuth start.  45° steps starting at 0 would put
# points on the coordinate planes and — on a mesh built around four sheets at
# multiples of 90° — plausibly on cell facets.
RING_AZIMUTH_JITTER_DEG = 3.7

# Step 1b's 180° reading, for the ±2 pp comparison below.  Recorded, not
# asserted: it came from a different sample set, and this leg exists to see
# whether that matters.  Log `20260830T003238Z_WF-6-step1b.log`.
STEP1B_DG0_180DEG_MISMATCH = 8.5970e-2


def _ring_points():
    """The 96-point rotation-invariant set, identical on every rank.

    Built from constants only — no mesh query, no rank-local array — so the
    set (and the reading on it) is the same at any rank count.
    """
    azimuths = np.radians(
        RING_AZIMUTH_JITTER_DEG
        + 360.0 / RING_AZIMUTH_COUNT * np.arange(RING_AZIMUTH_COUNT)
    )
    points = [
        (r * np.cos(phi), r * np.sin(phi), z)
        for r in RING_RADII_M
        for z in RING_HEIGHTS_M
        for phi in azimuths
    ]
    return np.asarray(points, dtype=np.float64)


@pytest.fixture(scope="module")
def ring_set_table(b1_plus_map):
    """The three covariance angles at DG0 on the rotation-invariant ring set.

    Same four solves as step 1 — only the points change.  ``P3@+90deg`` is the
    mis-rotated negative control and is asserted, not printed.
    """
    solves = b1_plus_map["solves"]
    delta = np.radians(b1_plus_map["delta_deg"])
    points = _ring_points()

    images = {
        "P1@0deg": ("P1", points),
        "P2@+90deg": ("P2", _rotate_z(points, delta)),
        "P4@-90deg": ("P4", _rotate_z(points, -delta)),
        "P3@180deg": ("P3", _rotate_z(points, 2.0 * delta)),
        "P3@+90deg": ("P3", _rotate_z(points, delta)),
    }
    values, valid = {}, {}
    for label, (pid, pts) in images.items():
        values[label], valid[label] = _read_b1_plus(solves[pid], pts)

    mask = np.logical_and.reduce([valid[label] for label in images])
    reference = "P1@0deg"
    table = {
        label: {
            "l2": _relative_l2(values[label], values[reference], mask),
            "pointwise": np.abs(values[label][mask] - values[reference][mask])
            / np.abs(values[reference][mask]),
        }
        for label in images
        if label != reference
    }

    # Per-ring structure: each (r, z) separately, over its 8 azimuths, so a
    # radial pattern in the scatter is on record for the review.
    radii = np.hypot(points[:, 0], points[:, 1])
    per_ring = {}
    for r in RING_RADII_M:
        for z in RING_HEIGHTS_M:
            sel = (np.abs(radii - r) < 1.0e-9) & (np.abs(points[:, 2] - z) < 1.0e-9)
            sel = sel & mask
            if not sel.any():
                continue
            per_ring[(r, z)] = {
                label: _relative_l2(values[label], values[reference], sel)
                for label in ("P2@+90deg", "P4@-90deg", "P3@180deg")
            }

    centroid = {
        "P2@+90deg": b1_plus_map["covariance"],
        "P4@-90deg": b1_plus_map["counter_rotated"],
        "P3@180deg": STEP1B_DG0_180DEG_MISMATCH,
    }

    if b1_plus_map["sweep"]["mesh"].comm.rank == 0:
        print(
            f"\n[WF-6 step1c] sample-set leg, DG0 estimator on a rotation-invariant "
            f"ring set: {int(mask.sum())} of {points.shape[0]} points valid in every "
            f"drive and image; r = {RING_RADII_M} m, z = {RING_HEIGHTS_M} m, "
            f"{RING_AZIMUTH_COUNT} azimuths jittered {RING_AZIMUTH_JITTER_DEG} deg; "
            f"drive rotation {b1_plus_map['delta_deg']:.6f} deg\n"
            f"    reference reproductions: centroid-set DG0 P2-at-+90deg "
            f"{b1_plus_map['covariance'] * 100:.4f}% vs step 1's "
            f"{STEP1_DG0_C4_MISMATCH * 100:.4f}%; gate (i) P1 residual "
            f"{abs(b1_plus_map['shares']['P1']['supplied'] - (b1_plus_map['shares']['P1']['phantom'] + b1_plus_map['shares']['P1']['conductor'] + b1_plus_map['shares']['P1']['sheet_total'])) / abs(b1_plus_map['shares']['P1']['supplied']):.6e}"
            f" vs step 1's {STEP1_GATE_I_P1_RESIDUAL:.6e}",
            flush=True,
        )
        print(
            "    relative l2 mismatch vs the P1 map on the ring set "
            "(centroid-set figure in parentheses, delta in pp):",
            flush=True,
        )
        for label in ("P2@+90deg", "P4@-90deg", "P3@180deg", "P3@+90deg"):
            row = table[label]
            if label in centroid:
                tail = (
                    f"(centroid {centroid[label] * 100:7.4f}%, delta "
                    f"{(row['l2'] - centroid[label]) * 100:+7.4f} pp)   "
                    "covariance identity"
                )
            else:
                tail = "mis-rotated control (must stay > 5%)"
            print(
                f"        {label:<12} {row['l2'] * 100:8.4f}%  "
                f"(med {np.median(row['pointwise']) * 100:7.4f}%, p90 "
                f"{np.percentile(row['pointwise'], 90) * 100:7.4f}%)   {tail}",
                flush=True,
            )
        print("    per ring (r m, z m), relative l2 over the 8 azimuths:", flush=True)
        for (r, z), row in sorted(per_ring.items()):
            print(
                f"        r = {r:.3f}, z = {z:+.3f}:  "
                + "   ".join(
                    f"{label} {row[label] * 100:7.4f}%"
                    for label in ("P2@+90deg", "P4@-90deg", "P3@180deg")
                ),
                flush=True,
            )
        deltas_pp = {
            label: (table[label]["l2"] - centroid[label]) * 100.0 for label in centroid
        }
        within = max(abs(v) for v in deltas_pp.values()) <= 2.0
        print(
            f"    |B1+| over the ring set, P1 driven: mean "
            f"{np.mean(values['P1@0deg'][mask]):.6e} T, max "
            f"{np.max(values['P1@0deg'][mask]):.6e} T, min "
            f"{np.min(values['P1@0deg'][mask]):.6e} T\n"
            f"    VERDICT (pre-registered, recorded not asserted): "
            + (
                "SAMPLE SET IS NOT THE MECHANISM — every angle within +/-2 pp of "
                "the centroid set, so the floor is the DG0 scatter itself"
                if within
                else "SAMPLE-SET SENSITIVE — at least one angle moves more than "
                "2 pp against the centroid set; the review reads the per-ring "
                "rows against the coil geometry"
            )
            + "  (deltas pp: "
            + ", ".join(f"{k} {v:+.4f}" for k, v in sorted(deltas_pp.items()))
            + ")",
            flush=True,
        )

    return {
        "table": table,
        "per_ring": per_ring,
        "points": points,
        "mask": mask,
        "n_valid": int(mask.sum()),
        "all_valid": bool(np.all(mask)),
        "b1_plus_p1": values["P1@0deg"],
    }


@complex_only
def test_the_ring_sample_set_lies_inside_the_phantom(ring_set_table):
    """Anchor (1): every one of the 96 points, and every rotated image, evaluates.

    The set is inside the tag-3 phantom by construction (max radius 0.020 m
    against 0.030, |z| 0.015 against 0.040), and a rotation about z maps it to
    itself, so a `valid` false is a geometry mistake — and it would silently
    drop the point out of the ℓ² rather than fail anything.
    """
    assert ring_set_table["points"].shape[0] == (
        len(RING_RADII_M) * len(RING_HEIGHTS_M) * RING_AZIMUTH_COUNT
    )
    assert ring_set_table["all_valid"], (
        f"only {ring_set_table['n_valid']} of "
        f"{ring_set_table['points'].shape[0]} ring points evaluated in every drive "
        "and every rotated image; the set is interior by construction, so this is "
        "a geometry mistake and the l2 would be reading a subset"
    )
    values = ring_set_table["b1_plus_p1"][ring_set_table["mask"]]
    assert np.all(np.isfinite(values)), "|B1+| is not finite on the ring set"
    assert float(np.min(values)) > 0.0, "|B1+| vanishes identically on the ring set"


@complex_only
def test_the_ring_set_reproduces_step_1s_records(ring_set_table, b1_plus_map):
    """Anchor (2): the fixture this leg reads is still step 1's fixture.

    Neither reading is new — they are the proof that changing the sample set
    changed only the sample set.
    """
    assert b1_plus_map["covariance"] == pytest.approx(
        STEP1_DG0_C4_MISMATCH, rel=RECORD_RTOL
    ), (
        f"the centroid-set DG0 P2-at-+90deg mismatch reads "
        f"{b1_plus_map['covariance'] * 100:.6f}%, not step 1's "
        f"{STEP1_DG0_C4_MISMATCH * 100:.4f}%"
    )

    p1 = b1_plus_map["shares"]["P1"]
    total = p1["phantom"] + p1["conductor"] + p1["sheet_total"]
    residual = abs(p1["supplied"] - total) / abs(p1["supplied"])
    assert residual == pytest.approx(STEP1_GATE_I_P1_RESIDUAL, rel=RECORD_RTOL), (
        f"gate (i)'s P1 residual reads {residual:.9e}, not step 1's "
        f"{STEP1_GATE_I_P1_RESIDUAL:.6e}"
    )


@complex_only
def test_the_ring_set_still_resolves_the_drive_azimuth(ring_set_table):
    """Anchor (3), the negative control: the mis-rotated P3 stays outside 5%.

    A ring set on which the 180°-away drive matches the P1 map inside the band
    is a set that cannot see azimuth at all, and its comfortable covariance
    readings would then say nothing about the field.
    """
    control = ring_set_table["table"]["P3@+90deg"]["l2"]
    assert control > C4_COVARIANCE_BAND, (
        f"on the ring set the mis-rotated control (P3 at +90deg, 180deg from P1) "
        f"matches the P1 map to {control * 100:.4f}%, inside the "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band — the ring set is not resolving the "
        "drive's azimuth, so its covariance readings carry no information"
    )
