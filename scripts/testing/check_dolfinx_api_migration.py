#!/usr/bin/env python3
"""`OPS-26` step 1 — static sweep for un-migrated DolfinX call sites.

The dolfinx 0.7.2 → 0.11 upgrade (`OPS-18`) was re-gated by running the suite
and reading the logs. That checks "every cited log is green", not "every gate
executes": two defects have since surfaced, **both found by the examples layer
rather than by the upgrade** — ``core/cavity.py``'s
``assemble_matrix(diagonal=)`` (`TH-9`'s cavity gate was non-executing on
``main`` from the merge until `OPS-24`) and ``th:7``'s private
``interpolate(cells=)`` copy (`OPS-25`). Both **import** and **collect**
cleanly; only running the line raises.

This sweep is the static half of the answer. It reads every ``.py`` file under
the given roots, resolves each call whose callee is a DolfinX symbol, and
checks the call against the **signature of the module actually installed in
this interpreter** (``inspect.signature``). It deliberately does *not* carry a
list of the known renames: a list-based check can only rediscover the five
migrations that are already found, and the sweep's whole value is the sixth.

Five finding classes, all derived from introspection:

* ``missing-attr`` — a dotted path into ``dolfinx`` that no longer resolves.
  This is the ``io.gmshio`` / ``fem.FunctionSpace`` class: the attribute was
  removed or renamed, so the line raises ``AttributeError``/``ImportError`` the
  moment it executes.
* ``unknown-kwarg`` — a keyword the installed signature does not accept. The
  ``diagonal=`` → ``diag=`` and ``cells=`` → ``cells0=`` class.
* ``missing-required`` — a parameter with no default that the call does not
  supply. The ``LinearProblem(petsc_options_prefix=)`` class: 0.11 added a
  required argument, so every un-migrated construction raises ``TypeError``.
* ``too-many-positional`` — more positional arguments than the signature can
  bind. An arity change (a parameter removed, or moved keyword-only).
* ``uncheckable`` — informational: the callee resolves but exposes no
  introspectable signature (C extension types, some ``functools`` wrappers).
  Reported so the coverage claim is honest; never a violation.

**What it cannot see.** A *return*-shape change is invisible to a signature
check — ``model_to_mesh`` returning a ``MeshData`` triple-holder rather than a
tuple is a real 0.11 break that this sweep cannot flag, and neither can a type
change to an argument that is still accepted by name. Step 2's execution
census is what covers that class; this pass covers the call-signature class
exhaustively and says so.

Scope notes: only calls whose base name is imported from ``dolfinx`` in the
same file are considered, and a base name that is rebound anywhere in the
enclosing function (or at module level) is skipped as shadowed — those skips
are counted and printed, so the denominator is never silently short.

Usage (must run inside the container, where dolfinx is importable):

    python3 scripts/testing/check_dolfinx_api_migration.py --roots src tests
    python3 scripts/testing/check_dolfinx_api_migration.py --negative-control

Exit codes:

* ``0`` — clean: every resolved DolfinX call site matches the installed
  signature.
* ``1`` — at least one violation (``missing-attr``, ``unknown-kwarg``,
  ``missing-required``, ``too-many-positional``), each printed with module,
  line, and the introspected reason.
* ``2`` — the sweep could not run (dolfinx not importable, root missing).

The last line of stdout is machine-readable, in the `OPS-19` style::

    RESULT: files=NNN calls=NNN apis=NN violations=N uncheckable=N shadowed=N
"""
from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT_PACKAGE = "dolfinx"

VIOLATION_KINDS = (
    "missing-attr",
    "unknown-kwarg",
    "missing-required",
    "too-many-positional",
)


@dataclass
class Finding:
    kind: str
    path: str
    line: int
    api: str
    detail: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: [{self.kind}] {self.api} — {self.detail}"


@dataclass
class SweepReport:
    files: int = 0
    call_sites: int = 0
    per_api: dict = field(default_factory=dict)
    findings: list = field(default_factory=list)
    uncheckable: list = field(default_factory=list)
    shadowed: int = 0
    method_sites: int = 0

    @property
    def violations(self) -> list:
        return [f for f in self.findings if f.kind in VIOLATION_KINDS]


# --------------------------------------------------------------------------
# Resolution against the installed package
# --------------------------------------------------------------------------

_resolve_cache: dict = {}


