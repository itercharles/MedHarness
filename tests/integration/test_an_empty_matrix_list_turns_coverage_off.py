"""`traceability_matrices: []` means no coverage is checked, as `required_traceability: []` means no rules.

An empty list used to fall back to the V-model chains, so the one key that opts out of
coverage could not.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from fixtures.starter import keep_the_starter_text

from medharness.cli import main
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Matrices")
    keep_the_starter_text(tmp_path / "DHF")
    next((tmp_path / "DHF" / "items").rglob("SWDD-001.yaml")).unlink()   # SRS-001 is now uncovered
    return tmp_path / "DHF"


def _verify(dhf: Path):
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf", "--strict"])
    return result, json.loads(result.stdout.splitlines()[0])


def _config(dhf: Path, text: str) -> None:
    global_yaml = dhf / "config" / "global.yaml"
    global_yaml.write_text(global_yaml.read_text() + "\n" + text)


def test_the_default_chains_notice_the_missing_design(dhf: Path) -> None:
    result, answer = _verify(dhf)
    assert result.exit_code == 1 and "SRS->SWDD: 1 uncovered" in answer["errors"]


def test_an_empty_list_checks_no_coverage(dhf: Path) -> None:
    _config(dhf, "traceability_matrices: []\n")
    result, answer = _verify(dhf)
    assert not any("uncovered" in e for e in answer["errors"]), answer["errors"]


def test_a_project_chain_replaces_the_defaults(dhf: Path) -> None:
    _config(dhf, "traceability_matrices:\n- name: Only this\n  description: d\n  path: [UC, CRS]\n")
    _, answer = _verify(dhf)
    assert not any("SRS->SWDD" in e for e in answer["errors"]), answer["errors"]


def test_a_release_with_no_chains_writes_no_matrix_report(dhf: Path, tmp_path: Path) -> None:
    _config(dhf, "traceability_matrices: []\n")
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "release", "--version", "1.0.0",
                                       "--out-dir", str(tmp_path / "rel")])
    artifacts = json.loads(result.stdout.splitlines()[0])["artifacts"]
    assert not any(a.startswith("traceability/") for a in artifacts), artifacts
