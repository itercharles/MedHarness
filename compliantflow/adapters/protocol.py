"""DHFAdapter Protocol — defines the interface between CompliantFlow and any DHF backend."""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol, runtime_checkable

from compliantflow.domain.schema import ProjectSchema


@runtime_checkable
class DHFAdapter(Protocol):
    """Protocol that any DHF backend must implement to plug into CompliantFlow."""

    def get_item(self, uid: str) -> Optional[dict]: ...
    def list_items(self, doc_type: Optional[str] = None) -> List[dict]: ...
    def create_item(
        self,
        data: dict,
        author: str = "system",
        cr_id: Optional[str] = None,
    ) -> dict: ...
    def update_item(
        self,
        uid: str,
        data: dict,
        author: Optional[str] = None,
        cr_id: Optional[str] = None,
    ) -> Optional[dict]: ...
    def delete_item(self, uid: str, author: Optional[str] = None) -> bool: ...
    def execute_transition(
        self,
        item_id: str,
        to_state: str,
        performed_by: Optional[str] = None,
    ) -> dict: ...
    def validate_schema(self) -> dict: ...
    def get_project_config(self) -> ProjectSchema: ...
    def get_test_result(self, tc_id: str) -> Optional[dict]: ...
    def get_all_test_results(self, status_filter: Optional[str] = None) -> Dict[str, dict]: ...
    def get_test_result_items(self) -> List[dict]: ...
    def get_document(self, doc_id: str) -> Optional[str]: ...
    def list_documents(self) -> List[str]: ...
    def get_implementation_context(self, cr_id: str) -> dict: ...
    def record_compliance_run(
        self,
        group_id: str,
        report_dict: dict,
        commit_sha: str = "",
        trigger: str = "manual",
    ) -> None: ...
    def get_compliance_runs(
        self,
        group_id: str,
        since_date: Optional[str] = None,
    ) -> List[Dict]: ...
