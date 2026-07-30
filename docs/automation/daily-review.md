# Daily review protocol (Fable, scheduled)

Run by `scripts/automation/daily-review.sh` via cron **three times daily**
(03:00, 10:30, 18:00 local), each followed by four implementer runs on a shared
90-minute grid. "Daily" is historical; read it as "each review interval". One
session, documentation work only — **no solves, no meshing**; reading harness
logs is fine. You are maintaining the plan, not executing it.

## Steps

1. Establish what happened since the last review:
   - `git log` since the previous `docs(plan): daily review` commit (or 24 h
     if none exists)
   - new rows in `docs/testing/test-results.md` and logs in
     `docs/testing/logs/`
   - new entries in `docs/testing/attempts.md`
   - `git branch --list 'attempt/*'` for parked incomplete work
   - `git status --porcelain -uno` — dirty tracked files at review time mean
     every implementer run since they appeared has been tripping preflight

2. **Clear any stalled tree, and dispose of `recovered/*` branches.** A dirty
   tracked tree older than one implementer cycle (90 min) is an outage, not a
   curiosity, and this review is the scheduled actor responsible for ending
   it. Read the diff and the attempts.md anomaly entries about it, then
   resolve it now: commit the changes (accurate message, its own commit) if
   they describe reality, or revert them if they do not, and record which
   you did and why in the review commit. Documentation-only diffs that a
   prior run journaled as an anomaly should normally have been landed by the
   next implementer run (implementer-run.md step 1 exception); if one is
   still sitting here, also note why that didn't happen. Never leave the
   tree dirty at the end of the review.

   `git branch --list 'recovered/*'` lists trees a *second* implementer
   encounter parked rather than stopped for (implementer-run.md step 1). Each
   one is a change nobody has adjudicated: read it, then land it, fold it into
   a §7 entry, or delete the branch — and say which in the review commit. An
   accumulating `recovered/*` list means the tree keeps going dirty from a
   source nobody has found; name that in the commit rather than clearing it
   silently.

3. **Audit every chunk whose status changed to ✅ since the last review**
   against PROJECT_PLAN.md §4: does a harness log exist, was the verification
   executed by the agent itself, is at least one assertion quantitative
   (closed form / convergence rate / conservation, reciprocity, or symmetry
   identity), is elapsed time recorded? Demote anything non-compliant to 🧪
   with a dated note. Do not re-run anything.

4. For each incomplete attempt (attempts.md entries + `attempt/*` branches):
   diagnose from the logs and the parked diff; rescope the chunk's §7 entry —
   smaller case, sharper implementation plan, or split into two chunks — and
   record the diagnosis in the entry. Delete an attempt branch only when its
   useful content is fully captured in the plan.

5. Assess against §10 success criteria: does the existing backlog still lead
   to the mission? If a gap exists, add new chunk entries (stable IDs,
   §4-compliant done-whens, implementation plans with known traps named). If
   no gap exists, do not invent work.

6. Refresh **"On deck"** in §9: top it up to **at least 5** items not done or
   blocked — the 4 runs before the next review, plus one spare — ordered, each
   sized for one implementer run (≤ 1 h wall clock, ≤ 10 min per compute
   command). An item that has failed twice must be rescoped before it may be
   listed again. If fewer than 5 ready items exist, list what exists and say
   so — step 5 still forbids inventing work.

   **Prefer independent items over a dependency chain.** Four runs will take
   items 1–4 in order without waiting for each other's results, so an item
   that only works if the item above it landed will fail for reasons that are
   not about that item. Where the critical path is genuinely serial, say so
   explicitly in the item ("depends on item 1 landing; if it did not, skip to
   item 3") rather than leaving the run to discover it.

7. Commit everything as `docs(plan): daily review YYYY-MM-DD`. If nothing
   needs changing, **commit nothing** — §5.2 explicitly prohibits audit-note
   commits, and that rule exists because of a 35-commit pile of them.

## Constraints

- Never loosen a test bound or a done-when to make history look better.
- known-issues.md discipline applies: failures observed but not fixed get an
  entry; entries leave only with the commit that fixes them.
- Your session transcript is not durable. Anything worth keeping goes into
  the repo in this session's commit.
