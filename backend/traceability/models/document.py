"""Document model for grouping items."""

from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
from .item import Item


class Document(BaseModel):
    """
    Collection of items forming a document.
    
    A document represents a logical grouping of items with the same prefix,
    typically stored in the same directory.
    """
    
    prefix: str = Field(..., description="Document prefix (e.g., 'SYS-')")
    name: str = Field(..., description="Document name (e.g., 'System Requirements')")
    parent: Optional[str] = Field(None, description="Parent document prefix")
    items: List[Item] = Field(default_factory=list, description="Items in this document")
    path: Optional[Path] = Field(None, description="Directory path for this document")
    
    def add_item(self, item: Item):
        """Add an item to this document."""
        if item.prefix == self.prefix:
            self.items.append(item)
        else:
            raise ValueError(f"Item {item.uid} does not match document prefix {self.prefix}")
    
    def get_item(self, uid: str) -> Optional[Item]:
        """Get an item by UID."""
        for item in self.items:
            if item.uid == uid:
                return item
        return None
    
    def remove_item(self, uid: str) -> bool:
        """Remove an item by UID. Returns True if removed."""
        for i, item in enumerate(self.items):
            if item.uid == uid:
                self.items.pop(i)
                return True
        return False
    
    @property
    def count(self) -> int:
        """Number of items in this document."""
        return len(self.items)
