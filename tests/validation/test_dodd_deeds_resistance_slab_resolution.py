"""`MAT-6` step 8: does ΔR move under *slab* refinement at fixed wire and box?

Step 5 attributed roughly a third of the landed 1.58% ΔR error to wire
discretisation (1.5834% → 1.0562% under ``resolution_wire`` 0.002 → 0.001 at
fixed box) and step 4 bounded the box term at < 0.01 pp of wobble past
W = 0.15.  The remaining ~1.06% is unattributed between two candidates, and
this module separates them by moving **only the slab knob**:

* **skin-depth resolution** — the landed ``resolution_near = 0.005`` gives
  ~3.2 cells per δ = 15.9 mm (10 MHz, σ = 100 S/m), degree-1 Nédélec, against
  an ohmic boundary layer that decays as e^(−z/δ).  Halving it to 0.0025 gives
  ~6.4 cells per δ.
* **filamentary-reference mismatch** — the closed form is evaluated for an
  ideal loop at ``(a, h)`` while the meshed coil is a 2.5 mm wire
  (``h/r_wire`` = 8 against step 2b's ≥ 16 target, measured unreachable in
  this container by step 5).  No slab mesh can remove it.

A ΔR that moves ~1 pp toward the closed form attributes the residual to
skin-depth resolution; a ΔR pinned near 1.06% says the residual is the coil
model, and that is equally the finding (§7).

**Nothing about the fixture moves except ``resolution_near``.**  ``W = 0.15``,
``resolution_wire = 0.002``, ``resolution_far = 0.025`` and the near-region
*extents* (``near_half_width``/``near_depth``/``near_height``) all stay put —
this refines cell size inside the region, not the region.  ``FEM_WIRE_RADIUS``
stays 0.0025 m, so ``_solve_projected`` and the step-2b constants are imported
and used verbatim, exactly as step 5 imported them for the wire sweep.
**Projected drive only** (§7): the production default path, two solves.

Measured ladder (``20260811T123143Z_MAT-6-step8-probe-mesh.log``), W = 0.15,
``resolution_wire = 0.002``:

===================  ==============  ==========  ==========
``resolution_near``  cells per δ     cells       vs landed
===================  ==============  ==========  ==========
0.005 (landed)       3.18            138 619     1.00×
0.0035               4.54            209 964     1.51×
0.0025 (**here**)    6.36            417 914     3.01×
===================  ==============  ==========  ==========

The §7 entry's naive bound was ~8× growth; the measured 3.01× is well under
it, and one projected loaded solve cost **108.8 s at -n 4** / 486 694 global
dofs (``20260811T123242Z_MAT-6-step8-probe-solve.log``), inside the 300 s
stop rule, so the gate runs at the full 0.0025 rung rather than the 0.0035
rescope rung.

**Gates are step 2b's, applied unchanged**: ΔR under a 5% hard ceiling, never
tightened in-slot; ΔX on sign and order of magnitude only, reported and never
gated to whatever it returns.

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_dodd_deeds_resistance_slab_resolution.py -v -s'
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
    SLAB_TAG,
    WIRE_TAG,
    _azimuthal_current_density,
)
from tests.validation.test_dodd_deeds_projected_drive import (
    _reduced_real,
    _solve_projected,
)

# The one parameter that moves.
RESOLUTION_NEAR_FINE = 0.0025
RESOLUTION_NEAR_LANDED = 0.005
# Skin depth at this fixture's 10 MHz / σ = 100 S/m: δ = 1/sqrt(pi f mu0 sigma).
SKIN_DEPTH_M = 1.0 / np.sqrt(np.pi * FEM_FREQUENCY_HZ * 4.0e-7 * np.pi * FEM_SIGMA_SLAB)

# The cell counts this step's own probe measured, both on record:
NCELLS_LANDED = 138_619
NCELLS_FINE = 417_914

# The ΔR ladder this step refines against — read off the logs, not recomputed:
#   wire 0.002 (landed)  ΔR rel. error 1.5834%
#     `20260804T213600Z_MAT-6-step3-gate-final.log` (projected drive)
#   wire 0.001 (step 5)  ΔR rel. error 1.0562%
#     `20260807T201036Z_MAT-6-step5-projected.log`
DR_REL_LANDED = 0.015834
DR_REL_FINE_WIRE = 0.010562

# Step 4's W-series measured ΔR moving < 0.01 percentage-point across a 2.17×
# change in cell count.  That is the reality floor: a refinement effect smaller
# than it is mesh noise, not physics.
DR_WOBBLE_FLOOR_PP = 0.01

# The meshed loop current at ``resolution_wire = 0.002``, on record at two box
# sizes and unmoved by either (`20260731T110515Z_MAT-6-step2b-gate-numbers.log`,
# "meshed loop current 0.919690 A").  The slab knob must not move it either —
# that is what makes this a slab-only refinement.
CURRENT_COARSE_WIRE_A = 0.919690


def _mesh_fine_slab(comm):
    """The step-2b fixture with one parameter moved: ``resolution_near``."""
    comm.Barrier()
    t0 = time.perf_counter()
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
    t_mesh = time.perf_counter() - t0
    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    return msh, cell_tags, float(t_mesh), int(ncells)


def _ohmic_resistance(msh, cell_tags, e_field, sigma_slab, current, comm) -> float:
    """``R = 2 P_loss / |I|²`` with ``P_loss = ½ ∫_slab σ |E|² dx``.

    Computed from fields the fixture already has, so it costs no solve.  Its
    only job here is the σ-blind control: at ``sigma_slab = 0`` the integrand
    is identically zero and the result must be ``+0.0`` **exactly**, with no
    tolerance — a σ-blind pipeline would return the loaded value for both.
    """
    dx_slab = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(SLAB_TAG,)
    )
    p_loss = 0.5 * sigma_slab * _reduced_real(
        ufl.inner(e_field, e_field) * dx_slab, comm
    )
    return 2.0 * p_loss / current**2


@pytest.fixture(scope="module")
def projected_fine_slab():
    """Loaded/free pair on the production default (projected) drive.

    Module-scoped: 417 914 cells and 108.8 s per solve at ``-n 4`` on record,
    so the pair is meshed and solved exactly once for the whole module.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags, t_mesh, ncells = _mesh_fine_slab(comm)

    e_loaded, j_prime_loaded, t_loaded = _solve_projected(
        msh, cell_tags, FEM_SIGMA_SLAB, comm
    )
    e_free, _, t_free = _solve_projected(msh, cell_tags, 0.0, comm)

    x = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_current_density(1.0)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )

    # The unprojected meshed current, as step 2b computes it: a pure measure of
    # the faceted torus's volume deficit, and therefore of whether this knob
    # leaked onto the wire.
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)
    v_wire = _reduced_real(
        fem.Constant(msh, np.array(1.0, dtype=np.complex128).item()) * dx_wire, comm
    )
    current_unprojected = j_magnitude * v_wire / (2.0 * np.pi * FEM_LOOP_RADIUS)

    # I' from the drive actually used, and ΔZ over the WHOLE domain: J' has
    # support everywhere, unlike J.  Both exactly as steps 3, 4 and 5 do it.
    current = _reduced_real(ufl.inner(j_prime_loaded, phi_hat) * dx_wire, comm) / (
        2.0 * np.pi * FEM_LOOP_RADIUS
    )
    # assemble_scalar is rank-local; reduce before forming ΔZ.  J' is real, so
    # inner()'s conjugation of the second argument is a no-op — reaction, not
    # power.
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

    r_ohmic_loaded = _ohmic_resistance(
        msh, cell_tags, e_loaded, FEM_SIGMA_SLAB, current, comm
    )
    r_ohmic_free = _ohmic_resistance(msh, cell_tags, e_free, 0.0, current, comm)

    rel_r = abs(dz.real / dz_ref.real - 1.0)
    ratio_x = dz.imag / dz_ref.imag
    if comm.rank == 0:
        print(
            f"\n[MAT-6 step 8 | projected | resolution_near = "
            f"{RESOLUTION_NEAR_FINE} m] {ncells} cells "
            f"({SKIN_DEPTH_M / RESOLUTION_NEAR_FINE:.2f} cells per skin depth "
            f"δ = {SKIN_DEPTH_M * 1e3:.1f} mm), mesh {t_mesh:.1f} s, solves "
            f"{t_loaded:.1f} s + {t_free:.1f} s at -n {comm.size}"
            f"\n[MAT-6 step 8 | projected] I' = {current:.6f} A; unprojected "
            f"meshed I = {current_unprojected:.6f} A"
            f"\n[MAT-6 step 8 | projected] FEM   dZ = {dz.real:+.7e} + "
            f"j({dz.imag:+.7e}) Ohm"
            f"\n[MAT-6 step 8 | projected] exact dZ = {dz_ref.real:+.7e} + "
            f"j({dz_ref.imag:+.7e}) Ohm"
            f"\n[MAT-6 step 8 | projected] dR rel. error {rel_r:.4%} "
            f"(ladder: {DR_REL_LANDED:.4%} at wire 0.002 / slab 0.005, "
            f"{DR_REL_FINE_WIRE:.4%} at wire 0.001 / slab 0.005)"
            f"\n[MAT-6 step 8 | projected] dX ratio {ratio_x:.4f} (reported, "
            f"never gated)"
            f"\n[MAT-6 step 8 | projected] sigma-blind control: ohmic R "
            f"loaded {r_ohmic_loaded:+.7e} Ohm vs free {r_ohmic_free:+.7e} Ohm",
            flush=True,
        )
    return dict(
        dz=dz,
        dz_ref=dz_ref,
        current=current,
        current_unprojected=current_unprojected,
        ncells=ncells,
        rel_r=rel_r,
        ratio_x=ratio_x,
        r_ohmic_loaded=r_ohmic_loaded,
        r_ohmic_free=r_ohmic_free,
    )


