"""`MAT-4` step 5 — the 1 g column on the `GEO-27` rung.

Step 4 closed the coil-driven mass-averaged SAR gate at ``phantom_resolution =
PHANTOM_RESOLUTION_FINE`` (7.5 mm phantom ``h``, 120 499 cells): the four cyclic
**10 g** C4 pairs read 0.3303 / 0.0756 / 0.0574 / 0.3132% against the imported,
unmoved 5% ``C4_COVARIANCE_BAND``, and the **1 g** column — a 6.204 mm ball on a
7.5 mm ``h``, i.e. 1.65 cells across the ball — was *printed* at 6.8383 / 2.9297
/ 0.4116 / 4.7159% with pre-registered verdict (b): outside the band, inside the
predicted pointwise class, "the route to a 1 g gate is ``h``"
(`20260907T003548Z_MAT-4-step4.log:1943–1947`).

This module walks exactly that route once.  `GEO-27` priced the next phantom
rung — ``phantom_resolution = 0.0025`` m gives **4.96 cells** across the 1 g ball
at 199 920 cells / 58 866 phantom cells, 36.27 s to mesh, one reading
(`20260908T033218Z_GEO-27.log`) — and this module runs **step 4's own
construction** on it: the same four single-drive solves, the same C95.3 operator
at the same imported ``QUADRATURE_DEGREE``, the same density map with the
phantom's ``0.0`` exclusion, the same ball radii from ``averaging_ball_radius``,
the same centres and the same C4 pairing.  Nothing is re-implemented here:
``_build_mass_averaged`` is imported from
``tests/validation/test_birdcage_sar_mass_averaged.py`` and called with
``phantom_resolution=PHANTOM_RESOLUTION_1G_RUNG``.  The one change to that module
is the keyword itself, whose default reproduces step 4 byte-for-byte (§9 rule
(c) disclosure; step 4's gate is re-run green in the same slot).

**Anchors, asserted — both imported and unmoved.**

* **(i) the 10 g C4 identity at the imported 5% band on this rung.**  The same
  assert step 4 runs at 0.0075 m.  An operator that is C4-covariant at ``h`` is
  C4-covariant at ``h/3``: a miss here is a finding about the *mesh* (the finer
  rung's partition, its phantom surface rendering), never a band to widen, and
  is a known-issues entry.
* **(ii) the whole-phantom ball identity** — a ball of radius
  ``WHOLE_PHANTOM_BALL_RADIUS_M`` returns the tag-3 ``½∫σ|E|²`` and
  ``ρ·V_phantom`` at the imported ``EXACT_IDENTITY_RTOL`` (1e-10), as step 4.
  This is the operator's cell-coverage anchor and it is a *different* statement
  on a different partition of a different mesh, which is why it is re-asserted
  rather than assumed.  Note that step 4's *third* anchor of this family — the
  power against ``STEP3F_FINE_PRIMAL_PHANTOM_POWER_W`` — is **not** re-asserted:
  that record belongs to the 0.0075 rung, and this rung has no such record.  The
  reading is printed beside it as the rung-to-rung move.
* containment, as step 4: ``r₀ + a₁₀g`` inside the phantom's CAD radius, and no
  ball through its flat face.  A ball straddling the phantom surface would
  average a discontinuous integrand.

**Step 5b (2026-09-08) — what the 2026-09-08 10:30 review ruled.**  Step 5 ran
this module and measured the 1 g column at **0.0957 / 0.1199 / 0.1305 / 0.1065%**
on two windows agreeing to the printed digit
(`20260908T140457Z_MAT-4-step5.log:1990–1993`,
`20260908T141147Z_MAT-4-step5-rerun.log:1990–1993`) — a factor 38 of headroom
against the same imported 5% band — and the mesh at **199 920 / 58 866** on three
windows (`20260908T033218Z_GEO-27.log:7155` and both of the above at
`:1981–1982`).  The review promoted both from printed records to gates:

* **(iii) the four cyclic 1 g C4 pairs** are now asserted against the *same*
  imported, unmoved ``C4_COVARIANCE_BAND``.  Nothing was widened to admit the 1 g
  column — ``h`` changed instead, exactly as step 4's verdict (b) predicted.
* **(iv) the rung's two cell counts** are version-tagged records
  (``ONE_GRAM_RUNG_CELL_RECORD`` / ``ONE_GRAM_RUNG_PHANTOM_CELL_RECORD``) asserted
  at the imported ``CELL_COUNT_BAND`` (1%), **never at equality** — an exact
  record goes stale on the next mesher (`OPS-27`).
* the mis-paired **1 g** control is *added* and stays printed: the ~85% on record
  is the 10 g column's, so rule (e) forbids asserting its size.  What is asserted
  about it is only that it is attributed to the right drive.

**Printed, predicted, never asserted (§9 rule (e) — no prior measurement of any
of these at this rung).**

1. the mis-paired **1 g** control ``SAR₁g(c_{k+2}; k)`` against ``SAR₁g(c_k; k)``,
   predicted **~85%** by analogy with the 10 g control's 85.25–85.29% on this
   rung — a different quantity, so predicted and gated by nothing.
2. the per-drive 10 g peaks against step 4's, and the per-drive 1 g averages at
   each drive's own centre (step 4's log printed the 1 g *pairs*, not the 1 g
   absolutes, so only the pairs have a recorded comparand) — the rung-to-rung
   move, predicted a few % on 10 g and larger on 1 g.

**Scope.**  One rung, 10 MHz, degree 1, four single drives.  `MAT-4`'s ✅ gains
"1 g **and** 10 g C4-gated on the 0.0025 rung" and nothing else: no band moved,
no ``src/`` change, no absolute SAR / C95.3 compliance / homogeneity / Larmor
claim, and two rungs of one quantity are **not** a convergence rate.

Run (complex build required)::

    scripts/testing/run_and_log.sh MAT-4-step5b "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 560 \\
       mpiexec -n 4 python3 -m pytest tests/environment \\
       tests/validation/test_birdcage_sar_1g_rung.py -v -s'"
"""

