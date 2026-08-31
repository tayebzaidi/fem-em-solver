"""`WF-6` step 3 — coil-driven point-SAR symmetry identities at 10 MHz.

Every SAR figure this repo has gated so far (`MAT-4` step 1, the lossy-sphere
closed form) was read on an **imposed uniform field**.  This module reads
``SAR = σ|E|²/(2ρ)`` from the *coil's own* solved field, on the same loaded
four-leg birdcage fixture, the same mesh and the same four single-drive solves
that steps 1–2 read ``|B₁⁺|`` from — the fixture, the sample set, the band, the
phase convention and the power record are all **imported**, never re-derived
here (`ANS-1`'s rule).

**What is different from the B₁⁺ legs, and why it matters.**  ``|B₁⁺|`` needs
``∇×E`` — a piecewise-constant DG0 curl whose cell-to-cell scatter is the whole
story of step 1b/1d's estimator hunt, settled by projecting to CG1.  SAR needs
no curl at all: ``E`` is the primal N1curl unknown, read through
:func:`~fem_em_solver.post.point_sar`, which evaluates the split
``e_real``/``e_imag`` fields at the sample points and forms ``σ|E|²/(2ρ)``.  So
the CG1 floor story does **not** transfer, and nobody has measured this
estimator's floor: the 5% band below is imported from step 1d as a *ceiling* to
test against, and the ceiling note the 10:30 review pre-registered is that SAR
is quadratic in ``E``, so a symmetric-error argument admits ~2× the B₁⁺ map's
~2.2% covariance floor.  5% is therefore a real bar for this quantity, not a
giveaway.

**The asserted identities**, all symmetry, all against the imported, unmoved
``C4_COVARIANCE_BAND``:

* **(i) C4 covariance of the single-drive SAR map.**  Rotating the drive from
  P1 to P2 rotates the whole problem by the sheets' azimuthal separation, and
  ``|E|`` is invariant in magnitude under that rotation, so ``SAR_P2(Rx) =
  SAR_P1(x)``.  Read at all three of step 1d's angles: ``+90°`` (P2), ``−90°``
  (P4), ``180°`` (P3).
* **(ii) C4 invariance of the quadrature SAR map.**  Advancing the phase
  pattern by one port multiplies the superposed field by a global phase, and a
  global phase does not move ``|E|²``: ``SAR_ccw(Rx) = SAR_ccw(x)``.
* **(iii) The mirror identity.**  ``M`` is the mirror plane through port 1's
  azimuth; it fixes ports 1 and 3, swaps 2 with 4, and turns the ccw phase
  pattern into the cw one.  ``E`` is a *true* vector (unlike ``B``), so
  ``E_cw(Mx) = M E_ccw(x)`` and the magnitude — hence the SAR — is equal:
  ``SAR_cw(Mx) = SAR_ccw(x)``.
* **(iv) A conservation cross-check, not a new band.**
  :func:`~fem_em_solver.post.mean_sar`'s ``dissipated_power_w`` on the P1 drive
  reproduces gate (i)'s phantom share **5.637745667e-08 W** at rtol 1e-3 — the
  same number, to every printed digit, in the step 1d and step 2 logs.  It is
  what ties this module's point map to step 1's gated power accounting: the
  point values and the volume integral are the same ``σ|E|²`` on the same
  solve.

**Negative controls, both asserted to *miss* the band.**  (1) The mis-rotated
single-drive comparison ``SAR_P3(Rx)`` against ``SAR_P1(x)`` — the 180° image
read at the 90° points, step 1d's own control (its ``|B₁⁺|`` analogue reads
23–27%).  (2) The quadrature map against the P1 single-drive map on the same
points: a rotating drive and a linear one do not deposit power in the same
places, and if they read alike then (ii)/(iii) are passing on a degeneracy
rather than on the superposition.

**A deviation from the scoped control set, with the reason.**  The 10:30
review's scoping listed "the mis-paired quadrature sense > 5%" as a control, by
analogy with step 2's ``|B₁⁺|_cw(Mx)`` (95.2%).  That analogy does not carry:
``|B₁⁺|`` and ``|B₁⁻|`` are *different* quantities of one field, so mis-pairing
them compares a driven sense against a nulled one, whereas SAR is a single
magnitude-squared with no ± decomposition — dropping the mirror from (iii)
compares ``SAR_ccw(Mx)`` with ``SAR_ccw(x)``, i.e. asks whether the quadrature
SAR map happens to be mirror-symmetric, which a nearly axisymmetric rotating
drive would satisfy for reasons having nothing to do with the identity.
Asserting it would be asserting a prediction this module expects to be false.
It is therefore **measured and printed, ungated**, beside the two controls that
do separate; the disposition is the review's.

**Recorded, ungated, labelled:** peak, mean and peak-to-mean point SAR at 1 V
per port for the P1 single drive and for the quadrature drive.  None of these
is an absolute claim: no converged mesh, no real drive, no tuning, and a 1 V
excitation is a normalisation and not a scanner.

**Scope.**  10 MHz, F-small, degree 1, symmetry identities plus one
reproduction.  **No** SAR10g / C95.3 averaging (`MAT-4` step 2 + `WF-7`), no
mass-averaged claim, no Larmor SAR (a later step mirrors step 2b's rung
pattern), no absolute or safety claim; `WF-6` stays 🟡.

Run (complex build required)::

    scripts/testing/run_and_log.sh WF-6-step3 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 400 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_birdcage_sar_map.py -v -s'"
"""