def resolve_path(dotted: str):
    """Resolve a dotted path into the installed package.

    Returns ``(obj, None)`` on success or ``(None, reason)`` where *reason*
    names the first segment that failed and whether its parent was a module
    (an unresolvable attribute on a module is a real break; an unresolvable
    attribute on an instance-producing object is simply out of the sweep's
    reach).
    """
    if dotted in _resolve_cache:
        return _resolve_cache[dotted]
    parts = dotted.split(".")
    try:
        obj = importlib.import_module(parts[0])
    except Exception as exc:  # pragma: no cover - dolfinx missing is fatal earlier
        result = (None, f"cannot import {parts[0]}: {exc}")
        _resolve_cache[dotted] = result
        return result
    walked = parts[0]
    for seg in parts[1:]:
        parent_is_module = inspect.ismodule(obj)
        try:
            obj = getattr(obj, seg)
        except AttributeError:
            if parent_is_module:
                # A submodule may simply not be imported yet.
                try:
                    obj = importlib.import_module(f"{walked}.{seg}")
                except Exception:
                    result = (None, f"{walked} has no attribute {seg!r}")
                    _resolve_cache[dotted] = result
                    return result
            else:
                result = (None, f"__opaque__:{walked}.{seg}")
                _resolve_cache[dotted] = result
                return result
        walked = f"{walked}.{seg}"
    result = (obj, None)
    _resolve_cache[dotted] = result
    return result


def signature_of(obj):
    """Best-effort ``inspect.signature``; ``None`` when not introspectable."""
    try:
        return inspect.signature(obj)
    except (ValueError, TypeError):
        return None


def candidate_signatures(obj):
    """Every signature a call to *obj* could legally match.

    Usually one. ``functools.singledispatch`` is the exception and it is not a
    corner case here: ``dolfinx.mesh.create_cell_partitioner`` is dispatched,
    so ``inspect.signature`` reports only the *base* implementation
    ``(part, mode, max_facet_to_cell_links)`` while the registered
    ``GhostMode`` overload takes ``(mode, max_facet_to_cell_links)``. Checking
    the base alone reported the repo's landed, green `OPS-18` migration as a
    missing required argument — a false positive that would have made this
    sweep's one finding noise. A call is a violation only when it violates
    **every** registered implementation.
    """
    registry = getattr(obj, "registry", None)
    dispatch = getattr(obj, "dispatch", None)
    if registry is not None and callable(dispatch):
        sigs = []
        for impl in registry.values():
            sig = signature_of(impl)
            if sig is not None:
                sigs.append(sig)
        if sigs:
            return sigs
    sig = signature_of(obj)
    return [sig] if sig is not None else []


# --------------------------------------------------------------------------
# Per-file AST analysis
# --------------------------------------------------------------------------


def import_aliases(tree: ast.Module) -> dict:
    """Map local names to dolfinx dotted paths, from this file's imports."""
    aliases: dict = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == ROOT_PACKAGE or alias.name.startswith(ROOT_PACKAGE + "."):
                    local = alias.asname or alias.name.split(".")[0]
                    target = alias.name if alias.asname else alias.name.split(".")[0]
                    aliases[local] = target
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level:  # relative import, never dolfinx
                continue
            if mod != ROOT_PACKAGE and not mod.startswith(ROOT_PACKAGE + "."):
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                aliases[alias.asname or alias.name] = f"{mod}.{alias.name}"
    return aliases


def bound_names(node) -> set:
    """Names bound by assignment/parameter/loop/with/except inside *node*.

    Nested function and class bodies are excluded — their bindings do not
    shadow anything in this scope.
    """
    names: set = set()

    def add_target(t):
        if isinstance(t, ast.Name):
            names.add(t.id)
        elif isinstance(t, (ast.Tuple, ast.List)):
            for elt in t.elts:
                add_target(elt)
        elif isinstance(t, ast.Starred):
            add_target(t.value)

    def visit(n, top: bool):
        if not top and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
            return
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and top:
            a = n.args
            for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs):
                names.add(arg.arg)
            if a.vararg:
                names.add(a.vararg.arg)
            if a.kwarg:
                names.add(a.kwarg.arg)
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in targets:
                add_target(t)
        elif isinstance(n, (ast.For, ast.AsyncFor)):
            add_target(n.target)
        elif isinstance(n, (ast.With, ast.AsyncWith)):
            for item in n.items:
                if item.optional_vars is not None:
                    add_target(item.optional_vars)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            names.add(n.name)
        elif isinstance(n, (ast.comprehension,)):
            add_target(n.target)
        elif isinstance(n, (ast.NamedExpr,)):
            add_target(n.target)
        for child in ast.iter_child_nodes(n):
            visit(child, top=False)

    visit(node, top=True)
    return names


