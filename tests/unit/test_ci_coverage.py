"""Tests for compute_item_coverage manual-verification hints."""

from __future__ import annotations

from pathlib import Path

from medharness.services.ci import compute_item_coverage
from tests.fixtures.stub_adapter import StubDHFAdapter


def _write_junit(path: Path, *, links: list[str], status: str = "pass", test_id: str = "TC-SYS-001-001") -> None:
    failure_block = "<failure>boom</failure>" if status != "pass" else ""
    links_value = ",".join(links)
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuite tests="1" failures="{0 if status == 'pass' else 1}">
  <testcase classname="suite" name="test_case">
    <properties>
      <property name="medharness.id" value="{test_id}"/>
      <property name="medharness.links" value="{links_value}"/>
    </properties>
    {failure_block}
  </testcase>
</testsuite>
""",
        encoding="utf-8",
    )


def _adapter() -> StubDHFAdapter:
    adapter = StubDHFAdapter()
    adapter._items["CRS-001"] = {"id": "CRS-001", "type": "CRS", "title": "Customer req"}
    adapter._items["SYS-001"] = {
        "id": "SYS-001",
        "type": "SYS",
        "title": "Safety system req",
        "critical_safety": True,
        "verification_method": ["Test", "Inspection"],
        "category": "Functional",
    }
    adapter._items["SYS-002"] = {
        "id": "SYS-002",
        "type": "SYS",
        "title": "Usability system req",
        "verification_method": ["Demonstration"],
        "category": "Usability",
    }
    adapter._items["SRS-001"] = {
        "id": "SRS-001",
        "type": "SRS",
        "title": "Software req",
        "derives_from": ["SYS-001"],
    }
    return adapter


def test_compute_item_coverage_reports_linked_passes(tmp_path: Path):
    junit = tmp_path / "results.xml"
    _write_junit(junit, links=["SYS-001", "SRS-001"])
    result = compute_item_coverage([junit], _adapter())
    assert result["computed"] is True
    assert result["coverage_by_item"]["SYS-001"] == ["TC-SYS-001-001"]
    assert result["coverage_by_item"]["SRS-001"] == ["TC-SYS-001-001"]


def test_compute_item_coverage_reports_uncovered_requirements_by_type(tmp_path: Path):
    junit = tmp_path / "results.xml"
    _write_junit(junit, links=["SYS-001"])
    result = compute_item_coverage([junit], _adapter())
    assert "SYS-002" in result["uncovered_requirements"]["SYS"]
    assert "SRS-001" in result["uncovered_requirements"]["SRS"]


def test_compute_item_coverage_ignores_failing_testcases(tmp_path: Path):
    junit = tmp_path / "results.xml"
    _write_junit(junit, links=["SYS-001"], status="fail")
    result = compute_item_coverage([junit], _adapter())
    assert "SYS-001" not in result["coverage_by_item"]


def test_compute_item_coverage_emits_manual_verification_candidates(tmp_path: Path):
    junit = tmp_path / "results.xml"
    _write_junit(junit, links=["SYS-001"])
    result = compute_item_coverage([junit], _adapter())
    candidates = result["manual_verification_candidates"]
    assert candidates["SYS-001"]["reasons"] == [
        "critical_safety",
        "verification_method:Inspection",
    ]
    assert candidates["SYS-002"]["reasons"] == [
        "verification_method:Demonstration",
        "category:Usability",
    ]


def test_compute_item_coverage_emits_manual_verification_criteria(tmp_path: Path):
    junit = tmp_path / "results.xml"
    _write_junit(junit, links=["SYS-001"])
    result = compute_item_coverage([junit], _adapter())
    assert result["manual_verification_criteria"] == {
        "critical_safety": True,
        "verification_methods": ["Inspection", "Demonstration"],
        "categories": ["Usability"],
    }
