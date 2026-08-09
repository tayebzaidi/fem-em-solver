"""Example (`EX-11`): coil loading by a conductive half-space, ΔR vs Dodd-Deeds.

The `§5.4` ramp entry for Phase 3's headline result. `MAT-6` is the only chunk
in the project that gates a *loaded coil*: a 1-turn loop 20 mm above a σ = 100
S/m half-space at 10 MHz raises its own resistance by ΔR = +3.277e-01 Ω, and the
FEM reproduces the Dodd-Deeds closed form for that rise to 1.58%. Nothing under
``examples/`` has ever shown it. This example runs the same two solves the gate
runs, asserts the same number, and writes the eddy-current density into the slab
so the operator can see *where* the loss lives.

**10 MHz, eddy-current regime — no Larmor claim.** PROJECT_PLAN §2.1 is explicit
that the saline/Larmor case is an extrapolation, not a result. This example
inherits that boundary exactly: it is a quantitative statement about a
conductive half-space at 10 MHz and about nothing else.

**It asserts, it does not merely render.** Every constant, the mesh, the
azimuthal drive and the solve itself are *imported* from the modules that closed
`MAT-6` steps 2b/3 — ``tests/validation/test_dodd_deeds_impedance.py`` and
``tests/validation/test_dodd_deeds_projected_drive.py`` — so the example and the
landed gate cannot drift apart:

* *The anchor:* ΔR against ``utils.dodd_deeds.coil_impedance_change`` at the
  same fixture, gated here at 2% (1.5834% on record, `MAT-6` step 3, log
  ``20260804T...`` / step 2b's ``20260731T110515Z_MAT-6-step2b-gate-numbers.log``).
  The gate's own ceiling is 5%; 2% is the §7 `EX-11` plan's, tighter than the
  gate only in the sense that it is what the fixture actually delivers — it is
  never loosened here, and a miss is a regression finding, not a tolerance
  question.
* *The sign:* a conductor must dissipate (ΔR > 0) and expel flux (ΔX < 0).
* *The negative control, in-fixture:* the free solve is the σ = 0 half of the
  same pair, so the control costs nothing and shares every other input. Its
  ohmic power in the slab is identically zero against the loaded solve's finite
  value — total separation, no tolerance needed — and the |J| field it would
  export is identically zero everywhere.
* *An independent energy identity, reported not gated:* the ohmic power
  ``∫_slab (σ/2)|E|² dV`` should equal ``½ ΔR |I'|²``. It is computed from the
  solved field rather than from the reaction integral ΔZ comes out of, so it is
  a genuine cross-check; it is printed rather than asserted because ΔX on this
  fixture is not converged in box size (−18.8% at W = 0.15, `MAT-6` step 3) and
  the plan licenses one gated anchor here, not a new one.

Run it through the example runner (the ``mat:`` group sources the complex build
automatically)::

    ./run_examples.sh -e mat:1

Output lands in ``examples/materials/paraview_output/``: open
``dodd_deeds_coil_loading_combined.xdmf``, threshold on ``CellTags``
(3 = the lossy slab, 1 = the wire) and colour by ``J_magnitude``. The induced
current hugs the slab surface under the loop and falls off with the skin depth
δ = 1/sqrt(pi f mu0 sigma) printed by the run.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

# The gated constants, the fixture and the solve live in the tests that closed
# `MAT-6` steps 2b/3; the §7 `EX-11` plan requires importing them rather than
# restating them. The runner puts only ``src`` on PYTHONPATH, so the repo root
# goes on sys.path here.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.core import HomogeneousMaterial  # noqa: E402
from fem_em_solver.core.time_harmonic import build_material_fields  # noqa: E402
from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.utils.dodd_deeds import coil_impedance_change  # noqa: E402

from tests.validation.test_dodd_deeds_impedance import (  # noqa: E402
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
from tests.validation.test_dodd_deeds_projected_drive import (  # noqa: E402
    _solve_projected,
)

#: The §7 `EX-11` plan's ceiling on ΔR. The `MAT-6` step-3 gate's own ceiling is
#: 5%; the fixture measures 1.5834%, so 2% is what the example can honestly
#: claim. Looser than the measurement, tighter than the gate — and not a knob:
#: a run outside it is a regression finding (see the module docstring).
DELTA_R_RTOL = 0.02

MU0 = 4.0e-7 * np.pi

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "dodd_deeds_coil_loading"


def _reduced_real(form, comm) -> float:
    """``assemble_scalar`` is rank-local; reduce, then take the real part."""
    return float(np.real(comm.allreduce(fem.assemble_scalar(fem.form(form)), op=MPI.SUM)))


def _build_fixture(comm):
    """`MAT-6`'s W = 0.15 fixture, meshed exactly as the step-3 gate meshes it."""
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=0.002,
        resolution_near=0.005,
        resolution_far=0.025,
        near_half_width=0.06,
        near_depth=0.05,
        near_height=0.03,
        comm=comm,
    )
    return msh, cell_tags


