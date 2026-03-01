"""CompliantFlow product facade.

This module is the single entry point for all business logic.
It composes infrastructure layers (traceability/, graph/, repository/)
via Mixin classes and exposes a unified API to the CLI and Streamlit UI.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml

from traceability.models.config import ProjectConfig
from traceability.graph.engine import GraphEngine
from traceability.repository.loader import ItemLoader
from traceability.repository.saver import ItemSaver
from traceability.repository.git import GitRepository

from compliantflow.mixins.lifecycle import _LifecycleMixin
from compliantflow.mixins.item_crud import _ItemCRUDMixin
from compliantflow.mixins.traceability import _TraceabilityMixin
from compliantflow.mixins.change_request import _ChangeRequestMixin
from compliantflow.mixins.schema_form import _SchemaFormMixin
from compliantflow.mixins.compliance import _ComplianceMixin
from compliantflow.mixins.test_results_mixin import _TestResultsMixin


class CompliantFlowCore(
    _LifecycleMixin,
    _ItemCRUDMixin,
    _TraceabilityMixin,
    _ChangeRequestMixin,
    _SchemaFormMixin,
    _ComplianceMixin,
    _TestResultsMixin,
):
    """
    Core CompliantFlow library.

    Provides a unified interface for managing requirements traceability
    using Pydantic v2, NetworkX, and GitPython.
    """

    def __init__(self, repo_root: Path, auto_commit: bool = False):
        """
        Initialize CompliantFlow core.

        Args:
            repo_root: Path to repository root
            auto_commit: Whether to auto-commit changes
        """
        self.repo_root = Path(repo_root)
        self.specs_dir = self.repo_root / "items"
        self.config_path = self.repo_root / "config" / "project_config.yaml"

        self.config: Optional[ProjectConfig] = None
        self.git = GitRepository(self.repo_root, auto_commit=auto_commit)
        self.loader = ItemLoader(self.specs_dir)
        self.saver = ItemSaver(self.specs_dir, git_repo=self.git)
        self.graph = GraphEngine()

        self._load_config()
        self.refresh()
        self._init_result_store()

    def _init_result_store(self):
        """Initialize the external test result store."""
        from test_results.result_store import ResultStore
        raw_config: dict = {}
        try:
            with open(self.config_path, "r") as f:
                raw_config = yaml.safe_load(f) or {}
        except Exception:
            pass
        result_store_cfg = raw_config.get("test_integration", {}).get("result_store", {})
        self.result_store = ResultStore(self.repo_root, result_store_cfg)

    def _load_config(self):
        """Load project configuration."""
        if not self.config_path.exists():
            print(f"Warning: Config not found at {self.config_path}")
            return

        try:
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f)
            self.config = ProjectConfig.model_validate(data)
            self.graph.config = self.config
            self.saver.project_config = self.config
            self.loader.project_config = self.config
        except Exception as e:
            print(f"Error loading config: {e}")

    def refresh(self):
        """Reload all items and rebuild graph."""
        items = self.loader.load_all()
        self.graph.build_from_items(items)

    def get_config(self) -> Optional[Dict[str, Any]]:
        """Get project configuration."""
        if not self.config:
            return None
        return self.config.model_dump()

    def _aggregate_relationship_fields(self, item: Dict[str, Any], doc_type_code: str) -> List[str]:
        """
        Aggregate all relationship field values from an item.

        Args:
            item: Item dictionary
            doc_type_code: Document type code (e.g., 'SRS', 'TC-SRS')

        Returns:
            List of all linked item IDs from all relationship fields
        """
        all_links = []

        if doc_type_code.startswith('TC'):
            if 'verifies' in item:
                value = item['verifies']
                if isinstance(value, list):
                    all_links.extend([v for v in value if v])
                elif value:
                    all_links.append(value)
            return all_links

        doc_type_config = self.config.get_doc_type(doc_type_code)
        if not doc_type_config:
            return []

        properties = doc_type_config.properties if hasattr(doc_type_config, 'properties') else []
        for prop in properties:
            if isinstance(prop, dict):
                prop_format = prop.get('format')
                field_name = prop.get('name')
            elif hasattr(prop, 'format'):
                prop_format = prop.format
                field_name = prop.name
            else:
                continue

            if prop_format == 'relationship' and field_name in item:
                value = item[field_name]
                if isinstance(value, list):
                    all_links.extend([v for v in value if v])
                elif value:
                    all_links.append(value)

        return all_links