def dotted_of(node) -> str | None:
    """Render a Name/Attribute chain as a dotted string, else ``None``."""
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if not isinstance(cur, ast.Name):
        return None
    parts.append(cur.id)
    return ".".join(reversed(parts))


def scope_map(tree: ast.Module) -> list:
    """(scope_node, bound_names) pairs, innermost scopes last."""
    scopes = [(tree, bound_names(tree))]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scopes.append((node, bound_names(node)))
    return scopes


def enclosing_bindings(scopes, target) -> set:
    """Union of bindings of every scope whose body contains *target*."""
    bound: set = set()
    for scope, names in scopes:
        if scope is target:
            continue
        for n in ast.walk(scope):
            if n is target:
                bound |= names
                break
    return bound


def check_call(node: ast.Call, dotted: str, path: str, report: SweepReport) -> None:
    obj, reason = resolve_path(dotted)
    report.call_sites += 1
    report.per_api[dotted] = report.per_api.get(dotted, 0) + 1
    if obj is None:
        if reason.startswith("__opaque__:"):
            return
        report.findings.append(
            Finding("missing-attr", path, node.lineno, dotted, reason)
        )
        return
    sigs = candidate_signatures(obj)
    if not sigs:
        report.uncheckable.append(
            Finding("uncheckable", path, node.lineno, dotted, "no introspectable signature")
        )
        return

    per_sig = [check_against(node, sig, dotted, path) for sig in sigs]
    if any(not findings for findings in per_sig):
        return  # at least one overload accepts this call
    # Report the shortest explanation, so a dispatched API does not print one
    # complaint per registered implementation.
    report.findings.extend(min(per_sig, key=len))


