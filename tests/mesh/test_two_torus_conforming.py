"""`GEO-8` conformity gate for ``MeshGenerator.two_torus_domain``.

Until 2026-08-01 the fixture added two tori and a box and never fragmented, so
gmsh meshed three mutually disconnected components: a *solid* box plus two
torus islands. Two independent signatures, both measured on the parked
`PORT-1` step-1 probe (commit 2700efe) and reproduced by the ⬇ "before"
numbers in the `GEO-8` §7 entry:

* volume — total mesh volume exceeded the analytic box by exactly the two
  torus volumes (1.315956e-02 vs 1.312500e-02 m³, ratio 1.002633), because the
  torus interiors were meshed twice;
* field — driving torus 1 with a tag-restricted source left ``∫|E|² dV`` over
  the air tag *exactly* zero: the field could not leave its island.

Both are asserted here. The volume test is the cheap one and runs in either
build; the field test needs a complex solve and is therefore ``@complex_only``.
"""

from __future__ import annotations

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from tests.complex_mode import complex_only
from tests.mesh.helpers import global_cell_tag_set

SEPARATION = 0.05
MAJOR_RADIUS = 0.02
MINOR_RADIUS = 0.005
RESOLUTION = 0.01
AIR_PADDING = 2.0 * MINOR_RADIUS
# Graded: the tori must actually be resolved for the volume band below to say
# anything about conformity. At the uniform 0.01 the cells are twice the wire
# minor radius and the meshed torus loses 40% of its volume to chordal deficit
# (5.905213e-06 vs 9.869604e-06 m^3, measured 2026-08-01) — a statement about
# resolution, not about the fragment.
WIRE_RESOLUTION = 0.002

WIRE_TAGS = (1, 2)
AIR_TAG = 3


def _analytic_box_volume(separation, major_radius, minor_radius, padding):
    half_x = major_radius + minor_radius + padding
    half_z = separation / 2.0 + minor_radius + padding
    return 8.0 * half_x * half_x * half_z


