"""`TH-13` steps 1 / 1′: does *any* ``W_m ≫ W_e`` fixture display the degree-2
``W_e`` explosion, or only the coil's feed model?

Commissioned by the 2026-08-23 weekly review (PROJECT_PLAN §7 `TH-13`) from the
confound `TH-12` step 3 named against itself.  Step 3 read the explosion as
**COIL-SPECIFIC** — the smoke fixture's incompatible axial drive moves
``W_e/W_m`` by 1.155× across element order and the sphere's imposed field by
1.015×, against the coil's 3.426e+07× — but the three fixtures do not share a
baseline: ``W_e/W_m`` is 2.16 on the smoke box, 1.07 on the sphere and 6.7e-6 on
the coil.  A gradient contamination of fixed *absolute* size therefore moves the
coil's ratio ~1e6× more than either cheap fixture's, whatever injected it.  So
step 3 excluded "``J·n ≠ 0`` is sufficient" but could not separate

* **FEED** — the coil's feed model injects gradient content; from
* **CLASS** — only a fixture with ``W_m ≫ W_e`` can *display* a contamination
  that is present everywhere, and the defect is the ungauged second-order
  gradient space itself.

The discriminator this module runs is the missing cell of that table: a fixture
that is **magnetically dominated** *and* has a **compatible drive**.  It is the
smoke box's own cylindrical mesh, driven by `POST-5` step 2's closed azimuthal
loop (``J = (-y, x, 0)/a`` restricted to the rod: ``div J = 0`` pointwise and
``J·n = 0`` on every boundary, so there is no incompatible part for the gradient
subspace to absorb), driven at **two frequencies on one mesh**.

**Step 1 ran at 10 MHz and missed its own precondition** (2026-08-30): the
fixture read degree-1 ``W_e/W_m`` = 1.952350e-02 against the ≤ 1e-2 band, so it
is not magnetically dominated and is not the missing cell.  Worse, and this is
what step 1′ fixes: from a 1.95e-2 baseline a 1e3× CLASS move would have to
reach ``W_e/W_m`` ≈ 20, well past the O(1) equipartition every fixture in the
family sits at — CLASS was arithmetically unreachable before the run began, so
the bands and the fixture were never compatible.

**Step 1′ rescoped by ω²** (2026-08-30 weekly review, §7): at fixed impressed
current ``W_e/W_m ~ ω²``, so the *same* fixture at **1 MHz** was predicted to
read ≈ 1.95e-4 — inside the unchanged band by 50×, with ~5e3× of headroom under
equipartition, which would make both verdict bands representable for the first
time.  **Measured, it does not** (`20260830T200305Z_TH-13-step1prime.log`): the
1 MHz row reads **1.926692e-02**, 98.7× the prediction and 1.3% *below* the
10 MHz row across a full decade of ω.  ``W_e``, ``W_m`` and the dissipated power
are all frequency-independent on this fixture, so the quasi-static ``E ~ ωA``
argument does not describe this solve and **frequency is not the knob that makes
the fixture magnetically dominated**.  The precondition therefore still fails,
and per §7 the step stops on that finding with the assertion left red rather
than loosened — the red moves from the 10 MHz row to the 1 MHz one, it does not
multiply.

The 10 MHz row stays in the table as a **recorded** reading: its precondition is
no longer asserted (1.95e-2 against 1e-2 is a known number and re-asserting it
gates nothing), but its degree-1 ratio and its in-between 5.156e+01× move are
asserted as the rescope's negative control — both reproduced to rtol 1e-3.

**Pre-registered, before the run** (PROJECT_PLAN §7 `TH-13` steps 1 / 1′,
restated in :data:`MAGNETIC_DOMINANCE_MAX` / :data:`CLASS_RATIO_FACTOR` /
:data:`FEED_RATIO_FACTOR` / :data:`OMEGA_SQUARED_PREDICTED_RATIO`):

* **Precondition, asserted at 1 MHz** — the fixture must first *be* magnetically
  dominated: degree-1 ``W_e/W_m ≤ 1e-2``, the band unmoved from step 1.  If it
  is not, the fixture is wrong, the reading below means nothing, and §7 says the
  step stops with that as its finding rather than reinterpreting the ratio.
* **The ω² prediction, printed not asserted** — 1.95e-4, measured 1.9267e-2.
  Pre-registered as an assertion; demoted to a printed record *after* the
  measurement refuted it, with the numbers in-comment at
  :data:`OMEGA_SQUARED_PREDICTED_RATIO`, because a second red on the same dead
  premise gates nothing the precondition does not.
* **Verdict** — the cross-order move in ``W_e/W_m`` on the 1 MHz row:
  ``≥ 1e3×`` ⇒ **CLASS**, ``≤ 10×`` ⇒ **FEED**.  In between is the finding,
  recorded, with no band invented around it.  A degree-2 ``W_e/W_m ≈ 1`` here,
  as at 10 MHz, would mean the contamination *saturates* at equipartition and
  "cross-order move" is the wrong discriminant — itself the finding, and step
  2's cue.

**Negative controls** (§7): `TH-12` step 3's own two fixtures, run here on the
same code path and through the same imported helpers, must reproduce their
recorded moves — smoke 1.155×, sphere 1.015× — so a CLASS reading is a property
of the new fixture and not of a code change since 2026-08-19; and the 10 MHz
loop row must reproduce step 1's own two numbers at rtol 1e-3.  The `POST-5`
dissipated-power anchor (1.199162e-06 W at rtol 1e-6 on 1 405 cells) rides along
with the smoke column, as it does in step 3.

**Energy forms are imported, never restated** (§7 trap):
:func:`fem_em_solver.core.resonance.stored_electric_energy` and
``test_coil_loading_larmor_probe._stored_magnetic_energy`` — the two forms
`TH-12` step 2 measured the coil with, reached here through step 3's own
``_solve_smoke_at_degree`` / ``_energies_of_sphere_row`` so that all four
fixtures are literally the same quantity measured four times.  ``ufl.inner``
conjugates its second argument; a hand-rolled ``W_e`` would flip the convention.

Scope: mechanism attribution only.  No coil solve runs here (the coil at degree
2 is 61.94 GiB), no coil number moves, the two degree-2 coil identity tests stay
failing, the known-issues degree-2 entry stays open, and §10's production-order
decision stays the weekly review's with this verdict on record.  Step 2 (the
absolute gradient content of ``E``) is scoped from this verdict, not run here.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_degree2_gradient_discriminator.py -v -s'
"""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from dolfinx import fem
from mpi4py import MPI

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.core.resonance import stored_electric_energy

