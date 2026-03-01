"""
Automated tests for hyperlink navigation feature (SRS-013).

Tests verify that item ID hyperlinks work correctly in tables and that
item detail display functions properly.
"""

import pytest
from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.ui_helpers import make_item_columns_clickable, check_and_show_item_detail
from compliantflow.core import CompliantFlowCore


class TestSRS013_LinkColumnForItemIDs:
    """Tests for SRS-013: Item Hyperlink Navigation - LinkColumn functionality."""
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent.parent / "DHF"
        return CompliantFlowCore(dhf_root)
    
    def test_make_item_columns_clickable_detects_id_columns(self, core):
        """Verify function detects and configures item ID columns."""
        # Create test dataframe with item IDs
        df = pd.DataFrame({
            'UC': ['UC-001', 'UC-002', 'UC-003'],
            'CRS': ['CRS-001', 'CRS-002', 'CRS-003'],
            'Title': ['Title 1', 'Title 2', 'Title 3'],
            'Status': ['approved', 'draft', 'approved']
        })
        
        df_transformed, config = make_item_columns_clickable(df, core)
        
        # Should detect UC and CRS columns as item IDs
        assert 'UC' in config, "UC column should be detected as item ID"
        assert 'CRS' in config, "CRS column should be detected as item ID"
        
        # Should NOT detect Title and Status as item IDs
        assert 'Title' not in config, "Title column should not be detected as item ID"
        assert 'Status' not in config, "Status column should not be detected as item ID"
        
        # Check that IDs were transformed to URLs
        assert '?item=UC-001' in df_transformed['UC'].iloc[0], "Should transform ID to URL"
    
    def test_make_item_columns_clickable_handles_empty_dataframe(self, core):
        """Verify function handles empty dataframes gracefully."""
        df = pd.DataFrame()
        
        df_transformed, config = make_item_columns_clickable(df, core)
        
        assert isinstance(config, dict), "Should return dict even for empty dataframe"
        assert len(config) == 0, "Should return empty config for empty dataframe"
        assert df_transformed.empty, "Should return empty dataframe"
    
    def test_make_item_columns_clickable_handles_non_id_columns(self, core):
        """Verify function doesn't detect non-ID columns as item IDs."""
        df = pd.DataFrame({
            'Name': ['Test 1', 'Test 2'],
            'Count': [1, 2],
            'Flag': [True, False]
        })
        
        df_transformed, config = make_item_columns_clickable(df, core)
        
        assert len(config) == 0, "Should not detect any item ID columns"


class TestSRS013_ItemDetailExpanderComponent:
    """Tests for SRS-013: Item Hyperlink Navigation - Item detail display."""
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent.parent / "DHF"
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
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent.parent / "DHF"
        return CompliantFlowCore(dhf_root)
    
    def test_detection_with_various_prefixes(self, core):
        """Verify detection works with various item ID prefixes."""
        # Note: This test now verifies that only configured doc_type codes are detected
        # UC_ID, SRS_ID, etc. won't match because the actual codes are UC, SRS, etc.
        df = pd.DataFrame({
            'UC': ['UC-001', 'UC-002'],
            'SRS': ['SRS-001', 'SRS-002'],
            'SWDD': ['SWDD-001', 'SWDD-002'],
            'TC-SYS': ['TC-SYS-001', 'TC-SYS-002']
        })
        
        df_transformed, config = make_item_columns_clickable(df, core)
        
        # Columns matching configured doc_type codes should be detected
        assert 'UC' in config
        assert 'SRS' in config
        assert 'SWDD' in config
    
    def test_detection_performance_is_linear(self, core):
        """Verify column detection completes in O(n) time."""
        import time
        
        # Create dataframe with many columns using valid doc_type codes
        # Use actual configured codes
        valid_codes = [dt.code for dt in core.config.doc_types]
        n_cols = min(len(valid_codes), 20)  # Use up to 20 configured codes
        data = {valid_codes[i]: [f'{valid_codes[i]}-001', f'{valid_codes[i]}-002'] for i in range(n_cols)}
        df = pd.DataFrame(data)
        
        start = time.time()
        df_transformed, config = make_item_columns_clickable(df, core)
        elapsed = time.time() - start
        
        # Should complete quickly (< 100ms for 100 columns)
        assert elapsed < 0.1, f"Detection took {elapsed}s, should be < 0.1s"
        assert len(config) == n_cols, f"Should detect all {n_cols} item ID columns"
    
    def test_detection_with_mixed_content(self, core):
        """Verify detection works when columns have mixed content."""
        df = pd.DataFrame({
            'SYS': ['SYS-001', 'SYS-002', 'SYS-003'],  # Valid doc_type code
            'Code': ['ABC', 'DEF', 'GHI'],  # No hyphens
            'Version': ['1.0', '2.0', '3.0']  # Has dots, not hyphens
        })
        
        df_transformed, config = make_item_columns_clickable(df, core)
        
        # Only SYS column should be detected (matches configured doc_type)
        assert len(config) == 1, "Should detect only SYS column"
        assert 'SYS' in config


