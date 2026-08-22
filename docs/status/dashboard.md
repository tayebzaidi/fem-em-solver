# FEM-EM Solver — status

**Updated:** 2026-08-21 18:00, **daily review (scheduled, ran normally)**;
Waiting-on-you amended 2026-08-22 00:00 by a drained implementer slot (item 1
promoted from heads-up to blocker, per §9 item 1's standing instruction), and
again 2026-08-22 by an interactive operator session — **both permission asks
are now settled**: item 1 (`Edit(docker/**)`) granted, narrowed to two named
files, so `OPS-18` is runnable; item 2 (`OPS-16`) closed **won't fix**. The
Waiting-on-you list currently owes you nothing on the automation side; the
next review deletes items 1 and 2. The rest of this page is the 18:00
review's and is not re-dated.
Headline: **the credit outage is over and the audit debt is cleared.** This
review launched on the same `--model claude-fable-5` that produced four
consecutive 146-byte `out of usage credits` deaths (Thu 10:30 → Fri 10:30),
so the budget has refilled; no config was changed. All **five closes from
Wednesday are now audited COMPLIANT** (`GEO-18` step 1, `GEO-17`, `MAG-17`,
`OPS-23`, `EX-26`), **`OPS-17` is closed** after a 9-attempt complex-suite
reconciliation (216 of 216 runnable validation tests observed; 2 files
formally deferred with reasons), and — per the standing written commitment —
**the DolfinX 0.7.2 → 0.11.0.post0 upgrade (`OPS-18`) is now queued at the
top of §9**, with `GEO-18` step 2 (the last mesh prerequisite before
birdcage ports) scoped and queued behind it. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. ✅ **`OPS-18` is UNBLOCKED — you did this 2026-08-22, nothing further
   owed.** The broad `Edit(docker/**)` ask rule is gone; `Dockerfile` and
   `docker-compose.yml` are individually **allowed**, `docker/.claude/**`
   newly **asked**. The broad rule was *removed* rather than shadowed by a
   narrower allow, since `ask` is evaluated ahead of `allow` and the glob
   would otherwise have kept matching. §9 items 1–3 (the serial upgrade)
   are runnable as written from the next slot; the drain ends with them.
   **One constraint the next slots are bound by, recorded in §9 item 1:**
   the compose allow exists for the upgrade's `PYTHONPATH` plumbing only.
   `volumes:` (line 9 is `- ..:/workspace`, i.e. the host mount), the 64 G
   memory limit and the ports are **not** to be touched by any chunk — a
   chunk that thinks it needs a mount change must stop and ask you, the
   same way the `FROM` bump did. **Next review: delete this item.**
2. ⬛ **`OPS-16` — CLOSED WON'T FIX, nothing owed by you.** *(Operator
   decision, interactive session 2026-08-22 — recorded here only so it is
   not re-raised.)* The permission unblock was declined on the
   self-modification ground: a session that can edit its own launcher can
   change its own model, effort, timeout and disallowed tools, and the
   narrowed three-file variant does not fix that.
   `Edit(scripts/automation/**)` **stays under `ask`**. The operator also
   ruled the avoided cost acceptable — losing a few implementer slots to an
   out-of-credits, API-500 or 529 launch failure is tolerated weather, not a
   defect to chase. **This will not appear on Waiting-on-you again**; future
   launch failures are journalled as cost and nothing more. Full disposition:
   PROJECT_PLAN §7 `OPS-16` closing note. Note this leaves item 1 as the
   *only* `permissions.ask` decision outstanding. **Next review: delete this
   item** — it is a closure receipt, not an ask.
3. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
4. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
5. **ANS-1 Ansys replication** — still yours; ANS-3 (item 3) is the second
   case in the same queue.
6. FYI (unchanged): degree-2 coil memory headroom ~2 GiB. Local `main` is
   well ahead of origin (push is manual; last push 08-18 night).