from tests.complex_mode import complex_only
from tests.solver.test_time_harmonic_smoke import (
    AXIAL_RECORD_DISSIPATED_W,
    EPSILON_R,
    SIGMA,
    _azimuthal_current,
    _smoke_mesh,
)
from tests.validation.test_coil_loading_larmor_probe import _stored_magnetic_energy
from tests.validation.test_degree2_energy_mechanism import (
    COIL_W_E_W_M_DEGREE1,
    COIL_W_E_W_M_DEGREE2,
    RECORD_REPRODUCTION_RTOL,
    SMOKE_RESOLUTION,
    _energies_of_sphere_row,
    _ratio_move,
    _solve_smoke_at_degree,
)
from tests.validation.test_lossy_sphere_degree2 import (
    POWER_IMAGINARY_BOUND,
    _run_at_degree,
)

# ---------------------------------------------------------------------------
# The pre-registered bands (PROJECT_PLAN §7 `TH-13` step 1).
# ---------------------------------------------------------------------------
# The precondition: the fixture must be magnetically dominated at degree 1, or
# it is not the missing cell of `TH-12` step 3's table at all.
MAGNETIC_DOMINANCE_MAX = 1.0e-2
# The verdict bands, the same two factors step 3 pre-registered so the two
# readings are commensurable.
CLASS_RATIO_FACTOR = 1.0e3
FEED_RATIO_FACTOR = 10.0

