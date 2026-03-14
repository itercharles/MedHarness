"""CompliantFlow product facade.

This module is the single entry point for all business logic.
It composes infrastructure layers via Mixin classes and exposes a unified API
to the CLI and Streamlit UI.

The core accepts any DHFAdapter implementation — it has no knowledge of
LocalDHFAdapter or any other concrete adapter. The caller (CLI, tests, etc.)
is responsible for constructing and passing the adapter.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any

from utils.models.config import ProjectConfig
from utils.models.item import Item
from compliantflow.traceability.graph.engine import GraphEngine

from compliantflow.mixins.lifecycle import _LifecycleMixin
from compliantflow.mixins.item_crud import _ItemCRUDMixin
from compliantflow.mixins.traceability import _TraceabilityMixin
from compliantflow.mixins.change_request import _ChangeRequestMixin
from compliantflow.mixins.schema_form import _SchemaFormMixin
from compliantflow.mixins.compliance import _ComplianceMixin
from compliantflow.mixins.test_results_mixin import _TestResultsMixin
from compliantflow.mixins.document_generation_mixin import _DocumentGenerationMixin


class CompliantFlowCore(
    _LifecycleMixin,
    _ItemCRUDMixin,
    _TraceabilityMixin,
    _ChangeRequestMixin,
    _SchemaFormMixin,
    _ComplianceMixin,
    _TestResultsMixin,
    _DocumentGenerationMixin,
):
    """
    Core CompliantFlow library.

    Provides a unified interface for traceability analysis, compliance checking,
    lifecycle management, and document generation.
    """

    def __init__(self, adapter):
        """
        Initialize CompliantFlow core.

        Args:
            adapter: A DHFAdapter instance. Use LocalDHFAdapter from
                     utils.local_adapter (DHF layer) or any custom implementation.
        """
        self._adapter = adapter
        self.config: ProjectConfig = adapter.get_project_config()
        self.graph = GraphEngine(config=self.config)

        # Keep repo_root for compliance engine file existence checks.
        # Resolved from the adapter; falls back to CWD for custom adapters.
        if hasattr(adapter, '_dhf_root'):
            self.repo_root = adapter._dhf_root
        else:
            self.repo_root = Path(".")

        self.refresh()
        # Compute verification_status in-memory once on startup.
        # DHF auto-fetches from GitHub if no local cache is present (transparent).
        self._refresh_verification_status()

    def refresh(self):
        """Reload all items and rebuild graph."""
        raw_items = self._adapter.list_items()
        tc_items = self._adapter.get_test_result_items()

        all_items = []
        for d in raw_items:
            try:
                all_items.append(Item.model_validate(d))
            except Exception as e:
                print(f"Warning: could not parse item {d.get('id')}: {e}")

        for d in tc_items:
            try:
                all_items.append(Item.model_validate(d))
            except Exception as e:
                print(f"Warning: could not parse TC item {d.get('id')}: {e}")

        self.graph.build_from_items(all_items)

    def get_config(self) -> Optional[Dict[str, Any]]:
        """Get project configuration."""
        if not self.config:
            return None
        return self.config.model_dump()
