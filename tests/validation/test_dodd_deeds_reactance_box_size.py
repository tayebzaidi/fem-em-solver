"""`MAT-6` step 4: does the projection *improve* ΔX, or just reshuffle box error?

Step 3 measured the reactance ratio move ``ΔX/ΔX_exact`` 0.8123 (pinned drive)
→ 0.9200 (projected drive) at W = 0.15 while ΔR moved 5e-5 relative.  That
fixture cannot attribute the move: it still has 5.57% of box motion left in ΔX
(measured W = 0.15 → 0.20, step 2a probe) and the filamentary reference spreads
30% over ``h ± r_wire``, both larger than the 13% shift.

The discriminator PROJECT_PLAN §7 asks for is a *larger box*.  If the
projection really removes spurious discrete gradient content from the reactive
part (`PORT-1` step 2e's ``W_e^spur`` mechanism), projected ΔX sits closer to
Dodd-Deeds than the pinned drive at **every** box size.  If instead the two
paths converge to the same ΔX as W grows, the 0.9200 was reshuffled truncation
error and the step-3 finding dies.

Everything except ``box_half_width`` is imported, not restated — the geometry,
the current density, the tags, both solve routines and the pinned reaction
integral come from ``test_dodd_deeds_impedance.py`` (pinned) and
``test_dodd_deeds_projected_drive.py`` (projected), so the only difference
between the numbers here and the recorded W = 0.15 numbers is the box.

**Gates are step 2b's, applied unchanged**: ΔR under a 5% hard ceiling; ΔX on
sign and order of magnitude only.  ΔX is *reported*, never gated to whatever it
returns — §7 forbids a tightened ΔX band in this slot, because the fixture is
what is under investigation.

Cost (measured, ``20260805T200132Z_MAT-6-step4-probe.log``): the W = 0.25 mesh
is **300 591 cells / 353 201 dofs**, 18 s to mesh and 81 s per projected solve
at ``-n 4``.  Four solves therefore do not fit one standard command, so the two
drives are separated by ``-k``: each command builds the mesh once and solves the
loaded/free pair for one drive.  Heavy tier, ``-n 2`` (CI width — the reaction
integral and the current are allreduced, and ``-n 2`` is the only width where a
missing reduction shows).

Run (complex build only, one drive per command)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_dodd_deeds_reactance_box_size.py -k projected -v -s'
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

# W = 0.25 m against the landed fixture's W = 0.15.  Box *volume* grows 4.63x;
# the measured cell count grows only 2.17x (138 619 → 300 591) because the
# added volume is all far-field at resolution_far = 0.025.
BOX_HALF_WIDTH_LARGE = 0.25

# The W = 0.15 numbers this step compares against, both on record and both
# re-derived from their own logs rather than recomputed here:
#   pinned    ΔR = +3.276882e-01 Ω (1.58%),   ΔX ratio 0.8123
#     `20260731T110515Z_MAT-6-step2b-gate-numbers.log`
#   projected ΔR = +3.2770406e-01 Ω (1.5834%), ΔX ratio 0.9200
#     `20260804T213600Z_MAT-6-step3-gate-final.log`
DX_RATIO_W015_PINNED = 0.8123
DX_RATIO_W015_PROJECTED = 0.9200


def _mesh_large_box(comm):
    """The step-2b fixture with one parameter moved: ``box_half_width``."""
    comm.Barrier()
    t0 = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=BOX_HALF_WIDTH_LARGE,
        resolution_wire=0.002,
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

    ΔZ goes as 1/I², so the meshed torus's volume deficit against
    ``π r² · 2π a`` must not be charged to the field solve.
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
    if comm.rank == 0:
        print(
            f"\n[MAT-6 step 4 | {label} | W = {BOX_HALF_WIDTH_LARGE} m] "
            f"{ncells} cells, mesh {t_mesh:.1f} s, solves "
            + " + ".join(f"{t:.1f} s" for t in t_solves)
            + f" at -n {comm.size}"
            f"\n[MAT-6 step 4 | {label}] I = {current:.6f} A"
            f"\n[MAT-6 step 4 | {label}] FEM   dZ = {dz.real:+.7e} + "
            f"j({dz.imag:+.7e}) Ohm"
            f"\n[MAT-6 step 4 | {label}] exact dZ = {dz_ref.real:+.7e} + "
            f"j({dz_ref.imag:+.7e}) Ohm"
            f"\n[MAT-6 step 4 | {label}] dR rel. error {rel_r:.4%}; "
            f"dX ratio {ratio_x:.4f} (W = 0.15 was "
            f"{DX_RATIO_W015_PROJECTED if label == 'projected' else DX_RATIO_W015_PINNED})",
            flush=True,
        )
    return dict(
        dz=dz, dz_ref=dz_ref, current=current, ncells=ncells, ratio_x=ratio_x
    )


@pytest.fixture(scope="module")
def projected_large_box():
    """Loaded/free pair on the **production default** (projected) drive."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, t_mesh, ncells = _mesh_large_box(comm)

    e_loaded, j_prime_loaded, t_loaded = _solve_projected(
        msh, cell_tags, FEM_SIGMA_SLAB, comm
    )
    e_free, _, t_free = _solve_projected(msh, cell_tags, 0.0, comm)

    # I' from the drive actually used, and ΔZ over the WHOLE domain: J' has
    # support everywhere, unlike J.  Both exactly as step 3 computes them.
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
def pinned_large_box():
    """Loaded/free pair on the **pinned** (``project_source=False``) drive.

    The pins in ``test_dodd_deeds_impedance.py`` are the provenance of the
    landed 1.58% and are never flipped; this fixture calls that module's
    ``_solve_loop``, which carries them.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags, t_mesh, ncells = _mesh_large_box(comm)

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
# projected drive, W = 0.25
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_projected_resistance_change_matches_dodd_deeds_on_the_large_box(
    projected_large_box,
):
    """ΔR keeps step 2b's 5% ceiling on the larger box.

    ΔR was already converged in box size at W = 0.15 (0.268% between W = 0.15
    and W = 0.20), so this is the control on the whole comparison: if ΔR moved
    materially here, the mesh — not the drive — would be what changed, and the
    ΔX reading below would mean nothing.  The ceiling is inherited, never widened.
    """
    dz, dz_ref = projected_large_box["dz"], projected_large_box["dz_ref"]
    rel = abs(dz.real / dz_ref.real - 1.0)
    print(f"\n  ΔR: FEM {dz.real:.7e} Ω vs exact {dz_ref.real:.7e} Ω → {rel:.4%}")
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert rel < 0.05, f"projected ΔR off the closed form by {rel:.2%}"


@complex_only
@pytest.mark.integration
def test_projected_reactance_change_has_the_right_sign_and_magnitude_on_the_large_box(
    projected_large_box,
):
    """ΔX on the projected drive: sign and order of magnitude, step 2b's gate.

    The ratio itself is the *reported* result of step 4 and is deliberately not
    gated to its measured value — the box convergence of ΔX is the open
    question, so a band sized to this run would assert the thing under test.
    """
    dz, dz_ref = projected_large_box["dz"], projected_large_box["dz_ref"]
    ratio = dz.imag / dz_ref.imag
    print(
        f"\n  ΔX: FEM {dz.imag:.7e} Ω vs exact {dz_ref.imag:.7e} Ω → ratio {ratio:.4f}"
        f"  (W = 0.15 projected: {DX_RATIO_W015_PROJECTED})"
    )
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
    assert 0.5 < ratio < 2.0, f"projected ΔX is not within an order of magnitude: {ratio}"


# ---------------------------------------------------------------------------
# pinned drive, W = 0.25
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_pinned_resistance_change_matches_dodd_deeds_on_the_large_box(
    pinned_large_box,
):
    """The same ΔR control for the pinned drive — step 2b's gate, larger box."""
    dz, dz_ref = pinned_large_box["dz"], pinned_large_box["dz_ref"]
    rel = abs(dz.real / dz_ref.real - 1.0)
    print(f"\n  ΔR: FEM {dz.real:.7e} Ω vs exact {dz_ref.real:.7e} Ω → {rel:.4%}")
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert rel < 0.05, f"pinned ΔR off the closed form by {rel:.2%}"


@complex_only
@pytest.mark.integration
def test_pinned_reactance_change_has_the_right_sign_and_magnitude_on_the_large_box(
    pinned_large_box,
):
    """ΔX on the pinned drive: the other half of step 4's four-number result."""
    dz, dz_ref = pinned_large_box["dz"], pinned_large_box["dz_ref"]
    ratio = dz.imag / dz_ref.imag
    print(
        f"\n  ΔX: FEM {dz.imag:.7e} Ω vs exact {dz_ref.imag:.7e} Ω → ratio {ratio:.4f}"
        f"  (W = 0.15 pinned: {DX_RATIO_W015_PINNED})"
    )
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
    assert 0.5 < ratio < 2.0, f"pinned ΔX is not within an order of magnitude: {ratio}"
