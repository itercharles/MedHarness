"""A completed CR whose approval no longer stands goes back to `develop`, and is completed again.

`completed` had no way out, so after approving a CR, a reviewer's "Request changes" could not start a
revision: the AI stages refused a completed CR and `item transition` offered no move.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from fixtures.starter import keep_the_starter_text, verify_the_starter

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf

CLOSED = {"implementation_notes": "n", "affected_risk_items": [], "affected_items": []}


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Reopen")
    keep_the_starter_text(tmp_path / "DHF")
    path = next((tmp_path / "DHF" / "items").rglob("CR-001.yaml"))
    data = yaml.safe_load(path.read_text())
    data.update(CLOSED)
    path.write_text(yaml.safe_dump(data))
    for state in ("design", "develop", "completed"):
        assert _run(tmp_path / "DHF", "item", "transition", "CR-001", state).exit_code == 0
    return tmp_path / "DHF"


def _run(dhf: Path, *args: str):
    return CliRunner().invoke(main, ["--dhf", str(dhf), *args])


def _status(dhf: Path) -> str:
    return json.loads(_run(dhf, "item", "get", "CR-001").stdout)["status"]


@pytest.mark.dhf_links("SRS-062")
@pytest.mark.dhf_testing("T2")
def test_a_completed_cr_is_reopened_to_develop(dhf: Path) -> None:
    assert _status(dhf) == "completed"
    result = _run(dhf, "item", "transition", "CR-001", "develop")
    assert result.exit_code == 0, result.stderr
    assert _status(dhf) == "develop"


@pytest.mark.dhf_links("SRS-062")
@pytest.mark.dhf_testing("T3")
def test_the_transition_is_offered_on_a_completed_cr(dhf: Path) -> None:
    moves = {t["to_state"]: t for t in json.loads(_run(dhf, "item", "transition", "CR-001").stdout)["transitions"]}
    assert moves["develop"]["can_transition"] is True


@pytest.mark.dhf_links("SRS-062")
@pytest.mark.dhf_testing("T2")
def test_a_reopened_cr_is_completed_again_on_the_next_approval(dhf: Path) -> None:
    _run(dhf, "item", "transition", "CR-001", "develop")
    assert _run(dhf, "item", "transition", "CR-001", "completed").exit_code == 0
    assert _status(dhf) == "completed"


@pytest.mark.dhf_links("SRS-061")
@pytest.mark.dhf_testing("T4")
def test_a_cr_a_release_lists_cannot_be_reopened(dhf: Path) -> None:
    created = _run(dhf, "item", "create", "--type", "REL", "--data", json.dumps(
        {"title": "r", "version": "1.0.0", "included_items": ["CR-001"], "release_notes": "n"}))
    assert created.exit_code == 0, created.stderr

    result = _run(dhf, "item", "transition", "CR-001", "develop")

    assert result.exit_code == 1 and "not_released" in result.stderr, result.stderr
    assert _status(dhf) == "completed"


@pytest.mark.dhf_links("SRS-044")
@pytest.mark.dhf_testing("T4")
def test_a_reopened_cr_is_left_out_of_a_release_until_it_is_completed_again(dhf: Path, tmp_path: Path) -> None:
    junit = verify_the_starter(dhf, tmp_path / "tr")
    release = lambda: json.loads(_run(dhf, "build", "release", "--version", "1.0.0", "--out-dir",
                                      str(tmp_path / "rel"), "--junit", str(junit)).stdout.splitlines()[0])
    assert release()["cr_ids"] == ["CR-001"]

    _run(dhf, "item", "transition", "CR-001", "develop")

    assert release()["cr_ids"] == []
