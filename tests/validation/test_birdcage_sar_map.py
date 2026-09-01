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

**Step 3b — the estimator column (2026-08-31 18:00 review's scoping).**  Step 3
measured every identity above missing by 25–40%, with both controls holding and
the power record reproducing to every digit; the diagnosis it recorded is the
*estimator*, not the code — SAR is read pointwise off the primal N1curl ``E``,
whose per-cell O(h) discontinuity the C4 rotation does not share, squared.  Step
1b/1d settled the same question for ``|B₁⁺|`` by L²-projecting to CG1, so this
step reads the same five identities off ``post.project_to_cg1(e_complex)``
beside the primal column, on the same solves, points, band and phase convention.

* The **primal column is now asserted against step 3's own readings**
  (:data:`STEP3_PRIMAL_IDENTITY_RECORDS`, :data:`STEP3_PRIMAL_CONTROL_RECORDS`,
  provenance in their docstrings) — the "nothing moved" anchor.  The five
  primal identity asserts above stay exactly as written, and red.
* The **CG1 column's two controls are asserted to still miss the band**: a
  projection that smoothed the wrong drive and the wrong rotation into 5% would
  buy the identities nothing.
* The **five CG1 identity readings are printed and journalled, never gated**,
  beside a pre-registered verdict — **(a)** all five inside the band with both
  CG1 controls surviving ⇒ the pointwise-``E`` estimator floor, and
  re-registering the SAR gate on CG1 is the *next review's* ruling exactly as 1d
  did for ``|B₁⁺|``; **(b)** the 180° identity inside but a ±90° one outside ⇒
  something rotation-specific in the field (sheet or mesh asymmetry), a review
  reads it; **(c)** all five outside ⇒ this fixture's ~1 cm phantom cells do not
  resolve a quadratic-in-``E`` map at this band, and a finer rung is the weekly
  review's question.  Whichever prints **is** the deliverable; no band moves
  in-slot under any of them.
* **Reported, ungated:** the CG1 column's phantom power ``½∫σ|E_cg1|²`` beside
  the primal record.  A projection does not conserve power (step 1d's ``B``
  projection moved its mean by 0.38%), so this is a size, not a check.

**Scope.**  10 MHz, F-small, degree 1, symmetry identities plus one
reproduction, and an estimator comparison on one fixture.  **No** SAR10g /
C95.3 averaging (`MAT-4` step 2 + `WF-7`), no mass-averaged claim, no Larmor
SAR (a later step mirrors step 2b's rung pattern), no absolute or safety claim;
`WF-6` stays 🟡 under every verdict.

Run (complex build required)::

    scripts/testing/run_and_log.sh WF-6-step3b "docker compose exec -T fem-em-solver \\
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

from fem_em_solver.post import mean_sar, project_to_cg1
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

# Step 3's five primal identity readings, `20260831T183526Z_WF-6-step3.log`
# (the fixture's identity table, `5 failed, 16 passed` / Status 1 / 96 s), and
# its two control readings from the same table.  Step 3b asserts the primal
# column against these at `CG1_RECORD_RTOL`: the estimator column below is only
# interpretable if the column it is being compared *to* has not moved, so this
# pair of records is the "nothing moved" anchor of the whole step.  They are
# reproductions, not bands — a miss here is a fixture finding (a solve that is
# no longer step 3's), never a licence to re-record.
STEP3_PRIMAL_IDENTITY_RECORDS = {
    "(i) SAR_P2(Rx) vs SAR_P1(x)": 25.1096e-2,
    "(i) SAR_P4(-Rx) vs SAR_P1(x)": 40.5462e-2,
    "(i) SAR_P3(180deg) vs SAR_P1(x)": 30.0142e-2,
    "(ii) SAR_ccw(Rx) vs SAR_ccw(x)": 38.6120e-2,
    "(iii) SAR_cw(Mx) vs SAR_ccw(x)": 28.1459e-2,
}
STEP3_PRIMAL_CONTROL_RECORDS = {
    "mis-rotated SAR_P3(Rx) vs SAR_P1(x)": 129.8187e-2,
    "quadrature SAR_ccw(x) vs single-drive SAR_P1(x)": 334.5786e-2,
}

# The three identities whose verdict clause (b) separates on: the 180° image is
# a *different* rotation of the same problem from the ±90° ones (it maps the
# port set to itself without exchanging the two mirror-related sheets), so a
# field asymmetry the mesh carries can miss on ±90° while 180° holds.
IDENTITY_180_LABEL = "(i) SAR_P3(180deg) vs SAR_P1(x)"
IDENTITY_PM90_LABELS = (
    "(i) SAR_P2(Rx) vs SAR_P1(x)",
    "(i) SAR_P4(-Rx) vs SAR_P1(x)",
)


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


def _split_complex(field, stem):
    """A complex ``Function`` as the (real, imag) pair ``point_sar`` wants.

    On the field's **own** space — the projection returns CG1 vectors, and
    handing ``point_sar`` the complex function twice (a tempting shortcut, since
    it takes ``np.real`` of each argument) would silently drop the imaginary
    part and halve every SAR value in the column.
    """
    space = field.function_space
    values = np.asarray(field.x.array)
    parts = []
    for part, values_part in (("real", np.real(values)), ("imag", np.imag(values))):
        out = fem.Function(space, name=f"{stem}_{part}")
        out.x.array[:] = values_part
        out.x.scatter_forward()
        parts.append(out)
    return tuple(parts)


def _superpose_complex(fields, weights, name):
    """``Σ_k c_k f_k`` as a fresh complex ``Function`` on the shared space.

    Superposing the *projected* fields equals projecting the superposition: the
    L² projection is linear and all four solves share one mass operator, so no
    fifth projection solve is needed for the quadrature senses.
    """
    space = fields[0].function_space
    out = fem.Function(space, name=name)
    acc = np.zeros_like(np.asarray(out.x.array))
    for coeff, field in zip(weights, fields):
        acc += complex(coeff) * np.asarray(field.x.array)
    out.x.array[:] = acc
    out.x.scatter_forward()
    return out


def _phantom_relative_l2_of_projection(projected, e_complex, cell_tags):
    """``‖E_cg1 − E‖_{L²(phantom)} / ‖E‖_{L²(phantom)}``, MPI-reduced.

    Diagnostic only, never asserted.  An L² projection is a *fit*: it does not
    conserve power, but it also cannot be far from the field it fits.  This
    number is what separates "the CG1 column is a coarser but honest estimator"
    from "the projection is not approximating ``E`` at all on this element",
    which the identity readings alone cannot distinguish.  ``assemble_scalar``
    is rank-local, so both integrals are summed across ranks before the ratio.
    """
    import ufl
    from dolfinx.fem import assemble_scalar, form

    msh = e_complex.function_space.mesh
    dx = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)(PHANTOM_CELL_TAG)
    difference = projected - e_complex
    numerator = assemble_scalar(form(ufl.inner(difference, difference) * dx))
    denominator = assemble_scalar(form(ufl.inner(e_complex, e_complex) * dx))
    comm = msh.comm
    numerator = comm.allreduce(complex(numerator), op=MPI.SUM)
    denominator = comm.allreduce(complex(denominator), op=MPI.SUM)
    return float(np.sqrt(abs(numerator) / abs(denominator)))


def _cg1_verdict(identities, controls, band):
    """The (a)/(b)/(c) verdict, pre-registered by the 2026-08-31 18:00 review.

    Evaluated from the readings rather than read off them by eye, so the log
    line the review acts on cannot disagree with the numbers printed above it.
    A reading pattern matching none of the three clauses is reported as such —
    the pre-registration is not stretched to cover it in-slot.
    """
    controls_survive = all(value > band for value in controls.values())
    inside = {label: value <= band for label, value in identities.items()}
    if all(inside.values()) and controls_survive:
        return "(a)", (
            "all five CG1 identities inside the band with both CG1 controls "
            "surviving — the pointwise-E estimator floor, exactly as step 1b "
            "found for the DG0 curl; re-registering the SAR gate on the CG1 "
            "estimator is the NEXT REVIEW's ruling, never in-slot"
        )
    if not any(inside.values()):
        return "(c)", (
            "all five CG1 identities miss — the projection is not the "
            "mechanism, and this fixture's ~1 cm phantom cells do not resolve "
            "a quadratic-in-E map at this band; a finer rung is the weekly "
            "review's question"
        )
    if inside[IDENTITY_180_LABEL] and not all(inside[l] for l in IDENTITY_PM90_LABELS):
        return "(b)", (
            "the 180 deg identity is inside the band and a +-90 deg one is "
            "not — something rotation-specific that the field does not share "
            "(sheet or mesh asymmetry); a review reads it"
        )
    return "(none)", (
        "the reading pattern matches none of the pre-registered clauses "
        f"(controls survive: {controls_survive}; inside: "
        + ", ".join(f"{label}={inside[label]}" for label in identities)
        + ") — reported as-is for the review, not forced into a clause"
    )


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


# --------------------------------------------------------------------------
# Step 3b — the CG1 estimator column, beside the primal one above.
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sar_map_cg1(sar_map, b1_plus_map):
    """The same five identities and two controls, off an L²-projected CG1 ``E``.

    No new curl-curl solve: step 1's four solved fields are projected with
    :func:`~fem_em_solver.post.project_to_cg1` — the production estimator step 1d
    registered — and read at exactly the image sets the primal column above used.
    The quadrature senses superpose the *projected* fields (linear, hence equal
    to projecting the superposition), so the column costs four vector mass solves
    and nothing else.
    """
    sweep = b1_plus_map["sweep"]
    solves = b1_plus_map["solves"]
    azimuths = b1_plus_map["azimuths"]
    points = b1_plus_map["points"]
    comm = sweep["mesh"].comm
    delta = np.radians(b1_plus_map["delta_deg"])
    order = sorted(solves)
    ks = [sar_map["indices"][pid] for pid in order]

    projected = {
        pid: project_to_cg1(solves[pid]["fields"].e_complex, name=f"E_cg1_{pid}")
        for pid in order
    }
    split = {pid: _split_complex(projected[pid], f"E_cg1_{pid}") for pid in order}

    kwargs = dict(sigma=SALINE_SIGMA, rho=PHANTOM_RHO_KG_PER_M3, comm=comm)
    images = {
        "P1@0deg": ("P1", points),
        "P2@+90deg": ("P2", _rotate_z(points, delta)),
        "P4@-90deg": ("P4", _rotate_z(points, -delta)),
        "P3@180deg": ("P3", _rotate_z(points, 2.0 * delta)),
        "P3@+90deg": ("P3", _rotate_z(points, delta)),
    }
    single = {
        label: point_sar(*split[pid], pts, **kwargs)
        for label, (pid, pts) in images.items()
    }

    mirrored = _mirror_xy(points, azimuths["P1"])
    rotated = _rotate_z(points, delta)
    superposed = {
        sense: _split_complex(
            _superpose_complex(
                [projected[pid] for pid in order],
                quadrature_phase_weights(ks, sense),
                name=f"E_cg1_{sense}",
            ),
            f"E_cg1_{sense}",
        )
        for sense in ("ccw", "cw")
    }
    quad = {
        ("ccw", "x"): point_sar(*superposed["ccw"], points, **kwargs),
        ("ccw", "Rx"): point_sar(*superposed["ccw"], rotated, **kwargs),
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

    phantom_power_w = float(
        mean_sar(
            projected["P1"],
            sigma=solves["P1"]["fields"].sigma_field,
            rho=PHANTOM_RHO_KG_PER_M3,
            cell_tags=sweep["cell_tags"],
            comm=comm,
            subdomain_ids=PHANTOM_CELL_TAG,
        )["dissipated_power_w"]
    )
    verdict, verdict_text = _cg1_verdict(identities, controls, C4_COVARIANCE_BAND)
    projection_relative_l2 = _phantom_relative_l2_of_projection(
        projected["P1"], solves["P1"]["fields"].e_complex, sweep["cell_tags"]
    )

    if comm.rank == 0:
        primal_identities = sar_map["identities"]
        primal_controls = sar_map["controls"]
        print(
            f"\n[WF-6 step3b] the same point-SAR identities off an L2-projected "
            f"CG1 E (post.project_to_cg1, step 1d's production estimator) beside "
            f"the primal N1curl column, same {points.shape[0]} points, same four "
            f"solves, band {C4_COVARIANCE_BAND * 100:.1f}% imported and unmoved\n"
            f"        {'':<36} {'primal':>10} {'CG1':>10}",
            flush=True,
        )
        for label in identities:
            print(
                f"        {label:<36} {primal_identities[label] * 100:9.4f}% "
                f"{identities[label] * 100:9.4f}%   primal ASSERTED (red, step 3), "
                "CG1 PRINTED NOT GATED",
                flush=True,
            )
        for label in controls:
            print(
                f"        {label:<36} {primal_controls[label] * 100:9.4f}% "
                f"{controls[label] * 100:9.4f}%   control, both ASSERTED > band",
                flush=True,
            )
        print(
            f"    pre-registered verdict: {verdict} — {verdict_text}\n"
            f"    CG1 phantom power 1/2*int(sigma|E_cg1|^2) = {phantom_power_w:.9e} W "
            f"vs the primal record {STEP1_GATE_I_P1_PHANTOM_POWER_W:.9e} W "
            f"({(phantom_power_w / STEP1_GATE_I_P1_PHANTOM_POWER_W - 1.0) * 100:+.4f}%)"
            " — REPORTED, NOT GATED: an L2 projection does not conserve power\n"
            f"    ||E_cg1 - E||/||E|| over the phantom (P1, diagnostic, NOT GATED) "
            f"= {projection_relative_l2 * 100:.4f}% — a projection that fits E "
            "reads O(h) here; an O(1) reading says the CG1 column is not a "
            "reading of this field at all",
            flush=True,
        )

    return {
        "identities": identities,
        "controls": controls,
        "phantom_power_w": phantom_power_w,
        "projection_relative_l2": projection_relative_l2,
        "verdict": verdict,
        "verdict_text": verdict_text,
    }


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3_PRIMAL_IDENTITY_RECORDS))
def test_the_primal_sar_identities_reproduce_step_3s_readings(sar_map_cg1, sar_map, label):
    """The "nothing moved" anchor: the primal column is still step 3's column.

    Comparing two estimators is only meaningful if the one being compared *to*
    has not moved.  These are reproductions of
    `20260831T183526Z_WF-6-step3.log`'s own table at ``CG1_RECORD_RTOL``, not
    bands: a miss means this leg is not on step 3's solve, and the CG1 column
    beside it says nothing about estimators.
    """
    reading = sar_map["identities"][label]
    record = STEP3_PRIMAL_IDENTITY_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"the primal identity '{label}' reads {reading * 100:.4f}%, not step 3's "
        f"recorded {record * 100:.4f}% (rtol {CG1_RECORD_RTOL:.0e}) — the primal "
        "column has moved, so the CG1 column is not an estimator comparison"
    )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3_PRIMAL_CONTROL_RECORDS))
