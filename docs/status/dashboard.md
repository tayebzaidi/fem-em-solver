# FEM-EM Solver — status

**Updated:** 2026-08-27 03:00, **daily review (scheduled, ran normally)**.
Headline: **the 0.11 execution census has covered its cheap half** —
`OPS-26` step 2 leg (a) took all four slots of the interval and finished:
184 of 189 tests in the seven cheap directories observed in footered runs
(182 green, 2 red), 5 deferred with a stated reason each, arithmetic
reconciled (182 + 2 + 5 = 189). The census did its job: it found **two new
reds and one rank-dependent deadlock**, all carrying the same 0.11 gmsh
"overlapping facets" string on three *different* geometry generators — so
the earlier "coarse-resolution floor" reading no longer covers the evidence
and a single owner (`GEO-23`) is commissioned. It also found a test module
that has silently been collecting zero tests. No chunk closed this interval;
nothing in §2 moved. What this does **not** say: nothing is compared
against an external reference at 64/128 MHz, nothing is tuned or resonant,
no B1+/SAR on the coil. Source of truth is `PROJECT_PLAN.md`; this page is
a read-only digest for the human operator.

## Waiting on you

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the
   second case in the same queue.
4. FYI, no action: the Sunday 08-30 weekly review owes three decisions —
   the F-human fixture directive, **`ANS-4` commissioning**, and whether a
   128 MHz resolution study is warranted. Local `main` remains well ahead
   of origin (push is manual).
5. FYI, no action: **the test suite on 0.11 is less healthy than "no known
   gate red" suggested** — three gmsh-abort sites and one dead module were
   found by the census in one night; none is a physics gate, all are
   filed and owned. Expect `GEO-23` in the queue for a slot or two.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); one sibling sampled band gets its own measurement (`MAG-20`, queued) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads 0.06–0.10% vs 0.5%; **self-consistency identities only — absolute accuracy at Larmor is `ANS-4` (weekly review)** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ⚠️ **census half done**: cheap roots 184/189 observed, **2 reds + 1 rank-dependent deadlock + 1 dead module filed** (none a physics gate) | `OPS-26` leg (b) — `validation` + `ports`, the expensive half — is queue item 1; the gmsh family is `GEO-23` |

## Recent activity (2026-08-26 18:00 → 2026-08-27 03:00)

- **19:30:** `OPS-26` leg (a), slot 1 — denominator re-derived (189, not the
  inherited 216/232); 30/189 observed; first red (coil+phantom gmsh abort)
  and the discovery that a red's teardown eats the rest of the command.
- **21:00:** slot 2 — 93/189; a second gmsh red on `birdcage_port_domain`'s
  own partition test; the dead `test_cylindrical_domain.py` filed.
- **22:30:** slot 3 — 137/189; `post` and `mesh` complete; `tests/solver`
  still 0/51 after two whole-root commands died; 23 non-green names
  **discarded** for want of a footer (fail-closed control).
- **00:00:** slot 4 — 184/189, **leg (a) done**; one command per module
  took `tests/solver` 0 → 47/51 and vindicated the discard: 21 of those 23
  would have been false reds. The one module that would not run deadlocked
  in both builds with the same test passing on one rank and failing on the
  other.
- **03:00 review:** no closures to audit; leg (a) dropped from the queue,
  leg (b) rewritten to the module-per-command shape and queued first;
  `GEO-23` commissioned as owner of the four new known-issues entries.

## Automation health

- Four of four scheduled slots ran, all landed on `main` clean — zero
  parked branches, zero wedges, zero denials. All four went to one item,
  by design (the census needed consecutive slots).
- ~4 100 s of harness compute across 31 logs; the leg's real cost was the
  three exit-124 windows before the per-module shape was adopted.
- Queue holds **six items**: `OPS-26` leg (b), then `MAG-20`, `GEO-20`
  step 2, `EX-34`, `GEO-22`, `GEO-23` — no serial dependencies.

## On deck (§9 — six items this review)

1. **`OPS-26` step 2 leg (b)** — execution census, `validation` + `ports`,
   one command per module (heavy; may not finish in one slot by design)
2. **`MAG-20`** — measure-then-dispose the last sampled two-sided rate
   band (standard)
3. **`GEO-20` step 2** — 32 ring-gap ports at 16 legs under the per-class
   reading (standard)
4. **`EX-34`** — birdcage S-matrix across 10 / 64 / 128 MHz on one mesh
   (`PORT-11` ramp; standard)
5. **`GEO-22`** — bisect and guard the straight-wire coarse-resolution
   floor (smoke + standard)
6. **`GEO-23` step 1** — classify the three "overlapping facets" sites by
   rank width, ladder the resolution, revive or delete the dead module
   (smoke + standard; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
