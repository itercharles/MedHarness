"""dhfkit stores and retrieves. medharness analyses.

A change-controlled organisation may already keep its DHF in Jira, Azure DevOps
or a system of its own, and those manage a single item well. What none of them
do is take the items together and ask whether the V-model holds. That analysis
is what this project is for, so it cannot live inside one storage
implementation — `dhfkit` is one backend among possible others, and an
organisation swapping it must keep the analysis.

The line is what a store already answers on its own: item well-formed, IDs
unique, links resolving. Coverage between layers, cycles, risk impact and
required-link rules all need the set, and all belong to medharness.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DHFKIT = ROOT / "dhfkit"

#: Names that mean analysis over the item set rather than storage of one item.
#: Matched on word boundaries: "cycle" as a substring also hits "lifecycle",
#: which is the state machine of a single item and squarely storage.
ANALYSIS = ("coverage", "orphan", "cycles", "link_cycle", "risk_chain",
            "affected_risk", "module_map", "required_traceability",
            "traceability_report", "check_traceability")

#: `find_dangling_links` is referential integrity: does this link name something
#: that exists. A store answers that, and a Jira link cannot dangle at all.
ALLOWED = {"find_dangling_links"}


def _dhfkit_functions() -> list[tuple[str, str]]:
    found = []
    for path in sorted(DHFKIT.rglob("*.py")):
        if "tests" in path.parts or "templates" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append((str(path.relative_to(ROOT)), node.name))
    return found


FUNCTIONS = _dhfkit_functions()


def test_the_scan_found_functions() -> None:
    assert len(FUNCTIONS) > 50, f"only {len(FUNCTIONS)} — the scan is broken"


@pytest.mark.parametrize("where,name", FUNCTIONS, ids=[f"{n}" for _w, n in FUNCTIONS])
def test_no_analysis_function_lives_in_storage(where: str, name: str) -> None:
    if name in ALLOWED:
        return
    lowered = name.lower()
    hit = next((a for a in ANALYSIS if a in lowered and "lifecycle" not in lowered), None)
    assert hit is None, (
        f"{where}::{name} looks like analysis ({hit!r}) and dhfkit stores.\n"
        f"Analysis over the item set belongs in medharness.services.traceability, "
        f"which takes items as data so it works against any adapter."
    )


class TestTheAnalysisTakesDataNotStorage:
    """It must not reach for a path or a loader, or it is coupled again."""

    def _module(self) -> ast.Module:
        return ast.parse(
            (ROOT / "medharness" / "services" / "traceability.py").read_text(encoding="utf-8")
        )

    def test_it_does_not_import_the_local_adapter(self) -> None:
        for node in ast.walk(self._module()):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "local_adapter" not in node.module, (
                    "the analysis imported one storage backend — it takes items "
                    "as data so any adapter works"
                )

    def test_it_does_no_file_access(self) -> None:
        ops = {"read_text", "write_text", "open", "rglob", "glob", "iterdir"}
        for node in ast.walk(self._module()):
            if isinstance(node, ast.Attribute) and node.attr in ops:
                pytest.fail(f"the analysis reads the filesystem: .{node.attr}()")


class TestTheStorageProtocolDoesNotDemandAnalysis:
    """What medharness asks of a backend must be storage only.

    `validate_traceability` used to sit in this protocol, so every backend — a
    Jira adapter included — had to implement the V-model analysis to satisfy it.
    """

    def test_the_protocol_has_no_analysis_method(self) -> None:
        protocol = (ROOT / "medharness" / "adapters" / "protocol.py").read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(protocol)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lowered = node.name.lower()
                hit = next((a for a in ANALYSIS
                            if a in lowered and "lifecycle" not in lowered), None)
                assert hit is None, (
                    f"the adapter protocol requires {node.name!r} — a backend "
                    f"would have to implement analysis to be a store"
                )
