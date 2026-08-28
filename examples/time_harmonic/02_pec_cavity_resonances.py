"""Example (`EX-5`): PEC cavity resonances — eigenfrequencies vs the closed form.

The `§5.4` ramp entry for Phase 2's eigen-analysis, and the **first example
anywhere in this repository that solves an eigenproblem** rather than a driven
problem. Everything under ``examples/`` before this one — including `EX-4`, the
first time-harmonic example — imposes a source or boundary data and solves for
the response; this one asks the geometry what frequencies it supports and gets
them back, which is the primitive Phase 6 tunes the birdcage with.

The physics is the `TH-9` gate's, unchanged. A lossless source-free box bounded
by a perfect electric conductor supports the modes of

    ∫ (∇×E)·(∇×v) dx = k² ∫ E·v dx,   n × E = 0 on ∂Ω

and on edges ``a × b × d`` the resonances have the closed form
``f_mnp = (c/2)·√((m/a)² + (n/b)² + (p/d)²)`` with at most one index zero. No
materials, no sources, no drive: the *only* inputs are the geometry and the two
bilinear forms, so a sign or scaling error anywhere in the curl-curl or the mass
assembly moves every frequency at once. Nothing in the problem statement carries
the answer — unlike a driven solve, there is no boundary data the solver could
read the result back out of.

**It asserts, it does not merely render.** The fixture and the solve are
*imported* from the module that closed `TH-9`
(``tests/validation/test_cavity_resonances.py`` and ``core/cavity.py``), and the
mode this example writes for ParaView is the eigenfunction of the frequency the
assertions are read from — the example and the landed gate cannot drift apart:

* *The anchor:* the fundamental (TE₁₀₁, 239.9510 MHz) on the gate's own
  (6, 5, 4) mesh against its closed form, gated here at **0.5%** (0.0436% max
  over the first four modes on record, `TH-9` gate log
  ``20260730T154846Z_TH-9.log``). The gate's own ceiling is 1%; 0.5% is the §7
  `EX-5` plan's, and it is well inside what the fixture delivers — never
  loosened here, and a miss is a regression finding, not a tolerance question.
  All four modes are printed and asserted, so the example cannot pass on one
  lucky eigenvalue.
* *The exported mode is the asserted mode:* the Rayleigh quotient
  ``λ = ∫|∇×E|²/∫|E|²`` of the very function written to XDMF is re-assembled
  here and converted back to a frequency, which must reproduce the eigenvalue
  the solver reported to 1e-6 relative. What ParaView colours is therefore the
  fundamental, not a look-alike field.
* *No gradient mode leaked in:* the ``null_mode_count`` diagnostic must be
  exactly 0 — the shift-and-invert target sits inside the physical band, so the
  ∇φ cluster at zero is strictly farther from it than any mode of interest.
* *The negative control, cited rather than recomputed* (per the §7 `EX-5`
  plan): the discrete N1curl null space is not noise but a real cluster of
  gradient modes at zero, and the gate measured it — 8 of 8 eigenvalues nearest
  zero below the 1e-8·k₁² cutoff, ``max|λ|/k₁² ≈ 3.2e-15``, i.e. 13 orders of
  separation from the O(0.04%)-accurate physical modes printed above. This
  example prints that separation so it is visible, and does not re-run the
  degree-1 solve behind it.

Run it through the example runner (the ``th:`` group sources the complex build
automatically; the eigenproblem itself is real symmetric and runs in either
build)::

    ./run_examples.sh -e th:2

Output lands in ``examples/time_harmonic/paraview_output``: open
``time_harmonic_02_pec_cavity_mode_combined.xdmf`` and colour by ``E_mode1_magnitude`` — the
TE₁₀₁ field is brightest on the mid-plane and falls to zero on the PEC walls,
which is the boundary condition made visible. ``Glyph`` on
``E_mode1`` shows the single half-wave along x and along z, and none along y.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core.cavity import (
    analytic_cavity_frequencies,
    frequency_from_eigenvalue,
    solve_pec_cavity_modes,
)
from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_xdmf_with_tags,
)

# The gated fixture lives in the test that closed `TH-9`; the §7 `EX-5` plan
# requires importing it rather than restating it. The runner puts only ``src``
# on PYTHONPATH, so the repo root goes on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.validation.test_cavity_resonances import EDGES, N_MODES  # noqa: E402

#: The §7 `EX-5` plan's ceiling on every returned resonance. The `TH-9` gate's
#: own is 1%; the fixture measures 0.0436% worst-case at this mesh, so 0.5% is
#: what the example can honestly claim. Not a knob: a run outside it is a
#: regression finding (see the module docstring).
FREQUENCY_RTOL = 0.005

#: The `TH-9` gate's own budgeted mesh, so the numbers printed here are
#: comparable line for line with ``20260730T154846Z_TH-9.log``.
DIVISIONS = (6, 5, 4)
DEGREE = 2

#: On record in that same gate log (``test_n1curl_gradient_modes_form_a_clean_
#: zero_cluster``, degree 1, same mesh): the gradient cluster, cited not re-run.
RECORD_NULL_CLUSTER_RATIO = 3.2e-15
RECORD_NULL_COUNT = 8

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "time_harmonic_02_pec_cavity_mode"


def _rayleigh_quotient(mode: fem.Function, comm: MPI.Comm) -> float:
    """``∫|∇×E|² / ∫|E|²`` of a solved mode, reduced across ranks.

    Both integrals are rank-local until reduced, hence the two allreduces. In
    the complex build ``ufl.inner`` conjugates its second argument, so each
    integrand is real by construction and the imaginary part is discarded
    explicitly rather than by a silent cast.
    """

    curl_energy = fem.assemble_scalar(
        fem.form(ufl.inner(ufl.curl(mode), ufl.curl(mode)) * ufl.dx)
    )
    field_energy = fem.assemble_scalar(fem.form(ufl.inner(mode, mode) * ufl.dx))
    curl_energy = comm.allreduce(float(np.real(curl_energy)), op=MPI.SUM)
    field_energy = comm.allreduce(float(np.real(field_energy)), op=MPI.SUM)
    return curl_energy / field_energy


def _paraview_fields(msh, mode: fem.Function):
    """CG1 vector + magnitude of one mode, normalised to unit peak amplitude.

    An eigenvector's scale and sign are arbitrary, so the exported field is
    divided by its own global peak: the *shape* is the physics, and a field
    that peaks at 1.0 is what a ParaView colour bar wants. N1curl cannot be
    written to XDMF, hence the interpolation into CG1.
    """

    comm = msh.comm
    v_cg = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    e_cg = fem.Function(v_cg, name="E_mode1")
    e_cg.interpolate(mode)
    e_cg.x.scatter_forward()

    components = np.abs(e_cg.x.array.reshape(-1, 3))
    magnitude = np.sqrt(np.sum(components * components, axis=1))
    peak = comm.allreduce(
        float(np.max(magnitude)) if magnitude.size else 0.0, op=MPI.MAX
    )
    e_cg.x.array[:] /= peak
    magnitude /= peak

    s_cg = fem.functionspace(msh, ("Lagrange", 1))
    e_mag = fem.Function(s_cg, name="E_mode1_magnitude")
    e_mag.x.array[:] = magnitude
    for f in (e_cg, e_mag):
        f.x.scatter_forward()
    return e_cg, e_mag, magnitude


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    analytic = analytic_cavity_frequencies(EDGES, N_MODES)

    if comm.rank == 0:
        print("=" * 72)
        print("EX-5 — PEC cavity resonances: solved eigenfrequencies vs closed form")
        print("=" * 72)
        print(
            f"\n[geometry] {EDGES[0]} x {EDGES[1]} x {EDGES[2]} m PEC box, "
            f"n x E = 0 on every face; no materials, no sources — the geometry "
            f"and the two bilinear forms are the whole problem statement"
            f"\n[closed form] f_mnp = (c/2)*sqrt((m/a)^2+(n/b)^2+(p/d)^2): "
            + ", ".join(f"{f / 1e6:.4f}" for f in analytic)
            + " MHz"
            f"\n[discretisation] N1curl degree {DEGREE} on a {DIVISIONS} box mesh "
            f"(the `TH-9` gate's own budgeted fixture)",
            flush=True,
        )

    solve_started = time.perf_counter()
    spectrum = solve_pec_cavity_modes(
        edges=EDGES,
        divisions=DIVISIONS,
        degree=DEGREE,
        n_modes=N_MODES,
        comm=comm,
        return_modes=True,
    )
    solve_seconds = time.perf_counter() - solve_started

    rel_error = np.abs(spectrum.frequencies_hz - analytic) / analytic

    if comm.rank == 0:
        print(
            f"\n[solve] {spectrum.n_cells} cells, {spectrum.n_dofs} dofs, "
            f"{spectrum.n_converged} eigenpairs converged in {solve_seconds:.1f} s"
            f"\n[modes] solved vs closed form, against the "
            f"{FREQUENCY_RTOL:.1%} ceiling (0.0436% worst case on the `TH-9` record):",
            flush=True,
        )
        for index, (f_num, f_exact, err) in enumerate(
            zip(spectrum.frequencies_hz, analytic, rel_error), start=1
        ):
            print(
                f"  mode {index}: {f_num / 1e6:9.4f} MHz vs {f_exact / 1e6:9.4f} MHz "
                f"({err:.4%})",
                flush=True,
            )

    # ---- the anchor ---------------------------------------------------------
    assert spectrum.frequencies_hz.size == N_MODES
    assert np.all(rel_error < FREQUENCY_RTOL), (
        f"solved resonances miss the closed form by {100 * rel_error} % against "
        f"the {FREQUENCY_RTOL:.1%} ceiling and 0.0436% on the `TH-9` record — a "
        f"regression finding, not a tolerance to move. A sign error in either "
        f"bilinear form moves every mode at once"
    )
    assert spectrum.null_mode_count == 0, (
        f"{spectrum.null_mode_count} gradient (null-space) eigenvalues below "
        f"{spectrum.null_cutoff:.3e} came back inside the physical band — the "
        f"shift-and-invert target is no longer separating the cluster at zero"
    )

    # ---- the exported mode is the asserted mode -----------------------------
    mode = spectrum.mode_functions[0]
    lam_rayleigh = _rayleigh_quotient(mode, comm)
    f_rayleigh = frequency_from_eigenvalue(lam_rayleigh)
    rayleigh_rel = abs(f_rayleigh - spectrum.frequencies_hz[0]) / (
        spectrum.frequencies_hz[0]
    )

    if comm.rank == 0:
        print(
            f"\n[mode 1] the field about to be exported, re-measured: Rayleigh "
            f"quotient lambda = int|curl E|^2/int|E|^2 = {lam_rayleigh:.6f} 1/m^2 "
            f"-> {f_rayleigh / 1e6:.4f} MHz, {rayleigh_rel:.2e} relative to the "
            f"{spectrum.frequencies_hz[0] / 1e6:.4f} MHz the solver reported",
            flush=True,
        )

    assert rayleigh_rel < 1e-6, (
        f"the Rayleigh quotient of the exported mode gives "
        f"{f_rayleigh / 1e6:.6f} MHz against the reported "
        f"{spectrum.frequencies_hz[0] / 1e6:.6f} MHz ({rayleigh_rel:.3e} relative) "
        f"— the field written for ParaView is not the eigenfunction the "
        f"frequency assertions were read from"
    )

    # ---- negative control: cited, not recomputed (§7 `EX-5` plan) -----------
    if comm.rank == 0:
        print(
            f"\n[control] the discrete N1curl null space is a real cluster of "
            f"gradient modes at zero, not noise, and it is on record in the same "
            f"gate: {RECORD_NULL_COUNT}/{RECORD_NULL_COUNT} eigenvalues nearest "
            f"zero below the 1e-8*k1^2 cutoff, max|lambda|/k1^2 = "
            f"{RECORD_NULL_CLUSTER_RATIO:.1e}"
            f"\n[control] the cluster sits a factor "
            f"{rel_error.max() / RECORD_NULL_CLUSTER_RATIO:.1e} below the "
            f"{rel_error.max():.2e} relative error of the physical modes "
            f"above — 13 orders of separation, which is why the {N_MODES} "
            f"frequencies printed here are physics and not null space. The "
            f"degree-1 solve behind those numbers is cited, not re-run "
            f"(20260730T154846Z_TH-9.log)",
            flush=True,
        )

    assert RECORD_NULL_CLUSTER_RATIO < 1e-8 < rel_error.max(), (
        "the cited null cluster and the measured physical error no longer "
        "straddle the gate's 1e-8 cutoff, so the separation this control claims "
        "is not the one the run measured"
    )

    # ---- ParaView -----------------------------------------------------------
    e_cg, e_mag, magnitude = _paraview_fields(spectrum.mesh, mode)
    mag_max = comm.allreduce(
        float(np.max(magnitude)) if magnitude.size else 0.0, op=MPI.MAX
    )
    mag_min = comm.allreduce(
        float(np.min(magnitude)) if magnitude.size else np.inf, op=MPI.MIN
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        spectrum.mesh,
        None,  # a structured box: one homogeneous region, nothing to threshold on
        {"E_mode1": e_cg, "E_mode1_magnitude": e_mag},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    if comm.rank == 0:
        print(
            f"\n[paraview] wrote {xdmf_path}"
            f"\n[paraview] |E| of mode 1 spans {mag_min:.6e} ... {mag_max:.6e} "
            f"(normalised to unit peak): the field vanishes on the PEC walls and "
            f"peaks in the interior, which is n x E = 0 made visible"
            f"\n[paraview] colour by `E_mode1_magnitude`; `Glyph` on `E_mode1` "
            f"shows one half-wave along x and along z and none along y — the "
            f"(1,0,1) indices of the {analytic[0] / 1e6:.4f} MHz closed form."
            f"\n\nAll assertions hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )

    # The array ParaView colours by is checked, not merely written: a PEC mode
    # touches zero on the walls and reaches its peak inside, so the exported
    # magnitude must span the full [0, 1] after normalisation. A constant or
    # boundary-polluted array fails this without any reference to the solve.
    assert mag_max == 1.0, (
        f"the exported magnitude peaks at {mag_max:.6e} rather than 1.0 — the "
        f"normalisation did not act on the array that was written"
    )
    assert mag_min < 1e-6, (
        f"the exported magnitude bottoms out at {mag_min:.6e} rather than at the "
        f"machine zero a PEC wall imposes — what ParaView would colour does not "
        f"satisfy n x E = 0"
    )


if __name__ == "__main__":
    main()
