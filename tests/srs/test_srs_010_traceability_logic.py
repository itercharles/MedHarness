"""
Tests for SRS-010: Test Case Traceability Logic

Unit tests for the core traceability logic, independent of configuration.
Tests the actual code that makes test case traceability work.

@links: SRS-010
"""

import pytest
from pathlib import Path
import sys

# Add src and tests/utils to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))


class TestTestCaseScannerIntegration:
    """Test that scanner correctly populates verifies field"""

    def test_TC_SRS_010_020_scanner_maps_links_to_verifies(self):
        """
        TC-SRS-010-020: Verify scanner maps @links to verifies field

        @links: SRS-010
        @test_id: TC-SRS-010-020

        Tests that the test scanner correctly maps @links annotations
        to the verifies field (not links field)
        """
        from case_scanner import AutomatedTestScanner

        scanner = AutomatedTestScanner(Path(__file__).parent.parent.parent)

        test_code = '''
def test_TC_SRS_001_example():
    """
    Test example

    @links: SRS-001
    @test_id: TC-SRS-001
    """
    pass
'''

        import ast
        tree = ast.parse(test_code)
        func_node = tree.body[0]

        test_case = scanner._extract_test_case(func_node, Path('test_file.py'))

        assert 'verifies' in test_case
        assert 'links' not in test_case
        assert 'SRS-001' in test_case['verifies']

    def test_TC_SRS_010_021_multiple_links_supported(self):
        """
        TC-SRS-010-021: Verify multiple @links are supported

        @links: SRS-010
        @test_id: TC-SRS-010-021
        """
        from case_scanner import AutomatedTestScanner

        scanner = AutomatedTestScanner(Path(__file__).parent.parent.parent)

        test_code = '''
def test_TC_SRS_002_example():
    """
    Test with multiple links

    @links: SRS-001, SRS-002, SRS-003
    @test_id: TC-SRS-002
    """
    pass
'''

        import ast
        tree = ast.parse(test_code)
        func_node = tree.body[0]

        test_case = scanner._extract_test_case(func_node, Path('test_file.py'))

        assert 'verifies' in test_case
        assert len(test_case['verifies']) == 3
        assert 'SRS-001' in test_case['verifies']
        assert 'SRS-002' in test_case['verifies']
        assert 'SRS-003' in test_case['verifies']
