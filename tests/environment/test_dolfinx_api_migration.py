"""`OPS-26` step 1 — the 0.11 migration completeness gate (static half).

`OPS-18` moved the image from dolfinx 0.7.2 to 0.11 and re-gated by running
the suite. That checks "every cited log is green", not "every gate executes":
two un-migrated call sites have since surfaced, **both found by the examples
layer rather than by the upgrade** — ``core/cavity.py``'s
``assemble_matrix(diagonal=)`` (`TH-9`'s cavity gate was non-executing on
``main`` from the merge until `OPS-24`) and ``th:7``'s private
``interpolate(cells=)`` copy (`OPS-25`). Both import and collect cleanly.

This module runs ``scripts/testing/check_dolfinx_api_migration.py``, which
resolves every DolfinX call site under ``src/`` and ``tests/`` against the
signature of the module **actually installed in this interpreter** rather than
against a list of known renames — a list can only rediscover the five
migrations already found, and the sweep's value is the sixth.

Three gates, all quantitative:

1. **Zero survivors** over ``src`` + ``tests``, with the census (files, call
   sites, distinct APIs) asserted non-degenerate so a sweep that silently
   stopped resolving anything cannot pass as clean.
2. **The negative control** — reverting six landed migrations in a temp copy
   must produce a finding *in the file each revert touched*. A sweep that
   cannot fail is not a sweep (`OPS-26` step 1, binding).
3. **The filed survivors** outside the gated roots stay exactly the two
   ``scripts/probes/`` sites this chunk found (known-issues 2026-08-25), so
   the count cannot drift in either direction unnoticed.

Static by construction: no mesh, no solve, smoke tier.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "scripts" / "testing" / "check_dolfinx_api_migration.py"

# Measured 2026-08-25 on the 0.11 image (log 20260825T200851Z_OPS-26): 159
# files, 434 resolved call sites, 29 distinct DolfinX APIs. Asserted as floors,
# not equalities — the suite grows, and pinning the exact count would turn
# every new test file into a red. The floors exist to catch the opposite
# failure: a resolution bug that quietly sweeps nothing and reports "clean".
MIN_FILES = 120
MIN_CALL_SITES = 350
MIN_APIS = 20

# `OPS-26` step 1's finding, filed not fixed (known-issues.md, 2026-08-25):
# two one-off probe scripts still construct `LinearProblem` without 0.11's
# required `petsc_options_prefix`. Nothing runs them — which is the point.
FILED_SURVIVORS = {
    ("scripts/probes/mag13_step2b_recovery.py", "missing-required"),
    ("scripts/probes/post3_step3_debug.py", "missing-required"),
}


@pytest.fixture(scope="module")
def checker():
    spec = importlib.util.spec_from_file_location("ops26_checker", CHECKER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_no_unmigrated_call_sites(checker):
    """Every resolved DolfinX call under src/ and tests/ matches 0.11."""
    report = checker.sweep(["src", "tests"], REPO_ROOT)

    assert report.files >= MIN_FILES, (
        f"swept only {report.files} files (floor {MIN_FILES}) — the sweep is "
        "not reaching the tree, so 'clean' would mean nothing"
    )
    assert report.call_sites >= MIN_CALL_SITES, (
        f"resolved only {report.call_sites} call sites (floor {MIN_CALL_SITES})"
    )
    assert len(report.per_api) >= MIN_APIS, (
        f"resolved only {len(report.per_api)} distinct APIs (floor {MIN_APIS})"
    )

    violations = report.violations
    assert violations == [], (
        "un-migrated DolfinX call site(s):\n  "
        + "\n  ".join(f.render() for f in violations)
    )


def test_negative_control_detects_reverted_migrations(checker, capsys):
    """Reverting a landed migration in a temp copy must be flagged.

    Binding per the chunk: the six reversions cover all three violation
    classes — ``missing-required`` (0.11's three-argument ``FunctionSpace``,
    which still *exists*, so the old two-argument call fails on arity rather
    than on lookup), ``unknown-kwarg`` (``cells0=``/``diag=``/
    ``petsc_options_prefix=``) and ``missing-attr`` (``io.gmsh`` reverted to
    ``io.gmshio``).
    """
    status = checker.negative_control(REPO_ROOT, ["src", "tests"])
    out = capsys.readouterr().out
    assert status == 0, f"negative control failed:\n{out}"
    assert "status=pass" in out
    assert "applied=6" in out, "a reversion silently found no site to revert"


def test_filed_survivors_outside_the_gated_roots_are_unchanged(checker):
    """The two filed ``scripts/probes/`` survivors, no more and no fewer."""
    report = checker.sweep(["examples", "scripts"], REPO_ROOT)
    found = {(f.path, f.kind) for f in report.violations}
    assert found == FILED_SURVIVORS, (
        "survivor set outside src/tests moved — expected the two filed probe "
        f"sites, found:\n  "
        + "\n  ".join(f.render() for f in report.violations)
    )
