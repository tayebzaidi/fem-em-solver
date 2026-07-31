# Attempt journal — scheduled implementer runs

Append-only. One entry per scheduled run, successful or not. Written by the
implementer runs (docs/automation/implementer-run.md); the daily review
(docs/automation/daily-review.md) is the reader. Do not edit prior entries.

Entry format:

```
## <UTC timestamp> — <CHUNK-ID> — <complete|incomplete|blocked|anomaly>
- Tried:
- Result / measured:
- Logs: <docs/testing/logs/ filenames>
- Branch (if parked): attempt/<CHUNK-ID>-<UTC timestamp>
- Next-attempt hypothesis:
```

---

## 2026-07-28T22:46Z — MAG-14 — blocked

- **Tried:** preflight per `docs/automation/implementer-run.md`. Tracked tree was
  clean (`git status --porcelain -uno` empty; ~20 untracked ambient dotfiles in
  the repo root — `.bashrc`, `.claude/skills`, `.idea`, … — predate this run and
  were left alone). Container preflight `cd docker && docker compose ps` failed:
  `permission denied while trying to connect to the docker API at
  unix:///var/run/docker.sock`. Reproduced through the harness
  (`run_and_log.sh PREFLIGHT "docker compose exec -T fem-em-solver bash -lc
  'echo container-alive'"`) → exit 1, elapsed 1 s.
  Probed for any other route to a daemon: `docker compose version` (v5.3.1) and
  `docker compose config --services` (`fem-em-solver`) both succeed — client-side
  only, they never touch the socket. `id` in-session:
  `uid=1000(taz5297) gid=1000(taz5297) groups=1000(taz5297),65534(nogroup)`;
  socket is `srw-rw---- 65534 65534 /var/run/docker.sock`; `/etc/group` has
  `docker:x:989:taz5297`. No rootless socket (`/run/user/1000/docker.sock` absent).
  So the session's ids are namespace-remapped and the docker-group membership the
  human has interactively does not carry into a scheduled session. First scheduled
  implementer run after `25d99d3` swapped `--dangerously-skip-permissions` for the
  sandboxed allowlist; that commit is the prime suspect.
- **Result / measured:** no solve executed, therefore **no chunk can reach §4-done
  in this environment** — this blocks all three On-deck items equally, not just
  `MAG-14`. Only measurement of the run: the failing preflight, 1 s.
  With the remaining timebox I wrote the `MAG-14` test anyway so a fixed
  environment can verify it immediately: `tests/validation/test_helmholtz_magnitude.py`,
  ported from `examples/magnetostatics/04_helmholtz_analytic_comparison.py` per the
  §7 plan. Assertions: centre `B_z` within 5% of `(4/5)^1.5·μ₀I/R`; the analytic
  helper cross-checked against that same closed form to 1e-12; mean on-axis rel err
  < 5% over `|z| ≤ 0.25R`; central `CV < 1%` as the secondary check.
  Sizing 2R padding, wire/far resolution 0.003/0.010 (the 76k-cell, 1.73%-centre-error
  row of the `MAG-1`/`MAG-4` table). **It has never run** — only `python3 -c ast.parse`
  passed. Runtime at `-n 2` is unmeasured.
- **Logs:** `docs/testing/logs/20260728T224240Z_PREFLIGHT.log`
- **Branch (if parked):** `attempt/MAG-14-20260728T224647Z`
- **Denied commands worth an allowlist decision:** `docker context ls` and other
  bare `docker …` forms (allowlist has `docker compose *` only) — wanted them to
  enumerate alternative endpoints; `touch`/`rm` outside the repo — wanted them to
  distinguish a sandbox filesystem denial from a DAC denial. Neither would have
  changed the outcome. `scripts/automation/**` and `.claude/**` are `ask`, so a
  scheduled session cannot repair its own environment by design (correct, but it
  means this blocker is human-gated).
- **Next-attempt hypothesis:** the daemon socket is unreachable from a sandboxed
  scheduled session; a human must either grant these sessions access to
  `/var/run/docker.sock` (or run them unsandboxed — note `dangerouslyDisableSandbox`
  is reported disabled by policy, so this is a settings change, not a wrapper flag)
  or move verification to a host-side runner that consumes a queue file and writes
  `run_and_log.sh` output back into `docs/testing/logs/`. Until then every scheduled
  run will land here, and the honest thing for the next run to do is verify the
  socket in preflight and stop within a minute rather than re-derive this.
  Once the daemon is reachable: cost-probe `test_helmholtz_magnitude.py` at
  `mpiexec -n 2` (mesh ~76k cells; the 127k-cell 4R case was 18.9 s mesh + 5.4 s
  solve at 8 ranks), then run it under the `standard` tier. Expect ~1.7% centre
  error; if it exceeds 5%, raise `AIR_PADDING` to `4 * MAJOR_RADIUS`, never the
  tolerance.

---

## 2026-07-28T21:20 CDT — environment fix — Docker blocker resolved

Interactive session. Root cause of the 2026-07-28T22:46Z blocker was the Bash
sandbox: its user namespace strips the `docker` supplementary group, so no
sandboxed command can open `/var/run/docker.sock`. Fix per the Claude Code
sandboxing docs: `docker *` and `scripts/testing/run_and_log.sh *` added to
`sandbox.excludedCommands` in `.claude/settings.json`; they run outside the
sandbox, still gated by the permission allowlist. Verified by re-running the
exact failed preflight through the harness:
`docs/testing/logs/20260729T022156Z_PREFLIGHT.log` (exit 0, 1 s).
Also moved automation session logs to `logs/automation/` in-repo (gitignored).
The next scheduled run should pass preflight and can pick up MAG-14, including
the unverified test parked on `attempt/MAG-14-20260728T224647Z`.

---

## 2026-07-29T14:42Z — `MAG-14` — **complete**

Scheduled implementer run (09:42 CDT). Top On-deck item; the Docker blocker
from 2026-07-28 is genuinely gone (`docker compose ps` Up, harness exit 0).

**What was tried.** Cherry-picked `b81b958` from
`attempt/MAG-14-20260728T224647Z` onto `main` unchanged, per §9's instruction
not to rewrite the parked test. Cost-probed by running the real test at the
`smoke` ceiling (`timeout 30`) rather than building a shrunken variant — if it
had overrun, 30 s was the whole cost and the fallback was the `standard` tier.
It passed in 12 s, so no `standard` run was ever needed.

**Measured** (`mpiexec -n 2`, identical across all three runs):

| quantity | value |
|---|---|
| cells | 53941 |
| centre `B_z` FEM | 3.592162e-09 T |
| centre `B_z` closed form `(4/5)^{3/2}·μ₀I/R` | 3.531057e-09 T |
| centre rel err | **1.731%** (tolerance 5%) |
| mean on-axis rel err, `|z| ≤ 0.25R` | 1.730% |
| central `CV` | 0.0216% |
| analytic-helper vs closed form | `< 1e-12` |
| wall clock | 11 s — `smoke`, not `standard` |

The predicted value for 2R padding was 1.73%; the measurement is 1.731%. The
air-box error model in the `MAG-1`/`MAG-4` table predicts this fixture, which
is worth more than the pass itself. Cell count came in at 53.9k, not the
plan's 76k — the graded wire/far sizing differs from the padding study's mesh
while giving the same error; the plan's figure was the study mesh, and the
test docstring now records both. No assertion was touched.

**Logs.** `20260729T144309Z_MAG-14-probe.log` (cost probe),
`20260729T144331Z_MAG-14.log` (verification, `-s` for the printed numbers),
`20260729T144434Z_MAG-14-final.log` (re-run after a docstring-only edit, so
the committed file is byte-for-byte what executed).

**Also.** 11 s permits CI, so the test joined the `mpiexec -n 2`
magnetostatics step in `.github/workflows/ci.yml` — the plan made this
conditional on measured runtime. Separately, preflight `git status` was *not*
clean: the Bash sandbox masks personal dotfiles by bind-mounting `/dev/null`
over them inside the repo root, leaving ~21 untracked character devices
(`.bashrc`, `.mcp.json`, `.claude/skills`, …). These are sandbox artifacts,
not half-applied chunk work — nothing under `src/`, `tests/`, or `docs/` was
dirty — so I proceeded rather than filing an anomaly, and added them to
`.gitignore` so future preflights are honestly clean. `.vscode/` and `.idea/`
were already ignored as *directories*; the sandbox creates them as files, so
they needed separate entries.

