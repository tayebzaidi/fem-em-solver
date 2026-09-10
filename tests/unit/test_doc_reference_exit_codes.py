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


WINDOW_H = checker.DEFAULT_MAX_AGE_S / 3600.0

# Either side of the default window, expressed as hours off the boundary rather
# than as literals, so the pair follows `DEFAULT_MAX_AGE_S` instead of pinning a
# second copy of it (`ANS-1`). Re-registered by `OPS-42` (2026-09-09) when the
# default moved 48 h -> 14 days; the assertion itself is unchanged, only the
# boundary it brackets.
BOUNDARY_CASES = [(WINDOW_H - 1.0, 0), (WINDOW_H + 1.0, 1)]
BOUNDARY_IDS = ["inside-window", "past-window"]


@pytest.mark.parametrize("age_h, expect_stale", BOUNDARY_CASES, ids=BOUNDARY_IDS)
def test_default_window_is_the_one_the_module_declares(tmp_path, age_h, expect_stale):
    """The behavioural boundary is exactly `DEFAULT_MAX_AGE_S`.

    Measured by behaviour on either side of the boundary rather than by reading
    the argparse default, so a default overridden anywhere in the call chain
    fails: `--max-age-s` is not passed here at all.
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


@pytest.mark.parametrize("age_h, expect_stale", BOUNDARY_CASES, ids=BOUNDARY_IDS)
def test_default_window_holds_on_example_relative_paths(tmp_path, age_h, expect_stale):
    """(c) The default-window boundary is the same wherever the artifact lives."""
    docs_root, example_output, unrelated = write_example_fixture(tmp_path, "fixture_field.xdmf")
    artifact = example_output / "fixture_field.xdmf"
    artifact.write_text("<Xdmf/>\n")
    age(artifact, age_h)

    status, counts = run_checker(*fixture_args(docs_root, unrelated))
    assert counts["stale"] == expect_stale
    assert status == (checker.EXIT_STALE_ONLY if expect_stale else checker.EXIT_OK)


def _stale_census(window_s: float) -> dict:
    """Walk the tree the way the fix says the checker must, independently.

    Returns a dict with the stale *set* (resolved artifact paths), the example
    directories those artifacts belong to, how many artifacts were age-checked
    at all, and how many of them the pre-`EX-29` basename exemption hid.
    Deliberately does not import the checker's resolution helpers — a
    re-implementation that agrees is evidence; a call into the same function
    would only assert it equals itself. `artifact_mtime` is the one exception:
    it is the *reading* of an artifact's age (`.bp` directories need the
    newest child, `EX-14`), not the rule under test.

    `window_s` is a parameter so the same walk produces the pre-`OPS-42` (48 h)
    and post-`OPS-42` (14 d) censuses from one implementation.
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
    stale: set[Path] = set()
    covered: set[Path] = set()
    cited_by: set[Path] = set()
    checked = hidden = 0
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
            if now - checker.artifact_mtime(target) > window_s:
                stale.add(target)
                covered.add(directory)
                cited_by.update(guides)
            break
    return {
        "stale": stale,
        "covered": covered,
        # The guides citing at least one stale artifact — "how many examples the
        # signal covers" in the units the 02:15 weekly used (40 of 47), which is
        # per *guide*, not per output directory (several guides share one
        # `paraview_output/`).
        "cited_by": cited_by,
        "checked": checked,
        "hidden": hidden,
    }


def _census_of_the_committed_tree() -> tuple[int, int, int]:
    """`(stale_count, checked_artifacts, hidden_by_the_old_exemption)` at the
    module's declared default window."""
    census = _stale_census(checker.DEFAULT_MAX_AGE_S)
    return len(census["stale"]), census["checked"], census["hidden"]


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


