"""Example (`EX-60`): the lossy-wall cavity — Q against σ beside Pozar.

`th:2` (`EX-5`) solves the `TH-9` box with PEC walls: real eigenvalues, no
loss, infinite Q. This example keeps the box and the mode but swaps the
boundary model. The Dirichlet pin is replaced by Jin §5.8.3's third-kind
surface-impedance (Leontovich) term on every wall,

    A += jω₀μ₀/Z_s ∫_Γ (n × u)·(n × v) dS,   Z_s = (1 + j)√(ω₀μ₀/(2σ)),

so the pencil turns complex and non-Hermitian. The TE₁₀₁ eigenvalue picks up
Im λ, and ``Q = Re ω / (2|Im ω|)`` is read straight off it (``ω = c√λ``).
That is the `TH-14` step 1 gate, which closed 2026-09-13.

**It asserts, and it does not re-implement** (the `ANS-1` rule). The rung
list, the bands, the mesh and Pozar's closed form ``Q_c`` are all imported from
``tests/validation/test_cavity_leontovich_q.py``. The solve is the gate's own
``solve_impedance_wall_cavity_mode``, which gains one additive keyword here,
``return_mode``, so the example can export the eigenfunction whose Q it
asserts.

* *Anchor (a):* σ = 1e4 S/m, ``|Q/Q_c − 1| ≤ Q_TOLERANCE`` (5 %), with Re f
  inside `TH-9`'s 1 % band of the PEC control.
* *Anchor (b), the √σ identity:* ``Q(1e6)/Q(1e4) = √(1e6/1e4) = 10`` within
  ``SCALING_TOLERANCE`` (5 %).
* *Negative control:* the PEC pencil, solved the same non-Hermitian way,
  gives ``|Im λ|/Re λ ≤ CONTROL_IM_RE_BOUND``. The lossless box shows no
  damping, so the Im λ above comes from the wall term.
* *Damping sign:* Im ω > 0 on both lossy rungs (e^{jωt} decays).
* *The exported mode is the asserted mode:* for the σ = 1e4 eigenfunction,
  the generalized Rayleigh quotient ``(∫|∇×E|² + γ∫|n×E|²)/∫|E|²`` must return
  the solver's λ to 1e-6 relative.

Printed only: copper (σ = 5.8e7) as the PEC-limit reading, beside its
``Q_c``, and the wall RMS ``|n × E|`` relative to the volume RMS ``|E|``.
That ratio is zero on a PEC wall and O(|Z_s|/η₀) on a Leontovich wall. It
makes the unpinned boundary visible, and it is not a band.

One box, one mode, no coil. Run it::

    ./run_examples.sh -e th:10

Output: ``examples/time_harmonic/paraview_output/
time_harmonic_10_lossy_wall_cavity_q_combined.xdmf``. Colour it by
``E_magnitude_normalised``.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.core.cavity import solve_impedance_wall_cavity_mode  # noqa: E402
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.setup_figure import write_setup_figure  # noqa: E402
from fem_em_solver.utils.constants import MU_0  # noqa: E402

from tests.validation.test_cavity_leontovich_q import (  # noqa: E402
    CONTROL_IM_RE_BOUND,
    DEGREE,
    EDGES,
    FINE,
    Q_TOLERANCE,
    SCALING_TOLERANCE,
    SIGMA_COPPER,
    SIGMA_GATE,
    SIGMA_SCALING,
    TH9_FREQUENCY_BAND,
    pozar_te10l_q_conductor,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
FIGURE_DIR = Path(__file__).resolve().parent / "figures"
BASENAME = "time_harmonic_10_lossy_wall_cavity_q"

#: TE₁₀ℓ with ℓ = 1, the gate's own mode (``solve_impedance_wall_cavity_mode``'s
#: default ``mode_indices=(1, 0, 1)``).
ELL = 1

#: The `EX-5` exported-mode ceiling, reused for the complex Rayleigh quotient.
RAYLEIGH_RTOL = 1e-6


def _say(comm, msg):
    if comm.rank == 0:
        print(msg, flush=True)


def _rung_line(key, sigma, r):
    """The gate fixture's own print format, so lines compare with its log."""
    return (
        f"[{key:8s}] div={FINE} sigma={sigma} cells={r.n_cells} dofs={r.n_dofs} "
        f"nconv={r.n_converged} n_bc_local={r.n_constrained_dofs_local} "
        f"Z_s={r.surface_impedance_ohm} lambda={r.eigenvalue:.10e} "
        f"f={r.omega_rad_s / (2 * np.pi) / 1e6:.6f} MHz Q={r.q:.6e}"
    )