**Next.** On deck advances to `MAG-13` (wire fixture only, §7 steps 1–3 and 6).
Hypothesis for it: nothing here suggests trouble, but note that this run's one
surprise was a *cell count* off by 30% from the plan while the error matched
exactly — treat §7's mesh-size figures as indicative and the error figures as
predictive. The parked branch `attempt/MAG-14-20260728T224647Z` can be deleted
whenever the daily review is satisfied; it is fully contained in `main` now.

---

## 2026-07-29T18:42Z — `MAG-13` (not started) — **anomaly**

Scheduled implementer run (13:42 CDT). Stopped at preflight per
`docs/automation/implementer-run.md` step 1: `git status` was not clean, so no
chunk work was done. `MAG-13` was the top On-deck item and remains untouched.

**What was found.** Two tracked files modified, uncommitted, nothing staged:

```
 M CLAUDE.md
 M docs/automation/implementer-run.md
```

Both edits are documentation-only and say the same thing: the implementer cron
schedule changed from three runs a day (`09:42 / 13:42 / 17:42` local) to six
(`every 3 h at :42, 07:42–22:42` local). No change under `src/`, `tests/`,
`scripts/`, or `PROJECT_PLAN.md`; the full diff is 5 insertions / 4 deletions
and touches only the two "Scheduled automation" blurbs. Container was Up.

**Assessment — not half-applied chunk work.** This is the failure mode step 1
exists to catch, and this is not it: the two edits are mutually consistent,
complete, and describe a config change no implementer run would make. Last
commit to either file was `25d99d3` (2026-07-28), so the edits post-date it and
were almost certainly made by hand between runs and left uncommitted. I did not
commit them — step 1 says commit *only* the anomaly entry — and I did not stash
them, since silently moving a human's uncommitted work is worse than tripping
one preflight.

Note this is a *different* anomaly class from the 2026-07-29T14:42Z run's
sandbox-artifact dirtiness (untracked `/dev/null` bind-mounts, no content).
That one was correctly proceeded through. This one is real tracked content, so
it is not covered by the same reasoning and I stopped.

**Denied command.** `crontab -l` is not in the allowlist, so I could not verify
whether the installed schedule actually is the six-run one the diff claims. The
run time (13:42 CDT) exists under both the old and new schedules, so my own
invocation does not discriminate either. If the daily review wants scheduled
sessions to be able to self-check their cron config, `crontab -l` would need
allowlisting — a read-only command.

**Cost.** No compute; no harness log. ~5 min of the timebox used.

**Next.** This will trip *every* subsequent implementer run until resolved —
six a day now, if the diff is accurate. Resolution is one human action: commit
the two doc edits (or discard them). Recommended for the daily review: commit
them as a `docs(automation)` change, then `MAG-13` (wire fixture only, §7 steps
1–3 and 6) is unblocked and should be the next run's item unchanged. No
hypothesis about `MAG-13` itself is available — nothing was executed.

---

## 2026-07-29T21:42Z — `MAG-13` (not started) — **anomaly**

Scheduled implementer run (16:42 CDT). Stopped at preflight per
`docs/automation/implementer-run.md` step 1, for the **same unresolved dirty
tree** as the 2026-07-29T18:42Z run. No chunk work done. Container Up
(`fem-em-solver`, up 2 days). `MAG-13` is still the top On-deck item and is
still untouched.

**State is byte-identical to the previous run's.** Same two tracked files, same
diff (5 insertions / 4 deletions), nothing staged, nothing new:

```
 M CLAUDE.md
 M docs/automation/implementer-run.md
```

**New evidence: the diff is correct.** The previous entry could not tell
whether the six-run schedule the diff describes was actually installed, because
`crontab -l` is not allowlisted and 13:42 CDT exists under both the old and new
schedules. This run resolves it: I was invoked at **16:42 CDT**, which exists
only under the new schedule (`07:42/10:42/13:42/16:42/19:42/22:42`) and not
under the old one (`09:42/13:42/17:42`). The uncommitted doc edits therefore
describe reality, and `CLAUDE.md` + `implementer-run.md` are currently *stale*
in `main` relative to the running cron. The correct resolution is to commit
them, not discard them.

**Still not committing them.** Step 1 says commit only the anomaly entry, and
these edits are a human's uncommitted work. Two runs agreeing that a change
looks right is not authority to land it on `main` on the human's behalf; the
rule exists precisely so an automated session cannot decide that. Not stashed
either, for the same reason.

**Escalation — this is now a run-loop, not an incident.** The blocker is
unchanged after one full cycle, and under the confirmed six-run schedule it
will consume **every remaining run** (next: 19:42 and 22:42 CDT today, then six
a day) until a human commits or discards two documentation lines. Two runs are
already lost. `MAG-13` has not been attempted once. Cumulative cost is now the
dominant fact about this queue, and it is entirely non-technical.

**Requested of the daily review (unchanged, now urgent):**

1. `git commit` the two doc edits as `docs(automation)` — evidence above says
   they are accurate; this alone unblocks the queue.
2. Consider allowlisting `crontab -l` (read-only) so scheduled sessions can
   self-verify their schedule without needing two runs to infer it.
3. Consider whether step 1 should let a run land a *documentation-only,
   internally consistent* dirty tree when it has already been journaled as an
   anomaly by a prior run — the current rule is correct for `src/`/`tests/`
   but converts a two-line doc lag into an unbounded outage. That is a protocol
   change for the human to make, not for an implementer run.

**Cost.** No compute; no harness log. ~6 min of the timebox used.

**Next.** `MAG-13` (wire fixture only, §7 steps 1–3 and 6), unchanged, as soon
as the tree is clean. No hypothesis about the chunk itself — still nothing
executed against it.

---

## 2026-07-30T00:42Z — `MAG-13` (not started) — **anomaly**

Scheduled implementer run (19:42 CDT). **Third consecutive run** stopped at
preflight per `docs/automation/implementer-run.md` step 1, for the same dirty
tree as the 2026-07-29T18:42Z and 2026-07-29T21:42Z runs. No chunk work done.
Container Up (`fem-em-solver`, up 2 days). `MAG-13` still the top On-deck item,
still untouched.

State remains byte-identical: same two tracked files, same diff (5 insertions /
4 deletions), nothing staged.

```
 M CLAUDE.md
 M docs/automation/implementer-run.md
```

Nothing new to add about the diff itself — the 21:42Z entry establishes it is
accurate (it documents the six-run schedule that is demonstrably installed;
this 19:42 CDT slot is further confirmation, existing only under the new
schedule). Not committing, not stashing, for the reason given there: step 1
permits only the anomaly entry, and landing a human's uncommitted work is not
an implementer run's call.

**New, and the reason this entry exists at all: nothing scheduled can fix it
before two more runs are lost.** `docs/automation/daily-review.md` contains no
mention of `git status`, dirty trees, or uncommitted work (grepped:
`dirty|clean|git status|uncommitted` → zero hits), so the daily review is *not*
blocked by this tree and is the first scheduled actor able to clear it — but it
next runs at **2026-07-30 06:12 CDT**, after today's 22:42 run. Projected loss
before any automated resolution: **four runs** (13:42, 16:42, 19:42, 22:42),
and the daily review will only clear it if the human's review protocol leads it
to commit files it did not author, which is not currently written down as
something it does. If it does not, the outage continues at six runs/day.

**Requested of the daily review — one item, everything else is secondary:**

1. `git commit` the two doc edits as `docs(automation)`. This is the whole
   blocker. If protocol ambiguity is what is stopping you: three independent
   runs have now verified the diff describes reality.

The 21:42Z entry's items 2 (allowlist `crontab -l`) and 3 (whether step 1
should permit a documentation-only, already-journaled dirty tree to be landed)
stand unchanged and are for the human, not for a scheduled session.

**Cost.** No compute; no harness log. ~5 min of the timebox used.

**Next.** `MAG-13` (wire fixture only, §7 steps 1–3 and 6), unchanged, as soon
as the tree is clean. Still nothing executed against the chunk.