def test_the_primal_sar_controls_reproduce_step_3s_readings(sar_map_cg1, sar_map, label):
    """The same anchor on the two controls — step 3's 129.8% and 334.6%."""
    reading = sar_map["controls"][label]
    record = STEP3_PRIMAL_CONTROL_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"the primal control '{label}' reads {reading * 100:.4f}%, not step 3's "
        f"recorded {record * 100:.4f}% (rtol {CG1_RECORD_RTOL:.0e}) — same "
        "fixture, same points, same drive, so this is a reproducibility finding"
    )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3_PRIMAL_CONTROL_RECORDS))
def test_the_cg1_negative_controls_still_miss_the_band(sar_map_cg1, label):
    """The projection must not smooth the controls into the band.

    The whole point of the CG1 column is that it may bring the *identities*
    inside 5%.  If it brought the wrong drive and the wrong rotation inside too
    — from primal ceilings of 129.8% and 334.6% — then the projection would have
    erased the azimuthal structure rather than the estimator noise, and a CG1
    identity inside the band would mean nothing at all.  A CG1 control anywhere
    below the band is itself the finding.
    """
    control = sar_map_cg1["controls"][label]
    assert control > CONTROL_MIN_MISMATCH, (
        f"the CG1 control '{label}' reads {control * 100:.4f}%, inside the "
        f"{CONTROL_MIN_MISMATCH * 100:.1f}% band (primal reads "
        f"{STEP3_PRIMAL_CONTROL_RECORDS[label] * 100:.4f}%) — the L2 projection "
        "has smoothed away the structure the identities claim to measure, so no "
        "CG1 identity reading here is interpretable"
    )