# Measured 2026-08-24 by `EX-29` (`git ls-files examples | grep -E
# '\.(xdmf|h5|bp|csv|json|png|msh)$'`), re-measured and re-pinned 2026-09-09 by
# `OPS-44`. The `EX-29` entry predicted the tracked set was empty; it is not —
# artifacts really are committed, and they are exactly the ones whose exemption
# the pre-fix comment described ("an artifact committed next to its own case").
# Pinning the paths, not the count, is what stops the exemption widening back to
# "any basename found under examples/".
#
# Provenance of each member, and why this record moved:
#   * `magnetostatics/straight_wire_validation.png` and the
#     `loop_over_lossy_slab_10MHz` / `two_torus_gap_ports_10MHz`
#     `metrics.json` — the three `EX-29` measured on 2026-08-24.
#   * `ansys_benchmarks/birdcage_four_port_10_64_128MHz/metrics.json`
#     (`ANS-2` step 1) and
#     `ansys_benchmarks/birdcage_coil_driven_sar_10MHz/metrics.json`
#     (`ANS-4`, committed 2026-09-09) — each landed under `ANS-1`'s rule that
#     an `ans:` case commits its own `metrics.json`, but neither declared the
#     widening here, so this test went red on `main` (found by `OPS-42`,
#     2026-09-09, `20260909T213349Z_OPS-42.log:194–195`). `OPS-44` writes that
#     declaration late rather than replacing the pin with an `ans:*/metrics.json`
#     glob: the 2026-09-09 18:00 review ruled that a pattern would trade one
#     line of maintenance per benchmark case for a weaker guarantee, and the
#     point of the pin is that widening the exemption must be *declared*.
COMMITTED_EXAMPLE_ARTIFACTS = {
    "examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/metrics.json",
    "examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/metrics.json",
    "examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/metrics.json",
    "examples/ansys_benchmarks/two_torus_gap_ports_10MHz/metrics.json",
    "examples/magnetostatics/straight_wire_validation.png",
}


