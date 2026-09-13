# AGENTS.md — for any agent that is not Claude Code

`CLAUDE.md` is the full onboarding document and everything in it applies to
you. This file exists because the project's safety rails are enforced by
Claude-Code-specific machinery — a `PreToolUse` hook and a permission list in
`.claude/settings.json` — and **none of it will run for you**. What that hook
mechanically prevents, you have to not do by reading.

Read `CLAUDE.md` first, then `PROJECT_PLAN.md` §2 (what is real), §4
(definition of done) and §5 (execution policy). This file is the short list of
things that will otherwise bite.

## The four rules nothing will stop you breaking

1. **Never put an Ansys number in a tracked file.** Licence terms restrict
   disclosure of AED benchmark results. They live only in the gitignored
   `examples/ansys_benchmarks/*/aed_results/`, `*/COMPARISON_private.md` and
   `docs/private/`. Tracked files, journals and commit messages get the
   qualitative verdict — agree / disagree / inconclusive, and what it decides
   — and nothing else. A commit is the point of no return: removing a number
   from history is a rewrite, not a revert.

   `scripts/testing/check_private_leak.py` catches this, and
   `scripts/testing/install_git_hooks.sh` wires it into `pre-commit`. **Run
   the installer once per clone** — `.git/hooks` is not tracked, so a fresh
   clone has no protection at all.

2. **Twelve cores, and every compute command goes through the harness.**
   `scripts/testing/run_and_log.sh <CHUNK-ID> "docker compose exec -T
   fem-em-solver bash -lc '…'"`, with `timeout -k 30 <ceiling>` inside it.
   `mpiexec -n 12` is the hard ceiling (16 only in the weekly XL slot, which
   only the weekly review commissions). This is a shared machine and the
   sandbox cannot see other users' load — see §5.1.

3. **Never loosen a failing assertion.** A missed band is evidence about the
   test as much as the code. If measurement shows the bound itself was wrong,
   change it *with the measurement recorded beside it* and say so in the
   commit. Quietly widening a tolerance destroys the only thing this
   repository is actually worth.

4. **Respect section ownership.** The daily review owns §7 chunk rows and the
   §9 On-deck queue. The weekly review owns §1, §6, §10, examples health and
   Ansys commissioning, and **never edits §9**. An implementer edits the row
   for its own chunk. Writing outside your role's section silently undoes
   someone else's reasoning. A chunk's history file under
   `docs/planning/chunks/<ID>.md` is part of its §7 row and carries the same
   ownership (and the same no-Ansys-numbers rule).

## What a review role may and may not do

Planning and review sessions are **documentation only — no solves, no
meshing**. Reading harness logs is expected. If you find yourself about to run
compute, you are outside the role.

Write access you need: `PROJECT_PLAN.md`, `docs/status/dashboard.md`,
`docs/testing/known-issues.md`, `docs/testing/attempts.md`, `docs/private/`.
Nothing else, and no `src/` or `tests/` edits from a review.

## How to read a result honestly here

This repository's value is that it does not overclaim, and its conventions
encode that. The traps that have actually cost time:

- **A symmetry, reciprocity or passivity gate is a weak gate.** A port model
  wrong by a constant factor passes all three. Do not read one as an accuracy
  claim; §2.2 says so repeatedly and means it.
- **A censored measurement is not a measurement.** "Peaked at exactly the
  container limit" bounds demand from below and licenses no extrapolation.
- **A log with no `## Exit` footer establishes nothing** — not the wall time,
  not the pass count. Check the footer before quoting any number from a log.
- **Distinguish asserted from printed.** A number the run printed is not a
  gate. Every claim in a chunk row must trace to an executed `assert` or be
  labelled as a record.
- **A pre-registered number that fails is a negative result to report**, not a
  decision to make in the moment. Journal it, mark the row, stop.

## Practical notes

- Frequency-domain work needs the complex build:
  `source /usr/local/bin/dolfinx-complex-mode` and `FEM_EM_REQUIRE_COMPLEX=1`,
  with `tests/environment` first in the pytest path list. Real mode raises.
- `docs/testing/known-issues.md` lists failures that predate you. Check it
  before debugging anything red.
- Logs older than 7 days are gzipped in place; read them with `zcat`.
- Commit code, tests, harness logs and plan updates together.
