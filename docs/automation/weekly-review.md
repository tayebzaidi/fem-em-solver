# Weekly planning review protocol (scheduled)

*Model: `scripts/automation/review-model.env` (dated override, self-expiring —
see CLAUDE.md § Scheduled automation). High effort.*

Run by `scripts/automation/weekly-review.sh` via cron **once weekly, Saturday
21:00 local** (wind-down schedule, operator directive 2026-09-13; canonical
crontab `scripts/automation/crontab`). It was Sunday and Wednesday 02:15
until then: the Sunday session exhausted the account's 5-hour allowance in
~20 min on both 09-06 and 09-13 and took the 03:00 review and two slots with
it, so it now runs in its own window — Saturday's slots are long done, the
Saturday XXL result is in the ledger, and it ends by 02:00 Sunday. The
Wednesday run is dropped; what the plan calls "the 09-16 weekly" is the
09-19 one. One session, documentation work only — **no solves, no meshing**;
reading harness logs is fine.

*(Wednesday added 2026-09-01 by operator directive. Reason: the daily review
can only queue items whose anchors exist, and several anchors are
weekly-owned — on 2026-09-01 that left it honestly two items short and two
implementer slots drained. Splitting the interval 3/4 days refills the
long-horizon queue mid-week instead of only at the week boundary.)*

**"This week" means "since the last weekly-review commit", not seven days.**
Both runs are the same protocol; the interval between them is 3 or 4 days,
so step 2's pace arithmetic must divide by the **measured** elapsed time
taken from `git log`, never by an assumed week. A rate extrapolated from a
3-day window as if it were 7 is exactly the kind of unmeasured estimate the
realism rules below delete on sight. Everything else — archive rotation,
examples ramp, benchmark commissioning — is interval-driven already and
needs no adjustment.

You are the project's **long-horizon planner**. The division of labour is
strict and two-way:

- **You own** §1 fidelity, the §6 phase map, §10's long-horizon roadmap
  (phases, subgoals, dated assessments), examples/ health policy, and Ansys
  benchmark commissioning and adjudication (§5.4).
- **The daily review owns** §7 chunk entries and the §9 On-deck queue. Do not
  edit §9. Where a subgoal needs implementer work, express it as a §7 chunk
  (stable ID, §4-compliant done-when) and let the daily review queue it.
  One carve-out: compressing a **closed** chunk's §7 narrative into a
  result block (step 6 below) is weekly-owned hygiene; editing open
  chunks' status/done-when/plans, and anything in §9, remains the daily
  review's.

Subagents are available and web tools are not — same economics as the daily
review: this session never solves, so subagents cost tokens, not cores. Use
them for the read-heavy sweeps (pace measurement, examples audit); keep the
judgement calls — what to kill, what to rescope, what a comparison result
means — for yourself. Six named agents exist in .claude/agents/ (`auditor`,
`log-pathologist`, `plan-navigator`, `mesh-probe`, `example-runner`,
`record-reconciler`); during the examples-audit sweep, flag any agent file
whose "Last verified against" footer is older than ~30 days. First review
after 2026-09-01: measure agent value — (a) demotion catch rate; (b)
pathologist OVERRULED/UNCOUNTABLE rate; (c) review completion vs the
2-of-3-died baseline; (d) navigator citation error count; (e) example-runner
closures audited vs implementer-run baseline (the Sonnet-tier experiment).
If reviews still die on limits, drop the pathologist to sonnet before other
mitigations.

## Steps

1. **Establish the week.** `git log` since the last `docs(plan): weekly
   review` commit (or 7 days if none): chunks/steps closed vs opened, the
   daily-review commits, growth in `docs/testing/test-results.md`, attempts
   parked, known-issues opened/retired.

2. **Measure pace, brutally.** Count §4-closed steps this week and attribute
   each to a §10 phase. Extrapolate the current phase's completion from the
   measured rate — write the number down even when it is embarrassing, with
   the arithmetic. No date may appear in §10 without a pace measurement
   behind it. If the extrapolation says a phase goal is more than ~a quarter
   away at current pace, that is a scoping problem to fix now (cut the goal,
   not the honesty).

