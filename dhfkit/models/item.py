"""Pydantic v2 models for MedHarness items."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date


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

    uid: str = Field(..., description="Unique identifier", alias="id")

    title: Optional[str] = Field(None, description="Item title")
    reviewer: Optional[str] = Field(None, description="Reviewer name")
    review_date: Optional[date] = Field(None, description="Review date")

    # Dynamic attributes are handled by model_config['extra'] = 'allow'
    # This allows any field defined in project_config.yaml to be stored on the item

    @property
    def prefix(self) -> str:
        """Extract prefix from UID (e.g., 'SYS-' from 'SYS-001' or 'TC-VER-' from 'TC-VER-001')."""
        if '-' in self.uid:
            # Split by rightmost hyphen to separate number
            parts = self.uid.rsplit('-', 1)
            if len(parts) == 2:
                return parts[0] + '-'
        return ''
