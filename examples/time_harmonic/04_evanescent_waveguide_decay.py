"""Example (`EX-7`): a waveguide below cutoff — decay set by geometry, not by loss.

The `§5.4` ramp entry for Phase 2's guided-wave case, and the counterpart to
`th:1`. `EX-4` (the lossy plane wave) shows a field dying because the medium
absorbs it: ``Im ε_c`` acting through the mass term. This example shows a field
dying in a **lossless** medium (``σ = 0``, ``εᵣ = μᵣ = 1``), purely because the
guide is too narrow for the frequency. Nothing here absorbs anything; the decay
is the transverse geometry acting through the operator's *real* part.

The physics is the `TH-7` gate's, unchanged. In an ``a × b`` PEC guide the TE₁₀
mode has transverse profile ``sin(πx/a)`` and cutoff wavenumber ``k_c = π/a``
(cutoff ``f_c = c/2a = 2.998 GHz`` at ``a = 0.05 m``). Driven *below* cutoff the
axial dependence is a real exponential rather than a travelling wave::

    E(x, y, z) = ŷ · sin(πx/a) · e^{−γz},    γ = √(k_c² − k₀²)   [Np/m]

At 2.4 GHz that is ``γ = 37.652670 Np/m``, so the amplitude falls 6.6× over the
``L = a`` guide. The example imposes the exact field on the whole boundary — it
pins the two end faces — and measures the **slope in between**, which nothing in
the boundary data states. That slope is ``k₀²`` reaching the mass term: a solver
that dropped ``k₀²ε`` entirely would still decay, but at ``γ = k_c = 62.83``,
67% too fast, at *every* frequency.

**It asserts, it does not merely render.** The fixture is *imported* from the
module that closed `TH-7` (``tests/validation/test_waveguide_cutoff.py`` —
geometry, frequency, the exact-field factory, the probe line and its fit
window), so the example and the landed gate cannot drift apart:

* *The anchor:* the fitted decay constant ``γ`` against ``√(k_c² − k₀²)`` at the
  gate's own **5%** ceiling (`PROJECT_PLAN` §10 MVP criterion). On record at
  this, the finer of the gate's two meshes: **0.006%**, log
  ``20260731T123411Z_TH-7-gate-final.log``. Never tightened, never loosened — a
  run outside 5% is a regression finding, not a tolerance question.
* *Two shape claims from the same record:* the whole-field relative ``L2`` error
  against the closed form (4.406648e-02 on record, held to the same 5%), and the
  residual ``|Im E_y|/|Re E_y|`` on the probe line — lossless material and real
  boundary data give a real operator and a real right-hand side, so the phasor
  must be real to round-off (0.000e+00 on record).
* *The exported field is the asserted field:* ``γ`` is fitted a **second** time
  from the CG1 array that is actually written to XDMF, and the transverse
  profile is read off that same array at mid-guide and checked against
  ``sin(πx/a)``. So what ParaView colours is the mode the anchor was measured
  on, and "mode profile" is a number here, not just a picture.
* *The negative control, cited rather than recomputed* (per the §7 `EX-7`
  plan): the gate swept three below-cutoff frequencies on one mesh and measured
  a ``γ`` ratio of **2.6373** across the band against the closed form's 2.6383
  (0.038%), asserted ``> 2.0``. A ``k₀``-blind solver returns ``γ ≡ k_c`` at
  every frequency — ratio exactly 1. That control is in the log cited above;
  this example prints the separation, asserts its own ``γ`` sits strictly below
  ``k_c``, and does not re-run the sweep.

Run it through the example runner (the ``th:`` group sources the complex build
automatically; a real build raises)::

    ./run_examples.sh -e th:4

Output lands in ``examples/time_harmonic/paraview_output``: open
``evanescent_waveguide_combined.xdmf`` and colour by ``E_magnitude``. The bright
end is the drive face at ``z = 0`` and the field fades along ``+z`` — that fade
*is* ``e^{−γz}``. ``Plot Over Line`` along ``z`` on a log scale gives the
straight line the fit above measured; the same filter along ``x`` at fixed ``z``
gives the ``sin(πx/a)`` half-arch, pinned to zero on both PEC side walls.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem, mesh as dmesh

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel

# The gated fixture lives in the test that closed `TH-7`; the §7 `EX-7` plan
# requires importing it rather than restating it. The runner puts only ``src``
# on PYTHONPATH, so the repo root goes on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.validation.test_waveguide_cutoff import (  # noqa: E402
    A_M,
    B_M,
    FREQUENCY_HZ,
    L_M,
    SWEEP_HZ,
    _analytic_gamma,
    _exact_factory,
    _k0,
    _probe_points,
    cutoff_frequency_hz,
)

#: The gate's finer mesh (``n = 24`` → 41 472 cells), so every number printed
#: here is comparable line for line with
#: ``20260731T123411Z_TH-7-gate-final.log``. One mesh, not the gate's two: the
#: refinement pair is the gate's job, this is the example.
RESOLUTION_N = 24

#: The `TH-7` gate's own ceiling (PROJECT_PLAN §10 MVP criterion), not a tighter
#: one. Measured at this mesh in the cited log: gamma 0.006%, rel L2 4.406648e-02.
GAMMA_RTOL = 0.05
FIELD_L2_MAX = 0.05
RECORD_GAMMA_ERROR = 6e-5
RECORD_REL_L2 = 4.406648e-02

#: Lossless problem, real data ⇒ real phasor. Measured 0.000e+00 in the cited
#: log; 1e-10 is the gate's own bound on it.
IMAG_RATIO_MAX = 1e-10

#: Negative control on record in the cited log
#: (``test_decay_tracks_frequency_and_the_resonance_guard_stays_quiet``): across
#: 1.0/2.4/2.8 GHz the measured gamma ratio was 2.6373 against the closed form's
#: 2.6383. A k0-blind solver returns gamma = k_c at every frequency, i.e. a ratio
#: of exactly 1. Cited, not re-run.
RECORD_SWEEP_RATIO = 2.6373
RECORD_SWEEP_RATIO_EXACT = 2.6383
BLIND_SWEEP_RATIO = 1.0

#: Bounds on the *exported* CG1 array, set from measurement rather than
#: inherited: the gate fits N1curl point evaluations, and nothing gated exists
#: for the interpolated CG1 field or for the transverse profile read off it.
#: Measured at this mesh (``20260810T020325Z_EX-7-run1.log``): the CG1 refit
#: lands **0.117%** from the N1curl fit, and the mid-guide transverse profile is
#: **0.200%** RMS from sin(pi x/a) after peak normalisation. The interpolation is
#: CG1 over the same tetrahedra, so a couple of tenths of a percent is the
#: expected scale of both; the bounds sit ~4x and ~10x above what was measured,
#: loose enough that mesh-partition-dependent point location cannot flip them.
#: The anchor above is untouched at the gate's own 5%.
CG1_VS_NEDELEC_MAX = 0.005
PROFILE_RMS_MAX = 0.02

#: Transverse probe line for the mode profile: mid-guide in z, off the mesh
#: symmetry plane in y (the same reason the gate's axial line is off-lattice),
#: and clipped away from the two PEC walls where sin(pi x/a) -> 0 and a relative
#: comparison would divide by nothing.
PROFILE_Z_FRACTION = 0.5
PROFILE_Y_FRACTION = 0.5137
PROFILE_X_MIN_FRACTION = 0.12
PROFILE_X_MAX_FRACTION = 0.88
N_PROFILE = 25

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "evanescent_waveguide"


def _profile_points() -> np.ndarray:
    """A line across the guide at mid-length, where the profile is ``sin(πx/a)``."""
    xs = np.linspace(
        PROFILE_X_MIN_FRACTION * A_M, PROFILE_X_MAX_FRACTION * A_M, N_PROFILE
    )
    return np.column_stack(
        [
            xs,
            np.full_like(xs, PROFILE_Y_FRACTION * B_M),
            np.full_like(xs, PROFILE_Z_FRACTION * L_M),
        ]
    )


def _solve():
    """The `TH-7` problem at the gate's finer mesh, fields kept for export.

    Source-free: the evanescent TE₁₀ mode is an exact solution of the solved PDE
    in a lossless medium, so the only data is the exact field on the boundary.
    """
    comm = MPI.COMM_WORLD
    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([A_M, B_M, L_M])],
        [RESOLUTION_N, max(1, RESOLUTION_N // 2), RESOLUTION_N],
        cell_type=dmesh.CellType.tetrahedron,
    )
    exact_numpy, exact_ufl = _exact_factory(FREQUENCY_HZ)
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=exact_numpy,
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()
    n_cells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    return msh, fields, exact_ufl, int(n_cells)


def _relative_l2_error(msh, fields, exact_ufl, comm: MPI.Comm) -> float:
    """``‖E − E_exact‖ / ‖E_exact‖`` over the guide. Both integrals are
    rank-local until reduced — the square root comes *after* the allreduce."""
    x = ufl.SpatialCoordinate(msh)
    exact = exact_ufl(x)
    diff = fields.e_complex - exact
    err_sq = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(diff, diff) * ufl.dx)), op=MPI.SUM
    )
    ref_sq = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(exact, exact) * ufl.dx)), op=MPI.SUM
    )
    return float(np.sqrt(abs(err_sq)) / np.sqrt(abs(ref_sq)))


def _probe_ey(field_real, field_imag, points: np.ndarray, comm: MPI.Comm):
    """``E_y`` (real and imaginary parts) at ``points``, validity enforced.

    Point evaluation goes through ``evaluate_vector_field_parallel``: the points
    live on whichever rank owns their cell, and a point nobody owns must be an
    error, not a silent zero.
    """
    real_values, valid_real = evaluate_vector_field_parallel(field_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(field_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(f"{int((~valid).sum())} probe points were not evaluated")
    return np.real(real_values[:, 1]), np.real(imag_values[:, 1])


def _fit_gamma(zs: np.ndarray, ey_real: np.ndarray, ey_imag: np.ndarray) -> float:
    """``ln|E_y| = −γz + const`` — the slope of a straight line in ``z``."""
    amplitude = np.abs(ey_real + 1j * ey_imag)
    return -float(np.polyfit(zs, np.log(amplitude), 1)[0])


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

    gamma_exact = _analytic_gamma(FREQUENCY_HZ)
    k_c = float(np.pi / A_M)
    k0 = _k0(FREQUENCY_HZ)
    f_c = cutoff_frequency_hz()

    if comm.rank == 0:
        print("=" * 72)
        print("EX-7 — evanescent TE10: decay with no loss anywhere in the problem")
        print("=" * 72)
        print(
            f"\n[geometry] PEC guide {A_M} x {B_M} x {L_M} m; the exact evanescent "
            f"field is Dirichlet data on the whole boundary, which pins the two end "
            f"faces — the slope between them is the solver's own output"
            f"\n[material] eps_r = 1, mu_r = 1, sigma = 0 — lossless, so nothing in "
            f"the medium can be causing the decay, and the phasor must come out real"
            f"\n[regime] f = {FREQUENCY_HZ / 1e9:.4g} GHz against the TE10 cutoff "
            f"f_c = c/2a = {f_c / 1e9:.4g} GHz: below cutoff, so the mode is "
            f"evanescent and gamma is real (no pole in the band)"
            f"\n[closed form] k_c = {k_c:.4f} 1/m, k0 = {k0:.4f} 1/m, "
            f"gamma = sqrt(k_c^2 - k0^2) = {gamma_exact:.6f} Np/m "
            f"(gamma*L = {gamma_exact * L_M:.3f}, an amplitude drop of "
            f"{np.exp(gamma_exact * L_M):.2f}x across the guide)"
            f"\n[vs EX-4] `EX-4` decays because Im(eps_c) absorbs the wave; here the "
            f"operator's real part alone does it, and a solver blind to k0 would "
            f"still decay — at k_c = {k_c:.2f} Np/m, {k_c / gamma_exact:.2f}x too "
            f"fast, at every frequency",
            flush=True,
        )

    solve_started = time.perf_counter()
    msh, fields, exact_ufl, n_cells = _solve()
    solve_seconds = time.perf_counter() - solve_started

    # ---- the anchor: fitted gamma vs sqrt(k_c^2 - k0^2) ---------------------
    points = _probe_points()
    zs = points[:, 2]
    ey_real, ey_imag = _probe_ey(fields.e_real, fields.e_imag, points, comm)
    gamma_fit = _fit_gamma(zs, ey_real, ey_imag)
    gamma_error = abs(gamma_fit - gamma_exact) / gamma_exact
    imag_ratio = float(np.max(np.abs(ey_imag)) / np.max(np.abs(ey_real)))
    rel_l2 = _relative_l2_error(msh, fields, exact_ufl, comm)

    if comm.rank == 0:
        print(
            f"\n[solve] {n_cells} cells (n = {RESOLUTION_N} — the `TH-7` gate's "
            f"finer mesh), solved in {solve_seconds:.1f} s"
            f"\n[decay] {points.shape[0]} probe points on an off-lattice line, fit "
            f"window z/L in [{zs[0] / L_M:.2f}, {zs[-1] / L_M:.2f}] (the drive and "
            f"far faces are excluded — fitting them fits the boundary data): "
            f"gamma = {gamma_fit:.6f} Np/m vs closed form {gamma_exact:.6f} Np/m "
            f"({gamma_error:.3%}, ceiling {GAMMA_RTOL:.0%}, "
            f"{RECORD_GAMMA_ERROR:.3%} on the TH-7 record)"
            f"\n[field] whole-domain relative L2 error {rel_l2:.6e} "
            f"({RECORD_REL_L2:.6e} on the record), residual |Im E_y|/|Re E_y| on "
            f"the line {imag_ratio:.3e} — lossless and real-data, so the quadrature "
            f"component is round-off or the convention has leaked",
            flush=True,
        )

    assert gamma_error < GAMMA_RTOL, (
        f"the fitted decay constant {gamma_fit:.6f} Np/m misses the closed form "
        f"{gamma_exact:.6f} Np/m by {gamma_error:.2%}, over the {GAMMA_RTOL:.0%} MVP "
        f"ceiling and against {RECORD_GAMMA_ERROR:.3%} on the `TH-7` record at this "
        f"same mesh — a regression finding, not a tolerance to move"
    )
    assert rel_l2 < FIELD_L2_MAX, (
        f"relative L2 error {rel_l2:.4e} against the analytic evanescent TE10 field "
        f"exceeds the {FIELD_L2_MAX:.0%} MVP criterion ({RECORD_REL_L2:.4e} on the "
        f"record) — the slope can be right while the mode is not"
    )
    assert imag_ratio < IMAG_RATIO_MAX, (
        f"|Im E_y|/|Re E_y| = {imag_ratio:.3e} on a lossless problem with real data "
        f"— the e^{{+jwt}} convention or a stray Im(eps_c) has leaked an imaginary "
        f"part (0.000e+00 on the record)"
    )

    # ---- the exported field is the asserted field ---------------------------
    e_re, e_im, e_mag = _paraview_fields(msh, fields)
    cg_real, cg_imag = _probe_ey(e_re, e_im, points, comm)
    gamma_cg = _fit_gamma(zs, cg_real, cg_imag)
    cg_vs_nedelec = abs(gamma_cg - gamma_fit) / gamma_fit

    profile_points = _profile_points()
    prof_real, prof_imag = _probe_ey(e_re, e_im, profile_points, comm)
    prof_amp = np.abs(prof_real + 1j * prof_imag)
    prof_exact = np.sin(np.pi * profile_points[:, 0] / A_M)
    # Amplitude is set by the e^{-gamma z} factor at this z, which the axial fit
    # already owns; the *shape* is what this checks, so both curves are scaled to
    # unit peak before they are compared.
    profile_rms = float(
        np.sqrt(np.mean((prof_amp / np.max(prof_amp) - prof_exact / np.max(prof_exact)) ** 2))
    )

    if comm.rank == 0:
        print(
            f"\n[cross-check] the same decay, refitted from the CG1 array that is "
            f"written to XDMF: gamma = {gamma_cg:.6f} Np/m, {cg_vs_nedelec:.3%} from "
            f"the N1curl fit — so what ParaView colours is the field the anchor was "
            f"measured on, not a look-alike"
            f"\n[mode profile] {N_PROFILE} points across the guide at z = "
            f"{PROFILE_Z_FRACTION:.2f} L, x/a in "
            f"[{PROFILE_X_MIN_FRACTION:.2f}, {PROFILE_X_MAX_FRACTION:.2f}]: "
            f"peak-normalised |E_y| is {profile_rms:.3%} RMS from sin(pi x/a) — the "
            f"TE10 half-arch is in the exported array, not just in the picture",
            flush=True,
        )

    assert cg_vs_nedelec < CG1_VS_NEDELEC_MAX, (
        f"the decay refitted from the exported CG1 field ({gamma_cg:.6f} Np/m) and "
        f"the one asserted above ({gamma_fit:.6f} Np/m) differ by "
        f"{cg_vs_nedelec:.2%} — the array being exported is not the field the anchor "
        f"was read from"
    )
    assert profile_rms < PROFILE_RMS_MAX, (
        f"the exported transverse profile is {profile_rms:.2%} RMS from sin(pi x/a) "
        f"after peak normalisation — the exported mode is not TE10, whatever the "
        f"axial slope reads"
    )

    # ---- negative control: cited, not recomputed (§7 `EX-7` plan) -----------
    if comm.rank == 0:
        print(
            f"\n[control] this gate cannot pass by reading back its own boundary "
            f"data, and the `TH-7` gate measured that: a k0-blind solver returns "
            f"gamma = k_c = {k_c:.4f} Np/m at *every* frequency, so its gamma across "
            f"the gate's 1.0/2.4/2.8 GHz sweep would have ratio "
            f"{BLIND_SWEEP_RATIO:.1f}. The measured ratio was "
            f"{RECORD_SWEEP_RATIO:.4f} against the closed form's "
            f"{RECORD_SWEEP_RATIO_EXACT:.4f} "
            f"({abs(RECORD_SWEEP_RATIO - RECORD_SWEEP_RATIO_EXACT) / RECORD_SWEEP_RATIO_EXACT:.3%}), "
            f"asserted > 2.0 — cited from 20260731T123411Z_TH-7-gate-final.log, not "
            f"re-run (sweep frequencies {', '.join(f'{f / 1e9:.1f}' for f in SWEEP_HZ)} "
            f"GHz). This run's own share of that control: gamma = {gamma_fit:.4f} "
            f"sits {k_c / gamma_fit:.2f}x below k_c, which a k0-blind operator "
            f"cannot do at any mesh",
            flush=True,
        )

    assert gamma_fit < k_c, (
        f"the fitted gamma {gamma_fit:.4f} Np/m is not strictly below the cutoff "
        f"wavenumber k_c = {k_c:.4f} Np/m — the k0^2*eps term is not reaching the "
        f"operator, which is exactly the blind case the cited sweep rules out"
    )
    assert RECORD_SWEEP_RATIO > 2.0 > BLIND_SWEEP_RATIO, (
        "the cited frequency-sweep control no longer separates a k0-aware solver "
        "from a blind one, so the discrimination this control claims is not the one "
        "the gate measured"
    )

    # ---- ParaView -----------------------------------------------------------
    mag_local = np.real(e_mag.x.array)
    mag_max = comm.allreduce(
        float(np.max(mag_local)) if mag_local.size else 0.0, op=MPI.MAX
    )
    mag_min = comm.allreduce(
        float(np.min(mag_local)) if mag_local.size else np.inf, op=MPI.MIN
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        None,  # a structured box: one homogeneous medium, nothing to threshold on
        {"E_real": e_re, "E_imag": e_im, "E_magnitude": e_mag},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    if comm.rank == 0:
        print(
            f"\n[paraview] wrote {xdmf_path}"
            f"\n[paraview] |E| spans {mag_min:.6e} … {mag_max:.6e} V/m over the "
            f"guide — the floor is the PEC side wall at x = 0, a, where sin(pi x/a) "
            f"pins the field to zero, and the peak is the drive face"
            f"\n[paraview] colour by `E_magnitude`: `Plot Over Line` along z on a log "
            f"scale is the straight line whose slope is the gamma asserted above; "
            f"the same filter along x at fixed z is the sin(pi x/a) half-arch."
            f"\n\nAll assertions hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )

    assert mag_min < 0.2 * mag_max, (
        f"the exported |E| array spans only {mag_max / max(mag_min, 1e-300):.2f}x "
        f"across the guide; the PEC walls and the {np.exp(gamma_exact * L_M):.1f}x "
        f"axial decay together have to leave a far wider range than that"
    )


if __name__ == "__main__":
    main()
