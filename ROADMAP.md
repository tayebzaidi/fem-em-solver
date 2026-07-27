# ROADMAP.md — merged into PROJECT_PLAN.md

This file is retained only as a redirect. As of 2026-07-27 the roadmap and the
project plan were consolidated into a single source of truth:

## → [PROJECT_PLAN.md](PROJECT_PLAN.md)

Everything that used to live here now has a home there:

| Was in `ROADMAP.md` | Now in `PROJECT_PLAN.md` |
|---|---|
| Mission | §1 Mission |
| Ground rules / quality bar | §4 Definition of done |
| Definition of done for a chunk | §4 Definition of done *(revised)* |
| Cron-safe execution policy | §5 Execution policy *(revised)* |
| Resource constraints | §5.1 Compute budget |
| Status legend | §3 Status legend |
| Tracks A–F chunks | §7 Chunk backlog |
| Immediate execution guidance | §9 Immediate sequencing |

**Chunk IDs changed.** The `A1`/`B2`/`C3`-style IDs used throughout git history and
`docs/testing/pending-tests.md` map to new subsystem-prefixed IDs
(`OPS-`, `MAG-`, `GEO-`, `TH-`, `MAT-`, `POST-`, `PORT-`, `WF-`) via the mapping
table in `PROJECT_PLAN.md` §8. Two generations of legacy IDs collided — `E1`–`E4`
referred to different chunks in `ROADMAP.md` than in `pending-tests.md` — which is
the reason the scheme was replaced.

Do not add new chunks here.
