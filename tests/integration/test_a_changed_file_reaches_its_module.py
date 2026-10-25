"""A changed code file reaches the items of the module that owns it, and `verify impact` asks for each to be settled.

Until a module declares `paths`, code changes reach nothing, so a CR that rewrote the dose calculation and
named no item passed every gate.
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
from medharness.scaffold import replace_placeholders, scaffold_dhf

DIMENSIONS = ("product", "requirements", "architecture", "risk", "soup", "test", "regulatory", "security", "usability")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _edit(repo: Path, name: str, **fields) -> None:
    path = next((repo / "DHF" / "items").rglob(name))
    data = yaml.safe_load(path.read_text())
    data.update(fields)
    path.write_text(yaml.safe_dump(data))


def _module_paths(repo: Path, *paths: str) -> None:
    """Rewrite MODULE-001's paths on the base, so the module itself is not a change of the branch."""
    _git(repo, "stash", "-u", "-q")
    _git(repo, "checkout", "-q", "main")
    _edit(repo, "MODULE-001.yaml", paths=list(paths))
    _git(repo, "commit", "-aqm", "paths")
    _git(repo, "checkout", "-q", "feat")
    _git(repo, "rebase", "-q", "main")
    _git(repo, "stash", "pop", "-q")


def _review(repo: Path, reviewed: list[str]) -> None:
    analysis = {
        "assumptions": ["the request means what it says"], "anchors": [], "created": [],
        "unchanged": [{"id": uid, "reason": "still holds"} for uid in reviewed],
        "dimensions": [{"dimension": d, "verdict": "not_required", "reason": "no effect", "items": []}
                       for d in DIMENSIONS],
    }
    _edit(repo, "CR-001.yaml", reviewed_items=reviewed, impact_analysis=analysis)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """MODULE-001 owns src/dose.py; the branch changes that file and nothing in the DHF."""
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Reach")
    keep_the_starter_text(tmp_path / "DHF")
    _edit(tmp_path, "MODULE-001.yaml", paths=["src/dose.py"])
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "dose.py").write_text("DOSE = 1\n")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "checkout", "-q", "-b", "feat")
    (tmp_path / "src" / "dose.py").write_text("DOSE = 2\n")
    _review(tmp_path, [])
    return tmp_path


def _impact(repo: Path):
    result = CliRunner().invoke(main, ["--dhf", str(repo / "DHF"), "verify", "impact", "--cr", "CR-001",
                                       "--since-ref", "main"])
    assert "Traceback" not in (result.stderr or "")
    return result, json.loads(result.stdout.splitlines()[0])


@pytest.mark.dhf_links("SRS-010")
@pytest.mark.dhf_testing("T1")
def test_a_changed_file_reaches_its_modules_design_and_requirement(repo: Path) -> None:
    result, answer = _impact(repo)
    assert result.exit_code == 1
    assert len(answer["errors"]) == 2 and all(e.startswith("code.src/dose.py: ") for e in answer["errors"])
    errors = " ".join(answer["errors"])
    assert "MODULE-001" in errors and "SWDD-001" in errors and "SRS-001" in errors


@pytest.mark.dhf_links("SRS-015")
@pytest.mark.dhf_testing("T3")
def test_reviewing_what_the_file_reaches_settles_it(repo: Path) -> None:
    _review(repo, ["SWDD-001", "SRS-001"])
    result, answer = _impact(repo)
    assert result.exit_code == 0 and answer["passed"] is True, answer["errors"]


@pytest.mark.dhf_links("SRS-015")
@pytest.mark.dhf_testing("T3")
def test_changing_the_items_it_reaches_settles_it(repo: Path) -> None:
    _edit(repo, "SWDD-001.yaml", content="Applies the new dose constant.")
    _edit(repo, "SRS-001.yaml", content="The dose constant is 2.")
    _edit(repo, "CR-001.yaml", affected_items=["SWDD-001", "SRS-001"])
    _review(repo, ["SYS-001", "CRS-001", "SYSARCH-001", "RCM-001"])
    result, answer = _impact(repo)
    assert result.exit_code == 0, answer["errors"]


