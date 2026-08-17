"""`PORT-1` step 3b-vi: the **tangential path-integral** gap voltage.

The port voltage gated here is what ``−∫E·dl`` literally is: the integral of the
component of ``E`` *along* the path the loop current would take through the gap.
The path is the torus **centreline arc** of major radius ``a`` through port
``i``'s gap, terminal to terminal — from the ``y < 0`` arc-end disc at
``φ = −gap_angle/2`` to the ``y > 0`` disc at ``φ = +gap_angle/2`` — and

    V_i = −∫ E·t̂ dl = −a ∫_{−g/2}^{+g/2} E(a cos φ, a sin φ, z_i)·t̂(φ) dφ ,
    t̂(φ) = (−sin φ, cos φ, 0)

is evaluated by Gauss–Legendre quadrature: the nodes are strictly interior to
``(−g/2, +g/2)``, so no sample ever lands on the gap/conductor interface, where
point location is ambiguous by construction.  ``t̂(0) = ŷ``, so the orientation
is the same ``+ŷ`` one the box, shadow and facet estimators used and the four
numbers are directly comparable in sign.  Sampling goes through
:func:`~fem_em_solver.post.evaluation.evaluate_vector_field_parallel`, never
``f.eval``.  Two quadrature resolutions (``PATH_QUADRATURE_ORDERS``) are taken
off the *same* solve and must agree to ``PATH_QUADRATURE_TOLERANCE`` before the
number is compared to anything: quadrature convergence is free, solve time is
not, and a path integral that has not converged in the quadrature says nothing
about the field.

**Why the tangential path and not the terminal facets.**  Step 3b-v read ``V``
as an area average of ``E·ŷ`` over the tagged arc-end discs (``201``/``202``,
emitted by step 3b-iv) times the ŷ chord joining them, and measured
**4.845 × ωM₁₂** with a reciprocity residual of 1.79e-2 — an order worse than
every other route on the same fixture.  That is not a tuning failure but a
category error: on the terminal disc ``E·ŷ`` is the facet-*normal* component,
which jumps across the material interface and is dominated by the surface charge
that terminates the conduction current, not by the tangential field the line
integral wants.  Two estimator families are now excluded by measurement — region
averages (box: sign-unstable; tube shadow: stable but 0.763–0.814 × ωM₁₂) and
terminal-facet sampling — and this file is the third, which is the only one that
integrates the tangential component along the path rather than sampling its
ends.  All three prior estimators are still computed here, printed beside the
path number and gated nowhere, so four estimators are compared on **one solve**
rather than across logs.  The facet route's own machinery is retained for the
same reason: it supplies the disc-area geometry gate.

**Known-issues 11 does not enter this estimator.**  At ``gap_overhang = 2e-4``
the tube protrudes 0.2018 mm through the gap box's ``−x`` face, so facet tags
``201``/``202`` are the arc-end disc pair *plus two lateral strips* and their
area sits 1.0241 × above the exact oblique cut.  The path integral uses no facet
tags at all; ``test_port_discs_are_the_arc_end_cut`` is retained for the
mirror-symmetry identities it still gates, but the ``meshed/exact`` band is
**printed and not asserted** at this overhang — that band was measured at
overhang 1e-3 where the tube clears the face, and known-issues 11 records that
it does not transfer.

**Why not a volume average.**  Step 3b-ii read ``V`` as a
volumetric mean over the whole gap box and measured +72.12%.  Step 3b-iii then
varied only ``gap_overhang`` — the transverse margin that sets how much of the
gap face is *not* conductor shadow:

    overhang    fringe    Im Z₁₂ / ωM₁₂     Im Z₁₂ [Ω]
    1.0e-3      0.4546    +1.7210            +2.137292   (3b-ii)
    5.0e-4      0.3509    -0.2391            -0.296954
    2.0e-4      0.2739    +0.3317            +0.411950

Non-monotone, and it changes **sign** between 2e-4 and 5e-4: the fringe
hypothesis 3b-ii raised (a 45% annulus of opposite-sign field inflating the
average) predicted a smooth march toward 1 as the annulus shrank, and that is
refuted.  A volumetric average over a *rectangular* region is not a port
voltage — the box's corners sample fringe field whose sign depends on where the
box face cuts the fringe pattern, not on how much of it there is.  Over the same
three geometries the tube-shadow-restricted volume average was stable and
sign-consistent at 0.687–0.814 × ωM₁₂; that ~0.78 common deficit is the number
this file's estimator must either close or inherit, and inheriting it is itself
a result (it would say the deficit is not the averaging region).
``MUTUAL_TOLERANCE`` is unmoved at 10%.

**The lazy collective (3b-iv, known-issues 9, retired).**  A ``dS`` integral
over a subdomain some rank does not own reaches
``create_entity_permutations()`` on only the ranks that do, and this partition
gives each rank exactly one port — so the call is hoisted here, unconditional
and on every rank, before any per-port facet form.  A ``-n 2`` hang in this
file is that before it is physics.

The first solved-field impedance in this repository read off a **driven port
gap** rather than a reaction integral.  Step 3b-i built the fixture: two
partial tori (tags ``1``/``2``) each bridged by a rectangular dielectric gap box
(tags ``101``/``102``), all fragmented conformally into one air box.  Here the
conductors become finite-σ material volumes, port ``k`` is driven by an
impressed current density across gap ``k``, and the two lumped-port quantities
are read off the solved field:

    I_k = (1/L_k) ∫_{wire k} σ E·φ̂ dV            (meshed arc length L_k)
    V_i = −∫_{arc i} E·t̂ dl                       (path route, step 3b-vi)
    Z_ik = V_i / I_k

``V`` is the tangential line integral along the gap arc; the facet average
(3b-v) and the two volumetric averages (3b-ii/3b-iii) are kept as printed
diagnostics.  ``I``
is the same
"meshed current" reduction step 2 used (``∫J_φ dV / arc length``), with the arc
length taken from the **meshed** conductor volume ``V_wire/(π r_wire²)`` rather
than the analytic ``a(2π − g)``, because the gap box swallows the arc ends
(step 3b-i measured the conductor at 0.9636 of the analytic partial torus).

What is gated, and why:

  * **mutual coupling** ``Im Z₁₂`` against the closed form
    ``ωM₁₂ = 1.241755 Ω`` (Jackson 5.37 via
    :func:`~tests.validation.test_port_reaction_impedance.mutual_inductance`),
    with port 2 open — its gap is a series C of ~7e-14 F, i.e. 2.2e5 Ω at
    10 MHz against the loop's ~7 Ω, so "open" is four orders of separation, not
    an approximation.  **Step 3b-xviii** made this the port-pair gate it had
    been deferred as since 3b-i/3b-ii, at ``MUTUAL_TOLERANCE`` unmoved and
    carrying its two measured systematics by name — the PEC box
    (``+1.69 pp`` at ``p = 1.657``, effective-range) and the gap-physics offset
    (``−3.0224e-02``, Jin 3e §10.4.2.1).  Between 3b-x and 3b-xviii it was
    printed and not asserted, because neither systematic had been measured yet
    and gating on the raw number would have gated the truncation box.
  * **reciprocity** ``|Z₁₂ − Z₂₁|/|Z₁₂|`` from the second port's solve on the
    *same* mesh — two different tags, two different loads, one operator.  This
    is a network identity the gap-voltage route has never been asked for; the
    reaction route measured 3e-13 for it, but that route is symmetric by
    construction (the same bilinear form appears twice), whereas here ``V`` and
    ``I`` are assembled on different subdomains with different integrands, so
    the two solves share no algebra beyond the matrix.  Banded from measurement.

**Negative control.**  The unfragmented ancestor of this fixture returned
``Z₁₂`` *identically zero* against the same 1.2418 Ω closed form
(`20260731T213222Z_PORT-1-step1-costprobe.log`, PROJECT_PLAN §7): the two loops
meshed as disconnected islands, so a source on one produced no field at the
other.  The separation between the honest and the broken fixture is total.

**σ is a precomputed constraint, not a knob.**  The current path must be
resolvable, so the tube radius must stay inside a skin depth:

    δ = √(2/(ωμ₀σ)) ≥ r_wire  ⇒  σ ≤ 2/(ωμ₀ r_wire²) ≈ 1.013e3 S/m

at f = 10 MHz, r_wire = 0.005 m.  ``SIGMA_WIRE_S_PER_M`` is 8e2, δ = 5.63 mm =
1.13 r_wire.  Recompute if either f or r_wire changes — the test asserts the
inequality rather than trusting this comment.  At quasi-statics the mutual is
geometry-only, so the anchor does not depend on the σ chosen.

**The diagonal is deliberately not gated.**  ``Z₁₁`` here inherits the gap's
series C *and* the loop's own ohmic resistance, and neither has a closed form on
this fixture; it is printed beside the Grover number for the record and gated
nowhere.  Step 2f gates the (projected, reaction-route) diagonal; this file does
not duplicate that claim through a different drive.

**Does not close** `PORT-1`: known-issues 3's two deliberately-red port tests
and the ``is_placeholder=False`` touchstone threading come after.  A green
3b-ii is the first solved-field Z on a gap-driven port, nothing more.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_gap_voltage_impedance.py -v -s'
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.ports.systematics import (
    GAP_PHYSICS_SYSTEMATIC as _GAP_PHYSICS_SYSTEMATIC,
    PEC_BOX_SYSTEMATIC as _PEC_BOX_SYSTEMATIC,
    PEC_BOX_SYSTEMATIC_EXPONENT as _PEC_BOX_SYSTEMATIC_EXPONENT,
    mutual_systematics_ladder,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.constants import EPSILON_0, MU_0

from tests.complex_mode import complex_only
from tests.validation.test_port_reaction_impedance import (
    AIR_PADDING,
    FREQUENCY_HZ,
    H_FAR,
    H_WIRE,
    MAJOR_RADIUS,
    MINOR_RADIUS,
    OMEGA,
    SEPARATION,
    mutual_inductance,
)

WIRE_TAGS = (1, 2)
GAP_TAGS = (101, 102)
AIR_TAG = 3
# Step 3b-iv's facet groups: the two arc-end discs of each port, i.e. the
# gap/conductor interface.  Measured area per port 1.563786482e-04 m^2 =
# 0.974490841 of the exact oblique cut, at -n 1 and -n 2 alike
# (20260805T171107Z_PORT-1-step3biv-parallel-gate-fixed.log).
PORT_FACET_TAGS = (201, 202)

# The exact oblique cut of the two arc ends per port, from 3b-iv's quadrature
# (and OCC's own getMass to every printed digit).  It depends on GAP_BURIAL and
# the torus radii only -- not on GAP_OVERHANG -- so 3b-iv's number carries over
# to this file's geometry unchanged.
PORT_DISC_AREA_EXACT_M2 = 1.604721580e-04
# Probe-set band on meshed/exact, from 3b-iv: a planar section of an inscribed
# linear-tet solid inherits the solid's chordal deficit (~0.98) rather than
# improving on it.
DISC_AREA_BAND = (0.970, 0.980)

# Step 3b-i's measured fixture parameters: the gap is a 0.30 rad wedge centred
# on +x, bridged by a box that buries GAP_BURIAL past each arc end-face centre.
GAP_ANGLE = 0.30
GAP_BURIAL = 1.0e-3

# Step 3b-iii's variable.  The burial is structural (the tilted end planes
# cannot be met flush), but the *transverse* overhang buys nothing and costs
# cross-section: at overhang o the gap box's face is 4(r+o)^2 against the tube's
# pi*r^2, so a fraction 1 - pi*r^2/(4(r+o)^2) of the y-lines the volumetric V
# averages never pass through conductor at either end.  That fringe is 45.5% at
# 3b-ii's 1 mm and 21.5% in the limit o -> 0 (a square circumscribing a circle
# keeps its corners), so this experiment halves the fringe rather than removing
# it.  2e-4 already sits at ~24.1%, within 3 points of the floor, and avoids the
# tangent-face (o = 0) OCC fragment-fragility class.
GAP_OVERHANG = 2.0e-4

# δ = sqrt(2/(omega*mu0*sigma)) = 5.63 mm at 8e2 S/m, i.e. 1.13 r_wire — inside
# the ceiling 2/(omega*mu0*r_wire^2) = 1.013e3 S/m asserted in
# ``test_sigma_respects_the_skin_depth_constraint``.
SIGMA_WIRE_S_PER_M = 8.0e2

# Nominal drive; every gated quantity is a ratio, so the scale is arbitrary.
DRIVE_CURRENT_A = 1.0

# Bands are filled from the probe log below (see the module docstring).
MUTUAL_TOLERANCE = 0.10
RECIPROCITY_TOLERANCE = 1.0e-2

# Step 3b-vi.  Two Gauss-Legendre resolutions on the same solve; the coarse one
# exists only to certify the fine one, and the gated V is the fine one.  Both
# node sets are strictly interior to the arc, so neither ever samples the
# gap/conductor interface.
#
# The plan proposed (33, 65).  Measured on the first gate run
# (`20260806T093603Z_PORT-1-step3bvi-gate-n2.log`) those two disagree by
# 1.07e-1 — two orders above the 1e-3 precondition — so the sequence is
# extended to measure the *rate* rather than assert a converged value at a node
# count picked a priori.  The reason the integrand is hard is structural: N1curl
# guarantees continuity of the facet-tangential component only, and the arc's
# own tangent is not facet-tangential, so E·t̂ jumps at every cell crossing;
# with h_wire = 2.5e-3 against an arc length a*g = 1.2e-2 only ~5 cells span
# the path, and Gauss quadrature over a piecewise-smooth integrand with jumps
# converges at O(1/n), not spectrally.
PATH_QUADRATURE_ORDERS = (33, 65, 129, 257, 513, 1025, 2049, 4097)
# The plan's precondition: the two resolutions agree to 0.1% before the number
# is compared to anything.
PATH_QUADRATURE_TOLERANCE = 1.0e-3

# Step 3b-vii.  The pair the precondition is *gated* on, and the source of the
# gated V; the tuple above stays as the printed rate diagnostic, so the plateau
# on the refined mesh can be read against 3b-vi's on the unrefined one.
#
# **Step 3b-x raises this pair from (129, 257) to (2049, 4097).** The bound
# below does not move; the integrand does.  Terminal-to-terminal limits add the
# two buried end zones, which is exactly where the terminal fields live — the
# whole reason the wedge estimator lost 45% of the EMF — so a rule that was
# converged to 1.18e-3 at 257 over the wedge is not converged over the wider
# span.  Measured on the first 3b-x gate run
# (`20260807T093906Z_PORT-1-step3bx-gate-n2.log`, undriven port, gap 101
# driven): |dV|/|V| = 2.99e-3 (129), 1.18e-3 (257), 6.29e-3 (513), 2.11e-3
# (1025), 5.47e-4 (2049), 3.91e-4 (4097).  Resolving the integrand rather than
# relaxing the tolerance is step 3b-vii's precedent (there it cost a mesh
# refinement; here it costs point evaluations on a field already solved).
PATH_QUADRATURE_GATE_ORDERS = (2049, 4097)

# Step 3b-vii's one mesh change: 3b-vi's quadrature plateau is a mesh property
# (~5 cells of h_wire = 2.5e-3 across the a*g = 1.2e-2 arc, and E·t̂ jumps at
# every cell crossing because N1curl is facet-tangentially continuous only), so
# the integrand is resolved rather than the quadrature.  3e-4 is 40 cells across
# the arc.  Cost measured before the gate was launched
# (20260806T170559Z_PORT-1-step3bvii-probe.log): 124 753 -> 178 055 cells
# (1.427x), mesh 29.2 s -> 41.4 s, gap-tagged cells 1569 -> 24 430 per port.
GAP_ARC_RESOLUTION = 3.0e-4

# ---------------------------------------------------------------------------
# Step 3b-ix: loop-closure decomposition and the sigma scaling.
#
# The identity under test is Faraday on the *closed* centreline circle:
# -∮E·t̂ dl = -iωΦ, whose magnitude on the undriven loop is ω M₁₂ I₁ (the
# undriven loop is open, so its self-flux is negligible — the same premise
# ``test_undriven_port_is_open_and_the_diagonal_is_reported`` already gates).
# The gap estimator integrates over the wedge (−g/2, +g/2) only; the rest of
# the circle is the missing half, and 3b-vi/3b-vii's 0.49 says the rest is not
# small.  The complement splits into two materials, so it is measured as two
# pieces rather than one, each with its own material precondition:
#
#   * the **buried** segments (±g/2 → ±φ_box).  The gap box buries
#     ``GAP_BURIAL`` past the arc-end face *centres*, so along the centreline
#     the dielectric extends past the nominal wedge out to
#     ``φ_box = arcsin(half_y / a)`` — 0.175338 rad against g/2 = 0.15.  These
#     two short arcs are gap-tagged, not wire-tagged, and leaving them out
#     would make the "closure" miss a piece of the loop.
#   * the **wire** arc (φ_box → 2π − φ_box), the conductor interior.  This is
#     the term the penetration hypothesis says is O(1): at δ = 1.125 r_wire the
#     centreline sits deep inside a conductor carrying an eddy response, and
#     E = J/σ there is small per cell but the arc is 0.246 m long.
#
# Orders are the plan's.  The wire integrand crosses ~800 cells of h_wire
# rather than the gap arc's ~40 of GAP_ARC_RESOLUTION, and E·t̂ jumps at every
# crossing (N1curl is facet-tangentially continuous only), so the precondition
# is 1e-2 — an order looser than the gap arc's, set by the plan before any
# number was measured, and a plateau above it is reportable rather than
# grounds for raising it.
WIRE_ARC_ORDERS = (513, 1025)
WIRE_ARC_TOLERANCE = 1.0e-2
# The buried segments are 1.0e-3 m of arc each, ~3 cells of GAP_ARC_RESOLUTION;
# their convergence is printed beside the wire arc's and enters the closure sum
# at the finer order.
BURIED_ARC_ORDERS = (129, 257)
# The wedge segment of the *closure* tiling keeps 3b-ix's orders even though the
# estimator's own gate moved to (2049, 4097): the decomposition on record —
# wedge 0.493653 / 0.491744, sum 0.896019 / 0.896299 x omega*M12 — is a
# measurement, and reproducing it bit for bit is how step 3b-x shows that only
# the integration limits changed between the two steps.
GAP_SEGMENT_ORDERS = (129, 257)

# The closure band.  The reference's own bound is step 2's −9.35% (≈ −9.36%
# attributable to the PEC box at padding 0.08) plus 3b-viii's +0.481%
# finite-cross-section correction; 0.15 is that bound with room for the
# discretisation of a 0.25 m piecewise-discontinuous integrand.  It is set
# here, before the measurement, and is not moved by what the measurement says.
CLOSURE_TOLERANCE = 0.15

# Step 3b-ix part 2.  δ/r_wire: 1.125 → 0.795 → 0.563.  **Never beyond ×4** —
# at ×16, δ = 1.4e-3 m < h_wire = 2.5e-3 m and the skin layer is unresolved, so
# the point would be noise.  One solve each, driving port 1 only, on the mesh
# the σ×1 solves already built.
SIGMA_SCALES = (2.0, 4.0)
SIGMA_SWEEP_DRIVEN_COLUMN = 0

# ---------------------------------------------------------------------------
# Step 3b-x: terminal-to-terminal limits.
#
# The estimator's limits are now the meshed dielectric's extent, and this is
# the gate that keeps them tied to it: the 201/202 facets are the
# conductor/dielectric cut, they lie in the gap box's own ``y`` faces, so
# ``arcsin(⟨y⟩_facet / a)`` must reproduce ``arcsin(half_y / a) = 0.175335``
# rad.  ``y`` is constant on each facet by construction, so this is a geometry
# identity, not an average with a discretisation error — 1e-6 is a tight bound
# on an exact number, and it fails *before* any solve.
TERMINAL_ANGLE_TOLERANCE = 1.0e-6

# The retiling identity.  The corrected terminal-to-terminal integral and
# 3b-ix's three-piece tiling (buried_neg + wedge + buried_pos) cover the same
# interval of the same field, so they must agree to quadrature error.  Both
# sides are Gauss-Legendre on a piecewise-discontinuous integrand at the orders
# each segment already used, so 1e-3 is the *quadrature*'s bound, not the
# estimator's; on record from 3b-ix the tiling sums to 0.893625 / 0.893983 x
# omega*M12 (undriven port, gap 101 / gap 102 driven).
RETILING_TOLERANCE = 1.0e-3
# Both sides of the identity are integrated at *matched, converged* orders, or
# the residual measures the two rules' different convergence rates instead of
# the tiling: the corrected estimator at PATH_QUADRATURE_GATE_ORDERS[-1] against
# the wedge at the same order and each buried segment at 1025 (they are 1.013 mm
# of arc, ~3 cells of GAP_ARC_RESOLUTION, so 1025 is far past resolved).  The
# closure decomposition keeps GAP_SEGMENT_ORDERS/BURIED_ARC_ORDERS separately,
# so 3b-ix's record is untouched by this.
RETILING_BURIED_ORDER = 1025

# Estimator-vs-reaction consistency: the gate the closed-form comparison used
# to carry.  The reaction route is the landed step-1/2 machinery
# (Z_21 = −∫E·J₂/(I₁I₂), `tests/validation/test_port_reaction_impedance.py`),
# evaluated on *this* gapped fixture off the *same* solved field, so both sides
# see the same mesh, the same PEC box and the same padding — the −10.4% the
# closure sum sits at against omega*M12 is common to both and cancels.  3% is
# the review-set bound: the closure sum is ~1.2 pp from the ungapped reaction
# route's −9.35%, and 3% leaves room for the gapped/ungapped difference.  The
# negative control is on record: the wedge-only estimator at 0.4937 x omega*M12
# is ~45% off the reaction route, 15x this bound.
REACTION_CONSISTENCY_TOLERANCE = 0.03

# Step 3b-xiii: the σ ladder on the *control*.  Three owners of the ~3%
# estimator-vs-control deviation are measured and excluded — the wedge limits
# (3b-x), the ωM₁₂ reference (3b-viii), the PEC box (3b-xii, which moved both
# routes together by +2.956/+3.045 pp).  What is left is that the two routes
# differ in two ways at once: the production loop is gapped and σ = 800 S/m,
# the control's is closed and lossless.  This ladder fills the missing corner
# of that 2×2 — closed *and* lossy — by re-running the same control solve with
# the loop footprints (wire ∪ gap box, so the loop stays electrically closed)
# given a conductivity through the same DG0 material map the production solves
# use.  σ is the only variable that moves: same mesh, same padding, same
# impressed drive, same normalisation, same reaction integral.
CONTROL_SIGMA_LADDER = (2.0e2, SIGMA_WIRE_S_PER_M)

# Step 3b-xiv: the reciprocal ladder, on the *production gapped* route.
# 3b-xiii ran the σ knob on the closed control and disproved that step's own
# premise: a closed lossy loop is a shorted turn (|I_cond/I′| reached 0.865 at
# σ = 800), so σ and closed-vs-gapped are confounded there and the corner it
# filled measures the short, not the loss.  The reciprocal half has no such
# degeneracy — hold the *gapped* production fixture fixed and lower σ on the
# conductor toward zero.  With the gap open there is no closed conducting path
# for a circulating current to exist on at any σ, so |I_cond/I′| collapses as
# σ → 0 rather than growing, and at σ = 0 the gap is the only structural
# difference left against the closed lossless control.
#
# σ goes on ``WIRE_TAGS`` only — the production conductor.  The gap boxes stay
# non-conducting: giving them σ is exactly what would close the loop and
# reproduce 3b-xiii's degeneracy.  (§9 item 1's "wire ∪ gap-box" phrasing is
# inherited from the *control*'s drive/test region, which is closed by
# construction; on this route the gap box is the gap.)
PRODUCTION_SIGMA_LADDER = (2.0e2, 0.0)

# ---------------------------------------------------------------------------
# Step 3b-xviii: the deferred 3b-i/3b-ii **port-pair gate**.
#
# The two systematics that stand between this fixture's Im Z12 and the
# filamentary closed form.  Both are measured on record, both are quoted with
# what they are, and neither is a fitted knob adjusted to make a gate green:
# they were fixed by the padding sweep and the matched-topology re-point before
# this gate existed.
#
#   * **PEC box.**  The truncation box at AIR_PADDING = 0.08 costs the mutual
#     D_inf = +1.69 pp of ratio, from step 3b-xi/decision-(4)'s free-exponent
#     fit ``ratio = r_inf - C*W^(-p)`` to three padding rungs, at **p = 1.657**
#     — an *effective-range* extrapolation, never to be quoted without its
#     exponent (pinning the dipolar p = 3 moves the term to -1.43 pp; the model
#     uncertainty is ~840x the data uncertainty, §7 3b-xi note).  The 10% band
#     dwarfs that 3.1 pp spread, which is why no fourth rung was commissioned.
#   * **Gap physics.**  The gapped fixture reads -3.0224e-02 against its own
#     sigma = 0 *closed* control (-2.9674e-02 under 1.57x feed refinement) —
#     the gap-generator feed model's documented, gap-geometry-dependent
#     impedance error (Jin, *The FEM in Electromagnetics* 3rd ed., §10.4.2.1).
#     Step 3b-xvi excluded feed discretisation as its owner by measurement
#     (+0.0508 pp under refinement against a 0.5 pp band), and 3b-xvii's
#     matched-topology gate is what licenses calling it a topology term rather
#     than an estimator defect.
#
# The closed form is filamentary and box-free, so a comparison against it must
# either carry these two or gate the box and the feed model instead of the
# estimator.  The gate below carries them: it asserts on the corrected ratio and
# prints the whole ladder, raw first, so the raw -10.57% is on the record beside
# the corrected number rather than hidden behind it.
# Lifted into the package by `EX-18` (2026-08-13) so the example and this gate
# share one definition of the three constants and the ladder — see
# ``fem_em_solver.ports.systematics``.  The values are unmoved; the module-level
# names are kept so every reference below and in the sibling padding/consistency
# modules reads exactly as it did when the numbers were measured, and
# ``test_lifted_systematics_ladder_is_bit_identical`` asserts the lift changed
# no digit.
PEC_BOX_SYSTEMATIC = _PEC_BOX_SYSTEMATIC
PEC_BOX_SYSTEMATIC_EXPONENT = _PEC_BOX_SYSTEMATIC_EXPONENT
GAP_PHYSICS_SYSTEMATIC = _GAP_PHYSICS_SYSTEMATIC

# Step 1's unfragmented-mesh record: the two loops meshed as disconnected
# islands and Z12 came out *identically* zero against this same 1.241755 Ohm
# closed form (`20260731T213222Z_PORT-1-step1-costprobe.log`).  That is the
# total-separation floor every step of this lineage cites, and the gate function
# below is executed on it as a negative control — a band that accepts the blind
# fixture's -100% would be gating nothing.
BLIND_FIXTURE_IM_Z12_OHM = 0.0

# The rung this ladder shares with the landed fixture, and the column it drives.
# Column 0's record at padding 0.08 is the estimator 0.894543 x omega*M12; the
# ladder is read against that and against the sigma = 0 closed control 0.922423
# (both on record, both cited rather than recomputed here -- the module's own
# gates re-measure them on every run of this fixture).
PRODUCTION_LADDER_DRIVEN_COLUMN = 0


def _mutual_systematics_ladder(im_z12_ohm: float, omega_m12: float) -> dict:
    """The 3b-xviii ladder: raw ratio → PEC-box corrected → gap-physics corrected.

    A pure function of one measured number, so the gate it drives can be
    executed on the blind fixture's ``Z₁₂ ≡ 0`` as a negative control without a
    second solve.  The two corrections are applied in the order they were
    measured, and each is *additive in the same units it was measured in*:

      * the PEC box moved the **ratio** by ``+D_inf`` pp (a padding
        extrapolation of ``|Im Z₁₂|/ωM₁₂`` itself), so it adds to the ratio;
      * the gap-physics term is a **relative** deviation of the gapped fixture
        against its own closed control, so removing it divides by
        ``1 + GAP_PHYSICS_SYSTEMATIC``.

    Returns every rung, not just the last: the gate asserts on ``corrected`` and
    the caller prints all of them.

    **`EX-18` (2026-08-13):** the arithmetic moved to
    :func:`fem_em_solver.ports.systematics.mutual_systematics_ladder` so
    ``examples/ports/01_two_torus_port_pair.py`` reproduces this gate's digits
    from the same code rather than from a copy of the three constants.  What
    stays here is ``passes`` alone — ``MUTUAL_TOLERANCE`` is *this module's*
    band, not a property of the systematics.
    """
    rungs = mutual_systematics_ladder(im_z12_ohm, omega_m12)
    return {
        **rungs,
        "passes": abs(rungs["corrected"] - 1.0) < MUTUAL_TOLERANCE,
    }


def test_lifted_systematics_ladder_is_bit_identical():
    """`EX-18`'s lift changed no digit of step 3b-xviii's ladder.

    The three constants and the two-rung arithmetic moved to
    ``fem_em_solver.ports.systematics`` so the example and this gate cannot
    drift apart.  A lift that quietly re-typed a constant would move the gated
    number without moving the band, so the comparison here is ``==`` against
    the literals and the expression as they stood when 3b-xviii measured them —
    exact equality, not a tolerance — evaluated at that gate's own recorded
    ``Im Z₁₂`` and ``ωM₁₂`` and at the blind fixture's ``Z₁₂ ≡ 0``.  No solve:
    the ladder is a pure function, which is why it could be lifted at all.
    """
    assert PEC_BOX_SYSTEMATIC == +1.69e-2
    assert PEC_BOX_SYSTEMATIC_EXPONENT == 1.657
    assert GAP_PHYSICS_SYSTEMATIC == -3.0224e-02

    omega_m12 = OMEGA * mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    # The gate's own recorded rung: raw 0.894283 x omega*M12
    # (20260813T020352Z_PORT-1-step3bxviii-pairgate-n2.log).
    for im_z12 in (0.894283 * omega_m12, BLIND_FIXTURE_IM_Z12_OHM, -1.5, 12.75):
        expected_raw = abs(im_z12) / omega_m12
        expected_box = expected_raw + 1.69e-2
        expected_corrected = expected_box / (1.0 + (-3.0224e-02))

        rungs = mutual_systematics_ladder(im_z12, omega_m12)
        assert rungs["raw"] == expected_raw
        assert rungs["box_corrected"] == expected_box
        assert rungs["corrected"] == expected_corrected
        assert rungs["raw_deviation"] == expected_raw - 1.0
        assert rungs["box_deviation"] == expected_box - 1.0
        assert rungs["deviation"] == expected_corrected - 1.0

        # The module's wrapper adds only the band, and takes it from
        # MUTUAL_TOLERANCE rather than from the lifted module.
        wrapped = _mutual_systematics_ladder(im_z12, omega_m12)
        assert wrapped["corrected"] == expected_corrected
        assert wrapped["passes"] == (
            abs(expected_corrected - 1.0) < MUTUAL_TOLERANCE
        )

    if MPI.COMM_WORLD.rank == 0:
        print(
            "[EX-18] lifted ladder bit-identical: PEC box "
            f"{PEC_BOX_SYSTEMATIC:+.6e} (p = {PEC_BOX_SYSTEMATIC_EXPONENT}), "
            f"gap physics {GAP_PHYSICS_SYSTEMATIC:+.6e}; at the 3b-xviii raw "
            "rung 0.894283 the ladder returns corrected "
            f"{mutual_systematics_ladder(0.894283 * omega_m12, omega_m12)['corrected']:.6f}",
            flush=True,
        )


def _gap_half_extents():
    """The gap box, recomputed from the same expressions as ``io/mesh``."""
    half_xz = MINOR_RADIUS + GAP_OVERHANG
    half_y = MAJOR_RADIUS * np.sin(0.5 * GAP_ANGLE) + GAP_BURIAL
    return half_xz, half_y


def _fringe_fraction(overhang: float) -> float:
    """Face area not in the tube's shadow, as a fraction of the box face."""
    return 1.0 - np.pi * MINOR_RADIUS**2 / (4.0 * (MINOR_RADIUS + overhang) ** 2)


