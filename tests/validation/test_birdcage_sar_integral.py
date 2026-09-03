"""`WF-6` step 3g — the coil-driven SAR identities read as **cell integrals**.

Steps 3–3f read the C4 identities *pointwise*, from ``σ|E|²/(2ρ)`` sampled at
the phantom's own tag-3 centroids.  Three candidate mechanisms for the 25–41%
primal miss have been separated and excluded one at a time: the projector
(step 3c), the estimator's *degree* (step 3e′ — a strictly better L² fit reads
the identities *worse*), and finally the phantom's ``h`` (step 3f — halving it
brings the restricted-estimator column inside the band).  What none of those
rungs touched is the **construction**: an identity read from a field at sampled
points inherits that field's pointwise error, squared.

This module turns the identity into an integral instead, and so needs no
estimator at all — the **primal N1curl ``E``** is integrated directly.  Let the
coil axis be ``z`` and ``θ_j = jπ/2``.  With

    ``c_j(x) = (x cos θ_j + y sin θ_j) / √(x² + y² + ε²)``,
    ``w_j(x) = ((c_j + √(c_j² + ε²)) / 2)²``,   ``ε = 1e-9 m``,

only the two adjacent ``w_j`` are non-zero at any point and they sum to
``cos² + sin² = 1``, so ``Σ_j w_j ≡ 1`` and — because the four directions are
exactly 90° apart — ``w_{j+1}(x) = w_j(R⁻¹x)`` under the 90° rotation ``R``.
The regularised ``sqrt`` is not decoration: ``ufl.max_value`` and every
ordering predicate are the `OPS-22` complex-build trap, and this form is
smooth, ordering-free and exact to O(ε²).

Read ``P_j^{(k)} = ½ ∫_{dx(3)} σ w_j |E^{(k)}|² dx`` for the four single drives
``k`` and the four quadrants ``j`` — sixteen cell integrals of the primal
field, ``assemble_scalar`` MPI-reduced, ``quadrature_degree`` pinned (the
integrand carries ``SpatialCoordinate``, `POST-5`) — plus the same four for the
step-2 quadrature drive.

**The identity being tested.**  Rotating the drive one port rotates the whole
problem: ``|E^{(k+1)}(Rx)| = |E^{(k)}(x)|`` — the very statement step 3's
``SAR_P2(Rx) vs SAR_P1(x)`` pairing makes, whose rotation sense is imported
from that module and **never re-derived here**.  Change variables in the
integral and the pointwise statement becomes

    ``P_{j+1}^{(k+1)} = P_j^{(k)}``   (twelve pairs, k = 0,1,2; j = 0..3)

with no sample set, no estimator and no projection anywhere in it.

**Anchors, asserted.**

* **(i) the partition identity** ``Σ_j P_j^{(k)} = P_phantom^{(k)}`` at rtol
  1e-10, for all five drives.  ``Σ_j w_j = 1`` holds *pointwise*, hence at
  every quadrature point of every cell, so this is an identity of the
  construction and not a physical claim: a miss is a defect in the integrals
  (a wrong measure, a dropped reduction, a partition that does not partition),
  which is exactly why it is asserted first and tightly.  The gate-(i) drive's
  total additionally reproduces step 1's phantom-power record
  **5.637745667e-08 W** at ``CG1_RECORD_RTOL`` — the tie between this module's
  integrals and step 1's gated three-way power accounting.
* **(ii) the mis-paired negative control**, pairing quadrant ``j`` under drive
  ``k`` with quadrant ``j+2`` (180°) under drive ``k+1``, reads **strictly
  larger** than the C4 pairing for every ``k``.  An *ordering*, not a factor:
  nobody has measured this ceiling, and pre-registering a size for it would be
  inventing a number.  The ratio is printed.

**The gate (step 3h, 2026-09-02 18:00 review).**  The twelve C4 pairs
``|P_{j+1}^{(k+1)} − P_j^{(k)}| / P_j^{(k)}`` and the quadrature drive's
four-quadrant spread are **asserted** ``≤ C4_COVARIANCE_BAND`` — the 5% band
imported from step 1d, unmoved — one parametrised test per pair, so a miss
names its ``(k, j)``.  They are additionally asserted against step 3g's
measured table (:data:`STEP3G_INTEGRAL_PAIR_RECORDS`) at ``CG1_RECORD_RTOL``,
so a mesh or image move is visible as itself rather than as a band miss.

This is the **first coil-driven SAR gate in the repo**, and it is exactly one
thing: *a C4 symmetry identity of quadrant powers on one fixture at 10 MHz at
fixed* ``h``.  Not an absolute SAR figure, not homogeneity, not C95.3, not
Larmor, not a convergence claim.  `WF-6` step 3 is ✅ with this module; the
chunk stays 🟡.

**The second identity (step 3i, 2026-09-03 03:00 review).**  The mirror through
the coil axis and drive ``k``'s own azimuth fixes quadrants ``k`` and ``k+2``
and exchanges the two flanks, so ``P_{k−1}^{(k)} = P_{k+1}^{(k)}`` for each of
the four drives — asserted against the *same* imported band, one parametrised
test per ``k``, recorded in :data:`STEP3I_MIRROR_RECORDS`, with the
flank-vs-opposite pairing as its negative control.  It runs on the same four
solves and the same partition: **no new solve, no new partition, no new band.**
Unlike the twelve C4 pairs it is a single-drive statement, so it is independent
evidence rather than a re-reading of the rotation identity.

The verdict below is kept as the printed pre-registration the 2026-09-02 10:30
review wrote, so the reading a review acts on stays visible beside the gate:

* **(a)** all ≤ 5% ⇒ the *integral* construction is the gateable one, and a
  **review** — never this module and never the slot that runs it — registers
  the first coil-driven SAR gate on it;
* **(b)** between 5% and the pointwise primal 25–41% ⇒ report the improvement;
* **(c)** at or above the pointwise readings ⇒ the sample set was not the
  mechanism either, and the phantom's ``h`` (step 3f) is what decides.

**Scope.**  Two symmetry identities (C4 rotation, mirror reflection) — no band
moved, no absolute SAR claim, and `WF-6` stays 🟡.  Nothing under ``src/``.  The coarse **default** mesh
(116 085 cells) on purpose: this rung is independent of step 3f's finer one, so
that "integral vs pointwise" is the only thing that differs from step 3's
window.

Run (complex build required)::

    scripts/testing/run_and_log.sh WF-6-step3g "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 600 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_birdcage_sar_integral.py -v -s'"
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_phantom_resolution import DEFAULT_CELL_COUNT
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.validation.test_birdcage_b1_plus_map import (
    C4_COVARIANCE_BAND,
    CG1_RECORD_RTOL,
    _solve_driven,
)
from tests.validation.test_birdcage_b1_quadrature import (
    QUADRATURE_STEP_DEG,
    _port_index,
    quadrature_phase_weights,
)
from tests.validation.test_birdcage_sar_map import (
    STEP1_GATE_I_P1_PHANTOM_POWER_W,
    STEP3_PRIMAL_IDENTITY_RECORDS,
    _superpose_complex,
)
from tests.validation.test_port_birdcage_four_port import build_four_port_sweep
from tests.validation.test_port_birdcage_lumped_column import PHANTOM_CELL_TAG

# The regularisation of the azimuthal partition, in metres.  Two roles, both
# needing it small: it desingularises ``1/r`` on the coil axis (the phantom
# straddles it) and it replaces the forbidden ``max(c, 0)`` by a smooth
# ``(c + √(c² + ε²))/2``.  The partition then sums to ``r²/(r² + ε²)`` rather
# than 1, i.e. a relative defect of ``(ε/r)²`` — 1e-14 already at r = 0.3 mm,
# far under the 1e-10 the identity is asserted at, and its O(ε³) axis
# neighbourhood contributes nothing at all.
PARTITION_EPS_M = 1.0e-9

# ``Σ_j w_j = 1`` holds at every point, hence at every quadrature point of
# every cell whatever the rule: the partition identity is therefore exact in
# *arithmetic*, and 1e-10 is a round-off bound on a sum of five assembled
# doubles, not a physical tolerance.  Loosening it would be hiding a defect in
# the integrals.
PARTITION_RTOL = 1.0e-10

# ``|E|²`` is degree 2 for the lowest-order N1curl unknown; ``σ`` is DG0; ``w``
# is a bounded non-polynomial.  Degree 4 is two orders above the polynomial
# part.  It is pinned because the integrand carries ``SpatialCoordinate`` and
# UFL's degree estimation on a ``sqrt`` of one is neither cheap nor defined
# (`POST-5`); the value cannot move the partition identity — the same rule is
# used for the parts and for the whole.
QUADRATURE_DEGREE = 4

# The pointwise primal readings this construction is being compared against,
# imported from step 3's own table (25.1096 … 40.5462%).  They are the
# boundary of the pre-registered clause (b)/(c), never a band.
POINTWISE_PRIMAL_MIN = min(STEP3_PRIMAL_IDENTITY_RECORDS.values())
POINTWISE_PRIMAL_MAX = max(STEP3_PRIMAL_IDENTITY_RECORDS.values())

# Step 3g's measured table, `20260902T213441Z_WF-6-step3g.log:4689-4692`, keyed
# by the drive step ``k -> k+1`` and the reference quadrant ``j``.  These are
# **records**, not a band: the gate is ``<= C4_COVARIANCE_BAND`` (imported,
# unmoved) and these say in addition that the mesh, the image and the four
# solves have not moved underneath it.  A miss here with the band still met is
# a fixture finding — re-record only under the (1*) licence, never to make a
# run pass.  Stored as fractions, like the readings they are compared with.
STEP3G_INTEGRAL_PAIR_RECORDS = {
    (0, 0): 0.7149e-2,
    (0, 1): 1.1908e-2,
    (0, 2): 1.4417e-2,
    (0, 3): 0.9703e-2,
    (1, 0): 1.5200e-2,
    (1, 1): 0.2132e-2,
    (1, 2): 0.3377e-2,
    (1, 3): 0.9086e-2,
    (2, 0): 1.0569e-2,
    (2, 1): 0.8355e-2,
    (2, 2): 0.2780e-2,
    (2, 3): 0.2302e-2,
}

# The quadrature drive's four-quadrant spread ``(max - min)/mean`` from the same
# table, same licence.
STEP3G_INTEGRAL_QUADRATURE_SPREAD = 0.4641e-2

# Step 3i's mirror readings ``|P_{k+1}^{(k)} - P_{k-1}^{(k)}| / P_{k-1}^{(k)}``,
# keyed by the drive ``k``.  Pre-computed by the 2026-09-03 03:00 review from
# step 3h's own printed quadrant table
# (`20260903T003309Z_WF-6-step3h.log:4682-4685`) and re-derived by the slot that
# first asserted them: k=0 9.206062871e-09 vs 9.047490023e-09, k=1
# 9.096436124e-09 vs 8.959698063e-09, k=2 9.127154706e-09 vs 9.095881751e-09,
# k=3 9.106144177e-09 vs 9.019887150e-09.  Same licence as the C4 records above:
# a record, never a band, stored as fractions.
STEP3I_MIRROR_RECORDS = {
    0: 1.7527e-2,
    1: 1.5262e-2,
    2: 0.3438e-2,
    3: 0.9563e-2,
}


def _quadrant_weight(x, j, eps):
    """``w_j`` as a UFL expression on the mesh's spatial coordinate.

    Written with a regularised ``sqrt`` rather than ``max(c, 0)`` because
    ``ufl.max_value`` — and every ordering predicate — raises on complex
    operands in the complex DolfinX build (`OPS-22`).  The form here is smooth,
    ordering-free, and agrees with ``max(c, 0)²`` to O(ε²).
    """
    import ufl

    theta = j * np.pi / 2.0
    radius = ufl.sqrt(x[0] * x[0] + x[1] * x[1] + eps * eps)
    c = (x[0] * float(np.cos(theta)) + x[1] * float(np.sin(theta))) / radius
    return ((c + ufl.sqrt(c * c + eps * eps)) / 2.0) ** 2


def _quadrant_powers(e_complex, sigma_field, dx_phantom, comm):
    """``(P_total, [P_0 … P_3])`` for one drive, in watts, MPI-reduced.

    ``assemble_scalar`` returns this rank's share of the integral — a rank
    owning no phantom cell returns 0 — so every one of the five scalars is
    summed across the communicator before it is returned, let alone asserted
    on.  ``ufl.inner`` conjugates its second argument, so ``inner(E, E)`` is
    ``|E|²`` and the imaginary part is round-off.
    """
    import ufl
    from dolfinx.fem import assemble_scalar, form

    x = ufl.SpatialCoordinate(e_complex.function_space.mesh)
    density = 0.5 * sigma_field * ufl.inner(e_complex, e_complex)

    def integrate(integrand):
        local = complex(assemble_scalar(form(integrand * dx_phantom)))
        return float(np.real(comm.allreduce(local, op=MPI.SUM)))

    total = integrate(density)
    parts = [
        integrate(_quadrant_weight(x, j, PARTITION_EPS_M) * density) for j in range(4)
    ]
    return total, parts


def _integral_verdict(pairs, band):
    """The (a)/(b)/(c) clause, pre-registered by the 2026-09-02 10:30 review.

    Evaluated from the readings in a fixed precedence rather than read off the
    table by eye, so the line a review acts on cannot disagree with the numbers
    printed above it.  A pattern matching no clause is reported as such — the
    pre-registration is never stretched to cover it in-slot.
    """
    values = list(pairs.values())
    worst = max(values)
    if worst <= band:
        return "(a)", (
            f"all twelve C4 integral pairs are inside the {band * 100:.1f}% band "
            f"(worst {worst * 100:.4f}%) — the INTEGRAL construction is the "
            "gateable one"
        )
    if worst >= POINTWISE_PRIMAL_MIN:
        return "(c)", (
            f"the worst C4 integral pair reads {worst * 100:.4f}%, at or above "
            f"the pointwise primal readings ({POINTWISE_PRIMAL_MIN * 100:.4f}–"
            f"{POINTWISE_PRIMAL_MAX * 100:.4f}%) — integrating did not help, so "
            "the sample set was not the mechanism and the phantom's h (step 3f) "
            "is what decides"
        )
    return "(b)", (
        f"the twelve C4 integral pairs span {min(values) * 100:.4f}–"
        f"{worst * 100:.4f}%, outside the {band * 100:.1f}% band but below the "
        f"pointwise primal {POINTWISE_PRIMAL_MIN * 100:.4f}–"
        f"{POINTWISE_PRIMAL_MAX * 100:.4f}% — the integral form improves on the "
        "pointwise one without reaching the band; report and stop"
    )


@pytest.fixture(scope="module")
def sar_integral():
    """Twenty cell integrals of the primal ``E`` on the default coarse mesh.

    Four curl-curl solves and **no** mass solves: the point of this rung is
    that an integral identity needs no estimator, so nothing here is projected,
    fitted or sampled.  No ``phantom_resolution`` — this is deliberately step
    3's own 116 085-cell mesh, so "integral vs pointwise" is the only thing
    that differs from step 3's window.
    """
    import ufl

    sweep = build_four_port_sweep()
    msh = sweep["mesh"]
    comm = msh.comm
    cells = int(sweep["cells"])

    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    order = sorted(azimuths)
    solves = {pid: _solve_driven(sweep, pid) for pid in order}
    # ``_port_index`` asserts the sheets sit on the 90° grid; the partition's
    # exact covariance ``w_{j+1}(x) = w_j(R⁻¹x)`` needs precisely that grid.
    indices = {
        pid: _port_index(azimuths[pid], azimuths["P1"], QUADRATURE_STEP_DEG)
        for pid in order
    }
    by_k = {indices[pid]: pid for pid in order}

    dx_phantom = ufl.Measure(
        "dx",
        domain=msh,
        subdomain_data=sweep["cell_tags"],
        metadata={"quadrature_degree": QUADRATURE_DEGREE},
    )(PHANTOM_CELL_TAG)
    sigma_field = solves["P1"]["fields"].sigma_field

    totals, quadrants = {}, {}
    for k in range(4):
        pid = by_k[k]
        totals[k], quadrants[k] = _quadrant_powers(
            solves[pid]["fields"].e_complex, sigma_field, dx_phantom, comm
        )

    ks = [indices[pid] for pid in order]
    e_quadrature = _superpose_complex(
        [solves[pid]["fields"].e_complex for pid in order],
        quadrature_phase_weights(ks, "ccw"),
        name="E_quadrature_ccw",
    )
    quad_total, quad_parts = _quadrant_powers(
        e_quadrature, sigma_field, dx_phantom, comm
    )

    # The twelve C4 pairs.  The rotation sense is step 3's, imported: its
    # ``SAR_P2(Rx) vs SAR_P1(x)`` pairing says drive k+1 at Rx equals drive k at
    # x, and the change of variables turns that into P_{j+1}^{(k+1)} = P_j^{(k)}.
    pairs, control_pairs = {}, {}
    for k in range(3):
        for j in range(4):
            ref = quadrants[k][j]
            pairs[(k, j)] = abs(quadrants[k + 1][(j + 1) % 4] - ref) / ref
            control_pairs[(k, j)] = abs(quadrants[k + 1][(j + 2) % 4] - ref) / ref
    c4_by_k = {k: float(np.mean([pairs[(k, j)] for j in range(4)])) for k in range(3)}
    control_by_k = {
        k: float(np.mean([control_pairs[(k, j)] for j in range(4)])) for k in range(3)
    }

    # Step 3i's mirror pairs, one per drive and read from that drive alone.  The
    # mirror through the coil axis and drive k's own azimuth fixes quadrants k
    # and k+2 and exchanges the two flanks k-1 and k+1, so the identity is
    # P_{k-1}^{(k)} = P_{k+1}^{(k)} — a *reflection* statement, using no
    # drive-to-drive pairing and therefore independent of the C4 pairs above.
    # The control keeps the same flank in the numerator but compares it with the
    # quadrant *opposite* the reference flank (k+2, which the mirror fixes rather
    # than exchanging): a pairing the symmetry does not predict.
    mirror_pairs, mirror_control = {}, {}
    for k in range(4):
        ref = quadrants[k][(k - 1) % 4]
        flank = quadrants[k][(k + 1) % 4]
        opposite = quadrants[k][(k + 2) % 4]
        mirror_pairs[k] = abs(flank - ref) / ref
        mirror_control[k] = abs(flank - opposite) / opposite

    quad_spread = (max(quad_parts) - min(quad_parts)) / float(np.mean(quad_parts))
    verdict, verdict_text = _integral_verdict(pairs, C4_COVARIANCE_BAND)

    if comm.rank == 0:
        print(
            f"\n[WF-6 step3g] the SAR identities as CELL INTEGRALS of the PRIMAL "
            f"N1curl E — no projection, no estimator, no sample set.  "
            f"{cells} cells (default resolution, step 3's own mesh; "
            f"{DEFAULT_CELL_COUNT} on record), f = "
            f"{sweep['problem'].frequency_hz:.3e} Hz, degree 1, "
            f"quadrature_degree {QUADRATURE_DEGREE}, eps = "
            f"{PARTITION_EPS_M:.0e} m\n"
            f"    port slots " + ", ".join(f"{p} k={indices[p]}" for p in order)
            + f"; P1 azimuth {azimuths['P1']:.3f} deg, quadrant axes at "
            "0/90/180/270 deg about the COIL axis\n"
            f"    solve times "
            + ", ".join(f"{p} {solves[p]['solve_time']:.2f} s" for p in order),
            flush=True,
        )
        print("    P_j^(k) = 1/2 int_tag3 sigma w_j |E^(k)|^2 dV  [W]:", flush=True)
        for k in range(4):
            row = "  ".join(f"{v:.9e}" for v in quadrants[k])
            print(
                f"        k={k} ({by_k[k]})  {row}   sum {sum(quadrants[k]):.9e}"
                f"   total {totals[k]:.9e}",
                flush=True,
            )
        row = "  ".join(f"{v:.9e}" for v in quad_parts)
        print(
            f"        quadrature   {row}   sum {sum(quad_parts):.9e}"
            f"   total {quad_total:.9e}\n"
            f"    (i) partition identity ASSERTED at rtol {PARTITION_RTOL:.0e} for "
            f"all five drives; P1 total vs step 1's record "
            f"{STEP1_GATE_I_P1_PHANTOM_POWER_W:.9e} W at rtol "
            f"{CG1_RECORD_RTOL:.0e}\n"
            f"    the twelve C4 pairs |P_(j+1)^(k+1) - P_j^(k)| / P_j^(k) "
            f"(step 3h: ASSERTED <= {C4_COVARIANCE_BAND * 100:.1f}%, the band "
            f"imported unmoved from step 1d, and against step 3g's records at "
            f"rtol {CG1_RECORD_RTOL:.0e}):",
            flush=True,
        )
        for k in range(3):
            row = "  ".join(f"{pairs[(k, j)] * 100:8.4f}%" for j in range(4))
            print(
                f"        k={k}->{k + 1}  {row}   mean {c4_by_k[k] * 100:8.4f}%"
                f"   mis-paired control {control_by_k[k] * 100:9.4f}%"
                f"   ratio {control_by_k[k] / c4_by_k[k]:7.3f}x   (ii) ASSERTED >",
                flush=True,
            )
        print(
            f"    step 3i: the MIRROR identity P_(k-1)^(k) = P_(k+1)^(k), one "
            f"reading per drive, no drive-to-drive pairing (ASSERTED <= "
            f"{C4_COVARIANCE_BAND * 100:.1f}%, the same imported unmoved band, "
            f"and against step 3i's records at rtol {CG1_RECORD_RTOL:.0e}):",
            flush=True,
        )
        for k in range(4):
            print(
                f"        k={k} ({by_k[k]})  |P_{(k + 1) % 4} - P_{(k - 1) % 4}|"
                f" / P_{(k - 1) % 4} = {mirror_pairs[k] * 100:8.4f}%"
                f"   (record {STEP3I_MIRROR_RECORDS[k] * 100:.4f}%)"
                f"   flank-vs-opposite control {mirror_control[k] * 100:9.4f}%"
                f"   ratio {mirror_control[k] / mirror_pairs[k]:8.3f}x"
                f"   ASSERTED >",
                flush=True,
            )
        print(
            f"    quadrature drive four-quadrant spread (max-min)/mean = "
            f"{quad_spread * 100:.4f}%   ASSERTED <= "
            f"{C4_COVARIANCE_BAND * 100:.1f}% and against "
            f"{STEP3G_INTEGRAL_QUADRATURE_SPREAD * 100:.4f}%\n"
            f"    pre-registered verdict: {verdict} — {verdict_text}\n"
            f"    scope: two SYMMETRY identities of quadrant powers on one "
            "fixture at 10 MHz at fixed h — the C4 rotation (step 3h) and the "
            "mirror reflection (step 3i) — and nothing more: no absolute SAR, no "
            "homogeneity, no C95.3, no Larmor, no convergence claim; the band "
            "is imported unmoved and WF-6 stays amber",
            flush=True,
        )

    return {
        "cells": cells,
        "indices": indices,
        "totals": totals,
        "quadrants": quadrants,
        "quadrature_total": quad_total,
        "quadrature_quadrants": quad_parts,
        "pairs": pairs,
        "c4_by_k": c4_by_k,
        "control_by_k": control_by_k,
        "mirror_pairs": mirror_pairs,
        "mirror_control": mirror_control,
        "quadrature_spread": quad_spread,
        "verdict": verdict,
        "verdict_text": verdict_text,
    }


@complex_only
@pytest.mark.parametrize("drive", ["k=0", "k=1", "k=2", "k=3", "quadrature"])
def test_the_quadrant_partition_recovers_the_whole_phantom_power(sar_integral, drive):
    """Anchor (i): ``Σ_j P_j = P_phantom``, exactly, for every drive.

    ``Σ_j w_j = 1`` pointwise, so the four weighted integrals and the unweighted
    one are the same quadrature sum re-associated — an identity of arithmetic.
    A miss at 1e-10 is therefore a defect in the *integrals* (a measure that is
    not the phantom's, a partition that does not partition, a reduction that
    did not happen on some rank), never a statement about the field, and it is
    asserted before any C4 reading is looked at for exactly that reason.
    """
    if drive == "quadrature":
        parts = sar_integral["quadrature_quadrants"]
        total = sar_integral["quadrature_total"]
    else:
        k = int(drive.split("=")[1])
        parts = sar_integral["quadrants"][k]
        total = sar_integral["totals"][k]
    assert total > 0.0, f"the phantom power for drive {drive} is {total!r} — no solve"
    assert sum(parts) == pytest.approx(total, rel=PARTITION_RTOL), (
        f"the four quadrant integrals for drive {drive} sum to {sum(parts):.12e} W "
        f"but the whole phantom reads {total:.12e} W (relative miss "
        f"{abs(sum(parts) / total - 1.0):.3e} against {PARTITION_RTOL:.0e}) — the "
        "azimuthal partition is not a partition of unity over the integration "
        "region; this is a defect in the integrals, not a physical reading"
    )


@complex_only
def test_the_p1_drive_total_reproduces_step_1s_phantom_power_record(sar_integral):
    """Anchor (i)'s second half: the unweighted integral is step 1's number.

    ``½∫σ|E|²`` over tag 3 on the P1 drive is gate (i)'s phantom share, printed
    to nine digits by the step 1d, step 2 and step 3 logs.  Reproducing it here
    is what ties this module's twenty integrals to step 1's gated three-way
    power accounting: same solve, same measure, same σ.  Read at the record
    rtol rather than the partition's, because this integral is quadrature-rule
    dependent (pinned to degree 4 here) where the partition identity is not.
    """
    k = sar_integral["indices"]["P1"]
    measured = sar_integral["totals"][k]
    assert measured == pytest.approx(
        STEP1_GATE_I_P1_PHANTOM_POWER_W, rel=CG1_RECORD_RTOL
    ), (
        f"the P1 drive's phantom power integrates to {measured:.9e} W, not step "
        f"1's recorded {STEP1_GATE_I_P1_PHANTOM_POWER_W:.9e} W (rtol "
        f"{CG1_RECORD_RTOL:.0e}) — this module is not integrating step 1's "
        "solve, so nothing below is comparable with the pointwise columns"
    )


@complex_only
@pytest.mark.parametrize("pair", sorted(STEP3G_INTEGRAL_PAIR_RECORDS))
def test_the_c4_integral_pair_is_inside_the_band(sar_integral, pair):
    """**The gate.** ``P_{j+1}^{(k+1)} = P_j^{(k)}`` to within 5%, pair by pair.

    Parametrised one test per ``(k, j)`` so a miss names the pair rather than a
    worst case.  The band is step 1d's ``C4_COVARIANCE_BAND``, **imported and
    unmoved** — this module defines no band of its own.  The record check beside
    it is a different question with a different failure meaning: the band asks
    whether the physics identity holds, the record asks whether this is still
    step 3g's mesh, image and four solves.
    """
    k, j = pair
    reading = sar_integral["pairs"][(k, j)]
    assert reading <= C4_COVARIANCE_BAND, (
        f"the C4 integral pair k={k}->{k + 1}, quadrant j={j} reads "
        f"{reading * 100:.4f}%, outside the imported "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band (step 3g measured "
        f"{STEP3G_INTEGRAL_PAIR_RECORDS[(k, j)] * 100:.4f}% here) — this is the "
        "repo's only coil-driven SAR gate; record it and stop, do not widen it"
    )
    assert reading == pytest.approx(
        STEP3G_INTEGRAL_PAIR_RECORDS[(k, j)], rel=CG1_RECORD_RTOL
    ), (
        f"the C4 integral pair k={k}->{k + 1}, j={j} reads {reading * 100:.4f}% "
        f"against step 3g's recorded "
        f"{STEP3G_INTEGRAL_PAIR_RECORDS[(k, j)] * 100:.4f}% (rtol "
        f"{CG1_RECORD_RTOL:.0e}) — the band above may still be met, but the "
        "mesh, the image or the solves have moved and the reading is no longer "
        "step 3g's; that is a fixture finding, not a licence to re-record"
    )


@complex_only
def test_the_quadrature_four_quadrant_spread_is_inside_the_band(sar_integral):
    """The quadrature drive puts equal power in all four quadrants.

    The ccw phase pattern is itself C4-covariant, so its ``P_j`` are four
    readings of one number; ``(max − min)/mean`` over them is the same identity
    read without a drive-to-drive pairing.  Same imported band, same record
    licence as the twelve pairs.
    """
    reading = sar_integral["quadrature_spread"]
    assert reading <= C4_COVARIANCE_BAND, (
        f"the quadrature drive's four-quadrant power spread is "
        f"{reading * 100:.4f}%, outside the imported "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band (step 3g measured "
        f"{STEP3G_INTEGRAL_QUADRATURE_SPREAD * 100:.4f}%) — four fields each "
        "inside the band should superpose to a C4-symmetric power distribution, "
        "so this is a finding about the superposition path"
    )
    assert reading == pytest.approx(
        STEP3G_INTEGRAL_QUADRATURE_SPREAD, rel=CG1_RECORD_RTOL
    ), (
        f"the quadrature four-quadrant spread reads {reading * 100:.4f}% against "
        f"step 3g's recorded {STEP3G_INTEGRAL_QUADRATURE_SPREAD * 100:.4f}% "
        f"(rtol {CG1_RECORD_RTOL:.0e}) — a fixture finding, not a re-record"
    )


@complex_only
@pytest.mark.parametrize("k", sorted(STEP3I_MIRROR_RECORDS))
def test_the_mirror_flanks_of_a_single_drive_carry_equal_power(sar_integral, k):
    """**Step 3i's gate.** ``P_{k−1}^{(k)} = P_{k+1}^{(k)}`` to within 5%.

    A second, *independent* symmetry of the same construction.  The plane
    containing the coil axis and drive ``k``'s own azimuth is a symmetry plane of
    the fixture-plus-excitation: it fixes quadrants ``k`` and ``k+2`` setwise and
    exchanges the two flanking quadrants ``k−1`` and ``k+1``.  Reflections
    preserve ``|E|`` (the mirror acts on the field, not on the drive), so the two
    flank integrals are one number read twice.  Unlike the twelve C4 pairs this
    uses **one** drive at a time, so it is not a re-reading of the rotation
    identity: a systematic error common to all four solves cancels out of the C4
    pairs and does *not* cancel out of this one.

    The band is step 1d's ``C4_COVARIANCE_BAND``, **imported and unmoved**; the
    record beside it asks the separate question of whether this is still step
    3h's mesh, image and four solves.  The control keeps the same flank in the
    numerator but pairs it with the quadrant the mirror *fixes* (``k+2``) instead
    of the one it exchanges — a comparison the symmetry does not predict, and it
    is asserted strictly larger, so a phantom power map with no azimuthal
    structure left could not pass this test by accident.
    """
    reading = sar_integral["mirror_pairs"][k]
    control = sar_integral["mirror_control"][k]
    assert reading <= C4_COVARIANCE_BAND, (
        f"the mirror pair for drive k={k} reads {reading * 100:.4f}%, outside the "
        f"imported {C4_COVARIANCE_BAND * 100:.1f}% band (step 3h's table predicts "
        f"{STEP3I_MIRROR_RECORDS[k] * 100:.4f}% here) — record it and stop, do "
        "not widen the band and do not re-record"
    )
    assert reading == pytest.approx(STEP3I_MIRROR_RECORDS[k], rel=CG1_RECORD_RTOL), (
        f"the mirror pair for drive k={k} reads {reading * 100:.4f}% against the "
        f"recorded {STEP3I_MIRROR_RECORDS[k] * 100:.4f}% (rtol "
        f"{CG1_RECORD_RTOL:.0e}) — the band above may still be met, but the mesh, "
        "the image or the solves have moved underneath it; a fixture finding, "
        "not a licence to re-record"
    )
    assert control > reading, (
        f"for drive k={k} the flank-vs-opposite control reads "
        f"{control * 100:.4f}% against the mirror pairing's {reading * 100:.4f}% "
        f"(ratio {control / reading:.4f}x) — a pairing the mirror symmetry does "
        "not predict agrees at least as well as the one it does, so the quadrant "
        "map carries no azimuthal structure and the mirror reading above is not "
        "interpretable"
    )


@complex_only
@pytest.mark.parametrize("k", [0, 1, 2])
def test_the_mis_paired_quadrant_control_reads_larger_than_the_c4_pairing(
    sar_integral, k
):
    """Anchor (ii): pairing across 180° must be *worse* than pairing across 90°.

    If quadrant ``j`` under drive ``k`` matched quadrant ``j+2`` under drive
    ``k+1`` as well as it matches quadrant ``j+1``, the twelve C4 readings above
    would be measuring nothing — a phantom power distribution with no azimuthal
    structure left satisfies every pairing equally.  Asserted as an **ordering**
    only: nobody has measured how large this ceiling is on this fixture, and
    pre-registering a factor would be inventing a number.
    """
    c4 = sar_integral["c4_by_k"][k]
    control = sar_integral["control_by_k"][k]
    assert control > c4, (
        f"for the drive step k={k}->{k + 1} the mis-paired (180 deg) control "
        f"reads {control * 100:.4f}% against the C4 pairing's {c4 * 100:.4f}% "
        f"(ratio {control / c4:.4f}x) — the mis-paired comparison is no worse "
        "than the correct one, so the integral quadrant map carries no "
        "azimuthal structure and no C4 reading in this module is interpretable"
    )
