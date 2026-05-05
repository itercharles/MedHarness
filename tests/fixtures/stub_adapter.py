"""
StubDHFAdapter — in-memory DHFAdapter for medharness unit tests.

Implements the full DHFAdapter protocol with no filesystem or utils dependency.
Use build_test_adapter() from tests/fixtures/data.py for a pre-populated instance.
"""

from __future__ import annotations

from typing import Dict, List, Optional


def _default_item_types() -> list[dict]:
    return [
        {"name": "UC", "code": "UC", "prefix": "UC-", "parent_types": [], "has_verification": False, "lifecycle": None, "fields": []},
        {"name": "CRS", "code": "CRS", "prefix": "CRS-", "parent_types": ["UC"], "has_verification": False, "lifecycle": None, "fields": []},
        {"name": "SYS", "code": "SYS", "prefix": "SYS-", "parent_types": ["CRS"], "has_verification": True, "lifecycle": None, "fields": []},
        {"name": "SRS", "code": "SRS", "prefix": "SRS-", "parent_types": ["SYS"], "has_verification": False, "lifecycle": None, "fields": []},
        {"name": "SYSARCH", "code": "SYSARCH", "prefix": "SYSARCH-", "parent_types": ["SYS"], "has_verification": False, "lifecycle": None, "fields": []},
        {"name": "RISK", "code": "RISK", "prefix": "RISK-", "parent_types": [], "has_verification": False, "lifecycle": None, "fields": []},
        {"name": "RCM", "code": "RCM", "prefix": "RCM-", "parent_types": ["RISK"], "has_verification": False, "lifecycle": None, "fields": []},
        {"name": "REL", "code": "REL", "prefix": "REL-", "parent_types": [], "has_verification": False, "lifecycle": None, "fields": []},
        {"name": "DEF", "code": "DEF", "prefix": "DEF-", "parent_types": [], "has_verification": False, "lifecycle": None, "fields": []},
        {"name": "CR", "code": "CR", "prefix": "CR-", "parent_types": [], "has_verification": False, "lifecycle": None, "fields": []},
        {"name": "TC", "code": "TC", "prefix": "TC-", "parent_types": [], "has_verification": False, "lifecycle": None, "fields": []},
    ]


def _default_lifecycle_states() -> list[dict]:
    return [
        {"id": "draft", "label": "Draft", "is_stable": False, "action_label": None, "icon": None, "color": None},
        {"id": "under_review", "label": "Under Review", "is_stable": False, "action_label": None, "icon": None, "color": None},
        {"id": "approved", "label": "Approved", "is_stable": True, "action_label": None, "icon": None, "color": None},
        {"id": "rejected", "label": "Rejected", "is_stable": True, "action_label": None, "icon": None, "color": None},
    ]


