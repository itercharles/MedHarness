"""A link's field and target type are checked, not only that the target exists.

`SYS satisfies RISK-001` passed `verify dhf --strict` although the schema says a
SYS satisfies a CRS, and a SWDD listing `SRS-002` under `module` made SRS-002
count as implemented — the one link that counts as coverage was in a field that
could never mean it. Defects' `violated_requirements` and releases'
`included_items` were not checked for dangling targets at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from fixtures.starter import keep_the_starter_text

from medharness.cli import main
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Typed")
    keep_the_starter_text(tmp_path / "DHF")
    return tmp_path / "DHF"


def _file(dhf: Path, name: str) -> Path:
    return next((dhf / "items").rglob(name))


def _write(path: Path, **fields) -> None:
    data = yaml.safe_load(path.read_text())
    data.update(fields)
    path.write_text(yaml.safe_dump(data))


def _verify(dhf: Path, *flags: str):
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf", *flags])
    return result, json.loads(result.stdout.splitlines()[0])


def _item(dhf: Path, *args: str):
    return CliRunner().invoke(main, ["--dhf", str(dhf), "item", *args])


def test_the_starter_chain_passes_strict(dhf: Path) -> None:
    result, answer = _verify(dhf, "--strict")
    assert result.exit_code == 0, answer["errors"]


def test_a_link_to_the_wrong_type_fails(dhf: Path) -> None:
    _write(_file(dhf, "SYS-001.yaml"), satisfies=["CRS-001", "RISK-001"])
    result, answer = _verify(dhf)
    assert result.exit_code == 1
    assert "SYS-001.satisfies → RISK-001: RISK is not one of CRS" in answer["errors"]
    assert "[link-type]" in result.stderr


def test_a_link_in_a_field_that_accepts_any_type_is_fine(dhf: Path) -> None:
    _write(_file(dhf, "CR-001.yaml"), affected_items=["SRS-001", "RISK-001", "SOUP-001"])
    result, answer = _verify(dhf, "--strict")
    assert result.exit_code == 0, answer["errors"]


def test_a_link_in_the_wrong_field_does_not_count_as_coverage(dhf: Path) -> None:
    """SRS-002 exists; the only link to it from a SWDD is under `module`, which takes MODULEs."""
    _write(_file(dhf, "SRS-001.yaml"))   # untouched; SRS-002 below
    srs = yaml.safe_load(_file(dhf, "SRS-001.yaml").read_text())
    srs.update({"id": "SRS-002", "title": "Second", "content": "Second requirement."})
    (_file(dhf, "SRS-001.yaml").parent / "SRS-002.yaml").write_text(yaml.safe_dump(srs))
    _write(_file(dhf, "SWDD-001.yaml"), module=["MODULE-001", "SRS-002"])

    result, answer = _verify(dhf, "--strict")

    assert result.exit_code == 1
    assert any("SWDD-001.module → SRS-002" in e for e in answer["errors"]), answer["errors"]
    assert any("SRS->SWDD: 1 uncovered" in e for e in answer["errors"]), answer["errors"]


@pytest.mark.parametrize("name,field,target", [
    ("DEF-001.yaml", "violated_requirements", "SRS-999"),
    ("REL-001.yaml", "included_items", "CR-777"),
])
def test_a_dangling_link_in_a_multiselect_field_is_found(dhf: Path, name: str, field: str, target: str) -> None:
    _write(_file(dhf, name), **{field: [target]})
    result, answer = _verify(dhf)
    assert result.exit_code == 1
    assert any(f".{field} → {target}: target does not exist" in e for e in answer["errors"]), answer["errors"]


class TestWritesAreRefusedToo:
    def test_create_with_a_wrong_type_link(self, dhf: Path) -> None:
        before = sorted((dhf / "items").rglob("*.yaml"))
        result = _item(dhf, "create", "--type", "SRS", "--data", json.dumps(
            {"title": "x", "content": "y", "derives_from": ["RISK-001"]}))
        assert result.exit_code == 1 and "accepts only SYS" in result.stderr
        assert sorted((dhf / "items").rglob("*.yaml")) == before

    def test_update_with_a_wrong_type_link_leaves_the_file(self, dhf: Path) -> None:
        path = _file(dhf, "SYS-001.yaml")
        before = path.read_bytes()
        result = _item(dhf, "update", "SYS-001", "--data", '{"satisfies": ["SRS-001"]}')
        assert result.exit_code == 1 and "SYS.satisfies accepts only CRS" in result.stderr
        assert path.read_bytes() == before

    def test_a_correct_link_is_accepted(self, dhf: Path) -> None:
        result = _item(dhf, "update", "SYS-001", "--data", '{"satisfies": ["CRS-001"]}')
        assert result.exit_code == 0, result.stderr
