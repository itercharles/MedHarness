"""Test results mixin for CompliantFlowCore.

Exposes test execution result import as a first-class core operation.
All persistence is delegated to the DHFAdapter; requirement item
verification_status fields are updated automatically on import.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from utils.junit_parser import ExecutionResult


class _TestResultsMixin:

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def import_test_results(
        self,
        results: "List[ExecutionResult]",
        tester: str,
        run_id: str = "",
        run_url: str = "",
        commit_sha: str = "",
    ) -> Dict:
        """Persist execution results and update linked requirement items.

        For each result:
        1. Writes to ResultStore via adapter.
        2. Collects linked requirement item IDs from the stored record.
        3. Aggregates verification_status for every touched requirement item.

        Returns summary: {imported, skipped, items_updated, failed_tcs}.
        """
        imported = 0
        skipped = 0
        touched_items: set = set()

        for result in results:
            if result.testing_status == "SKIP":
                skipped += 1
                continue
            self._adapter.record_test_result(
                tc_id=result.id,
                testing_status=result.testing_status,
                tester=tester,
                run_id=run_id,
                run_url=run_url,
                commit_sha=commit_sha,
                notes=result.error_message or "",
                links=result.links or None,
                title=result.title or "",
                reviewer=result.reviewer or "",
                review_date=result.review_date or "",
                review_status=result.review_status or "",
            )
            imported += 1
            record = self._adapter.get_test_result(result.id)
            for item_id in (record or {}).get("links") or []:
                touched_items.add(item_id)

        # Refresh graph so new TC items are visible
        self.refresh()

        items_updated = self._update_requirement_verification(touched_items)

        all_results = self._adapter.get_all_test_results()
        failed_tcs = [
            tc_id
            for tc_id, rec in all_results.items()
            if rec.get("testing_status") == "FAIL"
        ]
        return {
            "imported": imported,
            "skipped": skipped,
            "items_updated": items_updated,
            "failed_tcs": failed_tcs,
        }

    def get_test_result(self, tc_id: str) -> Optional[Dict]:
        """Return the stored record for a TC, or None if not found."""
        return self._adapter.get_test_result(tc_id)

    def get_all_test_results(self, status_filter: Optional[str] = None) -> Dict:
        """Return all stored test results, optionally filtered by testing_status."""
        return self._adapter.get_all_test_results(status_filter)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_requirement_verification(self, item_ids: set) -> List[str]:
        """Recompute and persist verification_status for each touched item."""
        updated: List[str] = []
        all_results = self._adapter.get_all_test_results()

        for item_id in item_ids:
            item = self.get_item(item_id)
            if item is None:
                continue

            doc_type_code = item_id.split("-")[0]
            doc_type_cfg = self.config.get_doc_type(doc_type_code) if self.config else None
            if not doc_type_cfg or not getattr(doc_type_cfg, "has_verification", False):
                continue

            linked_tc_results = [
                rec
                for rec in all_results.values()
                if item_id in (rec.get("links") or [])
                and rec.get("testing_status") in ("PASS", "FAIL")
            ]

            if not linked_tc_results:
                new_status = "not_verified"
            elif any(r["testing_status"] == "FAIL" for r in linked_tc_results):
                new_status = "failed"
            else:
                new_status = "verified"

            current_status = item.get("verification_status")
            if current_status != new_status:
                self.update_item(item_id, {**item, "verification_status": new_status})
                updated.append(item_id)

        return updated
