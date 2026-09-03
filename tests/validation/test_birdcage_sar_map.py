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

**The identities.**  Steps 3–3e′ asserted (i)–(iii) against the imported,
unmoved ``C4_COVARIANCE_BAND`` and they missed it at 25–41%.  The 2026-09-02
18:00 review (`WF-6` step 3h) ruled the **pointwise** construction the measured
floor rather than the gate: a quadratic in ``E`` read at sample points inherits
the field's pointwise error squared, and the same four solves satisfy the same
C4 statement as **cell integrals** to ≤ 1.52% in
``tests/validation/test_birdcage_sar_integral.py``, which is where the repo's
only coil-driven SAR gate lives.  (i)–(iii) below therefore assert their step-3
*records* at ``CG1_RECORD_RTOL`` **and** that they still exceed the band — the
quantity retired as a gate with its measurement kept, no band widened anywhere.
The two negative controls and (iv) are unchanged and still gated.

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

**Step 3c — the projector diagnosis (2026-09-01 03:00 review's scoping).**  Step
3b's CG1 column read *worse* than the primal one at every identity, with
``‖E_cg1 − E‖/‖E‖`` over the phantom at 1876%, which no fit of ``E`` can do.
Three candidates were separated in one slot: the mass solve converges (reason 2,
26 its), the projector reproduces ``a + b × x`` exactly (1.33e-13), and the
domain table — 32.78% whole mesh, 1876.19% phantom, 838.90% phantom core — names
the remaining one.  A **global** L² fit of this fixture is a fit of the sheet /
conductor-edge ``E`` that dominates ``‖E‖``; the phantom, orders of magnitude
lower in ``|E|``, gets that fit's tail.  Nothing is wrong with
``post.project_to_cg1``; the *use* is.

**Step 3d — the phantom-restricted estimator (2026-09-01 10:30 review's
scoping).**  The honest estimator fits over the region it is read over.  Same
``("Lagrange", 1, (3,))`` space, same CG + Jacobi at ``ksp_rtol`` 1e-12, on the
same parent mesh (no submesh, no cross-mesh interpolation of an N1curl field) —
but with the mass matrix and load integrated over ``dx(3)`` and every CG1 dof
with no phantom-cell support pinned to zero.  Its **asserted anchors** are
properties of the restriction, not of SAR: (i) the best-approximation inequality
``‖P_Ω E − E‖_Ω ≤ ‖P E − E‖_Ω`` = 1876.1871%, which holds by construction and
whose violation is a pinning or measure defect; (ii) ``P_Ω (a + b × x) = a + b ×
x`` to 1e-10 with the pinned dofs exactly zero, its control ``x² ê_x`` above the
arithmetic ``(h/D)² ≳ 1e-4`` floor; (iii) a positive ``converged_reason`` on all
six restricted solves; (iv) every step-3b/3c record reproduced.  The two
restricted controls are asserted to miss the band, exactly as the primal and
global-CG1 ones are.  The **five restricted identity readings and the restricted
phantom power are printed and journalled, never gated**, under step 3b's
pre-registered (a)/(b)/(c) verdict, unchanged.  The cellwise route the step-3c
entry named beside this one is struck by derivation, not run: a degree-1
first-kind N1curl function is ``a + b × x`` on every cell, so a per-cell L²
projection onto ``DG1³`` reproduces the primal ``E`` exactly and *is* the primal
column.

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

from fem_em_solver.post import mean_sar, project_to_cg1, project_to_cg1_restricted
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
    """Identity (i) at each of step 1d's three angles — as a **record**.

    Rotating which port is driven rotates the whole problem; ``|E|`` — and so
    ``σ|E|²/(2ρ)`` — is invariant in magnitude under that rotation.  Read
    *pointwise* off the primal N1curl ``E``, that statement misses the 5% band
    by 25–41%, and six rungs (3b/3c/3d/3e/3e′/3g) measured why: a quadratic in
    ``E`` read at sample points inherits the field's pointwise error squared.

    The 2026-09-02 18:00 review therefore ruled the **pointwise construction
    the measured floor, not the gate**.  The gate on this identity lives in
    ``tests/validation/test_birdcage_sar_integral.py``, where the same four
    solves satisfy it as cell integrals to ≤ 1.52%.  What is asserted here is
    the measurement itself — the reading reproduces step 3's record, *and* still
    exceeds the band, so a future change that silently made the pointwise map
    pass would be visible rather than absorbed.  Nothing was widened: this
    quantity was retired as a gate with its number kept.
    """
    reading = sar_map["identities"][label]
    record = STEP3_PRIMAL_IDENTITY_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"the pointwise single-drive SAR identity {label} reads "
        f"{reading * 100:.4f}%, not step 3's recorded {record * 100:.4f}% (rtol "
        f"{CG1_RECORD_RTOL:.0e}) — the fixture moved under this record; that is "
        "a fixture finding, not a licence to re-record"
    )
    assert reading > C4_COVARIANCE_BAND, (
        f"the pointwise SAR identity {label} now reads {reading * 100:.4f}%, "
        f"INSIDE the {C4_COVARIANCE_BAND * 100:.1f}% band this construction was "
        "measured to miss — the retirement of this quantity as a gate assumed it "
        "misses; re-open the ruling rather than absorbing the change"
    )


@complex_only
def test_quadrature_sar_map_is_c4_invariant(sar_map):
    """Identity (ii): the quadrature SAR map is unchanged by a 90° rotation.

    Advancing the phase pattern one port multiplies the superposed ``E`` by a
    global phase, which ``|E|²`` does not see.  As with identity (i), the
    *pointwise* construction is the measured floor and this test is its record;
    the gate on the quadrature drive is the four-quadrant integral spread in
    ``tests/validation/test_birdcage_sar_integral.py`` (0.4641%).
    """
    label = "(ii) SAR_ccw(Rx) vs SAR_ccw(x)"
    reading = sar_map["identities"][label]
    record = STEP3_PRIMAL_IDENTITY_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"the pointwise quadrature SAR identity reads {reading * 100:.4f}%, not "
        f"step 3's recorded {record * 100:.4f}% (rtol {CG1_RECORD_RTOL:.0e}) — a "
        "fixture finding, not a licence to re-record"
    )
    assert reading > C4_COVARIANCE_BAND, (
        f"the pointwise quadrature SAR identity now reads {reading * 100:.4f}%, "
        f"INSIDE the {C4_COVARIANCE_BAND * 100:.1f}% band this construction was "
        "measured to miss — re-open the ruling rather than absorbing the change"
    )


