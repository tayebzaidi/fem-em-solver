# FEM-EM Solver — status

**Updated:** 2026-08-20, 03:00 review. Headline: **the 18:00 review was
killed at launch by a transient API 500** — the exact failure class the
blocked `OPS-16` retry patch exists for — and the downstream cost was the
worst yet: the on-deck queue was never topped up, three implementer slots
ran the drain fallback and the fourth blocked with nothing to do. The
fallback slots were still productive: `PORT-9` step 3's preflight found,
with exact identities, that **the birdcage fixture cannot host ports at
all** — no port-sheet facet exists and the port boxes have *no terminals*
(conductor-facing area exactly 0.0 m² on all four; the coil is uncut and
the boxes float in air outside it). The fix is commissioned as `GEO-18`
(cut the legs, two-torus topology transplanted) and is queue item 1.
Also this interval: **POST-5 closed ✅** (the balance helper knows the
impressed-source term; the smoke xfail is now a plain 16.7% gate vs 25%),
`TH-12` step 3 read the degree-2 energy explosion as **COIL-SPECIFIC**,
`OPS-21` and `EX-22` closed (docrefs checker returned its first
`exit=0`), and all four closes audited COMPLIANT. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human
operator.

## Waiting on you

0. 🔴 **`OPS-16` unblock — now with a third, worst-cost occurrence.**
   The 2026-08-19 18:00 review died at launch on an API 500
   (`logs/automation/20260819T230001Z_daily-review.log`, one line), and
   because no review topped up the queue, it took one review + three
   drain-fallback slots + one blocked slot with it. The retry design has
   been parked and ready since 2026-08-14 (attempts.md 2026-08-14T02:03Z);
   it is blocked only by `Edit(scripts/automation/**)` sitting under
   `ask`. Your options, unchanged: (a) move the three launcher files to
   `allow` (keep `hooks/` gated), or (b) apply the patch by hand in an
   interactive session.
1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). The
   FEM half is on record; your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. The measured **0.23 pp drive dependence** between
   impressed-gap and lumped-sheet drives makes an AED lumped port a
   direct external check on both.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the
   second case in the same queue.
4. FYI (unchanged): memory headroom on degree-2 coil runs is ~2 GiB.
   Local `main` remains ahead of origin (push is manual; last push
   08-18 night — the PORT-9/POST-5/GEO-18 work since is local only).

## Honest current state (digest of §2 — one row updated this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells); the complex build reproduces the same records to the digit (OPS-22/OPS-20) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10); degree-2 N1curl gated at 0.1405% (TH-12 step 1, also an example — EX-25) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6). Adjudicated 08-18: no affordable (order, h) route to a gated 64 MHz bracket on this box. Larmor coil loading stays an extrapolation. New this interval: the degree-2 energy-identity defect is **coil-specific** (TH-12 step 3: smoke 1.155×, sphere 1.015×, coil 3.4e7× across order), mechanism input now with the weekly review |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil. **POST-5 closed ✅ this interval:** `poynting_power_balance` now scores the three-term identity (boundary + dissipated + impressed source); the former smoke xfail is a plain gate at 16.7% vs the unmoved 25%, with the J = 0 source term asserted exactly 0.0 on TH-6 |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only; PORT-9 step 2c reciprocal at 2.6e-11 (example EX-24). **Updated this interval: step 3 (birdcage) is 🚫-blocked on the mesh** — the birdcage has no port facets and no terminals (measured under exact closure identities, both legs 🚫). `GEO-18` (cut the legs) is commissioned and is queue item 1. §2.2's "no coil has ports" stands |

## Recent activity (2026-08-19 10:30 → 2026-08-20 03:00; eight implementer slots — the 18:00 review did not run)

- **OPS-17 leg (b2) attempt 3 🟡 (12:00 slot)** — first clean run under
  the rescope: coverage 44 → **63**/227, blocked 5 → 0, anchor
  reconciled exactly. Tail: 162 tests in ~35 files, now the expensive
  half; continuation prescription is in §7 (queue spare).
