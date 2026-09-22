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

    scripts/testing/check_private_leak.py            # staged changes (pre-commit)
    scripts/testing/check_private_leak.py --message-file .git/COMMIT_EDITMSG
                                                     # the message (commit-msg)
    scripts/testing/check_private_leak.py --audit    # every tracked file and every
                                                     # commit message, no
                                                     # already-published subtraction

**Exit codes** (OPS-58). 0 with ``clean: ...`` — the reference figures were
compared and none matched. 0 with ``SKIPPED: ...`` — no reference data on
this machine, **nothing was checked** (a CI runner's case; not a pass).
1 — a figure matched; locations are printed, never the figure. 2 with
``could not inspect: ...`` — git or a file could not be read, so there is no
verdict. Inspection used to fail open (a failing ``git diff`` yielded no
lines and read as clean); ``published_digits()`` failing is the safe
direction — nothing subtracted, more flagged — and is still swallowed.

**Overrides** (for ``scripts/testing/test_private_leak.py``): ``--root`` /
``PRIVATE_LEAK_ROOT`` and ``--secret-glob`` (repeatable) /
``PRIVATE_LEAK_SECRET_GLOBS`` (``os.pathsep``-separated).

**Where "secret" comes from.** Only the raw AED exports under
``aed_results/`` — those contain AED output and nothing of ours. The private
markdown deliberately mixes their numbers with ours (that is what makes it a
comparison), so using it as the source would flag our own published figures.

**What counts as a match.** A run of significant digits at least
``MIN_SIGNIFICANT_DIGITS`` long, shared as a prefix. That catches a truncated
quote (writing 0.12345 from 0.1234567890123456) while ignoring the ``50``,
``2026`` and ``1e-3`` that appear on every other line of this repo. A figure
rounded to 3–4 digits in prose, or turned into a ratio, is invisible to it by
design (OPS-58): the hook is a copy-paste net, the written rule the control.

**Already-published numbers are subtracted.** If a figure is already in a
tracked file at HEAD it is not a secret any more, whatever its provenance,
and flagging a second occurrence would be noise. ``--audit`` skips that
subtraction, which is how you find a leak that already happened.

**Shared inputs are allowlisted, one named site at a time** — see
``SHARED_INPUTS`` below. A value both sides were *given* (geometry, material
constants) appears in the raw exports because AED echoed its input back, not
because it measured anything; suppressing it is not suppressing a result.
Every suppression is counted and printed, so a suppressed match never reads
like no match.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("PRIVATE_LEAK_ROOT")
            or Path(__file__).resolve().parents[2])
SECRET_GLOBS = (os.environ["PRIVATE_LEAK_SECRET_GLOBS"].split(os.pathsep)
                if os.environ.get("PRIVATE_LEAK_SECRET_GLOBS")
                else ["examples/ansys_benchmarks/*/aed_results/*"])
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

# ---------------------------------------------------------------------------
# Shared-input allowlist (OPS-58, operator ruling 2026-09-21).
#
# THIS TABLE IS TRACKED, AND THAT IS SAFE ONLY BECAUSE EVERY ENTRY IS, BY
# CONSTRUCTION, ALREADY PUBLIC. An entry may name only a value the repo
# itself already publishes in a tracked file (``published_in``) *and* that
# is reproducible from published geometry or material constants
# (``closed_form``) — i.e. an input handed to both the FEM model and AED,
# which AED merely echoed back into its export. **Never add an AED output.**
# A measured result cannot satisfy ``closed_form``; if you find yourself
# wanting to delete that field to fit a number in, the number is a leak and
# the answer is a history rewrite, not an allowlist entry.
#
# Each entry is keyed on all three of (tracked path, key/identity that must
# appear on the line, exact value) — never on the value alone, so the same
# digits elsewhere in the tree are still flagged.
#
# The value is not written out: it is *computed* from ``compute``, so this
# file carries only the published geometry (0.03 m, 0.08 m) and no long digit
# string of its own — which also means an entry can exist only for a value
# that is reproducible by construction.
SHARED_INPUTS = (
    {
        "path": ("examples/ansys_benchmarks/"
                 "ans2_birdcage_coil_driven_sar_10MHz/metrics.json"),
        "key": "phantom_volume_closed_form_m3",
        "closed_form": "math.pi * 0.03**2 * 0.08",
        "compute": lambda: math.pi * 0.03 ** 2 * 0.08,
        "reason": ("shared input: the phantom cylinder's volume, a geometry "
                   "figure both solvers were given, not a solver result"),
        "published_in": ("examples/ansys_benchmarks/"
                         "ans2_birdcage_coil_driven_sar_10MHz/SPEC.md:167"),
    },
)


