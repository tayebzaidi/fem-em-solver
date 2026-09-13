"""`TH-19` step 3 — the two power identities at **degree 2** on the sheet-driven 4-leg birdcage.

**Why.**  `TH-19` steps 1–2 showed the degree-2 complex-power identity on the
*coil* fixture was the CG1 ∩ H¹₀ source projection's residue (outcome (a)):
under ``project_source="matched"`` it holds by five orders.  The birdcage's
lumped-sheet drive never reaches that projection — the driver passes
``current_density=None, project_source=False``
(:func:`~fem_em_solver.ports.lumped.run_lumped_sheet_port_case`) — so the
`TH-12` objection to degree 2 has never been tested on the drive the
production-order clause is about.  **That bypass is the object under test and
is left untouched here**: the drive goes through the package driver with
``degree=2`` and nothing else changed.

**Fixture.**  :func:`build_four_port_sweep` with ``build_only=True`` (imported,
never rebuilt) at 10 or 128 MHz — the 116 085-cell `GEO-19` mesh, the four
50 Ω sheets, P1 driven, P2–P4 terminated.  One frequency per process, selected
by ``TH19_STEP3_FREQ_MHZ`` (``10`` or ``128``; **no default**, an unset
selector raises) so each window returns its footer inside a foreground window.

**Anchors, on the degree-2 P1 solve** (both asserted):

(a) `PORT-16`'s exact discrete identity ``P_src,exact = P_vol + P_sheet,exact``
    at the imported ``DISCRETE_IDENTITY_RTOL`` (1e-6).  The terms are assembled
    by that module's own helpers (``_exact_shares``), i.e. through the
    package's sheet form builders with the solved phasor in both slots.

(b) the reactive identity ``Im S_src = 2ω(W_m − W_e)`` at the `TH-12` family
    band ``IDENTITY_TOLERANCE`` (1e-9), imported from its defining module
    ``test_coil_loading_larmor_probe`` (the module the `TH-12`/`TH-19` pair
    module imports it from).  Derivation, same as `PORT-16`'s for (i): with
    PEC data ``E`` is its own test function, so ``a(E,E) = L(E)`` exactly.
    ``S_src ≡ −½∫_S E·conj(K_imp) dA`` (supplied complex power on the
    ``e^{+jωt}`` convention) equals ``j·conj(L(E))/(2ωμ₀)``, so
    ``Re S_src = Im L(E)/(2ωμ₀) = P_src,exact`` and
    ``Im S_src = Re L(E)/(2ωμ₀)``.  The real part of ``a(E,E)`` is
    ``∫|∇×E|² − k₀²∫εᵣ|E|²`` (μᵣ = 1 on this fixture; ``Re(jωμ₀Y_s) = 0``
    for the real 50 Ω sheets; the solver adds no gauge term —
    ``gauge_penalty`` is ignored by ``TimeHarmonicSolver.solve``)
    ``= 4ω²μ₀(W_m − W_e)``, hence (b).  ``W_e`` and ``W_m`` are the family's
    own helpers (``stored_electric_energy``, ``_stored_magnetic_energy``).
    Relative residual ``|Im S − 2ω(W_m − W_e)|/|Im S|``, the shape of the
    `TH-12` residual ``|Im Z_reaction − Im Z_energy|/|Im Z_reaction|``.

``W_e``, ``W_m`` and ``W_e/W_m`` are printed for degree 2 beside degree 1's.

**Negative control (asserted, by record).**  The degree-1 P1 solve on the same
route in the same process reproduces `PORT-16` step 1's P1 readings —
``P_src,exact`` 3.143759587e-03 W, ``P_vol`` 4.482780406e-04 W,
``P_sheet,exact`` 2.695481546e-03 W (`20260907T051231Z_PORT-16.log:1882`,
re-read by `20260907T110826Z_PORT-16.log:1948`) at that module's own
record-reproduction tolerance ``STEP2D_10MHZ_RTOL`` (1e-5, imported), and its
rel dev under ``DISCRETE_IDENTITY_RTOL`` (the fourth reading, 6.760e-15 there).
Records exist at 10 MHz only, so the by-record control runs in the 10 MHz
window; the 128 MHz window prints the degree-1 readings and asserts only the
two identities at degree 1 (theorems, same bands) as its same-process control.
Record width is ``-n 2``; this module runs at ``-n 8`` — these are integrals,
not the point-sampled ``V`` `OPS-41` found width-sensitive.

**Scope.**  Two identities at degree 2 on one fixture.  No accuracy claim, no
default change, no band moved, ``src/`` untouched.

Run (complex build required), one frequency per window::

    scripts/testing/run_and_log.sh TH-19-step3 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 TH19_STEP3_FREQ_MHZ=10 \\
       timeout -k 30 590 mpiexec -n 8 python3 -m pytest \\
       tests/validation/test_birdcage_power_identity_degree2.py -v -s --tb=short'"
"""

