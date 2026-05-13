"""Unit tests for workflow command helpers that adapt service payloads."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from medharness.commands.cr import _generate_initial_spec


def test_generate_initial_spec_preserves_legacy_ok_passed_mapping(tmp_path: Path):
    dhf_root = tmp_path / "DHF"
    dhf_root.mkdir()
    with patch(
        "medharness.services.cr_generation.generate_spec",
        return_value={
            "outcome": "ok",
            "artifacts": {
                "spec_path": str(tmp_path / "docs" / "cr-specs" / "CR-001-Spec.md"),
                "spec_json_path": str(tmp_path / "docs" / "cr-specs" / "CR-001-Spec.json"),
            },
        },
    ):
        result = _generate_initial_spec("CR-001", dhf_root)
    assert result["spec_status"] == "ok"
    assert result["spec_validation"] == "passed"


def test_generate_initial_spec_preserves_legacy_ok_corrected_mapping(tmp_path: Path):
    dhf_root = tmp_path / "DHF"
    dhf_root.mkdir()
    with patch(
        "medharness.services.cr_generation.generate_spec",
        return_value={
            "outcome": "corrected",
            "artifacts": {
                "spec_path": str(tmp_path / "docs" / "cr-specs" / "CR-002-Spec.md"),
                "spec_json_path": str(tmp_path / "docs" / "cr-specs" / "CR-002-Spec.json"),
            },
        },
    ):
        result = _generate_initial_spec("CR-002", dhf_root)
    assert result["spec_status"] == "ok"
    assert result["spec_validation"] == "corrected"


def test_generate_initial_spec_preserves_legacy_completed_with_errors_mapping(tmp_path: Path):
    dhf_root = tmp_path / "DHF"
    dhf_root.mkdir()
    with patch(
        "medharness.services.cr_generation.generate_spec",
        return_value={
            "outcome": "completed_with_errors",
            "artifacts": {
                "spec_path": str(tmp_path / "docs" / "cr-specs" / "CR-003-Spec.md"),
                "spec_json_path": str(tmp_path / "docs" / "cr-specs" / "CR-003-Spec.json"),
            },
        },
    ):
        result = _generate_initial_spec("CR-003", dhf_root)
    assert result["spec_status"] == "completed_with_errors"
    assert result["spec_validation"] == "corrected"


def test_generate_initial_spec_maps_tool_error_to_error_status(tmp_path: Path):
    dhf_root = tmp_path / "DHF"
    dhf_root.mkdir()
    with patch(
        "medharness.services.cr_generation.generate_spec",
        return_value={"outcome": "tool_error", "artifacts": {}},
    ):
        result = _generate_initial_spec("CR-004", dhf_root)
    assert result["spec_status"] == "error"
    assert result["spec_validation"] is None
