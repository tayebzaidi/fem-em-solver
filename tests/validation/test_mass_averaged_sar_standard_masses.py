"""`MAT-4` step 3: the mass-averaging operator at the C95.3 masses, 1 g and 10 g.

Step 2 gated the averaging operator
(:func:`~fem_em_solver.post.sar.mass_averaged_sar`) at ``m = 0.05 g``, not
because the operator was suspect at 1 g but because the *sphere* was too small:
the step-1 fixture (R = 0.01 m, 4.19 g of water) cannot contain a 1 g ball with
margin, and 10 g exceeds it entirely.  The limit was the sizing.  This file
closes that gap on a sphere sized for the standard,

    R = 0.03 m, rho = 1000 kg/m^3   =>   1 g ball  r = 6.204e-3 m = 0.207 R
                                         10 g ball r = 1.337e-2 m = 0.446 R

so both averaging volumes sit inside with clearance (the 10 g ball's surface
clearance is R - r = 1.24 ball radii).  0.207 R is the same *relative* ball size
step 2 gated at 0.05 g, which is what makes the two runs comparable.

**No solve — deliberately.**  The subject here is the operator, and the operator
identity is a statement about a uniform field.  Growing R to 0.03 m puts the
step-1 closed form out of its quasi-static regime (``|k_in|R`` scales linearly,
so it is ~3x step 1's 0.179 and the O((k_in R)^2) model error ~9x), so a solved
field would only add error that has nothing to do with averaging.  The uniform
interior phasor is therefore *imposed* on the N1curl space directly.  Degree-1
Nedelec contains the constants exactly, so the imposed field carries no
interpolation error and every residual below belongs to the averaging kernel.
The value imposed is the step-1 interior closed form at sigma = 0.57 S/m, a
uniform complex vector, so the ``|E|^2`` path is exercised on both axes.

**The two anchors** (both pre-decided in the PROJECT_PLAN §7 step-3 plan).
1. *The uniform-field identity at both masses:* ``SAR_avg/SAR_point = 1``,
   gated at ``|ratio - 1| < 0.5%`` — 2x the step-2 measured-parts budget of
   0.26%, sized up for the coarser ball-to-mesh ratio here (2.07 cells per 1 g
   ball radius against step 2's 2.29).  On record at 0.05 g: 0.999846.
2. *Kernel mass conservation:* ``∫_B rho dV = m_avg`` to < 0.1% at both
   masses (0.040% on record at 0.05 g).  This is what catches an averaging
   region silently truncating at a mesh or rank boundary.  The first gate run
   read **0.3008% at 1 g** against this budget; the probe sweep below showed
   that is the *quadrature degree*, not the operator — the ball is a UFL
   conditional and degree 12 under-resolves its surface at 2.07 cells per ball
   radius.  See ``QUADRATURE_DEGREE``.

**Negative control — the 1 g ball on the surface.**  Re-centred on
``(0, 0, R)``, roughly half the ball lies in the lossless exterior, which
removes that share of the numerator while uniform rho leaves the denominator
untouched.  The sphere-sphere lens fraction is recomputed for *this* R and *this*
ball radius before anything is asserted (step 2's 2.1875 belongs to step 2's
geometry):

    f = (8 - 3a/R)/16 = 0.4612   (a/R = 0.2068)  =>  1/f = 2.1682

and both the plan's ``> 1.5`` floor and 5% agreement with the recomputed ``1/f``
are gated, as step 2 gated them.  (The §7 sentence also says "centre the 1 g ball
at R - r_ball"; that placement puts the ball wholly inside the conductor, where
the ratio is 1 by construction and there is no lens fraction to compare against
— the ``(8 - 3a/R)/16`` formula the same sentence invokes is the centre-on-the-
surface case, which is what step 2 measured and what is used here.)

**Does not close `MAT-4`.**  An IEEE C95.3-conformant 1 g/10 g SAR *claim* needs
a solved coil+phantom field, which stays unlicensed (§2.1).  This closes the
operator's sizing gap only; the chunk stays 🟡.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_mass_averaged_sar_standard_masses.py -v -s'
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core import HomogeneousMaterial
from fem_em_solver.core.time_harmonic import build_material_fields
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.sar import (
    averaging_ball_radius,
    build_density_field,
    mass_averaged_sar,
    point_sar,
)

from tests.complex_mode import complex_only
from tests.validation.test_lossy_sphere_sar import (
    EPSILON_R_SPHERE,
    RHO_KG_M3,
    SIGMA_HIGH,
    SPHERE_TAG,
    _interior_field_closed_form,
)

# Sized for the standard, not for the closed form: R holds 113 g of water, so
# both C95.3 masses fit with clearance.  Everything else is step 1's geometry
# scaled by 3, which keeps the cell count (~74k) and the ball-to-cell ratio
# comparable to step 2's.
SPHERE_RADIUS = 0.03
BOX_HALF_WIDTH = 0.06
H_SPHERE = SPHERE_RADIUS / 10.0
H_FAR = SPHERE_RADIUS / 5.0
# Chosen by measurement, not carried over from step 2.  Step 2's default of 12
# was measured at *its* geometry (ball radius 2.29 cells); at the 1 g ball here
# (2.07 cells) it is under-resolved — the kernel is a UFL conditional, so the
# degree sets how well the quadrature resolves the ball's own surface.  Sweep
# from 20260807T183401Z_MAT-4-step3-probe.log, kernel mass error:
#
#   degree      8        12        16        20        24        30
#   1 g     0.7637%   0.3008%   0.0120%   0.0145%   0.0039%   0.0036%
#   10 g    0.1523%   0.0187%   0.0044%   0.0069%   0.0044%   0.0021%
#   1 g @R  0.4294%   0.0291%   0.0027%   0.0002%   0.0456%   0.0038%
#
# The sequence is not monotone — the residual is sampling noise of where the
# ball surface falls among the quadrature points, not a truncation order — so
# the degree is picked as the smallest one at which *every* placement in the
# sweep sits an order of magnitude inside the 0.1% mass budget.  That is 16.
# The budget itself does not move; only the resolution of the region does.
QUADRATURE_DEGREE = 16

ONE_GRAM_KG = 1.0e-3
TEN_GRAM_KG = 1.0e-2

# Pre-decided in the §7 step-3 plan, from the step-2 measurements:
# 2x the 0.26% measured-parts budget, for the coarser ball-to-mesh ratio here.
IDENTITY_BUDGET = 0.005
# 0.040% on record at 0.05 g; the kernel may not lose an order of magnitude of
# its own mass by being asked to represent a *larger* ball on a coarser mesh.
KERNEL_MASS_BUDGET = 0.001


@pytest.fixture(scope="module")
def uniform_field_sphere():
    """The R = 0.03 m sphere with a uniform complex E imposed — no solve."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = MeshGenerator.sphere_in_box_domain(
        sphere_radius=SPHERE_RADIUS,
        box_half_width=BOX_HALF_WIDTH,
        resolution_sphere=H_SPHERE,
        resolution_far=H_FAR,
        comm=comm,
    )

    # sigma(x) through the production DG0 builder: lossless air outside, saline
    # inside.  The negative control is only meaningful because sigma is a field.
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

    n_cells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    if comm.rank == 0:
        print(
            f"\n[MAT-4 step 3] R = {SPHERE_RADIUS * 1e3:.1f} mm, "
            f"h_sphere = {H_SPHERE * 1e3:.2f} mm, {n_cells} cells, "
            f"imposed uniform E_z = {e_uniform:.6e} V/m "
            f"(|E| = {abs(e_uniform):.6e}), no solve"
        )

    return {
        "mesh": msh,
        "cell_tags": cell_tags,
        "sigma_field": sigma_field,
        "rho_field": build_density_field(msh, RHO_KG_M3),
        "e_complex": e_complex,
        "e_real": e_real,
        "e_imag": e_imag,
        "e_uniform": e_uniform,
        "comm": comm,
    }


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize(
    "label, mass_kg", [("1 g", ONE_GRAM_KG), ("10 g", TEN_GRAM_KG)]
)
def test_mass_averaging_is_the_identity_at_the_standard_masses(
    uniform_field_sphere, label, mass_kg
):
    """``SAR_avg/SAR_point = 1`` and ``∫_B rho dV = m_avg`` at 1 g and 10 g."""
    comm = uniform_field_sphere["comm"]
    radius = averaging_ball_radius(mass_kg=mass_kg, rho=RHO_KG_M3)
    centre = (0.0, 0.0, 0.0)

    averaged = mass_averaged_sar(
        uniform_field_sphere["e_complex"],
        sigma=uniform_field_sphere["sigma_field"],
        rho=uniform_field_sphere["rho_field"],
        center=centre,
        radius=radius,
        comm=comm,
        quadrature_degree=QUADRATURE_DEGREE,
    )
    pointwise = point_sar(
        uniform_field_sphere["e_real"],
        uniform_field_sphere["e_imag"],
        np.array([centre]),
        sigma=SIGMA_HIGH,
        rho=RHO_KG_M3,
        comm=comm,
    )[0]

    ratio = averaged["averaged_sar_w_per_kg"] / pointwise
    volume_exact = 4.0 / 3.0 * np.pi * radius**3
    mass_error = abs(averaged["mass_kg"] - mass_kg) / mass_kg

    # The closed-form pointwise value, independent of the evaluation path: the
    # imposed field is uniform, so sigma|E|^2/(2 rho) is known exactly here.
    sar_closed_form = (
        SIGMA_HIGH * abs(uniform_field_sphere["e_uniform"]) ** 2 / (2.0 * RHO_KG_M3)
    )
    point_error = abs(pointwise - sar_closed_form) / sar_closed_form

    if comm.rank == 0:
        print(
            f"  [{label}] ball radius {radius * 1e3:.4f} mm = "
            f"{radius / SPHERE_RADIUS:.3f} R, {radius / H_SPHERE:.2f} cells per "
            f"radius, quadrature degree {QUADRATURE_DEGREE}"
        )
        print(
            f"    SAR_avg = {averaged['averaged_sar_w_per_kg']:.8e} W/kg, "
            f"SAR_point = {pointwise:.8e} W/kg "
            f"(closed form {sar_closed_form:.8e}, {point_error:.2e}), "
            f"ratio = {ratio:.8f} [{abs(ratio - 1.0):.3%}]"
        )
        print(
            f"    kernel: meshed mass = {averaged['mass_kg']:.8e} kg vs m_avg "
            f"{mass_kg:.6e} ({mass_error:.4%}), V_kernel/V_exact = "
            f"{averaged['volume_m3'] / volume_exact:.6f}"
        )

    assert abs(ratio - 1.0) < IDENTITY_BUDGET, (
        f"mass averaging is not the identity on a uniform field at {label}: "
        f"SAR_avg/SAR_point = {ratio:.6f}, off by {abs(ratio - 1.0):.3%} against "
        f"the {IDENTITY_BUDGET:.1%} budget (2x the step-2 measured-parts budget "
        f"of 0.26%); ball radius {radius / SPHERE_RADIUS:.3f} R"
    )
    assert mass_error < KERNEL_MASS_BUDGET, (
        f"the averaging kernel does not conserve mass at {label}: meshed "
        f"{averaged['mass_kg']:.6e} kg against m_avg {mass_kg:.6e} kg "
        f"({mass_error:.4%}, budget {KERNEL_MASS_BUDGET:.1%}) — the ball is "
        "truncating against the mesh or the quadrature is not resolving it"
    )


