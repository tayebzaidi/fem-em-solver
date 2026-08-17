# FEM-EM Solver — status

**Updated:** 2026-08-17, 10:30 review. Three of four slots closed their
items, all three audited §4-compliant — `PORT-9` step 2 (the 7.71%
cross-route miss is **diagnosed**: it's the transverse average), `OPS-17`
step 2 (14 test dispositions landed, **4 real code defects surfaced**),
`EX-23` (port-sheet example). The fourth (`TH-11` step 5) stopped on its
own pre-stated cost gate — the 64 MHz third rung is priced and doesn't
fit a slot unmodified; rescoped. Source of truth is `PROJECT_PLAN.md`;
this page is a read-only digest for the human operator.

## Waiting on you

0. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). The
   FEM half is on record; your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. Newly relevant to it: `PORT-9` step 2 diagnosed the
   lumped-vs-gap feed difference as the sheet's transverse average — an
   AED lumped port (which uses an integration *line*) is now a direct
   external check on the review's narrow-the-sheet decision.
1. **Two operator decisions the automation cannot make** (unchanged):
   (a) **`OPS-16` unblock** — retry-on-529 is designed but
   `Edit(scripts/automation/**)` is under `ask`; move the three launcher
   files to `allow` or apply by hand (mind the `.gitignore` bare-`lib/`
   trap). (b) **Outage visibility** — nothing records a *missing* run.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 0) is the
   second case in the same queue.
4. Housekeeping: local `main` is **92 commits ahead** of `origin/main`
   (last push 2026-08-10) — push when convenient.

## Honest current state (digest of §2 — two bullets moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.88% (MAT-6); the apparent frequency trend is attributed to mesh resolution (TH-11 step 4), but 64 MHz still has **no h→0 bracket**. Step 5's third rung is priced — 2.8 M cells, doesn't fit a slot as scoped — and rescoped as 5a (cache the mesh + rank control, queued) / 5b (the solves). Larmor coil loading stays labeled an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil. New caveat: OPS-17 surfaced a wrong-sign Poynting flux on the smoke fixture (POST-5 commissioned) — power-accounting hygiene is now on the mission path explicitly |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only. **PORT-9 step 2: both pre-stated bands MISS and the miss is diagnosed** — the lumped port averages the gap voltage across the sheet (7.7783 pp of the 7.71%; path residual 0.0763 pp), a feed-definition property, not a solver defect. Review decision: **narrow the sheet toward the centreline** (step 2b, queued — the measured profile predicts ~1% at interior width). Bands unmoved; §2.2's "no coil has ports" stands |

## Recent activity (2026-08-17 03:00 → 10:30)

- **PORT-9 step 2 ✅ (chunk stays 🟡)** — both pre-stated bands miss
  (cross-route 7.7095% vs 5%, lumped mutual 12.6931% vs 10%) and the
  falsifiable hypothesis was **confirmed by decomposition**: transverse
  averaging accounts for 7.7783 pp, the path/projection residual is
  0.0763 pp vs a ~1 pp gate (13×). The gap route stays inside its band
  on the same field, so the solver and mesh are exonerated. The review
  chose the fix: narrow the sheet (a facet-filter change, no gmsh work).
- **OPS-17 step 2 ✅** — 4 deletions, 10 anchored replacements landed,
  no band loosened. The new anchors immediately earned their keep:
  **four real defects surfaced** (coil+phantom meshes lose 22% of coil
  volume when asked for a *finer* size; gauge multiplier non-zero for a
  compatible source; Poynting flux wrong-sign on the smoke fixture;
  `sigma=0.0` raises). Three carried as strict xfail; all four now have
  commissioned chunks (`GEO-17`, `MAG-17`, `POST-5`).
- **TH-11 step 5 🚫 → rescoped** — the cost probe worked as designed:
  third rung meshes to 2 807 309 cells (inside ceiling) but the mesh
  alone is 288 s and the solve died mid-assembly at the window. Module
  parked, nothing broken. Rescope: 5a caches the mesh to XDMF and buys
  `-n 8` with a measured rank-invariance control; 5b runs the pair off
  the cache.
- **EX-23 ✅** — first example with an interior sheet surface;
  meshed/CAD = 1.000000000000, negative control bit-matches the
  sheet-less record. Measured bonus: the port sheet costs +354 cells —
  essentially free for PORT-9 step 3's budget.

## Automation health

- **4/4 slots productive** (3 closures + 1 correct pre-stated stop; a
  stop condition firing as written is the process working, not a
  failure). All three ✅ audited COMPLIANT by independent auditors.
- **One process find from the audit:** two OPS-17 harness footers
  recorded `grep`'s exit 0 over a failing and a killed pytest run
  (piping inside the harness command). Now a named trap in the review
  rubric and the OPS-17 step-3 item; no result was misreported in prose.
- Tree clean at every handoff; one `attempt/*` branch parked by design
  (TH-11 step 5's module — item 2 lands it); no `recovered/*`.
- Standing weekly-review items unchanged: POST-4 export adoption (your
  ParaView check) and ANS-1/ANS-3 adjudication (no AED numbers yet).

## On deck (§9, restocked this review; items 1–4 independent, 5 spare)

1. **PORT-9 step 2b** — the narrowed sheet: width ladder
   f ∈ {1.0, 0.735, 0.5}; the 5% band, unmoved, expected to hold at
   interior width; reciprocity sweep if it does.
2. **TH-11 step 5a** — cache the 2.8 M-cell third-rung mesh to XDMF +
   the `-n 8` rank-invariance control (fine rung reproduces +2.8063%
   within 0.1 pp).
3. **OPS-17 step 3** — full-suite legs in four sized commands + the
   finiteness-sweep 59 → 45 before/after control.
4. **POST-5 step 1** — the scalar-σ one-liner + the Poynting wrong-sign
   h-ladder discriminator (`ds` orientation checked first).
5. *(spare)* **EX-22** — restore the six examples' artifacts
   (stale 24 → 0; heavy).

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
