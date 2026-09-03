"""`WF-6` step 3f — the finer-phantom rung of the coil-driven SAR identities.

Steps 3–3e′ measured, on the 116 085-cell F-small birdcage, that the five
C4 / mirror point-SAR identities miss the imported 5% band at **8.2868 /
9.4743 / 7.3477 / 6.8146 / 6.1185%** when read off
:func:`~fem_em_solver.post.project_to_cg1_restricted` (degree 1) — the only
honest ``E`` estimator this repo has on this fixture — and that two of the
three candidate mechanisms are **excluded**: the projector (step 3c: it
reproduces ``a + b × x`` to 1e-13 and its mass solve converges) and the
estimator's *degree* (step 3e′: the CG2³ restricted fit is strictly better in
the norm it minimises, 14.4724% vs 18.7238%, and yet reads the identities
*worse*, 11.3–19.3%).  What is left standing is verdict (c)'s own attribution:
the fixture's ~1 cm phantom cells.  This module turns that knob.

**The rung.**  `WF-6` step 3f₀ (2026-09-02) put ``phantom_resolution`` on
``birdcage_port_domain`` and threaded it through ``build_four_port_sweep``,
with the parameter-absent path measured as a bit-for-bit no-op (116 085 / 537
cells at 0.000e+00).  At ``phantom_resolution = 0.0075`` — one halving of the
0.015 global sizing, applied to the phantom alone — it measured **120 499**
cells of which **2 746** are tag-3 (5.11× the phantom cells, +4 414 overall,
the cells outside tag 3 moving 1.9%).  This module runs the whole four-drive
sweep on *that* mesh and re-reads every column, so the only thing that differs
from step 3e's window is the phantom's ``h``.

**Anchors, asserted.**

* **(iii) the mesh is step 3f₀'s mesh** — 120 499 global cells and 2 746 tag-3
  cells at exact equality.  It is the proof that the knob reached the
  constructor: a ``phantom_resolution`` silently dropped somewhere in the
  passthrough chain would rebuild the 116 085-cell mesh and every reading
  below would be step 3e's, re-printed under a new heading.
* **(i) the coil-side records did not move.**  Gate (i)'s three-way power
  accounting closes inside the unmoved ``POWER_BALANCE_BAND`` at both driven
  ports, with its conductor-drop negative control still missing; and the three
  CG1 ``|B₁⁺|`` C4 identities land within **0.5 pp** of their 10 MHz records
  (2.1870 / 2.1146 / 1.8911%).  These are *mesh-converged at the ~2% floor* by
  hypothesis and this is the first test of that hypothesis — a move larger
  than 0.5 pp is a fixture finding to be journalled, not a band to widen.  The
  mis-rotated ``|B₁⁺|`` control is asserted to survive, as everywhere else.
* **(ii) the estimator is still an estimator on the new mesh.**  The
  *same-mesh* best-approximation inequality — the restricted residual
  ``‖P_Ω E − E‖_Ω/‖E‖_Ω`` ≤ the **global** ``post.project_to_cg1`` residual
  over the same phantom cells, both measured in this run — plus
  ``P_Ω(a + b × x) = a + b × x`` to 1e-10, its control's control ``x² ê_x``
  above the arithmetic 1e-4 floor, the pin exactly zero over owned *and* ghost
  blocks, and a positive ``converged_reason`` on all six restricted solves.
  The 2026-09-02 10:30 review sharpened this anchor deliberately: comparing
  the new mesh's residual against step 3d's 18.7238% would compare two
  different meshes' primal fields and is **not** a theorem, so that figure is
  *printed* beside the reading and never asserted.
* **the negative controls survive.**  Both step-3b controls (the mis-rotated
  drive and the quadrature-vs-single-drive comparison) are asserted to stay
  outside the band on the new mesh, exactly as they are on the coarse one
  (123.6255% / 333.0778% there).  A finer mesh that smoothed them in would
  make every identity reading beside them uninterpretable.

**Printed, not gated — the deliverable.**  The five identities off the
restricted degree-1 estimator, beside their coarse-mesh records, under the
verdict the 2026-09-02 weekly review pre-registered and the 10:30 review
re-read:

* **(a)** all five ≤ 5% ⇒ verdict (c) is confirmed and *a review* — never this
  module and never the slot that runs it — may then register the first
  coil-driven SAR gate in the repo, on the restricted estimator at this rung;
* **(b)** they fall but stay > 5% ⇒ report the ratio.  One halving of ``h``
  should roughly *quarter* a second-order residual (6–9.5% → 1.5–2.5%); a
  ratio near 1 says ``h`` is not the mechanism either;
* **(c)** unchanged or **higher** ⇒ neither degree nor ``h``.  Step 3e′
  established that a better-resolved ``E`` can *raise* these numbers, so a
  rise here is a reading, not a defect — the module says which.

**One difference from the coarse column that cannot be avoided, and is
printed.**  The sample set is built from the *mesh's own* tag-3 centroids
inside the ``r ≤ 0.02 m, |z| ≤ 0.02 m`` cylinder, so a finer phantom gives more
of them (the coarse mesh gave 51).  An h-rung on a centroid sample set changes
both; step 1c already measured that the sample set is **not** the mechanism for
the ``|B₁⁺|`` column (±2 pp between a centroid set and a rotation-invariant
ring set), which is why this rung is read as an ``h`` rung.

**Scope.**  One rung, F-small, 10 MHz, degree 1.  No band moves, **no SAR gate
is registered whatever prints**, no homogeneity / absolute / C95.3 claim, and
`WF-6` stays 🟡.  The printed verdict is the deliverable.

**Step 3f′ (2026-09-02, ruled by the 18:00 review as option (2) of step 3f's
known-issues entry) adds three things to this same fixture — the same four
solves, no new solve.**

* **(A) the ring set.**  Step 1c's 96-point rotation-invariant set
  (:func:`tests.validation.test_birdcage_b1_plus_map._ring_points`, built from
  constants and therefore identical at any rank count and closed under the
  rotation) is read *beside* the mesh's own 373 tag-3 centroids, on **both**
  columns: the three ``|B₁⁺|`` C4 identities and the five restricted-CG1 SAR
  identities.  The rung moves the phantom's ``h`` and the centroid sample set
  together; this separates them, and **±2 pp** — step 1c's measured separation
  on the coarse DG0 column — is the asserted bar at all eight identities.  A
  larger disagreement means the sample set *is* a mechanism on this rung and
  every ``h``-attribution above is then a reading of two things at once.
* **(B) anchor (i) re-read one-sided.**  An identity may not get *worse* than
  its coarse record by more than 0.5 pp; a fall is the convergence measurement
  the rung was run to make, not a miss.  The fine readings 0.6177 / 0.5966 /
  0.5647% are recorded as ``STEP3F_B1_PLUS_FINE_RECORDS`` **beside** the coarse
  ones — the coarse records are imported unchanged and nothing is replaced.
* **(C) the integral column, printed not gated.**  Step 3g/3h's twelve C4
  integral pairs of the **primal** ``E`` formed on *this* mesh, beside the
  coarse mesh's 0.7149 … 0.2302%: the gate registered by step 3h at fixed ``h``
  gets its first ``h`` data point here.  Its partition identity and its P1
  total *are* asserted (they are arithmetic and a record, not a gate on the
  identities).

Run (complex build required)::

    scripts/testing/run_and_log.sh WF-6-step3f-prime "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 600 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_birdcage_sar_fine_phantom.py -v -s'"
"""

from __future__ import annotations

import numpy as np
import pytest
from dolfinx import fem