# The loop fixture's frequency.  With an impressed current held fixed, a
# quasi-static solve has ``B`` frequency-independent and ``E ~ ωA``, so
# ``W_e/W_m ~ ω²``; the frequency is therefore the one knob that moves this
# fixture's baseline without touching mesh, material, drive or forms.
#
# Step 1 ran at the coil's own 10 MHz and missed the precondition: it read
# ``W_e/W_m`` = 1.952350e-02 at degree 1 against the ≤ 1e-2 band, and — the
# defect in the step as written — from that baseline a 1e3× CLASS move would
# have had to reach ``W_e/W_m`` ≈ 20, far past the O(1) equipartition every
# fixture in the family sits at, so CLASS was arithmetically unreachable before
# the run began.  Step 1′ rescopes by ω²: at 1 MHz the same fixture is predicted
# to read ≈ 1.95e-4, inside the *unchanged* band by 50×, with ~5e3× of headroom
# under equipartition, so both verdict bands are representable for the first
# time.  Everything else about the box (material, mesh, tags, drive) is the
# smoke fixture's, imported.
LOOP_FREQUENCY_HZ = 1.0e6
# The step-1 frequency, kept as a *recorded* row rather than a gate: the 10 MHz
# fixture is now known not to be magnetically dominated, so asserting its
# precondition again gates nothing.  What it does still do is anchor the run
# against step 1's own reading on the same code path.
LOOP_RECORD_FREQUENCY_HZ = 10.0e6
LOOP_FREQUENCIES_HZ = (LOOP_FREQUENCY_HZ, LOOP_RECORD_FREQUENCY_HZ)

# `TH-13` step 1's recorded readings at 10 MHz
# (`20260830T020301Z_TH-13-step1.log`, PROJECT_PLAN §7): the degree-1 ratio that
# failed the precondition, and the in-between cross-order move.  Both are
# reproduced here as the negative control for the rescope — a moved 10 MHz
# column means this run is not comparable with step 1's.
STEP1_RECORD_DEGREE1_RATIO = 1.952350e-02
STEP1_RECORD_MOVE = 5.156e01
STEP1_RECORD_RTOL = 1.0e-3

# The ω² prediction for the 1 MHz row, pre-registered in §7 before the run:
# 1.952350e-02 × (1/10)² ≈ 1.95e-4, to be asserted within a factor of two.
#
# MEASURED 2026-08-30 (`20260830T200305Z_TH-13-step1prime.log`), REFUTED:
# the 1 MHz row reads W_e/W_m = **1.926692e-02** at degree 1 — 98.7× the
# prediction, and only 1.3% below the 10 MHz row's 1.952350e-02 across a full
# decade of ω.  On this fixture ``W_e/W_m`` is frequency-INDEPENDENT: W_e moves
# 5.621559e-19 → 5.544787e-19 J and W_m 2.879380e-17 → 2.877879e-17 J, i.e.
# both `E` and `H` are unchanged by the frequency, so the quasi-static
# ``E ~ ωA`` argument the rescope rests on does not describe this solve.  The
# prediction is therefore kept as a *printed* record rather than an assertion:
# re-asserting a premise that measurement has killed would only duplicate the
# precondition red below, and per §7 no band is invented around a negative.
# The factor stays defined for the print and for whoever scopes step 2.
OMEGA_SQUARED_PREDICTED_RATIO = STEP1_RECORD_DEGREE1_RATIO * (
    LOOP_FREQUENCY_HZ / LOOP_RECORD_FREQUENCY_HZ
) ** 2
OMEGA_SQUARED_PREDICTION_FACTOR = 2.0

# `TH-12` step 3's recorded cross-order moves
# (`20260819T183425Z_TH-12-step3-warm.log`, PROJECT_PLAN §7): the negative
# control this step needs, so a CLASS reading below is the new fixture's and not
# a code change.  Reproduced at step 3's own imported `EX-25` 1% band —
# `RECORD_REPRODUCTION_RTOL` — rather than a tighter one invented here.
SMOKE_MOVE_RECORD = 1.155
SPHERE_MOVE_RECORD = 1.015