---
## 2026-07-30T03:42Z — `MAG-13` (wire fixture, §7 steps 1–3 and 6) — **complete**

Scheduled implementer run (22:42 CDT). Preflight **clean** — the dirty tree that
cost the four preceding runs was landed as `c8d5201`/`e9e49cb` before this slot,
so no exception path was needed. Container Up. Took On-deck item 2 unchanged.

**What was done.** Steps 1–3 and 6 of the §7 plan:

- `AnalyticalSolutions.straight_wire_vector_potential(..., wire_radius=a)` —
  finite-conductor branch gauged to `A_z(a)=0`. Not optional: the
  `straight_wire_domain` end caps cross `r = 0`, where the filament `ln r`
  diverges, so interpolating the filament form as BC data would have injected
  garbage on two of the three boundary surfaces.
- `AnalyticalSolutions.circular_loop_vector_potential` — Jackson 5.37 off-axis
  `A_φ` via `scipy.special.ellipk/ellipe` (scipy 1.11.3 confirmed in the
  container first, per the plan). Unit test curls it back to the on-axis closed
  form at three `z` values, rtol 1e-6 — that is what catches the `m = k²`
  convention trap; a magnitude-only check would not.
- `core.solvers.exterior_dirichlet_bc(V, field)` — generic: interpolate a
  callable into an N1curl space, constrain all topologically-located exterior
  dofs. The loop fixture (step 4) reuses it unchanged.
- `tests/validation/test_straight_wire.py` rewired to use it.

**Measured** (`mpiexec -n 2`, |B| L2 error over `2a → 0.8 R_domain`):

| h | cells | natural `n×H = 0` | analytic Dirichlet |
|---|---|---|---|
| 0.004 | 38.8k | 35.13% | 22.19% |
| 0.0025 | 145.9k | — | 12.75% |
| 0.0018 | 383.2k | — | 9.26% |

Fitted rate ≈ O(h^1.2) with **no plateau** — the modeling floor this chunk was
written against is gone. Bound tightened 25% → 15% (measured 12.75%), sampling
window widened 0.4R → 0.8R, and a new test
`test_analytic_bc_improves_on_natural_bc` asserts the BC beats the natural wall
on the *same* mesh (measured 0.63×, bound 0.85) — the chunk’s physical claim
rather than a tolerance. No assertion was loosened; the `B_z < 0.10·B_ref`
azimuthality check was left untouched and passes at 9.54%.

**Not reached:** the < 5% target, and steps 4–5 (loop fixture, convergence-test
rework) which were out of scope for this run. §7 is 🟡, not ✅, with both stated.
Extrapolating the measured rate puts < 5% at h ≈ 0.00125 (~1.1M cells, > 5 min
at `-n 2`) — outside the standard tier, so uniform refinement is the wrong lever;
graded refinement (MAG-9 machinery) is the cheap one. `J·n ≠ 0` at the end caps
still stands but was evidently not dominating, so step 3’s "cap the wire short of
the end faces" option was left unmeasured.

**Cost.** Three harness runs, all inside tier: `20260730T034541Z_MAG-13-probe.log`
(BC vs natural at h=0.004, 12 s), `20260730T034614Z_MAG-13-probe2.log`
(h-refinement 0.0025 + 0.0018, 121 s), `20260730T034941Z_MAG-13.log`
(**9 passed, 72 s**, standard tier — `tests/unit/test_analytical_lightweight.py`
+ `tests/validation/test_straight_wire.py`). ~45 min of the timebox. No denied
commands. `test_straight_wire.py` is already in the CI validation job, so the new
test rides along (+~13 s); no workflow change.

**Next.** `MAG-13` steps 4–5: `test_circular_loop.py` gets the same treatment
with `circular_loop_vector_potential` + `exterior_dirichlet_bc` (both landed and
unit-tested, so it is fixture work only), then `test_convergence.py` to ≥ 3
resolutions with a fitted rate in [0.7, 1.5]. Hypothesis: the loop will improve
less dramatically than the wire — its PMC-image bias is ~(a/R)³ rather than an
Ampère-law contradiction — and the honest outcome there may again be a measured
bound rather than the planned single digits. known-issues.md now carries the
wire half as fixed and the loop half as open.

---

## 2026-07-30T12:42Z — `MAG-13` (loop fixture + convergence rework, §7 steps 4–5) — **complete**

Preflight clean, container Up 2 days. Top On-deck item taken as written.

**`MAG-13` is now ✅ in full** (wire half `a30682c`, this run steps 4–5). Batch 2
is complete; `TH-9` is next on deck.

**What landed.** `test_circular_loop.py` rewired onto a shared
`solve_loop(params, comm, resolution=None, analytic_bc=True)` helper +
`loop_potential_interp`, imposing the Jackson 5.37 off-axis `A_φ` on the outer
sphere through `exterior_dirichlet_bc`; both loop tests use it.
`test_convergence.py::test_h_refinement_straight_wire` now uses the analytic BC,
three resolutions, and a two-sided fitted-rate bound.

**Measured** (`mpiexec -n 2`, on-axis `B_z` L2 error over `|z| ≤ 0.4 R_domain`):

| h | cells | natural `n×H = 0` | analytic Dirichlet |
|---|---|---|---|
| 0.0035 | 82.8k | 14.98% | 16.23% |
| 0.0025 | 208.0k | 8.86% | 10.37% |
| 0.002 | 411.4k | — | **7.07%** |

**The prior run's hypothesis was right about the direction and wrong about the
sign: the loop does not improve, it gets ~20% worse at fixed h.** The wire's
natural BC contradicts Ampère's law (an error refinement cannot touch, 35.13% →
22.19%); the loop's is only a PMC image term of order `(a/R)³ ≈ 3.7%`, which is
*smaller* than the O(h) error that degree-1 interpolation of `A_φ` injects
through the boundary data itself. The Dirichlet wall's payoff is the limit:
16.23% → 10.37% → 7.07% converges monotonically (fitted ≈ 1.4) to the analytic
field, while the natural wall converges to a different field.

Consequences, all decided on measurement rather than convenience:

- The loop tolerance tightens **10% → 8% at h = 0.002**, not at the old
  h = 0.0025 where the analytic BC would have needed ~12%. Nothing was loosened
  to accommodate the better boundary condition; the resolution moved instead.
