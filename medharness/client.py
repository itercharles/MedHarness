"""DHFClient — direct Python API for DHF operations.

Wraps LocalDHFAdapter. Use this from product repos instead of shelling out to the CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dhfkit.local_adapter import LocalDHFAdapter


class DHFClient:
    """Direct Python API for DHF operations.

    Usage::

        from medharness.client import DHFClient

        client = DHFClient(Path("../WebTPS-DHF/DHF"))
        items = client.list_items(doc_type="CR")
        cr = client.get_item("CR-034")
        spec = client.get_document("CR-034-Spec")
    """

    def __init__(self, dhf_path: Path):
        self._adapter = LocalDHFAdapter(dhf_path)

    # -- Item CRUD ---------------------------------------------------------

    def list_items(self, doc_type: str | None = None) -> list[dict[str, Any]]:
        return self._adapter.list_items(doc_type)

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        return self._adapter.get_item(item_id)

    def create_item(
        self, doc_type: str, data: dict[str, Any], *,
        author: str = "system", cr_id: str | None = None,
    ) -> dict[str, Any]:
        data = {**data, "type": doc_type}
        return self._adapter.create_item(data, author=author, cr_id=cr_id)

    def update_item(
        self, item_id: str, data: dict[str, Any], *,
        author: str = "system", cr_id: str | None = None,
    ) -> dict[str, Any] | None:
        return self._adapter.update_item(item_id, data, author=author, cr_id=cr_id)

    def transition_item(
        self, item_id: str, to_state: str, *, performed_by: str,
    ) -> dict[str, Any]:
        return self._adapter.execute_transition(item_id, to_state, performed_by=performed_by)

    # -- Documents ----------------------------------------------------------

    def get_document(self, doc_id: str) -> str | None:
        return self._adapter.get_document(doc_id)

    # -- CR context ---------------------------------------------------------

    def get_cr_context(self, cr_id: str) -> dict[str, Any]:
        cr = self._adapter.get_item(cr_id)
        spec = self._adapter.get_document(f"{cr_id}-Spec")
        return {
            "cr": cr if cr is not None else {"id": cr_id, "found": False},
            "spec": spec or "",
        }
