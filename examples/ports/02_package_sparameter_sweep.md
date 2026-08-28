# EX-20 — package S-parameter sweep on a solved field

The first example that drives `run_n_port_sparameter_sweep()` — the package
entry point, rather than assembling `Z` by hand.

## 1. What this demonstrates

`EX-18` builds the impedance matrix itself and calls
`sparameters_from_impedance()` on it. This example hands the package a mesh, two
`PortDefinition`s and two `GapVoltagePortSpec`s and lets one call do the rest:

1. the same **gapped two-torus fixture** — two partial tori (cell tags 1/2),
   each bridged by a rectangular dielectric gap box (101/102), fragmented
   conformally into one air box (3) inside a PEC truncation box at padding 0.08,
   σ = 800 S/m, f = 10 MHz;
2. `run_n_port_sparameter_sweep(problem, ports, gap_voltage_ports=specs)` runs
   **one impressed-gap solve per port**, reads `V` and `I` off each solved
   field, assembles `Z` column by column and converts it to `S` at Z₀ = 50 Ω;
3. the two named systematics applied to the resulting `Im Z₁₂` through
   `mutual_systematics_ladder()`, printed rung by rung;
4. the **negative control in the same run**: the same call *without*
   `gap_voltage_ports=` is the retiring `PORT-0` proximity heuristic
   (known-issues 3) — its `DeprecationWarning` is printed and its S-matrix is
   asserted to differ from the solved-field one.

This is the capability `PORT-1` step 4 gated on 2026-08-13, from the entry-point
angle `EX-18` does not cover.

## 2. How to run it

```bash
./run_examples.sh -e ports:2 -n 2 -t 540
```

It needs the complex DolfinX build; the `ports:` runner group sources
`/usr/local/bin/dolfinx-complex-mode` automatically. Measured cost at `-n 2`:
**178.2 s** — mesh 36.9 s (178 055 cells), package sweep 47.9 s, heuristic
control 45.7 s, export solve 23.0 s
(`docs/testing/logs/20260816T050310Z_EX-20-example-n2.log`, exit 0).

## 3. How to analyze it, step by step — what one call produced

`Z` (Ω), read off two solved fields:

```
[[3.81895312+7.43491837j  0.00860323+1.11015591j]
 [0.00862493+1.11080327j  3.82003593+7.18544613j]]
```

The systematics ladder on `Im Z₁₂ = 1.110803269 Ω` against
`ωM₁₂ = 1.241755 Ω`:

| rung | ratio to `ωM₁₂` | deviation |
|---|---|---|
| raw | 0.894543 | **−10.55% — a miss** |
| + PEC box (`D∞ = +0.0169`, `p = 1.657`) | 0.911443 | −8.86% |
| + gap physics (`÷(1 − 0.030224)`) | 0.939849 | −6.02% |

The raw rung is printed **first and labelled a miss**, and the example asserts
it *fails* the 10% band: an example that showed the corrected number alone
would be advertising a gate that does not exist.

Network identities on the same matrices:

* `|Z₁₂ − Z₂₁|/|Z₂₁|` = 5.8309e-04 — two solves, two integrands, one operator,
  so this is a *measured* reciprocity, not an algebraic one;
* `‖S − Sᵀ‖/‖S‖` = 4.7586e-05, `‖S‖₂` = 0.864809 ≤ 1 (passive).

The negative control, same mesh and same ports:

```
S_heuristic = [[-0.99998596-9.3e-11j  0+0j]
               [ 0+0j                -0.99998589-9.4e-11j]]
max|S_heuristic − S_field| = 3.078260e-01
```

Its off-diagonal is *identically zero* — the heuristic has no coupling to
report at this port separation — while the field route's is
`0.0103 + 0.0362j`. That is the whole point of `PORT-1` step 4.

## Gates

All asserted values are allreduced. The two mutual-ratio bands cite
`docs/testing/logs/20260813T183606Z_PORT-1-step4-packagegate.log`; the two
S-matrix records are the `PORT-9` leg (d3) power-wave digits carried by the
gate module `tests/validation/test_port_package_sparameters.py`. All four
bands are deliberately **looser** than the digits they cite.

* four reproductions inside a pre-stated **1% relative** band — raw 0.894543,
  corrected 0.939849, `‖S − Sᵀ‖/‖S‖` 4.7586e-05, `‖S‖₂` 0.864809457; measured
  misses **2.98e-05 / 2.92e-05 / 3.13e-06 / 1.32e-10**
  (`20260826T123904Z_EX-30-ports-run-2to3.log`), i.e. at least two orders of
  magnitude inside the band.

  **Re-recorded 2026-08-26** (`EX-30` leg (ports), in-class (1\*) licence):
  the two S-matrix digits read 2.5494e-05 / 0.861449 until this date, from
  the v0.7.2 terminated-Z conversion. Leg (d3) changed the sweep to assemble
  `S` from power waves, so both moved; the symmetry record was the one that
  went red here (measured miss 8.67e-01 against the 1% band,
  `20260826T123139Z_EX-30-ports-run-1to2.log`) and it is what found the
  drift. No band moved and no physics gate was touched;
* the **raw** mutual asserted *outside* the unmoved `MUTUAL_TOLERANCE = 10%`
  and the corrected one *inside* it — the systematics have to be doing work;
* `‖S‖₂ ≤ 1` as an inequality (passivity), not a reproduction;
* `is_placeholder` False on the solved-field result, True on the heuristic;
* **negative control, executed in-run**: `max|S_heuristic − S_field| >
  2.0e-3` (measured 3.078e-01, two orders of headroom) and at least one
  `DeprecationWarning` raised by the heuristic route.

## What this is not

* **Not an `S₁₁` claim.** `PORT-1` step 2b localised an electric-energy excess
  on this fixture's diagonal, so no `Z_in` and no `S₁₁` may be read off it. The
  gated quantity is the mutual; `S₁₁`/`S₂₂` are printed because a 2×2 S-matrix
  has them.
* **Not a birdcage port, not B1+, not Touchstone.** Two-torus fixture only. No
  coil in this repository has ports at all (PROJECT_PLAN §2).
* **Not portable corrections.** Both systematics were measured on *this*
  geometry at *this* padding and must be re-measured anywhere else.

## A named limitation of the entry point

`run_n_port_sparameter_sweep()` returns port quantities, not fields:
`SParameterSweepResult` carries `s_matrix` / `z_matrix` and per-port responses,
and the solver's `TimeHarmonicFields` are discarded inside it. The ParaView
export below therefore costs **one extra solve** (23.0 s of the 178.2 s) of
port 1's drive, run directly through `TimeHarmonicSolver` exactly as the sweep
runs it. Surfacing the fields from the sweep would remove that cost; it is not
scoped here.

## ParaView

Writes `examples/ports/paraview_output/ports_02_package_sparameter_sweep_combined.xdmf`
(+ `.h5`): mesh, `CellTags`, and the port-1 drive's `E_real` / `E_imag` /
`E_magnitude` as CG1 Lagrange interpolants (XDMF cannot carry N1curl — the
`EX-14`/`EX-17` lesson). Threshold on `CellTags` to isolate the gap boxes
(101/102) and the conductors (1/2).
