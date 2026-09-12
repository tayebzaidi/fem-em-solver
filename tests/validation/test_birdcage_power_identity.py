"""`PORT-16` step 1 — the **exact** discrete power identity on the 4-leg fixture.

`POST-6` step 1b left a finding: every single drive on the loaded F-small
birdcage reads a real-power accounting gap

    gap = ½Re(V_src Ī_driven) − Σ_i ½|I_i|²Re Z_p − ½∫σ|E|² dV  ≈ 6.7e-05 W,

the same absolute figure on all four ports (0.23% scatter) and 0.98% of the
supplied power — i.e. sitting at 0.98× the imported 1% ``POWER_BALANCE_BAND``.
Both the ``supplied`` and the ``sheets`` legs of that sum are built from the
sheets' **terminal currents** (``test_birdcage_b1_plus_map.py::_power_shares``),
while the volume loss is an exact integral.  This module measures where the
gap sits by writing down the accounting the *discrete Galerkin solution itself*
satisfies, and differencing the two.

**The exact identity.**  The assembled problem is ``a(E, v) = L(v)`` for every
``v`` in the (homogeneous-PEC) test space, with

    a(E, v)   = ∫ μᵣ⁻¹(∇×E)·conj(∇×v) − k₀²ε_c E·conj(v) dV
                + Σ_sheets jωμ₀ Y_s ∫_S (n̂×E)·conj(n̂×v) dS       (Jin (1.63), L1)
    L(v)      = −jωμ₀ ∫_S K_imp·conj(v) dS                        (L3)

with ``ε_c = εᵣ − jσ/(ωε₀)`` and ``Y_s = 1/R`` the sheet admittance per square.
The Dirichlet data is zero, so ``E`` is itself an admissible test function and
``a(E, E) = L(E)`` **exactly**, up to the LU residual.  Taking the imaginary
part and dividing by ``ωμ₀`` (``μᵣ`` real, ``k₀² σ/(ωε₀) = ωμ₀σ``) gives

    P_src,exact = P_vol + P_sheet,exact                                    (i)

    P_vol       = ½∫σ|E|² dV                       (the whole domain)
    P_sheet,exact = Σ_sheets ½ Re(Y_s) ∫_S |n̂×E|² dS   = Im a_sheet(E,E)/(2ωμ₀)
    P_src,exact = −½ Re ∫_S K_imp·conj(E) dS       = +Im L(E)/(2ωμ₀)

(the ``+`` because ``L = −jωμ₀∫K·conj(E)`` already carries the load
convention's own minus — the first `PORT-16` window
`20260907T050816Z_PORT-16.log:1882` caught this file's transcription of that
sign as a ``rel dev`` of *exactly* 2.000e+00 on all four drives and on the
control, which is the signature of ``P_src = −(P_vol + P_sheet)``).

Nothing in (i) is a discretisation statement: it is the real part of the weak
form tested with its own solution, so 1e-6 leaves ~10⁴ of slack over the
1e-10-class solver residual.  The sheet and source terms are assembled here
through the package's **own** form builders
(:func:`~fem_em_solver.ports.lumped.lumped_port_bilinear_term` /
:func:`~fem_em_solver.ports.lumped.lumped_port_linear_term`, called with the
solved phasor in both argument slots), so a transcription error is impossible
and a miss is a statement about the assembly, not about this file.

**The Cauchy–Schwarz leg, corrected in derivation before measurement.**  The
sheet's constitutive law is ``K_s = Y_s(E_t + E_src ĥ)`` and its terminal
current is ``I = (Y_s/h)∫_S (E·ĥ + E_src) dA`` — the package's
:func:`~fem_em_solver.ports.lumped.sheet_terminal_current`.  With ``f = E·ĥ +
E_src``, ``Z_p = R h/w`` and ``A = h·w``,

    ½|I|² Re Z_p = ½|∫f dA|² /(R A) ≤ ½ (1/R) ∫|f|² dA
                 ≤ ½ Re(Y_s) ∫ |E_t + E_src ĥ|² dA                       (ii)

by Cauchy–Schwarz plus ``|f| = |(E + E_src ĥ)·ĥ| ≤ |E_t + E_src ĥ|`` (``ĥ``
lies in the sheet plane).  Equality only for a uniform total tangential field.
On the three **undriven** sheets of a drive ``E_src = 0`` and (ii) is exactly
the §9 item's pre-registered form ``½|I|²Re Z_p ≤ P_sheet,exact,i``.  On the
**driven** sheet the two differ, and the item's field-only form is *not* a
theorem: ``I`` there is driven by ``E_t + E_src ĥ`` while ``P_sheet,exact``
carries ``E_t`` alone (the ``E_src`` half of the sheet current was moved to the
right-hand side as ``K_imp``).  That is a derivation error in the
pre-registration, found on paper before this module was run; it is repaired by
**asserting the theorem** (ii) on all sixteen sheet readings and additionally
asserting the item's literal field-only form on the twelve undriven ones, with
the driven sheet's field-only ratio *printed* so the review can see how far the
item's form is from a bound there.  No band was widened: (ii) is new here, and
the version asserted is strictly the provable one.

**What this measures.**  Given (i), the accounting gap splits algebraically,

    gap = (P_sheet,exact − sheets_terminal) + (supplied_terminal − P_src,exact) (iii)

which is what the item pre-registered at ≤10% of the gap.  (iii) is therefore
*arithmetic*, and the finding is the **split**: the size of each of the two
terms relative to the gap they sum to.  Both are printed as multiples of the
gap; a split in which each term is O(gap) attributes it, and a split in which
they are orders larger and cancel says the 1% is in neither terminal form.
The first `PORT-16` window measured the latter — −54.28× and +55.28× the gap
(`20260907T050816Z_PORT-16.log:1912`, read with this file's sign bug removed
by hand) — so (iii) attributes nothing on its own.

**(iv) — the attribution that does close, registered on that same window.**
The Cauchy–Schwarz ceiling of (ii), summed over the four sheets, is what the
terminal form is *missing*: window 1 read ``ceiling/terminal = 1.010593`` on
**every one of the sixteen** sheet readings, and

    C − sheets_terminal = 6.7168e-05 W  vs  gap = 6.716202e-05 W,
    C ≡ Σ_sheets ½Re(Y_s)∫|E_t + E_src ĥ|² dA = 6.407962373e-03 W,
    supplied_terminal = 6.856240413e-03 W = P_vol + C to the printed digit

(`…:1884`, `…:1895–1898`, `…:1912`).  So the ~1%-of-supplied gap **is** the
Cauchy–Schwarz deficit of the terminal-current sheet form — the sheets'
tangential field is not uniform across the sheet, and ``½|I|²Re Z_p`` is the
uniform-field lower bound on the dissipation the field actually deposits.
That is `PORT-16`'s candidate (a), and it is asserted here at the row's own
done-when bar (≤10% of the gap).  It is **not** in the §9 item's
pre-registration: it was found by measurement in window 1 and is asserted in
window 2, which is why both windows' logs are committed.

**Negative control** (rule (e) — sign asserted, size predicted): the P1 drive
re-solved with every sheet's ``Z_p`` **doubled**.  *Asserted*: (i) still closes
at 1e-6 (an identity that is a theorem does not depend on ``Z_p``), and the
sheet term moves (the knob is wired).  *Predicted, printed beside the measured
value and never asserted*: ``P_sheet,exact`` moves by a factor in ``[0.5, 2]``,
ceiling the whole of ``P_src,exact`` (asserted, since ``P_vol > 0`` makes
``P_sheet ≤ P_src`` an exact consequence of (i)).  The volume term's
phantom/conductor ratio is printed for both.  Window 1 measured the factor at
**0.484102** (`20260907T050816Z_PORT-16.log:1918`) — just *below* the predicted
window, which is what a nearly-``1/R`` sheet term does when the field it
carries also responds to the doubled resistivity; recorded here because the
prediction is printed and never asserted, so nothing about it is a failure.

**Scope.**  A measurement of where the 1% sits.  No band moves:
``POWER_BALANCE_BAND`` is imported nowhere here, the deliberate red in
``test_port_drive_superposition.py`` is untouched, and no ``src/`` file
changed.  10 MHz, F-small, degree 1, four single drives plus one control solve
on the same 116 085-cell mesh.  Whether ``POWER_BALANCE_BAND`` is a band or a
record, and whether the ``h`` rungs (step 2) are needed, is the review's call
with this split in hand.

**`PORT-14` step 2d — the same accounting at 64 MHz** (§9 2026-09-12 03:00,
ruling (3)).  ``FEM_EM_PORT16_64MHZ`` (unset/``0`` = off, the default path
bit-identical) builds the sweep at 64 MHz; ω everywhere comes from
``sweep["problem"]``.  (i)–(iii) and the ×2 control stay asserted — theorems
and arithmetic, frequency-independent.  (iv) was registered on a 10 MHz window,
so under the flag it prints its residual and skips (rule (e)).
``test_step2d_c_over_terminal_is_printed`` prints ``C/terminal − 1`` per drive
and per sheet beside `PORT-14` step 2b's κ(64 MHz) — the question is whether κ
*is* this deficit — and asserts, flag off, the 10 MHz readings of
`20260907T051231Z_PORT-16.log:1917–1920` to rtol 1e-5 and, flag on, that S₁₁
moved off the 10 MHz record (the flag reached the builder).

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-16 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 300 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_birdcage_power_identity.py -v -s'"
"""

