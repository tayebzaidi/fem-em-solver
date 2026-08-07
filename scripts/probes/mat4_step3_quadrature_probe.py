"""`MAT-4` step 3 probe: is the averaging kernel's mass defect quadrature-limited?

The step-3 gate run (`20260807T183256Z_MAT-4-step3-gate.log`) measured the
uniform-field identity as *exact* at both standard masses (ratio 1.00000000)
but the 1 g kernel mass at **0.3008%** against a 0.1% budget, while the 10 g
ball came in at 0.0187%.  Both balls sit in the same mesh, so the difference is
not truncation — it is how well the quadrature rule resolves the UFL
``conditional`` that defines the ball.  ``mass_averaged_sar``'s docstring says
the degree "sets the accuracy of the region itself, not of the integrand", and
step 2's default 12 was chosen by measurement at its own geometry (ball radius
2.29 cells); this sweep asks the same question at 2.07 and 4.46 cells.

Prints ``V_kernel/V_exact`` and the mass error for both masses across a degree
sweep, so the gate's degree is a measured choice and not a guess.  No solve —
sigma and E never enter; only ``∫_B rho dV``.

Run::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src timeout 300 mpiexec -n 2 python3 \\
       scripts/probes/mat4_step3_quadrature_probe.py'
"""

from __future__ import annotations

import numpy as np
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.sar import averaging_ball_radius, build_density_field

SPHERE_RADIUS = 0.03
BOX_HALF_WIDTH = 0.06
RHO_KG_M3 = 1000.0
MASSES = {"1 g": 1.0e-3, "10 g": 1.0e-2}
DEGREES = (8, 12, 16, 20, 24, 30)


def main() -> None:
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = MeshGenerator.sphere_in_box_domain(
        sphere_radius=SPHERE_RADIUS,
        box_half_width=BOX_HALF_WIDTH,
        resolution_sphere=SPHERE_RADIUS / 10.0,
        resolution_far=SPHERE_RADIUS / 5.0,
        comm=comm,
    )
    rho_field = build_density_field(msh, RHO_KG_M3)

    # Reproduce mass_averaged_sar's kernel exactly: same conditional, same
    # measure, same allreduce — only the degree moves.
    import ufl

    x = ufl.SpatialCoordinate(msh)

    def kernel_mass(center, radius, degree):
        offset = x - ufl.as_vector([float(c) for c in center])
        inside = ufl.conditional(
            ufl.lt(ufl.real(ufl.dot(offset, offset)), float(radius) ** 2), 1.0, 0.0
        )
        dx = ufl.Measure("dx", domain=msh, metadata={"quadrature_degree": int(degree)})
        mass = comm.allreduce(
            fem.assemble_scalar(fem.form(inside * rho_field * dx)), op=MPI.SUM
        )
        return float(np.real(mass))

    if comm.rank == 0:
        print(f"[MAT-4 step 3 probe] R = {SPHERE_RADIUS * 1e3:.1f} mm, h = R/10")

    for label, mass_kg in MASSES.items():
        radius = averaging_ball_radius(mass_kg=mass_kg, rho=RHO_KG_M3)
        volume_exact = 4.0 / 3.0 * np.pi * radius**3
        if comm.rank == 0:
            print(
                f"\n  {label}: a = {radius * 1e3:.4f} mm = "
                f"{radius / SPHERE_RADIUS:.4f} R, "
                f"{radius / (SPHERE_RADIUS / 10.0):.2f} cells per radius"
            )
        for degree in DEGREES:
            m_centre = kernel_mass((0.0, 0.0, 0.0), radius, degree)
            if comm.rank == 0:
                print(
                    f"    degree {degree:>2d}: mass = {m_centre:.8e} kg, "
                    f"error {abs(m_centre - mass_kg) / mass_kg:.4%}, "
                    f"V_kernel/V_exact = {m_centre / (RHO_KG_M3 * volume_exact):.6f}"
                )

    # The surface placement too: the negative control uses the same kernel and
    # its mass must stay put (uniform rho) whatever the degree.
    radius = averaging_ball_radius(mass_kg=MASSES["1 g"], rho=RHO_KG_M3)
    if comm.rank == 0:
        print("\n  1 g at (0,0,R) — surface control denominator:")
    for degree in DEGREES:
        m_surface = kernel_mass((0.0, 0.0, SPHERE_RADIUS), radius, degree)
        if comm.rank == 0:
            print(
                f"    degree {degree:>2d}: mass = {m_surface:.8e} kg, "
                f"error {abs(m_surface - MASSES['1 g']) / MASSES['1 g']:.4%}"
            )


if __name__ == "__main__":
    main()
