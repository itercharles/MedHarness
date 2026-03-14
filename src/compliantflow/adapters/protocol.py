"""DHFAdapter Protocol — defines the interface between CompliantFlow and any DHF backend."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Protocol, runtime_checkable

from utils.models.config import ProjectConfig


@runtime_checkable
class DHFAdapter(Protocol):
    """Protocol that any DHF backend must implement to plug into CompliantFlow."""

    def get_item(self, uid: str) -> Optional[dict]: ...
    def list_items(self, doc_type: Optional[str] = None) -> List[dict]: ...
    def create_item(self, data: dict, author: str = "system") -> dict: ...
    def update_item(self, uid: str, data: dict, author: Optional[str] = None) -> Optional[dict]: ...
    def delete_item(self, uid: str, author: Optional[str] = None) -> bool: ...
    def validate_schema(self) -> dict: ...
    def get_project_config(self) -> ProjectConfig: ...
    def get_available_doc_types(self) -> List[str]: ...
    def generate_doc(self, doc_type_code: str) -> dict: ...
    def export_pdf(self, doc_type_code: str) -> dict: ...
    def get_test_result(self, tc_id: str) -> Optional[dict]: ...
    def get_all_test_results(self, status_filter: Optional[str] = None) -> Dict[str, dict]: ...
    def record_test_result(
        self,
        tc_id: str,
        testing_status: str,
        tester: str = "",
        run_id: str = "",
        run_url: str = "",
        commit_sha: str = "",
        notes: str = "",
        links: Optional[List[str]] = None,
        title: str = "",
        reviewer: str = "",
        review_date: str = "",
        review_status: str = "",
    ) -> None: ...
    def get_test_result_items(self) -> List[dict]: ...
    def import_results_from_file(
        self,
        xml_path: Path,
        tester: str = "",
        run_id: str = "",
        run_url: str = "",
        commit_sha: str = "",
    ) -> dict: ...
    def pull_results_from_artifacts(
        self,
        run_id: str = "",
        commit_sha: str = "",
    ) -> dict: ...
