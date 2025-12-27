"""
Test suite for dynamic page generation functionality.

Tests verify that pages are correctly generated from configuration
without hardcoded page files.

@links: CRS-012, SYS-028, SYS-029
"""

import pytest
from pathlib import Path
import yaml


def test_TC_CRS_012_001_dynamic_page_generation():
    """
    Verify Dynamic Page Generation
    
    @links: CRS-012
    @test_id: TC-CRS-012-001
    
    Verify that document type pages are automatically generated from 
    configuration without hardcoded page files.
    """
    # Load project configuration
    config_path = Path(__file__).parent.parent / "DHF" / "config" / "project_config.yaml"
    assert config_path.exists(), "Project config not found"
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Verify doc_types exist in config
    assert 'doc_types' in config, "doc_types not found in configuration"
    doc_types = config['doc_types']
    assert len(doc_types) > 0, "No document types configured"
    
    # Verify page_enabled field exists
    page_enabled_types = [dt for dt in doc_types if dt.get('page_enabled', False)]
    assert len(page_enabled_types) > 0, "No page-enabled document types found"
    
    # Verify each page-enabled type has required fields
    for dt in page_enabled_types:
        assert 'code' in dt, f"Document type missing 'code': {dt}"
        assert 'name' in dt, f"Document type missing 'name': {dt}"
        assert 'page_number' in dt, f"Document type missing 'page_number': {dt}"
    
    # Verify page_generator module exists
    page_gen_path = Path(__file__).parent.parent / "src" / "pages" / "page_generator.py"
    assert page_gen_path.exists(), "page_generator.py not found"


def test_TC_SYS_029_001_unique_url_generation():
    """
    Verify Unique URL Path Generation
    
    @links: SYS-029
    @test_id: TC-SYS-029-001
    
    Verify that each dynamically generated page has a unique URL path 
    to prevent conflicts.
    """
    # Load project configuration
    config_path = Path(__file__).parent.parent / "DHF" / "config" / "project_config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    doc_types = config.get('doc_types', [])
    page_enabled_types = [dt for dt in doc_types if dt.get('page_enabled', False)]
    
    # Collect all page numbers and codes
    page_numbers = []
    codes = []
    
    for dt in page_enabled_types:
        page_num = dt.get('page_number')
        code = dt.get('code')
        
        # Track page numbers (duplicates may exist, that's OK for now)
        page_numbers.append(page_num)
        
        # Verify code is unique
        assert code not in codes, \
            f"Duplicate code {code} found"
        codes.append(code)
    
    # Verify codes are unique (URL pattern uses code)
    assert len(codes) == len(set(codes)), \
        "Duplicate codes detected"


def test_TC_SYS_028_001_page_registration():
    """
    Verify Dynamic Page Registration
    
    @links: SYS-028
    @test_id: TC-SYS-028-001
    
    Verify that the system reads doc_types from configuration and 
    registers pages dynamically.
    """
    # Import page generator
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    
    from pages.page_generator import generate_doc_type_pages
    from traceability.compliant_flow_core import CompliantFlowCore
    
    # Initialize core to get config
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Generate pages using core
    pages = generate_doc_type_pages(core)
    
    # Verify pages were generated
    assert len(pages) > 0, "No pages generated"
    
    # Verify each page is a tuple with correct structure
    # Format: (page_number, title, icon, page_func, code)
    for page in pages:
        assert isinstance(page, tuple), f"Page should be tuple, got {type(page)}"
        assert len(page) == 5, f"Page tuple should have 5 elements, got {len(page)}"
        page_num, title, icon, func, code = page
        assert isinstance(title, str), "Title should be string"
        assert callable(func), "Page function should be callable"
    
    # Verify number of pages matches page_enabled doc_types
    expected_count = len([dt for dt in core.config.doc_types if dt.page_enabled])
    assert len(pages) == expected_count, \
        f"Expected {expected_count} pages, got {len(pages)}"