# --------------------------------------------------------------------------
# Step 3c — the projector diagnosis: is ``post.project_to_cg1`` a projector on
# N1curl input?  Scoped by the 2026-09-01 03:00 review out of step 3b's finding
# that ``‖E_cg1 − E‖/‖E‖`` over the phantom reads 1876%, which no fit of ``E``
# can do.  Three candidates, separated here: (1) a global L² fit dominated by
# the sheet / conductor-edge ``E`` singularities, (2) a non-converged mass
# solve the helper never checks, (3) an element-side mismatch the value-shape
# ``(3,)`` guard does not catch.  Diagnosis only — no band, no SAR gate, no
# re-registration.
# --------------------------------------------------------------------------

# Step 3b's readings, `20260901T003548Z_WF-6-step3b-diagnostic.log` lines
# 4732–4741 (`5 failed, 25 passed` / Status 1 / 100 s).  Records, not bands:
# the whole diagnosis below is about *this* projection of *this* solve, so a
# miss here means the thing being diagnosed is not the thing step 3b measured.
STEP3B_CG1_IDENTITY_RECORDS = {
    "(i) SAR_P2(Rx) vs SAR_P1(x)": 152.0459e-2,
    "(i) SAR_P4(-Rx) vs SAR_P1(x)": 109.7797e-2,
    "(i) SAR_P3(180deg) vs SAR_P1(x)": 169.5050e-2,
    "(ii) SAR_ccw(Rx) vs SAR_ccw(x)": 53.1869e-2,
    "(iii) SAR_cw(Mx) vs SAR_ccw(x)": 40.8440e-2,
}
STEP3B_CG1_CONTROL_RECORDS = {
    "mis-rotated SAR_P3(Rx) vs SAR_P1(x)": 163.6144e-2,
    "quadrature SAR_ccw(x) vs single-drive SAR_P1(x)": 75.9135e-2,
}
STEP3B_CG1_PHANTOM_POWER_W = 1.990062891e-05
STEP3B_PHANTOM_PROJECTION_RESIDUAL = 1876.1871e-2

