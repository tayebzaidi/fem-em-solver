#!/usr/bin/env python3
"""EX-12 gate: every file an examples/ guide names must really exist.

Two classes of reference, checked differently:

* **Scripts and modules** (``*.py``) — must exist somewhere in the repo. This
  is what caught ``PARAVIEW_VALIDATION_GUIDE.md``'s ``03_helmholtz_coil.py``,
  removed long before the guide was updated.
* **Run artifacts** (``.xdmf``/``.h5``/``.bp``/``.csv``/``.json``/``.png``/
  ``.msh``) — must exist in the output directory *and* be newer than
  ``--max-age-s``. Existence alone is not enough: ``paraview_output/`` is
  gitignored scratch that accumulates files from months-old runs, so a stale
  leftover would let a dead reference pass. Freshness is what makes the check
  mean "a run actually produces this". This is what caught the
  ``straight_wire.msh`` claim in ``MESH_DIAGNOSTIC_GUIDE.md`` (no run has ever
  written it) and the ``.bp`` instructions in ``PARAVIEW_GUIDE.md`` (VTX export
  raises on the N1curl potential, so the directory is never written).

Usage (run it *after* the examples whose artifacts are being checked):

    python3 scripts/testing/check_example_doc_references.py \
        --output-dir paraview_output --max-age-s 3600

Exit status 0 if every reference resolves, 1 otherwise, with one line per
violation.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ARTIFACT_SUFFIXES = (".xdmf", ".h5", ".bp", ".csv", ".json", ".png", ".msh")

# A filename-shaped token, with the extension not followed by another word
# character so "matplotlib.pyplot" does not read as "matplotlib.py".
REFERENCE_RE = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|" + "|".join(s[1:] for s in ARTIFACT_SUFFIXES) + r")(?![A-Za-z0-9_])"
)

# References that are deliberately not repo files or run outputs. Every entry
# carries the reason it is exempt; an empty reason is not allowed.
ALLOWLIST: dict[str, str] = {
    "lineplot.csv": (
        "user-created: the ParaView 'Plot Over Line' filter writes it by "
        "whatever name the reader chooses; the guide snippet is illustrative"
    ),
}


def collect_references(doc_paths: list[Path]) -> dict[str, list[str]]:
    """Map referenced filename -> list of "<relpath>:<line>" citation sites."""
    references: dict[str, list[str]] = {}
    for doc in doc_paths:
        rel = doc.relative_to(REPO_ROOT)
        for lineno, line in enumerate(doc.read_text().splitlines(), start=1):
            for match in REFERENCE_RE.finditer(line):
                name = Path(match.group(0)).name
                references.setdefault(name, []).append(f"{rel}:{lineno}")
    return references


def repo_basenames() -> set[str]:
    """Every file basename tracked in the source and example trees."""
    names: set[str] = set()
    for root in ("src", "examples", "scripts", "tests"):
        for path in (REPO_ROOT / root).rglob("*.py"):
            names.add(path.name)
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="paraview_output",
        help="directory the examples write artifacts to (default: paraview_output)",
    )
    parser.add_argument(
        "--max-age-s",
        type=float,
        default=3600.0,
        help="an artifact older than this is treated as a stale leftover, not "
        "as evidence that a run produces it (default: 3600)",
    )
    parser.add_argument(
        "--docs-root",
        default="examples",
        help="tree whose *.md files are scanned (default: examples)",
    )
    args = parser.parse_args()

    docs_root = REPO_ROOT / args.docs_root
    output_dir = REPO_ROOT / args.output_dir
    doc_paths = sorted(docs_root.rglob("*.md"))
    if not doc_paths:
        print(f"FAIL: no markdown guides found under {docs_root}")
        return 1

    references = collect_references(doc_paths)
    known_scripts = repo_basenames()
    in_tree_artifacts = {
        path.name
        for suffix in ARTIFACT_SUFFIXES
        for path in docs_root.rglob(f"*{suffix}")
    }
    now = time.time()
    violations: list[str] = []

    for name in sorted(references):
        sites = ", ".join(references[name])
        if name in ALLOWLIST:
            continue
        if name.endswith(".py"):
            if name not in known_scripts:
                violations.append(f"{name}: no such file in the repo  [{sites}]")
            continue

        # An artifact committed next to its own case (the `ans:` benchmarks keep
        # theirs in the case directory) is its own evidence — existence is
        # enough. Only the shared scratch directory needs the freshness rule.
        if name in in_tree_artifacts:
            continue

        target = output_dir / name
        if not target.exists():
            violations.append(
                f"{name}: no run produced it in {args.output_dir}/, and it is "
                f"not committed under {args.docs_root}/  [{sites}]"
            )
            continue
        age = now - target.stat().st_mtime
        if age > args.max_age_s:
            violations.append(
                f"{name}: stale in {args.output_dir}/ ({age / 3600:.1f} h old, "
                f"limit {args.max_age_s / 3600:.1f} h) — rerun the example that "
                f"writes it, or the reference is dead  [{sites}]"
            )

    checked = len(references) - len(ALLOWLIST & references.keys())
    print(
        f"Scanned {len(doc_paths)} guide(s) under {args.docs_root}/, "
        f"{checked} distinct file reference(s) checked, "
        f"{len(ALLOWLIST & references.keys())} allowlisted."
    )
    if violations:
        print(f"FAIL: {len(violations)} dead reference(s):")
        for violation in violations:
            print(f"  - {violation}")
        return 1
    print("PASS: every referenced file exists (artifacts fresh within the window).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
