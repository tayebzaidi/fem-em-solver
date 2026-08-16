"""`OPS-19` step 1: staleness must not own `check_example_doc_references.py`'s
exit code.

The checker's dead-reference pass used to score a stale-but-present artifact
exactly like a reference no run has ever produced, so 24 aged
`paraview_output/` files made *every* invocation exit 1 and a chunk touching
examples could not tell its own breakage from the backlog's (`EX-20`, `ANS-3`,
2026-08-16). These tests pin the split contract:

* hard violations (dead reference, missing guide, missing heading) → exit 1,
* staleness alone → exit 2 under the default `--stale-severity report`,
* staleness under `--stale-severity fail` → exit 1 (the old reading, opt-in),
* nothing wrong → exit 0.

The negative control is the third fixture below: a guide naming an artifact no
run ever wrote must still exit 1 after the split, or the checker has been
turned off rather than sharpened.

Every code and default is imported from the checker module, never restated
(`ANS-1`). Smoke tier: pure filesystem, no solves.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "scripts" / "testing" / "check_example_doc_references.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("docref_checker", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker()

RESULT_RE = re.compile(
    r"RESULT: dead=(\d+) guide=(\d+) stale=(\d+) "
    r"stale_severity=(\w+) exit=(\d+)"
)


def run_checker(*extra: str) -> tuple[int, dict]:
    """Invoke the checker as the harness does and parse its RESULT line."""
    proc = subprocess.run(
        [sys.executable, str(CHECKER), *extra],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    match = RESULT_RE.search(proc.stdout)
    assert match is not None, (
        f"no RESULT line in checker output (rc={proc.returncode})\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )
    counts = {
        "dead": int(match.group(1)),
        "guide": int(match.group(2)),
        "stale": int(match.group(3)),
        "stale_severity": match.group(4),
        "exit": int(match.group(5)),
    }
    print(proc.stdout)
    return proc.returncode, counts


def expected_status(counts: dict) -> int:
    """The contract, restated as arithmetic over the printed counts."""
    hard = counts["dead"] + counts["guide"]
    if counts["stale_severity"] == "fail":
        hard += counts["stale"]
    if hard:
        return checker.EXIT_HARD
    if counts["stale"]:
        return checker.EXIT_STALE_ONLY
    return checker.EXIT_OK


def write_fixture(tmp_path: Path, reference: str) -> tuple[Path, Path]:
    """A one-guide docs tree naming `reference`, plus an empty output dir."""
    docs_root = tmp_path / "guides"
    docs_root.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (docs_root / "01_fixture.md").write_text(
        "# Fixture guide\n\n"
        "## What this demonstrates\n\nA single reference.\n\n"
        "## How to run it\n\n"
        f"Open `{reference}` after the run.\n\n"
        "## How to analyze it, step by step\n\n1. Look at it.\n"
    )
    return docs_root, output_dir


def fixture_args(docs_root: Path, output_dir: Path, *extra: str) -> list[str]:
    return [
        "--docs-root", str(docs_root),
        "--output-dir", str(output_dir),
        *extra,
    ]


def test_current_tree_is_free_of_hard_violations_and_obeys_the_contract():
    """Anchor on the tree as committed: no dead reference, guide pass green,
    and the exit code is exactly the contract's function of the counts.

    Staleness is *not* asserted to any particular value — it is a function of
    when the examples last ran, which is precisely why it must not own the
    exit code. What is asserted is that whatever the stale count is, it can
    only move the exit code between EXIT_OK and EXIT_STALE_ONLY.
    """
    status, counts = run_checker()
    assert counts["dead"] == 0, "a guide names a file no run produces"
    assert counts["guide"] == 0, "an example is missing a guide or a heading"
    assert counts["stale_severity"] == "report", "the default must be report"
    assert status == expected_status(counts)
    assert status in (checker.EXIT_OK, checker.EXIT_STALE_ONLY)


def test_staleness_alone_exits_with_the_staleness_code(tmp_path):
    """One artifact, present but aged past the window: exit 2, dead count 0."""
    docs_root, output_dir = write_fixture(tmp_path, "fixture_field.xdmf")
    artifact = output_dir / "fixture_field.xdmf"
    artifact.write_text("<Xdmf/>\n")
    old = time.time() - 10 * 3600.0
    os.utime(artifact, (old, old))

    status, counts = run_checker(*fixture_args(docs_root, output_dir, "--max-age-s", "3600"))
    assert (counts["dead"], counts["guide"], counts["stale"]) == (0, 0, 1)
    assert status == checker.EXIT_STALE_ONLY
    assert status == expected_status(counts)


def test_stale_severity_fail_restores_the_old_all_or_nothing_reading(tmp_path):
    """Same tree, `--stale-severity fail`: the caller opted back in to exit 1."""
    docs_root, output_dir = write_fixture(tmp_path, "fixture_field.xdmf")
    artifact = output_dir / "fixture_field.xdmf"
    artifact.write_text("<Xdmf/>\n")
    old = time.time() - 10 * 3600.0
    os.utime(artifact, (old, old))

    status, counts = run_checker(
        *fixture_args(docs_root, output_dir, "--max-age-s", "3600", "--stale-severity", "fail")
    )
    assert counts["stale"] == 1 and counts["dead"] == 0
    assert status == checker.EXIT_HARD
    assert status == expected_status(counts)


@pytest.mark.parametrize(
    "reference",
    ["never_written_field.xdmf", "no_such_example_script.py"],
    ids=["dead-artifact", "dead-script"],
)
def test_dead_reference_still_exits_one_after_the_split(tmp_path, reference):
    """Negative control: the defect class the checker exists for must survive.

    The artifact case is the sharp one — it travels the same code path the
    staleness rule was carved out of, so a split that scored "missing" as
    staleness would silently downgrade the only violation this pass has ever
    caught in the wild (`EX-14`'s 158-h-old `.bp`).
    """
    docs_root, output_dir = write_fixture(tmp_path, reference)
    status, counts = run_checker(*fixture_args(docs_root, output_dir))
    assert counts["dead"] == 1 and counts["stale"] == 0
    assert status == checker.EXIT_HARD
    assert status == expected_status(counts)


def test_fresh_and_resolvable_references_exit_zero(tmp_path):
    """A guide whose artifact exists and is fresh scores clean."""
    docs_root, output_dir = write_fixture(tmp_path, "fixture_field.xdmf")
    (output_dir / "fixture_field.xdmf").write_text("<Xdmf/>\n")
    status, counts = run_checker(*fixture_args(docs_root, output_dir))
    assert (counts["dead"], counts["guide"], counts["stale"]) == (0, 0, 0)
    assert status == checker.EXIT_OK
    assert status == expected_status(counts)


@pytest.mark.parametrize(
    "age_h, expect_stale", [(47.0, 0), (49.0, 1)], ids=["within-48h", "past-48h"]
)
def test_default_window_is_unchanged_by_this_chunk(tmp_path, age_h, expect_stale):
    """`OPS-19`'s scope is exit-code semantics only: `OPS-15`'s 48 h stays put.

    Measured by behaviour on either side of the boundary rather than by reading
    the argparse default, so a default changed anywhere in the call chain fails.
    """
    docs_root, output_dir = write_fixture(tmp_path, "fixture_field.xdmf")
    artifact = output_dir / "fixture_field.xdmf"
    artifact.write_text("<Xdmf/>\n")
    stamp = time.time() - age_h * 3600.0
    os.utime(artifact, (stamp, stamp))

    status, counts = run_checker(*fixture_args(docs_root, output_dir))
    assert counts["stale"] == expect_stale
    assert status == (checker.EXIT_STALE_ONLY if expect_stale else checker.EXIT_OK)
