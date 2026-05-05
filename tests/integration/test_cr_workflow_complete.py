"""
Tests for CR workflow completion orchestration.

Verifies that product repositories can delegate CR closeout to MedHarness
instead of carrying DHF transition and git commit glue code locally.

"""

import json
from pathlib import Path

from click.testing import CliRunner

from medharness.cli import main


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


def test_cr_workflow_complete_transitions_and_commits(monkeypatch, tmp_path):
    """
    cr workflow complete transitions the CR and commits DHF changes.

    """
    dhf_repo = tmp_path / "dhf-repo"
    (dhf_repo / "DHF").mkdir(parents=True)
    adapter = FakeCompleteAdapter()
    git_calls = []

    def fake_run_git(repo_root: Path, args: list[str]) -> str:
        git_calls.append((repo_root, args))
        if args == ["status", "--porcelain"]:
            return " M DHF/items/06_cr/CR-043.yaml\n"
        return ""

    monkeypatch.setattr("medharness._helpers._make_adapter_for_dhf_root", lambda dhf_root: adapter)
    monkeypatch.setattr("medharness._helpers._run_git", fake_run_git)

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


def test_cr_workflow_complete_noops_without_changes(monkeypatch, tmp_path):
    """
    cr workflow complete skips commit when DHF files do not change.

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

    monkeypatch.setattr("medharness._helpers._make_adapter_for_dhf_root", lambda dhf_root: adapter)
    monkeypatch.setattr("medharness._helpers._run_git", fake_run_git)

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


def test_cr_workflow_complete_fails_when_cr_missing(monkeypatch, tmp_path):
    """
    cr workflow complete fails clearly when CR is absent.

    """
    dhf_repo = tmp_path / "dhf-repo"
    (dhf_repo / "DHF").mkdir(parents=True)
    adapter = FakeCompleteAdapter()

    monkeypatch.setattr("medharness._helpers._make_adapter_for_dhf_root", lambda dhf_root: adapter)

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


class TestCompleteFromGitHubPR:

    def _make_event(self, tmp_path, title="feat(CR-050): add feature"):
        import json as _json
        p = tmp_path / "event.json"
        p.write_text(_json.dumps({
            "action": "closed",
            "pull_request": {
                "number": 99,
                "title": title,
                "merged": True,
            },
        }), encoding="utf-8")
        return p

    def test_parses_cr_id_and_completes(self, monkeypatch, tmp_path):
        dhf_repo = tmp_path / "dhf"
        (dhf_repo / "DHF").mkdir(parents=True)
        adapter = FakeCompleteAdapter({"id": "CR-050", "status": "implementing"})
        event_path = self._make_event(tmp_path, "feat(CR-050): add evidence bundle")
        git_calls = []

        monkeypatch.setattr("medharness._helpers._make_adapter_for_dhf_root", lambda x: adapter)
        monkeypatch.setattr("medharness._helpers._run_git", lambda repo, args: git_calls.append(args))
        monkeypatch.setattr("medharness._helpers._git_has_changes", lambda repo: True)
        monkeypatch.setattr("medharness._helpers.subprocess.run", lambda *a, **kw: git_calls.append(kw.get("args", a)))

        result = CliRunner().invoke(main, [
            "--dhf", str(dhf_repo / "DHF"),
            "cr", "workflow", "complete-from-github-pr",
            "--dhf-repo", str(dhf_repo),
            "--event", str(event_path),
        ])

        assert result.exit_code == 0, f"out={result.output!r} err={result.stderr!r}"
        payload = json.loads(result.output.strip())
        assert payload["cr_id"] == "CR-050"
        assert payload["committed"] is True
        assert adapter.item["status"] == "completed"

    def test_skip_when_no_cr_in_title(self, monkeypatch, tmp_path):
        dhf_repo = tmp_path / "dhf"
        (dhf_repo / "DHF").mkdir(parents=True)
        event_path = self._make_event(tmp_path, "chore: update docs")

        monkeypatch.setattr("medharness._helpers._make_adapter_for_dhf_root", lambda x: FakeCompleteAdapter())

        result = CliRunner().invoke(main, [
            "--dhf", str(dhf_repo / "DHF"),
            "cr", "workflow", "complete-from-github-pr",
            "--dhf-repo", str(dhf_repo),
            "--event", str(event_path),
        ])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.strip())
        assert payload["skip"] is True

    def test_skip_when_no_event_and_no_title(self, monkeypatch, tmp_path):
        dhf_repo = tmp_path / "dhf"
        (dhf_repo / "DHF").mkdir(parents=True)

        monkeypatch.setattr("medharness._helpers._make_adapter_for_dhf_root", lambda x: FakeCompleteAdapter())

        result = CliRunner().invoke(main, [
            "--dhf", str(dhf_repo / "DHF"),
            "cr", "workflow", "complete-from-github-pr",
            "--dhf-repo", str(dhf_repo),
        ])

        assert result.exit_code == 0
        payload = json.loads(result.output.strip())
        assert payload["skip"] is True

    def test_uses_pr_title_option_over_event(self, monkeypatch, tmp_path):
        dhf_repo = tmp_path / "dhf"
        (dhf_repo / "DHF").mkdir(parents=True)
        adapter = FakeCompleteAdapter({"id": "CR-099", "status": "implementing"})
        event_path = self._make_event(tmp_path, "ignore this")

        monkeypatch.setattr("medharness._helpers._make_adapter_for_dhf_root", lambda x: adapter)
        monkeypatch.setattr("medharness._helpers._run_git", lambda repo, args: None)
        monkeypatch.setattr("medharness._helpers._git_has_changes", lambda repo: False)
        monkeypatch.setattr("medharness._helpers.subprocess.run", lambda *a, **kw: None)

        result = CliRunner().invoke(main, [
            "--dhf", str(dhf_repo / "DHF"),
            "cr", "workflow", "complete-from-github-pr",
            "--dhf-repo", str(dhf_repo),
            "--event", str(event_path),
            "--pr-title", "feat(CR-099): the real PR",
        ])

        assert result.exit_code == 0
        payload = json.loads(result.output.strip())
        assert payload["cr_id"] == "CR-099"