from __future__ import annotations

import pytest

from fem_em_solver.post.sar import mass_averaged_sar

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheet_prerequisite import CELL_COUNT_BAND
from tests.mesh.test_birdcage_port_tags import PHANTOM_HEIGHT, PHANTOM_RADIUS
from tests.validation.test_birdcage_b1_plus_map import C4_COVARIANCE_BAND
from tests.validation.test_birdcage_sar_mass_averaged import (
    CENTRE_RADIUS_M,
    EXACT_IDENTITY_RTOL,
    ONE_GRAM_PREDICTED_HIGH,
    PHANTOM_RHO_KG_PER_M3,
    WHOLE_PHANTOM_BALL_RADIUS_M,
    _build_mass_averaged,
)
from tests.validation.test_mass_averaged_sar_standard_masses import QUADRATURE_DEGREE

# The `GEO-27` rung (`20260908T033218Z_GEO-27.log`): the phantom edge length that
# puts 4.96 cells across the 1 g averaging ball, against 1.65 at step 4's
# 0.0075 m.  This is the *route to a 1 g gate* step 4's verdict (b) named.
PHANTOM_RESOLUTION_1G_RUNG = 0.0025

# The rung's mesh, REGISTERED as a version-tagged record by the 2026-09-08 10:30
# review (`MAT-4` step 5b, the (1*) licence): three independent windows on
# dolfinx 0.11.0.post0 / gmsh 4.15.2-git-657c8e9 read the same two integers —
# `20260908T033218Z_GEO-27.log:7155` (`GEO-27`'s first reading) and step 5's two
# windows `20260908T140457Z_MAT-4-step5.log:1981-1982` and
# `20260908T141147Z_MAT-4-step5-rerun.log:1981-1982`.  Asserted at the imported
# `CELL_COUNT_BAND` (1%), never at equality: an exact record goes stale on the
# next mesher version and fails for a reason that is not this fixture's
# (`OPS-27`'s stale-exact class; the `GEO-25` step-2 pattern).
ONE_GRAM_RUNG_CELL_RECORD = 199_920
ONE_GRAM_RUNG_PHANTOM_CELL_RECORD = 58_866

