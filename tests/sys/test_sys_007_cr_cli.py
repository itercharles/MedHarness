"""
Tests for SYS-007: CR CLI and cr_git_evidence policy check.

Covers:
  - `compliantflow cr check-status` for approved and non-approved CRs
  - `compliantflow cr generate-report` output structure
  - `cr_git_evidence` policy check reading from an artifact file
  - `compliantflow test import / status / list` commands

@links: SYS-006
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from compliantflow.cli import main as cf_main
from compliantflow.policy import PolicyEngine


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def dhf_str(test_dhf_root):
    return str(test_dhf_root)


# ---------------------------------------------------------------------------
# cr check-status
# ---------------------------------------------------------------------------

def test_TC_SYS_007_001_cr_check_status_approved(runner, dhf_str):
    """
    TC-SYS-007-001: `cr check-status` returns exit 0 and valid=true for an
    approved CR that has implementation_prs set.

    @test_id: TC-SYS-007-001
    @links: SYS-006
    """
    result = runner.invoke(cf_main, ["--dhf", dhf_str, "cr", "check-status", "CR-002"])
    # Parse JSON from stdout
    json_lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) >= 1, f"No JSON output: {result.output}"
    data = json.loads(json_lines[0])
    assert data["cr_id"] == "CR-002"
    assert data["found"] is True
    assert data["status"] == "approved"
    assert data["valid"] is True
    assert result.exit_code == 0, f"Expected exit 0 but got {result.exit_code}: {result.output}"


def test_TC_SYS_007_002_cr_check_status_draft_fails(runner, dhf_str):
    """
    TC-SYS-007-002: `cr check-status` returns exit 1 and valid=false for a
    draft CR (not yet approved).

    @test_id: TC-SYS-007-002
    @links: SYS-006
    """
    result = runner.invoke(cf_main, ["--dhf", dhf_str, "cr", "check-status", "CR-001"])
    json_lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) >= 1, f"No JSON output: {result.output}"
    data = json.loads(json_lines[0])
    assert data["cr_id"] == "CR-001"
    assert data["status"] == "draft"
    assert data["valid"] is False
    assert result.exit_code == 1


def test_TC_SYS_007_003_cr_check_status_not_found(runner, dhf_str):
    """
    TC-SYS-007-003: `cr check-status` returns exit 1 and found=false for a
    CR that does not exist.

    @test_id: TC-SYS-007-003
    @links: SYS-006
    """
    result = runner.invoke(cf_main, ["--dhf", dhf_str, "cr", "check-status", "CR-999"])
    json_lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) >= 1, f"No JSON output: {result.output}"
    data = json.loads(json_lines[0])
    assert data["found"] is False
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# cr generate-report
# ---------------------------------------------------------------------------

def test_TC_SYS_007_004_cr_generate_report_structure(runner, dhf_str):
    """
    TC-SYS-007-004: `cr generate-report` outputs valid JSON with cr_id and
    commits keys.

    @test_id: TC-SYS-007-004
    @links: SYS-006
    """
    result = runner.invoke(cf_main, ["--dhf", dhf_str, "cr", "generate-report", "CR-002"])
    assert result.exit_code == 0, f"Unexpected exit code: {result.output}"
    json_lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) >= 1, f"No JSON output: {result.output}"
    data = json.loads(json_lines[0])
    assert data.get("cr_id") == "CR-002"
    assert "commits" in data
    assert isinstance(data["commits"], list)


# ---------------------------------------------------------------------------
# cr_git_evidence policy check
# ---------------------------------------------------------------------------

def test_TC_SYS_007_005_cr_git_evidence_pass(test_dhf_root):
    """
    TC-SYS-007-005: cr_git_evidence returns True when the report JSON
    contains at least one commit.

    @test_id: TC-SYS-007-005
    @links: SYS-006
    """
    from compliantflow.core import CompliantFlowCore
    from utils.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(test_dhf_root, auto_commit=False)
    core = CompliantFlowCore(adapter)
    engine = PolicyEngine(core, root_dir=test_dhf_root)

    report_data = {
        "cr_id": "CR-002",
        "commits": [{"sha": "abc123", "message": "feat: implement CR-002"}],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(report_data, f)
        tmp_path = f.name

    try:
        passed, details, evidence = engine._check_cr_git_evidence(report_path=tmp_path)
    finally:
        os.unlink(tmp_path)

    assert passed is True
    assert evidence["commit_count"] == 1
    assert "CR-002" in details


def test_TC_SYS_007_006_cr_git_evidence_no_commits_fails(test_dhf_root):
    """
    TC-SYS-007-006: cr_git_evidence returns False when the report JSON
    has an empty commits list.

    @test_id: TC-SYS-007-006
    @links: SYS-006
    """
    from compliantflow.core import CompliantFlowCore
    from utils.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(test_dhf_root, auto_commit=False)
    core = CompliantFlowCore(adapter)
    engine = PolicyEngine(core, root_dir=test_dhf_root)

    report_data = {"cr_id": "CR-001", "commits": []}
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(report_data, f)
        tmp_path = f.name

    try:
        passed, details, evidence = engine._check_cr_git_evidence(report_path=tmp_path)
    finally:
        os.unlink(tmp_path)

    assert passed is False
    assert evidence["commit_count"] == 0


def test_TC_SYS_007_007_cr_git_evidence_env_var(test_dhf_root, monkeypatch):
    """
    TC-SYS-007-007: cr_git_evidence reads from COMPLIANTFLOW_CR_REPORT_PATH
    when no report_path param is provided.

    @test_id: TC-SYS-007-007
    @links: SYS-006
    """
    from compliantflow.core import CompliantFlowCore
    from utils.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(test_dhf_root, auto_commit=False)
    core = CompliantFlowCore(adapter)
    engine = PolicyEngine(core, root_dir=test_dhf_root)

    report_data = {
        "cr_id": "CR-002",
        "commits": [{"sha": "def456", "message": "fix: CR-002 follow-up"}],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(report_data, f)
        tmp_path = f.name

    try:
        monkeypatch.setenv("COMPLIANTFLOW_CR_REPORT_PATH", tmp_path)
        passed, details, evidence = engine._check_cr_git_evidence()
    finally:
        os.unlink(tmp_path)
        monkeypatch.delenv("COMPLIANTFLOW_CR_REPORT_PATH", raising=False)

    assert passed is True
    assert evidence["commit_count"] == 1


def test_TC_SYS_007_008_cr_git_evidence_no_path_fails(test_dhf_root, monkeypatch):
    """
    TC-SYS-007-008: cr_git_evidence returns False when neither report_path
    param nor env var is set.

    @test_id: TC-SYS-007-008
    @links: SYS-006
    """
    from compliantflow.core import CompliantFlowCore
    from utils.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(test_dhf_root, auto_commit=False)
    core = CompliantFlowCore(adapter)
    engine = PolicyEngine(core, root_dir=test_dhf_root)

    monkeypatch.delenv("COMPLIANTFLOW_CR_REPORT_PATH", raising=False)
    passed, details, _ = engine._check_cr_git_evidence()
    assert passed is False
    assert "not set" in details


# ---------------------------------------------------------------------------
# test import / status / list commands
# ---------------------------------------------------------------------------

def test_TC_SYS_007_009_test_import_command(runner, dhf_str, test_dhf_root):
    """
    TC-SYS-007-009: `test import` ingests a JUnit XML file and outputs a JSON
    summary with imported count.

    @test_id: TC-SYS-007-009
    @links: SYS-006
    """
    # Write a minimal JUnit XML with one passing test case
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="suite" tests="1" failures="0" errors="0">
    <testcase name="test_TC_SYS_001_001_basic" classname="test_basic" time="0.1">
      <properties>
        <property name="compliantflow.id" value="TC-SYS-001-001"/>
        <property name="compliantflow.links" value="SYS-001"/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""
    xml_path = test_dhf_root / "test-run.xml"
    xml_path.write_text(xml_content, encoding="utf-8")

    result = runner.invoke(cf_main, [
        "--dhf", dhf_str,
        "test", "import", str(xml_path),
        "--tester", "pytest",
        "--run-id", "test-run-1",
    ])
    assert result.exit_code == 0, f"Unexpected exit: {result.output}\n{result.exception}"
    json_lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) >= 1
    summary = json.loads(json_lines[0])
    assert summary["imported"] == 1
    assert summary["skipped"] == 0


def test_TC_SYS_007_010_test_status_command(runner, dhf_str, test_dhf_root):
    """
    TC-SYS-007-010: `test status` returns the stored result for a known TC ID.

    @test_id: TC-SYS-007-010
    @links: SYS-006
    """
    # First import a result so there is something to query
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="suite" tests="1" failures="0" errors="0">
    <testcase name="test_TC_SYS_002_001_status_test" classname="test_status" time="0.05">
      <properties>
        <property name="compliantflow.id" value="TC-SYS-002-001"/>
        <property name="compliantflow.links" value="SYS-001"/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""
    xml_path = test_dhf_root / "test-run-status.xml"
    xml_path.write_text(xml_content, encoding="utf-8")
    runner.invoke(cf_main, ["--dhf", dhf_str, "test", "import", str(xml_path)])

    result = runner.invoke(cf_main, ["--dhf", dhf_str, "test", "status", "TC-SYS-002-001"])
    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    json_lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) >= 1
    data = json.loads(json_lines[0])
    assert data.get("id") == "TC-SYS-002-001"
    assert data.get("testing_status") == "PASS"


def test_TC_SYS_007_011_test_status_not_found(runner, dhf_str):
    """
    TC-SYS-007-011: `test status` exits 1 for a TC that has no results.

    @test_id: TC-SYS-007-011
    @links: SYS-006
    """
    result = runner.invoke(cf_main, ["--dhf", dhf_str, "test", "status", "TC-SYS-999-001"])
    json_lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) >= 1
    data = json.loads(json_lines[0])
    assert data["found"] is False
    assert result.exit_code == 1


def test_TC_SYS_007_012_test_list_command(runner, dhf_str, test_dhf_root):
    """
    TC-SYS-007-012: `test list` outputs NDJSON rows for imported test results.

    @test_id: TC-SYS-007-012
    @links: SYS-006
    """
    # Import two results
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="suite" tests="2" failures="1" errors="0">
    <testcase name="test_TC_SYS_003_001_pass" classname="test_list" time="0.01">
      <properties>
        <property name="compliantflow.id" value="TC-SYS-003-001"/>
        <property name="compliantflow.links" value="SYS-001"/>
      </properties>
    </testcase>
    <testcase name="test_TC_SYS_003_002_fail" classname="test_list" time="0.01">
      <properties>
        <property name="compliantflow.id" value="TC-SYS-003-002"/>
        <property name="compliantflow.links" value="SYS-002"/>
      </properties>
      <failure message="Assertion error">assert False</failure>
    </testcase>
  </testsuite>
</testsuites>"""
    xml_path = test_dhf_root / "test-run-list.xml"
    xml_path.write_text(xml_content, encoding="utf-8")
    runner.invoke(cf_main, ["--dhf", dhf_str, "test", "import", str(xml_path)])

    result = runner.invoke(cf_main, ["--dhf", dhf_str, "test", "list"])
    assert result.exit_code == 0, result.output
    json_lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) >= 2

    # Filter by PASS
    result_pass = runner.invoke(cf_main, ["--dhf", dhf_str, "test", "list", "--status", "PASS"])
    assert result_pass.exit_code == 0
    pass_lines = [l for l in result_pass.output.splitlines() if l.strip().startswith("{")]
    for line in pass_lines:
        data = json.loads(line)
        assert data.get("testing_status") == "PASS"


# ---------------------------------------------------------------------------
# validate compliance --persist
# ---------------------------------------------------------------------------

def test_TC_SYS_007_013_validate_compliance_persist(runner, dhf_str, test_dhf_root):
    """
    TC-SYS-007-013: `validate compliance --persist` writes a compliance run
    to DHF/compliance-runs/<group_id>.yaml.

    @test_id: TC-SYS-007-013
    @links: SYS-006
    """
    gov_dir = str(test_dhf_root.parent / "governance")
    result = runner.invoke(cf_main, [
        "--dhf", dhf_str,
        "validate", "compliance", "IEC_62304",
        "--governance-dir", gov_dir,
        "--persist",
    ])
    assert result.exit_code in (0, 1), f"Unexpected exit: {result.output}"

    runs_file = test_dhf_root / "compliance-runs" / "IEC_62304.yaml"
    assert runs_file.exists(), f"Compliance run file not written: {runs_file}"

    import yaml
    with open(runs_file) as f:
        runs = yaml.safe_load(f)
    assert isinstance(runs, list)
    assert len(runs) >= 1
    run = runs[0]
    assert "standard_id" in run
    assert run["standard_id"] == "IEC_62304"
    assert "score" in run
    assert "timestamp" in run