from __future__ import annotations

import os
from dataclasses import replace

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.ports.lumped import (
    _sheet_measure,
    lumped_port_bilinear_term,
    lumped_port_linear_term,
)
from fem_em_solver.utils.constants import MU_0

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.validation.test_birdcage_b1_plus_map import (
    _power_shares,
    _solve_driven,
)
from tests.validation.test_port_birdcage_four_port import (
    TERMINATED_PORT_IMPEDANCE_OHM,
    build_four_port_sweep,
)
from tests.validation.test_port_drive_superposition import _loss_power_w
from tests.validation.test_port_lumped_rlc_termination import STEP1E_S11_S21_10MHZ

PORT_IDS = ("P1", "P2", "P3", "P4")

# --- `PORT-14` step 2d: the terminal-form deficit at 64 MHz, measured ---------
STEP2D_ENV = "FEM_EM_PORT16_64MHZ"
STEP2D_FREQUENCY_HZ = 64.0e6

# κ(64 MHz), `PORT-14` step 2b's proportional-law coefficient ΔZ = κ(Z_p − z0):
# pooled and per element (`20260912T020824Z_PORT-14-step2b-w2.log:1947–1951`).
# **Printed beside C/terminal − 1, never asserted** — rule (e), no prior 64 MHz
# reading of this module exists.
STEP2B_KAPPA_64MHZ_POOLED = 1.064081e-02
STEP2B_KAPPA_64MHZ = {"C": 1.057617e-02, "L": 1.064945e-02, "R": 1.058671e-02}
# *Predicted, printed only*: C/terminal − 1 at 64 MHz within this of κ(64).
STEP2D_PREDICTED_KAPPA_RTOL = 0.05