def check_against(node: ast.Call, sig, dotted: str, path: str) -> list:
    """Findings this call would produce against exactly one signature."""
    out: list = []
    params = sig.parameters
    has_var_kw = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
    has_var_pos = any(p.kind is inspect.Parameter.VAR_POSITIONAL for p in params.values())
    # A class's __init__ carries an implicit self that signature() already drops.

    star_args = any(isinstance(a, ast.Starred) for a in node.args)
    star_kwargs = any(k.arg is None for k in node.keywords)

    named = {k.arg for k in node.keywords if k.arg is not None}
    if not has_var_kw:
        for kw in sorted(named):
            if kw not in params:
                accepted = ", ".join(
                    p.name for p in params.values()
                    if p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
                )
                out.append(Finding(
                    "unknown-kwarg", path, node.lineno, dotted,
                    f"installed signature does not accept {kw!r}; accepts: {accepted}",
                ))

    positional = [a for a in node.args if not isinstance(a, ast.Starred)]
    bindable = [
        p for p in params.values()
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if not has_var_pos and not star_args and len(positional) > len(bindable):
        out.append(Finding(
            "too-many-positional", path, node.lineno, dotted,
            f"{len(positional)} positional argument(s), signature binds at most "
            f"{len(bindable)}: {sig}",
        ))

    if not star_args and not star_kwargs:
        supplied = set(named)
        for i, p in enumerate(bindable):
            if i < len(positional):
                supplied.add(p.name)
        for p in params.values():
            if p.default is not inspect.Parameter.empty:
                continue
            if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            if p.name not in supplied:
                out.append(Finding(
                    "missing-required", path, node.lineno, dotted,
                    f"required parameter {p.name!r} not supplied; signature: {sig}",
                ))

    return out


# --------------------------------------------------------------------------
# Method pass
# --------------------------------------------------------------------------

# Submodules walked for the class/method table. dolfinx's public API lives in
# these; ``dolfinx.cpp`` is deliberately excluded (pybind11 methods carry no
# introspectable Python signature, so every site would land in `uncheckable`).
METHOD_MODULES = (
    "dolfinx", "dolfinx.fem", "dolfinx.fem.petsc", "dolfinx.mesh", "dolfinx.io",
    "dolfinx.io.gmsh", "dolfinx.geometry", "dolfinx.la", "dolfinx.plot",
    "dolfinx.graph", "dolfinx.common",
)

# Method names the sweep declines to attribute to DolfinX from a call site
# alone. This set is **derived, not hand-written** — a guess-list is exactly
# what the chunk forbids:
#
# * every attribute of ``numpy.ndarray`` and of ``object`` (so ``.copy``,
#   ``.sum``, ``.astype`` on an array are never read as ``Function.copy``);
# * every method name defined by a class in the swept tree itself, read out of
#   the AST (so ``solver.solve(current_density=...)`` on this project's own
#   solver classes is not read as a DolfinX ``solve``).
#
# The receiver-alias rule below removes the rest: ``np.array(x, dtype=...)``
# is skipped because ``np`` is imported from a non-DolfinX module in that file.
_derived_generic_names: frozenset = frozenset()

_method_table: dict | None = None


def method_table() -> dict:
    """``method name -> [(owner qualname, signature), ...]`` over DolfinX classes.

    Built by introspection, like everything else here: the sweep never carries
    a list of method names it expects to have changed.
    """
    global _method_table
    if _method_table is not None:
        return _method_table
    table: dict = {}
    for mod_name in METHOD_MODULES:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        for cls_name, cls in vars(mod).items():
            if not inspect.isclass(cls) or cls_name.startswith("_"):
                continue
            if not getattr(cls, "__module__", "").startswith(ROOT_PACKAGE):
                continue
            for meth_name, meth in vars(cls).items():
                if meth_name.startswith("_") or meth_name in _derived_generic_names:
                    continue
                target = meth.fget if isinstance(meth, property) else meth
                if not (inspect.isfunction(target) or inspect.ismethod(target)):
                    continue
                sig = signature_of(target)
                if sig is None:
                    continue
                table.setdefault(meth_name, []).append(
                    (f"{mod_name}.{cls_name}.{meth_name}", sig)
                )
    _method_table = table
    return table


def derive_generic_names(files) -> frozenset:
    """Method names the method pass must not claim (see the comment above)."""
    names = set(dir(object))
    try:
        import numpy as _np
        names |= set(dir(_np.ndarray))
    except Exception:
        pass
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.add(item.name)
    return frozenset(names)


def foreign_aliases(tree: ast.Module) -> set:
    """Names this file imports from something other than dolfinx."""
    out: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == ROOT_PACKAGE or alias.name.startswith(ROOT_PACKAGE + "."):
                    continue
                out.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if not node.level and (mod == ROOT_PACKAGE or mod.startswith(ROOT_PACKAGE + ".")):
                continue
            for alias in node.names:
                if alias.name != "*":
                    out.add(alias.asname or alias.name)
    return out


def check_method_call(node: ast.Call, path: str, report: SweepReport) -> None:
    """Keyword check for ``obj.method(...)`` where *obj* is not statically known.

    This is the class the dotted-path pass structurally cannot see, and it is
    not a corner: `OPS-25`'s defect was ``e_series_fn.interpolate(cells=...)``
    on a ``Function`` instance, and `OPS-24`'s was one attribute lookup away
    from the same shape. A keyword is flagged only when **every** DolfinX class
    that defines a method of this name rejects it — so a same-named method on
    a non-DolfinX object is only ever mis-flagged if it happens to share the
    name *and* use a keyword no DolfinX overload accepts. That residual risk is
    what the clean baseline over ``src`` + ``tests`` measures.
    """
    name = node.func.attr
    owners = method_table().get(name)
    if not owners:
        return
    named = [k.arg for k in node.keywords if k.arg is not None]
    if not named:
        return
    report.method_sites += 1
    for kw in sorted(set(named)):
        accepted_by = []
        for qualname, sig in owners:
            params = sig.parameters
            if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
                accepted_by.append(qualname)
            elif kw in params:
                accepted_by.append(qualname)
        if accepted_by:
            continue
        consulted = ", ".join(q for q, _ in owners)
        report.findings.append(Finding(
            "unknown-kwarg", path, node.lineno, f"<instance>.{name}",
            f"no DolfinX class defining {name!r} accepts {kw!r}; consulted: {consulted}",
        ))


def check_attribute(node: ast.Attribute, dotted: str, path: str, report: SweepReport) -> None:
    obj, reason = resolve_path(dotted)
    if obj is None and not reason.startswith("__opaque__:"):
        report.findings.append(Finding("missing-attr", path, node.lineno, dotted, reason))


def sweep_file(path: Path, display: str, report: SweepReport) -> None:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        report.findings.append(Finding(
            "missing-attr", display, exc.lineno or 0, "<parse>", f"unparseable: {exc.msg}",
        ))
        return
    report.files += 1
    aliases = import_aliases(tree)
    foreign = foreign_aliases(tree)
    # One step of provenance: ``tree = ET.parse(...)`` makes ``tree`` an
    # ElementTree, so ``tree.write(encoding=...)`` is not DolfinX's
    # ``VTXWriter.write``. Without this the method pass reports the stdlib.
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Call)):
            continue
        src_dotted = dotted_of(node.value.func)
        if src_dotted and src_dotted.split(".")[0] in foreign:
            foreign.add(node.targets[0].id)

    # The method pass does not depend on this file importing dolfinx: a
    # `Function` reaches a helper as an argument, and the call site that rots
    # is in a module whose imports name only `fem_em_solver`. Calls the dotted
    # pass already owns are skipped here so nothing is reported twice.
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        dotted = dotted_of(node.func)
        if dotted is not None:
            base = dotted.split(".")[0]
            if base in aliases:
                continue  # the dotted pass owns this call
            if base in foreign:
                continue  # receiver comes from a non-DolfinX import
        check_method_call(node, display, report)

    if not aliases:
        return
    scopes = scope_map(tree)

    call_funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_funcs.add(id(node.func))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            dotted = dotted_of(node.func)
            if dotted is None:
                continue
            base = dotted.split(".")[0]
            if base not in aliases:
                continue
            if base in enclosing_bindings(scopes, node):
                report.shadowed += 1
                continue
            full = aliases[base] + dotted[len(base):]
            check_call(node, full, display, report)
        elif isinstance(node, ast.Attribute) and id(node) not in call_funcs:
            dotted = dotted_of(node)
            if dotted is None:
                continue
            base = dotted.split(".")[0]
            if base not in aliases:
                continue
            if base in enclosing_bindings(scopes, node):
                continue
            full = aliases[base] + dotted[len(base):]
            check_attribute(node, full, display, report)


