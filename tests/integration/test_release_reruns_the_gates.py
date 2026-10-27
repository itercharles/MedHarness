"""`build release` ships only what the gates still pass.

`completed` is a status anyone can write. A CR edited to it by hand shipped in a
release that `verify completion --cr` failed with four errors, and the release's
traceability report followed only the first configured matrix, so the chain from
risk to control was missing from its own evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from medharness.validation.project import keep_the_starter_text, verify_the_starter
from medharness.cli import main
from medharness.results import ReleaseReport
from medharness.scaffold import replace_placeholders, scaffold_dhf


def _project(tmp_path: Path, **cr_fields) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Rel")
    dhf = tmp_path / "DHF"
    keep_the_starter_text(dhf)
    cr = next((dhf / "items").rglob("CR-001.yaml"))
    data = yaml.safe_load(cr.read_text())
    data.update({"status": "completed", **cr_fields})
    cr.write_text(yaml.safe_dump(data))
    return dhf


CLOSED = {"implementation_notes": "n", "affected_risk_items": []}


def _release(dhf: Path, *extra: str, junit: Path | None = None):
    junit = junit or verify_the_starter(dhf, dhf.parent / "test-results")
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "release", "--version", "1.0.0",
                                       "--out-dir", str(dhf.parent / "rel"), "--junit", str(junit), *extra])
    return result, ReleaseReport.model_validate_json(result.stdout.splitlines()[0])


def _junit(tmp_path: Path, links: str, failed: bool = False) -> Path:
    body = "<failure message='x'/>" if failed else ""
    path = tmp_path / "r.xml"
    path.write_text(
        f'<testsuite><testcase name="t" classname="c"><properties>'
        f'<property name="medharness.links" value="{links}"/></properties>{body}</testcase></testsuite>')
    return path


@pytest.mark.dhf_links("SRS-044")
@pytest.mark.dhf_testing("T3")
def test_a_cr_edited_to_completed_by_hand_blocks_the_release(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    result, report = _release(dhf, "--write")
    assert result.exit_code == 1 and report.outcome == "completed_with_errors"
    assert any(e.startswith("CR-001:") for e in report.errors), report.errors
    assert report.rel_uid is None
    assert not list((dhf / "items").rglob("REL-002.yaml")), "a REL was recorded for a failed release"


@pytest.mark.dhf_links("SRS-044")
@pytest.mark.dhf_testing("T3")
def test_a_properly_closed_cr_releases(tmp_path: Path) -> None:
    result, report = _release(_project(tmp_path, **CLOSED, affected_items=[]))
    assert result.exit_code == 0, report.errors
    assert report.cr_ids == ["CR-001"]


@pytest.mark.dhf_links("SRS-046")
@pytest.mark.dhf_testing("T1", "T2")
def test_every_requirement_must_be_verified_by_the_junit_given(tmp_path: Path) -> None:
    """Not only those the included CRs touched: a release with no CR shipped on no evidence."""
    dhf = _project(tmp_path, **CLOSED, affected_items=["SRS-001"])
    verify_the_starter(dhf, tmp_path / "unused")

    result, failing = _release(dhf, junit=_junit(tmp_path, "CRS-001,SYS-001"))
    assert result.exit_code == 1 and any(e.startswith("Tests:") and "SRS" in e for e in failing.errors), failing.errors

    result, passing = _release(dhf, junit=_junit(tmp_path, "CRS-001,SYS-001,SRS-001"))
    assert result.exit_code == 0, passing.errors


@pytest.mark.dhf_links("SRS-046")
@pytest.mark.dhf_testing("T3")
def test_a_release_without_junit_is_refused(tmp_path: Path) -> None:
    dhf = _project(tmp_path, **CLOSED, affected_items=[])
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "release", "--version", "1.0.0",
                                       "--out-dir", str(tmp_path / "rel")])
    assert result.exit_code == 2 and "--junit" in result.output


def test_every_configured_matrix_gets_a_traceability_report(tmp_path: Path) -> None:
    _, report = _release(_project(tmp_path, **CLOSED, affected_items=[]))
    reports = [a for a in report.artifacts if a.startswith("traceability/") and a.endswith(".json")]
    assert "traceability/Requirements_Traceability_Report.json" in reports
    assert any("System_Requirements_to_System_Architecture" in a for a in reports), reports


@pytest.mark.dhf_links("SRS-043")
@pytest.mark.dhf_testing("T3")
def test_a_coverage_gap_in_the_chain_blocks_the_release(tmp_path: Path) -> None:
    dhf = _project(tmp_path, **CLOSED, affected_items=[])
    junit = verify_the_starter(dhf, tmp_path / "unused")
    for design in (dhf / "items").rglob("SWDD-*.yaml"):
        design.unlink()     # SRS-001 now has no design: advisory for `verify dhf`, a gap in a release

    result, report = _release(dhf, "--write", junit=junit)

    assert result.exit_code == 1 and report.rel_uid is None
    assert any(e.startswith("DHF:") and "SRS->SWDD: 1 uncovered" in e for e in report.errors), report.errors


@pytest.mark.dhf_links("SRS-048")
@pytest.mark.dhf_testing("T2")
def test_a_failing_release_still_writes_the_evidence_to_the_out_dir(tmp_path: Path) -> None:
    dhf = _project(tmp_path)            # CR-001 is completed by hand and fails its closure
    result, report = _release(dhf, "--write")

    assert result.exit_code == 1 and report.rel_uid is None
    assert "evidence-summary.json" in report.artifacts, report.artifacts
    assert any(a.startswith("specifications/SRS_Specification_") for a in report.artifacts), report.artifacts
    assert (tmp_path / "rel" / "evidence-manifest.json").is_file()
    assert not (dhf / "releases").exists()
