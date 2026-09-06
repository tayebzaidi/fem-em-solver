"""Archive rotation for the weekly planning review (weekly-review.md step 6).

Two verbatim moves, each with a zero-loss check:

  attempts  — move docs/testing/attempts.md lines [first, last] (1-indexed,
              inclusive) to the end of docs/testing/attempts-archive.md,
              preceded by a ``---`` separator.
  plan      — move closed §7 narratives out of PROJECT_PLAN.md into
              docs/planning/plan-archive.md under an entry header, replacing
              each with the result block given in a spec file.

Spec file format for ``plan`` (one or more sections; result-block lines are
copied into PROJECT_PLAN.md exactly as written)::

    === <CHUNK-ID> <first-line> <last-line>
    <result block line 1>
    ...

Sections are applied bottom-up so earlier line numbers stay valid; the
numbers must refer to the file as it is when the tool starts. Every removed
non-blank line must appear in the archive afterwards (set difference over
non-blank lines, the contract in weekly-review.md); the tool refuses to write
anything if that check fails. Never summarises, never edits a line it moves.

Usage:
  python3 scripts/maintenance/rotate_plan_archive.py attempts FIRST LAST DATE
  python3 scripts/maintenance/rotate_plan_archive.py plan SPEC DATE
DATE is the review date written into the archive headers (YYYY-MM-DD).
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "PROJECT_PLAN.md"
PLAN_ARCHIVE = ROOT / "docs" / "planning" / "plan-archive.md"
ATTEMPTS = ROOT / "docs" / "testing" / "attempts.md"
ATTEMPTS_ARCHIVE = ROOT / "docs" / "testing" / "attempts-archive.md"


def _read(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").split("\n")


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines), encoding="utf-8")


def _nonblank(lines) -> Counter:
    return Counter(l for l in lines if l.strip() and l.strip() != "---")


def _zero_loss(before_src, before_arc, after_src, after_arc, added: Counter, label: str):
    """Everything non-blank before must still be somewhere after, minus what we added."""
    before = _nonblank(before_src) + _nonblank(before_arc)
    after = _nonblank(after_src) + _nonblank(after_arc)
    after.subtract(added)
    lost = before - after
    gained = after - before
    if lost or gained:
        for l in list(lost)[:10]:
            print(f"LOST   {label}: {l[:120]!r}")
        for l in list(gained)[:10]:
            print(f"GAINED {label}: {l[:120]!r}")
        raise SystemExit(f"zero-loss check FAILED for {label}: {sum(lost.values())} lost, "
                         f"{sum(gained.values())} unexpected")
    print(f"zero-loss check passed for {label}: {sum(before.values())} non-blank lines conserved")


def rotate_attempts(first: int, last: int, date: str) -> None:
    src = _read(ATTEMPTS)
    arc = _read(ATTEMPTS_ARCHIVE)
    moved = src[first - 1:last]
    header_re = re.compile(r"^## \d{4}-\d{2}-\d{2}")
    n_entries = sum(1 for l in moved if header_re.match(l))
    if not header_re.match(moved[0]):
        raise SystemExit(f"line {first} is not an entry header: {moved[0][:80]!r}")
    if last < len(src) and not (src[last].strip() == "" or header_re.match(src[last])):
        raise SystemExit(f"line {last + 1} is neither blank nor an entry header: {src[last][:80]!r}")
    # Trim the archive's trailing blank lines, then separator, then the moved block.
    while arc and arc[-1].strip() == "":
        arc.pop()
    new_arc = arc + ["", "---", ""] + moved
    new_src = src[:first - 1] + src[last:]
    _zero_loss(src, arc, new_src, new_arc, Counter(), "attempts.md")
    _write(ATTEMPTS, new_src)
    _write(ATTEMPTS_ARCHIVE, new_arc + [""])
    print(f"moved {len(moved)} lines / {n_entries} entries ({date}); attempts.md now "
          f"{len(new_src)} lines, archive {len(new_arc) + 1}")


def rotate_plan(spec_path: Path, date: str) -> None:
    spec_lines = spec_path.read_text(encoding="utf-8").split("\n")
    sections: list[tuple[str, int, int, list[str]]] = []
    head_re = re.compile(r"^=== ([A-Z]+-\d+) (\d+) (\d+)\s*$")
    cur = None
    for l in spec_lines:
        m = head_re.match(l)
        if m:
            cur = (m.group(1), int(m.group(2)), int(m.group(3)), [])
            sections.append(cur)
        elif cur is not None:
            cur[3].append(l)
    if not sections:
        raise SystemExit("no sections in spec")
    for cid, a, b, block in sections:
        while block and block[-1].strip() == "":
            block.pop()
        if not block:
            raise SystemExit(f"{cid}: empty result block")
        if len(block) > 16:
            print(f"warning: {cid} result block is {len(block)} lines (guide ≤ 15)")
    plan = _read(PLAN)
    arc = _read(PLAN_ARCHIVE)
    new_plan = list(plan)
    arc_add: list[str] = []
    added = Counter()
    # Validate spans against the original file, then apply bottom-up.
    spans = sorted(sections, key=lambda s: s[1])
    for i in range(1, len(spans)):
        if spans[i][1] <= spans[i - 1][2]:
            raise SystemExit(f"overlapping spans: {spans[i - 1][0]} and {spans[i][0]}")
    for cid, a, b, block in sorted(sections, key=lambda s: -s[1]):
        moved = plan[a - 1:b]
        if not re.match(r"^(?:[-*] )?\*\*`?" + re.escape(cid), moved[0]):
            raise SystemExit(f"{cid}: line {a} does not open its narrative: {moved[0][:80]!r}")
        while moved and moved[-1].strip() == "":
            moved.pop()
        header = f"## §7 {cid} full narrative — archived {date} (weekly review)"
        arc_add = ["", header, ""] + moved + arc_add
        added[header] += 1
        for l in block:
            if l.strip() and l.strip() != "---":
                added[l] += 1
        new_plan[a - 1:b] = block + [""] if (b < len(plan) and plan[b].strip() != "") else block
        print(f"{cid}: archived {len(moved)} lines from {a}-{b}, result block {len(block)} lines")
    while arc and arc[-1].strip() == "":
        arc.pop()
    new_arc = arc + arc_add
    _zero_loss(plan, arc, new_plan, new_arc, added, "PROJECT_PLAN.md")
    _write(PLAN, new_plan)
    _write(PLAN_ARCHIVE, new_arc + [""])
    print(f"PROJECT_PLAN.md {len(plan)} -> {len(new_plan)} lines; archive {len(arc)} -> {len(new_arc) + 1}")


def main(argv: list[str]) -> None:
    if len(argv) >= 5 and argv[1] == "attempts":
        rotate_attempts(int(argv[2]), int(argv[3]), argv[4])
    elif len(argv) >= 4 and argv[1] == "plan":
        rotate_plan(Path(argv[2]), argv[3])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
