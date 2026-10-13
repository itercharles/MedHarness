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
        assert result.exit_code == 1 and "item transition DEF-001" in result.stderr
        assert path.read_bytes() == before

    def test_create_with_a_status_that_is_no_state_is_refused(self, dhf: Path) -> None:
        """A type with a lifecycle is given its initial state; one without takes what it is told."""
        result = _item(dhf, "create", "--type", "SRS", "--data", json.dumps(
            {"title": "t", "content": "c", "derives_from": ["SYS-001"], "status": "banana"}))
        assert result.exit_code == 1 and "is not a state of SRS" in result.stderr

    def test_update_cannot_move_a_lifecycle_even_to_a_state_of_the_type(self, dhf: Path) -> None:
        """`item update CR-001 --data '{"status": "completed"}'` from `new` skipped every criterion."""
        result = _item(dhf, "update", "CR-001", "--data", '{"status": "completed"}')
        assert result.exit_code == 1 and "item transition CR-001" in result.stderr
        assert json.loads(_item(dhf, "get", "CR-001").stdout)["status"] == "new"

    def test_update_that_leaves_the_status_as_it_is_is_accepted(self, dhf: Path) -> None:
        status = json.loads(_item(dhf, "get", "CR-001").stdout)["status"]
        assert _item(dhf, "update", "CR-001", "--data", json.dumps({"status": status, "priority": "High"})).exit_code == 0

    def test_the_lifecycle_still_moves_an_item(self, dhf: Path) -> None:
        assert _item(dhf, "transition", "CR-001", "design").exit_code == 0
        assert json.loads(_item(dhf, "get", "CR-001").stdout)["status"] == "design"


def test_a_defect_with_no_status_is_a_known_anomaly_at_release(dhf: Path, tmp_path: Path) -> None:
    """Only `resolved`, `closed` and `cancelled` count as resolved; a missing status is not one."""
    from medharness.services.verify_release import known_anomalies

    path = _file(dhf, "DEF-001.yaml")
    path.write_text("\n".join(l for l in path.read_text().splitlines() if not l.startswith("status:")) + "\n")

    anomalies, errors = known_anomalies(dhf)
    assert [a["defect"] for a in anomalies] == ["DEF-001"]
    assert any("DEF-001" in e and "release_rationale" in e for e in errors)


class TestAnItemFileThatSaysNothing:
    """An emptied item vanished from every count; a `.yml` item escaped the duplicate check."""

    def test_an_empty_item_file_is_an_error(self, dhf: Path) -> None:
        _file(dhf, "CRS-001.yaml").write_text("# nothing here any more\n")
        result, answer = _verify(dhf)
        assert result.exit_code == 1
        assert any("CRS-001.yaml is empty" in e for e in answer["errors"]), answer["errors"]

    def test_an_item_file_ending_in_yml_is_an_error(self, dhf: Path) -> None:
        source = _file(dhf, "SRS-001.yaml")
        (source.parent / "SRS-001-copy.yml").write_text(source.read_text())
        result, answer = _verify(dhf)
        assert result.exit_code == 1
        assert any("SRS-001-copy.yml" in e and ".yaml" in e for e in answer["errors"]), answer["errors"]


def test_a_status_that_is_no_state_can_be_repaired_by_update(dhf: Path) -> None:
    """The fix `verify dhf` prints for it is an `item update`; there is no transition out of it."""
    path = _file(dhf, "CR-001.yaml")
    path.write_text(path.read_text().replace("status: new", "status: implementing"))
    assert _item(dhf, "update", "CR-001", "--data", '{"status": "develop"}').exit_code == 0
    assert json.loads(_item(dhf, "get", "CR-001").stdout)["status"] == "develop"


def test_a_text_field_holding_a_list_is_refused_where_it_is_read(dhf: Path) -> None:
    """`testing` as a list passed `verify dhf` and then crashed `verify tests` with a traceback."""
    path = _file(dhf, "SRS-001.yaml")
    data = yaml.safe_load(path.read_text())
    data["testing"] = ["T1: one", "T2: two"]
    path.write_text(yaml.safe_dump(data))

    result, answer = _verify(dhf)
    assert result.exit_code == 1
    assert any("'testing' must be text" in e for e in answer["errors"]), answer["errors"]


def test_no_shipped_doc_type_declares_a_field_twice() -> None:
    from dhfkit.paths import DEFAULT_CONFIG_DIR

    for path in sorted((DEFAULT_CONFIG_DIR / "doc_types").glob("*.yaml")):
        names = [p["name"] for p in yaml.safe_load(path.read_text())["properties"] if isinstance(p, dict)]
        assert len(names) == len(set(names)), f"{path.name} declares {sorted({n for n in names if names.count(n) > 1})} twice"
