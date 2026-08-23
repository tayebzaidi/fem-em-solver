# FEM-EM Solver — status

**Updated:** 2026-08-23 03:00, **daily review (scheduled, ran normally)**.
Headline: **the birdcage's termination is found, and the upgrade is one
writing slot from green.** Three of four slots closed their item on the
first run: `MAG-18` replaced the sampler-fragile wire gate with a domain
L2 converging at rate **1.68** (closed ✅ this review), `EX-28` made the
gapped birdcage an example, and `PORT-9` leg (d0) showed that at the
ports' own **50 Ω** the birdcage conducts (current up **13 876×**) and its
four ports separate into their two symmetry classes with a **598×**
margin — the port impedance is the gap capacitor. `OPS-18` 3a stopped on
the review's own "bit-identical" clause, which the solver cannot meet at
~1e-10; restated here, the records are written next slot. The weekly
review ran at 02:15 and archived ~9 000 lines of plan history. `main`
still boots 0.7.2 by design. Source of truth is `PROJECT_PLAN.md`; this
page is a read-only digest for the human operator.

## Waiting on you

**Nothing new is blocked on you this interval.** The one decision owed
(`OPS-18` ruling (1)(b)) was the review's and is made.

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the second
   case in the same queue.
4. FYI: the weekly review (02:15) decided **degree 1 is the production
   order** for coil-fed solves (§10) and commissioned `PORT-11` (ports at
   64 MHz, serial on `PORT-9`). Local `main` is well ahead of origin (push
   is manual; last push 08-18 night).
5. FYI, standing: the `docker-compose.yml` allow is used only for
   `environment:` keys; `volumes:`, the mount and the 64 G limit are
   untouched. Every `OPS-18` slot has restored 0.7.2 and probed it.
6. FYI, a finding worth knowing: **the solver is run-to-run
   non-deterministic at ~1e-10 relative** (MPI summation / LU pivot
   order) — so "reproduces bit-identically" is not a criterion any record
   can meet. Every physics band is orders of magnitude above it; nothing
   was loosened. Records are now written to shared digits under a
   per-record rule ((b′), §7 `OPS-18`).

## Honest current state (digest of §2 — one line changed)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; Helmholtz 0.04%, loop 7.07%; **wire: `E_Ω` = 10.73% at h = 0.0025, rate 1.68 on the ladder (`MAG-18` ✅ 08-23)** — the retired 10-point number read 12.75%/15.80% on the same field; MAG-17 rate 2.4476 |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power 3.63% (TH-10); degree-2 gated at 0.1405% (TH-12/EX-25) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6); no affordable 64 MHz bracket on this box (adjudicated 08-18); Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus only; **the gapped birdcage has two solved port columns at 10 MHz** (PORT-9 legs (c)/(d0), 0.7.2): at 50 Ω, C4 adjacent spread 0.0152% vs 5%, classes separated 598× — still no network, no reciprocity claim; §2.2's "no coil has ports" stands until legs (d) + (d1) |
| Test-suite trust | ✅ reconciled | OPS-17 closed 08-21. **On 0.11 (branch only): TH-6, TH-10, MAT-4, MAT-6 reproduce; PORT-1's physics gates hold, `MAG-18`'s anchors hold (rate 1.6854); four reproduction records await their (b′) write** |

## Recent activity (2026-08-22 18:00 → 2026-08-23 03:00)

- **19:30:** `MAG-18` landed — `7 passed` / 270.64 s / `-n 2`. `E_Ω`
  25.38 → 10.73 → 6.67% on the h = 0.004/0.0025/0.0018 ladder, rate
  **1.6842** (pre-registered ≥ 0.7); natural-BC wall 3.0× worse; the
  retired sampler row reproduced under assertion. Anchor (ii) read
  7.28e-08 vs an unreachable 1e-10 — the direct-LU cross-width floor,
  measured not guessed; left for this review.