from fem_em_solver.post import (
    magnetic_flux_density_from_e,
    mean_sar,
    project_to_cg1,
    project_to_cg1_restricted,
)
from fem_em_solver.post.sar import point_sar

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_phantom_resolution import (
    DEFAULT_CELL_COUNT,
    DEFAULT_PHANTOM_CELL_COUNT,
    PHANTOM_RESOLUTION_FINE,
    _global_tag_cell_count,
)
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.validation.test_birdcage_b1_plus_map import (
    C4_COVARIANCE_BAND,
    CG1_RECORD_RTOL,
    MIN_SAMPLE_POINTS,
    PHANTOM_RHO_KG_PER_M3,
    POWER_BALANCE_BAND,
    STEP1B_CG1_RECORDS,
    _power_shares,
    _read_b1_plus_cg1,
    _relative_l2,
    _ring_points,
    _rotate_z,
    _sample_points,
    _solve_driven,
)
from tests.validation.test_birdcage_sar_integral import (
    PARTITION_EPS_M,
    PARTITION_RTOL,
    QUADRATURE_DEGREE,
    STEP3G_INTEGRAL_PAIR_RECORDS,
    _quadrant_powers,
)
from tests.validation.test_birdcage_b1_quadrature import (
    QUADRATURE_STEP_DEG,
    _mirror_xy,
    _port_index,
    quadrature_phase_weights,
)
from tests.validation.test_birdcage_sar_map import (
    CONTROL_MIN_MISMATCH,
    PROJECTOR_EXACT_RESIDUAL,
    RESTRICTED_CONTROL_MIN_RESIDUAL,
    RESTRICTED_PINNED_DOF_MAX,
    RESTRICTED_SOLVE_LABELS,
    STEP1_GATE_I_P1_PHANTOM_POWER_W,
    STEP3D_RESTRICTED_CONTROL_RECORDS,
    STEP3D_RESTRICTED_IDENTITY_RECORDS,
    STEP3D_RESTRICTED_PHANTOM_RESIDUAL,
    STEP3D_RESTRICTED_PHANTOM_POWER_W,
    _affine_field,
    _quadratic_field,
    _relative_l2_over_measure,
    _split_complex,
    _superpose_complex,
)
from tests.validation.test_lossy_sphere_fullwave import SALINE_SIGMA
from tests.validation.test_port_birdcage_four_port import build_four_port_sweep
from tests.validation.test_port_birdcage_lumped_column import PHANTOM_CELL_TAG

# Step 3f₀'s measurement of *this* rung, `20260902T140410Z_WF-6-step3f0.log`
# (`1 passed` / Status 0 / 86 s, `-n 2` real): at ``phantom_resolution =
# 0.0075`` the fixture meshes to 120 499 global cells of which 2 746 carry tag
# 3, against the default 116 085 / 537.  Asserted at **exact equality**, not in
# a band: gmsh is deterministic for a fixed input and this is the anchor that
# the knob reached the constructor at all.
FINE_CELL_COUNT = 120499
FINE_PHANTOM_CELL_COUNT = 2746

# Anchor (i)'s band on the coil-side ``|B₁⁺|`` C4 identities.  Their records
# (2.1870 / 2.1146 / 1.8911%) are step 1b's, imported through
# ``STEP1B_CG1_RECORDS``; they were measured on the *coarse* mesh, so they
# cannot be reproduced at ``CG1_RECORD_RTOL`` here — a different mesh is a
# different discretisation.  0.5 pp is the weekly review's pre-registered
# ceiling on the move, chosen because these figures are held to be
# mesh-converged at the ~2% floor and this rung is the first test of that: a
# larger move is a **fixture finding** to be journalled, never a band to widen.
COIL_SIDE_MOVE_CEILING_PP = 0.5

# The threshold at which an identity counts as having *moved* rather than
# stayed put, in percentage points.  Step 3e′'s ``STEP3E_PRIME_NULL_MOVE_PP``
# used the same 1 pp for the same purpose on the same five readings; it is
# repeated rather than imported so that clause (b)/(c) of *this* step's
# pre-registration is readable in one place.
NULL_MOVE_PP = 1.0

# The ratio band the weekly named for clause (b): one halving of ``h`` quarters
# a second-order residual, so 6.1–9.5% would land at 1.5–2.5% and the ratio
# ``new / coarse`` at ~0.25.  Printed as an interpretation aid only — nothing
# is asserted against it.
SECOND_ORDER_RATIO = 0.25

# --- step 3f′ -------------------------------------------------------------
#
# Step 1c measured the centroid set against the rotation-invariant ring set on
# the coarse DG0 ``|B₁⁺|`` column and found them to agree within **±2 pp**.
# That measurement is the bar here, on both columns and on this mesh: inside
# it, the sample set is not the mechanism and this module's rung is an ``h``
# rung; outside it, the two are confounded and the attribution above is not
# available.  It is a *comparison* bar between two readings of the same
# quantity, never a band on either reading.
RING_VS_CENTROID_CEILING_PP = 2.0

# Step 3f's own readings of the three ``|B₁⁺|`` C4 identities on THIS mesh,
# `20260902T170559Z_WF-6-step3f.log:4709-4711`.  Recorded **beside** the coarse
# ``STEP1B_CG1_RECORDS`` (2.1870 / 2.1146 / 1.8911%), which are imported
# unchanged and are what anchor (i) is still stated against: nothing is
# replaced here, and the one-sided form of that anchor below is what makes the
# −1.53 pp move a measurement rather than a miss.
STEP3F_B1_PLUS_FINE_RECORDS = {
    "P2@+90deg": 0.6177e-2,
    "P4@-90deg": 0.5966e-2,
    "P3@180deg": 0.5647e-2,
}

# Step 3f's five restricted-CG1 SAR identities on this mesh, same log
# (`:4725-4729`), and the run's other single-figure records.  They are
# reproductions — the whole point of adding columns to a fixture is that the
# columns already in it must not move — never bands.  Re-record only under the
# (1*) licence.
STEP3F_RESTRICTED_FINE_IDENTITY_RECORDS = {
    "(i) SAR_P2(Rx) vs SAR_P1(x)": 3.3600e-2,
    "(i) SAR_P4(-Rx) vs SAR_P1(x)": 3.4442e-2,
    "(i) SAR_P3(180deg) vs SAR_P1(x)": 3.4525e-2,
    "(ii) SAR_ccw(Rx) vs SAR_ccw(x)": 3.0332e-2,
    "(iii) SAR_cw(Mx) vs SAR_ccw(x)": 2.5465e-2,
}
STEP3F_FINE_RESTRICTED_RESIDUAL = 12.5225e-2
STEP3F_FINE_GLOBAL_RESIDUAL = 1626.2098e-2
# The affine reproduction residual is a Krylov round-off quantity, but the
# solve is deterministic for a fixed mesh, partition and rank count, so it
# reproduces run to run at this rank count.  It is recorded at
# ``CG1_RECORD_RTOL`` like the rest; a miss is a fixture finding (a different
# partition, a different image), not a licence to loosen the bound.
STEP3F_FINE_AFFINE_RESIDUAL = 9.947634e-13
STEP3F_FINE_PRIMAL_PHANTOM_POWER_W = 5.587038273e-08

# The worst of step 3g's twelve coarse-mesh C4 integral pairs (1.5200%), the
# construction step 3h registered as the repo's first coil-driven SAR gate at
# **fixed h**.  Clause (a) of this step's pre-registration is "the fine mesh
# does not read worse than that".
COARSE_INTEGRAL_WORST_PAIR = max(STEP3G_INTEGRAL_PAIR_RECORDS.values())


def _fine_integral_verdict(pairs, band):
    """The (a)/(b)/(c) clause for the integral column, pre-registered 2026-09-02.

    Step 3h's gate is a statement at one ``h``; this is its first second point.
    Evaluated in a fixed precedence from the readings so the clause a review
    acts on cannot disagree with the table printed above it.  **Nothing here is
    asserted** — the twelve pairs are printed on this mesh, by design.
    """
    worst = max(pairs.values())
    if worst <= COARSE_INTEGRAL_WORST_PAIR:
        return "(a)", (
            f"the worst C4 integral pair on the finer phantom reads "
            f"{worst * 100:.4f}%, at or below the coarse mesh's "
            f"{COARSE_INTEGRAL_WORST_PAIR * 100:.4f}% — the integral gate's "
            "headroom does not shrink with h"
        )
    if worst <= band:
        return "(b)", (
            f"the worst C4 integral pair reads {worst * 100:.4f}%, above the "
            f"coarse mesh's {COARSE_INTEGRAL_WORST_PAIR * 100:.4f}% but inside "
            f"the {band * 100:.1f}% band — report; step 3h's headroom is "
            "stated from the larger figure by the NEXT REVIEW, never in-slot"
        )
    return "(c)", (
        f"the worst C4 integral pair reads {worst * 100:.4f}%, OUTSIDE the "
        f"{band * 100:.1f}% band step 3h gates at fixed h — the integral "
        "construction is not h-stable; known-issues entry against step 3h and "
        "the next review decides"
    )


