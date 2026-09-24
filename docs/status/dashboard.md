# FEM-EM Solver — status

**Updated:** 2026-09-23 03:00 daily review (Wednesday). Headline: **Monday's
four slots emptied the queue — twelve items landed, including the first
*gated* human-scale result (`WF-7` step 1: the F-human 32×32's reciprocity,
passivity and 18 symmetry classes, all inside their bands) and six ✅ closures
from the external code review; all eight new ✅s audited PASS (one auditor
DEMOTE overruled with the log line).** Your image rebuild worked: last night's
XL window ran the `scikit-rf` test green on the new image with DolfinX and the
mesh records unchanged; the 04:30 slot closes `OPS-60` on the ordinary
service and then starts the `scikit-rf` circuit layer (`PORT-23`). The two
XL nights read the 64 MHz degree-2 *h*-ladder (converging, one class
ambiguous) and showed the 10 MHz near-band C4 spread was the uncut port
sheets, not the physics. Six items queued, 230 of the 240-minute floor.

**Still a self-consistency story at the Larmor frequencies for degree-1
figures:** the order-matched 4×4 is externally checked at 128 MHz (AGREE
stands); **at 64 MHz and 10 MHz it disagrees on the self class (`S₁₁`) while
agreeing on the couplings — no absolute `S₁₁` / `Z_in` claim at 10 or 64 MHz**
(known-issues 2026-09-19, `PORT-21`). "Tuned" means series resonance on one
F-small fixture. No C95.3 figure, no homogeneity, no closed-form B₁⁺ claim, no
absolute S on a copper coil. `PROJECT_PLAN.md` is the source of truth; this
page is a read-only digest for the human operator.

## Waiting on you

1. ✅ **Privacy — resolved 2026-09-24 (operator):** relative agreement
   levels against AED are publishable; the Privacy clause in `CLAUDE.md`
   and `weekly-review.md` now says so. The four flagged places stand as
   written; raw AED values stay private. Drop this item at the next review.
2. 🟠 **Re-run `scripts/testing/install_git_hooks.sh` once** *(carried from
   `OPS-58` ✅)* — `.git/hooks` is untracked and not agent-writable; this adds
   the `commit-msg` hook beside `pre-commit`.
3. 🟠 **`ans:3` needs one interactive re-run** *(carried)* — its tracked
   `metrics.json` / `COMPARISON.md` still show the pre-`PORT-20` S table; the
   script rewrites the gitignored private comparison, so no slot may run it.
   Also: **CLAUDE.md's "two external findings stand open" sentence still
   names `PORT-20`**, which is closed.
4. 🟠 **`ANS-6` adjudication is the 09-26 weekly's** *(carried)*. On our
   side: a resolution knob for `ans:6` is queued (item 35) and, once it lands,
   an XL cost probe of the matched hole-mesh rung (h = 0.005, degree 2) is
   pre-registered (`xl-pending.md` entry 14). Still no private-mode comparison
   writer for this example — say if you want one.
5. 🟠 **`GEO-34` (STEP import) is queued, with one substitution you may want
   to overrule.** Step 1 is split into 1a (STEP round trip + config group map,
   mesh-level gates — item 37), 1b (the four-port gates on the imported mesh)
   and 1c (an independent CAD emitter). CadQuery / build123d are **not in the
   image**, so 1a writes the STEP with Gmsh's own OCC writer: it exercises the
   STEP reader and the group map but not an independent CAD kernel. If you
   want 1c, add one of them to `docker/Dockerfile` and rebuild.
6. 🟠 **For the 09-26 weekly** *(information)*: `OPS-61` (Palace) to
   commission; `TH-17`'s gate "mode 1 at 64 MHz" may be mis-posed (the eigen
   solve terminates all four ports, the driven sweep one); **human-scale step
   H6 conflicts with your 09-20 strip-conductor note on `GEO-33`** (the chain
   says a round-tube cost rung; the note says the 32-leg rung should carry
   zero-thickness strips) — not queued until reconciled; feature-ladder B1
   (`TH-5`, radiation boundary) was never queued and now has its skip reason
   recorded.
7. 🟡 **`example-runner` should not be able to spawn agents, and its "no
   deviations" is not evidence.** *(Carried.)* The durable fix is in
   `.claude/agents/example-runner.md` (not writable from scheduled reviews).
