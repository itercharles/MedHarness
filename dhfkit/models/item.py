"""Pydantic v2 models for MedHarness items."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import date
from enum import Enum


class VerificationStatus(str, Enum):
    """Verification status for items."""
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"


class Item(BaseModel):
    """
    Core item model - similar to Doorstop but with medical device extensions.

    This model uses Pydantic v2 for type safety and validation.
    Extra fields are allowed to support custom properties per document type.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='allow',  # Allow custom fields for flexibility
        populate_by_name=True,
    )

    # Core fields (Doorstop-inspired)
    uid: str = Field(..., description="Unique identifier", alias="id")
    # Typed relationship fields (preserve semantic meaning)
    derives_from: Optional[List[str]] = Field(default=None, description="Items this derives from")
    implements: Optional[List[str]] = Field(default=None, description="Items this implements")
    guided_by: Optional[List[str]] = Field(default=None, description="Items that guide this")
    informs: Optional[List[str]] = Field(default=None, description="Items this informs")
    design: Optional[List[str]] = Field(default=None, description="Items this designs/addresses")
    mitigated_by: Optional[List[str]] = Field(default=None, description="Items that mitigate this")
    mitigates: Optional[List[str]] = Field(default=None, description="Items this mitigates")
    satisfies: Optional[List[str]] = Field(default=None, description="Items this satisfies")
    verifies: Optional[List[str]] = Field(default=None, description="Items this verifies")
    validates: Optional[List[str]] = Field(default=None, description="Items this validates")

    # Common fields
    title: Optional[str] = Field(None, description="Item title")
    reviewer: Optional[str] = Field(None, description="Reviewer name")
    review_date: Optional[date] = Field(None, description="Review date")

    # Verification — accepts both TC-level (PASS/FAIL/PENDING) and
    # requirement-level (verified/failed/not_verified) status strings.
    verification_status: Optional[str] = Field(None, description="Verification status")

    # History tracking
    history: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Change history")

    # Dynamic attributes are handled by model_config['extra'] = 'allow'
    # This allows any field defined in project_config.yaml to be stored on the item

    @property
    def all_links(self) -> Dict[str, List[str]]:
        """Get all relationships with their types."""
        return {
            'derives_from': self.derives_from or [],
            'implements': self.implements or [],
            'guided_by': self.guided_by or [],
            'informs': self.informs or [],
            'design': self.design or [],
            'mitigates': self.mitigates or [],
            'satisfies': self.satisfies or [],
            'verifies': self.verifies or [],
            'validates': self.validates or []
        }

    @property
    def all_linked_uids(self) -> List[str]:
        """Get flat list of all linked UIDs for graph traversal."""
        all_uids = set()
        for relationship_type, uids in self.all_links.items():
            all_uids.update(uids)
        return sorted(list(all_uids))

    @property
    def prefix(self) -> str:
        """Extract prefix from UID (e.g., 'SYS-' from 'SYS-001' or 'TC-VER-' from 'TC-VER-001')."""
        if '-' in self.uid:
            # Split by rightmost hyphen to separate number
            parts = self.uid.rsplit('-', 1)
            if len(parts) == 2:
                return parts[0] + '-'
        return ''

    def get_parent_uids(self) -> List[str]:
        """Get list of parent UIDs (all linked items)."""
        return self.all_linked_uids