# ``a + b × x`` is the exact range of the lowest-order Nédélec (Whitney) edge
# element *and* lies in ``CG1³``, so an L² projection onto ``CG1³`` must return
# it to solver tolerance.  1e-10 is four orders above the mass solve's 1e-12
# ``ksp_rtol`` and far below any residual an element-side mismatch could hide
# under.  The control's control ``x² ê_x`` is in neither space; its residual
# only has to be *visible* (> 1e-3) for the 1e-10 pass to mean something.
PROJECTOR_EXACT_RESIDUAL = 1.0e-10
PROJECTOR_CONTROL_MIN_RESIDUAL = 1.0e-3

# The affine test field, fixed here so the reading is reproducible: neither
# ``a`` nor ``b`` is axis-aligned, so no component of the identity passes by
# a coordinate accident.
PROJECTOR_FIELD_A = (0.3, -0.7, 1.1)
PROJECTOR_FIELD_B = (0.2, 0.5, -0.4)


def _relative_l2_over_measure(projected, reference, dx):
    """``‖projected − reference‖_{L²(dx)} / ‖reference‖_{L²(dx)}``, MPI-reduced.

    The measure is the caller's, so one helper serves the whole mesh, the
    phantom and the phantom core.  ``assemble_scalar`` is rank-local — a rank
    owning no cell of the subdomain returns 0 and would otherwise make the
    ratio a rank-dependent fiction — so both integrals are summed across ranks
    before the division.  ``ufl.inner`` conjugates its second argument, so
    ``inner(d, d)`` is ``|d|²`` and the result is real up to round-off.
    """
    import ufl
    from dolfinx.fem import assemble_scalar, form

    comm = reference.function_space.mesh.comm
    difference = projected - reference
    numerator = comm.allreduce(
        complex(assemble_scalar(form(ufl.inner(difference, difference) * dx))), op=MPI.SUM
    )
    denominator = comm.allreduce(
        complex(assemble_scalar(form(ufl.inner(reference, reference) * dx))), op=MPI.SUM
    )
    return float(np.sqrt(abs(numerator) / abs(denominator)))