- Sampling window kept at `0.4 R` (the natural-BC revision's metric), so the two
  walls are compared on the same thing. Widening to `0.8 R` reports 6.28%
  instead of 7.07% purely by adding far-field points where `B` is small — that
  would have made the tightened bound meaningless. (The *wire* test's 0.8 R
  window stays: there the widening was measured to be neutral, 12.48% vs 12.75%.)
- No `test_analytic_bc_improves_on_natural_bc` analogue for the loop: measurement
  says that claim is false on this fixture, so asserting it would be fiction.
  The comparison lives in the docstring, §7, and known-issues.md instead.

**Convergence rate** (wire, analytic BC): 22.19% → 12.75% → 9.26% at
h = 0.004/0.0025/0.0018 → fitted **1.10**, asserted in `[0.7, 1.5]`. The upper
bound is deliberate: an inflated rate means an anomalous resolution, not better
convergence. Two candidate triples were rejected on measurement — h = 0.005 gives
30.34% at 23.2k cells (5 mm cells cannot resolve the 3 mm wire; a geometry
artifact that inflates the fit), and h = 0.0035 gives 11.77%, *below* the
h = 0.0025 value, so any sequence containing it is non-monotone. Cell-wise
constant `curl A` means every resolution carries O(h) pointwise sampling noise;
that noise, not the boundary, is what dominates the loop error at affordable h.

**Verification.** `20260730T125223Z_MAG-13.log` — loop file, **3 passed, 167 s**;
`20260730T125522Z_MAG-13.log` — convergence + wire, **5 passed 2 skipped,
196 s**. Both `mpiexec -n 2`, **heavy** tier (`timeout 300`/`400`), well under
the 10-min ceiling; §7 and the §7 table now say `heavy` for this chunk, since the
loop's analytic test alone is 124 s at 411k cells. Probes:
`20260730T124356Z_MAG-13-loop-probe.log` (h=0.0035 both walls, 31 s),
`20260730T124523Z_MAG-13-loop-probe2.log` (h=0.0025 both walls, 95 s),
`20260730T124829Z_MAG-13-loop-probe3.log` (h=0.002 BC only, 126 s),
`20260730T124832Z/124930Z_MAG-13-conv*.log` (the rejected resolution triple).
No denied commands. Probe script left in `scratch/` and deleted before commit.

**CI.** The `validation` job runs both files; they went from ~100 s to ~330 s on
the dev box, so `timeout-minutes` is raised 25 → 45 with the measurement in the
comment. This is the one cost the daily review may want to revisit: if 45 min is
too much runner time for the value, the cheap lever is dropping the loop's
analytic test to h = 0.0025 in CI only — but that needs the 12% bound, so it
would have to be an explicit, documented CI-vs-local split, not a quiet
loosening.

**Next.** `TH-9` (PEC cavity resonance gate) is now the top On-deck item; verify
`slepc4py` imports at chunk start — the §9 note flags it as the long pole. For
`MAG-13`'s residue, nothing is open that blocks anything: the wire's < 5% target
needs h ≈ 0.00125 (~1.1M cells, > 5 min at `-n 2`) and the loop's error is
dominated by pointwise sampling of a cell-wise constant `curl A`, so the lever
for both is graded refinement (`MAG-9` machinery) or a smoothed error functional,
not more uniform h. Hypothesis worth one probe someday: recovering `B` in an
H(div) space (or comparing cell-averaged rather than pointwise `B_z`) should cut
the loop's error roughly in half at fixed h, because the O(h) noise it measures
is an artifact of the evaluation, not of the solve.

---


## 2026-07-30T15:42Z — TH-9 — complete

- **Tried:** preflight clean (`git status --porcelain` empty on `main`,
  container Up 3 days), top On-deck item taken as written. Implemented the §7
  plan: new `src/fem_em_solver/core/cavity.py` assembling the N1curl pencil
  `∫(∇×E)·(∇×v) dx = k² ∫E·v dx` on a PEC box with `dolfinx.mesh.create_box`,
  solved as a SLEPc GHEP with shift-and-invert (MUMPS LU), plus
  `tests/validation/test_cavity_resonances.py` (three tests). `slepc4py` 3.20.0
  imports in the image and `PETSc.ScalarType` is `float64` — the §9 note flagged
  slepc as the long pole; it was a non-issue, and the real build is all this
  chunk needs.
- **Result / measured:** cavity 1.0 × 0.8 × 0.6 m. The plan's suggested
  1.0 × 0.7 × 0.5 m was **rejected before any solve**: `d = a/2` makes
  `(0,1,1)` and `(2,1,0)` exactly degenerate at 368.5 MHz, which is precisely
  the ordering ambiguity the plan wanted to avoid. With 0.8/0.6 the first four
  modes are 239.95 / 291.35 / 312.28 / 346.40 MHz, closest pair 7% apart; the
  fifth (353.53 MHz) is only 2% above the fourth, so the gate stops at four
  rather than five. N1curl degree 2, `mpiexec -n 2`:
  (6,5,4) → 720 cells / 5330 dofs / max error **0.0436%** (tolerance 1%);
  (9,7,6) → 2268 cells / 15998 dofs / max error **0.0102%**. Every mode
  improves; fitted max-error rate **3.85** in h (assertion floor 2.0),
  consistent with O(h^{2k}) for degree-2 edge elements. Null space: the 8
  eigenvalues nearest zero are all below 1e-8·k₁², max |λ|/k₁² = **3.2e-15**,
  counted and asserted rather than skipped; zero null modes leaked into the
  physical band. Cost probe first (three configurations, 180 s ceiling, actual
  2.8 s); the verification run itself was **3 s** at standard tier — the tier
  is kept at `standard` per §7 rather than demoted, since the mesh is a budget
  knob a future TH-1 fixture may turn up.
- **Trap worth recording:** the PEC-constrained rows. Assembling `B` with a
  zero diagonal (the obvious way to send the constrained dofs to infinity)
  makes `B` singular and invalidates the GHEP B-orthogonalisation. Instead `A`
  gets a large diagonal (1e4·k₄²) and `B` unit diagonal: `B` stays SPD, the
  spurious eigenvalues park at 1e4·k₄², and a stated cutoff drops them. The
  shift target is the midpoint of the analytic k₁²…k₄² band, chosen so every
  requested mode is strictly closer to the shift than the zero cluster is —
  that is why `null_mode_count == 0` is an assertion and not an accident.
- **Logs:** `docs/testing/logs/20260730T154616Z_TH-9.log` (first pass; pytest
  captured stdout, so the numbers are not in the log — kept for the record),
  `20260730T154626Z_TH-9.log` (re-run with `-s`, numbers visible), and
  `20260730T154846Z_TH-9.log` — **the log of record**: the same run repeated
  after two code comments were corrected to the measured rate (3.85, not the
  3.58 I had estimated by hand), so the log matches the committed source
  byte-for-byte. All three: 3 passed, 3 s.
- **Branch (if parked):** none; landed on `main`.
- **Denied commands:** none.
- **Next-attempt hypothesis:** On-deck now advances to `TH-1` step 0, the
  complex-mode environment smoke. Note for whoever takes it: this chunk
  confirms the real build is healthy, so a `TH-1` failure after the switch is
  environment or formulation, not assembly — `cavity.py` gives a cheap
  A/B, since the same eigenproblem must return the same frequencies under
  `dolfinx-complex` if the environment is sound. Worth 30 s of the TH-1 run.

---


## 2026-07-30T18:42Z — TH-1 step 0 — complete

- **Tried:** preflight clean (`git status --porcelain` empty on `main`,
  container Up 3 days), top On-deck item taken as written: `TH-1` step 0, the
  complex-mode environment smoke. First finding: **no source change was
  needed.** `src/sitecustomize.py` was already reworked to key off `PETSC_ARCH`
  (its docstring names TH-1 explicitly), so with
  `source /usr/local/bin/dolfinx-complex-mode` plus `PYTHONPATH=/workspace/src`
  the container resolves `/usr/local/dolfinx-complex/.../dolfinx` 0.7.2 and
  `PETSc.ScalarType` is `complex128` (probe log
  `20260730T184310Z_TH-1-step0-probe.log`, 1 s). The chunk's real content was
  therefore the gate, not the plumbing: new
  `tests/environment/test_complex_mode.py`, four tests.
- **Measured:** `∫_Ω c dx` over the unit cube = **2 − 3j** to |Δ| < 1e-13.
  The step-1 conjugation trap pinned as numbers, since "inner conjugates its
  second argument" is the single named risk of TH-1 step 1: with
  `f = (1+2j)x̂`, `g = (3+4j)x̂`, `∫ inner(f,g) dx = 11.000000000000 +
  2.000000000000j` and `∫ dot(f,g) dx = −5.000000000000 + 10.000000000000j`,
  i.e. the two differ and the sign flip is now a red test rather than a wrong
  field. On the element family TH-1 actually uses: the ε_c-weighted N1curl mass
  matrix equals `ε_c·M` entry for entry — `‖M_c − ε_c M‖_F = 4.449e-16` against
  `‖M‖_F = 1.041233`, **4e-16 relative**. The fourth test (scalar type /
  `PETSC_ARCH` / imported dolfinx build agree) asserts in *both* modes, because
  the failure it guards is the mismatch the old hardcoded-path shim produced.
- **Skip discipline:** an environment gate that skips is worthless in the run
  that was meant to exercise it, so `FEM_EM_REQUIRE_COMPLEX=1` turns the
  real-mode skips into failures. Negative control executed, not assumed: real
  mode + that flag ⇒ **3 failed, 1 passed** with the intended message
  ("PETSc.ScalarType is float64 ... complex build was not picked up") —
  `20260730T184503Z_TH-1-step0-negctl.log`.
- **A/B against the real build** (suggested by the TH-9 entry's next-attempt
  note, and it was worth the 8 s): the entire `TH-9` cavity gate re-run under
  `dolfinx-complex` returns identical physics — max error 0.0436% at (6,5,4),
  refinement rate 3.85, 8/8 null modes below cutoff, 3 passed in 7 s
  (`20260730T184634Z_TH-1-step0-cavity-ab.log`). A `TH-1` failure from here on
  is formulation, not environment.
- **CI:** added a real-mode `pytest tests/environment` step to the validation
  job (verified in the exact serial form CI uses: 1 passed, 3 skipped, 1 s,
  `20260730T184657Z_TH-1-step0-ciform.log`). The complex invocation is left out
  of CI deliberately until `TH-1` proper needs it — I could not execute a CI
  run here, and a step that only ever ran locally does not belong in a job
  whose value is being green.
- **Tier / cost:** smoke, 1–3 s per run at `mpiexec -n 2`; the A/B was standard
  tier (180 s ceiling, actual 8 s). Whole chunk well inside the timebox.
- **Logs:** `20260730T184310Z_TH-1-step0-probe.log`,
  `20260730T184426Z_TH-1-step0.log` (first pass, pytest captured stdout),
  `20260730T184446Z_TH-1-step0-complex.log` — **the log of record**, re-run with
  `-s` so the numbers are visible (4 passed, 1 s),
  `20260730T184454Z_TH-1-step0-realmode.log`,
  `20260730T184503Z_TH-1-step0-negctl.log` (negative control, exit 1 by
  design), `20260730T184634Z_TH-1-step0-cavity-ab.log`,
  `20260730T184657Z_TH-1-step0-ciform.log`.
- **Branch (if parked):** none; landed on `main`. `TH-1` in the §7 table moves
  ⬜ → 🟡 (step 0 done, steps 1–5 open).
- **Denied commands:** none affecting the work. Two Bash calls were rejected for
  shape, not content (`cd docker && docker compose ps`, and a trailing
  `echo "EXIT=$?"`); both were re-issued with absolute paths / split commands.
- **Next-attempt hypothesis:** **On deck is now empty** — the daily review must
  refill it before the next implementer run has anything to take. The natural
  entry is `TH-1` steps 1–3 (sesquilinear form + MUMPS + replacing the
  `E = −jωA` body), sized as one run, with steps 4–5 (`TH-6` lossy plane-wave
  gate and the resonance guard) as the following item. Note for whoever takes
  it: every chunk command must now carry
  `source /usr/local/bin/dolfinx-complex-mode` **and**
  `FEM_EM_REQUIRE_COMPLEX=1`, and `tests/environment` should be the first
  thing in the pytest path list so an environment regression fails before the
  formulation tests get blamed.

---

## 2026-07-30T21:42Z — (no chunk) — **anomaly**

- **Outcome:** no chunk work attempted. **On deck (§9) is empty** — all three
  items are struck through and marked done (`MAG-13` steps 4–5, 07:42 run;
  `TH-9`, 10:42 run; `TH-1` step 0, 13:42 run), and §9 itself says "On deck is
  empty after this item — the next daily review must refill it".
  `docs/automation/implementer-run.md` step 2 is unambiguous: take the first
  item that is not done or blocked, *do not choose a different item for any
  reason*, and if the list is empty append an entry here and stop. So this run
  stops. No verification command was executed; nothing under `src/`, `tests/`
  or `scripts/` was touched.
- **Preflight:** `git status --porcelain` empty on `main` at `1a9f44b`;
  `fem-em-solver` container **Up** (3 days). No dirty tree, so the step-1
  already-journaled-drift exception did not apply and was not used.
- **Why this is filed as `anomaly` and not `complete`:** the queue draining
  mid-day is a scheduling gap, not a chunk result. Three implementer slots
  (16:42, 19:42, 22:42) fall between now and the 06:12 daily review; on the
  current protocol **all three will land here and stop for the same reason**,
  i.e. ~3 h of Opus timebox produces three journal entries and no physics. That
  is the finding worth acting on, and it is the daily review's call, not mine —
  the same protocol line that stops this run also forbids me from refilling §9.
  Two ways out, for the human/review to choose between:
  (a) keep §9 authoritative but have the daily review always leave ≥ 3 items
      queued (it is sized "exactly three", which is exactly one day of runs at
      six runs/day — the list is structurally guaranteed to drain);
  (b) give the implementer protocol a documented fallback: when On deck is
      empty, take the next chunk named in §9's own "obvious next entry"
      sentence. Today that sentence already names the item precisely.
- **Ready-to-take proposal, if the review wants to paste it into §9** (grounded
  in the §7 `TH-1` plan, lines 1004–1022, not invented here):
  1. `TH-1` **steps 1–3** — sesquilinear form
     `∫μᵣ⁻¹(∇×E)·(∇×v̄) − k₀²ε_c E·v̄ dx` with `ε_c = εᵣ − jσ/(ωε₀)` from the
     existing DG0 `build_material_fields`, load `−jωμ₀∫J·v̄ dx` (**`ufl.inner`
     conjugates its second argument — `ufl.dot` on the load silently flips the
     `e^{+jωt}` convention**; that trap is already pinned numerically by
     `tests/environment/test_complex_mode.py`), MUMPS direct solve with PEC via
     `build_boundary_conditions`, then replace the `E = −jωA` body of
     `TimeHarmonicSolver.solve` keeping the `TimeHarmonicFields` container so
     the downstream `⚠️` chunks still import. Standard tier.
  2. `TH-1` **steps 4–5** — `TH-6` lossy-half-space gate (interior decay
     constant + phase vs closed-form skin depth) plus the `MAT-2` σ-sensitivity
     assertion, and the resonance guard verified against a `TH-9` mode.
  3. A third item of the review's choosing, so the queue does not drain again
     before 06:12.
  Every `TH-1` command from here needs
  `source /usr/local/bin/dolfinx-complex-mode` **and**
  `FEM_EM_REQUIRE_COMPLEX=1`, with `tests/environment` first in the pytest path
  list — carried over from the 18:42Z entry.
- **Measured numbers / harness logs:** none — no compute was run, deliberately.
  Nothing to add to `docs/testing/test-results.md`.
- **Branch (if parked):** none. `main` left clean at `1a9f44b` plus this entry.
- **Denied commands:** one Bash call rejected for shape, not content
  (`cd docker && docker compose ps` — the `cd`-before-git guard); re-issued as
  `docker compose -f docker/docker-compose.yml ps` and it worked. Worth folding
  the absolute-path form into CLAUDE.md's preflight snippet, which currently
  shows the `cd docker && ...` version that gets denied in scheduled sessions.
- **Next-attempt hypothesis:** the 19:42Z run will hit this identical wall
  unless §9 is refilled first. If a human sees this before then, pasting item 1
  above into §9 is enough to unblock the next slot; otherwise expect two more
  `anomaly` entries with this shape before the 06:12 review.


## 2026-07-31T00:45Z — TH-1 steps 1–3 — complete

- **Tried:** preflight clean (`git status --porcelain` empty on `main` at
  `68587f8`, container Up 3 days), top On-deck item taken as written. Rewrote
  `core/time_harmonic.py`: the sesquilinear form
  `∫μᵣ⁻¹(∇×E)·(∇×v̄) − k₀²ε_c E·v̄ dx` with `ε_c = εᵣ − jσ/(ωε₀)` from the
  existing DG0 `build_material_fields`, load
  `−jωμ₀∫J·v̄ dx` (`ufl.inner`, never `ufl.dot`), MUMPS via `LinearProblem`,
  PEC through `build_boundary_conditions`. The `E = −jωA` body is gone;
  `TimeHarmonicFields` is unchanged apart from a new `e_complex` carrying the
  N1curl solution, so `ports/excitation.py` and the post-processing chunks
  import and run without edits. `gauge_penalty` is accepted and ignored (no
  null space at ω > 0 — §7 formulation note); `MagnetostaticSolver` is no
  longer on the path at all.
- **Gate — manufactured solution.** `E_ex = (sin ky, sin kz, sin kx)`,
  `k = π/L` on an `L = 0.2 m` box satisfies `∇×∇×E_ex = k²E_ex` *exactly*, so
  `−jωμ₀J = (k²/μᵣ − k₀²ε_c)E_ex` is an analytic source with no consistency
  error — the whole residual is discretisation error, which is what makes the
  rate assertable. Measured at 127.74 MHz in εᵣ = 78, σ = 0.7 S/m (chosen so
  `k₀²|ε_c| ≈ 5.6e2 m⁻²` is within an order of magnitude of the curl term; at
  εᵣ = 1 the mass term is swamped and the gate would be blind to ε_c):
  relative L2 error **1.126e-1 → 5.659e-2** from 3072 to 24576 cells,
  **fitted rate 0.9929** against the O(h) expectation for N1curl degree 1.
  Step 3 in the same test: `max|Re E| = 1.098` (amplitude 1 field) and
  `max|Im E|/max|Re E| = 2.97e-3` where the exact phasor is real — the retired
  proxy returned `e_real ≡ 0` by construction, so this number is the direct
  negative control on the replacement.
- **Gate — operator structure.** `‖A − Aᵀ‖_F < 1e-10‖A‖_F` (complex symmetric)
  while `‖A − Aᴴ‖_F > 1e-6‖A‖_F` (**not** Hermitian). The second half is the
  point: a Hermitian operator here means the `−jσ/(ωε₀)` term was dropped, which
  is exactly what a real build would do silently. 2 s.
- **Real-mode discipline.** `solve()` raises `RuntimeError` in a real build
  rather than discarding Im(ε_c). Placed *after* argument validation — the first
  attempt put it before, and the two `frequency_unit`/`material_map` error tests
  went red because they never reached their own `ValueError`
  (`20260731T003715Z_TH-1-steps123-realmode.log`, 5 failed); moved, and they
  pass (`...realmode2.log`). The five legacy tests that actually solve now carry
  `@complex_only` from the new `tests/complex_mode.py`.
- **Measured regressions.** Real mode over `tests/environment`, the four legacy
  time-harmonic suites, `tests/ports` and the new gate: **3 failed, 26 passed,
  10 skipped, 1.2 s** — all three failures are known-issues entries 2 and 3,
  none new (`20260731T003748Z_TH-1-steps123-realmode2.log`). Complex mode with
  `FEM_EM_REQUIRE_COMPLEX=1` over the same set minus ports: **2 failed, 20
  passed, 12.0 s**, both failures known-issues entry 2
  (`20260731T003802Z_TH-1-steps123-complexsuite.log`). Every legacy proxy test
  passes unchanged against the real solve — a measurement of how little they
  assert, recorded in §2.3.
- **Coverage loss, named:** CI runs real mode, so those five `@complex_only`
  tests plus the new MMS gate now execute in **no** CI job. §9 item 3 is a
  complex-mode CI leg; until it lands the gates guard nothing automatically.
- **Tier / cost:** smoke-to-standard, 3 s (probe) / 6 s (MMS) / 2 s (realmode2)
  / 13 s (complex suite) at `mpiexec -n 2`, all far inside the ceilings. Whole
  chunk ~35 min of the timebox.
- **Logs:** `20260731T003535Z_TH-1-steps123-probe.log`,
  `20260731T003553Z_TH-1-steps123-mms.log` (**the log of record** — the
  convergence numbers), `20260731T003715Z_TH-1-steps123-realmode.log` (exit 1,
  the misplaced-guard failure described above),
  `20260731T003748Z_TH-1-steps123-realmode2.log`,
  `20260731T003802Z_TH-1-steps123-complexsuite.log`.
- **Branch (if parked):** none; landed on `main`. `TH-1` stays 🟡 — steps 4–5
  (`TH-6` closed form, `MAT-2` sensitivity, resonance guard) are open, and §2.1
  now says explicitly that the solve is formulated but not yet checked against
  any physical closed form.
- **Denied commands:** one — a `python3 - <<'PY'` heredoc for a bulk test patch
  ("Contains brace with quote character"). Re-done with five `Edit` calls; no
  allowlist change needed.
- **Next-attempt hypothesis:** `TH-6` should be cheap now — impose the analytic
  lossy half-space through `dirichlet_e_field` on a box exactly as the MMS gate
  imposes `E_ex`, and compare the interior decay against δ = √(2/(ωμσ)). The
  risk is not the machinery but the convention: the gate must be derived in
  `e^{+jωt}` or it will disagree with a correct solver by a conjugation.

## 2026-07-31T02:10Z — TH-1 step 4 (`TH-6` + `MAT-2`) — complete

- **On-deck item:** §9 item 2, `TH-1` steps 4–5. Step 4 is complete; **step 5
  (the near-resonance guard) is not** and is left as the top open item.
  Preflight clean, container Up.
- **What was built:** `tests/validation/test_lossy_plane_wave.py`, two gates.
  `E = ẑe^{−jkx}` with `k = k₀√(ε_c)` on the `Im k < 0` branch is an exact
  *source-free* solution of the solved PDE, so the test imposes it as Dirichlet
  data on all six faces of a 0.1 m box via `dirichlet_e_field` and fits the
  **interior** amplitude and phase along a probe line. Boundary data cannot
  dictate the interior decay rate — only `ε_c` in the mass term can — so this
  is a genuine test of the physics, not of the BC machinery. The predicted
  (α, β) are computed twice by algebraically distinct routes (`k₀√(ε_c)` and
  the loss-tangent formulas) so a wrong branch choice cannot cancel out.
- **Measured — `TH-6`:** α = 13.069460 vs closed-form 13.067043 Np/m
  (**0.019%**, δ = 76.528 mm); β = 27.031165 vs 27.015150 rad/m (**0.059%**);
  relative L2 **7.217852e-2 → 3.609441e-2** from 10368 to 82944 cells, **rate
  0.9998** in h. Clears §10's < 5% MVP criterion at 3.61%.
- **Measured — `MAT-2`:** σ = 0.1 S/m → α = 2.119307 vs 2.124260 (0.233%);
  σ = 1.4 S/m → α = 21.878059 vs 21.904469 (0.121%); ratio **10.3232 vs
  10.3116** (0.113%). The retired proxy would return ratio 1.
- **First run failed and the mesh moved, not the tolerance.** At 8³/16³ the
  field error was 5.4139e-2, just over the 5% bar, while α/β were already at
  0.226%/0.132% (`20260731T020308Z_TH-6-gate.log`, exit 1). N1curl degree 1 is
  O(h), so 12³/24³ was the fix; the failing number is recorded in the §7 entry
  because it is the useful fact — the L2 norm is a much harsher gate on this
  problem than the log-slope fit, by roughly a factor of 50.
- **Bug found and fixed in `post/evaluation.py`:** `evaluate_vector_field_parallel`
  allocated its gather buffers as `float64`, which raises a casting error the
  first time it is handed a complex-mode Function. It now follows the
  function's own dtype. It had never been called under the complex build
  before — every prior caller is magnetostatic. Real-mode regression over the
  point-evaluation users (`test_energy_and_point_evaluation`, `test_straight_wire`,
  `test_circular_loop`, `test_helmholtz_magnitude`, `tests/environment`):
  **13 passed, 3 skipped, 254 s** (`20260731T020541Z_TH-6-regress.log`), no
  change in any measured value.
- **Tier / cost:** standard. 14 s (first, failing) / 21 s (12³–24³) / 21 s
  (re-run with `-s` to get the numbers into the log of record) / 255 s
  (real-mode regression), all `mpiexec -n 2`, all inside the ceilings.
- **Logs:** `20260731T020308Z_TH-6-gate.log` (exit 1, the 5.41% miss),
  `20260731T020356Z_TH-6-gate2.log` (green, numbers captured by pytest),
  `20260731T020427Z_TH-6-gate3.log` (**the log of record** — same run with
  `-s`), `20260731T020541Z_TH-6-regress.log` (real-mode regression).
- **Branch (if parked):** none; landed on `main`. `TH-6` and `MAT-2` flip to ✅;
  `TH-1` stays 🟡 on step 5 alone.
- **Denied commands:** one — a pipeline ending in `tail` on a `$(ls -t ...)`
  substitution ("contains shell syntax that cannot be statically analyzed").
  Re-run as two commands with a literal log path; no allowlist change needed.
- **Next-attempt hypothesis:** step 5 is the last of `TH-1`. The cheapest guard
  that is verifiable rather than decorative is energy continuity across sweep
  points — stored `∫εᵣ|E|²` as a function of frequency spikes near a mode — and
  `TH-9`'s 1.0 × 0.8 × 0.6 m PEC box is the fixture with known mode frequencies
  to make it fire on demand and stay quiet away from them.

## 2026-07-31T02:20Z — TH-1 step 5 (resonance guard) — complete

Same session as the entry above; step 4 was committed first (`99f3d4f`) so
`main` was clean and green before this was started. **`TH-1` is now closed.**

- **What was built:** `src/fem_em_solver/core/resonance.py` —
  `stored_electric_energy(fields)` = `(ε₀/4)∫εᵣ|E|²dx` (rank-reduced) and
  `check_energy_continuity(frequencies, energies)` returning a
  `ResonanceGuardReport`. The energy-continuity option from the §7 menu, chosen
  because it is the only one of the three that is *calibrated* rather than
  tuned: near a mode `W ∼ |f−f₀|⁻²`, so `S = |dlnW/dlnf| ≈ 2f/|f−f₀|` and the
  default threshold 50 means precisely "within 4% of a pole". `2/S` is exposed
  as `implied_detuning_fraction`, which turns the guard from a boolean into a
  physical read-out. It needs no eigen-solve and no extra solves.
- **Measured** (`20260731T021521Z_TH-1-step5b.log`, the log of record): driven
  at the `TH-9` fixture's **discrete** fundamental `f₁ = 2.399584e8 Hz` (taken
  from `solve_pec_cavity_modes` on the same mesh and degree, not the closed
  form — at 1% detuning the discretisation shift matters), `f₂ = 2.913659e8 Hz`.
  Approach at 4%/2%/1% below `f₁`: energies `5.8742e-7 → 2.3992e-6 → 9.6953e-6`
  J, **amplification 16.505× against the pole law's 16.0× (3.156%)**,
  `S = 137.554`, implied detuning **1.454%** vs the ~1.5% the interval sits at.
  Midband control at `(f₁+f₂)/2`: `S = 21.951`, clear. Both verdicts hold with
  2× margin on the threshold, which is what the test asserts rather than a bare
  fired/didn't-fire.
