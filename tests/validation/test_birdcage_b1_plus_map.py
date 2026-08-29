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
