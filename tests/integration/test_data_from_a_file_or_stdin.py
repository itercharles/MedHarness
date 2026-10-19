"""`--data` takes the JSON from a file (`@FILE`) or standard input (`-`).

A CR's `impact_analysis` is several kilobytes of nested JSON; written inline it has to be escaped for the shell,
and an agent doing that spent most of a session finding a way that worked.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf

FIELDS = {"implementation_notes": "It's \"quoted\", has a $dollar and a\nnewline."}


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Data")
    return tmp_path / "DHF"


def _notes(dhf: Path) -> str:
    return json.loads(CliRunner().invoke(main, ["--dhf", str(dhf), "item", "get", "CR-001"]).stdout)["implementation_notes"]


def test_update_reads_a_file(dhf: Path, tmp_path: Path) -> None:
    fields = tmp_path / "fields.json"
    fields.write_text(json.dumps(FIELDS))
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "update", "CR-001", "--data", f"@{fields}"])
    assert result.exit_code == 0, result.stderr
    assert _notes(dhf) == FIELDS["implementation_notes"]


def test_update_reads_standard_input(dhf: Path) -> None:
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "update", "CR-001", "--data", "-"],
                                input=json.dumps(FIELDS))
    assert result.exit_code == 0, result.stderr
    assert _notes(dhf) == FIELDS["implementation_notes"]


def test_create_reads_a_file(dhf: Path, tmp_path: Path) -> None:
    fields = tmp_path / "cr.json"
    fields.write_text(json.dumps({"title": "From a file", "description": "d"}))
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "create", "--type", "CR", "--data", f"@{fields}"])
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout)["title"] == "From a file"


@pytest.mark.parametrize("data", ["@/no/such/file.json", "@"])
def test_a_file_that_cannot_be_read_is_named(dhf: Path, data: str) -> None:
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "update", "CR-001", "--data", data])
    assert result.exit_code == 1 and "--data: cannot read" in result.stderr
    assert "Traceback" not in result.stderr


def test_a_file_that_is_not_text_is_named(dhf: Path, tmp_path: Path) -> None:
    binary = tmp_path / "x.json"
    binary.write_bytes(b"\xff\xfe\x00")
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "update", "CR-001", "--data", f"@{binary}"])
    assert result.exit_code == 1 and "--data: cannot read" in result.stderr


@pytest.mark.parametrize("content", ["", "[1, 2]", "{broken"])
def test_a_file_that_is_not_a_json_object_is_refused_like_inline_json(dhf: Path, tmp_path: Path, content: str) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(content)
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "update", "CR-001", "--data", f"@{bad}"])
    assert result.exit_code == 1 and "--data" in result.stderr


def test_empty_standard_input_is_refused(dhf: Path) -> None:
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "update", "CR-001", "--data", "-"], input="")
    assert result.exit_code == 1 and "not valid JSON" in result.stderr
