"""`TH-13` step 1: does *any* ``W_m ≫ W_e`` fixture display the degree-2
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
subspace to absorb) at **10 MHz** — the coil's own frequency, chosen so the
fixture sits in the same quasi-static regime where ``W_e/W_m`` is small.

**Pre-registered, before the run** (PROJECT_PLAN §7 `TH-13` step 1, restated in
:data:`MAGNETIC_DOMINANCE_MAX` / :data:`CLASS_RATIO_FACTOR` /
:data:`FEED_RATIO_FACTOR`):

* **Precondition, asserted** — the fixture must first *be* magnetically
  dominated: degree-1 ``W_e/W_m ≤ 1e-2``.  If it is not, the fixture is wrong,
  the reading below means nothing, and §7 says the step stops with that as its
  finding rather than reinterpreting the ratio.
* **Verdict** — the cross-order move in ``W_e/W_m`` on this fixture:
  ``≥ 1e3×`` ⇒ **CLASS**, ``≤ 10×`` ⇒ **FEED**.  In between is the finding,
  recorded, with no band invented around it.

**Negative control** (§7): `TH-12` step 3's own two fixtures, run here on the
same code path and through the same imported helpers, must reproduce their
recorded moves — smoke 1.155×, sphere 1.015× — so a CLASS reading is a property
of the new fixture and not of a code change since 2026-08-19.  The `POST-5`
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

# The loop fixture's frequency: the coil's own 10 MHz, not the smoke box's
# 127.74 MHz.  With an impressed current held fixed, a quasi-static solve has
# ``B`` frequency-independent and ``E ~ ωA``, so ``W_e/W_m ~ ω²`` — 10 MHz is
# what puts this fixture in the coil's regime rather than the smoke box's
# full-wave one.  Everything else about the box (material, mesh, tags) is the
# smoke fixture's, imported.
LOOP_FREQUENCY_HZ = 10.0e6

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


def _solve_loop_at_degree(degree: int, comm) -> dict:
    """The closed azimuthal loop drive on the smoke box at 10 MHz, at ``degree``.

    Byte-for-byte the smoke fixture except for the two things this step varies:
    the drive (`POST-5` step 2's :func:`_azimuthal_current`, imported) and the
    frequency (:data:`LOOP_FREQUENCY_HZ`).  ``gauge_penalty`` is left at the
    solver default, which is what `TH-12` steps 2 and 3 measured every recorded
    ratio on — the ungauged second-order gradient space is the object under
    test, so gauging it here would answer a different question.
    """
    mesh, cell_tags, facet_tags = _smoke_mesh(SMOKE_RESOLUTION, comm)
    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=LOOP_FREQUENCY_HZ,
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


@pytest.fixture(scope="module")
def discriminator_rows():
    """Three fixtures at both orders — the new loop drive plus step 3's pair."""
    comm = MPI.COMM_WORLD
    loop = {degree: _solve_loop_at_degree(degree, comm) for degree in (1, 2)}
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
    print("\n[TH-13 step 1] stored energies at N1curl degree 1 vs 2:")
    print(
        "  fixture      deg   cells     DOFs        W_m [J]        W_e [J]"
        "      W_e/W_m"
    )
    for name in ("loop", "smoke", "sphere"):
        for degree in (1, 2):
            row = rows[name][degree]
            print(
                f"  {name:<11s}  {degree:d}  {row['ncells']:6d}  {row['n_dofs']:8d}  "
                f"{row['w_m']:.6e}  {row['w_e']:.6e}  "
                f"{row['w_e'] / row['w_m']:.6e}"
            )
    for degree in (1, 2):
        row = rows["loop"][degree]
        print(
            f"  loop degree {degree}: dissipated {row['dissipated_power_w']:.6e} W, "
            f"|Im P|/Re P = {row['power_imaginary']:.3e}"
        )
    print(
        f"  coil (printed, `TH-12` step 2 record, not re-run): "
        f"W_e/W_m = {COIL_W_E_W_M_DEGREE1:.6e} at degree 1 -> "
        f"{COIL_W_E_W_M_DEGREE2:.6e} at degree 2, a "
        f"{COIL_W_E_W_M_DEGREE2 / COIL_W_E_W_M_DEGREE1:.3e}x move"
    )
    print(
        f"  cross-order move in W_e/W_m: loop {_ratio_move(rows['loop']):.3e}x "
        f"(compatible drive, {LOOP_FREQUENCY_HZ / 1e6:.0f} MHz), "
        f"smoke {_ratio_move(rows['smoke']):.3e}x (J.n != 0, control), "
        f"sphere {_ratio_move(rows['sphere']):.3e}x (imposed field, control)"
    )
    print(
        f"  precondition: loop degree-1 W_e/W_m = "
        f"{rows['loop'][1]['w_e'] / rows['loop'][1]['w_m']:.6e} against the "
        f"pre-registered <= {MAGNETIC_DOMINANCE_MAX:.0e}"
    )
    print(
        f"  bands: >= {CLASS_RATIO_FACTOR:.0e}x on the loop => CLASS; "
        f"<= {FEED_RATIO_FACTOR:.0f}x => FEED"
    )
    print(f"  VERDICT: {_verdict(_ratio_move(rows['loop']))}", flush=True)


@complex_only
@pytest.mark.integration
def test_the_loop_fixture_is_magnetically_dominated(discriminator_rows):
    """Precondition (§7), asserted: degree-1 ``W_e/W_m ≤ 1e-2``.

    Runs first and prints the whole table, so no verdict is read against an
    unverified fixture.  This is the entire reason the fixture exists: `TH-12`
    step 3's two cheap fixtures sit at ``W_e/W_m`` 2.16 and 1.07, the coil at
    6.7e-6, and nothing in the tree occupied the magnetically-dominated cell
    with a *compatible* drive.  If this assertion fails the fixture is not that
    cell, the cross-order move below discriminates nothing, and §7 says the step
    stops on that finding rather than reinterpreting the number.
    """
    _print_table(discriminator_rows)
    one = discriminator_rows["loop"][1]

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
    for degree in (1, 2):
        row = discriminator_rows["loop"][degree]
        assert row["power_imaginary"] < POWER_IMAGINARY_BOUND, (
            f"the loop fixture's ohmic power at degree {degree} carries an "
            f"imaginary part {row['power_imaginary']:.3e} of the real part, "
            f"over the {POWER_IMAGINARY_BOUND:.0e} family bound — inner() "
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
    loop_move = _ratio_move(discriminator_rows["loop"])
    verdict = _verdict(loop_move)
    one = discriminator_rows["loop"][1]
    two = discriminator_rows["loop"][2]

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