# ---------------------------------------------------------------------------
# the mesh itself: the refinement has to be real, and slab-local
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_refinement_landed_in_the_slab_and_not_on_the_wire_or_far_field(
    projected_fine_slab,
):
    """The knob did what it says: 3.01× cells, and the count is the probe's.

    The mesh is deterministic and only ``resolution_near`` moved, so the count
    must reproduce the probe's exactly.  The growth band brackets that measured
    value loosely enough not to restate it and tightly enough to catch a
    ``resolution_far`` leak, which would multiply the count far beyond it.
    """
    ncells = projected_fine_slab["ncells"]
    growth = ncells / NCELLS_LANDED
    print(
        f"\n  cells: {ncells} at resolution_near = {RESOLUTION_NEAR_FINE} m "
        f"vs {NCELLS_LANDED} landed → {growth:.2f}×"
    )
    assert ncells == NCELLS_FINE, (
        "the mesh is deterministic and only resolution_near moved, so the cell "
        f"count must be the probe's {NCELLS_FINE}; got {ncells}"
    )
    assert 2.0 < growth < 4.5, f"refinement growth {growth:.2f}× is not slab-local"


@complex_only
@pytest.mark.integration
def test_the_slab_knob_left_the_meshed_wire_alone(projected_fine_slab):
    """The torus volume — hence the meshed current — is unmoved by this knob.

    ``resolution_wire`` sets the torus surface triangulation and did not move,
    so the faceted torus must carry the same 0.919690 A step 2b recorded and
    step 4's box change left untouched.  This is what separates step 8's
    reading from step 5's: if the current moved, part of any ΔR shift would be
    the 1/I² prefactor rather than the slab field.
    """
    current = projected_fine_slab["current_unprojected"]
    rel = abs(current / CURRENT_COARSE_WIRE_A - 1.0)
    deficit = 1.0 - current / FEM_CURRENT_A
    print(
        f"\n  meshed I = {current:.6f} A vs on-record {CURRENT_COARSE_WIRE_A} A "
        f"→ {rel:.4%} (volume deficit {deficit:.4%})"
    )
    assert deficit > 0.0, (
        "an inscribed faceted torus cannot exceed the analytic volume, got "
        f"deficit {deficit:.4%}"
    )
    assert rel < 0.01, (
        "the slab knob must not move the meshed wire current; it moved "
        f"{rel:.4%} from the on-record {CURRENT_COARSE_WIRE_A} A"
    )


