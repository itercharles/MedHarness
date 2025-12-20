"""Manual test results provider."""

from typing import Dict
from datetime import datetime
from pathlib import Path


class ManualTestProvider:
    """Retrieves test results from manual test YAML files and audit log."""
    
    def __init__(self, config: dict):
        """Initialize manual test provider.
        
        Args:
            config: Configuration dict with 'audit_log' and validation settings
        """
        self.config = config
        self.audit_log_path = Path(config.get('audit_log', 'DHF/test-results/manual_tests.log'))
        self.require_verified_by = config.get('require_verified_by', True)
        self.require_verification_date = config.get('require_verification_date', True)
    
    def get_status(self, test_case: dict) -> Dict[str, any]:
        """Get verification status for manual test.
        
        Args:
            test_case: Test case dict from YAML file
        
        Returns:
            Status dict with keys: status, source, timestamp, verified_by, details
        """
        # Extract fields from YAML
        status_raw = test_case.get('verification_status', 'PENDING')
        
        # Convert to string if it's an enum
        if hasattr(status_raw, 'value'):
            status = status_raw.value
        elif hasattr(status_raw, 'name'):
            status = status_raw.name
        else:
            status = str(status_raw)
        
        verified_by = test_case.get('verified_by')
        verified_date = test_case.get('verified_date')
        notes = test_case.get('verification_notes')
        
        # Parse date if present
        timestamp = None
        if verified_date:
            try:
                timestamp = datetime.fromisoformat(verified_date)
            except (ValueError, TypeError):
                # Try other date formats
                try:
                    timestamp = datetime.strptime(verified_date, '%Y-%m-%d')
                except (ValueError, TypeError):
                    pass
        
        # Validate required fields
        warnings = []
        if status != 'PENDING':
            if self.require_verified_by and not verified_by:
                warnings.append("Missing verified_by field")
            if self.require_verification_date and not verified_date:
                warnings.append("Missing verified_date field")
        
        details = notes
        if warnings:
            details = (details or '') + ' | Warnings: ' + ', '.join(warnings)
        
        return {
            'status': status,
            'source': 'manual',
            'timestamp': timestamp,
            'verified_by': verified_by,
            'details': details
        }
    
    def update_status(self, test_id: str, status: str, verified_by: str, notes: str = None):
        """Update manual test verification status.
        
        This method is called from the UI to update test status.
        It updates both the YAML file and the audit log.
        
        Args:
            test_id: Test case ID
            status: New status (PASS, FAIL, PENDING)
            verified_by: Name of person verifying
            notes: Optional verification notes
        """
        # TODO: Implement YAML file update
        # TODO: Implement audit log append
        pass
    
    def get_audit_trail(self, test_id: str) -> list:
        """Get audit trail for a test case.
        
        Args:
            test_id: Test case ID
        
        Returns:
            List of audit log entries for this test
        """
        if not self.audit_log_path.exists():
            return []
        
        entries = []
        with open(self.audit_log_path, 'r') as f:
            for line in f:
                if test_id in line:
                    entries.append(line.strip())
        
        return entries
    
    def refresh_cache(self):
        """Manual tests don't use cache - always read from YAML."""
        pass
