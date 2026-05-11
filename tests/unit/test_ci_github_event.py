"""CLI tests for `medharness ci github-event`."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from medharness.cli import main


def _write_event(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_github_event_outputs_rich_context(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request_review")
    event_path = tmp_path / "event.json"
    _write_event(event_path, {
        "review": {"state": "approved"},
        "pull_request": {
            "number": 17,
            "head": {"ref": "feat/CR-200"},
            "labels": [{"name": "cr:stage/spec"}],
        },
    })

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "ci",
            "github-event",
            "--event",
            str(event_path),
            "--stage-label-prefix",
            "cr:stage/",
            "--branch-stage",
            "feat/=develop",
            "--review-action",
            "approved:spec=gen-design",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["cr_id"] == "CR-200"
    assert payload["pr_number"] == 17
    assert payload["event_name"] == "pull_request_review"
    assert payload["review_state"] == "approved"
    assert payload["stage"] == "spec"
    assert payload["action"] == "gen-design"


def test_github_event_writes_outputs_file(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    event_path = tmp_path / "event.json"
    github_output = tmp_path / "github-output.txt"
    _write_event(event_path, {"inputs": {"cr_id": "CR-210", "stage": "design"}})

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "ci",
            "github-event",
            "--event",
            str(event_path),
            "--dispatch-action",
            "design=gen-code",
            "--github-output",
            str(github_output),
        ],
    )

    assert result.exit_code == 0, result.output
    outputs = github_output.read_text(encoding="utf-8")
    assert "cr_id=CR-210" in outputs
    assert "mode=new" in outputs
    assert "stage=design" in outputs
    assert "action=gen-code" in outputs


def test_github_event_issue_comment_infers_stage_from_pr_labels(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issue_comment")
    event_path = tmp_path / "event.json"
    _write_event(event_path, {
        "issue": {
            "number": 18,
            "title": "CR-210 Review",
            "pull_request": {"url": "https://api.github.com/repos/acme/repo/pulls/18"},
            "labels": [{"name": "cr:stage/spec"}],
        },
        "comment": {"body": "/approve"},
    })

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "ci",
            "github-event",
            "--event",
            str(event_path),
            "--stage-label-prefix",
            "cr:stage/",
            "--dispatch-action",
            "spec=record-approval",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["cr_id"] == "CR-210"
    assert payload["pr_number"] == 18
    assert payload["event_name"] == "issue_comment"
    assert payload["stage"] == "spec"
    assert payload["action"] == "record-approval"
