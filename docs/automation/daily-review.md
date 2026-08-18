# Daily review protocol (Fable 5, scheduled)

Run by `scripts/automation/daily-review.sh` via cron **three times daily**
(03:00, 10:30, 18:00 local), each followed by four implementer runs on a shared
90-minute grid. "Daily" is historical; read it as "each review interval". One
session, documentation work only — **no solves, no meshing**; reading harness
logs is fine. You are maintaining the plan, not executing it.

**Subagents are available to you, and web tools are not.** Because this session
never solves or meshes, a subagent costs tokens rather than cores and does not
touch the 12-core compute budget. Use them for the mechanical, parallel, read-
heavy work — one auditor per newly-✅ chunk in step 3, an `Explore` sweep when
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
   with a dated note. Do not re-run anything.

4. For each incomplete attempt (attempts.md entries + `attempt/*` branches):
   diagnose from the logs and the parked diff; rescope the chunk's §7 entry —
   smaller case, sharper implementation plan, or split into two chunks — and
   record the diagnosis in the entry. Delete an attempt branch only when its
   useful content is fully captured in the plan.

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

6. Refresh **"On deck"** in §9: top it up to **at least 5** items not done or
   blocked — the 4 runs before the next review, plus one spare — ordered, each
   sized for one implementer run (≤ 1 h wall clock, ≤ 20 min per compute
   command, ≤ 12 ranks). An item that has failed twice must be rescoped before it may be
   listed again. If fewer than 5 ready items exist, list what exists and say
   so — step 5 still forbids inventing work. Each listed item meets the rubric
   below; an item that cannot yet state its anchor is not ready to queue, and
   writing that anchor is itself the better queue item.

   **Prefer independent items over a dependency chain.** Four runs will take
   items 1–4 in order without waiting for each other's results, so an item
   that only works if the item above it landed will fail for reasons that are
   not about that item. Where the critical path is genuinely serial, say so
   explicitly in the item ("depends on item 1 landing; if it did not, skip to
   item 3") rather than leaving the run to discover it.

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
step 5 or listed in step 6 states all six:

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
   heavy 1200 s, the rank count, and a cost estimate taken from a prior
   measurement where one exists (a probe's solve time, a comparable fixture).
   An item nobody has costed is an item that overruns.
4. **The traps already paid for** — name the failures this project has already
   bought, so the run does not buy them twice: `ufl.max_value` does not compile
   in the complex build; a killed run leaves a stale FFCx lock that fails the
   next until `~/.cache/fenics` is cleared; `cell_tags.values` and
   `assemble_scalar` are rank-local; pytest captures prints without `-s`;
   `-k a or b` splits into stray argv inside an already-quoted container
   command; a headless session that backgrounds a harness run and ends its
   turn exits the CLI and SIGKILLs the harness (footerless log, no journal —
   three slots on 2026-08-10/11): harness runs go foreground, Bash-tool
   timeout 660000 ms, container-side `timeout` sized to return a footer
   inside that window; the container-side `timeout` needs `-k 30` — a plain
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
   the degree — `POST-5` step 1, 2026-08-18, two windows). Add to
   this list as runs discover more.
5. **The scope boundary** — what the item does *not* close, stated so the
   implementer holds the chunk at 🟡 rather than over-claiming. `POST-3` step 1
   correctly stayed 🟡 because a scalar-σ identity does not gate the coil+
   phantom case, which is where it would earn its keep.
6. **What a negative result means** — the disposition if the measurement comes
   back wrong or zero. The answer is always *report the measurement and stop*,
   never fabricate a gate around it or loosen a bound to swallow it; the item
   should say which artifact captures it (a §7 annotation, a known-issues
   entry, an `attempt/*` branch).

Prefer items where a negative result is still informative — those convert a
failed hour into a finding. `PORT-1` step 1 measured exactly-zero mutual
coupling and thereby found the unfragmented mesh that had been quietly
corrupting three other fixtures.

## Constraints

- Never loosen a test bound or a done-when to make history look better.
- known-issues.md discipline applies: failures observed but not fixed get an
  entry; entries leave only with the commit that fixes them.
- Your session transcript is not durable. Anything worth keeping goes into
  the repo in this session's commit.