@complex_only
def test_reversing_the_rotation_sense_equals_reflecting_the_sar_map(sar_map):
    """Identity (iii): ``SAR_cw(Mx) = SAR_ccw(x)``, ``M`` through port 1.

    Unlike ``B``, ``E`` is a true vector, so the reflection acts on it without
    the pseudovector sign — and the mirror maps the port set to itself with 2
    and 4 swapped, which is exactly what turns the ccw phase pattern into the cw
    one.  A magnitude is blind to the remaining rotation of the vector.

    Again a **record**, not a gate: the pointwise construction is the measured
    floor (2026-09-02 18:00 ruling).  Note that no integral counterpart of the
    *mirror* identity exists yet — the C4 gate in
    ``tests/validation/test_birdcage_sar_integral.py`` covers rotations only, so
    the repo makes no gated mirror-symmetry SAR claim of any kind.
    """
    label = "(iii) SAR_cw(Mx) vs SAR_ccw(x)"
    reading = sar_map["identities"][label]
    record = STEP3_PRIMAL_IDENTITY_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"the pointwise SAR mirror identity reads {reading * 100:.4f}%, not step "
        f"3's recorded {record * 100:.4f}% (rtol {CG1_RECORD_RTOL:.0e}) — a "
        "fixture finding, not a licence to re-record"
    )
    assert reading > C4_COVARIANCE_BAND, (
        f"the pointwise SAR mirror identity now reads {reading * 100:.4f}%, "
        f"INSIDE the {C4_COVARIANCE_BAND * 100:.1f}% band this construction was "
        "measured to miss — re-open the ruling rather than absorbing the change"
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


def _affine_field(x):
    """``f = a + b × x`` as a **complex** array — the helper refuses real input.

    Module level so step 3c's whole-mesh reading and step 3d's phantom-restricted
    one are demonstrably the same field, not two transcriptions of it.
    """
    a = np.asarray(PROJECTOR_FIELD_A, dtype=np.complex128)
    b = np.asarray(PROJECTOR_FIELD_B, dtype=np.complex128)
    return np.array(
        [
            a[0] + b[1] * x[2] - b[2] * x[1],
            a[1] + b[2] * x[0] - b[0] * x[2],
            a[2] + b[0] * x[1] - b[1] * x[0],
        ],
        dtype=np.complex128,
    )


def _quadratic_field(x):
    """``x² ê_x`` — in neither ``N1curl₁`` nor ``CG1³``, the control's control."""
    return np.array(
        [x[0] ** 2, np.zeros_like(x[0]), np.zeros_like(x[0])], dtype=np.complex128
    )


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
    controls = {}
    for label, callable_ in (
        ("a + b x x", _affine_field),
        ("x^2 e_x", _quadratic_field),
    ):
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


# --------------------------------------------------------------------------
# Step 3d — the phantom-restricted CG1 ``E`` estimator, beside the primal and
# global-CG1 columns.  Scoped by the 2026-09-01 10:30 review out of step 3c's
# domain table: the projector is a projector (3c refuted the solver and the
# element), but a **global** L² fit of a fixture whose ``‖E‖`` is dominated by
# the sheets and conductor edges is not an ``E`` estimator inside the phantom,
# which reads that fit's tail (whole mesh 32.78% vs phantom 1876.19%, 57×
# apart).  The honest estimator restricts the fit to the region it is read
# over.  Estimator comparison only — no band moves, no SAR gate is registered.
# --------------------------------------------------------------------------

# Step 3c's domain table, `20260901T123421Z_WF-6-step3c.log`.  The phantom
# figure is asserted by
# :func:`test_the_phantom_projection_residual_reproduces_step_3bs_reading`
# above (it is step 3b's record); the other two are step 3c's own and are
# asserted here, because step 3d's anchor (i) is a *comparison* against them
# and a moved domain table would make the comparison meaningless.
STEP3C_PROJECTION_RESIDUAL_RECORDS = {
    "whole mesh": 32.7802e-2,
    "phantom core": 838.8978e-2,
}

# Anchor (ii)'s companion: with every CG1 dof outside the phantom pinned by a
# `dirichletbc` built from a zero `Function`, dolfinx's `set_bc` writes the
# boundary value into the solution vector *after* the solve, so those dofs are
# exactly representable zeros, not small numbers.  Anything above this is a
# defect in the pinning (a complement taken over owned blocks only, say), not
# a numerical tolerance to be widened.
RESTRICTED_PINNED_DOF_MAX = 0.0

# The control's control under the restriction.  ``x² ê_x`` is a quadratic, and
# its best CG1 fit over a region of diameter ``D`` meshed at ``h`` leaves a
# relative residual of order ``(h/D)²``.  This mesh's phantom is ~1 cm cells
# over a ~20 cm phantom, so ``D/h ≲ 100`` and ``(h/D)² ≳ 1e-4``: the floor
# below is arithmetic, not tuned to the reading.  (The *global* figure, over a
# domain that includes the coil, was 9.882703e-02.)
RESTRICTED_CONTROL_MIN_RESIDUAL = 1.0e-4

# The six restricted mass solves anchor (iii) reads a converged reason from:
# the four single drives plus the two projector controls.  The quadrature
# senses are dof-array superpositions of the four (the restricted projection is
# still linear and all six share one operator), so they cost no solve.
RESTRICTED_SOLVE_LABELS = ("P1", "P2", "P3", "P4", "a + b x x", "x^2 e_x")


# ---------------------------------------------------------------------------
# `WF-6` step 3e (2026-09-02): the restricted projector moved into the package
# as ``post.project_to_cg1_restricted`` — verbatim, `return_diagnostics` now
# defaulting off to match ``project_to_cg1``, and this module its first caller
# with ``return_diagnostics=True``.  Every record below is step 3d's, read off
# `20260901T183416Z_WF-6-step3d.log`, and every one of them is asserted through
# the *packaged* path: a code-location change whose only claim is reproduction.
# Nothing here gates SAR — the five primal asserts above stay red and unmoved.
STEP3D_RESTRICTED_PHANTOM_RESIDUAL = 18.7238e-2

# The negative control for the promotion: the *global* ``post.project_to_cg1``
# on the same field over the same phantom reads
# ``STEP3B_PHANTOM_PROJECTION_RESIDUAL`` = 1876.1871%.  Step 3d measured the
# separation at 100.20×; 50× is an order clear of any plausible drift and does
# not buy a marginal red, which asserting 100× would.
STEP3D_RESTRICTION_MIN_SEPARATION = 50.0

# Anchor (iii)'s block census, globally reduced (owned blocks only, summed over
# ranks) so it is rank-count independent, and anchors (iv)'s solver record.
STEP3D_RESTRICTED_FREE_BLOCKS = 170
STEP3D_RESTRICTED_OWNED_BLOCKS = 21397
STEP3D_RESTRICTED_DOFS = 64191
STEP3D_RESTRICTED_CONVERGED_REASON = 2  # KSP_CONVERGED_RTOL
STEP3D_RESTRICTED_ITERATION_RANGE = (21, 25)

STEP3D_RESTRICTED_PHANTOM_POWER_W = 5.440097168e-08

STEP3D_RESTRICTED_IDENTITY_RECORDS = {
    "(i) SAR_P2(Rx) vs SAR_P1(x)": 8.2868e-2,
    "(i) SAR_P4(-Rx) vs SAR_P1(x)": 9.4743e-2,
    "(i) SAR_P3(180deg) vs SAR_P1(x)": 7.3477e-2,
    "(ii) SAR_ccw(Rx) vs SAR_ccw(x)": 6.8146e-2,
    "(iii) SAR_cw(Mx) vs SAR_ccw(x)": 6.1185e-2,
}
STEP3D_RESTRICTED_CONTROL_RECORDS = {
    "mis-rotated SAR_P3(Rx) vs SAR_P1(x)": 123.6255e-2,
    "quadrature SAR_ccw(x) vs single-drive SAR_P1(x)": 333.0778e-2,
}

# The exact-reproduction control and its control, as step 3d measured them
# through the test-local helper.  The *asserted* bounds stay
# ``PROJECTOR_EXACT_RESIDUAL`` (1e-10) and ``RESTRICTED_CONTROL_MIN_RESIDUAL``
# (1e-4); these two are printed beside them so a moved reading is visible.
STEP3D_RESTRICTED_CONTROL_FIELD_RECORDS = {
    "a + b x x": 4.385695e-13,
    "x^2 e_x": 3.741459e-01,
}


@pytest.fixture(scope="module")
def sar_map_restricted(b1_plus_map, sar_map, sar_map_cg1, projector_diagnosis):
    """The five identities and two controls off the phantom-restricted CG1 ``E``.

    No new curl-curl solve and no submesh: six restricted mass solves on the
    parent mesh (four drives, two projector controls), the quadrature senses by
    superposing the projected dof arrays, ``point_sar`` on exactly the 51 points
    the primal and global-CG1 columns used, and the two controls step 3b built.

    Depends on ``projector_diagnosis`` so step 3c's domain table is printed —
    and asserted — above these readings, which are only interpretable against
    it.
    """
    import ufl

    sweep = b1_plus_map["sweep"]
    solves = b1_plus_map["solves"]
    azimuths = b1_plus_map["azimuths"]
    points = b1_plus_map["points"]
    msh = sweep["mesh"]
    comm = msh.comm
    cell_tags = sweep["cell_tags"]
    delta = np.radians(b1_plus_map["delta_deg"])
    order = sorted(solves)
    ks = [sar_map["indices"][pid] for pid in order]

    dx_phantom = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)(
        PHANTOM_CELL_TAG
    )

    diagnostics = {}
    projected = {}
    for pid in order:
        projected[pid], diagnostics[pid] = project_to_cg1_restricted(
            solves[pid]["fields"].e_complex,
            cell_tags,
            name=f"E_cg1_restricted_{pid}",
            tag=PHANTOM_CELL_TAG,
            return_diagnostics=True,
        )
    split = {
        pid: _split_complex(projected[pid], f"E_cg1_restricted_{pid}") for pid in order
    }

    # Anchor (i): the best-approximation inequality.  ``P_Ω`` minimises
    # ``‖· − E‖_Ω`` over all of ``CG1³``, and the *global* projection restricted
    # to the phantom is one member of that set, so the restricted residual
    # cannot exceed step 3b/3c's 1876.1871%.  A violation is a bug in the
    # restriction (the pinning or the measure), never a statement about SAR.
    restricted_residual = _relative_l2_over_measure(
        projected["P1"], solves["P1"]["fields"].e_complex, dx_phantom
    )

    # Anchor (ii): the exact-reproduction control and its control, re-run under
    # the restriction on the solve's own N1curl space.
    n1curl = solves["P1"]["fields"].e_complex.function_space
    control_fields = {}
    for label, callable_ in (
        ("a + b x x", _affine_field),
        ("x^2 e_x", _quadratic_field),
    ):
        stem = "affine" if label.startswith("a") else "quadratic"
        source = fem.Function(n1curl, name=f"f_{stem}_n1curl_restricted")
        source.interpolate(callable_)
        source.x.scatter_forward()
        fitted, diag = project_to_cg1_restricted(
            source,
            cell_tags,
            name=f"f_{stem}_cg1_restricted",
            tag=PHANTOM_CELL_TAG,
            return_diagnostics=True,
        )
        diagnostics[label] = diag
        control_fields[label] = {
            "residual": _relative_l2_over_measure(fitted, source, dx_phantom),
            "diagnostics": diag,
        }

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
                name=f"E_cg1_restricted_{sense}",
            ),
            f"E_cg1_restricted_{sense}",
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
            cell_tags=cell_tags,
            comm=comm,
            subdomain_ids=PHANTOM_CELL_TAG,
        )["dissipated_power_w"]
    )
    verdict, verdict_text = _cg1_verdict(identities, controls, C4_COVARIANCE_BAND)

    if comm.rank == 0:
        primal_identities = sar_map["identities"]
        primal_controls = sar_map["controls"]
        global_identities = sar_map_cg1["identities"]
        global_controls = sar_map_cg1["controls"]
        p1 = diagnostics["P1"]
        print(
            f"\n[WF-6 step3e] the same point-SAR identities off a **phantom-"
            f"restricted** CG1 E, now through the packaged "
            f"post.project_to_cg1_restricted — mass matrix and load integrated over dx(tag "
            f"{PHANTOM_CELL_TAG}) on the parent mesh, every CG1 dof with no "
            f"phantom support pinned to zero — beside the primal N1curl and the "
            f"global-CG1 columns, same {points.shape[0]} points, same four "
            f"solves, band {C4_COVARIANCE_BAND * 100:.1f}% imported and unmoved\n"
            f"    restriction: {p1['free_blocks']} free of "
            f"{p1['free_blocks'] + p1['pinned_blocks']} owned CG1 blocks "
            f"({p1['dofs']} dofs), pinned max |value| {p1['pinned_max_abs']:.3e} "
            f"(ASSERTED == 0)\n"
            f"    (iii) restricted mass solves (ASSERTED converged_reason > 0):",
            flush=True,
        )
        for label in RESTRICTED_SOLVE_LABELS:
            row = diagnostics[label]
            print(
                f"        {label:<12} reason {row['converged_reason']:>3}, "
                f"{row['iterations']:>4} its",
                flush=True,
            )
        print(
            f"    (i) ||P_O E - E||_O/||E||_O restricted = "
            f"{restricted_residual * 100:.4f}% vs the global fit's "
            f"{STEP3B_PHANTOM_PROJECTION_RESIDUAL * 100:.4f}% over the same "
            f"phantom (ASSERTED <=, best-approximation inequality; separation "
            f"{STEP3B_PHANTOM_PROJECTION_RESIDUAL / restricted_residual:.2f}x)",
            flush=True,
        )
        for label, row in control_fields.items():
            print(
                f"    (ii) ||P_O f - f||_O/||f||_O for f = {label:<9} "
                f"{row['residual']:.6e}   (reason "
                f"{row['diagnostics']['converged_reason']}, "
                f"{row['diagnostics']['iterations']} its; step 3d read "
                f"{STEP3D_RESTRICTED_CONTROL_FIELD_RECORDS[label]:.6e})",
                flush=True,
            )
        print(
            f"        {'':<36} {'primal':>10} {'CG1 glob':>10} {'CG1 restr':>10}",
            flush=True,
        )
        for label in identities:
            print(
                f"        {label:<36} {primal_identities[label] * 100:9.4f}% "
                f"{global_identities[label] * 100:9.4f}% "
                f"{identities[label] * 100:9.4f}%   primal ASSERTED (red, step 3), "
                "restricted PRINTED NOT GATED",
                flush=True,
            )
        for label in controls:
            print(
                f"        {label:<36} {primal_controls[label] * 100:9.4f}% "
                f"{global_controls[label] * 100:9.4f}% "
                f"{controls[label] * 100:9.4f}%   control, all three ASSERTED > band",
                flush=True,
            )
        print(
            f"    pre-registered verdict (3b's, unchanged): {verdict} — {verdict_text}\n"
            f"    restricted phantom power 1/2*int(sigma|E_O|^2) = "
            f"{phantom_power_w:.9e} W vs primal "
            f"{STEP1_GATE_I_P1_PHANTOM_POWER_W:.9e} W "
            f"({(phantom_power_w / STEP1_GATE_I_P1_PHANTOM_POWER_W - 1.0) * 100:+.4f}%)"
            f" and global CG1 {STEP3B_CG1_PHANTOM_POWER_W:.9e} W "
            f"({(phantom_power_w / STEP3B_CG1_PHANTOM_POWER_W - 1.0) * 100:+.4f}%)"
            " — REPORTED, NOT GATED: an L2 projection does not conserve power",
            flush=True,
        )

    return {
        "identities": identities,
        "controls": controls,
        "control_fields": control_fields,
        "diagnostics": diagnostics,
        "phantom_power_w": phantom_power_w,
        "projection_relative_l2": restricted_residual,
        # step 3e's negative control: the *measured* global-fit residual over
        # the same phantom, not the constant, so the separation below is a
        # comparison of two readings from the same run.
        "global_projection_relative_l2": projector_diagnosis["residuals"][
            "phantom (tag 3)"
        ],
        "verdict": verdict,
        "verdict_text": verdict_text,
    }


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3C_PROJECTION_RESIDUAL_RECORDS))
def test_the_projection_domain_table_reproduces_step_3cs_readings(
    projector_diagnosis, label
):
    """Anchor (iv) on step 3c's own two figures — 32.7802% and 838.8978%.

    The phantom figure is step 3b's and is asserted above.  These two are what
    made the *use* the diagnosis: step 3d's restricted estimator is a
    comparison against this table, so a moved table would make the comparison
    unreadable.
    """
    reading = projector_diagnosis["residuals"][label]
    record = STEP3C_PROJECTION_RESIDUAL_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"||E_cg1 - E||/||E|| over the {label} reads {reading * 100:.4f}%, not "
        f"step 3c's {record * 100:.4f}% (rtol {CG1_RECORD_RTOL:.0e}) — step 3d's "
        "restricted column is not being compared against step 3c's domain table"
    )


