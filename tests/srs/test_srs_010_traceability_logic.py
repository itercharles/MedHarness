"""
Tests for SRS-010: Test Case Traceability Logic

Unit tests for the core traceability logic, independent of configuration.
Tests the actual code that makes test case traceability work.

@links: SRS-010
"""

import pytest
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from traceability.compliant_flow_core import CompliantFlowCore


class TestAggregateRelationshipFieldsLogic:
    """Test the _aggregate_relationship_fields method logic"""
    
    @pytest.fixture
    def core(self):
        """Create a minimal CompliantFlowCore instance"""
        dhf_root = Path(__file__).parent.parent.parent / 'DHF'
        return CompliantFlowCore(dhf_root)
    
    def test_TC_SRS_010_015_tc_prefix_triggers_special_handling(self, core):
        """
        TC-SRS-010-015: Verify TC- prefix triggers special handling
        
        @links: SRS-010
        @test_id: TC-SRS-010-015
        
        Tests that any doc_type_code starting with 'TC' uses the special path
        """
        # Create a test case item
        test_item = {
            'id': 'TC-TEST-001',
            'verifies': ['REQ-001', 'REQ-002']
        }
        
        # Call with TC- prefix
        result = core._aggregate_relationship_fields(test_item, 'TC-TEST')
        
        # Should return verifies field values
        assert set(result) == {'REQ-001', 'REQ-002'}
    
    def test_TC_SRS_010_016_verifies_field_extracted_for_tc_items(self, core):
        """
        TC-SRS-010-016: Verify verifies field is extracted for TC-* items
        
        @links: SRS-010
        @test_id: TC-SRS-010-016
        
        Tests that the special handling extracts from 'verifies' field
        """
        # Test with list
        item_with_list = {
            'id': 'TC-SRS-001',
            'verifies': ['SRS-001', 'SRS-002']
        }
        result = core._aggregate_relationship_fields(item_with_list, 'TC-SRS')
        assert result == ['SRS-001', 'SRS-002']
        
        # Test with single string
        item_with_string = {
            'id': 'TC-SRS-002',
            'verifies': 'SRS-003'
        }
        result = core._aggregate_relationship_fields(item_with_string, 'TC-SRS')
        assert result == ['SRS-003']
        
        # Test with empty
        item_empty = {
            'id': 'TC-SRS-003',
            'verifies': []
        }
        result = core._aggregate_relationship_fields(item_empty, 'TC-SRS')
        assert result == []
    
    def test_TC_SRS_010_018_empty_verifies_returns_empty_list(self, core):
        """
        TC-SRS-010-018: Verify empty verifies field returns empty list
        
        @links: SRS-010
        @test_id: TC-SRS-010-018
        """
        item = {
            'id': 'TC-SRS-001'
            # No verifies field
        }
        
        result = core._aggregate_relationship_fields(item, 'TC-SRS')
        assert result == []
    
    def test_TC_SRS_010_019_filters_out_none_values(self, core):
        """
        TC-SRS-010-019: Verify None values are filtered out
        
        @links: SRS-010
        @test_id: TC-SRS-010-019
        """
        item = {
            'id': 'TC-SRS-001',
            'verifies': ['SRS-001', None, 'SRS-002', '']
        }
        
        result = core._aggregate_relationship_fields(item, 'TC-SRS')
        
        # Should filter out None and empty strings
        assert None not in result
        assert '' not in result
        assert set(result) == {'SRS-001', 'SRS-002'}


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
        from test_results.test_case_scanner import AutomatedTestScanner
        
        scanner = AutomatedTestScanner(Path(__file__).parent.parent.parent)
        
        # Create a mock test function with @links annotation
        test_code = '''
def test_TC_SRS_001_example():
    """
    Test example
    
    @links: SRS-001
    @test_id: TC-SRS-001
    """
    pass
'''
        
        # Extract test case metadata
        import ast
        tree = ast.parse(test_code)
        func_node = tree.body[0]
        
        test_case = scanner._extract_test_case(func_node, Path('test_file.py'))
        
        # Should have verifies field, not links
        assert 'verifies' in test_case
        assert 'links' not in test_case
        assert 'SRS-001' in test_case['verifies']
    
    def test_TC_SRS_010_021_multiple_links_supported(self):
        """
        TC-SRS-010-021: Verify multiple @links are supported
        
        @links: SRS-010
        @test_id: TC-SRS-010-021
        """
        from test_results.test_case_scanner import AutomatedTestScanner
        
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
        
        # Should have all 3 links in verifies
        assert 'verifies' in test_case
        assert len(test_case['verifies']) == 3
        assert 'SRS-001' in test_case['verifies']
        assert 'SRS-002' in test_case['verifies']
        assert 'SRS-003' in test_case['verifies']


