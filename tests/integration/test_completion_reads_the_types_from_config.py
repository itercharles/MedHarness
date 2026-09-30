"""`verify completion` holds every type that declares `verification_method` to it.

The list was written into the command — CRS, SRS, SYS, SOUP — so a type a project
added, such as hardware requirements, closed its change requests without anyone
asking whether the item was verified.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from medharness.cli import main
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

HWR = {
    "code": "HWR", "name": "Hardware Requirement", "prefix": "HWR-", "directory": "hwr",
    "role": "hardware_requirement",
    "properties": ["id", {"name": "title", "format": "short_text", "label": "Title"},
                   {"name": "verification_method", "format": "multiselect", "label": "Verification Method",
                    "options": ["Test", "Inspection", "Analysis", "Demonstration"]}],
}


def _project(tmp_path: Path, *, verification_method: list[str] | None) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Hw")
    dhf = tmp_path / "DHF"
    (dhf / "config" / "doc_types").mkdir(exist_ok=True)
    (dhf / "config" / "doc_types" / "hwr.yaml").write_text(yaml.safe_dump(HWR))
    (dhf / "items" / "hwr").mkdir(exist_ok=True)
    item = {"id": "HWR-001", "title": "Battery runs 8 hours"}
    if verification_method:
        item["verification_method"] = verification_method
    (dhf / "items" / "hwr" / "HWR-001.yaml").write_text(yaml.safe_dump(item))
    cr = next((dhf / "items").rglob("CR-001.yaml"))
    data = yaml.safe_load(cr.read_text())
    data.update({"implementation_notes": "n", "affected_risk_items": [],
                 "triage_result": {"verdict": "approved"}, "affected_items": ["HWR-001"]})
    cr.write_text(yaml.safe_dump(data))
    return dhf


def _completion(dhf: Path):
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "completion", "--cr", "CR-001"])
    return result, json.loads(result.stdout.splitlines()[0])


def test_an_added_type_with_no_verification_method_blocks_closure(tmp_path: Path) -> None:
    result, envelope = _completion(_project(tmp_path, verification_method=None))
    assert result.exit_code == 1 and envelope["passed"] is False
    assert any("HWR-001" in e for e in envelope["errors"]), envelope["errors"]


def test_an_added_type_with_a_declared_method_passes(tmp_path: Path) -> None:
    result, envelope = _completion(_project(tmp_path, verification_method=["Inspection"]))
    assert result.exit_code == 0, envelope
    assert envelope["passed"] is True
