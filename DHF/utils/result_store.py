"""Persistent store for external test results.

Stores test case definitions (registration) and execution results together,
keyed by TC ID, in DHF/test-results/results.yaml.

Storage format (v2 — append-mode, newest first):
    {tc_id: [record, record, ...], ...}

On load, old flat format {tc_id: record} is detected and migrated transparently.
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
            results.yaml   # history list per TC ID, newest first
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
        """Prepend a new execution record for a TC (preserving full history)."""
        all_records = self._load_all()
        history = all_records.get(tc_id, [])

        # Build from latest record so stable fields (title, links, review metadata)
        # carry forward when the caller omits them.
        latest = history[0] if history else {"id": tc_id}
        entry: dict = dict(latest)

        entry["id"] = tc_id
        if title:
            entry["title"] = title
        if links:
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

        # Prepend so index 0 is always newest
        all_records[tc_id] = [entry] + history
        self._save_all(all_records)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_latest(self, tc_id: str) -> Optional[Dict]:
        """Return the most recent record for a single TC, or None."""
        history = self._load_all().get(tc_id)
        if not history:
            return None
        return history[0]

    def get(self, tc_id: str) -> Optional[Dict]:
        """Alias for get_latest — backward-compatible with existing callers."""
        return self.get_latest(tc_id)

    def get_history(self, tc_id: str) -> List[Dict]:
        """Return the full list of records for a TC (newest first), or []."""
        return self._load_all().get(tc_id, [])

    def get_all(self, status_filter: Optional[str] = None) -> Dict[str, Dict]:
        """Return {tc_id: latest_record}, optionally filtered by testing_status.

        Interface is identical to the old flat-dict return so existing callers
        (local_adapter, core, CLI) require no changes.
        """
        all_records = self._load_all()
        result = {}
        for tc_id, history in all_records.items():
            if not history:
                continue
            latest = history[0]
            if status_filter is None or latest.get("testing_status") == status_filter:
                result[tc_id] = latest
        return result

    def as_tc_items(self) -> List[Dict]:
        """Return records shaped to match get_all_items() dicts.

        Each TC item includes ``all_linked_uids`` derived from ``links`` so
        the graph engine can build traceability edges.
        """
        items = []
        for rec in self.get_all().values():
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

    def _load_all(self) -> Dict[str, List[Dict]]:
        if not self._results_path.exists():
            return {}
        with open(self._results_path, "r") as f:
            data = yaml.safe_load(f) or {}
        return self._migrate(data)

    def _migrate(self, data: dict) -> Dict[str, List[Dict]]:
        """Transparently migrate old flat {tc_id: record} format to list format."""
        migrated = {}
        for tc_id, value in data.items():
            if isinstance(value, list):
                migrated[tc_id] = value
            else:
                # Old format: single record dict — wrap in a list
                migrated[tc_id] = [value]
        return migrated

    def _save_all(self, records: Dict[str, List[Dict]]) -> None:
        with open(self._results_path, "w") as f:
            yaml.dump(records, f, default_flow_style=False, sort_keys=True, allow_unicode=True)