2b. **Progress against cost — one dated section, ending in a decision**
   (added 2026-09-19, operator-approved, from an external code review).
   Step 2 measures how fast chunks close; this step asks whether the
   closures, the windows and the slots were *worth what they cost*, and
   forces one call. Run

   ```
   scripts/testing/run_and_log.sh WEEKLY-COUNTS "timeout -k 30 30 python3 scripts/automation/weekly_counts.py"
   ```

   and read the block from the log it names. (Through the harness because a
   bare `python3` is not on the headless allowlist and would be refused; the
   log is also the durable record of the counts.) It is
   read-only, < 1 s, no solves — counts from the launcher logs,
   `test-results.md`, both ledgers, `attempts.md` and `git`, over the same
   "since the last weekly-review commit" interval as step 1 (this session's
   own commits, younger than 12 h, are skipped). **Append**
   one section headed `## YYYY-MM-DD` to `docs/status/weekly-progress.md`:
   the script's block pasted verbatim, then these rows written by you, each
   ≤ 3 lines and each citing a chunk ID, a `log:line` or a commit:

   - **Newly supported workflows** — end-to-end capability a user could now
     run that they could not last week. "None" is the expected answer most
     weeks; a closed component gate is not a workflow, and per-workflow
     parity wording (realism rules below) applies.
   - **Uncertainties resolved** — questions that now have an answer,
     *including negative ones*: a record that says "flat in f", a cost
     probe that prices a family out, an `ANS-*` adjudication either way. A
     negative result that stops work is progress and is listed as such.
   - **Defects retired** — known-issues entries retired, by name.
   - **Repeated failure** — anything the script flags with ≥ 2 non-complete
     entries, plus any chunk that took ≥ 4 entries: say in one line *why*
     it keeps costing slots (a wrong estimate, an executor's first pass
     needing rework, a blocked prerequisite).
   - **Lost slots** — sessions that did not end `ok`, with the cause where
     the log gives one.
   - **Cost** — the script's compute and session figures stand as printed.
     Anything it prints as `unavailable` stays `unavailable`: never
     estimate tokens, never back-fill core-hours from memory.
   - **Decision** — exactly three lines: **Continue** one activity,
     **Change or stop** one activity, and the **evidence** for each from
     the rows above. If the honest answer is "stop nothing", say what
     evidence next week would change that. The stop call is carried out
     through your own instruments — a §10 epitaph, a rescoped subgoal, an
     `xl-pending.md` entry superseded — never by editing §9.

   **No single score, and three numbers are not success:** commit count,
   queue depth (the §9 slot-minutes floor and the XL backlog floor exist to
   avoid idle windows, not to be filled for their own sake) and machine
   time spent. Report what each XL / XXL window *decided*, never how many
   ran. Keep the section to about a screen; it is a report, not an
   analytics project — if a row needs a sweep to fill, write "not
   measured this week" and move on. Commit it on its own as
   `docs(plan): weekly review YYYY-MM-DD — progress vs cost` (step 6's
   commit-first rule).

3. **Audit the roadmap against the mission.** Is §10's phase/subgoal
   structure still the shortest path to §1 (AED-parity for the MRI-safety
   workflow: construct → tune at 64/128 MHz → drive with saline phantom ±
   implant → safety quantities; bioheat long-term)? Rescope or kill any
   subgoal that has not moved in a month. Add subgoals only where a phase
   lacks a next step concrete enough for the daily review to break down.
   Keep the §6 phase-map states current. **Keep every active §10 chain
   enumerated at least three open numbered steps ahead** (operator directive
   2026-09-18): the daily review executes chain steps under §9 rule (4), so
   a chain with no open numbered step is a week of slots draining into
   figures. Each chain step names its validation target and its serial
   prerequisites; the daily supplies the rest.

