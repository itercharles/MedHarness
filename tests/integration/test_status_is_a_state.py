"""An item's `status` is a state of its type.

`status` was a free field: a defect or a change request written as `banana` loaded and
passed `verify dhf --strict`, and anyone could write `completed` over a lifecycle that
exists to stop that. Release re-runs the closure gate, but the record itself was
never checked.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from fixtures.starter import keep_the_starter_text

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "States")
    keep_the_starter_text(tmp_path / "DHF")
    return tmp_path / "DHF"


def _file(dhf: Path, name: str) -> Path:
    return next((dhf / "items").rglob(name))


def _set(dhf: Path, name: str, **fields) -> None:
    path = _file(dhf, name)
    data = yaml.safe_load(path.read_text())
    data.update(fields)
    path.write_text(yaml.safe_dump(data))


def _verify(dhf: Path):
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf"])
    return result, json.loads(result.stdout.splitlines()[0])


def _item(dhf: Path, *args: str):
    return CliRunner().invoke(main, ["--dhf", str(dhf), "item", *args])


def test_the_starter_dhf_has_valid_statuses(dhf: Path) -> None:
    result, answer = _verify(dhf)
    assert result.exit_code == 0, answer["errors"]


def test_a_status_that_is_no_state_fails(dhf: Path) -> None:
    _set(dhf, "DEF-001.yaml", status="banana")
    result, answer = _verify(dhf)
    assert result.exit_code == 1
    assert any(e.startswith("DEF-001: status 'banana' is not a state of DEF (one of cancelled, closed,") for e in answer["errors"])
    assert "FAIL [status] DEF-001" in result.stderr


def test_a_type_with_a_lifecycle_takes_only_its_own_states(dhf: Path) -> None:
    """`draft` is a state of the global lifecycle but not of a CR's."""
    _set(dhf, "CR-001.yaml", status="draft")
    _, answer = _verify(dhf)
    assert any(e.startswith("CR-001: status 'draft' is not a state of CR") for e in answer["errors"])


def test_a_type_without_a_lifecycle_takes_the_global_states(dhf: Path) -> None:
    _set(dhf, "SRS-001.yaml", status="approved")
    assert _verify(dhf)[0].exit_code == 0
    _set(dhf, "SRS-001.yaml", status="banana")
    assert _verify(dhf)[0].exit_code == 1


class TestWrites:
    def test_update_to_a_status_that_is_no_state_is_refused(self, dhf: Path) -> None:
        path = _file(dhf, "DEF-001.yaml")
        before = path.read_bytes()
        result = _item(dhf, "update", "DEF-001", "--data", '{"status": "banana"}')
        assert result.exit_code == 1 and "is not a state of DEF" in result.stderr
        assert path.read_bytes() == before

    def test_create_with_a_status_that_is_no_state_is_refused(self, dhf: Path) -> None:
        """A type with a lifecycle is given its initial state; one without takes what it is told."""
        result = _item(dhf, "create", "--type", "SRS", "--data", json.dumps(
            {"title": "t", "content": "c", "derives_from": ["SYS-001"], "status": "banana"}))
        assert result.exit_code == 1 and "is not a state of SRS" in result.stderr

    def test_update_to_a_state_of_the_type_is_accepted(self, dhf: Path) -> None:
        assert _item(dhf, "update", "DEF-001", "--data", '{"status": "open"}').exit_code == 0

    def test_the_lifecycle_still_moves_an_item(self, dhf: Path) -> None:
        assert _item(dhf, "transition", "CR-001", "design").exit_code == 0
        assert json.loads(_item(dhf, "get", "CR-001").stdout)["status"] == "design"
