"""What counts as evidence for `verify tests`: a passing test, not a failed, errored or skipped one.

The cases here complete the requirement-by-requirement set the other `verify tests` tests start:
each runs the command's own gate on a DHF of requirements and a JUnit file whose test cases have a
chosen outcome.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from dhfkit.tests.fixtures import bare_dhf
from medharness.services.verify_tests import ci_test_coverage_gate


def _dhf(tmp_path: Path, *items: dict) -> Path:
    dhf = tmp_path / "DHF"
    bare_dhf(dhf)
    directory = dhf / "items" / "03_srs"
    directory.mkdir(parents=True, exist_ok=True)
    for item in items:
        lines = [f"id: {item['id']}", "title: t", "status: draft"]
        if "methods" in item:
            lines += ["verification_method:", *[f"  - {m}" for m in item["methods"]]]
        if "testing" in item:
            lines += ["testing: |", *[f"  {line}" for line in item["testing"].splitlines()]]
        (directory / f"{item['id']}.yaml").write_text("\n".join(lines) + "\n")
    return dhf


def _junit(tmp_path: Path, *cases: tuple[str, str, str, str]) -> Path:
    """Each case is (name, links, testing points, outcome): pass, fail, error or skip."""
    suite = ET.Element("testsuite", name="s")
    for name, links, points, outcome in cases:
        case = ET.SubElement(suite, "testcase", name=name, classname="c")
        props = ET.SubElement(case, "properties")
        ET.SubElement(props, "property", name="medharness.links", value=links)
        if points:
            ET.SubElement(props, "property", name="medharness.testing", value=points)
        if outcome == "fail":
            ET.SubElement(case, "failure", message="x")
        elif outcome == "error":
            ET.SubElement(case, "error", message="x")
        elif outcome == "skip":
            ET.SubElement(case, "skipped", message="x")
    path = tmp_path / "results.xml"
    ET.ElementTree(suite).write(path)
    return path


def _gate(dhf: Path, junit: Path, **kwargs) -> dict:
    return ci_test_coverage_gate(dhf_path=dhf, junit_paths=[junit], **kwargs)


@pytest.mark.dhf_links("SRS-024")
@pytest.mark.dhf_testing("T2")
def test_an_errored_test_does_not_count_as_evidence(tmp_path: Path) -> None:
    dhf = _dhf(tmp_path, {"id": "SRS-001", "methods": ["Test"]})

    result = _gate(dhf, _junit(tmp_path, ("t", "SRS-001", "", "error")))

    assert result["passed"] is False
    assert "SRS: 0/1 requirements covered" in result["errors"]


@pytest.mark.dhf_links("SRS-024")
@pytest.mark.dhf_testing("T3")
def test_a_skipped_test_does_not_count_as_evidence(tmp_path: Path) -> None:
    dhf = _dhf(tmp_path, {"id": "SRS-001", "methods": ["Test"]})

    result = _gate(dhf, _junit(tmp_path, ("t", "SRS-001", "", "skip")))

    assert result["passed"] is False
    assert "SRS: 0/1 requirements covered" in result["errors"]
    assert "SRS-001: declares Test but no passing case is linked" in result["errors"]


@pytest.mark.dhf_links("SRS-024")
@pytest.mark.dhf_testing("T4")
def test_one_failing_test_outweighs_a_passing_one_for_the_same_requirement(tmp_path: Path) -> None:
    dhf = _dhf(tmp_path, {"id": "SRS-001", "methods": ["Test"]})

    result = _gate(dhf, _junit(tmp_path, ("ok", "SRS-001", "", "pass"), ("bad", "SRS-001", "", "fail")))

    assert result["passed"] is False
    assert "SRS: 0/1 requirements covered" in result["errors"]


@pytest.mark.dhf_links("SRS-026")
@pytest.mark.dhf_testing("T2")
def test_a_missing_method_does_not_by_itself_fail_a_requirement_a_test_covers(tmp_path: Path) -> None:
    dhf = _dhf(tmp_path, {"id": "SRS-001"})

    result = _gate(dhf, _junit(tmp_path, ("t", "SRS-001", "", "pass")))

    assert result["passed"] is True, result["errors"]
    assert any(w.startswith("SRS-001: no verification_method declared") for w in result["warnings"])


@pytest.mark.dhf_links("SRS-027")
@pytest.mark.dhf_testing("T2")
def test_a_requirement_that_declares_test_and_inspection_still_needs_a_passing_test(tmp_path: Path) -> None:
    dhf = _dhf(tmp_path, {"id": "SRS-001", "methods": ["Test", "Inspection"]})

    result = _gate(dhf, _junit(tmp_path, ("t", "SRS-001", "", "fail")))

    assert result["passed"] is False
    assert "SRS-001: declares Test but no passing case is linked" in result["errors"]


@pytest.mark.dhf_links("SRS-027")
@pytest.mark.dhf_testing("T3")
def test_an_inspection_requirement_is_not_counted_among_the_covered(tmp_path: Path) -> None:
    dhf = _dhf(tmp_path, {"id": "SRS-001", "methods": ["Test"]}, {"id": "SRS-002", "methods": ["Inspection"]})

    result = _gate(dhf, _junit(tmp_path, ("t", "SRS-001", "", "pass")))

    assert result["passed"] is True, result["errors"]
    assert result["details"]["results"] == [
        {"type": "SRS", "passed": True, "covered": 1, "total": 1, "uncovered": []},
    ]
    assert [g["id"] for g in result["details"]["manual_review_required"]] == ["SRS-002"]


@pytest.mark.dhf_links("SRS-029")
@pytest.mark.dhf_testing("T2")
def test_a_requirement_with_every_declared_point_covered_passes(tmp_path: Path) -> None:
    dhf = _dhf(tmp_path, {"id": "SRS-001", "methods": ["Test"], "testing": "T1: One.\nT2: Two."})

    result = _gate(dhf, _junit(tmp_path, ("t", "SRS-001", "T1,T2", "pass")))

    assert result["passed"] is True, result["errors"]
    assert result["details"]["testing_points"] == [
        {"req_id": "SRS-001", "total": 2, "covered": 2, "uncovered": [], "passed": True},
    ]