@pytest.mark.dhf_links("SRS-012")
@pytest.mark.dhf_testing("T2")
def test_a_cr_marked_rejected_whose_branch_changes_a_file_is_stopped(repo: Path) -> None:
    _edit(repo, "CR-001.yaml", triage_result={"verdict": "rejected", "notes": "duplicate"})
    result, answer = _impact(repo)
    assert result.exit_code == 1
    assert answer["errors"][0].startswith("triage_result: ")
    assert any(e.startswith("code.src/dose.py: ") for e in answer["errors"]), answer["errors"]


@pytest.mark.dhf_links("SRS-011")
@pytest.mark.dhf_testing("T1")
def test_a_file_no_module_owns_fails_once_a_module_declares_paths(repo: Path) -> None:
    _review(repo, ["SWDD-001", "SRS-001"])
    (repo / "src" / "export.py").write_text("EXPORT = 1\n")
    result, answer = _impact(repo)
    assert result.exit_code == 1
    assert len(answer["errors"]) == 1
    assert answer["errors"][0].startswith("code.src/export.py: ") and "belongs to no module" in answer["errors"][0]


@pytest.mark.dhf_links("SRS-010")
@pytest.mark.dhf_testing("T3")
def test_a_directory_prefix_and_a_glob_each_own_their_files(repo: Path) -> None:
    _module_paths(repo, "src/")
    (repo / "src" / "export.py").write_text("EXPORT = 1\n")
    _review(repo, ["SWDD-001", "SRS-001"])
    assert _impact(repo)[0].exit_code == 0
    _module_paths(repo, "src/*.py")
    assert _impact(repo)[0].exit_code == 0


@pytest.mark.dhf_links("SRS-010")
@pytest.mark.dhf_testing("T2")
def test_a_deleted_file_reaches_its_module_too(repo: Path) -> None:
    (repo / "src" / "dose.py").unlink()
    result, answer = _impact(repo)
    assert result.exit_code == 1 and answer["errors"][0].startswith("code.src/dose.py: ")


def test_no_module_declaring_paths_turns_the_check_off(repo: Path) -> None:
    _module_paths(repo)
    (repo / "src" / "export.py").write_text("EXPORT = 1\n")
    result, answer = _impact(repo)
    assert result.exit_code == 0 and answer["passed"] is True, answer["errors"]


def test_an_impact_depth_of_zero_turns_the_check_off(repo: Path) -> None:
    global_yaml = repo / "DHF" / "config" / "global.yaml"
    global_yaml.write_text(global_yaml.read_text() + "\nimpact_depth: 0\n")
    result, answer = _impact(repo)
    assert result.exit_code == 0 and answer["passed"] is True, answer["errors"]


@pytest.mark.dhf_links("SRS-015")
@pytest.mark.dhf_testing("T4")
def test_docs_ci_and_lockfiles_need_no_module(repo: Path) -> None:
    _review(repo, ["SWDD-001", "SRS-001"])
    for name in ("README.md", "docs/guide.md", ".github/workflows/ci.yml", "uv.lock", "web/pnpm-lock.yaml"):
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text("changed\n")
    result, answer = _impact(repo)
    assert result.exit_code == 0 and answer["passed"] is True, answer["errors"]


@pytest.mark.dhf_links("SRS-011")
@pytest.mark.dhf_testing("T2")
def test_a_project_can_take_the_exemptions_away(repo: Path) -> None:
    _review(repo, ["SWDD-001", "SRS-001"])
    (repo / "README.md").write_text("changed\n")
    global_yaml = repo / "DHF" / "config" / "global.yaml"
    global_yaml.write_text(global_yaml.read_text() + "\nunowned_paths: []\n")
    result, answer = _impact(repo)
    assert result.exit_code == 1
    assert answer["errors"][0].startswith("code.README.md: ") and "belongs to no module" in answer["errors"][0]