# `GEO-27`'s `2a/h` *labels* for the 1 g ball — arithmetic on the requested edge
# length, not a measurement of any mesh.
CELLS_ACROSS_1G_STEP4 = 1.65
CELLS_ACROSS_1G_THIS_RUNG = 4.96

# Step 4's readings on the 0.0075 rung, for the printed rung-to-rung move
# (`20260907T003548Z_MAT-4-step4.log:1939-1947`).  Comparands, not bounds.
STEP4_TEN_GRAM_PEAKS_W_PER_KG = {
    0: 6.347807489e-07,
    1: 6.326843420e-07,
    2: 6.331624338e-07,
    3: 6.327987576e-07,
}
STEP4_TEN_GRAM_PAIRS = {0: 0.003303, 1: 0.000756, 2: 0.000574, 3: 0.003132}
STEP4_ONE_GRAM_PAIRS = {0: 0.068383, 1: 0.029297, 2: 0.004116, 3: 0.047159}

# The mis-paired **1 g** control's predicted size, printed never asserted (rule
# (e)).  The 85.2523 / 85.2921 / 85.2750 / 85.2857% at
# `20260908T140457Z_MAT-4-step5.log:1969-1972` is the **10 g** column's
# mis-paired control on this same rung, so there is no prior 1 g measurement of
# this comparison to assert against — only a prediction that the 1 g control
# lands near it.  A ratio of two positive SARs cannot exceed 100%.
ONE_GRAM_CONTROL_PREDICTED = 0.85
ONE_GRAM_CONTROL_CEILING = 1.00


def _one_gram_rung_verdict(one_pairs):
    """The clause step 5 pre-registered, kept as the log's narration.

    Three branches, fixed precedence, evaluated from the readings so the clause
    printed cannot disagree with the table above it.  Since step 5b the (A)
    branch is *equivalent to* the gate below (worst pair ≤ band), so this is the
    assert's own words rather than a record awaiting a ruling; branches (B) and
    (C) are unreachable without the gate going red first, and are kept so a red
    log still says which class the miss fell in.
    """
    worst = max(one_pairs.values())
    if worst <= C4_COVARIANCE_BAND:
        return "(A)", (
            f"the worst 1 g C4 pair reads {worst * 100:.4f}%, INSIDE the "
            f"{C4_COVARIANCE_BAND * 100:.1f}% band the 10 g column is gated at "
            "— step 5's prediction landed and the 2026-09-08 10:30 review RULED "
            "the 1 g column a gate at this rung, which is what the four asserts "
            "below now run"
        )
    if worst <= ONE_GRAM_PREDICTED_HIGH:
        return "(B)", (
            f"the worst 1 g C4 pair reads {worst * 100:.4f}%, still outside the "
            f"{C4_COVARIANCE_BAND * 100:.1f}% band at "
            f"{CELLS_ACROSS_1G_THIS_RUNG} cells across the ball — the prediction "
            "of this step MISSES, and the finding is that five cells is not "
            "enough for a 6.2 mm ball; report, no band moves"
        )
    return "(C)", (
        f"the worst 1 g C4 pair reads {worst * 100:.4f}%, above even step 4's "
        f"predicted {ONE_GRAM_PREDICTED_HIGH * 100:.0f}% pointwise ceiling and "
        f"so not a monotone improvement on step 4's "
        f"{max(STEP4_ONE_GRAM_PAIRS.values()) * 100:.4f}% — a reading neither "
        "the band nor either prediction covers; report as-is for the review"
    )


