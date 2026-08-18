# DolfinX 0.7.2 → 0.11.0.post0 migration pack (`OPS-18`)

Cached 2026-08-18 by an interactive operator session for the `OPS-18`
upgrade, because **scheduled implementer sessions have no network**
(`implementer-run.sh` disallows WebFetch/WebSearch and the sandbox blocks
network commands). Everything here was fetched from public sources on
that date; provenance is cited per file. This pack is a *map*, not an
authority — **the installed 0.11 API inside the new container is the
ground truth**; when this pack and the container disagree, trust the
container and note the discrepancy in the run journal.

Files:

- `migration-map.md` — distilled old→new API mapping plus the
  repo-specific hit list (which of our modules each change lands on).
  Start here.
- `release-notes.md` — per-version summaries of the upstream release
  notes for 0.8.0, 0.9.0 (including the curated blog post), and 0.11.0.
  **Known gap:** 0.10.0's notes could not be retrieved (GitHub page did
  not render, no curated blog exists); 0.10-era changes must be
  discovered by introspection against the installed API.
- `idioms-0.11.md` — verbatim 0.11 code idioms excerpted from the
  upstream demos (`demo_poisson.py`, `demo_gmsh.py`, tag v0.11.0):
  `LinearProblem`, gmsh interop, tag handling, XDMF output.

Sources: github.com/FEniCS/dolfinx releases (v0.8.0, v0.9.0, v0.11.0),
fenicsproject.org/blog/v0.9.0/, raw demo files at tag v0.11.0.