def _reduce(form, comm) -> complex:
    """``assemble_scalar`` is rank-local — reduce before anyone reads it."""
    return complex(comm.allreduce(fem.assemble_scalar(fem.form(form)), op=MPI.SUM))


def _tag_measure(msh, cell_tags, tag):
    return ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,))


def _tags_measure(msh, cell_tags, tags):
    """``dx`` over a *union* of cell tags — step 3b-x-b's loop footprint."""
    return ufl.Measure(
        "dx",
        domain=msh,
        subdomain_data=cell_tags,
        subdomain_id=tuple(int(t) for t in tags),
    )


def _port_facet_measure(msh, facet_tags, tag):
    """The two arc-end discs of one port. ``dS``, not ``ds``: they are interior."""
    return ufl.Measure(
        "dS", domain=msh, subdomain_data=facet_tags, subdomain_id=(tag,)
    )


def _side_indicator(msh, cell_tags, tags) -> "fem.Function":
    """DG0 indicator of ``tags``, ghost cells included.

    ``E·ŷ`` on a port disc is the facet-*normal* component, which jumps across
    the material interface, so a ``dS`` restriction must be chosen by physics
    and not by cell numbering: :func:`_restrict` uses this to pick the gap (or
    conductor) side deterministically on every rank. ``cell_tags`` does not
    carry ghost cells, hence the ``scatter_forward`` — same reason as
    ``io/mesh._interface_facet_tags``, and on a partition-boundary port facet
    the far cell *is* a ghost.
    """
    space = fem.functionspace(msh, ("DG", 0))
    chi = fem.Function(space)
    chi.x.array[:] = 0.0
    cell_to_dof = space.dofmap.list.reshape(-1)
    for tag in tags:
        chi.x.array[cell_to_dof[cell_tags.find(tag)]] = 1.0
    chi.x.scatter_forward()
    return chi


def _material_indicator_vector(msh, cell_tags):
    """DG0 vector whose components are the (gap, wire, air) indicators.

    Point evaluation only exists here for *vector* fields
    (:func:`evaluate_vector_field_parallel`), so the three scalar indicators are
    carried as the three components of one DG0 vector.  Evaluating it at the
    quadrature nodes says which material the cell containing each node belongs
    to — the containment gate the plan asks for, taken through the same locate
    path the field sampling uses rather than by arithmetic on the nominal
    geometry.  ``scatter_forward`` for the same reason as :func:`_side_indicator`.
    """
    space = fem.functionspace(msh, ("DG", 0, (3,)))
    chi = fem.Function(space)
    chi.x.array[:] = 0.0
    cell_to_dof = space.dofmap.list.reshape(-1)
    block = space.dofmap.index_map_bs
    for component, tags in enumerate((GAP_TAGS, WIRE_TAGS, (AIR_TAG,))):
        for tag in tags:
            dofs = cell_to_dof[cell_tags.find(tag)]
            chi.x.array[block * dofs + component] = 1.0
    chi.x.scatter_forward()
    return chi


def _gap_arc_quadrature(port_index: int, order: int):
    """Gauss-Legendre nodes on the centreline arc through port ``port_index``.

    The arc runs **terminal to terminal**: from the ``y < 0`` terminal at
    ``φ = −φ_term`` to the ``y > 0`` one at ``+φ_term``, where ``φ_term =
    arcsin(half_y / a)`` is where the gap box's own ``y`` face — the
    conductor/dielectric cut the 201/202 facet tags mark — meets the
    centreline.  ``t̂(0) = +ŷ``, so the resulting ``V`` carries the same sign
    convention as the box/shadow/facet estimators.  Legendre nodes are strictly
    inside ``(−1, 1)``, so the terminals themselves — where a point locates into
    a cell on either side of the material interface — are never sampled; that is
    the "handle the endpoints explicitly" trap discharged by construction rather
    than by an offset.

    **Step 3b-x.**  Until this step the limits were the *nominal wedge*
    ``±gap_angle/2 = ±0.15`` rad.  ``GAP_BURIAL > 0`` makes the meshed
    dielectric wider than that wedge, so the wedge limits stopped 1.013 mm of
    arc short of each terminal — 0.8% of the loop's length carrying 45% of its
    EMF, because it is exactly where the terminal fields are (3b-ix's
    decomposition: wedge 0.4937, buried pair 0.4000, wire 0.0024 × ωM₁₂).  The
    limits are the *geometry's*, and
    :func:`_measure_terminal_angles` asserts the mesh agrees with them to
    ``TERMINAL_ANGLE_TOLERANCE`` before any solve runs, so they cannot drift
    from it again.

    Returns ``(points, tangents, weights)`` with ``weights`` in ``dφ``; the
    Jacobian ``dl = a dφ`` is applied by the caller.
    """
    phi_term = _gap_box_edge_angle()
    return _arc_quadrature(port_index, -phi_term, phi_term, order)


def _arc_quadrature(port_index: int, phi_start: float, phi_end: float, order: int):
    """Gauss-Legendre nodes on ``(phi_start, phi_end)`` of the centreline circle.

    The general form of :func:`_gap_arc_quadrature`, added by step 3b-ix so the
    complement of the gap wedge is integrated by exactly the same machinery as
    the wedge itself — same nodes-strictly-interior property, same ``t̂ = φ̂``
    orientation, so segment voltages add.  With ``(−g/2, +g/2)`` it reproduces
    the gap arc's nodes and weights bit for bit (the midpoint is 0.0).
    """
    nodes, weights = np.polynomial.legendre.leggauss(order)
    midpoint = 0.5 * (phi_start + phi_end)
    half_span = 0.5 * (phi_end - phi_start)
    phi = midpoint + half_span * nodes
    z_c = (-1.0) ** (port_index + 1) * SEPARATION / 2.0
    points = np.column_stack(
        [
            MAJOR_RADIUS * np.cos(phi),
            MAJOR_RADIUS * np.sin(phi),
            np.full_like(phi, z_c),
        ]
    )
    tangents = np.column_stack([-np.sin(phi), np.cos(phi), np.zeros_like(phi)])
    return points, tangents, half_span * weights


