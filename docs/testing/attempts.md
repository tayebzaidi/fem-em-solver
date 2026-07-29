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