def python_files(roots, repo_root: Path):
    for root in roots:
        base = (repo_root / root).resolve()
        if not base.exists():
            raise FileNotFoundError(base)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in {"__pycache__", ".git"})
            for name in sorted(filenames):
                if name.endswith(".py"):
                    yield Path(dirpath) / name


def sweep(roots, repo_root: Path) -> SweepReport:
    global _derived_generic_names, _method_table
    _derived_generic_names = derive_generic_names(python_files(roots, repo_root))
    _method_table = None  # the exclusions feed the table; rebuild it
    report = SweepReport()
    for root in roots:
        base = (repo_root / root).resolve()
        if not base.exists():
            raise FileNotFoundError(base)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in {"__pycache__", ".git"})
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                p = Path(dirpath) / name
                try:
                    display = str(p.relative_to(repo_root))
                except ValueError:
                    display = str(p)
                sweep_file(p, display, report)
    return report


# --------------------------------------------------------------------------
# Negative control
# --------------------------------------------------------------------------

# Each entry reverts one landed 0.11 migration in a temp copy of a real repo
# file, and names the finding kind the sweep must produce. A sweep that cannot
# fail is not a sweep (`OPS-26` step 1, binding).
#
# ``FunctionSpace`` is the instructive one and its expected kind is *not*
# ``missing-attr``: 0.11 kept the name as a three-argument class
# ``(mesh, element, cppV)`` and moved the user-facing constructor to lowercase
# ``functionspace``. The old two-argument call therefore does not fail on
# lookup — it fails on **arity**, which is exactly why the rename was easy to
# miss by eye and why the sweep checks signatures rather than names.
REVERSIONS = (
    ("dolfinx.fem.functionspace(", "dolfinx.fem.FunctionSpace(", "missing-required"),
    ("fem.functionspace(", "fem.FunctionSpace(", "missing-required"),
    ("cells0=", "cells=", "unknown-kwarg"),
    ("diag=", "diagonal=", "unknown-kwarg"),
    ("petsc_options_prefix=", "legacy_options_prefix=", "unknown-kwarg"),
    ("from dolfinx.io import gmsh as", "from dolfinx.io import gmshio as",
     "missing-attr"),
)


