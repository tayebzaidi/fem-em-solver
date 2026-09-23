"""`PORT-23` step 1 — the circuit layer through `scikit-rf`, gated against (C2).

``ports/circuit_skrf.py`` builds an `skrf.Network` from a stored 4×4 and
terminates ports through an `skrf.Circuit` netlist (series impedance to ground
per terminated port, `Circuit.Port` per kept port).  The raw (C2) reduction
``ports.circuit.reduce_terminated_ports`` is the control.  Pure numpy + stored
records; no field solve.  Every record, fixture and band except the new
machine-precision identity band is imported from the `PORT-14` / `PORT-15`
modules, never restated.

(a) *asserted*: ``terminate`` vs ``reduce_terminated_ports`` on the stored 64 MHz
    4×4 (``S_64MHZ_EPS0_RECORD``) at ``C_tuned`` (`PORT-15` step 3's own
    ``tuning_sweep`` / ``select_c_tuned``, recomputed in-run), 1×1 kept
    (P2..P4 in ``C_tuned``) and 2×2 kept (P3, P4 in ``C_tuned``):
    ``max|Δ| ≤ IDENTITY_BAND`` = 1e-12.
(b) *asserted*: the same on the stored 10 MHz 4×4 with `PORT-15` step 2's
    terminations (``TERMINATIONS`` on ``TERMINATED_PORT_INDEX``), 3×3 kept.
(c) *asserted*: sweeping ``C`` through ``terminate`` with `PORT-15` step 3's
    root rule finds a zero of ``Im Z_in`` with ``|Im Z|/|Z| ≤ TUNING_IM_Z_RTOL``
    at a ``C`` equal to ``C_tuned`` to ``TUNING_IM_Z_RTOL`` (relative); the
    `skrf` tuned ``S₁₁`` there reproduces `PORT-15`'s in-model tuned ``S₁₁``
    record at the imported ``REDUCTION_BAND``.
(d) *asserted* (convention control): renormalising the Network to 75 Ω and back
    returns the input to 1e-12; ``s_def='power'`` and ``'traveling'`` give the
    same 75 Ω matrix to 1e-12; and that matrix equals the raw layer's
    ``z_to_s(s_to_z(S, 50), 75)`` to 1e-12 — the ``a = (V + z₀I)/(2√z₀)``
    convention ``ports/superposition.py`` documents.

Negative control (*asserted*, the row's floor): on the **2×2-kept** case
(P1, P2 kept; P3, P4 in ``C_tuned``) the netlist's port map with P2 ↔ P3
swapped misses the (C2) control by ``≥ NEGATIVE_CONTROL_FLOOR`` = 1e-3.  On the
1×1-kept case with equal terminations the swap is invisible by symmetry (review
2026-09-23), so the control is not run there.  The adjacent-vs-opposite class
gap ``|S₁₂ − S₁₃|`` of the imported 4×4 is printed beside the miss; if that gap
is itself < ``CLASS_GAP_STOP`` = 1e-2 the test stops before asserting the floor
(§9 item 34, rule (e)).

Printed, never gated: kept-port ``Z_in`` from both engines, ``skrf.__version__``.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from mpi4py import MPI

skrf = pytest.importorskip("skrf")

from fem_em_solver.ports.circuit import reduce_terminated_ports, s_to_z, z_to_s  # noqa: E402
from fem_em_solver.ports.circuit_skrf import (  # noqa: E402
    input_impedance,
    network_from_records,
    terminate,
)
from fem_em_solver.ports.lumped import series_rlc_impedance  # noqa: E402

from tests.validation.test_port_circuit_layer_field import (  # noqa: E402
    S_10MHZ_EPS0_RECORD,
    S_64MHZ_EPS0_RECORD,
    TUNING_2X2_TERMINATED_INDICES,
    TUNING_C_GRID_F,
    TUNING_IM_Z_RTOL,
    TUNING_TERMINATED_INDICES,
    _capacitor_impedance,
    _residual,
    select_c_tuned,
    tuning_sweep,
)
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ  # noqa: E402
from tests.validation.test_port_lumped_rlc_termination import (  # noqa: E402
    REDUCTION_BAND,
    STEP3_REGISTERED_FREQUENCY_HZ,
    TERMINATED_PORT_INDEX,
    TERMINATIONS,
)
from tests.validation.test_port_package_sparameters import REFERENCE_IMPEDANCE_OHM  # noqa: E402

# New bands (this module).  IDENTITY_BAND is not a tolerance: (C2) and the
# skrf netlist are the same algebra, so any residual above round-off is a
# convention finding (§9 item 34 "negative result"), never a band to widen.
IDENTITY_BAND = 1.0e-12
NEGATIVE_CONTROL_FLOOR = 1.0e-3  # the §7 row's asserted floor
CLASS_GAP_STOP = 1.0e-2  # §9 item 34: stop and report below this, before asserting
RENORM_Z0_OHM = 75.0
SWAPPED_PORT_MAP = (0, 2, 1, 3)  # logical P2 -> network P3 and vice versa

# `PORT-15` step 3's in-model tuned S11 at C_tuned (P2..P4 capacitor sheets,
# P1 driven, 116 085-cell gate mesh, -n 2) — printed there to 13 significant
# digits, never stored as a module constant: `20260914T020419Z_PORT-15.log:3732`
# ("in-model -7.614132983688e-01+6.285992898694e-05j").  A record, not a band.
PORT15_IN_MODEL_TUNED_S11_RECORD = complex(-7.614132983688e-01, 6.285992898694e-05)

Z0 = float(REFERENCE_IMPEDANCE_OHM)
F64 = float(STEP3_REGISTERED_FREQUENCY_HZ)
F10 = float(FREQUENCY_HZ)


def _root():
    return MPI.COMM_WORLD.rank == 0


def _say(text):
    if _root():
        print(text, flush=True)


def _maxabs(a, b):
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b))))


@pytest.fixture(scope="module")
def c_tuned():
    _, _, roots = tuning_sweep(S_64MHZ_EPS0_RECORD, F64)
    tuned = select_c_tuned(roots)
    assert tuned is not None, "PORT-15 step 3's sweep found no C_tuned on the stored record"
    return float(tuned["c_f"])


@pytest.fixture(scope="module")
def net64():
    return network_from_records(S_64MHZ_EPS0_RECORD, Z0, F64)


@pytest.fixture(scope="module")
def net10():
    return network_from_records(S_10MHZ_EPS0_RECORD, Z0, F10)


def test_skrf_version_is_printed():
    _say(f"\n[PORT-23] skrf.__version__ = {skrf.__version__} (PRINTED); "
         f"-n {MPI.COMM_WORLD.size}, every rank computes the same serial circuit")


def test_a_terminate_matches_c2_at_c_tuned_64mhz(net64, c_tuned):
    """(a) 1×1 and 2×2 kept at C_tuned, max|Δ| ≤ 1e-12."""
    z_c = _capacitor_impedance(F64, c_tuned)
    rows = []
    for label, indices in (("1x1 (P2..P4 in C)", TUNING_TERMINATED_INDICES),
                           ("2x2 (P3, P4 in C)", TUNING_2X2_TERMINATED_INDICES)):
        terms = {k: z_c for k in indices}
        raw = reduce_terminated_ports(S_64MHZ_EPS0_RECORD, Z0, terms)
        lib = terminate(net64, terms)[0]
        assert lib.shape == raw.shape, (label, lib.shape, raw.shape)
        rows.append((label, _maxabs(lib, raw), raw, lib))
    _say(f"\n[PORT-23] (a) 64 MHz, C_tuned = {c_tuned:.15e} F (Z_C = {z_c:.9e} Ohm), "
         f"skrf Circuit vs (C2) (ASSERTED max|d| <= {IDENTITY_BAND:.0e}):")
    for label, d, raw, lib in rows:
        _say(f"    {label:<18s} max|d| = {d:.3e}")
        _say(f"      S11 (C2) {complex(raw[0, 0]):.15e}  skrf {complex(lib[0, 0]):.15e}")
        _say(f"      Z_in (C2) {input_impedance(raw[0, 0], Z0):.12e} Ohm  skrf "
             f"{input_impedance(lib[0, 0], Z0):.12e} Ohm (PRINTED, drive port with the others "
             f"as in the kept network)")
    for label, d, _, _ in rows:
        assert d <= IDENTITY_BAND, f"(a) {label}: max|d| {d:.3e} > {IDENTITY_BAND:.0e} — convention finding"


def test_b_terminate_matches_c2_at_10mhz_step2_terminations(net10):
    """(b) 10 MHz, the step 2 C / L / R on P1, 3×3 kept, max|Δ| ≤ 1e-12."""
    rows = []
    for label, element in TERMINATIONS:
        z = series_rlc_impedance(F10, **element)
        terms = {TERMINATED_PORT_INDEX: z}
        raw = reduce_terminated_ports(S_10MHZ_EPS0_RECORD, Z0, terms)
        lib = terminate(net10, terms)[0]
        assert lib.shape == raw.shape
        rows.append((label, z, _maxabs(lib, raw)))
    _say(f"\n[PORT-23] (b) 10 MHz, P{TERMINATED_PORT_INDEX + 1} terminated, 3x3 kept "
         f"(ASSERTED max|d| <= {IDENTITY_BAND:.0e}):")
    for label, z, d in rows:
        _say(f"    {label:<12s} Z = {z:.9e} Ohm  max|d| = {d:.3e}")
    for label, _, d in rows:
        assert d <= IDENTITY_BAND, f"(b) {label}: max|d| {d:.3e} > {IDENTITY_BAND:.0e} — convention finding"


def _skrf_tuned(net, c_f):
    z_c = _capacitor_impedance(F64, c_f)
    s = terminate(net, {k: z_c for k in TUNING_TERMINATED_INDICES})[0]
    s11 = complex(s[0, 0])
    return input_impedance(s11, Z0), s11


def _skrf_tuning_sweep(net, grid=TUNING_C_GRID_F, max_iter=200):
    """`PORT-15` step 3's root rule, verbatim, with ``Im Z_in`` from `skrf`."""
    values = np.array([_skrf_tuned(net, c)[0].imag for c in grid])
    roots = []
    for i in range(len(grid) - 1):
        if not (np.isfinite(values[i]) and np.isfinite(values[i + 1])):
            continue
        if np.sign(values[i]) == np.sign(values[i + 1]):
            continue
        lo, hi, f_lo = np.log(grid[i]), np.log(grid[i + 1]), values[i]
        for _ in range(max_iter):
            mid = 0.5 * (lo + hi)
            f_mid = _skrf_tuned(net, np.exp(mid))[0].imag
            if f_mid == 0.0:
                lo = hi = mid
                break
            if np.sign(f_mid) == np.sign(f_lo):
                lo, f_lo = mid, f_mid
            else:
                hi = mid
            if hi - lo <= 1.0e-15:
                break
        c = float(np.exp(0.5 * (lo + hi)))
        z, s11 = _skrf_tuned(net, c)
        rel = abs(z.imag) / abs(z) if np.isfinite(abs(z)) else np.inf
        roots.append({"c_f": c, "z": z, "s11": s11, "im_rel": float(rel),
                      "zero": bool(rel <= TUNING_IM_Z_RTOL)})
    return roots


