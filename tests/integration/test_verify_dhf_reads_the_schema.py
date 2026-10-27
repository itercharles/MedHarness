"""`verify dhf` fails an item that does not match its type, without --strict, and names it.

A mistyped field in a hand-edited item is the likeliest mistake a DHF user makes; the command
whose purpose is reporting it must say which item and field, not crash or pass.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from medharness.validation.project import keep_the_starter_text

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Schema")
    keep_the_starter_text(tmp_path / "DHF")
    return tmp_path / "DHF"


def _verify(dhf: Path):
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf"])
    return result, json.loads(result.stdout.splitlines()[0])


@pytest.mark.dhf_links("SRS-035")
@pytest.mark.dhf_testing("T1")
def test_an_undeclared_field_fails_naming_the_item_and_the_field(dhf: Path) -> None:
    risk = next((dhf / "items").rglob("RISK-001.yaml"))
    risk.write_text(risk.read_text() + "typo_field: oops\n")

    result, answer = _verify(dhf)

    assert result.exit_code == 1 and answer["passed"] is False
    assert any("RISK-001" in e and "typo_field" in e for e in answer["errors"]), answer["errors"]


@pytest.mark.dhf_links("SRS-035")
@pytest.mark.dhf_testing("T2")
def test_an_item_with_no_id_fails_naming_its_file(dhf: Path) -> None:
    srs = next((dhf / "items").rglob("SRS-001.yaml"))
    srs.write_text("\n".join(l for l in srs.read_text().splitlines() if not l.startswith("id:")) + "\n")

    result, answer = _verify(dhf)

    assert result.exit_code == 1 and answer["passed"] is False
    assert any("SRS-001.yaml" in e and "'id'" in e for e in answer["errors"]), answer["errors"]


@pytest.mark.dhf_links("SRS-035")
@pytest.mark.dhf_testing("T4")
def test_a_broken_item_is_a_message_not_a_traceback(dhf: Path) -> None:
    risk = next((dhf / "items").rglob("RISK-001.yaml"))
    risk.write_text(risk.read_text() + "typo_field: oops\n")

    result, _ = _verify(dhf)

    assert "Traceback" not in (result.stderr or "")
    assert "RISK-001" in result.stderr and "typo_field" in result.stderr
