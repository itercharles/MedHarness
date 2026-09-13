"""A parameter the body never reads is a promise the function does not keep.

`approval_evidence(pr_number, stage)` never touched `stage`, so `--stage design`
and `--stage develop` returned the same verdict for two years of releases and
the docstring drifted to describe a mechanism that had been replaced.
`ci_structural_gate` took a `governance_dir` nothing passed,
`build_evidence_bundle` a `continue_on_gate_failure` the CLI honoured itself,
and `lifecycle.execute_transition` a `performed_by` that reached the store by a
different route.

None of these is caught by a type checker or by any test that calls the
function: passing an ignored argument succeeds.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

SOURCES = sorted(ROOT.glob("medharness/services/*.py")) + sorted(ROOT.glob("dhfkit/*.py"))

#: Parameters that must stay for a reason other than this function's own body.
ALLOWED: dict[str, set[str]] = {
    # Adapter methods implement medharness.adapters.protocol, which a backend
    # other than the local one does use. tests/contract/test_client_protocol.py
    # pins the signatures.
    "LocalDHFAdapter": {"*"},
}


def _unused_parameters(fn: ast.FunctionDef) -> list[str]:
    body = ast.Module(body=fn.body, type_ignores=[])
    read = {n.id for n in ast.walk(body) if isinstance(n, ast.Name)}
    read |= {n.attr for n in ast.walk(body) if isinstance(n, ast.Attribute)}
    read |= {n.arg for n in ast.walk(body) if isinstance(n, ast.keyword) and n.arg}
    params = [
        a.arg for a in (*fn.args.args, *fn.args.kwonlyargs)
        if a.arg not in ("self", "cls")
    ]
    return [p for p in params if p not in read]


def _public_functions() -> list[tuple[str, str, ast.FunctionDef]]:
    found = []
    for path in SOURCES:
        if "test" in path.name:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                found.append((path.name, node.name, node))
    return found


FUNCTIONS = _public_functions()


def test_the_scan_reads_the_services() -> None:
    assert len(FUNCTIONS) >= 40, (
        f"only {len(FUNCTIONS)} public functions found — the scan is broken, so "
        f"every assertion below passes vacuously"
    )


@pytest.mark.parametrize(
    "module,name,fn", FUNCTIONS, ids=[f"{m}::{n}" for m, n, _f in FUNCTIONS],
)
def test_every_parameter_is_read(module: str, name: str, fn: ast.FunctionDef) -> None:
    allowed = ALLOWED.get(name, set())
    unused = [p for p in _unused_parameters(fn) if "*" not in allowed and p not in allowed]
    assert not unused, (
        f"{module}::{name} accepts {unused} and never reads it. A caller passing "
        f"it gets no error and no effect — decide whether the parameter should "
        f"work or should go."
    )