3b. **Spend the XL slot, or explicitly do not.** §5.1's `xl` tier (operator
   directive 2026-09-05) is one run per 7 days at ≤ 512 GiB / 16 ranks / 2 h (since 2026-09-13: 4 h)
   against `fem-em-solver-xl` (since 2026-09-13: six per trailing 7 days — nightly —,
   02:00 Sun–Fri, plus the **`xxl`** tier — 754 GiB / 16 ranks / 8 h, one per
   trailing 7 days, 02:00 Saturday), and **this review is the only thing
   that decides what runs in them.** Since 2026-09-13 (operator directive)
   the decision and the queueing are split: you **pre-register** every
   window you commission in `docs/testing/xl-pending.md` — tier, chunk and
   step, the exact `XL_COMMAND`, the *measured* price from a priced
   smaller rung (no window without one, §5.1), the readout, and what each
   outcome decides — and the daily review, as clerk (daily-review.md step
   6b), copies every `READY` entry into `docs/testing/<tier>-queue.d/`
   (a FIFO the launcher drains one file per night, 2026-09-15) as the
   ledger budget allows, so all six XL windows and the XXL window can be
   used in a week you run once. Fill the list to the budget: up to six
   `xl` entries and one `xxl` entry ahead. Since 2026-09-15 the daily
   review also holds a **backlog floor** (≥ 4 `xl` and ≥ 1 `xxl` ahead)
   and a narrow licence to fill it with priced-family variants and cost
   probes (daily-review.md step 6b.4); read what it wrote, keep or
   supersede it, and own everything outside that licence. Read both ledgers and mark run entries. If nothing is ready for
   a tier, write "not spent" and why. Never split a window, never carry
   one over, never let an implementer commission one.

4. **Examples health.** `./run_examples.sh --list`; for each example, find
   its most recent verified run in `docs/testing/logs/` (or note there is
   none) and whether its XDMF outputs still reflect current capability.
   You may not solve — a stale or broken example becomes a §7 chunk with the
   staleness stated. §5.4's bar is a ramp: an in-progress phase owes
   `min(5, gating chunks closed ✅)` clean runnable examples, each
   demonstrating gated capability from a distinct angle (geometry, materials,
   drive, or output quantity), XDMF that opens in ParaView; a completed phase
   owes the full five. Count each phase against its ramp. The daily review
   enqueues an example chunk after each gate closure (daily-review.md step
   5), so a shortfall here means that mechanism missed — open the missing §7
   chunks yourself and state the per-phase count and shortfall in the
   review.

5. **Ansys benchmarks (§5.4), both directions.**
   - *Commission:* should a new `examples/ansys_benchmarks/<case>/` be
     opened? Yes only when a phase milestone has landed on **gated** physics
     since the last case. If yes: write the `SPEC.md` skeleton (geometry,
     materials, BCs, ports, frequencies, quantities to export — no judgement
     calls left to the operator) and a §7 chunk to implement the runnable
     half. Keep the case small enough that one AED session replicates it.
     A commissioned case that is ready for the operator to replicate goes at
     the top of the dashboard's Waiting-on-you list
     (`docs/status/dashboard.md`, daily-review.md step 7) — that list is how
     the operator learns about it.
   - **AED numbers are private (operator directive 2026-09-02).** Ansys
     licence terms restrict disclosure of benchmark results, so they are
     never in a tracked file: read them from the case's gitignored
     `COMPARISON_private.md` / `aed_results/` on this box (absent on a fresh
     clone), write the numeric adjudication to the gitignored
     `docs/private/<case>-adjudication-<date>.md`, and put **only the
     qualitative verdict** (agree / disagree / inconclusive, and what it
     decides) into PROJECT_PLAN.md, the dashboard and the commit message —
     no AED R/X/ΔZ values, tet counts, pass counts, energy errors or timings.
   - *Adjudicate:* if any case gained AED numbers from the human
     operator since last week, adjudicate them now — agreements promote into
     §7 gates with the AED value as the reference; disagreements open a
     known-issues entry and a diagnosis chunk. A disagreement is a finding,
     never something to explain away.

