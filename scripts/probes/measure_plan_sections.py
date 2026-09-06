"""Measure per-chunk narrative size inside PROJECT_PLAN.md §7.

Read-only probe used by the weekly planning review (weekly-review.md step 6)
to find closed chunks whose narrative exceeds the ~50-line guide. Attributes
each §7 line to the most recent chunk ID that opened a block: a table row
``| `ID` |`` or a paragraph/bullet beginning ``**`ID```. Prints the largest
owners with their status glyph and line span. Never edits anything.

Usage: python3 scripts/probes/measure_plan_sections.py [PROJECT_PLAN.md] [N]
       python3 scripts/probes/measure_plan_sections.py PROJECT_PLAN.md --blocks ID,ID,...
The second form prints, per chunk, the contiguous line blocks it owns
(``row`` = its table row, ``nar`` = narrative below a table) and the first
90 characters of its status cell.
"""
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "PROJECT_PLAN.md"
blocks_for = None
if len(sys.argv) > 3 and sys.argv[2] == "--blocks":
    blocks_for = sys.argv[3].split(",")
top = int(sys.argv[2]) if len(sys.argv) > 2 and blocks_for is None else 45
lines = open(path, encoding="utf-8").read().split("\n")

# §7 spans from "## 7." to the next "## " header.
start = next(i for i, l in enumerate(lines) if l.startswith("## 7."))
end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))

row_re = re.compile(r"^\| `([A-Z]+-[0-9]+)`")
open_re = re.compile(r"^(?:[-*] )?\*\*`?([A-Z]+-[0-9]+)`?")
owner = None
size, chars, first, last, status, cell, blocks = {}, {}, {}, {}, {}, {}, {}
for i in range(start, end):
    l = lines[i]
    m = row_re.match(l)
    kind = "nar"
    if m:
        owner = m.group(1)
        kind = "row"
        cells = l.split("|")
        status.setdefault(owner, cells[3].strip()[:2] if len(cells) > 3 else "?")
        cell.setdefault(owner, cells[3].strip()[:90] if len(cells) > 3 else "?")
    else:
        m2 = open_re.match(l)
        if m2:
            owner = m2.group(1)
        elif l.startswith("### ") or l.startswith("## "):
            owner = None
    if owner:
        size[owner] = size.get(owner, 0) + 1
        chars[owner] = chars.get(owner, 0) + len(l)
        first.setdefault(owner, i + 1)
        last[owner] = i + 1
        b = blocks.setdefault(owner, [])
        if b and b[-1][2] == kind and b[-1][1] == i:
            b[-1][1] = i + 1
        else:
            b.append([i + 1, i + 1, kind])

if blocks_for is not None:
    for k in blocks_for:
        print(f"== {k} status: {cell.get(k, '?')}")
        for a, b, kind in blocks.get(k, []):
            print(f"   {kind} {a}-{b} ({b - a + 1} lines)")
    sys.exit(0)

print(f"{'ID':9}{'status':8}{'lines':>6}{'kchars':>8}  first-last")
for k, v in sorted(size.items(), key=lambda kv: -kv[1])[:top]:
    print(f"{k:9}{status.get(k, '?'):8}{v:6}{chars[k] / 1000:8.1f}  {first[k]}-{last[k]}")
print("§7 lines", end - start, "chunks", len(size))