from __future__ import annotations

import os
import resource
import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core.resonance import stored_electric_energy
from fem_em_solver.ports.lumped import lumped_port_linear_term, run_lumped_sheet_port_case
from fem_em_solver.utils.constants import MU_0

from tests.complex_mode import complex_only
from tests.validation.test_birdcage_power_identity import (
    DISCRETE_IDENTITY_RTOL,
    STEP2D_10MHZ_RTOL,
    _exact_shares,
    _reduce,
)
from tests.validation.test_coil_loading_larmor_probe import (
    IDENTITY_TOLERANCE,
    _stored_magnetic_energy,
)
from tests.validation.test_port_birdcage_four_port import build_four_port_sweep
from tests.validation.test_port_birdcage_lumped_column import STEP2_CELL_COUNT

FREQ_ENV = "TH19_STEP3_FREQ_MHZ"
FREQUENCIES_HZ = {"10": 10.0e6, "128": 128.0e6}
DRIVEN = "P1"

# `PORT-16` step 1's P1 readings at 10 MHz, degree 1, `-n 2`
# (`20260907T051231Z_PORT-16.log:1882`; `20260907T110826Z_PORT-16.log:1948`
# reproduces P_src and P_sheet to every printed digit).
PORT16_STEP1_P1_10MHZ_W = {
    "p_src": 3.143759587e-03,
    "p_vol": 4.482780406e-04,
    "sheet_field_total": 2.695481546e-03,
}


def _frequency_key() -> str:
    raw = os.environ.get(FREQ_ENV)
    if raw is None or not raw.strip():
        raise RuntimeError(
            f"{FREQ_ENV} is unset and this module has no default: set it to "
            f"one of {sorted(FREQUENCIES_HZ)} (one frequency per window)"
        )
    key = raw.strip()
    if key not in FREQUENCIES_HZ:
        raise ValueError(f"{FREQ_ENV} must be one of {sorted(FREQUENCIES_HZ)}; got {raw!r}")
    return key


def _rss_per_rank_gib(comm) -> list[float]:
    """``ru_maxrss`` per rank (`OPS-43`), gathered on every rank."""
    local = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024.0 / 2**30
    return [float(x) for x in comm.allgather(local)]


def _reactive_source_power_w(sweep, driven_sheet, e_complex, omega) -> float:
    """``Im S_src = Re L(E)/(2ωμ₀)`` — the imaginary half of `PORT-16`'s P_src.

    Same builder, same form, same reduction as
    ``test_birdcage_power_identity._source_power_w``; the real part instead of
    the imaginary one (derivation in the module docstring).
    """
    form = lumped_port_linear_term(
        sweep["mesh"], sweep["facet_tags"], driven_sheet, e_complex, omega_rad_per_s=omega
    )
    return float(np.real(_reduce(sweep["mesh"].comm, form))) / (2.0 * omega * MU_0)


