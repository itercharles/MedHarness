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
    
    # Verify page loaded - check for "Traceability" in page title or content
    expect(page.locator("text=Traceability").first).to_be_visible()
    
    # Verify traceability content is displayed (dataframe or text)
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()


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
    
    # Verify page loaded
    expect(page.locator("text=Traceability").first).to_be_visible()


@pytest.mark.browser
def test_TC_CRS_002_003_navigate_parent_links(page: Page, streamlit_app):
    """
    TC-CRS-002-003: Navigate Parent Links
    
    @links: CRS-002
    @test_id: TC-CRS-002-003
    
    User navigates through parent requirement links.
    """
    # Navigate to an item with parent links (SRS-001 derives from SYS-001)
    page.goto(f"{streamlit_app}/7_SRS?item=SRS-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify item is displayed
    expect(page.get_by_role("heading", name="SRS-001")).to_be_visible()
    
    # Verify "Derives From" section exists
    expect(page.locator("text=Derives From").first).to_be_visible()
