"""`build plan` and `build code` leave their work uncommitted, and report all of it.

The caller commits: the recipe stages and commits what the run left. An agent
that committed inside its session left nothing to stage, so the caller pushed
nothing and reported success, and the commit died with the runner. And the
change sets were `git diff origin/main`, which does not see an untracked file,
so a file the agent created and did not commit was missing from them — for
`build plan`, missing from the CR's `affected_items`.

The model is replaced by a function that edits the checkout the way an agent
does: one file left untracked, one committed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from medharness.scaffold import replace_placeholders, scaffold_dhf


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Stages")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "-c", "user.email=t@e", "-c", "user.name=t", "add", "-A")
    _git(tmp_path, "-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", "base")
    _git(tmp_path, "remote", "add", "origin", str(tmp_path))
    _git(tmp_path, "fetch", "-q", "origin")
    return tmp_path


def _agent(repo: Path, untracked: str, committed: str):
    def run(prompt, *, resume_session="", model=""):
        if not (repo / committed).exists():
            for rel in (untracked, committed):
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                text = ("id: SRS-900\ntitle: New\nderives_from: [SYS-001]\n"
                        if rel.endswith(".yaml") else "x = 1\n")
                (repo / rel).write_text(text.replace("SRS-900", Path(rel).stem))
            _git(repo, "add", committed)
            _git(repo, "-c", "user.email=a@i", "-c", "user.name=agent", "commit", "-qm", "agent")
        return 0, "done", "sess"
    return run


@pytest.fixture(autouse=True)
def _no_github(monkeypatch):
    monkeypatch.setattr("medharness.services.cr_generation.get_session", lambda pr: "")
    monkeypatch.setattr("medharness.services.cr_generation.put_session", lambda pr, sid: "")


def test_build_code_uncommits_and_reports_both_files(repo: Path, monkeypatch) -> None:
    from medharness.services import cr_generation, llm

    start = _git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(llm, "_run_claude",
                        _agent(repo, "apps/new_untracked.py", "apps/new_committed.py"))

    result = cr_generation.generate_code("CR-001", repo / "DHF")

    assert _git(repo, "rev-parse", "HEAD") == start, "the agent's commit is still there"
    assert "apps/new_committed.py" in _git(repo, "diff", "--cached", "--name-only")
    assert set(result["artifacts"]["files_changed"]["created"]) >= {
        "apps/new_untracked.py", "apps/new_committed.py"}
    assert any(w["code"] == "agent_commits_undone" for w in result["warnings"])


def test_build_plan_records_an_uncommitted_item(repo: Path, monkeypatch) -> None:
    from medharness.services import cr_generation, llm

    monkeypatch.setattr(llm, "_run_claude", _agent(
        repo, "DHF/items/03_srs/SRS-901.yaml", "DHF/items/03_srs/SRS-902.yaml"))

    result = cr_generation.generate_dhf("CR-001", repo / "DHF")

    created = result["artifacts"]["items_changed"]["created"]
    assert {"SRS-901", "SRS-902"} <= set(created), created


def test_a_run_that_commits_nothing_warns_nothing(repo: Path, monkeypatch) -> None:
    from medharness.services import cr_generation, llm

    monkeypatch.setattr(llm, "_run_claude",
                        lambda prompt, *, resume_session="", model="": (0, "done", "s"))
    result = cr_generation.generate_code("CR-001", repo / "DHF")
    assert not any(w["code"] == "agent_commits_undone" for w in result["warnings"])
