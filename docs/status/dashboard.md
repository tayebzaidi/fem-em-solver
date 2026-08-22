# FEM-EM Solver — status

**Updated:** 2026-08-22 18:00, **daily review (scheduled, ran normally)**.
Headline: **the upgrade's two blocking rulings are made, and the birdcage
has its first solved port.** `OPS-18` step 3 spent three slots turning two
failing records into evidence — the two-torus mesh moved with gmsh (a
licensed re-record), and the straight-wire gate turns out to have been
passing on a sampler choice since July (replaced by a new `MAG-18`
statistic, not re-banded). `PORT-9` step 3 leg (c) put the first field on
the gapped birdcage at **7.55 s a solve** with C4 holding at 0.0159%, and
found that the open-port column is near-degenerate — the port impedance is
the birdcage's capacitor, not a numerical knob. `main` still boots 0.7.2 by
design. Source of truth is `PROJECT_PLAN.md`; this page is a read-only
digest for the human operator.

## Waiting on you

**Nothing new is blocked on you this interval.** The 16:30 slot's ⛔ on
`OPS-18` 3a (two rulings owed) is **cleared by this review** — both
rulings are in the §7 `OPS-18` entry and the two known-issues entries, and
the queue below carries them out. The upgrade is back on the automation's
own critical path: `MAG-18` (item 1) → `OPS-18` 3a resumed (item 4) →
3b merge (item 5).

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the second
   case in the same queue.
4. FYI (unchanged): degree-2 coil memory headroom ~2 GiB. Local `main` is
   well ahead of origin (push is manual; last push 08-18 night).
5. FYI, standing: the `docker-compose.yml` allow is used only for
   `environment:` keys; `volumes:`, the mount and the 64 G limit are
   untouched, as §9 requires. `git checkout` cannot swap the two docker
   files in the sandbox (bind-mounted) — slots move them with Edit; routine
   now, no action needed.
6. FYI, a finding worth knowing about: **the straight-wire validation gate
   (`MAG-13`, 15% band) has been passing on a sampler choice** — the same
   solved field reads 15.80% / 12.75% / 11.50% at 8 / 10 / 20 sample
   points on the 0.7.2 image. The solver is fine (it converges at rate
   1.10, and at 1.99 on 0.11); the *statistic* was not gateable. `MAG-18`
   replaces it. §2.1's "12.75%" is that number and will be re-quoted.

## Honest current state (digest of §2 — unchanged in substance)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; Helmholtz 0.04%, loop 7.07%; **wire: the 12.75% / 15%-band gate is sampler-fragile (see above) — `MAG-18` re-gates it on a domain L2; rate 1.10 stands**; MAG-17 rate 2.4476 |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power 3.63% (TH-10); degree-2 gated at 0.1405% (TH-12/EX-25) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6); no affordable 64 MHz bracket on this box (adjudicated 08-18); Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus only; **the gapped birdcage now has one solved port column** (PORT-9 leg (c), 0.7.2): C4 adjacent spread 0.0159% vs 5%, but near-degenerate at `Z_p = 1e6 Ω` — no network, no reciprocity claim; §2.2's "no coil has ports" stands until leg (d) |
| Test-suite trust | ✅ reconciled | OPS-17 closed 08-21. **On 0.11 (branch only): TH-6, TH-10, MAT-4, MAT-6 reproduce; PORT-1 meshes and its physics gates hold, three reproduction records await a licensed re-record; MAG family 17/18 with the wire gate awaiting MAG-18** |

## Recent activity (2026-08-22 10:30 → 18:00)

- **12:00:** `OPS-18` 3a attempt 3 — the numpy-2 `float()` coercion lands;
  `PORT-1` meshes again (`17 passed / 2 failed`, 260.93 s, vs SIGABRT at
  12 s); a **fifth** undocumented 0.11 break fixed
  (`element.interpolation_points` is a property); real-mode `MAG` leg
  `17 passed / 1 failed`. Both legs stopped on **moved records, not broken
  code** (two-torus `passivity_max_sigma` and gap ratio at 1e-4, wire
  15.3848% vs 15%) with every physics identity intact. The predicted
  birdcage `!r` siblings do not exist (one `MathEval` site in the package).
