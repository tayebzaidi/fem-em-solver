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


# --------------------------------------------------------------------------
# `EX-29` (2026-08-24): the freshness rule must reach *every* example's own
# `paraview_output/`, not just the repo-root one.
#
# The defect these four fixtures pin: the checker resolved artifacts only under
# `--output-dir` and exempted any basename found anywhere under the docs root
# on the premise that it was committed — but `.gitignore` ignores
# `paraview_output/` at every depth, so 22 of 27 runnable examples were never
# checked and every `stale=` reading was a census of 5. Measured pre-fix on the
# committed tree the same slot: `stale=24`
# (`20260824T110150Z_EX-29-prefix-control.log`).
# --------------------------------------------------------------------------


def write_example_fixture(tmp_path: Path, reference: str) -> tuple[Path, Path, Path]:
    """A docs tree whose guide sits in its *own* example directory.

    Returns `(docs_root, example_output_dir, unrelated_output_dir)`. The guide
    lives at ``guides/example_a/01_fixture.md`` and the artifact it names is
    written to ``guides/example_a/paraview_output/`` — the layout 22 of the 27
    runnable examples actually have. `unrelated_output_dir` stands in for the
    repo-root `paraview_output/`, and stays empty.
    """
    docs_root = tmp_path / "guides"
    example_dir = docs_root / "example_a"
    example_dir.mkdir(parents=True)
    (example_dir / "01_fixture.md").write_text(
        "# Fixture guide\n\n"
        "## What this demonstrates\n\nAn example-relative reference.\n\n"
        "## How to run it\n\n"
        f"Open `paraview_output/{reference}` after the run.\n\n"
        "## How to analyze it, step by step\n\n1. Look at it.\n"
    )
    example_output = example_dir / "paraview_output"
    example_output.mkdir()
    unrelated_output = tmp_path / "out"
    unrelated_output.mkdir()
    return docs_root, example_output, unrelated_output


def age(path: Path, hours: float) -> None:
    stamp = time.time() - hours * 3600.0
    os.utime(path, (stamp, stamp))