- **21:00:** `EX-28` closed as written on the first run (`mesh:6`, exit 0,
  46 s): sheet area = analytic on all four ports to 1e-12, C4 spread
  8.5e-16, and the uncut control measured facetless (`_global_facet_count`
  = 0) — the clause `GEO-18`'s audit found implied is now asserted.
- **22:30:** `PORT-9` leg (d0) — `8 passed` / 48.90 s, every digit
  reproduced by a second run. At `Z_p = 50 Ω`: margin **598.4×** vs 10×,
  adjacent spread **0.0152%** vs 5%, `|I₁|` 1.0 µA → 13.9 mA; the 1e6 Ω
  control reproduces leg (c) to 2.4e-10. `Z₁₁` goes 3.43 kΩ capacitive →
  21.7 + 7.5j Ω; mutuals 17.01 (adjacent) vs 16.03 Ω (opposite).
- **00:00:** `OPS-18` 3a attempt 6 — leg 2's `MAG-18` anchors hold on 0.11
  (rate **1.6854**, monotone, natural-BC 0.3285; the rate moved 7e-4 across
  a bump that moved the old statistic 21%). Leg 1 stopped on "bit-identical":
  two same-slot runs differ at 1.2e-10 / 3.3e-10 / **1.0e-06** (the
  symmetry residual, cancellation-amplified). Nothing written, no band
  touched; known-issues entry filed.
- **02:15:** weekly review — §10 Phase-5 assessment (exit ≈ 09-08…15),
  degree-1 production order decided, `PORT-11` commissioned, ~9 000
  lines archived out of the plan and attempts journal.
- **This review:** `EX-28` audited compliant; **`MAG-18` ✅** ((ii)
  re-registered at 1e-6, 14× the measured floor); **ruling (1)(b)
  restated as (b′)** per-record (the implementer's 1e-9 proposal would
  have rejected the symmetry record); **`PORT-9` legs (d) and (d1)
  scoped** — the 08-16 geometric control's wording corrected (rotate the
  leg with its port; a box off its leg is a degenerate port). Old §9
  block archived.

## Automation health

- Four slots, four useful outcomes: three first-run closes, one
  stop-on-evidence that named the exact clause it could not satisfy. No
  drain, no exit 124, no wedge, no permission denial. Tree clean at every
  handoff; no `recovered/*`; container probed 0.7.2 after the one restore
  (`20260823T052032Z_OPS-18-step3a-container-restore.log`).
- The weekly review ran in its slot and left a clean tree.
- `attempt/OPS-18` is the sanctioned worksite at `9b3c9e2` (main merged
  in) and persists until item 4 merges it.
- The queue holds **five** items: three independent (two on 0.7.2 `main`,
  one on the upgrade branch), one serial on the upgrade, one serial on
  `PORT-9` ✅ with an explicit stop-and-journal if it is reached early.

## On deck (§9 — five open items this review)

1. **`PORT-9` leg (d)** — the 4×4 at 50 Ω: reciprocity ≤ 1e-3, passivity,
   C4 class spreads ≤ 5%; (d0)-column and pooled-class controls (0.7.2,
   standard, ~60–80 s)
2. **`OPS-18` 3a under (b′)** — write the four re-records to shared digits,
   confirm `19 passed` / `11 passed`, finish leg 2's two cheap files
   (branch, heavy)
3. **`PORT-9` leg (d1)** — `leg_azimuth_offsets_rad` mesh knob; rotate one
   leg a quarter-spacing and assert the C4 gate *fails* while reciprocity
   holds (0.7.2, standard, independent of item 1)
4. **`OPS-18` 3b** — §5.3 table, drift disposal, confirming run, **merge**
   (depends on item 2)
5. **`PORT-11` step 1** — one priced 64 MHz solve on the loaded birdcage
   (serial on items 1 + 3 and `PORT-9` ✅; stop and journal if reached
   early)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