def _one_gram_ball(built, k, j):
    """``SAR_1g(c_j; drive k)`` off the fixture's own solved fields.

    ``_build_mass_averaged`` computes the full 4x4 of **10 g** averages but only
    the *diagonal* of the 1 g ones, so the mis-paired 1 g comparison has to be
    integrated here.  Nothing is re-solved and nothing is re-implemented: the
    solved phasor, its σ, the density field, the centres and the 1 g radius all
    come out of that construction, and the operator is the package's own
    ``mass_averaged_sar`` at the same imported ``QUADRATURE_DEGREE``.

    The drive-to-``k`` map is ``P{k+1}`` — step 4's module labels its rows that
    way on this fixture (`20260908T140457Z_MAT-4-step5.log:1964-1967`) — and it
    is *checked*, not assumed: the ``j == k`` call reproduces the diagonal the
    construction already returned, asserted below at the exact-identity band.
    A wrong map would miss it by an order of magnitude, not by round-off.
    """
    solved = built["solves"][f"P{k + 1}"]
    return float(
        mass_averaged_sar(
            solved["fields"].e_complex,
            sigma=solved["fields"].sigma_field,
            rho=built["rho_field"],
            center=built["centres"][j],
            radius=built["radii"]["1 g"],
            comm=built["mesh"].comm,
            quadrature_degree=QUADRATURE_DEGREE,
        )["averaged_sar_w_per_kg"]
    )


def _add_one_gram_control(built):
    """The mis-paired **1 g** control, drive by drive, and its map check.

    ``control_1g[k]`` is ``|SAR_1g(c_{k+2}; k) - SAR_1g(c_k; k)| / SAR_1g(c_k; k)``
    — step 4's negative control at 1 g instead of 10 g: the *far-side* ball under
    the same drive, which the C4 identity says nothing about and which must miss
    the band by a mile or the 1 g gate above is measuring a constant field rather
    than a covariance.  Printed and predicted only (rule (e)).
    ``diagonal_miss[k]`` is the drive-map check described in ``_one_gram_ball``.
    """
    control, diagonal_miss = {}, {}
    for k in range(4):
        own = _one_gram_ball(built, k, k)
        far = _one_gram_ball(built, k, (k + 2) % 4)
        recorded = built["one_gram"][(k, k)]["averaged_sar_w_per_kg"]
        diagonal_miss[k] = abs(own / recorded - 1.0)
        control[k] = abs(far - own) / own
    built["control_1g"] = control
    built["one_gram_diagonal_miss"] = diagonal_miss
    return built


