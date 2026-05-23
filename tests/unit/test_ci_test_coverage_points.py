"""Tests for requirement coverage with optional numbered test-point enforcement."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from click.testing import CliRunner

from medharness.cli import main
from medharness.services.ci import ci_test_coverage_gate


def _make_dhf(tmp_path: Path, items: list[dict]) -> Path:
    from dhfkit.cli import main as dhfkit_main

    dhf = tmp_path / "DHF"
    CliRunner().invoke(dhfkit_main, ["--dhf", str(dhf), "init"])
    items_dir = dhf / "items" / "03_srs"
    for item in items:
        lines = [f"id: {item['id']}", f"title: {item.get('title', 'Test item')}", "status: draft"]
        if "testing" in item:
            lines.append("testing: |")
            for point_line in item["testing"].splitlines():
                lines.append(f"  {point_line}")
        (items_dir / f"{item['id']}.yaml").write_text("\n".join(lines) + "\n")
    return dhf


def _make_junit(tmp_path: Path, testcases: list[dict], filename: str = "results.xml") -> Path:
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name="suite", tests=str(len(testcases)))
    for tc_data in testcases:
        tc = ET.SubElement(suite, "testcase", name=tc_data.get("name", "test"), classname="Tests")
        links = tc_data.get("links", "")
        testing = tc_data.get("testing", "")
        if links or testing:
            props = ET.SubElement(tc, "properties")
            if links:
                ET.SubElement(props, "property", name="medharness.links", value=links)
            if testing:
                ET.SubElement(props, "property", name="medharness.testing", value=testing)
        if tc_data.get("fail"):
            ET.SubElement(tc, "failure", message="test failed")
    path = tmp_path / filename
    ET.ElementTree(root).write(str(path))
    return path


def test_requirement_without_test_points_only_needs_linked_test(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "title": "Req"}])
    junit = _make_junit(tmp_path, [{"name": "test_req", "links": "SRS-001"}])
    result = ci_test_coverage_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is True
    assert result["results"][0]["covered"] == 1
    assert result["testing_points"] == []


def test_requirement_with_test_points_must_cover_all_points(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: One.\nT2: Two.\nT3: Three."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_req", "links": "SRS-001", "testing": "T1,T2"},
    ])
    result = ci_test_coverage_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is False
    assert result["results"][0]["covered"] == 1
    assert result["results"][0]["uncovered"] == []
    assert result["testing_points"] == [{
        "req_id": "SRS-001",
        "total": 3,
        "covered": 2,
        "uncovered": ["T3"],
        "passed": False,
    }]


def test_requirement_with_test_points_and_no_linked_test_still_fails_requirement_coverage(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: Must pass."},
    ])
    junit = _make_junit(tmp_path, [{"name": "test_other", "links": "SRS-999", "testing": "T1"}])
    result = ci_test_coverage_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is False
    assert result["results"][0]["uncovered"] == ["SRS-001"]
    assert result["testing_points"][0]["uncovered"] == ["T1"]


def test_failing_tests_do_not_count_for_requirement_or_point_coverage(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: Point."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_fail", "links": "SRS-001", "testing": "T1", "fail": True},
    ])
    result = ci_test_coverage_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is False
    assert result["results"][0]["uncovered"] == ["SRS-001"]
    assert result["testing_points"][0]["uncovered"] == ["T1"]


def test_js_style_tags_count_for_requirement_and_point_coverage(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: A point."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "covers @links:SRS-001 @testing:T1 scenario"},
    ])
    result = ci_test_coverage_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is True
    assert result["results"][0]["covered"] == 1
    assert result["testing_points"][0]["uncovered"] == []


def test_unknown_req_type_produces_warning_entry(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [])
    junit = _make_junit(tmp_path, [])
    result = ci_test_coverage_gate(dhf_path=dhf, junit_paths=[junit], req_types=("TYPO",))
    warning_rows = [r for r in result["results"] if r.get("warning")]
    assert len(warning_rows) == 1
    assert warning_rows[0]["type"] == "TYPO"
    assert warning_rows[0]["passed"] is True


def test_cli_test_coverage_reports_point_gaps_in_json(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: One.\nT2: Two."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_only_T1", "links": "SRS-001", "testing": "T1"},
    ])
    result = CliRunner().invoke(
        main,
        ["verify", "tests", "--dhf", str(dhf), "--junit", str(junit)],
    )
    assert result.exit_code != 0
    payload = json.loads(result.output.splitlines()[0])
    assert payload["passed"] is False
    assert payload["testing_points"][0]["uncovered"] == ["T2"]
