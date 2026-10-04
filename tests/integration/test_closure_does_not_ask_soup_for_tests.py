"""A CR that changed a SOUP item is not asked for test evidence.

`verify completion` chose the types to check by "declares a `verification_method`", which
includes SOUP (a third-party software record), while `verify tests` and `build plan` check
requirements. A CR whose `build soup` updated a dependency failed to close with
"SOUP-001: no verification_method declared".
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


def _closure(tmp_path: Path, affected: list[str]):
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Closure")
    dhf = tmp_path / "DHF"
    path = next((dhf / "items").rglob("CR-001.yaml"))
    data = yaml.safe_load(path.read_text())
    data.update(affected_items=affected, implementation_notes="Done.", affected_risk_items=[],
                triage_result={"verdict": "approved", "complexity": "small"})
    path.write_text(yaml.safe_dump(data))
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "completion", "--cr", "CR-001"])
    return result, json.loads(result.stdout.splitlines()[0])


def test_a_changed_soup_item_needs_no_verification_method(tmp_path: Path) -> None:
    result, answer = _closure(tmp_path, ["SOUP-001"])
    assert result.exit_code == 0, answer["errors"]
    assert not any("SOUP-001" in e for e in answer["errors"])


def test_a_changed_requirement_still_does(tmp_path: Path) -> None:
    """The requirement types keep their check: the starter SRS-001 declares no method."""
    result, answer = _closure(tmp_path, ["SRS-001"])
    assert result.exit_code == 1
    assert any("SRS-001" in e and "verification_method" in e for e in answer["errors"])
