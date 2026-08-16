# EX-18 — gap-voltage port pair → Z → S on the two-torus fixture

The first example in this repository that produces **port** quantities from a
solved field.

## 1. What this demonstrates

Exactly the capability `PORT-1` steps 3b-xvii/3b-xviii gated on 2026-08-13, and
nothing beyond it:

1. the **gapped two-torus fixture** — two partial tori (cell tags 1/2), each
   bridged by a rectangular dielectric gap box (101/102), all fragmented
   conformally into one air box (3) inside a PEC truncation box at padding 0.08;
2. one solve per port, driven by an impressed `+ŷ` current density across that
   port's gap box, conductors at σ = 800 S/m, f = 10 MHz;
3. `I_k` from the meshed conduction current, `V_i` from the
   **terminal-to-terminal** tangential path integral `−∫E·t̂ dl` along the
   centreline arc, and `Z_ik = V_i / I_k`;
4. the two named systematics through
   `fem_em_solver.ports.systematics.mutual_systematics_ladder()`;
5. `S = (Z − Z₀I)(Z + Z₀I)⁻¹` through
   `fem_em_solver.ports.sparameters.sparameters_from_impedance()` at Z₀ = 50 Ω.

## 2. How to run it

```bash
./run_examples.sh -e ports:1 -n 2 -t 540
```

It needs the complex DolfinX build; the `ports:` runner group sources
`/usr/local/bin/dolfinx-complex-mode` automatically. Measured cost at `-n 2`:
**134 s** — mesh 36.1 s (178 055 cells), two solves 22.0 s + 22.5 s
(`docs/testing/logs/20260813T110940Z_EX-18-example-n2-v3.log`, exit 0).

## 3. How to analyze it, step by step — the numbers it prints, and the one it prints first

| rung | ratio to `ωM₁₂` | deviation |
|---|---|---|
| raw | 0.894543 | **−10.55% — a miss** |
| + PEC box (`D∞ = +0.0169`, `p = 1.657`) | 0.911443 | −8.86% |
| + gap physics (`÷(1 − 0.030224)`) | 0.939849 | −6.02% |

The raw number is printed **first and labelled a miss**: the unmoved 10% band
would not accept it. Only after both measured systematics does the mutual land
inside. An example that showed the corrected number alone would be advertising
a gate that does not exist.

Network identities on the same Z:

* `|Z₁₂ − Z₂₁|/|Z₁₂|` = 5.8343e-04 (printed — two solves, two integrands, one
  operator, so this is a *measured* reciprocity, not an algebraic one);
* `‖S − Sᵀ‖/‖S‖` = 2.5494e-05, `‖S‖₂` = 0.861449 ≤ 1 (passive).

## Gates

All asserted values are allreduced. The bands cite
`docs/testing/logs/20260813T020352Z_PORT-1-step3bxviii-pairgate-n2.log` and are
deliberately **looser** than the digits they cite — a reproduction band, never
to be tightened onto the measurement, and never to be widened to make a run
pass.

* pre-solve geometry: terminal angles from facet tags 201/202 equal
  `arcsin(half_y/a) = 0.175335123` rad to 1e-6 — the integration limits against
  the meshed geometry, checked *before* two solves are bought;
* quadrature precondition: the **undriven** port's path integral agrees between
  Gauss orders 2049 and 4097 to < 1e-3 (measured 3.9111e-04 / 1.4044e-04). The
  driven diagonal is printed and not gated — step 3b-x's standing disposition:
  its path runs through the impressed source's own terminals and does not
  converge in the quadrature (2.3e-2 / 3.5e-2), which is a property of `Z₁₁`,
  which nothing here reads;
* raw and corrected mutual reproduce the record to 2e-3;
* corrected mutual inside the unmoved `MUTUAL_TOLERANCE = 10%`;
* **negative control**, cited not recomputed: step 1's *unfragmented* ancestor
  of this fixture returned `Im Z₁₂` identically zero
  (`20260731T213222Z_PORT-1-step1-costprobe.log`). The same ladder on that
  number reads **−98.26%**, and the example asserts it *fails* the band — a
  band that accepted the blind fixture would be gating nothing;
* `‖S − Sᵀ‖/‖S‖ < 1e-3` and `‖S‖₂ ≤ 1`.

## What this is not

* **Not an `S₁₁` claim.** `PORT-1` step 2b localised an electric-energy excess
  on this fixture's diagonal (`W_e/W_m = 6.524`), so no `Z_in` and no `S₁₁` may
  be read off it. The gated quantity is the mutual. `S₁₁`/`S₂₂` are printed
  because a 2×2 S-matrix has them, not because they mean anything here.
* **Not a birdcage port**, and not a general port capability: `PORT-1` stays 🟡
  and the package's *other* S-parameter path (`ports/excitation.py`) is still
  the ⚠️ heuristic of known-issues 3.
* **Not portable corrections.** Both systematics were measured on *this*
  geometry at *this* padding and must be re-measured anywhere else. The PEC-box
  term is an effective-range extrapolation and is never to be quoted without
  its exponent `p = 1.657` (pinning the dipolar `p = 3` moves it to −1.43 pp).

## ParaView

Writes `examples/ports/paraview_output/two_torus_port_pair_combined.xdmf`
(+ `.h5`): mesh, `CellTags`, and the port-1 drive's `E_real` / `E_imag` /
`E_magnitude` as CG1 Lagrange interpolants (XDMF cannot carry N1curl; the
writers take Lagrange only — the `EX-14`/`EX-17` lesson). Threshold on
`CellTags` to isolate the gap boxes (101/102) and the conductors (1/2).
