# FEM-EM Solver — status

**Updated:** 2026-08-30 10:30, **daily review (scheduled, ran normally)**.
Headline: **the overnight physics landed — `WF-6`'s two measurement legs
settled the 8.65% miss as the DG0 estimator floor (CG1 reads ~2%), and
`TH-13` step 1 returned a clean negative — but the 02:15 weekly review
died before committing and cost the day: five implementer slots and two
review slots stopped on a drained queue.** Its output was recovered from
`recovered/2026-08-30T1100Z` and landed by this review (the archive
rotation verified lossless, the `ANS-4` spec, four known-issues rulings);
what it never wrote — its §7 chunk entries and its §10 pass — this review
wrote where the rulings fully specify them, and flagged where they do not.
§9 is refilled with **six independent items**, three of which retire a
deliberate red on `main`. Nothing in §2 moved. What this does **not**
say: no B₁⁺ homogeneity/CV number, nothing compared against an external
reference at 64/128 MHz, nothing tuned or resonant, no SAR on a coil.
Source of truth is `PROJECT_PLAN.md`; this page is a read-only digest for
the human operator.

## Waiting on you

1. **Information — automation fix applied, please confirm you accept it:**
   `docs/automation/weekly-review.md` now has a **commit-first checkpoint**
   (rotation committed on its own before plan edits; step outputs committed
   as they complete). The 02:15 session wrote ~10 000 lines across seven
   files and died before its one commit; four implementer entries traced
   the outage to that and asked for this. Revert the paragraph if you
   want the single-commit form back. The second suggestion in those
   entries — letting a drained-queue slot re-run a known-red gate — was
   **not** adopted (the drain rule exists so slots cannot invent work).
2. 🟢 **`ANS-4`, the loaded birdcage 4-port S-matrix at 10 / 64 /
   128 MHz — `SPEC.md` is ready for you:**
   `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/SPEC.md`.
   The first independent absolute check of the coil-fed port model at a
   Larmor frequency (everything gated so far at 64/128 MHz is a
   self-consistency identity), on the fixture B1+/SAR are computed on.
   **Ranks above `ANS-1`/`ANS-3` in your AED queue.** Two AED runs per the
   `ANS-5` ruling — Zero Order (matched) and the default First Order —
   and please confirm the unknowns-per-tet figure AED prints. Our
   runnable half is §9 item 4 (queued today); the spec does not wait on it.
3. **`ANS-5` ruled (2026-08-30 weekly review):** AED at **Zero Order**
   (= our production `degree 1`) as the adjudication column **and** at its
   default **First Order** as an order-sensitivity column; Mixed Order
   forbidden; our side stays at one order. `ANS-1` is in scope for the
   spec line. If you have **already** run `ANS-1` or `ANS-3` at an
   unrecorded order, say which — the numbers stand as an "order-unknown"
   column. Spec wording is §9 item 5 (documentary).
4. 🟢 **`ANS-3` and `ANS-1` AED runs** — still yours, behind `ANS-4`
   (unchanged since 08-16 / 08-09; no AED number has come back for either
   in three weeks, and until one does no benchmark has been adjudicated).
5. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
6. FYI, no action — **two weekly-review deliverables were lost with the
   02:15 session and are owed by the 2026-09-06 weekly review:** the
   `GEO-25` (F-human cost probe) and `PORT-13` (Phase-6 ring-rung solve
   probe) rulings — stub rows only in §7, not queueable — and the §10
   pass, including your 08-25 `N ≤ 25` / 30 cm-coil directive's
   disposition, which §10 still marks "FOR THE 2026-08-30 WEEKLY REVIEW".
   The docker-socket denial (08-29 13:30) has not recurred. Local `main`
   remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11; the sibling sampled band validated by measurement (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; every Dodd–Deeds module green on 0.11 with version-tagged cell counts (`OPS-27` ✅) |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26; `EX-34` ✅ 08-28) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only.** Every gated birdcage digit reproduces at `-n 2` and `-n 12` (`GEO-24` ✅). The two-torus gap-route record is a `-n 2` statement: `PORT-12` step 2 (ruled: keep the 1e-4 record, bound the parallel drift at 3e-4, lumped route flat to 2e-9 asserted) is §9 item 2; absolute accuracy at Larmor is `ANS-4` |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated at any rank width | `GEO-18`/`19`/`20`/`24` ✅; the production high-pass layout (16 legs, 32 ring sheets, 265 621 cells) is an example (`mesh:9`, `EX-35` ✅); no solve exists on it yet (`PORT-13`, ruling owed) |
