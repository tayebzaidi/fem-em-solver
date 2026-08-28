# `ports:5` — the birdcage 4-port S-matrix across 10 / 64 / 128 MHz, one mesh

`EX-34`, the §5.4 ramp `PORT-11` ✅ (2026-08-26) owes. The first example in this
tree that solves a **port at a Larmor frequency**, and the first that puts all
three frequencies of the project's ladder side by side on one meshed object.

## 1. What this demonstrates

`ports:4` (`EX-32`) solves the coil's four lumped-sheet ports at **10 MHz**, the
port model's own frequency. `PORT-11` then carried the same three gates to 64 MHz
(step 2) and 128 MHz (step 3). Both gate modules build a **fresh mesh per rung** —
correct for a gate, where the mesh is part of what is asserted, but it means the
three frequencies are never the same meshed object in one process.

Here the `GEO-19` step-B fixture is built **once** — 116 085 cells, ratio
1.000000 of the record — and all **twelve driven solves** run on it. The
frequency is then demonstrably the only thing that moves between rungs, and the
resolution table below is a property of one mesh rather than three.

The fixture is `GEO-18`'s gapped, sheeted, phantom-loaded four-leg birdcage;
four `f = 0.5` lumped-element port sheets, one per leg, at `Z_p = 50 Ω`; each
rung is four driven solves assembled into a 4×4 by the **power-wave** route
(`PORT-9` leg (d3)).

### What it asserts

Nothing here is restated: every band and every record is imported from the
`PORT-9`/`PORT-11` modules, and the rungs are built by the gate module's own
`_four_port_rung` (`tests/validation/test_port_birdcage_leg_offset_sweep.py`),
called three times with `reuse=` pointing at the first rung.

* **gate (i)** reciprocity `‖S − Sᵀ‖/‖S‖ ≤ RECIPROCITY_BAND` (1e-3) — every rung;
* **gate (ii)** passivity `σ_max(S) ≤ 1 + PASSIVITY_SIGMA_TOLERANCE` (1e-9) with
  every column power sum `≤ 1` — every rung;
* **gate (iii′)** C4 symmetry, each circulant class of `Z` spreading
  `≤ ADJACENT_SPREAD_BAND` (0.5%), with the pooled-vs-worst control at
  `POOLED_SEPARATION_FLOOR` (10×) — every rung;
* **the pre-gate stop rule** `PHANTOM_CELLS_PER_LAMBDA_FLOOR` (10) at 128 MHz,
  imported *with its enforcement function* and run **before** any 128 MHz gate
  is read;
* **the 10 MHz anchor** — leg (d)'s recorded 4×4 `LEG_D_S_MATRIX_10MHZ` to
  `FREQUENCY_CONTROL_BAND` (1e-6) and leg (d0)'s `LEG_D0_Z_COLUMN` to
  `LEG_D0_REPRODUCTION_BAND` (1e-9);
* **the Larmor anchors** — the 64 and 128 MHz rungs reproduce `PORT-11` step
  2/3's recorded `σ_max`, max column power sum and three class spreads inside a
  pre-stated **1%** band (`LARMOR_RECORD_BAND`, the `EX-19` precedent).
  Reciprocity residuals are **excluded** by the (d3c) rule: power-wave readings
  sit at ~1e-16…1e-11 and reproduce in order of magnitude only;
* **the ladder itself** — the 64 and 128 MHz rungs assert `reused_mesh` and
  that their mesh *is the same Python object* as the 10 MHz rung's, so "one
  mesh" is a checked property and not a claim in a docstring.

### What it read on the run that landed it

`20260828T110615Z_EX-34-run2.log`, Status 0, **139 s** wall clock / 136.8 s
in-script at `-n 2` on the complex build. One mesh (116 085 cells, 24.0 s),
three sweeps of four driven solves (24.0 + 23.9 + 24.1 s), heuristic control
23.9 s, two export solves (5.8 + 6.0 s).

The frequency table on that one mesh — phantom region, from the full
lossy-medium propagation constants (never the good-conductor approximation):

| rung | loss tangent | δ (m) | λ (m) | cells/δ | cells/λ | air cells/λ |
|---|---|---|---|---|---|---|
| 10 MHz | 11.5225 | 2.350483e-01 | 1.354232e+00 | 12.0002 | 69.1393 | 3175.4062 |
| 64 MHz | 1.8004 | 1.159804e-01 | 4.288303e-01 | 5.9213 | 21.8936 | 496.1572 |
| 128 MHz | 0.9002 | 1.015497e-01 | 2.448845e-01 | 5.1845 | **12.5024** | 248.0786 |

The phantom crosses from conduction- to displacement-dominated up this ladder.
`δ` stops falling with frequency there, so it is `cells/λ` and not `cells/δ`
that tightens — which is why the stop rule is on λ. 12.5024 ≥ 10: **CLEAR**.

The three gates, all three rungs:

| rung | ‖S − Sᵀ‖/‖S‖ | σ_max(S) | max col. power | self / adjacent / opposite | pooled/worst |
|---|---|---|---|---|---|
| 10 MHz | 1.657e-14 | 0.999992805 | 0.793823974 | 0.0553 / 0.0353 / 0.0214% | 166.6766× |
| 64 MHz | 1.179e-15 | 0.999721388 | 0.804704664 | 0.0573 / 0.0599 / 0.0370% | 671.0527× |
| 128 MHz | 5.457e-15 | 0.998974779 | 0.861668762 | 0.1012 / 0.0916 / 0.0654% | 576.9483× |

