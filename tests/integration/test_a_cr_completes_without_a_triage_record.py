"""A CR completes on the record its stages write; no approved `triage_result` is needed.

The triage verdict was a field the model wrote about its own work, and the gates read it back as
approval. A rejected CR still carries one; an accepted CR does not, and its transitions do not ask.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from fixtures.starter import keep_the_starter_text

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf

RECORD = {"implementation_notes": "Scale the dose.", "affected_risk_items": [], "affected_items": []}


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Triage")
    keep_the_starter_text(tmp_path / "DHF")
    return tmp_path / "DHF"


def _run(dhf: Path, *args: str):
    return CliRunner().invoke(main, ["--dhf", str(dhf), *args])


def _cr(dhf: Path) -> dict:
    return json.loads(_run(dhf, "item", "get", "CR-001").stdout)


def test_a_cr_with_no_triage_result_goes_design_to_completed(dhf: Path) -> None:
    assert _run(dhf, "item", "transition", "CR-001", "design").exit_code == 0
    assert _run(dhf, "item", "update", "CR-001", "--data", json.dumps(RECORD)).exit_code == 0

    develop = _run(dhf, "item", "transition", "CR-001", "develop")
    assert develop.exit_code == 0, develop.stderr
    completed = _run(dhf, "item", "transition", "CR-001", "completed")
    assert completed.exit_code == 0, completed.stderr

    cr = _cr(dhf)
    assert cr["status"] == "completed"
    assert "triage_result" not in cr


def test_the_design_still_has_to_be_recorded_before_develop(dhf: Path) -> None:
    assert _run(dhf, "item", "transition", "CR-001", "design").exit_code == 0
    result = _run(dhf, "item", "transition", "CR-001", "develop")
    assert result.exit_code != 0
    assert _cr(dhf)["status"] == "design"
