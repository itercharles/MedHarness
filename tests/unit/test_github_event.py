"""Tests for medharness.services.github_event — parse_github_event."""

import json
from pathlib import Path

from medharness.services.github_event import GitHubEventContext, parse_github_event


def _write_event(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_workflow_dispatch_with_manual_cr(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")

    result = parse_github_event(manual_cr_id="CR-001")

    assert result.cr_id == "CR-001"
    assert result.mode == "new"


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
