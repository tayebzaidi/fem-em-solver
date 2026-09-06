# FEM-EM Solver — status

**Updated:** 2026-09-06 18:00 daily review. Headline: **the refined
Dodd–Deeds fixture is production (ΔR 0.27% against the filament form,
≈ −0.40% against the finite-wire-corrected one, 418 888 cells) and both
hole meshes of the conductor lineage are landed — but a PEC hole cannot
yet carry a port current, and that is today's queue item 2.** All four
implementer slots this interval fired and journaled; the queue drained at
16:30 and is refilled with five ordinary items plus the XL item, which is
skipped until you bring the XL service up. **Still a self-consistency
story at the Larmor frequencies: no absolute SAR, no homogeneity, no
C95.3, no Larmor coil accuracy claim, no resonance or tuning claim, and
no solve has touched the human-scale mesh.** Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. 🔴 **The account session limit ate four scheduled sessions on 09-06
   (02:15 weekly, 03:00 review, 04:30 and 06:00 slots) — schedule
   decision, yours only.** Unchanged since the 10:30 review. They died
   *at start*, in the band right after the 02:00 reset, so the limit was
   consumed by the preceding implementer slots. Either move the 02:15 /
   03:00 pair later (e.g. 07:15 / 08:00 — `scripts/automation/crontab`,
   then `crontab scripts/automation/crontab`) or thin the 21:00 / 22:30 /
   00:00 implementer slots. Tonight's 21:00 → 06:00 run is the next test.
2. 🟠 **Bring the XL service up for `ANS-4` step 2 (§9 item 6, `xl`)** —
   `docker compose -f docker/docker-compose.yml --profile xl up -d`, then
   the next implementer slot takes it (one window, ≤ 2 h, ≤ 512 GiB,
   `-n 16`); stop it afterwards. It was not Up at 18:00; the slot skips
   it unmarked until it is.
3. 🟡 **`ANS-1` note, no action yet:** the refined Dodd–Deeds fixture
   **landed at 12:00 today** and moved our ΔR column (the pin followed the
   fixture, as ruled). The 2026-09-02 AGREE verdict is re-checked
   privately by the 09-09 weekly; if the private margin was inside that
   move you will hear it there.
4. 🟢 **`ANS-3` AED run** — the top of your queue. Same low-order rule,
   same private-results handling; the tracked table's AED cells are blank
   by construction.
5. 🟡 **Agent-definition edits — still open.** Five one-liners remain
   (two for `example-runner.md`, one for `mesh-probe.md`, one for
   `implementer.md` — rule (d) — and rule (e) for both); the interactive
   session's attempt on `implementer.md` was denied at the prompt. Say
   which you want and an interactive session applies them.
   `implementer.md` also has no "Last verified against" footer.
6. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). It saved the
   rotation on 09-06; revert only if you want the single-commit form.
7. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
8. FYI, no action — physics worth a glance. **(a)** A PEC hole has no
   conduction current, so the gap-voltage port model — which reads its
   current as `σ∫E·φ̂ dV / L` over conductor cells — is undefined on it;
   the fix is an Ampère loop `∮H·dl` around the wire, anchored on the
   solid first (item 2). **(b)** The 4-leg coil as a hole meshes 31%
   cheaper (80 181 vs 116 085 cells) with every sheet identity intact;
   the only thing the cut revealed is that OCC's own mass quadrature on
   the tori misses the analytic box volume at 3e-8. **(c)** The 1% power
   gap on the 4-leg fixture has a candidate with the right sign: the
   sheet-loss accounting uses terminal currents, which by Cauchy–Schwarz
   under-count the sheet's dissipation whenever the field is not uniform
   across it (item 4 measures it). **(d)** The weekly's B1+ closed form
   ("infinitely long line currents") would miss the F-small centre field
   by 29% (finite-length factor 0.707); the anchor is finite legs plus
   rings, written first as pure numpy (item 5). Local `main` remains well
   ahead of origin (push is manual).