def _complex_ohmic_power(e_complex, sigma: float, comm) -> complex:
    """``½σ∫ E·conj(E) dV`` over the whole box, kept complex.

    ``ufl.inner`` conjugates its second argument, so the imaginary part is
    round-off rather than a truncated quantity; ``|Im P|/Re P`` is therefore a
    consistency read on the solve at each order, the same one
    `TH-12` step 1 gates the sphere with (:data:`POWER_IMAGINARY_BOUND`).
    ``assemble_scalar`` is rank-local — reduced here before the caller sees it.
    """
    local = fem.assemble_scalar(
        fem.form(0.5 * sigma * ufl.inner(e_complex, e_complex) * ufl.dx)
    )
    return complex(comm.allreduce(local, op=MPI.SUM))


def _solve_loop_at_degree(degree: int, comm, frequency_hz: float) -> dict:
    """The closed azimuthal loop drive on the smoke box at ``frequency_hz``.

    Byte-for-byte the smoke fixture except for the two things this step varies:
    the drive (`POST-5` step 2's :func:`_azimuthal_current`, imported) and the
    frequency (:data:`LOOP_FREQUENCIES_HZ`).  ``gauge_penalty`` is left at the
    solver default, which is what `TH-12` steps 2 and 3 measured every recorded
    ratio on — the ungauged second-order gradient space is the object under
    test, so gauging it here would answer a different question.
    """
    mesh, cell_tags, facet_tags = _smoke_mesh(SMOKE_RESOLUTION, comm)
    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=frequency_hz,
        material=HomogeneousMaterial(sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=1.0),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
    )
    solver = TimeHarmonicSolver(problem, degree=degree)

    j_azimuthal = _azimuthal_current(mesh)

    def current_density(x):
        # The coefficient is already the field; x is the solver's
        # SpatialCoordinate and is deliberately unused (`POST-5` step 2).
        return j_azimuthal

    fields = solver.solve(current_density=current_density, subdomain_id=1)

    tdim = mesh.topology.dim
    ncells = int(comm.allreduce(mesh.topology.index_map(tdim).size_local, op=MPI.SUM))
    v_space = fields.e_complex.function_space
    n_dofs = int(v_space.dofmap.index_map.size_global * v_space.dofmap.index_map_bs)
    p_complex = _complex_ohmic_power(fields.e_complex, SIGMA, comm)
    return {
        "degree": degree,
        "frequency_hz": frequency_hz,
        "ncells": ncells,
        "n_dofs": n_dofs,
        "w_e": stored_electric_energy(fields, comm=comm),
        "w_m": _stored_magnetic_energy(fields.e_complex, fields.omega, comm),
        "dissipated_power_w": float(np.real(p_complex)),
        "power_imaginary": abs(float(np.imag(p_complex))) / abs(float(np.real(p_complex))),
    }


def _verdict(loop_move: float) -> str:
    if loop_move >= CLASS_RATIO_FACTOR:
        return "CLASS (the ungauged second-order gradient space itself)"
    if loop_move <= FEED_RATIO_FACTOR:
        return "FEED (the coil's feed model injects it)"
    return "IN-BETWEEN (recorded, not forced)"


def _label(frequency_hz: float) -> str:
    return f"loop {frequency_hz / 1e6:.0f} MHz"


@pytest.fixture(scope="module")
def discriminator_rows():
    """Both loop rows at both orders, plus step 3's two control fixtures."""
    comm = MPI.COMM_WORLD
    loop = {
        frequency_hz: {
            degree: _solve_loop_at_degree(degree, comm, frequency_hz)
            for degree in (1, 2)
        }
        for frequency_hz in LOOP_FREQUENCIES_HZ
    }
    smoke = {degree: _solve_smoke_at_degree(degree, comm) for degree in (1, 2)}
    sphere = {
        degree: _energies_of_sphere_row(_run_at_degree(degree), comm)
        for degree in (1, 2)
    }
    return {"loop": loop, "smoke": smoke, "sphere": sphere}