def test_c_tuning_zero_through_skrf_reproduces_c_tuned(net64, c_tuned):
    """(c) C_tuned to TUNING_IM_Z_RTOL; tuned S11 vs in-model record ≤ REDUCTION_BAND."""
    t0 = time.perf_counter()
    roots = _skrf_tuning_sweep(net64)
    elapsed = time.perf_counter() - t0
    tuned = select_c_tuned(roots)
    _say(f"\n[PORT-23] (c) Im Z_in(C) swept through skrf on {TUNING_C_GRID_F.size} grid points "
         f"({elapsed:.1f} s): {len(roots)} sign change(s)")
    for r in roots:
        _say(f"    C = {r['c_f']:.15e} F  Z_in = {r['z']:.9e} Ohm  |S11| = {abs(r['s11']):.9f}  "
             f"|Im Z|/|Z| = {r['im_rel']:.3e}  {'ZERO' if r['zero'] else 'pole (rejected)'}")
    assert tuned is not None, "(c) no zero of Im Z_in through skrf — report, never widen the grid"
    c_rel = abs(tuned["c_f"] / c_tuned - 1.0)
    s11 = tuned["s11"]
    r_in_model = _residual(np.array([PORT15_IN_MODEL_TUNED_S11_RECORD]), np.array([s11]))
    z_raw = input_impedance(
        reduce_terminated_ports(S_64MHZ_EPS0_RECORD, Z0,
                                {k: _capacitor_impedance(F64, c_tuned) for k in TUNING_TERMINATED_INDICES}
                                )[0, 0], Z0)
    _say(f"    skrf C = {tuned['c_f']:.15e} F vs PORT-15 C_tuned {c_tuned:.15e} F: "
         f"|ratio - 1| = {c_rel:.3e} (ASSERTED <= {TUNING_IM_Z_RTOL:.0e}); |Im Z|/|Z| = "
         f"{tuned['im_rel']:.3e} (ASSERTED <= {TUNING_IM_Z_RTOL:.0e})")
    _say(f"    Z_in at C_tuned (PRINTED): skrf {tuned['z']:.12e} Ohm, (C2) {z_raw:.12e} Ohm")
    _say(f"    tuned S11 skrf {s11:.12e} vs PORT-15 in-model record "
         f"{PORT15_IN_MODEL_TUNED_S11_RECORD:.12e}: residual {r_in_model:.6e} "
         f"(ASSERTED <= REDUCTION_BAND {REDUCTION_BAND:.0e})")
    assert tuned["im_rel"] <= TUNING_IM_Z_RTOL
    assert c_rel <= TUNING_IM_Z_RTOL, f"(c) C through skrf off C_tuned by {c_rel:.3e}"
    assert r_in_model <= REDUCTION_BAND, f"(c) tuned S11 residual {r_in_model:.6e} > {REDUCTION_BAND:.0e}"


