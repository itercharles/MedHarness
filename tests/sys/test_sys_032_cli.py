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

# Ensure src/ is on the path so cli.py can import compliantflow.traceability.*
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from click.testing import CliRunner
from compliantflow.cli import main
from utils.cli import main as dhf_main


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
    TC-SYS-032-001: validate schema exits 0 when all items are schema-valid.

    @test_id: TC-SYS-032-001
    @links: SYS-032
    """
    result = runner.invoke(dhf_main, ["--dhf", dhf_str, "validate", "schema"])
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
    result = runner.invoke(dhf_main, ["--dhf", dhf_str, "item", "list"])
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
    result = runner.invoke(dhf_main, ["--dhf", dhf_str, "item", "list", "--type", "SYS"])
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
    result = runner.invoke(dhf_main, ["--dhf", dhf_str, "item", "get", "SRS-001"])
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
    result = runner.invoke(dhf_main, ["--dhf", dhf_str, "item", "get", "SYS-NONEXISTENT"])
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
    config_path = test_dhf_root / "config" / "global.yaml"
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


def test_TC_SYS_032_010_cr_update_no_pr_flags(runner, test_dhf_root, dhf_str):
    """
    TC-SYS-032-010: cr update does not accept --pr-number; PR linkage is GitOps-implicit.

    Per SYSARCH-011, PR metadata is not stored in CR YAML. The cr update command
    only accepts --item flags. Passing --pr-number must be rejected by click.

    @test_id: TC-SYS-032-010
    @links: SYS-032
    """
    result = runner.invoke(
        main,
        [
            "--dhf", dhf_str, "cr", "update", "CR-001",
            "--pr-number", "99",
        ],
    )
    # click should reject the unknown option
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# validate traceability / compliance
# ---------------------------------------------------------------------------

def test_TC_SYS_032_013_validate_traceability_reports_orphans(runner, dhf_str):
    """
    TC-SYS-032-013: validate traceability exits 1 and reports isolated items.

    CR-001 in the test fixture has no graph edges, so the command must exit 1
    and include an ORPHAN line identifying the isolated item.

    @test_id: TC-SYS-032-013
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "validate", "traceability"])
    assert result.exit_code == 1
    assert "ORPHAN" in result.output