from __future__ import annotations

import numpy as np
import pytest
from dolfinx import fem
from mpi4py import MPI

from fem_em_solver.post import mean_sar
from fem_em_solver.post.sar import point_sar

from tests.complex_mode import complex_only
from tests.validation.test_birdcage_b1_plus_map import (  # noqa: F401 — fixtures
    C4_COVARIANCE_BAND,
    CG1_RECORD_RTOL,
    MIN_SAMPLE_POINTS,
    PHANTOM_RHO_KG_PER_M3,
    _relative_l2,
    _rotate_z,
    b1_plus_map,
)
from tests.validation.test_birdcage_b1_quadrature import (
    QUADRATURE_STEP_DEG,
    _mirror_xy,
    _port_index,
    quadrature_phase_weights,
)
from tests.validation.test_lossy_sphere_fullwave import SALINE_SIGMA
from tests.validation.test_port_birdcage_lumped_column import PHANTOM_CELL_TAG

# Gate (i)'s phantom share on the P1 drive, ``½∫σ|E|²`` over tag 3, printed to
# this many digits by both `20260830T170242Z_WF-6-step1d.log` (line 4681) and
# `20260831T033704Z_WF-6-step2.log` — bit-identical across the two runs.  Read
# here at step 1b's looser record rtol because it is a Krylov-solved integral,
# not one of step 1's 1e-4-reproducible terminal scalars.
STEP1_GATE_I_P1_PHANTOM_POWER_W = 5.637745667e-08

# The phantom's conductivity must be *one* number for ``point_sar``, which takes
# a scalar σ.  The premise is asserted (see
# :func:`test_the_phantom_conductivity_is_uniform_and_matches_the_saline_spec`)
# against the fixture's own material spec rather than assumed; a graded phantom
# would make every SAR value here silently wrong by the ratio of two σ.
PHANTOM_SIGMA_RTOL = 1.0e-12

# The controls are asserted as lower bounds only, exactly as step 1d's
# mis-rotated control is: the *size* of a miss is a property of the coil, not
# something this step pre-registers.
CONTROL_MIN_MISMATCH = C4_COVARIANCE_BAND


