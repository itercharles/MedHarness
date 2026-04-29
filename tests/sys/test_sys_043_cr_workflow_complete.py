"""
Tests for CR workflow completion orchestration.

Verifies that product repositories can delegate CR closeout to CompliantFlow
instead of carrying DHF transition and git commit glue code locally.

@links: SYS-041
"""

import json
from pathlib import Path

from click.testing import CliRunner

from compliantflow.cli import main


class FakeCompleteAdapter:
    def __init__(self, item=None):
        self.item = item or {"id": "CR-043", "status": "implementing"}
        self.transitions = []

    def get_item(self, item_id):
        if item_id == self.item["id"]:
            return self.item
        return None

    def execute_transition(self, item_id, to_state, performed_by=None):
        result = {
            "id": item_id,
            "from_state": self.item["status"],
            "to_state": to_state,
            "performed_by": performed_by,
        }
        self.transitions.append(result)
        self.item["status"] = to_state
        return result


def test_TC_SYS_043_001_cr_workflow_complete_transitions_and_commits(monkeypatch, tmp_path):
    """
    TC-SYS-043-001: cr workflow complete transitions the CR and commits DHF changes.

    @test_id: TC-SYS-043-001
    @links: SYS-041
    """
    dhf_repo = tmp_path / "dhf-repo"
    (dhf_repo / "DHF").mkdir(parents=True)
    adapter = FakeCompleteAdapter()
    git_calls = []

    def fake_run_git(repo_root: Path, args: list[str]) -> str:
        git_calls.append((repo_root, args))
        if args == ["status", "--porcelain"]:
            return " M DHF/items/09_cr/CR-043.yaml\n"
        return ""

    monkeypatch.setattr("compliantflow.cli._make_adapter_for_dhf_root", lambda dhf_root: adapter)
    monkeypatch.setattr("compliantflow.cli._run_git", fake_run_git)

    result = CliRunner().invoke(
        main,
        [
            "--dhf", str(dhf_repo / "DHF"),
            "cr", "workflow", "complete",
            "--dhf-repo", str(dhf_repo),
            "--cr", "CR-043",
            "--by", "github-actions[bot]",
            "--push",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[0])
    assert payload["cr_id"] == "CR-043"
    assert payload["changed"] is True
    assert payload["committed"] is True
    assert payload["pushed"] is True
    assert adapter.transitions == [{
        "id": "CR-043",
        "from_state": "implementing",
        "to_state": "completed",
        "performed_by": "github-actions[bot]",
    }]
    assert (dhf_repo, ["add", "-A"]) in git_calls
    assert (dhf_repo, ["commit", "-m", "chore: complete CR-043 [skip ci]"]) in git_calls
    assert (dhf_repo, ["push"]) in git_calls


def test_TC_SYS_043_002_cr_workflow_complete_noops_without_changes(monkeypatch, tmp_path):
    """
    TC-SYS-043-002: cr workflow complete skips commit when DHF files do not change.

    @test_id: TC-SYS-043-002
    @links: SYS-041
    """
    dhf_repo = tmp_path / "dhf-repo"
    (dhf_repo / "DHF").mkdir(parents=True)
    adapter = FakeCompleteAdapter()
    git_calls = []

    def fake_run_git(repo_root: Path, args: list[str]) -> str:
        git_calls.append((repo_root, args))
        if args == ["status", "--porcelain"]:
            return ""
        return ""

    monkeypatch.setattr("compliantflow.cli._make_adapter_for_dhf_root", lambda dhf_root: adapter)
    monkeypatch.setattr("compliantflow.cli._run_git", fake_run_git)

    result = CliRunner().invoke(
        main,
        [
            "--dhf", str(dhf_repo / "DHF"),
            "cr", "workflow", "complete",
            "--dhf-repo", str(dhf_repo),
            "--cr", "CR-043",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[0])
    assert payload["changed"] is False
    assert payload["committed"] is False
    assert payload["pushed"] is False
    assert [args for _, args in git_calls] == [["status", "--porcelain"]]


def test_TC_SYS_043_003_cr_workflow_complete_fails_when_cr_missing(monkeypatch, tmp_path):
    """
    TC-SYS-043-003: cr workflow complete fails clearly when CR is absent.

    @test_id: TC-SYS-043-003
    @links: SYS-041
    """
    dhf_repo = tmp_path / "dhf-repo"
    (dhf_repo / "DHF").mkdir(parents=True)
    adapter = FakeCompleteAdapter()

    monkeypatch.setattr("compliantflow.cli._make_adapter_for_dhf_root", lambda dhf_root: adapter)

    result = CliRunner().invoke(
        main,
        [
            "--dhf", str(dhf_repo / "DHF"),
            "cr", "workflow", "complete",
            "--dhf-repo", str(dhf_repo),
            "--cr", "CR-999",
        ],
    )

    assert result.exit_code == 1
    assert "CR 'CR-999' not found" in result.output
