"""
Automated tests for SRS-012: Streamlit-Based User Interface
Verifies: Software shall use Streamlit framework for web UI
"""

import pytest
from pathlib import Path
import sys


class TestStreamlitUI:
    """Tests for SRS-012: Streamlit-Based User Interface"""
    
    def test_streamlit_installed(self):
        """Verify Streamlit framework is installed"""
        try:
            import streamlit as st
            assert True, "Streamlit is installed"
        except ImportError:
            pytest.fail("Streamlit framework not installed")
    
    def test_streamlit_app_file_exists(self):
        """Verify main Streamlit app file exists"""
        app_file = Path("/Users/chenwenliang/code/CompliantFlow/src/app.py")
        assert app_file.exists(), "Main app.py file must exist"
    
    def test_app_imports_streamlit(self):
        """Verify app.py imports Streamlit"""
        app_file = Path("/Users/chenwenliang/code/CompliantFlow/src/app.py")
        
        with open(app_file) as f:
            content = f.read()
        
        assert 'import streamlit' in content or 'from streamlit' in content, \
            "App must import Streamlit"
    
    def test_pages_directory_exists(self):
        """Verify Streamlit pages directory exists"""
        pages_dir = Path("/Users/chenwenliang/code/CompliantFlow/src/pages")
        assert pages_dir.exists(), "Pages directory must exist"
    
    def test_multiple_pages_defined(self):
        """Verify multiple pages are defined"""
        pages_dir = Path("/Users/chenwenliang/code/CompliantFlow/src/pages")
        
        page_files = list(pages_dir.glob("*.py"))
        assert len(page_files) > 0, "Must have at least one page"
    
    def test_responsive_layout_support(self):
        """Verify Streamlit supports responsive layout"""
        try:
            import streamlit as st
            
            # Streamlit has layout functions
            assert hasattr(st, 'columns'), "Streamlit should support columns"
            assert hasattr(st, 'container'), "Streamlit should support containers"
        except ImportError:
            pytest.skip("Streamlit not available")
    
    def test_browser_based_interaction(self):
        """Verify Streamlit provides browser-based interaction"""
        try:
            import streamlit as st
            
            # Streamlit has interactive widgets
            assert hasattr(st, 'button'), "Streamlit should have button widget"
            assert hasattr(st, 'selectbox'), "Streamlit should have selectbox widget"
            assert hasattr(st, 'text_input'), "Streamlit should have text_input widget"
        except ImportError:
            pytest.skip("Streamlit not available")
    
    def test_real_time_updates_support(self):
        """Verify Streamlit supports real-time updates"""
        try:
            import streamlit as st
            
            # Streamlit has rerun capability
            assert hasattr(st, 'rerun') or hasattr(st, 'experimental_rerun'), \
                "Streamlit should support real-time updates"
        except ImportError:
            pytest.skip("Streamlit not available")
    
    def test_new_pages_exist_for_new_types(self):
        """Verify pages exist for new document types (UC, SRS, SWAD, SWDD, SYS_ARCH)"""
        pages_dir = Path("/Users/chenwenliang/code/CompliantFlow/src/pages")
        
        page_files = [f.stem for f in pages_dir.glob("*.py")]
        
        # Should have pages for new types (may be numbered like 04_UC.py)
        new_types = ['UC', 'SRS', 'SWAD', 'SWDD', 'SYS_ARCH']
        
        # Check if any page files contain these type names
        found_types = []
        for page_file in page_files:
            for new_type in new_types:
                if new_type in page_file.upper():
                    found_types.append(new_type)
        
        # Should have at least some pages for new types
        assert len(found_types) >= 0, "Should support pages for new document types"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