def _fine_mesh_verdict(identities, coarse_records, controls, band):
    """The (a)/(b)/(c) verdict, pre-registered 2026-09-02 (weekly, re-read 10:30).

    Evaluated from the readings in a fixed precedence rather than read off them
    by eye, so the clause the review acts on cannot disagree with the table
    printed above it.  A pattern matching no clause is reported as such — the
    pre-registration is never stretched to cover it in-slot.

    ``controls`` is carried so no clause can be reported while the negative
    controls have collapsed into the band (they are asserted separately; this
    is the belt to those braces).
    """
    controls_survive = all(value > band for value in controls.values())
    deltas_pp = {
        label: (identities[label] - coarse_records[label]) * 100.0
        for label in coarse_records
    }
    ratios = {
        label: identities[label] / coarse_records[label] for label in coarse_records
    }
    if all(identities[label] <= band for label in coarse_records) and controls_survive:
        return "(a)", (
            "all five identities are inside the band on the finer phantom with "
            "both controls surviving — verdict (c)'s attribution to the "
            "phantom's h is CONFIRMED, and registering the first coil-driven "
            "SAR gate on the restricted estimator at this rung is the NEXT "
            "REVIEW's ruling, never in-slot"
        ), deltas_pp, ratios
    if all(value <= -NULL_MOVE_PP for value in deltas_pp.values()):
        mean_ratio = float(np.mean(list(ratios.values())))
        return "(b)", (
            f"all five identities FELL by more than {NULL_MOVE_PP:.1f} pp but "
            f"stay outside the {band * 100:.1f}% band — mean ratio "
            f"new/coarse {mean_ratio:.4f} against the {SECOND_ORDER_RATIO:.2f} "
            "one halving of h would give a second-order residual; a ratio near "
            "1 says h is not the mechanism either.  Report and stop"
        ), deltas_pp, ratios
    if all(value >= -NULL_MOVE_PP for value in deltas_pp.values()):
        risen = [label for label, value in deltas_pp.items() if value > NULL_MOVE_PP]
        return "(c)", (
            "no identity fell by more than "
            f"{NULL_MOVE_PP:.1f} pp on a phantom meshed at half the cell size "
            f"({len(risen)} of {len(deltas_pp)} rose by more than that) — "
            "NEITHER estimator degree (step 3e′) NOR mesh h is the mechanism.  "
            "Step 3e′ showed a better-resolved E can RAISE these numbers, so a "
            "rise here is a reading and not a defect; the construction itself "
            "(a quadratic identity read from a fitted field at sampled points) "
            "is what a review must adjudicate"
        ), deltas_pp, ratios
    return "(none)", (
        "the reading pattern matches none of the pre-registered clauses ("
        + ", ".join(f"{label}={deltas_pp[label]:+.4f} pp" for label in deltas_pp)
        + f"; controls survive: {controls_survive}) — reported as-is for the "
        "review, not forced into a clause"
    ), deltas_pp, ratios


