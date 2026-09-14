# Daily review protocol (scheduled)

*Model: `scripts/automation/review-model.env` (dated override, self-expiring —
see CLAUDE.md § Scheduled automation). Medium effort.*

Run by `scripts/automation/daily-review.sh` via cron **once on each active
day** (03:00 local, Sun/Mon/Wed/Fri/Sat — **Tuesday and Thursday are off**;
wind-down schedule, operator directive 2026-09-13, canonical crontab
`scripts/automation/crontab`), followed by four implementer runs at 04:30 /
06:00 / 07:30 / 09:00. "Since the last review" therefore spans a day, or two
across an off day; the restock floor is still one four-slot interval. One
session, documentation work only — **no solves, no meshing**; reading harness
logs is fine. You are maintaining the plan, not executing it.

**Subagents are available to you, and web tools are not.** Because this session
never solves or meshes, a subagent costs tokens rather than cores and does not
touch the 12-core compute budget. Use them for the mechanical, parallel, read-
heavy work — one `auditor` (.claude/agents/auditor.md) per newly-✅ chunk in
step 3, a `log-pathologist` ruling on any disputed or status-changing log
reading in step 4, `plan-navigator` for plan/known-issues lookups instead of
paging those files yourself, an `Explore` sweep when
step 5 asks whether the backlog still reaches §10 — and keep your own context
for the judgement calls: what a negative result means, and what to queue next.
A subagent's report is evidence, not a verdict; if one says a chunk passes §4,
the log it cites is what you cite back in the commit. Do not delegate steps 2,
6, 7, or 8 — disposition, queue order, the dashboard refresh, and the commit
are yours.

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
   with a dated note. Do not re-run anything. A chunk's evidence is its §7
   row **plus** its history file `docs/planning/chunks/<ID>.md` when the row
   points to one (`OPS-46`); the auditor reads both. Delegate each audit to the
   `auditor` agent; treat its DEMOTE/PASS as evidence and re-cite its
   log:line evidence yourself in the review commit. Through 2026-09-03:
   re-verify one cited claim per agent report (a random digit trace) before
   acting on it; this clause expires on its own after that date.

4. For each incomplete attempt (attempts.md entries + `attempt/*` branches):
   diagnose from the logs and the parked diff; rescope the chunk's §7 entry —
   smaller case, sharper implementation plan, or split into two chunks — and
   record the diagnosis in the entry. Delete an attempt branch only when its
   useful content is fully captured in the plan. Before banking a diagnosis
   whose log reading is surprising or changes a status, get a
   `log-pathologist` ruling; UNCOUNTABLE means diagnose from the parked diff
   only.

5. Assess against §10 success criteria: does the existing backlog still lead
   to the mission? If a gap exists, add new chunk entries (stable IDs,
   §4-compliant done-whens, implementation plans meeting the rubric below).
   If no gap exists, do not invent work. **Scope boundary:** the §6 phase map
   and §10's long-horizon roadmap (phases, subgoals, dated assessments)
   belong to the weekly planning review (docs/automation/weekly-review.md) —
   add chunks *within* the current phase's subgoals; do not restructure
   phases or edit the roadmap here.

   **Example chunks (§5.4 ramp):** for each chunk that newly closed a
   quantitative gate since the last review (the step-3 list, post-audit),
   check whether an existing example already demonstrates that capability;
   if not, add a standalone example chunk to §7 — sized for one implementer
   run, executed via `./run_examples.sh`, producing combined-XDMF that opens
   in ParaView, and demonstrating the capability from an angle no existing
   example covers (geometry, materials, drive, or output quantity). Example
   chunks are never riders on physics chunks and never target ungated
   capability.