# The 10 MHz readings this module logged (`20260907T051231Z_PORT-16.log:1917–1920`):
# per drive (C, gap) in W, gap = C − sheets_terminal to 3e-13, so
# C/terminal − 1 = gap/(C − gap).  **Asserted** flag-off at STEP2D_10MHZ_RTOL.
PORT16_10MHZ_C_AND_GAP_W = {
    "P1": (6.407962372e-03, 6.716202469e-05),
    "P2": (6.407717078e-03, 6.716397529e-05),
    "P3": (6.405693150e-03, 6.714497009e-05),
    "P4": (6.407255616e-03, 6.715513633e-05),
}
STEP2D_10MHZ_RTOL = 1.0e-5

# Negative control (asserted, flag on): S11 at 64 MHz differs from the 10 MHz
# record by more than 100x its 1e-9 print precision (`PORT-14` step 2 measured
# a wholly different S at 64 MHz, `20260911T183201Z_PORT-14-step2.log:1859, :1880`).
STEP2D_S11_MIN_MOVE = 100.0 * 1.0e-9


def _step2d_enabled():
    return os.environ.get(STEP2D_ENV, "") not in ("", "0")


def _c_over_terminal_minus_one(exact, terminal):
    """Pooled ``C/sheets_terminal − 1`` and the per-sheet ratios, for one drive."""
    pooled = exact["sheet_ceiling_total"] / terminal["sheet_total"] - 1.0
    per_sheet = {
        pid: exact["sheet_ceiling"][pid] / terminal["sheets"][pid] - 1.0
        for pid in PORT_IDS
    }
    return pooled, per_sheet

# **Anchor (i)**, pre-registered by the 2026-09-06 18:00 review (§9 item 4).
# ``a(E,E) = L(E)`` is exact for the discrete solution, so this is a statement
# about the assembly and the LU residual (1e-10-class), not a discretisation
# tolerance.  A miss is the finding that the assembled forms leak power.
DISCRETE_IDENTITY_RTOL = 1.0e-6

# **Anchor (iii)**, same pre-registration.  Given (i) the split is algebraic, so
# this bound is only violated if (i) is; it is asserted anyway because the item
# asks for it and because it pins the arithmetic that produces the printed
# shares.
ATTRIBUTION_RTOL = 1.0e-1

# `POST-6` step 1b's record for the P1 drive, restated here (it is not a
# constant in that module): supplied 6.856240413e-03 W, sheets 6.340800348e-03 W,
# P_vol 4.482780406e-04 W (`20260905T110305Z_POST-6.log:1924-1926`), whose
# difference is 6.7162e-05 W.  **Printed, never asserted** — it is a
# mesh/image-dependent reading, and this module recomputes it in-run.
POST6_STEP1B_P1_GAP_W = 6.7162e-05

# Negative control.  *Asserted*: the sheet term is not inert under the knob.
CONTROL_SHEET_MIN_REL_MOVE = 1.0e-3
# *Predicted, printed only* (rule (e)): the window the §9 item pre-stated.
CONTROL_PREDICTED_FACTOR_WINDOW = (0.5, 2.0)


def _reduce(comm, form) -> complex:
    """``assemble_scalar`` is rank-local — never read one without this."""
    return complex(comm.allreduce(fem.assemble_scalar(fem.form(form)), op=MPI.SUM))


def _sheet_field_dissipation_w(sweep, sheet, e_complex, omega) -> float:
    """``½ Re(Y_s)∫|n̂×E|² dA`` = ``Im a_sheet(E,E)/(2ωμ₀)``.

    Assembled through the package's **own** bilinear-term builder with the
    solved phasor in both argument slots, so this is literally the term the
    matrix carried.  ``ufl.inner`` conjugates its second argument, which is what
    turns ``a_sheet(E,E)`` into ``jωμ₀Y_s∫|n̂×E|²``.
    """
    form = lumped_port_bilinear_term(
        sweep["mesh"],
        sweep["facet_tags"],
        sheet,
        e_complex,
        e_complex,
        omega_rad_per_s=omega,
    )
    return float(np.imag(_reduce(sweep["mesh"].comm, form))) / (2.0 * omega * MU_0)


