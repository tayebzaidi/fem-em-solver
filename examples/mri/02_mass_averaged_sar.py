"""Example (`EX-3`): mass-averaged SAR at the C95.3 masses, point vs 1 g vs 10 g.

The `§5.4` ramp entry for `MAT-4` step 3. Nothing under ``examples/`` has ever
shown a SAR quantity, mass averaging, or any complex-build post quantity — and
mass-averaged SAR is exactly what the operator eyeballs when a future
coil+phantom SAR number looks wrong. This example puts the averaging operator
and the field it averages on screen, and asserts the step-3 record while it
does it.

**Imposed field, no solve — and no C95.3 claim.** `MAT-4` step 3 gated the
*averaging operator*, and that identity is a statement about a uniform field:
on a uniform ``E`` the mass-averaged SAR must equal the pointwise SAR exactly,
whatever the ball radius. So the uniform interior phasor is *imposed* on the
N1curl space (degree-1 Nedelec contains the constants exactly, so the imposed
field carries no interpolation error) and every residual below belongs to the
averaging kernel. An IEEE C95.3-conformant 1 g/10 g SAR *number* needs a solved
coil+phantom field, which stays unlicensed (PROJECT_PLAN §2.1): SAR-on-a-coil
is not gated, `MAT-4` stays 🟡, and nothing here changes that.

**It asserts, it does not merely render.** Every constant is imported from the
gate — ``tests/validation/test_mass_averaged_sar_standard_masses.py`` — so the
example and the landed test cannot drift apart:

* *The uniform-field identity at both standard masses:* ``SAR_avg/SAR_point``
  at 1 g and 10 g, gated at ``|ratio - 1| < 0.5%`` (1.00000000 on record).
* *Kernel mass conservation:* ``∫_B rho dV = m_avg`` to < 0.1% at both masses
  (0.0120% at 1 g, 0.0044% at 10 g on record). This is what catches an
  averaging region silently truncating at a mesh or rank boundary.
* *The pointwise path against its closed form:* ``sigma|E|²/(2 rho)`` is known
  exactly on a uniform field, and the evaluated value must match it to 1e-12
  (4.96e-16 on record).
* *The DG0 field ParaView shows is the same quantity:* its sphere-averaged
  value matches the same closed form to 1e-12.

**Negative control — the 1 g ball on the surface.** Re-centred on ``(0, 0, R)``
roughly half the ball lies in the lossless exterior, which removes that share
of the numerator while uniform ``rho`` leaves the denominator untouched. The
sphere-sphere lens fraction is recomputed for *this* geometry,
``f = (8 - 3a/R)/16``, so the ceiling ``1/f = 2.1682`` is derived here rather
than carried over (2.1894 measured on record, floor > 1.5). A kernel blind to
``sigma(x)`` would return 1.0 instead.

**Quadrature degree 16, and it is not a free parameter.** Degree 12 — the
library default — is measured *insufficient* at this ball-to-mesh ratio
(0.3008% kernel-mass error at 1 g, three times the budget); the step-3 sweep
picked 16 as the smallest degree at which every ball placement sits an order of
magnitude inside the 0.1% budget. The example imports ``QUADRATURE_DEGREE``
from the test rather than restating it.

Run it through the example runner (the ``mri:`` group sources the complex build
automatically)::

    ./run_examples.sh -e mri:2

Output lands in ``examples/mri/paraview_output/``: open
``mri_02_mass_averaged_sar_combined.xdmf``, threshold on ``CellTags``
(1 = lossy sphere, everything else is lossless air) and colour by ``SAR``.

Measured 2026-08-08 at ``-n 2`` (``20260808T020414Z_EX-3-gate.log``, exit 0,
13.4 s example-internal): 74 216 cells, mesh 7.1 s, ratio ``1.00000000`` at
both masses, kernel mass 0.0120% / 0.0044%, pointwise 4.96e-16 and the DG0
field 1.32e-15 against the closed form, surface separation 2.1894 vs the
recomputed ceiling 2.1681 (0.98%) — every number the `MAT-4` step-3 record.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

# The gated constants live in the test that closed `MAT-4` step 3, and the §7
# `EX-3` plan requires importing them rather than restating them — a restated
# quadrature degree or budget is exactly how an example drifts off the gate it
# claims to reproduce. The runner puts only ``src`` on PYTHONPATH, so the repo
# root goes on sys.path here.
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
from fem_em_solver.post.sar import (  # noqa: E402
    averaging_ball_radius,
    build_density_field,
    mass_averaged_sar,
    point_sar,
)

from tests.validation.test_lossy_sphere_sar import (  # noqa: E402
    EPSILON_R_SPHERE,
    RHO_KG_M3,
    SIGMA_HIGH,
    SPHERE_TAG,
    _interior_field_closed_form,
)
from tests.validation.test_mass_averaged_sar_standard_masses import (  # noqa: E402
    BOX_HALF_WIDTH,
    H_FAR,
    H_SPHERE,
    IDENTITY_BUDGET,
    KERNEL_MASS_BUDGET,
    ONE_GRAM_KG,
    QUADRATURE_DEGREE,
    SPHERE_RADIUS,
    TEN_GRAM_KG,
)

#: The pointwise path and the DG0 field are both evaluating a closed form that
#: is exact on a uniform field; anything above round-off is a defect, not a
#: discretisation error. 4.96e-16 on record for the pointwise path.
CLOSED_FORM_RTOL = 1e-12
#: Pre-decided in the §7 plan: a kernel that respects ``sigma(x)`` must lose the
#: exterior share of its numerator at the surface placement. A ``sigma``-blind
#: kernel returns 1.0.
SEPARATION_FLOOR = 1.5
#: ...and it must lose the *geometrically correct* share, as step 3 gated.
CEILING_RTOL = 0.05

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "mri_02_mass_averaged_sar"

MASSES = (("1 g", ONE_GRAM_KG), ("10 g", TEN_GRAM_KG))


def _build_uniform_field_sphere(comm):
    """`MAT-4` step 3's fixture, rebuilt: R = 0.03 m sphere, uniform E imposed."""
    msh, cell_tags, _ = MeshGenerator.sphere_in_box_domain(
        sphere_radius=SPHERE_RADIUS,
        box_half_width=BOX_HALF_WIDTH,
        resolution_sphere=H_SPHERE,
        resolution_far=H_FAR,
        comm=comm,
    )

    # sigma(x) through the production DG0 builder: lossless air outside, saline
    # inside. The negative control is only meaningful because sigma is a field.
    sigma_field, _ = build_material_fields(
        msh,
        HomogeneousMaterial(sigma=0.0, epsilon_r=1.0),
        cell_tags=cell_tags,
        material_map={
            SPHERE_TAG: HomogeneousMaterial(
                sigma=SIGMA_HIGH, epsilon_r=EPSILON_R_SPHERE
            )
        },
    )

    e_uniform = complex(_interior_field_closed_form(SIGMA_HIGH))

    def _uniform(x: np.ndarray) -> np.ndarray:
        values = np.zeros((3, x.shape[1]), dtype=np.complex128)
        values[2, :] = e_uniform
        return values

    n1curl = fem.functionspace(msh, ("N1curl", 1))
    e_complex = fem.Function(n1curl, name="E")
    e_complex.interpolate(_uniform)
    e_complex.x.scatter_forward()

    # Split parts exactly as TimeHarmonicSolver builds them, so point_sar sees
    # the same DG interpolation production would hand it.
    dg = fem.functionspace(msh, ("DG", 1, (3,)))
    e_dg = fem.Function(dg, name="E_dg")
    e_dg.interpolate(e_complex)
    e_real = fem.Function(dg, name="E_real")
    e_real.x.array[:] = np.real(e_dg.x.array)
    e_imag = fem.Function(dg, name="E_imag")
    e_imag.x.array[:] = np.imag(e_dg.x.array)
    e_real.x.scatter_forward()
    e_imag.x.scatter_forward()

    return {
        "mesh": msh,
        "cell_tags": cell_tags,
        "sigma_field": sigma_field,
        "rho_field": build_density_field(msh, RHO_KG_M3),
        "e_complex": e_complex,
        "e_real": e_real,
        "e_imag": e_imag,
        "e_uniform": e_uniform,
    }