@complex_only
def test_the_restricted_projection_cannot_beat_its_own_best_approximation(
    sar_map_restricted,
):
    """Anchor (i): the best-approximation inequality, a theorem about the code.

    ``P_Ω E`` minimises ``‖· − E‖_{L²(Ω)}`` over all of ``CG1³``.  The *global*
    projection ``P E``, restricted to Ω, is one member of that set and leaves
    step 3b/3c's 1876.1871%.  So ``‖P_Ω E − E‖_Ω ≤ ‖P E − E‖_Ω`` holds by
    construction — no mesh, no fixture and no physics enters.  A violation is a
    defect in the restriction (an unpinned ghost row, the wrong measure, a
    non-converged solve), and must be journalled as that rather than read as a
    statement about SAR or about the phantom.
    """
    reading = sar_map_restricted["projection_relative_l2"]
    assert reading <= STEP3B_PHANTOM_PROJECTION_RESIDUAL, (
        f"the phantom-restricted projection leaves {reading * 100:.4f}% over the "
        f"phantom, ABOVE the global fit's {STEP3B_PHANTOM_PROJECTION_RESIDUAL * 100:.4f}% "
        "on the same domain — the restricted fit minimises that very norm over a "
        "space containing the global fit's restriction, so this is a bug in the "
        "restriction (pinning or measure), not a finding about SAR"
    )


