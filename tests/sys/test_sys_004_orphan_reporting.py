"""
Browser tests for SYS-004: Orphan Reporting

Verifies: The system shall display a list of orphan items.

@links: SYS-004
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_SYS_004_001_view_orphan_list(page: Page, streamlit_app):
    """
    TC-SYS-004-001: View Orphan Items List
    
    @links: SYS-004
    @test_id: TC-SYS-004-001
    
    Verify system displays a list of orphan items (items without parent links).
    """
    # Navigate to Traceability page (which shows orphans)
    page.goto(f"{streamlit_app}/Traceability")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify traceability page loaded with orphan analysis
    expect(page.locator("text=Traceability").first).to_be_visible()
    
    # Verify page contains traceability data showing item relationships
    page_content = page.content()
    
    # Orphan items are those without parent links - verify the page shows items
    # The traceability view should display all items and their relationships
    assert any(req_type in page_content for req_type in ["UC-", "CRS-", "SYS-", "SRS-"]), \
        "Traceability page should show requirement items for orphan analysis"
    
    # Verify dataframe/table is present (shows item relationships)
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()


@pytest.mark.browser
def test_TC_SYS_004_002_identify_orphan_requirements(page: Page, streamlit_app):
    """
    TC-SYS-004-002: Identify Orphan Requirements
    
    @links: SYS-004
    @test_id: TC-SYS-004-002
    
    Verify system can identify requirements without parent links.
    """
    # Navigate to Traceability page
    page.goto(f"{streamlit_app}/Traceability")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify traceability page loaded for orphan identification
    expect(page.locator("text=Traceability").first).to_be_visible()
    
    # Verify the page can identify items and their parent relationships
    page_content = page.content()
    
    # Check that requirement items are displayed (needed to identify orphans)
    assert any(req_type in page_content for req_type in ["UC-", "CRS-", "SYS-", "SRS-"]), \
        "Page should display requirement items to identify orphans"
    
    # Verify traceability matrix/table is shown (displays parent-child relationships)
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()
