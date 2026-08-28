"""`TH-12` step 2: the loaded coil at **degree-2 N1curl** — a reading, no gate.

Step 1 gated degree 2 on the lossy sphere and it passed with room (0.1405%
interior relL2 on 5 866 cells against the degree-1 fine-rung record 3.643% at
17 670, cost sublinear in DOFs on both axes).  This step asks the question the
`TH-11` lineage actually needs answered: on the **coil**, does second order buy
the h → 0 limit that degree-1 refinement cannot reach on this box?

`TH-11` step 5 closed as a measured negative — 2 807 309 cells OOM at every
legal rank count and even the shrunk 994 258-cell rung pegs
``memory.max`` = 64.00 GiB, so no affordable third degree-1 rung exists.  Step 4
left a Richardson **bracket** for the 10 MHz ΔR deviation at h → 0,
``[−2.1492%, −0.9050%]`` (imported from
:mod:`tests.validation.test_coil_loading_larmor_third_rung`, never restated),
extrapolated from two rungs at assumed rates p = 1 and p = 2.  If degree 2 on
the *coarse* 138 490-cell rung (0.7.2: 138 619) lands inside that bracket, a
degree-2 rung is the
live replacement for the memory-infeasible degree-1 third rung — and that swap
is the review's call, not this module's.

**ΔR is printed, never gated.**  The bracket is Richardson-derived from two
rungs, not a closed form; asserting a band drawn from an extrapolation would
gate the thing under measurement (§7 `TH-12` step 2, and the `TH-11` step-1
trap list).  What *is* gated is the `TH-11` identity family at its unchanged
bounds, on every solve at both orders:

* the complex-power identity ``Im Z = 4ω(W_m − W_e)/I′²`` at 1e-9 — the
  reaction route integrates ``E·J′`` over the whole domain while the energy
  route never sees ``J′``, so a degree-2 assembly that mis-forms either one
  shows up here and a wrong ``I′`` cancels;
* the σ = 0 control: the free solve's ``½∫σ|E|²`` is ``+0.0`` **exactly**;
* the drive control at 1e-24 — loaded and free must use the identical ``J′``;
* the mesh is the 138 490-cell `MAT-6` step-3 baseline (0.7.2: 138 619),
  exactly.

**Negative control** (§7, and step 1's pattern): degree 1 on this fixture, *in
the same process, on the same mesh object*, must reproduce its recorded ΔR
deviation **+1.5834%** to the `MAT-6` step-8 run-to-run floor of 0.01 pp.
Without it a degree-2 number cannot distinguish "second order moved the answer"
from "this fixture is no longer the one the record was measured on".  It runs
first, and the degree-2 solve is only attempted after it passes.

**The mandatory cost probe** (§7: "print DOFs and the MUMPS in-core estimate
before solving; if the estimate exceeds the cgroup cap, stop — that number is
the step's result").  Between the two orders this module prints the degree-2
global DOF count and a memory projection built from the degree-1 solve measured
moments earlier on the same mesh, and **refuses to start the degree-2 solve**
if the projection exceeds the pre-registered fraction of ``memory.max``.  The
rule is registered here, before the run, in :data:`MEMORY_GUARD_FRACTION` and
:data:`MEMORY_GUARD_EXPONENT`; an over-cap projection is a clean negative and
the step's result, exactly as §7 says.

**Memory instrument.**  Summed ``ru_maxrss``, never ``/sys/fs/cgroup/memory.peak``
— the cgroup file is the container's *lifetime* high-water mark, not resettable
from inside a test, and on this box a `TH-11`-scale run has already touched the
cap, so it reads 64 GiB for every later job and measures nothing (step 1's
instrument note).  Both helpers are imported from step 1's module.  Note the
one thing ``ru_maxrss`` cannot do: it is a high-water mark over the whole
process, so the degree-2 reading includes the degree-1 solve that preceded it
in the same interpreter.  It is therefore an *upper bound* on degree 2's own
footprint, and it is reported as one.

Scope: one fixture, 10 MHz, one mesh rung, both orders.  No production element
order is decided here (§7 decision clause — that is the weekly review's, off
these numbers); no recorded degree-1 number moves; no coil-loading or SAR claim
in §2 moves either way.

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 8 python3 -m pytest tests/environment \\
       tests/validation/test_coil_loading_degree2.py -v -s'

``TH12_STEP2_MODE=probe`` stops after the degree-1 control and the cost probe
(the cheap rehearsal: mesh, one solved pair, the DOF count and the projection,
no degree-2 solve).  ``full`` is the default.
"""

