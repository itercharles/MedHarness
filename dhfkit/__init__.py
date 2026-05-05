"""dhfkit — standalone data-layer package for DHF repositories.

Public API
----------
Shared data types (safe to import anywhere):
    Item, ProjectConfig, DocTypeConfig, ValidationError

DHF I/O utilities (for direct DHF-layer consumers such as tests and adapters):
    ItemLoader, ResultStore, parse_junit_xml, ExecutionResult

Internal (not part of the public API):
    ItemSaver, GitRepository, DocumentGenerator
    — these are implementation details of the adapter layer.
"""

from dhfkit.models.item import Item
from dhfkit.models.config import ProjectConfig, DocTypeConfig
from dhfkit.exceptions import ValidationError
from dhfkit.result_store import ResultStore
from dhfkit.junit_parser import parse_junit_xml, ExecutionResult
from dhfkit.repository.loader import ItemLoader
from dhfkit.artifact_fetcher import GitHubArtifactFetcher
from dhfkit.local_adapter import LocalDHFAdapter

__all__ = [
    "Item",
    "ProjectConfig",
    "DocTypeConfig",
    "ValidationError",
    "ResultStore",
    "parse_junit_xml",
    "ExecutionResult",
    "ItemLoader",
    "GitHubArtifactFetcher",
    "LocalDHFAdapter",
]
