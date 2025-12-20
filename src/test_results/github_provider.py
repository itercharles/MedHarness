"""GitHub Actions test results provider."""

import os
import xml.etree.ElementTree as ET
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
import requests


class GitHubActionsProvider:
    """Retrieves test results from GitHub Actions artifacts.
    
    Supports two modes:
    1. Local file mode: Read from DHF/test-results/latest.xml
    2. API mode: Download artifacts via GitHub API (requires token)
    """
    
    def __init__(self, config: dict):
        """Initialize GitHub provider.
        
        Args:
            config: Configuration dict with 'github' or 'local' sections
        """
        self.config = config
        self.mode = 'local' if config.get('local') else 'github'
        self._cache = {}
        self._cache_timestamp = None
    
    def get_status(self, test_id: str) -> Dict[str, any]:
        """Get verification status for automated test.
        
        Args:
            test_id: Test case ID (e.g., TC-SYS-001)
        
        Returns:
            Status dict with keys: status, source, timestamp, details
        """
        # Refresh cache if needed
        if not self._cache or self._is_cache_stale():
            self._load_results()
        
        # Look up test result
        result = self._cache.get(test_id)
        
        if result:
            return {
                'status': result['status'],
                'source': 'automated',
                'timestamp': result.get('timestamp'),
                'verified_by': None,
                'details': result.get('message')
            }
        else:
            # Test not found in results - might not have run yet
            return {
                'status': 'PENDING',
                'source': 'automated',
                'timestamp': None,
                'verified_by': None,
                'details': 'Test not found in latest results'
            }
    
    def _load_results(self):
        """Load test results from configured source."""
        if self.mode == 'local':
            self._load_from_local_file()
        else:
            self._load_from_github_api()
        
        self._cache_timestamp = datetime.now()
    
    def _load_from_local_file(self):
        """Load results from local JUnit XML file."""
        local_config = self.config.get('local', {})
        results_file = local_config.get('results_file', 'test-results/latest.xml')
        
        # Resolve path relative to DHF directory
        file_path = Path(__file__).parent.parent.parent / 'DHF' / results_file
        
        if not file_path.exists():
            print(f"Warning: Test results file not found: {file_path}")
            self._cache = {}
            return
        
        self._parse_junit_xml(file_path)
    
    def _load_from_github_api(self):
        """Load results from GitHub Actions API."""
        github_config = self.config.get('github', {})
        
        # Get configuration
        repo = github_config.get('repository')
        workflow_name = github_config.get('workflow_name', 'Test Suite')
        artifact_name = github_config.get('artifact_name', 'test-results')
        token_env = github_config.get('token_env', 'GITHUB_TOKEN')
        
        # Get token from environment
        token = os.getenv(token_env)
        if not token:
            print(f"Warning: GitHub token not found in ${token_env}")
            self._cache = {}
            return
        
        # TODO: Implement GitHub API download
        # For now, fall back to local file
        print("GitHub API mode not yet implemented, falling back to local file")
        self._load_from_local_file()
    
    def _parse_junit_xml(self, file_path: Path):
        """Parse JUnit XML file and extract test results.
        
        Args:
            file_path: Path to JUnit XML file
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            self._cache = {}
            
            # Parse test cases
            for testcase in root.iter('testcase'):
                # Extract test ID from name or classname
                # Assuming test function names match test IDs
                name = testcase.get('name', '')
                classname = testcase.get('classname', '')
                
                # Try to extract test ID (e.g., test_TC_SYS_001 → TC-SYS-001)
                test_id = self._extract_test_id(name, classname)
                
                if not test_id:
                    continue
                
                # Determine status
                if testcase.find('failure') is not None:
                    status = 'FAIL'
                    message = testcase.find('failure').get('message', '')
                elif testcase.find('error') is not None:
                    status = 'FAIL'
                    message = testcase.find('error').get('message', '')
                elif testcase.find('skipped') is not None:
                    status = 'SKIP'
                    message = 'Test skipped'
                else:
                    status = 'PASS'
                    message = None
                
                self._cache[test_id] = {
                    'status': status,
                    'message': message,
                    'timestamp': datetime.fromtimestamp(file_path.stat().st_mtime)
                }
        
        except Exception as e:
            print(f"Error parsing JUnit XML: {e}")
            self._cache = {}
    
    def _extract_test_id(self, name: str, classname: str) -> Optional[str]:
        """Extract test ID from test name or classname.
        
        Supports formats:
        - test_TC_SYS_001
        - test_tc_sys_001
        - TestTCSYS001
        
        Args:
            name: Test function name
            classname: Test class name
        
        Returns:
            Test ID in format TC-SYS-001 or None
        """
        import re
        
        # Try to find pattern like TC_SYS_001 or tc_sys_001
        pattern = r'(TC|tc)[_-]([A-Z]+|[a-z]+)[_-](\d+)'
        
        for text in [name, classname]:
            match = re.search(pattern, text)
            if match:
                prefix = match.group(1).upper()
                doc_type = match.group(2).upper()
                number = match.group(3)
                return f"{prefix}-{doc_type}-{number}"
        
        return None
    
    def _is_cache_stale(self) -> bool:
        """Check if cache needs refresh (older than 5 minutes)."""
        if not self._cache_timestamp:
            return True
        
        age = (datetime.now() - self._cache_timestamp).total_seconds()
        return age > 300  # 5 minutes
    
    def refresh_cache(self):
        """Force refresh of cached results."""
        self._load_results()
