"""Tests for DHF change request domain operations."""

from __future__ import annotations

from typing import Any

import pytest

from dhfkit.change_requests import (
    ExternalChangeRequest,
    build_change_request_data,
    complete_change_request,
    find_change_request_by_source,
    next_change_request_id,
    prepare_change_request,
)


class FakeAdapter:
    def __init__(self, items: list[dict[str, Any]] | None = None, created_id: str = "CR-034"):
        self.items = items or []
        self.created_id = created_id
        self.created_data: dict[str, Any] | None = None
        self.transitions: list[dict[str, Any]] = []

    def get_item(self, uid: str) -> dict[str, Any] | None:
        return next((item for item in self.items if item.get("id") == uid), None)

    def list_items(self, doc_type: str | None = None) -> list[dict[str, Any]]:
        return self.items

    def create_item(
        self,
        data: dict[str, Any],
        author: str = "system",
        cr_id: str | None = None,
    ) -> dict[str, Any]:
        self.created_author = author
        self.created_data = data
        created = {"id": self.created_id, **data}
        self.items.append(created)
        return created

    def execute_transition(
        self,
        item_id: str,
        to_state: str,
        performed_by: str | None = None,
    ) -> dict[str, Any]:
        transition = {"id": item_id, "status": to_state, "performed_by": performed_by}
        self.transitions.append(transition)
        return transition


def make_request() -> ExternalChangeRequest:
    return ExternalChangeRequest(
        title="Add weekly CR intake",
        description="Create CR from accepted issue.",
        justification="Weekly intake is easier.",
        requested_by="charles",
        source_url="https://github.com/example/product/issues/123",
        target_version="2026-W18",
        category="Feature",
        content="- CR PR is opened automatically.",
        source_number=123,
    )


def test_next_change_request_id_uses_cr_items_only():
    assert next_change_request_id([{"id": "CR-001"}, {"id": "SYS-009"}, {"id": "CR-033"}]) == "CR-034"


def test_find_change_request_by_source_matches_description_url():
    assert find_change_request_by_source(
        [{"id": "CR-034", "description": "Source issue: https://github.com/example/product/issues/123"}],
        "https://github.com/example/product/issues/123",
    ) == "CR-034"


def test_build_change_request_data_maps_external_request():
    data = build_change_request_data(make_request())
    assert data["type"] == "CR"
    assert data["title"] == "Add weekly CR intake"
    assert data["description"] == "Create CR from accepted issue.\n\nSource issue: https://github.com/example/product/issues/123"
    assert data["justification"] == "Weekly intake is easier."


def test_prepare_change_request_creates_with_adapter():
    adapter = FakeAdapter()
    result = prepare_change_request(
        make_request(),
        adapter,
        write=True,
        branch_prefix="cr",
        title_prefix="cr",
        source_label="issue",
    )

    assert result.should_create is True
    assert result.cr_id == "CR-034"
    assert result.branch == "cr/CR-034-from-issue-123-add-weekly-cr-intake"
    assert result.title == "cr(CR-034): Add weekly CR intake"
    assert adapter.created_author == "issue-to-cr"
    assert adapter.created_data == build_change_request_data(make_request())


def test_prepare_change_request_skips_known_existing_cr():
    adapter = FakeAdapter([{"id": "CR-034", "description": ""}])
    result = prepare_change_request(make_request(), adapter, write=True, known_cr_id="CR-034")

    assert result.should_create is False
    assert result.reason == "existing CR marker found"
    assert result.cr_id == "CR-034"


def test_prepare_change_request_skips_existing_source_url():
    adapter = FakeAdapter([
        {"id": "CR-034", "description": "Source issue: https://github.com/example/product/issues/123"}
    ])
    result = prepare_change_request(make_request(), adapter, write=True)

    assert result.should_create is False
    assert result.reason == "source request already has CR"
    assert result.cr_id == "CR-034"


def test_prepare_change_request_dry_run_uses_next_id():
    adapter = FakeAdapter([{"id": "CR-001"}, {"id": "CR-033"}])
    result = prepare_change_request(make_request(), adapter, write=False)

    assert result.should_create is True
    assert result.reason == "dry-run"
    assert result.cr_id == "CR-034"
    assert adapter.created_data is None


def test_complete_change_request_transitions_to_completed():
    adapter = FakeAdapter([{"id": "CR-043", "status": "implementing"}])
    result = complete_change_request(adapter, "CR-043", performed_by="github-actions[bot]")

    assert result == {"id": "CR-043", "status": "completed", "performed_by": "github-actions[bot]"}
    assert adapter.transitions == [result]


def test_complete_change_request_fails_when_missing():
    with pytest.raises(ValueError, match="CR 'CR-999' not found"):
        complete_change_request(FakeAdapter(), "CR-999", performed_by="system")