8. 🟡 **Two figure-style choices are yours.** *(Carried.)* Legends collapse
   more than two same-colour entries to `first … last`, and one colour per
   region class cannot show a split between two same-class regions.
9. 🟡 **XL nights cannot prove "no orphans".** Every ledger row since 09-20
   reads "orphans: not established": the `ANS-4` commands carry no count and
   `xl-run.sh` does no post-window check. A one-line count in the launcher
   would make it uniform. Not queued — no status rides on it; flagged to the
   weekly.
10. 🟡 **XL / XXL windows ahead — information only.** Thu 09-24 `ANS-4` 3g
    (10 MHz four-rung ladder); Fri 09-25 `ANS-2` step 4 (phantom h-halving);
    Sat 09-26 XXL `WF-7` 0d (human-scale 32 ports at degree 2); Sun 09-27 3h
    and Mon 09-28 3i (the 10 and 64 MHz ladders on the symmetric port cut).
    Every night finds five charged rows in its own trailing week.
11. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
    `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
12. **Information:** the commit-first checkpoint in
    `docs/automation/weekly-review.md` (08-30) still awaits your OK.
13. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12.)
    `scripts/probes/post4_step5_probe.py` writes the `.bp`, reads it back
    exactly and ends `PROBE_RESULT PASS`.

Nothing is blocked on you today. Claude connectors for Gmail, Microsoft 365
and PubMed are unauthorised in this headless session; nothing here needs them.

## Honest current state (digest of §2 — §2 unchanged since 09-20; rows refreshed from §7)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅) — production order: target degree 2, default not flipped, decided 09-26 on the 3e / 3g ladders |
| Conductor model | ✅ two routes gated (`TH-14` ✅): the birdcage as a PEC hole and copper as a Leontovich surface | one loop, one liftoff, 10 MHz for the floor; no absolute S on a copper coil — `ANS-6` both halves landed, adjudication 09-26 |
| Coil loading | 🟡 measured flat in f across 10–64 MHz on one XL window — a record, not a gate | `MAT-6` ✅ Dodd–Deeds at 10 MHz; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; order-matched 4×4 externally checked: AGREE at 128 MHz; at 64 and 10 MHz couplings AGREE, **self class `S₁₁` DISAGREE, open** (`PORT-21` step 1 table on `main`); 64 MHz degree-2 *h*-ladder converging (ratios 1.88 / 1.92 / 1.64, one class ambiguous — the weekly rules); two-torus current route reports `S = z_to_s(Z)` (`PORT-20` ✅) | **no absolute `S₁₁` / `Z_in` at 10 or 64 MHz at either order**; `ans:3`'s tracked tables still pre-fix (Waiting-on-you 3) |
| Lumped RLC / circuit layer | ✅ `PORT-14`, `PORT-15`, `PORT-22` (circuit reduction = in-model tuned `S₁₁` to ≤ 8.3e-5, 44–84 MHz); `EX-61` ✅ plots the resonance curve | series resonance on one fixture, not matched; `scikit-rf` engine (`PORT-23`) queued behind `OPS-60`'s closure (items 33–34) |
| Multi-port drive | ✅ `POST-6` — 32-port ccw quadrature C16-invariant (0.81 %) | 10 MHz only; the human-scale version is item 36 |
| B₁⁺ | ✅ `WF-6` — two-rung convergence statement (5.25 % → 2.07 %) | a convergence statement only |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`); externally checked — `ANS-2` adjudicated AGREE, numbers private | no compliance claim; one fixture, 10 MHz; the phantom h-halving is an `xl` window, 09-25 |
| Human-scale mesh | 🟡 **identities gated** (`WF-7` step 1, 09-21): F-human 32×32 at 64 MHz, degree 1 — reciprocity 9.2e-15, σ_max 0.99991, 18 symmetry classes worst 3.70 % (band 5 %), exact power identity ≤ 2.8e-15 on 4 drives | no field, B₁⁺ or SAR yet (`|B₁⁺|` is item 36); degree 1 carries a 5.5 % order caveat; degree-2 32-port price 09-26 |
| Examples | **56 runnable**, census clean; **25 of 56 guides have a setup figure** (`EX-57`, recurring; 31 owed) | the figure helper refuses an over-long title (`OPS-53` ✅) |
| Test-suite trust | ✅ the external-review rows closed (`OPS-55` / `-56` / `-57` / `-58` / `-59` / `-62`, `OPS-50`); known reds: known-issues entry 3's two port tests, the padding module, and `OPS-60`'s deliberate red (item 33 retires it) | the `B` projection is not run-to-run reproducible below ≈ 4e-6 (no gate reads it) |

