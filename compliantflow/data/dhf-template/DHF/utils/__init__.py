"""DHF — standalone data-layer package for CompliantFlow.

Public API
----------
Shared data types (safe to import anywhere):
    Item, ProjectConfig, DocTypeConfig, ValidationError

DHF I/O utilities (for direct DHF-layer consumers such as tests/srs/ and adapters):
    ItemLoader, ResultStore, parse_junit_xml, ExecutionResult

Internal (not part of the public API):
    ItemSaver, GitRepository, DocumentGenerator
    — these are implementation details of the adapter layer.
"""

from utils.models.item import Item
from utils.models.config import ProjectConfig, DocTypeConfig
from utils.exceptions import ValidationError
from utils.result_store import ResultStore
from utils.junit_parser import parse_junit_xml, ExecutionResult
from utils.repository.loader import ItemLoader
from utils.artifact_fetcher import GitHubArtifactFetcher
from utils.local_adapter import LocalDHFAdapter

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