from __future__ import annotations

import os
import time

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core.resonance import stored_electric_energy
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.dodd_deeds import coil_impedance_change
from tests.complex_mode import complex_only
from tests.validation.test_coil_loading_larmor_probe import (
    DR_REL_10MHZ,
    IDENTITY_TOLERANCE,
    NCELLS_BASELINE,
    _ohmic_power,
    _skin_depth,
    _solve_projected_at,
    _stored_magnetic_energy,
)
from tests.validation.test_coil_loading_larmor_resolution import (
    NCELLS_FINE,
    RESOLUTION_NEAR_FINE,
    RESOLUTION_NEAR_STEP1,
)
from tests.validation.test_coil_loading_larmor_third_rung import (
    STEP4_BRACKET_10MHZ,
)
from tests.validation.test_coil_loading_richardson_ladder import (
    DR_WOBBLE_FLOOR_PP,
)
from tests.validation.test_dodd_deeds_impedance import (
    FEM_BOX_HALF_WIDTH,
    FEM_FREQUENCY_HZ,
    FEM_LIFTOFF,
    FEM_LOOP_RADIUS,
    FEM_SIGMA_SLAB,
    FEM_WIRE_RADIUS,
    WIRE_TAG,
    _azimuthal_current_density,
)
from tests.validation.test_dodd_deeds_projected_drive import _reduced_real
from tests.validation.test_lossy_sphere_degree2 import (
    _memory_peak_bytes,
    _rss_peak_bytes,
)

# ---------------------------------------------------------------------------
# The cost-probe stop rule, pre-registered (§7: print the estimate before
# solving; stop if it exceeds the cap).
#
# The projection scales the *solve-attributable* part of the degree-1 summed
# RSS — measured on this mesh, minutes earlier, at this rank count — by the DOF
# ratio raised to MEMORY_GUARD_EXPONENT.  The baseline (interpreter, dolfinx,
# the mesh) is measured separately and added back unscaled, because it does not
# grow with the element order.
#
# The exponent is **measured, not assumed**.  The first run of this module used
# a pre-registered guess of 1.5 (`TH-11` step 5c had measured the wall as
# superlinear on this machinery — 0.42 M cells comfortable, 0.99 M pegged at
# memory.max, 2.81 M OOM) and it stopped the degree-2 solve at a projected
# 69.49 GiB while the linear end of the same model read 30.54 GiB: the guess,
# not the machinery, was deciding the step.  The calibration rung
# (`20260818T183730Z_TH-12-step2-calibrate.log`, -n 8) fits it against a real
# second point — the `TH-11` fine rung, 417 914 cells, 486 694 DOFs (2.991x),
# solve-attributable summed RSS 21.78 GiB against the baseline rung's
# 5.41 GiB — giving **p = 1.271**, close to the N^(4/3) a 3D nested-dissection
# factorization is expected to store.  At that exponent degree 2 on the
# baseline rung projects to 47.61 GiB, under the threshold.  A linear
# projection is printed beside it as the optimistic end.
#
# The threshold is 0.80 of memory.max rather than memory.max itself.  §7 says
# "exceeds the cgroup cap"; the 20% headroom is this module's addition and is
# stated because an OOM does not merely fail the test — it kills the container
# and costs the next scheduled slot its preflight (`TH-11` step 5b, twice).
MEMORY_GUARD_EXPONENT = 1.271
MEMORY_GUARD_FRACTION = 0.80

# 10 MHz, the frequency `MAT-6` gated ΔR at and the one step 4's bracket is
# extrapolated at.  Imported from the `MAT-6` module, not restated.
FREQUENCY_HZ = FEM_FREQUENCY_HZ


