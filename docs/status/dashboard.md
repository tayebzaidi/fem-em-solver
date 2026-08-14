# FEM-EM Solver — status

**Updated:** 2026-08-13, 10:30 review (run interactively — the scheduled
slot died on an API 529; see Automation health). Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

0. 🔴 **The scheduled reviews are out of usage credits — the automation loop
   is half-dead, and the weekly review is ~1.4 days from dying too.**
   *(Added 2026-08-14 09:30Z by the 04:30 implementer slot, not by a review;
   updated by the 06:00, 07:30, 09:00, 12:00 and 13:30 slots — see their
   `docs/testing/attempts.md` entries.)* **Three** consecutive review slots
   (2026-08-13 18:00, 2026-08-14 03:00 and 10:30) each produced a **98-byte,
   byte-identical** log reading *"You're out of usage credits … Fable 5"* and
   ran no steps; the 2026-08-13 10:30 slot died separately on a 529. Three
   identical failures across two days ⇒ this is a standing balance problem,
   not a transient. The implementer pool (Opus) is unaffected and still runs
   — so the half of the loop that *consumes* §9 On-deck items is alive while
   the half that *refills* it is silent. Consequence: the queue drained at
   21:00 on 08-13 and **nine implementer slots have now idled consecutively
   (75 % of the day's twelve)**, none to a technical blocker. The next
   review event is 18:00 local, so **15:00 and 16:30 are already
   determined to idle as well** (11 by 16:30); 19:30 is the next slot whose
   outcome is still open. **Also at risk: the 2026-08-16 01:30 weekly
   planning review**, on the same model — it alone owns the `PORT-1` 3b
   branch-landing adjudication, the §10 roadmap and §5.4 Ansys
   commissioning. **Unblock:** restore Fable 5 credits, or repoint the three
   `scripts/automation/*.sh` launchers at a model with balance. A scheduled
   session can do neither — it cannot buy credits, and
   `.claude/settings.json` denies headless edits to `scripts/automation/**`
   (the same rule that blocked `OPS-16`). Note `OPS-16`'s retry-on-529 would
   **not** have saved any of these three slots.
1. **One click: does ParaView open a DG1 `.bp`?** (unchanged since the
   2026-08-12 18:00 review). `POST-4` step 5 measured the DG1/VTX export
   route bit-faithful (round-trip exactly 0.0) where the current P1 path is
   20–52% off pointwise; cost is 10.5× disk, zero wall clock. Adoption is
   blocked only on you opening a `.bp` in ParaView (ADIOS2/VTX reader) and
   confirming it renders — each field arrives as `<name>_real` /
   `<name>_imag`. `scripts/probes/post4_step5_probe.py` regenerates the
   files.
2. **ANS-1 Ansys replication** — the FEM half is complete
   (`examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/`, `SPEC.md`
   box 1 checked); the AED run is yours. Our ΔX is genuinely unconverged,
   so the AED number is informative, not a formality.
3. Housekeeping: local `main` is **~45 commits ahead** of `origin/main`
   (`b6e994f`, 2026-08-10) — push when convenient; every "in CI" claim is
   a local reproduction until then.

## Honest current state (digest of §2 — two rows moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; the < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; **Larmor-regime sphere now gated: 3.64% (64 MHz) / 1.83% (128 MHz) + ½∫σ\|E\|² to 3.63% — TH-10 closed ✅ this review** |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.88% on the combined fixture (MAT-6); **coil-at-Larmor is the remaining extrapolation → TH-11 commissioned** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4) + the Larmor power integral (TH-10); never on a coil |
| S-parameters | 🟡 test path real, package path heuristic | port-pair gate green at the unmoved 10% (3b-xviii, systematics named); **PORT-1 step 4 (package path) is queue item 1** |

## Recent activity (03:00 → 10:30 interval)

Five slots, five landings; all audited §4-compliant (one subagent auditor
per landing), no demotions:

- **TH-10 closed ✅** — the interior field gated against the Mie series at
  both Larmor frequencies and the SAR-relevant power integral at 64 MHz;
  the quasi-static route misses by 58%, so the gate measures genuinely
  full-wave physics. §2.1's long-standing extrapolation caveat narrows to
  coil-at-Larmor only.
- **EX-18** — first ports example (`ports:` runner group); the correction
  ladder now has a single source in `ports/systematics.py`, asserted
  bit-identical to the gate module.
- **MAG-13 rung 3** — the < 5% wire target reached by brute force (3.74%,
  1.52 M cells, 423 s); rung 2's near-wire error-map pattern refuted as
  mesh-realization noise and the §2 bullet corrected.
- New chunks from the findings: **TH-11** (coil loading across the
  eddy→displacement transition), **GEO-14** (the shared ~3% geometry-floor
  discriminator), **EX-19** (Larmor sphere example, §5.4 ramp), **OPS-16**
  (retry-on-529 in the launchers, spare).

## Automation health

- **The 10:30 review slot died on an API 529** (empty log, exit 1; an
  interactive relaunch attempt hit the same). This review was then run
  interactively at the operator's direction, ~6.5 h late — the drained
  queue was restocked before any implementer slot idled, so the outage
  cost zero slots. `OPS-16` (one guarded retry in the launchers) is queued
  to absorb this class in future.
- **Since that review, three more review slots died — all on exhausted Fable 5
  credits, not 529s** (2026-08-13 18:00, 2026-08-14 03:00 and 10:30; 98-byte
  logs, byte-identical, no steps run). §9 has therefore not been restocked
  since 2026-08-13 10:30, and the implementer slots at 21:00, 22:30, 00:00,
  04:30, 06:00, 07:30, 09:00, 12:00 and 13:30 all met a drained queue and
  stopped per §9's drain instruction — nine consecutive, three quarters of the
  day's capacity. See Waiting-on-you item 0 — this
  is the live blocker. **The 2026-08-16 01:30 weekly planning review is on the
  same model** (`weekly-review.sh:32` → `claude-fable-5`), so an unrestored
  balance also kills the owner of the `PORT-1` 3b branch-landing adjudication,
  the §10 roadmap and §5.4 Ansys commissioning. *(Line added by the
  2026-08-14 04:30 implementer slot and updated by the 06:00, 07:30, 09:00,
  12:00 and 13:30 ones; the rest of this section is the 10:30 review's.)*
- Grid otherwise clean: nine consecutive landing slots across the last two
  intervals; tree clean; no `attempt/*` or `recovered/*` branches — the
  three PORT-1 lineage branches were landed and deleted 2026-08-13.
- Standing weekly-review items (2026-08-16): the two-systematics
  composition question (3b-xviii), MAG-13 CG1 gate adoption, MAT-6
  step 10's ≥ 5.1× solve anomaly (memory-headroom lead), POST-4 export
  adoption (pending your ParaView check), and the birdcage-ports/B1+
  hold.

## On deck (§9, rebuilt this review; items mutually independent)

1. **PORT-1 step 4** — the package path reads the solved field: retire the
   `excitation.py` heuristic on the two-torus fixture. The §10 subgoal-2
   critical path; §2's "every packaged S-parameter is a heuristic"
   sentence falls only when this lands.
2. **EX-19** — Larmor lossy-sphere example, both frequencies, gate digits
   reproduced through the example path.
3. **GEO-14 step 1** — one-command discriminator: is the ~3% residual a
   geometry floor or resolution?
4. **TH-11 step 1** — coil loading at 64 MHz, cost/feasibility probe,
   measurement only, stop rule 300 s/solve.
5. *(spare)* **OPS-16** — retry-on-529 in the automation launchers.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
