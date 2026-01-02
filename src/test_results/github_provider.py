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
            config: Configuration dict with GitHub API settings
        """

        # Ensure .env is loaded (for Streamlit caching)
        from pathlib import Path
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path, override=True)
        
        self.config = config
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
        """Load test results from GitHub API."""

        self._load_from_github_api()
        self._cache_timestamp = datetime.now()
    
    
    def _load_from_github_api(self):
        """Load results from GitHub Actions API."""
        # Get configuration directly (no nesting)
        repo = self.config.get('repository')
        artifact_names = self.config.get('artifact_names', [])
        
        token_env = self.config.get('token_env', 'GITHUB_TOKEN')
        
        if not repo:
            print("ERROR: GitHub repository not configured in project_config.yaml")
            self._cache = {}
            return
        
        # Get token from environment
        token = os.getenv(token_env)
        if not token:
            print(f"ERROR: GitHub token not found in environment variable ${token_env}")
            print(f"Please set {token_env} in your .env file or environment")
            self._cache = {}
            return
        
        try:
            print(f"[INFO] Fetching test results from GitHub: {repo}")
            
            # Get latest workflow run
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Get workflow runs
            url = f'https://api.github.com/repos/{repo}/actions/runs'
            params = {
                'status': 'completed',
                'per_page': 10
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            runs = response.json().get('workflow_runs', [])
            if not runs:
                print("WARNING: No completed workflow runs found")
                self._cache = {}
                return
            
            # Find latest successful run
            latest_run = runs[0]
            run_id = latest_run['id']
            print(f"[INFO] Found workflow run #{run_id}")
            
            # Get artifacts for this run
            artifacts_url = f'https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts'
            response = requests.get(artifacts_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            artifacts = response.json().get('artifacts', [])
            
            # Initialize cache
            self._cache = {}
            
            # Download and parse each artifact
            artifacts_found = 0
            for artifact_name in artifact_names:
                # Find artifact by name
                test_artifact = None
                for artifact in artifacts:
                    if artifact['name'] == artifact_name:
                        test_artifact = artifact
                        break
                
                if not test_artifact:
                    print(f"WARNING: Artifact '{artifact_name}' not found in run {run_id}")
                    continue
                
                artifacts_found += 1
                print(f"[INFO] Downloading artifact: {artifact_name}")
                
                # Download and parse artifact
                download_url = test_artifact['archive_download_url']
                response = requests.get(download_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Save to temporary file and extract
                import tempfile
                import zipfile
                import io
                
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Extract zip
                    zip_data = io.BytesIO(response.content)
                    with zipfile.ZipFile(zip_data) as zf:
                        zf.extractall(tmpdir)
                    
                    # Find XML file
                    xml_files = list(Path(tmpdir).glob('*.xml'))
                    if xml_files:
                        print(f"[INFO] Parsing test results from {xml_files[0].name}")
                        # Parse and merge into existing cache
                        self._parse_junit_xml(xml_files[0])
                    else:
                        print(f"WARNING: No XML file found in artifact {artifact_name}")
            
            if artifacts_found > 0:
                print(f"[INFO] Loaded {len(self._cache)} test results from {artifacts_found} artifacts")
            else:
                available_names = [a['name'] for a in artifacts]
                print(f"ERROR: None of the configured artifacts found in run {run_id}")
                print(f"Available artifacts: {available_names}")
                self._cache = {}
        
        except requests.exceptions.RequestException as e:
            print(f"ERROR: GitHub API request failed: {e}")
            self._cache = {}
        except Exception as e:
            print(f"ERROR: Failed to fetch from GitHub API: {e}")
            import traceback
            traceback.print_exc()
            self._cache = {}
    
    def _parse_junit_xml(self, file_path: Path):
        """Parse JUnit XML file and extract test results.
        
        Args:
            file_path: Path to JUnit XML file
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Don't reset cache - merge results instead
            if not self._cache:
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
            # Don't clear cache on error - keep existing results
    
    def _extract_test_id(self, name: str, classname: str) -> Optional[str]:
        """Extract test ID from test name or classname.
        
        Supports formats:
        - test_TC_SYS_001
        - test_TC_CRS_009_001 (with sub-number)
        - test_tc_sys_001
        - TestTCSYS001
        
        Args:
            name: Test function name
            classname: Test class name
        
        Returns:
            Test ID in format TC-SYS-001 or TC-CRS-009-001 or None
        """
        import re
        
        # Try to find pattern like TC_SYS_001 or TC_CRS_009_001
        pattern = r'(TC|tc)[_-]([A-Z]+|[a-z]+)[_-](\d+)(?:[_-](\d+))?'
        
        for text in [name, classname]:
            match = re.search(pattern, text)
            if match:
                prefix = match.group(1).upper()
                doc_type = match.group(2).upper()
                number = match.group(3)
                sub_number = match.group(4)
                
                if sub_number:
                    return f"{prefix}-{doc_type}-{number}-{sub_number}"
                else:
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