# The baseline-rung probe this module measured on its first run, cited never
# recomputed (`20260818T183449Z_TH-12-step2-probe.log`, -n 8, 138 619 cells):
# the degree-1 row and the pre-solve baseline the calibration rung is read
# against.  Both are summed `ru_maxrss` in bytes.
PROBE_BASELINE_DOFS = 162_710
PROBE_BASELINE_RSS = 6.63 * 2**30
PROBE_BASELINE_RSS_PRESOLVE = 1.22 * 2**30


def _mode() -> str:
    mode = os.environ.get("TH12_STEP2_MODE", "full").strip().lower()
    if mode not in {"probe", "full", "calibrate"}:
        raise ValueError(
            f"TH12_STEP2_MODE must be 'probe', 'calibrate' or 'full'; got {mode!r}"
        )
    return mode


def _dof_count(msh, degree: int) -> int:
    """Global N1curl DOFs at ``degree`` on ``msh`` — the probe's headline number.

    Built from the mesh rather than reached for through the solver so the probe
    can price degree 2 *without* constructing anything that assembles.
    """
    space = fem.functionspace(msh, ("N1curl", degree))
    index_map = space.dofmap.index_map
    return int(index_map.size_global * space.dofmap.index_map_bs)


def _solve_pair(msh, cell_tags, degree: int, comm) -> dict:
    """The loaded/free pair at ``degree`` on an existing mesh — one row.

    Body is `TH-11` step 1's fixture with the mesh hoisted out and the element
    order freed: the solve helper, the energy helpers, the dissipation helper
    and the reaction form are all step 1's own imports, so the two orders are
    like-for-like by construction and the degree-1 row is comparable to the
    record it must reproduce.
    """
    fields_loaded, j_prime, t_loaded = _solve_projected_at(
        msh, cell_tags, FEM_SIGMA_SLAB, FREQUENCY_HZ, comm, degree=degree
    )
    fields_free, j_prime_free, t_free = _solve_projected_at(
        msh, cell_tags, 0.0, FREQUENCY_HZ, comm, degree=degree
    )
    e_loaded, e_free = fields_loaded.e_complex, fields_free.e_complex

    x = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_current_density(1.0)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    current = _reduced_real(ufl.inner(j_prime, phi_hat) * dx_wire, comm) / (
        2.0 * np.pi * FEM_LOOP_RADIUS
    )

    # ΔZ exactly as `MAT-6` steps 3–8 and `TH-11` steps 1–5 form it: the
    # reaction integral over the WHOLE domain (J′ has support everywhere),
    # reduced before the division.  J′ is real, so inner()'s conjugation of its
    # second argument is a no-op.
    def _reaction_z(e_field):
        reaction = comm.allreduce(
            fem.assemble_scalar(fem.form(ufl.inner(e_field, j_prime) * ufl.dx)),
            op=MPI.SUM,
        )
        return complex(-reaction / current**2)

    z_loaded, z_free = _reaction_z(e_loaded), _reaction_z(e_free)
    dz = z_loaded - z_free
    dz_ref = coil_impedance_change(
        FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )

    omega = 2.0 * np.pi * FREQUENCY_HZ
    identities = {}
    for name, fields_, z_reaction in (
        ("loaded", fields_loaded, z_loaded),
        ("free", fields_free, z_free),
    ):
        w_e = stored_electric_energy(fields_, comm=comm)
        w_m = _stored_magnetic_energy(fields_.e_complex, omega, comm)
        im_energy = 4.0 * omega * (w_m - w_e) / current**2
        identities[name] = dict(
            w_e=w_e,
            w_m=w_m,
            im_energy=im_energy,
            im_reaction=z_reaction.imag,
            residual=abs(z_reaction.imag - im_energy) / abs(z_reaction.imag),
        )

    p_loaded = _ohmic_power(msh, cell_tags, e_loaded, FEM_SIGMA_SLAB, comm)
    p_free = _ohmic_power(msh, cell_tags, e_free, 0.0, comm)

    return dict(
        degree=degree,
        n_dofs=_dof_count(msh, degree),
        current=current,
        dz=dz,
        dz_ref=dz_ref,
        dr_dev=dz.real / dz_ref.real - 1.0,
        dx_ratio=dz.imag / dz_ref.imag,
        dr_dissipation=2.0 * p_loaded / current**2,
        identities=identities,
        p_loaded=p_loaded,
        p_free=p_free,
        t_loaded=t_loaded,
        t_free=t_free,
        drive_mismatch=_reduced_real(
            ufl.inner(j_prime - j_prime_free, j_prime - j_prime_free) * ufl.dx, comm
        )
        / _reduced_real(ufl.inner(j_prime, j_prime) * ufl.dx, comm),
        rss_peak=_rss_peak_bytes(comm),
    )


