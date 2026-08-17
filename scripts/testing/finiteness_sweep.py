#!/usr/bin/env python3
"""Sweep ``tests/`` for test functions with no quantitative assertion.

`OPS-17` step 1. A test function is a **candidate** (finiteness-only) when none
of its ``assert`` statements — nor any ``pytest.raises``/``approx`` call it
makes — carries a quantitative comparison: a closed-form value, a tolerance, a
measured rate, or a conservation/reciprocity identity in floating point.

Buckets, per ``assert`` statement:

``QUANT``
    ``np.isclose`` / ``np.allclose`` / ``math.isclose`` / ``pytest.approx`` /
    ``assert_allclose`` / ``assert_array_almost_equal``, or any comparison
    whose other side is a float literal (``err < 1e-9``, ``rate > 1.8``) or a
    **name bound to a float** anywhere in the module or the function
    (``residual < RECIPROCITY_TOLERANCE``) — the tolerance-constant idiom this
    repo uses everywhere.
``RAISES``
    the function's only contract is ``pytest.raises`` — an error-path contract
    test.  Listed separately from the finiteness candidates because "rejects
    bad input with this message" is a real behavioural gate, not a
    finiteness-only one.
``FINITE``
    ``np.isfinite`` / ``np.isnan`` / ``> 0`` / ``>= 0`` against an integer
    zero, ``.shape``/``len``/``.size``/``.ndim`` structure, ``is None`` /
    ``is not None`` / ``isinstance`` / bare truthiness.
``OTHER``
    everything else — integer/exact equality, set identity, string content.
    Reported so a human can adjudicate; never counted as quantitative.

A function with zero ``assert`` statements is a candidate too ("does not
raise"), flagged ``NOASSERT``.

Limitation, stated so the table is honest: assertions made inside a helper the
test calls are invisible to this AST sweep. Every candidate is confirmed by
reading before it is dispositioned.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

QUANT_FUNCS = {
    "isclose",
    "allclose",
    "approx",
    "assert_allclose",
    "assert_array_almost_equal",
    "assert_almost_equal",
}
FINITE_FUNCS = {"isfinite", "isnan", "isinf", "isinstance", "len"}
STRUCT_ATTRS = {"shape", "size", "ndim", "dtype"}


def _name_of(node: ast.AST) -> str:
    """Dotted-ish name of a call target, e.g. ``np.isclose`` -> ``isclose``."""
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _has_float_literal(node: ast.AST) -> bool:
    return any(
        isinstance(n, ast.Constant) and isinstance(n.value, float)
        for n in ast.walk(node)
    )


def float_names(scope: ast.AST) -> set[str]:
    """Names assigned an expression containing a float, anywhere in ``scope``.

    Catches the tolerance-constant idiom (``RECIPROCITY_TOLERANCE = 1e-6``,
    ``tol = 0.05``, ``TOL = 3 * BASE_TOL``) that a literal-only scan misses.
    Transitive through one more level: a name assigned from another float name.
    """
    names: set[str] = set()
    for _ in range(3):  # fixed point in practice after 2 passes
        grew = False
        for node in ast.walk(scope):
            targets = []
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            else:
                continue
            referenced = {n.id for n in ast.walk(value) if isinstance(n, ast.Name)}
            if not (_has_float_literal(value) or referenced & names):
                continue
            for t in targets:
                if isinstance(t, ast.Name) and t.id not in names:
                    names.add(t.id)
                    grew = True
        if not grew:
            break
    return names


def classify(test: ast.AST, tol_names: set[str]) -> tuple[str, list[str]]:
    """Return (bucket, per-assert buckets) for one assert statement."""
    calls = {_name_of(n.func) for n in ast.walk(test) if isinstance(n, ast.Call)}
    if calls & QUANT_FUNCS:
        return "QUANT", []
    # a comparison against a float literal, or against a name bound to a
    # float, is a tolerance or a closed-form value
    for cmp_node in ast.walk(test):
        if not isinstance(cmp_node, ast.Compare):
            continue
        if _has_float_literal(cmp_node):
            return "QUANT", []
        if any(
            isinstance(n, ast.Name) and n.id in tol_names
            for n in ast.walk(cmp_node)
        ):
            return "QUANT", []
    attrs = {n.attr for n in ast.walk(test) if isinstance(n, ast.Attribute)}
    if calls & FINITE_FUNCS or attrs & STRUCT_ATTRS:
        return "FINITE", []
    if isinstance(test, ast.Assert):
        t = test.test
        if isinstance(t, ast.Compare):
            for op, comp in zip(t.ops, t.comparators):
                if isinstance(op, (ast.Is, ast.IsNot)):
                    return "FINITE", []
                if isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)) and (
                    isinstance(comp, ast.Constant) and comp.value in (0, 1)
                ):
                    return "FINITE", []
            return "OTHER", []
        if isinstance(t, (ast.Name, ast.Attribute, ast.Call)):
            return "FINITE", []
    return "OTHER", []


def sweep(root: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(root.rglob("test_*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError as exc:  # pragma: no cover - surfaced, not swallowed
            print(f"!! parse failure {path}: {exc}", file=sys.stderr)
            continue
        module_tols = float_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            tols = module_tols | float_names(node)
            buckets: list[str] = []
            sources: list[str] = []
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Assert):
                    buckets.append(classify(stmt, tols)[0])
                    src = ast.unparse(stmt.test).replace("\n", " ")
                    sources.append(src[:150])
            raises = sum(
                1
                for n in ast.walk(node)
                if isinstance(n, ast.withitem)
                and isinstance(n.context_expr, ast.Call)
                and _name_of(n.context_expr.func) == "raises"
            )
            calls_helper = any(
                _name_of(n.func).startswith(("_assert", "assert_", "check_"))
                for n in ast.walk(node)
                if isinstance(n, ast.Call)
            )
            rows.append(
                {
                    "file": str(path),
                    "test": node.name,
                    "line": node.lineno,
                    "n_assert": len(buckets),
                    "quant": buckets.count("QUANT"),
                    "finite": buckets.count("FINITE"),
                    "other": buckets.count("OTHER"),
                    "raises": raises,
                    "helper": calls_helper,
                    "sources": sources,
                }
            )
    return rows


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "tests")
    rows = sweep(root)
    no_quant = [r for r in rows if r["quant"] == 0]
    # an error-path contract test is reported apart from the finiteness list
    raises_only = [r for r in no_quant if r["raises"] and r["other"] == 0]
    raises_ids = {id(r) for r in raises_only}
    cands = [r for r in no_quant if id(r) not in raises_ids]
    noassert = [r for r in cands if r["n_assert"] == 0 and not r["raises"]]

    print(f"scanned files      : {len({r['file'] for r in rows})}")
    print(f"test functions     : {len(rows)}")
    print(f"with QUANT assert  : {len(rows) - len(no_quant)}")
    print(f"RAISES-only (error-path contract): {len(raises_only)}")
    print(f"CANDIDATES (no QUANT, not raises-only): {len(cands)}")
    print(f"  of which NOASSERT : {len(noassert)}")
    print(f"  of which call a helper (may assert indirectly): "
          f"{sum(1 for r in cands if r['helper'])}")
    print()
    print("file :: test :: line :: n_assert finite/other :: flags")
    print("-" * 78)
    for r in sorted(cands, key=lambda r: (r["file"], r["line"])):
        flags = []
        if r["n_assert"] == 0 and not r["raises"]:
            flags.append("NOASSERT")
        if r["raises"]:
            flags.append(f"RAISES{r['raises']}")
        if r["helper"]:
            flags.append("HELPER")
        print(
            f"{r['file']} :: {r['test']} :: {r['line']} :: "
            f"{r['n_assert']} {r['finite']}/{r['other']} :: {','.join(flags) or '-'}"
        )
        for src in r["sources"]:
            print(f"      assert {src}")
    print()
    print("RAISES-only list (error-path contracts, reported not dispositioned)")
    print("-" * 78)
    for r in sorted(raises_only, key=lambda r: (r["file"], r["line"])):
        print(f"{r['file']} :: {r['test']} :: {r['line']} :: raises={r['raises']}")
    print()
    print("per-directory candidate counts")
    dirs: dict[str, int] = {}
    for r in cands:
        dirs[str(Path(r["file"]).parent)] = dirs.get(str(Path(r["file"]).parent), 0) + 1
    for d in sorted(dirs):
        print(f"  {d}: {dirs[d]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
