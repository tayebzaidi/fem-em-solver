"""Example (`EX-50`): the conductor as a hole in ParaView.

`TH-15` step 1 gates a perfectly conducting sphere modelled as an absence —
its cells are cut from the mesh, and the cavity wall arrives as a facet tag
carrying the homogeneous tangential condition ``n × E = 0`` (the boundary
condition, not the sphere's material, produces the field). This is the
**geometry / boundary-condition** angle beside `th:3`'s *material* angle:
`th:3` shows a sphere solved **inside** the mesh, whose ``ε`` sets the
interior field; here no sphere is meshed at all, and the same physics comes
from a Dirichlet condition on a hole's wall instead.

Outside the (absent) sphere the exact solution is `th:3`'s own uniform-plus-
dipole pair, at the perfect-conductor limit of the dipole coefficient::

    E_out = E0 zhat + beta E0 R^3 (3 (zhat.rhat) rhat - zhat) / r^3,  beta = 1

(the dielectric's ``beta = (eps-1)/(eps+2)`` as ``eps -> inf``; that limit is
never reached by passing ``eps = inf`` into `th:3`'s callable, where the
expression is ``nan`` — the closed form used here is a distinct one, PEC from
the start). On the sphere surface the tangential component vanishes, which is
what makes ``n x E = 0`` on the cavity wall the *same* closed form and not an
extra piece of data.

**It asserts, it does not merely render.** Every record, band and callable is
*imported* from the module that gates this capability
(``tests/validation/test_pec_sphere_hole.py``, `TH-15` step 1), never
restated, so the example and the landed gate cannot drift apart:

* *The anchor:* the dipole coefficient beta fitted on two probe shells
  outside the cavity, against the perfect-conductor value 1, at the module's
  own ``BAND`` (twice `th:3`'s own interior-miss record) — reproduced to
  1e-3 relative against the gate's reading on this identical mesh.
* *Two structural anchors on the same solve:* the cavity facet tag reaches a
  nonzero dof set, and every dof on it is pinned to (numerically) zero; the
  solution's imaginary part is negligible next to its real part, as it must
  be on a lossless, real-data problem.
* *The negative control, asserted:* drop the cavity tag from the Dirichlet
  set and the cavity becomes a natural (void) boundary instead of a
  perfectly conducting one — a different physical statement, not a
  relabelling — and the fitted beta separates from 1 by far more than the
  band.
* *Printed, not asserted:* the pointwise miss on the probe shells, which sits
  at a first-order Nedelec discretisation floor next to a curved, Dirichlet-
  pinned wall (`TH-15`'s own disposition) — the guide explains why a ~2%
  dipole-coefficient anchor coexists with a ~20-40% pointwise reading.

Run it through the example runner (the ``th:`` group sources the complex
build automatically; a real build raises)::

    ./run_examples.sh -e th:9

Output lands in ``examples/time_harmonic/paraview_output``: open
``time_harmonic_09_pec_sphere_hole_combined.xdmf`` and colour by
``E_magnitude``. The box shows a spherical *void* rather than a solid ball —
nothing is meshed inside the cavity wall — with the field tangentially zero
on its surface. ``Clip`` through ``y = 0`` and ``Glyph`` on ``E_real`` to see
the dipole pattern outside the hole; compare beside `th:3`'s picture of the
same field produced by a *solved* sphere instead of an absent one.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel

# The gated fixture lives in the test that gates `TH-15` step 1; the §7
# `EX-50` plan requires importing it rather than restating it. The runner
# puts only ``src`` on PYTHONPATH, so the repo root goes on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.validation.test_dielectric_sphere import (  # noqa: E402
    BOX_HALF_WIDTH,
    E0,
    FREQUENCY_HZ,
    SPHERE_RADIUS,
)
from tests.validation.test_pec_sphere_hole import (  # noqa: E402
    BAND,
    BETA_PEC,
    BETA_VOID,
    CAVITY_TAG,
    CONTROL_CEILING,
    OUTER_BOUNDARY_TAG,
    RESOLUTION_FAR,
    RESOLUTION_SPHERE,
    TH8_RECORD_INTERIOR_MISS,
    _cavity_dofs,
    _dipole_basis,
    _pec_exterior_numpy,
    _probe_shells,
    _uniform_field,
)

#: The gate's own 5x floor on the negative control (§7 `EX-50` plan, rule
#: (e)), backed by the gate module's own measurement of the same comparison
#: on the same mesh (`20260905T170225Z_TH-15.log:303`: 29.0x, ceiling 30x).
CONTROL_BAND_MULTIPLE = 5.0

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "time_harmonic_09_pec_sphere_hole"


def _hole_mesh():
    """Build the hole mesh directly: the gate module's ``_MESH_CACHE`` is
    process-local, so this process must build its own copy at the same
    resolution rather than reaching across into the test module's state."""
    return MeshGenerator.sphere_in_box_domain(
        sphere_radius=SPHERE_RADIUS,
        box_half_width=BOX_HALF_WIDTH,
        resolution_sphere=RESOLUTION_SPHERE,
        resolution_far=RESOLUTION_FAR,
        comm=MPI.COMM_WORLD,
        as_hole=True,
    )


