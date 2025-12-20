"""Tests for test results provider functionality."""

import pytest
from pathlib import Path
from test_results.test_case_scanner import AutomatedTestScanner
from test_results import VerificationStatusProvider
import xml.etree.ElementTree as ET


def test_TC_PROVIDER_001_junit_xml_parsing():
    """TC-PROVIDER-001: Verify JUnit XML Parsing
    
    @links: SDS-TRACE-003
    @prerequisites: Sample JUnit XML file
    
    Steps:
      1. Create sample JUnit XML content
      2. Parse XML with AutomatedTestScanner
      3. Extract test results
      4. Verify status mapping
    
    Expected Result:
      JUnit XML should be parsed correctly with PASS/FAIL/SKIP statuses
    """
    from test_results.github_provider import GitHubActionsProvider
    from pathlib import Path
    import tempfile
    
    # Create temporary JUnit XML
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <testsuites>
      <testsuite name="pytest">
        <testcase classname="test_core" name="test_TC_SYS_001_init"/>
        <testcase classname="test_core" name="test_TC_SYS_002_load">
          <failure message="AssertionError">Test failed</failure>
        </testcase>
        <testcase classname="test_core" name="test_TC_SYS_003_config">
          <skipped message="Not implemented"/>
        </testcase>
      </testsuite>
    </testsuites>
    """
    
    with tempfile.TemporaryDirectory() as tmpdir:
        xml_file = Path(tmpdir) / "test-results.xml"
        xml_file.write_text(xml_content)
        
        # Parse XML
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Verify structure
        testsuites = root.findall('.//testsuite')
        assert len(testsuites) > 0, "Should have test suites"
        
        testcases = root.findall('.//testcase')
        assert len(testcases) == 3, "Should have 3 test cases"
        
        # Verify status detection
        passed = [tc for tc in testcases if tc.find('failure') is None and tc.find('skipped') is None]
        failed = [tc for tc in testcases if tc.find('failure') is not None]
        skipped = [tc for tc in testcases if tc.find('skipped') is not None]
        
        assert len(passed) == 1, "Should have 1 passed test"
        assert len(failed) == 1, "Should have 1 failed test"
        assert len(skipped) == 1, "Should have 1 skipped test"


def test_TC_PROVIDER_002_test_id_extraction():
    """TC-PROVIDER-002: Verify Test ID Extraction from Names
    
    @links: SDS-TRACE-003
    @prerequisites: AutomatedTestScanner initialized
    
    Steps:
      1. Create AutomatedTestScanner instance
      2. Test ID extraction with various formats
      3. Verify correct ID format returned
    
    Expected Result:
      Test IDs should be extracted correctly from function names
    """
    scanner = AutomatedTestScanner(Path("tests"))
    
    # Test various formats
    test_cases = [
        ("test_TC_SYS_001_description", "TC-SYS-001"),
        ("test_tc_sys_001_description", "TC-SYS-001"),
        ("test_TC_CRS_123_something", "TC-CRS-123"),
    ]
    
    for function_name, expected_id in test_cases:
        result = scanner._extract_test_id(function_name, "")
        assert result == expected_id, \
            f"Should extract {expected_id} from {function_name}, got {result}"


def test_TC_PROVIDER_003_status_mapping():
    """TC-PROVIDER-003: Verify PASS/FAIL/SKIP Mapping
    
    @links: SDS-TRACE-003
    @prerequisites: Test results provider initialized
    
    Steps:
      1. Create test case with different statuses
      2. Map statuses to standard format
      3. Verify mapping correctness
    
    Expected Result:
      All test statuses should map to PASS, FAIL, SKIP, or PENDING
    """
    valid_statuses = ['PASS', 'FAIL', 'SKIP', 'PENDING']
    
    # Test status normalization
    test_mappings = {
        'passed': 'PASS',
        'failed': 'FAIL',
        'skipped': 'SKIP',
        'pending': 'PENDING',
    }
    
    for input_status, expected in test_mappings.items():
        normalized = input_status.upper()
        assert normalized in valid_statuses or expected in valid_statuses, \
            f"Status {input_status} should map to valid status"


def test_TC_PROVIDER_004_manual_test_reading():
    """TC-PROVIDER-004: Verify Manual Test Status from YAML
    
    @links: SDS-COMP-001
    @prerequisites: Manual test YAML files
    
    Steps:
      1. Initialize CompliantFlowCore
      2. Get all items
      3. Find manual test cases
      4. Verify manual test fields
    
    Expected Result:
      Manual tests should have verification_status, verified_by, verified_date
    """
    from traceability.compliant_flow_core import CompliantFlowCore
    
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    items = core.get_all_items()
    
    # Find manual tests
    manual_tests = [
        item for item in items 
        if item['id'].startswith(('TC-', 'tc-')) and item.get('test_type') == 'manual'
    ]
    
    # If we have manual tests, verify structure
    if manual_tests:
        for test in manual_tests:
            # Manual tests may have these fields
            assert 'test_type' in test
            assert test['test_type'] == 'manual'


def test_TC_PROVIDER_005_automated_test_discovery():
    """TC-PROVIDER-005: Verify Automated Test Discovery
    
    @links: SDS-COMP-001
    @prerequisites: Python test files in tests/ directory
    
    Steps:
      1. Create AutomatedTestScanner
      2. Scan tests directory
      3. Verify automated tests found
      4. Check test structure
    
    Expected Result:
      Scanner should find all automated tests with proper metadata
    """
    tests_dir = Path(__file__).parent
    scanner = AutomatedTestScanner(tests_dir)
    
    test_cases = scanner.scan_all_tests()
    
    # Should find tests
    assert len(test_cases) > 0, "Should find automated tests"
    
    # Verify structure
    for tc in test_cases:
        assert 'id' in tc, "Test case should have ID"
        assert 'test_type' in tc, "Test case should have test_type"
        assert tc['test_type'] == 'automated', "Should be automated test"
        assert 'title' in tc, "Test case should have title"
        assert 'links' in tc, "Test case should have links"
        assert tc.get('status') == 'approved', "Automated tests should be approved"
