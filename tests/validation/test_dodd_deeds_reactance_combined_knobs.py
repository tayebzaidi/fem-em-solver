"""`MAT-6` step 7 Part 2 (step 6's gate): are the two mesh knobs additive?

Step 4 measured the **box** knob at coarse wire (projected ΔX ratio
0.9200 → 0.9849 for ``W`` 0.15 → 0.25); step 5 measured the **wire** knob at
fixed box (0.9200 → 0.9194 at ``W`` = 0.15).  If the two residual terms are
independent, turning both at once must land at

    0.9194 + 0.9849 − 0.9200 = **0.9843**

and this module measures that number on the combined fixture — ``W`` = 0.25
**and** ``resolution_wire`` = 0.001, projected drive only, nothing else moved.
The reading matters because single-knob extrapolation is the precondition for
ever writing a defensible ΔX gate: a real cross-term kills the shortcut before
anything downstream trusts it.

**Why this module exists only now.**  Step 6 could not run it: the combined
mesh is 697 401 cells and the container was capped at 16 G, which OOM-killed
the solve at ``-n 4`` (signal 9, ~262 s in) and again at ``-n 8`` (exit 137,
~138 s in) — a cgroup bound on the job's *total* footprint, which more ranks
cannot lower.  Step 7 Part 1 raised the cap to 64 G
(``docker/docker-compose.yml``; verified at the kernel,
``/sys/fs/cgroup/memory.max`` = 68719476736) and Part 2 is this measurement.
Those two kill records are the negative control and are **cited, never
recomputed**.

**The reading is pre-decided** (§7 step 6, inherited verbatim by step 7), so
that no band is sized to its own result:

=========================  =============================================
``|ratio − 0.9843|``       verdict
=========================  =============================================
≤ 0.5 pp                   consistent with additive
> 1.5 pp                   a real cross-term; single-knob extrapolation
                           is invalid
between                    ambiguous — report and stop
=========================  =============================================

**Gates are step 2b's, applied unchanged**: ΔR under a 5% hard ceiling; ΔX on
sign and order of magnitude only.  The ΔX ratio is *reported* against 0.9843,
never gated to it — whether ΔX converges is the thing under test.

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_dodd_deeds_reactance_combined_knobs.py -v -s'
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
)
from tests.validation.test_dodd_deeds_projected_drive import (
    _reduced_real,
    _solve_projected,
)

# Both knobs, each at the setting its own single-knob step measured.  Nothing
# else moves — in particular ``resolution_near``/``resolution_far`` and
# ``FEM_WIRE_RADIUS`` are the step-2b values, so the imported solve helpers are
# used verbatim.
BOX_HALF_WIDTH_LARGE = 0.25
RESOLUTION_WIRE_FINE = 0.001

# Measured three times now, byte-identically, at -n 4 / -n 8 / -n 4:
# `20260808T183121Z_MAT-6-step6-probe.log`,
# `20260808T183648Z_MAT-6-step6-probe-n8.log`,
# `20260811T003136Z_MAT-6-step7-part2-probe.log`.
# Re-recorded for the dolfinx-0.11 image (`OPS-27` step 2): the three readings
# above are the 0.7.2 mesher's 697 401; 0.11 meshes the same fixture at 697 926
# (+0.075%), measured by the `OPS-26` census in
# `20260827T184138Z_OPS-26-step2f-dodd-combined-knobs.log`.  Exact equality, no band.
NCELLS_COMBINED = 697_926

# The three projected-drive ΔX ratios this step composes, each read off its own
# log rather than recomputed here:
#   W = 0.15, coarse wire  0.9200  `20260804T213600Z_MAT-6-step3-gate-final.log`
#   W = 0.25, coarse wire  0.9849  `20260807T18*_MAT-6-step4-*` (step 4)
#   W = 0.15, fine wire    0.9194  `20260807T201036Z_MAT-6-step5-projected.log`
DX_RATIO_BASELINE = 0.9200
DX_RATIO_BOX_KNOB = 0.9849
DX_RATIO_WIRE_KNOB = 0.9194
DX_RATIO_ADDITIVE_PREDICTION = (
    DX_RATIO_WIRE_KNOB + DX_RATIO_BOX_KNOB - DX_RATIO_BASELINE
)  # 0.9843

# Pre-decided bands, in percentage points of ΔX ratio (§7 step 6).
ADDITIVE_BAND_PP = 0.5
CROSS_TERM_BAND_PP = 1.5

# The coarse-wire meshed current, on record at both box sizes (0.919690 A —
# the box does not touch it, only wire discretisation does), i.e. an 8.031%
# volume deficit on the faceted torus.  Step 5's fine wire at W = 0.15 shrank
# it to 2.0114%, a 3.99× shrink against the O(h²) prediction of ~4×.
CURRENT_COARSE_WIRE_A = 0.919690
VOLUME_DEFICIT_SHRINK_FLOOR = 1.5


def _mesh_combined(comm):
    """The step-2b fixture with *both* measured knobs turned at once."""
    comm.Barrier()
    t0 = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=BOX_HALF_WIDTH_LARGE,
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


def _meshed_torus_current(msh, cell_tags, comm) -> float:
    """``I = j · vol(meshed torus) / 2πa`` — the faceted torus's volume deficit.

    Step 5's control, and it needs no solve: it is a volume integral over the
    wire tag.  Reported here on the projected fixture so the combined mesh
    carries the same O(h²) mechanism check the single-knob runs did.
    """
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    v_wire = _reduced_real(
        fem.Constant(msh, np.array(1.0, dtype=np.complex128).item()) * dx_wire, comm
    )
    return j_magnitude * v_wire / (2.0 * np.pi * FEM_LOOP_RADIUS)


@pytest.fixture(scope="module")
def projected_combined():
    """Loaded/free pair on the production default (projected) drive."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, t_mesh, ncells = _mesh_combined(comm)

    e_loaded, j_prime_loaded, t_loaded = _solve_projected(
        msh, cell_tags, FEM_SIGMA_SLAB, comm
    )
    e_free, _, t_free = _solve_projected(msh, cell_tags, 0.0, comm)

    # I' from the drive actually used, and ΔZ over the WHOLE domain: J' has
    # support everywhere, unlike J.  Exactly as steps 3–5 compute them.
    x = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_current_density(1.0)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
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
    torus_current = _meshed_torus_current(msh, cell_tags, comm)

    ratio_x = dz.imag / dz_ref.imag
    defect_pp = 100.0 * (ratio_x - DX_RATIO_ADDITIVE_PREDICTION)
    if comm.rank == 0:
        print(
            f"\n[MAT-6 step 7 Part 2 | projected | W = {BOX_HALF_WIDTH_LARGE} m, "
            f"resolution_wire = {RESOLUTION_WIRE_FINE} m] {ncells} cells, "
            f"mesh {t_mesh:.1f} s, solves {t_loaded:.1f} s + {t_free:.1f} s "
            f"at -n {comm.size}"
            f"\n[MAT-6 step 7 Part 2] I' = {current:.6f} A; "
            f"meshed torus I = {torus_current:.6f} A"
            f"\n[MAT-6 step 7 Part 2] FEM   dZ = {dz.real:+.7e} + "
            f"j({dz.imag:+.7e}) Ohm"
            f"\n[MAT-6 step 7 Part 2] exact dZ = {dz_ref.real:+.7e} + "
            f"j({dz_ref.imag:+.7e}) Ohm"
            f"\n[MAT-6 step 7 Part 2] dR rel. error "
            f"{abs(dz.real / dz_ref.real - 1.0):.4%}"
            f"\n[MAT-6 step 7 Part 2] dX ratio {ratio_x:.4f} vs additive "
            f"prediction {DX_RATIO_ADDITIVE_PREDICTION:.4f} → defect "
            f"{defect_pp:+.3f} pp",
            flush=True,
        )
    return dict(
        dz=dz,
        dz_ref=dz_ref,
        current=current,
        torus_current=torus_current,
        ncells=ncells,
        ratio_x=ratio_x,
        defect_pp=defect_pp,
    )