def code_occurrence(text: str, needle: str):
    """Offset of the first *executable* occurrence of *needle*, else ``None``.

    A plain ``str.replace`` reverted the first textual match, which — once this
    checker's own gate module documented the ``cells0=`` rename — was a
    **docstring**. Reverting prose changes nothing, so the control reported a
    false failure. An occurrence counts only when the line it sits on carries a
    call or an import in the parsed AST.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    live = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Call, ast.Import, ast.ImportFrom)):
            for ln in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                live.add(ln)
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            return None
        if text.count("\n", 0, idx) + 1 in live:
            return idx
        start = idx + 1


def negative_control(repo_root: Path, roots) -> int:
    """Revert landed migrations in a temp copy; every revert must be flagged."""
    baseline = sweep(roots, repo_root)
    print("negative control — baseline over " + ", ".join(roots))
    print(f"  baseline violations: {len(baseline.violations)}")

    tmp = Path(tempfile.mkdtemp(prefix="ops26-negctl-"))
    try:
        for root in roots:
            shutil.copytree(repo_root / root, tmp / root,
                            ignore=shutil.ignore_patterns("__pycache__"))
        applied = []
        for new, old, kind in REVERSIONS:
            hit = None
            for p in sorted(tmp.rglob("*.py")):
                text = p.read_text(encoding="utf-8")
                offset = code_occurrence(text, new)
                if offset is None:
                    continue
                p.write_text(text[:offset] + old + text[offset + len(new):],
                             encoding="utf-8")
                hit = (p, text.count(new))
                break
            if hit is None:
                print(f"  SKIP  {new} -> {old}: no site in the tree to revert")
                continue
            applied.append((new, old, kind, str(hit[0].relative_to(tmp))))
            print(f"  revert {new} -> {old} in {hit[0].relative_to(tmp)} (expect {kind})")

        reverted = sweep(roots, tmp)
        print(f"  reverted-tree violations: {len(reverted.violations)}"
              f" (baseline {len(baseline.violations)})")
        for f in reverted.violations:
            print("    " + f.render())

        failures = []
        if len(reverted.violations) <= len(baseline.violations):
            failures.append("reverting migrations did not increase the violation count")
        # Matched per file, not globally: a control that only counts kinds
        # would pass on one revert detected six times.
        for new, old, kind, where in applied:
            if not any(f.kind == kind and f.path == where for f in reverted.violations):
                failures.append(f"revert {new}->{old} in {where} produced no {kind} finding")
        if not applied:
            failures.append("no reversion could be applied — the control is vacuous")

        if failures:
            for msg in failures:
                print(f"  FAIL: {msg}")
            print(f"RESULT: negative-control applied={len(applied)} "
                  f"detected=0 status=fail")
            return 1
        print(f"RESULT: negative-control applied={len(applied)} "
              f"baseline={len(baseline.violations)} "
              f"reverted={len(reverted.violations)} status=pass")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--roots", nargs="+", default=["src", "tests"])
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--negative-control", action="store_true")
    parser.add_argument("--show-apis", action="store_true",
                        help="print the per-API call-site census")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    try:
        importlib.import_module(ROOT_PACKAGE)
    except Exception as exc:
        print(f"cannot import {ROOT_PACKAGE}: {exc} — run this inside the container")
        return 2

    if args.negative_control:
        return negative_control(repo_root, args.roots)

    try:
        report = sweep(args.roots, repo_root)
    except FileNotFoundError as exc:
        print(f"root does not exist: {exc}")
        return 2

    if args.show_apis:
        print(f"per-API call-site census over {', '.join(args.roots)}:")
        for api, count in sorted(report.per_api.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {count:5d}  {api}")

    if report.uncheckable:
        by_api: dict = {}
        for f in report.uncheckable:
            by_api[f.api] = by_api.get(f.api, 0) + 1
        print(f"uncheckable (no introspectable signature) — {len(report.uncheckable)} "
              f"site(s) over {len(by_api)} API(s):")
        for api, count in sorted(by_api.items()):
            print(f"  {count:5d}  {api}")

    violations = report.violations
    if violations:
        print(f"VIOLATIONS ({len(violations)}):")
        for f in violations:
            print("  " + f.render())
    else:
        print("no un-migrated call sites: every resolved DolfinX call matches "
              "the installed signature")

    print(f"RESULT: files={report.files} calls={report.call_sites} "
          f"apis={len(report.per_api)} methods={report.method_sites} "
          f"violations={len(violations)} "
          f"uncheckable={len(report.uncheckable)} shadowed={report.shadowed}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
