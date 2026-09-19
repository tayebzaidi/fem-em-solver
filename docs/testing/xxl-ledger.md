# XXL-tier ledger — the Saturday window, one run per week, 754 GiB / 8 h

Operator directive 2026-09-10 (PROJECT_PLAN §5.1). The `fem-em-solver-xxl`
compose service (profile `xxl`, 754 G limit) exists for the cases a 2 h `xl`
window cannot hold. Commissioned like `xl` — by the weekly planning review or
the operator, with a pre-registered readout — and gated by the same guard,
which counts the rows below against a budget of **one per trailing 7 days**.

`run_and_log.sh` appends the row when a window **starts**, so a killed or
failed run has still spent the week. Fill the last four columns by hand from
the footer and commit the row with the log.

Why 754 GiB: this WSL VM's whole allocation, half of the machine's 1.5 TB. A
container limit equal to the VM's total memory means the kernel OOM killer
reaches a runaway before the cgroup does — recorded in `docker-compose.yml`
rather than silently softened.

| Date (UTC) | Chunk | Log | Ranks | Cells | Peak memory (GiB) | Elapsed (s) | Readout |
|---|---|---|---|---:|---:|---:|---|
| 2026-09-19 | WF-7-step0b | `20260919T070008Z_WF-7-step0b.log` | 16 | 507 266 (both legs; vs the 504 642 record, rel 5.200e-03, INSIDE the imported 1 % band — the window's only assertion, `:10603`, `:21174`) | **106.1** (`memory.peak` 113 950 359 552 B, `:21181–21182`, a high-water mark over both legs; degree-2 summed `ru_maxrss` 107.917, max rank 7.851, `:21172`) | 673 | **Both legs rc 0, `[capture] rc=0` last, Status 0** (`:10607`, `:21178`, `:21183–21188`); orphans 0 before and after (`:35–36`, `:21179–21180`); command identical to the queue file. Filled by the 2026-09-19 03:00 review from a `log-pathologist` reading (CONFIRMED countable; a real solve, not a stop branch), lines re-read by the review. **Degree 1 (control, `-n 16`):** 607 039 unknowns, solve (assemble + factorise + solve) 24.61 s, cumulative 166.77 s, summed `ru_maxrss` 13.419 GiB (`:10600–10601`); `S_driven(P17)` `0.407423+0.344417j` — step 0's `-n 8` digits to the last printed place, **printed, not asserted** at this width (`:10602`). **Degree 2:** **3 256 418 unknowns** (ZMUMPS `N`, `:20998`), factorisation 242.5 s (`:21112`), solve 347.56 s = 5.79 min, cumulative 497.05 s (`:21169–21171`); `S_driven(P17)` `0.436656+0.346994j` (`:21170`). **The price is about a third of the prediction on both axes** (≈ 235 GiB / ≈ 17 min predicted; the probe prints OUTSIDE, *below*, on both brackets) — decision-rule branch (c) does not fire. **Public readout (the review's arithmetic from the two printed values, not a probe print):** `|S₂ − S₁| / |S₁|` = **5.50 %** (magnitude +4.54 %). **One reading the weekly should not miss:** the printed, never-asserted power-accounting residual is **1.104e-02 at degree 2 against 4.187e-03 at degree 1** (`:21170`, `:10599`) — 2.6× *worse* at the higher order. Not attributed; nothing about the degree-2 `S` is asserted. Label defects in this log (known-issues 2026-09-19, `OPS-52`): the degree-2 leg prints `phase 4 flag-off control … vs the step-0 record` over the order-sensitivity readout (`:21173` — not a drift red), the degree-1 time bracket 3–8 min has never been met (24.61 s here, 37.02 s at step 0), and `solve … (solve)` dropped step 0's "(assemble+factorise+solve)" qualifier. Branch (a) vs (b) is the 09-19 weekly's. |
