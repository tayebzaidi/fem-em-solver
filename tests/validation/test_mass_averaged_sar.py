"""`MAT-4` step 2: the mass-averaging SAR operator, gated on the step-1 sphere.

Step 1 gated the *pointwise* SAR ``σ|E|²/(2ρ)`` against the quasi-static
lossy-sphere closed form.  This file gates the **averaging operator** that sits
on top of it,

    SAR_avg(x) = ∫_B(x) ½σ|E|² dV  /  ∫_B(x) ρ dV        [W/kg]

— absorbed power in an averaging volume divided by the *mass* of that volume.

**Why 0.05 g and not 1 g (read before changing the mass).**  At ρ = 1000 kg/m³
the step-1 sphere (R = 0.01 m) holds only **4.19 g**, so IEEE C95.3's 1 g
averaging volume is an equivalent ball of radius 6.20 mm = **0.62 R** — larger
than the 0.55 R core where step 1 measured the interior field uniform to
0.07%/0.11% — and 10 g exceeds the phantom entirely.  Growing R is not an
escape: ``|k_in|R = 0.179`` already at σ = 0.57 S/m and it scales linearly, so
R = 0.03 m leaves the closed form's quasi-static regime.  This fixture therefore
gates the operator on ``m_avg = 0.05 g`` ⇒ ball radius **2.29 mm = 0.23 R**,
comfortably inside the uniform core.  **It does not and cannot support an IEEE
C95.3-conformant 1 g/10 g claim** — that needs a phantom large enough to hold
the averaging volume with margin, i.e. the coil+phantom fixture after `GEO-9`
step 2.  `MAT-4` stays 🟡.

**The two anchors.**
1. *The uniform-field identity.*  Where σ, ρ and |E| are all uniform, averaging
   is the identity operator: ``SAR_avg(0)/SAR_point(0) = 1``.  Region-shape
   error cancels between numerator and denominator here (they integrate over the
   same ball), so what is left is field non-uniformity — step 1's measured
   0.07%/0.11% spread over 0.55 R, entering SAR as |E|² and so doubled — plus
   the N1curl point-evaluation error at the centre.  The budget is stated at the
   assertion from those measured parts; see MEASURED_* below.
2. *Kernel mass conservation.*  ``∫_B ρ dV`` equals ``m_avg`` to the accuracy the
   mesh can represent the ball, which is what catches an averaging region that
   silently truncates at a mesh or rank boundary.  The ball is imposed as a UFL
   conditional, so the bound is set by the quadrature degree that samples it —
   measured in the probe run, not assumed.

**Negative control — average at the surface; the ceiling is 2.19, not 2.**
Recentre the ball on ``(0, 0, R)``.  Roughly half of it then lies in the
lossless exterior (σ = 0), which removes that share of the numerator while ρ —
uniform here — leaves the denominator untouched.  The §7 plan put the ceiling at
2, i.e. exactly half; that is the *flat-interface* answer.  The interface is
convex, so the ball keeps **less** than half.  The sphere-sphere lens volume
gives the exact fraction

    f = (8 − 3a/R)/16 = 1/2 − 3a/(16R) = 0.4571      (a/R = 0.2285)

so a kernel that respects σ(x) must separate by ``1/f = 2.1875``, and *that* is
the arithmetic ceiling: no kernel can lose more than all the power outside the
phantom.  The test gates both — the plan's ``> 1.5`` floor, and agreement with
``1/f`` to a band taken from the measurement (`GEO-9` step-1 precedent), which
is the sharper statement: it says the kernel loses the right *amount* of power,
not merely some.  Note this control is why ρ is uniform across the box rather
than air outside: a density-contrasted exterior would cut numerator and
denominator together and the separation would collapse to ~1.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_mass_averaged_sar.py -v -s'
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.sar import (
    averaging_ball_radius,
    build_density_field,
    mass_averaged_sar,
    point_sar,
)

from tests.complex_mode import complex_only
from tests.validation.test_lossy_sphere_sar import (
    BOX_HALF_WIDTH,
    EPSILON_R_SPHERE,
    FREQUENCY_HZ,
    RHO_KG_M3,
    SIGMA_HIGH,
    SPHERE_RADIUS,
    SPHERE_TAG,
    _exact_exterior_numpy,
)

# 0.05 g — see the module docstring for why not 1 g.
AVERAGING_MASS_KG = 5.0e-5
# Step 1's fine mesh, unchanged: h_sphere = R/10 (74019 cells, 5 passed in 39.4 s
# for four solves).  This file runs one solve at one sigma.
H_SPHERE = SPHERE_RADIUS / 10.0
H_FAR = SPHERE_RADIUS / 5.0
QUADRATURE_DEGREE = 12

# Measured inputs to the tolerance budget, all from
# 20260803T020448Z_MAT-4-step1-gate.log at this same operating point:
MEASURED_INTERIOR_SPREAD = 0.0011  # 0.11% of E_z inside 0.55 R at sigma = 0.57
MEASURED_MESHED_SPHERE_ACCURACY = 0.0036  # V_mesh/V_exact = 0.9964 at h = R/10
# Kernel volume defect of the conditional ball at quadrature degree 12,
# measured in 20260804T020419Z_MAT-4-step2-probe.log: V_kernel/V_exact = 0.999599.
MEASURED_KERNEL_VOLUME_DEFECT = 0.0004

# Identity budget, summed from the measured parts above rather than picked:
# the interior field varies by MEASURED_INTERIOR_SPREAD over 0.55 R and SAR goes
# as |E|², which doubles it, plus the kernel's own volume defect.  The ball only
# reaches 0.23 R, so this over-counts the field term.
IDENTITY_BUDGET = 2.0 * MEASURED_INTERIOR_SPREAD + MEASURED_KERNEL_VOLUME_DEFECT
# Mass conservation is gated at step 1's *meshed-sphere* accuracy, per the §7
# plan: the kernel may not represent its own volume worse than the mesh
# represents the phantom it sits in.
KERNEL_MASS_BUDGET = MEASURED_MESHED_SPHERE_ACCURACY


@pytest.fixture(scope="module")
def solved_sphere():
    """One lossy-sphere solve at sigma = 0.57 S/m, reused by every test here."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = MeshGenerator.sphere_in_box_domain(
        sphere_radius=SPHERE_RADIUS,
        box_half_width=BOX_HALF_WIDTH,
        resolution_sphere=H_SPHERE,
        resolution_far=H_FAR,
        comm=comm,
    )
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0),
        cell_tags=cell_tags,
        material_map={
            SPHERE_TAG: HomogeneousMaterial(
                sigma=SIGMA_HIGH, epsilon_r=EPSILON_R_SPHERE
            )
        },
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=_exact_exterior_numpy(SIGMA_HIGH),
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()
    # rho as a DG0 field, not a python float multiplied in afterwards: the
    # averaging denominator is an integral of rho over a region that in general
    # spans materials.  Uniform value here — see the docstring's note on why the
    # negative control requires that.
    rho_field = build_density_field(msh, RHO_KG_M3)
    return {
        "mesh": msh,
        "cell_tags": cell_tags,
        "fields": fields,
        "rho_field": rho_field,
        "comm": comm,
    }


