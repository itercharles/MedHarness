"""Change request domain operations for DHF repositories."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from dhfkit.id_generator import get_next_id


class ChangeRequestAdapter(Protocol):
    """Minimal adapter surface needed by CR domain operations."""

    def get_item(self, uid: str) -> dict[str, Any] | None: ...

    def list_items(self, doc_type: str | None = None) -> list[dict[str, Any]]: ...

    def create_item(
        self,
        data: dict[str, Any],
        author: str = "system",
        cr_id: str | None = None,
    ) -> dict[str, Any]: ...

    def execute_transition(
        self,
        item_id: str,
        to_state: str,
        performed_by: str | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ExternalChangeRequest:
    """System-neutral input for creating a DHF Change Request."""

    title: str
    description: str
    justification: str
    requested_by: str
    source_url: str
    target_version: str
    category: str = "General"
    priority: str = "Medium"
    content: str = ""
    source_number: int | None = None


@dataclass(frozen=True)
class ChangeRequestPreparation:
    """Result of preparing a CR from an external change request."""

    should_create: bool
    reason: str
    cr_id: str | None = None
    branch: str | None = None
    cr_path: str | None = None
    title: str | None = None


def next_change_request_id(items: list[dict[str, Any]]) -> str:
    """Return the next available CR ID from a list of DHF items."""
    ids = [str(item.get("id", "")) for item in items if str(item.get("id", "")).startswith("CR-")]
    return get_next_id("CR-", ids)


def find_change_request_by_source(items: list[dict[str, Any]], source_url: str) -> str | None:
    """Find an existing CR that references an external source URL."""
    for item in items:
        description = str(item.get("description") or "")
        if source_url and source_url in description:
            return item.get("id")
    return None


def build_change_request_data(request: ExternalChangeRequest) -> dict[str, Any]:
    """Build canonical DHF CR item data from an external request."""
    return {
        "type": "CR",
        "title": request.title,
        "description": f"{request.description}\n\nSource issue: {request.source_url}".strip(),
        "justification": request.justification,
        "priority": request.priority,
        "requested_by": request.requested_by,
        "target_version": request.target_version,
        "category": request.category,
        "content": request.content,
    }


def prepare_change_request(
    request: ExternalChangeRequest,
    adapter: ChangeRequestAdapter,
    *,
    write: bool,
    known_cr_id: str | None = None,
    branch_prefix: str = "cr",
    title_prefix: str = "cr",
    source_label: str = "source",
    author: str = "issue-to-cr",
) -> ChangeRequestPreparation:
    """Prepare or create a DHF CR for an external change request."""
    all_cr_items = adapter.list_items("CR")

    if known_cr_id and adapter.get_item(known_cr_id):
        return ChangeRequestPreparation(False, "existing CR marker found", cr_id=known_cr_id)

    existing_cr_id = find_change_request_by_source(all_cr_items, request.source_url)
    if existing_cr_id:
        return ChangeRequestPreparation(False, "source request already has CR", cr_id=existing_cr_id)

    if write:
        created = adapter.create_item(build_change_request_data(request), author=author)
        cr_id = str(created["id"])
    else:
        cr_id = next_change_request_id(all_cr_items)

    slug = _slugify(request.title)
    source_suffix = f"-from-{source_label}-{request.source_number}" if request.source_number is not None else ""
    branch = f"{branch_prefix}/{cr_id}{source_suffix}-{slug}"
    return ChangeRequestPreparation(
        True,
        "created" if write else "dry-run",
        cr_id=cr_id,
        branch=branch,
        cr_path=f"DHF/items/06_cr/{cr_id}.yaml",
        title=f"{title_prefix}({cr_id}): {request.title}",
    )


def complete_change_request(
    adapter: ChangeRequestAdapter,
    cr_id: str,
    *,
    performed_by: str,
) -> dict[str, Any]:
    """Transition a DHF CR to completed."""
    existing = adapter.get_item(cr_id)
    if existing is None:
        raise ValueError(f"CR '{cr_id}' not found.")
    return adapter.execute_transition(cr_id, "completed", performed_by=performed_by)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "change-request"
