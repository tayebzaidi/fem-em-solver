# ANS-3 — two coaxial gapped loops at 10 MHz (2-port Z and S)

Guide page for `03_two_torus_gap_ports_10MHz.py`, the **runnable half** of the
second commissioned Ansys Electronics Desktop benchmark (PROJECT_PLAN §5.4,
chunk `ANS-3`). `SPEC.md` beside this file is the authority for the problem the
human operator replicates in AED; this page explains what our half produces and
how to read it.

## 1. What this demonstrates

Two coaxial copper-like loops, 40 mm centreline radius, 5 mm wire radius, 40 mm
apart on the z axis, each cut by a small gap box that carries a lumped port.
The script drives each port in turn, assembles the 2×2 impedance matrix column
by column, and converts it to an S-matrix at Z₀ = 50 Ω — all through the single
package entry point
`fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep`.

Three things are on show, in this order:

1. **A negative control, printed first.** The *raw* mutual ratio
   |Im Z₂₁|/ωM₁₂ = 0.894516 is **−10.55%** against the filamentary closed form
   and the script asserts that it **fails** the unmoved 10% mutual band. This is
   an inverted assertion on purpose: the case exists to expose two systematic
   corrections (PEC-box truncation and the gap-generator feed model), and if the
   uncorrected number ever landed inside the band on its own, those corrections
   would be decorating a result nobody needed. The run would then fail loudly
   rather than quietly report a "corrected" number.
2. **The corrected number and the identities.** After the two named systematics
   the ratio is 0.939822 (−6.02%, inside the band); reciprocity
   ‖S − Sᵀ‖/‖S‖ = 4.7586e-05 against the 1e-3 gate, and passivity
   ‖S‖₂ = 0.864809 ≤ 1. (Those two read 2.5494e-05 / 0.861449 until
   2026-08-26 — the `PORT-9` leg (d3) power-wave assembly moved both; this
   case *imports* all four records from `ports:2`, so they re-recorded here
   with no edit to this case's script. `EX-30` leg (ports).)
3. **That it is the gated path, not a lookalike.** Every one of those four
   numbers is asserted to reproduce `EX-20`'s **0.11-image** record within a
   pre-stated **1e-6 relative** band (**1e-6 absolute** on the symmetry
   residual). Those four records were the v0.7.2 image's until `OPS-33`
   (2026-09-03) re-based them under the in-class (1\*) example-record licence;
   before that the misses were record-vs-image gaps of ≤ 2.98e-05
   (`20260902T183603Z_OPS-32.log`) rather than run-to-run scatter, which is why
   the band could not be tightened. The superseded v0.7.2 digits are kept and
   **asserted to fail** the new band, so the band is shown to bite. The band
   itself is `EX-37`'s measured ≤ 5e-8 run-to-run Z/S scatter with ≥ 20×
   headroom, and it holds because the geometry, drive, quadrature and
   correction constants are *imported* from `examples/ports/02_package_sparameter_sweep.py`
   (`EX-20`) rather than restated here. If the gated path moves, this benchmark
   moves with it and the reproduction assertions fire.

**What it is not.** Two-torus fixture only: no birdcage, no coil, no B1+, no
SAR, no frequency sweep. Our `Z₁₁`/`Z₂₂` carry the unprojected electric-energy
caveat (`PORT-1` standing cautions) and are exported as secondary rows, not
claims. And the AED half is *not* done — adjudication belongs to a weekly review
after the operator returns numbers.

## 2. How to run it

Needs the complex DolfinX build; the runner's `ans:` group sources it
automatically.

```
./run_examples.sh -e ans:3 -n 2 -t 500
```

Measured **131 s** wall clock at `mpiexec -n 2` on 178 055 cells
(mesh 35.9 s, 2-column sweep 46.3 s, export solve 21.4 s) — the heavy tier.
Through the logging harness, as every verification run must be:

```
scripts/testing/run_and_log.sh ANS-3-runnable-half-n2 "./run_examples.sh -e ans:3 -n 2 -t 500"
```

Each run **overwrites** `metrics.json` and `COMPARISON.md` in this directory,
so re-running is how you refresh them; nothing is hand-edited except the AED
columns.

## 3. How to analyze it, step by step

1. **Read the negative control line first.** The run's first `[ANS-3]` result
   line is the raw mutual ratio and its `MISS` label. If that line ever says the
   raw ratio passed, stop — the systematics story has changed and the numbers
   below it need re-deriving, not reporting.
2. **Check the reproduction line.** `reproduction of the 0.11-image record`
   prints four misses (relative on raw / corrected / ‖S‖₂, absolute on the
   symmetry residual). All four should sit near 1e-8 or below, against the 1e-6
   band. A miss that grows toward the band means this benchmark has drifted off
   the gated path even though the assertions still pass — the early warning, not
   the failure. The line below it is the band's negative control: the superseded
   v0.7.2 digits miss by ~2.9e-05, three decades outside.
3. **Read `COMPARISON.md`.** The Z table's **Im Z₂₁** row is the primary
   adjudication row: ours is +1.1108033e+00 Ω against ωM₁₂ = 1.241755 Ω. The
   closed form spans 66.5% of nominal over ±r_wire, so treat it as an anchor,
   never a gate. The Identities table carries the two gated rows
   (reciprocity, passivity) and one reported row (|Z₁₂ − Z₂₁|/|Z₂₁| =
   5.8309e-04 — a discretisation asymmetry, not a physics claim).
4. **Read `metrics.json`** for everything at full precision: the complex 2×2 Z
   and S as `{re, im}` pairs, the full systematics ladder (`raw` →
   `box_corrected` → `corrected`, each with its deviation), mesh sizing, and
   the per-stage timings. This is the machine-readable twin of `COMPARISON.md`;
   the two are written from the same in-memory dict, so they cannot disagree.
5. **Open the field export.** Load
   `paraview_output/ans3_two_torus_gap_ports_combined.xdmf` in ParaView,
   `Threshold` on `CellTags` — 1 and 2 are the two conductors, 101 and 102 the
   gap boxes — and colour by `E_magnitude` [V/m]. You are looking at the
   **port-1 drive only**: the field concentrates in gap box 101 and the
   conduction current closes around loop 1, with a much weaker induced response
   on loop 2. That ratio is the mutual coupling the Z₂₁ row quantifies.
   *Caveat, stated because it is easy to misread:* the sweep discards
   `TimeHarmonicFields`, so this file comes from **one extra solve** of port 1's
   drive run exactly as the sweep runs it — it is not a by-product of the
   sweep, and it costs the 21.4 s the timing line reports.
6. **When AED numbers come back**, paste all printed digits into the blank AED
   columns of `COMPARISON.md` and leave adjudication to the weekly review
   (§5.4). A disagreement with the commercial solver is a finding to diagnose,
   never to explain away — and here it is specifically an input to `PORT-10`,
   the chunk asking whether the two systematic corrections compose.

## Provenance

* Gated path: `examples/ports/02_package_sparameter_sweep.py` (`EX-20`), whose
  constants and helpers this script imports rather than restates.
* Gate of record: `PORT-1` step 4, PROJECT_PLAN §7.
* Log of the run whose numbers appear above:
  `docs/testing/logs/20260816T110354Z_ANS-3-runnable-half-n2.log`.