def _gap_box_edge_angle() -> float:
    """``|φ|`` at which the centreline leaves the gap box, from the box's own
    half-extents.

    The box spans ``|y| ≤ half_y`` and the centreline has ``y = a sin φ``, so
    the dielectric reaches ``arcsin(half_y / a)``.  Because ``GAP_BURIAL > 0``
    this is strictly outside the nominal wedge — the burial is what makes the
    two end planes meetable — and the ``x`` face is never the binding
    constraint at this aspect ratio (checked in
    :func:`_closure_segments`'s caller gate).
    """
    _, half_y = _gap_half_extents()
    return float(np.arcsin(half_y / MAJOR_RADIUS))


def _closure_segments():
    """The four arcs whose union is the whole centreline circle, in order.

    ``(name, phi_start, phi_end, expected_material)`` with ``t̂ = +φ̂``
    throughout, so the four ``−∫E·t̂ dl`` add to ``−∮E·t̂ dl`` with no sign
    bookkeeping.  ``buried_neg`` is the image of ``buried_pos`` across ``y =
    0``; together with the wedge and the wire arc they tile ``(−φ_box,
    2π − φ_box)``.
    """
    half_gap = 0.5 * GAP_ANGLE
    phi_box = _gap_box_edge_angle()
    return (
        ("buried_neg", -phi_box, -half_gap, "gap"),
        ("gap", -half_gap, half_gap, "gap"),
        ("buried_pos", half_gap, phi_box, "gap"),
        ("wire", phi_box, 2.0 * np.pi - phi_box, "wire"),
    )


def _segment_voltage(
    e_field, port_index: int, phi_start: float, phi_end: float, order: int, comm
) -> complex:
    """``V = −∫E·t̂ dl`` along one centreline segment, ``order``-point Gauss."""
    points, tangents, weights = _arc_quadrature(port_index, phi_start, phi_end, order)
    values, valid = evaluate_vector_field_parallel(e_field, points, comm)
    if not bool(np.all(valid)):
        raise RuntimeError(
            f"port {port_index + 1}: {int((~valid).sum())} of {order} arc "
            "quadrature points located in no cell — the centreline path left "
            "the mesh"
        )
    e_tangential = np.einsum("ij,ij->i", values, tangents)
    return complex(-MAJOR_RADIUS * np.sum(weights * e_tangential))


def _path_voltage(e_field, port_index: int, order: int, comm) -> complex:
    """``V = −∫E·t̂ dl`` terminal to terminal, by ``order``-point Gauss-Legendre.

    Same limits as :func:`_gap_arc_quadrature` — step 3b-x's one change of
    substance.  The wedge-only integral it replaces is still computed, as the
    ``"gap"`` entry of :func:`_closure_segments`, so the retiling identity
    (wedge + both buried segments = this) is measurable off one field.
    """
    phi_term = _gap_box_edge_angle()
    return _segment_voltage(e_field, port_index, -phi_term, phi_term, order, comm)


def _segment_orders(name: str):
    """Which Gauss orders each closure segment is integrated at."""
    if name == "wire":
        return WIRE_ARC_ORDERS
    if name == "gap":
        return GAP_SEGMENT_ORDERS
    return BURIED_ARC_ORDERS


def _closure_decomposition(e_field, comm):
    """Per port, per segment, per order: ``−∫E·t̂ dl`` off one solved field.

    The gap wedge is recomputed here rather than read off
    ``path_voltages_by_order`` so that the σ-sweep solves — which never build
    that sweep — go through exactly the same code path as the σ×1 ones.  The
    two agree by construction: :func:`_gap_arc_quadrature` and the ``"gap"``
    entry of :func:`_closure_segments` are the same interval.
    """
    decomposition = []
    for port_index in range(2):
        record = {}
        for name, phi_start, phi_end, _material in _closure_segments():
            record[name] = {
                order: _segment_voltage(
                    e_field, port_index, phi_start, phi_end, order, comm
                )
                for order in _segment_orders(name)
            }
        decomposition.append(record)
    return decomposition


def _closure_sum(record) -> complex:
    """``−∮E·t̂ dl`` — the four segments at their finest orders."""
    return sum(
        record[name][_segment_orders(name)[-1]]
        for name, _s, _e, _m in _closure_segments()
    )


def _print_closure(label: str, context: str, decomposition, i_driven, omega_m) -> None:
    """Every closure number, per port, before anything is asserted (rank 0 only).

    The plan's instruction is literal — "print all three numbers per port
    before asserting anything" — so the segment voltages, their quadrature
    steps and the three ratios (wedge, wire, sum) all reach the log whether the
    gate that reads them passes or not.
    """
    for port_index, record in enumerate(decomposition):
        for name, _s, _e, material in _closure_segments():
            orders = _segment_orders(name)
            coarse, fine = record[name][orders[0]], record[name][orders[-1]]
            step = abs(fine - coarse) / abs(fine) if abs(fine) > 0.0 else np.inf
            print(
                f"[{label}] {context}: port {port_index + 1} V_{name} "
                f"({material}) = {fine:+.9e} V at order {orders[-1]}, "
                f"{coarse:+.9e} V at {orders[0]} (|dV|/|V| = {step:.4e})",
                flush=True,
            )
        v_gap = record["gap"][_segment_orders("gap")[-1]]
        v_wire = record["wire"][WIRE_ARC_ORDERS[-1]]
        v_buried = (
            record["buried_neg"][BURIED_ARC_ORDERS[-1]]
            + record["buried_pos"][BURIED_ARC_ORDERS[-1]]
        )
        v_sum = _closure_sum(record)

        def _ratio(v):
            return abs((v / i_driven).imag) / omega_m

        print(
            f"[{label}] {context}: port {port_index + 1} closure "
            f"V_gap = {_ratio(v_gap):.6f}, V_buried = {_ratio(v_buried):.6f}, "
            f"V_wire = {_ratio(v_wire):.6f}, sum = {_ratio(v_sum):.6f} x omega*M "
            f"(sum = {v_sum:+.9e} V, I_driven = {i_driven:+.6e} A)",
            flush=True,
        )


def _restrict(chi, expression):
    """``expression`` evaluated on whichever side of the facet ``chi`` marks."""
    return chi("+") * expression("+") + chi("-") * expression("-")


def _tag_volume(msh, cell_tags, tag, comm) -> float:
    one = fem.Constant(msh, np.array(1.0, dtype=np.complex128).item())
    return float(np.real(_reduce(one * _tag_measure(msh, cell_tags, tag), comm)))


def _azimuthal_unit(x):
    """``φ̂`` about the z-axis, regularised inside the sqrt (complex UFL refuses
    ``max_value`` on complex-typed operands)."""
    rho_safe = ufl.sqrt(x[0] ** 2 + x[1] ** 2 + 1e-24)
    return ufl.as_vector([-x[1] / rho_safe, x[0] / rho_safe, 0.0])


def _reaction_impedance(
    msh, cell_tags, e_field, test_tag: int, test_volume: float,
    test_arc_length: float, i_driven: complex, comm
) -> complex:
    """``Z = −∫E·J_test dV /(I_driven I_test)`` — step 1/2's reaction route.

    The landed machinery (``tests/validation/test_port_reaction_impedance.py``,
    ``_reaction``) applied to *this* gapped fixture and *this* solved field:
    ``E`` is whatever the gap drive produced, and ``J_test`` is the unit-current
    azimuthal density over the undriven conductor.  ``J`` is real, so
    ``inner()``'s conjugation of its second argument is a no-op — this is the
    reaction integral ``∫E·J``, not ``∫E·J̄``.

    ``I_test`` is read from the *meshed* conductor the same way the loop
    currents are (``I = j·V/L`` with ``L`` the effective arc length), so a mesh
    that lost part of the tube moves the reference rather than being papered
    over by ``πr²``.  Step 3b-x gates the corrected gap-voltage mutual against
    this; note the comparison is a ratio of two quantities that are *both*
    divided by ``I_driven``, so the loop-current reconstruction cancels out of
    it entirely.
    """
    j_magnitude = DRIVE_CURRENT_A / (np.pi * MINOR_RADIUS**2)
    i_test = j_magnitude * test_volume / test_arc_length
    x = ufl.SpatialCoordinate(msh)
    j_vec = j_magnitude * _azimuthal_unit(x)
    total = _reduce(
        ufl.inner(e_field, j_vec) * _tag_measure(msh, cell_tags, test_tag), comm
    )
    return complex(-total / (i_driven * i_test))


def _measure_terminal_angles(msh, cell_tags, facet_tags, comm):
    """``arcsin(y_extreme/a)`` on each signed half of each port facet pair.

    Step 3b-x's pre-solve gate.  The 201/202 facets are the gap/conductor
    interface, and the far reach of that interface along the loop is the gap
    box's ``y = ±half_y`` face where it cuts the tube — so the estimator's
    integration limit is ``arcsin(y_extreme / a)`` with ``y_extreme`` the
    extreme ``y`` the tagged facets attain.  Reading it off the tags rather
    than off the nominal geometry is the point: the wedge-vs-burial
    discrepancy that cost this chunk two slots was precisely the limits and the
    mesh disagreeing.

    **Why the extreme and not the mean.**  The first form of this gate took the
    area-weighted ``⟨y⟩`` and measured 0.173852 rad against the expected
    0.175335 — a 1.48e-3 deviation
    (`20260807T093604Z_PORT-1-step3bx-gate-n2.log`), and it is known-issues 11,
    not a geometry drift: at ``GAP_OVERHANG = 2e-4 < 6e-4`` the tube protrudes
    through the box's ``−x`` face, so the interface — and the tag — picks up
    *lateral strips* of tube surface at ``|y| < half_y`` alongside the two
    planar discs.  A mean over disc + strips is not the disc's plane.  The
    extreme is: every strip point lies inside the box, so none can exceed the
    face, and the face's nodes sit on it to machine precision (a plane, meshed
    by linear elements, is exact).  The contaminated mean is printed beside the
    gated extreme rather than dropped, since it is the measurement of
    known-issues 11 on this fixture.

    Returns ``(angles, mean_angles)``, each ``[[φ(y>0), φ(y<0)], ...]`` per
    port, in radians.  The first is gated; the second is the diagnostic.
    """
    import dolfinx

    tdim = msh.topology.dim
    x_ufl = ufl.SpatialCoordinate(msh)
    chi_gap = _side_indicator(msh, cell_tags, GAP_TAGS)
    chi_signs = (
        ufl.avg(ufl.conditional(ufl.gt(x_ufl[1], 0.0), 1.0, 0.0)),
        ufl.avg(ufl.conditional(ufl.lt(x_ufl[1], 0.0), 1.0, 0.0)),
    )
    angles, mean_angles = [], []
    for tag in PORT_FACET_TAGS:
        facets = facet_tags.find(tag)
        nodes = dolfinx.cpp.mesh.entities_to_geometry(
            msh._cpp_object, tdim - 1, np.asarray(facets, dtype=np.int32), False
        )
        y_nodes = msh.geometry.x[nodes][:, :, 1]
        facet_side = np.sign(y_nodes.mean(axis=1))

        dS_port = _port_facet_measure(msh, facet_tags, tag)
        both = chi_gap("+") + chi_gap("-")  # exactly one side is gap: = 1
        per_side, per_side_mean = [], []
        for sign, chi_sign in zip((1.0, -1.0), chi_signs):
            selected = y_nodes[facet_side == sign]
            # A rank may own no facet of this half; -inf loses the MAX.
            local = float(np.max(sign * selected)) if selected.size else -np.inf
            y_extreme = sign * float(comm.allreduce(local, op=MPI.MAX))
            per_side.append(float(np.arcsin(y_extreme / MAJOR_RADIUS)))

            area = float(np.real(_reduce(both * chi_sign * dS_port, comm)))
            mean_y = (
                float(
                    np.real(
                        _reduce(both * chi_sign * ufl.avg(x_ufl[1]) * dS_port, comm)
                    )
                )
                / area
            )
            per_side_mean.append(float(np.arcsin(mean_y / MAJOR_RADIUS)))
        angles.append(per_side)
        mean_angles.append(per_side_mean)
    return angles, mean_angles


def _gap_drive(j_magnitude: float):
    """Impressed current density across a gap box, along ``+ŷ``.

    At the gap's location (``x ≈ +a``, ``y ≈ 0``) the azimuthal direction *is*
    ``+ŷ``, so this drives the loop the way a lumped source across the gap
    would.  It is **not** solenoidal — it terminates on the arc end faces, where
    the conduction current ``σE`` takes over and closes the loop — so it is
    driven with ``project_source=False``: the divergence here is the physics,
    not the discrete-gradient artefact `PORT-1` step 2f removes.
    """

    def current_density(x):
        return ufl.as_vector([0.0, j_magnitude, 0.0])

    return current_density