@complex_only
def test_the_restricted_projector_reproduces_a_field_both_spaces_contain(
    sar_map_restricted,
):
    """Anchor (ii): ``P_Ω f = f`` on Ω for ``f = a + b × x``.

    The restriction changes the domain of integration, not the algebra: ``f``
    lies in ``N1curl₁`` and in ``CG1³``, so its restricted L² projection must
    return it over Ω to solver tolerance.  If it does not, the restricted
    operator is not the projection it claims to be — a mis-tagged measure or a
    pin that swallowed a dof the phantom needs — and every reading in the
    restricted column is a reading of nothing.
    """
    residual = sar_map_restricted["control_fields"]["a + b x x"]["residual"]
    assert residual <= PROJECTOR_EXACT_RESIDUAL, (
        f"the phantom-restricted projection of f = a + b x x — in N1curl_1 AND in "
        f"CG1^3 — leaves a relative L2 residual of {residual:.6e} over the phantom, "
        f"above {PROJECTOR_EXACT_RESIDUAL:.0e}: the restricted operator is not the "
        "L2 projection it is built to be"
    )


@complex_only
def test_every_cg1_dof_outside_the_phantom_is_pinned_to_exactly_zero(
    sar_map_restricted,
):
    """Anchor (ii)'s companion: the pin is a pin, on owned **and** ghost blocks.

    If the complement were taken over owned blocks only, the ghost rows of a
    partition cut would keep whatever the Krylov solve left in them, the two-rank
    answer would differ from the one-rank one, and the restricted field would be
    non-zero where the restricted problem does not define it.  ``set_bc`` writes
    an exact zero, so the bound is 0 and not a tolerance.
    """
    pinned_max = sar_map_restricted["diagnostics"]["P1"]["pinned_max_abs"]
    assert pinned_max <= RESTRICTED_PINNED_DOF_MAX, (
        f"a CG1 dof with no phantom-cell support holds {pinned_max:.6e} after the "
        "restricted solve — the zero Dirichlet pin did not reach every block "
        "(check that the complement is taken over size_local + num_ghosts)"
    )


@complex_only
def test_the_restricted_projector_control_field_is_not_reproduced(sar_map_restricted):
    """The control's control under the restriction: ``x² ê_x`` must leave a residual.

    Without it, a restricted "projection" that returned its own argument — or a
    residual helper reading zero over a mis-tagged empty measure — would pass the
    exact-reproduction test above and prove nothing.  The floor is arithmetic:
    a quadratic's CG1 fit error over a region of ``D/h ≲ 100`` cells is of order
    ``(h/D)² ≳ 1e-4``, and no phantom this mesh resolves at ~1 cm cells is finer.
    """
    residual = sar_map_restricted["control_fields"]["x^2 e_x"]["residual"]
    assert residual > RESTRICTED_CONTROL_MIN_RESIDUAL, (
        f"the control field x^2 e_x, in neither N1curl_1 nor CG1^3, restricted-"
        f"projects with a relative L2 residual of only {residual:.6e} over the "
        f"phantom — below the arithmetic floor {RESTRICTED_CONTROL_MIN_RESIDUAL:.0e}, "
        "at which the exact-reproduction test beside it is not measuring anything"
    )


@complex_only
@pytest.mark.parametrize("label", RESTRICTED_SOLVE_LABELS)
def test_every_restricted_mass_solve_converges(sar_map_restricted, label):
    """Anchor (iii): all six restricted mass solves converged.

    The restricted matrix is the phantom mass matrix bordered by an identity
    block, which is SPD, so CG with Jacobi is the right solver — but
    ``LinearProblem.solve()`` does not raise on a non-converged KSP, and step 3c
    only exonerated the *global* operator.  ``-3`` (``DIVERGED_ITS``) here would
    mean the restriction, not the field, and the cap is not raised in-slot.
    """
    diag = sar_map_restricted["diagnostics"][label]
    assert diag["converged_reason"] > 0, (
        f"the restricted CG1 mass solve for '{label}' returned PETSc converged "
        f"reason {diag['converged_reason']} after {diag['iterations']} iterations "
        f"on {diag['dofs']} dofs — every restricted reading in this column rests "
        "on this solve; record it, do not raise the iteration cap"
    )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3_PRIMAL_CONTROL_RECORDS))
def test_the_restricted_negative_controls_still_miss_the_band(sar_map_restricted, label):
    """The restriction must not smooth the controls into the band either.

    Primal reads 129.8% / 334.6% and the global CG1 column 163.6% / 75.9%.  A
    restricted control landing *below* 5% would mean the restricted fit had
    erased the azimuthal structure the identities claim to measure — and is
    itself the finding, not a licence to read the identity column beside it.
    """
    control = sar_map_restricted["controls"][label]
    assert control > CONTROL_MIN_MISMATCH, (
        f"the phantom-restricted control '{label}' reads {control * 100:.4f}%, "
        f"inside the {CONTROL_MIN_MISMATCH * 100:.1f}% band (primal reads "
        f"{STEP3_PRIMAL_CONTROL_RECORDS[label] * 100:.4f}%, global CG1 "
        f"{STEP3B_CG1_CONTROL_RECORDS[label] * 100:.4f}%) — the restricted fit has "
        "smoothed away the structure the identities measure, so no restricted "
        "identity reading here is interpretable"
    )


# ---------------------------------------------------------------------------
# `WF-6` step 3e — the promotion's own tests.  Each one asserts that a step-3d
# record survives the move into ``post/``; none of them gates SAR.


@complex_only
def test_the_packaged_restriction_separates_from_the_global_fit(sar_map_restricted):
    """Step 3e's negative control: the packaged restriction is not the global fit.

    Both readings come from the same run over the same phantom cells on the same
    ``E``: the global ``post.project_to_cg1`` leaves 1876.1871% there (step
    3b/3c, asserted above) and the packaged ``post.project_to_cg1_restricted``
    leaves 18.7238% (step 3d), a measured separation of 100.20×.  The bound is
    **50×** — an order clear of any plausible drift, and deliberately not 100×,
    which would buy a marginal red on a code-location change.  A promotion that
    accidentally kept integrating over ``dx`` instead of ``dx(tag)`` would land
    at a separation of 1.0 and is exactly what this catches.
    """
    restricted = sar_map_restricted["projection_relative_l2"]
    global_fit = sar_map_restricted["global_projection_relative_l2"]
    separation = global_fit / restricted
    assert separation >= STEP3D_RESTRICTION_MIN_SEPARATION, (
        f"the packaged post.project_to_cg1_restricted leaves "
        f"{restricted * 100:.4f}% over the phantom against the global fit's "
        f"{global_fit * 100:.4f}% — a separation of only {separation:.2f}x, below "
        f"{STEP3D_RESTRICTION_MIN_SEPARATION:.0f}x (step 3d measured 100.20x). The "
        "moved code is not restricting to the tagged subdomain"
    )