def _print_table(rows: dict) -> None:
    comm = MPI.COMM_WORLD
    if comm.rank != 0:
        return
    print("\n[TH-13 step 1'] stored energies at N1curl degree 1 vs 2:")
    print(
        "  fixture         deg   cells     DOFs        W_m [J]        W_e [J]"
        "      W_e/W_m"
    )
    named = [
        (_label(frequency_hz), rows["loop"][frequency_hz])
        for frequency_hz in LOOP_FREQUENCIES_HZ
    ] + [("smoke", rows["smoke"]), ("sphere", rows["sphere"])]
    for name, pair in named:
        for degree in (1, 2):
            row = pair[degree]
            print(
                f"  {name:<14s}  {degree:d}  {row['ncells']:6d}  "
                f"{row['n_dofs']:8d}  {row['w_m']:.6e}  {row['w_e']:.6e}  "
                f"{row['w_e'] / row['w_m']:.6e}"
            )
    for frequency_hz in LOOP_FREQUENCIES_HZ:
        for degree in (1, 2):
            row = rows["loop"][frequency_hz][degree]
            print(
                f"  {_label(frequency_hz)} degree {degree}: dissipated "
                f"{row['dissipated_power_w']:.6e} W, |Im P|/Re P = "
                f"{row['power_imaginary']:.3e}"
            )
    print(
        f"  coil (printed, `TH-12` step 2 record, not re-run): "
        f"W_e/W_m = {COIL_W_E_W_M_DEGREE1:.6e} at degree 1 -> "
        f"{COIL_W_E_W_M_DEGREE2:.6e} at degree 2, a "
        f"{COIL_W_E_W_M_DEGREE2 / COIL_W_E_W_M_DEGREE1:.3e}x move"
    )
    moves = ", ".join(
        f"{_label(frequency_hz)} {_ratio_move(rows['loop'][frequency_hz]):.3e}x"
        for frequency_hz in LOOP_FREQUENCIES_HZ
    )
    print(
        f"  cross-order move in W_e/W_m: {moves} (compatible drive), "
        f"smoke {_ratio_move(rows['smoke']):.3e}x (J.n != 0, control), "
        f"sphere {_ratio_move(rows['sphere']):.3e}x (imposed field, control)"
    )
    for frequency_hz in LOOP_FREQUENCIES_HZ:
        gated = "GATED" if frequency_hz == LOOP_FREQUENCY_HZ else "RECORDED, not gated"
        one = rows["loop"][frequency_hz][1]
        print(
            f"  precondition ({gated}): {_label(frequency_hz)} degree-1 W_e/W_m "
            f"= {one['w_e'] / one['w_m']:.6e} against the pre-registered "
            f"<= {MAGNETIC_DOMINANCE_MAX:.0e}"
        )
    measured = (
        rows["loop"][LOOP_FREQUENCY_HZ][1]["w_e"]
        / rows["loop"][LOOP_FREQUENCY_HZ][1]["w_m"]
    )
    print(
        f"  omega^2 rescope: predicted {OMEGA_SQUARED_PREDICTED_RATIO:.6e} at "
        f"{LOOP_FREQUENCY_HZ / 1e6:.0f} MHz from the "
        f"{STEP1_RECORD_DEGREE1_RATIO:.6e} step-1 record at "
        f"{LOOP_RECORD_FREQUENCY_HZ / 1e6:.0f} MHz; measured "
        f"{measured:.6e}, i.e. {measured / OMEGA_SQUARED_PREDICTED_RATIO:.1f}x "
        f"the prediction and {measured / STEP1_RECORD_DEGREE1_RATIO:.4f}x the "
        f"10 MHz reading -- W_e/W_m is frequency-INDEPENDENT on this fixture "
        f"and the omega^2 premise is REFUTED"
    )
    print(
        f"  bands: >= {CLASS_RATIO_FACTOR:.0e}x on the loop => CLASS; "
        f"<= {FEED_RATIO_FACTOR:.0f}x => FEED"
    )
    print(
        f"  VERDICT ({_label(LOOP_FREQUENCY_HZ)}): "
        f"{_verdict(_ratio_move(rows['loop'][LOOP_FREQUENCY_HZ]))}",
        flush=True,
    )