def _solve_gap_ports(comm, label: str, air_padding: float = AIR_PADDING) -> dict:
    """One gapped mesh, one solve per port; returns the measured 2×2 Z and timings.

    ``air_padding`` is the PEC truncation box's half-thickness beyond the coil
    bounding box.  It defaults to the landed fixture's ``AIR_PADDING = 0.08`` —
    every digit-string this module pins is measured at that value.  Step
    3b-xii's discriminator (`test_port_gap_voltage_padding.py`) is the one
    caller that passes anything else; it pins nothing and gates only the
    estimator/control deviation, which is what the box is supposed to move.
    """
    t_mesh = time.perf_counter()
    msh, cell_tags, facet_tags = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=H_FAR,
        air_padding=air_padding,
        wire_resolution=H_WIRE,
        far_resolution=H_FAR,
        port_gap=True,
        gap_angle=GAP_ANGLE,
        gap_burial=GAP_BURIAL,
        gap_overhang=GAP_OVERHANG,
        gap_arc_resolution=GAP_ARC_RESOLUTION,
        comm=comm,
    )
    t_mesh = time.perf_counter() - t_mesh

    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)

    # Every rank, unconditionally, before any facet form: the assembler reaches
    # `create_entity_permutations` lazily and only on a rank that owns
    # integration entities for the subdomain id, and this partition gives each
    # rank exactly one port — so a per-port `dS` form entered the collective on
    # one rank only and hung at -n 2 for 180 s while -n 1 finished in 22.5 s
    # (3b-iv, 2026-08-05; known-issues 9, retired). Hoisting makes it symmetric.
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    half_xz, half_y = _gap_half_extents()
    gap_length = 2.0 * half_y
    # Cross-section from the *meshed* gap volume, so a mesh that lost part of
    # the box would show up in V rather than being papered over by analytic
    # geometry.  Step 3b-i measured meshed/analytic = 1.000000000000 here.
    gap_volumes = [_tag_volume(msh, cell_tags, t, comm) for t in GAP_TAGS]
    gap_areas = [v / gap_length for v in gap_volumes]

    # Effective arc length of each meshed conductor: the gap box buries into the
    # arc ends, so a(2π − g) overstates it by the 3.6% step 3b-i measured.
    wire_volumes = [_tag_volume(msh, cell_tags, t, comm) for t in WIRE_TAGS]
    arc_lengths = [v / (np.pi * MINOR_RADIUS**2) for v in wire_volumes]

    x_ufl = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_unit(x_ufl)
    y_hat = ufl.as_vector([0.0, 1.0, 0.0])

    # The terminals.  Areas are measured once, before any solve, so a wrong
    # surface fails the geometry gate rather than showing up as a wrong voltage.
    chi_gap = _side_indicator(msh, cell_tags, GAP_TAGS)
    chi_wire = _side_indicator(msh, cell_tags, WIRE_TAGS)
    # Split the disc *pair* by the sign of y: the two discs of a port face
    # opposite ways along ŷ, and the plan's first instruction is to look at them
    # separately, because a sign error between them reproduces 3b-ii's symptom
    # exactly.  y is single-valued on the facet, so `avg` is the value.
    chi_ypos = ufl.avg(ufl.conditional(ufl.gt(x_ufl[1], 0.0), 1.0, 0.0))
    chi_yneg = ufl.avg(ufl.conditional(ufl.lt(x_ufl[1], 0.0), 1.0, 0.0))
    disc_measures = [
        _port_facet_measure(msh, facet_tags, t) for t in PORT_FACET_TAGS
    ]
    disc_areas, disc_areas_split = [], []
    for dS_port in disc_measures:
        both = chi_gap("+") + chi_gap("-")  # exactly one side is gap: = 1
        disc_areas.append(float(np.real(_reduce(both * dS_port, comm))))
        disc_areas_split.append(
            [
                float(np.real(_reduce(both * chi_sign * dS_port, comm)))
                for chi_sign in (chi_ypos, chi_yneg)
            ]
        )

    # Step 3b-x's pre-solve gate: the estimator's integration limits against
    # the terminals the mesh actually carries.  This is deliberately a hard
    # failure *here* rather than an assertion in a test — if the limits and the
    # geometry disagree, every voltage the solves produce is an integral over
    # the wrong interval, and buying two solves to report that is waste.
    terminal_angles, terminal_angles_mean = _measure_terminal_angles(
        msh, cell_tags, facet_tags, comm
    )
    phi_term_expected = _gap_box_edge_angle()
    if comm.rank == 0:
        print(
            f"[{label}] terminal angles from facet tags "
            f"{PORT_FACET_TAGS}: "
            + "; ".join(
                f"port {k + 1} y>0 {pair[0]:+.9f}, y<0 {pair[1]:+.9f} rad"
                for k, pair in enumerate(terminal_angles)
            )
            + f" (expected +-{phi_term_expected:.9f} = arcsin(half_y/a), "
            f"nominal wedge +-{0.5 * GAP_ANGLE:.9f}, tolerance "
            f"{TERMINAL_ANGLE_TOLERANCE:.1e})",
            flush=True,
        )
        print(
            f"[{label}] known-issues 11 diagnostic (printed, not gated): "
            "area-weighted mean over the same tags gives "
            + "; ".join(
                f"port {k + 1} y>0 {pair[0]:+.9f}, y<0 {pair[1]:+.9f} rad"
                for k, pair in enumerate(terminal_angles_mean)
            )
            + " — the deficit is the lateral strips the tag picks up at "
            f"gap_overhang = {GAP_OVERHANG:.1e} < 6e-4",
            flush=True,
        )
    for k, pair in enumerate(terminal_angles):
        for s, (measured, expected) in enumerate(
            zip(pair, (phi_term_expected, -phi_term_expected))
        ):
            if abs(measured - expected) >= TERMINAL_ANGLE_TOLERANCE:
                raise RuntimeError(
                    f"port {k + 1}, {'y>0' if s == 0 else 'y<0'} terminal: the "
                    f"facet tags put the conductor/dielectric cut at "
                    f"{measured:+.9f} rad, the estimator's limit is "
                    f"{expected:+.9f} rad (difference "
                    f"{measured - expected:+.3e} >= "
                    f"{TERMINAL_ANGLE_TOLERANCE:.1e}) — the integration limits "
                    "have drifted from the meshed geometry"
                )

    # Where the arc quadrature nodes actually land, measured once before any
    # solve: a node inside the conductor (or in air) would make the path
    # integral cross a material it has no business in, and it should fail as
    # geometry rather than as a voltage.  The finest order is the strict
    # superset test — Legendre nodes of different orders interleave, so both
    # sets are checked.
    chi_material = _material_indicator_vector(msh, cell_tags)
    path_node_materials = {}
    for port_index in range(2):
        for order in (PATH_QUADRATURE_ORDERS[0], PATH_QUADRATURE_ORDERS[-1]):
            points, _, _ = _gap_arc_quadrature(port_index, order)
            values, valid = evaluate_vector_field_parallel(chi_material, points, comm)
            path_node_materials[(port_index, order)] = {
                "valid": valid,
                "gap": np.real(values[:, 0]),
                "wire": np.real(values[:, 1]),
                "air": np.real(values[:, 2]),
            }
    if comm.rank == 0:
        for (port_index, order), rec in sorted(path_node_materials.items()):
            print(
                f"[{label}] port {port_index + 1} arc nodes (order {order}): "
                f"located {int(rec['valid'].sum())}/{order}, gap-tagged "
                f"{int(np.round(rec['gap'].sum()))}, wire-tagged "
                f"{int(np.round(rec['wire'].sum()))}, air-tagged "
                f"{int(np.round(rec['air'].sum()))}",
                flush=True,
            )

    # Step 3b-ix's precondition, the inverse of the gap arc's: the wire arc's
    # nodes must be *wire*-tagged and the buried segments' *gap*-tagged, or the
    # decomposition is not a decomposition of the loop.  Same DG0 indicator,
    # same locate path, same pre-solve placement as the wedge check above.
    closure_node_materials = {}
    for port_index in range(2):
        for name, phi_start, phi_end, material in _closure_segments():
            for order in _segment_orders(name):
                points, _, _ = _arc_quadrature(port_index, phi_start, phi_end, order)
                values, valid = evaluate_vector_field_parallel(
                    chi_material, points, comm
                )
                closure_node_materials[(port_index, name, order)] = {
                    "valid": valid,
                    "expected": material,
                    "gap": np.real(values[:, 0]),
                    "wire": np.real(values[:, 1]),
                    "air": np.real(values[:, 2]),
                }
    if comm.rank == 0:
        phi_box = _gap_box_edge_angle()
        print(
            f"[{label}] closure segments: gap wedge +-{0.5 * GAP_ANGLE:.6f} rad, "
            f"gap box reaches +-{phi_box:.6f} rad (buried {phi_box - 0.5 * GAP_ANGLE:.6e} "
            f"rad = {MAJOR_RADIUS * (phi_box - 0.5 * GAP_ANGLE):.6e} m per side), "
            f"wire arc {2.0 * (np.pi - phi_box):.6f} rad = "
            f"{MAJOR_RADIUS * 2.0 * (np.pi - phi_box):.6e} m",
            flush=True,
        )
        for (port_index, name, order), rec in sorted(closure_node_materials.items()):
            print(
                f"[{label}] port {port_index + 1} {name} nodes (order {order}): "
                f"located {int(rec['valid'].sum())}/{order}, gap-tagged "
                f"{int(np.round(rec['gap'].sum()))}, wire-tagged "
                f"{int(np.round(rec['wire'].sum()))}, air-tagged "
                f"{int(np.round(rec['air'].sum()))} (expected {rec['expected']})",
                flush=True,
            )

    z_matrix = np.zeros((2, 2), dtype=complex)
    currents = {}
    solve_times = []
    for col, driven_gap in enumerate(GAP_TAGS):
        j_magnitude = DRIVE_CURRENT_A / gap_areas[col]
        problem = TimeHarmonicProblem(
            mesh=msh,
            frequency_hz=FREQUENCY_HZ,
            material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
            cell_tags=cell_tags,
            material_map={
                tag: HomogeneousMaterial(
                    sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0
                )
                for tag in WIRE_TAGS
            },
            boundary_condition="pec_zero_tangential_a",
        )
        solver = TimeHarmonicSolver(problem, degree=1)
        comm.Barrier()
        t0 = time.perf_counter()
        fields = solver.solve(
            current_density=_gap_drive(j_magnitude),
            subdomain_ids=[driven_gap],
            project_source=False,
        )
        comm.Barrier()
        solve_times.append(time.perf_counter() - t0)

        e = fields.e_complex
        # I in *both* loops (the undriven one is the open-circuit check), and V
        # across both gaps; only the column's own entries are kept in Z.
        loop_currents = [
            SIGMA_WIRE_S_PER_M
            * _reduce(ufl.inner(e, phi_hat) * _tag_measure(msh, cell_tags, tag), comm)
            / arc_lengths[k]
            for k, tag in enumerate(WIRE_TAGS)
        ]
        gap_voltages = [
            -_reduce(ufl.inner(e, y_hat) * _tag_measure(msh, cell_tags, tag), comm)
            / gap_areas[k]
            for k, tag in enumerate(GAP_TAGS)
        ]
        # Diagnostic (printed, never gated): the same average restricted to the
        # tube's *shadow*.  At 3b-ii's 1 mm overhang the box cross-section was
        # 1.44e-4 m^2 against the tube's pi*r^2 = 7.85e-5, so 45.5% of the
        # ŷ-lines the full-box average takes never passed through conductor at
        # either end — they sampled fringing air, not the gap the loop current
        # sees, and the two averages disagreed by a factor 2.3.  Step 3b-iii
        # shrinks the overhang: if the fringe is the whole story these two
        # numbers must now converge toward each other.
        shadow_voltages = []
        for k, tag in enumerate(GAP_TAGS):
            z_c = (-1.0) ** (k + 1) * SEPARATION / 2.0
            r2 = (x_ufl[0] - MAJOR_RADIUS) ** 2 + (x_ufl[2] - z_c) ** 2
            chi = ufl.conditional(ufl.lt(r2, MINOR_RADIUS**2), 1.0, 0.0)
            dx_tag = _tag_measure(msh, cell_tags, tag)
            area = float(np.real(_reduce(chi * dx_tag, comm))) / gap_length
            shadow_voltages.append(
                -_reduce(chi * ufl.inner(e, y_hat) * dx_tag, comm) / area
            )
        # The step: V from the terminal discs alone.  <E·ŷ> over the disc pair,
        # taken on the *gap* side of the interface, times the ŷ chord that joins
        # the two terminals — i.e. −∫E·dl over exactly the conductor
        # cross-section, with no corner cells and no non-conductor path width.
        # The conductor-side reading is assembled too and printed beside it: E·ŷ
        # is the facet-normal component and is discontinuous there, so the size
        # of that jump is the cost of the restriction choice, and it belongs in
        # the log rather than in a comment.
        facet_voltages, facet_diagnostics = [], []
        for k, dS_port in enumerate(disc_measures):
            e_y = ufl.inner(e, y_hat)
            mean_gap = _reduce(_restrict(chi_gap, e_y) * dS_port, comm) / disc_areas[k]
            mean_wire = (
                _reduce(_restrict(chi_wire, e_y) * dS_port, comm) / disc_areas[k]
            )
            per_disc = [
                _reduce(_restrict(chi_gap, e_y) * chi_sign * dS_port, comm)
                / disc_areas_split[k][s]
                for s, chi_sign in enumerate((chi_ypos, chi_yneg))
            ]
            facet_voltages.append(-mean_gap * gap_length)
            facet_diagnostics.append(
                {
                    "mean_gap": mean_gap,
                    "mean_wire": mean_wire,
                    "per_disc": per_disc,
                }
            )

        # The step: V from the tangential component along the centreline arc.
        # Two resolutions per port off this one solve; the fine one is what Z
        # is built from, the coarse one certifies it.
        path_voltages_by_order = {
            order: [
                _path_voltage(e, port_index, order, comm) for port_index in range(2)
            ]
            for order in PATH_QUADRATURE_ORDERS
        }
        # 3b-vii: the gated V is the fine order of the *gated* pair, so the
        # number Z is built from is exactly the one the precondition certifies;
        # the rest of the sweep is the printed rate diagnostic.
        path_voltages = path_voltages_by_order[PATH_QUADRATURE_GATE_ORDERS[-1]]

        # Step 3b-ix (1): the rest of the loop, off this same field.
        closure = _closure_decomposition(e, comm)

        # Step 3b-x: the retiling identity's right-hand side, at orders matched
        # to the corrected estimator's.
        half_gap = 0.5 * GAP_ANGLE
        phi_term = _gap_box_edge_angle()
        fine = PATH_QUADRATURE_GATE_ORDERS[-1]
        retiling = [
            _segment_voltage(e, p, -half_gap, half_gap, fine, comm)
            + _segment_voltage(
                e, p, -phi_term, -half_gap, RETILING_BURIED_ORDER, comm
            )
            + _segment_voltage(
                e, p, half_gap, phi_term, RETILING_BURIED_ORDER, comm
            )
            for p in range(2)
        ]

        i_driven = loop_currents[col]

        # Step 3b-x anchor (2): the same field read by the landed reaction
        # route, with the *undriven* conductor as the test source.  No extra
        # solve — this is a second functional of the field the gap drive
        # already produced.
        z_reaction = _reaction_impedance(
            msh,
            cell_tags,
            e,
            WIRE_TAGS[1 - col],
            wire_volumes[1 - col],
            arc_lengths[1 - col],
            i_driven,
            comm,
        )

        currents[driven_gap] = {
            "driven": i_driven,
            "undriven": loop_currents[1 - col],
            "z_reaction": z_reaction,
            "retiling": retiling,
            "voltages": path_voltages,
            "closure": closure,
            "path_voltages_by_order": path_voltages_by_order,
            "facet_voltages": facet_voltages,
            "box_voltages": gap_voltages,
            "shadow_voltages": shadow_voltages,
        }
        for row in range(2):
            z_matrix[row, col] = path_voltages[row] / i_driven

        if comm.rank == 0:
            for port_index in range(2):
                for j, order in enumerate(PATH_QUADRATURE_ORDERS):
                    v = path_voltages_by_order[order][port_index]
                    if j == 0:
                        step = ""
                    else:
                        prev = path_voltages_by_order[PATH_QUADRATURE_ORDERS[j - 1]][
                            port_index
                        ]
                        step = f", |dV|/|V| vs previous order {abs(v - prev) / abs(v):.4e}"
                    print(
                        f"[{label}] port {col + 1} driven: V_path port "
                        f"{port_index + 1} order {order:5d} = {v:+.9e} V{step}",
                        flush=True,
                    )

        if comm.rank == 0:
            for k, diag in enumerate(facet_diagnostics):
                print(
                    f"[{label}] port {col + 1} driven: disc pair {PORT_FACET_TAGS[k]} "
                    f"<E.yhat> gap side = {diag['mean_gap']:+.6e}, wire side = "
                    f"{diag['mean_wire']:+.6e} V/m (jump ratio "
                    f"{abs(diag['mean_wire']) / abs(diag['mean_gap']):.4e}); "
                    f"per disc y>0 {diag['per_disc'][0]:+.6e}, y<0 "
                    f"{diag['per_disc'][1]:+.6e} V/m (ratio "
                    f"{(diag['per_disc'][0] / diag['per_disc'][1]):+.6f}); "
                    f"V_facet = {facet_voltages[k]:+.6e} V",
                    flush=True,
                )

        if comm.rank == 0:
            print(
                f"[{label}] port {col + 1} driven (tag {driven_gap}): "
                f"I_driven = {i_driven:+.6e} A, I_undriven = "
                f"{loop_currents[1 - col]:+.6e} A (ratio "
                f"{abs(loop_currents[1 - col]) / abs(i_driven):.4e}); "
                f"V1_facet = {facet_voltages[0]:+.6e} V, V2_facet = "
                f"{facet_voltages[1]:+.6e} V",
                flush=True,
            )
            omega_m = OMEGA * mutual_inductance(
                MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION
            )
            # Four estimators, one solve: the gated path route beside the three
            # excluded ones (box 3b-ii/3b-iii, tube shadow, facet 3b-v).  If the
            # path number lands in the shadow average's 0.687-0.814 band too,
            # the ~0.78 deficit is not the sampling geometry at all, and that is
            # the finding rather than a failure of this estimator.
            def _ratio(v):
                return abs((v[1 - col] / i_driven).imag) / omega_m

            print(
                f"[{label}] port {col + 1} diagnostic: mutual from path V = "
                f"{_ratio(path_voltages):.6f} x omega*M, from facet V = "
                f"{_ratio(facet_voltages):.6f} x omega*M, from full-box V = "
                f"{_ratio(gap_voltages):.6f} x omega*M, from tube-shadow V = "
                f"{_ratio(shadow_voltages):.6f} x omega*M "
                f"(V_path = {path_voltages[1 - col]:+.6e}, V_facet = "
                f"{facet_voltages[1 - col]:+.6e}, V_box = "
                f"{gap_voltages[1 - col]:+.6e}, V_shadow = "
                f"{shadow_voltages[1 - col]:+.6e} V); driven-gap V_path = "
                f"{path_voltages[col]:+.6e} V",
                flush=True,
            )
            _print_closure(label, f"port {col + 1} driven", closure, i_driven, omega_m)
            v_undriven = path_voltages[1 - col]
            z_gap = v_undriven / i_driven
            print(
                f"[{label}] port {col + 1} driven: terminal-to-terminal "
                f"Im Z_gap = {z_gap.imag:+.9e} Ohm "
                f"({abs(z_gap.imag) / omega_m:.6f} x omega*M), reaction-route "
                f"Im Z = {z_reaction.imag:+.9e} Ohm "
                f"({abs(z_reaction.imag) / omega_m:.6f} x omega*M), ratio "
                f"{abs(z_gap.imag) / abs(z_reaction.imag):.6f} "
                f"(Re Z_reaction = {z_reaction.real:+.6e} Ohm)",
                flush=True,
            )

    # ------------------------------------------------------------------
    # Step 3b-x-b: the same-fixture reaction *reference*.  One extra solve on
    # this same mesh, with the conductors made non-conducting and the source
    # impressed — the landed step-1/2 configuration transplanted onto the gapped
    # mesh.  Step 3b-x measured why the anchor cannot be read off the production
    # field: over a σ = 800 S/m arc of an *open* loop the reaction integral
    # returns the ohmic wire term, not the mutual (factor 244,
    # `20260807T093906Z_PORT-1-step3bx-gate-n2.log`).  At σ = 0 the test region
    # carries the full induced field again and −∫E·J₂ is the EMF.
    #
    # Drive and test regions are each the *loop footprint* — a wire tag together
    # with its own gap box — so the impressed current is a closed loop rather
    # than an open arc that would terminate on the arc-end faces with nothing to
    # carry it onward.  Both currents use the landed route's own normalisation,
    # ``I = ∫J·φ̂ dV/(2πa)``: for a uniform φ̂ density over a torus that is the
    # loop current exactly, and it is the convention `_reaction` already uses.
    # `project_source` stays at step 2f's default: the gap box bulges past the
    # tube, so the uniform density over the footprint is not exactly solenoidal,
    # and the projection is precisely the machinery that removes the
    # discrete-gradient part of such a source (unlike `_gap_drive`, whose
    # divergence *is* the physics because σE closes it).
    omega_m_ref = OMEGA * mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    control_regions = [(WIRE_TAGS[k], GAP_TAGS[k]) for k in range(2)]
    control_j = DRIVE_CURRENT_A / (np.pi * MINOR_RADIUS**2)
    loop_length = 2.0 * np.pi * MAJOR_RADIUS
    control_volumes = [
        float(
            np.real(
                _reduce(
                    fem.Constant(msh, np.array(1.0, dtype=np.complex128).item())
                    * _tags_measure(msh, cell_tags, tags),
                    comm,
                )
            )
        )
        for tags in control_regions
    ]
    control_currents = [control_j * v / loop_length for v in control_volumes]

    control_problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map=None,
        boundary_condition="pec_zero_tangential_a",
    )
    control_solver = TimeHarmonicSolver(control_problem, degree=1)
    comm.Barrier()
    t0 = time.perf_counter()
    control_fields = control_solver.solve(
        current_density=lambda x: control_j * _azimuthal_unit(x),
        subdomain_ids=list(control_regions[0]),
    )
    comm.Barrier()
    t_control = time.perf_counter() - t0

    e_control = control_fields.e_complex
    # Step 2f: the *driven* current is the projected J', not the prescribed J.
    projection = control_solver.projection()
    i_control_prime = (
        float(
            np.real(
                _reduce(
                    ufl.inner(projection.current, _azimuthal_unit(x_ufl))
                    * _tags_measure(msh, cell_tags, control_regions[0]),
                    comm,
                )
            )
        )
        / loop_length
    )
    control_reaction = {}
    for name, tags in (
        ("footprint", control_regions[1]),
        ("wire_only", (WIRE_TAGS[1],)),
    ):
        volume = float(
            np.real(
                _reduce(
                    fem.Constant(msh, np.array(1.0, dtype=np.complex128).item())
                    * _tags_measure(msh, cell_tags, tags),
                    comm,
                )
            )
        )
        i_test = control_j * volume / loop_length
        # J is real, so inner()'s conjugation of the second argument is a no-op:
        # this is ∫E·J, not ∫E·J̄.
        total = _reduce(
            ufl.inner(e_control, control_j * phi_hat)
            * _tags_measure(msh, cell_tags, tags),
            comm,
        )
        control_reaction[name] = complex(
            -total / (i_control_prime * i_test)
        )
    control = {
        "z21": control_reaction["footprint"],
        "z21_wire_only": control_reaction["wire_only"],
        "current_prescribed": control_currents[0],
        "current_prime": i_control_prime,
        "imag_ratio": projection.imag_ratio,
        "volumes": control_volumes,
        "solve_time": t_control,
    }
    if comm.rank == 0:
        print(
            f"\n[{label}] step 3b-x-b control (sigma = 0 everywhere, impressed "
            f"azimuthal drive over the wire+gap footprint of loop 1, "
            f"project_source on): solve {t_control:.1f} s; footprint volumes "
            f"{control_volumes[0]:.6e}, {control_volumes[1]:.6e} m^3 "
            f"(torus pi*r^2*2*pi*a = {np.pi * MINOR_RADIUS**2 * loop_length:.6e}); "
            f"I_prescribed = {control_currents[0]:+.6e} A, I' (projected) = "
            f"{i_control_prime:+.6e} A (ratio "
            f"{i_control_prime / control_currents[0]:.6f}), projection "
            f"imag_ratio = {projection.imag_ratio:.3e}",
            flush=True,
        )
        print(
            f"[{label}] step 3b-x-b reference: Im Z21 = "
            f"{control['z21'].imag:+.9e} Ohm "
            f"({abs(control['z21'].imag) / omega_m_ref:.6f} x omega*M), "
            f"Re Z21 = {control['z21'].real:+.6e} Ohm; test over the wire tag "
            f"alone = {control['z21_wire_only'].imag:+.9e} Ohm "
            f"({abs(control['z21_wire_only'].imag) / omega_m_ref:.6f} x "
            f"omega*M — the same field over 94.4% of the loop, printed as the "
            "measure of how much of the EMF the gap span carries)",
            flush=True,
        )

    # ------------------------------------------------------------------
    # Step 3b-xiii: the σ ladder on the control.  Everything above is repeated
    # verbatim except for the material map: the loop footprints (wire ∪ gap box
    # — the loop stays *closed*, which is the whole point of the corner being
    # filled) are given σ through the same DG0 map the production solves use.
    # The drive stays impressed over loop 1's footprint and the normalisation
    # stays ``I' = ∫J'·φ̂ dV / (2πa)``, the projected *impressed* current: if
    # the denominator changed with σ the ladder would measure the normalisation
    # rather than the physics.  At σ > 0 the footprint also carries a
    # conduction current σ∫E·φ̂/(2πa); it is computed and printed as a
    # diagnostic (and as the second, total-current normalisation) so the two
    # readings are on the record side by side, but the gate-facing number is
    # the one whose code path is byte-identical to the σ = 0 control.
    control_sigma_ladder = []
    for sigma in CONTROL_SIGMA_LADDER:
        ladder_problem = TimeHarmonicProblem(
            mesh=msh,
            frequency_hz=FREQUENCY_HZ,
            material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
            cell_tags=cell_tags,
            material_map={
                tag: HomogeneousMaterial(sigma=sigma, epsilon_r=1.0, mu_r=1.0)
                for tags in control_regions
                for tag in tags
            },
            boundary_condition="pec_zero_tangential_a",
        )
        ladder_solver = TimeHarmonicSolver(ladder_problem, degree=1)
        comm.Barrier()
        t0 = time.perf_counter()
        ladder_fields = ladder_solver.solve(
            current_density=lambda x: control_j * _azimuthal_unit(x),
            subdomain_ids=list(control_regions[0]),
        )
        comm.Barrier()
        t_ladder = time.perf_counter() - t0

        e_ladder = ladder_fields.e_complex
        ladder_projection = ladder_solver.projection()
        i_ladder_prime = (
            float(
                np.real(
                    _reduce(
                        ufl.inner(ladder_projection.current, _azimuthal_unit(x_ufl))
                        * _tags_measure(msh, cell_tags, control_regions[0]),
                        comm,
                    )
                )
            )
            / loop_length
        )
        # The induced conduction current in the driven footprint, same
        # convention: I = ∫σE·φ̂ dV / (2πa).
        i_ladder_conduction = complex(
            sigma
            * _reduce(
                ufl.inner(e_ladder, phi_hat)
                * _tags_measure(msh, cell_tags, control_regions[0]),
                comm,
            )
            / loop_length
        )
        ladder_reaction = {}
        for name, tags in (
            ("footprint", control_regions[1]),
            ("wire_only", (WIRE_TAGS[1],)),
        ):
            volume = float(
                np.real(
                    _reduce(
                        fem.Constant(
                            msh, np.array(1.0, dtype=np.complex128).item()
                        )
                        * _tags_measure(msh, cell_tags, tags),
                        comm,
                    )
                )
            )
            i_test = control_j * volume / loop_length
            total = _reduce(
                ufl.inner(e_ladder, control_j * phi_hat)
                * _tags_measure(msh, cell_tags, tags),
                comm,
            )
            ladder_reaction[name] = complex(-total / (i_ladder_prime * i_test))
        ladder_record = {
            "sigma": sigma,
            "delta_over_r": np.sqrt(2.0 / (OMEGA * MU_0 * sigma)) / MINOR_RADIUS,
            "z21": ladder_reaction["footprint"],
            "z21_wire_only": ladder_reaction["wire_only"],
            "current_prime": i_ladder_prime,
            "current_conduction": i_ladder_conduction,
            "imag_ratio": ladder_projection.imag_ratio,
            "solve_time": t_ladder,
        }
        control_sigma_ladder.append(ladder_record)
        if comm.rank == 0:
            print(
                f"\n[{label}] step 3b-xiii control ladder sigma = "
                f"{sigma:.3e} S/m (closed wire+gap footprints, impressed drive, "
                f"delta/r_wire = {ladder_record['delta_over_r']:.3f}): solve "
                f"{t_ladder:.1f} s, I' (projected impressed) = "
                f"{i_ladder_prime:+.6e} A, I_conduction = "
                f"{i_ladder_conduction.real:+.6e}{i_ladder_conduction.imag:+.6e}j A "
                f"(|I_cond/I'| = {abs(i_ladder_conduction) / abs(i_ladder_prime):.4e}), "
                f"projection imag_ratio = {ladder_projection.imag_ratio:.3e}",
                flush=True,
            )
            print(
                f"[{label}] step 3b-xiii control(sigma = {sigma:.3e}): Im Z21 = "
                f"{ladder_record['z21'].imag:+.9e} Ohm "
                f"({abs(ladder_record['z21'].imag) / omega_m_ref:.6f} x omega*M), "
                f"Re Z21 = {ladder_record['z21'].real:+.6e} Ohm; wire tag alone "
                f"{abs(ladder_record['z21_wire_only'].imag) / omega_m_ref:.6f} x "
                f"omega*M",
                flush=True,
            )

    # ------------------------------------------------------------------
    # Step 3b-ix (2): the σ scaling.  Same mesh, same drive, one extra solve
    # per scale, driving one port only — the ratio that carries the signature
    # is V_gap on the *undriven* port, so the second column adds cost without
    # adding information.  σ enters in two places and both must move together:
    # the material map (the physics) and the loop-current reconstruction
    # I = σ⟨E·φ̂⟩A (the measurement).  Reading I with the unscaled σ would
    # manufacture the monotone trend this step is looking for.
    sigma_sweep = []
    col = SIGMA_SWEEP_DRIVEN_COLUMN
    driven_gap = GAP_TAGS[col]
    for scale in SIGMA_SCALES:
        sigma = scale * SIGMA_WIRE_S_PER_M
        problem = TimeHarmonicProblem(
            mesh=msh,
            frequency_hz=FREQUENCY_HZ,
            material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
            cell_tags=cell_tags,
            material_map={
                tag: HomogeneousMaterial(sigma=sigma, epsilon_r=1.0, mu_r=1.0)
                for tag in WIRE_TAGS
            },
            boundary_condition="pec_zero_tangential_a",
        )
        solver = TimeHarmonicSolver(problem, degree=1)
        comm.Barrier()
        t0 = time.perf_counter()
        fields = solver.solve(
            current_density=_gap_drive(DRIVE_CURRENT_A / gap_areas[col]),
            subdomain_ids=[driven_gap],
            project_source=False,
        )
        comm.Barrier()
        t_sigma = time.perf_counter() - t0

        e = fields.e_complex
        loop_currents = [
            sigma
            * _reduce(ufl.inner(e, phi_hat) * _tag_measure(msh, cell_tags, tag), comm)
            / arc_lengths[k]
            for k, tag in enumerate(WIRE_TAGS)
        ]
        i_driven = loop_currents[col]
        closure = _closure_decomposition(e, comm)
        record = {
            "scale": scale,
            "sigma": sigma,
            "delta_over_r": np.sqrt(2.0 / (OMEGA * MU_0 * sigma)) / MINOR_RADIUS,
            "driven": i_driven,
            "undriven": loop_currents[1 - col],
            "closure": closure,
            "solve_time": t_sigma,
        }
        sigma_sweep.append(record)
        if comm.rank == 0:
            print(
                f"\n[{label}] sigma x{scale:g}: sigma = {sigma:.3e} S/m, "
                f"delta/r_wire = {record['delta_over_r']:.3f}, solve "
                f"{t_sigma:.1f} s, I_driven = {i_driven:+.6e} A, "
                f"|I_undriven/I_driven| = "
                f"{abs(record['undriven']) / abs(i_driven):.4e}",
                flush=True,
            )
            _print_closure(label, f"sigma x{scale:g}", closure, i_driven, omega_m_ref)

    # ------------------------------------------------------------------
    # Step 3b-xiv: the σ ladder on the *production gapped* route.  Same mesh,
    # same drive, same gap boxes, same estimator — only the conductor's σ moves,
    # down to zero.  Two normalisations are carried per rung and both are
    # printed, because the record's own normalisation is the thing that dies at
    # σ = 0:
    #
    #   I_cond = σ ∫_wire E·φ̂ dV / L_arc — the landed route's reconstruction,
    #       identically zero at σ = 0 by construction, not by physics;
    #   I′     = ∫_gapbox J·ŷ dV / L_gap — the *impressed* drive current, which
    #       is DRIVE_CURRENT_A by construction of ``_gap_drive`` and does not
    #       depend on σ at all.
    #
    # The ladder is read on I′.  That is only legitimate if the two agree where
    # both are defined, so the σ = 800 rung is solved here too and its
    # I′-normalised estimator is compared against the record's I_cond-normalised
    # 0.894543 — the ratio |I_cond/I′| is exactly the conversion factor, and it
    # is the negative control besides.
    production_sigma_ladder = []
    ladder_col = PRODUCTION_LADDER_DRIVEN_COLUMN
    ladder_gap = GAP_TAGS[ladder_col]
    ladder_j = DRIVE_CURRENT_A / gap_areas[ladder_col]
    for sigma in (*PRODUCTION_SIGMA_LADDER, SIGMA_WIRE_S_PER_M):
        ladder_problem = TimeHarmonicProblem(
            mesh=msh,
            frequency_hz=FREQUENCY_HZ,
            material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
            cell_tags=cell_tags,
            material_map={
                tag: HomogeneousMaterial(sigma=sigma, epsilon_r=1.0, mu_r=1.0)
                for tag in WIRE_TAGS
            },
            boundary_condition="pec_zero_tangential_a",
        )
        ladder_solver = TimeHarmonicSolver(ladder_problem, degree=1)
        comm.Barrier()
        t0 = time.perf_counter()
        ladder_fields = ladder_solver.solve(
            current_density=_gap_drive(ladder_j),
            subdomain_ids=[ladder_gap],
            project_source=False,
        )
        comm.Barrier()
        t_rung = time.perf_counter() - t0

        e_rung = ladder_fields.e_complex
        # The impressed current, assembled rather than asserted from j*A: the
        # meshed gap box is not exactly the analytic box, and this ladder's whole
        # normalisation rests on it.
        i_impressed = (
            _reduce(
                ufl.inner(_gap_drive(ladder_j)(x_ufl), y_hat)
                * _tag_measure(msh, cell_tags, ladder_gap),
                comm,
            )
            / gap_length
        )
        i_conduction = (
            sigma
            * _reduce(
                ufl.inner(e_rung, phi_hat)
                * _tag_measure(msh, cell_tags, WIRE_TAGS[ladder_col]),
                comm,
            )
            / arc_lengths[ladder_col]
        )
        v_undriven = _path_voltage(
            e_rung, 1 - ladder_col, PATH_QUADRATURE_GATE_ORDERS[-1], comm
        )
        z_impressed = v_undriven / i_impressed
        rung = {
            "sigma": sigma,
            "driven_impressed": i_impressed,
            "driven_conduction": i_conduction,
            "conduction_ratio": abs(i_conduction) / abs(i_impressed),
            "v_undriven": v_undriven,
            "z_impressed": z_impressed,
            "estimator_impressed": abs(z_impressed.imag) / omega_m_ref,
            "solve_time": t_rung,
        }
        # The record's normalisation, kept where it is defined and left None
        # where σ = 0 makes it identically zero — never silently replaced.
        if abs(i_conduction) > 0.0:
            z_cond = v_undriven / i_conduction
            rung["z_conduction"] = z_cond
            rung["estimator_conduction"] = abs(z_cond.imag) / omega_m_ref
        else:
            rung["z_conduction"] = None
            rung["estimator_conduction"] = None
        production_sigma_ladder.append(rung)
        if comm.rank == 0:
            est_cond = rung["estimator_conduction"]
            print(
                f"\n[{label}] step 3b-xiv gapped ladder sigma = {sigma:.3e} S/m: "
                f"solve {t_rung:.1f} s, I' (impressed) = {i_impressed:+.6e} A "
                f"(prescribed {DRIVE_CURRENT_A:+.6e}), I_conduction = "
                f"{i_conduction.real:+.6e}{i_conduction.imag:+.6e}j A, "
                f"|I_cond/I'| = {rung['conduction_ratio']:.6e}",
                flush=True,
            )
            print(
                f"[{label}] step 3b-xiv gapped(sigma = {sigma:.3e}): V_undriven = "
                f"{v_undriven:+.9e} V, Im Z_gap/I' = {z_impressed.imag:+.9e} Ohm "
                f"({rung['estimator_impressed']:.6f} x omega*M12); on the "
                "record's own I_cond normalisation "
                + (
                    f"{est_cond:.6f} x omega*M12"
                    if est_cond is not None
                    else "undefined (I_cond == 0 identically at sigma = 0)"
                ),
                flush=True,
            )

    if comm.rank == 0:
        delta = np.sqrt(2.0 / (OMEGA * MU_0 * SIGMA_WIRE_S_PER_M))
        print(
            f"\n[{label}] {ncells} cells, mesh {t_mesh:.1f} s, solves "
            + ", ".join(f"{t:.1f} s" for t in solve_times)
            + f"; sigma = {SIGMA_WIRE_S_PER_M:.3e} S/m, delta = {delta:.4e} m "
            f"({delta / MINOR_RADIUS:.3f} r_wire)",
            flush=True,
        )
        print(
            f"[{label}] gap_burial = {GAP_BURIAL:.3e} m, gap_overhang = "
            f"{GAP_OVERHANG:.3e} m => fringe fraction "
            f"{_fringe_fraction(GAP_OVERHANG):.4f} (was {_fringe_fraction(1.0e-3):.4f} "
            f"at 3b-ii's 1 mm; floor {1.0 - np.pi / 4.0:.4f})",
            flush=True,
        )
        print(
            f"[{label}] gap boxes {gap_volumes[0]:.9e}, {gap_volumes[1]:.9e} m^3 "
            f"(analytic {8.0 * half_xz**2 * half_y:.9e}, ratio "
            f"{gap_volumes[0] / (8.0 * half_xz**2 * half_y):.12f}); "
            f"(A = {gap_areas[0]:.6e} m^2, L = {gap_length:.6e} m); arc lengths "
            f"{arc_lengths[0]:.6e}, {arc_lengths[1]:.6e} m "
            f"(analytic {MAJOR_RADIUS * (2 * np.pi - GAP_ANGLE):.6e} m)",
            flush=True,
        )
        print(
            f"[{label}] port discs: A_201 = {disc_areas[0]:.9e}, A_202 = "
            f"{disc_areas[1]:.9e} m^2 (exact oblique cut pair "
            f"{PORT_DISC_AREA_EXACT_M2:.9e}, meshed/exact "
            f"{disc_areas[0] / PORT_DISC_AREA_EXACT_M2:.9f}, "
            f"{disc_areas[1] / PORT_DISC_AREA_EXACT_M2:.9f}); per-disc split "
            f"201 = {disc_areas_split[0][0]:.6e} / {disc_areas_split[0][1]:.6e}, "
            f"202 = {disc_areas_split[1][0]:.6e} / {disc_areas_split[1][1]:.6e} m^2",
            flush=True,
        )
        print(
            f"[{label}] Z = [[{z_matrix[0,0]:+.6e}, {z_matrix[0,1]:+.6e}],\n"
            f"          [{z_matrix[1,0]:+.6e}, {z_matrix[1,1]:+.6e}]] Ohm",
            flush=True,
        )
    return {
        "z": z_matrix,
        "air_padding": air_padding,
        "cells": ncells,
        "mesh_time": t_mesh,
        "solve_times": solve_times,
        "currents": currents,
        "gap_length": gap_length,
        "gap_areas": gap_areas,
        "gap_volumes": gap_volumes,
        "gap_volume_analytic": 8.0 * half_xz**2 * half_y,
        "arc_lengths": arc_lengths,
        "disc_areas": disc_areas,
        "disc_areas_split": disc_areas_split,
        "terminal_angles": terminal_angles,
        "terminal_angles_mean": terminal_angles_mean,
        "terminal_angle_expected": phi_term_expected,
        "path_node_materials": path_node_materials,
        "closure_node_materials": closure_node_materials,
        "sigma_sweep": sigma_sweep,
        "control": control,
        "control_sigma_ladder": control_sigma_ladder,
        "production_sigma_ladder": production_sigma_ladder,
        "omega_m": omega_m_ref,
    }


