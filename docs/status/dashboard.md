# FEM-EM Solver — status

**Updated:** 2026-08-25 03:00, **daily review (scheduled, ran normally)**.
Headline: **a fully green interval — all four slots closed on `main`,
the first time that has happened since the 0.11 merge.** The birdcage
port geometry (`GEO-19` step B) landed with the open-limit retirement,
both pieces of 0.11 migration debt are fixed (the silently dead `TH-9`
cavity gate is executing again and reproduces its record to the printed
digit; `th:7` is re-joined to its gate by hoist), and the whole
`time_harmonic` example family is green with its stale census at zero.
All four closures were independently audited §4-COMPLIANT — exactly two
assertions removed across the interval, both licensed by ruling (6\*),
zero bands moved. `PORT-9`'s last leg ((d1′)) and `GEO-19`'s last step
(the 16-leg cost rung) are now both unblocked and queued 1–2. Source of
truth is `PROJECT_PLAN.md`; this page is a read-only digest for the
human operator.

## Waiting on you

1. 🟡 **A geometry decision is coming your way: 32 legs do not fit
   `ring_radius = 0.07 m` with 14 mm port boxes.** The layout clearance
   floor caps the leg count at **N ≤ 25**; 32 legs need
   `ring_radius ≥ 0.0876 m` or narrower boxes. The weekly review owns
   §10 and will propose a disposition Sunday — if you have a preference
   (bigger ring vs narrower boxes vs 16 legs as the production count),
   leave it in the plan or say so.
2. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
3. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
4. **ANS-1 Ansys replication** — still yours; ANS-3 (item 2) is the
   second case in the same queue.
5. FYI: local `main` is well ahead of origin (push is manual). The
   128 GiB ceiling you raised is about to earn its keep: the 16-leg mesh
   cost rung (queue item 2) is the first heavy run under it. Re-pricing
   the `TH-12` degree-2 memory-wall negatives stays a weekly-review
   call, deliberately not queued.

## Honest current state (digest of §2 — two changes this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated on 0.11, dead gate **fixed** | closed forms; Helmholtz 0.04%; wire ladder re-gated 08-23; PEC-cavity **0.0436% executing again** (`OPS-24`, 08-25 — reproduces the pre-0.11 record to the printed digit, refinement rate 3.85) |
| Time-harmonic curl-curl | ✅ validated, example family fully re-gated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405%; all eight `th:` examples green on 0.11, census 0 |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; the 64 GiB "no affordable bracket" negatives are **unmeasured** since the 128 GiB raise, revival is a weekly-review call |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| S-parameters | ✅ field-derived; birdcage gates green on step B's mesh | records mesh-tagged at 116 085 (σ_max 0.999992805, class separation 166.7×, (d0) margin 2257×); open-limit `Z₁₁` retired as a record under (6\*); §2.2's "no coil has ports" stands until (d1′) — now queue item 1 |
| Test-suite trust | ✅ reconciled, on 0.11 | 437 collected / 0 errors both modes; the collect-clean ≠ executing lesson is banked (the cavity gate was dead for two days with a green-looking tree) |

## Recent activity (2026-08-24 18:00 → 08-25 03:00)

- **19:30:** `GEO-19` step B landed under ruling (6\*) — `6c1f54e`
  cherry-picked clean, open-limit column retired in the same commit,
  invariance `3 passed` from `main` and the three `PORT-9` modules
  `19 passed` twice with every pre-stated digit hit (116 085 cells at
  ratio 1.000000, leg (c)'s `I₁` reproducing to 5.9e-12). No band
  widened; both step-B attempt branches deleted.
- **21:00:** `OPS-24` closed — the dead cavity gate was a pure keyword
  rename (`diagonal=` → `diag=`), read off the installed signature, not
  assumed. Red reproduced first, then `13 passed` twice with every
  recorded figure to the printed digit (worst-mode 0.0436%, rate 3.85,
  guard 137.6 vs 22.0). Two source lines changed; known-issues entry
  retired.
- **22:30:** `OPS-25` closed — `th:7`'s private interpolation hoisted
  into the gate module; the moved code's only output reproduces
  **bit-identically to all ten printed digits**; `th:7` green in 14 s;
  the repo's `interpolate(cells=)` migration is now complete repo-wide.
- **00:00:** `EX-30` leg (th) closed — all eight `time_harmonic`
  examples green in 105 s total; the licensed 128 MHz record alignment
  executed and confirmed at ~2e-4 drift (the 18:00 review's
  documentation-only diagnosis held up under measurement); census
  51 → 47, derived, `time_harmonic` at zero. Three known-issues entries
  retired with their fixes.
- **This review:** all four closures audited §4-COMPLIANT (every log
  footer, every quoted digit, every diff checked for loosening); `EX-30`
  legs (root)/(mesh)/(ports) queued with the (1\*) example-record
  licences the re-scope required; (d1′) and step C promoted to items
  1–2; nothing demoted, no new known-issues entries.

## Automation health

- Four slots scheduled, **four ran, four closes** — no parks, no
  ruling-requests needed, no exit 124, no wedge, no `recovered/*`, tree
  clean at every handoff. One benign runner misfire (a Status-127
  docker-in-docker artifact on `OPS-25`'s first red attempt) was
  disclosed and re-run correctly within the slot.
- The 18:00 review's two splits (`OPS-24`/`OPS-25`) and one
  documentation-diagnosis (`th:6`) all resolved exactly as scoped —
  the diagnose-at-review, measure-at-slot division is working.
- Branches: `attempt/PORT-9-d1-20260823T124500Z` parked (item 1's
  payload, adjusted at landing per (6\*)(v));
  `attempt/GEO-19-20260823T214500Z` parked (item 2's payload).
- The queue holds **five items, all independent** — the first
  all-independent queue on record. Still unqueued by design:
  `PORT-11` step 1 (behind item 1), `GEO-20` step 2 (behind item 2).

## On deck (§9 — five open items this review)

1. **`PORT-9` leg (d1′)** — the geometric negative control on the
   power-wave route; closes `PORT-9` and ticks the §10 Phase-4 box at
   10 MHz (standard, independent)
2. **`GEO-19` step C** — the parked 16-leg gates module + Phase 6's
   first measured mesh cost, first heavy run under 128 GiB (heavy,
   independent)
3. **`EX-30` leg (root)** — repo-root + `mri:2` + `mat:1` example
   refresh, no re-record licence (standard, independent)
4. **`EX-30` leg (mesh)** — meshing examples, licensed cell-count
   re-records version-tagged from its own run (standard, independent)
5. **`EX-30` leg (ports)** — ports + `ans` examples, licensed
   (d3)-moved S-record re-records; closes `EX-30` if last to land
   (standard, independent; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
