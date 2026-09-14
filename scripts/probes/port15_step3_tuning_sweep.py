"""`PORT-15` step 3 sweep printer — ``Z_in(64 MHz; C)`` on the stored record.

Pure numpy on ``S_64MHZ_EPS0_RECORD`` (no solve): P1 driven at 50 Ω, P2..P4
terminated in one capacitor each.  Prints a decimated table of ``C``, ``Z_in``
and ``|S11|`` across the test module's grid, then every bisected sign change of
``Im Z_in`` (zero or pole) and the selected ``C_tuned``.  Asserts nothing; the
gate is ``tests/validation/test_port_circuit_layer_field.py::test_step3_*``.

Run::

    scripts/testing/run_and_log.sh PORT-15 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
      PYTHONPATH=/workspace/src:/workspace timeout -k 30 60 \\
      python3 scripts/probes/port15_step3_tuning_sweep.py'"
"""

from __future__ import annotations

import numpy as np

from tests.validation.test_port_circuit_layer_field import (
    S_64MHZ_EPS0_RECORD,
    STEP3_REGISTERED_FREQUENCY_HZ,
    TUNING_C_GRID_F,
    select_c_tuned,
    tuned_input,
    tuning_sweep,
)


def main():
    f = STEP3_REGISTERED_FREQUENCY_HZ
    print(f"[PORT-15 step3 probe] f = {f:.6e} Hz, P1 driven at 50 Ohm, P2..P4 in C")
    print(f"{'C (F)':>14s} {'Re Z_in':>16s} {'Im Z_in':>16s} {'|S11|':>12s}")
    for c in TUNING_C_GRID_F[::50]:
        z, s = tuned_input(S_64MHZ_EPS0_RECORD, f, c)
        print(f"{c:14.6e} {z.real:+16.6e} {z.imag:+16.6e} {abs(s[0, 0]):12.9f}")
    _, _, roots = tuning_sweep(S_64MHZ_EPS0_RECORD, f)
    print(f"[PORT-15 step3 probe] {len(roots)} sign change(s) of Im Z_in:")
    for r in roots:
        print(f"    C = {r['c_f']:.15e} F  Z_in = {r['z']:.9e}  |S11| = {abs(r['s11']):.9f}  "
              f"|Im Z|/|Z| = {r['im_rel']:.3e}  {'ZERO' if r['zero'] else 'pole'}")
    tuned = select_c_tuned(roots)
    if tuned is None:
        print("[PORT-15 step3 probe] no zero on the grid")
        return
    print(f"[PORT-15 step3 probe] C_tuned = {tuned['c_f']:.15e} F, |S11| = {abs(tuned['s11']):.9f}")
    for factor in (0.5, 2.0):
        _, s = tuned_input(S_64MHZ_EPS0_RECORD, f, factor * tuned["c_f"])
        print(f"    {factor:g} x C_tuned: |S11| = {abs(s[0, 0]):.9f}")


if __name__ == "__main__":
    main()