@pytest.fixture(scope="module")
def gap_ports():
    """One mesh, two solves.  Module-scoped so every assertion shares them; the
    reciprocity claim *requires* one mesh, or it would test mesh noise."""
    return _solve_gap_ports(MPI.COMM_WORLD, "PORT-1 step 3b-vi")


@complex_only
def test_sigma_respects_the_skin_depth_constraint():
    """``δ = √(2/(ωμ₀σ)) ≥ r_wire`` — the precondition, asserted not assumed.

    The mesh cannot resolve a current path thinner than the tube, so σ is a
    constraint fixed by f and r_wire rather than a free parameter.  This costs
    no solve and fails loudly if either constant is edited without recomputing
    the other.
    """
    delta = np.sqrt(2.0 / (OMEGA * MU_0 * SIGMA_WIRE_S_PER_M))
    sigma_max = 2.0 / (OMEGA * MU_0 * MINOR_RADIUS**2)
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 3b-vi] delta = {delta:.6e} m vs r_wire = "
            f"{MINOR_RADIUS:.6e} m; sigma = {SIGMA_WIRE_S_PER_M:.6e} <= "
            f"sigma_max = {sigma_max:.6e} S/m",
            flush=True,
        )
    assert delta >= MINOR_RADIUS, (
        f"skin depth {delta:.6e} m is thinner than r_wire {MINOR_RADIUS:.6e} m: "
        f"sigma must not exceed {sigma_max:.6e} S/m at f = {FREQUENCY_HZ:.3e} Hz"
    )


@complex_only
def test_gap_box_meshes_exactly_at_the_reduced_overhang(gap_ports):
    """Step 3b-i's exact-box identity, re-asserted on the *new* box.

    A rectangular gap region is planar-faced, so gmsh meshes it to roundoff
    whatever its aspect ratio — the identity holds for any ``(burial,
    overhang)`` pair and is what licenses reading ``A = V_gap / L`` off the
    meshed volume rather than off analytic geometry.  Shrinking the overhang
    5× makes the box a slab of aspect ratio ~1:10, which is exactly the regime
    where a fragment failure would show up as lost volume, so this is a live
    check on the mesh half of the step and not a re-run of 3b-i.  The two ports
    must also agree to ``1e-9`` — same construction, mirrored in ``z``.
    """
    v_analytic = gap_ports["gap_volume_analytic"]
    v_meshed = gap_ports["gap_volumes"]
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 3b-vi] gap boxes meshed/analytic = "
            f"{v_meshed[0] / v_analytic:.12f}, {v_meshed[1] / v_analytic:.12f} "
            f"(analytic {v_analytic:.9e} m^3 at overhang "
            f"{GAP_OVERHANG:.3e} m)",
            flush=True,
        )
    for k, v in enumerate(v_meshed):
        assert abs(v / v_analytic - 1.0) < 1e-9, (
            f"gap box {k + 1} meshed at {v:.9e} m^3 against the analytic "
            f"{v_analytic:.9e} m^3 — the fragment lost part of the box, so "
            "A = V/L is not the cross-section V is averaged over"
        )
    assert abs(v_meshed[0] / v_meshed[1] - 1.0) < 1e-9