def _sheet_total_field_dissipation_w(sweep, sheet, e_complex) -> float:
    """``½ Re(Y_s)∫|E_t + E_src ĥ|² dA`` — the Cauchy–Schwarz ceiling of (ii).

    ``E_t = E − (E·n̂)n̂`` with ``n̂`` from the restricted ('+') side; ``ufl.dot``
    rather than ``ufl.inner`` because the normal is real and ``inner`` would
    conjugate it, which is a silent sign trap on the ``e^{+jωt}`` convention.
    Equal to :func:`_sheet_field_dissipation_w` on an undriven sheet
    (``E_src = 0``), which is why the item's literal form is asserted there.
    """
    mesh = sweep["mesh"]
    ds_sheet = _sheet_measure(mesh, sweep["facet_tags"], sheet)
    n = ufl.FacetNormal(mesh)("+")
    e_r = e_complex("+")
    e_t = e_r - ufl.dot(e_r, n) * n
    e_src = complex(sheet.source_voltage_v) / float(sheet.gap_height_m)
    src_vec = ufl.as_vector(
        [default_scalar_type(e_src * c) for c in sheet.unit_drive()]
    )
    total = e_t + src_vec
    integral = _reduce(mesh.comm, ufl.inner(total, total) * ds_sheet)
    y_s = 1.0 / sheet.sheet_resistivity
    return 0.5 * float(np.real(y_s)) * float(np.real(integral))


def _source_power_w(sweep, driven_sheet, e_complex, omega) -> float:
    """``−½ Re ∫ K_imp·conj(E) dA`` = ``−Im L(E)/(2ωμ₀)``.

    Through the package's own load-term builder with the solved phasor in the
    test slot: the right-hand side the solve actually assembled, evaluated at
    its own solution.
    """
    form = lumped_port_linear_term(
        sweep["mesh"],
        sweep["facet_tags"],
        driven_sheet,
        e_complex,
        omega_rad_per_s=omega,
    )
    return float(np.imag(_reduce(sweep["mesh"].comm, form))) / (2.0 * omega * MU_0)


def _exact_shares(sweep, solved):
    """The exact (form-level) accounting of one drive, all MPI-reduced."""
    omega = float(solved["omega"])
    e = solved["fields"].e_complex
    specs = sweep["specs"]
    sheets = {
        spec.port_id: spec.sheet(driven=(spec.port_id == solved["driven"]))
        for spec in specs
    }
    field_diss = {
        pid: _sheet_field_dissipation_w(sweep, sheet, e, omega)
        for pid, sheet in sheets.items()
    }
    ceilings = {
        pid: _sheet_total_field_dissipation_w(sweep, sheet, e)
        for pid, sheet in sheets.items()
    }
    phantom, conductor = _loss_power_w(sweep, e, solved["fields"].sigma_field)
    return {
        "sheets": sheets,
        "sheet_field": field_diss,
        "sheet_ceiling": ceilings,
        "sheet_field_total": float(sum(field_diss.values())),
        "phantom": phantom,
        "conductor": conductor,
        "p_vol": float(phantom + conductor),
        "p_src": _source_power_w(sweep, sheets[solved["driven"]], e, omega),
        "sheet_ceiling_total": float(sum(ceilings.values())),
    }


def _terminal_sheet_powers(solved, port_impedance_ohm):
    """``½|I_i|² Re Z_p`` per sheet — the terminal form, for an arbitrary Z_p."""
    re_z = float(np.real(port_impedance_ohm))
    return {
        pid: 0.5 * abs(complex(i)) ** 2 * re_z
        for pid, i in solved["currents"].items()
    }