@complex_only
def test_the_restricted_phantom_residual_reproduces_step_3ds_reading(sar_map_restricted):
    """Anchor (i) as a *record*: 18.7238%, through the packaged path."""
    reading = sar_map_restricted["projection_relative_l2"]
    assert reading == pytest.approx(
        STEP3D_RESTRICTED_PHANTOM_RESIDUAL, rel=CG1_RECORD_RTOL
    ), (
        f"the packaged restricted projection leaves {reading * 100:.4f}% over the "
        f"phantom, not step 3d's {STEP3D_RESTRICTED_PHANTOM_RESIDUAL * 100:.4f}% "
        f"(rtol {CG1_RECORD_RTOL:.0e}) — the promotion changed the estimator, not "
        "just its address"
    )


@complex_only
def test_the_packaged_restriction_pins_the_same_blocks(sar_map_restricted):
    """Anchor (iii)'s census: 170 free of 21 397 owned blocks, 64 191 dofs.

    Globally reduced sums over owned blocks, so the numbers are rank-count
    independent; a pin taken over owned blocks only (the defect ``-n 2`` exists
    to catch) would move the free count, not crash.
    """
    diag = sar_map_restricted["diagnostics"]["P1"]
    owned = diag["free_blocks"] + diag["pinned_blocks"]
    assert (diag["free_blocks"], owned, diag["dofs"]) == (
        STEP3D_RESTRICTED_FREE_BLOCKS,
        STEP3D_RESTRICTED_OWNED_BLOCKS,
        STEP3D_RESTRICTED_DOFS,
    ), (
        f"the packaged restriction leaves {diag['free_blocks']} free of {owned} "
        f"owned CG1 blocks on {diag['dofs']} dofs, not step 3d's "
        f"{STEP3D_RESTRICTED_FREE_BLOCKS} / {STEP3D_RESTRICTED_OWNED_BLOCKS} / "
        f"{STEP3D_RESTRICTED_DOFS}"
    )


@complex_only
@pytest.mark.parametrize("label", RESTRICTED_SOLVE_LABELS)
def test_every_packaged_restricted_solve_reproduces_step_3ds_solver_record(
    sar_map_restricted, label
):
    """Anchor (iv) as a record: reason 2, 21–25 iterations, 64 191 dofs.

    The test beside this one asserts only ``reason > 0``, which is the physics
    gate; this one is the promotion's own, and is why the numbers are exact.  A
    moved iteration count on an unchanged operator, mesh and ``ksp_rtol`` would
    mean the packaged assembly differs from the test-local one.
    """
    diag = sar_map_restricted["diagnostics"][label]
    low, high = STEP3D_RESTRICTED_ITERATION_RANGE
    assert (
        diag["converged_reason"] == STEP3D_RESTRICTED_CONVERGED_REASON
        and low <= diag["iterations"] <= high
        and diag["dofs"] == STEP3D_RESTRICTED_DOFS
    ), (
        f"the packaged restricted solve for '{label}' returned reason "
        f"{diag['converged_reason']} after {diag['iterations']} its on "
        f"{diag['dofs']} dofs, not step 3d's reason "
        f"{STEP3D_RESTRICTED_CONVERGED_REASON} in {low}-{high} its on "
        f"{STEP3D_RESTRICTED_DOFS} dofs"
    )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3D_RESTRICTED_IDENTITY_RECORDS))
def test_the_restricted_identities_reproduce_step_3ds_readings(
    sar_map_restricted, label
):
    """Anchor (v): the five restricted identity readings, reproduced.

    A *reproduction*, not a gate — these five sit at 6.1–9.5%, outside the 5%
    band, and the primal asserts above stay red exactly as step 3 wrote them.
    Nothing about SAR is claimed here; what is claimed is that moving the
    estimator into ``post/`` moved no reading.
    """
    reading = sar_map_restricted["identities"][label]
    record = STEP3D_RESTRICTED_IDENTITY_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"the packaged restricted identity '{label}' reads {reading * 100:.4f}%, "
        f"not step 3d's {record * 100:.4f}% (rtol {CG1_RECORD_RTOL:.0e})"
    )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3D_RESTRICTED_CONTROL_RECORDS))
def test_the_restricted_controls_reproduce_step_3ds_readings(sar_map_restricted, label):
    """Anchor (v)'s controls: 123.6255% and 333.0778%, reproduced."""
    reading = sar_map_restricted["controls"][label]
    record = STEP3D_RESTRICTED_CONTROL_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"the packaged restricted control '{label}' reads {reading * 100:.4f}%, "
        f"not step 3d's {record * 100:.4f}% (rtol {CG1_RECORD_RTOL:.0e})"
    )


@complex_only
def test_the_restricted_phantom_power_reproduces_step_3ds_reading(sar_map_restricted):
    """Anchor (v): ``½∫_Ω σ|E_Ω|²`` = 5.440097168e-08 W through the packaged path.

    Reported, not gated — an L² projection does not conserve power.  It is here
    because it is the independent corroboration that the restricted fit is an
    honest estimator (−3.51% from the primal record, against the global fit's
    +35 198.9%), and a promotion that changed the fit would move it.
    """
    reading = sar_map_restricted["phantom_power_w"]
    assert reading == pytest.approx(
        STEP3D_RESTRICTED_PHANTOM_POWER_W, rel=CG1_RECORD_RTOL
    ), (
        f"the packaged restricted phantom power reads {reading:.9e} W, not step "
        f"3d's {STEP3D_RESTRICTED_PHANTOM_POWER_W:.9e} W (rtol "
        f"{CG1_RECORD_RTOL:.0e})"
    )


# ---------------------------------------------------------------------------
# `WF-6` step 3e′ (2026-09-02): the **estimator-degree** rung.
#
# Verdict (c) — step 3b's, uncontradicted by 3c/3d/3e — attributes the residual
# 6.1–9.5% miss of the five restricted-CG1 identities to the fixture's ~1 cm
# phantom cells reading a quadratic-in-``E`` map.  Nothing on this fixture has
# separated *estimator degree* from *mesh h*.  This block separates them for the
# cost of six mass solves and **no curl-curl solve**: the same four solved
# fields, the same 51 points, the same two controls, the same pinning, projected
# onto ``("Lagrange", 2, (3,))`` restricted to ``dx(3)``.  It is a different
# axis from step 3f's finer-*mesh* rung and does not pre-empt it.
#
# Everything below is **printed, not gated**, except the six anchors, which are
# theorems about the code (a CG2 fit cannot be worse than the CG1 fit it
# contains; a field lying in CG2³ must come back).  No band moves, no SAR gate
# is registered, and the five primal asserts above stay red.

# Anchor (i)'s bound: step 3d's CG1 restricted residual, imported from the
# constant above and never re-typed.  ``CG1³ ⊂ CG2³`` on one mesh, so the
# restricted best-approximation residual cannot *increase* with degree.
STEP3E_PRIME_DEGREE = 2

# Anchor (ii)/(iii): both control fields are carried on a ``CG3³`` space, where
# an affine field and a quadratic field are each represented **exactly**.  That
# matters and is the one deliberate deviation from the CG1 column's recipe: the
# CG1 column interpolated its controls onto the solve's ``N1curl₁`` space first,
# and the N1curl interpolant of ``x² ê_x`` is a tangentially-continuous
# piecewise field that does *not* lie in CG2³ — projecting it would measure the
# interpolation error, not the degree.  Carrying the exact quadratic instead is
# what makes the pre-registered flip ("CG1 leaves 3.741459e-01, CG2 must
# reproduce to 1e-10") a statement about degree.  The same-source CG1 reading is
# measured in this fixture too (one extra cheap CG1 solve) so the nine-decade
# separation is between two readings of one field, not across two recipes.
STEP3E_PRIME_CONTROL_SOURCE_DEGREE = 3

