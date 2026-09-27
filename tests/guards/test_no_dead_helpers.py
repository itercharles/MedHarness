"""No service or shared CLI helper may be unreachable.

`_helpers.py` was the shared-utility module, and three functions in it —
`_parse_json_object`, `_run_pytest_junit`, `_summarize_junit_file` — had zero
references anywhere across 39 lines. That module is gone; its functions now
sit with the code that uses them. This checks every such module instead of
one.

Command modules are out of scope: a Click command has no caller in the
source, and a check with false positives gets suppressed rather than fixed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULES = sorted((ROOT / "medharness" / "services").glob("*.py")) + [
    ROOT / "medharness" / "cli" / "options.py",
    ROOT / "medharness" / "cli" / "output.py",
]


def _defined() -> dict[str, Path]:
    return {
        node.name: path
        for path in MODULES
        for node in ast.parse(path.read_text(encoding="utf-8")).body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    }


def _unreferenced() -> list[str]:
    defined = _defined()
    referenced: set[str] = set()
    for path in ROOT.rglob("*.py"):
        if ".venv" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8", errors="replace"))):
            # A `def` is a FunctionDef, not a Name, so it never counts as its own reference.
            if isinstance(node, ast.Name):
                referenced.add(node.id)
            elif isinstance(node, ast.Attribute):
                referenced.add(node.attr)
            elif isinstance(node, ast.ImportFrom):
                referenced.update(alias.name for alias in node.names)
    return sorted(f"{defined[n].relative_to(ROOT)}::{n}" for n in set(defined) - referenced)


UNREFERENCED = _unreferenced()


def test_the_scan_sees_the_modules() -> None:
    """A scan that parsed nothing would make the assertion below vacuous."""
    assert len(_defined()) >= 50, f"only {len(_defined())} definitions found"


@pytest.mark.parametrize("name", UNREFERENCED, ids=UNREFERENCED or ["none"])
def test_a_helper_has_a_caller(name: str) -> None:
    pytest.fail(f"{name} is never referenced, in its own module or any other.")
