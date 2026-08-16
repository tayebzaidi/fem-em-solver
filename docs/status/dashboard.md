# FEM-EM Solver — status

**Updated:** 2026-08-16, 18:00 review. Third productive interval in a row:
three of four slots closed chunks (`TH-11` step 3, `EX-21`, `OPS-19`
step 1, all audited §4-compliant); the fourth parked a **gated lumped-port
formulation** that turned out to need a mesh surface the two-torus fixture
doesn't have — the review split that out as `GEO-16` and re-queued the
port work behind it. Source of truth is `PROJECT_PLAN.md`; this page is a
read-only digest for the human operator.

## Waiting on you

0. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 10:30). The
   FEM half is on record; your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. It is also the **independent adjudication input for
   `PORT-10`'s composition result** — worth doing before birdcage-port
   numbers start being quoted against the additive ladder.
1. **Two operator decisions the automation cannot make** (unchanged):
   (a) **`OPS-16` unblock** — retry-on-529 is designed but
   `Edit(scripts/automation/**)` is under `ask`; move the three launcher
   files to `allow` or apply by hand (mind the `.gitignore` bare-`lib/`
   trap). (b) **Outage visibility** — nothing records a *missing* run.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 0) is the
   second case in the same queue.
4. Housekeeping: local `main` is now **81 commits ahead** of
   `origin/main` (last push 2026-08-10) — push when convenient.

## Honest current state (digest of §2 — no capability row changed state)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.88% (MAT-6). TH-11 now has three transition points — 1.58 / 5.59 / 10.27% at 10 / 30 / 64 MHz — but the resolution confound is monotone with the signal, so it's still a set of points, not a trend. Step 4 (queued): Richardson extrapolation in h at fixed f |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only. **`PORT-9` step-1 formulation is written and identity-gated** (Jin resistive sheet, six exact identities incl. I = V/Z to < 1e-12, on a parked branch) — but its instantiation found the fixture has **no longitudinal port-sheet surface**; `GEO-16` (new mesh chunk) emits it, then the port work resumes. §2.2's "no coil has ports" stands |

## Recent activity (2026-08-16 10:30 → 18:00)

- **PORT-9 step 1 — parked, and the parking is the finding.** The
  lumped-port BC (Jin 3e §1.5.4/§6.5) landed gated on
  `attempt/PORT-9-20260816T170800Z`, but a port sheet needs current
  flowing *in* its plane, and the fixture's only tagged surfaces are
  cross-sections *normal* to the current — the wrong constitutive law.
  Review decision: mesh prerequisite split out as `GEO-16`; branch kept;
  step-1 re-run is a wiring job, not a re-derivation.
- **TH-11 step 3 ✅** — 30 MHz mid-point reads +5.5912% vs quasi-static
  Dodd–Deeds; identities at 1e-14; still unattributable between physics
  and resolution (1.84 cells/δ). Step 4 scoped: the h-ladder at fixed f.
- **EX-21 ✅** — first birdcage example of any kind
  (`examples/meshing/03_…`): graded rung keeps 0.967 of CAD conductor
  mass, baseline 0.740 asserted to *fail* the same gate, both rungs in
  ParaView-openable XDMF. Its own docrefs violation was caught and fixed
  by the checker in-run.
- **OPS-19 step 1 ✅** — the docrefs checker's signal is restored: exit
  0/1/2 (clean / hard / stale-only) plus a machine-readable `RESULT:`
  line; the standing 24 stale references now read exit 2 instead of
  masking real defects behind exit 1. A latent `--docs-root` crash was
  fixed in passing. It also **corrected `EX-22`'s premise by
  measurement**: the 24 artifacts *exist* (aged ~6 days), `dead=0` — the
  weekly review's "absent on disk" doesn't hold at this commit.

## Automation health

- **Implementer grid: 4/4 slots productive** (one parked-with-finding,
  three closures); tree clean at every handoff; the one `attempt/*`
  branch is deliberate and adjudicated, no `recovered/*`. All three
  review slots today ran normally; the weekly slot moved to Sunday 02:15
  (`5478b20`) past the usage reset, closing that failure mode.
- **Doc-reference checker signal restored** (`OPS-19`): example-running
  chunks now gate on `exit != 1` and read staleness as information.
  `EX-22` (artifact refresh) stays queued behind re-audited premises —
  its refresh work is unchanged, but "24 → 0" now means *stale* → 0.
- Standing weekly-review items: unchanged — POST-4 export adoption
  (your ParaView check) and ANS-1/ANS-3 adjudication (no AED numbers
  yet) still pending.

## On deck (§9, restocked this review; 1–3 independent, 4–5 serial)

1. **GEO-16** — emit the longitudinal port-sheet mid-plane in
   `two_torus_domain` (mesh-only; unblocks the port lineage).
2. **OPS-17 step 1** — finiteness-only test inventory (no solves).
3. **TH-11 step 4** — Richardson ladder at fixed f, 10 + 30 MHz (heavy).
4. *(depends on 1)* **PORT-9 step 1 re-run** — merge the parked branch,
   wire the sheet, print lumped Z beside the gap route.
5. *(spare; depends on 1 + 4)* **PORT-9 step 2** — cross-route identity
   gate.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
