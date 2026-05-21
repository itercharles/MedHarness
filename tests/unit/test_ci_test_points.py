"""Integration tests for ci_test_points_gate and the `ci test-points` CLI command."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.services.ci import ci_test_points_gate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dhf(tmp_path: Path, items: list[dict]) -> Path:
    """Bootstrap a minimal DHF with the given items and return its path."""
    from dhfkit.cli import main as dhfkit_main

    dhf = tmp_path / "DHF"
    CliRunner().invoke(dhfkit_main, ["--dhf", str(dhf), "init"])
    items_dir = dhf / "items" / "03_srs"
    for item in items:
        fname = f"{item['id']}.yaml"
        lines = [f"id: {item['id']}", f"title: {item.get('title', 'Test item')}", "status: draft"]
        if "testing" in item:
            # Write as a literal block scalar so newlines are preserved
            lines.append("testing: |")
            for point_line in item["testing"].splitlines():
                lines.append(f"  {point_line}")
        (items_dir / fname).write_text("\n".join(lines) + "\n")
    return dhf


def _make_junit(
    tmp_path: Path,
    testcases: list[dict],
    filename: str = "results.xml",
) -> Path:
    """Build a minimal JUnit XML file.

    Each entry in *testcases* is a dict with:
      - ``name``     : test name (str)
      - ``links``    : comma-separated requirement IDs (str, optional)
      - ``testing``  : comma-separated test-point IDs like "T1,T2" (str, optional)
      - ``fail``     : bool, default False
    """
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


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


def test_all_points_covered_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "title": "Req with points", "testing": "T1: Point one.\nT2: Point two."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_T1_T2", "links": "SRS-001", "testing": "T1,T2"},
    ])
    result = ci_test_points_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is True
    assert len(result["results"]) == 1
    row = result["results"][0]
    assert row["req_id"] == "SRS-001"
    assert row["covered"] == 2
    assert row["total"] == 2
    assert row["uncovered"] == []
    assert row["passed"] is True


def test_partial_coverage_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "title": "Req", "testing": "T1: One.\nT2: Two.\nT3: Three."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_covers_T1_T2", "links": "SRS-001", "testing": "T1,T2"},
    ])
    result = ci_test_points_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is False
    row = result["results"][0]
    assert row["covered"] == 2
    assert row["total"] == 3
    assert row["uncovered"] == ["T3"]
    assert row["passed"] is False


def test_no_coverage_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: Must pass.\nT2: Also must pass."},
    ])
    junit = _make_junit(tmp_path, [])
    result = ci_test_points_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is False
    row = result["results"][0]
    assert row["uncovered"] == ["T1", "T2"]


def test_failing_tests_do_not_count_as_coverage(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: Point."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_fail", "links": "SRS-001", "testing": "T1", "fail": True},
    ])
    result = ci_test_points_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is False
    assert "T1" in result["results"][0]["uncovered"]


def test_items_without_testing_field_are_skipped(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "title": "No points"},
        {"id": "SRS-002", "title": "Has points", "testing": "T1: A point."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_covers", "links": "SRS-002", "testing": "T1"},
    ])
    result = ci_test_points_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is True
    req_ids = [r["req_id"] for r in result["results"]]
    assert "SRS-001" not in req_ids
    assert "SRS-002" in req_ids


def test_multiple_tests_cover_different_points(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: One.\nT2: Two."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_T1", "links": "SRS-001", "testing": "T1"},
        {"name": "test_T2", "links": "SRS-001", "testing": "T2"},
    ])
    result = ci_test_points_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is True


def test_js_style_test_name_tags_are_parsed(tmp_path: Path) -> None:
    """Test names with @links:SRS-001 and @testing:T1 are parsed for JS-style tests."""
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: A point."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "covers @links:SRS-001 @testing:T1 scenario"},
    ])
    result = ci_test_points_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is True
    assert result["results"][0]["uncovered"] == []


def test_no_junit_files_returns_error(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [])
    result = ci_test_points_gate(dhf_path=dhf, junit_paths=[])
    assert result["passed"] is False
    assert "error" in result


def test_multiple_requirements(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: One."},
        {"id": "SRS-002", "testing": "T1: First.\nT2: Second."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_srs001", "links": "SRS-001", "testing": "T1"},
        {"name": "test_srs002_T1", "links": "SRS-002", "testing": "T1"},
        # T2 of SRS-002 is not covered
    ])
    result = ci_test_points_gate(dhf_path=dhf, junit_paths=[junit])
    assert result["passed"] is False
    srs001 = next(r for r in result["results"] if r["req_id"] == "SRS-001")
    srs002 = next(r for r in result["results"] if r["req_id"] == "SRS-002")
    assert srs001["passed"] is True
    assert srs002["passed"] is False
    assert srs002["uncovered"] == ["T2"]


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


def test_cli_test_points_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: A point."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_covers", "links": "SRS-001", "testing": "T1"},
    ])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "ci", "test-points",
         "--dhf", str(dhf), "--junit", str(junit)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[0])
    assert payload["passed"] is True


def test_cli_test_points_fails_on_gap(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: One.\nT2: Two."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_only_T1", "links": "SRS-001", "testing": "T1"},
    ])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "ci", "test-points",
         "--dhf", str(dhf), "--junit", str(junit)],
    )
    assert result.exit_code != 0


def test_cli_test_points_json_stdout(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "testing": "T1: First."},
    ])
    junit = _make_junit(tmp_path, [
        {"name": "test_it", "links": "SRS-001", "testing": "T1"},
    ])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "ci", "test-points",
         "--dhf", str(dhf), "--junit", str(junit)],
    )
    payload = json.loads(result.output.splitlines()[0])
    assert "passed" in payload
    assert "results" in payload
    row = payload["results"][0]
    assert "req_id" in row
    assert "total" in row
    assert "covered" in row
    assert "uncovered" in row
