"""`MAT-6` step 5: does ΔX move under *wire* refinement at fixed box?

Step 4 left the projected-drive ΔX ratio at 0.9849 (W = 0.25) with two residual
terms entangled: box truncation (still moving ~+0.06 per 0.10 m of W) and the
filamentary reference's own ~30% spread over ``h ± r_wire``, which no box can
remove.  This module turns the *other* knob step 2b named — mesh resolution on
the wire, at **fixed** ``W = 0.15`` — which moves only the wire-discretisation
term.  A ΔX ratio that moves under wire refinement at fixed box is finite-wire
discretisation error; a ratio that does not move says the residual is
reference ambiguity plus box tail, and that is equally the finding (§7).

**Nothing about the fixture moves except ``resolution_wire``.**  In particular
``FEM_WIRE_RADIUS`` stays 0.0025 m, so ``_solve_loop``, ``_solve_projected``
and ``_reaction_impedance`` — all of which derive the current density from it —
are imported and used verbatim, exactly as step 4 imported them for the box
sweep.  ``resolution_near``/``resolution_far`` stay put too: refining the far
field is what makes the cell count explode, and it would also stop being a
wire-only knob.

Measured ladder (``20260807T200206Z_MAT-6-step5-probe.log``), W = 0.15,
``r_wire = 0.0025`` m:

===================  =========  ==========
``resolution_wire``  r_wire/h   cells
===================  =========  ==========
0.002 (landed)       1.25       138 619
0.001 (**here**)     2.50       366 207
0.0005               5.00       1 458 561  — OOM-killed at ``-n 4``
===================  =========  ==========

So step 2b's literal ``h/r_wire >= 16`` target (``h <= 1.5625e-4`` m) is **not
reachable on this machine**: the cell count is already 1.46 M two doublings
short of it, and that mesh could not be held in memory at ``-n 4``.  0.001 is
the finest affordable rung, and §5.1 forbids buying the rest with a longer
timeout.  The refinement measured here is therefore a 2× one (r_wire/h
1.25 → 2.50, 2.64× the cells), which bounds the wire-discretisation term
rather than exhausting it.

**Gates are step 2b's, applied unchanged**: ΔR under a 5% hard ceiling; ΔX on
sign and order of magnitude only.  The ΔX ratios are *reported*, never gated to
whatever they return — §7 forbids a tightened ΔX band in this slot for the same
reason step 4 did: the convergence of ΔX is the thing under test, so a band
sized to this run would assert its own conclusion.

Run (complex build only, one drive per command)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_dodd_deeds_reactance_wire_resolution.py \\
       -k projected -v -s'
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.dodd_deeds import coil_impedance_change
from tests.complex_mode import complex_only
from tests.validation.test_dodd_deeds_impedance import (
    FEM_BOX_HALF_WIDTH,
    FEM_CURRENT_A,
    FEM_FREQUENCY_HZ,
    FEM_LIFTOFF,
    FEM_LOOP_RADIUS,
    FEM_SIGMA_SLAB,
    FEM_WIRE_RADIUS,
    WIRE_TAG,
    _azimuthal_current_density,
    _reaction_impedance,
    _solve_loop,
)
from tests.validation.test_dodd_deeds_projected_drive import (
    _reduced_real,
    _solve_projected,
)

# The one parameter that moves.  0.002 is the landed rung; 0.0005 does not fit
# in memory (probe log above), so this is the finest affordable refinement.
RESOLUTION_WIRE_FINE = 0.001

# The W = 0.15 numbers this step refines against, both on record and both read
# off their own logs rather than recomputed here:
#   pinned    ΔR = +3.276882e-01 Ω (1.58%),   ΔX ratio 0.8123
#     `20260731T110515Z_MAT-6-step2b-gate-numbers.log`
#   projected ΔR = +3.2770406e-01 Ω (1.5834%), ΔX ratio 0.9200
#     `20260804T213600Z_MAT-6-step3-gate-final.log`
DX_RATIO_COARSE_PINNED = 0.8123
DX_RATIO_COARSE_PROJECTED = 0.9200

# Step 4's own W-series measured ΔR moving < 0.01 percentage-point across a
# 2.17× change in cell count.  That is the reality floor: a refinement effect
# smaller than it is not distinguishable from mesh noise.
DR_WOBBLE_FLOOR_PP = 0.01

# The coarse-wire meshed current, on record at both box sizes:
# 0.919690 A at W = 0.15 (`20260731T110515Z_MAT-6-step2b-gate-numbers.log`,
# "meshed loop current 0.919690 A") and the same 0.919690 A at W = 0.25
# (step 4) — the box does not touch it, only the wire discretisation does.
# Against FEM_CURRENT_A = 1.0 that is an 8.031% volume deficit on the faceted
# torus.
CURRENT_COARSE_WIRE_A = 0.919690


def _mesh_fine_wire(comm):
    """The step-2b fixture with one parameter moved: ``resolution_wire``."""
    comm.Barrier()
    t0 = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=RESOLUTION_WIRE_FINE,
        resolution_near=0.005,
        resolution_far=0.025,
        near_half_width=0.06,
        near_depth=0.05,
        near_height=0.03,
        comm=comm,
    )
    comm.Barrier()
    t_mesh = time.perf_counter() - t0
    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    return msh, cell_tags, float(t_mesh), int(ncells)


def _meshed_current(msh, cell_tags, comm) -> float:
    """``I``: the current the *discretised* torus carries, as step 2b computes it.

    This is the number the refinement is expected to move most directly — a
    finer wire surface recovers more of the ``π r² · 2π a`` volume the coarse
    torus loses — and ΔZ goes as 1/I², so it must not be charged to the field.
    """
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    v_wire = _reduced_real(
        fem.Constant(msh, np.array(1.0, dtype=np.complex128).item()) * dx_wire, comm
    )
    return j_magnitude * v_wire / (2.0 * np.pi * FEM_LOOP_RADIUS)


def _report(label, dz, dz_ref, current, ncells, t_mesh, t_solves, comm):
    rel_r = abs(dz.real / dz_ref.real - 1.0)
    ratio_x = dz.imag / dz_ref.imag
    coarse = (
        DX_RATIO_COARSE_PROJECTED if label == "projected" else DX_RATIO_COARSE_PINNED
    )
    if comm.rank == 0:
        print(
            f"\n[MAT-6 step 5 | {label} | resolution_wire = {RESOLUTION_WIRE_FINE} m] "
            f"{ncells} cells, mesh {t_mesh:.1f} s, solves "
            + " + ".join(f"{t:.1f} s" for t in t_solves)
            + f" at -n {comm.size}"
            f"\n[MAT-6 step 5 | {label}] I = {current:.6f} A"
            f"\n[MAT-6 step 5 | {label}] FEM   dZ = {dz.real:+.7e} + "
            f"j({dz.imag:+.7e}) Ohm"
            f"\n[MAT-6 step 5 | {label}] exact dZ = {dz_ref.real:+.7e} + "
            f"j({dz_ref.imag:+.7e}) Ohm"
            f"\n[MAT-6 step 5 | {label}] dR rel. error {rel_r:.4%}; "
            f"dX ratio {ratio_x:.4f} (coarse wire was {coarse}; "
            f"moved {ratio_x - coarse:+.4f})",
            flush=True,
        )
    return dict(
        dz=dz, dz_ref=dz_ref, current=current, ncells=ncells, ratio_x=ratio_x
    )


@pytest.fixture(scope="module")
def projected_fine_wire():
    """Loaded/free pair on the **production default** (projected) drive."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, t_mesh, ncells = _mesh_fine_wire(comm)

    e_loaded, j_prime_loaded, t_loaded = _solve_projected(
        msh, cell_tags, FEM_SIGMA_SLAB, comm
    )
    e_free, _, t_free = _solve_projected(msh, cell_tags, 0.0, comm)

    # I' from the drive actually used, and ΔZ over the WHOLE domain: J' has
    # support everywhere, unlike J.  Both exactly as steps 3 and 4 compute them.
    x = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_current_density(1.0)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    current = _reduced_real(ufl.inner(j_prime_loaded, phi_hat) * dx_wire, comm) / (
        2.0 * np.pi * FEM_LOOP_RADIUS
    )
    # assemble_scalar is rank-local; reduce before forming ΔZ.  J' is real, so
    # inner()'s conjugation of the second argument is a no-op — reaction, not power.
    reaction = comm.allreduce(
        fem.assemble_scalar(
            fem.form(ufl.inner(e_loaded - e_free, j_prime_loaded) * ufl.dx)
        ),
        op=MPI.SUM,
    )
    dz = complex(-reaction / current**2)
    dz_ref = coil_impedance_change(
        FEM_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )
    return _report(
        "projected", dz, dz_ref, current, ncells, t_mesh, (t_loaded, t_free), comm
    )


