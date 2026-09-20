"""`OPS-53` — ``write_setup_figure`` refuses a title it cannot draw.

The helper draws its title as one unwrapped ``add_text`` on a fixed canvas, so
a title past the measured bracket ([126 ok, 150 clipped] at font size 11) is
silently clipped at the canvas edge — a false artefact the setup-figure census
cannot see (`broken` only checks that the file parses). This module asserts the
guard added by `OPS-53`:

* the limit itself — 131 characters raise, 130 do not, with both integers in
  the message;
* every ``write_setup_figure(`` call site in the tree whose ``title=`` is a
  compile-time constant is inside the limit (call sites parsed with ``ast``:
  an f-string title defeats a regex scan, and those sites are *listed*, not
  failed);
* the negative control — the 150-character case raises, and the helper at the
  pinned pre-change sha has no guard at all.

Nothing here renders: importing ``setup_figure`` must not import ``pyvista``
(the plotting imports live inside :func:`_render`), and that is asserted too.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from fem_em_solver.post.setup_figure import MAX_TITLE_CHARS, check_title_length

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER_REL = "src/fem_em_solver/post/setup_figure.py"
HELPER = REPO_ROOT / HELPER_REL

# `OPS-59` (2026-09-20) replaced the literal `EXPECTED_EXAMPLE_CALL_SITES = 18`
# by the identity it stood for. The literal was an equality on a count that
# `EX-57` grows by one per figure slot, so it was red on `main` within two days
# of being written (18 pinned, 21 on the tree — measured
# `20260920T130047Z_OPS-59-prechange.log:763–764`). What the pin actually meant
# is that the three counts move together: one `write_setup_figure(` call site
# per committed `*_setup.png` per census `ok` row. That is asserted below and
# needs no edit when a figure lands.
SETUP_FIGURE_SUFFIX = "_setup.png"
CENSUS = REPO_ROOT / "scripts" / "testing" / "check_example_setup_figures.py"


def _committed_setup_figures() -> list[str]:
    """Tracked `examples/**/figures/*_setup.png`, straight from git."""
    proc = subprocess.run(
        ["git", "-c", "safe.directory=*", "-C", str(REPO_ROOT),
         "ls-files", "-z", "--", "examples"],
        capture_output=True, text=True, check=True,
    )
    return sorted(
        entry for entry in proc.stdout.split("\0")
        if entry.endswith(SETUP_FIGURE_SUFFIX) and "/figures/" in entry
    )


def _census_ok_count() -> int:
    """The `EX-57` census's own `ok` count, from the census module."""
    spec = importlib.util.spec_from_file_location("ex57_census_for_ops59", CENSUS)
    census = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(census)
    return sum(
        1 for script in census.runnable_examples()
        if census.assess(script, 600.0)[0] == "ok"
    )

# The commit the guard was written against — the last commit before the
# `OPS-53` change. Pinned, never HEAD: the control has to read a tree that
# provably predates the guard.
PRE_CHANGE_SHA = "8ef79a1465c083e1abf60f3026579d78de78be69"

# The 150-character title the 2026-09-18 07:30 slot first tried is **not**
# recorded anywhere in the tree: `20260918T123728Z_EX-57.log`'s
# `[setup-figure]` line prints only the path and the region map, and
# attempts.md paraphrases the title rather than quoting it. So this is a
# *synthetic* 150-character string standing in for it — the guard depends on
# the length alone, not on the characters.
SYNTHETIC_150 = ("mesh:4 — two-torus port sheet: each gap box split by its "
                 "mid-plane port sheet, the split visible as the seam between "
                 "the two cell groups drawn (EX-57)")


def _title_node(call: ast.Call) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == "title":
            return keyword.value
    return None


def _write_setup_figure_calls(source: str, label: str) -> list[tuple[str, int, ast.expr | None]]:
    """Every ``write_setup_figure(...)`` *call* in ``source`` (not its def)."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name == "write_setup_figure":
            found.append((label, node.lineno, _title_node(node)))
    return found


def _exemplar_call() -> list[tuple[str, int, ast.expr | None]]:
    """The exemplar call in the helper module's own docstring.

    It lives in a literal block inside the docstring, so ``ast`` over the file
    never sees it; the block is dedented and parsed on its own.
    """
    module = ast.parse(HELPER.read_text())
    doc = ast.get_docstring(module)
    assert doc is not None, "setup_figure.py lost its module docstring"
    lines = doc.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.strip() == "write_setup_figure("]
    assert len(starts) == 1, f"expected one exemplar call in the docstring, found {len(starts)}"
    start = starts[0]
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == ")")
    snippet = textwrap.dedent("\n".join(lines[start:end + 1]))
    return _write_setup_figure_calls(snippet, f"{HELPER_REL} (docstring exemplar)")


def _constant_title(node: ast.expr | None) -> str | None:
    """The title as a compile-time string, or ``None`` if it is not one.

    Implicit concatenation of adjacent literals is already folded into a
    single ``ast.Constant`` by the parser; f-strings (``JoinedStr``) and
    ``%``/``+`` expressions (``BinOp``) are not constants and are listed.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