@complex_only
@pytest.mark.integration
def test_mass_averaging_is_the_identity_where_the_field_is_uniform(solved_sphere):
    """``SAR_avg/SAR_point = 1`` at the centre, and ``∫ρ dV = m_avg``."""
    comm = solved_sphere["comm"]
    fields = solved_sphere["fields"]

    radius = averaging_ball_radius(mass_kg=AVERAGING_MASS_KG, rho=RHO_KG_M3)
    centre = (0.0, 0.0, 0.0)

    averaged = mass_averaged_sar(
        fields.e_complex,
        sigma=fields.sigma_field,
        rho=solved_sphere["rho_field"],
        center=centre,
        radius=radius,
        comm=comm,
        quadrature_degree=QUADRATURE_DEGREE,
    )
    pointwise = point_sar(
        fields.e_real,
        fields.e_imag,
        np.array([centre]),
        sigma=SIGMA_HIGH,
        rho=RHO_KG_M3,
        comm=comm,
    )[0]

    ratio = averaged["averaged_sar_w_per_kg"] / pointwise
    volume_exact = 4.0 / 3.0 * np.pi * radius**3
    mass_error = abs(averaged["mass_kg"] - AVERAGING_MASS_KG) / AVERAGING_MASS_KG

    if comm.rank == 0:
        print(
            f"\n[MAT-4 step 2] m_avg = {AVERAGING_MASS_KG * 1e3:.3f} g -> ball radius "
            f"{radius * 1e3:.4f} mm = {radius / SPHERE_RADIUS:.3f} R, "
            f"h_sphere = {H_SPHERE * 1e3:.3f} mm ({radius / H_SPHERE:.2f} cells per radius), "
            f"quadrature degree {QUADRATURE_DEGREE}"
        )
        print(
            f"  centre: SAR_avg = {averaged['averaged_sar_w_per_kg']:.6e} W/kg, "
            f"SAR_point = {pointwise:.6e} W/kg, ratio = {ratio:.6f}"
        )
        print(
            f"  kernel: meshed mass = {averaged['mass_kg']:.6e} kg vs m_avg "
            f"{AVERAGING_MASS_KG:.6e} ({mass_error:.3%}), "
            f"V_kernel/V_exact = {averaged['volume_m3'] / volume_exact:.6f}, "
            f"P_diss(ball) = {averaged['dissipated_power_w']:.6e} W"
        )

    assert abs(ratio - 1.0) < IDENTITY_BUDGET, (
        f"mass averaging is not the identity on a uniform field: "
        f"SAR_avg/SAR_point = {ratio:.6f} at the sphere centre, off by "
        f"{abs(ratio - 1.0):.3%} against a budget of {IDENTITY_BUDGET:.3%} "
        f"(2x the measured {MEASURED_INTERIOR_SPREAD:.2%} interior field spread "
        f"plus the {MEASURED_KERNEL_VOLUME_DEFECT:.2%} kernel volume defect)"
    )

    assert mass_error < KERNEL_MASS_BUDGET, (
        f"the averaging kernel does not conserve mass: meshed "
        f"{averaged['mass_kg']:.6e} kg against m_avg {AVERAGING_MASS_KG:.6e} kg "
        f"({mass_error:.3%}, budget {KERNEL_MASS_BUDGET:.3%}) — the ball is "
        "truncating against the mesh or the quadrature is not resolving it"
    )