@pytest.fixture(scope="module")
def pinned_fine_wire():
    """Loaded/free pair on the **pinned** (``project_source=False``) drive.

    The pins in ``test_dodd_deeds_impedance.py`` are the provenance of the
    landed 1.58% and are never flipped; this fixture calls that module's
    ``_solve_loop``, which carries them.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags, t_mesh, ncells = _mesh_fine_wire(comm)

    e_loaded, t_loaded = _solve_loop(msh, cell_tags, FEM_SIGMA_SLAB, comm)
    e_free, t_free = _solve_loop(msh, cell_tags, 0.0, comm)

    current = _meshed_current(msh, cell_tags, comm)
    dz = _reaction_impedance(msh, cell_tags, e_loaded, e_free, current, comm)
    dz_ref = coil_impedance_change(
        FEM_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )
    return _report(
        "pinned", dz, dz_ref, current, ncells, t_mesh, (t_loaded, t_free), comm
    )


# ---------------------------------------------------------------------------
# the mesh itself: the refinement has to be real, and wire-local
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_refinement_landed_on_the_wire_and_not_on_the_far_field(
    projected_fine_wire,
):
    """The knob did what it says: 2.64× cells, and the count is the probe's.

    A wire-only refinement must reproduce the probe's measured cell count
    exactly — the mesh is deterministic and nothing else moved — and it must be
    a large multiple of the landed 138 619.  If ``resolution_far`` had been
    disturbed the count would be far larger, and the comparison against the
    coarse-wire ΔX would no longer isolate the wire.
    """
    ncells = projected_fine_wire["ncells"]
    growth = ncells / 138_619
    print(
        f"\n  cells: {ncells} at resolution_wire = {RESOLUTION_WIRE_FINE} m "
        f"vs 138619 landed → {growth:.2f}×"
    )
    assert ncells == 366_207, (
        "the mesh is deterministic and only resolution_wire moved, so the cell "
        f"count must be the probe's 366207; got {ncells}"
    )
    assert 2.0 < growth < 3.5, f"refinement growth {growth:.2f}× is not wire-local"


@complex_only
@pytest.mark.integration
def test_the_meshed_torus_recovers_volume_under_wire_refinement(pinned_fine_wire):
    """The discretised current closes on the analytic torus as the wire refines.

    ``I = j · vol(meshed torus) / 2πa`` and the exact torus carries
    ``FEM_CURRENT_A`` by construction, so ``I/I_exact`` is a pure measure of the
    faceted torus's volume deficit — 8.031% at the coarse rung, on record from
    step 2b and unmoved by step 4's box change.  A finer wire surface must
    shrink it: this is the one quantity the refinement is *guaranteed* to move,
    and it is what makes a null ΔX result interpretable rather than vacuous.

    The floor is a 1.5× shrink.  Facet chord error on a surface of revolution
    is O(h²), so halving ``resolution_wire`` predicts ~4×; 1.5× is far enough
    below that to gate the mechanism without asserting the measured value, and
    far enough above step 4's < 0.01 pp mesh-noise floor to be real.
    """
    current = pinned_fine_wire["current"]
    deficit = 1.0 - current / FEM_CURRENT_A
    deficit_coarse = 1.0 - CURRENT_COARSE_WIRE_A / FEM_CURRENT_A
    shrink = deficit_coarse / deficit
    print(
        f"\n  I = {current:.6f} A vs exact {FEM_CURRENT_A} A → volume deficit "
        f"{deficit:.4%} (coarse wire {deficit_coarse:.4%}) → shrink {shrink:.2f}×"
        f"  [O(h²) predicts ~4×]"
    )
    assert deficit > 0.0, (
        "an inscribed faceted torus cannot exceed the analytic volume, got "
        f"deficit {deficit:.4%}"
    )
    assert shrink > 1.5, (
        f"a 2× wire refinement must shrink the {deficit_coarse:.4%} volume "
        f"deficit by more than 1.5×; got {deficit:.4%}, i.e. {shrink:.2f}×"
    )


# ---------------------------------------------------------------------------
# projected drive, fine wire
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_projected_resistance_change_matches_dodd_deeds_on_the_fine_wire(
    projected_fine_wire,
):
    """ΔR keeps step 2b's 5% ceiling under wire refinement.

    ΔR is the control on the whole comparison, as in step 4: it was converged in
    box size and is dominated by the slab's skin layer, not the wire surface, so
    if it moved materially here the mesh — not the wire discretisation — would
    be what changed and the ΔX reading below would mean nothing.  The ceiling is
    inherited, never widened.
    """
    dz, dz_ref = projected_fine_wire["dz"], projected_fine_wire["dz_ref"]
    rel = abs(dz.real / dz_ref.real - 1.0)
    print(f"\n  ΔR: FEM {dz.real:.7e} Ω vs exact {dz_ref.real:.7e} Ω → {rel:.4%}")
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert rel < 0.05, f"projected ΔR off the closed form by {rel:.2%}"


@complex_only
@pytest.mark.integration
def test_projected_reactance_change_has_the_right_sign_and_magnitude_on_the_fine_wire(
    projected_fine_wire,
):
    """ΔX on the projected drive: sign and order of magnitude, step 2b's gate.

    The ratio and its movement against the coarse-wire 0.9200 are the *reported*
    result of step 5 and are deliberately not gated to their measured values —
    whether ΔX converges is the open question, so a band sized to this run would
    assert the thing under test.
    """
    dz, dz_ref = projected_fine_wire["dz"], projected_fine_wire["dz_ref"]
    ratio = dz.imag / dz_ref.imag
    print(
        f"\n  ΔX: FEM {dz.imag:.7e} Ω vs exact {dz_ref.imag:.7e} Ω → ratio {ratio:.4f}"
        f"  (coarse wire projected: {DX_RATIO_COARSE_PROJECTED}; "
        f"moved {ratio - DX_RATIO_COARSE_PROJECTED:+.4f})"
    )
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
    assert 0.5 < ratio < 2.0, (
        f"projected ΔX is not within an order of magnitude: {ratio}"
    )


# ---------------------------------------------------------------------------
# pinned drive, fine wire
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_pinned_resistance_change_matches_dodd_deeds_on_the_fine_wire(
    pinned_fine_wire,
):
    """The same ΔR control for the pinned drive — step 2b's gate, finer wire."""
    dz, dz_ref = pinned_fine_wire["dz"], pinned_fine_wire["dz_ref"]
    rel = abs(dz.real / dz_ref.real - 1.0)
    print(f"\n  ΔR: FEM {dz.real:.7e} Ω vs exact {dz_ref.real:.7e} Ω → {rel:.4%}")
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert rel < 0.05, f"pinned ΔR off the closed form by {rel:.2%}"


@complex_only
@pytest.mark.integration
def test_pinned_reactance_change_has_the_right_sign_and_magnitude_on_the_fine_wire(
    pinned_fine_wire,
):
    """ΔX on the pinned drive: the other half of step 5's reported pair."""
    dz, dz_ref = pinned_fine_wire["dz"], pinned_fine_wire["dz_ref"]
    ratio = dz.imag / dz_ref.imag
    print(
        f"\n  ΔX: FEM {dz.imag:.7e} Ω vs exact {dz_ref.imag:.7e} Ω → ratio {ratio:.4f}"
        f"  (coarse wire pinned: {DX_RATIO_COARSE_PINNED}; "
        f"moved {ratio - DX_RATIO_COARSE_PINNED:+.4f})"
    )
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
    assert 0.5 < ratio < 2.0, f"pinned ΔX is not within an order of magnitude: {ratio}"
