"""Tests for CLI command: validate traceability"""
import json

from click.testing import CliRunner

from dhfkit.cli import main


def _parse_json(output: str):
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            return json.loads(line)
    raise ValueError(f"No JSON found in output: {output!r}")


def test_validate_traceability_passes(populated_dhf):
    """validate traceability exits 0 on a clean DHF (may have orphan warnings)."""
    result = CliRunner().invoke(main, ["--dhf", str(populated_dhf), "validate", "traceability"])
    assert result.exit_code == 0, result.output + result.stderr


def test_validate_traceability_with_report(populated_dhf, tmp_path):
    """validate traceability --report writes a JSON file."""
    report_path = tmp_path / "trace.json"
    result = CliRunner().invoke(
        main,
        ["--dhf", str(populated_dhf), "validate", "traceability", "--report", str(report_path)],
    )
    assert result.exit_code == 0
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert "required" in data
    assert "coverage" in data