def _phantom_sigma_range(sweep, sigma_field):
    """Global (min, max, count) of the DG0 σ over tag-3 cells.

    ``cell_tags.find`` and ``x.array`` are rank-local — a rank that owns no
    phantom would otherwise report a happy uniform σ over nothing at all — so
    the extrema and the count are MPI-reduced before anyone looks at them.
    """
    msh = sweep["mesh"]
    comm = msh.comm
    tdim = msh.topology.dim
    owned = int(msh.topology.index_map(tdim).size_local)

    tagged = sweep["cell_tags"].find(PHANTOM_CELL_TAG)
    local_cells = np.asarray(tagged[tagged < owned], dtype=np.int32)
    dofmap = sigma_field.function_space.dofmap
    values = np.real(np.asarray(sigma_field.x.array))
    local = (
        np.concatenate([values[dofmap.cell_dofs(int(c))] for c in local_cells])
        if local_cells.size
        else np.zeros(0, dtype=np.float64)
    )

    lo = comm.allreduce(float(local.min()) if local.size else float("inf"), op=MPI.MIN)
    hi = comm.allreduce(float(local.max()) if local.size else -float("inf"), op=MPI.MAX)
    count = comm.allreduce(int(local.size), op=MPI.SUM)
    return lo, hi, count


def _superpose_split_e(solves, order, weights):
    """``Σ_k c_k E_k`` as a fresh split (real, imag) pair on the shared DG space.

    ``point_sar`` takes the split fields, so the superposition is done on the
    complex combination and split afterwards — the same arithmetic step 2 does
    on the DG0 ``B`` phasor, and exact for the same reason: one operator, four
    right-hand sides (step 2's
    ``test_the_four_solves_share_one_operator_so_superposition_is_exact``).
    """
    space = solves[order[0]]["fields"].e_real.function_space
    acc = np.zeros_like(np.asarray(solves[order[0]]["fields"].e_real.x.array))
    acc = acc.astype(np.complex128)
    for coeff, pid in zip(weights, order):
        fields = solves[pid]["fields"]
        acc += complex(coeff) * (
            np.real(np.asarray(fields.e_real.x.array))
            + 1j * np.real(np.asarray(fields.e_imag.x.array))
        )

    e_real = fem.Function(space, name="E_real_superposed")
    e_imag = fem.Function(space, name="E_imag_superposed")
    e_real.x.array[:] = np.real(acc)
    e_imag.x.array[:] = np.imag(acc)
    e_real.x.scatter_forward()
    e_imag.x.scatter_forward()
    return e_real, e_imag


