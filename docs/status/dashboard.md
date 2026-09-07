# FEM-EM Solver — status

**Updated:** 2026-09-07 03:00 daily review. Headline: **the C95.3 10 g
mass-averaging operator is gated on the coil-driven field (`MAT-4` ✅),
the 1% power-accounting gap on the 4-leg fixture is attributed to the
digit (it is the terminal form's own Cauchy–Schwarz deficit, not a leak),
and a PEC hole now carries a port current — but the loop that reads it
has a floor set by the drive, so the review ruled a third current
definition (the displacement current through the port's own gap), which
is today's queue item 1.** All four implementer slots this interval fired
and journaled; three landed first-run, one parked correctly. **Still a
self-consistency story at the Larmor frequencies: no absolute SAR, no
C95.3 compliance figure, no homogeneity, no Larmor coil accuracy claim,
no resonance or tuning claim, and no solve has touched the human-scale
mesh.** Source of truth is `PROJECT_PLAN.md`; this page is a read-only
digest for the human operator.

## Waiting on you

1. 🟠 **Bring the XL service up for `ANS-4` step 2 (§9 item 7, `xl`)** —
   `docker compose -f docker/docker-compose.yml --profile xl up -d`, then
   the next implementer slot takes it (one window, ≤ 2 h, ≤ 512 GiB,
   `-n 16`); stop it afterwards. Not Up at 03:00; the slot skips it
   unmarked until it is.
2. 🟡 **Agent-definition edits — now costing slots.** The `example-runner`
   ended its turn with a window running for the **second** time (22:30
   slot, `EX-52`), despite the rule in its spawn prompt; the slot
   recovered in the foreground at ~15 min cost. The five one-liners
   (two for `example-runner.md`, one for `mesh-probe.md`, one for
   `implementer.md` — rule (d) — and rule (e) for both) are the fix; the
   interactive session's attempt on `implementer.md` was denied at the
   prompt. Say which you want and an interactive session applies them.
3. 🟡 **Session-limit watch, 09-06 → 09-07:** the four sessions killed on
   09-06 (02:15 weekly, 03:00 review, 04:30, 06:00) did **not** repeat
   tonight — this 03:00 review fired on schedule after four full
   implementer slots. No schedule change made; if 04:30 / 06:00 die
   again the pattern is the 21:00–00:00 slots consuming the reset, and
   thinning them (or moving 02:15 / 03:00 later) is yours to decide.
4. 🟡 **`ANS-1` note, no action yet:** the refined Dodd–Deeds fixture
   moved our ΔR column on 09-06; the 2026-09-02 AGREE verdict is
   re-checked privately by the 09-09 weekly.
5. 🟢 **`ANS-3` AED run** — the top of your queue. Same low-order rule,
   same private-results handling; the tracked table's AED cells are blank
   by construction.
6. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert only if you
   want the single-commit form.
7. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
8. FYI, no action — physics worth a glance. **(a)** The 1% power gap on
   the 4-leg coil is closed as a *finding*: the exact discrete identity
   `P_src = P_vol + P_sheet` holds to 1e-14 on every drive, and the
   6.7e-05 W the accounting misses is exactly what the terminal-current
   form of a sheet's dissipation under-counts when the field is not
   uniform across the sheet (Cauchy–Schwarz, 1.06%, reproduced to 1e-13).
   The review ruled the 1% band a record and re-pointed the one red test
   at the exact identity (queue item 2). **(b)** An Ampère loop around a
   PEC hole's wire reads the driven current to 1.9% but the *undriven*
   port's current (1000× smaller) is buried under the loop's own sampling
   floor, which scales with the drive; the displacement current through
   the port's own gap scales with the port's own current by two decades
   and is the same integral form the package already uses (item 1).
   **(c)** 10 g mass-averaged SAR on the coil field is C4-covariant to
   0.33% at 10 MHz; the 1 g ball (6.2 mm on a 7.5 mm mesh) is not, at
   6.8% — a mesh statement, not an operator one. Local `main` remains
   well ahead of origin (push is manual).

## Honest current state (digest of §2 — SAR and multi-port rows moved)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **first gate + both hole meshes landed; a hole port current exists but is floored** (`TH-15` steps 1, 2a, 3a ✅; 2b parked) — every conductor in a *solved* coil fixture is still a solved-inside volume with σ capped by the mesh (800 S/m) | PEC sphere as a hole: β = 1.019746 vs 1 (1.97% against 4.886%), field miss converging at +1.19 in h. Two-torus hole 161 461 cells, birdcage hole 80 181 cells. **The Ampère-loop current gives the hole a full 2×2 with both mutuals inside 10%, but its DG0 sampling floor (~1e-2 A) swamps the undriven port's 1.2e-3 A** — reciprocity 4.5e-3 vs 1e-3; not landed. The gap-displacement current is On-deck item 1; step 2 (`Re Z = 0` on the hole) item 6, serial on it; step 3 proper the weekly's. `TH-14` (copper) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.2747% against the filament form, 0.3895% against the finite-wire-corrected form, 418 888 cells (`MAT-6` ✅); `ANS-1` AGREE (numbers private, re-checked 09-09); finite-wire term +0.115% on ΔR (`MAT-8` ✅). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only**; externally **AGREE at 10 MHz, inconclusive at 64 / 128 MHz** (`ANS-4`, private; the XL run is the discriminator). 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13, 18 classes ≤ 0.44% vs 5%. **RLC sheets exist, not gated** (`PORT-14` 🟡: single-mode to 3.4e-3, ruled a fixture record by the weekly); the circuit layer's algebra gated at 1e-12 (`PORT-15` step 1 ✅) and claims nothing about any meshed coil |
| Multi-port drive | 🟡 package-level, gated on the 4-leg identities (`POST-6` step 1); shown by `ports:13` (`EX-49` ✅) | quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087%, linearity 1e-12. **Power accounting attributed (`PORT-16` step 1 ✅, audited PASS):** the exact discrete identity closes at 6.8e-15 … 1.0e-14 on every drive; the 6.7e-05 W gap is the terminal form's Cauchy–Schwarz deficit to 3.2e-13 … 5.1e-13. The drive-level red (11.6% vs 1e-2) is re-pointed at the exact identity by ruling — On-deck item 2 lands it and retires the known-issues entry |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; F-human (0.15 m) gated on CAD identities (`GEO-25` ✅), shown by `mesh:12` | 4-leg record 111 898 / 116 085 (ports) / 80 181 as a hole; 16-leg 270 728; F-human 504 642 cells — **a mesh, never solved; 64 MHz cost unpriced** |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. The closed-form target is finite legs + rings (step 4a, On-deck item 3, pure numpy first). Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | ✅ **mass-averaged 10 g, C4-gated on one fixture at 10 MHz at fixed `h`** (`MAT-4` step 4, audited PASS); the integral gates of `WF-6` step 3h beneath it; shown by `ports:9`, the 10 g example is On-deck item 4 (`EX-53`) | four 10 g C4 pairs 0.3303 / 0.0756 / 0.0574 / 0.3132% vs 5%; whole-phantom identity 1.6e-14; far-side control ~86%. **The 1 g column misses at 6.84% and is a printed record** (a 6.2 mm ball on a 7.5 mm mesh). **No absolute SAR, no C95.3 compliance or limit figure, no Larmor, no convergence claim** |
| SAR, imposed field | ✅ lossy sphere 3.5% (`MAT-4` step 1); its example `mat:2` landed (`EX-52` ✅, audited PASS: 3.422 / 3.536% vs the imported 10%, σ = 0 at exactly 0.0 W) | — |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 5 deliberate/known**, unchanged (one is re-pointed by item 2); example-artifact census `dead=0 stale=79 exit=2` at `5d95cf9`, 46 examples | API sweep `violations=0` on all four roots; no new known-issues entry this interval; `OPS-40` (item 5) guards the collective that cost the 22:30 slot its first window |

## Recent activity (2026-09-06 18:00 → 2026-09-07 03:00)

- **19:30:** `MAT-4` step 4 landed — 10 g mass-averaged SAR on the four
  coil-driven solves, C4-covariant at 0.33% worst vs 5%, whole-phantom
  identity 1.6e-14, 1 g printed at 6.84%. `MAT-4` ✅; 132 s at 4 ranks.
  Audited PASS (13 of 13 digits; one `src/` permissiveness change,
  disclosed).
- **21:00:** `TH-15` step 2b — the Ampère-loop current **works on the
  hole** (full 2×2, both mutuals inside 10%) but its floor is ~1e-2 A
  absolute: empty loop 8.9e-3 vs 1e-3, reciprocity 1.4e-3 / 4.5e-3 vs
  1e-3. Parked, nothing loosened, §9 item marked in the same commit.
  222 s at 4 ranks.
- **22:30:** `EX-52` landed — `mat:2`, imposed-field SAR on the lossy
  sphere vs its closed form, 48 s at 2 ranks. The spawned runner ended
  its turn mid-window and was killed; the slot found the collective
  point-list bug and recovered in the foreground. ✅, audited PASS.
- **00:00:** `PORT-16` step 1 landed — the exact discrete power identity
  closes at 1e-14 on all four drives; the 6.7e-05 W gap **is** the
  terminal form's Cauchy–Schwarz deficit (1e-13). Mechanism (b) of
  `POST-6` excluded; 131 s at 2 ranks. Audited PASS (20 of 20 digits;
  two derivation repairs ratified).
- **03:00 review:** three audits PASS; six rulings (the gap-displacement
  current as the hole port's definition, `POWER_BALANCE_BAND` a record
  with the red re-pointed, `OPS-40` and `EX-53` opened, the loop-route
  deviation moot, the XL item kept); six ordinary items queued.

## Automation health

- **Four of four scheduled slots fired and journaled**; three landed
  first-run, one parked correctly (rule (d) honoured, third consecutive).
  First-run streak 35 of 35 over the slots that fired since 09-03 18:00.
  Container Up 3 days continuously; this 03:00 review fired on schedule.
- **Foreground-executor rule: broken at 54** by the `example-runner`
  (22:30 slot) — second occurrence for that agent; the slot recovered.
  No docker-socket denial this interval (3 of 75 overall; 0 of the last
  35); no allowlist denial; no compute-safety event.
- Tier labels: `MAT-4` step 4 heavy by ceiling, measured 132 s (standard);
  `TH-15` step 2b heavy by ceiling (222 s at 4 ranks); `EX-52` standard
  (48 / 56 s); `PORT-16` step 1 standard (131 s).
- **Housekeeping:** `attempts.md` at 16 258 lines vs the 6 000 budget —
  the window is the Wednesday weekly's call. 1 209 logs. Example census
  `stale` drifted 75 → 79 (severity `report`), the weekly's refresh.

## On deck (§9 — six ordinary items plus the XL item; 1–5 independent, 6 serial on 1)

1. **`TH-15` step 2c** — the gap-displacement port current
   `I = I_drive δ + (1/g)∫_gap (σ + jωε) E·ĥ dV` as an additive route on
   the spec, anchored on the solid two-torus: continuity vs the conduction
   current on both ports, reciprocity, the closed-form mutual, the loop
   route's 0.032 + 0.190j undriven ratio as the record to beat
   *(implementer; heavy by ceiling, 4 ranks, ≈ 220 s + the package gate
   re-run)*
2. **`PORT-16` step 2** — the exact power identity and its attribution on
   the superposed drive; the deliberate red re-pointed by ruling, the
   `POST-6` known-issues entry retired, the row ✅ *(implementer; ≈ 105 s
   at 2 ranks)*
3. **`WF-6` step 4a** — the birdcage mode-1 Biot–Savart closed form as
   pure numpy, gated on exact identities *(implementer; smoke, seconds)*
4. **`EX-53`** — mass-averaged 10 g SAR on the coil-driven field in
   ParaView, the gate's imported bands and mis-paired control
   *(example-runner, foreground; ≈ 150 s at 4 ranks)*
5. **`OPS-40`** — the point-evaluation collective refuses a rank-dependent
   point list, on every rank; `EX-52`'s gate and example re-run green
   *(implementer; smoke + two standard re-runs)*
6. **`TH-15` step 2 proper** — the parked PEC-hole 2×2 module on the
   displacement route (`Re Z = 0`, reciprocity, mutual) — **skip unmarked
   if item 1 did not land** *(implementer; ≈ 220 s at 4 ranks)*
7. **`ANS-4` step 2 (`xl`)** — skipped unmarked until `fem-em-solver-xl`
   is Up (Waiting-on-you item 1)

The 09:00 slot drains by protocol only if all six ordinary items land or
block; the 10:30 review refills.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