@pytest.fixture(scope="module")
def rung():
    """Step 4's construction, once, at ``phantom_resolution = 0.0025`` m.

    ``_build_mass_averaged`` is step 4's own body — four single-drive solves, 21
    ``mass_averaged_sar`` calls, the C4 pairing and the whole-phantom ball — and
    the only argument it takes is the rung.  Everything printed by it is step 4's
    printing; the block below adds only what this step owns.
    """
    built = _build_mass_averaged(phantom_resolution=PHANTOM_RESOLUTION_1G_RUNG)
    _add_one_gram_control(built)

    # comm.rank == 0 is where _build_mass_averaged printed; every value below is
    # already an MPI-reduced scalar (mass_averaged_sar and mean_sar reduce over
    # comm, _global_tag_cell_count MPI.SUMs the size_local restriction), so this
    # block is a print of reduced numbers and not a rank-local read.
    from mpi4py import MPI

    verdict, verdict_text = _one_gram_rung_verdict(built["one_pairs"])
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[MAT-4 step 5] THE 1 g COLUMN ON THE GEO-27 RUNG — step 4's "
            f"construction at phantom_resolution = {PHANTOM_RESOLUTION_1G_RUNG} m "
            f"(the block above is step 4's own printing, on this rung)\n"
            f"    (3) MESH, ASSERTED at the imported "
            f"{CELL_COUNT_BAND * 100:.0f}% CELL_COUNT_BAND against the records "
            f"the 2026-09-08 10:30 review registered from three windows (never "
            f"at equality):\n"
            f"        size_global   {built['cells']} vs the record "
            f"{ONE_GRAM_RUNG_CELL_RECORD} "
            f"({abs(built['cells'] / ONE_GRAM_RUNG_CELL_RECORD - 1.0) * 100:.4f}% "
            f"— ASSERTED < {CELL_COUNT_BAND * 100:.0f}%)\n"
            f"        phantom tag-3 {built['phantom_cells']} vs the record "
            f"{ONE_GRAM_RUNG_PHANTOM_CELL_RECORD} "
            f"({abs(built['phantom_cells'] / ONE_GRAM_RUNG_PHANTOM_CELL_RECORD - 1.0) * 100:.4f}% "
            f"— ASSERTED < {CELL_COUNT_BAND * 100:.0f}%)\n"
            f"        cells across the 1 g ball (GEO-27's 2a/h LABEL, not a "
            f"measurement): {CELLS_ACROSS_1G_THIS_RUNG} here vs "
            f"{CELLS_ACROSS_1G_STEP4} at step 4's rung",
            flush=True,
        )
        print(
            f"    (i) ASSERTED — the four cyclic 10 g C4 pairs against the "
            f"imported, unmoved {C4_COVARIANCE_BAND * 100:.1f}% band, beside "
            f"step 4's readings on the 0.0075 rung:",
            flush=True,
        )
        for k in range(4):
            here = built["ten_pairs"][k]
            there = STEP4_TEN_GRAM_PAIRS[k]
            print(
                f"        k={k}->{(k + 1) % 4}  10 g {here * 100:9.4f}%  "
                f"(step 4 {there * 100:9.4f}%, ratio {here / there:7.4f}x)  "
                f"ASSERTED <= {C4_COVARIANCE_BAND * 100:.1f}%",
                flush=True,
            )
        print(
            f"    (1) ASSERTED — the four cyclic 1 g C4 pairs against the SAME "
            f"imported, unmoved {C4_COVARIANCE_BAND * 100:.1f}% band, the gate "
            f"the 2026-09-08 10:30 review registered at "
            f"{CELLS_ACROSS_1G_THIS_RUNG} cells across the ball; beside them the "
            f"mis-paired 1 g control (c_k+2; k), PRINTED and PREDICTED "
            f"~{ONE_GRAM_CONTROL_PREDICTED * 100:.0f}% (rule (e): the 85.3% on "
            f"record is the 10 g column, ceiling "
            f"{ONE_GRAM_CONTROL_CEILING * 100:.0f}%):",
            flush=True,
        )
        for k in range(4):
            here = built["one_pairs"][k]
            there = STEP4_ONE_GRAM_PAIRS[k]
            print(
                f"        k={k}->{(k + 1) % 4}   1 g {here * 100:9.4f}%  "
                f"(step 4 {there * 100:9.4f}%, ratio {here / there:7.4f}x)  "
                f"ASSERTED <= {C4_COVARIANCE_BAND * 100:.1f}%   "
                f"mis-paired 1 g control (c_{(k + 2) % 4}; {k}) "
                f"{built['control_1g'][k] * 100:9.4f}% (PRINTED, PREDICTED "
                f"~{ONE_GRAM_CONTROL_PREDICTED * 100:.0f}%, ASSERTED BY NOTHING; "
                f"diagonal re-integration miss "
                f"{built['one_gram_diagonal_miss'][k]:.3e}, ASSERTED <= "
                f"{EXACT_IDENTITY_RTOL:.0e})",
                flush=True,
            )
        print(
            f"    (2) PRINTED, PREDICTED — the per-drive peaks, rung to rung.  "
            f"NOT a C95.3 compliance figure on either rung:",
            flush=True,
        )
        for k in range(4):
            peak = built["peaks"][k]
            ref = STEP4_TEN_GRAM_PEAKS_W_PER_KG[k]
            print(
                f"        k={k}  10 g peak over centres {peak:.9e} W/kg  "
                f"(step 4 {ref:.9e}, move {(peak / ref - 1.0) * 100:+8.4f}%)   "
                f"1 g at the drive's own centre "
                f"{built['one_gram'][(k, k)]['averaged_sar_w_per_kg']:.9e} W/kg "
                f"(step 4 printed no 1 g absolute — only the pairs above)",
                flush=True,
            )
        print(
            f"    (ii) ASSERTED — the whole-phantom ball "
            f"(r = {WHOLE_PHANTOM_BALL_RADIUS_M} m) on THIS rung's partition: "
            f"{built['whole']['dissipated_power_w']:.12e} W vs the tag-3 integral's "
            f"{built['tagged']['dissipated_power_w']:.12e} W, relative "
            f"{abs(built['whole']['dissipated_power_w'] / built['tagged']['dissipated_power_w'] - 1.0):.6e} "
            f"<= {EXACT_IDENTITY_RTOL:.0e}\n"
            f"        PRINTED, NOT ASSERTED: that power against step 4's rung "
            f"5.587038273302e-08 W is a RUNG-TO-RUNG MOVE, not a record — "
            f"{abs(built['whole']['dissipated_power_w'] / 5.587038273302e-08 - 1.0) * 100:+.4f}% "
            f"(step 4's STEP3F record belongs to the 0.0075 mesh and is NOT "
            f"re-asserted here)",
            flush=True,
        )
        print(
            f"    PRE-REGISTERED 1 g VERDICT ON THIS RUNG: {verdict} — "
            f"{verdict_text}\n"
            "    SCOPE: one rung, 10 MHz, degree 1, four single drives.  The "
            "1 g AND 10 g columns are C4-gated on this 0.0025 m rung at the same "
            "imported unmoved 5% band, and the rung's mesh is a version-tagged "
            "record asserted at 1%.  NO absolute SAR, "
            "NO C95.3 compliance or limit claim, no homogeneity, no Larmor, and "
            "NO convergence claim — two rungs of one quantity are not a rate.",
            flush=True,
        )

    built["verdict_1g_rung"] = verdict
    built["verdict_1g_rung_text"] = verdict_text
    return built


