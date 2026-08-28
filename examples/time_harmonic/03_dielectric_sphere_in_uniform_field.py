"""Example (`EX-6`): a dielectric sphere in a uniform field — *solved*, not imposed.

The `§5.4` ramp entry for Phase 2's material-contrast case, and the answer to a
question `EX-3` deliberately does not ask. `EX-3` computes mass-averaged SAR on a
sphere whose field is **imposed** analytically: the material never acts on the
field, it only weights it. This example puts the same kind of sphere in a solved
time-harmonic problem and lets ``ε`` *set* the field — the interior value comes
out of the assembly, not out of the input.

The physics is the `TH-8` gate's, unchanged. A sphere of radius ``R`` and
relative permittivity ``ε`` in a uniform field ``E₀ẑ`` polarises uniformly, and
in the quasi-static limit (``k₀R = 5e-3`` here) the electrostatic solution is
exact::

    E_in  = 3/(ε + 2) · E₀ ẑ                                  (r < R)
    E_out = E₀ ẑ + β E₀ R³ (3 (ẑ·r̂) r̂ − ẑ)/r³,  β = (ε−1)/(ε+2)  (r > R)

At ``ε = 78`` (water/saline, the phantom material this project is built around)
the interior field is **26.7× smaller** than the drive. The example imposes
``E_out`` as Dirichlet data on the box wall — exact there, since the exterior
branch holds on any surface outside the sphere — and measures the interior,
which nothing in the boundary data states. ``3/(ε+2)`` is produced by ``ε``
acting through the mass term ``−k₀²ε_c E`` and by the normal-``D`` jump at the
sphere surface; that jump is what ParaView shows.

**It asserts, it does not merely render.** The fixture is *imported* from the
module that closed `TH-8` (``tests/validation/test_dielectric_sphere.py`` —
geometry, frequency, probe cloud, and the exterior Dirichlet callable), so the
example and the landed gate cannot drift apart:

* *The anchor:* the probe-averaged interior ``E_z`` against ``3/(ε+2)E₀`` at the
  gate's own **5%** ceiling (`PROJECT_PLAN` §10 MVP criterion). On record at
  this, the finest of the gate's three meshes: **2.443%**, log
  ``20260731T200457Z_TH-8-gate-final.log``. Never tightened, never loosened — a
  run outside 5% is a regression finding, not a tolerance question.
* *Three shape claims from the same record:* the closed-form interior field is
  uniform, purely ``z``-directed, and real, so the run must also reproduce the
  gate's spread (0.080% on record), transverse ratio (0.085%), and
  ``|Im|/|Re|`` (0.0e+00) bounds at this mesh.
* *The exported field is the asserted field:* the interior average is
  re-measured a second, independent way — the volume integral
  ``∫_sphere E_z dx / ∫_sphere dx`` over the tagged sphere cells, which samples
  the whole ball out to ``r = R`` rather than the probe cloud's two shells
  inside ``0.55R``. What ParaView colours is therefore the field the assertions
  were read from, and the agreement between a point-probe average and a volume
  average is itself evidence the interior really is uniform.
* *The interface jump, measured:* the exterior field is probed just outside the
  pole and the equator of the sphere, and the ratio to the interior is checked
  against the closed form's own ``E_out``/``E_in`` there — 59.20× vs 56.27× over
  the pole, 11.46× vs 11.83× at the equator. The jump the picture shows is a
  number in the log. These two probes sit in the *far* mesh, twice as coarse as
  the sphere's and unrefined by the fixture, so they are held to 10% rather than
  the interior's 5% (see ``EXTERIOR_RTOL``); `TH-8` gates the interior only.
* *The negative control, cited rather than recomputed* (per the §7 `EX-6`
  plan): drop the sphere from the ``material_map`` under the *same* Dirichlet
  data and the interior lands at ``E_z = 0.918143``, **2348%** off the closed
  form — so the gate cannot pass by reading back its own boundary data. That
  control is in the log cited above; this example prints the separation and does
  not re-run it.

Run it through the example runner (the ``th:`` group sources the complex build
automatically; a real build raises)::

    ./run_examples.sh -e th:3

Output lands in ``examples/time_harmonic/paraview_output``: open
``time_harmonic_03_dielectric_sphere_combined.xdmf`` and colour by ``E_magnitude``. The sphere is
a dark ball inside a bright box — that contrast *is* ``3/(ε+2)``. ``Threshold``
on ``CellTags`` (1 = sphere, 2 = air) to isolate either region, and ``Glyph`` on
``E_real`` in a clip through ``y = 0`` to see the dipole pattern outside and the
uniform, ``z``-directed field inside.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

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
from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel

# The gated fixture lives in the test that closed `TH-8`; the §7 `EX-6` plan
# requires importing it rather than restating it. The runner puts only ``src``
# on PYTHONPATH, so the repo root goes on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.validation.test_dielectric_sphere import (  # noqa: E402
    BOX_HALF_WIDTH,
    E0,
    EPSILON_R_SPHERE,
    FREQUENCY_HZ,
    K0_R,
    SPHERE_RADIUS,
    SPHERE_TAG,
    _exact_exterior_numpy,
    _interior_probe_points,
    interior_field_closed_form,
)

#: The gate's finest mesh, so every number printed here is comparable line for
#: line with ``20260731T200457Z_TH-8-gate-final.log``. One mesh, not the gate's
#: three: the convergence sweep is the gate's job, this is the example.
RESOLUTION_SPHERE, RESOLUTION_FAR = 0.00625, 0.0125

#: The `TH-8` gate's own ceiling (PROJECT_PLAN §10 MVP criterion), not a tighter
#: one. Measured at this mesh in the cited log: 2.443%.
INTERIOR_RTOL = 0.05
RECORD_INTERIOR_ERROR = 0.02443

#: Shape bounds, also the gate's own; the record at this mesh is in brackets.
SPREAD_MAX = 0.01  # [0.080%]
TRANSVERSE_MAX = 0.01  # [0.085%]
IMAG_RATIO_MAX = 1e-6  # [0.0e+00 — the problem is lossless and its data real]

#: Negative control on record in the cited log (`test_sphere_permittivity_is_
#: what_sets_the_interior_field`, middle resolution): an ε-blind solve handed the
#: *same* Dirichlet data lands here instead. Cited, not re-run.
RECORD_BLIND_EZ = 0.918143
RECORD_BLIND_ERROR = 23.48382

#: The volume average over the tagged sphere cells reaches out to ``r = R``,
#: where the discretisation is coarsest relative to the interface; the probe
#: cloud stops at 0.55R, so the two are not required to agree exactly. Measured
#: separation at this mesh: **0.014%** (`20260810T003418Z_EX-6-run1.log`), so 3%
#: is a bound on it, not a fit.
VOLUME_VS_PROBE_MAX = 0.03

#: Ceiling on the *exterior* probes, which is looser than the interior one on
#: purpose and was set from measurement. The exterior points sit at r = 1.2 R,
#: one cell outside the interface in the **far** mesh (h_far = 0.0125 m = 0.25 R,
#: twice the sphere's h), where the dipole term falls as 1/r³ — a far harsher
#: place to interpolate than the sphere interior, which the fixture refines and
#: where the exact field is constant. `TH-8` gates the interior only and says
#: nothing about the exterior, so no gated bound exists to inherit here.
#: Measured at this mesh (`20260810T003418Z_EX-6-run1.log`): **7.782%** over the
#: pole, **0.756%** at the equator — the two ends of the same effect, since the
#: polar point carries the whole 2βR³/r³ dipole lobe and the equatorial one only
#: half of it with the opposite sign. 10% bounds the worse of the two; the
#: interior anchor above is untouched at the gate's own 5%.
EXTERIOR_RTOL = 0.10

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "time_harmonic_03_dielectric_sphere"


def _exterior_probe_points() -> np.ndarray:
    """Two points just outside the sphere: one over the pole, one at the equator.

    The closed form's exterior branch is strongest and simplest at exactly these
    two places — over the pole the dipole adds to ``E₀`` (``E_z = E₀(1 + 2βR³/r³)``),
    at the equator it subtracts (``E_z = E₀(1 − βR³/r³)``) — so probing both
    shows the jump *and* its sign reversal in one pair. Kept at 1.2 R, well
    inside the box wall at 2 R, and off the mesh symmetry planes in the
    transverse coordinates.
    """
    r = 1.2 * SPHERE_RADIUS
    return np.array(
        [
            [0.031 * SPHERE_RADIUS, -0.027 * SPHERE_RADIUS, r],
            [r * 0.9994, 0.0349 * r, 0.017 * SPHERE_RADIUS],
        ]
    )


def _exterior_ez_closed_form(points: np.ndarray, epsilon_r: float) -> np.ndarray:
    """``E_z`` of the exact exterior branch at ``points`` — the same callable the
    Dirichlet data is built from, evaluated where the solver was *not* told."""
    field = _exact_exterior_numpy(epsilon_r)(points.T)
    return np.real(np.asarray(field[2], dtype=complex))


def _solve() -> tuple:
    """The `TH-8` problem at the gate's finest mesh, fields kept for export."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = MeshGenerator.sphere_in_box_domain(
        sphere_radius=SPHERE_RADIUS,
        box_half_width=BOX_HALF_WIDTH,
        resolution_sphere=RESOLUTION_SPHERE,
        resolution_far=RESOLUTION_FAR,
        comm=comm,
    )
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0),
        cell_tags=cell_tags,
        material_map={
            SPHERE_TAG: HomogeneousMaterial(sigma=0.0, epsilon_r=EPSILON_R_SPHERE)
        },
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=_exact_exterior_numpy(EPSILON_R_SPHERE),
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()
    n_cells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    return msh, cell_tags, fields, int(n_cells)