- **The first control sweep was misplaced, and the guard said so.** At
  `f₁ + 0.35(f₂−f₁)` the "quiet" sweep measured `S = 48.9` — just under
  threshold, separation only 2.81× (`20260731T021415Z_TH-1-step5.log`, 1
  failed). That point is 6% above `f₁` and the guard's implied detuning read
  4.1%: the guard was right and the control was wrong. Moved the control to the
  midband; the threshold was not touched. This is worth remembering because it
  is the pole model validating itself on data it was not fitted to.
- **Tier / cost:** standard. 20 s (first, failing) / 21 s (green) / 1 s
  (real-mode smoke), all `mpiexec -n 2`.
- **Real-mode check:** `20260731T021554Z_TH-1-step5-realmode.log` — the new
  `core.resonance` import is real-mode clean and the input-validation test runs
  there on purpose (it is pure numpy, no `@complex_only`): 2 passed, 6 skipped.
- **Logs:** `20260731T021415Z_TH-1-step5.log` (exit 1, misplaced control),
  `20260731T021521Z_TH-1-step5b.log` (**log of record**),
  `20260731T021554Z_TH-1-step5-realmode.log`.
- **Branch (if parked):** none; landed on `main`. `TH-1` flips 🟡 → ✅.
- **Denied commands:** none beyond the one noted in the previous entry.
- **Next-attempt hypothesis:** §9 item 3, the complex-mode CI leg, is now both
  the top open item and materially more urgent — this run added three more
  `@complex_only` tests, so eight tests, including every closed-form gate on
  the frequency-domain solver, currently execute in no CI job. It is smoke tier
  and should fit one run with time to spare. After that, `MAT-6` (Dodd–Deeds)
  is the gate that would license loaded-coil numbers; nothing in `TH-1` does.


