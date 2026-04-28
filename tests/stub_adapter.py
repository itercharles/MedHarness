"""
StubDHFAdapter — in-memory DHFAdapter for compliantflow unit tests.

Implements the full DHFAdapter protocol with no filesystem or utils dependency.
Use build_test_adapter() from tests/fixtures/test_data.py for a pre-populated instance.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from compliantflow.domain.schema import (
    GlobalLifecycle,
    ItemTypeSchema,
    LifecycleStateInfo,
    ProjectSchema,
)


def _default_schema() -> ProjectSchema:
    global_lifecycle = GlobalLifecycle(
        states=[
            LifecycleStateInfo(id="draft", label="Draft"),
            LifecycleStateInfo(id="under_review", label="Under Review"),
            LifecycleStateInfo(id="approved", label="Approved", is_stable=True),
            LifecycleStateInfo(id="rejected", label="Rejected", is_stable=True),
        ]
    )
    item_types = [
        ItemTypeSchema(name="UC", id_prefix="UC-", parent_types=[]),
        ItemTypeSchema(name="CRS", id_prefix="CRS-", parent_types=["UC"]),
        ItemTypeSchema(name="SYS", id_prefix="SYS-", parent_types=["CRS"], has_verification=True),
        ItemTypeSchema(name="SRS", id_prefix="SRS-", parent_types=["SYS"]),
        ItemTypeSchema(name="SYSARCH", id_prefix="SYSARCH-", parent_types=["SYS"]),
        ItemTypeSchema(name="RISK", id_prefix="RISK-", parent_types=[]),
        ItemTypeSchema(name="RCM", id_prefix="RCM-", parent_types=["RISK"]),
        ItemTypeSchema(name="REL", id_prefix="REL-", parent_types=[]),
        ItemTypeSchema(name="DEF", id_prefix="DEF-", parent_types=[]),
        ItemTypeSchema(name="CR", id_prefix="CR-", parent_types=[]),
        ItemTypeSchema(name="TC", id_prefix="TC-", parent_types=[]),
    ]
    return ProjectSchema(item_types=item_types, global_lifecycle=global_lifecycle)


class StubDHFAdapter:
    """In-memory DHFAdapter implementation for testing.

    Implements all 14 DHFAdapter protocol methods without any filesystem
    or utils dependency. Items are stored in a plain dict keyed by ID.
    """

    def __init__(self) -> None:
        self._items: Dict[str, dict] = {}
        self._documents: Dict[str, str] = {}
        self._test_results: Dict[str, dict] = {}
        self._compliance_runs: Dict[str, List[dict]] = {}
        self._schema: ProjectSchema = _default_schema()

    # ------------------------------------------------------------------
    # Item CRUD
    # ------------------------------------------------------------------

    def get_item(self, uid: str) -> Optional[dict]:
        return self._items.get(uid)

    # Relationship fields that contribute to graph edges (mirrors DHF Item.all_links).
    _LINK_FIELDS = (
        "derives_from", "implements", "guided_by", "informs", "design",
        "mitigates", "satisfies", "verifies", "validates",
    )

    def list_items(self, doc_type: Optional[str] = None) -> List[dict]:
        items = list(self._items.values())
        if doc_type:
            prefix = f"{doc_type}-"
            items = [i for i in items if i.get("id", "").startswith(prefix)]
        return [self._with_linked_uids(i) for i in items]

    def _with_linked_uids(self, item: dict) -> dict:
        """Return a copy of item with all_linked_uids computed from relationship fields."""
        all_uids: set = set()
        for field in self._LINK_FIELDS:
            val = item.get(field)
            if isinstance(val, list):
                all_uids.update(val)
        return {**item, "all_linked_uids": sorted(all_uids)}

    def create_item(self, data: dict, author: str = "system", cr_id: Optional[str] = None) -> dict:
        if "id" in data:
            item_id = data["id"]
        elif "type" in data:
            item_id = self._next_id(data["type"])
        else:
            raise ValueError("create_item requires either 'id' or 'type' in data")
        result = {**data, "id": item_id}
        self._items[item_id] = result
        return result

    def update_item(
        self,
        uid: str,
        data: dict,
        author: Optional[str] = None,
        cr_id: Optional[str] = None,
    ) -> Optional[dict]:
        if uid not in self._items:
            return None
        updated = {**self._items[uid], **data, "id": uid}
        self._items[uid] = updated
        return updated

    def delete_item(self, uid: str, author: Optional[str] = None) -> bool:
        if uid in self._items:
            del self._items[uid]
            return True
        return False

    def execute_transition(
        self,
        item_id: str,
        to_state: str,
        performed_by: Optional[str] = None,
    ) -> dict:
        if item_id not in self._items:
            raise ValueError(f"Item not found: {item_id}")
        self._items[item_id] = {
            **self._items[item_id],
            "status": to_state,
            f"{to_state}_by": performed_by,
        }
        return self._items[item_id]

    # ------------------------------------------------------------------
    # Schema / config
    # ------------------------------------------------------------------

    def validate_schema(self) -> dict:
        return {"valid": True, "errors": []}

    def get_project_config(self) -> ProjectSchema:
        return self._schema

    # ------------------------------------------------------------------
    # Test results
    # ------------------------------------------------------------------

    def get_test_result(self, tc_id: str) -> Optional[dict]:
        return self._test_results.get(tc_id)

    def get_all_test_results(self, status_filter: Optional[str] = None) -> Dict[str, dict]:
        if status_filter:
            return {k: v for k, v in self._test_results.items()
                    if v.get("testing_status") == status_filter}
        return dict(self._test_results)

    def get_test_result_items(self) -> List[dict]:
        return list(self._test_results.values())

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def get_document(self, doc_id: str) -> Optional[str]:
        return self._documents.get(doc_id)

    def list_documents(self) -> List[str]:
        return list(self._documents.keys())

    def get_implementation_context(self, cr_id: str) -> dict:
        return {
            "cr": self.get_item(cr_id),
            "implementation_spec": self.get_document(f"{cr_id}-Spec"),
            "dhf_references": [cr_id, f"{cr_id}-Spec"],
        }

    # ------------------------------------------------------------------
    # Compliance runs
    # ------------------------------------------------------------------

    def record_compliance_run(
        self,
        group_id: str,
        report_dict: dict,
        commit_sha: str = "",
        trigger: str = "manual",
    ) -> None:
        if group_id not in self._compliance_runs:
            self._compliance_runs[group_id] = []
        self._compliance_runs[group_id].append({
            **report_dict,
            "group_id": group_id,
            "commit_sha": commit_sha,
            "trigger": trigger,
        })

    def get_compliance_runs(
        self,
        group_id: str,
        since_date: Optional[str] = None,
    ) -> List[Dict]:
        return list(self._compliance_runs.get(group_id, []))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_id(self, type_prefix: str) -> str:
        """Auto-generate the next available ID for a given type prefix."""
        n = 1
        while f"{type_prefix}-{n:03d}" in self._items:
            n += 1
        return f"{type_prefix}-{n:03d}"