@complex_only
@pytest.mark.integration
def test_averaging_at_the_surface_loses_half_the_power(solved_sphere):
    """Negative control: half the ball in the lossless exterior halves SAR_avg."""
    comm = solved_sphere["comm"]
    fields = solved_sphere["fields"]
    radius = averaging_ball_radius(mass_kg=AVERAGING_MASS_KG, rho=RHO_KG_M3)

    def _avg(center):
        return mass_averaged_sar(
            fields.e_complex,
            sigma=fields.sigma_field,
            rho=solved_sphere["rho_field"],
            center=center,
            radius=radius,
            comm=comm,
            quadrature_degree=QUADRATURE_DEGREE,
        )

    centre = _avg((0.0, 0.0, 0.0))
    surface = _avg((0.0, 0.0, SPHERE_RADIUS))
    separation = centre["averaged_sar_w_per_kg"] / surface["averaged_sar_w_per_kg"]

    # Sphere-sphere lens: a ball of radius a centred on the surface of a sphere
    # of radius R keeps the fraction (8 - 3a/R)/16 of its volume inside.  The
    # flat-interface answer 1/2 is the a/R -> 0 limit and overstates it.
    interior_fraction = (8.0 - 3.0 * radius / SPHERE_RADIUS) / 16.0
    geometric_ceiling = 1.0 / interior_fraction
    ceiling_error = abs(separation - geometric_ceiling) / geometric_ceiling

    if comm.rank == 0:
        print(
            f"  surface control: SAR_avg(0,0,R) = "
            f"{surface['averaged_sar_w_per_kg']:.6e} W/kg vs centre "
            f"{centre['averaged_sar_w_per_kg']:.6e} W/kg => separation "
            f"{separation:.4f} against the lens ceiling 1/f = "
            f"{geometric_ceiling:.4f} (f = {interior_fraction:.4f}) "
            f"[{ceiling_error:.2%}]"
        )
        print(
            f"    surface ball mass {surface['mass_kg']:.6e} kg "
            f"({surface['mass_kg'] / AVERAGING_MASS_KG:.4f} of m_avg — uniform rho, "
            f"so the denominator does not move)"
        )

    # The plan's floor: the kernel must lose most of the exterior power at all.
    assert separation > 1.5, (
        f"averaging at the sphere surface returned only {separation:.4f}x less SAR "
        "than at the centre; the exterior part of the ball is lossless, so a "
        f"kernel that respects sigma(x) must lose ~{1 - interior_fraction:.1%} of "
        f"its numerator there (ceiling {geometric_ceiling:.4f})"
    )
    # The sharper statement: the *amount* lost is the lens fraction.  Band from
    # the measurement — 1.00% on the probe/gate runs at h = R/10, whose residue is
    # the interior field's own variation over the cap plus the kernel's
    # quadrature; 5% is that measurement with room, not a round number chosen
    # before it.
    assert ceiling_error < 0.05, (
        f"the surface separation {separation:.4f} misses the sphere-sphere lens "
        f"ceiling {geometric_ceiling:.4f} by {ceiling_error:.2%}: the kernel is "
        "not losing the geometrically correct share of the numerator outside the "
        f"phantom (interior volume fraction f = {interior_fraction:.4f})"
    )