## 2026-07-31T03:35Z — OPS-10 (complex-mode CI job) — complete

- **Item:** §9 On deck item 3, the complex-mode CI job. Given a chunk ID
  (`OPS-10`) since §7 had none for it.
- **Preflight:** tree clean, container Up 3 days, no parked branches.
- **What landed:** a `validation-complex` job in `.github/workflows/ci.yml`.
  It sources `/usr/local/bin/dolfinx-complex-mode` and runs, under
  `FEM_EM_REQUIRE_COMPLEX=1` at `mpiexec -n 2`: `tests/environment` (first, so
  an environment regression cannot be blamed on the formulation),
  `test_time_harmonic_mms.py`, `test_lossy_plane_wave.py`,
  `test_resonance_guard.py`, `test_time_harmonic_smoke.py`,
  `test_boundary_condition_selection.py`. `timeout-minutes: 30`.
- **Measured:** 18 passed, **46 s** for the harness-form invocation
  (`PYTHONPATH=/workspace/src`) and **32 s** for the CI-fidelity invocation —
  no `PYTHONPATH` override, `fem_em_solver` resolved through the installed
  package exactly as `pip install -e ".[dev]"` leaves it in CI. That second run
  is the one that matters: it proves `src/sitecustomize.py` is not load-bearing
  for this job, because sourcing the mode script sets `PYTHONPATH` itself and
  nothing overwrites it afterwards.