def _solve_and_read(sweep, degree: int) -> dict:
    comm = sweep["mesh"].comm
    problem = sweep["problem"]
    omega = 2.0 * np.pi * float(problem.frequency_hz)
    comm.Barrier()
    t0 = time.perf_counter()
    _result, fields = run_lumped_sheet_port_case(
        problem,
        sweep["port_defs"],
        sweep["specs"],
        facet_tags=sweep["facet_tags"],
        driven_port_id=DRIVEN,
        degree=degree,
        verbose=False,
        return_fields=True,
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    e = fields.e_complex
    space = e.function_space
    n_dofs = int(space.dofmap.index_map.size_global * space.dofmap.index_map_bs)
    solved = {"omega": omega, "fields": fields, "driven": DRIVEN}
    exact = _exact_shares(sweep, solved)
    driven_sheet = exact["sheets"][DRIVEN]
    q_src = _reactive_source_power_w(sweep, driven_sheet, e, omega)
    w_e = stored_electric_energy(fields, comm=comm)
    w_m = _stored_magnetic_energy(e, omega, comm)
    q_energy = 2.0 * omega * (w_m - w_e)
    a_resid = abs(exact["p_src"] - exact["p_vol"] - exact["sheet_field_total"]) / abs(
        exact["p_src"]
    )
    b_resid = abs(q_src - q_energy) / abs(q_src)
    return {
        "degree": degree,
        "n_dofs": n_dofs,
        "space_degree": int(space.ufl_element().embedded_superdegree),
        "t_solve": t_solve,
        "exact": exact,
        "q_src": q_src,
        "q_energy": q_energy,
        "w_e": w_e,
        "w_m": w_m,
        "a_resid": a_resid,
        "b_resid": b_resid,
        "rss_gib": _rss_per_rank_gib(comm),
    }


def _print_row(row, f_hz) -> None:
    ex = row["exact"]
    print(
        f"[TH-19 step3] f = {f_hz:.3e} Hz degree {row['degree']} "
        f"(space superdegree {row['space_degree']}): {row['n_dofs']} DOFs, "
        f"P1 solve {row['t_solve']:.1f} s",
        flush=True,
    )
    print(
        f"    (a) P_src,exact {ex['p_src']:.9e} W   P_vol {ex['p_vol']:.9e} W "
        f"(phantom {ex['phantom']:.9e}, conductor {ex['conductor']:.9e})   "
        f"P_sheet,exact {ex['sheet_field_total']:.9e} W   rel dev "
        f"{row['a_resid']:.3e} (band {DISCRETE_IDENTITY_RTOL:g})",
        flush=True,
    )
    print(
        f"    (b) Im S_src {row['q_src']:.9e} W   2w(W_m - W_e) "
        f"{row['q_energy']:.9e} W   rel dev {row['b_resid']:.3e} "
        f"(band {IDENTITY_TOLERANCE:g})",
        flush=True,
    )
    print(
        f"    W_e {row['w_e']:.6e} J   W_m {row['w_m']:.6e} J   W_e/W_m "
        f"{row['w_e'] / row['w_m']:.6e}",
        flush=True,
    )
    rss = row["rss_gib"]
    print(
        "    ru_maxrss per rank (GiB, process high-water mark): "
        + ", ".join(f"{x:.2f}" for x in rss)
        + f"   sum {sum(rss):.2f}   max {max(rss):.2f}",
        flush=True,
    )


@pytest.fixture(scope="module")
def degree_rows():
    key = _frequency_key()
    f_hz = FREQUENCIES_HZ[key]
    comm = MPI.COMM_WORLD
    t0 = time.perf_counter()
    sweep = build_four_port_sweep(frequency_hz=f_hz, build_only=True)
    t_build = time.perf_counter() - t0
    if comm.rank == 0:
        print(
            f"\n[TH-19 step3] {FREQ_ENV}={key}: {sweep['cells']} cells (record "
            f"{STEP2_CELL_COUNT}), build {t_build:.1f} s at -n {comm.size}; "
            f"driven {DRIVEN}; the sheet drive goes through "
            "run_lumped_sheet_port_case (project_source=False, untouched)",
            flush=True,
        )
    row1 = _solve_and_read(sweep, 1)
    if comm.rank == 0:
        _print_row(row1, f_hz)
    row2 = _solve_and_read(sweep, 2)
    if comm.rank == 0:
        _print_row(row2, f_hz)
        print(
            f"[TH-19 step3] W_e/W_m degree 1 {row1['w_e'] / row1['w_m']:.6e}   "
            f"degree 2 {row2['w_e'] / row2['w_m']:.6e}   W_e(2)/W_e(1) "
            f"{row2['w_e'] / row1['w_e']:.6e}   W_m(2)/W_m(1) "
            f"{row2['w_m'] / row1['w_m']:.6e}",
            flush=True,
        )
    return {"key": key, "f_hz": f_hz, "sweep": sweep, 1: row1, 2: row2}


@complex_only
def test_the_mesh_is_the_record_mesh_and_degree_reaches_the_space(degree_rows):
    """116 085 cells; the degree-2 solve really is second order (DOFs grow)."""
    assert int(degree_rows["sweep"]["cells"]) == STEP2_CELL_COUNT
    assert degree_rows[1]["space_degree"] == 1
    assert degree_rows[2]["space_degree"] == 2
    assert degree_rows[2]["n_dofs"] > degree_rows[1]["n_dofs"]


@complex_only
def test_degree1_control_reproduces_port16_step1(degree_rows):
    """Negative control (asserted, by record at 10 MHz; theorems at 128 MHz)."""
    row = degree_rows[1]
    assert row["a_resid"] <= DISCRETE_IDENTITY_RTOL, (
        f"degree 1: discrete power identity rel dev {row['a_resid']:.3e}"
    )
    if degree_rows["key"] == "10":
        for name, rec in PORT16_STEP1_P1_10MHZ_W.items():
            got = row["exact"][name]
            rel = abs(got - rec) / abs(rec)
            if MPI.COMM_WORLD.rank == 0:
                print(
                    f"\n    degree-1 {name} {got:.9e} W vs PORT-16 record "
                    f"{rec:.9e} W: rel {rel:.3e} (rtol {STEP2D_10MHZ_RTOL:g})",
                    flush=True,
                )
            assert rel <= STEP2D_10MHZ_RTOL, (
                f"degree-1 {name} {got:.9e} W misses the PORT-16 step-1 record "
                f"{rec:.9e} W by {rel:.3e}"
            )
    else:
        assert row["b_resid"] <= IDENTITY_TOLERANCE, (
            f"degree 1 at {degree_rows['f_hz']:.3e} Hz: reactive identity rel dev "
            f"{row['b_resid']:.3e}"
        )


@complex_only
def test_degree2_discrete_power_identity(degree_rows):
    """Anchor (a): ``P_src,exact = P_vol + P_sheet,exact`` at degree 2."""
    row = degree_rows[2]
    assert row["exact"]["p_src"] > 0.0
    assert row["a_resid"] <= DISCRETE_IDENTITY_RTOL, (
        f"degree 2 at {degree_rows['f_hz']:.3e} Hz: discrete power identity rel dev "
        f"{row['a_resid']:.6e} against {DISCRETE_IDENTITY_RTOL:g}"
    )


@complex_only
def test_degree2_reactive_identity(degree_rows):
    """Anchor (b): ``Im S_src = 2ω(W_m − W_e)`` at degree 2, `TH-12` band."""
    row = degree_rows[2]
    assert row["b_resid"] <= IDENTITY_TOLERANCE, (
        f"degree 2 at {degree_rows['f_hz']:.3e} Hz: reactive identity rel dev "
        f"{row['b_resid']:.6e} against {IDENTITY_TOLERANCE:g} — Im S_src "
        f"{row['q_src']:.9e} W vs 2w(W_m - W_e) {row['q_energy']:.9e} W "
        f"(W_e {row['w_e']:.6e} J, W_m {row['w_m']:.6e} J)"
    )
