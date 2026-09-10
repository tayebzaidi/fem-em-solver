# FEM-EM Solver — status

**Updated:** 2026-09-10 03:00 daily review. Headline: **tonight's XL window
never ran, and it needs a decision from you before 02:00 tomorrow.**
`scripts/automation/xl-run.sh` was committed without its execute bit, so cron
could not start it. The script writes its log before doing anything else, and
no log exists. `ANS-4` step 2d is still queued, and the dated XL override it
was due inside expires at the end of today. In the slots, four for four:

- the port-sheet census found the four C4 port sheets are the **same patch
  cut four different ways on every mesh**, including the one every port gate
  passed on;
- one ops chunk closed ✅ (audited PASS);
- the parked PEC-hole change **landed on `main`**, with its re-run proven at
  4 ranks;
- a memory instrument was calibrated. Its control proves the container's
  `memory.peak` cannot tell two runs apart.

This review also found and repaired a record defect: one landing commit had
silently deleted nine test-results rows. **Still a self-consistency story at
the Larmor frequencies:** no absolute SAR, no C95.3 figure, no homogeneity, no
Larmor coil accuracy, no resonance or tuning, no closed-form B₁⁺ claim, and no
solve on the human-scale mesh. `PROJECT_PLAN.md` is the source of truth; this
page is a read-only digest for the human operator.

## Waiting on you

1. 🔴 **The 02:00 XL window did not run. Decide what tonight's 02:00 does.**
   - **Evidence:** `git ls-files -s scripts/automation/xl-run.sh` reads mode
     `100644` (introduced by `b4fffa3`); the other four launchers are `755`.
     The script's first action is to create `logs/automation/*_xl-run.log`,
     and none has ever been written. `xl-queue.env` is still armed with
     `ANS-4-step2d`. `fem-em-solver-xl` has been up 17 h, never recreated,
     running nothing.
   - **Two traps before you flip the bit.**
     - A cron-launched window does **not** pass the 7-day interval gate. Only
       the Claude hook (`bash_guard.py`) reads the ledger, and
       `run_and_log.sh` just appends the row. Tonight (09-11) is past the
       override (`XL_OVERRIDE_UNTIL="2026-09-10"`), and the ledger's last XL
       row is 09-09. An executable script would therefore run an XL window
       that §5.1's rule says is not due, and no mechanism would stop it.
     - Sessions here cannot run `crontab -l` without a prompt, so nobody has
       confirmed the installed crontab even carries the 02:00 line.
   - **Options:**
     - **(a)** Authorise it: `chmod +x` plus
       `git update-index --chmod=+x scripts/automation/xl-run.sh`, re-date
       `xl-override.env` to cover 09-11, and check `crontab -l`.
     - **(b)** Empty `xl-queue.env` and hand step 2d back to the 09-13 weekly.

   Either way, stop the idle XL service. §9 item 5 and the plan's
   `OPS-43` (c) wiring (item 4) both wait on this.
2. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried, unchanged, still the
   highest-value AED item.)*
   - The spec reuses your `ANS-4` HFSS project, adding a phantom density and a
     field-calculator export
     (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`).
   - Pointwise SAR and phantom power are the adjudicating rows.
   - Our drive is 5 mW incident against HFSS's 1 W, and nothing is rescaled
     on either side.
3. 🟠 **`TH-11` step 5d's §2 sentence is the 09-13 weekly's.** *(Carried, no
   action.)* One correction landed this interval: §2.1 now says the
   263.4 GiB figure is a container-lifetime `memory.peak` spanning the killed
   first attempt, not that run's peak. `OPS-43` (c) has now *measured*
   `memory.peak` failing to separate two runs.
4. 🟡 **Agent-definition edits.** *(Carried.)* Five one-liners for
   `example-runner.md`, `mesh-probe.md` and `implementer.md`, plus
   `implementer.md`'s missing "Last verified against" footer. The foreground
   rule held on all four spawns again.
5. 🟢 **Model watch.** The review override (`claude-opus-5`) is dated through
   **2026-09-11**; the first 09-12 session falls back to Fable by itself. If
   the Fable credits are not back by then, move `REVIEW_MODEL_OVERRIDE_UNTIL`,
   otherwise the 09-12 03:00 review dies and drains three slots (09-08
   precedent).
6. 🟢 **`ANS-3` AED run** — behind item 2. Same low-order and private-results
   rules.
7. **Information:** the commit-first checkpoint in
   `docs/automation/weekly-review.md` (08-30) still awaits your OK.
8. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12;
   `scripts/probes/post4_step5_probe.py` regenerates.)

## Honest current state (digest of §2 — **one caveat added; no capability claim moved**)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% (`TH-12` ✅) |
| Conductor model | 🟡 **the PEC-hole gap-volume fix is on `main`** (`TH-15` step 3b, `8d4cf58`) — additive `gap_cell_tags`, default **not** flipped | Re-run at `-n 4`: impedance module **31 passed, 479 s**, every gate at its unmoved band (mutual 0.939398, −6.06% vs 10%; negative control −98.26%). Padding module **12 passed / 1 failed, 540 s** — the first footered run in its history; the red is `PORT-1` 3b-xii's month-old 3.1% vs 2.5%, reproduced to six figures, filed in known-issues. **Ruled this review:** the flip stays off — both-halves halves `\|V\|` and leaves corrected `M` (0.929199) and `‖S−Sᵀ‖` (1.276737e-03) bit-identical, so it buys no gate. `TH-15` stays 🟡 on step 2's unitarity gate |
| Coil loading | ⚠️ eddy-current regime only; the 64 MHz bracket sentence is the weekly's | `MAT-6` ✅ Dodd–Deeds; `TH-11` step 5d bracket [−2.04%, −0.43%] overlaps the 10 / 30 MHz ones — memory figure now correctly caveated as unattributable |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; **self-consistency only**; ANS-4 AGREE at 10 MHz, inconclusive at 64/128 | `GEO-31` 🧪: the four sheets share support and boundary to ≤ 3e-14 m, but their interior cuts differ by 0.44–0.99 facet lengths **on every rung, ×1 included**. Next is `PORT-18`: on this fixture the sheet's normal is the drive direction, so the port reads a component N1curl leaves discontinuous, off a `'+'` side the cut chooses |
| B₁⁺ | 🧪 symmetry-gated at CG1; ladder on `main` 5.25% → 2.07% | unchanged; ×0.0095 rung stays out |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | unchanged; no absolute or compliance claim |
| Test-suite trust | ✅ **`OPS-44` retired the pinned-artifact red**; residual reds at `-n 2`: 4 deliberate/known | Plus the padding module's pre-existing red, now observable at `-n 4`. **Record repair:** `8d4cf58` landed a parked branch by path-checking out `test-results.md` and deleted nine rows (WF-6 ×3, OPS-42 ×2, GEO-31 ×3, OPS-44 ×1), all restored; the trap is now in the review rubric |

## Recent activity (2026-09-09 18:00 → 2026-09-10 03:00)

- **19:30:** `GEO-31` (mesh-probe, 144 s, 2 ranks, no solve) — **same patch,
  different cut**, at all four rungs. Equal facet counts do not imply a
  congruent cut: on the ×1 mesh, two of four sheets sit half a facet off
  their rotated image. That moves the question from the mesher to the port
  model.
- **21:00:** `OPS-44` ✅ (8 s) — the exempt-artifact pin now equals git's five
  tracked artifacts and an independent re-derivation. Audited **PASS** this
  review (log `:162`, `:208`, `:211–212`).
- **22:30:** `TH-15` step 3b — landed; both modules footered at 4 ranks.
  Hypothesis confirmed: they were rank-bound, not unfittable.
- **00:00:** `OPS-43` (c) — the instrument read **1.0020×** a known 0.5 GiB
  allocation. `memory.peak` read the same 24.18 GiB at all three sampling
  points, while summed `ru_maxrss` separated the two runs **2.56×**. The slot
  **correctly held back** wiring the helper into the module the 02:00 XL
  window was about to read. The item's own note had wrongly assumed every
  slot starts after 02:00.
- **02:00:** XL window — **did not start** (Waiting-on-you 1).
- **03:00 review (this one):**
  - one audit, PASS;
  - nine test-results rows restored;
  - one redundant branch deleted, four remain;
  - `PORT-18` opened;
  - `ANS-1` gains a same-commit pin rule so the artifact red cannot recur
    silently a third time;
  - the `-n 4` re-tier sweep **not** opened: the only other Status-124
    deferral already timed out at `-n 8`, so it would retire nothing.

## Automation health

- **Four of four implementer slots fired and did chunk work**, exit 0, no
  denials, wedges, orphans, or backgrounded windows. Tier labels were honest.
  The `TH-15` windows ran with 111 s and 50 s of headroom: heavy at 4 ranks,
  and a place to watch.
- **XL launcher broken since `b4fffa3`** (execute bit). The cron path also
  bypasses the 7-day gate — see Waiting-on-you 1. Referred to the 09-13
  weekly with ruling (6)'s XL questions.
- **New trap, paid for once:** landing a parked branch by path checkout of an
  append-only record deletes every row `main` added since. Now in the review
  rubric's trap list.
- Branches: 4 `attempt/*` (`TH-15-step2proper`, `WF-6-step4b/4c/4e`, kept on
  the 18:00 ruling), no `recovered/*`. Tree clean at review start.

## On deck (§9 — three takeable items; fewer than five, stated not padded)

1. **`PORT-18`** *(mesh-probe; no solve; 2 ranks + 1 rank, ≈ 3–4 min)* — do
   the four sheets read different mixes of lower-side and upper-side traces?
   Anchored on a partition identity and an exactly-representable field;
   arithmetic negative control ≥ 1.40.
2. **`OPS-43` (d) gate** *(implementer; smoke)* — the progress variable is
   bit-inert on the solution and prints only when set.
3. **`OPS-43` (b)** *(implementer; smoke)* — the harness refuses to start
   while ranks survive in the target service, and proceeds once they are
   gone.
4. 🚫 `OPS-43` (c) ladder wiring — blocked on the XL decision.
5. 🚫 `ANS-4` step 2d (`xl`) — blocked on Waiting-on-you 1.

A fourth slot, if it finds nothing takeable, stops and journals. That is the
rule, not a failure.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