@pytest.fixture(scope="module")
def degree_rows():
    """One mesh; degree 1 (the control), the cost probe, then degree 2.

    Order is load-bearing.  The control solves first so a degree-2 reading is
    never interpreted against an unpinned fixture, and it doubles as the input
    to the memory projection that decides whether degree 2 is attempted at all.
    """
    if _mode() == "calibrate":
        pytest.skip("calibrate mode measures the memory exponent, not the orders")

    comm = MPI.COMM_WORLD
    comm.Barrier()
    t_mesh = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=0.002,
        resolution_near=RESOLUTION_NEAR_STEP1,
        resolution_far=0.025,
        near_half_width=0.06,
        near_depth=0.05,
        near_height=0.03,
        comm=comm,
    )
    comm.Barrier()
    t_mesh = time.perf_counter() - t_mesh
    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )

    # The pre-solve baseline: interpreter + dolfinx + this mesh.  Subtracted
    # from the degree-1 peak so the projection scales only what the solve costs.
    rss_baseline = _rss_peak_bytes(comm)

    rows = {1: _solve_pair(msh, cell_tags, 1, comm)}

    # ---- the mandatory cost probe, before any degree-2 assembly -----------
    n_dofs_2 = _dof_count(msh, 2)
    dof_ratio = n_dofs_2 / rows[1]["n_dofs"]
    solve_part = max(rows[1]["rss_peak"] - rss_baseline, 0.0)
    projection = {
        "n_dofs_2": n_dofs_2,
        "dof_ratio": dof_ratio,
        "rss_baseline": rss_baseline,
        "solve_part": solve_part,
        "linear": rss_baseline + solve_part * dof_ratio,
        "guard": rss_baseline + solve_part * dof_ratio**MEMORY_GUARD_EXPONENT,
    }
    _, cap = _memory_peak_bytes()
    projection["cap"] = cap
    projection["threshold"] = cap * MEMORY_GUARD_FRACTION
    projection["over_cap"] = bool(projection["guard"] > projection["threshold"])

    if comm.rank == 0:
        print(
            f"\n[TH-12 2 | f = {FREQUENCY_HZ / 1e6:g} MHz | near "
            f"{RESOLUTION_NEAR_STEP1}] {ncells} cells, mesh {t_mesh:.1f} s at "
            f"-n {comm.size}; skin depth "
            f"{_skin_depth(FREQUENCY_HZ, FEM_SIGMA_SLAB) * 1e3:.2f} mm "
            f"({_skin_depth(FREQUENCY_HZ, FEM_SIGMA_SLAB) / RESOLUTION_NEAR_STEP1:.2f}"
            f" cells per delta)"
            f"\n[TH-12 2] COST PROBE (before any degree-2 assembly): "
            f"{rows[1]['n_dofs']} DOFs at degree 1 -> {n_dofs_2} at degree 2 "
            f"({dof_ratio:.2f}x)"
            f"\n[TH-12 2]   degree-1 summed peak RSS "
            f"{rows[1]['rss_peak'] / 2**30:.2f} GiB, of which "
            f"{rss_baseline / 2**30:.2f} GiB is the pre-solve baseline "
            f"(interpreter + mesh, does not scale with order)"
            f"\n[TH-12 2]   projection at exponent {MEMORY_GUARD_EXPONENT} "
            f"(pre-registered): {projection['guard'] / 2**30:.2f} GiB "
            f"(linear end: {projection['linear'] / 2**30:.2f} GiB) against "
            f"{MEMORY_GUARD_FRACTION:.0%} of memory.max = "
            f"{projection['threshold'] / 2**30:.2f} GiB"
            f"\n[TH-12 2]   VERDICT: "
            + (
                "OVER CAP — degree 2 is not attempted; this number is the "
                "step's result (§7 negative-result clause)"
                if projection["over_cap"]
                else "under cap — the degree-2 solve is attempted"
            ),
            flush=True,
        )

    if _mode() == "full" and not projection["over_cap"]:
        rows[2] = _solve_pair(msh, cell_tags, 2, comm)

    if comm.rank == 0:
        _print_reading(rows, projection, ncells)

    return dict(rows=rows, projection=projection, ncells=int(ncells), t_mesh=t_mesh)


