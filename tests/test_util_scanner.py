"""Test the AutomatedTestScanner functionality."""

import pytest
from pathlib import Path
from test_results.test_case_scanner import AutomatedTestScanner


def test_scanner_extracts_test_id():
    """Test that scanner correctly extracts test IDs from function names."""
    scanner = AutomatedTestScanner(Path("tests"))
    
    # Test various formats
    assert scanner._extract_test_id("test_TC_SYS_001_description", "") == "TC-SYS-001"
    assert scanner._extract_test_id("test_tc_sys_001_description", "") == "TC-SYS-001"
    assert scanner._extract_test_id("test_TC_CRS_123_something", "") == "TC-CRS-123"


def test_scanner_parses_docstring():
    """Test that scanner correctly parses docstring metadata."""
    scanner = AutomatedTestScanner(Path("tests"))
    
    docstring = """TC-SYS-001: Test Title
    
    @links: SYS-001, SYS-002
    @prerequisites: Some prerequisite
    
    Steps:
      1. First step
      2. Second step
    
    Expected Result:
      Expected outcome
    """
    
    metadata = scanner._parse_docstring(docstring)
    
    assert metadata['title'] == "Test Title"
    assert metadata['links'] == ["SYS-001", "SYS-002"]
    assert metadata['prerequisites'] == "Some prerequisite"
    assert len(metadata['steps']) == 2
    assert "Expected outcome" in metadata['expected_result']


def test_scanner_finds_test_files():
    """Test that scanner finds test files in tests directory."""
    tests_dir = Path(__file__).parent
    scanner = AutomatedTestScanner(tests_dir)
    
    test_cases = scanner.scan_all_tests()
    
    # Should find at least the tests in test_core.py
    assert len(test_cases) >= 3
    
    # Verify test case structure
    for tc in test_cases:
        assert 'id' in tc
        assert 'test_type' in tc
        assert tc['test_type'] == 'automated'
        assert 'title' in tc
        assert 'links' in tc