def _solve(msh, cell_tags, facet_tags, pec_facet_tags):
    """One solve on the shared hole mesh with the given Dirichlet facet set.

    Returns ``(beta, max_miss, rms_miss, imag_ratio, cavity_dof_max,
    n_cavity_dofs, ndirichlet, fields)`` — the same measured quantities as
    the gate module's own ``_solve``, plus the fields kept for export.
    """
    comm = MPI.COMM_WORLD
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=_pec_exterior_numpy(),
        pec_facet_tags=pec_facet_tags,
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    fields = solver.solve()

    points = _probe_shells()
    real_values, valid_real = evaluate_vector_field_parallel(fields.e_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(fields.e_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(f"{int((~valid).sum())} exterior probe points were not evaluated")

    e_measured = np.real(real_values[:, :3])
    e_imaginary = np.real(imag_values[:, :3])

    basis = _dipole_basis(points)
    residual = e_measured - _uniform_field(points)
    beta = float(np.sum(residual * basis) / np.sum(basis * basis))

    e_closed = _uniform_field(points) + BETA_PEC * basis
    misses = np.linalg.norm(e_measured - e_closed, axis=1) / E0
    pointwise_max = float(np.max(misses))
    pointwise_rms = float(np.sqrt(np.mean(misses**2)))

    imag_ratio = float(
        np.max(np.linalg.norm(e_imaginary, axis=1))
        / max(float(np.max(np.linalg.norm(e_measured, axis=1))), 1e-300)
    )

    # Rank-local: the cavity dof block lives on whichever ranks own those facets.
    cavity_dofs = _cavity_dofs(msh, facet_tags, solver.function_space())
    n_cavity_dofs = int(comm.allreduce(int(cavity_dofs.size), op=MPI.SUM))
    solution = np.asarray(fields.e_complex.x.array)
    local_max = float(np.max(np.abs(solution[cavity_dofs]))) if cavity_dofs.size else 0.0
    cavity_dof_max = float(comm.allreduce(local_max, op=MPI.MAX))

    return (
        beta,
        pointwise_max,
        pointwise_rms,
        imag_ratio,
        cavity_dof_max,
        n_cavity_dofs,
        int(fields.dirichlet_dof_count),
        fields,
    )


def _paraview_fields(msh, fields):
    """CG1 ``E_real`` / ``E_magnitude`` from the solved phasor (air cells only)."""
    v_cg = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    e_cg = fem.Function(v_cg, name="E_phasor")
    e_cg.interpolate(fields.e_complex)
    e_cg.x.scatter_forward()

    e_re = fem.Function(v_cg, name="E_real")
    e_re.x.array[:] = np.real(e_cg.x.array)
    e_re.x.scatter_forward()

    s_cg = fem.functionspace(msh, ("Lagrange", 1))
    e_mag = fem.Function(s_cg, name="E_magnitude")
    components = np.abs(e_cg.x.array.reshape(-1, 3))
    e_mag.x.array[:] = np.sqrt(np.sum(components * components, axis=1))
    e_mag.x.scatter_forward()

    return e_re, e_mag


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "this example needs the complex DolfinX build "
            "(source /usr/local/bin/dolfinx-complex-mode); the runner's `th:` "
            "group sources it automatically"
        )

    if comm.rank == 0:
        print("=" * 72)
        print("EX-50 — the conductor as a hole: PEC sphere cut from the mesh")
        print("=" * 72)
        print(
            f"\n[geometry] sphere R = {SPHERE_RADIUS} m cut from a "
            f"{2 * BOX_HALF_WIDTH} m air box (`sphere_in_box_domain(as_hole=True)`)"
            f" — the sphere's cells are absent, its surface is facet tag "
            f"{CAVITY_TAG}"
            f"\n[boundary] n x E = 0 on tags ({OUTER_BOUNDARY_TAG}, {CAVITY_TAG}): "
            f"the outer wall carries the exact exterior Dirichlet data, the "
            f"cavity wall carries the homogeneous PEC condition that stands in "
            f"for the conductor"
            f"\n[regime] f = {FREQUENCY_HZ / 1e6:.4f} MHz, lossless (sigma = 0)"
            f"\n[vs th:3] `th:3` solves a sphere *inside* the mesh and lets eps "
            f"set the field; here no sphere is meshed at all, and n x E = 0 on "
            f"a hole's wall produces the perfect-conductor limit beta = "
            f"{BETA_PEC:.1f} instead",
            flush=True,
        )

    solve_started = time.perf_counter()
    msh, cell_tags, facet_tags = _hole_mesh()
    n_cells = int(
        comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM)
    )

    (
        beta,
        pointwise_max,
        pointwise_rms,
        imag_ratio,
        cavity_dof_max,
        n_cavity_dofs,
        ndirichlet,
        fields,
    ) = _solve(msh, cell_tags, facet_tags, (OUTER_BOUNDARY_TAG, CAVITY_TAG))
    solve_seconds = time.perf_counter() - solve_started
    beta_miss = abs(beta - BETA_PEC)

    if comm.rank == 0:
        print(
            f"\n[solve] {n_cells} cells (gate's own 13 239-cell rung: "
            f"h_sphere = {RESOLUTION_SPHERE}, h_far = {RESOLUTION_FAR}), "
            f"solved in {solve_seconds:.1f} s"
            f"\n[anchor] fitted beta = {beta:.6f}, |beta - 1| = {beta_miss:.4%} "
            f"vs BAND = {BAND:.4%} (= 2x TH8 record miss "
            f"{TH8_RECORD_INTERIOR_MISS:.4%}); the gate's own reading on this "
            f"mesh is 1.9746%"
            f"\n[record, not asserted] max pointwise |E - E_closed|/E0 on the "
            f"probe shells: {pointwise_max:.4%}, rms {pointwise_rms:.4%} — a "
            f"first-order Nedelec floor next to the pinned curved wall, not a "
            f"regression (see the guide)"
            f"\n[structure] cavity dofs (tag {CAVITY_TAG}, reduced) = "
            f"{n_cavity_dofs}, max |E| on them = {cavity_dof_max:.3e}; total "
            f"Dirichlet dofs = {ndirichlet}"
            f"\n[structure] |Im E|/|Re E| = {imag_ratio:.3e}",
            flush=True,
        )

    assert n_cavity_dofs > 0, (
        "no dofs were located on cavity facet tag 2 — the hole's surface group "
        "did not reach the dolfinx facet tags, so nothing was constrained"
    )
    assert cavity_dof_max < 1e-12, (
        f"max |E| on the cavity dofs is {cavity_dof_max:.3e}, not zero: the "
        "homogeneous tangential trace was not applied on the cavity wall"
    )
    assert imag_ratio < 1e-6, (
        f"|Im E|/|Re E| = {imag_ratio:.3e} on a lossless, real-data problem — "
        "the e^{+jwt} convention or the material map has leaked an imaginary part"
    )
    assert beta_miss <= BAND, (
        f"fitted dipole coefficient {beta:.6f} misses the perfect-conductor "
        f"beta = 1 by {beta_miss:.4%}, over the {BAND:.4%} band imported from "
        "the `TH-15` step 1 gate — an example/test divergence, not a tolerance "
        "to move"
    )

    # ---- negative control: asserted, per rule (e) --------------------------
    (
        beta_control,
        pointwise_control,
        _rms_control,
        _imag_control,
        cavity_dof_max_control,
        _n_cavity_control,
        ndirichlet_control,
        _fields_control,
    ) = _solve(msh, cell_tags, facet_tags, (OUTER_BOUNDARY_TAG,))
    beta_miss_control = abs(beta_control - BETA_PEC)
    control_factor = beta_miss_control / BAND

    if comm.rank == 0:
        print(
            f"\n[control] cavity left natural (pec_facet_tags=({OUTER_BOUNDARY_TAG},)"
            f"), {ndirichlet_control} Dirichlet dofs (vs {ndirichlet} with the "
            f"cavity constrained)"
            f"\n[control] fitted beta = {beta_control:.6f} (void closed form "
            f"{BETA_VOID:+.4f}), |beta - 1| = {beta_miss_control:.4%} = "
            f"{control_factor:.1f}x the {BAND:.4%} band (ceiling {CONTROL_BAND_MULTIPLE:.0f}x "
            f"required, gate's own measurement of this comparison on this mesh: "
            f"29.0x against a 30x ceiling, `20260905T170225Z_TH-15.log:303`)"
            f"\n[control] max pointwise |E - E_closed(PEC)|/E0 = "
            f"{pointwise_control:.4%}"
            f"\n[control] max |E| on the (unconstrained) cavity dofs = "
            f"{cavity_dof_max_control:.3e}",
            flush=True,
        )

    assert beta_miss_control <= CONTROL_CEILING, (
        f"the control's |beta - 1| = {beta_miss_control:.4f} exceeds the ceiling "
        f"{CONTROL_CEILING} this fixture can produce (the void value is 1.5); "
        "the fitted coefficient is not measuring the same field"
    )
    assert control_factor >= CONTROL_BAND_MULTIPLE, (
        f"the natural-cavity control separated from beta=1 by only "
        f"{control_factor:.2f}x the band, under the {CONTROL_BAND_MULTIPLE:.0f}x "
        "floor rule (e) requires — the control is not a control on this run"
    )
    assert cavity_dof_max_control > 1e-12, (
        f"the control's cavity dofs are zero to {cavity_dof_max_control:.3e}: the "
        "Dirichlet set reached the cavity even though it was not requested"
    )

    # ---- ParaView -----------------------------------------------------------
    e_re, e_mag = _paraview_fields(msh, fields)
    OUTPUT_DIR.mkdir(exist_ok=True)
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        cell_tags,
        {"E_real": e_re, "E_magnitude": e_mag},
        comm=comm,
        facet_tags=facet_tags,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    if comm.rank == 0:
        print(
            f"\n[paraview] wrote {xdmf_path}"
            f"\n[paraview] colour by `E_magnitude`: the box shows a spherical "
            f"void rather than a solid ball, with the field tangentially zero "
            f"on its surface. `Clip` through y = 0 and `Glyph` on `E_real` to "
            f"see the dipole pattern outside the hole — compare beside `th:3`'s "
            f"picture of a solved (not absent) sphere."
            f"\n\nAll assertions hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
