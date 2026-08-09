"""Example (`EX-4`): a solved lossy plane wave — decay and phase vs closed form.

The `§5.4` ramp entry for Phase 2, and the **first example anywhere in this
repository that runs a time-harmonic solve at all**. Everything under
``examples/`` before this one was either magnetostatic, a mesh fixture, or an
ungated end-to-end demo; the complex curl-curl solver that `TH-1`/`TH-6` closed
on 2026-07-31 had no runnable demonstration.

The physics is the `TH-6` gate's, unchanged. In the ``e^{+jωt}`` convention a
plane wave travelling in ``+x`` and polarised along ``z`` in a homogeneous lossy
medium is ``E = ẑ exp(−j k x)`` with ``k = k₀√(ε_c)``, ``ε_c = εᵣ − jσ/(ωε₀)``,
on the branch with ``Im k < 0``. Writing ``k = β − jα``, the amplitude falls as
``e^{−αx}`` and the phase advances as ``−βx``. The analytic field is imposed as
Dirichlet data on the *whole boundary* of the box and the **interior** slopes are
measured — nothing in the boundary data tells the interior how fast to decay,
so α and β are the solver's own output. Drop ``Im ε_c`` and α collapses to zero.

**It asserts, it does not merely render.** The constants, the fixture and the
solve are *imported* from the module that closed `TH-6`
(``tests/validation/test_lossy_plane_wave.py``), and the field this example
writes for ParaView is the very same solve object the assertions are read from —
the example and the landed gate cannot drift apart:

* *The anchor:* the fitted α and β on the 24³ mesh against their closed forms,
  gated here at **1%** (0.019% / 0.059% on record, `TH-6` gate log
  ``20260731T020427Z_TH-6-gate3.log``). The gate's own ceiling is 5%
  (PROJECT_PLAN §10's MVP criterion); 1% is the §7 `EX-4` plan's, and it is what
  the fixture actually delivers — never loosened here, and a miss is a
  regression finding, not a tolerance question.
* *The sign:* α > 0, i.e. the wave decays into the medium rather than growing
  out of it. A conjugated ``e^{−jωt}`` convention flips exactly this.
* *Convergence:* the relative L2 error against the analytic field falls under
  refinement at the O(h) rate N1curl degree 1 owes (0.9998 on record), so a
  coincidental match at one mesh size cannot pass.
* *The negative control, structural and cited rather than recomputed* (per the
  §7 `EX-4` plan): the same closed form at σ = 0 gives **α ≡ 0 exactly** — a
  lossless medium has no decay at all — against the ~13 Np/m measured here.
  The solved-field version of that separation is on record in the same gate log
  as `MAT-2`: σ = 0.1 → α = 2.1193 Np/m and σ = 1.4 → α = 21.878 Np/m, a ratio
  of 10.3232 against the closed-form 10.3116 (0.113%). This example does not
  re-run those solves.

Run it through the example runner (the ``th:`` group sources the complex build
automatically)::

    ./run_examples.sh -e th:1

Output lands in ``examples/time_harmonic/paraview_output``: open
``lossy_plane_wave_combined.xdmf`` and colour by ``E_magnitude`` — the field is
brightest on the ``x = 0`` face and fades by ~3.7× across the box. ``Plot Over
Line`` along x through the middle of the box reproduces the fitted exponential
directly; ``E_real``/``E_imag`` show the phase winding underneath it.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

# The gated constants, the fixture and the solve live in the test that closed
# `TH-6`; the §7 `EX-4` plan requires importing them rather than restating them.
# The runner puts only ``src`` on PYTHONPATH, so the repo root goes on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)

from tests.validation.test_lossy_plane_wave import (  # noqa: E402
    BOX_L,
    EPSILON_R,
    FREQUENCY_HZ,
    SIGMA,
    _analytic_alpha_beta,
    _solve_plane_wave,
    _wavenumber,
)

#: The §7 `EX-4` plan's ceiling on the fitted decay and phase constants. The
#: `TH-6` gate's own is 5% (§10's MVP criterion); the fixture measures 0.019% and
#: 0.059%, so 1% is what the example can honestly claim. Not a knob: a run
#: outside it is a regression finding (see the module docstring).
ALPHA_BETA_RTOL = 0.01

#: The `TH-6` gate's own mesh pair, so the numbers printed here are comparable
#: line for line with ``20260731T020427Z_TH-6-gate3.log``.
N_COARSE, N_FINE = 12, 24

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "lossy_plane_wave"


def _paraview_fields(msh, fields):
    """CG1 ``E_real`` / ``E_imag`` / ``E_magnitude`` from the solved phasor.

    The N1curl solution is interpolated once into a CG1 vector space (XDMF
    cannot carry N1curl), then split. ``|E|`` is the phasor magnitude
    ``sqrt(Σ|E_i|²)``, taken on the array so no complex ``sqrt`` is formed.
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

    k = _wavenumber(SIGMA)
    alpha_exact, beta_exact = _analytic_alpha_beta(SIGMA)
    skin_depth = 1.0 / alpha_exact

    if comm.rank == 0:
        print("=" * 72)
        print("EX-4 — lossy plane wave: solved decay and phase vs the closed form")
        print("=" * 72)
        print(
            f"\n[geometry] {BOX_L} m cube, the analytic wave imposed as Dirichlet "
            f"data on every face; the interior slopes are the solver's own output"
            f"\n[material] σ = {SIGMA} S/m, εᵣ = {EPSILON_R} at "
            f"f = {FREQUENCY_HZ / 1e6:.2f} MHz"
            f"\n[closed form] k = k₀√(ε_c) = {k:.6g} 1/m → α = {alpha_exact:.6f} Np/m, "
            f"β = {beta_exact:.6f} rad/m, δ = 1/α = {skin_depth * 1e3:.2f} mm"
            f"\n[box] αL = {alpha_exact * BOX_L:.3f} ({np.exp(alpha_exact * BOX_L):.2f}× "
            f"amplitude drop), βL = {beta_exact * BOX_L:.3f} rad of phase travel",
            flush=True,
        )

    # ---- the two solves: the `TH-6` gate's own coarse/fine pair --------------
    coarse_started = time.perf_counter()
    rel_coarse, alpha_coarse, beta_coarse, cells_coarse = _solve_plane_wave(
        N_COARSE, SIGMA
    )
    coarse_seconds = time.perf_counter() - coarse_started

    fine_started = time.perf_counter()
    rel_fine, alpha_fine, beta_fine, cells_fine, msh, fields = _solve_plane_wave(
        N_FINE, SIGMA, return_fields=True
    )
    fine_seconds = time.perf_counter() - fine_started

    rate = float(np.log(rel_coarse / rel_fine) / np.log(2.0))
    alpha_err = abs(alpha_fine - alpha_exact) / alpha_exact
    beta_err = abs(beta_fine - beta_exact) / beta_exact

    if comm.rank == 0:
        print(
            f"\n[solve] coarse {N_COARSE}³ ({cells_coarse} cells) in "
            f"{coarse_seconds:.1f} s: rel L2 = {rel_coarse:.6e}, "
            f"α = {alpha_coarse:.6f}, β = {beta_coarse:.6f}"
            f"\n[solve] fine   {N_FINE}³ ({cells_fine} cells) in "
            f"{fine_seconds:.1f} s: rel L2 = {rel_fine:.6e}, "
            f"α = {alpha_fine:.6f}, β = {beta_fine:.6f}"
            f"\n[rate]  measured L2 rate in h: {rate:.4f} "
            f"(O(h) expected for N1curl degree 1; 0.9998 on the `TH-6` record)"
            f"\n[α]     {alpha_fine:.6f} vs {alpha_exact:.6f} Np/m — "
            f"{alpha_err:.4%} against the {ALPHA_BETA_RTOL:.0%} ceiling "
            f"(0.019% on record)"
            f"\n[β]     {beta_fine:.6f} vs {beta_exact:.6f} rad/m — "
            f"{beta_err:.4%} against the {ALPHA_BETA_RTOL:.0%} ceiling "
            f"(0.059% on record)",
            flush=True,
        )

    # ---- the anchor ---------------------------------------------------------
    assert alpha_err < ALPHA_BETA_RTOL, (
        f"measured decay constant {alpha_fine:.6f} Np/m misses the closed form "
        f"{alpha_exact:.6f} Np/m by {alpha_err:.3%}, against the "
        f"{ALPHA_BETA_RTOL:.0%} ceiling and 0.019% on the `TH-6` record — a "
        f"regression finding, not a tolerance to move. A lost Im(ε_c) drives "
        f"this to zero"
    )
    assert beta_err < ALPHA_BETA_RTOL, (
        f"measured phase constant {beta_fine:.6f} rad/m misses the closed form "
        f"{beta_exact:.6f} rad/m by {beta_err:.3%}, against the "
        f"{ALPHA_BETA_RTOL:.0%} ceiling and 0.059% on the `TH-6` record"
    )
    assert alpha_fine > 0.0, (
        f"measured decay constant {alpha_fine:.6f} Np/m is not positive — the "
        "wave grows into the medium, i.e. the e^{+jωt} convention is conjugated"
    )
    assert rel_fine < rel_coarse, (
        f"refinement did not reduce the field error: {rel_coarse:.4e} -> "
        f"{rel_fine:.4e}"
    )
    assert rate > 0.9, (
        f"measured L2 convergence rate {rate:.4f} is below the O(h) expectation "
        "for N1curl degree 1 — the solve is not converging to the plane wave"
    )

    # ---- negative control: structural, cited (§7 `EX-4` plan) ----------------
    alpha_lossless, _ = _analytic_alpha_beta(0.0)

    if comm.rank == 0:
        print(
            f"\n[control] the same closed form at σ = 0 gives α = "
            f"{alpha_lossless:.1f} Np/m exactly — a lossless medium does not "
            f"attenuate — against {alpha_fine:.6f} Np/m measured here: total "
            f"separation, no tolerance needed"
            f"\n[control] the solved-field version is on record and is not re-run: "
            f"`MAT-2` in the same gate log measured α = 2.119307 Np/m at "
            f"σ = 0.1 S/m and 21.878059 Np/m at σ = 1.4 S/m — ratio 10.3232 vs "
            f"the closed-form 10.3116 (0.113%)",
            flush=True,
        )

    assert alpha_lossless == 0.0, (
        f"the closed form gives α = {alpha_lossless:.6e} Np/m at σ = 0; with a "
        "zero loss tangent the decay constant is identically zero, so anything "
        "else means the control is not lossless"
    )

    # ---- ParaView -----------------------------------------------------------
    e_re, e_im, e_mag = _paraview_fields(msh, fields)
    # In complex mode every Function is complex-dtype even when its values are
    # real, as ``E_magnitude``'s are by construction; take the real part
    # explicitly rather than let float() discard a zero imaginary part.
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

    # The array ParaView colours by is checked, not merely written: across the
    # box |E| must span the e^{αL} the closed form predicts. The extrema sit on
    # the Dirichlet faces where |E| is pinned to e^{−αx}, so this is a bound on
    # the exported array, not a second measurement of α.
    span = mag_max / mag_min
    span_exact = float(np.exp(alpha_exact * BOX_L))

    if comm.rank == 0:
        print(
            f"\n[paraview] wrote {xdmf_path}"
            f"\n[paraview] |E| spans {mag_min:.6e} … {mag_max:.6e} V/m across the "
            f"box — a {span:.3f}× drop against the closed-form {span_exact:.3f}× "
            f"between the x = 0 and x = L faces"
            f"\n[paraview] colour by `E_magnitude`; `Plot Over Line` along x shows "
            f"the exponential the fit above measured, and `E_real`/`E_imag` the "
            f"phase winding underneath it."
            f"\n\nAll assertions hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )

    assert 0.9 * span_exact < span < 1.1 * span_exact, (
        f"the exported |E| array spans {span:.3f}× across the box against the "
        f"closed-form {span_exact:.3f}× — what ParaView would colour is not the "
        f"field the assertions above were read from"
    )


if __name__ == "__main__":
    main()