# ---------------------------------------------------------------------------
# the mesh: both knobs really turned, and the memory ceiling really moved
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_combined_mesh_is_the_probes_and_both_knobs_moved(projected_combined):
    """The mesh is deterministic: the count must be the probe's 697 401.

    Reproducing it here is also the statement that this is the *same* fixture
    step 6 could not solve — the comparison against 0.9843 is meaningless on
    any other mesh.  It is 5.03× the W = 0.15 coarse-wire baseline of 138 619,
    so both knobs are plainly in.
    """
    ncells = projected_combined["ncells"]
    growth = ncells / 138_619
    print(f"\n  cells: {ncells} vs 138619 baseline → {growth:.2f}×")
    assert ncells == NCELLS_COMBINED, (
        "the mesh is deterministic and both knobs are at their single-knob "
        f"settings, so the count must be the probe's {NCELLS_COMBINED}; "
        f"got {ncells}"
    )
    assert growth > 4.0, f"the combined mesh is not both knobs: {growth:.2f}×"


@complex_only
@pytest.mark.integration
def test_the_meshed_torus_recovers_volume_on_the_combined_mesh(projected_combined):
    """Step 5's O(h²) control, re-asserted on the new mesh.

    The faceted torus loses 8.031% of its volume at ``resolution_wire`` =
    0.002 (on record at both box sizes — the box does not touch the wire).
    Halving the wire resolution must shrink that deficit; O(h²) chord error
    predicts ~4× and step 5 measured 3.99× at W = 0.15.  The floor is 1.5×,
    well below the prediction so the gate does not assert its own answer, and
    well above step 4's < 0.01 pp mesh-noise wobble so it is real.  If the box
    knob had disturbed the wire discretisation, this is where it would show.
    """
    current = projected_combined["torus_current"]
    deficit = 1.0 - current / FEM_CURRENT_A
    deficit_coarse = 1.0 - CURRENT_COARSE_WIRE_A / FEM_CURRENT_A
    shrink = deficit_coarse / deficit
    print(
        f"\n  meshed torus I = {current:.6f} A vs exact {FEM_CURRENT_A} A → "
        f"volume deficit {deficit:.4%} (coarse wire {deficit_coarse:.4%}) → "
        f"shrink {shrink:.2f}×  [O(h²) predicts ~4×; step 5 measured 3.99× at "
        f"W = 0.15]"
    )
    assert deficit > 0.0, (
        "an inscribed faceted torus cannot exceed the analytic volume, got "
        f"deficit {deficit:.4%}"
    )
    assert shrink > VOLUME_DEFICIT_SHRINK_FLOOR, (
        f"a 2× wire refinement must shrink the {deficit_coarse:.4%} volume "
        f"deficit by more than {VOLUME_DEFICIT_SHRINK_FLOOR}×; got "
        f"{deficit:.4%}, i.e. {shrink:.2f}×"
    )