# The five CG1 restricted identity records this column is read against, and the
# ~1 pp threshold the pre-registered (β) clause names.
STEP3E_PRIME_NULL_MOVE_PP = 1.0

STEP3E_PRIME_SOLVE_LABELS = RESTRICTED_SOLVE_LABELS


def _cg2_degree_verdict(cg2_identities, cg1_records, controls, band):
    """The α/β/γ verdict, pre-registered by the 2026-09-02 03:00 review.

    Evaluated from the readings rather than read off them by eye, and in a fixed
    precedence so the printed clause cannot disagree with the table above it:

    * **(α)** all five CG2 identities inside ``band`` ⇒ the residual was the
      *estimator's degree*, verdict (c) is wrong about its cause, and a review —
      never this slot — re-opens the gate question.
    * **(β)** every reading moves by less than ~1 pp from its CG1 record ⇒
      degree is not the mechanism, (c) is corroborated, and step 3f's
      finer-mesh rung is the remaining candidate.  **This is the expected
      outcome and the informative one.**
    * **(γ)** all five get *worse* ⇒ the CG2 restriction is mis-assembled and
      anchors (i)/(ii) should have caught it — a defect in the step, not a
      reading about physics.

    ``controls`` is carried so the clause can never be reported while the
    negative controls have collapsed into the band (they are asserted
    separately; this is the belt to that braces).
    """
    controls_survive = all(value > band for value in controls.values())
    deltas_pp = {
        label: (cg2_identities[label] - cg1_records[label]) * 100.0
        for label in cg1_records
    }
    if all(cg2_identities[label] <= band for label in cg1_records) and controls_survive:
        return "(alpha)", (
            "all five CG2 identities inside the band with both controls "
            "surviving — the residual was the ESTIMATOR'S DEGREE, not the "
            "phantom's cells; verdict (c) is wrong about its cause and "
            "re-opening the SAR gate question is the NEXT REVIEW's ruling, "
            "never in-slot"
        ), deltas_pp
    if all(abs(value) < STEP3E_PRIME_NULL_MOVE_PP for value in deltas_pp.values()):
        return "(beta)", (
            f"every CG2 identity moves by less than {STEP3E_PRIME_NULL_MOVE_PP:.1f} pp "
            "from its CG1 record — DEGREE IS NOT THE MECHANISM, verdict (c) is "
            "corroborated from the other side, and the finer-MESH rung (step 3f) "
            "is the remaining candidate; the expected and informative outcome"
        ), deltas_pp
    if all(value > 0.0 for value in deltas_pp.values()):
        return "(gamma)", (
            "all five CG2 identities are WORSE than their CG1 records — a "
            "richer space cannot fit the same field worse, so this is a "
            "mis-assembled CG2 restriction (anchors (i)/(ii) should have caught "
            "it); journal as a defect in the step, not as a reading about physics"
        ), deltas_pp
    return "(none)", (
        "the reading pattern matches none of the three pre-registered clauses ("
        + ", ".join(f"{label}={deltas_pp[label]:+.4f} pp" for label in deltas_pp)
        + f"; controls survive: {controls_survive}) — reported as-is for the "
        "review, not forced into a clause"
    ), deltas_pp