def _sigma_field(msh, cell_tags, sigma_slab):
    """σ(x) through the production DG0 builder: the slab is lossy, air is not."""
    sigma, _ = build_material_fields(
        msh,
        HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            SLAB_TAG: HomogeneousMaterial(sigma=sigma_slab, epsilon_r=1.0, mu_r=1.0)
        },
    )
    return sigma


def _ohmic_power_in_slab(e_complex, sigma, msh, cell_tags, comm) -> float:
    """``∫_slab (σ/2)|E|² dV`` — the dissipated power, from the field itself.

    ``ufl.inner`` conjugates its second argument in complex UFL, so this is
    |E|² and not E², and the result is real up to round-off.
    """
    dx_slab = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(SLAB_TAG,)
    )
    return _reduced_real(0.5 * sigma * ufl.inner(e_complex, e_complex) * dx_slab, comm)


def _current_density_magnitude(e_complex, sigma, msh):
    """``|J| = σ|E|`` as a DG0 field — what ParaView colours by.

    ``|J|²`` is interpolated (a polynomial expression UFL is happy with) and the
    square root is taken on the array, so no complex ``sqrt`` is ever formed.
    """
    dg0 = fem.functionspace(msh, ("DG", 0))
    j_squared = fem.Function(dg0)
    j_squared.interpolate(
        fem.Expression(
            sigma * sigma * ufl.inner(e_complex, e_complex),
            dg0.element.interpolation_points(),
        )
    )
    j_mag = fem.Function(dg0, name="J_magnitude")
    j_mag.x.array[:] = np.sqrt(np.maximum(np.real(j_squared.x.array), 0.0))
    j_mag.x.scatter_forward()
    return j_mag


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "this example needs the complex DolfinX build "
            "(source /usr/local/bin/dolfinx-complex-mode); the runner's `mat:` "
            "group sources it automatically"
        )

    skin_depth = 1.0 / np.sqrt(np.pi * FEM_FREQUENCY_HZ * MU0 * FEM_SIGMA_SLAB)

    if comm.rank == 0:
        print("=" * 72)
        print("EX-11 — coil loading by a conductive half-space: ΔR vs Dodd-Deeds")
        print("=" * 72)
        print(
            f"\n[geometry] a = {FEM_LOOP_RADIUS * 1e3:.0f} mm loop "
            f"(wire r = {FEM_WIRE_RADIUS * 1e3:.1f} mm) at liftoff "
            f"h = {FEM_LIFTOFF * 1e3:.0f} mm over a half-space, in a "
            f"W = {FEM_BOX_HALF_WIDTH} m half-width box"
            f"\n[material] slab σ = {FEM_SIGMA_SLAB} S/m at f = "
            f"{FEM_FREQUENCY_HZ / 1e6:.0f} MHz; skin depth δ = "
            f"{skin_depth * 1e3:.2f} mm = {skin_depth / FEM_LOOP_RADIUS:.3f} a"
            f"\n[caveat] eddy-current regime at 10 MHz — this says NOTHING about "
            f"saline at the Larmor frequency (§2.1)",
            flush=True,
        )

    mesh_started = time.perf_counter()
    msh, cell_tags = _build_fixture(comm)
    mesh_seconds = time.perf_counter() - mesh_started
    n_cells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )

    if comm.rank == 0:
        print(
            f"\n[mesh] {n_cells} cells built in {mesh_seconds:.1f} s", flush=True
        )

    # ---- the two solves: loaded (σ = 100) and free (σ = 0) ------------------
    e_loaded, j_prime, t_loaded = _solve_projected(
        msh, cell_tags, FEM_SIGMA_SLAB, comm
    )
    e_free, _, t_free = _solve_projected(msh, cell_tags, 0.0, comm)

    # I': the projected drive's circuit current, the same cross-section integral
    # the step-3 gate uses (azimuthal current averaged over the loop's length).
    x = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_current_density(1.0)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    current = _reduced_real(ufl.inner(j_prime, phi_hat) * dx_wire, comm) / (
        2.0 * np.pi * FEM_LOOP_RADIUS
    )

    # ΔZ = -(1/I'²) ∫ (E_loaded - E_free)·J' over the WHOLE domain: J' (unlike J)
    # is supported everywhere. J' is real, so inner()'s conjugation is a no-op
    # and this is the reaction integral, not a power.
    reaction = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(e_loaded - e_free, j_prime) * ufl.dx)),
        op=MPI.SUM,
    )
    dz = complex(-reaction / current**2)
    dz_ref = coil_impedance_change(
        FEM_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )
    delta_r_error = abs(dz.real / dz_ref.real - 1.0)

    if comm.rank == 0:
        print(
            f"\n[solve] loaded {t_loaded:.1f} s, free {t_free:.1f} s "
            f"(each incl. the CG1 Poisson projection of the drive)"
            f"\n[drive] I' = {current:.6f} A against the nominal "
            f"{FEM_CURRENT_A:.1f} A"
            f"\n[ΔZ]    FEM   = {dz.real:+.7e} + j({dz.imag:+.7e}) Ω"
            f"\n[ΔZ]    exact = {dz_ref.real:+.7e} + j({dz_ref.imag:+.7e}) Ω"
            f"\n[ΔR]    relative error {delta_r_error:.4%} against the "
            f"{DELTA_R_RTOL:.0%} ceiling (1.5834% on the `MAT-6` step-3 record)"
            f"\n[ΔX]    ratio {dz.imag / dz_ref.imag:.4f} — reported, never gated: "
            f"ΔX is not converged in box size on this fixture (`MAT-6` step 3)",
            flush=True,
        )

    # ---- the anchor ---------------------------------------------------------
    assert dz.real > 0.0, (
        f"a conductive half-space must dissipate, got ΔR = {dz.real:.6e} Ω"
    )
    assert delta_r_error < DELTA_R_RTOL, (
        f"ΔR = {dz.real:.7e} Ω misses the Dodd-Deeds closed form "
        f"{dz_ref.real:.7e} Ω by {delta_r_error:.2%}, against the {DELTA_R_RTOL:.0%} "
        f"ceiling and 1.5834% on the `MAT-6` step-3 record — a regression finding, "
        f"not a tolerance to move"
    )
    assert dz.imag < 0.0, (
        f"the induced currents must expel flux, got ΔX = {dz.imag:.6e} Ω"
    )

    # ---- negative control: the free solve dissipates nothing -----------------
    sigma_loaded = _sigma_field(msh, cell_tags, FEM_SIGMA_SLAB)
    sigma_free = _sigma_field(msh, cell_tags, 0.0)
    power_loaded = _ohmic_power_in_slab(e_loaded, sigma_loaded, msh, cell_tags, comm)
    power_free = _ohmic_power_in_slab(e_free, sigma_free, msh, cell_tags, comm)

    # The independent cross-check: P = ½ ΔR |I'|², computed from the solved field
    # rather than from the reaction integral ΔZ came out of.
    power_from_dr = 0.5 * dz.real * current**2

    if comm.rank == 0:
        print(
            f"\n[control] ohmic power in the slab: loaded "
            f"{power_loaded:.6e} W, free {power_free:.6e} W — the σ = 0 half of "
            f"the same pair, so every other input is shared"
            f"\n[control] ½ ΔR I'² = {power_from_dr:.6e} W from the reaction "
            f"integral vs {power_loaded:.6e} W from the field "
            f"[ratio {power_loaded / power_from_dr:.4f}] — reported, not gated",
            flush=True,
        )

    assert power_loaded > 0.0, (
        f"the loaded solve dissipates no power in the slab: {power_loaded:.6e} W"
    )
    assert power_free == 0.0, (
        f"the σ = 0 control dissipates {power_free:.6e} W — with σ identically "
        f"zero the integrand is zero cell by cell, so anything but exactly 0.0 "
        f"means the control is not lossless"
    )

    # ---- ParaView -----------------------------------------------------------
    j_mag = _current_density_magnitude(e_loaded, sigma_loaded, msh)
    j_mag_free = _current_density_magnitude(e_free, sigma_free, msh)
    j_max = comm.allreduce(
        float(np.max(j_mag.x.array)) if j_mag.x.array.size else 0.0, op=MPI.MAX
    )
    j_max_free = comm.allreduce(
        float(np.max(j_mag_free.x.array)) if j_mag_free.x.array.size else 0.0,
        op=MPI.MAX,
    )
    assert j_max_free == 0.0, (
        f"the lossless control carries eddy current: max |J| = {j_max_free:.6e} A/m²"
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        cell_tags,
        {"J_magnitude": j_mag},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    if comm.rank == 0:
        print(
            f"\n[paraview] wrote {xdmf_path}"
            f"\n[paraview] max |J| = {j_max:.6e} A/m² in the loaded solve, "
            f"{j_max_free:.6e} A/m² in the lossless control"
            "\n[paraview] threshold `CellTags` (3 = lossy slab, 1 = wire) and "
            "colour by `J_magnitude` (A/m²); the induced current hugs the slab "
            "surface under the loop and decays over the skin depth."
            f"\n\nAll assertions hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
