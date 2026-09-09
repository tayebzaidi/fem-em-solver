#!/usr/bin/env python3
"""Refuse to commit an Ansys benchmark number into a tracked file.

Ansys licence terms restrict disclosure of benchmark results (operator
directive 2026-09-02), so AED-derived figures live only in the gitignored
``examples/ansys_benchmarks/*/aed_results/``, ``*/COMPARISON_private.md`` and
``docs/private/``. Until now **nothing mechanical enforced that** — the rule
was held entirely by whichever agent was writing, and one slip would put a
licence-restricted number into git history, where removing it means a
history rewrite rather than a revert.

This makes the rule a mechanism. It is also the reason a non-Claude planning
agent can be given the review role at all: the project's other rails are
Claude-Code-specific hooks, and this one is a git hook that applies to
anything that commits.

    scripts/testing/check_private_leak.py            # staged changes (hook mode)
    scripts/testing/check_private_leak.py --audit    # every tracked file, no
                                                     # already-published subtraction

**Where "secret" comes from.** Only the raw AED exports under
``aed_results/`` — those contain AED output and nothing of ours. The private
markdown deliberately mixes their numbers with ours (that is what makes it a
comparison), so using it as the source would flag our own published figures.

**What counts as a match.** A run of significant digits at least
``MIN_SIGNIFICANT_DIGITS`` long, shared as a prefix. That catches a truncated
quote (writing 0.12345 from 0.1234567890123456) while ignoring the ``50``,
``2026`` and ``1e-3`` that appear on every other line of this repo.

**Already-published numbers are subtracted.** If a figure is already in a
tracked file at HEAD it is not a secret any more, whatever its provenance,
and flagging a second occurrence would be noise. ``--audit`` skips that
subtraction, which is how you find a leak that already happened.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECRET_GLOBS = ["examples/ansys_benchmarks/*/aed_results/*"]
MIN_SIGNIFICANT_DIGITS = 8
# Length alone is not enough: `0.500000` reduces to six digits and would then
# prefix-match any AED value beginning with a 5. Real measured figures carry
# digit *entropy*; round numbers do not, and this repo is full of round ones
# (0.500000000000, 90.0000, 1.000000). Requiring several distinct digits
# separates "a measurement someone could have copied" from "a ratio that came
# out exactly a half". Measured on the tracked tree: this cut the audit from
# 985 hits, all false, to zero.
MIN_DISTINCT_DIGITS = 5

# A number, in any of the spellings these files use: 0.1234567890123456,
# -9.87, 1.1111e+06, 987.6543210987.
NUMBER = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def informative(digits: str) -> bool:
    """Could this digit string identify one specific measured value?"""
    return (len(digits) >= MIN_SIGNIFICANT_DIGITS
            and len(set(digits)) >= MIN_DISTINCT_DIGITS)


def significant_digits(token: str) -> str:
    """The token's significant digits, sign/point/exponent stripped.

    ``0.1234567890123456`` and ``-1.234567890123456e-01`` both reduce to
    ``1234567890123456``, so a number quoted in a different spelling is still
    caught. Leading zeros are not significant and go.
    """
    mantissa = re.split(r"[eE]", token)[0]
    digits = re.sub(r"\D", "", mantissa).lstrip("0")
    return digits


def collect(paths) -> set[str]:
    out: set[str] = set()
    for path in paths:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            continue
        for token in NUMBER.findall(text):
            digits = significant_digits(token)
            if informative(digits):
                out.add(digits)
    return out


def secret_digits() -> set[str]:
    files = []
    for pattern in SECRET_GLOBS:
        files.extend(ROOT.glob(pattern))
    return collect(f for f in files if f.is_file())


def published_digits() -> set[str]:
    """Significant digits already in tracked files **at HEAD**.

    "At HEAD" is load-bearing and was a bug once: reading the working tree via
    ``git ls-files`` includes the index, so a freshly staged leak counted as
    already-published and whitelisted itself — the check passed a planted AED
    figure in its own positive control. Files touched by this commit are
    therefore read from ``HEAD``, not from disk, and a file that is new in this
    commit contributes nothing.
    """
    skip = (".log", ".gz", ".png", ".pdf", ".s4p")
    try:
        names = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files"],
            check=True, capture_output=True, text=True,
        ).stdout.split()
        staged = set(subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--cached", "--name-only"],
            check=True, capture_output=True, text=True,
        ).stdout.split())
    except Exception:
        return set()

    out = collect(ROOT / n for n in names
                  if not n.endswith(skip) and n not in staged)
    for n in staged:
        if n.endswith(skip):
            continue
        try:
            text = subprocess.run(
                ["git", "-C", str(ROOT), "show", f"HEAD:{n}"],
                check=True, capture_output=True, text=True,
            ).stdout
        except Exception:
            continue  # new in this commit: nothing of it is published yet
        for token in NUMBER.findall(text):
            digits = significant_digits(token)
            if informative(digits):
                out.add(digits)
    return out


def staged_additions():
    """(file, line_no, text) for every added line in the staged tracked diff."""
    try:
        diff = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--cached", "--unified=0",
             "--no-color", "--diff-filter=ACMR"],
            check=True, capture_output=True, text=True,
        ).stdout
    except Exception:
        return
    path, lineno = None, 0
    for line in diff.split("\n"):
        if line.startswith("+++ b/"):
            path, lineno = line[6:], 0
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            if path:
                yield path, lineno, line[1:]
            lineno += 1


def tracked_lines():
    try:
        names = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files"],
            check=True, capture_output=True, text=True,
        ).stdout.split()
    except Exception:
        return
    skip = (".gz", ".png", ".pdf", ".s4p")
    for n in names:
        if n.endswith(skip):
            continue
        try:
            text = (ROOT / n).read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            continue
        for i, line in enumerate(text.split("\n"), 1):
            yield n, i, line


def scan(lines, secrets):
    hits = []
    for path, lineno, text in lines:
        for token in NUMBER.findall(text):
            digits = significant_digits(token)
            if not informative(digits):
                continue
            for secret in secrets:
                # Either spelling may be the truncated one.
                if secret.startswith(digits) or digits.startswith(secret):
                    hits.append((path, lineno, token, text.strip()[:100]))
                    break
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audit", action="store_true",
                    help="scan every tracked file and do not subtract already-published numbers")
    args = ap.parse_args()

    secrets = secret_digits()
    if not secrets:
        # No raw AED exports on this machine (a fresh clone, for instance).
        # Nothing to leak, so nothing to say — and never a reason to block.
        return 0
    if not args.audit:
        secrets -= published_digits()
        if not secrets:
            return 0

    hits = scan(tracked_lines() if args.audit else staged_additions(), secrets)
    if not hits:
        if args.audit:
            print(f"clean: no tracked file carries any of the {len(secrets)} "
                  f"AED figures (>= {MIN_SIGNIFICANT_DIGITS} digits, >= {MIN_DISTINCT_DIGITS} distinct)")
        return 0

    where = "tracked files" if args.audit else "staged changes"
    print(f"\nBLOCKED — Ansys benchmark figures found in {where}.\n")
    print("Licence terms restrict disclosure of these (operator directive")
    print("2026-09-02). They belong only in the gitignored aed_results/,")
    print("COMPARISON_private.md and docs/private/. Committing one puts it in")
    print("git history, where the fix is a rewrite and not a revert.\n")
    for path, lineno, token, text in hits[:20]:
        print(f"  {path}:{lineno}   {token}")
        print(f"      {text}")
    if len(hits) > 20:
        print(f"  ... and {len(hits) - 20} more")
    print("\nWrite the qualitative verdict instead — agree / disagree /")
    print("inconclusive, and what it decides. That is what §5.4 asks for.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