@pytest.fixture(scope="module")
def power_identity_case():
    """One mesh, four single drives, one ×2-resistivity control drive.

    ``build_four_port_sweep`` is imported, never rebuilt (the `EX-33` reading of
    `ANS-1`); ``_solve_driven`` and ``_power_shares`` come from `WF-6` step 1's
    module so the terminal side of every comparison below is literally the
    fixture's own.
    """
    if _step2d_enabled():
        sweep = build_four_port_sweep(frequency_hz=STEP2D_FREQUENCY_HZ)
    else:
        sweep = build_four_port_sweep()
    comm = sweep["mesh"].comm

    solves = {pid: _solve_driven(sweep, pid) for pid in PORT_IDS}
    terminal = {pid: _power_shares(sweep, solves[pid]) for pid in PORT_IDS}
    exact = {pid: _exact_shares(sweep, solves[pid]) for pid in PORT_IDS}

    # The control: every sheet's terminal impedance doubled, so R = Z_p·w/h
    # doubles in both (L1) and K_imp.  Same mesh, same facet tags, same drive.
    specs_x2 = [
        replace(spec, port_impedance_ohm=2.0 * complex(spec.port_impedance_ohm))
        for spec in sweep["specs"]
    ]
    sweep_x2 = dict(sweep)
    sweep_x2["specs"] = specs_x2
    control = _solve_driven(sweep_x2, "P1")
    exact_x2 = _exact_shares(sweep_x2, control)
    terminal_x2 = _terminal_sheet_powers(
        control, 2.0 * complex(TERMINATED_PORT_IMPEDANCE_OHM)
    )

    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }

    if comm.rank == 0:
        print(
            "\n[PORT-16 step1] the exact discrete power identity on the 4-leg "
            f"fixture at f = {float(sweep['problem'].frequency_hz):.3e} Hz, "
            f"Z_p = {TERMINATED_PORT_IMPEDANCE_OHM:.6e} Ohm, "
            f"sheet azimuths {[f'{azimuths[p]:.1f}' for p in PORT_IDS]}",
            flush=True,
        )
        print(
            "    (i) P_src,exact = P_vol + P_sheet,exact   "
            f"(ASSERTED rel <= {DISCRETE_IDENTITY_RTOL:g})",
            flush=True,
        )
        for pid in PORT_IDS:
            ex, tm = exact[pid], terminal[pid]
            resid = abs(ex["p_src"] - ex["p_vol"] - ex["sheet_field_total"]) / abs(
                ex["p_src"]
            )
            print(
                f"        {pid}  P_src,exact {ex['p_src']:.9e} W   "
                f"P_vol {ex['p_vol']:.9e} W   "
                f"P_sheet,exact {ex['sheet_field_total']:.9e} W   "
                f"rel dev {resid:.3e}",
                flush=True,
            )
            print(
                f"            volume split: phantom {ex['phantom']:.9e} W, "
                f"conductor {ex['conductor']:.9e} W, "
                f"phantom/conductor {ex['phantom'] / ex['conductor']:.6e}",
                flush=True,
            )
            print(
                f"            terminal side: supplied {tm['supplied']:.9e} W, "
                f"sheets {tm['sheet_total']:.9e} W",
                flush=True,
            )
        print(
            "    (ii) Cauchy-Schwarz: 1/2|I|^2 Re Z_p <= 1/2 Re(Y_s) int "
            "|E_t + E_src h|^2 dA on every sheet (ASSERTED); the item's "
            "field-only form is that same statement on the undriven sheets "
            "(ASSERTED) and is not a theorem on the driven one (PRINTED)",
            flush=True,
        )
        for pid in PORT_IDS:
            ex = exact[pid]
            sheets_terminal = _terminal_sheet_powers(
                solves[pid], TERMINATED_PORT_IMPEDANCE_OHM
            )
            for other in PORT_IDS:
                tag = "driven" if other == pid else "undriven"
                print(
                    f"        drive {pid} sheet {other} ({tag}): "
                    f"terminal {sheets_terminal[other]:.9e} W   "
                    f"ceiling {ex['sheet_ceiling'][other]:.9e} W   "
                    f"ratio ceiling/terminal "
                    f"{ex['sheet_ceiling'][other] / sheets_terminal[other]:.6f}   "
                    f"field-only {ex['sheet_field'][other]:.9e} W   "
                    f"ratio field-only/terminal "
                    f"{ex['sheet_field'][other] / sheets_terminal[other]:.6f}",
                    flush=True,
                )
        print(
            "    (iii) the attribution of the accounting gap "
            f"(ASSERTED rel <= {ATTRIBUTION_RTOL:g}); "
            f"`POST-6` step 1b's P1 record {POST6_STEP1B_P1_GAP_W:.6e} W "
            "(PRINTED, not asserted)",
            flush=True,
        )
        for pid in PORT_IDS:
            ex, tm = exact[pid], terminal[pid]
            gap = tm["supplied"] - tm["sheet_total"] - ex["p_vol"]
            d_sheet = ex["sheet_field_total"] - tm["sheet_total"]
            d_src = tm["supplied"] - ex["p_src"]
            print(
                f"        {pid}  gap {gap:.9e} W   "
                f"(sheets_exact - sheets_terminal) {d_sheet:.9e} W "
                f"[{d_sheet / gap:.4f} x gap]   "
                f"(supplied_terminal - P_src,exact) {d_src:.9e} W "
                f"[{d_src / gap:.4f} x gap]   "
                f"sum {d_sheet + d_src:.9e} W   "
                f"rel dev {abs(d_sheet + d_src - gap) / abs(gap):.3e}",
                flush=True,
            )
        print(
            "    (iv) the Cauchy-Schwarz deficit of the terminal sheet form "
            f"reproduces the gap (ASSERTED rel <= {ATTRIBUTION_RTOL:g})",
            flush=True,
        )
        for pid in PORT_IDS:
            ex, tm = exact[pid], terminal[pid]
            gap = tm["supplied"] - tm["sheet_total"] - ex["p_vol"]
            deficit = ex["sheet_ceiling_total"] - tm["sheet_total"]
            print(
                f"        {pid}  gap {gap:.9e} W   "
                f"C = sum_sheets 1/2 Re(Y_s) int |E_t + E_src h|^2 dA "
                f"{ex['sheet_ceiling_total']:.9e} W   "
                f"C - sheets_terminal {deficit:.9e} W   "
                f"C/sheets_terminal {ex['sheet_ceiling_total'] / tm['sheet_total']:.6f}   "
                f"rel dev {abs(deficit - gap) / abs(gap):.3e}   "
                f"[P_vol + C {ex['p_vol'] + ex['sheet_ceiling_total']:.9e} W vs "
                f"supplied_terminal {tm['supplied']:.9e} W]",
                flush=True,
            )
        base, ctl = exact["P1"], exact_x2
        factor = ctl["sheet_field_total"] / base["sheet_field_total"]
        resid = abs(ctl["p_src"] - ctl["p_vol"] - ctl["sheet_field_total"]) / abs(
            ctl["p_src"]
        )
        print(
            "    negative control: P1 with every sheet's Z_p doubled "
            f"({2.0 * float(np.real(TERMINATED_PORT_IMPEDANCE_OHM)):.6e} Ohm)",
            flush=True,
        )
        print(
            f"        (i) rel dev {resid:.3e} (ASSERTED <= "
            f"{DISCRETE_IDENTITY_RTOL:g})   P_src,exact {ctl['p_src']:.9e} W   "
            f"P_vol {ctl['p_vol']:.9e} W   "
            f"P_sheet,exact {ctl['sheet_field_total']:.9e} W",
            flush=True,
        )
        print(
            f"        P_sheet,exact factor vs the unmodified P1 drive {factor:.6f} "
            f"(PREDICTED window "
            f"[{CONTROL_PREDICTED_FACTOR_WINDOW[0]}, "
            f"{CONTROL_PREDICTED_FACTOR_WINDOW[1]}], printed not asserted; "
            f"ASSERTED: it moved by >= {CONTROL_SHEET_MIN_REL_MOVE:g} relative, "
            "and P_sheet,exact <= P_src,exact)",
            flush=True,
        )
        print(
            f"        volume phantom/conductor: control "
            f"{ctl['phantom'] / ctl['conductor']:.6e}   "
            f"unmodified P1 {base['phantom'] / base['conductor']:.6e}   "
            f"terminal sheets (x2) "
            f"{float(sum(terminal_x2.values())):.9e} W",
            flush=True,
        )

    return {
        "sweep": sweep,
        "solves": solves,
        "terminal": terminal,
        "exact": exact,
        "control": control,
        "exact_x2": exact_x2,
        "terminal_x2": terminal_x2,
    }