@complex_only
@pytest.mark.integration
def test_the_loop_fixture_is_magnetically_dominated(discriminator_rows):
    """Precondition (§7 step 1′), asserted at 1 MHz: degree-1 ``W_e/W_m ≤ 1e-2``.

    Runs first and prints the whole table, so no verdict is read against an
    unverified fixture.  This is the entire reason the fixture exists: `TH-12`
    step 3's two cheap fixtures sit at ``W_e/W_m`` 2.16 and 1.07, the coil at
    6.7e-6, and nothing in the tree occupied the magnetically-dominated cell
    with a *compatible* drive.  If this assertion fails the fixture is not that
    cell, the cross-order move below discriminates nothing, and §7 says the step
    stops on that finding rather than reinterpreting the number.

    The band is step 1's, unmoved: what step 1′ changed is the *fixture's*
    frequency, on the pre-registered ω² argument, not the bar it has to clear.
    **The rescope failed** — 1.926692e-02 at 1 MHz against 1.952350e-02 at
    10 MHz, so this assertion is red on `main` by design, as step 1's was at
    10 MHz.  It is the chunk's finding, not a defect to be tuned away: no band
    moves here without a fixture that actually clears it.
    """
    _print_table(discriminator_rows)
    one = discriminator_rows["loop"][LOOP_FREQUENCY_HZ][1]

    assert one["ncells"] == 1405, (
        f"the loop fixture meshed to {one['ncells']} cells, not the smoke box's "
        f"recorded 1 405 — the mesh moved under the control columns"
    )
    ratio = one["w_e"] / one["w_m"]
    assert ratio <= MAGNETIC_DOMINANCE_MAX, (
        f"the closed azimuthal drive at {LOOP_FREQUENCY_HZ / 1e6:.0f} MHz reads "
        f"W_e/W_m = {ratio:.6e} at degree 1, over the pre-registered "
        f"{MAGNETIC_DOMINANCE_MAX:.0e} — this fixture is not magnetically "
        f"dominated, so it is not the missing cell of `TH-12` step 3's table "
        f"and its cross-order move discriminates FEED from CLASS not at all"
    )
    for frequency_hz in LOOP_FREQUENCIES_HZ:
        for degree in (1, 2):
            row = discriminator_rows["loop"][frequency_hz][degree]
            assert row["power_imaginary"] < POWER_IMAGINARY_BOUND, (
                f"the {_label(frequency_hz)} fixture's ohmic power at degree "
                f"{degree} carries an imaginary part "
                f"{row['power_imaginary']:.3e} of the real part, over the "
                f"{POWER_IMAGINARY_BOUND:.0e} family bound — inner() "
                f"conjugates, so this is a solve defect, not a convention"
            )


@complex_only
@pytest.mark.integration
def test_the_step3_controls_reproduce_their_recorded_moves(discriminator_rows):
    """Negative control (§7): step 3's two fixtures still read 1.155× / 1.015×.

    Both run here through step 3's own imported helpers, so this is the same
    code path measured on 2026-08-19.  If either control has drifted, the loop
    fixture's move is not comparable with the recorded coil / smoke / sphere
    family and the verdict below is not attributable to the fixture.
    """
    smoke_move = _ratio_move(discriminator_rows["smoke"])
    sphere_move = _ratio_move(discriminator_rows["sphere"])

    assert np.isclose(smoke_move, SMOKE_MOVE_RECORD, rtol=RECORD_REPRODUCTION_RTOL), (
        f"the `TH-12` step 3 smoke control moved {smoke_move:.4f}x in W_e/W_m "
        f"across order against its recorded {SMOKE_MOVE_RECORD:.3f}x"
    )
    assert np.isclose(sphere_move, SPHERE_MOVE_RECORD, rtol=RECORD_REPRODUCTION_RTOL), (
        f"the `TH-12` step 3 sphere control moved {sphere_move:.4f}x in W_e/W_m "
        f"across order against its recorded {SPHERE_MOVE_RECORD:.3f}x"
    )

    dissipated = discriminator_rows["smoke"][1]["dissipated_power_w"]
    assert np.isclose(dissipated, AXIAL_RECORD_DISSIPATED_W, rtol=1e-6), (
        f"the degree-1 smoke column dissipated {dissipated:.6e} W against the "
        f"`POST-5` record {AXIAL_RECORD_DISSIPATED_W:.6e} W — the anchor that "
        f"says this is the same box, the same material and the same solve the "
        f"whole degree-2 family was measured on"
    )


