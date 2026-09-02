"""A mock is a claim about what the real function returns.

When the claim stops being true, nothing fails: the test keeps feeding the CLI
a shape production no longer produces, the line stays green in coverage, and the
real call path breaks. That is exactly how `verify branch` shipped a TypeError
in 0.14.0 — its test mocked the service with dicts in `errors` while the service
had moved to strings.

This compares every literal mock in the suite against the shape the real
function actually returns, so a service that changes shape fails here rather
than in a user's pipeline.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"


def _own_returns(fn: ast.FunctionDef) -> list[object]:
    """Return shapes of *this* function, not of helpers defined inside it.

    Walking the whole subtree attributes a nested helper's returns to its
    parent — which made an early version of this file report a false mismatch
    for `_get_pr_feedback`, whose inner `_fetch` returns a different shape.
    """
    nested = {n for child in fn.body
              if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
              for n in ast.walk(child)}
    shapes: list[object] = []

    def record(value: ast.expr) -> None:
        if isinstance(value, ast.Dict):
            shapes.append(frozenset(k.value for k in value.keys
                                    if isinstance(k, ast.Constant)))
        elif isinstance(value, ast.Tuple):
            shapes.append(("tuple", len(value.elts)))

    for node in ast.walk(fn):
        if node in nested or not isinstance(node, ast.Return) or node.value is None:
            continue
        if isinstance(node.value, ast.Name):
            # `return out` — find the dict literal that `out` was built from.
            for assign in ast.walk(fn):
                if (isinstance(assign, ast.Assign) and assign not in nested
                        and any(getattr(t, "id", None) == node.value.id
                                for t in assign.targets)):
                    record(assign.value)
                elif (isinstance(assign, ast.AnnAssign) and assign not in nested
                      and getattr(assign.target, "id", None) == node.value.id
                      and assign.value is not None):
                    record(assign.value)
        else:
            record(node.value)
    return shapes


def _annotated_shape(fn: ast.FunctionDef) -> object | None:
    """A declared `-> tuple[...]` is the contract; prefer it over inference.

    `_run_llm` returns by delegating to two other functions, so it has no return
    literal of its own — but it is annotated `tuple[int, str, str]`.
    """
    ann = fn.returns
    if isinstance(ann, ast.Subscript) and getattr(ann.value, "id", "") == "tuple":
        elts = ann.slice.elts if isinstance(ann.slice, ast.Tuple) else [ann.slice]
        if not any(isinstance(e, ast.Constant) and e.value is Ellipsis for e in elts):
            return ("tuple", len(elts))
    return None


def _defining_module(dotted: str) -> tuple[Path, str] | None:
    """Resolve a patch target to the file that actually defines the function.

    A target may name a re-export rather than the definition — patching
    `services.cr_generation.git.collect_dhf_item_changes` reaches the function
    defined in `services/git.py`. Walking segments off the front and giving up
    silently left 18 mocks unchecked.
    """
    module, _, fname = dotted.rpartition(".")
    candidates = []
    parts = module.split(".")
    for i in range(len(parts), 0, -1):
        candidates.append(ROOT / ("/".join(parts[:i]) + ".py"))
    # A re-export names the source module as its last segment: ...cr_generation.git
    candidates.append(ROOT / "medharness" / "services" / f"{parts[-1]}.py")
    for path in candidates:
        if not path.exists():
            continue
        tree = ast.parse(path.read_text())
        if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fname
               for n in tree.body):
            return path, fname
    return None


def _real_shapes(dotted: str) -> list[object] | None:
    """Shapes returned by the service function a patch target names."""
    found = _defining_module(dotted)
    if not found:
        return None
    path, fname = found
    tree = ast.parse(path.read_text())
    fn = next(n for n in tree.body
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fname)
    annotated = _annotated_shape(fn)
    return [annotated] if annotated else _own_returns(fn)


def _mock_shape(node: ast.expr) -> object | None:
    if isinstance(node, ast.Dict) and all(isinstance(k, ast.Constant) for k in node.keys):
        return frozenset(k.value for k in node.keys)
    if isinstance(node, ast.Tuple):
        return ("tuple", len(node.elts))
    return None


def _mocks() -> list[tuple[str, object, str, int]]:
    found = []
    for f in sorted(TESTS.rglob("test_*.py")):
        for n in ast.walk(ast.parse(f.read_text())):
            if not (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "patch"):
                continue
            if not (n.args and isinstance(n.args[0], ast.Constant)):
                continue
            target = n.args[0].value
            if not target.startswith("medharness."):
                continue
            rv = next((k.value for k in n.keywords if k.arg == "return_value"), None)
            shape = _mock_shape(rv) if rv is not None else None
            if shape is not None:
                found.append((target, shape, f.name, n.lineno))
    return found


MOCKS = _mocks()


def test_the_scan_found_the_mocks() -> None:
    """A silent zero would make every assertion below vacuous."""
    assert len(MOCKS) > 30, f"only {len(MOCKS)} literal mocks found — scan is broken"


@pytest.mark.parametrize(
    "target,shape,where,line",
    MOCKS,
    ids=[f"{t.rpartition('.')[2]}@{f}:{ln}" for t, _s, f, ln in MOCKS],
)
def test_mock_matches_what_the_service_returns(
    target: str, shape: object, where: str, line: int
) -> None:
    real = _real_shapes(target)
    if not real:
        pytest.skip(f"{target}: no literal return shape to compare against")
    assert shape in real, (
        f"{where}:{line} mocks {target} as {sorted(shape) if isinstance(shape, frozenset) else shape}, "
        f"but it returns {[sorted(r) if isinstance(r, frozenset) else r for r in real]}.\n"
        f"The mock froze a shape the service no longer produces."
    )