# ---------------------------------------------------------------------------
# the σ-blind control, re-asserted on the new mesh
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_free_solve_dissipates_exactly_nothing_on_the_refined_slab(
    projected_fine_slab,
):
    """σ = 0 ⇒ ohmic ``R = +0.0`` exactly, no tolerance; loaded ⇒ positive.

    §7's negative control for this step.  ``½∫σ|E|²`` over the slab is the one
    quantity that must vanish identically when the material carries no
    conductivity — a pipeline that ignored σ (the failure mode step 2b's
    σ-blind control was written for, 100% separation on record) would return
    the loaded value here.  Separation is infinite by construction, so the
    assertion is exact equality rather than a band.
    """
    loaded = projected_fine_slab["r_ohmic_loaded"]
    free = projected_fine_slab["r_ohmic_free"]
    print(f"\n  ohmic R: loaded {loaded:+.7e} Ω, free (σ = 0) {free:+.7e} Ω")
    assert free == 0.0, f"a σ = 0 slab must dissipate exactly nothing, got {free!r}"
    assert loaded > 0.0, f"the loaded slab must dissipate, got {loaded!r}"


# ---------------------------------------------------------------------------
# the reading: ΔR against Dodd–Deeds on the refined slab
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_projected_resistance_change_matches_dodd_deeds_on_the_refined_slab(
    projected_fine_slab,
):
    """ΔR keeps step 2b's 5% ceiling under slab refinement.

    The ceiling is inherited from step 2b and never tightened in-slot: whether
    slab resolution owns the residual ~1.06% is the question under test, so a
    band sized to this run would assert its own conclusion.  The attribution is
    the *reported* movement against the ladder, printed by the fixture.
    """
    dz, dz_ref = projected_fine_slab["dz"], projected_fine_slab["dz_ref"]
    rel = projected_fine_slab["rel_r"]
    # This rung's wire resolution is the landed 0.002, so the like-for-like
    # comparison is DR_REL_LANDED; DR_REL_FINE_WIRE is step 5's *other* knob and
    # is printed only to place the slab movement beside the wire movement.
    moved_pp = 100.0 * (rel - DR_REL_LANDED)
    print(
        f"\n  ΔR: FEM {dz.real:.7e} Ω vs exact {dz_ref.real:.7e} Ω → {rel:.4%}"
        f"  (same wire rung, slab 0.005: {DR_REL_LANDED:.4%} → this rung moved "
        f"{moved_pp:+.4f} pp; step 5's wire knob alone reached "
        f"{DR_REL_FINE_WIRE:.4%}; reality floor {DR_WOBBLE_FLOOR_PP} pp)"
    )
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert rel < 0.05, f"projected ΔR off the closed form by {rel:.2%}"


@complex_only
@pytest.mark.integration
def test_projected_reactance_change_has_the_right_sign_and_magnitude_on_the_refined_slab(
    projected_fine_slab,
):
    """ΔX on the projected drive: sign and order of magnitude, step 2b's gate.

    ΔX is reported everywhere in `MAT-6` and gated nowhere; step 8 changes
    nothing about that.
    """
    dz, dz_ref = projected_fine_slab["dz"], projected_fine_slab["dz_ref"]
    ratio = projected_fine_slab["ratio_x"]
    print(
        f"\n  ΔX: FEM {dz.imag:.7e} Ω vs exact {dz_ref.imag:.7e} Ω → ratio {ratio:.4f}"
    )
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
    assert 0.5 < ratio < 2.0, (
        f"projected ΔX is not within an order of magnitude: {ratio}"
    )