@complex_only
def test_the_discrete_power_identity_closes_on_every_drive(power_identity_case):
    """(i) ``P_src,exact = P_vol + P_sheet,exact`` at 1e-6 on all four drives.

    The real part of ``a(E,E) = L(E)``.  A miss here is not a discretisation
    reading — it says the assembled forms do not conserve power against their
    own solution.
    """
    exact = power_identity_case["exact"]
    for pid in PORT_IDS:
        ex = exact[pid]
        assert ex["p_src"] > 0.0, f"{pid}: P_src,exact must be positive, got {ex['p_src']:.6e}"
        residual = abs(ex["p_src"] - ex["p_vol"] - ex["sheet_field_total"]) / abs(
            ex["p_src"]
        )
        assert residual <= DISCRETE_IDENTITY_RTOL, (
            f"{pid}: the discrete power identity misses by {residual:.6e} against "
            f"{DISCRETE_IDENTITY_RTOL:g} — P_src,exact {ex['p_src']:.9e} W, "
            f"P_vol {ex['p_vol']:.9e} W, P_sheet,exact "
            f"{ex['sheet_field_total']:.9e} W"
        )


@complex_only
def test_the_terminal_sheet_power_is_a_lower_bound_on_every_sheet(power_identity_case):
    """(ii) Cauchy–Schwarz, on all sixteen sheet readings.

    The theorem is against the **total** tangential field ``E_t + E_src ĥ`` (see
    the module docstring); on the twelve undriven sheets that is identically the
    §9 item's field-only form, which is asserted separately there.
    """
    exact = power_identity_case["exact"]
    solves = power_identity_case["solves"]
    for pid in PORT_IDS:
        terminal = _terminal_sheet_powers(solves[pid], TERMINATED_PORT_IMPEDANCE_OHM)
        for other in PORT_IDS:
            assert terminal[other] <= exact[pid]["sheet_ceiling"][other], (
                f"drive {pid} sheet {other}: the terminal form "
                f"{terminal[other]:.9e} W exceeds its Cauchy-Schwarz ceiling "
                f"{exact[pid]['sheet_ceiling'][other]:.9e} W"
            )
            if other != pid:
                assert terminal[other] <= exact[pid]["sheet_field"][other], (
                    f"drive {pid} undriven sheet {other}: the terminal form "
                    f"{terminal[other]:.9e} W exceeds the exact field-only "
                    f"dissipation {exact[pid]['sheet_field'][other]:.9e} W"
                )