@complex_only
@pytest.mark.integration
def test_the_step1_10mhz_row_reproduces_its_recorded_reading(discriminator_rows):
    """Negative control for the rescope (§7 step 1′): the 10 MHz row is unmoved.

    Step 1's fixture is kept in the table as a *recorded* row — its precondition
    is no longer asserted, because 1.952350e-02 against a 1e-2 band is a known
    reading and re-asserting it gates nothing but a deliberate red.  What is
    asserted is that this run reproduces it: the degree-1 ratio and the
    in-between cross-order move 5.156e+01× at rtol 1e-3.  If either has drifted,
    the 1 MHz row is not step 1's fixture rescoped and the verdict below is not
    comparable with the recorded coil / smoke / sphere family.
    """
    record = discriminator_rows["loop"][LOOP_RECORD_FREQUENCY_HZ]
    ratio = record[1]["w_e"] / record[1]["w_m"]
    move = _ratio_move(record)

    assert np.isclose(ratio, STEP1_RECORD_DEGREE1_RATIO, rtol=STEP1_RECORD_RTOL), (
        f"the {LOOP_RECORD_FREQUENCY_HZ / 1e6:.0f} MHz row reads degree-1 "
        f"W_e/W_m = {ratio:.6e} against step 1's recorded "
        f"{STEP1_RECORD_DEGREE1_RATIO:.6e} — the fixture moved since "
        f"2026-08-30, so the rescope is not measuring the same thing"
    )
    assert np.isclose(move, STEP1_RECORD_MOVE, rtol=STEP1_RECORD_RTOL), (
        f"the {LOOP_RECORD_FREQUENCY_HZ / 1e6:.0f} MHz row moved {move:.4e}x "
        f"across order against step 1's recorded {STEP1_RECORD_MOVE:.4e}x"
    )


@complex_only
@pytest.mark.integration
def test_the_magnetically_dominated_compatible_drive_discriminates(
    discriminator_rows,
):
    """The reading: does a compatible drive with ``W_m ≫ W_e`` explode too?

    ``≥ 1e3×`` ⇒ **CLASS** — the ungauged second-order gradient space fills on
    any such fixture, the coil's feed is not special, and the next chunk is a
    gauged / tree-cotree / ``H¹``-augmented degree-2 formulation.  ``≤ 10×`` ⇒
    **FEED** — the coil's port feed is the injector and the next chunk is the
    feed model.  Whichever band the run lands in is *asserted*, so a later
    change that quietly moves second-order gradient behaviour shows up on a
    1 405-cell fixture instead of a 62 GiB one.  Only an in-between reading is
    left ungated: §7 says record it, invent no band around it.
    """
    rows = discriminator_rows["loop"][LOOP_FREQUENCY_HZ]
    loop_move = _ratio_move(rows)
    verdict = _verdict(loop_move)
    one = rows[1]
    two = rows[2]

    if verdict.startswith("CLASS"):
        assert loop_move >= CLASS_RATIO_FACTOR, (
            f"the magnetically-dominated compatible drive moved "
            f"{loop_move:.3e}x in W_e/W_m across order "
            f"({one['w_e'] / one['w_m']:.6e} -> {two['w_e'] / two['w_m']:.6e}), "
            f"under the pre-registered {CLASS_RATIO_FACTOR:.0e} that made this "
            f"reading CLASS"
        )
    elif verdict.startswith("FEED"):
        assert loop_move <= FEED_RATIO_FACTOR, (
            f"the magnetically-dominated compatible drive moved "
            f"{loop_move:.3e}x in W_e/W_m across order "
            f"({one['w_e'] / one['w_m']:.6e} -> {two['w_e'] / two['w_m']:.6e}), "
            f"outside the pre-registered {FEED_RATIO_FACTOR:.0f}x that made "
            f"this reading FEED"
        )
        assert loop_move < CLASS_RATIO_FACTOR
    else:
        pytest.skip(
            f"`TH-13` step 1 read {verdict}: the loop fixture moved "
            f"{loop_move:.3e}x across order, between the pre-registered "
            f"{FEED_RATIO_FACTOR:.0f}x and {CLASS_RATIO_FACTOR:.0e}. Per §7 the "
            f"reading is recorded in the plan and in known-issues and no band "
            f"is fabricated around it here"
        )