@pytest.fixture(scope="module")
def fine_phantom():
    """One finer-phantom mesh, four drives, and every column step 3e read.

    Four curl-curl solves (the drives), four global CG1 mass solves (the
    ``|B₁⁺|`` estimator of gate (ii)), one global CG1 mass solve on ``E`` (the
    same-mesh negative control for the best-approximation inequality) and six
    restricted mass solves (four drives + two projector controls).  No
    ``reuse=`` anywhere: it hands back the *coarse* mesh by construction, which
    would make this whole module a second printing of step 3e.
    """
    import ufl

    sweep = build_four_port_sweep(phantom_resolution=PHANTOM_RESOLUTION_FINE)
    msh = sweep["mesh"]
    comm = msh.comm
    cell_tags = sweep["cell_tags"]
    cells = int(sweep["cells"])
    phantom_cells = _global_tag_cell_count(msh, cell_tags, PHANTOM_CELL_TAG, comm)

    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    delta_deg = (azimuths["P2"] - azimuths["P1"]) % 360.0
    delta = np.radians(delta_deg)

    solves = {pid: _solve_driven(sweep, pid) for pid in ("P1", "P2", "P3", "P4")}
    shares = {pid: _power_shares(sweep, solves[pid]) for pid in ("P1", "P2")}

    points = _sample_points(sweep)
    order = sorted(solves)
    indices = {
        pid: _port_index(azimuths[pid], azimuths["P1"], QUADRATURE_STEP_DEG)
        for pid in order
    }
    ks = [indices[pid] for pid in order]

    images = {
        "P1@0deg": ("P1", points),
        "P2@+90deg": ("P2", _rotate_z(points, delta)),
        "P4@-90deg": ("P4", _rotate_z(points, -delta)),
        "P3@180deg": ("P3", _rotate_z(points, 2.0 * delta)),
        "P3@+90deg": ("P3", _rotate_z(points, delta)),
    }

    # --- anchor (i): the coil-side |B1+| column, CG1 estimator, gate (ii)'s.
    b_projected = {
        pid: project_to_cg1(
            magnetic_flux_density_from_e(
                solves[pid]["fields"].e_complex, solves[pid]["omega"]
            ),
            name=f"B_cg1_{pid}",
        )
        for pid in order
    }
    b1_values, b1_valid = {}, {}
    for label, (pid, pts) in images.items():
        b1_values[label], b1_valid[label] = _read_b1_plus_cg1(b_projected[pid], pts)
    b1_mask = np.logical_and.reduce([b1_valid[label] for label in images])
    b1_table = {
        label: _relative_l2(b1_values[label], b1_values["P1@0deg"], b1_mask)
        for label in images
        if label != "P1@0deg"
    }

    # --- anchor (ii): the restricted estimator on the new mesh, with the
    # same-mesh global fit beside it as the asserted comparison.
    dx_phantom = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)(
        PHANTOM_CELL_TAG
    )
    diagnostics = {}
    projected = {}
    for pid in order:
        projected[pid], diagnostics[pid] = project_to_cg1_restricted(
            solves[pid]["fields"].e_complex,
            cell_tags,
            name=f"E_cg1_restricted_fine_{pid}",
            tag=PHANTOM_CELL_TAG,
            return_diagnostics=True,
        )
    restricted_residual = _relative_l2_over_measure(
        projected["P1"], solves["P1"]["fields"].e_complex, dx_phantom
    )
    e_global, global_diag = project_to_cg1(
        solves["P1"]["fields"].e_complex,
        name="E_cg1_global_fine_P1",
        return_diagnostics=True,
    )
    global_residual = _relative_l2_over_measure(
        e_global, solves["P1"]["fields"].e_complex, dx_phantom
    )

    n1curl = solves["P1"]["fields"].e_complex.function_space
    control_fields = {}
    for label, callable_ in (
        ("a + b x x", _affine_field),
        ("x^2 e_x", _quadratic_field),
    ):
        stem = "affine" if label.startswith("a") else "quadratic"
        source = fem.Function(n1curl, name=f"f_{stem}_n1curl_fine")
        source.interpolate(callable_)
        source.x.scatter_forward()
        fitted, diag = project_to_cg1_restricted(
            source,
            cell_tags,
            name=f"f_{stem}_cg1_restricted_fine",
            tag=PHANTOM_CELL_TAG,
            return_diagnostics=True,
        )
        diagnostics[label] = diag
        control_fields[label] = {
            "residual": _relative_l2_over_measure(fitted, source, dx_phantom),
            "diagnostics": diag,
        }

    # --- the five identities and two controls, off the restricted E.
    kwargs = dict(sigma=SALINE_SIGMA, rho=PHANTOM_RHO_KG_PER_M3, comm=comm)
    split = {
        pid: _split_complex(projected[pid], f"E_cg1_restricted_fine_{pid}")
        for pid in order
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
                name=f"E_cg1_restricted_fine_{sense}",
            ),
            f"E_cg1_restricted_fine_{sense}",
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

    # --- step 3f′ (A): the same eight identities on step 1c's ring set.
    #
    # The set is built from constants about the COIL axis, is closed under the
    # rotation by construction, and is identical on every rank — so the only
    # thing that differs from the block above is *which points* are read.  Both
    # columns go through the same helpers as their centroid counterparts (the
    # CG1 ``|B₁⁺|`` reader and ``post.sar.point_sar``, which evaluates through
    # ``evaluate_vector_field_parallel`` and raises rather than returning a
    # zero for a point no rank owns).
    def _columns_on(pts):
        images_pts = {
            "P1@0deg": ("P1", pts),
            "P2@+90deg": ("P2", _rotate_z(pts, delta)),
            "P4@-90deg": ("P4", _rotate_z(pts, -delta)),
            "P3@180deg": ("P3", _rotate_z(pts, 2.0 * delta)),
            "P3@+90deg": ("P3", _rotate_z(pts, delta)),
        }
        values, valid_flags = {}, {}
        for label, (pid, p) in images_pts.items():
            values[label], valid_flags[label] = _read_b1_plus_cg1(b_projected[pid], p)
        mask = np.logical_and.reduce([valid_flags[label] for label in images_pts])
        b1 = {
            label: _relative_l2(values[label], values["P1@0deg"], mask)
            for label in images_pts
            if label != "P1@0deg"
        }
        sar_single = {
            label: point_sar(*split[pid], p, **kwargs)
            for label, (pid, p) in images_pts.items()
        }
        sar_quad = {
            ("ccw", "x"): point_sar(*superposed["ccw"], pts, **kwargs),
            ("ccw", "Rx"): point_sar(
                *superposed["ccw"], _rotate_z(pts, delta), **kwargs
            ),
            ("cw", "Mx"): point_sar(
                *superposed["cw"], _mirror_xy(pts, azimuths["P1"]), **kwargs
            ),
        }
        every = np.ones(pts.shape[0], dtype=bool)
        ref = sar_single["P1@0deg"]
        ident = {
            "(i) SAR_P2(Rx) vs SAR_P1(x)": _relative_l2(
                sar_single["P2@+90deg"], ref, every
            ),
            "(i) SAR_P4(-Rx) vs SAR_P1(x)": _relative_l2(
                sar_single["P4@-90deg"], ref, every
            ),
            "(i) SAR_P3(180deg) vs SAR_P1(x)": _relative_l2(
                sar_single["P3@180deg"], ref, every
            ),
            "(ii) SAR_ccw(Rx) vs SAR_ccw(x)": _relative_l2(
                sar_quad[("ccw", "Rx")], sar_quad[("ccw", "x")], every
            ),
            "(iii) SAR_cw(Mx) vs SAR_ccw(x)": _relative_l2(
                sar_quad[("cw", "Mx")], sar_quad[("ccw", "x")], every
            ),
        }
        ctrl = {
            "mis-rotated SAR_P3(Rx) vs SAR_P1(x)": _relative_l2(
                sar_single["P3@+90deg"], ref, every
            ),
            "quadrature SAR_ccw(x) vs single-drive SAR_P1(x)": _relative_l2(
                sar_quad[("ccw", "x")], ref, every
            ),
        }
        return b1, int(mask.sum()), ident, ctrl

    ring_points = _ring_points()
    ring_b1_table, ring_b1_valid, ring_identities, ring_controls = _columns_on(
        ring_points
    )
    ring_vs_centroid_pp = {
        f"|B1+| {label}": (ring_b1_table[label] - b1_table[label]) * 100.0
        for label in STEP1B_CG1_RECORDS
    }
    ring_vs_centroid_pp.update(
        {
            f"SAR {label}": (ring_identities[label] - identities[label]) * 100.0
            for label in identities
        }
    )

    # --- step 3f′ (C): step 3g/3h's integral construction on THIS mesh.
    #
    # The primal N1curl field, no projection and no sample set; the partition's
    # ``eps`` and the pinned ``quadrature_degree`` are imported constants, and
    # the powers come back MPI-reduced from the same helper the gate uses.
    dx_partition = ufl.Measure(
        "dx",
        domain=msh,
        subdomain_data=cell_tags,
        metadata={"quadrature_degree": QUADRATURE_DEGREE},
    )(PHANTOM_CELL_TAG)
    sigma_field = solves["P1"]["fields"].sigma_field
    by_k = {indices[pid]: pid for pid in order}
    integral_totals, integral_quadrants = {}, {}
    for k in range(4):
        integral_totals[k], integral_quadrants[k] = _quadrant_powers(
            solves[by_k[k]]["fields"].e_complex, sigma_field, dx_partition, comm
        )
    integral_pairs, integral_control_pairs = {}, {}
    for k in range(3):
        for j in range(4):
            ref_power = integral_quadrants[k][j]
            integral_pairs[(k, j)] = (
                abs(integral_quadrants[k + 1][(j + 1) % 4] - ref_power) / ref_power
            )
            integral_control_pairs[(k, j)] = (
                abs(integral_quadrants[k + 1][(j + 2) % 4] - ref_power) / ref_power
            )
    integral_verdict, integral_verdict_text = _fine_integral_verdict(
        integral_pairs, C4_COVARIANCE_BAND
    )

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
    primal_phantom_power_w = float(
        mean_sar(
            solves["P1"]["fields"].e_complex,
            sigma=solves["P1"]["fields"].sigma_field,
            rho=PHANTOM_RHO_KG_PER_M3,
            cell_tags=cell_tags,
            comm=comm,
            subdomain_ids=PHANTOM_CELL_TAG,
        )["dissipated_power_w"]
    )

    verdict, verdict_text, deltas_pp, ratios = _fine_mesh_verdict(
        identities, STEP3D_RESTRICTED_IDENTITY_RECORDS, controls, C4_COVARIANCE_BAND
    )

    if comm.rank == 0:
        p1 = diagnostics["P1"]
        print(
            f"\n[WF-6 step3f] the finer-PHANTOM rung: the whole four-drive sweep "
            f"rebuilt at phantom_resolution = {PHANTOM_RESOLUTION_FINE} m (one "
            f"halving of the 0.015 global sizing, phantom only), f = "
            f"{sweep['problem'].frequency_hz:.3e} Hz, degree 1\n"
            f"    (iii) mesh: {cells} cells ({DEFAULT_CELL_COUNT} coarse, "
            f"{cells - DEFAULT_CELL_COUNT:+d}), tag-3 phantom {phantom_cells} "
            f"({DEFAULT_PHANTOM_CELL_COUNT} coarse, "
            f"{phantom_cells / DEFAULT_PHANTOM_CELL_COUNT:.4f}x) — ASSERTED at "
            f"exact equality against step 3f0's {FINE_CELL_COUNT} / "
            f"{FINE_PHANTOM_CELL_COUNT}\n"
            f"    sample set: {points.shape[0]} tag-3 centroids in the r <= 0.02 m, "
            f"|z| <= 0.02 m cylinder (the coarse mesh gave 51) — a finer phantom "
            f"gives more of its own centroids, which is inherent to an h rung; "
            f"step 1c measured the sample set is NOT the mechanism for the |B1+| "
            f"column\n"
            f"    solve times "
            + ", ".join(f"{p} {solves[p]['solve_time']:.2f} s" for p in order),
            flush=True,
        )
        for pid, sh in shares.items():
            total = sh["phantom"] + sh["conductor"] + sh["sheet_total"]
            print(
                f"    (i) [{pid} driven] supplied {sh['supplied']:.9e} W = phantom "
                f"{sh['phantom']:.9e} + conductor {sh['conductor']:.9e} + sheets "
                f"{sh['sheet_total']:.9e}; residual "
                f"{abs(sh['supplied'] - total) / abs(sh['supplied']):.6e} "
                f"(ASSERTED <= {POWER_BALANCE_BAND:.0e}, unmoved), without the "
                f"conductor term "
                f"{abs(sh['supplied'] - (total - sh['conductor'])) / abs(sh['supplied']):.6e} "
                f"(ASSERTED > band)",
                flush=True,
            )
        print(
            f"    (i) CG1 |B1+| C4 identities on {int(b1_mask.sum())} of "
            f"{points.shape[0]} centroids (band {C4_COVARIANCE_BAND * 100:.1f}%, "
            f"records from the coarse mesh, ASSERTED within "
            f"{COIL_SIDE_MOVE_CEILING_PP:.1f} pp of them):",
            flush=True,
        )
        for label, record in STEP1B_CG1_RECORDS.items():
            print(
                f"        {label:<12} {b1_table[label] * 100:9.4f}%   coarse record "
                f"{record * 100:7.4f}%   move {(b1_table[label] - record) * 100:+7.4f} pp",
                flush=True,
            )
        print(
            f"        {'P3@+90deg':<12} {b1_table['P3@+90deg'] * 100:9.4f}%   "
            f"mis-rotated control, ASSERTED > band\n"
            f"    (ii) restriction: {p1['free_blocks']} free of "
            f"{p1['free_blocks'] + p1['pinned_blocks']} owned CG1 blocks "
            f"({p1['dofs']} dofs; coarse 170 / 21 397 / 64 191), pinned max |value| "
            f"{p1['pinned_max_abs']:.3e} (ASSERTED == 0)\n"
            f"    (ii) restricted mass solves (ASSERTED converged_reason > 0):",
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
            f"    (ii) SAME-MESH best approximation: restricted "
            f"{restricted_residual * 100:.4f}% <= global fit "
            f"{global_residual * 100:.4f}% over the same phantom cells (ASSERTED; "
            f"separation {global_residual / restricted_residual:.2f}x, global solve "
            f"reason {global_diag['converged_reason']} in "
            f"{global_diag['iterations']} its).  The coarse mesh read "
            f"{STEP3D_RESTRICTED_PHANTOM_RESIDUAL * 100:.4f}% restricted — PRINTED, "
            f"NOT ASSERTED: two meshes' primal fields are not comparable and that "
            f"comparison is not a theorem",
            flush=True,
        )
        for label, row in control_fields.items():
            print(
                f"    (ii) ||P_O f - f||_O/||f||_O for f = {label:<9} "
                f"{row['residual']:.6e}   (reason "
                f"{row['diagnostics']['converged_reason']}, "
                f"{row['diagnostics']['iterations']} its)",
                flush=True,
            )
        print(
            f"        {'':<36} {'coarse h':>10} {'fine h':>10} {'delta pp':>10} "
            f"{'ratio':>8}",
            flush=True,
        )
        for label in identities:
            print(
                f"        {label:<36} "
                f"{STEP3D_RESTRICTED_IDENTITY_RECORDS[label] * 100:9.4f}% "
                f"{identities[label] * 100:9.4f}% {deltas_pp[label]:+9.4f} "
                f"{ratios[label]:8.4f}   PRINTED NOT GATED",
                flush=True,
            )
        for label in controls:
            print(
                f"        {label:<36} "
                f"{STEP3D_RESTRICTED_CONTROL_RECORDS[label] * 100:9.4f}% "
                f"{controls[label] * 100:9.4f}% "
                f"{(controls[label] - STEP3D_RESTRICTED_CONTROL_RECORDS[label]) * 100:+9.4f} "
                f"{'':>8}   control, ASSERTED > band",
                flush=True,
            )
        print(
            f"    [step 3f'] (A) the SAME eight identities on step 1c's "
            f"rotation-invariant RING set: {ring_points.shape[0]} points "
            f"({ring_b1_valid} valid in every image) about the coil axis, "
            f"against the {points.shape[0]} tag-3 centroids above.  ASSERTED: "
            f"|ring - centroid| <= {RING_VS_CENTROID_CEILING_PP:.1f} pp at every "
            f"one of the eight (step 1c's measured separation on the coarse DG0 "
            f"column):",
            flush=True,
        )
        print(
            f"        {'':<40} {'centroid':>10} {'ring':>10} {'delta pp':>10}",
            flush=True,
        )
        for label in STEP1B_CG1_RECORDS:
            print(
                f"        {'|B1+| ' + label:<40} {b1_table[label] * 100:9.4f}% "
                f"{ring_b1_table[label] * 100:9.4f}% "
                f"{ring_vs_centroid_pp['|B1+| ' + label]:+9.4f}",
                flush=True,
            )
        for label in identities:
            print(
                f"        {'SAR ' + label:<40} {identities[label] * 100:9.4f}% "
                f"{ring_identities[label] * 100:9.4f}% "
                f"{ring_vs_centroid_pp['SAR ' + label]:+9.4f}",
                flush=True,
            )
        print(
            f"        {'|B1+| P3@+90deg (mis-rotated)':<40} "
            f"{b1_table['P3@+90deg'] * 100:9.4f}% "
            f"{ring_b1_table['P3@+90deg'] * 100:9.4f}%      control, ASSERTED > band",
            flush=True,
        )
        for label in ring_controls:
            print(
                f"        {'SAR ' + label:<40} {controls[label] * 100:9.4f}% "
                f"{ring_controls[label] * 100:9.4f}%      control, ASSERTED > band",
                flush=True,
            )
        print(
            f"    [step 3f'] (B) anchor (i) is now ONE-SIDED: an identity may "
            f"not exceed its coarse record by more than "
            f"{COIL_SIDE_MOVE_CEILING_PP:.1f} pp (a fall is the convergence "
            f"measurement); the fine readings are recorded BESIDE the coarse "
            f"ones at rtol {CG1_RECORD_RTOL:.0e}, replacing nothing:",
            flush=True,
        )
        for label, record in STEP3F_B1_PLUS_FINE_RECORDS.items():
            print(
                f"        {label:<12} {b1_table[label] * 100:9.4f}%   fine record "
                f"{record * 100:7.4f}%   coarse record "
                f"{STEP1B_CG1_RECORDS[label] * 100:7.4f}%   one-sided ceiling "
                f"{(STEP1B_CG1_RECORDS[label] + COIL_SIDE_MOVE_CEILING_PP / 100.0) * 100:7.4f}%",
                flush=True,
            )
        print(
            f"    [step 3f'] (C) step 3g/3h's INTEGRAL construction on this mesh "
            f"— primal N1curl E, no projection, no estimator, no sample set; "
            f"quadrature_degree {QUADRATURE_DEGREE}, eps {PARTITION_EPS_M:.0e} m "
            f"(imported).  P_j^(k) = 1/2 int_tag3 sigma w_j |E^(k)|^2 dV [W]:",
            flush=True,
        )
        for k in range(4):
            row = "  ".join(f"{v:.9e}" for v in integral_quadrants[k])
            print(
                f"        k={k} ({by_k[k]})  {row}   sum "
                f"{sum(integral_quadrants[k]):.9e}   total "
                f"{integral_totals[k]:.9e}",
                flush=True,
            )
        print(
            f"    (iv) partition identity ASSERTED at rtol {PARTITION_RTOL:.0e} for "
            f"all four drives; the P1 total against this mesh's primal phantom "
            f"power record {STEP3F_FINE_PRIMAL_PHANTOM_POWER_W:.9e} W at rtol "
            f"{CG1_RECORD_RTOL:.0e}\n"
            f"    the twelve C4 integral pairs |P_(j+1)^(k+1) - P_j^(k)| / P_j^(k) "
            f"on the FINER phantom — PRINTED NOT GATED (step 3h owns the gate, at "
            f"fixed h; coarse-mesh record in parentheses):",
            flush=True,
        )
        for k in range(3):
            row = "  ".join(
                f"{integral_pairs[(k, j)] * 100:7.4f}% "
                f"({STEP3G_INTEGRAL_PAIR_RECORDS[(k, j)] * 100:6.4f})"
                for j in range(4)
            )
            print(
                f"        k={k}->{k + 1}  {row}   mis-paired control mean "
                f"{np.mean([integral_control_pairs[(k, j)] for j in range(4)]) * 100:9.4f}%",
                flush=True,
            )
        print(
            f"    [step 3f'] PRE-REGISTERED INTEGRAL VERDICT: {integral_verdict} — "
            f"{integral_verdict_text}",
            flush=True,
        )
        print(
            f"    PRE-REGISTERED VERDICT: {verdict} — {verdict_text}\n"
            f"    restricted phantom power 1/2*int(sigma|E_O|^2) = "
            f"{phantom_power_w:.9e} W vs this mesh's PRIMAL "
            f"{primal_phantom_power_w:.9e} W "
            f"({(phantom_power_w / primal_phantom_power_w - 1.0) * 100:+.4f}%); the "
            f"coarse mesh read {STEP3D_RESTRICTED_PHANTOM_POWER_W:.9e} W restricted "
            f"against a primal {STEP1_GATE_I_P1_PHANTOM_POWER_W:.9e} W "
            f"(-3.5058%) — ALL PRINTED, NOT GATED: an L2 projection does not "
            f"conserve power and two meshes do not share a primal record.\n"
            "    SCOPE: no band moved, NO SAR GATE IS REGISTERED, no homogeneity / "
            "absolute / C95.3 claim, WF-6 stays yellow whichever clause printed.",
            flush=True,
        )

    return {
        "sweep": sweep,
        "cells": cells,
        "phantom_cells": phantom_cells,
        "points": points,
        "n_points": int(points.shape[0]),
        "b1_valid": int(b1_mask.sum()),
        "shares": shares,
        "b1_table": b1_table,
        "diagnostics": diagnostics,
        "control_fields": control_fields,
        "restricted_residual": restricted_residual,
        "global_residual": global_residual,
        "identities": identities,
        "controls": controls,
        "deltas_pp": deltas_pp,
        "ratios": ratios,
        "phantom_power_w": phantom_power_w,
        "primal_phantom_power_w": primal_phantom_power_w,
        "verdict": verdict,
        "verdict_text": verdict_text,
        "ring_points": int(ring_points.shape[0]),
        "ring_b1_valid": ring_b1_valid,
        "ring_b1_table": ring_b1_table,
        "ring_identities": ring_identities,
        "ring_controls": ring_controls,
        "ring_vs_centroid_pp": ring_vs_centroid_pp,
        "integral_totals": integral_totals,
        "integral_quadrants": integral_quadrants,
        "integral_pairs": integral_pairs,
        "integral_control_pairs": integral_control_pairs,
        "integral_verdict": integral_verdict,
        "integral_verdict_text": integral_verdict_text,
        "p1_slot": indices["P1"],
    }


