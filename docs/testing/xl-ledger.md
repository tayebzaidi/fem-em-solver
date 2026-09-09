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
