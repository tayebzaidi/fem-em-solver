# FEM-EM Solver — status

**Updated:** 2026-08-22 03:00, **daily review (scheduled, ran normally)**.
Headline: **both permission asks are settled, the queue is full again, and
the birdcage finally has somewhere to put a port.** `GEO-18` closed (leg
terminals + port sheets, every identity exact to 1e-12 or better) and
`EX-27` closed, both audited COMPLIANT. Your 2026-08-22 hand edit of
`.claude/settings.json` unblocked the DolfinX upgrade (`OPS-18`, §9 items
1–3); `OPS-16` is closed won't-fix per your decision. `PORT-9` step 3 — the
first port solve on a coil — is queued behind the upgrade as a priced cost
probe. Source of truth is `PROJECT_PLAN.md`; this page is a read-only digest
for the human operator.

## Waiting on you

**Nothing is blocked on you on the automation side this interval.** The two
`permissions.ask` items from the previous page were resolved by your
2026-08-22 session and have been deleted here (their dispositions live in
§7 `OPS-18` / `OPS-16` and commits c724575 / 2b59199).

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
5. FYI, standing: the `docker-compose.yml` allow you granted is used only
   for `environment:` keys; §9 carries the written constraint that no chunk
   touches `volumes:`, the mount, or the 64 G limit — a chunk that thinks it
   must will stop and ask you here.

## Honest current state (digest of §2 — one line changed this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field (MAG-13, 3.74%); complex build reproduces the records to the digit; MAG-17: multiplier spread is a discrete-source residual, rate 2.4476 |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power 3.63% (TH-10); degree-2 gated at 0.1405% (TH-12/EX-25) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6); no affordable 64 MHz bracket on this box (adjudicated 08-18); Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil; GEO-17's region policy (+10.7% coil recovery) is the meshing leg of the road there |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus only; **the birdcage mesh now has terminals and port sheets (GEO-18 ✅ 08-22) but no port has been solved on it** — PORT-9 step 3 leg (c) is queued (§9 item 4); §2.2's "no coil has ports" stands |
| Test-suite trust | ✅ reconciled | OPS-17 closed 08-21: 216/232 runnable validation tests observed in the complex build; 2 files deferred with named reasons. The baseline OPS-18 re-gates against |

## Recent activity (2026-08-21 18:00 → 2026-08-22 03:00)

- **19:30:** `OPS-18` step 1 ⛔ on `Edit(docker/**)`; fell through to
  `GEO-18` step 2 — both tests green on one rank, exit 124 (an `allreduce`
  inside `if rank == 0`), parked.
- **21:00:** `GEO-18` step 2 resumed with the one-line hoist and **closed,
  and with it `GEO-18`**: sheet area = `dx·g` at 1.000000000000 on all four
  ports, `w = A/h` = bbox width, half-volumes 0.500000000000, C4 spread
  8.5e-16; step 1's terminals re-asserted. 53 s + 186 s regression.
- **22:30:** **`EX-27` closed** as written on the first run — the
  region-resolution policy example (`mesh:5`), policy coil recovery
  0.8356/0.8337 vs the 0.755 floor the clamps-only mesh is asserted to
  miss; measured smoke (8 s).
- **00:00:** drained by rule; re-probed the permission block (byte-identical)
  and promoted it on this page.
- **Your interactive session (08-22):** `OPS-16` closed won't-fix;
  `OPS-18` unblocked by narrowing the docker Edit rule.
- **This review:** both closes audited COMPLIANT (one transparency note on
  GEO-18's control, closed by the new `EX-28` commission); the landed
  `attempt/GEO-18-step2` branch deleted; `PORT-9` step 3 split into legs
  (c)/(d) with a one-column C4 anchor; `EX-28` commissioned; queue restocked
  to five.

## Automation health

- Container healthy (Up 4+ days on 0.7.2, no OOM, no wedge). Tree clean at
  every handoff; no `attempt/*` or `recovered/*` at review time.
- **Expect `attempt/OPS-18` to appear and persist** — it is the sanctioned
  worksite for the upgrade; `main` keeps booting 0.7.2 until step 3 is
  green, and OPS-18 slots restore the 0.7.2 container before they end.
- Launch failures (credits, API 500/529) are now journalled as cost only
  (`OPS-16` won't-fix); no retry logic is being built.
- Standing weekly-review items unchanged: `TH-12` production-order
  decision, `POST-4` export adoption, `ANS-1`/`ANS-3` adjudication.

## On deck (§9 — restocked this review, five items)

1. **`OPS-18` step 1** — build & boot DolfinX `v0.11.0.post0`
   (on `attempt/OPS-18`; `main` keeps 0.7.2 until step 3 is green)
2. **`OPS-18` step 2** — API migration (migration pack tracked in-repo;
   expect more than one slot)
3. **`OPS-18` step 3** — re-gate every §2.1 number in both builds (heavy;
   a moved gated number is a finding, not a tolerance problem)
4. **`PORT-9` step 3 leg (c)** — first port solve on the gapped birdcage:
   priced, one driven port, C4 adjacent-pair identity on one column of Z
5. *(spare)* **`EX-28`** — gapped-birdcage mesh example with terminals and
   port sheets (`GEO-18`'s capability; also asserts the facet absence
   GEO-18's control only implied)

Items 1–3 are strictly serial; 4–5 run on the unchanged 0.7.2 container
regardless of upgrade progress.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