@complex_only
def test_the_terminal_minus_exact_split_reproduces_the_accounting_gap(
    power_identity_case,
):
    """(iii) the two terminal-vs-exact differences sum to the gap, ≤10% of it.

    Algebraic given (i); asserted because the item pre-registered it and because
    it pins the arithmetic behind the printed shares.  The *finding* is the
    split, in the log's ``x gap`` columns.
    """
    exact = power_identity_case["exact"]
    terminal = power_identity_case["terminal"]
    for pid in PORT_IDS:
        ex, tm = exact[pid], terminal[pid]
        gap = tm["supplied"] - tm["sheet_total"] - ex["p_vol"]
        assert gap != 0.0, f"{pid}: the accounting gap is exactly zero — nothing to attribute"
        attributed = (ex["sheet_field_total"] - tm["sheet_total"]) + (
            tm["supplied"] - ex["p_src"]
        )
        residual = abs(attributed - gap) / abs(gap)
        assert residual <= ATTRIBUTION_RTOL, (
            f"{pid}: the split misses the gap by {residual:.6e} against "
            f"{ATTRIBUTION_RTOL:g} — gap {gap:.9e} W, attributed "
            f"{attributed:.9e} W"
        )


@complex_only
def test_the_cauchy_schwarz_deficit_of_the_terminal_form_reproduces_the_gap(
    power_identity_case,
):
    """(iv) `PORT-16`'s candidate (a): the gap *is* the sheets' C–S deficit.

    Registered on window 1's measurement (see the module docstring), asserted at
    the §7 row's own done-when bar — "one candidate reproduces the gap on the
    record mesh to ≤10% of itself".  Unlike (iii) this is not arithmetic: the
    left-hand side is a facet integral of the solved field and the right-hand
    side is a difference of terminal readings.
    """
    exact = power_identity_case["exact"]
    terminal = power_identity_case["terminal"]
    if _step2d_enabled():
        # Rule (e): registered on a 10 MHz window; at 64 MHz printed, not asserted.
        # The skip is decided from the environment, identical on every rank.
        if MPI.COMM_WORLD.rank == 0:
            for pid in PORT_IDS:
                ex, tm = exact[pid], terminal[pid]
                gap = tm["supplied"] - tm["sheet_total"] - ex["p_vol"]
                deficit = ex["sheet_ceiling_total"] - tm["sheet_total"]
                print(
                    f"[PORT-14 step2d] (iv) at {STEP2D_FREQUENCY_HZ:.3e} Hz {pid}: "
                    f"gap {gap:.9e} W   C - sheets_terminal {deficit:.9e} W   "
                    f"rel dev {abs(deficit - gap) / abs(gap):.3e} "
                    f"(PRINTED; band {ATTRIBUTION_RTOL:g} registered at 10 MHz)",
                    flush=True,
                )
        pytest.skip(
            f"{STEP2D_ENV} on: (iv) was registered on a 10 MHz measurement; its "
            "64 MHz residual is printed, not asserted (rule (e))"
        )
    for pid in PORT_IDS:
        ex, tm = exact[pid], terminal[pid]
        gap = tm["supplied"] - tm["sheet_total"] - ex["p_vol"]
        deficit = ex["sheet_ceiling_total"] - tm["sheet_total"]
        assert deficit > 0.0, (
            f"{pid}: the Cauchy-Schwarz deficit must be positive, got "
            f"{deficit:.9e} W"
        )
        residual = abs(deficit - gap) / abs(gap)
        assert residual <= ATTRIBUTION_RTOL, (
            f"{pid}: the Cauchy-Schwarz deficit {deficit:.9e} W misses the "
            f"accounting gap {gap:.9e} W by {residual:.6e} against "
            f"{ATTRIBUTION_RTOL:g}"
        )


@complex_only
def test_doubling_the_sheet_resistivity_keeps_the_identity_and_moves_the_sheet_term(
    power_identity_case,
):
    """Negative control: sign asserted, size predicted and printed (rule (e)).

    Asserted — (i) still closes at 1e-6 (a theorem does not depend on ``Z_p``),
    the sheet term is not inert under the knob, and ``P_sheet,exact ≤
    P_src,exact`` (the ceiling, exact from (i) with ``P_vol > 0``).
    Predicted — the ×0.5–2 factor window, printed beside the measurement in the
    fixture's block and asserted nowhere.
    """
    base = power_identity_case["exact"]["P1"]
    ctl = power_identity_case["exact_x2"]

    residual = abs(ctl["p_src"] - ctl["p_vol"] - ctl["sheet_field_total"]) / abs(
        ctl["p_src"]
    )
    assert residual <= DISCRETE_IDENTITY_RTOL, (
        f"control (Z_p x2): the discrete power identity misses by "
        f"{residual:.6e} against {DISCRETE_IDENTITY_RTOL:g} — an identity that "
        "is a theorem must not depend on Z_p"
    )

    move = abs(ctl["sheet_field_total"] - base["sheet_field_total"]) / base[
        "sheet_field_total"
    ]
    assert move >= CONTROL_SHEET_MIN_REL_MOVE, (
        f"control (Z_p x2): P_sheet,exact moved only {move:.6e} relative "
        f"(< {CONTROL_SHEET_MIN_REL_MOVE:g}) — the resistivity knob is not "
        "reaching the sheet term"
    )
    assert ctl["sheet_field_total"] <= ctl["p_src"], (
        f"control (Z_p x2): P_sheet,exact {ctl['sheet_field_total']:.9e} W "
        f"exceeds its ceiling P_src,exact {ctl['p_src']:.9e} W"
    )
    assert ctl["p_vol"] > 0.0, "control (Z_p x2): the volume loss must be positive"


