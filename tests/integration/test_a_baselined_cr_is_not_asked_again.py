"""A completed CR that a REL lists is not asked for its closure record again.

`build release` runs `verify dhf --strict`. A project that adopted MedHarness with CRs completed
before `implementation_notes` and `affected_items` existed baselines them in a REL rather than
backfilling a record nobody wrote at the time; asking those CRs for the record on every release
would make that advice fail the release it exists for.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


def _dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Baseline")
    dhf = tmp_path / "DHF"
    cr = next((dhf / "items").rglob("CR-001.yaml"))
    data = yaml.safe_load(cr.read_text())
    for field in ("implementation_notes", "affected_items", "affected_risk_items"):
        data.pop(field, None)
    data["status"] = "completed"
    cr.write_text(yaml.safe_dump(data))
    return dhf


def _closing_findings(dhf: Path) -> list[str]:
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf", "--strict"])
    answer = json.loads(result.stdout.splitlines()[0])
    return [m for m in answer["errors"] + answer["warnings"] if "completed, but" in m]


@pytest.mark.dhf_links("SRS-002")
@pytest.mark.dhf_testing("T1")
def test_a_completed_cr_a_rel_lists_is_not_asked_for_its_closure_record(tmp_path: Path) -> None:
    dhf = _dhf(tmp_path)
    assert any("CR-001" in m for m in _closing_findings(dhf)), "the control: the unlisted CR is asked"

    rel = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "create", "--type", "REL", "--data", json.dumps({
        "title": "Baseline", "version": "baseline", "included_items": ["CR-001"], "release_notes": "Accepted as it is."})])
    assert rel.exit_code == 0, rel.output
    assert _closing_findings(dhf) == []