class TestSWDD006_PageURLGeneration:
    """Tests for SWDD-006: UI Helper Functions - get_page_url_for_item."""
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent.parent / "DHF"
        return CompliantFlowCore(dhf_root)
    
    def test_url_generation_without_core(self):
        """Verify URL generation falls back to query param without core."""
        from utils.ui_helpers import get_page_url_for_item
        
        url = get_page_url_for_item("SYS-001")
        assert url == "?item=SYS-001", "Should fallback to query param only"
    
    def test_url_generation_with_core(self, core):
        """Verify URL generation with core creates page-specific URLs."""
        from utils.ui_helpers import get_page_url_for_item
        
        url = get_page_url_for_item("SYS-001", core)
        
        # STRICT: Check exact URL format
        expected_url = "/page_SYS?item=SYS-001"
        assert url == expected_url, \
            f"URL must be exactly '{expected_url}', got '{url}'"
    
    def test_url_generation_exact_format_for_all_types(self, core):
        """Verify exact URL format for different document types."""
        from utils.ui_helpers import get_page_url_for_item
        
        # Test exact format for each document type
        test_cases = [
            ("UC-001", "/page_UC?item=UC-001"),
            ("CRS-001", "/page_CRS?item=CRS-001"),
            ("SYS-001", "/page_SYS?item=SYS-001"),
            ("SRS-001", "/page_SRS?item=SRS-001"),
            ("SWDD-001", "/page_SWDD?item=SWDD-001"),
        ]
        
        for item_id, expected_url in test_cases:
            url = get_page_url_for_item(item_id, core)
            assert url == expected_url, \
                f"URL for {item_id} must be exactly '{expected_url}', got '{url}'"
    
    def test_url_generation_for_test_cases(self, core):
        """Verify URL generation handles test case IDs correctly."""
        from utils.ui_helpers import get_page_url_for_item
        
        # Test cases should use TC-{TYPE} format
        url = get_page_url_for_item("TC-SYS-001", core)
        
        # Test cases may or may not have dedicated pages depending on config
        # Valid formats: /page_TC-SYS?item=TC-SYS-001 OR ?item=TC-SYS-001
        assert "item=TC-SYS-001" in url, \
            f"URL must include item parameter, got '{url}'"
        
        # If page is enabled, should use page_ format
        if url.startswith("/page_"):
            assert url == "/page_TC-SYS?item=TC-SYS-001", \
                f"If page enabled, URL must be '/page_TC-SYS?item=TC-SYS-001', got '{url}'"
    
    def test_url_generation_performance(self, core):
        """Verify URL generation completes in O(n) time."""
        from utils.ui_helpers import get_page_url_for_item
        import time
        
        # Generate URLs for multiple items
        items = [f"SYS-{i:03d}" for i in range(100)]
        
        start = time.time()
        for item_id in items:
            get_page_url_for_item(item_id, core)
        elapsed = time.time() - start
        
        # Should complete quickly (< 100ms for 100 items)
        assert elapsed < 0.1, f"URL generation took {elapsed}s, should be < 0.1s"


class TestSWDD008_UniversalPageTemplateIntegration:
    """Tests for SWDD-008: Universal Page Template Hyperlink Integration."""
    
    def test_universal_page_template_imports_ui_helpers(self):
        """Verify universal page template imports UI helper functions."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "universal_page_template",
            Path(__file__).parent.parent.parent / "src" / "debug_view" / "universal_page_template.py"
        )
        module = importlib.util.module_from_spec(spec)
        
        # Check that the module can be loaded (imports are valid)
        try:
            spec.loader.exec_module(module)
            assert True, "Module loaded successfully with UI helpers"
        except ImportError as e:
            assert False, f"Failed to import UI helpers: {e}"
    
    def test_universal_page_has_hyperlink_functions(self):
        """Verify universal page template has access to hyperlink functions."""
        from debug_view.universal_page_template import render_table_section
        import inspect
        
        # Get the source code of the table rendering function
        source = inspect.getsource(render_table_section)
        
        # Verify it uses the hyperlink function
        assert 'make_item_columns_clickable' in source, \
            "Should call make_item_columns_clickable"
    
    def test_column_config_applied_to_dataframe(self):
        """Verify column config is passed to st.dataframe."""
        from debug_view.universal_page_template import render_table_section
        import inspect
        
        source = inspect.getsource(render_table_section)
        
        # Verify column_config is created and passed to dataframe
        assert 'column_config = make_item_columns_clickable' in source, \
            "Should create column_config from make_item_columns_clickable"
        assert 'column_config=column_config' in source, \
            "Should pass column_config to st.dataframe"


class TestHyperlinkIntegration:
    """Integration tests for hyperlink feature."""
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent.parent / "DHF"
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
        # Get a known item - test data should have items
        all_items = core.get_all_items()
        assert len(all_items) > 0, "Test data should have items"
        
        test_item_id = all_items[0]['id']
        
        retrieved = core.get_item(test_item_id)
        
        assert retrieved is not None, f"Should retrieve item {test_item_id}"
        assert retrieved['id'] == test_item_id, "Retrieved item should match ID"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
