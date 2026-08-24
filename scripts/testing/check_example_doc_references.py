#!/usr/bin/env python3
"""EX-12/EX-15 gate: examples/ guides name only real files, and every runnable
example has one.

Two passes, independent:

**Reference pass (`EX-12`)** — every file an examples/ guide names must really
exist. Two classes of reference, checked differently:

* **Scripts and modules** (``*.py``) — must exist somewhere in the repo. This
  is what caught ``PARAVIEW_VALIDATION_GUIDE.md``'s ``03_helmholtz_coil.py``,
  removed long before the guide was updated.
* **Run artifacts** (``.xdmf``/``.h5``/``.bp``/``.csv``/``.json``/``.png``/
  ``.msh``) — must exist *and* be newer than ``--max-age-s``. An artifact is
  looked for in the citing guide's own ``paraview_output/`` first and in the
  shared ``--output-dir`` second (`EX-29`, 2026-08-24), because that is where
  each example actually writes; only artifacts **git tracks** under the docs
  root are exempt from the freshness rule. Existence alone is not enough:
  ``paraview_output/`` is
  gitignored scratch that accumulates files from months-old runs, so a stale
  leftover would let a dead reference pass. Freshness is what makes the check
  mean "a run actually produces this". This is what caught the
  ``straight_wire.msh`` claim in ``MESH_DIAGNOSTIC_GUIDE.md`` (no run has ever
  written it) and the ``.bp`` instructions in ``PARAVIEW_GUIDE.md`` (VTX export
  raises on the N1curl potential, so the directory is never written).

  The default window is **48 h** (`OPS-15`, 2026-08-10). One hour was shorter
  than the 90-minute automation slot grid, so every slot that ran the checker
  after its examples had aged half an hour paid an 80–200 s refresh solve — a
  structural tax, not a freshness finding. 48 h keeps a committed guide green
  across a review interval and still flags the one genuinely dead reference
  this pass has ever caught (a 158-h-old `.bp`, `EX-14`). In-slot controls that
  want the strict reading pass `--max-age-s 1` explicitly.

**Guide pass (`EX-15`)** — every entry ``./run_examples.sh --list`` enumerates
must have a **same-stem** ``.md`` next to it (``01_lossy_plane_wave.py`` →
``01_lossy_plane_wave.md``) carrying the three required headings: *What this
demonstrates*, *How to run it*, *How to analyze it, step by step*. The runner's
own ``--list`` output is the source of truth, so an example added to a group
directory is orphaned by this check the moment it appears — no second list to
keep in sync. Group-level guides (``PARAVIEW_GUIDE.md`` and friends) are scanned
by the reference pass but do not satisfy the per-example requirement.

Usage (run it *after* the examples whose artifacts are being checked):

    python3 scripts/testing/check_example_doc_references.py \
        --output-dir paraview_output --max-age-s 172800

**Exit codes (`OPS-19`, 2026-08-16)** — staleness does not own the exit code:

* ``0`` — clean: every reference resolves, every artifact is fresh, every
  example has its guide with all required headings.
* ``1`` — a **hard** violation: a dead reference (named file exists nowhere,
  or no run ever wrote the artifact), a missing guide, or a missing required
  heading. This is the defect class the checker exists for.
* ``2`` — **staleness only**: every reference resolves and the guide pass is
  green, but at least one `--output-dir` artifact is older than
  ``--max-age-s``. Nobody has re-run those examples lately; nothing is broken.

Before the split, 24 stale `paraview_output/` artifacts drove exit 1 on every
invocation, so a chunk touching examples could not tell its own breakage from
the backlog's without reading the log body (`EX-20`, `ANS-3`, both 2026-08-16).
``--stale-severity fail`` restores the old all-or-nothing reading (staleness
exits 1) for callers that want it; the default is ``report``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Exit codes (`OPS-19`). Callers gate on these, so they are named here and
# imported by the test module rather than restated (`ANS-1`).
EXIT_OK = 0
EXIT_HARD = 1
EXIT_STALE_ONLY = 2

RUNNER = REPO_ROOT / "scripts" / "run_examples.sh"

# `--list` prints one "  <selector> -> <repo-relative path>.py" line per example.
LIST_ENTRY_RE = re.compile(r"->\s+(\S+\.py)\s*$")

# Required guide sections (EX-15 / PROJECT_PLAN §5.4). Matched against markdown
# heading text case-insensitively as a substring, so "## 3. How to analyze it,
# step by step" satisfies the third one.
REQUIRED_HEADINGS = (
    "What this demonstrates",
    "How to run it",
    "How to analyze it, step by step",
)

ARTIFACT_SUFFIXES = (".xdmf", ".h5", ".bp", ".csv", ".json", ".png", ".msh")

# A filename-shaped token, with the extension not followed by another word
# character so "matplotlib.pyplot" does not read as "matplotlib.py".
REFERENCE_RE = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|" + "|".join(s[1:] for s in ARTIFACT_SUFFIXES) + r")(?![A-Za-z0-9_])"
)

# References that are deliberately not repo files or run outputs. Every entry
# carries the reason it is exempt; an empty reason is not allowed.
ALLOWLIST: dict[str, str] = {
    "lineplot.csv": (
        "user-created: the ParaView 'Plot Over Line' filter writes it by "
        "whatever name the reader chooses; the guide snippet is illustrative"
    ),
}


def artifact_mtime(target: Path) -> float:
    """Newest mtime of an artifact, looking *inside* directory artifacts.

    A `.bp` is an ADIOS2 directory, and rewriting it overwrites the same
    entries (`data.0`, `md.0`, ...) without touching the directory's own
    mtime — so `straight_wire_A.bp` read 158 h old on 2026-08-10 minutes
    after a run had refreshed every file in it (`EX-14`). Take the newest
    mtime in the tree instead, or the freshness rule flags an artifact no
    rerun can clear.
    """
    newest = target.stat().st_mtime
    if target.is_dir():
        for child in target.rglob("*"):
            newest = max(newest, child.stat().st_mtime)
    return newest


def display_path(path: Path) -> Path:
    """Repo-relative when the path is in the repo, absolute otherwise.

    `--docs-root` may point outside the repo (the `OPS-19` exit-code tests
    drive the checker over temp-dir fixtures), and a bare `relative_to` raises
    there — an unhandled ValueError, not a violation report.
    """
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


def collect_references(doc_paths: list[Path]) -> dict[str, list[tuple[Path, int]]]:
    """Map referenced filename -> list of ``(guide path, line number)`` sites.

    The *guide* is kept, not just its printable name, because `EX-29` resolves
    an artifact against the directory the citing example actually writes to.
    """
    references: dict[str, list[tuple[Path, int]]] = {}
    for doc in doc_paths:
        for lineno, line in enumerate(doc.read_text().splitlines(), start=1):
            for match in REFERENCE_RE.finditer(line):
                name = Path(match.group(0)).name
                references.setdefault(name, []).append((doc, lineno))
    return references


def format_sites(sites: list[tuple[Path, int]]) -> str:
    """The "<relpath>:<line>, ..." citation string reports carry."""
    return ", ".join(f"{display_path(doc)}:{lineno}" for doc, lineno in sites)


# Every example writes its artifacts to a `paraview_output/` directory; which
# one depends on the example (`Path(__file__).parent / "paraview_output"` for
# everything outside `mag`/`mri:1`, which write to the repo root).
OUTPUT_SUBDIR = "paraview_output"


def candidate_dirs(sites: list[tuple[Path, int]], output_dir: Path) -> list[Path]:
    """Directories an artifact cited at `sites` could legitimately live in.

    Example-relative first — that is the directory the citing example writes —
    then the shared `--output-dir`. Before `EX-29` only the latter was searched
    and any basename found anywhere under the docs root was exempted outright,
    so **22 of 27** runnable examples were never freshness-checked and every
    `stale=` reading was a census of the 5 that write to the repo root
    (known-issues 2026-08-23; measured pre-fix on 2026-08-24 at `stale=24`).
    """
    dirs: list[Path] = []
    for doc, _ in sites:
        example_dir = doc.parent / OUTPUT_SUBDIR
        if example_dir not in dirs:
            dirs.append(example_dir)
    if output_dir not in dirs:
        dirs.append(output_dir)
    return dirs


def safe_directory_args(docs_root: Path) -> list[str]:
    """`-c safe.directory=...` for every root a `git ls-files` here could need.

    The container runs as root over a bind mount owned by the host user, so a
    bare `git ls-files` in `/workspace` dies with "detected dubious ownership"
    (exit 128) — measured 2026-08-24 in the `fem-em-solver` image. Left
    unhandled that failure is silent in the wrong direction: `tracked_artifacts`
    returns `{}`, the `ans:` benchmark cases lose their committed-artifact
    exemption, and their `metrics.json` is reported as a *dead reference*. Both
    the repo root and the docs root are named because the exit-code fixtures
    point `--docs-root` at a throwaway repo of their own. `-c` is protected
    configuration, so git honours it; the value is not read from the repository
    under inspection.
    """
    roots = [REPO_ROOT, docs_root.resolve()]
    return [arg for root in roots for arg in ("-c", f"safe.directory={root}")]


def tracked_artifacts(docs_root: Path) -> dict[str, list[Path]]:
    """Artifact basenames git actually tracks under `docs_root`.

    A committed artifact is its own evidence — no run has to produce it, so the
    freshness rule does not apply. The pre-`EX-29` code assumed *any* artifact
    found under `examples/` was committed, but `.gitignore` ignores
    `paraview_output/` at every depth, so the exemption swallowed the entire
    scratch census. Asking git is the only reading of "committed" that cannot
    drift; a docs root that is not in a work tree yields an empty exemption,
    which is the safe direction.
    """
    if not docs_root.is_dir():
        return {}
    try:
        proc = subprocess.run(
            ["git", *safe_directory_args(docs_root), "ls-files", "-z", "--", "."],
            cwd=docs_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return {}
    tracked: dict[str, list[Path]] = {}
    for entry in proc.stdout.split("\0"):
        if not entry or not entry.endswith(ARTIFACT_SUFFIXES):
            continue
        path = docs_root / entry
        tracked.setdefault(path.name, []).append(path)
    return tracked


def repo_basenames() -> set[str]:
    """Every file basename tracked in the source and example trees."""
    names: set[str] = set()
    for root in ("src", "examples", "scripts", "tests"):
        for path in (REPO_ROOT / root).rglob("*.py"):
            names.add(path.name)
    return names


# Examples whose guides are commissioned but not yet written. Every entry names
# the step that owes it, and that step deletes its entries in the same commit
# that adds the guide — an empty reason is not allowed, and an entry for a
# script that already has a guide is itself a violation, so the list cannot rot
# into a permanent exemption. **Empty since `EX-15` step 3 (2026-08-11)**: the
# chunk landed guides for all 16 runnable examples, so every `--list` entry is
# now checked against the three required headings. A new example must ship its
# guide with it; adding an entry here is a deliberate, temporary exception.
PENDING_GUIDES: dict[str, str] = {}


def runnable_examples() -> list[Path]:
    """Every script ``./run_examples.sh --list`` enumerates, as absolute paths.

    The runner is asked rather than re-implemented: it discovers group scripts
    with ``find``, so any hand-maintained copy of the list here would drift the
    first time an example lands.
    """
    proc = subprocess.run(
        ["bash", str(RUNNER), "--list"],
        capture_output=True,
        text=True,
        check=True,
    )
    scripts: list[Path] = []
    for line in proc.stdout.splitlines():
        match = LIST_ENTRY_RE.search(line)
        if match:
            scripts.append(REPO_ROOT / match.group(1))
    return scripts


def markdown_headings(text: str) -> list[str]:
    """Heading text of every ATX heading line, markers and numbering stripped."""
    headings = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            headings.append(stripped.lstrip("#").strip().lower())
    return headings


def check_guides(scripts: list[Path]) -> list[str]:
    """One violation per missing guide or missing required heading."""
    violations: list[str] = []
    for script in scripts:
        rel_script = script.relative_to(REPO_ROOT)
        guide = script.with_suffix(".md")
        rel_guide = guide.relative_to(REPO_ROOT)
        if script.name in PENDING_GUIDES:
            if guide.exists():
                violations.append(
                    f"{rel_guide}: guide exists but {script.name} is still in "
                    f"PENDING_GUIDES ({PENDING_GUIDES[script.name]}) — drop the "
                    f"entry so the guide is actually checked"
                )
            continue
        if not guide.exists():
            violations.append(
                f"{rel_script}: runnable example with no guide page — write "
                f"{rel_guide} (EX-15: same-stem .md next to every "
                f"./run_examples.sh --list entry)"
            )
            continue
        headings = markdown_headings(guide.read_text())
        for required in REQUIRED_HEADINGS:
            if not any(required.lower() in heading for heading in headings):
                violations.append(
                    f"{rel_guide}: missing required heading '{required}' "
                    f"(EX-15: guides need all of {', '.join(REQUIRED_HEADINGS)})"
                )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="paraview_output",
        help="directory the examples write artifacts to (default: paraview_output)",
    )
    parser.add_argument(
        "--max-age-s",
        type=float,
        default=172800.0,
        help="an artifact older than this is treated as a stale leftover, not "
        "as evidence that a run produces it (default: 172800 = 48 h)",
    )
    parser.add_argument(
        "--docs-root",
        default="examples",
        help="tree whose *.md files are scanned (default: examples)",
    )
    parser.add_argument(
        "--stale-severity",
        choices=("fail", "report"),
        default="report",
        help="how a stale-but-present artifact is scored: 'report' (default) "
        f"keeps it out of the hard exit code (staleness alone exits "
        f"{EXIT_STALE_ONLY}), 'fail' restores the pre-OPS-19 reading where "
        f"staleness exits {EXIT_HARD}",
    )
    args = parser.parse_args()

    docs_root = REPO_ROOT / args.docs_root
    output_dir = REPO_ROOT / args.output_dir
    doc_paths = sorted(docs_root.rglob("*.md"))
    if not doc_paths:
        print(f"FAIL: no markdown guides found under {docs_root}")
        return EXIT_HARD

    references = collect_references(doc_paths)
    known_scripts = repo_basenames()
    tracked = tracked_artifacts(docs_root)
    now = time.time()
    violations: list[str] = []
    stale: list[str] = []

    for name in sorted(references):
        sites = format_sites(references[name])
        if name in ALLOWLIST:
            continue
        if name.endswith(".py"):
            if name not in known_scripts:
                violations.append(f"{name}: no such file in the repo  [{sites}]")
            continue

        # An artifact committed next to its own case (the `ans:` benchmarks keep
        # theirs in the case directory) is its own evidence — existence is
        # enough. Only run-written scratch needs the freshness rule, and only
        # git decides which is which (`EX-29`).
        if name in tracked:
            continue

        searched = candidate_dirs(references[name], output_dir)
        target = next((d / name for d in searched if (d / name).exists()), None)
        if target is None:
            where = ", ".join(f"{display_path(d)}/" for d in searched)
            violations.append(
                f"{name}: no run produced it in {where}, and it is "
                f"not committed under {args.docs_root}/  [{sites}]"
            )
            continue
        age = now - artifact_mtime(target)
        if age > args.max_age_s:
            stale.append(
                f"{name}: stale in {display_path(target.parent)}/ "
                f"({age / 3600:.1f} h old, "
                f"limit {args.max_age_s / 3600:.1f} h) — rerun the example that "
                f"writes it, or the reference is dead  [{sites}]"
            )

    checked = len(references) - len(ALLOWLIST & references.keys())
    print(
        f"Scanned {len(doc_paths)} guide(s) under {args.docs_root}/, "
        f"{checked} distinct file reference(s) checked, "
        f"{len(ALLOWLIST & references.keys())} allowlisted."
    )
    if violations:
        print(f"FAIL: {len(violations)} dead reference(s):")
        for violation in violations:
            print(f"  - {violation}")
    else:
        print("PASS: every referenced file exists.")
    if stale:
        label = "FAIL" if args.stale_severity == "fail" else "STALE"
        print(f"{label}: {len(stale)} stale artifact(s) (--stale-severity {args.stale_severity}):")
        for violation in stale:
            print(f"  - {violation}")
    else:
        print("PASS: every referenced artifact is fresh within the window.")

    try:
        scripts = runnable_examples()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: could not enumerate examples via {RUNNER.name} --list: {exc}")
        return EXIT_HARD
    if not scripts:
        print(f"FAIL: {RUNNER.name} --list enumerated no examples")
        return EXIT_HARD
    guide_violations = check_guides(scripts)
    pending = sum(1 for s in scripts if s.name in PENDING_GUIDES)
    print(
        f"Guide pass: {len(scripts)} runnable example(s) from "
        f"{RUNNER.relative_to(REPO_ROOT)} --list, {len(scripts) - pending} "
        f"checked against {len(REQUIRED_HEADINGS)} required heading(s), "
        f"{pending} pending (EX-15 steps 2-3)."
    )
    if guide_violations:
        print(f"FAIL: {len(guide_violations)} guide violation(s):")
        for violation in guide_violations:
            print(f"  - {violation}")
    else:
        print("PASS: every runnable example has a guide with all required sections.")

    # Exit-code contract (`OPS-19`): hard violations dominate, staleness only
    # reaches the exit code as EXIT_STALE_ONLY (or as a hard failure when the
    # caller asked for --stale-severity fail). The counts are printed on the
    # line below so a caller can gate on the numbers without parsing the body.
    stale_is_hard = args.stale_severity == "fail"
    hard_count = len(violations) + len(guide_violations) + (len(stale) if stale_is_hard else 0)
    if hard_count:
        status = EXIT_HARD
    elif stale:
        status = EXIT_STALE_ONLY
    else:
        status = EXIT_OK
    print(
        f"RESULT: dead={len(violations)} guide={len(guide_violations)} "
        f"stale={len(stale)} stale_severity={args.stale_severity} exit={status}"
    )
    return status


if __name__ == "__main__":
    sys.exit(main())