def test_TC_SYS_032_014_validate_compliance_passes(runner, dhf_str):
    """
    TC-SYS-032-014: validate compliance IEC_62304 exits 0 and outputs a JSON report.

    @test_id: TC-SYS-032-014
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "validate", "compliance", "IEC_62304"])
    assert result.exit_code == 0, result.output + (result.exception and str(result.exception) or "")
    json_line = next(l for l in result.output.splitlines() if l.strip().startswith("{"))
    parsed = json.loads(json_line)
    assert "score" in parsed
    assert "results" in parsed


def test_TC_SYS_032_015_validate_compliance_not_found_exits_1(runner, dhf_str):
    """
    TC-SYS-032-015: validate compliance with unknown group_id exits 1.

    @test_id: TC-SYS-032-015
    @links: SYS-032
    """
    result = runner.invoke(main, ["--dhf", dhf_str, "validate", "compliance", "NONEXISTENT"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# item create / update / delete
# ---------------------------------------------------------------------------

def test_TC_SYS_032_016_item_create_returns_created_item(runner, dhf_str):
    """
    TC-SYS-032-016: item create outputs the created item as JSON and exits 0.

    @test_id: TC-SYS-032-016
    @links: SYS-032
    """
    result = runner.invoke(
        dhf_main,
        ["--dhf", dhf_str, "item", "create",
         "--type", "SYS",
         "--data", '{"title": "CLI created requirement", "content": "Created via CLI"}'],
    )
    assert result.exit_code == 0, result.output + str(result.exception or "")
    json_line = next(l for l in result.output.splitlines() if l.strip().startswith("{"))
    parsed = json.loads(json_line)
    assert parsed["id"].startswith("SYS-")
    assert parsed["title"] == "CLI created requirement"
    # SYS items use GitOps model — no status field
    assert "status" not in parsed


def test_TC_SYS_032_017_item_create_invalid_json_exits_1(runner, dhf_str):
    """
    TC-SYS-032-017: item create with malformed JSON in --data exits 1.

    @test_id: TC-SYS-032-017
    @links: SYS-032
    """
    result = runner.invoke(
        dhf_main,
        ["--dhf", dhf_str, "item", "create", "--type", "SYS", "--data", "{not valid json}"],
    )
    assert result.exit_code == 1


def test_TC_SYS_032_018_item_create_unknown_field_exits_1(runner, dhf_str):
    """
    TC-SYS-032-018: item create with a field not in doc-type schema exits 1.

    The schema validator rejects unknown fields and the CLI surfaces the error
    without leaving a stale YAML file in the DHF.

    @test_id: TC-SYS-032-018
    @links: SYS-032
    """
    result = runner.invoke(
        dhf_main,
        ["--dhf", dhf_str, "item", "create",
         "--type", "SYS",
         "--data", '{"title": "Bad item", "nonexistent_field": "value"}'],
    )
    assert result.exit_code == 1
    assert "ERROR" in result.output


def test_TC_SYS_032_019_item_update_merges_fields(runner, test_dhf_root, dhf_str):
    """
    TC-SYS-032-019: item update merges JSON fields into the existing item.

    SYS-002 is in draft status; we update its title and verify the change.

    @test_id: TC-SYS-032-019
    @links: SYS-032
    """
    result = runner.invoke(
        dhf_main,
        ["--dhf", dhf_str, "item", "update", "SYS-002",
         "--data", '{"title": "Updated via CLI"}'],
    )
    assert result.exit_code == 0, result.output + str(result.exception or "")
    json_line = next(l for l in result.output.splitlines() if l.strip().startswith("{"))
    parsed = json.loads(json_line)
    assert parsed["title"] == "Updated via CLI"
    assert parsed["id"] == "SYS-002"
    # other fields must still be present
    assert "content" in parsed


def test_TC_SYS_032_020_item_update_not_found_exits_1(runner, dhf_str):
    """
    TC-SYS-032-020: item update with a nonexistent ID exits 1.

    @test_id: TC-SYS-032-020
    @links: SYS-032
    """
    result = runner.invoke(
        dhf_main,
        ["--dhf", dhf_str, "item", "update", "SYS-NONEXISTENT",
         "--data", '{"title": "ghost"}'],
    )
    assert result.exit_code == 1


def test_TC_SYS_032_021_item_delete_removes_item(runner, test_dhf_root, dhf_str):
    """
    TC-SYS-032-021: item delete removes the item and outputs {"deleted": id}.

    We create a throwaway item first so the test is self-contained.

    @test_id: TC-SYS-032-021
    @links: SYS-032
    """
    # Create the item to delete
    create_result = runner.invoke(
        dhf_main,
        ["--dhf", dhf_str, "item", "create",
         "--type", "SYS",
         "--data", '{"title": "To be deleted"}'],
    )
    assert create_result.exit_code == 0, create_result.output
    created = json.loads(next(l for l in create_result.output.splitlines() if l.startswith("{")))
    item_id = created["id"]

    # Delete it
    result = runner.invoke(dhf_main, ["--dhf", dhf_str, "item", "delete", item_id])
    assert result.exit_code == 0, result.output
    parsed = json.loads(next(l for l in result.output.splitlines() if l.startswith("{")))
    assert parsed["deleted"] == item_id

    # Confirm it's gone
    get_result = runner.invoke(dhf_main, ["--dhf", dhf_str, "item", "get", item_id])
    assert get_result.exit_code == 1


def test_TC_SYS_032_022_item_delete_not_found_exits_1(runner, dhf_str):
    """
    TC-SYS-032-022: item delete with a nonexistent ID exits 1.

    @test_id: TC-SYS-032-022
    @links: SYS-032
    """
    result = runner.invoke(dhf_main, ["--dhf", dhf_str, "item", "delete", "SYS-NONEXISTENT"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# item transitions / transition
# ---------------------------------------------------------------------------

def test_TC_SYS_032_023_item_transitions_returns_list(runner, dhf_str):
    """
    TC-SYS-032-023: item transitions outputs JSON with current_status and transitions list.

    CR-001 is in draft; the fixture lifecycle allows draft → approved.
    SYS items have no lifecycle (GitOps model) — transitions are empty.

    @test_id: TC-SYS-032-023
    @links: SYS-032
    """
    # CR has explicit lifecycle
    result = runner.invoke(main, ["--dhf", dhf_str, "item", "transitions", "CR-001"])
    assert result.exit_code == 0, result.output
    json_line = next(l for l in result.output.splitlines() if l.strip().startswith("{"))
    parsed = json.loads(json_line)
    assert parsed["item_id"] == "CR-001"
    assert parsed["current_status"] == "draft"
    assert isinstance(parsed["transitions"], list)
    assert len(parsed["transitions"]) > 0, "CR in draft should have transitions"

    # SYS items have no lifecycle — empty transitions
    sys_result = runner.invoke(main, ["--dhf", dhf_str, "item", "transitions", "SYS-002"])
    assert sys_result.exit_code == 0, sys_result.output
    sys_json = next(l for l in sys_result.output.splitlines() if l.strip().startswith("{"))
    sys_parsed = json.loads(sys_json)
    assert sys_parsed["item_id"] == "SYS-002"
    assert sys_parsed["current_status"] is None
    assert sys_parsed["transitions"] == []


def test_TC_SYS_032_024_item_transition_executes_state_change(runner, test_dhf_root, dhf_str):
    """
    TC-SYS-032-024: item transition changes a CR's status and outputs updated item JSON.

    CR-001 (draft) → approved; the fixture lifecycle allows this transition.

    @test_id: TC-SYS-032-024
    @links: SYS-032
    """
    result = runner.invoke(
        main,
        ["--dhf", dhf_str, "item", "transition", "CR-001", "approved", "--by", "tester"],
    )
    assert result.exit_code == 0, result.output + str(result.exception or "")
    json_line = next(l for l in result.output.splitlines() if l.strip().startswith("{"))
    parsed = json.loads(json_line)
    assert parsed["status"] == "approved"

    # Verify persisted to DHF
    from compliantflow.core import CompliantFlowCore
    core = CompliantFlowCore(test_dhf_root)
    item = core.get_item("CR-001")
    assert item["status"] == "approved"


# ---------------------------------------------------------------------------
# doc list / generate / export
# ---------------------------------------------------------------------------

@pytest.fixture
def real_dhf_str():
    """Return the real DHF path (not the isolated test fixture) for doc tests."""
    return str(Path(__file__).parent.parent.parent / "DHF")


def test_TC_SYS_032_025_doc_list_returns_json(runner, dhf_str):
    """
    TC-SYS-032-025: doc list outputs JSON with a doc_types key.

    @test_id: TC-SYS-032-025
    @links: SYS-032
    """
    result = runner.invoke(dhf_main, ["--dhf", dhf_str, "doc", "list"])
    assert result.exit_code == 0, result.output
    json_line = next(l for l in result.output.splitlines() if l.strip().startswith("{"))
    parsed = json.loads(json_line)
    assert "doc_types" in parsed
    assert isinstance(parsed["doc_types"], list)


def test_TC_SYS_032_026_doc_generate_writes_markdown(runner, real_dhf_str, tmp_path):
    """
    TC-SYS-032-026: doc generate writes a markdown file and outputs JSON with output_path.

    Uses the real DHF so Jinja2 templates are available.

    @test_id: TC-SYS-032-026
    @links: SYS-032
    """
    result = runner.invoke(dhf_main, ["--dhf", real_dhf_str, "doc", "generate", "SYS"])
    assert result.exit_code == 0, result.output + str(result.exception or "")
    json_line = next(l for l in result.output.splitlines() if l.strip().startswith("{"))
    parsed = json.loads(json_line)
    assert parsed["doc_type"] == "SYS"
    assert parsed["output_path"].endswith(".md")
    assert Path(parsed["output_path"]).exists()
    assert parsed["version"] != ""


def test_TC_SYS_032_027_doc_export_writes_pdf(runner, real_dhf_str):
    """
    TC-SYS-032-027: doc export regenerates markdown then produces a PDF file.

    Uses the real DHF so Jinja2 templates and WeasyPrint are available.

    @test_id: TC-SYS-032-027
    @links: SYS-032
    """
    result = runner.invoke(dhf_main, ["--dhf", real_dhf_str, "doc", "export", "SYS"])
    assert result.exit_code == 0, result.output + str(result.exception or "")
    json_line = next(l for l in result.output.splitlines() if l.strip().startswith("{"))
    parsed = json.loads(json_line)
    assert parsed["doc_type"] == "SYS"
    assert parsed["pdf_path"].endswith(".pdf")
    assert Path(parsed["pdf_path"]).exists()
    assert parsed["md_path"].endswith(".md")
