"""Generic traceable artifact model."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class Item(BaseModel):
    """A generic traceable item from any DHF backend.

    ``type`` is a domain-level name supplied by the adapter
    (e.g. ``"system_requirement"``, ``"risk"``, ``"test_case"``).
    Multi-level hierarchies are captured through ``all_linked_uids``
    and the graph — no specialised sub-class is needed.

    ``attributes`` holds any DHF-specific extra fields that compliantflow
    does not need to understand natively.
    """

    id: str
    type: str
    title: str = ""
    status: Optional[str] = None
    all_linked_uids: List[str] = []
    attributes: Dict[str, Any] = {}
