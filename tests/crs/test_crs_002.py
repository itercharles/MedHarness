"""
Browser tests for CRS-002: Traceability Analysis

Tests verify traceability features through UI.

@links: CRS-002
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_CRS_002_001_view_traceability_table(page: Page, streamlit_app):
    """
    TC-CRS-002-001: View Traceability Table
    
    @links: CRS-002
    @test_id: TC-CRS-002-001
    
    User views traceability matrix showing requirement relationships.
    """
    # Navigate to Traceability page (correct URL)
    page.goto(f"{streamlit_app}/Traceability")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify traceability page loaded with data
    expect(page.locator("text=Traceability").first).to_be_visible()
    
    # Verify traceability table/dataframe is displayed
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()
    
    # Verify table contains requirement IDs
    page_content = page.content()
    assert any(req_type in page_content for req_type in ["UC-", "CRS-", "SYS-", "SRS-"]), \
        "Traceability table should contain requirement IDs"


@pytest.mark.browser
def test_TC_CRS_002_002_view_traceability_graph(page: Page, streamlit_app):
    """
    TC-CRS-002-002: View Traceability Graph
    
    @links: CRS-002
    @test_id: TC-CRS-002-002
    
    User views interactive traceability graph.
    """
    # Navigate to Traceability page
    page.goto(f"{streamlit_app}/Traceability")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)  # Graph may take time to render
    
    # Verify traceability page loaded with graph
    expect(page.locator("text=Traceability").first).to_be_visible()
    
    # Verify graph shows requirement nodes
    page_content = page.content()
    assert any(req_type in page_content for req_type in ["UC-", "CRS-", "SYS-", "SRS-"]), \
        "Traceability graph should display requirement nodes"


@pytest.mark.browser
def test_TC_CRS_002_003_navigate_parent_links(page: Page, streamlit_app):
    """
    TC-CRS-002-003: Navigate Parent Links
    
    @links: CRS-002
    @test_id: TC-CRS-002-003
    
    User navigates through parent requirement links.
    """
    # Navigate to an item with parent links (SRS-001 derives from SYS-001)
    page.goto(f"{streamlit_app}/page_SRS?item=SRS-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify SRS-001 is displayed with parent links
    expect(page.get_by_role("heading", name="SRS-001")).to_be_visible()
    
    # Verify "Derives From" section shows parent relationship
    expect(page.locator("text=Derives From").first).to_be_visible()
    
    # Verify parent link SYS-001 is displayed
    page_content = page.content()
    assert "SYS-001" in page_content, "Should display parent requirement SYS-001"