| B₁⁺ / coil-driven SAR | 🧪 computed, not gated | `WF-6` step 1: `\|B₁⁺\|` on the loaded F-small birdcage at 10 MHz, mean 2.08e-8 T at 1 V; power accounting 9.80e-3 (band 1e-2) ✅; C4 covariance **8.65% vs 5% ❌ at DG0** — steps 1b/1c measured it as the DG0 cell-scatter floor (CG1 2.19 / 2.11 / 1.89% at +90 / −90 / 180°; ring set does not move it); gate (ii) re-registered on CG1 = §9 item 1; `MAT-4`'s coil route follows it |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ✅ census complete (452/478 observed on 0.11); **residual reds on `main` at `-n 2`: 5, two of them pre-registered physics gates held red on purpose** — 2 placeholder-route names (entry 3, `PORT-0/1`), `test_birdcage_volumes_partition_the_box` (`GEO-21`'s floor entry), `WF-6` gate (ii) (retires with §9 item 1), `TH-13` step 1's precondition (retires with item 3). At `-n > 2` only: the two-torus `PORT-12` drift (retires with item 2) | example-artifact census `dead=53 exit=1` since the 08-28 rename — `EX-36`, §9 item 6 + drain fallback |

## Recent activity (2026-08-29 18:00 → 2026-08-30 10:30)

- **19:30:** `WF-6` step 1b — CG1-projected `B` on the 51 centroids: DG0
  8.6516 / 9.5808 / 8.5970% vs CG1 **2.1870 / 2.1146 / 1.8911%** at
  +90 / −90 / 180°, control 23.26%, records reproduced. Verdict **(a),
  estimator floor**. 98 s. No band moved.
- **21:00:** `TH-13` step 1 — loop drive at 10 MHz, degrees 1 / 2:
  precondition **1.952350e-02 vs 1e-2 ❌**, move 5.156e+01× (in-between),
  both step-3 controls to the digit. CLASS was unreachable from that
  baseline (ω² arithmetic); rescope to 1 MHz is §9 item 3. 36 s. Chunk
  ⬜ → 🧪, one deliberate red.
- **22:30:** `WF-6` step 1c — 96-point rotation-invariant ring set at DG0:
  9.9271 / 9.9519 / 8.4706%, every angle within ±2 pp of the centroid set;
  **the sample set is not the mechanism**. 97 s. No band moved.
- **00:00 → 09:00:** five slots stopped — 00:00 on the drained queue (as
  designed); 04:30 on a dirty tree (first encounter, journaled); 06:00
  parked it on `recovered/2026-08-30T1100Z` and stopped on the queue;
  07:30 and 09:00 on the queue. No compute in any of them.
- **02:15 weekly review:** wrote the archive rotation, `ANS-4`'s spec, the
  `WF-6` 1d / `PORT-12` step 2 / `GEO-21` / `EX-30` rulings and the
  dashboard, then **died before committing**; no §7 chunk entries, no §10
  pass. The 03:00 daily review left no commit.
- **10:30 review:** landed the recovered branch (merge `dc1af52`, lossless
  rotation verified), deleted it, wrote the six §7 entries the rulings
  specify, stubbed `GEO-25` / `PORT-13`, added the weekly-review
  checkpoint, refilled §9 with six independent items.

## Automation health

- Three of eight scheduled slots did chunk work (all three landed, 231 s
  of recorded compute, 3 harness logs); five stopped correctly with clean
  trees and journals; zero wedges, zero exit-124 windows. Container Up 3+
  days.
- One `recovered/*` branch this interval, **landed and deleted**; zero
  `attempt/*`; tree clean at review time.
- Root cause of the lost day is upstream and fixed in the protocol
  (Waiting-on-you item 1). The 03:00 daily review's no-commit is
  consistent with finding the dirty tree and declining to write over it —
  protocol step 2 now makes that review the actor that clears it, which
  is what this one did.
- Queue holds **six independent items** (five ready + spare) with a
  pre-authorised `EX-36` fallback for the drain, so the 12:00 / 13:30 /
  15:00 / 16:30 slots all have work regardless of each other's result.

## On deck (§9 — six independent items this review)

1. **`WF-6` step 1d** — gate (ii) re-registered on the CG1 estimator at
   three angles, 5% band unchanged; `post/faraday.py` gains the projection;
   retires a deliberate red (standard, complex, ≈ 100 s + two example
   re-runs)
2. **`PORT-12` step 2** — `-n 2` record kept, `PARALLEL_DRIFT_ENVELOPE =
   3e-4` at `-n > 2`, lumped-route flatness asserted at 1e-8; retires the
   `-n > 2` red (smoke, complex, ≈ 260 s over three windows)
3. **`TH-13` step 1′** — the loop discriminator at 1 MHz where both bands
   are representable; retires a deliberate red (standard, complex, ≤ 60 s)
4. **`ANS-4` runnable half** — `ans:4`, the 4×4 at 10 / 64 / 128 MHz via
   the `ports:5` path, `COMPARISON.md` with two blank AED columns (heavy by
   `-t 500`, ≈ 160 s)
5. **`ANS-5` steps 1–2** — the element-order ruling written into every
   spec, README and comparison table (documentary, no compute)
6. *(spare)* **`EX-36` leg (th)** — re-run the eight `time_harmonic`
   examples so the census stops reading `dead` for that group (≈ 105 s);
   legs (mesh) / (root) / (ports) are the pre-authorised drain fallback

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
