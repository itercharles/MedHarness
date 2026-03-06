"""CompliantFlow product facade.

This module is the single entry point for all business logic.
It composes infrastructure layers via Mixin classes and exposes a unified API
to the CLI and Streamlit UI.

The core accepts a DHFAdapter (default: LocalDHFAdapter) so any backend
implementing the protocol can plug in.
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

    def __init__(
        self,
        dhf_root: Optional[Path] = None,
        auto_commit: bool = False,
        adapter=None,
    ):
        """
        Initialize CompliantFlow core.

        Args:
            dhf_root: Path to the DHF directory (used when adapter is None).
            auto_commit: Whether to auto-commit changes (used when adapter is None).
            adapter: Optional DHFAdapter instance. If provided, dhf_root is ignored.
        """
        if adapter is None:
            from compliantflow.adapters.local import LocalDHFAdapter
            if dhf_root is None:
                raise ValueError("Either dhf_root or adapter must be provided")
            adapter = LocalDHFAdapter(Path(dhf_root), auto_commit=auto_commit)

        self._adapter = adapter
        self.config: ProjectConfig = adapter.get_project_config()
        self.graph = GraphEngine(config=self.config)

        # Keep repo_root for compliance engine file existence checks
        if dhf_root is not None:
            self.repo_root = Path(dhf_root)
        elif hasattr(adapter, '_dhf_root'):
            self.repo_root = adapter._dhf_root
        else:
            self.repo_root = Path(".")

        self.refresh()

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
