"""
Tests for CRS-008: CI/CD Integration and Automated Test Result Import

Verifies that external test results can be imported via JUnit XML and
the ResultStore CLI, and that linked requirement items are updated.

@links: CRS-008
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from click.testing import CliRunner
from utils.cli import main
from utils.local_adapter import LocalDHFAdapter
from compliantflow.core import CompliantFlowCore
from utils.junit_parser import parse_junit_xml


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def dhf_str(test_dhf_root):
    return str(test_dhf_root)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enable_verification(test_dhf_root: Path) -> None:
    """Add has_verification:true to the SYS doc type in the test config."""
    # Split config: each doc type has its own file under config/doc_types/
    sys_config_path = test_dhf_root / "config" / "doc_types" / "sys.yaml"
    with open(sys_config_path) as f:
        cfg = yaml.safe_load(f)
    cfg["has_verification"] = True
    with open(sys_config_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)


def _make_junit_xml(test_dhf_root: Path, testcases: list[dict]) -> Path:
    """Write a minimal JUnit XML file to DHF/test-results/tmp.xml."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<testsuites>', '  <testsuite name="suite">']
    for tc in testcases:
        name = tc["name"]
        props = tc.get("props", {})
        failure = tc.get("failure")
        skipped = tc.get("skipped", False)

        prop_block = ""
        if props:
            prop_items = "".join(
                f'\n      <property name="{k}" value="{v}"/>' for k, v in props.items()
            )
            prop_block = f"\n    <properties>{prop_items}\n    </properties>"

        if failure:
            body = f'\n    <failure message="{failure}">details</failure>'
        elif skipped:
            body = '\n    <skipped/>'
        else:
            body = ""

        lines.append(f'    <testcase name="{name}" time="0.1">{prop_block}{body}\n    </testcase>')

    lines += ['  </testsuite>', '</testsuites>']
    xml_path = test_dhf_root / "test-results" / "tmp.xml"
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text("\n".join(lines))
    return xml_path


# ---------------------------------------------------------------------------
# TC-SYS-033-001: JUnit XML parsing
# ---------------------------------------------------------------------------

def test_TC_SYS_033_001_parse_junit_xml(test_dhf_root):
    """
    TC-SYS-033-001: parse_junit_xml extracts TC IDs and statuses correctly.

    Verifies ID extraction from explicit property and from test name regex,
    plus PASS/FAIL/SKIP status detection.

    @test_id: TC-SYS-033-001
    @links: CRS-008
    """
    xml_path = _make_junit_xml(test_dhf_root, [
        {
            "name": "test_TC_SYS_001_object_creation",
        },
        {
            "name": "some_frontend_test",
            "props": {
                "compliantflow.id": "TC-CRS-001",
                "compliantflow.links": "CRS-001",
            },
            "failure": "AssertionError",
        },
        {
            "name": "test_TC_SRS_002_schema",
            "skipped": True,
        },
        {
            "name": "test_without_tc_id",  # should be skipped
        },
    ])

    results = parse_junit_xml(xml_path)
    assert len(results) == 3, f"Expected 3 traceable results, got {len(results)}: {[r.id for r in results]}"

    ids = {r.id: r for r in results}
    assert "TC-SYS-001" in ids
    assert "TC-CRS-001" in ids
    assert "TC-SRS-002" in ids

    assert ids["TC-SYS-001"].testing_status == "PASS"
    assert ids["TC-CRS-001"].testing_status == "FAIL"
    assert ids["TC-CRS-001"].links == ["CRS-001"]
    assert ids["TC-SRS-002"].testing_status == "SKIP"


# ---------------------------------------------------------------------------
# TC-SYS-033-002: All-PASS import → requirement marked verified
# ---------------------------------------------------------------------------

def test_TC_SYS_033_002_pass_import_marks_item_verified(test_dhf_root):
    """
    TC-SYS-033-002: recording a PASS result and refreshing sets
    the linked SYS item's verification_status to 'verified'.

    @test_id: TC-SYS-033-002
    @links: CRS-008
    """
    _enable_verification(test_dhf_root)
    adapter = LocalDHFAdapter(test_dhf_root)
    core = CompliantFlowCore(adapter)

    adapter.record_test_result(tc_id="TC-SYS-001", testing_status="PASS", tester="CI",
                               links=["SYS-001"])
    core.refresh()

    sys_item = core.get_item("SYS-001")
    assert sys_item["verification_status"] == "verified"


# ---------------------------------------------------------------------------
# TC-SYS-033-003: FAIL import → requirement marked failed
# ---------------------------------------------------------------------------

def test_TC_SYS_033_003_fail_import_marks_item_failed(test_dhf_root):
    """
    TC-SYS-033-003: recording a FAIL result and refreshing sets
    the linked SYS item's verification_status to 'failed'.

    @test_id: TC-SYS-033-003
    @links: CRS-008
    """
    _enable_verification(test_dhf_root)
    adapter = LocalDHFAdapter(test_dhf_root)
    core = CompliantFlowCore(adapter)

    adapter.record_test_result(tc_id="TC-SYS-999", testing_status="FAIL", tester="CI",
                               links=["SYS-001"], notes="AssertionError")
    core.refresh()

    sys_item = core.get_item("SYS-001")
    assert sys_item["verification_status"] == "failed"
    all_results = adapter.get_all_test_results()
    assert all_results["TC-SYS-999"]["testing_status"] == "FAIL"


