"""`build plan` records its analysis on the CR, so the CR type has to declare where.

A project that edits `cr.yaml` and drops one of those fields used to meet an obscure schema refusal
mid-run, or a gate that silently found nothing. `verify dhf` and the AI stages now name the field.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf
from fixtures.starter import keep_the_starter_text

SHIPPED = Path(__file__).resolve().parents[2] / "dhfkit" / "templates" / "config" / "doc_types" / "cr.yaml"


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Fields")
    keep_the_starter_text(tmp_path / "DHF")
    return tmp_path / "DHF"


def _drop(dhf: Path, *names: str) -> None:
    data = yaml.safe_load(SHIPPED.read_text())
    data["properties"] = [p for p in data["properties"] if not (isinstance(p, dict) and p["name"] in names)]
    path = dhf / "config" / "doc_types" / "cr.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data))


def _run(dhf: Path, *args: str):
    return CliRunner().invoke(main, ["--dhf", str(dhf), *args])


def test_the_shipped_cr_type_declares_every_field(dhf: Path) -> None:
    result = _run(dhf, "verify", "dhf")
    assert result.exit_code == 0, result.stderr
    assert not [e for e in json.loads(result.stdout.splitlines()[0])["errors"] if "does not declare" in e]


@pytest.mark.dhf_links("SRS-041")
@pytest.mark.dhf_testing("T2")
def test_verify_dhf_names_the_missing_fields(dhf: Path) -> None:
    _drop(dhf, "impact_analysis", "triage_result")
    result = _run(dhf, "verify", "dhf")
    errors = json.loads(result.stdout.splitlines()[0])["errors"]
    assert result.exit_code == 1
    assert any("CR does not declare triage_result, impact_analysis" in e for e in errors), errors


@pytest.mark.parametrize("stage", ["plan", "code"])
def test_the_stages_refuse_before_any_model_runs(dhf: Path, stage: str) -> None:
    _drop(dhf, "implementation_notes")
    result = _run(dhf, "build", stage, "--cr", "CR-001", "--prompt")
    assert result.exit_code == 1
    assert "does not declare implementation_notes" in result.stderr and "cr.yaml" in result.stderr