@pytest.fixture(scope="module")
def sar_map(b1_plus_map):
    """Point-SAR maps for the four single drives and both quadrature senses.

    No new solve: step 1's four solved fields are read again, this time as
    ``E`` rather than as ``∇×E``.  The image sets are step 1d's (the sample
    points rotated by ±90° and 180°) plus step 2's mirror image in port 1's
    plane.
    """
    sweep = b1_plus_map["sweep"]
    solves = b1_plus_map["solves"]
    azimuths = b1_plus_map["azimuths"]
    points = b1_plus_map["points"]
    comm = sweep["mesh"].comm
    delta = np.radians(b1_plus_map["delta_deg"])

    sigma_lo, sigma_hi, sigma_cells = _phantom_sigma_range(
        sweep, solves["P1"]["fields"].sigma_field
    )

    order = sorted(solves)
    indices = {
        pid: _port_index(azimuths[pid], azimuths["P1"], QUADRATURE_STEP_DEG)
        for pid in order
    }
    ks = [indices[pid] for pid in order]

    kwargs = dict(sigma=SALINE_SIGMA, rho=PHANTOM_RHO_KG_PER_M3, comm=comm)
    images = {
        "P1@0deg": ("P1", points),
        "P2@+90deg": ("P2", _rotate_z(points, delta)),
        "P4@-90deg": ("P4", _rotate_z(points, -delta)),
        "P3@180deg": ("P3", _rotate_z(points, 2.0 * delta)),
        "P3@+90deg": ("P3", _rotate_z(points, delta)),
    }
    single = {
        label: point_sar(
            solves[pid]["fields"].e_real, solves[pid]["fields"].e_imag, pts, **kwargs
        )
        for label, (pid, pts) in images.items()
    }

    mirrored = _mirror_xy(points, azimuths["P1"])
    rotated = _rotate_z(points, delta)
    superposed = {
        sense: _superpose_split_e(solves, order, quadrature_phase_weights(ks, sense))
        for sense in ("ccw", "cw")
    }
    quad = {
        ("ccw", "x"): point_sar(*superposed["ccw"], points, **kwargs),
        ("ccw", "Rx"): point_sar(*superposed["ccw"], rotated, **kwargs),
        ("ccw", "Mx"): point_sar(*superposed["ccw"], mirrored, **kwargs),
        ("cw", "Mx"): point_sar(*superposed["cw"], mirrored, **kwargs),
    }

    full = np.ones(points.shape[0], dtype=bool)
    reference = single["P1@0deg"]
    identities = {
        "(i) SAR_P2(Rx) vs SAR_P1(x)": _relative_l2(single["P2@+90deg"], reference, full),
        "(i) SAR_P4(-Rx) vs SAR_P1(x)": _relative_l2(single["P4@-90deg"], reference, full),
        "(i) SAR_P3(180deg) vs SAR_P1(x)": _relative_l2(single["P3@180deg"], reference, full),
        "(ii) SAR_ccw(Rx) vs SAR_ccw(x)": _relative_l2(
            quad[("ccw", "Rx")], quad[("ccw", "x")], full
        ),
        "(iii) SAR_cw(Mx) vs SAR_ccw(x)": _relative_l2(
            quad[("cw", "Mx")], quad[("ccw", "x")], full
        ),
    }
    controls = {
        "mis-rotated SAR_P3(Rx) vs SAR_P1(x)": _relative_l2(
            single["P3@+90deg"], reference, full
        ),
        "quadrature SAR_ccw(x) vs single-drive SAR_P1(x)": _relative_l2(
            quad[("ccw", "x")], reference, full
        ),
    }
    # Ungated, and the docstring says why: the mirror-omitted comparison asks
    # whether the quadrature map is mirror-symmetric, which is not the identity
    # under test and which an axisymmetric rotating drive satisfies for free.
    ungated_comparison = _relative_l2(quad[("ccw", "Mx")], quad[("ccw", "x")], full)

    def stats(values):
        return {
            "peak": float(np.max(values)),
            "mean": float(np.mean(values)),
            "peak_to_mean": float(np.max(values) / np.mean(values)),
        }

    reported = {
        "P1 single drive": stats(reference),
        "quadrature (ccw)": stats(quad[("ccw", "x")]),
    }

    phantom_power_w = float(
        mean_sar(
            solves["P1"]["fields"].e_complex,
            sigma=solves["P1"]["fields"].sigma_field,
            rho=PHANTOM_RHO_KG_PER_M3,
            cell_tags=sweep["cell_tags"],
            comm=comm,
            subdomain_ids=PHANTOM_CELL_TAG,
        )["dissipated_power_w"]
    )

    if comm.rank == 0:
        print(
            f"\n[WF-6 step3] coil-driven point SAR sigma|E|^2/(2 rho) on the "
            f"loaded birdcage, {sweep['cells']} cells, f = "
            f"{sweep['problem'].frequency_hz:.3e} Hz, degree 1, primal N1curl E "
            f"(no curl, no projection)\n"
            f"    phantom sigma over {sigma_cells} tag-3 cells: "
            f"[{sigma_lo:.9e}, {sigma_hi:.9e}] S/m against the fixture's "
            f"{SALINE_SIGMA:.9e}; rho = {PHANTOM_RHO_KG_PER_M3:.1f} kg/m^3; port "
            "slots " + ", ".join(f"{pid} k={indices[pid]}" for pid in order) + "\n"
            f"    identities on {points.shape[0]} phantom centroids (band "
            f"{C4_COVARIANCE_BAND * 100:.1f}%, imported from step 1d; ceiling "
            "note: SAR is quadratic in E, ~2x the 2.2% B1+ floor):",
            flush=True,
        )
        for label, value in identities.items():
            print(
                f"        {label:<36} {value * 100:9.4f}%   ASSERTED <= band",
                flush=True,
            )
        for label, value in controls.items():
            print(
                f"        {label:<36} {value * 100:9.4f}%   control, ASSERTED > band",
                flush=True,
            )
        print(
            f"        {'mirror-omitted SAR_ccw(Mx) vs (x)':<36} "
            f"{ungated_comparison * 100:9.4f}%   REPORTED, NOT GATED (see module "
            "docstring)\n"
            f"    mean_sar phantom dissipated power on P1 = {phantom_power_w:.9e} W "
            f"vs step 1's record {STEP1_GATE_I_P1_PHANTOM_POWER_W:.9e} W "
            f"(rtol {CG1_RECORD_RTOL:.0e})\n"
            f"    point SAR at 1 V per port (REPORTED, NOT GATED — no converged "
            "mesh, no real drive, no mass averaging, not a safety figure):",
            flush=True,
        )
        for label, row in reported.items():
            print(
                f"        {label:<18} peak {row['peak']:.6e} W/kg, mean "
                f"{row['mean']:.6e} W/kg, peak/mean {row['peak_to_mean']:.4f}",
                flush=True,
            )

    return {
        "sweep": sweep,
        "n_points": int(points.shape[0]),
        "sigma_range": (sigma_lo, sigma_hi, sigma_cells),
        "indices": indices,
        "single": single,
        "quadrature": quad,
        "identities": identities,
        "controls": controls,
        "ungated_comparison": ungated_comparison,
        "reported": reported,
        "phantom_power_w": phantom_power_w,
    }