# ---------------------------------------------------------------------------
# TC-SYS-033-004: Tests with no TC metadata are silently skipped
# ---------------------------------------------------------------------------

def test_TC_SYS_033_004_non_tc_tests_skipped(test_dhf_root):
    """
    TC-SYS-033-004: parse_junit_xml silently ignores testcases that have
    no recognisable TC ID in name or properties.

    @test_id: TC-SYS-033-004
    @links: CRS-008
    """
    xml_path = _make_junit_xml(test_dhf_root, [
        {"name": "test_without_any_tc_marker"},
        {"name": "another_random_test"},
        {"name": "test_TC_SYS_001_valid"},
    ])
    results = parse_junit_xml(xml_path)
    assert len(results) == 1
    assert results[0].id == "TC-SYS-001"


# ---------------------------------------------------------------------------
# TC-SYS-033-005: Review fields from JUnit XML properties are persisted
# ---------------------------------------------------------------------------

def test_TC_SYS_033_005_review_fields_via_import(test_dhf_root):
    """
    TC-SYS-033-005: import persists reviewer/review_date/review_status
    from compliantflow.* XML properties.

    @test_id: TC-SYS-033-005
    @links: CRS-008
    """
    xml_path = _make_junit_xml(test_dhf_root, [
        {
            "name": "test_TC_SYS_001_obj",
            "props": {
                "compliantflow.links": "SYS-001",
                "compliantflow.reviewer": "Alice",
                "compliantflow.review_date": "2026-01-15",
                "compliantflow.review_status": "approved",
            },
        },
    ])

    adapter = LocalDHFAdapter(test_dhf_root)
    core = CompliantFlowCore(adapter)
    results = parse_junit_xml(xml_path)
    for r in results:
        adapter.record_test_result(
            tc_id=r.id, testing_status=r.testing_status, tester="CI",
            links=r.links or [], reviewer=r.reviewer or "",
            review_date=r.review_date or "", review_status=r.review_status or "",
        )
    core.refresh()

    record = adapter.get_test_result("TC-SYS-001")
    assert record is not None
    assert record["reviewer"] == "Alice"
    assert record["review_date"] == "2026-01-15"
    assert record["review_status"] == "approved"
    assert record["links"] == ["SYS-001"]
    assert record["testing_status"] == "PASS"


# ---------------------------------------------------------------------------
# TC-SYS-033-006: CLI test import exits 0, JSON summary has provenance
# ---------------------------------------------------------------------------

def test_TC_SYS_033_006_cli_test_import(runner, test_dhf_root, dhf_str):
    """
    TC-SYS-033-006: `test import` exits 0 and stdout contains JSON summary
    with run_id in the stored records.

    @test_id: TC-SYS-033-006
    @links: CRS-008
    """
    xml_path = _make_junit_xml(test_dhf_root, [
        {"name": "test_TC_SYS_001_obj"},
    ])

    result = runner.invoke(main, [
        "--dhf", dhf_str, "test", "import", str(xml_path),
        "--format", "junit",
        "--tester", "GitHub Actions",
        "--run-id", "7890123",
        "--run-url", "https://example.com/runs/7890123",
        "--commit", "abc123def",
    ])
    assert result.exit_code == 0, result.output + str(result.exception or "")

    json_line = next(l for l in result.output.splitlines() if l.strip().startswith("{"))
    summary = json.loads(json_line)
    assert "imported" in summary
    assert summary["imported"] >= 1

    record = LocalDHFAdapter(test_dhf_root).get_test_result("TC-SYS-001")
    assert record is not None
    assert record.get("run_id") == "7890123"
    assert record.get("commit_sha") == "abc123def"


# ---------------------------------------------------------------------------
# TC-SYS-033-007: CLI test list --status PASS filters correctly
# ---------------------------------------------------------------------------

def test_TC_SYS_033_007_cli_test_list_filter(runner, test_dhf_root, dhf_str):
    """
    TC-SYS-033-007: `test list --status PASS` returns only PASS records.

    @test_id: TC-SYS-033-007
    @links: CRS-008
    """
    xml_path = _make_junit_xml(test_dhf_root, [
        {"name": "test_TC_SYS_001_pass"},
        {"name": "test_TC_SYS_002_fail", "failure": "AssertionError"},
    ])
    runner.invoke(main, [
        "--dhf", dhf_str, "test", "import", str(xml_path),
        "--format", "junit", "--tester", "CI",
    ])

    result = runner.invoke(main, ["--dhf", dhf_str, "test", "list", "--status", "PASS"])
    assert result.exit_code == 0, result.output

    lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(lines) >= 1
    for line in lines:
        record = json.loads(line)
        assert record.get("testing_status") == "PASS"
