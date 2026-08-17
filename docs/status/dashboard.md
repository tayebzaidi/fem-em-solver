# FEM-EM Solver — status

**Updated:** 2026-08-17, 03:00 review. A clean-sweep interval: **all four
slots closed their items**, all four audited §4-compliant — `GEO-16`
(port-sheet mesh), `OPS-17` step 1 (finiteness inventory), `TH-11` step 4
(the "frequency trend" was mesh resolution), and `PORT-9` step 1 (the
**first lumped-port Z ever solved** in this project, 7.71% off the gated
gap route — deliberately not gated; step 2 adjudicates). Source of truth
is `PROJECT_PLAN.md`; this page is a read-only digest for the human
operator.

## Waiting on you

0. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). The
   FEM half is on record; your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. Now doubly worth doing: it independently adjudicates
   both `PORT-10`'s composition result **and** the new `PORT-9`
   cross-route question.
1. **Two operator decisions the automation cannot make** (unchanged):
   (a) **`OPS-16` unblock** — retry-on-529 is designed but
   `Edit(scripts/automation/**)` is under `ask`; move the three launcher
   files to `allow` or apply by hand (mind the `.gitignore` bare-`lib/`
   trap). (b) **Outage visibility** — nothing records a *missing* run.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 0) is the
   second case in the same queue.
4. Housekeeping: local `main` is now **87 commits ahead** of
   `origin/main` (last push 2026-08-10) — push when convenient.

## Honest current state (digest of §2 — two bullets moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.88% (MAT-6). **TH-11 step 4 attributed the apparent frequency trend to mesh resolution**: fixed-f h-ladders read flat, the 10/30 MHz h→0 brackets overlap at ~−1%. But 64 MHz — the frequency that matters — still has **no h→0 bracket** (finest rung +2.81% at 2.52 cells/δ); step 5 (queued) prices its third rung. Larmor coil loading stays labeled an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only. **PORT-9 step 1 closed: the first lumped-port Z is solved** (Jin resistive sheet on GEO-16's new interior surface, identities green) — it reads 0.829782 × ωM₁₂ vs the gated gap route's 0.894310, a 7.71% cross-route miss against step 2's pre-stated 5% band. The band does not move; step 2 tests the sheet-average-vs-centreline fringe hypothesis. §2.2's "no coil has ports" stands |

## Recent activity (2026-08-16 18:00 → 08-17 03:00)

- **GEO-16 ✅** — `two_torus_domain` now emits the gap boxes'
  longitudinal mid-plane behind an opt-in kwarg, facet tags rebuilt
  dolfinx-side (known-issues 9); sheet area = CAD to `1.000000000000`,
  kwarg-off control bit-matches the recorded mesh. Unblocked the port
  lineage the same night.
- **PORT-9 step 1 ✅ (chunk stays 🟡)** — parked formulation branch
  merged, six exact identities green on the merge, sheet wired onto the
  solve fixture with **measured** extents (w/h = 0.745249896 — the
  mesh-only fixture's 1.504 would have scaled R by 2×; the run caught
  this). Gap route re-measured on the fragmented mesh moved only
  −0.0233 pp. Cross-route 7.71% is the finding step 2 exists to
  adjudicate — recorded with a falsifiable hypothesis, band untouched.
- **TH-11 step 4 ✅** — Richardson ladders at fixed f: refinement moves
  the deviation −1.87 pp (10 MHz) / −4.48 pp (30 MHz), brackets overlap
  at ~−1%. The monotone 1.58/5.59/10.27% set was the resolution
  confound, not physics. Step 5 scoped: the 64 MHz third rung
  (~9 min/solve — cost-probe binding).
- **OPS-17 step 1 ✅** — AST sweep of all 306 test functions: 59
  finiteness-only candidates, each confirmed by reading — **10 replace
  (anchors named) / 4 delete / 45 keep (justified)**. Key negative
  finding: no ⚠️ chunk rests on a swept row, so step 2's ⚠️-retirement
  clause was rescoped to "confirm and say so".
- Review housekeeping: merged `attempt/*` branch deleted; both stale
  §2.2 bullets rewritten; OPS-17's 1 s/2 s elapsed slip corrected.

## Automation health

- **Implementer grid: 4/4 slots productive, 4/4 audited COMPLIANT** —
  second clean interval in a row, and the first with a 100% closure
  rate. Tree clean at every handoff; no `attempt/*` or `recovered/*`
  branches remain.
- The one process wrinkle: PORT-9's first re-run log carried a
  comparator sign slip (generator convention), caught and corrected
  in-run with both logs committed — the audit trail pattern working as
  intended.
- Standing weekly-review items unchanged: POST-4 export adoption (your
  ParaView check) and ANS-1/ANS-3 adjudication (no AED numbers yet).

## On deck (§9, restocked this review; items 1–4 independent, 5 spare)

1. **PORT-9 step 2** — cross-route adjudication: bands as pre-stated
   (7.71% is outside; expect the diagnosis branch — quantify the
   fringe hypothesis).
2. **OPS-17 step 2** — execute the dispositions (4 deletes, 10 anchored
   replacements; sweep re-run as before/after control).
3. **TH-11 step 5** — 64 MHz third rung, the missing h→0 bracket
   (heavy; cost-probe binding).
4. **EX-23** — port-sheet mesh example (GEO-16's gated capability;
   mesh-only, standard).
5. *(spare)* **EX-22** — restore the six examples' artifacts
   (stale 24 → 0; heavy).

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