class InspectionError(RuntimeError):
    """git or a file could not be read: no verdict exists, exit 2."""


def git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args],
            check=True, capture_output=True, text=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise InspectionError(
            f"git {' '.join(args)} exited {exc.returncode}: "
            f"{(exc.stderr or '').strip()[:200]}") from exc
    except OSError as exc:
        raise InspectionError(f"git {' '.join(args)}: {exc}") from exc


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


def digits_in(text: str) -> set[str]:
    out: set[str] = set()
    for token in NUMBER.findall(text):
        digits = significant_digits(token)
        if informative(digits):
            out.add(digits)
    return out


def collect(paths, strict: bool = True) -> set[str]:
    """Informative digit strings in ``paths``.

    ``strict`` (the default, used for the reference data): an unreadable file
    raises InspectionError — it used to be skipped, so an unreadable export
    silently shrank the reference set.
    """
    out: set[str] = set()
    for path in paths:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError) as exc:
            if strict:
                raise InspectionError(f"{path}: {exc}") from exc
            continue
        out |= digits_in(text)
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

    Every failure here is swallowed on purpose: less subtracted means more
    flagged, the safe direction (OPS-58 keeps this one fail-open).
    """
    skip = (".log", ".gz", ".png", ".pdf", ".s4p")
    try:
        names = git("ls-files").split()
        staged = set(git("diff", "--cached", "--name-only").split())
    except InspectionError:
        return set()

    out = collect((ROOT / n for n in names
                   if not n.endswith(skip) and n not in staged), strict=False)
    for n in staged:
        if n.endswith(skip):
            continue
        try:
            text = git("show", f"HEAD:{n}")
        except InspectionError:
            continue  # new in this commit: nothing of it is published yet
        out |= digits_in(text)
    return out


def staged_additions():
    """(file, line_no, text) for every added line in the staged tracked diff.

    A failing ``git diff`` raises InspectionError (exit 2); it used to yield
    nothing, which read as a clean pass.
    """
    diff = git("diff", "--cached", "--unified=0", "--no-color",
               "--diff-filter=ACMR")
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
    names = git("ls-files", "-z").split("\0")
    skip = (".gz", ".png", ".pdf", ".s4p")
    for n in names:
        if not n or n.endswith(skip):
            continue
        path = ROOT / n
        if not path.exists() and not path.is_symlink():
            # Deleted in the work tree but still tracked: audit what git holds.
            text = git("show", f"HEAD:{n}")
        else:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeError) as exc:
                raise InspectionError(f"{n}: {exc}") from exc
        for i, line in enumerate(text.split("\n"), 1):
            yield n, i, line


def commit_message_lines():
    """("commit <sha>", line_no, text) for every line of every commit message."""
    log = git("log", "--all", "--format=%x00%H%n%B")
    for record in log.split("\0"):
        if not record.strip():
            continue
        sha, _, body = record.partition("\n")
        for i, line in enumerate(body.split("\n"), 1):
            yield f"commit {sha}", i, line


def message_file_lines(path: str):
    """The message git will record: comment lines and the scissors tail go."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError) as exc:
        raise InspectionError(f"{path}: {exc}") from exc
    for i, line in enumerate(text.split("\n"), 1):
        if line.startswith("# ------------------------ >8"):
            break
        if line.startswith("#"):
            continue
        yield "commit message", i, line


def shared_input_entry(path: str, text: str, digits: str):
    """The allowlist entry covering this match, or None.

    All three of path, key and exact value must agree: the same digits in a
    different file, or on a line that does not carry the named key, are not
    covered (`test_private_leak.py` asserts both).
    """
    for entry in SHARED_INPUTS:
        if (path == entry["path"]
                and entry["key"] in text
                and digits == significant_digits(repr(entry["compute"]()))):
            return entry
    return None