def test_d_wave_convention_control(net64):
    """(d) 75 Ω round trip; power vs traveling; vs the raw layer's S↔Z, all ≤ 1e-12."""
    s50 = net64.s[0].copy()
    rt = net64.copy()
    rt.renormalize(RENORM_Z0_OHM, s_def="power")
    rt.renormalize(Z0, s_def="power")
    d_rt = _maxabs(rt.s[0], s50)
    by_def = {}
    for s_def in ("power", "traveling", "pseudo"):
        n = net64.copy()
        n.renormalize(RENORM_Z0_OHM, s_def=s_def)
        by_def[s_def] = n.s[0].copy()
    d_pt = _maxabs(by_def["power"], by_def["traveling"])
    d_pp = _maxabs(by_def["power"], by_def["pseudo"])
    raw75 = z_to_s(s_to_z(S_64MHZ_EPS0_RECORD, Z0), RENORM_Z0_OHM)
    d_raw = _maxabs(by_def["power"], raw75)
    d_moved = _maxabs(by_def["power"], s50)
    _say(f"\n[PORT-23] (d) convention control on the 64 MHz 4x4 (ASSERTED <= {IDENTITY_BAND:.0e}):")
    _say(f"    50 -> {RENORM_Z0_OHM:g} -> 50 Ohm round trip  max|d| = {d_rt:.3e}")
    _say(f"    75 Ohm: power vs traveling       max|d| = {d_pt:.3e}")
    _say(f"    75 Ohm: power vs raw z_to_s(s_to_z) max|d| = {d_raw:.3e}")
    _say(f"    75 Ohm: power vs pseudo (PRINTED) max|d| = {d_pp:.3e}; the 75 Ohm matrix moved "
         f"{d_moved:.3e} from the 50 Ohm one (PRINTED: the renormalisation is not a no-op)")
    assert d_rt <= IDENTITY_BAND
    assert d_pt <= IDENTITY_BAND
    assert d_raw <= IDENTITY_BAND