class TestDocTypeConfiguration:
    """Test that TC-* document types are properly configured"""
    
    @pytest.fixture
    def core(self):
        dhf_root = Path(__file__).parent.parent.parent / 'DHF'
        return CompliantFlowCore(dhf_root)
    
    def test_TC_SRS_010_022_tc_srs_doc_type_exists(self, core):
        """
        TC-SRS-010-022: Verify TC-SRS document type is configured
        
        @links: SRS-010
        @test_id: TC-SRS-010-022
        
        Tests that TC-SRS document type exists in config
        This is what allows get_doc_type_code to work correctly
        """
        doc_types = {dt.code for dt in core.config.doc_types}
        assert 'TC-SRS' in doc_types
    
    def test_TC_SRS_010_023_tc_crs_doc_type_exists(self, core):
        """
        TC-SRS-010-023: Verify TC-CRS document type is configured
        
        @links: SRS-010
        @test_id: TC-SRS-010-023
        """
        doc_types = {dt.code for dt in core.config.doc_types}
        assert 'TC-CRS' in doc_types
    
    def test_TC_SRS_010_024_tc_sys_doc_type_exists(self, core):
        """
        TC-SRS-010-024: Verify TC-SYS document type is configured
        
        @links: SRS-010
        @test_id: TC-SRS-010-024
        """
        doc_types = {dt.code for dt in core.config.doc_types}
        assert 'TC-SYS' in doc_types
    
    def test_TC_SRS_010_025_tc_doc_types_have_verifies_property(self, core):
        """
        TC-SRS-010-025: Verify TC-* doc types have verifies property
        
        @links: SRS-010
        @test_id: TC-SRS-010-025
        
        Tests that the document type configuration includes verifies relationship
        """
        for code in ['TC-SRS', 'TC-CRS', 'TC-SYS']:
            doc_type = next((dt for dt in core.config.doc_types if dt.code == code), None)
            assert doc_type is not None, f"{code} document type should exist"
            
            # Check if verifies property exists
            has_verifies = False
            for p in doc_type.properties:
                if isinstance(p, dict):
                    if p.get('name') == 'verifies':
                        has_verifies = True
                        break
                elif isinstance(p, str):
                    if p == 'verifies':
                        has_verifies = True
                        break
                elif hasattr(p, 'name') and p.name == 'verifies':
                    has_verifies = True
                    break
            
            assert has_verifies, f"{code} should have verifies property"


class TestRegressionPrevention:
    """Tests that specifically prevent the bugs we just fixed"""
    
    @pytest.fixture
    def core(self):
        dhf_root = Path(__file__).parent.parent.parent / 'DHF'
        return CompliantFlowCore(dhf_root)
    
    def test_TC_SRS_010_026_removing_tc_special_handling_breaks(self, core):
        """
        TC-SRS-010-026: Verify removing TC- special handling would break
        
        @links: SRS-010
        @test_id: TC-SRS-010-026
        
        This test ensures that if someone removes the special TC- handling,
        the test will fail
        """
        # Get a TC item
        all_items = core.get_all_items()
        tc_items = [i for i in all_items if i['id'].startswith('TC-')]
        
        assert len(tc_items) > 0, "Need TC items for this test"
        
        tc = tc_items[0]
        
        # The special handling should work
        result = core._aggregate_relationship_fields(tc, 'TC-SRS')
        
        # If special handling is removed, this would return empty
        assert len(result) > 0, \
            "TC- special handling is required for test case traceability"

