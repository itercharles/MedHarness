"""
Tests for SYS-006: CLI for CI/CD Integration

Verifies that both CLIs (compliantflow analysis CLI and utils data CLI)
produce machine-readable JSON on stdout and support headless CI/CD usage.

@links: SYS-006
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from compliantflow.cli import main as cf_main
from utils.cli import main as utils_main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def dhf_str(test_dhf_root):
    return str(test_dhf_root)


@pytest.fixture
def gov_str(governance_dir):
    return str(governance_dir)


# ---------------------------------------------------------------------------
# Analysis CLI (compliantflow) — read-only
# ---------------------------------------------------------------------------

def test_TC_SYS_006_001_cf_validate_traceability(runner, dhf_str):
    """
    TC-SYS-006-001: `compliantflow validate traceability` exits 0 (no orphans)
    or 1 (orphans found); no unhandled exception.

    @test_id: TC-SYS-006-001
    @links: SYS-006
    """
    result = runner.invoke(cf_main, ["--dhf", dhf_str, "validate", "traceability"])
    assert result.exit_code in (0, 1), f"Unexpected exit code {result.exit_code}: {result.output}"
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_TC_SYS_006_002_cf_traceability_matrix(runner, dhf_str):
    """
    TC-SYS-006-002: `compliantflow traceability matrix` exits 0 and outputs
    one JSON row object per line to stdout (NDJSON format).

    @test_id: TC-SYS-006-002
    @links: SYS-006
    """
    result = runner.invoke(cf_main, ["--dhf", dhf_str, "traceability", "matrix", "CRS", "SYS"])
    assert result.exit_code == 0, result.output + str(result.exception or "")
    # Rows are output as NDJSON (one JSON object per line); columns header goes to stderr
    row_lines = [
        l for l in result.output.splitlines()
        if l.strip().startswith("{") and "is_complete" in l
    ]
    assert len(row_lines) >= 1, f"No row JSON in output: {result.output}"
    row = json.loads(row_lines[0])
    assert "CRS" in row
    assert "SYS" in row
    assert "is_complete" in row


def test_TC_SYS_006_003_cf_validate_compliance(runner, dhf_str, gov_str):
    """
    TC-SYS-006-003: `compliantflow validate compliance` exits and outputs JSON report.

    @test_id: TC-SYS-006-003
    @links: SYS-006
    """
    result = runner.invoke(cf_main, [
        "--dhf", dhf_str,
        "validate", "compliance", "IEC_62304",
        "--governance-dir", gov_str,
    ])
    assert result.exit_code in (0, 1)  # 1 if any policy fails
    json_lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) >= 1, f"No JSON in output: {result.output}"
    report = json.loads(json_lines[0])
    assert "score" in report
    assert "results" in report


# ---------------------------------------------------------------------------
# Data CLI (utils) — mutations
# ---------------------------------------------------------------------------

def test_TC_SYS_006_004_utils_item_list_json(runner, dhf_str):
    """
    TC-SYS-006-004: `utils item list` exits 0 and outputs JSON items on stdout.

    @test_id: TC-SYS-006-004
    @links: SYS-006
    """
    result = runner.invoke(utils_main, ["--dhf", dhf_str, "item", "list", "--type", "SYS"])
    assert result.exit_code == 0, result.output + str(result.exception or "")
    json_lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) >= 1, "Expected at least one JSON item"
    item = json.loads(json_lines[0])
    assert "id" in item


def test_TC_SYS_006_005_utils_validate_schema(runner, dhf_str):
    """
    TC-SYS-006-005: `utils validate schema` exits 0 for a valid DHF.

    @test_id: TC-SYS-006-005
    @links: SYS-006
    """
    result = runner.invoke(utils_main, ["--dhf", dhf_str, "validate", "schema"])
    assert result.exit_code == 0, result.output + str(result.exception or "")
    assert "passed" in result.output.lower() or "valid" in result.output.lower()


def test_TC_SYS_006_006_cli_stdout_json_parseable(runner, dhf_str):
    """
    TC-SYS-006-006: utils item list output contains parseable JSON objects;
    every line that starts with '{' must be valid JSON.

    @test_id: TC-SYS-006-006
    @links: SYS-006
    """
    result = runner.invoke(utils_main, ["--dhf", dhf_str, "item", "list", "--type", "CRS"])
    assert result.exit_code == 0, result.output
    json_lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) >= 1, "Expected at least one JSON line"
    for line in json_lines:
        parsed = json.loads(line)
        assert isinstance(parsed, dict)
        assert "id" in parsed
