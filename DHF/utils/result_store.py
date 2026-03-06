"""Persistent store for external test results.

Stores test case definitions (registration) and execution results together,
keyed by TC ID, in DHF/test-results/results.yaml.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class ResultStore:
    """Read/write test execution results and review metadata.

    Storage layout::

        DHF/test-results/
            results.yaml   # latest record per TC ID
    """

    _DEFAULT_RESULTS_PATH = "test-results/results.yaml"

    def __init__(self, dhf_path: Path, config: dict = {}):
        results_rel = config.get("path", self._DEFAULT_RESULTS_PATH)
        self._results_path = Path(dhf_path) / results_rel
        self._results_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def record_execution(
        self,
        tc_id: str,
        testing_status: str,
        tester: str = "",
        testing_date: Optional[str] = None,
        run_id: str = "",
        run_url: str = "",
        commit_sha: str = "",
        notes: str = "",
        links: Optional[List[str]] = None,
        title: str = "",
        reviewer: str = "",
        review_date: str = "",
        review_status: str = "",
    ) -> None:
        """Store execution result for a TC (upserts the entry)."""
        record = self._load_all()
        entry = record.get(tc_id, {"id": tc_id})
        entry["id"] = tc_id
        if title and not entry.get("title"):
            entry["title"] = title
        if links and not entry.get("links"):
            entry["links"] = links
        if reviewer:
            entry["reviewer"] = reviewer
        if review_date:
            entry["review_date"] = review_date
        if review_status:
            entry["review_status"] = review_status
        entry["testing_status"] = testing_status
        entry["tester"] = tester
        entry["testing_date"] = testing_date or datetime.now(timezone.utc).isoformat()
        if run_id:
            entry["run_id"] = run_id
        if run_url:
            entry["run_url"] = run_url
        if commit_sha:
            entry["commit_sha"] = commit_sha
        if notes:
            entry["testing_notes"] = notes
        record[tc_id] = entry
        self._save_all(record)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get(self, tc_id: str) -> Optional[Dict]:
        """Return the record for a single TC, or None."""
        return self._load_all().get(tc_id)

    def get_all(self, status_filter: Optional[str] = None) -> Dict[str, Dict]:
        """Return all records, optionally filtered by testing_status."""
        records = self._load_all()
        if status_filter is None:
            return records
        return {
            tc_id: rec
            for tc_id, rec in records.items()
            if rec.get("testing_status") == status_filter
        }

    def as_tc_items(self) -> List[Dict]:
        """Return records shaped to match get_all_items() dicts.

        Each TC item includes ``all_linked_uids`` derived from ``links`` so
        the graph engine can build traceability edges.
        """
        items = []
        for rec in self._load_all().values():
            item = dict(rec)
            item.setdefault("title", "")
            item.setdefault("status", "approved")
            links = item.get("links") or []
            item["verifies"] = links
            item["all_linked_uids"] = links
            items.append(item)
        return items

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_all(self) -> Dict[str, Dict]:
        if not self._results_path.exists():
            return {}
        with open(self._results_path, "r") as f:
            data = yaml.safe_load(f) or {}
        return data

    def _save_all(self, records: Dict[str, Dict]) -> None:
        with open(self._results_path, "w") as f:
            yaml.dump(records, f, default_flow_style=False, sort_keys=True, allow_unicode=True)