@complex_only
def test_the_phantom_conductivity_is_uniform_and_matches_the_saline_spec(sar_map):
    """The premise ``point_sar``'s scalar σ rests on, asserted not assumed.

    ``point_sar`` multiplies one number by ``|E|²``.  If the phantom were graded
    — or if the tag-3 cells had picked up the background σ = 0 — every SAR value
    in this module would be wrong by that ratio while every *symmetry* identity
    still passed, because a constant factor cancels out of a relative ℓ².  This
    test is the only thing standing between that and a silent wrong answer.
    """
    lo, hi, count = sar_map["sigma_range"]
    assert count > 0, "no tag-3 cells found on any rank — the phantom is not in the mesh"
    assert lo == pytest.approx(SALINE_SIGMA, rel=PHANTOM_SIGMA_RTOL) and hi == pytest.approx(
        SALINE_SIGMA, rel=PHANTOM_SIGMA_RTOL
    ), (
        f"phantom sigma spans [{lo:.9e}, {hi:.9e}] S/m over {count} tag-3 cells, not "
        f"the fixture's uniform {SALINE_SIGMA:.9e} — a scalar sigma is not a faithful "
        "reading of this phantom and point_sar must not be handed one"
    )


@complex_only
def test_the_sample_set_is_a_map_and_not_a_handful_of_cells(sar_map):
    """Structural: the same 51-point set steps 1–2 read, all of it evaluated.

    ``point_sar`` raises rather than returning a zero for a point it cannot
    evaluate, so reaching this assertion at all means every point in every image
    set was found; what is left to check is that there are enough of them for a
    relative ℓ² to be a map reading.
    """
    assert sar_map["n_points"] >= MIN_SAMPLE_POINTS, (
        f"only {sar_map['n_points']} sample points — below step 1's floor of "
        f"{MIN_SAMPLE_POINTS}, at which the identities stop being map readings"
    )
    assert sorted(sar_map["indices"].values()) == [0, 1, 2, 3], (
        f"the four sheets do not occupy the four quadrature slots: {sar_map['indices']}"
    )


@complex_only
@pytest.mark.parametrize(
    "label",
    [
        "(i) SAR_P2(Rx) vs SAR_P1(x)",
        "(i) SAR_P4(-Rx) vs SAR_P1(x)",
        "(i) SAR_P3(180deg) vs SAR_P1(x)",
    ],
)
def test_single_drive_sar_map_is_c4_covariant(sar_map, label):
    """Identity (i) at each of step 1d's three angles.

    Rotating which port is driven rotates the whole problem; ``|E|`` — and so
    ``σ|E|²/(2ρ)`` — is invariant in magnitude under that rotation.  The band is
    step 1d's, imported and unmoved.
    """
    reading = sar_map["identities"][label]
    assert reading <= C4_COVARIANCE_BAND, (
        f"the single-drive SAR map misses C4 covariance at {label} by "
        f"{reading * 100:.4f}%, outside the imported {C4_COVARIANCE_BAND * 100:.1f}% "
        "band — SAR is read off the primal N1curl E with no projection chain, so "
        "this is an estimator finding about the E-field map (record it, do not "
        "widen the band)"
    )


