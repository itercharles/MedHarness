"""Main test results provider - routes to appropriate backend."""

from typing import Dict, Optional
from datetime import datetime


class VerificationStatusProvider:
    """Unified interface for test verification status retrieval.
    
    Routes requests to appropriate provider based on test type:
    - automated tests → GitHubActionsProvider
    - manual tests → ManualTestProvider
    """
    
    def __init__(self, config: dict):
        """Initialize provider with configuration.
        
        Args:
            config: Project configuration dict containing test_integration section
        """
        self.config = config
        self.test_integration_config = config.get('test_integration', {})
        

        # Lazy load providers to avoid import errors if dependencies missing
        self._github_provider = None
        self._manual_provider = None
    
    @property
    def github_provider(self):
        """Lazy load GitHub provider."""
        if self._github_provider is None:
            from .github_provider import GitHubActionsProvider
            self._github_provider = GitHubActionsProvider(
                self.test_integration_config.get('automated', {})
            )
        return self._github_provider
    
    @property
    def manual_provider(self):
        """Lazy load manual test provider."""
        if self._manual_provider is None:
            from .manual_provider import ManualTestProvider
            self._manual_provider = ManualTestProvider(
                self.test_integration_config.get('manual', {})
            )
        return self._manual_provider
    
    def get_verification_status(self, test_case: dict) -> Dict[str, any]:
        """Get verification status for a test case.
        
        Args:
            test_case: Test case dict with 'id' and 'test_type' fields
        
        Returns:
            Dict with keys:
            - status: str (PASS, FAIL, PENDING, SKIP)
            - source: str (automated, manual)
            - timestamp: datetime or None
            - verified_by: str or None (for manual tests)
            - details: str or None (failure message, notes, etc.)
        """
        test_type = test_case.get('test_type', 'manual')
        
        if test_type == 'automated':
            return self.github_provider.get_status(test_case['id'])
        else:
            return self.manual_provider.get_status(test_case)
    
    def get_all_statuses(self, test_cases: list) -> Dict[str, Dict]:
        """Get statuses for multiple test cases efficiently.
        
        Args:
            test_cases: List of test case dicts
        
        Returns:
            Dict mapping test_id to status dict
        """
        results = {}
        for test_case in test_cases:
            results[test_case['id']] = self.get_verification_status(test_case)
        return results
    
    def refresh_cache(self):
        """Refresh cached test results from all providers."""
        if self._github_provider:
            self._github_provider.refresh_cache()
        if self._manual_provider:
            self._manual_provider.refresh_cache()