- **13:30:** attempt 4 — both discriminating experiments run. Two-torus
  mesh **moved** (184 919 → 184 176 cells, −4.017e-03 — 24–40× the misses).
  Straight-wire ladder on both images **refutes** the mesh for leg 2: rate
  1.10 → 1.99, fine rung 9.26% → **4.46%**, the gated rung a 1.8× outlier
  on its own ladder and bit-identical at `-n 4`. 0.7.2 controls reproduce
  July to ≤ 0.04% on all three rungs.
- **15:00:** attempt 5 — `n_points` 8/10/20 on one solve per rung, both
  images. Sampler excluded as the outlier's cause; **the 15% band already
  fails on 0.7.2 at `n_points = 8` (15.8028%)**. Nothing touched.
- **16:30:** 3a marked ⛔ on its own text and fell through; **`PORT-9`
  step 3 leg (c) closed** — first field on the gapped birdcage, 116 416
  cells at ratio 1.000000, one solve **7.55 s** at `-n 2`, `6 passed 40 s`;
  `|Z₂₁ − Z₄₁|/|Z₂₁|` = **0.0159%** vs 5%; anti-degeneracy control at a
  1.0060× margin (the finding). One structural check fixed with its
  measurement (bbox centre, 1e-9 band kept).
- **This review:** leg (c) audited compliant from its log footer. **Two
  rulings made**: leg 1 re-record licensed (version-tagged, bit-identical
  twice, no band moved); leg 2 gate replaced by **`MAG-18`** (commissioned),
  not re-banded. **`PORT-9` leg (d0)** scoped — the 50 Ω termination probe
  with a ≥ 10× discrimination margin. §9 archive pass done (10:30 recap,
  items 1/2/4 texts → `plan-archive.md`). No chunk turned ✅, so no example
  is owed.

## Automation health

- Four slots, four useful outcomes: three stops-on-evidence that converted
  the blocked item into two decidable questions, one step close. No drain,
  no wedge, no permission denial needing an ask; one exit 124 was a
  deliberate `-n 1` sizing probe (400 s), not an overrun. Tree clean at
  every handoff; no `recovered/*`; container probed 0.7.2 after every
  restore (last: `20260822T201412Z_OPS-18-step3-container-restore3.log`).
- `attempt/OPS-18` is the sanctioned worksite at `731c40e` and persists
  until item 5 merges it. Round-trip ~2 min each way per OPS-18 slot.
- The queue holds **five** ready items: three independent (0.7.2), two
  serial on the upgrade.
- Standing weekly-review items unchanged: `TH-12` production-order
  decision, `POST-4` export adoption, `ANS-1`/`ANS-3` adjudication.

## On deck (§9 — five open items this review)

1. **`MAG-18`** — sampler-independent straight-wire gate: annulus domain
   L2 of `|B_h| − |B_ana|`, rate ≥ 0.7 pre-registered, `-n 2`/`-n 4`
   agreement, natural-BC control (0.7.2, `main`, heavy)
2. **`EX-28`** — gapped-birdcage mesh example with terminals and port
   sheets (0.7.2, standard, independent)
3. **`PORT-9` leg (d0)** — termination probe at `Z_p = 50 Ω`: discrimination
   margin ≥ 10× with C4 ≤ 5%, 1e6 Ω control bit-identical (0.7.2, standard)
4. **`OPS-18` 3a resumed** — leg 1 re-records under ruling (1); leg 2
   re-measures `MAG-18`'s statistic on 0.11 (depends on item 1; else leg 1
   only)
5. **`OPS-18` 3b** — §5.3 table, drift disposal, confirming run, **merge**
   (depends on item 4)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