6. **Plan hygiene.** If `PROJECT_PLAN.md` exceeds 4,000 lines, or any
   closed chunk or closed step carries more than ~50 lines of narrative,
   move the closed narrative **verbatim** to
   `docs/planning/plan-archive.md` (append, matching its entry-header
   format and preamble contract — never summarize into the archive), and
   leave a result block of ≤ 15 lines in §7: status, close date, the
   gated numbers, log IDs, live carry-forwards, and the archive pointer.
   Verify zero loss before committing: every removed line must appear
   verbatim in the archive (a set-difference check over non-blank lines
   is sufficient), and every § reference in CLAUDE.md and
   docs/automation/*.md must still resolve. Same treatment for
   `docs/testing/attempts.md`: entries older than **7 days** move verbatim
   to `docs/testing/attempts-archive.md` (was 14 until 2026-09-19: the
   rotation ran every week and the file was still 1.04 MB / 14 194 lines,
   because 14 days at ~12 entries a day *is* that much — measured, 220
   entries. Nothing reads further back than the interval since the last
   weekly; the archive is one grep away). **`docs/testing/known-issues.md`
   (added 2026-09-19):** every agent is told to check that file before
   debugging, and two thirds of it was retired entries — 451 KB of 669 KB.
   Move them out each week, mechanically:

   ```
   scripts/testing/run_and_log.sh WEEKLY-ROTATE "timeout -k 30 30 python3 scripts/maintenance/rotate_plan_archive.py known-issues YYYY-MM-DD"
   ```

   (through the harness: a bare `python3` is not on the headless allowlist).
   The tool moves every entry whose heading says RETIRED / RESOLVED / FIXED /
   CLOSED to `docs/testing/known-issues-archive.md`, verbatim, runs the
   zero-loss check itself, and leaves one index line per entry so a grep for
   a test name still lands. It is a no-op when nothing is retired. A §7 row whose
   history already moved to `docs/planning/chunks/<ID>.md` (`OPS-46`,
   `rotate_plan_archive.py chunks`) keeps that file where it is when the
   chunk closes — closed chunks' files are not rotated into
   `plan-archive.md`; this rotation is otherwise unchanged.

   **Commit-first checkpoint (added 2026-08-30).** Do the rotation
   **before** any other edit in this session and commit it on its own as
   `docs(plan): weekly review YYYY-MM-DD — archive rotation` the moment
   the zero-loss check passes. Then, after each of steps 3–5 lands a
   file, `git add` it and amend nothing — commit again as
   `… — <step name>` if the step's output is complete, otherwise leave it
   staged. Reason: the 2026-08-30 02:15 session wrote ~10 000 lines across
   seven files between 02:19 and 02:52 and died before its single commit;
   the dirty tree tripped the 04:30 slot's preflight, was parked by the
   06:00 slot, and every implementer slot until the 10:30 daily review
   found a drained §9 — five implementer slots and two review slots lost
   to one un-checkpointed session (attempts.md `2026-08-30T09:31Z` …
   `T14:00Z`). Several small commits are cheaper than that; §5.2's
   audit-note prohibition is about content-free commits, not about
   checkpointing real work.

7. **Commit** the remainder as `docs(plan): weekly review YYYY-MM-DD`. If
   nothing needs changing, commit nothing — §5.2's audit-note prohibition
   applies here too.

## Realism rules (the reason this review exists)

- **Measured pace or no estimate.** Every dated assessment cites the week's
  closure count and the arithmetic. "On track" without a number is deleted
  on sight.
- **Per-workflow parity claims only.** "Tunes a shielded 8-rung birdcage at
  128 MHz to within X of AED" is a claim; "HFSS parity" is not.
- **A goal names its validation target** — closed form, published
  measurement, or AED comparison — or it is not a goal yet, and writing the
  target is the subgoal.
- **Kill stalled subgoals in writing.** A subgoal rescoped or killed gets a
  dated one-line epitaph in §10 saying why; silent deletion hides the lesson.
- **Do not let scaffolding outrun physics.** The ⚠️ backlog came from
  building features on a proxy (§2). A phase may not open implementation
  subgoals while its predecessor's validation gate is red.

## Constraints

- §9 On deck belongs to the daily review; never edit it here.
- Never loosen a test bound, a done-when, or a §10 criterion to make history
  look better.
- known-issues.md discipline applies.
- Your session transcript is not durable; anything worth keeping goes into
  the repo in this session's commit.
