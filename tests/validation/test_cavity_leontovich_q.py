"""Validation test: Leontovich (surface-impedance) wall on the TH-9 cavity (TH-14 step 1).

The `TH-9` 1.0 × 0.8 × 0.6 m box with its Dirichlet PEC pin replaced by the
third-kind boundary term (Jin §5.8.3)

    jω₀μ₀/Z_s ∫_Γ (n × u)·(n × v) dS,   Z_s = (1 + j)√(ω₀μ₀/(2σ)),

linearised at the PEC TE₁₀₁ frequency ω₀ (≈ 291.4 MHz, the *second* mode of
this box — TE₁₁₀-like (1,1,0) at 240 MHz is lower). The complex eigenvalue
λ = k² gives ω = c√λ and Q = Re ω / (2|Im ω|), gated against Pozar's
perturbation closed form for TE₁₀ℓ

    Q_c = (kad)³ b η / (2π² R_s) · 1/(2a³b + 2bd³ + a³d + ad³).

Asserted (PROJECT_PLAN §9 item 2 of the 2026-09-13 18:00 review):
  (a) σ = 1e4 S/m, fine rung (9, 7, 6): |Q/Q_c − 1| ≤ 5 %, and Re f within the
      `TH-9` 1 % band of the PEC value;
  (b) Q(σ = 1e6)/Q(σ = 1e4) = 10 within 5 % (Q_c ∝ √σ);
  (c) lossy damping sign: Im ω > 0, i.e. e^{jωt} decays;
  control: the Dirichlet PEC pencil, solved GNHEP, |Im λ|/Re λ ≤ 1e-10.
Printed only: copper σ = 5.8e7, the coarse-rung (6, 5, 4) Q, and one
fixed-point update Z_s(Re ω).
"""

import time

import numpy as np
import pytest
from mpi4py import MPI
from petsc4py import PETSc

from fem_em_solver.core.cavity import (
    pozar_te10l_q_conductor,
    solve_impedance_wall_cavity_mode,
)

pytestmark = pytest.mark.skipif(
    not np.issubdtype(PETSc.ScalarType, np.complexfloating),
    reason="surface-impedance cavity needs the complex DolfinX build",
)

EDGES = (1.0, 0.8, 0.6)
FINE = (9, 7, 6)
COARSE = (6, 5, 4)
DEGREE = 2
SIGMA_GATE = 1.0e4
SIGMA_SCALING = 1.0e6
SIGMA_COPPER = 5.8e7

Q_TOLERANCE = 0.05  # pre-registered, §9 item 2 anchor (a)
SCALING_TOLERANCE = 0.05  # pre-registered, anchor (b)
TH9_FREQUENCY_BAND = 0.01  # TH-9's FREQUENCY_TOLERANCE_PCT = 1.0
CONTROL_IM_RE_BOUND = 1e-10  # pre-registered negative control


def _say(msg):
    if MPI.COMM_WORLD.rank == 0:
        print(msg, flush=True)


@pytest.fixture(scope="module")
def solves():
    comm = MPI.COMM_WORLD
    out = {}
    t0 = time.perf_counter()
    for key, divisions, sigma in (
        ("pec", FINE, None),
        ("gate", FINE, SIGMA_GATE),
        ("scaling", FINE, SIGMA_SCALING),
        ("copper", FINE, SIGMA_COPPER),
        ("coarse", COARSE, SIGMA_GATE),
    ):
        t = time.perf_counter()
        out[key] = solve_impedance_wall_cavity_mode(
            edges=EDGES, divisions=divisions, degree=DEGREE, sigma_s_per_m=sigma, comm=comm
        )
        r = out[key]
        _say(
            f"[TH-14] {key:8s} div={divisions} sigma={sigma} cells={r.n_cells} "
            f"dofs={r.n_dofs} nconv={r.n_converged} n_bc_local={r.n_constrained_dofs_local} "
            f"Z_s={r.surface_impedance_ohm} lambda={r.eigenvalue:.10e} "
            f"f={r.omega_rad_s / (2 * np.pi) / 1e6:.6f} MHz Q={r.q:.6e} "
            f"({time.perf_counter() - t:.1f}s)"
        )
    # One fixed-point update of Z_s(ω) at the gate rung: re-linearise at Re ω.
    t = time.perf_counter()
    out["gate_fp1"] = solve_impedance_wall_cavity_mode(
        edges=EDGES,
        divisions=FINE,
        degree=DEGREE,
        sigma_s_per_m=SIGMA_GATE,
        omega_linearisation_rad_s=out["gate"].omega_rad_s.real,
        comm=comm,
    )
    r = out["gate_fp1"]
    _say(
        f"[TH-14] fixed-point update (sigma=1e4, Z_s at Re omega): Z_s={r.surface_impedance_ohm} "
        f"Q={r.q:.6e} vs linearised Q={out['gate'].q:.6e} "
        f"(rel {r.q / out['gate'].q - 1:+.3e}); f={r.omega_rad_s.real / (2 * np.pi) / 1e6:.6f} MHz "
        f"({time.perf_counter() - t:.1f}s)"
    )
    _say(f"[TH-14] all solves elapsed={time.perf_counter() - t0:.1f}s")
    return out