@complex_only
def test_port_discs_are_the_arc_end_cut(gap_ports):
    """The terminals ``V`` is read off are the surfaces 3b-iv gated.

    The disc pair is measured *through the solve's own restriction machinery*
    — ``chi_gap('+') + chi_gap('-')`` under the port ``dS``, i.e. the same
    expression that later carries ``E·ŷ`` — so a restriction that silently
    picked the wrong side, or a rank that never entered the facet assembly,
    fails here as an area rather than downstream as a voltage.  The band and the
    exact oblique cut are 3b-iv's, measured at overhang 1e-3; the cut depends on
    ``GAP_BURIAL`` and the torus radii only, so it carries over to this file's
    2e-4 geometry unchanged.  The two ports are the same construction mirrored
    in ``z`` and must agree to ``1e-9``; the two discs of a port are the same
    cut mirrored in ``y`` and must too — an asymmetry there is the sign-error
    class the estimator is most exposed to.

    The ``meshed/exact`` ratio itself is **printed and not asserted** here.
    3b-iv's band ``DISC_AREA_BAND`` was measured at ``gap_overhang = 1e-3``,
    where the tube clears the gap box's ``−x`` face by 0.598 mm and tags
    ``201``/``202`` are the disc pair alone.  At this file's 2e-4 the tube
    protrudes 0.2018 mm *through* that face, so the tags additionally carry two
    lateral strips and the area lands 1.0241 × above the exact cut — above a
    band an inscribed linear-tet section must sit below.  That is known-issues
    11, a property of the fixture and not of this estimator, and the step-3b-vi
    plan is explicit that nothing may be gated on the 2xx areas at this
    overhang.  The path integral uses no facet tags, so it is unaffected either
    way; what survives as a gate here are the two mirror symmetries, which hold
    strips or no strips.
    """
    areas = gap_ports["disc_areas"]
    split = gap_ports["disc_areas_split"]
    lo, hi = DISC_AREA_BAND
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 3b-vi] disc pair areas {areas[0]:.9e}, "
            f"{areas[1]:.9e} m^2; meshed/exact "
            f"{areas[0] / PORT_DISC_AREA_EXACT_M2:.9f}, "
            f"{areas[1] / PORT_DISC_AREA_EXACT_M2:.9f} (ungated at overhang "
            f"{GAP_OVERHANG:.1e} — known-issues 11; 3b-iv's band {lo}-{hi} was "
            f"measured at 1e-3); port ratio {areas[0] / areas[1]:.12f}",
            flush=True,
        )
    assert abs(areas[0] / areas[1] - 1.0) < 1e-9
    for k, (a_pos, a_neg) in enumerate(split):
        # The *port* ratio above is 1e-9 because the two ports are the same
        # mesh mirrored in z and gmsh reproduces that structurally.  The
        # per-disc y-split is not: it is two independent sums of ~1e5-cell
        # facet areas, and 3b-vi measured the residual at 1.1e-8 on the
        # unrefined mesh (20260806T093808Z log) — a *floating-point* floor, not
        # a geometry defect, so the bound is set from that measurement with a
        # decade of headroom rather than assumed.  A misassigned split is
        # O(1), four orders above anything this can hide.
        assert abs(a_pos / a_neg - 1.0) < 1e-7, (
            f"port {k + 1}: the y>0 disc is {a_pos:.9e} m^2 and the y<0 disc "
            f"{a_neg:.9e} m^2 — the cut is mirror-symmetric in y, so they cannot "
            "differ; the per-disc split is misassigned"
        )


@complex_only
def test_arc_quadrature_nodes_lie_strictly_inside_the_gap(gap_ports):
    """Every path node located, and located in a **gap** cell.

    The estimator's one geometric precondition: ``−∫E·t̂ dl`` between the
    terminals is only that integral if the path stays inside the gap for its
    whole length.  A node in a conductor cell would mean the arc left the gap
    box before reaching the terminal; a node in an air cell would mean the gap
    region is not what the tags say; an unlocated node would mean the path left
    the mesh.  Measured through the same locate path the field sampling uses
    (:func:`evaluate_vector_field_parallel` on a DG0 material indicator), not by
    arithmetic on the nominal geometry, so it also catches a mesh whose gap
    volume is fine but whose tagging is not.
    """
    records = gap_ports["path_node_materials"]
    for (port_index, order), rec in sorted(records.items()):
        n_gap = int(np.round(rec["gap"].sum()))
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 3b-vi] port {port_index + 1} order {order}: "
                f"{int(rec['valid'].sum())}/{order} located, {n_gap} gap, "
                f"{int(np.round(rec['wire'].sum()))} wire, "
                f"{int(np.round(rec['air'].sum()))} air",
                flush=True,
            )
        assert bool(np.all(rec["valid"])), (
            f"port {port_index + 1}, order {order}: "
            f"{int((~rec['valid']).sum())} arc quadrature nodes located in no "
            "cell — the centreline path left the mesh"
        )
        assert n_gap == order, (
            f"port {port_index + 1}, order {order}: only {n_gap} of {order} arc "
            "quadrature nodes are in a gap-tagged cell — the path does not stay "
            "inside the gap between the terminals, so it is not −∫E·dl across "
            "the port"
        )


@complex_only
def test_path_voltage_is_converged_in_the_quadrature(gap_ports):
    """The two Gauss orders agree to ``PATH_QUADRATURE_TOLERANCE``.

    The plan's precondition, and it is a precondition rather than a result: a
    path integral that still moves with the node count is measuring the
    quadrature, not the field, and comparing it to ``ωM₁₂`` would be
    meaningless.  Both resolutions come off the *same* solved field — the extra
    cost is point evaluation, seconds against the solve's tens of seconds — so
    this separates quadrature error from every other error in the estimator at
    essentially no compute.

    **Step 3b-x gates the undriven port and prints the driven one**, on the same
    standing disposition that keeps ``Z₁₁`` printed and never gated (§7: "``Z₁₁``
    stays printed, never gated"): with terminal-to-terminal limits the *driven*
    port's path runs through the impressed source's own terminals, and its
    integral does not converge in the quadrature at all — 2.6e-1, 1.7e-1,
    1.6e-1, 5.4e-2, 3.2e-2, 2.3e-2 at 129 → 4097, with ``Im V`` swinging
    5.56–8.63 V (`20260807T093906Z_PORT-1-step3bx-gate-n2.log`).  That is a
    property of ``Z₁₁``, which no gate in this file reads; the mutual is built
    from the undriven port, where the same sweep converges to 3.9e-4.  The
    tolerance is unchanged.
    """
    for tag, record in sorted(gap_ports["currents"].items()):
        by_order = record["path_voltages_by_order"]
        coarse_order, fine_order = PATH_QUADRATURE_GATE_ORDERS
        driven_index = GAP_TAGS.index(tag)
        for port_index in range(2):
            coarse = by_order[coarse_order][port_index]
            fine = by_order[fine_order][port_index]
            residual = abs(fine - coarse) / abs(fine)
            gated = port_index != driven_index
            role = "gated" if gated else "printed, the driven diagonal"
            if MPI.COMM_WORLD.rank == 0:
                print(
                    f"[PORT-1 step 3b-x] gap {tag} driven, port "
                    f"{port_index + 1} ({role}): V({fine_order}) = {fine:+.6e} V, "
                    f"V({coarse_order}) = {coarse:+.6e} V, relative difference "
                    f"{residual:.4e} (tolerance "
                    f"{PATH_QUADRATURE_TOLERANCE:.1e})",
                    flush=True,
                )
            if not gated:
                continue
            assert residual < PATH_QUADRATURE_TOLERANCE, (
                f"gap {tag} driven, port {port_index + 1}: the path voltage "
                f"moves by {residual:.4e} between {coarse_order} and "
                f"{fine_order} quadrature nodes — not converged, so it measures "
                "the quadrature rather than the field"
            )


@complex_only
def test_terminal_angles_match_the_meshed_gap_extent(gap_ports):
    """``arcsin(⟨y⟩_facet/a) = ±arcsin(half_y/a)`` to ``1e-6`` rad.

    Step 3b-x's precondition, and the reason this step exists: the estimator's
    integration limits are the terminals, and the terminals are where the mesh
    puts them, not where the nominal ``gap_angle`` wedge would.  ``y`` is
    constant on each facet half (the gap box's face is a plane), so the
    expected value is exact and the bound is a geometry bound rather than a
    discretisation one.  The fixture raises on a mismatch *before* any solve —
    this test asserts the recorded numbers so the gate is visible in the report
    rather than only as a collection error.

    The negative control is the whole of 3b-vi through 3b-ix: with the wedge
    limits (``±0.15`` rad against ``±0.175335``) the estimator returned
    0.4937 × ωM₁₂, and the 0.8% of arc between the two angles carried 45% of
    the loop's EMF.  The area-weighted mean over the same tags — known-issues
    11's lateral strips, printed beside this and not gated — is the second
    control: it lands ~1.5e-3 rad short, which is why the gated quantity is the
    interface's extreme reach and not its average.
    """
    expected = gap_ports["terminal_angle_expected"]
    for k, pair in enumerate(gap_ports["terminal_angles"]):
        for s, (measured, target) in enumerate(zip(pair, (expected, -expected))):
            deviation = measured - target
            if MPI.COMM_WORLD.rank == 0:
                print(
                    f"[PORT-1 step 3b-x] port {k + 1} facet tag "
                    f"{PORT_FACET_TAGS[k]}, {'y>0' if s == 0 else 'y<0'}: "
                    f"phi_terminal = {measured:+.9f} rad vs "
                    f"{target:+.9f} (deviation {deviation:+.3e}, tolerance "
                    f"{TERMINAL_ANGLE_TOLERANCE:.1e}; nominal wedge limit "
                    f"{(0.5 * GAP_ANGLE) * (1 if s == 0 else -1):+.9f})",
                    flush=True,
                )
            assert abs(deviation) < TERMINAL_ANGLE_TOLERANCE, (
                f"port {k + 1} {'y>0' if s == 0 else 'y<0'} terminal sits at "
                f"{measured:+.9f} rad, not {target:+.9f} — the estimator's "
                "limits and the meshed geometry disagree"
            )


@complex_only
def test_terminal_to_terminal_voltage_retiles_the_closure_decomposition(gap_ports):
    """``V_terminal = V_buried₋ + V_wedge + V_buried₊`` to ``1e-3`` relative.

    The identity that certifies step 3b-x's change is a change of *limits* and
    nothing else: one Gauss rule over ``(−φ_term, +φ_term)`` against 3b-ix's
    three-piece tiling of the same interval, off the same solved field, at the
    orders each piece already used.  Nothing physical can distinguish them, so
    a failure here says the new limits read the wrong tags — not that the
    estimator is wrong.

    Both sides are integrated at matched, converged orders
    (``PATH_QUADRATURE_GATE_ORDERS[-1]`` for the estimator and the wedge,
    ``RETILING_BURIED_ORDER`` for each buried segment); the closure
    decomposition's own coarser orders stay where 3b-ix set them, and its
    numbers are printed unchanged beside these.  As with the convergence
    precondition above, the **driven** port is printed and the undriven one
    gated: the driven path crosses the impressed source's terminals and does not
    converge in the quadrature (2.3e-2 at 4097), so a retiling residual there
    measures that, not the tiling.

    On record from 3b-ix (undriven port, gap 101 / gap 102 driven): wedge
    0.493653 / 0.491744, buried pair 0.399972 / 0.402239, tiling sum
    0.893625 / 0.893983 × ωM₁₂.
    """
    omega_m = gap_ports["omega_m"]
    for tag, record in sorted(gap_ports["currents"].items()):
        i_driven = record["driven"]
        driven_index = GAP_TAGS.index(tag)
        for port_index in range(2):
            corrected = record["path_voltages_by_order"][
                PATH_QUADRATURE_GATE_ORDERS[-1]
            ][port_index]
            tiled = record["retiling"][port_index]
            per_segment = record["closure"][port_index]
            recorded = (
                per_segment["gap"][GAP_SEGMENT_ORDERS[-1]]
                + per_segment["buried_neg"][BURIED_ARC_ORDERS[-1]]
                + per_segment["buried_pos"][BURIED_ARC_ORDERS[-1]]
            )
            residual = abs(corrected - tiled) / abs(tiled)
            gated = port_index != driven_index
            role = "gated" if gated else "printed, the driven diagonal"
            if MPI.COMM_WORLD.rank == 0:
                print(
                    f"[PORT-1 step 3b-x] gap {tag} driven, port "
                    f"{port_index + 1} ({role}): V_terminal = {corrected:+.9e} V "
                    f"({abs((corrected / i_driven).imag) / omega_m:.6f} x "
                    f"omega*M), wedge + buried = {tiled:+.9e} V "
                    f"({abs((tiled / i_driven).imag) / omega_m:.6f} x omega*M), "
                    f"relative difference {residual:.4e} (tolerance "
                    f"{RETILING_TOLERANCE:.1e}); 3b-ix's own orders give "
                    f"{abs((recorded / i_driven).imag) / omega_m:.6f} x omega*M",
                    flush=True,
                )
            if not gated:
                continue
            assert residual < RETILING_TOLERANCE, (
                f"gap {tag} driven, port {port_index + 1}: the "
                f"terminal-to-terminal integral differs from the wedge + "
                f"buried tiling of the same interval by {residual:.4e} — the "
                "new limits do not cover the same arc the decomposition does"
            )


# `OPS-17` step 2 (2026-08-17): the step-3b-x record, pinned. The test below
# was print-only — it carried the factor-244 finding in its docstring and its
# output, and asserted nothing, so nothing stopped the numbers the narrative is
# built on from drifting. These are the measured values at `-n 2` from
# `20260813T003532Z_PORT-1-step3bxvii-repoint-n2.log`, per gap tag:
#
#   gap 101: Im Z_gap = +1.110803269e+00 Ohm, Im Z_reaction = +4.537587930e-03
#            Ohm, ratio 244.800
#   gap 102: Im Z_gap = +1.110155911e+00 Ohm, Im Z_reaction = +4.537466163e-03
#            Ohm, ratio 244.664
#
# The band is a *regression* band, not an accuracy claim: these are records of
# what this fixture reads, and the test's finding (the reaction route over an
# open conducting loop measures the wire term, not the mutual) is a statement
# about which of them is which. 1% admits the run-to-run and partition variation
# the rest of this module already tolerates while catching any change that moves
# the finding. Nothing here gates the physics —
# REACTION_CONSISTENCY_TOLERANCE remains unmoved and unapplied.
REACTION_RECORD_RTOL = 0.01
REACTION_RECORDS = {
    101: {"im_z_gap_ohm": 1.110803269e00, "im_z_reaction_ohm": 4.537587930e-03},
    102: {"im_z_gap_ohm": 1.110155911e00, "im_z_reaction_ohm": 4.537466163e-03},
}


@complex_only
def test_reaction_route_on_the_gapped_fixture_reproduces_its_record(gap_ports):
    """``−∫E·J_test/(I₁I_test)`` over the undriven conductor — **a pinned record
    of step 3b-x's anchor (2), not a gate on the physics.**

    The plan's second anchor was to gate the corrected gap voltage against the
    landed step-1/2 reaction route evaluated on *this* fixture and *this* solved
    field.  Executed literally, that anchor is measured here at
    ``Im Z_reaction = 4.5376e-3 Ω`` against the estimator's ``1.1072 Ω`` — a
    factor 244 (`20260807T093906Z_PORT-1-step3bx-gate-n2.log`) — and the reason
    is structural, not a defect in either route:

    * the landed reaction route drives an **impressed** azimuthal current in a
      **non-conducting closed** torus, so ``E`` over the test region is the full
      induced field and ``−∫E·J₂`` is the mutual EMF;
    * here the test region is a **σ = 800 S/m arc of an open loop**.  The
      undriven loop is open (gated at 1e-2), so the field inside its conductor
      is the ohmic ``E = J/σ`` — the induced EMF stands across the gap, not
      along the wire.  ``4.5376e-3/ωM₁₂ = 0.003654`` is precisely the
      ``V_wire/ωM₁₂ = 0.002394`` term 3b-ix decomposed, to within the
      difference between an ``E·φ̂``-weighted and an arc-length-weighted
      average of the same small field.

    So the reaction integral over a *gapped* conductor measures the wire term of
    the loop-closure decomposition, not the mutual.  A same-fixture reaction
    reference needs its own impressed-current control solve with the conductors
    made non-conducting (σ = 0 on the wire tags, ``project_source`` per step
    2f's treatment of a source that terminates on the arc ends) — a solve this
    step did not buy and a question this step does not settle.  Reported here so
    the next attempt starts from the measurement rather than from the plan's
    premise.  ``REACTION_CONSISTENCY_TOLERANCE`` is unmoved and ungated: nothing
    was loosened, the anchor is simply not yet computable on this fixture.

    `OPS-17` step 2 (2026-08-17) pinned both measured numbers as a regression
    bound — see ``REACTION_RECORDS`` above for the values and why the band is a
    record band rather than an accuracy claim.
    """
    omega_m = gap_ports["omega_m"]
    for tag, record in sorted(gap_ports["currents"].items()):
        col = GAP_TAGS.index(tag)
        z_gap = record["voltages"][1 - col] / record["driven"]
        z_reaction = record["z_reaction"]
        per_segment = record["closure"][1 - col]
        v_wire = per_segment["wire"][WIRE_ARC_ORDERS[-1]]
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 3b-x] gap {tag} driven: Im Z_gap = "
                f"{z_gap.imag:+.9e} Ohm ({abs(z_gap.imag) / omega_m:.6f} x "
                f"omega*M), reaction over the gapped conductor = "
                f"{z_reaction.imag:+.9e} Ohm "
                f"({abs(z_reaction.imag) / omega_m:.6f} x omega*M), ratio "
                f"{abs(z_gap.imag) / abs(z_reaction.imag):.3f}; 3b-ix's V_wire "
                f"term = {abs((v_wire / record['driven']).imag) / omega_m:.6f} "
                f"x omega*M — the reaction route over an open, conducting loop "
                f"reads the wire term, not the mutual (ungated; "
                f"REACTION_CONSISTENCY_TOLERANCE = "
                f"{REACTION_CONSISTENCY_TOLERANCE:.0%}, unmoved)",
                flush=True,
            )

        expected = REACTION_RECORDS[tag]
        for name, measured, want in (
            ("Im Z_gap", z_gap.imag, expected["im_z_gap_ohm"]),
            ("Im Z_reaction", z_reaction.imag, expected["im_z_reaction_ohm"]),
        ):
            rel = abs(measured / want - 1.0)
            assert rel < REACTION_RECORD_RTOL, (
                f"gap {tag}: {name} = {measured:+.9e} Ohm against the step-3b-x "
                f"record {want:+.9e} Ohm (relative {rel:.4e}, band "
                f"{REACTION_RECORD_RTOL:.0%}); the factor-244 finding this test "
                "documents is built on these two numbers"
            )

        # The finding itself: the reaction route reads a quantity ~244x smaller
        # than the terminal estimator, which is what identifies it as the wire
        # term of the loop-closure decomposition rather than the mutual.
        ratio = abs(z_gap.imag) / abs(z_reaction.imag)
        want_ratio = abs(expected["im_z_gap_ohm"] / expected["im_z_reaction_ohm"])
        assert abs(ratio / want_ratio - 1.0) < REACTION_RECORD_RTOL, (
            f"gap {tag}: Im Z_gap / Im Z_reaction = {ratio:.3f} against the "
            f"record {want_ratio:.3f}"
        )


