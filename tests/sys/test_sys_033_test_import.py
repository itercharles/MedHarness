"""
Tests for SYS-033: External Test Result Integration

Verifies that external test results can be imported via JUnit XML and
the ResultStore CLI, and that linked requirement items are updated.

@links: SYS-033, SRS-012
"""

import json
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from click.testing import CliRunner
from cli.cli import main
from compliantflow.core import CompliantFlowCore
from test_results.junit_parser import parse_junit_xml, ExecutionResult


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
    config_path = test_dhf_root / "config" / "project_config.yaml"
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    for dt in cfg["doc_types"]:
        if dt["code"] == "SYS":
            dt["has_verification"] = True
            break
    with open(config_path, "w") as f:
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
    @links: SYS-033
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
    TC-SYS-033-002: import_test_results with all-PASS results sets
    the linked SYS item's verification_status to 'verified'.

    @test_id: TC-SYS-033-002
    @links: SYS-033
    """
    _enable_verification(test_dhf_root)
    core = CompliantFlowCore(test_dhf_root, auto_commit=False)

    # Register TC definition
    core.register_test_cases([{"id": "TC-SYS-001", "title": "Object creation", "links": ["SYS-001"]}])

    # Import PASS result
    results = [ExecutionResult(id="TC-SYS-001", testing_status="PASS", name="test_TC_SYS_001", links=[])]
    summary = core.import_test_results(results, tester="CI")

    assert summary["imported"] == 1
    assert "SYS-001" in summary["items_updated"]

    sys_item = core.get_item("SYS-001")
    assert sys_item["verification_status"] == "verified"


# ---------------------------------------------------------------------------
# TC-SYS-033-003: FAIL import → requirement marked failed
# ---------------------------------------------------------------------------

def test_TC_SYS_033_003_fail_import_marks_item_failed(test_dhf_root):
    """
    TC-SYS-033-003: import_test_results with a FAIL result sets
    the linked SYS item's verification_status to 'failed'.

    @test_id: TC-SYS-033-003
    @links: SYS-033
    """
    _enable_verification(test_dhf_root)
    core = CompliantFlowCore(test_dhf_root, auto_commit=False)

    core.register_test_cases([{"id": "TC-SYS-999", "title": "Failing test", "links": ["SYS-001"]}])
    results = [ExecutionResult(id="TC-SYS-999", testing_status="FAIL", name="test_TC_SYS_999",
                               links=[], error_message="AssertionError")]
    summary = core.import_test_results(results, tester="CI")

    assert summary["imported"] == 1
    assert "SYS-001" in summary["items_updated"]

    sys_item = core.get_item("SYS-001")
    assert sys_item["verification_status"] == "failed"
    assert "TC-SYS-999" in summary["failed_tcs"]


# ---------------------------------------------------------------------------
# TC-SYS-033-004: Tests with no TC metadata are silently skipped
# ---------------------------------------------------------------------------

def test_TC_SYS_033_004_non_tc_tests_skipped(test_dhf_root):
    """
    TC-SYS-033-004: parse_junit_xml silently ignores testcases that have
    no recognisable TC ID in name or properties.

    @test_id: TC-SYS-033-004
    @links: SYS-033
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
# TC-SYS-033-005: register_test_cases persists definition fields
# ---------------------------------------------------------------------------

def test_TC_SYS_033_005_register_persists_definition(test_dhf_root):
    """
    TC-SYS-033-005: register_test_cases stores reviewer/review_date/review_status.

    @test_id: TC-SYS-033-005
    @links: SYS-033
    """
    core = CompliantFlowCore(test_dhf_root, auto_commit=False)
    summary = core.register_test_cases([{
        "id": "TC-SYS-042",
        "title": "Design review test",
        "links": ["SYS-001"],
        "reviewer": "Alice",
        "review_date": "2026-01-15",
        "review_status": "approved",
    }])
    assert summary["registered"] == 1
    assert summary["errors"] == []

    record = core.get_test_result("TC-SYS-042")
    assert record is not None
    assert record["reviewer"] == "Alice"
    assert record["review_status"] == "approved"
    assert record["links"] == ["SYS-001"]


# ---------------------------------------------------------------------------
# TC-SYS-033-006: CLI test register --from-file exits 0
# ---------------------------------------------------------------------------

def test_TC_SYS_033_006_cli_register_from_file(runner, test_dhf_root, dhf_str, tmp_path):
    """
    TC-SYS-033-006: `test register --from-file` exits 0 and writes records.

    @test_id: TC-SYS-033-006
    @links: SYS-033
    """
    tc_file = tmp_path / "test_cases.yaml"
    tc_file.write_text(textwrap.dedent("""\
        - id: TC-SYS-010
          title: Register via CLI
          links: [SYS-001]
          reviewer: Bob
          review_status: approved
    """))

    result = runner.invoke(main, ["--dhf", dhf_str, "test", "register",
                                  "--from-file", str(tc_file)])
    assert result.exit_code == 0, result.output + str(result.exception or "")

    core = CompliantFlowCore(test_dhf_root, auto_commit=False)
    record = core.get_test_result("TC-SYS-010")
    assert record is not None
    assert record["reviewer"] == "Bob"


# ---------------------------------------------------------------------------
# TC-SYS-033-007: CLI test import exits 0, JSON summary has provenance
# ---------------------------------------------------------------------------

def test_TC_SYS_033_007_cli_test_import(runner, test_dhf_root, dhf_str):
    """
    TC-SYS-033-007: `test import` exits 0 and stdout contains JSON summary
    with run_id in the stored records.

    @test_id: TC-SYS-033-007
    @links: SYS-033
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

    core = CompliantFlowCore(test_dhf_root, auto_commit=False)
    record = core.get_test_result("TC-SYS-001")
    assert record is not None
    assert record.get("run_id") == "7890123"
    assert record.get("commit_sha") == "abc123def"


# ---------------------------------------------------------------------------
# TC-SYS-033-008: CLI test list --status PASS filters correctly
# ---------------------------------------------------------------------------

def test_TC_SYS_033_008_cli_test_list_filter(runner, test_dhf_root, dhf_str):
    """
    TC-SYS-033-008: `test list --status PASS` returns only PASS records.

    @test_id: TC-SYS-033-008
    @links: SYS-033
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
