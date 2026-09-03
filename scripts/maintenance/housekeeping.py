#!/usr/bin/env python3
"""Repo housekeeping sweep — implements docs/testing/retention-policy.md.

Usage:
    scripts/maintenance/housekeeping.py --report          # read-only census + plan
    scripts/maintenance/housekeeping.py --apply           # compress / delete / gc, stage changes
    scripts/maintenance/housekeeping.py --check           # exit 1 if any §3 budget is exceeded
    scripts/maintenance/housekeeping.py --report --as-of 2026-09-03

Classes (policy §1):
  gating      log basename cited from PROJECT_PLAN.md, plan-archive.md,
              known-issues.md, examples/**/*.md, docs/validation/**/*.md,
              docs/ports/**/*.md, or pinned in docs/testing/retention-keep.txt
              -> gzip at COMPRESS_DAYS, never deleted
  non-gating  everything else in docs/testing/logs/
              -> gzip at COMPRESS_DAYS, deleted at DELETE_DAYS

Ages come from the UTC timestamp in the filename, never from mtime.
The sweep never modifies log contents, never rewrites history, never
touches journals or probe scripts (those are reported only), and runs no
compute.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "docs" / "testing" / "logs"
KEEP_FILE = ROOT / "docs" / "testing" / "retention-keep.txt"
SWEEP_LOG = ROOT / "docs" / "testing" / "housekeeping.md"
PROBE_DIR = ROOT / "scripts" / "probes"
PLAN = ROOT / "PROJECT_PLAN.md"

CITATION_SOURCES = [
    PLAN,
    ROOT / "docs" / "planning" / "plan-archive.md",
    ROOT / "docs" / "testing" / "known-issues.md",
]
CITATION_GLOBS = ["examples/**/*.md", "docs/validation/**/*.md", "docs/ports/**/*.md"]

COMPRESS_DAYS = 7
DELETE_DAYS = 14

# §3 budgets
LOG_VOLUME_CEILING_MB = 25.0
LOOSE_OBJECTS_CEILING_MIB = 50.0
JOURNAL_CEILINGS = {
    "docs/testing/attempts.md": 6000,
    "docs/testing/known-issues.md": 6000,
    "PROJECT_PLAN.md": 9000,
}

LOG_NAME = re.compile(r"^(?P<ts>\d{8}T\d{6}Z)_(?P<chunk>[A-Za-z0-9._-]+)\.log(?P<gz>\.gz)?$")
CITATION = re.compile(r"\d{8}T\d{6}Z_[A-Za-z0-9._-]+\.log")


def git(*args: str, check: bool = True) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=check, capture_output=True, text=True
    ).stdout


def tracked_logs() -> list[Path]:
    names = git("ls-files", "--", "docs/testing/logs").split()
    return [ROOT / n for n in names if LOG_NAME.match(Path(n).name)]


def cited_basenames() -> set[str]:
    files = list(CITATION_SOURCES)
    for pattern in CITATION_GLOBS:
        files.extend(ROOT.glob(pattern))
    cited: set[str] = set()
    for f in files:
        if f.is_file():
            cited.update(CITATION.findall(f.read_text(encoding="utf-8", errors="replace")))
    if KEEP_FILE.is_file():
        for line in KEEP_FILE.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                cited.add(line.removesuffix(".gz"))
    return cited


def age_days(name: str, as_of: dt.datetime) -> float:
    ts = LOG_NAME.match(name).group("ts")
    stamp = dt.datetime.strptime(ts, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    return (as_of - stamp).total_seconds() / 86400.0


def plan_logs(as_of: dt.datetime):
    cited = cited_basenames()
    compress: list[Path] = []
    delete: list[Path] = []
    census = Counter()
    volume = 0
    for p in tracked_logs():
        m = LOG_NAME.match(p.name)
        base = p.name.removesuffix(".gz")
        gating = base in cited
        age = age_days(p.name, as_of)
        volume += p.stat().st_size if p.exists() else 0
        cls = "gating" if gating else "non-gating"
        census[cls] += 1
        if m.group("gz"):
            census[f"{cls} (gz)"] += 1
        if not gating and age >= DELETE_DAYS:
            delete.append(p)
        elif not m.group("gz") and age >= COMPRESS_DAYS:
            compress.append(p)
    return compress, delete, census, volume, len(cited)


def loose_objects_mib() -> float:
    out = git("count-objects", "-v")
    for line in out.splitlines():
        if line.startswith("size:"):
            return int(line.split()[1]) / 1024.0
    return 0.0


def journal_lines() -> dict[str, int]:
    return {
        rel: sum(1 for _ in (ROOT / rel).open(encoding="utf-8", errors="replace"))
        for rel in JOURNAL_CEILINGS
        if (ROOT / rel).is_file()
    }


def orphan_probes() -> list[str]:
    if not PROBE_DIR.is_dir() or not PLAN.is_file():
        return []
    plan_text = PLAN.read_text(encoding="utf-8", errors="replace")
    orphans = []
    for p in sorted(PROBE_DIR.glob("*.py")):
        m = re.match(r"^([a-z]+)(\d+)", p.stem)
        if not m:
            continue
        chunk = f"{m.group(1).upper()}-{m.group(2)}"
        if not re.search(rf"`{re.escape(chunk)}`|\b{re.escape(chunk)}\b", plan_text):
            orphans.append(f"{p.name} ({chunk})")
    return orphans


def compress_file(p: Path) -> Path:
    target = p.with_name(p.name + ".gz")
    with p.open("rb") as src, gzip.GzipFile(target, "wb", mtime=0) as dst:
        shutil.copyfileobj(src, dst)
    p.unlink()
    return target


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--report", action="store_true", help="read-only census and planned actions")
    mode.add_argument("--apply", action="store_true", help="perform the sweep and stage the result")
    mode.add_argument("--check", action="store_true", help="exit 1 if any §3 budget is exceeded")
    ap.add_argument("--as-of", help="UTC date YYYY-MM-DD to evaluate ages against (default: now)")
    args = ap.parse_args()

    as_of = (
        dt.datetime.strptime(args.as_of, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
        if args.as_of
        else dt.datetime.now(dt.timezone.utc)
    )

    compress, delete, census, volume, n_cited = plan_logs(as_of)
    loose = loose_objects_mib()
    journals = journal_lines()
    orphans = orphan_probes()

    breaches = []
    if volume / 1e6 > LOG_VOLUME_CEILING_MB:
        breaches.append(f"log volume {volume/1e6:.1f} MB > {LOG_VOLUME_CEILING_MB} MB")
    if loose > LOOSE_OBJECTS_CEILING_MIB:
        breaches.append(f"loose objects {loose:.0f} MiB > {LOOSE_OBJECTS_CEILING_MIB:.0f} MiB")
    for rel, n in journals.items():
        if n > JOURNAL_CEILINGS[rel]:
            breaches.append(f"{rel} {n} lines > {JOURNAL_CEILINGS[rel]}")

    print(f"# Housekeeping {'report' if not args.apply else 'sweep'} — as of {as_of:%Y-%m-%d %H:%M} UTC")
    print()
    print("| Metric | Value |")
    print("|---|---:|")
    print(f"| Tracked logs | {sum(v for k, v in census.items() if '(gz)' not in k)} |")
    print(f"| Gating (cited) | {census['gating']} of {n_cited} cited basenames |")
    print(f"| Non-gating | {census['non-gating']} |")
    print(f"| Already compressed | {census['gating (gz)'] + census['non-gating (gz)']} |")
    print(f"| Log volume | {volume/1e6:.1f} MB (ceiling {LOG_VOLUME_CEILING_MB:.0f}) |")
    print(f"| Loose git objects | {loose:.0f} MiB (ceiling {LOOSE_OBJECTS_CEILING_MIB:.0f}) |")
    for rel, n in journals.items():
        print(f"| {rel} | {n} lines (ceiling {JOURNAL_CEILINGS[rel]}) |")
    print()
    print(f"Planned: compress {len(compress)} (≥ {COMPRESS_DAYS} d), delete {len(delete)} non-gating (≥ {DELETE_DAYS} d).")
    if orphans:
        print(f"Orphan probe candidates (chunk ID absent from PROJECT_PLAN.md; report only): {len(orphans)}")
        for o in orphans:
            print(f"  - {o}")
    if breaches:
        print("Budget breaches:")
        for b in breaches:
            print(f"  - {b}")

    if args.check:
        return 1 if breaches else 0

    if not args.apply:
        return 0

    # --apply
    for p in delete:
        git("rm", "-q", "--", str(p.relative_to(ROOT)))
    for p in compress:
        target = compress_file(p)
        git("add", "--", str(target.relative_to(ROOT)))
        git("rm", "-q", "--cached", "--", str(p.relative_to(ROOT)), check=False)
    gc_ran = False
    if loose > LOOSE_OBJECTS_CEILING_MIB:
        subprocess.run(["git", "-C", str(ROOT), "gc", "--quiet"], check=False)
        gc_ran = True

    if not SWEEP_LOG.is_file():
        SWEEP_LOG.write_text(
            "# Housekeeping sweeps\n\n"
            "Append-only record of `scripts/maintenance/housekeeping.py --apply` runs "
            "under docs/testing/retention-policy.md. Deleted logs remain indexed in "
            "test-results.md and recoverable from git history.\n\n"
            "| UTC date | Compressed | Deleted | Log volume after (MB) | gc | Breaches |\n"
            "|---|---:|---:|---:|---|---|\n"
        )
    # The index now reflects the sweep, so ls-files lists the .gz files and not the removed ones.
    after = sum(p.stat().st_size for p in tracked_logs() if p.exists())
    with SWEEP_LOG.open("a") as fh:
        fh.write(
            f"| {as_of:%Y-%m-%d} | {len(compress)} | {len(delete)} | {after/1e6:.1f} | "
            f"{'yes' if gc_ran else 'no'} | {'; '.join(breaches) or '—'} |\n"
        )
    git("add", "--", str(SWEEP_LOG.relative_to(ROOT)))
    print()
    print(f"Applied: compressed {len(compress)}, deleted {len(delete)}, gc={'yes' if gc_ran else 'no'}. "
          "Changes are staged; commit as `chore(housekeeping): weekly sweep YYYY-MM-DD`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
