"""A registered gate must be able to fail.

`verify code` was registered with `"blocking": "always"` and IEC 62304 §5.5, and
its validator was `return []`. It printed PASS on every run, recorded an "ok"
step in the AI workflow's diagnostics, and told the code reviewer that
deterministic checks "have been verified mechanically" — none of which had
happened. A gate that cannot fail is worse than an absent one: it is evidence
of a check that never ran.
"""

from __future__ import annotations

import ast
from pathlib import Path

from medharness.services.gates import GATES

ROOT = Path(__file__).resolve().parents[2]


def _always_returns_empty(func: ast.FunctionDef) -> bool:
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    return bool(returns) and all(
        isinstance(r.value, ast.List) and not r.value.elts for r in returns
    )


def test_the_gate_list_is_not_empty() -> None:
    assert len(GATES) >= 5, f"only {len(GATES)} gates — the import is wrong"


def test_no_service_a_gate_calls_returns_an_empty_literal() -> None:
    offenders = []
    for path in sorted((ROOT / "medharness" / "services").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
                continue
            if _always_returns_empty(node):
                offenders.append(f"{path.name}::{node.name} always returns []")
    assert not offenders, (
        "these can never report a finding, so any gate built on them always "
        "passes:\n  " + "\n  ".join(offenders)
    )
