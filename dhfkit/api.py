"""dhfkit API — reusable Python functions for DHF operations.

All functions accept a DHF root path and return structured data.
No Click, no stdout/stderr, no CLI concerns.
"""

from pathlib import Path
from typing import Optional

from dhfkit.local_adapter import LocalDHFAdapter


def _adapter(dhf_root: Path) -> LocalDHFAdapter:
    return LocalDHFAdapter(dhf_root, auto_commit=False)


# -- Item operations ----------------------------------------------------------

def get_item(dhf_root: Path, item_id: str) -> Optional[dict]:
    return _adapter(dhf_root).get_item(item_id)


def list_items(dhf_root: Path, doc_type: Optional[str] = None) -> list[dict]:
    return _adapter(dhf_root).list_items(doc_type)


def create_item(dhf_root: Path, data: dict, author: str = "system",
                cr_id: Optional[str] = None) -> dict:
    return _adapter(dhf_root).create_item(data, author=author, cr_id=cr_id)


def update_item(dhf_root: Path, item_id: str, data: dict,
                author: Optional[str] = None,
                cr_id: Optional[str] = None) -> Optional[dict]:
    return _adapter(dhf_root).update_item(item_id, data, author=author, cr_id=cr_id)


def delete_item(dhf_root: Path, item_id: str, author: Optional[str] = None) -> bool:
    return _adapter(dhf_root).delete_item(item_id, author=author)


def get_item_transitions(dhf_root: Path, item_id: str) -> list[dict]:
    return _adapter(dhf_root).get_available_transitions(item_id)


def transition_item(dhf_root: Path, item_id: str, to_state: str,
                    performed_by: Optional[str] = None) -> dict:
    return _adapter(dhf_root).execute_transition(item_id, to_state, performed_by=performed_by)


# -- Validation operations ----------------------------------------------------

def validate_schema(dhf_root: Path) -> dict:
    return _adapter(dhf_root).validate_schema()


def validate_traceability(dhf_root: Path) -> dict:
    return _adapter(dhf_root).validate_traceability()


# -- Document operations ------------------------------------------------------

def list_doc_types(dhf_root: Path) -> list[str]:
    return _adapter(dhf_root).get_available_doc_types()


def generate_doc(dhf_root: Path, doc_type_code: str) -> dict:
    return _adapter(dhf_root).generate_doc(doc_type_code)


def export_pdf(dhf_root: Path, doc_type_code: str) -> dict:
    return _adapter(dhf_root).export_pdf(doc_type_code)


# -- Test result operations ---------------------------------------------------

def get_test_status(dhf_root: Path, tc_id: str) -> Optional[dict]:
    return _adapter(dhf_root).get_test_result(tc_id)


def list_test_results(dhf_root: Path, status_filter: Optional[str] = None) -> dict[str, dict]:
    return _adapter(dhf_root).get_all_test_results(status_filter)


# -- Config operations --------------------------------------------------------

def list_doc_type_configs(dhf_root: Path) -> list[dict]:
    return _adapter(dhf_root).list_item_types()