@complex_only
def test_quadrature_sar_map_is_c4_invariant(sar_map):
    """Identity (ii): the quadrature SAR map is unchanged by a 90° rotation.

    Advancing the phase pattern one port multiplies the superposed ``E`` by a
    global phase, which ``|E|²`` does not see.
    """
    reading = sar_map["identities"]["(ii) SAR_ccw(Rx) vs SAR_ccw(x)"]
    assert reading <= C4_COVARIANCE_BAND, (
        f"the quadrature SAR map misses C4 invariance by {reading * 100:.4f}%, "
        f"outside the imported {C4_COVARIANCE_BAND * 100:.1f}% band — four fields "
        "each inside the band should superpose to one inside it, so this is a "
        "finding about the superposition path"
    )


@complex_only
def test_reversing_the_rotation_sense_equals_reflecting_the_sar_map(sar_map):
    """Identity (iii): ``SAR_cw(Mx) = SAR_ccw(x)``, ``M`` through port 1.

    Unlike ``B``, ``E`` is a true vector, so the reflection acts on it without
    the pseudovector sign — and the mirror maps the port set to itself with 2
    and 4 swapped, which is exactly what turns the ccw phase pattern into the cw
    one.  A magnitude is blind to the remaining rotation of the vector.
    """
    reading = sar_map["identities"]["(iii) SAR_cw(Mx) vs SAR_ccw(x)"]
    assert reading <= C4_COVARIANCE_BAND, (
        f"the SAR mirror identity misses by {reading * 100:.4f}%, outside the "
        f"imported {C4_COVARIANCE_BAND * 100:.1f}% band — either the superposition "
        "or the mirror-plane reading is wrong; record both readings, do not widen"
    )


@complex_only
@pytest.mark.parametrize(
    "label",
    [
        "mis-rotated SAR_P3(Rx) vs SAR_P1(x)",
        "quadrature SAR_ccw(x) vs single-drive SAR_P1(x)",
    ],
)
def test_the_negative_controls_miss_the_band(sar_map, label):
    """The two comparisons that must **not** pass, or (i)–(iii) mean nothing.

    A SAR map smooth enough that the wrong drive and the wrong sample rotation
    also land inside 5% is a map with no azimuthal structure left to be
    covariant, and the identities above would then be passing on a degeneracy.
    """
    control = sar_map["controls"][label]
    assert control > CONTROL_MIN_MISMATCH, (
        f"the control '{label}' reads {control * 100:.4f}%, inside the "
        f"{CONTROL_MIN_MISMATCH * 100:.1f}% band — the SAR map is not resolving the "
        "difference the identities claim to be measuring"
    )


@complex_only
def test_mean_sar_reproduces_step_1s_phantom_power_record(sar_map):
    """Identity (iv): the volume integral of the same ``σ|E|²`` is step 1's.

    Not a new band — a cross-check that this module's point map and step 1's
    gated three-way power accounting are reading one solve.  ``dissipated_power_w``
    is ``½∫σ|E|²dV`` over tag 3 and is ρ-independent, so it is comparable to the
    record regardless of the ρ this module passes.
    """
    measured = sar_map["phantom_power_w"]
    assert measured == pytest.approx(
        STEP1_GATE_I_P1_PHANTOM_POWER_W, rel=CG1_RECORD_RTOL
    ), (
        f"the phantom's dissipated power reads {measured:.9e} W, not step 1's "
        f"{STEP1_GATE_I_P1_PHANTOM_POWER_W:.9e} W — this leg is not on step 1's "
        "fixture, and the point-SAR map above is a map of some other solve"
    )