@pytest.mark.validation
def test_pec_control_pencil_has_no_damping(solves):
    r = solves["pec"]
    ratio = abs(r.eigenvalue.imag) / r.eigenvalue.real
    f_pec = r.omega_rad_s.real / (2 * np.pi)
    f_exact = r.omega0_rad_s / (2 * np.pi)
    _say(
        f"[TH-14] control: |Im lambda|/Re lambda={ratio:.3e} (bound {CONTROL_IM_RE_BOUND:.0e}); "
        f"f_PEC={f_pec / 1e6:.6f} MHz vs closed form {f_exact / 1e6:.6f} MHz "
        f"({100 * abs(f_pec / f_exact - 1):.4f}%)"
    )
    assert ratio <= CONTROL_IM_RE_BOUND
    # The control found the right mode (TE101), inside TH-9's band.
    assert abs(f_pec / f_exact - 1) < TH9_FREQUENCY_BAND


@pytest.mark.validation
def test_leontovich_q_matches_pozar_closed_form(solves):
    gate = solves["gate"]
    q_c = pozar_te10l_q_conductor(EDGES, 1, SIGMA_GATE)
    miss = gate.q / q_c - 1.0
    f_re = gate.omega_rad_s.real / (2 * np.pi)
    f_pec = solves["pec"].omega_rad_s.real / (2 * np.pi)
    df = f_re / f_pec - 1.0
    coarse = solves["coarse"]
    copper = solves["copper"]
    q_c_cu = pozar_te10l_q_conductor(EDGES, 1, SIGMA_COPPER)
    _say(
        f"[TH-14] (a) sigma=1e4 fine: Q={gate.q:.6e} Q_c={q_c:.6e} miss={100 * miss:+.3f}% "
        f"(band {100 * Q_TOLERANCE:.0f}%); Re f={f_re / 1e6:.6f} MHz vs PEC "
        f"{f_pec / 1e6:.6f} MHz ({100 * df:+.4f}%, band {100 * TH9_FREQUENCY_BAND:.0f}%); "
        f"-1/(2Q_c)={-100 / (2 * q_c):+.4f}% (Pozar-perturbation shift, printed)"
    )
    _say(
        f"[TH-14] printed: coarse (6,5,4) Q={coarse.q:.6e} miss={100 * (coarse.q / q_c - 1):+.3f}%; "
        f"copper Q={copper.q:.6e} Q_c={q_c_cu:.6e} miss={100 * (copper.q / q_c_cu - 1):+.3f}% "
        f"(Im lambda/Re lambda={copper.eigenvalue.imag / copper.eigenvalue.real:.3e})"
    )
    assert abs(miss) <= Q_TOLERANCE
    assert abs(df) < TH9_FREQUENCY_BAND


@pytest.mark.validation
def test_q_scales_as_sqrt_sigma(solves):
    ratio = solves["scaling"].q / solves["gate"].q
    _say(
        f"[TH-14] (b) Q(1e6)/Q(1e4)={ratio:.6f} (expected 10, band "
        f"{100 * SCALING_TOLERANCE:.0f}%, miss {100 * (ratio / 10 - 1):+.3f}%)"
    )
    assert abs(ratio / 10.0 - 1.0) <= SCALING_TOLERANCE


@pytest.mark.validation
def test_damping_sign_is_lossy(solves):
    # e^{jωt}: a field ∝ e^{jωt} = e^{j Re ω t} e^{−Im ω t} decays iff Im ω > 0.
    for key in ("gate", "scaling", "coarse", "copper", "gate_fp1"):
        r = solves[key]
        _say(f"[TH-14] (c) {key}: Im omega={r.omega_rad_s.imag:+.6e} rad/s")
    for key in ("gate", "scaling", "coarse"):
        assert solves[key].omega_rad_s.imag > 0.0, key
