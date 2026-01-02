"""
Tests for SRS-010: GitHub Provider Multi-Artifact Support

Verifies that the GitHub provider correctly:
- Downloads multiple artifacts
- Aggregates results from all artifacts
- Handles missing artifacts gracefully
- Parses JUnit XML correctly

@links: SRS-010
"""

import pytest
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, MagicMock
import io
import zipfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from test_results.github_provider import GitHubActionsProvider


class TestMultiArtifactSupport:
    """Test SRS-010: Multi-artifact test results aggregation"""
    
    def create_junit_xml(self, test_results):
        """Helper to create JUnit XML content
        
        Args:
            test_results: List of (test_id, status) tuples
                         status can be 'pass', 'fail', 'skip'
        """
        root = ET.Element('testsuite')
        root.set('name', 'test_suite')
        root.set('tests', str(len(test_results)))
        
        for test_id, status in test_results:
            testcase = ET.SubElement(root, 'testcase')
            # Convert TC-SRS-001 to test_TC_SRS_001
            test_name = f"test_{test_id.replace('-', '_')}"
            testcase.set('name', test_name)
            testcase.set('classname', 'tests.test_module')
            
            if status == 'fail':
                failure = ET.SubElement(testcase, 'failure')
                failure.set('message', 'Test failed')
            elif status == 'skip':
                skipped = ET.SubElement(testcase, 'skipped')
                skipped.set('message', 'Test skipped')
        
        return ET.tostring(root, encoding='unicode')
    
    def create_artifact_zip(self, xml_content):
        """Create a zip file containing JUnit XML"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('test-results.xml', xml_content)
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    def test_TC_SRS_010_010_multiple_artifacts_downloaded(self):
        """
        TC-SRS-010-010: Verify all configured artifacts are downloaded
        
        @links: SRS-010
        @test_id: TC-SRS-010-010
        
        Steps:
          1. Configure provider with 3 artifact names
          2. Mock GitHub API to return 3 artifacts
          3. Verify provider attempts to download all 3
        
        Expected Result:
          All 3 artifacts should be downloaded
        """
        config = {
            'repository': 'test/repo',
            'artifact_names': ['unit-tests', 'sys-tests', 'crs-tests'],
            'token_env': 'GITHUB_TOKEN'
        }
        
        provider = GitHubActionsProvider(config)
        
        # Mock GitHub API responses
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'fake_token'}):
            with patch('requests.get') as mock_get:
                # Mock workflow runs response
                runs_response = Mock()
                runs_response.json.return_value = {
                    'workflow_runs': [{'id': 123}]
                }
                runs_response.raise_for_status = Mock()
                
                # Mock artifacts response
                artifacts_response = Mock()
                artifacts_response.json.return_value = {
                    'artifacts': [
                        {'name': 'unit-tests', 'archive_download_url': 'url1'},
                        {'name': 'sys-tests', 'archive_download_url': 'url2'},
                        {'name': 'crs-tests', 'archive_download_url': 'url3'},
                    ]
                }
                artifacts_response.raise_for_status = Mock()
                
                # Mock artifact download responses
                xml_content = self.create_junit_xml([('TC-SRS-001', 'pass')])
                zip_content = self.create_artifact_zip(xml_content)
                
                download_response = Mock()
                download_response.content = zip_content
                download_response.raise_for_status = Mock()
                
                # Set up mock to return different responses
                mock_get.side_effect = [
                    runs_response,      # GET workflow runs
                    artifacts_response, # GET artifacts
                    download_response,  # Download artifact 1
                    download_response,  # Download artifact 2
                    download_response,  # Download artifact 3
                ]
                
                # Load results
                provider._load_results()
                
                # Verify 5 API calls (runs, artifacts, 3 downloads)
                assert mock_get.call_count == 5
    
    def test_TC_SRS_010_011_results_aggregated_from_all_artifacts(self):
        """
        TC-SRS-010-011: Verify test results from all artifacts are merged
        
        @links: SRS-010
        @test_id: TC-SRS-010-011
        
        Steps:
          1. Mock 3 artifacts with different test results
          2. Load results
          3. Verify cache contains results from all 3
        
        Expected Result:
          Cache should contain test results from all artifacts
        """
        config = {
            'repository': 'test/repo',
            'artifact_names': ['unit-tests', 'sys-tests', 'crs-tests'],
            'token_env': 'GITHUB_TOKEN'
        }
        
        provider = GitHubActionsProvider(config)
        
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'fake_token'}):
            with patch('requests.get') as mock_get:
                # Mock workflow runs
                runs_response = Mock()
                runs_response.json.return_value = {
                    'workflow_runs': [{'id': 123}]
                }
                runs_response.raise_for_status = Mock()
                
                # Mock artifacts
                artifacts_response = Mock()
                artifacts_response.json.return_value = {
                    'artifacts': [
                        {'name': 'unit-tests', 'archive_download_url': 'url1'},
                        {'name': 'sys-tests', 'archive_download_url': 'url2'},
                        {'name': 'crs-tests', 'archive_download_url': 'url3'},
                    ]
                }
                artifacts_response.raise_for_status = Mock()
                
                # Create different test results for each artifact
                xml1 = self.create_junit_xml([('TC-SRS-001', 'pass')])
                xml2 = self.create_junit_xml([('TC-SYS-001', 'pass')])
                xml3 = self.create_junit_xml([('TC-CRS-001', 'fail')])
                
                download1 = Mock()
                download1.content = self.create_artifact_zip(xml1)
                download1.raise_for_status = Mock()
                
                download2 = Mock()
                download2.content = self.create_artifact_zip(xml2)
                download2.raise_for_status = Mock()
                
                download3 = Mock()
                download3.content = self.create_artifact_zip(xml3)
                download3.raise_for_status = Mock()
                
                mock_get.side_effect = [
                    runs_response,
                    artifacts_response,
                    download1,
                    download2,
                    download3,
                ]
                
                provider._load_results()
                
                # Verify all 3 test results are in cache
                assert 'TC-SRS-001' in provider._cache
                assert 'TC-SYS-001' in provider._cache
                assert 'TC-CRS-001' in provider._cache
                
                # Verify statuses
                assert provider._cache['TC-SRS-001']['status'] == 'PASS'
                assert provider._cache['TC-SYS-001']['status'] == 'PASS'
                assert provider._cache['TC-CRS-001']['status'] == 'FAIL'
    
    def test_TC_SRS_010_012_missing_artifact_doesnt_fail_others(self):
        """
        TC-SRS-010-012: Verify missing artifact doesn't prevent loading others
        
        @links: SRS-010
        @test_id: TC-SRS-010-012
        
        Steps:
          1. Configure 3 artifacts
          2. Mock only 2 available
          3. Verify 2 artifacts are loaded successfully
        
        Expected Result:
          Available artifacts should be loaded even if one is missing
        """
        config = {
            'repository': 'test/repo',
            'artifact_names': ['unit-tests', 'sys-tests', 'missing-tests'],
            'token_env': 'GITHUB_TOKEN'
        }
        
        provider = GitHubActionsProvider(config)
        
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'fake_token'}):
            with patch('requests.get') as mock_get:
                runs_response = Mock()
                runs_response.json.return_value = {
                    'workflow_runs': [{'id': 123}]
                }
                runs_response.raise_for_status = Mock()
                
                # Only 2 artifacts available
                artifacts_response = Mock()
                artifacts_response.json.return_value = {
                    'artifacts': [
                        {'name': 'unit-tests', 'archive_download_url': 'url1'},
                        {'name': 'sys-tests', 'archive_download_url': 'url2'},
                        # 'missing-tests' not present
                    ]
                }
                artifacts_response.raise_for_status = Mock()
                
                xml1 = self.create_junit_xml([('TC-SRS-001', 'pass')])
                xml2 = self.create_junit_xml([('TC-SYS-001', 'pass')])
                
                download1 = Mock()
                download1.content = self.create_artifact_zip(xml1)
                download1.raise_for_status = Mock()
                
                download2 = Mock()
                download2.content = self.create_artifact_zip(xml2)
                download2.raise_for_status = Mock()
                
                mock_get.side_effect = [
                    runs_response,
                    artifacts_response,
                    download1,
                    download2,
                ]
                
                provider._load_results()
                
                # Should have results from 2 artifacts
                assert 'TC-SRS-001' in provider._cache
                assert 'TC-SYS-001' in provider._cache
                assert len(provider._cache) == 2


class TestJUnitXMLParsing:
    """Test SRS-010: JUnit XML parsing"""
    
    def test_TC_SRS_010_013_parse_pass_fail_skip_statuses(self):
        """
        TC-SRS-010-013: Verify all test statuses are correctly parsed
        
        @links: SRS-010
        @test_id: TC-SRS-010-013
        
        Steps:
          1. Create JUnit XML with PASS, FAIL, SKIP tests
          2. Parse XML
          3. Verify statuses are correctly extracted
        
        Expected Result:
          All statuses should be correctly mapped
        """
        config = {
            'repository': 'test/repo',
            'artifact_names': ['test-results'],
            'token_env': 'GITHUB_TOKEN'
        }
        
        provider = GitHubActionsProvider(config)
        
        # Create XML with different statuses
        root = ET.Element('testsuite')
        
        # PASS test
        pass_test = ET.SubElement(root, 'testcase')
        pass_test.set('name', 'test_TC_SRS_001')
        pass_test.set('classname', 'tests.test_module')
        
        # FAIL test
        fail_test = ET.SubElement(root, 'testcase')
        fail_test.set('name', 'test_TC_SRS_002')
        fail_test.set('classname', 'tests.test_module')
        failure = ET.SubElement(fail_test, 'failure')
        failure.set('message', 'Assertion failed')
        
        # SKIP test
        skip_test = ET.SubElement(root, 'testcase')
        skip_test.set('name', 'test_TC_SRS_003')
        skip_test.set('classname', 'tests.test_module')
        skipped = ET.SubElement(skip_test, 'skipped')
        skipped.set('message', 'Test skipped')
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(ET.tostring(root, encoding='unicode'))
            temp_file = Path(f.name)
        
        try:
            provider._parse_junit_xml(temp_file)
            
            # Verify statuses
            assert provider._cache['TC-SRS-001']['status'] == 'PASS'
            assert provider._cache['TC-SRS-002']['status'] == 'FAIL'
            assert provider._cache['TC-SRS-003']['status'] == 'SKIP'
            
        finally:
            temp_file.unlink()
    
    def test_TC_SRS_010_014_test_id_extraction_patterns(self):
        """
        TC-SRS-010-014: Verify various test ID naming patterns are recognized
        
        @links: SRS-010
        @test_id: TC-SRS-010-014
        
        Steps:
          1. Test ID extraction with various formats
          2. Verify correct ID format returned
        
        Expected Result:
          All naming patterns should map to correct TC-* format
        """
        config = {'repository': 'test/repo', 'artifact_names': [], 'token_env': 'GITHUB_TOKEN'}
        provider = GitHubActionsProvider(config)
        
        # Test various naming patterns
        test_cases = [
            ('test_TC_SRS_001', 'tests.module', 'TC-SRS-001'),
            ('test_tc_srs_002', 'tests.module', 'TC-SRS-002'),
            ('test_TC_CRS_009_001', 'tests.module', 'TC-CRS-009-001'),
        ]
        
        for name, classname, expected_id in test_cases:
            result = provider._extract_test_id(name, classname)
            assert result == expected_id, \
                f"Expected {expected_id} from {name}, got {result}"
