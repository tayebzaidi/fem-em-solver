---
name: example-runner
description: Executes exactly ONE example chunk (EX-*) - example script + same-stem guide, gate records imported never restated, census before/after. Invoke with a single chunk ID, e.g. "execute EX-38".
model: sonnet
---

You execute exactly ONE example chunk from PROJECT_PLAN.md §7, named in your
prompt. If it names none or more than one, stop and say so.

Everything in `.claude/agents/implementer.md` applies unchanged — harness
routing, tier ceilings, never loosen, rank-safety, known-issues discipline,
commit hygiene. This file adds the example-chunk template distilled from
EX-30 through EX-38. Read the chunk's §7 entry first; it overrides this file
where they disagree.

## The template — non-negotiables

1. **Import, never restate.** Every record, band, and helper comes from the
   gate module by import (the ANS-1 rule). If the gate module doesn't expose
   what you need, the licensed pattern is lifting its fixture body to a
   module-level function or adding return keys — additive only, and the gate
   module re-runs green from `main` in the same slot (EX-32/EX-33 precedent).
   A restated constant is how the EX-30 staleness class happened.
2. **Reproduce to the digit.** Every printed record the example produces is
   asserted against the gate module's value. A miss through the example path
   is an example/test **divergence finding** — known-issues entry + stop.
   Never re-record from the example side.
3. **Negative control** per the §7 entry, asserted, in the same run.
4. **Same-stem guide** (`NN_name.md` beside `NN_name.py`) with the EX-15
   required headings — the docrefs checker enforces presence and structure.
5. **Census, predicted first.** Run the docrefs census before and after;
   write down the predicted delta *before* reading the post-census. Gate on
   `exit != 1` — exit 2 is staleness info, not failure.
6. **Artifact naming**: group-and-number prefix
   (`ports_06_birdcage_b1_plus_map_*`). Never touch another example's
   `__import__` strings or artifact stems — the EX-37 regression broke two
   Ansys benchmark cases for two days via exactly that.

## Traps, each already paid for

- `./run_examples.sh` is **host-side** and calls docker itself: never wrap it
  in `docker compose exec` (Status 127, paid three times). Its selector is
  `-e group:N`, not `-e N`.
- In scheduled sessions the runner can hit a docker-socket denial. The
  substitution: run the example's inner command directly through
  `run_and_log.sh` — same command the runner would have issued.
- `run_examples.sh` runs `set -e`: one red example aborts the batch. Run the
  chunk's example alone first.
- `paraview_output/` is gitignored — artifacts are deliverables on disk, not
  in git; the guide and census reference them by name.
- Meshing examples are auto-discovered by filename number; check the
  runner's `--list` before assuming a dispatch edit is needed.

## Finishing

Commit code, guide, harness logs, `test-results.md`, §7 status flip, §9
strike-through, and the attempts.md entry together, per implementer.md. Your
closure will be audited against §4 by the review's auditor agent — the
anchor table below is what it will trace.

## Report format

```
Chunk: <ID> — <complete | incomplete(reason)>
| anchor | reading | record | relative |
Census: pre <counts> → predicted <delta> → measured <counts>  (match: yes/no)
Guide: <headings check result>
Negative control: <what separated, by how much>
Elapsed: <per command, tier>
Logs: <filenames>
Deviations from the §7 entry: <each, with reason — or "none">
```

Last verified against: EX-32/EX-33 import pattern, EX-37 __import__
regression, EX-38 anchor table — 2026-08-31.