def _probe(fields, points: np.ndarray, comm: MPI.Comm):
    """Real and imaginary ``E`` at ``points``, with the validity mask enforced.

    Point evaluation goes through ``evaluate_vector_field_parallel``: the points
    live on whichever rank owns their cell, and a point nobody owns must be an
    error, not a silent zero.
    """
    real_values, valid_real = evaluate_vector_field_parallel(fields.e_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(fields.e_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(f"{int((~valid).sum())} probe points were not evaluated")
    return np.real(real_values), np.real(imag_values)


def _sphere_volume_average_ez(msh, cell_tags, fields, comm: MPI.Comm):
    """``∫_sphere E_z dx / ∫_sphere dx`` — the interior average, measured again.

    Independent of the probe cloud in both the sampling set (the whole ball, not
    two shells) and the machinery (assembly, not point location). Both integrals
    are rank-local until reduced. The integrand is complex in this build, so the
    real part is taken explicitly rather than by a silent cast; the imaginary
    part is separately asserted negligible above.
    """
    dx = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)
    e_z = fields.e_complex[2]
    numerator = fem.assemble_scalar(fem.form(e_z * dx(SPHERE_TAG)))
    volume = fem.assemble_scalar(fem.form(fem.Constant(msh, default_scalar_type(1.0)) * dx(SPHERE_TAG)))
    numerator = comm.allreduce(float(np.real(numerator)), op=MPI.SUM)
    volume = comm.allreduce(float(np.real(volume)), op=MPI.SUM)
    return numerator / volume, volume


def _paraview_fields(msh, fields):
    """CG1 ``E_real`` / ``E_imag`` / ``E_magnitude`` from the solved phasor.

    XDMF cannot carry N1curl, so the solution is interpolated once into a CG1
    vector space and split. ``|E|`` is the phasor magnitude taken on the array,
    so no complex ``sqrt`` is formed.
    """
    v_cg = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    e_cg = fem.Function(v_cg, name="E_phasor")
    e_cg.interpolate(fields.e_complex)
    e_cg.x.scatter_forward()

    e_re = fem.Function(v_cg, name="E_real")
    e_re.x.array[:] = np.real(e_cg.x.array)
    e_im = fem.Function(v_cg, name="E_imag")
    e_im.x.array[:] = np.imag(e_cg.x.array)

    s_cg = fem.functionspace(msh, ("Lagrange", 1))
    e_mag = fem.Function(s_cg, name="E_magnitude")
    components = np.abs(e_cg.x.array.reshape(-1, 3))
    e_mag.x.array[:] = np.sqrt(np.sum(components * components, axis=1))

    for f in (e_re, e_im, e_mag):
        f.x.scatter_forward()
    return e_re, e_im, e_mag


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "this example needs the complex DolfinX build "
            "(source /usr/local/bin/dolfinx-complex-mode); the runner's `th:` "
            "group sources it automatically"
        )

    expected = interior_field_closed_form(EPSILON_R_SPHERE)
    beta = (EPSILON_R_SPHERE - 1.0) / (EPSILON_R_SPHERE + 2.0)

    if comm.rank == 0:
        print("=" * 72)
        print("EX-6 — dielectric sphere in a uniform field: the SOLVED interior")
        print("=" * 72)
        print(
            f"\n[geometry] sphere R = {SPHERE_RADIUS} m inside a "
            f"{2 * BOX_HALF_WIDTH} m air box; the exact exterior field is "
            f"Dirichlet data on the wall, the interior is the solver's own output"
            f"\n[material] eps_r = {EPSILON_R_SPHERE} in the sphere (water/saline), "
            f"vacuum outside, sigma = 0 — lossless, so the answer is real"
            f"\n[regime] f = {FREQUENCY_HZ / 1e6:.4f} MHz, k0*R = {K0_R:.1e}: "
            f"quasi-static, the retardation the closed form drops is O((k_in R)^2) "
            f"~ 0.2%"
            f"\n[closed form] E_in/E0 = 3/(eps+2) = {expected:.6f} "
            f"({E0 / expected:.1f}x smaller than the drive), beta = "
            f"{beta:.6f}"
            f"\n[vs EX-3] `EX-3` *imposes* its field on a sphere and weights it by "
            f"the material; here eps *sets* the field, and nothing in the boundary "
            f"data states the interior value",
            flush=True,
        )

    solve_started = time.perf_counter()
    msh, cell_tags, fields, n_cells = _solve()
    solve_seconds = time.perf_counter() - solve_started

    # ---- the anchor: probe-averaged interior E_z vs 3/(eps+2) ---------------
    points = _interior_probe_points()
    real_values, imag_values = _probe(fields, points, comm)
    ez = real_values[:, 2]
    ez_mean = float(np.mean(ez))
    spread = float(np.max(np.abs(ez - ez_mean)) / abs(ez_mean))
    transverse = float(
        np.max(np.hypot(real_values[:, 0], real_values[:, 1])) / abs(ez_mean)
    )
    imag_ratio = float(np.max(np.abs(imag_values[:, 2])) / abs(ez_mean))
    error = abs(ez_mean - expected) / expected

    if comm.rank == 0:
        print(
            f"\n[solve] {n_cells} cells (h_sphere = {RESOLUTION_SPHERE}, "
            f"h_far = {RESOLUTION_FAR} — the `TH-8` gate's finest mesh), "
            f"solved in {solve_seconds:.1f} s"
            f"\n[interior] {points.shape[0]} probe points inside 0.55 R: "
            f"E_z = {ez_mean:.6f} V/m vs closed form {expected:.6f} V/m "
            f"({error:.3%}, ceiling {INTERIOR_RTOL:.0%}, "
            f"{RECORD_INTERIOR_ERROR:.3%} on the TH-8 record)"
            f"\n[interior] spread {spread:.3%}, transverse/E_z {transverse:.3%}, "
            f"|Im|/|Re| {imag_ratio:.3e} — the closed-form interior field is "
            f"uniform, z-directed and real, and the solve has to be all three",
            flush=True,
        )

    assert error < INTERIOR_RTOL, (
        f"the solved interior field {ez_mean:.6f} V/m misses the closed form "
        f"{expected:.6f} V/m by {error:.2%}, over the {INTERIOR_RTOL:.0%} MVP "
        f"ceiling and against {RECORD_INTERIOR_ERROR:.3%} on the `TH-8` record at "
        f"this same mesh — a regression finding, not a tolerance to move"
    )
    assert spread < SPREAD_MAX, (
        f"interior field is not uniform: spread {spread:.2%} across probes inside "
        f"0.55 R, where the closed form is constant (0.080% on the record)"
    )
    assert transverse < TRANSVERSE_MAX, (
        f"transverse interior field is {transverse:.2%} of E_z; the closed-form "
        f"interior field is purely z-directed (0.085% on the record)"
    )
    assert imag_ratio < IMAG_RATIO_MAX, (
        f"|Im E_z|/|Re E_z| = {imag_ratio:.3e} on a lossless problem with real "
        f"data — the e^{{+jwt}} convention or the material map has leaked an "
        f"imaginary part"
    )

    # ---- the exported field is the asserted field ---------------------------
    volume_ez, sphere_volume = _sphere_volume_average_ez(msh, cell_tags, fields, comm)
    volume_exact = 4.0 / 3.0 * np.pi * SPHERE_RADIUS**3
    volume_error = abs(sphere_volume - volume_exact) / volume_exact
    volume_vs_probe = abs(volume_ez - ez_mean) / abs(ez_mean)

    if comm.rank == 0:
        print(
            f"\n[cross-check] the same interior average, measured a second way: "
            f"int_sphere E_z dx / int_sphere dx = {volume_ez:.6f} V/m over the "
            f"tagged sphere cells, {volume_vs_probe:.3%} from the probe average "
            f"— assembly over the whole ball vs point location on two shells, "
            f"and they agree because the interior really is uniform"
            f"\n[cross-check] the tagged region is the sphere: assembled volume "
            f"{sphere_volume:.6e} m^3 vs 4/3*pi*R^3 = {volume_exact:.6e} m^3 "
            f"({volume_error:.3%}) — a faceted tetrahedral ball under-fills the "
            f"true sphere, which is exactly what this reads",
            flush=True,
        )

    assert volume_vs_probe < VOLUME_VS_PROBE_MAX, (
        f"the volume-averaged interior field {volume_ez:.6f} V/m and the "
        f"probe-averaged {ez_mean:.6f} V/m differ by {volume_vs_probe:.2%} — the "
        f"field being exported is not the field the anchor was read from, or the "
        f"interior is not uniform out to r = R"
    )
    assert volume_error < 0.02, (
        f"the cells tagged {SPHERE_TAG} enclose {sphere_volume:.6e} m^3 against "
        f"the sphere's {volume_exact:.6e} m^3 ({volume_error:.2%}) — the material "
        f"map is not being applied to the region the closed form describes"
    )

    # ---- the interface jump, as a number ------------------------------------
    ext_points = _exterior_probe_points()
    ext_real, _ = _probe(fields, ext_points, comm)
    ext_ez = ext_real[:, 2]
    ext_exact = _exterior_ez_closed_form(ext_points, EPSILON_R_SPHERE)
    ext_error = np.abs(ext_ez - ext_exact) / np.abs(ext_exact)
    jump = ext_ez / ez_mean
    jump_exact = ext_exact / expected

    if comm.rank == 0:
        for label, i in (("over the pole", 0), ("at the equator", 1)):
            print(
                f"\n[jump] {label} at r = 1.2 R: E_z = {ext_ez[i]:.6f} V/m vs "
                f"closed form {ext_exact[i]:.6f} V/m ({ext_error[i]:.3%}); "
                f"E_out/E_in = {jump[i]:.2f}x vs {jump_exact[i]:.2f}x — the "
                f"discontinuity ParaView shows, measured",
                flush=True,
            )

    assert np.all(ext_error < EXTERIOR_RTOL), (
        f"the solved exterior field misses its closed form by {ext_error} at "
        f"r = 1.2 R, against the {EXTERIOR_RTOL:.0%} ceiling and 7.782% / 0.756% "
        f"on record — the dipole outside the sphere is wrong even though the "
        f"interior passed, so the jump the picture shows is not the physical one"
    )
    assert jump[0] > 20.0 > jump[1] > 0.0, (
        f"the interface jump E_out/E_in reads {jump[0]:.2f}x over the pole and "
        f"{jump[1]:.2f}x at the equator; the closed form puts them at "
        f"{jump_exact[0]:.2f}x and {jump_exact[1]:.2f}x — both large, and the "
        f"polar one larger, because the dipole adds over the pole and subtracts "
        f"at the equator"
    )

    # ---- negative control: cited, not recomputed (§7 `EX-6` plan) -----------
    if comm.rank == 0:
        print(
            f"\n[control] this gate cannot pass by reading back its own boundary "
            f"data, and the `TH-8` gate measured that: the identical solve with "
            f"the sphere dropped from the material_map — same mesh, same "
            f"Dirichlet data, vacuum interior — returns E_z = "
            f"{RECORD_BLIND_EZ:.6f} V/m, {RECORD_BLIND_ERROR:.1%} off the closed "
            f"form, a factor {RECORD_BLIND_EZ / ez_mean:.1f} above what this run "
            f"measured. Cited from 20260731T200457Z_TH-8-gate-final.log, not "
            f"re-run: the wall data contributes at most 2*beta*R^3/W^3 = "
            f"{2 * beta * SPHERE_RADIUS**3 / BOX_HALF_WIDTH**3:.1%} of E0, while "
            f"the asserted interior is {E0 / expected:.1f}x below E0",
            flush=True,
        )

    assert RECORD_BLIND_ERROR > 1.0 > error, (
        "the cited eps-blind control and this run's measured error no longer "
        "straddle 100%, so the discrimination this control claims is not the one "
        "the run measured"
    )

    # ---- ParaView -----------------------------------------------------------
    e_re, e_im, e_mag = _paraview_fields(msh, fields)
    OUTPUT_DIR.mkdir(exist_ok=True)
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        cell_tags,
        {"E_real": e_re, "E_imag": e_im, "E_magnitude": e_mag},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    if comm.rank == 0:
        print(
            f"\n[paraview] wrote {xdmf_path}"
            f"\n[paraview] colour by `E_magnitude`: the sphere is a dark ball in a "
            f"bright box, and that contrast is 3/(eps+2) = {expected:.4f}. "
            f"`Threshold` on `CellTags` (1 = sphere, 2 = air) isolates either "
            f"region; `Glyph` on `E_real` in a y = 0 clip shows the dipole outside "
            f"and the uniform z-directed field inside."
            f"\n\nAll assertions hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