@complex_only
def test_gap_voltage_mutual_matches_the_same_fixture_reaction_control(gap_ports):
    """Step 3b-x's anchor (2), **re-pointed to matched topology** (decision (3)).

    History, because the re-pointing is the whole content of this test.  Until
    2026-08-12 this gate compared the gapped terminal-to-terminal estimator
    against ``Im Z₂₁`` from the σ = 0 **closed** impressed-current control on the
    same mesh, and read ``−3.0224e-02`` against a 3% bound — a red whose premise
    the lineage then disproved.  Six diagnostic steps excluded every other owner
    of that offset (3b-xi/3b-xii the PEC box, 3b-x the wedge limits, 3b-xiii the
    closed-lossy route as degenerate, 3b-xiv loss by sensitivity), and 3b-xvi
    excluded the last one — feed discretisation — by measurement: 1.57× local
    refinement of the gap region moves the estimator by ``+0.0508 pp``
    (0.894543 → 0.895051) against a 0.5 pp band, so the reading is converged at
    the feed (`20260812T170317Z_PORT-1-step3bxvi-solve6e4.log`, mesh arm
    `20260812T170128Z_PORT-1-step3bxvi-mesh6e4-repointed.log`).

    The offset is therefore **gap physics, not an estimator defect** — the
    documented artifact class of a gap-generator feed (Jin, *The FEM in
    Electromagnetics* 3rd ed., §10.4.2.1: the gap generator specifies the field
    across a gap a priori and is the least accurate of the feed models for
    impedance, with a gap-geometry-dependent error).  A closed loop and a gapped
    loop are different fixtures, so gating one against the other gates the
    topology change.  Per the 2026-08-12 adjudication decision (3) the
    comparison is re-aimed at **matched topology**: both sides below are read off
    the *gapped* solve, at σ = 800 S/m, on one mesh.  Neither
    ``REACTION_CONSISTENCY_TOLERANCE`` (0.03) nor ``MUTUAL_TOLERANCE`` (0.10)
    moved to make this green — the matched comparison passes with ~11× margin,
    which is the point.

    **What is gated.**  Faraday closure on the gapped loop: the
    terminal-to-terminal voltage ``V_terminal`` must account for the whole
    loop's EMF up to the conductor's own ohmic drop.  Around the gapped loop the
    closed contour splits as ``V_loop = V_terminal + V_wire``, where ``V_wire``
    is 3b-ix's ``∫E·φ̂`` along the σ = 800 S/m wire arc between the terminals; a
    terminal reading that is a good port voltage must satisfy
    ``|V_terminal|/|V_loop| = 1`` to within that ohmic term.  On record from
    3b-ix the wire term is ``0.002394 × ωM₁₂`` against a terminal reading of
    ``0.894543``, so the deviation is ~2.7e-3 — inside 3% by 11×.  Nothing else
    in this file gates the wire term's magnitude: the retiling gate
    (:func:`test_terminal_to_terminal_voltage_retiles_the_closure_decomposition`,
    1e-3) checks that the terminal limits tile the *gap* arc and is blind to the
    wire, and the reciprocity gate (1e-2) compares the two drives with each
    other, not the estimator with the loop.

    **Negative control on record:** the wedge-only estimator, 0.4937 × ωM₁₂,
    misses this same closure by ~45% — 15× the bound (3b-vi/3b-vii; the
    buried-arc correction of 3b-x is exactly what removed it).

    **Record kept, ungated, with its owner named:** the gapped-vs-closed
    deviation this gate used to assert, ``−3.0224e-02`` at the production mesh
    and ``−2.9674e-02`` under 1.57× feed refinement, is printed below against
    the closed control 0.922423 × ωM₁₂ and labeled **gap physics
    (Jin §10.4.2.1)**.  It is a measured property of the gapped fixture and
    travels with the port-pair gate as a stated systematic, alongside the PEC-box
    term (D∞ = +1.69 pp at p = 1.657, an effective-range extrapolation — never
    quoted without its exponent, §7 3b-xi).
    """
    omega_m = gap_ports["omega_m"]
    control = gap_ports["control"]
    z_closed = control["z21"].imag
    for tag, record in sorted(gap_ports["currents"].items()):
        col = GAP_TAGS.index(tag)
        port_index = 1 - col
        z_gap = record["voltages"][port_index] / record["driven"]
        # Matched topology: both terms off the gapped solve, same field, same
        # quadrature family.  V_loop closes the contour by adding the wire arc.
        v_terminal = record["path_voltages_by_order"][
            PATH_QUADRATURE_GATE_ORDERS[-1]
        ][port_index]
        v_wire = record["closure"][port_index]["wire"][WIRE_ARC_ORDERS[-1]]
        v_loop = v_terminal + v_wire
        z_loop = v_loop / record["driven"]
        ratio = abs(z_gap.imag) / abs(z_loop.imag)
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 3b-xvi] gap {tag} driven, MATCHED TOPOLOGY "
                f"(gapped solve both sides): Im Z_terminal = {z_gap.imag:+.9e} "
                f"Ohm ({abs(z_gap.imag) / omega_m:.6f} x omega*M) vs gapped "
                f"loop closure Im Z_loop = {z_loop.imag:+.9e} Ohm "
                f"({abs(z_loop.imag) / omega_m:.6f} x omega*M, wire term "
                f"{abs((v_wire / record['driven']).imag) / omega_m:.6f} x "
                f"omega*M): ratio {ratio:.6f}, deviation {ratio - 1.0:+.4e} "
                f"(tolerance {REACTION_CONSISTENCY_TOLERANCE:.0%}, unmoved); "
                f"wedge-only negative control 0.4937 x omega*M would give ratio "
                f"{0.493653 * omega_m / abs(z_loop.imag):.4f}",
                flush=True,
            )
            print(
                f"[PORT-1 step 3b-xvi] gap {tag} driven, RECORD (ungated): "
                f"against the sigma = 0 CLOSED control Im Z21 = {z_closed:+.9e} "
                f"Ohm ({abs(z_closed) / omega_m:.6f} x omega*M) the gapped "
                f"estimator deviates "
                f"{abs(z_gap.imag) / abs(z_closed) - 1.0:+.4e} (record "
                f"-3.0224e-02; refined -2.9674e-02 at 1.57x feed refinement) — "
                f"gap physics, Jin 3e sec. 10.4.2.1 gap-generator feed model; a "
                f"topology change, not an estimator defect, and not gated here",
                flush=True,
            )
        assert abs(ratio - 1.0) < REACTION_CONSISTENCY_TOLERANCE, (
            f"gap {tag} driven: the terminal-to-terminal gap voltage gives "
            f"Im Z = {z_gap.imag:+.6e} Ohm, the gapped loop's own closure "
            f"(terminal + wire arc, matched topology) gives "
            f"{z_loop.imag:+.6e} Ohm — ratio {ratio:.6f}, outside "
            f"{REACTION_CONSISTENCY_TOLERANCE:.0%}"
        )


@complex_only
def test_control_sigma_ladder_separates_loss_from_gap(gap_ports):
    """Step 3b-xiii: is the ~3% estimator-vs-control deviation loss, or the gap?

    The two routes compared by
    ``test_gap_voltage_mutual_matches_the_same_fixture_reaction_control``
    differ in two ways at once — the production loop is **gapped** and
    **σ = 800 S/m**, the control's is **closed** and **lossless**.  Three other
    candidate owners of the deviation are measured and excluded (wedge limits,
    3b-x; the ωM₁₂ reference, 3b-viii; the PEC box, 3b-xii, which moved both
    routes together).  This ladder moves σ *only*: the same control solve, the
    same mesh, the same impressed drive over the same closed footprints, with
    σ ∈ {200, 800} S/m through the DG0 material map.

    What is gated here is the ladder's **ordering**, which is what makes it a
    ladder rather than two unrelated numbers: the σ = 200 rung must lie between
    the σ = 0 and σ = 800 rungs.  That is a monotonicity identity in a single
    parameter, and it fails loudly if the σ = 800 point is noise or if σ enters
    somewhere it should not.  The band adjudication itself (does control(800)
    land on the estimator or on the σ = 0 control?) is **printed** — the
    thresholds are the review's, pre-decided in §7, and a disposition is a plan
    decision, not an assertion.
    """
    omega_m = gap_ports["omega_m"]
    ladder = gap_ports["control_sigma_ladder"]
    assert len(ladder) == len(CONTROL_SIGMA_LADDER)

    control_zero = abs(gap_ports["control"]["z21"].imag) / omega_m
    estimators = [
        abs(
            (
                record["voltages"][1 - GAP_TAGS.index(tag)] / record["driven"]
            ).imag
        )
        / omega_m
        for tag, record in sorted(gap_ports["currents"].items())
    ]
    estimator = float(np.mean(estimators))
    rungs = [abs(r["z21"].imag) / omega_m for r in ladder]

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-1 step 3b-xiii] ladder (x omega*M12): control(sigma=0) = "
            f"{control_zero:.6f}; "
            + "; ".join(
                f"control(sigma={r['sigma']:.3e}) = {v:.6f}"
                for r, v in zip(ladder, rungs)
            )
            + f"; estimator = {estimator:.6f} "
            f"({', '.join(f'{e:.6f}' for e in estimators)})",
            flush=True,
        )
        top = rungs[-1]
        d_estimator = abs(top - estimator)
        d_control = abs(top - control_zero)
        spread = abs(control_zero - estimator)
        if d_estimator <= 0.007:
            verdict = "LOSS owns the deviation (band: within 0.7 pp of the estimator)"
        elif d_control <= 0.007:
            verdict = "GAP owns it — loss exonerated (within 0.7 pp of control(0))"
        else:
            verdict = "MIXED — neither band; report the ladder and park"
        print(
            f"[PORT-1 step 3b-xiii] endpoints {spread * 100.0:+.3f} pp apart; "
            f"control(sigma=800) sits {d_estimator * 100.0:.3f} pp from the "
            f"estimator and {d_control * 100.0:.3f} pp from control(sigma=0) "
            f"=> {verdict}.  Negative control on record: the wedge-only "
            f"estimator at 0.5181/0.5352 x the control is 15x the 3% threshold.",
            flush=True,
        )

    lo, hi = sorted((control_zero, rungs[-1]))
    assert lo <= rungs[0] <= hi, (
        f"the sigma ladder is not monotone: control(sigma=0) = "
        f"{control_zero:.6f}, control(sigma={ladder[0]['sigma']:.3e}) = "
        f"{rungs[0]:.6f}, control(sigma={ladder[-1]['sigma']:.3e}) = "
        f"{rungs[-1]:.6f} (x omega*M12) — the intermediate rung must lie "
        f"between the endpoints or the ladder measures noise, not sigma"
    )


@complex_only
def test_production_sigma_ladder_removes_the_loss_from_the_gapped_route(gap_ports):
    """Step 3b-xiv: the reciprocal, non-degenerate half of 3b-xiii's sweep.

    3b-xiii lowered σ on the *closed* control and found the corner it was
    filling is physically degenerate — a closed lossy loop is a shorted turn,
    ``|I_cond/I′|`` reached 0.865, and the back-field of that circulating
    current, not the loss, is what moved the reaction integral.  σ and
    closed-vs-gapped are therefore confounded on that route.

    This is the other half: the **production gapped** fixture, nothing
    geometric moved, σ on the conductor lowered through {800, 200, 0}.  With
    the gap open there is no closed conducting path at any σ, so the loop
    carries only what the impressed source pushes through it in *series*.

    Two things are asserted, both identities rather than adjudications:

    1. **The σ = 800 rung reproduces the landed record.**  This rung re-solves
       exactly the production problem the module's own gates solve, so its
       estimator on the record's own ``I_cond`` normalisation must return the
       landed 0.894543 × ωM₁₂ to solver determinism.  It is the bridge that
       licenses reading the rest of the ladder on the impressed normalisation.
    2. **The ladder's ordering** — the σ = 200 rung lies between its
       neighbours, or the ladder measures noise rather than σ.

    The band adjudication (does ``est(σ = 0)`` land on the estimator endpoint
    0.8945 or the control endpoint 0.9224?) is **printed**.  Every disposition
    parks: the thresholds are §7's, and the branch's fate is the weekly
    review's, per 3b-xiii's escalation.

    On the negative control, and this is a finding about §9's wording rather
    than about the measurement: ``|I_cond/I′|`` on *this* route is a
    **series-continuity** number, not a shorted-turn number.  A value near 1 at
    σ = 800 means the impressed gap current returns through the wire as it must;
    it is the opposite of the closed control's 0.865, where the same magnitude
    meant a parallel short.  What the column does say here — and it is the
    reason the record's normalisation cannot be carried to the bottom rung — is
    that it collapses to exactly zero at σ = 0.
    """
    omega_m = gap_ports["omega_m"]
    ladder = gap_ports["production_sigma_ladder"]
    assert len(ladder) == len(PRODUCTION_SIGMA_LADDER) + 1
    by_sigma = {r["sigma"]: r for r in ladder}
    top = by_sigma[SIGMA_WIRE_S_PER_M]
    mid = by_sigma[PRODUCTION_SIGMA_LADDER[0]]
    bottom = by_sigma[0.0]

    # The two on-record endpoints this ladder is read between, both measured
    # afresh by this same fixture's other gates -- cited here, not recomputed.
    control_zero = abs(gap_ports["control"]["z21"].imag) / omega_m
    record = gap_ports["currents"][GAP_TAGS[PRODUCTION_LADDER_DRIVEN_COLUMN]]
    record_estimator = (
        abs(
            (
                record["voltages"][1 - PRODUCTION_LADDER_DRIVEN_COLUMN]
                / record["driven"]
            ).imag
        )
        / omega_m
    )

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-1 step 3b-xiv] gapped ladder on the impressed "
            f"normalisation (x omega*M12): "
            + "; ".join(
                f"sigma={r['sigma']:.3e} -> {r['estimator_impressed']:.6f} "
                f"(|I_cond/I'| = {r['conduction_ratio']:.6e})"
                for r in ladder
            ),
            flush=True,
        )
        print(
            f"[PORT-1 step 3b-xiv] bridge at sigma = 800: I_cond normalisation "
            f"gives {top['estimator_conduction']:.6f} x omega*M12 against this "
            f"fixture's own production estimator {record_estimator:.6f} "
            f"(relative difference "
            f"{abs(top['estimator_conduction'] / record_estimator - 1.0):.3e}); "
            f"impressed normalisation gives {top['estimator_impressed']:.6f}, "
            f"the two differing by exactly |I_cond/I'| = "
            f"{top['conduction_ratio']:.6f}",
            flush=True,
        )
        est_zero = bottom["estimator_impressed"]
        d_estimator = abs(est_zero - record_estimator)
        d_control = abs(est_zero - control_zero)
        spread = abs(control_zero - record_estimator)
        if d_control <= 0.007:
            verdict = (
                "LOSS owns the ~3% deviation (est(sigma=0) within 0.7 pp of "
                "the sigma=0 closed control)"
            )
        elif d_estimator <= 0.007:
            verdict = (
                "GAP/ESTIMATOR owns it (est(sigma=0) within 0.7 pp of the "
                "sigma=800 gapped estimator) — the escalation is real"
            )
        else:
            verdict = "MIXED — neither band; report all three rungs and park"
        print(
            f"[PORT-1 step 3b-xiv] endpoints {spread * 100.0:+.3f} pp apart "
            f"(estimator {record_estimator:.6f}, control(sigma=0) "
            f"{control_zero:.6f}); est(sigma=0) = {est_zero:.6f} sits "
            f"{d_estimator * 100.0:.3f} pp from the estimator and "
            f"{d_control * 100.0:.3f} pp from control(sigma=0) => {verdict}. "
            f"Negative control on record: the wedge-only estimator at "
            f"0.5181/0.5352 x the control is 15x the 3% threshold. All "
            f"dispositions park; nothing is re-pointed in-slot "
            f"(REACTION_CONSISTENCY_TOLERANCE stays "
            f"{REACTION_CONSISTENCY_TOLERANCE:.2f}, MUTUAL_TOLERANCE stays "
            f"{MUTUAL_TOLERANCE:.2f}).",
            flush=True,
        )

    # (1) The bridge.  Same problem, same mesh, same drive, same normalisation
    # as the landed production solve -- this must be the same number, and if it
    # is not, the ladder is not on the production route at all.
    assert top["estimator_conduction"] is not None, (
        "the sigma = 800 rung reconstructed a zero conduction current; the "
        "ladder is not solving the production problem"
    )
    assert abs(top["estimator_conduction"] / record_estimator - 1.0) < 1.0e-6, (
        f"the ladder's sigma = 800 rung gives "
        f"{top['estimator_conduction']:.9f} x omega*M12 on the record's own "
        f"normalisation, against this fixture's production estimator "
        f"{record_estimator:.9f} — the same problem solved twice must agree to "
        "solver determinism, so the ladder is not the production route"
    )
    # (2) The collapse.  Not a shorted-turn check on this route (see the
    # docstring): the content is that sigma = 0 leaves the loop with no
    # conduction current at all, which is why the record's normalisation is
    # undefined there and the ladder is read on the impressed one.
    assert bottom["conduction_ratio"] == 0.0, (
        f"|I_cond/I'| at sigma = 0 is {bottom['conduction_ratio']:.6e}, not "
        "identically zero: sigma reached the loop-current reconstruction from "
        "somewhere other than the material map"
    )
    assert bottom["estimator_conduction"] is None
    # (3) The ordering.
    lo, hi = sorted(
        (bottom["estimator_impressed"], top["estimator_impressed"])
    )
    assert lo <= mid["estimator_impressed"] <= hi, (
        f"the gapped sigma ladder is not monotone: sigma=0 -> "
        f"{bottom['estimator_impressed']:.6f}, sigma="
        f"{mid['sigma']:.3e} -> {mid['estimator_impressed']:.6f}, sigma="
        f"{top['sigma']:.3e} -> {top['estimator_impressed']:.6f} "
        "(x omega*M12) — the intermediate rung must lie between the endpoints "
        "or the ladder measures noise, not sigma"
    )


