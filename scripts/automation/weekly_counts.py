#!/usr/bin/env python3
"""Mechanical counts for the weekly review's progress-vs-cost section.

    scripts/automation/weekly_counts.py                # since the last weekly-review commit
    scripts/automation/weekly_counts.py --since 2026-09-13T09:50:07-05:00

Prints one markdown block to stdout. It **counts and never judges**: what was
learned, which workflow became supported, and what to continue or stop are the
review's to write (docs/automation/weekly-review.md step 2b). The point of
the script is that the review spends its tokens on that judgement and not on
counting rows.

Read-only, no solves, no network, stdlib only. Every figure names its source;
the token table reads Claude Code's own session transcripts, outside the repo.
A figure that cannot be measured is printed as `unavailable` with the reason —
never estimated, never omitted. Nothing here is a score, and three of these
numbers are explicitly NOT success measures: commit count, queue depth and
machine time spent.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEEKLY_SUBJECT = r"^docs(plan): weekly review"
TS_FMT = "%Y%m%dT%H%M%SZ"
SAME_SESSION_H = 12
UTC = dt.timezone.utc


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          capture_output=True, text=True).stdout


def interval_start(since_arg: str | None) -> tuple[dt.datetime, str]:
    if since_arg:
        return dt.datetime.fromisoformat(since_arg).astimezone(UTC), f"--since {since_arg}"
    # A weekly session commits several times under this subject, the first of
    # them (the archive rotation, step 6's commit-first rule) BEFORE this script
    # runs — so "the last such commit" would be minutes old. Commits younger
    # than SAME_SESSION_H belong to the session now running and are skipped.
    cutoff = dt.datetime.now(UTC) - dt.timedelta(hours=SAME_SESSION_H)
    for line in git("log", "--format=%H %cI", f"--grep={WEEKLY_SUBJECT}").splitlines():
        sha, when_s = line.split()
        when = dt.datetime.fromisoformat(when_s).astimezone(UTC)
        if when < cutoff:
            return when, f"last weekly-review commit {sha[:7]}"
    return dt.datetime.now(UTC) - dt.timedelta(days=7), "no weekly-review commit found; 7 days"


def family(chunk: str) -> str:
    m = re.match(r"[A-Za-z]+", chunk.strip("` "))
    return m.group(0).upper() if m else "?"


# --- sessions (logs/automation, gitignored: present on this box only) --------
def sessions(since: dt.datetime) -> list[str]:
    logdir = ROOT / "logs" / "automation"
    rows: dict[str, Counter] = defaultdict(Counter)
    minutes: dict[str, float] = defaultdict(float)
    n = 0
    for f in sorted(logdir.glob("*.log")):
        ts, _, kind = f.stem.partition("_")
        try:
            start = dt.datetime.strptime(ts, TS_FMT).replace(tzinfo=UTC)
        except ValueError:
            continue
        if start < since:
            continue
        n += 1
        text = f.read_text(encoding="utf-8", errors="replace")
        outcome = re.findall(r"outcome=([a-z-]+) exit=(\d+)", text)
        legacy = re.findall(r"\bexit=(\d+)", text)
        if "holds the lock; skipping" in text:
            label = "skipped-lock"
        elif outcome:
            label = outcome[-1][0]
        elif legacy:                     # pre-2026-09-19 launchers: no outcome= token
            label = "ok" if legacy[-1] == "0" else f"exit={legacy[-1]}"
        elif kind.endswith("-run"):      # xl-run.sh writes no footer of this shape
            label = "ran" if "run_and_log exit=" in text else "no-window"
        else:
            label = "NO FOOTER (died or still running)"
        rows[kind][label] += 1
        minutes[kind] += max(0.0, f.stat().st_mtime - start.timestamp()) / 60.0
    if not n:
        return ["- unavailable — no launcher logs in `logs/automation/` for this interval "
                "(the directory is gitignored; run this on the automation box)"]
    out = ["| Session kind | Count | Outcomes | Wall-minutes |", "|---|---:|---|---:|"]
    for kind in sorted(rows):
        tally = ", ".join(f"{k} ×{v}" for k, v in rows[kind].most_common())
        out.append(f"| {kind} | {sum(rows[kind].values())} | {tally} | {minutes[kind]:.0f} |")
    lost = sum(v for kind in rows for k, v in rows[kind].items()
               if k not in ("ok", "ran", "no-window") and not kind.endswith("-run"))
    out.append("")
    out.append(f"- Sessions that did not end `ok` (lost or skipped slots): **{lost}**. "
               "Before 2026-09-19 a failed launch wrote no footer at all, so older rows read `NO FOOTER`.")
    return out


# --- compute (docs/testing/test-results.md + ledgers) -------------------------
def compute(since: dt.datetime) -> list[str]:
    fam_rows: Counter = Counter()
    fam_secs: Counter = Counter()
    fam_fail: Counter = Counter()
    path = ROOT / "docs" / "testing" / "test-results.md"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 9 or not re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", cells[1]):
            continue
        when = dt.datetime.strptime(cells[1], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        if when < since:
            continue
        fam = family(cells[2])
        fam_rows[fam] += 1
        fam_secs[fam] += int(cells[4]) if cells[4].isdigit() else 0
        fam_fail[fam] += cells[6] not in ("0", "`0`")
    out = ["| Chunk family | Harness runs | Non-zero exits | Elapsed (min) |", "|---|---:|---:|---:|"]
    for fam, _ in fam_secs.most_common():
        out.append(f"| {fam} | {fam_rows[fam]} | {fam_fail[fam]} | {fam_secs[fam] / 60:.1f} |")
    out.append(f"| **all** | {sum(fam_rows.values())} | {sum(fam_fail.values())} | {sum(fam_secs.values()) / 60:.1f} |")
    out.append("")
    out.append("- Elapsed is harness wall-clock, not core-time: ranks are not in the index, so core-hours are "
               "**unavailable** without reading each log's command line. A non-zero exit is a run, not a verdict "
               "(negative controls and refused windows exit non-zero by design).")
    for tier in ("xl", "xxl"):
        ledger = ROOT / "docs" / "testing" / f"{tier}-ledger.md"
        ran, secs, blank = 0, 0.0, 0
        if ledger.exists():
            for m in re.finditer(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|(.*)$", ledger.read_text(encoding="utf-8"), flags=re.M):
                if dt.date.fromisoformat(m.group(1)) < since.date():
                    continue
                cells = [c.strip() for c in m.group(2).split("|")]
                num = re.search(r"\d+(?:\.\d+)?", cells[5]) if len(cells) > 5 else None
                if num and float(num.group(0)) > 0:
                    ran += 1
                    secs += float(num.group(0))
                else:
                    blank += 1
        out.append(f"- `{tier}` windows (`{tier}-ledger.md`): **{ran}** ran, {secs / 3600:.2f} h of box time; "
                   f"{blank} row(s) with no elapsed (never started, or killed). What each window *decided* is the "
                   "review's to state — windows run is not progress.")
    return out


# --- attempts journal ---------------------------------------------------------
def attempts(since: dt.datetime) -> list[str]:
    path = ROOT / "docs" / "testing" / "attempts.md"
    by_chunk: dict[str, Counter] = defaultdict(Counter)
    closed: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"## (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})Z\b(.*)", line)
        if not m:
            continue
        when = dt.datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)
        if when < since:
            continue
        rest = m.group(2)
        # The id is backticked in some headings and bare in others.
        chunk = re.search(r"\b([A-Z]{2,5}-\d+[a-z]?)\b", rest.split("—", 1)[-1])
        closed.extend(re.findall(r"\b([A-Z]{2,5}-\d+[a-z]?)`?\s*(?:⬜|🟡|🧪|⚠️)\s*→\s*✅", rest))
        low = rest.lower()
        if "anomaly" in low:
            kind = "anomaly"
        elif "blocked" in low:
            kind = "blocked"
        elif re.search(r"incomplete|parked|partial|timebox|not complete", low):
            kind = "incomplete"
        elif re.search(r"complete|✅|green|landed|gated", low):
            kind = "complete"
        else:
            kind = "other"
        by_chunk[chunk.group(1) if chunk else "(no chunk id)"][kind] += 1
    if not by_chunk:
        return ["- no journal entries in this interval"]
    total = Counter()
    for c in by_chunk.values():
        total.update(c)
    out = ["- Entries by heading outcome: " + ", ".join(f"{k} ×{v}" for k, v in total.most_common())
           + "  *(heading keywords — a heuristic; read the entry before citing it)*"]
    out.append("- Headings recording a flip to ✅: "
               + (", ".join(f"`{c}`" for c in sorted(set(closed))) if closed else "none")
               + "  *(the journal's claim; §4 compliance is the audit's, not this count's)*")
    repeat = {k: v for k, v in by_chunk.items() if sum(n for o, n in v.items() if o != "complete") >= 2}
    many = {k: v for k, v in by_chunk.items() if sum(v.values()) >= 4 and k not in repeat}
    if repeat:
        out.append("- **Chunks with ≥ 2 non-complete entries** (repeated failure candidates): "
                   + "; ".join(f"`{k}` ({', '.join(f'{o} ×{n}' for o, n in v.items())})" for k, v in sorted(repeat.items())))
    else:
        out.append("- Chunks with ≥ 2 non-complete entries: none")
    if many:
        out.append("- Chunks with ≥ 4 entries of any outcome (where the slots went): "
                   + ", ".join(f"`{k}` ×{sum(v.values())}" for k, v in sorted(many.items(), key=lambda kv: -sum(kv[1].values()))))
    return out


# --- tokens (Claude Code session transcripts, outside the repo) ---------------
# Every session — headless `claude -p` included — writes a JSONL transcript to
# <config>/projects/<repo path with non-alphanumerics as '-'>/<session>.jsonl,
# its subagents to <session>/subagents/*.jsonl. Assistant lines carry the
# API's `usage`; a streamed message repeats its id, so the last line per id wins.
PROMPT_KINDS = (("Scheduled daily review", "daily-review"),
                ("Scheduled weekly planning review", "weekly-review"),
                ("Scheduled implementer run", "implementer"))
USAGE_KEYS = (("input_tokens", "Input Mtok"), ("cache_creation_input_tokens", "Cache write Mtok"),
              ("cache_read_input_tokens", "Cache read Mtok"), ("output_tokens", "Output Mtok"))


def transcript_dir() -> Path:
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
    return base / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))


def session_kind(path: Path) -> str:
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") != "user":
                continue
            c = d.get("message", {}).get("content")
            text = c if isinstance(c, str) else " ".join(
                b.get("text", "") for b in c or [] if isinstance(b, dict))
            return next((k for p, k in PROMPT_KINDS if text.startswith(p)), "interactive")
    return "interactive"


def tokens(since: dt.datetime) -> list[str]:
    tdir = transcript_dir()
    if not tdir.is_dir():
        return [f"- unavailable — no transcript directory `{tdir}` (run this on the automation box, "
                "as the user the cron sessions run as)"]
    by_kind: dict[str, Counter] = defaultdict(Counter)
    by_model: dict[str, Counter] = defaultdict(Counter)
    sessions_seen: dict[str, set] = defaultdict(set)
    for main in tdir.glob("*.jsonl"):
        if main.stat().st_mtime < since.timestamp():
            continue
        kind = session_kind(main)
        last: dict[str, tuple[str, dict]] = {}
        for f in [main, *sorted((tdir / main.stem).glob("subagents/*.jsonl"))]:
            with f.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                        when = dt.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
                    m = d.get("message") or {}
                    if when < since or not m.get("usage") or not m.get("id") or m.get("model") == "<synthetic>":
                        continue
                    last[f"{f.name}:{m['id']}"] = (m.get("model", "?"), m["usage"])
        if not last:
            continue
        sessions_seen[kind].add(main.stem)
        for model, u in last.values():
            for key, _ in USAGE_KEYS:
                by_kind[kind][key] += u.get(key) or 0
                by_model[model][key] += u.get(key) or 0
    if not by_kind:
        return [f"- no transcript messages in this interval (`{tdir}`)"]

    def mtok(c: Counter) -> str:
        return " | ".join(f"{c[k] / 1e6:.2f}" for k, _ in USAGE_KEYS)

    head = " | ".join(label for _, label in USAGE_KEYS)
    out = [f"| Session kind | Sessions | {head} |", "|---|---:|" + "---:|" * len(USAGE_KEYS)]
    for kind in sorted(by_kind):
        out.append(f"| {kind} | {len(sessions_seen[kind])} | {mtok(by_kind[kind])} |")
    total = sum(by_kind.values(), Counter())
    out.append(f"| **all** | {sum(len(s) for s in sessions_seen.values())} | {mtok(total)} |")
    out += ["", f"| Model | {head} |", "|---|" + "---:|" * len(USAGE_KEYS)]
    for model in sorted(by_model):
        out.append(f"| `{model}` | {mtok(by_model[model])} |")
    out.append("")
    out.append("- Source: Claude Code transcripts in `" + str(tdir) + "`, subagents included and "
               "attributed to the session that spawned them; kind from the session's first prompt "
               "(the launchers' `-p` text), everything else is `interactive`. Messages are counted by "
               "their own timestamp, so a session straddling the interval start is split. Tokens only — "
               "no prices: what a token costs depends on the plan, and this script does not judge.")
    return out


# --- git-derived --------------------------------------------------------------
def git_counts(since: dt.datetime) -> list[str]:
    iso = since.isoformat()
    subjects = [s for s in git("log", f"--since={iso}", "--format=%s").splitlines() if s]
    types = Counter(re.match(r"[a-z]+", s).group(0) if re.match(r"[a-z]+[(:]", s) else "other" for s in subjects)
    base = git("rev-list", "-1", f"--before={iso}", "HEAD").strip()
    opened = retired = 0
    if base:
        diff = git("diff", f"{base}..HEAD", "--unified=0", "--", "docs/testing/known-issues.md")
        for line in diff.splitlines():
            if re.match(r"\+#{2,3} ", line):
                if "RETIRED" in line:
                    retired += 1
                else:
                    opened += 1
    parked = [b.strip() for b in git("branch", "--list", "attempt/*", "recovered/*", "--format=%(refname:short)").splitlines() if b.strip()]
    return [
        f"- known-issues headings added since the interval began: **{opened}** opened, **{retired}** retired "
        "(`git diff` on `known-issues.md`; a retitled heading counts as both)",
        f"- `attempt/*` and `recovered/*` branches present now: {len(parked)}"
        + (f" ({', '.join(parked[:8])}{' …' if len(parked) > 8 else ''})" if parked else ""),
        f"- Commits: {len(subjects)} ({', '.join(f'{k} {v}' for k, v in types.most_common())}) — context only, **not a progress measure**",
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", help="ISO timestamp; default: the last 'docs(plan): weekly review' commit")
    args = ap.parse_args()
    since, how = interval_start(args.since)
    now = dt.datetime.now(UTC)
    days = (now - since).total_seconds() / 86400
    print(f"### Mechanical counts — {since:%Y-%m-%d %H:%M}Z → {now:%Y-%m-%d %H:%M}Z "
          f"({days:.2f} days; {how})\n")
    print("*Generated by `scripts/automation/weekly_counts.py`; counts only, no judgement.*\n")
    for title, fn in (("Sessions and lost slots", sessions), ("Compute", compute),
                      ("Attempts journal", attempts), ("Defects and parked work", git_counts),
                      ("Tokens", tokens)):
        print(f"**{title}**\n")
        try:
            print("\n".join(fn(since)))
        except Exception as exc:  # one broken source must not take the others with it
            print(f"- unavailable — `{fn.__name__}` failed: {type(exc).__name__}: {exc}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