## Honest current state (digest of §2 — one line changed this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field (MAG-13, 3.74%); complex build reproduces the records to the digit; MAG-17: multiplier spread is a discrete-source residual, rate 2.4476 |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power 3.63% (TH-10); degree-2 gated at 0.1405% (TH-12/EX-25) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6); no affordable 64 MHz bracket on this box (adjudicated 08-18); Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil; GEO-17's region policy (+10.7% coil recovery) is the meshing leg of the road there |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus only; birdcage blocked on one remaining mesh step — **GEO-18 step 2 is now scoped and queued** (§9 item 4); §2.2's "no coil has ports" stands |
| **Test-suite trust (new)** | ✅ reconciled | **OPS-17 closed 2026-08-21**: every runnable validation test (216/232) observed in a completed complex run; the 16 absent are exactly 2 files, deferred with named reasons (TH-12 memory wall; padded-record-only). The complex baseline OPS-18 needs now exists |

## Recent activity (2026-08-20 03:00 → 2026-08-21 18:00)

- **Wed:** eight slots, five closes (all now audited) + `OPS-17` leg (b2)
  attempts 4–6 (coverage 63 → 101, `dodd_deeds_*` closed 38/38).
- **Wed night / Thu early:** attempts 7–9 finished the job — `coil_loading_*`
  44/58, `richardson_ladder` in one command instead of two, then six more
  runs in one slot exhausted the runnable tail at **216**. Eight commands,
  zero exit-124, no assertion touched.
- **Thu 00:00:** queue drained; the slot spent itself independently
  corroborating the 216 denominator (fresh collect: 236 = 4 env + 232
  validation; the two absent files are exactly the deferred pair).
- **Thu 04:30 → Fri 16:30:** eight drained slots journalled per protocol —
  no governing session could run (see below). No compute, no digit moved,
  tree clean throughout.
- **This review:** five COMPLIANT audits (two minor transparency notes now
  in §7/§9: MAG-17's cited ladder log is a disclosed exit-1 pre-fix run;
  OPS-23's annotation omits one benign green log). OPS-17 closed. OPS-18
  commitment executed. GEO-18 step 2 scoped. EX-27 commissioned (GEO-17's
  policy capability; the GEO-18 example is deferred until that fixture
  stops moving; MAG-17's angle is already covered by EX-9/EX-10).

## Automation health

- **Credit-outage postmortem (resolved, no action taken or needed):** four
  review launches died on exhausted credits while every Opus implementer
  wrapper launched normally — the 12:00 Fri slot proved the failure
  model-scoped by wrapper-log comparison. This 18:00 review launching on
  the unchanged config closes the incident as a budget refill. Total cost:
  4 dead reviews + 8 drained implementer slots + 1 audited drain. The
  incident produced one useful artifact: the independent 216-denominator
  audit.
- **The `OPS-16` class is closed won't-fix** (operator decision 2026-08-22):
  launch-failure retry is not being built, and launch failures — credits,
  API 500, 529 — are henceforth recorded as ordinary cost. Retry logic would
  not have helped this interval's credit outage in any case.
- Container healthy all interval (Up 3+ days, no OOM, no wedge). Tree clean
  at every handoff; no `attempt/*` or `recovered/*` branches at review time.
- **Expect `attempt/OPS-18` to appear and persist** — it is the sanctioned
  worksite for the upgrade (see Waiting item 2), not a stalled tree.
- Standing weekly-review items unchanged: `TH-12` production-order
  decision, `POST-4` export adoption, `ANS-1`/`ANS-3` adjudication.

## On deck (§9 — restocked this review, five items)

1. **`OPS-18` step 1** — build & boot DolfinX `v0.11.0.post0`
   (on `attempt/OPS-18`; `main` keeps 0.7.2 until step 3 is green)
2. **`OPS-18` step 2** — API migration (migration pack is tracked in-repo;
   expect more than one slot)
3. **`OPS-18` step 3** — re-gate every §2.1 number in both builds (heavy;
   a moved gated number is a finding, not a tolerance problem)
4. **`GEO-18` step 2** — port-sheet mid-plane on the leg gaps; landing it
   completes `PORT-9` step 3's mesh prerequisite
5. *(spare)* **`EX-27`** — region-resolution policy example on the
   coil+phantom mesh (GEO-17's capability)

Items 1–3 are strictly serial; 4–5 run on the unchanged 0.7.2 container
regardless of upgrade progress.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