def _print_reading(rows: dict, projection: dict, ncells: int) -> None:
    """The step's deliverable: both orders' rows and ΔR beside step 4's bracket."""
    low, high = STEP4_BRACKET_10MHZ
    print(
        f"\n[TH-12 2] READING at {FREQUENCY_HZ / 1e6:g} MHz on {ncells} cells "
        f"(printed, never gated — the bracket is Richardson-derived, not a "
        f"closed form)"
    )
    for degree in sorted(rows):
        row = rows[degree]
        print(
            f"  degree {degree}: {row['n_dofs']:8d} DOFs, "
            f"dR = {row['dz'].real:+.7e} Ohm, dX = {row['dz'].imag:+.7e} Ohm, "
            f"dR deviation {row['dr_dev']:+.4%}, dX ratio {row['dx_ratio']:.4f}, "
            f"solves {row['t_loaded']:.1f} s + {row['t_free']:.1f} s, "
            f"summed peak RSS {row['rss_peak'] / 2**30:.2f} GiB "
            f"(process high-water mark, so degree 2's includes degree 1's — an "
            f"upper bound on its own footprint)"
        )
        print(
            f"    identity residuals: loaded "
            f"{row['identities']['loaded']['residual']:.4e}, free "
            f"{row['identities']['free']['residual']:.4e} (bound "
            f"{IDENTITY_TOLERANCE:.0e}); P_loss loaded {row['p_loaded']:+.7e} W "
            f"vs free {row['p_free']:+.7e} W"
        )
    print(
        f"  step-4 h -> 0 bracket at this f: [{low:+.4%}, {high:+.4%}]; "
        f"degree-1 record on this rung {DR_REL_10MHZ:+.4%}"
    )
    if 2 in rows:
        dev = rows[2]["dr_dev"]
        inside = low <= dev <= high
        print(
            f"  degree-2 deviation {dev:+.4%} is "
            f"{'INSIDE' if inside else 'OUTSIDE'} the bracket, a move of "
            f"{100.0 * (dev - rows[1]['dr_dev']):+.4f} pp off degree 1 on the "
            f"same mesh — read by the review, which owns the rung-swap decision"
        )
    else:
        print(
            "  degree 2 was not solved (cost probe over cap, or probe mode) — "
            "the projection above is the step's result"
        )


