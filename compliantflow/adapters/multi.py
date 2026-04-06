"""MultiDHFAdapter — routes DHFAdapter calls across multiple named DHF projects.

Items returned from cross-project queries have their IDs namespaced as
``slug::original-id`` so callers can identify which project each item belongs
to and route follow-up calls back to the correct adapter.

Usage::

    from utils.local_adapter import LocalDHFAdapter
    from compliantflow.adapters.multi import MultiDHFAdapter
    from compliantflow.core import CompliantFlowCore

    adapters = {
        "device-a": LocalDHFAdapter(Path("/repo/device-a/DHF"), auto_commit=False),
        "device-b": LocalDHFAdapter(Path("/repo/device-b/DHF"), auto_commit=False),
    }
    core = CompliantFlowCore(MultiDHFAdapter(adapters))
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class MultiDHFAdapter:
    """Aggregates multiple DHFAdapter instances behind the DHFAdapter interface.

    Each project is identified by a short slug (e.g. ``"device-a"``).  IDs
    returned from aggregate operations are prefixed ``slug::id`` so downstream
    callers can route follow-up calls unambiguously.

    The *primary* project (first entry in ``adapters``) is used for operations
    that return a single value (``get_project_config``, ``record_compliance_run``,
    ``get_compliance_runs``).  Mutations (``create_item``, ``update_item``,
    ``delete_item``) are routed to whichever project the namespaced UID points
    to; un-namespaced UIDs go to the primary project.
    """

    SEP = "::"

    def __init__(self, adapters: Dict[str, Any]) -> None:
        if not adapters:
            raise ValueError("MultiDHFAdapter requires at least one adapter.")
        self._adapters: Dict[str, Any] = dict(adapters)
        self._primary_slug: str = next(iter(self._adapters))
        self._primary: Any = self._adapters[self._primary_slug]

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------

    # Fields that contain UIDs referencing other items within the same project.
    # These must also be namespaced so the graph engine can resolve edges.
    _LINK_FIELDS = ("all_linked_uids", "satisfies", "derives_from", "affected_items")

    def _namespace(self, slug: str, item: dict) -> dict:
        """Return a copy of *item* with its ``id`` and all intra-project link
        fields prefixed by ``slug::``."""
        result = dict(item)
        if "id" in result:
            result["id"] = f"{slug}{self.SEP}{result['id']}"
        for field in self._LINK_FIELDS:
            if field in result and isinstance(result[field], list):
                result[field] = [
                    f"{slug}{self.SEP}{uid}" if self.SEP not in str(uid) else uid
                    for uid in result[field]
                ]
        return result

    def _route(self, uid: str):
        """Return ``(slug, bare_id, adapter)`` for a possibly-namespaced *uid*."""
        if self.SEP in uid:
            slug, bare = uid.split(self.SEP, 1)
            adapter = self._adapters.get(slug)
            if adapter is None:
                raise KeyError(f"Unknown project slug: {slug!r}")
            return slug, bare, adapter
        return self._primary_slug, uid, self._primary

    # ------------------------------------------------------------------
    # DHFAdapter protocol implementation
    # ------------------------------------------------------------------

    def get_item(self, uid: str) -> Optional[dict]:
        slug, bare_id, adapter = self._route(uid)
        item = adapter.get_item(bare_id)
        return self._namespace(slug, item) if item is not None else None

    def list_items(self, doc_type: Optional[str] = None) -> List[dict]:
        result: List[dict] = []
        for slug, adapter in self._adapters.items():
            for item in adapter.list_items(doc_type):
                result.append(self._namespace(slug, item))
        return result

    def create_item(self, data: dict, author: str = "system") -> dict:
        # Optional routing hint: caller may include ``target_project`` in data.
        d = dict(data)
        target = d.pop("target_project", None)
        if target and target in self._adapters:
            slug, adapter = target, self._adapters[target]
        else:
            slug, adapter = self._primary_slug, self._primary
        item = adapter.create_item(d, author)
        return self._namespace(slug, item)

    def update_item(self, uid: str, data: dict, author: Optional[str] = None) -> Optional[dict]:
        slug, bare_id, adapter = self._route(uid)
        item = adapter.update_item(bare_id, data, author)
        return self._namespace(slug, item) if item is not None else None

    def delete_item(self, uid: str, author: Optional[str] = None) -> bool:
        _, bare_id, adapter = self._route(uid)
        return adapter.delete_item(bare_id, author)

    def validate_schema(self) -> dict:
        errors: dict = {}
        for slug, adapter in self._adapters.items():
            for key, value in adapter.validate_schema().items():
                errors[f"{slug}{self.SEP}{key}"] = value
        return errors

    def get_project_config(self):
        return self._primary.get_project_config()

    def get_test_result(self, tc_id: str) -> Optional[dict]:
        _, bare_id, adapter = self._route(tc_id)
        return adapter.get_test_result(bare_id)

    def get_all_test_results(self, status_filter: Optional[str] = None) -> Dict[str, dict]:
        result: Dict[str, dict] = {}
        for slug, adapter in self._adapters.items():
            for tc_id, value in adapter.get_all_test_results(status_filter).items():
                result[f"{slug}{self.SEP}{tc_id}"] = value
        return result

    def get_test_result_items(self) -> List[dict]:
        result: List[dict] = []
        for slug, adapter in self._adapters.items():
            for item in adapter.get_test_result_items():
                result.append(self._namespace(slug, item))
        return result

    def get_document(self, doc_id: str) -> Optional[str]:
        _, bare_id, adapter = self._route(doc_id)
        return adapter.get_document(bare_id)

    def list_documents(self) -> List[str]:
        result: List[str] = []
        for slug, adapter in self._adapters.items():
            result.extend(f"{slug}{self.SEP}{d}" for d in adapter.list_documents())
        return result

    def record_compliance_run(
        self,
        group_id: str,
        report_dict: dict,
        commit_sha: str = "",
        trigger: str = "manual",
    ) -> None:
        self._primary.record_compliance_run(group_id, report_dict, commit_sha, trigger)

    def get_compliance_runs(
        self,
        group_id: str,
        since_date: Optional[str] = None,
    ) -> List[Dict]:
        return self._primary.get_compliance_runs(group_id, since_date)

    # ------------------------------------------------------------------
    # Multi-project introspection
    # ------------------------------------------------------------------

    @property
    def project_slugs(self) -> List[str]:
        """Return the list of project slugs in insertion order."""
        return list(self._adapters.keys())

    @property
    def primary_slug(self) -> str:
        """Return the slug of the primary project."""
        return self._primary_slug