# --------------------------------------------------------------------------
# (a) the limit
# --------------------------------------------------------------------------

def test_one_character_over_the_limit_raises_naming_both_integers():
    too_long = "x" * (MAX_TITLE_CHARS + 1)
    with pytest.raises(ValueError) as excinfo:
        check_title_length(too_long)
    message = str(excinfo.value)
    print(f"[OPS-53] ValueError at {MAX_TITLE_CHARS + 1} chars: {message}", flush=True)
    assert str(MAX_TITLE_CHARS + 1) in message, message
    assert str(MAX_TITLE_CHARS) in message, message


def test_exactly_the_limit_does_not_raise():
    at_limit = "x" * MAX_TITLE_CHARS
    assert check_title_length(at_limit) == at_limit


def test_limit_is_the_measured_value():
    # Bracket [126 ok, 150 clipped]; see the constant's comment.
    assert MAX_TITLE_CHARS == 130
    assert 126 <= MAX_TITLE_CHARS < 150


def test_guard_path_does_not_import_pyvista():
    assert "pyvista" not in sys.modules, (
        "importing fem_em_solver.post.setup_figure must not pull in pyvista; "
        "the plotting imports belong inside _render"
    )


# --------------------------------------------------------------------------
# (b) the call-site scan
# --------------------------------------------------------------------------

def test_every_constant_call_site_title_is_within_the_limit():
    example_calls: list[tuple[str, int, ast.expr | None]] = []
    for path in sorted((REPO_ROOT / "examples").rglob("*.py")):
        source = path.read_text()
        if "write_setup_figure(" not in source:
            continue
        example_calls.extend(
            _write_setup_figure_calls(source, str(path.relative_to(REPO_ROOT)))
        )

    figures = _committed_setup_figures()
    census_ok = _census_ok_count()
    print(
        f"[OPS-59] call_sites={len(example_calls)} committed_setup_pngs="
        f"{len(figures)} census_ok={census_ok}",
        flush=True,
    )
    assert len(example_calls) == len(figures) == census_ok, (
        f"the three counts must move together: {len(example_calls)} "
        f"write_setup_figure call sites under examples/, {len(figures)} "
        f"committed *_setup.png, {census_ok} census ok. Call sites: "
        + ", ".join(f"{label}:{line}" for label, line, _ in example_calls)
        + f". Figures: {figures}"
    )

    calls = example_calls + _exemplar_call()
    over, non_constant = [], []
    for label, line, node in calls:
        assert node is not None, f"{label}:{line} passes no title"
        title = _constant_title(node)
        if title is None:
            non_constant.append(f"{label}:{line}")
            continue
        if len(title) > MAX_TITLE_CHARS:
            over.append(f"{label}:{line} ({len(title)} chars)")

    # Listed, never failed: a runtime-formatted title cannot be checked here,
    # only by the guard when the example runs.
    print(
        "[OPS-53] non-constant titles (checked at runtime by the guard, "
        f"not here): {non_constant or 'none'}",
        flush=True,
    )
    assert not over, f"call-site titles over MAX_TITLE_CHARS={MAX_TITLE_CHARS}: {over}"


# --------------------------------------------------------------------------
# (c) the negative control
# --------------------------------------------------------------------------

def test_the_150_character_case_raises():
    assert len(SYNTHETIC_150) == 150, len(SYNTHETIC_150)
    with pytest.raises(ValueError):
        check_title_length(SYNTHETIC_150)


def test_pre_change_helper_has_no_guard():
    scratch_dir = REPO_ROOT / "logs"
    scratch_dir.mkdir(exist_ok=True)
    scratch = scratch_dir / f"ops53_setup_figure_pre_change_{os.getpid()}.py"
    completed = subprocess.run(
        ["git", "-c", "safe.directory=*", "-C", str(REPO_ROOT),
         "show", f"{PRE_CHANGE_SHA}:{HELPER_REL}"],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    scratch.write_text(completed.stdout)
    try:
        spec = importlib.util.spec_from_file_location(
            f"_ops53_pre_change_{os.getpid()}", scratch
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert not hasattr(module, "check_title_length"), (
            f"{PRE_CHANGE_SHA} already has a guard function — the pin is wrong"
        )
        assert not hasattr(module, "MAX_TITLE_CHARS"), (
            f"{PRE_CHANGE_SHA} already has MAX_TITLE_CHARS — the pin is wrong"
        )
        # And the pre-change helper accepts the 150-character title without
        # complaint at every point a guard could have lived.
        assert "MAX_TITLE_CHARS" not in completed.stdout
    finally:
        scratch.unlink(missing_ok=True)