def _phantom_core_cells(msh, cell_tags):
    """Owned phantom cells with **no** vertex on the phantom's boundary.

    Selection is by cell→vertex connectivity over the local view *including
    ghosts* — a cell at a partition boundary must be able to see the
    non-phantom cell across the cut, or the core would leak the interface it
    exists to exclude.  Only owned cells are returned (dolfinx integrates over
    owned cells; a ghost in the tag would be counted twice).
    """
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim, 0)
    c2v = msh.topology.connectivity(tdim, 0)
    imap = msh.topology.index_map(tdim)
    n_all = int(imap.size_local + imap.num_ghosts)
    offsets = np.asarray(c2v.offsets)
    per_cell = int(offsets[1] - offsets[0])
    conn = np.asarray(c2v.array)[: n_all * per_cell].reshape(n_all, per_cell)

    is_phantom = np.zeros(n_all, dtype=bool)
    tagged = np.asarray(cell_tags.find(PHANTOM_CELL_TAG), dtype=np.int64)
    is_phantom[tagged[tagged < n_all]] = True

    outside_vertices = np.unique(conn[~is_phantom]) if (~is_phantom).any() else np.zeros(0)
    owned_phantom = tagged[tagged < int(imap.size_local)]
    if owned_phantom.size == 0:
        return np.zeros(0, dtype=np.int32), 0
    rows = conn[owned_phantom]
    touches = np.isin(rows, outside_vertices).any(axis=1)
    core = np.sort(owned_phantom[~touches]).astype(np.int32)
    return core, int(owned_phantom.size)


