# FEM-EM Solver — status

**Updated:** 2026-09-12 18:00 daily review. Headline: **all four slots since
10:30 did chunk work** — no row closed, four measurements landed, and your
four directives from the 12:11 session are **all accepted and enacted**:
the plan-file split is queued as four steps, slots now take a second item
when they finish early, step families are capped at four attempts (three
families are frozen today), and every queued item must name the status it
can move.

What the slots found:
- **`ANS-4`: the fixed-mesh degree-1 ladders are not converged on either
  knob, and the knobs interact.** A fourth global rung pulled the fitted
  exponent from ≈ 3 into the 1.4–1.9 range and moved the extrapolant by up
  to 1.2 %; repeating the ladder at a finer conductor grading moved the
  opposite-port class differently (its steps stop shrinking). Banked as a
  measured negative for the weekly's Larmor verdict: the only converging,
  order-matched sequence on record is the degree-2 XL ladder from 09-10.
- **`PORT-14`: the corrected width works at 64 MHz.** Scaling every sheet
  width by (1 + κ) took both lossless residuals under the band on the gate
  mesh, with the zero point re-measured in the same window to 1e-7. The
  step-2 family is closed on that positive reading; registering a κ-derived
  route (128 MHz out of sample) is the weekly's step 3.
- **`WF-6`: the ×0.0095 facet is not a sliver.** The no-solve census puts it
  among the best-shaped facets on its sheet and the largest, on the lateral
  rim. Four slots have now diagnosed a rung already off the ladder; the
  family is frozen and the entry stays open as a banked negative.

**Still a self-consistency story at the Larmor frequencies:** no absolute SAR,
no C95.3 figure, no homogeneity, no Larmor coil accuracy, no resonance or
tuning, no closed-form B₁⁺ claim, and no solve on the human-scale mesh.
`PROJECT_PLAN.md` is the source of truth; this page is a read-only digest for
the human operator.

## Waiting on you

1. 🟠 **`OPS-46` needs two agent-definition edits only you can make.**
   *(New.)* `Edit(.claude/**)` is on the *ask* list, so headless sessions
   cannot touch `.claude/agents/plan-navigator.md` (add
   `docs/planning/chunks/` to its corpus) or `.claude/agents/auditor.md`
   (step 1: "the row plus its chunk file"). Until then the navigator will
   answer NOT FOUND for moved text and reviews Read the chunk files
   directly. Step 1 of the chunk journals the exact one-liners.
2. 🔴 **Privacy slip in `998edf9` (ANS-4 step 2d record).** *(Carried.)* The
   ours-vs-AED gap percentages were redacted from the tracked files, but they
   are still in that commit's diff. Decide **before the next push** whether to
   rewrite that history.
3. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried.)* The spec reuses your
   `ANS-4` HFSS project
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`).
4. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
   `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
5. 🟡 **Both containers were `Exited (137)` around 14:00 CDT on 09-10**, cause
   unknown. *(Carried; referred to the weekly.)* No recurrence: `fem-em-solver`
   has been Up for 2 days.
6. 🟢 **For the 09-13 weekly (no action):** the Larmor verdict with the
   two-knob ladder readings and the degree-2 sequence; three frozen families
   needing a numbered next step (`ANS-4` step 3, `PORT-14` step 3, `WF-6`
   step 5); `POST-6`'s row (open item absorbed by `PORT-16` ✅ — audit and
   close or re-scope); `TH-11` step 5d's §2 sentence; `TH-19` outcome (a);
   the third draw of the 2-rank MUMPS drift.
7. 🟡 **Agent-definition edits.** *(Carried.)* Five one-liners for
   `example-runner.md`, `mesh-probe.md` and `implementer.md`, plus
   `implementer.md`'s missing "Last verified against" footer. Item 1's two
   edits belong in the same sitting.
8. 🟢 **`ANS-3` AED run** — behind item 3.
9. **Information:** the commit-first checkpoint in
   `docs/automation/weekly-review.md` (08-30) still awaits your OK.
10. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12;
    `scripts/probes/post4_step5_probe.py` regenerates.)

## Honest current state (digest of §2 — **unchanged this interval**)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅). On the coil, degree 2 passes the power identity **only under `"matched"`** (`TH-19`) |
| Conductor model | 🟡 PEC-hole gap-volume fix on `main` (`TH-15` step 3b), default not flipped | unchanged |
| Coil loading | ⚠️ eddy-current regime only; the 64 MHz bracket sentence is the weekly's | `MAT-6` ✅ Dodd–Deeds; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; **self-consistency only** | degree-1 ladders on the fixed fixture **not in an asymptotic range on either knob, and the knobs interact** (`ANS-4` steps 2f/2g, family frozen); the degree-2 XL ladder converges (step 2d); factor reuse reproduces the 4×4 exactly (`PORT-19` ✅) |
| Lumped RLC | 🟡 10 MHz floor registered; **64 MHz: a (1 + κ)-corrected width takes both residuals under the band** (step 2e), not yet a registered route | family frozen; step 3 is the weekly's |
| B₁⁺ | 🧪 symmetry-gated at CG1; ladder on `main` 5.25% → 2.07% | ×0.0095 power miss located on one large, well-shaped rim facet, **not explained**; family frozen |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | unchanged; no absolute or compliance claim |
| Test-suite trust | ✅ residual reds at `-n 2`: **3** deliberate/known | harness honours a final capture rc line (`OPS-45` ✅) |

## Recent activity (2026-09-12 10:30 → 18:00)

- **12:00:** `ANS-4` step 2f landed. One window, 440 s at 8 ranks; p ≈ 3
  did not hold.
- **12:11:** your interactive session left four directives (`247290d`).
- **13:30:** `PORT-14` step 2e landed. One window, 191 s; both residuals
  under the band at 64 MHz.
- **15:00:** `ANS-4` step 2g landed. One window, 432 s at 8 ranks; the
  knobs interact.
- **16:30:** `WF-6` step 4k landed via `mesh-probe`. Four no-solve windows,
  29–39 s each; not a sliver.
- **18:00 review (this one):**
  - no row turned ✅, so nothing to audit;
  - all four directives accepted and enacted (`implementer-run.md`,
    `daily-review.md`, §9 preamble, §7 `OPS-46` row);
  - three step families frozen with their rulings in §7 and known-issues;
  - five items queued (four are the plan split, in a stated chain); the
    10:30 narrative archived.

## Automation health

- **Implementer slots: 4 of 4 fired** and all landed work. No window died, no
  ranks were orphaned, no masked status. One slot correctly shortened a
  container `timeout` the item had over-sized (900 → 600 s).
- **Slots now take a second item when the first is committed before
  minute 30** (enacted this review). Watch the 19:30–00:00 journals for the
  first double-item slot.
- **XL / XXL path:** both queue files are empty.
- **Tree:** clean. **Branches:** 4 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e`), kept. No `recovered/*`.
- **Review model:** `claude-fable-5-1`; no override set.

## On deck (§9 — five items; 1 and 3–5 are one chunk in a chain, 2 is independent)

1. **`OPS-46` step 1** *(implementer; smoke, no compute)* — the tooling for
   the plan-file split: leak-check coverage, the byte-identity `chunks`
   subcommand, protocol sentences, a dry run over the 74 rows over 2 KB.
2. **`PORT-19` step 6** *(implementer; ≈ 6 min, 2 ranks, runs only)* — the two
   unrun example callers (`ports:3`, `ports:13`) on the reuse-on default.
3. **`OPS-46` step 2** *(depends on 1)* — move the WF, ANS and PORT
   families (12 rows, ≈ 175 KB), one commit per family.
4. **`OPS-46` step 3** *(depends on 1)* — move OPS, GEO and MAG (34 rows).
5. **`OPS-46` step 4** *(depends on 1; closure on 3 and 4)* — move TH, MAT,
   POST and EX (27 rows), re-measure the plan (< 0.85 MB), claim closure.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
