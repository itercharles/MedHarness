"""Nothing in `_helpers.py` may be unreachable.

It is the shared-utility module, so anything landing there without a caller
stays: three functions — `_parse_json_object`, `_run_pytest_junit`,
`_summarize_junit_file` — had zero references anywhere, including inside the
file itself, across 39 lines.

Scoped to this one module deliberately. A blanket dead-code rule across the
repo would flag Click commands, pytest hooks and `dhfkit.api`'s public surface,
and a check with false positives gets suppressed rather than fixed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPERS = ROOT / "medharness" / "_helpers.py"


def _unreferenced() -> list[str]:
    source = HELPERS.read_text(encoding="utf-8")
    defined = {
        node.name
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef)
    }

    referenced: set[str] = set()
    for path in ROOT.rglob("*.py"):
        if ".venv" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            name = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in defined:
                        referenced.add(alias.name)
            if name in defined:
                # A function's own `def` is not a reference to it.
                if path == HELPERS and isinstance(node, ast.Name):
                    referenced.add(name)
                elif path != HELPERS:
                    referenced.add(name)
                else:
                    referenced.add(name)
    return sorted(defined - referenced)


UNREFERENCED = _unreferenced()


def test_the_scan_sees_the_module() -> None:
    """A scan that parsed nothing would make the assertion below vacuous."""
    defined = [
        n.name for n in ast.parse(HELPERS.read_text(encoding="utf-8")).body
        if isinstance(n, ast.FunctionDef)
    ]
    assert len(defined) > 10, f"only {len(defined)} helpers found"


@pytest.mark.parametrize("name", UNREFERENCED, ids=UNREFERENCED or ["none"])
def test_a_helper_has_a_caller(name: str) -> None:
    pytest.fail(
        f"medharness/_helpers.py::{name} is never referenced, in this file or "
        f"any other. A shared-utility module is where unreachable code goes to "
        f"stay."
    )