@complex_only
def test_every_averaging_ball_lies_inside_the_phantom_on_this_rung(rung):
    """Containment, as step 4: no ball straddles the phantom's surface.

    The averaging ball is a UFL ``conditional`` and the integrand jumps at the
    phantom boundary (σ inside, 0 outside), so a ball reaching outside would
    average a discontinuity and its C4 identity would be measuring the mesh's
    rendering of a CAD surface.  Geometry is unchanged from step 4 — the radii
    come from ``averaging_ball_radius`` and the centres from ``CENTRE_RADIUS_M``
    — but the assert is cheap and this module must not import a *conclusion*.
    """
    reach = CENTRE_RADIUS_M + rung["radii"]["10 g"]
    assert reach < PHANTOM_RADIUS, (
        f"the 10 g ball reaches r = {reach:.6f} m from the axis, outside the "
        f"phantom's {PHANTOM_RADIUS:.6f} m CAD radius"
    )
    for k, centre in rung["centres"].items():
        assert abs(centre[2]) + rung["radii"]["10 g"] < 0.5 * PHANTOM_HEIGHT, (
            f"centre {k} at z = {centre[2]:.6f} m puts the 10 g ball through the "
            "phantom's flat face"
        )


@complex_only
def test_the_whole_phantom_ball_reproduces_the_tagged_integral_on_this_rung(rung):
    """Anchor (ii): the operator's cell coverage on the finer rung's partition.

    Same statement as step 4's, on a different mesh and therefore a different
    partition: ``mass_averaged_sar`` integrates ``½σ|E|²`` weighted by the ball
    indicator over the whole mesh, ``mean_sar`` integrates it over the tag-3
    cells, σ is zero in the air, and a 0.0501 m ball encloses the phantom
    (circumradius exactly 0.05 m) while reaching no conductor.  The two are the
    same discrete integral written twice, both quadratures exact for the degree-2
    integrand, so the band is round-off over an MPI reduction — imported and
    unmoved at 1e-10.  A miss is missed cells, double-counted ghosts, or an
    unreduced local sum on the 199 920-cell partition; it is a known-issues
    entry, never a widened band.
    """
    whole = rung["whole"]
    tagged = rung["tagged"]
    power_miss = abs(whole["dissipated_power_w"] / tagged["dissipated_power_w"] - 1.0)
    assert power_miss <= EXACT_IDENTITY_RTOL, (
        f"on the {PHANTOM_RESOLUTION_1G_RUNG} m rung the enclosing ball absorbs "
        f"{whole['dissipated_power_w']:.12e} W against the tagged integral's "
        f"{tagged['dissipated_power_w']:.12e} W — relative {power_miss:.6e} > "
        f"{EXACT_IDENTITY_RTOL:.0e}"
    )
    mass_miss = abs(
        whole["mass_kg"] / (PHANTOM_RHO_KG_PER_M3 * tagged["volume_m3"]) - 1.0
    )
    assert mass_miss <= EXACT_IDENTITY_RTOL, (
        f"the ball's mass {whole['mass_kg']:.12e} kg is not rho times this rung's "
        f"phantom meshed volume {PHANTOM_RHO_KG_PER_M3 * tagged['volume_m3']:.12e} "
        f"kg — relative {mass_miss:.6e} > {EXACT_IDENTITY_RTOL:.0e}"
    )


