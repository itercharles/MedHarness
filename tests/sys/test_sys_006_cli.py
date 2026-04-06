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


# ---------------------------------------------------------------------------
# migrate rdm command (CR-026)
# ---------------------------------------------------------------------------

def test_TC_SYS_006_007_migrate_rdm_dry_run(runner, dhf_str, tmp_path):
    """
    TC-SYS-006-007: `compliantflow migrate rdm --dry-run` maps RDM items to
    CompliantFlow types and outputs a JSON report without writing any files.

    @test_id: TC-SYS-006-007
    @links: SYS-006
    """
    import yaml as _yaml

    # Build a minimal RDM-style source directory
    sys_dir = tmp_path / "system_requirements"
    sys_dir.mkdir()
    (sys_dir / "SYS-001.yaml").write_text(_yaml.dump({
        "id": "SYS-001",
        "title": "Safety Interlock",
        "description": "The system shall prevent unsafe operation.",
        "level": "system",
    }))

    srs_dir = tmp_path / "software_requirements"
    srs_dir.mkdir()
    (srs_dir / "SRS-001.yaml").write_text(_yaml.dump({
        "id": "SRS-001",
        "title": "Interlock Software Check",
        "description": "Software shall check interlock state on startup.",
        "level": "software",
        "parent_ids": ["SYS-001"],
    }))

    result = runner.invoke(
        cf_main,
        ["--dhf", dhf_str, "migrate", "rdm", str(tmp_path), "--dry-run"],
    )
    assert result.exit_code == 0, result.output

    json_text = "\n".join(
        l for l in result.output.splitlines()
        if not l.startswith("✓")
    )
    report = json.loads(json_text)

    assert report["dry_run"] is True
    created_types = {c["type"] for c in report["created"]}
    assert "SYS" in created_types
    assert "SRS" in created_types
    assert len(report["skipped"]) == 0

    # Dry run must not write any new files
    dhf_items = Path(dhf_str) / "items"
    file_count_after = sum(1 for _ in dhf_items.rglob("*.yaml"))
    # The fixture created 11 items; dry-run must not add any
    assert file_count_after == 11, f"Dry run wrote files: {file_count_after} found"


def test_TC_SYS_006_008_migrate_rdm_writes_files_and_preserves_links(runner, dhf_str, tmp_path):
    """
    TC-SYS-006-008: `compliantflow migrate rdm` writes YAML files to the DHF
    and preserves parent→child traceability links.

    @test_id: TC-SYS-006-008
    @links: SYS-006
    """
    import yaml as _yaml

    rdm_dir = tmp_path / "rdm_repo"
    rdm_dir.mkdir()
    crs_dir = rdm_dir / "user_needs"
    crs_dir.mkdir()
    (crs_dir / "UN-001.yaml").write_text(_yaml.dump({
        "id": "UN-001",
        "title": "User Safety Need",
        "description": "Users need the device to be safe.",
        "level": "user_need",
    }))

    sys_dir = rdm_dir / "system_requirements"
    sys_dir.mkdir()
    (sys_dir / "SR-001.yaml").write_text(_yaml.dump({
        "id": "SR-001",
        "title": "Safety Requirement",
        "description": "System shall be safe.",
        "level": "system",
        "parent_ids": ["UN-001"],
    }))

    result = runner.invoke(
        cf_main,
        ["--dhf", dhf_str, "migrate", "rdm", str(rdm_dir)],
    )
    assert result.exit_code == 0, result.output

    # CRS item written
    crs_items = list((Path(dhf_str) / "items" / "01_req_crs").glob("CRS-*.yaml"))
    assert len(crs_items) >= 1
    crs_data = _yaml.safe_load(crs_items[0].read_text())
    assert crs_data["title"] == "User Safety Need"

    # SYS item written with satisfies link to the new CRS id
    sys_items = list((Path(dhf_str) / "items" / "02_req_sys").glob("SYS-*.yaml"))
    assert len(sys_items) >= 1
    sys_data = _yaml.safe_load(sys_items[0].read_text())
    assert sys_data["title"] == "Safety Requirement"
    assert "satisfies" in sys_data
    assert crs_data["id"] in sys_data["satisfies"]


def test_TC_SYS_006_009_migrate_rdm_skips_non_requirement_yaml(runner, dhf_str, tmp_path):
    """
    TC-SYS-006-009: YAML files without an `id` field or with an unresolvable
    type are skipped and reported in the `skipped` list.

    @test_id: TC-SYS-006-009
    @links: SYS-006
    """
    import yaml as _yaml

    rdm_dir = tmp_path / "rdm_repo"
    rdm_dir.mkdir()

    # File with no id — should be silently ignored (not in skipped)
    (rdm_dir / "config.yaml").write_text(_yaml.dump({"some_key": "some_value"}))

    # File with id but unresolvable type
    (rdm_dir / "unknown.yaml").write_text(_yaml.dump({
        "id": "UNKNOWN-001",
        "title": "Unknown type item",
        "description": "No level, no directory hint.",
    }))

    result = runner.invoke(
        cf_main,
        ["--dhf", dhf_str, "migrate", "rdm", str(rdm_dir), "--dry-run"],
    )
    assert result.exit_code == 0, result.output

    json_text = "\n".join(
        l for l in result.output.splitlines() if not l.startswith("✓")
    )
    report = json.loads(json_text)
    skipped_ids = [s["rdm_id"] for s in report["skipped"]]
    assert "UNKNOWN-001" in skipped_ids