@complex_only
def test_step2d_c_over_terminal_is_printed(power_identity_case):
    """`PORT-14` step 2d: is κ the terminal form's Cauchy–Schwarz deficit?

    Runs at both frequencies.  Prints, per drive, ``C/terminal − 1`` pooled and
    per sheet beside κ(64 MHz) — the comparison is *predicted* and never
    asserted.  Asserted: flag off, the 10 MHz readings reproduce to
    STEP2D_10MHZ_RTOL; flag on, S₁₁ moved off the 10 MHz record (the builder
    was reached).
    """
    sweep = power_identity_case["sweep"]
    exact = power_identity_case["exact"]
    terminal = power_identity_case["terminal"]
    on = _step2d_enabled()
    freq = float(sweep["problem"].frequency_hz)
    s11 = complex(np.asarray(sweep["s"], dtype=np.complex128)[0, 0])
    s11_10 = complex(STEP1E_S11_S21_10MHZ[0])
    s11_move = abs(s11 - s11_10)

    readings = {
        pid: _c_over_terminal_minus_one(exact[pid], terminal[pid]) for pid in PORT_IDS
    }
    refs = {
        pid: gap / (c - gap) for pid, (c, gap) in PORT16_10MHZ_C_AND_GAP_W.items()
    }

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-14 step2d] {STEP2D_ENV} {'on' if on else 'off'}: "
            f"f = {freq:.3e} Hz; S11 = {s11.real:+.9e}{s11.imag:+.9e}j   "
            f"10 MHz record = {s11_10.real:+.9e}{s11_10.imag:+.9e}j   "
            f"|diff| = {s11_move:.6e}"
            + (f" (ASSERTED > {STEP2D_S11_MIN_MOVE:.1e})" if on else " (PRINTED)"),
            flush=True,
        )
        kappa_line = "   ".join(f"{k} {v:.6e}" for k, v in STEP2B_KAPPA_64MHZ.items())
        print(
            f"[PORT-14 step2d] kappa(64 MHz) pooled {STEP2B_KAPPA_64MHZ_POOLED:.6e}   "
            f"per element {kappa_line}   (step 2b; PREDICTED: C/terminal - 1 "
            f"within {STEP2D_PREDICTED_KAPPA_RTOL:.0%} of pooled kappa at 64 MHz, "
            "printed not asserted)",
            flush=True,
        )
        for pid in PORT_IDS:
            pooled, per_sheet = readings[pid]
            sheets_line = "   ".join(
                f"{other} {per_sheet[other]:.6e}" for other in PORT_IDS
            )
            print(
                f"[PORT-14 step2d] drive {pid}: C/terminal - 1 = {pooled:.9e}   "
                f"/kappa_pooled {pooled / STEP2B_KAPPA_64MHZ_POOLED:.6f}   "
                f"(rel {pooled / STEP2B_KAPPA_64MHZ_POOLED - 1.0:+.4e})   "
                f"10 MHz reference {refs[pid]:.9e}   "
                f"shift vs 10 MHz {pooled / refs[pid] - 1.0:+.4e}"
                + ("" if on else f" (ASSERTED rtol {STEP2D_10MHZ_RTOL:g})"),
                flush=True,
            )
            print(f"                 per sheet: {sheets_line}", flush=True)

    if on:
        assert freq == STEP2D_FREQUENCY_HZ, (
            f"{STEP2D_ENV} on but the sweep ran at {freq:.6e} Hz"
        )
        assert s11_move > STEP2D_S11_MIN_MOVE, (
            f"{STEP2D_ENV} on but S11 {s11:.9e} sits {s11_move:.3e} from the "
            f"10 MHz record — the frequency did not reach the builder"
        )
        return
    for pid in PORT_IDS:
        pooled, _ = readings[pid]
        rel = abs(pooled - refs[pid]) / refs[pid]
        assert rel <= STEP2D_10MHZ_RTOL, (
            f"{pid}: C/terminal - 1 = {pooled:.9e} misses the 10 MHz reading "
            f"{refs[pid]:.9e} by {rel:.3e} against {STEP2D_10MHZ_RTOL:g}"
        )
