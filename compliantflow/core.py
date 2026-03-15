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

from compliantflow.domain.schema import ProjectSchema
from compliantflow.graph import GraphEngine

from compliantflow.mixins.lifecycle import _LifecycleMixin
from compliantflow.mixins.item_crud import _ItemCRUDMixin
from compliantflow.mixins.traceability import _TraceabilityMixin
from compliantflow.mixins.schema_form import _SchemaFormMixin
from compliantflow.mixins.compliance import _ComplianceMixin


class CompliantFlowCore(
    _LifecycleMixin,
    _ItemCRUDMixin,
    _TraceabilityMixin,
    _SchemaFormMixin,
    _ComplianceMixin,
):
    """
    Core CompliantFlow library.

    Provides a unified interface for traceability analysis, compliance checking,
    lifecycle management, and test result tracking.
    """

    def __init__(self, adapter):
        """
        Initialize CompliantFlow core.

        Args:
            adapter: A DHFAdapter instance. Use LocalDHFAdapter from
                     utils.local_adapter (DHF layer) or any custom implementation.
        """
        self._adapter = adapter
        self.config: ProjectSchema = adapter.get_project_config()
        self.graph = GraphEngine(config=self.config)

        # Keep repo_root for compliance engine file existence checks.
        # Resolved from the adapter; falls back to CWD for custom adapters.
        if hasattr(adapter, '_dhf_root'):
            self.repo_root = adapter._dhf_root
        else:
            self.repo_root = Path(".")

        self.refresh()

    def refresh(self):
        """Reload all items, rebuild graph, and recompute verification status."""
        raw_items = self._adapter.list_items()
        tc_items = self._adapter.get_test_result_items()
        self.graph.build_from_items(raw_items + tc_items)
        self._refresh_verification_status()

    def get_config(self) -> Optional[Dict[str, Any]]:
        """Get project configuration."""
        if not self.config:
            return None
        return self.config.model_dump()

    # ------------------------------------------------------------------
    # Verification status computation (derived, in-memory only)
    # ------------------------------------------------------------------

    def _refresh_verification_status(self) -> None:
        """Recompute verification_status in-memory for all verifiable graph nodes."""
        all_results = self._adapter.get_all_test_results()
        if not all_results:
            return
        verifiable_ids = {
            node_id
            for node_id in self.graph.graph.nodes
            if self.config and (
                cfg := self.config.get_type_by_prefix(node_id.split("-")[0] + "-")
            ) and cfg.has_verification
        }
        self._inject_verification_status(verifiable_ids)

    def _inject_verification_status(self, item_ids: set) -> None:
        """Compute verification_status from test results and update graph nodes in-memory."""
        all_results = self._adapter.get_all_test_results()
        for item_id in item_ids:
            if not self.graph.graph.has_node(item_id):
                continue
            prefix = item_id.split("-")[0] + "-"
            doc_type_cfg = self.config.get_type_by_prefix(prefix) if self.config else None
            if not doc_type_cfg or not doc_type_cfg.has_verification:
                continue
            linked = [
                rec for rec in all_results.values()
                if item_id in (rec.get("links") or [])
                and rec.get("testing_status") in ("PASS", "FAIL")
            ]
            if not linked:
                new_status = "not_verified"
            elif any(r["testing_status"] == "FAIL" for r in linked):
                new_status = "failed"
            else:
                new_status = "verified"
            self.graph.graph.nodes[item_id]["item"]["verification_status"] = new_status
