"""Persistent store for compliance run history.

Mirrors result_store.py. Stores compliance check runs under
DHF/compliance-runs/<standard_id>.yaml in append mode (new entries are
added; existing entries are never overwritten).

Each entry contains:
    run_id, standard_id, timestamp, commit_sha, score,
    total_policies, passed_policies, results, trigger, content_hash
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class ComplianceStore:
    """Append-mode store for compliance run history keyed by standard ID.

    Storage layout::

        DHF/compliance-runs/
            IEC_62304.yaml    # list of run entries for IEC 62304
            IEC_82304_1.yaml  # list of run entries for IEC 82304-1
            ...
    """

    _DEFAULT_DIR = "compliance-runs"

    def __init__(self, dhf_path: Path, runs_dir: Optional[str] = None):
        base = Path(dhf_path) / (runs_dir or self._DEFAULT_DIR)
        base.mkdir(parents=True, exist_ok=True)
        self._base = base

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def append_run(
        self,
        standard_id: str,
        run_id: str,
        score: float,
        total_policies: int,
        passed_policies: int,
        results: List[Dict],
        commit_sha: str = "",
        trigger: str = "manual",
        timestamp: Optional[str] = None,
    ) -> None:
        """Append a new compliance run record.  Never overwrites existing entries."""
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        content_hash = _hash_results(results)
        entry = {
            "run_id": run_id,
            "standard_id": standard_id,
            "timestamp": ts,
            "commit_sha": commit_sha,
            "score": score,
            "total_policies": total_policies,
            "passed_policies": passed_policies,
            "trigger": trigger,
            "content_hash": content_hash,
            "results": results,
        }
        path = self._path_for(standard_id)
        runs = self._load(path)
        runs.append(entry)
        self._save(path, runs)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_runs(
        self,
        standard_id: str,
        since_date: Optional[str] = None,
    ) -> List[Dict]:
        """Return all run entries for a standard, optionally filtered by since_date (ISO 8601)."""
        runs = self._load(self._path_for(standard_id))
        if since_date is None:
            return runs
        return [r for r in runs if r.get("timestamp", "") >= since_date]

    def get_latest_run(self, standard_id: str) -> Optional[Dict]:
        """Return the most-recently appended run, or None."""
        runs = self._load(self._path_for(standard_id))
        return runs[-1] if runs else None

    def list_standards(self) -> List[str]:
        """Return standard IDs that have at least one run recorded."""
        return [p.stem for p in self._base.glob("*.yaml")]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _path_for(self, standard_id: str) -> Path:
        return self._base / f"{standard_id}.yaml"

    def _load(self, path: Path) -> List[Dict]:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, list):
            return []
        return data

    def _save(self, path: Path, runs: List[Dict]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(runs, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _hash_results(results: List[Dict]) -> str:
    """Compute a short content hash over the policy results list."""
    serialised = json.dumps(results, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode()).hexdigest()[:16]
