"""`item create`, `update` and `transition` answer with the item as `item get` shows it.

Each answered in a shape of its own: `create` had no `file_path`, `transition` carried a stray
`uid`, and `create` wrote the derived `type` into the file. A refused transition names what is unmet.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Writes")
    return tmp_path / "DHF"


def _run(dhf: Path, *args: str):
    return CliRunner().invoke(main, ["--dhf", str(dhf), *args])


def _answer(result) -> dict:
    assert result.exit_code == 0, result.stderr
    return json.loads(result.stdout)


def test_each_write_answers_with_what_item_get_shows(dhf: Path) -> None:
    created = _answer(_run(dhf, "item", "create", "--type", "CR", "--data", '{"title": "t", "description": "d"}'))
    cr = created["id"]
    assert created == _answer(_run(dhf, "item", "get", cr))
    updated = _answer(_run(dhf, "item", "update", cr, "--data", '{"priority": "High"}'))
    assert updated == _answer(_run(dhf, "item", "get", cr))
    moved = _answer(_run(dhf, "item", "transition", cr, "design"))
    assert moved == _answer(_run(dhf, "item", "get", cr))

    for answer in (created, updated, moved):
        assert "uid" not in answer and Path(answer["file_path"]).name == f"{cr}.yaml"
    assert created["status"] == "new" and moved["status"] == "design"


def test_a_created_item_does_not_store_its_derived_type(dhf: Path) -> None:
    cr = _answer(_run(dhf, "item", "create", "--type", "CR", "--data", '{"title": "t", "description": "d"}'))

    assert "type" not in yaml.safe_load(Path(cr["file_path"]).read_text())
    assert cr["type"] == "CR"


def test_a_refused_transition_names_the_unmet_field(dhf: Path) -> None:
    _run(dhf, "item", "transition", "CR-001", "design")

    result = _run(dhf, "item", "transition", "CR-001", "develop")

    assert result.exit_code == 1
    assert "CR-001 cannot move to 'develop': Implementation notes written (implementation_notes)." in result.stderr
    assert "_recorded" not in result.stderr
