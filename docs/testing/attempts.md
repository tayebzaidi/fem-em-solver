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