@pytest.fixture(scope="module")
def sar_map_restricted_cg2(b1_plus_map, sar_map, sar_map_restricted):
    """The same five identities and two controls off a **CG2**-restricted ``E``.

    Six restricted mass solves at ``degree=2`` on the parent mesh (four drives,
    two control fields), the quadrature senses by superposing the projected dof
    arrays exactly as the CG1 column does, ``point_sar`` on the same 51 points.
    No curl-curl solve, no submesh, no new mesh.

    Depends on ``sar_map_restricted`` so the CG1 column it is compared against is
    measured in the *same run* — anchor (vi), "nothing moved", is the existing
    step-3d/3e reproduction tests, which share this window.
    """
    import ufl

    sweep = b1_plus_map["sweep"]
    solves = b1_plus_map["solves"]
    azimuths = b1_plus_map["azimuths"]
    points = b1_plus_map["points"]
    msh = sweep["mesh"]
    comm = msh.comm
    cell_tags = sweep["cell_tags"]
    delta = np.radians(b1_plus_map["delta_deg"])
    order = sorted(solves)
    ks = [sar_map["indices"][pid] for pid in order]

    dx_phantom = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)(
        PHANTOM_CELL_TAG
    )

    diagnostics = {}
    projected = {}
    for pid in order:
        projected[pid], diagnostics[pid] = project_to_cg1_restricted(
            solves[pid]["fields"].e_complex,
            cell_tags,
            name=f"E_cg2_restricted_{pid}",
            tag=PHANTOM_CELL_TAG,
            degree=STEP3E_PRIME_DEGREE,
            return_diagnostics=True,
        )
    # Anchor (i): the degree-monotonicity of the restricted best approximation.
    restricted_residual = _relative_l2_over_measure(
        projected["P1"], solves["P1"]["fields"].e_complex, dx_phantom
    )

    # Anchors (ii)/(iii): the two control fields, carried exactly on CG3³ and
    # restricted-projected at degree 2 — and, for ``x² ê_x``, at degree 1 too so
    # the pre-registered flip is a same-source comparison.
    source_space = fem.functionspace(
        msh, ("Lagrange", STEP3E_PRIME_CONTROL_SOURCE_DEGREE, (3,))
    )
    control_fields = {}
    for label, callable_ in (
        ("a + b x x", _affine_field),
        ("x^2 e_x", _quadratic_field),
    ):
        stem = "affine" if label.startswith("a") else "quadratic"
        source = fem.Function(source_space, name=f"f_{stem}_cg3_exact")
        source.interpolate(callable_)
        source.x.scatter_forward()
        fitted, diag = project_to_cg1_restricted(
            source,
            cell_tags,
            name=f"f_{stem}_cg2_restricted",
            tag=PHANTOM_CELL_TAG,
            degree=STEP3E_PRIME_DEGREE,
            return_diagnostics=True,
        )
        diagnostics[label] = diag
        control_fields[label] = {
            "residual": _relative_l2_over_measure(fitted, source, dx_phantom),
            "diagnostics": diag,
        }
        if label == "x^2 e_x":
            fitted_cg1, diag_cg1 = project_to_cg1_restricted(
                source,
                cell_tags,
                name=f"f_{stem}_cg1_restricted_same_source",
                tag=PHANTOM_CELL_TAG,
                degree=1,
                return_diagnostics=True,
            )
            control_fields[label]["degree_1_residual"] = _relative_l2_over_measure(
                fitted_cg1, source, dx_phantom
            )
            control_fields[label]["degree_1_diagnostics"] = diag_cg1

    kwargs = dict(sigma=SALINE_SIGMA, rho=PHANTOM_RHO_KG_PER_M3, comm=comm)
    split = {
        pid: _split_complex(projected[pid], f"E_cg2_restricted_{pid}") for pid in order
    }
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
                name=f"E_cg2_restricted_{sense}",
            ),
            f"E_cg2_restricted_{sense}",
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
            cell_tags=cell_tags,
            comm=comm,
            subdomain_ids=PHANTOM_CELL_TAG,
        )["dissipated_power_w"]
    )

    verdict, verdict_text, deltas_pp = _cg2_degree_verdict(
        identities, STEP3D_RESTRICTED_IDENTITY_RECORDS, controls, C4_COVARIANCE_BAND
    )

    if comm.rank == 0:
        cg1_identities = sar_map_restricted["identities"]
        cg1_controls = sar_map_restricted["controls"]
        primal_identities = sar_map["identities"]
        p1 = diagnostics["P1"]
        cg1_p1 = sar_map_restricted["diagnostics"]["P1"]
        print(
            f"\n[WF-6 step3e'] the estimator-DEGREE rung: the same point-SAR "
            f"identities off a **CG2**-restricted E, same mesh, same "
            f"{points.shape[0]} points, same four solves, same pinning, NO new "
            f"curl-curl solve — separating estimator degree from mesh h, which "
            f"nothing on this fixture had done\n"
            f"    (iv) restriction at degree {p1['degree']}: {p1['free_blocks']} free "
            f"of {p1['free_blocks'] + p1['pinned_blocks']} owned CG2 blocks "
            f"({p1['dofs']} dofs) vs CG1's {cg1_p1['free_blocks']} / "
            f"{cg1_p1['free_blocks'] + cg1_p1['pinned_blocks']} / {cg1_p1['dofs']} "
            f"— REPORTED, NOT ASSERTED (no CG2 record exists); pinned max |value| "
            f"{p1['pinned_max_abs']:.3e} (ASSERTED == 0)\n"
            f"    (v) restricted CG2 mass solves (ASSERTED converged_reason == 2, "
            f"iterations REPORTED):",
            flush=True,
        )
        for label in STEP3E_PRIME_SOLVE_LABELS:
            row = diagnostics[label]
            print(
                f"        {label:<12} reason {row['converged_reason']:>3}, "
                f"{row['iterations']:>4} its on {row['dofs']} dofs",
                flush=True,
            )
        print(
            f"    (i) ||P2_O E - E||_O/||E||_O = {restricted_residual * 100:.4f}% vs "
            f"the CG1 restriction's {STEP3D_RESTRICTED_PHANTOM_RESIDUAL * 100:.4f}% "
            f"(ASSERTED <=: CG1^3 subset CG2^3 on one mesh, so the restricted "
            f"best-approximation residual CANNOT increase with degree — a theorem "
            f"about the code, so a violation is a bug, not physics)",
            flush=True,
        )
        for label, row in control_fields.items():
            extra = (
                f"; the SAME source at degree 1 reads "
                f"{row['degree_1_residual']:.6e}, and the N1curl-borne CG1 column "
                f"read {STEP3D_RESTRICTED_CONTROL_FIELD_RECORDS[label]:.6e}"
                if "degree_1_residual" in row
                else f"; CG1 column read "
                f"{STEP3D_RESTRICTED_CONTROL_FIELD_RECORDS[label]:.6e}"
            )
            print(
                f"    (ii/iii) ||P2_O f - f||_O/||f||_O for f = {label:<9} "
                f"{row['residual']:.6e}   (ASSERTED <= "
                f"{PROJECTOR_EXACT_RESIDUAL:.0e}; reason "
                f"{row['diagnostics']['converged_reason']}, "
                f"{row['diagnostics']['iterations']} its{extra})",
                flush=True,
            )
        print(
            f"        {'':<36} {'primal':>10} {'CG1 restr':>10} {'CG2 restr':>10} "
            f"{'delta pp':>10}",
            flush=True,
        )
        for label in identities:
            print(
                f"        {label:<36} {primal_identities[label] * 100:9.4f}% "
                f"{cg1_identities[label] * 100:9.4f}% "
                f"{identities[label] * 100:9.4f}% "
                f"{deltas_pp[label]:+9.4f}   CG2 PRINTED NOT GATED",
                flush=True,
            )
        for label in controls:
            print(
                f"        {label:<36} {'':>10} {cg1_controls[label] * 100:9.4f}% "
                f"{controls[label] * 100:9.4f}% "
                f"{(controls[label] - cg1_controls[label]) * 100:+9.4f}   control, "
                "ASSERTED > band",
                flush=True,
            )
        # The (γ) clause pre-registers *one* cause — a mis-assembled CG2
        # restriction — and names anchors (i)/(ii) as what would catch it.  If
        # those anchors are green while (γ) prints, the pre-registered cause is
        # *excluded by this run's own measurements*, and the log must say so
        # rather than leave a reviewer to act on the clause's prose.  This is a
        # printed caveat, not a re-verdict: the clause label stands as computed.
        anchors_green = (
            restricted_residual <= STEP3D_RESTRICTED_PHANTOM_RESIDUAL
            and all(
                row["residual"] <= PROJECTOR_EXACT_RESIDUAL
                for row in control_fields.values()
            )
            and p1["pinned_max_abs"] <= RESTRICTED_PINNED_DOF_MAX
            and all(
                diagnostics[label]["converged_reason"]
                == STEP3D_RESTRICTED_CONVERGED_REASON
                for label in STEP3E_PRIME_SOLVE_LABELS
            )
        )
        if verdict == "(gamma)" and anchors_green:
            print(
                f"    NOTE, and it is the whole reading: (gamma)'s pre-registered "
                f"cause — 'the CG2 restriction is mis-assembled' — is EXCLUDED by "
                f"this run's own anchors, every one green with room. The degree-2 "
                f"fit is strictly BETTER in the norm it minimises "
                f"({restricted_residual * 100:.4f}% vs "
                f"{STEP3D_RESTRICTED_PHANTOM_RESIDUAL * 100:.4f}%, anchor (i)), it "
                f"reproduces both fields it contains to ~1e-12 (anchors (ii)/(iii), "
                f"the quadratic flipping "
                f"{control_fields['x^2 e_x']['degree_1_residual']:.6e} -> "
                f"{control_fields['x^2 e_x']['residual']:.6e} on ONE source), the pin "
                f"is exact 0 (anchor (iv)) and all six solves are reason 2 (anchor "
                f"(v)). So what is measured is that a globally better L2 fit of E "
                f"over the phantom is POINTWISE WORSE for these C4 identities at "
                f"these {points.shape[0]} points: the CG1 fit's extra smoothing was "
                f"flattering the identities, not resolving them. That is a finding "
                f"about the identity-from-a-fitted-field construction itself, it is "
                f"NOT a defect in this step and NOT a rescope this slot may make — "
                f"a review adjudicates it.",
                flush=True,
            )
        print(
            f"    PRE-REGISTERED VERDICT: {verdict} — {verdict_text}\n"
            f"    CG2-restricted phantom power 1/2*int(sigma|E_O|^2) = "
            f"{phantom_power_w:.9e} W vs primal "
            f"{STEP1_GATE_I_P1_PHANTOM_POWER_W:.9e} W "
            f"({(phantom_power_w / STEP1_GATE_I_P1_PHANTOM_POWER_W - 1.0) * 100:+.4f}%)"
            f" and CG1-restricted {STEP3D_RESTRICTED_PHANTOM_POWER_W:.9e} W "
            f"({(phantom_power_w / STEP3D_RESTRICTED_PHANTOM_POWER_W - 1.0) * 100:+.4f}%)"
            " — REPORTED, NOT GATED: an L2 projection does not conserve power.\n"
            "    SCOPE: no band moved, NO SAR GATE IS REGISTERED, no homogeneity / "
            "absolute / C95.3 claim, the five primal asserts stay red and WF-6 "
            "stays yellow whichever clause printed.",
            flush=True,
        )

    return {
        "identities": identities,
        "controls": controls,
        "control_fields": control_fields,
        "diagnostics": diagnostics,
        "phantom_power_w": phantom_power_w,
        "projection_relative_l2": restricted_residual,
        "cg1_projection_relative_l2": sar_map_restricted["projection_relative_l2"],
        "deltas_pp": deltas_pp,
        "verdict": verdict,
        "verdict_text": verdict_text,
    }