# ---------------------------------------------------------------------------
# the impedance: step 2b's gates, inherited unchanged
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_combined_resistance_change_matches_dodd_deeds(projected_combined):
    """ΔR keeps step 2b's 5% ceiling with both knobs turned.

    ΔR is the control on the whole comparison: it is converged in box size and
    dominated by the slab's skin layer, not by the wire surface or the box
    tail, so a ΔR that moved materially here would say the *mesh* changed
    under the fixture and the ΔX reading below would mean nothing.  The
    ceiling is inherited from step 2b, never widened.
    """
    dz, dz_ref = projected_combined["dz"], projected_combined["dz_ref"]
    rel = abs(dz.real / dz_ref.real - 1.0)
    print(
        f"\n  ΔR: FEM {dz.real:.7e} Ω vs exact {dz_ref.real:.7e} Ω → {rel:.4%} "
        f"(landed 1.5834% at W = 0.15 coarse wire; 1.0562% at W = 0.15 fine)"
    )
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert rel < 0.05, f"combined-fixture ΔR off the closed form by {rel:.2%}"


@complex_only
@pytest.mark.integration
def test_combined_reactance_change_has_the_right_sign_and_magnitude(
    projected_combined,
):
    """ΔX: sign and order of magnitude (step 2b's gate), ratio reported.

    The additivity defect against 0.9843 is the *reading* of this step and is
    deliberately not asserted — a band sized to this run would assert the
    thing under test.  The pre-decided verdict bands are printed beside it so
    the log carries the classification, not the reader's arithmetic.
    """
    dz, dz_ref = projected_combined["dz"], projected_combined["dz_ref"]
    ratio = projected_combined["ratio_x"]
    defect_pp = projected_combined["defect_pp"]
    if abs(defect_pp) <= ADDITIVE_BAND_PP:
        verdict = "consistent with ADDITIVE"
    elif abs(defect_pp) > CROSS_TERM_BAND_PP:
        verdict = "a real CROSS-TERM: single-knob extrapolation is invalid"
    else:
        verdict = "AMBIGUOUS — report and stop"
    print(
        f"\n  ΔX: FEM {dz.imag:.7e} Ω vs exact {dz_ref.imag:.7e} Ω → ratio "
        f"{ratio:.4f}"
        f"\n  additivity: {DX_RATIO_WIRE_KNOB} + {DX_RATIO_BOX_KNOB} − "
        f"{DX_RATIO_BASELINE} = {DX_RATIO_ADDITIVE_PREDICTION:.4f} predicted; "
        f"measured {ratio:.4f} → defect {defect_pp:+.3f} pp → {verdict}"
        f"\n  (bands: ≤ {ADDITIVE_BAND_PP} pp additive / "
        f"> {CROSS_TERM_BAND_PP} pp cross-term / between ambiguous)"
    )
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
    assert 0.5 < ratio < 2.0, (
        f"combined-fixture ΔX is not within an order of magnitude: {ratio}"
    )