@complex_only
@pytest.mark.parametrize("k", [0, 1, 2, 3])
def test_the_ten_gram_average_is_c4_covariant_on_the_finer_rung(rung, k):
    """**The gate of this step.** Step 4's 10 g identity survives ``h/3``.

    Exactly the assert step 4 runs at 0.0075 m, against the *same* imported and
    unmoved ``C4_COVARIANCE_BAND``: an operator that is C4-covariant at ``h`` is
    C4-covariant at ``h/3``, so this is the anchor that says the finer rung is
    the same fixture measured better rather than a different one.  A pair above
    the band is a finding about this mesh — its partition, its phantom surface —
    and is a known-issues entry with both columns, never a band to widen.
    """
    reading = rung["ten_pairs"][k]
    assert reading <= C4_COVARIANCE_BAND, (
        f"on the {PHANTOM_RESOLUTION_1G_RUNG} m rung the 10 g C4 pair "
        f"k={k}->{(k + 1) % 4} reads {reading * 100:.4f}%, outside the imported "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band (step 4's 0.0075 rung read "
        f"{STEP4_TEN_GRAM_PAIRS[k] * 100:.4f}% on the same pair; SAR "
        f"{rung['ten_gram'][(k, k)]['averaged_sar_w_per_kg']:.9e} vs "
        f"{rung['ten_gram'][((k + 1) % 4, (k + 1) % 4)]['averaged_sar_w_per_kg']:.9e} "
        "W/kg)"
    )


@complex_only
@pytest.mark.parametrize("k", [0, 1, 2, 3])
def test_the_one_gram_average_is_c4_covariant_on_the_finer_rung(rung, k):
    """**The gate step 5b registers.** The 1 g column, asserted at last.

    Step 4 could only *print* this column: a 6.204 mm ball on a 7.5 mm phantom
    ``h`` is 1.65 cells across and read 6.8383% worst, verdict (b), "the route to
    a 1 g gate is ``h``".  Step 5 walked that route and measured 0.0957 / 0.1199
    / 0.1305 / 0.1065% at 4.96 cells across on two windows agreeing to the
    printed digit (`20260908T140457Z_MAT-4-step5.log:1990-1993`,
    `20260908T141147Z_MAT-4-step5-rerun.log:1990-1993`) — a factor 38 of
    headroom against the band — and the 2026-09-08 10:30 review ruled the column
    a gate here.  The band is `C4_COVARIANCE_BAND`, imported and **unmoved** at
    the same 5% the 10 g column has always been gated at; nothing was widened to
    admit this column, the mesh changed instead.

    A miss is a finding about this mesh or this operator — a known-issues entry
    with both columns, never a band to widen.
    """
    reading = rung["one_pairs"][k]
    assert reading <= C4_COVARIANCE_BAND, (
        f"on the {PHANTOM_RESOLUTION_1G_RUNG} m rung the 1 g C4 pair "
        f"k={k}->{(k + 1) % 4} reads {reading * 100:.4f}%, outside the imported "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band (step 4's 0.0075 rung read "
        f"{STEP4_ONE_GRAM_PAIRS[k] * 100:.4f}% on the same pair; SAR "
        f"{rung['one_gram'][(k, k)]['averaged_sar_w_per_kg']:.9e} vs "
        f"{rung['one_gram'][((k + 1) % 4, (k + 1) % 4)]['averaged_sar_w_per_kg']:.9e} "
        "W/kg)"
    )


@complex_only
@pytest.mark.parametrize("k", [0, 1, 2, 3])
def test_the_mis_paired_one_gram_control_is_attributed_to_its_own_drive(rung, k):
    """The control's map check — *not* a claim about the control's size.

    The mis-paired 1 g control is printed and predicted only (rule (e)): the
    ~85% on record is the **10 g** column's, so there is no prior 1 g
    measurement of this comparison to assert against.  What is asserted is that
    the number is attributed to the right drive: re-integrating the *diagonal*
    ``SAR_1g(c_k; drive P{k+1})`` must reproduce the value
    ``_build_mass_averaged`` already returned for pair ``k``, which it can only
    do if ``P{k+1}`` is drive ``k``.  Same integrand, same cells, same
    quadrature, so the band is the imported exact-identity round-off, and a
    wrong map misses it by an order of magnitude.
    """
    miss = rung["one_gram_diagonal_miss"][k]
    assert miss <= EXACT_IDENTITY_RTOL, (
        f"re-integrating SAR_1g(c_{k}; drive P{k + 1}) does not reproduce the "
        f"construction's own 1 g diagonal for k={k} — relative {miss:.6e} > "
        f"{EXACT_IDENTITY_RTOL:.0e}, so the printed mis-paired control "
        f"{rung['control_1g'][k] * 100:.4f}% is attributed to the wrong drive"
    )


@complex_only
def test_the_rung_meshes_to_its_registered_cell_counts(rung):
    """The rung's mesh, pinned as a version-tagged record at the imported band.

    `GEO-27` read 199 920 / 58 866 once; step 5 repeated both integers exactly on
    two further windows (`20260908T033218Z_GEO-27.log:7155`,
    `…140457Z:1981-1982`, `…141147Z:1981-1982`), which is what the 2026-09-08
    10:30 review pinned them from.  The band is the imported `CELL_COUNT_BAND`
    (1%) and **not** equality: a mesher upgrade moves a count by a fraction of a
    percent and an exact record would then fail for a reason that has nothing to
    do with this fixture (`OPS-27`'s stale-exact class), while a *different*
    mesh cannot hide inside 1%.  A reading outside the band is an `OPS-18`-class
    drift — a known-issues entry and a re-record under the (1*) licence, never a
    widened band.
    """
    cell_miss = abs(rung["cells"] / ONE_GRAM_RUNG_CELL_RECORD - 1.0)
    assert cell_miss < CELL_COUNT_BAND, (
        f"the {PHANTOM_RESOLUTION_1G_RUNG} m rung meshes to {rung['cells']} "
        f"cells against the registered {ONE_GRAM_RUNG_CELL_RECORD} — relative "
        f"{cell_miss:.6f} >= {CELL_COUNT_BAND}"
    )
    phantom_miss = abs(
        rung["phantom_cells"] / ONE_GRAM_RUNG_PHANTOM_CELL_RECORD - 1.0
    )
    assert phantom_miss < CELL_COUNT_BAND, (
        f"the phantom (tag 3) carries {rung['phantom_cells']} cells against the "
        f"registered {ONE_GRAM_RUNG_PHANTOM_CELL_RECORD} — relative "
        f"{phantom_miss:.6f} >= {CELL_COUNT_BAND}"
    )
