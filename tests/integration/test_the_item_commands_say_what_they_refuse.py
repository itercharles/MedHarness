"""A command that cannot do what it was asked says so, and changes nothing.

`item update` wrote `type`, `doc_type` and `timestamp` into an item, and `file_path` wrote a copy of it to
the current directory; `item list --type` answered an unknown code with an empty list; `init --dhf` was
ignored; a transition of an item with no lifecycle spoke of state 'None'; `verify tests` printed each
warning twice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Refusals")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run(*args: str):
    return CliRunner().invoke(main, list(args))


def _snapshot(root: Path) -> dict[Path, bytes]:
    return {p: p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.mark.dhf_links("SRS-057")
@pytest.mark.dhf_testing("T7")
@pytest.mark.parametrize("field", ["type", "doc_type", "file_path", "timestamp"])
def test_update_refuses_a_field_the_store_derives(project: Path, field: str) -> None:
    before = _snapshot(project)

    result = _run("item", "update", "SRS-001", "--data", json.dumps({field: "x"}))

    assert result.exit_code == 1 and result.stdout == ""
    assert f"'{field}' is derived by the store and cannot be set" in result.stderr
    assert _snapshot(project) == before


@pytest.mark.dhf_links("SRS-060")
@pytest.mark.dhf_testing("T5")
def test_an_item_with_no_lifecycle_is_told_so(project: Path) -> None:
    before = _snapshot(project)

    moved = _run("item", "transition", "SRS-001", "draft")
    asked = _run("item", "transitions", "SRS-001")

    for result in (moved, asked):
        assert result.exit_code == 1 and result.stdout == ""
        assert "SRS has no lifecycle: SRS-001 has no status to move." in result.stderr
        assert "None" not in result.stderr
    assert _snapshot(project) == before


def test_listing_by_type_is_case_sensitive_and_names_the_valid_codes(project: Path) -> None:
    result = _run("item", "list", "--type", "srs")

    assert result.exit_code == 1 and result.stdout == ""
    assert "Unknown doc type 'srs'. Valid codes: " in result.stderr
    assert "SRS" in result.stderr


def test_listing_by_link_to_an_unknown_item_is_refused(project: Path) -> None:
    result = _run("item", "list", "--linked-to", "SRS-999")

    assert result.exit_code == 1 and result.stdout == ""
    assert "Item 'SRS-999' not found." in result.stderr


def test_init_refuses_dhf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = _run("--dhf", "custom", "init")

    assert result.exit_code == 2 and result.stdout == ""
    assert "init always scaffolds ./DHF and takes no --dhf." in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_init_still_scaffolds_without_dhf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = _run("init")

    assert result.exit_code == 0, result.stderr
    assert (tmp_path / "DHF").is_dir()


def test_verify_tests_prints_each_warning_once(project: Path) -> None:
    result = _run("verify", "tests")

    warnings = [line for line in result.stderr.splitlines() if line.startswith("WARN ")]
    assert warnings and len(warnings) == len(set(warnings))


def test_verify_tests_help_says_junit_is_required() -> None:
    result = _run("verify", "tests", "--help")

    assert " ".join(result.stdout.split()).count("Required, except with --cr") == 1


def test_verify_tests_without_junit_fails_unless_a_cr_needs_no_evidence(project: Path) -> None:
    result = _run("verify", "tests")

    assert result.exit_code == 1
    assert "No JUnit files found — pass --junit." in result.stderr