def _pointwise_sar_field(fixture):
    """``sigma(x)|E|²/(2 rho(x))`` as a DG0 function — what ParaView colours by.

    ``ufl.inner`` conjugates its second argument in complex UFL, so this is the
    same expression :func:`~fem_em_solver.post.sar.mri_02_mass_averaged_sar` integrates,
    not a real-mode look-alike. The imaginary part is identically zero by
    construction and is dropped so the array ParaView reads is unambiguous.
    """
    msh = fixture["mesh"]
    e = fixture["e_complex"]
    expr = (
        0.5
        * fixture["sigma_field"]
        * ufl.inner(e, e)
        / fixture["rho_field"]
    )

    dg0 = fem.functionspace(msh, ("DG", 0))
    sar = fem.Function(dg0, name="SAR")
    sar.interpolate(fem.Expression(expr, dg0.element.interpolation_points))
    sar.x.array[:] = np.real(sar.x.array)
    sar.x.scatter_forward()
    return sar


def _sphere_average(field, fixture, comm):
    """``∫_sphere f dV / ∫_sphere dV`` — both integrals reduced before dividing.

    ``assemble_scalar`` is rank-local; a rank holding no sphere cell contributes
    zero to both sums and the ratio is only meaningful after the reduction.
    """
    msh = fixture["mesh"]
    dx_sphere = ufl.Measure(
        "dx", domain=msh, subdomain_data=fixture["cell_tags"], subdomain_id=(SPHERE_TAG,)
    )
    one = fem.Constant(msh, default_scalar_type(1.0))
    integral = comm.allreduce(
        fem.assemble_scalar(fem.form(field * dx_sphere)), op=MPI.SUM
    )
    volume = comm.allreduce(
        fem.assemble_scalar(fem.form(one * dx_sphere)), op=MPI.SUM
    )
    return float(np.real(integral)) / float(np.real(volume)), float(np.real(volume))


