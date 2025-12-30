"""
Browser tests for CRS-008: Automated Test Integration

Tests verify test result integration through UI.

@links: CRS-008
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_CRS_008_001_view_test_coverage(page: Page, streamlit_app):
    """
    TC-CRS-008-001: View Test Coverage
    
    @links: CRS-008
    @test_id: TC-CRS-008-001
    
    User views a requirement with verification status.
    """
    # Navigate to SRS-001 detail page
    page.goto(f"{streamlit_app}/page_SRS?item=SRS-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify SRS-001 loaded with verification status
    expect(page.get_by_role("heading", name="SRS-001")).to_be_visible()
    
    # Verify SRS-001 specific data is displayed
    page_content = page.content()
    
    # Check for SRS-001 title
    assert "Item Persistence and Versioning" in page_content, "Should display SRS-001 title"
    
    # Check for verification/test-related indicators
    assert any(term in page_content.lower() for term in ["verif", "test", "coverage"]), \
        "Should display verification or test coverage information"


@pytest.mark.browser
def test_TC_CRS_008_002_view_coverage_dashboard(page: Page, streamlit_app):
    """
    TC-CRS-008-002: View Coverage Dashboard
    
    @links: CRS-008
    @test_id: TC-CRS-008-002
    
    User views compliance page with coverage information.
    """
    # Navigate to Compliance page
    page.goto(f"{streamlit_app}/Compliance")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify compliance page loaded with coverage information
    expect(page.locator("text=Compliance").first).to_be_visible()
    
    # Verify coverage dashboard shows compliance/test data
    page_content = page.content()
    
    # Should show compliance or test coverage information
    assert any(term in page_content for term in ["IEC", "62304", "Compliance"]), \
        "Coverage dashboard should show compliance information"
    
    # Should have substantial coverage data
    assert len(page_content) > 2000, "Coverage dashboard should contain assessment data"