# ---------------------------------------------------------------------------
# the calibration rung: the memory exponent, measured instead of assumed
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_memory_exponent_measured_on_the_fine_rung():
    """Measure ``RSS_solve ∝ DOF^p`` on this machinery, at fixed element order.

    The probe's stop rule needs an exponent, and the first run used a
    *pre-registered guess* of 1.5 whose projection (69.49 GiB) and linear end
    (30.54 GiB) straddle the threshold — i.e. the guess, not the measurement,
    decided the step.  This test replaces it with a number: the same solve on
    the `TH-11` **fine** rung (418 888 cells on 0.11 / 417 914 on 0.7.2,
    `MAT-6` step 8's own second rung,
    imported not restated) gives a second (DOFs, RSS) point at unchanged order,
    solver, drive and rank count, and two points fix ``p``.

    Only the **loaded** solve runs — half the cost of the pair, and the pair's
    second solve adds no memory information because MUMPS factors the same
    sparsity structure either way.

    Quantitative assertion: the fine rung meshes to its recorded 418 888 cells
    (0.7.2: 417 914; the assertion imports `NCELLS_FINE`, never restates it),
    so the two points really are the two rungs whose records `TH-11` measured;
    and the fitted exponent must exceed 1, which is what "MUMPS fill-in grows
    faster than the unknown count" means — a fit at or below 1 would say this
    fixture has no fill-in growth at all and would invalidate the projection's
    whole form rather than just its exponent.
    """
    if _mode() != "calibrate":
        pytest.skip("the calibration rung runs under TH12_STEP2_MODE=calibrate")

    comm = MPI.COMM_WORLD
    comm.Barrier()
    t_mesh = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=0.002,
        resolution_near=RESOLUTION_NEAR_FINE,
        resolution_far=0.025,
        near_half_width=0.06,
        near_depth=0.05,
        near_height=0.03,
        comm=comm,
    )
    comm.Barrier()
    t_mesh = time.perf_counter() - t_mesh
    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )

    rss_presolve = _rss_peak_bytes(comm)
    n_dofs = _dof_count(msh, 1)
    _, _, t_solve = _solve_projected_at(
        msh, cell_tags, FEM_SIGMA_SLAB, FREQUENCY_HZ, comm, degree=1
    )
    rss_peak = _rss_peak_bytes(comm)

    solve_part = rss_peak - rss_presolve
    base_part = PROBE_BASELINE_RSS - PROBE_BASELINE_RSS_PRESOLVE
    dof_ratio = n_dofs / PROBE_BASELINE_DOFS
    exponent = float(np.log(solve_part / base_part) / np.log(dof_ratio))

    # What the measured exponent says about the degree-2 question the probe
    # stopped on: the same model, same baseline row, only p replaced.
    degree2_ratio = 882_296 / PROBE_BASELINE_DOFS
    projected = PROBE_BASELINE_RSS_PRESOLVE + base_part * degree2_ratio**exponent
    _, cap = _memory_peak_bytes()

    if comm.rank == 0:
        print(
            f"\n[TH-12 2 | CALIBRATION] fine rung {ncells} cells, mesh "
            f"{t_mesh:.1f} s, loaded solve {t_solve:.1f} s at -n {comm.size}"
            f"\n[TH-12 2 | CALIBRATION] {n_dofs} DOFs ({dof_ratio:.3f}x the "
            f"baseline rung's {PROBE_BASELINE_DOFS}); solve-attributable summed "
            f"RSS {solve_part / 2**30:.2f} GiB vs the baseline rung's "
            f"{base_part / 2**30:.2f} GiB"
            f"\n[TH-12 2 | CALIBRATION] MEASURED exponent p = {exponent:.3f} "
            f"(module constant, now itself calibrated: "
            f"{MEMORY_GUARD_EXPONENT}; the original pre-registered guess was 1.5)"
            f"\n[TH-12 2 | CALIBRATION] degree 2 on the baseline rung "
            f"re-projected at the measured p: {projected / 2**30:.2f} GiB "
            f"against memory.max {cap / 2**30:.2f} GiB and the "
            f"{MEMORY_GUARD_FRACTION:.0%} threshold "
            f"{cap * MEMORY_GUARD_FRACTION / 2**30:.2f} GiB — "
            + (
                "still over: the stop rule stands on a measured exponent"
                if projected > cap * MEMORY_GUARD_FRACTION
                else "under: the guessed exponent, not the machinery, was what "
                "stopped the degree-2 solve"
            ),
            flush=True,
        )

    assert ncells == NCELLS_FINE, (
        "the calibration point must be the recorded fine rung so the two "
        f"points are `TH-11`'s own two rungs; got {ncells}, expected "
        f"{NCELLS_FINE}"
    )
    assert exponent > 1.0, (
        f"the fitted memory exponent is {exponent:.3f} ≤ 1, i.e. this fixture "
        "would have no MUMPS fill-in growth at all — the projection's form, "
        "not just its exponent, is then wrong and the step's stop rule must be "
        "rebuilt rather than re-tuned"
    )


