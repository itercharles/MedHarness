"""Main test results provider — delegates to ResultStore via ManualTestProvider."""

from typing import Dict


class VerificationStatusProvider:
    """Unified interface for test verification status retrieval.

    All test results (automated and manual) are stored in the external
    ResultStore and accessed through ManualTestProvider.  The legacy
    automated-test routing (GitHubActionsProvider) has been removed.
    """

    def __init__(self, config: dict, dhf_path=None):
        self.config = config
        self.test_integration_config = config.get("test_integration", {})
        self._dhf_path = dhf_path
        self._provider = None

    @property
    def provider(self):
        """Lazy-load the underlying provider."""
        if self._provider is None:
            from .manual_provider import ManualTestProvider
            from pathlib import Path
            self._provider = ManualTestProvider(
                self.test_integration_config.get("manual", {}),
                dhf_path=Path(self._dhf_path) if self._dhf_path else None,
            )
        return self._provider

    def get_verification_status(self, test_case: dict) -> Dict:
        """Get verification status for a test case.

        Returns dict with keys:
            status, source, timestamp, verified_by, details
        """
        return self.provider.get_status(test_case)

    def get_all_statuses(self, test_cases: list) -> Dict[str, Dict]:
        """Batch status lookup for a list of test case dicts."""
        return {tc["id"]: self.get_verification_status(tc) for tc in test_cases}

    def refresh_cache(self):
        """No-op: ResultStore reads from disk on every call."""
        if self._provider:
            self._provider.refresh_cache()