def _tracked_example_artifacts_via_git() -> set[str]:
    """The pinned set re-derived *independently of the checker*: plain
    `git ls-files examples` filtered on `ARTIFACT_SUFFIXES`.

    Deliberately not `checker.tracked_artifacts` — that is the code under test,
    and an anchor that called it would only prove the checker agrees with
    itself.
    """
    proc = subprocess.run(
        ["git", *checker.safe_directory_args(REPO_ROOT), "ls-files", "-z", "--", "examples"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        entry
        for entry in proc.stdout.split("\0")
        if entry and entry.endswith(checker.ARTIFACT_SUFFIXES)
    }


def test_the_in_tree_exemption_cannot_silently_widen():
    """The exemption covers exactly the artifacts git tracks, named here.

    The pre-`EX-29` exemption was justified by "it is committed" and applied to
    every basename found under `examples/`, committed or not. Now it is the
    tracked set, and the tracked set is pinned: a chunk that commits a new
    artifact has to say so here, and a chunk that re-broadens the rule to
    untracked scratch fails on the extra entries.

    `OPS-44` anchor: the identity holds against an *independent* re-derivation
    from `git ls-files`, not merely against a count.
    """
    tracked = {
        str(path.relative_to(REPO_ROOT))
        for paths in checker.tracked_artifacts(REPO_ROOT / "examples").values()
        for path in paths
    }
    from_git = _tracked_example_artifacts_via_git()
    print(f"OPS-44 pinned={len(COMMITTED_EXAMPLE_ARTIFACTS)} "
          f"checker={len(tracked)} git_ls_files={len(from_git)}")
    for path in sorted(from_git):
        print(f"  tracked example artifact: {path}")
    assert tracked == from_git, (
        "checker.tracked_artifacts disagrees with git ls-files — that is a "
        "defect in the checker, not in the pinned record"
    )
    assert tracked == COMMITTED_EXAMPLE_ARTIFACTS
    assert len(COMMITTED_EXAMPLE_ARTIFACTS) == 5


def test_dropping_any_pinned_path_turns_the_identity_red():
    """`OPS-44` negative control, half 1 — separation arithmetic.

    The anchor above is a set equality, so it can only be trusted if removing
    any single member breaks it. A pin "fixed" by deleting or weakening the
    assertion passes the anchor and fails here.
    """
    tracked = {
        str(path.relative_to(REPO_ROOT))
        for paths in checker.tracked_artifacts(REPO_ROOT / "examples").values()
        for path in paths
    }
    for dropped in sorted(COMMITTED_EXAMPLE_ARTIFACTS):
        weakened = COMMITTED_EXAMPLE_ARTIFACTS - {dropped}
        assert tracked != weakened, (
            f"the identity survives dropping {dropped} — the pin is not "
            "actually constraining that path"
        )
        assert len(weakened) == 4


def test_an_untracked_example_artifact_never_enters_the_exemption(tmp_path):
    """`OPS-44` negative control, half 2 — the exemption is still "git tracks
    it", not "it lives under an example directory".

    Mirrors `test_tracked_in_tree_artifact_is_exempt_from_freshness` with the
    `git add` removed: same tree, same age, no index entry. If the exemption had
    widened back to "any basename under `examples/`", this artifact would be
    exempt and the census would read clean.
    """
    docs_root, example_output, unrelated = write_example_fixture(tmp_path, "fixture_field.xdmf")
    artifact = example_output / "fixture_field.xdmf"
    artifact.write_text("<Xdmf/>\n")
    age(artifact, 10.0)

    git("init", "-q", cwd=docs_root)  # a work tree, but the artifact is not added

    exempt = {
        str(path)
        for paths in checker.tracked_artifacts(docs_root).values()
        for path in paths
    }
    print(f"OPS-44 untracked control: exemption holds {len(exempt)} path(s)")
    assert str(artifact) not in exempt
    assert exempt == set()

    status, counts = run_checker(*fixture_args(docs_root, unrelated, "--max-age-s", "3600"))
    assert (counts["dead"], counts["guide"], counts["stale"]) == (0, 0, 1)
    assert status == checker.EXIT_STALE_ONLY


def test_the_orphaned_magnetostatics_output_dir_is_gone():
    """`02_circular_loop.py` has written to the repo root since `EX-17`; the
    2026-08-03/04 `circular_loop_*` leftovers under `examples/magnetostatics/`
    were an orphan that the example-relative resolution would now read as the
    example's live output."""
    assert not (REPO_ROOT / "examples" / "magnetostatics" / "paraview_output").exists()


# --------------------------------------------------------------------------
# `OPS-42` (2026-09-09): the default window moves 172 800 s (48 h) -> 1 209 600 s
# (14 days), because the corpus that ran daily when `OPS-15` chose 48 h now runs
# weekly. Pre-change census on this tree: `dead=0 guide=0 stale=87
# stale_severity=report exit=2`
# (`20260909T141114Z_ANS-2-step1-census.log:126`); the weekly's health finding
# read `stale=81` over 40 of the 47 examples
# (`20260907T140926Z_EX-53-census-post.log:120`).
#
# The two tests below are the chunk's anchor and its negative control. The
# anchor alone cannot detect a threshold change that *disabled* the check —
# both sides would read zero and agree — which is exactly why the control is
# here and why it asserts a rise of exactly 1 rather than "at least 1".
# --------------------------------------------------------------------------

# The window this replaced, kept only to print the before/after comparison the
# `OPS-42` item asks for. It is not a threshold any assertion here depends on.
PRE_OPS42_MAX_AGE_S = 172800.0


def test_reported_stale_set_equals_an_independent_recomputation_at_the_new_window():
    """Anchor: `stale=` is exactly the set recomputed from the artifacts' own
    `st_mtime` against `DEFAULT_MAX_AGE_S`, with `dead=0 guide=0` unchanged.

    This is a consistency identity the checker cannot satisfy by accident: the
    recomputation walks the guides, resolves each artifact the way `EX-29` says
    it must, and applies the age rule itself. Also prints the before/after
    counts and how many example output directories they cover, so the review
    can see whether the signal became informative — a post-change `stale` that
    is still most of the corpus is a finding about the cadence, not a reason to
    move the window again.
    """
    status, counts = run_checker()
    after = _stale_census(checker.DEFAULT_MAX_AGE_S)
    before = _stale_census(PRE_OPS42_MAX_AGE_S)

    total_guides = len(sorted((REPO_ROOT / "examples").rglob("*.md")))

    def _cover(census: dict) -> str:
        return (
            f"{len(census['stale'])} stale artifact(s) cited by "
            f"{len(census['cited_by'])} guide(s) of {total_guides}, in "
            f"{len(census['covered'])} output dir(s)"
        )

    print(
        f"OPS-42 window {PRE_OPS42_MAX_AGE_S:.0f} s -> "
        f"{checker.DEFAULT_MAX_AGE_S:.0f} s: "
        f"before {_cover(before)}; after {_cover(after)}; "
        f"{after['checked']} artifact(s) age-checked in total; "
        f"reported stale={counts['stale']}"
    )
    for target in sorted(after["stale"]):
        print(f"  still stale at 14 d: {target.relative_to(REPO_ROOT)}")

    assert counts["dead"] == 0, "a guide names a file no run produces"
    assert counts["guide"] == 0, "an example is missing a guide or a heading"
    assert counts["stale_severity"] == "report", "OPS-19's default must not move"
    # The identity. A mismatch means the checker's age arithmetic disagrees with
    # the filesystem, which is worth more than the threshold: report both sets,
    # open a known-issues row and revert the default (`OPS-42`, negative result).
    assert counts["stale"] == len(after["stale"]), (
        "reported stale count disagrees with the independent recomputation; "
        f"recomputed set = {sorted(str(p.relative_to(REPO_ROOT)) for p in after['stale'])}"
    )
    # Widening a window can only ever un-flag artifacts, never flag new ones.
    assert after["stale"] <= before["stale"]
    assert status == expected_status(counts)


def test_backdating_one_artifact_past_the_new_window_still_reports_it_stale(tmp_path):
    """Negative control: the check is widened, not switched off.

    Three artifacts in one fixture tree, all fresh (`stale=0`); push exactly one
    past `DEFAULT_MAX_AGE_S` and the reported count must rise by **exactly 1**
    and the exit code must move OK -> stale-only. A
    threshold change that quietly disabled the age rule passes the anchor above
    and fails here. `os.utime` is applied only to files this fixture created —
    never to a committed artifact or to the corpus's own scratch.
    """
    docs_root = tmp_path / "guides"
    docs_root.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    names = ["alpha_field.xdmf", "beta_field.h5", "gamma_metrics.json"]
    (docs_root / "01_fixture.md").write_text(
        "# Fixture guide\n\n"
        "## What this demonstrates\n\nThree run artifacts.\n\n"
        "## How to run it\n\n"
        + "".join(f"Open `{name}` after the run.\n\n" for name in names)
        + "## How to analyze it, step by step\n\n1. Look at them.\n"
    )
    for name in names:
        (output_dir / name).write_text("{}\n")

    baseline_status, baseline = run_checker(*fixture_args(docs_root, output_dir))
    assert (baseline["dead"], baseline["guide"], baseline["stale"]) == (0, 0, 0)
    assert baseline_status == checker.EXIT_OK

    backdated = output_dir / names[1]
    age(backdated, WINDOW_H + 1.0)

    status, counts = run_checker(*fixture_args(docs_root, output_dir))
    print(
        f"negative control: stale {baseline['stale']} -> {counts['stale']} "
        f"after backdating {backdated.name} to {WINDOW_H + 1.0:.1f} h "
        f"(window {WINDOW_H:.1f} h)"
    )
    assert counts["stale"] == baseline["stale"] + 1
    assert (counts["dead"], counts["guide"]) == (0, 0)
    assert status == checker.EXIT_STALE_ONLY
    assert status == expected_status(counts)
