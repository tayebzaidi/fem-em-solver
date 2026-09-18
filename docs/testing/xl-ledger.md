# XL-tier ledger — one run per week, 512 GiB / 16 ranks / 2 h

Operator directive 2026-09-05 (interactive session; PROJECT_PLAN §5.1). The
`fem-em-solver-xl` compose service (profile `xl`, 512 G limit) exists for
**one** run per 7 days, commissioned **only by the weekly planning review**,
which names the chunk and its pre-registered readout. The bash guard
(`scripts/automation/hooks/bash_guard.py`) reads the most recent date in this
table and denies any XL command inside 7 days of it; `run_and_log.sh` appends
the row automatically when a harness command targets the XL service. Fill in
the last four columns by hand from the log after the run, and commit the row
with the log.

| Date (UTC) | Chunk | Log | Ranks | Cells | Peak memory (GiB) | Elapsed (s) | Readout |
|---|---|---|---:|---:|---:|---:|---|
| 2026-09-09 | ANS-4-step2b | `20260909T143756Z_ANS-4-step2b.log` | 16 | 116 085 | ~16.6 observed (see note) | 249 | degree 2 moves the three C4 classes of S at 128 MHz by **6.0900 / 5.3841 / 6.6959 %** off the degree-1 record; all imported gates green on both rungs, degree-2 class spreads *tighter* (0.0191–0.0334 % vs 0.0654–0.1012 %). **The slot was not needed:** 249 s against the predicted 1 100–1 300 s and ~16.6 GiB against ≳ 49 — this case fits the heavy tier and the ordinary 128 G service. |

**Note on the memory column (2026-09-09).** The step-2b module carries no
in-run `ru_maxrss` print, so 16.6 GiB is a `docker stats` reading taken by the
operator's interactive session while the degree-2 solve was running, **not a
measured peak** — the true peak is at or above it and was not instrumented. Any
future XL commissioning that leans on this figure should print `ru_maxrss`
instead. It is nonetheless a decade under the ordinary service's own 128 G
limit, which is the load-bearing part: this run did not need the tier.
| 2026-09-09 | TH-11-step5d | `20260909T145530Z_TH-11-step5d.log` | 8 | 2 808 204 | 260.9 (spot) | — | **KILLED, no footer — uncountable.** Wrapper killed at ~40 min; the container-side `timeout`/`mpiexec`/8 ranks survived it with nothing consuming their output, so the run could produce no evidence and was stopped. Only durable reading: 260.9 GiB from the cgroup. Cause and the three fixes: `OPS-43`. |
| 2026-09-09 | TH-11-step5d | `20260909T153910Z_TH-11-step5d.log` | 8 | 2 808 204 | 263.4 (container lifetime — spans the killed attempt, see note) | 4838 | **17 passed / 1 skipped, Status 0 — the rung solved for the first time.** Loaded 2331.7 s + free 2257.6 s. 64 MHz ladder h 0.005 → 0.0025 → 0.00125: **+10.2698 % → +2.8063 % → +0.3824 %**; three-rung fit **p = 1.623, d₀ = −0.7834 %**; two-rung bracket **[−2.0415 %, −0.4256 %]**, overlapping step 4's 10 MHz [−2.1492, −0.9050] and 30 MHz [−3.3675, −0.3812]. |

**Note on the 2026-09-09 peaks.** Both rows share one container lifetime
(started 14:55:23Z, before the first attempt), and `memory.peak` cannot be reset
on this kernel, so **263.4 GiB is the maximum over both runs**, not this run's
own peak. Same workload at the same rank count, so the figure is representative
— but it is not attributable, and §5.1 now requires restarting the service
before an `xl` window so the next one is.
| 2026-09-10 | ANS-4-step2d | `20260910T151845Z_ANS-4-step2d.log` | — | — | — | 0 | **DID NOT START — no compute, no slot spent in substance.** `docker compose` was permission-denied from inside `xl-run.sh` (the socket is reachable from a direct agent command but not from a script in the sandbox); the window died in 0 s *after* the harness had already appended this row. Row kept because the ledger records attempts, not successes. `xl-run.sh` now preflights docker before anything consumes the slot. |
| 2026-09-10 | ANS-4-step2d | `20260910T152049Z_ANS-4-step2d.log` (footerless; full output recovered to `20260910T180911Z_ANS-4-step2d-capture.log`) | 16 | 592 744 (finest rung) | **290.2** (clean — service restarted immediately before the window) | 7225 | **14 passed / 1 failed in 7225.01 s (2:00:25).** Ladder h=0.015 deg 1 → h=0.015/0.0075/0.005 deg 2 at 116 085 / 116 085 / 281 728 / 592 744 cells and 0.14 / 0.74 / 1.80 / **3.79 M unknowns**; four drives 12.0 / 169.0 / 1119.2 / **5653.5 s**. The three C4 classes of `S` move monotonically with both order and `h` and the degree-2 sequence converges (successive change 1.19 % → 0.62 %, ratio 1.90). The single failure is a defect in the ladder module's refinement control, not physics — it compared two rungs sharing one mesh (`116085 > 116085`); fixed the same day, every physics gate passed. Ran 25 s past the 2 h ceiling and completed only because the deadline was lifted by hand. |
| 2026-09-16 | ANS-4-step3 | `20260916T070008Z_ANS-4-step3.log` | 16 | 592 744 (degree-2 rung; ×1 rung 116 085) | **280.8** (`memory.peak` 301 547 610 112 B; service recreated before the window, so attributable; summed `ru_maxrss` 282.3) | 1658 | **16 passed, Status 0 — the first FIFO-queued window, run by cron with no session.** 64 MHz, `RUNGSPEC="0.015:1 0.005:2"`: degree-2 rung 3.79 M unknowns, mesh 105.7 s, four drives 1476.9 s (the 2000–3000 s prediction beaten — `PORT-19` reuse); imported `PORT-11` gates green (reciprocity 1.6e-14, σ_max 0.999758, spreads 0.1985 / 0.1715 / 0.1946 %). Degree 1 → 2 move on the driven column **6.51 / 2.60 / 4.11 %** (self / adjacent / opposite; 128 MHz step 2d: 6.09 / 5.38 / 6.70 %). Private AED miss and decision rule: the 09-19 weekly's (`xl-pending.md` entry 2). Columns filled by the 2026-09-16 03:00 review. |
| 2026-09-17 | ANS-4-step3b | `20260917T070008Z_ANS-4-step3b.log` | | | | 1539 | |
| 2026-09-18 | ANS-4-step3c | `20260918T070008Z_ANS-4-step3c.log` | | | | 1603 | |