def _averaged(fixture, comm, *, centre, radius):
    return mass_averaged_sar(
        fixture["e_complex"],
        sigma=fixture["sigma_field"],
        rho=fixture["rho_field"],
        center=centre,
        radius=radius,
        comm=comm,
        quadrature_degree=QUADRATURE_DEGREE,
    )


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "this example needs the complex DolfinX build "
            "(source /usr/local/bin/dolfinx-complex-mode); the runner's `mri:` "
            "group sources it automatically"
        )

    if comm.rank == 0:
        print("=" * 72)
        print("EX-3 — mass-averaged SAR: point vs 1 g vs 10 g on the standard sphere")
        print("=" * 72)
        print(
            f"\n[geometry] R = {SPHERE_RADIUS * 1e3:.1f} mm sphere "
            f"({4.0 / 3.0 * np.pi * SPHERE_RADIUS**3 * RHO_KG_M3 * 1e3:.0f} g of "
            f"water) in a {BOX_HALF_WIDTH * 2e3:.0f} mm box"
            f"\n[material] sigma = {SIGMA_HIGH} S/m inside, 0 outside (a DG0 field, "
            f"not a global); rho = {RHO_KG_M3:.0f} kg/m^3"
            f"\n[caveat] the field is IMPOSED, not solved — this gates the averaging "
            f"OPERATOR only. SAR on a coil is unlicensed (§2.1); no C95.3 claim.",
            flush=True,
        )

    mesh_started = time.perf_counter()
    fixture = _build_uniform_field_sphere(comm)
    mesh_seconds = time.perf_counter() - mesh_started

    msh = fixture["mesh"]
    n_cells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    e_uniform = fixture["e_uniform"]

    # The closed form the whole example is measured against: on a uniform field
    # sigma|E|^2/(2 rho) is known exactly, with no discretisation in it.
    sar_closed_form = SIGMA_HIGH * abs(e_uniform) ** 2 / (2.0 * RHO_KG_M3)

    if comm.rank == 0:
        print(
            f"\n[mesh] {n_cells} cells built in {mesh_seconds:.1f} s "
            f"(h_sphere = {H_SPHERE * 1e3:.2f} mm)"
            f"\n[field] imposed uniform E_z = {e_uniform:.6e} V/m "
            f"(|E| = {abs(e_uniform):.6e} V/m), no solve"
            f"\n[closed form] sigma|E|^2/(2 rho) = {sar_closed_form:.8e} W/kg",
            flush=True,
        )

    # ---- the pointwise path, and the field ParaView will show ---------------
    pointwise = point_sar(
        fixture["e_real"],
        fixture["e_imag"],
        np.array([(0.0, 0.0, 0.0)]),
        sigma=SIGMA_HIGH,
        rho=RHO_KG_M3,
        comm=comm,
    )[0]
    point_error = abs(pointwise - sar_closed_form) / sar_closed_form

    sar_field = _pointwise_sar_field(fixture)
    field_mean, sphere_volume = _sphere_average(sar_field, fixture, comm)
    field_error = abs(field_mean - sar_closed_form) / sar_closed_form

    if comm.rank == 0:
        print(
            f"\n[point]  SAR_point(0,0,0) = {pointwise:.8e} W/kg "
            f"vs closed form [{point_error:.2e} relative]"
            f"\n[field]  DG0 SAR averaged over the sphere = {field_mean:.8e} W/kg "
            f"vs closed form [{field_error:.2e} relative]"
            f"\n[field]  (V_sphere = {sphere_volume:.6e} m^3; the DG0 array is what "
            f"ParaView colours by, so it is checked, not just written)",
            flush=True,
        )

    assert point_error < CLOSED_FORM_RTOL, (
        f"the evaluated pointwise SAR {pointwise:.8e} W/kg misses the closed form "
        f"{sar_closed_form:.8e} W/kg by {point_error:.2e} — on a uniform field "
        f"sigma|E|^2/(2 rho) has no discretisation error in it, so this is an "
        f"evaluation-path defect, not a mesh effect"
    )
    assert field_error < CLOSED_FORM_RTOL, (
        f"the DG0 SAR field averages to {field_mean:.8e} W/kg over the sphere "
        f"against the closed form {sar_closed_form:.8e} W/kg ({field_error:.2e}) — "
        f"the array ParaView shows is not the quantity the operator integrates"
    )

    # ---- anchor: the averaging identity at 1 g and 10 g ---------------------
    for label, mass_kg in MASSES:
        radius = averaging_ball_radius(mass_kg=mass_kg, rho=RHO_KG_M3)
        averaged = _averaged(fixture, comm, centre=(0.0, 0.0, 0.0), radius=radius)

        ratio = averaged["averaged_sar_w_per_kg"] / pointwise
        volume_exact = 4.0 / 3.0 * np.pi * radius**3
        mass_error = abs(averaged["mass_kg"] - mass_kg) / mass_kg

        if comm.rank == 0:
            print(
                f"\n[{label}] ball radius {radius * 1e3:.4f} mm = "
                f"{radius / SPHERE_RADIUS:.3f} R, {radius / H_SPHERE:.2f} cells per "
                f"radius, quadrature degree {QUADRATURE_DEGREE} (imported from the "
                f"step-3 gate; the default 12 is measured insufficient here)"
                f"\n[{label}]   SAR_avg = {averaged['averaged_sar_w_per_kg']:.8e} W/kg,"
                f" SAR_point = {pointwise:.8e} W/kg, ratio = {ratio:.8f} "
                f"[{abs(ratio - 1.0):.3%} vs the {IDENTITY_BUDGET:.1%} budget]"
                f"\n[{label}]   kernel: meshed mass = {averaged['mass_kg']:.8e} kg vs "
                f"m_avg {mass_kg:.6e} kg [{mass_error:.4%} vs "
                f"{KERNEL_MASS_BUDGET:.1%}], V_kernel/V_exact = "
                f"{averaged['volume_m3'] / volume_exact:.6f}",
                flush=True,
            )

        assert abs(ratio - 1.0) < IDENTITY_BUDGET, (
            f"mass averaging is not the identity on a uniform field at {label}: "
            f"SAR_avg/SAR_point = {ratio:.6f}, off by {abs(ratio - 1.0):.3%} against "
            f"the {IDENTITY_BUDGET:.1%} step-3 budget"
        )
        assert mass_error < KERNEL_MASS_BUDGET, (
            f"the averaging kernel does not conserve mass at {label}: meshed "
            f"{averaged['mass_kg']:.6e} kg against m_avg {mass_kg:.6e} kg "
            f"({mass_error:.4%}, budget {KERNEL_MASS_BUDGET:.1%}) — the ball is "
            f"truncating against the mesh or the quadrature is not resolving it"
        )

    # ---- negative control: the 1 g ball on the surface ----------------------
    radius_1g = averaging_ball_radius(mass_kg=ONE_GRAM_KG, rho=RHO_KG_M3)
    centre_1g = _averaged(fixture, comm, centre=(0.0, 0.0, 0.0), radius=radius_1g)
    surface_1g = _averaged(
        fixture, comm, centre=(0.0, 0.0, SPHERE_RADIUS), radius=radius_1g
    )
    separation = (
        centre_1g["averaged_sar_w_per_kg"] / surface_1g["averaged_sar_w_per_kg"]
    )

    # Recomputed for THIS geometry: a ball of radius a centred on the surface of
    # a sphere of radius R keeps (8 - 3a/R)/16 of its volume inside.
    interior_fraction = (8.0 - 3.0 * radius_1g / SPHERE_RADIUS) / 16.0
    geometric_ceiling = 1.0 / interior_fraction
    ceiling_error = abs(separation - geometric_ceiling) / geometric_ceiling

    if comm.rank == 0:
        print(
            f"\n[control] 1 g ball re-centred on (0,0,R), a/R = "
            f"{radius_1g / SPHERE_RADIUS:.4f}: SAR_avg = "
            f"{surface_1g['averaged_sar_w_per_kg']:.8e} W/kg vs centre "
            f"{centre_1g['averaged_sar_w_per_kg']:.8e} W/kg"
            f"\n[control] separation = {separation:.4f} against the recomputed lens "
            f"ceiling 1/f = {geometric_ceiling:.4f} (f = {interior_fraction:.4f}) "
            f"[{ceiling_error:.2%}], floor {SEPARATION_FLOOR}"
            f"\n[control] surface ball mass {surface_1g['mass_kg']:.6e} kg "
            f"({surface_1g['mass_kg'] / ONE_GRAM_KG:.4f} of m_avg — uniform rho, so "
            f"the denominator does not move; a sigma-blind kernel returns 1.0)",
            flush=True,
        )

    assert separation > SEPARATION_FLOOR, (
        f"averaging the 1 g ball at the sphere surface returned only "
        f"{separation:.4f}x less SAR than at the centre; the exterior part of the "
        f"ball is lossless, so a kernel that respects sigma(x) must lose "
        f"~{1 - interior_fraction:.1%} of its numerator there "
        f"(ceiling {geometric_ceiling:.4f})"
    )
    assert ceiling_error < CEILING_RTOL, (
        f"the surface separation {separation:.4f} misses the recomputed "
        f"sphere-sphere lens ceiling {geometric_ceiling:.4f} by {ceiling_error:.2%}: "
        f"the kernel is not losing the geometrically correct share of the numerator "
        f"outside the phantom (f = {interior_fraction:.4f})"
    )

    # ---- ParaView ----------------------------------------------------------
    OUTPUT_DIR.mkdir(exist_ok=True)
    # Mesh first, then the tags and the field, or ParaView has nothing to bind
    # the arrays to.
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        fixture["cell_tags"],
        {"SAR": sar_field},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    if comm.rank == 0:
        print(
            f"\n[paraview] wrote {xdmf_path}"
            "\n[paraview] threshold `CellTags` (1 = lossy sphere) and colour by "
            "`SAR` (W/kg); outside the sphere sigma = 0, so SAR is identically zero."
            f"\n\nAll identities hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
