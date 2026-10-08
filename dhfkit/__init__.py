"""dhfkit — standalone data-layer package for DHF repositories.

Public API
----------
Shared data types (safe to import anywhere):
    Item, ProjectConfig, DocTypeConfig, ValidationError

DHF I/O utilities (for direct DHF-layer consumers such as tests and adapters):
    ItemLoader

Internal (not part of the public API):
    ItemSaver, DocumentGenerator
    — these are implementation details of the adapter layer.
"""

from dhfkit.models.item import Item
from dhfkit.models.config import ProjectConfig, DocTypeConfig
from dhfkit.exceptions import ValidationError
from dhfkit.repository.loader import ItemLoader
from dhfkit.item_store import ItemStore

__all__ = [
    "Item",
    "ProjectConfig",
    "DocTypeConfig",
    "ValidationError",
    "ItemLoader",
    "ItemStore",
]
