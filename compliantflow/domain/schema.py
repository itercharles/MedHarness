"""ProjectSchema — describes the structure of a connected DHF system.

All vocabulary here is compliantflow-domain: no mention of doc_types,
prefixes as implementation details, or any DHF-specific metadata.
The adapter is responsible for converting its native config into this schema.
"""

from typing import List, Optional
from pydantic import BaseModel


class LifecycleStateInfo(BaseModel):
    """A single state in the global lifecycle state machine."""

    id: str
    label: str
    is_stable: bool = False
    action_label: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class GlobalLifecycle(BaseModel):
    """All states available across the project."""

    states: List[LifecycleStateInfo] = []


class ItemTypeSchema(BaseModel):
    """Describes one category of traceable items as seen by compliantflow.

    ``name``       — domain type name, e.g. ``"system_requirement"``.
                     Adapters that have no explicit mapping fall back to the
                     DHF doc-type code (e.g. ``"SYS"``), which keeps existing
                     test fixtures working unchanged.
    ``id_prefix``  — ID prefix used to identify items of this type (``"SYS-"``).
    ``parent_types`` — type names of items this type may derive from.
                       Enables multi-level hierarchies (sub-requirements, etc.)
                       without any changes to the engine.
    """

    name: str
    id_prefix: str
    parent_types: List[str] = []
    lifecycle: Optional[dict] = None
    has_verification: bool = False


class ProjectSchema(BaseModel):
    """Complete schema for the connected DHF system."""

    item_types: List[ItemTypeSchema] = []
    global_lifecycle: Optional[GlobalLifecycle] = None

    def get_type(self, name: str) -> Optional[ItemTypeSchema]:
        """Look up an item type by its domain name."""
        for t in self.item_types:
            if t.name == name:
                return t
        return None

    def get_type_by_prefix(self, prefix: str) -> Optional[ItemTypeSchema]:
        """Look up an item type by its ID prefix (e.g. ``"SYS-"``)."""
        for t in self.item_types:
            if t.id_prefix == prefix:
                return t
        return None