class StubDHFAdapter:
    """In-memory DHFAdapter implementation for testing."""

    def __init__(self) -> None:
        self._items: Dict[str, dict] = {}
        self._documents: Dict[str, str] = {}
        self._test_results: Dict[str, dict] = {}
        self._compliance_runs: Dict[str, List[dict]] = {}
        self._item_types: list[dict] = _default_item_types()
        self._lifecycle_states: list[dict] = _default_lifecycle_states()

    # ------------------------------------------------------------------
    # Item CRUD

    def get_item(self, uid: str) -> Optional[dict]:
        return self._items.get(uid)

    def list_items(self, doc_type: Optional[str] = None) -> List[dict]:
        items = list(self._items.values())
        if doc_type:
            prefix = f"{doc_type}-"
            items = [i for i in items if i["id"].startswith(prefix)]
        return items

    def create_item(self, data: dict, author: str = "system", cr_id: Optional[str] = None) -> dict:
        uid = data.get("id")
        if uid is None:
            prefix = f"{data.get('type', 'UNK')}-"
            uid = self._next_id(prefix)
            data = {**data, "id": uid}
        self._items[uid] = dict(data)
        _add_all_linked_uids(self._items[uid])
        return self._items[uid]

    def update_item(self, uid: str, data: dict, author: Optional[str] = None, cr_id: Optional[str] = None) -> Optional[dict]:
        if uid not in self._items:
            return None
        self._items[uid] = {**self._items[uid], **data}
        return self._items[uid]

    def delete_item(self, uid: str, author: Optional[str] = None) -> bool:
        if uid not in self._items:
            return False
        del self._items[uid]
        return True

    # ------------------------------------------------------------------
    # Lifecycle

    def get_available_transitions(self, item_id: str) -> List[Dict]:
        return []

    def execute_transition(self, item_id: str, to_state: str, performed_by: Optional[str] = None) -> dict:
        if item_id not in self._items:
            raise ValueError(f"Item not found: {item_id}")
        self._items[item_id] = {**self._items[item_id], "status": to_state, f"{to_state}_by": performed_by}
        return self._items[item_id]

    # ------------------------------------------------------------------
    # Item type metadata

    def get_item_type(self, prefix: str) -> Optional[dict]:
        for t in self._item_types:
            if t["prefix"] == prefix:
                return dict(t)
        return None

    def list_item_types(self) -> List[dict]:
        return [dict(t) for t in self._item_types]

    def get_lifecycle_states(self) -> List[dict]:
        return [dict(s) for s in self._lifecycle_states]

    # ------------------------------------------------------------------
    # Validation

    def validate_schema(self) -> dict:
        return {"valid": True, "errors": []}

    def validate_traceability(self) -> dict:
        return {"valid": True, "orphans": [], "gaps": []}

    # ------------------------------------------------------------------
    # Test results

    def get_test_result(self, tc_id: str) -> Optional[dict]:
        return self._test_results.get(tc_id)

    def get_all_test_results(self, status_filter: Optional[str] = None) -> Dict[str, dict]:
        if status_filter:
            return {k: v for k, v in self._test_results.items() if v.get("testing_status") == status_filter}
        return dict(self._test_results)

    def get_test_result_items(self) -> List[dict]:
        return list(self._test_results.values())

    def import_results_from_file(self, xml_path, tester: str = "", run_id: str = "",
                                  run_url: str = "", commit_sha: str = "") -> dict:
        return {"recorded": [], "skipped": 0}

    def record_test_result(self, tc_id: str, testing_status: str, tester: str = "",
                            run_id: str = "", run_url: str = "", commit_sha: str = "",
                            notes: str = "", links: Optional[List[str]] = None,
                            title: str = "", reviewer: str = "", review_date: str = "",
                            review_status: str = "") -> None:
        self._test_results[tc_id] = {"id": tc_id, "testing_status": testing_status}

    def pull_results_from_artifacts(self, run_id: str = "", commit_sha: str = "",
                                     provider: str = "github") -> dict:
        return {"recorded": [], "skipped": 0, "run_id": "", "run_url": ""}

    # ------------------------------------------------------------------
    # Documents

    def get_document(self, doc_id: str) -> Optional[str]:
        return self._documents.get(doc_id)

    def list_documents(self) -> List[str]:
        return list(self._documents.keys())

    def get_implementation_context(self, cr_id: str) -> dict:
        return {"cr": self.get_item(cr_id), "implementation_spec": None}

    # ------------------------------------------------------------------
    # Compliance runs (no-op)

    def record_compliance_run(self, group_id: str, report_dict: dict,
                               commit_sha: str = "", trigger: str = "manual") -> None:
        if group_id not in self._compliance_runs:
            self._compliance_runs[group_id] = []
        self._compliance_runs[group_id].append(dict(report_dict))

    def get_compliance_runs(self, group_id: str, since_date: Optional[str] = None) -> List[Dict]:
        return list(self._compliance_runs.get(group_id, []))

    def get_available_doc_types(self) -> List[str]:
        return ["SYS", "CRS", "SRS", "SWDD"]

    def generate_doc(self, doc_type_code: str) -> dict:
        return {"doc_type": doc_type_code, "output_path": f"/tmp/{doc_type_code}.md", "version": "1.0"}

    def export_pdf(self, doc_type_code: str) -> dict:
        return {"doc_type": doc_type_code, "pdf_path": f"/tmp/{doc_type_code}.pdf"}

    # ------------------------------------------------------------------
    # Internal

    def _next_id(self, type_prefix: str) -> str:
        n = 1
        while f"{type_prefix}-{n:03d}" in self._items:
            n += 1
        return f"{type_prefix}-{n:03d}"


def _add_all_linked_uids(item: dict) -> None:
    _LINK_FIELDS = ("derives_from", "implements", "mitigates", "satisfies", "guided_by", "informs", "design", "verifies", "validates")
    linked = []
    for field in _LINK_FIELDS:
        vals = item.get(field)
        if isinstance(vals, list):
            linked.extend(vals)
    item["all_linked_uids"] = linked
