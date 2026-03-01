"""External test results provider (formerly ManualTestProvider).

Reads and writes test results exclusively via ResultStore.
No YAML test-case files are used.
"""

from pathlib import Path
from typing import Dict


class ManualTestProvider:
    """Retrieve and update test verification status from the ResultStore.

    Configuration keys (under ``test_integration.manual``):
        audit_log: relative path to audit log (default: test-results/audit.log)
        require_verified_by: bool (kept for compatibility, not enforced here)
        require_verification_date: bool (kept for compatibility)
    """

    def __init__(self, config: dict, dhf_path: Path = None):
        self.config = config
        self._dhf_path = Path(dhf_path) if dhf_path else None
        self._store = None

    @property
    def store(self):
        """Lazy-load ResultStore."""
        if self._store is None:
            from .result_store import ResultStore
            if self._dhf_path is None:
                raise RuntimeError("ManualTestProvider requires dhf_path to use ResultStore")
            self._store = ResultStore(self._dhf_path, self.config)
        return self._store

    def get_status(self, test_case: dict) -> Dict:
        """Return the latest verification status for a test case.

        Falls back to PENDING if no result has been recorded yet.
        """
        tc_id = test_case.get("id")
        if tc_id and self._dhf_path:
            record = self.store.get(tc_id)
            if record:
                return {
                    "status": record.get("testing_status", "PENDING"),
                    "source": "external",
                    "timestamp": record.get("testing_date"),
                    "verified_by": record.get("tester"),
                    "details": record.get("testing_notes"),
                }
        # No result found
        return {
            "status": "PENDING",
            "source": "external",
            "timestamp": None,
            "verified_by": None,
            "details": "No test result recorded",
        }

    def update_status(
        self,
        test_id: str,
        status: str,
        verified_by: str,
        notes: str = None,
    ) -> None:
        """Record a manual test execution result in the ResultStore."""
        self.store.record_execution(
            tc_id=test_id,
            testing_status=status,
            tester=verified_by,
            notes=notes or "",
        )

    def get_audit_trail(self, test_id: str) -> list:
        """Return audit log lines mentioning test_id."""
        audit_path = (
            self._dhf_path / self.config.get("audit_log", "test-results/audit.log")
            if self._dhf_path
            else None
        )
        if not audit_path or not audit_path.exists():
            return []
        entries = []
        with open(audit_path, "r") as f:
            for line in f:
                if test_id in line:
                    entries.append(line.strip())
        return entries

    def refresh_cache(self):
        """No-op: ResultStore reads from disk on every call."""
        pass