- **TH-12 step 3 ✅ (13:30 slot, audited COMPLIANT)** — the degree-2
  `W_e` explosion is **COIL-SPECIFIC**: incompatible `J·n ≠ 0` drive
  moves `W_e/W_m` only 1.155× across order (sphere 1.015×) vs the
  coil's 3.4e7×, so the incompatible-drive hypothesis is refuted.
  Confound honestly on record: the fixtures' baseline ratios span six
  orders, so "feed model" vs "only a W_m ≫ W_e fixture can display it"
  is still open — the weekly review's decision clause has its input.
- **POST-5 step 4 ✅ and chunk ✅ (15:00 slot, audited COMPLIANT)** —
  the helper takes `current_density` + `source_measure`; smoke xfail →
  plain gate at 16.7465% vs unmoved 25%; J = 0 control exactly 0.0 W,
  bit-identical elsewhere. Audit note: the σ-blind separation bar was
  re-derived 10× → ≥ 3.0× when the score became three-term (arithmetic
  ceiling 5.97×; measured 4.97×) — disclosed, journal-pre-registered.
- **OPS-21 ✅ (16:30 slot, audited COMPLIANT)** — exact attribute-set
  identity in both builds; the commissioned "tmp-path race" diagnosis
  was wrong — the test's own rank-0-only `return` was the defect, and
  the executed red baseline proves the verdict is now collective.
  Follow-on: the same pattern was found at four more sites (→ OPS-23).
- **EX-22 ✅ (19:30 slot, audited COMPLIANT)** — the standing stale=24
  docrefs backlog is **0**; first `exit=0` under the OPS-19 contract.
  The audit confirmed stale=0 is perishable **by design** (48 h
  freshness window; staleness exits 2 = report-only) — it will read
  stale=24 again from ~08-22 and that is expected, not a regression.
- **PORT-9 step 3 legs (a)+(b) 🚫 (21:00 + 22:30 drain-fallback slots)**
  — decisive negatives, both anchored: no port-sheet facet (global
  facet set `{1}`), no terminals (0.0 m² conductor area on all four
  boxes, closure identity 1.000000000000, phantom↔air control 0.971 of
  closed form). Leg (b) refuted leg (a)'s mid-plane prescription and
  wrote the corrected one this review commissioned as `GEO-18`.
- **00:00 slot blocked cleanly** — queue drained + fallback exhausted;
  journal only, plus a free grep survey that measured the OPS-23 sites.

## Automation health

- **The 18:00 review never ran** — API 500 at launch, one-line wrapper
  log. 8/8 implementer-grid slots launched; 5 did commissioned queue
  work, 2 ran the drain fallback usefully, 1 blocked per protocol. This is
  the queue-topology cost of a lost review, and it lands on the
  Waiting-on-you item 0 decision.
- Container healthy all interval (Up 2+ d): no OOM, no wedge. Tree
  clean at every handoff; no `attempt/*` or `recovered/*` branches.
- All four ✅ closes this interval audited COMPLIANT (one subagent
  auditor each; every claimed number verified against its log footer).
- OPS-18 (DolfinX upgrade) unchanged: its fired trigger remains
  unqueued per the 2026-08-19 operator note.
- Standing weekly-review items: TH-12 production-order decision now has
  its step-3 mechanism input; POST-4 export adoption and ANS-1/ANS-3
  adjudication unchanged.

## On deck (§9, restocked this review; six items, 1–5 independent)

1. **GEO-18 step 1** — cut the birdcage legs so the ports have
   terminals (the PORT-9 step-3 prerequisite; terminal disks gated
   against π·r² closed form, uncut fixture asserted bit-unchanged).
2. **GEO-17 step 1** — the region-resolution policy that shrinks the
   coil volumes it refines (MAT-4's road to SAR-on-a-coil).
3. **MAG-17 step 1** — Coulomb-gauge multiplier h-ladder discriminator
   (pre-registered DISCRETE-SOURCE vs ASSEMBLY-DEFECT bands).
4. **OPS-23** — sweep the OPS-21 rank-0-return defect pattern (4
   measured sites) + the helmholtz Im-bound; red baseline per file.
5. **EX-26** — Poynting power-balance audit example (POST-5's newly
   gated capability; no existing example covers power accounting).
6. *(spare)* **OPS-17 leg (b2) next coverage leg** — one
   coil_loading/dodd_deeds family per 540 s window, balance file alone.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
