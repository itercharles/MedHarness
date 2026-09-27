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
    # The types are inherited, not copied: a copy freezes them at this version.
    assert not (dhf / "config" / "doc_types").exists()
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
    from dhfkit.models.config import ProjectConfig

    rules = ProjectConfig.load(dhf / "config").required_traceability or []
    source_types = {r.source_type for r in rules}
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


def test_init_inherits_the_document_specifications(tmp_path: Path) -> None:
    from dhfkit.models.config import ProjectConfig

    dhf = tmp_path / "DHF"
    CliRunner().invoke(main, ["--dhf", str(dhf), "init"])
    doc_specs = ProjectConfig.load(dhf / "config").document_specifications
    assert {"SYS", "SRS", "RISK", "RCM"} <= set(doc_specs)


def test_documents_land_inside_a_dhf_of_any_name(tmp_path: Path) -> None:
    dhf = tmp_path / "my-dhf"
    CliRunner().invoke(main, ["--dhf", str(dhf), "init"])
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "doc", "SYS"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output.splitlines()[0])["md_path"].startswith(str(dhf))


def test_init_doc_generate_succeeds(tmp_path: Path) -> None:
    """doc generate SYS works on a freshly initialised DHF."""
    dhf = tmp_path / "DHF"
    CliRunner().invoke(main, ["--dhf", str(dhf), "init"])
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "doc", "SYS"])
    assert result.exit_code == 0, result.output
