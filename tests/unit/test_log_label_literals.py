"""`OPS-51`: no `tests/validation` print may hardcode a rank width or frequency.

Six prints stated ``-n 2`` / ``128 MHz`` as literals, so the 2026-09-17 and
2026-09-18 XL windows printed ``wall at -n 2`` on ``-n 16`` runs and
``at 128 MHz ===`` over 10 MHz data (known-issues 2026-09-18).  The labels are
prints — no gate reads them — but a reader pricing a run from a ``PRICE`` or
rung-header line is off by 8x in core-seconds.

The gate is a count identity: the number of matches for the two literal
patterns over ``tests/validation/*.py`` is **0** after the change and **6** on
the same files at the pinned pre-change commit.  The pre-change count is the
asserted negative control — without it the 0 is equally consistent with a
broken regex.

Trap kept in mind: this module's own source contains both patterns (as regex
strings), so the scan is over ``tests/validation`` only, never ``tests/``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

# The two literals, exactly as they appeared in the offending f-strings.
LITERAL_PATTERNS = (
    r"wall at -n 2",
    r"at 128 MHz ===",
)

# The commit the six literals were last present at — the change under test is
# its child.  Pinned, never `HEAD`: the control must not follow the branch.
PRE_CHANGE_SHA = "e091c0cbbea9146b64472e72d3215732a7431497"

# Count of `LITERAL_PATTERNS` matches over `tests/validation/*.py` at
# `PRE_CHANGE_SHA` (known-issues 2026-09-18 lists the six sites).
PRE_CHANGE_LITERAL_COUNT = 6

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_DIR = REPO_ROOT / "tests" / "validation"


def _count_in_text(text: str) -> int:
    return sum(len(re.findall(pattern, text)) for pattern in LITERAL_PATTERNS)


def _validation_sources() -> list[Path]:
    return sorted(VALIDATION_DIR.glob("*.py"))


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", f"safe.directory={REPO_ROOT}", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_no_validation_print_hardcodes_a_rank_width_or_frequency():
    """The gate: zero matches over `tests/validation/*.py`."""
    sources = _validation_sources()
    assert len(sources) > 50, f"scan found only {len(sources)} modules — wrong dir?"

    hits: list[str] = []
    total = 0
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for pattern in LITERAL_PATTERNS:
            for match in re.finditer(pattern, text):
                line = text.count("\n", 0, match.start()) + 1
                hits.append(f"{path.relative_to(REPO_ROOT)}:{line}: {pattern!r}")
                total += 1

    print(
        f"\n[OPS-51] scanned {len(sources)} modules under "
        f"tests/validation; literal patterns {LITERAL_PATTERNS}; "
        f"count = {total} (required 0)",
        flush=True,
    )
    for hit in hits:
        print(f"    HIT {hit}", flush=True)

    assert total == 0, f"{total} hardcoded label literal(s): " + "; ".join(hits)


def test_the_same_count_at_the_pinned_pre_change_commit_is_six():
    """Asserted negative control: 6 -> 0 is the count identity.

    Reads the same file list out of `PRE_CHANGE_SHA` with `git show`; the
    regexes are the ones the gate above uses, so a regex that matches nothing
    fails here instead of passing there.
    """
    probe = _git("cat-file", "-e", f"{PRE_CHANGE_SHA}^{{commit}}")
    if probe.returncode != 0:
        pytest.fail(
            f"pinned commit {PRE_CHANGE_SHA} not readable from the container: "
            f"{probe.stderr.strip()}"
        )

    listing = _git("ls-tree", "--name-only", f"{PRE_CHANGE_SHA}:tests/validation")
    assert listing.returncode == 0, listing.stderr
    names = [n for n in listing.stdout.split() if n.endswith(".py")]
    assert len(names) > 50, f"pre-change tree listed only {len(names)} modules"

    hits: list[str] = []
    total = 0
    for name in names:
        blob = _git("show", f"{PRE_CHANGE_SHA}:tests/validation/{name}")
        assert blob.returncode == 0, blob.stderr
        text = blob.stdout
        for pattern in LITERAL_PATTERNS:
            for match in re.finditer(pattern, text):
                line = text.count("\n", 0, match.start()) + 1
                hits.append(f"{name}:{line}: {pattern!r}")
                total += 1

    print(
        f"\n[OPS-51] negative control at {PRE_CHANGE_SHA[:7]}: scanned "
        f"{len(names)} modules; count = {total} "
        f"(expected {PRE_CHANGE_LITERAL_COUNT})",
        flush=True,
    )
    for hit in hits:
        print(f"    PRE-CHANGE HIT {hit}", flush=True)

    assert total == PRE_CHANGE_LITERAL_COUNT, (
        f"pre-change count {total} != {PRE_CHANGE_LITERAL_COUNT}; the control "
        "no longer separates — re-pin the sha with its measured count"
    )
