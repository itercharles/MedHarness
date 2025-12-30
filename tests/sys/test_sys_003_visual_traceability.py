"""
Browser tests for SYS-003: Visual Traceability

Verifies: The system shall provide a view of traceability graph or table,
including requirements, architecture, tests, and change requests.

@links: SYS-003
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_SYS_003_001_view_traceability_table(page: Page, streamlit_app):
    """
    TC-SYS-003-001: View Traceability Table
    
    @links: SYS-003
    @test_id: TC-SYS-003-001
    
    Verify system displays traceability table view.
    """
    # Navigate to Traceability page
    page.goto(f"{streamlit_app}/Traceability")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify traceability page loaded
    expect(page.locator("text=Traceability").first).to_be_visible()
    
    # Verify table/dataframe is displayed with data
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()
    
    # Verify traceability contains requirement types (UC, CRS, SYS, SRS, etc.)
    page_content = page.content()
    assert any(req_type in page_content for req_type in ["UC-", "CRS-", "SYS-", "SRS-"]), \
        "Traceability table should contain requirement IDs"
    
    # Verify table shows configurable titles/columns
    # The traceability table should show item types and their relationships
    assert any(col in page_content for col in ["ID", "Type", "Title", "Status"]), \
        "Traceability table should display configurable column headers"
    
    # Verify actual traceability relationships are shown
    # For example, SRS items should trace to SYS items
    # Check that multiple requirement levels are present (indicating traceability chain)
    req_types_found = sum(1 for req_type in ["UC-", "CRS-", "SYS-", "SRS-"] if req_type in page_content)
    assert req_types_found >= 2, f"Traceability table should show multiple requirement levels, found {req_types_found}"
    
    # Verify item IDs are clickable links with correct format
    assert "/page_" in page_content, "Traceability table should contain clickable item links"
    
    # Try clicking on an item link to verify navigation works
    link = page.locator("a[href*='/page_']").first
    if link.is_visible():
        href = link.get_attribute("href")
        assert href.startswith("/page_"), f"Item link should use /page_ format, got: {href}"
        
        # Click and verify no "Page not found" error
        link.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        page_content_after = page.content()
        assert "Page not found" not in page_content_after, \
            "Clicking item link should navigate to valid page"


@pytest.mark.browser
def test_TC_SYS_003_002_view_traceability_graph(page: Page, streamlit_app):
    """
    TC-SYS-003-002: View Traceability Graph
    
    @links: SYS-003
    @test_id: TC-SYS-003-002
    
    Verify system displays traceability graph visualization.
    """
    # Navigate to Traceability page
    page.goto(f"{streamlit_app}/Traceability")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)  # Graph may take time to render
    
    # Verify traceability page loaded with graph visualization
    expect(page.locator("text=Traceability").first).to_be_visible()
    
    # Verify graph or visual elements are present
    page_content = page.content()
    
    # The page should contain requirement items that would be shown in graph
    assert any(req_type in page_content for req_type in ["UC-", "CRS-", "SYS-", "SRS-"]), \
        "Traceability graph should display requirement nodes"
    
    # Verify substantial visualization data is present
    assert len(page_content) > 2000, "Graph visualization should contain substantial data"
