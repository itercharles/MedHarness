"""Pydantic v2 models for CompliantFlow items."""

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
    text: str = Field(..., description="Main content", alias="content")
    links: List[str] = Field(default_factory=list, description="Links to parent items")
    active: bool = Field(default=True, description="Whether item is active")
    
    # Common fields
    title: Optional[str] = Field(None, description="Item title")
    reviewer: Optional[str] = Field(None, description="Reviewer name")
    review_date: Optional[date] = Field(None, description="Review date")
    
    # Verification
    verification_status: Optional[VerificationStatus] = Field(None, description="Verification status")
    
    # History tracking
    history: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Change history")
    
    # Dynamic attributes are handled by model_config['extra'] = 'allow'
    # This allows any field defined in project_config.yaml to be stored on the item

    
    @property
    def prefix(self) -> str:
        """Extract prefix from UID (e.g., 'SYS-' from 'SYS-001')."""
        if '-' in self.uid:
            return self.uid.split('-')[0] + '-'
        return ''
    
    def get_parent_uids(self) -> List[str]:
        """Get list of parent UIDs."""
        return self.links
    
    def add_link(self, parent_uid: str):
        """Add a link to a parent item."""
        if parent_uid not in self.links:
            self.links.append(parent_uid)
    
    def remove_link(self, parent_uid: str):
        """Remove a link to a parent item."""
        if parent_uid in self.links:
            self.links.remove(parent_uid)