# ---------------------------------------------------------------------------
# the fixture really is the fixture, and only the element order moved
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_mesh_is_the_mat6_step3_baseline(degree_rows):
    """138 490 cells (0.7.2: 138 619): the mesh both the record and step 4's
    bracket sit on.

    The element order never reaches the mesh generator, so a different count
    would mean the degree comparison is across two different problems and the
    bracket below is about neither of them.
    """
    ncells = degree_rows["ncells"]
    print(f"\n  cells: {ncells} (record: {NCELLS_BASELINE})")
    assert ncells == NCELLS_BASELINE, (
        "the element order does not reach the mesh generator, so the count must "
        f"be the step-3 baseline's {NCELLS_BASELINE}; got {ncells}"
    )


@complex_only
@pytest.mark.integration
def test_the_cost_probe_priced_degree2_before_solving_it(degree_rows):
    """The §7 probe produced a real number, and the stop rule was evaluated.

    Quantitative in its own right: degree-2 N1curl carries 2 DOFs per edge and
    2 per face against degree 1's 1 per edge, so on a tetrahedral mesh the ratio
    is bounded well away from 1 — a probe reporting anything at or below unity
    has not priced the space it claims to.
    """
    projection = degree_rows["projection"]
    print(
        f"\n  degree-2 DOFs {projection['n_dofs_2']} "
        f"({projection['dof_ratio']:.3f}x degree 1); projection "
        f"{projection['guard'] / 2**30:.2f} GiB vs threshold "
        f"{projection['threshold'] / 2**30:.2f} GiB "
        f"(over cap: {projection['over_cap']})"
    )
    assert projection["dof_ratio"] > 1.0, (
        f"degree 2 priced at {projection['dof_ratio']:.3f}x the degree-1 DOF "
        "count: a second-order N1curl space on the same mesh cannot have fewer "
        "unknowns, so the probe measured the wrong space"
    )
    assert np.isfinite(projection["guard"]), (
        "the memory projection is not finite, so the §7 stop rule was never "
        f"actually evaluated: {projection}"
    )


@complex_only
@pytest.mark.integration
def test_the_degree1_control_reproduces_its_recorded_deviation(degree_rows):
    """+1.5834% to the `MAT-6` step-8 run-to-run floor of 0.01 pp.

    Same-process pinning (step 1's pattern): the control shares this mesh
    object, this rank count and this interpreter with the degree-2 row, so a
    drift here is a change in the fixture or the solver and it invalidates the
    degree-2 reading before it is made.  The bound is a measured floor, not a
    fitted tolerance — the re-solve is deterministic and is expected far inside
    it.
    """
    row = degree_rows["rows"][1]
    moved_pp = 100.0 * (row["dr_dev"] - DR_REL_10MHZ)
    print(
        f"\n  degree 1: {row['dr_dev']:+.4%} vs record {DR_REL_10MHZ:+.4%} → "
        f"{moved_pp:+.5f} pp (floor {DR_WOBBLE_FLOOR_PP} pp)"
    )
    assert abs(moved_pp) <= DR_WOBBLE_FLOOR_PP, (
        f"the degree-1 anchor moved {moved_pp:+.5f} pp off its record "
        f"{DR_REL_10MHZ:+.4%}, beyond the {DR_WOBBLE_FLOOR_PP} pp run-to-run "
        "floor: the fixture changed under the record, so nothing measured at "
        "degree 2 here is comparable to it"
    )


# ---------------------------------------------------------------------------
# the bookkeeping gates: the printed reading is only as good as these
# ---------------------------------------------------------------------------