@pytest.fixture(scope="module")
def projector_diagnosis(b1_plus_map, sar_map_cg1):
    """The three readings that separate the candidates, on step 3b's fixture.

    No new curl-curl solve: three vector mass solves on the same 116 085-cell
    mesh — ``E`` (re-projected with the diagnostics kwarg, so the KSP the helper
    otherwise discards can be read), the affine control, and the control's
    control.
    """
    import ufl
    from dolfinx import mesh as dmesh

    sweep = b1_plus_map["sweep"]
    solves = b1_plus_map["solves"]
    msh = sweep["mesh"]
    comm = msh.comm
    e_complex = solves["P1"]["fields"].e_complex
    n1curl = e_complex.function_space

    # (i) the mass solve on the real E, with its solver exposed.
    e_cg1, e_diag = project_to_cg1(
        e_complex, name="E_cg1_P1_diag", return_diagnostics=True
    )

    # (ii) the exact-reproduction control and its control, both interpolated
    # into the *solve's own* N1curl space (the helper refuses real inputs, so
    # the callables return complex arrays).
    a = np.asarray(PROJECTOR_FIELD_A, dtype=np.complex128)
    b = np.asarray(PROJECTOR_FIELD_B, dtype=np.complex128)

    def affine(x):
        return np.array(
            [
                a[0] + b[1] * x[2] - b[2] * x[1],
                a[1] + b[2] * x[0] - b[0] * x[2],
                a[2] + b[0] * x[1] - b[1] * x[0],
            ],
            dtype=np.complex128,
        )

    def quadratic(x):
        return np.array(
            [x[0] ** 2, np.zeros_like(x[0]), np.zeros_like(x[0])], dtype=np.complex128
        )

    controls = {}
    for label, callable_ in (("a + b x x", affine), ("x^2 e_x", quadratic)):
        stem = "affine" if label.startswith("a") else "quadratic"
        source = fem.Function(n1curl, name=f"f_{stem}_n1curl")
        source.interpolate(callable_)
        source.x.scatter_forward()
        projected, diag = project_to_cg1(
            source, name=f"f_{stem}_cg1", return_diagnostics=True
        )
        controls[label] = {
            "residual": _relative_l2_over_measure(projected, source, ufl.dx(domain=msh)),
            "diagnostics": diag,
        }

    # (iii) the same E residual over three domains.
    core_cells, owned_phantom = _phantom_core_cells(msh, sweep["cell_tags"])
    core_tags = dmesh.meshtags(
        msh,
        msh.topology.dim,
        core_cells,
        np.full(core_cells.size, PHANTOM_CELL_TAG, dtype=np.int32),
    )
    dx_whole = ufl.dx(domain=msh)
    dx_phantom = ufl.Measure("dx", domain=msh, subdomain_data=sweep["cell_tags"])(
        PHANTOM_CELL_TAG
    )
    dx_core = ufl.Measure("dx", domain=msh, subdomain_data=core_tags)(PHANTOM_CELL_TAG)
    residuals = {
        "whole mesh": _relative_l2_over_measure(e_cg1, e_complex, dx_whole),
        "phantom (tag 3)": _relative_l2_over_measure(e_cg1, e_complex, dx_phantom),
        "phantom core": _relative_l2_over_measure(e_cg1, e_complex, dx_core),
    }
    core_count = comm.allreduce(int(core_cells.size), op=MPI.SUM)
    phantom_count = comm.allreduce(int(owned_phantom), op=MPI.SUM)

    if comm.rank == 0:
        print(
            f"\n[WF-6 step3c] is post.project_to_cg1 a projector on N1curl input? "
            f"three readings on step 3b's fixture ({sweep['cells']} cells), no new "
            f"curl-curl solve\n"
            f"    (i)   mass solve on E: converged_reason "
            f"{e_diag['converged_reason']} (ASSERTED > 0; 2 = KSP_CONVERGED_RTOL, "
            f"-3 = DIVERGED_ITS = candidate 2), iterations "
            f"{e_diag['iterations']}, {e_diag['dofs']} CG1 dofs, ksp_rtol "
            f"{e_diag['ksp_rtol']:.0e}",
            flush=True,
        )
        for label, row in controls.items():
            print(
                f"    (ii)  ||P f - f||/||f|| for f = {label:<9} "
                f"{row['residual']:.6e}   (reason {row['diagnostics']['converged_reason']}, "
                f"{row['diagnostics']['iterations']} its)",
                flush=True,
            )
        print(
            f"    (iii) ||E_cg1 - E||/||E|| by domain (PRINTED; the phantom figure "
            f"also asserted against step 3b's record):",
            flush=True,
        )
        for label, value in residuals.items():
            print(f"        {label:<18} {value * 100:12.4f}%", flush=True)
        print(
            f"        phantom core is {core_count} of {phantom_count} owned tag-3 "
            f"cells (no vertex on the phantom boundary)",
            flush=True,
        )

    return {
        "e_diagnostics": e_diag,
        "controls": controls,
        "residuals": residuals,
        "core_count": core_count,
        "phantom_count": phantom_count,
    }