- **Negative control:** the same file in **real** mode with
  `FEM_EM_REQUIRE_COMPLEX=1` → 3 failed, 1 passed in 2 s, "FEM_EM_REQUIRE_COMPLEX=1
  but PETSc.ScalarType is float64 … the complex build was not picked up". The
  job therefore cannot go green by skipping, which was the whole failure mode
  being guarded.
- **Coverage delta:** 13 `@complex_only` tests exist; 10 now run in CI. The
  three that do not are blocked on known-issues.md entries 1
  (`DummyMagnetostaticSolver`, 2 tests) and 2 (residual-trend classifier, whose
  non-complex sibling fails too, so the file has nothing selectable). Both
  entries now say so, and the CI file carries a comment at the exact place the
  files should be added when they are fixed.
- **Tier / cost:** smoke. 46 s + 32 s + 2 s, all `mpiexec -n 2`, well inside
  budget.
- **Logs:** `20260731T033128Z_OPS-10-probe.log`,
  `20260731T033311Z_OPS-10-ci-fidelity.log` (**log of record**),
  `20260731T033355Z_OPS-10-negctl.log`.
- **Branch (if parked):** none; landed on `main`.
- **Denied commands:** none.
- **Caveat for the reviewer:** the job is verified by local reproduction of its
  invocation, not by a GitHub Actions run — nothing in this session can trigger
  one. The residual risk is CI-environment-specific: whether
  `dolfinx/dolfinx:v0.7.2` on a runner carries both builds at the same paths as
  our image (it is the same tag our Dockerfile bases on, so this is likely but
  unproven), and whether `source` behaves in the runner's default shell (it is
  `bash -e {0}`, so yes). First push to `main` settles both.
- **Next-attempt hypothesis:** On deck is now empty, so the next run falls back
  to `MAT-6` (Dodd–Deeds loading gate) per §9's "obvious next entry" sentence.
  That is a genuinely new closed form rather than a rescope, so it may want the
  review to size it first; the review is also overdue to refill On deck to six.

## 2026-07-31T05:05Z — MAT-6 step 1 (Dodd–Deeds closed form) — partial

- **Outcome:** partial. `MAT-6` step 1 (the closed form) is landed and gated on
  `main`; step 2 (the FEM gate, which is what actually closes the chunk) is not
  started. §7 status `⬜` → `🟡` with both steps written out.
- **Item selection:** every On-deck item was done, so this is the §9 **fallback**
  to `MAT-6` per `implementer-run.md` step 2. Scoped to one run by splitting the
  chunk: closed form now, FEM comparison next.
- **What was built:** `src/fem_em_solver/utils/dodd_deeds.py` —
  `ΔZ = jωπμ₀a²∫₀^∞ Γ(α)J₁(αa)²e^{−2αh}dα` with `Γ = (μᵣα−α₁)/(μᵣα+α₁)`,
  `α₁ = √(α²+jωμ₀μᵣσ)`, integrated piecewise between the zeros of `J₁(αa)`
  (one semi-infinite oscillatory `quad` under-resolves silently) and truncated
  where `e^{−2αh}` has killed the integrand. Plus
  `tests/validation/test_dodd_deeds_impedance.py`, 6 tests, no dolfinx, real
  build.
