"""The item store as the business layer sees it.

`medharness` depends on this interface and on `open_store`, never on the class
behind it, so what holds the items — YAML files today, another system through a
adapter (`dhfkit.adapter`) — is invisible to every check and build step.
`tests/guards/test_the_business_layer_sees_only_the_store_interface.py` holds
that line.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Protocol


class DHFStore(Protocol):
    @property
    def config(self) -> Any:
        """The project configuration: doc types, traceability rules, lifecycle."""

    @property
    def store_type(self) -> str:
        """The `type` in `store:` of global.yaml."""

    @property
    def tracks_files(self) -> bool:
        """Whether items are files in Git; what `verify changes` and the build stages read."""

    # items
    def get_item(self, uid: str) -> Optional[dict]: ...
    def list_items(self, doc_type: Optional[str] = None) -> list[dict]: ...
    def create_item(self, data: dict) -> dict: ...
    def update_item(self, uid: str, data: dict) -> Optional[dict]: ...
    def validate_schema(self) -> dict: ...

    # lifecycle
    def get_available_transitions(self, item_id: str) -> list[dict]: ...
    def unmet_criteria(self, item_id: str, to_state: str) -> list[dict]: ...
    def execute_transition(self, item_id: str, to_state: str) -> dict: ...
    def list_item_types(self) -> list[dict]: ...

    # documents
    def get_available_doc_types(self) -> list[str]: ...
    def render_spec(self, doc_type_code: str, fmt: str, out_dir: Path, version: str) -> dict: ...
    def get_document(self, doc_id: str) -> Optional[str]: ...
    def list_documents(self, category: Optional[str] = None) -> list[str]: ...
    def document_path(self, doc_id: str) -> Optional[Path]: ...


def open_store(dhf_root: Path) -> DHFStore:
    """The DHF at `dhf_root`, with its items in whatever adapter its config names."""
    from dhfkit.item_store import ItemStore

    return ItemStore(dhf_root)
