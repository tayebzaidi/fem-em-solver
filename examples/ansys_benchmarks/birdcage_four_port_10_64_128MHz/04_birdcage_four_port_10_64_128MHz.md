# ANS-4 — loaded birdcage, four lumped ports, 10 / 64 / 128 MHz (4×4 Z and S)

Guide to `04_birdcage_four_port_10_64_128MHz.py`, the third commissioned Ansys
Electronics Desktop benchmark case (PROJECT_PLAN §5.4, chunk `ANS-4`) and the
**first at a Larmor frequency**. `SPEC.md` in this directory is the authority for
the boundary-value problem the human operator replicates in AED; this script is
our half of it.

## 1. What this demonstrates

The `GEO-18` gapped, sheeted, phantom-loaded four-leg birdcage, driven one
lumped port at a time with the other three terminated in 50 Ω, at **10, 64 and
128 MHz on one mesh** — twelve driven solves on `GEO-19` step B's 116 085 cells,
built once and reused. It regenerates the 4×4 `Z` and `S` that `PORT-9` ✅
(10 MHz) and `PORT-11` ✅ (64 and 128 MHz) gated, and writes them out for AED to
disagree with:

| Artifact | Contents |
|---|---|
| `metrics.json` | full complex 4×4 `Z` and `S` at each frequency, the three gate figures per rung, `\|Im P\|/Re P` at the driven port, the resolution table, mesh / timing / basis-order metadata |
| `COMPARISON.md` | the SPEC's export tables, our column filled and **two** AED columns blank (Zero Order and First Order, the `ANS-5` ruling) |
| `paraview_output/ans4_birdcage_four_port_128mhz_combined.xdmf` | the port-1-driven `E`/`B` phasor magnitudes at 128 MHz, beside `CellTags` |

**Nothing here is re-implemented.** The rungs are built by `_four_port_rung`,
the gate modules' *own* constructor
(`tests/validation/test_port_birdcage_leg_offset_sweep.py`), and the bands,
records, gate assertions, heuristic control and ParaView field builder are
imported from `examples/ports/05_birdcage_larmor_frequency_ladder.py` (`EX-34`).
That is the `ANS-1` rule: a benchmark that transcribes numbers can drift away
from the gate it claims to export. If the gated path moves, this case moves with
it and its reproduction assertions fire.

**Scope — read before quoting any number.** `PORT-11`'s claim verbatim:
**self-consistency identities on one fixture, not an absolute-accuracy,
resonance or tuning claim.** A port model wrong by a constant factor passes all
three gates — which is exactly why this case exists and why the AED columns
matter. There is no B1+ and no SAR figure here; `|Im P|/Re P` is exported and
never gated. Adjudication belongs to the weekly review *after* the operator's
two AED runs land.

## 2. How to run it

```
./run_examples.sh -e ans:4 -n 2 -t 500
```

The `ans:` group sources the complex DolfinX build automatically; the script
raises rather than solving if it finds a real build. Cost: twelve driven solves
on one mesh plus one export solve and one heuristic control, ≈ 120–220 s at
`-n 2`, heavy tier by the runner's `-t 500`. `metrics.json` and `COMPARISON.md`
are rewritten in place on every run; `paraview_output/` is not tracked, as
everywhere else in this repository.

## 3. How to analyze it, step by step

1. **Read the negative control, which prints first.** The retired `PORT-0`
   coupling heuristic runs on the same problem and the same mesh at 128 MHz:
   `is_placeholder` asserted True, its `DeprecationWarning` shown, its
   **identically zero** off-diagonal printed (it predicts no coupling at all),
   and its separation from the field-derived `S` — 1.585460 — asserted above
   `EX-20`'s 2e-3 floor. The gates are never the first thing the log shows.
2. **Check the mesh line.** 116 085 cells at ratio 1.000000 against `GEO-19`
   step B's record, and `reused_mesh` asserted on both Larmor rungs. The SPEC
   promises AED one geometry solved at three frequencies; these two assertions
   are what make that structurally true rather than merely described.
3. **Check the pre-gate stop rule**, enforced *before* any 128 MHz gate is read:
   phantom cells/λ = 12.5024 against the imported floor of 10. A resolution miss
   must never be reported as a gate pass.
4. **Read the three gates on each of the three rungs**: (i) reciprocity
   `‖S − Sᵀ‖/‖S‖ ≤ 1e-3`, (ii) passivity `σ_max(S) ≤ 1 + 1e-9` with every column
   power sum `≤ 1`, (iii′) each circulant class of `Z` spreading `≤ 0.5%`, with
   the pooled-vs-worst separation control above its 10× floor. Reciprocity
   residuals sit at ~1e-16…1e-14 and reproduce in **order of magnitude only**
   (the `PORT-11` (d3c) rule) — compare the decade, not the digits.
5. **Read the record reproductions.** The 10 MHz rung reproduces leg (d)'s
   recorded 4×4 `S` to 1e-6 (worst entry 1.16e-10) and leg (d0)'s terminated `Z`
   column to 1e-9 (worst 2.57e-10). The 64 and 128 MHz rungs reproduce
   `PORT-11` steps 2/3's `σ_max`, column-power maximum and class spreads inside
   `EX-34`'s pre-stated 1% band (worst ≈ 1.1e-3, on a spread quoted to three
   digits).
6. **Open `COMPARISON.md`** — the nine C4-class entries at the top are the
   primary adjudication rows. Fill the **AED (Zero Order)** column from the
   matched discretization (our degree-1 Nédélec, 6 unknowns/tet) and the **AED
   (First Order)** column from the AED default (20 unknowns/tet) as an
   order-sensitivity reading. Mixed Order is forbidden — we have no per-element
   order and could not reproduce it. `Z₁₁` is a secondary row carrying our
   sheet-width convention `w = A/h` (`PORT-9` step 2b) and is never gated.
7. **Open the XDMF in ParaView** to see the field the terminal numbers came
   from: threshold `CellTags` (1 = conductor, 2 = phantom) and colour by
   `E_magnitude` [V/m] or `B_magnitude` [T]. It is the port-1-driven case at
   128 MHz. A named limitation, `EX-20`'s: the sweep returns port quantities,
   not fields, so this file costs **one extra solve** — the script says so
   rather than pretending the sweep produced it.

## Provenance

* Gated path: `examples/ports/05_birdcage_larmor_frequency_ladder.py` (`EX-34`)
  and the gate modules' own `_four_port_rung`.
* Gates of record: `PORT-9` ✅ 2026-08-25 (10 MHz), `PORT-11` ✅ 2026-08-26
  (64 and 128 MHz), PROJECT_PLAN §7.
* Fixture: `GEO-18` gapped + sheeted four-leg birdcage, phantom loaded, on the
  `GEO-19` step B mesh.
* Element-order correspondence: the `ANS-5` ruling, 2026-08-30.
