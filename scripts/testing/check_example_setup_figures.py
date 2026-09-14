#!/usr/bin/env python3
"""`EX-57` census: which example guides carry a committed setup figure.

Every script ``./run_examples.sh --list`` enumerates owes its same-stem guide
a ``## Setup figure`` section that embeds one PNG from the group's
``figures/`` directory (``![...](figures/<basename>_setup.png)``), so a reader
sees the problem geometry — tagged regions, slice plane, ports — before any
number. This script is the mechanical reading of that obligation, and the
daily review's step 6 uses ``--next`` to pick the example the next figure slot
takes, in a fixed order, without judgment.

Coverage states per example:

* ``ok``      — heading present, image reference present, file exists on
  disk, and the file is ``<= --max-kib`` (600 KiB default; the corpus is
  ~50 guides and a tracked PNG is forever).
* ``missing`` — no ``## Setup figure`` heading (the example still owes one).
* ``broken``  — heading present but the image reference or the file is
  absent, or the file is over the size cap. A guide that *claims* a figure it
  does not carry is the same defect class as a dead reference
  (`EX-12`) and is what this census exists to catch.

Exit codes follow the docrefs checker's contract (`OPS-19`): ``0`` when every
example is ``ok``, ``2`` when some are ``missing`` (information — work still
owed, nothing wrong), ``1`` when any is ``broken``.

Usage::

    python3 scripts/testing/check_example_setup_figures.py          # table
    python3 scripts/testing/check_example_setup_figures.py --next   # one path
    python3 scripts/testing/check_example_setup_figures.py --next 3 # next three

The listing order is the runner's own ``--list`` order, so "next" is stable
across runs and across reviews.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "testing"))

from check_example_doc_references import (  # noqa: E402
    markdown_headings,
    runnable_examples,
)

FIGURE_HEADING = "Setup figure"
FIGURE_DIRNAME = "figures"
IMAGE_RE = re.compile(r"!\[[^\]]*\]\((?P<target>[^)\s]+\.png)\)")

EXIT_OK, EXIT_BROKEN, EXIT_MISSING = 0, 1, 2


def guide_for(script: Path) -> Path:
    return script.with_suffix(".md")


def figure_section(text: str) -> str | None:
    """Body of the ``## Setup figure`` section, or ``None`` when absent."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("#") and FIGURE_HEADING.lower() in line.lower():
            start = i
            break
    if start is None:
        return None
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("#") and (len(line) - len(line.lstrip("#"))) <= level:
            break
        body.append(line)
    return "\n".join(body)


def assess(script: Path, max_kib: float) -> tuple[str, str]:
    """(state, detail) for one runnable example."""
    guide = guide_for(script)
    if not guide.is_file():
        return "missing", "no same-stem guide (docrefs checker owns that violation)"
    text = guide.read_text(encoding="utf-8", errors="replace")
    if not any(FIGURE_HEADING.lower() in h for h in markdown_headings(text)):
        return "missing", f"no '## {FIGURE_HEADING}' heading"
    section = figure_section(text) or ""
    images = IMAGE_RE.findall(section)
    if not images:
        return "broken", "heading present but no ![..](….png) image in the section"
    problems = []
    for target in images:
        if target.startswith(("http://", "https://", "/")):
            problems.append(f"{target}: must be a repo-relative path under {FIGURE_DIRNAME}/")
            continue
        file = (guide.parent / target).resolve()
        if FIGURE_DIRNAME not in Path(target).parts:
            problems.append(f"{target}: not under {FIGURE_DIRNAME}/")
        if not file.is_file():
            problems.append(f"{target}: file not found")
            continue
        kib = file.stat().st_size / 1024.0
        if kib > max_kib:
            problems.append(f"{target}: {kib:.0f} KiB > {max_kib:.0f} KiB cap")
    if problems:
        return "broken", "; ".join(problems)
    return "ok", ", ".join(images)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--next",
        nargs="?",
        const=1,
        type=int,
        default=None,
        metavar="N",
        help="print only the next N examples (default 1) still owing a figure, one repo-relative script path per line",
    )
    parser.add_argument("--max-kib", type=float, default=600.0, help="size cap per figure (default 600 KiB)")
    args = parser.parse_args()

    rows = []
    for script in runnable_examples():
        state, detail = assess(script, args.max_kib)
        rows.append((script.relative_to(REPO_ROOT), state, detail))

    counts = {s: sum(1 for _, st, _ in rows if st == s) for s in ("ok", "missing", "broken")}

    if args.next is not None:
        owed = [str(p) for p, st, _ in rows if st == "missing"]
        for path in owed[: args.next]:
            print(path)
    else:
        width = max((len(str(p)) for p, _, _ in rows), default=20)
        for path, state, detail in rows:
            print(f"{str(path):<{width}}  {state:<8} {detail}")
        print()
    print(
        f"SUMMARY: examples={len(rows)} ok={counts['ok']} missing={counts['missing']} "
        f"broken={counts['broken']}",
        file=sys.stderr if args.next is not None else sys.stdout,
    )
    if counts["broken"]:
        return EXIT_BROKEN
    if counts["missing"]:
        return EXIT_MISSING
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