def _row_or_skip(degree_rows, degree: int) -> dict:
    rows = degree_rows["rows"]
    if degree not in rows:
        projection = degree_rows["projection"]
        pytest.skip(
            f"degree {degree} was not solved: cost-probe projection "
            f"{projection['guard'] / 2**30:.2f} GiB against threshold "
            f"{projection['threshold'] / 2**30:.2f} GiB "
            f"(over cap: {projection['over_cap']}), mode {_mode()!r}"
        )
    return rows[degree]


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("degree", [1, 2])
@pytest.mark.parametrize("which", ["loaded", "free"])
def test_complex_power_identity_holds_at_this_order(degree_rows, degree, which):
    """``Im Z = 4ω(W_m − W_e)/I′²`` to 1e-9 on every solve at every order.

    Exact for the discrete solution, so this gates bookkeeping rather than
    accuracy; the `TH-11` rungs met it at ~1e-14.  The bound is the step-2f
    family's and is **not** widened for the ~5× larger degree-2 system: if
    second order assembles or conditions differently, this is where it shows.
    """
    row = _row_or_skip(degree_rows, degree)
    entry = row["identities"][which]
    print(
        f"\n  degree {degree}, {which}: Im Z reaction {entry['im_reaction']:.6e} Ω "
        f"vs energy {entry['im_energy']:.6e} Ω → residual "
        f"{entry['residual']:.4e} (W_m {entry['w_m']:.4e} J, W_e "
        f"{entry['w_e']:.4e} J)"
    )
    assert entry["residual"] < IDENTITY_TOLERANCE, (
        f"complex-power identity broken on the {which} solve at degree "
        f"{degree}: reaction {entry['im_reaction']:.6e} Ohm vs energy "
        f"{entry['im_energy']:.6e} Ohm, relative {entry['residual']:.4e}"
    )


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("degree", [1, 2])
def test_the_free_solve_dissipates_exactly_nothing(degree_rows, degree):
    """σ = 0 ⇒ ``½∫σ|E|²`` is ``+0.0`` exactly; loaded ⇒ positive.

    `EX-11`'s control, carried onto the second-order space.  A σ-blind pipeline
    returns the loaded value for both, so the separation is infinite by
    construction and the assertion is exact equality, not a band.
    """
    row = _row_or_skip(degree_rows, degree)
    print(
        f"\n  degree {degree} P_loss: loaded {row['p_loaded']:+.7e} W, "
        f"free (σ = 0) {row['p_free']:+.7e} W"
    )
    assert row["p_free"] == 0.0, (
        f"a σ = 0 slab must dissipate exactly nothing at degree {degree}, got "
        f"{row['p_free']!r}"
    )
    assert row["p_loaded"] > 0.0, (
        f"the loaded slab must dissipate at degree {degree}, got "
        f"{row['p_loaded']!r}"
    )


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("degree", [1, 2])
def test_both_solves_are_driven_by_the_same_projected_current(degree_rows, degree):
    """The drive control at both orders, at the family's 1e-24.

    ``remove_gradient_content`` sees the mesh, ``J`` and the cell tags but never
    the material, so the loaded and free solves must use the identical ``J′`` —
    otherwise the reaction difference measures the drive rather than the
    half-space.  The projection runs in the degree-2 space here, which is the
    part that has never been exercised.
    """
    row = _row_or_skip(degree_rows, degree)
    print(f"\n  degree {degree}: ||J'_loaded - J'_free||^2 / ||J'||^2 = "
          f"{row['drive_mismatch']:.3e}")
    assert row["drive_mismatch"] < 1.0e-24, (
        f"the two degree-{degree} solves used different drives: "
        f"{row['drive_mismatch']}"
    )


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("degree", [1, 2])
def test_the_loaded_coil_dissipates_and_expels_flux(degree_rows, degree):
    """Signs only: ΔR > 0, ΔX < 0 — passivity and Lenz's law, not Dodd–Deeds.

    The magnitudes are printed by the fixture beside step 4's bracket and
    deliberately not gated (§7: ΔR printed, never gated).  These two signs are
    the strongest statement that does not depend on the quasi-static kernel, so
    they stay assertable at both orders.
    """
    row = _row_or_skip(degree_rows, degree)
    dz = row["dz"]
    print(
        f"\n  degree {degree}: ΔR = {dz.real:+.7e} Ω, ΔX = {dz.imag:+.7e} Ω, "
        f"deviation {row['dr_dev']:+.4%}"
    )
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
