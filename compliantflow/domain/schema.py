"""ProjectSchema — describes the structure of a connected DHF system.

All vocabulary here is compliantflow-domain: no mention of doc_types,
prefixes as implementation details, or any DHF-specific metadata.
The adapter is responsible for converting its native config into this schema.
"""

from typing import Any, List, Optional
from pydantic import BaseModel


class FieldSchema(BaseModel):
    """Describes a single field on an item type.

    Adapters populate this from the ``properties`` list in each
    ``DHF/config/doc_types/*.yaml`` file so that the analysis layer
    can describe and validate item fields without reaching into the
    utils layer.
    """

    name: str
    format: str = "short_text"
    label: str = ""
    required: bool = False
    options: List[str] = []
    default: Optional[Any] = None
    target_types: List[str] = []


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
    fields: List[FieldSchema] = []


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

    def get_fields(self, type_name: str) -> List[FieldSchema]:
        """Return the field definitions for the given item type name.

        Returns an empty list if the type is not found or has no fields.
        """
        t = self.get_type(type_name)
        if t is None:
            return []
        return t.fields