RING_COMPARISON_LABELS = tuple(f"|B1+| {label}" for label in STEP1B_CG1_RECORDS) + tuple(
    f"SAR {label}" for label in STEP3D_RESTRICTED_IDENTITY_RECORDS
)


@complex_only
def test_the_sweep_ran_on_step_3f0s_finer_phantom_mesh(fine_phantom):
    """Anchor (iii): 120 499 cells, 2 746 of them tag 3, at exact equality.

    This is the anchor that the knob reached the constructor.  ``build_four_port_
    sweep`` ignores ``phantom_resolution`` under ``reuse=`` (it builds no mesh
    then), and a passthrough dropped anywhere in ``_build`` →
    ``birdcage_port_domain`` would silently rebuild the 116 085-cell default —
    at which point every column below would be step 3e's, re-printed under a
    new heading and read as an h rung.  gmsh is deterministic for a fixed
    input, so the bound is equality and not a band.  The tag-3 count is
    ``size_local``-restricted and ``MPI.SUM``-reduced (the reason for ``-n 2``).
    """
    assert (fine_phantom["cells"], fine_phantom["phantom_cells"]) == (
        FINE_CELL_COUNT,
        FINE_PHANTOM_CELL_COUNT,
    ), (
        f"the sweep meshed to {fine_phantom['cells']} cells with "
        f"{fine_phantom['phantom_cells']} in tag 3, not step 3f0's "
        f"{FINE_CELL_COUNT} / {FINE_PHANTOM_CELL_COUNT} (the coarse default is "
        f"{DEFAULT_CELL_COUNT} / {DEFAULT_PHANTOM_CELL_COUNT}) — if these are the "
        "coarse numbers the phantom_resolution passthrough did not reach the "
        "constructor and this module is not an h rung at all"
    )
    assert fine_phantom["n_points"] >= MIN_SAMPLE_POINTS, (
        f"only {fine_phantom['n_points']} sample points — below step 1's floor of "
        f"{MIN_SAMPLE_POINTS}, at which the identities stop being map readings"
    )


