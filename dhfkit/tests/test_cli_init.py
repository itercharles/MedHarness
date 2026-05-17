"""Tests for dhfkit init command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from dhfkit.cli import main


def test_init_creates_expected_structure(tmp_path: Path) -> None:
    dhf = tmp_path / "DHF"
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "init", "--project-name", "Test Device"])
    assert result.exit_code == 0, result.output + (result.exception and str(result.exception) or "")

    assert (dhf / "config" / "global.yaml").exists()
    assert (dhf / "config" / "doc_types" / "sys.yaml").exists()
    assert (dhf / "config" / "doc_types" / "srs.yaml").exists()
    assert (dhf / "config" / "doc_types" / "risk.yaml").exists()
    assert (dhf / "config" / "doc_types" / "rcm.yaml").exists()
    assert (dhf / "items" / "02_sys").is_dir()
    assert (dhf / "items" / "03_srs").is_dir()
    assert (dhf / "items" / "10_risk").is_dir()
    assert (dhf / "items" / "11_rcm").is_dir()


def test_init_global_yaml_contains_project_name(tmp_path: Path) -> None:
    dhf = tmp_path / "DHF"
    CliRunner().invoke(main, ["--dhf", str(dhf), "init", "--project-name", "My Device"])
    config = yaml.safe_load((dhf / "config" / "global.yaml").read_text())
    assert config["project_name"] == "My Device"


def test_init_global_yaml_has_required_traceability(tmp_path: Path) -> None:
    dhf = tmp_path / "DHF"
    CliRunner().invoke(main, ["--dhf", str(dhf), "init"])
    config = yaml.safe_load((dhf / "config" / "global.yaml").read_text())
    rules = config.get("required_traceability", [])
    source_types = {r["source_type"] for r in rules}
    assert "SRS" in source_types
    assert "RCM" in source_types


def test_init_produces_valid_dhf(tmp_path: Path) -> None:
    """Initialised DHF passes schema validation."""
    dhf = tmp_path / "DHF"
    CliRunner().invoke(main, ["--dhf", str(dhf), "init"])
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "validate", "schema"])
    assert result.exit_code == 0, result.output


def test_init_stdout_is_json(tmp_path: Path) -> None:
    dhf = tmp_path / "DHF"
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "init", "--project-name", "Foo"])
    first_line = result.output.splitlines()[0]
    payload = json.loads(first_line)
    assert payload["project_name"] == "Foo"
    assert "created" in payload


def test_init_fails_if_directory_not_empty(tmp_path: Path) -> None:
    dhf = tmp_path / "DHF"
    dhf.mkdir()
    (dhf / "existing.txt").write_text("hello")
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "init"])
    assert result.exit_code != 0
    assert "not empty" in result.output


def test_init_default_project_name(tmp_path: Path) -> None:
    dhf = tmp_path / "DHF"
    CliRunner().invoke(main, ["--dhf", str(dhf), "init"])
    config = yaml.safe_load((dhf / "config" / "global.yaml").read_text())
    assert config["project_name"] == "My Project"


def test_init_project_name_with_quotes(tmp_path: Path) -> None:
    dhf = tmp_path / "DHF"
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "init", "--project-name", 'My "Device" v2'])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((dhf / "config" / "global.yaml").read_text())
    assert config["project_name"] == 'My "Device" v2'
