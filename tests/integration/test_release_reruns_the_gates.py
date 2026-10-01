"""`build release` ships only what the gates still pass.

`completed` is a status anyone can write. A CR edited to it by hand shipped in a
release that `verify completion --cr` failed with four errors, and the release's
traceability report followed only the first configured matrix, so the chain from
risk to control was missing from its own evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from fixtures.starter import keep_the_starter_text
from medharness.cli import main
from medharness.results import ReleaseReport
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


def _project(tmp_path: Path, **cr_fields) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Rel")
    dhf = tmp_path / "DHF"
    keep_the_starter_text(dhf)
    cr = next((dhf / "items").rglob("CR-001.yaml"))
    data = yaml.safe_load(cr.read_text())
    data.update({"status": "completed", **cr_fields})
    cr.write_text(yaml.safe_dump(data))
    return dhf


CLOSED = {"implementation_notes": "n", "affected_risk_items": [], "triage_result": {"verdict": "approved"}}


def _release(dhf: Path, *extra: str):
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "release", "--version", "1.0.0",
                                       "--out-dir", str(dhf.parent / "rel"), *extra])
    return result, ReleaseReport.model_validate_json(result.stdout.splitlines()[0])


def _junit(tmp_path: Path, links: str, failed: bool = False) -> Path:
    body = "<failure message='x'/>" if failed else ""
    path = tmp_path / "r.xml"
    path.write_text(
        f'<testsuite><testcase name="t" classname="c"><properties>'
        f'<property name="medharness.links" value="{links}"/></properties>{body}</testcase></testsuite>')
    return path


def test_a_cr_edited_to_completed_by_hand_blocks_the_release(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    result, report = _release(dhf, "--write")
    assert result.exit_code == 1 and report.outcome == "completed_with_errors"
    assert any(e.startswith("CR-001:") for e in report.errors), report.errors
    assert report.rel_uid is None
    assert not list((dhf / "items").rglob("REL-002.yaml")), "a REL was recorded for a failed release"


def test_a_properly_closed_cr_releases(tmp_path: Path) -> None:
    result, report = _release(_project(tmp_path, **CLOSED, affected_items=[]))
    assert result.exit_code == 0, report.errors
    assert report.cr_ids == ["CR-001"]


def test_test_evidence_is_checked_when_given_and_flagged_when_not(tmp_path: Path) -> None:
    dhf = _project(tmp_path, **CLOSED, affected_items=["SRS-001"])
    srs = next((dhf / "items").rglob("SRS-001.yaml"))
    data = yaml.safe_load(srs.read_text())
    data["verification_method"] = ["Test"]
    srs.write_text(yaml.safe_dump(data))

    _, without = _release(dhf)
    assert any("test evidence not checked" in w for w in without.warnings), without.warnings

    result, failing = _release(dhf, "--junit", str(_junit(tmp_path, "CRS-001")))
    assert result.exit_code == 1 and any("SRS-001" in e for e in failing.errors), failing.errors

    result, passing = _release(dhf, "--junit", str(_junit(tmp_path, "SRS-001")))
    assert result.exit_code == 0, passing.errors


def test_every_configured_matrix_gets_a_traceability_report(tmp_path: Path) -> None:
    _, report = _release(_project(tmp_path, **CLOSED, affected_items=[]))
    reports = [a for a in report.artifacts if a.startswith("traceability/") and a.endswith(".json")]
    assert "traceability/Requirements_Traceability_Report.json" in reports
    assert any("System_Requirements_to_System_Architecture" in a for a in reports), reports
