# Weekly planning review protocol (Fable 5, scheduled)

Run by `scripts/automation/weekly-review.sh` via cron **weekly** (Sunday
01:30 local, in the buffer slot before that day's 03:00 daily review; the
shared flock prevents overlap). One session, documentation work only — **no
solves, no meshing**; reading harness logs is fine.

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
means — for yourself.

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

3. **Audit the roadmap against the mission.** Is §10's phase/subgoal
   structure still the shortest path to §1 (AED-parity for the MRI-safety
   workflow: construct → tune at 64/128 MHz → drive with saline phantom ±
   implant → safety quantities; bioheat long-term)? Rescope or kill any
   subgoal that has not moved in a month. Add subgoals only where a phase
   lacks a next step concrete enough for the daily review to break down.
   Keep the §6 phase-map states current.

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
   - *Adjudicate:* if any `COMPARISON.md` gained AED numbers from the human
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
   `docs/testing/attempts.md`: entries older than 14 days move verbatim
   to `docs/testing/attempts-archive.md` (create it with a one-paragraph
   preamble mirroring plan-archive.md's on first use).

7. **Commit** as `docs(plan): weekly review YYYY-MM-DD`. If nothing needs
   changing, commit nothing — §5.2's audit-note prohibition applies here
   too.

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