def _reduced(comm, form):
    return comm.allreduce(complex(fem.assemble_scalar(fem.form(form))), op=MPI.SUM)


def _rayleigh_quotient(mode, msh, z_s, omega_lin, comm):
    """``(∫|∇×E|² + γ∫|n×E|²) / ∫|E|²`` with ``γ = jωμ₀/Z_s``, reduced.

    ``ufl.inner`` conjugates its second slot and the N1curl basis is real, so
    each integral is ``xᴴAx`` / ``xᴴBx``. For a right eigenvector the quotient
    is λ exactly, up to the solver tolerance.
    """
    n = ufl.FacetNormal(msh)
    gamma = fem.Constant(msh, default_scalar_type(1j * omega_lin * MU_0 / complex(z_s)))
    num = _reduced(comm, ufl.inner(ufl.curl(mode), ufl.curl(mode)) * ufl.dx) + _reduced(
        comm, gamma * ufl.inner(ufl.cross(n, mode), ufl.cross(n, mode)) * ufl.ds
    )
    den = _reduced(comm, ufl.inner(mode, mode) * ufl.dx)
    return num / den


def _wall_to_volume_rms(mode, msh, comm):
    """RMS ``|n × E|`` over the walls divided by RMS ``|E|`` over the volume."""
    n = ufl.FacetNormal(msh)
    one = fem.Constant(msh, default_scalar_type(1.0))
    wall = _reduced(comm, ufl.inner(ufl.cross(n, mode), ufl.cross(n, mode)) * ufl.ds).real
    area = _reduced(comm, one * ufl.ds).real
    vol_e = _reduced(comm, ufl.inner(mode, mode) * ufl.dx).real
    vol = _reduced(comm, one * ufl.dx).real
    return float(np.sqrt(wall / area) / np.sqrt(vol_e / vol))