## Recent activity (2026-09-21 03:00 → 2026-09-23 03:00; Tuesday off)

- **Mon 04:30 slot:** `OPS-60` pin (→ 🟡); **`WF-7` step 1 🧪 → 🟡**;
  `PORT-21` step 1 on `main` (the symmetric-cut variant inside its band);
  `ANS-6` degree knob + first degree-2 price on the hole mesh.
- **Mon 06:00 slot:** `TH-17` step 1c green (the eigen pencil reproduces an
  LC loop's closed form to 2 %); **`OPS-59`, `OPS-50`, `OPS-55`, `OPS-56`,
  `OPS-57` ✅**.
- **Mon 07:30 slot:** `OPS-58` stopped on its pre-registered audit hit (you
  ruled it that evening); **`EX-61` ✅**; `EX-57` `mesh:9`.
- **Mon 09:00 slot:** queue drained ⇒ `EX-57` `mesh:10` fallback.
- **Your sessions:** `OPS-58` ✅ (allowlist); `OPS-62` ✅ (ladder guard);
  image rebuild; Opus 5.5 for implementers and this review.
- **`xl` 09-22:** `ANS-4` 3e — every gate green, Status 1 on two non-physics
  reds only. **`xl` 09-23:** 3f — 18 / 18, first window on the new image.
- **03:00 review (this one):** eight audits (seven PASS, one DEMOTE
  overruled); two XL ledger rows filled; 3e not re-run; three XL entries
  written (two queued, one pending); six items written. Journal:
  `docs/planning/reviews/2026-09-23-daily.md`.

## Automation health

- **Implementer slots: 4 of 4 fired Monday; 14 items attempted, 12 landed,
  1 parked for you (since resolved), 1 fallback figure.** No window died, no
  masked status, no dirty tree. Take-next carried the 06:00 slot through
  six items.
- **Reviews:** this one ran on `claude-opus-5-5` (the daily override through
  09-29). Thursday is off; next daily Friday 09-25 03:00, weekly Saturday
  09-26 21:00.
- **XL: 6 of 6 windows used in the trailing 7 days as of today (each queued
  night counts 5 at its own cutoff), 4 entries ahead (floor 4) — met.**
  **XXL: 1 ahead (09-26, floor 1) — met.** Entry 14 waits on item 35.
- **Docker socket:** the 09-22 evening denial was specific to that sandboxed
  session; this review and last night's XL window both reached the
  container.
- **Tree:** clean. **Branches:** 5 `attempt/*` (4 kept on the 09-09 ruling;
  `attempt/OPS-50-…` kept because its tip is the `OPS-50` control's pinned
  sha). No `recovered/*`.
- **§9 size:** 45.8 KB against a ~25 KB target (59.3 KB before) — six
  full-rubric items are ~24 KB on their own (journal §7).

## On deck (§9 — six items, 230 predicted slot-minutes; floor 240: short 10 min; ≥ 5 items: met)

33. ~~**`OPS-60`**~~ **DONE 04:30 slot — `OPS-60` ✅**: `skrf=2.1.0` green on
    the ordinary service, no recreate needed; your rebuild is fully landed.
34. ~~**`PORT-23` step 1**~~ **DONE 04:30 slot** — the `scikit-rf` circuit
    layer matches the raw reduction to machine precision; step 2 open.
35. ~~**`ANS-6` step 2b**~~ **DONE 04:30 slot** — resolution knob landed;
    XL entry 14 (hole-mesh probe) is READY for the next review to queue.
36. ~~**`WF-7` step 2**~~ **DONE 04:30 slot** — human-scale `|B₁⁺|` is
    C16-symmetric to 0.15 % (5 % band); H5 (hotspot) becomes queueable.
37. **`GEO-34` step 1a** *(standard)* — STEP round trip of the F-small
    birdcage through a config-driven importer, mesh-level gates.
38. **`EX-57` figure** — `meshing/11_birdcage_sixteen_ring_sheet_longitudinal.py`.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