## Honest current state (digest of §2 — coil loading and conductor rows moved)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **first gate + both hole meshes landed** (`TH-15` steps 1, 2a, 3a) — every conductor in a *solved* coil fixture is still a solved-inside volume with σ capped by the mesh (800 S/m) | PEC sphere as a hole: β = 1.019746 vs 1 (1.97% against 4.886%), field miss converging at +1.19 in h, natural-cavity control 29×. Two-torus hole 161 461 cells, birdcage hole 80 181 cells, sheets at 1e-16, cavity areas vs the solid interfaces 3.7e-7 / 3.9e-7. **No port has carried a current on a hole** — step 2b (On-deck item 2) adds the Ampère-loop current; step 2 (`Re Z = 0`) is parked on `attempt/*` behind it; step 3 proper is the weekly's. `TH-14` (copper) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only | **Dodd–Deeds ΔR 0.2747% against the filament form, 0.3895% against the finite-wire-corrected form, 418 888 cells (`MAT-6` step 11 landed 09-06 12:00; 1.58% was the pre-refinement record)**; `ANS-1` AGREE (numbers private, re-checked 09-09); finite-wire term +0.115% on ΔR (`MAT-8` ✅). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only**; externally **AGREE at 10 MHz, inconclusive at 64 / 128 MHz** (`ANS-4`, private; the XL run is the discriminator). 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13, 18 classes ≤ 0.44% vs 5%. **RLC sheets exist, not gated** (`PORT-14` 🟡: single-mode to 3.4e-3, a field effect of the sheet, ruled a fixture record by the weekly); the circuit layer's algebra gated at 1e-12 (`PORT-15` step 1 ✅) and claims nothing about any meshed coil |
| Multi-port drive | 🟡 package-level, gated on the 4-leg identities (`POST-6` step 1); shown by `ports:13` (`EX-49` ✅) | quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087%, linearity 1e-12. **Drive-level power identity reads 11.6% vs 1e-2 — deliberate red**; the 1%-of-supplied gap is `PORT-16`, whose step 1 (On-deck item 4) assembles the exact discrete identity |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; F-human (0.15 m) gated on CAD identities (`GEO-25` ✅), shown by `mesh:12` | 4-leg record 111 898 / 116 085 (ports) / **80 181 as a hole**; 16-leg 270 728; F-human 504 642 cells — **a mesh, never solved; 64 MHz cost unpriced** |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. The closed-form target is now finite legs + rings (step 4a, On-deck item 5, pure numpy first). Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🟡 two integral gates on one fixture at 10 MHz at fixed `h`; shown by `ports:9` | twelve rotation pairs ≤ 1.52%, four mirror pairs ≤ 1.75%, both vs 5%; partition identity exact. **The mass-averaged 1 g / 10 g step is On-deck item 1** (`MAT-4` step 4 — 10 g C4 identity asserted, 1 g printed). No absolute SAR, no C95.3, no Larmor, no convergence claim |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4` step 1); its example (`EX-52`, `mat:2`) is On-deck item 3 |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 5 deliberate/known**, unchanged; example-artifact census `dead=0 exit=2` at `237a7af`, 45 examples | API sweep `violations=0` on all four roots; the probe-census known-issues entry retired by `OPS-39` ✅ (audited PASS); no new entry |

## Recent activity (2026-09-06 10:30 → 18:00)

- **11:29:** weekly review completed interactively (`ANS-4` adjudicated,
  `PORT-14` / `POST-6` rulings, `PORT-16` and `EX-52` opened, the XL item
  placed).
- **12:00:** `MAT-6` step 11 landed — the slab-refined fixture is
  production; `ans:1` exit 0 with ΔR 0.2747% and the re-pinned record
  reproduced to 3.5e-10; `mat:1` exit 0; both guides, `COMPARISON.md`,
  §2 / §6 / §7 moved; branch deleted. 262 + 273 s at 8 ranks. Audited
  PASS (no tolerance moved; the auditor's one caveat re-traced and
  overruled — the 0.27998% is exact arithmetic on the log's ΔZ values).
- **13:30:** `TH-15` step 2 — **blocked, not failed**: the hole meshes
  and solves, then the gap-voltage route raises because a hole has no
  conductor cells to integrate a current over. Parked on `attempt/*`,
  §9 item marked in the same commit. 102 s at 4 ranks.
- **15:00:** `OPS-39` — the probe census is rank-safe, gated on the exact
  count identity (naive overshoot = 256 = Σ ghosts at 2 ranks); the
  known-issues entry retired. ✅, audited PASS (15 of 15 digits).
- **16:30:** `TH-15` step 3a — `birdcage_port_domain(as_hole=True)`;
  80 181 cells, sheets at 3e-16, cavity wall vs the solid interface
  3.9e-7; the partition anchor re-registered by measurement against OCC's
  own quadrature (ratified). 54 s at 2 ranks. Step ✅, row 🟡. Queue drained.
- **18:00 review:** two audits PASS; six rulings (step 2's blocker is a
  step 2b, step 3a's re-registration ratified, `MAT-4`'s coil step named
  and queued, `WF-6` step 4 split, `PORT-16` step 1 sharpened, the XL
  item kept); five items queued.

## Automation health

- **Four of four scheduled slots fired and journaled**; three landed
  first-run, one parked correctly (rule (d) honoured for the second time
  in two days). First-run streak 32 of 32 over the slots that fired since
  09-03 18:00. Container Up 3 days continuously.
- **Foreground-executor rule: 54 for 54** since written. No docker-socket
  denial this interval (3 of 71 slots overall; 0 of the last 31). One
  cosmetic `bash_guard` denial (a `grep` pattern containing "pytest");
  no compute-safety event.
- Every digit re-read from the log by the slot owner; one slot converted
  a blocked item into a named missing capability inside its window; one
  slot re-registered a band by measurement and said so in the docstring.
  Tier labels: `MAT-6` heavy by ceiling (262 / 273 s at 8 ranks); `TH-15`
  step 2 heavy by ceiling (102 s at 4 ranks); `OPS-39` smoke + standard
  (≤ 57 s); `TH-15` step 3a standard (54 s).
- **Housekeeping:** `attempts.md` at 15 907 lines vs the 6 000 budget —
  the window is the Wednesday weekly's call. 1 236 logs.

## On deck (§9 — five ordinary items plus the XL item; all independent)

1. **`MAT-4` step 4** — mass-averaged 1 g / 10 g SAR on the coil-driven
   field; the 10 g C4 identity asserted at 5% on the finer-phantom rung,
   the whole-phantom identity exact *(implementer; heavy by ceiling,
   4 ranks, ≈ 3–5 min predicted)*
2. **`TH-15` step 2b** — the Ampère-loop port current `∮H·dl`, anchored
   on the solid two-torus (reciprocity, closed-form mutual, empty-loop
   control) then read once on the hole *(implementer; ≈ 250 s at 4 ranks
   + the package gate re-run)*
3. **`EX-52`** — imposed-field SAR on the lossy sphere in ParaView, the
   `MAT-4` step 1 gate's own bands and two-σ control *(example-runner;
   ≈ 40 s)*
4. **`PORT-16` step 1** — the exact discrete power identity on the 4-leg
   fixture and the terminal-current split against it *(implementer;
   ≈ 140 s at 2 ranks)*
5. **`WF-6` step 4a** — the birdcage mode-1 Biot–Savart closed form as
   pure numpy, gated on exact identities *(implementer; smoke, seconds)*
6. **`ANS-4` step 2 (`xl`)** — skipped unmarked until `fem-em-solver-xl`
   is Up (Waiting-on-you item 2)

The 00:00 slot drains by protocol only if all five ordinary items land;
the next review refills.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