def _tag_volume(msh, cell_tags, tag, comm):
    """``∫_tag 1 dV``, reduced — ``assemble_scalar`` is rank-local."""
    dx_tag = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,))
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * dx_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _total_volume(msh, comm):
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * ufl.dx))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def test_two_torus_volumes_partition_the_box():
    """The three tagged volumes tile the box exactly — no doubly-meshed tori."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=RESOLUTION,
        air_padding=AIR_PADDING,
        wire_resolution=WIRE_RESOLUTION,
        far_resolution=RESOLUTION,
        comm=comm,
    )

    assert global_cell_tag_set(msh, cell_tags) == {1, 2, 3}

    v_box = _analytic_box_volume(SEPARATION, MAJOR_RADIUS, MINOR_RADIUS, AIR_PADDING)
    v_total = _total_volume(msh, comm)
    v_wires = [_tag_volume(msh, cell_tags, t, comm) for t in WIRE_TAGS]
    v_air = _tag_volume(msh, cell_tags, AIR_TAG, comm)

    # The union of the three volumes is the box, and the box's boundary is
    # planar, so the linear-tet mesh reproduces it to roundoff: the curvature
    # deficit of the torus surfaces is interior and cancels between the wire
    # and air sides. The broken fixture gave 1.002633 here.
    assert abs(v_total / v_box - 1.0) < 1e-9, (
        f"total mesh volume {v_total:.6e} m^3 vs analytic box {v_box:.6e} m^3 "
        f"(ratio {v_total / v_box:.6f}); a ratio near 1.0026 is the "
        "non-fragmented signature — the tori are meshed twice"
    )

    # Tags partition the mesh: air is the box *minus* the tori, not the box.
    assert abs((v_air + sum(v_wires)) / v_total - 1.0) < 1e-9

    # Each meshed torus sits just inside its analytic volume (chordal deficit
    # of a linear-tet approximation to a curved surface: it inscribes).
    v_torus = 2.0 * np.pi**2 * MAJOR_RADIUS * MINOR_RADIUS**2
    for tag, v in zip(WIRE_TAGS, v_wires):
        assert 0.80 * v_torus < v < v_torus, (
            f"tag {tag} meshed volume {v:.6e} m^3 outside the inscribed band "
            f"(0.80, 1.00) x analytic {v_torus:.6e} m^3"
        )

    if comm.rank == 0:
        print(
            f"\nV_box={v_box:.6e}  V_mesh={v_total:.6e}  ratio={v_total / v_box:.9f}"
            f"\nV_wire1={v_wires[0]:.6e}  V_wire2={v_wires[1]:.6e}  "
            f"V_torus_analytic={v_torus:.6e}  "
            f"meshed/analytic={v_wires[0] / v_torus:.4f}, {v_wires[1] / v_torus:.4f}"
            f"\nV_air={v_air:.6e}  (box - 2 tori = {v_box - 2 * v_torus:.6e})",
            flush=True,
        )

    assert v_air < v_box - 1.5 * v_torus, (
        f"air volume {v_air:.6e} m^3 is not the box minus the two tori "
        f"(box {v_box:.6e}, tori {2 * v_torus:.6e})"
    )


@complex_only
def test_driven_torus_field_reaches_the_air_region():
    """A source on torus 1 alone drives a field in the air — no islands.

    This is the `PORT-1` step-1 diagnostic promoted to an assertion. On the
    non-fragmented mesh ``∫_air |E|²`` was identically 0 while the driven
    torus held 2.0537e-04, because no cell was shared between the two.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=RESOLUTION,
        air_padding=AIR_PADDING,
        wire_resolution=WIRE_RESOLUTION,
        far_resolution=RESOLUTION,
        comm=comm,
    )

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=10.0e6,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map=None,
        boundary_condition="pec_zero_tangential_a",
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    j_magnitude = 1.0 / (np.pi * MINOR_RADIUS**2)

    def current_density(x):
        # Regularised inside the sqrt: complex UFL refuses max_value here.
        rho_safe = ufl.sqrt(x[0] ** 2 + x[1] ** 2 + 1e-24)
        return ufl.as_vector(
            [-x[1] / rho_safe * j_magnitude, x[0] / rho_safe * j_magnitude, 0.0]
        )

    fields = solver.solve(current_density=current_density, subdomain_ids=[WIRE_TAGS[0]])
    e_field = fields.e_complex

    def energy(tag):
        dx_tag = ufl.Measure(
            "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,)
        )
        local = fem.assemble_scalar(fem.form(ufl.inner(e_field, e_field) * dx_tag))
        return float(np.real(comm.allreduce(local, op=MPI.SUM)))

    e_driven = energy(WIRE_TAGS[0])
    e_air = energy(AIR_TAG)
    e_undriven = energy(WIRE_TAGS[1])

    if comm.rank == 0:
        print(
            f"\nint|E|^2: driven torus={e_driven:.6e}  air={e_air:.6e}  "
            f"undriven torus={e_undriven:.6e}"
            f"\nratios to driven: air={e_air / e_driven:.6e}  "
            f"undriven={e_undriven / e_driven:.6e}",
            flush=True,
        )

    assert e_driven > 0.0, "driven torus carries no field at all"
    # The air must see the driven loop. Ratio, not an absolute floor: the
    # broken mesh gave exactly 0, so any physically connected value clears a
    # bound many orders of magnitude above machine noise.
    assert e_air / e_driven > 1e-6, (
        f"int|E|^2 over the air tag is {e_air:.6e} against {e_driven:.6e} in "
        "the driven torus — the driven torus is still an island"
    )
    # And the coupling that PORT-1 needs: the *undriven* torus is reached too.
    assert e_undriven / e_driven > 1e-9, (
        f"int|E|^2 over the undriven torus is {e_undriven:.6e} against "
        f"{e_driven:.6e} driven — no path between the two loops"
    )