@complex_only
def test_power_accounting_still_closes_on_the_finer_phantom(fine_phantom):
    """Anchor (i), first half: gate (i)'s conservation identity, band unmoved.

    The domain is PEC-walled, so real power supplied at the driven sheet has
    nowhere to go but the phantom, the conductor and the four sheets — a
    statement about the physics, not about the mesh, and therefore one a finer
    phantom must not break.  The negative control (drop the conductor term) is
    asserted with it, exactly as in step 1: an identity that closes without a
    term it is supposed to weigh is not weighing anything.
    """
    for pid, sh in fine_phantom["shares"].items():
        supplied = sh["supplied"]
        assert supplied > 0.0, (
            f"[{pid}] the driven sheet supplies {supplied:.9e} W on the finer mesh"
        )
        total = sh["phantom"] + sh["conductor"] + sh["sheet_total"]
        residual = abs(supplied - total) / abs(supplied)
        assert residual <= POWER_BALANCE_BAND, (
            f"[{pid}] on the finer phantom ({FINE_PHANTOM_CELL_COUNT} tag-3 cells) "
            f"power accounting misses by {residual:.6e} of the supplied "
            f"{supplied:.9e} W (phantom {sh['phantom']:.9e}, conductor "
            f"{sh['conductor']:.9e}, sheets {sh['sheet_total']:.9e}); band "
            f"{POWER_BALANCE_BAND:.0e}, unmoved — a coil-side gate that moves with "
            "the phantom's h is a fixture finding, not a band to widen"
        )
        blind = abs(supplied - (total - sh["conductor"])) / abs(supplied)
        assert blind > POWER_BALANCE_BAND, (
            f"[{pid}] dropping the conductor term still closes to {blind:.6e}, "
            f"inside the {POWER_BALANCE_BAND:.0e} band"
        )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP1B_CG1_RECORDS))
def test_the_b1_plus_c4_identities_do_not_move_with_the_phantom_h(fine_phantom, label):
    """Anchor (i), second half: the ``|B₁⁺|`` gate reads the same on the new mesh.

    Gate (ii) is the CG1 C4 covariance identity at +90 / −90 / 180°, recorded at
    2.1870 / 2.1146 / 1.8911% on the coarse mesh.  Those records were measured
    on a *different* discretisation, so they cannot be reproduced at
    ``CG1_RECORD_RTOL`` here — what is asserted is the band itself (unmoved,
    imported) and that the identity does not get **worse** than its coarse
    record by more than 0.5 pp.

    **Step 3f′ made this anchor one-sided, and that is the whole change.**  As
    written for step 3f it was two-sided (``|reading − record| ≤ 0.5 pp``), on
    the hypothesis that these figures were mesh-converged at a ~2% floor.  The
    rung measured that hypothesis to be false in the *favourable* direction —
    2.1870 / 2.1146 / 1.8911% → 0.6177 / 0.5966 / 0.5647%, −1.57 / −1.52 /
    −1.33 pp, a 3.5× fall at all three angles at once — which is a
    discretisation floor still falling with ``h``, i.e. the convergence
    measurement the rung exists to make, not a gate miss.  The 2026-09-02 18:00
    review ruled the anchor one-sided on exactly that reading: *an identity may
    not get worse*, and a fall is recorded (``STEP3F_B1_PLUS_FINE_RECORDS``,
    asserted separately) rather than flagged.  The ceiling itself is **not**
    widened, the band is **not** moved, and a reading *above* the coarse record
    by more than 0.5 pp is still a fixture finding to be journalled.
    """
    reading = fine_phantom["b1_table"][label]
    record = STEP1B_CG1_RECORDS[label]
    assert reading <= C4_COVARIANCE_BAND, (
        f"on the finer phantom the CG1 |B1+| identity '{label}' reads "
        f"{reading * 100:.4f}%, outside the imported "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band (coarse record "
        f"{record * 100:.4f}%) — the coil-side gate does not survive the rung"
    )
    move_pp = (reading - record) * 100.0
    assert move_pp <= COIL_SIDE_MOVE_CEILING_PP, (
        f"the CG1 |B1+| identity '{label}' gets WORSE by {move_pp:.4f} pp (from "
        f"{record * 100:.4f}% to {reading * 100:.4f}%) when the phantom's h is "
        f"halved, above the pre-registered {COIL_SIDE_MOVE_CEILING_PP:.1f} pp — "
        "an identity that degrades under refinement is a fixture finding and "
        "not a licence to widen this ceiling (a fall is the convergence "
        "measurement and is recorded, not flagged)"
    )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3F_B1_PLUS_FINE_RECORDS))
def test_the_fine_rung_b1_plus_readings_reproduce_their_records(fine_phantom, label):
    """Step 3f′ (B): the fine-rung ``|B₁⁺|`` figures, recorded beside the coarse.

    0.6177 / 0.5966 / 0.5647% is what this mesh reads.  Recording it is what
    turns the one-sided anchor above from a weakening into a bookkeeping move:
    the fall is now a *number the suite asserts*, so a later change that quietly
    put the identities back at 2% — or moved them anywhere else — is visible
    rather than absorbed by the one-sidedness.  ``STEP1B_CG1_RECORDS`` is
    untouched and still the coarse mesh's.
    """
    reading = fine_phantom["b1_table"][label]
    record = STEP3F_B1_PLUS_FINE_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"the fine-rung CG1 |B1+| identity '{label}' reads {reading * 100:.4f}%, "
        f"not step 3f's recorded {record * 100:.4f}% at rtol "
        f"{CG1_RECORD_RTOL:.0e} — the mesh, the image or the four solves have "
        "moved under this rung; re-record only under the (1*) licence"
    )


@complex_only
def test_the_b1_plus_control_still_resolves_the_drive_azimuth(fine_phantom):
    """The coil-side negative control: the mis-rotated P3 stays outside the band.

    A finer phantom that smoothed the 180°-away drive into the band would make
    the three identities above pass on a map with no azimuthal structure left.
    """
    control = fine_phantom["b1_table"]["P3@+90deg"]
    assert control > C4_COVARIANCE_BAND, (
        f"on the finer phantom the mis-rotated |B1+| control (P3 at +90deg) "
        f"matches the P1 map to {control * 100:.4f}%, inside the "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band"
    )