def _e_magnitude_dg0(mode, msh, comm):
    """``|E|`` as DG0, normalised by its global owned peak (the scale is arbitrary)."""
    dg0 = fem.functionspace(msh, ("DG", 0))
    e_sq = fem.Function(dg0)
    e_sq.interpolate(fem.Expression(ufl.inner(mode, mode), dg0.element.interpolation_points))
    mag = np.sqrt(np.maximum(np.real(e_sq.x.array), 0.0))
    n_owned = dg0.dofmap.index_map.size_local
    peak = comm.allreduce(float(np.max(mag[:n_owned])) if n_owned else 0.0, op=MPI.MAX)
    e_mag = fem.Function(dg0, name="E_magnitude_normalised")
    e_mag.x.array[:] = mag / peak
    e_mag.x.scatter_forward()
    return e_mag


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `th:` group)."
        )

    _say(comm, "=" * 78)
    _say(comm, "EX-60 -- the lossy-wall cavity: Q against sigma beside Pozar (TE101)")
    _say(comm, "=" * 78)
    _say(comm, f"\n[geometry] {EDGES} m box, N1curl degree {DEGREE}, divisions {FINE} "
               "(the TH-14 step 1 gate's fine rung)")

    rungs = {}
    for key, sigma in (
        ("pec", None),
        ("gate", SIGMA_GATE),
        ("scaling", SIGMA_SCALING),
        ("copper", SIGMA_COPPER),
    ):
        t = time.perf_counter()
        rungs[key] = solve_impedance_wall_cavity_mode(
            edges=EDGES, divisions=FINE, degree=DEGREE, sigma_s_per_m=sigma, comm=comm,
            return_mode=(key == "gate"),
        )
        _say(comm, _rung_line(key, sigma, rungs[key]) + f" ({time.perf_counter() - t:.1f}s)")

    pec, gate, scaling, copper = (rungs[k] for k in ("pec", "gate", "scaling", "copper"))

    # ---- setup figure (EX-57): the solver owns the mesh, so render on it ----
    write_setup_figure(
        gate.mesh,
        None,
        FIGURE_DIR / f"{BASENAME}_setup.png",
        region_names={0: "cavity (vacuum)"},
        slice_normal=(0.0, 1.0, 0.0),
        title="th:10 -- TH-9 box, Leontovich wall on every face (TE101, E along y)",
        comm=comm,
    )

    # ---- negative control: the PEC pencil has no damping --------------------
    control_ratio = abs(pec.eigenvalue.imag) / pec.eigenvalue.real
    f_pec = pec.omega_rad_s.real / (2 * np.pi)
    _say(comm, f"\n[control] PEC pencil |Im lambda|/Re lambda = {control_ratio:.3e} "
               f"(ASSERTED <= {CONTROL_IM_RE_BOUND:.0e})")
    assert control_ratio <= CONTROL_IM_RE_BOUND, control_ratio

    # ---- anchor (a): Q against Pozar at sigma = 1e4 ------------------------
    q_c = pozar_te10l_q_conductor(EDGES, ELL, SIGMA_GATE)
    miss = gate.q / q_c - 1.0
    df = gate.omega_rad_s.real / (2 * np.pi) / f_pec - 1.0
    _say(comm, f"[a] sigma = {SIGMA_GATE:.0e}: Q = {gate.q:.6e}, Pozar Q_c = {q_c:.6e}, "
               f"miss {100 * miss:+.3f}% (ASSERTED |miss| <= {100 * Q_TOLERANCE:.0f}%); "
               f"Re f shift vs PEC {100 * df:+.4f}% (ASSERTED < {100 * TH9_FREQUENCY_BAND:.0f}%)")
    assert abs(miss) <= Q_TOLERANCE, miss
    assert abs(df) < TH9_FREQUENCY_BAND, df

    # ---- anchor (b): the sqrt(sigma) identity -------------------------------
    expected = float(np.sqrt(SIGMA_SCALING / SIGMA_GATE))
    ratio = scaling.q / gate.q
    _say(comm, f"[b] Q({SIGMA_SCALING:.0e})/Q({SIGMA_GATE:.0e}) = {ratio:.6f} vs "
               f"sqrt(sigma ratio) = {expected:g}: miss {100 * (ratio / expected - 1):+.3f}% "
               f"(ASSERTED <= {100 * SCALING_TOLERANCE:.0f}%)")
    assert abs(ratio / expected - 1.0) <= SCALING_TOLERANCE, ratio

    # ---- damping sign -------------------------------------------------------
    for key in ("gate", "scaling"):
        _say(comm, f"[c] {key}: Im omega = {rungs[key].omega_rad_s.imag:+.6e} rad/s (ASSERTED > 0)")
        assert rungs[key].omega_rad_s.imag > 0.0, key

    # ---- printed: copper as the PEC-limit reading ---------------------------
    q_c_cu = pozar_te10l_q_conductor(EDGES, ELL, SIGMA_COPPER)
    _say(comm, f"\n[printed, no band] copper sigma = {SIGMA_COPPER:.1e}: Q = {copper.q:.6e}, "
               f"Pozar Q_c = {q_c_cu:.6e} (miss {100 * (copper.q / q_c_cu - 1):+.3f}%); "
               f"Im lambda/Re lambda = {copper.eigenvalue.imag / copper.eigenvalue.real:.3e} "
               f"vs the PEC control's {control_ratio:.3e}")

    # ---- the exported mode is the asserted mode -----------------------------
    mode = gate.mode_function
    msh = gate.mesh
    lam_rq = _rayleigh_quotient(mode, msh, gate.surface_impedance_ohm, gate.omega0_rad_s, comm)
    rq_rel = abs(lam_rq - gate.eigenvalue) / abs(gate.eigenvalue)
    _say(comm, f"\n[mode] sigma = {SIGMA_GATE:.0e} eigenfunction: Rayleigh quotient "
               f"{lam_rq:.10e} vs solver lambda {gate.eigenvalue:.10e}: rel {rq_rel:.3e} "
               f"(ASSERTED <= {RAYLEIGH_RTOL:g})")
    assert rq_rel <= RAYLEIGH_RTOL, (lam_rq, gate.eigenvalue, rq_rel)

    wall_ratio = _wall_to_volume_rms(mode, msh, comm)
    z_over_eta = abs(gate.surface_impedance_ohm) / (MU_0 * 299792458.0)
    _say(comm, f"[printed, no band] wall RMS |n x E| / volume RMS |E| = {wall_ratio:.3e} "
               f"beside |Z_s|/eta_0 = {z_over_eta:.3e} (order-of-magnitude context: the "
               "wall is not pinned)")

    # ---- ParaView -----------------------------------------------------------
    OUTPUT_DIR.mkdir(exist_ok=True)
    e_mag = _e_magnitude_dg0(mode, msh, comm)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined", msh, None,
        {"E_magnitude_normalised": e_mag}, comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    _say(comm, f"\n[output] {path} -- E_magnitude_normalised (DG0, TE101 at sigma = "
               f"{SIGMA_GATE:.0e}, unit peak)")
    _say(comm, f"\n[timing] total {time.perf_counter() - started:.1f} s at -n {comm.size}")
    _say(comm, "\nAll imported gates hold.")


if __name__ == "__main__":
    main()