def scan(lines, secrets):
    # Either spelling may be the truncated one. Every prefix of a secret (at
    # the minimum length or longer) goes in one set, so `digits` is a prefix
    # of some secret iff it is in that set, and a secret is a prefix of
    # `digits` iff one of digits' own prefixes is a secret: O(len) per token
    # instead of O(#secrets) — the pairwise loop overran the 30 s smoke
    # ceiling on this clone's --audit (OPS-58, 20260921T123356Z log).
    prefixes = {s[:k] for s in secrets
                for k in range(MIN_SIGNIFICANT_DIGITS, len(s) + 1)}
    hits = []
    suppressed = []
    for path, lineno, text in lines:
        for token in NUMBER.findall(text):
            digits = significant_digits(token)
            if not informative(digits):
                continue
            if digits in prefixes or any(
                    digits[:k] in secrets
                    for k in range(MIN_SIGNIFICANT_DIGITS, len(digits))):
                entry = shared_input_entry(path, text, digits)
                if entry is not None:
                    suppressed.append((path, lineno, entry))
                    continue
                hits.append((path, lineno, token, text.strip()[:100]))
    return hits, suppressed


def run(args) -> int:
    secrets = secret_digits()
    if not secrets:
        # No raw AED exports on this machine (a fresh clone, a CI runner).
        # Never a reason to block — and never a pass either: say so.
        print("SKIPPED: no reference data on this machine; nothing was checked")
        return 0
    n_ref = len(secrets)
    if not args.audit:
        secrets -= published_digits()

    if args.audit:
        where = "tracked files and commit messages"
        lines = list(tracked_lines()) + list(commit_message_lines())
    elif args.message_file:
        where = "the commit message"
        lines = list(message_file_lines(args.message_file))
    else:
        where = "staged changes"
        lines = list(staged_additions())  # inspect even if nothing is left to match
    hits, suppressed = scan(lines, secrets)
    # Never silent: a suppressed match is reported whether or not anything
    # else matched, so it can never be mistaken for no match at all.
    note = ""
    if suppressed:
        note = (f"; {len(suppressed)} shared-input match"
                f"{'es' if len(suppressed) != 1 else ''} suppressed "
                f"(allowlisted, already published: "
                + ", ".join(sorted({f"{p}:{n} [{e['key']}]"
                                    for p, n, e in suppressed})) + ")")
    if not hits:
        print(f"clean: {where} ({len(lines)} lines) carry none of the {n_ref} "
              f"reference figures ({len(secrets)} compared; "
              f">= {MIN_SIGNIFICANT_DIGITS} digits, "
              f">= {MIN_DISTINCT_DIGITS} distinct){note}")
        return 0

    print(f"\nBLOCKED — Ansys benchmark figures found in {where}.\n")
    if suppressed:
        print(f"(also{note[1:]})\n")
    print("Licence terms restrict disclosure of these (operator directive")
    print("2026-09-02). They belong only in the gitignored aed_results/,")
    print("COMPARISON_private.md and docs/private/. Committing one puts it in")
    print("git history, where the fix is a rewrite and not a revert.\n")
    # Locations only, never the figure: this output lands in logs.
    for path, lineno, _token, _text in hits[:20]:
        print(f"  {path}:{lineno}")
    if len(hits) > 20:
        print(f"  ... and {len(hits) - 20} more")
    print(f"\n{len(hits)} match(es).")
    print("Write the qualitative verdict instead — agree / disagree /")
    print("inconclusive, and what it decides. That is what §5.4 asks for.")
    return 1


def main() -> int:
    global ROOT, SECRET_GLOBS
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--audit", action="store_true",
                      help="scan every tracked file and every commit message; "
                           "do not subtract already-published numbers")
    mode.add_argument("--message-file", metavar="PATH",
                      help="scan a commit message (commit-msg hook mode)")
    ap.add_argument("--root", help="repository to check (default: this clone)")
    ap.add_argument("--secret-glob", action="append",
                    help="glob under the root holding reference figures (repeatable)")
    args = ap.parse_args()
    if args.root:
        ROOT = Path(args.root).resolve()
    if args.secret_glob:
        SECRET_GLOBS = args.secret_glob
    try:
        return run(args)
    except InspectionError as exc:
        print(f"could not inspect: {exc}", file=sys.stderr)
        print("No verdict — nothing was shown to be clean.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