@complex_only
def test_the_restricted_fit_beats_the_global_one_on_this_mesh(fine_phantom):
    """Anchor (ii): the **same-mesh** best-approximation inequality.

    ``P_Ω E`` minimises ``‖· − E‖_{L²(Ω)}`` over all of ``CG1³``, and the global
    projection ``P E`` of the *same* field restricted to Ω is one member of that
    set, so ``‖P_Ω E − E‖_Ω ≤ ‖P E − E‖_Ω`` holds by construction — no mesh, no
    fixture and no physics enters.  Both numbers are measured in this run on
    this mesh, which is the whole point: the 2026-09-02 10:30 review struck the
    scoping's "≤ the coarse mesh's 18.7238%" because that compares two different
    meshes' primal fields and is not a theorem.  A violation here is a defect in
    the restriction (pinning, measure, a non-converged solve), never a statement
    about SAR.
    """
    restricted = fine_phantom["restricted_residual"]
    global_fit = fine_phantom["global_residual"]
    assert restricted <= global_fit, (
        f"on the finer mesh the phantom-restricted projection leaves "
        f"{restricted * 100:.4f}% over the phantom, ABOVE the same-mesh global "
        f"fit's {global_fit * 100:.4f}% on the same cells — the restricted fit "
        "minimises that very norm over a space containing the global fit's "
        "restriction, so this is a bug in the restriction, not a finding about "
        "SAR or about the phantom's h"
    )


@complex_only
def test_the_restricted_projector_reproduces_a_field_both_spaces_contain(fine_phantom):
    """Anchor (ii): ``P_Ω(a + b × x) = a + b × x`` on the new mesh, to 1e-10.

    ``a + b × x`` spans the lowest-order Nédélec element exactly and lies in
    ``CG1³``, so its restricted L² projection must return it to solver
    tolerance on *any* mesh.  A miss means the restricted operator is not a
    projection on this mesh — a mis-tagged measure or a pin that swallowed a dof
    the phantom needs — and every reading in the column is a reading of nothing.
    """
    residual = fine_phantom["control_fields"]["a + b x x"]["residual"]
    assert residual <= PROJECTOR_EXACT_RESIDUAL, (
        f"on the finer mesh the phantom-restricted projection of f = a + b x x — "
        f"in N1curl_1 AND in CG1^3 — leaves a relative L2 residual of "
        f"{residual:.6e} over the phantom, above {PROJECTOR_EXACT_RESIDUAL:.0e}"
    )


@complex_only
def test_the_restricted_projector_control_field_is_not_reproduced(fine_phantom):
    """The control's control: ``x² ê_x`` must still leave a visible residual.

    Without it, a restricted "projection" that returned its own argument — or a
    residual helper reading zero over a mis-tagged empty measure — would pass
    the exact-reproduction test above and prove nothing.  The floor stays the
    arithmetic ``(h/D)² ≳ 1e-4``: halving ``h`` quarters that quantity, and
    1e-4 was already two orders below the coarse mesh's 3.741459e-01 reading.
    """
    residual = fine_phantom["control_fields"]["x^2 e_x"]["residual"]
    assert residual > RESTRICTED_CONTROL_MIN_RESIDUAL, (
        f"the control field x^2 e_x restricted-projects with a relative L2 "
        f"residual of only {residual:.6e} over the finer phantom — below the "
        f"arithmetic floor {RESTRICTED_CONTROL_MIN_RESIDUAL:.0e}, at which the "
        "exact-reproduction test beside it is not measuring anything"
    )


@complex_only
def test_every_cg1_dof_outside_the_phantom_is_pinned_to_exactly_zero(fine_phantom):
    """Anchor (ii): the pin is a pin at the new dof count, owned **and** ghost.

    The finer phantom has its own dofmap and its own partition cut.  If the
    complement were taken over owned blocks only, the ghost rows across that cut
    would keep whatever the Krylov solve left in them and the two-rank answer
    would differ from the one-rank one.  ``set_bc`` writes an exact zero, so the
    bound is 0 and not a tolerance.
    """
    pinned_max = fine_phantom["diagnostics"]["P1"]["pinned_max_abs"]
    assert pinned_max <= RESTRICTED_PINNED_DOF_MAX, (
        f"a CG1 dof with no phantom-cell support holds {pinned_max:.6e} after the "
        "restricted solve on the finer mesh — the zero Dirichlet pin did not "
        "reach every block"
    )


@complex_only
@pytest.mark.parametrize("label", RESTRICTED_SOLVE_LABELS)
def test_every_restricted_mass_solve_converges(fine_phantom, label):
    """Anchor (ii): all six restricted mass solves converged on the new mesh.

    The restricted matrix is the phantom mass matrix bordered by an identity
    block — SPD, so CG with Jacobi is the right solver — but 5.1× as many free
    blocks changes its conditioning, and ``LinearProblem.solve()`` does not raise
    on a non-converged KSP.  The iteration count is *reported*, not gated: no
    record exists for this mesh and inventing one in-slot would be a band this
    step is not allowed to move.
    """
    diag = fine_phantom["diagnostics"][label]
    assert diag["converged_reason"] > 0, (
        f"the restricted CG1 mass solve for '{label}' on the finer mesh returned "
        f"PETSc converged reason {diag['converged_reason']} after "
        f"{diag['iterations']} iterations on {diag['dofs']} dofs — record it, do "
        "not raise the iteration cap"
    )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3D_RESTRICTED_CONTROL_RECORDS))
def test_the_negative_controls_survive_the_finer_phantom(fine_phantom, label):
    """The negative control the whole rung rests on: both controls stay outside.

    The mis-rotated drive and the quadrature-vs-single-drive comparison read
    123.6255% and 333.0778% on the coarse mesh.  A finer phantom that brought
    either *inside* 5% would mean the refinement had erased the azimuthal
    structure the identities claim to measure — and clause (a) of the
    pre-registered verdict would then be an artefact, not a gate-able reading.
    That is itself the finding, not a licence to read the column beside it.
    """
    control = fine_phantom["controls"][label]
    assert control > CONTROL_MIN_MISMATCH, (
        f"on the finer phantom the restricted control '{label}' reads "
        f"{control * 100:.4f}%, inside the {CONTROL_MIN_MISMATCH * 100:.1f}% band "
        f"(the coarse mesh reads "
        f"{STEP3D_RESTRICTED_CONTROL_RECORDS[label] * 100:.4f}%) — the rung has "
        "smoothed away the structure the identities measure, so no identity "
        "reading here is interpretable"
    )


@complex_only
def test_the_five_identities_are_printed_with_a_pre_registered_verdict(fine_phantom):
    """The deliverable: the verdict clause is one of the pre-registered ones.

    The five identities are **printed, not gated** — this step registers no SAR
    gate under any clause, and the assertion here is only that the module
    classified its own readings into the pre-registration rather than leaving a
    reviewer to eyeball a table.  ``(none)`` is a legitimate measured outcome
    and is *not* asserted away; it fails here only if the verdict machinery
    returned something outside the four labels it can produce.
    """
    assert fine_phantom["verdict"] in {"(a)", "(b)", "(c)", "(none)"}, (
        f"the verdict machinery returned {fine_phantom['verdict']!r}"
    )
    assert set(fine_phantom["identities"]) == set(STEP3D_RESTRICTED_IDENTITY_RECORDS), (
        "the identity labels have drifted from the coarse-mesh records, so the "
        "delta and ratio columns are not comparing the same five quantities"
    )


@complex_only
@pytest.mark.parametrize("label", sorted(STEP3F_RESTRICTED_FINE_IDENTITY_RECORDS))
def test_the_five_fine_identities_reproduce_step_3fs_records(fine_phantom, label):
    """Step 3f′ anchor (iii): the printed column of step 3f has not moved.

    3.3600 / 3.4442 / 3.4525 / 3.0332 / 2.5465%, from step 3f's own log.  They
    stay **printed, not gated** — no SAR gate is registered on this
    construction, and step 3h put the repo's only coil-driven SAR gate on the
    *integral* one — but a printed column that nothing pins is a column that
    can drift while three additions are bolted to the fixture around it.  This
    is a reproduction, not a band: a miss is a fixture finding.
    """
    reading = fine_phantom["identities"][label]
    record = STEP3F_RESTRICTED_FINE_IDENTITY_RECORDS[label]
    assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
        f"the fine-rung restricted-CG1 identity '{label}' reads "
        f"{reading * 100:.4f}%, not step 3f's recorded {record * 100:.4f}% at "
        f"rtol {CG1_RECORD_RTOL:.0e}"
    )


