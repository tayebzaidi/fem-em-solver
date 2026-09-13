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

  chunks    — (OPS-46) move a heavy §7 table row's history out of
              PROJECT_PLAN.md into docs/planning/chunks/<ID>.md, byte for
              byte, leaving a short cell with the pointer.

Spec file format for ``chunks`` (one state line per ID, ≤ 2 sentences,
written from the row's last ruling)::

    === <CHUNK-ID>
    <state line>

§7 tables are ``| ID | Title | Status | Tier |`` (one table adds ``| Result |``)
and a row's history accumulates in the Title and Status cells, so the moved
text is the **span between the ID cell and the Tier cell** — both cells and
the unescaped ``|`` between them, exactly as they sit in the row. Cells are
split on unescaped ``|`` only (the rows carry ``\\|``). The chunk file is
``# <ID> — <title>``, a blank line, the span, a newline. The row becomes
``| `ID` | <title> | <glyph> <state line> *History: `docs/planning/chunks/<ID>.md`.* |``
followed by the untouched Tier (and Result) cells. Before the plan is written
the chunk file is re-read and the tool **refuses (exit 1, nothing written to
the plan) unless its body equals the extracted span**; a chunk file that
already exists is never overwritten, only compared, so a byte altered after
extraction is refused on the next run. The state line may carry no digit run
the row does not already carry. ``--dry-run`` prints ID, glyph, span bytes and
replacement bytes and writes nothing; ``--census`` dry-runs every §7 row whose
line exceeds ``--min-bytes`` (default 2048) and prints per-family totals.

Usage:
  python3 scripts/maintenance/rotate_plan_archive.py attempts FIRST LAST DATE
  python3 scripts/maintenance/rotate_plan_archive.py plan SPEC DATE
  python3 scripts/maintenance/rotate_plan_archive.py chunks SPEC [--dry-run]
          [--plan PATH] [--chunks-dir DIR]
  python3 scripts/maintenance/rotate_plan_archive.py chunks --census
          [--min-bytes N] [--plan PATH]
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


CHUNKS_DIR = ROOT / "docs" / "planning" / "chunks"
GLYPHS = ("✅", "🟡", "⬜", "🧪", "🚫", "⚠️", "❌", "⏸️", "🔁")


def _split_unescaped(row: str) -> list[int]:
    """Offsets of every ``|`` in ``row`` not preceded by a backslash."""
    return [i for i, ch in enumerate(row) if ch == "|" and (i == 0 or row[i - 1] != "\\")]


def _section7(plan: list[str]) -> tuple[int, int]:
    start = next(i for i, l in enumerate(plan) if l.startswith("## 7."))
    end = next(i for i in range(start + 1, len(plan)) if plan[i].startswith("## "))
    return start, end


class RowError(Exception):
    pass


def _ncols(plan: list[str], i: int) -> int:
    """Column count of the table row ``i`` sits in, read from its ``| ID |`` header."""
    for j in range(i - 1, -1, -1):
        if plan[j].startswith("| ID |"):
            return len(plan[j].split("|")) - 2
        if not plan[j].startswith("|"):
            break
    raise RowError(f"line {i + 1}: no '| ID |' table header above the row")


def _parse_row(row: str, cid: str, ncols: int) -> dict:
    """Split one §7 table row into prefix / span / suffix, byte-exact.

    Unescaped ``|`` also occur inside code spans (```mpiexec|hydra_pmi_proxy```,
    ``|ΔV|/|V|``), so cells are not counted from the left: the Tier (and Result)
    cells are taken from the right, and the Title/Status boundary is the first
    unescaped ``|`` followed by a status glyph. The moved span — ID cell end to
    Tier cell start — does not depend on where that boundary falls.
    """
    pipes = _split_unescaped(row)
    trailing = ncols - 3  # Tier, plus Result in the MAG table
    # Later MAG rows (MAG-18, MAG-19) omit the Result cell and end on Tier.
    if trailing == 2 and len(pipes) >= 2 and re.match(
            r"\s*(?:(?:smoke|standard|heavy|xl|xxl)\b|—)", row[pipes[-2] + 1:pipes[-1]]):
        trailing = 1
    if ncols not in (4, 5) or not row.endswith("|") or len(pipes) < trailing + 4:
        raise RowError(f"{cid}: {len(pipes)} unescaped pipes for a {ncols}-column table")
    if row[:pipes[1] + 1] != f"| `{cid}` |":
        raise RowError(f"{cid}: ID cell is not exactly '| `{cid}` |'")
    tier_pipe = pipes[-1 - trailing]
    if len(row[tier_pipe:]) > 600:
        raise RowError(f"{cid}: trailing Tier cell(s) are {len(row[tier_pipe:])} chars — misparsed")
    boundary = next((p for p in pipes[2:] if p < tier_pipe
                     and row[p + 1:].lstrip(" *").startswith(GLYPHS)), None)
    if boundary is None:
        raise RowError(f"{cid}: no status cell opening with a known glyph")
    glyph = next(g for g in GLYPHS if row[boundary + 1:].lstrip(" *").startswith(g))
    title = row[pipes[1] + 1:boundary].split(" — ", 1)[0].replace("**", "").strip()
    if len(title) > 160:
        title = title[:160].rsplit(" ", 1)[0] + " …"
    if title.count("`") % 2:
        title = title[:title.rfind("`")].rstrip() + " …"
    # A title head can carry a code span with bare pipes (MAG-18's `|B_h| − |B_ana|`);
    # the title is derived text, not the moved span, so escape them for the table.
    title = re.sub(r"(?<!\\)\|", r"\\|", title)
    if not title or _split_unescaped(title):
        raise RowError(f"{cid}: cannot derive a pipe-free title (got {title[:60]!r})")
    return {"prefix": row[:pipes[1] + 1], "span": row[pipes[1] + 1:tier_pipe],
            "suffix": row[tier_pipe:], "title": title, "glyph": glyph}


def _find_row(plan: list[str], cid: str) -> int:
    start, end = _section7(plan)
    hits = [i for i in range(start, end) if plan[i].startswith(f"| `{cid}` |")]
    if len(hits) != 1:
        raise RowError(f"{cid}: {len(hits)} §7 table rows found (expected exactly 1)")
    return hits[0]


def _replacement(cid: str, parsed: dict, state: str) -> tuple[str, str]:
    new_span = (f" {parsed['title']} | {parsed['glyph']} {state} "
                f"*History: `docs/planning/chunks/{cid}.md`.* ")
    chunk_text = f"# {cid} — {parsed['title']}\n\n{parsed['span']}\n"
    return new_span, chunk_text


def _read_spec(spec_path: Path) -> list[tuple[str, str]]:
    head_re = re.compile(r"^=== ([A-Z]+-\d+)\s*$")
    out: list[tuple[str, list[str]]] = []
    for l in spec_path.read_text(encoding="utf-8").split("\n"):
        m = head_re.match(l)
        if m:
            out.append((m.group(1), []))
        elif out and l.strip():
            out[-1][1].append(l)
        elif l.strip():
            raise SystemExit(f"spec text before the first header: {l[:60]!r}")
    if not out:
        raise SystemExit("no sections in spec")
    res = []
    for cid, body in out:
        if len(body) != 1:
            raise SystemExit(f"{cid}: spec needs exactly one state line, got {len(body)}")
        res.append((cid, body[0].strip()))
    ids = [c for c, _ in res]
    if len(set(ids)) != len(ids):
        raise SystemExit("duplicate IDs in spec")
    return res


def _check_state(cid: str, state: str, row: str) -> None:
    if "|" in state.replace("\\|", ""):
        raise RowError(f"{cid}: state line carries an unescaped '|'")
    if len(re.findall(r"[.!?](?:\s|$)", state)) > 2:
        raise RowError(f"{cid}: state line is more than two sentences")
    row_digits = set(re.findall(r"\d+", row))
    new = [d for d in re.findall(r"\d+", state) if d not in row_digits]
    if new:
        raise RowError(f"{cid}: state line carries digit runs the row does not: {new[:5]}")


def rotate_chunks(spec_path: Path, plan_path: Path, chunks_dir: Path, dry_run: bool) -> int:
    raw = plan_path.read_bytes()
    plan = raw.decode("utf-8").split("\n")
    work = list(plan)
    pending: list[tuple[str, Path, str]] = []
    try:
        for cid, state in _read_spec(spec_path):
            i = _find_row(work, cid)
            row = work[i]
            parsed = _parse_row(row, cid, _ncols(work, i))
            _check_state(cid, state, row)
            new_span, chunk_text = _replacement(cid, parsed, state)
            span_b, new_b = len(parsed["span"].encode()), len(new_span.encode())
            print(f"{cid:9} {parsed['glyph']}  span {span_b:7d} B -> replacement {new_b:4d} B"
                  f"  (row shrinks {span_b - new_b} B)")
            if dry_run:
                print(f"    replacement: {new_span.strip()}")
                continue
            work[i] = parsed["prefix"] + new_span + parsed["suffix"]
            pending.append((cid, chunks_dir / f"{cid}.md", chunk_text))
    except RowError as e:
        print(f"REFUSED: {e}")
        return 1
    if dry_run:
        print("dry run: nothing written")
        return 0
    chunks_dir.mkdir(parents=True, exist_ok=True)
    for cid, path, text in pending:
        if path.exists():
            print(f"{cid}: {path.name} exists — comparing, never overwriting")
        else:
            path.write_bytes(text.encode("utf-8"))
    # Byte-identity gate: re-read every chunk file from disk before the plan moves.
    for cid, path, text in pending:
        on_disk = path.read_bytes()
        header = text.split("\n\n", 1)[0].encode("utf-8") + b"\n\n"
        span = text.encode("utf-8")[len(header):-1]
        body = on_disk[len(header):]
        if not on_disk.startswith(header) or body != span + b"\n":
            where = next((k for k, (a, b) in enumerate(zip(body, span + b"\n")) if a != b),
                         min(len(body), len(span) + 1))
            print(f"REFUSED: {cid}: {path} body differs from the extracted span "
                  f"(first difference at body byte {where}; {len(body)} vs {len(span) + 1} B); "
                  f"plan not written")
            return 1
        print(f"{cid}: chunk-file body equals the extracted span ({len(span)} B)")
    new_raw = "\n".join(work).encode("utf-8")
    plan_path.write_bytes(new_raw)
    print(f"{plan_path.name}: {len(raw)} -> {len(new_raw)} B ({len(raw) - len(new_raw)} B moved out)")
    return 0


def census_chunks(plan_path: Path, min_bytes: int) -> int:
    plan = plan_path.read_bytes().decode("utf-8").split("\n")
    start, end = _section7(plan)
    row_re = re.compile(r"^\| `([A-Z]+)-(\d+)` \|")
    fam: dict[str, list] = {}
    bad = 0
    total_row = total_span = total_new = 0
    for i in range(start, end):
        m = row_re.match(plan[i])
        if not m:
            continue
        row_b = len(plan[i].encode("utf-8"))
        if row_b <= min_bytes:
            continue
        cid = f"{m.group(1)}-{m.group(2)}"
        try:
            parsed = _parse_row(plan[i], cid, _ncols(plan, i))
        except RowError as e:
            print(f"UNPARSEABLE {e}")
            bad += 1
            continue
        new_span, _ = _replacement(cid, parsed, "<state line>")
        span_b, new_b = len(parsed["span"].encode()), len(new_span.encode())
        print(f"{cid:9} {parsed['glyph']}  line {i + 1:5d}  row {row_b:6d} B  span {span_b:6d} B"
              f"  replacement {new_b:4d} B  title {parsed['title'][:50]!r}")
        f = fam.setdefault(m.group(1), [0, 0, []])
        f[0] += 1
        f[1] += row_b
        f[2].append(cid)
        total_row += row_b
        total_span += span_b
        total_new += new_b
    print(f"families (rows over {min_bytes} B):")
    for k, (n, b, ids) in sorted(fam.items(), key=lambda kv: (-kv[1][0], kv[0])):
        print(f"  {k:5} {n:3d} rows  {b:7d} B  {' '.join(ids)}")
    n_rows = sum(f[0] for f in fam.values())
    print(f"CENSUS rows={n_rows} unparseable={bad} row_bytes={total_row} span_bytes={total_span} "
          f"replacement_bytes={total_new} plan_bytes={plan_path.stat().st_size}")
    return 1 if bad else 0


def _chunks_main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="rotate_plan_archive.py chunks")
    ap.add_argument("spec", nargs="?", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--min-bytes", type=int, default=2048)
    ap.add_argument("--plan", type=Path, default=PLAN)
    ap.add_argument("--chunks-dir", type=Path, default=CHUNKS_DIR)
    a = ap.parse_args(argv)
    if a.census:
        return census_chunks(a.plan, a.min_bytes)
    if a.spec is None:
        ap.error("a SPEC is required unless --census")
    return rotate_chunks(a.spec, a.plan, a.chunks_dir, a.dry_run)


def main(argv: list[str]) -> None:
    if len(argv) >= 5 and argv[1] == "attempts":
        rotate_attempts(int(argv[2]), int(argv[3]), argv[4])
    elif len(argv) >= 4 and argv[1] == "plan":
        rotate_plan(Path(argv[2]), argv[3])
    elif len(argv) >= 3 and argv[1] == "chunks":
        sys.exit(_chunks_main(argv[2:]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