- **Measured numbers:**
  - **Anchor** — perfect-conductor limit: `ΔL` from the Hankel integral at
    σ = 1e12 S/m is `−6.753682e−08 H`; minus the image mutual inductance
    `−2πa·A_φ(a,2h)` from the elliptic-integral `A_φ` in `AnalyticalSolutions`
    is `−6.753694e−08 H`. **0.0002%.** Two derivations sharing no algebra
    beyond μ₀ — this is what pins the `jωπμ₀a²` prefactor and the sign of Γ.
  - σ = 0 gives `|ΔZ|/|ΔZ_pec| < 1e−12` (Γ ≡ 0 identically, not just small).
  - σ = 1e6 S/m: `ΔZ = 9.7728e−02 − 5.4108e+01j Ω` — dissipates, expels flux.
  - Thin-skin identity `ΔR/(ΔX−ΔX_pec)` → 0.99148, 0.99729, 0.99914, 0.99973
    for σ = 1e5…1e8 S/m: monotone to 1, as `Γ+1 ≈ αδ(1−j)` requires.
  - `ΔR ∝ ω^0.5009` over a decade at σ = 1e7 (expect exactly 0.5).
- **The one real dead end, kept as evidence:** the first draft used the full
  complex permittivity `ε_c` in the half-space while keeping the
  magnetoquasistatic `e^{−α|z−h|}` kernel in free space. Inconsistent, and the
  σ = 0 test caught it immediately — vacuum reflected `Γ = −1` at α = 0
  (log `20260731T050326Z_MAT-6-step1.log`, the only failing run). Fixed by going
  consistently eddy-current, which is what Dodd & Deeds (1968) actually is.
  **Consequence the reviewer must not lose:** the kernel needs loss tangent
  `σ/(ωε₀εᵣ) ≫ 1`, and gelled saline at 127.74 MHz sits at **≈ 1.26**. So step 2
  cannot point this at saline as written — it must either gate against a high-σ
  half-space or upgrade to the full-wave kernel first. Both the module docstring
  and the §7 entry say so.
- **Tolerance tightened, not loosened:** the image-limit bound was drafted at
  0.5% and moved to **2e−5** once the measurement came in at 0.0002%, with the
  number and log in a code comment.
- **Tier / cost:** smoke. 2 s at `-n 2` for the 6 new tests; 3 s for the final
  run including `tests/unit` (11 passed). No solver runs at all this session.
- **Logs:** `20260731T050326Z_MAT-6-step1.log` (the instructive failure),
  `20260731T050449Z_MAT-6-step1b.log` (**log of record**, 6 passed),
  `20260731T050500Z_MAT-6-step1-numbers.log` (printed measurements, `-s`),
  `20260731T050515Z_MAT-6-step1-final.log` (tightened bound + unit regression).
- **Branch (if parked):** none. The work is self-contained, green, and adds no
  half-applied change, so it landed on `main` rather than an `attempt/*` branch;
  `main` is clean.
- **Denied commands:** none.
- **Next-attempt hypothesis:** step 2's cost driver is the air box, not the
  solve — the PEC outer boundary contaminates ΔZ unless it is far out. The
  reaction-integral form `ΔZ = −(1/I²)∫(E_loaded − E_free)·J dV` over two solves
  differing *only* in σ should cancel most of that truncation error along with
  the coil self-impedance, which is why it is the recommended route in §7. Next
  run should cost-probe the mesh before committing to a box size, and settle the
  kernel question (high-σ gate vs full-wave upgrade) first, since it decides the
  material parameters the mesh is built for.

## 2026-07-31T09:50Z — MAT-6 step 2a (loop-over-half-space fixture + box probe) — complete

- **On-deck item:** §9 item 1 (first open item; taken as written, not rescoped).
- **What landed:** `MeshGenerator.loop_over_half_space_domain` (torus over a
  slab-filled lower half-box, graded three-scale sizing: wire / near-field /
  far) and `scripts/probes/mat6_step2a_probe.py`, which solves loaded + free at
  each box size and extracts `ΔZ = −(1/I²)∫(E_loaded−E_free)·J dV` over the wire.
  Nothing is asserted — step 2a's product is the measurement, and the §7 entry
  now carries it. `MAT-6` stays 🟡; step 2b is the gate.
- **Configuration chosen, all three eddy-current constraints checked:**
  f = 10 MHz, σ = 100 S/m, εᵣ = 1, a = 0.04 m, h = 0.02 m, r_wire = 0.0025 m.
  Loss tangent 1.80e5; δ = 15.915 mm at 3.18 near-cells per δ; slab 6.28 δ deep;
  k₀·(box diagonal) = 0.073/0.109/0.145 at W = 0.10/0.15/0.20 m. Low f with high
  σ is the combination that satisfies "δ resolvable" and "k₀·box ≪ 1" together.
- **Measured numbers (the deliverable):** closed form +0.322596 − j0.615868 Ω.
  W = 0.10 (96 726 cells) ΔZ = +0.30952 − j0.39841; W = 0.15 (138 619)
  +0.32769 − j0.50027; W = 0.20 (205 327) +0.32857 − j0.52812.
  (i) **Box sensitivity** 0.10→0.15: ΔR 5.87%, ΔX 25.6%; 0.15→0.20: ΔR 0.268%,
  ΔX 5.57%. (ii) **Wall clock per solve** at `-n 2`: 14.4 / 26.5 / 69.0 s, mesh
  6.5 / 9.9 / 14.5 s.
- **The finding that matters:** ΔR converges (1.6–1.9% off the closed form,
  box-insensitive by W = 0.15); ΔX does not (−35% → −19% → −14%, still moving
  5.6% per box step). Re-evaluating the *filamentary* reference at h ± r_wire
  spreads ΔR by 38% and ΔX by 30%, so the finite torus section is a first-order
  modelling error the probe could not separate from PEC-wall imaging. §9 item 2
  is rescoped accordingly: gate ΔR at 5% + a σ = 0 control, ΔX on sign and order
  of magnitude only, with the reason in a code comment.
- **Two traps, each cost a run:** (1) `ufl.max_value` does not compile in the
  complex build (UFL refuses conditionals on complex operands), so
  `test_circular_loop.py::azimuthal_current_density` cannot be reused verbatim
  in a frequency-domain solve — regularise inside the sqrt instead. (2) A killed
  run leaves a stale FFCx lock and the *next* run dies with "JIT compilation
  timed out, probably due to a failed previous compile"; `rm -rf ~/.cache/fenics`
  in the container clears it. Both are recorded in §7.
- **Also fixed while measuring:** ΔZ ∝ 1/I², and the meshed torus is 8% short of
  the analytic volume, so the probe divides by the *meshed* loop current
  (∫J dV / 2πa) rather than the nominal 1 A. Uncorrected this is a ~17% ΔZ error
  that looks like physics.
- **Tier / cost:** heavy. Two probe runs of 96 s and 196 s; three earlier
  cost-probe/diagnostic runs of 180 s (timed out on a cold JIT compile), 0 s
  (stale lock) and 8 s / 13 s. No command exceeded its `timeout`.
- **Logs:** `20260731T093422Z_MAT-6-step2a-costprobe.log` (cold-JIT timeout),
  `20260731T093914Z_MAT-6-step2a-costprobe3.log` (pipeline first working),
  `20260731T094030Z_MAT-6-step2a-diag.log` (Z_free/Z_loaded split),
  `20260731T094211Z_MAT-6-step2a-boxprobe.log` and
  `20260731T094411Z_MAT-6-step2a-boxprobe-w20.log` (**logs of record**),
  `20260731T094911Z_MAT-6-step2a-regression.log` (`tests/mesh` minus birdcage +
  `tests/unit`, 18 passed / 1 failed in 8.8 s — the failure is known-issues
  entry 5, `test_coil_phantom_domain_sizing_...`, pre-existing and untouched by
  the additive `io/mesh.py` change).
- **Branch (if parked):** none — `main` is clean and green.
- **Denied commands:** none. (One Bash call was rejected for unanalyzable shell
  syntax — a `$(...)` inside a compound command — and was re-issued split up.)
- **Next-attempt hypothesis:** step 2b's ΔR gate should pass at W = 0.15 as
  measured. If ΔX is wanted quantitatively later, thin the wire to
  r_wire ≤ 1.25 mm *first* (h/r_wire ≥ 16) and only then grow the box — the
  finite-section spread is 30%, larger than the 5.6% of box motion left, so
  spending cells on a bigger box before thinning the wire buys nothing.
