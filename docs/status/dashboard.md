# FEM-EM Solver — status

**Updated:** 2026-09-25 03:00 daily review (Friday). Headline: **the
ordinary solver container had been down since ≈ 10:00 Wednesday. This
review found it, restarted it, and cleared the untracked XL output that
would have stopped both today's first slot and Saturday's XXL window.**
Two XL nights read: the phantom h-halving for the coil-driven SAR case
(`ANS-2`) came back in branch (a). The point-SAR symmetry scatter fell from
15.7 % to 4.5 % and the phantom power did not move, so the residual against
HFSS is the feed and the pointwise band tightens to 4.5 %. The 10 MHz
degree-2 ladder (`ANS-4` 3g) falls but has not converged on `S₁₁` (last
change 3.6 %), which the weekly rules on. Wednesday's slots landed the
`scikit-rf` circuit engine, the human-scale `|B₁⁺|` symmetry gate and the
STEP import round trip. Four items are queued (165 of the 240-minute floor);
the first is the human-scale 10 g SAR hotspot, which can close `WF-7`.

**Still a self-consistency story at the Larmor frequencies for degree-1
figures:** the order-matched 4×4 is externally checked at 128 MHz (AGREE
stands); **at 64 MHz and 10 MHz it disagrees on the self class (`S₁₁`) while
agreeing on the couplings — no absolute `S₁₁` / `Z_in` claim at 10 or 64 MHz**
(known-issues 2026-09-19, `PORT-21`). "Tuned" means series resonance on one
F-small fixture. No C95.3 figure, no homogeneity, no closed-form B₁⁺ claim, no
absolute S on a copper coil. `PROJECT_PLAN.md` is the source of truth; this
page is a read-only digest for the human operator.

## Waiting on you

1. 🟠 **An AED figure sits in tracked text: your call on history.** The
   `ans:2` example's docstring and one print line (since `a2e4a04`, 09-19)
   quote HFSS's own driven-point C4 spread. That is an AED value, not a
   relative agreement level. Last night's tracked XL log printed it again
   (`20260925T070008Z_ANS-2-step4.log:2113`). The source lines are queued
   for removal (`OPS-63`, item 41), and this review redacted the same figure
   from the plan's `ANS-2` row. The logs and history already committed need
   your decision. The number is quoted nowhere in this review.
2. 🟠 **The solver container died at ≈ 10:00 Wednesday, cause unknown**
   (`Exited (137)`, i.e. SIGKILL, typical of an OOM kill or a manual stop). No
   automation stops it. It is running again, and no known-issues entry was
   opened because the restart resolved it. If you know what happened (Docker
   Desktop, WSL, a manual stop), say so. Nothing was lost: Thursday was off.
3. 🟠 **Re-run `scripts/testing/install_git_hooks.sh` once** *(carried from
   `OPS-58` ✅)* — `.git/hooks` is untracked and agents cannot write it;
   the script adds the `commit-msg` hook beside `pre-commit`.
4. 🟠 **`ans:3` needs one interactive re-run** *(carried)* — its tracked
   `metrics.json` / `COMPARISON.md` still show the pre-`PORT-20` S table.
   Also: **CLAUDE.md's "two external findings stand open" sentence still
   names `PORT-20`**, which is closed.
5. 🟠 **`ANS-6` adjudication is Saturday's weekly** *(carried)*. The
   hole-mesh degree-2 cost probe runs Tue 09-29 (XL entry 14). There is
   still no private-mode comparison writer for this example; say if you
   want one.
6. 🟡 **`example-runner` must not spawn agents** *(carried; happened again
   09-23)*. On Wednesday a spawned runner started a background runner, which
   **resumed after the slot had committed**; the slot caught it. The rule
   now sits in §9, but the durable fix is `.claude/agents/example-runner.md`,
   which scheduled sessions cannot write.
7. 🟡 **`GEO-34` step 1c needs a CAD kernel in the image** *(carried)* —
   CadQuery / build123d in `docker/Dockerfile` plus a rebuild, if you want
   the independent-emitter check. Step 1b (the four-port gates on the
   imported mesh) is queued without it.
8. 🟡 **Leftover directory `.worktrees/census-before`** (09-23 slot):
   gitignored, partly root-owned. `sudo rm -rf` it when convenient.
9. 🟡 **For the 09-26 weekly** *(information)*: 3g's "falling but not
   converged" reading, which the pre-registered rule does not cover; the
   `ANS-2` band into the private file; no XXL window is pre-registered after
   Saturday's; H6 vs your strip-conductor note on `GEO-33`; B1 `TH-5`;
   `OPS-54`, `OPS-61`.
10. 🟡 **XL nights still cannot prove "no orphans" for the `ANS-4` windows**
    *(carried)*. The `ANS-2` / `ANS-6` commands count them; the ladder
    commands do not, and `xl-run.sh` does no post-window check.
11. 🟡 **Two figure-style choices are yours.** *(Carried.)* Legends collapse
    more than two same-colour entries to `first … last`, and one colour per
    region class cannot show a split between two same-class regions.
12. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
    `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
13. **Information:** the commit-first checkpoint in
    `docs/automation/weekly-review.md` (08-30) still awaits your OK. **One
    click:** does ParaView open a DG1 `.bp`? (since 2026-08-12;
    `scripts/probes/post4_step5_probe.py` writes it and ends `PROBE_RESULT PASS`.)

The privacy item from 09-23 is closed by your 09-24 ruling and dropped.
Claude connectors for Gmail, Microsoft 365 and PubMed are unauthorised in
this headless session; nothing here needs them.

## Honest current state (digest of §2 — §2 changed: the circuit layer names its engine)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅). Production order: target degree 2, decided by the weekly; 3g (10 MHz) not converged on `S₁₁` |
| Conductor model | ✅ two routes gated (`TH-14` ✅) | no absolute S on a copper coil. `ANS-6` adjudication 09-26; hole-mesh degree-2 probe 09-29 |
| Coil loading | 🟡 measured flat in f across 10–64 MHz on one XL window — a record, not a gate | `MAT-6` ✅ Dodd–Deeds at 10 MHz |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; order-matched 4×4: AGREE at 128 MHz; at 64 and 10 MHz couplings AGREE, **`S₁₁` DISAGREE, open**; degree-2 *h*-ladders: 64 MHz converging, **10 MHz falling but not converged on `S₁₁`** | **no absolute `S₁₁` / `Z_in` at 10 or 64 MHz** |
| Lumped RLC / circuit layer | ✅ `PORT-14`, `PORT-15`, `PORT-22`, `EX-61`; **`scikit-rf` 2.1.0 engine = raw reduction to ≤ 3.5e-16** (`PORT-23` step 1, `OPS-60` ✅) | series resonance on one fixture, not matched |
| Multi-port drive | ✅ `POST-6` — 32-port ccw quadrature C16-invariant | 10 MHz on the ring rung; human-scale version below |
| B₁⁺ | ✅ `WF-6` — two-rung convergence statement (5.25 % → 2.07 %) | a convergence statement only |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz (`MAT-4`); `ANS-2` AGREE, **phantom h-halving → branch (a): residual is the feed, pointwise band 10 % → 4.5 %** | no compliance claim; one fixture, 10 MHz |
| Human-scale | 🟡 **identities + `|B₁⁺|` C16 gated** (`WF-7` steps 1–2): 32×32 reciprocity 9.2e-15, 18 classes ≤ 3.70 %; ccw `|B₁⁺|` C16 0.15 %, mirror 0.16 % | the 10 g hotspot is item 39; degree 1 carries a 5.5 % order caveat; degree-2 32-port price 09-26 (XXL) |
| CAD input | 🟡 STEP round trip of F-small through a config group map, mesh gates green (`GEO-34` 1a) | four-port gates on the import are item 40; no independent CAD kernel |
| Examples | **56 runnable**, census clean; **29 of 56 guides have a setup figure** (`EX-57`; 27 owed) | — |
| Test-suite trust | ✅ external-review rows closed; known reds: known-issues entry 3's two port tests, the padding module; **new: the `ans:2` example's mislabelled ASSERTED lines** (`OPS-63`) | the `B` projection is not run-to-run reproducible below ≈ 4e-6 (no gate reads it) |

## Recent activity (2026-09-23 03:00 → 2026-09-25 03:00; Thursday off)

- **Wed 04:30 slot:** `OPS-60` ✅; `PORT-23` step 1 (the `scikit-rf`
  engine); `ANS-6` resolution knob; `WF-7` step 2 (human-scale `|B₁⁺|`).
- **Wed 06:00 slot:** `GEO-34` step 1a (STEP import); `EX-57` `mesh:11`,
  `mesh:12`.
- **Wed 07:30 / 09:00 slots:** queue drained ⇒ `EX-57` `mat:1`, `mat:2`.
- **≈ Wed 10:00:** solver container exited (found and restarted 09-25).
- **XL Thu:** `ANS-4` 3g, 18 / 18, 2084 s. **XL Fri:** `ANS-2` step 4, rc 0,
  1315 s, 39.9 GiB.
- **Your sessions:** the privacy ruling; `weekly_counts.py` tokens.
- **03:00 review (this one):** one audit (DEMOTE on a tier word, overruled);
  two XL rows read and ruled; two XL entries queued (one written); `OPS-63`
  opened; four items written. Journal:
  `docs/planning/reviews/2026-09-25-daily.md`.

## Automation health

- **Implementer slots: 4 of 4 fired Wednesday.** Six items and four
  fallback figures landed; nothing parked; one executor-nesting breach,
  caught.
- **Service outage:** the ordinary container was down ≈ 41 h (mostly the
  off day); restarted 03:03 local.
- **Reviews:** this one ran on `claude-opus-5-5` (the daily override
  through 09-29). Next daily Sat 09-26 03:00; weekly Sat 09-26 21:00.
- **XL: 6 of 6 windows used in the trailing 7 days, 4 entries ahead
  (floor 4) — met.** **XXL: 1 ahead (09-26), floor 1 — met;** nothing
  after it.
- **Tree:** clean after this commit. The untracked XL output was moved into
  the gitignored `paraview_output/`: committing it would break the artifact
  pin.
  **Branches:** five `attempt/*` kept; no `recovered/*`.
- **§9 size:** 39.3 KB against a ~25 KB target (48.0 KB before).

## On deck (§9 — four items, 165 predicted slot-minutes; floor 240: short 75 min; ≥ 5 items: short one)

39. **`WF-7` step 3** *(heavy)* — the 10 g SAR hotspot on the human-scale
    birdcage (refined phantom), C16- and mirror-gated; can close `WF-7`.
40. **`GEO-34` step 1b** *(standard)* — the four-port gates at 10 MHz on the
    STEP-imported mesh.
41. **`OPS-63`** *(heavy)* — the `ans:2` example asserts what it says it
    asserts; the AED figure leaves its source.
42. **`EX-57` figure** — `time_harmonic/01_lossy_plane_wave.py`.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
