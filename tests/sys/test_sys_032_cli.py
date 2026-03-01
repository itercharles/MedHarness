"""
Tests for SYS-032: Command-Line Interface

Verifies that the `python -m compliantflow` CLI correctly exposes
core DHF operations for CI/CD pipeline integration.

@links: SYS-032, SRS-012
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path so cli.py can import traceability.*
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from click.testing import CliRunner
from compliantflow.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def dhf_str(test_dhf_root):
    """Return the test DHF path as a string for --dhf option."""
    return str(test_dhf_root)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

def test_TC_SYS_032_001_validate_passes(runner, dhf_str):
    """
    TC-SYS-032-001: validate exits 0 when all items are schema-valid.

    @test_id: TC-SYS-032-001
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "validate"])
    assert result.exit_code == 0, result.output + (result.exception and str(result.exception) or "")
    assert "passed schema validation" in result.output


# ---------------------------------------------------------------------------
# item list / get
# ---------------------------------------------------------------------------

def test_TC_SYS_032_002_item_list_returns_json(runner, dhf_str):
    """
    TC-SYS-032-002: item list outputs newline-delimited JSON records.

    @test_id: TC-SYS-032-002
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "item", "list"])
    assert result.exit_code == 0, result.output
    lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(lines) > 0, "Expected at least one JSON line"
    parsed = json.loads(lines[0])
    assert "id" in parsed


def test_TC_SYS_032_003_item_list_filter_by_type(runner, dhf_str):
    """
    TC-SYS-032-003: item list --type SYS returns only SYS items.

    @test_id: TC-SYS-032-003
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "item", "list", "--type", "SYS"])
    assert result.exit_code == 0, result.output
    lines = [l for l in result.output.splitlines() if l.strip().startswith("{")]
    assert len(lines) > 0
    for line in lines:
        item = json.loads(line)
        assert item["id"].startswith("SYS-"), f"Expected SYS item, got {item['id']}"


def test_TC_SYS_032_004_item_get_returns_json(runner, dhf_str):
    """
    TC-SYS-032-004: item get <ID> outputs a single JSON object.

    @test_id: TC-SYS-032-004
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "item", "get", "SRS-001"])
    assert result.exit_code == 0, result.output
    # Find the JSON line (stdout may include a Git warning line)
    json_line = next(l for l in result.output.splitlines() if l.strip().startswith("{"))
    parsed = json.loads(json_line)
    assert parsed["id"] == "SRS-001"


def test_TC_SYS_032_005_item_get_not_found_exits_1(runner, dhf_str):
    """
    TC-SYS-032-005: item get with unknown ID exits 1.

    @test_id: TC-SYS-032-005
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "item", "get", "SYS-NONEXISTENT"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# cr check-status
# ---------------------------------------------------------------------------

def test_TC_SYS_032_006_cr_check_status_open_cr(runner, dhf_str):
    """
    TC-SYS-032-006: cr check-status exits 0 for a non-stable CR.

    CR-001 is in 'draft' status (non-stable) in the test fixture.

    @test_id: TC-SYS-032-006
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "cr", "check-status", "CR-001"])
    assert result.exit_code == 0, result.output
    assert "open" in result.output


def test_TC_SYS_032_007_cr_check_status_stable_cr_exits_1(runner, test_dhf_root, dhf_str):
    """
    TC-SYS-032-007: cr check-status exits 1 when the CR is in a stable state.

    We add a 'closed' stable state to the test fixture's global lifecycle config,
    then write it directly to the YAML to avoid lifecycle transition validation.

    @test_id: TC-SYS-032-007
    @links: SYS-032
    """
    import yaml

    # Add global_lifecycle with a stable 'closed' state to the test config
    config_path = test_dhf_root / "config" / "project_config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    config["global_lifecycle"] = {
        "states": [
            {"id": "draft", "label": "Draft"},
            {"id": "approved", "label": "Approved"},
            {"id": "rejected", "label": "Rejected"},
            {"id": "closed", "label": "Closed", "is_stable": True},
        ]
    }
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # Directly write 'closed' status to CR-001 YAML
    cr_yaml = test_dhf_root / "items" / "08_cr" / "CR-001.yaml"
    with open(cr_yaml) as f:
        cr_data = yaml.safe_load(f)
    cr_data["status"] = "closed"
    with open(cr_yaml, "w") as f:
        yaml.dump(cr_data, f, default_flow_style=False, sort_keys=False)

    result = runner.invoke(main, ["--dhf", dhf_str, "cr", "check-status", "CR-001"])
    assert result.exit_code == 1
    assert "stable" in result.output


def test_TC_SYS_032_008_cr_check_status_missing_cr_exits_1(runner, dhf_str):
    """
    TC-SYS-032-008: cr check-status exits 1 when CR does not exist.

    @test_id: TC-SYS-032-008
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "cr", "check-status", "CR-NONEXISTENT"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# cr update
# ---------------------------------------------------------------------------

def test_TC_SYS_032_009_cr_update_adds_items(runner, test_dhf_root, dhf_str):
    """
    TC-SYS-032-009: cr update --item adds the item to CR's affected_items.

    @test_id: TC-SYS-032-009
    @links: SYS-032
    """
    result = runner.invoke(
        main,
        ["--dhf", dhf_str, "cr", "update", "CR-001", "--item", "SYS-001", "--item", "SRS-002"],
    )
    assert result.exit_code == 0, result.output

    from compliantflow.core import CompliantFlowCore
    core = CompliantFlowCore(test_dhf_root)
    cr = core.get_item("CR-001")
    affected = cr.get("affected_items", [])
    assert "SYS-001" in affected
    assert "SRS-002" in affected


def test_TC_SYS_032_010_cr_update_tracks_pr(runner, test_dhf_root, dhf_str):
    """
    TC-SYS-032-010: cr update --pr-number records PR info on the CR.

    @test_id: TC-SYS-032-010
    @links: SYS-032
    """
    result = runner.invoke(
        main,
        [
            "--dhf", dhf_str, "cr", "update", "CR-001",
            "--pr-number", "99",
            "--pr-url", "https://github.com/test/repo/pull/99",
            "--pr-title", "feat: add CLI layer",
        ],
    )
    assert result.exit_code == 0, result.output

    from compliantflow.core import CompliantFlowCore
    core = CompliantFlowCore(test_dhf_root)
    cr = core.get_item("CR-001")
    prs = cr.get("implementation_prs", [])
    assert any(p.get("pr_number") == 99 for p in prs)


# ---------------------------------------------------------------------------
# traceability neighbors
# ---------------------------------------------------------------------------

def test_TC_SYS_032_011_traceability_neighbors_returns_json(runner, dhf_str):
    """
    TC-SYS-032-011: traceability neighbors outputs JSON with upstream/downstream.

    @test_id: TC-SYS-032-011
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "traceability", "neighbors", "SRS-001"])
    assert result.exit_code == 0, result.output
    # Find the JSON line (stdout may include a Git warning line)
    json_line = next(l for l in result.output.splitlines() if l.strip().startswith("{"))
    parsed = json.loads(json_line)
    assert "upstream" in parsed
    assert "downstream" in parsed
    assert isinstance(parsed["upstream"], list)
    assert isinstance(parsed["downstream"], list)


def test_TC_SYS_032_012_traceability_neighbors_not_found_exits_1(runner, dhf_str):
    """
    TC-SYS-032-012: traceability neighbors exits 1 for unknown item.

    @test_id: TC-SYS-032-012
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "traceability", "neighbors", "UNKNOWN-999"])
    assert result.exit_code == 1