@complex_only
def test_the_cg2_restriction_cannot_be_worse_than_the_cg1_one(sar_map_restricted_cg2):
    """Anchor (i): degree monotonicity of the restricted best approximation.

    ``CG1³ ⊂ CG2³`` on the same mesh, so the CG1 restricted fit is one member of
    the set the CG2 fit minimises over — ``‖P²_Ω E − E‖_Ω ≤ ‖P¹_Ω E − E‖_Ω``
    holds by construction.  No mesh, no fixture and no physics enters, so a
    violation is a defect in the CG2 restriction (an unpinned ghost block, the
    wrong measure, a non-converged solve) and must be journalled as that.  The
    bound is step 3d's *measured* CG1 figure, imported from the constant and
    compared against the same-run CG1 reading beside it.
    """
    reading = sar_map_restricted_cg2["projection_relative_l2"]
    same_run_cg1 = sar_map_restricted_cg2["cg1_projection_relative_l2"]
    assert reading <= STEP3D_RESTRICTED_PHANTOM_RESIDUAL, (
        f"the CG2-restricted projection leaves {reading * 100:.4f}% over the "
        f"phantom, ABOVE the CG1 restriction's "
        f"{STEP3D_RESTRICTED_PHANTOM_RESIDUAL * 100:.4f}% (this run's CG1 column "
        f"reads {same_run_cg1 * 100:.4f}%) — a richer space cannot fit the same "
        "field worse, so this is a bug in the degree-2 restriction, not a "
        "finding about SAR or about the phantom"
    )


@complex_only
def test_the_cg2_restriction_reproduces_the_quadratic_control_exactly(
    sar_map_restricted_cg2,
):
    """Anchor (ii), the sharp one: ``x² ê_x`` lies in ``CG2³`` **exactly**.

    This is the control's control flipping sign of difficulty.  Under the CG1
    restriction the quadratic could only be *fitted* — step 3d read
    3.741459e-01, and the test beside it asserts that residual stays visible.
    Under the CG2 restriction the same field is in the target space, so the
    restricted projection must return it to solver tolerance: a pre-registered
    separation of **nine decades** on one fixture, and the strongest evidence
    available that the CG2 restriction is assembled correctly.  A miss here
    means the CG2 space, its bc's zero ``Function`` or the pinned complement is
    wrong — never that the phantom is coarse.
    """
    row = sar_map_restricted_cg2["control_fields"]["x^2 e_x"]
    residual = row["residual"]
    assert residual <= PROJECTOR_EXACT_RESIDUAL, (
        f"the phantom-restricted CG2 projection of f = x^2 e_x — which lies in "
        f"CG2^3 EXACTLY — leaves a relative L2 residual of {residual:.6e} over "
        f"the phantom, above {PROJECTOR_EXACT_RESIDUAL:.0e}.  The same source at "
        f"degree 1 reads {row['degree_1_residual']:.6e}; the degree-2 restricted "
        "operator is not the L2 projection it is built to be"
    )


@complex_only
def test_the_cg2_restriction_reproduces_the_affine_control_exactly(
    sar_map_restricted_cg2,
):
    """Anchor (iii): ``a + b × x`` is in both spaces and must come back at either.

    It is the CG1 column's exact-reproduction control (4.385695e-13 there), and
    raising the degree cannot cost it: an affine field lies in ``CG2³`` too.
    """
    residual = sar_map_restricted_cg2["control_fields"]["a + b x x"]["residual"]
    assert residual <= PROJECTOR_EXACT_RESIDUAL, (
        f"the phantom-restricted CG2 projection of f = a + b x x leaves a "
        f"relative L2 residual of {residual:.6e} over the phantom, above "
        f"{PROJECTOR_EXACT_RESIDUAL:.0e} (the CG1 column reads "
        f"{STEP3D_RESTRICTED_CONTROL_FIELD_RECORDS['a + b x x']:.6e})"
    )


@complex_only
def test_the_quadratic_control_still_misses_at_degree_one_on_the_same_source(
    sar_map_restricted_cg2,
):
    """Anchor (ii)'s other half: the flip is a flip, not a broken residual helper.

    The nine-decade separation only means something if the *same* source field,
    through the *same* restricted operator, still leaves a visible residual at
    degree 1.  If both degrees read ~1e-10 the residual helper is measuring
    nothing (an empty measure, a mis-tagged subdomain) and the test above proves
    nothing.  The floor is the arithmetic one step 3d used: a quadratic's CG1 fit
    error over a region of ``D/h ≲ 100`` cells is of order ``(h/D)² ≳ 1e-4``.
    """
    residual = sar_map_restricted_cg2["control_fields"]["x^2 e_x"]["degree_1_residual"]
    assert residual > RESTRICTED_CONTROL_MIN_RESIDUAL, (
        f"the exact quadratic source x^2 e_x restricted-projects at DEGREE 1 with "
        f"a relative L2 residual of only {residual:.6e} over the phantom — below "
        f"the arithmetic floor {RESTRICTED_CONTROL_MIN_RESIDUAL:.0e}, at which the "
        "nine-decade degree-2 separation beside it is not measuring anything"
    )


@complex_only
def test_every_cg2_dof_outside_the_phantom_is_pinned_to_exactly_zero(
    sar_map_restricted_cg2,
):
    """Anchor (iv): the pin is a pin at degree 2, on owned **and** ghost blocks.

    The CG2 space has its own dofmap, its own ghost layer and its own zero
    ``Function`` for the bc — reusing CG1's would mis-size the pin silently.
    ``set_bc`` writes an exact zero, so the bound is 0 and not a tolerance, and
    ``-n 2`` is the only width at which a complement taken over owned blocks
    alone is visible.
    """
    pinned_max = sar_map_restricted_cg2["diagnostics"]["P1"]["pinned_max_abs"]
    assert pinned_max <= RESTRICTED_PINNED_DOF_MAX, (
        f"a CG2 dof with no phantom-cell support holds {pinned_max:.6e} after the "
        "degree-2 restricted solve — the zero Dirichlet pin did not reach every "
        "block (check that the bc's zero Function is built on the CG2 space and "
        "that the complement is taken over size_local + num_ghosts)"
    )


@complex_only
@pytest.mark.parametrize("label", STEP3E_PRIME_SOLVE_LABELS)
def test_every_cg2_restricted_mass_solve_converges(sar_map_restricted_cg2, label):
    """Anchor (v): all six CG2 restricted mass solves returned reason 2.

    ``LinearProblem.solve()`` does not raise on a non-converged KSP, and the CG2
    mass matrix is worse conditioned than the CG1 one, so this is where a
    degree-2 rung would fail quietly.  The iteration count is *reported*, not
    gated: no CG2 record exists to gate it against, and inventing one in-slot
    would be a band this step is not allowed to move.
    """
    diag = sar_map_restricted_cg2["diagnostics"][label]
    assert diag["converged_reason"] == STEP3D_RESTRICTED_CONVERGED_REASON, (
        f"the degree-2 restricted mass solve for '{label}' returned PETSc "
        f"converged reason {diag['converged_reason']} after {diag['iterations']} "
        f"iterations on {diag['dofs']} dofs — every CG2 reading in this column "
        "rests on this solve; record it, do not raise the iteration cap"
    )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3D_RESTRICTED_CONTROL_RECORDS))
def test_the_cg2_negative_controls_still_miss_the_band(sar_map_restricted_cg2, label):
    """The negative control: a higher-degree fit must not smooth the controls in.

    The mis-rotated drive and the quadrature-vs-single-drive comparison read
    123.6255% and 333.0778% under the CG1 restriction.  A CG2 control landing
    *under* 5% would mean the richer fit had erased the azimuthal structure the
    identities claim to measure — and is itself the finding, not a licence to
    read the identity column beside it.
    """
    control = sar_map_restricted_cg2["controls"][label]
    assert control > CONTROL_MIN_MISMATCH, (
        f"the CG2-restricted control '{label}' reads {control * 100:.4f}%, inside "
        f"the {CONTROL_MIN_MISMATCH * 100:.1f}% band (the CG1 restriction reads "
        f"{STEP3D_RESTRICTED_CONTROL_RECORDS[label] * 100:.4f}%) — the degree-2 "
        "fit has smoothed away the structure the identities measure, so no CG2 "
        "identity reading here is interpretable"
    )
