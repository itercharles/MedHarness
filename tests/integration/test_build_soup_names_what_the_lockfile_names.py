"""`build soup` registers the packages a lockfile lists under the names it gives them.

An npm scoped package (`@types/node`) was registered as `node`, so its vulnerability lookup and
its purl named another package altogether. A uv lockfile lists the project itself, which is the
software being built and not SOUP. A failed update of a SOUP item crashed on a key the item
does not have, instead of saying which item failed.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dhfkit.tests.fixtures import bare_dhf
from medharness.cli import main


@pytest.fixture
def project(tmp_path: Path) -> Path:
    bare_dhf(tmp_path / "DHF")
    return tmp_path


def _soup(project: Path, *args: str):
    result = CliRunner().invoke(main, ["--dhf", str(project / "DHF"), "build", "soup", *args])
    return result, json.loads(result.stdout.splitlines()[0])


def test_a_scoped_npm_package_keeps_its_scope(project: Path) -> None:
    (project / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": {
        "": {"name": "app"},
        "node_modules/@types/node": {"version": "20.1.0"},
        "node_modules/express": {"version": "4.18.2"},
        "node_modules/express/node_modules/@babel/core": {"version": "7.0.0"},
    }}))

    result, answer = _soup(project)

    assert result.exit_code == 0, answer["errors"]
    assert sorted(answer["to_create"]) == ["@babel/core", "@types/node", "express"]


def test_the_project_a_uv_lockfile_lists_is_not_soup(project: Path) -> None:
    (project / "uv.lock").write_text(
        'version = 1\n\n'
        '[[package]]\nname = "myapp"\nversion = "1.0.0"\nsource = { editable = "." }\n\n'
        '[[package]]\nname = "requests"\nversion = "2.31.0"\nsource = { registry = "https://pypi.org/simple" }\n'
    )

    result, answer = _soup(project)

    assert result.exit_code == 0, answer["errors"]
    assert answer["to_create"] == ["requests"]


def test_a_failed_update_names_the_item_instead_of_crashing(project: Path) -> None:
    (project / "requirements.txt").write_text("requests==2.31.0\n")
    _soup(project)
    (project / "requirements.txt").write_text("requests==2.32.0\n")

    with patch("dhfkit.item_store.ItemStore.update_item", side_effect=ValueError("refused")):
        result, answer = _soup(project)

    assert result.exit_code == 1
    assert any("Failed to update SOUP-" in e and "refused" in e for e in answer["errors"]), answer["errors"]


def test_a_malformed_source_in_soup_sources_is_an_error_not_a_traceback(project: Path) -> None:
    (project / "DHF" / "config" / "soup-sources.yaml").write_text("sources:\n  - just a string\n")

    result, answer = _soup(project)

    assert result.exit_code == 1
    assert any("must be a mapping" in e for e in answer["errors"]), answer["errors"]