Anchors: the 10 MHz rung reproduces leg (d)'s recorded 4×4 to a worst
**1.158e-10** against 1e-6, and leg (d0)'s terminated column to **2.568e-10**
against 1e-9. The Larmor rungs reproduce `PORT-11`'s records to a worst
**1.075e-03** (64 MHz, `spread_opposite`) and **6.755e-04** (128 MHz,
`spread_opposite`) against the pre-stated 1e-2 — those two worst misses are the
print precision of the recorded spreads (four significant figures), not a
physical difference; `σ_max` and the column-power maximum, which are recorded to
nine decimals, reproduce to **2.814e-10** and **4.374e-11**.

`|Im P|/Re P` at the driven port is **printed and never gated** — it is the
coil's stored energy, not a resonance reading.

### The negative control

The deprecated `PORT-0` coupling heuristic, on the same problem and the same
mesh, at **128 MHz** — the rung no control has ever been run on. It emits its
`DeprecationWarning`, reports `is_placeholder = True`, and prints an
**identically zero** off-diagonal (`max|off-diagonal| = 0.000000e+00`): the
retired route predicts no coupling between the coil's legs at all. Its
separation from the field-derived `S` reads **1.585461e+00** against the `EX-20`
floor of 2e-3.

The heuristic is handed the gap-box **cell** halves rather than the port sheets
because it validates its terminal tags against cell tags — it predates the port
sheet entirely and cannot address one. That is the control's content as much as
the numbers are: the retired route reads regions and a ring-distance rule, and
at 128 MHz it does not even know the frequency changed.

### Scope — read this before quoting a number

`PORT-11`'s claim, verbatim: these are **self-consistency identities on one
fixture, not an absolute-accuracy, resonance or tuning claim**. A reciprocal,
passive, C4-circulant 4×4 at 128 MHz says the assembly and the port model are
consistent at that frequency. It says nothing about whether this coil is tuned,
where its resonances are, or how close any entry is to a measurement or to
Ansys. There is no B1+ or SAR figure here, and the feed systematics on record
are the two-torus ones (`PORT-1` §2.2) — this fixture has no vessel wall, so its
regions are conductor, phantom and air.

## 2. How to run it

Needs the complex DolfinX build; the runner sources it for the `ports:` group
automatically. Run from the **host**, not inside the container — the runner
drives `docker` itself:

```
./run_examples.sh -e ports:5 -n 2 -t 400
```

Through the logging harness, as everything verified in this repo is:

```
scripts/testing/run_and_log.sh EX-34 "./run_examples.sh -e ports:5 -n 2 -t 400"
```

Standard tier: 139 s at `-n 2`.

## 3. How to analyze it, step by step

1. **Read the stop rule before the gates.** `[stop rule]` prints the 128 MHz
   phantom `cells/λ` against the imported floor of 10. The example calls the
   gate module's own `_require_resolution` there, which fails with the
   resolution as its message — a resolution miss must never be reported as a
   gate pass. If it ever reads below 10, the follow-on is a `GEO`
   phantom-sizing chunk a review commissions, never a widened band.
2. **Read the ladder table.** The interesting physics of this example is in the
   loss-tangent column: 11.52 → 1.80 → 0.90. The phantom is a conductor at
   10 MHz and a lossy dielectric at 128 MHz, and the two length scales behave
   differently across that crossing.
3. **Read the gates rung by rung.** All three hold at all three frequencies, and
   the class spreads roughly double from 10 to 128 MHz (0.0553 → 0.1012% on the
   self class) while staying five times inside the 0.5% band — the trend is a
   reading for a review, not a gate.
4. **Check the anchors.** The 10 MHz rung is the frequency control: it must give
   back leg (d)'s recorded 4×4 to 1e-6, or the harness moved rather than the
   frequency and nothing the Larmor rungs read is comparable.
5. **Open the fields.** In `paraview_output/`,
   `birdcage_larmor_frequency_ladder_128mhz_combined.xdmf` and
   `birdcage_larmor_frequency_ladder_10mhz_combined.xdmf` carry `E_real` / `E_imag` / `E_magnitude` (CG1) and
   `B_magnitude` (DG0, `B = ∇×E/(−jω)` from Faraday's law) beside `CellTags`.
   They are **on the same mesh**, so they open side by side and subtract. Open
   `birdcage_larmor_frequency_ladder_facets.xdmf` and threshold `mesh_tags` on
   211–214 to see the four port sheets the lumped BC lives on.

## Related

* `ports:4` (`EX-32`) — the same 4×4 at 10 MHz alone, with the full `Z` matrix
  and the leg (d0) column anchor.
* `ports:3` (`EX-24`) — the lumped-element sheet port itself, on the two-torus.
* `ports:2` (`EX-20`) — the package sweep and the heuristic control this
  example's negative control follows.
* `mesh:8` (`EX-33`) — the same coil at sixteen legs, mesh only; no solve
  exists there.
* PROJECT_PLAN.md §2 and the `PORT-9` / `PORT-11` entries in §7 — what an
  S-parameter figure from this repo may and may not be used for.
