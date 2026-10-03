"""Edits that could make a test pass without fixing the code: refused before they are applied.

The tests are the executive's only verifier, so an edit that defeats the tests is the one
failure it cannot see (review finding F4 C: a float subclass whose `__eq__` is always true
passed the visible and the held-out tests). Mutation testing does not catch that shape either,
since a mutated always-equal value still compares equal. These checks are static, run on the
file as it would be after the edit, and look only at what the edit *adds*:

- comparison, truth, hashing or attribute-hook dunders (`__eq__`, `__bool__`, `__getattr__`, ...);
- references to test or interpreter machinery (`pytest`, `unittest`, `sys.modules`, `builtins`,
  `os._exit`, `sys.exit`, `atexit`, `__import__`, `inspect`, `gc`, frame access);
- broad exception swallowing (`except:` or `except Exception`/`BaseException` whose body only
  passes, returns or continues);
- non-trivial literals copied from the failing test (special-casing the test's inputs or
  expected values).

A hit hands the subgoal off (`out_of_scope`) instead of applying the edit. False positives cost
a handoff to a stronger tier, never a wrong `complete`.
"""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

DUNDERS = {"__eq__", "__ne__", "__lt__", "__le__", "__gt__", "__ge__", "__bool__", "__len__", "__hash__",
           "__getattr__", "__getattribute__", "__instancecheck__", "__subclasscheck__", "__contains__",
           "__float__", "__int__", "__index__", "__round__", "__abs__", "__repr__", "__str__", "__del__"}
MACHINERY_NAMES = {"pytest", "unittest", "builtins", "__builtins__", "atexit", "__import__", "inspect", "gc",
                   "_pytest", "importlib", "ctypes"}
MACHINERY_ATTRS = {("sys", "modules"), ("sys", "exit"), ("os", "_exit"), ("sys", "_getframe"),
                   ("sys", "settrace"), ("sys", "setprofile"), ("sys", "excepthook"), ("os", "kill")}
TRIVIAL = {0, 1, -1, 2, 0.0, 1.0, "", True, False, None}


def _features(tree: ast.AST) -> Counter:
    out: Counter = Counter()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in DUNDERS:
            out[("dunder", node.name)] += 1
        elif isinstance(node, ast.Name) and node.id in MACHINERY_NAMES:
            out[("machinery", node.id)] += 1
        elif isinstance(node, ast.alias) and node.name.split(".")[0] in MACHINERY_NAMES:
            out[("machinery", node.name.split(".")[0])] += 1
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in MACHINERY_NAMES:
            out[("machinery", node.module.split(".")[0])] += 1
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and (node.value.id, node.attr) in MACHINERY_ATTRS:
            out[("machinery", f"{node.value.id}.{node.attr}")] += 1
        elif isinstance(node, ast.Attribute) and node.attr in ("f_back", "f_locals", "f_globals", "tb_frame"):
            out[("machinery", node.attr)] += 1
        elif isinstance(node, ast.ExceptHandler) and _broad(node):
            out[("swallow", "except")] += 1
        if isinstance(node, (ast.Constant, ast.List, ast.Tuple, ast.Set, ast.Dict)):
            lit = _literal(node)
            if lit is not None:
                out[("literal", lit)] += 1
    return out


def _broad(h: ast.ExceptHandler) -> bool:
    if h.type is not None and not (isinstance(h.type, ast.Name) and h.type.id in ("Exception", "BaseException")):
        return False
    return all(isinstance(s, (ast.Pass, ast.Continue)) or (isinstance(s, ast.Return)) or
               (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)) for s in h.body)


def _literal(node: ast.AST) -> str | None:
    """A canonical form of a non-trivial literal, or None."""
    try:
        value = ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return None if value in TRIVIAL else repr(value)
    if isinstance(value, str):
        return None if len(value) <= 3 else repr(value)
    if isinstance(value, (list, tuple, set, dict)):
        return repr(value) if len(value) >= 2 else None
    return None


def _test_literals(root: Path, nodeid: str | None) -> set:
    if not nodeid:
        return set()
    path = root / nodeid.split("::", 1)[0]
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return set()
    return {k[1] for k in _features(tree) if k[0] == "literal"}


def suspicious(root: Path, edits: list[dict], failing_test: str | None) -> str | None:
    """Why this edit could game the tests, or None. Edits are {path, old, new} on workspace files."""
    root = Path(root)
    by_path: dict[str, str] = {}
    for e in edits:
        p = root / e["path"]
        before = by_path.get(e["path"])
        if before is None:
            try:
                before = p.read_text(encoding="utf-8")
            except OSError:
                return None  # the edit will be refused by the workspace anyway
            by_path.setdefault(f"__before__{e['path']}", before)
        if e["old"] not in before:
            return None
        by_path[e["path"]] = before.replace(e["old"], e["new"], 1)
    test_lits = _test_literals(root, failing_test)
    reasons = []
    for path, after in by_path.items():
        if path.startswith("__before__"):
            continue
        try:
            t_before = ast.parse(by_path[f"__before__{path}"])
            t_after = ast.parse(after)
        except SyntaxError:
            continue  # a syntax error fails the tests; nothing to game
        added = _features(t_after) - _features(t_before)
        for (kind, what), _n in sorted(added.items(), key=str):
            if kind == "dunder":
                reasons.append(f"adds {what} in {path}")
            elif kind == "machinery":
                reasons.append(f"adds a reference to {what} in {path}")
            elif kind == "swallow":
                reasons.append(f"adds a broad except that swallows errors in {path}")
            elif kind == "literal" and what in test_lits:
                reasons.append(f"copies the test's literal {what[:40]} into {path}")
    if not reasons:
        return None
    return "edit could pass the tests without fixing the code: " + "; ".join(reasons[:4])
