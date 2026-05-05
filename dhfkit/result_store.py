"""Persistent store for external test results.

Stores test case definitions (registration) and execution results together,
keyed by TC ID, in DHF/test-results/results.yaml.

Storage format (v3 — latest-only):
    {tc_id: record, ...}

On load, old history format {tc_id: [record, record, ...]} is detected and
migrated transparently by keeping the first record as the latest.
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
        """Record the latest execution result for a TC."""
        all_records = self._load_all()

        # Build from latest record so stable fields (title, links, review metadata)
        # carry forward when the caller omits them.
        latest = all_records.get(tc_id) or {"id": tc_id}
        entry: dict = dict(latest)

        all_records[tc_id] = self._build_entry(
            entry,
            tc_id=tc_id,
            testing_status=testing_status,
            tester=tester,
            testing_date=testing_date,
            run_id=run_id,
            run_url=run_url,
            commit_sha=commit_sha,
            notes=notes,
            links=links,
            title=title,
            reviewer=reviewer,
            review_date=review_date,
            review_status=review_status,
        )
        self._save_all(all_records)

    def record_executions(self, executions: List[Dict]) -> None:
        """Record multiple latest execution results with one file read/write."""
        all_records = self._load_all()
        for execution in executions:
            tc_id = execution["tc_id"]
            latest = all_records.get(tc_id) or {"id": tc_id}
            all_records[tc_id] = self._build_entry(dict(latest), **execution)
        self._save_all(all_records)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_latest(self, tc_id: str) -> Optional[Dict]:
        """Return the most recent record for a single TC, or None."""
        return self._load_all().get(tc_id)

    def get(self, tc_id: str) -> Optional[Dict]:
        """Alias for get_latest — backward-compatible with existing callers."""
        return self.get_latest(tc_id)

    def get_history(self, tc_id: str) -> List[Dict]:
        """Return the latest record in list form for backward compatibility."""
        latest = self.get_latest(tc_id)
        return [latest] if latest else []

    def get_all(self, status_filter: Optional[str] = None) -> Dict[str, Dict]:
        """Return {tc_id: latest_record}, optionally filtered by testing_status.

        Interface is identical to the old flat-dict return so existing callers
        (local_adapter, core, CLI) require no changes.
        """
        result = {}
        for tc_id, record in self._load_all().items():
            if status_filter is None or record.get("testing_status") == status_filter:
                result[tc_id] = record
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

    def _load_all(self) -> Dict[str, Dict]:
        if not self._results_path.exists():
            return {}
        with open(self._results_path, "r") as f:
            data = yaml.safe_load(f) or {}
        return self._migrate(data)

    def _migrate(self, data: dict) -> Dict[str, Dict]:
        """Migrate old history-list records to latest-only records."""
        migrated = {}
        for tc_id, value in data.items():
            if isinstance(value, list):
                if value:
                    migrated[tc_id] = value[0]
            elif isinstance(value, dict):
                migrated[tc_id] = value
        return migrated

    def _save_all(self, records: Dict[str, Dict]) -> None:
        with open(self._results_path, "w") as f:
            yaml.dump(records, f, default_flow_style=False, sort_keys=True, allow_unicode=True)

    def _build_entry(
        self,
        entry: Dict,
        *,
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
    ) -> Dict:
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
        return entry