@complex_only
def test_the_cg1_mass_solve_converges(projector_diagnosis):
    """Candidate 2: the mass solve ``project_to_cg1`` builds and throws away.

    ``LinearProblem.solve()`` does not raise on a non-converged KSP, so a
    Jacobi-preconditioned CG that hit PETSc's 10 000-iteration default on a
    116 085-cell vector CG1 space would return a garbage "projection" that
    looks exactly like a good one.  A positive reason rules that out; ``-3``
    (``DIVERGED_ITS``) would confirm it — in which case the finding is recorded
    and the cap is *not* raised in-slot.
    """
    diag = projector_diagnosis["e_diagnostics"]
    assert diag["converged_reason"] > 0, (
        f"the CG1 mass solve for E returned PETSc converged reason "
        f"{diag['converged_reason']} after {diag['iterations']} iterations on "
        f"{diag['dofs']} dofs — a non-converged mass solve is candidate 2 for step "
        "3b's 1876% projection residual; record it, do not raise the iteration cap"
    )


@complex_only
def test_the_projector_reproduces_a_field_both_spaces_contain(projector_diagnosis):
    """Candidate 3: an element-side mismatch the ``(3,)`` value-shape guard misses.

    ``f = a + b × x`` spans the lowest-order Nédélec element exactly and is also
    in ``CG1³``, so ``P f = f`` is an algebraic identity of the L² projection —
    it holds independently of the mesh, the solve and the fixture.  If it fails,
    ``project_to_cg1`` is not computing the projection its docstring claims (a
    wrong element, a mis-assembled right-hand side), and step 3b's CG1 column is
    a reading of nothing.  If it passes, the projector is a projector and step
    3b's 1876% is a statement about ``E``, not about the helper.
    """
    residual = projector_diagnosis["controls"]["a + b x x"]["residual"]
    assert residual <= PROJECTOR_EXACT_RESIDUAL, (
        f"projecting f = a + b x x — which lies in N1curl_1 AND in CG1^3 — leaves a "
        f"relative L2 residual of {residual:.6e}, above {PROJECTOR_EXACT_RESIDUAL:.0e}: "
        "the L2 projection of a field the target space contains must return it, so "
        "post.project_to_cg1 is not the projection it documents"
    )