def git(*argv: str, cwd: Path) -> subprocess.CompletedProcess:
    """`git` with the ownership exception the container needs (see the
    checker's `safe_directory_args`: root over a host-owned bind mount)."""
    return subprocess.run(
        ["git", *checker.safe_directory_args(cwd), *argv],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def test_untracked_in_tree_artifact_is_freshness_checked(tmp_path):
    """(a) An aged artifact in the example's own output dir counts as stale.

    Pre-fix this scored clean twice over: the basename existed under the docs
    root (so it was exempted), and it was not in `--output-dir` at all.
    """
    docs_root, example_output, unrelated = write_example_fixture(tmp_path, "fixture_field.xdmf")
    artifact = example_output / "fixture_field.xdmf"
    artifact.write_text("<Xdmf/>\n")
    age(artifact, 10.0)

    status, counts = run_checker(*fixture_args(docs_root, unrelated, "--max-age-s", "3600"))
    assert (counts["dead"], counts["guide"], counts["stale"]) == (0, 0, 1)
    assert status == checker.EXIT_STALE_ONLY
    assert status == expected_status(counts)


def test_tracked_in_tree_artifact_is_exempt_from_freshness(tmp_path):
    """(b) The same artifact, committed, is its own evidence — never stale.

    The exemption is exactly "git tracks it", not "a file of that name exists
    somewhere". The `ans:` benchmark cases rely on it; scratch must not.
    """
    docs_root, example_output, unrelated = write_example_fixture(tmp_path, "fixture_field.xdmf")
    artifact = example_output / "fixture_field.xdmf"
    artifact.write_text("<Xdmf/>\n")
    age(artifact, 10.0)

    git("init", "-q", cwd=docs_root)
    git("add", "-f", "example_a/paraview_output/fixture_field.xdmf", cwd=docs_root)

    status, counts = run_checker(*fixture_args(docs_root, unrelated, "--max-age-s", "3600"))
    assert (counts["dead"], counts["guide"], counts["stale"]) == (0, 0, 0)
    assert status == checker.EXIT_OK

    # And the exemption is the *only* difference: drop it from the index and the
    # identical tree is stale again.
    git("rm", "-q", "--cached", "example_a/paraview_output/fixture_field.xdmf", cwd=docs_root)
    status, counts = run_checker(*fixture_args(docs_root, unrelated, "--max-age-s", "3600"))
    assert counts["stale"] == 1
    assert status == checker.EXIT_STALE_ONLY


@pytest.mark.parametrize(
    "age_h, expect_stale", [(47.0, 0), (49.0, 1)], ids=["within-48h", "past-48h"]
)
def test_default_window_holds_on_example_relative_paths(tmp_path, age_h, expect_stale):
    """(c) The 47 h / 49 h boundary is the same wherever the artifact lives."""
    docs_root, example_output, unrelated = write_example_fixture(tmp_path, "fixture_field.xdmf")
    artifact = example_output / "fixture_field.xdmf"
    artifact.write_text("<Xdmf/>\n")
    age(artifact, age_h)

    status, counts = run_checker(*fixture_args(docs_root, unrelated))
    assert counts["stale"] == expect_stale
    assert status == (checker.EXIT_STALE_ONLY if expect_stale else checker.EXIT_OK)


def _census_of_the_committed_tree() -> tuple[int, int, int]:
    """Walk the tree the way the fix says the checker must, independently.

    Returns `(stale_count, checked_artifacts, hidden_by_the_old_exemption)`.
    Deliberately does not import the checker's resolution helpers — a
    re-implementation that agrees is evidence; a call into the same function
    would only assert it equals itself.
    """
    examples = REPO_ROOT / "examples"
    tracked = {
        Path(p).name
        for p in git("ls-files", cwd=examples).stdout.split()
        if p.endswith(checker.ARTIFACT_SUFFIXES)
    }
    # name -> the guides citing it, in the order the checker scans them.
    cited: dict[str, list[Path]] = {}
    for guide in sorted(examples.rglob("*.md")):
        for line in guide.read_text().splitlines():
            for match in checker.REFERENCE_RE.finditer(line):
                name = Path(match.group(0)).name
                guides = cited.setdefault(name, [])
                if guide not in guides:
                    guides.append(guide)

    root_output = REPO_ROOT / "paraview_output"
    now = time.time()
    stale = checked = hidden = 0
    for name, guides in cited.items():
        if name.endswith(".py") or name in checker.ALLOWLIST or name in tracked:
            continue
        for directory in [g.parent / "paraview_output" for g in guides] + [root_output]:
            target = directory / name
            if not target.exists():
                continue
            checked += 1
            if directory != root_output:
                # The old code exempted this by basename and never applied the
                # age rule to it.
                hidden += 1
            if now - checker.artifact_mtime(target) > 172800.0:
                stale += 1
            break
    return stale, checked, hidden


def test_committed_tree_stale_count_equals_an_independent_full_census():
    """(d) The printed `stale=` figure is the *whole* census, not 5 examples.

    Negative control for the same defect: the census now reaches artifacts the
    pre-`EX-29` basename exemption hid, and that set is non-empty — which is
    what makes the pre-fix `stale=24` reading (measured this slot on this same
    tree) a census of 5 rather than of 27.
    """
    _, counts = run_checker()
    expected_stale, checked, hidden = _census_of_the_committed_tree()
    print(f"independent census: stale={expected_stale} checked={checked} hidden_pre_fix={hidden}")
    assert hidden > 0, (
        "no referenced artifact resolves outside the repo-root output dir — "
        "the EX-29 defect cannot be demonstrated on this tree"
    )
    assert counts["stale"] == expected_stale


# Measured 2026-08-24 (`git ls-files examples | grep -E '\.(xdmf|h5|bp|csv|json|
# png|msh)$'`). The `EX-29` entry predicted the tracked set was empty; it is
# not — three artifacts really are committed, and they are exactly the ones
# whose exemption the pre-fix comment described ("an artifact committed next to
# its own case"). Pinning the paths, not the count, is what stops the exemption
# widening back to "any basename found under examples/".
COMMITTED_EXAMPLE_ARTIFACTS = {
    "examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/metrics.json",
    "examples/ansys_benchmarks/two_torus_gap_ports_10MHz/metrics.json",
    "examples/magnetostatics/straight_wire_validation.png",
}


def test_the_in_tree_exemption_cannot_silently_widen():
    """The exemption covers exactly the artifacts git tracks, named here.

    The pre-`EX-29` exemption was justified by "it is committed" and applied to
    every basename found under `examples/`, committed or not. Now it is the
    tracked set, and the tracked set is pinned: a chunk that commits a new
    artifact has to say so here, and a chunk that re-broadens the rule to
    untracked scratch fails on the extra entries.
    """
    tracked = {
        str(path.relative_to(REPO_ROOT))
        for paths in checker.tracked_artifacts(REPO_ROOT / "examples").values()
        for path in paths
    }
    assert tracked == COMMITTED_EXAMPLE_ARTIFACTS


def test_the_orphaned_magnetostatics_output_dir_is_gone():
    """`02_circular_loop.py` has written to the repo root since `EX-17`; the
    2026-08-03/04 `circular_loop_*` leftovers under `examples/magnetostatics/`
    were an orphan that the example-relative resolution would now read as the
    example's live output."""
    assert not (REPO_ROOT / "examples" / "magnetostatics" / "paraview_output").exists()