@complex_only
def test_the_estimator_diagnostics_reproduce_step_3fs_records(fine_phantom):
    """Step 3f′ anchor (iii), the single-figure half of the same statement.

    The same-mesh best-approximation pair (12.5225% ≤ 1626.2098%), the affine
    reproduction residual (9.947634e-13) and this mesh's primal phantom power
    (5.587038273e-08 W).  The inequality itself is a theorem and is asserted
    separately above; what is asserted here is that the two sides of it, and the
    two other figures the fine rung is quoted by, are the numbers step 3f
    measured.  The affine residual is a Krylov quantity but a deterministic one
    at a fixed mesh, partition and rank count.
    """
    for name, reading, record in (
        ("restricted residual", fine_phantom["restricted_residual"],
         STEP3F_FINE_RESTRICTED_RESIDUAL),
        ("same-mesh global residual", fine_phantom["global_residual"],
         STEP3F_FINE_GLOBAL_RESIDUAL),
        ("affine reproduction residual",
         fine_phantom["control_fields"]["a + b x x"]["residual"],
         STEP3F_FINE_AFFINE_RESIDUAL),
        ("primal phantom power [W]", fine_phantom["primal_phantom_power_w"],
         STEP3F_FINE_PRIMAL_PHANTOM_POWER_W),
    ):
        assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
            f"the fine rung's {name} reads {reading:.6e}, not step 3f's recorded "
            f"{record:.6e} at rtol {CG1_RECORD_RTOL:.0e} — a record of this rung "
            "moved, which is a fixture finding and not something to re-record "
            "in-slot"
        )


@complex_only
@pytest.mark.parametrize("label", RING_COMPARISON_LABELS)
def test_the_ring_set_agrees_with_the_centroid_set(fine_phantom, label):
    """Step 3f′ anchor (i): the sample set is not the mechanism on this rung.

    The rung halves the phantom's ``h``, and the centroid sample set is built
    from that same mesh — so it grew 51 → 373 points with the refinement, and
    every reading above moves *two* things at once.  Step 1c separated them for
    the coarse DG0 ``|B₁⁺|`` column with a rotation-invariant ring set built
    from constants (96 points, closed under the rotation, identical on every
    rank) and measured the two sample sets to agree within ±2 pp.  That measured
    separation is the bar here, imported as a number and applied to all eight
    identities on this mesh.

    A disagreement larger than 2 pp is **the finding**: it would mean the
    sample set is a mechanism at this ``h``, and the ``h``-attribution of the
    whole rung would then be unavailable until a review rules.  It is not a band
    on either reading and nothing about it may be widened.
    """
    delta_pp = fine_phantom["ring_vs_centroid_pp"][label]
    assert abs(delta_pp) <= RING_VS_CENTROID_CEILING_PP, (
        f"on the finer phantom the identity '{label}' reads {delta_pp:+.4f} pp "
        f"differently on step 1c's {fine_phantom['ring_points']}-point ring set "
        f"than on the mesh's {fine_phantom['n_points']} tag-3 centroids, outside "
        f"step 1c's measured ±{RING_VS_CENTROID_CEILING_PP:.1f} pp — the sample "
        "set IS a mechanism on this rung, so the h-attribution of every column "
        "above is confounded; journal it, do not widen this"
    )


@complex_only
def test_the_negative_controls_survive_on_the_ring_set_too(fine_phantom):
    """Step 3f′: all three negative controls, re-read on the ring set.

    The centroid set reads 25.4563% (mis-rotated ``|B₁⁺|``) and 121.0800% /
    384.1297% (the two SAR controls).  A ring set on which the controls had
    collapsed into the band would make the eight agreement readings beside them
    agreements about nothing.
    """
    control = fine_phantom["ring_b1_table"]["P3@+90deg"]
    assert control > C4_COVARIANCE_BAND, (
        f"on the ring set the mis-rotated |B1+| control (P3 at +90deg) matches "
        f"the P1 map to {control * 100:.4f}%, inside the "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band"
    )
    for label, reading in fine_phantom["ring_controls"].items():
        assert reading > CONTROL_MIN_MISMATCH, (
            f"on the ring set the restricted SAR control '{label}' reads "
            f"{reading * 100:.4f}%, inside the {CONTROL_MIN_MISMATCH * 100:.1f}% "
            "band — the ring set has no azimuthal structure left to measure"
        )


@complex_only
@pytest.mark.parametrize("k", [0, 1, 2, 3])
def test_the_integral_partition_recovers_the_phantom_power_on_this_mesh(
    fine_phantom, k
):
    """Step 3f′ anchor (iv): ``Σ_j P_j = P_phantom`` on the finer mesh, exactly.

    ``Σ_j w_j = 1`` pointwise, so the four weighted integrals and the unweighted
    one are the same quadrature sum re-associated — arithmetic, not physics, and
    therefore asserted at round-off before the twelve pairs beside it are looked
    at.  A miss at 1e-10 on *this* mesh would say the imported construction did
    not survive the change of mesh (a measure that is not this phantom's, a
    reduction that did not happen on some rank), which would make the printed
    column below uninterpretable.
    """
    parts = fine_phantom["integral_quadrants"][k]
    total = fine_phantom["integral_totals"][k]
    assert total > 0.0, f"the phantom power for drive k={k} is {total!r} — no solve"
    assert sum(parts) == pytest.approx(total, rel=PARTITION_RTOL), (
        f"on the finer phantom the four quadrant integrals for drive k={k} sum to "
        f"{sum(parts):.12e} W but the whole phantom reads {total:.12e} W "
        f"(relative miss {abs(sum(parts) / total - 1.0):.3e} against "
        f"{PARTITION_RTOL:.0e})"
    )


@complex_only
def test_the_integral_p1_total_reproduces_this_meshs_primal_phantom_power(
    fine_phantom,
):
    """Step 3f′ anchor (iv): the integral column is reading the same field.

    ``½∫_{tag 3} σ|E^{(P1)}|²`` assembled by the partition helper at
    ``quadrature_degree`` 4 against the same quantity assembled independently by
    ``post.mean_sar`` in this fixture — and against step 3f's record for it,
    5.587038273e-08 W.  Two different assemblies of one integral: if they
    disagreed, the twelve pairs printed beside them would be pairs of some other
    quantity.
    """
    p1_total = fine_phantom["integral_totals"][fine_phantom["p1_slot"]]
    assert p1_total == pytest.approx(
        fine_phantom["primal_phantom_power_w"], rel=CG1_RECORD_RTOL
    ), (
        f"the partition's P1 total {p1_total:.9e} W disagrees with mean_sar's "
        f"{fine_phantom['primal_phantom_power_w']:.9e} W on the same primal field "
        f"and the same tag-3 cells, at rtol {CG1_RECORD_RTOL:.0e}"
    )
    assert p1_total == pytest.approx(
        STEP3F_FINE_PRIMAL_PHANTOM_POWER_W, rel=CG1_RECORD_RTOL
    ), (
        f"the partition's P1 total {p1_total:.9e} W is not step 3f's recorded "
        f"{STEP3F_FINE_PRIMAL_PHANTOM_POWER_W:.9e} W for this mesh at rtol "
        f"{CG1_RECORD_RTOL:.0e}"
    )


@complex_only
def test_the_integral_pairs_on_this_mesh_are_printed_with_a_pre_registered_verdict(
    fine_phantom,
):
    """Step 3f′ (C): step 3h's gate gets its first ``h`` data point — printed.

    Step 3h registered the twelve C4 integral pairs as the repo's first
    coil-driven SAR gate **at fixed h** (worst 1.5200% inside a 5% band).  This
    module forms the same twelve on a mesh whose phantom is meshed at half the
    cell size and prints them against that record under a pre-registered clause:
    (a) worst ≤ 1.5200% ⇒ the headroom does not shrink with ``h``; (b) between
    that and 5% ⇒ report, and the *next review* restates the headroom from the
    larger figure; (c) above 5% ⇒ the construction is not ``h``-stable, which is
    a known-issues entry against step 3h.

    **Nothing about the pairs is asserted here.**  Step 3h owns the gate; this
    step registers none, moves no band and re-records nothing.  What is asserted
    is only that the module classified its own readings into the
    pre-registration rather than leaving a reviewer to eyeball a table, and that
    the twelve pairs it classified are the twelve step 3g recorded.
    """
    assert fine_phantom["integral_verdict"] in {"(a)", "(b)", "(c)"}, (
        f"the integral verdict machinery returned "
        f"{fine_phantom['integral_verdict']!r}"
    )
    assert set(fine_phantom["integral_pairs"]) == set(STEP3G_INTEGRAL_PAIR_RECORDS), (
        "the (k, j) keys of the fine-mesh integral pairs differ from step 3g's "
        "coarse-mesh records, so the printed comparison is not comparing the "
        "same twelve quantities"
    )