@complex_only
@pytest.mark.integration
def test_one_gram_ball_at_the_surface_loses_the_lens_fraction(uniform_field_sphere):
    """Negative control: the 1 g ball on the surface keeps only ``f`` of its power."""
    comm = uniform_field_sphere["comm"]
    radius = averaging_ball_radius(mass_kg=ONE_GRAM_KG, rho=RHO_KG_M3)

    def _avg(center):
        return mass_averaged_sar(
            uniform_field_sphere["e_complex"],
            sigma=uniform_field_sphere["sigma_field"],
            rho=uniform_field_sphere["rho_field"],
            center=center,
            radius=radius,
            comm=comm,
            quadrature_degree=QUADRATURE_DEGREE,
        )

    centre = _avg((0.0, 0.0, 0.0))
    surface = _avg((0.0, 0.0, SPHERE_RADIUS))
    separation = centre["averaged_sar_w_per_kg"] / surface["averaged_sar_w_per_kg"]

    # Recomputed for THIS geometry, not carried over from step 2 (2.1875 at
    # a/R = 0.2285).  Sphere-sphere lens: a ball of radius a centred on the
    # surface of a sphere of radius R keeps (8 - 3a/R)/16 of its volume inside.
    interior_fraction = (8.0 - 3.0 * radius / SPHERE_RADIUS) / 16.0
    geometric_ceiling = 1.0 / interior_fraction
    ceiling_error = abs(separation - geometric_ceiling) / geometric_ceiling

    if comm.rank == 0:
        print(
            f"  surface control (1 g, a/R = {radius / SPHERE_RADIUS:.4f}): "
            f"SAR_avg(0,0,R) = {surface['averaged_sar_w_per_kg']:.8e} W/kg vs "
            f"centre {centre['averaged_sar_w_per_kg']:.8e} W/kg => separation "
            f"{separation:.4f} against the recomputed lens ceiling 1/f = "
            f"{geometric_ceiling:.4f} (f = {interior_fraction:.4f}) "
            f"[{ceiling_error:.2%}]"
        )
        print(
            f"    surface ball mass {surface['mass_kg']:.6e} kg "
            f"({surface['mass_kg'] / ONE_GRAM_KG:.4f} of m_avg — uniform rho, so "
            "the denominator does not move)"
        )

    assert separation > 1.5, (
        f"averaging the 1 g ball at the sphere surface returned only "
        f"{separation:.4f}x less SAR than at the centre; the exterior part of the "
        f"ball is lossless, so a kernel that respects sigma(x) must lose "
        f"~{1 - interior_fraction:.1%} of its numerator there "
        f"(ceiling {geometric_ceiling:.4f})"
    )
    assert ceiling_error < 0.05, (
        f"the surface separation {separation:.4f} misses the recomputed "
        f"sphere-sphere lens ceiling {geometric_ceiling:.4f} by "
        f"{ceiling_error:.2%}: the kernel is not losing the geometrically correct "
        f"share of the numerator outside the phantom (f = {interior_fraction:.4f})"
    )
