"""build soup, run against a real DHF with nothing mocked.

Every existing test mocked `api.list_items` with dicts keyed "uid". Items carry
"id" and always have. So `build soup` — nine parsers, multi-ecosystem, the
headline of v0.11.0 — raised `KeyError: 'uid'` on every real project, in seven
places, while its suite passed.

No mocks here. That is the whole point: the defect lived exactly in the gap
between the shape the tests supplied and the shape production produces.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main as mh_main
from dhfkit.tests.fixtures import bare_dhf


@pytest.fixture
def project(tmp_path: Path) -> Path:
    dhf = tmp_path / "DHF"
    bare_dhf(dhf)
    (tmp_path / "requirements.txt").write_text("flask==3.0.0\nnumpy==1.26.0\n")
    return tmp_path


def _sync(project: Path, *extra: str) -> dict:
    r = CliRunner().invoke(mh_main, [
        "--dhf", str(project / "DHF"), "build", "soup",
        "--manifest", str(project / "requirements.txt"), *extra,
    ])
    assert "Traceback" not in (r.stderr or ""), r.stderr[-500:]
    assert r.exit_code == 0, (r.exit_code, r.output, r.stderr)
    return json.loads(r.stdout.splitlines()[0])


class TestItRunsAtAll:
    def test_writing_creates_items(self, project: Path) -> None:
        result = _sync(project)
        assert result["outcome"] == "completed"
        assert len(result["items_created"]) == 2
        assert all(i.startswith("SOUP-") for i in result["items_created"]), \
            result["items_created"]

    def test_a_second_run_matches_instead_of_duplicating(self, project: Path) -> None:
        """The path that read item["uid"] and crashed on every existing item."""
        _sync(project)
        again = _sync(project)
        assert again["to_create"] == []
        assert again["matched_count"] == 2

    def test_a_drifted_version_is_reported(self, project: Path) -> None:
        _sync(project)
        (project / "requirements.txt").write_text("flask==3.1.0\nnumpy==1.26.0\n")
        result = _sync(project)
        assert {e["name"] for e in result["to_update"]} == {"flask"}

    def test_an_item_no_longer_in_the_manifest_is_an_orphan(self, project: Path) -> None:
        _sync(project)
        (project / "requirements.txt").write_text("flask==3.0.0\n")
        result = _sync(project)
        assert [o["name"] for o in result["orphans"]] == ["numpy"]
        # The artifact key stays "uid" — existing consumers read it.
        assert "uid" in result["orphans"][0]