6. Refresh **"On deck"** in §9. **The restock floor counts slot-minutes, not
   items (operator directive 2026-09-13, on the weekly review's finding):**
   the queue must carry **≥ 240 predicted slot-minutes** of open, unblocked
   work — the four runs before the next review — **and ≥ 5 items** (the
   spare). An item's predicted slot-minutes are its costed wall clock from
   rubric element 3 (every verification window, not just the solve) **plus
   15 min** of fixed cost (onboarding, journal, commit). Write the running
   total beside the list. Since 2026-09-12 a slot that commits its item with
   a clean tree before minute 30 takes the next one (implementer-run.md
   step 2), which is why five items is not a floor any more: on 09-12 a
   five-item queue of cheap serial moves lasted two slots and three further
   slots drained with every review alive. Each item is still sized for one
   run (≤ 1 h wall clock, ≤ 20 min per compute command, ≤ 12 ranks) and
   ordered; independent items first. If the ready items do not reach the
   floor, list what exists, **state the shortfall in minutes**, and say so —
   step 5 still forbids inventing work, and a visible shortfall is the
   signal the weekly needs. Each listed item meets the rubric below; an item
   that cannot yet state its anchor is not ready to queue, and writing that
   anchor is itself the better queue item.

   **The family cap (operator directive 2026-09-12, four attempts).** A
   *step family* is a numbered step plus all of its lettered sub-steps
   (`4`, `4a`–`4k` are one family). Count the attempts since the last
   sub-step in the family that landed a gate — an asserted, pre-registered
   anchor that moved a §7 status, retired a known-issues entry or registered
   a record; a green run of *imported* gates does not count. **At four, the
   family is frozen**: this review must either re-scope the question at a
   higher altitude as a *new numbered step* or bank the measured negative and
   close the question in the §7 row and known-issues — it may not queue a
   fifth letter. Relettering does not reset the count; a landed gate does.
   The rule replaced §9's "fails twice" rule, which never fired because every
   reletter was formally a new item (`WF-6` step 4 ran twelve).

   **Prefer independent items over a dependency chain.** Four runs will take
   items 1–4 in order without waiting for each other's results, so an item
   that only works if the item above it landed will fail for reasons that are
   not about that item. Where the critical path is genuinely serial, say so
   explicitly in the item ("depends on item 1 landing; if it did not, skip to
   item 3") rather than leaving the run to discover it.

6b. **XL clerk (operator directive 2026-09-13).** Read
   `docs/testing/xl-pending.md`. For each tier whose
   `docs/testing/<tier>-queue.env` is empty: if the top `READY` entry's
   prerequisite has landed on `main` and the tier's budget allows — `xl`:
   fewer than six rows with non-zero `Elapsed` in the trailing 7 days of
   `docs/testing/xl-ledger.md`; `xxl`: none in the trailing 7 days of
   `xxl-ledger.md` — copy its `XL_CHUNK` / `XL_COMMAND` into the queue file
   **verbatim** (the Write tool, not a shell redirect — the guard trips on
   XL command text in a shell command), mark the entry `QUEUED <today> for
   <run date>`, and say so in the review commit. You never write an entry,
   never alter a command, never queue past the budget, never queue on a
   dirty tree. When a ledger has gained a row since the last review, mark
   the matching entry `RUN <log>`. The weekly still decides *what* runs;
   this step is the clerk that keeps zero-token compute from idling
   between weeklies. A `PENDING PREREQUISITE` entry's prerequisite is an
   ordinary §9 item — queue it in step 6 like any other.

7. **Refresh the status dashboard.** Rewrite `docs/status/dashboard.md` from
   what steps 1–6 established — Waiting-on-you first, then the §2 digest
   (only when §2 changed), recent activity, automation health, on-deck
   summary. Keep it a digest: no content that exists only there.

   The artifact republish is **interactive-only**: the Artifact tool is not
   available in headless scheduled sessions, so do not attempt it here —
   the file update is this step's whole deliverable. The published copy at

   `https://claude.ai/code/artifact/d5040a1e-ae6c-42dd-8e11-2330e0b9bbc8`

   is refreshed by the next interactive session (pass that URL as `url` so
   the link stays stable), and lags `docs/status/dashboard.md` until one
   runs — the operator confirmed this arrangement 2026-08-11 after the
   artifact was found six days stale. Anything blocked on the human
   operator goes at the
   top of Waiting-on-you — the dashboard is the only alerting channel; do
   not send push notifications. Dashboard staleness alone does not justify
   a commit — fold the refresh into a commit the other steps already
   earned, or skip it this interval.

8. Commit everything as `docs(plan): daily review YYYY-MM-DD`. If nothing
   needs changing, **commit nothing** — §5.2 explicitly prohibits audit-note
   commits, and that rule exists because of a 35-commit pile of them.

## Rubric: what a queueable item states

This is the standard the strongest items have already met — `PORT-1` step 1
named its closed form, its meshed-vs-nominal current correction, and the two
traps that had each cost a run, which is why it returned a decisive negative
inside one slot instead of a confused half-result. Below that bar, the
implementer spends its hour rescoping instead of measuring. Every item added in
step 5 or listed in step 6 states all six. An item whose chunk class has a
specialist executor (`example-runner` for EX-* example chunks, `mesh-probe`
for measurement-only mesh/resolution probes, `record-reconciler` for
version-bump record sweeps) says so in its first line:

1. **The anchor** — the specific closed form, conservation/reciprocity
   identity, or convergence rate the item will assert against, named with the
   symbol or the function that computes it (`utils/analytical.py`, a paper's
   kernel). "Check that it works" is not an anchor, and an item without one
   cannot close a chunk under §4.
2. **The negative control** — what a blind or broken solver returns on the same
   fixture, and the separation to assert. Compute the *ceiling* before naming a
   factor: `POST-3` step 2's blind imbalance saturates just under 100%, so
   1/0.1185 = 8.4× is arithmetically the most that fixture can show and a 10×
   bar would have been unreachable, not merely unmet.
3. **Tier, ranks, and expected wall clock** — smoke 30 s / standard 180 s /
   heavy 1200 s (never `xl`: that tier is the weekly review's to commission,
   §5.1), the rank count, and a cost estimate taken from a prior
   measurement where one exists (a probe's solve time, a comparable fixture).
   An item nobody has costed is an item that overruns.
4. **The traps already paid for** — name the failures this project has already
   bought, so the run does not buy them twice: `ufl.max_value` and any
   ordering comparison (`<=`) on complex-typed operands do not compile in the
   complex build — the error surfaces either as a UFL `ComplexComparisonError`
   or as a swallowed FFCx "root node" failure, and three fixture
   `current_density` callables carried it (`OPS-22`, 2026-08-19; regularise
   inside the `sqrt` instead) — and **real operands do not save a comparison
   that contains a `sqrt`**: UFL types `Sqrt` as complex whatever its
   argument, so `proj > sqrt(x² + y²)·c` on a real `SpatialCoordinate` raised
   the same error and cost a 400 s window (`WF-6` step 4c, 2026-09-08; compare
   squares — `proj > 0 ∧ proj² > (x² + y²)·c²`); a killed compile leaves a **0-byte `.c` stub**
   in `/root/.cache/fenics` that is a *live lock* — later runs (even in the
   same session) stall in `MPI_Bcast` or fail blaming the cache, and three
   windows went to it on 2026-08-18/19 — sweep
   `find /root/.cache/fenics -name '*.c' -size 0` and delete stubs only,
   never clear the cache wholesale (the targeted delete is also the
   diagnostic: a real defect re-creates its stub, a cache artifact does not); `cell_tags.values` and
   `assemble_scalar` are rank-local; pytest captures prints without `-s`;
   `-k a or b` splits into stray argv inside an already-quoted container
   command; a headless session that backgrounds a harness run and ends its
   turn exits the CLI and SIGKILLs the harness (footerless log, no journal —
   three slots on 2026-08-10/11): harness runs go foreground, Bash-tool
   timeout 660000 ms, container-side `timeout` sized to return a footer
   inside that window — and the same rule binds a **spawned executor's**
   windows and the slot that spawned it: on 2026-09-01 00:00
   `example-runner` returned with a `./run_examples.sh` window still
   running (killed host-side 267 s in, footerless, the container process
   orphaned), and the slot that ended its turn waiting for it was
   terminated by the CLI's 600 s background ceiling with no journal —
   spawn executors foreground, state the rule in the spawn prompt; the
   container-side `timeout` needs `-k 30` — a plain
   TERM does not reliably stop an `mpiexec` job, and an overrun can wedge
   the container (MAT-6 step 10, 2026-08-12; recovery is
   `docker compose up -d --force-recreate`); piping pytest through
   `grep -v` (or anything) inside the harness command makes the log
   footer record the pipe's exit status, not pytest's — two OPS-17
   step-2 footers show exit 0 over a failing and a killed run
   (2026-08-17); filter after the fact, never in the pipeline; a
   `SpatialCoordinate`-bearing facet integral on a gmsh mesh without
   `metadata={"quadrature_degree": …}` can send FFCx into a compile that
   does not finish in nine minutes, and each killed window poisons that
   form's cache entry (`rm /root/.cache/fenics/*<hash>*` recovers; pin
   the degree — `POST-5` step 1, 2026-08-18, two windows); landing a
   parked branch by **path checkout** of an append-only record
   (`git checkout attempt/… -- docs/testing/test-results.md`) replaces
   the file and silently deletes every row `main` appended since the
   branch — `8d4cf58` (`TH-15` step 3b, 2026-09-09) dropped nine rows
   across four chunks, restored by the 2026-09-10 03:00 review; take
   code by path, append record rows by hand, and check
   `git diff --stat` shows only insertions on record files; a negative
   control that copies `HEAD:` of the file its change edits goes stale the
   moment that change lands — `test_orphan_guard.sh`'s control was red on
   every HEAD after `d10a940` and cost `OPS-43` (a)'s regression a window
   (2026-09-10 16:30); pin the pre-change commit (`<sha>^`) instead; an
   orphan-rank check spelled `pgrep -f "python3 -m pytest"` is **denied by
   `bash_guard.py`** (the string matches its pytest-routing rule) —
   `pgrep -c python3` inside the container is the check that runs
   (`TH-19` steps 1–2, 2026-09-10 22:30); a durable-capture command that
   drops the idiom's trailing **`; exit $rc`** exits with `cat`'s status, so
   the harness footer and test-results row read **0 over a failed pytest** —
   `WF-6` step 4h's red window (`[capture] rc=1`, `Status: 0`, 2026-09-11
   09:00); copy §5.1's idiom verbatim. Since `OPS-45` (2026-09-11 12:00) the
   footer honours a **final** `[capture] rc=` line, but an rc line followed
   by any further output is still ignored by design, so the trailing
   `; exit $rc` stays mandatory. Add to this list as runs discover
   more.
5. **The scope boundary** — what the item does *not* close, stated so the
   implementer holds the chunk at 🟡 rather than over-claiming. `POST-3` step 1
   correctly stayed 🟡 because a scalar-σ identity does not gate the coil+
   phantom case, which is where it would earn its keep.
6. **What a negative result means** — the disposition if the measurement comes
   back wrong or zero. The answer is always *report the measurement and stop*,
   never fabricate a gate around it or loosen a bound to swallow it; the item
   should say which artifact captures it (a §7 annotation, a known-issues
   entry, an `attempt/*` branch).
7. **The status its result can move** *(added 2026-09-12, operator
   directive)* — the §7 chunk row, §2 sentence or known-issues entry the
   measurement can change, and what result would change it (a glyph flip, a
   retired entry, a registered record, a re-pointed §2 clause). An item that
   cannot name one is a curiosity, not work, and the review declines to queue
   it — `WF-6` steps 4h–4k all diagnosed a rung the review had already
   removed from the ladder, four slots that could not move a status by
   construction. This is a filter applied while queueing, not a regret
   afterwards.

Prefer items where a negative result is still informative — those convert a
failed hour into a finding. `PORT-1` step 1 measured exactly-zero mutual
coupling and thereby found the unfragmented mesh that had been quietly
corrupting three other fixtures.

## Constraints

- AED benchmark numbers are private (CLAUDE.md hard rules): read the gitignored `aed_results/` / `COMPARISON_private.md` / `docs/private/` files if you need context, but never copy a number from them into a tracked file, a journal entry or a commit message.
- Never loosen a test bound or a done-when to make history look better.
- known-issues.md discipline applies: failures observed but not fixed get an
  entry; entries leave only with the commit that fixes them.
- Your session transcript is not durable. Anything worth keeping goes into
  the repo in this session's commit.