@complex_only
def test_the_projector_control_field_is_not_reproduced(projector_diagnosis):
    """The control's control: a field neither space contains must leave a residual.

    Without this, a `project_to_cg1` that returned its own argument unchanged —
    or a residual helper that always read zero — would pass the exact-reproduction
    test above and prove nothing.
    """
    residual = projector_diagnosis["controls"]["x^2 e_x"]["residual"]
    assert residual > PROJECTOR_CONTROL_MIN_RESIDUAL, (
        f"the control field x^2 e_x, in neither N1curl_1 nor CG1^3, projects with a "
        f"relative L2 residual of only {residual:.6e} — below "
        f"{PROJECTOR_CONTROL_MIN_RESIDUAL:.0e}, at which the exact-reproduction test "
        "beside it is not measuring anything"
    )


@complex_only
def test_the_phantom_projection_residual_reproduces_step_3bs_reading(projector_diagnosis):
    """The anchor for reading (iii): step 3b's 1876.1871%, re-measured.

    The whole-mesh and phantom-core figures are only interpretable *against* the
    phantom one, so the phantom one is asserted as a record.
    """
    reading = projector_diagnosis["residuals"]["phantom (tag 3)"]
    assert reading == pytest.approx(
        STEP3B_PHANTOM_PROJECTION_RESIDUAL, rel=CG1_RECORD_RTOL
    ), (
        f"||E_cg1 - E||/||E|| over the phantom reads {reading * 100:.4f}%, not step "
        f"3b's {STEP3B_PHANTOM_PROJECTION_RESIDUAL * 100:.4f}% (rtol "
        f"{CG1_RECORD_RTOL:.0e}) — this diagnosis is not on step 3b's projection"
    )


@complex_only
def test_the_phantom_core_is_a_nonempty_subdomain(projector_diagnosis):
    """Structural: the core reading needs cells to be read over.

    A connectivity bug that selected nothing would make the core residual an
    ``inf``/``nan`` rather than a small number, and a reviewer reading "core ≪
    phantom" off an empty domain would draw exactly the wrong conclusion.
    """
    core = projector_diagnosis["core_count"]
    phantom = projector_diagnosis["phantom_count"]
    assert 0 < core < phantom, (
        f"the phantom core holds {core} of {phantom} tag-3 cells — it must be a "
        "proper, non-empty subset for the core residual to be a reading of the "
        "phantom interior"
    )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3B_CG1_IDENTITY_RECORDS))
def test_the_cg1_sar_identities_reproduce_step_3bs_readings(sar_map_cg1, label):
    """The CG1 column reproduces step 3b's, at ``CG1_RECORD_RTOL``.

    Records of a printed column, not gates: the CG1 identities are *not*
    asserted against the 5% band anywhere and no SAR claim follows from them.
    """
    reading = sar_map_cg1["identities"][label]
    record = STEP3B_CG1_IDENTITY_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"the CG1 identity '{label}' reads {reading * 100:.4f}%, not step 3b's "
        f"recorded {record * 100:.4f}% (rtol {CG1_RECORD_RTOL:.0e})"
    )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3B_CG1_CONTROL_RECORDS))
def test_the_cg1_sar_controls_reproduce_step_3bs_readings(sar_map_cg1, label):
    """The same, for the two CG1 controls (163.6144% and 75.9135%)."""
    reading = sar_map_cg1["controls"][label]
    record = STEP3B_CG1_CONTROL_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"the CG1 control '{label}' reads {reading * 100:.4f}%, not step 3b's "
        f"recorded {record * 100:.4f}% (rtol {CG1_RECORD_RTOL:.0e})"
    )


@complex_only
def test_the_cg1_phantom_power_reproduces_step_3bs_reading(sar_map_cg1):
    """Step 3b's ``½∫σ|E_cg1|²`` = 1.990062891e-05 W, re-measured.

    Reported never gated (a projection does not conserve power); asserted here
    only as the reproduction anchor step 3c's readings hang from.
    """
    reading = sar_map_cg1["phantom_power_w"]
    assert reading == pytest.approx(STEP3B_CG1_PHANTOM_POWER_W, rel=CG1_RECORD_RTOL), (
        f"the CG1 phantom power reads {reading:.9e} W, not step 3b's "
        f"{STEP3B_CG1_PHANTOM_POWER_W:.9e} W (rtol {CG1_RECORD_RTOL:.0e})"
    )
