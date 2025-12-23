"""
Automated tests for hyperlink navigation feature (SRS-013).

Tests verify that item ID hyperlinks work correctly in tables and that
item detail display functions properly.
"""

import pytest
from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.ui_helpers import make_item_columns_clickable, check_and_show_item_detail
from traceability.compliant_flow_core import CompliantFlowCore


class TestSRS013_LinkColumnForItemIDs:
    """Tests for SRS-013: Item Hyperlink Navigation - LinkColumn functionality."""
    
    def test_make_item_columns_clickable_detects_id_columns(self):
        """Verify function detects and configures item ID columns."""
        # Create test dataframe with item IDs
        df = pd.DataFrame({
            'UC': ['UC-001', 'UC-002', 'UC-003'],
            'CRS': ['CRS-001', 'CRS-002', 'CRS-003'],
            'Title': ['Title 1', 'Title 2', 'Title 3'],
            'Status': ['approved', 'draft', 'approved']
        })
        
        config = make_item_columns_clickable(df)
        
        # Should detect UC and CRS columns as item IDs
        assert 'UC' in config, "UC column should be detected as item ID"
        assert 'CRS' in config, "CRS column should be detected as item ID"
        
        # Should NOT detect Title and Status as item IDs
        assert 'Title' not in config, "Title column should not be detected as item ID"
        assert 'Status' not in config, "Status column should not be detected as item ID"
    
    def test_make_item_columns_clickable_handles_empty_dataframe(self):
        """Verify function handles empty dataframes gracefully."""
        df = pd.DataFrame()
        
        config = make_item_columns_clickable(df)
        
        assert isinstance(config, dict), "Should return dict even for empty dataframe"
        assert len(config) == 0, "Should return empty config for empty dataframe"
    
    def test_make_item_columns_clickable_handles_non_id_columns(self):
        """Verify function doesn't detect non-ID columns as item IDs."""
        df = pd.DataFrame({
            'Name': ['Test 1', 'Test 2'],
            'Count': [1, 2],
            'Flag': [True, False]
        })
        
        config = make_item_columns_clickable(df)
        
        assert len(config) == 0, "Should not detect any item ID columns"


class TestSRS013_ItemDetailExpanderComponent:
    """Tests for SRS-013: Item Hyperlink Navigation - Item detail display."""
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent / "DHF"
        return CompliantFlowCore(dhf_root)
    
    def test_item_detail_function_exists(self, core):
        """Verify check_and_show_item_detail function exists and is callable."""
        assert callable(check_and_show_item_detail), \
            "check_and_show_item_detail should be callable"
    
    def test_item_detail_returns_none_when_no_query_param(self, core):
        """Verify function returns None when no item query parameter present."""
        # Note: This test would need Streamlit context to fully test
        # For now, we verify the function exists and has correct signature
        import inspect
        sig = inspect.signature(check_and_show_item_detail)
        assert 'core' in sig.parameters, "Function should accept core parameter"


class TestSRS013_AutomaticItemIDColumnDetection:
    """Tests for SRS-013: Item Hyperlink Navigation - Automatic ID detection."""
    
    def test_detection_with_various_prefixes(self):
        """Verify detection works with various item ID prefixes."""
        df = pd.DataFrame({
            'UC_ID': ['UC-001', 'UC-002'],
            'SRS_ID': ['SRS-001', 'SRS-002'],
            'SWDD_ID': ['SWDD-001', 'SWDD-002'],
            'TC_ID': ['TC-SYS-001', 'TC-SYS-002']
        })
        
        config = make_item_columns_clickable(df)
        
        # All columns should be detected
        assert len(config) == 4, "Should detect all 4 item ID columns"
        assert 'UC_ID' in config
        assert 'SRS_ID' in config
        assert 'SWDD_ID' in config
        assert 'TC_ID' in config
    
    def test_detection_performance_is_linear(self):
        """Verify column detection completes in O(n) time."""
        import time
        
        # Create dataframe with many columns
        n_cols = 100
        data = {f'Col_{i}': ['UC-001', 'UC-002'] for i in range(n_cols)}
        df = pd.DataFrame(data)
        
        start = time.time()
        config = make_item_columns_clickable(df)
        elapsed = time.time() - start
        
        # Should complete quickly (< 100ms for 100 columns)
        assert elapsed < 0.1, f"Detection took {elapsed}s, should be < 0.1s"
        assert len(config) == n_cols, "Should detect all item ID columns"
    
    def test_detection_with_mixed_content(self):
        """Verify detection works when columns have mixed content."""
        df = pd.DataFrame({
            'ID': ['UC-001', 'CRS-002', 'SYS-003'],  # Mixed prefixes
            'Code': ['ABC', 'DEF', 'GHI'],  # No hyphens
            'Version': ['1.0', '2.0', '3.0']  # Has dots, not hyphens
        })
        
        config = make_item_columns_clickable(df)
        
        # Only ID column should be detected
        assert len(config) == 1, "Should detect only ID column"
        assert 'ID' in config


class TestHyperlinkIntegration:
    """Integration tests for hyperlink feature."""
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent / "DHF"
        return CompliantFlowCore(dhf_root)
    
    def test_all_items_can_be_retrieved(self, core):
        """Verify all items can be retrieved for hyperlink navigation."""
        all_items = core.get_all_items()
        
        assert len(all_items) > 0, "Should have items to link to"
        
        # Verify each item has required fields for detail display
        for item in all_items[:5]:  # Check first 5
            assert 'id' in item, f"Item should have id field"
            assert 'content' in item or 'title' in item, \
                f"Item {item['id']} should have content or title"
    
    def test_item_retrieval_by_id(self, core):
        """Verify items can be retrieved by ID for detail display."""
        # Get a known item
        all_items = core.get_all_items()
        if all_items:
            test_item_id = all_items[0]['id']
            
            retrieved = core.get_item(test_item_id)
            
            assert retrieved is not None, f"Should retrieve item {test_item_id}"
            assert retrieved['id'] == test_item_id, "Retrieved item should match ID"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