@complex_only
def test_gap_voltage_port_pair_mutual_carries_its_systematics(gap_ports):
    """Step 3b-xviii, **the port-pair gate**: ``Im Z₁₂`` against ``ωM₁₂``.

    The deferred 3b-i/3b-ii gate, pre-registered by the 2026-08-12 adjudication
    decision (3) and authored only once its two systematics had been measured
    rather than assumed.  ``Im Z₁₂ = V₂/I₁`` from the gap-voltage route on the
    landed gapped two-torus fixture (padding 0.08, 178 055 cells) is compared to
    the filamentary closed form ``ωM₁₂ = +1.241755 Ω`` (Jackson 5.37, via
    :func:`~tests.validation.test_port_reaction_impedance.mutual_inductance`) at
    ``MUTUAL_TOLERANCE`` = 10%, **unmoved**.

    **Why the comparison needs corrections, and why that is not band-shopping.**
    The closed form is a filament pair in free space; this fixture is a pair of
    finite-cross-section tori inside a PEC truncation box, each broken by a
    dielectric gap the source is impressed across.  Two of those differences are
    measured, and both were fixed on the record *before* this gate existed:

      * the **PEC box**, ``D∞ = +1.69 pp`` of ratio at ``p = 1.657`` — an
        effective-range extrapolation of decision-(4)'s free-exponent fit to
        three padding rungs, never quotable without its exponent (§7 3b-xi);
      * the **gap-physics offset**, ``−3.0224e-02`` against this fixture's own
        σ = 0 closed control (Jin 3e §10.4.2.1's gap-generator feed model;
        3b-xvi excluded feed discretisation as its owner, 3b-xvii gated the
        matched-topology closure that licenses the label).

    Both are named in the assertion message, and the ladder is printed raw
    first: the **raw** ratio 0.894283 is −10.57%, which this band would *not*
    accept, and saying so is the point of printing it.  The corrections are not
    free parameters — a knob fitted to this gate would have been chosen after
    seeing it; these were both published with their uncertainties in earlier
    steps, and the residual they leave (~−6%) is the finite cross-section, the
    remaining truncation, and the discretisation, not a tuned zero.

    **Negative control, executed:** :func:`_mutual_systematics_ladder` is run on
    step 1's unfragmented-mesh record — ``Z₁₂ ≡ 0`` exactly, the two loops
    meshed as disconnected islands — and must be **rejected** by the same band
    that accepts the measured number.  The blind fixture reads −100% even with
    both corrections applied; the separation between it and this fixture is
    total, and a band that could not tell them apart would gate nothing.

    Reciprocity is the standing tripwire and is gated next door
    (:func:`test_gap_voltage_z_matrix_is_reciprocal`, 5.83e-4 against an unmoved
    1e-2); the ``1e-9`` identity belongs to the *reaction* route, where the same
    bilinear form appears in both off-diagonals and symmetry is structural
    (`test_reaction_impedance_matrix_is_reciprocal`).  Here ``V`` and ``I`` are
    assembled on different subdomains with different integrands, so 5.83e-4 is
    what a real network identity costs on this route, not a loosened 1e-9.

    **Scope.**  This gate validates the two-torus ``∫E·dl`` machinery *with its
    systematics stated*.  It does not close `PORT-1`: the estimator is a
    stated-path convention (decision (5)) and claims no path-independence, and
    birdcage ports and B1+ stay held.
    """
    z = gap_ports["z"]
    m12 = mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    omega_m12 = OMEGA * m12
    z12 = 0.5 * (z[0, 1] + z[1, 0])
    ladder = _mutual_systematics_ladder(z12.imag, omega_m12)
    blind = _mutual_systematics_ladder(BLIND_FIXTURE_IM_Z12_OHM, omega_m12)
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 3b-xviii] M12 = {m12:.6e} H, omega*M12 = "
            f"{omega_m12:+.6e} Ohm; Im Z12 = {z[0,1].imag:+.6e}, Im Z21 = "
            f"{z[1,0].imag:+.6e}, mean |Im Z12| = {abs(z12.imag):.6e} Ohm at "
            f"fringe fraction {_fringe_fraction(GAP_OVERHANG):.4f} "
            f"(3b-ii: 1.721 at 0.4545; wedge-limited 3b-vii: 0.4937)",
            flush=True,
        )
        print(
            f"[PORT-1 step 3b-xviii] systematics ladder vs omega*M12: "
            f"raw {ladder['raw']:.6f} ({ladder['raw_deviation']:+.2%}) "
            f"-> +PEC box {PEC_BOX_SYSTEMATIC:+.4f} (D_inf at p = "
            f"{PEC_BOX_SYSTEMATIC_EXPONENT:.3f}, effective-range) "
            f"{ladder['box_corrected']:.6f} ({ladder['box_deviation']:+.2%}) "
            f"-> /(1 {GAP_PHYSICS_SYSTEMATIC:+.6f}) gap physics (Jin 3e sec. "
            f"10.4.2.1) {ladder['corrected']:.6f} "
            f"({ladder['deviation']:+.2%}) against MUTUAL_TOLERANCE = "
            f"{MUTUAL_TOLERANCE:.2f} (unmoved). The RAW number does not clear "
            f"this band; the two stated systematics are what it is compared "
            f"with, not a widened bound.",
            flush=True,
        )
        print(
            f"[PORT-1 step 3b-xviii] negative control (step 1 unfragmented "
            f"mesh, Im Z12 = {BLIND_FIXTURE_IM_Z12_OHM:+.1f} Ohm exactly): "
            f"same ladder gives corrected {blind['corrected']:.6f} "
            f"({blind['deviation']:+.2%}), passes = {blind['passes']} — the "
            f"blind fixture is rejected by the band that accepts the measured "
            f"number",
            flush=True,
        )
    assert not blind["passes"], (
        "negative control failed: the unfragmented-mesh record Im Z12 = 0 "
        f"is accepted at MUTUAL_TOLERANCE = {MUTUAL_TOLERANCE:.2f} "
        f"(corrected ratio {blind['corrected']:.6f}) — this band gates nothing"
    )
    assert ladder["passes"], (
        f"gap-voltage port pair: |Im Z12| = {abs(z12.imag):.6e} Ohm is "
        f"{ladder['raw']:.6f} x omega*M12 raw; carrying the two stated "
        f"systematics — PEC box D_inf = {PEC_BOX_SYSTEMATIC:+.4f} of ratio at "
        f"p = {PEC_BOX_SYSTEMATIC_EXPONENT:.3f} (effective-range "
        f"extrapolation, §7 3b-xi) and gap physics "
        f"{GAP_PHYSICS_SYSTEMATIC:+.6f} vs the closed control (Jin 3e sec. "
        f"10.4.2.1) — gives {ladder['corrected']:.6f} x omega*M12, deviation "
        f"{ladder['deviation']:+.4e}, outside MUTUAL_TOLERANCE = "
        f"{MUTUAL_TOLERANCE:.2f}"
    )


@complex_only
def test_gap_voltage_scattering_matrix_is_symmetric_and_passive(gap_ports):
    """Step 3b-xviii's network tripwire: ``S`` at ``Z₀ = 50 Ω``, this fixture.

    The step-2 machinery
    (:func:`~tests.validation.test_port_reaction_impedance.scattering_from_impedance`,
    ``S = (Z − Z₀I)(Z + Z₀I)⁻¹``) applied to the gap-voltage ``Z`` for the first
    time.  Two claims, and deliberately not step 2's third:

      * **symmetric**, to the same 1e-2 the route's own reciprocity residual is
        gated at — ``S``'s asymmetry is ``Z``'s asymmetry pushed through a
        smooth map, so 5.83e-4 in ``Z`` cannot become 1e-9 in ``S``.  Step 2's
        1e-9 lives on the reaction route where symmetry is algebraic.
      * **passive**, ``‖S‖₂ ≤ 1``.  This is the physical claim: the fixture
        contains a σ = 800 S/m conductor and no source but the impressed one, so
        a network that reflected more power than it accepted would mean the
        solved field is delivering energy from nowhere.

    Step 2's **unitarity** assertion is deliberately absent: that fixture was
    lossless air, this one dissipates (``Re Z₁₁ = +3.82 Ω``), so ``‖S‖₂ = 1``
    would be the wrong claim here.  ``1 − ‖S‖₂`` is printed as the loss margin.
    """
    from tests.validation.test_port_reaction_impedance import (
        REFERENCE_IMPEDANCE_OHM,
        scattering_from_impedance,
    )

    z = gap_ports["z"]
    s = scattering_from_impedance(z, REFERENCE_IMPEDANCE_OHM)
    asymmetry = np.linalg.norm(s - s.T) / np.linalg.norm(s)
    spectral_norm = float(np.linalg.norm(s, 2))
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 3b-xviii] S (Z0 = {REFERENCE_IMPEDANCE_OHM:.0f} "
            f"Ohm) from the gap-voltage Z: S11 = {s[0,0]:+.6e}, S21 = "
            f"{s[1,0]:+.6e}; ||S-S^T||/||S|| = {asymmetry:.4e} (band "
            f"{RECIPROCITY_TOLERANCE:.1e}, the route's own reciprocity "
            f"convention), ||S||_2 = {spectral_norm:.12f}, loss margin "
            f"1 - ||S||_2 = {1.0 - spectral_norm:+.6e} (lossy fixture: "
            f"unitarity is NOT claimed, unlike step 2's air pair)",
            flush=True,
        )
    assert asymmetry < RECIPROCITY_TOLERANCE, (
        f"S asymmetry {asymmetry:.4e} exceeds {RECIPROCITY_TOLERANCE:.1e} — "
        "the gap-voltage Z is not reciprocal enough for an S-matrix"
    )
    assert spectral_norm <= 1.0 + 1e-9, (
        f"||S||_2 = {spectral_norm:.12f} is not passive: the solved field "
        "would be delivering power the impressed source did not supply"
    )


@complex_only
def test_gap_voltage_z_matrix_is_reciprocal(gap_ports):
    """``|Z₁₂ − Z₂₁|/|Z₁₂|`` from two solves on one mesh.

    Unlike the reaction route — where the same bilinear form appears in both
    off-diagonals and symmetry is structural — here ``V`` and ``I`` are
    assembled on different tags with different integrands, so this is a real
    network identity rather than an algebraic tautology.  The two solves must
    share one mesh or the number measures mesh noise instead.
    """
    z = gap_ports["z"]
    residual = abs(z[0, 1] - z[1, 0]) / abs(z[0, 1])
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 3b-vi] reciprocity |Z12 - Z21|/|Z12| = "
            f"{residual:.4e}  (Z12 = {z[0,1]:+.6e}, Z21 = {z[1,0]:+.6e} Ohm)",
            flush=True,
        )
    assert residual < RECIPROCITY_TOLERANCE, (
        f"gap-voltage reciprocity residual {residual:.4e} exceeds "
        f"{RECIPROCITY_TOLERANCE:.1e}: Z12 = {z[0,1]:.6e}, Z21 = {z[1,0]:.6e} Ohm"
    )


@complex_only
def test_undriven_port_is_open_and_the_diagonal_is_reported(gap_ports):
    """The open-circuit precondition of the ``Im Z₁₂ = ωM₁₂`` anchor.

    ``Z₁₂ = V₂/I₁`` is the *mutual* only if port 2 draws no current.  Its gap is
    a series C of ε₀A/L ≈ 7e-14 F, i.e. |1/ωC| ≈ 2e5 Ω against the loop's ~7 Ω
    reactance, so the undriven loop current must be orders below the driven one.
    Asserted at 1e-2 — four orders looser than the estimate, so it states
    "open" without gating the capacitance model.

    ``Z₁₁`` is **printed, not gated**: it carries the gap's series C and the
    loop's ohmic R, neither of which has a closed form here.
    """
    for tag, record in gap_ports["currents"].items():
        ratio = abs(record["undriven"]) / abs(record["driven"])
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 3b-vi] gap {tag} driven: |I_undriven/I_driven| = "
                f"{ratio:.4e}",
                flush=True,
            )
        assert ratio < 1.0e-2, (
            f"gap {tag}: undriven loop carries {ratio:.4e} of the driven "
            "current — port 2 is not open, so V2/I1 is not the mutual"
        )
    z = gap_ports["z"]
    if MPI.COMM_WORLD.rank == 0:
        c_gap = EPSILON_0 * gap_ports["gap_areas"][0] / gap_ports["gap_length"]
        print(
            f"[PORT-1 step 3b-vi] diagonal (ungated): Z11 = {z[0,0]:+.6e}, "
            f"Z22 = {z[1,1]:+.6e} Ohm; gap C = {c_gap:.4e} F "
            f"(1/omega*C = {1.0 / (OMEGA * c_gap):.4e} Ohm)",
            flush=True,
        )


# ---------------------------------------------------------------------------
# Step 3b-ix.


@complex_only
def test_closure_arc_nodes_lie_in_the_expected_material(gap_ports):
    """Wire-arc nodes are wire-tagged; buried-segment nodes are gap-tagged.

    The inverse of ``test_arc_quadrature_nodes_lie_strictly_inside_the_gap``,
    and the precondition of the decomposition rather than of any one segment:
    if the wire arc's nodes were in the dielectric — or the buried segments'
    in the conductor — the four segments would not tile the loop and their sum
    would not be ``−∮E·t̂ dl``.  Measured through the same DG0 indicator and
    the same locate path as the field sampling, before any solve.
    """
    records = gap_ports["closure_node_materials"]
    for (port_index, name, order), rec in sorted(records.items()):
        expected = rec["expected"]
        n_expected = int(np.round(rec[expected].sum()))
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 3b-ix] port {port_index + 1} {name} order "
                f"{order}: {int(rec['valid'].sum())}/{order} located, "
                f"{int(np.round(rec['gap'].sum()))} gap, "
                f"{int(np.round(rec['wire'].sum()))} wire, "
                f"{int(np.round(rec['air'].sum()))} air (expected {expected})",
                flush=True,
            )
        assert bool(np.all(rec["valid"])), (
            f"port {port_index + 1}, {name}, order {order}: "
            f"{int((~rec['valid']).sum())} nodes located in no cell"
        )
        assert n_expected == order, (
            f"port {port_index + 1}, {name}, order {order}: only {n_expected} "
            f"of {order} nodes are in a {expected}-tagged cell, so the four "
            "closure segments do not tile the centreline loop"
        )


@complex_only
def test_wire_arc_quadrature_is_converged(gap_ports):
    """``|V_wire(1025) − V_wire(513)|/|V_wire(1025)| < 1e-2``.

    The plan's precondition for part (1), and the same argument as the gap
    arc's: an integral that still moves with the node count measures the
    quadrature, not the field.  The bound is an order looser than the wedge's
    because the integrand crosses ~20× more cells over a 20× longer arc and
    jumps at each crossing; it was fixed by the plan before the first number
    was measured.

    **Step 3b-x's split, decided by the plan review, not in the slot.** The
    bound does not move; what moves is which port it gates.  The *driven*
    port's wire arc converges at 5.7e-4 / 1.7e-4 (3b-ix, on record) and is
    gated.  The *undriven* port's reaches 2.01e-2 and is printed: it is a
    relative bound on a term worth 0.24% of that loop, so its absolute stake is
    5e-5 × ωM₁₂ — a hundredth of the closure band — and gating a relative
    tolerance on a quantity that small measures the smallness, not the field.
    Both numbers reach the log either way.
    """
    for tag, record in sorted(gap_ports["currents"].items()):
        driven_index = GAP_TAGS.index(tag)
        for port_index, per_segment in enumerate(record["closure"]):
            coarse_order, fine_order = WIRE_ARC_ORDERS
            coarse = per_segment["wire"][coarse_order]
            fine = per_segment["wire"][fine_order]
            residual = abs(fine - coarse) / abs(fine)
            gated = port_index == driven_index
            if MPI.COMM_WORLD.rank == 0:
                print(
                    f"[PORT-1 step 3b-x] gap {tag} driven, port "
                    f"{port_index + 1} ({'gated' if gated else 'printed'}): "
                    f"V_wire({fine_order}) = {fine:+.6e} V, "
                    f"V_wire({coarse_order}) = {coarse:+.6e} V, relative "
                    f"difference {residual:.4e} (tolerance "
                    f"{WIRE_ARC_TOLERANCE:.1e})",
                    flush=True,
                )
            if not gated:
                continue
            assert residual < WIRE_ARC_TOLERANCE, (
                f"gap {tag} driven, port {port_index + 1}: the wire-arc "
                f"voltage moves by {residual:.4e} between {coarse_order} and "
                f"{fine_order} nodes — not converged, so the decomposition "
                "measures the quadrature rather than the field"
            )


@complex_only
def test_loop_closure_sum_recovers_the_emf(gap_ports):
    """``|Im[(V_gap + V_buried + V_wire)/I₁]| / ωM₁₂ = 1 ± 0.15`` on the
    undriven loop.

    Faraday on the closed centreline circle, and the anchor of step 3b-ix.
    The undriven loop is open (gated separately at 1e-2), so the flux linking
    it is the mutual one and ``−∮E·t̂ dl`` must be ``ωM₁₂I₁`` — independently of
    what any single segment contributes.  The band is the reference's own
    (step 2's −9.35%, of which −9.36% is the PEC box; step 3b-viii's +0.481%
    finite-cross-section correction) plus discretisation.

    This is the measurement that separates the two readings of 3b-vi/3b-vii's
    0.4937: if the sum closes, the missing half is *in the wire* and the gap
    estimator is reporting a real terminal voltage rather than the EMF; if it
    does not, neither named suspect survives and the question is what a gap
    port should report at all.
    """
    omega_m = gap_ports["omega_m"]
    for tag, record in sorted(gap_ports["currents"].items()):
        col = GAP_TAGS.index(tag)
        port_index = 1 - col
        per_segment = record["closure"][port_index]
        i_driven = record["driven"]
        v_gap = per_segment["gap"][GAP_SEGMENT_ORDERS[-1]]
        v_wire = per_segment["wire"][WIRE_ARC_ORDERS[-1]]
        v_buried = (
            per_segment["buried_neg"][BURIED_ARC_ORDERS[-1]]
            + per_segment["buried_pos"][BURIED_ARC_ORDERS[-1]]
        )
        v_sum = _closure_sum(per_segment)

        def _ratio(v):
            return abs((v / i_driven).imag) / omega_m

        closure_ratio = _ratio(v_sum)
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 3b-ix] gap {tag} driven, undriven port "
                f"{port_index + 1}: V_gap = {_ratio(v_gap):.6f}, V_buried = "
                f"{_ratio(v_buried):.6f}, V_wire = {_ratio(v_wire):.6f}, "
                f"closure = {closure_ratio:.6f} x omega*M "
                f"(omega*M = {omega_m:.6e} Ohm, tolerance "
                f"{CLOSURE_TOLERANCE:.2f})",
                flush=True,
            )
        assert abs(closure_ratio - 1.0) < CLOSURE_TOLERANCE, (
            f"gap {tag} driven: the centreline loop integral closes at "
            f"{closure_ratio:.6f} x omega*M, not 1 +- {CLOSURE_TOLERANCE:.2f} "
            f"(V_gap {_ratio(v_gap):.6f}, V_buried {_ratio(v_buried):.6f}, "
            f"V_wire {_ratio(v_wire):.6f}) — the missing half of the gap "
            "voltage is not accounted for by the rest of the loop"
        )


@complex_only
def test_sigma_sweep_keeps_the_undriven_port_open(gap_ports):
    """The open-circuit premise still holds at ``σ×2`` and ``σ×4``.

    ``V_gap/ωM₁₂`` is only a mutual-impedance ratio while the undriven loop
    draws no current, and raising σ raises every conduction current in the
    problem — so the premise is re-measured at each scale rather than
    inherited from the σ×1 solve.  Same 1e-2 bound as
    ``test_undriven_port_is_open_and_the_diagonal_is_reported``.
    """
    for record in gap_ports["sigma_sweep"]:
        ratio = abs(record["undriven"]) / abs(record["driven"])
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 3b-ix] sigma x{record['scale']:g}: "
                f"|I_undriven/I_driven| = {ratio:.4e}",
                flush=True,
            )
        assert ratio < 1.0e-2, (
            f"sigma x{record['scale']:g}: undriven loop carries {ratio:.4e} of "
            "the driven current — V2/I1 is not the mutual at this scale"
        )
