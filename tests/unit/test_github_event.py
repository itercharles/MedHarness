"""Tests for medharness.services.github_event."""

import json
from pathlib import Path
from unittest.mock import patch

from medharness.services.github_event import (
    GitHubEventContext,
    infer_stage,
    parse_github_event,
    plan_github_event,
)


def _write_event(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_workflow_dispatch_with_manual_cr(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")

    result = parse_github_event(manual_cr_id="CR-001")

    assert result.cr_id == "CR-001"
    assert result.mode == "new"
    assert result.event_name == "workflow_dispatch"


def test_workflow_dispatch_without_cr(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")

    result = parse_github_event()

    assert result.mode == "skip"


def test_pull_request_merged_with_cr_in_branch(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    event_path = tmp_path / "event.json"
    _write_event(event_path, {
        "pull_request": {
            "head": {"ref": "cr/CR-034"},
            "merged": True,
            "number": 12,
        },
    })

    result = parse_github_event(event_path)

    assert result.cr_id == "CR-034"
    assert result.mode == "new"
    assert result.branch_ref == "cr/CR-034"
    assert result.merged is True


def test_pull_request_merged_falls_back_to_diff_when_branch_has_no_cr(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    event_path = tmp_path / "event.json"
    _write_event(event_path, {
        "pull_request": {
            "head": {"ref": "feature/new-work"},
            "merged": True,
            "merge_commit_sha": "abc123",
            "number": 12,
        },
    })

    with patch("medharness.services.github_event._extract_cr_from_diff", return_value="CR-099"):
        result = parse_github_event(event_path)

    assert result.cr_id == "CR-099"
    assert result.mode == "new"


def test_pull_request_not_merged_spec_branch(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    event_path = tmp_path / "event.json"
    _write_event(event_path, {
        "pull_request": {
            "head": {"ref": "spec/CR-034"},
            "merged": False,
            "number": 12,
        },
    })

    result = parse_github_event(event_path)

    assert result.cr_id == "CR-034"
    assert result.mode == "cancel"


def test_pull_request_review_changes_requested(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request_review")
    event_path = tmp_path / "event.json"
    _write_event(event_path, {
        "review": {"state": "changes_requested"},
        "pull_request": {
            "head": {"ref": "spec/CR-034"},
            "number": 12,
        },
    })

    result = parse_github_event(event_path)

    assert result.cr_id == "CR-034"
    assert result.mode == "iterate"
    assert result.pr_number == 12
    assert result.review_state == "changes_requested"


def test_pull_request_review_not_changes_requested(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request_review")
    event_path = tmp_path / "event.json"
    _write_event(event_path, {
        "review": {"state": "approved"},
        "pull_request": {
            "head": {"ref": "spec/CR-034"},
            "number": 12,
        },
    })

    result = parse_github_event(event_path)

    assert result.mode == "skip"


def test_issue_comment_on_pull_request_extracts_cr_and_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issue_comment")
    event_path = tmp_path / "event.json"
    _write_event(event_path, {
        "issue": {
            "number": 21,
            "title": "CR-034 Spec review",
            "pull_request": {"url": "https://api.github.com/repos/acme/repo/pulls/21"},
            "labels": [{"name": "cr:stage/spec"}],
        },
        "comment": {"body": "/approve"},
    })

    result = parse_github_event(event_path)

    assert result.cr_id == "CR-034"
    assert result.pr_number == 21
    assert result.mode == "skip"
    assert result.labels == ("cr:stage/spec",)


def test_issue_comment_on_issue_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issue_comment")
    event_path = tmp_path / "event.json"
    _write_event(event_path, {
        "issue": {
            "number": 22,
            "title": "CR-035 question",
        },
        "comment": {"body": "/approve"},
    })

    result = parse_github_event(event_path)

    assert result.cr_id is None
    assert result.mode == "skip"
    assert "not on a pull request" in result.reason


def test_repository_dispatch(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "repository_dispatch")
    event_path = tmp_path / "event.json"
    _write_event(event_path, {
        "client_payload": {"cr_id": "CR-034"},
    })

    result = parse_github_event(event_path)

    assert result.cr_id == "CR-034"
    assert result.mode == "new"


def test_unhandled_event(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    event_path = tmp_path / "event.json"
    event_path.write_text("{}", encoding="utf-8")

    result = parse_github_event(event_path)

    assert result.mode == "skip"


def test_no_event_path(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_EVENT_PATH", "/nonexistent/event.json")

    result = parse_github_event()

    assert result.mode == "skip"


def test_parse_includes_labels_and_dispatch_stage(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    event_path = tmp_path / "event.json"
    _write_event(event_path, {
        "inputs": {
            "cr_id": "CR-010",
            "stage": "spec",
        },
        "pull_request": {
            "head": {"ref": "feat/CR-010"},
            "labels": [{"name": "cr:stage/design"}],
        },
    })

    result = parse_github_event(event_path)

    assert result.cr_id == "CR-010"
    assert result.dispatch_stage == "spec"
    assert result.labels == ("cr:stage/design",)


def test_infer_stage_from_label_prefix():
    context = GitHubEventContext(
        cr_id="CR-050",
        mode="skip",
        branch_ref="feat/CR-050",
        labels=("cr:stage/design",),
    )
    assert infer_stage(
        context,
        branch_stage_pairs=(("feat/", "develop"),),
        stage_label_prefix="cr:stage/",
    ) == "design"


def test_infer_stage_from_branch_prefix():
    context = GitHubEventContext(
        cr_id="CR-050",
        mode="skip",
        branch_ref="spec/CR-050",
    )
    assert infer_stage(
        context,
        branch_stage_pairs=(("spec/", "spec"), ("feat/", "develop")),
    ) == "spec"


def test_plan_review_action_uses_stage_label_config():
    context = GitHubEventContext(
        cr_id="CR-034",
        mode="iterate",
        pr_number=12,
        event_name="pull_request_review",
        branch_ref="feat/CR-034",
        review_state="approved",
        labels=("cr:stage/spec",),
    )

    plan = plan_github_event(
        context,
        branch_stage_pairs=(("feat/", "develop"),),
        stage_label_prefix="cr:stage/",
        review_actions={"approved:spec": "gen-design"},
        default_action="noop",
    )

    assert plan.stage == "spec"
    assert plan.action == "gen-design"


def test_plan_review_action_falls_back_to_state_only():
    context = GitHubEventContext(
        cr_id="CR-034",
        mode="iterate",
        pr_number=12,
        event_name="pull_request_review",
        branch_ref="spec/CR-034",
        review_state="changes_requested",
    )

    plan = plan_github_event(
        context,
        branch_stage_pairs=(("spec/", "spec"),),
        review_actions={"changes_requested": "revise"},
        default_action="noop",
    )

    assert plan.stage == "spec"
    assert plan.action == "revise"


def test_plan_dispatch_action_uses_manual_stage():
    context = GitHubEventContext(
        cr_id="CR-100",
        mode="new",
        event_name="workflow_dispatch",
    )

    plan = plan_github_event(
        context,
        manual_stage="design",
        dispatch_actions={"design": "gen-code"},
        default_action="noop",
    )

    assert plan.stage == "design"
    assert plan.action == "gen-code"


def test_plan_pr_action_handles_merged_stage():
    context = GitHubEventContext(
        cr_id="CR-100",
        mode="new",
        event_name="pull_request",
        branch_ref="spec/CR-100",
        merged=True,
    )

    plan = plan_github_event(
        context,
        branch_stage_pairs=(("spec/", "spec"),),
        pr_actions={"merged:spec": "advance-to-design"},
        default_action="noop",
    )

    assert plan.stage == "spec"
    assert plan.action == "advance-to-design"


def test_plan_issue_comment_uses_stage_label_config():
    context = GitHubEventContext(
        cr_id="CR-034",
        mode="skip",
        pr_number=21,
        event_name="issue_comment",
        labels=("cr:stage/spec",),
    )

    plan = plan_github_event(
        context,
        stage_label_prefix="cr:stage/",
        dispatch_actions={"spec": "record-approval"},
        default_action="noop",
    )

    assert plan.stage == "spec"
    assert plan.action == "record-approval"
