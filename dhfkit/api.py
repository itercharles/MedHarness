"""dhfkit API — reusable Python functions for DHF operations.

All functions accept a DHF root path and return structured data.
No Click, no stdout/stderr, no CLI concerns.
"""

from pathlib import Path
from typing import Optional

from dhfkit.local_adapter import LocalDHFAdapter


def _adapter(dhf_root: Path) -> LocalDHFAdapter:
    return LocalDHFAdapter(dhf_root)


# -- Item operations ----------------------------------------------------------

def get_item(dhf_root: Path, item_id: str) -> Optional[dict]:
    return _adapter(dhf_root).get_item(item_id)


def list_items(dhf_root: Path, doc_type: Optional[str] = None) -> list[dict]:
    return _adapter(dhf_root).list_items(doc_type)


def create_item(dhf_root: Path, data: dict) -> dict:
    return _adapter(dhf_root).create_item(data)


def update_item(dhf_root: Path, item_id: str, data: dict) -> Optional[dict]:
    return _adapter(dhf_root).update_item(item_id, data)


def delete_item(dhf_root: Path, item_id: str) -> bool:
    return _adapter(dhf_root).delete_item(item_id)


def get_item_transitions(dhf_root: Path, item_id: str) -> list[dict]:
    return _adapter(dhf_root).get_available_transitions(item_id)


def transition_item(dhf_root: Path, item_id: str, to_state: str) -> dict:
    return _adapter(dhf_root).execute_transition(item_id, to_state)


# -- Validation operations ----------------------------------------------------

def validate_schema(dhf_root: Path) -> dict:
    return _adapter(dhf_root).validate_schema()




# -- Document operations ------------------------------------------------------

def list_doc_types(dhf_root: Path) -> list[str]:
    return _adapter(dhf_root).get_available_doc_types()


def generate_doc(dhf_root: Path, doc_type_code: str) -> dict:
    return _adapter(dhf_root).generate_doc(doc_type_code)


def export_pdf(dhf_root: Path, doc_type_code: str) -> dict:
    return _adapter(dhf_root).export_pdf(doc_type_code)


# -- Config operations --------------------------------------------------------

def get_config(dhf_root: Path):
    """The project's configuration — safety class, doc types, traceability rules.

    `medharness` read `adapter._config` in ten places: a private attribute of a
    `dhfkit` class, reached across the package boundary. `dhfkit` is meant to be
    usable standalone, which means it has a public surface, and a consumer
    pinned to an underscore has no contract at all.
    """
    return _adapter(dhf_root)._config


def list_doc_type_configs(dhf_root: Path) -> list[dict]:
    return _adapter(dhf_root).list_item_types()