def test_negative_control_swapped_ports_2x2_breaks_gate_a(net64, c_tuned):
    """Negative control (ASSERTED): P2 ↔ P3 swapped in the netlist, 2×2 kept, miss ≥ 1e-3."""
    z_c = _capacitor_impedance(F64, c_tuned)
    terms = {k: z_c for k in TUNING_2X2_TERMINATED_INDICES}
    raw = reduce_terminated_ports(S_64MHZ_EPS0_RECORD, Z0, terms)
    swapped = terminate(net64, terms, port_map=SWAPPED_PORT_MAP)[0]
    miss = _maxabs(swapped, raw)
    s = S_64MHZ_EPS0_RECORD
    gap = abs(complex(s[0, 1]) - complex(s[0, 2]))
    _say(f"\n[PORT-23] negative control (ASSERTED >= {NEGATIVE_CONTROL_FLOOR:.0e}): 2x2 kept "
         f"(P1, P2), P3/P4 in C_tuned, netlist port map {SWAPPED_PORT_MAP} (P2 <-> P3)")
    _say(f"    class gap |S12 - S13| of the imported 4x4 = {gap:.6e} (stop below {CLASS_GAP_STOP:.0e})")
    _say(f"    miss vs (C2) max|d| = {miss:.6e} = {miss / NEGATIVE_CONTROL_FLOOR:.1f}x the floor; "
         f"miss / gap = {miss / gap:.4f}")
    if gap < CLASS_GAP_STOP:
        pytest.fail(f"class gap {gap:.3e} < {CLASS_GAP_STOP:.0e}: stop and report before asserting "
                    "the negative-control floor (§9 item 34)")
    assert miss >= NEGATIVE_CONTROL_FLOOR, (
        f"swapped port map missed (C2) by only {miss:.3e} — the gate does not see port order"
    )
