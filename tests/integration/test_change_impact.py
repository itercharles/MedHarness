"""A change reaches the items that depend on it, and `verify changes` says which.

Changing SYS-001 passed `verify changes` although SRS-001, SYSARCH-001 and RCM-001 hang
off it untouched. Now an item that depends on a changed one, through a typed link in a
traceability chain, must be changed too or listed in the CR's `reviewed_items`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from fixtures.starter import keep_the_starter_text

from medharness.cli import main
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Impact")
    keep_the_starter_text(tmp_path / "DHF")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "checkout", "-q", "-b", "feat")
    return tmp_path


def _edit(repo: Path, name: str, **fields) -> None:
    path = next((repo / "DHF" / "items").rglob(name))
    data = yaml.safe_load(path.read_text())
    data.update(fields)
    path.write_text(yaml.safe_dump(data))


def _change_sys(repo: Path, **cr_fields) -> None:
    _edit(repo, "SYS-001.yaml", content="Changed requirement.")
    _edit(repo, "CR-001.yaml", affected_items=["SYS-001"], **cr_fields)


def _changes(repo: Path):
    result = CliRunner().invoke(main, ["--dhf", str(repo / "DHF"), "verify", "changes", "--cr", "CR-001",
                                       "--since-ref", "main"])
    return result, json.loads(result.stdout.splitlines()[0])


def _impact(answer: dict) -> list[str]:
    return sorted(e.split(" depends on")[0].removeprefix("impact: ") for e in answer["errors"] if e.startswith("impact:"))


def test_items_that_depend_on_a_changed_one_are_named(repo: Path) -> None:
    _change_sys(repo)
    result, answer = _changes(repo)
    assert result.exit_code == 1
    assert _impact(answer) == ["RCM-001", "SRS-001", "SYSARCH-001"]
    assert any("SRS-001 depends on SYS-001, which this branch changes" in e for e in answer["errors"])


def test_reviewing_them_settles_it(repo: Path) -> None:
    _change_sys(repo, reviewed_items=["SRS-001", "SYSARCH-001", "RCM-001"])
    result, answer = _changes(repo)
    assert result.exit_code == 0, answer["errors"]


def test_changing_a_dependent_settles_it_and_reaches_its_own_dependents(repo: Path) -> None:
    """SRS-001 followed the change, so it is settled; SWDD-001 now depends on a changed item."""
    _change_sys(repo)
    _edit(repo, "SRS-001.yaml", content="Followed the change.")
    _edit(repo, "CR-001.yaml", affected_items=["SYS-001", "SRS-001"], reviewed_items=["SYSARCH-001", "RCM-001"])
    result, answer = _changes(repo)
    assert result.exit_code == 1 and _impact(answer) == ["SWDD-001"], answer["errors"]

    _edit(repo, "CR-001.yaml", reviewed_items=["SYSARCH-001", "RCM-001", "SWDD-001"])
    result, answer = _changes(repo)
    assert result.exit_code == 0, answer["errors"]


def test_the_depth_is_configurable(repo: Path) -> None:
    _change_sys(repo, reviewed_items=["SRS-001", "SYSARCH-001", "RCM-001"])
    global_yaml = repo / "DHF" / "config" / "global.yaml"
    original = global_yaml.read_text()
    global_yaml.write_text(original + "\nimpact_depth: 2\n")
    _, deeper = _changes(repo)
    assert _impact(deeper) == ["SWDD-001"], deeper["errors"]      # SWDD-001 implements SRS-001
    global_yaml.write_text(original + "\nimpact_depth: 0\n")
    result, off = _changes(repo)
    assert result.exit_code == 0, off["errors"]


def test_a_cr_that_lists_a_changed_item_is_not_its_dependent(repo: Path) -> None:
    """`affected_items` is bookkeeping: another CR naming SYS-001 does not need review."""
    _change_sys(repo, reviewed_items=["SRS-001", "SYSARCH-001", "RCM-001"])
    other = next((repo / "DHF" / "items").rglob("CR-001.yaml"))
    data = yaml.safe_load(other.read_text())
    data.update({"id": "CR-002", "title": "Other"})
    (other.parent / "CR-002.yaml").write_text(yaml.safe_dump(data))
    result, answer = _changes(repo)
    assert "CR-002" not in _impact(answer)


def test_a_branch_that_changes_no_item_has_no_impact(repo: Path) -> None:
    _edit(repo, "CR-001.yaml", title="Retitled")
    _, answer = _changes(repo)
    assert _impact(answer) == []
